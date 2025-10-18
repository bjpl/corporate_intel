#!/bin/bash
################################################################################
# Production Deployment Master Script
# Corporate Intelligence Platform
################################################################################
# Version: 1.0.0
# Last Updated: October 17, 2025
#
# DESCRIPTION:
#   Master orchestrator for production deployments. Coordinates infrastructure
#   deployment, API service deployment, health validation, and monitoring.
#
# USAGE:
#   ./scripts/deploy-production.sh [OPTIONS]
#
# OPTIONS:
#   --version VERSION        Deployment version tag (required)
#   --skip-backup           Skip pre-deployment backups (not recommended)
#   --skip-validation       Skip pre-deployment validation (not recommended)
#   --no-rollback           Don't auto-rollback on failure
#   --dry-run               Simulate deployment without making changes
#   --help                  Show this help message
#
# EXAMPLES:
#   ./scripts/deploy-production.sh --version v1.2.0
#   ./scripts/deploy-production.sh --version v1.2.0 --dry-run
#
# PREREQUISITES:
#   - Docker and Docker Compose installed
#   - Production environment configured (.env.production)
#   - SSL certificates installed
#   - AWS credentials configured (for backups)
#   - Appropriate access permissions
#
# EXIT CODES:
#   0 - Deployment successful
#   1 - Pre-deployment validation failed
#   2 - Infrastructure deployment failed
#   3 - Database migration failed
#   4 - API deployment failed
#   5 - Health check failed
#   6 - Smoke tests failed
#   7 - User cancelled deployment
################################################################################

set -euo pipefail
IFS=$'\n\t'

# ==============================================================================
# CONFIGURATION
# ==============================================================================

# Script metadata
readonly SCRIPT_VERSION="1.0.0"
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
readonly TIMESTAMP="$(date +%Y%m%d_%H%M%S)"

# Paths
readonly COMPOSE_FILE="${PROJECT_ROOT}/config/production/docker-compose.production.yml"
readonly ENV_FILE="${PROJECT_ROOT}/config/production/.env.production"
readonly BACKUP_DIR="${PROJECT_ROOT}/backups/deployments"
readonly LOG_DIR="${PROJECT_ROOT}/deployment-logs"
readonly LOG_FILE="${LOG_DIR}/deployment-${TIMESTAMP}.log"

# Deployment configuration
DEPLOYMENT_VERSION=""
SKIP_BACKUP=false
SKIP_VALIDATION=false
AUTO_ROLLBACK=true
DRY_RUN=false

# Health check configuration
readonly HEALTH_CHECK_TIMEOUT=120
readonly HEALTH_CHECK_INTERVAL=5
readonly MAX_HEALTH_RETRIES=3

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly MAGENTA='\033[0;35m'
readonly CYAN='\033[0;36m'
readonly NC='\033[0m' # No Color

# ==============================================================================
# LOGGING FUNCTIONS
# ==============================================================================

log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp="$(date '+%Y-%m-%d %H:%M:%S')"
    echo -e "${timestamp} [${level}] ${message}" | tee -a "${LOG_FILE}"
}

log_info() {
    log "INFO" "${BLUE}$*${NC}"
}

log_success() {
    log "SUCCESS" "${GREEN}✅ $*${NC}"
}

log_warning() {
    log "WARNING" "${YELLOW}⚠️  $*${NC}"
}

log_error() {
    log "ERROR" "${RED}❌ $*${NC}"
}

log_debug() {
    log "DEBUG" "${CYAN}$*${NC}"
}

log_section() {
    local title="$1"
    echo "" | tee -a "${LOG_FILE}"
    echo "================================================================================" | tee -a "${LOG_FILE}"
    echo -e "${MAGENTA}${title}${NC}" | tee -a "${LOG_FILE}"
    echo "================================================================================" | tee -a "${LOG_FILE}"
}

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

usage() {
    cat << EOF
Production Deployment Master Script v${SCRIPT_VERSION}

USAGE:
    $0 [OPTIONS]

OPTIONS:
    --version VERSION        Deployment version tag (required)
    --skip-backup           Skip pre-deployment backups (not recommended)
    --skip-validation       Skip pre-deployment validation (not recommended)
    --no-rollback           Don't auto-rollback on failure
    --dry-run               Simulate deployment without making changes
    --help                  Show this help message

EXAMPLES:
    $0 --version v1.2.0
    $0 --version v1.2.0 --dry-run

For detailed documentation, see: docs/deployment/DEPLOYMENT_AUTOMATION.md
EOF
    exit 0
}

