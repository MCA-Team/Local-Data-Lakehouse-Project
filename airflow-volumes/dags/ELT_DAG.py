from airflow import DAG
from airflow.sensors.filesystem import FileSensor
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from datetime import datetime
from utilities import elt_functions


# Loading of TOML config file's variables
config = elt_functions.load_config()

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

    

    # Task: Checking for the existence of raw JSON files (following the pattern "sales*.json") in the local filesystem before extraction and dumping to bronze zone
    checking_raw_json_files_existence = FileSensor(
            task_id="raw_json_files_availabilty_verification",
            fs_conn_id=config["TASKS"]["fileSensor_connection_id"],   # Connection pointing to /opt/airflow/local-data/ and have to be configured through Airflow webserver UI > Admin > Connections
            filepath=f"{config["STORAGE"]["source_dir"]}/{config['TASKS']["checking_raw_json_files_existence_file_pattern"]}.json",
            poke_interval=config["TASKS"]["checking_raw_json_files_existence_poke_interval"],
            timeout=config["TASKS"]["checking_raw_json_files_existence_timeout"],
            soft_fail=True  # Skips instead of failing
        )
    
    # Task: Extract JSON files from source directory and dumping them into MinIO bronze bucket
    extract = PythonOperator(
        task_id="extract_raw_json_files_to_minio_bronze",
        python_callable=elt_functions.extract_raw_json_files_to_minio_bronze,
        op_kwargs={"toml_config": config}
    )

    # Task: BashOperator task which removes all files from the local source directory after successfully completing the extract task
    remove_local_files = BashOperator(
        task_id="remove_extracted_local_raw_json_files",
        bash_command=f"rm -f {config["STORAGE"]["source_dir"]}/{config['TASKS']["checking_raw_json_files_existence_file_pattern"]}.json",
        trigger_rule = "all_success"
    )

    # Task: Transform (flattening, type checking, filtering) JSON files data from MinIO Bronze Bucket and dumping them into MinIO Silver Bucket
    transform = PythonOperator(
        task_id="transform_bronze_data_and_dump_into_silver_zone",
        python_callable=elt_functions.transform_bronze_data_to_silver,
        op_kwargs={"toml_config": config}
    )

    # Task: Harness and reprocess MinIO Silver bucket data for MinIO Gold Bucket (which is designed for BI purposes)
    load = PythonOperator(
        task_id="data_from_silver_to_gold",
        python_callable=elt_functions.data_from_silver_to_gold,
        op_kwargs={"toml_config": config}
    )

    # DAG's task interdependance
    checking_raw_json_files_existence >> extract >> [transform, remove_local_files]
    transform >> load
