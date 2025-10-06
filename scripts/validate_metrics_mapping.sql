-- Validation script for dbt metrics mapping fix
-- Run this after `dbt build` to verify metrics are properly populated

-- 1. Check raw metrics in staging (should now include negative values)
SELECT
    metric_type,
    COUNT(*) AS total_count,
    COUNT(DISTINCT company_id) AS companies_with_metric,
    MIN(metric_value) AS min_value,
    MAX(metric_value) AS max_value,
    AVG(metric_value) AS avg_value,
    COUNT(*) FILTER (WHERE metric_value < 0) AS negative_values
FROM stg_financial_metrics
WHERE is_high_confidence = 1 AND is_valid_range = 1
GROUP BY metric_type
ORDER BY total_count DESC;

-- 2. Check intermediate model pivoted metrics
SELECT
    COUNT(*) FILTER (WHERE latest_revenue IS NOT NULL) AS has_revenue,
    COUNT(*) FILTER (WHERE latest_gross_margin IS NOT NULL) AS has_gross_margin,
    COUNT(*) FILTER (WHERE latest_operating_margin IS NOT NULL) AS has_operating_margin,
    COUNT(*) FILTER (WHERE latest_profit_margin IS NOT NULL) AS has_profit_margin,
    COUNT(*) FILTER (WHERE revenue_yoy_growth IS NOT NULL) AS has_yoy_growth,
    COUNT(*) FILTER (WHERE earnings_growth IS NOT NULL) AS has_earnings_growth,
    COUNT(*) FILTER (WHERE pe_ratio IS NOT NULL) AS has_pe_ratio,
    COUNT(*) FILTER (WHERE forward_pe IS NOT NULL) AS has_forward_pe,
    COUNT(*) FILTER (WHERE market_cap IS NOT NULL) AS has_market_cap,
    COUNT(*) FILTER (WHERE eps IS NOT NULL) AS has_eps,
    COUNT(*) FILTER (WHERE roe IS NOT NULL) AS has_roe,
    COUNT(*) AS total_companies
FROM int_company_metrics_quarterly;

-- 3. Check mart company performance
SELECT
    COUNT(*) FILTER (WHERE revenue_yoy_growth IS NOT NULL) AS has_yoy_growth,
    COUNT(*) FILTER (WHERE pe_ratio IS NOT NULL) AS has_pe_ratio,
    COUNT(*) FILTER (WHERE earnings_growth IS NOT NULL) AS has_earnings_growth,
    COUNT(*) FILTER (WHERE eps IS NOT NULL) AS has_eps,
    COUNT(*) FILTER (WHERE roe IS NOT NULL) AS has_roe,
    COUNT(*) AS total_companies,
    AVG(overall_score) AS avg_overall_score
FROM mart_company_performance;

-- 4. Show sample companies with all metrics
SELECT
    ticker,
    company_name,
    latest_revenue,
    revenue_yoy_growth,
    earnings_growth,
    latest_gross_margin,
    latest_operating_margin,
    pe_ratio,
    forward_pe,
    eps,
    roe,
    overall_score,
    company_health_status
FROM mart_company_performance
WHERE revenue_yoy_growth IS NOT NULL OR pe_ratio IS NOT NULL
ORDER BY overall_score DESC
LIMIT 10;

-- 5. Verify competitive landscape mart
SELECT
    edtech_category,
    companies_in_segment,
    total_segment_revenue,
    total_segment_market_cap,
    avg_revenue_growth,
    avg_gross_margin,
    avg_operating_margin,
    avg_pe_ratio,
    avg_roe,
    market_stage,
    segment_economics,
    strategic_recommendation
FROM mart_competitive_landscape
ORDER BY total_segment_revenue DESC;

-- 6. Check for any companies with negative growth (should exist now)
SELECT
    ticker,
    company_name,
    revenue_yoy_growth,
    earnings_growth,
    company_health_status
FROM mart_company_performance
WHERE revenue_yoy_growth < 0 OR earnings_growth < 0
ORDER BY revenue_yoy_growth;

-- 7. Verify data quality metrics
SELECT
    data_freshness,
    COUNT(*) AS company_count,
    AVG(metrics_available) AS avg_metrics_per_company
FROM mart_company_performance
GROUP BY data_freshness
ORDER BY data_freshness;