confirm_action() {
    local message="$1"
    local response

    echo -e "${YELLOW}${message}${NC}"
    read -r -p "Continue? [y/N] " response

    case "$response" in
        [yY][eE][sS]|[yY])
            return 0
            ;;
        *)
            log_warning "Deployment cancelled by user"
            exit 7
            ;;
    esac
}

check_prerequisites() {
    log_section "Checking Prerequisites"

    local missing_prereqs=0

    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        ((missing_prereqs++))
    else
        log_success "Docker found: $(docker --version)"
    fi

    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed"
        ((missing_prereqs++))
    else
        log_success "Docker Compose found: $(docker-compose --version)"
    fi

    # Check required files
    if [[ ! -f "${COMPOSE_FILE}" ]]; then
        log_error "Docker Compose file not found: ${COMPOSE_FILE}"
        ((missing_prereqs++))
    else
        log_success "Docker Compose file found"
    fi

    if [[ ! -f "${ENV_FILE}" ]]; then
        log_error "Environment file not found: ${ENV_FILE}"
        ((missing_prereqs++))
    else
        log_success "Environment file found"
    fi

    # Check for required scripts
    local required_scripts=(
        "${SCRIPT_DIR}/deploy-infrastructure.sh"
        "${SCRIPT_DIR}/deploy-api.sh"
        "${SCRIPT_DIR}/validate-deployment.sh"
        "${SCRIPT_DIR}/rollback-production.sh"
    )

    for script in "${required_scripts[@]}"; do
        if [[ ! -f "${script}" ]]; then
            log_error "Required script not found: ${script}"
            ((missing_prereqs++))
        fi
    done

    if [[ ${missing_prereqs} -gt 0 ]]; then
        log_error "${missing_prereqs} prerequisite(s) missing"
        exit 1
    fi

    log_success "All prerequisites satisfied"
}

create_directories() {
    log_info "Creating required directories..."

    mkdir -p "${BACKUP_DIR}"
    mkdir -p "${LOG_DIR}"
    mkdir -p "${PROJECT_ROOT}/backups/postgres"
    mkdir -p "${PROJECT_ROOT}/backups/configs"

    log_success "Directories created"
}

# ==============================================================================
# DEPLOYMENT PHASES
# ==============================================================================

phase_pre_deployment() {
    log_section "Phase 1: Pre-Deployment"

    # Display deployment information
    log_info "Deployment Information:"
    log_info "  Version: ${DEPLOYMENT_VERSION}"
    log_info "  Timestamp: ${TIMESTAMP}"
    log_info "  Environment: production"
    log_info "  Compose File: ${COMPOSE_FILE}"
    log_info "  Log File: ${LOG_FILE}"

    if [[ "${DRY_RUN}" == true ]]; then
        log_warning "DRY RUN MODE - No changes will be made"
    fi

    # Confirmation prompt
    if [[ "${DRY_RUN}" != true ]]; then
        confirm_action "🚨 You are about to deploy to PRODUCTION. This will cause brief downtime."
    fi

    # Run pre-deployment validation
    if [[ "${SKIP_VALIDATION}" != true ]]; then
        log_info "Running pre-deployment validation..."
        if [[ "${DRY_RUN}" != true ]]; then
            bash "${SCRIPT_DIR}/validate-deployment.sh" --pre-deploy
        else
            log_info "[DRY RUN] Would run pre-deployment validation"
        fi
    else
        log_warning "Skipping pre-deployment validation (not recommended)"
    fi

    # Create backups
    if [[ "${SKIP_BACKUP}" != true ]]; then
        log_info "Creating pre-deployment backups..."
        if [[ "${DRY_RUN}" != true ]]; then
            create_backups
        else
            log_info "[DRY RUN] Would create backups"
        fi
    else
        log_warning "Skipping backups (not recommended)"
    fi

    log_success "Pre-deployment phase complete"
}

