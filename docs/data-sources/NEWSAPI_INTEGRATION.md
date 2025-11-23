# NewsAPI Integration Guide

## Overview

NewsAPI integration provides real-time news article ingestion with sentiment analysis for the Corporate Intelligence Platform. This integration enables tracking of company news, market events, and sentiment trends.

## Features

- Real-time news article retrieval
- Sentiment analysis using TextBlob
- Company-specific news tracking
- Keyword-based search
- Top headlines monitoring
- Automatic deduplication
- Rate limiting and caching

## API Details

- **Provider**: NewsAPI.org
- **Base URL**: https://newsapi.org/v2
- **Authentication**: API Key (Header: X-Api-Key)
- **Documentation**: https://newsapi.org/docs

## Rate Limits

### Free Tier
- 1,000 requests per day
- 100 requests per hour
- Development only (no commercial use)

### Developer Tier
- 100,000 requests per day
- Commercial use allowed
- $449/month

### Business Tier
- Unlimited requests
- Advanced features
- Custom pricing

## Configuration

### Environment Variables

```bash
# Required
NEWSAPI_KEY=your-api-key-here

# Optional
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=corporate_intel
POSTGRES_USER=intel_user
POSTGRES_PASSWORD=your-password
```

### Configuration File

Location: `/config/production/data-sources/newsapi-config.yml`

Key settings:
- Search parameters (language, sources, lookback period)
- Sentiment analysis configuration
- Rate limiting settings
- Caching options
- Quality filters
- Monitoring preferences

## Getting Started

### 1. Obtain API Key

1. Visit https://newsapi.org/register
2. Create a free account
3. Copy your API key
4. Set the `NEWSAPI_KEY` environment variable

```bash
export NEWSAPI_KEY="your-api-key-here"
```

### 2. Install Dependencies

```bash
pip install newsapi-python textblob pyyaml psycopg2-binary
```

### 3. Test Connectivity

```bash
python scripts/test-newsapi-connectivity.py
```

Expected output:
- ✓ API Key found
- ✓ NewsAPI client initialized
- ✓ Top headlines fetched
- ✓ Company news search working
- ✓ Sentiment analysis functional

## Usage

### Command-Line Interface

#### Fetch News for a Specific Ticker

```bash
python scripts/data-ingestion/ingest-news-sentiment.py --ticker CHGG
```

#### Fetch News with Custom Lookback

```bash
python scripts/data-ingestion/ingest-news-sentiment.py --ticker CHGG --days 30
```

#### Search by Keyword

```bash
python scripts/data-ingestion/ingest-news-sentiment.py --keyword "online education"
```

#### Process All Watchlist Tickers

```bash
python scripts/data-ingestion/ingest-news-sentiment.py --all-watchlist
```

### Python API

```python
from scripts.data_ingestion.ingest_news_sentiment import NewsAPIIngestionPipeline

# Initialize pipeline
pipeline = NewsAPIIngestionPipeline()

# Fetch news for a ticker
articles = pipeline.fetch_news_by_ticker('CHGG', days=7)

# Process with sentiment analysis
processed = pipeline.process_articles(articles, ticker='CHGG')

# Store in database
pipeline.store_articles(processed)

# Print statistics
pipeline.print_stats()

# Clean up
pipeline.close()
```

## Data Schema

### news_articles Table

```sql
CREATE TABLE news_articles (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(10),
    source_name VARCHAR(255),
    author VARCHAR(255),
    title TEXT NOT NULL,
    description TEXT,
    url TEXT UNIQUE NOT NULL,
    url_to_image TEXT,
    published_at TIMESTAMP,
    content TEXT,
    sentiment_polarity FLOAT,        -- Range: -1.0 to 1.0
    sentiment_subjectivity FLOAT,    -- Range: 0.0 to 1.0
    sentiment_category VARCHAR(20),   -- very_negative, negative, neutral, positive, very_positive
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_news_ticker ON news_articles(ticker);
CREATE INDEX idx_news_published ON news_articles(published_at);
CREATE INDEX idx_news_sentiment ON news_articles(sentiment_category);
```

## Sentiment Analysis

### Sentiment Categories

Based on TextBlob polarity scores:

| Category | Polarity Range | Description |
|----------|---------------|-------------|
| Very Positive | 0.6 to 1.0 | Highly positive sentiment |
| Positive | 0.2 to 0.6 | Positive sentiment |
| Neutral | -0.2 to 0.2 | Neutral or mixed |
| Negative | -0.6 to -0.2 | Negative sentiment |
| Very Negative | -1.0 to -0.6 | Highly negative sentiment |

### Sentiment Metrics

- **Polarity**: Emotional tone (-1.0 = negative, +1.0 = positive)
- **Subjectivity**: Opinion vs. fact (0.0 = objective, 1.0 = subjective)

### Example Analysis

```python
from textblob import TextBlob

text = "Company reports record quarterly earnings with strong growth"
blob = TextBlob(text)

print(f"Polarity: {blob.sentiment.polarity}")        # 0.35 (positive)
print(f"Subjectivity: {blob.sentiment.subjectivity}") # 0.65 (subjective)
```

## API Endpoints

### 1. Everything Endpoint

