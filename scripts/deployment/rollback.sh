#!/bin/bash
# Emergency Rollback Script for Corporate Intelligence Platform
# Usage: ./rollback.sh [--emergency] [--to-version <tag>] [--dry-run]
#
# Target: Complete rollback in <10 minutes
# Supports: Application rollback, database rollback (if safe), service restoration

set -euo pipefail
IFS=$'\n\t'

# Script metadata
SCRIPT_VERSION="1.0.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
LOG_FILE="${PROJECT_ROOT}/logs/rollback-$(date +%Y%m%d_%H%M%S).log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
NC='\033[0m'

# Rollback configuration
EMERGENCY_MODE=false
TARGET_VERSION=""
DRY_RUN=false
ROLLBACK_DB=false
COMPOSE_FILE=""
ROLLBACK_START_TIME=$(date +%s)

# Logging functions
log() {
    local level=$1
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local elapsed=$(($(date +%s) - ROLLBACK_START_TIME))
    echo -e "${timestamp} [${elapsed}s] [${level}] ${message}" | tee -a "${LOG_FILE}"
}

log_info() { log "INFO" "${BLUE}$*${NC}"; }
log_success() { log "SUCCESS" "${GREEN}✓ $*${NC}"; }
log_warning() { log "WARNING" "${YELLOW}⚠ $*${NC}"; }
log_error() { log "ERROR" "${RED}✗ $*${NC}"; }
log_critical() { log "CRITICAL" "${MAGENTA}☠ $*${NC}"; }

# Error handler
handle_error() {
    local line_num=$1
    log_critical "Rollback failed at line ${line_num}"
    log_critical "System may be in inconsistent state!"
    log_critical "Manual intervention required"
    log_critical "Log file: ${LOG_FILE}"
    exit 1
}

trap 'handle_error ${LINENO}' ERR

# Parse arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --emergency)
                EMERGENCY_MODE=true
                log_warning "EMERGENCY MODE ACTIVATED"
                shift
                ;;
            --to-version)
                TARGET_VERSION="$2"
                log_info "Rolling back to version: ${TARGET_VERSION}"
                shift 2
                ;;
            --rollback-db)
                ROLLBACK_DB=true
                log_warning "Database rollback enabled"
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                log_info "Dry run mode - no changes will be made"
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

Emergency rollback script for Corporate Intelligence Platform.

⚠️  CRITICAL: This performs emergency rollback. Use only when necessary.

OPTIONS:
    --emergency             Emergency mode (skip confirmations)
    --to-version <tag>      Rollback to specific git tag
    --rollback-db           Also rollback database (DANGEROUS)
    --dry-run              Preview rollback actions
    -h, --help             Show this help message

EXAMPLES:
    $0 --emergency                          # Fast emergency rollback
    $0 --to-version v1.0.0                  # Rollback to specific version
    $0 --emergency --rollback-db            # Full rollback including DB

ROLLBACK TARGET: <10 minutes

PHASES:
    1. Stop current services (30 seconds)
    2. Restore previous version (2 minutes)
    3. Database rollback (optional, 3 minutes)
    4. Start services (2 minutes)
    5. Validate health (2 minutes)

EOF
}

# Detect environment and compose file
detect_environment() {
    log_info "Detecting deployment environment..."

    # Check which services are running
    if docker ps --format '{{.Names}}' | grep -q "corporate-intel-nginx"; then
        COMPOSE_FILE="docker-compose.prod.yml"
        log_info "Detected PRODUCTION environment"
    elif docker ps --format '{{.Names}}' | grep -q "corporate-intel.*staging"; then
        COMPOSE_FILE="docker-compose.staging.yml"
        log_info "Detected STAGING environment"
    else
        log_warning "Could not detect environment, using production"
        COMPOSE_FILE="docker-compose.prod.yml"
    fi

    if [ ! -f "${PROJECT_ROOT}/${COMPOSE_FILE}" ]; then
        log_error "Compose file not found: ${COMPOSE_FILE}"
        exit 1
    fi

    log_success "Using compose file: ${COMPOSE_FILE}"
}

