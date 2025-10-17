# After Machine Restart - Quick Start Checklist
**Date**: October 17, 2025
**Status**: Ready to execute A→B→C plan

---

## ✅ What's Already Done (Committed & Pushed)

1. ✅ Diagnosed Docker Desktop API issue (500 errors)
2. ✅ Created test scripts (650+ lines)
   - `scripts/test_staging_api.py` - Full validation
   - `scripts/quick_db_test.py` - Quick DB test
3. ✅ Created comprehensive documentation
   - `docs/DOCKER_DESKTOP_ISSUE_REPORT.md`
   - `docs/STAGING_RESUME_INSTRUCTIONS.md`
4. ✅ All changes committed and pushed to GitHub

---

## 🚀 After Restart - Quick Steps (15 minutes total)

### Step 1: Verify Docker Works (1 min)
```bash
# Open Git Bash or terminal
docker version
docker ps
```

✅ **Success**: Commands work without 500 errors
❌ **Fail**: If still broken, try Docker Desktop → Settings → Troubleshoot → "Reset to Factory Defaults"

---

### Step 2: Start Staging Environment (3 min)
```bash
cd C:\Users\brand\Development\Project_Workspace\active-development\corporate_intel

# Start all services
docker-compose -f docker-compose.staging.yml --env-file .env.staging up -d

# Wait 30 seconds for health checks
timeout 30

# Check status (all should show "Up" or "Up (healthy)")
docker-compose -f docker-compose.staging.yml ps
```

**Expected Output:**
```
NAME                               STATUS              PORTS
corporate-intel-staging-api        Up (healthy)        0.0.0.0:8004->8000/tcp
corporate-intel-staging-postgres   Up (healthy)        0.0.0.0:5435->5432/tcp
corporate-intel-staging-redis      Up (healthy)        0.0.0.0:6382->6379/tcp
corporate-intel-staging-prometheus Up                  0.0.0.0:9091->9090/tcp
corporate-intel-staging-grafana    Up                  0.0.0.0:3001->3000/tcp
```

---

### Step 3: Run Quick Database Test (2 min) - **TASK A**
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

✅ DATABASE TEST PASSED - Staging environment is operational!
```

---

### Step 4: Run Full API Validation (3 min) - **TASK A**
```bash
python scripts/test_staging_api.py lsZXGgU92KhK5VqR
```

**Expected**: 5/5 tests passed
- ✅ API Health
- ✅ API Docs
- ✅ Database Connection
- ✅ Database Schema
- ✅ Sample Data Loaded

---

### Step 5: Run SEC Filing Ingestion (5 min) - **TASK B**
```bash
# Enter API container
docker exec -it corporate-intel-staging-api bash

# Run SEC ingestion for Chegg (EdTech company)
python -m src.pipeline.run_sec_ingestion --ticker CHGG --forms 10-K --limit 1

# Exit container
exit
```

**Expected**: SEC 10-K filing data ingested for CHGG

---

### Step 6: Run Integration Tests (5 min) - **TASK C**
```bash
docker-compose -f docker-compose.staging.yml exec api pytest tests/integration/ -v
```

**Expected**: All integration tests pass

---

## 📊 Quick Reference

### Key Files Created This Session
- `scripts/test_staging_api.py` (500+ lines)
- `scripts/quick_db_test.py` (150+ lines)
- `docs/DOCKER_DESKTOP_ISSUE_REPORT.md`
- `docs/STAGING_RESUME_INSTRUCTIONS.md`
- `AFTER_RESTART_CHECKLIST.md` (this file)

### Access Points After Startup
| Service | URL | Notes |
|---------|-----|-------|
| API Health | http://localhost:8004/health | Quick health check |
| API Docs | http://localhost:8004/api/v1/docs | Interactive Swagger UI |
| Grafana | http://localhost:3001 | Metrics dashboard |
| Prometheus | http://localhost:9091 | Raw metrics |
| Database | localhost:5435 | PostgreSQL + TimescaleDB |

### Credentials
- **Database**: `intel_staging_user` / `lsZXGgU92KhK5VqR`
- **Grafana**: admin / (see GRAFANA_PASSWORD in .env.staging)

---

## 🎯 Success Criteria

**Task A Complete** ✅ when:
- Docker CLI working
- All containers healthy
- Database test passes
- API test passes
- 5 companies loaded (AAPL, MSFT, GOOGL, CHGG, DUOL)

**Task B Complete** ✅ when:
- SEC filing ingested for CHGG
- Data in `sec_filings` table
- No pipeline errors

**Task C Complete** ✅ when:
- Integration tests pass
- All API endpoints validated
- Full system operational

---

## ⏱️ Total Timeline

| Step | Duration | Cumulative |
|------|----------|------------|
| 1. Verify Docker | 1 min | 1 min |
| 2. Start Environment | 3 min | 4 min |
| 3. Quick DB Test | 2 min | 6 min |
| 4. Full API Test | 3 min | 9 min |
| 5. SEC Ingestion | 5 min | 14 min |
| 6. Integration Tests | 5 min | **19 min** |

**Total**: ~20 minutes from restart to complete A→B→C

---

## 🆘 Troubleshooting

### Docker Still Broken?
```bash
# Nuclear option - reset Docker Desktop
# Docker Desktop → Settings → Troubleshoot → "Reset to Factory Defaults"
# WARNING: Deletes all containers/images
```

### Containers Won't Start?
```bash
# Check logs
docker-compose -f docker-compose.staging.yml logs api
docker-compose -f docker-compose.staging.yml logs postgres

# Force cleanup and restart
docker-compose -f docker-compose.staging.yml down -v
docker-compose -f docker-compose.staging.yml up -d
```

### Database Connection Fails?
```bash
# Check postgres is ready
docker logs corporate-intel-staging-postgres | grep "ready to accept connections"

# Direct connection test
psql -h localhost -p 5435 -U intel_staging_user -d corporate_intel_staging
# Password: lsZXGgU92KhK5VqR
```

---

## 📝 Git Status

**All work saved and pushed:**
- Commit: `b0acd09` - Session metrics update
- Commit: `2b3c166` - Test scripts and documentation
- Commit: `17a75d9` - Metrics update
- Branch: `master`
- Remote: Up to date

---

**Next**: Restart machine → Follow this checklist → Complete A→B→C in ~20 minutes

**Created**: October 17, 2025, 12:42 AM PST
**Status**: ✅ Ready to restart
