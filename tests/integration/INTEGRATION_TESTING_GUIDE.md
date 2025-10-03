# SEC Pipeline Integration Testing Guide

## Overview

This guide covers integration testing for the SEC ingestion pipeline, including test database setup, mock API patterns, and troubleshooting tips.

## Test Database Setup

### Prerequisites

- PostgreSQL 14+ with TimescaleDB extension
- pgvector extension
- Python 3.11+
- Test database credentials configured in `.env`

### Database Configuration

The integration tests use a dedicated test database that is automatically created and destroyed:

```python
# Test database name
TEST_DB_NAME = "corporate_intel_test"

# Connection URL
TEST_DB_URL = "postgresql+asyncpg://user:password@localhost:5432/corporate_intel_test"
```

### Automatic Setup

The test suite automatically:

1. **Creates test database** - Fresh database for each test session
2. **Installs extensions** - TimescaleDB and pgvector
3. **Creates tables** - All application tables via SQLAlchemy
4. **Converts to hypertable** - `financial_metrics` table for time-series
5. **Cleans up** - Drops database after tests complete

### Manual Setup (Optional)

If you need to manually create the test database:

```sql
-- Create test database
CREATE DATABASE corporate_intel_test;

-- Connect to test database
\c corporate_intel_test

-- Install extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Convert financial_metrics to hypertable
SELECT create_hypertable(
    'financial_metrics',
    'metric_date',
    if_not_exists => TRUE
);
```

## Running Integration Tests

### Run All Integration Tests

```bash
# Run all integration tests
pytest tests/integration/test_sec_pipeline_integration.py -v

# Run with coverage
pytest tests/integration/test_sec_pipeline_integration.py --cov=src.pipeline --cov-report=html

# Run specific test class
pytest tests/integration/test_sec_pipeline_integration.py::TestEndToEndWorkflow -v
```

### Run Specific Test Categories

```bash
# End-to-end workflow tests
pytest tests/integration/test_sec_pipeline_integration.py::TestEndToEndWorkflow

# Duplicate handling tests
pytest tests/integration/test_sec_pipeline_integration.py::TestDuplicateFilingHandling

# Error recovery tests
pytest tests/integration/test_sec_pipeline_integration.py::TestErrorRecoveryRollback

# Concurrent execution tests
pytest tests/integration/test_sec_pipeline_integration.py::TestConcurrentExecution

# TimescaleDB feature tests
pytest tests/integration/test_sec_pipeline_integration.py::TestTimescaleDBFeatures

# Performance tests
pytest tests/integration/test_sec_pipeline_integration.py::TestPerformance
```

## Mock API Patterns

### SEC EDGAR API Mocking

The tests use a comprehensive mock HTTP client that simulates SEC EDGAR API responses:

```python
# Mock company info response
company_info_response = {
    "cik": "1835631",
    "name": "Duolingo, Inc.",
    "sic": "7372",
    "sicDescription": "Services-Prepackaged Software",
    "filings": {
        "recent": {
            "form": ["10-K", "10-Q"],
            "filingDate": ["2024-03-15", "2023-11-03"],
            "accessionNumber": ["0001835631-24-000012", "0001835631-23-000024"]
        }
    }
}
```

### Using Mock Client

```python
@pytest.fixture
def mock_http_client(mock_sec_api_responses):
    """Mock HTTP client for SEC API requests."""

    class MockAsyncClient:
        async def get(self, url, **kwargs):
            if "submissions/CIK" in url:
                return MockResponse(json_data=mock_sec_api_responses["company_info"])
            elif "10-K" in url:
                return MockResponse(text_data=mock_sec_api_responses["filing_10k"])
            return MockResponse(status_code=404)

    return MockAsyncClient

# Apply to tests
@pytest.mark.asyncio
async def test_with_mock_api(patch_httpx_client):
    # Test code using mocked SEC API
    pass
```

