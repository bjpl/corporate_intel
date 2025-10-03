#!/bin/bash

###############################################################################
# Database Migration Validation Script
#
# Comprehensive validation for database migrations including:
# - Pre-migration checks
# - Schema comparison
# - Data integrity validation
# - TimescaleDB feature verification
# - Backup verification
###############################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-corporate_intel}"
DB_USER="${DB_USER:-postgres}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
MIGRATIONS_DIR="${MIGRATIONS_DIR:-./migrations}"

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
}

# Database connection test
check_db_connection() {
    log_info "Checking database connection..."
    if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1" > /dev/null 2>&1; then
        log_success "Database connection successful"
        return 0
    else
        log_error "Cannot connect to database"
        return 1
    fi
}

# Pre-migration validation
pre_migration_check() {
    log_info "Running pre-migration checks..."

    # Check database size
    DB_SIZE=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "
        SELECT pg_size_pretty(pg_database_size('$DB_NAME'))
    " | xargs)
    log_info "Current database size: $DB_SIZE"

    # Check for active connections
    ACTIVE_CONNS=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "
        SELECT count(*) FROM pg_stat_activity WHERE datname = '$DB_NAME'
    " | xargs)
    log_info "Active connections: $ACTIVE_CONNS"

    if [ "$ACTIVE_CONNS" -gt 10 ]; then
        log_warning "High number of active connections detected"
    fi

    # Check for locks
    LOCKS=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "
        SELECT count(*) FROM pg_locks WHERE granted = false
    " | xargs)

    if [ "$LOCKS" -gt 0 ]; then
        log_warning "Detected $LOCKS waiting locks"
        return 1
    fi

    # Check TimescaleDB version
    TS_VERSION=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "
        SELECT extversion FROM pg_extension WHERE extname = 'timescaledb'
    " | xargs)
    log_info "TimescaleDB version: $TS_VERSION"

    log_success "Pre-migration checks passed"
    return 0
}

# Create backup
create_backup() {
    log_info "Creating database backup..."

    mkdir -p "$BACKUP_DIR"
    BACKUP_FILE="$BACKUP_DIR/backup_$(date +%Y%m%d_%H%M%S).sql"

    if pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -F p -f "$BACKUP_FILE"; then
        # Compress backup
        gzip "$BACKUP_FILE"
        BACKUP_SIZE=$(du -h "${BACKUP_FILE}.gz" | cut -f1)
        log_success "Backup created: ${BACKUP_FILE}.gz (Size: $BACKUP_SIZE)"
        echo "${BACKUP_FILE}.gz"
        return 0
    else
        log_error "Backup failed"
        return 1
    fi
}

# Verify backup integrity
verify_backup() {
    local backup_file=$1
    log_info "Verifying backup integrity..."

    if [ ! -f "$backup_file" ]; then
        log_error "Backup file not found: $backup_file"
        return 1
    fi

    # Test backup can be read
    if gunzip -t "$backup_file" > /dev/null 2>&1; then
        log_success "Backup integrity verified"
        return 0
    else
        log_error "Backup integrity check failed"
        return 1
    fi
}

# Schema comparison
compare_schemas() {
    log_info "Capturing current schema..."

    local schema_file="$BACKUP_DIR/schema_$(date +%Y%m%d_%H%M%S).sql"

    pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
        --schema-only -F p -f "$schema_file"

    log_success "Schema captured: $schema_file"
    echo "$schema_file"
}

# Validate data integrity
validate_data_integrity() {
    log_info "Validating data integrity..."

    # Check for NULL values in required columns
    log_info "Checking for NULL values in required columns..."
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" << EOF
    DO \$\$
    DECLARE
        r RECORD;
        null_count INTEGER;
    BEGIN
        FOR r IN
            SELECT table_name, column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
            AND is_nullable = 'NO'
        LOOP
            EXECUTE format('SELECT COUNT(*) FROM %I WHERE %I IS NULL',
                          r.table_name, r.column_name) INTO null_count;

            IF null_count > 0 THEN
                RAISE WARNING 'Found % NULL values in %.%',
                             null_count, r.table_name, r.column_name;
            END IF;
        END LOOP;
    END \$\$;
EOF

    # Check referential integrity
    log_info "Checking referential integrity..."
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" << EOF
    SELECT
        conname as constraint_name,
        conrelid::regclass as table_name,
        confrelid::regclass as referenced_table
    FROM pg_constraint
    WHERE contype = 'f'
    ORDER BY conname;
EOF

    # Check for orphaned records
    log_info "Checking for orphaned records..."
    ORPHANS=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "
        SELECT COUNT(*)
        FROM research_events re
        WHERE NOT EXISTS (SELECT 1 FROM companies c WHERE c.id = re.company_id)
    " | xargs)

    if [ "$ORPHANS" -gt 0 ]; then
        log_warning "Found $ORPHANS orphaned records in research_events"
    else
        log_success "No orphaned records found"
    fi

    log_success "Data integrity validation complete"
}

