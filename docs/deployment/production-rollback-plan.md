# Production Rollback Plan

**Version:** 2.0.0
**Last Updated:** October 17, 2025
**Environment:** Production
**Maximum Rollback Time:** 15 minutes
**Last Tested:** _________________

---

## Overview

This document provides comprehensive rollback procedures for production deployments. Use this guide when deployment issues are detected that cannot be resolved through forward fixes.

### When to Rollback

**Immediate Rollback Triggers (Critical):**
- Error rate > 5%
- P99 latency > 500ms (baseline: 32ms)
- Database connection failures
- Service unavailability > 1 minute
- Data corruption detected
- Security breach detected
- Critical functionality broken

**Planned Rollback Triggers (Major):**
- Error rate 1-5%
- P99 latency 200-500ms
- Degraded performance (>30% slower than baseline)
- Non-critical functionality broken
- User-reported critical bugs

### Rollback Decision Authority

**Immediate Rollback (no approval needed):**
- On-call engineer
- DevOps lead
- SRE team member

**Planned Rollback (requires approval):**
- Technical lead
- Product owner (for feature rollbacks)

---

## Quick Rollback Procedures

### 🚨 Emergency 5-Minute Rollback

**Use when:** Critical issues, immediate action required

```bash
#!/bin/bash
# Emergency rollback script
# Location: /scripts/emergency-rollback.sh

set -e

echo "🚨 EMERGENCY ROLLBACK INITIATED"
echo "Timestamp: $(date)"
echo "Initiated by: $USER"

# 1. Stop current containers
echo "Stopping current deployment..."
docker-compose -f docker-compose.prod.yml down

# 2. Restore previous docker-compose file
echo "Restoring previous configuration..."
cp docker-compose.prod.yml.backup docker-compose.prod.yml
cp .env.production.backup .env.production

# 3. Start previous version
echo "Starting previous version..."
docker-compose -f docker-compose.prod.yml up -d

# 4. Wait for health checks
echo "Waiting for services to be healthy..."
sleep 30

# 5. Verify health
echo "Verifying health endpoints..."
curl -f http://localhost:8000/health || echo "⚠️ Health check failed!"

# 6. Check all services
docker-compose -f docker-compose.prod.yml ps

echo "✅ EMERGENCY ROLLBACK COMPLETE"
echo "Time elapsed: $SECONDS seconds"
echo "Next steps:"
echo "1. Verify application is working"
echo "2. Check error logs"
echo "3. Notify team"
echo "4. Create incident report"
```

**Execution:**
```bash
# Run emergency rollback
cd /opt/corporate-intel
./scripts/emergency-rollback.sh

# Estimated time: 3-5 minutes
```

---

## Standard Rollback Procedures

### 1. Application Rollback (Docker Compose)

**Estimated Time:** 10 minutes
**Downtime:** 2-3 minutes

#### Step 1: Verify Rollback Target

```bash
# List available backup configurations
ls -lah /opt/corporate-intel/backups/deployments/

# Example output:
# docker-compose.prod.yml.2025-10-17-120000  <- Current deployment
# docker-compose.prod.yml.2025-10-16-180000  <- Previous stable version
# docker-compose.prod.yml.2025-10-15-150000
```

```bash
# Verify backup integrity
diff docker-compose.prod.yml /opt/corporate-intel/backups/deployments/docker-compose.prod.yml.2025-10-16-180000

# Check image availability
docker images | grep corporate-intel
```

#### Step 2: Create Pre-Rollback Snapshot

```bash
# Take snapshot of current state (for analysis)
mkdir -p /opt/corporate-intel/incident-snapshots/$(date +%Y%m%d_%H%M%S)
SNAPSHOT_DIR=/opt/corporate-intel/incident-snapshots/$(date +%Y%m%d_%H%M%S)

# Save current logs
docker-compose -f docker-compose.prod.yml logs > $SNAPSHOT_DIR/logs-before-rollback.txt

# Save current config
cp docker-compose.prod.yml $SNAPSHOT_DIR/
cp .env.production $SNAPSHOT_DIR/

# Save metrics snapshot
curl http://localhost:9090/api/v1/query?query=up > $SNAPSHOT_DIR/metrics-snapshot.json

# Document issue
echo "Rollback initiated at $(date)" > $SNAPSHOT_DIR/rollback-reason.txt
echo "Reason: [DESCRIBE ISSUE]" >> $SNAPSHOT_DIR/rollback-reason.txt
```

