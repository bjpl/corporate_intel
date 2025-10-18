# Production Smoke Tests

**Version:** 2.0.0
**Last Updated:** October 17, 2025
**Environment:** Production
**Execution Time:** 15-20 minutes
**Performance Baseline:** P99: 32ms, Success Rate: 100%

---

## Overview

Post-deployment smoke tests validate critical functionality immediately after production deployment. These tests should be executed within 10 minutes of deployment completion.

### Test Categories

1. **Infrastructure Tests** - Services, connectivity, resources
2. **API Tests** - Endpoints, authentication, data integrity
3. **Database Tests** - Connectivity, queries, performance
4. **Integration Tests** - External services, cache, storage
5. **Performance Tests** - Response times, throughput
6. **Security Tests** - HTTPS, headers, authentication

---

## Quick Smoke Test Script

**Location:** `/scripts/smoke-tests/production-smoke-tests.sh`

```bash
#!/bin/bash
# Production Smoke Tests
# Usage: ./production-smoke-tests.sh [base_url]
# Example: ./production-smoke-tests.sh https://api.corporate-intel.com

set -e

BASE_URL="${1:-https://api.corporate-intel.com}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RESULTS_FILE="/tmp/smoke-test-results-${TIMESTAMP}.txt"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
PASSED=0
FAILED=0
WARNINGS=0

# Helper functions
pass() {
    echo -e "${GREEN}✅ PASS${NC}: $1"
    echo "PASS: $1" >> $RESULTS_FILE
    ((PASSED++))
}

fail() {
    echo -e "${RED}❌ FAIL${NC}: $1"
    echo "FAIL: $1" >> $RESULTS_FILE
    ((FAILED++))
}

warn() {
    echo -e "${YELLOW}⚠️  WARN${NC}: $1"
    echo "WARN: $1" >> $RESULTS_FILE
    ((WARNINGS++))
}

echo "==================================="
echo "Production Smoke Tests"
echo "==================================="
echo "Base URL: $BASE_URL"
echo "Timestamp: $TIMESTAMP"
echo "==================================="
echo ""

# =====================================
# 1. INFRASTRUCTURE TESTS
# =====================================
echo ">>> INFRASTRUCTURE TESTS"

# Test 1.1: DNS Resolution
if host $(echo $BASE_URL | sed 's|https://||' | sed 's|/.*||') > /dev/null 2>&1; then
    pass "DNS resolution successful"
else
    fail "DNS resolution failed"
fi

# Test 1.2: HTTPS Connectivity
if curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/health" | grep -q "200"; then
    pass "HTTPS connectivity established"
else
    fail "HTTPS connectivity failed"
fi

# Test 1.3: SSL Certificate Valid
SSL_EXPIRY=$(echo | openssl s_client -servername $(echo $BASE_URL | sed 's|https://||' | sed 's|/.*||') -connect $(echo $BASE_URL | sed 's|https://||' | sed 's|/.*||'):443 2>/dev/null | openssl x509 -noout -enddate | cut -d= -f2)
if [ ! -z "$SSL_EXPIRY" ]; then
    pass "SSL certificate valid (expires: $SSL_EXPIRY)"
else
    warn "SSL certificate check inconclusive"
fi

# Test 1.4: HTTP to HTTPS Redirect
HTTP_URL=$(echo $BASE_URL | sed 's|https://|http://|')
HTTP_REDIRECT=$(curl -s -o /dev/null -w "%{http_code}" -L "$HTTP_URL/health")
if [ "$HTTP_REDIRECT" = "200" ]; then
    pass "HTTP to HTTPS redirect working"
else
    warn "HTTP redirect returned: $HTTP_REDIRECT"
fi

echo ""

# =====================================
# 2. HEALTH CHECKS
# =====================================
echo ">>> HEALTH CHECKS"

# Test 2.1: Basic Health Endpoint
HEALTH_STATUS=$(curl -s "$BASE_URL/health" | jq -r '.status' 2>/dev/null)
if [ "$HEALTH_STATUS" = "healthy" ]; then
    pass "Basic health endpoint: healthy"
else
    fail "Basic health endpoint failed (status: $HEALTH_STATUS)"
fi

# Test 2.2: Ping Endpoint
PING_RESPONSE=$(curl -s "$BASE_URL/health/ping")
if echo "$PING_RESPONSE" | grep -q "pong"; then
    pass "Ping endpoint responding"
else
    fail "Ping endpoint not responding correctly"
fi

# Test 2.3: Detailed Health Check
DETAILED_HEALTH=$(curl -s "$BASE_URL/api/v1/health")
DB_STATUS=$(echo $DETAILED_HEALTH | jq -r '.database.status' 2>/dev/null)
CACHE_STATUS=$(echo $DETAILED_HEALTH | jq -r '.cache.status' 2>/dev/null)

if [ "$DB_STATUS" = "healthy" ]; then
    pass "Database health check: healthy"
else
    fail "Database health check failed (status: $DB_STATUS)"
fi

if [ "$CACHE_STATUS" = "healthy" ]; then
    pass "Cache health check: healthy"
else
    fail "Cache health check failed (status: $CACHE_STATUS)"
fi

echo ""

# =====================================
# 3. API ENDPOINT TESTS
# =====================================
echo ">>> API ENDPOINT TESTS"

# Test 3.1: Companies List Endpoint
COMPANIES_RESPONSE=$(curl -s "$BASE_URL/api/v1/companies?limit=5")
COMPANIES_COUNT=$(echo $COMPANIES_RESPONSE | jq '. | length' 2>/dev/null)

if [ "$COMPANIES_COUNT" -gt 0 ] 2>/dev/null; then
    pass "Companies endpoint returned $COMPANIES_COUNT companies"
else
    fail "Companies endpoint returned no data"
fi

# Test 3.2: Company Detail Endpoint (ticker: AAPL)
COMPANY_DETAIL=$(curl -s "$BASE_URL/api/v1/companies/AAPL")
COMPANY_NAME=$(echo $COMPANY_DETAIL | jq -r '.name' 2>/dev/null)

if [ ! -z "$COMPANY_NAME" ] && [ "$COMPANY_NAME" != "null" ]; then
    pass "Company detail endpoint working (company: $COMPANY_NAME)"
else
    fail "Company detail endpoint failed for ticker AAPL"
fi

# Test 3.3: Financial Metrics Endpoint
FINANCIAL_RESPONSE=$(curl -s "$BASE_URL/api/v1/financial/metrics?ticker=AAPL&limit=5")
METRICS_COUNT=$(echo $FINANCIAL_RESPONSE | jq '. | length' 2>/dev/null)

if [ "$METRICS_COUNT" -gt 0 ] 2>/dev/null; then
    pass "Financial metrics endpoint returned $METRICS_COUNT metrics"
else
    warn "Financial metrics endpoint returned no data (may be expected)"
fi

# Test 3.4: API Documentation Endpoint
DOCS_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/docs")
if [ "$DOCS_STATUS" = "200" ]; then
    pass "API documentation accessible"
else
    warn "API documentation returned status: $DOCS_STATUS"
fi

# Test 3.5: OpenAPI Schema
OPENAPI_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/openapi.json")
if [ "$OPENAPI_STATUS" = "200" ]; then
    pass "OpenAPI schema accessible"
else
    warn "OpenAPI schema returned status: $OPENAPI_STATUS"
fi

echo ""

# =====================================
# 4. PERFORMANCE TESTS
# =====================================
echo ">>> PERFORMANCE TESTS"

# Test 4.1: Response Time - Health Endpoint (Target: <10ms)
HEALTH_TIME=$(curl -s -o /dev/null -w "%{time_total}" "$BASE_URL/health")
HEALTH_TIME_MS=$(echo "$HEALTH_TIME * 1000" | bc | cut -d. -f1)

if [ "$HEALTH_TIME_MS" -lt 10 ]; then
    pass "Health endpoint response time: ${HEALTH_TIME_MS}ms (excellent)"
elif [ "$HEALTH_TIME_MS" -lt 50 ]; then
    pass "Health endpoint response time: ${HEALTH_TIME_MS}ms (good)"
else
    warn "Health endpoint response time: ${HEALTH_TIME_MS}ms (slower than baseline)"
fi

# Test 4.2: Response Time - Companies Endpoint (Target: <50ms)
COMPANIES_TIME=$(curl -s -o /dev/null -w "%{time_total}" "$BASE_URL/api/v1/companies?limit=5")
COMPANIES_TIME_MS=$(echo "$COMPANIES_TIME * 1000" | bc | cut -d. -f1)

if [ "$COMPANIES_TIME_MS" -lt 50 ]; then
    pass "Companies endpoint response time: ${COMPANIES_TIME_MS}ms (excellent)"
elif [ "$COMPANIES_TIME_MS" -lt 100 ]; then
    pass "Companies endpoint response time: ${COMPANIES_TIME_MS}ms (good)"
else
    warn "Companies endpoint response time: ${COMPANIES_TIME_MS}ms (slower than baseline)"
fi

# Test 4.3: Response Time - Company Detail (Target: <20ms)
DETAIL_TIME=$(curl -s -o /dev/null -w "%{time_total}" "$BASE_URL/api/v1/companies/AAPL")
DETAIL_TIME_MS=$(echo "$DETAIL_TIME * 1000" | bc | cut -d. -f1)

if [ "$DETAIL_TIME_MS" -lt 20 ]; then
    pass "Company detail response time: ${DETAIL_TIME_MS}ms (excellent)"
elif [ "$DETAIL_TIME_MS" -lt 50 ]; then
    pass "Company detail response time: ${DETAIL_TIME_MS}ms (good)"
else
    warn "Company detail response time: ${DETAIL_TIME_MS}ms (slower than baseline)"
fi

echo ""

# =====================================
# 5. SECURITY TESTS
# =====================================
echo ">>> SECURITY TESTS"

# Test 5.1: HSTS Header
HSTS_HEADER=$(curl -s -I "$BASE_URL/health" | grep -i "strict-transport-security")
if [ ! -z "$HSTS_HEADER" ]; then
    pass "HSTS header present"
else
    fail "HSTS header missing"
fi

# Test 5.2: X-Frame-Options Header
XFRAME_HEADER=$(curl -s -I "$BASE_URL/health" | grep -i "x-frame-options")
if [ ! -z "$XFRAME_HEADER" ]; then
    pass "X-Frame-Options header present"
else
    warn "X-Frame-Options header missing"
fi

# Test 5.3: Content Security Policy
CSP_HEADER=$(curl -s -I "$BASE_URL/health" | grep -i "content-security-policy")
if [ ! -z "$CSP_HEADER" ]; then
    pass "Content-Security-Policy header present"
else
    warn "Content-Security-Policy header missing"
fi

# Test 5.4: X-Content-Type-Options
XCONTENT_HEADER=$(curl -s -I "$BASE_URL/health" | grep -i "x-content-type-options")
if [ ! -z "$XCONTENT_HEADER" ]; then
    pass "X-Content-Type-Options header present"
else
    warn "X-Content-Type-Options header missing"
fi

# Test 5.5: Authentication Required for Protected Endpoints
# Attempt to access a protected endpoint without auth
PROTECTED_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/v1/admin/users")
if [ "$PROTECTED_STATUS" = "401" ] || [ "$PROTECTED_STATUS" = "403" ]; then
    pass "Authentication required for protected endpoints (status: $PROTECTED_STATUS)"
else
    warn "Protected endpoint returned unexpected status: $PROTECTED_STATUS"
fi

echo ""

# =====================================
# 6. DATA INTEGRITY TESTS
# =====================================
echo ">>> DATA INTEGRITY TESTS"

# Test 6.1: Company Data Structure
COMPANY_TICKER=$(echo $COMPANY_DETAIL | jq -r '.ticker' 2>/dev/null)
COMPANY_CATEGORY=$(echo $COMPANY_DETAIL | jq -r '.category' 2>/dev/null)

if [ "$COMPANY_TICKER" = "AAPL" ]; then
    pass "Company data structure valid (ticker: $COMPANY_TICKER)"
else
    fail "Company data structure invalid"
fi

# Test 6.2: Expected Companies Present
EXPECTED_COMPANIES=("AAPL" "GOOGL" "MSFT")
for ticker in "${EXPECTED_COMPANIES[@]}"; do
    COMPANY_EXISTS=$(curl -s "$BASE_URL/api/v1/companies/$ticker" | jq -r '.ticker' 2>/dev/null)
    if [ "$COMPANY_EXISTS" = "$ticker" ]; then
        pass "Expected company present: $ticker"
    else
        warn "Expected company missing: $ticker"
    fi
done

echo ""

# =====================================
# 7. ERROR HANDLING TESTS
# =====================================
echo ">>> ERROR HANDLING TESTS"

# Test 7.1: 404 Not Found
NOT_FOUND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/v1/nonexistent")
if [ "$NOT_FOUND_STATUS" = "404" ]; then
    pass "404 error handled correctly"
else
    warn "404 error returned status: $NOT_FOUND_STATUS"
fi

# Test 7.2: Invalid Ticker
INVALID_TICKER=$(curl -s "$BASE_URL/api/v1/companies/INVALID_TICKER_9999")
ERROR_DETAIL=$(echo $INVALID_TICKER | jq -r '.detail' 2>/dev/null)
if [ ! -z "$ERROR_DETAIL" ]; then
    pass "Invalid ticker handled gracefully"
else
    warn "Invalid ticker response unclear"
fi

# Test 7.3: Malformed Request
MALFORMED_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/v1/companies?limit=invalid")
if [ "$MALFORMED_STATUS" = "422" ] || [ "$MALFORMED_STATUS" = "400" ]; then
    pass "Malformed request handled correctly (status: $MALFORMED_STATUS)"
else
    warn "Malformed request returned status: $MALFORMED_STATUS"
fi

echo ""

# =====================================
# RESULTS SUMMARY
# =====================================
echo "==================================="
echo "SMOKE TESTS COMPLETE"
echo "==================================="
echo -e "Passed:   ${GREEN}$PASSED${NC}"
echo -e "Failed:   ${RED}$FAILED${NC}"
echo -e "Warnings: ${YELLOW}$WARNINGS${NC}"
echo "==================================="
echo "Results saved to: $RESULTS_FILE"
echo ""

# Determine overall status
if [ $FAILED -gt 0 ]; then
    echo -e "${RED}❌ SMOKE TESTS FAILED${NC}"
    echo "Action required: Investigate failures before proceeding"
    exit 1
elif [ $WARNINGS -gt 5 ]; then
    echo -e "${YELLOW}⚠️  SMOKE TESTS PASSED WITH WARNINGS${NC}"
    echo "Review warnings to ensure expected behavior"
    exit 0
else
    echo -e "${GREEN}✅ SMOKE TESTS PASSED${NC}"
    echo "System ready for production use"
    exit 0
fi
```

