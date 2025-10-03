# Test Architecture - Corporate Intelligence Platform

## Executive Summary

This document defines the comprehensive testing strategy for the Corporate Intelligence Platform, a FastAPI application with authentication, API endpoints, database integration, and distributed processing capabilities. The goal is to achieve 80%+ test coverage across all modules with a focus on quality, maintainability, and reliability.

## Architecture Overview

### Current State
- 0% test coverage (critical gap)
- No existing test infrastructure
- Production-ready codebase without tests

### Target State
- 80%+ overall test coverage
- 90%+ coverage for critical paths (auth, API endpoints)
- Full CI/CD integration with test gates
- Performance and load testing baseline

## Test Strategy by Layer

### 1. Unit Tests (Target: 85% coverage)

**Purpose**: Test individual components in isolation with mocked dependencies.

**Coverage Areas**:
- Service layer logic (auth, metrics extraction, document processing)
- Utilities and helper functions
- Model methods and validators
- Configuration management

**Testing Approach**:
- Mock external dependencies (database, Redis, MinIO, APIs)
- Use pytest fixtures for common test objects
- Fast execution (< 5 seconds for full unit test suite)
- No external service dependencies

**Coverage Targets**:
| Module | Target Coverage | Priority |
|--------|----------------|----------|
| src/auth/service.py | 90% | Critical |
| src/processing/metrics_extractor.py | 85% | High |
| src/processing/text_chunker.py | 85% | High |
| src/core/config.py | 90% | Critical |
| src/core/cache.py | 80% | Medium |
| src/validation/data_quality.py | 85% | High |

### 2. Integration Tests (Target: 75% coverage)

**Purpose**: Test interactions between components with real database.

**Coverage Areas**:
- API endpoint behavior (FastAPI routes)
- Database operations (SQLAlchemy models and queries)
- Authentication flows (JWT, API keys, sessions)
- Cache interactions (Redis)
- File storage (MinIO)

**Testing Approach**:
- Use TestContainers for PostgreSQL, Redis, MinIO
- Real database transactions with rollback after each test
- HTTP client testing with TestClient
- Async test patterns for FastAPI endpoints

**Coverage Targets**:
| Module | Target Coverage | Priority |
|--------|----------------|----------|
| src/api/v1/companies.py | 85% | Critical |
| src/api/v1/filings.py | 80% | High |
| src/api/v1/metrics.py | 80% | High |
| src/api/v1/intelligence.py | 80% | High |
| src/api/v1/reports.py | 75% | Medium |
| src/auth/routes.py | 90% | Critical |

### 3. End-to-End Tests (Target: 60% coverage)

**Purpose**: Test complete user workflows and critical paths.

**Coverage Areas**:
- User registration and login flows
- Company data ingestion pipeline
- SEC filing processing workflow
- Report generation end-to-end
- API authentication and authorization

**Testing Approach**:
- Full stack integration with all services running
- Docker Compose test environment
- Real external API mocking (SEC EDGAR)
- Performance measurement during E2E tests

### 4. Performance Tests

**Purpose**: Establish baseline performance and identify bottlenecks.

**Test Scenarios**:
- API endpoint latency (p50, p95, p99)
- Database query performance
- Document processing throughput
- Concurrent user handling
- Vector search performance

**Tools**:
- Locust for load testing
- pytest-benchmark for microbenchmarks
- Custom Ray performance tests

**Targets**:
| Metric | Target | Critical Threshold |
|--------|--------|--------------------|
| API response time (p95) | < 200ms | < 500ms |
| Document processing | 10 docs/sec | 5 docs/sec |
| Vector search | < 100ms | < 300ms |
| Concurrent users | 100+ | 50+ |

## Test Organization Structure

```
tests/
├── conftest.py                 # Global fixtures
├── unit/                       # Unit tests (fast, isolated)
│   ├── conftest.py            # Unit test fixtures
│   ├── test_auth_service.py
│   ├── test_metrics_extractor.py
│   ├── test_text_chunker.py
│   ├── test_config.py
│   └── test_cache.py
├── integration/               # Integration tests (with DB)
│   ├── conftest.py           # Integration fixtures
│   ├── test_api_companies.py
│   ├── test_api_filings.py
│   ├── test_api_auth.py
│   ├── test_database_models.py
│   └── test_cache_integration.py
├── e2e/                      # End-to-end tests
│   ├── conftest.py
│   ├── test_user_workflows.py
│   ├── test_ingestion_pipeline.py
│   └── test_report_generation.py
├── performance/              # Performance tests
│   ├── conftest.py
│   ├── test_api_load.py
│   ├── test_processing_throughput.py
│   └── locustfile.py
└── fixtures/                 # Test data
    ├── sample_filings/
    ├── sample_documents/
    └── test_data.json
```

