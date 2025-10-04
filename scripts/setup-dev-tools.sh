#!/bin/bash
# Development Tools Setup Script
# Corporate Intelligence Platform

set -e

echo "========================================="
echo "Development Tools Setup"
echo "========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Python version
echo -e "\n${YELLOW}Checking Python version...${NC}"
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.10"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo -e "${RED}Error: Python $required_version or higher required. Found: $python_version${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python $python_version${NC}"

# Install development dependencies
echo -e "\n${YELLOW}Installing development dependencies...${NC}"
pip install -q -r requirements-dev.txt
echo -e "${GREEN}✓ Development dependencies installed${NC}"

# Install pre-commit hooks
echo -e "\n${YELLOW}Setting up pre-commit hooks...${NC}"
if command -v pre-commit &> /dev/null; then
    pre-commit install
    echo -e "${GREEN}✓ Pre-commit hooks installed${NC}"

    # Test hooks
    echo -e "\n${YELLOW}Testing pre-commit hooks...${NC}"
    pre-commit run --all-files || echo -e "${YELLOW}Some hooks need fixes (this is normal on first run)${NC}"
else
    echo -e "${RED}Warning: pre-commit not found. Installing...${NC}"
    pip install pre-commit
    pre-commit install
    echo -e "${GREEN}✓ Pre-commit installed and configured${NC}"
fi

# Install package in development mode
echo -e "\n${YELLOW}Installing package in development mode...${NC}"
pip install -e .
echo -e "${GREEN}✓ Package installed in editable mode${NC}"

# Verify installations
echo -e "\n${YELLOW}Verifying installations...${NC}"
tools=("black" "ruff" "mypy" "pytest" "bandit")
all_good=true

for tool in "${tools[@]}"; do
    if command -v $tool &> /dev/null; then
        version=$($tool --version 2>&1 | head -n1)
        echo -e "${GREEN}✓ $tool: $version${NC}"
    else
        echo -e "${RED}✗ $tool not found${NC}"
        all_good=false
    fi
done

# Check Docker
echo -e "\n${YELLOW}Checking Docker installation...${NC}"
if command -v docker &> /dev/null; then
    docker_version=$(docker --version)
    echo -e "${GREEN}✓ Docker: $docker_version${NC}"

    if command -v docker-compose &> /dev/null; then
        compose_version=$(docker-compose --version)
        echo -e "${GREEN}✓ Docker Compose: $compose_version${NC}"
    else
        echo -e "${YELLOW}! Docker Compose not found (optional)${NC}"
    fi
else
    echo -e "${YELLOW}! Docker not found (optional for local development)${NC}"
fi

# Summary
echo -e "\n========================================="
if [ "$all_good" = true ]; then
    echo -e "${GREEN}✓ All development tools installed successfully!${NC}"
    echo -e "\nNext steps:"
    echo -e "  1. Copy .env.example to .env and configure"
    echo -e "  2. Run: docker-compose -f docker-compose.dev.yml up -d"
    echo -e "  3. Run: alembic upgrade head"
    echo -e "  4. Run: pytest tests/"
    echo -e "  5. Start development: uvicorn src.main:app --reload"
else
    echo -e "${RED}Some tools failed to install. Please check errors above.${NC}"
    exit 1
fi
echo "========================================="
