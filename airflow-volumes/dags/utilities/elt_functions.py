from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from airflow.models.connection import Connection
from pathlib import Path
from typing import Any
import duckdb, os, logging, functools, tomllib,requests


########################################## CONSTANTS/VARIABLES ##########################################

CONFIG_PATH = Path(__file__).parent / "utilities" / "dev-config.toml"



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
    # Data idempotency and consistency: Clear existing files in the targeted partition path in MinIO Bronze Bucket
    if len(files_in_bronze_partition_path) > 0:
        s3_hook.delete_objects(bucket=toml_config["STORAGE"]["bronze_bucket_name"], 
                               keys=files_in_bronze_partition_path)
        logging.info(f"Existing files were removed from MinIO Bronze Bucket at the path: {partition_path}/")

    # Now, Scanning all JSON files, following the config["TASKS"]["checking_raw_json_files_existence_file_pattern"]'s patter 
    # in the local source directory and loading them in the MinIO bronze bucket
    for file in os.listdir(toml_config["STORAGE"]["source_dir"]):
        if os.path.isfile(os.path.join(toml_config["STORAGE"]["source_dir"], file)) and \
                          file.startswith("sales") and \
                          file.endswith(".json"):
            logging.info(f"====================================================== Uploading file {toml_config["STORAGE"]["source_dir"]}/{file} to MinIO bronze bucket... ======================================================")
            s3_hook.load_file(
                                filename=f"{toml_config["STORAGE"]["source_dir"]}/{file}",  # Path of the source file to load 
                                key=f"{partition_path}/{file}",                             # Destination file path
                                bucket_name=toml_config["STORAGE"]["bronze_bucket_name"],   
                                replace=True
                            )
            logging.info(f"====================================================== File {toml_config["STORAGE"]["bronze_bucket_name"]}/{partition_path}/{file} successfully uploaded to MinIO bronze bucket. ======================================================")



# ===============================================================================================================================================




# "Transform" function which processes data from Bronze Bucket to the Silver one
def transform_bronze_data_to_silver(toml_config:dict[str, Any], ds:str) -> None:
    """
    Transforms data from MinIO Bronze Bucket to the Silver Bucket.
    Args:
        toml_config (dict[str, Any]): The TOML configuration dictionary.
        ds (str): The DAG run's execution date in 'YYYY-MM-DD' format. Automatically passed by Airflow.
    Returns:
        None
    """
    partition_path:str = _get_partition_path_blueprint(ds)
    # Example: Silver partition path is: year=2026/month=02/day=23
    logging.info(f"Silver partition path is: {partition_path}")

    # Initialize S3Hook to interact with MinIO Bronze Bucket and list targeted files to transform
    s3_hook:S3Hook = S3Hook(aws_conn_id=toml_config["STORAGE"]["airflow_aws_connection_id"])  # Connection pointing to MinIO container and have to be configured through Airflow webserver UI > Admin > Connections
    files_to_transform_list:list[str] = s3_hook.list_keys(bucket_name=toml_config["STORAGE"]["bronze_bucket_name"], 
                                                          prefix=f"{partition_path}")
    # Example: Bronze files to be transformed: ['year=2026/month=02/day=23/sales_2025.json', 'year=2026/month=02/day=23/sales_2026.json']
    logging.info(f"Bronze files to be transformed: {files_to_transform_list}")

    # Data idempotency and consistency: Clear existing files in the targeted partition path in MinIO Silver Bucket
    files_in_silver_partition_path:list[str] = s3_hook.list_keys(bucket_name=toml_config["STORAGE"]["silver_bucket_name"], 
                                                                 prefix=f"{partition_path}")
    if len(files_in_silver_partition_path) > 0:
        s3_hook.delete_objects(bucket=toml_config["STORAGE"]["silver_bucket_name"], 
                               keys=files_in_silver_partition_path)
        logging.info(f"Existing files were removed from MinIO Silver Bucket at the path: {partition_path}/")

    # Opening an in-memory connection to DuckDB engine with a AWS S3 configuration 
    with duckdb.connect(config = _get_duckdb_s3_config(toml_config=toml_config)) as conn:
        # Ensure httpfs extension is installed and loaded for interactions between MinIO S3 API and DuckDB engine
        if conn.sql("SELECT installed FROM duckdb_extensions() where extension_name='httpfs' AND installed='true'").shape[0] == 0:
            conn.execute("INSTALL httpfs;")
        if conn.sql("SELECT loaded FROM duckdb_extensions() where extension_name='httpfs' AND loaded='true'").shape[0] == 0:
            conn.execute("LOAD httpfs;")

        # Transformation logic goes there
        for bronze_file_path in files_to_transform_list:
            _apply_silver_transformations_and_write_parquet( 
                                                             toml_config=toml_config,
                                                             duckdb_connection=conn,
                                                             fileToTransform_path=bronze_file_path, 
                                                             silver_partition_path=partition_path
                                                           )
    logging.info("Data transformation from Bronze to Silver completed.")



