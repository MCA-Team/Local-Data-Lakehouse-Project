from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from dotenv import dotenv_values
from pathlib import Path
from typing import Any
import duckdb, os, logging, functools, tomllib



########################################## CONSTANTS ##########################################

CONFIG_PATH = Path(__file__).parent / "utilities" / "dev-config.toml"




########################################## FUNCTIONS ##########################################

# Extract function to load raw JSON files from local directory to MinIO bronze bucket
def extract_raw_json_files_to_minio_bronze(toml_config:dict[str, Any], ds:str):
    """
    Extracts raw JSON files from local filesystem and uploads them to MinIO bronze bucket.
    Args:
        toml_config (dict[str, Any]): The TOML configuration dictionary.
        ds (str): The DAG run's execution date in 'YYYY-MM-DD' format. Automatically passed by Airflow.
    Returns:
        None
    """
    partition_path:str = get_partition_path_blueprint(ds)
    logging.info(f"Partition path is: {partition_path}")

    s3_hook = S3Hook(aws_conn_id=toml_config["STORAGE"]["airflow_aws_connection_id"])  # Connection pointing to MinIO container and have to be configured through Airflow UI > Admin > Connections
    files_in_bronze_partition_path = s3_hook.list_keys(bucket_name=toml_config["STORAGE"]["bronze_bucket_name"],
                                                       prefix=f"{partition_path}")
    # Data idempotency and consistency: Clear (if exist) files in the target partition path in MinIO bronze bucket
    if len(files_in_bronze_partition_path) > 0:
        s3_hook.delete_objects(bucket=toml_config["STORAGE"]["bronze_bucket_name"], 
                               keys=files_in_bronze_partition_path)
        logging.info(f"Deleted existing files in MinIO bronze bucket at prefix: {partition_path}")

    # Now, Scanning all JSON files, following the config["TASKS"]["checking_raw_json_files_existence_file_pattern"]'s patter 
    # in the local source directory and loading them in the MinIO bronze bucket
    for file in os.listdir(toml_config["STORAGE"]["source_dir"]):
        if os.path.isfile(os.path.join(toml_config["STORAGE"]["source_dir"], file)) and file.endswith(".json"):
            logging.info(f"Uploading file {toml_config["STORAGE"]["source_dir"]}/{file} to MinIO bronze bucket...")
            s3_hook.load_file(
                                filename=f"{toml_config["STORAGE"]["source_dir"]}/{file}",  # Source file to load path
                                key=f"{partition_path}/{file}",                             # Destination file path
                                bucket_name=toml_config["STORAGE"]["bronze_bucket_name"],   
                                replace=True
                            )
            logging.info(f"File {toml_config["STORAGE"]["bronze_bucket_name"]}/{partition_path}/{file} successfully uploaded to MinIO bronze bucket.")



# ===============================================================================================================================================




