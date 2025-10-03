#!/bin/bash

################################################################################
# Corporate Intelligence Platform - Staging Deployment Script
################################################################################
# Description: Automated deployment script for staging environment
# Version: 1.0.0
# Author: Staging Deployment Specialist Agent
# Date: 2025-10-02
################################################################################

set -euo pipefail

# Color codes for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# Configuration
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"
readonly DEPLOY_DIR="${DEPLOY_DIR:-/opt/corporate-intel/staging}"
readonly ENV_FILE="${PROJECT_ROOT}/.env.staging"
readonly BACKUP_DIR="${PROJECT_ROOT}/backups"
readonly LOG_FILE="${PROJECT_ROOT}/logs/deployment-$(date +%Y%m%d-%H%M%S).log"

# Deployment settings
readonly HEALTH_CHECK_RETRIES=30
readonly HEALTH_CHECK_INTERVAL=5
readonly DEPLOYMENT_TIMEOUT=600

################################################################################
# Utility Functions
################################################################################

log() {
  local level=$1
  shift
  local message="$@"
  local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

  echo -e "${timestamp} [${level}] ${message}" | tee -a "${LOG_FILE}"
}

log_info() {
  echo -e "${BLUE}ℹ${NC} $@"
  log "INFO" "$@"
}

log_success() {
  echo -e "${GREEN}✓${NC} $@"
  log "SUCCESS" "$@"
}

log_warning() {
  echo -e "${YELLOW}⚠${NC} $@"
  log "WARNING" "$@"
}

log_error() {
  echo -e "${RED}✗${NC} $@"
  log "ERROR" "$@"
}

error_exit() {
  log_error "$@"
  log_error "Deployment failed. Check ${LOG_FILE} for details."
  exit 1
}

check_command() {
  command -v "$1" >/dev/null 2>&1 || error_exit "$1 is required but not installed."
}

################################################################################
# Pre-flight Checks
################################################################################

preflight_checks() {
  log_info "=== Running Pre-flight Checks ==="

  # Check required commands
  check_command docker
  check_command docker-compose
  check_command curl
  check_command jq

  # Check Docker daemon
  if ! docker info >/dev/null 2>&1; then
    error_exit "Docker daemon is not running"
  fi
  log_success "Docker daemon is running"

  # Check environment file
  if [ ! -f "${ENV_FILE}" ]; then
    error_exit "Environment file not found: ${ENV_FILE}"
  fi
  log_success "Environment file found"

  # Check disk space (minimum 10GB)
  local available_space=$(df -BG "${PROJECT_ROOT}" | awk 'NR==2 {print $4}' | sed 's/G//')
  if [ "${available_space}" -lt 10 ]; then
    log_warning "Low disk space: ${available_space}GB available"
  else
    log_success "Sufficient disk space: ${available_space}GB available"
  fi

  # Check Docker Compose file
  if [ ! -f "${PROJECT_ROOT}/docker-compose.yml" ]; then
    error_exit "docker-compose.yml not found"
  fi
  log_success "docker-compose.yml found"

  # Validate docker-compose configuration
  cd "${PROJECT_ROOT}"
  if ! docker-compose --env-file "${ENV_FILE}" config >/dev/null 2>&1; then
    error_exit "Invalid docker-compose configuration"
  fi
  log_success "docker-compose configuration is valid"

  log_success "=== Pre-flight Checks Passed ==="
}

################################################################################
# Backup Current State
################################################################################

