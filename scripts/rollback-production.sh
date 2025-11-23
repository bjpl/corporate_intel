#!/bin/bash
################################################################################
# Production Rollback Script
# Corporate Intelligence Platform
################################################################################
# Version: 1.0.0
# Last Updated: October 17, 2025
#
# DESCRIPTION:
#   Emergency rollback script for production deployments. Restores previous
#   version of services, configurations, and optionally database state.
#
# USAGE:
#   ./scripts/rollback-production.sh [OPTIONS]
#
# OPTIONS:
#   --auto                  Automatic rollback (skip confirmations)
#   --reason "REASON"       Reason for rollback (required for auto)
#   --config-only           Rollback configuration only (not containers)
#   --database              Include database rollback (use with caution)
#   --timestamp TIMESTAMP   Specific backup timestamp to restore
#   --dry-run               Show what would be done without doing it
#   --help                  Show this help message
#
# WARNING:
#   Database rollbacks can result in data loss. Only use --database flag
#   if absolutely necessary and after confirming data loss is acceptable.
#
# EXIT CODES:
#   0 - Rollback successful
#   1 - Rollback failed
#   2 - No backups available
#   3 - User cancelled
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
readonly BACKUP_DIR="${PROJECT_ROOT}/backups/deployments"
readonly INCIDENT_DIR="${PROJECT_ROOT}/incident-snapshots"
readonly TIMESTAMP="$(date +%Y%m%d_%H%M%S)"

# Rollback options
AUTO_ROLLBACK=false
ROLLBACK_REASON=""
CONFIG_ONLY=false
INCLUDE_DATABASE=false
SPECIFIC_TIMESTAMP=""
DRY_RUN=false

# Colors
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly RED='\033[0;31m'
readonly BLUE='\033[0;34m'
readonly MAGENTA='\033[0;35m'
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

log_critical() {
    echo -e "${RED}${MAGENTA}[CRITICAL]${NC} 🚨 $*"
}

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

confirm_action() {
    local message="$1"

    if [[ "${AUTO_ROLLBACK}" == true ]]; then
        log_info "Auto-rollback enabled - skipping confirmation"
        return 0
    fi

    echo -e "${YELLOW}${message}${NC}"
    read -r -p "Continue? [y/N] " response

    case "$response" in
        [yY][eE][sS]|[yY])
            return 0
            ;;
        *)
            log_warning "Rollback cancelled by user"
            exit 3
            ;;
    esac
}

find_latest_backup() {
    log_info "Looking for latest backup..."

    if [[ ! -d "${BACKUP_DIR}" ]]; then
        log_error "Backup directory not found: ${BACKUP_DIR}"
        return 2
    fi

    # Find latest docker-compose backup
    local latest_compose
    latest_compose=$(ls -t "${BACKUP_DIR}"/docker-compose.production.yml.* 2>/dev/null | head -1 || echo "")

    if [[ -z "${latest_compose}" ]]; then
        log_error "No backups found in ${BACKUP_DIR}"
        return 2
    fi

    # Extract timestamp from filename
    SPECIFIC_TIMESTAMP=$(basename "${latest_compose}" | sed 's/docker-compose.production.yml.//')

    log_success "Latest backup found: ${SPECIFIC_TIMESTAMP}"
    return 0
}

create_incident_snapshot() {
    log_info "Creating incident snapshot..."

    local snapshot_dir="${INCIDENT_DIR}/${TIMESTAMP}"
    mkdir -p "${snapshot_dir}"

    # Save current configuration
    if [[ -f "${COMPOSE_FILE}" ]]; then
        cp "${COMPOSE_FILE}" "${snapshot_dir}/docker-compose.production.yml" || log_warning "Failed to backup compose file"
    fi

    if [[ -f "${ENV_FILE}" ]]; then
        cp "${ENV_FILE}" "${snapshot_dir}/.env.production" || log_warning "Failed to backup env file"
    fi

    # Export container logs
    log_info "Exporting container logs..."
    if docker-compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" ps &> /dev/null; then
        docker-compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" logs --tail=500 > "${snapshot_dir}/logs-before-rollback.txt" 2>&1 || true
    fi

    # Save metrics snapshot
    if curl -sf http://localhost:9090/api/v1/query?query=up &> /dev/null; then
        curl -s http://localhost:9090/api/v1/query?query=up > "${snapshot_dir}/metrics-snapshot.json" 2>&1 || true
    fi

    # Document rollback reason
    cat > "${snapshot_dir}/rollback-info.txt" << EOF
Rollback initiated at: $(date)
Rollback reason: ${ROLLBACK_REASON}
Rollback user: ${USER}
Rollback host: $(hostname)
Restoring backup from: ${SPECIFIC_TIMESTAMP}
EOF

    log_success "Incident snapshot saved to: ${snapshot_dir}"
}

# ==============================================================================
# ROLLBACK FUNCTIONS
# ==============================================================================

