{{ config(
    materialized='table',
    indexes=[
        {'columns': ['edtech_category', 'analysis_quarter'], 'unique': False}
    ],
    tags=['marts', 'intelligence', 'competitive']
) }}

WITH company_performance AS (
    SELECT * FROM {{ ref('mart_company_performance') }}
),

quarterly_metrics AS (
    SELECT * FROM {{ ref('int_company_metrics_quarterly') }}
),

latest_quarter AS (
    SELECT MAX(metric_quarter) AS analysis_quarter
    FROM quarterly_metrics
),

segment_analysis AS (
    SELECT
        edtech_category,
        lq.analysis_quarter,
        
        -- Market size metrics
        COUNT(DISTINCT company_id) AS companies_in_segment,
        SUM(latest_revenue) AS total_segment_revenue,
        SUM(latest_mau) AS total_segment_users,
        
        -- Growth metrics
        AVG(revenue_yoy_growth) AS avg_revenue_growth,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY revenue_yoy_growth) AS median_revenue_growth,
        MAX(revenue_yoy_growth) AS max_revenue_growth,
        MIN(revenue_yoy_growth) AS min_revenue_growth,
        
        -- Retention metrics
        AVG(latest_nrr) AS avg_nrr,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY latest_nrr) AS median_nrr,
        
        -- Efficiency metrics
        AVG(latest_ltv_cac_ratio) AS avg_ltv_cac_ratio,
        AVG(latest_gross_margin) AS avg_gross_margin,
        
        -- Market concentration (HHI - Herfindahl-Hirschman Index)
        SUM(POWER(latest_revenue / NULLIF(SUM(latest_revenue) OVER (PARTITION BY edtech_category), 0) * 100, 2)) AS hhi_index
        
    FROM company_performance
    CROSS JOIN latest_quarter lq
    GROUP BY edtech_category, lq.analysis_quarter
),

company_positions AS (
    SELECT
        cp.*,
        lq.analysis_quarter,
        
        -- Market share calculation
        cp.latest_revenue / NULLIF(sa.total_segment_revenue, 0) * 100 AS market_share_pct,
        
        -- Relative performance
        cp.revenue_yoy_growth - sa.avg_revenue_growth AS growth_vs_segment_avg,
        cp.latest_nrr - sa.avg_nrr AS nrr_vs_segment_avg,
        
        -- Competitive position
        CASE
            WHEN cp.revenue_rank_in_category <= 3 THEN 'Leader'
            WHEN cp.revenue_rank_in_category <= 6 THEN 'Challenger'
            WHEN cp.growth_rank_in_category <= 3 THEN 'Disruptor'
            ELSE 'Niche Player'
        END AS competitive_position,
        
        -- Strategic group (based on delivery model and size)
        CASE
            WHEN cp.delivery_model = 'b2b' AND cp.latest_revenue > 100000000 THEN 'Enterprise B2B'
            WHEN cp.delivery_model = 'b2b' THEN 'SMB B2B'
            WHEN cp.delivery_model = 'b2c' AND cp.latest_mau > 1000000 THEN 'Mass Market B2C'
            WHEN cp.delivery_model = 'b2c' THEN 'Niche B2C'
            WHEN cp.delivery_model = 'marketplace' THEN 'Platform'
            ELSE 'Hybrid'
        END AS strategic_group
        
    FROM company_performance cp
    CROSS JOIN latest_quarter lq
    LEFT JOIN segment_analysis sa 
        ON cp.edtech_category = sa.edtech_category 
        AND sa.analysis_quarter = lq.analysis_quarter
),

competitive_dynamics AS (
    SELECT
        edtech_category,
        analysis_quarter,
        
        -- Leader analysis
        STRING_AGG(
            CASE WHEN competitive_position = 'Leader' THEN ticker ELSE NULL END, 
            ', ' ORDER BY revenue_rank_in_category
        ) AS segment_leaders,
        
        -- Fast growers
        STRING_AGG(
            CASE WHEN growth_rank_in_category <= 3 THEN ticker || ' (' || ROUND(revenue_yoy_growth, 1) || '%)' ELSE NULL END,
            ', ' ORDER BY growth_rank_in_category
        ) AS fastest_growers,
        
        -- At risk companies
        STRING_AGG(
            CASE WHEN company_health_status = 'At Risk' THEN ticker ELSE NULL END,
            ', '
        ) AS at_risk_companies,
        
        -- Competitive intensity metrics
        COUNT(DISTINCT CASE WHEN competitive_position = 'Disruptor' THEN company_id END) AS disruptor_count,
        
        MAX(market_share_pct) AS leader_market_share,
        SUM(CASE WHEN revenue_rank_in_category <= 3 THEN market_share_pct ELSE 0 END) AS top3_concentration
        
    FROM company_positions
    GROUP BY edtech_category, analysis_quarter
),