---

## Manual Smoke Test Checklist

Use this checklist for manual verification after automated tests:

### 1. Infrastructure Validation

**Time:** 5 minutes

- [ ] **DNS Resolution**
  ```bash
  dig api.corporate-intel.com +short
  nslookup api.corporate-intel.com
  ```
  - Expected: Returns correct IP address
  - Actual: _________________

- [ ] **SSL Certificate**
  ```bash
  echo | openssl s_client -servername api.corporate-intel.com -connect api.corporate-intel.com:443 2>/dev/null | openssl x509 -noout -dates
  ```
  - Expected: Valid certificate, expires in 60+ days
  - Actual: _________________

- [ ] **HTTPS Grade**
  - Test at: https://www.ssllabs.com/ssltest/
  - Expected: Grade A or A+
  - Actual: _________________

- [ ] **Container Status**
  ```bash
  docker-compose -f docker-compose.prod.yml ps
  ```
  - Expected: All services "Up" and "healthy"
  - API: [ ] Up [ ] Healthy
  - PostgreSQL: [ ] Up [ ] Healthy
  - Redis: [ ] Up [ ] Healthy
  - MinIO: [ ] Up [ ] Healthy
  - Prometheus: [ ] Up [ ] Healthy
  - Grafana: [ ] Up [ ] Healthy
  - Jaeger: [ ] Up [ ] Healthy

