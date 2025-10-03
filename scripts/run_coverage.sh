#!/bin/bash
# Corporate Intelligence Platform - Coverage Runner Script

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}=== Corporate Intelligence Platform - Coverage Runner ===${NC}"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

if [[ -z "${VIRTUAL_ENV}" ]]; then
    echo -e "${YELLOW}Warning: No virtual environment detected${NC}"
    echo "Consider activating your venv: source .venv/bin/activate"
    echo ""
fi

echo -e "${YELLOW}Cleaning previous coverage data...${NC}"
rm -rf .coverage .coverage.* htmlcov/ coverage.xml

echo -e "${YELLOW}Running tests with coverage...${NC}"
python -m pytest \
    --cov=src \
    --cov-report=term-missing:skip-covered \
    --cov-report=html:htmlcov \
    --cov-report=xml:coverage.xml \
    --cov-branch \
    --cov-fail-under=80 \
    --verbose \
    "$@"

EXIT_CODE=$?

echo ""
echo -e "${YELLOW}=== Coverage Summary ===${NC}"
python -m coverage report --precision=2

COVERAGE=$(python -m coverage report --precision=2 | grep "TOTAL" | awk '{print $4}' | sed 's/%//')

if (( $(echo "$COVERAGE >= 80" | bc -l) )); then
    echo ""
    echo -e "${GREEN}✓ Coverage ($COVERAGE%) meets minimum threshold (80%)${NC}"
else
    echo ""
    echo -e "${RED}✗ Coverage ($COVERAGE%) below minimum threshold (80%)${NC}"
    EXIT_CODE=1
fi

echo ""
echo -e "${YELLOW}Report locations:${NC}"
echo "  • HTML Report: htmlcov/index.html"
echo "  • XML Report:  coverage.xml"
echo "  • Terminal:    (shown above)"

if [[ "$EXIT_CODE" -eq 0 ]]; then
    echo ""
    echo -e "${GREEN}View detailed HTML report:${NC}"
    if command -v open &> /dev/null; then
        echo "  open htmlcov/index.html"
    elif command -v xdg-open &> /dev/null; then
        echo "  xdg-open htmlcov/index.html"
    else
        echo "  Open htmlcov/index.html in your browser"
    fi
fi

echo ""
exit $EXIT_CODE
