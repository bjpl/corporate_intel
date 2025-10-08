# Real-World Data Ingestion Testing Guide

## Overview

Real-world integration tests validate the data ingestion pipelines against actual APIs (SEC EDGAR, Yahoo Finance, Alpha Vantage). These tests ensure:

- **API Connectivity**: Services are accessible and responding
- **Data Quality**: Retrieved data meets quality standards
- **Error Handling**: Graceful degradation when errors occur
- **Rate Limiting**: API quotas are respected
- **Cross-Source Consistency**: Data from different sources aligns
- **Performance**: Ingestion completes within acceptable timeframes

## ⚠️ Important Considerations

### API Costs & Rate Limits

Real-world tests make actual API calls, which may:

- **Consume API quotas** (especially Alpha Vantage free tier: 5 calls/min, 500/day)
- **Take significant time** (rate limiting enforced)
- **Cost money** (if using paid API tiers)

**Always use the `--real-world` flag** to prevent accidental API calls during regular testing.

### Prerequisites

1. **Environment Variables** (`.env` file):
   ```env
   # Required for SEC EDGAR
   SEC_USER_AGENT=YourName your@email.com

   # Optional for Alpha Vantage tests
   ALPHA_VANTAGE_API_KEY=your_api_key_here

   # Database connection
   DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/corporate_intel
   ```

2. **Database**: Running PostgreSQL instance with TimescaleDB extension

3. **Internet Connection**: Stable connection for API calls

4. **Python Environment**: All dependencies installed (`pip install -e .`)

## Quick Start

### Run Quick Smoke Tests (Recommended)

Fast connectivity checks (~30 seconds):

```bash
# Windows (Git Bash)
bash scripts/run_real_world_tests.sh --quick

# Linux/Mac
./scripts/run_real_world_tests.sh --quick

# Or directly with pytest
pytest tests/integration/test_real_world_ingestion.py::TestRealWorldSECIngestion::test_sec_api_connectivity \
       tests/integration/test_real_world_ingestion.py::TestRealWorldYahooFinanceIngestion::test_yahoo_finance_api_connectivity \
       --real-world -v
```

### Run SEC EDGAR Tests

Tests SEC filing ingestion pipeline:

```bash
bash scripts/run_real_world_tests.sh --sec

# Or directly
pytest tests/integration/test_real_world_ingestion.py::TestRealWorldSECIngestion --real-world -v
```

**Tests Include**:
- ✅ SEC API connectivity
- ✅ Filing data quality validation
- ✅ Content download and validation
- ✅ Rate limiting compliance (10 req/sec)
- ✅ End-to-end ingestion workflow

**Expected Duration**: 2-3 minutes

### Run Yahoo Finance Tests

Tests Yahoo Finance data ingestion:

```bash
bash scripts/run_real_world_tests.sh --yahoo

# Or directly
pytest tests/integration/test_real_world_ingestion.py::TestRealWorldYahooFinanceIngestion --real-world -v
```

**Tests Include**:
- ✅ Yahoo Finance API connectivity
- ✅ Quarterly financials data quality
- ✅ Revenue, margin, and growth metrics
- ✅ End-to-end ingestion workflow

**Expected Duration**: 1-2 minutes

### Run Alpha Vantage Tests (Optional)

Tests Alpha Vantage fundamental data ingestion:

```bash
bash scripts/run_real_world_tests.sh --alpha

# Or directly
pytest tests/integration/test_real_world_ingestion.py::TestRealWorldAlphaVantageIngestion --real-world -v
```

**Tests Include**:
- ✅ Alpha Vantage API connectivity
- ✅ Rate limiting (5 calls/min, 12s between calls)
- ✅ Fundamental data quality (P/E, EPS, market cap)

**Expected Duration**: 1-2 minutes (due to rate limiting)

⚠️ **Note**: Requires `ALPHA_VANTAGE_API_KEY` in `.env`. Tests will be skipped if not configured.

### Run Full Test Suite

Complete validation of all sources:

```bash
bash scripts/run_real_world_tests.sh --full --report

# Or directly
pytest tests/integration/test_real_world_ingestion.py --real-world -v
```

**Expected Duration**: 5-10 minutes

## Test Categories

### 1. API Connectivity Tests

**Purpose**: Verify APIs are accessible and returning data

**Tests**:
- `test_sec_api_connectivity`: SEC EDGAR API
- `test_yahoo_finance_api_connectivity`: Yahoo Finance
- `test_alpha_vantage_api_connectivity`: Alpha Vantage

**Success Criteria**:
- API returns valid response
- Response format matches expected structure
- No authentication errors

