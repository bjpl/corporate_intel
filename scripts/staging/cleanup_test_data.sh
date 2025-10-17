#!/bin/bash
# Test Data Cleanup Utility
# Removes test data from staging environment while preserving production data

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Database configuration
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-corporate_intel}"
DB_USER="${DB_USER:-corpintel_user}"

# Test data identifiers
TEST_PREFIX="${TEST_PREFIX:-TEST}"
TEST_TICKER_PATTERN="${TEST_TICKER_PATTERN:-TEST%}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Test Data Cleanup Utility${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Function to confirm cleanup
confirm_cleanup() {
    local env=$1
    echo -e "${YELLOW}⚠️  WARNING: This will delete test data from ${env} environment${NC}"
    echo -e "${YELLOW}Database: ${DB_HOST}:${DB_PORT}/${DB_NAME}${NC}\n"

    read -p "Are you sure you want to continue? (yes/no): " confirm
    if [[ "$confirm" != "yes" ]]; then
        echo -e "${RED}❌ Cleanup cancelled${NC}"
        exit 1
    fi
}

# Function to backup before cleanup
backup_before_cleanup() {
    echo -e "${BLUE}📦 Creating backup before cleanup...${NC}"

    BACKUP_FILE="${PROJECT_ROOT}/backups/pre-cleanup-$(date +%Y%m%d-%H%M%S).sql"
    mkdir -p "${PROJECT_ROOT}/backups"

    PGPASSWORD="${DB_PASSWORD}" pg_dump \
        -h "${DB_HOST}" \
        -p "${DB_PORT}" \
        -U "${DB_USER}" \
        -d "${DB_NAME}" \
        -F p \
        -f "${BACKUP_FILE}"

    if [[ $? -eq 0 ]]; then
        echo -e "${GREEN}✅ Backup created: ${BACKUP_FILE}${NC}"
    else
        echo -e "${RED}❌ Backup failed!${NC}"
        exit 1
    fi
}

# Function to delete test companies
cleanup_test_companies() {
    echo -e "${BLUE}🗑️  Cleaning up test companies...${NC}"

    PGPASSWORD="${DB_PASSWORD}" psql \
        -h "${DB_HOST}" \
        -p "${DB_PORT}" \
        -U "${DB_USER}" \
        -d "${DB_NAME}" \
        <<EOF
    BEGIN;

    -- Count before deletion
    SELECT 'Companies to delete: ' || COUNT(*)
    FROM companies
    WHERE ticker LIKE '${TEST_TICKER_PATTERN}' OR name LIKE '%${TEST_PREFIX}%';

    -- Delete test companies (cascades to related data)
    DELETE FROM companies
    WHERE ticker LIKE '${TEST_TICKER_PATTERN}' OR name LIKE '%${TEST_PREFIX}%';

    -- Verify deletion
    SELECT 'Remaining test companies: ' || COUNT(*)
    FROM companies
    WHERE ticker LIKE '${TEST_TICKER_PATTERN}' OR name LIKE '%${TEST_PREFIX}%';

    COMMIT;
EOF

    echo -e "${GREEN}✅ Test companies cleaned up${NC}"
}

# Function to delete orphaned financial metrics
cleanup_orphaned_metrics() {
    echo -e "${BLUE}🗑️  Cleaning up orphaned metrics...${NC}"

    PGPASSWORD="${DB_PASSWORD}" psql \
        -h "${DB_HOST}" \
        -p "${DB_PORT}" \
        -U "${DB_USER}" \
        -d "${DB_NAME}" \
        <<EOF
    BEGIN;

    -- Delete metrics without corresponding companies
    DELETE FROM financial_metrics
    WHERE company_id NOT IN (SELECT id FROM companies);

    -- Delete old test metrics (older than 7 days)
    DELETE FROM financial_metrics
    WHERE created_at < NOW() - INTERVAL '7 days'
    AND company_id IN (
        SELECT id FROM companies
        WHERE ticker LIKE '${TEST_TICKER_PATTERN}'
    );

    COMMIT;
EOF

    echo -e "${GREEN}✅ Orphaned metrics cleaned up${NC}"
}

