"""Initial schema with TimescaleDB and pgvector

Revision ID: 001
Revises:
Create Date: 2025-10-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to version 001."""

    # ====================
    # 1. CREATE EXTENSIONS
    # ====================

    # Enable TimescaleDB extension
    op.execute('CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE')

    # Enable pgvector extension for embeddings
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')

    # Enable UUID generation
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # ====================
    # 2. CREATE TABLES
    # ====================

    # Companies table
    op.create_table(
        'companies',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('ticker', sa.String(10), nullable=False, unique=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('cik', sa.String(10), unique=True),
        sa.Column('sector', sa.String(100)),
        sa.Column('subsector', sa.String(100)),
        sa.Column('category', sa.String(50)),
        sa.Column('subcategory', postgresql.JSON),
        sa.Column('delivery_model', sa.String(50)),
        sa.Column('monetization_strategy', postgresql.JSON),
        sa.Column('founded_year', sa.Integer),
        sa.Column('headquarters', sa.String(255)),
        sa.Column('website', sa.String(255)),
        sa.Column('employee_count', sa.Integer),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now(), server_default=sa.func.now()),
    )

    # SEC Filings table
    op.create_table(
        'sec_filings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('companies.id'), nullable=False),
        sa.Column('filing_type', sa.String(20), nullable=False),
        sa.Column('filing_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('accession_number', sa.String(25), unique=True, nullable=False),
        sa.Column('filing_url', sa.Text),
        sa.Column('raw_text', sa.Text),
        sa.Column('parsed_sections', postgresql.JSON),
        sa.Column('processing_status', sa.String(20), server_default='pending'),
        sa.Column('processed_at', sa.DateTime(timezone=True)),
        sa.Column('error_message', sa.Text),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now(), server_default=sa.func.now()),
    )

    # Financial Metrics table (TimescaleDB hypertable)
    op.create_table(
        'financial_metrics',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('companies.id'), nullable=False),
        sa.Column('metric_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('period_type', sa.String(20), nullable=False),
        sa.Column('metric_type', sa.String(50), nullable=False),
        sa.Column('metric_category', sa.String(50)),
        sa.Column('value', sa.Float, nullable=False),
        sa.Column('unit', sa.String(20)),
        sa.Column('source', sa.String(50)),
        sa.Column('source_document_id', postgresql.UUID(as_uuid=True)),
        sa.Column('confidence_score', sa.Float),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now(), server_default=sa.func.now()),
    )

    # Convert financial_metrics to TimescaleDB hypertable
    op.execute("""
        SELECT create_hypertable(
            'financial_metrics',
            'metric_date',
            chunk_time_interval => INTERVAL '1 month',
            if_not_exists => TRUE
        )
    """)

    # Documents table
    op.create_table(
        'documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('companies.id')),
        sa.Column('document_type', sa.String(50), nullable=False),
        sa.Column('title', sa.String(500)),
        sa.Column('document_date', sa.DateTime(timezone=True)),
        sa.Column('source_url', sa.Text),
        sa.Column('storage_path', sa.Text),
        sa.Column('file_hash', sa.String(64)),
        sa.Column('file_size', sa.BigInteger),
        sa.Column('mime_type', sa.String(100)),
        sa.Column('content', sa.Text),
        sa.Column('extracted_data', postgresql.JSON),
        sa.Column('embedding', sa.String),  # Will be converted to vector(1536) after pgvector is confirmed
        sa.Column('processing_status', sa.String(20), server_default='pending'),
        sa.Column('processed_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now(), server_default=sa.func.now()),
    )

    # Document Chunks table
    op.create_table(
        'document_chunks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('documents.id'), nullable=False),
        sa.Column('chunk_index', sa.Integer, nullable=False),
        sa.Column('chunk_text', sa.Text, nullable=False),
        sa.Column('chunk_tokens', sa.Integer),
        sa.Column('embedding', sa.String),  # Will be converted to vector(1536) after pgvector is confirmed
        sa.Column('page_number', sa.Integer),
        sa.Column('section_name', sa.String(255)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now(), server_default=sa.func.now()),
    )

    # Analysis Reports table
    op.create_table(
        'analysis_reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('report_type', sa.String(50), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('companies', postgresql.JSON),
        sa.Column('date_range_start', sa.DateTime(timezone=True)),
        sa.Column('date_range_end', sa.DateTime(timezone=True)),
        sa.Column('executive_summary', sa.Text),
        sa.Column('findings', postgresql.JSON),
        sa.Column('recommendations', postgresql.JSON),
        sa.Column('report_url', sa.Text),
        sa.Column('format', sa.String(20)),
        sa.Column('cache_key', sa.String(255), unique=True),
        sa.Column('expires_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now(), server_default=sa.func.now()),
    )

    # Market Intelligence table
    op.create_table(
        'market_intelligence',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('intel_type', sa.String(50), nullable=False),
        sa.Column('category', sa.String(50)),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('summary', sa.Text),
        sa.Column('full_content', sa.Text),
        sa.Column('primary_company_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('companies.id')),
        sa.Column('related_companies', postgresql.JSON),
        sa.Column('event_date', sa.DateTime(timezone=True)),
        sa.Column('source', sa.String(255)),
        sa.Column('source_url', sa.Text),
        sa.Column('confidence_score', sa.Float),
        sa.Column('impact_assessment', postgresql.JSON),
        sa.Column('sentiment_score', sa.Float),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now(), server_default=sa.func.now()),
    )

    # ====================
    # 3. AUTHENTICATION TABLES
    # ====================

    # Users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('email', sa.String, unique=True, nullable=False),
        sa.Column('username', sa.String, unique=True, nullable=False),
        sa.Column('hashed_password', sa.String, nullable=False),
        sa.Column('full_name', sa.String),
        sa.Column('organization', sa.String),
        sa.Column('role', sa.String, nullable=False, server_default='viewer'),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('is_verified', sa.Boolean, server_default='false'),
        sa.Column('email_verified_at', sa.DateTime),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('last_login_at', sa.DateTime),
        sa.Column('api_calls_today', sa.Integer, server_default='0'),
        sa.Column('api_calls_reset_at', sa.DateTime, server_default=sa.func.now()),
    )

    # Permissions table
    op.create_table(
        'permissions',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('scope', sa.String, unique=True, nullable=False),
        sa.Column('description', sa.String),
    )

    # User-Permissions association table
    op.create_table(
        'user_permissions',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('permission_id', sa.Integer, sa.ForeignKey('permissions.id')),
    )

    # API Keys table
    op.create_table(
        'api_keys',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('name', sa.String, nullable=False),
        sa.Column('key_hash', sa.String, nullable=False, unique=True),
        sa.Column('key_prefix', sa.String, nullable=False),
        sa.Column('scopes', sa.String),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('expires_at', sa.DateTime),
        sa.Column('last_used_at', sa.DateTime),
        sa.Column('rate_limit_per_hour', sa.Integer, server_default='1000'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('revoked_at', sa.DateTime),
    )

    # User Sessions table
    op.create_table(
        'user_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('token_jti', sa.String, unique=True, nullable=False),
        sa.Column('ip_address', sa.String),
        sa.Column('user_agent', sa.String),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime, nullable=False),
        sa.Column('revoked_at', sa.DateTime),
    )

    # ====================
    # 4. CREATE INDEXES
    # ====================

    # Companies indexes
    op.create_index('idx_company_ticker', 'companies', ['ticker'])
    op.create_index('idx_company_cik', 'companies', ['cik'])
    op.create_index('idx_company_category', 'companies', ['category'])
    op.create_index('idx_company_sector_subsector', 'companies', ['sector', 'subsector'])

    # SEC Filings indexes
    op.create_index('idx_filing_date', 'sec_filings', ['filing_date'])
    op.create_index('idx_filing_type_date', 'sec_filings', ['filing_type', 'filing_date'])
    op.create_index('idx_filing_company', 'sec_filings', ['company_id'])

    # Financial Metrics indexes
    op.create_index('idx_metric_time', 'financial_metrics', ['metric_date', 'metric_type'])
    op.create_index('idx_company_metric', 'financial_metrics', ['company_id', 'metric_type', 'metric_date'])

    # Documents indexes
    op.create_index('idx_document_type_date', 'documents', ['document_type', 'document_date'])
    op.create_index('idx_document_company', 'documents', ['company_id'])

    # Document Chunks indexes
    op.create_index('idx_chunk_document', 'document_chunks', ['document_id'])

    # Analysis Reports indexes
    op.create_index('idx_report_type_date', 'analysis_reports', ['report_type', 'created_at'])
    op.create_index('idx_report_cache', 'analysis_reports', ['cache_key', 'expires_at'])

    # Market Intelligence indexes
    op.create_index('idx_intel_type_date', 'market_intelligence', ['intel_type', 'event_date'])
    op.create_index('idx_intel_company', 'market_intelligence', ['primary_company_id', 'event_date'])

    # User indexes
    op.create_index('idx_user_email', 'users', ['email'])
    op.create_index('idx_user_username', 'users', ['username'])

    # ====================
    # 5. ADD CONSTRAINTS
    # ====================

    # Unique constraints
    op.create_unique_constraint('uq_company_filing', 'sec_filings', ['company_id', 'accession_number'])
    op.create_unique_constraint('uq_company_metric_period', 'financial_metrics',
                               ['company_id', 'metric_type', 'metric_date', 'period_type'])
    op.create_unique_constraint('uq_document_chunk', 'document_chunks', ['document_id', 'chunk_index'])

    # ====================
    # 6. TIMESCALEDB OPTIMIZATIONS
    # ====================

    # Enable compression on financial_metrics (compress data older than 30 days)
    op.execute("""
        ALTER TABLE financial_metrics SET (
            timescaledb.compress,
            timescaledb.compress_segmentby = 'company_id, metric_type'
        )
    """)

    # Add compression policy (compress chunks older than 30 days)
    op.execute("""
        SELECT add_compression_policy('financial_metrics', INTERVAL '30 days')
    """)

    # Add retention policy (drop chunks older than 2 years)
    op.execute("""
        SELECT add_retention_policy('financial_metrics', INTERVAL '2 years')
    """)

    # Create continuous aggregate for daily metrics summary
    op.execute("""
        CREATE MATERIALIZED VIEW daily_metrics_summary
        WITH (timescaledb.continuous) AS
        SELECT
            company_id,
            metric_type,
            time_bucket('1 day', metric_date) AS day,
            AVG(value) AS avg_value,
            MIN(value) AS min_value,
            MAX(value) AS max_value,
            COUNT(*) AS data_points
        FROM financial_metrics
        GROUP BY company_id, metric_type, day
        WITH NO DATA
    """)

    # Add refresh policy for continuous aggregate
    op.execute("""
        SELECT add_continuous_aggregate_policy('daily_metrics_summary',
            start_offset => INTERVAL '3 days',
            end_offset => INTERVAL '1 hour',
            schedule_interval => INTERVAL '1 hour')
    """)

    print("✅ Initial schema with TimescaleDB and pgvector created successfully")


def downgrade() -> None:
    """Downgrade schema from version 001."""

    # Drop continuous aggregate and policies
    op.execute("DROP MATERIALIZED VIEW IF EXISTS daily_metrics_summary CASCADE")

    # Drop tables in reverse order (respecting foreign keys)
    op.drop_table('user_sessions')
    op.drop_table('api_keys')
    op.drop_table('user_permissions')
    op.drop_table('permissions')
    op.drop_table('users')
    op.drop_table('market_intelligence')
    op.drop_table('analysis_reports')
    op.drop_table('document_chunks')
    op.drop_table('documents')
    op.drop_table('financial_metrics')
    op.drop_table('sec_filings')
    op.drop_table('companies')

    # Drop extensions (optional - comment out if you want to keep extensions)
    # op.execute('DROP EXTENSION IF EXISTS vector')
    # op.execute('DROP EXTENSION IF EXISTS timescaledb CASCADE')
    # op.execute('DROP EXTENSION IF EXISTS "uuid-ossp"')

    print("✅ Schema downgraded successfully")
