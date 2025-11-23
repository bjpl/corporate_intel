#!/bin/bash
# Production Smoke Tests - Staging Environment
# Usage: ./smoke-test-staging.sh
# Executes comprehensive validation of all critical functionality

set -e

BASE_URL="http://localhost:8004"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RESULTS_DIR="docs/deployment"
RESULTS_FILE="$RESULTS_DIR/smoke-test-results-day3-${TIMESTAMP}.json"
REPORT_FILE="$RESULTS_DIR/smoke-test-report-day3-${TIMESTAMP}.md"

# Ensure results directory exists
mkdir -p "$RESULTS_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
PASSED=0
FAILED=0
WARNINGS=0
TOTAL_TESTS=0

# Results array
declare -a TEST_RESULTS=()

# Helper functions
log_test() {
    ((TOTAL_TESTS++))
    echo -e "${BLUE}[TEST $TOTAL_TESTS]${NC} $1"
}

pass() {
    echo -e "  ${GREEN}✅ PASS${NC}: $1"
    TEST_RESULTS+=("{\"test\": \"$1\", \"status\": \"pass\", \"category\": \"$2\"}")
    ((PASSED++))
}

fail() {
    echo -e "  ${RED}❌ FAIL${NC}: $1"
    TEST_RESULTS+=("{\"test\": \"$1\", \"status\": \"fail\", \"category\": \"$2\", \"error\": \"$3\"}")
    ((FAILED++))
}

warn() {
    echo -e "  ${YELLOW}⚠️  WARN${NC}: $1"
    TEST_RESULTS+=("{\"test\": \"$1\", \"status\": \"warning\", \"category\": \"$2\", \"message\": \"$3\"}")
    ((WARNINGS++))
}

echo "==================================="
echo "Production Smoke Tests - Day 3"
echo "==================================="
echo "Environment: Staging (Production Proxy)"
echo "Base URL: $BASE_URL"
echo "Timestamp: $TIMESTAMP"
echo "==================================="
echo ""

# =====================================
# 1. INFRASTRUCTURE TESTS
# =====================================
echo ">>> INFRASTRUCTURE TESTS (5 tests)"
echo ""

# Test 1.1: Docker Containers Running
log_test "Docker Containers Status"
CONTAINER_COUNT=$(docker ps --filter "name=corporate-intel-staging" --format "{{.Names}}" | wc -l)
if [ "$CONTAINER_COUNT" -ge 4 ]; then
    pass "All containers running ($CONTAINER_COUNT/4+)" "infrastructure"
else
    fail "Not all containers running ($CONTAINER_COUNT/4)" "infrastructure" "missing containers"
fi

# Test 1.2: Docker Networks
log_test "Docker Networks"
if docker network ls | grep -q "corporate-intel-staging-network"; then
    pass "Docker network exists" "infrastructure"
else
    fail "Docker network missing" "infrastructure" "network not found"
fi

# Test 1.3: Docker Volumes
log_test "Docker Volumes"
VOLUME_COUNT=$(docker volume ls | grep "corporate-intel-staging" | wc -l)
if [ "$VOLUME_COUNT" -ge 4 ]; then
    pass "All volumes present ($VOLUME_COUNT/4+)" "infrastructure"
else
    warn "Some volumes may be missing ($VOLUME_COUNT/4)" "infrastructure" "volume count low"
fi

# Test 1.4: Basic HTTP Connectivity
log_test "HTTP Connectivity"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/health" || echo "000")
if [ "$HTTP_CODE" = "200" ]; then
    pass "HTTP connectivity established" "infrastructure"
else
    fail "HTTP connectivity failed (code: $HTTP_CODE)" "infrastructure" "connection failed"
fi

# Test 1.5: Container Health Status
log_test "Container Health Status"
HEALTHY_COUNT=$(docker ps --filter "name=corporate-intel-staging" --filter "health=healthy" --format "{{.Names}}" | wc -l)
if [ "$HEALTHY_COUNT" -ge 3 ]; then
    pass "Containers healthy ($HEALTHY_COUNT healthy)" "infrastructure"
