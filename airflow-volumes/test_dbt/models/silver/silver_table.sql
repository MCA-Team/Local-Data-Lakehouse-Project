{{ config(
    materialized='table',
    properties={
      "format": "'PARQUET'",
      "partitioning": "['ingestion_date']"
    }
) }}


WITH source AS (
    SELECT
        *
    FROM {{ source('bronze_source', 'bronze_table')}}
), final_data AS (
    SELECT 
         transaction_id,
         transaction_date,
         client_name,
         basket_items_product_name AS item_product_name,
         basket_items_quantity AS item_quantity,
         basket_items_unit_price AS item_unit_price,
         basket_items_total_amount AS total_amount,
         currency AS transaction_currency,
         payment_method,
         ingestion_date
    FROM source
    WHERE transaction_id IS NOT NULL
)

SELECT * FROM final_data