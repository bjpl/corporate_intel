# Production Deployment Roadmap - Corporate Intelligence Platform
**5-7 Day Production Readiness Plan**

**Date Created:** October 2, 2025
**Target Production Date:** October 9, 2025
**Current Readiness Score:** 78/100
**Target Readiness Score:** 95/100

---

## Executive Summary

### Current State Assessment
- **Overall Readiness:** 78/100 (Conditional Approval)
- **Test Coverage:** ~35% (Target: 80%+)
- **Infrastructure:** Docker-compose ready, K8s configured
- **Security:** 90/100 (Excellent)
- **Documentation:** 85/100 (Comprehensive)
- **Code Quality:** 85/100 (Production-grade)

### Critical Success Factors
1. Increase test coverage from 35% to 80%+ (48 hours effort)
2. Validate startup sequence with live services (8 hours)
3. Complete integration testing with external APIs (16 hours)
4. Execute performance and load testing (16 hours)
5. Security hardening and audit (12 hours)
6. Production deployment and validation (8 hours)

### Timeline Overview
```
Day 1-2: Foundation & Testing (Priority 1)
Day 3-4: Integration & Coverage (Priority 2)
Day 5-6: Performance & Security (Priority 3)
Day 7:   Production Deployment & Validation
```

---

## Day-by-Day Roadmap

### **DAY 1: Foundation & Environment Setup** (8 hours)
*Goal: Establish working environment and fix critical blockers*

#### Morning (4 hours)
**1. Environment Configuration & Dependencies (2 hours)**
- [ ] Create `.env` from `.env.example` with production-safe values
- [ ] Generate secure `SECRET_KEY` using `python -c "import secrets; print(secrets.token_urlsafe(32))"`
- [ ] Configure database passwords (strong, 24+ characters)
- [ ] Set Redis passwords
- [ ] Configure MinIO access keys
- [ ] Add placeholder API keys (Alpha Vantage, NewsAPI, SEC User-Agent)

**Commands:**
```bash
# Generate secure keys
python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))" >> .env.local
python -c "import secrets; print('POSTGRES_PASSWORD=' + secrets.token_urlsafe(24))" >> .env.local
python -c "import secrets; print('REDIS_PASSWORD=' + secrets.token_urlsafe(16))" >> .env.local

# Copy and merge with .env.example
cp .env.example .env
# Manually merge .env.local values into .env
```

**2. Fix Test Dependencies (2 hours)**
- [ ] Create `requirements-test.txt` with missing dependencies
- [ ] Install OpenTelemetry test modules
- [ ] Install pytest-cov, pytest-mock, coverage[toml]
- [ ] Verify all test dependencies resolve correctly

**requirements-test.txt:**
```
pytest>=7.4.3
pytest-asyncio>=0.21.1
pytest-cov>=4.1.0
pytest-mock>=3.12.0
pytest-benchmark>=4.0.0
coverage[toml]>=7.3.2
httpx>=0.25.0
faker>=20.0.0
factory-boy>=3.3.0
```

**Commands:**
```bash
pip install -r requirements-test.txt
pytest --version
pytest --collect-only  # Verify tests are discoverable
```

#### Afternoon (4 hours)
**3. Infrastructure Startup Validation (3 hours)**
- [ ] Start Docker Compose infrastructure services
- [ ] Verify PostgreSQL with TimescaleDB extension
- [ ] Verify Redis connectivity
- [ ] Verify MinIO object storage
- [ ] Check all health endpoints

**Commands:**
```bash
# Start core infrastructure
docker-compose up -d postgres redis minio

# Wait for services to be healthy
docker-compose ps

# Verify PostgreSQL
docker exec corporate-intel-postgres psql -U intel_user -d corporate_intel -c "SELECT version();"
docker exec corporate-intel-postgres psql -U intel_user -d corporate_intel -c "CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;"
docker exec corporate-intel-postgres psql -U intel_user -d corporate_intel -c "CREATE EXTENSION IF NOT EXISTS vector CASCADE;"

# Verify Redis
docker exec corporate-intel-redis redis-cli ping

# Verify MinIO
curl http://localhost:9001/  # MinIO Console
```

**4. Database Migration Execution (1 hour)**
- [ ] Run Alembic migrations to create schema
- [ ] Verify all tables created
- [ ] Verify TimescaleDB hypertables
- [ ] Verify pgvector extension enabled

**Commands:**
```bash
# Run migrations
alembic upgrade head

# Verify schema
docker exec corporate-intel-postgres psql -U intel_user -d corporate_intel -c "\dt"
docker exec corporate-intel-postgres psql -U intel_user -d corporate_intel -c "SELECT * FROM timescaledb_information.hypertables;"
docker exec corporate-intel-postgres psql -U intel_user -d corporate_intel -c "\dx vector"
```

**End of Day 1 Deliverables:**
- ✅ Working .env configuration
- ✅ All test dependencies installed
- ✅ Infrastructure services running
- ✅ Database schema initialized
- ✅ All health checks passing

---

### **DAY 2: Application Startup & Basic Testing** (8 hours)
*Goal: Validate application starts and runs basic test suite*

#### Morning (4 hours)
**1. Application Startup Validation (2 hours)**
- [ ] Start FastAPI application with Uvicorn
- [ ] Verify all endpoints respond (health, docs, API v1)
- [ ] Test authentication endpoints
- [ ] Verify OpenAPI documentation accessible
- [ ] Check Prometheus /metrics endpoint

**Commands:**
```bash
# Start API server
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# In separate terminal, test endpoints
curl http://localhost:8000/health
curl http://localhost:8000/health/database
curl http://localhost:8000/api/v1/docs
curl http://localhost:8000/metrics

# Test authentication
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Test123!@#","username":"testuser"}'
```

**2. Run Existing Test Suite (2 hours)**
- [ ] Execute pytest with coverage reporting
- [ ] Document current coverage baseline
- [ ] Identify test failures and fix blocking issues
- [ ] Generate HTML coverage report

**Commands:**
```bash
# Run tests with coverage
pytest --cov=src --cov-report=html --cov-report=term-missing --cov-report=xml -v

# View coverage report
python -m http.server 8080 --directory htmlcov

# Generate coverage badge
coverage-badge -o coverage.svg -f
```

#### Afternoon (4 hours)
**3. Fix Critical Test Failures (3 hours)**
- [ ] Address OpenTelemetry import errors
- [ ] Fix database connection issues in tests
- [ ] Resolve async/await test problems
- [ ] Ensure all existing tests pass

**Priority Fixes:**
1. Mock OpenTelemetry dependencies where needed
2. Fix database session management in test fixtures
3. Update async test patterns for pytest-asyncio
4. Resolve any API client mocking issues

**4. Baseline Coverage Documentation (1 hour)**
- [ ] Document current coverage by module
- [ ] Identify top 10 untested critical modules
- [ ] Create test coverage improvement plan
- [ ] Set coverage targets for each module category

**End of Day 2 Deliverables:**
- ✅ Application running successfully
- ✅ All existing tests passing
- ✅ Baseline coverage report generated
- ✅ Coverage improvement plan documented

---

### **DAY 3: Test Coverage Expansion - Critical Modules** (8 hours)
*Goal: Increase coverage from 35% to 60% focusing on critical paths*

#### Morning (4 hours)
**1. API Endpoint Testing (4 hours)**
Target modules with 0% coverage:
- [ ] `src/api/v1/companies.py` - Companies CRUD endpoints
- [ ] `src/api/v1/filings.py` - SEC filings endpoints
- [ ] `src/api/v1/metrics.py` - Financial metrics endpoints

**Test File: tests/unit/test_api_companies.py**
```python
class TestCompaniesEndpoint:
    def test_create_company_handler()
    def test_create_company_validation()
    def test_get_company_by_id()
    def test_get_company_not_found()
    def test_list_companies_pagination()
    def test_update_company_authorization()
    def test_delete_company_cascade()
    def test_search_companies()
```

**Estimated Coverage Gain:** +10%

#### Afternoon (4 hours)
**2. Data Pipeline Testing (4 hours)**
Target modules with 0% coverage:
- [ ] `src/pipeline/sec_ingestion.py` - SEC data ingestion (Prefect flows)
- [ ] `src/processing/document_processor.py` - Document processing
- [ ] `src/processing/metrics_extractor.py` - Metrics extraction

**Test File: tests/unit/test_pipeline.py**
```python
class TestSECIngestion:
    def test_fetch_filings()
    def test_parse_10k_document()
    def test_extract_financial_data()
    def test_error_handling_rate_limit()
    def test_retry_logic()

class TestDocumentProcessor:
    def test_pdf_extraction()
    def test_html_parsing()
    def test_text_cleaning()
    def test_chunking_strategy()
```

**Estimated Coverage Gain:** +15%

**End of Day 3 Deliverables:**
- ✅ API endpoint test suite (60%+ coverage)
- ✅ Data pipeline test suite (40%+ coverage)
- ✅ Overall coverage: ~60%

---

### **DAY 4: Test Coverage Expansion - Infrastructure** (8 hours)
*Goal: Increase coverage from 60% to 80% focusing on core infrastructure*

#### Morning (4 hours)
**1. Core Infrastructure Testing (4 hours)**
Target modules with 0% coverage:
- [ ] `src/core/cache.py` - Redis caching layer
- [ ] `src/core/exceptions.py` - Custom exceptions
- [ ] `src/core/dependencies.py` - FastAPI dependencies
- [ ] `src/db/base.py` - Database base classes

**Test Files:**
```python
# tests/unit/test_core_cache.py
class TestCacheManager:
    def test_get_set_delete()
    def test_ttl_expiration()
    def test_cache_invalidation()
    def test_connection_pool()

# tests/unit/test_core_exceptions.py
class TestCustomExceptions:
    def test_authentication_error()
    def test_validation_error()
    def test_not_found_error()
    def test_error_serialization()

# tests/unit/test_core_dependencies.py
class TestDependencyInjection:
    def test_get_database_dependency()
    def test_get_cache_dependency()
    def test_get_current_user()
    def test_require_admin_role()
```

**Estimated Coverage Gain:** +10%

#### Afternoon (4 hours)
**2. Integration Test Suite Creation (4 hours)**
- [ ] Create end-to-end workflow tests
- [ ] Test database transaction isolation
- [ ] Test external API integration patterns
- [ ] Test caching integration

**Test File: tests/integration/test_full_workflows.py**
```python
class TestEndToEndWorkflows:
    @pytest.mark.integration
    async def test_full_sec_filing_pipeline():
        # 1. Ingest SEC filing
        # 2. Process document
        # 3. Extract metrics
        # 4. Generate embeddings
        # 5. Run analysis
        # 6. Create report

    @pytest.mark.integration
    async def test_company_creation_to_analysis():
        # Complete workflow from company creation to analysis

    @pytest.mark.integration
    async def test_cache_warming_strategy():
        # Test cache population and invalidation
```

**Estimated Coverage Gain:** +10%