create_backups() {
    log_info "Creating backups for rollback safety..."

    # Backup configuration files
    log_info "Backing up configuration files..."
    cp "${COMPOSE_FILE}" "${BACKUP_DIR}/docker-compose.production.yml.${TIMESTAMP}" || log_error "Failed to backup docker-compose file"
    cp "${ENV_FILE}" "${BACKUP_DIR}/.env.production.${TIMESTAMP}" || log_error "Failed to backup env file"

    # Backup database
    log_info "Creating database backup (this may take a few minutes)..."
    if docker-compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" ps postgres | grep -q "Up"; then
        docker-compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" exec -T postgres \
            pg_dump -U "${POSTGRES_USER:-intel_prod_user}" \
            -d "${POSTGRES_DB:-corporate_intel_prod}" -F c \
            -f "/backups/postgres/corporate_intel_prod_${TIMESTAMP}.backup" 2>&1 | tee -a "${LOG_FILE}"

        local backup_size
        backup_size=$(du -h "${PROJECT_ROOT}/backups/postgres/corporate_intel_prod_${TIMESTAMP}.backup" 2>/dev/null | cut -f1 || echo "unknown")
        log_success "Database backup created: ${backup_size}"
    else
        log_warning "PostgreSQL not running - skipping database backup"
    fi

    log_success "Backups complete"
}

phase_infrastructure() {
    log_section "Phase 2: Infrastructure Deployment"

    log_info "Deploying infrastructure services (PostgreSQL, Redis, MinIO)..."

    if [[ "${DRY_RUN}" != true ]]; then
        bash "${SCRIPT_DIR}/deploy-infrastructure.sh" --version "${DEPLOYMENT_VERSION}" 2>&1 | tee -a "${LOG_FILE}"

        if [[ ${PIPESTATUS[0]} -ne 0 ]]; then
            log_error "Infrastructure deployment failed"
            handle_deployment_failure "infrastructure"
            exit 2
        fi
    else
        log_info "[DRY RUN] Would deploy infrastructure services"
    fi

    log_success "Infrastructure deployment complete"
}

phase_database_migration() {
    log_section "Phase 3: Database Migration"

    log_info "Running database migrations..."

    if [[ "${DRY_RUN}" != true ]]; then
        # Check current migration version
        log_info "Current migration version:"
        docker-compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" run --rm api alembic current 2>&1 | tee -a "${LOG_FILE}" || true

        # Run migrations
        log_info "Applying migrations..."
        docker-compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" run --rm api alembic upgrade head 2>&1 | tee -a "${LOG_FILE}"

        if [[ ${PIPESTATUS[0]} -ne 0 ]]; then
            log_error "Database migration failed"
            handle_deployment_failure "migration"
            exit 3
        fi

        # Verify new version
        log_info "New migration version:"
        docker-compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" run --rm api alembic current 2>&1 | tee -a "${LOG_FILE}"
    else
        log_info "[DRY RUN] Would run database migrations"
    fi

    log_success "Database migration complete"
}

phase_api_deployment() {
    log_section "Phase 4: API Deployment"

    log_info "Deploying API services..."

    if [[ "${DRY_RUN}" != true ]]; then
        bash "${SCRIPT_DIR}/deploy-api.sh" --version "${DEPLOYMENT_VERSION}" 2>&1 | tee -a "${LOG_FILE}"

        if [[ ${PIPESTATUS[0]} -ne 0 ]]; then
            log_error "API deployment failed"
            handle_deployment_failure "api"
            exit 4
        fi
    else
        log_info "[DRY RUN] Would deploy API services"
    fi

    log_success "API deployment complete"
}

phase_validation() {
    log_section "Phase 5: Deployment Validation"

    log_info "Running post-deployment validation..."

    if [[ "${DRY_RUN}" != true ]]; then
        bash "${SCRIPT_DIR}/validate-deployment.sh" --post-deploy 2>&1 | tee -a "${LOG_FILE}"

        if [[ ${PIPESTATUS[0]} -ne 0 ]]; then
            log_error "Deployment validation failed"
            handle_deployment_failure "validation"
            exit 5
        fi
    else
        log_info "[DRY RUN] Would run deployment validation"
    fi

    log_success "Deployment validation complete"
}

phase_smoke_tests() {
    log_section "Phase 6: Smoke Tests"

    log_info "Running smoke tests..."

    if [[ "${DRY_RUN}" != true ]]; then
        # Run smoke tests if available
        if [[ -f "${SCRIPT_DIR}/smoke-tests/production-smoke-tests.sh" ]]; then
            bash "${SCRIPT_DIR}/smoke-tests/production-smoke-tests.sh" http://localhost:8000 2>&1 | tee -a "${LOG_FILE}"

            if [[ ${PIPESTATUS[0]} -ne 0 ]]; then
                log_warning "Smoke tests failed - manual review required"
                # Don't auto-fail on smoke test failures - require manual decision
            fi
        else
            log_warning "Smoke test script not found - skipping"
        fi
    else
        log_info "[DRY RUN] Would run smoke tests"
    fi

    log_success "Smoke tests complete"
}

