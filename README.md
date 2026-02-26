# Local-Data-Lakehouse-Project

<image src="./doc/arch.png" width=1000 center>

[<img src="https://img.shields.io/badge/docker-29.1.5-blue.svg?logo=docker   ">](https://www.docker.com/)
[<img src="https://img.shields.io/badge/Apache Airflow-2.10.5-successgreen.svg?logo=apacheairflow">](https://airflow.apache.org/docs/apache-airflow/2.10.5/index.html)
[<img src="https://img.shields.io/badge/DuckDB-1.4.3-yellow.svg?logo=duckdb">](https://duckdb.org/docs/stable/clients/python/overview)       [<img src="https://img.shields.io/badge/DuckDB--Engine-0.17.0-yellow.svg?logo=duckdb">](https://duckdb.org/docs/stable/clients/python/overview)
[<img src="https://img.shields.io/badge/quay.io/minio/aistor/minio-RELEASE.2026--02--07T07--43--34Z-red.svg?logo=minio">](https://quay.io/repository/minio/aistor/minio?tab=tags&tag=latest)    [<img src="https://img.shields.io/badge/minio/mc-RELEASE.2025--08--13T08--35--41Z-red.svg?logo=minio">](https://hub.docker.com/r/minio/mc)   [<img src="https://img.shields.io/badge/Apache Superset-6.0.0-turquoise.svg?logo=apachesuperset">](https://superset.apache.org/docs/intro)

## Table of contents
[Overiew](#overiew)

[Prerequisites](#prerequisites)

[Setting up](#setting-up)

[Project directory structure](#project-directory-structure)

[Local lakehouse architecture explained](#local-lakehouse-architecture-explained)

[Run the project](#run-the-project)

---

## Overiew
This project is an exploration of data lakehouse concept. It helps us to understand how a data lake and a data warehouse act together in a single one system: **the data lakehouse**. This project implements the latter locally, simply and is based on a medallion architecture (bronze - silver - gold layers), with open-source and free tools. It is embedded with a practical use case of ELT workflow which transforms raw sales data (JSON format) into actionable KPIs, while meeting industry standards for managing a Lakehouse Data.
> **How does it work ?** <br/>
> This ELT pipeline follows a Medallion Architecture to transform raw sales data into business insights, beginning with the Bronze Zone, where raw JSON files are ingested into MinIO without modification. The data then progresses to the Silver Zone, where it undergoes rigorous processing and is saved to Parquet files. Finally, in the Gold Zone, through SQL aggregations on the Silver Parquet files, high-value business metrics are generated and are stored as final analytical assets.

## Prerequisites
To run this project locally, you must have the following tools already installed on your device:
- **Docker**: which will be the containerization engine (you can use Podman as well)
- **Git**: for pulling the project's repository

## Setting up
After satisfying the requirements above, you can continue with the following steps:

**Step 1**: Clone the project's repository
```bash
git clone https://github.com/MCA-Team/Local-Data-Lakehouse-Project.git
```

**Step 2**: In your terminal, navigate to the project's root  directory. Then, execute the following command in order to automatically create the containers binded volumes directories:
```bash
make create-mount-volumes
```

**Step 3**: Execute the following command in order to generate docker secrets files:
```bash
make create-docker-secrets
```

**Step 4**: Execute the following command in order to generate a blueprint of specific `.env` files for Airflow, MinIO and Superset. It generates in :
- **./airflow-volumes/**: `airflow_core_variables.env` and `airflow_metadata_postgres_variables.env` files
- **./minio-volumes/**: `minio_variables.env` file
- **./superset-volumes/**: `superset_core_variables.env` and `superset_metadata_postgres_variables.env` files
```bash
make airflow-dotenv minio-dotenv superset-dotenv
```
> [!WARNING]
> Every execution overrides the existing files (if they exist)

**Step 5**: Execute the following command in order to generate a blueprint of the global `.env` file. It generates the `./.env` file:
```bash
make dotenv
```
> [!WARNING]
> Every execution overrides the existing files (if they exist)

**Step 6**: Include a MinIO AIStor license in the `./minio-volumes/` directory because without it, MinIO will not run correctly. Go to [MinIO AIStor website](https://www.min.io/pricing) and click **Free > Get started**. You'll receive your free and individual license through e-mail. Download it on your local disk and drop the `minio.license` file into `./minio-volumes/` directory. It should look like this at the end :

```bash
$ tree minio-volumes
minio-volumes/
├── certs/
├── data/
├── minio.license 
└── minio_variables.env
```

## Project directory structure
Now, after setting up some stuff as shown in the previous section, the project directory's structure will look like this:
```bash
$ tree -L 4
.
├── airflow-volumes/
│   ├── airflow_core_variables.env
│   ├── airflow_metadata_postgres_variables.env
│   ├── config/
│   ├── dags/
│   │   ├── ELT_DAG.py
│   │   └── utilities/
│   │       ├── dev-config.toml
│   │       ├── elt_functions.py
│   │       └── __init__.py
│   ├── logs/
│   ├── metadata-postgres-volume/
│   └── plugins/
├── data/
├── doc/
├── docker-compose.yaml
├── dockerfile.airflow
├── docker-secrets/
│   ├── airflow/
│   │   ├── airflow_metadata_postgres_password.secrets
│   │   ├── airflow_sql_alchemy_connection_string.secrets
│   │   └── airflow_www_user_password.secrets
│   ├── minio/
│   │   └── minio_root_passwd.secrets
│   └── superset/
│       ├── superset_admin_password.secrets
│       └── superset_postgres_password.secrets
├── Makefile
├── minio-volumes/
│   ├── certs/
│   ├── data/
│   ├── minio.license
│   └── minio_variables.env
├── README.md
├── requirements.txt
└── superset-volumes/
    ├── cache-redis-volume/
    ├── docker-bootstrap.sh
    ├── docker-entrypoint-initdb.d/
    │   ├── cypress-init.sh
    │   └── examples-init.sh
    ├── docker-init.sh
    ├── metadata-postgres-volume/
    ├── pythonpath_dev/
    │   ├── superset_config_local.example
    │   └── superset_config.py
    ├── requirements-local.txt
    ├── superset_core_variables.env
    ├── superset_home/
    └── superset_metadata_postgres_variables.env
```
Let's explore each directory or file and figure out their purposes:
- **airflow-volumes/**: This directory contains all required volumes to persist Apache Airflow's data. Thoses volumes are binded or mount to ensure data sharing between the Airflow-related containers and local files:
    - <u>***config/***</u>: Apache Airflow allows the user to use a custom configuration to run Airflow. Through this directory, the user can upload a [`airflow.cfg`](https://github.com/puckel/docker-airflow/blob/master/config/airflow.cfg) file detailling the wanted Airflow configuration. If the directory is empty, Airflow will run with default configuration.
    - <u>***dags/***</u>: contains all DAG definitions which will be executed as DAG runs in Airflow. In this context, the only one DAG definition available is `ELT_DAG.py` file which describes the relation between each task from the raw data extraction (for bronze layer) to its refined one (stored in gold layer). This directory contains a subdirectory:
        - ***dags/utilities/***: This directory has 2 files:
            - **`dev-config.toml`**: Through this file, the DAG (defined by `airflow-volumes/dags/ELT_DAG.py` file) can be entirely configured. The file contains a lot of variables the user has to set a value for each. It is configured with default values but feel free to modify it at your ease. This file is designed for development environment usage. For production environment purposes, you can create a `prod-config.toml` file in the same directory as `dev-config.toml` one and based on it.
            - **`elt_functions.py`**: This file is a kind of module with function definitions. Those functions are written based on the values in the `airflow-volumes/dags/utilities/dev-config.toml` file and are called by `airflow-volumes/dags/ELT_DAG.py` file during the Airflow DAG run's execution. In production environment, if you have created a `prod-config.toml` file, you have just to modify the **line 10** of `airflow-volumes/dags/utilities/elt_functions.py` file like this:
            ```python
            CONFIG_PATH = Path(__file__).parent / "utilities" / "prod-config.toml"
            ```
    - <u>***logs/***</u>: This directory contains all persisted Airflow's scheduler logs. Through these logs, the user is able to deeply inspect what happened during a DAG's execution.
    - <u>***plugins/***</u>: All Airflow's installed plugins metadata will be stored in this directory.
    - <u>***postgresql-volume/***</u> In this directory, many informations about Airflow's metadata database are stored. In our case, the database is PostgreSQL.
- **apache-superset-files/**: Apache Supserset needs some configuration before running as a container. This directory holds the necessary files for Superset's containers.
    - **`docker-bootstrap.sh`**: This Bash script is written for **superset(app)**, **superset-worker** and **superset-worker-beat** containers. The script installs the Python requirements for Superset (defined in `./apache-superset-files/requirements-local.txt` file) and for each container, executes the appropriate command in order to start them correctly.
    - <u>***docker-entrypoint-initdb.d/***</u>: The directory contains 2 files:
        - **`cypress-init.sh`**: This Bash script creates a database for Cypress in the Superset metadata database (the **superset-metadata-pgsql** container). Cypress is a testing framework which will simulate a real user and will test some features. It's disabled by default. Take a peek at [Troubleshooting](#troubleshooting) section for additional infos.

        - **`examples-init.sh`**: This Bash script contains all instructions allowing the downloading and the loading of Superset examples (preset dashboards, charts, dataset,...). It's only executed if the variable `SUPERSET_LOAD_EXAMPLES` is set to **yes** in the `./.env` file.
    - **`docker-init.sh`**</u>: This Bash script is written for **superset-init** docker service. It executes the Superset examples loading, if `SUPERSET_LOAD_EXAMPLES=yes` in `./.env` file and sets up admin credentials and permissions.
    - <u>***pythonpath_dev/***</u>: 
        - **`superset_config.py`**: This file contains the pythonic definition of Superset environment variables. It overrides the defined ones in the `./.env` file and uses default values otherwise.
    - **`requirements-local.txt`**: This file contains the definition of all necessary Python additional packages for **Superset containers**.
- **data/**: This directory will receive all `JSON` raw files that will be extracted and dumped into `Bronze` layer later.
- **doc/**: contains some elements for `README.md` documentation file tweaking.
- **docker-compose.yaml**: This `.yaml` file describes the local data lakehouse architecture as a docker stack where each service is interconnected. There are 3 different parts: the data orchestration side with Airflow-related services, the storage side with MinIO services and the BI side with Superset-related ones.
- **dockerfile.airflow**: This dockerfile configures a custom image based on **apache/airflow:2.10.5**'s one by installing the `./requirements.txt` file dependencies.
- **Makefile**: The file which contains preset commands definitions. The `create-binded-volumes` and `dotenv` commands are defined there. It allows wrapping up complex commands sequences in one.
- **minio-volumes/**: This directory contains all required volumes to persist MinIO AIStor's data. Thoses volumes are binded or mount to ensure data sharing between the MinIO container and local files:
    - <u>***certs/***</u>: This directory holds security certificates and shares them with MinIO's container. Especially for SSL authentication, this should be helpful.
    - <u>***data/***</u>: This directory contains the some data about the MinIO container (configuration files, buckets informations like logs, cache,...).
    - **`minio.license`**: It's the activation license required to run the MinIO container correctly. Without it, the MinIO container will not start (correctly).
- **README.md**: The documentation file.
- **requirements.txt**: This file contains the definition of all necessary Python packages to build the `dockerfile.airflow` custom image

## Local lakehouse architecture explained
The architecture is pretty simple. The core is composed by 3 parts :
- **The data orchestrator**: represented by Apache Airflow's ecosystem. It controls the tasks flows and triggers specific tasks accordingly to specific events.
- **The storage**: which represents the Medallion architecture. MinIO which is a S3-compatible Object Storage is fitted for this role. With 3 buckets, each associated to Bronze - Silver - Gold concepts, it fulfills storage requirements for this use case.
- **The BI**: Apache Superset is a modern, open-source and efficient BI tool which totally satisfies BI requirements, providing rich charts and visualization assets.

> How do these 3 parts interact ?

<image src="./doc/arch.png" width=1000 center>

The 3 elements above interact in an ELT process pattern. Apache Airflow configures some tasks. The first Airflow task scans `./data/` directory in order to find `.json` files following the `sales*.json` name pattern. If no file is found, The process exits. Otherwise, Airflow starts its second task which picks found files from `./data/` directory and dumps them into MinIO Bronze bucket. After this operation, files are automatically removed from `./data/` directory. Then, the Bronze bucket's files are selected, processed by DuckDB in-memory engine (installed in Airflow-sceduler container through `./requirements.txt` file) and saved as `.parquet` files into MinIO Silver bucket. Finally, for BI purposes, the last Airflow's task uses the processed Silver files, and apply processings like aggregations in order to keep only one line per date. Those new processed files are saved into MinIO Gold bucket as `.parquet` files.

After that, Apache Superset is preconfigured with DuckDB-engine to allow requests between Superset itself and MinIO Gold bucket files. Then, through SQL queries and drag-and-drop components, a neat and informative dashboard can spring up. That's the global data flow of this local data lakehouse system.

> [!NOTE]
> After the data extraction task successfully wrote the files in Bronze bucket, another task must remove the files from `./data/` directory for local memory purpopes and because Bronze bucket acts like a data lake.

> [!NOTE]
> For **data idempotency and partioning**, the files are stored in MinIO following a temporal file structure for each bucket : `/year=2024/month=01/day=15/sales_20240115.parquet` for example. This allows the user to replay a specific day without impacting the rest.

> [!NOTE]
> This infrastructure is designed as a Modern Data Stack (MDS)



## Run the project
The infrastructure is a set of docker containers. That's why the user have to set up the containers stack by executing the following command in the terminal at the root of the repository's directory:
```bash
make setup-infra
```

> [!WARNING]
> Check the status of all containers. You must have the **'Up'** status for all containers before going on. You can easily check the status through this command:
> ```
> docker container ls
> ```

Main containers Web UI addresses:
Address     | Container/service
----------- | ---------
`http://localhost:8080` | Apache Airflow Web UI
`http://localhost:8088` | Apache Superset Web UI
`http://localhost:9009` | MinIO AIStor Console

After setting up the insfrastructure, the user must configure some stuffs in order to ensure everything is running well:

### 1. Apache Airflow Connections

It is a Airflow's feature that allows the user to store sensitive information like credentials. The configuration can be done through the Airflow Web UI (**Admin > Connection**). The user have to configure 2 Airflow connections:

- **Check `.json` files existence**: To allow Airflow to scan the local directory `./data/` to check the files existence, The user must configure a Airflow connection:

    - <u>*Connection id*</u>: must be the same as the value of `fileSensor_connection_id` variable in `./airflow-volumes/dags/utilities/dev-config.toml` file. By default, it is **"fs_conn"**.
    - <u>*Connection Type*</u>: **File (path)**
    - <u>*Path*</u>: **/opt/airflow/local-data**

<image src="./doc/fs_conn.gif" width=1000 center>

- **Connect Airflow to MinIO**: To allow Airflow to read and write files in MinIO buckets. MinIO being a S3-compatible object storage, its API works like AWS S3 one:

    - <u>*Connection id*</u>: must be the same as the value of `airflow_aws_connection_id` variable in `./airflow-volumes/dags/utilities/dev-config.toml` file. By default, it is **"minio_conn"**.
    - <u>*Connection Type*</u>: **Amazon Web Services**
    - <u>*AWS Access Key ID*</u>: the value of `MINIO_ROOT_USER` variable in `./.env` file.
    - <u>*AWS Secret Access Key*</u>: the value of `MINIO_ROOT_PASSWORD` variable in `./.env` file.
    - <u>*Extra*</u>: The endpoint URL is a string built like this: *"http://<MINIO_CONTAINER_NAME>:<MINIO_API_PORT>"* (it's litteraly the URL which will be used by Airflow to communicate with MinIO's API). So, copy and paste the following snippet:
    ```json
    {
      "endpoint_url": "http://minio-server:9008"
    }
    ```

> [!NOTE]
> For more details: [Airflow S3 connection](https://airflow.apache.org/docs/apache-airflow-providers-amazon/9.2.0/connections/aws.html)

<image src="./doc/minio_conn.gif" width=1000 center>

### 2. Apache Superset configuration
Apache Superset needs an engine to query data from Gold bucket and display it on the dashboard. DuckDB in-memory engine is already embedded in our Superset container. So, the user needs to connect Superset to this engine through **"+ > Data > Connect database"** by following the steps shown below:

<image src="./doc/superset_duckdb.gif" width=1000 center>

- Use SQLAlchemy DuckDB URI for the connection
    - for in-memory usage
        ```
        duckdb:///:memory:
        ```
    - if the user wants to persist data through DuckDB Engine (replace <DB_NAME> by the wanted file name, `superset.db` for example)
        ```
        duckdb:///<DB_NAME>.db
        ```
- The JSON snippet below allows Superset DuckDB's engine to communicate with MinIO's S3 API through an endpoint. Copy and paste the snippet for **Engine Parameters** section:
```json
{
    "connect_args": {
        "config": {
            "s3_endpoint": "minio-server:9008",
            "s3_access_key_id": "<MINIO_ROOT_USER>",
            "s3_secret_access_key": "<MINIO_ROOT_PASSWD>",
            "s3_use_ssl": "false",
            "s3_url_style": "path"
        }
    }
}
```
Then, the user have to create a Superset dataset which is a kind of table view in Superset. In our case, it's simple to do it through the **Superset SQL Lab** with the simple DuckDB SQL request below (replace `YEAR`, `MONTH` and `DAY` by the correct values in order to have the right path to the files in the MinIO Gold bucket):
```sql
SELECT * FROM read_parquet("s3://gold/year=YEAR/month=MONTH/day=DAY/*.parquet");
```
<image src="./doc/superset_dataset.gif" width=1000 center>

Now, the user can build a custom BI dashboard based on the created dataset. There is an example of dataset:







List of useful commands for this project:

Command     | Description
----------- | ---------
```make dotenv``` | Generates a new blueprint for `./.env` file
```make create-binded-volumes``` | Automatically creates the containers binded volumes
```make setup-infra``` | Automatically sets up the infrastructure
```make shutdown-infra``` | Shutdowns and remove all containers

## Troubleshooting

> [!WARNING]
> Cypress is being phased out in favor of Playwright. Use Playwright for all new tests.