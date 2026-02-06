# Local-Data-Lakehouse-Project

<image src="./doc/arch.png" width=1000 center>

[<img src="https://img.shields.io/badge/docker-29.1.5-blue.svg?logo=docker   ">](https://www.docker.com/)
[<img src="https://img.shields.io/badge/Apache Airflow-2.10.5-successgreen.svg?logo=apacheairflow">](https://airflow.apache.org/docs/apache-airflow/2.10.5/index.html)
[<img src="https://img.shields.io/badge/DuckDB-1.4.3-yellow.svg?logo=duckdb">](https://duckdb.org/docs/stable/clients/python/overview)
[<img src="https://img.shields.io/badge/quay.io/minio/aistor/minio-latest-red.svg?logo=minio">](https://quay.io/repository/minio/aistor/minio?tab=tags&tag=latest)       [<img src="https://img.shields.io/badge/Apache Superset-6.0.0-turquoise.svg?logo=apachesuperset">](https://superset.apache.org/docs/intro)

## Table of contents
[Overiew](#overiew)

[Prerequisites](#prerequisites)

[Setting up](#setting-up)

[Project arborescence](#project-arborescence)

[Local lakehouse architecture explained](#local-lakehouse-architecture-explained)


## Overiew
This project is an exploration of data lakehouse concept. It helps us to understand how a data lake and a data warehouse act together in a single one system: **the data lakehouse**. This project implements it locally, simply and based on a medallion architecture (bronze - silver - gold layers), with open-source and free tools. 

## Prerequisites
To run this project locally, you must have the following tools already installed on your device:
- **Docker**: which will be the containerization engine (you can use Podman as well)
- **Git**: for pulling the project's repository

## Setting up
After satisfying the above requirements, you can continue with the following steps:

**Step 1**: Clone the project's repository
```bash
git clone https://github.com/MCA-Team/Local-Data-Lakehouse-Project.git
```

**Step 2**: In your terminal, navigate to the repository's root directory. Then execute the following command in order to automatically create containers' binded volumes.
```bash
make create-binded-volumes
```

**Step 3**: Execute the following command in order to generate a blueprint of the `.env` file:
```bash
make dotenv
```





## Project arborescence

## Local lakehouse architecture explained

## Demo

## Troubleshooting
