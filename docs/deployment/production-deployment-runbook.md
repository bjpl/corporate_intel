# Production Deployment Runbook

**Version:** 2.0.0
**Last Updated:** October 17, 2025
**Environment:** Production
**Total Deployment Time:** 60-90 minutes
**Performance Baseline:** 9.2/10 (P99: 32ms, Success: 100%)
**Security Score:** 9.2/10 (0 Critical, 0 High vulnerabilities)

---

## Quick Reference

| Phase | Duration | Key Tasks | Rollback Point |
|-------|----------|-----------|----------------|
| Pre-Deployment | 20 min | Backups, validation, approvals | N/A |
| Deployment | 30-40 min | Stop services, deploy, migrate | Before migration |
| Validation | 20 min | Smoke tests, performance checks | After deployment |
| Monitoring | 1 hour | Monitor stability, resolve issues | After validation |

**Critical Contacts:**
- On-Call: Check PagerDuty schedule
- DevOps Lead: @devops-lead
- Platform Lead: @platform-lead
- Emergency: See "Emergency Contacts" section

---

## Timeline Overview

```
T-24h:  Deployment planning and review
T-1h:   Pre-deployment checks
T-0:    Deployment begins
T+10m:  Smoke tests start
T+30m:  Performance validation
T+1h:   Deployment complete (if successful)
T+24h:  Post-deployment review
```

---

## Phase 1: Pre-Deployment (T-1h to T-0)

**Duration:** 20-30 minutes
**Checklist:** `/docs/deployment/production-deployment-checklist.md`

### 1.1 Communication (T-60m)

```bash
# Timeline: T-60 minutes (1 hour before deployment)

# 1. Post deployment announcement
# Slack: #engineering, #operations, #product
```

**Message Template:**
```
🚀 PRODUCTION DEPLOYMENT SCHEDULED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📅 Date: [DATE]
🕐 Time: [START_TIME] - [END_TIME] UTC
⏱️ Duration: ~60-90 minutes
📦 Version: v[VERSION]

Deployment Team:
• Lead: @[LEAD_NAME]
• DevOps: @[DEVOPS_NAME]
• Database: @[DBA_NAME]
• On-Call: @[ONCALL_NAME]

Rollback Plan: Ready ✅
Performance Baseline: 9.2/10 ✅
Security Validation: PASSED ✅

Deployment Channel: #deployment-[DATE]
Status Page: https://status.corporate-intel.com

🔗 Runbook: /docs/deployment/production-deployment-runbook.md
🔗 Rollback Plan: /docs/deployment/production-rollback-plan.md
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

```bash
# 2. Create dedicated deployment channel
# Create Slack channel: #deployment-20251017

# 3. Update status page (if applicable)
# Status: Scheduled Maintenance
# Message: "Scheduled deployment in progress. Brief downtime expected."
```

**Sign-off:** Communication sent [ ] Yes [ ] No

---

### 1.2 Pre-Deployment Verification (T-30m)

```bash
# Timeline: T-30 minutes
# Location: /opt/corporate-intel

echo "=== PRE-DEPLOYMENT VERIFICATION ==="
echo "Timestamp: $(date)"

# 1. Verify all checklist items complete
# Reference: /docs/deployment/production-deployment-checklist.md

# 2. Check current system status
docker-compose -f docker-compose.prod.yml ps
docker-compose -f docker-compose.prod.yml exec postgres pg_isready
docker-compose -f docker-compose.prod.yml exec redis redis-cli -a $REDIS_PASSWORD ping

# 3. Capture pre-deployment metrics
curl -s http://localhost:9090/api/v1/query?query=up > /tmp/pre-deployment-metrics.json
docker-compose -f docker-compose.prod.yml logs --tail=100 > /tmp/pre-deployment-logs.txt

# 4. Verify deployment artifacts
ls -la docker-compose.prod.yml
ls -la .env.production
docker images | grep corporate-intel

# 5. Test rollback procedure (dry-run)
echo "Rollback artifacts verified:"
ls -la /opt/corporate-intel/backups/deployments/ | tail -5
```

**Checklist:**
- [ ] All containers healthy
- [ ] No critical alerts firing
- [ ] Deployment artifacts present
- [ ] Rollback artifacts verified
- [ ] Team ready and on standby

**Sign-off:** Pre-deployment checks passed [ ] Yes [ ] No

---

### 1.3 Create Backups (T-20m)

```bash
# Timeline: T-20 minutes
# CRITICAL: Do not skip this step!

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/corporate-intel/backups/deployments"

echo "=== CREATING PRE-DEPLOYMENT BACKUPS ==="
echo "Timestamp: $TIMESTAMP"

# 1. Backup current configuration
mkdir -p $BACKUP_DIR
cp docker-compose.prod.yml $BACKUP_DIR/docker-compose.prod.yml.$TIMESTAMP
cp .env.production $BACKUP_DIR/.env.production.$TIMESTAMP
cp config/nginx.conf $BACKUP_DIR/nginx.conf.$TIMESTAMP

