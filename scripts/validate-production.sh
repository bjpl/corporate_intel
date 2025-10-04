#!/bin/bash
# Production Environment Validation Script
# Corporate Intelligence Platform
#
# This script validates that the production environment is properly configured
# and meets all security and infrastructure requirements before deployment.

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
CHECKS_PASSED=0
CHECKS_FAILED=0
CHECKS_WARNING=0

# Results array
declare -a FAILED_CHECKS
declare -a WARNING_CHECKS

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((CHECKS_PASSED++))
}

log_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    FAILED_CHECKS+=("$1")
    ((CHECKS_FAILED++))
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
    WARNING_CHECKS+=("$1")
    ((CHECKS_WARNING++))
}

echo "========================================="
echo "Production Environment Validation"
echo "Corporate Intelligence Platform"
echo "========================================="
echo ""

# 1. Check Operating System
log_info "Checking operating system..."
if [[ -f /etc/os-release ]]; then
    source /etc/os-release
    log_success "OS: $PRETTY_NAME"
else
    log_fail "Cannot determine operating system"
fi

# 2. Check Docker Installation
log_info "Checking Docker installation..."
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version | awk '{print $3}' | sed 's/,//')
    log_success "Docker installed: $DOCKER_VERSION"
else
    log_fail "Docker not installed"
fi

# 3. Check Docker Compose
log_info "Checking Docker Compose..."
if command -v docker-compose &> /dev/null; then
    COMPOSE_VERSION=$(docker-compose --version | awk '{print $4}' | sed 's/,//')
    log_success "Docker Compose installed: $COMPOSE_VERSION"
else
    log_fail "Docker Compose not installed"
fi

# 4. Check System Resources
log_info "Checking system resources..."

# RAM
TOTAL_RAM=$(free -g | awk '/^Mem:/{print $2}')
if [[ $TOTAL_RAM -ge 8 ]]; then
    log_success "RAM: ${TOTAL_RAM}GB (minimum 8GB)"
else
    log_fail "RAM: ${TOTAL_RAM}GB (minimum 8GB required)"
fi

# CPU Cores
CPU_CORES=$(nproc)
if [[ $CPU_CORES -ge 4 ]]; then
    log_success "CPU Cores: $CPU_CORES (minimum 4)"
else
    log_fail "CPU Cores: $CPU_CORES (minimum 4 required)"
fi

# Disk Space
DISK_AVAIL=$(df -BG / | awk 'NR==2 {print $4}' | sed 's/G//')
if [[ $DISK_AVAIL -ge 100 ]]; then
    log_success "Disk Space: ${DISK_AVAIL}GB available (minimum 100GB)"
else
    log_fail "Disk Space: ${DISK_AVAIL}GB available (minimum 100GB required)"
fi

# 5. Check Required Ports
log_info "Checking port availability..."
check_port() {
    local port=$1
    local service=$2
    if ! ss -tuln | grep -q ":$port "; then
        log_success "Port $port available for $service"
    else
        log_warn "Port $port already in use (required for $service)"
    fi
}

check_port 80 "HTTP"
check_port 443 "HTTPS"
check_port 5432 "PostgreSQL"
check_port 6379 "Redis"
check_port 9000 "MinIO"

# 6. Check Environment Files
log_info "Checking environment configuration..."
if [[ -f .env.production ]]; then
    log_success ".env.production file exists"

    # Check for placeholder values
    if grep -q "CHANGE_ME" .env.production; then
        log_fail ".env.production contains CHANGE_ME placeholders"
    else
        log_success ".env.production has been customized"
    fi

    # Check for required variables
    required_vars=("POSTGRES_PASSWORD" "REDIS_PASSWORD" "SECRET_KEY" "MINIO_ROOT_PASSWORD")
    for var in "${required_vars[@]}"; do
        if grep -q "^${var}=" .env.production; then
            log_success "Required variable $var is set"
        else
            log_fail "Required variable $var is missing"
        fi
    done
else
    log_fail ".env.production file not found"
fi

# 7. Check SSL/TLS Certificates
log_info "Checking SSL/TLS configuration..."
SSL_CERT_PATH="/etc/letsencrypt/live"
if [[ -d "$SSL_CERT_PATH" ]]; then
    log_success "SSL certificate directory exists"
else
    log_warn "SSL certificates not found. Configure Let's Encrypt or provide certificates."
fi

