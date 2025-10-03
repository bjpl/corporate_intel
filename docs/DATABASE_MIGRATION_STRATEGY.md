# Database Migration Strategy - Corporate Intelligence Platform

## Executive Summary

This document outlines the comprehensive database migration strategy for the Corporate Intelligence Platform using Alembic with PostgreSQL/TimescaleDB. The strategy ensures version-controlled schema evolution, supports TimescaleDB-specific features, and integrates seamlessly with CI/CD pipelines.

**Status**: Architecture Design Phase
**Last Updated**: 2025-10-02
**Owner**: System Architecture Team

---

## 1. Current State Analysis

### 1.1 Database Schema Overview

The platform uses **PostgreSQL 15** with **TimescaleDB** and **pgvector** extensions:

**Tables Identified:**
1. **companies** - EdTech company master data (UUID primary key)
2. **sec_filings** - SEC filing documents with content
3. **financial_metrics** - Time-series metrics (TimescaleDB hypertable)
4. **documents** - Generic document storage with vector embeddings
5. **document_chunks** - Chunked documents for semantic search
6. **analysis_reports** - Generated analysis reports with caching
7. **market_intelligence** - Market insights and competitive intelligence
8. **users** - Authentication and user management (UUID primary key)
9. **permissions** - Fine-grained access control
10. **user_permissions** - Many-to-many user-permission mapping
11. **api_keys** - API key management with scoping
12. **user_sessions** - Session tracking for security

### 1.2 Key Features Requiring Special Handling

**TimescaleDB Hypertables:**
- `financial_metrics` table uses `metric_date` as time column
- Requires special migration handling for hypertable creation
- Compression policies after 30 days (configurable)
- Retention policies (2 years default)

**pgvector Indexes:**
- `documents.embedding` - IVFFlat index for 1536-dimensional vectors
- `document_chunks.embedding` - IVFFlat index for chunked embeddings
- Vector similarity searches (cosine distance)

**Complex Relationships:**
- Cascading deletes on company relationships
- Many-to-many user permissions
- Foreign key constraints across all modules

**Special Constraints:**
- Unique compound indexes (company_id + metric_type + metric_date)
- Partial indexes for performance
- GIN indexes for JSON columns (future consideration)

---

## 2. Alembic Architecture Design

### 2.1 Configuration Structure

```
corporate_intel/
├── alembic/
│   ├── versions/          # Migration scripts
│   ├── env.py            # Alembic environment configuration
│   ├── script.py.mako    # Migration template
│   └── README            # Version control documentation
├── alembic.ini           # Alembic configuration
├── src/
│   ├── db/
│   │   ├── base.py       # Base declarative class
│   │   └── models.py     # SQLAlchemy models
│   └── auth/
│       └── models.py     # Auth models
└── scripts/
    ├── migrations/
    │   ├── init_timescale.py      # TimescaleDB initialization
    │   ├── create_baseline.py     # Baseline migration generator
    │   └── validate_migration.py  # Pre-deployment validation
    └── init-db.sql       # Database initialization
```

### 2.2 Environment-Specific Configuration

**Multi-Environment Support:**

```python
# alembic/env.py enhancements
def get_url():
    """Get database URL based on environment."""
    environment = os.getenv("ENVIRONMENT", "development")

    if environment == "production":
        # Use production database URL with SSL
        return os.getenv("DATABASE_URL_PRODUCTION")
    elif environment == "staging":
        return os.getenv("DATABASE_URL_STAGING")
    else:
        # Development/local
        return settings.sync_database_url
```

**Environment Variable Precedence:**
1. `DATABASE_URL_{ENVIRONMENT}` - Explicit environment URLs
2. `DATABASE_URL` - Fallback URL
3. Settings from `src.core.config` - Default configuration

### 2.3 TimescaleDB Integration Strategy

**Custom Migration Operations:**

