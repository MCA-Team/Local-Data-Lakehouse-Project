from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from dotenv import dotenv_values, load_dotenv
import duckdb
import os
import logging

# Extract function to load raw JSON files from local directory to MinIO bronze bucket
def extract_raw_json_files_to_minio_bronze(ds: str):
    """
    Extracts raw JSON files from local filesystem and uploads them to MinIO bronze bucket.
    Args:
        ds (str): The DAG run's execution date in 'YYYY-MM-DD' format. Automatically passed by Airflow.
    Returns:
        None
    """
    partition_path = ds.split("-")
    logging.info(f"Partition path is: {partition_path}")
    s3_hook = S3Hook(aws_conn_id="minio_conn")  # Connection pointing to MinIO instance and have to be configured through Airflow UI > Admin > Connections
    for file in os.listdir("/opt/airflow/local-data/"):
        if os.path.isfile(os.path.join("/opt/airflow/local-data/", file)) and file.endswith(".json"):
            logging.info(f"Uploading file {file} to MinIO bronze bucket...")
            s3_hook.load_file(
                filename=f"/opt/airflow/local-data/{file}",
                key=f"{partition_path[0]}/{partition_path[1]}/{partition_path[2]}/json/{file}",
                bucket_name="bronze", 
                replace=True)
            logging.info(f"File {file} successfully uploaded to MinIO bronze bucket.")


# Transform function to process data from bronze to silver zone
def transform_bronze_data_to_silver():
    """
    Transforms data from MinIO bronze bucket to silver bucket.
    This is a placeholder function and should be implemented with actual transformation logic.
    Returns:
        None
    """
    logging.info("Transforming data from bronze to silver...")
    # dotenv_values("./.env")
    config = dotenv_values("./.env")
    print(config.keys())
    print(f"s3 key = {config["MINIO_ROOT_USER"]}")
    # Transformation logic goes here
    conn = duckdb.connect(config = {
                                    "s3_access_key_id": dotenv_values(".env")["MINIO_ROOT_USER"],
                                    "s3_secret_access_key": dotenv_values(".env")["MINIO_ROOT_PASSWORD"],
                                    "s3_endpoint": "minio-aistor:9008",
                                    "s3_url_style": "path",
                                    "s3_use_ssl": "false"
                                    }
                        )
    conn.execute("INSTALL httpfs; LOAD httpfs;")
    conn.sql("SELECT name, value, description \
            FROM duckdb_settings() \
            WHERE name LIKE 's3_%';").show()
    
    # conn = duckdb.connect()
    # sales = conn.read_json("s3://bronze/2026/01/21/json/sales_2024.json")
    conn.read_json("s3://bronze/2026/01/21/json/sales_2024.json").limit(5).show()
    # sales.select("customer.name", "currency").show()
    logging.info("Data transformation from bronze to silver completed.")
