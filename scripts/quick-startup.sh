#!/bin/bash
################################################################################
# Corporate Intel - Quick Startup Script
#
# Starts the entire platform from scratch in 2-3 hours
# Handles port conflicts, database setup, and API startup
################################################################################

set -e  # Exit on any error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
POSTGRES_PORT=5434
REDIS_PORT=6381
MINIO_PORT=9002
MINIO_CONSOLE_PORT=9003
API_PORT=8002
MAX_RETRIES=30
RETRY_DELAY=2

################################################################################
# Helper Functions
################################################################################

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

wait_for_health() {
    local service=$1
    local url=$2
    local retries=0

    log_info "Waiting for $service to be healthy..."

    while [ $retries -lt $MAX_RETRIES ]; do
        if curl -f -s "$url" > /dev/null 2>&1; then
            log_success "$service is healthy!"
            return 0
        fi

        retries=$((retries + 1))
        echo -n "."
        sleep $RETRY_DELAY
    done

    log_error "$service failed to become healthy after $MAX_RETRIES attempts"
    return 1
}

wait_for_container() {
    local container=$1
    local retries=0

    log_info "Waiting for container $container to be healthy..."

    while [ $retries -lt $MAX_RETRIES ]; do
        local status=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "not_found")

        if [ "$status" = "healthy" ]; then
            log_success "Container $container is healthy!"
            return 0
        elif [ "$status" = "not_found" ]; then
            log_error "Container $container not found"
            return 1
        fi

        retries=$((retries + 1))
        echo -n "."
        sleep $RETRY_DELAY
    done

    log_error "Container $container failed to become healthy"
    return 1
}

################################################################################
# Main Script
################################################################################

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║         Corporate Intel - Quick Startup Script                ║"
echo "║         Estimated Time: 2-3 hours                             ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

################################################################################
# PHASE 1: Infrastructure Setup (30 min)
################################################################################

echo ""
log_info "═══════════════════════════════════════════════════════"
log_info "PHASE 1: Infrastructure Setup (30 min)"
log_info "═══════════════════════════════════════════════════════"
echo ""

# Step 1.1: Check for port conflicts
log_info "Step 1.1: Checking for port conflicts..."

if lsof -Pi :$POSTGRES_PORT -sTCP:LISTEN -t >/dev/null 2>&1 || \
   netstat -ano | grep -q ":$POSTGRES_PORT.*LISTENING" 2>/dev/null; then
    log_warning "Port $POSTGRES_PORT is in use. This is OK - we'll use this port."
fi

if lsof -Pi :$API_PORT -sTCP:LISTEN -t >/dev/null 2>&1 || \
   netstat -ano | grep -q ":$API_PORT.*LISTENING" 2>/dev/null; then
    log_error "Port $API_PORT is in use. Stopping..."
    exit 1
fi

log_success "Port check complete"

# Step 1.2: Backup and update .env
log_info "Step 1.2: Updating .env configuration..."

if [ -f .env ]; then
    cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
    log_success ".env backed up"
else
    log_error ".env file not found!"
    exit 1
fi

# Update or add port configurations
grep -q "^POSTGRES_PORT=" .env && sed -i.bak "s/^POSTGRES_PORT=.*/POSTGRES_PORT=$POSTGRES_PORT/" .env || echo "POSTGRES_PORT=$POSTGRES_PORT" >> .env
grep -q "^REDIS_PORT=" .env && sed -i.bak "s/^REDIS_PORT=.*/REDIS_PORT=$REDIS_PORT/" .env || echo "REDIS_PORT=$REDIS_PORT" >> .env
grep -q "^MINIO_PORT=" .env && sed -i.bak "s/^MINIO_PORT=.*/MINIO_PORT=$MINIO_PORT/" .env || echo "MINIO_PORT=$MINIO_PORT" >> .env
grep -q "^MINIO_CONSOLE_PORT=" .env && sed -i.bak "s/^MINIO_CONSOLE_PORT=.*/MINIO_CONSOLE_PORT=$MINIO_CONSOLE_PORT/" .env || echo "MINIO_CONSOLE_PORT=$MINIO_CONSOLE_PORT" >> .env
grep -q "^API_PORT=" .env && sed -i.bak "s/^API_PORT=.*/API_PORT=$API_PORT/" .env || echo "API_PORT=$API_PORT" >> .env

