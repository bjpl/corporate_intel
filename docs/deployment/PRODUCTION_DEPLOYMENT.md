# Production Deployment Guide - Corporate Intelligence Platform

## Table of Contents
- [Pre-Deployment Checklist](#pre-deployment-checklist)
- [Security Hardening](#security-hardening)
- [Resource Configuration](#resource-configuration)
- [Monitoring Setup](#monitoring-setup)
- [Backup Strategies](#backup-strategies)
- [Disaster Recovery](#disaster-recovery)
- [Deployment Steps](#deployment-steps)
- [Post-Deployment Validation](#post-deployment-validation)

## Pre-Deployment Checklist

### Infrastructure Requirements

- [ ] **Docker Engine** v20.10+ installed
- [ ] **Docker Compose** v2.0+ installed
- [ ] **Minimum Resources:**
  - 8 CPU cores
  - 32 GB RAM
  - 200 GB SSD storage
  - 100 Mbps network

### Security Requirements

- [ ] SSL/TLS certificates obtained
- [ ] Firewall rules configured
- [ ] VPC/Network isolation implemented
- [ ] Secrets management system ready
- [ ] Access control policies defined
- [ ] Audit logging enabled

### Configuration Files

- [ ] `.env` file created from `.env.example`
- [ ] All secrets generated and secured
- [ ] Database credentials rotated
- [ ] API keys configured
- [ ] Monitoring endpoints configured

### Testing Validation

- [ ] All tests passing (391+ tests)
- [ ] Load testing completed
- [ ] Security scanning passed
- [ ] Performance benchmarks met
- [ ] Failover scenarios tested

## Security Hardening

### 1. Environment Variables

**Generate Secure Secrets:**

```bash
# SECRET_KEY (32+ chars)
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Database password (24+ chars)
openssl rand -base64 24

# Redis password
openssl rand -base64 24

# MinIO credentials
openssl rand -base64 16
```

**Production .env Template:**

```bash
# CRITICAL: Never use development values in production!

ENVIRONMENT=production
DEBUG=false
SECRET_KEY=<GENERATED_SECRET_32_CHARS_MINIMUM>

# Database - Use strong passwords
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=prod_intel_user
POSTGRES_PASSWORD=<STRONG_PASSWORD_24_CHARS>
POSTGRES_DB=corporate_intel_prod

# Redis - Enable password
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=<STRONG_PASSWORD_24_CHARS>

# MinIO - Rotate credentials
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=<STRONG_ACCESS_KEY>
MINIO_SECRET_KEY=<STRONG_SECRET_KEY_32_CHARS>
MINIO_USE_SSL=true

# Observability
SENTRY_DSN=<YOUR_SENTRY_DSN>
OTEL_EXPORTER_OTLP_ENDPOINT=<YOUR_OTLP_ENDPOINT>
```

### 2. Docker Security

**Update Dockerfile for Production:**

```dockerfile
# Ensure non-root user
USER appuser

# Drop capabilities
--cap-drop=ALL
--cap-add=NET_BIND_SERVICE

# Read-only root filesystem
--read-only
--tmpfs /tmp:rw,noexec,nosuid
```

**Docker Compose Security:**

```yaml
services:
  api:
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
    read_only: true
    tmpfs:
      - /tmp
      - /app/tmp
```

### 3. Network Security

**Firewall Rules (iptables example):**

```bash
# Allow only necessary ports
iptables -A INPUT -p tcp --dport 80 -j ACCEPT    # HTTP
iptables -A INPUT -p tcp --dport 443 -j ACCEPT   # HTTPS
iptables -A INPUT -p tcp --dport 22 -j ACCEPT    # SSH (restrict to specific IPs)

# Block direct database access from outside
iptables -A INPUT -p tcp --dport 5432 -j DROP
iptables -A INPUT -p tcp --dport 6379 -j DROP
```

**Internal Network Isolation:**

```yaml
networks:
  frontend:
    driver: bridge
  backend:
    driver: bridge
    internal: true  # No external access

services:
  api:
    networks:
      - frontend
      - backend

  postgres:
    networks:
      - backend  # Only internal access
```

### 4. SSL/TLS Configuration

**Nginx Reverse Proxy:**

```nginx
server {
    listen 443 ssl http2;
    server_name api.corporate-intel.com;

    ssl_certificate /etc/ssl/certs/corporate-intel.crt;
    ssl_certificate_key /etc/ssl/private/corporate-intel.key;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Resource Configuration

### 1. Docker Resource Limits

**docker-compose.prod.yml:**

```yaml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G
        reservations:
          cpus: '2'
          memory: 4G
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
        window: 120s

  postgres:
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 16G
        reservations:
          cpus: '2'
          memory: 8G

  redis:
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 1G
```

### 2. PostgreSQL Optimization

```sql
-- Production PostgreSQL settings
ALTER SYSTEM SET shared_buffers = '8GB';
ALTER SYSTEM SET effective_cache_size = '24GB';
ALTER SYSTEM SET maintenance_work_mem = '2GB';
ALTER SYSTEM SET work_mem = '128MB';
ALTER SYSTEM SET max_connections = 200;

-- Connection pooling
ALTER SYSTEM SET max_prepared_transactions = 100;

-- Performance
ALTER SYSTEM SET random_page_cost = 1.1;  -- SSD
ALTER SYSTEM SET effective_io_concurrency = 200;  -- SSD

-- WAL and checkpoints
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET max_wal_size = '4GB';
```

### 3. Gunicorn Worker Configuration

```yaml
api:
  command: >
    gunicorn src.api.main:app
    --worker-class uvicorn.workers.UvicornWorker
    --workers 8
    --worker-connections 1000
    --max-requests 10000
    --max-requests-jitter 1000
    --timeout 120
    --keep-alive 5
    --bind 0.0.0.0:8000
    --access-logfile -
    --error-logfile -
    --log-level info
```

**Worker Formula:**
- CPU-bound: `workers = (2 x CPU cores) + 1`
- I/O-bound: `workers = (4 x CPU cores) + 1`

## Monitoring Setup

### 1. Health Check Endpoints

```python
# src/api/health.py
@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "version": "1.0.0"
    }

@router.get("/health/ready")
async def readiness_check(db: Session = Depends(get_db)):
    # Check database
    db.execute("SELECT 1")

    # Check Redis
    await redis_client.ping()

    return {"status": "ready"}

@router.get("/health/live")
async def liveness_check():
    return {"status": "alive"}
```

### 2. Prometheus Metrics

**prometheus.yml:**

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

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
```

### 3. Log Aggregation

```yaml
services:
  api:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "5"
        labels: "service,environment"
        env: "ENVIRONMENT"

  # Optional: Centralized logging
  loki:
    image: grafana/loki:latest
    ports:
      - "3100:3100"
    volumes:
      - loki_data:/loki
```

### 4. Alerting Rules

**alerts.yml:**

```yaml
groups:
  - name: api_alerts
    interval: 30s
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        annotations:
          summary: "High error rate detected"

      - alert: HighResponseTime
        expr: histogram_quantile(0.95, http_request_duration_seconds) > 1
        for: 5m
        annotations:
          summary: "95th percentile response time > 1s"

      - alert: DatabaseConnectionPoolExhausted
        expr: db_connections_used / db_connections_max > 0.9
        for: 2m
        annotations:
          summary: "Database connection pool > 90% utilized"
```

## Backup Strategies

### 1. Automated Database Backups

**backup.sh:**

```bash
#!/bin/bash
# Automated PostgreSQL backup script

BACKUP_DIR="/backups/postgresql"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# Create backup
docker-compose exec -T postgres pg_dump \
  -U ${POSTGRES_USER} \
  -d ${POSTGRES_DB} \
  --format=custom \
  --compress=9 \
  > "${BACKUP_DIR}/backup_${TIMESTAMP}.dump"

# Upload to S3 (example)
aws s3 cp \
  "${BACKUP_DIR}/backup_${TIMESTAMP}.dump" \
  "s3://corporate-intel-backups/postgresql/"

# Remove old backups
find ${BACKUP_DIR} -name "backup_*.dump" -mtime +${RETENTION_DAYS} -delete

echo "Backup completed: backup_${TIMESTAMP}.dump"
```

**Cron Schedule:**

```bash
# Daily at 2 AM
0 2 * * * /scripts/backup.sh

# Hourly WAL archiving
0 * * * * /scripts/archive_wal.sh
```

### 2. Volume Snapshots

```bash
# Create volume snapshot
docker run --rm \
  -v corporate-intel-postgres-data:/data \
  -v $(pwd)/snapshots:/backup \
  alpine tar czf /backup/postgres_snapshot_$(date +%Y%m%d).tar.gz -C /data .

# Restore from snapshot
docker run --rm \
  -v corporate-intel-postgres-data:/data \
  -v $(pwd)/snapshots:/backup \
  alpine tar xzf /backup/postgres_snapshot_20240101.tar.gz -C /data
```

### 3. Application State Backup

```bash
#!/bin/bash
# Backup all persistent data

BACKUP_ROOT="/backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p ${BACKUP_ROOT}

# Database
docker-compose exec -T postgres pg_dumpall -U postgres > ${BACKUP_ROOT}/full_backup.sql

# MinIO buckets
docker-compose exec -T minio mc mirror /data ${BACKUP_ROOT}/minio

# Redis dump
docker-compose exec -T redis redis-cli BGSAVE
docker cp corporate-intel-redis:/data/dump.rdb ${BACKUP_ROOT}/redis_dump.rdb

# Application logs and data
tar czf ${BACKUP_ROOT}/app_data.tar.gz ./logs ./data ./cache

echo "Full backup completed: ${BACKUP_ROOT}"
```

## Disaster Recovery

### 1. Recovery Time Objective (RTO)

**Target: < 1 hour**

**Procedures:**

```bash
# 1. Provision new infrastructure
terraform apply

# 2. Restore from latest backup
./scripts/restore.sh --backup-id 20240101_020000

# 3. Verify data integrity
./scripts/verify_restore.sh

# 4. Start services
docker-compose -f docker-compose.prod.yml up -d

# 5. Run health checks
./scripts/health_check.sh
```

### 2. Recovery Point Objective (RPO)

**Target: < 15 minutes**

**Strategies:**
- Continuous WAL archiving (PostgreSQL)
- Redis AOF with 1-second fsync
- MinIO replication
- Transaction log backups

### 3. Failover Procedures

**Automated Failover (Kubernetes example):**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: corporate-intel-api
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    spec:
      containers:
      - name: api
        image: corporate-intel-api:latest
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8000
          initialDelaySeconds: 15
          periodSeconds: 5
```

### 4. Multi-Region Setup

```yaml
# Primary region
services:
  postgres:
    environment:
      POSTGRES_SYNCHRONOUS_STANDBY_NAMES: 'standby1,standby2'

# Standby region
services:
  postgres_standby:
    environment:
      POSTGRES_MASTER_HOST: primary-db.region1.internal
      POSTGRES_REPLICATION_MODE: slave
```

## Deployment Steps

### 1. Pre-Deployment

```bash
# Pull latest code
git pull origin main

# Build images
docker-compose -f docker-compose.prod.yml build --no-cache

# Run tests
make ci-test

# Security scan
make security-scan

# Tag images
docker tag corporate-intel-api:latest corporate-intel-api:v1.0.0
```

### 2. Database Migration

```bash
# Backup current database
make db-backup

# Test migrations on staging
docker-compose -f docker-compose.staging.yml exec api alembic upgrade head

# Production migration (off-peak hours)
docker-compose -f docker-compose.prod.yml exec api alembic upgrade head
```

### 3. Rolling Deployment

```bash
# Method 1: Blue-Green Deployment
docker-compose -f docker-compose.prod.yml up -d api_green
# Test green deployment
# Switch traffic
# Remove blue deployment

# Method 2: Rolling Update
for i in {1..3}; do
  docker-compose -f docker-compose.prod.yml up -d --no-deps --scale api=$i api
  sleep 30
  # Verify health
done
```

### 4. Post-Deployment

```bash
# Verify services
docker-compose -f docker-compose.prod.yml ps

# Check logs
docker-compose -f docker-compose.prod.yml logs -f --tail=100

# Run smoke tests
./scripts/smoke_test.sh

# Monitor metrics
curl http://localhost:9090/metrics

# Verify health endpoints
curl http://api.corporate-intel.com/health
curl http://api.corporate-intel.com/health/ready
```

## Post-Deployment Validation

### Checklist

- [ ] All services running (docker-compose ps)
- [ ] Health checks passing
- [ ] Database migrations applied
- [ ] Monitoring dashboards active
- [ ] Alerts configured
- [ ] Logs flowing to aggregation system
- [ ] Backups scheduled and verified
- [ ] SSL certificates valid
- [ ] Load balancer distributing traffic
- [ ] Smoke tests passing
- [ ] Performance metrics within SLAs
- [ ] Security scans clean
- [ ] Documentation updated

### Smoke Tests

```bash
#!/bin/bash
# smoke_test.sh

API_URL="https://api.corporate-intel.com"

# Health check
curl -f ${API_URL}/health || exit 1

# API functionality
curl -f ${API_URL}/api/v1/companies || exit 1

# Database connectivity
curl -f ${API_URL}/health/ready || exit 1

# Response time check
RESPONSE_TIME=$(curl -o /dev/null -s -w '%{time_total}' ${API_URL}/health)
if (( $(echo "$RESPONSE_TIME > 1.0" | bc -l) )); then
  echo "Response time too high: ${RESPONSE_TIME}s"
  exit 1
fi

echo "All smoke tests passed"
```

### Rollback Procedure

```bash
#!/bin/bash
# rollback.sh

# Stop current version
docker-compose -f docker-compose.prod.yml down

# Restore previous version
docker-compose -f docker-compose.prod.yml up -d --force-recreate

# Restore database backup
./scripts/restore.sh --backup-id ${PREVIOUS_BACKUP_ID}

# Verify rollback
./scripts/smoke_test.sh

echo "Rollback completed"
```

## Maintenance Windows

### Planned Maintenance

```bash
# 1. Notify users
# 2. Put system in maintenance mode
docker-compose exec api python -m scripts.maintenance_mode on

# 3. Perform maintenance
docker-compose -f docker-compose.prod.yml down
# ... maintenance tasks ...
docker-compose -f docker-compose.prod.yml up -d

# 4. Verify system
./scripts/smoke_test.sh

# 5. Exit maintenance mode
docker-compose exec api python -m scripts.maintenance_mode off
```

## Next Steps

- [Monitoring Guide](../monitoring/MONITORING_SETUP.md)
- [Security Guide](../security/SECURITY_BEST_PRACTICES.md)
- [Performance Tuning](../performance/OPTIMIZATION_GUIDE.md)
