# Staging Environment Configuration Checklist

**Purpose:** Ensure all staging environment requirements are met before deployment
**Version:** 1.0.0
**Last Updated:** 2025-10-02

---

## Pre-Deployment Requirements

### 1. Infrastructure Setup

#### Server Provisioning
- [ ] **Application Server**
  - [ ] 4 CPU cores minimum
  - [ ] 8 GB RAM minimum (16 GB recommended)
  - [ ] 50 GB SSD storage
  - [ ] Ubuntu 22.04 LTS or similar
  - [ ] Static IP address assigned

- [ ] **Database Server** (can be same as app server for staging)
  - [ ] 4 CPU cores
  - [ ] 8 GB RAM minimum
  - [ ] 100 GB SSD storage with auto-expansion
  - [ ] Backup storage configured

#### Network Configuration
- [ ] **Firewall Rules Configured**
  - [ ] Port 8000 (API) - restricted to authorized IPs
  - [ ] Port 5432 (PostgreSQL) - internal only
  - [ ] Port 6379 (Redis) - internal only
  - [ ] Port 9000 (MinIO API) - internal only
  - [ ] Port 9001 (MinIO Console) - restricted access
  - [ ] Port 16686 (Jaeger UI) - restricted access
  - [ ] Port 9090 (Prometheus) - restricted access
  - [ ] Port 3000 (Grafana) - restricted access
  - [ ] SSH (22) - restricted to bastion host

- [ ] **DNS Records Configured**
  - [ ] staging-api.corporate-intel.example.com → Application server IP
  - [ ] staging-storage.corporate-intel.example.com → MinIO endpoint
  - [ ] staging-monitor.corporate-intel.example.com → Grafana endpoint

