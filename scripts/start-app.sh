#!/bin/bash
# Corporate Intel Application Startup Script
# This script handles the complete startup process for the application

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
REQUIREMENTS_FILE="${APP_DIR}/requirements.txt"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-corporate_intel}"
DB_USER="${DB_USER:-postgres}"
API_HOST="${API_HOST:-0.0.0.0}"
API_PORT="${API_PORT:-8000}"
WORKERS="${WORKERS:-4}"
LOG_LEVEL="${LOG_LEVEL:-info}"

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

# Check if running in virtual environment
check_virtualenv() {
    log_info "Checking virtual environment..."

    if [ -z "$VIRTUAL_ENV" ]; then
        if [ -d "$VENV_DIR" ]; then
            log_info "Activating virtual environment..."
            source "$VENV_DIR/bin/activate" 2>/dev/null || source "$VENV_DIR/Scripts/activate" 2>/dev/null || {
                log_error "Failed to activate virtual environment"
                exit 1
            }
            log_success "Virtual environment activated"
        else
            log_error "Virtual environment not found at $VENV_DIR"
            log_info "Run scripts/setup-dev.sh first"
            exit 1
        fi
    else
        log_success "Already in virtual environment"
    fi
}

# Check and install dependencies
check_dependencies() {
    log_info "Checking dependencies..."

    if [ ! -f "$REQUIREMENTS_FILE" ]; then
        log_error "requirements.txt not found"
        exit 1
    fi

    # Check if dependencies are installed
    python -c "import fastapi, sqlalchemy, redis" 2>/dev/null || {
        log_warning "Dependencies not installed or outdated"
        log_info "Installing dependencies..."
        pip install -r "$REQUIREMENTS_FILE" --quiet || {
            log_error "Failed to install dependencies"
            exit 1
        }
        log_success "Dependencies installed"
    }

    log_success "All dependencies satisfied"
}

# Check database connection
check_database() {
    log_info "Checking database connection..."

    # Wait for PostgreSQL to be ready
    max_attempts=30
    attempt=0

    while [ $attempt -lt $max_attempts ]; do
        if pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" >/dev/null 2>&1; then
            log_success "Database is ready"
            return 0
        fi

        attempt=$((attempt + 1))
        if [ $attempt -lt $max_attempts ]; then
            log_warning "Database not ready, waiting... (attempt $attempt/$max_attempts)"
            sleep 2
        fi
    done

    log_error "Database connection timeout"
    log_error "Please ensure PostgreSQL is running and accessible"
    exit 1
}

# Check Redis connection
check_redis() {
    log_info "Checking Redis connection..."

    REDIS_HOST="${REDIS_HOST:-localhost}"
    REDIS_PORT="${REDIS_PORT:-6379}"

    if command -v redis-cli >/dev/null 2>&1; then
        if redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping >/dev/null 2>&1; then
            log_success "Redis is ready"
            return 0
        fi
    fi

    log_warning "Redis not available (optional for caching)"
    log_info "Application will run without Redis caching"
}

# Run database migrations
run_migrations() {
    log_info "Running database migrations..."

    cd "$APP_DIR"

    # Check if Alembic is configured
    if [ -f "alembic.ini" ]; then
        alembic upgrade head || {
            log_error "Migration failed"
            exit 1
        }
        log_success "Migrations completed"
    else
        log_warning "Alembic not configured, skipping migrations"
    fi
}

# Create necessary directories
create_directories() {
    log_info "Creating necessary directories..."

    mkdir -p "$APP_DIR/logs"
    mkdir -p "$APP_DIR/data"
    mkdir -p "$APP_DIR/tmp"

    log_success "Directories created"
}

# Start the application
start_application() {
    log_info "Starting Corporate Intel API server..."

    cd "$APP_DIR"

    # Set environment variables
    export PYTHONPATH="$APP_DIR:$PYTHONPATH"

    # Start uvicorn with appropriate settings
    if [ "$ENVIRONMENT" = "production" ]; then
        log_info "Starting in PRODUCTION mode"
        uvicorn app.main:app \
            --host "$API_HOST" \
            --port "$API_PORT" \
            --workers "$WORKERS" \
            --log-level "$LOG_LEVEL" \
            --no-access-log \
            --proxy-headers \
            --forwarded-allow-ips='*'
    else
        log_info "Starting in DEVELOPMENT mode"
        uvicorn app.main:app \
            --host "$API_HOST" \
            --port "$API_PORT" \
            --reload \
            --log-level debug
    fi
}

# Health check after startup
verify_health() {
    log_info "Waiting for application to start..."
    sleep 5

    if bash "$APP_DIR/scripts/health-check.sh" >/dev/null 2>&1; then
        log_success "Application is healthy"
    else
        log_warning "Health check failed, but application may still be starting"
    fi
}

# Main execution
main() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  Corporate Intel Application Startup  ${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""

    # Pre-flight checks
    check_virtualenv
    check_dependencies
    create_directories
    check_database
    check_redis
    run_migrations

    echo ""
    log_success "All pre-flight checks passed"
    echo ""

    # Start application
    start_application
}

# Handle script arguments
case "${1:-start}" in
    start)
        main
        ;;
    check)
        check_virtualenv
        check_dependencies
        check_database
        check_redis
        log_success "All checks passed"
        ;;
    migrate)
        check_virtualenv
        check_database
        run_migrations
        ;;
    *)
        echo "Usage: $0 {start|check|migrate}"
        echo "  start   - Start the application (default)"
        echo "  check   - Run pre-flight checks only"
        echo "  migrate - Run database migrations only"
        exit 1
        ;;
esac