**End of Day 4 Deliverables:**
- ✅ Core infrastructure tests (80%+ coverage)
- ✅ Integration test suite created
- ✅ Overall coverage: 80%+ achieved

---

### **DAY 5: Performance Testing & Optimization** (8 hours)
*Goal: Validate application performance under load*

#### Morning (4 hours)
**1. Performance Benchmarking Setup (2 hours)**
- [ ] Install k6 or Locust for load testing
- [ ] Create performance test scenarios
- [ ] Set performance baselines
- [ ] Configure monitoring during tests

**k6 Test Script: tests/load/api-load-test.js**
```javascript
import http from 'k6/http';
import { check, sleep } from 'k6';

export let options = {
  stages: [
    { duration: '2m', target: 10 },  // Ramp up to 10 users
    { duration: '5m', target: 50 },  // Stay at 50 users
    { duration: '2m', target: 100 }, // Spike to 100 users
    { duration: '3m', target: 0 },   // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<200'], // 95% of requests under 200ms
    http_req_failed: ['rate<0.01'],   // Error rate < 1%
  },
};

export default function () {
  let response = http.get('http://localhost:8000/api/v1/companies');
  check(response, {
    'status is 200': (r) => r.status === 200,
    'response time < 200ms': (r) => r.timings.duration < 200,
  });
  sleep(1);
}
```

**2. Execute Performance Tests (2 hours)**
- [ ] Run load tests against local environment
- [ ] Monitor database connection pool usage
- [ ] Monitor memory consumption
- [ ] Monitor API response times

**Commands:**
```bash
# Install k6
curl https://github.com/grafana/k6/releases/download/v0.47.0/k6-v0.47.0-linux-amd64.tar.gz -L | tar xvz

# Run load test
k6 run tests/load/api-load-test.js

# Monitor during test
docker stats
htop
```

#### Afternoon (4 hours)
**3. Performance Optimization (3 hours)**
- [ ] Optimize slow database queries
- [ ] Tune connection pool settings
- [ ] Implement query result caching
- [ ] Optimize API response serialization

**Optimization Targets:**
- API p95 latency: < 200ms
- Database connection pool: 20-50 connections
- Redis cache hit rate: > 80%
- Memory usage: < 1GB per worker

**4. Performance Validation (1 hour)**
- [ ] Re-run load tests after optimizations
- [ ] Document performance improvements
- [ ] Create performance baseline report
- [ ] Set up performance monitoring dashboards

**End of Day 5 Deliverables:**
- ✅ Load test suite created
- ✅ Performance baseline documented
- ✅ Optimization implemented
- ✅ Performance targets met (p95 < 200ms)

---

### **DAY 6: Security Hardening & Production Preparation** (8 hours)
*Goal: Complete security audit and production hardening*

#### Morning (4 hours)
**1. Security Audit Execution (3 hours)**

**Security Checklist:**

**Authentication & Authorization:**
- [ ] JWT token secret is cryptographically secure (32+ bytes)
- [ ] API keys use secure random generation
- [ ] Password hashing uses bcrypt with cost factor 12+
- [ ] Token expiration properly enforced (15min access, 7d refresh)
- [ ] Role-based access control working correctly
- [ ] API key revocation functional

**API Security:**
- [ ] Rate limiting enabled (100 req/min per IP)
- [ ] CORS origins properly restricted
- [ ] Input validation on all endpoints (Pydantic)
- [ ] SQL injection prevention (parameterized queries)
- [ ] XSS protection (response headers)
- [ ] CSRF protection for state-changing operations

**Infrastructure Security:**
- [ ] No hardcoded secrets anywhere in codebase
- [ ] All sensitive config from environment variables
- [ ] Docker container runs as non-root user (UID 1000)
- [ ] Database passwords are strong (24+ characters)
- [ ] Redis requires authentication
- [ ] MinIO uses secure access keys

**Security Headers:**
```python
# Add to src/api/main.py middleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware

app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*.example.com"])
app.add_middleware(
    HTTPSRedirectMiddleware
)  # Only in production

# Add security headers
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response
```

**2. Dependency Security Scan (1 hour)**
- [ ] Run `pip-audit` for vulnerable dependencies
- [ ] Run `safety check` for known vulnerabilities
- [ ] Update vulnerable packages
- [ ] Document security exceptions

**Commands:**
```bash
# Install security tools
pip install pip-audit safety

# Run security scans
pip-audit
safety check --json
```

#### Afternoon (4 hours)
**3. Docker Security Hardening (2 hours)**
- [ ] Pin base image with SHA256 digest
- [ ] Run container security scan (docker scout)
- [ ] Minimize image size (multi-stage build already done)
- [ ] Add security labels to Dockerfile
- [ ] Create .dockerignore (already exists)

**Commands:**
```bash
# Build production image
docker build -t corporate-intel-api:latest .

# Security scan
docker scout cves corporate-intel-api:latest
docker scout recommendations corporate-intel-api:latest

# Verify non-root user
docker run --rm corporate-intel-api:latest whoami
```

**4. Production Deployment Checklist Creation (2 hours)**
- [ ] Create deployment runbook
- [ ] Document rollback procedures
- [ ] Create smoke test script
- [ ] Document monitoring setup
- [ ] Create incident response guide

**End of Day 6 Deliverables:**
- ✅ Security audit completed
- ✅ All security issues resolved
- ✅ Docker image hardened
- ✅ Deployment runbook created

---

### **DAY 7: Production Deployment & Validation** (8 hours)
*Goal: Deploy to production and validate all systems*

#### Morning (4 hours)
**1. Pre-Deployment Validation (2 hours)**
- [ ] Final test suite execution (all tests pass)
- [ ] Coverage verification (80%+)
- [ ] Security scan clean
- [ ] Performance benchmarks met
- [ ] Documentation complete

**Pre-Deployment Checklist:**
```bash
# Run full test suite
pytest --cov=src --cov-report=term-missing --cov-fail-under=80 -v

# Verify coverage
coverage report --fail-under=80

# Security scan
pip-audit
safety check

# Load test
k6 run tests/load/api-load-test.js

# Smoke test
bash scripts/smoke-test.sh
```

**2. Production Deployment (2 hours)**

**Option A: Docker Compose (Simple Deployment)**
```bash
# Build production images
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build

# Deploy
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Verify health
curl https://api.example.com/health
```

**Option B: Kubernetes (Enterprise Deployment)**
```bash
# Create namespace
kubectl apply -f k8s/namespace.yaml

# Create secrets (from environment variables)
kubectl create secret generic api-secrets \
  --from-env-file=.env.production \
  --namespace=corporate-intel

# Deploy database
kubectl apply -f k8s/postgres.yaml

# Wait for database
kubectl wait --for=condition=ready pod -l app=postgres --timeout=5m -n corporate-intel

# Run migrations
kubectl run migrations \
  --image=corporate-intel-api:latest \
  --restart=Never \
  --namespace=corporate-intel \
  --env="DATABASE_URL=$DATABASE_URL" \
  -- alembic upgrade head

# Deploy API
kubectl apply -f k8s/api-deployment.yaml

# Verify deployment
kubectl get pods -n corporate-intel
kubectl get svc -n corporate-intel
```

#### Afternoon (4 hours)
**3. Post-Deployment Validation (2 hours)**
- [ ] Verify all pods/containers healthy
- [ ] Test all critical API endpoints
- [ ] Verify database connectivity
- [ ] Test authentication flow
- [ ] Verify external API integrations
- [ ] Check monitoring dashboards

**Smoke Test Script:**
```bash
#!/bin/bash
# scripts/smoke-test.sh

API_URL="${API_URL:-http://localhost:8000}"

echo "Running smoke tests against $API_URL"

# Health check
echo "Testing health endpoint..."
curl -f $API_URL/health || exit 1

# Database health
echo "Testing database health..."
curl -f $API_URL/health/database || exit 1

# API documentation
echo "Testing API docs..."
curl -f $API_URL/api/v1/docs || exit 1

# Authentication
echo "Testing authentication..."
REGISTER_RESPONSE=$(curl -s -X POST $API_URL/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"smoke-test@example.com","password":"Test123!@#","username":"smoketest"}')

# Companies API
echo "Testing companies API..."
curl -f $API_URL/api/v1/companies || exit 1

# Metrics endpoint
echo "Testing metrics..."
curl -f $API_URL/metrics || exit 1

echo "All smoke tests passed!"
```

**4. Monitoring & Observability Setup (2 hours)**
- [ ] Start observability stack (Jaeger, Prometheus, Grafana)
- [ ] Import Grafana dashboards
- [ ] Configure Prometheus alerts
- [ ] Set up Sentry error tracking
- [ ] Verify distributed tracing

**Commands:**
```bash
# Start observability stack
docker-compose --profile observability up -d

# Import Grafana dashboards
curl -X POST http://admin:admin@localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -d @monitoring/grafana/dashboards/api-performance.json

# Verify Prometheus targets
curl http://localhost:9090/api/v1/targets

# Check Jaeger UI
open http://localhost:16686

# Configure Sentry (if using)
export SENTRY_DSN="your-sentry-dsn"
```

**End of Day 7 Deliverables:**
- ✅ Production deployment successful
- ✅ All smoke tests passing
- ✅ Monitoring operational
- ✅ Documentation updated
- ✅ Team handoff complete

---

## Test Coverage Improvement Strategy

### Current State: 35% Coverage
**Breakdown by Module:**
- Authentication: 85% ✅
- API Endpoints: 60% ⚠️
- Analysis Engine: 40% ⚠️
- Data Processing: 0% ❌
- Data Pipeline: 0% ❌
- Database Layer: 25% ❌
- Core Infrastructure: 0% ❌
- Observability: 0% ❌

### Target State: 80% Coverage
**Priority-Based Approach:**

#### Phase 1: Critical Paths (Day 3) - Target 60%
**Focus:** Business-critical modules that would cause production failures

1. **API Endpoints (src/api/v1/)** - Currently 60%, Target 85%
   - Companies CRUD operations
   - SEC filings management
   - Financial metrics APIs
   - Analysis endpoints
   - Reports generation

   **Test Files to Create:**
   - `tests/unit/test_api_companies.py` (15 tests)
   - `tests/unit/test_api_filings.py` (12 tests)
   - `tests/unit/test_api_metrics.py` (10 tests)
   - `tests/unit/test_api_intelligence.py` (8 tests)

   **Estimated Effort:** 4 hours
   **Coverage Gain:** +10%

2. **Data Pipeline (src/pipeline/)** - Currently 0%, Target 40%
   - SEC data ingestion (Prefect flows)
   - Document processing pipeline
   - Metrics extraction logic

   **Test Files to Create:**
   - `tests/unit/test_sec_ingestion.py` (20 tests)
   - `tests/unit/test_document_processor.py` (15 tests)
   - `tests/unit/test_metrics_extractor.py` (12 tests)

   **Estimated Effort:** 4 hours
   **Coverage Gain:** +15%

#### Phase 2: Infrastructure (Day 4) - Target 80%
**Focus:** Core infrastructure that supports all features

