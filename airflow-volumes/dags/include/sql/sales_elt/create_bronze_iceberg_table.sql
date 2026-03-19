
CREATE TABLE IF NOT EXISTS minio_warehouse.{{ params.schema }}.{{ params.table_name }} (
    transaction_id VARCHAR,
    transaction_date TIMESTAMP,
    client_name VARCHAR,
    customer_loyalty_member BOOLEAN,
    basket_items_count INTEGER,
    basket_items_product_name VARCHAR,
    basket_items_quantity INTEGER,
    basket_items_unit_price DOUBLE,
    basket_items_total_amount DOUBLE,
    total_amount DOUBLE,
    currency VARCHAR,
    payment_method VARCHAR,
    ingestion_date DATE
)
    WITH ( partitioning = ARRAY['ingestion_date'], 
        format = 'PARQUET', 
        location = 's3a://{{ params.warehouse_name }}/{{ params.schema }}/{{ params.table_name }}/' )