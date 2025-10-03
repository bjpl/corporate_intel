#!/bin/bash
# Docker Database Initialization Script
# Sets up PostgreSQL with TimescaleDB and pgvector extensions

set -e

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[DB-INIT]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[DB-INIT]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[DB-INIT]${NC} $1"
}

log_error() {
    echo -e "${RED}[DB-INIT]${NC} $1"
}

# This script runs as part of docker-entrypoint-initdb.d
# It's executed automatically by the PostgreSQL container

log_info "========================================"
log_info "Initializing Corporate Intel Database"
log_info "Database: ${POSTGRES_DB}"
log_info "User: ${POSTGRES_USER}"
log_info "========================================"

# Enable TimescaleDB extension
log_info "Enabling TimescaleDB extension..."
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
    SELECT extname, extversion FROM pg_extension WHERE extname = 'timescaledb';
EOSQL
log_success "TimescaleDB extension enabled"

# Enable pgvector extension for embeddings
log_info "Enabling pgvector extension..."
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE EXTENSION IF NOT EXISTS vector;
    SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';
EOSQL
log_success "pgvector extension enabled"

# Enable additional useful extensions
log_info "Enabling additional PostgreSQL extensions..."
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- UUID support
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

    -- Cryptographic functions
    CREATE EXTENSION IF NOT EXISTS pgcrypto;

    -- Full-text search
    CREATE EXTENSION IF NOT EXISTS pg_trgm;

    -- JSON functions
    CREATE EXTENSION IF NOT EXISTS btree_gin;
    CREATE EXTENSION IF NOT EXISTS btree_gist;

    SELECT extname, extversion FROM pg_extension
    WHERE extname IN ('uuid-ossp', 'pgcrypto', 'pg_trgm', 'btree_gin', 'btree_gist');
EOSQL
log_success "Additional extensions enabled"

# Create schemas
log_info "Creating application schemas..."
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Main application schema
    CREATE SCHEMA IF NOT EXISTS corporate_intel;

    -- Analytics schema for processed data
    CREATE SCHEMA IF NOT EXISTS analytics;

    -- Audit schema for tracking changes
    CREATE SCHEMA IF NOT EXISTS audit;

    -- Grant permissions
    GRANT USAGE ON SCHEMA corporate_intel TO ${POSTGRES_USER};
    GRANT USAGE ON SCHEMA analytics TO ${POSTGRES_USER};
    GRANT USAGE ON SCHEMA audit TO ${POSTGRES_USER};

    GRANT CREATE ON SCHEMA corporate_intel TO ${POSTGRES_USER};
    GRANT CREATE ON SCHEMA analytics TO ${POSTGRES_USER};
    GRANT CREATE ON SCHEMA audit TO ${POSTGRES_USER};

    -- Set search path
    ALTER DATABASE ${POSTGRES_DB} SET search_path TO corporate_intel, analytics, audit, public;
EOSQL
log_success "Application schemas created"

# Create audit trigger function
log_info "Creating audit trigger function..."
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-'EOSQL'
    CREATE OR REPLACE FUNCTION audit.audit_trigger()
    RETURNS TRIGGER AS $$
    BEGIN
        IF TG_OP = 'INSERT' THEN
            INSERT INTO audit.log (
                table_name, operation, row_data, changed_at
            ) VALUES (
                TG_TABLE_NAME, 'INSERT', to_jsonb(NEW), NOW()
            );
            RETURN NEW;
        ELSIF TG_OP = 'UPDATE' THEN
            INSERT INTO audit.log (
                table_name, operation, row_data, changed_fields, changed_at
            ) VALUES (
                TG_TABLE_NAME, 'UPDATE', to_jsonb(NEW),
                jsonb_diff(to_jsonb(OLD), to_jsonb(NEW)), NOW()
            );
            RETURN NEW;
        ELSIF TG_OP = 'DELETE' THEN
            INSERT INTO audit.log (
                table_name, operation, row_data, changed_at
            ) VALUES (
                TG_TABLE_NAME, 'DELETE', to_jsonb(OLD), NOW()
            );
            RETURN OLD;
        END IF;
    END;
    $$ LANGUAGE plpgsql SECURITY DEFINER;
EOSQL
log_success "Audit trigger function created"

