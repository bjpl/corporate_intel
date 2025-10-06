# dbt Metrics Mapping Fix - Summary

## Problem Identified
The dbt intermediate model (`int_company_metrics_quarterly.sql`) was correctly configured, but the staging model (`stg_financial_metrics.sql`) was filtering out negative values, which prevented growth metrics from being materialized.

## Root Cause
**Staging Model Filter Issue:**
- Line 59 had: `AND value >= 0`
- This filtered out all negative growth metrics (revenue_growth_yoy, earnings_growth)
- Growth can legitimately be negative (declining revenue/earnings)

## Changes Made

### 1. Fixed Staging Model (`stg_financial_metrics.sql`)
**Before:**
```sql
WHERE
    value IS NOT NULL
    AND value >= 0  -- ❌ Too restrictive!
    AND metric_date <= CURRENT_DATE
```

**After:**
```sql
WHERE
    value IS NOT NULL
    -- Allow negative values for growth metrics and margins
    AND metric_date <= CURRENT_DATE
```

### 2. Enhanced Intermediate Model (`int_company_metrics_quarterly.sql`)
**Added Missing Metrics:**
```sql
-- Added to pivoted CTE:
MAX(CASE WHEN metric_type = 'eps' AND recency_rank = 1 THEN metric_value END) AS eps,
MAX(CASE WHEN metric_type = 'roe' AND recency_rank = 1 THEN metric_value END) AS roe,

-- Removed mock fields:
- latest_mau (NULL)
- latest_arpu (NULL)
- latest_nrr (100::FLOAT)
- latest_ltv_cac_ratio (NULL)
```

**Complete Metric Mapping (Actual Data):**
- `revenue`: Revenue (115 rows, 23 companies)
- `gross_margin`: Gross margin %
- `operating_margin`: Operating margin %
- `profit_margin`: Profit margin %
- `earnings_growth`: Earnings growth % (67 rows, 12 companies)
- `revenue_growth_yoy`: Revenue YoY growth % (5 rows from Alpha Vantage)
- `pe_ratio`: Price-to-earnings ratio (5 rows)
- `forward_pe`: Forward P/E ratio (5 rows)
- `market_cap`: Market capitalization (5 rows)
- `eps`: Earnings per share (5 rows)
- `roe`: Return on equity % (5 rows)

### 3. Updated Mart Models

#### `mart_company_performance.sql`
**Removed Fields:**
- `latest_mau`, `latest_arpu`, `latest_nrr`, `latest_ltv_cac_ratio`
- `nrr_rank_in_category`
- `retention_score`, `efficiency_score`

**Added Fields:**
- `eps`, `roe`
- `margin_score`, `profitability_score`

**Updated Health Status Logic:**
```sql
-- Old (used non-existent fields):
WHEN latest_nrr >= 110 AND revenue_yoy_growth >= 20 AND ltv_cac_ratio >= 2

-- New (uses actual metrics):
WHEN revenue_yoy_growth >= 20 AND latest_operating_margin >= 10 AND latest_gross_margin >= 60
```

#### `mart_competitive_landscape.sql`
**Removed Fields:**
- `total_segment_users`
- `avg_nrr`, `median_nrr`
- `avg_ltv_cac_ratio`

**Added Fields:**
- `total_segment_market_cap`
- `avg_operating_margin`, `avg_profit_margin`
- `avg_pe_ratio`, `avg_roe`

**Updated Segment Economics Logic:**
```sql
-- Old (used non-existent fields):
WHEN avg_ltv_cac_ratio > 3 AND avg_nrr > 110 THEN 'Strong Unit Economics'

-- New (uses actual profitability metrics):
WHEN avg_gross_margin > 70 AND avg_operating_margin > 10 AND avg_roe > 15 THEN 'Strong Profitability'
```

## Expected Results After Rebuild

After running `dbt build`, the marts should now show:

### Companies with Growth Metrics:
- **revenue_yoy_growth**: 5 companies (was 0)
  - CHGG, LRFC, ATGE, DUOL, UDMY
- **earnings_growth**: 12 companies (was NULL)

### Companies with Valuation Metrics:
- **pe_ratio**: 3 companies (was 0)
- **forward_pe**: 3 companies (was 0)
- **eps**: 5 companies (was NULL)
- **roe**: 5 companies (was NULL)

### Companies with Financial Metrics:
- **revenue**: 23 companies
- **gross_margin**: 23 companies
- **operating_margin**: 24 companies
- **profit_margin**: 5 companies

## Validation Query

Run this to verify metrics are populated:
```sql
SELECT
    COUNT(*) FILTER (WHERE revenue_yoy_growth IS NOT NULL) AS has_yoy_growth,
    COUNT(*) FILTER (WHERE pe_ratio IS NOT NULL) AS has_pe_ratio,
    COUNT(*) FILTER (WHERE earnings_growth IS NOT NULL) AS has_earnings_growth,
    COUNT(*) FILTER (WHERE eps IS NOT NULL) AS has_eps,
    COUNT(*) FILTER (WHERE roe IS NOT NULL) AS has_roe,
    COUNT(*) AS total_companies
FROM mart_company_performance;
```

Expected:
- has_yoy_growth: 5
- has_pe_ratio: 3
- has_earnings_growth: 12
- has_eps: 5
- has_roe: 5
- total_companies: 23-24

## Files Modified

1. `dbt/models/staging/stg_financial_metrics.sql` - Removed `value >= 0` filter
2. `dbt/models/intermediate/int_company_metrics_quarterly.sql` - Added eps, roe; removed mock fields
3. `dbt/models/marts/finance/mart_company_performance.sql` - Updated to use actual metrics
4. `dbt/models/marts/intelligence/mart_competitive_landscape.sql` - Updated segment analysis

## Next Steps

1. Run `dbt build` to materialize all models
2. Verify mart tables have non-NULL values
3. Update dashboard to use new field names (removed MAU, ARPU, NRR, LTV/CAC)
4. Consider adding more Alpha Vantage tickers to get broader valuation coverage
