# Disaster Recovery Playbook

**Version:** 1.0.0
**Last Updated:** 2025-10-25
**24/7 Incident Response:** +1-XXX-XXX-XXXX

---

## Table of Contents

1. [Recovery Objectives](#1-recovery-objectives)
2. [Incident Classification](#2-incident-classification)
3. [Recovery Procedures](#3-recovery-procedures)
4. [Failover Procedures](#4-failover-procedures)
5. [Communication Protocols](#5-communication-protocols)
6. [Post-Incident Review](#6-post-incident-review)

---

## 1. Recovery Objectives

### RTO/RPO Targets

```yaml
Recovery Time Objectives (RTO):
  Critical System Failure: 4 hours
  Database Corruption: 2 hours
  Accidental Data Deletion: 30 minutes
  Regional Outage: 1 hour (failover to backup region)
  Security Breach: Immediate (isolation), 8 hours (full recovery)

Recovery Point Objectives (RPO):
  Database: 5 minutes (continuous WAL archiving)
  Application State: 15 minutes
  User Data: 0 minutes (real-time replication)
  Configuration: 1 hour
```

### Service Level Agreements

```yaml
Availability: 99.9% (43.2 minutes downtime/month)
Performance: p99 < 200ms
Error Rate: < 0.1%
Support Response: < 15 minutes (P0), < 1 hour (P1)
```

---

## 2. Incident Classification

### Severity Levels

#### P0 - Critical (Response: Immediate)
**Impact:** Complete service outage or data loss

**Examples:**
- Production API completely down
- Database unavailable
- Active data breach
- Ransomware attack
- Complete data center failure

**Response Team:**
- Incident Commander
- On-Call Engineer
- Database Administrator
- Security Lead
- CTO (if prolonged)

**Communication:**
- Customer notification: Immediate
- Status page: Update every 30 minutes
- Exec team: Immediate notification

---

#### P1 - High (Response: 1 hour)
**Impact:** Significant degradation, partial outage

**Examples:**
- API latency > 5 seconds
- Database read replicas down
- Single availability zone failure
- Critical feature unavailable
- Suspicious data access

**Response Team:**
- On-Call Engineer
- Database Administrator
- Optional: Security Lead

**Communication:**
- Customer notification: Within 2 hours
- Status page: Update every 1 hour
- Exec team: Within 1 hour

---

#### P2 - Medium (Response: 4 hours)
**Impact:** Minor degradation, workaround available

**Examples:**
- Non-critical API endpoint slow
- Monitoring service degraded
- Background job failures
- Minor security configuration issue

**Response Team:**
- On-Call Engineer

**Communication:**
- Internal only unless prolonged
- Status page: Optional

---

#### P3 - Low (Response: 24 hours)
**Impact:** No immediate customer impact

**Examples:**
- Non-urgent bug
- Documentation issue
- Low-priority feature request

**Response Team:**
- Standard ticket queue

**Communication:**
- None required

---

## 3. Recovery Procedures

### 3.1 Database Recovery

#### Scenario: Database Corruption

**Detection:**
```bash
# Symptom: Application errors, data inconsistency
# Alert: "PostgreSQL integrity check failed"
```

**Recovery Steps:**

**Step 1: Assess Damage (5 minutes)**
```bash
# SSH to database host
ssh postgres-primary

# Check database status
sudo -u postgres psql -c "\l"

# Check for corruption
sudo -u postgres pg_dump corporate_intel --schema-only > /dev/null
echo $?  # 0 = OK, non-zero = corruption

# Identify corrupted tables
sudo -u postgres psql corporate_intel -c "
SELECT schemaname, tablename
FROM pg_tables
WHERE schemaname = 'public';
" | while read schema table; do
    if ! sudo -u postgres pg_dump -t "$schema.$table" corporate_intel > /dev/null 2>&1; then
        echo "Corrupted: $schema.$table"
    fi
done
```

**Step 2: Stop Application (2 minutes)**
```bash
# Scale down API pods to prevent further corruption
kubectl scale deployment corporate-intel-api --replicas=0

# Or stop Docker containers
docker-compose -f docker-compose.production.yml stop api
```

**Step 3: Restore from Backup (30-60 minutes)**
```bash
# Find latest backup
aws s3 ls s3://corporate-intel-backups/daily/ --recursive | sort | tail -1

# Download backup
BACKUP_FILE="corporate_intel_20251025_020000.sql.gz"
aws s3 cp "s3://corporate-intel-backups/daily/$BACKUP_FILE" /tmp/

# Stop database (if completely corrupted)
docker-compose -f docker-compose.production.yml stop postgres

# Restore database
gunzip -c "/tmp/$BACKUP_FILE" | pg_restore \
    --host=localhost \
    --port=5432 \
    --username=postgres \
    --dbname=corporate_intel \
    --clean \
    --if-exists \
    --jobs=4 \
    --verbose

# Verify restore
psql -U postgres -d corporate_intel -c "\dt"
psql -U postgres -d corporate_intel -c "SELECT COUNT(*) FROM companies;"
```

**Step 4: Apply WAL Archives (5-10 minutes)**
```bash
# Replay WAL archives since backup
aws s3 sync s3://corporate-intel-backups/wal/ /var/lib/postgresql/wal/

# PostgreSQL will auto-apply WAL files on startup
docker-compose -f docker-compose.production.yml start postgres

# Monitor recovery progress
tail -f /var/log/postgresql/postgresql-*.log
```

**Step 5: Verify & Resume Service (5 minutes)**
```bash
# Verify data integrity
psql -U postgres -d corporate_intel -c "
SELECT 'companies' as table, COUNT(*) FROM companies
UNION ALL
SELECT 'filings', COUNT(*) FROM filings
UNION ALL
SELECT 'metrics', COUNT(*) FROM metrics;
"

# Compare with pre-corruption counts
# If data looks good, restart API
kubectl scale deployment corporate-intel-api --replicas=5

# Monitor errors
kubectl logs -f deployment/corporate-intel-api
```

**Total Time: 47-82 minutes (within RTO of 2 hours)**

---

#### Scenario: Accidental Data Deletion

**Detection:**
```sql
-- User reports: "All my companies were deleted!"
-- Alert: "Unexpected bulk DELETE detected"
```

**Recovery Steps:**

**Step 1: Stop Further Damage (1 minute)**
```bash
# Immediately revoke user permissions
psql -U postgres -d corporate_intel -c "
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM affected_user;
"

# Or block specific API key
redis-cli SADD blocked_api_keys "user_api_key_xyz"
```

**Step 2: Identify Deleted Data (5 minutes)**
```sql
-- Check audit logs
SELECT
    table_name,
    action,
    row_data,
    changed_fields,
    timestamp
FROM audit_log
WHERE action = 'DELETE'
  AND timestamp > NOW() - INTERVAL '1 hour'
ORDER BY timestamp DESC;
```

**Step 3: Restore from Point-in-Time (15 minutes)**
```bash
# Option A: WAL-based point-in-time recovery

# Stop database
docker-compose stop postgres

# Edit recovery.conf
cat > /var/lib/postgresql/data/recovery.conf <<EOF
restore_command = 'aws s3 cp s3://corporate-intel-backups/wal/%f %p'
recovery_target_time = '2025-10-25 14:30:00'  # Before deletion
recovery_target_action = 'promote'
EOF

# Start database (will recover to specified time)
docker-compose start postgres

# Monitor recovery
tail -f /var/log/postgresql/postgresql-*.log
```

**Step 4: Extract Deleted Data (10 minutes)**
```sql
-- Export deleted records
\copy (
    SELECT * FROM companies WHERE id IN (...)
) TO '/tmp/deleted_companies.csv' CSV HEADER;

-- Promote database to normal operation
SELECT pg_wal_replay_resume();
```

**Total Time: 31 minutes (within RTO of 30 minutes)**

---

### 3.2 Application Recovery

#### Scenario: API Service Down

**Detection:**
```bash
# Alert: "API health check failed"
# Symptom: All requests returning 502/503
```

**Recovery Steps:**

**Step 1: Triage (2 minutes)**
```bash
# Check pod status
kubectl get pods -l app=corporate-intel

# Check recent events
kubectl get events --sort-by='.lastTimestamp' | head -20

# Check logs
kubectl logs -l app=corporate-intel --tail=100
```

**Step 2: Quick Fixes (3 minutes)**
```bash
# Option A: Restart pods
kubectl rollout restart deployment/corporate-intel-api

# Option B: Scale up to force new pods
kubectl scale deployment corporate-intel-api --replicas=10
sleep 30
kubectl scale deployment corporate-intel-api --replicas=5

# Option C: Rollback to previous version
kubectl rollout undo deployment/corporate-intel-api

# Monitor recovery
kubectl rollout status deployment/corporate-intel-api
```

**Step 3: Verify Service (2 minutes)**
```bash
# Test health endpoint
curl -f https://api.corporate-intel.com/health

# Test critical endpoints
curl -f https://api.corporate-intel.com/api/v1/companies?limit=10

# Check metrics
curl -s https://api.corporate-intel.com/metrics | grep http_requests_total
```

**Total Time: 7 minutes (well within RTO of 4 hours)**

---

### 3.3 Infrastructure Recovery

#### Scenario: Complete Kubernetes Cluster Failure

**Detection:**
```bash
# Alert: "Kubernetes API unreachable"
# Symptom: kubectl commands failing
```

**Recovery Steps:**

**Step 1: Assess Cluster (5 minutes)**
```bash
# Check control plane
kubectl get nodes
kubectl get componentstatuses

# Check etcd health
kubectl exec -it etcd-0 -n kube-system -- etcdctl endpoint health

# Check cluster events
kubectl get events -A --sort-by='.lastTimestamp'
```

**Step 2: Activate Backup Cluster (30 minutes)**
```bash
# Switch to backup cluster context
kubectl config use-context backup-cluster

# Deploy latest application
kubectl apply -k k8s/overlays/production/

# Verify deployment
kubectl get pods -n corporate-intel
kubectl get svc -n corporate-intel

# Update DNS (Route53)
aws route53 change-resource-record-sets \
    --hosted-zone-id Z1234567890ABC \
    --change-batch file://dns-failover.json

# Verify DNS propagation
dig api.corporate-intel.com
```

**Step 3: Restore Database Connection (15 minutes)**
```bash
# Point application to database read replica
kubectl set env deployment/corporate-intel-api \
    POSTGRES_HOST=postgres-replica.us-west-2.rds.amazonaws.com

# Promote read replica to master
aws rds promote-read-replica \
    --db-instance-identifier corporate-intel-replica

# Wait for promotion
aws rds wait db-instance-available \
    --db-instance-identifier corporate-intel-replica

# Update application to use new master
kubectl set env deployment/corporate-intel-api \
    POSTGRES_HOST=corporate-intel-replica.us-west-2.rds.amazonaws.com
```

**Total Time: 50 minutes (within RTO of 1 hour for regional outage)**

---

## 4. Failover Procedures

### 4.1 Multi-Region Failover

**Architecture:**
```
Primary Region: us-east-1
Backup Region: us-west-2

DNS: Route53 with health checks
Database: Primary + Read Replica (with auto-promotion)
Application: Active-passive deployment
```

**Automated Failover** (scripts/failover-to-backup.sh):
```bash
#!/bin/bash
set -euo pipefail

PRIMARY_HEALTH="https://api.corporate-intel.com/health"
BACKUP_REGION="us-west-2"
ROUTE53_ZONE="Z1234567890ABC"

echo "Initiating failover to backup region..."

# 1. Verify primary is down
if curl -f "$PRIMARY_HEALTH" --max-time 10 --retry 3; then
    echo "ERROR: Primary appears healthy. Aborting failover."
    exit 1
fi

# 2. Promote database replica
echo "Promoting database replica to master..."
aws rds promote-read-replica \
    --region $BACKUP_REGION \
    --db-instance-identifier corporate-intel-replica

aws rds wait db-instance-available \
    --region $BACKUP_REGION \
    --db-instance-identifier corporate-intel-replica

# 3. Update DNS to point to backup
echo "Updating Route53 DNS records..."
aws route53 change-resource-record-sets \
    --hosted-zone-id $ROUTE53_ZONE \
    --change-batch '{
        "Changes": [{
            "Action": "UPSERT",
            "ResourceRecordSet": {
                "Name": "api.corporate-intel.com",
                "Type": "A",
                "AliasTarget": {
                    "HostedZoneId": "Z0987654321XYZ",
                    "DNSName": "backup-lb.us-west-2.elb.amazonaws.com",
                    "EvaluateTargetHealth": true
                }
            }
        }]
    }'

# 4. Scale up backup region
echo "Scaling backup region..."
kubectl config use-context backup-cluster
kubectl scale deployment corporate-intel-api --replicas=10

# 5. Verify backup region health
sleep 30
BACKUP_HEALTH="https://backup.corporate-intel.com/health"
if ! curl -f "$BACKUP_HEALTH" --max-time 10; then
    echo "ERROR: Backup region unhealthy after failover!"
    exit 1
fi

# 6. Send notifications
echo "Sending failover notifications..."
aws sns publish \
    --region us-east-1 \
    --topic-arn arn:aws:sns:us-east-1:123456789:critical-alerts \
    --subject "FAILOVER COMPLETED: Now serving from $BACKUP_REGION" \
    --message "Primary region failed. Traffic now routed to backup region."

# 7. Update status page
curl -X POST https://status.corporate-intel.com/api/incidents \
    -H "Authorization: Bearer $STATUS_PAGE_API_KEY" \
    -d '{
        "name": "Service Failover to Backup Region",
        "status": "investigating",
        "message": "We have failed over to our backup infrastructure. Service is restored."
    }'

echo "Failover completed successfully!"
echo "Monitor: https://backup.corporate-intel.com"
```

### 4.2 Database Failover

**Automated Database Promotion:**
```bash
#!/bin/bash
# scripts/promote-database-replica.sh

REPLICA_ID="corporate-intel-replica"
REGION="us-west-2"

# Promote replica
aws rds promote-read-replica \
    --region $REGION \
    --db-instance-identifier $REPLICA_ID

# Wait for promotion
aws rds wait db-instance-available \
    --region $REGION \
    --db-instance-identifier $REPLICA_ID

# Update application config
kubectl set env deployment/corporate-intel-api \
    POSTGRES_HOST=${REPLICA_ID}.${REGION}.rds.amazonaws.com \
    POSTGRES_PORT=5432

# Verify connection
kubectl exec -it deploy/corporate-intel-api -- \
    psql -h ${REPLICA_ID}.${REGION}.rds.amazonaws.com \
         -U postgres \
         -d corporate_intel \
         -c "SELECT 1;"
```

---

## 5. Communication Protocols

### 5.1 Internal Communication

**Incident War Room:**
```
Platform: Slack #incidents channel
Participants:
  - Incident Commander (IC)
  - On-Call Engineer
  - Database Administrator
  - Security Lead (if security-related)
  - CTO (for P0 incidents)
```

**Status Updates:**
```yaml
P0 Incidents:
  Frequency: Every 15 minutes
  Format: "Status Update: [timestamp] - [current status] - [next steps]"

P1 Incidents:
  Frequency: Every 30 minutes
  Format: Same as P0

P2/P3 Incidents:
  Frequency: As needed
```

### 5.2 External Communication

**Customer Notifications:**

**P0 Incidents (Immediate):**
```
Channel: Email + Status Page
Timing: Within 15 minutes of incident start

Template:
---
Subject: Service Disruption - Corporate Intelligence Platform

We are currently experiencing a service disruption affecting [impacted services].
Our team is actively working to resolve this issue.

Status: Investigating
Impact: [Brief description]
Started: [Timestamp]
Next Update: [15 minutes from now]

For real-time updates: https://status.corporate-intel.com
---
```

**P1 Incidents (Within 2 hours):**
```
Channel: Status Page
Timing: Within 2 hours

Template:
---
We are experiencing degraded performance on [impacted services].
A workaround is available: [workaround details]

Status: Investigating
Impact: [Brief description]
Workaround: [Details]
---
```

### 5.3 Escalation Path

```
Level 1: On-Call Engineer (0-30 minutes)
  ↓ (if unresolved after 30 min)
Level 2: Senior Engineer + DBA (30-60 minutes)
  ↓ (if unresolved after 1 hour)
Level 3: Engineering Manager + CTO (1-2 hours)
  ↓ (if unresolved after 2 hours)
Level 4: CEO + External Consultants (2+ hours)
```

---

## 6. Post-Incident Review

### 6.1 Incident Report Template

```markdown
# Incident Report: [Brief Title]

**Incident ID:** INC-YYYYMMDD-###
**Severity:** P0 / P1 / P2
**Date:** YYYY-MM-DD
**Duration:** [Start time] - [End time] (Total: X hours Y minutes)
**Incident Commander:** [Name]

## Summary
[2-3 sentence summary of what happened]

## Impact
- **Users Affected:** [Number/Percentage]
- **Services Affected:** [List]
- **Revenue Impact:** $[Amount] (if applicable)
- **RTO Target:** [X hours] | **Actual:** [Y hours]
- **RPO Target:** [X minutes] | **Actual:** [Y minutes]

## Timeline
| Time (UTC) | Event |
|------------|-------|
| 14:00 | Alert triggered: API health check failed |
| 14:02 | Incident declared, IC assigned |
| 14:05 | Root cause identified: Database connection pool exhausted |
| 14:10 | Mitigation started: Increased pool size |
| 14:15 | Service partially restored |
| 14:20 | Full service restored |
| 14:30 | Incident resolved, monitoring continues |

## Root Cause
[Detailed explanation of what caused the incident]

## Resolution
[What was done to resolve the incident]

## Action Items
1. [ ] [Action item 1] - Owner: [Name] - Due: [Date]
2. [ ] [Action item 2] - Owner: [Name] - Due: [Date]
3. [ ] [Action item 3] - Owner: [Name] - Due: [Date]

## Lessons Learned
### What Went Well
- [Item 1]
- [Item 2]

### What Could Be Improved
- [Item 1]
- [Item 2]

## Preventive Measures
[What will be done to prevent this from happening again]
```

### 6.2 Blameless Postmortem Process

**Schedule:** Within 48 hours of incident resolution

**Attendees:**
- Incident Commander
- All responders
- Engineering Manager
- Product Owner (if customer-facing)

**Agenda:**
1. Review timeline (10 min)
2. Discuss root cause (15 min)
3. Identify what went well (10 min)
4. Identify improvements (15 min)
5. Assign action items (10 min)

**Rules:**
- No blame or punishment
- Focus on systems and processes, not individuals
- All perspectives welcome
- Document everything
- Follow up on action items

---

## Emergency Contacts

```yaml
Incident Response:
  24/7 Hotline: +1-XXX-XXX-XXXX
  Email: incidents@corporate-intel.com
  PagerDuty: https://corporate-intel.pagerduty.com

On-Call Rotation:
  Primary: Check PagerDuty schedule
  Secondary: Check PagerDuty schedule

Key Personnel:
  CTO: cto@corporate-intel.com | +1-XXX-XXX-XXXX
  Engineering Manager: eng-manager@corporate-intel.com
  Database Administrator: dba@corporate-intel.com
  Security Lead: security@corporate-intel.com

External Vendors:
  AWS Support: Enterprise Support (24/7)
  Database Consultant: [Contact info]
  Security Consultant: [Contact info]
```

---

## Appendices

### A. Pre-Flight Checklist

**Before Every Deployment:**
- [ ] Backup verified within last 24 hours
- [ ] Rollback plan documented
- [ ] Communication plan prepared
- [ ] On-call engineer identified
- [ ] Incident response team briefed

### B. Recovery Scripts Location

```
scripts/disaster-recovery/
├── failover-to-backup.sh
├── restore-database.sh
├── promote-replica.sh
├── rollback-deployment.sh
└── verify-recovery.sh
```

### C. Testing Schedule

```yaml
Disaster Recovery Drills:
  Database Restore: Monthly
  Application Failover: Quarterly
  Full Regional Failover: Semi-annually
  Security Incident: Annually
```

---

**Document Version:** 1.0.0
**Last Drill:** [Date]
**Next Drill:** [Date]
**Next Review:** 2025-11-25