# Confirm rollback (unless emergency mode)
confirm_rollback() {
    if [ "${EMERGENCY_MODE}" = true ] || [ "${DRY_RUN}" = true ]; then
        return 0
    fi

    log_critical "=========================================="
    log_critical "EMERGENCY ROLLBACK CONFIRMATION"
    log_critical "=========================================="
    log_warning "This will rollback the production deployment!"
    log_warning "Current services will be stopped and replaced"
    log_info ""

    read -p "Type 'ROLLBACK NOW' to confirm: " -r
    if [ "$REPLY" != "ROLLBACK NOW" ]; then
        log_info "Rollback cancelled by user"
        exit 0
    fi

    log_success "Rollback confirmed, proceeding..."
}

# Get current deployment version
get_current_version() {
    log_info "Detecting current deployment version..."

    cd "${PROJECT_ROOT}"
    local current_commit=$(git rev-parse --short HEAD)
    local current_tag=$(git describe --tags --exact-match 2>/dev/null || echo "")

    log_info "Current commit: ${current_commit}"

    if [ -n "${current_tag}" ]; then
        log_info "Current tag: ${current_tag}"
    else
        log_warning "No tag on current commit"
    fi
}

# Determine rollback target version
determine_rollback_target() {
    log_info "Determining rollback target version..."

    cd "${PROJECT_ROOT}"

    if [ -n "${TARGET_VERSION}" ]; then
        # User specified target version
        if git rev-parse "${TARGET_VERSION}" >/dev/null 2>&1; then
            log_success "Target version: ${TARGET_VERSION}"
        else
            log_error "Invalid target version: ${TARGET_VERSION}"
            exit 1
        fi
    else
        # Find previous tagged version
        local previous_tag=$(git describe --abbrev=0 --tags "$(git rev-list --tags --skip=1 --max-count=1)" 2>/dev/null || echo "")

        if [ -n "${previous_tag}" ]; then
            TARGET_VERSION="${previous_tag}"
            log_success "Auto-detected previous version: ${TARGET_VERSION}"
        else
            log_error "Could not determine previous version"
            log_error "Specify version with: --to-version <tag>"
            exit 1
        fi
    fi
}

# Stop current services
stop_current_services() {
    log_info "Stopping current services..."
    local stop_start_time=$(date +%s)

    if [ "${DRY_RUN}" = true ]; then
        log_info "[DRY RUN] Would stop services"
        return 0
    fi

    cd "${PROJECT_ROOT}"

    # Graceful shutdown with timeout
    timeout 30 docker-compose -f "${COMPOSE_FILE}" down || {
        log_warning "Graceful shutdown timed out, forcing stop..."
        docker-compose -f "${COMPOSE_FILE}" down --timeout 5
    }

    local stop_duration=$(($(date +%s) - stop_start_time))
    log_success "Services stopped in ${stop_duration} seconds"
}

# Restore previous version
restore_previous_version() {
    log_info "Restoring version: ${TARGET_VERSION}..."
    local restore_start_time=$(date +%s)

    if [ "${DRY_RUN}" = true ]; then
        log_info "[DRY RUN] Would checkout ${TARGET_VERSION}"
        return 0
    fi

    cd "${PROJECT_ROOT}"

    # Stash any uncommitted changes
    if [ -n "$(git status --porcelain)" ]; then
        log_warning "Stashing uncommitted changes..."
        git stash push -m "Rollback stash $(date +%Y%m%d_%H%M%S)"
    fi

    # Checkout target version
    log_info "Checking out ${TARGET_VERSION}..."
    git checkout "${TARGET_VERSION}"

    # Verify checkout
    local checked_out_version=$(git describe --tags --exact-match 2>/dev/null || git rev-parse --short HEAD)
    log_success "Checked out version: ${checked_out_version}"

    # Rebuild images for rolled back version
    log_info "Rebuilding images for rolled back version..."
    docker-compose -f "${COMPOSE_FILE}" build --no-cache 2>&1 | tail -20

    local restore_duration=$(($(date +%s) - restore_start_time))
    log_success "Version restored in ${restore_duration} seconds"
}