rollback_containers() {
    log_info "Rolling back containers..."

    if [[ "${DRY_RUN}" == true ]]; then
        log_info "[DRY RUN] Would stop current containers"
        log_info "[DRY RUN] Would start previous version"
        return 0
    fi

    # Stop current containers
    log_info "Stopping current containers..."
    docker-compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" down --timeout 30 2>&1 || log_warning "Some containers may not have stopped cleanly"

    # Wait for containers to fully stop
    sleep 5

    # Start previous version
    log_info "Starting previous version..."
    docker-compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" up -d

    log_success "Containers rolled back"
}

rollback_configuration() {
    log_info "Rolling back configuration..."

    if [[ "${DRY_RUN}" == true ]]; then
        log_info "[DRY RUN] Would restore configuration files"
        return 0
    fi

    # Backup current configuration (for recovery if rollback fails)
    cp "${COMPOSE_FILE}" "${COMPOSE_FILE}.failed" 2>/dev/null || true
    cp "${ENV_FILE}" "${ENV_FILE}.failed" 2>/dev/null || true

    # Restore previous docker-compose file
    local compose_backup="${BACKUP_DIR}/docker-compose.production.yml.${SPECIFIC_TIMESTAMP}"
    if [[ -f "${compose_backup}" ]]; then
        cp "${compose_backup}" "${COMPOSE_FILE}"
        log_success "Docker Compose file restored"
    else
        log_error "Docker Compose backup not found: ${compose_backup}"
        return 1
    fi

    # Restore previous environment file
    local env_backup="${BACKUP_DIR}/.env.production.${SPECIFIC_TIMESTAMP}"
    if [[ -f "${env_backup}" ]]; then
        cp "${env_backup}" "${ENV_FILE}"
        log_success "Environment file restored"
    else
        log_warning "Environment file backup not found: ${env_backup}"
    fi

    log_success "Configuration rolled back"
}

rollback_database() {
    log_critical "Database rollback requested - THIS CAN CAUSE DATA LOSS!"

    if [[ "${AUTO_ROLLBACK}" != true ]]; then
        confirm_action "⚠️  WARNING: Database rollback will restore to ${SPECIFIC_TIMESTAMP}. All data changes since then will be LOST!"
    fi

    if [[ "${DRY_RUN}" == true ]]; then
        log_info "[DRY RUN] Would rollback database to ${SPECIFIC_TIMESTAMP}"
        return 0
    fi

    # Find database backup
    local db_backup="${PROJECT_ROOT}/backups/postgres/corporate_intel_prod_${SPECIFIC_TIMESTAMP}.backup"

    if [[ ! -f "${db_backup}" ]]; then
        log_error "Database backup not found: ${db_backup}"
        log_info "Available backups:"
        ls -lh "${PROJECT_ROOT}/backups/postgres/" | tail -5
        return 1
    fi

    log_info "Stopping API to prevent connections..."
    docker-compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" stop api || true

    log_info "Creating pre-rollback database backup..."
    docker-compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" exec -T postgres \
        pg_dump -U "${POSTGRES_USER:-intel_prod_user}" -d "${POSTGRES_DB:-corporate_intel_prod}" -F c \
        -f "/backups/pre-rollback-${TIMESTAMP}.backup" 2>&1 || log_warning "Pre-rollback backup failed"

    log_info "Restoring database from ${SPECIFIC_TIMESTAMP}..."

    # Drop and recreate database
    docker-compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" exec -T postgres psql -U "${POSTGRES_USER:-intel_prod_user}" -c "
        DROP DATABASE IF EXISTS ${POSTGRES_DB:-corporate_intel_prod}_restore;
        CREATE DATABASE ${POSTGRES_DB:-corporate_intel_prod}_restore;
    "

    # Restore backup
    docker-compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" exec -T postgres \
        pg_restore -U "${POSTGRES_USER:-intel_prod_user}" -d "${POSTGRES_DB:-corporate_intel_prod}_restore" \
        -v < "${db_backup}" 2>&1 || log_error "Database restore failed"

    # Swap databases
    docker-compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" exec -T postgres psql -U "${POSTGRES_USER:-intel_prod_user}" -c "
        ALTER DATABASE ${POSTGRES_DB:-corporate_intel_prod} RENAME TO ${POSTGRES_DB:-corporate_intel_prod}_old;
        ALTER DATABASE ${POSTGRES_DB:-corporate_intel_prod}_restore RENAME TO ${POSTGRES_DB:-corporate_intel_prod};
    "

    log_success "Database rolled back"

    # Restart API
    log_info "Restarting API..."
    docker-compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" start api

    log_warning "Old database preserved as ${POSTGRES_DB}_old - can be dropped after verification"
}

