# Load Testing Suite

## Overview

This directory contains comprehensive load testing scenarios using Locust to validate system performance under various conditions.

## Quick Start

### Prerequisites

```bash
# Install Locust
pip install locust

# Set environment variables
export PRODUCTION_API_URL="https://api.example.com"
export PRODUCTION_AUTH_TOKEN="your-auth-token"
export PRODUCTION_ADMIN_TOKEN="your-admin-token"  # Optional
```

### Run Individual Scenarios

```bash
# Baseline (10 users, 5 min)
locust -f locustfile_production.py \
    --host=$PRODUCTION_API_URL \
    --users=10 \
    --spawn-rate=1 \
    --run-time=5m \
    --headless

# Peak Load (100 users, 10 min)
locust -f locustfile_production.py \
    --host=$PRODUCTION_API_URL \
    --users=100 \
    --spawn-rate=10 \
    --run-time=10m \
    --headless

# Stress Test (200 users, 15 min)
locust -f locustfile_production.py \
    --host=$PRODUCTION_API_URL \
    --users=200 \
    --spawn-rate=20 \
    --run-time=15m \
    --headless

# Endurance (50 users, 60 min)
locust -f locustfile_production.py \
    --host=$PRODUCTION_API_URL \
    --users=50 \
    --spawn-rate=5 \
    --run-time=60m \
    --headless
```

### Run All Scenarios (Automated)

```bash
chmod +x run_load_tests.sh
./run_load_tests.sh
```

This will run all four scenarios sequentially and generate reports.

## Test Scenarios

### 1. Baseline Load Test

**Purpose**: Establish baseline performance metrics under normal load

**Configuration**:
- Users: 10 concurrent
- Spawn Rate: 1 user/sec
- Duration: 5 minutes
- User Types: 70% Normal, 20% Peak, 10% Admin

**Success Criteria**:
- P50 < 100ms
- P95 < 300ms
- P99 < 500ms
- Error Rate < 0.1%
- CPU < 30%
- Memory < 40%

### 2. Peak Load Test (2x Normal)

**Purpose**: Validate system handles peak traffic during busy periods

**Configuration**:
- Users: 100 concurrent
- Spawn Rate: 10 users/sec
- Duration: 10 minutes

**Success Criteria**:
- P95 < 500ms
- P99 < 1000ms
- Error Rate < 1%
- CPU < 70%
- Memory < 80%
- Auto-scaling triggers

### 3. Stress Test

**Purpose**: Find system breaking point and validate graceful degradation

**Configuration**:
- Users: 200 concurrent
- Spawn Rate: 20 users/sec
- Duration: 15 minutes

**Success Criteria**:
- System remains available
- Error Rate < 5%
- Graceful degradation
- Alerts triggered
- System recovers
- No memory leaks

### 4. Endurance Test

**Purpose**: Detect memory leaks and stability issues under sustained load

**Configuration**:
- Users: 50 concurrent
- Spawn Rate: 5 users/sec
- Duration: 60 minutes

**Success Criteria**:
- Memory usage stable
- Response times consistent
- No connection leaks
- Error rate remains low
- System stable for duration

## User Classes

### BaselineUser (70% of traffic)

Simulates normal user behavior with realistic wait times.

**Tasks**:
- Health checks (50%)
- List companies (40%)
- View company details (30%)
- Get metrics (30%)
- Search companies (15%)
- Intelligence summary (10%)

**Wait Time**: 2-5 seconds between requests

### PeakUser (20% of traffic)

More aggressive usage patterns during peak periods.

**Tasks**:
- Rapid company browsing (50%)
- Concurrent metrics requests (30%)
- Dashboard refreshes (20%)

**Wait Time**: 1-3 seconds between requests

### AdminUser (10% of traffic)

Resource-intensive admin operations.

**Tasks**:
- System health checks (50%)
- Bulk data queries (30%)
- Report generation (20%)

**Wait Time**: 5-15 seconds between requests

### StressTestUser

Extreme load for stress testing only.

**Tasks**:
- Rapid fire requests to various endpoints

**Wait Time**: 0.1-0.5 seconds between requests

## Metrics and Reporting

### Real-time Metrics

During test execution, Locust tracks:
- Requests per second (RPS)
- Response times (min/max/avg/percentiles)
- Failure rates
- Active users
- Request distribution by endpoint

### Performance Report

After test completion, detailed reports include:

```
LOAD TEST PERFORMANCE REPORT
============================

BASIC STATISTICS
----------------
Total Requests:        125,432
Total Failures:        234
Failure Rate:          0.19%
Requests/sec:          418.11

RESPONSE TIME STATISTICS
------------------------
Average:               125.45ms
Median:                89.23ms
Min:                   12.34ms
Max:                   2,345.67ms
50th Percentile (P50): 89.23ms
75th Percentile (P75): 156.78ms
90th Percentile (P90): 245.89ms
95th Percentile (P95): 378.45ms
99th Percentile (P99): 892.34ms

PERFORMANCE VALIDATION
----------------------
✅ P95 Response Time: 378.45ms (threshold: 500ms)
✅ P99 Response Time: 892.34ms (threshold: 1000ms)
✅ Average Response Time: 125.45ms (threshold: 200ms)
✅ Failure Rate: 0.19% (threshold: 1%)

ALL PERFORMANCE THRESHOLDS MET
```

