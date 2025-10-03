# Deployment Runbook

**Production deployment checklist and operational procedures for Corporate Intel platform.**

## Quick Reference

| Environment | URL | Namespace | Min Replicas |
|------------|-----|-----------|--------------|
| Staging | https://staging-api.corporate-intel.com | staging | 2 |
| Production | https://api.corporate-intel.com | production | 5 |

## Pre-Deployment Checklist

### 1. Code Review ✓
- [ ] All PRs reviewed and approved
- [ ] CI/CD pipeline passing (green build)
- [ ] Security scan completed (no critical vulnerabilities)
- [ ] Unit tests passing (>90% coverage)
- [ ] Integration tests passing
- [ ] Performance tests passing (no regression)

### 2. Infrastructure Validation ✓
- [ ] Kubernetes cluster healthy
- [ ] Database connections verified
- [ ] Redis/cache available
- [ ] RabbitMQ operational
- [ ] MinIO/S3 accessible
- [ ] Vault secrets accessible

### 3. Database Preparation ✓
- [ ] Database backup completed
- [ ] Migration scripts reviewed
- [ ] Migration dry-run successful
- [ ] Rollback plan documented

### 4. Monitoring Setup ✓
- [ ] Grafana dashboards accessible
- [ ] Prometheus collecting metrics
- [ ] AlertManager configured
- [ ] Slack notifications working
- [ ] PagerDuty integration active

## Deployment Procedures

### Staging Deployment

**Timeline: ~15 minutes**

```bash
# 1. Verify current state
kubectl get pods -n staging
helm list -n staging

# 2. Create backup
./scripts/backup/backup-database.sh

# 3. Deploy to staging
./scripts/deploy-staging.sh staging-<git-sha>

# 4. Verify deployment
kubectl rollout status deployment/staging-corporate-intel-api -n staging

# 5. Run smoke tests
kubectl run smoke-test \
  --image=curlimages/curl:latest \
  --namespace=staging \
  --restart=Never --rm -it \
  --command -- sh -c "
    curl -sf https://staging-api.corporate-intel.com/health &&
    curl -sf https://staging-api.corporate-intel.com/api/v1/health
  "

# 6. Monitor for 10 minutes
kubectl logs -f -n staging -l app=corporate-intel
```

**Success Criteria:**
- All pods running and healthy
- Health checks passing
- No errors in logs
- Smoke tests successful
- Response times < 500ms

### Production Deployment

**Timeline: ~30-45 minutes**

#### Phase 1: Pre-Deployment (10 min)

```bash
# 1. Announce maintenance window
# Send notifications to #engineering and #ops

# 2. Create database backup
./scripts/backup/backup-database.sh

# 3. Review changes
git diff production..main

# 4. Tag release
git tag -a v1.0.0 -m "Production release v1.0.0"
git push origin v1.0.0
```

#### Phase 2: Deployment (15 min)

```bash
# 1. Deploy to production (with safety checks)
./scripts/deploy-production.sh v1.0.0

# The script will:
# - Verify Docker image exists
# - Run security scan
# - Check database connectivity
# - Preview migrations
# - Deploy with Helm
# - Run migrations
# - Wait for rollout
# - Validate health checks
```

#### Phase 3: Post-Deployment (15 min)

```bash
# 1. Verify application health
curl -sf https://api.corporate-intel.com/health

# 2. Run comprehensive smoke tests
./tests/integration/smoke-tests.sh production

# 3. Monitor metrics
# - Grafana: Error rates, latency, throughput
# - Prometheus: Resource usage
# - Logs: Check for errors

# 4. Performance validation
k6 run --vus 50 --duration 2m tests/performance/k6-script.js

# 5. Create deployment record
cat > deployment-record.md <<EOF
## Deployment v1.0.0
- **Time:** $(date)
- **Deployed by:** $USER
- **Git SHA:** $(git rev-parse HEAD)
- **Status:** SUCCESS
- **Rollback plan:** helm rollback corporate-intel -n production
EOF
```

**Success Criteria:**
- All pods healthy (5+ replicas)
- Error rate < 0.1%
- P95 latency < 500ms
- P99 latency < 1s
- No critical alerts firing
- Smoke tests passing
- Performance metrics stable

## Rollback Procedures

### Quick Rollback (< 5 minutes)

```bash
# Helm rollback (recommended)
helm rollback corporate-intel -n production
kubectl rollout status deployment/prod-corporate-intel-api -n production

# Or kubectl rollback
kubectl rollout undo deployment/prod-corporate-intel-api -n production
```

### Full Rollback with Database

```bash
# 1. Rollback application
helm rollback corporate-intel -n production

# 2. Rollback database (if migrations ran)
# List available backups
aws s3 ls s3://corporate-intel-backups/postgres/

# Restore database
./scripts/backup/restore-database.sh corporate_intel_20250103_120000.sql.gz

# 3. Verify rollback
curl -sf https://api.corporate-intel.com/health
./tests/integration/smoke-tests.sh production
```

## Canary Deployment

**For zero-downtime deployments with gradual traffic shift**

### Phase 1: Deploy Canary (10%)

```bash
./scripts/canary-deploy.sh v1.0.0 10

# Monitor for 15 minutes
# - Error rates
# - Latency (P95, P99)
# - Resource usage
# - Business metrics
```

### Phase 2: Increase to 50%

```bash
# If metrics are stable
./scripts/canary-deploy.sh v1.0.0 50

# Monitor for 15 minutes
```

### Phase 3: Full Rollout

```bash
# If all metrics stable
./scripts/canary-deploy.sh v1.0.0 100

# Cleanup old version
kubectl delete deployment prod-corporate-intel-api-v0-9-0 -n production
```

