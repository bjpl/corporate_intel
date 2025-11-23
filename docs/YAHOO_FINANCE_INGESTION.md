# Yahoo Finance Data Ingestion Pipeline

## Overview

The Yahoo Finance ingestion pipeline fetches financial data for the top 10 EdTech companies and populates the `companies` and `financial_metrics` tables with quarterly financial data spanning 2 years (8 quarters).

## Target Companies

| # | Ticker | Company Name | Category | Subcategories |
|---|--------|-------------|----------|---------------|
| 1 | CHGG | Chegg Inc. | D2C | Higher Ed, Tutoring |
| 2 | COUR | Coursera Inc. | D2C | Higher Ed, Online Learning |
| 3 | DUOL | Duolingo Inc. | D2C | Language Learning, Mobile-First |
| 4 | ARCE | Arco Platform Limited | B2B | K-12, Brazil Market |
| 5 | LRN | Stride Inc. | B2B | K-12, Virtual Schools |
| 6 | UDMY | Udemy Inc. | Marketplace | Corporate Learning, Skills Training |
| 7 | PSO | Pearson PLC | B2B | Higher Ed, Assessment, Publishing |
| 8 | ATGE | Adtalem Global Education Inc. | B2B | Higher Ed, Healthcare Education |
| 9 | LOPE | Grand Canyon Education Inc. | B2B | Higher Ed, Online Programs |
| 10 | STRA | Strategic Education Inc. | B2B | Higher Ed, Career Education |

## Data Collected

### Company Information
- Ticker symbol
- Company name
- Sector and category
- Website
- Employee count
- Headquarters location
- Subcategories

### Financial Metrics (Quarterly)
- **Revenue**: Total revenue in USD
- **Gross Margin**: Gross profit / revenue * 100 (%)
- **Operating Margin**: Operating income / revenue * 100 (%)
- **Earnings Growth**: Year-over-year earnings growth (%)

All metrics are stored for up to 8 quarters (2 years) of quarterly data.

## Usage

### Running the Ingestion Pipeline

#### As a Python Module
```bash
python -m src.pipeline.yahoo_finance_ingestion
```

#### Programmatically
```python
import asyncio
from src.pipeline.yahoo_finance_ingestion import run_ingestion

# Run the ingestion
result = asyncio.run(run_ingestion())

# Check results
print(f"Companies created: {result['statistics']['companies_created']}")
print(f"Metrics ingested: {result['statistics']['total_metrics']}")
```

### Expected Output

```
================================================================================
Yahoo Finance Data Ingestion Pipeline
================================================================================
2025-10-06 04:00:00 | INFO     | Starting Yahoo Finance data ingestion pipeline
2025-10-06 04:00:00 | INFO     | Target: 10 companies, 2 years quarterly data
2025-10-06 04:00:05 | INFO     | [1/10] Processing CHGG - Chegg Inc.
2025-10-06 04:00:07 | INFO     | Created company: CHGG
2025-10-06 04:00:10 | INFO     | Ingested 8 quarters of financial data for CHGG
...
================================================================================
INGESTION SUMMARY
================================================================================
Companies Created: 10
Companies Updated: 0
Metrics Created: 320
Metrics Updated: 0
Total Errors: 0
================================================================================
```

## Features

### 1. Idempotent Ingestion (Upsert Logic)
The pipeline uses PostgreSQL's `ON CONFLICT DO UPDATE` to handle duplicates gracefully:
- If a company exists, it updates the metadata
- If a metric exists, it updates the value and timestamp
- No duplicate entries are created

### 2. Retry Logic with Exponential Backoff
- Maximum 3 retry attempts per API call
- Exponential backoff: 1s, 2s, 4s
- Handles transient network errors

### 3. Comprehensive Error Handling
- Continues processing on individual company failures
- Collects all errors for reporting
- Provides detailed error messages

### 4. Progress Tracking
- Logs progress for each company
- Sends notifications via coordination hooks
- Tracks statistics (created/updated counts)

### 5. TimescaleDB Hypertable Support
- Metrics are stored in TimescaleDB hypertable format
- Optimized for time-series queries
- Efficient compression and retention policies

## Database Schema

### Companies Table
```sql
companies (
    id UUID PRIMARY KEY,
    ticker VARCHAR(10) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    sector VARCHAR(100),
    category VARCHAR(50),
    subcategory JSON,
    website VARCHAR(255),
    employee_count INTEGER,
    headquarters VARCHAR(255),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
)
```

