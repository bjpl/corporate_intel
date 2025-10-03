{{ config(
    materialized='table',
    indexes=[
        {'columns': ['company_id', 'metric_quarter'], 'unique': False},
        {'columns': ['ticker', 'metric_quarter'], 'unique': False}
    ],
    tags=['intermediate', 'quarterly']
) }}

WITH companies AS (
    SELECT * FROM {{ ref('stg_companies') }}
),

metrics AS (
    SELECT * FROM {{ ref('stg_financial_metrics') }}
    WHERE is_high_confidence = 1
    AND is_valid_range = 1
),

quarterly_pivoted AS (
    SELECT
        company_id,
        metric_quarter,
        
        -- Financial metrics
        MAX(CASE WHEN metric_type = 'revenue' THEN metric_value END) AS revenue,
        MAX(CASE WHEN metric_type = 'gross_margin' THEN metric_value END) AS gross_margin,
        
        -- User metrics
        MAX(CASE WHEN metric_type = 'monthly_active_users' THEN metric_value END) AS monthly_active_users,
        MAX(CASE WHEN metric_type = 'average_revenue_per_user' THEN metric_value END) AS arpu,
        
        -- Unit economics
        MAX(CASE WHEN metric_type = 'customer_acquisition_cost' THEN metric_value END) AS cac,
        MAX(CASE WHEN metric_type = 'lifetime_value' THEN metric_value END) AS ltv,
        
        -- Retention metrics
        MAX(CASE WHEN metric_type = 'net_revenue_retention' THEN metric_value END) AS net_revenue_retention,
        MAX(CASE WHEN metric_type = 'churn_rate' THEN metric_value END) AS churn_rate,
        MAX(CASE WHEN metric_type = 'course_completion_rate' THEN metric_value END) AS completion_rate,
        
        -- Data quality
        AVG(confidence_score) AS avg_confidence_score,
        COUNT(DISTINCT metric_type) AS metrics_available
        
    FROM metrics
    GROUP BY company_id, metric_quarter
),

with_growth_rates AS (
    SELECT
        *,
        
        -- Calculate QoQ growth rates
        LAG(revenue) OVER (PARTITION BY company_id ORDER BY metric_quarter) AS prev_quarter_revenue,
        LAG(monthly_active_users) OVER (PARTITION BY company_id ORDER BY metric_quarter) AS prev_quarter_mau,
        
        -- Calculate YoY growth rates
        LAG(revenue, 4) OVER (PARTITION BY company_id ORDER BY metric_quarter) AS year_ago_revenue,
        LAG(monthly_active_users, 4) OVER (PARTITION BY company_id ORDER BY metric_quarter) AS year_ago_mau,
        
        -- Moving averages
        AVG(revenue) OVER (
            PARTITION BY company_id 
            ORDER BY metric_quarter 
            ROWS BETWEEN 3 PRECEDING AND CURRENT ROW
        ) AS revenue_4q_avg,
        
        AVG(net_revenue_retention) OVER (
            PARTITION BY company_id 
            ORDER BY metric_quarter 
            ROWS BETWEEN 3 PRECEDING AND CURRENT ROW
        ) AS nrr_4q_avg
        
    FROM quarterly_pivoted
),

final AS (
    SELECT
        c.company_id,
        c.ticker,
        c.company_name,
        c.edtech_category,
        c.delivery_model,
        m.metric_quarter,
        
        -- Metrics
        m.revenue,
        m.gross_margin,
        m.monthly_active_users,
        m.arpu,
        m.cac,
        m.ltv,
        m.net_revenue_retention,
        m.churn_rate,
        m.completion_rate,
        
        -- Growth rates
        CASE 
            WHEN m.prev_quarter_revenue > 0 
            THEN ((m.revenue - m.prev_quarter_revenue) / m.prev_quarter_revenue) * 100
            ELSE NULL 
        END AS revenue_qoq_growth,
        
        CASE 
            WHEN m.year_ago_revenue > 0 
            THEN ((m.revenue - m.year_ago_revenue) / m.year_ago_revenue) * 100
            ELSE NULL 
        END AS revenue_yoy_growth,
        
        CASE 
            WHEN m.prev_quarter_mau > 0 
            THEN ((m.monthly_active_users - m.prev_quarter_mau) / m.prev_quarter_mau) * 100
            ELSE NULL 
        END AS mau_qoq_growth,
        
        CASE 
            WHEN m.year_ago_mau > 0 
            THEN ((m.monthly_active_users - m.year_ago_mau) / m.year_ago_mau) * 100
            ELSE NULL 
        END AS mau_yoy_growth,
        
        -- Calculated metrics
        CASE 
            WHEN m.ltv > 0 AND m.cac > 0 
            THEN m.ltv / m.cac 
            ELSE NULL 
        END AS ltv_cac_ratio,
        
        CASE 
            WHEN m.monthly_active_users > 0 AND m.revenue > 0 
            THEN m.revenue / m.monthly_active_users 
            ELSE m.arpu 
        END AS calculated_arpu,
        
        -- Moving averages
        m.revenue_4q_avg,
        m.nrr_4q_avg,
        
        -- Data quality
        m.avg_confidence_score,
        m.metrics_available,
        
        CURRENT_TIMESTAMP AS refreshed_at
        
    FROM with_growth_rates m
    INNER JOIN companies c ON m.company_id = c.company_id
)

SELECT * FROM final