# API Testing Guide

## Overview

This guide covers comprehensive API endpoint testing using FastAPI's TestClient. The test suite validates request/response handling, authentication, validation, error cases, and edge cases for all API endpoints.

## Test Structure

```
tests/api/
├── __init__.py
├── conftest.py              # Shared fixtures and test utilities
├── test_health.py           # Health check endpoint tests
├── test_companies.py        # Company CRUD endpoint tests
├── test_filings.py          # SEC filing endpoint tests
├── test_auth.py             # Authentication endpoint tests
├── test_metrics.py          # Financial metrics endpoint tests
└── API_TESTING_GUIDE.md     # This documentation
```

## Running API Tests

### Run All API Tests
```bash
# Run all API endpoint tests
pytest tests/api/ -v

# Run with coverage
pytest tests/api/ --cov=src/api --cov-report=html

# Run specific test file
pytest tests/api/test_companies.py -v

# Run specific test class
pytest tests/api/test_companies.py::TestCompanyListEndpoint -v

# Run specific test
pytest tests/api/test_companies.py::TestCompanyListEndpoint::test_list_companies_success -v
```

### Run Tests in Parallel
```bash
# Install pytest-xdist
pip install pytest-xdist

# Run tests in parallel
pytest tests/api/ -n auto
```

## Test Categories

### 1. Health Check Tests (`test_health.py`)

Tests for application health monitoring endpoints.

**Endpoints Tested:**
- `GET /health` - Basic health check
- `GET /health/database` - Database health check
- `GET /health/cache` - Redis cache health check
- `GET /metrics` - Prometheus metrics

**Example Test:**
```python
def test_basic_health_check(api_client: TestClient):
    """Test basic health check endpoint returns healthy status."""
    response = api_client.get("/health")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["status"] == "healthy"
    assert "version" in data
    assert "environment" in data
```

### 2. Company API Tests (`test_companies.py`)

Tests for company CRUD operations and related endpoints.

**Endpoints Tested:**
- `GET /api/v1/companies/` - List companies with filtering/pagination
- `GET /api/v1/companies/{id}` - Get specific company
- `GET /api/v1/companies/{id}/metrics` - Get company metrics
- `GET /api/v1/companies/watchlist` - Get watchlist (requires auth)
- `POST /api/v1/companies/` - Create company (requires auth)
- `PUT /api/v1/companies/{id}` - Update company (requires auth)
- `DELETE /api/v1/companies/{id}` - Delete company (requires auth)

**Test Classes:**
- `TestCompanyListEndpoint` - List/filter/pagination tests
- `TestGetCompanyEndpoint` - Get specific company tests
- `TestGetCompanyMetricsEndpoint` - Company metrics tests
- `TestWatchlistEndpoint` - Watchlist authentication tests
- `TestCreateCompanyEndpoint` - Company creation tests
- `TestUpdateCompanyEndpoint` - Company update tests
- `TestDeleteCompanyEndpoint` - Company deletion tests

**Example Test:**
```python
def test_list_companies_filter_by_category(
    api_client: TestClient, sample_companies: list[Company]
):
    """Test filtering companies by category."""
    response = api_client.get("/api/v1/companies/?category=higher_education")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert isinstance(data, list)
    assert all(c["category"] == "higher_education" for c in data)
```

### 3. SEC Filing Tests (`test_filings.py`)

Tests for SEC filing endpoints.

**Endpoints Tested:**
- `GET /api/v1/filings/` - List filings with filtering
- `GET /api/v1/filings/{id}` - Get specific filing

**Test Classes:**
- `TestListFilingsEndpoint` - List/filter/pagination tests
- `TestGetFilingEndpoint` - Get specific filing tests
- `TestFilingsByCompany` - Company-filing relationship tests
- `TestFilingTypes` - Filing type filtering tests
- `TestFilingProcessingStatus` - Processing status tests
- `TestFilingCaching` - Caching behavior tests

**Example Test:**
```python
def test_list_filings_sorted_by_date(
    api_client: TestClient, sample_filings: list[SECFiling]
):
    """Test filings are sorted by filing date descending."""
    response = api_client.get("/api/v1/filings/")

    data = response.json()

    if len(data) > 1:
        dates = [datetime.fromisoformat(f["filing_date"].replace('Z', '+00:00')) for f in data]
        assert dates == sorted(dates, reverse=True)
```

### 4. Authentication Tests (`test_auth.py`)

