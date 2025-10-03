# Corporate Intelligence Platform - Staging Deployment Plan

**Version:** 1.0.0
**Date:** 2025-10-02
**Environment:** Staging
**Prepared by:** Staging Deployment Specialist Agent

---

## Table of Contents

1. [Overview](#overview)
2. [Infrastructure Requirements](#infrastructure-requirements)
3. [Pre-Deployment Checklist](#pre-deployment-checklist)
4. [Environment Configuration](#environment-configuration)
5. [Deployment Steps](#deployment-steps)
6. [Health Check Procedures](#health-check-procedures)
7. [Monitoring Setup](#monitoring-setup)
8. [Rollback Plan](#rollback-plan)
9. [Post-Deployment Verification](#post-deployment-verification)
10. [Troubleshooting](#troubleshooting)

---

## 1. Overview

### Purpose
Deploy the Corporate Intelligence Platform to staging environment for pre-production testing and validation.

### Deployment Strategy
- **Type:** Blue-Green deployment with health checks
- **Downtime:** Zero-downtime deployment
- **Rollback:** Automated rollback on health check failures

### Key Components
- FastAPI application (Python 3.11)
- PostgreSQL 15 with TimescaleDB
- Redis 7 (caching)
- MinIO (object storage)
- Observability stack (Jaeger, Prometheus, Grafana)

---

## 2. Infrastructure Requirements

### Minimum Server Specifications

#### Application Server
- **CPU:** 4 cores (2 GHz+)
- **RAM:** 8 GB minimum, 16 GB recommended
- **Storage:** 50 GB SSD
- **Network:** 100 Mbps bandwidth

#### Database Server
- **CPU:** 4 cores
- **RAM:** 8 GB minimum
- **Storage:** 100 GB SSD (with automatic expansion)
- **IOPS:** 3000+ for TimescaleDB operations

### Software Prerequisites
```bash
# Required software versions
Docker Engine: 24.0+
Docker Compose: 2.20+
Git: 2.40+
curl/wget: latest
jq: 1.6+ (for JSON processing)
```

### Network Configuration
- **Ports Required:**
  - 8000: FastAPI application
  - 5432: PostgreSQL
  - 6379: Redis
  - 9000: MinIO API
  - 9001: MinIO Console
  - 16686: Jaeger UI
  - 4317/4318: OTLP endpoints
  - 9090: Prometheus
  - 3000: Grafana

### DNS/Domain Setup
- Staging API: `staging-api.corporate-intel.example.com`
- Staging MinIO: `staging-storage.corporate-intel.example.com`
- Staging Monitoring: `staging-monitor.corporate-intel.example.com`

---

## 3. Pre-Deployment Checklist

### Security Review
- [ ] All secrets rotated from development values
- [ ] SSL/TLS certificates obtained and validated
- [ ] Firewall rules configured
- [ ] VPN/bastion host access configured
- [ ] Database credentials secured in secrets manager
- [ ] API keys validated and rate-limited

### Environment Validation
- [ ] Docker and Docker Compose installed
- [ ] Sufficient disk space available (100GB+)
- [ ] Network connectivity verified
- [ ] DNS records configured
- [ ] Load balancer configured (if applicable)
- [ ] Backup strategy in place

### Code Readiness
- [ ] Docker image built and tagged
- [ ] Database migrations tested
- [ ] Integration tests passed
- [ ] Security scan completed (no critical vulnerabilities)
- [ ] Performance benchmarks validated

### External Dependencies
- [ ] Alpha Vantage API key configured
- [ ] NewsAPI key configured
- [ ] SEC EDGAR user agent configured
- [ ] Sentry DSN configured (optional)
- [ ] External API rate limits verified

---

## 4. Environment Configuration

### Environment Variables (.env.staging)

Create `/path/to/.env.staging` with the following configuration:

```bash
# ============================================================================
# STAGING ENVIRONMENT CONFIGURATION
# ============================================================================

# Environment Settings
ENVIRONMENT=staging
DEBUG=true
LOG_LEVEL=DEBUG

# Security - CRITICAL: Use secure random values
SECRET_KEY=<GENERATE_WITH: python -c "import secrets; print(secrets.token_urlsafe(64))">

# Database Configuration
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=intel_staging_user
POSTGRES_PASSWORD=<SECURE_PASSWORD_FROM_SECRETS_MANAGER>
POSTGRES_DB=corporate_intel_staging
DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}

# Redis Configuration
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=<SECURE_REDIS_PASSWORD>
REDIS_DB=0
REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0

# MinIO Object Storage
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=intel_staging_admin
MINIO_SECRET_KEY=<SECURE_MINIO_SECRET>
MINIO_USE_SSL=false
MINIO_BUCKET_DOCUMENTS=staging-documents
MINIO_BUCKET_REPORTS=staging-reports

# External APIs
ALPHA_VANTAGE_API_KEY=<YOUR_API_KEY>
NEWSAPI_KEY=<YOUR_API_KEY>
SEC_USER_AGENT=Corporate Intel Platform/1.0 (staging@corporate-intel.example.com)

# Observability
OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317
OTEL_SERVICE_NAME=corporate-intel-staging
OTEL_TRACES_ENABLED=true
SENTRY_DSN=<YOUR_SENTRY_DSN>
SENTRY_ENVIRONMENT=staging
SENTRY_TRACES_SAMPLE_RATE=1.0

# Monitoring
GRAFANA_PASSWORD=<SECURE_GRAFANA_PASSWORD>

# Application Settings
API_PORT=8000
CORS_ORIGINS=["https://staging.corporate-intel.example.com"]
RATE_LIMIT_PER_MINUTE=100
SESSION_TIMEOUT_MINUTES=120
```

### Secrets Management

**Recommended approach:** Use environment-specific secrets manager

```bash
# AWS Secrets Manager example
aws secretsmanager get-secret-value \
  --secret-id corporate-intel/staging/database \
  --query SecretString \
  --output text | jq -r .password

# HashiCorp Vault example
vault kv get -field=password secret/corporate-intel/staging/postgres
```

---

## 5. Deployment Steps

### Step 1: Prepare Deployment Environment

```bash
#!/bin/bash
# File: scripts/deploy-staging-prep.sh

set -euo pipefail

echo "=== Corporate Intel - Staging Deployment Preparation ==="

# 1. Create deployment directory
DEPLOY_DIR="/opt/corporate-intel/staging"
sudo mkdir -p ${DEPLOY_DIR}
cd ${DEPLOY_DIR}

# 2. Clone/update repository
if [ -d ".git" ]; then
  git fetch origin
  git checkout main
  git pull origin main
else
  git clone https://github.com/brandonjplambert/corporate-intel.git .
fi

# 3. Verify Docker availability
docker --version || { echo "Docker not installed"; exit 1; }
docker-compose --version || { echo "Docker Compose not installed"; exit 1; }

# 4. Load staging environment
if [ ! -f .env.staging ]; then
  echo "ERROR: .env.staging not found"
  exit 1
fi

cp .env.staging .env

# 5. Create necessary directories
mkdir -p logs data backups monitoring/dashboards

echo "✓ Preparation complete"
```

### Step 2: Build Docker Image

```bash
#!/bin/bash
# File: scripts/deploy-staging-build.sh

set -euo pipefail

echo "=== Building Docker Image for Staging ==="

# Build with staging tag
docker build \
  --tag corporate-intel-api:staging-$(date +%Y%m%d-%H%M%S) \
  --tag corporate-intel-api:staging-latest \
  --build-arg ENVIRONMENT=staging \
  --file Dockerfile \
  --progress=plain \
  .

# Verify image was created
docker images | grep corporate-intel-api

echo "✓ Docker image built successfully"
```

### Step 3: Database Initialization

```bash
#!/bin/bash
# File: scripts/deploy-staging-database.sh

set -euo pipefail

echo "=== Initializing Staging Database ==="

# 1. Start PostgreSQL service only
docker-compose up -d postgres

# 2. Wait for database to be ready
echo "Waiting for PostgreSQL to be ready..."
timeout 60 bash -c 'until docker-compose exec -T postgres pg_isready -U intel_staging_user -d corporate_intel_staging; do sleep 2; done'

# 3. Run database migrations
echo "Running Alembic migrations..."
docker-compose run --rm api alembic upgrade head

# 4. Verify migrations
docker-compose exec -T postgres psql -U intel_staging_user -d corporate_intel_staging -c "\dt"

echo "✓ Database initialized successfully"
```

### Step 4: Deploy Application Stack

```bash
#!/bin/bash
# File: scripts/deploy-staging-app.sh

set -euo pipefail

echo "=== Deploying Corporate Intel Application Stack ==="

# 1. Pull latest images for dependencies
docker-compose pull postgres redis minio jaeger

# 2. Start all services
docker-compose up -d

# 3. Wait for all services to be healthy
echo "Waiting for services to be healthy..."
timeout 180 bash -c '
  until [ "$(docker-compose ps | grep -c "Up (healthy)")" -ge 4 ]; do
    echo "Waiting for health checks..."
    sleep 5
  done
'

# 4. Display service status
docker-compose ps

echo "✓ Application stack deployed successfully"
```

### Step 5: Initialize MinIO Buckets

```bash
#!/bin/bash
# File: scripts/deploy-staging-storage.sh

set -euo pipefail

echo "=== Initializing MinIO Storage Buckets ==="

# Install MinIO client if not available
if ! command -v mc &> /dev/null; then
  wget https://dl.min.io/client/mc/release/linux-amd64/mc
  chmod +x mc
  sudo mv mc /usr/local/bin/
fi

# Configure MinIO client
mc alias set staging-minio http://localhost:9000 \
  ${MINIO_ACCESS_KEY} ${MINIO_SECRET_KEY}

# Create buckets
mc mb staging-minio/staging-documents --ignore-existing
mc mb staging-minio/staging-reports --ignore-existing

# Set bucket policies (public read for reports)
mc anonymous set download staging-minio/staging-reports

# Verify buckets
mc ls staging-minio

echo "✓ MinIO storage initialized successfully"
```

---

## 6. Health Check Procedures

### Automated Health Checks

```bash
#!/bin/bash
# File: scripts/health-check-staging.sh

set -euo pipefail

echo "=== Corporate Intel Staging - Health Check ==="

API_URL="http://localhost:8000"
TIMEOUT=10

# Function to check endpoint
check_endpoint() {
  local endpoint=$1
  local expected_status=$2

  echo -n "Checking ${endpoint}... "

  status_code=$(curl -s -o /dev/null -w "%{http_code}" \
    --max-time ${TIMEOUT} \
    "${API_URL}${endpoint}")

  if [ "${status_code}" -eq "${expected_status}" ]; then
    echo "✓ OK (${status_code})"
    return 0
  else
    echo "✗ FAILED (${status_code}, expected ${expected_status})"
    return 1
  fi
}

# Health check endpoints
check_endpoint "/health" 200 || exit 1
check_endpoint "/api/v1/health/database" 200 || exit 1
check_endpoint "/api/v1/health/redis" 200 || exit 1
check_endpoint "/api/v1/health/minio" 200 || exit 1

# Check service dependencies
echo -n "Checking PostgreSQL... "
docker-compose exec -T postgres pg_isready -U intel_staging_user && echo "✓ OK" || exit 1

echo -n "Checking Redis... "
docker-compose exec -T redis redis-cli ping | grep -q PONG && echo "✓ OK" || exit 1

echo -n "Checking MinIO... "
curl -sf http://localhost:9000/minio/health/live > /dev/null && echo "✓ OK" || exit 1

echo ""
echo "=== All Health Checks Passed ==="
```

### Manual Health Verification

```bash
# 1. Check API response
curl http://localhost:8000/health | jq

# Expected output:
# {
#   "status": "healthy",
#   "timestamp": "2025-10-02T12:00:00Z",
#   "environment": "staging",
#   "version": "1.0.0"
# }

# 2. Check database connectivity
docker-compose exec postgres psql -U intel_staging_user -d corporate_intel_staging -c "SELECT version();"

# 3. Check Redis
docker-compose exec redis redis-cli ping

# 4. Check MinIO
curl http://localhost:9001 # Should return MinIO console

# 5. Check Jaeger
curl http://localhost:16686 # Should return Jaeger UI
```

---

## 7. Monitoring Setup

### Prometheus Configuration

Create `monitoring/prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    environment: staging
    cluster: corporate-intel

scrape_configs:
  - job_name: 'corporate-intel-api'
    static_configs:
      - targets: ['api:8000']
    metrics_path: '/metrics'

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']

alerting:
  alertmanagers:
    - static_configs:
        - targets: []
```

### Grafana Dashboard Setup

```bash
# Import pre-configured dashboards
curl -X POST http://localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -u admin:${GRAFANA_PASSWORD} \
  -d @monitoring/dashboards/corporate-intel-overview.json
```

### Log Aggregation

```bash
# View application logs
docker-compose logs -f api

# View all service logs
docker-compose logs -f

# Export logs for analysis
docker-compose logs --no-color > staging-logs-$(date +%Y%m%d).log
```

### Key Metrics to Monitor

1. **Application Metrics**
   - Request rate (requests/second)
   - Response time (p50, p95, p99)
   - Error rate (%)
   - Active connections

2. **Database Metrics**
   - Connection pool utilization
   - Query execution time
   - Cache hit ratio
   - Replication lag (if applicable)

3. **Infrastructure Metrics**
   - CPU utilization
   - Memory usage
   - Disk I/O
   - Network throughput

4. **Business Metrics**
   - API endpoint usage
   - Data ingestion rate
   - Report generation time
   - User activity

---

## 8. Rollback Plan

### Automated Rollback Triggers

- Health check failures (3 consecutive)
- Critical error rate > 5%
- Response time degradation > 50%
- Database connection failures

### Rollback Procedure

```bash
#!/bin/bash
# File: scripts/rollback-staging.sh

set -euo pipefail

echo "=== ROLLBACK INITIATED ==="

# 1. Stop current deployment
echo "Stopping current deployment..."
docker-compose down

# 2. Restore previous Docker image
PREVIOUS_TAG=$(docker images corporate-intel-api --format "{{.Tag}}" | grep staging | sed -n '2p')
echo "Rolling back to: ${PREVIOUS_TAG}"

# Update docker-compose to use previous tag
sed -i "s/image: corporate-intel-api:staging-latest/image: corporate-intel-api:${PREVIOUS_TAG}/" docker-compose.yml

# 3. Restore database from backup (if needed)
LATEST_BACKUP=$(ls -t backups/staging-db-*.sql | head -1)
if [ -n "${LATEST_BACKUP}" ]; then
  echo "Restoring database from: ${LATEST_BACKUP}"
  docker-compose up -d postgres
  sleep 10
  docker-compose exec -T postgres psql -U intel_staging_user -d corporate_intel_staging < "${LATEST_BACKUP}"
fi

# 4. Start services with previous version
echo "Starting services with previous version..."
docker-compose up -d

# 5. Wait for health checks
echo "Waiting for health checks..."
sleep 30
bash scripts/health-check-staging.sh

# 6. Verify rollback
if [ $? -eq 0 ]; then
  echo "✓ Rollback successful"
else
  echo "✗ Rollback failed - manual intervention required"
  exit 1
fi
```

### Database Rollback

```bash
# Rollback database migrations
docker-compose run --rm api alembic downgrade -1

# Restore from backup
docker-compose exec -T postgres pg_restore \
  -U intel_staging_user \
  -d corporate_intel_staging \
  --clean \
  /backups/staging-db-backup-latest.dump
```

---

## 9. Post-Deployment Verification

### Functional Testing Checklist

```bash
# 1. API Endpoints
curl http://localhost:8000/api/v1/companies/search?q=Apple | jq
curl http://localhost:8000/api/v1/market/quotes?symbols=AAPL | jq

# 2. Database Queries
docker-compose exec postgres psql -U intel_staging_user -d corporate_intel_staging -c "
  SELECT COUNT(*) FROM companies;
  SELECT COUNT(*) FROM market_data;
"

# 3. Cache Operations
docker-compose exec redis redis-cli INFO stats

# 4. Storage Operations
mc ls staging-minio/staging-documents
```

### Performance Baseline

```bash
# Run basic load test
ab -n 1000 -c 10 http://localhost:8000/health

# Expected results (baseline):
# - Requests per second: > 500
# - Mean response time: < 50ms
# - 95th percentile: < 100ms
```

### Security Validation

```bash
# 1. Check SSL/TLS configuration
curl -I https://staging-api.corporate-intel.example.com

# 2. Verify authentication
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"test"}'

# 3. Check CORS headers
curl -I -X OPTIONS http://localhost:8000/api/v1/companies \
  -H "Origin: https://staging.corporate-intel.example.com"
```

---

## 10. Troubleshooting

### Common Issues and Solutions

#### Issue 1: Container Fails to Start

```bash
# Check container logs
docker-compose logs api

# Common causes:
# - Missing environment variables
# - Port conflicts
# - Database connection issues

# Solution:
docker-compose down
docker-compose up -d postgres redis minio
# Wait 30 seconds
docker-compose up -d api
```

#### Issue 2: Database Migration Failures

```bash
# Check current migration status
docker-compose run --rm api alembic current

# View migration history
docker-compose run --rm api alembic history

# Manually fix and re-run
docker-compose run --rm api alembic upgrade head --sql > migration.sql
# Review migration.sql
docker-compose exec -T postgres psql -U intel_staging_user -d corporate_intel_staging < migration.sql
```

#### Issue 3: High Memory Usage

```bash
# Check container resource usage
docker stats

# Identify memory-heavy processes
docker-compose exec api ps aux --sort=-%mem | head

# Restart specific service
docker-compose restart api
```

#### Issue 4: Slow API Response

```bash
# Check database query performance
docker-compose exec postgres psql -U intel_staging_user -d corporate_intel_staging -c "
  SELECT query, calls, mean_exec_time, stddev_exec_time
  FROM pg_stat_statements
  ORDER BY mean_exec_time DESC
  LIMIT 10;
"

# Check cache hit rate
docker-compose exec redis redis-cli INFO stats | grep keyspace
```

### Emergency Contacts

- **DevOps Lead:** devops@corporate-intel.example.com
- **Database Admin:** dba@corporate-intel.example.com
- **Security Team:** security@corporate-intel.example.com
- **On-Call Engineer:** oncall@corporate-intel.example.com

### Support Resources

- Documentation: https://docs.corporate-intel.example.com
- Internal Wiki: https://wiki.corporate-intel.example.com
- Issue Tracker: https://github.com/brandonjplambert/corporate-intel/issues
- Slack Channel: #corporate-intel-staging

---

## Appendix A: Quick Reference Commands

```bash
# Start staging environment
docker-compose --env-file .env.staging up -d

# Stop staging environment
docker-compose down

# View logs
docker-compose logs -f api

# Run database migrations
docker-compose run --rm api alembic upgrade head

# Create database backup
docker-compose exec postgres pg_dump -U intel_staging_user corporate_intel_staging > backup.sql

# Rebuild and restart
docker-compose up -d --build api

# Scale workers
docker-compose up -d --scale api=3

# Clean up (CAUTION: removes volumes)
docker-compose down -v
```

---

## Appendix B: Deployment Timeline

| Phase | Duration | Description |
|-------|----------|-------------|
| Pre-deployment preparation | 30 min | Environment setup, secrets configuration |
| Docker image build | 10 min | Build and tag production image |
| Database initialization | 15 min | Create database, run migrations |
| Service deployment | 10 min | Start all containers |
| Health checks | 10 min | Verify all services healthy |
| Monitoring setup | 15 min | Configure dashboards, alerts |
| Smoke testing | 20 min | Basic functional verification |
| **Total** | **~2 hours** | Complete staging deployment |

---

## Appendix C: Success Criteria

Deployment is considered successful when ALL criteria are met:

- [ ] All containers running and healthy (0 restarts in 10 minutes)
- [ ] All health check endpoints returning 200 OK
- [ ] Database migrations completed without errors
- [ ] MinIO buckets created and accessible
- [ ] Application logs show no ERROR level messages
- [ ] Prometheus scraping metrics successfully
- [ ] Grafana dashboards displaying data
- [ ] API response time < 100ms (p95)
- [ ] No memory leaks (stable memory usage over 1 hour)
- [ ] Integration tests pass (if available)

---

**Document Version:** 1.0.0
**Last Updated:** 2025-10-02
**Next Review:** Before next staging deployment
