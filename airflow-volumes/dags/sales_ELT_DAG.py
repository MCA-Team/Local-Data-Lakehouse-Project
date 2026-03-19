from airflow import DAG
from airflow.sensors.filesystem import FileSensor
from airflow.operators.python import PythonOperator
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
from airflow.operators.bash import BashOperator
from datetime import datetime
from utilities import sales_elt_functions


# Loading of TOML config file's variables
config = sales_elt_functions.load_config()
# DBT config variables from the "dev-config.toml" file
DBT_PROJECT_DIR = config["DBT"]["dbt_project_dir"]
DBT_PROFILES_DIR = config["DBT"]["dbt_profiles_dir"]

# Airflow ELT DAG's default arguments
def_args = {
    "owner": config["DAG"]["owner"],
    "retries": config["DAG"]["retries_number"],
    "start_date": datetime(int(config["DAG"]["start_date"].split("-")[0]),
                           int(config["DAG"]["start_date"].split("-")[1]),
                           int(config["DAG"]["start_date"].split("-")[2])),
    "schedule": config["DAG"]["schedule"]
}


# Our ELT DAG
with DAG(
    dag_id = config["DAG"]["dag_id"],
    description=config["DAG"]["dag_description"],
    catchup=config["DAG"]["catchup"],
    default_args = def_args
) as dag:

    

    # Task FileSensor: Checking for the existence of raw JSON files (following the pattern "sales*.json") in the local filesystem before extraction and dumping to bronze zone
    checking_raw_json_files_existence = FileSensor(
            task_id="raw_json_files_availabilty_verification",
            fs_conn_id=config["TASKS"]["fileSensor_connection_id"],   # Connection pointing to /opt/airflow/local-data/ and have to be configured through Airflow webserver UI > Admin > Connections
            filepath=f"{config['TASKS']["checking_raw_json_files_existence_file_pattern"]}.json",
            poke_interval=config["TASKS"]["checking_raw_json_files_existence_poke_interval"],
            timeout=config["TASKS"]["checking_raw_json_files_existence_timeout"],
            soft_fail=True  # Skips instead of failing
        )
    
    # Task PythonOperator: Extract raw JSON files from source directory and dumping them into MinIO bronze bucket.
    # It also converts raw JSON files to Parquet format and dumping them into MinIO bronze bucket.
    extract = PythonOperator(
                task_id="extract_raw_json_files_to_minio_bronze",
                python_callable=sales_elt_functions.extract_raw_json_files_to_minio_bronze,
                op_kwargs={"toml_config": config}
            )

    # Task BashOperator: task which removes all files from the local source directory after successfully completing the extract task
    remove_local_files = BashOperator(
        task_id="remove_extracted_local_raw_json_files",
        bash_command=f"rm -f {config["TASKS"]["source_dir"]}/{config['TASKS']["checking_raw_json_files_existence_file_pattern"]}.json",
        trigger_rule = "all_success"
    )

    # Task BashOperator: Transform (filtering, aggregations) of data from Iceberg Bronze table data to MinIO Silver and Gold Iceberg tables using dbt.
    dbt_transform = BashOperator(
        task_id="dbt-transformations",
        bash_command=f"dbt run --profiles-dir {DBT_PROFILES_DIR} --project-dir {DBT_PROJECT_DIR}",
        trigger_rule = "all_success"
    )

    # Task PythonOperator: Loading of raw parquet files from MinIO bronze bucket to the Iceberg Bronze table in the MinIO warehouse. This task is executed only after the successful creation of the Iceberg Bronze table and it ensures idempotent loading of data by using the "ingestion_date" partition column in the Iceberg Bronze table.
    populate_bronze_iceberg_table = PythonOperator(
                                        task_id="load_raw_parquet_files_to_bronze_iceberg_table",
                                        python_callable=sales_elt_functions.load_raw_parquet_files_to_bronze_iceberg_table,
                                        op_kwargs={"toml_config": config}
                                    )

    # Task SQLExecuteQueryOperator: Creation of the Iceberg Bronze table schema and in the MinIO warehouse.
    create_iceberg_bronze_table_schema = SQLExecuteQueryOperator(
        task_id='create_iceberg_bronze_table_schema',
        conn_id='trino_conn',
        sql=f"{sales_elt_functions.SQL_SCRIPTS_FOLDER}/create_bronze_iceberg_table_schema.sql",
        params={
            "schema": config["STORAGE"]["minio_warehouse_namespace"],
            "warehouse_name": config["STORAGE"]["minio_warehouse_name"]
        },
        autocommit=True,
        dag=dag
    )

    # Task SQLExecuteQueryOperator: Creation of the Iceberg Bronze table in the MinIO warehouse. 
    # The table is partitioned by the "ingestion_date" column to ensure idempotent loading of raw parquet files from MinIO Bronze Bucket to the Iceberg Bronze table.
    create_iceberg_bronze_table = SQLExecuteQueryOperator(
        task_id='create_iceberg_bronze_table',
        conn_id='trino_conn',
        sql=f"{sales_elt_functions.SQL_SCRIPTS_FOLDER}/create_bronze_iceberg_table.sql",
        params={
            "schema": config["STORAGE"]["minio_warehouse_namespace"],
            "table_name": config["STORAGE"]["minio_warehouse_bronze_table_name"],
            "warehouse_name": config["STORAGE"]["minio_warehouse_name"]
        },
        autocommit=True,
        dag=dag
    )

    # DAG's task interdependency
    checking_raw_json_files_existence >> extract >> [create_iceberg_bronze_table_schema, remove_local_files] 
    create_iceberg_bronze_table_schema >> create_iceberg_bronze_table >> populate_bronze_iceberg_table >> dbt_transform

