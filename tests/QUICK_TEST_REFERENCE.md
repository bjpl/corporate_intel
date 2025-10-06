# Quick Test Reference

## Pipeline Tests - Quick Commands

### Run All Pipeline Tests
```bash
# All pipeline and aggregator tests
pytest tests/unit/test_*_pipeline.py tests/unit/test_data_aggregator.py -v

# Short version
pytest tests/unit/test_{yahoo,sec,alpha}_*.py tests/unit/test_data_aggregator.py -v
```

### Run Specific Pipeline Tests
```bash
# Yahoo Finance only
pytest tests/unit/test_yahoo_finance_pipeline.py -v

# SEC only
pytest tests/unit/test_sec_pipeline.py -v

# Alpha Vantage only
pytest tests/unit/test_alpha_vantage_pipeline.py -v

# Data Aggregator only
pytest tests/unit/test_data_aggregator.py -v
```

### Coverage Report
```bash
# Generate HTML coverage report
pytest tests/unit/test_*_pipeline.py tests/unit/test_data_aggregator.py \
  --cov=src/pipeline \
  --cov=src/connectors \
  --cov-report=html \
  --cov-report=term-missing

# View report
open htmlcov/index.html  # macOS/Linux
start htmlcov/index.html  # Windows
```

### Filter by Test Category
```bash
# Edge cases only
pytest tests/unit/ -k "edge" -v

# Error handling only
pytest tests/unit/ -k "error" -v

# Success scenarios only
pytest tests/unit/ -k "success" -v

# Integration tests only
pytest tests/unit/ -k "integration" -v

# Retry logic only
pytest tests/unit/ -k "retry" -v
```

### Parallel Execution
```bash
# Run tests in parallel (faster)
pytest tests/unit/test_*_pipeline.py tests/unit/test_data_aggregator.py -n auto -v
```

### Watch Mode (for development)
```bash
# Re-run tests on file changes
pytest-watch tests/unit/test_yahoo_finance_pipeline.py
```

## Test Files Overview

### Created/Enhanced
- ✅ `test_yahoo_finance_pipeline.py` - 30+ tests (NEW)
- ✅ `test_data_aggregator.py` - 16+ tests (NEW)
- ✅ `test_sec_pipeline.py` - 40+ tests (Enhanced)
- ✅ `test_alpha_vantage_pipeline.py` - 35+ tests (Enhanced)

### Total Coverage
- **115+ tests** across all pipeline modules
- **~75% estimated coverage** (from 16%)

## Quick Test Validation

### Verify Tests Can Run
```bash
# Check test collection
pytest tests/unit/test_yahoo_finance_pipeline.py --collect-only

# Expected output:
# collected 30 items
```

### Run Quick Smoke Test
```bash
# Run first test from each file
pytest tests/unit/test_yahoo_finance_pipeline.py::TestSuccessfulDataFetch::test_fetch_valid_ticker -v
pytest tests/unit/test_data_aggregator.py::TestSuccessfulAggregation::test_aggregate_all_sources -v
```

## Common Issues & Solutions

### Issue: Tests Not Found
```bash
# Solution: Run from project root
cd C:/Users/brand/Development/Project_Workspace/active-development/corporate_intel
pytest tests/unit/test_yahoo_finance_pipeline.py -v
```

### Issue: Import Errors
```bash
# Solution: Install test dependencies
pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-cov pytest-mock
```

### Issue: Async Warnings
```bash
# Solution: Use pytest-asyncio
pip install pytest-asyncio

# Add to pytest.ini:
# [pytest]
# asyncio_mode = auto
```

## Expected Results

### Successful Run
```
======================== test session starts =========================
collected 115 items

test_yahoo_finance_pipeline.py ..............................  [ 26%]
test_sec_pipeline.py .....................................      [ 61%]
test_alpha_vantage_pipeline.py ...........................      [ 91%]
test_data_aggregator.py ..........                             [100%]

======================== 115 passed in 8.42s ========================
```

### Coverage Report
```
Name                                    Stmts   Miss  Cover   Missing
---------------------------------------------------------------------
src/pipeline/yahoo_finance_ingestion.py   250     50    80%   45-50, 120-125
src/pipeline/sec_ingestion.py             300     45    85%   78-82, 234-240
src/pipeline/alpha_vantage_ingestion.py   200     50    75%   89-95, 178-185
src/connectors/data_sources.py            350     35    90%   445-450
---------------------------------------------------------------------
TOTAL                                    1100    180    75%
```

## Test Categories

### By Module (30 tests)
- Yahoo Finance: Fetch, transform, store
- SEC: Download, validate, store
- Alpha Vantage: API calls, 'None' handling
- Aggregator: Multi-source integration

### By Scenario (40 tests)
- Success scenarios
- Invalid data handling
- Rate limiting & retries
- Database operations
- Error handling
- Edge cases

### By Type (45 tests)
- Unit tests (isolated functions)
- Integration tests (multi-component)
- Async tests (concurrent operations)
- Mock tests (external dependencies)

## Next Steps After Running Tests

1. **Check Coverage**: Verify 70%+ achieved
2. **Fix Failures**: Address any failing tests
3. **Add Missing**: Cover any gaps in coverage report
4. **Document**: Update test docs with any changes
5. **CI/CD**: Integrate into GitHub Actions

---

**Quick Start**:
```bash
# 1. Run all tests
pytest tests/unit/test_*_pipeline.py tests/unit/test_data_aggregator.py -v

# 2. Generate coverage
pytest tests/unit/test_*_pipeline.py tests/unit/test_data_aggregator.py \
  --cov=src/pipeline --cov=src/connectors --cov-report=html

# 3. View results
open htmlcov/index.html
```