### 2. Data Quality Tests

**Purpose**: Validate data meets quality standards (MANDATORY-20)

**Tests**:
- `test_sec_filings_data_quality`: Filing metadata completeness
- `test_yahoo_quarterly_financials_data_quality`: Financial metrics
- `test_alpha_vantage_data_quality`: Fundamental data ranges

**Success Criteria**:
- All required fields present
- Data types correct
- Values within reasonable ranges
- Date formats consistent

### 3. Rate Limiting Tests

**Purpose**: Ensure API quotas are respected (MANDATORY-18)

**Tests**:
- `test_sec_rate_limiting`: 10 requests/second limit
- `test_alpha_vantage_rate_limiting`: 5 requests/minute limit

**Success Criteria**:
- Delays enforced between requests
- No 429 (Too Many Requests) errors
- Timing measurements within expected range

### 4. End-to-End Integration Tests

**Purpose**: Validate complete ingestion workflows (MANDATORY-8)

**Tests**:
- `test_sec_end_to_end_ingestion`: SEC filing pipeline
- `test_yahoo_finance_end_to_end_ingestion`: Yahoo Finance pipeline

**Success Criteria**:
- Data fetched from API
- Data validated
- Data stored in database
- Database integrity verified

### 5. Cross-Source Consistency Tests

**Purpose**: Ensure data consistency across sources (MANDATORY-20)

**Tests**:
- `test_company_data_consistency`: Company names/tickers match
- `test_revenue_data_consistency`: Revenue figures align

**Success Criteria**:
- No conflicting data between sources
- Values in same order of magnitude
- Company identifiers match

### 6. Error Handling Tests

**Purpose**: Validate graceful degradation (MANDATORY-7)

**Tests**:
- `test_invalid_ticker_handling`: Invalid input handling
- `test_network_timeout_handling`: Timeout scenarios
- `test_rate_limit_handling`: Rate limit errors

**Success Criteria**:
- No crashes on errors
- Appropriate error messages
- Proper exception types
- Retry logic works

### 7. Performance Tests

**Purpose**: Measure ingestion performance (MANDATORY-14)

**Tests**:
- `test_batch_ingestion_performance`: Multiple companies
- `test_concurrent_ingestion_performance`: Parallel processing

**Success Criteria**:
- Batch ingestion < 60s for 3 companies
- Average time < 20s per company
- No memory issues

### 8. Data Quality Report

**Purpose**: Generate comprehensive quality metrics (MANDATORY-16, MANDATORY-20)

**Test**: `test_generate_data_quality_report`

**Output**:
- Companies with complete data
- Missing data gaps
- Data freshness
- Quality score (0-100)

**Success Criteria**:
- Quality score >= 50
- Report generation successful

## Common Issues & Solutions

### Issue: `SEC_USER_AGENT not configured`

**Solution**: Add to `.env` file:
```env
SEC_USER_AGENT=YourName your@email.com
```

SEC requires a User-Agent header with contact information.

### Issue: `Rate limit exceeded` (429 error)

**Solution**: Tests include rate limiting, but if you get this error:

1. Wait 60 seconds before retrying
2. Reduce test scope (use `--quick` flag)
3. Check if other processes are hitting the API

### Issue: `Database connection failed`

**Solution**:
1. Ensure PostgreSQL is running: `docker compose up -d postgres`
2. Check `DATABASE_URL` in `.env`
3. Run migrations: `alembic upgrade head`

### Issue: `Alpha Vantage tests skipped`

**Solution**: This is expected if `ALPHA_VANTAGE_API_KEY` is not configured. To enable:

1. Get free API key from https://www.alphavantage.co/support/#api-key
2. Add to `.env`: `ALPHA_VANTAGE_API_KEY=your_key`
3. Re-run tests

### Issue: Tests taking too long

**Solution**:
- Use `--quick` flag for smoke tests
- Run specific test suites (`--sec`, `--yahoo`)
- Check internet connection speed
- Rate limiting is intentional for API compliance

## Interpreting Results

### Success Output

```
============================================================================
Real-World Data Ingestion Tests
============================================================================

✓ Environment configured
✓ Database connection successful

Running quick smoke tests...
test_sec_api_connectivity PASSED
test_yahoo_finance_api_connectivity PASSED

✓ Quick tests passed

============================================================================
All tests completed successfully!
============================================================================
```

### Partial Failure Example

```
test_alpha_vantage_api_connectivity FAILED
  Error: ALPHA_VANTAGE_API_KEY not configured

⚠ Alpha Vantage tests skipped (expected if API key not configured)
```