Tests for authentication and authorization endpoints.

**Endpoints Tested:**
- `POST /auth/register` - User registration
- `POST /auth/login` - User login
- `POST /auth/refresh` - Token refresh
- `POST /auth/logout` - User logout
- `GET /auth/me` - Get current user
- `PUT /auth/me` - Update current user
- `POST /auth/api-keys` - Create API key
- `GET /auth/api-keys` - List API keys
- `DELETE /auth/api-keys/{id}` - Revoke API key
- `GET /auth/users` - List users (admin only)
- `PUT /auth/users/{id}/role` - Update user role (admin only)
- `PUT /auth/users/{id}/status` - Update user status (admin only)

**Test Classes:**
- `TestRegisterEndpoint` - Registration tests
- `TestLoginEndpoint` - Login tests
- `TestRefreshTokenEndpoint` - Token refresh tests
- `TestLogoutEndpoint` - Logout tests
- `TestCurrentUserEndpoint` - Current user tests
- `TestUpdateCurrentUserEndpoint` - User update tests
- `TestAPIKeyEndpoints` - API key management tests
- `TestAdminEndpoints` - Admin-only endpoint tests
- `TestAuthenticationErrors` - Error handling tests

**Example Test:**
```python
def test_login_success(api_client: TestClient, test_user: User):
    """Test successful login with email."""
    login_data = {
        "identifier": test_user.email,
        "password": "Test123!@#"
    }

    response = api_client.post("/auth/login", json=login_data)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
```

### 5. Financial Metrics Tests (`test_metrics.py`)

Tests for financial metrics endpoints.

**Endpoints Tested:**
- `GET /api/v1/metrics/` - List metrics with filtering

**Test Classes:**
- `TestListMetricsEndpoint` - List/filter/pagination tests
- `TestMetricTypes` - Metric type filtering tests
- `TestPeriodTypes` - Period type filtering tests
- `TestMetricsByCompany` - Company-metric relationship tests
- `TestMetricValueTypes` - Value type and unit tests
- `TestMetricCombinations` - Combined filter tests
- `TestMetricsCaching` - Caching behavior tests
- `TestMetricsEdgeCases` - Edge case tests

**Example Test:**
```python
def test_list_metrics_filter_by_type(
    api_client: TestClient, sample_metrics: list[FinancialMetric]
):
    """Test filtering metrics by metric type."""
    response = api_client.get("/api/v1/metrics/?metric_type=revenue")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert isinstance(data, list)
    assert all(m["metric_type"] == "revenue" for m in data)
```

## Test Fixtures

### Core Fixtures (`conftest.py`)

#### API Client
```python
@pytest.fixture
def api_client(client: TestClient) -> TestClient:
    """FastAPI test client for API endpoints."""
    return client
```

#### Sample Data Fixtures
```python
@pytest.fixture
def sample_company(db_session: Session) -> Company:
    """Create a sample company for testing."""
    # Returns Duolingo company fixture

@pytest.fixture
def sample_companies(db_session: Session) -> list[Company]:
    """Create multiple sample companies for pagination/filtering."""
    # Returns list of EdTech companies

@pytest.fixture
def sample_filing(db_session: Session, sample_company: Company) -> SECFiling:
    """Create a sample SEC filing."""
    # Returns 10-K filing fixture

@pytest.fixture
def sample_metrics(db_session: Session, sample_company: Company) -> list[FinancialMetric]:
    """Create sample financial metrics."""
    # Returns revenue, growth, and engagement metrics
```

#### Authentication Fixtures
```python
@pytest.fixture
def unauthorized_headers() -> Dict[str, str]:
    """Headers without authentication."""
    return {}

@pytest.fixture
def invalid_token_headers() -> Dict[str, str]:
    """Headers with invalid token."""
    return {"Authorization": "Bearer invalid.token.here"}

@pytest.fixture
def expired_token_headers(auth_service) -> Dict[str, str]:
    """Headers with expired token."""
    # Returns headers with expired JWT
```

## Authentication Testing Patterns

### 1. Testing Protected Endpoints

```python
def test_endpoint_requires_auth(api_client: TestClient, unauthorized_headers):
    """Test endpoint requires authentication."""
    response = api_client.get("/api/v1/companies/watchlist", headers=unauthorized_headers)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
```

### 2. Testing with Valid Auth

```python
def test_endpoint_with_auth(api_client: TestClient, auth_headers):
    """Test endpoint with valid authentication."""
    response = api_client.get("/api/v1/companies/watchlist", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
```