segment_opportunities AS (
    SELECT
        sa.edtech_category,
        sa.analysis_quarter,
        
        -- TAM expansion indicators
        CASE
            WHEN sa.avg_revenue_growth > 30 THEN 'Rapid Expansion'
            WHEN sa.avg_revenue_growth > 15 THEN 'Growing'
            WHEN sa.avg_revenue_growth > 0 THEN 'Mature'
            ELSE 'Declining'
        END AS market_stage,
        
        -- Entry barriers
        CASE
            WHEN sa.hhi_index > 2500 THEN 'High Concentration'
            WHEN sa.hhi_index > 1500 THEN 'Moderate Concentration'
            ELSE 'Fragmented'
        END AS market_concentration,
        
        -- Opportunity scores
        CASE
            WHEN sa.avg_revenue_growth > 20 AND sa.hhi_index < 1500 THEN 'High Opportunity'
            WHEN sa.avg_revenue_growth > 10 OR sa.hhi_index < 1500 THEN 'Medium Opportunity'
            ELSE 'Low Opportunity'
        END AS opportunity_level,
        
        -- Investment thesis
        CASE
            WHEN sa.avg_ltv_cac_ratio > 3 AND sa.avg_nrr > 110 THEN 'Strong Unit Economics'
            WHEN sa.avg_ltv_cac_ratio > 2 AND sa.avg_nrr > 100 THEN 'Solid Fundamentals'
            WHEN sa.avg_ltv_cac_ratio > 1.5 OR sa.avg_nrr > 100 THEN 'Mixed Signals'
            ELSE 'Challenging Economics'
        END AS segment_economics
        
    FROM segment_analysis sa
),

final AS (
    SELECT
        sa.edtech_category,
        sa.analysis_quarter,
        
        -- Market metrics
        sa.companies_in_segment,
        sa.total_segment_revenue,
        sa.total_segment_users,
        
        -- Growth metrics
        sa.avg_revenue_growth,
        sa.median_revenue_growth,
        sa.max_revenue_growth,
        sa.min_revenue_growth,
        
        -- Retention & efficiency
        sa.avg_nrr,
        sa.median_nrr,
        sa.avg_ltv_cac_ratio,
        sa.avg_gross_margin,
        
        -- Market structure
        sa.hhi_index,
        so.market_concentration,
        so.market_stage,
        
        -- Competitive landscape
        cd.segment_leaders,
        cd.fastest_growers,
        cd.at_risk_companies,
        cd.disruptor_count,
        cd.leader_market_share,
        cd.top3_concentration,
        
        -- Strategic insights
        so.opportunity_level,
        so.segment_economics,
        
        -- Recommendations
        CASE
            WHEN so.opportunity_level = 'High Opportunity' AND so.segment_economics IN ('Strong Unit Economics', 'Solid Fundamentals')
            THEN 'Priority Investment Target'
            WHEN so.opportunity_level = 'High Opportunity'
            THEN 'Growth Opportunity'
            WHEN so.segment_economics = 'Strong Unit Economics'
            THEN 'Value Opportunity'
            WHEN cd.disruptor_count > 2
            THEN 'Monitor Disruption'
            ELSE 'Selective Approach'
        END AS strategic_recommendation,
        
        CURRENT_TIMESTAMP AS refreshed_at
        
    FROM segment_analysis sa
    LEFT JOIN competitive_dynamics cd 
        ON sa.edtech_category = cd.edtech_category 
        AND sa.analysis_quarter = cd.analysis_quarter
    LEFT JOIN segment_opportunities so 
        ON sa.edtech_category = so.edtech_category 
        AND sa.analysis_quarter = so.analysis_quarter
)

SELECT * FROM final
ORDER BY edtech_category