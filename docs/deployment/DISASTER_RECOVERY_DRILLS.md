# Disaster Recovery Drill Procedures

## Overview

This document outlines comprehensive disaster recovery (DR) drill procedures to ensure business continuity and validate recovery capabilities.

**Last Updated**: 2025-10-25
**Review Frequency**: Quarterly

---

## DR Drill Types

### 1. Tabletop Exercise (Quarterly)
### 2. Simulated Failure (Monthly)
### 3. Full DR Test (Bi-Annual)
### 4. Regional Failover (Annual)

---

## 1. Tabletop Exercise

**Duration**: 2-4 hours
**Participants**: DevOps, Engineering, Management, Support
**Frequency**: Quarterly
**Impact**: No production impact

### Objectives

- Review DR procedures
- Identify gaps in documentation
- Test team communication
- Validate contact information
- Update runbooks

### Procedure

#### Phase 1: Preparation (30 minutes)

1. **Schedule Session**
   - Book conference room
   - Send calendar invites
   - Distribute materials in advance

2. **Prepare Scenario**
   ```yaml
   scenario:
     type: database_corruption
     severity: critical
     affected_systems:
       - PostgreSQL primary
       - Redis cache
     business_impact: complete_outage
     detection_method: monitoring_alert
   ```

3. **Gather Materials**
   - Current DR runbooks
   - System architecture diagrams
   - Contact lists
   - Backup inventory
   - RTO/RPO documentation

#### Phase 2: Scenario Walkthrough (90 minutes)

1. **Initial Detection** (15 min)
   - Who receives the alert?
   - What is the escalation path?
   - How do we assess severity?

2. **Assessment** (30 min)
   - What data do we need?
   - How do we access systems?
   - What is the impact assessment?

3. **Recovery Steps** (30 min)
   - What is the recovery procedure?
   - Who performs each step?
   - What are the dependencies?
   - What are the verification steps?

4. **Communication** (15 min)
   - Who needs to be notified?
   - What is the communication template?
   - When do we notify customers?

#### Phase 3: Review and Improve (60 minutes)

1. **Identify Gaps**
   - Document unclear procedures
   - Note missing information
   - Identify training needs

2. **Action Items**
   - Assign owners
   - Set deadlines
   - Track in project management tool

3. **Update Documentation**
   - Revise runbooks
   - Update contact lists
   - Improve procedures

### Success Criteria

- [ ] All participants understand their roles
- [ ] Recovery procedures are clear
- [ ] Communication plan is validated
- [ ] Gaps are documented
- [ ] Action items are assigned
- [ ] Documentation is updated

---

## 2. Simulated Failure Tests

**Duration**: 1-3 hours per test
**Frequency**: Monthly
**Environment**: Staging only
**Impact**: No production impact

### Test Scenarios

#### 2.1 Database Primary Failure

**Scenario**: PostgreSQL primary database becomes unavailable

**Procedure**:

```bash
#!/bin/bash
# Simulate database primary failure

echo "=== Database Failure Simulation ==="

# 1. Verify baseline
echo "Verifying baseline..."
psql -U postgres -h primary -c "SELECT 1;" || echo "❌ Primary not accessible"

# 2. Simulate failure (stop primary)
echo "Stopping primary database..."
docker stop corporate-intel-postgres-primary

# 3. Monitor failover
echo "Monitoring failover..."
sleep 10

# 4. Verify replica promotion
psql -U postgres -h replica -c "SELECT pg_is_in_recovery();"
# Expected: false (promoted to primary)

# 5. Test application connectivity
echo "Testing application..."
curl -f http://staging:8000/api/v1/health/database || echo "❌ App cannot connect"

# 6. Verify data writes
psql -U postgres -h replica -c "INSERT INTO audit_log (message) VALUES ('DR test');"

# 7. Measure recovery time
echo "Recovery completed in X seconds"

# 8. Restore primary
docker start corporate-intel-postgres-primary

# 9. Re-sync replica
# Follow replication setup procedures

echo "=== Test Complete ==="
```

**Success Criteria**:
- Automatic failover occurs
- RTO < 5 minutes
- No data loss (RPO = 0)
- Application reconnects automatically
- Data writes succeed on new primary

#### 2.2 Redis Cache Failure

**Scenario**: Redis cache becomes unavailable

**Procedure**:

```bash
# 1. Stop Redis
docker stop corporate-intel-redis

# 2. Test application degradation
# App should still work (slower, direct DB queries)
curl -f http://staging:8000/api/v1/companies

# 3. Monitor performance impact
# Response time should increase but stay < 1s

# 4. Restart Redis
docker start corporate-intel-redis

# 5. Verify cache warming
# Cache should repopulate automatically

# 6. Monitor performance recovery
# Response time should return to baseline
```

**Success Criteria**:
- Application remains available
- Performance degradation is acceptable
- No errors returned to users
- Cache recovers automatically
- Performance returns to normal

#### 2.3 API Service Failure

**Scenario**: API service crashes

```bash
# 1. Kill API process
docker kill corporate-intel-api

# 2. Monitor health checks
# Health checks should fail

# 3. Wait for auto-restart (Docker restart policy)
sleep 30

# 4. Verify service recovery
curl -f http://staging:8000/api/v1/health/ping

# 5. Check logs for errors
docker logs corporate-intel-api --tail 50
```

#### 2.4 Network Partition

**Scenario**: Network connectivity lost between components

```bash
# 1. Block network (iptables)
iptables -A OUTPUT -d 10.0.2.0/24 -j DROP

# 2. Monitor impact
# Services should handle gracefully

# 3. Restore network
iptables -D OUTPUT -d 10.0.2.0/24 -j DROP

# 4. Verify recovery
# All services should reconnect
```

#### 2.5 Disk Full Scenario

**Scenario**: Disk space exhausted

```bash
# 1. Fill disk (use fallocate in test)
fallocate -l 10G /var/lib/postgresql/data/test_fill.dat

# 2. Monitor alerts
# Should receive disk space alert

# 3. Test application behavior
# Should handle gracefully (no crashes)

# 4. Clean up
rm /var/lib/postgresql/data/test_fill.dat

# 5. Verify recovery
# Services should return to normal
```

### Monthly Test Schedule

| Week | Test Scenario |
|------|---------------|
| Week 1 | Database Primary Failure |
| Week 2 | Redis Cache Failure |
| Week 3 | API Service Failure |
| Week 4 | Network Partition or Disk Full |

---

## 3. Full Disaster Recovery Test

**Duration**: 4-8 hours
**Frequency**: Bi-annual
**Environment**: Dedicated DR environment
**Impact**: No production impact

### Objectives

- Validate complete system recovery
- Test all backup systems
- Measure actual RTO/RPO
- Train team on procedures
- Identify improvements

### Prerequisites

- [ ] DR environment provisioned
- [ ] Recent backups available
- [ ] All team members available
- [ ] Runbooks updated
- [ ] Communication plan ready
- [ ] Monitoring configured

### Procedure

#### Phase 1: Scenario Initiation (30 min)

```yaml
disaster_scenario:
  type: complete_datacenter_loss
  cause: catastrophic_failure
  affected_systems: all_production_systems
  data_loss: none_expected
  estimated_downtime: 4_hours
```

**Actions**:
1. Declare disaster scenario
2. Activate DR team
3. Begin communication plan
4. Start time tracking

#### Phase 2: Assessment (30 min)

1. **Verify Backup Status**
   ```bash
   # Check latest backups
   ls -lh /backups/database/
   ls -lh /backups/application/

   # Verify backup age
   find /backups -type f -mtime -1

   # Check backup integrity
   md5sum /backups/database/latest.sql
   ```

2. **Review DR Infrastructure**
   - Verify DR servers are available
   - Check network connectivity
   - Validate DNS configuration
   - Confirm storage availability

#### Phase 3: Infrastructure Provisioning (60 min)

```bash
#!/bin/bash
# Provision DR infrastructure

# 1. Provision servers (if not pre-provisioned)
terraform apply -var-file=dr.tfvars

# 2. Configure networking
./scripts/setup_dr_network.sh

# 3. Setup DNS
./scripts/configure_dr_dns.sh

# 4. Verify connectivity
ping -c 4 dr-database.example.com
ping -c 4 dr-api.example.com
```

#### Phase 4: Database Recovery (90 min)

