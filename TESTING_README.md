# User Testing Documentation

Welcome to the Corporate Intelligence Platform user testing! This README provides an overview of all testing documentation and how to get started.

---

## 📚 Documentation Overview

This testing suite includes comprehensive documentation to help you test the application systematically:

| Document | Purpose | When to Use |
|----------|---------|-------------|
| **USER_TESTING_GUIDE.md** | Complete setup and testing guide | Read first - your main reference |
| **USER_TESTING_CHECKLIST.md** | Detailed test scenarios and cases | Use during testing sessions |
| **BUG_REPORT_TEMPLATE.md** | Standard bug report template | When you find issues |
| **TEST_DATA.md** | Test data documentation | When loading/creating test data |
| **TESTING_NOTES.md** | Personal testing journal | Track your progress and findings |

---

## 🚀 Quick Start

### Option 1: Automated Setup (Recommended)

Run the automated setup script:

```bash
./scripts/setup_testing.sh
```

This will:
- ✅ Check prerequisites (Docker, Python, etc.)
- ✅ Create .env from template
- ✅ Start all Docker services
- ✅ Set up Python virtual environment
- ✅ Run database migrations
- ✅ Load test data with dbt
- ✅ Verify everything is working

### Option 2: Manual Setup

Follow the detailed steps in `USER_TESTING_GUIDE.md`:

1. **Environment Setup**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

2. **Start Services**
   ```bash
   docker-compose up -d
   ```

3. **Python Setup**
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -e .
   ```

4. **Database Setup**
   ```bash
   alembic upgrade head
   cd dbt && dbt deps && dbt seed && dbt run && cd ..
   ```

5. **Start Application**
   ```bash
   # Terminal 1: API Server
   uvicorn src.api.main:app --reload

   # Terminal 2: Dashboard (optional)
   python -m src.visualization.dash_app
   ```

---

## 🎯 Testing Workflow

### 1. Preparation (30 minutes)

- [ ] Read `USER_TESTING_GUIDE.md` completely
- [ ] Run setup script or follow manual setup
- [ ] Verify all services are running
- [ ] Open `USER_TESTING_CHECKLIST.md` for reference
- [ ] Open `TESTING_NOTES.md` to track findings
- [ ] Create a `bugs/` directory for bug reports

### 2. Testing Sessions (2-4 hours each)

**Session Structure:**
1. Pick a testing area from checklist
2. Follow test scenarios systematically
3. Document findings in TESTING_NOTES.md
4. Create bug reports for issues found
5. Take breaks every hour

**Recommended Testing Order:**
1. **Session 1**: Authentication & Basic API (1-2 hours)
   - User registration/login
   - API authentication
   - Company listing and details

2. **Session 2**: Core Features (2-3 hours)
   - Company CRUD operations
   - Financial metrics
   - Search and filtering

3. **Session 3**: Advanced Features (2-3 hours)
   - Competitive analysis
   - Reports generation
   - Dashboard visualizations

4. **Session 4**: Infrastructure (1-2 hours)
   - Data pipelines
   - Monitoring & observability
   - Performance testing

5. **Session 5**: Edge Cases & Security (1-2 hours)
   - Error handling
   - Security testing
   - Edge cases and unusual inputs

### 3. Documentation (Throughout)

**During Testing:**
- Use TESTING_NOTES.md to journal observations
- Create bug reports immediately when issues found
- Take screenshots of UI problems
- Note performance issues

**After Each Session:**
- Update testing checklist with completed items
- Summarize findings in TESTING_NOTES.md
- Prioritize bugs by severity
- Plan next session focus

### 4. Wrap-up & Review (1-2 hours)

- [ ] Complete testing summary in TESTING_NOTES.md
- [ ] Review all bug reports
- [ ] Prioritize issues (Critical → High → Medium → Low)
- [ ] Assess production readiness
- [ ] Document recommendations

---

## 📋 Testing Checklist Summary

**Must Test:**
- ✅ Authentication (register, login, tokens)
- ✅ Company management (list, create, update, delete)
- ✅ Financial data (metrics, SEC filings, stock data)
- ✅ Analysis features (competitive, segment, cohort)
- ✅ Reports (performance, landscape)
- ✅ Dashboard (charts, filters, interactions)
- ✅ Data pipelines (ingestion, quality checks)
- ✅ API (endpoints, responses, errors)
- ✅ Performance (response times, load handling)
- ✅ Security (validation, authentication, authorization)

**See `USER_TESTING_CHECKLIST.md` for complete list (300+ test cases)**

---

## 🐛 Bug Reporting Process

### When You Find a Bug:

1. **Try to Reproduce**: Attempt to reproduce 2-3 times
2. **Document Immediately**: Don't wait - create report now
3. **Use Template**: Copy `BUG_REPORT_TEMPLATE.md`
4. **Save in bugs/**: Name as `bugs/bug-YYYYMMDD-[description].md`
5. **Assign Severity**: Critical/High/Medium/Low
6. **Reference in Notes**: Link in TESTING_NOTES.md

### Bug Severity Guidelines:

| Severity | Description | Examples |
|----------|-------------|----------|
| **Critical** | System down, data loss, security issue | App crashes, database corruption |
| **High** | Major feature broken, no workaround | Login doesn't work, API returns 500 |
| **Medium** | Feature works but has issues, workaround exists | Slow loading, minor display issues |
| **Low** | Cosmetic issues, rare edge cases | Typos, color inconsistencies |

---

## 🎨 Dashboard Testing

Access the different UIs:

| Interface | URL | Purpose |
|-----------|-----|---------|
| API Docs | http://localhost:8000/api/v1/docs | Interactive API testing |
| Health Check | http://localhost:8000/health | System status |
| Dashboard | http://localhost:8050 | Data visualizations |
| Grafana | http://localhost:3000 | Metrics & monitoring |
| Prometheus | http://localhost:9090 | Raw metrics |
| Ray | http://localhost:8265 | Distributed processing |
| Prefect | http://localhost:4200 | Workflow orchestration |

---

## 📊 Test Data

### Default Test Users

After running setup, these test accounts are available:

```
Email: test@example.com
Password: TestPassword123!
Role: User

