# Production Deployment Automation

**Version:** 1.0.0
**Last Updated:** October 17, 2025
**Status:** Production-Ready

---

## Overview

This document describes the automated deployment scripts for the Corporate Intelligence Platform production environment. These scripts provide a comprehensive, safe, and repeatable deployment process with built-in validation, health checks, and automatic rollback capabilities.

## Architecture

### Deployment Script Hierarchy

```
deploy-production.sh (Master Orchestrator)
├── validate-deployment.sh --pre-deploy
├── deploy-infrastructure.sh
│   ├── PostgreSQL with TimescaleDB
│   ├── Redis Cache
│   ├── MinIO Object Storage
│   └── Prometheus Exporters
├── deploy-api.sh
│   ├── Corporate Intelligence API
│   ├── Nginx Reverse Proxy
│   ├── Prometheus
│   ├── Grafana
│   ├── Jaeger
│   └── Alertmanager
├── validate-deployment.sh --post-deploy
└── rollback-production.sh (if needed)
```

---

## Scripts Overview

### 1. deploy-production.sh (Master Orchestrator)

**Purpose:** Main deployment script that coordinates all deployment phases.

**Features:**
- Pre-deployment validation
- Automated backups
- Infrastructure deployment
- Database migrations
- API deployment
- Post-deployment validation
- Smoke tests
- Monitoring activation
- Automatic rollback on failure

**Usage:**
```bash
./scripts/deploy-production.sh --version v1.2.0
```

**Options:**
```
--version VERSION        Deployment version tag (required)
--skip-backup           Skip pre-deployment backups (not recommended)
--skip-validation       Skip pre-deployment validation (not recommended)
--no-rollback           Don't auto-rollback on failure
--dry-run               Simulate deployment without making changes
--help                  Show this help message
```

**Exit Codes:**
- `0` - Deployment successful
- `1` - Pre-deployment validation failed
- `2` - Infrastructure deployment failed
- `3` - Database migration failed
- `4` - API deployment failed
- `5` - Health check failed
- `6` - Smoke tests failed
- `7` - User cancelled deployment

**Example:**
```bash
# Standard deployment
./scripts/deploy-production.sh --version v1.2.0

# Dry run (test without changes)
./scripts/deploy-production.sh --version v1.2.0 --dry-run

# Skip backups (not recommended for production)
./scripts/deploy-production.sh --version v1.2.0 --skip-backup
```

---

### 2. deploy-infrastructure.sh

**Purpose:** Deploys infrastructure services (PostgreSQL, Redis, MinIO).

**Features:**
- Network creation
- Volume provisioning
- PostgreSQL with TimescaleDB deployment
- Redis cache with persistence
- MinIO object storage with bucket creation
- Prometheus exporters
- Health check validation

**Usage:**
```bash
./scripts/deploy-infrastructure.sh --version v1.2.0
```

**Options:**
```
--version VERSION        Deployment version tag
--skip-health-checks    Skip health check validation
--recreate              Force recreate containers
--help                  Show this help message
```

**Services Deployed:**
- PostgreSQL 15 with TimescaleDB 2.13.0 (Port: 5432)
- Redis 7.2 with AOF persistence (Port: 6379)
- MinIO S3-compatible storage (Ports: 9000, 9001)
- PostgreSQL Exporter (Port: 9187)
- Redis Exporter (Port: 9121)

**Health Checks:**
- PostgreSQL: 60-second timeout, pg_isready check
- Redis: 30-second timeout, PING check
- MinIO: 45-second timeout, health endpoint check

---

### 3. deploy-api.sh

**Purpose:** Deploys API services and monitoring stack.

**Features:**
- Docker image pulling
- API deployment (with optional rolling update)
- Nginx reverse proxy configuration
- Monitoring stack deployment (Prometheus, Grafana, Jaeger)
- Health check validation
- Cache warm-up

**Usage:**
```bash
./scripts/deploy-api.sh --version v1.2.0
```

**Options:**
```
--version VERSION        Deployment version tag
--skip-health-checks    Skip health check validation
--rolling-update        Perform rolling update (zero-downtime)
--help                  Show this help message
```

**Services Deployed:**
- Corporate Intelligence API (Port: 8000)
- Nginx reverse proxy (Ports: 80, 443)
- Prometheus metrics (Port: 9090)
- Grafana dashboards (Port: 3000)
- Jaeger tracing (Port: 16686)
- Alertmanager (Port: 9093)
- Node Exporter (Port: 9100)
- cAdvisor (Port: 8080)

