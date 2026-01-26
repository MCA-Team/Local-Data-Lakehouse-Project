from airflow import DAG
from airflow.sensors.filesystem import FileSensor
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
import logging, tomllib
from datetime import datetime
from utilities import etl_functions

def_args = {
    "owner": "local-lakehouse",
    "retries": 5,
    "catchup": False,  
    "start_date": datetime(2026, 1, 16),
    "schedule": "@hourly"
}

with DAG(
    dag_id = "Ecommerce_data_ETL_DAG",
    description="Through a medallion architecture, this DAG describes the data ETL process",
    default_args = def_args
) as dag:

    with open("dev-config.toml", "rb") as config_file:
        data = tomllib.load(config_file)

    # Task: Check for the existence of raw JSON files in the local filesystem before extraction and dumping to bronze zone
    checking_raw_json_files_existence = FileSensor(
            task_id="raw_json_files_availabilty_verification",
            fs_conn_id="fs_conn",   # Connection pointing to /opt/airflow/local-data/ and have to be configured through Airflow UI > Admin > Connections
            filepath="sales_*.json",
            poke_interval=10,
            soft_fail=True,  # Skips instead of failing
            timeout=30
        )
    

    extract = PythonOperator(
        task_id="extract_raw_json_files_to_minio_bronze",
        python_callable=etl_functions.extract_raw_json_files_to_minio_bronze
    )

    remove_local_files = BashOperator(
        task_id="remove_local_raw_json_files",
        bash_command="rm -f /opt/airflow/local-data/sales_*.json"
    )

    transform = PythonOperator(
        task_id="transform_bronze_data_to_silver_zone",
        python_callable=etl_functions.transform_bronze_data_to_silver
    )

    checking_raw_json_files_existence >> extract >> [transform, remove_local_files]
    # extract >> transform