```bash
#!/bin/bash
# Database recovery procedure

echo "=== Starting Database Recovery ==="

# 1. Install PostgreSQL (if needed)
apt-get install -y postgresql-14

# 2. Stop PostgreSQL
systemctl stop postgresql

# 3. Restore database files
echo "Restoring database backup..."
gunzip -c /backups/database/latest.sql.gz | psql -U postgres -d corporate_intel

# 4. Verify data integrity
echo "Verifying data integrity..."
psql -U postgres -d corporate_intel -c "SELECT COUNT(*) FROM companies;"
psql -U postgres -d corporate_intel -c "SELECT COUNT(*) FROM financial_metrics;"

# 5. Check for errors
psql -U postgres -d corporate_intel -c "SELECT * FROM companies LIMIT 1;"

# 6. Start PostgreSQL
systemctl start postgresql

# 7. Verify database is operational
psql -U postgres -c "SELECT version();"

echo "=== Database Recovery Complete ==="
```

#### Phase 5: Application Deployment (90 min)

```bash
#!/bin/bash
# Application deployment in DR environment

echo "=== Deploying Application ==="

# 1. Clone repository (or restore from backup)
git clone https://github.com/example/corporate-intel.git
cd corporate-intel

# 2. Restore configuration
cp /backups/config/.env .env

# 3. Build containers
docker-compose -f docker-compose.dr.yml build

# 4. Start services
docker-compose -f docker-compose.dr.yml up -d

# 5. Wait for services
sleep 30

# 6. Check service health
curl -f http://dr-api:8000/api/v1/health/ping
curl -f http://dr-api:8000/api/v1/health/ready

echo "=== Application Deployment Complete ==="
```

#### Phase 6: Verification and Testing (90 min)

```bash
#!/bin/bash
# Comprehensive verification

echo "=== Running Verification Tests ==="

# 1. Run smoke tests
pytest tests/production/test_critical_path.py -v

# 2. Verify all endpoints
./scripts/verify_endpoints.sh

# 3. Test authentication
./scripts/test_auth.sh

# 4. Check data accessibility
python -c "
from src.database import get_db
db = get_db()
count = db.query('SELECT COUNT(*) FROM companies').scalar()
print(f'Companies: {count}')
assert count > 0
"

# 5. Load test (light)
locust -f tests/load/locustfile_production.py \
    --host=http://dr-api:8000 \
    --users=10 \
    --spawn-rate=1 \
    --run-time=5m \
    --headless

echo "=== Verification Complete ==="
```

#### Phase 7: Cutover Simulation (30 min)

**Note**: In actual disaster, this would redirect production traffic

```bash
# 1. Update DNS (in real DR)
# aws route53 change-resource-record-sets ...

# 2. Verify DNS propagation
dig api.example.com

# 3. Monitor traffic
# Check load balancer metrics

# 4. Verify user access
# Test from external network
```

#### Phase 8: Debrief and Documentation (60 min)

1. **Measure Metrics**
   - Actual RTO achieved
   - Data loss (RPO)
   - Issues encountered
   - Resolution times

2. **Team Feedback**
   - What went well?
   - What needs improvement?
   - Documentation gaps?
   - Training needs?

3. **Action Items**
   - Update runbooks
   - Fix identified issues
   - Schedule training
   - Improve automation

### Success Criteria

- [ ] Complete system recovered within RTO (4 hours)
- [ ] No data loss (RPO = 0)
- [ ] All critical paths functional
- [ ] Performance acceptable
- [ ] Team confident in procedures
- [ ] Documentation validated
- [ ] Improvements identified

### Metrics to Track

```yaml
dr_metrics:
  detection_time: "5 minutes"
  assessment_time: "30 minutes"
  infrastructure_provisioning: "60 minutes"
  database_recovery: "90 minutes"
  application_deployment: "90 minutes"
  verification: "90 minutes"
  total_rto: "6 hours 5 minutes"
  rpo: "0 minutes (no data loss)"

  success_criteria:
    smoke_tests_passed: true
    performance_acceptable: true
    no_critical_issues: true
    documentation_accurate: true
```

---

## 4. Regional Failover Test

**Duration**: Full day (8+ hours)
**Frequency**: Annual
**Environment**: Production + DR region
**Impact**: Potential user impact (scheduled maintenance)

### Objectives

- Test geographic redundancy
- Validate cross-region replication
- Measure failover time
- Test DNS failover
- Verify load balancer configuration

### Procedure

#### Phase 1: Preparation (1 week before)

