#!/bin/bash
#
# Migration Validation Script for Corporate Intelligence Platform
# Checks migration status and validates database schema
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# Check if database URL is set
if [ -z "$DATABASE_URL" ] && [ -z "$POSTGRES_URL" ]; then
    print_error "DATABASE_URL or POSTGRES_URL environment variable not set"
    exit 1
fi

# Banner
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Corporate Intelligence Platform - Migration Check  ${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo ""

# 1. Check database connection
print_info "Step 1/6: Checking database connection..."
python -c "
from sqlalchemy import create_engine
import os
db_url = os.getenv('DATABASE_URL', os.getenv('POSTGRES_URL'))
try:
    engine = create_engine(db_url)
    with engine.connect() as conn:
        result = conn.execute('SELECT version()').fetchone()
        print(f'  PostgreSQL Version: {result[0].split(',')[0]}')
except Exception as e:
    print(f'  ❌ Connection failed: {e}')
    exit(1)
" || exit 1
print_success "Database connection healthy"
echo ""

# 2. Check required extensions
print_info "Step 2/6: Checking PostgreSQL extensions..."
python << EOF
from sqlalchemy import create_engine, text
import os

db_url = os.getenv('DATABASE_URL', os.getenv('POSTGRES_URL'))
engine = create_engine(db_url)

extensions = ['timescaledb', 'vector', 'uuid-ossp']
with engine.connect() as conn:
    result = conn.execute(text("SELECT extname FROM pg_extension"))
    installed = [row[0] for row in result]

    print("  Installed extensions:")
    for ext in extensions:
        if ext in installed:
            print(f"    ✅ {ext}")
        else:
            print(f"    ❌ {ext} (MISSING)")

    # Check if critical extensions are present
    if 'timescaledb' not in installed or 'vector' not in installed:
        print("\n  ⚠️  Critical extensions missing. Run migrations to install them.")
EOF
echo ""

# 3. Check current migration status
print_info "Step 3/6: Checking migration status..."
current=$(alembic current 2>&1)
if [[ $current == *"head"* ]]; then
    print_success "Database is at latest migration"
elif [[ $current == *"(head)"* ]]; then
    print_success "Database is at latest migration"
else
    print_warning "Database may need migration"
    echo "  Current: $current"
fi
echo ""

# 4. List all migrations
print_info "Step 4/6: Available migrations..."
alembic history --verbose | head -20
echo ""

# 5. Check for pending migrations
print_info "Step 5/6: Checking for pending migrations..."
python << EOF
from alembic import command, config as alembic_config
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine
import os

db_url = os.getenv('DATABASE_URL', os.getenv('POSTGRES_URL'))
cfg = alembic_config.Config("alembic.ini")
cfg.set_main_option("sqlalchemy.url", db_url)

script = ScriptDirectory.from_config(cfg)
engine = create_engine(db_url)

with engine.connect() as connection:
    context = MigrationContext.configure(connection)
    current = context.get_current_revision()
    heads = script.get_heads()

    if current in heads:
        print("  ✅ No pending migrations")
    else:
        print(f"  ⚠️  Pending migrations detected")
        print(f"  Current: {current}")
        print(f"  Latest: {', '.join(heads)}")
EOF
echo ""

# 6. Validate table structure
print_info "Step 6/6: Validating core tables..."
python << EOF
from sqlalchemy import create_engine, text
import os

db_url = os.getenv('DATABASE_URL', os.getenv('POSTGRES_URL'))
engine = create_engine(db_url)

core_tables = [
    'companies',
    'sec_filings',
    'financial_metrics',
    'documents',
    'document_chunks',
    'analysis_reports',
    'market_intelligence',
    'users',
    'permissions',
    'api_keys'
]

with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
    """))
    existing_tables = [row[0] for row in result]

    print("  Core tables status:")
    for table in core_tables:
        if table in existing_tables:
            print(f"    ✅ {table}")
        else:
            print(f"    ❌ {table} (MISSING)")

    # Check TimescaleDB hypertables
    try:
        result = conn.execute(text("""
            SELECT hypertable_name
            FROM timescaledb_information.hypertables
        """))
        hypertables = [row[0] for row in result]

        print("\n  TimescaleDB hypertables:")
        if 'financial_metrics' in hypertables:
            print("    ✅ financial_metrics")
        else:
            print("    ⚠️  financial_metrics (not configured)")
    except:
        print("\n  ⚠️  TimescaleDB not configured")
EOF
echo ""

# Summary
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
print_success "Migration check complete!"
echo ""
print_info "Next steps:"
echo "  • To apply migrations: ./scripts/run-migrations.sh upgrade"
echo "  • To check status: ./scripts/run-migrations.sh status"
echo "  • To create migration: ./scripts/run-migrations.sh create '<message>'"
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