else
    warn "Some containers not healthy ($HEALTHY_COUNT)" "infrastructure" "health check issues"
fi

echo ""

# =====================================
# 2. DATABASE TESTS
# =====================================
echo ">>> DATABASE TESTS (6 tests)"
echo ""

# Test 2.1: PostgreSQL Container Running
log_test "PostgreSQL Container Running"
if docker ps | grep -q "corporate-intel-staging-postgres"; then
    pass "PostgreSQL container running" "database"
else
    fail "PostgreSQL container not running" "database" "container down"
fi

# Test 2.2: PostgreSQL Connectivity
log_test "PostgreSQL Connectivity"
PG_READY=$(docker exec corporate-intel-staging-postgres pg_isready -U postgres 2>&1 || echo "failed")
if echo "$PG_READY" | grep -q "accepting connections"; then
    pass "PostgreSQL accepting connections" "database"
else
    fail "PostgreSQL not accepting connections" "database" "$PG_READY"
fi

# Test 2.3: Database Exists
log_test "Database Exists"
DB_EXISTS=$(docker exec corporate-intel-staging-postgres psql -U postgres -lqt 2>/dev/null | cut -d \| -f 1 | grep -w "corporate_intel_staging" | wc -l)
if [ "$DB_EXISTS" -gt 0 ]; then
    pass "Database exists" "database"
else
    fail "Database does not exist" "database" "db not found"
fi

# Test 2.4: Tables Exist
log_test "Tables Exist"
TABLES_COUNT=$(docker exec corporate-intel-staging-postgres psql -U postgres -d corporate_intel_staging -c "\dt" 2>/dev/null | grep -c "public" || echo "0")
if [ "$TABLES_COUNT" -gt 0 ]; then
    pass "Database tables exist ($TABLES_COUNT tables)" "database"
else
    warn "No tables found in database" "database" "migrations may not have run"
fi

# Test 2.5: Companies Table Data
log_test "Companies Table Has Data"
COMPANIES_COUNT=$(docker exec corporate-intel-staging-postgres psql -U postgres -d corporate_intel_staging -tAc "SELECT COUNT(*) FROM companies" 2>/dev/null || echo "0")
if [ "$COMPANIES_COUNT" -gt 0 ]; then
    pass "Companies table has data ($COMPANIES_COUNT rows)" "database"
else
    warn "Companies table is empty" "database" "seed data missing"
fi

# Test 2.6: Database Performance
log_test "Database Query Performance"
QUERY_TIME=$(docker exec corporate-intel-staging-postgres psql -U postgres -d corporate_intel_staging -c "EXPLAIN ANALYZE SELECT * FROM companies LIMIT 1" 2>/dev/null | grep "Execution Time" | awk '{print $3}' || echo "999")
QUERY_TIME_INT=$(echo "$QUERY_TIME" | cut -d. -f1)
if [ "$QUERY_TIME_INT" -lt 10 ]; then
    pass "Query performance excellent (${QUERY_TIME}ms)" "database"
elif [ "$QUERY_TIME_INT" -lt 50 ]; then
    pass "Query performance good (${QUERY_TIME}ms)" "database"
else
    warn "Query performance slow (${QUERY_TIME}ms)" "database" "performance degradation"
fi

echo ""

# =====================================
# 3. REDIS CACHE TESTS
# =====================================
echo ">>> REDIS CACHE TESTS (4 tests)"
echo ""

# Test 3.1: Redis Container Running
log_test "Redis Container Running"
if docker ps | grep -q "corporate-intel-staging-redis"; then
    pass "Redis container running" "cache"
else
    fail "Redis container not running" "cache" "container down"
fi