### 3. Testing Role-Based Access

```python
def test_admin_only_endpoint(api_client: TestClient, auth_headers, admin_headers):
    """Test admin-only endpoint access."""
    # Regular user - should fail
    response = api_client.get("/auth/users", headers=auth_headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN

    # Admin user - should succeed
    response = api_client.get("/auth/users", headers=admin_headers)
    assert response.status_code == status.HTTP_200_OK
```

## TestClient Usage

### Making Requests

```python
# GET request
response = api_client.get("/api/v1/companies/")

# GET with query parameters
response = api_client.get("/api/v1/companies/?category=k12&limit=10")

# GET with path parameters
response = api_client.get(f"/api/v1/companies/{company_id}")

# POST request with JSON body
response = api_client.post("/auth/login", json={"email": "test@example.com", "password": "pass"})

# PUT request with authentication
response = api_client.put(f"/api/v1/companies/{id}", json=data, headers=auth_headers)

# DELETE request
response = api_client.delete(f"/api/v1/companies/{id}", headers=auth_headers)
```

### Response Validation

```python
# Status code
assert response.status_code == status.HTTP_200_OK

# JSON response
data = response.json()
assert isinstance(data, list)
assert len(data) > 0

# Response headers
assert "content-type" in response.headers
assert "application/json" in response.headers["content-type"]

# Response schema
assert "id" in data[0]
assert "name" in data[0]
```

## Error Testing

### 1. Validation Errors (422)

```python
def test_invalid_input_returns_422(api_client: TestClient):
    """Test invalid input returns validation error."""
    response = api_client.get("/api/v1/companies/?limit=1000")  # Exceeds max
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
```

### 2. Not Found Errors (404)

```python
def test_nonexistent_resource_returns_404(api_client: TestClient):
    """Test accessing non-existent resource."""
    response = api_client.get(f"/api/v1/companies/{uuid4()}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
```

### 3. Authentication Errors (401)

```python
def test_unauthorized_returns_401(api_client: TestClient):
    """Test unauthorized access."""
    response = api_client.get("/api/v1/companies/watchlist")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
```

### 4. Authorization Errors (403)

```python
def test_insufficient_permissions_returns_403(api_client: TestClient, auth_headers):
    """Test insufficient permissions."""
    response = api_client.get("/auth/users", headers=auth_headers)  # Viewer trying admin endpoint
    assert response.status_code == status.HTTP_403_FORBIDDEN
```

### 5. Conflict Errors (409)

```python
def test_duplicate_resource_returns_409(api_client: TestClient, auth_headers, sample_company):
    """Test creating duplicate resource."""
    data = {"ticker": sample_company.ticker, "name": "Duplicate"}
    response = api_client.post("/api/v1/companies/", json=data, headers=auth_headers)
    assert response.status_code == status.HTTP_409_CONFLICT
```

## Pagination Testing

```python
def test_pagination_with_limit_and_offset(api_client: TestClient, sample_companies):
    """Test pagination parameters."""
    # First page
    response1 = api_client.get("/api/v1/companies/?limit=2&offset=0")
    data1 = response1.json()
    assert len(data1) <= 2

    # Second page
    response2 = api_client.get("/api/v1/companies/?limit=2&offset=2")
    data2 = response2.json()

    # Ensure different results
    if len(data1) > 0 and len(data2) > 0:
        assert data1[0]["id"] != data2[0]["id"]
```

## Filtering Testing

```python
def test_multiple_filters_combined(api_client: TestClient):
    """Test combining multiple filters."""
    response = api_client.get(
        "/api/v1/companies/?category=k12&sector=Technology&limit=10"
    )

    data = response.json()
    assert all(c["category"] == "k12" for c in data)
    assert all(c["sector"] == "Technology" for c in data)
```

## Caching Testing

```python
def test_endpoint_caching_behavior(api_client: TestClient, sample_company):
    """Test endpoint uses caching correctly."""
    # First request
    response1 = api_client.get(f"/api/v1/companies/{sample_company.id}")
    data1 = response1.json()

    # Second request (may be cached)
    response2 = api_client.get(f"/api/v1/companies/{sample_company.id}")
    data2 = response2.json()

    # Data should be consistent
    assert data1 == data2
```

## Edge Cases

### Null/Empty Values