# ===============================================================================================================================================



def data_from_silver_to_gold(toml_config:dict[str, Any], ds:str) -> None:
    """
    Winnows and refines data from MinIO Silver Bucket to the Gold Bucket.
    Args:
        toml_config (dict[str, Any]): The TOML configuration dictionary.
        ds (str): The DAG run's execution date in 'YYYY-MM-DD' format. Automatically passed by Airflow.
    Returns:
        None
    """
    partition_path:str = _get_partition_path_blueprint(ds)
    # Example: Gold partition path is: year=2026/month=02/day=23
    logging.info(f"Gold partition path is: {partition_path}")

    # Initialize S3Hook to interact with MinIO Silver Bucket and list targeted files to transform
    s3_hook:S3Hook = S3Hook(aws_conn_id=toml_config["STORAGE"]["airflow_aws_connection_id"])  # Connection pointing to MinIO container and have to be configured through Airflow webserver UI > Admin > Connections
    files_to_transform_list:list[str] = s3_hook.list_keys(bucket_name=toml_config["STORAGE"]["silver_bucket_name"], 
                                                          prefix=f"{partition_path}")
    # Example: Silver files to be transformed: ['year=2026/month=02/day=23/sales_2025.parquet', 'year=2026/month=02/day=23/sales_2026.parquet']
    logging.info(f"Silver files to be transformed: {files_to_transform_list}")

    # Data idempotency and consistency: Clear existing files in the targeted partition path in MinIO Gold Bucket
    files_in_gold_partition_path:list[str] = s3_hook.list_keys(bucket_name=toml_config["STORAGE"]["gold_bucket_name"], 
                                                                prefix=f"{partition_path}")
    if len(files_in_gold_partition_path) > 0:
        s3_hook.delete_objects(bucket=toml_config["STORAGE"]["gold_bucket_name"], 
                               keys=files_in_gold_partition_path)
        logging.info(f"Existing files were removed from MinIO Gold Bucket at the path: {partition_path}/")

    # Opening an in-memory connection to DuckDB engine with a AWS S3 configuration
    with duckdb.connect(config = _get_duckdb_s3_config(toml_config=toml_config)) as conn:
        # Ensure httpfs extension is installed and loaded for interactions between MinIO s3 API and DuckDB
        if conn.sql("SELECT installed FROM duckdb_extensions() where extension_name='httpfs' AND installed='true'").shape[0] == 0:
            conn.execute("INSTALL httpfs;")
        if conn.sql("SELECT loaded FROM duckdb_extensions() where extension_name='httpfs' AND loaded='true'").shape[0] == 0:
            conn.execute("LOAD httpfs;")

        # Transformation logic goes here
        for silver_file_path in files_to_transform_list:
            _gold_layer_processing( 
                                    toml_config=toml_config,
                                    duckdb_connection=conn,
                                    fileToTransform_path=silver_file_path, 
                                    gold_partition_path=partition_path
                                  )
    logging.info("Data transformation from Silver to Gold completed.")