---

### 2. API Endpoint Tests

**Time:** 5 minutes

- [ ] **Health Endpoints**
  ```bash
  # Basic health
  curl -f https://api.corporate-intel.com/health
  # Expected: {"status": "healthy"}

  # Ping
  curl -f https://api.corporate-intel.com/health/ping
  # Expected: {"message": "pong"}

  # Detailed health
  curl -f https://api.corporate-intel.com/api/v1/health
  # Expected: Detailed status with database, cache, storage
  ```
  - All health checks passing: [ ] Yes [ ] No

- [ ] **Companies Endpoint**
  ```bash
  curl https://api.corporate-intel.com/api/v1/companies?limit=5
  ```
  - Expected: Returns 5 companies
  - Actual count: _________________
  - Response time: _____ ms (target: <50ms)

- [ ] **Company Detail**
  ```bash
  curl https://api.corporate-intel.com/api/v1/companies/AAPL
  ```
  - Expected: Returns Apple Inc. details
  - Company name: _________________
  - Response time: _____ ms (target: <20ms)

- [ ] **Financial Metrics**
  ```bash
  curl https://api.corporate-intel.com/api/v1/financial/metrics?ticker=AAPL&limit=5
  ```
  - Expected: Returns financial data
  - Metrics count: _________________
  - Response time: _____ ms (target: <50ms)