## Fixture Design Patterns

### Global Fixtures (tests/conftest.py)

```python
# Database fixtures
@pytest.fixture(scope="session")
async def test_db_engine()
    """Create test database engine with TestContainers."""

@pytest.fixture(scope="function")
async def db_session()
    """Provide clean database session for each test."""

@pytest.fixture(scope="function")
async def test_client()
    """Provide FastAPI TestClient."""

# Authentication fixtures
@pytest.fixture
def test_user()
    """Create test user with standard permissions."""

@pytest.fixture
def admin_user()
    """Create admin user with all permissions."""

@pytest.fixture
def auth_headers()
    """Provide valid JWT auth headers."""

@pytest.fixture
def api_key_headers()
    """Provide valid API key headers."""

# Data fixtures
@pytest.fixture
def sample_company()
    """Create sample company in test database."""

@pytest.fixture
def sample_filing()
    """Create sample SEC filing."""

# Mock fixtures
@pytest.fixture
def mock_redis()
    """Mock Redis client."""

@pytest.fixture
def mock_minio()
    """Mock MinIO client."""
```

### Unit Test Fixtures (tests/unit/conftest.py)

```python
@pytest.fixture
def mock_db_session()
    """Mock SQLAlchemy session."""

@pytest.fixture
def sample_user_create()
    """Sample UserCreate pydantic model."""

@pytest.fixture
def mock_jwt_token()
    """Mock JWT token payload."""
```

### Integration Test Fixtures (tests/integration/conftest.py)

```python
@pytest.fixture(scope="session")
async def postgres_container()
    """Start PostgreSQL container."""

@pytest.fixture(scope="session")
async def redis_container()
    """Start Redis container."""

@pytest.fixture
async def isolated_db_transaction()
    """Database transaction that rolls back."""
```

## Test Data Management

### Strategy
1. **Minimal viable data**: Create only what's needed for each test
2. **Factories over fixtures**: Use factory pattern for complex objects
3. **Snapshot testing**: For complex JSON responses
4. **Synthetic data**: Generate realistic test data

### Test Data Sources
- `tests/fixtures/sample_filings/`: Real SEC filing samples (anonymized)
- `tests/fixtures/sample_documents/`: PDF samples for processing tests
- `tests/fixtures/test_data.json`: JSON fixtures for API responses
- Factory classes for model generation

### Factory Pattern Example

```python
class CompanyFactory:
    """Factory for creating test companies."""

    @staticmethod
    def create(db: Session, **kwargs):
        company_data = {
            "ticker": "TEST",
            "name": "Test Company",
            "cik": "0001234567",
            "category": "higher_education",
            **kwargs
        }
        company = Company(**company_data)
        db.add(company)
        db.commit()
        return company

class UserFactory:
    """Factory for creating test users."""

    @staticmethod
    def create(db: Session, role: UserRole = UserRole.VIEWER, **kwargs):
        user_data = {
            "email": f"test_{uuid4()}@example.com",
            "username": f"testuser_{uuid4()}",
            "hashed_password": pwd_context.hash("TestPass123!"),
            "role": role,
            **kwargs
        }
        user = User(**user_data)
        db.add(user)
        db.commit()
        return user
```

## Pytest Configuration

### pytest.ini

```ini
[pytest]
# Test discovery
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# Markers
markers =
    unit: Unit tests (fast, isolated)
    integration: Integration tests (with database)
    e2e: End-to-end tests (full stack)
    slow: Slow tests (> 1 second)
    performance: Performance tests
    requires_postgres: Requires PostgreSQL
    requires_redis: Requires Redis
    requires_minio: Requires MinIO

# Async support
asyncio_mode = auto

# Coverage
addopts =
    --verbose
    --strict-markers
    --cov=src
    --cov-report=term-missing
    --cov-report=html:coverage_html
    --cov-report=xml:coverage.xml
    --cov-fail-under=80

# Parallel execution
# Run with: pytest -n auto
```

### pyproject.toml (test configuration)

```toml
[tool.pytest.ini_options]
minversion = "7.0"
testpaths = ["tests"]

[tool.coverage.run]
source = ["src"]
omit = [
    "*/tests/*",
    "*/__pycache__/*",
    "*/site-packages/*",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
    "class .*\\bProtocol\\):",
    "@(abc\\.)?abstractmethod",
]

[tool.coverage.html]
directory = "coverage_html"
```

