# SEC Company Deduplication Fix

## Overview

Fixed the SEC ingestion pipeline to prevent creating duplicate company records when processing filings. The script now properly looks up existing companies by both CIK and ticker before creating new records.

## Problem

The original implementation in `src/pipeline/sec_ingestion.py` would create duplicate company records with names like "Company CIK [number]" when it should have been linking filings to existing companies in the database.

### Root Cause
- Only looked up companies by CIK
- Did not check for existing companies by ticker
- Created new companies without fetching proper names from SEC
- No reverse lookup using SEC ticker-to-CIK mappings

## Solution

### New `get_or_create_company()` Function

Created a dedicated function that implements a three-tier lookup strategy:

#### 1. Lookup by CIK (Primary)
```python
# First try to find by CIK (most reliable identifier)
result = await session.execute(
    select(Company).where(Company.cik == company_cik)
)
company = result.scalar_one_or_none()
```

#### 2. Lookup by Ticker (Secondary)
```python
# Get ticker from SEC mappings by reverse lookup
ticker_mapping = await client.get_ticker_to_cik_mapping()
cik_to_ticker = {v: k for k, v in ticker_mapping.items()}
mapped_ticker = cik_to_ticker.get(company_cik.zfill(10))

if mapped_ticker:
    result = await session.execute(
        select(Company).where(Company.ticker == mapped_ticker)
    )
    company = result.scalar_one_or_none()
```

#### 3. Create with Proper Name (Fallback)
```python
# Fetch company name from SEC API
company_info_url = f"{client.BASE_URL}/submissions/CIK{company_cik.zfill(10)}.json"
response = await http_client.get(company_info_url, headers=client.headers)
company_name = company_info.get("name", f"Company CIK {company_cik}")

company = Company(
    cik=company_cik,
    ticker=mapped_ticker or ticker or company_cik,
    name=company_name,  # Proper name from SEC, not "Company CIK [number]"
    category=filing_data.get("category", "enabling_technology"),
)
```

## Benefits

1. **No More Duplicates**: Prevents creating duplicate company records when script runs multiple times
2. **Proper Names**: Uses real company names from SEC instead of generic "Company CIK [number]"
3. **Better Matching**: Finds existing companies by both CIK and ticker
4. **Auto-Update**: Updates missing CIK values when company is found by ticker
5. **Comprehensive Logging**: Shows when companies are found vs created

## Logging Output

The function now provides clear logging:

```
INFO: Found existing company by CIK: Apple Inc. (CIK: 0000320193, ID: abc-123)
INFO: Found existing company by ticker: Microsoft Corporation (ticker: MSFT, ID: def-456)
INFO: Retrieved company name from SEC: Alphabet Inc.
INFO: Creating new company record for CIK 0001652044: Alphabet Inc.
```

## Testing

Created comprehensive tests in `tests/test_sec_company_lookup.py`:

- `test_company_lookup_by_cik`: Verifies existing company found by CIK
- `test_company_lookup_by_ticker`: Verifies fallback to ticker lookup
- `test_company_creation_with_sec_name`: Verifies proper name retrieval from SEC
- `test_no_duplicate_company_on_rerun`: Verifies no duplicates on script rerun

## Migration Notes

### For Existing Duplicate Records

If you have existing "Company CIK [number]" records in the database:

1. Identify duplicates:
```sql
SELECT * FROM companies WHERE name LIKE 'Company CIK%';
```

2. Merge duplicate companies:
```sql
-- Update filings to point to correct company
UPDATE sec_filings
SET company_id = (SELECT id FROM companies WHERE cik = 'XXXX' AND name NOT LIKE 'Company CIK%')
WHERE company_id = (SELECT id FROM companies WHERE name = 'Company CIK XXXX');

-- Delete duplicate company records
DELETE FROM companies WHERE name LIKE 'Company CIK%';
```

### Running Script Again

The script is now safe to run multiple times without creating duplicates. It will:
- Find existing companies by CIK or ticker
- Link new filings to existing companies
- Only create companies that truly don't exist

## Code Changes

### Files Modified
- `src/pipeline/sec_ingestion.py`: Added `get_or_create_company()` function

### Files Added
- `tests/test_sec_company_lookup.py`: Comprehensive test suite
- `docs/pipeline/sec_company_deduplication.md`: This documentation

## Usage Example

```python
from src.pipeline.sec_ingestion import sec_ingestion_flow, FilingRequest

# First run - creates companies
await sec_ingestion_flow(FilingRequest(
    company_ticker="AAPL",
    filing_types=["10-K", "10-Q"]
))

# Second run - reuses existing companies (no duplicates!)
await sec_ingestion_flow(FilingRequest(
    company_ticker="AAPL",
    filing_types=["8-K"]
))
```

## Performance Considerations

- **SEC API Rate Limiting**: Still respects SEC rate limits when fetching company names
- **Caching**: SEC ticker mappings are cached in `SECAPIClient`
- **Database Queries**: Uses indexed lookups (CIK and ticker are both indexed)
- **Minimal Extra Calls**: Only fetches company info from SEC API when creating new companies

## Future Enhancements

Consider these improvements:
1. Cache company lookups in memory for batch processing
2. Add fuzzy matching for company names
3. Implement bulk company creation for better performance
4. Add data quality checks for company information
