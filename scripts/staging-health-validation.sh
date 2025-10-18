#!/bin/bash
# Corporate Intelligence Platform - Staging Health Validation Script
# ===================================================================
# Comprehensive health validation for Plan A Day 3
# Validates all services and creates detailed report

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

# Staging configuration
API_URL="http://localhost:8004"
POSTGRES_CONTAINER="corporate-intel-staging-postgres"
POSTGRES_USER="intel_staging_user"
POSTGRES_DB="corporate_intel_staging"
REDIS_CONTAINER="corporate-intel-staging-redis"
REDIS_PASSWORD="dev-redis-password"
PROMETHEUS_URL="http://localhost:9091"
GRAFANA_URL="http://localhost:3001"

# Results tracking
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
WARNINGS=0

# Arrays to store results
declare -a PASSED_TESTS
declare -a FAILED_TESTS
declare -a WARNING_TESTS

# Test result function
test_result() {
    local test_name=$1
    local result=$2  # "pass", "fail", or "warn"
    local details=$3

    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

    case "$result" in
        "pass")
            PASSED_CHECKS=$((PASSED_CHECKS + 1))
            PASSED_TESTS+=("$test_name: $details")
            echo -e "${GREEN}✓${NC} $test_name: ${GREEN}$details${NC}"
            ;;
        "fail")
            FAILED_CHECKS=$((FAILED_CHECKS + 1))
            FAILED_TESTS+=("$test_name: $details")
            echo -e "${RED}✗${NC} $test_name: ${RED}$details${NC}"
            ;;
        "warn")
            WARNINGS=$((WARNINGS + 1))
            WARNING_TESTS+=("$test_name: $details")
            echo -e "${YELLOW}⚠${NC} $test_name: ${YELLOW}$details${NC}"
            ;;
    esac
}

# Header
echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Plan A Day 3 - Staging Health Validation                     ║${NC}"
echo -e "${BLUE}║  Corporate Intelligence Platform                               ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}Started: $(date '+%Y-%m-%d %H:%M:%S')${NC}"
echo ""

# ============================================
# API SERVICE VALIDATION
# ============================================
echo -e "${MAGENTA}━━━ API SERVICE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Test API health endpoint
api_response=$(curl -s -w "\n%{http_code}" "$API_URL/health" 2>/dev/null)
http_code=$(echo "$api_response" | tail -n1)
api_body=$(echo "$api_response" | head -n-1)

if [ "$http_code" = "200" ]; then
    version=$(echo "$api_body" | python -c "import sys, json; print(json.load(sys.stdin).get('version', 'unknown'))" 2>/dev/null || echo "unknown")
    environment=$(echo "$api_body" | python -c "import sys, json; print(json.load(sys.stdin).get('environment', 'unknown'))" 2>/dev/null || echo "unknown")
    test_result "API Health Endpoint" "pass" "HTTP 200, v$version, env=$environment"
else
    test_result "API Health Endpoint" "fail" "HTTP $http_code"
fi

# Test API metrics
metrics_code=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/metrics/" 2>/dev/null)
if [ "$metrics_code" = "200" ]; then
    test_result "API Metrics Endpoint" "pass" "HTTP 200"
else
    test_result "API Metrics Endpoint" "fail" "HTTP $metrics_code"
fi

# Test API response time
response_time=$(curl -s -o /dev/null -w "%{time_total}" "$API_URL/health" 2>/dev/null || echo "0")
if (( $(echo "$response_time < 1.0" | bc -l 2>/dev/null || echo "0") )); then
    test_result "API Response Time" "pass" "${response_time}s (< 1s)"
elif (( $(echo "$response_time < 3.0" | bc -l 2>/dev/null || echo "0") )); then
    test_result "API Response Time" "warn" "${response_time}s (> 1s but < 3s)"
else
    test_result "API Response Time" "fail" "${response_time}s (> 3s)"
fi

echo ""

# ============================================
# DATABASE VALIDATION
# ============================================
echo -e "${MAGENTA}━━━ DATABASE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Test PostgreSQL connection
if docker exec $POSTGRES_CONTAINER pg_isready -U $POSTGRES_USER -d $POSTGRES_DB > /dev/null 2>&1; then
    test_result "PostgreSQL Connection" "pass" "Accepting connections"
else
    test_result "PostgreSQL Connection" "fail" "Not accepting connections"
fi

