#!/bin/bash

# Database Load Testing Script
# Tests performance with applied indexes on corporate_intel database

DB_HOST="localhost"
DB_PORT="5434"
DB_USER="intel_user"
DB_PASSWORD="lsZXGgU92KhK5VqR"
DB_NAME="corporate_intel"

PGPASSWORD=$DB_PASSWORD
export PGPASSWORD

echo "======================================================================"
echo "DATABASE LOAD TESTING - WITH APPLIED INDEXES"
echo "======================================================================"
echo ""

# Check database connection
echo "Checking database connection..."
if ! psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "SELECT 1" > /dev/null 2>&1; then
    echo "ERROR: Cannot connect to database"
    echo "Please ensure the database is running on $DB_HOST:$DB_PORT"
    exit 1
fi
echo "✓ Database connection successful"
echo ""

# Function to measure query execution time
time_query() {
    local query=$1
    local name=$2
    echo -n "  Testing $name... "

    START=$(date +%s.%N)
    psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "$query" > /dev/null 2>&1
    END=$(date +%s.%N)

    DIFF=$(echo "$END - $START" | bc)
    MS=$(echo "$DIFF * 1000" | bc)
    echo "${MS} ms"
}

# Function to run EXPLAIN ANALYZE
explain_query() {
    local query=$1
    local name=$2
    echo ""
    echo "EXPLAIN ANALYZE: $name"
    echo "----------------------------------------------------------------------"
    psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "EXPLAIN (ANALYZE, BUFFERS) $query"
}

echo "========================================================================"
echo "Phase 1: Individual Query Benchmarks"
echo "========================================================================"
echo ""

# Ticker Lookups
echo "Benchmark: Ticker Lookups (idx_companies_ticker)"
time_query "SELECT * FROM companies WHERE ticker = 'CHGG'" "CHGG ticker lookup"
time_query "SELECT * FROM companies WHERE ticker = 'AAPL'" "AAPL ticker lookup"
time_query "SELECT * FROM companies WHERE ticker = 'MSFT'" "MSFT ticker lookup"
echo ""

# Category Filters
echo "Benchmark: Category Filters (idx_companies_category)"
time_query "SELECT * FROM companies WHERE category = 'edtech'" "edtech category filter"
time_query "SELECT * FROM companies WHERE category = 'technology'" "technology category filter"
echo ""

# Company Search (trigram)
echo "Benchmark: Company Search (idx_companies_name_trgm)"
time_query "SELECT * FROM companies WHERE name ILIKE '%Chegg%' LIMIT 20" "Chegg name search"
time_query "SELECT * FROM companies WHERE name ILIKE '%Apple%' LIMIT 20" "Apple name search"
echo ""

# Financial Metrics
echo "Benchmark: Financial Metrics (compound index)"
time_query "SELECT c.ticker, c.name, fm.* FROM companies c JOIN financial_metrics fm ON c.company_id = fm.company_id WHERE c.ticker = 'CHGG' ORDER BY fm.report_date DESC LIMIT 10" "CHGG financial metrics"
echo ""

# SEC Filings
echo "Benchmark: SEC Filings (date range index)"
time_query "SELECT c.ticker, s.* FROM companies c JOIN sec_filings s ON c.company_id = s.company_id WHERE s.filing_date >= CURRENT_DATE - INTERVAL '90 days' AND s.form_type = '10-Q' ORDER BY s.filing_date DESC" "SEC filings 10-Q"
echo ""

# Complex Join
echo "Benchmark: Complex Multi-table Join"
time_query "SELECT c.ticker, c.name, COUNT(DISTINCT s.filing_id) as filing_count, COUNT(DISTINCT e.earnings_id) as earnings_count FROM companies c LEFT JOIN sec_filings s ON c.company_id = s.company_id LEFT JOIN earnings_calls e ON c.company_id = e.company_id WHERE c.category = 'edtech' GROUP BY c.ticker, c.name" "Complex join query"
echo ""

echo "========================================================================"
echo "Phase 2: Index Usage Verification (EXPLAIN ANALYZE)"
echo "========================================================================"

explain_query "SELECT * FROM companies WHERE ticker = 'CHGG'" "Ticker Index"
explain_query "SELECT * FROM companies WHERE category = 'edtech'" "Category Index"
explain_query "SELECT * FROM companies WHERE name ILIKE '%Chegg%'" "Trigram Index"
explain_query "SELECT c.*, fm.* FROM companies c JOIN financial_metrics fm ON c.company_id = fm.company_id WHERE c.ticker = 'CHGG'" "Join with Indexes"
explain_query "SELECT * FROM sec_filings WHERE filing_date >= CURRENT_DATE - INTERVAL '90 days' AND form_type = '10-Q'" "SEC Filings Composite"

echo ""
echo "========================================================================"
echo "Phase 3: Database Statistics"
echo "========================================================================"
echo ""

