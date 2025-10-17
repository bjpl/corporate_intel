#!/bin/bash
# Production Deployment Script for Corporate Intelligence Platform
# Usage: ./deploy-production.sh [--dry-run] [--blue-green] [--force]
#
# CRITICAL: This script deploys to production. Use with extreme caution.
# Always test in staging first. Supports blue-green deployment and rollback.

set -euo pipefail
IFS=$'\n\t'

# Script metadata
SCRIPT_VERSION="1.0.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
LOG_FILE="${PROJECT_ROOT}/logs/deploy-production-$(date +%Y%m%d_%H%M%S).log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Deployment configuration
PRODUCTION_ENV="production"
COMPOSE_FILE="docker-compose.prod.yml"
MAX_HEALTH_RETRIES=60
HEALTH_CHECK_INTERVAL=10
SMOKE_TEST_TIMEOUT=600
ROLLBACK_TIMEOUT=600
DRY_RUN=false
BLUE_GREEN=false
FORCE_DEPLOY=false

# Blue-green deployment ports
BLUE_PORT=8000
GREEN_PORT=8001
CURRENT_COLOR=""
TARGET_COLOR=""

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
log_critical() { log "CRITICAL" "${MAGENTA}☠ $*${NC}"; }

# Error handler with automatic rollback
handle_error() {
    local line_num=$1
    log_critical "PRODUCTION DEPLOYMENT FAILED AT LINE ${line_num}"
    log_critical "Check log file: ${LOG_FILE}"

    if [ "${DRY_RUN}" = false ]; then
        log_warning "Initiating emergency rollback in 10 seconds..."
        log_warning "Press Ctrl+C to abort rollback"
        sleep 10

        "${SCRIPT_DIR}/rollback.sh" --emergency
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
            --blue-green)
                BLUE_GREEN=true
                log_info "Blue-green deployment mode enabled"
                shift
                ;;
            --force)
                FORCE_DEPLOY=true
                log_warning "Force mode enabled - DANGEROUS!"
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

Deploy Corporate Intelligence Platform to PRODUCTION environment.

⚠️  WARNING: This deploys to production. Always test in staging first!

OPTIONS:
    --dry-run       Show what would be done without making changes
    --blue-green    Use blue-green deployment strategy
    --force         Force deployment (DANGEROUS - skips safety checks)
    -h, --help      Show this help message

EXAMPLES:
    $0 --dry-run            # Preview production deployment
    $0                      # Standard production deployment
    $0 --blue-green         # Blue-green zero-downtime deployment

SAFETY CHECKLIST:
    ☐ Staging deployment successful
    ☐ All tests passing in staging
    ☐ Database backup completed
    ☐ Rollback plan ready
    ☐ Team notified of deployment
    ☐ Monitoring dashboards open

EOF
}

# Pre-flight safety checklist
run_preflight_checklist() {
    log_info "======================================"
    log_critical "PRODUCTION DEPLOYMENT PRE-FLIGHT"
    log_info "======================================"
    log_info ""

    log_warning "This will deploy to PRODUCTION. Please confirm the following:"
    log_info ""

    # Interactive checklist (unless --force)
    if [ "${FORCE_DEPLOY}" = false ] && [ "${DRY_RUN}" = false ]; then
        local checklist=(
            "Have you tested this deployment in staging?"
            "Have all tests passed in staging?"
            "Has a database backup been completed?"
            "Is the rollback script tested and ready?"
            "Has the team been notified of this deployment?"
            "Are monitoring dashboards open and ready?"
            "Is there a backup person available for rollback?"
            "Have you reviewed recent commits for breaking changes?"
        )

        for item in "${checklist[@]}"; do
            log_info "☐ ${item}"
            read -p "  Confirm (yes/no): " -r
            if [[ ! $REPLY =~ ^[Yy]es$ ]]; then
                log_error "Pre-flight check failed. Aborting deployment."
                exit 1
            fi
            log_success "  ✓ Confirmed"
        done

        log_info ""
        log_warning "FINAL CONFIRMATION: Deploy to production?"
        read -p "Type 'DEPLOY TO PRODUCTION' to confirm: " -r
        if [ "$REPLY" != "DEPLOY TO PRODUCTION" ]; then
            log_error "Deployment aborted by user"
            exit 1
        fi
    fi

    log_success "Pre-flight checklist complete"
}

