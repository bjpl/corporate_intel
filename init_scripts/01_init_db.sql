-- Enable required PostgreSQL extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "timescaledb";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Create schema for better organization
CREATE SCHEMA IF NOT EXISTS intel;

-- Set default search path
SET search_path TO intel, public;

-- Create custom types for EdTech categories
CREATE TYPE edtech_category AS ENUM (
    'k12',
    'higher_education',
    'corporate_learning',
    'direct_to_consumer',
    'enabling_technology'
);

CREATE TYPE delivery_model AS ENUM (
    'b2b',
    'b2c',
    'b2b2c',
    'marketplace',
    'hybrid'
);

-- Function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create continuous aggregates for common metrics (after tables are created)
-- This will be done in the next migration after hypertables are set up