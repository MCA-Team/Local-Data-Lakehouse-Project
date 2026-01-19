from airflow.providers.amazon.aws.hooks.s3 import S3Hook
import os
import logging

# Extract function to load raw JSON files from local directory to MinIO bronze bucket
def extract_raw_json_files_to_minio_bronze():
    s3_hook = S3Hook(aws_conn_id="minio_conn")  # Connection pointing to MinIO instance and have to be configured through Airflow UI > Admin > Connections
    for file in os.listdir("/opt/airflow/local-data/"):
        if os.path.isfile(os.path.join("/opt/airflow/local-data/", file)) and file.endswith(".json"):
            logging.info(f"Uploading file {file} to MinIO bronze bucket...")
            s3_hook.load_file(
                filename=f"/opt/airflow/local-data/{file}",
                key=f"json/{file}",
                bucket_name="bronze", 
                replace=True)
            logging.info(f"File {file} successfully uploaded to MinIO bronze bucket.")