# Runbook: Backup Failure

**Alert Name:** `PostgreSQLBackupFailure` / `MinIOBackupFailure` / `BackupExecutionError`
**Severity:** Critical (Page)
**Component:** Backup
**Team:** DevOps

## Overview

This alert fires when a backup job fails or hasn't completed successfully within the expected timeframe (typically 24 hours). Regular backups are critical for disaster recovery and data protection.

## Impact

- **Data loss risk** if system failure occurs
- **Compliance violations** for data retention requirements
- **Recovery Time Objective (RTO) at risk**
- **Recovery Point Objective (RPO) at risk**

## Immediate Response

### 1. Assess Current Backup Status

```bash
# Check last successful backup timestamps
curl http://prometheus:9090/api/v1/query?query='backup_last_success_timestamp_seconds'

# Check recent backup executions
ls -lth /path/to/backups/ | head -20

# Verify backup storage availability
df -h | grep backup
```

### 2. Identify Failed Component

```bash
# PostgreSQL backups
ls -lth /var/backups/postgres/ | head -10

# Redis backups
ls -lth /var/backups/redis/ | head -10

# MinIO backups
mc ls minio-backup/corporate-intel/

# Check backup logs
tail -100 /var/log/backups/backup.log
```

## Diagnostic Steps

### PostgreSQL Backup Failure

**Check backup script execution:**

```bash
# Review backup script logs
cat /var/log/backups/postgres-backup.log

# Manually test backup script
sudo -u postgres /scripts/backup/postgres-backup.sh --test

# Check pg_dump availability
docker exec corporate-intel-postgres which pg_dump

# Verify database connectivity
docker exec corporate-intel-postgres pg_isready -U $POSTGRES_USER
```

**Common PostgreSQL backup issues:**

1. **Insufficient Disk Space:**
   ```bash
   # Check available space
   df -h /var/backups/postgres

   # Clean old backups (keep last 30 days)
   find /var/backups/postgres -name "*.sql.gz" -mtime +30 -delete

   # Check backup size estimates
   docker exec corporate-intel-postgres psql -U $POSTGRES_USER -d $POSTGRES_DB -c \
     "SELECT pg_size_pretty(pg_database_size('$POSTGRES_DB'));"
   ```

2. **Permission Denied:**
   ```bash
   # Check backup directory permissions
   ls -ld /var/backups/postgres

   # Fix permissions if needed
   sudo chown -R postgres:postgres /var/backups/postgres
   sudo chmod 750 /var/backups/postgres
   ```

3. **Database Lock/Timeout:**
   ```bash
   # Check for long-running transactions
   docker exec corporate-intel-postgres psql -U $POSTGRES_USER -d $POSTGRES_DB -c \
     "SELECT pid, usename, application_name, state, query_start, query FROM pg_stat_activity WHERE state = 'active' ORDER BY query_start;"

   # Increase backup timeout in script
   # Edit /scripts/backup/postgres-backup.sh
   # Add: --lock-wait-timeout=3600
   ```

4. **pg_dump Version Mismatch:**
   ```bash
   # Check PostgreSQL version
   docker exec corporate-intel-postgres psql -U postgres -c "SELECT version();"

   # Check pg_dump version
   pg_dump --version

   # Use matching version from container
   docker exec corporate-intel-postgres pg_dump --version
   ```

### Redis Backup Failure

**Check Redis persistence:**

```bash
# Check Redis configuration
docker exec corporate-intel-redis redis-cli CONFIG GET save
docker exec corporate-intel-redis redis-cli CONFIG GET appendonly

# Check last BGSAVE
docker exec corporate-intel-redis redis-cli LASTSAVE

# Check for BGSAVE errors
docker exec corporate-intel-redis redis-cli INFO persistence | grep last_bgsave

# Manually trigger backup
docker exec corporate-intel-redis redis-cli BGSAVE
```

**Common Redis backup issues:**