#### Step 3: Stop Current Deployment

```bash
# Announce maintenance (optional, if time permits)
# Update status page or send notification

# Stop all containers gracefully
docker-compose -f docker-compose.prod.yml down --timeout 30

# Verify all containers stopped
docker ps | grep corporate-intel
```

#### Step 4: Restore Previous Version

```bash
# Restore previous docker-compose configuration
cp /opt/corporate-intel/backups/deployments/docker-compose.prod.yml.2025-10-16-180000 docker-compose.prod.yml

# Restore previous environment file
cp /opt/corporate-intel/backups/deployments/.env.production.2025-10-16-180000 .env.production

# Verify restored files
md5sum docker-compose.prod.yml
md5sum .env.production
```

#### Step 5: Start Previous Version

```bash
# Pull images if needed
docker-compose -f docker-compose.prod.yml pull

# Start services
docker-compose -f docker-compose.prod.yml up -d

# Monitor startup
docker-compose -f docker-compose.prod.yml logs -f --tail=100
```

#### Step 6: Verify Rollback Success

```bash
# Wait for services to be healthy (max 2 minutes)
timeout 120 bash -c 'until curl -f http://localhost:8000/health; do sleep 5; done'

# Check all containers
docker-compose -f docker-compose.prod.yml ps

# Expected output: All services "Up" and "healthy"

# Verify health endpoints
curl -f http://localhost:8000/health
curl -f http://localhost:8000/api/v1/health

# Check application logs for errors
docker-compose -f docker-compose.prod.yml logs --tail=50 api | grep -i error
```

---

### 2. Database Rollback

**⚠️ WARNING:** Database rollbacks are complex and can result in data loss. Only perform if absolutely necessary.

#### 2.1 Migration Rollback (Preferred)

**Estimated Time:** 15-30 minutes
**Data Loss Risk:** Low (if migrations are reversible)

```bash
# Step 1: Verify current migration version
docker-compose -f docker-compose.prod.yml exec api alembic current

# Example output:
# 2a4f7b3c8d9e (head) - Add new indexes for performance

# Step 2: List migration history
docker-compose -f docker-compose.prod.yml exec api alembic history

# Step 3: Identify target migration (previous stable version)
# Example target: 1b2c3d4e5f6a

# Step 4: Create database backup BEFORE rollback
docker-compose -f docker-compose.prod.yml exec postgres pg_dump \
  -U $POSTGRES_USER -d $POSTGRES_DB -F c \
  -f /backups/pre-migration-rollback-$(date +%Y%m%d_%H%M%S).backup

# Step 5: Perform migration rollback
docker-compose -f docker-compose.prod.yml exec api alembic downgrade 1b2c3d4e5f6a

# Step 6: Verify migration rollback
docker-compose -f docker-compose.prod.yml exec api alembic current

# Step 7: Test database functionality
docker-compose -f docker-compose.prod.yml exec api python -c "
from src.core.database import get_db
from src.models.company import Company
db = next(get_db())
print(f'Company count: {db.query(Company).count()}')
"
```

#### 2.2 Full Database Restore (Last Resort)

**Estimated Time:** 30-60 minutes
**Data Loss:** All data changes since backup
**Downtime:** 30-60 minutes

