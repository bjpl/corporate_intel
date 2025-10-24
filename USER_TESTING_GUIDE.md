# User Testing Guide - Corporate Intelligence Platform

## Overview
This guide will help you test the Corporate Intelligence Platform for EdTech Analysis. This is a self-testing guide where you'll verify all major features and workflows.

---

## 🚀 Quick Start Setup

### Prerequisites
- Docker & Docker Compose installed
- Python 3.11+ installed
- Git installed
- At least 4GB RAM available
- API keys for external services (optional for basic testing)

### Step 1: Environment Configuration

1. **Create your environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` with minimal required settings:**
   ```bash
   # Database
   POSTGRES_USER=corp_intel
   POSTGRES_PASSWORD=your_secure_password
   POSTGRES_DB=corporate_intel
   DATABASE_URL=postgresql://corp_intel:your_secure_password@localhost:5432/corporate_intel

   # Redis
   REDIS_URL=redis://localhost:6379/0

   # JWT Secret (generate a secure random string)
   JWT_SECRET_KEY=your-super-secret-jwt-key-change-this

   # MinIO
   MINIO_ROOT_USER=minioadmin
   MINIO_ROOT_PASSWORD=minioadmin123

   # API Keys (optional - for full testing)
   SEC_API_KEY=your_sec_api_key
   ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key
   NEWS_API_KEY=your_news_api_key
   ```

### Step 2: Start Infrastructure

```bash
# Start all services (PostgreSQL, Redis, MinIO, Ray, Grafana, etc.)
docker-compose up -d

# Wait 30 seconds for services to be ready
sleep 30

# Verify services are running
docker-compose ps
```

**Expected Services:**
- PostgreSQL (port 5432)
- Redis (port 6379)
- MinIO (port 9000, 9001)
- Ray Head (port 8265)
- Grafana (port 3000)
- Prometheus (port 9090)
- Prefect (port 4200)

### Step 3: Python Environment Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .

# Verify installation
python -c "import fastapi, dash, sqlalchemy; print('Dependencies OK')"
```

### Step 4: Database Initialization

```bash
# Run database migrations
alembic upgrade head

# Initialize dbt (data transformation)
cd dbt
dbt deps
dbt seed    # Load sample data
dbt run     # Run transformations
cd ..
```

### Step 5: Start the Application

**Terminal 1 - API Server:**
```bash
source venv/bin/activate
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Dashboard (optional):**
```bash
source venv/bin/activate
python -m src.visualization.dash_app
```

### Step 6: Verify Everything is Running

Open your browser and check:
- ✅ API Documentation: http://localhost:8000/api/v1/docs
- ✅ Health Check: http://localhost:8000/health
- ✅ Dashboard: http://localhost:8050 (if started)
- ✅ Grafana: http://localhost:3000 (admin/admin)
- ✅ Ray Dashboard: http://localhost:8265

---

## 🧪 Testing Workflow

### Testing Approach
1. **Exploratory Testing**: Navigate through features naturally
2. **Scenario Testing**: Follow specific user workflows
3. **Edge Case Testing**: Try unusual inputs and error scenarios
4. **Performance Testing**: Test with realistic data volumes

### Testing Sessions
- **Session Duration**: 30-60 minutes per area
- **Document As You Go**: Note issues immediately
- **Take Screenshots**: Capture errors and UI issues
- **Test Systematically**: Follow the checklist (see USER_TESTING_CHECKLIST.md)

---

## 📋 Core Features to Test

### 1. Authentication & Authorization
**Location**: `/api/v1/auth/`

**Test Scenarios:**
- [ ] Register new user
- [ ] Login with valid credentials
- [ ] Login with invalid credentials
- [ ] Access protected endpoints with token
- [ ] Access protected endpoints without token
- [ ] Token expiration handling
- [ ] API key authentication

**How to Test:**
```bash
# Register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Test123!","full_name":"Test User"}'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test@example.com","password":"Test123!"}'