Email: admin@example.com
Password: AdminPassword123!
Role: Admin
```

### Sample Companies

Seed data includes EdTech companies like:
- Coursera (COUR)
- Duolingo (DUOL)
- Chegg (CHGG)
- 2U Inc (TWOU)

**See `TEST_DATA.md` for complete data documentation**

---

## 🔍 Common Testing Scenarios

### Scenario 1: New User Registration Flow

```bash
# 1. Register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"newuser@example.com","password":"SecurePass123!","full_name":"New User"}'

# 2. Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"newuser@example.com","password":"SecurePass123!"}'

# 3. Get token and use it
TOKEN="<access_token_from_response>"

# 4. Access protected endpoint
curl http://localhost:8000/api/v1/companies \
  -H "Authorization: Bearer $TOKEN"
```

### Scenario 2: Analyze a Company

```bash
# 1. Get company list
curl http://localhost:8000/api/v1/companies -H "Authorization: Bearer $TOKEN"

# 2. Get specific company
curl http://localhost:8000/api/v1/companies/1 -H "Authorization: Bearer $TOKEN"

# 3. Get company metrics
curl http://localhost:8000/api/v1/companies/1/metrics -H "Authorization: Bearer $TOKEN"

# 4. Run competitive analysis
curl -X POST http://localhost:8000/api/v1/analysis/competitive \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"company_id": 1, "competitor_ids": [2, 3]}'
```

### Scenario 3: Data Pipeline Testing

1. Navigate to Prefect UI: http://localhost:4200
2. Find "SEC Data Ingestion" flow
3. Click "Run" to trigger manually
4. Monitor execution in real-time
5. Check logs for errors
6. Verify data in database

---

## ⚡ Performance Benchmarks

Expected performance targets:

| Operation | Target | Acceptable |
|-----------|--------|------------|
| API Health Check | < 50ms | < 100ms |
| List Companies | < 100ms | < 200ms |
| Get Company Details | < 100ms | < 200ms |
| Simple Analysis | < 500ms | < 1s |
| Complex Analysis | < 2s | < 5s |
| Dashboard Load | < 2s | < 5s |
| Data Ingestion (100 docs) | < 60s | < 120s |

**Flag performance issues that exceed "Acceptable" thresholds**

---

## 🛡️ Security Testing

### Tests to Perform:

1. **Input Validation**
   - Try SQL injection: `' OR '1'='1`
   - Try XSS: `<script>alert('xss')</script>`
   - Try path traversal: `../../../etc/passwd`

2. **Authentication**
   - Invalid credentials
   - Expired tokens
   - Missing tokens
   - Malformed tokens

3. **Authorization**
   - Access other users' data
   - Admin-only endpoints as regular user
   - CRUD operations without permission

**Document any security issues as CRITICAL bugs**

---

## 📈 Progress Tracking

Use this quick checklist to track overall progress:

### Setup Phase
- [ ] Automated setup completed
- [ ] All services running
- [ ] Test data loaded
- [ ] Can access all interfaces

### Testing Phase
- [ ] Session 1: Authentication - Completed
- [ ] Session 2: Core Features - Completed
- [ ] Session 3: Advanced Features - Completed
- [ ] Session 4: Infrastructure - Completed
- [ ] Session 5: Edge Cases - Completed

### Documentation Phase
- [ ] TESTING_NOTES.md updated
- [ ] All bugs documented
- [ ] Screenshots captured
- [ ] Bug severity assigned

### Review Phase
- [ ] Testing summary written
- [ ] Bugs prioritized
- [ ] Recommendations documented
- [ ] Production readiness assessed

---

## 🎯 Success Criteria

Your testing is complete when:

- ✅ All areas in checklist have been tested
- ✅ All bugs are documented with severity
- ✅ Critical and high-priority bugs are identified
- ✅ Performance benchmarks are recorded
- ✅ Security testing is complete
- ✅ Testing summary is written
- ✅ Production readiness decision is made

---

## 🆘 Troubleshooting

### Services Won't Start

```bash
# Check Docker
docker ps

