# Solo Developer Deployment Guide
## Corporate Intelligence Platform - Step-by-Step Setup

**Target Audience:** Single developer (you) setting up the complete platform locally
**Time Required:** 30-45 minutes
**Difficulty:** Intermediate

---

## Prerequisites Check

Before starting, verify you have these installed:

```bash
# Check versions
python --version          # Need 3.11+
docker --version         # Need 20.10+
docker-compose --version # Need 2.0+
git --version           # Any recent version
```

**If missing, install:**
- **Python 3.11+**: https://www.python.org/downloads/
- **Docker Desktop**: https://www.docker.com/products/docker-desktop/
- **Git**: https://git-scm.com/downloads

---

## Step 1: Clone the Repository (Already Done!)

You already have it at:
```bash
cd /mnt/c/Users/brand/Development/Project_Workspace/active-development/corporate_intel
```

---

## Step 2: Create Environment File

**Create `.env` file** (copy from template):

```bash
# Copy the example
cp .env.example .env

# Open in your editor
code .env  # or nano .env, vim .env, etc.
```

**Edit `.env` with these REQUIRED settings:**

```bash
# ============================================
# REQUIRED: Generate a secure secret key
# ============================================
# Run this command to generate:
# python -c "import secrets; print(secrets.token_urlsafe(32))"

SECRET_KEY=YOUR_GENERATED_SECRET_KEY_HERE  # ← REPLACE THIS!

# ============================================
# Database - Use these defaults for local dev
# ============================================
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=intel_user
POSTGRES_PASSWORD=ChangeMe123!  # ← CHANGE THIS!
POSTGRES_DB=corporate_intel

# ============================================
# Redis - Defaults work fine
# ============================================
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=  # Leave empty for local dev

# ============================================
# MinIO - For local development
# ============================================
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin  # ← CHANGE THIS!
MINIO_SECRET_KEY=minioadmin123  # ← CHANGE THIS!
MINIO_SECURE=false

# ============================================
# OPTIONAL: External APIs (add if you have keys)
# ============================================
# SEC EDGAR is free, just needs user agent
SEC_USER_AGENT=Corporate Intel Bot/1.0 (your.email@example.com)  # ← Add your email

# Alpha Vantage (optional - for stock data)
# Get free key: https://www.alphavantage.co/support/#api-key
ALPHA_VANTAGE_API_KEY=  # ← Add if you have one

# ============================================
# Application Settings
# ============================================
ENVIRONMENT=development
DEBUG=true
APP_NAME=Corporate Intelligence Platform
API_V1_PREFIX=/api/v1
```

**Generate SECRET_KEY:**
```bash
# Run this command and copy the output
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Example output: abc123xyz789_RANDOM_STRING_HERE
# Copy this into your .env file as SECRET_KEY
```

---

## Step 3: Start the Development Environment

**Option A: Use the Makefile (Easiest)**

```bash
# Start all services (Docker Compose)
make dev-up

# This will start:
# - PostgreSQL with TimescaleDB
# - Redis
# - MinIO
# - Prefect
# - pgAdmin (database UI at http://localhost:5050)
# - Mailhog (email testing at http://localhost:8025)
```

**Option B: Manual Docker Compose**

```bash
# Start services in background
docker-compose -f docker-compose.dev.yml up -d

# View logs
docker-compose -f docker-compose.dev.yml logs -f
```

**Wait for services to be healthy (~30 seconds):**

```bash
# Check status
docker-compose -f docker-compose.dev.yml ps

# All should show "healthy" status
```

---

## Step 4: Install Python Dependencies

```bash
# Create virtual environment
python -m venv venv

# Activate it
# On Windows (PowerShell):
venv\Scripts\Activate.ps1

# On Windows (CMD):
venv\Scripts\activate.bat

# On macOS/Linux/WSL:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Verify installation
pip list | grep fastapi
pip list | grep sqlalchemy
```

---

## Step 5: Initialize Database

**Run database migrations:**

```bash
# Initialize Alembic (first time only)
alembic upgrade head

# You should see output like:
# INFO  [alembic.runtime.migration] Running upgrade -> abc123
# INFO  [alembic.runtime.migration] Running upgrade abc123 -> def456
```

**Verify database:**

```bash
# Using psql (if you have it)
psql postgresql://intel_user:ChangeMe123!@localhost:5432/corporate_intel

# Or use pgAdmin at http://localhost:5050
# Login: admin@admin.com / admin
# Add server: localhost:5432, intel_user, your password
```

---

## Step 6: Start the FastAPI Application

```bash
# Development server with hot reload
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# You should see:
# INFO:     Uvicorn running on http://0.0.0.0:8000
# INFO:     Application startup complete.
```

**Test it works:**

```bash
# In a new terminal
curl http://localhost:8000/health

# Should return:
# {"status":"healthy","version":"0.1.0"}
```

---

## Step 7: Access the Services

Open these URLs in your browser:

| Service | URL | Credentials |
|---------|-----|-------------|
| **API Docs** | http://localhost:8000/docs | None needed |
| **API Redoc** | http://localhost:8000/redoc | None needed |
| **pgAdmin** | http://localhost:5050 | admin@admin.com / admin |
| **MinIO Console** | http://localhost:9001 | minioadmin / minioadmin123 |
| **Mailhog** | http://localhost:8025 | None needed |
| **Prefect UI** | http://localhost:4200 | None needed |

---

## Step 8: Test the SEC Pipeline (Optional)

