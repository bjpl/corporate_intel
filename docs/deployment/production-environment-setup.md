# Production Environment Setup Guide

**Corporate Intelligence Platform - Production Deployment**

Version: 1.0.0
Last Updated: 2025-10-17
Status: Production Ready

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Production Architecture](#production-architecture)
4. [Environment Configuration](#environment-configuration)
5. [Secrets Management](#secrets-management)
6. [Docker Compose Configuration](#docker-compose-configuration)
7. [SSL/TLS Setup](#ssltls-setup)
8. [Deployment Procedure](#deployment-procedure)
9. [Health Checks & Validation](#health-checks--validation)
10. [Monitoring & Alerting](#monitoring--alerting)
11. [Backup & Disaster Recovery](#backup--disaster-recovery)
12. [Security Hardening](#security-hardening)
13. [Troubleshooting](#troubleshooting)
14. [Environment Comparison](#environment-comparison)

---

## Overview

This guide provides comprehensive instructions for deploying the Corporate Intelligence Platform to a production environment. The production setup includes:

- High-availability PostgreSQL with TimescaleDB for time-series data
- Redis cluster for distributed caching and session management
- MinIO for S3-compatible object storage
- Nginx reverse proxy with SSL/TLS termination
- Complete observability stack (Prometheus, Grafana, Jaeger)
- Automated backups and disaster recovery
- Security hardening and compliance features

### Production vs Staging Differences

| Feature | Staging | Production |
|---------|---------|------------|
| SSL/TLS | Optional | Required |
| Debug Mode | Enabled | Disabled |
| Log Level | DEBUG | WARNING/ERROR |
| Database Pool | 10 connections | 30 connections |
| Redis Memory | 512MB | 4GB |
| API Workers | 2 | 4 |
| Backup Frequency | Daily | Every 2 hours |
| Monitoring Retention | 7 days | 30 days |
| Rate Limiting | Relaxed (100/min) | Strict (60/min) |

---

## Prerequisites

### System Requirements

**Minimum Hardware:**
- CPU: 4 cores (8 recommended)
- RAM: 8GB (16GB recommended)
- Disk: 100GB SSD (500GB recommended)
- Network: 1Gbps

**Software Requirements:**
- Docker Engine 24.0+
- Docker Compose 2.20+
- Python 3.11+
- Git 2.40+
- OpenSSL 3.0+

**Operating System:**
- Ubuntu 22.04 LTS (recommended)
- Debian 12
- RHEL 9 / Rocky Linux 9
- Amazon Linux 2023

### Access Requirements

- [ ] AWS Account with appropriate IAM permissions
- [ ] Domain name with DNS management access
- [ ] SSL certificate (Let's Encrypt or commercial)
- [ ] GitHub Container Registry access (for Docker images)
- [ ] External API keys (Alpha Vantage, NewsAPI, etc.)
- [ ] PagerDuty/Slack webhooks for alerting

### Network Requirements

**Inbound Ports:**
- 80/tcp - HTTP (redirects to HTTPS)
- 443/tcp - HTTPS

**Outbound Ports:**
- 443/tcp - External API calls, package downloads
- 25/tcp or 587/tcp - SMTP for email notifications

---

## Production Architecture

### Service Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Internet (HTTPS)                          │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
              ┌───────────────┐
              │  Nginx Proxy  │  (SSL Termination)
              │   Port 443    │
              └───────┬───────┘
                      │
      ┌───────────────┼───────────────┐
      │               │               │
      ▼               ▼               ▼
┌──────────┐   ┌──────────┐   ┌──────────┐
│   API    │   │ Grafana  │   │  MinIO   │
│ (FastAPI)│   │Dashboard │   │ Console  │
└────┬─────┘   └────┬─────┘   └────┬─────┘
     │              │              │
     │         ┌────┴────┐         │
     │         │         │         │
     ▼         ▼         ▼         ▼
┌─────────────────────────────────────┐
│        Backend Network              │
│  ┌──────────┐  ┌──────────┐        │
│  │PostgreSQL│  │  Redis   │        │
│  │TimescaleDB│ │  Cache  │        │
│  └──────────┘  └──────────┘        │
│                                     │
│  ┌─────────────────────────┐       │
│  │   Monitoring Stack      │       │
│  │ Prometheus | Jaeger     │       │
│  └─────────────────────────┘       │
└─────────────────────────────────────┘
```

### Network Segmentation

**Frontend Network (172.20.1.0/24):**
- Nginx reverse proxy
- API service (exposed via proxy)

**Backend Network (172.20.2.0/24):**
- PostgreSQL database
- Redis cache
- MinIO object storage
- Internal services only

**Monitoring Network (172.20.3.0/24):**
- Prometheus
- Grafana
- Jaeger
- Exporters

---

## Environment Configuration

### Step 1: Copy Production Template

```bash
# Create production configuration directory
mkdir -p config/production

# Copy template
cp config/production/.env.production.template \
   config/production/.env.production

# Set secure permissions
chmod 600 config/production/.env.production
```

### Step 2: Generate Secure Secrets

```bash
# Generate SECRET_KEY (64 characters)
python -c "import secrets; print(secrets.token_urlsafe(64))"

# Generate SESSION_SECRET_KEY (64 characters)
python -c "import secrets; print(secrets.token_urlsafe(64))"

# Generate database password (32 characters)
openssl rand -base64 32

# Generate Redis password (32 characters)
openssl rand -base64 32

# Generate MinIO credentials
openssl rand -base64 32  # Root password
```

### Step 3: Configure Critical Variables

Edit `config/production/.env.production`:

```bash
# Security (MUST REPLACE)
SECRET_KEY=<generated-64-char-key>
SESSION_SECRET_KEY=<generated-64-char-key>

# Database (MUST REPLACE)
POSTGRES_PASSWORD=<generated-password>

# Redis (MUST REPLACE)
REDIS_PASSWORD=<generated-password>

# MinIO (MUST REPLACE)
MINIO_ROOT_PASSWORD=<generated-password>

# Domain Configuration (MUST REPLACE)
DOMAIN_NAME=corporate-intel.company.com
API_DOMAIN=api.corporate-intel.company.com

# External APIs (MUST REPLACE)
ALPHA_VANTAGE_API_KEY=<your-premium-key>
NEWSAPI_KEY=<your-business-key>
SEC_USER_AGENT=Corporate Intel Platform/1.0 (production@company.com)

# Monitoring (MUST REPLACE)
GRAFANA_ADMIN_PASSWORD=<strong-password>
SENTRY_DSN=<your-sentry-dsn>

# Alerting (MUST REPLACE)
SLACK_WEBHOOK_URL=<your-slack-webhook>
PAGERDUTY_SERVICE_KEY=<your-pagerduty-key>
SMTP_PASSWORD=<your-smtp-password>

# AWS Integration (MUST REPLACE)
AWS_ACCESS_KEY_ID=<your-aws-key>
AWS_SECRET_ACCESS_KEY=<your-aws-secret>

# Deployment Metadata
DEPLOYMENT_VERSION=v1.0.0
DEPLOYMENT_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ)
```

---

## Secrets Management

### Option 1: AWS Secrets Manager (Recommended)

**1. Store secrets in AWS:**

```bash
# Create secret
aws secretsmanager create-secret \
  --name corporate-intel-prod-secrets \
  --description "Production secrets for Corporate Intelligence Platform" \
  --secret-string file://config/production/secrets.json \
  --region us-east-1

# Secret rotation configuration
aws secretsmanager rotate-secret \
  --secret-id corporate-intel-prod-secrets \
  --rotation-lambda-arn arn:aws:lambda:us-east-1:xxx:function:rotate-secret \
  --rotation-rules AutomaticallyAfterDays=90
```

**2. Configure application to fetch secrets:**

```python
# In application startup
import boto3
import json

def get_production_secrets():
    client = boto3.client('secretsmanager', region_name='us-east-1')
    response = client.get_secret_value(SecretId='corporate-intel-prod-secrets')
    return json.loads(response['SecretString'])
```

### Option 2: HashiCorp Vault

**1. Store secrets:**

```bash
# Write secrets to Vault
vault kv put secret/corporate-intel/prod \
  db_password="<password>" \
  redis_password="<password>" \
  secret_key="<key>"

# Configure auto-rotation
vault write database/rotate-role/corporate-intel-prod
```

### Option 3: Docker Secrets (Swarm Mode)

```bash
# Create Docker secrets
echo "<db-password>" | docker secret create db_password -
echo "<redis-password>" | docker secret create redis_password -

# Reference in docker-compose.yml
secrets:
  db_password:
    external: true
```

### Secret Rotation Policy

| Secret Type | Rotation Frequency | Method |
|-------------|-------------------|--------|
| API Keys | Every 90 days | Manual via provider dashboard |
| Database Passwords | Every 90 days | Automated via AWS Secrets Manager |
| Redis Passwords | Every 90 days | Automated via AWS Secrets Manager |
| SSL Certificates | Every 60 days | Automated via Let's Encrypt |
| Session Keys | Every 30 days | Automated via deployment |

---

## Docker Compose Configuration

### Production-Specific Settings

**Resource Limits:**

```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 4G
    reservations:
      cpus: '1.0'
      memory: 2G
```

**Restart Policies:**

```yaml
restart: always
deploy:
  restart_policy:
    condition: unless-stopped
    delay: 5s
    max_attempts: 3
```

**Health Checks:**

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 60s
```

### Port Mappings

| Service | Internal Port | External Port | Exposed |
|---------|---------------|---------------|---------|
| Nginx | 80, 443 | 80, 443 | Public |
| API | 8000 | 127.0.0.1:8000 | Localhost only |
| PostgreSQL | 5432 | 127.0.0.1:5432 | Localhost only |
| Redis | 6379 | 127.0.0.1:6379 | Localhost only |
| MinIO | 9000, 9001 | 127.0.0.1:9000-9001 | Localhost only |
| Prometheus | 9090 | 127.0.0.1:9090 | Localhost only |
| Grafana | 3000 | 127.0.0.1:3000 | Localhost only |
| Jaeger UI | 16686 | 127.0.0.1:16686 | Localhost only |

**Security Note:** Only Nginx is exposed publicly. All other services are bound to localhost and accessed via reverse proxy.

### Volume Management

**Persistent Data Volumes:**

```bash
# List production volumes
docker volume ls | grep corporate-intel-.*-prod

# Backup volume
docker run --rm -v corporate-intel-postgres-data-prod:/data \
  -v $(pwd)/backups:/backup alpine \
  tar czf /backup/postgres-$(date +%Y%m%d).tar.gz /data

# Restore volume
docker run --rm -v corporate-intel-postgres-data-prod:/data \
  -v $(pwd)/backups:/backup alpine \
  tar xzf /backup/postgres-20251017.tar.gz -C /
```

---

## SSL/TLS Setup

### Option 1: Let's Encrypt (Automated & Free)

**1. Install Certbot:**

```bash
sudo apt-get update
sudo apt-get install certbot python3-certbot-nginx
```

**2. Obtain Certificate:**

```bash
# Stop nginx if running
docker-compose -f config/production/docker-compose.production.yml stop nginx

# Obtain certificate
sudo certbot certonly --standalone \
  -d corporate-intel.company.com \
  -d api.corporate-intel.company.com \
  -d grafana.corporate-intel.company.com \
  --email ssl-admin@company.com \
  --agree-tos \
  --non-interactive

# Certificates stored at:
# /etc/letsencrypt/live/corporate-intel.company.com/
```

**3. Configure Auto-Renewal:**

```bash
# Test renewal
sudo certbot renew --dry-run

# Add cron job for auto-renewal
sudo crontab -e

# Add this line:
0 3 * * * certbot renew --quiet --deploy-hook "docker-compose -f /path/to/docker-compose.production.yml restart nginx"
```

### Option 2: Commercial Certificate

**1. Generate CSR:**

```bash
openssl req -new -newkey rsa:4096 -nodes \
  -keyout corporate-intel.key \
  -out corporate-intel.csr \
  -subj "/C=US/ST=California/L=San Francisco/O=Company Inc/CN=corporate-intel.company.com"
```

**2. Submit CSR to Certificate Authority**

**3. Install Certificate:**

```bash
# Copy certificates
sudo mkdir -p /etc/letsencrypt/live/corporate-intel.company.com/
sudo cp corporate-intel.crt /etc/letsencrypt/live/corporate-intel.company.com/fullchain.pem
sudo cp corporate-intel.key /etc/letsencrypt/live/corporate-intel.company.com/privkey.pem
sudo cp ca-bundle.crt /etc/letsencrypt/live/corporate-intel.company.com/chain.pem

# Set permissions
sudo chmod 644 /etc/letsencrypt/live/corporate-intel.company.com/*.pem
sudo chmod 600 /etc/letsencrypt/live/corporate-intel.company.com/privkey.pem
```

### SSL Configuration Verification

```bash
# Test SSL configuration
openssl s_client -connect corporate-intel.company.com:443 -servername corporate-intel.company.com

# Check certificate expiry
openssl x509 -in /etc/letsencrypt/live/corporate-intel.company.com/fullchain.pem \
  -noout -dates

# Test with SSL Labs (external)
# Visit: https://www.ssllabs.com/ssltest/analyze.html?d=corporate-intel.company.com
```

---

## Deployment Procedure

### Pre-Deployment Checklist

- [ ] All environment variables configured in `.env.production`
- [ ] Secrets stored in AWS Secrets Manager or Vault
- [ ] SSL certificates obtained and installed
- [ ] DNS records configured (A, CNAME)
- [ ] Firewall rules configured (ports 80, 443)
- [ ] Docker images built and pushed to registry
- [ ] Database migrations tested in staging
- [ ] Backup procedures tested
- [ ] Monitoring dashboards configured
- [ ] Alert rules configured
- [ ] On-call rotation set up
- [ ] Runbook reviewed by team

### Step-by-Step Deployment

**1. Prepare Host System:**

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install dependencies
sudo apt-get install -y docker.io docker-compose-v2 git curl

# Configure firewall
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# Create directory structure
sudo mkdir -p /opt/corporate-intel
cd /opt/corporate-intel
```

**2. Clone Repository:**

```bash
# Clone from GitHub
git clone https://github.com/company/corporate-intel.git .

# Checkout production tag
git checkout tags/v1.0.0

# Verify integrity
git verify-tag v1.0.0
```

**3. Configure Environment:**

```bash
# Copy production environment file
cp config/production/.env.production.template \
   config/production/.env.production

# Edit with production values
nano config/production/.env.production

# Validate configuration
python scripts/validate-production-config.py
```

**4. Build and Pull Images:**

```bash
# Login to container registry
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Pull production images
docker-compose -f config/production/docker-compose.production.yml \
  --env-file config/production/.env.production \
  pull

# Or build locally (if needed)
docker-compose -f config/production/docker-compose.production.yml \
  --env-file config/production/.env.production \
  build --no-cache
```

**5. Initialize Database:**

```bash
# Start only database first
docker-compose -f config/production/docker-compose.production.yml \
  --env-file config/production/.env.production \
  up -d postgres

# Wait for database to be ready
docker-compose -f config/production/docker-compose.production.yml \
  exec postgres pg_isready -U intel_prod_user

# Run migrations
docker-compose -f config/production/docker-compose.production.yml \
  run --rm api python -m alembic upgrade head
```

**6. Deploy All Services:**

```bash
# Deploy entire stack
docker-compose -f config/production/docker-compose.production.yml \
  --env-file config/production/.env.production \
  up -d

# Verify all services started
docker-compose -f config/production/docker-compose.production.yml ps

# Check logs
docker-compose -f config/production/docker-compose.production.yml logs -f
```

**7. Smoke Tests:**

```bash
# Health check
curl -f https://corporate-intel.company.com/health

# API endpoint
curl -f https://api.corporate-intel.company.com/api/v1/health

# Metrics
curl -f http://localhost:9090/-/healthy

# Verify database connection
docker-compose -f config/production/docker-compose.production.yml \
  exec api python -c "from src.database import engine; print(engine.connect())"
```

---

## Health Checks & Validation

### Service Health Checks

```bash
# Check all services
docker-compose -f config/production/docker-compose.production.yml ps

# Individual service health
docker inspect --format='{{.State.Health.Status}}' corporate-intel-api-prod
docker inspect --format='{{.State.Health.Status}}' corporate-intel-postgres-prod
docker inspect --format='{{.State.Health.Status}}' corporate-intel-redis-prod
```

### Application Health Endpoints

| Endpoint | Purpose | Expected Response |
|----------|---------|-------------------|
| `/health` | Basic liveness | `{"status": "healthy"}` |
| `/health/ready` | Readiness (DB connected) | `{"status": "ready"}` |
| `/health/live` | Kubernetes liveness | `{"status": "live"}` |
| `/metrics` | Prometheus metrics | Metrics in text format |

### Validation Script

```bash
#!/bin/bash
# scripts/validate-production-deployment.sh

echo "Validating production deployment..."

# Check API health
if curl -sf https://corporate-intel.company.com/health > /dev/null; then
  echo "✓ API health check passed"
else
  echo "✗ API health check failed"
  exit 1
fi

# Check database connectivity
if docker-compose exec -T postgres pg_isready -U intel_prod_user; then
  echo "✓ Database connectivity passed"
else
  echo "✗ Database connectivity failed"
  exit 1
fi

# Check Redis connectivity
if docker-compose exec -T redis redis-cli -a $REDIS_PASSWORD ping | grep -q PONG; then
  echo "✓ Redis connectivity passed"
else
  echo "✗ Redis connectivity failed"
  exit 1
fi

# Check SSL certificate
if openssl s_client -connect corporate-intel.company.com:443 \
   -servername corporate-intel.company.com < /dev/null 2>/dev/null | \
   grep -q "Verify return code: 0"; then
  echo "✓ SSL certificate valid"
else
  echo "✗ SSL certificate invalid"
  exit 1
fi

echo "All validation checks passed!"
```

---

## Monitoring & Alerting

### Prometheus Targets

Access Prometheus at `http://localhost:9090/targets`

**Expected Targets:**
- `postgres-exporter` - Database metrics
- `redis-exporter` - Cache metrics
- `node-exporter` - System metrics
- `cadvisor` - Container metrics
- `api` - Application metrics

### Grafana Dashboards

Access Grafana at `https://grafana.corporate-intel.company.com`

**Pre-configured Dashboards:**
1. **System Overview** - CPU, memory, disk, network
2. **Application Metrics** - Request rate, latency, errors
3. **Database Performance** - Query performance, connections, locks
4. **Redis Metrics** - Hit rate, memory usage, commands/sec
5. **Business Metrics** - Data pipeline execution, API usage

### Alert Rules

**Critical Alerts (PagerDuty + Slack):**
- Database connection failures
- API error rate > 1%
- Disk usage > 90%
- Memory usage > 95%
- Certificate expiring < 7 days

**Warning Alerts (Slack only):**
- High API latency (p95 > 1s)
- Database slow queries
- High cache miss rate
- Backup failures

### Alert Configuration

Edit `config/alertmanager.yml`:

```yaml
route:
  group_by: ['alertname', 'severity']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  receiver: 'pagerduty-critical'
  routes:
  - match:
      severity: critical
    receiver: pagerduty-critical
  - match:
      severity: warning
    receiver: slack-warnings

receivers:
- name: 'pagerduty-critical'
  pagerduty_configs:
  - service_key: '<YOUR_PAGERDUTY_KEY>'
  slack_configs:
  - api_url: '<YOUR_SLACK_WEBHOOK>'
    channel: '#critical-alerts'

- name: 'slack-warnings'
  slack_configs:
  - api_url: '<YOUR_SLACK_WEBHOOK>'
    channel: '#production-alerts'
```

---

## Backup & Disaster Recovery

### Automated Backup Schedule

**Backup Frequency:**
- Database: Every 2 hours
- Object storage: Daily
- Application logs: Daily
- Configuration: On every change

### Database Backup

**Script:** `scripts/backup-postgres-production.sh`

```bash
#!/bin/bash

BACKUP_DIR="/backups/postgres"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="corporate_intel_prod_${TIMESTAMP}.sql.gz"

# Create backup
docker-compose -f config/production/docker-compose.production.yml \
  exec -T postgres pg_dump -U intel_prod_user corporate_intel_prod | \
  gzip > "${BACKUP_DIR}/${BACKUP_FILE}"

# Upload to S3
aws s3 cp "${BACKUP_DIR}/${BACKUP_FILE}" \
  s3://corporate-intel-backups-prod/postgres/

# Verify backup
aws s3 ls s3://corporate-intel-backups-prod/postgres/${BACKUP_FILE}

# Cleanup old backups (keep 30 days)
find ${BACKUP_DIR} -name "*.sql.gz" -mtime +30 -delete

# Send success notification
curl -X POST $SLACK_WEBHOOK_URL \
  -H 'Content-Type: application/json' \
  -d "{\"text\": \"✓ Production database backup completed: ${BACKUP_FILE}\"}"
```

**Cron Schedule:**

```cron
# Backup every 2 hours
0 */2 * * * /opt/corporate-intel/scripts/backup-postgres-production.sh

# Weekly full backup
0 2 * * 0 /opt/corporate-intel/scripts/backup-full-production.sh
```

### Restore Procedure

```bash
# Stop application (keep database running)
docker-compose -f config/production/docker-compose.production.yml \
  stop api

# Download backup from S3
aws s3 cp s3://corporate-intel-backups-prod/postgres/backup.sql.gz \
  /tmp/restore.sql.gz

# Restore database
gunzip -c /tmp/restore.sql.gz | \
docker-compose -f config/production/docker-compose.production.yml \
  exec -T postgres psql -U intel_prod_user corporate_intel_prod

# Verify restore
docker-compose -f config/production/docker-compose.production.yml \
  exec postgres psql -U intel_prod_user corporate_intel_prod \
  -c "SELECT COUNT(*) FROM companies;"

# Restart application
docker-compose -f config/production/docker-compose.production.yml \
  start api
```

### Disaster Recovery Runbook

**RTO (Recovery Time Objective):** 60 minutes
**RPO (Recovery Point Objective):** 2 hours

**DR Steps:**

1. **Assess Situation** (5 min)
   - Identify failure type
   - Notify on-call team
   - Create incident in PagerDuty

2. **Activate DR Site** (15 min)
   - Spin up DR infrastructure in us-west-2
   - Update DNS to point to DR site
   - Verify SSL certificates

3. **Restore Data** (30 min)
   - Download latest backup from S3
   - Restore to DR database
   - Verify data integrity

4. **Validate Services** (10 min)
   - Run smoke tests
   - Check all health endpoints
   - Verify monitoring

5. **Communication** (ongoing)
   - Update status page
   - Notify stakeholders
   - Document incident

---

## Security Hardening

### Security Checklist

- [ ] All services run as non-root users
- [ ] Network segmentation configured
- [ ] SSL/TLS enabled with strong ciphers
- [ ] Secrets stored externally (not in env files)
- [ ] Rate limiting enabled
- [ ] CORS properly configured
- [ ] Security headers enabled (HSTS, CSP)
- [ ] Database connections encrypted
- [ ] Regular security scanning enabled
- [ ] Vulnerability patching schedule defined

### Nginx Security Headers

```nginx
# config/nginx-ssl.conf
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';" always;
```

### Database Security

```sql
-- Revoke public schema permissions
REVOKE ALL ON SCHEMA public FROM PUBLIC;

-- Create read-only user for analytics
CREATE ROLE analytics_readonly WITH LOGIN PASSWORD '<strong-password>';
GRANT CONNECT ON DATABASE corporate_intel_prod TO analytics_readonly;
GRANT USAGE ON SCHEMA public TO analytics_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO analytics_readonly;

-- Enable row-level security
ALTER TABLE companies ENABLE ROW LEVEL SECURITY;

-- Create policy
CREATE POLICY company_access_policy ON companies
  FOR SELECT
  USING (organization_id = current_setting('app.current_org_id')::uuid);
```

### Security Scanning

```bash
# Scan Docker images for vulnerabilities
docker scan corporate-intel:latest

# Scan dependencies
pip-audit --requirement requirements.txt

# SAST (Static Application Security Testing)
bandit -r src/

# Network security scan
nmap -sV -sC corporate-intel.company.com
```

---

## Troubleshooting

### Common Issues

#### Issue: API Not Responding

**Symptoms:** Health check returning 502/503

**Diagnosis:**
```bash
# Check API logs
docker-compose -f config/production/docker-compose.production.yml logs api

# Check API container status
docker inspect corporate-intel-api-prod

# Check database connectivity from API
docker-compose -f config/production/docker-compose.production.yml \
  exec api python -c "from src.database import engine; engine.connect()"
```

**Resolution:**
```bash
# Restart API service
docker-compose -f config/production/docker-compose.production.yml restart api

# If persistent, recreate container
docker-compose -f config/production/docker-compose.production.yml \
  up -d --force-recreate api
```

#### Issue: Database Connection Pool Exhausted

**Symptoms:** `FATAL: remaining connection slots are reserved`

**Diagnosis:**
```bash
# Check active connections
docker-compose -f config/production/docker-compose.production.yml \
  exec postgres psql -U intel_prod_user corporate_intel_prod \
  -c "SELECT count(*) FROM pg_stat_activity;"

# Check connection states
docker-compose -f config/production/docker-compose.production.yml \
  exec postgres psql -U intel_prod_user corporate_intel_prod \
  -c "SELECT state, count(*) FROM pg_stat_activity GROUP BY state;"
```

**Resolution:**
```bash
# Terminate idle connections
docker-compose -f config/production/docker-compose.production.yml \
  exec postgres psql -U intel_prod_user corporate_intel_prod \
  -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle' AND state_change < now() - interval '5 minutes';"

# Increase max_connections (if needed)
# Edit postgres environment: POSTGRES_MAX_CONNECTIONS=300
docker-compose -f config/production/docker-compose.production.yml restart postgres
```

#### Issue: High Memory Usage

**Diagnosis:**
```bash
# Check container memory usage
docker stats --no-stream

# Check specific service
docker stats corporate-intel-api-prod --no-stream

# Check heap usage
docker-compose -f config/production/docker-compose.production.yml \
  exec api python -c "import psutil; print(f'Memory: {psutil.virtual_memory().percent}%')"
```

**Resolution:**
```bash
# Restart service to clear memory
docker-compose -f config/production/docker-compose.production.yml restart api

# Adjust memory limits in docker-compose.yml
# deploy.resources.limits.memory: 6G

# Scale API horizontally
docker-compose -f config/production/docker-compose.production.yml \
  up -d --scale api=3
```

### Performance Tuning

**Database Query Optimization:**

```sql
-- Identify slow queries
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 20;

-- Check missing indexes
SELECT schemaname, tablename, attname, n_distinct, correlation
FROM pg_stats
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY n_distinct DESC;
```

**Redis Performance:**

```bash
# Check Redis memory usage
docker-compose -f config/production/docker-compose.production.yml \
  exec redis redis-cli -a $REDIS_PASSWORD INFO memory

# Monitor Redis commands
docker-compose -f config/production/docker-compose.production.yml \
  exec redis redis-cli -a $REDIS_PASSWORD MONITOR

# Check slow log
docker-compose -f config/production/docker-compose.production.yml \
  exec redis redis-cli -a $REDIS_PASSWORD SLOWLOG GET 10
```

---

## Environment Comparison

### Configuration Differences

| Configuration | Development | Staging | Production |
|---------------|-------------|---------|------------|
| **Environment** |
| DEBUG | true | true | false |
| LOG_LEVEL | DEBUG | DEBUG | WARNING |
| SSL/TLS | false | false | true |
| SECURE_COOKIES | false | false | true |
| **Database** |
| POSTGRES_HOST | localhost | postgres | postgres |
| DB_POOL_SIZE | 5 | 10 | 30 |
| DB_MAX_OVERFLOW | 2 | 5 | 20 |
| **Redis** |
| REDIS_MAXMEMORY | 256mb | 512mb | 4gb |
| REDIS_MAX_CONNECTIONS | 20 | 50 | 100 |
| **API** |
| API_WORKERS | 1 | 2 | 4 |
| API_TIMEOUT | 30 | 60 | 120 |
| RATE_LIMIT_PER_MINUTE | 1000 | 100 | 60 |
| **Monitoring** |
| PROMETHEUS_RETENTION | 7d | 7d | 30d |
| SENTRY_SAMPLE_RATE | 1.0 | 0.5 | 0.1 |
| OTEL_TRACES_ENABLED | false | true | true |
| **Backups** |
| BACKUP_ENABLED | false | true | true |
| BACKUP_SCHEDULE | - | 0 2 * * * | 0 */2 * * * |
| BACKUP_RETENTION_DAYS | - | 7 | 30 |

### Migration Path

**Development → Staging:**
1. Enable monitoring and logging
2. Use production-like data volumes
3. Test backup/restore procedures
4. Enable rate limiting
5. Test SSL/TLS configuration

**Staging → Production:**
1. Replace all credentials with production values
2. Enable strict security settings
3. Configure external monitoring services
4. Set up automated backups to S3
5. Enable alerting and on-call rotation
6. Perform security audit
7. Load test with production-level traffic

---

## Appendix

### Useful Commands

```bash
# View all production containers
docker ps --filter "name=corporate-intel-*-prod"

# View logs for all services
docker-compose -f config/production/docker-compose.production.yml logs -f

# Restart specific service
docker-compose -f config/production/docker-compose.production.yml restart api

# Scale API service
docker-compose -f config/production/docker-compose.production.yml up -d --scale api=3

# Execute database query
docker-compose -f config/production/docker-compose.production.yml \
  exec postgres psql -U intel_prod_user corporate_intel_prod -c "SELECT version();"

# View Prometheus targets
curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job: .labels.job, health: .health}'

# Export metrics
curl -s http://localhost:8000/metrics > metrics-$(date +%Y%m%d).txt
```

### Reference Documentation

- [Docker Compose Reference](./DOCKER_COMPOSE_REFERENCE.md)
- [Deployment Runbook](./DEPLOYMENT_RUNBOOKS.md)
- [Security Hardening Guide](../security/SECURITY_HARDENING.md)
- [Monitoring Setup](../monitoring/MONITORING_SETUP.md)
- [Disaster Recovery](./DISASTER_RECOVERY.md)

### Support Contacts

- **On-Call Engineer:** oncall@company.com
- **DevOps Team:** devops@company.com
- **Security Team:** security@company.com
- **PagerDuty:** https://company.pagerduty.com
- **Status Page:** https://status.corporate-intel.company.com

---

**Document Version:** 1.0.0
**Last Updated:** 2025-10-17
**Next Review:** 2025-11-17
**Owner:** DevOps Team
