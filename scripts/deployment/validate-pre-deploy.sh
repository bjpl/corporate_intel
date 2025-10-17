#!/bin/bash
# Pre-Deployment Validation Script for Corporate Intelligence Platform
# Usage: ./validate-pre-deploy.sh [--environment staging|production] [--strict]
#
# Validates all deployment prerequisites before actual deployment.
# Prevents deployment if critical requirements are not met.

set -euo pipefail
IFS=$'\n\t'

# Script metadata
SCRIPT_VERSION="1.0.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
LOG_FILE="${PROJECT_ROOT}/logs/pre-deploy-validation-$(date +%Y%m%d_%H%M%S).log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
ENVIRONMENT="production"
STRICT_MODE=false
VALIDATION_ERRORS=0
VALIDATION_WARNINGS=0

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
log_warning() {
    log "WARNING" "${YELLOW}⚠ $*${NC}"
    VALIDATION_WARNINGS=$((VALIDATION_WARNINGS + 1))
}
log_error() {
    log "ERROR" "${RED}✗ $*${NC}"
    VALIDATION_ERRORS=$((VALIDATION_ERRORS + 1))
}

# Parse arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            --strict)
                STRICT_MODE=true
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

Validate deployment prerequisites for Corporate Intelligence Platform.

OPTIONS:
    --environment <env>     Environment to validate (staging|production) [default: production]
    --strict               Treat warnings as errors
    -h, --help             Show this help message

EXAMPLES:
    $0                                  # Validate production
    $0 --environment staging            # Validate staging
    $0 --strict                         # Strict validation mode

VALIDATION CHECKS:
    ☐ Environment variables
    ☐ SSL certificates
    ☐ DNS configuration
    ☐ Database connectivity
    ☐ Backup systems
    ☐ Docker services
    ☐ Disk space
    ☐ Port availability

EOF
}

