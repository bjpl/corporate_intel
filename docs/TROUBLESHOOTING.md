# Corporate Intel - Troubleshooting Guide

Quick solutions to common startup problems.

---

## Problem: Port Already in Use

**Symptoms:**
- `Error: port is already allocated`
- Container fails to start
- `docker-compose up` exits with error

**Solutions:**

### Option 1: Change Ports in .env
```bash
# Edit .env and add:
POSTGRES_PORT=5434
REDIS_PORT=6381
MINIO_PORT=9002
API_PORT=8002

# Restart services
docker-compose down
docker-compose up -d
```

### Option 2: Find and Stop Conflicting Process (Windows)
```bash
# Find process using port 5432
netstat -ano | findstr :5432

# Kill the process (replace PID)
taskkill /PID <pid> /F
```

### Option 3: Stop Other Docker Containers
```bash
# See what's running
docker ps

# Stop specific container
docker stop colombia_intel_db

# Or stop all running containers
docker stop $(docker ps -q)
```

---

## Problem: Database Connection Failed

**Symptoms:**
- `could not connect to server`
- `Connection refused`
- API health check fails

**Solutions:**

### 1. Check if Postgres is Running
```bash
# Check container status
docker ps | grep postgres

# Should show (healthy)
# If not healthy, check logs
docker logs corporate-intel-postgres
```

### 2. Verify Database Credentials
```bash
# Check .env file
cat .env | grep POSTGRES

# Should match docker-compose.yml settings
```

### 3. Test Connection Manually
```bash
# From host
docker exec corporate-intel-postgres pg_isready -U intel_user -d corporate_intel

# Connect with psql
docker exec -it corporate-intel-postgres psql -U intel_user -d corporate_intel

# Inside psql:
\l      # List databases
\conninfo   # Connection info
```

### 4. Recreate Database
```bash
# CAREFUL - This deletes all data
docker-compose down -v
docker-compose up -d postgres
docker-compose run --rm api alembic upgrade head
```

---

## Problem: Redis Connection Failed

**Symptoms:**
- `Error connecting to Redis`
- Cache health check fails
- API logs show Redis errors

**Solutions:**

### 1. Check Redis Status
```bash
# Check container
docker ps | grep redis

# Test connection
docker exec corporate-intel-redis redis-cli ping
# Should return: PONG
```

### 2. Check Redis Logs
```bash
docker logs corporate-intel-redis
```

### 3. Restart Redis
```bash
docker-compose restart redis

# Wait a few seconds, then test
docker exec corporate-intel-redis redis-cli ping
```

### 4. Skip Redis (Temporary)
The API can run without Redis for basic testing. Redis failures are logged as warnings but won't stop the API.

---

## Problem: API Container Exits Immediately

**Symptoms:**
- `docker ps` doesn't show API container
- Container status is "Exited"
- API health check fails

**Solutions:**

### 1. Check API Logs
```bash
# View last 50 lines
docker-compose logs --tail=50 api

# Follow logs in real-time
docker-compose logs -f api
```

### 2. Common Errors and Fixes

**Import Error:**
```
ModuleNotFoundError: No module named 'X'
```
**Fix:**
```bash
# Rebuild with no cache
docker-compose build --no-cache api
docker-compose up -d api
```

**Database Not Ready:**
```
sqlalchemy.exc.OperationalError: could not connect
```
**Fix:**
```bash
# Wait for postgres to be healthy first
docker-compose up -d postgres
sleep 30
docker-compose up -d api
```

**Environment Variable Missing:**
```
ValidationError: X field required
```
**Fix:**
```bash
# Check .env has all required variables
cat .env | grep SECRET_KEY
cat .env | grep POSTGRES

# Compare with .env.example
```

### 3. Run API Locally to See Errors
```bash
# Activate virtual environment
python -m venv venv
source venv/Scripts/activate  # Windows Git Bash

# Install dependencies
pip install -r requirements.txt

# Run locally to see detailed errors
python -m uvicorn src.api.main:app --reload
```

---

## Problem: Migrations Fail

**Symptoms:**
- `alembic upgrade head` fails
- "Target database is not up to date"
- Migration errors in logs

**Solutions:**

### 1. Check Current Migration Status
```bash
# See current version
docker-compose run --rm api alembic current

# See migration history
docker-compose run --rm api alembic history
```

### 2. Check Database Tables
```bash
docker exec -it corporate-intel-postgres psql -U intel_user -d corporate_intel

# Inside psql:
\dt                          # List tables
SELECT * FROM alembic_version;   # Check version
```

### 3. Reset Migrations (Development Only)
```bash
# CAREFUL - This deletes all data
docker-compose down -v
docker-compose up -d postgres
sleep 20

# Run migrations fresh
docker-compose run --rm api alembic upgrade head
```

### 4. Fix Specific Migration Error
```bash
# If stuck on a specific version, can stamp it
docker-compose run --rm api alembic stamp head

# Then try upgrade again
docker-compose run --rm api alembic upgrade head
```

---

## Problem: API Health Check Fails

**Symptoms:**
- `curl http://localhost:8002/health` fails
- Container shows (unhealthy)
- Can't access API docs

**Solutions:**

### 1. Check if API is Actually Running
```bash
# Check process inside container
docker exec corporate-intel-api ps aux

# Should see uvicorn process
```

### 2. Test Health Endpoint
```bash
# Try with verbose output
curl -v http://localhost:8002/health

# Check what port API is on
docker port corporate-intel-api
```

### 3. Check API Logs
```bash
docker-compose logs -f api

# Look for:
# - "Uvicorn running on..."
# - "Application startup complete"
# - Any error messages
```

### 4. Restart API
```bash
docker-compose restart api
sleep 20
curl http://localhost:8002/health
```

