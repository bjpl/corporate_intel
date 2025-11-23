# Backup and Restoration Procedures

## Table of Contents

- [Overview](#overview)
- [Backup Strategy](#backup-strategy)
- [PostgreSQL Database Backups](#postgresql-database-backups)
- [MinIO Object Storage Backups](#minio-object-storage-backups)
- [Backup Scheduling](#backup-scheduling)
- [Restoration Procedures](#restoration-procedures)
- [Disaster Recovery](#disaster-recovery)
- [Monitoring and Verification](#monitoring-and-verification)
- [Troubleshooting](#troubleshooting)

## Overview

This document describes the automated backup and restoration procedures for the Corporate Intel production environment.

### Recovery Objectives

- **RTO (Recovery Time Objective)**: < 1 hour
- **RPO (Recovery Point Objective)**: < 24 hours

### Backup Components

1. **PostgreSQL Database**: Full backups with WAL archiving for point-in-time recovery
2. **MinIO Object Storage**: Snapshot backups and bucket replication
3. **Configuration Files**: System and application configuration backups

## Backup Strategy

### Retention Policy

| Backup Type | Frequency | Retention Period | Storage Location |
|-------------|-----------|------------------|------------------|
| Daily Full  | Every day at 2:00 AM | 7 days | Local + S3 |
| Weekly Full | Sundays at 3:00 AM | 28 days (4 weeks) | Local + S3 |
| Monthly Full | 1st of month at 4:00 AM | 365 days (12 months) | Local + S3 |
| WAL Archives | Continuous | 7 days local, 30 days S3 | Local + S3 |
| MinIO Snapshots | Daily at 1:00 AM | 7 days | Local + S3 |

### Storage Locations

- **Primary**: Local filesystem (`/var/backups/`)
- **Secondary**: S3-compatible object storage (off-site)
- **Archive**: Long-term archival storage (S3 Glacier/Deep Archive)

## PostgreSQL Database Backups

### Backup Script

Location: `/opt/corporate-intel/scripts/backup/postgres-backup.sh`

### Configuration

Set the following environment variables in `/etc/default/corporate-intel-backup`:

```bash
# Database connection
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=corporate_intel
export DB_USER=postgres
export PGPASSWORD=your_secure_password

# Backup directories
export BACKUP_ROOT=/var/backups/postgres

# Encryption (GPG)
export ENCRYPT_BACKUPS=true
export GPG_RECIPIENT=backup@corporate-intel.local

# Remote storage (S3)
export REMOTE_STORAGE=true
export S3_BUCKET=corporate-intel-backups
export S3_ENDPOINT=https://s3.amazonaws.com
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key

# Alerting
export SLACK_WEBHOOK=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
export EMAIL_ALERTS=ops@corporate-intel.local
```

### Manual Backup Execution

```bash
# Daily backup
sudo -u postgres /opt/corporate-intel/scripts/backup/postgres-backup.sh daily

# Weekly backup
sudo -u postgres /opt/corporate-intel/scripts/backup/postgres-backup.sh weekly

# Monthly backup
sudo -u postgres /opt/corporate-intel/scripts/backup/postgres-backup.sh monthly
```

### Backup File Structure

```
/var/backups/postgres/
├── daily/
│   ├── corporate_intel_daily_20251017-020000.sql.gz.gpg
│   ├── corporate_intel_daily_20251017-020000.sql.gz.gpg.metadata.json
│   └── globals_20251017-020000.sql.gz.gpg
├── weekly/
│   └── corporate_intel_weekly_20251013-030000.sql.gz.gpg
├── monthly/
│   └── corporate_intel_monthly_20251001-040000.sql.gz.gpg
├── wal-archive/
│   └── 000000010000000000000001
└── logs/
    └── backup-20251017-020000.log
```

### WAL Archiving Configuration

Add to `postgresql.conf`:

```conf
# WAL archiving for point-in-time recovery
wal_level = replica
archive_mode = on
archive_command = '/opt/corporate-intel/scripts/backup/postgres-backup.sh archive-wal %p %f'
archive_timeout = 3600  # Archive every hour
```

## MinIO Object Storage Backups

### Backup Script

Location: `/opt/corporate-intel/scripts/backup/minio-backup.sh`

### Configuration

```bash
# Source MinIO
export MINIO_SOURCE_ENDPOINT=http://localhost:9000
export MINIO_SOURCE_ACCESS_KEY=minioadmin
export MINIO_SOURCE_SECRET_KEY=minioadmin

# Backup MinIO (optional separate instance)
export MINIO_BACKUP_ENDPOINT=http://backup-minio:9000
export MINIO_BACKUP_ACCESS_KEY=minioadmin
export MINIO_BACKUP_SECRET_KEY=minioadmin

# Buckets to backup
export BUCKETS_TO_BACKUP=company-data,embeddings,user-uploads

# Backup directory
export BACKUP_ROOT=/var/backups/minio
```

### Manual Backup Execution

```bash
# Create snapshot backups
/opt/corporate-intel/scripts/backup/minio-backup.sh backup

# Setup bucket replication
/opt/corporate-intel/scripts/backup/minio-backup.sh replicate

# Verify backup sync
/opt/corporate-intel/scripts/backup/minio-backup.sh verify
```

## Backup Scheduling

### Crontab Installation

```bash
# Copy scripts
sudo cp scripts/backup/*.sh /opt/corporate-intel/scripts/backup/
sudo chmod +x /opt/corporate-intel/scripts/backup/*.sh

# Install crontab
sudo crontab -u postgres config/production/backups/crontab

# Verify installation
sudo crontab -u postgres -l
```

### Schedule Overview

```
2:00 AM - PostgreSQL daily backup
1:00 AM - MinIO snapshot backup
Every 6 hours - Backup verification
Every hour - Health monitoring
Sundays 3:00 AM - PostgreSQL weekly backup
1st of month 4:00 AM - PostgreSQL monthly backup
```

## Restoration Procedures

### Full Database Restoration

Location: `/opt/corporate-intel/scripts/backup/restore-database.sh`

#### Step 1: List Available Backups

```bash
/opt/corporate-intel/scripts/backup/restore-database.sh --list
```

#### Step 2: Verify Backup (Test Restore)

```bash
# Test restore to temporary database
/opt/corporate-intel/scripts/backup/restore-database.sh \
  /var/backups/postgres/daily/corporate_intel_daily_20251017-020000.sql.gz.gpg \
  --verify-only
```

#### Step 3: Perform Restoration

```bash
# Full restore (will prompt for confirmation)
/opt/corporate-intel/scripts/backup/restore-database.sh \
  /var/backups/postgres/daily/corporate_intel_daily_20251017-020000.sql.gz.gpg
```

### Point-In-Time Recovery (PITR)

For recovering to a specific timestamp:

```bash
/opt/corporate-intel/scripts/backup/restore-database.sh \
  /var/backups/postgres/daily/corporate_intel_daily_20251017-020000.sql.gz.gpg \
  --pitr "2025-10-17 14:30:00"
```

**Note**: PITR requires WAL archives and PostgreSQL data directory access. See script output for detailed procedures.

### MinIO Object Restoration

#### Restore from Snapshot

```bash
# Extract snapshot
cd /var/backups/minio/snapshots
tar -xzf company-data_20251017-010000.tar.gz

# Copy to MinIO using mc
mc mirror company-data_20251017-010000/ source-minio/company-data/
```

#### Restore from Replication

If you have replication configured:

```bash
# Sync from backup MinIO to source MinIO
mc mirror backup-minio/company-data/ source-minio/company-data/
```

## Disaster Recovery

### Complete System Recovery

In case of total system failure:

#### 1. Prepare New Environment

```bash
# Deploy new infrastructure (EC2, RDS, etc.)
# Install PostgreSQL and MinIO
# Configure network and security groups
```

#### 2. Restore Database

```bash
# Download latest backup from S3
aws s3 cp s3://corporate-intel-backups/daily/corporate_intel_daily_20251017-020000.sql.gz.gpg /tmp/

# Restore database
/opt/corporate-intel/scripts/backup/restore-database.sh /tmp/corporate_intel_daily_20251017-020000.sql.gz.gpg
```

#### 3. Restore MinIO Data

```bash
# Download MinIO snapshot from S3
aws s3 cp s3://corporate-intel-backups/minio-snapshots/company-data_20251017-010000.tar.gz /tmp/

# Extract and restore
tar -xzf /tmp/company-data_20251017-010000.tar.gz -C /tmp/
mc mirror /tmp/company-data_20251017-010000/ new-minio/company-data/
```

#### 4. Verify System

```bash
# Run verification script
/opt/corporate-intel/scripts/backup/verify-backups.sh --all

# Test application connectivity
curl http://localhost:8000/api/health
```

### Disaster Recovery Runbook

**Target**: RTO < 1 hour

| Step | Action | Estimated Time | Responsible |
|------|--------|----------------|-------------|
| 1 | Assess damage and declare incident | 5 min | On-call Engineer |
| 2 | Spin up new infrastructure | 10 min | DevOps Lead |
| 3 | Download latest backups from S3 | 5 min | DevOps Engineer |
| 4 | Restore PostgreSQL database | 15 min | Database Admin |
| 5 | Restore MinIO object storage | 10 min | DevOps Engineer |
| 6 | Restore configuration files | 5 min | DevOps Engineer |
| 7 | Verify data integrity | 5 min | QA Engineer |
| 8 | Update DNS and routing | 5 min | Network Admin |
| 9 | Test application functionality | 5 min | QA Engineer |
| 10 | Communicate resolution | 5 min | Incident Commander |
| **Total** | | **70 min** | |

## Monitoring and Verification

### Backup Verification Script

Location: `/opt/corporate-intel/scripts/backup/verify-backups.sh`

```bash
# Verify latest backups
/opt/corporate-intel/scripts/backup/verify-backups.sh --latest

# Verify all backups
/opt/corporate-intel/scripts/backup/verify-backups.sh --all

# Verify specific backup
/opt/corporate-intel/scripts/backup/verify-backups.sh --backup-file /path/to/backup.sql.gz.gpg
```

### Backup Monitoring Script

Location: `/opt/corporate-intel/scripts/backup/monitor-backups.sh`

Runs hourly via cron and checks:

- Backup age (alert if > 24 hours)
- Backup size (alert if suspiciously small or large)
- Disk usage (alert at 80% and 90%)
- Backup success rate (alert if < 95%)
- Remote storage sync status

### Metrics and Dashboards

Backup metrics are stored in `/var/backups/postgres/metrics/` as JSON:

```json
{
  "timestamp": "2025-10-17T02:00:00Z",
  "metrics": {
    "last_backup_age_hours": 2,
    "last_backup_size_mb": 1250,
    "disk_usage_percent": 45,
    "success_rate_percent": 100.0,
    "daily_backup_count": 7,
    "weekly_backup_count": 4,
    "monthly_backup_count": 12
  }
}
```

### Alerting Channels

1. **Slack**: Real-time notifications to `#ops-alerts`
2. **Email**: Alerts sent to `ops@corporate-intel.local`
3. **PagerDuty**: Critical alerts trigger on-call engineer pages

## Troubleshooting

### Common Issues

#### Backup Failed: Disk Full

```bash
# Check disk usage
df -h /var/backups/

# Cleanup old backups manually
find /var/backups/postgres/daily -name "*.sql.*" -mtime +7 -delete

# Increase retention settings or add more storage
```

#### Backup Failed: Database Connection Error

```bash
# Test database connection
psql -h localhost -U postgres -d corporate_intel -c "SELECT 1"

# Check PostgreSQL is running
systemctl status postgresql

# Verify credentials in /etc/default/corporate-intel-backup
```

#### Backup Encryption Failed

```bash
# Check GPG key exists
gpg --list-keys backup@corporate-intel.local

# Generate new key if needed
gpg --gen-key

# Import key on restore server
gpg --import backup-private-key.asc
```

#### Restore Failed: Checksum Mismatch

```bash
# Re-download backup from S3
aws s3 cp s3://corporate-intel-backups/daily/backup.sql.gz.gpg /var/backups/postgres/daily/

# Verify file integrity
sha256sum /var/backups/postgres/daily/backup.sql.gz.gpg

# Compare with metadata
cat /var/backups/postgres/daily/backup.sql.gz.gpg.metadata.json
```

#### S3 Upload Failed

```bash
# Test S3 connectivity
aws s3 ls s3://corporate-intel-backups/ --endpoint-url https://s3.amazonaws.com

# Verify credentials
aws configure list

# Check network connectivity
curl -I https://s3.amazonaws.com
```

### Support Contacts

- **DevOps Team**: ops@corporate-intel.local
- **On-Call Engineer**: +1-555-0123 (PagerDuty)
- **Database Admin**: dba@corporate-intel.local
- **Slack Channel**: #ops-alerts

### Useful Commands

```bash
# Check backup logs
tail -f /var/backups/postgres/logs/backup-*.log

# Monitor cron jobs
tail -f /var/log/cron

# Check backup disk usage
du -sh /var/backups/postgres/*

# List recent backups
ls -lht /var/backups/postgres/daily/ | head -10

# Test backup file integrity
gzip -t backup.sql.gz

# Decrypt backup for inspection
gpg --decrypt backup.sql.gz.gpg | gunzip | head -100
```

## Appendix

### Backup Script Locations

- PostgreSQL Backup: `/opt/corporate-intel/scripts/backup/postgres-backup.sh`
- MinIO Backup: `/opt/corporate-intel/scripts/backup/minio-backup.sh`
- Restoration: `/opt/corporate-intel/scripts/backup/restore-database.sh`
- Verification: `/opt/corporate-intel/scripts/backup/verify-backups.sh`
- Monitoring: `/opt/corporate-intel/scripts/backup/monitor-backups.sh`

### Configuration Files

- Crontab: `/opt/corporate-intel/config/production/backups/crontab`
- Environment: `/etc/default/corporate-intel-backup`
- PostgreSQL Config: `/etc/postgresql/14/main/postgresql.conf`

### Documentation

- Backup Procedures: `/opt/corporate-intel/docs/deployment/backup-restore.md`
- Disaster Recovery Plan: `/opt/corporate-intel/docs/deployment/disaster-recovery.md`
- Runbooks: `/opt/corporate-intel/docs/runbooks/`

---

**Last Updated**: 2025-10-17
**Version**: 1.0
**Owner**: DevOps Team
