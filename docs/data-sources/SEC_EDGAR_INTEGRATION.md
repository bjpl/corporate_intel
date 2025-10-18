# SEC EDGAR API Integration Guide

## Overview

The SEC EDGAR (Electronic Data Gathering, Analysis, and Retrieval) system provides free public access to corporate filings submitted to the U.S. Securities and Exchange Commission. This integration enables automated collection of public company financial data, disclosures, and regulatory filings for EdTech companies.

**Implementation Status**: Production Ready
**Last Updated**: 2025-10-17
**Maintainer**: Backend Development Team

---

## Table of Contents

1. [API Overview](#api-overview)
2. [Authentication & Rate Limiting](#authentication--rate-limiting)
3. [Data Schema](#data-schema)
4. [Integration Architecture](#integration-architecture)
5. [Configuration](#configuration)
6. [Usage Examples](#usage-examples)
7. [Error Handling](#error-handling)
8. [Monitoring](#monitoring)
9. [Troubleshooting](#troubleshooting)

---

## API Overview

### Base URLs

- **Company Data**: `https://data.sec.gov`
- **Filing Archives**: `https://www.sec.gov/Archives/edgar/data`
- **Ticker Mapping**: `https://www.sec.gov/files/company_tickers.json`

### Key Endpoints

| Endpoint | Purpose | Rate Limit |
|----------|---------|------------|
| `/submissions/CIK{cik}.json` | Company information and filing list | 10 req/sec |
| `/Archives/edgar/data/{cik}/{accession}/{file}` | Download filing content | 10 req/sec |
| `/files/company_tickers.json` | Ticker-to-CIK mapping | Daily refresh |

### Filing Types Collected

- **10-K**: Annual reports with audited financial statements
- **10-Q**: Quarterly reports with unaudited financials
- **8-K**: Current reports for material events
- **10-K/A, 10-Q/A**: Amended annual/quarterly reports
- **S-1**: Initial public offering registration
- **S-4**: Merger/acquisition registration
- **DEF 14A**: Proxy statements for shareholder meetings
- **SC 13D/13G**: Beneficial ownership disclosures

---

## Authentication & Rate Limiting

### User-Agent Requirement

**CRITICAL**: SEC requires a User-Agent header identifying your organization and contact information.

**Format**: `Company Name/Version (contact@email.com)`

**Configuration**:
```bash
# .env.staging or .env.production
SEC_USER_AGENT="Corporate Intel Platform/1.0 (brandon.lambert87@gmail.com)"
```

**Failure to provide a proper User-Agent will result in 403 Forbidden responses.**

### Rate Limiting

SEC enforces strict rate limits to ensure fair access:

- **Limit**: 10 requests per second
- **Burst**: No burst allowance
- **Enforcement**: Server-side (503 responses when exceeded)

**Implementation**:
```python
class RateLimiter:
    """Enforces 10 requests/second limit."""
    def __init__(self, calls_per_second: int = 10):
        self.min_interval = 1.0 / calls_per_second
        self.last_call = 0.0

    async def acquire(self):
        """Wait if necessary to respect rate limit."""
        time_since_last = time.time() - self.last_call
        if time_since_last < self.min_interval:
            await asyncio.sleep(self.min_interval - time_since_last)
        self.last_call = time.time()
```

### Backoff Strategy

When receiving 503 (Service Unavailable) responses:

1. **Initial Delay**: 60 seconds
2. **Exponential Backoff**: Double delay on each retry (60s → 120s → 240s)
3. **Maximum Delay**: 600 seconds (10 minutes)
4. **Maximum Retries**: 3 attempts

---

## Data Schema

### Company Information

```json
{
  "cik": "0001364612",
  "name": "Duolingo Inc.",
  "ticker": "DUOL",
  "sic": "7372",
  "sicDescription": "Services-Prepackaged Software",
  "category": "enabling_technology",
  "filings": {
    "recent": {
      "form": ["10-K", "10-Q"],
      "filingDate": ["2024-03-15", "2024-06-10"],
      "accessionNumber": ["0001364612-24-000012", "0001364612-24-000023"]
    }
  }
}
```

### Filing Record

```python
# Database Model: SECFiling
{
  "id": UUID,
  "company_id": UUID,  # Foreign key to Company table
  "filing_type": "10-K",
  "filing_date": datetime(2024, 3, 15),
  "accession_number": "0001364612-24-000012",
  "filing_url": "https://www.sec.gov/Archives/edgar/data/...",
  "raw_text": "Full filing content...",
  "content_hash": "sha256_hash",
  "processing_status": "pending|processed|failed",
  "created_at": datetime,
  "updated_at": datetime
}
```

### EdTech Company Categories

Companies are automatically classified based on SIC codes:

- **k12**: Elementary and secondary schools (SIC 8211)
- **higher_education**: Colleges and universities (SIC 8221, 8222)
- **corporate_learning**: Vocational and technical training (SIC 8243, 8249)
- **enabling_technology**: Educational software (SIC 7372, 7373)
- **direct_to_consumer**: Other educational services (SIC 8299)

---

## Integration Architecture

### Component Overview

```
┌─────────────────┐
│ Prefect Flow    │  Orchestration layer
│ sec_ingestion   │
└────────┬────────┘
         │
    ┌────▼────────────────────┐
    │ SECAPIClient            │  API client with rate limiting
    │ - get_company_info()    │
    │ - get_filings()         │
    │ - download_filing()     │
    └────────┬────────────────┘
             │
    ┌────────▼─────────────┐
    │ RateLimiter          │  10 req/sec enforcement
    └────────┬─────────────┘
             │
    ┌────────▼─────────────┐
    │ httpx.AsyncClient    │  HTTP client
    └──────────────────────┘
```

### Data Flow

1. **Company Discovery**: Load EdTech watchlist from configuration
2. **CIK Lookup**: Map ticker symbols to CIK numbers
3. **Filing Enumeration**: Fetch list of filings for each company
4. **Filing Download**: Download filing content (rate-limited)
5. **Validation**: Validate data quality using Great Expectations
6. **Storage**: Store in PostgreSQL (companies + filings tables)
7. **Post-Processing**: Extract financial metrics, text sections

### Prefect Tasks

```python
@task(retries=3, retry_delay_seconds=60)
async def fetch_company_data(ticker: str) -> Dict[str, Any]:
    """Fetch company data from SEC EDGAR."""

@task(retries=3, retry_delay_seconds=60)
async def fetch_filings(cik: str, filing_types: List[str]) -> List[Dict]:
    """Fetch filing list for company."""

@task(retries=2, retry_delay_seconds=120)
async def download_filing(filing: Dict) -> Dict:
    """Download filing content."""

@task
def validate_filing_data(filing_data: Dict) -> bool:
    """Validate using Great Expectations."""

@task
async def store_filing(filing_data: Dict, cik: str) -> str:
    """Store filing in database."""
```

---

## Configuration

### Production Configuration

**File**: `config/production/sec-api-config.yml`

Key settings:
- **Rate Limiting**: 10 requests/second
- **Retry Logic**: 3 attempts with exponential backoff
- **Caching**: 24-hour cache for ticker mapping
- **Validation**: Great Expectations quality checks
- **Monitoring**: Prometheus metrics

### Environment Variables

```bash
# Required
SEC_USER_AGENT="Corporate Intel Platform/1.0 (brandon.lambert87@gmail.com)"

# Optional (uses defaults if not set)
SEC_RATE_LIMIT=10  # Requests per second
```

---

## Usage Examples

### Basic Filing Ingestion

```python
from src.pipeline.sec_ingestion import FilingRequest, sec_ingestion_flow

# Single company ingestion
request = FilingRequest(
    company_ticker="DUOL",
    filing_types=["10-K", "10-Q"],
    start_date=datetime(2023, 1, 1)
)

result = await sec_ingestion_flow(request)
print(f"Stored {result['filings_stored']} filings for {result['ticker']}")
```

### Batch Processing

```python
from src.pipeline.sec_ingestion import batch_sec_ingestion_flow

# Process multiple companies
edtech_companies = ["DUOL", "CHGG", "COUR", "UDMY"]
results = await batch_sec_ingestion_flow(edtech_companies)

for result in results:
    print(f"{result['ticker']}: {result['filings_stored']} filings")
```

### Manual API Client Usage

```python
from src.pipeline.sec_ingestion import SECAPIClient

client = SECAPIClient()

# Get company information
company_info = await client.get_company_info("DUOL")
print(f"CIK: {company_info['cik']}, Name: {company_info['name']}")

# Fetch recent filings
filings = await client.get_filings(
    cik="0001364612",
    filing_types=["10-K", "10-Q"],
    start_date=datetime(2024, 1, 1)
)

# Download filing content
for filing in filings:
    content = await client.download_filing_content(filing)
    print(f"Downloaded {len(content)} characters for {filing['accessionNumber']}")
```

---

## Error Handling

### Common Errors

| Error | HTTP Code | Cause | Solution |
|-------|-----------|-------|----------|
| Missing User-Agent | 403 | User-Agent header not provided | Set `SEC_USER_AGENT` in environment |
| Rate Limit Exceeded | 503 | More than 10 req/sec | Automatic backoff (60s delay) |
| CIK Not Found | 404 | Invalid CIK or ticker | Verify ticker in `company_tickers.json` |
| Network Timeout | Timeout | SEC server slow/unresponsive | Retry with exponential backoff |
| Invalid Accession Number | 404 | Malformed accession number | Validate format: `NNNNNNNNNN-NN-NNNNNN` |

### Error Response Handling

```python
try:
    result = await sec_ingestion_flow(request)
except ValueError as e:
    # Missing required data (ticker not found, invalid CIK)
    logger.error(f"Data validation error: {e}")
except httpx.HTTPStatusError as e:
    # HTTP errors (403, 404, 503)
    if e.response.status_code == 503:
        logger.warning("Rate limit hit, waiting 60 seconds...")
        await asyncio.sleep(60)
    else:
        logger.error(f"HTTP error {e.response.status_code}: {e}")
except Exception as e:
    # Unexpected errors
    logger.error(f"Unexpected error: {e}", exc_info=True)
```

---

## Monitoring

### Prometheus Metrics

**Endpoint**: `http://localhost:9090/metrics`

Key metrics:
```
# Request metrics
sec_api_requests_total{status="success|error"}
sec_api_request_duration_seconds{endpoint="/submissions"}

# Rate limiting
sec_api_rate_limit_hits_total
sec_api_backoff_delays_total

# Data quality
sec_filings_downloaded_total
sec_filings_validated_total{result="pass|fail"}
sec_filings_stored_total
```

### Grafana Dashboard

**Dashboard**: SEC EDGAR Data Ingestion

Panels:
- API request rate (requests/second)
- Error rate (percentage)
- Filing download throughput
- Validation success rate
- Database storage latency

### Logging

**Format**: JSON structured logs

**Example**:
```json
{
  "timestamp": "2025-10-17T18:30:45.123Z",
  "level": "INFO",
  "message": "Fetching filings for CIK 0001364612",
  "context": {
    "ticker": "DUOL",
    "cik": "0001364612",
    "filing_types": ["10-K", "10-Q"],
    "trace_id": "abc123..."
  }
}
```

---

## Troubleshooting

### Issue: 403 Forbidden Errors

**Symptom**: All API requests return 403
**Cause**: Missing or invalid User-Agent header
**Solution**:
1. Check `SEC_USER_AGENT` environment variable
2. Ensure format: `Company Name/Version (email@example.com)`
3. Restart application to reload environment

### Issue: Frequent 503 Errors

**Symptom**: High rate of 503 Service Unavailable
**Cause**: Exceeding 10 requests/second limit
**Solution**:
1. Check rate limiter configuration
2. Reduce concurrent downloads: `concurrent_downloads: 3`
3. Increase delay between batches

### Issue: No Filings Found for Valid Ticker

**Symptom**: API returns empty filings list
**Cause**:
- Ticker recently went public (no historical filings)
- Date range too restrictive
**Solution**:
1. Check company IPO date
2. Expand `start_date` or remove date filter
3. Verify ticker in `company_tickers.json`

### Issue: Filing Content Download Fails

**Symptom**: 404 error when downloading filing
**Cause**:
- Malformed accession number
- Primary document URL changed
**Solution**:
1. Validate accession number format
2. Check `primaryDocument` field in filing metadata
3. Retry with alternate document if available

### Issue: Database Duplicate Key Errors

**Symptom**: IntegrityError on accession_number
**Cause**: Attempting to insert duplicate filing
**Solution**:
- Deduplication is automatic (returns existing ID)
- Check logs for duplicate warnings
- No action needed (expected behavior)

---

## Best Practices

### 1. Respect Rate Limits
- Always use the built-in RateLimiter
- Never bypass rate limiting in production
- Monitor 503 response rates

### 2. Handle Failures Gracefully
- Use automatic retry with backoff
- Log all errors for analysis
- Implement circuit breaker for sustained failures

### 3. Cache Appropriately
- Cache ticker-to-CIK mapping (changes infrequently)
- Cache company information (6-hour TTL)
- Do NOT cache filing content (too large)

### 4. Validate Data Quality
- Run Great Expectations validation on all filings
- Check required fields before storage
- Monitor validation failure rates

### 5. Monitor Performance
- Track API request metrics
- Alert on high error rates (>10%)
- Monitor database storage latency

---

## Production Checklist

- [ ] `SEC_USER_AGENT` environment variable configured
- [ ] Rate limiting set to 10 requests/second
- [ ] Retry logic with exponential backoff enabled
- [ ] Great Expectations validation configured
- [ ] Database connection pool sized appropriately
- [ ] Prometheus metrics endpoint exposed
- [ ] Grafana dashboard configured
- [ ] Error alerting set up (Sentry/PagerDuty)
- [ ] Circuit breaker thresholds configured
- [ ] Caching strategy implemented
- [ ] Logging configured with JSON format
- [ ] Backup/recovery procedures documented

---

## Additional Resources

- **SEC EDGAR API Documentation**: https://www.sec.gov/edgar/sec-api-documentation
- **SEC Filing Types**: https://www.sec.gov/forms
- **Company Ticker Mapping**: https://www.sec.gov/files/company_tickers.json
- **XBRL Financial Data**: https://www.sec.gov/structureddata/osd-inline-xbrl.html

---

## Support

**Issues**: Create ticket in project issue tracker
**Questions**: Contact backend development team
**Emergency**: Page on-call engineer via PagerDuty
