# Disaster Recovery Plan
## Corporate Intelligence Platform

**Version:** 1.0
**Last Updated:** 2025-10-03
**Owner:** Infrastructure Team

---

## Table of Contents
1. [Overview](#overview)
2. [Recovery Objectives](#recovery-objectives)
3. [Backup Strategy](#backup-strategy)
4. [Recovery Procedures](#recovery-procedures)
5. [Failover Procedures](#failover-procedures)
6. [Communication Plan](#communication-plan)
7. [Testing & Maintenance](#testing--maintenance)

---

## Overview

This document outlines the disaster recovery (DR) procedures for the Corporate Intelligence Platform. It provides step-by-step instructions for recovering from various failure scenarios to ensure business continuity.

### Disaster Scenarios Covered
- Complete database failure
- Application server failure
- Data corruption
- Infrastructure compromise
- Regional outages
- Accidental data deletion

### Key Contacts

| Role | Primary | Secondary | Contact |
|------|---------|-----------|---------|
| DR Coordinator | [Name] | [Name] | [Phone/Email] |
| Database Admin | [Name] | [Name] | [Phone/Email] |
| DevOps Lead | [Name] | [Name] | [Phone/Email] |
| Security Officer | [Name] | [Name] | [Phone/Email] |

---

## Recovery Objectives

### Recovery Time Objective (RTO)
- **Critical Systems**: 4 hours
- **Database**: 2 hours
- **API Services**: 1 hour
- **Analytics/Reporting**: 8 hours

### Recovery Point Objective (RPO)
- **Production Database**: 1 hour (maximum acceptable data loss)
- **File Storage**: 24 hours
- **Analytics Data**: 24 hours

### Service Level Agreements
- 99.9% uptime target (8.76 hours downtime/year allowed)
- Critical bug response: < 1 hour
- Major incident response: < 30 minutes

---

## Backup Strategy

### Automated Backups

#### 1. Database Backups (PostgreSQL)

**Daily Full Backups**
```bash
# Automated via cron: 2 AM UTC daily
0 2 * * * /opt/corporate-intel/scripts/backup.sh daily
```

**Hourly Incremental Backups**
```bash
# Automated via cron: Every hour
0 * * * * /opt/corporate-intel/scripts/backup.sh incremental
```

**Retention Policy**
- Daily backups: 7 days
- Weekly backups: 30 days
- Monthly backups: 365 days

#### 2. Docker Volume Backups

**Volumes Backed Up**
- `corporate-intel-postgres-data`
- `corporate-intel-redis-data`
- `corporate-intel-minio-data`

**Backup Schedule**
```bash
# Daily at 3 AM UTC
0 3 * * * /opt/corporate-intel/scripts/backup-volumes.sh
```

#### 3. Configuration Backups

**What's Backed Up**
- Environment files (encrypted)
- Docker compose files
- Nginx configurations
- SSL certificates
- Application configurations

**Backup Location**
```
/var/backups/corporate-intel/
├── daily/
├── weekly/
├── monthly/
└── config/
```

### Backup Verification

**Automated Testing**
```bash
# Weekly backup restoration test
0 4 * * 0 /opt/corporate-intel/scripts/test-backup-restore.sh
```

**Manual Verification Checklist**
- [ ] Backup files are accessible
- [ ] Backup size is reasonable (not empty)
- [ ] Backup encryption is working
- [ ] Restore test completes successfully
- [ ] Data integrity checks pass

---

## Recovery Procedures

### Scenario 1: Database Failure

**Symptoms:**
- Database connection errors
- Data inconsistencies
- Corruption warnings in logs

**Recovery Steps:**

1. **Assess Damage**
   ```bash
   # Check PostgreSQL status
   docker-compose ps postgres
   docker-compose logs postgres --tail=100

   # Attempt to connect
   docker-compose exec postgres psql -U intel_user -d corporate_intel
   ```

2. **Stop Application Services**
   ```bash
   docker-compose stop api prefect
   ```

3. **Backup Current State (if possible)**
   ```bash
   # Even if corrupted, save current state for forensics
   docker-compose exec postgres pg_dumpall -U postgres > /tmp/emergency-backup-$(date +%Y%m%d_%H%M%S).sql
   ```

4. **Restore from Backup**
   ```bash
   # Stop database
   docker-compose stop postgres

   # Remove corrupted volume
   docker volume rm corporate-intel-postgres-data

   # Restore from latest backup
   /opt/corporate-intel/scripts/restore.sh database --latest

   # Or specific backup
   /opt/corporate-intel/scripts/restore.sh database --file /var/backups/corporate-intel/daily/20250103_020000/postgres-backup.sql.gz
   ```

5. **Verify Database Integrity**
   ```bash
   # Start database
   docker-compose up -d postgres

   # Wait for database to be ready
   sleep 10

   # Check database
   docker-compose exec postgres psql -U intel_user -d corporate_intel -c "\dt"
   docker-compose exec postgres psql -U intel_user -d corporate_intel -c "SELECT COUNT(*) FROM companies;"
   ```

6. **Restart Services**
   ```bash
   docker-compose up -d
   ```

7. **Validate Application**
   ```bash
   # Run health checks
   curl http://localhost:8000/health

   # Check API functionality
   curl http://localhost:8000/api/v1/companies?limit=1
   ```

**Estimated Recovery Time:** 30-60 minutes

---

### Scenario 2: Complete System Failure

**Symptoms:**
- Server is unreachable
- Hardware failure
- Complete infrastructure loss

**Recovery Steps:**

1. **Provision New Infrastructure**
   ```bash
   # Using infrastructure as code (Terraform/CloudFormation)
   terraform apply -var="environment=production-recovery"
   ```

2. **Install Prerequisites**
   ```bash
   # Install Docker and Docker Compose
   curl -fsSL https://get.docker.com | sh
   sudo apt install docker-compose-plugin

   # Install other tools
   sudo apt update && sudo apt install -y git postgresql-client redis-tools
   ```

3. **Clone Repository**
   ```bash
   git clone https://github.com/your-org/corporate-intel.git
   cd corporate-intel
   git checkout production  # or specific tag
   ```

4. **Restore Configuration**
   ```bash
   # Restore from config backup
   scp backup-server:/backups/corporate-intel/config/latest/.env.production .
   scp backup-server:/backups/corporate-intel/config/latest/docker-compose.yml .

   # Or restore from secrets manager
   python config/vault_integration.py load --path production
   ```

5. **Restore Data**
   ```bash
   # Create volumes
   docker volume create corporate-intel-postgres-data
   docker volume create corporate-intel-redis-data
   docker volume create corporate-intel-minio-data

   # Restore database
   ./scripts/restore.sh database --latest

   # Restore MinIO data
   ./scripts/restore.sh minio --latest
   ```

6. **Start Services**
   ```bash
   docker-compose up -d
   ```

7. **Verify Recovery**
   ```bash
   # Run validation script
   ./scripts/validate-production.sh

   # Check all services
   docker-compose ps
   docker-compose logs --tail=50
   ```

8. **Update DNS**
   ```bash
   # Point DNS to new server
   # Update A record for corporate-intel.example.com
   ```

9. **Monitor Closely**
   ```bash
   # Watch logs for 30 minutes
   docker-compose logs -f

   # Monitor metrics in Grafana
   # Check error rates, response times
   ```

**Estimated Recovery Time:** 2-4 hours

---

### Scenario 3: Data Corruption or Accidental Deletion

**Symptoms:**
- Reports of missing data
- Inconsistent query results
- User reports data anomalies

**Recovery Steps:**

1. **Stop All Write Operations**
   ```bash
   # Scale down API to prevent further writes
   docker-compose scale api=0
   ```

2. **Assess Scope**
   ```bash
   # Identify affected data
   # Check database logs
   docker-compose logs postgres | grep -i "delete\|drop\|truncate"

   # Compare with backup
   # List recent backups
   ls -lh /var/backups/corporate-intel/daily/ | tail -5
   ```

3. **Point-in-Time Recovery**
   ```bash
   # Restore to specific timestamp (before corruption)
   # This uses PostgreSQL WAL archiving

   # Stop database
   docker-compose stop postgres

   # Restore base backup
   ./scripts/restore.sh database --file /var/backups/daily/20250103_020000/postgres-backup.sql.gz

   # Apply WAL logs up to corruption point
   # (Requires WAL archiving to be configured)
   docker-compose exec postgres pg_receivewal -D /var/lib/postgresql/data/pg_wal --until='2025-01-03 14:30:00'
   ```

4. **Selective Data Recovery**
   ```bash
   # If only specific tables affected, restore selectively

   # Extract specific table from backup
   pg_restore -t companies /var/backups/latest/postgres-backup.dump > companies-restore.sql

   # Review and apply
   psql -U intel_user -d corporate_intel -f companies-restore.sql
   ```

5. **Verify Data Integrity**
   ```bash
   # Run data validation queries
   # Check row counts
   # Verify critical data exists
   ```

6. **Resume Operations**
   ```bash
   docker-compose up -d
   ```

**Estimated Recovery Time:** 1-3 hours

---

## Failover Procedures

### Active-Passive Failover

**Prerequisites:**
- Secondary server configured and synced
- Database replication enabled
- Load balancer configured

**Failover Steps:**

1. **Detect Failure**
   ```bash
   # Automated health check failure or manual detection
   curl -f http://primary-server/health || FAILOVER_NEEDED=true
   ```

2. **Promote Secondary Database**
   ```bash
   # On secondary server
   docker-compose exec postgres pg_ctl promote
   ```

3. **Update DNS/Load Balancer**
   ```bash
   # Point traffic to secondary server
   # Update load balancer configuration
   ```

4. **Verify Secondary**
   ```bash
   # Check all services on secondary
   curl http://secondary-server/health
   ```

5. **Monitor Traffic**
   ```bash
   # Watch for errors
   # Monitor response times
   ```

**Estimated Failover Time:** 5-10 minutes

---

## Communication Plan

### Incident Declaration

**When to Declare:**
- RTO/RPO at risk
- Customer-facing functionality impaired
- Data integrity compromised
- Security breach suspected

### Notification Workflow

1. **Immediate** (< 5 minutes)
   - Notify on-call engineer via PagerDuty
   - Post in #incidents Slack channel

2. **Within 15 minutes**
   - Notify DR Coordinator
   - Create incident ticket
   - Start incident bridge call

3. **Within 30 minutes**
   - Notify executive team
   - Prepare customer communication
   - Document actions taken

### Status Updates

**Internal:**
- Every 30 minutes during active incident
- Posted to #incidents channel
- Include: current status, ETA, actions taken

**External (Customers):**
- Initial notice within 1 hour
- Updates every 2 hours
- Post-incident report within 48 hours

### Communication Templates

**Initial Incident Notice:**
```
Subject: [Service Alert] Corporate Intelligence Platform - [Brief Description]

We are currently experiencing [issue description].
Our team is actively working on resolution.

Impact: [description]
ETA: [estimate or "investigating"]

We will provide updates every [frequency].
```

**Resolution Notice:**
```
Subject: [Resolved] Corporate Intelligence Platform Incident

The issue affecting [service] has been resolved.

Incident Summary:
- Start: [timestamp]
- End: [timestamp]
- Duration: [duration]
- Impact: [description]
- Root Cause: [brief explanation]

A detailed post-incident report will be available within 48 hours.
```

---

## Testing & Maintenance

### Recovery Testing Schedule

| Test Type | Frequency | Last Executed | Next Due |
|-----------|-----------|---------------|----------|
| Database Restore | Weekly | - | - |
| Full System Recovery | Quarterly | - | - |
| Failover Test | Monthly | - | - |
| Backup Integrity | Daily (automated) | - | - |

### Test Procedures

**Quarterly Full DR Test:**
1. Schedule during maintenance window
2. Provision test environment
3. Restore from production backups
4. Validate all functionality
5. Document any issues
6. Update DR plan as needed

**Post-Test Actions:**
- [ ] Document test results
- [ ] Update RTO/RPO estimates
- [ ] Fix any issues identified
- [ ] Train team on changes
- [ ] Review and improve procedures

### Plan Maintenance

**Review Triggers:**
- After any incident
- Quarterly scheduled review
- After infrastructure changes
- After team changes

**Review Checklist:**
- [ ] Verify contact information
- [ ] Update recovery procedures
- [ ] Test backup restoration
- [ ] Validate RTO/RPO targets
- [ ] Update documentation
- [ ] Train new team members

---

## Appendix

### A. Backup File Locations

```
Production Backups:
/var/backups/corporate-intel/
  ├── daily/[YYYYMMDD_HHMMSS]/
  │   ├── postgres-backup.sql.gz
  │   ├── postgres-backup.sql.gz.sha256
  │   ├── redis-snapshot.rdb.gz
  │   └── minio-backup.tar.gz
  ├── weekly/
  └── monthly/

Offsite Backups:
s3://corporate-intel-backups/[environment]/[YYYY-MM-DD]/

Config Backups:
/var/backups/corporate-intel/config/
  ├── .env.production.enc
  ├── docker-compose.yml
  ├── nginx.conf
  └── ssl/
```

### B. Critical Dependencies

```yaml
External Services:
  - AWS S3 (backup storage)
  - HashiCorp Vault (secrets management)
  - PagerDuty (incident alerting)
  - StatusPage (customer communication)
  - CloudFlare (DNS, CDN)

Internal Dependencies:
  - PostgreSQL 16
  - Redis 7
  - MinIO
  - Nginx
```

### C. Recovery Scripts Reference

```bash
# Full backup
./scripts/backup.sh [daily|weekly|monthly]

# Restore database
./scripts/restore.sh database --file [path] [--timestamp YYYY-MM-DD_HH:MM:SS]

# Restore volumes
./scripts/restore.sh volumes --latest

# Validate environment
./scripts/validate-production.sh

# Test backup integrity
./scripts/test-backup-restore.sh [backup-file]
```

### D. Change Log

| Date | Version | Changes | Author |
|------|---------|---------|--------|
| 2025-10-03 | 1.0 | Initial DR plan | Infrastructure Team |

---

**Document Classification:** CONFIDENTIAL
**Review Frequency:** Quarterly
**Next Review Date:** 2026-01-03