3. **Core Infrastructure (src/core/)** - Currently 0%, Target 75%
   - Cache manager (Redis operations)
   - Custom exceptions
   - Dependency injection
   - Configuration validation

   **Test Files to Create:**
   - `tests/unit/test_core_cache.py` (15 tests)
   - `tests/unit/test_core_exceptions.py` (8 tests)
   - `tests/unit/test_core_dependencies.py` (10 tests)

   **Estimated Effort:** 3 hours
   **Coverage Gain:** +8%

4. **Database Layer (src/db/)** - Currently 25%, Target 70%
   - SQLAlchemy models
   - Session management
   - Database initialization
   - Migration utilities

   **Test Files to Create:**
   - `tests/unit/test_db_models.py` (20 tests)
   - `tests/unit/test_db_session.py` (8 tests)

   **Estimated Effort:** 2 hours
   **Coverage Gain:** +7%

#### Phase 3: Advanced Features (Day 4 afternoon) - Target 85%
**Focus:** Value-add features and quality improvements

5. **Integration Tests** - Create end-to-end workflow tests
   - Full SEC filing ingestion to report
   - User authentication to analysis
   - Cache warming and invalidation
   - External API integration patterns

   **Test Files to Create:**
   - `tests/integration/test_full_workflows.py` (8 tests)
   - `tests/integration/test_external_apis.py` (6 tests)

   **Estimated Effort:** 4 hours
   **Coverage Gain:** +5%

6. **Analysis Engine (src/analysis/)** - Currently 40%, Target 75%
   - Competitor analysis strategy
   - Segment opportunity analysis
   - Cohort retention analysis
   - Custom analysis engines

   **Test Files to Update:**
   - `tests/unit/test_analysis_service.py` (add 10 more tests)

   **Estimated Effort:** 2 hours
   **Coverage Gain:** +5%

### Testing Best Practices

**Test Structure:**
```python
# tests/unit/test_example.py
import pytest
from src.module import function_to_test

class TestModuleName:
    """Test suite for module_name functionality."""

    def test_happy_path(self, fixture):
        """Test normal operation with valid inputs."""
        result = function_to_test(valid_input)
        assert result == expected_output

    def test_edge_case_empty_input(self):
        """Test behavior with empty input."""
        with pytest.raises(ValueError, match="Input cannot be empty"):
            function_to_test("")

    def test_error_handling_invalid_type(self):
        """Test error handling for invalid input types."""
        with pytest.raises(TypeError):
            function_to_test(123)  # String expected

    @pytest.mark.asyncio
    async def test_async_operation(self, async_fixture):
        """Test asynchronous operations."""
        result = await async_function(input)
        assert result is not None
```

**Coverage Targets by Module Type:**
- **Critical Business Logic:** 90%+ (authentication, data processing)
- **API Endpoints:** 85%+ (request handling, validation)
- **Infrastructure:** 75%+ (caching, database, config)
- **Utilities:** 70%+ (helpers, formatters)
- **External Integrations:** 60%+ (API wrappers - often mocked)

### Coverage Verification
```bash
# Generate coverage report
pytest --cov=src --cov-report=html --cov-report=term-missing --cov-fail-under=80

# View detailed report
open htmlcov/index.html

# Check specific module
pytest --cov=src.api.v1.companies --cov-report=term-missing tests/unit/test_api_companies.py
```

---

## Integration Testing Plan

### Integration Testing Strategy

**Goal:** Validate component interactions and end-to-end workflows

### Test Levels

#### 1. Component Integration Tests
**Scope:** Two or more components working together
**Duration:** 10-30 seconds per test
**Dependencies:** Docker services (Postgres, Redis, MinIO)

**Examples:**
- API → Database (CRUD operations)
- API → Cache → Database (cache-aside pattern)
- Document Processor → Object Storage (file upload/download)
- Analysis Engine → Database → Cache (data retrieval)

**Test File: tests/integration/test_component_integration.py**
```python
@pytest.mark.integration
class TestComponentIntegration:
    async def test_api_database_crud(self, db_session, client):
        """Test API creates record in database."""
        response = client.post("/api/v1/companies", json=company_data)
        assert response.status_code == 201

        # Verify in database
        company = db_session.query(Company).filter_by(ticker="TEST").first()
        assert company is not None
        assert company.name == company_data["name"]

    async def test_cache_aside_pattern(self, redis_client, db_session):
        """Test cache-aside pattern implementation."""
        # First request - cache miss, DB hit
        result1 = await get_company_with_cache(ticker="AAPL")
        assert result1 is not None

        # Verify cached
        cached = await redis_client.get("company:AAPL")
        assert cached is not None

        # Second request - cache hit
        result2 = await get_company_with_cache(ticker="AAPL")
        assert result2 == result1
```

#### 2. External API Integration Tests
**Scope:** Integration with external services (SEC, Yahoo Finance, etc.)
**Duration:** 2-5 seconds per test (rate-limited)
**Dependencies:** Live API keys (or mocked)

**Test Approach:**
- Use **real API calls** in staging/CI with rate limiting
- Use **VCR.py** to record/replay API responses
- Use **mocks** for unit tests

**Test File: tests/integration/test_external_apis.py**
```python
import pytest
import vcr

@pytest.mark.integration
@pytest.mark.slow
class TestExternalAPIIntegration:

    @vcr.use_cassette('fixtures/vcr/sec_filing.yaml')
    def test_sec_api_fetch_10k(self):
        """Test SEC EDGAR API integration."""
        filing = fetch_sec_filing(cik="0001326801", form_type="10-K")
        assert filing is not None
        assert filing.form_type == "10-K"

    @vcr.use_cassette('fixtures/vcr/yahoo_finance.yaml')
    def test_yahoo_finance_stock_data(self):
        """Test Yahoo Finance API integration."""
        data = fetch_stock_data(ticker="AAPL", period="1d")
        assert data is not None
        assert "Close" in data.columns

    @pytest.mark.skipif(not os.getenv("LIVE_API_TEST"), reason="Live API test")
    async def test_alpha_vantage_live(self):
        """Test Alpha Vantage API with live credentials."""
        data = await fetch_alpha_vantage_data("AAPL", "TIME_SERIES_DAILY")
        assert data is not None
```

**VCR.py Setup:**
```python
# conftest.py
import vcr

@pytest.fixture(scope="module")
def vcr_config():
    return {
        "filter_headers": [("authorization", "REDACTED")],
        "filter_query_parameters": [("apikey", "REDACTED")],
        "record_mode": "once",  # Record on first run, replay after
    }
```

#### 3. End-to-End Workflow Tests
**Scope:** Complete business workflows from start to finish
**Duration:** 30-60 seconds per test
**Dependencies:** Full stack (API, DB, Cache, Object Storage)

**Test File: tests/integration/test_workflows.py**
```python
@pytest.mark.integration
@pytest.mark.e2e
class TestEndToEndWorkflows:

    async def test_sec_filing_to_analysis(self, client, auth_headers):
        """Test complete workflow: Ingest → Process → Analyze → Report."""

        # Step 1: Trigger SEC filing ingestion
        response = client.post(
            "/api/v1/filings/ingest",
            headers=auth_headers,
            json={"ticker": "DUOL", "form_type": "10-K", "year": 2024}
        )
        assert response.status_code == 202  # Accepted
        job_id = response.json()["job_id"]

        # Step 2: Wait for processing (poll status)
        for _ in range(30):
            status = client.get(f"/api/v1/jobs/{job_id}").json()
            if status["state"] == "completed":
                break
            await asyncio.sleep(2)

        assert status["state"] == "completed"
        filing_id = status["result"]["filing_id"]

        # Step 3: Verify filing stored
        filing = client.get(f"/api/v1/filings/{filing_id}").json()
        assert filing["ticker"] == "DUOL"
        assert filing["form_type"] == "10-K"

        # Step 4: Run analysis on filing
        analysis = client.post(
            "/api/v1/analysis/financial",
            headers=auth_headers,
            json={"filing_id": filing_id}
        ).json()

        assert analysis["revenue_growth"] is not None
        assert analysis["profitability_metrics"] is not None

        # Step 5: Generate report
        report = client.post(
            "/api/v1/reports/generate",
            headers=auth_headers,
            json={"analysis_id": analysis["id"]}
        ).json()

        assert report["status"] == "generated"
        assert report["download_url"] is not None
```

#### 4. Database Transaction Tests
**Scope:** ACID properties, concurrency, rollbacks
**Duration:** 5-10 seconds per test

**Test File: tests/integration/test_database_transactions.py**
```python
@pytest.mark.integration
class TestDatabaseTransactions:

    async def test_transaction_rollback_on_error(self, db_session):
        """Test database rollback on application error."""
        initial_count = db_session.query(Company).count()

        with pytest.raises(ValueError):
            async with db_session.begin():
                # Create company
                company = Company(ticker="TEST", name="Test Corp")
                db_session.add(company)

                # Simulate error
                raise ValueError("Simulated error")

        # Verify rollback
        final_count = db_session.query(Company).count()
        assert final_count == initial_count

    async def test_concurrent_updates_isolation(self):
        """Test database isolation with concurrent updates."""
        # Use two separate sessions
        async with get_session() as session1, get_session() as session2:
            company1 = session1.query(Company).filter_by(ticker="AAPL").first()
            company2 = session2.query(Company).filter_by(ticker="AAPL").first()

            # Update in both sessions
            company1.name = "Apple Inc. (Session 1)"
            company2.name = "Apple Inc. (Session 2)"

            await session1.commit()

            # Session 2 should fail due to conflict
            with pytest.raises(IntegrityError):
                await session2.commit()
```

### Integration Test Execution Strategy

**Local Development:**
```bash
# Run all integration tests
pytest -m integration -v

# Run only fast integration tests (< 10s)
pytest -m "integration and not slow" -v

# Run specific workflow test
pytest tests/integration/test_workflows.py::TestEndToEndWorkflows::test_sec_filing_to_analysis -v
```

**CI/CD Pipeline:**
```yaml
# .github/workflows/integration-tests.yml
name: Integration Tests

on: [push, pull_request]

jobs:
  integration:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: timescale/timescaledb:latest-pg15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s

      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"

      minio:
        image: minio/minio:latest
        env:
          MINIO_ROOT_USER: minioadmin
          MINIO_ROOT_PASSWORD: minioadmin
        options: >-
          --health-cmd "curl -f http://localhost:9000/minio/health/live"

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-test.txt

      - name: Run integration tests
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost/test_db
          REDIS_URL: redis://localhost:6379/0
          MINIO_ENDPOINT: localhost:9000
        run: |
          pytest -m integration --cov=src --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

**Staging Environment:**
```bash
# Run integration tests against staging
ENVIRONMENT=staging pytest -m integration --slow -v