echo "Index Usage Statistics:"
echo "----------------------------------------------------------------------"
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME << 'EOF'
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan as scans,
    idx_tup_read as tuples_read,
    idx_tup_fetch as tuples_fetched
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan DESC
LIMIT 15;
EOF

echo ""
echo "Cache Hit Ratio:"
echo "----------------------------------------------------------------------"
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME << 'EOF'
SELECT
    'Heap Cache Hit Ratio' as metric,
    CASE
        WHEN sum(heap_blks_hit) + sum(heap_blks_read) = 0 THEN 0
        ELSE round(100.0 * sum(heap_blks_hit) /
            nullif(sum(heap_blks_hit) + sum(heap_blks_read), 0), 2)
    END as percentage
FROM pg_statio_user_tables
UNION ALL
SELECT
    'Index Cache Hit Ratio' as metric,
    CASE
        WHEN sum(idx_blks_hit) + sum(idx_blks_read) = 0 THEN 0
        ELSE round(100.0 * sum(idx_blks_hit) /
            nullif(sum(idx_blks_hit) + sum(idx_blks_read), 0), 2)
    END as percentage
FROM pg_statio_user_tables;
EOF

echo ""
echo "Table Sizes and Index Sizes:"
echo "----------------------------------------------------------------------"
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME << 'EOF'
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS table_size,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) -
                   pg_relation_size(schemaname||'.'||tablename)) AS indexes_size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
EOF

echo ""
echo "========================================================================"
echo "Phase 4: Concurrent Load Simulation"
echo "========================================================================"
echo ""

echo "Running concurrent queries (simulated)..."
echo ""

# Simple concurrent load test using background jobs
concurrent_test() {
    local num_queries=20
    local query="SELECT * FROM companies WHERE ticker = 'CHGG'"

    START=$(date +%s.%N)

    for i in $(seq 1 $num_queries); do
        psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "$query" > /dev/null 2>&1 &
    done

    wait

    END=$(date +%s.%N)
    DIFF=$(echo "$END - $START" | bc)

    echo "  ✓ Executed $num_queries concurrent queries in ${DIFF}s"

    QPS=$(echo "scale=2; $num_queries / $DIFF" | bc)
    echo "  ✓ Throughput: ${QPS} queries/second"
}

concurrent_test

echo ""
echo "========================================================================"
echo "RECOMMENDATIONS"
echo "========================================================================"
echo ""

# Generate recommendations based on statistics
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME << 'EOF'
DO $$
DECLARE
    heap_hit_ratio numeric;
    idx_hit_ratio numeric;
    unused_indexes integer;
BEGIN
    -- Check heap cache hit ratio
    SELECT CASE
        WHEN sum(heap_blks_hit) + sum(heap_blks_read) = 0 THEN 0
        ELSE round(100.0 * sum(heap_blks_hit) /
            nullif(sum(heap_blks_hit) + sum(heap_blks_read), 0), 2)
    END INTO heap_hit_ratio
    FROM pg_statio_user_tables;

    -- Check index cache hit ratio
    SELECT CASE
        WHEN sum(idx_blks_hit) + sum(idx_blks_read) = 0 THEN 0
        ELSE round(100.0 * sum(idx_blks_hit) /
            nullif(sum(idx_blks_hit) + sum(idx_blks_read), 0), 2)
    END INTO idx_hit_ratio
    FROM pg_statio_user_tables;

    -- Check for unused indexes
    SELECT COUNT(*) INTO unused_indexes
    FROM pg_stat_user_indexes
    WHERE idx_scan = 0 AND schemaname = 'public';

    RAISE NOTICE '';
    RAISE NOTICE '✓ Performance Analysis:';
    RAISE NOTICE '  Heap Cache Hit Ratio: %% (target: >95%%)', heap_hit_ratio;
    RAISE NOTICE '  Index Cache Hit Ratio: %% (target: >95%%)', idx_hit_ratio;
    RAISE NOTICE '  Unused Indexes: % (consider removing)', unused_indexes;

    IF heap_hit_ratio < 95 THEN
        RAISE NOTICE '';
        RAISE NOTICE '⚠️  Heap cache hit ratio is below 95%% - consider increasing shared_buffers';
    END IF;

    IF idx_hit_ratio < 95 THEN
        RAISE NOTICE '';
        RAISE NOTICE '⚠️  Index cache hit ratio is below 95%% - consider increasing effective_cache_size';
    END IF;

    IF unused_indexes > 0 THEN
        RAISE NOTICE '';
        RAISE NOTICE '⚠️  Found % unused indexes - consider removing to improve write performance', unused_indexes;
    END IF;
END $$;
EOF

echo ""
echo "========================================================================"
echo "Load Testing Complete"
echo "========================================================================"
echo ""

unset PGPASSWORD