echo "✅ Configuration backed up"

# 2. Backup database
echo "Creating database backup..."
docker-compose -f docker-compose.prod.yml exec postgres pg_dump \
  -U $POSTGRES_USER -d $POSTGRES_DB -F c \
  -f /backups/postgres/corporate_intel_prod_${TIMESTAMP}.backup

# Verify backup size (should be >1MB for populated database)
BACKUP_SIZE=$(du -h /opt/corporate-intel/backups/postgres/corporate_intel_prod_${TIMESTAMP}.backup | cut -f1)
echo "Database backup size: $BACKUP_SIZE"

# Upload to S3 (if configured)
aws s3 cp /opt/corporate-intel/backups/postgres/corporate_intel_prod_${TIMESTAMP}.backup \
  s3://corporate-intel-backups/postgres/ || echo "⚠️ S3 upload skipped"

echo "✅ Database backed up"

# 3. Backup MinIO data (optional, for critical data)
docker-compose -f docker-compose.prod.yml exec minio \
  mc mirror local/prod-corporate-documents /backups/minio/documents_${TIMESTAMP}/ || echo "⚠️ MinIO backup skipped"

echo "✅ Object storage backed up"

# 4. Export current metrics
curl -s http://localhost:9090/api/v1/query?query=up > $BACKUP_DIR/metrics_${TIMESTAMP}.json

echo "✅ Metrics exported"

# 5. Verify backups
echo ""
echo "Backup verification:"
ls -lh $BACKUP_DIR/ | tail -5
ls -lh /opt/corporate-intel/backups/postgres/ | tail -5

echo ""
echo "=== BACKUPS COMPLETE ==="
```

**Estimated Time:** 5-10 minutes

**Checklist:**
- [ ] Configuration files backed up
- [ ] Database backup created and verified
- [ ] Backup size reasonable (>1MB)
- [ ] Optional: Backups uploaded to S3
- [ ] Backup timestamp recorded: _________________

**Sign-off:** Backups complete [ ] Yes [ ] No

---

### 1.4 Final Go/No-Go Decision (T-10m)

```bash
# Timeline: T-10 minutes
```

**Go/No-Go Criteria:**

| Criterion | Status | Approver |
|-----------|--------|----------|
| All pre-deployment checks passed | [ ] Go [ ] No-Go | __________ |
| Backups verified | [ ] Go [ ] No-Go | __________ |
| No critical production issues | [ ] Go [ ] No-Go | __________ |
| Team ready | [ ] Go [ ] No-Go | __________ |
| Rollback plan ready | [ ] Go [ ] No-Go | __________ |

**Final Decision:**
- [ ] **GO** - Proceed with deployment
- [ ] **NO-GO** - Postpone deployment

**Reason for No-Go (if applicable):** _______________________________

**Sign-off:**
- Technical Lead: __________ Time: __________
- DevOps Lead: __________ Time: __________

---

## Phase 2: Deployment (T-0 to T+30m)

**Duration:** 30-40 minutes
**Downtime Window:** 5-10 minutes (during service restart)

### 2.1 Begin Deployment (T-0)

```bash
# Timeline: T-0 (deployment start)
# MARK THIS TIME: __________

echo "=== DEPLOYMENT STARTED ==="
echo "Start time: $(date)"
echo "Version: v1.0.0"
echo "Deployer: $USER"

# Post in Slack
# Channel: #deployment-20251017
# Message: "🚀 Deployment started at $(date)"
```

**Announcement:**
```
🚀 DEPLOYMENT IN PROGRESS
━━━━━━━━━━━━━━━━━━━━━
Started: [TIMESTAMP]
Status: Phase 2 - Deployment
ETA: 30-40 minutes

Next update in 10 minutes
━━━━━━━━━━━━━━━━━━━━━
```

---

### 2.2 Stop Current Services (T+2m)

```bash
# Timeline: T+2 minutes
# DOWNTIME BEGINS HERE

echo "=== STOPPING CURRENT SERVICES ==="

# 1. Drain connections gracefully (if load balancer configured)
# Mark instance as unhealthy in load balancer
# Wait 30 seconds for active connections to complete
sleep 30

# 2. Stop containers gracefully (30-second timeout)
docker-compose -f docker-compose.prod.yml down --timeout 30

# 3. Verify all containers stopped
docker ps | grep corporate-intel

# Expected output: No containers running

echo "✅ Services stopped"
echo "Downtime started: $(date)"
```

**Estimated Time:** 2-3 minutes

**Checklist:**
- [ ] Containers stopped gracefully
- [ ] No zombie processes
- [ ] Ports released (verify with `netstat` or `lsof`)

---

### 2.3 Deploy New Version (T+5m)

```bash
# Timeline: T+5 minutes