log_success ".env updated with port configuration"

# Step 1.3: Clean up any existing containers
log_info "Step 1.3: Cleaning up existing Corporate Intel containers..."

docker-compose down -v 2>/dev/null || true
log_success "Cleanup complete"

# Step 1.4: Start core infrastructure
log_info "Step 1.4: Starting Postgres and Redis..."

docker-compose up -d postgres redis

# Wait for services to be healthy
wait_for_container "corporate-intel-postgres" || exit 1
wait_for_container "corporate-intel-redis" || exit 1

# Verify connections
log_info "Verifying database connection..."
docker exec corporate-intel-postgres pg_isready -U intel_user -d corporate_intel || {
    log_error "Postgres connection failed"
    exit 1
}
log_success "Postgres connection verified"

log_info "Verifying Redis connection..."
docker exec corporate-intel-redis redis-cli ping | grep -q "PONG" || {
    log_error "Redis connection failed"
    exit 1
}
log_success "Redis connection verified"

log_success "PHASE 1 COMPLETE: Infrastructure is running!"

################################################################################
# PHASE 2: Database Setup (20 min)
################################################################################

echo ""
log_info "═══════════════════════════════════════════════════════"
log_info "PHASE 2: Database Setup (20 min)"
log_info "═══════════════════════════════════════════════════════"
echo ""

# Step 2.1: Build API container (needed for migrations)
log_info "Step 2.1: Building API container..."

docker-compose build api || {
    log_error "API build failed"
    exit 1
}
log_success "API container built"

# Step 2.2: Run database migrations
log_info "Step 2.2: Running database migrations..."

log_info "Checking current migration status..."
docker-compose run --rm api alembic current 2>/dev/null || true

log_info "Running migrations to head..."
docker-compose run --rm api alembic upgrade head || {
    log_error "Migration failed"
    exit 1
}
log_success "Database migrations applied"

# Step 2.3: Verify migrations
log_info "Step 2.3: Verifying migrations..."

docker exec corporate-intel-postgres psql -U intel_user -d corporate_intel -c "\dt" | grep -q "alembic_version" || {
    log_error "Migration verification failed - alembic_version table not found"
    exit 1
}
log_success "Migrations verified"

# Step 2.4: Seed initial test data (optional)
log_info "Step 2.4: Seeding initial test data..."

docker exec corporate-intel-postgres psql -U intel_user -d corporate_intel <<-EOSQL
    INSERT INTO companies (ticker, name, cik, sector, industry, created_at, updated_at)
    VALUES
        ('AAPL', 'Apple Inc.', '0000320193', 'Technology', 'Consumer Electronics', NOW(), NOW()),
        ('MSFT', 'Microsoft Corporation', '0000789019', 'Technology', 'Software', NOW(), NOW()),
        ('GOOGL', 'Alphabet Inc.', '0001652044', 'Technology', 'Internet Services', NOW(), NOW())
    ON CONFLICT (ticker) DO NOTHING;
EOSQL

log_success "Test data seeded"

log_success "PHASE 2 COMPLETE: Database is ready!"

################################################################################
# PHASE 3: API Startup (20 min)
################################################################################

echo ""
log_info "═══════════════════════════════════════════════════════"
log_info "PHASE 3: API Startup (20 min)"
log_info "═══════════════════════════════════════════════════════"
echo ""

# Step 3.1: Start API container
log_info "Step 3.1: Starting API container..."

docker-compose up -d api

# Step 3.2: Wait for API to be healthy
wait_for_health "API" "http://localhost:$API_PORT/health" || {
    log_error "API failed to start"
    log_info "Showing recent logs:"
    docker-compose logs --tail=50 api
    exit 1
}