```python
# Custom Alembic operations for TimescaleDB
from alembic.operations import Operations, MigrateOperation

@Operations.register_operation("create_hypertable")
class CreateHypertableOp(MigrateOperation):
    """Create TimescaleDB hypertable."""

    def __init__(self, table_name, time_column, chunk_interval=None):
        self.table_name = table_name
        self.time_column = time_column
        self.chunk_interval = chunk_interval or "1 week"

    @classmethod
    def create_hypertable(cls, operations, table_name, time_column, **kwargs):
        op = cls(table_name, time_column, **kwargs)
        return operations.invoke(op)

@Operations.implementation_for(CreateHypertableOp)
def create_hypertable(operations, operation):
    """Execute hypertable creation."""
    operations.execute(
        f"SELECT create_hypertable('{operation.table_name}', "
        f"'{operation.time_column}', chunk_time_interval => "
        f"INTERVAL '{operation.chunk_interval}');"
    )
```

**Compression Policy:**

```python
@Operations.register_operation("add_compression_policy")
class AddCompressionPolicyOp(MigrateOperation):
    """Add compression policy to hypertable."""

    def __init__(self, table_name, compress_after):
        self.table_name = table_name
        self.compress_after = compress_after

    @classmethod
    def add_compression_policy(cls, operations, table_name, compress_after):
        op = cls(table_name, compress_after)
        return operations.invoke(op)

@Operations.implementation_for(AddCompressionPolicyOp)
def add_compression_policy(operations, operation):
    """Execute compression policy."""
    operations.execute(
        f"ALTER TABLE {operation.table_name} SET (timescaledb.compress);"
    )
    operations.execute(
        f"SELECT add_compression_policy('{operation.table_name}', "
        f"INTERVAL '{operation.compress_after}');"
    )
```

### 2.4 pgvector Index Strategy

**Vector Index Creation:**

```python
# Migration pattern for vector indexes
def upgrade():
    # Create table first
    op.create_table(
        'documents',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('embedding', Vector(1536), nullable=True),
        # ... other columns
    )

    # Create vector index (IVFFlat)
    # Note: Requires data in table first for IVFFlat
    op.execute("""
        CREATE INDEX idx_document_embedding
        ON documents
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100);
    """)

def downgrade():
    op.drop_index('idx_document_embedding')
    op.drop_table('documents')
```

---

## 3. Migration Workflow Design

### 3.1 Initial Baseline Migration

**Purpose:** Capture current schema state as version-controlled baseline.

**Approach:**
1. Generate initial migration from current models
2. Include all extensions (TimescaleDB, pgvector)
3. Create all tables, indexes, and constraints
4. Set up hypertables and compression policies

**Script:**

```bash
# Create baseline migration
alembic revision --autogenerate -m "Initial baseline schema"

# Review generated migration
# Manual adjustments needed for:
# - TimescaleDB hypertables
# - Vector indexes (IVFFlat)
# - Extension creation order
```

**Baseline Migration Structure:**

```python
# versions/001_initial_baseline.py
"""Initial baseline schema

Revision ID: 001_baseline
Revises:
Create Date: 2025-10-02
"""

def upgrade():
    # 1. Create extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb;")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_stat_statements;")

    # 2. Create base tables (companies, users, etc.)
    # ... autogenerated table creation

    # 3. Convert financial_metrics to hypertable
    op.execute("""
        SELECT create_hypertable(
            'financial_metrics',
            'metric_date',
            chunk_time_interval => INTERVAL '1 week'
        );
    """)

    # 4. Add compression policy
    op.execute("""
        ALTER TABLE financial_metrics
        SET (timescaledb.compress,
             timescaledb.compress_segmentby = 'company_id,metric_type');
    """)
    op.execute("""
        SELECT add_compression_policy(
            'financial_metrics',
            INTERVAL '30 days'
        );
    """)

    # 5. Create vector indexes (after tables populated)
    # Defer to post-deployment script

def downgrade():
    # Drop in reverse order
    op.execute("DROP TABLE IF EXISTS financial_metrics CASCADE;")
    # ... other drops
    op.execute("DROP EXTENSION IF EXISTS vector;")
    op.execute("DROP EXTENSION IF EXISTS timescaledb CASCADE;")
```

