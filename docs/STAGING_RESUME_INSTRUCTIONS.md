# Staging Environment - Resume Instructions
**Date**: October 17, 2025
**Status**: ⚠️ **DOCKER RESTART REQUIRED**

---

## Current Situation

**Problem**: Docker Desktop API is malfunctioning (500 errors on all requests)
**Impact**: Cannot manage containers via docker-compose
**Solution**: Restart Docker Desktop

---

## Quick Resume Steps

### Step 1: Restart Docker Desktop (2 minutes)

1. **Exit Docker Desktop**
   - Right-click Docker icon in system tray
   - Select "Quit Docker Desktop"
   - Wait 10 seconds

2. **Restart Docker Desktop**
   - Start Docker Desktop from Start Menu
   - Wait for "Docker Desktop is running" status
   - Green icon in system tray = ready

3. **Verify Docker Works**
   ```bash
   docker version
   docker ps -a
   ```

   ✅ If these commands work → Continue to Step 2
   ❌ If still failing → See Troubleshooting section

### Step 2: Start Staging Environment (3 minutes)

```bash
cd C:\Users\brand\Development\Project_Workspace\active-development\corporate_intel

# Start all staging services
docker-compose -f docker-compose.staging.yml --env-file .env.staging up -d

# Wait for services to be healthy (30 seconds)
timeout 30

# Check status
docker-compose -f docker-compose.staging.yml ps
```

**Expected Output:**
```
corporate-intel-staging-api        Up (healthy)   0.0.0.0:8004->8000/tcp
corporate-intel-staging-postgres   Up (healthy)   0.0.0.0:5435->5432/tcp
corporate-intel-staging-redis      Up (healthy)   0.0.0.0:6382->6379/tcp
corporate-intel-staging-prometheus Up             0.0.0.0:9091->9090/tcp
corporate-intel-staging-grafana    Up             0.0.0.0:3001->3000/tcp
```

### Step 3: Run Validation Tests (5 minutes)

**Quick Database Test:**
```bash
python scripts/quick_db_test.py
```

**Expected Output:**
```
================================================================================
QUICK DATABASE TEST - Corporate Intel Staging
================================================================================

1. Connecting to database...
   ✅ Connected successfully!

2. Checking database schema...
   ✅ Found 13 tables

3. Loading sample companies...
   ✓ Inserted: AAPL - Apple Inc.
   ✓ Inserted: MSFT - Microsoft Corporation
   ✓ Inserted: GOOGL - Alphabet Inc.
   ✓ Inserted: CHGG - Chegg, Inc.
   ✓ Inserted: DUOL - Duolingo, Inc.

   ✅ Success! Inserted: 5, Updated: 0
   ✅ Total companies in database: 5

================================================================================
✅ DATABASE TEST PASSED - Staging environment is operational!
================================================================================
```

**Full API Test:**
```bash
python scripts/test_staging_api.py lsZXGgU92KhK5VqR
```

**Expected Output:**
```
================================================================================
TASK A: Testing API Health
================================================================================

📡 Testing: http://localhost:8004/health
✅ Status Code: 200
✅ Response: {"status":"healthy","version":"0.1.0","environment":"staging"}

================================================================================
TEST SUMMARY
================================================================================

Results: 5/5 tests passed

✅ PASS  Api Health
✅ PASS  Api Docs
✅ PASS  Database Connection
✅ PASS  Database Schema
✅ PASS  Sample Data Loaded

🎉 ALL TESTS PASSED - Staging environment is operational!
```

### Step 4: Access Services

Once tests pass, you can access:

| Service | URL | Credentials |
|---------|-----|-------------|
| **API Docs** | http://localhost:8004/api/v1/docs | N/A |
| **API Health** | http://localhost:8004/health | N/A |
| **Grafana** | http://localhost:3001 | admin / (see .env.staging) |
| **Prometheus** | http://localhost:9091 | N/A |
| **Database** | localhost:5435 | intel_staging_user / lsZXGgU92KhK5VqR |

---

## Next: Task A → B → C

### ✅ Task A: Test API & Load Sample Data (READY)

Commands created and ready to run after Docker restart:
- `python scripts/quick_db_test.py` - Quick validation
- `python scripts/test_staging_api.py lsZXGgU92KhK5VqR` - Full test suite

**Sample companies that will be loaded:**
1. AAPL - Apple Inc. (Technology)
2. MSFT - Microsoft Corporation (Technology)
3. GOOGL - Alphabet Inc. (Technology)
4. CHGG - Chegg, Inc. (EdTech)
5. DUOL - Duolingo, Inc. (EdTech)

### 📋 Task B: Run SEC Filing Ingestion (PENDING)

