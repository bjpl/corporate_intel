# Corporate Intel - Startup Checklist (2-3 Hours)

**Quick Reference Guide for Getting Running TODAY**

---

## Prerequisites Check

- [ ] Docker installed and running
- [ ] Docker Compose installed
- [ ] Python 3.10+ installed (for local development)
- [ ] `.env` file exists in project root
- [ ] Git Bash or WSL (for running shell scripts on Windows)

---

## Option 1: Automated Startup (RECOMMENDED)

**Use the quick-startup script:**

```bash
# Linux/Mac/Git Bash
./scripts/quick-startup.sh

# Windows Command Prompt
scripts\quick-startup.bat
```

**Expected time:** 30-45 minutes (mostly waiting for containers)

---

## Option 2: Manual Startup (Step-by-Step)

### PHASE 1: Infrastructure (30 min)

#### 1. Handle Port Conflicts (5 min)

**Check what's running:**
```bash
docker ps
netstat -ano | grep -E ":(5432|6379|8000|9000)"
```

**Update .env ports if needed:**
```bash
# Add these to .env to avoid conflicts
echo "POSTGRES_PORT=5434" >> .env
echo "REDIS_PORT=6381" >> .env
echo "API_PORT=8002" >> .env
```

- [ ] Ports checked and configured
- [ ] No conflicts remain

#### 2. Start Core Services (15 min)

```bash
# Start database and cache
docker-compose up -d postgres redis

# Wait for health checks (watch for "healthy" status)
docker ps

# Verify connections
docker exec corporate-intel-postgres pg_isready -U intel_user
docker exec corporate-intel-redis redis-cli ping
```

**Success criteria:**
- [ ] Postgres shows "accepting connections"
- [ ] Redis responds with "PONG"
- [ ] Both containers show (healthy) in `docker ps`

#### 3. Optional: Start MinIO (10 min)

```bash
docker-compose up -d minio
```

- [ ] MinIO running (optional - can skip for now)

---

### PHASE 2: Database Setup (20 min)

#### 1. Build API Container (5 min)

```bash
docker-compose build api
```

- [ ] API container built successfully
- [ ] No build errors

#### 2. Run Migrations (10 min)

```bash
# Run database migrations
docker-compose run --rm api alembic upgrade head

# Verify migrations applied
docker exec corporate-intel-postgres psql -U intel_user -d corporate_intel -c "\dt"
```

**Success criteria:**
- [ ] Migrations run without errors
- [ ] `alembic_version` table exists
- [ ] Core tables created (companies, users, etc.)

#### 3. Seed Test Data (5 min - OPTIONAL)

```bash
docker exec corporate-intel-postgres psql -U intel_user -d corporate_intel <<-SQL
    INSERT INTO companies (ticker, name, cik, sector, industry, created_at, updated_at)
    VALUES
        ('AAPL', 'Apple Inc.', '0000320193', 'Technology', 'Consumer Electronics', NOW(), NOW()),
        ('MSFT', 'Microsoft Corporation', '0000789019', 'Technology', 'Software', NOW(), NOW())
    ON CONFLICT (ticker) DO NOTHING;
SQL
```

- [ ] Test data inserted (optional)

---

### PHASE 3: API Startup (20 min)

#### 1. Start API (10 min)

```bash
# Start the API container
docker-compose up -d api

# Watch logs for startup
docker-compose logs -f api
```

**Look for:**
- "Uvicorn running on http://0.0.0.0:8000"
- "Starting Corporate Intelligence Platform API"
- "Application startup complete"

- [ ] API container started
- [ ] No error messages in logs
- [ ] Shows (healthy) in `docker ps`

#### 2. Verify Health (10 min)

```bash
# Test health endpoints
curl http://localhost:8002/health
curl http://localhost:8002/health/database
curl http://localhost:8002/health/cache

# Open API documentation
# Browser: http://localhost:8002/api/v1/docs
```

**Success criteria:**
- [ ] Health endpoint returns `{"status": "healthy"}`
- [ ] Database health check passes
- [ ] Cache health check passes
- [ ] API docs load successfully

---

### PHASE 4: Basic Testing (30 min)

