# Runbook: Database Down

**Alert Name:** `DatabaseDown`
**Severity:** Critical (Page)
**Component:** Database
**Team:** Backend / DevOps

## Overview

This alert fires when PostgreSQL database is unreachable for more than 2 minutes. This is a critical incident that will cause complete API outage.

## Impact

- **Complete API outage** - All read/write operations fail
- **Data pipeline failures** - ETL processes cannot execute
- **User impact** - Application unavailable
- **P0 Incident** - Immediate response required

## Immediate Response (First 5 Minutes)

### 1. Acknowledge Alert

```bash
# Acknowledge in PagerDuty
# Post in #incidents Slack channel: "Database down alert - investigating"
```

### 2. Check Database Container Status

```bash
# Check if container is running
docker ps -a | grep postgres

# If not running, check why it stopped
docker logs corporate-intel-postgres --tail 100

# Check container health
docker inspect corporate-intel-postgres --format='{{.State.Status}} - {{.State.Health.Status}}'
```

### 3. Quick Health Check

```bash
# Try to connect directly
docker exec corporate-intel-postgres pg_isready -U $POSTGRES_USER

# Check PostgreSQL is listening
docker exec corporate-intel-postgres netstat -plnt | grep 5432
```

## Diagnostic Steps

### Check Container State

```bash
# View detailed container state
docker inspect corporate-intel-postgres | jq '.[0].State'

# Check recent container events
docker events --since 30m --filter 'container=corporate-intel-postgres'

# Review restart history
docker inspect corporate-intel-postgres | jq '.[0].RestartCount'
```

### Check Database Logs

```bash
# Review PostgreSQL logs
docker logs corporate-intel-postgres --tail 200

# Look for specific error patterns
docker logs corporate-intel-postgres | grep -i -E "fatal|error|panic|corruption"

# Check for authentication issues
docker logs corporate-intel-postgres | grep -i "authentication\|password"
```

### Check System Resources

```bash
# Check disk space on database volume
df -h | grep postgres

# Check memory usage
free -h

# Check for OOM kills
dmesg | grep -i -E "oom|out of memory|postgres"

# Check I/O wait
iostat -x 5 3
```

### Check Network Connectivity

```bash
# Test network from API container
docker exec corporate-intel-api nc -zv postgres 5432

# Check DNS resolution
docker exec corporate-intel-api nslookup postgres

# Verify network exists
docker network inspect corporate-intel-network
```

## Common Causes and Solutions

### Cause 1: Container Crashed/Stopped

**Symptoms:**
- Container status shows "Exited" or "Dead"
- Recent restart in logs

**Solution:**
```bash
# Start the container
docker start corporate-intel-postgres

# If that fails, check docker-compose
docker-compose -f docker-compose.prod.yml up -d postgres

# Monitor startup
docker logs -f corporate-intel-postgres

# Verify connectivity
docker exec corporate-intel-postgres pg_isready -U $POSTGRES_USER
```

### Cause 2: Disk Space Exhausted

**Symptoms:**
- Logs show "No space left on device"
- df shows 100% usage

**Solution:**
```bash
# Check disk usage
df -h

# Identify large files
du -sh /var/lib/docker/volumes/* | sort -rh | head -10

# Clean up Docker (CAUTION - may remove data)
docker system prune -a --volumes

# If critical, add emergency storage
# Or clear old WAL files (PostgreSQL)
docker exec postgres sh -c "cd /var/lib/postgresql/data/pg_wal && ls -lt | tail -n +11 | awk '{print $9}' | xargs rm -f"

# Restart database
docker restart corporate-intel-postgres
```

### Cause 3: Corrupted Data Files

**Symptoms:**
- Logs show "could not open file" or "invalid page header"
- Database refuses to start
- Checksum failures

**Solution:**
```bash
# CRITICAL: This is a restore scenario

# 1. Stop all services
docker-compose -f docker-compose.prod.yml down

# 2. Backup corrupted data (for forensics)
sudo cp -r /var/lib/docker/volumes/corporate-intel-postgres-data /tmp/postgres-corrupted-$(date +%Y%m%d)

# 3. Restore from most recent backup
# See: docs/runbooks/backup-failure.md

# 4. If no backup available, attempt recovery
docker run --rm -v corporate-intel-postgres-data:/var/lib/postgresql/data \
  timescale/timescaledb:latest-pg15 \
  pg_resetwal -f /var/lib/postgresql/data

# 5. Restart services
docker-compose -f docker-compose.prod.yml up -d
```

### Cause 4: Authentication/Permission Issues

**Symptoms:**
- Logs show "authentication failed" or "FATAL: password authentication failed"
- pg_isready works but applications can't connect

