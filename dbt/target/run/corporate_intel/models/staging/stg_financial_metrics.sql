
  create view "corporate_intel"."public_staging"."stg_financial_metrics__dbt_tmp"
    
    
  as (
    

WITH source AS (
    SELECT * FROM "corporate_intel"."public"."financial_metrics"
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
            WHEN confidence_score >= 0.7 THEN 1 
            ELSE 0 
        END AS is_high_confidence,
        
        CASE
            -- Fail if obvious invalid ranges
            WHEN metric_type IN ('gross_margin', 'operating_margin', 'profit_margin')
                AND value NOT BETWEEN -100 AND 200 THEN 0
            WHEN metric_type IN ('pe_ratio', 'forward_pe', 'trailing_pe', 'peg_ratio')
                AND value NOT BETWEEN -100 AND 1000 THEN 0
            WHEN metric_type IN ('revenue', 'market_cap', 'eps')
                AND value < 0 THEN 0
            -- Otherwise assume valid
            ELSE 1
        END AS is_valid_range
        
    FROM source
    WHERE
        -- Remove obviously bad data
        value IS NOT NULL
        -- Allow negative values for growth metrics and margins
        AND metric_date <= CURRENT_DATE
        AND metric_date >= '2015-01-01'
)

SELECT * FROM validated
  );