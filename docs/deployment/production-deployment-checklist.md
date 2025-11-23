# Production Deployment Checklist

**Version:** 2.0.0
**Last Updated:** October 17, 2025
**Environment:** Production (corporate-intel-production)
**Target Platform:** Docker Compose / Kubernetes
**Performance Baseline:** 9.2/10 (P99: 32ms, Success: 100%)
**Security Score:** 9.2/10 (0 Critical, 0 High vulnerabilities)

---

## Overview

This comprehensive checklist ensures all systems, services, and configurations are validated before production deployment. Each section must be completed and signed off by designated team members.

**Estimated Total Time:** 4-6 hours (excluding DNS propagation)

---

## 1. Infrastructure Readiness

### 1.1 Server Provisioning

**Status:** [ ] Complete
**Owner:** Infrastructure Team
**Estimated Time:** 30 minutes (if already provisioned)

- [ ] **Production Server**
  - [ ] 8+ CPU cores available
  - [ ] 16+ GB RAM available (32 GB recommended)
  - [ ] 200+ GB SSD storage
  - [ ] Ubuntu 22.04 LTS or RHEL 8+
  - [ ] Static IP address assigned
  - [ ] Hostname configured: `prod-corporate-intel-01`

- [ ] **Database Server** (can be same server if specs allow)
  - [ ] 8+ CPU cores
  - [ ] 16+ GB RAM (32 GB recommended)
  - [ ] 500+ GB SSD with IOPS provisioning
  - [ ] Automated backups enabled
  - [ ] RAID configuration for redundancy

- [ ] **Load Balancer** (optional for single-server deployment)
  - [ ] Health check endpoints configured
  - [ ] SSL termination configured
  - [ ] Request routing rules defined

**Validation Command:**
```bash
# Verify server specs
lscpu | grep -E "^CPU\(s\)|^Model name"
free -h
df -h
uname -a
```

**Sign-off:** __________ Date: __________

---

### 1.2 Network Configuration

**Status:** [ ] Complete
**Owner:** Network/DevOps Team
**Estimated Time:** 45 minutes

#### Firewall Rules

- [ ] **Inbound Rules Configured**
  - [ ] Port 80 (HTTP) - Open to internet (redirects to HTTPS)
  - [ ] Port 443 (HTTPS) - Open to internet
  - [ ] Port 22 (SSH) - Restricted to bastion host IP only
  - [ ] Port 5432 (PostgreSQL) - Internal only (127.0.0.1)
  - [ ] Port 6379 (Redis) - Internal only (127.0.0.1)
  - [ ] Port 9000 (MinIO API) - Internal only (127.0.0.1)
  - [ ] Port 9001 (MinIO Console) - Restricted to admin IPs
  - [ ] Port 9090 (Prometheus) - Restricted to monitoring IPs
  - [ ] Port 3000 (Grafana) - Restricted to team IPs
  - [ ] Port 16686 (Jaeger UI) - Restricted to team IPs

- [ ] **Outbound Rules Configured**
  - [ ] Port 80/443 - Allow (external API calls)
  - [ ] Port 25/587 - Allow (email if applicable)
  - [ ] DNS (53) - Allow

**Validation Command:**
```bash
# Test firewall rules
sudo ufw status verbose
# Or for iptables:
sudo iptables -L -n -v
```

#### DNS Configuration

- [ ] **A Records Created**
  - [ ] `api.corporate-intel.com` → Production server IP
  - [ ] `www.corporate-intel.com` → Production server IP (if web frontend exists)

- [ ] **CNAME Records (Optional)**
  - [ ] `grafana.corporate-intel.com` → `api.corporate-intel.com`
  - [ ] `storage.corporate-intel.com` → `api.corporate-intel.com`

