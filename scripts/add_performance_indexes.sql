-- Performance Indexes for Corporate Intelligence Platform
-- Created: October 5, 2025
-- Purpose: Add missing indexes for optimal query performance

-- ============================================================================
-- COMPANIES TABLE INDEXES
-- ============================================================================

-- Ticker lookup (most common query)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_companies_ticker
ON companies(ticker);

-- Category filtering
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_companies_category
ON companies(category) WHERE category IS NOT NULL;

-- Sector/subsector filtering
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_companies_sector_subsector
ON companies(sector, subsector) WHERE sector IS NOT NULL;

-- ============================================================================
-- FINANCIAL_METRICS TABLE INDEXES
-- ============================================================================

-- Covering index for common metric lookups
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_financial_metrics_lookup
ON financial_metrics(company_id, metric_type, metric_date DESC)
INCLUDE (value, unit);

-- Metric type filtering with date range
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_financial_metrics_type_date
ON financial_metrics(metric_type, metric_date DESC)
WHERE metric_type IN ('revenue', 'gross_margin', 'operating_margin', 'earnings_growth');

-- Period-based queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_financial_metrics_period
ON financial_metrics(period_type, metric_date DESC);

-- Source-based queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_financial_metrics_source
ON financial_metrics(source, created_at DESC)
WHERE source IS NOT NULL;

-- ============================================================================
-- SEC_FILINGS TABLE INDEXES
-- ============================================================================

-- Filing type and date lookup
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sec_filings_type_date
ON sec_filings(filing_type, filing_date DESC);

-- Company filings lookup
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sec_filings_company_date
ON sec_filings(company_id, filing_date DESC);

-- Processing status lookup
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sec_filings_status
ON sec_filings(processing_status, created_at DESC)
WHERE processing_status != 'completed';

-- ============================================================================
-- DOCUMENTS TABLE INDEXES
-- ============================================================================

-- Document type and date lookup
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_documents_type_date
ON documents(document_type, document_date DESC)
WHERE document_type IS NOT NULL;

-- Company documents lookup
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_documents_company
ON documents(company_id, created_at DESC)
WHERE company_id IS NOT NULL;

-- ============================================================================
-- ANALYSIS SUMMARY
-- ============================================================================

-- Expected performance improvements:
-- 1. Ticker lookups: 10-50x faster (common in API)
-- 2. Metric queries: 20-100x faster (dashboard queries)
-- 3. Filing lookups: 5-20x faster
-- 4. Category filtering: 10-30x faster

-- Index sizes (estimated):
-- - idx_companies_ticker: ~100 KB
-- - idx_financial_metrics_lookup: ~5-10 MB
-- - idx_financial_metrics_type_date: ~2-5 MB
-- - idx_sec_filings_company_date: ~1-2 MB

-- Total additional storage: ~10-20 MB
-- Performance gain: 10-100x on indexed queries

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Verify indexes were created
SELECT
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename IN ('companies', 'financial_metrics', 'sec_filings', 'documents')
ORDER BY tablename, indexname;

-- Check index sizes
SELECT
    indexname,
    pg_size_pretty(pg_relation_size(indexname::regclass)) as index_size
FROM pg_indexes
WHERE schemaname = 'public'
AND tablename IN ('companies', 'financial_metrics', 'sec_filings', 'documents')
ORDER BY pg_relation_size(indexname::regclass) DESC;

-- ============================================================================
-- MAINTENANCE
-- ============================================================================

-- Run ANALYZE after creating indexes
ANALYZE companies;
ANALYZE financial_metrics;
ANALYZE sec_filings;
ANALYZE documents;

-- Set statistics targets for key columns (better query planning)
ALTER TABLE financial_metrics ALTER COLUMN metric_type SET STATISTICS 1000;
ALTER TABLE financial_metrics ALTER COLUMN company_id SET STATISTICS 1000;
ALTER TABLE companies ALTER COLUMN ticker SET STATISTICS 1000;
