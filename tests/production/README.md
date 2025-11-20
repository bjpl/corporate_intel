# Production Smoke Tests

## Overview

Critical path smoke tests to validate production deployments. These tests ensure the system is operational and ready to serve users.

**Run these tests**:
- After every deployment
- Daily in production
- Before major releases
- After infrastructure changes

## Quick Start

### Prerequisites

```bash
# Install pytest
pip install pytest pytest-html requests sqlalchemy redis

# Set environment variables
export PRODUCTION_API_URL="https://api.example.com"
export PRODUCTION_DASHBOARD_URL="https://dashboard.example.com"
export PRODUCTION_AUTH_TOKEN="your-auth-token"
export PRODUCTION_DATABASE_URL="postgresql://user:pass@prod-db:5432/corporate_intel"
```

### Run All Tests

```bash
# Run all critical path tests
pytest tests/production/test_critical_path.py -v

# Run only critical tests
pytest tests/production/ -m critical -v

# Generate HTML report
pytest tests/production/ --html=smoke_report.html --self-contained-html

# Run with specific verbosity
pytest tests/production/ -v --tb=short
```

## Test Categories

### 1. Critical Health Checks

**Purpose**: Verify all services are operational

**Tests**:
- Ping endpoint responds quickly (< 100ms)
- Readiness check shows all systems healthy
- Database is connected and responsive
- Cache (Redis) is connected and responsive

**Success Criteria**:
- All endpoints return 200
- Response times within thresholds
- All dependencies healthy

### 2. Critical User Journeys

**Purpose**: Validate core user functionality

**Tests**:
- User can view companies list
- User can view company details
- User can view financial metrics
- Dashboard is accessible and loads

**Success Criteria**:
- All operations succeed
- Data is returned correctly
- No authentication errors
- Acceptable performance

### 3. Critical Data Integrity

**Purpose**: Ensure data quality and consistency

**Tests**:
- Companies have required fields
- Metrics contain valid data
- No null values in critical fields
- Data relationships intact

**Success Criteria**:
- All required fields present
- Data types correct
- No data corruption
- Referential integrity maintained

### 4. Critical Security

**Purpose**: Validate security controls

**Tests**:
- Authentication required for protected endpoints
- CORS headers configured
- HTTPS enforced
- Security headers present

**Success Criteria**:
- Unauthorized requests rejected
- HTTPS only
- Security headers present
- No security regressions

### 5. Critical Performance

**Purpose**: Ensure acceptable performance

**Tests**:
- API response times acceptable
- Database query performance good
- No timeout errors

**Success Criteria**:
- P95 < 500ms
- P99 < 1000ms
- Database queries < 200ms
- Consistent performance

## Test Markers

Use pytest markers to run specific test categories:

```bash
# Run only critical tests
pytest tests/production/ -m critical

# Run only performance tests
pytest tests/production/ -m performance

# Run only security tests
pytest tests/production/ -m security

# Run critical AND performance tests
pytest tests/production/ -m "critical and performance"

# Run critical OR security tests
pytest tests/production/ -m "critical or security"
```

## Expected Output

### Successful Run

```
tests/production/test_critical_path.py::TestCriticalHealthChecks::test_ping_responds_quickly PASSED
tests/production/test_critical_path.py::TestCriticalHealthChecks::test_readiness_check_all_systems PASSED
tests/production/test_critical_path.py::TestCriticalHealthChecks::test_database_connectivity PASSED
tests/production/test_critical_path.py::TestCriticalHealthChecks::test_cache_connectivity PASSED
tests/production/test_critical_path.py::TestCriticalUserJourneys::test_user_can_view_companies PASSED
tests/production/test_critical_path.py::TestCriticalUserJourneys::test_user_can_view_company_details PASSED
tests/production/test_critical_path.py::TestCriticalUserJourneys::test_user_can_view_financial_metrics PASSED
tests/production/test_critical_path.py::TestCriticalUserJourneys::test_dashboard_accessible PASSED
tests/production/test_critical_path.py::TestCriticalDataIntegrity::test_companies_have_required_fields PASSED
tests/production/test_critical_path.py::TestCriticalDataIntegrity::test_metrics_have_valid_data PASSED
tests/production/test_critical_path.py::TestCriticalSecurity::test_authentication_required PASSED
tests/production/test_critical_path.py::TestCriticalSecurity::test_cors_headers_configured PASSED
tests/production/test_critical_path.py::TestCriticalSecurity::test_https_enforced PASSED
tests/production/test_critical_path.py::TestCriticalSecurity::test_security_headers_present PASSED
tests/production/test_critical_path.py::TestCriticalPerformance::test_api_response_time_acceptable PASSED
tests/production/test_critical_path.py::TestCriticalPerformance::test_database_query_performance PASSED

========================== 16 passed in 12.34s ==========================
```

### Failed Test Example

