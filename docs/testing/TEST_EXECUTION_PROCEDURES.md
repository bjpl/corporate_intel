# Test Execution Procedures and Success Criteria

## Overview

This document provides comprehensive procedures for executing production validation tests and defines success criteria for each test category.

---

## Table of Contents

1. [Production Smoke Tests](#1-production-smoke-tests)
2. [Load Testing](#2-load-testing)
3. [Backup and Restore Testing](#3-backup-and-restore-testing)
4. [Disaster Recovery Drills](#4-disaster-recovery-drills)
5. [Security Testing](#5-security-testing)
6. [Performance Testing](#6-performance-testing)

---

## 1. Production Smoke Tests

### Purpose
Validate critical functionality after deployment to ensure the system is operational.

### Execution

```bash
# Set production environment variables
export PRODUCTION_API_URL="https://api.example.com"
export PRODUCTION_DASHBOARD_URL="https://dashboard.example.com"
export PRODUCTION_AUTH_TOKEN="your-token-here"
export PRODUCTION_DATABASE_URL="postgresql://user:pass@prod-db:5432/corporate_intel"

# Run production smoke tests
pytest tests/production/test_critical_path.py -v --tb=short

# Run with specific markers
pytest tests/production/ -m critical -v

# Generate HTML report
pytest tests/production/ --html=smoke_test_report.html --self-contained-html
```

### Success Criteria

#### Critical Health Checks
- ✅ All health endpoints return 200 status
- ✅ Health check response time < 100ms
- ✅ Database shows as healthy
- ✅ Redis shows as healthy
- ✅ All required services operational

#### Critical User Journeys
- ✅ User can authenticate successfully
- ✅ User can view companies list
- ✅ User can view company details
- ✅ User can view financial metrics
- ✅ Dashboard loads successfully

#### Data Integrity
- ✅ Companies have all required fields
- ✅ Metrics contain valid data
- ✅ No null values in critical fields
- ✅ Data relationships intact

#### Security
- ✅ Protected endpoints require authentication
- ✅ HTTPS enforced
- ✅ CORS headers configured
- ✅ Security headers present

#### Performance
- ✅ API response time P95 < 500ms
- ✅ Database query time < 200ms
- ✅ No timeout errors

### Test Duration
**Estimated Time**: 5-10 minutes

### Frequency
- After every deployment
- Daily in production
- Before major releases

### Failure Response
If smoke tests fail:
1. **STOP** further deployment
2. Alert on-call team
3. Initiate rollback if necessary
4. Investigate failures
5. Fix issues in staging
6. Re-run smoke tests
7. Only proceed when all tests pass

---

## 2. Load Testing

### Purpose
Validate system performance under various load conditions and identify capacity limits.

### Execution

#### Scenario 1: Baseline Load (Normal Traffic)

```bash
# Purpose: Establish baseline performance metrics
# Expected: 10 concurrent users, normal usage patterns
# Duration: 5 minutes

cd tests/load

locust -f locustfile_production.py \
    --host=https://api.example.com \
    --users=10 \
    --spawn-rate=1 \
    --run-time=5m \
    --headless \
    --html=reports/baseline_$(date +%Y%m%d).html
```

**Success Criteria**:
- ✅ P50 response time < 100ms
- ✅ P95 response time < 300ms
- ✅ P99 response time < 500ms
- ✅ Error rate < 0.1%
- ✅ CPU usage < 30%
- ✅ Memory usage < 40%
- ✅ No errors in logs

#### Scenario 2: Peak Load (2x Normal Traffic)

```bash
# Purpose: Validate system handles peak traffic
# Expected: 100 concurrent users, busy period simulation
# Duration: 10 minutes

locust -f locustfile_production.py \
    --host=https://api.example.com \
    --users=100 \
    --spawn-rate=10 \
    --run-time=10m \
    --headless \
    --html=reports/peak_load_$(date +%Y%m%d).html
```

**Success Criteria**:
- ✅ P95 response time < 500ms
- ✅ P99 response time < 1000ms
- ✅ Error rate < 1%
- ✅ CPU usage < 70%
- ✅ Memory usage < 80%
- ✅ Auto-scaling triggers if needed
- ✅ All services remain healthy

#### Scenario 3: Stress Test (Find Breaking Point)

```bash
# Purpose: Identify system capacity limits
# Expected: 200+ concurrent users, heavy load
# Duration: 15 minutes

locust -f locustfile_production.py \
    --host=https://api.example.com \
    --users=200 \
    --spawn-rate=20 \
    --run-time=15m \
    --headless \
    --html=reports/stress_test_$(date +%Y%m%d).html
```

**Success Criteria**:
- ✅ System remains available (no crashes)
- ✅ Graceful degradation under extreme load
- ✅ Error rate < 5%
- ✅ Alerts triggered appropriately
- ✅ System recovers after load decreases
- ✅ No memory leaks detected

#### Scenario 4: Endurance Test (Sustained Load)

```bash
# Purpose: Detect memory leaks and stability issues
# Expected: 50 concurrent users, sustained for 1 hour
# Duration: 60 minutes

locust -f locustfile_production.py \
    --host=https://api.example.com \
    --users=50 \
    --spawn-rate=5 \
    --run-time=60m \
    --headless \
    --html=reports/endurance_$(date +%Y%m%d).html
```

**Success Criteria**:
- ✅ Memory usage remains stable (no continuous growth)
- ✅ Response times remain consistent
- ✅ No connection pool exhaustion
- ✅ No database connection leaks
- ✅ Error rate remains low
- ✅ System stable for entire duration

### Test Duration
- Baseline: 5 minutes
- Peak Load: 10 minutes
- Stress Test: 15 minutes
- Endurance: 60 minutes
- **Total**: ~90 minutes

### Frequency
- Baseline: Weekly
- Peak Load: Bi-weekly
- Stress Test: Monthly
- Endurance: Monthly

### Automated Execution

Use the provided script for automated testing:

```bash
cd tests/load
chmod +x run_load_tests.sh
./run_load_tests.sh
```

### Performance Metrics to Track

| Metric | Baseline | Peak | Stress | Endurance |
|--------|----------|------|--------|-----------|
| P50 Response Time | < 100ms | < 200ms | < 300ms | < 150ms |
| P95 Response Time | < 300ms | < 500ms | < 1000ms | < 400ms |
| P99 Response Time | < 500ms | < 1000ms | < 2000ms | < 800ms |
| Error Rate | < 0.1% | < 1% | < 5% | < 0.5% |
| Requests/sec | ~20 | ~200 | ~400 | ~100 |
| CPU Usage | < 30% | < 70% | < 90% | < 50% |
| Memory Usage | < 40% | < 80% | < 95% | Stable |

---

## 3. Backup and Restore Testing

### Purpose
Validate backup and recovery procedures to ensure data can be recovered in case of disaster.

### Execution

#### Weekly: Backup Verification

```bash
# Verify latest backup exists and is valid
python tests/production/verify_backups.py

# Expected output:
# ✅ Database backup OK: /backups/db_20251025.sql.gz
#    Age: 2 hours
#    Size: 856.32 MB
# ✅ Backup restoration verified (15,234 companies)
```

**Success Criteria**:
- ✅ Backup file exists
- ✅ Backup age < 24 hours
- ✅ Backup size > expected minimum
- ✅ Backup integrity verified
- ✅ Test restoration succeeds

#### Monthly: Full Restore Test

```bash
# Full restore test to separate environment
./scripts/test_full_restore.sh

# Steps:
# 1. Create test environment
# 2. Restore database backup
# 3. Restore application files
# 4. Restore configuration
# 5. Start services
# 6. Run smoke tests
# 7. Verify data integrity
```

**Success Criteria**:
- ✅ Database restores completely
- ✅ All tables present
- ✅ Row counts match
- ✅ Foreign keys intact
- ✅ Indexes restored
- ✅ Application starts successfully
- ✅ Smoke tests pass
- ✅ No data corruption

#### Quarterly: Point-in-Time Recovery

```bash
# Test PITR to specific timestamp
./scripts/test_pitr.sh "2025-10-25 14:30:00"
```

**Success Criteria**:
- ✅ Recovery to exact timestamp
- ✅ Data before timestamp intact
- ✅ Data after timestamp not present
- ✅ Database in consistent state
- ✅ No missing transactions

### Test Duration
- Backup Verification: 5 minutes
- Full Restore: 30-60 minutes
- PITR: 30-90 minutes

### Frequency
- Backup Verification: Daily (automated)
- Full Restore: Monthly
- PITR: Quarterly

---

## 4. Disaster Recovery Drills

### Purpose
Validate complete system recovery procedures and team readiness.

### Execution Types

#### Quarterly: Tabletop Exercise
- **Duration**: 2-4 hours
- **Format**: Discussion-based walkthrough
- **Participants**: All team members
- **No systems affected**

**Success Criteria**:
- ✅ All participants understand their roles
- ✅ Recovery procedures are clear
- ✅ Communication plan validated
- ✅ Gaps identified and documented
- ✅ Action items assigned

#### Monthly: Simulated Failure
- **Duration**: 1-3 hours
- **Environment**: Staging only
- **Impact**: No production impact

**Test Scenarios**:
1. Database primary failure
2. Redis cache failure
3. API service crash
4. Network partition
5. Disk full scenario

**Success Criteria** (per scenario):
- ✅ Failure detected automatically
- ✅ Alerts triggered correctly
- ✅ Failover occurs (if applicable)
- ✅ Service recovers within RTO
- ✅ No data loss (RPO = 0)
- ✅ Team responds appropriately

#### Bi-Annual: Full DR Test
- **Duration**: 4-8 hours
- **Environment**: Dedicated DR environment
- **Impact**: No production impact

**Phases**:
1. Scenario initiation (30 min)
2. Assessment (30 min)
3. Infrastructure provisioning (60 min)
4. Database recovery (90 min)
5. Application deployment (90 min)
6. Verification (90 min)
7. Debrief (60 min)

**Success Criteria**:
- ✅ RTO < 4 hours
- ✅ RPO = 0 (no data loss)
- ✅ All critical paths functional
- ✅ Performance acceptable
- ✅ Team confident in procedures
- ✅ Documentation accurate

### Test Duration
- Tabletop: 2-4 hours
- Simulated Failure: 1-3 hours each
- Full DR Test: 4-8 hours

### Frequency
- Tabletop: Quarterly
- Simulated Failures: Monthly (different scenarios)
- Full DR Test: Bi-annually

---

## 5. Security Testing

### Purpose
Validate security controls and identify vulnerabilities.

### Execution

#### Continuous: Automated Security Scans

```bash
# Run security vulnerability scan
safety check --json > security_report.json

# Scan Docker images
docker scan corporate-intel-api:latest

# OWASP dependency check
dependency-check --scan . --format JSON
```

#### Monthly: Security Validation Tests

```bash
# Run security-focused tests
pytest tests/production/test_critical_path.py -m security -v

# Test authentication
./scripts/test_authentication.sh

# Test authorization
./scripts/test_authorization.sh

# Test input validation
./scripts/test_input_validation.sh
```

**Success Criteria**:
- ✅ No critical vulnerabilities
- ✅ Authentication required for protected endpoints
- ✅ Authorization checks working
- ✅ Input validation preventing injection
- ✅ Security headers present
- ✅ HTTPS enforced

#### Quarterly: Penetration Testing
- External security audit
- Professional penetration test
- Security code review

### Test Duration
- Automated Scans: 10-30 minutes
- Security Validation: 30-60 minutes
- Penetration Testing: 1-2 days (external)

### Frequency
- Automated Scans: Daily
- Security Validation: Monthly
- Penetration Testing: Quarterly or annually

---

## 6. Performance Testing

### Purpose
Validate system performance meets requirements under various conditions.

### Execution

#### Database Performance

```bash
# Run database performance tests
pytest tests/performance/test_database_performance.py -v

# Test query execution times
./scripts/benchmark_queries.sh

# Test connection pool
./scripts/test_connection_pool.sh
```

**Success Criteria**:
- ✅ Simple queries < 50ms
- ✅ Complex queries < 200ms
- ✅ Bulk operations < 500ms
- ✅ Index utilization > 90%
- ✅ Connection pool not exhausted

#### API Performance

```bash
# Test API endpoint performance
./scripts/benchmark_api_endpoints.sh

# Output:
# GET /api/v1/companies: 45ms (P95: 78ms)
# GET /api/v1/metrics: 89ms (P95: 156ms)
# GET /api/v1/intelligence/summary: 234ms (P95: 445ms)
```

**Success Criteria**:
- ✅ P50 < 100ms
- ✅ P95 < 500ms
- ✅ P99 < 1000ms
- ✅ No timeouts
- ✅ Consistent performance

#### Frontend Performance

```bash
# Test dashboard load time
./scripts/test_dashboard_performance.sh
```

**Success Criteria**:
- ✅ Initial load < 2 seconds
- ✅ Time to interactive < 3 seconds
- ✅ No layout shifts
- ✅ Smooth interactions

### Test Duration
- Database Performance: 15-30 minutes
- API Performance: 15-30 minutes
- Frontend Performance: 15-30 minutes

### Frequency
- Database: Weekly
- API: Weekly
- Frontend: Bi-weekly

---

## Test Execution Schedule

### Daily
- Production smoke tests (automated)
- Backup verification (automated)
- Security scans (automated)

### Weekly
- Baseline load test
- Database performance test
- API performance test

### Bi-Weekly
- Peak load test
- Frontend performance test

### Monthly
- Stress test
- Endurance test
- Full backup restore test
- Simulated failure drill
- Security validation tests

### Quarterly
- Tabletop exercise
- Point-in-time recovery test
- Penetration testing

### Bi-Annual
- Full disaster recovery test

### Annual
- Regional failover test
- Complete security audit

---

## Reporting and Metrics

### Test Results Dashboard

Track and visualize:
- Test execution history
- Pass/fail rates
- Performance trends
- Coverage metrics
- Incident correlation

### Key Metrics

| Metric | Target | Alerting |
|--------|--------|----------|
| Smoke Test Pass Rate | 100% | Alert if < 100% |
| Load Test P95 | < 500ms | Alert if > 750ms |
| Backup Success Rate | 100% | Alert if fails |
| DR Drill RTO | < 4 hours | Track trend |
| Security Vulnerabilities | 0 critical | Alert on critical |
| Test Coverage | > 80% | Alert if < 75% |

### Monthly Report Template

```markdown
# Testing Report - [Month Year]

## Executive Summary
- Tests Executed: [X]
- Tests Passed: [Y]
- Pass Rate: [Z%]
- Critical Issues: [N]

## Test Results
### Smoke Tests
- Executions: [Daily, total X]
- Success Rate: [Y%]
- Issues: [List]

### Load Tests
- Baseline: [Result]
- Peak: [Result]
- Performance: [Trend]

### Security Tests
- Vulnerabilities Found: [N]
- Severity: [Distribution]
- Remediation: [Status]

## Issues and Actions
| Issue | Severity | Status | Owner | Due Date |
|-------|----------|--------|-------|----------|

## Recommendations
1. [Recommendation 1]
2. [Recommendation 2]
```

---

## Contacts

**QA Lead**: qa-lead@example.com
**Performance Engineer**: perf-engineer@example.com
**Security Officer**: security@example.com
**On-Call**: oncall@example.com

---

## References

- Production Smoke Tests: tests/production/test_critical_path.py
- Load Tests: tests/load/locustfile_production.py
- Backup Procedures: docs/testing/BACKUP_RESTORE_PROCEDURES.md
- DR Drills: docs/deployment/DISASTER_RECOVERY_DRILLS.md
- Validation Checklist: docs/deployment/PRODUCTION_VALIDATION_CHECKLIST.md
