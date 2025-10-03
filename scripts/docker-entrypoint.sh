#!/bin/bash
# Docker Entrypoint Script for Corporate Intelligence Platform
# Handles initialization, migrations, and graceful startup/shutdown

set -e  # Exit on error

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Trap signals for graceful shutdown
cleanup() {
    log_info "Received shutdown signal, cleaning up..."
    # Kill background jobs
    jobs -p | xargs -r kill 2>/dev/null || true
    log_success "Cleanup complete"
    exit 0
}

trap cleanup SIGTERM SIGINT SIGQUIT

# Environment validation
validate_environment() {
    log_info "Validating environment variables..."

    local required_vars=(
        "POSTGRES_HOST"
        "POSTGRES_PORT"
        "POSTGRES_USER"
        "POSTGRES_PASSWORD"
        "POSTGRES_DB"
    )

    local missing_vars=()

    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            missing_vars+=("$var")
        fi
    done

    if [ ${#missing_vars[@]} -ne 0 ]; then
        log_error "Missing required environment variables: ${missing_vars[*]}"
        exit 1
    fi

    log_success "Environment validation complete"
}

# Wait for PostgreSQL to be ready
wait_for_postgres() {
    log_info "Waiting for PostgreSQL at ${POSTGRES_HOST}:${POSTGRES_PORT}..."

    local max_attempts=30
    local attempt=0

    until pg_isready -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" > /dev/null 2>&1; do
        attempt=$((attempt + 1))

        if [ $attempt -eq $max_attempts ]; then
            log_error "PostgreSQL did not become ready after ${max_attempts} attempts"
            exit 1
        fi

        log_info "Waiting for PostgreSQL... (attempt ${attempt}/${max_attempts})"
        sleep 2
    done

    log_success "PostgreSQL is ready"
}

# Wait for Redis to be ready
wait_for_redis() {
    if [ -n "$REDIS_HOST" ]; then
        log_info "Waiting for Redis at ${REDIS_HOST}:${REDIS_PORT:-6379}..."

        local max_attempts=30
        local attempt=0

        until redis-cli -h "$REDIS_HOST" -p "${REDIS_PORT:-6379}" ping > /dev/null 2>&1; do
            attempt=$((attempt + 1))

            if [ $attempt -eq $max_attempts ]; then
                log_warning "Redis did not become ready, continuing anyway..."
                return 0
            fi

            log_info "Waiting for Redis... (attempt ${attempt}/${max_attempts})"
            sleep 2
        done

        log_success "Redis is ready"
    fi
}

# Initialize database extensions
init_database_extensions() {
    log_info "Initializing database extensions..."

    PGPASSWORD="$POSTGRES_PASSWORD" psql \
        -h "$POSTGRES_HOST" \
        -p "$POSTGRES_PORT" \
        -U "$POSTGRES_USER" \
        -d "$POSTGRES_DB" \
        -c "CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;" \
        -c "CREATE EXTENSION IF NOT EXISTS vector;" \
        -c "SELECT extname, extversion FROM pg_extension;" \
        > /dev/null 2>&1 || log_warning "Some extensions may already exist"

    log_success "Database extensions initialized"
}

# Run database migrations
run_migrations() {
    log_info "Running database migrations..."

    # Check if alembic is available
    if ! command -v alembic &> /dev/null; then
        log_warning "Alembic not found, skipping migrations"
        return 0
    fi

    # Check current migration status
    if alembic current 2>&1 | grep -q "No such file"; then
        log_info "Initializing alembic for the first time..."
        alembic stamp head || log_warning "Could not stamp head"
    fi

    # Run migrations
    if alembic upgrade head; then
        log_success "Database migrations completed"
    else
        log_error "Database migration failed"
        exit 1
    fi
}

# Seed initial data (optional)
seed_data() {
    if [ "$SEED_DATA" = "true" ]; then
        log_info "Seeding initial data..."

        if [ -f "/app/scripts/seed_data.py" ]; then
            python /app/scripts/seed_data.py || log_warning "Data seeding failed, continuing anyway"
            log_success "Data seeding completed"
        else
            log_warning "Seed script not found, skipping"
        fi
    fi
}

# Health check
health_check() {
    log_info "Running health check..."

    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        log_success "Health check passed"
        return 0
    else
        log_warning "Health check failed"
        return 1
    fi
}

# Create necessary directories
create_directories() {
    log_info "Creating application directories..."

    mkdir -p /app/logs /app/data /app/cache /app/tmp

    # Set permissions if running as root (will switch to appuser)
    if [ "$(id -u)" = "0" ]; then
        chown -R appuser:appuser /app/logs /app/data /app/cache /app/tmp 2>/dev/null || true
    fi

    log_success "Directories created"
}

# Main execution
main() {
    log_info "========================================"
    log_info "Corporate Intelligence Platform Starting"
    log_info "Environment: ${ENVIRONMENT:-production}"
    log_info "========================================"

    # Validation and setup
    validate_environment
    create_directories

    # Wait for services
    wait_for_postgres
    wait_for_redis

    # Database initialization
    init_database_extensions
    run_migrations
    seed_data

    log_info "========================================"
    log_info "Starting application server..."
    log_info "========================================"

    # Execute the main command passed to docker run
    exec "$@"
}

# Run main function
main "$@"
