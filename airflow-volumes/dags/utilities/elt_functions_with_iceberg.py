from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from airflow.models.connection import Connection
from pathlib import Path
from typing import Any
from pyiceberg.catalog import load_catalog
from pyiceberg.expressions import EqualTo
import pyarrow.parquet as pq
from pyarrow import fs
import duckdb, os, logging, functools, tomllib,requests, pyarrow


########################################## CONSTANTS/VARIABLES ##########################################

CONFIG_PATH = Path(__file__).parent / "dev-config.toml"



########################################## FUNCTIONS ##########################################

# Extract function to load raw JSON files from local directory to MinIO Bronze Bucket
def extract_raw_json_files_to_minio_bronze(toml_config:dict[str, Any], ds:str) -> None:
    """
    Extracts raw JSON files from local filesystem and uploads them to MinIO Bronze Bucket.
    Args:
        toml_config (dict[str, Any]): The TOML configuration dictionary.
        ds (str): The DAG run's execution date in 'YYYY-MM-DD' format. Automatically passed by Airflow.
    Returns:
        None
    """
    partition_path:str = _get_partition_path_blueprint(ds)
    # Example: Bronze partition path is: year=2026/month=02/day=23
    logging.info(f"Bronze partition path is: {partition_path}")

    s3_hook:S3Hook = S3Hook(aws_conn_id=toml_config["STORAGE"]["airflow_aws_connection_id"])  # Connection pointing to the MinIO server container and have to be configured through Airflow webserver UI > Admin > Connections
    files_in_bronze_partition_path:list[str] = s3_hook.list_keys(bucket_name=toml_config["STORAGE"]["bronze_bucket_name"],
                                                                 prefix=f"{partition_path}")

    raw_parquet_files_in_bronze_partition_path:list[str] = s3_hook.list_keys(bucket_name=toml_config["STORAGE"]["bronze_bucket_name"],
                                                                 prefix=f"raw_parquets/{partition_path}")

    logging.info(f"Existing files in MinIO Bronze Bucket at the path raw_parquets/{partition_path}/ : {raw_parquet_files_in_bronze_partition_path}")                                                             
    # Data idempotency and consistency: Clear existing files in the targeted partition path in MinIO Bronze Bucket
    if len(files_in_bronze_partition_path) > 0:
        s3_hook.delete_objects(bucket=toml_config["STORAGE"]["bronze_bucket_name"], 
                               keys=files_in_bronze_partition_path)
        logging.info(f"Existing files were removed from MinIO Bronze Bucket at the path: {partition_path}/")

    if len(raw_parquet_files_in_bronze_partition_path) > 0:
        s3_hook.delete_objects(bucket=toml_config["STORAGE"]["bronze_bucket_name"], 
                               keys=raw_parquet_files_in_bronze_partition_path)
        logging.info(f"Existing files were removed from MinIO Bronze Bucket at the path: {partition_path}/")


    # Now, Scanning all JSON files, following the config["TASKS"]["checking_raw_json_files_existence_file_pattern"]'s patter 
    # in the local source directory and loading them in the MinIO bronze bucket
    with duckdb.connect(config = _get_duckdb_s3_config(toml_config=toml_config)) as conn:
        # Ensure httpfs extension is installed and loaded for interactions between MinIO s3 API and DuckDB
        if conn.sql("SELECT installed FROM duckdb_extensions() where extension_name='httpfs' AND installed='true'").shape[0] == 0:
            conn.execute("INSTALL httpfs;")
        if conn.sql("SELECT loaded FROM duckdb_extensions() where extension_name='httpfs' AND loaded='true'").shape[0] == 0:
            conn.execute("LOAD httpfs;")
        for file in os.listdir(toml_config["TASKS"]["source_dir"]):
            if os.path.isfile(os.path.join(toml_config["TASKS"]["source_dir"], file)) and \
                            file.startswith("sales") and \
                            file.endswith(".json"):
                logging.info(f"====================================================== Uploading file {toml_config["TASKS"]["source_dir"]}/{file} to MinIO bronze bucket... ======================================================")
                s3_hook.load_file(
                                    filename=f"{toml_config["TASKS"]["source_dir"]}/{file}",  # Path of the source file to load 
                                    key=f"{partition_path}/{file}",                             # Destination file path
                                    bucket_name=toml_config["STORAGE"]["bronze_bucket_name"],   
                                    replace=True
                                )
                logging.info(f"====================================================== File {toml_config["STORAGE"]["bronze_bucket_name"]}/{partition_path}/{file} successfully uploaded to MinIO bronze bucket. ======================================================")

                raw_parquet:duckdb.DuckDBPyRelation = conn.read_json(f"{toml_config["TASKS"]["source_dir"]}/{file}")

                # Store raw json as parquet: type casting, columns flatening
                final_file:duckdb.DuckDBPyRelation = raw_parquet\
                                                            .select(
                                                                    duckdb.ColumnExpression("transaction_id").cast("VARCHAR").alias("transaction_id"),                      # Casts transaction_id to VARCHAR
                                                                    duckdb.ColumnExpression("date").cast("TIMESTAMP").alias("transaction_date"),                            # Casts transaction_date to TIMESTAMP
                                                                    duckdb.ColumnExpression("customer.name").cast("VARCHAR").alias("client_name"),                          # Casts client_name to VARCHAR
                                                                    duckdb.ColumnExpression("customer.loyalty_member").cast("BOOLEAN").alias("customer_loyalty_member"),   # Casts customer_loyalty_member to BOOLEAN
                                                                    duckdb.ColumnExpression("basket.items_count").cast("INTEGER").alias("basket_items_count"),              # Casts basket_items_count to INTEGER
                                                                    duckdb.SQLExpression("UNNEST(basket.items).product_name").cast("VARCHAR").alias("basket_items_product_name"),   # Casts item_product_name to VARCHAR
                                                                    duckdb.SQLExpression("UNNEST(basket.items).quantity").cast("INTEGER").alias("basket_items_quantity"),          # Casts item_quantity to INTEGER
                                                                    duckdb.SQLExpression("UNNEST(basket.items).unit_price").cast("DOUBLE").alias("basket_items_unit_price"),        # Casts item_unit_price to DOUBLE
                                                                    duckdb.SQLExpression("UNNEST(basket.items).total_amount").cast("DOUBLE").alias("basket_items_total_amount"),         # Casts total_amount to DOUBLE
                                                                    duckdb.ColumnExpression("total_amount").cast("DOUBLE").alias("total_amount"),                      # Casts transaction_currency to VARCHAR
                                                                    duckdb.ColumnExpression("currency").cast("VARCHAR").alias("currency"),                      # Casts transaction_currency to VARCHAR
                                                                    duckdb.ColumnExpression("payment_method").cast("VARCHAR").alias("payment_method"),                       # Casts payment_method to VARCHAR
                                                                    duckdb.ConstantExpression(ds).cast("DATE").alias("ingestion_date")              # Adds a new column "base_currency" with the value defined in the config file for each row, to be used later in the Gold layer transformations
                                                                )

                                                                    
                final_file.write_parquet(
                                        f"s3://{toml_config['STORAGE']['bronze_bucket_name']}/raw_parquets/{partition_path}/{file.split('/')[-1].replace('.json', '.parquet')}", 
                                        compression=toml_config['STORAGE']['parquet_files_compression_mode'],
                                        overwrite=True
                                    )
                logging.info(final_file.shape)