### Custom Mock Responses

Create custom mock responses for specific test scenarios:

```python
@pytest.fixture
def custom_mock_response():
    return {
        "cik": "9999999",
        "name": "Test Company",
        "filings": {
            "recent": {
                "form": ["8-K"],
                "filingDate": ["2024-01-15"],
                "accessionNumber": ["0009999999-24-000001"]
            }
        }
    }
```

## Test Fixtures

### Database Fixtures

```python
@pytest_asyncio.fixture
async def db_session(setup_test_database) -> AsyncSession:
    """Provides clean database session for each test."""
    # Automatic rollback after test

@pytest_asyncio.fixture
async def test_company(db_session) -> Company:
    """Creates test company in database."""

@pytest_asyncio.fixture
async def test_filing(db_session, test_company) -> SECFiling:
    """Creates test SEC filing in database."""
```

### Data Fixtures

```python
@pytest.fixture
def sample_company_data():
    """Sample company data for testing."""

@pytest.fixture
def sample_sec_filing_data():
    """Sample SEC filing data with realistic content."""

@pytest.fixture
def mock_sec_api_responses():
    """Complete mock SEC API response set."""
```

## Test Scenarios

### 1. End-to-End Workflow

Tests complete ingestion flow from API to database:

```python
async def test_complete_ingestion_flow_new_company():
    """
    1. Fetch company info from SEC API
    2. Fetch filings list
    3. Download filing content
    4. Validate data
    5. Store in database
    6. Verify all steps completed successfully
    """
```

### 2. Duplicate Detection

Tests duplicate filing handling:

```python
async def test_duplicate_filing_skipped():
    """
    1. Store initial filing
    2. Attempt to store duplicate
    3. Verify duplicate detected
    4. Verify only one filing in database
    """
```

### 3. Error Recovery

Tests transaction rollback on errors:

```python
async def test_validation_failure_rollback():
    """
    1. Attempt to store invalid filing
    2. Validation fails
    3. Transaction rolls back
    4. Verify no partial data stored
    """
```

### 4. Concurrent Execution

Tests parallel processing:

```python
async def test_concurrent_filing_downloads():
    """
    1. Create multiple download tasks
    2. Execute concurrently with asyncio.gather
    3. Verify all complete successfully
    4. Check rate limiting respected
    """
```

### 5. TimescaleDB Features

Tests time-series capabilities:

```python
async def test_time_bucket_aggregation():
    """
    1. Insert time-series metrics
    2. Use time_bucket for aggregation
    3. Verify weekly/monthly rollups
    4. Test continuous aggregates
    """
```

## Troubleshooting

### Database Connection Errors

**Issue**: `sqlalchemy.exc.OperationalError: connection refused`

**Solution**:
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Verify connection settings
psql -h localhost -U intel_user -d postgres

# Check .env file has correct credentials
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=intel_user
POSTGRES_PASSWORD=your_password
```

### TimescaleDB Extension Missing

**Issue**: `extension "timescaledb" does not exist`

**Solution**:
```bash
# Install TimescaleDB
sudo apt install timescaledb-2-postgresql-14

# Add to postgresql.conf
shared_preload_libraries = 'timescaledb'

# Restart PostgreSQL
sudo systemctl restart postgresql

# Create extension in database
psql -U intel_user -d corporate_intel_test -c "CREATE EXTENSION timescaledb;"
```

### pgvector Extension Missing

**Issue**: `extension "vector" does not exist`

**Solution**:
```bash
# Install pgvector
cd /tmp
git clone https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install

# Create extension
psql -U intel_user -d corporate_intel_test -c "CREATE EXTENSION vector;"
```

### Mock API Not Working

**Issue**: Tests fail with real API calls instead of mocks

**Solution**:
```python
# Ensure fixture is applied
@pytest.mark.asyncio
async def test_my_function(patch_httpx_client):  # <-- Add fixture
    # Test code
    pass