# Run only external API tests with live credentials
LIVE_API_TEST=1 pytest tests/integration/test_external_apis.py -v
```

### Integration Test Coverage Goals

**Target Coverage:**
- Component Integration: 60%+ of component interactions
- External APIs: 40%+ (limited by rate limits)
- End-to-End Workflows: 80%+ of critical user journeys
- Database Transactions: 70%+ of transaction scenarios

**Critical Workflows to Test:**
1. SEC filing ingestion → analysis → report (most important)
2. User registration → authentication → API access
3. Company creation → metrics ingestion → dashboard update
4. Document upload → embedding generation → semantic search
5. Cache population → invalidation → refresh

---

## Performance & Load Testing Approach

### Performance Testing Goals

**Objectives:**
1. Validate application meets performance SLAs
2. Identify bottlenecks and optimization opportunities
3. Determine maximum capacity and scaling thresholds
4. Establish performance baseline for future monitoring

### Performance SLA Targets

| Metric | Target | Critical Threshold |
|--------|--------|-------------------|
| API Response Time (p50) | < 50ms | < 100ms |
| API Response Time (p95) | < 150ms | < 300ms |
| API Response Time (p99) | < 300ms | < 500ms |
| Database Query Time (p95) | < 25ms | < 50ms |
| Cache Hit Ratio | > 80% | > 60% |
| Error Rate | < 0.1% | < 1% |
| Throughput | 500 req/s | 200 req/s |
| Concurrent Users | 100+ | 50+ |

### Testing Tools

**Primary Tool: k6 (Recommended)**
- Cloud-native load testing
- JavaScript-based test scenarios
- Real-time metrics
- Integration with Prometheus/Grafana

**Alternative: Locust (Python-based)**
- More flexible for complex scenarios
- Python-based test definition
- Web UI for monitoring

### k6 Test Scenarios

#### 1. Smoke Test (Baseline Validation)
**Purpose:** Verify system works with minimal load
**Duration:** 5 minutes
**Users:** 1-5

```javascript
// tests/load/smoke-test.js
import http from 'k6/http';
import { check, sleep } from 'k6';

export let options = {
  vus: 5,
  duration: '5m',
  thresholds: {
    http_req_duration: ['p(95)<500'],
    http_req_failed: ['rate<0.01'],
  },
};

const BASE_URL = __ENV.API_URL || 'http://localhost:8000';

export default function () {
  // Health check
  let health = http.get(`${BASE_URL}/health`);
  check(health, { 'health check': (r) => r.status === 200 });

  // List companies
  let companies = http.get(`${BASE_URL}/api/v1/companies`);
  check(companies, {
    'status is 200': (r) => r.status === 200,
    'response time < 500ms': (r) => r.timings.duration < 500,
  });

  sleep(1);
}
```

#### 2. Load Test (Sustained Traffic)
**Purpose:** Test system under expected production load
**Duration:** 30 minutes
**Users:** 10-50-100

```javascript
// tests/load/load-test.js
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

let errorRate = new Rate('errors');
let responseTime = new Trend('response_time');

export let options = {
  stages: [
    { duration: '5m', target: 10 },   // Ramp up to 10 users
    { duration: '10m', target: 50 },  // Ramp up to 50 users
    { duration: '10m', target: 100 }, // Ramp up to 100 users
    { duration: '5m', target: 0 },    // Ramp down
  ],
  thresholds: {
    'http_req_duration': ['p(95)<200', 'p(99)<500'],
    'http_req_failed': ['rate<0.01'],
    'errors': ['rate<0.01'],
  },
};

const BASE_URL = __ENV.API_URL || 'http://localhost:8000';

// Test data
const TICKERS = ['AAPL', 'DUOL', 'CHGG', 'COUR', 'TWOU'];

export default function () {
  // Weighted scenario: 70% reads, 30% writes
  let rand = Math.random();

  if (rand < 0.7) {
    // Read operations
    readScenario();
  } else {
    // Write operations (requires auth)
    writeScenario();
  }

  sleep(Math.random() * 3); // Random think time 0-3s
}

function readScenario() {
  let responses = http.batch([
    ['GET', `${BASE_URL}/api/v1/companies`],
    ['GET', `${BASE_URL}/api/v1/companies?ticker=${TICKERS[Math.floor(Math.random() * TICKERS.length)]}`],
    ['GET', `${BASE_URL}/health/database`],
  ]);

  responses.forEach((response) => {
    errorRate.add(response.status !== 200);
    responseTime.add(response.timings.duration);
    check(response, {
      'status is 200': (r) => r.status === 200,
    });
  });
}

function writeScenario() {
  // Authenticate first (cache token)
  let authResponse = http.post(`${BASE_URL}/auth/login`, JSON.stringify({
    email: 'loadtest@example.com',
    password: 'LoadTest123!',
  }), {
    headers: { 'Content-Type': 'application/json' },
  });

  if (authResponse.status === 200) {
    let token = authResponse.json('access_token');

    // Perform write operation
    let writeResponse = http.post(
      `${BASE_URL}/api/v1/companies`,
      JSON.stringify({
        ticker: `TEST${Date.now()}`,
        name: 'Load Test Company',
        sector: 'EdTech',
      }),
      {
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
      }
    );

    errorRate.add(writeResponse.status !== 201);
    responseTime.add(writeResponse.timings.duration);
  }
}
```

#### 3. Stress Test (Breaking Point)
**Purpose:** Find system limits and failure modes
**Duration:** 20 minutes
**Users:** Ramp up until failure

```javascript
// tests/load/stress-test.js
export let options = {
  stages: [
    { duration: '2m', target: 50 },
    { duration: '5m', target: 100 },
    { duration: '5m', target: 200 },
    { duration: '5m', target: 300 },
    { duration: '3m', target: 0 },
  ],
  thresholds: {
    'http_req_duration': ['p(95)<1000'], // More lenient
    'http_req_failed': ['rate<0.05'],     // Accept 5% errors at peak
  },
};

// Same test logic as load test
```

#### 4. Spike Test (Traffic Surge)
**Purpose:** Test autoscaling and resilience to sudden load
**Duration:** 15 minutes
**Users:** Sudden spike from 10 to 200

```javascript
// tests/load/spike-test.js
export let options = {
  stages: [
    { duration: '2m', target: 10 },   // Normal load
    { duration: '1m', target: 200 },  // Sudden spike
    { duration: '5m', target: 200 },  // Sustained spike
    { duration: '2m', target: 10 },   // Return to normal
    { duration: '5m', target: 10 },   // Recovery
  ],
  thresholds: {
    'http_req_duration': ['p(95)<500'], // Allow degradation during spike
  },
};
```

### Database Performance Testing

#### Query Performance Benchmarks
```sql
-- tests/performance/benchmark_queries.sql

-- 1. Companies list with pagination (target: < 20ms)
EXPLAIN ANALYZE
SELECT * FROM companies
ORDER BY created_at DESC
LIMIT 50 OFFSET 0;

-- 2. Financial metrics time series (target: < 30ms)
EXPLAIN ANALYZE
SELECT ticker, metric_name, value, report_period
FROM financial_metrics
WHERE ticker = 'AAPL'
  AND report_period >= NOW() - INTERVAL '5 years'
ORDER BY report_period DESC;

-- 3. Document similarity search (target: < 50ms)
EXPLAIN ANALYZE
SELECT filing_id, 1 - (embedding <=> '[0.1, 0.2, ...]'::vector) AS similarity
FROM document_embeddings
ORDER BY embedding <=> '[0.1, 0.2, ...]'::vector
LIMIT 10;

-- 4. Aggregated metrics (target: < 100ms)
EXPLAIN ANALYZE
SELECT
  ticker,
  AVG(value) as avg_value,
  STDDEV(value) as stddev_value
FROM financial_metrics
WHERE metric_name = 'revenue'
  AND report_period >= NOW() - INTERVAL '1 year'
GROUP BY ticker;
```

**Optimization Checklist:**
- [ ] Indexes on foreign keys
- [ ] Indexes on frequently queried columns
- [ ] TimescaleDB compression enabled
- [ ] Connection pooling configured (min: 10, max: 50)
- [ ] Query result caching in Redis
- [ ] Database statistics updated (ANALYZE)

### Performance Monitoring During Tests

**Real-Time Monitoring Stack:**
```bash
# Start monitoring before tests
docker-compose --profile observability up -d

# Grafana: http://localhost:3000
# Prometheus: http://localhost:9090
# Jaeger: http://localhost:16686
```

**Metrics to Monitor:**
1. **API Metrics:**
   - Request rate (requests/second)
   - Response time (p50, p95, p99)
   - Error rate (errors/second)
   - Active connections

2. **Database Metrics:**
   - Connection pool usage
   - Query duration
   - Slow queries (> 100ms)
   - Lock wait time
   - Cache hit ratio

3. **System Metrics:**
   - CPU usage (per container)
   - Memory usage (per container)
   - Disk I/O
   - Network throughput

4. **Cache Metrics:**
   - Redis memory usage
   - Cache hit/miss ratio
   - Eviction rate

### Test Execution Plan

**Day 5 Morning (4 hours):**
1. **Setup (1 hour)**
   - Install k6: `curl https://github.com/grafana/k6/releases/download/v0.47.0/k6-v0.47.0-linux-amd64.tar.gz -L | tar xvz`
   - Start monitoring stack
   - Prepare test environment (seed database)
   - Create test user accounts

2. **Smoke Test (30 minutes)**
   ```bash
   k6 run tests/load/smoke-test.js
   ```
   - Verify all endpoints respond
   - Establish baseline metrics

3. **Load Test (1.5 hours)**
   ```bash
   k6 run --out json=results/load-test.json tests/load/load-test.js
   ```
   - Monitor Grafana dashboards
   - Identify slow endpoints
   - Check database query performance

4. **Analysis (1 hour)**
   - Review k6 summary report
   - Analyze slow queries in database logs
   - Identify bottlenecks (CPU, memory, DB, cache)
   - Document findings

**Day 5 Afternoon (4 hours):**
1. **Optimization (3 hours)**
   - Add missing database indexes
   - Tune connection pool settings
   - Implement query result caching
   - Optimize slow endpoints

2. **Validation (1 hour)**
   - Re-run load test
   - Verify improvements
   - Document before/after metrics

### Performance Test Success Criteria

**Must Pass:**
- ✅ API p95 response time < 200ms under 100 concurrent users
- ✅ Error rate < 1% during load test
- ✅ Database connection pool < 80% utilization
- ✅ Cache hit ratio > 60%
- ✅ No memory leaks (stable memory usage over time)

**Target (Nice to Have):**
- ✅ API p99 response time < 300ms
- ✅ Throughput > 500 requests/second
- ✅ Cache hit ratio > 80%
- ✅ Database query time p95 < 25ms

### Performance Test Report Template

