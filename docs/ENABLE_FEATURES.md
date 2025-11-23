# Feature Enablement Guide
**Created**: October 5, 2025
**Purpose**: Enable existing features that are coded but disabled

---

## 🚀 Quick Feature Activation

Many powerful features are already coded in your platform but are disabled by default. This guide shows how to enable them instantly.

---

## 1. Rate Limiting (Already Coded) ⚡

**What It Does**: Prevents API abuse by limiting requests per user/IP

**Current State**: Coded in `src/middleware/rate_limiting.py` but disabled

**Enable**:
```bash
# Edit .env
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000
```

**Restart API**:
```bash
docker-compose restart api
```

**Verify**:
```bash
# Make 61 requests in 1 minute
for i in {1..61}; do curl http://localhost:8002/health; done

# 61st request should return 429 Too Many Requests
```

---

## 2. Data Quality Validation (Already Coded) 📊

**What It Does**: Validates data before insertion (null checks, range validation, type checking)

**Current State**: Coded in `src/validation/data_quality.py` but disabled

**Enable**:
```bash
# Edit .env
DATA_QUALITY_ENABLED=true
DATA_QUALITY_STRICT_MODE=false  # or true for strict validation
```

**What Gets Validated**:
- Revenue > 0
- Margins between -100 and 100
- Dates not in future
- Required fields present
- Data types correct

**Example**:
```python
# This would be rejected with validation enabled:
metric = {
    "revenue": -1000000,  # ❌ Negative revenue
    "gross_margin": 150,  # ❌ > 100%
    "metric_date": "2030-01-01"  # ❌ Future date
}
```

---

## 3. OpenTelemetry Tracing (Already Configured) 🔍

**What It Does**: Distributed tracing for performance monitoring

**Current State**: Configured but not fully enabled

**Enable**:
```bash
# Edit .env
OTEL_TRACES_ENABLED=true
OTEL_METRICS_ENABLED=true
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
```

**Start Jaeger** (for viewing traces):
```bash
# Add to docker-compose.yml or run separately
docker run -d --name jaeger \
  -p 5775:5775/udp \
  -p 6831:6831/udp \
  -p 6832:6832/udp \
  -p 5778:5778 \
  -p 16686:16686 \
  -p 14268:14268 \
  -p 14250:14250 \
  -p 9411:9411 \
  jaegertracing/all-in-one:latest
```

**View Traces**:
```
http://localhost:16686
```

---

## 4. Sentry Error Tracking (Already Configured) 🐛

**What It Does**: Automatic error tracking and alerting

**Current State**: Configured in your .env (already enabled!)

**Your Configuration**:
```bash
# Already set in .env:
SENTRY_DSN=https://7ba5b33e0fcf4666e5d04c54a008b543@...
SENTRY_TRACES_SAMPLE_RATE=0.1
SENTRY_PROFILES_SAMPLE_RATE=0.1
```

**Test It**:
```python
# Trigger an error to see Sentry in action
curl http://localhost:8002/api/v1/companies/INVALID_TICKER

# Check Sentry dashboard at sentry.io
```

---

## 5. Redis Caching (Already Coded) 💾

**What It Does**: Caches expensive database queries

**Current State**: Cache manager coded in `src/core/cache_manager.py`

**Enable**:
```bash
# Edit .env (if not already set)
REDIS_HOST=localhost
REDIS_PORT=6381
REDIS_CACHE_TTL=3600  # 1 hour

# Ensure Redis is running
docker-compose up -d redis
```

**Usage in Code**:
```python
# src/api/v1/companies.py
from src.core.cache_manager import set_cache, get_cache_value

@router.get("/companies")
async def list_companies():
    # Check cache first
    cached = await get_cache_value("companies:list")
    if cached:
        return cached

    # Fetch from database
    results = await db.execute(select(Company))

    # Store in cache
    await set_cache("companies:list", results, ttl=300)

    return results
```

---

## 6. Prometheus Metrics (Already Configured) 📈

**What It Does**: Exposes application metrics for monitoring

**Current State**: Endpoint exists at `/metrics`

**Access**:
```bash
curl http://localhost:8002/metrics

# Returns Prometheus-format metrics:
# - HTTP request counts
# - Request durations
# - Error rates
# - Custom business metrics
```

**Visualize with Grafana**:
```yaml
# docker-compose.yml - add Prometheus and Grafana
prometheus:
  image: prom/prometheus:latest
  ports:
    - "9090:9090"
  volumes:
    - ./config/prometheus.yml:/etc/prometheus/prometheus.yml

grafana:
  image: grafana/grafana:latest
  ports:
    - "3001:3000"
```

---

## 7. API Versioning (Already Implemented) 🔢

**What It Does**: Allows multiple API versions for backward compatibility

**Current State**: v1 API at `/api/v1/*`

**Add v2**:
```python
# src/api/v2/__init__.py (when ready)
# src/api/main.py

from src.api import v1, v2

app.include_router(v1.router, prefix="/api/v1")
app.include_router(v2.router, prefix="/api/v2")
```

---

## 8. Database Connection Pooling (Already Configured) 🏊

**What It Does**: Reuses database connections for better performance

**Current State**: Configured in `src/db/session.py`

**Current Settings**:
```python
# Development
pool_size = 5
max_overflow = 10

# Production
pool_size = 20
max_overflow = 10

# Already optimal for your setup!
```