### HTML Reports

HTML reports are generated for each scenario:
- `baseline_YYYYMMDD_HHMMSS.html`
- `peak_load_YYYYMMDD_HHMMSS.html`
- `stress_test_YYYYMMDD_HHMMSS.html`
- `endurance_YYYYMMDD_HHMMSS.html`

Open in browser for interactive charts and detailed statistics.

### JSON Reports

Detailed JSON reports are saved:
- `load_test_report_YYYYMMDD_HHMMSS.json`

Contains:
- Summary statistics
- Slow requests (>1s)
- Failed requests
- Endpoint-level metrics

## Performance Thresholds

| Metric | Baseline | Peak | Stress | Endurance |
|--------|----------|------|--------|-----------|
| P50 Response Time | < 100ms | < 200ms | < 300ms | < 150ms |
| P95 Response Time | < 300ms | < 500ms | < 1000ms | < 400ms |
| P99 Response Time | < 500ms | < 1000ms | < 2000ms | < 800ms |
| Error Rate | < 0.1% | < 1% | < 5% | < 0.5% |
| RPS | ~20 | ~200 | ~400 | ~100 |
| CPU Usage | < 30% | < 70% | < 90% | < 50% |
| Memory Usage | < 40% | < 80% | < 95% | Stable |

## Interpreting Results

### Good Results ✅

- All thresholds met
- Response times consistent
- Error rate low
- Resource usage within limits
- System stable

### Warning Signs ⚠️

- P95 approaching threshold
- Error rate increasing
- Memory usage growing
- CPU consistently high
- Slow requests increasing

### Critical Issues ❌

- Thresholds exceeded
- High error rate (>5%)
- System crashes
- Memory leaks detected
- Response times degrading
- Connection pool exhaustion

## Troubleshooting

### High Response Times

**Possible Causes**:
- Database queries not optimized
- Missing indexes
- Cache misses
- Network latency
- Insufficient resources

**Actions**:
1. Check slow query log
2. Verify indexes
3. Check cache hit ratio
4. Monitor network
5. Review resource allocation

### High Error Rate

**Possible Causes**:
- Rate limiting
- Database connection pool exhausted
- Memory issues
- Service crashes
- Network issues

**Actions**:
1. Check error logs
2. Verify connection pool settings
3. Monitor memory usage
4. Check service health
5. Review network connectivity

### Memory Leaks

**Indicators**:
- Memory usage continuously growing
- No stabilization over time
- OOM errors

**Actions**:
1. Profile memory usage
2. Check for unclosed connections
3. Review caching strategy
4. Monitor garbage collection
5. Analyze heap dumps

## Best Practices

### Before Testing

1. **Notify Stakeholders**: Inform team about testing
2. **Verify Environment**: Ensure environment is stable
3. **Baseline Metrics**: Capture current performance
4. **Monitoring Ready**: Have dashboards open
5. **Rollback Plan**: Be ready to stop if issues

### During Testing

1. **Monitor Closely**: Watch metrics in real-time
2. **Check Logs**: Look for errors and warnings
3. **Resource Usage**: Monitor CPU, memory, disk
4. **Network**: Check network utilization
5. **Database**: Watch query performance

### After Testing

1. **Analyze Results**: Review all metrics
2. **Compare Baselines**: Track performance trends
3. **Document Issues**: Record any problems
4. **Action Items**: Create tasks for improvements
5. **Update Thresholds**: Adjust based on results

## Integration with CI/CD

### Automated Load Tests

```yaml
# .github/workflows/load-test.yml
name: Weekly Load Test

on:
  schedule:
    - cron: '0 2 * * 0'  # Every Sunday at 2 AM
  workflow_dispatch:

jobs:
  load-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Install dependencies
        run: pip install locust
      - name: Run baseline test
        run: |
          locust -f tests/load/locustfile_production.py \
            --host=${{ secrets.PRODUCTION_API_URL }} \
            --users=10 \
            --spawn-rate=1 \
            --run-time=5m \
            --headless
      - name: Upload results
        uses: actions/upload-artifact@v2
        with:
          name: load-test-results
          path: load_test_report_*.json
```

## Continuous Monitoring

Set up alerts for:
- Test failures
- Performance degradation
- Error rate increases
- Resource exhaustion

## Support

**Performance Engineer**: perf@example.com
**DevOps Team**: devops@example.com
**On-Call**: oncall@example.com

## References

- Locust Documentation: https://docs.locust.io/
- Performance Testing Guide: docs/testing/TEST_EXECUTION_PROCEDURES.md
- Production Validation: docs/deployment/PRODUCTION_VALIDATION_CHECKLIST.md
