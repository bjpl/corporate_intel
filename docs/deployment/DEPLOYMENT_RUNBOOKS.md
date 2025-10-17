# Deployment Runbooks - Corporate Intelligence Platform

## Table of Contents

1. [Production Deployment](#production-deployment)
2. [Emergency Rollback](#emergency-rollback)
3. [SSL Certificate Renewal](#ssl-certificate-renewal)
4. [Database Backup & Recovery](#database-backup--recovery)
5. [Service Restart Procedures](#service-restart-procedures)
6. [Incident Response](#incident-response)
7. [Monitoring & Alerting](#monitoring--alerting)
8. [Common Issues & Solutions](#common-issues--solutions)

---

## Production Deployment

### Overview
Complete production deployment procedure for the Corporate Intelligence Platform.

### Prerequisites Checklist

```bash
# 1. Verify environment configuration
[ ] Production .env file configured
[ ] All API keys obtained and validated
[ ] Database credentials stored in AWS Secrets Manager
[ ] SSL certificates generated/configured
[ ] DNS records configured and propagated
[ ] Backup system tested
[ ] Monitoring alerts configured
```

### Deployment Steps

#### Step 1: Pre-Deployment Verification (15 minutes)

```bash
# Verify infrastructure
./scripts/deployment/verify-dns.sh corporate-intel.com
./scripts/generate_ssl_cert.sh --type letsencrypt --domain corporate-intel.com --email admin@corporate-intel.com

# Test database connection
PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB -c "SELECT version();"

# Verify Docker images
docker pull ghcr.io/yourusername/corporate-intel:latest
docker images | grep corporate-intel
```

#### Step 2: Database Migration (10 minutes)

```bash
# Backup current database
./scripts/backup/backup-database.sh

# Run migrations
docker-compose -f docker-compose.prod.yml run --rm api alembic upgrade head

# Verify migrations
docker-compose -f docker-compose.prod.yml run --rm api alembic current
```

#### Step 3: Deploy Services (20 minutes)

```bash
# Pull latest images
docker-compose -f docker-compose.prod.yml pull

# Start services in order
docker-compose -f docker-compose.prod.yml up -d postgres redis minio
sleep 30  # Wait for databases to initialize

# Start application services
docker-compose -f docker-compose.prod.yml up -d api nginx

# Start monitoring stack
docker-compose -f docker-compose.prod.yml up -d prometheus grafana jaeger

# Verify all services are running
docker-compose -f docker-compose.prod.yml ps
```

#### Step 4: Smoke Tests (10 minutes)

```bash
# Health check
curl -f https://corporate-intel.com/health || exit 1

# API test
curl -X GET https://corporate-intel.com/api/v1/health \
  -H "Content-Type: application/json"

# Database connectivity
docker-compose -f docker-compose.prod.yml exec api python -c "from src.database import get_db; next(get_db())"

# Run smoke test suite
pytest tests/smoke/ -v
```

#### Step 5: Post-Deployment Verification (15 minutes)

```bash
# Check logs for errors
docker-compose -f docker-compose.prod.yml logs --tail=100 api | grep ERROR

# Verify monitoring
curl http://localhost:9090/-/healthy  # Prometheus
curl http://localhost:3000/api/health # Grafana

# Test SSL
openssl s_client -connect corporate-intel.com:443 -servername corporate-intel.com < /dev/null

# Verify alerts are configured
curl http://localhost:9093/api/v1/alerts  # Alertmanager
```

### Rollback Procedure

If deployment fails, follow [Emergency Rollback](#emergency-rollback) procedure.

### Post-Deployment Tasks

```bash
# Tag release
git tag -a v1.0.0 -m "Production release v1.0.0"
git push origin v1.0.0

# Document deployment
echo "Deployed v1.0.0 on $(date)" >> /docs/deployment/DEPLOYMENT_LOG.md

# Notify team
# Send notification to Slack/email about successful deployment
```

---

## Emergency Rollback

### When to Rollback

- Critical bugs affecting user experience
- Data corruption detected
- Services failing health checks
- Security vulnerability discovered
- High error rates (>5%)

### Rollback Procedure (10 minutes)

#### Option 1: Previous Docker Image

```bash
# Stop current deployment
docker-compose -f docker-compose.prod.yml down

# Rollback to previous version
export PREVIOUS_VERSION="v0.9.5"
docker-compose -f docker-compose.prod.yml up -d \
  -e IMAGE_TAG=$PREVIOUS_VERSION

# Verify services
docker-compose -f docker-compose.prod.yml ps
curl -f https://corporate-intel.com/health
```

#### Option 2: Database Restore

```bash
# List available backups
./scripts/backup/restore-database.sh --list

# Restore previous backup
./scripts/backup/restore-database.sh --latest

# Restart services
docker-compose -f docker-compose.prod.yml restart api
```

#### Option 3: Full Infrastructure Rollback

```bash
# Checkout previous commit
git checkout $PREVIOUS_COMMIT

# Rebuild and deploy
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d

# Restore database
./scripts/backup/restore-database.sh --file backup_pre_deployment.sql.gz
```

### Post-Rollback Tasks

1. Document incident in incident log
2. Create post-mortem document
3. Schedule retrospective meeting
4. Update monitoring/alerts based on lessons learned

---

## SSL Certificate Renewal

### Automatic Renewal (Recommended)

Let's Encrypt certificates auto-renew via cron job.

```bash
# Verify renewal configuration
sudo certbot renew --dry-run

# Check cron job
sudo crontab -l | grep certbot

# Expected output:
# 0 3 * * * certbot renew --quiet --post-hook 'systemctl reload nginx'
```

### Manual Renewal

```bash
# Renew certificate
sudo certbot renew --force-renewal

# Reload nginx
docker-compose -f docker-compose.prod.yml restart nginx

# Verify new certificate
openssl s_client -connect corporate-intel.com:443 -servername corporate-intel.com < /dev/null 2>/dev/null | openssl x509 -noout -dates
```

### Certificate Expiry Monitoring

```bash
# Check days until expiry
./scripts/deployment/check-ssl-expiry.sh corporate-intel.com

# View Prometheus metric
curl http://localhost:9090/api/v1/query?query=ssl_cert_expiry_days
```

### Troubleshooting Certificate Issues

```bash
# Verify DNS is correct
dig corporate-intel.com A +short

# Test ACME challenge
curl http://corporate-intel.com/.well-known/acme-challenge/test

# Check certbot logs
sudo tail -f /var/log/letsencrypt/letsencrypt.log

# Remove and regenerate certificate
sudo certbot delete --cert-name corporate-intel.com
./scripts/deployment/setup-ssl-letsencrypt.sh -d corporate-intel.com -e admin@corporate-intel.com
```

---

## Database Backup & Recovery

### Daily Automated Backups

Backups run automatically via cron at 2 AM UTC.

```bash
# Verify backup cron job
sudo crontab -l | grep backup-database

# Expected:
# 0 2 * * * /path/to/scripts/backup/backup-database.sh >> /var/log/backup.log 2>&1
```

### Manual Backup

```bash
# Full database backup
./scripts/backup/backup-database.sh

# Backup with custom retention
RETENTION_DAYS=60 ./scripts/backup/backup-database.sh

# Backup and upload to S3
S3_BUCKET=s3://corporate-intel-backups-prod/postgres ./scripts/backup/backup-database.sh
```

### Restore from Backup

```bash
# List available backups
./scripts/backup/restore-database.sh --list

# Restore latest backup
./scripts/backup/restore-database.sh --latest

# Restore specific backup
./scripts/backup/restore-database.sh --file corporate_intel_20250116_120000.sql.gz

# Restore from S3
./scripts/backup/restore-database.sh --mode s3 --latest
```

### Testing Backup Restoration (Monthly)

```bash
# Create test environment
docker-compose -f docker-compose.test.yml up -d postgres-test

# Restore backup to test database
DB_NAME=test_restore ./scripts/backup/restore-database.sh --latest

# Verify restoration
psql -h localhost -U postgres -d test_restore -c "\dt"
psql -h localhost -U postgres -d test_restore -c "SELECT COUNT(*) FROM companies;"

# Cleanup
docker-compose -f docker-compose.test.yml down -v
```

---

## Service Restart Procedures

### Restart Individual Service

```bash
# Restart API only
docker-compose -f docker-compose.prod.yml restart api

# Restart with fresh logs
docker-compose -f docker-compose.prod.yml stop api
docker-compose -f docker-compose.prod.yml up -d api

# Follow logs
docker-compose -f docker-compose.prod.yml logs -f api
```

### Restart All Services

```bash
# Graceful restart (zero downtime)
docker-compose -f docker-compose.prod.yml up -d --force-recreate --no-deps api

# Full restart (brief downtime)
docker-compose -f docker-compose.prod.yml restart

# Hard restart (clears volumes - use with caution)
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d
```

### Restart Database (Planned Maintenance)

```bash
# 1. Put application in maintenance mode
docker-compose -f docker-compose.prod.yml scale api=0

# 2. Backup database
./scripts/backup/backup-database.sh

# 3. Restart PostgreSQL
docker-compose -f docker-compose.prod.yml restart postgres

# 4. Verify database is healthy
docker-compose -f docker-compose.prod.yml exec postgres pg_isready

# 5. Bring application back online
docker-compose -f docker-compose.prod.yml scale api=2
```

---

## Incident Response

### Severity Levels

- **P0 (Critical)**: Complete outage, data loss, security breach
- **P1 (High)**: Major feature unavailable, significant performance degradation
- **P2 (Medium)**: Minor feature issue, some users affected
- **P3 (Low)**: Cosmetic issue, minimal impact

### P0 Incident Response

#### Immediate Actions (0-5 minutes)

```bash
# 1. Verify incident
curl -f https://corporate-intel.com/health

# 2. Check service status
docker-compose -f docker-compose.prod.yml ps

# 3. Check logs
docker-compose -f docker-compose.prod.yml logs --tail=200 api | grep ERROR

# 4. Notify team
# Send alert to #incidents Slack channel
# Page on-call engineer via PagerDuty
```

#### Investigation (5-15 minutes)

```bash
# Check system resources
docker stats

# Check database
docker-compose -f docker-compose.prod.yml exec postgres psql -U postgres -c "SELECT * FROM pg_stat_activity;"

# Check external dependencies
curl https://api.alphavantage.co/health
curl https://www.sec.gov/cgi-bin/browse-edgar
```

#### Resolution (15-30 minutes)

```bash
# Option 1: Restart affected service
docker-compose -f docker-compose.prod.yml restart api

# Option 2: Rollback deployment
git checkout $PREVIOUS_COMMIT
docker-compose -f docker-compose.prod.yml up -d --build

# Option 3: Restore from backup
./scripts/backup/restore-database.sh --latest
```

#### Post-Incident (24-48 hours)

1. Create incident report
2. Schedule post-mortem meeting
3. Document lessons learned
4. Update runbooks
5. Implement preventive measures

---

## Monitoring & Alerting

### Key Metrics to Monitor

```bash
# API Health
curl http://localhost:9090/api/v1/query?query=up{job="corporate-intel-api"}

# Error Rate
curl http://localhost:9090/api/v1/query?query=rate(http_requests_total{status=~"5.."}[5m])

# Response Time
curl http://localhost:9090/api/v1/query?query=histogram_quantile(0.95,rate(http_request_duration_seconds_bucket[5m]))

# Database Connections
curl http://localhost:9090/api/v1/query?query=pg_stat_database_numbackends

# Memory Usage
curl http://localhost:9090/api/v1/query?query=container_memory_usage_bytes{name="corporate-intel-api"}
```

### Access Dashboards

- **Grafana**: https://corporate-intel.com/grafana
- **Prometheus**: http://localhost:9090 (internal only)
- **Jaeger**: http://localhost:16686 (internal only)
- **Alertmanager**: http://localhost:9093 (internal only)

### Silence Alerts (Planned Maintenance)

```bash
# Silence all alerts for 2 hours
curl -X POST http://localhost:9093/api/v1/silences \
  -H "Content-Type: application/json" \
  -d '{
    "matchers": [{"name": "alertname", "value": ".*", "isRegex": true}],
    "startsAt": "'$(date -u +%Y-%m-%dT%H:%M:%S.000Z)'",
    "endsAt": "'$(date -u -d '+2 hours' +%Y-%m-%dT%H:%M:%S.000Z)'",
    "createdBy": "admin",
    "comment": "Planned maintenance window"
  }'
```

---

## Common Issues & Solutions

### Issue: API Not Responding

**Symptoms**: 502/503 errors, timeouts

**Diagnosis**:
```bash
docker-compose -f docker-compose.prod.yml logs api --tail=100
docker-compose -f docker-compose.prod.yml ps api
```

**Solution**:
```bash
# Restart API
docker-compose -f docker-compose.prod.yml restart api

# If persists, check resource limits
docker stats
```

### Issue: Database Connection Pool Exhausted

**Symptoms**: "too many connections" errors

**Diagnosis**:
```bash
docker-compose -f docker-compose.prod.yml exec postgres psql -U postgres -c "SELECT count(*) FROM pg_stat_activity;"
```

**Solution**:
```bash
# Terminate idle connections
docker-compose -f docker-compose.prod.yml exec postgres psql -U postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle' AND state_change < now() - interval '10 minutes';"

# Restart API to reset connection pool
docker-compose -f docker-compose.prod.yml restart api
```

### Issue: High Memory Usage

**Symptoms**: OOM kills, slow performance

**Diagnosis**:
```bash
docker stats
free -h
```

**Solution**:
```bash
# Clear cache
docker-compose -f docker-compose.prod.yml exec redis redis-cli FLUSHDB

# Restart high-memory service
docker-compose -f docker-compose.prod.yml restart api

# Increase memory limits in docker-compose.prod.yml
```

### Issue: SSL Certificate Expired

**Symptoms**: Certificate warnings in browser

**Diagnosis**:
```bash
openssl s_client -connect corporate-intel.com:443 -servername corporate-intel.com < /dev/null 2>/dev/null | openssl x509 -noout -dates
```

**Solution**:
```bash
# Force renewal
sudo certbot renew --force-renewal

# Reload nginx
docker-compose -f docker-compose.prod.yml restart nginx
```

### Issue: Disk Space Full

**Symptoms**: Write failures, crashes

**Diagnosis**:
```bash
df -h
du -sh /var/lib/docker/*
```

**Solution**:
```bash
# Clean up old Docker images
docker system prune -a --volumes

# Remove old logs
find /var/log -name "*.log" -mtime +30 -delete

# Clean old backups
find /backups/postgres -name "*.sql.gz" -mtime +30 -delete
```

---

## Emergency Contacts

- **On-Call Engineer**: +1-XXX-XXX-XXXX
- **DevOps Team**: devops@corporate-intel.com
- **Database Admin**: dba@corporate-intel.com
- **Security Team**: security@corporate-intel.com
- **PagerDuty**: https://corporate-intel.pagerduty.com

---

## Maintenance Windows

- **Scheduled Maintenance**: Sundays 2:00 AM - 4:00 AM UTC
- **Emergency Maintenance**: As needed with 1-hour notice
- **Backup Schedule**: Daily at 2:00 AM UTC

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2025-01-16 | DevOps Team | Initial release |

---

**Last Updated**: 2025-01-16
**Next Review**: 2025-04-16