# Test database size
db_size=$(docker exec $POSTGRES_CONTAINER psql -U $POSTGRES_USER -d $POSTGRES_DB -t -c "SELECT pg_size_pretty(pg_database_size('$POSTGRES_DB'));" 2>/dev/null | xargs || echo "N/A")
if [ "$db_size" != "N/A" ]; then
    test_result "Database Size" "pass" "$db_size"
else
    test_result "Database Size" "fail" "Unable to retrieve"
fi

# Test connection pool
conn_count=$(docker exec $POSTGRES_CONTAINER psql -U $POSTGRES_USER -d $POSTGRES_DB -t -c "SELECT COUNT(*) FROM pg_stat_activity WHERE datname='$POSTGRES_DB';" 2>/dev/null | xargs || echo "0")
if [ "$conn_count" -gt 0 ] && [ "$conn_count" -lt 50 ]; then
    test_result "Active Connections" "pass" "$conn_count connections (healthy)"
elif [ "$conn_count" -ge 50 ]; then
    test_result "Active Connections" "warn" "$conn_count connections (high)"
else
    test_result "Active Connections" "fail" "No active connections"
fi

# Test TimescaleDB extension
timescale=$(docker exec $POSTGRES_CONTAINER psql -U $POSTGRES_USER -d $POSTGRES_DB -t -c "SELECT extversion FROM pg_extension WHERE extname='timescaledb';" 2>/dev/null | xargs || echo "")
if [ -n "$timescale" ]; then
    test_result "TimescaleDB Extension" "pass" "v$timescale installed"
else
    test_result "TimescaleDB Extension" "warn" "Not installed"
fi

# Test database tables
table_count=$(docker exec $POSTGRES_CONTAINER psql -U $POSTGRES_USER -d $POSTGRES_DB -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';" 2>/dev/null | xargs || echo "0")
if [ "$table_count" -gt 0 ]; then
    test_result "Database Tables" "pass" "$table_count tables"
else
    test_result "Database Tables" "warn" "No tables (fresh database)"
fi

echo ""

# ============================================
# REDIS CACHE VALIDATION
# ============================================
echo -e "${MAGENTA}━━━ REDIS CACHE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Test Redis ping
if docker exec $REDIS_CONTAINER redis-cli -a $REDIS_PASSWORD ping 2>/dev/null | grep -q "PONG"; then
    test_result "Redis Connection" "pass" "PONG received"
else
    test_result "Redis Connection" "fail" "No response"
fi

# Test Redis memory
redis_memory=$(docker exec $REDIS_CONTAINER redis-cli -a $REDIS_PASSWORD INFO memory 2>/dev/null | grep "used_memory_human:" | cut -d: -f2 | tr -d '\r' || echo "N/A")
if [ "$redis_memory" != "N/A" ]; then
    test_result "Redis Memory Usage" "pass" "$redis_memory"
else
    test_result "Redis Memory Usage" "fail" "Unable to retrieve"
fi

# Test Redis clients
redis_clients=$(docker exec $REDIS_CONTAINER redis-cli -a $REDIS_PASSWORD INFO clients 2>/dev/null | grep "connected_clients:" | cut -d: -f2 | tr -d '\r' || echo "0")
if [ "$redis_clients" -gt 0 ]; then
    test_result "Redis Connected Clients" "pass" "$redis_clients clients"
else
    test_result "Redis Connected Clients" "warn" "No connected clients"
fi

# Test Redis version
redis_version=$(docker exec $REDIS_CONTAINER redis-cli -a $REDIS_PASSWORD INFO server 2>/dev/null | grep "redis_version:" | cut -d: -f2 | tr -d '\r' || echo "N/A")
if [ "$redis_version" != "N/A" ]; then
    test_result "Redis Version" "pass" "v$redis_version"
else
    test_result "Redis Version" "fail" "Unable to retrieve"
fi

echo ""

# ============================================
# MONITORING VALIDATION
# ============================================
echo -e "${MAGENTA}━━━ MONITORING ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Test Prometheus
prom_code=$(curl -s -o /dev/null -w "%{http_code}" "$PROMETHEUS_URL/-/healthy" 2>/dev/null)
if [ "$prom_code" = "200" ]; then
    test_result "Prometheus Health" "pass" "HTTP 200"
else
    test_result "Prometheus Health" "fail" "HTTP $prom_code"
fi

# Test Prometheus targets
targets_up=$(curl -s "$PROMETHEUS_URL/api/v1/targets" 2>/dev/null | python -c "import sys, json; data=json.load(sys.stdin); print(sum(1 for t in data['data']['activeTargets'] if t['health']=='up'))" 2>/dev/null || echo "0")
targets_total=$(curl -s "$PROMETHEUS_URL/api/v1/targets" 2>/dev/null | python -c "import sys, json; data=json.load(sys.stdin); print(len(data['data']['activeTargets']))" 2>/dev/null || echo "0")
if [ "$targets_total" -gt 0 ]; then
    if [ "$targets_up" -eq "$targets_total" ]; then
        test_result "Prometheus Targets" "pass" "All $targets_total targets UP"
    elif [ "$targets_up" -gt 0 ]; then
        test_result "Prometheus Targets" "warn" "$targets_up/$targets_total targets UP"
    else
        test_result "Prometheus Targets" "fail" "0/$targets_total targets UP"
    fi
else
    test_result "Prometheus Targets" "warn" "No targets configured"
fi

# Test Grafana
grafana_code=$(curl -s -o /dev/null -w "%{http_code}" "$GRAFANA_URL/api/health" 2>/dev/null)
if [ "$grafana_code" = "200" ]; then
    grafana_version=$(curl -s "$GRAFANA_URL/api/health" 2>/dev/null | python -c "import sys, json; print(json.load(sys.stdin).get('version', 'unknown'))" 2>/dev/null || echo "unknown")
    test_result "Grafana Health" "pass" "HTTP 200, v$grafana_version"
else
    test_result "Grafana Health" "fail" "HTTP $grafana_code"
fi

echo ""

# ============================================
# DOCKER CONTAINER VALIDATION
# ============================================
echo -e "${MAGENTA}━━━ DOCKER CONTAINERS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Check each container
for container in corporate-intel-staging-api corporate-intel-staging-postgres corporate-intel-staging-redis corporate-intel-staging-prometheus corporate-intel-staging-grafana; do
    if docker ps --format "{{.Names}}" | grep -q "^${container}$"; then
        # Check health status
        health=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "no-health-check")

        case "$health" in
            "healthy")
                test_result "Container: $container" "pass" "HEALTHY"
                ;;
            "unhealthy")
                test_result "Container: $container" "fail" "UNHEALTHY"
                ;;
            "starting")
                test_result "Container: $container" "warn" "STARTING"
                ;;
            "no-health-check")
                # If no health check, check if running
                running=$(docker inspect --format='{{.State.Running}}' "$container" 2>/dev/null)
                if [ "$running" = "true" ]; then
                    test_result "Container: $container" "pass" "RUNNING (no health check)"
                else
                    test_result "Container: $container" "fail" "NOT RUNNING"
                fi
                ;;
        esac
    else
        test_result "Container: $container" "fail" "NOT FOUND"
    fi