# Function to delete test SEC filings
cleanup_test_filings() {
    echo -e "${BLUE}🗑️  Cleaning up test SEC filings...${NC}"

    PGPASSWORD="${DB_PASSWORD}" psql \
        -h "${DB_HOST}" \
        -p "${DB_PORT}" \
        -U "${DB_USER}" \
        -d "${DB_NAME}" \
        <<EOF
    BEGIN;

    -- Delete test filings
    DELETE FROM sec_filings
    WHERE company_id IN (
        SELECT id FROM companies
        WHERE ticker LIKE '${TEST_TICKER_PATTERN}'
    );

    -- Delete orphaned filings
    DELETE FROM sec_filings
    WHERE company_id NOT IN (SELECT id FROM companies);

    COMMIT;
EOF

    echo -e "${GREEN}✅ Test SEC filings cleaned up${NC}"
}

# Function to clean up test cache data
cleanup_test_cache() {
    echo -e "${BLUE}🗑️  Cleaning up test cache data...${NC}"

    # Redis cache cleanup
    if command -v redis-cli &> /dev/null; then
        redis-cli KEYS "test:*" | xargs -r redis-cli DEL
        echo -e "${GREEN}✅ Redis test cache cleaned up${NC}"
    else
        echo -e "${YELLOW}⚠️  redis-cli not found, skipping cache cleanup${NC}"
    fi
}

# Function to vacuum database
vacuum_database() {
    echo -e "${BLUE}🧹 Vacuuming database...${NC}"

    PGPASSWORD="${DB_PASSWORD}" psql \
        -h "${DB_HOST}" \
        -p "${DB_PORT}" \
        -U "${DB_USER}" \
        -d "${DB_NAME}" \
        -c "VACUUM ANALYZE;"

    echo -e "${GREEN}✅ Database vacuumed${NC}"
}

# Function to display cleanup summary
show_cleanup_summary() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}  Cleanup Summary${NC}"
    echo -e "${BLUE}========================================${NC}\n"

    PGPASSWORD="${DB_PASSWORD}" psql \
        -h "${DB_HOST}" \
        -p "${DB_PORT}" \
        -U "${DB_USER}" \
        -d "${DB_NAME}" \
        <<EOF
    SELECT
        'Total Companies' as metric,
        COUNT(*) as count
    FROM companies
    UNION ALL
    SELECT
        'Total Metrics',
        COUNT(*)
    FROM financial_metrics
    UNION ALL
    SELECT
        'Total SEC Filings',
        COUNT(*)
    FROM sec_filings;
EOF
}

# Function to delete generated test files
cleanup_test_files() {
    echo -e "${BLUE}🗑️  Cleaning up test files...${NC}"

    # Remove test result files
    rm -rf "${PROJECT_ROOT}/test-results"
    rm -rf "${PROJECT_ROOT}/test-data"
    rm -rf "${PROJECT_ROOT}/.pytest_cache"
    rm -rf "${PROJECT_ROOT}/htmlcov"
    rm -f "${PROJECT_ROOT}/.coverage"*

    echo -e "${GREEN}✅ Test files cleaned up${NC}"
}

# Main execution
main() {
    local skip_backup=false
    local skip_confirmation=false

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --skip-backup)
                skip_backup=true
                shift
                ;;
            --yes|-y)
                skip_confirmation=true
                shift
                ;;
            --help|-h)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --skip-backup       Skip backup before cleanup"
                echo "  --yes, -y          Skip confirmation prompt"
                echo "  --help, -h         Show this help message"
                exit 0
                ;;
            *)
                echo -e "${RED}Unknown option: $1${NC}"
                exit 1
                ;;
        esac
    done

    # Confirm cleanup
    if [[ "$skip_confirmation" != true ]]; then
        confirm_cleanup "staging"
    fi

    # Backup
    if [[ "$skip_backup" != true ]]; then
        backup_before_cleanup
    fi

    # Run cleanup operations
    cleanup_test_companies
    cleanup_orphaned_metrics
    cleanup_test_filings
    cleanup_test_cache
    cleanup_test_files

    # Optimize database
    vacuum_database

    # Show summary
    show_cleanup_summary

    echo -e "\n${GREEN}✅ Test data cleanup completed successfully!${NC}\n"
}

# Run main function
main "$@"