backup_current_state() {
  log_info "=== Creating Backup of Current State ==="

  mkdir -p "${BACKUP_DIR}"
  local backup_timestamp=$(date +%Y%m%d-%H%M%S)

  # Backup database if running
  if docker-compose ps postgres | grep -q "Up"; then
    log_info "Backing up database..."

    docker-compose exec -T postgres pg_dump \
      -U intel_staging_user \
      -d corporate_intel_staging \
      --clean \
      --if-exists \
      > "${BACKUP_DIR}/staging-db-${backup_timestamp}.sql" 2>/dev/null || {
      log_warning "Database backup failed (database may not exist yet)"
    }

    if [ -f "${BACKUP_DIR}/staging-db-${backup_timestamp}.sql" ]; then
      log_success "Database backup created: staging-db-${backup_timestamp}.sql"
    fi
  else
    log_info "Database not running, skipping backup"
  fi

  # Backup MinIO data if needed
  if docker-compose ps minio | grep -q "Up"; then
    log_info "MinIO is running (data persists in volumes)"
  fi

  # Keep only last 5 backups
  cd "${BACKUP_DIR}"
  ls -t staging-db-*.sql 2>/dev/null | tail -n +6 | xargs -r rm

  log_success "=== Backup Complete ==="
}

################################################################################
# Build Docker Image
################################################################################

build_docker_image() {
  log_info "=== Building Docker Image ==="

  cd "${PROJECT_ROOT}"

  local image_tag="staging-$(date +%Y%m%d-%H%M%S)"

  log_info "Building image: corporate-intel-api:${image_tag}"

  docker build \
    --tag "corporate-intel-api:${image_tag}" \
    --tag "corporate-intel-api:staging-latest" \
    --build-arg ENVIRONMENT=staging \
    --file Dockerfile \
    --progress=plain \
    . 2>&1 | tee -a "${LOG_FILE}"

  if [ ${PIPESTATUS[0]} -eq 0 ]; then
    log_success "Docker image built successfully: ${image_tag}"
  else
    error_exit "Docker image build failed"
  fi

  # Update image reference in docker-compose
  export DOCKER_IMAGE_TAG="${image_tag}"

  log_success "=== Docker Image Build Complete ==="
}

################################################################################
# Deploy Services
################################################################################

deploy_services() {
  log_info "=== Deploying Services ==="

  cd "${PROJECT_ROOT}"

  # Load environment variables
  set -a
  source "${ENV_FILE}"
  set +a

  # Pull dependency images
  log_info "Pulling dependency images..."
  docker-compose pull postgres redis minio jaeger prometheus grafana 2>&1 | tee -a "${LOG_FILE}"

  # Start infrastructure services first
  log_info "Starting infrastructure services (postgres, redis, minio)..."
  docker-compose up -d postgres redis minio

  # Wait for infrastructure to be healthy
  log_info "Waiting for infrastructure services to be healthy..."
  local retry=0
  while [ $retry -lt ${HEALTH_CHECK_RETRIES} ]; do
    local healthy_count=$(docker-compose ps | grep -c "Up (healthy)" || echo "0")

    if [ "${healthy_count}" -ge 3 ]; then
      log_success "Infrastructure services are healthy"
      break
    fi

    retry=$((retry + 1))
    log_info "Waiting for health checks... (${retry}/${HEALTH_CHECK_RETRIES})"
    sleep ${HEALTH_CHECK_INTERVAL}
  done

  if [ $retry -eq ${HEALTH_CHECK_RETRIES} ]; then
    error_exit "Infrastructure services failed to become healthy"
  fi

  # Run database migrations
  log_info "Running database migrations..."
  docker-compose run --rm api alembic upgrade head 2>&1 | tee -a "${LOG_FILE}"

  if [ ${PIPESTATUS[0]} -eq 0 ]; then
    log_success "Database migrations completed"
  else
    error_exit "Database migrations failed"
  fi

  # Start application and observability services
  log_info "Starting application and observability services..."
  docker-compose up -d

  log_success "=== Services Deployed ==="
}

################################################################################
# Health Checks
################################################################################

