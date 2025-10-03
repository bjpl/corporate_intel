#!/bin/bash
# Corporate Intelligence Platform - Quick Coverage Check

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}=== Quick Coverage Check ===${NC}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

python -m pytest \
    --cov=src \
    --cov-report=term-missing:skip-covered \
    --cov-fail-under=80 \
    --quiet \
    --tb=line \
    -x \
    2>&1 | grep -E "(TOTAL|FAILED|ERROR)" || true

COVERAGE=$(python -m coverage report --precision=2 2>/dev/null | grep "TOTAL" | awk '{print $4}' | sed 's/%//' || echo "0")

echo ""
if (( $(echo "$COVERAGE >= 80" | bc -l) )); then
    echo -e "${GREEN}✓ Coverage: $COVERAGE% (threshold: 80%)${NC}"
    exit 0
else
    echo -e "${RED}✗ Coverage: $COVERAGE% (threshold: 80%)${NC}"
    echo -e "${YELLOW}Run './scripts/run_coverage.sh' for detailed report${NC}"
    exit 1
fi
