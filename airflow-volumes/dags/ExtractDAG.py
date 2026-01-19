from airflow import DAG
from airflow.sensors.filesystem import FileSensor
from airflow.operators.python import PythonOperator
import logging
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

    # Task: Check for the existence of raw JSON files in the local filesystem before extraction and dumping to bronze zone
    checking_raw_json_files_existence = FileSensor(
            task_id="source_files_verification",
            fs_conn_id="fs_conn",   # Connection pointing to /opt/airflow/local-data/ and have to be configured through Airflow UI > Admin > Connections
            filepath="sales_*.json",
            poke_interval=10,
            timeout=30
        )
    
    
    logging.info("Source files are available for extraction.")

    extract = PythonOperator(
        task_id="extract_raw_json_files_to_minio_bronze",
        python_callable=etl_functions.extract_raw_json_files_to_minio_bronze
    )

    checking_raw_json_files_existence >> extract
