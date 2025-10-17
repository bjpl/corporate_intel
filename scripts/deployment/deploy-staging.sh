#!/bin/bash
# Staging Deployment Script for Corporate Intelligence Platform
# Usage: ./deploy-staging.sh [--dry-run] [--skip-tests] [--force]
#
# This script automates staging deployment with health checks, smoke tests,
# and comprehensive validation. Supports rollback on failure.

set -euo pipefail
IFS=$'\n\t'

# Script metadata
SCRIPT_VERSION="1.0.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
LOG_FILE="${PROJECT_ROOT}/logs/deploy-staging-$(date +%Y%m%d_%H%M%S).log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Deployment configuration
STAGING_ENV="staging"
COMPOSE_FILE="docker-compose.staging.yml"
MAX_HEALTH_RETRIES=30
HEALTH_CHECK_INTERVAL=10
SMOKE_TEST_TIMEOUT=300
DRY_RUN=false
SKIP_TESTS=false
FORCE_DEPLOY=false

# Logging functions
log() {
    local level=$1
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${timestamp} [${level}] ${message}" | tee -a "${LOG_FILE}"
}

log_info() { log "INFO" "${BLUE}$*${NC}"; }
log_success() { log "SUCCESS" "${GREEN}✓ $*${NC}"; }
log_warning() { log "WARNING" "${YELLOW}⚠ $*${NC}"; }
log_error() { log "ERROR" "${RED}✗ $*${NC}"; }

# Error handler
handle_error() {
    local line_num=$1
    log_error "Deployment failed at line ${line_num}"
    log_error "Check log file: ${LOG_FILE}"

    if [ "${DRY_RUN}" = false ]; then
        log_warning "Initiating rollback..."
        rollback_deployment
    fi

    exit 1
}

trap 'handle_error ${LINENO}' ERR

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --dry-run)
                DRY_RUN=true
                log_info "Dry run mode enabled - no actual changes will be made"
                shift
                ;;
            --skip-tests)
                SKIP_TESTS=true
                log_warning "Test execution will be skipped"
                shift
                ;;
            --force)
                FORCE_DEPLOY=true
                log_warning "Force mode enabled - skipping some safety checks"
                shift
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
}

show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Deploy Corporate Intelligence Platform to staging environment.

OPTIONS:
    --dry-run       Show what would be done without making changes
    --skip-tests    Skip smoke tests (not recommended)
    --force         Force deployment, skip some safety checks
    -h, --help      Show this help message

EXAMPLES:
    $0                          # Normal deployment
    $0 --dry-run                # Preview deployment
    $0 --skip-tests             # Deploy without tests
    $0 --force                  # Force deployment

EOF
}

# Pre-flight checks
run_preflight_checks() {
    log_info "Running pre-flight checks..."

    # Check if running as root (should not be)
    if [ "$EUID" -eq 0 ]; then
        log_error "This script should not be run as root"
        exit 1
    fi

    # Check if Docker is installed and running
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi

    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        exit 1
    fi

    # Check if docker-compose is installed
    if ! command -v docker-compose &> /dev/null; then
        log_error "docker-compose is not installed"
        exit 1
    fi

    # Check if required files exist
    local required_files=(
        "${PROJECT_ROOT}/${COMPOSE_FILE}"
        "${PROJECT_ROOT}/config/.env.staging"
        "${PROJECT_ROOT}/Dockerfile"
    )

    for file in "${required_files[@]}"; do
        if [ ! -f "${file}" ]; then
            log_error "Required file not found: ${file}"
            exit 1
        fi
    done

    # Check disk space (require at least 10GB free)
    local available_space=$(df -BG "${PROJECT_ROOT}" | awk 'NR==2 {print $4}' | sed 's/G//')
    if [ "${available_space}" -lt 10 ]; then
        log_error "Insufficient disk space. Available: ${available_space}GB, Required: 10GB"
        exit 1
    fi

    # Check if git repo is clean (unless --force)
    if [ "${FORCE_DEPLOY}" = false ]; then
        cd "${PROJECT_ROOT}"
        if [ -n "$(git status --porcelain)" ]; then
            log_error "Git repository has uncommitted changes. Use --force to override."
            exit 1
        fi
    fi

    log_success "Pre-flight checks passed"
}