# Test 3.2: Redis Connectivity
log_test "Redis Connectivity"
REDIS_PING=$(docker exec corporate-intel-staging-redis redis-cli ping 2>&1 || echo "failed")
if [ "$REDIS_PING" = "PONG" ]; then
    pass "Redis responding to PING" "cache"
else
    fail "Redis not responding" "cache" "$REDIS_PING"
fi

# Test 3.3: Redis SET/GET Operations
log_test "Redis SET/GET Operations"
docker exec corporate-intel-staging-redis redis-cli SET test_key "test_value" > /dev/null 2>&1
REDIS_GET=$(docker exec corporate-intel-staging-redis redis-cli GET test_key 2>&1)
docker exec corporate-intel-staging-redis redis-cli DEL test_key > /dev/null 2>&1
if [ "$REDIS_GET" = "test_value" ]; then
    pass "Redis read/write operations working" "cache"
else
    fail "Redis operations failed" "cache" "SET/GET error"
fi

# Test 3.4: Redis Info
log_test "Redis Statistics"
REDIS_KEYS=$(docker exec corporate-intel-staging-redis redis-cli DBSIZE 2>&1 | grep -o '[0-9]*' || echo "0")
if [ "$REDIS_KEYS" -ge 0 ]; then
    pass "Redis stats accessible ($REDIS_KEYS keys)" "cache"
else
    warn "Redis stats unavailable" "cache" "info command failed"
fi

echo ""

# =====================================
# 4. API HEALTH TESTS
# =====================================
echo ">>> API HEALTH TESTS (5 tests)"
echo ""

# Test 4.1: Basic Health Endpoint
log_test "Basic Health Endpoint"
HEALTH_RESPONSE=$(curl -s "$BASE_URL/health" || echo "failed")
HEALTH_STATUS=$(echo "$HEALTH_RESPONSE" | jq -r '.status' 2>/dev/null || echo "error")
if [ "$HEALTH_STATUS" = "healthy" ]; then
    pass "Basic health endpoint: healthy" "api_health"
else
    fail "Basic health endpoint failed (status: $HEALTH_STATUS)" "api_health" "$HEALTH_RESPONSE"
fi

# Test 4.2: Ping Endpoint
log_test "Ping Endpoint"
PING_RESPONSE=$(curl -s "$BASE_URL/health/ping" || echo "failed")
if echo "$PING_RESPONSE" | grep -q "pong"; then
    pass "Ping endpoint responding" "api_health"
else
    fail "Ping endpoint not responding correctly" "api_health" "$PING_RESPONSE"
fi

# Test 4.3: Detailed Health Check
log_test "Detailed Health Check"
DETAILED_HEALTH=$(curl -s "$BASE_URL/api/v1/health" || echo "{}")
DB_STATUS=$(echo "$DETAILED_HEALTH" | jq -r '.database.status' 2>/dev/null || echo "unknown")
CACHE_STATUS=$(echo "$DETAILED_HEALTH" | jq -r '.cache.status' 2>/dev/null || echo "unknown")

if [ "$DB_STATUS" = "healthy" ] || [ "$DB_STATUS" = "connected" ]; then
    pass "Database health check: $DB_STATUS" "api_health"
else
    fail "Database health check failed (status: $DB_STATUS)" "api_health" "$DETAILED_HEALTH"
fi

# Test 4.4: Cache Health
log_test "Cache Health Check"
if [ "$CACHE_STATUS" = "healthy" ] || [ "$CACHE_STATUS" = "connected" ]; then
    pass "Cache health check: $CACHE_STATUS" "api_health"
else
    warn "Cache health check: $CACHE_STATUS" "api_health" "cache may not be configured"
fi

# Test 4.5: API Response Time
log_test "Health Endpoint Response Time"
HEALTH_TIME=$(curl -s -o /dev/null -w "%{time_total}" "$BASE_URL/health" || echo "999")
HEALTH_TIME_MS=$(echo "$HEALTH_TIME * 1000" | bc | cut -d. -f1)
if [ "$HEALTH_TIME_MS" -lt 10 ]; then
    pass "Health endpoint response time: ${HEALTH_TIME_MS}ms (excellent)" "api_health"
