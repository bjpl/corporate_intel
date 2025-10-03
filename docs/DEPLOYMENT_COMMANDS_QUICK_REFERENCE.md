# Staging Deployment - Quick Reference Commands

**Environment:** Staging
**Version:** 1.0.0
**Last Updated:** 2025-10-02

---

## Deployment Commands

### Full Automated Deployment
```bash
# Run complete deployment with all checks
./scripts/deploy-staging.sh

# Expected duration: ~15-20 minutes
```

### Manual Step-by-Step Deployment

#### 1. Pre-deployment Checks
```bash
# Verify Docker is running
docker info

# Validate docker-compose configuration
docker-compose --env-file .env.staging config

# Check disk space
df -h

# Verify environment file
cat .env.staging | grep -v PASSWORD | grep -v SECRET
```

#### 2. Build Docker Image
```bash
# Build with specific tag
docker build -t corporate-intel-api:staging-$(date +%Y%m%d-%H%M%S) \
  --build-arg ENVIRONMENT=staging \
  -f Dockerfile .

# Tag as latest
docker tag corporate-intel-api:staging-$(date +%Y%m%d-%H%M%S) \
  corporate-intel-api:staging-latest
```

#### 3. Start Infrastructure Services
```bash
# Start database, cache, and storage
docker-compose up -d postgres redis minio

# Wait for health checks
docker-compose ps

# Verify services are healthy
docker-compose exec postgres pg_isready -U intel_staging_user
docker-compose exec redis redis-cli ping
curl http://localhost:9000/minio/health/live
```

#### 4. Run Database Migrations
```bash
# Apply all pending migrations
docker-compose run --rm api alembic upgrade head

# Check current migration version
docker-compose run --rm api alembic current

# View migration history
docker-compose run --rm api alembic history
```

#### 5. Start Application
```bash
# Start all services
docker-compose up -d

# Monitor startup
docker-compose logs -f api
```

#### 6. Initialize Storage
```bash
# Install MinIO client (if needed)
wget https://dl.min.io/client/mc/release/linux-amd64/mc
chmod +x mc
sudo mv mc /usr/local/bin/

# Configure MinIO
mc alias set staging-minio http://localhost:9000 \
  ${MINIO_ACCESS_KEY} ${MINIO_SECRET_KEY}

# Create buckets
mc mb staging-minio/staging-documents --ignore-existing
mc mb staging-minio/staging-reports --ignore-existing

# Set policies
mc anonymous set download staging-minio/staging-reports
```

---

## Health Check Commands

### Quick Health Check
```bash
# API health
curl http://localhost:8000/health | jq

# Expected response:
# {
#   "status": "healthy",
#   "environment": "staging",
#   "timestamp": "2025-10-02T12:00:00Z"
# }
```

### Detailed Health Checks
```bash
# Database health
curl http://localhost:8000/api/v1/health/database | jq

# Redis health
curl http://localhost:8000/api/v1/health/redis | jq

# MinIO health
curl http://localhost:8000/api/v1/health/minio | jq

# All health checks
./scripts/health-check.sh
```

### Service-Level Health Checks
```bash
# PostgreSQL
docker-compose exec postgres pg_isready -U intel_staging_user

# PostgreSQL connection test
docker-compose exec postgres psql -U intel_staging_user -d corporate_intel_staging -c "SELECT version();"

# Redis
docker-compose exec redis redis-cli ping

# Redis info
docker-compose exec redis redis-cli INFO

# MinIO
curl http://localhost:9000/minio/health/live
```

---

## Monitoring Commands

### View Logs
```bash
# API logs (live)
docker-compose logs -f api

# All services
docker-compose logs -f

# Last 100 lines
docker-compose logs --tail=100 api

# Save logs to file
docker-compose logs --no-color > staging-logs-$(date +%Y%m%d).log
```

### Container Status
```bash
# List all containers
docker-compose ps

# Detailed container info
docker-compose ps -a

# Container resource usage
docker stats

# Specific service stats
docker stats corporate-intel-api
```

### System Metrics
```bash
# Prometheus metrics
curl http://localhost:8000/metrics

# Query Prometheus
curl http://localhost:9090/api/v1/query?query=up

# Grafana dashboards
open http://localhost:3000
```

