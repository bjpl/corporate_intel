# Database Migration Testing Guide

## Overview

This guide provides comprehensive procedures for testing and validating database migrations for the Corporate Intelligence Platform. All migrations must pass these tests before deployment to production.

## Table of Contents

- [Quick Reference](#quick-reference)
- [Testing Procedures](#testing-procedures)
- [Rollback Procedures](#rollback-procedures)
- [Disaster Recovery](#disaster-recovery)
- [Common Issues](#common-issues)
- [CI/CD Integration](#cicd-integration)

## Quick Reference

### Run All Tests
```bash
npm test tests/migrations/
```

### Validate Migrations
```bash
bash scripts/validate-migrations.sh
```

### Create Backup
```bash
pg_dump -h localhost -U postgres -d corporate_intel -F c -f backup.dump
```

### Restore from Backup
```bash
pg_restore -h localhost -U postgres -d corporate_intel -c backup.dump
```

## Testing Procedures

### 1. Local Development Testing

#### Prerequisites
- PostgreSQL 15+ with TimescaleDB 2.13+
- Node.js 20+
- Test database: `corporate_intel_test`

#### Setup Test Environment
```bash
# Create test database
createdb -h localhost -U postgres corporate_intel_test

# Enable TimescaleDB
psql -h localhost -U postgres -d corporate_intel_test -c "CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;"

# Set environment variables
export TEST_DB_HOST=localhost
export TEST_DB_PORT=5432
export TEST_DB_NAME=corporate_intel_test
export TEST_DB_USER=postgres
export TEST_DB_PASSWORD=postgres
```

#### Run Migration Tests
```bash
# Run all migration tests
npm test tests/migrations/migration.test.js

# Run specific test suite
npm test -- --testNamePattern="Migration Up/Down Tests"

# Run with coverage
npm test -- --coverage tests/migrations/
```

### 2. Pre-Migration Validation

#### Run Validation Script
```bash
bash scripts/validate-migrations.sh
```

This script performs:
- Database connection check
- Active connection monitoring
- Lock detection
- TimescaleDB version verification
- Schema comparison
- Data integrity validation
- Backup creation and verification

#### Manual Validation Checklist

- [ ] Review migration SQL files for syntax errors
- [ ] Verify all foreign key constraints are valid
- [ ] Check for potentially blocking operations (ALTER TABLE, CREATE INDEX)
- [ ] Ensure down migration exists for every up migration
- [ ] Verify migration version numbers are sequential
- [ ] Test migrations on a copy of production data
- [ ] Document expected downtime (if any)
- [ ] Notify stakeholders of maintenance window

### 3. Migration Testing Workflow

#### Step 1: Create Backup
```bash
# Create compressed backup
pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME -F c -f backup_$(date +%Y%m%d_%H%M%S).dump

# Verify backup integrity
pg_restore --list backup_*.dump
```

#### Step 2: Apply Migration (Forward)
```bash
# Apply migration
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f migrations/20240101000000_example.up.sql

# Verify migration applied
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT * FROM schema_migrations ORDER BY version DESC LIMIT 1;"
```

#### Step 3: Validate Schema and Data
```bash
# Check table structure
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "\d+ table_name"

# Verify data integrity
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT COUNT(*) FROM table_name;"

# Check TimescaleDB features
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT * FROM timescaledb_information.hypertables;"
```

#### Step 4: Test Application
```bash
# Start application with migrated database
npm start

# Run integration tests
npm test -- --testMatch="**/integration/**"

# Manual smoke testing
# - Verify critical features work
# - Check API endpoints
# - Test data retrieval
```

#### Step 5: Test Rollback (Down)
```bash
# Apply down migration
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f migrations/20240101000000_example.down.sql

# Verify rollback
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "\dt"

# Compare with pre-migration schema
diff schema_before.sql schema_after_rollback.sql
```

### 4. Idempotency Testing

Migrations should be idempotent - running them multiple times should produce the same result.

```bash
# Run migration twice
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f migrations/20240101000000_example.up.sql
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f migrations/20240101000000_example.up.sql

# Compare schemas
pg_dump --schema-only -h $DB_HOST -U $DB_USER -d $DB_NAME > schema_after_double.sql
diff schema_after_first.sql schema_after_double.sql
```

### 5. Performance Testing

#### Measure Migration Duration
```bash
time psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f migrations/20240101000000_example.up.sql
```

#### Check Table Locks
```bash
# Monitor locks during migration
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "
SELECT
    pid,
    usename,
    pg_blocking_pids(pid) as blocked_by,
    query
FROM pg_stat_activity
WHERE datname = current_database()
AND cardinality(pg_blocking_pids(pid)) > 0;
"
```

#### Verify Index Creation
```bash
# Check index creation progress
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "
SELECT
    pid,
    now() - pg_stat_activity.query_start AS duration,
    query
FROM pg_stat_activity
WHERE query LIKE '%CREATE INDEX%';
"
```

## Rollback Procedures

### Automatic Rollback

If migration fails, automatic rollback is triggered:

```bash
#!/bin/bash
set -e

psql -h $DB_HOST -U $DB_USER -d $DB_NAME << EOF
BEGIN;
\i migrations/20240101000000_example.up.sql
COMMIT;
EOF

if [ $? -ne 0 ]; then
    echo "Migration failed, rolling back..."
    psql -h $DB_HOST -U $DB_USER -d $DB_NAME << EOF
BEGIN;
\i migrations/20240101000000_example.down.sql
COMMIT;
EOF
fi
```

### Manual Rollback Steps

1. **Identify Migration Version**
```bash
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT * FROM schema_migrations ORDER BY version DESC LIMIT 1;"
```

2. **Create Pre-Rollback Backup**
```bash
pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME -F c -f pre_rollback_backup.dump
```

3. **Apply Down Migration**
```bash
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f migrations/YYYYMMDDHHMMSS_migration_name.down.sql
```

4. **Verify Rollback**
```bash
# Check schema
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "\dt"

# Verify data integrity
bash scripts/validate-migrations.sh

# Test application
npm test
```

5. **Update Migration Record**
```bash
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "DELETE FROM schema_migrations WHERE version = 'YYYYMMDDHHMMSS';"
```

## Disaster Recovery

### Scenario 1: Migration Corrupted Data

1. **Stop all services**
```bash
systemctl stop corporate-intel-api
```

2. **Restore from last known good backup**
```bash
# Drop and recreate database
dropdb -h $DB_HOST -U $DB_USER $DB_NAME
createdb -h $DB_HOST -U $DB_USER $DB_NAME

# Restore backup
pg_restore -h $DB_HOST -U $DB_USER -d $DB_NAME -c backup_YYYYMMDD_HHMMSS.dump
```

3. **Verify restoration**
```bash
bash scripts/validate-migrations.sh
```

4. **Restart services**
```bash
systemctl start corporate-intel-api
```

### Scenario 2: Migration Locked Database

1. **Identify blocking queries**
```bash
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "
SELECT
    pid,
    usename,
    application_name,
    client_addr,
    query_start,
    state,
    query
FROM pg_stat_activity
WHERE state = 'active'
ORDER BY query_start;
"
```

2. **Terminate blocking connections**
```bash
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = current_database()
AND pid != pg_backend_pid()
AND state = 'active';
"
```

3. **Retry migration**

### Scenario 3: TimescaleDB Extension Issue

1. **Check extension version**
```bash
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT extname, extversion FROM pg_extension WHERE extname = 'timescaledb';"
```

2. **Update extension if needed**
```bash
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "ALTER EXTENSION timescaledb UPDATE;"
```

3. **Verify hypertables**
```bash
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT * FROM timescaledb_information.hypertables;"
```

## Common Issues

### Issue 1: Migration Takes Too Long

**Symptoms:**
- Migration hangs for extended period
- Database becomes unresponsive

**Solution:**
```bash
# Check long-running queries
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "
SELECT
    pid,
    now() - pg_stat_activity.query_start AS duration,
    state,
    query
FROM pg_stat_activity
WHERE state = 'active'
ORDER BY duration DESC;
"

# Consider running migration with statement timeout
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SET statement_timeout = '60s';"
```

### Issue 2: Foreign Key Constraint Violation

**Symptoms:**
- Migration fails with constraint violation error

**Solution:**
```bash
# Temporarily disable triggers
ALTER TABLE table_name DISABLE TRIGGER ALL;

# Run migration

# Re-enable triggers
ALTER TABLE table_name ENABLE TRIGGER ALL;

# Verify constraints
SELECT * FROM information_schema.table_constraints WHERE table_name = 'table_name';
```

### Issue 3: Out of Disk Space

**Symptoms:**
- Migration fails with "No space left on device"

**Solution:**
```bash
# Check disk usage
df -h

# Clean up old backups
find backups/ -name "*.dump" -mtime +30 -delete

# Vacuum database to reclaim space
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "VACUUM FULL;"
```

### Issue 4: Hypertable Conversion Fails

**Symptoms:**
- CREATE HYPERTABLE fails

**Solution:**
```bash
# Check if table already is a hypertable
SELECT * FROM timescaledb_information.hypertables WHERE hypertable_name = 'table_name';

# If exists, skip hypertable creation
# If not, ensure time column exists and has correct type
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'table_name' AND column_name = 'created_at';
```

## CI/CD Integration

### GitHub Actions Workflow

The `.github/workflows/test-migrations.yml` workflow automatically tests migrations on every push and pull request.

**Workflow Jobs:**
1. **validate-migrations**: Checks file naming, duplicates, syntax
2. **test-migrations-forward**: Tests applying all migrations
3. **test-migrations-rollback**: Tests rolling back migrations
4. **test-migrations-idempotency**: Tests running migrations twice
5. **test-production-readiness**: Checks for dangerous operations

### Running Locally

```bash
# Install act (GitHub Actions local runner)
brew install act  # macOS
# or
curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash

# Run workflow locally
act -W .github/workflows/test-migrations.yml
```

### Pre-Commit Hooks

Add to `.git/hooks/pre-commit`:
```bash
#!/bin/bash

# Run migration validation
bash scripts/validate-migrations.sh

if [ $? -ne 0 ]; then
    echo "Migration validation failed. Commit aborted."
    exit 1
fi
```

## Production Deployment Checklist

- [ ] All tests pass in CI/CD pipeline
- [ ] Migration tested on staging with production data snapshot
- [ ] Backup created and verified
- [ ] Rollback procedure tested and documented
- [ ] Maintenance window scheduled and communicated
- [ ] Database replication lag minimal (if applicable)
- [ ] Monitoring alerts configured
- [ ] Team on standby for deployment
- [ ] Post-deployment validation plan ready

## Monitoring Post-Migration

```bash
# Check database size
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT pg_size_pretty(pg_database_size(current_database()));"

# Monitor query performance
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "
SELECT
    query,
    calls,
    total_exec_time,
    mean_exec_time,
    max_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
"

# Check replication lag (if applicable)
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT pg_last_wal_receive_lsn(), pg_last_wal_replay_lsn();"
```

## Support and Resources

- **Documentation**: `/docs/database/`
- **Migration Files**: `/migrations/`
- **Test Files**: `/tests/migrations/`
- **Validation Scripts**: `/scripts/validate-migrations.sh`

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2024-01-01 | Initial migration testing framework |