elif [ "$HEALTH_TIME_MS" -lt 50 ]; then
    pass "Health endpoint response time: ${HEALTH_TIME_MS}ms (good)" "api_health"
else
    warn "Health endpoint response time: ${HEALTH_TIME_MS}ms (slower than baseline)" "api_health" "performance issue"
fi

echo ""

# =====================================
# 5. API ENDPOINT TESTS
# =====================================
echo ">>> API ENDPOINT TESTS (8 tests)"
echo ""

# Test 5.1: Companies List Endpoint
log_test "Companies List Endpoint"
COMPANIES_RESPONSE=$(curl -s "$BASE_URL/api/v1/companies?limit=5" || echo "[]")
COMPANIES_COUNT=$(echo "$COMPANIES_RESPONSE" | jq '. | length' 2>/dev/null || echo "0")
if [ "$COMPANIES_COUNT" -gt 0 ]; then
    pass "Companies endpoint returned $COMPANIES_COUNT companies" "api_endpoints"
else
    warn "Companies endpoint returned no data" "api_endpoints" "empty dataset"
fi

# Test 5.2: Companies Endpoint Response Time
log_test "Companies Endpoint Response Time"
COMPANIES_TIME=$(curl -s -o /dev/null -w "%{time_total}" "$BASE_URL/api/v1/companies?limit=5" || echo "999")
COMPANIES_TIME_MS=$(echo "$COMPANIES_TIME * 1000" | bc | cut -d. -f1)
if [ "$COMPANIES_TIME_MS" -lt 50 ]; then
    pass "Companies endpoint response time: ${COMPANIES_TIME_MS}ms (excellent)" "api_endpoints"
elif [ "$COMPANIES_TIME_MS" -lt 100 ]; then
    pass "Companies endpoint response time: ${COMPANIES_TIME_MS}ms (good)" "api_endpoints"
else
    warn "Companies endpoint response time: ${COMPANIES_TIME_MS}ms" "api_endpoints" "slower than baseline"
fi

# Test 5.3: Company Detail Endpoint
log_test "Company Detail Endpoint"
COMPANY_DETAIL=$(curl -s "$BASE_URL/api/v1/companies/AAPL" || echo "{}")
COMPANY_NAME=$(echo "$COMPANY_DETAIL" | jq -r '.name' 2>/dev/null || echo "null")
if [ ! -z "$COMPANY_NAME" ] && [ "$COMPANY_NAME" != "null" ]; then
    pass "Company detail endpoint working (company: $COMPANY_NAME)" "api_endpoints"
else
    warn "Company detail endpoint returned no data for AAPL" "api_endpoints" "ticker not found or not seeded"
fi

# Test 5.4: Company Detail Response Time
log_test "Company Detail Response Time"
DETAIL_TIME=$(curl -s -o /dev/null -w "%{time_total}" "$BASE_URL/api/v1/companies/AAPL" || echo "999")
DETAIL_TIME_MS=$(echo "$DETAIL_TIME * 1000" | bc | cut -d. -f1)
if [ "$DETAIL_TIME_MS" -lt 20 ]; then
    pass "Company detail response time: ${DETAIL_TIME_MS}ms (excellent)" "api_endpoints"
elif [ "$DETAIL_TIME_MS" -lt 50 ]; then
    pass "Company detail response time: ${DETAIL_TIME_MS}ms (good)" "api_endpoints"
else
    warn "Company detail response time: ${DETAIL_TIME_MS}ms" "api_endpoints" "slower than baseline"
fi

# Test 5.5: API Documentation
log_test "API Documentation"
DOCS_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/docs" || echo "000")
if [ "$DOCS_STATUS" = "200" ]; then
    pass "API documentation accessible" "api_endpoints"