```bash
# Step 1: List available backups
aws s3 ls s3://corporate-intel-backups/postgres/
# Or local backups:
ls -lah /opt/corporate-intel/backups/postgres/

# Example backups:
# corporate_intel_prod_2025-10-17_060000.backup  <- Daily backup (this morning)
# corporate_intel_prod_2025-10-16_180000.backup  <- Pre-deployment backup
# corporate_intel_prod_2025-10-16_060000.backup  <- Yesterday

# Step 2: Select backup (choose pre-deployment backup)
BACKUP_FILE="corporate_intel_prod_2025-10-16_180000.backup"

# Step 3: Download backup if from S3
aws s3 cp s3://corporate-intel-backups/postgres/$BACKUP_FILE /tmp/$BACKUP_FILE

# Step 4: Stop API to prevent connections
docker-compose -f docker-compose.prod.yml stop api

# Step 5: Drop and recreate database
docker-compose -f docker-compose.prod.yml exec postgres psql -U $POSTGRES_USER -c "
DROP DATABASE IF EXISTS ${POSTGRES_DB}_restore;
CREATE DATABASE ${POSTGRES_DB}_restore;
"

# Step 6: Restore backup to new database
docker-compose -f docker-compose.prod.yml exec -T postgres pg_restore \
  -U $POSTGRES_USER -d ${POSTGRES_DB}_restore \
  -v < /tmp/$BACKUP_FILE

# Step 7: Verify restored database
docker-compose -f docker-compose.prod.yml exec postgres psql -U $POSTGRES_USER -d ${POSTGRES_DB}_restore -c "
SELECT COUNT(*) FROM companies;
SELECT COUNT(*) FROM financial_metrics;
"

# Step 8: Swap databases (minimal downtime)
docker-compose -f docker-compose.prod.yml exec postgres psql -U $POSTGRES_USER -c "
ALTER DATABASE $POSTGRES_DB RENAME TO ${POSTGRES_DB}_old;
ALTER DATABASE ${POSTGRES_DB}_restore RENAME TO $POSTGRES_DB;
"

# Step 9: Restart API
docker-compose -f docker-compose.prod.yml start api

# Step 10: Verify application functionality
curl -f http://localhost:8000/health
curl -f http://localhost:8000/api/v1/companies?limit=5

# Step 11: Drop old database after verification (24 hours later)
# docker-compose -f docker-compose.prod.yml exec postgres psql -U $POSTGRES_USER -c "DROP DATABASE ${POSTGRES_DB}_old;"
```

---

### 3. Configuration Rollback

**Estimated Time:** 5 minutes
**Downtime:** 1-2 minutes

#### 3.1 Environment Variable Rollback

```bash
# Step 1: Backup current environment
cp .env.production .env.production.failed

# Step 2: Restore previous environment
cp /opt/corporate-intel/backups/configs/.env.production.2025-10-16-180000 .env.production

# Step 3: Restart affected services
docker-compose -f docker-compose.prod.yml restart api

# Step 4: Verify
docker-compose -f docker-compose.prod.yml logs --tail=50 api
```

#### 3.2 Nginx Configuration Rollback

```bash
# Step 1: Restore previous nginx config
cp /opt/corporate-intel/backups/configs/nginx.conf.2025-10-16-180000 /opt/corporate-intel/config/nginx.conf

# Step 2: Test configuration
docker-compose -f docker-compose.prod.yml exec nginx nginx -t

# Step 3: Reload nginx
docker-compose -f docker-compose.prod.yml exec nginx nginx -s reload

# Or restart if reload fails
docker-compose -f docker-compose.prod.yml restart nginx

# Step 4: Verify
curl -I https://api.corporate-intel.com
```

---

### 4. Cache Rollback (Redis)

**Estimated Time:** 2 minutes
**Downtime:** None (cache can be rebuilt)

```bash
# Step 1: Flush current cache (if corrupted)
docker-compose -f docker-compose.prod.yml exec redis redis-cli -a $REDIS_PASSWORD FLUSHALL

# Step 2: Verify cache is empty
docker-compose -f docker-compose.prod.yml exec redis redis-cli -a $REDIS_PASSWORD INFO keyspace

# Step 3: Restart API to rebuild cache
docker-compose -f docker-compose.prod.yml restart api

# Step 4: Monitor cache rebuilding
docker-compose -f docker-compose.prod.yml exec redis redis-cli -a $REDIS_PASSWORD INFO stats | grep keyspace_hits
```

---

### 5. Object Storage Rollback (MinIO)

**Estimated Time:** 10-30 minutes (depending on data size)
**Data Loss Risk:** Changes since backup

```bash
# Step 1: List MinIO backups
mc ls minio-backup/corporate-intel-prod-backups/

# Step 2: Verify backup integrity
mc stat minio-backup/corporate-intel-prod-backups/2025-10-16-180000/

# Step 3: Stop API to prevent writes
docker-compose -f docker-compose.prod.yml stop api

# Step 4: Rename current buckets
mc mb minio-prod/prod-corporate-documents-old
mc mirror minio-prod/prod-corporate-documents minio-prod/prod-corporate-documents-old

# Step 5: Restore from backup
mc mirror minio-backup/corporate-intel-prod-backups/2025-10-16-180000/prod-corporate-documents \
          minio-prod/prod-corporate-documents

# Step 6: Verify restore
mc ls minio-prod/prod-corporate-documents

# Step 7: Restart API
docker-compose -f docker-compose.prod.yml start api

# Step 8: Test file access
curl -f http://localhost:8000/api/v1/documents/test-document.pdf
```

