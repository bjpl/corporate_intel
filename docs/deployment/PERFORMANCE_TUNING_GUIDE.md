# Production Performance Tuning Guide

**Version:** 1.0.0
**Last Updated:** 2025-10-25
**Target:** Sub-100ms p99 latency, 99.9% uptime

---

## Table of Contents

1. [Performance Baselines](#1-performance-baselines)
2. [FastAPI Optimization](#2-fastapi-optimization)
3. [Database Performance](#3-database-performance)
4. [Caching Strategies](#4-caching-strategies)
5. [Load Testing](#5-load-testing)
6. [Monitoring & Profiling](#6-monitoring--profiling)

---

## 1. Performance Baselines

### Current Performance Metrics (from README)

```yaml
Target Performance:
  API Response Time:
    p50: < 50ms
    p95: < 100ms
    p99: < 200ms

  Data Processing:
    Document Processing: 100+ docs/second (Ray)
    Embedding Generation: 1000 docs/minute

  Storage:
    TimescaleDB Compression: 10x

  Dashboard:
    Rendering: < 100ms for 10K data points
```

### Performance SLOs

```yaml
Service Level Objectives:
  Availability: 99.9% (43.2 min downtime/month)
  API Latency (p99): < 200ms
  Error Rate: < 0.1%
  Database Query Time (p95): < 50ms
  Cache Hit Ratio: > 80%
```

---

## 2. FastAPI Optimization

### 2.1 Async Everywhere

**Bad Practice:**
```python
# Blocking I/O in async endpoint
@app.get("/companies/{id}")
async def get_company(id: int):
    company = db.query(Company).filter_by(id=id).first()  # Blocking!
    return company
```

**Good Practice:**
```python
# Non-blocking async operations
@app.get("/companies/{id}")
async def get_company(id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Company).where(Company.id == id)
    )
    company = result.scalar_one_or_none()
    return company
```

### 2.2 Connection Pool Tuning

**Recommended Settings (8GB RAM server):**
```python
from sqlalchemy.ext.asyncio import create_async_engine

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=30,                    # Core pool
    max_overflow=20,                 # Additional connections (total: 50)
    pool_pre_ping=True,              # Health check before use
    pool_recycle=3600,               # Recycle every hour
    pool_timeout=30,                 # Wait 30s for connection
    connect_args={
        "server_settings": {
            "application_name": "corporate-intel-api",
            "jit": "off"             # Disable JIT for faster simple queries
        },
        "command_timeout": 60,
        "timeout": 10,
    }
)
```

### 2.3 Request/Response Optimization

**Enable Response Compression:**
```python
from fastapi.middleware.gzip import GZipMiddleware

app.add_middleware(GZipMiddleware, minimum_size=1000)  # Compress >1KB responses
```

**Use Response Models:**
```python
from pydantic import BaseModel

class CompanyResponse(BaseModel):
    id: int
    ticker: str
    name: str

    class Config:
        orm_mode = True

@app.get("/companies/{id}", response_model=CompanyResponse)
async def get_company(id: int):
    # Only serialize necessary fields
    company = await db.get_company(id)
    return company
```

**Streaming Large Responses:**
```python
from fastapi.responses import StreamingResponse

@app.get("/reports/{id}/download")
async def download_report(id: int):
    async def generate_csv():
        async for row in db.stream_report_data(id):
            yield f"{row.date},{row.value}\n"

    return StreamingResponse(
        generate_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=report_{id}.csv"}
    )
```

### 2.4 Background Tasks

**Offload Heavy Processing:**
```python
from fastapi import BackgroundTasks

@app.post("/filings/ingest")
async def ingest_filing(
    filing: FilingCreate,
    background_tasks: BackgroundTasks
):
    # Quick validation and acknowledgment
    filing_id = await db.create_filing(filing)

    # Heavy processing in background
    background_tasks.add_task(
        process_filing_content,
        filing_id
    )

    return {"id": filing_id, "status": "processing"}
```

---

## 3. Database Performance

### 3.1 Query Optimization

**Use EXPLAIN ANALYZE:**
```sql
-- Identify slow query plans
EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
SELECT c.*, COUNT(f.id) as filing_count
FROM companies c
LEFT JOIN filings f ON f.company_id = c.id
WHERE c.sector = 'EdTech'
GROUP BY c.id;
```

**Add Missing Indexes:**
```sql
-- Find missing indexes
SELECT
    schemaname,
    tablename,
    attname,
    n_distinct,
    correlation
FROM pg_stats
WHERE schemaname = 'public'
  AND n_distinct > 100
  AND correlation < 0.5
ORDER BY n_distinct DESC;

-- Create composite indexes
CREATE INDEX CONCURRENTLY idx_filings_company_date
ON filings(company_id, filing_date DESC);

CREATE INDEX CONCURRENTLY idx_metrics_company_metric_date
ON metrics(company_id, metric_name, date DESC);
```

**Optimize JOIN Queries:**
```sql
-- Bad: Cartesian product
SELECT * FROM companies c, filings f
WHERE c.id = f.company_id;

-- Good: Explicit JOIN
SELECT * FROM companies c
INNER JOIN filings f ON c.id = f.company_id;

-- Better: Materialized view for frequent queries
CREATE MATERIALIZED VIEW company_filing_summary AS
SELECT
    c.id,
    c.ticker,
    c.name,
    COUNT(f.id) as filing_count,
    MAX(f.filing_date) as last_filing_date
FROM companies c
LEFT JOIN filings f ON f.company_id = c.id
GROUP BY c.id, c.ticker, c.name;

CREATE UNIQUE INDEX ON company_filing_summary(id);
REFRESH MATERIALIZED VIEW CONCURRENTLY company_filing_summary;
```

### 3.2 TimescaleDB Optimization

**Hypertable Configuration:**
```sql
-- Convert to hypertable (already done in migrations)
SELECT create_hypertable('metrics', 'date', chunk_time_interval => INTERVAL '7 days');

-- Enable compression
ALTER TABLE metrics SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'company_id,metric_name',
    timescaledb.compress_orderby = 'date DESC'
);

-- Compress chunks older than 30 days
SELECT add_compression_policy('metrics', INTERVAL '30 days');

-- Retention policy (drop data older than 2 years)
SELECT add_retention_policy('metrics', INTERVAL '2 years');
```

**Continuous Aggregates:**
```sql
-- Pre-compute daily aggregations
CREATE MATERIALIZED VIEW metrics_daily
WITH (timescaledb.continuous) AS
SELECT
    company_id,
    metric_name,
    time_bucket('1 day', date) AS day,
    AVG(value) as avg_value,
    MAX(value) as max_value,
    MIN(value) as min_value,
    COUNT(*) as count
FROM metrics
GROUP BY company_id, metric_name, day;

-- Auto-refresh policy
SELECT add_continuous_aggregate_policy('metrics_daily',
    start_offset => INTERVAL '3 days',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour'
);
```

### 3.3 Connection Pooling with PgBouncer

**Why PgBouncer?**
- Reduces connection overhead (10,000 client connections → 100 database connections)
- Enables connection reuse
- Faster query execution

**docker-compose.production.yml addition:**
```yaml
services:
  pgbouncer:
    image: edoburu/pgbouncer:1.21.0
    container_name: corporate-intel-pgbouncer
    restart: always
    environment:
      DATABASE_URL: postgres://postgres:${POSTGRES_PASSWORD}@postgres:5432/corporate_intel
      POOL_MODE: transaction
      MAX_CLIENT_CONN: 10000
      DEFAULT_POOL_SIZE: 25
      RESERVE_POOL_SIZE: 5
      SERVER_IDLE_TIMEOUT: 600
      SERVER_LIFETIME: 3600
      QUERY_TIMEOUT: 120
    ports:
      - "127.0.0.1:6432:6432"
    depends_on:
      postgres:
        condition: service_healthy
    networks:
      - backend
```

**Application Configuration:**
```python
# Update connection string
SQLALCHEMY_DATABASE_URI = "postgresql+asyncpg://user:pass@pgbouncer:6432/corporate_intel"

# Reduce app pool size (PgBouncer handles pooling)
engine = create_async_engine(
    SQLALCHEMY_DATABASE_URI,
    pool_size=10,        # Reduced from 30
    max_overflow=5,      # Reduced from 20
)
```

---

## 4. Caching Strategies

### 4.1 Multi-Layer Cache Architecture

```
Request Flow:
1. Application Memory Cache (L1) - 50ms
2. Redis Cache (L2) - 1-5ms
3. Database (L3) - 10-50ms
```

**Implementation:**
```python
from functools import lru_cache
import pickle
from typing import Optional

class MultiLayerCache:
    def __init__(self, redis_client):
        self.redis = redis_client
        self._memory_cache = {}

    @lru_cache(maxsize=1000)
    async def get(self, key: str) -> Optional[dict]:
        # L1: Memory cache
        if key in self._memory_cache:
            return self._memory_cache[key]

        # L2: Redis
        cached = await self.redis.get(key)
        if cached:
            value = pickle.loads(cached)
            self._memory_cache[key] = value
            return value

        return None

    async def set(self, key: str, value: dict, ttl: int = 300):
        # Store in both layers
        self._memory_cache[key] = value
        await self.redis.setex(key, ttl, pickle.dumps(value))
```

### 4.2 Cache Warming

**Preload Hot Data:**
```python
async def warm_cache_on_startup():
    """Warm cache with frequently accessed data"""

    # Top 100 companies
    companies = await db.execute(
        select(Company)
        .order_by(Company.market_cap.desc())
        .limit(100)
    )
    for company in companies.scalars():
        cache_key = f"company:{company.id}"
        await cache.set(cache_key, company.dict(), ttl=3600)

    # Latest filings
    filings = await db.execute(
        select(Filing)
        .order_by(Filing.filing_date.desc())
        .limit(1000)
    )
    for filing in filings.scalars():
        cache_key = f"filing:{filing.id}"
        await cache.set(cache_key, filing.dict(), ttl=1800)

    logger.info("Cache warming completed")
```

### 4.3 Cache Invalidation

**Event-Based Invalidation:**
```python
from fastapi import BackgroundTasks

@app.post("/companies/{id}")
async def update_company(
    id: int,
    data: CompanyUpdate,
    background_tasks: BackgroundTasks
):
    # Update database
    company = await db.update_company(id, data)

    # Invalidate caches in background
    background_tasks.add_task(invalidate_company_caches, id)

    return company

async def invalidate_company_caches(company_id: int):
    """Invalidate all related cache keys"""
    patterns = [
        f"company:{company_id}",
        f"company:{company_id}:*",
        f"filings:company:{company_id}",
        f"metrics:company:{company_id}",
    ]
    for pattern in patterns:
        await cache.delete_pattern(pattern)
```

---

## 5. Load Testing

### 5.1 Load Testing Strategy

**Test Scenarios:**
```yaml
Baseline:
  Concurrent Users: 100
  Duration: 10 minutes
  Expected: < 100ms p95

Normal Load:
  Concurrent Users: 500
  Duration: 30 minutes
  Expected: < 200ms p95

Peak Load:
  Concurrent Users: 2000
  Duration: 15 minutes
  Expected: < 500ms p95, error rate < 1%

Stress Test:
  Concurrent Users: 5000
  Duration: 10 minutes
  Expected: Identify breaking point
```

### 5.2 Locust Load Tests

**locustfile.py:**
```python
from locust import HttpUser, task, between

class CorporateIntelUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def get_companies(self):
        self.client.get("/api/v1/companies?limit=20")

    @task(2)
    def get_company_detail(self):
        company_id = random.randint(1, 1000)
        self.client.get(f"/api/v1/companies/{company_id}")

    @task(1)
    def get_filings(self):
        company_id = random.randint(1, 1000)
        self.client.get(f"/api/v1/companies/{company_id}/filings")

    @task(1)
    def search_companies(self):
        self.client.get("/api/v1/companies/search?q=education")
```

**Run Load Test:**
```bash
# Install Locust
pip install locust

# Run test
locust -f locustfile.py \
    --host=https://api.corporate-intel.com \
    --users 1000 \
    --spawn-rate 50 \
    --run-time 10m \
    --html=loadtest_report.html
```

### 5.3 Database Load Testing

**pgbench Test:**
```bash
# Initialize test database
pgbench -i -s 100 corporate_intel_test

# Run benchmark (100 clients, 10 threads, 60 seconds)
pgbench -c 100 -j 10 -T 60 -r corporate_intel_test

# Custom SQL script
pgbench -c 100 -j 10 -T 60 -f custom_queries.sql corporate_intel_test
```

---

## 6. Monitoring & Profiling

### 6.1 Application Profiling

**py-spy for Production Profiling:**
```bash
# Install py-spy
pip install py-spy

# Profile running process
py-spy top --pid <API_PID>

# Generate flame graph
py-spy record -o profile.svg --pid <API_PID> --duration 60

# Profile specific endpoint
py-spy record -o api_endpoint.svg -- python -m pytest tests/api/test_companies.py
```

**Built-in Profiling Middleware:**
```python
from fastapi import Request
import time
import cProfile
import pstats
import io

@app.middleware("http")
async def profile_request(request: Request, call_next):
    if request.query_params.get("profile") == "true":
        profiler = cProfile.Profile()
        profiler.enable()

        response = await call_next(request)

        profiler.disable()
        s = io.StringIO()
        ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
        ps.print_stats(20)

        logger.info(f"Profile for {request.url}:\n{s.getvalue()}")
        return response
    else:
        return await call_next(request)
```

### 6.2 Database Query Profiling

**Enable pg_stat_statements:**
```sql
-- postgresql.conf
shared_preload_libraries = 'pg_stat_statements'
pg_stat_statements.track = all
pg_stat_statements.max = 10000

-- Create extension
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
```

**Monitor Slow Queries:**
```sql
-- Top 20 slowest queries
SELECT
    calls,
    total_time::numeric(10,2) as total_ms,
    mean_time::numeric(10,2) as mean_ms,
    max_time::numeric(10,2) as max_ms,
    stddev_time::numeric(10,2) as stddev_ms,
    LEFT(query, 100) as query_sample
FROM pg_stat_statements
WHERE mean_time > 100
ORDER BY total_time DESC
LIMIT 20;

-- Reset statistics
SELECT pg_stat_statements_reset();
```

### 6.3 Real-Time Performance Monitoring

**Prometheus Metrics:**
```python
from prometheus_client import Counter, Histogram, Gauge

# Request metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0]
)

# Database metrics
DB_POOL_SIZE = Gauge(
    'db_connection_pool_size',
    'Database connection pool size'
)

DB_POOL_CHECKED_OUT = Gauge(
    'db_connections_checked_out',
    'Number of database connections in use'
)

# Middleware to track metrics
@app.middleware("http")
async def track_metrics(request: Request, call_next):
    start_time = time.time()

    response = await call_next(request)

    duration = time.time() - start_time

    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()

    REQUEST_LATENCY.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)

    return response
```

**Grafana Dashboard Queries:**
```promql
# p95 latency by endpoint
histogram_quantile(0.95,
  rate(http_request_duration_seconds_bucket[5m])
)

# Request rate
rate(http_requests_total[5m])

# Error rate
rate(http_requests_total{status=~"5.."}[5m])
/ rate(http_requests_total[5m])
```

---

## Performance Optimization Checklist

### Pre-Deployment
- [ ] All database queries use indexes
- [ ] Connection pooling configured (PgBouncer)
- [ ] Redis caching enabled for hot paths
- [ ] API responses compressed (gzip)
- [ ] Static assets served from CDN
- [ ] Database queries profiled with EXPLAIN

### Load Testing
- [ ] Baseline load test passed (100 users)
- [ ] Normal load test passed (500 users)
- [ ] Peak load test passed (2000 users)
- [ ] Stress test identified breaking point
- [ ] Resource utilization < 70% at peak load

### Monitoring
- [ ] Prometheus metrics exported
- [ ] Grafana dashboards configured
- [ ] p95/p99 latency alerts set
- [ ] Database slow query logging enabled
- [ ] APM tool integrated (Sentry, DataDog)

---

**Document Version:** 1.0.0
**Next Review:** 2025-11-25