## Incident Response

### Critical Error Detected

```bash
# 1. IMMEDIATE: Rollback
helm rollback corporate-intel -n production

# 2. Verify rollback successful
kubectl get pods -n production
curl -sf https://api.corporate-intel.com/health

# 3. Notify team
# Post in #incidents Slack channel
# Update status page

# 4. Investigate
kubectl logs -n production -l app=corporate-intel --tail=1000
kubectl get events -n production --sort-by='.lastTimestamp'

# 5. Create incident report
```

### Database Issues

```bash
# 1. Check database health
kubectl run db-check \
  --image=postgres:15 \
  --namespace=production \
  --restart=Never --rm -it \
  --command -- psql $DATABASE_URL -c "SELECT 1"

# 2. Check connections
kubectl exec -it <api-pod> -n production -- \
  psql $DATABASE_URL -c "SELECT count(*) FROM pg_stat_activity"

# 3. If needed, restart database pods
kubectl rollout restart statefulset/postgres -n production
```

### Performance Degradation

```bash
# 1. Check resource usage
kubectl top pods -n production
kubectl top nodes

# 2. Scale up if needed
kubectl scale deployment/prod-corporate-intel-api --replicas=20 -n production

# 3. Check for slow queries
kubectl exec -it postgres-0 -n production -- psql -c "
  SELECT pid, now() - query_start as duration, query
  FROM pg_stat_activity
  WHERE state = 'active'
  ORDER BY duration DESC
  LIMIT 10;
"

# 4. Clear cache if needed
kubectl exec -it redis-0 -n production -- redis-cli FLUSHDB
```

## Health Checks

### Application Health

```bash
# Basic health
curl https://api.corporate-intel.com/health

# Detailed health
curl https://api.corporate-intel.com/api/v1/health

# Check all pods
kubectl get pods -n production -o wide
kubectl describe deployment prod-corporate-intel-api -n production
```

### Database Health

```bash
# Connection count
kubectl exec -it postgres-0 -n production -- \
  psql -c "SELECT count(*) FROM pg_stat_activity;"

# Replication lag
kubectl exec -it postgres-0 -n production -- \
  psql -c "SELECT pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn) AS lag FROM pg_stat_replication;"

# Active queries
kubectl exec -it postgres-0 -n production -- \
  psql -c "SELECT * FROM pg_stat_activity WHERE state = 'active';"
```

### Cache Health

```bash
# Redis info
kubectl exec -it redis-0 -n production -- redis-cli INFO

# Hit rate
kubectl exec -it redis-0 -n production -- redis-cli INFO stats | grep hit
```

## Monitoring Dashboards

### Grafana Dashboards

1. **Application Dashboard**: https://grafana.corporate-intel.com/d/api
   - Request rates
   - Error rates
   - Latency (P50, P95, P99)
   - Throughput

2. **Database Dashboard**: https://grafana.corporate-intel.com/d/database
   - Connection pool usage
   - Query performance
   - Replication lag
   - Transaction rates

3. **Infrastructure Dashboard**: https://grafana.corporate-intel.com/d/infra
   - CPU/Memory usage
   - Network I/O
   - Disk usage
   - Pod status

4. **Business KPIs**: https://grafana.corporate-intel.com/d/business
   - Active users
   - API calls
   - Report generation
   - Data processing

### Alert Channels

- **Critical**: PagerDuty + Slack (#critical-alerts)
- **Warning**: Slack (#alerts)
- **Info**: Slack (#monitoring)

## Troubleshooting Guide

### Issue: Pods Crashing

```bash
# Check logs
kubectl logs --previous <pod-name> -n production

# Check events
kubectl describe pod <pod-name> -n production

# Check resource limits
kubectl top pod <pod-name> -n production

# Increase resources if needed
kubectl patch deployment prod-corporate-intel-api -n production -p '
{
  "spec": {
    "template": {
      "spec": {
        "containers": [{
          "name": "api",
          "resources": {
            "limits": {"memory": "4Gi", "cpu": "2000m"}
          }
        }]
      }
    }
  }
}'
```

### Issue: High Latency

```bash
# Check active connections
kubectl exec -it <api-pod> -n production -- netstat -an | grep ESTABLISHED | wc -l

# Check database query performance
kubectl exec -it postgres-0 -n production -- psql -c "
  SELECT query, mean_exec_time, calls
  FROM pg_stat_statements
  ORDER BY mean_exec_time DESC
  LIMIT 10;
"

# Check cache hit rate
kubectl exec -it redis-0 -n production -- redis-cli INFO stats | grep keyspace
```

### Issue: Out of Memory

```bash
# Identify memory-hungry pods
kubectl top pods -n production --sort-by=memory

# Check for memory leaks
kubectl exec -it <api-pod> -n production -- cat /proc/meminfo

# Restart pod
kubectl delete pod <pod-name> -n production
```

## Post-Deployment Tasks

- [ ] Update deployment log
- [ ] Notify stakeholders
- [ ] Monitor for 1 hour
- [ ] Update documentation if needed
- [ ] Create release notes
- [ ] Schedule post-mortem if issues occurred

## Emergency Contacts

- **DevOps Lead**: @devops-lead (Slack)
- **Database Admin**: @dba-oncall (PagerDuty)
- **Platform Lead**: @platform-lead (Slack/Phone)
- **On-Call Engineer**: Check PagerDuty schedule

## Additional Resources

- [Kubernetes Guide](./KUBERNETES_GUIDE.md)
- [Monitoring Setup](./MONITORING_SETUP.md)
- [Disaster Recovery](./DISASTER_RECOVERY.md)
- [Performance Testing](./PERFORMANCE_TESTING.md)