#### 1. Test Authentication (10 min)

**Register a user:**
```bash
curl -X POST http://localhost:8002/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePass123!",
    "full_name": "Test User"
  }'
```

**Login:**
```bash
curl -X POST http://localhost:8002/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=SecurePass123!"
```

**Save the access token for next steps**

- [ ] User registration works
- [ ] Login returns access token
- [ ] Token saved for testing

#### 2. Test API Endpoints (10 min)

```bash
# Set your token
export TOKEN="paste_your_token_here"

# Test companies endpoint
curl http://localhost:8002/api/v1/companies \
  -H "Authorization: Bearer $TOKEN"

# Test single company
curl http://localhost:8002/api/v1/companies/AAPL \
  -H "Authorization: Bearer $TOKEN"
```

- [ ] Companies endpoint returns data
- [ ] Single company lookup works
- [ ] Authentication required (401 without token)

#### 3. Smoke Test All Endpoints (10 min)

Use the interactive API docs: http://localhost:8002/api/v1/docs

**Test these endpoints:**
- [ ] GET /api/v1/companies
- [ ] GET /api/v1/companies/{ticker}
- [ ] GET /api/v1/filings
- [ ] GET /api/v1/metrics/{ticker}
- [ ] GET /api/v1/intelligence/analyze

---

## Success Criteria - YOU'RE DONE!

**All of these should be true:**

- [ ] PostgreSQL running and healthy
- [ ] Redis running and healthy
- [ ] API running and healthy
- [ ] Database migrations applied
- [ ] Can access API documentation
- [ ] Can register and login users
- [ ] Can query companies endpoint
- [ ] No critical errors in logs

**Total time:** 2-3 hours including troubleshooting

---

## Quick Commands Reference

```bash
# View all services status
docker-compose ps

# View API logs
docker-compose logs -f api

# View database logs
docker-compose logs -f postgres

# Restart API
docker-compose restart api

# Stop everything
docker-compose down

# Stop and remove volumes (CAREFUL - deletes data)
docker-compose down -v

# Connect to database
docker exec -it corporate-intel-postgres psql -U intel_user -d corporate_intel

# Check Redis
docker exec -it corporate-intel-redis redis-cli

# Rebuild API
docker-compose build --no-cache api
```

---

## Troubleshooting Quick Fixes

**API won't start:**
```bash
# Check logs
docker-compose logs api

# Rebuild
docker-compose build --no-cache api
docker-compose up -d api
```

**Database connection errors:**
```bash
# Check if postgres is running
docker ps | grep postgres

# Verify connection
docker exec corporate-intel-postgres pg_isready -U intel_user
```

**Port conflicts:**
```bash
# Find what's using the port (Windows)
netstat -ano | findstr :8002

# Kill the process
taskkill /PID <pid> /F

# Or change ports in .env
```

**Migrations fail:**
```bash
# Check current status
docker-compose run --rm api alembic current

# Force to latest (development only)
docker-compose run --rm api alembic stamp head
docker-compose run --rm api alembic upgrade head
```

---

## What You Have After Startup

**Running Services:**
- PostgreSQL with TimescaleDB (port 5434)
- Redis cache (port 6381)
- FastAPI application (port 8002)

**Available Endpoints:**
- API Docs: http://localhost:8002/api/v1/docs
- Health Check: http://localhost:8002/health
- Metrics: http://localhost:8002/metrics

**Database:**
- Tables created for companies, filings, metrics, users
- Test data available (AAPL, MSFT if seeded)

**Next Steps:**
1. Add more test data
2. Set up frontend (if needed)
3. Configure data ingestion
4. Deploy to staging

---

## Important Files

- `docker-compose.yml` - Service definitions
- `.env` - Configuration and secrets
- `src/api/main.py` - FastAPI application
- `alembic/` - Database migrations
- `scripts/quick-startup.sh` - Automated startup script

---

## Emergency Stop

```bash
# Stop everything immediately
docker-compose down

# Stop and remove all data
docker-compose down -v

# Stop but keep data
docker-compose stop
```

---

**You're ready to start developing! 🚀**
