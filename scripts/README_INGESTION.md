# Yahoo Finance Data Ingestion Scripts

## Quick Start

### 1. Validate Pipeline (Recommended First Step)
Before running the actual ingestion, validate that all data sources are accessible:

```bash
python scripts/test_yahoo_ingestion.py
```

Expected output:
```
✓ Successfully fetched data for CHGG
✓ Successfully fetched 5 quarters of data for DUOL
✓ ALL TESTS PASSED - Pipeline is ready to run
```

### 2. Run Ingestion
Once validation passes, run the full ingestion pipeline:

```bash
python -m src.pipeline.yahoo_finance_ingestion
```

## Files

### `src/pipeline/yahoo_finance_ingestion.py`
Main ingestion pipeline that:
- Fetches data for 10 EdTech companies
- Ingests 2 years of quarterly financials (8 quarters)
- Populates `companies` and `financial_metrics` tables
- Uses upsert logic to handle duplicates
- Includes retry logic and error handling

### `scripts/test_yahoo_ingestion.py`
Validation script that:
- Tests Yahoo Finance API connectivity
- Validates data availability for all companies
- Checks quarterly financial data structure
- **Does not write to database**

## Data Flow

```
Yahoo Finance API
        ↓
YahooFinanceIngestionPipeline
        ↓
    ┌───────────────┬────────────────────┐
    ↓               ↓                    ↓
Companies Table  Financial Metrics   Error Log
(10 records)    (320+ records)    (if any failures)
```

## Metrics Collected

For each company, the pipeline collects **quarterly data** for:

1. **Revenue** - Total quarterly revenue in USD
2. **Gross Margin** - (Gross Profit / Revenue) × 100
3. **Operating Margin** - (Operating Income / Revenue) × 100
4. **Earnings Growth** - Year-over-year earnings growth percentage

**Total Expected Metrics**: ~320 records
- 10 companies × 8 quarters × 4 metrics = 320 metrics

## Error Handling

### Graceful Degradation
The pipeline continues processing even if individual companies fail:
- Errors are logged but don't stop execution
- Failed companies are reported in the final summary
- Partial data is committed to the database

### Retry Logic
- 3 retry attempts per API call
- Exponential backoff: 1s, 2s, 4s
- Handles transient network errors

### Duplicate Handling
- Uses PostgreSQL `ON CONFLICT DO UPDATE`
- Updates existing records instead of failing
- Idempotent: can be run multiple times safely

## Database Requirements

### Required Tables
1. **companies** - Company master data
2. **financial_metrics** - TimescaleDB hypertable for time-series metrics

### Database Connection
Configure in `.env`:
```bash
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=intel_user
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=corporate_intel
```

## Running with Docker

If using Docker Compose:

```bash
# Start database
docker-compose up -d postgres

# Run migrations
alembic upgrade head

# Run ingestion
docker-compose exec api python -m src.pipeline.yahoo_finance_ingestion
```

## Monitoring

### Log Output
The pipeline provides detailed logging:
- Progress: `[X/10] Processing TICKER - Company Name`
- Company status: `Created company: TICKER` or `Updated company: TICKER`
- Metrics: `Ingested N quarters of financial data for TICKER`
- Final summary with statistics

### Coordination Hooks
The pipeline integrates with Claude Flow for tracking:
- Pre-task hook on start
- Progress notifications during execution
- Post-task hook on completion

View hook data:
```bash
npx claude-flow@alpha hooks session-restore --session-id "swarm-yahoo-ingestion"
```

## Troubleshooting

### No data for ARCE
Arco Platform (ARCE) may have limited data on Yahoo Finance. This is expected and the pipeline will skip it gracefully.

### TimescaleDB Warning
```
SAWarning: Can't validate argument 'timescaledb_hypertable'
```
This is a SQLAlchemy warning about TimescaleDB-specific table options. It's safe to ignore - the hypertable will be created properly via Alembic migrations.

### Database Connection Error
```
could not connect to server
```
**Solution**: Ensure PostgreSQL is running and credentials in `.env` are correct.

### Missing Dependencies
```
No module named 'yfinance'
```
**Solution**: Install dependencies:
```bash
pip install -r requirements.txt
```

## Performance

- **Validation Test**: ~10 seconds
- **Full Ingestion**: 1-2 minutes
- **Per Company**: 5-10 seconds
- **Total Records**: 10 companies + 320 metrics

## Next Steps

After successful ingestion:

1. **Query the data**:
   ```sql
   SELECT c.ticker, c.name, COUNT(fm.id) as metrics_count
   FROM companies c
   LEFT JOIN financial_metrics fm ON c.id = fm.company_id
   GROUP BY c.id, c.ticker, c.name
   ORDER BY c.ticker;
   ```

2. **Visualize in Dash**:
   ```bash
   python src/visualization/dash_app.py
   ```

3. **Schedule periodic updates**:
   - Set up cron job
   - Use Prefect workflow
   - Or run manually quarterly

## Related Documentation

- [Yahoo Finance Ingestion Guide](../docs/YAHOO_FINANCE_INGESTION.md)
- [Database Schema](../docs/DATABASE_SCHEMA.md)
- [Data Connectors](../src/connectors/data_sources.py)
