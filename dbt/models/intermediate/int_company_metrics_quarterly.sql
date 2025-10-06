{{ config(
    materialized='table',
    indexes=[
        {'columns': ['company_id'], 'unique': False},
        {'columns': ['ticker'], 'unique': False}
    ],
    tags=['intermediate', 'latest']
) }}

-- Simplified intermediate model for competitive intelligence
-- Focus: Latest metrics per company for comparison, not time-series analysis

WITH companies AS (
    SELECT * FROM {{ ref('stg_companies') }}
),

metrics AS (
    SELECT * FROM {{ ref('stg_financial_metrics') }}
    WHERE is_high_confidence = 1
    AND is_valid_range = 1
),

-- Get latest metrics for each company and metric type
latest_metrics AS (
    SELECT
        company_id,
        metric_type,
        metric_value,
        metric_date,
        metric_quarter,
        data_source,
        confidence_score,
        ROW_NUMBER() OVER (
            PARTITION BY company_id, metric_type
            ORDER BY metric_date DESC
        ) AS recency_rank
    FROM metrics
),

-- Pivot to get latest value for each metric type
pivoted AS (
    SELECT
        company_id,

        -- Financial metrics
        MAX(CASE WHEN metric_type = 'revenue' AND recency_rank = 1 THEN metric_value END) AS latest_revenue,
        MAX(CASE WHEN metric_type = 'gross_margin' AND recency_rank = 1 THEN metric_value END) AS latest_gross_margin,
        MAX(CASE WHEN metric_type = 'operating_margin' AND recency_rank = 1 THEN metric_value END) AS latest_operating_margin,
        MAX(CASE WHEN metric_type = 'profit_margin' AND recency_rank = 1 THEN metric_value END) AS latest_profit_margin,

        -- Growth metrics
        MAX(CASE WHEN metric_type = 'revenue_growth_yoy' AND recency_rank = 1 THEN metric_value END) AS revenue_yoy_growth,
        MAX(CASE WHEN metric_type = 'earnings_growth' AND recency_rank = 1 THEN metric_value END) AS earnings_growth,

        -- Valuation metrics (from Alpha Vantage)
        MAX(CASE WHEN metric_type = 'pe_ratio' AND recency_rank = 1 THEN metric_value END) AS pe_ratio,
        MAX(CASE WHEN metric_type = 'forward_pe' AND recency_rank = 1 THEN metric_value END) AS forward_pe,
        MAX(CASE WHEN metric_type = 'market_cap' AND recency_rank = 1 THEN metric_value END) AS market_cap,

        -- Mock/estimated metrics (for dashboard compatibility)
        -- These would come from additional data sources in production
        NULL::FLOAT AS latest_mau,
        NULL::FLOAT AS latest_arpu,
        100::FLOAT AS latest_nrr,  -- Assume 100% as baseline
        NULL::FLOAT AS latest_ltv_cac_ratio,

        -- Data quality
        MAX(metric_date) AS latest_data_date,
        AVG(confidence_score) AS avg_confidence_score,
        COUNT(DISTINCT metric_type) AS metrics_available

    FROM latest_metrics
    WHERE recency_rank = 1
    GROUP BY company_id
),

final AS (
    SELECT
        c.company_id,
        c.ticker,
        c.company_name,
        c.edtech_category,
        c.delivery_model,

        -- Latest metrics
        p.latest_revenue,
        p.latest_gross_margin,
        p.latest_operating_margin,
        p.latest_profit_margin,
        p.latest_mau,
        p.latest_arpu,
        p.latest_nrr,
        p.latest_ltv_cac_ratio,

        -- Growth
        p.revenue_yoy_growth,
        p.earnings_growth,

        -- Valuation
        p.pe_ratio,
        p.forward_pe,
        p.market_cap,

        -- Mock calculated metrics for dashboard
        CASE
            WHEN p.latest_ltv_cac_ratio > 0
            THEN p.latest_ltv_cac_ratio
            ELSE 2.5  -- Mock LTV/CAC ratio
        END AS ltv_cac_ratio,

        -- Data quality
        p.latest_data_date,
        p.avg_confidence_score,
        p.metrics_available,

        CURRENT_TIMESTAMP AS refreshed_at

    FROM companies c
    LEFT JOIN pivoted p ON c.company_id = p.company_id
    WHERE p.latest_revenue IS NOT NULL  -- Only companies with revenue data
)

SELECT * FROM final