echo "=== DEPLOYING NEW VERSION ==="

# 1. Pull new Docker images (if from registry)
docker-compose -f docker-compose.prod.yml pull

# Or load from local tar (if offline deployment)
# docker load -i /tmp/corporate-intel-v1.0.0.tar

# 2. Verify new image
docker images | grep corporate-intel
# Expected: corporate-intel:v1.0.0

# 3. Update configuration (if needed)
# Already prepared in .env.production and docker-compose.prod.yml

# 4. Start services (no migrations yet)
echo "Starting services..."
docker-compose -f docker-compose.prod.yml up -d postgres redis minio

# Wait for database to be ready
echo "Waiting for database..."
timeout 120 bash -c 'until docker-compose -f docker-compose.prod.yml exec postgres pg_isready -U $POSTGRES_USER -d $POSTGRES_DB; do sleep 5; done'

echo "✅ Infrastructure services started"
```

**Estimated Time:** 5-7 minutes

---

### 2.4 Run Database Migrations (T+12m)

```bash
# Timeline: T+12 minutes
# CRITICAL STEP: Migrations can be rolled back if issues occur

echo "=== RUNNING DATABASE MIGRATIONS ==="

# 1. Check current migration version
docker-compose -f docker-compose.prod.yml run --rm api alembic current
echo "Current version: $(docker-compose -f docker-compose.prod.yml run --rm api alembic current)"

# 2. Preview migrations
docker-compose -f docker-compose.prod.yml run --rm api alembic upgrade --sql head > /tmp/migration-preview.sql
echo "Migration preview saved to /tmp/migration-preview.sql"

# 3. Create pre-migration snapshot
docker-compose -f docker-compose.prod.yml exec postgres pg_dump \
  -U $POSTGRES_USER -d $POSTGRES_DB -F c \
  -f /backups/postgres/pre-migration-$(date +%Y%m%d_%H%M%S).backup

# 4. Run migrations
echo "Applying migrations..."
docker-compose -f docker-compose.prod.yml run --rm api alembic upgrade head

MIGRATION_EXIT_CODE=$?

if [ $MIGRATION_EXIT_CODE -eq 0 ]; then
    echo "✅ Migrations completed successfully"

    # Verify new version
    NEW_VERSION=$(docker-compose -f docker-compose.prod.yml run --rm api alembic current)
    echo "New migration version: $NEW_VERSION"

    # Verify table structure
    docker-compose -f docker-compose.prod.yml exec postgres psql -U $POSTGRES_USER -d $POSTGRES_DB -c "\dt"

else
    echo "❌ MIGRATION FAILED!"
    echo "Exit code: $MIGRATION_EXIT_CODE"
    echo ""
    echo "🚨 ROLLBACK REQUIRED"
    echo "1. Run migration rollback: alembic downgrade -1"
    echo "2. Or restore database from backup"
    echo "3. Execute rollback plan: /docs/deployment/production-rollback-plan.md"

    # DO NOT START API - halt deployment
    exit 1
fi

echo "=== MIGRATIONS COMPLETE ==="
```

**Estimated Time:** 5-10 minutes (depends on migration complexity)

**Checklist:**
- [ ] Current migration version recorded
- [ ] Migration preview reviewed
- [ ] Pre-migration snapshot created
- [ ] Migrations applied successfully
- [ ] New migration version verified
- [ ] Table structure verified

**ROLLBACK POINT:** If migrations fail, restore from pre-migration backup before proceeding.

---

### 2.5 Start Application Services (T+22m)

```bash
# Timeline: T+22 minutes

echo "=== STARTING APPLICATION SERVICES ==="

# 1. Start API and supporting services
docker-compose -f docker-compose.prod.yml up -d

# 2. Monitor startup logs
docker-compose -f docker-compose.prod.yml logs -f --tail=100 api &
LOG_PID=$!

# 3. Wait for health checks (max 2 minutes)
echo "Waiting for services to be healthy..."
timeout 120 bash -c 'until curl -f http://localhost:8000/health; do sleep 5; done'

HEALTH_CHECK_STATUS=$?

# Stop log monitoring
kill $LOG_PID 2>/dev/null

if [ $HEALTH_CHECK_STATUS -eq 0 ]; then
    echo "✅ Application started successfully"
else
    echo "❌ APPLICATION FAILED TO START"
    echo "Health check timeout"
    echo ""
    echo "🚨 IMMEDIATE ROLLBACK REQUIRED"
    echo "Execute: ./scripts/emergency-rollback.sh"
    exit 1
fi

# 4. Verify all containers
docker-compose -f docker-compose.prod.yml ps

# Expected: All services "Up" and "healthy"

