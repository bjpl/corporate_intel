

-- Simplified mart for competitive intelligence
-- Focus: Latest company metrics for comparison

WITH company_metrics AS (
    SELECT * FROM "corporate_intel"."public_intermediate"."int_company_metrics_quarterly"
),

company_rankings AS (
    SELECT
        *,

        -- Rankings within category
        RANK() OVER (PARTITION BY edtech_category ORDER BY latest_revenue DESC NULLS LAST) AS revenue_rank_in_category,
        RANK() OVER (PARTITION BY edtech_category ORDER BY revenue_yoy_growth DESC NULLS LAST) AS growth_rank_in_category,

        -- Overall rankings
        RANK() OVER (ORDER BY latest_revenue DESC NULLS LAST) AS revenue_rank_overall,
        RANK() OVER (ORDER BY revenue_yoy_growth DESC NULLS LAST) AS growth_rank_overall,

        -- Performance scores (0-100)
        CASE
            WHEN revenue_yoy_growth >= 50 THEN 100
            WHEN revenue_yoy_growth >= 30 THEN 80
            WHEN revenue_yoy_growth >= 15 THEN 60
            WHEN revenue_yoy_growth >= 0 THEN 40
            ELSE 20
        END AS growth_score,

        CASE
            WHEN latest_gross_margin >= 80 THEN 100
            WHEN latest_gross_margin >= 70 THEN 80
            WHEN latest_gross_margin >= 60 THEN 60
            WHEN latest_gross_margin >= 50 THEN 40
            ELSE 20
        END AS margin_score,

        CASE
            WHEN latest_operating_margin >= 20 THEN 100
            WHEN latest_operating_margin >= 10 THEN 80
            WHEN latest_operating_margin >= 0 THEN 60
            WHEN latest_operating_margin >= -10 THEN 40
            ELSE 20
        END AS profitability_score

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
        latest_gross_margin,
        latest_operating_margin,
        latest_profit_margin,

        -- Growth metrics
        revenue_yoy_growth,
        earnings_growth,

        -- Valuation
        pe_ratio,
        forward_pe,
        market_cap,
        eps,
        roe,

        -- Rankings
        revenue_rank_in_category,
        growth_rank_in_category,
        revenue_rank_overall,
        growth_rank_overall,

        -- Performance scores
        growth_score,
        margin_score,
        profitability_score,
        (growth_score + margin_score + profitability_score) / 3.0 AS overall_score,

        -- Health indicators
        CASE
            WHEN revenue_yoy_growth >= 20 AND latest_operating_margin >= 10 AND latest_gross_margin >= 60
            THEN 'Excellent'
            WHEN revenue_yoy_growth >= 0 AND latest_operating_margin >= 0 AND latest_gross_margin >= 50
            THEN 'Good'
            WHEN revenue_yoy_growth < 0 OR latest_operating_margin < -10
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