**Rolling Update:**
```bash
# Zero-downtime deployment
./scripts/deploy-api.sh --version v1.2.0 --rolling-update
```

This will:
1. Scale up to 2 API instances
2. Wait for new instance health check
3. Scale down old instance

---

### 4. validate-deployment.sh

**Purpose:** Validates deployment health and functionality.

**Features:**
- Container health status verification
- Service connectivity testing (PostgreSQL, Redis, MinIO)
- API endpoint health checks
- Database schema validation
- Cache functionality tests
- Performance metric validation
- Disk space monitoring

**Usage:**
```bash
# Pre-deployment validation
./scripts/validate-deployment.sh --pre-deploy

# Post-deployment validation
./scripts/validate-deployment.sh --post-deploy

# Quick validation (health checks only)
./scripts/validate-deployment.sh --quick

# Full validation (includes performance tests)
./scripts/validate-deployment.sh --full
```

**Options:**
```
--pre-deploy            Run pre-deployment validation
--post-deploy           Run post-deployment validation
--quick                 Run quick validation (health checks only)
--full                  Run full validation (includes performance tests)
--help                  Show this help message
```

**Validation Checks:**

**Quick Validation:**
- Docker daemon running
- Compose and environment files exist
- Containers running
- Service connectivity (PostgreSQL, Redis, MinIO)
- API health endpoint

**Full Validation:**
- All quick validation checks
- Container health status
- Docker volumes and networks
- Database tables exist
- Redis persistence enabled
- API response time (<100ms target)
- Monitoring stack health
- Database query performance (<50ms target)
- Cache hit ratio statistics
- Disk space (<70% usage target)

**Exit Code:**
- `0` - All validations passed
- `1` - One or more validations failed

---

### 5. rollback-production.sh

**Purpose:** Emergency rollback for failed deployments.

**Features:**
- Configuration rollback
- Container rollback
- Database rollback (optional, with data loss warning)
- Incident snapshot creation
- Automated or interactive mode
- Verification of rollback success

**Usage:**
```bash
# Interactive rollback to latest backup
./scripts/rollback-production.sh

# Automatic rollback (no confirmations)
./scripts/rollback-production.sh --auto --reason "API not starting"

# Rollback to specific timestamp
./scripts/rollback-production.sh --timestamp 20251017_120000

# Rollback with database restore (use with caution)
./scripts/rollback-production.sh --database --reason "Data corruption detected"

# Dry run (test without changes)
./scripts/rollback-production.sh --dry-run
```

**Options:**
```
--auto                  Automatic rollback (skip confirmations)
--reason "REASON"       Reason for rollback (required for auto)
--config-only           Rollback configuration only (not containers)
--database              Include database rollback (use with caution)
--timestamp TIMESTAMP   Specific backup timestamp to restore
--dry-run               Show what would be done without doing it
--help                  Show this help message
```

**Rollback Phases:**
1. **Incident Snapshot:** Saves current state for post-mortem
2. **Configuration Rollback:** Restores previous docker-compose and .env files
3. **Container Rollback:** Stops current, starts previous version
4. **Database Rollback (optional):** Restores database from backup
5. **Verification:** Health checks to confirm rollback success

**Warning:** Database rollback causes data loss! Only use when absolutely necessary.

---

## Deployment Workflow

### Standard Production Deployment

```bash
# 1. Prepare environment
cd /opt/corporate-intel
export DEPLOYMENT_VERSION="v1.2.0"

# 2. Run deployment (dry-run first)
./scripts/deploy-production.sh --version ${DEPLOYMENT_VERSION} --dry-run

# 3. Review dry-run output, then deploy for real
./scripts/deploy-production.sh --version ${DEPLOYMENT_VERSION}

# 4. Monitor deployment logs
tail -f deployment-logs/deployment-*.log

# 5. Verify deployment
./scripts/validate-deployment.sh --post-deploy --full

# 6. Monitor for 1 hour
# - Check Grafana: http://localhost:3000
# - Check Prometheus: http://localhost:9090
# - Check logs: docker-compose -f config/production/docker-compose.production.yml logs -f api
```

### Deployment Timeline

**Total Time:** 30-40 minutes (typical)