## Mock vs Real Database Strategy

### Unit Tests: ALWAYS MOCK
- Mock all database interactions
- Use MagicMock or pytest-mock
- Focus on business logic, not infrastructure

### Integration Tests: REAL DATABASE
- Use TestContainers for PostgreSQL
- Fresh database schema for each test session
- Transaction rollback for test isolation
- Real queries, real constraints, real relationships

### Decision Matrix

| Test Type | Database | Redis | MinIO | External APIs |
|-----------|----------|-------|-------|---------------|
| Unit | Mock | Mock | Mock | Mock |
| Integration | Real (Container) | Real (Container) | Mock | Mock |
| E2E | Real (Container) | Real (Container) | Real (Container) | Mock |
| Performance | Real (Staging) | Real (Staging) | Real (Staging) | Mock |

## Async Test Patterns

### Pytest-Asyncio Configuration

```python
import pytest
import pytest_asyncio
from httpx import AsyncClient
from fastapi import FastAPI

@pytest_asyncio.fixture
async def async_client(app: FastAPI) -> AsyncClient:
    """Provide async HTTP client for API testing."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.mark.asyncio
async def test_api_endpoint(async_client: AsyncClient):
    """Test async API endpoint."""
    response = await async_client.get("/api/v1/companies")
    assert response.status_code == 200
```

### AsyncIO Event Loop Management

```python
@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
```

## Coverage Targets Matrix

### Critical Modules (90%+ coverage required)

| Module | Lines | Target Coverage | Rationale |
|--------|-------|-----------------|-----------|
| src/auth/service.py | ~370 | 90% | Security critical |
| src/auth/dependencies.py | ~100 | 90% | Auth gates |
| src/core/config.py | ~160 | 90% | Configuration validation |
| src/api/v1/companies.py | ~275 | 85% | Core API functionality |
| src/db/models.py | ~280 | 85% | Data integrity |

### High Priority (80%+ coverage)

| Module | Lines | Target Coverage | Rationale |
|--------|-------|-----------------|-----------|
| src/api/v1/filings.py | ~250 | 80% | Important API |
| src/api/v1/metrics.py | ~200 | 80% | Analytics core |
| src/processing/metrics_extractor.py | ~300 | 85% | Business logic |
| src/processing/text_chunker.py | ~150 | 85% | Data processing |
| src/core/cache.py | ~100 | 80% | Performance critical |

### Medium Priority (70%+ coverage)

| Module | Lines | Target Coverage | Rationale |
|--------|-------|-----------------|-----------|
| src/api/v1/intelligence.py | ~200 | 75% | Feature API |
| src/api/v1/reports.py | ~180 | 75% | Report generation |
| src/processing/document_processor.py | ~300 | 75% | Complex processing |
| src/validation/data_quality.py | ~200 | 80% | Data validation |

### Excluded from Coverage
- `src/__init__.py` files (empty)
- `src/api/main.py` (application setup, tested via E2E)
- `src/visualization/*` (UI components, separate testing)

## Plugin Selection

### Required Plugins

```txt
# Core testing
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0
pytest-mock>=3.11.1

# Integration testing
pytest-docker>=2.0.0
testcontainers>=3.7.0
httpx>=0.24.0

# Performance testing
pytest-benchmark>=4.0.0
locust>=2.15.0

# Test utilities
pytest-xdist>=3.3.0        # Parallel test execution
pytest-timeout>=2.1.0       # Test timeouts
pytest-sugar>=0.9.7         # Better test output
pytest-html>=3.2.0          # HTML reports

# Mocking and fixtures
faker>=19.0.0               # Test data generation
factory-boy>=3.3.0          # Factory pattern
freezegun>=1.2.0            # Time mocking

# Database testing
alembic>=1.11.0             # Migration testing
sqlalchemy-utils>=0.41.1    # Database utilities
```

## Testing Standards

### Naming Conventions

```python
# Test file naming
test_<module_name>.py

# Test class naming
class TestUserAuthentication:
    """Test user authentication flows."""

# Test function naming
def test_create_user_with_valid_data_succeeds():
    """Test that creating user with valid data succeeds."""

def test_login_with_invalid_credentials_raises_authentication_error():
    """Test that login with invalid credentials raises error."""
```

### AAA Pattern (Arrange-Act-Assert)