```python
def test_optional_fields_can_be_null(api_client: TestClient, db_session):
    """Test handling of null optional fields."""
    company = Company(ticker="TEST", name="Test", cik=None, sector=None)
    db_session.add(company)
    db_session.commit()

    response = api_client.get(f"/api/v1/companies/{company.id}")
    data = response.json()

    assert data["cik"] is None
    assert data["sector"] is None
```

### Large Values

```python
def test_large_value_handling(api_client: TestClient, sample_company, db_session):
    """Test handling of very large numeric values."""
    metric = FinancialMetric(
        company_id=sample_company.id,
        metric_type="market_cap",
        value=1000000000000.0,  # 1 trillion
    )
    db_session.add(metric)
    db_session.commit()

    response = api_client.get("/api/v1/metrics/?metric_type=market_cap")
    data = response.json()

    assert any(m["value"] >= 1000000000000.0 for m in data)
```

### Zero/Negative Values

```python
def test_negative_values_for_losses(api_client: TestClient, sample_company, db_session):
    """Test handling of negative values (losses)."""
    metric = FinancialMetric(
        company_id=sample_company.id,
        metric_type="net_income",
        value=-5000000.0,
    )
    db_session.add(metric)
    db_session.commit()

    response = api_client.get("/api/v1/metrics/?metric_type=net_income")
    data = response.json()

    assert any(m["value"] < 0 for m in data)
```

## Best Practices

### 1. Test Isolation
- Each test should be independent
- Use fixtures to create fresh data
- Clean up after tests (handled by conftest)

### 2. Descriptive Test Names
```python
# Good
def test_list_companies_filter_by_category_returns_filtered_results()

# Bad
def test_companies()
```

### 3. Arrange-Act-Assert Pattern
```python
def test_create_company_success(api_client, auth_headers):
    # Arrange
    company_data = {"ticker": "TEST", "name": "Test Company"}

    # Act
    response = api_client.post("/api/v1/companies/", json=company_data, headers=auth_headers)

    # Assert
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["ticker"] == "TEST"
```

### 4. Test Both Success and Failure Cases
```python
class TestCreateCompany:
    def test_create_success(self, api_client, auth_headers):
        """Test successful company creation."""
        # Success case

    def test_create_duplicate_fails(self, api_client, auth_headers, sample_company):
        """Test creating duplicate company fails."""
        # Failure case

    def test_create_requires_auth(self, api_client):
        """Test creating company requires authentication."""
        # Auth failure case
```

### 5. Use Parametrize for Similar Tests
```python
@pytest.mark.parametrize("filing_type", ["10-K", "10-Q", "8-K"])
def test_filter_by_filing_type(api_client, filing_type):
    """Test filtering by different filing types."""
    response = api_client.get(f"/api/v1/filings/?filing_type={filing_type}")
    data = response.json()
    assert all(f["filing_type"] == filing_type for f in data)
```

## Coverage Goals

- **Statements**: >80%
- **Branches**: >75%
- **Functions**: >80%
- **Lines**: >80%

### Check Coverage
```bash
pytest tests/api/ --cov=src/api --cov-report=term-missing
```

## Continuous Integration

### GitHub Actions Workflow
```yaml
- name: Run API Tests
  run: |
    pytest tests/api/ -v --cov=src/api --cov-report=xml

- name: Upload Coverage
  uses: codecov/codecov-action@v3
  with:
    files: ./coverage.xml
    flags: api-tests
```

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Ensure test database is properly configured
   - Check `conftest.py` database fixtures

2. **Authentication Failures**
   - Verify JWT secret key is set
   - Check token expiration settings

3. **Fixture Not Found**
   - Ensure fixture is defined in `conftest.py`
   - Check fixture scope (function vs session)

4. **Async Test Issues**
   - Use `@pytest.mark.asyncio` for async tests
   - Install `pytest-asyncio`

### Debug Tips

```bash
# Run with verbose output
pytest tests/api/test_companies.py -vv

# Run with print statements
pytest tests/api/test_companies.py -s

# Run specific test with debugging
pytest tests/api/test_companies.py::test_name -vv --pdb

# Show test durations
pytest tests/api/ --durations=10
```

## Summary

This test suite provides comprehensive coverage of all API endpoints with:

- **80+ test cases** across 5 test files
- **Request/response validation**
- **Authentication/authorization testing**
- **Error handling validation**
- **Pagination and filtering tests**
- **Edge case coverage**
- **Caching behavior tests**

All tests use FastAPI's TestClient for synchronous, fast API testing without requiring a running server.
