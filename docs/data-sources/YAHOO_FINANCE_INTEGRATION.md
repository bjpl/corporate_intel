# Yahoo Finance Integration Guide

## Overview

Yahoo Finance integration provides real-time and historical market data for the Corporate Intelligence Platform using the unofficial yfinance Python library. This integration enables tracking of stock prices, company fundamentals, financial statements, and market trends.

## Features

- Real-time stock quotes
- Historical price data
- Company information and fundamentals
- Financial statements (Income, Balance Sheet, Cash Flow)
- Analyst recommendations
- Institutional holders
- Earnings data
- Options data (optional)
- Market indices tracking

## API Details

- **Provider**: Yahoo Finance (Unofficial)
- **Library**: yfinance (Python)
- **Authentication**: None required
- **Documentation**: https://github.com/ranaroussi/yfinance

## Important Notes

### Unofficial API

Yahoo Finance data is accessed through the **unofficial** yfinance library:

- ✓ No API key required
- ✓ Free to use
- ✓ Real-time data
- ⚠ No official support
- ⚠ May break without notice
- ⚠ Subject to rate limiting
- ⚠ Terms of service considerations

### Best Practices

1. **Implement conservative rate limiting** (30 requests/minute recommended)
2. **Use caching** to minimize requests
3. **Have backup data sources** (Alpha Vantage, SEC)
4. **Monitor for API changes** and service disruptions
5. **Don't abuse the service** - it's provided freely

## Configuration

### Environment Variables

```bash
# Optional - only for database storage
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=corporate_intel
POSTGRES_USER=intel_user
POSTGRES_PASSWORD=your-password

# Yahoo Finance specific
YAHOO_FINANCE_ENABLED=true
```

### Configuration File

Location: `/config/production/data-sources/yahoo-finance-config.yml`

Key settings:
- Data types to fetch (quotes, historical, info, financials)
- Rate limiting parameters
- Caching configuration
- Watchlist tickers
- Quality validation rules
- Backup data sources

## Getting Started

### 1. Install Dependencies

```bash
pip install yfinance pandas pyyaml psycopg2-binary
```

### 2. Test Connectivity

```bash
python scripts/test-yahoo-finance-connectivity.py
```

Expected output:
- ✓ Quote data fetched successfully
- ✓ Historical data retrieved
- ✓ Company information available
- ✓ Multiple tickers working
- ✓ Market indices accessible

### 3. Verify Installation

```python
import yfinance as yf

# Test basic functionality
ticker = yf.Ticker("CHGG")
info = ticker.info
print(f"Company: {info.get('longName')}")
print(f"Price: ${info.get('regularMarketPrice')}")
```

## Usage

### Command-Line Interface

#### Fetch Data for a Single Ticker

```bash
python scripts/data-ingestion/ingest-yahoo-finance.py --ticker CHGG
```

#### Fetch All Data Types

```bash
python scripts/data-ingestion/ingest-yahoo-finance.py --ticker CHGG --full
```

#### Custom Historical Period

```bash
python scripts/data-ingestion/ingest-yahoo-finance.py --ticker CHGG --period 5y
```

#### Process All Watchlist Tickers

```bash
python scripts/data-ingestion/ingest-yahoo-finance.py --all-watchlist
```

### Python API

```python
from scripts.data_ingestion.ingest_yahoo_finance import YahooFinanceIngestionPipeline

# Initialize pipeline
pipeline = YahooFinanceIngestionPipeline()

# Fetch quote data
quote = pipeline.fetch_quote('CHGG')

# Fetch historical data
hist = pipeline.fetch_historical('CHGG', period='1y', interval='1d')

# Fetch company info
info = pipeline.fetch_company_info('CHGG')

# Fetch financials
financials = pipeline.fetch_financials('CHGG')

# Store in database
pipeline.store_quote(quote)
pipeline.store_historical(hist, 'CHGG')
pipeline.store_company_info(info)

# Print statistics
pipeline.print_stats()

# Clean up
pipeline.close()
```

## Data Types

### 1. Real-Time Quotes

Current market data:

```python
import yfinance as yf

stock = yf.Ticker("CHGG")
info = stock.info

quote = {
    'price': info['regularMarketPrice'],
    'change': info['regularMarketChange'],
    'change_percent': info['regularMarketChangePercent'],
    'volume': info['regularMarketVolume'],
    'market_cap': info['marketCap'],
    'pe_ratio': info.get('trailingPE'),
    'beta': info.get('beta')
}
```

### 2. Historical Data