---

## Database Commands

### Connection
```bash
# Connect to database
docker-compose exec postgres psql -U intel_staging_user -d corporate_intel_staging

# Run query from command line
docker-compose exec postgres psql -U intel_staging_user -d corporate_intel_staging -c "SELECT COUNT(*) FROM companies;"
```

### Migrations
```bash
# Check current version
docker-compose run --rm api alembic current

# Upgrade to latest
docker-compose run --rm api alembic upgrade head

# Downgrade one version
docker-compose run --rm api alembic downgrade -1

# View migration SQL (dry run)
docker-compose run --rm api alembic upgrade head --sql

# Create new migration
docker-compose run --rm api alembic revision --autogenerate -m "description"
```

### Backup and Restore
```bash
# Create backup
docker-compose exec postgres pg_dump \
  -U intel_staging_user \
  -d corporate_intel_staging \
  --clean --if-exists \
  > backups/staging-db-$(date +%Y%m%d-%H%M%S).sql

# Restore from backup
docker-compose exec -T postgres psql \
  -U intel_staging_user \
  -d corporate_intel_staging \
  < backups/staging-db-20251002-120000.sql

# Compressed backup
docker-compose exec postgres pg_dump \
  -U intel_staging_user \
  -d corporate_intel_staging \
  -Fc > backups/staging-db-$(date +%Y%m%d-%H%M%S).dump

# Restore compressed backup
docker-compose exec postgres pg_restore \
  -U intel_staging_user \
  -d corporate_intel_staging \
  --clean \
  backups/staging-db-20251002-120000.dump
```

---

## Service Management

### Start/Stop Services
```bash
# Start all services
docker-compose up -d

# Start specific service
docker-compose up -d api

# Stop all services
docker-compose down

# Stop specific service
docker-compose stop api

# Restart service
docker-compose restart api

# Rebuild and restart
docker-compose up -d --build api
```

### Scale Services
```bash
# Scale API workers
docker-compose up -d --scale api=3

# View scaled services
docker-compose ps
```

### Service Dependencies
```bash
# Start with dependencies
docker-compose up -d api

# This automatically starts: postgres, redis, minio
```

---

## Troubleshooting Commands

### Inspect Containers
```bash
# View container details
docker inspect corporate-intel-api

# View container logs
docker logs corporate-intel-api

# Execute command in container
docker-compose exec api bash

# Run one-off command
docker-compose run --rm api python --version
```

### Network Debugging
```bash
# List networks
docker network ls

# Inspect network
docker network inspect corporate-intel-network

# Test connectivity between containers
docker-compose exec api ping postgres
docker-compose exec api curl http://redis:6379
```

### Resource Usage
```bash
# Container CPU and memory
docker stats --no-stream

# Disk usage
docker system df

# Clean up unused resources
docker system prune -a
```

### Application Debugging
```bash
# Python shell in API container
docker-compose exec api python

# Run tests
docker-compose run --rm api pytest

# Check installed packages
docker-compose exec api pip list

# Verify environment variables
docker-compose exec api env | grep -E "POSTGRES|REDIS|MINIO"
```

---

## Rollback Commands

### Automated Rollback
```bash
# Run rollback script
./scripts/rollback-staging.sh

# This will:
# 1. Stop current deployment
# 2. Restore previous image
# 3. Optionally restore database
# 4. Restart services
```

### Manual Rollback
```bash
# 1. Stop services
docker-compose down

# 2. List available images
docker images corporate-intel-api

# 3. Tag previous version as latest
docker tag corporate-intel-api:staging-20251001-150000 \
  corporate-intel-api:staging-latest

# 4. Restart services
docker-compose up -d

# 5. Verify health
curl http://localhost:8000/health
```

### Database Rollback
```bash
# Rollback 1 migration
docker-compose run --rm api alembic downgrade -1

# Rollback to specific version
docker-compose run --rm api alembic downgrade <revision>

# Restore from backup
docker-compose exec -T postgres psql -U intel_staging_user \
  -d corporate_intel_staging < backups/staging-db-latest.sql
```

---

## Maintenance Commands

### Update Dependencies
```bash
# Pull latest images
docker-compose pull

# Rebuild with updated dependencies
docker-compose build --no-cache api
```

