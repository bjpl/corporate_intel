#!/bin/bash
# Real-World Data Ingestion Test Runner
#
# This script runs real-world integration tests that call actual APIs.
#
# PREREQUISITES:
# - Valid API keys in .env file
# - Working database connection
# - Internet connectivity
#
# USAGE:
#   ./scripts/run_real_world_tests.sh [options]
#
# OPTIONS:
#   --full        Run all tests including slow tests
#   --sec         Run only SEC tests
#   --yahoo       Run only Yahoo Finance tests
#   --alpha       Run only Alpha Vantage tests
#   --quick       Run quick smoke tests only
#   --report      Generate detailed report
#
# EXAMPLES:
#   ./scripts/run_real_world_tests.sh --quick
#   ./scripts/run_real_world_tests.sh --sec --yahoo
#   ./scripts/run_real_world_tests.sh --full --report

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default options
RUN_SEC=false
RUN_YAHOO=false
RUN_ALPHA=false
RUN_QUICK=false
RUN_FULL=false
GENERATE_REPORT=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --full)
            RUN_FULL=true
            RUN_SEC=true
            RUN_YAHOO=true
            RUN_ALPHA=true
            shift
            ;;
        --sec)
            RUN_SEC=true
            shift
            ;;
        --yahoo)
            RUN_YAHOO=true
            shift
            ;;
        --alpha)
            RUN_ALPHA=true
            shift
            ;;
        --quick)
            RUN_QUICK=true
            shift
            ;;
        --report)
            GENERATE_REPORT=true
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# If no specific tests selected, run quick tests
if [ "$RUN_SEC" = false ] && [ "$RUN_YAHOO" = false ] && [ "$RUN_ALPHA" = false ] && [ "$RUN_QUICK" = false ]; then
    echo -e "${YELLOW}No tests specified, running quick smoke tests${NC}"
    RUN_QUICK=true
fi

echo "=============================================================================="
echo "Real-World Data Ingestion Tests"
echo "=============================================================================="
echo ""

# Check environment setup
echo -e "${YELLOW}Checking prerequisites...${NC}"

# Check .env file
if [ ! -f .env ]; then
    echo -e "${RED}ERROR: .env file not found${NC}"
    echo "Please create .env file with required API keys:"
    echo "  SEC_USER_AGENT=YourName your@email.com"
    echo "  ALPHA_VANTAGE_API_KEY=your_key (optional)"
    exit 1
fi

# Check SEC_USER_AGENT
if ! grep -q "SEC_USER_AGENT" .env; then
    echo -e "${RED}ERROR: SEC_USER_AGENT not configured in .env${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Environment configured${NC}"

# Check database connectivity
echo -e "${YELLOW}Checking database connection...${NC}"
python -c "
from src.db.session import get_session_factory
import asyncio

async def test_db():
    factory = get_session_factory()
    async with factory() as session:
        await session.execute('SELECT 1')

asyncio.run(test_db())
print('✓ Database connection successful')
" || {
    echo -e "${RED}ERROR: Database connection failed${NC}"
    exit 1
}

echo ""
echo "=============================================================================="
echo "Starting Tests"
echo "=============================================================================="
echo ""

# Create results directory
mkdir -p test-results

# Quick tests
if [ "$RUN_QUICK" = true ]; then
    echo -e "${YELLOW}Running quick smoke tests...${NC}"
    pytest tests/integration/test_real_world_ingestion.py::TestRealWorldSECIngestion::test_sec_api_connectivity \
           tests/integration/test_real_world_ingestion.py::TestRealWorldYahooFinanceIngestion::test_yahoo_finance_api_connectivity \
           --real-world \
           -v \
           --tb=short \
           --junit-xml=test-results/quick-tests.xml || {
        echo -e "${RED}Quick tests failed${NC}"
        exit 1
    }
    echo -e "${GREEN}✓ Quick tests passed${NC}"
fi

# SEC tests
if [ "$RUN_SEC" = true ]; then
    echo ""
    echo -e "${YELLOW}Running SEC EDGAR tests...${NC}"
    pytest tests/integration/test_real_world_ingestion.py::TestRealWorldSECIngestion \
           --real-world \
           -v \
           --tb=short \
           --junit-xml=test-results/sec-tests.xml || {
        echo -e "${RED}SEC tests failed${NC}"
        exit 1
    }
    echo -e "${GREEN}✓ SEC tests passed${NC}"
fi

# Yahoo Finance tests
if [ "$RUN_YAHOO" = true ]; then
    echo ""
    echo -e "${YELLOW}Running Yahoo Finance tests...${NC}"
    pytest tests/integration/test_real_world_ingestion.py::TestRealWorldYahooFinanceIngestion \
           --real-world \
           -v \
           --tb=short \
           --junit-xml=test-results/yahoo-tests.xml || {
        echo -e "${RED}Yahoo Finance tests failed${NC}"
        exit 1
    }
    echo -e "${GREEN}✓ Yahoo Finance tests passed${NC}"
fi

# Alpha Vantage tests
if [ "$RUN_ALPHA" = true ]; then
    echo ""
    echo -e "${YELLOW}Running Alpha Vantage tests...${NC}"

    # Check if API key is configured
    if ! grep -q "ALPHA_VANTAGE_API_KEY" .env || grep -q "ALPHA_VANTAGE_API_KEY=$" .env; then
        echo -e "${YELLOW}⚠ Alpha Vantage API key not configured, skipping tests${NC}"
    else
        pytest tests/integration/test_real_world_ingestion.py::TestRealWorldAlphaVantageIngestion \
               --real-world \
               -v \
               --tb=short \
               --junit-xml=test-results/alpha-tests.xml || {
            echo -e "${RED}Alpha Vantage tests failed${NC}"
            exit 1
        }
        echo -e "${GREEN}✓ Alpha Vantage tests passed${NC}"
    fi
fi

# Cross-source consistency tests
if [ "$RUN_FULL" = true ]; then
    echo ""
    echo -e "${YELLOW}Running cross-source consistency tests...${NC}"
    pytest tests/integration/test_real_world_ingestion.py::TestCrossSourceConsistency \
           --real-world \
           -v \
           --tb=short \
           --junit-xml=test-results/consistency-tests.xml || {
        echo -e "${RED}Consistency tests failed${NC}"
        exit 1
    }
    echo -e "${GREEN}✓ Consistency tests passed${NC}"
fi

# Generate report
if [ "$GENERATE_REPORT" = true ]; then
    echo ""
    echo -e "${YELLOW}Generating data quality report...${NC}"
    pytest tests/integration/test_real_world_ingestion.py::TestDataQualityReport::test_generate_data_quality_report \
           --real-world \
           -v \
           -s \
           --tb=short || {
        echo -e "${RED}Report generation failed${NC}"
        exit 1
    }
    echo -e "${GREEN}✓ Report generated${NC}"
fi

echo ""
echo "=============================================================================="
echo -e "${GREEN}All tests completed successfully!${NC}"
echo "=============================================================================="
echo ""
echo "Results saved to: test-results/"
echo ""

# Summary
if [ "$GENERATE_REPORT" = true ]; then
    echo "Next steps:"
    echo "  1. Review test results in test-results/"
    echo "  2. Check data quality report output above"
    echo "  3. Address any data quality issues identified"
fi

exit 0