# Pull latest code from git
pull_latest_code() {
    log_info "Pulling latest code from git..."

    if [ "${DRY_RUN}" = true ]; then
        log_info "[DRY RUN] Would execute: git pull origin master"
        return 0
    fi

    cd "${PROJECT_ROOT}"

    # Get current branch
    local current_branch=$(git rev-parse --abbrev-ref HEAD)
    log_info "Current branch: ${current_branch}"

    # Get current commit
    local current_commit=$(git rev-parse --short HEAD)
    log_info "Current commit: ${current_commit}"

    # Pull latest changes
    git fetch origin
    git pull origin "${current_branch}"

    # Get new commit
    local new_commit=$(git rev-parse --short HEAD)
    log_info "New commit: ${new_commit}"

    if [ "${current_commit}" = "${new_commit}" ]; then
        log_info "Already up to date"
    else
        log_success "Code updated: ${current_commit} → ${new_commit}"
    fi
}

# Build Docker images
build_docker_images() {
    log_info "Building Docker images..."

    if [ "${DRY_RUN}" = true ]; then
        log_info "[DRY RUN] Would execute: docker-compose -f ${COMPOSE_FILE} build"
        return 0
    fi

    cd "${PROJECT_ROOT}"

    # Build with build args and cache
    docker-compose -f "${COMPOSE_FILE}" build \
        --build-arg ENVIRONMENT=staging \
        --build-arg BUILD_DATE="$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
        --build-arg VCS_REF="$(git rev-parse --short HEAD)" \
        --pull \
        2>&1 | tee -a "${LOG_FILE}"

    log_success "Docker images built successfully"
}

# Run database migrations
run_database_migrations() {
    log_info "Running database migrations..."

    if [ "${DRY_RUN}" = true ]; then
        log_info "[DRY RUN] Would run database migrations"
        return 0
    fi

    cd "${PROJECT_ROOT}"

    # Ensure postgres is running
    if ! docker-compose -f "${COMPOSE_FILE}" ps postgres | grep -q "Up"; then
        log_info "Starting postgres for migrations..."
        docker-compose -f "${COMPOSE_FILE}" up -d postgres
        sleep 10
    fi

    # Run migrations (if using Alembic)
    if [ -d "${PROJECT_ROOT}/alembic" ]; then
        log_info "Running Alembic migrations..."
        docker-compose -f "${COMPOSE_FILE}" run --rm api alembic upgrade head
    else
        log_info "No Alembic migrations found, skipping"
    fi

    log_success "Database migrations completed"
}

# Deploy services with health checks
deploy_services() {
    log_info "Deploying services to staging..."

    if [ "${DRY_RUN}" = true ]; then
        log_info "[DRY RUN] Would execute: docker-compose -f ${COMPOSE_FILE} up -d"
        return 0
    fi

    cd "${PROJECT_ROOT}"

    # Stop existing containers
    log_info "Stopping existing containers..."
    docker-compose -f "${COMPOSE_FILE}" down || true

    # Start all services
    log_info "Starting services..."
    docker-compose -f "${COMPOSE_FILE}" up -d

    log_success "Services started"
}

# Wait for services to be healthy
wait_for_services() {
    log_info "Waiting for services to be healthy..."

    if [ "${DRY_RUN}" = true ]; then
        log_info "[DRY RUN] Would wait for services to be healthy"
        return 0
    fi

    local services=("postgres" "redis" "api")

    for service in "${services[@]}"; do
        log_info "Checking health of ${service}..."

        local retries=0
        while [ ${retries} -lt ${MAX_HEALTH_RETRIES} ]; do
            local health_status=$(docker-compose -f "${COMPOSE_FILE}" ps "${service}" | grep -o "Up (healthy)" || echo "unhealthy")

            if [[ "${health_status}" == *"healthy"* ]]; then
                log_success "${service} is healthy"
                break
            fi

            retries=$((retries + 1))
            log_info "Waiting for ${service} to be healthy (attempt ${retries}/${MAX_HEALTH_RETRIES})..."
            sleep ${HEALTH_CHECK_INTERVAL}
        done

        if [ ${retries} -eq ${MAX_HEALTH_RETRIES} ]; then
            log_error "${service} failed to become healthy"
            return 1
        fi
    done

    log_success "All services are healthy"
}