### Financial Metrics Table (TimescaleDB Hypertable)
```sql
financial_metrics (
    id BIGINT,
    company_id UUID REFERENCES companies(id),
    metric_date TIMESTAMP NOT NULL,
    period_type VARCHAR(20) NOT NULL,  -- 'quarterly'
    metric_type VARCHAR(50) NOT NULL,  -- 'revenue', 'gross_margin', etc.
    metric_category VARCHAR(50),       -- 'financial'
    value FLOAT NOT NULL,
    unit VARCHAR(20),                  -- 'USD', 'percent'
    source VARCHAR(50),                -- 'yahoo_finance'
    confidence_score FLOAT,            -- 0.95
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    PRIMARY KEY (id, metric_date),
    UNIQUE (company_id, metric_type, metric_date, period_type)
)
```

## Coordination Hooks

The pipeline integrates with Claude Flow coordination hooks:

### Pre-Task Hook
```bash
npx claude-flow@alpha hooks pre-task --description "Yahoo Finance ingestion"
```

### Progress Notifications
```bash
npx claude-flow@alpha hooks notify --message "Completed X/10 companies"
```

### Post-Task Hook
```bash
npx claude-flow@alpha hooks post-task --task-id "yahoo-ingestion"
```

## Error Handling

### Common Errors and Solutions

#### 1. No Data Available
```
Error: No data available from Yahoo Finance
```
**Solution**: Some tickers may not have quarterly data available. The pipeline will skip and continue.

#### 2. Database Connection Error
```
Error: could not connect to server
```
**Solution**: Ensure PostgreSQL is running and connection settings in `.env` are correct.

#### 3. Missing Dependencies
```
Error: No module named 'yfinance'
```
**Solution**: Install dependencies with `pip install -r requirements.txt`

## Data Quality

### Confidence Scores
All ingested metrics have a confidence score of **0.95** indicating high-quality data from Yahoo Finance API.

### Data Validation
- Revenue values are checked for NULL/NaN
- Margins are calculated only when both numerator and denominator exist
- All dates are timezone-aware for TimescaleDB compatibility

## Performance

### Expected Runtime
- **Per Company**: 5-10 seconds
- **Total Pipeline**: 1-2 minutes for all 10 companies
- **Metrics Ingested**: ~320 metrics (10 companies × 8 quarters × 4 metrics)

### Rate Limiting
Yahoo Finance API is free and doesn't have strict rate limits, but the pipeline includes:
- Async execution to avoid blocking
- Exponential backoff on failures
- Respectful request pacing

## Extending the Pipeline

### Adding More Companies
Edit `EDTECH_COMPANIES` list in `src/pipeline/yahoo_finance_ingestion.py`:

```python
EDTECH_COMPANIES = [
    # ... existing companies ...
    {
        "ticker": "NEW",
        "name": "New EdTech Company",
        "sector": "Education Technology",
        "category": "B2B",
        "subcategory": ["K-12"],
    },
]
```

### Adding More Metrics
Extend `_ingest_quarterly_financials` method:

```python
# Net Income
if "Net Income" in quarterly_income.index:
    net_income = quarterly_income.loc["Net Income", quarter_date]
    if net_income and not pd.isna(net_income):
        metrics_to_insert.append({
            "metric_type": "net_income",
            "value": float(net_income),
            "unit": "USD",
            "metric_category": "financial",
        })
```

## Troubleshooting

### Enable Debug Logging
```python
import sys
from loguru import logger

logger.remove()
logger.add(sys.stderr, level="DEBUG")
```

### Check Ingested Data
```sql
-- Count companies
SELECT COUNT(*) FROM companies;

-- Count metrics by type
SELECT metric_type, COUNT(*)
FROM financial_metrics
GROUP BY metric_type;

-- View latest metrics for a company
SELECT c.ticker, fm.metric_type, fm.value, fm.unit, fm.metric_date
FROM financial_metrics fm
JOIN companies c ON fm.company_id = c.id
WHERE c.ticker = 'CHGG'
ORDER BY fm.metric_date DESC;
```

## Future Enhancements

1. **Annual Data**: Add annual financial statements (10-K data)
2. **More Metrics**: MAU (Monthly Active Users), CAC (Customer Acquisition Cost)
3. **Historical Data**: Extend beyond 2 years for trend analysis
4. **Validation**: Cross-reference with SEC filings
5. **Alerts**: Email notifications on completion or errors
6. **Scheduling**: Cron job or Prefect workflow for periodic updates

## Related Documentation

- [Database Schema](./DATABASE_SCHEMA.md)
- [Data Connectors](../src/connectors/data_sources.py)
- [Pipeline Architecture](./PIPELINE_ARCHITECTURE.md)
