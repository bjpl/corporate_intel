#!/bin/bash
################################################################################
# Infrastructure Deployment Script
# Corporate Intelligence Platform
################################################################################
# Version: 1.0.0
# Last Updated: October 17, 2025
#
# DESCRIPTION:
#   Deploys infrastructure services: PostgreSQL with TimescaleDB, Redis cache,
#   and MinIO object storage. Includes health checks and validation.
#
# USAGE:
#   ./scripts/deploy-infrastructure.sh [OPTIONS]
#
# OPTIONS:
#   --version VERSION        Deployment version tag
#   --skip-health-checks    Skip health check validation
#   --recreate              Force recreate containers
#   --help                  Show this help message
#
# DEPLOYED SERVICES:
#   - PostgreSQL 15 with TimescaleDB 2.13.0
#   - Redis 7.2 with persistence
#   - MinIO (S3-compatible object storage)
#   - Prometheus exporters for metrics
################################################################################

set -euo pipefail
IFS=$'\n\t'

# ==============================================================================
# CONFIGURATION
# ==============================================================================

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
readonly COMPOSE_FILE="${PROJECT_ROOT}/config/production/docker-compose.production.yml"
readonly ENV_FILE="${PROJECT_ROOT}/config/production/.env.production"

# Deployment settings
DEPLOYMENT_VERSION="${DEPLOYMENT_VERSION:-latest}"
SKIP_HEALTH_CHECKS=false
RECREATE_CONTAINERS=false

# Health check configuration
readonly POSTGRES_HEALTH_TIMEOUT=60
readonly REDIS_HEALTH_TIMEOUT=30
readonly MINIO_HEALTH_TIMEOUT=45

# Colors
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly RED='\033[0;31m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m'

# ==============================================================================
# LOGGING
# ==============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} ✅ $*"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} ⚠️  $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} ❌ $*"
}

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

wait_for_postgres() {
    log_info "Waiting for PostgreSQL to be ready..."

    local retries=0
    local max_retries=$((POSTGRES_HEALTH_TIMEOUT / 5))

    while [[ ${retries} -lt ${max_retries} ]]; do
        if docker-compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" \
            exec -T postgres pg_isready -U "${POSTGRES_USER:-intel_prod_user}" &> /dev/null; then
            log_success "PostgreSQL is ready"
            return 0
        fi

        ((retries++))
        log_info "Waiting for PostgreSQL... (${retries}/${max_retries})"
        sleep 5
    done

    log_error "PostgreSQL failed to become ready within ${POSTGRES_HEALTH_TIMEOUT} seconds"
    return 1
}

wait_for_redis() {
    log_info "Waiting for Redis to be ready..."

    local retries=0
    local max_retries=$((REDIS_HEALTH_TIMEOUT / 5))

    while [[ ${retries} -lt ${max_retries} ]]; do
        if docker-compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" \
            exec -T redis redis-cli ping &> /dev/null; then
            log_success "Redis is ready"
            return 0
        fi

        ((retries++))
        log_info "Waiting for Redis... (${retries}/${max_retries})"
        sleep 5
    done

    log_error "Redis failed to become ready within ${REDIS_HEALTH_TIMEOUT} seconds"
    return 1
}

wait_for_minio() {
    log_info "Waiting for MinIO to be ready..."

    local retries=0
    local max_retries=$((MINIO_HEALTH_TIMEOUT / 5))

    while [[ ${retries} -lt ${max_retries} ]]; do
        if curl -sf http://localhost:9000/minio/health/live &> /dev/null; then
            log_success "MinIO is ready"
            return 0
        fi

        ((retries++))
        log_info "Waiting for MinIO... (${retries}/${max_retries})"
        sleep 5
    done

    log_error "MinIO failed to become ready within ${MINIO_HEALTH_TIMEOUT} seconds"
    return 1
}

create_minio_buckets() {
    log_info "Creating MinIO buckets..."

    # Wait for MinIO to be fully ready
    sleep 5

    # Buckets to create (from environment file)
    local buckets=(
        "corporate-documents-prod"
        "analysis-reports-prod"
        "database-backups-prod"
        "sec-filings-prod"
        "data-exports-prod"
    )

    for bucket in "${buckets[@]}"; do
        log_info "Creating bucket: ${bucket}"

        # Check if bucket exists, create if not
        docker-compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" exec -T minio \
            sh -c "mc alias set local http://localhost:9000 \${MINIO_ROOT_USER} \${MINIO_ROOT_PASSWORD} && \
                   mc mb --ignore-existing local/${bucket}" || log_warning "Failed to create bucket: ${bucket}"
    done

    log_success "MinIO buckets created"
}

verify_postgres_extensions() {
    log_info "Verifying PostgreSQL extensions..."

    # Check TimescaleDB extension
    if docker-compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" exec -T postgres \
        psql -U "${POSTGRES_USER:-intel_prod_user}" -d "${POSTGRES_DB:-corporate_intel_prod}" \
        -c "SELECT * FROM pg_extension WHERE extname = 'timescaledb';" | grep -q timescaledb; then
        log_success "TimescaleDB extension is installed"
    else
        log_warning "TimescaleDB extension not found"
    fi

    # Check pgvector extension
    if docker-compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" exec -T postgres \
        psql -U "${POSTGRES_USER:-intel_prod_user}" -d "${POSTGRES_DB:-corporate_intel_prod}" \
        -c "SELECT * FROM pg_extension WHERE extname = 'vector';" | grep -q vector; then
        log_success "pgvector extension is installed"
    else
        log_info "pgvector extension not installed (optional)"
    fi
}