**Run a test SEC filing ingestion:**

```bash
# Create a test script
cat > test_sec_pipeline.py << 'EOF'
import asyncio
from src.pipeline.sec_ingestion import fetch_company_filings, store_filing
from src.db.session import get_session_factory

async def test_pipeline():
    # Test with Apple Inc (CIK: 0000320193)
    cik = "0000320193"

    print(f"Fetching filings for CIK: {cik}")
    filings = await fetch_company_filings(cik, form_type="10-K", count=1)

    print(f"Found {len(filings)} filings")
    for filing in filings:
        print(f"Filing: {filing.get('accessionNumber')} - {filing.get('form')}")

        # Store in database
        result = await store_filing(filing, cik)
        print(f"Stored filing: {result}")

if __name__ == "__main__":
    asyncio.run(test_pipeline())
EOF

# Run it
python test_sec_pipeline.py

# Should see:
# Fetching filings for CIK: 0000320193
# Found 1 filings
# Filing: 0000320193-23-000077 - 10-K
# Stored filing: <filing_id>
```

---

## Step 9: Run Tests (Optional)

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# View coverage report
open htmlcov/index.html  # macOS
start htmlcov/index.html  # Windows
```

---

## Step 10: Set Up Pre-commit Hooks (Optional but Recommended)

```bash
# Install pre-commit
pre-commit install

# Run on all files (first time)
pre-commit run --all-files

# Now it will run automatically on git commit
```

---

## Common Issues and Solutions

### Issue 1: Port Already in Use

**Error:** `Bind for 0.0.0.0:8000 failed: port is already allocated`

**Solution:**
```bash
# Find what's using the port
# Windows:
netstat -ano | findstr :8000

# macOS/Linux:
lsof -i :8000

# Kill the process or use a different port
uvicorn src.main:app --reload --port 8001
```

### Issue 2: Database Connection Failed

**Error:** `could not connect to server: Connection refused`

**Solution:**
```bash
# Check if PostgreSQL container is running
docker-compose -f docker-compose.dev.yml ps

# If not running, start it
docker-compose -f docker-compose.dev.yml up -d postgres

# Check logs
docker-compose -f docker-compose.dev.yml logs postgres
```

### Issue 3: SECRET_KEY Validation Error

**Error:** `SECRET_KEY must be at least 32 characters long`

**Solution:**
```bash
# Generate a new key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Update .env file with the generated key
```

### Issue 4: Module Import Errors

**Error:** `ModuleNotFoundError: No module named 'fastapi'`

**Solution:**
```bash
# Make sure virtual environment is activated
# You should see (venv) in your prompt

# If not, activate it:
source venv/bin/activate  # macOS/Linux/WSL
venv\Scripts\activate     # Windows

# Reinstall dependencies
pip install -r requirements.txt
```

---

## Daily Development Workflow

### Starting Work:

```bash
# 1. Navigate to project
cd /mnt/c/Users/brand/Development/Project_Workspace/active-development/corporate_intel

# 2. Activate virtual environment
source venv/bin/activate  # or venv\Scripts\activate on Windows

# 3. Start services
make dev-up

# 4. Start FastAPI
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### During Work:

```bash
# Run tests frequently
pytest tests/unit/test_config.py -v

# Check code quality
make lint  # or: black . && isort . && flake8

# View logs
make logs

# Access database shell
make db-shell
```

### Ending Work:

```bash
# Stop FastAPI (Ctrl+C)

# Stop Docker services
make dev-down

# Deactivate virtual environment
deactivate
```

---

## Useful Make Commands

```bash
make dev-up          # Start all services
make dev-down        # Stop all services
make logs            # View all logs
make shell           # Access app container shell
make db-shell        # Access PostgreSQL shell
make migrate         # Run database migrations
make test            # Run all tests
make lint            # Run linters
make clean           # Clean up containers and volumes
```

---

## Next Steps After Setup

1. **Explore the API:** http://localhost:8000/docs
2. **Run the SEC pipeline:** Ingest some company filings
3. **Check the database:** Use pgAdmin to see stored data
4. **Run tests:** Verify everything works
5. **Start developing:** Add new features!

---

## Getting Help

- **Documentation:** Check `docs/` directory
- **API Reference:** http://localhost:8000/docs
- **GitHub Issues:** https://github.com/bjpl/corporate_intel/issues
- **Logs:** `make logs` or `docker-compose -f docker-compose.dev.yml logs -f`

---

## Environment Variables Quick Reference

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `SECRET_KEY` | ✅ Yes | JWT signing key (32+ chars) | Generate with Python |
| `POSTGRES_PASSWORD` | ✅ Yes | Database password | ChangeMe123! |
| `POSTGRES_HOST` | ✅ Yes | Database host | localhost |
| `MINIO_ACCESS_KEY` | ✅ Yes | Object storage access | minioadmin |
| `MINIO_SECRET_KEY` | ✅ Yes | Object storage secret | minioadmin123 |
| `SEC_USER_AGENT` | ⚠️ Recommended | SEC API user agent | Your email |
| `ALPHA_VANTAGE_API_KEY` | ❌ Optional | Stock data API key | Get free key |
| `DEBUG` | ❌ Optional | Enable debug mode | true |
| `ENVIRONMENT` | ❌ Optional | Environment name | development |

---

**You're all set!** 🎉

The platform is now running locally and ready for development. Start with the API docs at http://localhost:8000/docs to explore the endpoints.
