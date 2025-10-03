# Test Execution Guide

**Corporate Intelligence Platform - Testing Infrastructure**

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Test Environment Setup](#test-environment-setup)
3. [Running Tests](#running-tests)
4. [Coverage Analysis](#coverage-analysis)
5. [Test Categories](#test-categories)
6. [CI/CD Integration](#cicd-integration)
7. [Troubleshooting](#troubleshooting)
8. [Best Practices](#best-practices)

---

## Quick Start

### Prerequisites

- Python 3.11+
- pip or Poetry package manager
- SQLite (for test database)
- Redis (optional - mocked in tests)

### Installation

```bash
# Clone repository
cd corporate_intel

# Install dependencies (choose one method)

# Method 1: pip
pip install -r requirements.txt -r requirements-dev.txt

# Method 2: Poetry
poetry install

# Method 3: setuptools
pip install -e .
```

### Run All Tests

```bash
# Using pytest directly
pytest

# With verbose output
pytest -v

# With coverage
pytest --cov=src --cov-report=term-missing
```

---

## Test Environment Setup

### 1. Virtual Environment (Recommended)

```bash
# Create virtual environment
python -m venv venv

# Activate (Linux/Mac)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt -r requirements-dev.txt
```

### 2. Environment Variables

Create a `.env.test` file (optional - tests use defaults):

```bash
# Test Database
DATABASE_URL=sqlite:///:memory:

# Redis (mocked in tests)
REDIS_URL=redis://localhost:6379/15

# Test Settings
ENVIRONMENT=testing
DEBUG=True
CACHE_ENABLED=False
RATE_LIMIT_ENABLED=False
```

### 3. Database Setup

Tests use SQLite in-memory database by default (no setup required).

For PostgreSQL testing (advanced):

```bash
# Install PostgreSQL driver
pip install psycopg2-binary

# Set test database URL
export TEST_DATABASE_URL="postgresql://test_user:test_pass@localhost:5432/test_db"
```

---

## Running Tests

### Basic Commands

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with extra verbosity (show all output)
pytest -vv

# Run specific test file
pytest tests/unit/test_sec_pipeline.py

# Run specific test function
pytest tests/unit/test_auth.py::test_user_creation

# Run specific test class
pytest tests/integration/test_auth_api.py::TestUserRegistration
```

### Test Selection

```bash
# Run only unit tests
pytest tests/unit/

# Run only integration tests
pytest tests/integration/

# Run only validation tests
pytest tests/validation/

# Run tests matching pattern
pytest -k "auth"
pytest -k "test_store_filing"
pytest -k "not slow"
```

### Markers

```bash
# Run tests with specific marker
pytest -m "critical"
pytest -m "slow"
pytest -m "integration"

# Run tests excluding marker
pytest -m "not slow"

# List all markers
pytest --markers
```

### Parallel Execution

```bash
# Install pytest-xdist
pip install pytest-xdist

# Run tests in parallel (4 workers)
pytest -n 4

# Run tests in parallel (auto-detect CPUs)
pytest -n auto
```

---

## Coverage Analysis

### Generate Coverage Reports

```bash
# Terminal coverage report
pytest --cov=src

# Terminal with missing lines
pytest --cov=src --cov-report=term-missing

# HTML coverage report
pytest --cov=src --cov-report=html

# XML coverage report (for CI/CD)
pytest --cov=src --cov-report=xml

# Multiple report formats
pytest --cov=src --cov-report=html --cov-report=term --cov-report=xml
```

### View HTML Coverage Report

```bash
# Generate HTML report
pytest --cov=src --cov-report=html

# Open in browser (Linux/Mac)
open htmlcov/index.html

# Open in browser (Windows)
start htmlcov/index.html
```

### Coverage Configuration

Create `.coveragerc` file:

```ini
[run]
source = src
omit =
    */tests/*
    */migrations/*
    */__pycache__/*
    */venv/*

[report]
precision = 2
show_missing = True
skip_covered = False

[html]
directory = htmlcov
```

### Coverage Thresholds

```bash
# Fail if coverage below 80%
pytest --cov=src --cov-fail-under=80

# Check coverage by module
pytest --cov=src.auth --cov-report=term
pytest --cov=src.pipeline --cov-report=term
```

---

## Test Categories

### 1. Unit Tests (`tests/unit/`)

**Purpose:** Test individual functions and classes in isolation

```bash
# Run all unit tests
pytest tests/unit/

# Run specific unit test modules
pytest tests/unit/test_sec_pipeline.py
pytest tests/unit/test_sec_validation.py
pytest tests/unit/test_auth.py
pytest tests/unit/test_analysis_service.py
pytest tests/unit/test_data_processing.py
pytest tests/unit/test_data_quality.py
pytest tests/unit/test_integrations.py
```

**Characteristics:**
- Fast execution (< 5 seconds total)
- Heavy use of mocks and fixtures
- No external dependencies
- Tests single functions/methods

### 2. Integration Tests (`tests/integration/`)

**Purpose:** Test API endpoints and component interactions

```bash
# Run all integration tests
pytest tests/integration/

# Run specific integration test modules
pytest tests/integration/test_auth_api.py
pytest tests/integration/test_company_api.py
pytest tests/integration/test_document_api.py
pytest tests/integration/test_metrics_api.py
pytest tests/integration/test_analysis_api.py
```

**Characteristics:**
- Moderate execution time (10-30 seconds)
- Uses TestClient for API testing
- Tests complete request/response cycles
- Database interactions included

### 3. Validation Tests (`tests/validation/`)

**Purpose:** Test data validation and business rules

```bash
# Run all validation tests
pytest tests/validation/

# Run SEC filing validation tests
pytest tests/validation/test_sec_filing_expectations.py
```

**Characteristics:**
- Tests business logic and rules
- Data quality validation
- Regulatory compliance checks
- Expected data format validation

---

## CI/CD Integration

### GitHub Actions

Create `.github/workflows/test.yml`:

```yaml
name: Test Suite

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test:
    runs-on: ubuntu-latest

    strategy:
      matrix:
        python-version: [3.11, 3.12]

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install dependencies
      run: |
        pip install -r requirements.txt -r requirements-dev.txt

    - name: Run tests with coverage
      run: |
        pytest --cov=src --cov-report=xml --cov-report=term

    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        fail_ci_if_error: true
```

### GitLab CI

Create `.gitlab-ci.yml`:

```yaml
test:
  image: python:3.11

  before_script:
    - pip install -r requirements.txt -r requirements-dev.txt

  script:
    - pytest --cov=src --cov-report=xml --cov-report=term

  coverage: '/TOTAL.*\s+(\d+%)$/'

  artifacts:
    reports:
      coverage_report:
        coverage_format: cobertura
        path: coverage.xml
```

### Jenkins

```groovy
pipeline {
    agent any

    stages {
        stage('Install Dependencies') {
            steps {
                sh 'pip install -r requirements.txt -r requirements-dev.txt'
            }
        }

        stage('Run Tests') {
            steps {
                sh 'pytest --cov=src --cov-report=xml --cov-report=html'
            }
        }

        stage('Coverage Report') {
            steps {
                publishHTML([
                    reportDir: 'htmlcov',
                    reportFiles: 'index.html',
                    reportName: 'Coverage Report'
                ])
            }
        }
    }
}
```

---

## Troubleshooting

### Common Issues and Solutions

#### 1. Import Errors

**Problem:** `ModuleNotFoundError: No module named 'src'`

**Solution:**
```bash
# Option 1: Install package in editable mode
pip install -e .

# Option 2: Add to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Option 3: Run from project root
cd /path/to/corporate_intel
pytest
```

#### 2. Database Errors

**Problem:** `sqlalchemy.exc.OperationalError: unable to open database file`

**Solution:**
```bash
# Tests use in-memory SQLite by default
# Ensure conftest.py is using TEST_DATABASE_URL

# Check conftest.py has:
TEST_DATABASE_URL = "sqlite:///:memory:"
```

#### 3. Async/Await Errors

**Problem:** `RuntimeWarning: coroutine was never awaited`

**Solution:**
```python
# Ensure async tests use proper decorator
import pytest

@pytest.mark.asyncio
async def test_async_function():
    result = await async_operation()
    assert result is not None
```

#### 4. Fixture Not Found

**Problem:** `fixture 'db_session' not found`

**Solution:**
```bash
# Ensure conftest.py is in correct location
ls tests/conftest.py

# Check fixture is defined and imported
pytest --fixtures | grep db_session
```

#### 5. Missing Dependencies

**Problem:** `ModuleNotFoundError: No module named 'pytest'`

**Solution:**
```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov pytest-mock

# Or install all dev dependencies
pip install -r requirements-dev.txt
```

#### 6. Redis Connection Errors

**Problem:** `redis.exceptions.ConnectionError`

**Solution:**
```python
# Tests mock Redis by default
# If real Redis needed, ensure it's running:
redis-server

# Or disable Redis in test settings
settings.CACHE_ENABLED = False  # Set in conftest.py
```

#### 7. Slow Tests

**Problem:** Tests taking too long to run

**Solution:**
```bash
# Run tests in parallel
pip install pytest-xdist
pytest -n auto

# Skip slow tests
pytest -m "not slow"

# Profile tests to find bottlenecks
pytest --durations=10
```

#### 8. Coverage Report Not Generated

**Problem:** Coverage report missing or incomplete

**Solution:**
```bash
# Install pytest-cov
pip install pytest-cov

# Ensure source directory is correct
pytest --cov=src --cov-report=html

# Check .coveragerc configuration
cat .coveragerc
```

---

## Best Practices

### Writing Tests

1. **Use Descriptive Names**
   ```python
   # Good
   def test_store_filing_with_valid_data_creates_filing_in_database():
       ...

   # Bad
   def test_filing():
       ...
   ```

2. **Follow AAA Pattern (Arrange, Act, Assert)**
   ```python
   def test_user_creation():
       # Arrange
       user_data = {"email": "test@example.com", ...}

       # Act
       user = auth_service.create_user(user_data)

       # Assert
       assert user.email == "test@example.com"
       assert user.id is not None
   ```

3. **Use Fixtures for Setup**
   ```python
   @pytest.fixture
   def sample_company():
       return Company(ticker="DUOL", name="Duolingo Inc.")

   def test_with_fixture(sample_company):
       assert sample_company.ticker == "DUOL"
   ```

4. **Test Edge Cases**
   ```python
   def test_invalid_inputs():
       # Test empty input
       # Test null values
       # Test boundary conditions
       # Test invalid formats
   ```

5. **Mock External Dependencies**
   ```python
   from unittest.mock import Mock, patch

   @patch('src.connectors.SECConnector')
   def test_with_mock(mock_sec):
       mock_sec.get_filings.return_value = [...]
       # Test logic
   ```

### Running Tests Efficiently

1. **Use Test Markers**
   ```python
   @pytest.mark.critical
   @pytest.mark.slow
   def test_important_feature():
       ...
   ```

2. **Run Specific Suites**
   ```bash
   # Quick unit tests first
   pytest tests/unit/ -v

   # Then integration tests
   pytest tests/integration/ -v
   ```

3. **Parallel Execution for Speed**
   ```bash
   pytest -n auto --dist loadscope
   ```

4. **Use Coverage Incrementally**
   ```bash
   # Check coverage of specific module
   pytest tests/unit/test_auth.py --cov=src.auth
   ```

---

## Performance Testing

### Benchmarking Tests

```bash
# Install pytest-benchmark
pip install pytest-benchmark

# Run benchmark tests
pytest tests/benchmarks/ --benchmark-only

# Compare benchmarks
pytest tests/benchmarks/ --benchmark-compare
```

### Load Testing

```bash
# Install locust
pip install locust

# Run load tests
locust -f tests/load/locustfile.py --host=http://localhost:8000
```

---

## Test Data Management

### Using Factories

```python
# tests/factories.py
import factory
from src.db.models import Company

class CompanyFactory(factory.Factory):
    class Meta:
        model = Company

    ticker = "DUOL"
    name = "Duolingo Inc."
    sector = "EdTech"

# In tests
def test_with_factory():
    company = CompanyFactory()
    assert company.ticker == "DUOL"
```

### Using Fixtures for Reusable Data

```python
@pytest.fixture
def sample_filing_data():
    return {
        "form": "10-K",
        "filingDate": "2024-03-15",
        "content": "Annual Report..."
    }
```

---

## Continuous Integration Best Practices

### Pre-commit Hooks

Install pre-commit to run tests before commits:

```bash
# Install pre-commit
pip install pre-commit

# Setup hooks
pre-commit install

# Configure .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: pytest-check
        name: pytest-check
        entry: pytest
        language: system
        pass_filenames: false
        always_run: true
```

### Coverage Gates

```bash
# Fail CI if coverage below threshold
pytest --cov=src --cov-fail-under=80

# Generate badge
coverage-badge -o coverage.svg
```

---

## Resources

### Documentation
- [Pytest Documentation](https://docs.pytest.org/)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)
- [pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)

### Test Files Location
- Unit Tests: `/tests/unit/`
- Integration Tests: `/tests/integration/`
- Validation Tests: `/tests/validation/`
- Fixtures: `/tests/conftest.py`

### Key Commands Reference

```bash
# Basic execution
pytest                                    # Run all tests
pytest -v                                # Verbose output
pytest -vv                               # Extra verbose

# Coverage
pytest --cov=src                         # Basic coverage
pytest --cov=src --cov-report=html      # HTML report
pytest --cov=src --cov-fail-under=80    # Fail if < 80%

# Selection
pytest tests/unit/                       # Run unit tests
pytest -k "auth"                         # Tests matching "auth"
pytest -m "critical"                     # Tests with marker

# Performance
pytest -n auto                           # Parallel execution
pytest --durations=10                    # Show slowest tests

# Debugging
pytest -s                                # Show print statements
pytest --pdb                             # Drop into debugger on failure
pytest --lf                              # Run last failed tests
pytest --ff                              # Run failures first
```

---

**Last Updated:** October 3, 2025
**Maintainer:** Platform Engineering Team
**Support:** Create issue in GitHub repository