# Copy the access_token from response
```

### 2. Company Data Management
**Location**: `/api/v1/companies`

**Test Scenarios:**
- [ ] List all companies
- [ ] Get specific company details
- [ ] Search companies by name
- [ ] Filter companies by sector
- [ ] Create new company record
- [ ] Update company information
- [ ] Delete company record
- [ ] Handle invalid company IDs

**How to Test:**
```bash
# Get all companies
curl http://localhost:8000/api/v1/companies \
  -H "Authorization: Bearer YOUR_TOKEN"

# Get specific company
curl http://localhost:8000/api/v1/companies/1 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 3. Financial Data & Metrics
**Location**: `/api/v1/companies/{id}/metrics`

**Test Scenarios:**
- [ ] Retrieve company metrics
- [ ] Filter metrics by date range
- [ ] View historical trends
- [ ] Check data accuracy
- [ ] Handle missing data gracefully
- [ ] Validate metric calculations

### 4. Competitive Analysis
**Location**: `/api/v1/analysis/competitive`

**Test Scenarios:**
- [ ] Run competitive analysis for company
- [ ] Compare multiple companies
- [ ] View market positioning
- [ ] Check analysis accuracy
- [ ] Export analysis results

### 5. Segment Analysis
**Location**: `/api/v1/analysis/segment`

**Test Scenarios:**
- [ ] Analyze market segments
- [ ] View segment performance
- [ ] Compare segments over time
- [ ] Filter by criteria

### 6. Reports & Visualizations
**Location**: `/api/v1/reports/`

**Test Scenarios:**
- [ ] Generate performance report
- [ ] Generate landscape report
- [ ] View market landscape
- [ ] Export reports (PDF/CSV)
- [ ] Schedule automated reports