1. **Disk Space:**
   ```bash
   df -h /var/lib/docker/volumes/corporate-intel-redis-data

   # Clean old AOF/RDB files if safe
   # WARNING: This can cause data loss
   docker exec corporate-intel-redis sh -c "find /data -name 'temp-*.rdb' -delete"
   ```

2. **Write Permissions:**
   ```bash
   docker exec corporate-intel-redis ls -la /data

   # Check Redis log for permission errors
   docker logs corporate-intel-redis | grep -i permission
   ```

3. **BGSAVE Failures:**
   ```bash
   # Check system memory
   free -h

   # Check for fork() failures
   docker logs corporate-intel-redis | grep -i "fork\|background"

   # Temporarily disable background saves and use SAVE (blocking)
   docker exec corporate-intel-redis redis-cli SAVE
   ```

### MinIO Backup Failure

**Check MinIO backup job:**

```bash
# Verify MinIO accessibility
mc ls minio/corporate-intel/

# Check backup destination
mc ls minio-backup/corporate-intel/

# Test connectivity
mc admin info minio
mc admin info minio-backup

# Review mc mirror logs
cat /var/log/backups/minio-backup.log
```

**Common MinIO backup issues:**

1. **Network Connectivity:**
   ```bash
   # Test network to backup destination
   ping -c 3 backup-server.example.com

   # Test S3 compatibility
   aws s3 ls s3://backup-bucket/corporate-intel/ --endpoint-url=https://backup-server.example.com
   ```

2. **Authentication Failure:**
   ```bash
   # Verify MinIO credentials
   mc alias ls

   # Re-configure alias if needed
   mc alias set minio-backup https://backup.example.com ACCESS_KEY SECRET_KEY

   # Test authentication
   mc admin info minio-backup
   ```

3. **Bucket Permissions:**
   ```bash
   # Check bucket policy
   mc admin policy list minio-backup

   # Verify bucket exists
   mc ls minio-backup | grep corporate-intel

   # Create bucket if missing
   mc mb minio-backup/corporate-intel
   ```

## Manual Backup Execution

If automated backups are failing, run manual backups:

### PostgreSQL Manual Backup

```bash
# Full database backup
docker exec corporate-intel-postgres pg_dump \
  -U $POSTGRES_USER \
  -d $POSTGRES_DB \
  -F c \
  -f /backups/manual-backup-$(date +%Y%m%d-%H%M%S).dump

# Copy backup out of container
docker cp corporate-intel-postgres:/backups/manual-backup-*.dump \
  /var/backups/postgres/emergency/

# Compress and verify
gzip /var/backups/postgres/emergency/manual-backup-*.dump
ls -lh /var/backups/postgres/emergency/
```

### Redis Manual Backup

```bash
# Trigger BGSAVE
docker exec corporate-intel-redis redis-cli BGSAVE

# Wait for completion
while [ "$(docker exec corporate-intel-redis redis-cli LASTSAVE)" == "$LAST_SAVE" ]; do
  sleep 5
done

# Copy RDB file
docker cp corporate-intel-redis:/data/dump.rdb \
  /var/backups/redis/emergency/redis-$(date +%Y%m%d-%H%M%S).rdb
```

### MinIO Manual Backup

```bash
# Mirror to backup location
mc mirror minio/corporate-intel minio-backup/corporate-intel-$(date +%Y%m%d)

# Or sync specific bucket
aws s3 sync s3://corporate-intel s3://backup-bucket/corporate-intel-$(date +%Y%m%d) \
  --endpoint-url=http://minio:9000
```

## Backup Verification

Always verify backups after manual or automated execution:

### Verify PostgreSQL Backup