| Phase | Duration | Description |
|-------|----------|-------------|
| Pre-Deployment | 5-10 min | Validation, backups, confirmations |
| Infrastructure | 5-7 min | PostgreSQL, Redis, MinIO deployment |
| Database Migration | 5-10 min | Alembic migrations |
| API Deployment | 5-7 min | API, Nginx, monitoring stack |
| Validation | 5-10 min | Health checks, smoke tests |
| Monitoring | 1-2 min | Verify monitoring services |

**Downtime Window:** 2-5 minutes (during service restart)

---

## Safety Features

### 1. Idempotent Operations
All scripts can be run multiple times safely:
- Containers recreated if already exist
- Volumes preserved across deployments
- Networks reused if present
- Database migrations track applied changes

### 2. Automated Backups
Created before deployment:
- Docker Compose configuration
- Environment files
- Database dump (PostgreSQL)
- Metrics snapshot
- Container logs

**Backup Location:** `./backups/deployments/${TIMESTAMP}/`

### 3. Health Checks
Comprehensive validation:
- Container health status
- Service connectivity
- API endpoint responsiveness
- Database query performance
- Cache functionality

### 4. Automatic Rollback
Triggered on failure in any phase:
- Infrastructure deployment failure
- Database migration failure
- API deployment failure
- Health check failure

**Disable:** Use `--no-rollback` flag (not recommended)

### 5. Incident Snapshots
On rollback, creates snapshot with:
- Current configuration files
- Container logs (last 500 lines)
- Metrics snapshot
- Rollback reason and metadata

**Snapshot Location:** `./incident-snapshots/${TIMESTAMP}/`

---

## Configuration

### Required Files

**1. Docker Compose File**
```
config/production/docker-compose.production.yml
```
Defines all services, networks, volumes, and resource limits.

**2. Environment File**
```
config/production/.env.production
```
Contains all environment variables, secrets, and configuration.

### Required Directories

```
corporate_intel/
├── scripts/
│   ├── deploy-production.sh       # Master orchestrator
│   ├── deploy-infrastructure.sh   # Infrastructure deployment
│   ├── deploy-api.sh              # API deployment
│   ├── validate-deployment.sh     # Validation
│   └── rollback-production.sh     # Rollback
├── config/production/
│   ├── docker-compose.production.yml
│   └── .env.production
├── backups/
│   ├── deployments/               # Config backups
│   ├── postgres/                  # Database backups
│   └── configs/                   # Historical configs
├── deployment-logs/               # Deployment logs
└── incident-snapshots/            # Rollback snapshots
```

### Environment Variables

**Required in .env.production:**
```bash
# Database
POSTGRES_USER=intel_prod_user
POSTGRES_PASSWORD=<secret>
POSTGRES_DB=corporate_intel_prod

# Redis
REDIS_PASSWORD=<secret>

# MinIO
MINIO_ROOT_USER=intel_prod_admin
MINIO_ROOT_PASSWORD=<secret>

# Deployment
DEPLOYMENT_VERSION=v1.2.0
DOCKER_REGISTRY=ghcr.io
DOCKER_IMAGE_NAME=corporate-intel
```

---

## Performance Baseline

**Target Metrics** (from Day 1 baseline):

| Metric | Target | Baseline |
|--------|--------|----------|
| API P99 Latency | <100ms | 32.14ms |
| API Mean Latency | <50ms | 8.42ms |
| Health Endpoint | <10ms | 2.15ms |
| Database Queries | <50ms | 2.15ms |
| Throughput | >20 QPS | 27.3 QPS |
| Success Rate | >99.9% | 100% |
| Cache Hit Ratio | >95% | 99.2% |

**Validation:** Scripts verify performance doesn't degrade beyond these thresholds.

---

## Security Validation

**Automated Security Checks:**

1. **Container Security:**
   - No privileged containers (except cAdvisor)
   - Read-only root filesystems where possible
   - Non-root users
   - Resource limits enforced

2. **Network Security:**
   - Internal networks for backend services
   - Only necessary ports exposed
   - PostgreSQL/Redis only on localhost
   - SSL/TLS for external access

3. **Secret Management:**
   - Secrets in .env file (not hardcoded)
   - File permissions restricted (600)
   - No secrets in logs
   - AWS Secrets Manager integration ready

4. **Health Checks:**
   - All containers have health checks
   - Health check intervals: 10-30s
   - Start period grace time
   - Retry limits configured

---

## Monitoring Integration

### Prometheus Metrics