```markdown
# Performance Test Report

## Test Environment
- Date: YYYY-MM-DD
- Duration: X hours
- Infrastructure: Docker Compose / Kubernetes
- Database: PostgreSQL 15 + TimescaleDB
- Cache: Redis 7

## Test Scenarios Executed
1. Smoke Test (5 minutes, 5 VUs)
2. Load Test (30 minutes, 10-100 VUs)
3. Stress Test (20 minutes, 50-300 VUs)

## Results Summary

| Metric | Target | Result | Status |
|--------|--------|--------|--------|
| API p50 Response Time | < 50ms | 42ms | ✅ |
| API p95 Response Time | < 200ms | 178ms | ✅ |
| API p99 Response Time | < 500ms | 312ms | ✅ |
| Error Rate | < 1% | 0.3% | ✅ |
| Throughput | 500 req/s | 612 req/s | ✅ |
| Cache Hit Ratio | > 80% | 84% | ✅ |

## Bottlenecks Identified
1. Database query on financial_metrics table (no index on ticker + report_period)
2. Connection pool exhaustion at 150+ concurrent users
3. Slow JSON serialization for large responses

## Optimizations Implemented
1. Added composite index: `CREATE INDEX idx_metrics_ticker_period ON financial_metrics(ticker, report_period)`
2. Increased connection pool max from 20 to 50
3. Implemented pagination for large responses

## Recommendations
1. Consider read replicas for database at scale
2. Implement CDN for static assets
3. Add Redis Cluster for cache high availability
```

---

## Security Audit Checklist

### Pre-Deployment Security Review

**Completion Target:** Day 6 (8 hours)

#### 1. Authentication & Authorization (2 hours)

**JWT Token Security:**
- [ ] JWT secret key is cryptographically secure (32+ bytes)
  ```bash
  # Verify secret key strength
  python -c "import os; print(len(os.getenv('SECRET_KEY', '')))"  # Should be 32+
  ```
- [ ] Token expiration properly configured
  - Access token: 15 minutes
  - Refresh token: 7 days
- [ ] Token refresh mechanism implemented
- [ ] Token revocation functional (blacklist/Redis)
- [ ] No tokens stored in localStorage (XSS vulnerability)

**Password Security:**
- [ ] Password hashing uses bcrypt with cost factor 12+
  ```python
  # Verify in src/auth/service.py
  bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12))
  ```
- [ ] Password strength requirements enforced:
  - Minimum 8 characters
  - Contains uppercase, lowercase, number, special char
  - Not in common password list
- [ ] Password reset flow secure (token-based, time-limited)
- [ ] No password logging or exposure in error messages

**API Key Security:**
- [ ] API keys generated with secure random (32+ bytes)
- [ ] API keys stored hashed (not plaintext)
- [ ] API key revocation functional
- [ ] API key scopes/permissions enforced
- [ ] Rate limiting per API key

**Role-Based Access Control (RBAC):**
- [ ] Roles properly defined (viewer, analyst, admin)
- [ ] Permission checks on all protected endpoints
- [ ] No privilege escalation vulnerabilities
- [ ] Admin actions require admin role

**Test Commands:**
```bash
# Test authentication
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"security-test@example.com","password":"weak","username":"sectest"}'
# Should fail with weak password

curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"security-test@example.com","password":"Secure123!@#","username":"sectest"}'
# Should succeed

# Test token expiration
curl -X GET http://localhost:8000/api/v1/companies \
  -H "Authorization: Bearer EXPIRED_TOKEN"
# Should return 401 Unauthorized
```

#### 2. API Security (2 hours)

**Rate Limiting:**
- [ ] Rate limiting enabled (100 requests/minute per IP)
- [ ] Burst capacity configured
- [ ] Rate limit headers returned (X-RateLimit-Limit, X-RateLimit-Remaining)
- [ ] Different limits for authenticated vs anonymous
- [ ] Redis-based rate limiting (distributed)

**Implementation:**
```python
# src/core/middleware.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, storage_uri="redis://localhost:6379")

@app.get("/api/v1/companies")
@limiter.limit("100/minute")
async def list_companies():
    ...
```

**CORS Configuration:**
- [ ] CORS origins restricted (no wildcard `*` in production)
- [ ] Allowed methods explicitly defined
- [ ] Credentials handling secure
- [ ] Preflight requests handled

**Implementation:**
```python
# src/api/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://app.example.com"],  # No wildcard!
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
```

**Input Validation:**
- [ ] All inputs validated with Pydantic models
- [ ] Email validation enforced
- [ ] String length limits enforced
- [ ] Integer ranges validated
- [ ] File upload size limits enforced (10MB max)
- [ ] File type validation (MIME type checking)

**SQL Injection Prevention:**
- [ ] All database queries use parameterized statements
- [ ] SQLAlchemy ORM used (not raw SQL)
- [ ] No string concatenation in queries
- [ ] Dynamic filters properly escaped

**Verify:**
```python
# Good: Parameterized query
session.query(Company).filter(Company.ticker == user_input).first()

# Bad: String concatenation (DO NOT DO THIS)
session.execute(f"SELECT * FROM companies WHERE ticker = '{user_input}'")
```

**XSS Protection:**
- [ ] Response headers include X-Content-Type-Options: nosniff
- [ ] HTML special characters escaped in responses
- [ ] Content-Security-Policy header configured
- [ ] No user input rendered directly in HTML

**CSRF Protection:**
- [ ] CSRF tokens required for state-changing operations
- [ ] Double-submit cookie pattern implemented (for SPAs)
- [ ] SameSite cookie attribute set

**Security Headers:**
```python
# src/api/main.py
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response
```

**Test Commands:**
```bash
# Test rate limiting
for i in {1..150}; do
  curl -w "%{http_code}\n" http://localhost:8000/api/v1/companies -o /dev/null -s
done
# Should see 429 Too Many Requests after 100 requests

# Test CORS
curl -H "Origin: https://evil.com" http://localhost:8000/api/v1/companies -v
# Should not include Access-Control-Allow-Origin header

# Test SQL injection
curl "http://localhost:8000/api/v1/companies?ticker=AAPL'+OR+'1'='1"
# Should return 400 Bad Request (validation error)
```

#### 3. Infrastructure Security (2 hours)

**Environment Variables:**
- [ ] No hardcoded secrets anywhere in codebase
  ```bash
  # Scan for potential secrets
  git grep -i "password\|secret\|key\|token" | grep -v ".md"
  ```
- [ ] All sensitive config from environment variables
- [ ] .env file not committed to Git (.gitignore)
- [ ] .env.example contains only placeholders

**Docker Security:**
- [ ] Container runs as non-root user (UID 1000)
  ```dockerfile
  # Dockerfile
  RUN useradd -m -u 1000 -s /bin/bash appuser
  USER appuser
  ```
- [ ] Base image pinned with SHA256 digest
  ```dockerfile
  FROM python:3.11-slim@sha256:abc123...
  ```
- [ ] No sensitive data in Docker image layers
- [ ] .dockerignore prevents secret exposure
- [ ] Health check implemented
- [ ] Read-only root filesystem (where possible)

**Verify:**
```bash
# Check user in container
docker run --rm corporate-intel-api:latest whoami
# Should output: appuser

# Scan for vulnerabilities
docker scout cves corporate-intel-api:latest
docker scout recommendations corporate-intel-api:latest
```

**Database Security:**
- [ ] Database password strong (24+ characters)
- [ ] Database user has minimal required privileges
- [ ] PostgreSQL SSL/TLS enabled in production
- [ ] Database not exposed to public internet
- [ ] Connection pooling configured
- [ ] Prepared statements used (SQL injection prevention)

**Redis Security:**
- [ ] Redis password configured
- [ ] Redis not exposed to public internet
- [ ] Redis bind to localhost or private network only
- [ ] Redis maxmemory policy configured
- [ ] TLS enabled for Redis in production

**Object Storage (MinIO) Security:**
- [ ] MinIO access keys strong (24+ characters)
- [ ] Bucket policies restrict public access
- [ ] TLS enabled for MinIO in production
- [ ] Signed URLs for temporary access
- [ ] File upload virus scanning (optional, but recommended)

**Network Security:**
- [ ] Internal services not exposed to public internet
- [ ] Firewall rules configured (allow only necessary ports)
- [ ] Services communicate over private network
- [ ] TLS/SSL enabled for all external communication

**Test Commands:**
```bash
# Verify non-root user
docker exec corporate-intel-api whoami

# Check for exposed secrets in environment
docker exec corporate-intel-api env | grep -i "password\|secret\|key"
# Should show: POSTGRES_PASSWORD=*** (masked)

# Verify database connection encryption
docker exec corporate-intel-postgres psql -U intel_user -d corporate_intel -c "SHOW ssl;"
# Should show: on
```

#### 4. Dependency Security (1 hour)

**Dependency Scanning:**
- [ ] Run pip-audit for Python vulnerabilities
- [ ] Run safety check for known vulnerabilities
- [ ] Update vulnerable packages
- [ ] Document security exceptions (with justification)

**Commands:**
```bash
# Install security tools
pip install pip-audit safety

# Scan for vulnerabilities
pip-audit --desc
safety check --json --output safety-report.json

# Review results
cat safety-report.json | jq '.vulnerabilities[] | {package, severity, advisory}'

# Update vulnerable packages
pip install --upgrade <package-name>
```

**Supply Chain Security:**
- [ ] All dependencies from trusted sources (PyPI)
- [ ] Package integrity verified (checksums)
- [ ] Minimal dependencies (remove unused packages)
- [ ] Regular dependency updates scheduled

**License Compliance:**
- [ ] Review licenses of all dependencies
- [ ] Ensure GPL/AGPL compliance (if applicable)
- [ ] Document license attributions

#### 5. Application Security (1 hour)

**Error Handling:**
- [ ] No stack traces exposed to users
- [ ] Generic error messages for auth failures
- [ ] Detailed errors logged server-side only
- [ ] No sensitive data in error messages

**Implementation:**
```python
# src/core/exceptions.py
class BaseException(Exception):
    def __init__(self, detail: str):
        self.detail = detail
        # Log full error internally
        logger.error(f"Error: {detail}", exc_info=True)

    def to_response(self):
        # Return generic message to user
        return {"error": "An error occurred. Please try again."}
```

**Logging Security:**
- [ ] No passwords logged
- [ ] No API keys logged
- [ ] No PII logged (or encrypted if necessary)
- [ ] Logs access-controlled
- [ ] Log injection prevented

**File Upload Security:**
- [ ] File size limits enforced (10MB)
- [ ] File type validation (MIME type + magic bytes)
- [ ] Uploaded files stored outside web root
- [ ] File names sanitized (no path traversal)
- [ ] Virus scanning (optional, recommended)

**Session Management:**
- [ ] Session tokens securely generated
- [ ] Sessions expire after inactivity (30 minutes)
- [ ] Logout invalidates session
- [ ] Concurrent session limits enforced

#### 6. Compliance & Auditing (1 hour)

**Audit Logging:**
- [ ] All authentication events logged
- [ ] All authorization failures logged
- [ ] All data modifications logged
- [ ] Logs include: timestamp, user, action, result
- [ ] Logs tamper-proof (write-only, external storage)

**Data Protection:**
- [ ] Sensitive data encrypted at rest (database)
- [ ] Sensitive data encrypted in transit (TLS)
- [ ] PII handling complies with regulations (GDPR, CCPA)
- [ ] Data retention policy documented