### Clean Up
```bash
# Remove old containers
docker-compose down --remove-orphans

# Remove old images (keep last 3)
docker images corporate-intel-api --format "{{.Tag}}" | \
  tail -n +4 | \
  xargs -I {} docker rmi corporate-intel-api:{}

# Clean up volumes (CAUTION: deletes data)
docker-compose down -v
```

### Backup Maintenance
```bash
# List backups
ls -lh backups/

# Delete old backups (keep last 7 days)
find backups/ -name "staging-db-*.sql" -mtime +7 -delete

# Compress old backups
gzip backups/staging-db-*.sql
```

---

## Security Commands

### Rotate Credentials
```bash
# Run credential rotation script
./scripts/rotate-credentials.sh

# Update secrets in .env.staging
nano .env.staging

# Restart services to apply new credentials
docker-compose restart
```

### Security Scan
```bash
# Scan Docker image for vulnerabilities
./scripts/docker-security-scan.sh

# Expected: No critical vulnerabilities
```

### SSL/TLS Verification
```bash
# Test SSL certificate
openssl s_client -connect staging-api.corporate-intel.example.com:443

# Check certificate expiration
echo | openssl s_client -connect staging-api.corporate-intel.example.com:443 2>/dev/null | \
  openssl x509 -noout -dates
```

---

## Performance Testing

### Load Testing
```bash
# Simple load test with Apache Bench
ab -n 1000 -c 10 http://localhost:8000/health

# Expected results:
# - Requests per second: > 500
# - Mean response time: < 50ms
# - 95th percentile: < 100ms
```

### Stress Testing
```bash
# Install wrk if needed
sudo apt-get install wrk

# Run stress test
wrk -t4 -c100 -d30s http://localhost:8000/api/v1/companies/search?q=Apple
```

---

## Monitoring Setup

### Configure Monitoring
```bash
# Run monitoring setup script
./scripts/monitoring-setup.sh

# Access dashboards:
# - Prometheus: http://localhost:9090
# - Grafana: http://localhost:3000 (admin/admin)
# - Jaeger: http://localhost:16686
```

### Query Metrics
```bash
# Prometheus API query
curl -G http://localhost:9090/api/v1/query \
  --data-urlencode 'query=up{job="corporate-intel-api"}'

# Get all metrics
curl http://localhost:8000/metrics
```

---

## Emergency Procedures

### Complete System Restart
```bash
# 1. Stop everything
docker-compose down

# 2. Wait 10 seconds
sleep 10

# 3. Start infrastructure first
docker-compose up -d postgres redis minio

# 4. Wait for health checks
sleep 30

# 5. Start application
docker-compose up -d api

# 6. Verify
curl http://localhost:8000/health
```

### Emergency Shutdown
```bash
# Graceful shutdown
docker-compose down

# Force shutdown (if graceful fails)
docker-compose kill

# Clean up
docker-compose rm -f
```

---

## Useful One-Liners

```bash
# Quick status check
docker-compose ps && curl -s http://localhost:8000/health | jq

# Follow all logs with timestamps
docker-compose logs -f --timestamps

# Restart only API without downtime
docker-compose up -d --force-recreate --no-deps api

# Database quick stats
docker-compose exec postgres psql -U intel_staging_user -d corporate_intel_staging -c "\
  SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size \
  FROM pg_tables WHERE schemaname = 'public' ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;"

# Redis memory usage
docker-compose exec redis redis-cli INFO memory | grep used_memory_human

# Container health summary
docker-compose ps | awk '{print $1, $6}' | column -t

# Quick backup
docker-compose exec postgres pg_dump -U intel_staging_user corporate_intel_staging | gzip > backup-$(date +%Y%m%d).sql.gz
```

---

## Support and Documentation

- **Full Deployment Plan:** `/docs/STAGING_DEPLOYMENT_PLAN.md`
- **Environment Checklist:** `/docs/STAGING_ENVIRONMENT_CHECKLIST.md`
- **Deployment Logs:** `/logs/deployment-*.log`
- **Health Check Script:** `/scripts/health-check.sh`
- **Rollback Script:** `/scripts/rollback-staging.sh`

---

**Quick Reference Version:** 1.0.0
**Last Updated:** 2025-10-02