### 7. Data Ingestion Pipelines
**Location**: Prefect UI (http://localhost:4200)

**Test Scenarios:**
- [ ] Trigger manual data ingestion
- [ ] Monitor pipeline execution
- [ ] View ingestion logs
- [ ] Handle ingestion failures
- [ ] Verify data quality checks
- [ ] Test different data sources (SEC, Yahoo Finance, etc.)

### 8. Dashboard & Visualizations
**Location**: http://localhost:8050

**Test Scenarios:**
- [ ] Load dashboard successfully
- [ ] Interactive charts work (zoom, pan, filter)
- [ ] Data updates in real-time
- [ ] Filters apply correctly
- [ ] Dashboard is responsive
- [ ] Export visualizations

### 9. Search & Discovery
**Test Scenarios:**
- [ ] Full-text search for companies
- [ ] Semantic search (vector similarity)
- [ ] Filter search results
- [ ] Search performance with large datasets

### 10. Monitoring & Observability
**Locations**:
- Grafana: http://localhost:3000
- Prometheus: http://localhost:9090

**Test Scenarios:**
- [ ] View API metrics
- [ ] Check error rates
- [ ] Monitor database performance
- [ ] View distributed traces
- [ ] Check log aggregation

---

## 🐛 Bug Tracking

### When You Find an Issue

1. **Stop and Document**: Don't just make a mental note
2. **Use the Bug Template**: See BUG_REPORT_TEMPLATE.md
3. **Reproduce**: Try to reproduce the issue 2-3 times
4. **Categorize Severity**:
   - **Critical**: App crashes, data loss, security issue
   - **High**: Feature doesn't work, blocking workflow
   - **Medium**: Feature works but has issues
   - **Low**: Minor UI/UX issues, typos

### Quick Bug Capture
Create a file named `bugs/bug-YYYY-MM-DD-HH-MM.md` with:
```markdown
# Bug: [Short Description]

**Date**: 2025-10-24
**Severity**: Critical/High/Medium/Low
**Area**: Authentication/API/Dashboard/etc.

## Steps to Reproduce
1.
2.
3.

## Expected Behavior


## Actual Behavior


## Screenshots/Logs
[Paste here]

## Environment
- Browser:
- API Version:
- Database:
```

---

## 📊 Test Data

### Sample Companies
The `dbt seed` command should have loaded sample EdTech companies. Verify:

```sql
-- Connect to PostgreSQL
psql $DATABASE_URL

-- Check sample data
SELECT id, name, ticker, sector FROM companies LIMIT 10;
```

### Creating Test Data

If you need more test data:

```bash
# Option 1: Use the API
curl -X POST http://localhost:8000/api/v1/companies \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test EdTech Co",
    "ticker": "TEST",
    "sector": "EdTech",
    "description": "A test company"
  }'

# Option 2: Add to dbt seeds
# Edit: dbt/seeds/companies.csv
# Then run: cd dbt && dbt seed --select companies
```

---

## ⚠️ Common Issues & Troubleshooting

### Issue: "Connection refused" to PostgreSQL
```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# Check logs
docker-compose logs postgres

# Restart if needed
docker-compose restart postgres
```

### Issue: "Module not found" errors
```bash
# Reinstall dependencies
pip install -e .

# Or with force reinstall
pip install -e . --force-reinstall
```

### Issue: Database migration errors
```bash
# Check current migration status
alembic current

# Rollback and reapply
alembic downgrade -1
alembic upgrade head
```

### Issue: API returns 500 errors
```bash
# Check API logs (in terminal running uvicorn)
# Check Sentry dashboard for error details
# Check application logs
tail -f logs/app.log
```

### Issue: Dashboard won't load
```bash
# Check if port 8050 is in use
lsof -i :8050

# Check dashboard logs in terminal
# Verify data is in database
```

### Issue: Slow performance
```bash
# Check Redis is running
docker-compose ps redis

# Check Ray cluster
curl http://localhost:8265/api/cluster_status

# Monitor database
docker-compose exec postgres psql -U corp_intel -d corporate_intel -c "SELECT * FROM pg_stat_activity;"
```

---

## 🎯 Testing Goals

By the end of your testing, you should be able to answer:

- ✅ Can I successfully set up and run the application?
- ✅ Do all core features work as expected?
- ✅ Is the API documentation accurate and helpful?
- ✅ Are error messages clear and actionable?
- ✅ Is the performance acceptable for realistic data volumes?
- ✅ Are there any critical bugs or security issues?
- ✅ Is the user experience intuitive?

---

## 📝 Testing Notes

Keep a testing journal (create `TESTING_NOTES.md`):

```markdown
# Testing Session - [Date]

## Session Info
- Duration:
- Focus Area:
- Environment: Local development

## What Worked Well
-

## Issues Found
- [Link to bug reports]

## Questions/Unclear
-

## Next Session
-
```

---

## 🚦 Testing Status

Track your overall progress:

- [ ] Environment setup complete
- [ ] All services running
- [ ] Authentication tested
- [ ] Company management tested
- [ ] Financial data tested
- [ ] Analysis features tested
- [ ] Reports tested
- [ ] Data pipelines tested
- [ ] Dashboard tested
- [ ] Monitoring tested
- [ ] Performance tested
- [ ] Security tested
- [ ] Documentation reviewed

---

## 📞 Getting Help

If you get stuck:
1. Check the main README.md
2. Review API docs at http://localhost:8000/api/v1/docs
3. Check Docker logs: `docker-compose logs [service_name]`
4. Review application logs in `logs/` directory
5. Check Grafana dashboards for system health

---

## Next Steps

1. Complete the setup steps above
2. Review the detailed test scenarios in `USER_TESTING_CHECKLIST.md`
3. Start with basic features (authentication, companies list)
4. Progress to complex features (analysis, reports)
5. Document all findings in bug reports
6. Review your findings and prioritize fixes

Happy Testing! 🎉