---

## Problem: Can't Access API Documentation

**Symptoms:**
- http://localhost:8002/api/v1/docs returns 404
- Page won't load
- Connection refused

**Solutions:**

### 1. Verify API Port
```bash
# Check what port API is using
docker ps | grep corporate-intel-api

# Try the mapped port
curl http://localhost:<PORT>/api/v1/docs
```

### 2. Check API Prefix Settings
```bash
# In .env, check:
API_V1_PREFIX=/api/v1

# Documentation should be at:
# http://localhost:8002/api/v1/docs
```

### 3. Try Alternative Endpoints
```bash
# Try ReDoc instead
http://localhost:8002/api/v1/redoc

# Try basic health
http://localhost:8002/health

# Try OpenAPI JSON
http://localhost:8002/api/v1/openapi.json
```

---

## Problem: Authentication Fails

**Symptoms:**
- Can't register users
- Login returns 401
- Token doesn't work

**Solutions:**

### 1. Check SECRET_KEY in .env
```bash
# Must be set
grep SECRET_KEY .env

# If missing, generate one:
python -c "import secrets; print(secrets.token_hex(32))"
# Add to .env
```

### 2. Test Registration
```bash
curl -X POST http://localhost:8002/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePass123!",
    "full_name": "Test User"
  }'
```

### 3. Test Login
```bash
curl -X POST http://localhost:8002/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=SecurePass123!"
```

### 4. Check Database Users Table
```bash
docker exec -it corporate-intel-postgres psql -U intel_user -d corporate_intel

# Check if users table exists and has data
SELECT email, is_active FROM users;
```

---

## Problem: Docker Build Fails

**Symptoms:**
- `docker-compose build` fails
- Build errors in output
- Image not created

**Solutions:**

### 1. Check Dockerfile Syntax
```bash
# Verify Dockerfile exists and is valid
cat Dockerfile
```

### 2. Clean Docker Cache
```bash
# Remove old images
docker system prune -a

# Rebuild from scratch
docker-compose build --no-cache api
```

### 3. Check Disk Space
```bash
# Docker can fail if disk is full
docker system df

# Clean up if needed
docker system prune -a --volumes
```

### 4. Build with Verbose Output
```bash
# See detailed build logs
docker-compose build --progress=plain api
```

---

## Problem: Container is Unhealthy

**Symptoms:**
- `docker ps` shows (unhealthy)
- Health check keeps failing

**Solutions:**

### 1. Check Health Check Configuration
```bash
# View health check in docker-compose.yml
# For API, it should curl /health endpoint
```

### 2. Test Health Check Manually
```bash
# Run health check command inside container
docker exec corporate-intel-api curl -f http://localhost:8000/health
```

### 3. Increase Health Check Timing
```bash
# In docker-compose.yml, increase:
# - start_period: 40s -> 60s
# - timeout: 10s -> 20s
# - interval: 30s -> 60s
```

---

## Problem: Data Not Persisting

**Symptoms:**
- Data disappears after restart
- Changes don't save
- Migrations need to be re-run

**Solutions:**

### 1. Check Docker Volumes
```bash
# List volumes
docker volume ls | grep corporate-intel

# Should see:
# - corporate-intel-postgres-data
# - corporate-intel-redis-data
```

### 2. Verify Volume Mounts
```bash
# Check volume is mounted
docker inspect corporate-intel-postgres | grep Mounts -A 20
```

### 3. Don't Use -v Flag
```bash
# This deletes volumes!
docker-compose down -v  # DON'T USE unless you want to delete data

# Use this instead:
docker-compose down  # Keeps volumes
```

---

## Emergency Reset (Nuclear Option)

**When all else fails:**

```bash
# 1. Stop everything
docker-compose down -v

# 2. Remove all project containers and volumes
docker container prune -f
docker volume prune -f

# 3. Rebuild from scratch
docker-compose build --no-cache

# 4. Start fresh
docker-compose up -d postgres redis
sleep 30
docker-compose run --rm api alembic upgrade head
docker-compose up -d api

# 5. Verify
curl http://localhost:8002/health
```

---

## Getting Help

If none of these solutions work:

1. **Check Logs:**
   ```bash
   docker-compose logs -f
   ```

2. **Check Docker Status:**
   ```bash
   docker ps -a
   docker-compose ps
   ```

3. **Check .env Configuration:**
   ```bash
   cat .env
   ```

4. **Check Docker Resources:**
   - Docker Desktop -> Settings -> Resources
   - Increase memory to 4GB+
   - Increase CPU to 2+

5. **Restart Docker:**
   - Docker Desktop -> Restart
   - Wait for Docker to fully start

6. **Check Docker Version:**
   ```bash
   docker --version
   docker-compose --version
   ```

---

## Common Error Messages and Solutions

| Error | Likely Cause | Solution |
|-------|--------------|----------|
| `port is already allocated` | Port conflict | Change ports in .env |
| `could not connect to server` | Database not ready | Wait 30s, check postgres logs |
| `Connection refused` | Service not started | Check `docker ps` |
| `ModuleNotFoundError` | Missing dependency | Rebuild: `docker-compose build --no-cache api` |
| `ValidationError` | Missing .env variable | Check .env has all required vars |
| `Target database is not up to date` | Migration issue | Run `alembic upgrade head` |
| `permission denied` | File permissions | Run with sudo or fix permissions |
| `network not found` | Docker network issue | `docker-compose down && docker-compose up` |
| `unhealthy` | Health check failing | Check logs, increase timeouts |
| `no space left on device` | Disk full | Clean: `docker system prune -a` |

---

**Still stuck? Check the logs first - they usually tell you exactly what's wrong!**

```bash
docker-compose logs -f
```