# Rollback database (if requested)
rollback_database() {
    if [ "${ROLLBACK_DB}" = false ]; then
        log_info "Database rollback not requested, skipping"
        return 0
    fi

    log_warning "Starting database rollback..."
    local db_rollback_start=$(date +%s)

    if [ "${DRY_RUN}" = true ]; then
        log_info "[DRY RUN] Would rollback database"
        return 0
    fi

    # Check if Alembic migrations exist
    if [ -d "${PROJECT_ROOT}/alembic" ]; then
        log_info "Rolling back Alembic migrations..."

        # Start postgres for migrations
        docker-compose -f "${COMPOSE_FILE}" up -d postgres
        sleep 10

        # Rollback one version
        docker-compose -f "${COMPOSE_FILE}" run --rm api alembic downgrade -1

        log_success "Database rolled back one migration"
    else
        log_warning "No migration system found, skipping database rollback"
    fi

    # Alternative: Restore from backup
    local backup_script="${SCRIPT_DIR}/../backup/restore-database.sh"
    if [ -f "${backup_script}" ]; then
        log_info "Database backup restoration script found"

        if [ "${EMERGENCY_MODE}" = true ]; then
            log_warning "Restoring latest database backup..."
            bash "${backup_script}" --latest
        else
            log_info "To restore from backup manually, run:"
            log_info "  ${backup_script} --latest"
        fi
    fi

    local db_duration=$(($(date +%s) - db_rollback_start))
    log_success "Database rollback completed in ${db_duration} seconds"
}

# Start services with rolled back version
start_services() {
    log_info "Starting services with rolled back version..."
    local start_start_time=$(date +%s)

    if [ "${DRY_RUN}" = true ]; then
        log_info "[DRY RUN] Would start services"
        return 0
    fi

    cd "${PROJECT_ROOT}"

    # Start all services
    docker-compose -f "${COMPOSE_FILE}" up -d

    local start_duration=$(($(date +%s) - start_start_time))
    log_success "Services started in ${start_duration} seconds"
}

# Validate rolled back deployment
validate_rollback() {
    log_info "Validating rolled back deployment..."
    local validate_start_time=$(date +%s)

    if [ "${DRY_RUN}" = true ]; then
        log_info "[DRY RUN] Would validate rollback"
        return 0
    fi

    local max_retries=20
    local retry_interval=5
    local api_url="http://localhost:8000"

    # Wait for API to respond
    log_info "Waiting for API to be healthy..."
    local retries=0
    while [ ${retries} -lt ${max_retries} ]; do
        if curl -sf "${api_url}/health" > /dev/null 2>&1; then
            log_success "API is responding"
            break
        fi

        retries=$((retries + 1))
        if [ ${retries} -eq ${max_retries} ]; then
            log_error "API failed to respond after rollback"
            return 1
        fi

        log_info "Waiting for API... (${retries}/${max_retries})"
        sleep ${retry_interval}
    done

    # Run critical health checks
    log_info "Running critical health checks..."
    local health_failures=0

    local critical_endpoints=(
        "${api_url}/health"
        "${api_url}/api/v1/health/database"
        "${api_url}/api/v1/health/ready"
    )

    for endpoint in "${critical_endpoints[@]}"; do
        if curl -sf "${endpoint}" > /dev/null 2>&1; then
            log_success "✓ ${endpoint}"
        else
            log_error "✗ ${endpoint}"
            health_failures=$((health_failures + 1))
        fi
    done

    if [ ${health_failures} -gt 0 ]; then
        log_error "Health validation failed: ${health_failures} failures"
        return 1
    fi

    # Check container status
    log_info "Checking container status..."
    local unhealthy_containers=$(docker-compose -f "${COMPOSE_FILE}" ps | grep -v "Up (healthy)\|Up$" | grep -v "NAME\|---" | wc -l)

    if [ ${unhealthy_containers} -gt 0 ]; then
        log_warning "${unhealthy_containers} containers are not healthy"
        docker-compose -f "${COMPOSE_FILE}" ps
    else
        log_success "All containers are healthy"
    fi

    local validate_duration=$(($(date +%s) - validate_start_time))
    log_success "Validation completed in ${validate_duration} seconds"
}