```python
def test_create_company(db_session, auth_headers, async_client):
    """Test company creation."""
    # Arrange
    company_data = {
        "ticker": "TEST",
        "name": "Test Company",
        "cik": "0001234567",
        "category": "higher_education",
    }

    # Act
    response = await async_client.post(
        "/api/v1/companies",
        json=company_data,
        headers=auth_headers,
    )

    # Assert
    assert response.status_code == 201
    data = response.json()
    assert data["ticker"] == "TEST"
    assert data["name"] == "Test Company"
```

### Test Documentation

```python
def test_rate_limiting_blocks_excessive_requests():
    """Test that rate limiting blocks excessive requests.

    Given: A user with API rate limit of 100 requests/day
    When: User makes 101 requests in one day
    Then: 101st request returns 429 Too Many Requests
    And: Response includes Retry-After header
    """
```

### Parametrized Tests

```python
@pytest.mark.parametrize("role,expected_status", [
    (UserRole.ADMIN, 200),
    (UserRole.EDITOR, 200),
    (UserRole.VIEWER, 403),
    (UserRole.GUEST, 401),
])
def test_endpoint_authorization_by_role(role, expected_status, client):
    """Test endpoint authorization for different user roles."""
    user = create_user_with_role(role)
    response = client.get("/admin/endpoint", auth=user)
    assert response.status_code == expected_status
```

## Performance Testing Guidelines

### Benchmark Structure

```python
def test_metrics_extraction_performance(benchmark, sample_filing_text):
    """Benchmark metrics extraction performance."""
    extractor = EdTechMetricsExtractor()

    result = benchmark(extractor.extract_metrics, sample_filing_text)

    # Performance assertions
    assert benchmark.stats.mean < 0.5  # Mean under 500ms
    assert len(result) > 0  # Should extract metrics
```

### Load Testing

```python
# tests/performance/locustfile.py
from locust import HttpUser, task, between

class CorporateIntelUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def get_companies(self):
        self.client.get("/api/v1/companies")

    @task(1)
    def get_company_metrics(self):
        self.client.get("/api/v1/companies/uuid/metrics")
```

## CI/CD Integration

### GitHub Actions Test Workflow

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements-dev.txt

      - name: Run unit tests
        run: pytest tests/unit -m unit --cov-fail-under=85

      - name: Run integration tests
        run: pytest tests/integration -m integration --cov-fail-under=75

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

### Test Gates

1. **Pre-commit**: Fast unit tests only
2. **Pull Request**: Full test suite including integration
3. **Main branch**: All tests + performance benchmarks
4. **Release**: All tests + E2E + load tests

## Implementation Roadmap

### Phase 1: Foundation (Week 1-2)
- [ ] Set up pytest configuration
- [ ] Create conftest.py with basic fixtures
- [ ] Implement TestContainers setup
- [ ] Create first unit tests for auth service
- [ ] Create first integration tests for companies API

### Phase 2: Core Coverage (Week 3-4)
- [ ] Unit tests for all service modules (80%+ coverage)
- [ ] Integration tests for all API endpoints (75%+ coverage)
- [ ] Database model tests
- [ ] Authentication flow tests

### Phase 3: Advanced Testing (Week 5-6)
- [ ] End-to-end workflow tests
- [ ] Performance benchmarks
- [ ] Load testing scenarios
- [ ] Security testing

### Phase 4: CI/CD Integration (Week 7)
- [ ] GitHub Actions workflows
- [ ] Coverage reporting
- [ ] Test result dashboards
- [ ] Automated test execution

## Success Metrics

### Quantitative
- Overall test coverage: 80%+
- Critical module coverage: 90%+
- Test execution time: < 5 minutes for full suite
- Test success rate: 99%+
- Zero flaky tests

### Qualitative
- Tests serve as documentation
- Easy to write new tests
- Fast feedback loop
- Confidence in refactoring
- Clear test failures

## Maintenance Guidelines

### Test Maintenance
- Update tests when functionality changes
- Remove obsolete tests
- Refactor duplicated test code
- Keep test data fixtures up-to-date

### Coverage Monitoring
- Weekly coverage reports
- Coverage trends over time
- Coverage requirements in CI/CD
- Team coverage goals

### Test Performance
- Monitor test execution time
- Optimize slow tests
- Parallelize where possible
- Use caching appropriately

## Conclusion

This test architecture provides a comprehensive foundation for achieving 80%+ test coverage while maintaining test quality, speed, and maintainability. The strategy balances thorough testing with practical development velocity, ensuring the Corporate Intelligence Platform remains reliable and maintainable as it grows.