# Transform function to process data from bronze to silver zone
def transform_bronze_data_to_silver(toml_config:dict[str, Any], ds:str):
    """
    Transforms data from MinIO bronze bucket to silver bucket.
    This is a placeholder function and should be implemented with actual transformation logic.
    Args:
        toml_config (dict[str, Any]): The TOML configuration dictionary.
        ds (str): The DAG run's execution date in 'YYYY-MM-DD' format. Automatically passed by Airflow.
    Returns:
        None
    """
    partition_path:str = get_partition_path_blueprint(ds)

    logging.info("Transforming data from Bronze to Silver...")

    # Initialize S3Hook to interact with MinIO Bronze bucket and list targeted files to transform
    s3_hook = S3Hook(aws_conn_id=toml_config["STORAGE"]["airflow_aws_connection_id"])  # Connection pointing to MinIO container and have to be configured through Airflow UI > Admin > Connections
    files_to_transform_list = s3_hook.list_keys(bucket_name=toml_config["STORAGE"]["bronze_bucket_name"], prefix=f"{partition_path}")
    logging.info(f"Bronze files to be transformed: {files_to_transform_list}")

    # Data idempotency and consistency: Clear existing files in the target partition    path in MinIO Silver bucket
    files_in_silver_partition_path = s3_hook.list_keys(bucket_name=toml_config["STORAGE"]["silver_bucket_name"], 
                                                       prefix=f"{partition_path}")
    if len(files_in_silver_partition_path) > 0:
        s3_hook.delete_objects(bucket=toml_config["STORAGE"]["silver_bucket_name"], 
                                keys=files_in_silver_partition_path)
        logging.info(f"Deleted existing files in MinIO silver Bucket at prefix: {partition_path}/")

    # Opening an in-memory connection to DuckDB while setting up s3 config parameters 
    with duckdb.connect(config = {
                                    "s3_access_key_id": dotenv_values("dags/utilities/.env")["MINIO_ROOT_USER"],
                                    "s3_secret_access_key": dotenv_values("dags/utilities/.env")["MINIO_ROOT_PASSWORD"],
                                    "s3_endpoint": f"{toml_config["STORAGE"]["minio_docker_service_name"]}:{toml_config["STORAGE"]["minio_s3_api_port"]}",     # MinIO service name as defined in docker-compose file followed by ":{MiniIO_API_Port}" (e.g., "minio:9000"). Do not use "http://" or "https://", and do not use the MinIO Console port.
                                    "s3_url_style": toml_config["STORAGE"]["duckdb_s3_url_style_config_param"],     # Use "path" URLs style for MinIO and "vhost" for AWS S3
                                    "s3_use_ssl": toml_config["STORAGE"]["duckdb_s3_use_ssl_config_param"]       # MinIO by default does not use SSL; set to "true" if SSL is configured
                                }
    ) as conn:
        # Ensure httpfs extension is installed and loaded for interactions between MinIO s3 API and DuckDB
        if conn.sql("SELECT installed FROM duckdb_extensions() where extension_name='httpfs' AND installed='true'").shape[0] == 0:
            conn.execute("INSTALL httpfs;")
        if conn.sql("SELECT loaded FROM duckdb_extensions() where extension_name='httpfs' AND loaded='true'").shape[0] == 0:
            conn.execute("LOAD httpfs;")

        # Transformation logic goes here
        for bronze_file_path in files_to_transform_list:
            apply_transformations_and_write_parquet(toml_config=toml_config,
                                                    duckdb_connection=conn,
                                                    fileToTransform_path=bronze_file_path, 
                                                    partition_path=partition_path)
            
    logging.info("Data transformation from Bronze to Silver completed.")



# ===============================================================================================================================================



def apply_transformations_and_write_parquet(toml_config:dict[str, Any], 
                                            duckdb_connection: duckdb.DuckDBPyConnection, 
                                            fileToTransform_path: str, 
                                            partition_path: str) -> None:
    """
    Applies necessary transformations to the sales data and writes it to MinIO silver bucket in Parquet format.
    Args:
        toml_config (dict[str, Any]): The TOML configuration dictionary.
        duckdb_connection (duckdb.DuckDBPyConnection): The DuckDB connection object.
        fileToTransform_path (str): The path of the file to transform within the bronze bucket.
        partition_path (str): The Silver final file partition path based on the Airflow execution date.
    Returns:
        None
    """

    fileToTransform = duckdb_connection.read_json(f"s3://{toml_config['STORAGE']['bronze_bucket_name']}/{fileToTransform_path}")

    # Transformations: type casting, columns flatening, filtering
    final_file = fileToTransform\
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

    # Ensuring all transformations went well and the final data is as identical as the excepted result
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

    # Writting of the final data into Silver bucket
    final_file.write_parquet(
                                f"s3://{toml_config['STORAGE']['silver_bucket_name']}/{partition_path}/{fileToTransform_path.split('/')[-1].replace('.json', '.parquet')}", 
                                compression=toml_config['STORAGE']['silver_parquet_files_compression_mode'],
                                overwrite=True
                            )
    logging.info(f"Transformed data written to MinIO Silver bucket in Parquet format at : s3://{toml_config['STORAGE']['silver_bucket_name']}/{partition_path}/{fileToTransform_path.split('/')[-1].replace('.json', '.parquet')}")



# ===============================================================================================================================================



