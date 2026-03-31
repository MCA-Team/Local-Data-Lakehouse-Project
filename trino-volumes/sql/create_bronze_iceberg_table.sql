
CREATE TABLE IF NOT EXISTS minio_warehouse.sales_schema.bronze_table (
    transaction_id VARCHAR COMMENT 'The unique identifier for each transaction.',
    transaction_date TIMESTAMP COMMENT 'The date and time when the transaction occurred.',
    client_name VARCHAR COMMENT 'The name of the client who made the transaction.',
    customer_loyalty_member BOOLEAN COMMENT 'The status of the client, loyal member or not.',
    basket_items_count INTEGER COMMENT 'Total number of distinct product name.',
    basket_items_product_name VARCHAR COMMENT 'The name of the product that was purchased in the transaction.',
    basket_items_quantity INTEGER COMMENT 'Total quantity of purchased product for the specific product name.',
    basket_items_unit_price DOUBLE COMMENT 'The unit price of the product that was purchased in the transaction.',
    basket_items_total_amount DOUBLE COMMENT 'The total amount of the purchased product_name (calculated as basket_items_quantity * basket_items_unit_price).',
    total_amount DOUBLE COMMENT 'The sum of basket_items_total_amount for all purchased basket_items_product_name.',
    currency VARCHAR COMMENT 'The currency in which the transaction was made (e.g., USD, EUR, etc.).',
    payment_method VARCHAR COMMENT 'The method of payment used for the transaction (e.g., credit card, cash, etc.).',
    ingestion_date DATE COMMENT 'The date when the transaction data was ingested into the bronze table.'
)
    COMMENT 'Bronze Iceberg table which retrieves raw ingested data.'
    WITH ( partitioning = ARRAY['ingestion_date'], 
           format = 'PARQUET');

-- ALTER TABLE minio_warehouse.sales_schema.bronze_table 
-- SET PROPERTIES (
--     -- Snapshots retrieval duration (7 days for example)
--     'vacuum_max_snapshot_age' = '7d'
-- );