# ===============================================================================================================================================



def _apply_silver_transformations_and_write_parquet(toml_config:dict[str, Any], 
                                                    duckdb_connection: duckdb.DuckDBPyConnection, 
                                                    fileToTransform_path: str, 
                                                    silver_partition_path: str) -> None:
    """
    Applies necessary transformations to the sales raw data and writes the output into MinIO Silver Bucket through Parquet format.
    Args:
        toml_config (dict[str, Any]): The TOML configuration dictionary.
        duckdb_connection (duckdb.DuckDBPyConnection): The DuckDB engine connection object. It allows SQL operations through data.
        fileToTransform_path (str): The path of the file to transform within the Bronze Bucket.
        silver_partition_path (str): The destination path (within the Silver Bucket) where the transformed data will be written. This path is based on the Airflow execution date.
    Returns:
        None
    """
    logging.info(f"====================================================== Performing Silver data processing for the file  : s3://{toml_config['STORAGE']['bronze_bucket_name']}/{fileToTransform_path} ======================================================")
    fileToTransform:duckdb.DuckDBPyRelation = duckdb_connection.read_json(f"s3://{toml_config['STORAGE']['bronze_bucket_name']}/{fileToTransform_path}")

    # Transformations: type casting, columns flatening, data filtering
    final_file:duckdb.DuckDBPyRelation = fileToTransform\
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

    # Ensuring all transformations performed well and the final data is as identical as the excepted result
    logging.info("Data verification before writting in Silver bucket...")
    type_validator:dict[str, str] = {column_name:type_name for column_name, type_name in zip(final_file.columns, final_file.types)}
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
    logging.info("Data verification completed successfully. Writing transformed data to MinIO Silver Bucket...")

    # Writting of the final data into Silver bucket
    final_file.write_parquet(
                                f"s3://{toml_config['STORAGE']['silver_bucket_name']}/{silver_partition_path}/{fileToTransform_path.split('/')[-1].replace('.json', '.parquet')}", 
                                compression=toml_config['STORAGE']['silver_parquet_files_compression_mode'],
                                overwrite=True
                            )
    logging.info(f"====================================================== Transformed data written to MinIO Silver Bucket through Parquet format at : s3://{toml_config['STORAGE']['silver_bucket_name']}/{silver_partition_path}/{fileToTransform_path.split('/')[-1].replace('.json', '.parquet')} ======================================================")



# ===============================================================================================================================================



