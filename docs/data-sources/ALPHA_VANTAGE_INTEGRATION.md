# Alpha Vantage Integration Guide

**Corporate Intelligence Platform - Plan A Day 4**
**Created:** 2025-10-17
**Version:** 1.0.0

---

## Table of Contents

1. [Overview](#overview)
2. [API Configuration](#api-configuration)
3. [Rate Limiting](#rate-limiting)
4. [Data Workflows](#data-workflows)
5. [Database Schema](#database-schema)
6. [Error Handling](#error-handling)
7. [Caching Strategy](#caching-strategy)
8. [Monitoring](#monitoring)
9. [Cost Optimization](#cost-optimization)
10. [Production Deployment](#production-deployment)
11. [Troubleshooting](#troubleshooting)

---

## Overview

Alpha Vantage provides comprehensive financial data including:

- **Market Data**: Real-time and historical stock prices
- **Fundamentals**: Company overview, financial statements
- **Technical Indicators**: SMA, EMA, RSI, MACD, etc.
- **Economic Indicators**: GDP, inflation, unemployment
- **Forex & Crypto**: Exchange rates and cryptocurrency data

### Key Features

- **Free Tier Available**: 5 API calls/minute, 500 calls/day
- **Premium Tiers**: Up to 1200 calls/day with higher rate limits
- **JSON/CSV Output**: Flexible data formats
- **RESTful API**: Simple HTTP GET requests
- **No Authentication Header**: API key in query parameter

### Integration Architecture

```
┌─────────────────────────────────────────────────────────┐
│               Alpha Vantage Integration                 │
└─────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
   ┌────▼────┐        ┌─────▼─────┐      ┌─────▼─────┐
   │ Stock   │        │ Fundamental│      │Technical  │
   │ Prices  │        │    Data    │      │Indicators │
   └────┬────┘        └─────┬─────┘      └─────┬─────┘
        │                   │                   │
        │         ┌─────────▼─────────┐         │
        │         │   Rate Limiter    │         │
        │         │  (5 calls/min)    │         │
        │         └─────────┬─────────┘         │
        │                   │                   │
        └───────────────────┼───────────────────┘
                            │
                    ┌───────▼───────┐
                    │ Redis Cache   │
                    │ (1-7 day TTL) │
                    └───────┬───────┘
                            │
                    ┌───────▼───────┐
                    │  PostgreSQL   │
                    │ financial_    │
                    │   metrics     │
                    └───────────────┘
```

---

## API Configuration

### Authentication

Alpha Vantage uses API key authentication via query parameter:

```bash
https://www.alphavantage.co/query?function=OVERVIEW&symbol=IBM&apikey=YOUR_API_KEY
```

**Get Your API Key:**
1. Visit: https://www.alphavantage.co/support/#api-key
2. Sign up for free or purchase premium tier
3. Store key securely in environment variables

### Environment Setup

**Development (.env):**
```bash
ALPHA_VANTAGE_API_KEY=demo  # Use 'demo' for testing
ALPHA_VANTAGE_TIER=free
```

**Production (.env.production):**
```bash
ALPHA_VANTAGE_API_KEY=YOUR_PREMIUM_KEY_HERE
ALPHA_VANTAGE_TIER=premium
REDIS_HOST=redis.production.internal
REDIS_PASSWORD=secure_redis_password
```

### Configuration File

Production settings are defined in:
```
config/production/alpha-vantage-config.yml
```

Key sections:
- **API Settings**: Base URL, timeout, retries
- **Rate Limits**: Free/Premium tier limits
- **Endpoints**: Available data functions
- **Caching**: Redis configuration
- **Monitoring**: Prometheus metrics

---

## Rate Limiting

### Free Tier (Default)

- **5 API calls per minute** (12-second intervals)
- **500 API calls per day**
- **No burst allowance**

**Implementation:**
```python
from src.connectors.data_sources import AlphaVantageConnector

connector = AlphaVantageConnector()
# Rate limiter built-in: 5 calls/60 seconds

# Sequential processing with delays
for ticker in tickers:
    data = await connector.get_company_overview(ticker)
    await asyncio.sleep(12)  # Respect rate limit
```

### Premium Tier

- **75 API calls per minute** (1-second intervals)
- **1,200 API calls per day**
- **Burst allowance: 5 calls**

**Upgrade Benefits:**
- 15x more calls per minute
- 2.4x more daily calls
- Faster data ingestion
- Priority support

### Rate Limit Handling

**Automatic Detection:**
```yaml
# config/production/alpha-vantage-config.yml
rate_limits:
  enforcement:
    adaptive: true  # Adjust based on 429 responses
    backoff_on_429: true
    backoff_multiplier: 2
```

**HTTP 429 Response:**
```python
# Automatic retry with exponential backoff
# Attempt 1: Wait 4 seconds
# Attempt 2: Wait 8 seconds
# Attempt 3: Wait 16 seconds
# Max: 3 attempts, then fail
```

---

## Data Workflows

### 1. Stock Price Ingestion

**Schedule:** Daily at 5 PM (market close)
**Endpoint:** `TIME_SERIES_DAILY`
**Target:** All EdTech companies

```python
# src/pipeline/alpha_vantage_ingestion.py
from src.connectors.data_sources import AlphaVantageConnector

async def ingest_stock_prices():
    connector = AlphaVantageConnector()

    for ticker in EDTECH_TICKERS:
        # Fetch daily OHLCV data
        data = await connector.get_time_series_daily(ticker)

        # Store in stock_prices table
        await store_stock_prices(ticker, data)

        # Rate limit delay
        await asyncio.sleep(12)
```

**Data Structure:**
```json
{
  "Meta Data": {
    "1. Information": "Daily Prices (open, high, low, close) and Volumes",
    "2. Symbol": "CHGG",
    "3. Last Refreshed": "2025-10-17",
    "4. Output Size": "Compact",
    "5. Time Zone": "US/Eastern"
  },
  "Time Series (Daily)": {
    "2025-10-17": {
      "1. open": "15.2500",
      "2. high": "15.5000",
      "3. low": "15.1000",
      "4. close": "15.4500",
      "5. volume": "1234567"
    }
  }
}
```

### 2. Fundamental Data Ingestion

**Schedule:** Weekly on Saturday at 6 PM
**Endpoints:** Multiple (overview, income, balance sheet, cash flow)
**Target:** EdTech companies only

```python
async def ingest_fundamentals():
    connector = AlphaVantageConnector()

    for ticker in EDTECH_TICKERS:
        # Company overview
        overview = await connector.get_company_overview(ticker)
        await store_financial_metrics(ticker, overview)

        # Income statement
        income = await connector.get_income_statement(ticker)
        await store_financial_statements(ticker, income)

        # Rate limit between endpoints
        await asyncio.sleep(2)
```

**Metrics Collected:**

| Category | Metrics |
|----------|---------|
| **Valuation** | P/E, PEG, Price-to-Book, Price-to-Sales, EV/Revenue, EV/EBITDA |
| **Profitability** | EPS, ROE, Profit Margin, Operating Margin, ROA |
| **Growth** | Revenue Growth YoY, Earnings Growth YoY |
| **Size** | Market Cap, Enterprise Value |
| **Income** | Dividend Yield |

### 3. Technical Indicators (Optional)

**Schedule:** Daily at 7 PM (disabled by default)
**Indicators:** SMA, EMA, RSI, MACD
**Target:** EdTech companies

```python
async def ingest_technical_indicators():
    connector = AlphaVantageConnector()

    for ticker in EDTECH_TICKERS:
        # Simple Moving Average (20-day)
        sma = await connector.get_sma(ticker, interval='daily', time_period=20)

        # Relative Strength Index (14-day)
        rsi = await connector.get_rsi(ticker, interval='daily', time_period=14)

        await store_technical_indicators(ticker, sma, rsi)
        await asyncio.sleep(12)
```

---

## Database Schema

### Financial Metrics Table

**Table:** `financial_metrics`

```sql
CREATE TABLE financial_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id),
    metric_date TIMESTAMP WITH TIME ZONE NOT NULL,
    period_type VARCHAR(20) NOT NULL,  -- 'quarterly', 'annual'
    metric_type VARCHAR(50) NOT NULL,   -- 'pe_ratio', 'eps', etc.
    metric_category VARCHAR(30) NOT NULL,  -- 'valuation', 'profitability'
    value DECIMAL(20, 4) NOT NULL,
    unit VARCHAR(20) NOT NULL,  -- 'USD', 'percent', 'ratio'
    source VARCHAR(50) NOT NULL,  -- 'alpha_vantage'
    confidence_score DECIMAL(3, 2) DEFAULT 0.95,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Unique constraint: one metric per company/date/type
    UNIQUE(company_id, metric_type, metric_date, period_type)
);

CREATE INDEX idx_financial_metrics_company ON financial_metrics(company_id);
CREATE INDEX idx_financial_metrics_date ON financial_metrics(metric_date);
CREATE INDEX idx_financial_metrics_type ON financial_metrics(metric_type);
CREATE INDEX idx_financial_metrics_source ON financial_metrics(source);
```

### Field Mappings

**Alpha Vantage → Database:**

```yaml
# config/production/alpha-vantage-config.yml
database:
  financial_metrics:
    field_mappings:
      PERatio: {column: "pe_ratio", category: "valuation", unit: "ratio"}
      EPS: {column: "eps", category: "profitability", unit: "USD"}
      ReturnOnEquityTTM: {column: "roe", category: "profitability", unit: "percent"}
      QuarterlyRevenueGrowthYOY: {column: "revenue_growth_yoy", category: "growth", unit: "percent"}
      MarketCapitalization: {column: "market_cap", category: "size", unit: "USD"}
```

### Upsert Logic

**PostgreSQL ON CONFLICT:**
```sql
INSERT INTO financial_metrics (
    company_id, metric_date, period_type, metric_type,
    metric_category, value, unit, source, confidence_score
)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
ON CONFLICT (company_id, metric_type, metric_date, period_type)
DO UPDATE SET
    value = EXCLUDED.value,
    confidence_score = EXCLUDED.confidence_score,
    updated_at = NOW()
RETURNING id;
```

**Benefits:**
- Avoids duplicate entries
- Updates changed metrics
- Atomic operation (no race conditions)
- Returns inserted/updated ID

---

## Error Handling

### Error Categories

1. **Retryable Errors** (Auto-retry with backoff)
   - `ClientError` - Network issues
   - `TimeoutError` - Request timeout
   - `HTTPStatus.429` - Rate limit exceeded
   - `HTTPStatus.500/502/503` - Server errors

2. **Non-Retryable Errors** (Fail immediately)
   - `ValueError` - Data quality issues
   - `HTTPStatus.400` - Bad request
   - `HTTPStatus.401` - Invalid API key
   - `HTTPStatus.404` - Symbol not found

### Retry Strategy

**Exponential Backoff:**
```python
async def ingest_with_retry(ticker: str, max_attempts: int = 3):
    attempt = 0

    while attempt < max_attempts:
        try:
            data = await connector.get_company_overview(ticker)
            return data

        except (ClientError, TimeoutError) as e:
            attempt += 1
            if attempt >= max_attempts:
                raise

            # Exponential backoff: 4s, 8s, 16s
            wait_time = 4 * (2 ** (attempt - 1))
            logger.warning(f"{ticker}: Retry {attempt}/{max_attempts} in {wait_time}s")
            await asyncio.sleep(wait_time)
```

### Error Responses

**API Error Response:**
```json
{
  "Error Message": "Invalid API call. Please retry or visit the documentation...",
  "Note": "Thank you for using Alpha Vantage! Our standard API call frequency is 5 calls per minute..."
}
```

**Handling:**
```python
if 'Error Message' in response:
    if 'frequency' in response.get('Note', ''):
        # Rate limit error
        raise RateLimitError(response['Error Message'])
    else:
        # Other API error
        raise APIError(response['Error Message'])
```

### Fallback Behavior

**Configuration:**
```yaml
# config/production/alpha-vantage-config.yml
error_handling:
  fallback:
    use_cached_data: true
    cache_stale_threshold_hours: 48
    return_partial_results: true
```

**Implementation:**
```python
try:
    data = await connector.get_company_overview(ticker)
except APIError:
    # Try cached data if available
    cached = await cache.get(f"alpha_vantage:{ticker}")

    if cached and cache_age < 48_hours:
        logger.warning(f"{ticker}: Using cached data (age: {cache_age}h)")
        return cached
    else:
        raise  # No valid fallback
```

---

## Caching Strategy

### Redis Configuration

**Production Setup:**
```yaml
# config/production/alpha-vantage-config.yml
caching:
  enabled: true
  backend: "redis"

  redis:
    host: "${REDIS_HOST:localhost}"
    port: 6379
    db: 2  # Dedicated DB for Alpha Vantage
    password: "${REDIS_PASSWORD:}"
    key_prefix: "alpha_vantage:"
```

### TTL Policies

| Data Type | TTL | Rationale |
|-----------|-----|-----------|
| **Real-time prices** | 5 minutes | High volatility |
| **Daily OHLC** | 1 hour | Updates once per day |
| **Company overview** | 24 hours | Changes infrequently |
| **Financial statements** | 7 days | Quarterly updates |

**Implementation:**
```python
@cache_key_wrapper(prefix="alpha_vantage", expire=3600)
async def get_company_overview(ticker: str):
    # Cached for 1 hour
    return await self._fetch_overview(ticker)
```

### Cache Keys

**Format:** `alpha_vantage:{function}:{symbol}:{params}`

**Examples:**
```
alpha_vantage:overview:CHGG
alpha_vantage:time_series_daily:COUR:compact
alpha_vantage:sma:DUOL:daily:20
```

### Invalidation

**Manual Invalidation:**
```bash
# Clear specific company
redis-cli DEL "alpha_vantage:overview:CHGG"

# Clear all Alpha Vantage cache
redis-cli --scan --pattern "alpha_vantage:*" | xargs redis-cli DEL
```

**Automatic Invalidation:**
- On error response (bad data)
- On 401/403 (authentication issue)
- On user request (force refresh)

### Cache Metrics

**Monitor via Prometheus:**
```
alpha_vantage_cache_hit_rate{function="overview"} 0.85
alpha_vantage_cache_size_bytes 524288000
alpha_vantage_cache_evictions_total 42
```

---

## Monitoring

### Prometheus Metrics

**API Metrics:**
```
# Total API calls
alpha_vantage_api_calls_total{status="success"} 450
alpha_vantage_api_calls_total{status="error"} 10
alpha_vantage_api_calls_total{status="rate_limited"} 5

# Request duration
alpha_vantage_request_duration_seconds{function="overview",quantile="0.5"} 0.8
alpha_vantage_request_duration_seconds{function="overview",quantile="0.95"} 1.2
alpha_vantage_request_duration_seconds{function="overview",quantile="0.99"} 2.1

# Rate limit usage
alpha_vantage_rate_limit_remaining{tier="free"} 45
alpha_vantage_daily_quota_used{tier="free"} 455
alpha_vantage_daily_quota_remaining{tier="free"} 45
```

**Business Metrics:**
```
# Companies processed
alpha_vantage_companies_processed_total{source="alpha_vantage"} 27

# Metrics collected
alpha_vantage_metrics_collected_total{category="valuation"} 216
alpha_vantage_metrics_collected_total{category="profitability"} 135

# Data coverage
alpha_vantage_data_coverage_percent{ticker="CHGG"} 95.0
```

### Logging

**Structured Logging:**
```python
logger.info(
    "Alpha Vantage ingestion completed",
    extra={
        "ticker": ticker,
        "metrics_fetched": 16,
        "metrics_stored": 14,
        "duration_seconds": 1.2,
        "api_calls": 1,
        "cache_hit": False
    }
)
```

**Log Levels:**
- **DEBUG**: API requests/responses, cache operations
- **INFO**: Ingestion progress, metrics stored
- **WARNING**: Rate limits, retries, cached data used
- **ERROR**: API failures, data validation errors

### Alerts

**Prometheus Alert Rules:**
```yaml
# config/production/prometheus/alerts/alpha-vantage-alerts.yml
groups:
  - name: alpha_vantage
    interval: 1m
    rules:
      - alert: AlphaVantageHighErrorRate
        expr: rate(alpha_vantage_api_calls_total{status="error"}[5m]) > 0.1
        for: 5m
        annotations:
          summary: "High error rate on Alpha Vantage API"

      - alert: AlphaVantageDailyQuotaExceeded
        expr: alpha_vantage_daily_quota_remaining < 50
        annotations:
          summary: "Alpha Vantage daily quota running low"

      - alert: AlphaVantageRateLimitExceeded
        expr: rate(alpha_vantage_api_calls_total{status="rate_limited"}[1m]) > 0
        for: 1m
        annotations:
          summary: "Alpha Vantage rate limit exceeded"
```

---

## Cost Optimization

### Free Tier Optimization

**Daily Budget:** 500 API calls

**Allocation Strategy:**
```
Stock Prices (Daily):     27 companies × 1 call = 27 calls
Company Overview (Weekly): 27 companies ÷ 7 days = 4 calls/day
Financial Statements:      Save for weekends

Total daily usage: ~31 calls (6% of quota)
```

### Premium Tier ROI

**Free Tier:**
- 500 calls/day = 15,000 calls/month
- Cost: $0
- Limitations: Slow ingestion, no real-time

**Premium Tier ($49.99/month):**
- 1,200 calls/day = 36,000 calls/month
- 15x faster rate limit (75/min vs 5/min)
- Real-time data access
- Priority support

**Break-Even Analysis:**
```
If you need > 500 calls/day → Premium required
If you need < 500 calls/day → Free tier sufficient

Current usage (27 EdTech companies):
- Daily: ~100 calls (with all features)
- Monthly: ~3,000 calls
→ Free tier is sufficient
```

### Caching Impact

**Without Caching:**
```
27 companies × 4 metrics/day × 30 days = 3,240 calls/month
Cost: Free tier sufficient, but nearing limit
```

**With Caching (24-hour TTL):**
```
27 companies × 1 call/day × 30 days = 810 calls/month
Savings: 75% reduction in API calls
Cost: Well within free tier
```

### Batching Optimization

**Sequential Processing:**
```python
# Free tier: 5 calls/min = 1 call every 12s
for ticker in tickers:
    await fetch(ticker)
    await asyncio.sleep(12)  # 27 companies × 12s = 5.4 minutes
```

**Premium Tier:**
```python
# Premium: 75 calls/min = 1 call every 0.8s
for ticker in tickers:
    await fetch(ticker)
    await asyncio.sleep(1)  # 27 companies × 1s = 27 seconds
```

**Speedup:** 12x faster with premium tier

---

## Production Deployment

### Prerequisites

1. **Alpha Vantage API Key**
   - Get premium key from: https://www.alphavantage.co/premium/
   - Store in `.env.production`

2. **Redis (for caching)**
   ```bash
   docker run -d --name redis-alpha-vantage \
     -p 6379:6379 \
     -v redis-data:/data \
     redis:7-alpine redis-server --appendonly yes
   ```

3. **PostgreSQL (database)**
   - Ensure `financial_metrics` table exists
   - Run migrations: `alembic upgrade head`

### Environment Configuration

**File:** `.env.production`
```bash
# Alpha Vantage API
ALPHA_VANTAGE_API_KEY=your_premium_key_here
ALPHA_VANTAGE_TIER=premium

# Redis Cache
REDIS_HOST=redis.production.internal
REDIS_PORT=6379
REDIS_DB=2
REDIS_PASSWORD=secure_password_here

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/corporate_intel

# Monitoring
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=9091
```

### Deployment Steps

**1. Install Dependencies**
```bash
pip install -r requirements.txt
```

**2. Run Database Migrations**
```bash
alembic upgrade head
```

**3. Verify Configuration**
```bash
python -c "
from src.core.config import get_settings
settings = get_settings()
assert settings.ALPHA_VANTAGE_API_KEY, 'API key not set'
print('✓ Configuration valid')
"
```

**4. Test API Connectivity**
```bash
python scripts/data-ingestion/test-alpha-vantage.py
```

**5. Run Initial Ingestion**
```bash
python scripts/data-ingestion/ingest-alpha-vantage.py --test-mode
```

**6. Schedule Cron Jobs**
```bash
# Add to crontab
0 17 * * 1-5 /app/scripts/data-ingestion/ingest-alpha-vantage.py --workflow=stock_prices
0 18 * * 6 /app/scripts/data-ingestion/ingest-alpha-vantage.py --workflow=fundamentals
```

### Docker Deployment

**Dockerfile:**
```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "scripts/data-ingestion/ingest-alpha-vantage.py"]
```

**Docker Compose:**
```yaml
# config/production/docker-compose.production.yml
services:
  alpha-vantage-ingestion:
    build: .
    env_file: .env.production
    depends_on:
      - postgres
      - redis
    volumes:
      - ./logs:/var/log/corporate_intel
    restart: unless-stopped
```

---

## Troubleshooting

### Common Issues

#### 1. "API key not configured"

**Symptoms:**
```
ERROR | Alpha Vantage API key not configured. Please set ALPHA_VANTAGE_API_KEY in .env
```

**Solution:**
```bash
# Check .env file
cat .env | grep ALPHA_VANTAGE_API_KEY

# Set API key
echo "ALPHA_VANTAGE_API_KEY=your_key_here" >> .env

# Verify
python -c "import os; print(os.getenv('ALPHA_VANTAGE_API_KEY'))"
```

#### 2. Rate Limit Exceeded

**Symptoms:**
```
WARNING | CHGG: Rate limit exceeded (HTTP 429) - retrying in 4s
```

**Solution:**
```bash
# Check current tier
cat .env | grep ALPHA_VANTAGE_TIER

# Adjust delay between calls
# Edit config/production/alpha-vantage-config.yml
rate_limits:
  free:
    min_delay_seconds: 15  # Increase from 12 to 15
```

#### 3. No Data Returned

**Symptoms:**
```
WARNING | CHGG: No valid metrics returned from API or stored
```

**Possible Causes:**
- Invalid ticker symbol
- Market holiday (no trading data)
- API returned empty response

**Debug:**
```bash
# Test API directly
curl "https://www.alphavantage.co/query?function=OVERVIEW&symbol=CHGG&apikey=YOUR_KEY"

# Check response
python -c "
import asyncio
from src.connectors.data_sources import AlphaVantageConnector

async def test():
    connector = AlphaVantageConnector()
    data = await connector.get_company_overview('CHGG')
    print(data)

asyncio.run(test())
"
```

#### 4. Database Connection Error

**Symptoms:**
```
ERROR | Failed to get/create company record - database_error
```

**Solution:**
```bash
# Test database connection
python -c "
import asyncio
from src.db.session import get_session_factory

async def test():
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute('SELECT 1')
        print('✓ Database connected')

asyncio.run(test())
"

# Check DATABASE_URL
cat .env | grep DATABASE_URL
```

#### 5. Cache Connection Error

**Symptoms:**
```
WARNING | Redis connection failed, falling back to no-cache mode
```

**Solution:**
```bash
# Test Redis connection
redis-cli -h localhost -p 6379 -a your_password PING

# Check Redis configuration
cat .env | grep REDIS

# Restart Redis
docker restart redis-alpha-vantage
```

### Debug Mode

**Enable verbose logging:**
```bash
# Set log level to DEBUG
export LOG_LEVEL=DEBUG

# Run ingestion
python src/pipeline/alpha_vantage_ingestion.py
```

**Check logs:**
```bash
# View real-time logs
tail -f /var/log/corporate_intel/alpha_vantage.log

# Search for errors
grep ERROR /var/log/corporate_intel/alpha_vantage.log

# Filter by ticker
grep "CHGG" /var/log/corporate_intel/alpha_vantage.log
```

---

## API Reference

### Core Endpoints

#### Company Overview
```python
GET /query?function=OVERVIEW&symbol={TICKER}&apikey={API_KEY}

Response:
{
  "Symbol": "CHGG",
  "AssetType": "Common Stock",
  "Name": "Chegg Inc",
  "MarketCapitalization": "1200000000",
  "PERatio": "18.5",
  "PEGRatio": "1.2",
  "EPS": "0.85",
  ...
}
```

#### Time Series Daily
```python
GET /query?function=TIME_SERIES_DAILY&symbol={TICKER}&apikey={API_KEY}

Response:
{
  "Time Series (Daily)": {
    "2025-10-17": {
      "1. open": "15.25",
      "2. high": "15.50",
      "3. low": "15.10",
      "4. close": "15.45",
      "5. volume": "1234567"
    }
  }
}
```

#### Income Statement
```python
GET /query?function=INCOME_STATEMENT&symbol={TICKER}&apikey={API_KEY}

Response:
{
  "symbol": "CHGG",
  "annualReports": [...],
  "quarterlyReports": [
    {
      "fiscalDateEnding": "2025-09-30",
      "totalRevenue": "200000000",
      "grossProfit": "150000000",
      "netIncome": "20000000"
    }
  ]
}
```

### Python Client

```python
from src.connectors.data_sources import AlphaVantageConnector

# Initialize connector
connector = AlphaVantageConnector()

# Fetch company overview
overview = await connector.get_company_overview('CHGG')

# Fetch time series
prices = await connector.get_time_series_daily('CHGG')

# Fetch financials
income = await connector.get_income_statement('CHGG')
balance = await connector.get_balance_sheet('CHGG')
cash_flow = await connector.get_cash_flow('CHGG')

# Technical indicators
sma = await connector.get_sma('CHGG', interval='daily', time_period=20)
rsi = await connector.get_rsi('CHGG', interval='daily', time_period=14)
```

---

## Support & Resources

### Official Documentation
- **Alpha Vantage Docs**: https://www.alphavantage.co/documentation/
- **API Support**: https://www.alphavantage.co/support/
- **Pricing**: https://www.alphavantage.co/premium/

### Internal Resources
- **Configuration**: `config/production/alpha-vantage-config.yml`
- **Source Code**: `src/connectors/data_sources.py`
- **Ingestion Script**: `src/pipeline/alpha_vantage_ingestion.py`
- **Tests**: `tests/integration/test_alpha_vantage_production.py`

### Contact
- **Platform Team**: platform@corporate-intel.internal
- **Data Engineering**: data-eng@corporate-intel.internal
- **On-Call**: +1-555-DATA-OPS

---

**Last Updated:** 2025-10-17
**Maintained By:** Data Engineering Team
**Version:** 1.0.0
