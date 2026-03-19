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
    FROM {{ ref('silver_table') }}
), tableToTransform AS (
    SELECT 
         transaction_id,
         CAST(transaction_date AS DATE) AS transaction_date,
         item_product_name,
         total_amount,
         ingestion_date
    FROM source
), 

total_revenue AS (
    SELECT 
         transaction_date, 
         ingestion_date,
         SUM(total_amount) AS total_revenue
    FROM tableToTransform
    GROUP BY
         transaction_date,
         ingestion_date
),

order_count AS (
    SELECT
         transaction_date, 
         ingestion_date,
         COUNT(DISTINCT transaction_id) AS order_count
    FROM tableToTransform
    GROUP BY
         transaction_date,
         ingestion_date
),

total_revenue_per_category_per_day AS (
    SELECT
         transaction_date,
         ingestion_date,
         item_product_name AS top_category_product_name,
         SUM(total_amount) AS categories_daily_total_revenue
    FROM tableToTransform
    GROUP BY
         transaction_date,
         item_product_name,
         ingestion_date
),

top_category_total_revenue_per_day AS  (
    SELECT 
         transaction_date,
         ingestion_date,
         MAX(categories_daily_total_revenue) AS top_category_total_revenue
    FROM total_revenue_per_category_per_day      
    GROUP BY
         transaction_date,
         ingestion_date

),

top_category AS (
    SELECT
         t1.transaction_date,
         t2.top_category_product_name,
         t1.top_category_total_revenue,
         t1.ingestion_date
    FROM top_category_total_revenue_per_day AS t1
    INNER JOIN total_revenue_per_category_per_day AS t2
    ON t1.top_category_total_revenue = t2.categories_daily_total_revenue
        AND t1.transaction_date = t2.transaction_date
        AND t1.ingestion_date = t2.ingestion_date
)

SELECT
     tr.transaction_date AS sales_day, 
     tr.total_revenue, 
     oc.order_count,
     tr.total_revenue/oc.order_count AS avg_order_value,
     tc.top_category_product_name,
     tc.top_category_total_revenue,
     tr.ingestion_date
FROM total_revenue AS tr
INNER JOIN order_count AS oc
ON oc.transaction_date = tr.transaction_date
    AND oc.ingestion_date = tr.ingestion_date
INNER JOIN top_category AS tc
ON tc.transaction_date = tr.transaction_date
    AND tc.ingestion_date = tr.ingestion_date