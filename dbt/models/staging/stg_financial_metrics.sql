{{ config(
    materialized='view',
    tags=['staging', 'metrics', 'timescaledb']
) }}

WITH source AS (
    SELECT * FROM {{ source('raw', 'financial_metrics') }}
),

validated AS (
    SELECT
        -- IDs
        id AS metric_id,
        company_id,
        
        -- Time dimensions
        metric_date,
        DATE_TRUNC('quarter', metric_date) AS metric_quarter,
        DATE_TRUNC('year', metric_date) AS metric_year,
        period_type,
        
        -- Metric details
        metric_type,
        metric_category,
        value AS metric_value,
        unit AS metric_unit,
        
        -- Data quality
        source AS data_source,
        source_document_id,
        confidence_score,
        
        -- Timestamps
        created_at,
        updated_at,
        
        -- Validation flags
        CASE 
            WHEN confidence_score >= {{ var('min_confidence_score') }} THEN 1 
            ELSE 0 
        END AS is_high_confidence,
        
        CASE
            WHEN metric_type = 'net_revenue_retention' 
                AND value BETWEEN 50 AND 200 THEN 1
            WHEN metric_type = 'churn_rate' 
                AND value BETWEEN 0 AND 50 THEN 1
            WHEN metric_type = 'gross_margin' 
                AND value BETWEEN 0 AND 100 THEN 1
            WHEN metric_type IN ('revenue', 'monthly_active_users')
                AND value > 0 THEN 1
            ELSE 0
        END AS is_valid_range
        
    FROM source
    WHERE
        -- Remove obviously bad data
        value IS NOT NULL
        AND value >= 0
        AND metric_date <= CURRENT_DATE
        AND metric_date >= '2015-01-01'
)

SELECT * FROM validated