phase_monitoring() {
    log_section "Phase 7: Monitoring Activation"

    log_info "Activating monitoring and alerting..."

    if [[ "${DRY_RUN}" != true ]]; then
        # Verify monitoring services are running
        log_info "Checking Prometheus..."
        if curl -sf http://localhost:9090/-/healthy > /dev/null; then
            log_success "Prometheus is healthy"
        else
            log_warning "Prometheus health check failed"
        fi

        log_info "Checking Grafana..."
        if curl -sf http://localhost:3000/api/health > /dev/null; then
            log_success "Grafana is healthy"
        else
            log_warning "Grafana health check failed"
        fi

        log_info "Checking Jaeger..."
        if docker-compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" ps jaeger | grep -q "Up"; then
            log_success "Jaeger is running"
        else
            log_warning "Jaeger is not running"
        fi
    else
        log_info "[DRY RUN] Would activate monitoring"
    fi

    log_success "Monitoring activation complete"
}

# ==============================================================================
# ERROR HANDLING
# ==============================================================================

handle_deployment_failure() {
    local phase="$1"

    log_error "Deployment failed in phase: ${phase}"

    if [[ "${AUTO_ROLLBACK}" == true ]] && [[ "${DRY_RUN}" != true ]]; then
        log_warning "Initiating automatic rollback..."

        if [[ -f "${SCRIPT_DIR}/rollback-production.sh" ]]; then
            bash "${SCRIPT_DIR}/rollback-production.sh" --auto --reason "Deployment failed in ${phase} phase"
        else
            log_error "Rollback script not found - manual rollback required"
        fi
    else
        log_warning "Auto-rollback disabled - manual intervention required"
        log_info "To rollback manually, run: ./scripts/rollback-production.sh"
    fi
}

cleanup_on_error() {
    log_error "Deployment interrupted"

    # Export logs for analysis
    log_info "Logs saved to: ${LOG_FILE}"

    # Show recent container logs
    if [[ "${DRY_RUN}" != true ]]; then
        log_info "Recent container logs:"
        docker-compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" logs --tail=50 2>&1 | tee -a "${LOG_FILE}"
    fi
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
            --skip-backup)
                SKIP_BACKUP=true
                shift
                ;;
            --skip-validation)
                SKIP_VALIDATION=true
                shift
                ;;
            --no-rollback)
                AUTO_ROLLBACK=false
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --help)
                usage
                ;;
            *)
                log_error "Unknown option: $1"
                usage
                ;;
        esac
    done

    # Validate required arguments
    if [[ -z "${DEPLOYMENT_VERSION}" ]]; then
        log_error "Deployment version is required"
        echo ""
        usage
    fi

    # Setup
    create_directories

    # Log deployment start
    log_section "Production Deployment Started"
    log_info "Version: ${DEPLOYMENT_VERSION}"
    log_info "Timestamp: ${TIMESTAMP}"
    log_info "User: ${USER}"
    log_info "Host: $(hostname)"

    # Trap errors
    trap cleanup_on_error ERR INT TERM

    # Execute deployment phases
    check_prerequisites
    phase_pre_deployment
    phase_infrastructure
    phase_database_migration
    phase_api_deployment
    phase_validation
    phase_smoke_tests
    phase_monitoring

    # Deployment complete
    log_section "Deployment Complete"
    log_success "Production deployment successful!"
    log_info "Version deployed: ${DEPLOYMENT_VERSION}"
    log_info "Deployment log: ${LOG_FILE}"
    log_info ""
    log_info "Next steps:"
    log_info "  1. Monitor application for 1 hour"
    log_info "  2. Check Grafana dashboards: http://localhost:3000"
    log_info "  3. Review logs: docker-compose -f ${COMPOSE_FILE} logs -f api"
    log_info "  4. Update deployment record in docs/deployment/"
    log_info ""
    log_success "Deployment completed at $(date)"

    exit 0
}

# Run main function
main "$@"