**Incident Response:**
- [ ] Security incident response plan documented
- [ ] Contact information for security issues
- [ ] Automated alerting for security events
- [ ] Backup and recovery procedures tested

### Security Testing

**Automated Security Scans:**
```bash
# 1. Dependency vulnerabilities
pip-audit --format json --output security/pip-audit-report.json

# 2. Docker image scanning
docker scout cves corporate-intel-api:latest --format json > security/docker-scout-report.json

# 3. Static code analysis
bandit -r src/ -f json -o security/bandit-report.json

# 4. Secret detection
gitleaks detect --source . --report-path security/gitleaks-report.json
```

**Manual Security Testing:**
```bash
# 1. Authentication bypass attempts
curl -X GET http://localhost:8000/api/v1/companies/admin-only

# 2. SQL injection attempts
curl "http://localhost:8000/api/v1/companies?ticker=AAPL'+OR+'1'='1"

# 3. XSS attempts
curl -X POST http://localhost:8000/api/v1/companies \
  -d '{"name":"<script>alert(1)</script>"}'

# 4. Path traversal attempts
curl http://localhost:8000/api/v1/filings/../../etc/passwd

# 5. Rate limit bypass
for i in {1..200}; do curl http://localhost:8000/api/v1/companies & done
```

### Security Audit Report Template

```markdown
# Security Audit Report

**Date:** YYYY-MM-DD
**Auditor:** Security Agent
**Scope:** Production Deployment Security Review

## Summary
- Total Issues Found: X
- Critical: 0
- High: 0
- Medium: X
- Low: X

## Critical Issues (MUST FIX)
None

## High Priority Issues
None

## Medium Priority Issues
1. **Issue:** Rate limiting not enabled
   **Risk:** DoS vulnerability
   **Fix:** Implement Redis-based rate limiting
   **Status:** FIXED

## Low Priority Issues
1. **Issue:** Security headers missing
   **Risk:** Defense-in-depth
   **Fix:** Add security headers middleware
   **Status:** FIXED

## Compliance
- [x] No hardcoded secrets
- [x] Strong password policy
- [x] Secure session management
- [x] HTTPS enforced in production
- [x] Audit logging enabled

## Recommendations
1. Implement WAF (Web Application Firewall)
2. Set up automated security scanning in CI/CD
3. Conduct penetration testing before production launch

## Sign-Off
This application has passed security review and is approved for production deployment.
```

---

## Production Deployment Timeline

### 7-Day Detailed Schedule

**Overview:**
```
Day 1: Foundation (Environment + Dependencies)
Day 2: Startup Validation (Application + Tests)
Day 3: Test Coverage (API + Pipeline)
Day 4: Test Coverage (Infrastructure + Integration)
Day 5: Performance Testing
Day 6: Security Audit
Day 7: Production Deployment
```

### Day 1: Foundation & Environment Setup
**Date:** Day 1
**Duration:** 8 hours
**Focus:** Establish working environment

**Morning Session (4 hours)**
- 09:00-11:00: Environment configuration
  - Create .env from .env.example
  - Generate secure SECRET_KEY
  - Set database passwords
  - Configure Redis passwords
  - Set MinIO credentials
  - Add API keys (Alpha Vantage, NewsAPI)

- 11:00-13:00: Fix test dependencies
  - Create requirements-test.txt
  - Install OpenTelemetry modules
  - Install pytest plugins
  - Verify test discovery

**Afternoon Session (4 hours)**
- 14:00-17:00: Infrastructure startup
  - Start Docker Compose services
  - Verify PostgreSQL + TimescaleDB
  - Verify Redis connectivity
  - Verify MinIO storage
  - Check health endpoints

- 17:00-18:00: Database migration
  - Run Alembic migrations
  - Verify schema creation
  - Verify TimescaleDB hypertables
  - Verify pgvector extension

**End of Day Deliverables:**
✅ Working .env configuration
✅ Test dependencies installed
✅ Infrastructure services running
✅ Database schema initialized

---

### Day 2: Application Startup & Basic Testing
**Date:** Day 2
**Duration:** 8 hours
**Focus:** Validate application runs and passes tests

**Morning Session (4 hours)**
- 09:00-11:00: Application startup
  - Start FastAPI with Uvicorn
  - Test health endpoints
  - Test API documentation
  - Test authentication endpoints
  - Verify Prometheus metrics

- 11:00-13:00: Run existing test suite
  - Execute pytest with coverage
  - Document baseline coverage
  - Generate HTML coverage report
  - Identify failing tests

**Afternoon Session (4 hours)**
- 14:00-17:00: Fix critical test failures
  - Resolve OpenTelemetry imports
  - Fix database session issues
  - Update async test patterns
  - Resolve mocking issues

- 17:00-18:00: Coverage baseline documentation
  - Document current coverage by module
  - Identify top 10 untested modules
  - Create coverage improvement plan
  - Set module-specific targets

**End of Day Deliverables:**
✅ Application running
✅ All existing tests passing
✅ Baseline coverage: ~35%
✅ Coverage improvement plan

---

### Day 3: Test Coverage Expansion - Critical Modules
**Date:** Day 3
**Duration:** 8 hours
**Focus:** Increase coverage to 60%

**Morning Session (4 hours)**
- 09:00-13:00: API endpoint testing
  - Create tests/unit/test_api_companies.py
  - Create tests/unit/test_api_filings.py
  - Create tests/unit/test_api_metrics.py
  - Target: 85%+ coverage on API endpoints

**Afternoon Session (4 hours)**
- 14:00-18:00: Data pipeline testing
  - Create tests/unit/test_sec_ingestion.py
  - Create tests/unit/test_document_processor.py
  - Create tests/unit/test_metrics_extractor.py
  - Target: 40%+ coverage on pipeline

**End of Day Deliverables:**
✅ API endpoint coverage: 85%
✅ Pipeline coverage: 40%
✅ Overall coverage: ~60%

---

### Day 4: Test Coverage Expansion - Infrastructure
**Date:** Day 4
**Duration:** 8 hours
**Focus:** Achieve 80% overall coverage

**Morning Session (4 hours)**
- 09:00-13:00: Core infrastructure testing
  - Create tests/unit/test_core_cache.py
  - Create tests/unit/test_core_exceptions.py
  - Create tests/unit/test_core_dependencies.py
  - Create tests/unit/test_db_models.py

**Afternoon Session (4 hours)**
- 14:00-18:00: Integration test suite
  - Create tests/integration/test_full_workflows.py
  - Create tests/integration/test_database_transactions.py
  - Create tests/integration/test_external_apis.py
  - End-to-end workflow testing

**End of Day Deliverables:**
✅ Infrastructure coverage: 80%
✅ Integration test suite
✅ Overall coverage: 80%+

---

### Day 5: Performance Testing & Optimization
**Date:** Day 5
**Duration:** 8 hours
**Focus:** Validate performance SLAs

**Morning Session (4 hours)**
- 09:00-11:00: Performance test setup
  - Install k6 load testing tool
  - Create load test scenarios
  - Configure monitoring stack
  - Prepare test environment

- 11:00-13:00: Execute performance tests
  - Run smoke test (5 mins)
  - Run load test (30 mins)
  - Monitor database performance
  - Document bottlenecks

**Afternoon Session (4 hours)**
- 14:00-17:00: Performance optimization
  - Add missing database indexes
  - Tune connection pool settings
  - Implement query caching
  - Optimize slow endpoints

- 17:00-18:00: Validation
  - Re-run load tests
  - Verify improvements
  - Document performance metrics

**End of Day Deliverables:**
✅ Load test suite
✅ Performance baseline
✅ p95 latency < 200ms
✅ Throughput > 500 req/s

---

### Day 6: Security Hardening & Production Prep
**Date:** Day 6
**Duration:** 8 hours
**Focus:** Complete security audit

**Morning Session (4 hours)**
- 09:00-12:00: Security audit
  - Authentication & authorization review
  - API security validation
  - Rate limiting implementation
  - Security headers configuration

- 12:00-13:00: Dependency scanning
  - Run pip-audit
  - Run safety check
  - Update vulnerable packages

**Afternoon Session (4 hours)**
- 14:00-16:00: Docker security
  - Run container security scan
  - Verify non-root user
  - Pin base images
  - Update .dockerignore

- 16:00-18:00: Production runbook
  - Create deployment checklist
  - Document rollback procedures
  - Create smoke test script
  - Write incident response guide

**End of Day Deliverables:**
✅ Security audit passed
✅ All vulnerabilities resolved
✅ Docker image hardened
✅ Production runbook complete

---

### Day 7: Production Deployment & Validation
**Date:** Day 7
**Duration:** 8 hours
**Focus:** Deploy to production

**Morning Session (4 hours)**
- 09:00-11:00: Pre-deployment validation
  - Run full test suite
  - Verify 80%+ coverage
  - Run security scans
  - Execute performance tests
  - Final smoke test

- 11:00-13:00: Production deployment
  - Build production Docker images
  - Deploy to Kubernetes/Docker Compose
  - Run database migrations
  - Start application services

**Afternoon Session (4 hours)**
- 14:00-16:00: Post-deployment validation
  - Verify all pods/containers healthy
  - Run smoke tests against production
  - Test critical user flows
  - Verify monitoring operational

- 16:00-18:00: Observability setup
  - Start Prometheus + Grafana
  - Import dashboards
  - Configure alerts
  - Set up Sentry error tracking
  - Verify distributed tracing

**End of Day Deliverables:**
✅ Production deployment live
✅ All smoke tests passing
✅ Monitoring operational
✅ Team handoff complete

---

## Risk Assessment & Mitigation

### High-Impact Risks (Priority 1)

#### Risk 1: Untested Startup Sequence
**Impact:** HIGH
**Likelihood:** MEDIUM
**Risk Score:** 8/10

**Description:**
Application has never been started end-to-end with all services. Infrastructure services (Postgres, Redis, MinIO) may not connect properly, or application may fail during initialization.

**Mitigation Strategy:**
1. **Day 1-2:** Dedicated startup validation sessions
2. **Incremental Testing:** Start services one at a time and verify
3. **Health Checks:** Implement comprehensive health check endpoints
4. **Documentation:** Create detailed startup troubleshooting guide
5. **Rollback Plan:** Document clean shutdown procedures

**Validation:**
```bash
# Startup health check script
#!/bin/bash
echo "Checking PostgreSQL..."
docker exec postgres pg_isready || exit 1

echo "Checking Redis..."
docker exec redis redis-cli ping || exit 1

echo "Checking MinIO..."
curl -f http://localhost:9000/minio/health/live || exit 1

echo "Starting API..."
uvicorn src.api.main:app &
sleep 10

echo "Checking API health..."
curl -f http://localhost:8000/health || exit 1
```

**Contingency:**
If startup fails on Day 2:
- Allocate Day 3 morning to troubleshooting
- Adjust timeline: Delay coverage expansion by 4 hours
- Accept lower coverage target (75% instead of 80%)

---

