# Backup and Restore Test Procedures

## Overview

This document provides comprehensive procedures for testing backup and restore operations to ensure data recovery capabilities in production.

## Test Categories

### 1. Database Backup Testing
### 2. File System Backup Testing
### 3. Configuration Backup Testing
### 4. Full System Restore Testing
### 5. Point-in-Time Recovery Testing

---

## 1. Database Backup Testing

### 1.1 PostgreSQL Full Backup Test

**Objective**: Verify full database backup can be created and restored

**Prerequisites**:
- PostgreSQL database running
- Sufficient disk space for backup
- Backup user with appropriate permissions

**Procedure**:

```bash
# 1. Create full backup
pg_dump -U postgres -h localhost -d corporate_intel > backup_$(date +%Y%m%d_%H%M%S).sql

# 2. Verify backup file
ls -lh backup_*.sql
# Expected: File exists, size > 0

# 3. Check backup integrity
head -n 50 backup_*.sql
# Expected: Valid SQL header, version info

# 4. Create test restore database
createdb -U postgres test_restore

# 5. Restore to test database
psql -U postgres -d test_restore < backup_*.sql

# 6. Verify restoration
psql -U postgres -d test_restore -c "SELECT COUNT(*) FROM companies;"
psql -U postgres -d test_restore -c "SELECT COUNT(*) FROM financial_metrics;"

# 7. Cleanup test database
dropdb -U postgres test_restore
```

**Success Criteria**:
- Backup file created successfully
- Backup file size matches expected size
- Restore completes without errors
- Row counts match source database
- Foreign key constraints intact
- Indexes restored correctly

### 1.2 Incremental Backup Test

**Objective**: Verify incremental backups work correctly

**Procedure**:

```bash
# 1. Create base backup
pg_basebackup -U postgres -D /backups/base -Ft -z -P

# 2. Enable WAL archiving (in postgresql.conf)
# archive_mode = on
# archive_command = 'cp %p /backups/wal_archive/%f'

# 3. Make changes to database
psql -U postgres -d corporate_intel -c "INSERT INTO audit_log (message) VALUES ('Test backup');"

# 4. Force WAL switch
psql -U postgres -c "SELECT pg_switch_wal();"

# 5. Verify WAL files archived
ls -lh /backups/wal_archive/

# 6. Test PITR (Point-In-Time Recovery)
# Stop PostgreSQL
# Restore base backup
# Configure recovery.conf
# Start PostgreSQL and verify
```

**Success Criteria**:
- Base backup created successfully
- WAL files archived continuously
- Can recover to specific point in time
- No data loss within recovery window

---

## 2. File System Backup Testing

### 2.1 Application Files Backup

**Objective**: Verify application code and configuration backups

**Procedure**:

```bash
# 1. Create application backup
tar -czf app_backup_$(date +%Y%m%d_%H%M%S).tar.gz \
    /opt/corporate_intel/src \
    /opt/corporate_intel/config \
    /opt/corporate_intel/logs

# 2. Verify backup
tar -tzf app_backup_*.tar.gz | head -20

# 3. Test restore to temporary location
mkdir -p /tmp/restore_test
tar -xzf app_backup_*.tar.gz -C /tmp/restore_test

# 4. Verify files
diff -r /opt/corporate_intel/src /tmp/restore_test/opt/corporate_intel/src

# 5. Cleanup
rm -rf /tmp/restore_test
```

**Success Criteria**:
- All files included in backup
- No file corruption
- Directory structure preserved
- Permissions preserved

### 2.2 Static Assets Backup

**Objective**: Backup and restore static files, uploads, etc.

**Procedure**:

```bash
# 1. Create static files backup
rsync -av --delete /var/www/static/ /backups/static_$(date +%Y%m%d)/

# 2. Verify backup
du -sh /backups/static_*

# 3. Test restore
rsync -av /backups/static_$(date +%Y%m%d)/ /tmp/static_test/

# 4. Compare
diff -r /var/www/static/ /tmp/static_test/
```

---

## 3. Configuration Backup Testing

### 3.1 Environment Variables

**Objective**: Backup and restore environment configuration

**Procedure**:

```bash
# 1. Export environment variables
env | grep -E "POSTGRES|REDIS|SECRET" > env_backup_$(date +%Y%m%d).txt

# 2. Encrypt backup
gpg -c env_backup_*.txt

# 3. Test decryption
gpg -d env_backup_*.txt.gpg > env_restore.txt

# 4. Verify
diff env_backup_*.txt env_restore.txt
```

### 3.2 Docker Configuration

**Objective**: Backup Docker Compose and configuration files

**Procedure**:

```bash
# 1. Backup Docker configs
cp docker-compose.yml docker-compose_backup_$(date +%Y%m%d).yml
cp -r .docker .docker_backup_$(date +%Y%m%d)

# 2. Test restore
docker-compose -f docker-compose_backup_*.yml config
```

---

## 4. Full System Restore Testing

### 4.1 Complete System Recovery

**Objective**: Validate complete system can be restored from backups

**Prerequisites**:
- Clean test environment (separate from production)
- All backup files available
- Access credentials

**Procedure**:

```bash
#!/bin/bash
# Full system restore test script

set -e

echo "=== Starting Full System Restore Test ==="

# 1. Restore Database
echo "Restoring database..."
dropdb -U postgres --if-exists corporate_intel_test
createdb -U postgres corporate_intel_test
psql -U postgres -d corporate_intel_test < latest_backup.sql

# 2. Restore Application Files
echo "Restoring application files..."
tar -xzf app_backup_latest.tar.gz -C /tmp/restore_test/

# 3. Restore Configuration
echo "Restoring configuration..."
cp env_backup_latest.txt /tmp/restore_test/.env

# 4. Start Services
echo "Starting services..."
cd /tmp/restore_test
docker-compose up -d

# 5. Wait for services to be ready
echo "Waiting for services..."
sleep 30

# 6. Run smoke tests
echo "Running smoke tests..."
pytest tests/production/test_critical_path.py -v

# 7. Verify data integrity
echo "Verifying data integrity..."
python -c "
from src.database.connection import get_db
db = get_db()
companies = db.query('SELECT COUNT(*) FROM companies').scalar()
print(f'Companies in restored database: {companies}')
assert companies > 0, 'No companies found'
"

echo "=== Full System Restore Test Complete ==="
```

**Success Criteria**:
- Database restored with all data
- Application starts successfully
- All services operational
- Smoke tests pass
- Data integrity verified
- No configuration errors

**Duration**: Approximately 30-60 minutes

---

## 5. Point-in-Time Recovery Testing

### 5.1 PITR Procedure

**Objective**: Restore database to specific point in time

**Scenario**: Recover from accidental data deletion at 14:30

**Procedure**:

```bash
# 1. Identify recovery target time
RECOVERY_TIME="2025-10-25 14:29:00"

# 2. Stop PostgreSQL
sudo systemctl stop postgresql

# 3. Backup current data directory
mv /var/lib/postgresql/data /var/lib/postgresql/data.old

# 4. Restore base backup
tar -xzf base_backup.tar.gz -C /var/lib/postgresql/data

# 5. Create recovery.conf
cat > /var/lib/postgresql/data/recovery.conf << EOF
restore_command = 'cp /backups/wal_archive/%f %p'
recovery_target_time = '$RECOVERY_TIME'
recovery_target_action = 'promote'
EOF

# 6. Start PostgreSQL in recovery mode
sudo systemctl start postgresql

# 7. Monitor recovery
tail -f /var/log/postgresql/postgresql.log

# 8. Verify recovery completed
psql -U postgres -c "SELECT pg_is_in_recovery();"
# Expected: false (recovery complete)

# 9. Verify data at recovery point
psql -U postgres -d corporate_intel -c "SELECT MAX(created_at) FROM companies;"
# Expected: Timestamp before recovery target
```

**Success Criteria**:
- Database recovers to exact point in time
- Data after recovery point is not present
- Data before recovery point is intact
- Database is in consistent state

---

## Backup Test Schedule

### Daily Tests
- Verify automated backups completed
- Check backup file sizes
- Verify backup location accessibility

### Weekly Tests
- Restore test database from backup
- Verify data integrity
- Test backup encryption/decryption

### Monthly Tests
- Full system restore to test environment
- Point-in-time recovery drill
- Backup retention verification

