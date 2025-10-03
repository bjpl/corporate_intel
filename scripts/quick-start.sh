#!/bin/bash
# Corporate Intelligence Quick Start
# First-time setup script with automatic configuration

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
echo "║   Corporate Intelligence Quick Start                 ║"
echo "║   Automated First-Time Setup                         ║"
echo "╚══════════════════════════════════════════════════════╝"
echo -e "${NC}"

# 1. Check for existing .env
if [ -f "$PROJECT_ROOT/.env" ]; then
    log_warning ".env file already exists"
    read -p "Do you want to overwrite it? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Keeping existing .env file. Proceeding to launch..."
        exec "$SCRIPT_DIR/launch-app.sh"
    fi
fi

# 2. Copy .env.example to .env
log_info "Creating .env file from template..."
if [ ! -f "$PROJECT_ROOT/.env.example" ]; then
    log_error ".env.example not found. Cannot proceed."
    exit 1
fi

cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
log_success ".env file created"

# 3. Generate SECRET_KEY
log_info "Generating secure SECRET_KEY..."
SECRET_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')

# Replace SECRET_KEY in .env
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    sed -i '' "s|SECRET_KEY=.*|SECRET_KEY=$SECRET_KEY|g" "$PROJECT_ROOT/.env"
else
    # Linux/Git Bash
    sed -i "s|SECRET_KEY=.*|SECRET_KEY=$SECRET_KEY|g" "$PROJECT_ROOT/.env"
fi

log_success "SECRET_KEY generated and configured"

# 4. Configure database defaults
log_info "Configuring database settings..."

# Prompt for database type
echo ""
echo "Database Configuration:"
echo "  1) PostgreSQL (Recommended for production)"
echo "  2) SQLite (Quick start for development)"
read -p "Select database type (1/2) [default: 2]: " DB_CHOICE

if [ "$DB_CHOICE" = "1" ]; then
    # PostgreSQL configuration
    read -p "Database host [default: localhost]: " DB_HOST
    DB_HOST=${DB_HOST:-localhost}

    read -p "Database port [default: 5432]: " DB_PORT
    DB_PORT=${DB_PORT:-5432}

    read -p "Database name [default: corporate_intel]: " DB_NAME
    DB_NAME=${DB_NAME:-corporate_intel}

    read -p "Database user [default: postgres]: " DB_USER
    DB_USER=${DB_USER:-postgres}

    read -s -p "Database password: " DB_PASSWORD
    echo

    DATABASE_URL="postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME"
else
    # SQLite configuration
    DATABASE_URL="sqlite:///./corporate_intel.db"
    log_info "Using SQLite database: corporate_intel.db"
fi

# Update DATABASE_URL in .env
if [[ "$OSTYPE" == "darwin"* ]]; then
    sed -i '' "s|DATABASE_URL=.*|DATABASE_URL=$DATABASE_URL|g" "$PROJECT_ROOT/.env"
else
    sed -i "s|DATABASE_URL=.*|DATABASE_URL=$DATABASE_URL|g" "$PROJECT_ROOT/.env"
fi

log_success "Database configured"

# 5. Configure admin credentials
echo ""
log_info "Setting up admin user..."
read -p "Admin email [default: admin@corporate-intel.com]: " ADMIN_EMAIL
ADMIN_EMAIL=${ADMIN_EMAIL:-admin@corporate-intel.com}

read -s -p "Admin password [default: changeme]: " ADMIN_PASSWORD
echo
ADMIN_PASSWORD=${ADMIN_PASSWORD:-changeme}

# Add admin credentials to .env
echo "" >> "$PROJECT_ROOT/.env"
echo "# Admin User Configuration" >> "$PROJECT_ROOT/.env"
echo "ADMIN_EMAIL=$ADMIN_EMAIL" >> "$PROJECT_ROOT/.env"
echo "ADMIN_PASSWORD=$ADMIN_PASSWORD" >> "$PROJECT_ROOT/.env"

log_success "Admin user configured"

# 6. Configure Redis (optional)
echo ""
read -p "Enable Redis for caching? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    read -p "Redis URL [default: redis://localhost:6379]: " REDIS_URL
    REDIS_URL=${REDIS_URL:-redis://localhost:6379}

    echo "" >> "$PROJECT_ROOT/.env"
    echo "# Redis Configuration" >> "$PROJECT_ROOT/.env"
    echo "REDIS_URL=$REDIS_URL" >> "$PROJECT_ROOT/.env"

    log_success "Redis configured"
fi

# 7. Install Python dependencies
log_info "Setting up Python environment..."
cd "$PROJECT_ROOT"

if [ ! -d "venv" ] && [ ! -d ".venv" ]; then
    log_info "Creating virtual environment..."
    python -m venv venv
fi

# Activate venv
if [ -d "venv" ]; then
    source venv/bin/activate || source venv/Scripts/activate
else
    source .venv/bin/activate || source .venv/Scripts/activate
fi

log_info "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

log_success "Dependencies installed"

# 8. Summary
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   Quick Start Setup Complete!                        ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Configuration Summary:${NC}"
echo -e "  Database:      $(echo $DATABASE_URL | cut -d'@' -f2 || echo 'SQLite')"
echo -e "  Admin Email:   $ADMIN_EMAIL"
echo -e "  Secret Key:    ✓ Generated"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo -e "  1. Review your .env file for any additional settings"
echo -e "  2. The application will now start automatically"
echo ""
read -p "Press Enter to launch the application..."

# 9. Launch the application
log_info "Launching application..."
exec "$SCRIPT_DIR/launch-app.sh"
