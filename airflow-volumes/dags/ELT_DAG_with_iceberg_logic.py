from airflow import DAG
from airflow.sensors.filesystem import FileSensor
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from datetime import datetime
from utilities import elt_functions_with_iceberg


# Loading of TOML config file's variables
config = elt_functions_with_iceberg.load_config()

DBT_PROJECT_DIR = "/opt/airflow/dbt"  # Path to the dbt project directory inside the Airflow container
DBT_PROFILES_DIR = "/opt/airflow/dbt/dbt_profiles"  # Path to the dbt profiles directory inside the Airflow container

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
    dag_id = "DAG_with_Iceberg_logic",
    description=config["DAG"]["dag_description"],
    catchup=config["DAG"]["catchup"],
    default_args = def_args
) as dag:

    

    # Task: Checking for the existence of raw JSON files (following the pattern "sales*.json") in the local filesystem before extraction and dumping to bronze zone
    checking_raw_json_files_existence = FileSensor(
            task_id="raw_json_files_availabilty_verification",
            fs_conn_id=config["TASKS"]["fileSensor_connection_id"],   # Connection pointing to /opt/airflow/local-data/ and have to be configured through Airflow webserver UI > Admin > Connections
            filepath=f"{config['TASKS']["checking_raw_json_files_existence_file_pattern"]}.json",
            poke_interval=config["TASKS"]["checking_raw_json_files_existence_poke_interval"],
            timeout=config["TASKS"]["checking_raw_json_files_existence_timeout"],
            soft_fail=True  # Skips instead of failing
        )
    
    # Task: Extract raw JSON files from source directory and dumping them into MinIO bronze bucket
    extract = PythonOperator(
                task_id="extract_raw_json_files_to_minio_bronze",
                python_callable=elt_functions_with_iceberg.extract_raw_json_files_to_minio_bronze,
                op_kwargs={"toml_config": config}
            )

    # Task BashOperator: task which removes all files from the local source directory after successfully completing the extract task
    remove_local_files = BashOperator(
        task_id="remove_extracted_local_raw_json_files",
        bash_command=f"rm -f {config["TASKS"]["source_dir"]}/{config['TASKS']["checking_raw_json_files_existence_file_pattern"]}.json",
        trigger_rule = "all_success"
    )

    # Task BashOperator: Transform (filtering, aggregations) of data from Iceberg Bronze table data to MinIO silver and gold Iceberg tables using dbt.
    transform = BashOperator(
        task_id="dbt-transformation",
        bash_command=f"dbt run --profiles-dir {DBT_PROFILES_DIR} --project-dir {DBT_PROJECT_DIR}",
        trigger_rule = "all_success"
    )

    bronze_iceberg = PythonOperator(
                        task_id="load_raw_parquet_files_to_bronze_iceberg_table",
                        python_callable=elt_functions_with_iceberg.load_raw_parquet_files_to_bronze_iceberg_table,
                        op_kwargs={"toml_config": config}
                    )

    # DAG's task interdependency
    checking_raw_json_files_existence >> extract >> bronze_iceberg >> [transform, remove_local_files]

    # transform >> load