# Or use with statement
async def test_with_mock():
    with patch("httpx.AsyncClient") as mock:
        # Configure mock
        # Test code
```

### Async Test Errors

**Issue**: `RuntimeError: no running event loop`

**Solution**:
```python
# Use pytest-asyncio markers
import pytest

@pytest.mark.asyncio
async def test_async_function():
    # Test code

# Or configure in pytest.ini
[pytest]
asyncio_mode = auto
```

### Test Database Cleanup

**Issue**: Test database not cleaned up

**Solution**:
```bash
# Manual cleanup
psql -U postgres -c "DROP DATABASE IF EXISTS corporate_intel_test;"

# Or let fixtures handle it
# The setup_test_database fixture automatically cleans up
```

### Slow Tests

**Issue**: Tests take too long to run

**Solution**:
```python
# Run tests in parallel
pytest tests/integration -n auto

# Skip slow tests in development
pytest tests/integration -m "not slow"

# Use smaller test datasets
@pytest.fixture
def sample_data_small():
    return generate_filings(count=10)  # Instead of 100
```

### Transaction Isolation Issues

**Issue**: Test data bleeding between tests

**Solution**:
```python
# Ensure rollback in fixture
@pytest_asyncio.fixture
async def db_session(setup_test_database):
    async with session_factory() as session:
        yield session
        await session.rollback()  # <-- Important!

# Or use separate sessions
@pytest.fixture(scope="function")  # Not "session"
async def db_session():
    # Creates new session per test
```

## Best Practices

### 1. Test Isolation

- Each test should be independent
- Use fixtures for setup/teardown
- Always rollback transactions
- Don't rely on test execution order

### 2. Mock External APIs

- Never call real APIs in integration tests
- Use comprehensive mock responses
- Cover error scenarios (404, 500, timeouts)
- Test rate limiting with mocks

### 3. Test Data Management

- Use factories for test data generation
- Keep test data realistic but minimal
- Clean up after each test
- Use separate test database

### 4. Performance Considerations

- Use `pytest-xdist` for parallel execution
- Mock slow operations (network, file I/O)
- Set appropriate timeouts
- Profile slow tests

### 5. Error Testing

- Test happy path AND error paths
- Verify rollback behavior
- Check error messages
- Test recovery mechanisms

## Integration Test Checklist

- [ ] Database setup automated
- [ ] All external APIs mocked
- [ ] Test data cleanup working
- [ ] Concurrent execution tested
- [ ] Error scenarios covered
- [ ] Performance benchmarks passing
- [ ] Documentation updated
- [ ] CI/CD integration configured

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Integration Tests

on: [push, pull_request]

jobs:
  integration-tests:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: timescale/timescaledb:latest-pg14
        env:
          POSTGRES_PASSWORD: test_password
          POSTGRES_USER: test_user
          POSTGRES_DB: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest-asyncio pytest-cov

      - name: Install pgvector
        run: |
          sudo apt-get install postgresql-server-dev-14
          git clone https://github.com/pgvector/pgvector.git
          cd pgvector && make && sudo make install

      - name: Run integration tests
        env:
          POSTGRES_HOST: localhost
          POSTGRES_PORT: 5432
          POSTGRES_USER: test_user
          POSTGRES_PASSWORD: test_password
        run: |
          pytest tests/integration -v --cov=src --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Additional Resources

- [pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
- [SQLAlchemy Async Documentation](https://docs.sqlalchemy.org/en/14/orm/extensions/asyncio.html)
- [TimescaleDB Testing Guide](https://docs.timescale.com/timescaledb/latest/how-to-guides/testing/)
- [Great Expectations Testing](https://docs.greatexpectations.io/docs/guides/testing/)

## Support

For issues or questions:

1. Check this guide first
2. Review test fixtures in `conftest.py`
3. Examine similar working tests
4. Check logs and error messages
5. Open issue with reproduction steps