- [ ] **API Documentation**
  - Access: https://api.corporate-intel.com/docs
  - Swagger UI loads: [ ] Yes [ ] No
  - All endpoints visible: [ ] Yes [ ] No

---

### 3. Database Tests

**Time:** 3 minutes

- [ ] **Database Connectivity**
  ```bash
  docker-compose -f docker-compose.prod.yml exec postgres pg_isready -U $POSTGRES_USER -d $POSTGRES_DB
  ```
  - Expected: "accepting connections"
  - Actual: _________________

- [ ] **Table Counts**
  ```bash
  docker-compose -f docker-compose.prod.yml exec postgres psql -U $POSTGRES_USER -d $POSTGRES_DB -c "
    SELECT 'companies' AS table_name, COUNT(*) FROM companies
    UNION ALL
    SELECT 'financial_metrics', COUNT(*) FROM financial_metrics
    UNION ALL
    SELECT 'sec_filings', COUNT(*) FROM sec_filings;
  "
  ```
  - Companies: _____ (expected: >0)
  - Financial Metrics: _____ (expected: >0)
  - SEC Filings: _____ (expected: >0)

- [ ] **Query Performance**
  ```bash
  docker-compose -f docker-compose.prod.yml exec postgres psql -U $POSTGRES_USER -d $POSTGRES_DB -c "
    EXPLAIN ANALYZE SELECT * FROM companies WHERE ticker = 'AAPL';
  "
  ```
  - Execution time: _____ ms (target: <5ms)
  - Index used: [ ] Yes [ ] No

