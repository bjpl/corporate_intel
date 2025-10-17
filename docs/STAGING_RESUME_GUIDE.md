# Staging Deployment Resume Guide
**Quick Reference for Resuming Staging Work**

---

## Current Status (as of October 16, 2025)

### ✅ What's Working

1. **All Containers Operational**
   - API: `corporate-intel-staging-api` (healthy on port 8004)
   - Database: `corporate-intel-staging-postgres` (healthy on port 5435)
   - Cache: `corporate-intel-staging-redis` (healthy on port 6382)
   - Monitoring: Prometheus (port 9091), Grafana (port 3001)

2. **API Successfully Started**
   - Health endpoint responding: http://localhost:8004/health
   - Environment: staging
   - Version: 0.1.0

3. **Issues Resolved**
   - ✅ Fixed API restart loop (missing MinIO env vars)
   - ✅ Updated docker-compose.staging.yml with MinIO configuration
   - ✅ All services now healthy

### 📋 What's Pending

1. **MinIO Service**
   - Environment variables configured
   - Service not yet deployed
   - Optional for core functionality

2. **Testing**
   - Smoke tests not yet run
   - Integration tests pending
   - Load tests pending

3. **API Validation**
   - SEC ticker-to-CIK lookup needs testing
   - Full endpoint validation pending
   - Performance benchmarking needed

---

## Quick Start (5 Minutes)

### Check System Status

```bash
# Navigate to project
cd C:\Users\brand\Development\Project_Workspace\active-development\corporate_intel

# Check all containers
docker ps --filter "name=corporate-intel-staging"

# Expected output: 5 containers running (API, postgres, redis, prometheus, grafana)
```

### Verify API Health

```bash
# Basic health check
curl http://localhost:8004/health

# Expected: {"status":"healthy","version":"0.1.0","environment":"staging"}

# Detailed health (includes database check)
curl http://localhost:8004/health/detailed

# Ping endpoint (ultra-lightweight)
curl http://localhost:8004/health/ping
```

### View Logs

```bash
# API logs (real-time)
docker logs corporate-intel-staging-api -f --tail 50

# All services logs
docker-compose -f docker-compose.staging.yml logs -f

# Specific service
docker logs corporate-intel-staging-postgres --tail 100
```

---

## Common Operations

### Start/Stop Services

```bash
# Start all staging services
docker-compose -f docker-compose.staging.yml --env-file .env.staging up -d

# Stop all services (keeps data)
docker-compose -f docker-compose.staging.yml down

# Stop and remove volumes (CAUTION: deletes data!)
docker-compose -f docker-compose.staging.yml down -v

# Restart specific service
docker-compose -f docker-compose.staging.yml restart api
```

### Rebuild After Changes

```bash
# Rebuild and restart API only
docker-compose -f docker-compose.staging.yml up -d --build api

# Full rebuild
docker-compose -f docker-compose.staging.yml down
docker-compose -f docker-compose.staging.yml --env-file .env.staging up -d --build
```

### Database Operations

```bash
# Connect to database
docker exec -it corporate-intel-staging-postgres psql -U intel_staging_user -d corporate_intel_staging

# Run migrations
docker exec corporate-intel-staging-api alembic upgrade head

# Check migration status
docker exec corporate-intel-staging-api alembic current

# Database backup
docker exec corporate-intel-staging-postgres pg_dump -U intel_staging_user corporate_intel_staging > backup_$(date +%Y%m%d).sql
```

### Redis Operations

```bash
# Connect to Redis
docker exec -it corporate-intel-staging-redis redis-cli -a dev-redis-password

# Check Redis stats
docker exec corporate-intel-staging-redis redis-cli -a dev-redis-password INFO stats

# Clear cache
docker exec corporate-intel-staging-redis redis-cli -a dev-redis-password FLUSHDB
```

---

## Testing Workflow

### 1. Run Smoke Tests (5 minutes)

```bash
# Navigate to tests
cd tests/staging

# Run smoke tests
pytest test_smoke.py -v

# Expected: All basic connectivity tests pass
```

### 2. Run Integration Tests (15 minutes)

```bash
# Full integration suite
pytest test_integration.py -v

# Specific test
pytest test_integration.py::test_pipeline_integration -v
```

### 3. Run Load Tests (30 minutes)

```bash
# Start Locust UI
locust -f tests/staging/test_load.py --host=http://localhost:8004

# Open browser: http://localhost:8089
# Configure: 100 users, 10 spawn rate
# Duration: 10 minutes
```

