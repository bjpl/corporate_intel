{{ config(
    materialized='table',
    indexes=[
        {'columns': ['ticker'], 'unique': True},
        {'columns': ['edtech_category'], 'unique': False}
    ],
    tags=['marts', 'finance', 'executive']
) }}

WITH quarterly_metrics AS (
    SELECT * FROM {{ ref('int_company_metrics_quarterly') }}
),

latest_quarter AS (
    SELECT MAX(metric_quarter) AS max_quarter
    FROM quarterly_metrics
),

current_metrics AS (
    SELECT
        q.*,
        ROW_NUMBER() OVER (PARTITION BY q.company_id ORDER BY q.metric_quarter DESC) AS quarter_rank
    FROM quarterly_metrics q
    WHERE q.metric_quarter >= DATE_TRUNC('quarter', CURRENT_DATE - INTERVAL '2 years')
),

company_summary AS (
    SELECT
        company_id,
        ticker,
        company_name,
        edtech_category,
        delivery_model,
        
        -- Latest metrics (most recent quarter)
        MAX(CASE WHEN quarter_rank = 1 THEN revenue END) AS latest_revenue,
        MAX(CASE WHEN quarter_rank = 1 THEN monthly_active_users END) AS latest_mau,
        MAX(CASE WHEN quarter_rank = 1 THEN arpu END) AS latest_arpu,
        MAX(CASE WHEN quarter_rank = 1 THEN net_revenue_retention END) AS latest_nrr,
        MAX(CASE WHEN quarter_rank = 1 THEN gross_margin END) AS latest_gross_margin,
        MAX(CASE WHEN quarter_rank = 1 THEN ltv_cac_ratio END) AS latest_ltv_cac_ratio,
        
        -- Growth metrics
        MAX(CASE WHEN quarter_rank = 1 THEN revenue_qoq_growth END) AS revenue_qoq_growth,
        MAX(CASE WHEN quarter_rank = 1 THEN revenue_yoy_growth END) AS revenue_yoy_growth,
        MAX(CASE WHEN quarter_rank = 1 THEN mau_yoy_growth END) AS mau_yoy_growth,
        
        -- Historical averages (last 4 quarters)
        AVG(CASE WHEN quarter_rank <= 4 THEN revenue END) AS revenue_4q_avg,
        AVG(CASE WHEN quarter_rank <= 4 THEN net_revenue_retention END) AS nrr_4q_avg,
        AVG(CASE WHEN quarter_rank <= 4 THEN gross_margin END) AS gross_margin_4q_avg,
        
        -- Volatility metrics
        STDDEV(CASE WHEN quarter_rank <= 8 THEN revenue_qoq_growth END) AS revenue_growth_volatility,
        
        -- Trend indicators (comparing last 2 quarters to previous 2)
        AVG(CASE WHEN quarter_rank IN (1, 2) THEN revenue END) - 
        AVG(CASE WHEN quarter_rank IN (3, 4) THEN revenue END) AS revenue_trend,
        
        AVG(CASE WHEN quarter_rank IN (1, 2) THEN monthly_active_users END) - 
        AVG(CASE WHEN quarter_rank IN (3, 4) THEN monthly_active_users END) AS mau_trend,
        
        -- Data completeness
        COUNT(DISTINCT metric_quarter) AS quarters_available,
        MAX(metric_quarter) AS latest_data_quarter,
        AVG(metrics_available) AS avg_metrics_completeness
        
    FROM current_metrics
    GROUP BY company_id, ticker, company_name, edtech_category, delivery_model
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
            WHEN latest_ltv_cac_ratio >= 3 THEN 100
            WHEN latest_ltv_cac_ratio >= 2 THEN 80
            WHEN latest_ltv_cac_ratio >= 1.5 THEN 60
            WHEN latest_ltv_cac_ratio >= 1 THEN 40
            ELSE 20
        END AS efficiency_score
        
    FROM company_summary
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
        latest_ltv_cac_ratio,
        
        -- Growth metrics
        revenue_qoq_growth,
        revenue_yoy_growth,
        mau_yoy_growth,
        
        -- Historical metrics
        revenue_4q_avg,
        nrr_4q_avg,
        gross_margin_4q_avg,
        revenue_growth_volatility,
        
        -- Trends
        CASE 
            WHEN revenue_trend > 0 THEN 'Growing'
            WHEN revenue_trend < 0 THEN 'Declining'
            ELSE 'Stable'
        END AS revenue_trend_direction,
        
        CASE 
            WHEN mau_trend > 0 THEN 'Growing'
            WHEN mau_trend < 0 THEN 'Declining'
            ELSE 'Stable'
        END AS user_trend_direction,
        
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
            WHEN latest_nrr >= 110 AND revenue_yoy_growth >= 20 AND latest_ltv_cac_ratio >= 2 
            THEN 'Excellent'
            WHEN latest_nrr >= 100 AND revenue_yoy_growth >= 0 AND latest_ltv_cac_ratio >= 1.5 
            THEN 'Good'
            WHEN latest_nrr >= 90 OR revenue_yoy_growth < 0 OR latest_ltv_cac_ratio < 1 
            THEN 'Needs Attention'
            ELSE 'At Risk'
        END AS company_health_status,
        
        -- Data quality
        quarters_available,
        latest_data_quarter,
        avg_metrics_completeness,
        
        CASE 
            WHEN latest_data_quarter >= DATE_TRUNC('quarter', CURRENT_DATE - INTERVAL '3 months')
            THEN 'Current'
            WHEN latest_data_quarter >= DATE_TRUNC('quarter', CURRENT_DATE - INTERVAL '6 months')
            THEN 'Recent'
            ELSE 'Stale'
        END AS data_freshness,
        
        CURRENT_TIMESTAMP AS refreshed_at
        
    FROM company_rankings
)

SELECT * FROM final
ORDER BY overall_score DESC