- [ ] **Cache Hit Ratio**
  ```bash
  docker-compose -f docker-compose.prod.yml exec postgres psql -U $POSTGRES_USER -d $POSTGRES_DB -c "
    SELECT
      sum(heap_blks_hit) / (sum(heap_blks_hit) + sum(heap_blks_read)) * 100 AS cache_hit_ratio
    FROM pg_statio_user_tables;
  "
  ```
  - Cache hit ratio: _____% (target: >95%, baseline: 99.2%)

---

### 4. Cache Tests (Redis)

**Time:** 2 minutes

- [ ] **Redis Connectivity**
  ```bash
  docker-compose -f docker-compose.prod.yml exec redis redis-cli -a $REDIS_PASSWORD ping
  ```
  - Expected: PONG
  - Actual: _________________

- [ ] **Redis Info**
  ```bash
  docker-compose -f docker-compose.prod.yml exec redis redis-cli -a $REDIS_PASSWORD INFO stats
  ```
  - Total connections: _____
  - Keyspace hits: _____
  - Keyspace misses: _____
  - Hit rate: _____% (target: >80%)

- [ ] **Cache Operations**
  ```bash
  # Test SET/GET
  docker-compose -f docker-compose.prod.yml exec redis redis-cli -a $REDIS_PASSWORD SET test_key "test_value"
  docker-compose -f docker-compose.prod.yml exec redis redis-cli -a $REDIS_PASSWORD GET test_key
  docker-compose -f docker-compose.prod.yml exec redis redis-cli -a $REDIS_PASSWORD DEL test_key
  ```
  - Cache writes working: [ ] Yes [ ] No
  - Cache reads working: [ ] Yes [ ] No

---

### 5. Object Storage Tests (MinIO)

**Time:** 2 minutes

- [ ] **MinIO Health**
  ```bash
  curl -f http://localhost:9000/minio/health/live
  ```
  - Expected: 200 OK
  - Actual status: _________________

- [ ] **Bucket Access**
  ```bash
  docker-compose -f docker-compose.prod.yml exec minio mc ls local
  ```
  - Expected buckets visible:
    - [ ] prod-corporate-documents
    - [ ] prod-analysis-reports