- [ ] **SSL/TLS Certificates**
  - [ ] Certificates obtained (Let's Encrypt or corporate CA)
  - [ ] Certificates installed and configured
  - [ ] Auto-renewal configured
  - [ ] Certificate expiration monitoring setup

---

### 2. Software Installation

#### Required Software
- [ ] **Docker Engine**
  - [ ] Version 24.0+ installed
  - [ ] Docker daemon running
  - [ ] Current user added to docker group
  - [ ] Docker socket permissions verified

- [ ] **Docker Compose**
  - [ ] Version 2.20+ installed
  - [ ] docker-compose command available
  - [ ] Compose file syntax validated

- [ ] **System Utilities**
  - [ ] curl (for health checks)
  - [ ] jq (for JSON processing)
  - [ ] git (for code deployment)
  - [ ] PostgreSQL client tools (psql)
  - [ ] MinIO client (mc) - optional but recommended

- [ ] **Monitoring Tools**
  - [ ] htop or similar resource monitor
  - [ ] netdata or prometheus node exporter
  - [ ] Log rotation configured (logrotate)

#### System Configuration
- [ ] **System Limits**
  - [ ] File descriptors increased (ulimit -n 65536)
  - [ ] Max user processes increased
  - [ ] Kernel parameters tuned for containers

- [ ] **Storage Configuration**
  - [ ] Docker storage driver configured (overlay2)
  - [ ] Volume mounts created
  - [ ] Backup storage mounted

---

### 3. Security Configuration

#### Access Control
- [ ] **User Accounts**
  - [ ] Service account created for application
  - [ ] SSH key-based authentication only
  - [ ] Root login disabled
  - [ ] sudo access restricted

- [ ] **Secrets Management**
  - [ ] Secrets manager configured (AWS Secrets Manager, Vault, etc.)
  - [ ] Database passwords generated (minimum 24 characters)
  - [ ] Redis password generated
  - [ ] MinIO credentials generated
  - [ ] Application secret key generated (64+ characters)
  - [ ] API keys obtained and stored securely

- [ ] **Network Security**
  - [ ] VPN or bastion host configured
  - [ ] Security groups/firewall rules validated
  - [ ] DDoS protection enabled (if applicable)
  - [ ] Rate limiting configured

#### Security Scanning
- [ ] **Container Security**
  - [ ] Docker image vulnerability scan completed
  - [ ] No critical vulnerabilities found
  - [ ] Base image updated to latest
  - [ ] Non-root user configured in containers

- [ ] **Dependency Scanning**
  - [ ] Python dependencies scanned (pip-audit)
  - [ ] No known vulnerabilities in dependencies
  - [ ] Dependency versions pinned

---

### 4. Environment Variables

Copy `.env.staging` and verify all values:

#### Required Environment Variables
- [ ] **Environment Settings**
  ```bash
  ENVIRONMENT=staging
  DEBUG=true  # For staging only
  LOG_LEVEL=DEBUG
  ```

- [ ] **Database Configuration**
  ```bash
  POSTGRES_HOST=postgres
  POSTGRES_PORT=5432
  POSTGRES_USER=intel_staging_user
  POSTGRES_PASSWORD=<SECURE_PASSWORD>
  POSTGRES_DB=corporate_intel_staging
  ```

- [ ] **Redis Configuration**
  ```bash
  REDIS_HOST=redis
  REDIS_PORT=6379
  REDIS_PASSWORD=<SECURE_PASSWORD>
  ```

- [ ] **MinIO Configuration**
  ```bash
  MINIO_ENDPOINT=minio:9000
  MINIO_ACCESS_KEY=intel_staging_admin
  MINIO_SECRET_KEY=<SECURE_SECRET>
  ```

- [ ] **Security Keys**
  ```bash
  SECRET_KEY=<64_CHAR_RANDOM_STRING>
  ```

- [ ] **External API Keys**
  ```bash
  ALPHA_VANTAGE_API_KEY=<YOUR_KEY>
  NEWSAPI_KEY=<YOUR_KEY>
  SEC_USER_AGENT=Corporate Intel/1.0 (staging@example.com)
  ```

- [ ] **Observability**
  ```bash
  OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317
  SENTRY_DSN=<YOUR_DSN>
  SENTRY_ENVIRONMENT=staging
  ```

#### Variable Validation
- [ ] All required variables present
- [ ] No default/placeholder values in production settings
- [ ] Passwords meet complexity requirements
- [ ] API keys validated and active
- [ ] Email addresses updated with valid staging contacts

---

### 5. External Services

#### API Keys and Credentials
- [ ] **Alpha Vantage**
  - [ ] API key obtained (https://www.alphavantage.co/support/#api-key)
  - [ ] Key tested and working
  - [ ] Rate limits understood (5 req/min for free tier)

- [ ] **NewsAPI**
  - [ ] API key obtained (https://newsapi.org/register)
  - [ ] Key tested and working
  - [ ] Rate limits understood

- [ ] **SEC EDGAR**
  - [ ] User-Agent configured with valid email
  - [ ] Rate limiting implemented (10 req/sec max)

- [ ] **Sentry** (Optional)
  - [ ] Project created for staging
  - [ ] DSN configured
  - [ ] Sample rate configured
  - [ ] Alert rules configured

#### Third-Party Integrations
- [ ] **Email Service** (if applicable)
  - [ ] SMTP credentials configured
  - [ ] Test emails sent successfully

- [ ] **Monitoring Services**
  - [ ] Prometheus remote write configured (if applicable)
  - [ ] Grafana Cloud configured (if applicable)

---

### 6. Database Setup

#### PostgreSQL Configuration
- [ ] **Database Created**
  - [ ] Database user created with appropriate permissions
  - [ ] Database created: `corporate_intel_staging`
  - [ ] TimescaleDB extension enabled
  - [ ] pgvector extension enabled
  - [ ] Connection pooling configured

- [ ] **Performance Settings**
  - [ ] shared_buffers = 2GB (25% of RAM)
  - [ ] effective_cache_size = 6GB (75% of RAM)
  - [ ] work_mem = 50MB
  - [ ] maintenance_work_mem = 512MB
  - [ ] max_connections = 100

- [ ] **Backup Strategy**
  - [ ] Automated daily backups configured
  - [ ] Backup retention policy: 7 days
  - [ ] Backup restoration tested
  - [ ] Point-in-time recovery configured (WAL archiving)

#### Database Migrations
- [ ] **Migration Files**
  - [ ] All migration files present in `alembic/versions/`
  - [ ] Migration history validated
  - [ ] No migration conflicts

- [ ] **Migration Testing**
  - [ ] Migrations tested in development
  - [ ] Rollback procedures tested
  - [ ] Migration execution time estimated

---

### 7. Storage Configuration

#### MinIO Object Storage
- [ ] **Buckets Created**
  - [ ] `staging-documents` bucket
  - [ ] `staging-reports` bucket
  - [ ] Bucket policies configured
  - [ ] Versioning enabled

- [ ] **Access Configuration**
  - [ ] Access credentials secured
  - [ ] Public access restricted
  - [ ] CORS policies configured
  - [ ] Lifecycle policies configured (optional)

- [ ] **Backup**
  - [ ] MinIO data volume backup configured
  - [ ] Retention policy defined

---

### 8. Monitoring and Observability

#### Prometheus
- [ ] **Configuration**
  - [ ] Scrape targets configured
  - [ ] Alert rules created
  - [ ] Storage retention configured (15 days for staging)

- [ ] **Exporters Configured**
  - [ ] PostgreSQL exporter
  - [ ] Redis exporter
  - [ ] Node exporter
  - [ ] Container metrics

#### Grafana
- [ ] **Setup**
  - [ ] Admin password changed from default
  - [ ] Prometheus data source configured
  - [ ] Alert notification channels configured
  - [ ] SSL/TLS enabled for web interface

- [ ] **Dashboards Imported**
  - [ ] Application overview dashboard
  - [ ] Database performance dashboard
  - [ ] Infrastructure metrics dashboard
  - [ ] API performance dashboard

#### Jaeger (Distributed Tracing)
- [ ] **Configuration**
  - [ ] OTLP endpoint accessible
  - [ ] Sample rate configured
  - [ ] Storage backend configured
  - [ ] UI accessible

#### Logging
- [ ] **Log Aggregation**
  - [ ] Docker logs configured with json-file driver
  - [ ] Log rotation configured
  - [ ] Log retention: 7 days
  - [ ] Centralized logging (optional: Loki, ELK)

- [ ] **Application Logging**
  - [ ] Log level set to DEBUG for staging
  - [ ] Structured logging configured
  - [ ] Sensitive data redacted from logs

---

### 9. Application Configuration

#### API Configuration
- [ ] **CORS Settings**
  - [ ] Allowed origins configured
  - [ ] Allowed methods validated
  - [ ] Allowed headers configured

- [ ] **Rate Limiting**
  - [ ] Rate limits configured (100 req/min for staging)
  - [ ] Rate limit storage (Redis) configured
  - [ ] Rate limit bypass for health checks

- [ ] **Authentication**
  - [ ] JWT secret configured
  - [ ] Token expiration time set
  - [ ] Refresh token mechanism configured

#### Workers and Scaling
- [ ] **Gunicorn Configuration**
  - [ ] Worker count: 4 (2 x CPU cores)
  - [ ] Worker class: uvicorn.workers.UvicornWorker
  - [ ] Timeout: 120 seconds
  - [ ] Max requests: 1000
  - [ ] Graceful timeout: 30 seconds

---

### 10. Testing and Validation

#### Pre-Deployment Testing
- [ ] **Unit Tests**
  - [ ] All unit tests passing
  - [ ] Code coverage > 80%

- [ ] **Integration Tests**
  - [ ] Database integration tests passing
  - [ ] Redis integration tests passing
  - [ ] MinIO integration tests passing
  - [ ] External API integration tests passing

- [ ] **Security Tests**
  - [ ] OWASP ZAP scan completed
  - [ ] SQL injection tests passed
  - [ ] XSS tests passed
  - [ ] Authentication tests passed

#### Post-Deployment Testing
- [ ] **Smoke Tests**
  - [ ] Health endpoint responding
  - [ ] API documentation accessible
  - [ ] Database connectivity verified
  - [ ] Cache operations working
  - [ ] Object storage accessible

- [ ] **Functional Tests**
  - [ ] Critical user workflows tested
  - [ ] Data ingestion working
  - [ ] Report generation working
  - [ ] Search functionality working

- [ ] **Performance Tests**
  - [ ] Load testing completed
  - [ ] Response time baseline established
  - [ ] No memory leaks detected
  - [ ] Database query performance validated

---

### 11. Documentation

- [ ] **Deployment Documentation**
  - [ ] Staging deployment plan reviewed
  - [ ] Runbook created for common operations
  - [ ] Troubleshooting guide available
  - [ ] Architecture diagrams updated

- [ ] **API Documentation**
  - [ ] OpenAPI/Swagger docs accessible
  - [ ] API examples provided
  - [ ] Authentication flow documented

- [ ] **Operational Documentation**
  - [ ] Monitoring dashboard guide
  - [ ] Alert response procedures
  - [ ] Backup and restore procedures
  - [ ] Incident response plan

---

### 12. Team Readiness

- [ ] **Access Granted**
  - [ ] DevOps team has server access
  - [ ] Development team has staging environment access
  - [ ] QA team has testing access
  - [ ] Monitoring dashboards shared

- [ ] **Training Completed**
  - [ ] Team trained on deployment process
  - [ ] Team trained on monitoring tools
  - [ ] Team trained on incident response
  - [ ] On-call rotation established

- [ ] **Communication**
  - [ ] Deployment schedule communicated
  - [ ] Stakeholders notified
  - [ ] Maintenance windows scheduled
  - [ ] Emergency contacts updated

---

## Final Verification

### Pre-Deployment Sign-Off

- [ ] **Technical Lead:** _______________________  Date: _________
- [ ] **DevOps Lead:** _______________________  Date: _________
- [ ] **Security Officer:** _______________________  Date: _________
- [ ] **Product Owner:** _______________________  Date: _________

### Deployment Approval

- [ ] All checklist items completed
- [ ] Risk assessment conducted
- [ ] Rollback plan documented and tested
- [ ] Go/No-Go decision made

**Deployment Approved:** ☐ Yes  ☐ No

**Approver:** _______________________
**Date:** _________
**Signature:** _______________________

---

## Post-Deployment Checklist

- [ ] All services running and healthy
- [ ] Health checks passing
- [ ] Monitoring dashboards showing data
- [ ] Logs flowing correctly
- [ ] Smoke tests passed
- [ ] Performance within acceptable ranges
- [ ] No critical errors in logs
- [ ] Deployment documented in change log
- [ ] Team notified of successful deployment

---

## Notes

**Additional Requirements:**

**Risks Identified:**

**Mitigation Strategies:**

---

**Checklist Version:** 1.0.0
**Last Updated:** 2025-10-02
**Next Review:** Before next staging deployment
