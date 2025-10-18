#!/bin/bash
# API validation script to run inside Docker container

echo "==================================================================="
echo "API ENDPOINT VALIDATION - Running from inside container"
echo "==================================================================="

API_BASE="http://localhost:8000"
RESULTS_FILE="/tmp/api_validation_results.txt"
echo "API Validation Results - $(date)" > $RESULTS_FILE
echo "==================================================================" >> $RESULTS_FILE

# Test counter
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Function to test endpoint
test_endpoint() {
    local METHOD=$1
    local ENDPOINT=$2
    local DESCRIPTION=$3
    local EXPECTED_STATUS=${4:-200}

    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo "Testing: $METHOD $ENDPOINT - $DESCRIPTION"

    # Run curl 3 times to measure latency
    RESPONSE_TIMES=()
    for i in {1..3}; do
        START=$(date +%s%3N)
        STATUS_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X $METHOD "$API_BASE$ENDPOINT" 2>/dev/null)
        END=$(date +%s%3N)
        RESPONSE_TIME=$((END - START))
        RESPONSE_TIMES+=($RESPONSE_TIME)
    done

    # Calculate average response time
    AVG_TIME=0
    for t in "${RESPONSE_TIMES[@]}"; do
        AVG_TIME=$((AVG_TIME + t))
    done
    AVG_TIME=$((AVG_TIME / 3))

    # Check status code
    if [ "$STATUS_CODE" == "$EXPECTED_STATUS" ]; then
        PASSED_TESTS=$((PASSED_TESTS + 1))
        echo "  ✓ PASSED (status: $STATUS_CODE, avg: ${AVG_TIME}ms)"
        echo "✓ $METHOD $ENDPOINT - $DESCRIPTION (${AVG_TIME}ms)" >> $RESULTS_FILE
    else
        FAILED_TESTS=$((FAILED_TESTS + 1))
        echo "  ✗ FAILED (expected: $EXPECTED_STATUS, got: $STATUS_CODE)"
        echo "✗ $METHOD $ENDPOINT - $DESCRIPTION (expected $EXPECTED_STATUS, got $STATUS_CODE)" >> $RESULTS_FILE
    fi
}

# Health endpoints
test_endpoint "GET" "/health" "Basic health check"
test_endpoint "GET" "/api/v1/health" "API v1 health check"
test_endpoint "GET" "/api/v1/health/ping" "Ping endpoint"
test_endpoint "GET" "/api/v1/health/detailed" "Detailed health check"
test_endpoint "GET" "/api/v1/health/readiness" "Readiness probe"

# Company endpoints
test_endpoint "GET" "/api/v1/companies?limit=10" "List companies with pagination"
test_endpoint "GET" "/api/v1/companies?category=k12&limit=5" "Filter companies by category"
test_endpoint "GET" "/api/v1/companies/trending/top-performers?metric=growth&limit=5" "Top performers by growth"
test_endpoint "GET" "/api/v1/companies/trending/top-performers?metric=revenue&limit=5" "Top performers by revenue"

# Metrics endpoints
test_endpoint "GET" "/api/v1/metrics?limit=10" "List financial metrics"
test_endpoint "GET" "/api/v1/metrics?metric_type=revenue&limit=5" "Filter metrics by type"

# Filings endpoints
test_endpoint "GET" "/api/v1/filings?limit=10" "List SEC filings"
test_endpoint "GET" "/api/v1/filings?filing_type=10-K&limit=5" "Filter filings by type"

# Intelligence endpoints
test_endpoint "GET" "/api/v1/intelligence?limit=10" "List market intelligence"

# Reports endpoints
test_endpoint "GET" "/api/v1/reports?limit=10" "List analysis reports"

# Error handling tests
test_endpoint "GET" "/api/v1/companies/00000000-0000-0000-0000-000000000000" "Non-existent company (404)" 404
test_endpoint "GET" "/api/v1/companies/invalid-uuid" "Invalid UUID format (422)" 422

# Authenticated endpoints (will fail without token, expected 401 or 403)
test_endpoint "GET" "/api/v1/companies/watchlist" "Watchlist (requires auth)" 401

# Summary
echo ""
echo "==================================================================="
echo "VALIDATION SUMMARY"
echo "==================================================================="
echo "Total Tests: $TOTAL_TESTS"
echo "Passed: $PASSED_TESTS"
echo "Failed: $FAILED_TESTS"
echo "Success Rate: $(echo "scale=2; $PASSED_TESTS * 100 / $TOTAL_TESTS" | bc)%"
echo ""

echo "" >> $RESULTS_FILE
echo "==================================================================" >> $RESULTS_FILE
echo "SUMMARY" >> $RESULTS_FILE
echo "Total Tests: $TOTAL_TESTS" >> $RESULTS_FILE
echo "Passed: $PASSED_TESTS" >> $RESULTS_FILE
echo "Failed: $FAILED_TESTS" >> $RESULTS_FILE
echo "Success Rate: $(echo "scale=2; $PASSED_TESTS * 100 / $TOTAL_TESTS" | bc)%" >> $RESULTS_FILE

# Output results
cat $RESULTS_FILE
