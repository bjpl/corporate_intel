#!/bin/bash
# Type checking script with mypy for corporate_intel project

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Type Checking with Mypy              ${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if mypy is installed
if ! command -v mypy &> /dev/null; then
    echo -e "${RED}Error: mypy is not installed${NC}"
    echo "Install with: pip install mypy"
    exit 1
fi

# Set up paths
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC_DIR="${PROJECT_ROOT}/src"
REPORTS_DIR="${PROJECT_ROOT}/reports/type_coverage"

# Create reports directory
mkdir -p "${REPORTS_DIR}"

echo -e "${YELLOW}Running mypy type checking...${NC}"
echo ""

# Run mypy with different report formats
echo -e "${BLUE}1. Running strict type check...${NC}"
if mypy "${SRC_DIR}" \
    --config-file="${PROJECT_ROOT}/pyproject.toml" \
    --pretty \
    --show-error-codes \
    --show-error-context; then
    echo -e "${GREEN}✓ Type checking passed!${NC}"
    TYPE_CHECK_PASSED=true
else
    echo -e "${RED}✗ Type checking found issues${NC}"
    TYPE_CHECK_PASSED=false
fi

echo ""
echo -e "${BLUE}2. Generating HTML coverage report...${NC}"
mypy "${SRC_DIR}" \
    --config-file="${PROJECT_ROOT}/pyproject.toml" \
    --html-report="${REPORTS_DIR}/html" \
    --no-error-summary 2>/dev/null || true

echo -e "${GREEN}✓ HTML report generated at: ${REPORTS_DIR}/html/index.html${NC}"

echo ""
echo -e "${BLUE}3. Generating text coverage report...${NC}"
mypy "${SRC_DIR}" \
    --config-file="${PROJECT_ROOT}/pyproject.toml" \
    --txt-report="${REPORTS_DIR}/text" \
    --no-error-summary 2>/dev/null || true

echo -e "${GREEN}✓ Text report generated at: ${REPORTS_DIR}/text/index.txt${NC}"

echo ""
echo -e "${BLUE}4. Generating line-precision report...${NC}"
mypy "${SRC_DIR}" \
    --config-file="${PROJECT_ROOT}/pyproject.toml" \
    --linecount-report="${REPORTS_DIR}/linecount" \
    --no-error-summary 2>/dev/null || true

echo -e "${GREEN}✓ Line count report generated at: ${REPORTS_DIR}/linecount/linecount.txt${NC}"

echo ""
echo -e "${BLUE}5. Calculating type coverage percentage...${NC}"

# Parse linecount report for coverage percentage
if [ -f "${REPORTS_DIR}/linecount/linecount.txt" ]; then
    # Extract totals from linecount report
    TOTAL_LINES=$(grep -E "^TOTAL" "${REPORTS_DIR}/linecount/linecount.txt" | awk '{print $2}' || echo "0")
    TYPED_LINES=$(grep -E "^TOTAL" "${REPORTS_DIR}/linecount/linecount.txt" | awk '{print $3}' || echo "0")

    if [ "$TOTAL_LINES" -gt 0 ]; then
        COVERAGE=$(awk "BEGIN {printf \"%.1f\", ($TYPED_LINES / $TOTAL_LINES) * 100}")
        echo -e "${GREEN}Type Coverage: ${COVERAGE}% (${TYPED_LINES}/${TOTAL_LINES} lines)${NC}"
    fi
fi

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Type Check Summary                   ${NC}"
echo -e "${BLUE}========================================${NC}"

if [ "$TYPE_CHECK_PASSED" = true ]; then
    echo -e "${GREEN}✓ All type checks passed${NC}"
    echo -e "${GREEN}✓ Reports generated successfully${NC}"
    echo ""
    echo -e "View detailed reports at:"
    echo -e "  - HTML: ${REPORTS_DIR}/html/index.html"
    echo -e "  - Text: ${REPORTS_DIR}/text/index.txt"
    echo -e "  - Lines: ${REPORTS_DIR}/linecount/linecount.txt"
    exit 0
else
    echo -e "${RED}✗ Type checking found issues${NC}"
    echo -e "${YELLOW}Review the errors above and check reports for details${NC}"
    exit 1
fi
