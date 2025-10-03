#!/bin/bash
# Dependency Verification Script for Corporate Intelligence Platform
# Verifies installed packages, versions, and import capabilities

set -e

echo "========================================"
echo "CORPORATE INTEL - DEPENDENCY VERIFICATION"
echo "========================================"
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Python version
echo "1. Python Version Check"
echo "   Expected: Python 3.10+"
python_version=$(python --version 2>&1 | cut -d' ' -f2)
echo "   Found: Python $python_version"
echo ""

# Check pip version
echo "2. Pip Version Check"
pip_version=$(pip --version | cut -d' ' -f2)
echo "   Found: pip $python_version"
echo ""

# List installed packages
echo "3. Installed Packages"
echo "   Saving package list to logs/installed-packages.txt"
pip list > logs/installed-packages.txt
echo "   Total packages: $(pip list | wc -l)"
echo ""

# Check critical packages with versions
echo "4. Critical Package Version Check"
echo ""

critical_packages=(
    "fastapi"
    "uvicorn"
    "pydantic"
    "sqlalchemy"
    "asyncpg"
    "pandas"
    "numpy"
    "prefect"
    "ray"
    "redis"
    "opentelemetry-api"
    "loguru"
    "pytest"
)

for package in "${critical_packages[@]}"; do
    if pip show "$package" > /dev/null 2>&1; then
        version=$(pip show "$package" | grep "Version:" | cut -d' ' -f2)
        echo -e "   ${GREEN}✓${NC} $package ($version)"
    else
        echo -e "   ${RED}✗${NC} $package (NOT INSTALLED)"
    fi
done

echo ""
echo "5. Running Python Import Tests"
echo "   Testing all critical imports..."
echo ""

# Run Python import verification
if python scripts/verify-imports.py; then
    echo -e "${GREEN}✓ All imports successful!${NC}"
else
    echo -e "${RED}✗ Some imports failed!${NC}"
    exit 1
fi

echo ""
echo "6. Package Dependency Check"
echo "   Checking for dependency conflicts..."
pip check

echo ""
echo "========================================"
echo "VERIFICATION COMPLETE"
echo "========================================"
echo ""
echo "Logs saved to:"
echo "  - logs/install-main.log"
echo "  - logs/install-dev.log"
echo "  - logs/install-editable.log"
echo "  - logs/installed-packages.txt"
echo ""