### 4. Security Validation (15 minutes)

```bash
# Run security tests
pytest tests/staging/test_security.py -v

# Expected: SQL injection, XSS, auth bypass tests pass
```

---

## Troubleshooting

### API Won't Start

**Symptom**: Container in restart loop

```bash
# Check logs for errors
docker logs corporate-intel-staging-api --tail 200

# Common issues:
# 1. Missing environment variables
# 2. Database connection failed
# 3. Port already in use

# Fix: Check .env.staging file
cat .env.staging | grep -E "POSTGRES|REDIS|MINIO"

# Fix: Restart database first
docker-compose -f docker-compose.staging.yml restart postgres
sleep 10
docker-compose -f docker-compose.staging.yml restart api
```

### Database Connection Issues

```bash
# Check database is ready
docker exec corporate-intel-staging-postgres pg_isready -U intel_staging_user

# Test direct connection
docker exec -it corporate-intel-staging-postgres psql -U intel_staging_user -d corporate_intel_staging -c "SELECT version();"

# Check connection from API container
docker exec corporate-intel-staging-api env | grep POSTGRES
```

### Redis Connection Issues

```bash
# Check Redis is running
docker exec corporate-intel-staging-redis redis-cli -a dev-redis-password ping

# Expected: PONG

# Check Redis from API
docker exec corporate-intel-staging-api env | grep REDIS
```

### Port Conflicts

```bash
# Check what's using ports
netstat -ano | findstr "8004"  # API port
netstat -ano | findstr "5435"  # PostgreSQL port
netstat -ano | findstr "6382"  # Redis port

# Kill process if needed
taskkill /PID <process_id> /F

# Or change ports in docker-compose.staging.yml
```

---

## Next Steps Checklist

### Immediate (Today)
- [ ] Run smoke tests: `pytest tests/staging/test_smoke.py -v`
- [ ] Verify SEC API lookup works
- [ ] Test all main API endpoints
- [ ] Check database has schema/tables
- [ ] Verify Redis caching works

### Short-term (Tomorrow)
- [ ] Run full integration test suite
- [ ] Execute load tests with Locust
- [ ] Validate all data pipelines
- [ ] Set up continuous monitoring alerts
- [ ] Document any issues found

### Medium-term (Week 1)
- [ ] Deploy MinIO service (if needed)
- [ ] Run security validation tests
- [ ] Performance optimization based on results
- [ ] Create production deployment plan
- [ ] Set up automated testing

---

## Important Files

### Configuration
- `.env.staging` - Environment variables
- `docker-compose.staging.yml` - Container orchestration
- `src/core/config.py` - Application settings

### Documentation
- `docs/STAGING_STATE_DOCUMENTATION.md` - Current state (this session)
- `docs/STAGING_DEPLOYMENT_PLAN.md` - Original plan
- `docs/PLAN_A_COMPLETION_REPORT.md` - Recent work summary

### Tests
- `tests/staging/test_smoke.py` - Basic connectivity
- `tests/staging/test_integration.py` - Multi-service workflows
- `tests/staging/test_load.py` - Performance testing
- `tests/staging/test_security.py` - Security validation

### Recent Additions
- `src/pipeline/common.py` - Shared pipeline utilities (NEW)
- `tests/verify_refactoring.py` - Dashboard verification (NEW)

---

## Key Endpoints to Test

### Health & Monitoring
```bash
# Basic health
GET http://localhost:8004/health

# Detailed health (with database check)
GET http://localhost:8004/health/detailed

# Ping (for load balancers)
GET http://localhost:8004/health/ping

# Readiness probe
GET http://localhost:8004/health/readiness
```

### API Documentation
```bash
# Swagger UI
http://localhost:8004/docs

# ReDoc
http://localhost:8004/redoc

# OpenAPI schema
http://localhost:8004/openapi.json
```

### Company Endpoints
```bash
# Search companies
GET http://localhost:8004/api/v1/companies?search=Apple

# Get company by ID
GET http://localhost:8004/api/v1/companies/{company_id}

# SEC ticker lookup (needs verification)
GET http://localhost:8004/api/v1/companies/sec/lookup?ticker=AAPL
```

### Monitoring
```bash
# Prometheus
http://localhost:9091

# Grafana
http://localhost:3001
# Username: admin
# Password: (see GRAFANA_PASSWORD in .env.staging)
```

---

## Environment Variables Reference