### Quarterly Tests
- Complete disaster recovery drill
- Cross-region backup restoration
- Backup performance optimization review

---

## Automated Backup Verification

### Backup Verification Script

```python
#!/usr/bin/env python3
"""Automated backup verification script."""

import os
import subprocess
import sys
from datetime import datetime, timedelta
import psycopg2

def verify_database_backup():
    """Verify latest database backup."""
    backup_dir = "/backups/database"
    latest_backup = max(
        [os.path.join(backup_dir, f) for f in os.listdir(backup_dir)],
        key=os.path.getctime
    )

    # Check age
    backup_age = datetime.now() - datetime.fromtimestamp(os.path.getctime(latest_backup))
    if backup_age > timedelta(hours=24):
        print(f"❌ Backup is {backup_age} old (should be < 24h)")
        return False

    # Check size
    backup_size = os.path.getsize(latest_backup)
    if backup_size < 1024 * 1024:  # < 1MB
        print(f"❌ Backup size {backup_size} bytes is too small")
        return False

    print(f"✅ Database backup OK: {latest_backup}")
    print(f"   Age: {backup_age}")
    print(f"   Size: {backup_size / (1024*1024):.2f} MB")
    return True

def verify_backup_restoration():
    """Test backup can be restored."""
    try:
        # Create test database
        subprocess.run(
            ["createdb", "-U", "postgres", "backup_verify_test"],
            check=True
        )

        # Restore backup
        latest_backup = "/backups/database/latest.sql"
        subprocess.run(
            ["psql", "-U", "postgres", "-d", "backup_verify_test", "-f", latest_backup],
            check=True,
            capture_output=True
        )

        # Verify data
        conn = psycopg2.connect(
            dbname="backup_verify_test",
            user="postgres",
            host="localhost"
        )
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM companies")
        count = cursor.fetchone()[0]
        conn.close()

        # Cleanup
        subprocess.run(["dropdb", "-U", "postgres", "backup_verify_test"])

        if count > 0:
            print(f"✅ Backup restoration verified ({count} companies)")
            return True
        else:
            print("❌ Backup restoration failed (no data)")
            return False

    except Exception as e:
        print(f"❌ Backup restoration failed: {e}")
        return False

if __name__ == "__main__":
    print("=== Backup Verification ===")

    db_ok = verify_database_backup()
    restore_ok = verify_backup_restoration()

    if db_ok and restore_ok:
        print("\n✅ All backup verifications passed")
        sys.exit(0)
    else:
        print("\n❌ Backup verification failed")
        sys.exit(1)
```

---

## Monitoring and Alerting

### Backup Monitoring Checklist

- [ ] Automated backup completion notifications
- [ ] Backup failure alerts (email/Slack)
- [ ] Backup size trend monitoring
- [ ] Storage capacity alerts
- [ ] Backup age monitoring
- [ ] Restoration test results tracking

### Grafana Dashboard Metrics

```yaml
backup_metrics:
  - backup_success_rate
  - backup_duration_seconds
  - backup_size_bytes
  - last_successful_backup_timestamp
  - restore_test_success_rate
  - restore_duration_seconds
```

---

## Troubleshooting

### Common Issues

**Issue**: Backup file is too large
- **Solution**: Use compression (`pg_dump -Fc`), incremental backups

**Issue**: Restore takes too long
- **Solution**: Use parallel restore (`pg_restore -j 4`), faster storage

**Issue**: Backup fails with "disk full"
- **Solution**: Clean old backups, increase storage, use compression

**Issue**: Point-in-time recovery fails
- **Solution**: Verify WAL archiving is working, check recovery.conf

---

## Compliance and Audit

### Backup Testing Records

Maintain records of:
- Backup test execution dates
- Test results (pass/fail)
- Issues encountered
- Time to restore
- Data integrity verification results

### Retention Policy

- Daily backups: Retain 7 days
- Weekly backups: Retain 4 weeks
- Monthly backups: Retain 12 months
- Yearly backups: Retain 7 years (compliance)

---

## Contact Information

**Backup Administrator**: backup-admin@example.com
**On-Call DBA**: oncall-dba@example.com
**Incident Response**: incident@example.com

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-10-25 | QA Team | Initial version |