echo "=== APPLICATION SERVICES STARTED ==="
echo "Downtime ended: $(date)"
```

**Estimated Time:** 3-5 minutes

**DOWNTIME ENDS HERE** (Total downtime: ~5-10 minutes)

**Checklist:**
- [ ] All containers started
- [ ] Health checks passing
- [ ] No critical errors in logs
- [ ] Services responding to requests

---

### 2.6 Warm Up Cache (T+27m)

```bash
# Timeline: T+27 minutes
# Optional but recommended for better initial performance

echo "=== WARMING UP CACHE ==="

# Flush any stale cache from previous version
docker-compose -f docker-compose.prod.yml exec redis redis-cli -a $REDIS_PASSWORD FLUSHDB

# Make requests to warm up cache
WARMUP_ENDPOINTS=(
    "/api/v1/companies?limit=100"
    "/api/v1/companies/AAPL"
    "/api/v1/companies/GOOGL"
    "/api/v1/companies/MSFT"
    "/api/v1/financial/metrics?ticker=AAPL"
)

for endpoint in "${WARMUP_ENDPOINTS[@]}"; do
    echo "Warming up: $endpoint"
    curl -s "http://localhost:8000$endpoint" > /dev/null
done

# Verify cache has entries
CACHE_KEYS=$(docker-compose -f docker-compose.prod.yml exec redis redis-cli -a $REDIS_PASSWORD DBSIZE)
echo "Cache keys loaded: $CACHE_KEYS"

echo "✅ Cache warmed up"
```

**Estimated Time:** 1-2 minutes

---

### 2.7 Deployment Complete (T+30m)

```bash
# Timeline: T+30 minutes

echo "=== DEPLOYMENT PHASE COMPLETE ==="
echo "Deployment completed at: $(date)"
echo ""
echo "Next: Phase 3 - Validation (20 minutes)"
echo "Status: Proceeding to smoke tests"
```

**Announcement:**
```
✅ DEPLOYMENT COMPLETE
━━━━━━━━━━━━━━━━━━━━━
Completed: [TIMESTAMP]
Duration: [XX] minutes
Downtime: ~[XX] minutes

Status: Validation in progress
Next update in 10 minutes
━━━━━━━━━━━━━━━━━━━━━
```

---

## Phase 3: Validation (T+30m to T+50m)

**Duration:** 20-30 minutes
**Reference:** `/docs/deployment/production-smoke-tests.md`

### 3.1 Run Smoke Tests (T+30m)

```bash
# Timeline: T+30 minutes
# Location: /scripts/smoke-tests/

echo "=== RUNNING SMOKE TESTS ==="

# Execute automated smoke tests
./production-smoke-tests.sh https://api.corporate-intel.com

SMOKE_TEST_EXIT_CODE=$?

if [ $SMOKE_TEST_EXIT_CODE -eq 0 ]; then
    echo "✅ SMOKE TESTS PASSED"
else
    echo "❌ SMOKE TESTS FAILED"
    echo "Exit code: $SMOKE_TEST_EXIT_CODE"
    echo ""
    echo "⚠️ REVIEW REQUIRED"
    echo "1. Review smoke test results"
    echo "2. Investigate failures"
    echo "3. Determine if rollback needed"

    # DO NOT auto-rollback - require manual decision
fi

# Save results
cp /tmp/smoke-test-results-*.txt /opt/corporate-intel/deployment-logs/
```

**Estimated Time:** 5-7 minutes

**Critical Tests (must pass):**
- [ ] Health endpoints responding
- [ ] Database connectivity verified
- [ ] Cache operational
- [ ] API endpoints returning data
- [ ] No critical errors in logs

**See full smoke test checklist:** `/docs/deployment/production-smoke-tests.md`

---

### 3.2 Performance Validation (T+37m)

```bash
# Timeline: T+37 minutes

echo "=== PERFORMANCE VALIDATION ==="

# Performance baselines (from /docs/PLAN_A_DAY1_PERFORMANCE_BASELINE.md):
# - P99 latency: 32.14ms (target: <100ms)
# - Mean latency: 8.42ms (target: <50ms)
# - Throughput: 27.3 QPS (target: >20 QPS)
# - Success rate: 100% (target: >99.9%)

# 1. Response time check
echo "Testing response times..."
for i in {1..20}; do
    curl -s -o /dev/null -w "%{time_total}\n" https://api.corporate-intel.com/health
done | awk '{s+=$1; count++} END {print "Health endpoint avg:", s/count*1000, "ms (target: <10ms)"}'

for i in {1..20}; do
    curl -s -o /dev/null -w "%{time_total}\n" https://api.corporate-intel.com/api/v1/companies?limit=5
done | awk '{s+=$1; count++} END {print "Companies endpoint avg:", s/count*1000, "ms (target: <50ms)"}'

# 2. Concurrent load test (10 users)
echo "Testing concurrent load (10 users)..."
seq 1 10 | xargs -n1 -P10 -I{} curl -s -o /dev/null -w "%{time_total}\n" https://api.corporate-intel.com/api/v1/companies/AAPL | \
  awk '{s+=$1; if($1>max) max=$1; count++} END {print "Avg:", s/count*1000, "ms | Max:", max*1000, "ms (target max: <100ms)"}'

