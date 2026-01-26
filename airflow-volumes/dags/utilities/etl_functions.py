from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from dotenv import dotenv_values
import duckdb
import os
import logging

# Extract function to load raw JSON files from local directory to MinIO bronze bucket
def extract_raw_json_files_to_minio_bronze(ds:str):
    """
    Extracts raw JSON files from local filesystem and uploads them to MinIO bronze bucket.
    Args:
        ds (str): The DAG run's execution date in 'YYYY-MM-DD' format. Automatically passed by Airflow.
    Returns:
        None
    """
    partition_path:str = ds.replace("-", "/")
    logging.info(f"Partition path is: {partition_path}")

    s3_hook = S3Hook(aws_conn_id="minio_conn")  # Connection pointing to MinIO container and have to be configured through Airflow UI > Admin > Connections

    # Data idempotency and consistency: Clear existing files in the target partition    path in MinIO bronze bucket
    if s3_hook.list_keys(bucket_name='bronze', prefix=f"{partition_path}") is not None:
        s3_hook.delete_objects(bucket='bronze', keys=s3_hook.list_keys(bucket_name='bronze', prefix=f"{partition_path}"))
        logging.info(f"Deleted existing files in MinIO bronze bucket at prefix: {partition_path}")

    for file in os.listdir("/opt/airflow/local-data/"):
        if os.path.isfile(os.path.join("/opt/airflow/local-data/", file)) and file.endswith(".json"):
            logging.info(f"Uploading file /opt/airflow/local-data/{file} to MinIO bronze bucket...")
            s3_hook.load_file(
                filename=f"/opt/airflow/local-data/{file}",
                key=f"{partition_path}/{file}",
                bucket_name="bronze", 
                replace=True)
            logging.info(f"File bronze/{partition_path}/{file} successfully uploaded to MinIO bronze bucket.")




# ===============================================================================================================================================




# Transform function to process data from bronze to silver zone
def transform_bronze_data_to_silver(ds:str):
    """
    Transforms data from MinIO bronze bucket to silver bucket.
    This is a placeholder function and should be implemented with actual transformation logic.
    Args:
        credentials_file_path (dict): Path to the credentials file. Default is "../../.env" file.
    Returns:
        None
    """
    partition_path:str = ds.replace("-", "/")

    logging.info("Transforming data from Bronze to Silver...")

    # Initialize S3Hook to interact with MinIO Bronze bucket and list targeted files
    s3_hook = S3Hook(aws_conn_id="minio_conn")  # Connection pointing to MinIO container and have to be configured through Airflow UI > Admin > Connections
    files_list = s3_hook.list_keys(bucket_name='bronze', prefix=f"{partition_path}")
    logging.info(f"Bronze files to be transformed: {files_list}")

    # Data idempotency and consistency: Clear existing files in the target partition    path in MinIO bronze bucket
    if s3_hook.list_keys(bucket_name='silver', prefix=f"{partition_path}") is not None:
        s3_hook.delete_objects(bucket='silver', keys=s3_hook.list_keys(bucket_name='silver', prefix=f"{partition_path}"))
        logging.info(f"Deleted existing files in MinIO silver bucket at prefix: {partition_path}/")

    with duckdb.connect(config = {
                                    "s3_access_key_id": 'airflow', #dotenv_values(credentials_file_path)["MINIO_ROOT_USER"],
                                    "s3_secret_access_key": 'miniopasswd', #dotenv_values(credentials_file_path)["MINIO_ROOT_PASSWORD"],
                                    "s3_endpoint": "minio-aistor:9008",     # MinIO service name as defined in docker-compose file followed by ":{MiniIO_API_Port}" (e.g., "minio:9000"). Do not use "http://" or "https://", and do not use the MinIO Console port.
                                    "s3_url_style": "path",     # Use "path" URLs style for MinIO and "vhost" for AWS S3
                                    "s3_use_ssl": "false"       # MinIO by default does not use SSL; set to "true" if SSL is configured
                                }
    ) as conn:
        # Ensure httpfs extension is installed and loaded for S3 interactions
        if conn.sql("SELECT installed FROM duckdb_extensions() where extension_name='httpfs' AND installed='true'").shape[0] == 0:
            conn.execute("INSTALL httpfs;")
        if conn.sql("SELECT loaded FROM duckdb_extensions() where extension_name='httpfs' AND loaded='true'").shape[0] == 0:
            conn.execute("LOAD httpfs;")

        for bronze_file_path in files_list:
            # Transformation logic goes here
            apply_transformations_and_write_parquet(duckdb_connection=conn,
                                                    fileToTransform_path=bronze_file_path, 
                                                    partition_path=partition_path
                                                    )

    logging.info("Data transformation from bronze to silver completed.")