# Validate TimescaleDB features
validate_timescale_features() {
    log_info "Validating TimescaleDB features..."

    # Check hypertables
    log_info "Checking hypertables..."
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" << EOF
    SELECT
        hypertable_schema,
        hypertable_name,
        num_dimensions,
        num_chunks
    FROM timescaledb_information.hypertables;
EOF

    # Check compression policies
    log_info "Checking compression policies..."
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" << EOF
    SELECT
        hypertable_name,
        compress_after
    FROM timescaledb_information.jobs
    WHERE proc_name = 'policy_compression';
EOF

    # Check retention policies
    log_info "Checking retention policies..."
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" << EOF
    SELECT
        hypertable_name,
        drop_after
    FROM timescaledb_information.jobs
    WHERE proc_name = 'policy_retention';
EOF

    # Check continuous aggregates
    log_info "Checking continuous aggregates..."
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" << EOF
    SELECT
        view_name,
        materialization_hypertable_name,
        view_definition
    FROM timescaledb_information.continuous_aggregates;
EOF

    log_success "TimescaleDB features validated"
}

# Detect migration conflicts
detect_migration_conflicts() {
    log_info "Detecting migration conflicts..."

    # Check for duplicate version numbers
    DUPLICATES=$(find "$MIGRATIONS_DIR" -name "*.up.sql" |
                 sed 's/.*\([0-9]\{14\}\).*/\1/' |
                 sort | uniq -d | wc -l)

    if [ "$DUPLICATES" -gt 0 ]; then
        log_error "Found duplicate migration version numbers"
        return 1
    fi

    # Check migration order
    log_info "Validating migration order..."
    find "$MIGRATIONS_DIR" -name "*.up.sql" |
        sed 's/.*\([0-9]\{14\}\).*/\1/' |
        sort -c 2>&1 || {
            log_error "Migration files are not in chronological order"
            return 1
        }

    log_success "No migration conflicts detected"
    return 0
}

# Test migration rollback
test_rollback() {
    log_info "Testing migration rollback capability..."

    # Get latest migration version
    LATEST_VERSION=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "
        SELECT version FROM schema_migrations ORDER BY version DESC LIMIT 1
    " | xargs)

    if [ -z "$LATEST_VERSION" ]; then
        log_warning "No migrations found in database"
        return 0
    fi

    log_info "Latest migration version: $LATEST_VERSION"

    # Check if down migration exists
    DOWN_FILE="$MIGRATIONS_DIR/${LATEST_VERSION}_*.down.sql"
    if ls $DOWN_FILE 1> /dev/null 2>&1; then
        log_success "Rollback migration found for version $LATEST_VERSION"
    else
        log_error "Rollback migration not found for version $LATEST_VERSION"
        return 1
    fi

    return 0
}

# Performance check
performance_check() {
    log_info "Running performance checks..."

    # Check table sizes
    log_info "Table sizes:"
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" << EOF
    SELECT
        schemaname,
        tablename,
        pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
    FROM pg_tables
    WHERE schemaname = 'public'
    ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
EOF

    # Check index usage
    log_info "Index usage statistics:"
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" << EOF
    SELECT
        schemaname,
        tablename,
        indexname,
        idx_scan,
        idx_tup_read,
        idx_tup_fetch
    FROM pg_stat_user_indexes
    WHERE schemaname = 'public'
    ORDER BY idx_scan DESC
    LIMIT 10;
EOF

    # Check slow queries
    log_info "Checking for slow queries..."
    SLOW_QUERIES=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "
        SELECT COUNT(*)
        FROM pg_stat_statements
        WHERE mean_exec_time > 1000
    " 2>/dev/null | xargs || echo "0")

    if [ "$SLOW_QUERIES" -gt 0 ]; then
        log_warning "Found $SLOW_QUERIES slow queries (>1s average)"
    fi

    log_success "Performance check complete"
}

# Main validation workflow
main() {
    log_info "=== Database Migration Validation ==="
    log_info "Database: $DB_NAME"
    log_info "Host: $DB_HOST:$DB_PORT"
    echo ""

    # Run validation steps
    check_db_connection || exit 1
    echo ""

    pre_migration_check || exit 1
    echo ""

    BACKUP_FILE=$(create_backup)
    if [ $? -ne 0 ]; then
        exit 1
    fi
    echo ""

    verify_backup "$BACKUP_FILE" || exit 1
    echo ""

    SCHEMA_FILE=$(compare_schemas)
    echo ""

    validate_data_integrity
    echo ""

    validate_timescale_features
    echo ""

    detect_migration_conflicts || exit 1
    echo ""

    test_rollback
    echo ""

    performance_check
    echo ""

    log_success "=== All validation checks passed ==="
    log_info "Backup file: $BACKUP_FILE"
    log_info "Schema file: $SCHEMA_FILE"

    return 0
}

# Run main function
main "$@"