#### Risk 2: Low Test Coverage (35% vs 80% Target)
**Impact:** HIGH
**Likelihood:** HIGH
**Risk Score:** 9/10

**Description:**
Current test coverage at 35% is significantly below 80% target. Critical modules (data pipeline, core infrastructure) have 0% coverage. Achieving 80% requires writing 150+ new tests in 16 hours (Days 3-4).

**Mitigation Strategy:**
1. **Prioritization:** Focus on business-critical paths first
2. **Parallel Work:** Divide tests across multiple sessions
3. **Test Templates:** Create reusable test patterns
4. **Acceptance Criteria:** Define minimum coverage per module
5. **Fallback Plan:** Accept 75% coverage if needed

**Coverage Priorities:**
1. **Tier 1 (Must Cover - 90%+):**
   - Authentication (already 85%)
   - API endpoints (companies, filings, metrics)
   - Database models

2. **Tier 2 (Should Cover - 70%+):**
   - Data pipeline (ingestion, processing)
   - Core infrastructure (cache, exceptions)
   - Analysis engine

3. **Tier 3 (Nice to Cover - 50%+):**
   - Visualization components
   - Observability/telemetry
   - Utilities

**Time Allocation:**
- Day 3: 8 hours → Target +25% coverage (35% → 60%)
- Day 4: 8 hours → Target +20% coverage (60% → 80%)
- Buffer: Accept 75% if behind schedule

**Contingency:**
If coverage target missed:
- Document untested modules with justification
- Plan post-deployment coverage improvements
- Increase monitoring in production for untested paths
- Schedule 2-week sprint for remaining coverage

---

#### Risk 3: External API Dependencies
**Impact:** MEDIUM
**Likelihood:** HIGH
**Risk Score:** 7/10

**Description:**
Application depends on external APIs (SEC EDGAR, Yahoo Finance, Alpha Vantage, NewsAPI) which may:
- Change without notice
- Enforce rate limits
- Experience downtime
- Return unexpected data formats

**Mitigation Strategy:**
1. **Circuit Breaker Pattern:** Fail gracefully when API down
2. **Retry Logic:** Exponential backoff with jitter
3. **Aggressive Caching:** Cache API responses for 24 hours
4. **Rate Limit Handling:** Implement rate limit detection and backoff
5. **Monitoring:** Alert on API failures

**Implementation:**
```python
# src/connectors/resilient_client.py
from tenacity import retry, stop_after_attempt, wait_exponential

class ResilientAPIClient:
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def fetch_data(self, url: str):
        try:
            response = await http_client.get(url)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:  # Rate limit
                wait_time = e.response.headers.get("Retry-After", 60)
                await asyncio.sleep(int(wait_time))
                raise  # Retry
            raise
```

**Monitoring:**
- Track API success/failure rates
- Alert if success rate < 95%
- Track rate limit events
- Monitor API response times

**Contingency:**
If external API fails in production:
1. Serve cached data (24-48 hours old)
2. Display staleness warning to users
3. Queue failed requests for retry
4. Fallback to alternative data source (if available)

---

### Medium-Impact Risks (Priority 2)

#### Risk 4: Performance at Scale
**Impact:** MEDIUM
**Likelihood:** MEDIUM
**Risk Score:** 5/10

**Description:**
Performance characteristics unknown under production load. May experience:
- Database connection pool exhaustion
- Slow queries under concurrent load
- Memory leaks over time
- CPU bottlenecks

**Mitigation Strategy:**
1. **Day 5:** Comprehensive load testing (100+ concurrent users)
2. **Connection Pooling:** Configure 20-50 database connections
3. **Query Optimization:** Add indexes, analyze slow queries
4. **Resource Limits:** Set memory/CPU limits per container
5. **Auto-scaling:** Configure HPA (Horizontal Pod Autoscaler)

**Load Test Scenarios:**
```javascript
// k6 load test
export let options = {
  stages: [
    { duration: '5m', target: 50 },   // Ramp to 50 users
    { duration: '10m', target: 100 }, // Sustain 100 users
    { duration: '5m', target: 200 },  // Spike to 200 users
  ],
  thresholds: {
    'http_req_duration': ['p(95)<200'],
    'http_req_failed': ['rate<0.01'],
  },
};
```

**Performance SLAs:**
- API p95 latency: < 200ms
- Database query p95: < 25ms
- Error rate: < 1%
- Throughput: 500+ req/s

**Contingency:**
If performance SLAs not met:
1. **Identify Bottleneck:**
   - Database: Add read replicas
   - API: Increase replicas
   - Cache: Add Redis cluster

2. **Quick Wins:**
   - Add missing indexes
   - Implement query result caching
   - Increase connection pool size

3. **If Still Failing:**
   - Accept degraded SLA temporarily (p95 < 500ms)
   - Schedule performance optimization sprint
   - Add performance monitoring alerts

---

#### Risk 5: Database Migration Failures
**Impact:** HIGH (but low likelihood)
**Likelihood:** LOW
**Risk Score:** 4/10

**Description:**
Database migrations may fail in production due to:
- Schema conflicts
- Data type mismatches
- TimescaleDB/pgvector extension issues
- Migration rollback problems

**Mitigation Strategy:**
1. **Pre-Deployment Testing:**
   - Test migrations on production-like data
   - Verify migration idempotency
   - Test rollback procedures

2. **Backup Strategy:**
   - Full database backup before migration
   - Point-in-time recovery enabled
   - Backup retention: 7 days

3. **Migration Safety:**
   - Run migrations in transaction (if possible)
   - Add checks for existing objects (IF NOT EXISTS)
   - Avoid data-destructive operations (DROP, TRUNCATE)

4. **Rollback Plan:**
   ```bash
   # If migration fails
   alembic downgrade -1  # Rollback one version
   pg_restore -d corporate_intel backup_pre_migration.sql
   ```

**Pre-Deployment Validation:**
```bash
# Test migration on copy of production data
pg_dump production_db > production_copy.sql
createdb test_migration
psql test_migration < production_copy.sql
alembic upgrade head
# Verify schema
alembic downgrade -1
# Verify clean rollback
```

**Contingency:**
If migration fails in production:
1. **Immediate:** Rollback migration using alembic downgrade
2. **If rollback fails:** Restore from backup
3. **Data loss < 5 minutes:** Restore from point-in-time recovery
4. **Incident response:** Document failure, create hotfix

---

### Low-Impact Risks (Priority 3)

#### Risk 6: Docker Image Size / Build Time
**Impact:** LOW
**Likelihood:** LOW
**Risk Score:** 2/10

**Description:**
Large Docker images may slow deployment and increase storage costs.

**Current State:**
- Multi-stage build already implemented
- Expected image size: 800MB - 1.2GB (Python + dependencies)

**Mitigation:**
- Already using `python:3.11-slim` base image
- Multi-stage build reduces layers
- .dockerignore excludes unnecessary files

**Monitoring:**
```bash
docker images corporate-intel-api:latest
# Target: < 1.5GB

docker history corporate-intel-api:latest
# Identify large layers
```

**Optimization (if needed):**
1. Use Alpine base image (reduces to ~400MB)
2. Install only production dependencies
3. Use Docker layer caching in CI/CD
4. Compress image with `docker save | gzip`

---

#### Risk 7: Third-Party Service Costs
**Impact:** LOW
**Likelihood:** MEDIUM
**Risk Score:** 3/10

**Description:**
External services may incur unexpected costs:
- Sentry error tracking
- External API rate limits
- Cloud infrastructure

**Mitigation:**
1. **Cost Monitoring:**
   - Set budget alerts in cloud provider
   - Monitor API usage/quotas
   - Track Sentry event volume

2. **Cost Optimization:**
   - Cache API responses aggressively
   - Implement request deduplication
   - Use free tiers where available

3. **Quotas:**
   - Alpha Vantage: 5 requests/minute (free tier)
   - NewsAPI: 100 requests/day (free tier)
   - Sentry: 5k events/month (free tier)

**Contingency:**
If costs exceed budget:
- Increase cache TTL (reduce API calls)
- Implement request queuing (batch API calls)
- Upgrade to paid tier (if justified)
- Reduce Sentry sampling rate

---

## Success Metrics & Monitoring Plan

### Production Readiness Metrics

**Deployment Readiness Score: 95/100**

| Category | Weight | Current | Target | Status |
|----------|--------|---------|--------|--------|
| Test Coverage | 20% | 35% → 80% | 80% | 🟢 On Track |
| Security Audit | 20% | 90% | 95% | 🟢 Excellent |
| Performance | 15% | TBD → p95<200ms | p95<200ms | 🟡 Testing Required |
| Documentation | 10% | 85% | 90% | 🟢 Good |
| Infrastructure | 15% | 80% | 95% | 🟡 Validation Needed |
| Integration Tests | 10% | 0% → 60% | 60% | 🟢 On Track |
| Observability | 10% | 75% | 90% | 🟡 Setup Required |

**Overall Score Calculation:**
```
Final Score = (80 * 0.20) + (95 * 0.20) + (95 * 0.15) + (90 * 0.10) + (95 * 0.15) + (60 * 0.10) + (90 * 0.10)
            = 16 + 19 + 14.25 + 9 + 14.25 + 6 + 9
            = 87.5/100 → Round to 88/100 (GOOD)
```

**Target by Day 7:** 95/100

---

### Application Performance Metrics

#### SLA Targets

**API Performance:**
- p50 response time: < 50ms (target), < 100ms (critical)
- p95 response time: < 150ms (target), < 300ms (critical)
- p99 response time: < 300ms (target), < 500ms (critical)
- p100 (max) response time: < 2000ms
- Error rate: < 0.1% (target), < 1% (critical)
- Availability: 99.9% (target), 99% (minimum)

**Database Performance:**
- Query duration p95: < 25ms (target), < 50ms (critical)
- Connection pool utilization: < 70% (target), < 90% (critical)
- Slow queries (>100ms): < 5% (target), < 10% (critical)
- Connection timeout errors: 0 (target), < 0.1% (critical)

**Cache Performance:**
- Cache hit ratio: > 80% (target), > 60% (critical)
- Cache response time p95: < 5ms
- Cache memory usage: < 80% max memory
- Eviction rate: < 10% of total requests

**System Resources:**
- CPU usage (per pod): < 70% (target), < 90% (critical)
- Memory usage (per pod): < 80% (target), < 95% (critical)
- Disk I/O wait: < 10%
- Network throughput: < 80% of capacity

#### Monitoring Stack Setup

**Prometheus Metrics Collection:**
```yaml
# monitoring/prometheus.yml
scrape_configs:
  - job_name: 'corporate-intel-api'
    static_configs:
      - targets: ['api:8000']
    metrics_path: '/metrics'
    scrape_interval: 15s
    scrape_timeout: 10s

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']
```

**Grafana Dashboards:**

1. **API Performance Dashboard**
   - Request rate (req/s)
   - Response time (p50, p95, p99)
   - Error rate (4xx, 5xx)
   - Active connections
   - Throughput (MB/s)