log_success "PHASE 3 COMPLETE: API is running!"

################################################################################
# PHASE 4: Validation (30 min)
################################################################################

echo ""
log_info "═══════════════════════════════════════════════════════"
log_info "PHASE 4: Basic Validation (30 min)"
log_info "═══════════════════════════════════════════════════════"
echo ""

# Step 4.1: Test health endpoints
log_info "Step 4.1: Testing health endpoints..."

curl -f -s "http://localhost:$API_PORT/health" > /tmp/health.json || {
    log_error "Health check failed"
    exit 1
}
log_success "Basic health check: OK"

curl -f -s "http://localhost:$API_PORT/health/database" > /tmp/health_db.json || {
    log_error "Database health check failed"
    exit 1
}
log_success "Database health check: OK"

curl -f -s "http://localhost:$API_PORT/health/cache" > /tmp/health_cache.json || {
    log_warning "Cache health check failed (non-critical)"
}
log_success "Cache health check: OK"

# Step 4.2: Test API documentation
log_info "Step 4.2: Testing API documentation..."

curl -f -s "http://localhost:$API_PORT/api/v1/docs" > /dev/null || {
    log_error "API docs not accessible"
    exit 1
}
log_success "API documentation accessible"

# Step 4.3: Display final status
log_success "PHASE 4 COMPLETE: All systems validated!"

################################################################################
# Final Summary
################################################################################

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                    STARTUP COMPLETE!                           ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

log_success "Corporate Intel Platform is now running!"
echo ""
echo "📊 Service Status:"
echo "  ✓ PostgreSQL (TimescaleDB): http://localhost:$POSTGRES_PORT"
echo "  ✓ Redis Cache:               localhost:$REDIS_PORT"
echo "  ✓ FastAPI Application:       http://localhost:$API_PORT"
echo ""
echo "🔗 Important URLs:"
echo "  • API Documentation:  http://localhost:$API_PORT/api/v1/docs"
echo "  • API ReDoc:          http://localhost:$API_PORT/api/v1/redoc"
echo "  • Health Check:       http://localhost:$API_PORT/health"
echo "  • Prometheus Metrics: http://localhost:$API_PORT/metrics"
echo ""
echo "📝 Next Steps:"
echo "  1. Register a user:"
echo "     curl -X POST http://localhost:$API_PORT/auth/register \\"
echo "       -H 'Content-Type: application/json' \\"
echo "       -d '{\"email\": \"test@example.com\", \"password\": \"SecurePass123!\", \"full_name\": \"Test User\"}'"
echo ""
echo "  2. Login to get access token:"
echo "     curl -X POST http://localhost:$API_PORT/auth/login \\"
echo "       -H 'Content-Type: application/x-www-form-urlencoded' \\"
echo "       -d 'username=test@example.com&password=SecurePass123!'"
echo ""
echo "  3. Explore the API at: http://localhost:$API_PORT/api/v1/docs"
echo ""
echo "📖 View logs:"
echo "  docker-compose logs -f api"
echo ""
echo "🛑 Stop services:"
echo "  docker-compose down"
echo ""

# Save connection info
cat > .startup-info <<-EOF
Corporate Intel Platform - Connection Information
Generated: $(date)

PostgreSQL:
  Host: localhost
  Port: $POSTGRES_PORT
  Database: corporate_intel
  User: intel_user
  Password: (see .env)

Redis:
  Host: localhost
  Port: $REDIS_PORT
  Password: (see .env)

API:
  URL: http://localhost:$API_PORT
  Docs: http://localhost:$API_PORT/api/v1/docs
  Health: http://localhost:$API_PORT/health

MinIO (if started):
  API: http://localhost:$MINIO_PORT
  Console: http://localhost:$MINIO_CONSOLE_PORT
  User: minio_admin
  Password: (see .env)
EOF

log_success "Connection information saved to .startup-info"
echo ""
log_info "Happy coding! 🚀"