### 3.2 Ongoing Migration Patterns

**Common Patterns:**

1. **Add Column:**
```python
def upgrade():
    op.add_column('companies',
        sa.Column('market_cap', sa.BigInteger(), nullable=True)
    )
    # Backfill if needed
    op.execute("UPDATE companies SET market_cap = 0 WHERE market_cap IS NULL;")
    op.alter_column('companies', 'market_cap', nullable=False)
```

2. **Add Index:**
```python
def upgrade():
    op.create_index(
        'idx_companies_market_cap',
        'companies',
        ['market_cap', 'sector'],
        postgresql_using='btree'
    )
```

3. **Add Foreign Key:**
```python
def upgrade():
    op.create_foreign_key(
        'fk_metrics_company',
        'financial_metrics',
        'companies',
        ['company_id'],
        ['id'],
        ondelete='CASCADE'
    )
```

4. **Modify Hypertable:**
```python
def upgrade():
    # Add column to hypertable
    op.add_column('financial_metrics',
        sa.Column('source_confidence', sa.Float(), nullable=True)
    )
    # Note: Cannot add NOT NULL to existing hypertable column without backfill
```

### 3.3 Data Migration Strategy

**Zero-Downtime Migrations:**

**Phase 1: Additive Changes**
- Add new columns as nullable
- Add new tables/indexes
- Deploy application code that writes to both old and new

**Phase 2: Backfill**
- Run background job to populate new columns
- Monitor progress and performance

**Phase 3: Switch Over**
- Deploy code that reads from new schema
- Verify data consistency

**Phase 4: Cleanup**
- Remove old columns/tables
- Make new columns NOT NULL if needed

**Example - Column Rename:**

```python
# Migration 1: Add new column
def upgrade():
    op.add_column('companies',
        sa.Column('employee_count_verified', sa.Integer(), nullable=True)
    )
    # Backfill
    op.execute("""
        UPDATE companies
        SET employee_count_verified = employee_count
    """)

# Migration 2 (after code deployment): Remove old column
def upgrade():
    op.drop_column('companies', 'employee_count')
```

---

## 4. Rollback Strategy

### 4.1 Rollback Principles

**Guidelines:**
1. **Every upgrade must have a working downgrade**
2. **Test downgrades in staging before production**
3. **Data loss in downgrades must be documented**
4. **Critical tables require backup before migration**

### 4.2 Rollback Patterns

**Safe Rollback (No Data Loss):**
```python
def upgrade():
    op.add_column('companies', sa.Column('new_field', sa.String(100)))

def downgrade():
    op.drop_column('companies', 'new_field')
    # Safe: new field likely empty or non-critical
```

**Destructive Rollback (Data Loss):**
```python
def upgrade():
    op.drop_column('companies', 'deprecated_field')

def downgrade():
    op.add_column('companies',
        sa.Column('deprecated_field', sa.String(100), nullable=True)
    )
    # WARNING: Data in deprecated_field is lost permanently
    # Document in migration docstring
```

### 4.3 Emergency Rollback Procedure

**Manual Rollback Steps:**

```bash
# 1. Stop application (prevent writes)
docker-compose stop api

# 2. Backup current database
docker-compose exec postgres pg_dump -U intel_user corporate_intel > backup.sql

# 3. Rollback to specific version
docker-compose exec api alembic downgrade -1  # One version back
# OR
docker-compose exec api alembic downgrade <revision>

# 4. Verify database state
docker-compose exec postgres psql -U intel_user corporate_intel -c "\dt"

# 5. Restart application with previous code version
git checkout <previous_commit>
docker-compose up -d api
```

---

## 5. CI/CD Integration

### 5.1 Pre-Deployment Validation