After Task A passes:
```bash
# Enter API container
docker exec -it corporate-intel-staging-api bash

# Run SEC ingestion for one company
python -m src.pipeline.run_sec_ingestion --ticker CHGG --forms 10-K --limit 1

# Or use Python script directly
python -c "
from src.pipeline.run_sec_ingestion import run_sec_ingestion
import asyncio
asyncio.run(run_sec_ingestion(ticker='CHGG', forms=['10-K'], limit=1))
"
```

**Expected Duration**: 2-5 minutes per filing
**Expected Output**: SEC filing data in `sec_filings` table

### 📋 Task C: Run Integration Tests (PENDING)

```bash
# Run comprehensive integration tests
docker-compose -f docker-compose.staging.yml exec api pytest tests/integration/ -v

# Or specific test suites
pytest tests/integration/test_api_endpoints.py -v
pytest tests/integration/test_data_pipeline.py -v
pytest tests/integration/test_database.py -v
```

**Expected**: All integration tests should pass

---

## Troubleshooting

### Docker Version Shows API Error
```bash
# Try resetting Docker settings
# Docker Desktop → Settings → Troubleshoot → "Restart Docker Desktop"
```

### Containers Won't Start
```bash
# Check logs
docker-compose -f docker-compose.staging.yml logs api
docker-compose -f docker-compose.staging.yml logs postgres

# Common fixes:
# 1. Port conflict - check if ports are in use
netstat -ano | findstr ":8004"
netstat -ano | findstr ":5435"

# 2. Previous containers stuck - force cleanup
docker-compose -f docker-compose.staging.yml down -v
docker-compose -f docker-compose.staging.yml up -d
```

### Database Connection Fails
```bash
# Wait for postgres to be fully ready
docker-compose -f docker-compose.staging.yml logs postgres | grep "ready to accept connections"

# Manual connection test
psql -h localhost -p 5435 -U intel_staging_user -d corporate_intel_staging
# Password: lsZXGgU92KhK5VqR
```

### API Returns 500 Errors
```bash
# Check API logs for errors
docker logs corporate-intel-staging-api -f

# Common causes:
# - Database not connected
# - Missing environment variables
# - Redis not connected
# - MinIO not configured
```

---

## Files Created During This Session

### Test Scripts (Ready to Use)
1. **`scripts/test_staging_api.py`** (500+ lines)
   - Comprehensive API and database testing
   - Loads sample company data
   - Verifies schema and hypertables
   - Usage: `python scripts/test_staging_api.py lsZXGgU92KhK5VqR`

2. **`scripts/quick_db_test.py`** (150+ lines)
   - Quick database connectivity check
   - Loads 5 sample companies
   - Verifies all tables
   - Usage: `python scripts/quick_db_test.py`

### Documentation
3. **`docs/DOCKER_DESKTOP_ISSUE_REPORT.md`**
   - Detailed analysis of Docker API issue
   - Root cause and solutions
   - Workarounds

4. **`docs/STAGING_RESUME_INSTRUCTIONS.md`** (this file)
   - Step-by-step resume guide
   - Quick reference for next steps

---

## Success Criteria

✅ **Task A Complete** when:
- [ ] Docker Desktop API working (`docker ps` succeeds)
- [ ] All staging containers healthy
- [ ] `quick_db_test.py` passes
- [ ] `test_staging_api.py` passes
- [ ] 5 sample companies loaded
- [ ] API responding on port 8004
- [ ] Database accessible on port 5435

✅ **Task B Complete** when:
- [ ] SEC filing ingested for CHGG
- [ ] Data appears in `sec_filings` table
- [ ] No pipeline errors
- [ ] Filing data validated

✅ **Task C Complete** when:
- [ ] Integration tests pass
- [ ] API endpoints tested
- [ ] Database operations validated
- [ ] Pipeline functionality confirmed

---

## Estimated Timeline

| Task | Duration | Status |
|------|----------|--------|
| Docker Desktop Restart | 2 min | ⏸️ Pending |
| Start Staging Environment | 3 min | ⏸️ Pending |
| Run Validation Tests (A) | 5 min | ⏸️ Pending |
| SEC Filing Ingestion (B) | 5 min | ⏸️ Pending |
| Integration Tests (C) | 10 min | ⏸️ Pending |
| **Total** | **25 min** | **Ready to start** |

---

## Quick Commands Reference

```bash
# Check Docker status
docker ps

# Start staging
docker-compose -f docker-compose.staging.yml --env-file .env.staging up -d

# Check logs
docker-compose -f docker-compose.staging.yml logs -f api

# Run tests
python scripts/quick_db_test.py
python scripts/test_staging_api.py lsZXGgU92KhK5VqR

# Stop staging
docker-compose -f docker-compose.staging.yml down
```

---

**Next Action**: Restart Docker Desktop and run Step 1 commands
**Expected Total Time**: ~25 minutes from Docker restart to Task C complete
**Status**: ⏸️ **READY TO RESUME**

---

**Created**: October 17, 2025
**Last Updated**: October 17, 2025
**Session**: A→B→C Execution Plan