def setup_environment(access_key: str, secret_key: str, region: str) -> None:
    """
    Configure AWS environment variables for authentication.
    Args:        
        access_key (str): The AWS access key ID.
        secret_key (str): The AWS secret access key.
        region (str): The AWS region name.
    Returns:        None
    """
    os.environ["AWS_ACCESS_KEY_ID"] = access_key
    os.environ["AWS_SECRET_ACCESS_KEY"] = secret_key
    os.environ["AWS_REGION"] = region


def load_raw_parquet_files_to_bronze_iceberg_table(toml_config:dict[str, Any], ds:str) -> None:
    """
    Loads raw parquet files from MinIO Bronze Bucket to the Iceberg Bronze Table.
    Args:
        toml_config (dict[str, Any]): The TOML configuration dictionary.
        ds (str): The DAG run's execution date in 'YYYY-MM-DD' format. Automatically passed by Airflow.
    Returns:
        None
    """

    # Example: Bronze partition path is: year=2026/month=02/day=23
    partition_path:str = _get_partition_path_blueprint(ds)
    logging.info(f"Bronze partition path is: {partition_path}")

    s3_hook:S3Hook = S3Hook(aws_conn_id=toml_config["STORAGE"]["airflow_aws_connection_id"])
    raw_parquet_files_in_bronze_partition_path:list[str] = s3_hook.list_keys(bucket_name=toml_config["STORAGE"]["bronze_bucket_name"],
                                                                             prefix=f"raw_parquets/{partition_path}")
    logging.info(f"Existing parquet files in MinIO Bronze Bucket : {raw_parquet_files_in_bronze_partition_path}")

    # This configuration is necessary to allow the pyiceberg engine to interact with MinIO S3 API and load the raw parquet files from MinIO to the Iceberg Bronze table
    setup_environment(
                        access_key=Connection.get_connection_from_secrets(toml_config["STORAGE"]["airflow_aws_connection_id"]).login,
                        secret_key=Connection.get_connection_from_secrets(toml_config["STORAGE"]["airflow_aws_connection_id"]).password,
                        region="local"
                    )

    # Load the Pyiceberg catalog with a configuration allowing it to interact with MinIO S3 API
    catalog = load_catalog(
                    "minio_warehouse",
                    **{
                        "uri": f"{Connection.get_connection_from_secrets(toml_config["STORAGE"]["airflow_aws_connection_id"]).extra_dejson["endpoint_url"]}/_iceberg",
                        "warehouse": toml_config["STORAGE"]["minio_warehouse_name"],
                        "rest.sigv4-enabled": "true",
                        "rest.signing-name": "s3tables",
                        "rest.signing-region": os.getenv("AWS_REGION"),
                        "s3.access-key-id": os.getenv("AWS_ACCESS_KEY_ID"),
                        "s3.secret-access-key": os.getenv("AWS_SECRET_ACCESS_KEY"),
                        "s3.path-style-access": "true",
                        "s3.endpoint": Connection.get_connection_from_secrets(toml_config["STORAGE"]["airflow_aws_connection_id"]).extra_dejson["endpoint_url"]
                    }
            )

    # Configure a PyArrow filesystem to allow interactions between PyArrow and MinIO S3 API for the loading of raw parquet files from MinIO to the Iceberg Bronze table
    minio_fs = fs.S3FileSystem(
        endpoint_override=Connection.get_connection_from_secrets(toml_config["STORAGE"]["airflow_aws_connection_id"]).extra_dejson["endpoint_url"],
        access_key=os.getenv("AWS_ACCESS_KEY_ID"),
        secret_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region=os.getenv("AWS_REGION"),
        scheme="http"
    )

    # Partition columns to remove from the raw parquet file schema before loading to Iceberg, as they will be added as partition columns in the Iceberg table definition
    cols_to_remove = ['year', 'month', 'day']

    # Loading of Bronze Iceberg table's catalog as a Pyiceberg catalog object
    table_identifier = (toml_config["STORAGE"]["minio_warehouse_namespace"], 
                        toml_config["STORAGE"]["minio_warehouse_bronze_table_name"])
    table = catalog.load_table(table_identifier)
    
    # Filter defintion to ensure partition overwriting will only affect the partition corresponding to the Iceberg Bronze table
    bronze_iceberg_table_partition_overwriting_filter = EqualTo(toml_config["STORAGE"]["minio_warehouse_bronze_table_partition_column"], ds) 
    
    pyiceberg_tables_to_write = []

    for bronze_parquet_file in raw_parquet_files_in_bronze_partition_path:
        arrow_table = pq.read_table(f"{toml_config['STORAGE']['bronze_bucket_name']}/{bronze_parquet_file}", filesystem=minio_fs)
        arrow_table = arrow_table.drop(cols_to_remove)  # Drop partition columns from the table schema before loading to Iceberg, as they will be added as partition columns in the Iceberg table definition
        pyiceberg_tables_to_write.append(arrow_table)
        logging.info(f"Parquet file loaded: {bronze_parquet_file}")
    
    # Overwrite the partition ensuring idempotency and consistency of data in the Iceberg Bronze table, then append the parquet file to the table. 
    # The overwrite action will only affect the partition corresponding to the parquet file's data 
    # (e.g., if the parquet file contains transactions dated "2022-03-22", only the partition "transaction_date=2022-03-22" will be overwritten in the Iceberg table, and not the entire table)
    final_table = pyarrow.concat_tables(pyiceberg_tables_to_write)
    table.overwrite(final_table, overwrite_filter=bronze_iceberg_table_partition_overwriting_filter)
    logging.info("All raw parquet files from MinIO Bronze Bucket were loaded to the Iceberg Bronze table !")