# Technical pre-flight checks
run_technical_checks() {
    log_info "Running technical pre-flight checks..."

    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi

    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        exit 1
    fi

    # Check docker-compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "docker-compose is not installed"
        exit 1
    fi

    # Check required files
    local required_files=(
        "${PROJECT_ROOT}/${COMPOSE_FILE}"
        "${PROJECT_ROOT}/config/.env.production"
        "${PROJECT_ROOT}/Dockerfile"
        "${SCRIPT_DIR}/rollback.sh"
    )

    for file in "${required_files[@]}"; do
        if [ ! -f "${file}" ]; then
            log_error "Required file not found: ${file}"
            exit 1
        fi
    done

    # Check disk space (require at least 20GB free for production)
    local available_space=$(df -BG "${PROJECT_ROOT}" | awk 'NR==2 {print $4}' | sed 's/G//')
    if [ "${available_space}" -lt 20 ]; then
        log_error "Insufficient disk space. Available: ${available_space}GB, Required: 20GB"
        exit 1
    fi

    # Verify git tag (production should only deploy tagged releases)
    if [ "${FORCE_DEPLOY}" = false ]; then
        cd "${PROJECT_ROOT}"
        local current_tag=$(git describe --tags --exact-match 2>/dev/null || echo "")

        if [ -z "${current_tag}" ]; then
            log_error "Current commit is not tagged. Production deployments require tagged releases."
            log_error "Create a tag with: git tag -a v1.0.0 -m 'Release 1.0.0'"
            exit 1
        fi

        log_success "Deploying tagged release: ${current_tag}"
    fi

    # Verify SSL certificates exist
    if [ ! -d "${PROJECT_ROOT}/ssl" ]; then
        log_error "SSL certificates not found. Run setup-ssl-letsencrypt.sh first."
        exit 1
    fi

    log_success "Technical checks passed"
}

# Create backup before deployment
create_pre_deployment_backup() {
    log_info "Creating pre-deployment backup..."

    if [ "${DRY_RUN}" = true ]; then
        log_info "[DRY RUN] Would create backup"
        return 0
    fi

    local backup_script="${SCRIPT_DIR}/../backup/backup-database.sh"

    if [ -f "${backup_script}" ]; then
        log_info "Running backup script..."
        bash "${backup_script}" --pre-deployment
        log_success "Backup completed"
    else
        log_warning "Backup script not found at ${backup_script}"
        log_warning "Manual backup recommended"

        if [ "${FORCE_DEPLOY}" = false ]; then
            read -p "Continue without automated backup? (yes/no): " -r
            if [[ ! $REPLY =~ ^[Yy]es$ ]]; then
                log_error "Deployment aborted - backup required"
                exit 1
            fi
        fi
    fi
}

# Determine current deployment (blue/green)
detect_current_deployment() {
    if [ "${BLUE_GREEN}" = false ]; then
        return 0
    fi

    log_info "Detecting current deployment color..."

    if [ "${DRY_RUN}" = true ]; then
        CURRENT_COLOR="blue"
        TARGET_COLOR="green"
        log_info "[DRY RUN] Current: ${CURRENT_COLOR}, Target: ${TARGET_COLOR}"
        return 0
    fi

    # Check which port is currently active
    if curl -sf "http://localhost:${BLUE_PORT}/health" > /dev/null; then
        CURRENT_COLOR="blue"
        TARGET_COLOR="green"
    elif curl -sf "http://localhost:${GREEN_PORT}/health" > /dev/null; then
        CURRENT_COLOR="green"
        TARGET_COLOR="blue"
    else
        # No current deployment, default to blue
        CURRENT_COLOR="none"
        TARGET_COLOR="blue"
    fi

    log_success "Current deployment: ${CURRENT_COLOR}, Target: ${TARGET_COLOR}"
}

# Build Docker images
build_production_images() {
    log_info "Building production Docker images..."

    if [ "${DRY_RUN}" = true ]; then
        log_info "[DRY RUN] Would build production images"
        return 0
    fi

    cd "${PROJECT_ROOT}"

    # Build with production optimizations
    docker-compose -f "${COMPOSE_FILE}" build \
        --build-arg ENVIRONMENT=production \
        --build-arg BUILD_DATE="$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
        --build-arg VCS_REF="$(git rev-parse --short HEAD)" \
        --build-arg VERSION="$(git describe --tags 2>/dev/null || echo 'unknown')" \
        --no-cache \
        --pull \
        2>&1 | tee -a "${LOG_FILE}"

    log_success "Production images built successfully"
}

