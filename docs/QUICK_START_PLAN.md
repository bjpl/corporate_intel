# Corporate Intel - Pragmatic Startup Plan (2-3 Hours)

**Current Status Analysis:**
- Existing containers running on ports: 5432 (Postgres), 6379 (Redis), 8000 (Colombia Intel), 8001 (Subjunctive)
- Need to use alternative ports to avoid conflicts
- Docker Compose configured for: Postgres (TimescaleDB), Redis, MinIO, API
- FastAPI app ready in src/api/main.py
- Database migrations setup with Alembic

---

## PHASE 1: Infrastructure Cleanup & Startup (30 min)

### Step 1.1: Stop Conflicting Services (5 min)

**Identify what we can safely stop:**
```bash
# Check what colombia_intel containers are doing
docker ps --filter "name=colombia_intel"

# If not needed, stop conflicting containers
docker stop colombia_intel_db colombia_intel_redis colombia_intel_backend
```

**Alternative: Use different ports in .env (RECOMMENDED)**
```bash
# Edit .env to use non-conflicting ports
POSTGRES_PORT=5434
REDIS_PORT=6381
MINIO_PORT=9002
MINIO_CONSOLE_PORT=9003
API_PORT=8002
```

**Expected Output:** Containers stopped or .env updated with new ports

**Troubleshooting:**
- If containers won't stop: `docker stop -t 0 <container_id>`
- If ports still in use: `netstat -ano | findstr :<port>` and kill process

**Time: 5 minutes**

---

### Step 1.2: Update .env for Port Conflicts (5 min)

**Commands:**
```bash
# Backup current .env
cp .env .env.backup

# Add port overrides to .env (append these lines)
echo "" >> .env
echo "# Port overrides to avoid conflicts" >> .env
echo "POSTGRES_PORT=5434" >> .env
echo "REDIS_PORT=6381" >> .env
echo "MINIO_PORT=9002" >> .env
echo "MINIO_CONSOLE_PORT=9003" >> .env
echo "API_PORT=8002" >> .env
```

**Verify:**
```bash
grep -E "POSTGRES_PORT|REDIS_PORT|MINIO_PORT|API_PORT" .env
```

**Expected Output:**
```
POSTGRES_PORT=5434
REDIS_PORT=6381
MINIO_PORT=9002
MINIO_CONSOLE_PORT=9003
API_PORT=8002
```

**Time: 5 minutes**

---

### Step 1.3: Start Core Infrastructure (15 min)

**Start database and cache only (minimal services):**
```bash
# Start just postgres and redis first
docker-compose up -d postgres redis

# Watch the logs to confirm healthy
docker-compose logs -f postgres redis
```

**Success Criteria:**
- Postgres: "database system is ready to accept connections"
- Redis: "Ready to accept connections"
- Both show (healthy) in `docker ps`

**Verify health:**
```bash
# Check container status
docker ps --filter "name=corporate-intel"

# Test Postgres connection
docker exec corporate-intel-postgres pg_isready -U intel_user -d corporate_intel

# Test Redis connection
docker exec corporate-intel-redis redis-cli ping
```

**Expected Output:**
- Postgres: "corporate-intel-postgres:5432 - accepting connections"
- Redis: "PONG"

**Troubleshooting:**
- Postgres unhealthy: Check logs with `docker logs corporate-intel-postgres`
- Redis unhealthy: Check `docker logs corporate-intel-redis`
- Port conflicts: Use `docker-compose down` and fix .env ports

**Time: 15 minutes**

---

### Step 1.4: Start MinIO (Optional - Can Wait) (5 min)

**Commands:**
```bash
# Start MinIO object storage
docker-compose up -d minio

# Check logs
docker-compose logs -f minio
```

**Success Criteria:**
- MinIO shows "Console: http://localhost:9003"
- Health check passing

**Access MinIO Console:**
- URL: http://localhost:9003
- User: minio_admin
- Password: minio_password (from .env)

**Note:** MinIO is optional for initial testing. Can skip for now if time-limited.

**Time: 5 minutes (OPTIONAL)**

---

## PHASE 2: Database Setup (20 min)

### Step 2.1: Verify Database Connection (5 min)

