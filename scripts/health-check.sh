#!/bin/bash
# Corporate Intel Health Check Script
# This script verifies all services are running correctly

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
API_HOST="${API_HOST:-localhost}"
API_PORT="${API_PORT:-8000}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-corporate_intel}"
DB_USER="${DB_USER:-postgres}"
REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-6379}"

# Exit codes
EXIT_SUCCESS=0
EXIT_FAILURE=1

# Track overall health
OVERALL_HEALTH=true

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    OVERALL_HEALTH=false
}

# Check API health endpoint
check_api_health() {
    log_info "Checking API health endpoint..."

    API_URL="http://${API_HOST}:${API_PORT}/health"

    if command -v curl >/dev/null 2>&1; then
        response=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL" 2>/dev/null || echo "000")

        if [ "$response" = "200" ]; then
            log_success "API is healthy (HTTP 200)"

            # Get detailed health info
            health_data=$(curl -s "$API_URL" 2>/dev/null || echo "{}")

            if [ "$health_data" != "{}" ]; then
                echo "$health_data" | python3 -m json.tool 2>/dev/null || echo "$health_data"
            fi

            return 0
        else
            log_error "API health check failed (HTTP $response)"
            return 1
        fi
    elif command -v wget >/dev/null 2>&1; then
        if wget -q --spider "$API_URL" 2>/dev/null; then
            log_success "API is healthy"
            return 0
        else
            log_error "API health check failed"
            return 1
        fi
    else
        log_warning "Neither curl nor wget available, skipping API check"
        return 1
    fi
}

# Check API specific endpoints
check_api_endpoints() {
    log_info "Checking API endpoints..."

    BASE_URL="http://${API_HOST}:${API_PORT}"

    # Check OpenAPI docs
    if curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/docs" 2>/dev/null | grep -q "200"; then
        log_success "API documentation available at $BASE_URL/docs"
    else
        log_warning "API documentation endpoint not accessible"
    fi

    # Check version endpoint
    if curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/v1/version" 2>/dev/null | grep -q "200"; then
        version=$(curl -s "$BASE_URL/api/v1/version" 2>/dev/null || echo "{}")
        log_success "Version endpoint accessible"
        echo "  Version: $(echo $version | python3 -c 'import sys, json; print(json.load(sys.stdin).get("version", "unknown"))' 2>/dev/null || echo 'unknown')"
    fi
}

# Check database connection
check_database() {
    log_info "Checking database connection..."

    if command -v pg_isready >/dev/null 2>&1; then
        if pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" >/dev/null 2>&1; then
            log_success "Database is accessible and ready"

            # Get database version
            db_version=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT version();" 2>/dev/null | head -n1 || echo "unknown")
            echo "  PostgreSQL: $(echo $db_version | cut -d',' -f1)"

            # Get connection count
            conn_count=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT count(*) FROM pg_stat_activity WHERE datname='$DB_NAME';" 2>/dev/null || echo "0")
            echo "  Active connections: $(echo $conn_count | tr -d ' ')"

            return 0
        else
            log_error "Database is not accessible"
            return 1
        fi
    else
        log_warning "pg_isready not available, attempting direct connection..."

        if command -v psql >/dev/null 2>&1; then
            if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" >/dev/null 2>&1; then
                log_success "Database connection successful"
                return 0
            else
                log_error "Database connection failed"
                return 1
            fi
        else
            log_warning "psql not available, cannot verify database"
            return 1
        fi
    fi
}

# Check Redis connection
check_redis() {
    log_info "Checking Redis connection..."

    if command -v redis-cli >/dev/null 2>&1; then
        if redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping >/dev/null 2>&1; then
            log_success "Redis is accessible and responding"

            # Get Redis info
            redis_version=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" INFO server 2>/dev/null | grep "redis_version" | cut -d':' -f2 | tr -d '\r' || echo "unknown")
            echo "  Redis version: $redis_version"

            # Get memory usage
            redis_memory=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" INFO memory 2>/dev/null | grep "used_memory_human" | cut -d':' -f2 | tr -d '\r' || echo "unknown")
            echo "  Memory usage: $redis_memory"

            return 0
        else
            log_warning "Redis is not accessible (optional service)"
            return 1
        fi
    else
        log_warning "redis-cli not available, cannot verify Redis"
        return 1
    fi
}

# Check system resources
check_system_resources() {
    log_info "Checking system resources..."

    # Check disk space
    if command -v df >/dev/null 2>&1; then
        disk_usage=$(df -h . | awk 'NR==2 {print $5}' | tr -d '%')
        if [ "$disk_usage" -gt 90 ]; then
            log_warning "Disk usage is high: ${disk_usage}%"
        else
            log_success "Disk usage: ${disk_usage}%"
        fi
    fi

    # Check memory (if available)
    if command -v free >/dev/null 2>&1; then
        mem_usage=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100}')
        if [ "$mem_usage" -gt 90 ]; then
            log_warning "Memory usage is high: ${mem_usage}%"
        else
            log_success "Memory usage: ${mem_usage}%"
        fi
    fi

    # Check CPU load (if available)
    if command -v uptime >/dev/null 2>&1; then
        load_avg=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | tr -d ',')
        log_info "CPU load average: $load_avg"
    fi
}

# Check application logs for errors
check_logs() {
    log_info "Checking recent application logs..."

    LOG_DIR="$(dirname "$0")/../logs"

    if [ -d "$LOG_DIR" ]; then
        # Check for recent errors
        error_count=$(find "$LOG_DIR" -name "*.log" -mtime -1 -exec grep -i "error" {} \; 2>/dev/null | wc -l || echo "0")

        if [ "$error_count" -gt 0 ]; then
            log_warning "Found $error_count error(s) in recent logs"
        else
            log_success "No recent errors in logs"
        fi
    else
        log_info "Log directory not found, skipping log check"
    fi
}

# Generate health report
generate_report() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  Health Check Summary                 ${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""

    if [ "$OVERALL_HEALTH" = true ]; then
        echo -e "${GREEN}Status: HEALTHY${NC}"
        echo ""
        echo "All critical services are operational"
        return $EXIT_SUCCESS
    else
        echo -e "${RED}Status: UNHEALTHY${NC}"
        echo ""
        echo "One or more critical services are not operational"
        echo "Please check the errors above for details"
        return $EXIT_FAILURE
    fi
}

# Main execution
main() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  Corporate Intel Health Check         ${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""

    # Run all health checks
    check_api_health
    check_api_endpoints
    check_database
    check_redis
    check_system_resources
    check_logs

    # Generate and display report
    generate_report
}

# Handle script arguments
case "${1:-all}" in
    all)
        main
        ;;
    api)
        check_api_health
        check_api_endpoints
        ;;
    db)
        check_database
        ;;
    redis)
        check_redis
        ;;
    system)
        check_system_resources
        ;;
    *)
        echo "Usage: $0 {all|api|db|redis|system}"
        echo "  all    - Run all health checks (default)"
        echo "  api    - Check API health only"
        echo "  db     - Check database only"
        echo "  redis  - Check Redis only"
        echo "  system - Check system resources only"
        exit 1
        ;;
esac

exit $?
