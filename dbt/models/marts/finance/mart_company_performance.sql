{{ config(
    materialized='table',
    indexes=[
        {'columns': ['ticker'], 'unique': True},
        {'columns': ['edtech_category'], 'unique': False}
    ],
    tags=['marts', 'finance', 'executive']
) }}

-- Simplified mart for competitive intelligence
-- Focus: Latest company metrics for comparison

WITH company_metrics AS (
    SELECT * FROM {{ ref('int_company_metrics_quarterly') }}
),

company_rankings AS (
    SELECT
        *,

        -- Rankings within category
        RANK() OVER (PARTITION BY edtech_category ORDER BY latest_revenue DESC NULLS LAST) AS revenue_rank_in_category,
        RANK() OVER (PARTITION BY edtech_category ORDER BY revenue_yoy_growth DESC NULLS LAST) AS growth_rank_in_category,
        RANK() OVER (PARTITION BY edtech_category ORDER BY latest_nrr DESC NULLS LAST) AS nrr_rank_in_category,

        -- Overall rankings
        RANK() OVER (ORDER BY latest_revenue DESC NULLS LAST) AS revenue_rank_overall,
        RANK() OVER (ORDER BY revenue_yoy_growth DESC NULLS LAST) AS growth_rank_overall,

        -- Performance scores (0-100)
        CASE
            WHEN latest_nrr >= 120 THEN 100
            WHEN latest_nrr >= 110 THEN 80
            WHEN latest_nrr >= 100 THEN 60
            WHEN latest_nrr >= 90 THEN 40
            ELSE 20
        END AS retention_score,

        CASE
            WHEN revenue_yoy_growth >= 50 THEN 100
            WHEN revenue_yoy_growth >= 30 THEN 80
            WHEN revenue_yoy_growth >= 15 THEN 60
            WHEN revenue_yoy_growth >= 0 THEN 40
            ELSE 20
        END AS growth_score,

        CASE
            WHEN ltv_cac_ratio >= 3 THEN 100
            WHEN ltv_cac_ratio >= 2 THEN 80
            WHEN ltv_cac_ratio >= 1.5 THEN 60
            WHEN ltv_cac_ratio >= 1 THEN 40
            ELSE 20
        END AS efficiency_score

    FROM company_metrics
),

final AS (
    SELECT
        -- Identifiers
        company_id,
        ticker,
        company_name,
        edtech_category,
        delivery_model,

        -- Current metrics
        latest_revenue,
        latest_mau,
        latest_arpu,
        latest_nrr,
        latest_gross_margin,
        ltv_cac_ratio AS latest_ltv_cac_ratio,

        -- Growth metrics
        revenue_yoy_growth,
        earnings_growth,

        -- Valuation
        pe_ratio,
        forward_pe,
        market_cap,

        -- Rankings
        revenue_rank_in_category,
        growth_rank_in_category,
        nrr_rank_in_category,
        revenue_rank_overall,
        growth_rank_overall,

        -- Performance scores
        retention_score,
        growth_score,
        efficiency_score,
        (retention_score + growth_score + efficiency_score) / 3.0 AS overall_score,

        -- Health indicators
        CASE
            WHEN latest_nrr >= 110 AND revenue_yoy_growth >= 20 AND ltv_cac_ratio >= 2
            THEN 'Excellent'
            WHEN latest_nrr >= 100 AND revenue_yoy_growth >= 0 AND ltv_cac_ratio >= 1.5
            THEN 'Good'
            WHEN latest_nrr >= 90 OR revenue_yoy_growth < 0 OR ltv_cac_ratio < 1
            THEN 'Needs Attention'
            ELSE 'At Risk'
        END AS company_health_status,

        -- Data quality
        metrics_available,
        latest_data_date,

        CASE
            WHEN latest_data_date >= CURRENT_DATE - INTERVAL '3 months'
            THEN 'Current'
            WHEN latest_data_date >= CURRENT_DATE - INTERVAL '6 months'
            THEN 'Recent'
            ELSE 'Stale'
        END AS data_freshness,

        CURRENT_TIMESTAMP AS refreshed_at

    FROM company_rankings
)

SELECT * FROM final
ORDER BY overall_score DESC
