# Database Migration Guide

## Overview

This guide covers database schema migrations for the Corporate Intelligence Platform using Alembic with TimescaleDB and pgvector extensions.

## Quick Start

### 1. Initial Setup

```bash
# Set database connection
export DATABASE_URL="postgresql://intel_user:password@localhost:5432/corporate_intel"

# Or use the alternative format
export POSTGRES_URL="postgresql://intel_user:password@localhost:5432/corporate_intel"

# Check migration status
./scripts/check-migrations.sh

# Apply all migrations
./scripts/run-migrations.sh upgrade
```

### 2. Common Operations

```bash
# Check current migration status
./scripts/run-migrations.sh status

# Upgrade to latest version
./scripts/run-migrations.sh upgrade

# Downgrade one step
./scripts/run-migrations.sh downgrade

# Create new migration
./scripts/run-migrations.sh create "add new feature"
```

## Architecture

### Components

1. **Alembic**: Python-based database migration tool
2. **TimescaleDB**: Time-series data optimization for financial metrics
3. **pgvector**: Vector similarity search for document embeddings
4. **PostgreSQL**: Core relational database

### Directory Structure

```
corporate_intel/
├── alembic/
│   ├── versions/          # Migration scripts
│   │   └── 001_initial_schema_with_timescaledb.py
│   ├── env.py            # Alembic environment configuration
│   ├── script.py.mako    # Migration template
│   └── README            # Alembic readme
├── alembic.ini           # Alembic configuration
├── scripts/
│   ├── run-migrations.sh      # Migration runner
│   └── check-migrations.sh    # Migration validator
└── docs/
    └── MIGRATION_GUIDE.md     # This file
```

## Database Schema

### Core Tables

#### 1. Companies
Main entity table for EdTech companies.

**Columns:**
- `id` (UUID) - Primary key
- `ticker` (String) - Stock ticker symbol (unique)
- `name` (String) - Company name
- `cik` (String) - SEC Central Index Key
- `sector`, `subsector` - Industry classification
- `category` - EdTech category (K-12, Higher Ed, etc.)
- `subcategory` (JSON) - Detailed subcategories
- `delivery_model` - B2B, B2C, B2B2C, Marketplace
- `monetization_strategy` (JSON) - Revenue models

**Indexes:**
- `idx_company_ticker` on ticker
- `idx_company_cik` on cik
- `idx_company_category` on category
- `idx_company_sector_subsector` on (sector, subsector)

#### 2. SEC Filings
SEC documents (10-K, 10-Q, 8-K, etc.).

**Columns:**
- `id` (UUID) - Primary key
- `company_id` (UUID) - Foreign key to companies
- `filing_type` - Document type
- `filing_date` - When filed
- `accession_number` - SEC accession number (unique)
- `raw_text` - Full document text
- `parsed_sections` (JSON) - Structured sections

**Indexes:**
- `idx_filing_date` on filing_date
- `idx_filing_type_date` on (filing_type, filing_date)

#### 3. Financial Metrics (TimescaleDB Hypertable)
Time-series financial and operational metrics.

**Columns:**
- `id` (BigInt) - Primary key
- `company_id` (UUID) - Foreign key to companies
- `metric_date` - Time dimension (hypertable partition key)
- `period_type` - quarterly, annual, monthly
- `metric_type` - revenue, mau, arpu, cac, etc.
- `value` - Metric value
- `unit` - USD, percent, count
- `confidence_score` - 0-1 confidence in extraction

**TimescaleDB Features:**
- Partitioned by `metric_date` (1-month chunks)
- Compression after 30 days
- Retention policy: 2 years
- Continuous aggregate: `daily_metrics_summary`

**Indexes:**
- `idx_metric_time` on (metric_date, metric_type)
- `idx_company_metric` on (company_id, metric_type, metric_date)

#### 4. Documents
Generic document storage with vector embeddings.

**Columns:**
- `id` (UUID) - Primary key
- `company_id` (UUID) - Foreign key to companies
- `document_type` - earnings_transcript, presentation, etc.
- `content` - Full text
- `embedding` - Vector(1536) for semantic search
- `storage_path` - MinIO object storage path

**Vector Search:**
- Uses pgvector extension
- 1536-dimensional embeddings (OpenAI compatible)
- IVFFlat index for similarity search

#### 5. Document Chunks
Granular text chunks for precise semantic search.

**Columns:**
- `id` (UUID) - Primary key
- `document_id` (UUID) - Foreign key to documents
- `chunk_index` - Sequential chunk number
- `chunk_text` - Text content
- `embedding` - Vector(1536)

#### 6. Analysis Reports
Generated analysis and intelligence reports.