# 3. Error rate check
ERROR_COUNT=$(docker-compose -f docker-compose.prod.yml logs --tail=1000 api | grep -i error | wc -l)
echo "Error count in last 1000 log lines: $ERROR_COUNT (target: 0)"

# 4. Database performance
DB_RESPONSE=$(docker-compose -f docker-compose.prod.yml exec postgres psql -U $POSTGRES_USER -d $POSTGRES_DB -c "
  EXPLAIN ANALYZE SELECT * FROM companies WHERE ticker = 'AAPL';
" | grep "Execution Time")
echo "Database query time: $DB_RESPONSE (target: <5ms)"

# 5. Cache hit ratio
CACHE_HITS=$(docker-compose -f docker-compose.prod.yml exec redis redis-cli -a $REDIS_PASSWORD INFO stats | grep keyspace_hits | cut -d: -f2)
CACHE_MISSES=$(docker-compose -f docker-compose.prod.yml exec redis redis-cli -a $REDIS_PASSWORD INFO stats | grep keyspace_misses | cut -d: -f2)
if [ "$CACHE_HITS" -gt 0 ]; then
    CACHE_HIT_RATIO=$(echo "scale=2; $CACHE_HITS * 100 / ($CACHE_HITS + $CACHE_MISSES)" | bc)
    echo "Cache hit ratio: $CACHE_HIT_RATIO% (target: >95%, baseline: 99.2%)"
fi

echo "=== PERFORMANCE VALIDATION COMPLETE ==="
```

**Estimated Time:** 5-7 minutes

**Performance Criteria (from baseline):**
- [ ] Health endpoint: <10ms average
- [ ] Companies endpoint: <50ms average (baseline: 6.5ms)
- [ ] Concurrent load: <100ms max (baseline P99: 32ms)
- [ ] Error count: 0
- [ ] Database queries: <5ms (baseline: 2.15ms)
- [ ] Cache hit ratio: >95% (baseline: 99.2%)

---

### 3.3 Security Validation (T+44m)

```bash
# Timeline: T+44 minutes

echo "=== SECURITY VALIDATION ==="

# Security baseline: 9.2/10 (0 Critical, 0 High vulnerabilities)

# 1. HTTPS enforcement
HTTP_REDIRECT=$(curl -s -o /dev/null -w "%{http_code}" http://api.corporate-intel.com/health)
if [ "$HTTP_REDIRECT" = "301" ] || [ "$HTTP_REDIRECT" = "308" ]; then
    echo "✅ HTTPS redirect working (status: $HTTP_REDIRECT)"
else
    echo "⚠️ HTTPS redirect unexpected status: $HTTP_REDIRECT"
fi

# 2. Security headers
echo "Checking security headers..."
HEADERS=$(curl -I https://api.corporate-intel.com/health)

echo "$HEADERS" | grep -i "strict-transport-security" && echo "✅ HSTS header present" || echo "❌ HSTS missing"
echo "$HEADERS" | grep -i "x-frame-options" && echo "✅ X-Frame-Options present" || echo "⚠️ X-Frame-Options missing"
echo "$HEADERS" | grep -i "x-content-type-options" && echo "✅ X-Content-Type-Options present" || echo "⚠️ X-Content-Type-Options missing"
echo "$HEADERS" | grep -i "content-security-policy" && echo "✅ CSP present" || echo "⚠️ CSP missing"

# 3. Authentication check
AUTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://api.corporate-intel.com/api/v1/admin/users)
if [ "$AUTH_STATUS" = "401" ] || [ "$AUTH_STATUS" = "403" ]; then
    echo "✅ Authentication required (status: $AUTH_STATUS)"
else
    echo "⚠️ Authentication check returned: $AUTH_STATUS"
fi

# 4. SSL grade (if time permits)
echo "For SSL grade check, visit: https://www.ssllabs.com/ssltest/analyze.html?d=api.corporate-intel.com"
echo "Target: Grade A or A+"

echo "=== SECURITY VALIDATION COMPLETE ==="
```

**Estimated Time:** 2-3 minutes

**Security Criteria:**
- [ ] HTTPS enforced
- [ ] Security headers present (HSTS, X-Frame-Options, CSP, etc.)
- [ ] Authentication working
- [ ] SSL grade A or A+ (manual check)

---

### 3.4 Integration Testing (T+47m)

```bash
# Timeline: T+47 minutes

echo "=== INTEGRATION TESTING ==="

# 1. External API connectivity (if applicable)
# Test Alpha Vantage
if [ ! -z "$ALPHA_VANTAGE_API_KEY" ]; then
    ALPHA_TEST=$(curl -s "https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol=IBM&interval=5min&apikey=$ALPHA_VANTAGE_API_KEY" | jq -r '.Note // .Information // "OK"')
    echo "Alpha Vantage: $ALPHA_TEST"
fi

# 2. Database write test
echo "Testing database write..."
docker-compose -f docker-compose.prod.yml exec postgres psql -U $POSTGRES_USER -d $POSTGRES_DB -c "
  INSERT INTO system_health_checks (check_time, status, message)
  VALUES (NOW(), 'deployment_validation', 'Post-deployment check');
" && echo "✅ Database write successful"

# 3. MinIO connectivity
MINIO_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:9000/minio/health/live)
if [ "$MINIO_HEALTH" = "200" ]; then
    echo "✅ MinIO healthy"
else
    echo "⚠️ MinIO health check: $MINIO_HEALTH"
fi

# 4. Monitoring stack
PROMETHEUS_UP=$(curl -s http://localhost:9090/api/v1/query?query=up | jq -r '.data.result[0].value[1]')
echo "Prometheus metrics: $PROMETHEUS_UP (expected: 1)"

GRAFANA_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/api/health)
echo "Grafana health: $GRAFANA_HEALTH (expected: 200)"

echo "=== INTEGRATION TESTING COMPLETE ==="
```

**Estimated Time:** 3-5 minutes

---

### 3.5 Validation Summary (T+50m)

```bash
# Timeline: T+50 minutes

echo "======================================"
echo "VALIDATION SUMMARY"
echo "======================================"
echo "Timestamp: $(date)"
echo ""
echo "Smoke Tests:        [PASSED/FAILED]"
echo "Performance:        [PASSED/FAILED]"
echo "Security:           [PASSED/FAILED]"
echo "Integration:        [PASSED/FAILED]"
echo ""
echo "Overall Status:     [PASSED/FAILED/WARNINGS]"
echo "======================================"

# If all tests passed:
if [ "$OVERALL_STATUS" = "PASSED" ]; then
    echo "✅ VALIDATION COMPLETE - DEPLOYMENT SUCCESSFUL"
    echo "Proceeding to monitoring phase"
else
    echo "⚠️ VALIDATION ISSUES DETECTED"
    echo "Review results and determine next steps:"
    echo "1. Investigate issues"
    echo "2. Apply hotfix if minor"
    echo "3. Rollback if critical"
fi
```

**Decision Point:**
- **All tests passed:** Proceed to monitoring phase
- **Minor issues:** Investigate and apply hotfix
- **Critical issues:** Execute rollback plan

---

## Phase 4: Monitoring (T+50m to T+110m)

**Duration:** 60 minutes
**Intensity:** High monitoring for first hour, then normal operations

### 4.1 Active Monitoring (T+50m to T+110m)

```bash
# Timeline: T+50 minutes (start 1-hour monitoring period)

echo "=== ACTIVE MONITORING PHASE ==="
echo "Duration: 60 minutes"
echo "Start: $(date)"
echo ""

# Monitor these metrics continuously:
# 1. Error rate (target: <0.1%)
# 2. Response times (target: P99 <100ms, baseline: 32ms)
# 3. Resource utilization (CPU <70%, Memory <80%)
# 4. Database performance (cache hit >95%)
# 5. Application logs (no critical errors)

# Set up monitoring dashboard
echo "Monitoring dashboards:"
echo "- Grafana: http://localhost:3000"
echo "- Prometheus: http://localhost:9090"
echo "- Logs: docker-compose -f docker-compose.prod.yml logs -f api"
echo ""

# Automated monitoring script
./scripts/monitoring/post-deployment-monitor.sh 60 &
MONITOR_PID=$!

echo "Automated monitoring started (PID: $MONITOR_PID)"
echo "This will run for 60 minutes"
echo ""
echo "Manual checks to perform:"
echo "[ ] T+5m:  Quick health check"
echo "[ ] T+15m: Performance review"
echo "[ ] T+30m: Error log review"
echo "[ ] T+45m: Resource utilization check"
echo "[ ] T+60m: Final validation"
```

**Monitoring Checklist:**

| Time | Check | Expected | Actual | Status |
|------|-------|----------|--------|--------|
| T+55m (5 min) | Health endpoints | 200 OK | _____ | [ ] ✅ [ ] ⚠️ |
| T+55m | Error rate | <0.1% | _____% | [ ] ✅ [ ] ⚠️ |
| T+55m | Response time | <100ms | _____ms | [ ] ✅ [ ] ⚠️ |
| T+65m (15 min) | CPU usage | <70% | _____% | [ ] ✅ [ ] ⚠️ |
| T+65m | Memory usage | <80% | _____% | [ ] ✅ [ ] ⚠️ |
| T+65m | Database pool | Healthy | _____ | [ ] ✅ [ ] ⚠️ |
| T+80m (30 min) | Error logs | 0 critical | _____ | [ ] ✅ [ ] ⚠️ |
| T+80m | Cache hit ratio | >95% | _____% | [ ] ✅ [ ] ⚠️ |
| T+95m (45 min) | Disk usage | <70% | _____% | [ ] ✅ [ ] ⚠️ |
| T+95m | Network I/O | Normal | _____ | [ ] ✅ [ ] ⚠️ |
| T+110m (60 min) | Overall health | Stable | _____ | [ ] ✅ [ ] ⚠️ |

---

### 4.2 Monitoring Commands

```bash
# Quick health check
curl -f https://api.corporate-intel.com/health

# Check error rate
docker-compose -f docker-compose.prod.yml logs --since 5m api | grep -i error | wc -l

# Check response times
for i in {1..10}; do
    curl -s -o /dev/null -w "%{time_total}\n" https://api.corporate-intel.com/api/v1/companies?limit=5
done | awk '{s+=$1; count++} END {print "Avg:", s/count*1000, "ms"}'

# Check resource usage
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemPerc}}"