**Migration Validation Script:**

```python
# scripts/migrations/validate_migration.py
"""Validate migration before deployment."""
import sys
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

def validate_migration():
    """Run validation checks on pending migrations."""
    config = Config("alembic.ini")
    script = ScriptDirectory.from_config(config)

    # Check 1: Ensure all migrations have upgrade/downgrade
    for revision in script.walk_revisions():
        if not revision.module.upgrade:
            print(f"ERROR: {revision.revision} missing upgrade()")
            return False
        if not revision.module.downgrade:
            print(f"ERROR: {revision.revision} missing downgrade()")
            return False

    # Check 2: Check for destructive operations
    destructive_ops = [
        'drop_table',
        'drop_column',
        'drop_constraint',
    ]

    for revision in script.walk_revisions():
        source = revision.module.__doc__ or ""
        for op in destructive_ops:
            if op in source:
                print(f"WARNING: {revision.revision} contains {op}")

    # Check 3: Test migration in isolated database
    # Create test database, run migration, verify schema

    return True

if __name__ == "__main__":
    sys.exit(0 if validate_migration() else 1)
```

### 5.2 GitHub Actions Workflow

**Migration CI Pipeline:**

```yaml
# .github/workflows/database-migration.yml
name: Database Migration CI

on:
  pull_request:
    paths:
      - 'alembic/versions/**'
      - 'src/db/models.py'
      - 'src/auth/models.py'

jobs:
  validate-migration:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: timescale/timescaledb:latest-pg15
        env:
          POSTGRES_USER: test_user
          POSTGRES_PASSWORD: test_password
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt

      - name: Run migration validation
        run: |
          python scripts/migrations/validate_migration.py

      - name: Test migration (upgrade)
        env:
          DATABASE_URL: postgresql://test_user:test_password@localhost/test_db
        run: |
          alembic upgrade head

      - name: Verify schema
        run: |
          python scripts/migrations/verify_schema.py

      - name: Test rollback (downgrade)
        run: |
          alembic downgrade -1
          alembic upgrade head

      - name: Generate migration report
        run: |
          alembic history --verbose > migration_report.txt

      - name: Comment on PR
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const report = fs.readFileSync('migration_report.txt', 'utf8');
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: '## Migration Validation\n```\n' + report + '\n```'
            });
```

### 5.3 Deployment Automation

**Docker Entrypoint Migration:**

```bash
# scripts/docker-entrypoint.sh
#!/bin/bash
set -e

# Wait for database
echo "Waiting for PostgreSQL..."
while ! pg_isready -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER; do
  sleep 1
done

# Run migrations
echo "Running database migrations..."
alembic upgrade head

# Start application
echo "Starting application..."
exec uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

**Kubernetes Job for Migrations:**

```yaml
# k8s/migration-job.yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: db-migration
spec:
  template:
    spec:
      containers:
      - name: migration
        image: corporate-intel-api:latest
        command: ["alembic", "upgrade", "head"]
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: url
      restartPolicy: OnFailure
  backoffLimit: 3
```

---

## 6. Testing Strategy

### 6.1 Migration Testing Levels

**1. Unit Tests (Model Validation):**
```python
# tests/test_migrations.py
def test_models_match_migrations():
    """Ensure models match latest migration."""
    from alembic.autogenerate import compare_metadata
    from src.db.base import Base
    from alembic.migration import MigrationContext

    # Compare current models to database schema
    with engine.connect() as conn:
        ctx = MigrationContext.configure(conn)
        diff = compare_metadata(ctx, Base.metadata)
        assert len(diff) == 0, f"Model-migration mismatch: {diff}"
```

**2. Integration Tests (Full Migration):**
```python
def test_full_migration_cycle():
    """Test complete upgrade/downgrade cycle."""
    # Start with empty database
    alembic_cfg = Config("alembic.ini")

    # Upgrade to head
    command.upgrade(alembic_cfg, "head")

    # Verify all tables exist
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    assert "companies" in tables
    assert "financial_metrics" in tables

    # Downgrade to base
    command.downgrade(alembic_cfg, "base")

    # Verify clean state
    tables = inspector.get_table_names()
    assert len(tables) == 0