# ===============================================================================================================================================



def apply_transformations_and_write_parquet(duckdb_connection: duckdb.DuckDBPyConnection, fileToTransform_path: str, partition_path: str) -> None:
    """
    Applies necessary transformations to the sales data and writes it to MinIO silver bucket in Parquet format.
    Args:
        duckdb_connection (duckdb.DuckDBPyConnection): The DuckDB connection object.
        fileToTransform_path (str): The path of the file to transform within the bronze bucket.
        partition_path (str): The Silver final file partition path based on the Airflow execution date.
    Returns:
        None
    """

    source_file = duckdb_connection.read_json(f"s3://bronze/{fileToTransform_path}")
    final_file = source_file\
                            .select(
                                        duckdb.ColumnExpression("transaction_id").cast("VARCHAR").alias("transaction_id"),                      # Casts transaction_id to VARCHAR
                                        duckdb.ColumnExpression("date").cast("TIMESTAMP").alias("transaction_date"),                            # Casts transaction_date to TIMESTAMP
                                        duckdb.ColumnExpression("customer.name").cast("VARCHAR").alias("client_name"),                          # Casts client_name to VARCHAR
                                        duckdb.SQLExpression("UNNEST(basket.items).product_name").cast("VARCHAR").alias("item_product_name"),   # Casts item_product_name to VARCHAR
                                        duckdb.SQLExpression("UNNEST(basket.items).quantity").cast("UINTEGER").alias("item_quantity"),          # Casts item_quantity to UINTEGER (Unsigned Integer)  
                                        duckdb.SQLExpression("UNNEST(basket.items).unit_price").cast("DOUBLE").alias("item_unit_price"),        # Casts item_unit_price to DOUBLE
                                        duckdb.SQLExpression("UNNEST(basket.items).total_amount").cast("DOUBLE").alias("total_amount"),         # Casts total_amount to DOUBLE
                                        duckdb.ColumnExpression("currency").cast("VARCHAR").alias("transaction_currency"),                      # Casts transaction_currency to VARCHAR
                                        duckdb.ColumnExpression("payment_method").cast("VARCHAR").alias("payment_method")                       # Casts payment_method to VARCHAR
                                    )\
                            .filter(duckdb.ColumnExpression("transaction_id").isnotnull())  # Ensures transaction_id is not null

    logging.info("Data verification before writting in Silver bucket...")

    type_validator ={column_name:type_name for column_name, type_name in zip(final_file.columns, final_file.types)}

    assert final_file.filter(duckdb.ColumnExpression("transaction_id").isnull()).shape[0] == 0, "Transformed data contains null values for 'transaction_id' column."
    assert  type_validator["transaction_id"] == "VARCHAR", "Data type mismatch for 'transaction_id' column."
    assert  type_validator["transaction_date"] == "TIMESTAMP", "Data type mismatch for 'transaction_date' column."
    assert  type_validator["client_name"] == "VARCHAR", "Data type mismatch for 'client_name' column."
    assert  type_validator["item_product_name"] == "VARCHAR", "Data type mismatch for 'item_product_name' column."
    assert  type_validator["item_quantity"] == "UINTEGER", "Data type mismatch for 'item_quantity' column."
    assert  type_validator["item_unit_price"] == "DOUBLE", "Data type mismatch for 'item_unit_price' column."
    assert  type_validator["total_amount"] == "DOUBLE", "Data type mismatch for 'total_amount' column."
    assert  type_validator["transaction_currency"] == "VARCHAR", "Data type mismatch for 'transaction_currency' column."
    assert  type_validator["payment_method"] == "VARCHAR", "Data type mismatch for 'payment_method' column."
    
    logging.info("Data verification completed successfully. Writing transformed data to MinIO Silver bucket...")

    final_file.write_parquet(
                                f"s3://silver/{partition_path}/{fileToTransform_path.split('/')[-1].replace('.json', '.parquet')}", 
                                compression="SNAPPY",
                                overwrite=True
                            )
    logging.info(f"Transformed data written to MinIO Silver bucket in Parquet format at : s3://silver/{partition_path}/{fileToTransform_path.split('/')[-1].replace('.json', '.parquet')}")
    