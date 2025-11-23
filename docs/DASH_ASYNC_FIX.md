# Dashboard Async Event Loop Fix

## Problem Summary

**Error**: `RuntimeError: asyncio.run() cannot be called from a running event loop`

**Root Cause**: Dash applications run inside an existing asyncio event loop. When callbacks attempted to use `asyncio.run()` to execute async database queries, it conflicted with Dash's event loop, causing the application to crash.

## Solution Implemented

Converted dashboard database queries from **asynchronous** to **synchronous** using standard SQLAlchemy (psycopg2 driver).

### Changes Made

#### 1. Updated Imports (lines 3-17)
```python
# REMOVED:
import asyncio
from src.db.session import get_db, get_session_factory
from src.services.dashboard_service import DashboardService

# ADDED:
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
```

#### 2. Modified Dashboard Initialization (lines 35-57)
```python
def __init__(self):
    self.settings = get_settings()
    self.logger = logging.getLogger(__name__)

    # Create synchronous database engine for Dash callbacks
    try:
        sync_url = self.settings.sync_database_url  # Uses psycopg2
        self.engine = create_engine(sync_url, pool_pre_ping=True)
        self.logger.info("Database engine initialized successfully")
    except Exception as e:
        self.logger.warning(f"Failed to initialize database engine: {e}. Will use sample data.")
        self.engine = None
```

#### 3. Rewrote update_data Callback (lines 477-604)

**Before** (async with asyncio.run):
```python
async def fetch_data():
    session_factory = get_session_factory()
    async with session_factory() as session:
        service = DashboardService(session)
        companies_data = await service.get_company_performance(...)
        # ... more async calls
        return companies_data, market_data, freshness

companies_data, market_data, freshness = asyncio.run(fetch_data())  # ❌ FAILS
```

**After** (synchronous queries):
```python
if self.engine is None:
    raise SQLAlchemyError("Database engine not initialized")

with self.engine.connect() as conn:
    # Direct SQL queries using synchronous connection
    company_query = text("""
        SELECT ticker, company_name, edtech_category, ...
        FROM public_marts.mart_company_performance
        WHERE (:category IS NULL OR edtech_category = :category)
        ORDER BY latest_revenue DESC NULLS LAST
    """)

    company_result = conn.execute(company_query, {"category": category_filter})
    companies_data = [dict(row._mapping) for row in company_result]
```

## Benefits

1. **No Event Loop Conflicts**: Synchronous queries work seamlessly in Dash callbacks
2. **Simpler Code**: Direct SQL queries without async/await complexity
3. **Better Performance**: No event loop overhead for simple queries
4. **Robust Fallback**: Gracefully falls back to sample data if database unavailable
5. **Production Ready**: Uses connection pooling and pre-ping for reliability

## Database URL Configuration

The fix leverages the existing `sync_database_url` property in `src/core/config.py`:

```python
@property
def sync_database_url(self) -> str:
    """Build synchronous PostgreSQL connection URL."""
    password = self.POSTGRES_PASSWORD.get_secret_value()
    return f"postgresql://{self.POSTGRES_USER}:{password}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
```

This uses the **psycopg2** driver (already in requirements.txt) instead of asyncpg.

## Testing

Created test suite to verify:
- ✅ No `asyncio.run()` calls in dashboard code
- ✅ Synchronous SQLAlchemy imports present
- ✅ Sync database engine creation works
- ✅ Parameterized queries with NULL handling
- ✅ Graceful fallback to sample data

**Test Files**:
- `tests/test_dash_sync_simple.py` - Standalone verification test
- `tests/test_dash_db_connection.py` - Comprehensive pytest suite

## Dependencies

No new dependencies required! Uses existing packages:
- `sqlalchemy>=2.0.0` (already installed)
- `psycopg2-binary>=2.9.0` (already installed)

## Running the Dashboard

```bash
# Standard startup
python src/visualization/dash_app.py

# Access at http://localhost:8050
```

The dashboard will:
1. Attempt to connect to PostgreSQL using sync engine
2. Query data from `public_marts.mart_company_performance` and `public_marts.mart_competitive_landscape`
3. Fall back to sample data if database unavailable (with clear UI message)
4. Auto-refresh every 60 seconds with fresh data

## Files Modified

| File | Lines Changed | Description |
|------|--------------|-------------|
| `src/visualization/dash_app.py` | 3-17, 35-57, 477-604 | Removed asyncio, added sync SQLAlchemy queries |

## Files Added

| File | Description |
|------|-------------|
| `tests/test_dash_sync_simple.py` | Standalone test for sync database queries |
| `tests/test_dash_db_connection.py` | Comprehensive pytest suite |
| `docs/DASH_ASYNC_FIX.md` | This documentation |

## Future Considerations

While synchronous queries work perfectly for dashboard callbacks, consider these optimizations:

1. **Query Optimization**: Add indexes on frequently filtered columns (edtech_category, ticker)
2. **Caching**: Implement Redis caching for slow-changing aggregate data
3. **Connection Pooling**: Tune pool size for concurrent dashboard users
4. **Materialized Views**: Pre-compute expensive aggregations

## Verification

Run the verification test:

```bash
python tests/test_dash_sync_simple.py
```

Expected output:
```
✓ No asyncio.run() found in dash_app.py
✓ Synchronous SQLAlchemy imports present
✓ Using sync_database_url property
✓ ALL TESTS PASSED
```

---

**Status**: ✅ FIXED - Dashboard now runs without async event loop errors

**Author**: Claude Code Implementation Agent
**Date**: 2025-10-05
**Issue**: RuntimeError: asyncio.run() cannot be called from a running event loop
**Solution**: Synchronous SQLAlchemy queries with psycopg2 driver
