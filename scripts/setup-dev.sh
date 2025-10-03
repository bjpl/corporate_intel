#!/bin/bash
# Corporate Intel Development Environment Setup Script
# This script sets up a complete development environment

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${APP_DIR}/venv"
PYTHON_VERSION="${PYTHON_VERSION:-3.11}"

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check system requirements
check_system() {
    log_info "Checking system requirements..."

    # Check Python version
    if ! command -v python3 >/dev/null 2>&1; then
        log_error "Python 3 is not installed"
        exit 1
    fi

    PYTHON_INSTALLED=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
    log_info "Found Python $PYTHON_INSTALLED"

    # Check PostgreSQL
    if ! command -v psql >/dev/null 2>&1; then
        log_warning "PostgreSQL client not found in PATH"
        log_info "Please ensure PostgreSQL is installed"
    else
        log_success "PostgreSQL client found"
    fi

    # Check Git
    if ! command -v git >/dev/null 2>&1; then
        log_warning "Git not found (recommended for version control)"
    else
        log_success "Git found"
    fi

    log_success "System requirements check complete"
}

# Create virtual environment
create_virtualenv() {
    log_info "Setting up virtual environment..."

    if [ -d "$VENV_DIR" ]; then
        log_warning "Virtual environment already exists"
        read -p "Recreate virtual environment? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            log_info "Removing existing virtual environment..."
            rm -rf "$VENV_DIR"
        else
            log_info "Using existing virtual environment"
            return 0
        fi
    fi

    log_info "Creating virtual environment..."
    python3 -m venv "$VENV_DIR" || {
        log_error "Failed to create virtual environment"
        exit 1
    }

    log_success "Virtual environment created"
}

# Activate virtual environment
activate_virtualenv() {
    log_info "Activating virtual environment..."

    if [ -f "$VENV_DIR/bin/activate" ]; then
        source "$VENV_DIR/bin/activate"
    elif [ -f "$VENV_DIR/Scripts/activate" ]; then
        source "$VENV_DIR/Scripts/activate"
    else
        log_error "Virtual environment activation script not found"
        exit 1
    fi

    log_success "Virtual environment activated"
}

# Install dependencies
install_dependencies() {
    log_info "Installing Python dependencies..."

    # Upgrade pip
    pip install --upgrade pip setuptools wheel --quiet

    # Install main dependencies
    if [ -f "$APP_DIR/requirements.txt" ]; then
        pip install -r "$APP_DIR/requirements.txt" || {
            log_error "Failed to install dependencies"
            exit 1
        }
        log_success "Main dependencies installed"
    else
        log_error "requirements.txt not found"
        exit 1
    fi

    # Install development dependencies
    if [ -f "$APP_DIR/requirements-dev.txt" ]; then
        pip install -r "$APP_DIR/requirements-dev.txt" --quiet || {
            log_warning "Failed to install dev dependencies"
        }
        log_success "Development dependencies installed"
    fi
}

# Setup pre-commit hooks
setup_precommit() {
    log_info "Setting up pre-commit hooks..."

    if command -v pre-commit >/dev/null 2>&1; then
        cd "$APP_DIR"

        if [ -f ".pre-commit-config.yaml" ]; then
            pre-commit install || {
                log_warning "Failed to install pre-commit hooks"
                return 1
            }
            log_success "Pre-commit hooks installed"
        else
            log_warning ".pre-commit-config.yaml not found, skipping"
        fi
    else
        log_warning "pre-commit not installed, skipping hooks setup"
    fi
}

# Setup database
setup_database() {
    log_info "Setting up database..."

    DB_NAME="${DB_NAME:-corporate_intel}"
    DB_USER="${DB_USER:-postgres}"
    DB_HOST="${DB_HOST:-localhost}"
    DB_PORT="${DB_PORT:-5432}"

    # Check if PostgreSQL is accessible
    if ! pg_isready -h "$DB_HOST" -p "$DB_PORT" >/dev/null 2>&1; then
        log_warning "PostgreSQL is not running or not accessible"
        log_info "Please start PostgreSQL manually and run migrations"
        return 1
    fi

    # Create database if it doesn't exist
    log_info "Creating database '$DB_NAME'..."
    createdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME" 2>/dev/null || {
        log_warning "Database already exists or creation failed"
    }

    # Run migrations
    if [ -f "$APP_DIR/alembic.ini" ]; then
        log_info "Running database migrations..."
        cd "$APP_DIR"
        alembic upgrade head || {
            log_warning "Migrations failed, you may need to run them manually"
        }
        log_success "Database setup complete"
    else
        log_warning "Alembic not configured, skipping migrations"
    fi
}

# Create environment file
create_env_file() {
    log_info "Creating environment configuration..."

    ENV_FILE="$APP_DIR/.env"

    if [ -f "$ENV_FILE" ]; then
        log_warning ".env file already exists"
        return 0
    fi

    cat > "$ENV_FILE" << 'EOF'
# Corporate Intel Environment Configuration

# Application
ENVIRONMENT=development
DEBUG=true
SECRET_KEY=change-me-in-production
API_HOST=0.0.0.0
API_PORT=8000

# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=corporate_intel
DB_USER=postgres
DB_PASSWORD=your-password-here

# Redis (Optional)
REDIS_HOST=localhost
REDIS_PORT=6379

# OpenAI API
OPENAI_API_KEY=your-openai-api-key-here

# Logging
LOG_LEVEL=debug

# CORS (Comma-separated origins)
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=60
EOF

    log_success "Environment file created at $ENV_FILE"
    log_warning "Please update .env with your actual configuration"
}

# Create necessary directories
create_directories() {
    log_info "Creating project directories..."

    mkdir -p "$APP_DIR/logs"
    mkdir -p "$APP_DIR/data"
    mkdir -p "$APP_DIR/tmp"
    mkdir -p "$APP_DIR/tests"

    log_success "Directories created"
}

# Load sample data
load_sample_data() {
    log_info "Would you like to load sample data? (optional)"
    read -p "Load sample data? (y/N): " -n 1 -r
    echo

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if [ -f "$APP_DIR/scripts/load-sample-data.py" ]; then
            python "$APP_DIR/scripts/load-sample-data.py" || {
                log_warning "Failed to load sample data"
            }
            log_success "Sample data loaded"
        else
            log_warning "Sample data script not found"
        fi
    else
        log_info "Skipping sample data"
    fi
}

# Display completion message
show_completion() {
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  Development Environment Ready!       ${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "${BLUE}Next steps:${NC}"
    echo "  1. Update .env file with your configuration"
    echo "  2. Ensure PostgreSQL is running"
    echo "  3. Start the application:"
    echo -e "     ${YELLOW}bash scripts/start-app.sh${NC}"
    echo ""
    echo -e "${BLUE}Useful commands:${NC}"
    echo "  - Run tests:     pytest"
    echo "  - Code format:   black app/"
    echo "  - Type check:    mypy app/"
    echo "  - Linting:       ruff check app/"
    echo ""
    echo -e "${BLUE}Documentation:${NC}"
    echo "  - Getting Started: docs/GETTING_STARTED.md"
    echo "  - API Docs:        http://localhost:8000/docs"
    echo ""
}

# Main execution
main() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  Corporate Intel Dev Environment Setup${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""

    cd "$APP_DIR"

    # Run setup steps
    check_system
    create_virtualenv
    activate_virtualenv
    install_dependencies
    create_directories
    create_env_file
    setup_precommit
    setup_database
    load_sample_data

    # Show completion message
    show_completion
}

# Run main function
main