# Check database connections
docker-compose -f docker-compose.prod.yml exec postgres psql -U $POSTGRES_USER -d $POSTGRES_DB -c "
  SELECT count(*) FROM pg_stat_activity WHERE datname = '$POSTGRES_DB';
"

# Check cache performance
docker-compose -f docker-compose.prod.yml exec redis redis-cli -a $REDIS_PASSWORD INFO stats | grep -E "keyspace_hits|keyspace_misses"
```

---

### 4.3 Incident Response

**If issues detected during monitoring:**

**Minor Issues (performance degradation <30%):**
1. Document issue in deployment notes
2. Continue monitoring
3. Plan optimization for next deployment

**Major Issues (performance degradation 30-50%):**
1. Create incident channel: #incident-YYYYMMDD
2. Gather diagnostic data
3. Attempt hotfix
4. If hotfix fails within 30 minutes, rollback

**Critical Issues (errors >1%, downtime, data corruption):**
1. **IMMEDIATE ROLLBACK**
2. Execute: `/scripts/emergency-rollback.sh`
3. See: `/docs/deployment/production-rollback-plan.md`
4. Notify all stakeholders

---

## Phase 5: Deployment Completion (T+110m)

**Duration:** 10 minutes

### 5.1 Final Validation (T+110m)

```bash
# Timeline: T+110 minutes (after 1-hour monitoring)