**Collected Metrics:**
- Container metrics (cAdvisor)
- System metrics (Node Exporter)
- PostgreSQL metrics (postgres-exporter)
- Redis metrics (redis-exporter)
- API metrics (application instrumentation)

**Access:** http://localhost:9090

### Grafana Dashboards

**Pre-configured Dashboards:**
- System Overview
- PostgreSQL Performance
- Redis Performance
- API Performance
- Container Metrics

**Access:** http://localhost:3000
**Default Credentials:** See .env.production

### Jaeger Tracing

**Distributed Tracing:**
- API request tracing
- Database query tracing
- Cache operation tracing
- External API call tracing

**Access:** http://localhost:16686

### Alertmanager

**Alert Routing:**
- Email notifications
- Slack integration
- PagerDuty integration

**Access:** http://localhost:9093

---

## Troubleshooting

### Common Issues

**1. Script Permission Denied**
```bash
chmod +x scripts/*.sh
```

**2. Docker Compose File Not Found**
```bash
ls -la config/production/docker-compose.production.yml
# If missing, check configuration
```

**3. Health Checks Timeout**
```bash
# Check container logs
docker-compose -f config/production/docker-compose.production.yml logs api

# Check if services are starting
docker-compose -f config/production/docker-compose.production.yml ps
```

**4. Database Migration Failed**
```bash
# Check migration logs
docker-compose -f config/production/docker-compose.production.yml logs api

# Manually check database
docker-compose -f config/production/docker-compose.production.yml exec postgres \
  psql -U intel_prod_user -d corporate_intel_prod
```

**5. Rollback Needed**
```bash
# Emergency rollback
./scripts/rollback-production.sh --auto --reason "Health checks failing"

# Check rollback logs
tail -f deployment-logs/deployment-*.log
```

---

## Best Practices

### Before Deployment

1. **Review Changes:**
   - Review git diff
   - Check breaking changes
   - Verify database migrations

2. **Test Staging:**
   - Deploy to staging first
   - Run full test suite
   - Verify performance

3. **Communication:**
   - Notify team of deployment
   - Schedule deployment window
   - Prepare rollback plan

4. **Backups:**
   - Verify backup storage available
   - Test backup restore (quarterly)
   - Check S3 backup upload works

### During Deployment

1. **Monitor Closely:**
   - Watch deployment logs
   - Monitor container startup
   - Check health checks

2. **Validate Each Phase:**
   - Don't skip validation
   - Review migration SQL before applying
   - Confirm backups created

3. **Be Ready to Rollback:**
   - Keep rollback command ready
   - Know rollback triggers
   - Don't hesitate if issues detected

### After Deployment

1. **Monitor for 1 Hour:**
   - Watch error rates
   - Monitor response times
   - Check resource usage

2. **Verify Functionality:**
   - Test key user flows
   - Check API endpoints
   - Verify integrations

3. **Document:**
   - Record deployment time
   - Note any issues
   - Update runbook if needed

---

## Appendix

### A. Script Dependencies

**Required Software:**
- Docker 20.10+
- Docker Compose 2.0+
- Bash 4.0+
- curl
- jq (optional, for JSON parsing)
- bc (for calculations)

**Optional:**
- AWS CLI (for S3 backups)
- git (for deployment tags)

### B. File Permissions

```bash
# Scripts should be executable
chmod +x scripts/*.sh

# Environment file should be restricted
chmod 600 config/production/.env.production

# Backup directory should be writable
chmod 755 backups/
```

### C. Backup Retention

**Configuration Backups:**
- Retention: 30 days
- Location: `backups/deployments/`
- Cleanup: Manual (run cleanup script monthly)

**Database Backups:**
- Retention: 30 days
- Location: `backups/postgres/` and S3
- Cleanup: Automated via S3 lifecycle policy

**Incident Snapshots:**
- Retention: 90 days
- Location: `incident-snapshots/`
- Cleanup: Manual (after post-mortem)

### D. Support Contacts

**For Issues:**
- DevOps Team: @devops-team (Slack)
- On-Call: PagerDuty schedule
- Emergency: See production runbook

**Documentation:**
- Main Runbook: `docs/deployment/production-deployment-runbook.md`
- Rollback Plan: `docs/deployment/production-rollback-plan.md`
- Security Validation: `docs/security_validation_day1_results.json`

---

**Document Version:** 1.0.0
**Last Updated:** October 17, 2025
**Maintained By:** DevOps Team
**Next Review:** Before each major deployment

---

**END OF DOCUMENTATION**
