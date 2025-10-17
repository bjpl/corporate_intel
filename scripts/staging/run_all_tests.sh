#!/bin/bash
# Run all staging tests in sequence
# Usage: ./scripts/staging/run_all_tests.sh [staging_url]

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
STAGING_URL="${1:-http://localhost:8000}"
STAGING_DASHBOARD_URL="${STAGING_DASHBOARD_URL:-http://localhost:8050}"
STAGING_DATABASE_URL="${STAGING_DATABASE_URL:-postgresql://user:pass@localhost:5432/corporate_intel_staging}"
STAGING_REDIS_URL="${STAGING_REDIS_URL:-redis://localhost:6379/0}"

# Test results directory
RESULTS_DIR="tests/staging/results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p "$RESULTS_DIR"

# Export environment variables
export STAGING_API_URL="$STAGING_URL"
export STAGING_DASHBOARD_URL="$STAGING_DASHBOARD_URL"
export STAGING_DATABASE_URL="$STAGING_DATABASE_URL"
export STAGING_REDIS_URL="$STAGING_REDIS_URL"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}CORPORATE INTEL STAGING TEST SUITE${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "Staging URL: ${YELLOW}$STAGING_URL${NC}"
echo -e "Dashboard URL: ${YELLOW}$STAGING_DASHBOARD_URL${NC}"
echo -e "Database URL: ${YELLOW}$STAGING_DATABASE_URL${NC}"
echo -e "Redis URL: ${YELLOW}$STAGING_REDIS_URL${NC}"
echo -e "Results Directory: ${YELLOW}$RESULTS_DIR${NC}"
echo ""

# Test counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Function to run a test suite
run_test_suite() {
    local name=$1
    local test_file=$2
    local report_file="$RESULTS_DIR/${name}_${TIMESTAMP}.xml"
    local log_file="$RESULTS_DIR/${name}_${TIMESTAMP}.log"

    echo -e "${BLUE}----------------------------------------${NC}"
    echo -e "${BLUE}Running: $name${NC}"
    echo -e "${BLUE}----------------------------------------${NC}"

    if pytest "$test_file" -v --junitxml="$report_file" --tb=short 2>&1 | tee "$log_file"; then
        echo -e "${GREEN}✓ $name PASSED${NC}"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo -e "${RED}✗ $name FAILED${NC}"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi

    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo ""
}

# Function to run load tests with Locust
run_load_tests() {
    local name="Load Tests"
    local test_file="tests/staging/test_load.py"
    local report_file="$RESULTS_DIR/load_test_${TIMESTAMP}.html"

    echo -e "${BLUE}----------------------------------------${NC}"
    echo -e "${BLUE}Running: $name${NC}"
    echo -e "${BLUE}----------------------------------------${NC}"

    # Run Locust in headless mode
    # 10 users, spawn rate 2/sec, run for 2 minutes
    if locust -f "$test_file" \
        --host="$STAGING_URL" \
        --users=10 \
        --spawn-rate=2 \
        --run-time=2m \
        --headless \
        --html="$report_file" \
        --csv="$RESULTS_DIR/load_test_${TIMESTAMP}"; then
        echo -e "${GREEN}✓ $name PASSED${NC}"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo -e "${RED}✗ $name FAILED${NC}"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi

    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo ""
}

# Start time
START_TIME=$(date +%s)

# 1. Smoke Tests (Quick validation)
echo -e "${YELLOW}PHASE 1: SMOKE TESTS${NC}"
echo ""
run_test_suite "Smoke Tests" "tests/staging/test_smoke.py"

# If smoke tests failed, stop here
if [ $FAILED_TESTS -gt 0 ]; then
    echo -e "${RED}❌ Smoke tests failed. Stopping test suite.${NC}"
    exit 1
fi

# 2. Integration Tests
echo -e "${YELLOW}PHASE 2: INTEGRATION TESTS${NC}"
echo ""
run_test_suite "Integration Tests" "tests/staging/test_integration.py"

# 3. Security Tests
echo -e "${YELLOW}PHASE 3: SECURITY TESTS${NC}"
echo ""
run_test_suite "Security Tests" "tests/staging/test_security.py"

# 4. Performance Tests
echo -e "${YELLOW}PHASE 4: PERFORMANCE BENCHMARKS${NC}"
echo ""
run_test_suite "Performance Tests" "tests/staging/test_performance.py"

# 5. Load Tests (using Locust)
echo -e "${YELLOW}PHASE 5: LOAD TESTS${NC}"
echo ""

# Check if Locust is installed
if command -v locust &> /dev/null; then
    run_load_tests
else
    echo -e "${YELLOW}⚠ Locust not installed. Skipping load tests.${NC}"
    echo -e "${YELLOW}Install with: pip install locust${NC}"
    echo ""
fi

# End time
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

# Generate summary report
SUMMARY_FILE="$RESULTS_DIR/summary_${TIMESTAMP}.txt"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}TEST SUMMARY${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "Total Test Suites: ${YELLOW}$TOTAL_TESTS${NC}"
echo -e "Passed: ${GREEN}$PASSED_TESTS${NC}"
echo -e "Failed: ${RED}$FAILED_TESTS${NC}"
echo -e "Duration: ${YELLOW}${DURATION}s${NC}"
echo ""

# Write summary to file
cat > "$SUMMARY_FILE" <<EOF
CORPORATE INTEL STAGING TEST SUMMARY
=====================================

Timestamp: $(date)
Staging URL: $STAGING_URL
Dashboard URL: $STAGING_DASHBOARD_URL

Test Suites Run: $TOTAL_TESTS
Passed: $PASSED_TESTS
Failed: $FAILED_TESTS
Duration: ${DURATION}s

Results Directory: $RESULTS_DIR

Details:
EOF

# Append test results
for log in "$RESULTS_DIR"/*_${TIMESTAMP}.log; do
    if [ -f "$log" ]; then
        echo "- $(basename "$log")" >> "$SUMMARY_FILE"
    fi
done

echo -e "Summary saved to: ${YELLOW}$SUMMARY_FILE${NC}"
echo ""

# Exit code based on results
if [ $FAILED_TESTS -gt 0 ]; then
    echo -e "${RED}❌ STAGING TESTS FAILED${NC}"
    echo -e "${RED}Review logs in: $RESULTS_DIR${NC}"
    exit 1
else
    echo -e "${GREEN}✅ ALL STAGING TESTS PASSED${NC}"
    echo -e "${GREEN}Staging environment validated successfully!${NC}"
    exit 0
fi