health_checks() {
  log_info "=== Running Health Checks ==="

  local api_url="http://localhost:8000"

  # Wait for API to be responsive
  log_info "Waiting for API to be responsive..."
  local retry=0
  while [ $retry -lt ${HEALTH_CHECK_RETRIES} ]; do
    if curl -sf "${api_url}/health" >/dev/null 2>&1; then
      log_success "API is responsive"
      break
    fi

    retry=$((retry + 1))
    log_info "Waiting for API... (${retry}/${HEALTH_CHECK_RETRIES})"
    sleep ${HEALTH_CHECK_INTERVAL}
  done

  if [ $retry -eq ${HEALTH_CHECK_RETRIES} ]; then
    error_exit "API failed to become responsive"
  fi

  # Detailed health checks
  log_info "Checking API health endpoint..."
  local health_response=$(curl -s "${api_url}/health")
  local health_status=$(echo "${health_response}" | jq -r '.status' 2>/dev/null || echo "unknown")

  if [ "${health_status}" == "healthy" ]; then
    log_success "API health check passed"
    echo "${health_response}" | jq '.' | tee -a "${LOG_FILE}"
  else
    log_error "API health check failed: ${health_response}"
    error_exit "API is not healthy"
  fi

  # Check database connectivity
  log_info "Checking database connectivity..."
  if docker-compose exec -T postgres pg_isready -U intel_staging_user >/dev/null 2>&1; then
    log_success "Database is ready"
  else
    error_exit "Database connectivity check failed"
  fi

  # Check Redis
  log_info "Checking Redis connectivity..."
  if docker-compose exec -T redis redis-cli ping 2>&1 | grep -q "PONG"; then
    log_success "Redis is ready"
  else
    error_exit "Redis connectivity check failed"
  fi

  # Check MinIO
  log_info "Checking MinIO availability..."
  if curl -sf http://localhost:9000/minio/health/live >/dev/null 2>&1; then
    log_success "MinIO is ready"
  else
    error_exit "MinIO availability check failed"
  fi

  # Check all containers are running
  log_info "Checking container status..."
  docker-compose ps | tee -a "${LOG_FILE}"

  local running_count=$(docker-compose ps | grep -c "Up" || echo "0")
  if [ "${running_count}" -ge 4 ]; then
    log_success "All required containers are running"
  else
    error_exit "Some containers are not running"
  fi

  log_success "=== All Health Checks Passed ==="
}

################################################################################
# Initialize Storage
################################################################################

initialize_storage() {
  log_info "=== Initializing Storage ==="

  # Check if mc (MinIO client) is available
  if ! command -v mc >/dev/null 2>&1; then
    log_warning "MinIO client (mc) not found, skipping bucket initialization"
    log_info "Install mc with: wget https://dl.min.io/client/mc/release/linux-amd64/mc"
    return 0
  fi

  # Configure MinIO client
  log_info "Configuring MinIO client..."
  mc alias set staging-minio http://localhost:9000 \
    "${MINIO_ACCESS_KEY:-intel_staging_admin}" \
    "${MINIO_SECRET_KEY}" \
    >/dev/null 2>&1 || {
    log_warning "Failed to configure MinIO client"
    return 0
  }

  # Create buckets
  log_info "Creating MinIO buckets..."
  mc mb staging-minio/staging-documents --ignore-existing 2>&1 | tee -a "${LOG_FILE}"
  mc mb staging-minio/staging-reports --ignore-existing 2>&1 | tee -a "${LOG_FILE}"

  # Set bucket policy for reports (public read)
  mc anonymous set download staging-minio/staging-reports 2>&1 | tee -a "${LOG_FILE}"

  # List buckets
  log_info "Available buckets:"
  mc ls staging-minio | tee -a "${LOG_FILE}"

  log_success "=== Storage Initialized ==="
}

################################################################################
# Post-Deployment Verification
################################################################################