```

**3. Data Integrity Tests:**
```python
def test_data_preserved_after_migration():
    """Ensure data survives migration."""
    # Insert test data
    # Run migration
    # Verify data still present and valid
```

### 6.2 Staging Environment Testing

**Pre-Production Checklist:**
- [ ] Restore production data to staging
- [ ] Run migration on staging
- [ ] Verify application functionality
- [ ] Test rollback procedure
- [ ] Measure migration duration
- [ ] Check for locking issues
- [ ] Validate data integrity

---

## 7. Monitoring & Observability

### 7.1 Migration Metrics

**Track:**
- Migration execution time
- Number of rows affected
- Lock duration on tables
- Disk space before/after
- Index creation time

**Implementation:**

```python
# alembic/env.py
def run_migrations_online():
    import time
    from prometheus_client import Counter, Histogram

    migration_duration = Histogram(
        'alembic_migration_duration_seconds',
        'Migration execution time'
    )

    with migration_duration.time():
        # ... existing migration code
```

### 7.2 Alerting

**Alert Conditions:**
- Migration takes longer than expected (>5 minutes)
- Migration fails with error
- Rollback required
- Database connection pool exhaustion during migration

---

## 8. Best Practices & Guidelines

### 8.1 Migration Naming Convention

**Format:** `{revision}_{operation}_{table}_{description}.py`

**Examples:**
- `001_create_companies_initial_schema.py`
- `002_add_companies_market_cap_column.py`
- `003_create_index_metrics_date_type.py`

### 8.2 Migration Review Checklist

- [ ] Migration has both upgrade() and downgrade()
- [ ] Destructive operations are documented
- [ ] TimescaleDB hypertables use custom operations
- [ ] Vector indexes created after data population
- [ ] Foreign keys have proper ON DELETE clauses
- [ ] Indexes use appropriate method (btree, ivfflat, gin)
- [ ] Large data migrations use batching
- [ ] Migration tested in isolation
- [ ] Rollback tested
- [ ] Performance impact assessed

### 8.3 Common Pitfalls to Avoid

**1. Adding NOT NULL without default:**
```python
# WRONG
op.add_column('companies', sa.Column('required_field', sa.String(), nullable=False))

# RIGHT
op.add_column('companies', sa.Column('required_field', sa.String(), nullable=True))
op.execute("UPDATE companies SET required_field = 'default_value'")
op.alter_column('companies', 'required_field', nullable=False)
```

**2. Modifying hypertables incorrectly:**
```python
# WRONG - Cannot add NOT NULL to hypertable directly
op.alter_column('financial_metrics', 'new_column', nullable=False)

# RIGHT - Add as nullable, backfill, then constraint
# Hypertables have limitations on schema changes
```

**3. Creating vector index on empty table:**
```python
# WRONG - IVFFlat requires data
op.execute("CREATE INDEX ... USING ivfflat ...")

# RIGHT - Defer to data population script
# Or use placeholder data during migration
```

---

## 9. Disaster Recovery

### 9.1 Backup Strategy

**Pre-Migration Backup:**
```bash
# Automated backup before migration
pg_dump -Fc -U intel_user corporate_intel > backup_$(date +%Y%m%d_%H%M%S).dump
```

**Continuous WAL Archiving:**
- Enable point-in-time recovery
- Archive to S3/MinIO
- Test restore procedures monthly

### 9.2 Recovery Procedures

**Scenario 1: Failed Migration**
```bash
# Rollback migration
alembic downgrade -1

# Restore from backup if needed
pg_restore -U intel_user -d corporate_intel backup.dump

