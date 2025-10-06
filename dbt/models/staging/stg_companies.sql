{{ config(
    materialized='view',
    tags=['staging', 'edtech']
) }}

WITH source AS (
    SELECT * FROM {{ source('raw', 'companies') }}
),

cleaned AS (
    SELECT
        -- IDs
        id AS company_id,
        ticker,
        cik,
        
        -- Company info
        name AS company_name,
        sector,
        subsector,
        
        -- EdTech categorization
        category AS edtech_category,
        subcategory AS edtech_subcategories,
        delivery_model,
        monetization_strategy,
        
        -- Company metadata
        founded_year,
        headquarters,
        website,
        employee_count,
        
        -- Timestamps
        created_at,
        updated_at,
        
        -- Data quality
        CASE 
            WHEN ticker IS NOT NULL 
                AND name IS NOT NULL 
                AND category IS NOT NULL 
            THEN 1 
            ELSE 0 
        END AS is_complete_record
        
    FROM source
    WHERE
        -- Remove test data only (don't filter by category - accept all)
        LOWER(name) NOT LIKE '%test%'
        AND ticker IS NOT NULL
)

SELECT * FROM cleaned