**Commands:**
```bash
# Connect to database and verify
docker exec -it corporate-intel-postgres psql -U intel_user -d corporate_intel

# Inside psql, run:
\l                          # List databases
\dt                         # List tables (should be empty initially)
SELECT version();           # Check Postgres version
SELECT * FROM pg_extension; # Check TimescaleDB extension
\q                          # Exit
```

**Expected Output:**
- Database "corporate_intel" exists
- TimescaleDB extension should be listed
- No tables yet (migrations not run)

**Time: 5 minutes**

---

### Step 2.2: Run Database Migrations (10 min)

**Check migration status:**
```bash
# See what migrations exist
ls -la alembic/versions/

# Check current migration status (will fail initially, that's OK)
docker-compose run --rm api alembic current
```

**Run migrations:**
```bash
# Run all pending migrations
docker-compose run --rm api alembic upgrade head

# Alternative if Docker not built yet - use local Python:
# python -m alembic upgrade head
```

**Success Criteria:**
- Migrations apply without errors
- Output shows: "Running upgrade ... -> <revision>, <description>"

**Verify migrations applied:**
```bash
# Connect to database
docker exec -it corporate-intel-postgres psql -U intel_user -d corporate_intel

# Check tables created
\dt

# Should see tables like: alembic_version, companies, users, etc.
```

**Expected Tables:**
- alembic_version
- users
- companies
- sec_filings
- financial_metrics
- news_articles
- market_data
- (etc.)

**Troubleshooting:**
- "API container not built": Build it with `docker-compose build api`
- Migration errors: Check `alembic/env.py` has correct database URL
- Connection errors: Verify POSTGRES_HOST=postgres in docker-compose.yml

**Time: 10 minutes**

---

### Step 2.3: Seed Initial Data (Optional) (5 min)

**Create a test user and company:**
```bash
# Connect to database
docker exec -it corporate-intel-postgres psql -U intel_user -d corporate_intel

# Insert test data
INSERT INTO companies (ticker, name, cik, sector, industry)
VALUES ('AAPL', 'Apple Inc.', '0000320193', 'Technology', 'Consumer Electronics');

INSERT INTO companies (ticker, name, cik, sector, industry)
VALUES ('MSFT', 'Microsoft Corporation', '0000789019', 'Technology', 'Software');

# Verify
SELECT ticker, name, cik FROM companies;

\q
```

**Expected Output:**
- 2 rows inserted
- SELECT shows AAPL and MSFT

**Note:** This is optional - API can run without data initially

**Time: 5 minutes (OPTIONAL)**

---

## PHASE 3: API Startup (20 min)

### Step 3.1: Build API Container (5 min)

**Commands:**
```bash
# Build the API image
docker-compose build api

# Check build succeeded
docker images | grep corporate-intel-api
```

**Success Criteria:**
- Build completes without errors
- Image "corporate-intel-api:latest" exists

**Troubleshooting:**
- Dockerfile errors: Check Dockerfile syntax
- Build hangs: May need to increase Docker memory (Settings -> Resources)
- Python errors: Verify requirements.txt is complete

**Time: 5 minutes**

---

### Step 3.2: Start API Container (5 min)

**Commands:**
```bash
# Start the API (depends on postgres, redis, minio)
docker-compose up -d api

# Watch logs for startup
docker-compose logs -f api
```

**Success Criteria:**
- API shows "Uvicorn running on http://0.0.0.0:8000"
- "Starting Corporate Intelligence Platform API"
- Database initialized
- No error messages

**Expected Log Output:**
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Starting Corporate Intelligence Platform API
INFO:     Database connection pool initialized
INFO:     Redis cache initialized
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**Troubleshooting:**
- Health check failing: Check database connection
- Import errors: Rebuild with `docker-compose build --no-cache api`
- Port conflicts: Update API_PORT in .env

**Time: 5 minutes**

---

### Step 3.3: Verify API Health (5 min)

**Commands:**
```bash
# Basic health check
curl http://localhost:8002/health

# Database health check
curl http://localhost:8002/health/database

# Cache health check
curl http://localhost:8002/health/cache

# Check API documentation
# Open browser: http://localhost:8002/api/v1/docs
```

**Expected Responses:**

