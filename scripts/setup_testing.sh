#!/bin/bash

# User Testing Setup Script
# This script automates the setup process for user testing

set -e  # Exit on error

echo "=========================================="
echo "Corporate Intelligence Platform"
echo "User Testing Setup Script"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_step() {
    echo ""
    echo "=========================================="
    echo "$1"
    echo "=========================================="
}

# Check prerequisites
print_step "Step 1: Checking Prerequisites"

# Check Docker
if command -v docker &> /dev/null; then
    print_success "Docker is installed"
else
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

# Check Docker Compose
if command -v docker-compose &> /dev/null; then
    print_success "Docker Compose is installed"
else
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Check Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    print_success "Python is installed (version $PYTHON_VERSION)"
else
    print_error "Python 3 is not installed. Please install Python 3.11+ first."
    exit 1
fi

# Check if .env exists
print_step "Step 2: Environment Configuration"

if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        echo "Creating .env file from .env.example..."
        cp .env.example .env
        print_success ".env file created"
        print_warning "Please edit .env file with your configuration before continuing"
        echo ""
        echo "Press Enter to continue after editing .env, or Ctrl+C to exit..."
        read
    else
        print_error ".env.example not found. Cannot create .env file."
        exit 1
    fi
else
    print_success ".env file exists"
fi

# Start Docker services
print_step "Step 3: Starting Infrastructure Services"

echo "Starting PostgreSQL, Redis, MinIO, Ray, Grafana, Prometheus..."
docker-compose up -d

echo "Waiting 30 seconds for services to initialize..."
sleep 30

# Check if services are running
print_success "Services started"

echo ""
echo "Verifying services..."
docker-compose ps

# Create virtual environment
print_step "Step 4: Python Environment Setup"

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    print_success "Virtual environment created"
else
    print_success "Virtual environment already exists"
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing Python dependencies..."
pip install -e . --quiet
print_success "Dependencies installed"

# Database setup
print_step "Step 5: Database Initialization"

echo "Running database migrations..."
alembic upgrade head
print_success "Migrations completed"

# Bootstrap real data
print_step "Step 6: Bootstrap Real Test Data"

echo "Bootstrapping REAL EdTech company data from APIs..."
echo "(This will fetch live data from Yahoo Finance, SEC EDGAR, etc.)"
echo ""

if python scripts/bootstrap_test_data.py; then
    print_success "Real data bootstrapped successfully!"
else
    print_warning "Bootstrap had issues, but you can run it manually later:"
    echo "  python scripts/bootstrap_test_data.py"
fi

# Summary
print_step "Setup Complete!"

echo ""
echo "=========================================="
echo "🎉 User Testing Environment Ready!"
echo "=========================================="
echo ""
echo "Next Steps:"
echo ""
echo "1. Start the API server (in a new terminal):"
echo "   $ source venv/bin/activate"
echo "   $ uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000"
echo ""
echo "2. (Optional) Start the dashboard (in another terminal):"
echo "   $ source venv/bin/activate"
echo "   $ python -m src.visualization.dash_app"
echo ""
echo "3. Access the application:"
echo "   • API Docs:  http://localhost:8000/api/v1/docs"
echo "   • Health:    http://localhost:8000/health"
echo "   • Dashboard: http://localhost:8050"
echo "   • Grafana:   http://localhost:3000 (admin/admin)"
echo "   • Ray:       http://localhost:8265"
echo ""
echo "4. Review the testing documentation:"
echo "   • Main Guide: USER_TESTING_GUIDE.md"
echo "   • Checklist:  USER_TESTING_CHECKLIST.md"
echo "   • Bug Template: BUG_REPORT_TEMPLATE.md"
echo "   • Test Data:  TEST_DATA.md"
echo ""
echo "5. Start testing and document your findings!"
echo ""
echo "=========================================="
echo "Useful Commands:"
echo "=========================================="
echo ""
echo "# Check service status"
echo "docker-compose ps"
echo ""
echo "# View service logs"
echo "docker-compose logs -f [service_name]"
echo ""
echo "# Stop all services"
echo "docker-compose down"
echo ""
echo "# Connect to database"
echo "psql \$DATABASE_URL"
echo ""
echo "=========================================="
echo ""
echo "Happy Testing! 🚀"
echo ""
