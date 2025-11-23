# Smoke Test Report - Day 3

**Date:** 2025-10-17 18:48:30
**Environment:** Staging (Production Proxy)
**Base URL:** http://localhost:8004
**Duration:** 26.31 seconds

## Executive Summary

- **Total Tests:** 38
- **Passed:** 14 (36.8%)
- **Failed:** 7
- **Warnings:** 17

### Overall Status

❌ **SMOKE TESTS FAILED** - Action required before production deployment

## Results by Category

| Category | Total | Passed | Failed | Warnings |
|----------|-------|--------|--------|----------|
| Infrastructure | 5 | 3 | 1 | 1 |
| Database | 6 | 2 | 1 | 3 |
| Cache | 4 | 3 | 1 | 0 |
| Api Health | 5 | 1 | 2 | 2 |
| Api Endpoints | 7 | 0 | 1 | 6 |
| Performance | 5 | 1 | 1 | 3 |
| Security | 3 | 1 | 0 | 2 |
| Monitoring | 3 | 3 | 0 | 0 |

## Detailed Test Results


### Infrastructure

- ✅ **Docker Containers Running** (316.31ms): All containers running (5/4+)
- ✅ **Docker Network Exists** (210.30ms): Network configured correctly
- ✅ **Docker Volumes Present** (168.95ms): All volumes present (6/4+)
- ❌ **HTTP Connectivity** (4156.46ms): Connection failed
  - Error: HTTPConnectionPool(host='localhost', port=8004): Max retries exceeded with url: /health (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x000001EA27D14FD0>: Failed to establish a new connection: [WinError 10061] No connection could be made because the target machine actively refused it'))
- ⚠️ **Container Health Status** (262.21ms): Some containers not healthy (2)
  - Error: Health check issues

### Database

- ✅ **PostgreSQL Container Running** (333.44ms): Container is running
- ✅ **PostgreSQL Connectivity** (383.83ms): Accepting connections
- ❌ **Database Exists** (314.16ms): Database not found
  - Error: DB missing
- ⚠️ **Database Tables Exist** (333.32ms): No tables found
  - Error: Migrations may not have run
- ⚠️ **Companies Table Has Data** (422.62ms): Table is empty
  - Error: Seed data missing
- ⚠️ **Database Query Performance** (485.28ms): Query took 485.28ms
  - Error: Performance degradation

### Cache

- ✅ **Redis Container Running** (247.01ms): Container is running
- ❌ **Redis Connectivity** (508.16ms): Redis not responding
  - Error: NOAUTH Authentication required.


- ✅ **Redis SET/GET Operations** (0.50ms): Redis operations available (auth configured)
- ✅ **Redis Statistics** (0.50ms): Redis stats accessible

### Api Health

- ❌ **Basic Health Endpoint** (4089.59ms): Request failed
  - Error: HTTPConnectionPool(host='localhost', port=8004): Max retries exceeded with url: /health (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x000001EA27D15450>: Failed to establish a new connection: [WinError 10061] No connection could be made because the target machine actively refused it'))
- ❌ **Ping Endpoint** (4085.71ms): Request failed
  - Error: HTTPConnectionPool(host='localhost', port=8004): Max retries exceeded with url: /health/ping (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x000001EA27D16A10>: Failed to establish a new connection: [WinError 10061] No connection could be made because the target machine actively refused it'))
- ⚠️ **Detailed Health Check** (515.22ms): Request failed
  - Error: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
- ⚠️ **Health Endpoint Response Time** (7.22ms): Request failed
  - Error: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
- ✅ **API Readiness** (0.10ms): API accepting requests

### Api Endpoints

- ❌ **Companies List Endpoint** (10.50ms): Request failed
  - Error: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
- ⚠️ **Companies Endpoint Response Time** (22.98ms): Request failed
  - Error: ('Connection aborted.', ConnectionAbortedError(10053, 'An established connection was aborted by the software in your host machine', None, 10053, None))
- ⚠️ **Company Detail Endpoint** (22.50ms): Request failed
  - Error: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
- ⚠️ **API Documentation** (23.81ms): Request failed
  - Error: ('Connection aborted.', ConnectionAbortedError(10053, 'An established connection was aborted by the software in your host machine', None, 10053, None))
- ⚠️ **OpenAPI Schema** (17.22ms): Request failed
  - Error: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
- ⚠️ **404 Error Handling** (9.48ms): Request failed
  - Error: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
- ⚠️ **Invalid Ticker Handling** (9.99ms): Request failed
  - Error: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))

### Performance

- ❌ **Concurrent Requests (10 users)** (94.75ms): Test failed
  - Error: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
- ⚠️ **Throughput Test** (15.17ms): Test failed
  - Error: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
- ⚠️ **Average Response Time** (0.00ms): Test failed
  - Error: ('Connection aborted.', ConnectionAbortedError(10053, 'An established connection was aborted by the software in your host machine', None, 10053, None))
- ⚠️ **P95 Response Time** (0.00ms): Test failed
  - Error: list index out of range
- ✅ **API Container Memory Usage** (2333.46ms): 102.1MiB (healthy)

### Security

- ⚠️ **Security Headers Present** (4351.90ms): Failed to check headers
  - Error: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
- ⚠️ **Authentication Required** (7.69ms): Request failed
  - Error: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
- ✅ **SQL Injection Prevention** (24.50ms): Request rejected
  - Error: ('Connection aborted.', ConnectionAbortedError(10053, 'An established connection was aborted by the software in your host machine', None, 10053, None))

### Monitoring

- ✅ **Prometheus Container** (234.89ms): Container running
- ✅ **Grafana Container** (223.10ms): Container running
- ✅ **Prometheus Health** (2038.86ms): Healthy and accessible

## Performance Comparison to Baseline

- **Baseline P50:** 5.31ms
- **Baseline P95:** 18.93ms
- **Baseline P99:** 32.14ms
- **Baseline Mean:** 8.42ms
- **Baseline Throughput:** 27.3 QPS
- **Baseline Success Rate:** 100.0%

## Recommendations

### Critical Actions Required

- Fix: HTTP Connectivity - Connection failed
- Fix: Database Exists - Database not found
- Fix: Redis Connectivity - Redis not responding
- Fix: Basic Health Endpoint - Request failed
- Fix: Ping Endpoint - Request failed
- Fix: Companies List Endpoint - Request failed
- Fix: Concurrent Requests (10 users) - Test failed

### Items to Review

- Review: Container Health Status - Some containers not healthy (2)
- Review: Database Tables Exist - No tables found
- Review: Companies Table Has Data - Table is empty
- Review: Database Query Performance - Query took 485.28ms
- Review: Detailed Health Check - Request failed
- Review: Health Endpoint Response Time - Request failed
- Review: Companies Endpoint Response Time - Request failed
- Review: Company Detail Endpoint - Request failed
- Review: API Documentation - Request failed
- Review: OpenAPI Schema - Request failed
- Review: 404 Error Handling - Request failed
- Review: Invalid Ticker Handling - Request failed
- Review: Throughput Test - Test failed
- Review: Average Response Time - Test failed
- Review: P95 Response Time - Test failed
- Review: Security Headers Present - Failed to check headers
- Review: Authentication Required - Request failed

---

*Report generated automatically by smoke test suite*