**Columns:**
- `id` (UUID) - Primary key
- `report_type` - competitor, segment, opportunity
- `companies` (JSON) - Array of company IDs
- `findings` (JSON) - Structured findings
- `cache_key` - For caching results

#### 7. Market Intelligence
Market events and competitive insights.

**Columns:**
- `id` (UUID) - Primary key
- `intel_type` - funding, acquisition, partnership
- `primary_company_id` - Main company involved
- `impact_assessment` (JSON) - Impact analysis
- `sentiment_score` - -1 to 1

### Authentication Tables

#### 8. Users
User accounts with role-based access control.

**Columns:**
- `id` (UUID) - Primary key
- `email`, `username` - Unique identifiers
- `hashed_password` - Bcrypt hash
- `role` - admin, analyst, viewer, service
- `api_calls_today` - Rate limiting counter

#### 9. Permissions
Fine-grained permission scopes.

**Examples:**
- `read:companies`, `write:companies`
- `read:filings`, `write:filings`
- `run:analysis`, `export:data`

#### 10. API Keys
Programmatic access keys.

**Columns:**
- `id` (UUID) - Primary key
- `user_id` - Owner
- `key_hash` - SHA256 hash of key
- `scopes` - Comma-separated permissions
- `rate_limit_per_hour` - Request limit

#### 11. User Sessions
Active session tracking for security.

**Columns:**
- `id` (UUID) - Primary key
- `user_id` - Session owner
- `token_jti` - JWT ID (unique)
- `expires_at` - Session expiration

## Migration Procedures

### Creating New Migrations

#### Auto-Generated Migration

```bash
# Let Alembic detect changes in models
./scripts/run-migrations.sh create "add user preferences table"

# Review the generated file in alembic/versions/
# Edit if needed, then apply
./scripts/run-migrations.sh upgrade
```

#### Manual Migration

```bash
# Create empty migration template
./scripts/run-migrations.sh create-empty "add custom index"

# Edit the file in alembic/versions/
# Implement upgrade() and downgrade() functions
# Apply migration
./scripts/run-migrations.sh upgrade
```

### Migration Best Practices

1. **Always Review Auto-Generated Migrations**
   ```python
   # Check the generated migration file
   # Ensure it matches your intent
   # Add custom logic if needed
   ```

2. **Write Reversible Migrations**
   ```python
   def upgrade():
       op.add_column('companies', sa.Column('new_field', sa.String(100)))

   def downgrade():
       op.drop_column('companies', 'new_field')
   ```

3. **Test Migrations Before Production**
   ```bash
   # Apply migration
   ./scripts/run-migrations.sh upgrade

   # Test the changes
   # ...

   # Rollback if needed
   ./scripts/run-migrations.sh downgrade
   ```

4. **Handle Data Migrations Carefully**
   ```python
   def upgrade():
       # Create new column
       op.add_column('companies', sa.Column('new_field', sa.String(100)))

       # Migrate data
       op.execute("""
           UPDATE companies
           SET new_field = old_field
           WHERE old_field IS NOT NULL
       """)

       # Drop old column
       op.drop_column('companies', 'old_field')
   ```

### Common Migration Patterns

#### Adding a New Table

```python
def upgrade():
    op.create_table(
        'new_table',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('idx_new_table_name', 'new_table', ['name'])

def downgrade():
    op.drop_table('new_table')
```

#### Adding a Foreign Key

```python
def upgrade():
    op.add_column('documents', sa.Column('user_id', postgresql.UUID(as_uuid=True)))
    op.create_foreign_key('fk_documents_user', 'documents', 'users', ['user_id'], ['id'])

def downgrade():
    op.drop_constraint('fk_documents_user', 'documents', type_='foreignkey')
    op.drop_column('documents', 'user_id')
```

#### Adding a Vector Index

```python
def upgrade():
    # Add vector column
    op.execute("""
        ALTER TABLE documents
        ADD COLUMN embedding vector(1536)
    """)

    # Create IVFFlat index
    op.execute("""
        CREATE INDEX idx_documents_embedding
        ON documents
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
    """)

def downgrade():
    op.execute("DROP INDEX IF EXISTS idx_documents_embedding")
    op.drop_column('documents', 'embedding')
```

#### Adding a TimescaleDB Hypertable

```python
def upgrade():
    # Create table
    op.create_table(
        'sensor_data',
        sa.Column('time', sa.DateTime(timezone=True), primary_key=True),
        sa.Column('sensor_id', sa.Integer, nullable=False),
        sa.Column('value', sa.Float),
    )

    # Convert to hypertable
    op.execute("""
        SELECT create_hypertable(
            'sensor_data',
            'time',
            chunk_time_interval => INTERVAL '1 day'
        )
    """)

    # Add compression
    op.execute("""
        ALTER TABLE sensor_data SET (
            timescaledb.compress,
            timescaledb.compress_segmentby = 'sensor_id'
        )
    """)

def downgrade():
    op.drop_table('sensor_data')
```