# ===============================================================================================================================================



def _get_partition_path_blueprint(execution_date:str) -> str:
    """
    Crafts a Airflow execution date to a partition path for MinIO buckets.
    Args:
        execution_date (str): The DAG run's execution date in 'YYYY-MM-DD' format. Automatically passed by Airflow.
    Returns:
        str: A string following this format: "year=YYYY/month=MM/day=DD" (based on the values of the "execution_date" parameter)
    """
    partition_path:list[str] = execution_date.split("-")
    partition_path[0] = ''.join(("year=", partition_path[0]))
    partition_path[1] = ''.join(("month=", partition_path[1]))
    partition_path[2] = ''.join(("day=", partition_path[2]))

    # Example of input: "2026-02-23"
    # Example of output: "year=2026/month=02/day=23"
    return '/'.join(partition_path)



# ===============================================================================================================================================



def _get_duckdb_s3_config(toml_config:dict[str, Any]) -> dict[str, str]:
    """
    Returns a preset S3 configuration for a DuckDB relation object. 
    The configuration contains all necessary informations to allow communication between DuckDB engine and MinIO S3 API
    Args:
        toml_config (dict[str, Any]): The TOML configuration dictionary.
    Returns:
        dict[str, str]: A dictionnary containing a S3 API connection parameters for DuckDB
    """
    return {
                "s3_access_key_id": Connection.get_connection_from_secrets(toml_config["STORAGE"]["airflow_aws_connection_id"]).login,
                "s3_secret_access_key": Connection.get_connection_from_secrets(toml_config["STORAGE"]["airflow_aws_connection_id"]).password,
                "s3_endpoint": Connection.get_connection_from_secrets(toml_config["STORAGE"]["airflow_aws_connection_id"]).extra_dejson["endpoint_url"].replace("http://",""),     # MinIO service name as defined in docker-compose file followed by ":{MiniIO_API_Port}" (e.g., "minio-aistor-server:9008"). Do not use "http://" or "https://", and do not use the MinIO Console port instead.
                "s3_url_style": toml_config["STORAGE"]["s3_url_style_config_param"],     # Use "path" URL style for MinIO and "vhost" for AWS S3
                "s3_use_ssl": toml_config["STORAGE"]["s3_use_ssl_config_param"]       # By default MinIO does not enable SSL; set the "duckdb_s3_use_ssl_config_param" variable to "true" in "dev-config.toml" file if a proxy is configured for MinIO
            }



# ===============================================================================================================================================



@functools.cache
def load_config(toml_file_path: str = CONFIG_PATH) -> dict[str, Any]:
    """
    Loads the value of configured variables from a TOML file.
    Args:
        toml_file_path (str): Path to the TOML configuration file.
    Returns:
        dict: The loaded configuration dictionary.
    """
    logging.info(f"Print: {CONFIG_PATH}")
    with open(toml_file_path, "rb") as config_file:
        return tomllib.load(config_file)
   