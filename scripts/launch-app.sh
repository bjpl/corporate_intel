#!/bin/bash
# Corporate Intelligence Application Launcher
# Complete startup flow with validation and health checks

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Log functions
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
echo "║   Corporate Intelligence Application Launcher        ║"
echo "║   FastAPI + PostgreSQL Intelligence Platform         ║"
echo "╚══════════════════════════════════════════════════════╝"
echo -e "${NC}"

# 1. Check Python version
log_info "Checking Python version..."
if ! command -v python &> /dev/null; then
    log_error "Python is not installed. Please install Python 3.10 or higher."
    exit 1
fi

PYTHON_VERSION=$(python -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_VERSION="3.10"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    log_error "Python $REQUIRED_VERSION or higher is required. Found: $PYTHON_VERSION"
    exit 1
fi

log_success "Python $PYTHON_VERSION detected"

# 2. Verify dependencies
log_info "Checking Python dependencies..."
if [ ! -d "$PROJECT_ROOT/venv" ] && [ ! -d "$PROJECT_ROOT/.venv" ]; then
    log_warning "Virtual environment not found. Creating one..."
    python -m venv "$PROJECT_ROOT/venv"
    source "$PROJECT_ROOT/venv/bin/activate" || source "$PROJECT_ROOT/venv/Scripts/activate"
    pip install --upgrade pip
    pip install -r "$PROJECT_ROOT/requirements.txt"
else
    # Activate existing venv
    if [ -d "$PROJECT_ROOT/venv" ]; then
        source "$PROJECT_ROOT/venv/bin/activate" || source "$PROJECT_ROOT/venv/Scripts/activate"
    else
        source "$PROJECT_ROOT/.venv/bin/activate" || source "$PROJECT_ROOT/.venv/Scripts/activate"
    fi
fi

log_success "Dependencies verified"

# 3. Check .env file
log_info "Checking environment configuration..."
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    log_error ".env file not found. Run './scripts/quick-start.sh' for first-time setup."
    exit 1
fi

# Source .env file
export $(grep -v '^#' "$PROJECT_ROOT/.env" | xargs)

# Verify required environment variables
REQUIRED_VARS=("DATABASE_URL" "SECRET_KEY")
MISSING_VARS=()

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        MISSING_VARS+=("$var")
    fi
done

if [ ${#MISSING_VARS[@]} -ne 0 ]; then
    log_error "Missing required environment variables: ${MISSING_VARS[*]}"
    log_info "Please configure these in your .env file"
    exit 1
fi

log_success "Environment configuration validated"

# 4. Check database connectivity
log_info "Checking database connectivity..."

# Start Docker services if docker-compose.yml exists
if [ -f "$PROJECT_ROOT/docker-compose.yml" ]; then
    log_info "Starting Docker services..."
    docker-compose -f "$PROJECT_ROOT/docker-compose.yml" up -d postgres redis
    sleep 3  # Wait for services to start
    log_success "Docker services started"
fi

# Test database connection
python - <<EOF
import sys
from sqlalchemy import create_engine, text
from app.core.config import settings

try:
    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("✓ Database connection successful")
    sys.exit(0)
except Exception as e:
    print(f"✗ Database connection failed: {e}")
    sys.exit(1)
EOF

if [ $? -ne 0 ]; then
    log_error "Database connection failed. Please check your DATABASE_URL"
    exit 1
fi

log_success "Database connectivity verified"

# 5. Run migrations
log_info "Running database migrations..."
cd "$PROJECT_ROOT"

if [ -f "alembic.ini" ]; then
    alembic upgrade head
    log_success "Database migrations completed"
else
    log_warning "Alembic not configured. Skipping migrations."
fi

# 6. Initialize admin user if needed
log_info "Checking for admin user..."
python - <<EOF
from app.core.database import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash
import os

db = SessionLocal()
try:
    admin_email = os.getenv("ADMIN_EMAIL", "admin@corporate-intel.com")
    admin = db.query(User).filter(User.email == admin_email).first()

    if not admin:
        admin = User(
            email=admin_email,
            username="admin",
            hashed_password=get_password_hash(os.getenv("ADMIN_PASSWORD", "changeme")),
            is_active=True,
            is_superuser=True
        )
        db.add(admin)
        db.commit()
        print(f"✓ Created admin user: {admin_email}")
    else:
        print(f"✓ Admin user exists: {admin_email}")
finally:
    db.close()
EOF

# 7. Start the application
log_info "Starting FastAPI application..."

# Determine host and port
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"

# Start with uvicorn
log_info "Application starting on http://$HOST:$PORT"
echo ""
log_success "╔══════════════════════════════════════════════════════╗"
log_success "║   Application is READY                               ║"
log_success "╚══════════════════════════════════════════════════════╝"
echo ""
echo -e "${GREEN}Access URLs:${NC}"
echo -e "  🌐 Application:    http://localhost:$PORT"
echo -e "  📚 API Docs:       http://localhost:$PORT/docs"
echo -e "  🔄 ReDoc:          http://localhost:$PORT/redoc"
echo -e "  ❤️  Health Check:  http://localhost:$PORT/api/v1/health"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop the application${NC}"
echo ""

# Start the application
cd "$PROJECT_ROOT"
uvicorn app.main:app --host "$HOST" --port "$PORT" --reload

# This will only execute after Ctrl+C
log_info "Shutting down application..."