echo "=== FINAL DEPLOYMENT VALIDATION ==="

# Run smoke tests again to confirm stability
./scripts/smoke-tests/production-smoke-tests.sh https://api.corporate-intel.com

# Check metrics over last hour
echo "Metrics summary (last 60 minutes):"
echo "- Uptime: $(curl -s http://localhost:9090/api/v1/query?query=up)"
echo "- Request count: $(curl -s http://localhost:9090/api/v1/query?query=http_requests_total)"
echo "- Error count: $(docker-compose -f docker-compose.prod.yml logs --since 60m api | grep -i error | wc -l)"

# If all stable:
echo "✅ DEPLOYMENT SUCCESSFUL AND STABLE"
echo "System ready for production traffic"
```

**Checklist:**
- [ ] No critical errors in last 60 minutes
- [ ] Performance metrics stable
- [ ] Resource utilization normal
- [ ] Smoke tests passing
- [ ] Monitoring dashboards showing healthy metrics

---

### 5.2 Documentation and Communication (T+115m)

```bash
# Create deployment record
DEPLOYMENT_RECORD="/opt/corporate-intel/deployment-logs/deployment-$(date +%Y%m%d_%H%M%S).md"

cat > $DEPLOYMENT_RECORD <<EOF
# Deployment Record

**Date:** $(date)
**Version:** v1.0.0
**Git SHA:** $(git rev-parse HEAD)
**Deployed By:** $USER

## Summary
- Start Time: [START_TIME]
- End Time: $(date)
- Total Duration: [DURATION] minutes
- Downtime: ~5-10 minutes
- Status: SUCCESS

## Changes Deployed
- [List major changes]
- [Feature updates]
- [Bug fixes]

## Performance Metrics (Post-Deployment)
- Health Endpoint: [X]ms avg
- API Endpoints: [X]ms avg
- Database Queries: [X]ms avg
- Cache Hit Ratio: [X]%
- Error Rate: [X]%

## Issues Encountered
- [None / List issues]

## Rollback Plan
- Available at: /docs/deployment/production-rollback-plan.md
- Rollback command: helm rollback corporate-intel -n production
- Database backup: [BACKUP_TIMESTAMP]

## Sign-Off
- Deployer: $USER
- DevOps Lead: [NAME]
- Date: $(date)
EOF

echo "Deployment record created: $DEPLOYMENT_RECORD"
```

**Announcement:**
```
✅ DEPLOYMENT COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━
Completed: [TIMESTAMP]
Total Duration: [XX] minutes
Downtime: ~5-10 minutes