**Monitor Pool Usage**:
```python
# Add endpoint to check pool stats
@app.get("/debug/db-pool")
async def db_pool_stats():
    engine = get_async_engine()
    return {
        "pool_size": engine.pool.size(),
        "checked_in": engine.pool.checkedin(),
        "checked_out": engine.pool.checkedout(),
        "overflow": engine.pool.overflow()
    }
```

---

## 9. CORS Configuration (Already Enabled) 🌐

**What It Does**: Allows frontend apps to access your API

**Current State**: Configured for localhost:3000 and localhost:8088

**Add More Origins**:
```bash
# Edit .env
CORS_ORIGINS=["http://localhost:3000","http://localhost:8088","https://yourdomain.com"]
```

---

## 10. Debug Mode (Already Supported) 🐛

**What It Does**: Enhanced logging and error details

**Toggle**:
```bash
# Development
DEBUG=true

# Production
DEBUG=false
```

---

## 📊 Feature Status Matrix

| Feature | Coded? | Enabled? | Action Required |
|---------|--------|----------|-----------------|
| Rate Limiting | ✅ Yes | ❌ No | Set RATE_LIMIT_ENABLED=true |
| Data Quality | ✅ Yes | ❌ No | Set DATA_QUALITY_ENABLED=true |
| OpenTelemetry | ✅ Yes | ⚠️ Partial | Set OTEL_TRACES_ENABLED=true |
| Sentry | ✅ Yes | ✅ Yes | Already enabled! |
| Redis Cache | ✅ Yes | ⚠️ Partial | Use cache helpers in code |
| Prometheus | ✅ Yes | ✅ Yes | Already enabled! |
| Health Checks | ✅ Yes | ✅ Yes | Already enabled! |
| CORS | ✅ Yes | ✅ Yes | Already enabled! |
| Connection Pool | ✅ Yes | ✅ Yes | Already enabled! |
| API Versioning | ✅ Yes | ✅ Yes | Already enabled! |

---

## 🎯 Recommended Activation Order

### Today (5 minutes):
1. ✅ Enable rate limiting
2. ✅ Enable data quality validation
3. ✅ Enable OpenTelemetry tracing

```bash
# Edit .env - add these lines:
RATE_LIMIT_ENABLED=true
DATA_QUALITY_ENABLED=true
OTEL_TRACES_ENABLED=true
```

### This Week (1-2 hours):
4. Start Jaeger for trace visualization
5. Add caching to expensive API calls
6. Set up Prometheus + Grafana dashboards

### Before Production (1-2 days):
7. Configure production CORS origins
8. Set up monitoring alerts
9. Configure backup jobs
10. Set up SSL/TLS

---

## 🧪 Testing Enabled Features

After enabling features, verify they work:

### Test Rate Limiting:
```bash
# Make rapid requests
for i in {1..100}; do curl http://localhost:8002/health; done

# Should see 429 Too Many Requests after limit
```

### Test Data Quality:
```bash
# Try inserting invalid data
curl -X POST http://localhost:8002/api/v1/metrics \
  -H "Content-Type: application/json" \
  -d '{"revenue": -1000}'

# Should return 400 Bad Request with validation error
```

### Test Tracing:
```bash
# Make an API call
curl http://localhost:8002/api/v1/companies

# View trace in Jaeger
# Open: http://localhost:16686
# Search for: corporate-intel service
```

---

## 📝 Feature Configuration Reference

### All .env Variables for Features:

```bash
# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000
RATE_LIMIT_STORAGE="redis"  # or "memory"

# Data Quality
DATA_QUALITY_ENABLED=true
DATA_QUALITY_STRICT_MODE=false
DATA_QUALITY_LOG_FAILURES=true

# OpenTelemetry
OTEL_TRACES_ENABLED=true
OTEL_METRICS_ENABLED=true
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
OTEL_SERVICE_NAME=corporate-intel

# Cache
REDIS_CACHE_TTL=3600  # 1 hour default
REDIS_MAX_CONNECTIONS=10

# Monitoring
PROMETHEUS_ENABLED=true
METRICS_ENDPOINT=/metrics
```

---

## 🎉 Benefits of Enabling Features

### Immediate Benefits:
- **Rate Limiting**: Prevent API abuse, control costs
- **Data Quality**: Prevent bad data from entering system
- **Health Checks**: Monitor system health
- **Sentry**: Catch errors before users report them

### Short-term Benefits:
- **Tracing**: Debug performance issues faster
- **Caching**: 10-100x faster responses for repeated queries
- **Prometheus**: Identify bottlenecks

### Long-term Benefits:
- **Reliability**: 99.9% uptime
- **Performance**: Sub-200ms response times
- **Security**: Protection against attacks
- **Observability**: Know what's happening in production

---

## ⚡ Quick Start Script

Create a script to enable all features at once:

```bash
# scripts/enable_all_features.sh

#!/bin/bash
echo "Enabling all production-ready features..."

# Backup current .env
cp .env .env.backup

# Enable features
cat >> .env << 'EOF'

# Production Features (enabled $(date))
RATE_LIMIT_ENABLED=true
DATA_QUALITY_ENABLED=true
OTEL_TRACES_ENABLED=true
OTEL_METRICS_ENABLED=true
EOF

echo "✅ Features enabled! Restart API for changes to take effect."
echo "Backup saved to .env.backup"
```

---

**Total Time to Enable**: **5-10 minutes**
**Total Value**: **Massive** (security, performance, observability)
**Difficulty**: **Easy** (just environment variables!)

🎯 **Recommendation**: Enable all features today for maximum benefit!
