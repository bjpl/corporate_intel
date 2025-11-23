#!/bin/bash
# Corporate Intelligence Platform - Deployment Validation Script
# Validates production environment before and after deployment

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Counters
PASSED=0
FAILED=0
WARNINGS=0

# Check result tracker
declare -a FAILED_CHECKS=()
declare -a WARNING_CHECKS=()

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((PASSED++))
}

log_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((FAILED++))
    FAILED_CHECKS+=("$1")
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
    ((WARNINGS++))
    WARNING_CHECKS+=("$1")
}

# Header
echo "=========================================="
echo "Corporate Intelligence Platform"
echo "Production Deployment Validation"
echo "=========================================="
echo ""

# 1. System Requirements
log_info "Checking system requirements..."

# Docker
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version | cut -d ' ' -f3 | tr -d ',')
    log_success "Docker installed: $DOCKER_VERSION"
else
    log_fail "Docker is not installed"
fi

# Docker Compose
if command -v docker-compose &> /dev/null; then
    COMPOSE_VERSION=$(docker-compose --version | cut -d ' ' -f4 | tr -d ',')
    log_success "Docker Compose installed: $COMPOSE_VERSION"
else
    log_fail "Docker Compose is not installed"
fi

# Disk Space
DISK_AVAIL=$(df -h / | awk 'NR==2 {print $4}' | sed 's/G//')
if (( $(echo "$DISK_AVAIL > 50" | bc -l) )); then
    log_success "Disk space available: ${DISK_AVAIL}G"
else
    log_warn "Low disk space: ${DISK_AVAIL}G (recommend >50G)"
fi

# Memory
TOTAL_MEM=$(free -g | awk 'NR==2 {print $2}')
if (( TOTAL_MEM >= 8 )); then
    log_success "System memory: ${TOTAL_MEM}GB"
else
    log_warn "Low system memory: ${TOTAL_MEM}GB (recommend >=8GB)"
fi

echo ""

# 2. Required Files
log_info "Checking required files..."