```
FAILED tests/production/test_critical_path.py::TestCriticalHealthChecks::test_database_connectivity
  AssertionError: Database not healthy: error
  assert 'error' == 'healthy'

CRITICAL: Production deployment validation FAILED
```

## Troubleshooting

### Test Failures

#### Health Check Failures

**Symptom**: Health endpoints returning non-200 status

**Possible Causes**:
- Service not started
- Database connection issue
- Redis connection issue
- Network problem

**Actions**:
1. Check service logs: `docker logs corporate-intel-api`
2. Verify database: `psql -h prod-db -U postgres -c "SELECT 1;"`
3. Verify Redis: `redis-cli -h prod-redis ping`
4. Check network: `curl -v https://api.example.com/api/v1/health/ping`

#### Authentication Failures

**Symptom**: 401/403 errors on protected endpoints

**Possible Causes**:
- Invalid auth token
- Token expired
- User doesn't exist
- Permissions issue

**Actions**:
1. Verify token is set: `echo $PRODUCTION_AUTH_TOKEN`
2. Test token manually: `curl -H "Authorization: Bearer $PRODUCTION_AUTH_TOKEN" https://api.example.com/api/v1/companies`
3. Generate new token if needed
4. Check user permissions

#### Performance Failures

**Symptom**: Response times exceed thresholds

**Possible Causes**:
- High load
- Database slow
- Cache miss
- Network latency

**Actions**:
1. Check system load
2. Review slow query log
3. Check cache hit ratio
4. Monitor network latency
5. Review resource allocation

## Performance Thresholds

| Test | Threshold | Alert Level |
|------|-----------|-------------|
| Health Check | < 100ms | Critical if > 200ms |
| API P95 | < 500ms | Warning if > 400ms |
| API P99 | < 1000ms | Critical if > 1500ms |
| Database Query | < 200ms | Warning if > 300ms |
| Dashboard Load | < 2s | Warning if > 3s |

## Automation

### Daily Automated Tests

Set up daily automated smoke tests:

```yaml
# .github/workflows/production-smoke-tests.yml
name: Daily Production Smoke Tests

on:
  schedule:
    - cron: '0 6 * * *'  # Every day at 6 AM UTC
  workflow_dispatch:

jobs:
  smoke-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Install dependencies
        run: pip install pytest pytest-html requests sqlalchemy redis
      - name: Run smoke tests
        env:
          PRODUCTION_API_URL: ${{ secrets.PRODUCTION_API_URL }}
          PRODUCTION_AUTH_TOKEN: ${{ secrets.PRODUCTION_AUTH_TOKEN }}
        run: pytest tests/production/test_critical_path.py -v --html=report.html
      - name: Upload results
        if: always()
        uses: actions/upload-artifact@v2
        with:
          name: smoke-test-results
          path: report.html
      - name: Notify on failure
        if: failure()
        uses: 8398a7/action-slack@v3
        with:
          status: ${{ job.status }}
          text: 'Production smoke tests FAILED!'
          webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

### Post-Deployment Hook

Add to deployment script:

```bash
#!/bin/bash
# deploy.sh

# ... deployment steps ...

echo "Running production smoke tests..."
pytest tests/production/test_critical_path.py -v

if [ $? -eq 0 ]; then
    echo "✅ Smoke tests PASSED - Deployment successful"
    exit 0
else
    echo "❌ Smoke tests FAILED - Rolling back deployment"
    ./scripts/rollback.sh
    exit 1
fi
```

## Integration with Monitoring

Send test results to monitoring:

```python
# conftest.py
import pytest
import requests

def pytest_sessionfinish(session, exitstatus):
    """Send test results to monitoring."""
    if exitstatus == 0:
        status = "success"
    else:
        status = "failure"

    # Send to monitoring endpoint
    try:
        requests.post(
            "https://monitoring.example.com/api/test-results",
            json={
                "test_suite": "production_smoke_tests",
                "status": status,
                "timestamp": datetime.now().isoformat(),
                "exit_code": exitstatus
            }
        )
    except Exception as e:
        print(f"Failed to send monitoring data: {e}")
```

## Best Practices

1. **Run After Every Deployment**: Always run smoke tests immediately after deployment
2. **Don't Skip**: Never skip smoke tests, even for "small" changes
3. **Monitor Trends**: Track test execution times to detect degradation
4. **Act on Failures**: Investigate and fix failures immediately
5. **Update Tests**: Keep tests current with application changes
6. **Document Changes**: Note any test modifications in commit messages

## Support

**QA Lead**: qa@example.com
**DevOps**: devops@example.com
**On-Call**: oncall@example.com

## References

- Test Execution Procedures: docs/testing/TEST_EXECUTION_PROCEDURES.md
- Production Validation Checklist: docs/deployment/PRODUCTION_VALIDATION_CHECKLIST.md
- Performance Thresholds: docs/testing/performance-thresholds.md