Price and volume history:

```python
# Available periods: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
# Available intervals: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo

stock = yf.Ticker("CHGG")
hist = stock.history(period="1y", interval="1d")

# Returns DataFrame with:
# - Date (index)
# - Open, High, Low, Close
# - Volume
# - Dividends
# - Stock Splits
```

### 3. Company Information

Fundamentals and metadata:

```python
stock = yf.Ticker("CHGG")
info = stock.info

company_data = {
    'name': info['longName'],
    'sector': info['sector'],
    'industry': info['industry'],
    'employees': info['fullTimeEmployees'],
    'website': info['website'],
    'summary': info['longBusinessSummary'],
    'market_cap': info['marketCap'],
    'beta': info['beta']
}
```

### 4. Financial Statements

```python
stock = yf.Ticker("CHGG")

# Income Statement
income_stmt = stock.financials          # Annual
income_stmt_q = stock.quarterly_financials  # Quarterly

# Balance Sheet
balance_sheet = stock.balance_sheet     # Annual
balance_sheet_q = stock.quarterly_balance_sheet  # Quarterly

# Cash Flow
cashflow = stock.cashflow               # Annual
cashflow_q = stock.quarterly_cashflow   # Quarterly
```

### 5. Other Data Types

```python
# Analyst recommendations
recommendations = stock.recommendations

# Institutional holders
inst_holders = stock.institutional_holders

# Major holders
major_holders = stock.major_holders

# Earnings dates
earnings = stock.earnings_dates

# Options (if enabled)
options = stock.options  # Available dates
chain = stock.option_chain('2024-12-20')
```

## Data Schema

### yahoo_quotes Table