✅ All smoke tests passed
✅ Performance validated
✅ Security verified
✅ 1-hour monitoring complete

System Status: OPERATIONAL
Version: v1.0.0

Deployment Record: [LINK]
Thank you team! 🎉
━━━━━━━━━━━━━━━━━━━━━━━━
```

---

### 5.3 Post-Deployment Tasks

**Within 2 hours:**
- [ ] Update status page: "All systems operational"
- [ ] Send deployment summary email to stakeholders
- [ ] Update changelog/release notes
- [ ] Archive deployment logs
- [ ] Schedule post-deployment review meeting

**Within 24 hours:**
- [ ] Review monitoring data for trends
- [ ] Document any issues encountered
- [ ] Update runbook based on learnings
- [ ] Create tickets for optimization opportunities
- [ ] Share metrics with team

**Within 1 week:**
- [ ] Post-deployment retrospective
- [ ] Update documentation
- [ ] Plan next deployment improvements

---

## Emergency Procedures

### Critical Error During Deployment

**If critical error occurs at any phase:**

```bash
# STOP DEPLOYMENT IMMEDIATELY
echo "🚨 CRITICAL ERROR DETECTED"
echo "Initiating emergency rollback"

# Execute emergency rollback
./scripts/emergency-rollback.sh

# Notify team
# Slack: #incidents
# Message: "🚨 Production deployment rollback in progress. Incident channel: #incident-[DATE]"

# Create incident report
# Document: What happened, when, impact, actions taken
```

**See full rollback procedures:** `/docs/deployment/production-rollback-plan.md`

---

## Deployment Metrics Template

**Record these metrics for every deployment:**

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| **Timing** |
| Total deployment time | 60-90 min | _____ min | [ ] ✅ [ ] ⚠️ |
| Downtime | 5-10 min | _____ min | [ ] ✅ [ ] ⚠️ |
| Migration time | <15 min | _____ min | [ ] ✅ [ ] ⚠️ |
| Smoke test time | <10 min | _____ min | [ ] ✅ [ ] ⚠️ |
| **Performance** |
| Health endpoint P99 | <10ms | _____ ms | [ ] ✅ [ ] ⚠️ |
| API endpoint P99 | <100ms | _____ ms | [ ] ✅ [ ] ⚠️ |
| Database P99 | <50ms | _____ ms | [ ] ✅ [ ] ⚠️ |
| Cache hit ratio | >95% | _____% | [ ] ✅ [ ] ⚠️ |
| Throughput | >20 QPS | _____ QPS | [ ] ✅ [ ] ⚠️ |
| **Quality** |
| Smoke tests passed | 100% | _____% | [ ] ✅ [ ] ⚠️ |
| Error rate | <0.1% | _____% | [ ] ✅ [ ] ⚠️ |
| Rollback needed | No | Yes/No | [ ] ✅ [ ] ⚠️ |
| Issues encountered | 0 | _____ | [ ] ✅ [ ] ⚠️ |

---

## Appendix

### A. Pre-Deployment Checklist Quick Reference

**1 Day Before:**
- [ ] Review deployment runbook
- [ ] Verify all checklist items
- [ ] Schedule deployment window
- [ ] Notify stakeholders

**1 Hour Before:**
- [ ] Create backups
- [ ] Verify team availability
- [ ] Prepare rollback artifacts
- [ ] Final go/no-go decision

### B. Emergency Contacts

**Incident Response:**
- On-Call Engineer: PagerDuty schedule
- DevOps Lead: @devops-lead (Slack)
- Platform Lead: @platform-lead (Slack/Phone)
- Database Admin: @dba-oncall (PagerDuty)
- Security Team: @security-team (Slack)

**Escalation Path:**
1. On-Call Engineer (0-15 min)
2. DevOps Lead (15-30 min)
3. Platform Lead (30-60 min)
4. CTO (critical incidents)

### C. Reference Documents

- Main Checklist: `/docs/deployment/production-deployment-checklist.md`
- Rollback Plan: `/docs/deployment/production-rollback-plan.md`
- Smoke Tests: `/docs/deployment/production-smoke-tests.md`
- Performance Baseline: `/docs/PLAN_A_DAY1_PERFORMANCE_BASELINE.md`
- Security Validation: `/docs/security_validation_day1_results.json`

### D. Deployment Scripts

- Emergency Rollback: `/scripts/emergency-rollback.sh`
- Full Rollback: `/scripts/rollback/full-rollback.sh`
- Smoke Tests: `/scripts/smoke-tests/production-smoke-tests.sh`
- Post-Deployment Monitor: `/scripts/monitoring/post-deployment-monitor.sh`

---

**Runbook Version:** 2.0.0
**Last Updated:** October 17, 2025
**Last Used:** _________________
**Next Review:** Before each deployment
**Maintained By:** DevOps Team

---

**END OF DEPLOYMENT RUNBOOK**