# 8. Check Firewall
log_info "Checking firewall configuration..."
if command -v ufw &> /dev/null; then
    if sudo ufw status | grep -q "Status: active"; then
        log_success "UFW firewall is active"
    else
        log_warn "UFW firewall is not active"
    fi
else
    log_warn "UFW firewall not installed"
fi

# 9. Check Security Tools
log_info "Checking security tools..."

if command -v fail2ban-client &> /dev/null; then
    log_success "fail2ban installed"
else
    log_warn "fail2ban not installed (recommended for SSH protection)"
fi

if command -v auditd &> /dev/null; then
    log_success "auditd installed"
else
    log_warn "auditd not installed (recommended for security auditing)"
fi

# 10. Check Docker Images
log_info "Checking Docker images..."
required_images=("postgres:16-alpine" "redis:7-alpine" "minio/minio:latest")
for image in "${required_images[@]}"; do
    if docker images | grep -q "${image%%:*}"; then
        log_success "Docker image available: $image"
    else
        log_warn "Docker image not found: $image (will be pulled on first run)"
    fi
done

# 11. Check Backup Configuration
log_info "Checking backup configuration..."
BACKUP_DIR="/var/backups/corporate-intel"
if [[ -d "$BACKUP_DIR" ]]; then
    log_success "Backup directory exists: $BACKUP_DIR"
else
    log_warn "Backup directory not found: $BACKUP_DIR"
fi

if [[ -f "scripts/backup.sh" ]]; then
    log_success "Backup script exists"
    if [[ -x "scripts/backup.sh" ]]; then
        log_success "Backup script is executable"
    else
        log_fail "Backup script is not executable"
    fi
else
    log_fail "Backup script not found"
fi

# 12. Check Secrets Manager
log_info "Checking secrets management..."
if [[ -n "${VAULT_ADDR:-}" ]]; then
    log_success "Vault address configured: $VAULT_ADDR"
    if command -v vault &> /dev/null; then
        log_success "Vault CLI installed"
    else
        log_warn "Vault CLI not installed"
    fi
else
    log_warn "Vault not configured (secrets in .env files)"
fi

# 13. Check Python Environment
log_info "Checking Python environment..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

    if [[ $PYTHON_MAJOR -eq 3 ]] && [[ $PYTHON_MINOR -ge 10 ]]; then
        log_success "Python $PYTHON_VERSION (minimum 3.10)"
    else
        log_fail "Python $PYTHON_VERSION (minimum 3.10 required)"
    fi
else
    log_fail "Python 3 not installed"
fi

# 14. Check Network Connectivity
log_info "Checking network connectivity..."
if ping -c 1 8.8.8.8 &> /dev/null; then
    log_success "Internet connectivity available"
else
    log_warn "No internet connectivity (may affect external API calls)"
fi

# 15. Check DNS Resolution
log_info "Checking DNS resolution..."
if host github.com &> /dev/null; then
    log_success "DNS resolution working"
else
    log_fail "DNS resolution not working"
fi

# Summary
echo ""
echo "========================================="
echo "Validation Summary"
echo "========================================="
echo -e "${GREEN}Passed: $CHECKS_PASSED${NC}"
echo -e "${YELLOW}Warnings: $CHECKS_WARNING${NC}"
echo -e "${RED}Failed: $CHECKS_FAILED${NC}"
echo ""

if [[ $CHECKS_FAILED -gt 0 ]]; then
    echo -e "${RED}Failed Checks:${NC}"
    for check in "${FAILED_CHECKS[@]}"; do
        echo "  - $check"
    done
    echo ""
fi

if [[ $CHECKS_WARNING -gt 0 ]]; then
    echo -e "${YELLOW}Warnings:${NC}"
    for check in "${WARNING_CHECKS[@]}"; do
        echo "  - $check"
    done
    echo ""
fi

# Exit code
if [[ $CHECKS_FAILED -gt 0 ]]; then
    echo -e "${RED}❌ Production environment validation FAILED${NC}"
    echo "Please resolve all failed checks before deploying to production."
    exit 1
elif [[ $CHECKS_WARNING -gt 0 ]]; then
    echo -e "${YELLOW}⚠️  Production environment validation passed with warnings${NC}"
    echo "Review warnings and address if necessary."
    exit 0
else
    echo -e "${GREEN}✅ Production environment validation PASSED${NC}"
    echo "Environment is ready for deployment."
    exit 0
fi