def data_from_silver_to_gold(toml_config:dict[str, Any], ds:str) -> None:
    partition_path:str = get_partition_path_blueprint(ds)

    logging.info("Transforming data from Silver to Gold...")

    # Initialize S3Hook to interact with MinIO Silver bucket and list targeted files to transform
    s3_hook = S3Hook(aws_conn_id=toml_config["STORAGE"]["airflow_aws_connection_id"])  # Connection pointing to MinIO container and have to be configured through Airflow UI > Admin > Connections
    files_to_transform_list = s3_hook.list_keys(bucket_name=toml_config["STORAGE"]["silver_bucket_name"], prefix=f"{partition_path}")
    logging.info(f"Silver files to be transformed: {files_to_transform_list}")

    # Data idempotency and consistency: Clear existing files in the target partition    path in MinIO Gold bucket
    files_in_silver_partition_path = s3_hook.list_keys(bucket_name=toml_config["STORAGE"]["gold_bucket_name"], 
                                                       prefix=f"{partition_path}")
    if len(files_in_silver_partition_path) > 0:
        s3_hook.delete_objects(bucket=toml_config["STORAGE"]["gold_bucket_name"], 
                                keys=files_in_silver_partition_path)
        logging.info(f"Deleted existing files in MinIO Gold Bucket at prefix: {partition_path}/")

    # Opening an in-memory connection to DuckDB while setting up s3 config parameters 
    with duckdb.connect(config = {
                                    "s3_access_key_id": dotenv_values("dags/utilities/.env")["MINIO_ROOT_USER"],
                                    "s3_secret_access_key": dotenv_values("dags/utilities/.env")["MINIO_ROOT_PASSWORD"],
                                    "s3_endpoint": f"{toml_config["STORAGE"]["minio_docker_service_name"]}:{toml_config["STORAGE"]["minio_s3_api_port"]}",     # MinIO service name as defined in docker-compose file followed by ":{MiniIO_API_Port}" (e.g., "minio:9000"). Do not use "http://" or "https://", and do not use the MinIO Console port.
                                    "s3_url_style": toml_config["STORAGE"]["duckdb_s3_url_style_config_param"],     # Use "path" URLs style for MinIO and "vhost" for AWS S3
                                    "s3_use_ssl": toml_config["STORAGE"]["duckdb_s3_use_ssl_config_param"]       # MinIO by default does not use SSL; set to "true" if SSL is configured
                                }
    ) as conn:
        # Ensure httpfs extension is installed and loaded for interactions between MinIO s3 API and DuckDB
        if conn.sql("SELECT installed FROM duckdb_extensions() where extension_name='httpfs' AND installed='true'").shape[0] == 0:
            conn.execute("INSTALL httpfs;")
        if conn.sql("SELECT loaded FROM duckdb_extensions() where extension_name='httpfs' AND loaded='true'").shape[0] == 0:
            conn.execute("LOAD httpfs;")

        # Transformation logic goes here



# ===============================================================================================================================================



@functools.cache
def load_config(toml_file_path: str = CONFIG_PATH) -> dict[str, Any]:
    """
    Loads the configuration from a TOML file.
    Args:
        toml_file_path (str): Path to the TOML configuration file.
    Returns:
        dict: The loaded configuration dictionary.
    """
    logging.info(f"Print: {CONFIG_PATH}")
    with open(toml_file_path, "rb") as config_file:
        return tomllib.load(config_file)
    


# ===============================================================================================================================================



def get_partition_path_blueprint(execution_date:str) ->str:
    """
    Loads the configuration from a TOML file.
    Args:
        execution_date (str): The DAG run's execution date in 'YYYY-MM-DD' format. Automatically passed by Airflow.
    Returns:
        str: A string following this format: "year=YYYY/month=MM/day=DD" (based on values of the execution_date parameter)
    """
    partition_path:list[str] = execution_date.split("-")
    partition_path[0] = ''.join(("year=", partition_path[0]))
    partition_path[1] = ''.join(("month=", partition_path[1]))
    partition_path[2] = ''.join(("day=", partition_path[2]))

    return '/'.join(partition_path)


def create_FileSensor_connection_informations() -> None:

    pass