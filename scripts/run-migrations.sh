#!/bin/bash
#
# Migration Runner Script for Corporate Intelligence Platform
# Usage: ./scripts/run-migrations.sh [command] [options]
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Change to project root
cd "$PROJECT_ROOT"

# Function to print colored output
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Function to check database connection
check_database() {
    print_info "Checking database connection..."

    if [ -z "$DATABASE_URL" ] && [ -z "$POSTGRES_URL" ]; then
        print_error "DATABASE_URL or POSTGRES_URL environment variable not set"
        print_info "Set it using: export DATABASE_URL='postgresql://user:pass@host:port/dbname'"
        exit 1
    fi

    # Try to connect to database
    python -c "
from sqlalchemy import create_engine
import os
db_url = os.getenv('DATABASE_URL', os.getenv('POSTGRES_URL'))
try:
    engine = create_engine(db_url)
    conn = engine.connect()
    conn.close()
    print('✅ Database connection successful')
except Exception as e:
    print(f'❌ Database connection failed: {e}')
    exit(1)
" || exit 1
}

# Function to show current migration status
show_status() {
    print_info "Current migration status:"
    alembic current -v
    print_info "\nMigration history:"
    alembic history -v
}

# Function to upgrade to latest
upgrade_latest() {
    print_info "Upgrading database to latest version..."
    check_database
    alembic upgrade head
    print_success "Database upgraded to latest version"
    show_status
}

# Function to upgrade to specific revision
upgrade_to() {
    local revision=$1
    if [ -z "$revision" ]; then
        print_error "Please specify a revision"
        print_info "Usage: $0 upgrade-to <revision>"
        exit 1
    fi

    print_info "Upgrading database to revision $revision..."
    check_database
    alembic upgrade "$revision"
    print_success "Database upgraded to revision $revision"
    show_status
}

# Function to downgrade by steps
downgrade_steps() {
    local steps=${1:-1}
    print_warning "Downgrading database by $steps step(s)..."
    check_database
    alembic downgrade -$steps
    print_success "Database downgraded by $steps step(s)"
    show_status
}

# Function to downgrade to specific revision
downgrade_to() {
    local revision=$1
    if [ -z "$revision" ]; then
        print_error "Please specify a revision"
        print_info "Usage: $0 downgrade-to <revision>"
        exit 1
    fi

    print_warning "Downgrading database to revision $revision..."
    check_database
    alembic downgrade "$revision"
    print_success "Database downgraded to revision $revision"
    show_status
}

# Function to create new migration
create_migration() {
    local message=$1
    if [ -z "$message" ]; then
        print_error "Please provide a migration message"
        print_info "Usage: $0 create '<migration message>'"
        exit 1
    fi

    print_info "Creating new migration: $message"
    alembic revision --autogenerate -m "$message"
    print_success "Migration created successfully"
    print_warning "Please review the generated migration file before applying it!"
}

# Function to create empty migration
create_empty() {
    local message=$1
    if [ -z "$message" ]; then
        print_error "Please provide a migration message"
        print_info "Usage: $0 create-empty '<migration message>'"
        exit 1
    fi

    print_info "Creating empty migration: $message"
    alembic revision -m "$message"
    print_success "Empty migration created successfully"
}

# Function to show help
show_help() {
    cat << EOF
${GREEN}Corporate Intelligence Platform - Database Migration Tool${NC}

${BLUE}Usage:${NC}
    $0 <command> [options]

${BLUE}Commands:${NC}
    ${GREEN}status${NC}              Show current migration status
    ${GREEN}upgrade${NC}             Upgrade to latest version (default)
    ${GREEN}upgrade-to <rev>${NC}    Upgrade to specific revision
    ${GREEN}downgrade [n]${NC}       Downgrade by n steps (default: 1)
    ${GREEN}downgrade-to <rev>${NC}  Downgrade to specific revision
    ${GREEN}create '<msg>'${NC}      Create new auto-generated migration
    ${GREEN}create-empty '<msg>'${NC} Create empty migration template
    ${GREEN}check${NC}               Check database connection
    ${GREEN}help${NC}                Show this help message

${BLUE}Examples:${NC}
    # Upgrade to latest version
    $0 upgrade

    # Check current status
    $0 status

    # Create new migration
    $0 create 'add user preferences table'

    # Downgrade one step
    $0 downgrade

    # Downgrade to specific revision
    $0 downgrade-to 001

${BLUE}Environment Variables:${NC}
    ${YELLOW}DATABASE_URL${NC}        PostgreSQL connection string
                        Format: postgresql://user:pass@host:port/dbname

${BLUE}Migration Files Location:${NC}
    alembic/versions/

${BLUE}Configuration:${NC}
    alembic.ini          Alembic configuration
    alembic/env.py       Environment configuration

EOF
}

# Main script logic
case "${1:-upgrade}" in
    status)
        show_status
        ;;
    upgrade)
        upgrade_latest
        ;;
    upgrade-to)
        upgrade_to "$2"
        ;;
    downgrade)
        downgrade_steps "${2:-1}"
        ;;
    downgrade-to)
        downgrade_to "$2"
        ;;
    create)
        create_migration "$2"
        ;;
    create-empty)
        create_empty "$2"
        ;;
    check)
        check_database
        print_success "Database connection is healthy"
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        print_info "Run '$0 help' for usage information"
        exit 1
        ;;
esac