# Generate rollback report
generate_rollback_report() {
    log_info "Generating rollback report..."

    local report_file="${PROJECT_ROOT}/logs/rollback-report-$(date +%Y%m%d_%H%M%S).md"
    local total_duration=$(($(date +%s) - ROLLBACK_START_TIME))

    cat > "${report_file}" << EOF
# Emergency Rollback Report

**Date**: $(date '+%Y-%m-%d %H:%M:%S %Z')
**Script Version**: ${SCRIPT_VERSION}
**Total Duration**: ${total_duration} seconds
**Target**: <10 minutes (600 seconds)
**Status**: $([[ ${total_duration} -lt 600 ]] && echo "✓ SUCCESS" || echo "⚠ EXCEEDED TARGET")

## Rollback Details

- **Emergency Mode**: ${EMERGENCY_MODE}
- **Target Version**: ${TARGET_VERSION}
- **Database Rollback**: ${ROLLBACK_DB}
- **Environment**: ${COMPOSE_FILE}

## Git Information

- **Current Branch**: $(git rev-parse --abbrev-ref HEAD)
- **Current Commit**: $(git rev-parse --short HEAD)
- **Current Tag**: $(git describe --tags --exact-match 2>/dev/null || echo "No tag")

## Timeline

- **Rollback Started**: $(date -d "@${ROLLBACK_START_TIME}" '+%Y-%m-%d %H:%M:%S')
- **Rollback Completed**: $(date '+%Y-%m-%d %H:%M:%S')
- **Total Duration**: ${total_duration} seconds

## Container Status

\`\`\`
$(docker-compose -f "${COMPOSE_FILE}" ps)
\`\`\`

## Health Checks

$(for endpoint in health api/v1/health/database api/v1/health/ready; do
    echo "### /${endpoint}"
    curl -s "http://localhost:8000/${endpoint}" 2>/dev/null || echo "Endpoint unavailable"
    echo ""
done)

## Next Steps

1. ✓ Services have been rolled back to ${TARGET_VERSION}
2. Monitor application health closely
3. Investigate root cause of failure
4. Review logs: ${LOG_FILE}
5. Plan corrective actions before next deployment

## Monitoring

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000
- **Logs**: docker-compose -f ${COMPOSE_FILE} logs -f

## Incident Documentation

Document the incident:
- What triggered the rollback?
- What was the failure mode?
- How was it detected?
- What needs to be fixed before redeployment?

---
*Generated by rollback script v${SCRIPT_VERSION}*
EOF

    log_success "Rollback report: ${report_file}"
    cat "${report_file}"
}

# Main rollback flow
main() {
    log_critical "=========================================="
    log_critical "EMERGENCY ROLLBACK INITIATED"
    log_critical "=========================================="
    log_info "Script Version: ${SCRIPT_VERSION}"
    log_info "Start Time: $(date '+%Y-%m-%d %H:%M:%S')"
    log_info ""

    # Create log directory
    mkdir -p "$(dirname "${LOG_FILE}")"

    # Parse arguments
    parse_args "$@"

    # Rollback phases
    detect_environment
    confirm_rollback
    get_current_version
    determine_rollback_target

    log_info ""
    log_critical "EXECUTING ROLLBACK TO ${TARGET_VERSION}"
    log_info "Target: Complete in <10 minutes"
    log_info ""

    stop_current_services
    restore_previous_version
    rollback_database
    start_services
    validate_rollback

    local total_time=$(($(date +%s) - ROLLBACK_START_TIME))

    log_info ""
    log_success "=========================================="
    log_success "ROLLBACK COMPLETED SUCCESSFULLY"
    log_success "=========================================="
    log_success "Total time: ${total_time} seconds"

    if [ ${total_time} -lt 600 ]; then
        log_success "✓ Completed within 10-minute target"
    else
        log_warning "⚠ Exceeded 10-minute target (${total_time}s > 600s)"
    fi

    log_info ""

    # Generate report
    if [ "${DRY_RUN}" = false ]; then
        generate_rollback_report
    fi

    log_info "Rollback to ${TARGET_VERSION} complete"
    log_info "Monitor the application closely for the next hour"
    log_warning "Investigate root cause before attempting redeployment"
}

# Execute main function
main "$@"