# Investigate and fix migration
# Re-test in staging
# Re-deploy
```

**Scenario 2: Data Corruption**
```bash
# Stop application
# Restore from backup
# Replay WAL to specific point in time
# Verify data integrity
# Restart application
```

---

## 10. Future Enhancements

### 10.1 Planned Improvements

1. **Automated Schema Diff Reports**
   - Generate visual diffs for migrations
   - Highlight breaking changes
   - Estimate migration duration

2. **Blue-Green Migration Strategy**
   - Zero-downtime for major schema changes
   - Parallel schema versions
   - Gradual traffic migration

3. **Migration Performance Optimization**
   - Parallel index creation
   - Batched data updates
   - Connection pooling during migration

4. **Enhanced Rollback Safety**
   - Automatic backup before migration
   - Snapshot-based instant rollback
   - Dry-run mode for production

### 10.2 Tools & Extensions

**Consider Adding:**
- `sqlfluff` - SQL linting in migrations
- `pgbackrest` - Advanced backup/restore
- `pgbouncer` - Connection pooling
- `pgaudit` - Audit logging for schema changes

---

## 11. Appendices

### Appendix A: Alembic Commands Reference

```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Manual migration (no autogenerate)
alembic revision -m "Description"

# Upgrade to latest
alembic upgrade head

# Upgrade to specific revision
alembic upgrade <revision>

# Downgrade one version
alembic downgrade -1

# Show current revision
alembic current

# Show migration history
alembic history --verbose

# Show SQL without executing
alembic upgrade head --sql

# Merge multiple heads
alembic merge -m "Merge branches" <rev1> <rev2>
```

### Appendix B: Database Schema Diagram

```
┌─────────────┐
│  companies  │──┐
└─────────────┘  │
                 │
      ┌──────────┼────────────┬─────────────┐
      │          │            │             │
      ▼          ▼            ▼             ▼
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│ filings  │ │ metrics  │ │documents │ │  intel   │
│          │ │(hypertbl)│ │ (vector) │ │          │
└──────────┘ └──────────┘ └────┬─────┘ └──────────┘
                                │
                                ▼
                         ┌──────────┐
                         │  chunks  │
                         │ (vector) │
                         └──────────┘

┌─────────────┐
│    users    │──┬──────────────┐
└─────────────┘  │              │
                 ▼              ▼
         ┌──────────┐    ┌──────────┐
         │ api_keys │    │ sessions │
         └──────────┘    └──────────┘
                 │
                 ▼
         ┌──────────────┐
         │ permissions  │
         │ (many-many)  │
         └──────────────┘
```

### Appendix C: TimescaleDB Hypertable Configuration

```sql
-- Create hypertable
SELECT create_hypertable(
    'financial_metrics',
    'metric_date',
    chunk_time_interval => INTERVAL '1 week',
    if_not_exists => TRUE
);

-- Enable compression
ALTER TABLE financial_metrics SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'company_id,metric_type',
    timescaledb.compress_orderby = 'metric_date DESC'
);

-- Add compression policy (compress after 30 days)
SELECT add_compression_policy(
    'financial_metrics',
    INTERVAL '30 days'
);

-- Add retention policy (drop after 2 years)
SELECT add_retention_policy(
    'financial_metrics',
    INTERVAL '2 years'
);

-- Create continuous aggregate (materialized view)
CREATE MATERIALIZED VIEW metrics_monthly
WITH (timescaledb.continuous) AS
SELECT
    company_id,
    metric_type,
    time_bucket('1 month', metric_date) AS month,
    AVG(value) AS avg_value,
    MAX(value) AS max_value,
    MIN(value) AS min_value
FROM financial_metrics
GROUP BY company_id, metric_type, month;
```

---

## Document Control

**Version History:**
- v1.0 (2025-10-02): Initial architecture design

**Approval:**
- System Architect: [Pending]
- Database Administrator: [Pending]
- DevOps Lead: [Pending]

**Review Schedule:** Quarterly or upon major schema changes

---

**END OF DOCUMENT**