REQUIRED_FILES=(
    "docker-compose.yml"
    "Dockerfile"
    ".env.production"
    "config/nginx.conf"
    "scripts/backup.sh"
    "requirements-prod.txt"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        log_success "File exists: $file"
    else
        log_fail "Missing file: $file"
    fi
done

echo ""

# 3. Environment Variables
log_info "Checking environment variables..."

if [ -f ".env.production" ]; then
    source .env.production

    # Critical variables
    CRITICAL_VARS=(
        "POSTGRES_PASSWORD"
        "REDIS_PASSWORD"
        "MINIO_ROOT_PASSWORD"
        "SECRET_KEY"
    )

    for var in "${CRITICAL_VARS[@]}"; do
        if [ -n "${!var:-}" ]; then
            # Check if using default/weak passwords
            if [[ "${!var}" == *"CHANGE_ME"* ]] || [[ "${!var}" == *"password"* ]]; then
                log_warn "$var is set but appears to use default/weak value"
            else
                log_success "$var is configured"
            fi
        else
            log_fail "$var is not set"
        fi
    done
else
    log_fail ".env.production file not found"
fi

echo ""

# 4. Docker Services
log_info "Checking Docker services..."

if docker ps &> /dev/null; then
    SERVICES=(
        "corporate-intel-postgres"
        "corporate-intel-redis"
        "corporate-intel-minio"
        "corporate-intel-api"
    )

    for service in "${SERVICES[@]}"; do
        if docker ps --format '{{.Names}}' | grep -q "$service"; then
            STATUS=$(docker inspect --format='{{.State.Health.Status}}' "$service" 2>/dev/null || echo "no-healthcheck")
            if [ "$STATUS" = "healthy" ] || [ "$STATUS" = "no-healthcheck" ]; then
                log_success "Service running: $service"
            else
                log_warn "Service unhealthy: $service ($STATUS)"
            fi
        else
            log_warn "Service not running: $service"
        fi
    done
else
    log_warn "Docker daemon not accessible or containers not started"
fi

echo ""

# 5. Network Connectivity
log_info "Checking network connectivity..."

# Check if services are listening
PORTS=(
    "5432:PostgreSQL"
    "6379:Redis"
    "9000:MinIO"
    "8000:API"
)

for port_info in "${PORTS[@]}"; do
    PORT="${port_info%%:*}"
    SERVICE="${port_info##*:}"

    if netstat -tuln 2>/dev/null | grep -q ":$PORT " || ss -tuln 2>/dev/null | grep -q ":$PORT "; then
        log_success "$SERVICE listening on port $PORT"
    else
        log_warn "$SERVICE not listening on port $PORT"
    fi
done

echo ""

# 6. API Health Checks
log_info "Checking API health..."

if command -v curl &> /dev/null; then
    # Health endpoint
    if curl -f -s http://localhost:8000/health > /dev/null 2>&1; then
        log_success "API health endpoint responding"
    else
        log_warn "API health endpoint not responding"
    fi

    # API docs
    if curl -f -s http://localhost:8000/docs > /dev/null 2>&1; then
        log_success "API documentation accessible"
    else
        log_warn "API documentation not accessible"
    fi
else
    log_warn "curl not installed, skipping API checks"
fi

echo ""

# 7. Database Connectivity
log_info "Checking database connectivity..."

if docker ps --format '{{.Names}}' | grep -q "corporate-intel-postgres"; then
    if docker exec corporate-intel-postgres pg_isready -U ${POSTGRES_USER:-intel_user} > /dev/null 2>&1; then
        log_success "PostgreSQL accepting connections"

        # Check database exists
        DB_EXISTS=$(docker exec corporate-intel-postgres psql -U ${POSTGRES_USER:-intel_user} -lqt 2>/dev/null | cut -d \| -f 1 | grep -w ${POSTGRES_DB:-corporate_intel} | wc -l)
        if [ "$DB_EXISTS" -gt 0 ]; then
            log_success "Database '${POSTGRES_DB:-corporate_intel}' exists"
        else
            log_fail "Database '${POSTGRES_DB:-corporate_intel}' does not exist"
        fi
    else
        log_fail "PostgreSQL not accepting connections"
    fi
fi

echo ""

# 8. Security Checks
log_info "Checking security configuration..."

# Check file permissions
if [ -f ".env.production" ]; then
    PERMS=$(stat -c "%a" .env.production 2>/dev/null || stat -f "%A" .env.production 2>/dev/null)
    if [ "$PERMS" = "600" ] || [ "$PERMS" = "400" ]; then
        log_success ".env.production has secure permissions ($PERMS)"
    else
        log_warn ".env.production has insecure permissions ($PERMS), should be 600 or 400"
    fi
fi

# Check if running as root
if [ "$(id -u)" = "0" ]; then
    log_warn "Script running as root (consider using non-root user)"
else
    log_success "Script running as non-root user"
fi

# Check firewall
if command -v ufw &> /dev/null; then
    if ufw status | grep -q "Status: active"; then
        log_success "UFW firewall is active"
    else
        log_warn "UFW firewall is not active"
    fi
elif command -v firewall-cmd &> /dev/null; then
    if firewall-cmd --state 2>/dev/null | grep -q "running"; then
        log_success "Firewalld is active"
    else
        log_warn "Firewalld is not active"
    fi
else
    log_warn "No firewall detected (ufw/firewalld)"
fi

echo ""

# 9. SSL/TLS Configuration
log_info "Checking SSL/TLS configuration..."

if [ -d "ssl" ] || [ -d "/etc/letsencrypt" ]; then
    log_success "SSL certificate directory exists"
else
    log_warn "SSL certificate directory not found"
fi

if command -v nginx &> /dev/null; then
    if nginx -t 2>/dev/null; then
        log_success "Nginx configuration is valid"
    else
        log_warn "Nginx configuration has errors"
    fi
else
    log_warn "Nginx not installed"
fi

echo ""

# 10. Backup System
log_info "Checking backup configuration..."

if [ -f "scripts/backup.sh" ]; then
    if [ -x "scripts/backup.sh" ]; then
        log_success "Backup script is executable"
    else
        log_warn "Backup script is not executable (run: chmod +x scripts/backup.sh)"
    fi

    # Check if backup directory is configured
    BACKUP_DIR=$(grep "BACKUP_ROOT=" scripts/backup.sh | cut -d'"' -f2)
    if [ -n "$BACKUP_DIR" ]; then
        log_success "Backup directory configured: $BACKUP_DIR"
        if [ -d "$BACKUP_DIR" ]; then
            log_success "Backup directory exists"
        else
            log_warn "Backup directory does not exist (will be created on first backup)"
        fi
    fi
else
    log_fail "Backup script not found"
fi

# Check for cron job
if crontab -l 2>/dev/null | grep -q "backup.sh"; then
    log_success "Backup cron job configured"
else
    log_warn "Backup cron job not configured"
fi

echo ""

# Summary
echo "=========================================="
echo "VALIDATION SUMMARY"
echo "=========================================="
echo -e "${GREEN}Passed:${NC}   $PASSED"
echo -e "${YELLOW}Warnings:${NC} $WARNINGS"
echo -e "${RED}Failed:${NC}   $FAILED"
echo ""

if [ $FAILED -gt 0 ]; then
    echo -e "${RED}FAILED CHECKS:${NC}"
    for check in "${FAILED_CHECKS[@]}"; do
        echo "  - $check"
    done
    echo ""
fi

if [ $WARNINGS -gt 0 ]; then
    echo -e "${YELLOW}WARNINGS:${NC}"
    for check in "${WARNING_CHECKS[@]}"; do
        echo "  - $check"
    done
    echo ""
fi

# Exit code
if [ $FAILED -gt 0 ]; then
    echo -e "${RED}Validation FAILED. Please fix critical issues before deploying.${NC}"
    exit 1
elif [ $WARNINGS -gt 0 ]; then
    echo -e "${YELLOW}Validation PASSED with warnings. Review warnings before deploying.${NC}"
    exit 0
else
    echo -e "${GREEN}Validation PASSED. System ready for deployment.${NC}"
    exit 0
fi