Search all articles:

```python
client.get_everything(
    q='CHGG OR Chegg',
    from_param='2024-10-01',
    language='en',
    sort_by='publishedAt',
    page_size=100
)
```

Parameters:
- `q`: Keywords or phrases
- `from_param`: Start date (YYYY-MM-DD)
- `to`: End date (YYYY-MM-DD)
- `language`: ISO 639-1 language code
- `sort_by`: relevancy, popularity, publishedAt
- `page_size`: Results per page (max 100)

### 2. Top Headlines Endpoint

Get breaking news:

```python
client.get_top_headlines(
    category='business',
    country='us',
    page_size=20
)
```

Parameters:
- `category`: business, technology, entertainment, etc.
- `country`: ISO 3166-1 country code
- `sources`: Specific news sources

## Best Practices

### 1. Rate Limiting

```python
import time

# Respect rate limits
requests_per_minute = 5
time.sleep(60 / requests_per_minute)
```

### 2. Error Handling

```python
try:
    response = client.get_everything(q=query)
    if response['status'] == 'ok':
        articles = response['articles']
    else:
        logger.error(f"API error: {response.get('message')}")
except Exception as e:
    logger.error(f"Request failed: {e}")
```

### 3. Deduplication

Articles are deduplicated by URL using database UNIQUE constraint.

### 4. Caching

Cache responses to minimize API calls:

```python
# Redis cache
cache_key = f"newsapi:{ticker}:{date}"
if cached := redis.get(cache_key):
    return json.loads(cached)
```

## Monitoring

### Metrics to Track

- Total API calls
- Articles fetched
- Articles stored
- Failed requests
- Sentiment distribution
- Response times

### Alerting

Alert on:
- Rate limit approaching (>90% usage)
- API errors (status != 'ok')
- High negative sentiment spikes
- Missing data for watchlist companies

## Troubleshooting

### Common Issues

#### 1. API Key Invalid

**Error**: `401 Unauthorized`

**Solution**: Verify NEWSAPI_KEY is set correctly

```bash
echo $NEWSAPI_KEY
```

#### 2. Rate Limit Exceeded

**Error**: `429 Too Many Requests`

**Solution**:
- Implement exponential backoff
- Reduce request frequency
- Upgrade to higher tier

#### 3. No Results Found

**Possible causes**:
- Ticker/keyword too specific
- Date range too narrow
- Language filter too restrictive

**Solution**: Broaden search parameters

#### 4. Sentiment Analysis Errors

**Error**: TextBlob import issues

**Solution**:
```bash
pip install textblob
python -m textblob.download_corpora
```

## Advanced Features

### 1. Multi-Keyword Search

```python
keywords = ["earnings", "merger", "acquisition"]
query = " OR ".join(keywords)
articles = client.get_everything(q=query)
```

### 2. Source Filtering

```python
# Only trusted sources
domains = "wsj.com,bloomberg.com,reuters.com"
articles = client.get_everything(q=query, domains=domains)
```

### 3. Batch Processing

```python
tickers = ['CHGG', 'COUR', 'DUOL', 'TWOU']
for ticker in tickers:
    articles = pipeline.fetch_news_by_ticker(ticker)
    pipeline.store_articles(articles)
    time.sleep(12)  # 5 requests per minute
```

## Integration with Other Services

### SEC Filings Cross-Reference

```python
# Correlate news with SEC filings
SELECT
    n.title,
    n.published_at,
    n.sentiment_category,
    f.form_type,
    f.filing_date
FROM news_articles n
LEFT JOIN sec_filings f
    ON n.ticker = f.ticker
    AND DATE(n.published_at) = DATE(f.filing_date)
WHERE n.ticker = 'CHGG'
ORDER BY n.published_at DESC;
```

### Yahoo Finance Price Correlation

```python
# Analyze sentiment vs. price movement
SELECT
    n.published_at::date as date,
    AVG(n.sentiment_polarity) as avg_sentiment,
    y.close as price
FROM news_articles n
JOIN yahoo_historical y
    ON n.ticker = y.ticker
    AND n.published_at::date = y.date::date
WHERE n.ticker = 'CHGG'
GROUP BY n.published_at::date, y.close
ORDER BY date DESC;
```

## Cost Management

### Optimizing API Usage

1. **Cache aggressively**: Store responses for 1 hour minimum
2. **Batch requests**: Combine multiple queries when possible
3. **Filter early**: Use specific keywords and date ranges
4. **Schedule wisely**: Run during off-peak hours
5. **Monitor usage**: Track daily/hourly request counts

### Free Tier Limitations

With 1,000 requests/day:
- ~40 requests/hour
- ~7 requests per watchlist ticker per day
- ~140 requests per ticker per month

## Support

- NewsAPI Docs: https://newsapi.org/docs
- Support: support@newsapi.org
- Status Page: https://status.newsapi.org

## References

- NewsAPI Documentation: https://newsapi.org/docs/endpoints
- TextBlob Sentiment: https://textblob.readthedocs.io/en/dev/
- ISO 639-1 Language Codes: https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes
- ISO 3166-1 Country Codes: https://en.wikipedia.org/wiki/List_of_ISO_3166_country_codes