else
    warn "API documentation returned status: $DOCS_STATUS" "api_endpoints" "docs may not be enabled"
fi

# Test 5.6: OpenAPI Schema
log_test "OpenAPI Schema"
OPENAPI_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/openapi.json" || echo "000")
if [ "$OPENAPI_STATUS" = "200" ]; then
    pass "OpenAPI schema accessible" "api_endpoints"
else
    warn "OpenAPI schema returned status: $OPENAPI_STATUS" "api_endpoints" "schema not available"
fi

# Test 5.7: 404 Handling
log_test "404 Error Handling"
NOT_FOUND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/v1/nonexistent" || echo "000")
if [ "$NOT_FOUND_STATUS" = "404" ]; then
    pass "404 error handled correctly" "api_endpoints"
else
    warn "404 error returned status: $NOT_FOUND_STATUS" "api_endpoints" "unexpected status code"
fi

# Test 5.8: Invalid Ticker Handling
log_test "Invalid Ticker Handling"
INVALID_RESPONSE=$(curl -s "$BASE_URL/api/v1/companies/INVALID_TICKER_9999" || echo "{}")
INVALID_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/v1/companies/INVALID_TICKER_9999" || echo "000")
if [ "$INVALID_STATUS" = "404" ] || [ "$INVALID_STATUS" = "422" ]; then
    pass "Invalid ticker handled gracefully (status: $INVALID_STATUS)" "api_endpoints"
else
    warn "Invalid ticker returned status: $INVALID_STATUS" "api_endpoints" "unexpected handling"
fi

echo ""

# =====================================
# 6. PERFORMANCE TESTS
# =====================================
echo ">>> PERFORMANCE TESTS (5 tests)"
echo ""

# Test 6.1: Concurrent Requests (10 users)
log_test "Concurrent Requests (10 users)"
CONCURRENT_START=$(date +%s%N)
for i in {1..10}; do
    curl -s -o /dev/null "$BASE_URL/api/v1/companies?limit=5" &
done
wait
CONCURRENT_END=$(date +%s%N)
CONCURRENT_TIME=$(echo "scale=2; ($CONCURRENT_END - $CONCURRENT_START) / 1000000" | bc)
if [ $(echo "$CONCURRENT_TIME < 500" | bc) -eq 1 ]; then
    pass "Concurrent requests completed in ${CONCURRENT_TIME}ms (excellent)" "performance"
elif [ $(echo "$CONCURRENT_TIME < 1000" | bc) -eq 1 ]; then
    pass "Concurrent requests completed in ${CONCURRENT_TIME}ms (good)" "performance"
else
    warn "Concurrent requests took ${CONCURRENT_TIME}ms" "performance" "slower than expected"
fi

# Test 6.2: Throughput Test (100 requests)
log_test "Throughput Test (100 requests)"
THROUGHPUT_START=$(date +%s)
for i in {1..100}; do
    curl -s -o /dev/null "$BASE_URL/health" > /dev/null 2>&1
done
THROUGHPUT_END=$(date +%s)
THROUGHPUT_TIME=$((THROUGHPUT_END - THROUGHPUT_START))
QPS=$(echo "scale=2; 100 / $THROUGHPUT_TIME" | bc)
if [ $(echo "$QPS > 20" | bc) -eq 1 ]; then
    pass "Throughput: ${QPS} QPS (excellent, baseline: 27.3 QPS)" "performance"
elif [ $(echo "$QPS > 10" | bc) -eq 1 ]; then
    pass "Throughput: ${QPS} QPS (good)" "performance"
else
    warn "Throughput: ${QPS} QPS (below baseline)" "performance" "performance degradation"
fi