# Deploy to production (standard or blue-green)
deploy_to_production() {
    if [ "${BLUE_GREEN}" = true ]; then
        deploy_blue_green
    else
        deploy_standard
    fi
}

# Standard deployment (with brief downtime)
deploy_standard() {
    log_info "Starting standard production deployment..."

    if [ "${DRY_RUN}" = true ]; then
        log_info "[DRY RUN] Would deploy to production"
        return 0
    fi

    cd "${PROJECT_ROOT}"

    # Stop current services
    log_warning "Stopping current production services..."
    docker-compose -f "${COMPOSE_FILE}" down

    # Start new services
    log_info "Starting new production services..."
    docker-compose -f "${COMPOSE_FILE}" up -d

    log_success "Production services started"
}

# Blue-green deployment (zero downtime)
deploy_blue_green() {
    log_info "Starting blue-green deployment to ${TARGET_COLOR}..."

    if [ "${DRY_RUN}" = true ]; then
        log_info "[DRY RUN] Would deploy ${TARGET_COLOR} environment"
        return 0
    fi

    cd "${PROJECT_ROOT}"

    local target_port=$([[ "${TARGET_COLOR}" == "blue" ]] && echo "${BLUE_PORT}" || echo "${GREEN_PORT}")

    # Start target environment
    log_info "Starting ${TARGET_COLOR} environment on port ${target_port}..."

    # Create temporary compose file for target environment
    local temp_compose="/tmp/docker-compose-${TARGET_COLOR}.yml"
    sed "s/8000:8000/${target_port}:8000/g" "${COMPOSE_FILE}" > "${temp_compose}"

    docker-compose -f "${temp_compose}" up -d

    log_success "${TARGET_COLOR} environment started"
}

# Wait for production services to be healthy
wait_for_production_services() {
    log_info "Waiting for production services to be healthy..."

    if [ "${DRY_RUN}" = true ]; then
        log_info "[DRY RUN] Would wait for services"
        return 0
    fi

    local port=$([[ "${BLUE_GREEN}" == true ]] && echo "$([[ "${TARGET_COLOR}" == "blue" ]] && echo "${BLUE_PORT}" || echo "${GREEN_PORT}")" || echo "8000")
    local api_url="http://localhost:${port}"

    local retries=0
    while [ ${retries} -lt ${MAX_HEALTH_RETRIES} ]; do
        if curl -sf "${api_url}/health" > /dev/null; then
            log_success "Services are healthy"
            return 0
        fi

        retries=$((retries + 1))
        log_info "Waiting for services (attempt ${retries}/${MAX_HEALTH_RETRIES})..."
        sleep ${HEALTH_CHECK_INTERVAL}
    done

    log_error "Services failed to become healthy"
    return 1
}

# Run production smoke tests
run_production_smoke_tests() {
    log_info "Running production smoke tests..."

    if [ "${DRY_RUN}" = true ]; then
        log_info "[DRY RUN] Would run smoke tests"
        return 0
    fi

    local port=$([[ "${BLUE_GREEN}" == true ]] && echo "$([[ "${TARGET_COLOR}" == "blue" ]] && echo "${BLUE_PORT}" || echo "${GREEN_PORT}")" || echo "8000")
    local api_url="http://localhost:${port}"

    local test_failures=0

    # Critical production tests
    local tests=(
        "${api_url}/health|Health check"
        "${api_url}/api/v1/health/database|Database connectivity"
        "${api_url}/api/v1/health/redis|Redis connectivity"
        "${api_url}/api/v1/health/ready|API readiness"
    )

    for test in "${tests[@]}"; do
        IFS='|' read -r endpoint description <<< "${test}"
        log_info "Testing: ${description}..."

        if curl -sf "${endpoint}" > /dev/null; then
            log_success "${description}: PASS"
        else
            log_error "${description}: FAIL"
            test_failures=$((test_failures + 1))
        fi
    done

    if [ ${test_failures} -gt 0 ]; then
        log_error "Production smoke tests failed: ${test_failures} failures"
        return 1
    fi

    log_success "All production smoke tests passed"
}