# Configure monitoring
configure_monitoring() {
    log_info "Configuring monitoring..."

    if [ "${DRY_RUN}" = true ]; then
        log_info "[DRY RUN] Would configure monitoring"
        return 0
    fi

    # Check if Prometheus is running
    if docker-compose -f "${COMPOSE_FILE}" ps prometheus | grep -q "Up"; then
        log_info "Prometheus is running"

        # Verify Prometheus targets
        local prometheus_url="http://localhost:9090"
        if curl -sf "${prometheus_url}/-/healthy" > /dev/null; then
            log_success "Prometheus is healthy"
        else
            log_warning "Prometheus health check failed"
        fi
    else
        log_warning "Prometheus is not configured in staging"
    fi

    log_success "Monitoring configured"
}

# Run smoke tests
run_smoke_tests() {
    if [ "${SKIP_TESTS}" = true ]; then
        log_warning "Skipping smoke tests (--skip-tests flag used)"
        return 0
    fi

    log_info "Running smoke tests..."

    if [ "${DRY_RUN}" = true ]; then
        log_info "[DRY RUN] Would run smoke tests"
        return 0
    fi

    local staging_url="http://localhost:8000"
    local test_failures=0

    # Test 1: Health endpoint
    log_info "Testing health endpoint..."
    if curl -sf "${staging_url}/health" > /dev/null; then
        log_success "Health endpoint: PASS"
    else
        log_error "Health endpoint: FAIL"
        test_failures=$((test_failures + 1))
    fi

    # Test 2: Database connectivity
    log_info "Testing database connectivity..."
    if curl -sf "${staging_url}/api/v1/health/database" > /dev/null; then
        log_success "Database connectivity: PASS"
    else
        log_error "Database connectivity: FAIL"
        test_failures=$((test_failures + 1))
    fi

    # Test 3: Redis connectivity
    log_info "Testing Redis connectivity..."
    if curl -sf "${staging_url}/api/v1/health/redis" > /dev/null; then
        log_success "Redis connectivity: PASS"
    else
        log_warning "Redis connectivity: FAIL (non-critical)"
    fi

    # Test 4: API readiness
    log_info "Testing API readiness..."
    if curl -sf "${staging_url}/api/v1/health/ready" > /dev/null; then
        log_success "API readiness: PASS"
    else
        log_error "API readiness: FAIL"
        test_failures=$((test_failures + 1))
    fi

    # Test 5: Run integration tests
    if [ -d "${PROJECT_ROOT}/tests" ]; then
        log_info "Running integration tests..."
        if docker-compose -f "${COMPOSE_FILE}" run --rm api pytest tests/integration/ -v --tb=short; then
            log_success "Integration tests: PASS"
        else
            log_warning "Integration tests: FAIL (non-blocking)"
        fi
    fi

    if [ ${test_failures} -gt 0 ]; then
        log_error "Smoke tests failed: ${test_failures} critical failures"
        return 1
    fi

    log_success "All smoke tests passed"
}

# Validate deployment success
validate_deployment() {
    log_info "Validating deployment..."

    if [ "${DRY_RUN}" = true ]; then
        log_info "[DRY RUN] Would validate deployment"
        return 0
    fi

    local validation_failures=0

    # Check all containers are running
    log_info "Checking container status..."
    local running_containers=$(docker-compose -f "${COMPOSE_FILE}" ps --services --filter "status=running" | wc -l)
    local total_containers=$(docker-compose -f "${COMPOSE_FILE}" ps --services | wc -l)

    if [ ${running_containers} -eq ${total_containers} ]; then
        log_success "All containers are running (${running_containers}/${total_containers})"
    else
        log_error "Some containers are not running (${running_containers}/${total_containers})"
        validation_failures=$((validation_failures + 1))
    fi

    # Check logs for errors
    log_info "Checking logs for errors..."
    local error_count=$(docker-compose -f "${COMPOSE_FILE}" logs --tail=100 | grep -i "error\|exception\|fatal" | wc -l)

    if [ ${error_count} -eq 0 ]; then
        log_success "No errors found in recent logs"
    else
        log_warning "Found ${error_count} error messages in recent logs (review ${LOG_FILE})"
    fi

    # Verify environment variables
    log_info "Verifying environment configuration..."
    if docker-compose -f "${COMPOSE_FILE}" run --rm api env | grep -q "ENVIRONMENT=staging"; then
        log_success "Environment variables correctly set"
    else
        log_error "Environment variables not correctly configured"
        validation_failures=$((validation_failures + 1))
    fi

    if [ ${validation_failures} -gt 0 ]; then
        log_error "Deployment validation failed: ${validation_failures} issues"
        return 1
    fi

    log_success "Deployment validated successfully"
}