# Create audit log table
log_info "Creating audit log table..."
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE TABLE IF NOT EXISTS audit.log (
        id BIGSERIAL PRIMARY KEY,
        table_name TEXT NOT NULL,
        operation TEXT NOT NULL,
        row_data JSONB,
        changed_fields JSONB,
        changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        changed_by TEXT DEFAULT current_user
    );

    -- Create index for efficient querying
    CREATE INDEX IF NOT EXISTS idx_audit_log_table_name ON audit.log(table_name);
    CREATE INDEX IF NOT EXISTS idx_audit_log_changed_at ON audit.log(changed_at DESC);

    -- Create hypertable for time-series audit data
    SELECT create_hypertable(
        'audit.log',
        'changed_at',
        if_not_exists => TRUE,
        chunk_time_interval => INTERVAL '1 month'
    );

    -- Set retention policy (keep audit logs for 2 years)
    SELECT add_retention_policy(
        'audit.log',
        INTERVAL '2 years',
        if_not_exists => TRUE
    );
EOSQL
log_success "Audit log table created with TimescaleDB hypertable"

# Create helper function for JSONB diff
log_info "Creating helper functions..."
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-'EOSQL'
    CREATE OR REPLACE FUNCTION jsonb_diff(old_data jsonb, new_data jsonb)
    RETURNS jsonb AS $$
    DECLARE
        result jsonb := '{}'::jsonb;
        k text;
        v jsonb;
    BEGIN
        FOR k, v IN SELECT * FROM jsonb_each(new_data)
        LOOP
            IF old_data->k IS DISTINCT FROM v THEN
                result := result || jsonb_build_object(
                    k, jsonb_build_object(
                        'old', old_data->k,
                        'new', v
                    )
                );
            END IF;
        END LOOP;
        RETURN result;
    END;
    $$ LANGUAGE plpgsql IMMUTABLE;
EOSQL
log_success "Helper functions created"

# Set database configuration for optimal performance
log_info "Configuring database performance settings..."
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Optimize for analytics workloads
    ALTER DATABASE ${POSTGRES_DB} SET work_mem = '32MB';
    ALTER DATABASE ${POSTGRES_DB} SET maintenance_work_mem = '256MB';
    ALTER DATABASE ${POSTGRES_DB} SET effective_cache_size = '4GB';
    ALTER DATABASE ${POSTGRES_DB} SET random_page_cost = 1.1;

    -- TimescaleDB specific settings
    ALTER DATABASE ${POSTGRES_DB} SET timescaledb.max_background_workers = 8;
EOSQL
log_success "Database performance settings configured"

# Create vector similarity search function
log_info "Creating vector search functions..."
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-'EOSQL'
    -- Cosine similarity for vector search
    CREATE OR REPLACE FUNCTION cosine_similarity(a vector, b vector)
    RETURNS float AS $$
        SELECT 1 - (a <=> b)
    $$ LANGUAGE SQL IMMUTABLE STRICT PARALLEL SAFE;

    -- L2 distance for vector search
    CREATE OR REPLACE FUNCTION euclidean_distance(a vector, b vector)
    RETURNS float AS $$
        SELECT a <-> b
    $$ LANGUAGE SQL IMMUTABLE STRICT PARALLEL SAFE;
EOSQL
log_success "Vector search functions created"

# Display summary
log_info "========================================"
log_info "Database Initialization Summary:"
log_info "========================================"
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    SELECT
        'Extensions' as category,
        count(*) as count
    FROM pg_extension
    WHERE extname IN ('timescaledb', 'vector', 'uuid-ossp', 'pgcrypto', 'pg_trgm')

    UNION ALL

    SELECT
        'Schemas' as category,
        count(*) as count
    FROM pg_namespace
    WHERE nspname IN ('corporate_intel', 'analytics', 'audit')

    UNION ALL

    SELECT
        'Functions' as category,
        count(*) as count
    FROM pg_proc p
    JOIN pg_namespace n ON p.pronamespace = n.oid
    WHERE n.nspname IN ('audit', 'public')
    AND p.proname IN ('audit_trigger', 'jsonb_diff', 'cosine_similarity', 'euclidean_distance');
EOSQL

log_success "========================================"
log_success "Database initialization completed!"
log_success "========================================"