def _gold_layer_processing(toml_config:dict[str, Any], 
                        duckdb_connection: duckdb.DuckDBPyConnection, 
                        fileToTransform_path: str, 
                        gold_partition_path: str) -> None:
    """
    Affines Silver Bucket data through additional transformations and aggregations and writes the outpout into MinIO Gold Bucket through Parquet format.
    Args:
        toml_config (dict[str, Any]): The TOML configuration dictionary.
        duckdb_connection (duckdb.DuckDBPyConnection): The DuckDB engine connection object. It allows SQL operations through data.
        fileToTransform_path (str): The path of the file to transform within the Silver Bucket.
        gold_partition_path (str): The destination path (within the Gold Bucket) where the transformed data will be written. This path is based on the Airflow execution date.
    Returns:
        None
    """
    logging.info(f"====================================================== Performing Gold data processing for the file  : s3://{toml_config['STORAGE']['silver_bucket_name']}/{fileToTransform_path} ======================================================")
    fileToTransform:duckdb.DuckDBPyRelation = duckdb_connection.sql( f"""
                                                                        SELECT  transaction_id, \
                                                                                transaction_date::DATE AS transaction_date, \
                                                                                item_product_name,  \
                                                                                total_amount,  \
                                                                                transaction_currency,  \
                                                                        FROM    read_parquet('s3://{toml_config['STORAGE']['silver_bucket_name']}/{fileToTransform_path}')
                                                                        """)
    
    # Retrieval of all unique currency in the column "transaction_currency" and conversion of each one (through an real-time updated API service) to the base currency.
    # By default, "EUR" is the base currency, but it can be changed through ["TASKS"]["gold_bucket_base_currency"] variable in the dev-config.toml file
    transaction_currencies:list[str] = [currency[0].lower() for currency in fileToTransform.select("transaction_currency").distinct().fetchall()]
    conversion_bag:dict[str, float] = _get_currencies_rates(currencies_to_convert=transaction_currencies, 
                                                            base_currency_code=toml_config["TASKS"]["gold_bucket_base_currency"])

    # Conversion of all values in "total_amount" column into base currency equivalent through the conversion_bag defined above
    convert_currency:callable[[float, str], float] = lambda amount, currency_code_to_convert : round(amount / conversion_bag[currency_code_to_convert],3)
    if len(duckdb_connection\
                        .execute("SELECT function_name FROM duckdb_functions() WHERE function_name = 'convert_currency'")\
                        .fetchall()
            )==0:
        duckdb_connection.create_function("convert_currency", 
                                          convert_currency, 
                                          ['DOUBLE', 'VARCHAR'], 'DOUBLE')

    total_amount_base_currency_expr:duckdb.Expression = duckdb.FunctionExpression( "convert_currency",
                                                                               duckdb.ColumnExpression("total_amount"),
                                                                               duckdb.ColumnExpression("transaction_currency"))

    # Appending "total_amount_eur" column (which is the total amount equivalent in the base currency) to the table to transform
    fileToTransform:duckdb.DuckDBPyRelation = fileToTransform\
                                                        .select(duckdb.StarExpression(), 
                                                                total_amount_base_currency_expr.alias("total_amount_base_currency"))
    logging.info(f"file to transform sample: \n{fileToTransform.limit(3)}")


    # Each day total revenue: Sum of total_amount aggregated per day
    total_revenue:duckdb.DuckDBPyRelation = fileToTransform\
                                                    .aggregate(
                                                        aggr_expr="transaction_date, SUM(total_amount_base_currency)::DECIMAL(10,3) AS total_revenue", 
                                                        group_expr="transaction_date")\
                                                    .set_alias("total_revenue")
    logging.info(f"total_revenue column created")
    
    # Each day total number of orders
    assert fileToTransform.select("transaction_date").distinct().count("transaction_date").shape[0] <= 366, "A year got a maximum of 366 days"
    order_count:duckdb.DuckDBPyRelation = fileToTransform\
                                                    .aggregate(
                                                        aggr_expr="transaction_date, COUNT(DISTINCT transaction_id) AS order_count", 
                                                        group_expr="transaction_date")\
                                                    .set_alias("order_count")
    logging.info(f"order_count column created")
    
    # avg_order_value : the average amount expensed per day by a customer
    ## joining order_count and total_revenue tables
    tmp:duckdb.DuckDBPyRelation = order_count.join(other_rel=total_revenue, 
                                                    condition="transaction_date", 
                                                    how="inner")
    ## computing the avg_order_value
    avg_order_value_expr:duckdb.Expression = duckdb.FunctionExpression('divide', 
                                                                       duckdb.ColumnExpression("total_revenue"), 
                                                                       duckdb.ColumnExpression("order_count"))

    avg_order_value:duckdb.DuckDBPyRelation = tmp.select(duckdb.StarExpression(), 
                                                         avg_order_value_expr.cast('DECIMAL(10,3)').alias("avg_order_value"))\
                                                 .set_alias("avg_order_value")
    logging.info(f"avg_order_value column created")

    # top_category_product_name : most sold item per day (and its revenue)
    ## retrieving each distinct category and its total revenue per day
    total_revenue_per_category_per_day:duckdb.DuckDBPyRelation = fileToTransform\
                                                                            .aggregate(aggr_expr="transaction_date, item_product_name  AS top_category_product_name, SUM(total_amount_base_currency)::DECIMAL(10,3) AS categories_daily_total_revenue",
                                                                                        group_expr="transaction_date, top_category_product_name")\
                                                                            .set_alias("total_revenue_per_category_per_day")
    ## retrieving the highest value for "categories_daily_total_revenue" colmun per day
    top_category_total_revenue_per_day:duckdb.DuckDBPyRelation = total_revenue_per_category_per_day\
                                                                                        .aggregate(aggr_expr="transaction_date, MAX(categories_daily_total_revenue) AS top_category_total_revenue",
                                                                                                    group_expr="transaction_date")\
                                                                                        .distinct()\
                                                                                        .set_alias("top_category_total_revenue_per_day")

    ## joining "total_revenue_per_category_per_day" and "top_category_total_revenue_per_day" to get the top category name and total_revenue per day
    top_category:duckdb.DuckDBPyRelation = top_category_total_revenue_per_day\
                                                                .join(other_rel=total_revenue_per_category_per_day, 
                                                                        condition="top_category_total_revenue_per_day.top_category_total_revenue = total_revenue_per_category_per_day.categories_daily_total_revenue AND \
                                                                                    top_category_total_revenue_per_day.transaction_date = total_revenue_per_category_per_day.transaction_date", 
                                                                        how="inner")\
                                                                .select(*["top_category_total_revenue_per_day.transaction_date", "top_category_product_name", "top_category_total_revenue"])
    logging.info(f"top_category_product_name column created")

    # Merging all metric columns into a single final Gold table
    final_gold_table:duckdb.DuckDBPyRelation = top_category\
                                                        .join(avg_order_value, condition="transaction_date", how="inner")\
                                                        .order("transaction_date")
    logging.info(f"final_gold_table created sample: \n{final_gold_table.limit(5)}")

    # Writting of the final data into Gold bucket
    final_gold_table.write_parquet(
                                    f"s3://{toml_config['STORAGE']['gold_bucket_name']}/{gold_partition_path}/{fileToTransform_path.split('/')[-1]}", 
                                    compression=toml_config['STORAGE']['gold_parquet_files_compression_mode'],
                                    overwrite=True
                                )
    logging.info(f"====================================================== Transformed data written to MinIO Gold Bucket through Parquet format at : s3://{toml_config['STORAGE']['gold_bucket_name']}/{gold_partition_path}/{fileToTransform_path.split('/')[-1]} ======================================================")
 