## Troubleshooting

### Common Issues

#### 1. Migration Conflicts

```bash
# If you see "multiple heads" error
alembic heads

# Merge heads
alembic merge -m "merge multiple heads" head1 head2

# Or reset to a clean state (CAUTION: destroys data)
./scripts/run-migrations.sh downgrade-to base
```

#### 2. Out-of-Sync Database

```bash
# Check current state
./scripts/check-migrations.sh

# Stamp database with current version (if migrations were applied manually)
alembic stamp head
```

#### 3. Failed Migration

```bash
# Downgrade to previous version
./scripts/run-migrations.sh downgrade 1

# Fix the migration file
# Try again
./scripts/run-migrations.sh upgrade
```

#### 4. Extension Not Found

```bash
# Install required extensions manually
psql $DATABASE_URL << EOF
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
EOF
```

### Validation Commands

```bash
# Check migration integrity
./scripts/check-migrations.sh

# Verify database connection
./scripts/run-migrations.sh check

# Show migration history
alembic history --verbose

# Show current revision
alembic current --verbose

# Show SQL without executing
alembic upgrade head --sql
```

## Production Deployment

### Pre-Deployment Checklist

- [ ] Review all pending migrations
- [ ] Test migrations on staging database
- [ ] Backup production database
- [ ] Plan rollback strategy
- [ ] Notify stakeholders of downtime (if needed)
- [ ] Test application with new schema

### Deployment Steps

```bash
# 1. Backup database
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql

# 2. Check migration status
./scripts/check-migrations.sh

# 3. Apply migrations
./scripts/run-migrations.sh upgrade

# 4. Verify migrations
./scripts/check-migrations.sh

# 5. Test application
# ... run integration tests ...

# 6. If rollback needed
./scripts/run-migrations.sh downgrade-to <previous_revision>
```

### Zero-Downtime Migrations

For large tables, use these strategies:

1. **Add Column (Nullable)**
   ```python
   # Migration 1: Add nullable column
   op.add_column('large_table', sa.Column('new_field', sa.String(100)))

   # Migration 2: Populate data (background job)
   # Migration 3: Make column non-nullable
   op.alter_column('large_table', 'new_field', nullable=False)
   ```

2. **Create Index Concurrently**
   ```python
   def upgrade():
       op.execute("CREATE INDEX CONCURRENTLY idx_name ON table(column)")

   def downgrade():
       op.execute("DROP INDEX CONCURRENTLY idx_name")
   ```

3. **Rename Column**
   ```python
   # Add new column, copy data, drop old column
   # Over multiple migrations to avoid locking
   ```

## Monitoring

### TimescaleDB Monitoring

```sql
-- Check hypertable stats
SELECT * FROM timescaledb_information.hypertables;

-- Check compression stats
SELECT * FROM timescaledb_information.compression_settings;

-- Check chunk information
SELECT * FROM timescaledb_information.chunks
WHERE hypertable_name = 'financial_metrics'
ORDER BY range_start DESC
LIMIT 10;
```

### pgvector Index Stats

```sql
-- Check vector index usage
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read
FROM pg_stat_user_indexes
WHERE indexname LIKE '%embedding%';
```

### Migration Performance

```bash
# Time a migration
time ./scripts/run-migrations.sh upgrade

# Show SQL that would be executed
alembic upgrade head --sql > migration.sql
```

## Advanced Topics

### Custom Migration Commands

Edit `alembic/env.py` to add custom behavior:

```python
def run_migrations_online() -> None:
    # Custom pre-migration logic
    # ...

    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        # Add custom render options
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()

    # Custom post-migration logic
    # ...
```

### Branch Management

```bash
# Create a branch label
alembic revision -m "feature branch" --branch-label feature_x

# Merge branches
alembic merge -m "merge feature" feature_x main
```

### Offline SQL Generation

```bash
# Generate SQL for offline execution
alembic upgrade head --sql > upgrade.sql

# Review and execute manually
psql $DATABASE_URL < upgrade.sql
```

## References

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [TimescaleDB Best Practices](https://docs.timescale.com/timescaledb/latest/overview/core-concepts/hypertables-and-chunks/)
- [pgvector Documentation](https://github.com/pgvector/pgvector)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review Alembic logs in the console
3. Consult database logs: `tail -f /var/log/postgresql/postgresql.log`
4. Contact the platform team

---

**Last Updated:** 2025-10-03
**Version:** 1.0.0
