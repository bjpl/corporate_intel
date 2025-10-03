#!/bin/bash

################################################################################
# Corporate Intelligence Platform - Staging Rollback Script
################################################################################
# Description: Automated rollback script for staging environment
# Version: 1.0.0
# Author: Staging Deployment Specialist Agent
# Date: 2025-10-02
################################################################################

set -euo pipefail

# Color codes
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m'

# Configuration
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"
readonly BACKUP_DIR="${PROJECT_ROOT}/backups"
readonly LOG_FILE="${PROJECT_ROOT}/logs/rollback-$(date +%Y%m%d-%H%M%S).log"

################################################################################
# Utility Functions
################################################################################

log_info() {
  echo -e "${BLUE}ℹ${NC} $@" | tee -a "${LOG_FILE}"
}

log_success() {
  echo -e "${GREEN}✓${NC} $@" | tee -a "${LOG_FILE}"
}

log_warning() {
  echo -e "${YELLOW}⚠${NC} $@" | tee -a "${LOG_FILE}"
}

log_error() {
  echo -e "${RED}✗${NC} $@" | tee -a "${LOG_FILE}"
}

################################################################################
# Rollback Functions
################################################################################

confirm_rollback() {
  log_warning "========================================="
  log_warning "  ROLLBACK INITIATED"
  log_warning "========================================="
  echo ""
  log_warning "This will:"
  echo "  1. Stop current deployment"
  echo "  2. Restore previous Docker image"
  echo "  3. Restore database from backup (optional)"
  echo "  4. Restart services"
  echo ""

  read -p "Are you sure you want to rollback? (yes/no): " -r
  echo

  if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    log_info "Rollback cancelled"
    exit 0
  fi
}

stop_current_deployment() {
  log_info "=== Stopping Current Deployment ==="

  cd "${PROJECT_ROOT}"

  log_info "Stopping all services..."
  docker-compose down

  log_success "Services stopped"
}

restore_previous_image() {
  log_info "=== Restoring Previous Docker Image ==="

  # Get previous image tag
  local previous_tag=$(docker images corporate-intel-api --format "{{.Tag}}" | grep staging | sed -n '2p')

  if [ -z "${previous_tag}" ]; then
    log_error "No previous image found"
    return 1
  fi

  log_info "Previous image tag: ${previous_tag}"

  # Tag as latest
  docker tag "corporate-intel-api:${previous_tag}" "corporate-intel-api:staging-latest"

  log_success "Previous image restored: ${previous_tag}"
}

restore_database_backup() {
  log_info "=== Database Rollback ==="

  # Check if database backup exists
  local latest_backup=$(ls -t "${BACKUP_DIR}"/staging-db-*.sql 2>/dev/null | head -1)

  if [ -z "${latest_backup}" ]; then
    log_warning "No database backup found, skipping database restoration"
    return 0
  fi

  log_info "Latest backup: $(basename ${latest_backup})"

  read -p "Restore database from backup? (yes/no): " -r
  echo

  if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    log_info "Skipping database restoration"
    return 0
  fi

  # Start PostgreSQL
  log_info "Starting PostgreSQL..."
  docker-compose up -d postgres
  sleep 15

  # Wait for PostgreSQL to be ready
  timeout 60 bash -c 'until docker-compose exec -T postgres pg_isready -U intel_staging_user; do sleep 2; done'

  # Restore database
  log_info "Restoring database from: ${latest_backup}"
  docker-compose exec -T postgres psql -U intel_staging_user -d corporate_intel_staging < "${latest_backup}"

  log_success "Database restored successfully"
}

rollback_migrations() {
  log_info "=== Rolling Back Database Migrations ==="

  read -p "How many migrations to rollback? (0 to skip): " -r
  echo

  if [ "$REPLY" -eq 0 ]; then
    log_info "Skipping migration rollback"
    return 0
  fi

  local steps=$REPLY

  docker-compose run --rm api alembic downgrade -${steps}

  log_success "Rolled back ${steps} migration(s)"
}

restart_services() {
  log_info "=== Restarting Services ==="

  cd "${PROJECT_ROOT}"

  # Start all services
  log_info "Starting services with previous version..."
  docker-compose up -d

  # Wait for services to be healthy
  log_info "Waiting for services to be healthy..."
  sleep 30

  # Check health
  if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
    log_success "API is responsive"
  else
    log_error "API is not responsive"
    return 1
  fi

  # Display service status
  docker-compose ps

  log_success "Services restarted successfully"
}

verify_rollback() {
  log_info "=== Verifying Rollback ==="

  # Run health checks
  bash "${SCRIPT_DIR}/health-check.sh" 2>/dev/null || {
    log_warning "Health check script not found, running basic checks..."

    # Basic health checks
    curl -sf http://localhost:8000/health | jq '.' || log_error "Health check failed"

    docker-compose exec -T postgres pg_isready -U intel_staging_user || log_error "Database check failed"

    docker-compose exec -T redis redis-cli ping || log_error "Redis check failed"
  }

  log_success "Rollback verification complete"
}

rollback_summary() {
  log_info "========================================="
  log_info "  ROLLBACK COMPLETE"
  log_info "========================================="
  echo ""
  log_success "Rollback completed at $(date)"
  echo ""
  log_info "Service Status:"
  docker-compose ps
  echo ""
  log_info "Next Steps:"
  echo "  1. Verify critical functionality"
  echo "  2. Check application logs: docker-compose logs -f api"
  echo "  3. Monitor for any errors"
  echo "  4. Investigate root cause of deployment failure"
  echo ""
  log_info "Rollback log: ${LOG_FILE}"
}

################################################################################
# Main Execution
################################################################################

main() {
  mkdir -p "${PROJECT_ROOT}/logs"

  log_info "Corporate Intelligence Platform - Rollback Script v1.0.0"
  log_info "Start time: $(date)"
  echo ""

  confirm_rollback
  stop_current_deployment
  restore_previous_image

  # Optional: Restore database
  restore_database_backup

  # Optional: Rollback migrations
  # rollback_migrations

  restart_services
  verify_rollback
  rollback_summary

  log_success "Rollback process completed successfully"

  exit 0
}

main "$@"