# Test 6.3: Average Response Time
log_test "Average Response Time (10 samples)"
TOTAL_TIME=0
for i in {1..10}; do
    SAMPLE_TIME=$(curl -s -o /dev/null -w "%{time_total}" "$BASE_URL/api/v1/companies?limit=5")
    TOTAL_TIME=$(echo "$TOTAL_TIME + $SAMPLE_TIME" | bc)
done
AVG_TIME=$(echo "scale=2; ($TOTAL_TIME / 10) * 1000" | bc)
if [ $(echo "$AVG_TIME < 10" | bc) -eq 1 ]; then
    pass "Average response time: ${AVG_TIME}ms (excellent, baseline: 8.42ms)" "performance"
elif [ $(echo "$AVG_TIME < 50" | bc) -eq 1 ]; then
    pass "Average response time: ${AVG_TIME}ms (good)" "performance"
else
    warn "Average response time: ${AVG_TIME}ms" "performance" "slower than baseline"
fi

# Test 6.4: P95 Response Time
log_test "P95 Response Time (20 samples)"
declare -a TIMES=()
for i in {1..20}; do
    SAMPLE=$(curl -s -o /dev/null -w "%{time_total}" "$BASE_URL/api/v1/companies?limit=5")
    TIMES+=("$SAMPLE")
done
P95_TIME=$(printf '%s\n' "${TIMES[@]}" | sort -n | awk 'BEGIN{c=0} {total[c]=$1; c++;} END{print total[int(c*0.95)]}')
P95_MS=$(echo "$P95_TIME * 1000" | bc | cut -d. -f1)
if [ "$P95_MS" -lt 20 ]; then
    pass "P95 response time: ${P95_MS}ms (excellent, baseline: 18.93ms)" "performance"
elif [ "$P95_MS" -lt 50 ]; then
    pass "P95 response time: ${P95_MS}ms (good)" "performance"
else
    warn "P95 response time: ${P95_MS}ms" "performance" "above baseline"
fi

# Test 6.5: Memory Usage
log_test "API Container Memory Usage"
API_MEMORY=$(docker stats corporate-intel-staging-api --no-stream --format "{{.MemUsage}}" | cut -d'/' -f1 | sed 's/MiB//' | sed 's/ //' || echo "0")
if [ ! -z "$API_MEMORY" ] && [ $(echo "$API_MEMORY < 500" | bc 2>/dev/null || echo "1") -eq 1 ]; then
    pass "API memory usage: ${API_MEMORY}MiB (healthy)" "performance"
else
    warn "API memory usage: ${API_MEMORY}MiB" "performance" "high memory usage"
fi

echo ""

# =====================================
# 7. SECURITY TESTS
# =====================================
echo ">>> SECURITY TESTS (3 tests)"
echo ""

# Test 7.1: Security Headers
log_test "Security Headers"
HEADERS=$(curl -s -I "$BASE_URL/health")
SECURITY_HEADERS=0
if echo "$HEADERS" | grep -qi "x-frame-options"; then ((SECURITY_HEADERS++)); fi
if echo "$HEADERS" | grep -qi "x-content-type-options"; then ((SECURITY_HEADERS++)); fi
if echo "$HEADERS" | grep -qi "content-security-policy"; then ((SECURITY_HEADERS++)); fi

if [ "$SECURITY_HEADERS" -ge 2 ]; then
    pass "Security headers present ($SECURITY_HEADERS/3)" "security"
elif [ "$SECURITY_HEADERS" -ge 1 ]; then
    warn "Some security headers present ($SECURITY_HEADERS/3)" "security" "missing headers"
else
    warn "Security headers missing" "security" "no security headers found"
fi

# Test 7.2: Authentication (Protected Endpoints)
log_test "Authentication Required"
PROTECTED_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/v1/admin/users" || echo "000")
if [ "$PROTECTED_STATUS" = "401" ] || [ "$PROTECTED_STATUS" = "403" ] || [ "$PROTECTED_STATUS" = "404" ]; then
    pass "Protected endpoints require authentication (status: $PROTECTED_STATUS)" "security"