post_deployment_verification() {
  log_info "=== Running Post-Deployment Verification ==="

  # API endpoint tests
  log_info "Testing API endpoints..."

  local api_url="http://localhost:8000"

  # Test health endpoint
  if curl -sf "${api_url}/health" | jq -e '.status == "healthy"' >/dev/null; then
    log_success "Health endpoint test passed"
  else
    log_warning "Health endpoint test failed"
  fi

  # Test API documentation
  if curl -sf "${api_url}/docs" >/dev/null 2>&1; then
    log_success "API documentation is accessible"
  else
    log_warning "API documentation is not accessible"
  fi

  # Database verification
  log_info "Verifying database schema..."
  local table_count=$(docker-compose exec -T postgres psql -U intel_staging_user -d corporate_intel_staging -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';" 2>/dev/null | tr -d ' ')

  if [ "${table_count}" -gt 0 ]; then
    log_success "Database schema verified (${table_count} tables)"
  else
    log_warning "Database schema verification failed"
  fi

  # Log collection
  log_info "Collecting deployment logs..."
  docker-compose logs --tail=50 > "${PROJECT_ROOT}/logs/deployment-services-$(date +%Y%m%d-%H%M%S).log"

  log_success "=== Post-Deployment Verification Complete ==="
}

################################################################################
# Display Deployment Summary
################################################################################

deployment_summary() {
  log_info "========================================="
  log_info "    STAGING DEPLOYMENT SUCCESSFUL"
  log_info "========================================="

  echo ""
  log_success "Application URL: http://localhost:8000"
  log_success "API Documentation: http://localhost:8000/docs"
  log_success "MinIO Console: http://localhost:9001"
  log_success "Jaeger UI: http://localhost:16686"
  log_success "Prometheus: http://localhost:9090"
  log_success "Grafana: http://localhost:3000"
  echo ""

  log_info "Service Status:"
  docker-compose ps
  echo ""

  log_info "Deployment Log: ${LOG_FILE}"
  log_info "Backup Directory: ${BACKUP_DIR}"
  echo ""

  log_info "Quick Commands:"
  echo "  View logs:        docker-compose logs -f api"
  echo "  Stop services:    docker-compose down"
  echo "  Restart API:      docker-compose restart api"
  echo "  Database console: docker-compose exec postgres psql -U intel_staging_user -d corporate_intel_staging"
  echo ""

  log_success "Next steps:"
  echo "  1. Run integration tests"
  echo "  2. Verify monitoring dashboards"
  echo "  3. Test critical workflows"
  echo "  4. Update deployment documentation"
  echo ""
}

################################################################################
# Rollback Function
################################################################################

rollback() {
  log_error "=== ROLLBACK INITIATED ==="

  # Stop current deployment
  docker-compose down

  # Restore database from latest backup if available
  local latest_backup=$(ls -t "${BACKUP_DIR}"/staging-db-*.sql 2>/dev/null | head -1)

  if [ -n "${latest_backup}" ]; then
    log_info "Restoring database from: ${latest_backup}"

    docker-compose up -d postgres
    sleep 15

    docker-compose exec -T postgres psql -U intel_staging_user -d corporate_intel_staging < "${latest_backup}"

    log_success "Database restored"
  fi

  # Use previous Docker image
  local previous_tag=$(docker images corporate-intel-api --format "{{.Tag}}" | grep staging | sed -n '2p')

  if [ -n "${previous_tag}" ]; then
    log_info "Rolling back to image: ${previous_tag}"
    export DOCKER_IMAGE_TAG="${previous_tag}"
  fi

  # Restart services
  docker-compose up -d

  log_warning "Rollback complete - please verify system status"
}

################################################################################
# Main Execution Flow
################################################################################

main() {
  local start_time=$(date +%s)

  # Create log directory
  mkdir -p "${PROJECT_ROOT}/logs"

  log_info "========================================="
  log_info "  Corporate Intelligence Platform"
  log_info "  Staging Deployment Script v1.0.0"
  log_info "========================================="
  log_info "Start time: $(date)"
  log_info "Environment: Staging"
  log_info "Project root: ${PROJECT_ROOT}"
  log_info "Log file: ${LOG_FILE}"
  echo ""

  # Trap errors and run rollback
  trap 'rollback' ERR

  # Deployment steps
  preflight_checks
  backup_current_state
  build_docker_image
  deploy_services
  health_checks
  initialize_storage
  post_deployment_verification

  # Calculate deployment time
  local end_time=$(date +%s)
  local duration=$((end_time - start_time))
  local minutes=$((duration / 60))
  local seconds=$((duration % 60))

  deployment_summary

  log_success "Total deployment time: ${minutes}m ${seconds}s"
  log_success "Deployment completed successfully at $(date)"

  exit 0
}

# Run main function
main "$@"