# ===============================================================================================================================================



def _get_currencies_rates(currencies_to_convert:list[str], 
                         base_currency_code:str="EUR") -> dict[str, float]:
    """
    Crafts a Airflow execution date to a partition path for MinIO buckets.
    Args:
        currencies_to_convert (list[str]): The list of the currencies which will be converted.
        base_currency_code (str): The code of the currency on which each conversion will be performed.
        For example if "EUR" is the base_currency_code, we have to convert other currencies amounts into EUR
    Returns:
        str: A dictionary which has as keys, elements in currencies_to_convert, and as value the related converted value to each key based on the base_currency_code.
        Example: The output is {"XOF": 656.66, "EUR":1} for the following inputs: base_currency_code="EUR" and currencies_to_convert = ["XOF", "EUR"]
    """
    api_url:str = f"https://open.er-api.com/v6/latest/{base_currency_code}"
    exchange_rates:dict[str, float] = requests.get(api_url).json()["rates"]

    conversion_bag = {currency.upper() : exchange_rates[currency.upper()] for currency in currencies_to_convert}
    logging.info(f"The base currency is : {base_currency_code}")
    logging.info(f"Conversion bag is: {conversion_bag}")
    return conversion_bag



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
                "s3_url_style": toml_config["STORAGE"]["duckdb_s3_url_style_config_param"],     # Use "path" URL style for MinIO and "vhost" for AWS S3
                "s3_use_ssl": toml_config["STORAGE"]["duckdb_s3_use_ssl_config_param"]       # By default MinIO does not enable SSL; set the "duckdb_s3_use_ssl_config_param" variable to "true" in "dev-config.toml" file if SSL is configured
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
   