**Basic Health:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "environment": "development"
}
```

**Database Health:**
```json
{
  "status": "healthy",
  "database": "connected",
  "pool_size": 5,
  "migrations_applied": true
}
```

**Cache Health:**
```json
{
  "status": "healthy",
  "redis": "connected",
  "ping": "PONG"
}
```

**Troubleshooting:**
- 502 Bad Gateway: API container not started
- Connection errors: Check docker network
- 500 errors: Check API logs with `docker-compose logs api`

**Time: 5 minutes**

---

### Step 3.4: Alternative - Run Locally (Without Docker) (10 min)

**If Docker is problematic, run locally:**

```bash
# Create virtual environment
python -m venv venv
source venv/Scripts/activate  # Windows Git Bash

# Install dependencies
pip install -r requirements.txt

# Update .env for localhost
# Change:
POSTGRES_HOST=localhost
POSTGRES_PORT=5434
REDIS_HOST=localhost
REDIS_PORT=6381

# Run migrations
python -m alembic upgrade head

# Start API
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8002 --reload
```

**Success Criteria:**
- Uvicorn starts without errors
- Can access http://localhost:8002/health

**Time: 10 minutes (ALTERNATIVE)**

---

## PHASE 4: Basic Validation (30 min)

### Step 4.1: Test Authentication Endpoints (10 min)

**Register a test user:**
```bash
# Register new user
curl -X POST http://localhost:8002/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePass123!",
    "full_name": "Test User"
  }'
```

**Expected Response:**
```json
{
  "id": 1,
  "email": "test@example.com",
  "full_name": "Test User",
  "is_active": true
}
```

**Login and get token:**
```bash
# Login
curl -X POST http://localhost:8002/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=SecurePass123!"
```

**Expected Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Save the token for next steps:**
```bash
export TOKEN="<paste_access_token_here>"
```

**Time: 10 minutes**

---

### Step 4.2: Test Company Endpoints (10 min)

**Get list of companies:**
```bash
# List companies (with auth)
curl http://localhost:8002/api/v1/companies \
  -H "Authorization: Bearer $TOKEN"
```

**Expected Response:**
```json
{
  "items": [
    {
      "ticker": "AAPL",
      "name": "Apple Inc.",
      "cik": "0000320193",
      "sector": "Technology",
      "industry": "Consumer Electronics"
    },
    {
      "ticker": "MSFT",
      "name": "Microsoft Corporation",
      "cik": "0000789019",
      "sector": "Technology",
      "industry": "Software"
    }
  ],
  "total": 2,
  "page": 1,
  "size": 50
}
```

**Get single company:**
```bash
# Get Apple details
curl http://localhost:8002/api/v1/companies/AAPL \
  -H "Authorization: Bearer $TOKEN"
```

**Create a new company (if authorized):**
```bash
curl -X POST http://localhost:8002/api/v1/companies \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "GOOGL",
    "name": "Alphabet Inc.",
    "cik": "0001652044",
    "sector": "Technology",
    "industry": "Internet Services"
  }'
```

**Time: 10 minutes**

---

### Step 4.3: Quick Smoke Test (10 min)

**Test all main endpoints:**
```bash
# Health checks
curl http://localhost:8002/health
curl http://localhost:8002/health/database
curl http://localhost:8002/health/cache

# Get API docs (open in browser)
open http://localhost:8002/api/v1/docs

# Check metrics endpoint
curl http://localhost:8002/metrics

# Test companies endpoint
curl http://localhost:8002/api/v1/companies -H "Authorization: Bearer $TOKEN"

# Test filings endpoint (may be empty)
curl http://localhost:8002/api/v1/filings -H "Authorization: Bearer $TOKEN"

# Test metrics endpoint
curl http://localhost:8002/api/v1/metrics/AAPL -H "Authorization: Bearer $TOKEN"
```

**Success Criteria:**
- All endpoints return 200 or valid error responses
- API docs load successfully
- Authentication works (401 without token)
- Database queries execute

**Time: 10 minutes**

---

## COMPLETE QUICK START SCRIPT

**For those who want to run everything at once:**

```bash
#!/bin/bash
# Quick start script - Run all phases

set -e  # Exit on error

echo "=== PHASE 1: Infrastructure ==="
echo "Updating .env with non-conflicting ports..."
cp .env .env.backup
echo "" >> .env
echo "POSTGRES_PORT=5434" >> .env
echo "REDIS_PORT=6381" >> .env
echo "MINIO_PORT=9002" >> .env
echo "MINIO_CONSOLE_PORT=9003" >> .env
echo "API_PORT=8002" >> .env

