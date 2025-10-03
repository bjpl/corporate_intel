#!/usr/bin/env bash
# Python version checker for Corporate Intelligence Platform
# Ensures Python 3.10+ is installed

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

MIN_PYTHON_VERSION="3.10"
REQUIRED_VERSION_MAJOR=3
REQUIRED_VERSION_MINOR=10

echo "Corporate Intelligence Platform - Python Version Check"
echo "======================================================="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo -e "${RED}ERROR: Python is not installed!${NC}"
    echo ""
    echo "Please install Python 3.10 or higher."
    echo "Visit: https://www.python.org/downloads/"
    exit 1
fi

# Get Python version
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
else
    PYTHON_CMD="python"
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

echo "Detected Python version: $PYTHON_VERSION"
echo ""

# Check version requirement
if [ "$PYTHON_MAJOR" -lt "$REQUIRED_VERSION_MAJOR" ] || \
   ([ "$PYTHON_MAJOR" -eq "$REQUIRED_VERSION_MAJOR" ] && [ "$PYTHON_MINOR" -lt "$REQUIRED_VERSION_MINOR" ]); then
    echo -e "${RED}ERROR: Python version $PYTHON_VERSION is too old!${NC}"
    echo ""
    echo "This project requires Python $MIN_PYTHON_VERSION or higher."
    echo "Current version: $PYTHON_VERSION"
    echo ""
    echo -e "${YELLOW}Please upgrade Python:${NC}"
    echo ""
    echo "macOS (Homebrew):"
    echo "  brew install python@3.10"
    echo ""
    echo "Ubuntu/Debian:"
    echo "  sudo apt update"
    echo "  sudo apt install python3.10 python3.10-venv python3.10-dev"
    echo ""
    echo "Windows:"
    echo "  Download from https://www.python.org/downloads/"
    echo ""
    exit 1
fi

echo -e "${GREEN}✓ Python version check passed!${NC}"
echo ""

# Check for virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}WARNING: Not running in a virtual environment${NC}"
    echo ""
    echo "It's recommended to use a virtual environment:"
    echo "  python3 -m venv venv"
    echo "  source venv/bin/activate  # On Windows: venv\\Scripts\\activate"
    echo ""
else
    echo -e "${GREEN}✓ Running in virtual environment: $VIRTUAL_ENV${NC}"
    echo ""
fi

# Check pip version
PIP_VERSION=$($PYTHON_CMD -m pip --version 2>&1 | awk '{print $2}')
echo "pip version: $PIP_VERSION"
echo ""

# Optional: Check if required packages can be installed
echo "Checking critical dependencies..."
CRITICAL_PACKAGES=("fastapi" "pydantic>=2.0" "sqlalchemy>=2.0")

for pkg in "${CRITICAL_PACKAGES[@]}"; do
    pkg_name=$(echo $pkg | cut -d'>' -f1 | cut -d'=' -f1)
    if $PYTHON_CMD -c "import $pkg_name" 2>/dev/null; then
        echo -e "  ${GREEN}✓${NC} $pkg_name installed"
    else
        echo -e "  ${YELLOW}⚠${NC} $pkg_name not installed (will be installed during setup)"
    fi
done

echo ""
echo -e "${GREEN}Python environment check complete!${NC}"
echo ""
echo "Next steps:"
echo "  1. Create virtual environment: python3 -m venv venv"
echo "  2. Activate it: source venv/bin/activate"
echo "  3. Install dependencies: pip install -e ."
echo ""

exit 0
