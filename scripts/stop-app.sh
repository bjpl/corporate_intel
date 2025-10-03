#!/bin/bash
# Corporate Intelligence Application Shutdown
# Gracefully stop all services

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

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
}

# Banner
echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════╗"
echo "║   Corporate Intelligence Application Shutdown        ║"
echo "╚══════════════════════════════════════════════════════╝"
echo -e "${NC}"

# 1. Stop FastAPI application
log_info "Stopping FastAPI application..."

# Find and kill uvicorn processes
UVICORN_PIDS=$(pgrep -f "uvicorn app.main:app" || true)

if [ -n "$UVICORN_PIDS" ]; then
    for PID in $UVICORN_PIDS; do
        log_info "Stopping process $PID..."
        kill -TERM "$PID" 2>/dev/null || kill -KILL "$PID" 2>/dev/null
    done

    # Wait for graceful shutdown
    sleep 2

    # Check if still running
    REMAINING=$(pgrep -f "uvicorn app.main:app" || true)
    if [ -n "$REMAINING" ]; then
        log_warning "Force killing remaining processes..."
        kill -KILL $REMAINING 2>/dev/null
    fi

    log_success "FastAPI application stopped"
else
    log_info "No running FastAPI application found"
fi

# 2. Stop Docker services if they exist
if [ -f "$PROJECT_ROOT/docker-compose.yml" ]; then
    log_info "Stopping Docker services..."

    cd "$PROJECT_ROOT"

    # Check if docker-compose is running
    if docker-compose ps | grep -q "Up"; then
        docker-compose down
        log_success "Docker services stopped"
    else
        log_info "No running Docker services found"
    fi
fi

# 3. Clean up any remaining processes
log_info "Cleaning up background processes..."

# Check for any Python processes related to the app
APP_PROCESSES=$(pgrep -f "app.main" || true)
if [ -n "$APP_PROCESSES" ]; then
    log_warning "Found remaining app processes. Cleaning up..."
    kill -TERM $APP_PROCESSES 2>/dev/null || kill -KILL $APP_PROCESSES 2>/dev/null
fi

# 4. Display shutdown summary
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   Application Shutdown Complete                      ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Stopped Services:${NC}"

STOPPED_SERVICES=()

if [ -n "$UVICORN_PIDS" ]; then
    STOPPED_SERVICES+=("  ✓ FastAPI Application")
fi

if [ -f "$PROJECT_ROOT/docker-compose.yml" ] && docker-compose ps 2>/dev/null | grep -q "Exit"; then
    STOPPED_SERVICES+=("  ✓ Docker Services (PostgreSQL, Redis)")
fi

if [ ${#STOPPED_SERVICES[@]} -eq 0 ]; then
    echo -e "  ${YELLOW}No services were running${NC}"
else
    for service in "${STOPPED_SERVICES[@]}"; do
        echo -e "$service"
    done
fi

echo ""
echo -e "${BLUE}System Status:${NC}"
echo -e "  Port 8000:     $(lsof -i :8000 >/dev/null 2>&1 && echo '✗ Still in use' || echo '✓ Available')"
echo -e "  Port 5432:     $(lsof -i :5432 >/dev/null 2>&1 && echo '✗ Still in use' || echo '✓ Available')"
echo -e "  Port 6379:     $(lsof -i :6379 >/dev/null 2>&1 && echo '✗ Still in use' || echo '✓ Available')"
echo ""

# 5. Optional cleanup
read -p "Remove temporary files and caches? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log_info "Cleaning up temporary files..."

    # Clean Python cache
    find "$PROJECT_ROOT" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find "$PROJECT_ROOT" -type f -name "*.pyc" -delete 2>/dev/null || true

    # Clean pytest cache
    rm -rf "$PROJECT_ROOT/.pytest_cache" 2>/dev/null || true

    log_success "Temporary files cleaned"
fi

echo ""
log_success "Shutdown complete. You can restart with './scripts/launch-app.sh'"