```bash
# Check backup file integrity
pg_restore --list /var/backups/postgres/backup-latest.dump | head -20

# Test restore to temporary database (RECOMMENDED)
docker exec corporate-intel-postgres psql -U postgres -c "CREATE DATABASE backup_test;"
docker exec corporate-intel-postgres pg_restore \
  -U postgres \
  -d backup_test \
  /backups/backup-latest.dump

# Verify table counts
docker exec corporate-intel-postgres psql -U postgres -d backup_test -c \
  "SELECT schemaname, tablename, n_live_tup FROM pg_stat_user_tables ORDER BY n_live_tup DESC;"

# Cleanup test database
docker exec corporate-intel-postgres psql -U postgres -c "DROP DATABASE backup_test;"
```

### Verify Redis Backup

```bash
# Check RDB file integrity
redis-check-rdb /var/backups/redis/dump.rdb

# Optional: Load into test instance
docker run --rm -v /var/backups/redis:/data redis:7-alpine \
  redis-server --dbfilename dump.rdb --dir /data --port 0 --save ""
```

### Verify MinIO Backup

```bash
# Compare file counts
SOURCE_COUNT=$(mc ls --recursive minio/corporate-intel | wc -l)
BACKUP_COUNT=$(mc ls --recursive minio-backup/corporate-intel-latest | wc -l)

echo "Source files: $SOURCE_COUNT"
echo "Backup files: $BACKUP_COUNT"

# Verify critical files
mc ls minio-backup/corporate-intel-latest/data/
mc ls minio-backup/corporate-intel-latest/reports/
```

## Recovery Testing

Schedule regular recovery tests (quarterly):

```bash
# Full disaster recovery test
# See: docs/deployment/disaster-recovery-test.md

# Quick recovery test
./scripts/backup/test-restore.sh
```

## Root Cause Analysis

Common root causes to investigate:

1. **Storage Issues:**
   - Disk space exhaustion
   - I/O performance degradation
   - Mount point failures

2. **Resource Constraints:**
   - Memory pressure during backup
   - CPU saturation
   - Network bandwidth limits

3. **Timing Issues:**
   - Backup running during peak load
   - Overlapping backup jobs
   - Timeout too aggressive

4. **Configuration Drift:**
   - Changed credentials
   - Modified permissions
   - Firewall rules blocking backup traffic

## Escalation

If backups cannot be restored within 2 hours:

1. **Page:** Senior DevOps Engineer
2. **Notify:** CTO and VP Engineering
3. **Create:** P0 incident
4. **Document:** All troubleshooting steps taken
5. **Consider:** Emergency snapshot of production data
6. **Engage:** Vendor support if using managed backup service

## Prevention & Hardening

After resolving backup failures:

1. **Implement backup monitoring:**
   ```bash
   # Add Prometheus metrics
   # Add backup verification alerts
   # Schedule automated restore tests
   ```

2. **Review backup strategy:**
   - Increase backup frequency for critical data
   - Implement incremental backups
   - Add offsite/cloud backup replication
   - Test backup retention policies

3. **Improve backup scripts:**
   - Add comprehensive error handling
   - Implement retry logic
   - Add Slack/email notifications
   - Log all backup operations

4. **Document recovery procedures:**
   - Update disaster recovery plan
   - Train team on restore procedures
   - Create runbooks for each component

## Related Alerts

- `BackupStorageLow`
- `BackupVerificationFailure`
- `BackupNotVerified`
- `DRTestOverdue`

## Additional Resources

- [Backup Architecture](../deployment/backup-architecture.md)
- [Disaster Recovery Plan](../deployment/disaster-recovery.md)
- [Backup Scripts](../../scripts/backup/)
- [PostgreSQL Backup Documentation](https://www.postgresql.org/docs/current/backup.html)
- [Redis Persistence Documentation](https://redis.io/docs/management/persistence/)
- [MinIO Backup Best Practices](https://min.io/docs/minio/linux/operations/data-recovery.html)

---

**Last Updated:** 2025-10-25
**Owner:** DevOps Team
**Critical:** Test backups monthly, verify quarterly
