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
    for file in os.listdir("/opt/airflow/local-data/"):
        if os.path.isfile(os.path.join("/opt/airflow/local-data/", file)) and file.endswith(".json"):
            logging.info(f"Uploading file /opt/airflow/local-data/{file} to MinIO bronze bucket...")
            s3_hook.load_file(
                filename=f"/opt/airflow/local-data/{file}",
                key=f"{partition_path}/json/{file}",
                bucket_name="bronze", 
                replace=True)
            logging.info(f"File bronze/{partition_path}/json/{file} successfully uploaded to MinIO bronze bucket.")


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

    with duckdb.connect(config = {
                                    "s3_access_key_id": '', #dotenv_values(credentials_file_path)["MINIO_ROOT_USER"],
                                    "s3_secret_access_key": '', #dotenv_values(credentials_file_path)["MINIO_ROOT_PASSWORD"],
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
            logging.info("Transformed data written to MinIO Silver bucket in Parquet format at : {s3_hook.getlist}")

    logging.info("Data transformation from bronze to silver completed.")


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
    file_read = duckdb_connection.read_json(f"s3://bronze/{fileToTransform_path}")
    file_read\
        .select(
                    duckdb.ColumnExpression("transaction_id").isnotnull().alias("transaction_id"),      # Ensures transaction_id is not null
                    duckdb.ColumnExpression("date").cast("TIMESTAMP").alias("transaction_date"),    # Casts date to TIMESTAMP
                    duckdb.ColumnExpression("customer.name").alias("client_name"),
                    duckdb.ColumnExpression("customer.loyalty_member").alias("client_is_loyalty_member"),
                    duckdb.SQLExpression("UNNEST(basket.items).product_name").alias("item_product_name"),
                    duckdb.SQLExpression("UNNEST(basket.items).quantity").alias("quantity"),
                    duckdb.SQLExpression("UNNEST(basket.items).unit_price").cast("DOUBLE").alias("item_unit_price"),       # Casts unit_price to DOUBLE
                    duckdb.SQLExpression("UNNEST(basket.items).total_amount").cast("DOUBLE").alias("total_amount"),     # Casts total_amount to DOUBLE
                    duckdb.ColumnExpression("currency"),
                    duckdb.ColumnExpression("payment_method")
                )\
        .write_parquet(
                        f"s3://silver/{partition_path}/{fileToTransform_path.split('/')[-1].replace('.json', '.parquet')}", 
                        compression="SNAPPY",
                        overwrite=True
                    )
    