**Solution:**
```bash
# Verify environment variables
docker exec corporate-intel-postgres env | grep POSTGRES

# Check pg_hba.conf
docker exec corporate-intel-postgres cat /var/lib/postgresql/data/pg_hba.conf

# Reset password (if necessary)
docker exec corporate-intel-postgres psql -U postgres -c "ALTER USER $POSTGRES_USER WITH PASSWORD '$NEW_PASSWORD';"

# Update application environment variables
# Edit .env file and restart API
docker-compose -f docker-compose.prod.yml restart api
```

### Cause 5: Too Many Connections

**Symptoms:**
- Logs show "too many connections" or "remaining connection slots are reserved"
- Connection pool exhaustion

**Solution:**
```bash
# Check current connections
docker exec corporate-intel-postgres psql -U $POSTGRES_USER -d $POSTGRES_DB -c \
  "SELECT count(*) FROM pg_stat_activity;"

# Check max_connections setting
docker exec corporate-intel-postgres psql -U $POSTGRES_USER -d $POSTGRES_DB -c \
  "SHOW max_connections;"

# Identify connection sources
docker exec corporate-intel-postgres psql -U $POSTGRES_USER -d $POSTGRES_DB -c \
  "SELECT application_name, count(*) FROM pg_stat_activity GROUP BY application_name;"

# Kill idle connections (if safe)
docker exec corporate-intel-postgres psql -U $POSTGRES_USER -d $POSTGRES_DB -c \
  "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle' AND state_change < now() - interval '5 minutes';"

# Increase max_connections (edit docker-compose.prod.yml)
# Then restart database
docker-compose -f docker-compose.prod.yml restart postgres
```

### Cause 6: Out of Memory (OOM)

**Symptoms:**
- Container restarted suddenly
- dmesg shows OOM killer events
- "Memory cgroup out of memory" in logs

**Solution:**
```bash
# Check OOM kills
dmesg | grep -i oom | grep postgres

# Check memory limits
docker inspect corporate-intel-postgres | jq '.[0].HostConfig.Memory'

# Increase memory limit in docker-compose.prod.yml
# Add/modify:
#   mem_limit: 4g
#   memswap_limit: 4g

# Restart with new limits
docker-compose -f docker-compose.prod.yml up -d postgres

# Tune PostgreSQL memory settings
# Edit docker-compose.prod.yml environment variables:
#   POSTGRES_SHARED_BUFFERS: 1GB (reduce from 2GB)
#   POSTGRES_EFFECTIVE_CACHE_SIZE: 3GB (reduce from 6GB)
```

## Recovery Verification

After database is restored:

```bash
# 1. Verify database is running
docker exec corporate-intel-postgres pg_isready -U $POSTGRES_USER

# 2. Test query execution
docker exec corporate-intel-postgres psql -U $POSTGRES_USER -d $POSTGRES_DB -c "SELECT 1;"

# 3. Check replication lag (if applicable)
docker exec corporate-intel-postgres psql -U $POSTGRES_USER -d $POSTGRES_DB -c \
  "SELECT * FROM pg_stat_replication;"

# 4. Verify API connectivity
curl http://api:8000/health

# 5. Monitor error rate
watch -n 5 'curl -s http://prometheus:9090/api/v1/query?query="sum(rate(http_requests_total{status=~\"5..\"}[1m]))" | jq'

# 6. Check alert status
curl http://alertmanager:9093/api/v2/alerts | jq '.[] | select(.labels.alertname=="DatabaseDown")'
```

## Escalation

**Immediate Escalation Required:**

1. **Notify:** Post in #incidents Slack channel
2. **Page:** Database Administrator (if different from on-call)
3. **Create:** P0 incident ticket
4. **Status Page:** Update status.corporate-intel.com
5. **Stakeholders:** Notify executive team if outage >15 minutes

## Prevention

After recovery, implement these preventive measures:

1. **Review and test backups:**
   ```bash
   # Run backup verification
   ./scripts/backup/verify-backups.sh
   ```

2. **Increase monitoring sensitivity:**
   - Add disk space trending alerts
   - Add replication lag monitoring
   - Add connection pool usage alerts

3. **Review resource limits:**
   - Ensure adequate disk space (>50% free)
   - Verify memory limits are appropriate
   - Check connection pool configuration

4. **Update documentation:**
   - Document root cause in incident report
   - Update this runbook with learnings
   - Share findings with team

## Related Alerts

- `HighDatabaseConnectionPoolUsage`
- `DatabaseReplicationLag`
- `HighDatabaseStorageUsage`
- `APIServiceDown`

## Additional Resources

- [Backup & Recovery Procedures](../deployment/backup-recovery.md)
- [Database Tuning Guide](../deployment/database-tuning.md)
- [PostgreSQL Official Documentation](https://www.postgresql.org/docs/)
- [TimescaleDB Documentation](https://docs.timescale.com/)

---

**Last Updated:** 2025-10-25
**Owner:** DevOps Team
**Reviewers:** Backend Team, Database Administrator