# Restart services
docker-compose down
docker-compose up -d

# View logs
docker-compose logs -f postgres
```

### Database Issues

```bash
# Reset database
alembic downgrade base
alembic upgrade head
cd dbt && dbt seed --full-refresh && cd ..
```

### API Errors

```bash
# Check API logs
tail -f logs/app.log

# Check Sentry (if configured)
# Open Sentry dashboard

# Restart API
# Ctrl+C in terminal running uvicorn
# Re-run: uvicorn src.api.main:app --reload
```

### Can't Access UI

```bash
# Check if port is in use
lsof -i :8000  # API
lsof -i :8050  # Dashboard
lsof -i :3000  # Grafana

# Kill process if needed
kill -9 <PID>
```

**See USER_TESTING_GUIDE.md for more troubleshooting tips**

---

## 📞 Resources

### Documentation Files
- `USER_TESTING_GUIDE.md` - Complete testing guide
- `USER_TESTING_CHECKLIST.md` - All test cases
- `BUG_REPORT_TEMPLATE.md` - Bug report format
- `TEST_DATA.md` - Test data reference
- `TESTING_NOTES.md` - Your testing journal

### Application Docs
- `README.md` - Project overview
- `docs/` - Additional documentation
- API Docs: http://localhost:8000/api/v1/docs

### Support
- GitHub Issues: [Create issue for setup problems]
- Project Lead: [Contact info]

---

## 🎉 Ready to Start?

1. **Run setup**: `./scripts/setup_testing.sh`
2. **Open guide**: Read `USER_TESTING_GUIDE.md`
3. **Start testing**: Follow `USER_TESTING_CHECKLIST.md`
4. **Document findings**: Use `TESTING_NOTES.md`
5. **Report bugs**: Copy `BUG_REPORT_TEMPLATE.md`

**Estimated Total Testing Time**: 8-12 hours
**Recommended Schedule**: 2-3 hour sessions over several days

---

## 📝 Quick Reference Commands

```bash
# Setup
./scripts/setup_testing.sh

# Start services
docker-compose up -d

# Start API
source venv/bin/activate
uvicorn src.api.main:app --reload

# Start dashboard
python -m src.visualization.dash_app

# Check service status
docker-compose ps

# View logs
docker-compose logs -f [service]

# Database console
psql $DATABASE_URL

# Stop everything
docker-compose down
```

---

**Happy Testing! Your thorough testing will help make this application production-ready.** 🚀

For questions or issues with the testing process, document them in TESTING_NOTES.md.
