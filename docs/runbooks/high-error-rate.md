# Runbook: High API Error Rate

**Alert Name:** `HighAPIErrorRate`
**Severity:** Critical
**Component:** API
**Team:** Backend

## Overview

This alert fires when the API error rate (5xx responses) exceeds 1% over a 5-minute period. This indicates a significant problem with the API service that requires immediate investigation.

## Impact

- Users experiencing service degradation or failures
- Data pipeline disruptions
- Potential data loss or corruption
- SLA violations

## Triage Steps

### 1. Verify the Alert

```bash
# Check current error rate
curl http://prometheus:9090/api/v1/query?query='sum(rate(http_requests_total{status=~"5.."}[5m]))/sum(rate(http_requests_total[5m]))*100'

# Check which endpoints are failing
curl http://prometheus:9090/api/v1/query?query='topk(10,sum(rate(http_requests_total{status=~"5.."}[5m]))by(endpoint,method))'
```

### 2. Check Service Health

```bash
# Verify API containers are running
docker ps | grep corporate-intel-api

# Check container health status
docker inspect corporate-intel-api --format='{{.State.Health.Status}}'

# Review recent container events
docker events --since 30m --filter 'container=corporate-intel-api'
```

### 3. Review Logs

```bash
# Check API error logs (last 100 lines)
docker logs corporate-intel-api --tail 100 | grep -i error

# Follow real-time logs
docker logs -f corporate-intel-api

# Check for specific error patterns
docker logs corporate-intel-api --since 15m | grep -E "500|502|503|504"
```

### 4. Check Dependencies

```bash
# Verify database connectivity
docker exec corporate-intel-api pg_isready -h postgres -U $POSTGRES_USER

# Check Redis connectivity
docker exec corporate-intel-api redis-cli -h redis -a $REDIS_PASSWORD ping

# Verify external API status
curl -I https://www.sec.gov/
curl -I https://finance.yahoo.com/
```

## Common Causes and Solutions

### Cause 1: Database Connection Pool Exhaustion

**Symptoms:**
- Logs show "connection pool exhausted" or "too many connections"
- Database connection alerts also firing

**Solution:**
```bash
# Check current database connections
docker exec postgres psql -U $POSTGRES_USER -d $POSTGRES_DB -c "SELECT count(*) FROM pg_stat_activity;"

# Identify long-running queries
docker exec postgres psql -U $POSTGRES_USER -d $POSTGRES_DB -c "SELECT pid, now() - pg_stat_activity.query_start AS duration, query FROM pg_stat_activity WHERE state = 'active' ORDER BY duration DESC;"

# If necessary, kill long-running queries
docker exec postgres psql -U $POSTGRES_USER -d $POSTGRES_DB -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE pid = <PID>;"

# Restart API to reset connection pool
docker restart corporate-intel-api
```

### Cause 2: Memory Pressure / OOM

**Symptoms:**
- Container restarts in logs
- High memory usage metrics
- Logs show "MemoryError" or OOM events

**Solution:**
```bash
# Check container memory usage
docker stats corporate-intel-api --no-stream

# Review OOM events
dmesg | grep -i oom

# Scale up API instances (if using orchestration)
docker-compose -f docker-compose.prod.yml up -d --scale api=3

# Increase container memory limits (edit docker-compose.prod.yml)
# Then restart:
docker-compose -f docker-compose.prod.yml up -d api
```

### Cause 3: External API Failures

**Symptoms:**
- External API error alerts also firing
- Logs show "connection timeout" or "external API error"
- Circuit breaker states show "OPEN"

**Solution:**
```bash
# Check external API circuit breaker states
curl http://prometheus:9090/api/v1/query?query='external_api_circuit_breaker_state'

# Temporarily disable problematic external API integrations
# (Implementation depends on your configuration management)

# Monitor for recovery
watch -n 5 'docker logs corporate-intel-api --tail 20 | grep "external.*api"'
```

### Cause 4: Code Deployment Issues

**Symptoms:**
- Errors started after recent deployment
- Specific endpoints returning 500s
- Stack traces in logs point to new code

**Solution:**
```bash
# Rollback to previous version
docker pull ghcr.io/yourusername/corporate-intel:<previous-tag>
docker-compose -f docker-compose.prod.yml up -d api

# Or use git to revert and redeploy
git revert <commit-hash>
git push
# Trigger CI/CD pipeline

# Monitor error rate after rollback
watch -n 10 'curl -s http://prometheus:9090/api/v1/query?query="sum(rate(http_requests_total{status=~\"5..\"}[5m]))/sum(rate(http_requests_total[5m]))*100" | jq ".data.result[0].value[1]"'
```

## Escalation

If the issue persists after 30 minutes of troubleshooting:

1. **Page on-call engineer:** Use PagerDuty to escalate
2. **Notify stakeholders:** Post in #incidents Slack channel
3. **Create incident:** Open incident ticket with severity P1
4. **Engage vendor support:** If external API issues, contact provider

## Post-Incident

After resolving the incident:

1. Document root cause in incident report
2. Update this runbook with new learnings
3. Schedule post-mortem meeting
4. Create follow-up tasks for preventive measures

## Monitoring & Alerts

- **Grafana Dashboard:** [API Performance](http://grafana:3000/d/api-performance)
- **Prometheus:** http://prometheus:9090
- **Sentry:** Check for error spikes
- **Related Alerts:**
  - `HighAPILatencyP99`
  - `DatabaseDown`
  - `RedisDown`
  - `SECAPIHighErrorRate`

## Additional Resources

- [API Architecture Documentation](../deployment/api-architecture.md)
- [Database Troubleshooting Guide](./database-down.md)
- [External API Configuration](../../config/production/data-sources/)
- [Deployment Procedures](../deployment/deployment-guide.md)

---

**Last Updated:** 2025-10-25
**Owner:** Backend Team
**Reviewers:** DevOps Team