### Data Quality Report Example

```
Data Quality Report:
  Total Companies: 27
  Companies with Financials: 25 (93%)
  Companies with Filings: 22 (81%)
  Average Metrics per Company: 8.5
  Data Quality Score: 87/100

✓ Data quality meets minimum standards (>= 50)
```

## Best Practices

### 1. Run Quick Tests First

Always start with `--quick` to verify connectivity before running expensive full tests:

```bash
bash scripts/run_real_world_tests.sh --quick
```

### 2. Incremental Testing

Test one source at a time during development:

```bash
# First, test SEC only
bash scripts/run_real_world_tests.sh --sec

# Then Yahoo
bash scripts/run_real_world_tests.sh --yahoo

# Finally, full suite
bash scripts/run_real_world_tests.sh --full
```

### 3. Monitor API Quotas

**Alpha Vantage Free Tier**:
- 5 API calls per minute
- 500 calls per day

Keep track of usage to avoid hitting limits.

### 4. Generate Reports Regularly

Run data quality reports to identify issues:

```bash
bash scripts/run_real_world_tests.sh --quick --report
```

### 5. CI/CD Integration

For automated testing, use scheduled jobs (not on every commit):

```yaml
# .github/workflows/real-world-tests.yml
name: Real-World Integration Tests
on:
  schedule:
    - cron: '0 2 * * 1'  # Weekly on Monday at 2 AM
  workflow_dispatch:  # Manual trigger

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Tests
        run: bash scripts/run_real_world_tests.sh --quick --report
        env:
          SEC_USER_AGENT: ${{ secrets.SEC_USER_AGENT }}
          ALPHA_VANTAGE_API_KEY: ${{ secrets.ALPHA_VANTAGE_API_KEY }}
```

## Advanced Usage

### Running Specific Tests

```bash
# Single test
pytest tests/integration/test_real_world_ingestion.py::TestRealWorldSECIngestion::test_sec_api_connectivity --real-world -v

# Test class
pytest tests/integration/test_real_world_ingestion.py::TestRealWorldSECIngestion --real-world -v

# Multiple test classes
pytest tests/integration/test_real_world_ingestion.py::TestRealWorldSECIngestion \
       tests/integration/test_real_world_ingestion.py::TestCrossSourceConsistency \
       --real-world -v
```

### Custom Pytest Options

```bash
# Verbose output with full tracebacks
pytest tests/integration/test_real_world_ingestion.py --real-world -vv --tb=long

# Stop on first failure
pytest tests/integration/test_real_world_ingestion.py --real-world -x

# Run with coverage
pytest tests/integration/test_real_world_ingestion.py --real-world --cov=src.pipeline

# Parallel execution (use with caution due to rate limits)
pytest tests/integration/test_real_world_ingestion.py --real-world -n 2
```

### Debugging Failed Tests

```bash
# Show print statements
pytest tests/integration/test_real_world_ingestion.py::test_name --real-world -s

# Enter debugger on failure
pytest tests/integration/test_real_world_ingestion.py::test_name --real-world --pdb

# Show local variables on failure
pytest tests/integration/test_real_world_ingestion.py::test_name --real-world -l
```

## Contributing

When adding new real-world tests:

1. **Mark with `@pytest.mark.real_world`** decorator
2. **Require `real_world_enabled` fixture** to prevent accidental runs
3. **Respect rate limits** - add appropriate delays
4. **Validate data quality** - check for expected fields and ranges
5. **Handle errors gracefully** - test error scenarios
6. **Document expected duration** in docstring
7. **Minimize API calls** - use sample data where possible

Example:

```python
@pytest.mark.real_world
@pytest.mark.asyncio
async def test_new_api_integration(real_world_enabled):
    """Test new API integration.

    Expected duration: 1-2 minutes

    Validates:
    - API connectivity
    - Data format
    - Error handling
    """
    # Test implementation
    pass
```

## Support

For issues or questions:

1. Check this guide first
2. Review test output and error messages
3. Check API status pages:
   - SEC EDGAR: https://www.sec.gov/
   - Yahoo Finance: https://finance.yahoo.com/
   - Alpha Vantage: https://www.alphavantage.co/
4. Open GitHub issue with:
   - Test command used
   - Error output
   - Environment details (OS, Python version)

---

**Related Documentation**:
- [Deployment Validation Report](deployment_validation_report_2025-10-06.md)
- [Integration Testing Guide](tests/integration/INTEGRATION_TESTING_GUIDE.md)
- [API Documentation](API_REFERENCE.md)
