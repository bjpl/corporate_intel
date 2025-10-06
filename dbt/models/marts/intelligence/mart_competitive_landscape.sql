{{ config(
    materialized='table',
    indexes=[
        {'columns': ['edtech_category'], 'unique': False}
    ],
    tags=['marts', 'intelligence', 'competitive']
) }}

-- Simplified mart for market segment analysis
-- Focus: Category-level competitive dynamics

WITH company_performance AS (
    SELECT * FROM {{ ref('mart_company_performance') }}
),

-- Add competitive_position field first
company_performance_enhanced AS (
    SELECT
        cp.*,
        -- Competitive position based on rankings
        CASE
            WHEN cp.revenue_rank_in_category <= 3 THEN 'Leader'
            WHEN cp.revenue_rank_in_category <= 6 THEN 'Challenger'
            WHEN cp.growth_rank_in_category <= 3 THEN 'Disruptor'
            ELSE 'Niche Player'
        END AS competitive_position
    FROM company_performance cp
),

segment_totals AS (
    SELECT
        edtech_category,
        SUM(latest_revenue) AS total_revenue
    FROM company_performance_enhanced
    GROUP BY edtech_category
),

segment_analysis AS (
    SELECT
        cp.edtech_category,

        -- Market size metrics
        COUNT(DISTINCT cp.company_id) AS companies_in_segment,
        SUM(cp.latest_revenue) AS total_segment_revenue,
        SUM(cp.latest_mau) AS total_segment_users,

        -- Growth metrics
        AVG(cp.revenue_yoy_growth) AS avg_revenue_growth,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY cp.revenue_yoy_growth) AS median_revenue_growth,
        MAX(cp.revenue_yoy_growth) AS max_revenue_growth,
        MIN(cp.revenue_yoy_growth) AS min_revenue_growth,

        -- Retention metrics
        AVG(cp.latest_nrr) AS avg_nrr,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY cp.latest_nrr) AS median_nrr,

        -- Efficiency metrics
        AVG(cp.latest_ltv_cac_ratio) AS avg_ltv_cac_ratio,
        AVG(cp.latest_gross_margin) AS avg_gross_margin,

        -- Market concentration (HHI - Herfindahl-Hirschman Index)
        SUM(POWER((cp.latest_revenue / NULLIF(st.total_revenue, 0)) * 100, 2)) AS hhi_index

    FROM company_performance_enhanced cp
    LEFT JOIN segment_totals st ON cp.edtech_category = st.edtech_category
    GROUP BY cp.edtech_category
),

competitive_dynamics AS (
    SELECT
        cp.edtech_category,

        -- Leader analysis
        STRING_AGG(
            CASE WHEN cp.competitive_position = 'Leader' THEN cp.ticker ELSE NULL END,
            ', ' ORDER BY cp.revenue_rank_in_category
        ) AS segment_leaders,

        -- Fast growers
        STRING_AGG(
            CASE WHEN cp.growth_rank_in_category <= 3
                 THEN cp.ticker || ' (' || ROUND(cp.revenue_yoy_growth::numeric, 1)::text || '%)'
                 ELSE NULL END,
            ', ' ORDER BY cp.growth_rank_in_category
        ) AS fastest_growers,

        -- At risk companies
        STRING_AGG(
            CASE WHEN cp.company_health_status = 'At Risk' THEN cp.ticker ELSE NULL END,
            ', '
        ) AS at_risk_companies,

        -- Competitive intensity metrics
        COUNT(DISTINCT CASE WHEN cp.competitive_position = 'Disruptor' THEN cp.company_id END) AS disruptor_count,

        MAX(cp.latest_revenue / NULLIF(st.total_revenue, 0) * 100) AS leader_market_share,
        SUM(CASE WHEN cp.revenue_rank_in_category <= 3
                 THEN (cp.latest_revenue / NULLIF(st.total_revenue, 0) * 100)
                 ELSE 0 END) AS top3_concentration

    FROM company_performance_enhanced cp
    LEFT JOIN segment_totals st ON cp.edtech_category = st.edtech_category
    GROUP BY cp.edtech_category
),

segment_opportunities AS (
    SELECT
        sa.edtech_category,

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
    LEFT JOIN competitive_dynamics cd ON sa.edtech_category = cd.edtech_category
    LEFT JOIN segment_opportunities so ON sa.edtech_category = so.edtech_category
)

SELECT * FROM final
ORDER BY edtech_category