verify_rollback() {
    log_info "Verifying rollback..."

    if [[ "${DRY_RUN}" == true ]]; then
        log_info "[DRY RUN] Would verify rollback"
        return 0
    fi

    # Wait for services to start
    log_info "Waiting for services to be ready..."
    sleep 15

    # Check container status
    log_info "Checking container status..."
    docker-compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" ps

    # Test API health
    log_info "Testing API health..."
    local retries=0
    while [[ ${retries} -lt 24 ]]; do
        if curl -sf http://localhost:8000/health &> /dev/null; then
            log_success "API is responding"
            curl -s http://localhost:8000/health | jq '.' || true
            break
        fi

        ((retries++))
        log_info "Waiting for API... (${retries}/24)"
        sleep 5
    done

    if [[ ${retries} -eq 24 ]]; then
        log_error "API did not become healthy after rollback"
        log_error "Check logs: docker-compose -f ${COMPOSE_FILE} logs api"
        return 1
    fi

    # Test database connectivity
    if docker-compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" \
        exec -T postgres pg_isready -U "${POSTGRES_USER:-intel_prod_user}" &> /dev/null; then
        log_success "PostgreSQL is responding"
    else
        log_error "PostgreSQL is not responding"
        return 1
    fi

    # Test Redis connectivity
    if docker-compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" \
        exec -T redis redis-cli ping | grep -q "PONG"; then
        log_success "Redis is responding"
    else
        log_error "Redis is not responding"
        return 1
    fi

    log_success "Rollback verification complete"
    return 0
}

# ==============================================================================
# MAIN EXECUTION
# ==============================================================================

main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --auto)
                AUTO_ROLLBACK=true
                shift
                ;;
            --reason)
                ROLLBACK_REASON="$2"
                shift 2
                ;;
            --config-only)
                CONFIG_ONLY=true
                shift
                ;;
            --database)
                INCLUDE_DATABASE=true
                shift
                ;;
            --timestamp)
                SPECIFIC_TIMESTAMP="$2"
                shift 2
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --help)
                cat << EOF
Production Rollback Script

USAGE:
    $0 [OPTIONS]

OPTIONS:
    --auto                  Automatic rollback (skip confirmations)
    --reason "REASON"       Reason for rollback (required for auto)
    --config-only           Rollback configuration only (not containers)
    --database              Include database rollback (use with caution)
    --timestamp TIMESTAMP   Specific backup timestamp to restore
    --dry-run               Show what would be done without doing it
    --help                  Show this help message

WARNING:
    Database rollbacks can result in data loss. Only use --database flag
    if absolutely necessary and after confirming data loss is acceptable.

EXAMPLES:
    $0                                    # Interactive rollback to latest backup
    $0 --auto --reason "API not starting" # Automatic rollback
    $0 --timestamp 20251017_120000        # Rollback to specific backup
    $0 --dry-run                          # Test rollback without changes
EOF
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    # Validate requirements
    if [[ "${AUTO_ROLLBACK}" == true ]] && [[ -z "${ROLLBACK_REASON}" ]]; then
        log_error "Rollback reason required for automatic rollback (--reason)"
        exit 1
    fi

    # Display rollback information
    echo "================================================================================"
    echo -e "${RED}PRODUCTION ROLLBACK${NC}"
    echo "================================================================================"
    echo "Timestamp: $(date)"
    echo "User: ${USER}"
    echo "Host: $(hostname)"
    echo "Reason: ${ROLLBACK_REASON:-Interactive rollback}"
    echo ""

    if [[ "${DRY_RUN}" == true ]]; then
        log_warning "DRY RUN MODE - No changes will be made"
        echo ""
    fi

    # Find backup to restore
    if [[ -z "${SPECIFIC_TIMESTAMP}" ]]; then
        find_latest_backup || exit 2
    else
        log_info "Using specified backup timestamp: ${SPECIFIC_TIMESTAMP}"
    fi

    # Confirm rollback
    if [[ "${DRY_RUN}" != true ]]; then
        confirm_action "🚨 You are about to ROLLBACK production to backup: ${SPECIFIC_TIMESTAMP}"
    fi

    # Create incident snapshot
    create_incident_snapshot

    # Execute rollback
    log_info "Starting rollback procedure..."
    echo ""

    rollback_configuration

    if [[ "${CONFIG_ONLY}" != true ]]; then
        rollback_containers
    fi

    if [[ "${INCLUDE_DATABASE}" == true ]]; then
        rollback_database
    fi

    # Verify rollback
    verify_rollback

    # Summary
    echo ""
    echo "================================================================================"
    log_success "Rollback completed successfully!"
    echo "================================================================================"
    echo ""
    echo "Rollback details:"
    echo "  Restored from: ${SPECIFIC_TIMESTAMP}"
    echo "  Incident snapshot: ${INCIDENT_DIR}/${TIMESTAMP}"
    echo "  Configuration: Rolled back"
    echo "  Containers: $(if [[ "${CONFIG_ONLY}" == true ]]; then echo "Not rolled back"; else echo "Rolled back"; fi)"
    echo "  Database: $(if [[ "${INCLUDE_DATABASE}" == true ]]; then echo "Rolled back"; else echo "Not rolled back"; fi)"
    echo ""
    echo "Next steps:"
    echo "  1. Verify application is working correctly"
    echo "  2. Check logs: docker-compose -f ${COMPOSE_FILE} logs -f api"
    echo "  3. Monitor metrics in Grafana"
    echo "  4. Create incident report documenting the issue"
    echo "  5. Schedule post-mortem meeting"
    echo ""

    exit 0
}

main "$@"