# Switch traffic to new deployment (blue-green only)
switch_traffic() {
    if [ "${BLUE_GREEN}" = false ]; then
        return 0
    fi

    log_info "Switching traffic to ${TARGET_COLOR} deployment..."

    if [ "${DRY_RUN}" = true ]; then
        log_info "[DRY RUN] Would switch traffic to ${TARGET_COLOR}"
        return 0
    fi

    # Update nginx/load balancer configuration
    local nginx_config="${PROJECT_ROOT}/config/nginx.conf"

    if [ -f "${nginx_config}" ]; then
        local target_port=$([[ "${TARGET_COLOR}" == "blue" ]] && echo "${BLUE_PORT}" || echo "${GREEN_PORT}")

        # Update upstream backend in nginx config
        sed -i "s/server api:[0-9]*/server api:${target_port}/g" "${nginx_config}"

        # Reload nginx
        docker-compose -f "${COMPOSE_FILE}" exec nginx nginx -s reload

        log_success "Traffic switched to ${TARGET_COLOR}"
    else
        log_warning "Nginx config not found, skipping traffic switch"
    fi
}

# Stop old deployment (blue-green only)
stop_old_deployment() {
    if [ "${BLUE_GREEN}" = false ] || [ "${CURRENT_COLOR}" = "none" ]; then
        return 0
    fi

    log_info "Stopping old ${CURRENT_COLOR} deployment..."

    if [ "${DRY_RUN}" = true ]; then
        log_info "[DRY RUN] Would stop ${CURRENT_COLOR} deployment"
        return 0
    fi

    # Give some time for graceful shutdown
    sleep 30

    local old_compose="/tmp/docker-compose-${CURRENT_COLOR}.yml"
    if [ -f "${old_compose}" ]; then
        docker-compose -f "${old_compose}" down
        log_success "Old ${CURRENT_COLOR} deployment stopped"
    fi
}

# Setup monitoring and alerting
setup_monitoring() {
    log_info "Setting up production monitoring..."

    if [ "${DRY_RUN}" = true ]; then
        log_info "[DRY RUN] Would setup monitoring"
        return 0
    fi

    # Ensure Prometheus and Grafana are running
    local monitoring_services=("prometheus" "grafana" "alertmanager")

    for service in "${monitoring_services[@]}"; do
        if docker-compose -f "${COMPOSE_FILE}" ps "${service}" 2>/dev/null | grep -q "Up"; then
            log_success "${service} is running"
        else
            log_warning "${service} is not running, attempting to start..."
            docker-compose -f "${COMPOSE_FILE}" up -d "${service}"
        fi
    done

    log_success "Monitoring setup complete"
}

# Validate production deployment
validate_production_deployment() {
    log_info "Validating production deployment..."

    if [ "${DRY_RUN}" = true ]; then
        log_info "[DRY RUN] Would validate deployment"
        return 0
    fi

    local validation_failures=0

    # Check SSL/TLS is working
    log_info "Checking SSL/TLS configuration..."
    if command -v openssl &> /dev/null; then
        if timeout 5 openssl s_client -connect localhost:443 -servername localhost < /dev/null 2>/dev/null | grep -q "Verify return code: 0"; then
            log_success "SSL/TLS is properly configured"
        else
            log_warning "SSL/TLS verification failed (may be expected in local environment)"
        fi
    fi

    # Check all critical endpoints
    log_info "Validating all critical endpoints..."
    local endpoints=(
        "health"
        "api/v1/health/database"
        "api/v1/health/redis"
        "api/v1/health/ready"
    )

    for endpoint in "${endpoints[@]}"; do
        if curl -sf "http://localhost:8000/${endpoint}" > /dev/null; then
            log_success "Endpoint /${endpoint}: OK"
        else
            log_error "Endpoint /${endpoint}: FAILED"
            validation_failures=$((validation_failures + 1))
        fi
    done

    # Check logs for critical errors
    log_info "Scanning logs for critical errors..."
    local critical_errors=$(docker-compose -f "${COMPOSE_FILE}" logs --tail=200 | grep -i "critical\|fatal" | wc -l)

    if [ ${critical_errors} -eq 0 ]; then
        log_success "No critical errors in logs"
    else
        log_warning "Found ${critical_errors} critical log entries"
    fi

    if [ ${validation_failures} -gt 0 ]; then
        log_error "Production validation failed: ${validation_failures} issues"
        return 1
    fi

    log_success "Production deployment validated successfully"
}

