# Alpha Vantage Data Ingestion

## Overview

The Alpha Vantage ingestion script fetches fundamental financial data for EdTech companies and stores it in the `financial_metrics` table. It supplements Yahoo Finance data with additional metrics like P/E ratio, PEG ratio, EPS, ROE, and profit margins.

## Features

- **Rate Limit Compliant**: Respects Alpha Vantage's 5 calls/minute limit
- **Sequential Processing**: Processes companies one at a time with 12-second delays
- **Upsert Logic**: Avoids duplicates while updating existing data
- **Progress Tracking**: Clear logging and coordination hooks
- **Error Handling**: Graceful failure handling per company

## Metrics Tracked

The script stores 16 financial metrics across 4 categories:

### Valuation Metrics
- `pe_ratio` - Price-to-Earnings ratio
- `peg_ratio` - PEG ratio (P/E to Growth)
- `trailing_pe` - Trailing P/E ratio
- `forward_pe` - Forward P/E ratio
- `price_to_book` - Price-to-Book ratio
- `price_to_sales` - Price-to-Sales ratio
- `ev_to_revenue` - Enterprise Value to Revenue
- `ev_to_ebitda` - Enterprise Value to EBITDA

### Profitability Metrics
- `eps` - Earnings Per Share
- `roe` - Return on Equity (%)
- `profit_margin` - Net Profit Margin (%)
- `operating_margin` - Operating Margin (%)
- `return_on_assets` - Return on Assets (%)

### Growth Metrics
- `revenue_growth_yoy` - Year-over-Year Revenue Growth (%)

### Size Metrics
- `market_cap` - Market Capitalization

### Income Metrics
- `dividend_yield` - Dividend Yield (%)

## Target Companies

The script processes the same 10 EdTech companies as SEC ingestion:

1. CHGG - Chegg
2. COUR - Coursera
3. DUOL - Duolingo
4. ARCE - Arco Platform
5. LRN - Stride (K12)
6. UDMY - Udemy
7. PSO - Pearson
8. ATGE - Adtalem Global Education
9. LOPE - Grand Canyon Education
10. STRA - Strategic Education

## Usage

### Run the ingestion script:

```bash
# From project root
python src/pipeline/alpha_vantage_ingestion.py
```

### Expected output:

```
2025-10-06 00:00:00 | INFO     | Starting Alpha Vantage ingestion for 10 EdTech companies
2025-10-06 00:00:00 | INFO     | Rate limit: 5 calls/minute = 1 call every 12 seconds
--------------------------------------------------------------------------------
2025-10-06 00:00:01 | INFO     | [1/10] Processing CHGG...
2025-10-06 00:00:02 | INFO     | [1/10] CHGG: SUCCESS - Fetched 30 fields, Stored 14 metrics
2025-10-06 00:00:02 | INFO     | Rate limit: Waiting 12 seconds before next company...
2025-10-06 00:00:14 | INFO     | [2/10] Processing COUR...
...
--------------------------------------------------------------------------------
ALPHA VANTAGE INGESTION SUMMARY
--------------------------------------------------------------------------------
Total companies processed: 10
Successful: 10
Failed: 0
Total metrics fetched: 300
Total metrics stored: 140
Average metrics per company: 14.0
--------------------------------------------------------------------------------
```

## Rate Limiting

The script respects Alpha Vantage's API rate limits:

- **Free Tier**: 5 API calls per minute, 500 calls per day
- **Delay**: 12 seconds between companies (5 calls/60 seconds)
- **Total Runtime**: ~2 minutes for 10 companies

## Database Schema

Metrics are stored in the `financial_metrics` table with:

```python
{
    'company_id': UUID,           # Foreign key to companies table
    'metric_date': DateTime,      # When data was fetched
    'period_type': 'quarterly',   # Time period
    'metric_type': str,           # e.g., 'pe_ratio', 'eps'
    'metric_category': str,       # e.g., 'valuation', 'profitability'
    'value': float,               # Metric value
    'unit': str,                  # 'USD', 'percent', 'ratio'
    'source': 'alpha_vantage',    # Data source
    'confidence_score': 0.95,     # Data quality confidence
}
```

## Upsert Logic

The script uses PostgreSQL's `INSERT ... ON CONFLICT DO UPDATE` to:

1. Insert new metrics if they don't exist
2. Update existing metrics if data changes
3. Avoid duplicate entries

Uniqueness is based on: `(company_id, metric_type, metric_date, period_type)`

## Error Handling

- **API Key Missing**: Exits with error message
- **Company Not Found**: Creates placeholder company record
- **API Failures**: Logs error, continues with next company
- **No Data**: Logs warning, marks as failed

## Integration with Coordination Hooks

The script automatically runs coordination hooks:

- **Pre-task**: Before starting ingestion
- **Notify**: After each company (during rate limit delay)
- **Post-task**: After completing all companies

## Prerequisites

1. **Alpha Vantage API Key**: Set `ALPHA_VANTAGE_API_KEY` in `.env`
2. **Database**: PostgreSQL with `companies` and `financial_metrics` tables
3. **Dependencies**: See `requirements.txt`

## Testing

```bash
# Validate script without running
python -c "
from src.pipeline.alpha_vantage_ingestion import EDTECH_TICKERS, METRIC_MAPPINGS
print(f'Companies: {len(EDTECH_TICKERS)}')
print(f'Metrics: {len(METRIC_MAPPINGS)}')
"

# Run with single company (manual test)
python -c "
import asyncio
from src.pipeline.alpha_vantage_ingestion import run_alpha_vantage_ingestion
asyncio.run(run_alpha_vantage_ingestion(['CHGG']))
"
```

## Monitoring

Monitor ingestion via logs:

- **Success**: Shows metrics fetched and stored
- **Failures**: Shows error messages per company
- **Summary**: Final statistics at end

## Next Steps

After ingestion:

1. Verify data in database:
   ```sql
   SELECT company_id, metric_type, value, metric_date
   FROM financial_metrics
   WHERE source = 'alpha_vantage'
   ORDER BY metric_date DESC;
   ```

2. Compare with Yahoo Finance data
3. Run analytics queries using both data sources
4. Schedule regular updates (daily/weekly)

## Troubleshooting

### "API key not configured"
- Check `.env` file has `ALPHA_VANTAGE_API_KEY=your_key`

### "No data returned from Alpha Vantage"
- Verify ticker symbol is correct
- Check API key is valid
- Ensure rate limit not exceeded (500/day)

### "Failed to get/create company record"
- Check database connection
- Verify `companies` table exists
- Check database user permissions

## File Location

```
src/pipeline/alpha_vantage_ingestion.py
```

## Related Files

- `src/connectors/data_sources.py` - AlphaVantageConnector class
- `src/db/models.py` - Company and FinancialMetric models
- `src/pipeline/run_sec_ingestion.py` - Similar ingestion pattern