done

echo ""

# ============================================
# SUMMARY
# ============================================
echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  VALIDATION SUMMARY                                            ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  Total Checks:    $TOTAL_CHECKS"
echo -e "  ${GREEN}Passed:          $PASSED_CHECKS${NC}"
echo -e "  ${YELLOW}Warnings:        $WARNINGS${NC}"
echo -e "  ${RED}Failed:          $FAILED_CHECKS${NC}"
echo ""

# Calculate success rate
if [ $TOTAL_CHECKS -gt 0 ]; then
    success_rate=$((PASSED_CHECKS * 100 / TOTAL_CHECKS))
    echo -e "  Success Rate:    ${success_rate}%"
fi

echo ""

# Print failed tests if any
if [ ${#FAILED_TESTS[@]} -gt 0 ]; then
    echo -e "${RED}Failed Tests:${NC}"
    for test in "${FAILED_TESTS[@]}"; do
        echo -e "  ${RED}✗${NC} $test"
    done
    echo ""
fi

# Print warnings if any
if [ ${#WARNING_TESTS[@]} -gt 0 ]; then
    echo -e "${YELLOW}Warnings:${NC}"
    for test in "${WARNING_TESTS[@]}"; do
        echo -e "  ${YELLOW}⚠${NC} $test"
    done
    echo ""
fi

# Final verdict
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
if [ $FAILED_CHECKS -eq 0 ]; then
    echo -e "${GREEN}✓ ALL HEALTH CHECKS PASSED${NC}"
    if [ $WARNINGS -gt 0 ]; then
        echo -e "${YELLOW}  ($WARNINGS warnings to review)${NC}"
    fi
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    exit 0
else
    echo -e "${RED}✗ HEALTH CHECK FAILED${NC}"
    echo -e "${RED}  $FAILED_CHECKS test(s) failed${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    exit 1
fi
