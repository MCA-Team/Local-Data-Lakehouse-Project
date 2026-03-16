from airflow import DAG
# Establishing connection to Trino engine
# from trino.dbapi import connect
from utilities import elt_functions
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta
import os
import logging

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


# Define the SQL query to return a value
query = """ALTER TABLE silver.sales.bronze_table 
        EXECUTE add_files(
            location => 's3://bronze/raw_parquets/year={{ execution_date.year }}/month={{ "{:02d}".format(execution_date.month) }}/day={{ "{:02d}".format(execution_date.day) }}/',
            format => 'PARQUET'
        ) """

             
# Define the Python function to get sql query
def get_sql_from_xcom(**kwargs):
    ti = kwargs['ti']
    sql_query = ti.xcom_pull(task_ids='get_table_rowcount')
    if sql_query:
        return sql_query[0][0]
    else:
        return None


with DAG(
    dag_id = "test_elt_dag",
    description=config["DAG"]["dag_description"],
    catchup=config["DAG"]["catchup"],
    default_args = def_args
) as dag:

    create_schema_iceberg = SQLExecuteQueryOperator(
        task_id='create_iceberg_schema',
        conn_id='trino',
        sql="""
            CREATE SCHEMA IF NOT EXISTS silver.sales
            WITH (location = 's3a://silver/')
            """,
        autocommit=True,
        dag=dag
    )

    create_raw_iceberg_sales = SQLExecuteQueryOperator(
        task_id='create_iceberg_sales_table',
        conn_id='trino',
        sql="""
            CREATE TABLE IF NOT EXISTS silver.sales.bronze_table (
               transaction_id VARCHAR,
               transaction_date TIMESTAMP,
               client_name VARCHAR,
               customer_loyalty_member BOOLEAN,
               basket_items_count INTEGER,
               basket_items_product_name VARCHAR,
               basket_items_quantity INTEGER,
               basket_items_unit_price DOUBLE,
               basket_items_total_amount DOUBLE,
               total_amount DOUBLE,
               currency VARCHAR,
               payment_method VARCHAR,
               ingestion_date DATE
            )
             WITH ( format = 'PARQUET', location = 's3a://silver/sales/bronze_table/' )
        """,
        autocommit=True,
        dag=dag
    )

    # Task to execute the SQL query
    get_table_rowcount = SQLExecuteQueryOperator(
        task_id='add_new_files_to_bronze',
        sql=query,
        conn_id='trino',  # Replace with your connection ID
    )

    # Tâche pour vider la table
    drop_bronze = SQLExecuteQueryOperator(
        task_id='drop_bronze_table',
        conn_id='trino',
        sql="DROP TABLE IF EXISTS silver.sales.bronze_table", # Supprime les données, garde le schéma
        dag=dag
    )

    get_sql_from_xcom_task = PythonOperator(
        task_id='get_sql_from_xcom_task',
        python_callable=get_sql_from_xcom,
        provide_context=True
        )

    add_table_data  = SQLExecuteQueryOperator(
        task_id='update_add_data',
        sql="{{ ti.xcom_pull(task_ids='get_sql_from_xcom_task') }}",
        conn_id='trino', 
        autocommit=True
    )

    create_schema_iceberg >> drop_bronze >> create_raw_iceberg_sales >> get_table_rowcount >> get_sql_from_xcom_task >> add_table_data
    
    # Task: Extract raw JSON files from source directory and dumping them into MinIO bronze bucket
    # extract = PythonOperator(
    #     task_id="icerberg_test_task",
    #     python_callable=icerberg_test_task
    # )

    