### Critical Variables (Must be Set)
```bash
# Database
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=intel_staging_user
POSTGRES_PASSWORD=<secure_password>
POSTGRES_DB=corporate_intel_staging

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=<secure_password>

# MinIO (REQUIRED for API to start)
MINIO_ACCESS_KEY=intel_staging_admin
MINIO_SECRET_KEY=<secure_key>
MINIO_HOST=minio
MINIO_PORT=9000
MINIO_SECURE=false
MINIO_BUCKET=corporate-intel-staging

# Security
SECRET_KEY=<32+ character key>
ENVIRONMENT=staging
```

### External APIs (Optional but Recommended)
```bash
# Alpha Vantage
ALPHA_VANTAGE_API_KEY=<your_key>

# NewsAPI
NEWSAPI_KEY=<your_key>

# SEC EDGAR
SEC_USER_AGENT=Corporate Intel Platform/1.0 (your.email@example.com)
```

---

## Performance Baselines

### Expected Performance
- **API Health Check**: < 50ms
- **Database Query**: < 100ms
- **Search Endpoint**: < 500ms
- **Concurrent Users**: 100+
- **Requests/sec**: 500+

### Resource Usage (Normal)
- **API Container**: ~200-400 MB RAM
- **PostgreSQL**: ~300-500 MB RAM
- **Redis**: ~50-100 MB RAM
- **Total CPU**: < 50% on 4-core system

---

## Git Workflow

### Check Current State
```bash
# View uncommitted changes
git status

# See what's modified
git diff docker-compose.staging.yml
```

### Commit Changes
```bash
# Stage files
git add docker-compose.staging.yml
git add docs/STAGING_STATE_DOCUMENTATION.md
git add docs/STAGING_RESUME_GUIDE.md
git add src/pipeline/common.py
git add tests/verify_refactoring.py

# Create commit
git commit -m "feat: complete staging deployment + MinIO fix + comprehensive documentation

- Fixed API container restart loop (missing MinIO env vars)
- Updated docker-compose.staging.yml with MinIO configuration
- Added shared pipeline utilities (src/pipeline/common.py)
- Created dashboard refactoring verification script
- Documented complete staging state
- Created staging resume guide

All containers healthy and operational. Ready for testing phase."

# Push to remote
git push origin master
```

---

## Success Criteria

### ✅ Deployment Successful When:
- [ ] All 5 containers running and healthy
- [ ] API responding to health checks
- [ ] Database accessible and migrated
- [ ] Redis operational with low latency
- [ ] Monitoring stack collecting metrics
- [ ] Smoke tests passing
- [ ] No errors in logs (past 10 minutes)

### ✅ Ready for Production When:
- [ ] All integration tests passing
- [ ] Load tests show acceptable performance
- [ ] Security tests all passing
- [ ] No critical or high priority bugs
- [ ] Documentation complete
- [ ] Rollback procedure tested
- [ ] Monitoring alerts configured
- [ ] Backup/restore verified

---

## Quick Command Reference

```bash
# Status
docker ps --filter "name=corporate-intel-staging"

# Health
curl http://localhost:8004/health | jq

# Logs
docker logs corporate-intel-staging-api -f --tail 50

# Restart
docker-compose -f docker-compose.staging.yml restart

# Full restart
docker-compose -f docker-compose.staging.yml down && \
docker-compose -f docker-compose.staging.yml --env-file .env.staging up -d

# Database
docker exec -it corporate-intel-staging-postgres psql -U intel_staging_user -d corporate_intel_staging

# Redis
docker exec -it corporate-intel-staging-redis redis-cli -a dev-redis-password

# Tests
pytest tests/staging/test_smoke.py -v

# Monitoring
echo "Prometheus: http://localhost:9091"
echo "Grafana: http://localhost:3001"
```

---

## Support & Resources

### Documentation
- Full staging state: `docs/STAGING_STATE_DOCUMENTATION.md`
- Original plan: `docs/STAGING_DEPLOYMENT_PLAN.md`
- Plan A completion: `docs/PLAN_A_COMPLETION_REPORT.md`
- Repository pattern: `docs/architecture/ADR-001-REPOSITORY-PATTERN.md`

### Contacts
- Project: Corporate Intelligence Platform
- Repository: `corporate-intel`
- Branch: `master`
- Environment: Staging

---

**Last Updated**: October 16, 2025
**Status**: ✅ Operational - Ready for Testing
**Next Action**: Run smoke tests