# Validate environment variables
validate_environment_variables() {
    log_info "Validating environment variables..."

    local env_file="${PROJECT_ROOT}/config/.env.${ENVIRONMENT}"

    if [ ! -f "${env_file}" ]; then
        log_error "Environment file not found: ${env_file}"
        return 1
    fi

    log_success "Environment file exists: ${env_file}"

    # Critical environment variables
    local critical_vars=(
        "POSTGRES_USER"
        "POSTGRES_PASSWORD"
        "POSTGRES_DB"
        "POSTGRES_HOST"
        "SECRET_KEY"
        "ENVIRONMENT"
    )

    # Source the environment file
    set -a
    source "${env_file}"
    set +a

    local missing_vars=0
    for var in "${critical_vars[@]}"; do
        if [ -z "${!var:-}" ]; then
            log_error "Missing critical variable: ${var}"
            missing_vars=$((missing_vars + 1))
        else
            log_success "✓ ${var} is set"
        fi
    done

    # Optional but recommended variables
    local optional_vars=(
        "ALPHA_VANTAGE_API_KEY"
        "NEWSAPI_KEY"
        "SEC_USER_AGENT"
        "REDIS_PASSWORD"
    )

    for var in "${optional_vars[@]}"; do
        if [ -z "${!var:-}" ]; then
            log_warning "Optional variable not set: ${var}"
        else
            log_success "✓ ${var} is set"
        fi
    done

    # Validate SECRET_KEY length (should be long and random)
    if [ -n "${SECRET_KEY:-}" ] && [ ${#SECRET_KEY} -lt 32 ]; then
        log_warning "SECRET_KEY is too short (${#SECRET_KEY} chars, recommended: 64+)"
    fi

    # Validate ENVIRONMENT matches
    if [ -n "${ENVIRONMENT_VAR:-}" ] && [ "${ENVIRONMENT_VAR}" != "${ENVIRONMENT}" ]; then
        log_error "ENVIRONMENT variable mismatch: ${ENVIRONMENT_VAR} != ${ENVIRONMENT}"
    fi

    if [ ${missing_vars} -gt 0 ]; then
        log_error "Missing ${missing_vars} critical environment variables"
        return 1
    fi

    log_success "Environment variables validation passed"
}

# Validate SSL certificates
validate_ssl_certificates() {
    log_info "Validating SSL certificates..."

    if [ "${ENVIRONMENT}" != "production" ]; then
        log_info "Skipping SSL validation for ${ENVIRONMENT}"
        return 0
    fi

    local ssl_dir="${PROJECT_ROOT}/ssl"

    if [ ! -d "${ssl_dir}" ]; then
        log_error "SSL directory not found: ${ssl_dir}"
        return 1
    fi

    # Check for certificate files
    local cert_files=(
        "${ssl_dir}/live/*/fullchain.pem"
        "${ssl_dir}/live/*/privkey.pem"
    )

    local found_certs=false
    for pattern in "${cert_files[@]}"; do
        if compgen -G "${pattern}" > /dev/null; then
            found_certs=true
            log_success "Found SSL certificate: ${pattern}"
        fi
    done

    if [ "${found_certs}" = false ]; then
        log_error "No SSL certificates found in ${ssl_dir}"
        log_error "Run: scripts/deployment/setup-ssl-letsencrypt.sh"
        return 1
    fi

    # Validate certificate expiration
    for cert in ${ssl_dir}/live/*/fullchain.pem; do
        if [ -f "${cert}" ]; then
            local expiry=$(openssl x509 -enddate -noout -in "${cert}" 2>/dev/null | cut -d= -f2)
            local expiry_epoch=$(date -d "${expiry}" +%s 2>/dev/null || echo "0")
            local now_epoch=$(date +%s)
            local days_until_expiry=$(( (expiry_epoch - now_epoch) / 86400 ))

            if [ ${days_until_expiry} -lt 0 ]; then
                log_error "SSL certificate expired: ${cert}"
            elif [ ${days_until_expiry} -lt 30 ]; then
                log_warning "SSL certificate expires in ${days_until_expiry} days: ${cert}"
            else
                log_success "SSL certificate valid for ${days_until_expiry} days"
            fi
        fi
    done

    log_success "SSL certificates validation passed"
}

# Validate DNS configuration
validate_dns_configuration() {
    log_info "Validating DNS configuration..."

    if [ "${ENVIRONMENT}" != "production" ]; then
        log_info "Skipping DNS validation for ${ENVIRONMENT}"
        return 0
    fi

    # Load domain from environment
    local env_file="${PROJECT_ROOT}/config/.env.${ENVIRONMENT}"
    if [ -f "${env_file}" ]; then
        source "${env_file}"
    fi

    local domain="${DOMAIN:-corporate-intel.example.com}"

    log_info "Checking DNS for domain: ${domain}"

    # Check if domain resolves
    if host "${domain}" > /dev/null 2>&1; then
        local ip=$(host "${domain}" | grep "has address" | awk '{print $4}' | head -1)
        log_success "Domain ${domain} resolves to ${ip}"

        # Get current server IP
        local server_ip=$(curl -s ifconfig.me 2>/dev/null || echo "unknown")
        if [ "${ip}" = "${server_ip}" ]; then
            log_success "DNS points to this server"
        else
            log_warning "DNS points to ${ip}, but this server is ${server_ip}"
        fi
    else
        log_error "Domain ${domain} does not resolve"
        log_error "Configure DNS A record to point to this server"
        return 1
    fi

    log_success "DNS configuration validation passed"
}

# Validate database connectivity
validate_database_connectivity() {
    log_info "Validating database connectivity..."

    # Load database config
    local env_file="${PROJECT_ROOT}/config/.env.${ENVIRONMENT}"
    if [ -f "${env_file}" ]; then
        source "${env_file}"
    fi

    local db_host="${POSTGRES_HOST:-localhost}"
    local db_port="${POSTGRES_PORT:-5432}"
    local db_user="${POSTGRES_USER:-}"
    local db_password="${POSTGRES_PASSWORD:-}"
    local db_name="${POSTGRES_DB:-}"

    # Check if postgres is running
    if command -v pg_isready &> /dev/null; then
        if pg_isready -h "${db_host}" -p "${db_port}" > /dev/null 2>&1; then
            log_success "PostgreSQL is accepting connections"
        else
            log_error "Cannot connect to PostgreSQL at ${db_host}:${db_port}"
            return 1
        fi
    else
        log_warning "pg_isready not found, skipping connection test"
    fi

    # Try to connect via Docker if postgres container is running
    if docker ps --format '{{.Names}}' | grep -q "postgres"; then
        log_info "Testing database connection via Docker..."

        if docker exec -it $(docker ps --filter "name=postgres" --format "{{.ID}}") \
            psql -U "${db_user}" -d "${db_name}" -c "SELECT 1;" > /dev/null 2>&1; then
            log_success "Database connection successful"
        else
            log_error "Database connection failed"
            return 1
        fi
    fi

    log_success "Database connectivity validation passed"
}

# Validate backup systems
validate_backup_systems() {
    log_info "Validating backup systems..."

    local backup_dir="${PROJECT_ROOT}/backups"

    if [ ! -d "${backup_dir}" ]; then
        log_warning "Backup directory not found: ${backup_dir}"
        mkdir -p "${backup_dir}"
        log_info "Created backup directory"
    fi

    # Check backup scripts
    local backup_script="${SCRIPT_DIR}/../backup/backup-database.sh"
    if [ -f "${backup_script}" ]; then
        log_success "Backup script exists: ${backup_script}"

        if [ -x "${backup_script}" ]; then
            log_success "Backup script is executable"
        else
            log_warning "Backup script is not executable"
        fi
    else
        log_warning "Backup script not found: ${backup_script}"
    fi

    # Check for recent backups
    if [ -d "${backup_dir}" ]; then
        local recent_backups=$(find "${backup_dir}" -type f -name "*.sql*" -mtime -7 | wc -l)

        if [ ${recent_backups} -gt 0 ]; then
            log_success "Found ${recent_backups} backup(s) from last 7 days"
        else
            log_warning "No recent backups found (last 7 days)"
        fi
    fi

    # Check backup disk space
    local backup_space=$(df -BG "${backup_dir}" 2>/dev/null | awk 'NR==2 {print $4}' | sed 's/G//' || echo "0")
    if [ ${backup_space} -lt 10 ]; then
        log_error "Insufficient backup disk space: ${backup_space}GB (need 10GB+)"
    else
        log_success "Backup disk space: ${backup_space}GB"
    fi

    log_success "Backup systems validation passed"
}

# Validate Docker services
validate_docker_services() {
    log_info "Validating Docker services..."

    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        return 1
    fi

    log_success "Docker is installed: $(docker --version)"

    # Check if Docker daemon is running
    if ! docker info > /dev/null 2>&1; then
        log_error "Docker daemon is not running"
        return 1
    fi

    log_success "Docker daemon is running"

    # Check docker-compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "docker-compose is not installed"
        return 1
    fi

    log_success "docker-compose is installed: $(docker-compose --version)"

    # Check Docker disk usage
    local docker_space=$(df -BG /var/lib/docker 2>/dev/null | awk 'NR==2 {print $4}' | sed 's/G//' || echo "unknown")
    if [ "${docker_space}" != "unknown" ] && [ ${docker_space} -lt 20 ]; then
        log_error "Insufficient Docker disk space: ${docker_space}GB (need 20GB+)"
    else
        log_success "Docker disk space: ${docker_space}GB"
    fi

    log_success "Docker services validation passed"
}

# Validate disk space
validate_disk_space() {
    log_info "Validating disk space..."

    local required_space=20 # GB

    local available_space=$(df -BG "${PROJECT_ROOT}" | awk 'NR==2 {print $4}' | sed 's/G//')

    if [ ${available_space} -lt ${required_space} ]; then
        log_error "Insufficient disk space: ${available_space}GB available, ${required_space}GB required"
        return 1
    fi

    log_success "Disk space: ${available_space}GB available (${required_space}GB required)"

    # Check inode usage
    local inode_usage=$(df -i "${PROJECT_ROOT}" | awk 'NR==2 {print $5}' | sed 's/%//')

    if [ ${inode_usage} -gt 90 ]; then
        log_warning "High inode usage: ${inode_usage}%"
    else
        log_success "Inode usage: ${inode_usage}%"
    fi

    log_success "Disk space validation passed"
}

# Validate port availability
validate_port_availability() {
    log_info "Validating port availability..."

    local required_ports=("80" "443" "5432" "6379" "8000" "9090" "3000")

    for port in "${required_ports[@]}"; do
        if netstat -tuln 2>/dev/null | grep -q ":${port} "; then
            local process=$(lsof -ti:${port} 2>/dev/null || echo "unknown")
            log_warning "Port ${port} is already in use (process: ${process})"
        else
            log_success "Port ${port} is available"
        fi
    done

    log_success "Port availability validation passed"
}

# Validate Git repository
validate_git_repository() {
    log_info "Validating Git repository..."

    cd "${PROJECT_ROOT}"

    # Check if in git repo
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        log_error "Not in a git repository"
        return 1
    fi

    log_success "In git repository"

    # Check for uncommitted changes (production only)
    if [ "${ENVIRONMENT}" = "production" ]; then
        if [ -n "$(git status --porcelain)" ]; then
            log_error "Git repository has uncommitted changes"
            log_error "Commit all changes before production deployment"
            return 1
        fi

        log_success "No uncommitted changes"

        # Check for tagged release
        local current_tag=$(git describe --tags --exact-match 2>/dev/null || echo "")
        if [ -z "${current_tag}" ]; then
            log_warning "Current commit is not tagged (recommended for production)"
        else
            log_success "Current commit is tagged: ${current_tag}"
        fi
    fi

    log_success "Git repository validation passed"
}

# Generate validation report
generate_validation_report() {
    local report_file="${PROJECT_ROOT}/logs/pre-deploy-validation-report-$(date +%Y%m%d_%H%M%S).txt"

    cat > "${report_file}" << EOF
===============================================================================
PRE-DEPLOYMENT VALIDATION REPORT
===============================================================================

Validation Date: $(date '+%Y-%m-%d %H:%M:%S %Z')
Script Version: ${SCRIPT_VERSION}
Environment: ${ENVIRONMENT}
Strict Mode: ${STRICT_MODE}

VALIDATION SUMMARY
------------------
Errors:   ${VALIDATION_ERRORS}
Warnings: ${VALIDATION_WARNINGS}

$([[ ${VALIDATION_ERRORS} -eq 0 ]] && echo "✓ VALIDATION PASSED" || echo "✗ VALIDATION FAILED")

CHECKS PERFORMED
----------------
☐ Environment variables
☐ SSL certificates
☐ DNS configuration
☐ Database connectivity
☐ Backup systems
☐ Docker services
☐ Disk space
☐ Port availability
☐ Git repository

NEXT STEPS
----------
$([[ ${VALIDATION_ERRORS} -eq 0 ]] && cat << PASS
1. Review validation warnings (if any)
2. Proceed with deployment
3. Run: ./deploy-${ENVIRONMENT}.sh
PASS
|| cat << FAIL
1. Fix validation errors listed above
2. Re-run validation: ./validate-pre-deploy.sh
3. Do NOT proceed with deployment until all errors are resolved
FAIL
)

FULL LOG
--------
See ${LOG_FILE}

===============================================================================
EOF

    log_info "Validation report: ${report_file}"
    cat "${report_file}"
}

# Main validation flow
main() {
    log_info "=========================================="
    log_info "Pre-Deployment Validation"
    log_info "Corporate Intelligence Platform"
    log_info "=========================================="
    log_info ""

    mkdir -p "$(dirname "${LOG_FILE}")"

    parse_args "$@"

    log_info "Validating ${ENVIRONMENT} deployment prerequisites..."
    log_info "Strict mode: ${STRICT_MODE}"
    log_info ""

    # Run all validation checks
    validate_environment_variables || true
    validate_ssl_certificates || true
    validate_dns_configuration || true
    validate_database_connectivity || true
    validate_backup_systems || true
    validate_docker_services || true
    validate_disk_space || true
    validate_port_availability || true
    validate_git_repository || true

    log_info ""
    log_info "=========================================="

    # Determine final status
    if [ ${VALIDATION_ERRORS} -eq 0 ]; then
        if [ ${VALIDATION_WARNINGS} -eq 0 ]; then
            log_success "ALL VALIDATIONS PASSED ✓"
        elif [ "${STRICT_MODE}" = true ]; then
            log_error "VALIDATION FAILED (strict mode: ${VALIDATION_WARNINGS} warnings)"
            VALIDATION_ERRORS=1
        else
            log_warning "VALIDATION PASSED WITH ${VALIDATION_WARNINGS} WARNINGS"
        fi
    else
        log_error "VALIDATION FAILED: ${VALIDATION_ERRORS} errors, ${VALIDATION_WARNINGS} warnings"
    fi

    log_info "=========================================="
    log_info ""

    generate_validation_report

    # Exit with appropriate code
    if [ ${VALIDATION_ERRORS} -eq 0 ]; then
        exit 0
    else
        exit 1
    fi
}

main "$@"