echo "Starting Postgres and Redis..."
docker-compose up -d postgres redis

echo "Waiting for services to be healthy..."
sleep 30

echo "=== PHASE 2: Database Setup ==="
echo "Building API container..."
docker-compose build api

echo "Running migrations..."
docker-compose run --rm api alembic upgrade head

echo "=== PHASE 3: API Startup ==="
echo "Starting API..."
docker-compose up -d api

echo "Waiting for API to start..."
sleep 20

echo "=== PHASE 4: Validation ==="
echo "Testing health endpoints..."
curl -f http://localhost:8002/health || echo "Health check failed"
curl -f http://localhost:8002/health/database || echo "Database health check failed"
curl -f http://localhost:8002/health/cache || echo "Cache health check failed"

echo ""
echo "=== STARTUP COMPLETE ==="
echo "API Documentation: http://localhost:8002/api/v1/docs"
echo "Health Check: http://localhost:8002/health"
echo "Metrics: http://localhost:8002/metrics"
echo ""
echo "Next steps:"
echo "1. Register a user: POST http://localhost:8002/auth/register"
echo "2. Login: POST http://localhost:8002/auth/login"
echo "3. Explore API: http://localhost:8002/api/v1/docs"
```

---

## WHAT CAN WAIT (Not Needed Today)

**Skip these for initial startup:**

1. **MinIO Object Storage** - Not needed until file uploads
2. **Jaeger Tracing** - Observability can wait
3. **Prometheus/Grafana** - Monitoring not critical for dev
4. **Data Ingestion** - Can manually test with sample data
5. **Production SSL Certificates** - Development only
6. **Redis Cloud** - Local Redis is fine for dev
7. **Comprehensive Test Suite** - Basic smoke tests sufficient

**Focus on:**
- Database up and migrated
- Redis connected
- API responding to requests
- Basic CRUD operations working

---

## TROUBLESHOOTING GUIDE

### Database Connection Errors

**Symptom:** "could not connect to server"
```bash
# Check if postgres is running
docker ps | grep postgres

# Check logs
docker logs corporate-intel-postgres

# Verify port
netstat -ano | findstr :5434

# Test connection manually
docker exec -it corporate-intel-postgres psql -U intel_user -d corporate_intel
```

### Redis Connection Errors

**Symptom:** "Connection refused to Redis"
```bash
# Check Redis status
docker ps | grep redis

# Test connection
docker exec -it corporate-intel-redis redis-cli ping

# Check configuration
docker exec -it corporate-intel-redis redis-cli CONFIG GET maxmemory
```

### API Won't Start

**Symptom:** Container exits or unhealthy
```bash
# Check detailed logs
docker-compose logs -f api

# Check if port is in use
netstat -ano | findstr :8002

# Rebuild without cache
docker-compose build --no-cache api

# Run in foreground to see errors
docker-compose up api
```

### Migration Errors

**Symptom:** "Target database is not up to date"
```bash
# Check current revision
docker-compose run --rm api alembic current

# Check migration history
docker-compose run --rm api alembic history

# Force to head (CAREFUL - dev only)
docker-compose run --rm api alembic stamp head
docker-compose run --rm api alembic upgrade head
```

---

## SUCCESS CHECKLIST

After completing all phases, verify:

- [ ] Postgres running on port 5434 (healthy)
- [ ] Redis running on port 6381 (healthy)
- [ ] API running on port 8002 (healthy)
- [ ] Database migrations applied
- [ ] Health endpoints responding
- [ ] Can register and login user
- [ ] Can query companies endpoint
- [ ] API documentation accessible
- [ ] No critical errors in logs

**Total Time: 2-3 hours (depending on troubleshooting)**

---

## NEXT STEPS AFTER STARTUP

Once running, focus on:

1. **Data Ingestion:** Run scripts to populate companies and filings
2. **Frontend:** Set up basic UI to interact with API
3. **Testing:** Write integration tests for critical paths
4. **Documentation:** Add examples to API docs
5. **Deployment:** Prepare for staging environment

**For today, a working API with basic CRUD is SUCCESS!**