1. **Customer Notification**
   ```
   Subject: Scheduled Maintenance - Regional Failover Test

   Dear Customers,

   We will be conducting a regional failover test on [DATE] from [TIME] to [TIME].
   You may experience brief interruptions during this period.

   Expected impact:
   - Service interruption: < 5 minutes
   - No data loss expected
   - Performance may vary during test

   Thank you for your patience.
   ```

2. **Team Preparation**
   - Review runbooks
   - Assign roles
   - Schedule war room
   - Prepare monitoring dashboards

3. **Pre-flight Checks**
   ```bash
   # Verify DR region readiness
   ./scripts/verify_dr_region.sh

   # Check replication lag
   ./scripts/check_replication_lag.sh

   # Test DNS configuration
   ./scripts/test_dns_failover.sh
   ```

#### Phase 2: Execution

1. **Initiate Failover** (T+0)
   ```bash
   # Update Route53 to point to DR region
   ./scripts/failover_to_dr.sh
   ```

2. **Monitor** (T+0 to T+30min)
   - DNS propagation
   - Traffic shift
   - Error rates
   - Performance metrics

3. **Verify** (T+30min to T+1hr)
   - All services operational
   - Data consistency
   - User access

4. **Operate in DR** (T+1hr to T+4hr)
   - Normal operations
   - Monitor closely
   - Collect metrics

5. **Failback** (T+4hr)
   ```bash
   # Failback to primary region
   ./scripts/failback_to_primary.sh
   ```

6. **Post-Failback Verification** (T+4hr to T+5hr)
   - Services restored
   - Replication re-established
   - Performance normal

### Success Criteria

- [ ] Failover completed within 5 minutes
- [ ] No data loss
- [ ] < 0.1% error rate during transition
- [ ] DR region handles full load
- [ ] Failback successful
- [ ] Customer impact minimal

---

## DR Drill Schedule (Annual)

| Quarter | Activity | Type | Duration |
|---------|----------|------|----------|
| Q1 | Tabletop Exercise | Discussion | 2-4 hrs |
| Q1 | Database Failure | Simulated | 1-3 hrs |
| Q2 | Tabletop Exercise | Discussion | 2-4 hrs |
| Q2 | Full DR Test | Complete Recovery | 4-8 hrs |
| Q3 | Tabletop Exercise | Discussion | 2-4 hrs |
| Q3 | Network Partition | Simulated | 1-3 hrs |
| Q4 | Tabletop Exercise | Discussion | 2-4 hrs |
| Q4 | Regional Failover | Production | Full day |

---

## Roles and Responsibilities

### Incident Commander
- Overall coordination
- Decision making
- External communication

### Database Lead
- Database recovery
- Data integrity verification
- Replication setup

### Infrastructure Lead
- Server provisioning
- Network configuration
- DNS management

### Application Lead
- Application deployment
- Configuration management
- Service verification

### Communications Lead
- Customer notifications
- Status updates
- Stakeholder communication

### Documentation Lead
- Record timeline
- Document issues
- Capture lessons learned

---

## Post-Drill Report Template

```markdown
# DR Drill Report - [DATE]

## Executive Summary
- Drill Type: [Type]
- Duration: [Actual time]
- Overall Result: [Success/Partial/Failed]

## Metrics
- RTO Target: [X hours]
- RTO Achieved: [Y hours]
- RPO Target: [X minutes]
- RPO Achieved: [Y minutes]

## What Went Well
1. [Item 1]
2. [Item 2]

## Issues Encountered
1. [Issue 1]
   - Impact: [High/Medium/Low]
   - Resolution: [How resolved]
   - Action item: [What to improve]

## Action Items
| Item | Owner | Due Date | Priority |
|------|-------|----------|----------|
| [Action] | [Person] | [Date] | [H/M/L] |

## Recommendations
1. [Recommendation 1]
2. [Recommendation 2]

## Next Steps
- [ ] Update runbooks
- [ ] Schedule training
- [ ] Implement improvements
```

---

## Contact Information

**DR Coordinator**: dr-coordinator@example.com
**Incident Response**: incident@example.com
**24/7 Hotline**: +1-XXX-XXX-XXXX

---

## References

- Backup and Restore Procedures: docs/testing/BACKUP_RESTORE_PROCEDURES.md
- Production Deployment Runbook: docs/deployment/PRODUCTION_DEPLOYMENT.md
- Monitoring and Alerting: docs/deployment/monitoring-setup.md

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-10-25 | QA Team | Initial version |