---

## Rollback Validation

### Post-Rollback Checklist

After completing rollback, verify all systems are functioning:

```bash
#!/bin/bash
# Location: /scripts/post-rollback-validation.sh

echo "=== Post-Rollback Validation ==="

# 1. Service Health
echo "Checking service health..."
docker-compose -f docker-compose.prod.yml ps

# 2. Health Endpoints
echo "Testing health endpoints..."
curl -f http://localhost:8000/health || echo "❌ Health check failed"
curl -f http://localhost:8000/api/v1/health || echo "❌ API health check failed"

# 3. Database Connectivity
echo "Testing database..."
docker-compose -f docker-compose.prod.yml exec api python -c "
from src.core.database import engine
with engine.connect() as conn:
    result = conn.execute('SELECT 1')
    print('✅ Database connected')
" || echo "❌ Database connection failed"

# 4. Redis Connectivity
echo "Testing Redis..."
docker-compose -f docker-compose.prod.yml exec redis redis-cli -a $REDIS_PASSWORD ping || echo "❌ Redis failed"

# 5. MinIO Connectivity
echo "Testing MinIO..."
curl -f http://localhost:9000/minio/health/live || echo "❌ MinIO health check failed"

# 6. API Endpoints
echo "Testing API endpoints..."
curl -f http://localhost:8000/api/v1/companies?limit=1 || echo "❌ Companies endpoint failed"

# 7. Check Error Logs
echo "Checking for errors in logs..."
docker-compose -f docker-compose.prod.yml logs --tail=100 api | grep -i error | head -10

# 8. Performance Check
echo "Checking response times..."
time curl -s http://localhost:8000/api/v1/companies/AAPL

echo "=== Validation Complete ==="
```

### Success Criteria

Rollback is successful when:

- [ ] All containers running and healthy
- [ ] Health endpoints return 200 OK
- [ ] Database queries successful
- [ ] Redis cache operational
- [ ] MinIO accessible
- [ ] No critical errors in logs (last 100 lines)
- [ ] API response times < 100ms (baseline: 8.42ms mean, 32ms P99)
- [ ] Error rate < 0.1%
- [ ] Key business functionality working

---

## Partial Rollback Strategies

### Canary Rollback

If using canary deployments, rollback specific pods/instances:

```bash
# Stop canary deployment
kubectl scale deployment corporate-intel-canary --replicas=0 -n production

# Increase stable deployment
kubectl scale deployment corporate-intel-stable --replicas=10 -n production

# Verify traffic routing
kubectl get pods -n production -l app=corporate-intel
```

### Feature Flag Rollback

For feature-flag-based deployments:

```bash
# Disable feature via environment variable
docker-compose -f docker-compose.prod.yml exec api \
  python -c "
from src.core.config import settings
settings.FEATURE_NEW_ANALYTICS = False
"

# Or update environment and restart
echo "FEATURE_NEW_ANALYTICS=false" >> .env.production
docker-compose -f docker-compose.prod.yml restart api
```

---

## Communication Plan

### During Rollback

**Immediate (within 5 minutes):**
1. Post in #incidents Slack channel:
   ```
   🚨 PRODUCTION ROLLBACK IN PROGRESS
   - Time: [TIMESTAMP]
   - Reason: [BRIEF DESCRIPTION]
   - ETA: 15 minutes
   - Status page: Updated
   ```

2. Update status page:
   - Status: "Investigating issue"
   - Message: "We're experiencing technical difficulties. Our team is working on a fix."

3. Notify on-call rotation

**After Rollback (within 30 minutes):**
1. Post in #incidents:
   ```
   ✅ ROLLBACK COMPLETE
   - Services restored
   - Functionality verified
   - Monitoring ongoing
   - Incident report: [LINK]
   ```

2. Update status page:
   - Status: "Operational"
   - Message: "Systems have been restored. Monitoring for stability."