```sql
CREATE TABLE yahoo_quotes (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    regular_market_price NUMERIC,
    regular_market_change NUMERIC,
    regular_market_change_percent NUMERIC,
    regular_market_volume BIGINT,
    market_cap BIGINT,
    fifty_two_week_low NUMERIC,
    fifty_two_week_high NUMERIC,
    fifty_day_average NUMERIC,
    two_hundred_day_average NUMERIC,
    trailing_pe NUMERIC,
    forward_pe NUMERIC,
    dividend_yield NUMERIC,
    beta NUMERIC,
    fetched_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### yahoo_historical Table

```sql
CREATE TABLE yahoo_historical (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    date TIMESTAMP NOT NULL,
    open NUMERIC,
    high NUMERIC,
    low NUMERIC,
    close NUMERIC,
    volume BIGINT,
    dividends NUMERIC,
    stock_splits NUMERIC,
    fetched_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ticker, date)
);
```

### yahoo_company_info Table

```sql
CREATE TABLE yahoo_company_info (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(10) UNIQUE NOT NULL,
    short_name VARCHAR(255),
    long_name VARCHAR(255),
    sector VARCHAR(100),
    industry VARCHAR(100),
    full_time_employees INTEGER,
    city VARCHAR(100),
    state VARCHAR(100),
    country VARCHAR(100),
    website VARCHAR(255),
    business_summary TEXT,
    market_cap BIGINT,
    beta NUMERIC,
    trailing_pe NUMERIC,
    forward_pe NUMERIC,
    dividend_rate NUMERIC,
    dividend_yield NUMERIC,
    recommendation_key VARCHAR(50),
    fetched_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Rate Limiting

### Recommended Limits

Since Yahoo Finance is unofficial with no documented limits:

```python
# Conservative approach
REQUESTS_PER_MINUTE = 30
REQUESTS_PER_HOUR = 1000
REQUEST_DELAY = 1  # seconds between requests

# Implementation
import time

def fetch_with_rate_limit(ticker):
    data = fetch_data(ticker)
    time.sleep(REQUEST_DELAY)
    return data
```

### Adaptive Rate Limiting

```python
class AdaptiveRateLimiter:
    def __init__(self):
        self.consecutive_failures = 0
        self.delay = 1

    def on_success(self):
        self.consecutive_failures = 0
        self.delay = max(1, self.delay * 0.9)

    def on_failure(self):
        self.consecutive_failures += 1
        if self.consecutive_failures > 3:
            self.delay = min(60, self.delay * 2)

    def wait(self):
        time.sleep(self.delay)
```

## Error Handling

### Common Errors

#### 1. No Data Available

```python
import yfinance as yf

stock = yf.Ticker("INVALID")
info = stock.info

if not info or 'regularMarketPrice' not in info:
    print("Invalid ticker or no data available")
```

#### 2. Rate Limiting

```python
try:
    stock = yf.Ticker("CHGG")
    data = stock.history(period="1y")
except Exception as e:
    if "429" in str(e) or "rate" in str(e).lower():
        print("Rate limited - backing off")
        time.sleep(60)
    else:
        raise
```

#### 3. Network Issues

```python
from requests.exceptions import RequestException

try:
    stock = yf.Ticker("CHGG")
    data = stock.info
except RequestException as e:
    logger.error(f"Network error: {e}")
    # Implement retry with exponential backoff
```

## Caching Strategy

### Redis Cache Example

```python
import redis
import json

cache = redis.Redis(host='localhost', port=6379, db=0)

def get_quote_cached(ticker, ttl=300):
    cache_key = f"yahoo:quote:{ticker}"

    # Check cache
    cached = cache.get(cache_key)
    if cached:
        return json.loads(cached)

    # Fetch from API
    stock = yf.Ticker(ticker)
    quote = stock.info

    # Store in cache
    cache.setex(cache_key, ttl, json.dumps(quote))

    return quote
```

### File-Based Cache

```python
import pickle
from pathlib import Path
from datetime import datetime, timedelta

CACHE_DIR = Path('.cache/yahoo_finance')
CACHE_TTL = timedelta(hours=1)

def get_cached_or_fetch(ticker, data_type='quote'):
    cache_file = CACHE_DIR / f"{ticker}_{data_type}.pkl"

    # Check if cache exists and is fresh
    if cache_file.exists():
        cache_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
        if cache_age < CACHE_TTL:
            with open(cache_file, 'rb') as f:
                return pickle.load(f)

    # Fetch fresh data
    stock = yf.Ticker(ticker)
    data = stock.info

    # Save to cache
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(cache_file, 'wb') as f:
        pickle.dump(data, f)

    return data
```

## Watchlist Management

### EdTech Companies

```python
EDTECH_WATCHLIST = [
    'CHGG',  # Chegg
    'COUR',  # Coursera
    'DUOL',  # Duolingo
    'TWOU',  # 2U Inc
    'ARCE',  # Arco Platform
    'LAUR',  # Laureate Education
    'INST',  # Instructure
    'POWL'   # Powell Industries
]
```

### Market Indices

```python
MARKET_INDICES = [
    '^GSPC',  # S&P 500
    '^DJI',   # Dow Jones
    '^IXIC',  # NASDAQ
    '^VIX'    # Volatility Index
]
```

### Sector ETFs

```python
SECTOR_ETFS = [
    'XLK',  # Technology
    'XLY',  # Consumer Discretionary
    'XLE',  # Energy
    'XLF',  # Financials
]
```

## Data Quality

### Validation Rules

```python
def validate_quote(quote):
    """Validate quote data quality."""
    checks = {
        'has_price': 'regularMarketPrice' in quote,
        'price_positive': quote.get('regularMarketPrice', 0) > 0,
        'has_volume': 'regularMarketVolume' in quote,
        'volume_positive': quote.get('regularMarketVolume', 0) >= 0
    }

    return all(checks.values()), checks
```

### Anomaly Detection

```python
def detect_price_anomaly(current_price, historical_avg, threshold=0.20):
    """Detect significant price movements."""
    if historical_avg == 0:
        return False

    change_pct = abs(current_price - historical_avg) / historical_avg
    return change_pct > threshold
```

## Scheduling

### Cron Examples

```bash
# Intraday updates (every 15 minutes during market hours)
*/15 9-16 * * 1-5 python scripts/data-ingestion/ingest-yahoo-finance.py --all-watchlist

# End-of-day update (after market close)
0 17 * * 1-5 python scripts/data-ingestion/ingest-yahoo-finance.py --all-watchlist --full

# Weekly full refresh
0 2 * * 0 python scripts/data-ingestion/ingest-yahoo-finance.py --all-watchlist --full --period max
```

### Python Scheduler

```python
import schedule
import time

def intraday_update():
    pipeline = YahooFinanceIngestionPipeline()
    pipeline.run_watchlist_ingestion(fetch_all=False)
    pipeline.close()

def end_of_day_update():
    pipeline = YahooFinanceIngestionPipeline()
    pipeline.run_watchlist_ingestion(fetch_all=True, period='1y')
    pipeline.close()

# Schedule jobs
schedule.every(15).minutes.do(intraday_update)
schedule.every().day.at("17:00").do(end_of_day_update)

# Run
while True:
    schedule.run_pending()
    time.sleep(60)
```

## Integration with Other Sources

### Cross-Validation with Alpha Vantage

```python
def cross_validate_price(ticker, yahoo_price, alpha_vantage_price, tolerance=0.05):
    """Validate price data across sources."""
    if abs(yahoo_price - alpha_vantage_price) / yahoo_price > tolerance:
        logger.warning(f"Price discrepancy for {ticker}: "
                      f"Yahoo=${yahoo_price}, AV=${alpha_vantage_price}")
        return False
    return True
```

### Combine with NewsAPI

```sql
-- Correlate price movements with news sentiment
SELECT
    yh.date,
    yh.close as price,
    yh.volume,
    COUNT(na.id) as news_count,
    AVG(na.sentiment_polarity) as avg_sentiment
FROM yahoo_historical yh
LEFT JOIN news_articles na
    ON yh.ticker = na.ticker
    AND yh.date::date = na.published_at::date
WHERE yh.ticker = 'CHGG'
    AND yh.date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY yh.date, yh.close, yh.volume
ORDER BY yh.date DESC;
```

## Backup Strategies

### Fallback Data Sources

```python
def fetch_with_fallback(ticker):
    """Fetch data with fallback to alternative sources."""
    try:
        # Primary: Yahoo Finance
        return fetch_yahoo_finance(ticker)
    except Exception as e:
        logger.warning(f"Yahoo Finance failed: {e}")

        try:
            # Fallback 1: Alpha Vantage
            return fetch_alpha_vantage(ticker)
        except Exception as e:
            logger.warning(f"Alpha Vantage failed: {e}")

            # Fallback 2: SEC Edgar (limited data)
            return fetch_sec_data(ticker)
```

## Monitoring

### Metrics to Track

```python
METRICS = {
    'requests_total': 0,
    'requests_failed': 0,
    'tickers_processed': 0,
    'average_response_time': 0,
    'cache_hit_rate': 0,
    'data_completeness': 0
}
```

### Alerts

Alert on:
- API failures > 5% of requests
- Response time > 10 seconds
- Missing data for watchlist tickers
- Price anomalies > 20% change
- Service unavailability

## Performance Optimization

### Async Requests

```python
import asyncio
import yfinance as yf

async def fetch_ticker_async(ticker):
    return yf.Ticker(ticker).info

async def fetch_multiple_tickers(tickers):
    tasks = [fetch_ticker_async(ticker) for ticker in tickers]
    return await asyncio.gather(*tasks)

# Usage
tickers = ['CHGG', 'COUR', 'DUOL']
data = asyncio.run(fetch_multiple_tickers(tickers))
```

### Batch Processing

```python
def batch_fetch(tickers, batch_size=10):
    """Fetch tickers in batches to manage rate limiting."""
    results = []

    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i+batch_size]

        for ticker in batch:
            results.append(fetch_ticker(ticker))
            time.sleep(1)

        # Pause between batches
        if i + batch_size < len(tickers):
            time.sleep(10)

    return results
```

## Troubleshooting

### Issue: Empty DataFrame

**Symptom**: `stock.history()` returns empty DataFrame

**Causes**:
- Invalid ticker symbol
- No trading data for period
- Market closed/holiday

**Solution**:
```python
hist = stock.history(period="1mo")
if hist.empty:
    # Try longer period
    hist = stock.history(period="1y")
```

### Issue: Missing Info Fields

**Symptom**: `KeyError` when accessing `info` dictionary

**Solution**:
```python
info = stock.info
price = info.get('regularMarketPrice', None)
if price is None:
    logger.warning(f"No price data for {ticker}")
```

### Issue: Stale Data

**Symptom**: Data not updating

**Solution**:
```python
# Force fresh download
stock = yf.Ticker(ticker)
stock.history(period="1d", prepost=False, auto_adjust=False)
```

## References

- yfinance GitHub: https://github.com/ranaroussi/yfinance
- yfinance Documentation: https://pypi.org/project/yfinance/
- Yahoo Finance: https://finance.yahoo.com/
- Pandas Documentation: https://pandas.pydata.org/docs/

## Legal Considerations

⚠️ **Important**: Yahoo Finance data access through yfinance is:

1. **Unofficial** - Not endorsed by Yahoo
2. **Subject to change** - API may break without notice
3. **Terms of Service** - Review Yahoo's ToS before commercial use
4. **Rate Limits** - Respect reasonable usage limits
5. **Attribution** - Consider proper data attribution

Always consult legal counsel for commercial usage compliance.