2. **Database Dashboard**
   - Active connections
   - Connection pool usage
   - Query duration (p50, p95, p99)
   - Slow queries (>100ms)
   - Locks and deadlocks
   - Cache hit ratio

3. **System Resources Dashboard**
   - CPU usage per pod
   - Memory usage per pod
   - Disk I/O
   - Network I/O
   - Pod restart count

4. **Business Metrics Dashboard**
   - Total companies tracked
   - SEC filings ingested (per day)
   - Analysis runs (per day)
   - Reports generated (per day)
   - Active users (DAU, MAU)

**Alert Rules:**
```yaml
# monitoring/alerts/api-alerts.yml
groups:
  - name: api_alerts
    interval: 30s
    rules:
      - alert: HighResponseTime
        expr: histogram_quantile(0.95, http_request_duration_seconds) > 0.3
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "API p95 response time > 300ms"
          description: "API response time has been high for 5 minutes"

      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.01
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Error rate > 1%"
          description: "API error rate exceeds threshold"

      - alert: DatabaseConnectionPoolExhausted
        expr: database_connections_active / database_connections_max > 0.9
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Database connection pool > 90%"
          description: "Database may reject new connections"

      - alert: LowCacheHitRatio
        expr: redis_keyspace_hits / (redis_keyspace_hits + redis_keyspace_misses) < 0.6
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Cache hit ratio < 60%"
          description: "Cache effectiveness is low"
```

---

### Distributed Tracing (Jaeger)

**Trace Collection:**
- All API requests traced
- Database queries traced
- External API calls traced
- Cache operations traced
- Background jobs traced

**Trace Analysis:**
- Identify slow endpoints
- Database query bottlenecks
- External API latency
- Service dependency map

**Setup:**
```python
# src/observability/telemetry.py
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# Initialize tracer
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

# OTLP exporter (Jaeger)
otlp_exporter = OTLPSpanExporter(
    endpoint="http://jaeger:4317",
    insecure=True
)
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(otlp_exporter)
)

# Instrument FastAPI
FastAPIInstrumentor.instrument_app(app)
```

---

### Error Tracking (Sentry)

**Error Monitoring:**
- All unhandled exceptions
- API errors (4xx, 5xx)
- Database errors
- External API failures
- Background job failures

**Sentry Integration:**
```python
# src/api/main.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

sentry_sdk.init(
    dsn=settings.SENTRY_DSN,
    environment=settings.ENVIRONMENT,
    traces_sample_rate=0.1,  # 10% of transactions
    integrations=[
        FastApiIntegration(),
        SqlalchemyIntegration(),
    ],
    before_send=filter_sensitive_data,  # Scrub PII
)
```

**Error Severity Levels:**
- **Critical:** Data loss, service down
- **Error:** Failed requests, database errors
- **Warning:** Performance degradation, rate limits
- **Info:** Successful operations, cache misses

---

### Log Aggregation

**Structured Logging (Loguru):**
```python
# src/core/logging_config.py
from loguru import logger
import sys

logger.remove()  # Remove default handler

# Console logging (development)
logger.add(
    sys.stdout,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
    level="INFO",
    colorize=True
)

# File logging (production)
logger.add(
    "logs/api-{time:YYYY-MM-DD}.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
    level="INFO",
    rotation="500 MB",
    retention="30 days",
    compression="zip"
)

# JSON logging (for log aggregation)
logger.add(
    "logs/api-json-{time:YYYY-MM-DD}.log",
    format=lambda record: json.dumps({
        "timestamp": record["time"].isoformat(),
        "level": record["level"].name,
        "message": record["message"],
        "module": record["name"],
        "function": record["function"],
        "line": record["line"],
    }) + "\n",
    level="INFO",
    rotation="500 MB",
    retention="30 days"
)
```

**Log Levels:**
- DEBUG: Development debugging
- INFO: Normal operations (requests, responses)
- WARNING: Rate limits, slow queries, cache misses
- ERROR: Failed requests, database errors
- CRITICAL: Service failures, data corruption

**Log Analysis:**
- Aggregate logs with ELK stack (optional)
- Search logs by request ID
- Track error patterns
- Identify slow operations

---

### Business Metrics

**User Metrics:**
- Daily Active Users (DAU)
- Monthly Active Users (MAU)
- New user registrations (per day)
- User retention (7-day, 30-day)

**Data Metrics:**
- Total companies tracked
- SEC filings ingested (per day)
- Financial metrics stored
- Documents processed
- Embeddings generated

**Analysis Metrics:**
- Analysis runs (per day)
- Reports generated (per day)
- Average analysis duration
- Cache hit rate for analysis

**API Metrics:**
- Total API requests (per day)
- API requests by endpoint
- API requests by user
- API key usage

**Implementation:**
```python
# src/api/middleware.py
from prometheus_client import Counter, Histogram

# Business metrics
api_requests_total = Counter(
    'api_requests_total',
    'Total API requests',
    ['method', 'endpoint', 'status']
)

filings_ingested_total = Counter(
    'filings_ingested_total',
    'Total SEC filings ingested'
)

analysis_duration = Histogram(
    'analysis_duration_seconds',
    'Analysis execution duration',
    ['analysis_type']
)

@app.middleware("http")
async def track_metrics(request: Request, call_next):
    response = await call_next(request)
    api_requests_total.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    return response
```

---

### Health Checks & Uptime Monitoring

**Health Check Endpoints:**

1. **Basic Health Check (`/health`):**
   ```python
   @app.get("/health")
   async def health_check():
       return {
           "status": "healthy",
           "version": settings.APP_VERSION,
           "timestamp": datetime.utcnow().isoformat()
       }
   ```

2. **Database Health Check (`/health/database`):**
   ```python
   @app.get("/health/database")
   async def database_health(db: AsyncSession = Depends(get_db)):
       try:
           await db.execute(text("SELECT 1"))
           return {"status": "healthy", "database": "connected"}
       except Exception as e:
           raise HTTPException(status_code=503, detail=f"Database unhealthy: {str(e)}")
   ```

3. **Dependencies Health Check (`/health/dependencies`):**
   ```python
   @app.get("/health/dependencies")
   async def dependencies_health():
       checks = {
           "database": await check_database(),
           "redis": await check_redis(),
           "minio": await check_minio(),
       }
       all_healthy = all(checks.values())
       status_code = 200 if all_healthy else 503
       return JSONResponse(status_code=status_code, content=checks)
   ```

**Uptime Monitoring:**
- Use external monitoring service (UptimeRobot, Pingdom)
- Check `/health` endpoint every 5 minutes
- Alert if downtime > 5 minutes
- Track uptime SLA (99.9% target)

---

### Monitoring Dashboard Screenshots

**Grafana Dashboard Layout:**

```
┌─────────────────────────────────────────────────────┐
│ Corporate Intelligence Platform - API Performance   │
├───────────────┬─────────────────┬───────────────────┤
│ Request Rate  │ Response Time   │ Error Rate        │
│ 523 req/s     │ p95: 142ms      │ 0.08%             │
├───────────────┴─────────────────┴───────────────────┤
│ Response Time Distribution (Last 1 hour)            │
│ ▁▂▃▄▅▆█▇▆▅▄▃▂▁ (histogram)                          │
├─────────────────────────────────────────────────────┤
│ Top 5 Slowest Endpoints                             │
│ 1. /api/v1/analysis/competitor - 387ms              │
│ 2. /api/v1/filings/search - 234ms                   │
│ 3. /api/v1/companies?limit=100 - 156ms              │
├─────────────────────────────────────────────────────┤
│ Database Performance                                │
│ Connections: 23/50 (46%)                            │
│ Query p95: 18ms                                     │
│ Slow queries: 2.3%                                  │
├─────────────────────────────────────────────────────┤
│ Cache Performance                                   │
│ Hit ratio: 84%                                      │
│ Memory: 312MB / 512MB (61%)                         │
└─────────────────────────────────────────────────────┘
```

---

### Production Validation Checklist

**Pre-Deployment Validation:**
- [ ] All tests passing (100%)
- [ ] Test coverage ≥ 80%
- [ ] Security audit passed (0 critical issues)
- [ ] Performance tests passed (p95 < 200ms)
- [ ] Load tests passed (100+ concurrent users)
- [ ] Docker image scanned (no critical CVEs)
- [ ] Documentation complete
- [ ] Runbooks created

**Post-Deployment Validation:**
- [ ] All pods/containers healthy
- [ ] Health checks passing (`/health`, `/health/database`)
- [ ] Database migrations applied successfully
- [ ] API endpoints responding (smoke test)
- [ ] Authentication working
- [ ] Monitoring operational (Prometheus, Grafana, Jaeger)
- [ ] Alerts configured
- [ ] Logs being collected

**Day 1 Production Checklist:**
- [ ] Monitor error rate (target < 1%)
- [ ] Monitor response times (target p95 < 200ms)
- [ ] Monitor database connection pool (< 70%)
- [ ] Monitor cache hit ratio (> 60%)
- [ ] Check for memory leaks (stable over 24 hours)
- [ ] Verify data ingestion working
- [ ] Test critical user flows
- [ ] Review Sentry for unexpected errors

---

### Success Criteria

**Production Deployment is considered SUCCESSFUL if:**

1. **Availability:**
   - Uptime > 99% in first 7 days
   - No unplanned downtime > 10 minutes
   - All health checks passing continuously

2. **Performance:**
   - API p95 < 300ms (critical threshold)
   - Error rate < 1%
   - Database queries < 50ms (p95)
   - Cache hit ratio > 60%

3. **Reliability:**
   - No data loss
   - No critical security incidents
   - Backup and restore tested successfully
   - Rollback procedures documented and tested

4. **Monitoring:**
   - All monitoring dashboards operational
   - Alerts configured and tested
   - Incident response plan in place
   - On-call rotation established

5. **Quality:**
   - Test coverage ≥ 80%
   - Security audit passed
   - Code review completed
   - Documentation up-to-date

**If any success criteria not met:**
- Document issue and workaround
- Create remediation plan
- Schedule post-deployment improvements
- Increase monitoring for affected areas

---

## Final Deliverables

**Documentation:**
1. Production Deployment Roadmap (this document)
2. Test Coverage Report
3. Security Audit Report
4. Performance Test Report
5. API Documentation (OpenAPI)
6. Operations Runbook
7. Incident Response Guide

**Code & Tests:**
1. Production-ready application code
2. Comprehensive test suite (80%+ coverage)
3. Load test scripts (k6)
4. Smoke test scripts

**Infrastructure:**
1. Docker Compose configuration
2. Kubernetes manifests
3. CI/CD pipeline (.github/workflows)
4. Monitoring configuration (Prometheus, Grafana)

**Deployment Artifacts:**
1. Docker images (tagged and pushed)
2. Database migration files
3. Configuration templates
4. Deployment scripts

---

**END OF ROADMAP**

**Next Steps:** Begin Day 1 execution immediately.

**Questions/Issues:** Contact deployment team lead.

**Version:** 1.0
**Last Updated:** October 2, 2025
**Maintained By:** Production Readiness Specialist Agent
