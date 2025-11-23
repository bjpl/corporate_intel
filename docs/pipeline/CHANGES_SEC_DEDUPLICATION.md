# SEC Company Deduplication - Change Summary

## Changes Made

### 1. New Function: `get_or_create_company()`

**Location**: `src/pipeline/sec_ingestion.py` (lines 467-559)

**Purpose**: Centralized company lookup/creation logic with intelligent matching

**Key Features**:
- Three-tier lookup strategy (CIK -> Ticker -> Create)
- Fetches proper company names from SEC API
- Uses SEC ticker-to-CIK mappings for reverse lookup
- Prevents duplicate company records
- Comprehensive logging at each step

### 2. Modified Function: `store_filing()`

**Location**: `src/pipeline/sec_ingestion.py` (line 595)

**Change**: Replaced inline company lookup with call to new `get_or_create_company()` function

**Before**:
```python
# Check if company exists by CIK, create if not
result = await session.execute(
    select(Company).where(Company.cik == company_cik)
)
company = result.scalar_one_or_none()

if company is None:
    # Create new company record with basic info from filing
    logger.info(f"Creating new company record for CIK {company_cik}")
    company = Company(
        cik=company_cik,
        ticker=filing_data.get("ticker", company_cik),
        name=filing_data.get("companyName", f"Company CIK {company_cik}"),  # Problem!
        category=filing_data.get("category", "enabling_technology"),
    )
```

**After**:
```python
# Get or create company using improved lookup logic
company = await get_or_create_company(session, company_cik, filing_data)
```

## Lookup Logic Flow

```
┌─────────────────────────────────────┐
│ Start: Get/Create Company           │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ 1. Lookup by CIK                    │
│    SELECT * FROM companies          │
│    WHERE cik = ?                    │
└──────────────┬──────────────────────┘
               │
        ┌──────┴──────┐
        │             │
     Found          Not Found
        │             │
        ▼             ▼
   ┌────────┐  ┌──────────────────────┐
   │ Return │  │ 2. Get SEC Ticker    │
   │ Existing│  │    Mapping (cached)  │
   └────────┘  └──────┬───────────────┘
                      │
                      ▼
               ┌─────────────────────────┐
               │ 3. Reverse Lookup       │
               │    CIK -> Ticker        │
               └──────┬──────────────────┘
                      │
                      ▼
               ┌─────────────────────────┐
               │ 4. Lookup by Ticker     │
               │    SELECT * FROM companies│
               │    WHERE ticker = ?      │
               └──────┬──────────────────┘
                      │
               ┌──────┴──────┐
               │             │
            Found          Not Found
               │             │
               ▼             ▼
        ┌─────────────┐  ┌────────────────┐
        │ Update CIK  │  │ 5. Fetch Name  │
        │ Return      │  │    from SEC API│
        └─────────────┘  └──────┬─────────┘
                                │
                                ▼
                         ┌──────────────────┐
                         │ 6. Create Company│
                         │    with proper   │
                         │    name & data   │
                         └──────┬───────────┘
                                │
                                ▼
                         ┌──────────────────┐
                         │ Return New       │
                         │ Company          │
                         └──────────────────┘
```

## Testing

### Test Coverage
- `tests/test_sec_company_lookup.py`: 5 test cases covering all scenarios

### Test Scenarios
1. **Existing Company (CIK)**: Finds company by CIK, no duplicates
2. **Existing Company (Ticker)**: Finds company by ticker when CIK missing
3. **New Company**: Creates company with proper SEC name
4. **Rerun Safety**: No duplicates when script runs multiple times
5. **CIK Update**: Updates CIK when found by ticker

## Impact Analysis

### Positive Impacts
- No more duplicate "Company CIK [number]" records
- Proper company names in database
- Safe to run script multiple times
- Better data quality and integrity

### Breaking Changes
- None - fully backward compatible

### Migration Required
- Optional: Clean up existing "Company CIK [number]" duplicates

## Verification Steps

1. **Syntax Check**: `python -m py_compile src/pipeline/sec_ingestion.py` ✓
2. **Unit Tests**: `pytest tests/test_sec_company_lookup.py -v`
3. **Integration Test**: Run script on test data
4. **Database Check**: Verify no "Company CIK" records created

## Files Changed

```
src/pipeline/sec_ingestion.py              (Modified - 93 lines added/changed)
tests/test_sec_company_lookup.py           (New - 169 lines)
docs/pipeline/sec_company_deduplication.md (New - documentation)
docs/pipeline/CHANGES_SEC_DEDUPLICATION.md (New - this file)
```

## Performance Impact

- **Minimal**: Added lookups use indexed columns (CIK, ticker)
- **Cached**: SEC ticker mappings cached in memory
- **Optimized**: Only fetches company info when creating new records
- **Rate Limited**: Respects SEC API rate limits

## Example Output

### Before Fix
```
INFO: Creating new company record for CIK 0000320193
INFO: Created company abc-123 for CIK 0000320193
INFO: Successfully stored filing ... for company Company CIK 0000320193
```

### After Fix
```
INFO: Retrieved company name from SEC: Apple Inc.
INFO: Creating new company record for CIK 0000320193: Apple Inc.
INFO: Created company abc-123 for CIK 0000320193: Apple Inc.
INFO: Successfully stored filing ... for company Apple Inc. (CIK: 0000320193)
```

### On Rerun (After Fix)
```
INFO: Found existing company by CIK: Apple Inc. (CIK: 0000320193, ID: abc-123)
INFO: Successfully stored filing ... for company Apple Inc. (CIK: 0000320193)
```

## Next Steps

1. Run unit tests to verify functionality
2. Test on staging environment with real data
3. Monitor logs for proper company matching
4. Clean up any existing duplicate records
5. Document cleanup procedure for production

## Rollback Plan

If issues arise, revert to previous version:
```bash
git revert HEAD
```

The original functionality is preserved in git history.