- [ ] **DNS Propagation Verified**
  - [ ] TTL set to 300 seconds (5 min) for initial deployment
  - [ ] Records propagated globally (check: https://dnschecker.org)

**Validation Command:**
```bash
# Verify DNS resolution
dig api.corporate-intel.com +short
nslookup api.corporate-intel.com
host api.corporate-intel.com
```

#### SSL/TLS Certificates

- [ ] **Certificates Obtained**
  - [ ] Primary domain: `api.corporate-intel.com`
  - [ ] Additional domains: `www.corporate-intel.com` (if needed)
  - [ ] Wildcard cert: `*.corporate-intel.com` (recommended)
  - [ ] Certificate authority: Let's Encrypt / DigiCert / Corporate CA

- [ ] **Certificates Installed**
  - [ ] Certificate files in `/etc/letsencrypt/live/` or `/etc/ssl/`
  - [ ] Nginx/Apache configured with cert paths
  - [ ] Intermediate certificates included
  - [ ] Private key secured (600 permissions)

- [ ] **Auto-Renewal Configured**
  - [ ] Certbot cron job scheduled
  - [ ] Renewal tested successfully
  - [ ] Email notifications configured

- [ ] **SSL Grade Verified**
  - [ ] Test at: https://www.ssllabs.com/ssltest/
  - [ ] Target Grade: A or A+
  - [ ] TLS 1.2 and 1.3 only (no TLS 1.0/1.1)
  - [ ] Strong cipher suites only
  - [ ] HSTS header enabled

**Validation Command:**
```bash
# Test SSL configuration
openssl s_client -connect api.corporate-intel.com:443 -servername api.corporate-intel.com
# Check certificate expiration
echo | openssl s_client -servername api.corporate-intel.com -connect api.corporate-intel.com:443 2>/dev/null | openssl x509 -noout -dates
```

**Sign-off:** __________ Date: __________

---

### 1.3 Software Installation

**Status:** [ ] Complete
**Owner:** DevOps Team
**Estimated Time:** 30 minutes

- [ ] **Docker Engine**
  - [ ] Version 24.0+ installed
  - [ ] Docker daemon running and enabled
  - [ ] Current user added to docker group
  - [ ] Docker storage driver: overlay2
  - [ ] Log rotation configured

```bash
# Install Docker (Ubuntu)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
# Logout and login for group changes to take effect
```

- [ ] **Docker Compose**
  - [ ] Version 2.20+ installed
  - [ ] `docker-compose` or `docker compose` command available

```bash
# Install Docker Compose (if not included with Docker)
sudo curl -L "https://github.com/docker/compose/releases/download/v2.23.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
docker-compose --version
```

- [ ] **System Utilities**
  - [ ] `curl` installed
  - [ ] `jq` installed (JSON processing)
  - [ ] `git` installed
  - [ ] `htop` or similar installed
  - [ ] `postgresql-client` installed
  - [ ] `redis-tools` installed (optional)
  - [ ] `minio-client` (mc) installed (optional)

```bash
# Install utilities (Ubuntu)
sudo apt update
sudo apt install -y curl jq git htop postgresql-client redis-tools
```

- [ ] **System Configuration**
  - [ ] File descriptors increased: `ulimit -n 65536`
  - [ ] Max user processes increased: `ulimit -u 4096`
  - [ ] Kernel parameters tuned (sysctl)
  - [ ] Swap configured appropriately

```bash
# Add to /etc/security/limits.conf
* soft nofile 65536
* hard nofile 65536
* soft nproc 4096
* hard nproc 4096

# Add to /etc/sysctl.conf
vm.max_map_count=262144
net.core.somaxconn=1024
```

**Validation Command:**
```bash
docker --version
docker-compose --version
ulimit -n
ulimit -u
```

**Sign-off:** __________ Date: __________

---

## 2. Security Configuration

### 2.1 Secrets Management

**Status:** [ ] Complete
**Owner:** Security/DevOps Team
**Estimated Time:** 45 minutes
**Security Score:** 9.2/10 (validated)

- [ ] **Production Secrets Generated**
  - [ ] `SECRET_KEY`: 64-character hex (256-bit)
  - [ ] `POSTGRES_PASSWORD`: 32+ character random string
  - [ ] `REDIS_PASSWORD`: 32+ character random string
  - [ ] `MINIO_ROOT_USER`: Unique username
  - [ ] `MINIO_ROOT_PASSWORD`: 32+ character random string
  - [ ] `GRAFANA_PASSWORD`: 24+ character random string
  - [ ] All passwords meet complexity requirements

```bash
# Generate secure secrets
# SECRET_KEY (64-character hex)
openssl rand -hex 32

# Passwords (32-character base64)
openssl rand -base64 32

# Or use Python
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

- [ ] **Secrets Manager Configured**
  - [ ] HashiCorp Vault configured (recommended) OR
  - [ ] AWS Secrets Manager configured OR
  - [ ] Azure Key Vault configured OR
  - [ ] Google Secret Manager configured
  - [ ] Access policies configured (least privilege)
  - [ ] Audit logging enabled

- [ ] **Secrets Uploaded**
  - [ ] All production secrets uploaded to secrets manager
  - [ ] Secret retrieval tested successfully
  - [ ] Fallback to .env file documented
  - [ ] Emergency access procedure documented

- [ ] **Environment Files Secured**
  - [ ] `.env.production` created with placeholders only
  - [ ] Actual credentials never committed to git
  - [ ] `.gitignore` includes `.env*` patterns
  - [ ] File permissions: `600` (owner read/write only)

**Validation Command:**
```bash
# Verify .env.production has no real secrets
grep -E "CHANGE_ME|REPLACE_WITH" .env.production

# Check file permissions
ls -la .env.production

# Test secret retrieval (example for Vault)
vault kv get secret/corporate-intel/production
```

**Sign-off:** __________ Date: __________

---

### 2.2 External API Keys

**Status:** [ ] Complete
**Owner:** Product/DevOps Team
**Estimated Time:** 30 minutes

- [ ] **Alpha Vantage**
  - [ ] Production API key obtained
  - [ ] Key tested and working
  - [ ] Rate limits documented: 5 req/min (free), 75 req/min (premium)
  - [ ] Fallback behavior configured
  - [ ] Key stored in secrets manager

- [ ] **NewsAPI**
  - [ ] Production API key obtained
  - [ ] Key tested and working
  - [ ] Rate limits documented: 100 req/day (free), unlimited (premium)
  - [ ] Key stored in secrets manager

- [ ] **SEC EDGAR**
  - [ ] User-Agent configured with valid production email
  - [ ] Format: `Corporate Intel/1.0 (production@corporate-intel.com)`
  - [ ] Rate limiting configured: 10 req/sec max
  - [ ] Compliant with SEC guidelines

- [ ] **Sentry (Error Tracking)**
  - [ ] Production project created
  - [ ] DSN obtained
  - [ ] Sample rate configured: 0.1 (10%)
  - [ ] Alert rules configured
  - [ ] Team notifications configured

**Validation Command:**
```bash
# Test Alpha Vantage
curl "https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol=IBM&interval=5min&apikey=YOUR_KEY"

# Test NewsAPI
curl "https://newsapi.org/v2/top-headlines?country=us&apikey=YOUR_KEY"

# Test Sentry
curl -X POST YOUR_SENTRY_DSN -d '{}'
```

**Sign-off:** __________ Date: __________

---

### 2.3 Access Control

**Status:** [ ] Complete
**Owner:** Security Team
**Estimated Time:** 30 minutes

- [ ] **User Accounts**
  - [ ] Service account created: `corporate-intel-app`
  - [ ] SSH key-based authentication configured
  - [ ] Password authentication disabled
  - [ ] Root login disabled
  - [ ] Sudo access restricted to authorized personnel

- [ ] **Database Access**
  - [ ] Production database user created: `intel_prod_user`
  - [ ] Minimal required permissions granted (no SUPERUSER)
  - [ ] Connection limited to localhost/internal network
  - [ ] Password complexity enforced

- [ ] **Team Access**
  - [ ] VPN or bastion host configured
  - [ ] Team members granted appropriate access levels
  - [ ] SSH keys uploaded for authorized users
  - [ ] Access audit log configured

**Validation Command:**
```bash
# Verify SSH configuration
grep -E "PasswordAuthentication|PermitRootLogin" /etc/ssh/sshd_config

# Check database permissions
psql -U intel_prod_user -d corporate_intel_prod -c "\du"
```

**Sign-off:** __________ Date: __________

---

## 3. Database Configuration

### 3.1 PostgreSQL Setup

**Status:** [ ] Complete
**Owner:** Database Team
**Estimated Time:** 45 minutes
**Performance Baseline:** P99: 34.7ms, Cache Hit: 99.2%

- [ ] **Database Created**
  - [ ] Database name: `corporate_intel_prod`
  - [ ] Database user: `intel_prod_user`
  - [ ] User permissions configured (CONNECT, CREATE, SELECT, INSERT, UPDATE, DELETE)
  - [ ] Connection pooling ready (5-20 connections)

- [ ] **Extensions Enabled**
  - [ ] TimescaleDB extension installed
  - [ ] pgvector extension installed
  - [ ] pg_stat_statements enabled (query monitoring)
  - [ ] pg_trgm enabled (trigram search)

```sql
-- Enable extensions
CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

- [ ] **Performance Tuning**
  - [ ] `shared_buffers = 4GB` (25% of RAM for 16GB server)
  - [ ] `effective_cache_size = 12GB` (75% of RAM)
  - [ ] `work_mem = 64MB`
  - [ ] `maintenance_work_mem = 1GB`
  - [ ] `max_connections = 200`
  - [ ] `checkpoint_completion_target = 0.9`
  - [ ] `wal_buffers = 16MB`
  - [ ] `random_page_cost = 1.1` (SSD)

- [ ] **Backup Strategy**
  - [ ] Automated daily backups scheduled (cron or pg_cron)
  - [ ] Backup retention: 30 days
  - [ ] Backup storage: S3/MinIO/NFS
  - [ ] Point-in-time recovery (WAL archiving) enabled
  - [ ] Backup restoration tested successfully

```bash
# Backup script example
pg_dump -U intel_prod_user -d corporate_intel_prod -F c -f /backups/corporate_intel_$(date +%Y%m%d_%H%M%S).backup
```

- [ ] **Monitoring**
  - [ ] PostgreSQL exporter running for Prometheus
  - [ ] Slow query logging enabled (queries > 100ms)
  - [ ] Connection pool metrics tracked
  - [ ] Cache hit ratio monitored (target: >95%)

**Validation Command:**
```bash
# Test database connection
psql -U intel_prod_user -d corporate_intel_prod -c "SELECT version();"

# Check extensions
psql -U intel_prod_user -d corporate_intel_prod -c "\dx"

# Verify performance settings
psql -U intel_prod_user -d corporate_intel_prod -c "SHOW shared_buffers; SHOW effective_cache_size;"
```

**Sign-off:** __________ Date: __________

---

### 3.2 Database Migrations

**Status:** [ ] Complete
**Owner:** Development/Database Team
**Estimated Time:** 30 minutes

- [ ] **Migration Files Validated**
  - [ ] All migration files present in `alembic/versions/`
  - [ ] Migration history consistent
  - [ ] No migration conflicts
  - [ ] Rollback scripts tested

- [ ] **Pre-Migration Checklist**
  - [ ] Database backup completed (see 3.1)
  - [ ] Migration dry-run successful
  - [ ] Estimated execution time documented: _____ minutes
  - [ ] Downtime window scheduled (if applicable)

- [ ] **Migration Execution**
  - [ ] Migrations applied successfully
  - [ ] Schema version verified
  - [ ] Data integrity checks passed
  - [ ] Indexes created successfully

```bash
# Run migrations
docker-compose -f docker-compose.prod.yml exec api alembic upgrade head

# Verify migration status
docker-compose -f docker-compose.prod.yml exec api alembic current
```

**Validation Command:**
```bash
# Check table count
psql -U intel_prod_user -d corporate_intel_prod -c "\dt"

# Verify indexes
psql -U intel_prod_user -d corporate_intel_prod -c "SELECT tablename, indexname FROM pg_indexes WHERE schemaname = 'public';"

# Check data integrity
psql -U intel_prod_user -d corporate_intel_prod -c "SELECT COUNT(*) FROM companies;"
```

**Sign-off:** __________ Date: __________

---

## 4. Services Configuration

### 4.1 Redis Cache

**Status:** [ ] Complete
**Owner:** DevOps Team
**Estimated Time:** 15 minutes

- [ ] **Redis Configured**
  - [ ] Password authentication enabled
  - [ ] Persistence enabled (appendonly yes)
  - [ ] Max memory: 2GB
  - [ ] Eviction policy: `allkeys-lru`
  - [ ] Listen on localhost only (127.0.0.1)

- [ ] **Monitoring**
  - [ ] Redis exporter running for Prometheus
  - [ ] Hit rate monitored (target: >95%)
  - [ ] Memory usage tracked

**Validation Command:**
```bash
# Test Redis connection
docker-compose -f docker-compose.prod.yml exec redis redis-cli -a $REDIS_PASSWORD ping

# Check Redis info
docker-compose -f docker-compose.prod.yml exec redis redis-cli -a $REDIS_PASSWORD INFO
```

**Sign-off:** __________ Date: __________

---

### 4.2 MinIO Object Storage

**Status:** [ ] Complete
**Owner:** DevOps Team
**Estimated Time:** 20 minutes

- [ ] **MinIO Configured**
  - [ ] Root credentials set
  - [ ] Browser console accessible (restricted IPs)
  - [ ] API endpoint configured
  - [ ] SSL/TLS enabled (if applicable)

- [ ] **Buckets Created**
  - [ ] `prod-corporate-documents` bucket
  - [ ] `prod-analysis-reports` bucket
  - [ ] Bucket policies configured (private)
  - [ ] Versioning enabled
  - [ ] Lifecycle policies configured (optional)

- [ ] **Backup**
  - [ ] MinIO data volume backup configured
  - [ ] Retention policy: 30 days

**Validation Command:**
```bash
# Test MinIO health
curl -f http://localhost:9000/minio/health/live

# List buckets (using mc client)
mc alias set prod-minio http://localhost:9000 $MINIO_ROOT_USER $MINIO_ROOT_PASSWORD
mc ls prod-minio
```

**Sign-off:** __________ Date: __________

---

## 5. Application Deployment

### 5.1 Docker Images

**Status:** [ ] Complete
**Owner:** DevOps Team
**Estimated Time:** 30 minutes

- [ ] **Images Built**
  - [ ] Production image built: `corporate-intel:v1.0.0`
  - [ ] Image tagged with git SHA: `corporate-intel:$(git rev-parse --short HEAD)`
  - [ ] Image scanned for vulnerabilities (0 critical, 0 high)
  - [ ] Image size optimized (<500MB)
  - [ ] Multi-stage build used

```bash
# Build production image
docker build -t corporate-intel:v1.0.0 -f Dockerfile.prod .

# Tag with git SHA
docker tag corporate-intel:v1.0.0 corporate-intel:$(git rev-parse --short HEAD)

# Scan for vulnerabilities
docker scan corporate-intel:v1.0.0
```

- [ ] **Images Pushed**
  - [ ] Images pushed to registry (Docker Hub / GHCR / ECR)
  - [ ] Registry authentication configured
  - [ ] Image pull secrets configured (if private registry)

```bash
# Push to registry
docker push corporate-intel:v1.0.0
```

**Validation Command:**
```bash
# Verify image
docker images | grep corporate-intel

# Test image locally
docker run --rm corporate-intel:v1.0.0 python --version
```

**Sign-off:** __________ Date: __________

---

### 5.2 Docker Compose Deployment

**Status:** [ ] Complete
**Owner:** DevOps Team
**Estimated Time:** 45 minutes

- [ ] **Configuration Files**
  - [ ] `docker-compose.prod.yml` reviewed and validated
  - [ ] `.env.production` configured with production values
  - [ ] Volume mounts configured correctly
  - [ ] Network configuration verified
  - [ ] Resource limits defined (CPU, memory)

- [ ] **Services Started**
  - [ ] PostgreSQL container running and healthy
  - [ ] Redis container running and healthy
  - [ ] MinIO container running and healthy
  - [ ] API container running and healthy
  - [ ] Prometheus container running
  - [ ] Grafana container running
  - [ ] Jaeger container running
  - [ ] Nginx container running (if applicable)

```bash
# Start all services
docker-compose -f docker-compose.prod.yml up -d

# Check service status
docker-compose -f docker-compose.prod.yml ps

# Check logs
docker-compose -f docker-compose.prod.yml logs -f --tail=100
```

- [ ] **Health Checks Passing**
  - [ ] All containers report healthy status
  - [ ] No restart loops detected
  - [ ] Resource usage within normal limits

**Validation Command:**
```bash
# Check container health
docker-compose -f docker-compose.prod.yml ps

# Verify health endpoints
curl -f http://localhost:8000/health
curl -f http://localhost:8000/api/v1/health
```

**Sign-off:** __________ Date: __________

---

## 6. Monitoring and Observability

### 6.1 Prometheus

**Status:** [ ] Complete
**Owner:** DevOps/SRE Team
**Estimated Time:** 30 minutes

- [ ] **Configuration**
  - [ ] Scrape targets configured (API, Postgres, Redis, Node)
  - [ ] Scrape interval: 15s
  - [ ] Storage retention: 30 days
  - [ ] Alert rules created
  - [ ] AlertManager configured (if applicable)

- [ ] **Exporters Running**
  - [ ] PostgreSQL exporter (port 9187)
  - [ ] Redis exporter (port 9121)
  - [ ] Node exporter (port 9100)
  - [ ] cAdvisor (port 8080)

**Validation Command:**
```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Test query
curl 'http://localhost:9090/api/v1/query?query=up'
```

**Sign-off:** __________ Date: __________

---

### 6.2 Grafana

**Status:** [ ] Complete
**Owner:** DevOps/SRE Team
**Estimated Time:** 30 minutes

- [ ] **Setup**
  - [ ] Admin password changed from default
  - [ ] Prometheus data source configured
  - [ ] SSL/TLS enabled
  - [ ] Alert notification channels configured (email, Slack, PagerDuty)

- [ ] **Dashboards Imported**
  - [ ] Application overview dashboard
  - [ ] Database performance dashboard
  - [ ] Infrastructure metrics dashboard
  - [ ] API performance dashboard
  - [ ] Business KPI dashboard

**Validation Command:**
```bash
# Test Grafana access
curl -f http://localhost:3000/api/health

# Login and verify dashboards at: http://localhost:3000
```

**Sign-off:** __________ Date: __________

---

### 6.3 Distributed Tracing (Jaeger)

**Status:** [ ] Complete
**Owner:** DevOps Team
**Estimated Time:** 15 minutes

- [ ] **Configuration**
  - [ ] OTLP endpoint accessible (port 4317)
  - [ ] Sample rate configured: 0.1 (10%)
  - [ ] Storage configured (Badger or Elasticsearch)
  - [ ] UI accessible (port 16686)

**Validation Command:**
```bash
# Test Jaeger health
curl -f http://localhost:16686

# Check for traces in UI
```

**Sign-off:** __________ Date: __________

---

### 6.4 Logging

**Status:** [ ] Complete
**Owner:** DevOps Team
**Estimated Time:** 20 minutes

- [ ] **Log Configuration**
  - [ ] Docker logs driver: json-file
  - [ ] Log rotation configured (max-size: 10m, max-file: 5)
  - [ ] Log level: WARNING (production)
  - [ ] Structured logging enabled
  - [ ] Sensitive data redacted

- [ ] **Log Aggregation (Optional)**
  - [ ] Loki / ELK / Splunk configured
  - [ ] Logs flowing to central system
  - [ ] Log retention: 30 days

**Validation Command:**
```bash
# Check log configuration
docker inspect corporate-intel-api | jq '.[0].HostConfig.LogConfig'

# View recent logs
docker-compose -f docker-compose.prod.yml logs --tail=100 api
```

**Sign-off:** __________ Date: __________

---

## 7. Testing and Validation

### 7.1 Smoke Tests

**Status:** [ ] Complete
**Owner:** QA/DevOps Team
**Estimated Time:** 30 minutes

Run post-deployment smoke tests to verify all critical functionality:

- [ ] **Health Endpoints**
  - [ ] `/health` returns 200 OK
  - [ ] `/health/ping` returns 200 OK
  - [ ] `/api/v1/health` returns detailed status

```bash
curl -f https://api.corporate-intel.com/health
curl -f https://api.corporate-intel.com/health/ping
curl -f https://api.corporate-intel.com/api/v1/health
```

- [ ] **API Endpoints**
  - [ ] `/api/v1/companies` returns company list
  - [ ] `/api/v1/companies/{ticker}` returns company details
  - [ ] `/api/v1/financial/metrics` returns financial data
  - [ ] Authentication working (JWT tokens)

```bash
# Test companies endpoint
curl https://api.corporate-intel.com/api/v1/companies?limit=5

# Test ticker lookup
curl https://api.corporate-intel.com/api/v1/companies/AAPL
```

- [ ] **Database Connectivity**
  - [ ] Database queries successful
  - [ ] Connection pool healthy
  - [ ] Indexes being used

- [ ] **Cache Operations**
  - [ ] Redis connectivity verified
  - [ ] Cache hits occurring
  - [ ] Cache eviction working

- [ ] **Object Storage**
  - [ ] MinIO accessible
  - [ ] File upload successful
  - [ ] File retrieval successful

**Validation Script:**
```bash
# Run comprehensive smoke tests
./tests/integration/smoke-tests.sh production
```

**Sign-off:** __________ Date: __________

---

### 7.2 Performance Validation

**Status:** [ ] Complete
**Owner:** Performance/SRE Team
**Estimated Time:** 45 minutes
**Performance Baseline:** P99: 32ms, QPS: 27.3

- [ ] **Load Testing**
  - [ ] 50 concurrent users tested
  - [ ] P95 latency < 100ms ✅ Baseline: 18.93ms
  - [ ] P99 latency < 200ms ✅ Baseline: 32.14ms
  - [ ] Success rate > 99.9% ✅ Baseline: 100%
  - [ ] No errors under load

```bash
# Run load tests
k6 run --vus 50 --duration 5m tests/performance/k6-script.js

# Or use custom load test
python scripts/performance_baseline.py --target production --users 50 --duration 300
```

- [ ] **Resource Utilization**
  - [ ] CPU usage < 70% under load ✅ Baseline: 35%
  - [ ] Memory usage < 80% ✅ Baseline: 24%
  - [ ] Disk I/O healthy
  - [ ] Network bandwidth sufficient

**Sign-off:** __________ Date: __________

---

### 7.3 Security Validation

**Status:** [ ] Complete
**Owner:** Security Team
**Estimated Time:** 45 minutes
**Security Score:** 9.2/10 (validated)

- [ ] **Security Scan**
  - [ ] No critical vulnerabilities (0 found)
  - [ ] No high vulnerabilities (0 found)
  - [ ] SSL grade A or A+ verified
  - [ ] Security headers validated
  - [ ] OWASP Top 10 checks passed

```bash
# Run security scan
docker scan corporate-intel:v1.0.0

# Test SSL
curl -I https://api.corporate-intel.com | grep -E "Strict-Transport|X-Frame|X-Content"

# SSL Labs test
https://www.ssllabs.com/ssltest/analyze.html?d=api.corporate-intel.com
```

- [ ] **Authentication Testing**
  - [ ] JWT authentication working
  - [ ] Invalid tokens rejected
  - [ ] Token expiration enforced
  - [ ] Rate limiting active

- [ ] **HTTPS Enforcement**
  - [ ] HTTP redirects to HTTPS
  - [ ] HSTS header present
  - [ ] Certificate valid

**Validation Result:** See `/docs/security_validation_day1_results.json`

**Sign-off:** __________ Date: __________

---

## 8. Documentation

### 8.1 Deployment Documentation

**Status:** [ ] Complete
**Owner:** Technical Lead
**Estimated Time:** 30 minutes

- [ ] **Runbooks Created**
  - [ ] Deployment procedures documented
  - [ ] Rollback procedures documented
  - [ ] Common operations documented
  - [ ] Troubleshooting guide available

- [ ] **Architecture Documentation**
  - [ ] System architecture diagram updated
  - [ ] Network diagram created
  - [ ] Database schema documented
  - [ ] API documentation current

- [ ] **Operational Documentation**
  - [ ] Monitoring guide created
  - [ ] Alert response procedures documented
  - [ ] Backup and restore procedures documented
  - [ ] Disaster recovery plan documented

**Reference Documents:**
- `/docs/deployment/production-deployment-runbook.md`
- `/docs/deployment/production-rollback-plan.md`
- `/docs/deployment/production-smoke-tests.md`

**Sign-off:** __________ Date: __________

---

### 8.2 API Documentation

**Status:** [ ] Complete
**Owner:** Development Team
**Estimated Time:** 20 minutes

- [ ] **OpenAPI/Swagger**
  - [ ] API docs accessible at `/docs`
  - [ ] All endpoints documented
  - [ ] Request/response schemas defined
  - [ ] Authentication flow documented
  - [ ] Examples provided

**Validation:**
```bash
curl https://api.corporate-intel.com/docs
curl https://api.corporate-intel.com/openapi.json
```

**Sign-off:** __________ Date: __________

---

## 9. Team Readiness

### 9.1 Access and Permissions

**Status:** [ ] Complete
**Owner:** Security/HR Team
**Estimated Time:** 30 minutes

- [ ] **Team Access Granted**
  - [ ] DevOps team: Server SSH access
  - [ ] Development team: VPN/bastion access
  - [ ] SRE team: Monitoring dashboards access
  - [ ] QA team: API access for testing
  - [ ] Management: Read-only monitoring access

- [ ] **On-Call Rotation**
  - [ ] On-call schedule created
  - [ ] PagerDuty/Opsgenie configured
  - [ ] Escalation procedures defined
  - [ ] Emergency contacts updated

**Sign-off:** __________ Date: __________

---

### 9.2 Training and Communication

**Status:** [ ] Complete
**Owner:** Team Lead
**Estimated Time:** 1 hour

- [ ] **Training Completed**
  - [ ] Team trained on deployment procedures
  - [ ] Team trained on monitoring tools
  - [ ] Team trained on incident response
  - [ ] Team trained on rollback procedures

- [ ] **Communication Plan**
  - [ ] Deployment schedule communicated to stakeholders
  - [ ] Maintenance window announced (if applicable)
  - [ ] Status page updated
  - [ ] Customer communication prepared (if applicable)

**Sign-off:** __________ Date: __________

---

## 10. Final Pre-Deployment Verification

### 10.1 Deployment Readiness Review

**Status:** [ ] Complete
**Owner:** Technical Lead
**Estimated Time:** 30 minutes

- [ ] **All Checklist Items Completed**
  - [ ] Infrastructure readiness (Section 1)
  - [ ] Security configuration (Section 2)
  - [ ] Database configuration (Section 3)
  - [ ] Services configuration (Section 4)
  - [ ] Application deployment (Section 5)
  - [ ] Monitoring setup (Section 6)
  - [ ] Testing complete (Section 7)
  - [ ] Documentation current (Section 8)
  - [ ] Team ready (Section 9)

- [ ] **Risk Assessment**
  - [ ] All known risks documented
  - [ ] Mitigation strategies in place
  - [ ] Rollback plan tested
  - [ ] Incident response ready

- [ ] **Performance Validation**
  - [ ] Performance baseline: 9.2/10 ✅
  - [ ] P99 latency: 32.14ms (<100ms target) ✅
  - [ ] Cache hit ratio: 99.2% (>95% target) ✅
  - [ ] Throughput: 27.3 QPS (>20 QPS target) ✅

- [ ] **Security Validation**
  - [ ] Security score: 9.2/10 ✅
  - [ ] Zero critical vulnerabilities ✅
  - [ ] Zero high vulnerabilities ✅
  - [ ] SSL grade A+ ✅

**Sign-off:** __________ Date: __________

---

## 11. Go/No-Go Decision

### 11.1 Deployment Approval

**Deployment Window:** _________________ (Date/Time)

**Go/No-Go Criteria:**

| Criteria | Status | Approver | Date |
|----------|--------|----------|------|
| Infrastructure Ready | [ ] Go [ ] No-Go | __________ | _____ |
| Security Validated | [ ] Go [ ] No-Go | __________ | _____ |
| Performance Acceptable | [ ] Go [ ] No-Go | __________ | _____ |
| Tests Passed | [ ] Go [ ] No-Go | __________ | _____ |
| Team Ready | [ ] Go [ ] No-Go | __________ | _____ |
| Documentation Complete | [ ] Go [ ] No-Go | __________ | _____ |
| Rollback Plan Ready | [ ] Go [ ] No-Go | __________ | _____ |

**Final Decision:**

☐ **GO** - Proceed with production deployment
☐ **NO-GO** - Delay deployment

**Reason (if No-Go):** _________________________________________________

**New Target Date (if No-Go):** _______________________________________

---

### 11.2 Sign-Off

**Technical Lead:** _________________________ Date: _________

**Security Officer:** _________________________ Date: _________

**DevOps Lead:** _________________________ Date: _________

**Product Owner:** _________________________ Date: _________

**Executive Sponsor:** _________________________ Date: _________

---

## 12. Post-Deployment Tasks

**To be completed within 1 hour of deployment:**

- [ ] Verify all services healthy
- [ ] Run smoke tests
- [ ] Check error logs (no critical errors)
- [ ] Monitor performance metrics
- [ ] Verify monitoring dashboards
- [ ] Update deployment log
- [ ] Notify stakeholders of successful deployment
- [ ] Update status page

**To be completed within 24 hours:**

- [ ] Monitor for 24 hours
- [ ] Review error logs
- [ ] Analyze performance trends
- [ ] Customer feedback review
- [ ] Create deployment report
- [ ] Schedule post-mortem (if issues occurred)
- [ ] Update documentation based on learnings

---

## Emergency Contacts

**On-Call Engineer:** Check PagerDuty schedule
**DevOps Lead:** @devops-lead (Slack)
**Database Admin:** @dba-oncall (PagerDuty)
**Security Team:** @security-team (Slack)
**Platform Lead:** @platform-lead (Slack/Phone)

**Escalation Path:**
1. On-Call Engineer (immediate response)
2. DevOps Lead (within 15 minutes)
3. Platform Lead (within 30 minutes)
4. CTO (critical incidents only)

---

## Appendix

### A. Performance Baseline Summary

**Source:** `/docs/PLAN_A_DAY1_PERFORMANCE_BASELINE.md`

- P99 Latency: 32.14ms (68% under target)
- Mean Response Time: 8.42ms (83% under target)
- Database P99: 34.7ms (65% under target)
- Cache Hit Ratio: 99.2% (4.2% above target)
- Throughput: 27.3 QPS (136% of target)
- Success Rate: 100% (perfect)

### B. Security Validation Summary

**Source:** `/docs/security_validation_day1_results.json`

- Overall Score: 9.2/10
- Critical Vulnerabilities: 0
- High Vulnerabilities: 0
- SSL Grade: A+
- OWASP Top 10: All addressed
- Compliance: GDPR, SOC2, NIST aligned

### C. Reference Documentation

- Deployment Runbook: `/docs/deployment/production-deployment-runbook.md`
- Rollback Plan: `/docs/deployment/production-rollback-plan.md`
- Smoke Tests: `/docs/deployment/production-smoke-tests.md`
- Architecture Docs: `/docs/architecture/`
- Security Docs: `/docs/SECURITY_AUDIT_REPORT.md`

---

**Checklist Version:** 2.0.0
**Last Updated:** October 17, 2025
**Next Review:** Before each production deployment
**Maintained By:** DevOps Team

---

**END OF CHECKLIST**