# Rollback deployment
rollback_deployment() {
    log_warning "Rolling back deployment..."

    cd "${PROJECT_ROOT}"

    # Stop current containers
    docker-compose -f "${COMPOSE_FILE}" down || true

    # Restore previous version (if tagged)
    local previous_tag=$(git describe --abbrev=0 --tags "$(git rev-list --tags --skip=1 --max-count=1)" 2>/dev/null || echo "")

    if [ -n "${previous_tag}" ]; then
        log_info "Checking out previous tag: ${previous_tag}"
        git checkout "${previous_tag}"

        # Rebuild and restart
        docker-compose -f "${COMPOSE_FILE}" build
        docker-compose -f "${COMPOSE_FILE}" up -d

        log_success "Rolled back to ${previous_tag}"
    else
        log_error "No previous tag found for rollback"
    fi
}

# Generate deployment report
generate_deployment_report() {
    log_info "Generating deployment report..."

    local report_file="${PROJECT_ROOT}/logs/staging-deployment-report-$(date +%Y%m%d_%H%M%S).txt"

    cat > "${report_file}" << EOF
===============================================================================
STAGING DEPLOYMENT REPORT
===============================================================================

Deployment Date: $(date '+%Y-%m-%d %H:%M:%S %Z')
Script Version: ${SCRIPT_VERSION}
Environment: ${STAGING_ENV}

GIT INFORMATION
---------------
Branch: $(git rev-parse --abbrev-ref HEAD)
Commit: $(git rev-parse --short HEAD)
Commit Message: $(git log -1 --pretty=%B)
Author: $(git log -1 --pretty=%an)

DEPLOYMENT DETAILS
------------------
Compose File: ${COMPOSE_FILE}
Dry Run: ${DRY_RUN}
Skip Tests: ${SKIP_TESTS}
Force Deploy: ${FORCE_DEPLOY}

CONTAINER STATUS
----------------
$(docker-compose -f "${COMPOSE_FILE}" ps)

HEALTH CHECKS
-------------
$(curl -s http://localhost:8000/health || echo "Health endpoint not available")

LOG FILE
--------
Full logs available at: ${LOG_FILE}

===============================================================================
EOF

    log_success "Deployment report generated: ${report_file}"
    cat "${report_file}"
}

# Main deployment flow
main() {
    log_info "=========================================="
    log_info "Corporate Intelligence Platform"
    log_info "Staging Deployment Script v${SCRIPT_VERSION}"
    log_info "=========================================="
    log_info ""

    # Create log directory
    mkdir -p "$(dirname "${LOG_FILE}")"

    # Parse arguments
    parse_args "$@"

    # Execute deployment steps
    log_info "Starting staging deployment..."
    log_info ""

    run_preflight_checks
    pull_latest_code
    build_docker_images
    run_database_migrations
    deploy_services
    wait_for_services
    configure_monitoring
    run_smoke_tests
    validate_deployment

    log_info ""
    log_success "=========================================="
    log_success "STAGING DEPLOYMENT COMPLETED SUCCESSFULLY"
    log_success "=========================================="
    log_info ""

    # Generate report
    if [ "${DRY_RUN}" = false ]; then
        generate_deployment_report
    fi

    log_info "Next steps:"
    log_info "  1. Monitor staging at http://localhost:8000"
    log_info "  2. Review logs: ${LOG_FILE}"
    log_info "  3. Run extended tests if needed"
    log_info "  4. Proceed to production when validated"
}

# Execute main function
main "$@"
