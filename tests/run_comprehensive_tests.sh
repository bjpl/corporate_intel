#!/bin/bash
# Comprehensive Test Suite Runner
# This script runs all tests with coverage reporting

set -e

echo "=================================="
echo "Comprehensive Test Suite"
echo "Corporate Intelligence Platform"
echo "=================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test directories
DTO_TESTS="tests/dto"
JOB_TESTS="tests/jobs"
REFACTORING_TESTS="tests/refactoring"

echo "Test Configuration:"
echo "  - DTO Tests: $DTO_TESTS"
echo "  - Job Tests: $JOB_TESTS"
echo "  - Refactoring Tests: $REFACTORING_TESTS"
echo ""

# Function to run tests with coverage
run_tests() {
    local test_dir=$1
    local test_name=$2

    echo "${YELLOW}Running $test_name...${NC}"

    if pytest "$test_dir" -v --cov=src --cov-report=term-missing --tb=short; then
        echo "${GREEN}✓ $test_name passed${NC}"
        return 0
    else
        echo "${RED}✗ $test_name failed${NC}"
        return 1
    fi
}

# Track failures
FAILED_TESTS=""

# Run DTO tests
echo "=================================="
echo "1. Running DTO Layer Tests"
echo "=================================="
if ! run_tests "$DTO_TESTS" "DTO Tests"; then
    FAILED_TESTS="$FAILED_TESTS DTO"
fi
echo ""

# Run Job tests
echo "=================================="
echo "2. Running Job Orchestration Tests"
echo "=================================="
if ! run_tests "$JOB_TESTS" "Job Tests"; then
    FAILED_TESTS="$FAILED_TESTS Jobs"
fi
echo ""

# Run Refactoring tests
echo "=================================="
echo "3. Running Refactoring Validation Tests"
echo "=================================="
if ! run_tests "$REFACTORING_TESTS" "Refactoring Tests"; then
    FAILED_TESTS="$FAILED_TESTS Refactoring"
fi
echo ""

# Run all tests with comprehensive coverage
echo "=================================="
echo "4. Running Complete Test Suite"
echo "=================================="
echo "${YELLOW}Generating comprehensive coverage report...${NC}"

if pytest tests/ -v \
    --cov=src \
    --cov-report=html \
    --cov-report=term-missing \
    --cov-report=json \
    --cov-fail-under=90 \
    --tb=short; then
    echo "${GREEN}✓ All tests passed with 90%+ coverage${NC}"
else
    echo "${YELLOW}⚠ Some tests failed or coverage below 90%${NC}"
    FAILED_TESTS="$FAILED_TESTS Coverage"
fi
echo ""

# Generate summary
echo "=================================="
echo "Test Suite Summary"
echo "=================================="

if [ -z "$FAILED_TESTS" ]; then
    echo "${GREEN}✓ All test suites passed successfully!${NC}"
    echo ""
    echo "Coverage report generated:"
    echo "  - HTML: htmlcov/index.html"
    echo "  - JSON: coverage.json"
    echo ""
    echo "View coverage report:"
    echo "  open htmlcov/index.html"
    exit 0
else
    echo "${RED}✗ The following test suites had failures:${NC}"
    echo "${RED}  $FAILED_TESTS${NC}"
    echo ""
    echo "Please review the test output above for details."
    exit 1
fi