- [ ] **File Operations** (if applicable)
  ```bash
  # Test file upload
  echo "test content" > /tmp/test.txt
  docker-compose -f docker-compose.prod.yml exec minio mc cp /tmp/test.txt local/prod-corporate-documents/smoke-test.txt

  # Test file download
  docker-compose -f docker-compose.prod.yml exec minio mc cat local/prod-corporate-documents/smoke-test.txt

  # Cleanup
  docker-compose -f docker-compose.prod.yml exec minio mc rm local/prod-corporate-documents/smoke-test.txt
  ```
  - Upload successful: [ ] Yes [ ] No
  - Download successful: [ ] Yes [ ] No

---

### 6. Performance Validation

**Time:** 3 minutes

**Baseline Metrics (from performance baseline):**
- P50: 5.31ms
- P95: 18.93ms
- P99: 32.14ms
- Mean: 8.42ms
- Throughput: 27.3 QPS

- [ ] **Response Time - Health Endpoint**
  ```bash
  for i in {1..10}; do
    curl -s -o /dev/null -w "%{time_total}\n" https://api.corporate-intel.com/health
  done | awk '{s+=$1; count++} END {print "Avg:", s/count*1000, "ms"}'
  ```
  - Average: _____ ms (target: <10ms)
  - Status: [ ] Pass [ ] Fail

- [ ] **Response Time - Companies Endpoint**
  ```bash
  for i in {1..10}; do
    curl -s -o /dev/null -w "%{time_total}\n" https://api.corporate-intel.com/api/v1/companies?limit=5
  done | awk '{s+=$1; count++} END {print "Avg:", s/count*1000, "ms"}'
  ```
  - Average: _____ ms (target: <50ms, baseline: 6.5ms)
  - Status: [ ] Pass [ ] Fail

- [ ] **Concurrent Requests** (10 users)
  ```bash
  seq 1 10 | xargs -n1 -P10 -I{} curl -s -o /dev/null -w "%{time_total}\n" https://api.corporate-intel.com/api/v1/companies/AAPL
  ```
  - Max response time: _____ ms (target: <100ms)
  - Status: [ ] Pass [ ] Fail

---

### 7. Security Validation

**Time:** 3 minutes
**Security Score Baseline:** 9.2/10

- [ ] **HTTPS Enforcement**
  ```bash
  curl -I http://api.corporate-intel.com/health
  ```
  - Redirects to HTTPS: [ ] Yes [ ] No
  - Status code: _____ (expected: 301 or 308)

- [ ] **Security Headers**
  ```bash
  curl -I https://api.corporate-intel.com/health
  ```
  - [ ] Strict-Transport-Security present
  - [ ] X-Frame-Options present
  - [ ] X-Content-Type-Options present
  - [ ] Content-Security-Policy present
  - [ ] Referrer-Policy present

- [ ] **Authentication**
  ```bash
  # Should require authentication
  curl -s -o /dev/null -w "%{http_code}" https://api.corporate-intel.com/api/v1/admin/users
  ```
  - Status code: _____ (expected: 401 or 403)
  - Authentication required: [ ] Yes [ ] No

- [ ] **Rate Limiting**
  ```bash
  # Make 150 rapid requests (over limit of 100/min)
  for i in {1..150}; do
    curl -s -o /dev/null -w "%{http_code}\n" https://api.corporate-intel.com/health
  done | tail -10
  ```
  - Rate limiting triggered: [ ] Yes [ ] No
  - Status code when limited: _____ (expected: 429)

---

### 8. Monitoring & Observability

**Time:** 2 minutes

- [ ] **Prometheus**
  - Access: http://localhost:9090
  - Targets up: [ ] Yes [ ] No
  - Metrics collecting: [ ] Yes [ ] No
  - Query test:
    ```
    up{job="corporate-intel-api"}
    ```
    - Result: _____ (expected: 1)

- [ ] **Grafana**
  - Access: http://localhost:3000
  - Login successful: [ ] Yes [ ] No
  - Dashboards visible: [ ] Yes [ ] No
  - Data flowing: [ ] Yes [ ] No

- [ ] **Jaeger**
  - Access: http://localhost:16686
  - UI accessible: [ ] Yes [ ] No
  - Traces visible: [ ] Yes [ ] No
  - Services listed: [ ] Yes [ ] No

---

## Smoke Test Results Template

**Deployment Date:** _________________
**Deployment Version:** _________________
**Tested By:** _________________
**Test Start Time:** _________________
**Test End Time:** _________________