3. Email stakeholders (if user-impacting)

### Post-Rollback (within 24 hours)

1. **Create Incident Report**
   - What happened
   - Root cause
   - Impact (users affected, duration)
   - Actions taken
   - Lessons learned
   - Prevention measures

2. **Schedule Post-Mortem**
   - Within 48 hours of incident
   - Invite relevant team members
   - Document action items

3. **Update Runbooks**
   - Add learnings to procedures
   - Update rollback timing estimates
   - Document any new failure modes

---

## Rollback Testing

### Monthly Rollback Drills

Schedule monthly rollback tests to ensure procedures are current:

```bash
# Scheduled rollback drill (non-production hours)
# 1. Deploy to staging
# 2. Intentionally trigger rollback
# 3. Measure rollback time
# 4. Validate procedures
# 5. Update documentation
```

**Testing Schedule:**
- Full application rollback: Monthly
- Database migration rollback: Quarterly
- Configuration rollback: Monthly
- Cache flush: Monthly

**Test Results Log:**
```
Date: 2025-10-01
Type: Full Application Rollback
Result: SUCCESS
Time: 8 minutes 32 seconds
Issues: None
Notes: Updated health check timeout

Date: 2025-10-08
Type: Database Migration Rollback
Result: SUCCESS
Time: 12 minutes 15 seconds
Issues: None
Notes: Verified backup integrity
```

---

## Rollback Checklist

Use this quick checklist during actual rollbacks:

### Pre-Rollback
- [ ] Rollback decision approved
- [ ] Incident channel created (#incident-YYYYMMDD)
- [ ] Status page updated
- [ ] Snapshot of current state captured
- [ ] Logs exported for analysis
- [ ] Metrics snapshot taken

### During Rollback
- [ ] Current deployment stopped
- [ ] Previous version restored
- [ ] Services restarted
- [ ] Health checks passing
- [ ] Database verified (if rolled back)
- [ ] Cache verified (if flushed)
- [ ] Monitoring dashboards checked

### Post-Rollback
- [ ] All services healthy
- [ ] API endpoints responding correctly
- [ ] No critical errors in logs
- [ ] Performance metrics normal
- [ ] Team notified
- [ ] Status page updated
- [ ] Customer communication sent (if needed)
- [ ] Incident report started

### Follow-Up
- [ ] Root cause analysis completed
- [ ] Post-mortem scheduled
- [ ] Action items created
- [ ] Documentation updated
- [ ] Preventive measures implemented

---

## Appendix

### A. Rollback Scripts Location

All rollback scripts located in: `/scripts/rollback/`

- `emergency-rollback.sh` - Fast rollback (5 min)
- `full-rollback.sh` - Complete rollback with validation (15 min)
- `database-rollback.sh` - Database-specific rollback
- `config-rollback.sh` - Configuration rollback
- `post-rollback-validation.sh` - Validation script

### B. Backup Locations

**Configuration Backups:**
- `/opt/corporate-intel/backups/deployments/`
- Retention: 30 days

**Database Backups:**
- `/opt/corporate-intel/backups/postgres/`
- S3: `s3://corporate-intel-backups/postgres/`
- Retention: 30 days

**MinIO Backups:**
- `s3://corporate-intel-backups/minio/`
- Retention: 30 days

### C. Escalation Path

1. **On-Call Engineer** (0-5 min) - Execute rollback
2. **DevOps Lead** (5-15 min) - Approve rollback, provide guidance
3. **Platform Lead** (15-30 min) - Complex rollbacks, stakeholder communication
4. **CTO** (30+ min) - Critical incidents, customer communication

### D. Contact Information

**Emergency Contacts:**
- On-Call Rotation: PagerDuty schedule
- DevOps Lead: @devops-lead (Slack)
- Database Team: @dba-team (Slack)
- Platform Lead: @platform-lead (Slack/Phone)

**Communication Channels:**
- Incidents: #incidents (Slack)
- Status Updates: #production-status (Slack)
- Customer Support: support@corporate-intel.com

---

**Document Version:** 2.0.0
**Last Updated:** October 17, 2025
**Last Tested:** _________________
**Next Test Due:** _________________
**Maintained By:** DevOps Team

---

**END OF ROLLBACK PLAN**