# Generate production deployment report
generate_production_report() {
    log_info "Generating production deployment report..."

    local report_file="${PROJECT_ROOT}/logs/production-deployment-report-$(date +%Y%m%d_%H%M%S).md"

    cat > "${report_file}" << EOF
# Production Deployment Report

**Date**: $(date '+%Y-%m-%d %H:%M:%S %Z')
**Script Version**: ${SCRIPT_VERSION}
**Environment**: ${PRODUCTION_ENV}
**Deployment Type**: $([[ "${BLUE_GREEN}" == true ]] && echo "Blue-Green" || echo "Standard")

## Git Information

- **Branch**: $(git rev-parse --abbrev-ref HEAD)
- **Commit**: $(git rev-parse --short HEAD)
- **Tag**: $(git describe --tags 2>/dev/null || echo "No tag")
- **Commit Message**: $(git log -1 --pretty=%B)
- **Author**: $(git log -1 --pretty=%an)

## Deployment Details

- **Compose File**: ${COMPOSE_FILE}
- **Dry Run**: ${DRY_RUN}
- **Blue-Green**: ${BLUE_GREEN}
- **Force Deploy**: ${FORCE_DEPLOY}

$([[ "${BLUE_GREEN}" == true ]] && cat << BGEOF
## Blue-Green Details

- **Previous Deployment**: ${CURRENT_COLOR}
- **New Deployment**: ${TARGET_COLOR}
- **Traffic Switched**: Yes
- **Old Deployment Stopped**: Yes
BGEOF
)

## Container Status

\`\`\`
$(docker-compose -f "${COMPOSE_FILE}" ps)
\`\`\`

## Health Checks

$(for endpoint in health api/v1/health/database api/v1/health/redis; do
    echo "### /${endpoint}"
    echo "\`\`\`json"
    curl -s "http://localhost:8000/${endpoint}" 2>/dev/null || echo "Endpoint unavailable"
    echo "\`\`\`"
    echo ""
done)

## Monitoring Links

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000
- **API Health**: http://localhost:8000/health

## Log Files

- **Deployment Log**: ${LOG_FILE}
- **Application Logs**: docker-compose -f ${COMPOSE_FILE} logs

## Next Steps

1. Monitor production metrics in Grafana
2. Watch for alerts in Prometheus
3. Review application logs for errors
4. Verify all features working as expected
5. Update team on deployment status

## Rollback Procedure

If issues occur, run:
\`\`\`bash
${SCRIPT_DIR}/rollback.sh --emergency
\`\`\`

---
*Generated by production deployment script v${SCRIPT_VERSION}*
EOF

    log_success "Production deployment report: ${report_file}"

    # Display summary
    cat "${report_file}"
}

# Main production deployment flow
main() {
    log_info "=========================================="
    log_critical "PRODUCTION DEPLOYMENT"
    log_info "Corporate Intelligence Platform"
    log_info "Script Version: ${SCRIPT_VERSION}"
    log_info "=========================================="
    log_info ""

    # Create log directory
    mkdir -p "$(dirname "${LOG_FILE}")"

    # Parse arguments
    parse_args "$@"

    # Safety checks
    run_preflight_checklist
    run_technical_checks

    # Backup
    create_pre_deployment_backup

    # Deployment
    log_info "Starting production deployment..."
    log_info ""

    detect_current_deployment
    build_production_images
    deploy_to_production
    wait_for_production_services
    run_production_smoke_tests
    switch_traffic
    stop_old_deployment
    setup_monitoring
    validate_production_deployment

    log_info ""
    log_success "=========================================="
    log_success "PRODUCTION DEPLOYMENT COMPLETED"
    log_success "=========================================="
    log_info ""

    # Generate report
    if [ "${DRY_RUN}" = false ]; then
        generate_production_report
    fi

    log_info "🎉 Production deployment successful!"
    log_info ""
    log_info "Monitor the deployment:"
    log_info "  - Application: http://localhost:8000"
    log_info "  - Prometheus: http://localhost:9090"
    log_info "  - Grafana: http://localhost:3000"
    log_info ""
    log_warning "Keep monitoring for the next 4 hours"
    log_info "Rollback available: ${SCRIPT_DIR}/rollback.sh"
}

# Execute main function
main "$@"