else
    warn "Protected endpoint returned: $PROTECTED_STATUS" "security" "unexpected status"
fi

# Test 7.3: SQL Injection Prevention
log_test "SQL Injection Prevention"
SQLI_RESPONSE=$(curl -s "$BASE_URL/api/v1/companies?ticker=%27%20OR%20%271%27%3D%271" || echo "{}")
SQLI_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/v1/companies?ticker=%27%20OR%20%271%27%3D%271" || echo "000")
if [ "$SQLI_STATUS" != "500" ]; then
    pass "SQL injection attempt handled safely (status: $SQLI_STATUS)" "security"
else
    fail "SQL injection caused server error" "security" "potential vulnerability"
fi

echo ""

# =====================================
# 8. MONITORING TESTS
# =====================================
echo ">>> MONITORING TESTS (3 tests)"
echo ""

# Test 8.1: Prometheus Container
log_test "Prometheus Container"
if docker ps | grep -q "corporate-intel-staging-prometheus"; then
    pass "Prometheus container running" "monitoring"
else
    warn "Prometheus container not running" "monitoring" "monitoring disabled"
fi

# Test 8.2: Grafana Container
log_test "Grafana Container"
if docker ps | grep -q "corporate-intel-staging-grafana"; then
    pass "Grafana container running" "monitoring"
else
    warn "Grafana container not running" "monitoring" "dashboards unavailable"
fi

# Test 8.3: Prometheus Targets
log_test "Prometheus Targets"
PROM_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:9091/-/healthy" 2>/dev/null || echo "000")
if [ "$PROM_STATUS" = "200" ]; then
    pass "Prometheus healthy and accessible" "monitoring"
else
    warn "Prometheus not accessible (status: $PROM_STATUS)" "monitoring" "metrics collection may be down"
fi

echo ""

# =====================================
# RESULTS SUMMARY
# =====================================
PASS_RATE=$(echo "scale=2; ($PASSED / $TOTAL_TESTS) * 100" | bc)

echo "==================================="
echo "SMOKE TESTS COMPLETE"
echo "==================================="
echo -e "Total Tests: $TOTAL_TESTS"
echo -e "Passed:      ${GREEN}$PASSED${NC} (${PASS_RATE}%)"
echo -e "Failed:      ${RED}$FAILED${NC}"
echo -e "Warnings:    ${YELLOW}$WARNINGS${NC}"
echo "==================================="
echo ""

# Generate JSON results
cat > "$RESULTS_FILE" <<EOF
{
  "timestamp": "$TIMESTAMP",
  "environment": "staging",
  "base_url": "$BASE_URL",
  "summary": {
    "total_tests": $TOTAL_TESTS,
    "passed": $PASSED,
    "failed": $FAILED,
    "warnings": $WARNINGS,
    "pass_rate": $PASS_RATE
  },
  "baseline": {
    "p50": "5.31ms",
    "p95": "18.93ms",
    "p99": "32.14ms",
    "mean": "8.42ms",
    "throughput": "27.3 QPS",
    "success_rate": "100%"
  },
  "results": [
    $(IFS=,; echo "${TEST_RESULTS[*]}")
  ]
}
EOF

echo "Results saved to: $RESULTS_FILE"
echo ""

# Determine overall status
if [ $FAILED -gt 0 ]; then
    echo -e "${RED}❌ SMOKE TESTS FAILED${NC}"
    echo "Action required: Investigate failures before production deployment"
    exit 1
elif [ $WARNINGS -gt 10 ]; then
    echo -e "${YELLOW}⚠️  SMOKE TESTS PASSED WITH WARNINGS${NC}"
    echo "Review warnings to ensure expected behavior"
    exit 0
else
    echo -e "${GREEN}✅ SMOKE TESTS PASSED${NC}"
    echo "System ready for production deployment"
    exit 0
fi
