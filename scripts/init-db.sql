-- Corporate Intelligence Platform Database Initialization Script
-- Creates necessary extensions and initial schema

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Performance tuning for TimescaleDB
ALTER SYSTEM SET shared_preload_libraries = 'timescaledb,pg_stat_statements';
ALTER SYSTEM SET timescaledb.telemetry_level = 'off';

-- Set optimal PostgreSQL settings for analytics workloads
ALTER SYSTEM SET max_connections = 200;
ALTER SYSTEM SET shared_buffers = '2GB';
ALTER SYSTEM SET effective_cache_size = '6GB';
ALTER SYSTEM SET maintenance_work_mem = '512MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;
ALTER SYSTEM SET random_page_cost = 1.1;
ALTER SYSTEM SET effective_io_concurrency = 200;
ALTER SYSTEM SET work_mem = '16MB';
ALTER SYSTEM SET min_wal_size = '1GB';
ALTER SYSTEM SET max_wal_size = '4GB';

-- Create schemas
CREATE SCHEMA IF NOT EXISTS analytics;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS mart;

-- Grant permissions
GRANT ALL ON SCHEMA public TO intel_user;
GRANT ALL ON SCHEMA analytics TO intel_user;
GRANT ALL ON SCHEMA staging TO intel_user;
GRANT ALL ON SCHEMA mart TO intel_user;

-- Create custom types
DO $$ BEGIN
    CREATE TYPE user_role AS ENUM ('admin', 'analyst', 'viewer', 'service');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE filing_type AS ENUM ('10-K', '10-Q', '8-K', 'S-1', 'DEF 14A', 'PROXY');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE analysis_status AS ENUM ('pending', 'processing', 'completed', 'failed');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- Create audit function for tracking changes
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create function for automatic TimescaleDB hypertable creation
CREATE OR REPLACE FUNCTION create_hypertable_if_not_exists(
    table_name TEXT,
    time_column TEXT,
    chunk_interval INTERVAL DEFAULT INTERVAL '1 month'
)
RETURNS VOID AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM timescaledb_information.hypertables 
        WHERE hypertable_name = table_name
    ) THEN
        PERFORM create_hypertable(table_name, time_column, 
                                 chunk_time_interval => chunk_interval);
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Create compression policy function
CREATE OR REPLACE FUNCTION add_compression_policy_if_not_exists(
    table_name TEXT,
    compress_after INTERVAL
)
RETURNS VOID AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM timescaledb_information.compression_settings
        WHERE hypertable_name = table_name
    ) THEN
        PERFORM add_compression_policy(table_name, compress_after);
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Create retention policy function
CREATE OR REPLACE FUNCTION add_retention_policy_if_not_exists(
    table_name TEXT,
    drop_after INTERVAL
)
RETURNS VOID AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM timescaledb_information.retention_policies
        WHERE hypertable_name = table_name
    ) THEN
        PERFORM add_retention_policy(table_name, drop_after);
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Create materialized view refresh function
CREATE OR REPLACE FUNCTION refresh_materialized_views()
RETURNS VOID AS $$
DECLARE
    mat_view RECORD;
BEGIN
    FOR mat_view IN 
        SELECT schemaname, matviewname 
        FROM pg_matviews 
        WHERE schemaname IN ('analytics', 'mart')
    LOOP
        EXECUTE format('REFRESH MATERIALIZED VIEW CONCURRENTLY %I.%I', 
                      mat_view.schemaname, mat_view.matviewname);
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Create index maintenance function
CREATE OR REPLACE FUNCTION maintain_indexes()
RETURNS VOID AS $$
BEGIN
    -- Reindex tables with high bloat
    PERFORM schemaname, tablename 
    FROM pg_tables 
    WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
    AND pg_relation_size(schemaname||'.'||tablename) > 100000000; -- 100MB
    
    -- Analyze tables for query optimization
    ANALYZE;
END;
$$ LANGUAGE plpgsql;

-- Schedule maintenance jobs
SELECT cron.schedule('refresh-materialized-views', '0 */6 * * *', 
                    'SELECT refresh_materialized_views()');
SELECT cron.schedule('maintain-indexes', '0 2 * * 0', 
                    'SELECT maintain_indexes()');

-- Create initial indices for common queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_companies_ticker 
    ON companies(ticker) WHERE deleted_at IS NULL;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_companies_sector 
    ON companies(sector) WHERE deleted_at IS NULL;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_filings_company_date 
    ON sec_filings(company_id, filing_date DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_metrics_company_date 
    ON financial_metrics(company_id, date DESC);

-- Create GIN index for full-text search
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_documents_content_gin 
    ON documents USING gin(to_tsvector('english', content));

-- Create HNSW index for vector similarity search (pgvector)
-- Note: HNSW provides better query performance than IVFFlat for most use cases
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chunks_embedding_hnsw 
    ON document_chunks USING hnsw(embedding vector_l2_ops)
    WITH (m = 16, ef_construction = 64);

-- Output initialization complete message
DO $$
BEGIN
    RAISE NOTICE 'Database initialization completed successfully';
    RAISE NOTICE 'Extensions enabled: TimescaleDB, pgvector, pg_stat_statements';
    RAISE NOTICE 'Schemas created: analytics, staging, mart';
    RAISE NOTICE 'Helper functions created for hypertables and maintenance';
END $$;