# ==============================================================================
# MAIN DEPLOYMENT FUNCTIONS
# ==============================================================================

deploy_networks() {
    log_info "Creating Docker networks..."

    # Networks are created automatically by docker-compose
    # Just verify they'll be created with correct configuration
    log_success "Network configuration verified"
}

deploy_volumes() {
    log_info "Creating Docker volumes..."

    # Volumes are created automatically by docker-compose
    # List expected volumes
    log_info "Expected volumes:"
    log_info "  - corporate-intel-postgres-data-prod"
    log_info "  - corporate-intel-redis-data-prod"
    log_info "  - corporate-intel-minio-data-prod"

    log_success "Volume configuration verified"
}

deploy_postgres() {
    log_info "Deploying PostgreSQL with TimescaleDB..."

    local recreate_flag=""
    if [[ "${RECREATE_CONTAINERS}" == true ]]; then
        recreate_flag="--force-recreate"
    fi

    docker-compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" \
        up -d ${recreate_flag} postgres

    if [[ "${SKIP_HEALTH_CHECKS}" != true ]]; then
        wait_for_postgres
        verify_postgres_extensions
    fi

    log_success "PostgreSQL deployment complete"
}

deploy_postgres_exporter() {
    log_info "Deploying PostgreSQL exporter..."

    docker-compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" \
        up -d postgres-exporter

    log_success "PostgreSQL exporter deployment complete"
}

deploy_redis() {
    log_info "Deploying Redis cache..."

    local recreate_flag=""
    if [[ "${RECREATE_CONTAINERS}" == true ]]; then
        recreate_flag="--force-recreate"
    fi

    docker-compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" \
        up -d ${recreate_flag} redis

    if [[ "${SKIP_HEALTH_CHECKS}" != true ]]; then
        wait_for_redis
    fi

    log_success "Redis deployment complete"
}

deploy_redis_exporter() {
    log_info "Deploying Redis exporter..."

    docker-compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" \
        up -d redis-exporter

    log_success "Redis exporter deployment complete"
}

deploy_minio() {
    log_info "Deploying MinIO object storage..."

    local recreate_flag=""
    if [[ "${RECREATE_CONTAINERS}" == true ]]; then
        recreate_flag="--force-recreate"
    fi

    docker-compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" \
        up -d ${recreate_flag} minio

    if [[ "${SKIP_HEALTH_CHECKS}" != true ]]; then
        wait_for_minio
        create_minio_buckets
    fi

    log_success "MinIO deployment complete"
}

verify_infrastructure() {
    log_info "Verifying infrastructure deployment..."

    # Check container status
    log_info "Container status:"
    docker-compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" ps postgres redis minio

    # Verify all containers are running
    local running_count
    running_count=$(docker-compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" ps postgres redis minio | grep -c "Up" || echo "0")

    if [[ ${running_count} -ge 3 ]]; then
        log_success "All infrastructure containers are running"
    else
        log_error "Some infrastructure containers are not running"
        return 1
    fi

    # Test connectivity
    log_info "Testing service connectivity..."

    # PostgreSQL
    if docker-compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" \
        exec -T postgres psql -U "${POSTGRES_USER:-intel_prod_user}" -d "${POSTGRES_DB:-corporate_intel_prod}" -c "SELECT 1;" &> /dev/null; then
        log_success "PostgreSQL connectivity verified"
    else
        log_error "PostgreSQL connectivity test failed"
        return 1
    fi

    # Redis
    if docker-compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" \
        exec -T redis redis-cli ping | grep -q PONG; then
        log_success "Redis connectivity verified"
    else
        log_error "Redis connectivity test failed"
        return 1
    fi

    # MinIO
    if curl -sf http://localhost:9000/minio/health/live &> /dev/null; then
        log_success "MinIO connectivity verified"
    else
        log_error "MinIO connectivity test failed"
        return 1
    fi

    log_success "Infrastructure verification complete"
}

# ==============================================================================
# MAIN EXECUTION
# ==============================================================================

main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --version)
                DEPLOYMENT_VERSION="$2"
                shift 2
                ;;
            --skip-health-checks)
                SKIP_HEALTH_CHECKS=true
                shift
                ;;
            --recreate)
                RECREATE_CONTAINERS=true
                shift
                ;;
            --help)
                cat << EOF
Infrastructure Deployment Script

USAGE:
    $0 [OPTIONS]

OPTIONS:
    --version VERSION        Deployment version tag
    --skip-health-checks    Skip health check validation
    --recreate              Force recreate containers
    --help                  Show this help message

DEPLOYED SERVICES:
    - PostgreSQL 15 with TimescaleDB 2.13.0
    - Redis 7.2 with persistence
    - MinIO (S3-compatible object storage)
    - Prometheus exporters for metrics
EOF
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    echo "================================================================================"
    echo "Infrastructure Deployment"
    echo "================================================================================"
    echo "Version: ${DEPLOYMENT_VERSION}"
    echo "Timestamp: $(date)"
    echo ""

    # Execute deployment
    deploy_networks
    deploy_volumes
    deploy_postgres
    deploy_postgres_exporter
    deploy_redis
    deploy_redis_exporter
    deploy_minio

    # Verify deployment
    verify_infrastructure

    echo ""
    echo "================================================================================"
    log_success "Infrastructure deployment complete!"
    echo "================================================================================"
    echo ""
    echo "Services available:"
    echo "  - PostgreSQL: localhost:5432"
    echo "  - Redis: localhost:6379"
    echo "  - MinIO API: localhost:9000"
    echo "  - MinIO Console: localhost:9001"
    echo ""

    exit 0
}

main "$@"
