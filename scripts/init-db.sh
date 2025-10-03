#!/bin/bash
# Database initialization script for Corporate Intelligence Platform

set -e  # Exit on error

echo "=========================================="
echo "Corporate Intelligence Database Setup"
echo "=========================================="

# Load environment variables
if [ -f .env ]; then
    echo "✓ Loading environment from .env file"
    export $(grep -v '^#' .env | xargs)
else
    echo "⚠ No .env file found - using defaults"
fi

# Database connection parameters
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_USER="${POSTGRES_USER:-intel_user}"
DB_NAME="${POSTGRES_DB:-corporate_intel}"
DB_PASSWORD="${POSTGRES_PASSWORD}"

# Check if password is set
if [ -z "$DB_PASSWORD" ]; then
    echo "✗ Error: POSTGRES_PASSWORD not set in environment"
    echo "  Please set it in .env file or export it"
    exit 1
fi

echo ""
echo "Connection Details:"
echo "  Host: $DB_HOST"
echo "  Port: $DB_PORT"
echo "  Database: $DB_NAME"
echo "  User: $DB_USER"
echo ""

# Function to run SQL command
run_sql() {
    PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "$1"
}

# Function to check if database exists
check_database() {
    PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U postgres -lqt | cut -d \| -f 1 | grep -qw "$DB_NAME"
}

# Step 1: Check database connectivity
echo "Step 1: Checking database connectivity..."
if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U postgres -c "SELECT 1" > /dev/null 2>&1; then
    echo "✓ Database server is accessible"
else
    echo "✗ Cannot connect to database server"
    echo "  Make sure PostgreSQL is running and credentials are correct"
    exit 1
fi

# Step 2: Create database if it doesn't exist
echo ""
echo "Step 2: Creating database (if needed)..."
if check_database; then
    echo "✓ Database '$DB_NAME' already exists"
else
    echo "Creating database '$DB_NAME'..."
    PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U postgres -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"
    echo "✓ Database created"
fi

# Step 3: Create extensions
echo ""
echo "Step 3: Creating PostgreSQL extensions..."

echo "  Creating TimescaleDB extension..."
if run_sql "CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;" > /dev/null 2>&1; then
    echo "  ✓ TimescaleDB extension created"
else
    echo "  ✗ Failed to create TimescaleDB extension"
    echo "    Make sure TimescaleDB is installed: https://docs.timescale.com/install/"
    exit 1
fi

echo "  Creating pgvector extension..."
if run_sql "CREATE EXTENSION IF NOT EXISTS vector;" > /dev/null 2>&1; then
    echo "  ✓ pgvector extension created"
else
    echo "  ✗ Failed to create pgvector extension"
    echo "    Make sure pgvector is installed: https://github.com/pgvector/pgvector"
    exit 1
fi

echo "  Creating uuid-ossp extension..."
if run_sql "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";" > /dev/null 2>&1; then
    echo "  ✓ uuid-ossp extension created"
else
    echo "  ✗ Failed to create uuid-ossp extension"
    exit 1
fi

# Step 4: Run Alembic migrations
echo ""
echo "Step 4: Running database migrations..."
if command -v alembic > /dev/null 2>&1; then
    echo "Running: alembic upgrade head"
    alembic upgrade head
    echo "✓ Migrations completed"
else
    echo "⚠ Alembic not found - please install: pip install alembic"
    echo "  Then run: alembic upgrade head"
fi

# Step 5: Verify setup
echo ""
echo "Step 5: Verifying database setup..."

# Check extensions
echo "Checking extensions..."
EXTENSIONS=$(run_sql "SELECT extname FROM pg_extension WHERE extname IN ('timescaledb', 'vector', 'uuid-ossp');" 2>/dev/null | grep -E 'timescaledb|vector|uuid-ossp' | wc -l)
if [ "$EXTENSIONS" -eq 3 ]; then
    echo "✓ All required extensions are installed"
else
    echo "⚠ Some extensions may be missing (found $EXTENSIONS/3)"
fi

# Check tables
TABLE_COUNT=$(run_sql "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | grep -E '^[0-9]+$' | head -1)
if [ -n "$TABLE_COUNT" ] && [ "$TABLE_COUNT" -gt 0 ]; then
    echo "✓ Found $TABLE_COUNT tables in database"
else
    echo "⚠ No tables found - migrations may not have run"
fi

# Check hypertables
HYPERTABLE_COUNT=$(run_sql "SELECT COUNT(*) FROM timescaledb_information.hypertables;" 2>/dev/null | grep -E '^[0-9]+$' | head -1)
if [ -n "$HYPERTABLE_COUNT" ] && [ "$HYPERTABLE_COUNT" -gt 0 ]; then
    echo "✓ Found $HYPERTABLE_COUNT TimescaleDB hypertable(s)"
else
    echo "⚠ No hypertables found - migrations may not have run"
fi

# Step 6: Display connection info
echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Database URL (async):"
echo "  postgresql+asyncpg://$DB_USER:****@$DB_HOST:$DB_PORT/$DB_NAME"
echo ""
echo "Next steps:"
echo "  1. Verify connection: python -c 'from src.db.init import init_database; import asyncio; asyncio.run(init_database())'"
echo "  2. Start API server: uvicorn src.api.main:app --reload"
echo "  3. Check health: curl http://localhost:8000/health"
echo ""
echo "=========================================="