### Test Results Summary

| Category | Tests | Passed | Failed | Warnings |
|----------|-------|--------|--------|----------|
| Infrastructure | 4 | _____ | _____ | _____ |
| Health Checks | 5 | _____ | _____ | _____ |
| API Endpoints | 10 | _____ | _____ | _____ |
| Performance | 5 | _____ | _____ | _____ |
| Security | 8 | _____ | _____ | _____ |
| Database | 4 | _____ | _____ | _____ |
| Cache | 3 | _____ | _____ | _____ |
| Storage | 3 | _____ | _____ | _____ |
| Monitoring | 3 | _____ | _____ | _____ |
| **TOTAL** | **45** | **_____** | **_____** | **_____** |

### Overall Status

☐ **PASS** - All critical tests passed, system ready for production
☐ **PASS WITH WARNINGS** - Critical tests passed, investigate warnings
☐ **FAIL** - Critical tests failed, rollback recommended

### Issues Identified

1. _________________________________________________________________
2. _________________________________________________________________
3. _________________________________________________________________

### Actions Taken

1. _________________________________________________________________
2. _________________________________________________________________
3. _________________________________________________________________

### Sign-Off

**Tester:** _________________________ Date: _________
**DevOps Lead:** _________________________ Date: _________
**Approval:** ☐ Approved ☐ Requires Action

---

## Continuous Smoke Testing

### Automated Smoke Test Schedule

**Post-Deployment:** Immediate (within 10 minutes)
**Hourly:** First 24 hours after deployment
**Daily:** For first week after deployment
**Weekly:** Ongoing production validation

### Smoke Test Monitoring

Configure alerts for smoke test failures:

```yaml
# prometheus/alerts/smoke-tests.yml
groups:
  - name: smoke_tests
    interval: 5m
    rules:
      - alert: SmokeTestFailure
        expr: smoke_test_failures_total > 0
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Smoke tests failing in production"
          description: "{{ $value }} smoke tests have failed in the last 5 minutes"
```

---

## Appendix

### A. Expected Response Times (from baseline)

| Endpoint | Mean | P95 | P99 | Status |
|----------|------|-----|-----|--------|
| /health/ping | 1.5ms | 3.2ms | 3.2ms | Optimal |
| /health | 2.8ms | 5.4ms | 5.4ms | Optimal |
| /api/v1/companies/{ticker} | 2.15ms | 4.8ms | 4.8ms | Optimal |
| /api/v1/companies | 6.5ms | 14.2ms | 14.2ms | Excellent |
| /api/v1/financial/metrics | 6.92ms | 15.3ms | 15.3ms | Excellent |
| /health/detailed | 15.2ms | 28.5ms | 28.5ms | Excellent |
| /api/v1/intelligence/competitive | 24.56ms | 42.1ms | 42.1ms | Good |

### B. Automated Test Script Usage

```bash
# Run automated smoke tests
./scripts/smoke-tests/production-smoke-tests.sh https://api.corporate-intel.com

# Save results
./scripts/smoke-tests/production-smoke-tests.sh https://api.corporate-intel.com > /tmp/smoke-test-$(date +%Y%m%d_%H%M%S).log

# Run with custom timeout
timeout 300 ./scripts/smoke-tests/production-smoke-tests.sh https://api.corporate-intel.com

# Run in CI/CD pipeline
SMOKE_TEST_EXIT_CODE=$?
if [ $SMOKE_TEST_EXIT_CODE -ne 0 ]; then
    echo "Smoke tests failed, triggering rollback"
    ./scripts/emergency-rollback.sh
fi
```

### C. Troubleshooting Common Issues

**Issue: Health endpoint returns 502/503**
- Check: Container status
- Check: Application logs
- Action: Restart containers or rollback

**Issue: Slow response times (>100ms)**
- Check: Database connection pool
- Check: Cache hit ratio
- Check: Resource utilization (CPU/memory)
- Action: Scale up or investigate queries

**Issue: Authentication failures**
- Check: SECRET_KEY configured correctly
- Check: JWT token expiration settings
- Check: Redis cache accessible
- Action: Verify configuration

---

**Document Version:** 2.0.0
**Last Updated:** October 17, 2025
**Maintained By:** QA/DevOps Team

---

**END OF SMOKE TESTS**
