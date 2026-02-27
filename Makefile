.PHONY: help create-mount-volumes setup-infra shutdown-infra create-docker-secrets airflow-dotenv minio-dotenv superset-dotenv dotenv
.DEFAULT_GOAL = help


help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-24s\033[0m %s\n", $$1, $$2}'

create-mount-volumes: ## Automatically creates the containers mount volumes
	@for directory_name in "airflow-volumes/dags" \
							"airflow-volumes/logs" \
							"airflow-volumes/config" \
							"airflow-volumes/plugins" \
							"airflow-volumes/metadata-postgres-volume" \
							"minio-volumes/data" \
							"minio-volumes/certs" \
							"superset-volumes/cache-redis-volume" \
							"superset-volumes/metadata-postgres-volume" \
							"superset-volumes/superset_home"; \
	do \
		if [ ! -d "$$directory_name" ]; then \
			echo "Creation of $$directory_name directory"; \
			mkdir -p $$directory_name; \
			echo "Successfully done"; \
		else \
			echo "$$directory_name directory already exists"; \
		fi \
	done
	@echo "============================================================="
	@echo "All mount volumes created"
	
	
setup-infra: ## Automatically sets up the infra by creating the containers, the volumes and the network(s)
	@docker compose -f docker-compose.yaml up -d
	@echo "Wait a moment...\n"
	@sleep 5
# 	@docker compose rm -f superset-init minio-autocreate-buckets
	@echo "Infrastructure successfully set up !"

shutdown-infra:	## Automatically shuts down the infra removing the containers and the network(s)
	@docker compose down

create-docker-secrets:	## Automatically creates '.secrets' files in the docker-secrets/ directory in order to store docker container's sensitive information
	@if [ ! -d "./docker-secrets/" ]; then\
		mkdir ./docker-secrets;\
	else\
		for directory_name in "./docker-secrets/airflow/" \
							  "./docker-secrets/minio/" \
							  "./docker-secrets/superset/"; \
		do \
			if [ ! -d "$$directory_name" ]; then\
				mkdir -p $$directory_name;\
			fi\
		done \
	fi
	@touch ./docker-secrets/airflow/airflow_www_user_password.secrets\
		   ./docker-secrets/airflow/airflow_metadata_postgres_password.secrets \
		   ./docker-secrets/minio/minio_root_passwd.secrets \
		   ./docker-secrets/superset/superset_postgres_password.secrets \
		   ./docker-secrets/superset/superset_admin_password.secrets
	@echo "postgresql+psycopg2://<AIRFLOW_POSTGRES_USER>:$<AIRFLOW_POSTGRES_PASSWORD>@airflow-postgres/<AIRFLOW_POSTGRES_DB>" >> ./docker-secrets/airflow/airflow_sql_alchemy_connection_string.secrets
	@echo "Docker secrets successfully created !"

airflow-dotenv: ## Generates all required .env files for Apache Airflow containers
	@echo "Creation of new './airflow-volumes/airflow_core_variables.env' file
	@echo "# AIRFLOW CORE ENV. VARIABLES\n\
_AIRFLOW_WWW_USER_USERNAME=airflow" > ./airflow-volumes/airflow_core_variables.env
	@echo "Creation of new './airflow-volumes/airflow_metadata_postgres_variables.env' file
	@echo "# AIRFLOW POSTGRES METADATA DATABASE ENV. VARIABLES\n\
POSTGRES_USER=airflow\n\
POSTGRES_DB=airflow" > ./airflow-volumes/airflow_metadata_postgres_variables.env
	@echo "Successfully done"

minio-dotenv: ## Generates all required .env files for MinIO AIStor containers
	@echo "Creation of new './minio-volumes/minio_variables.env' file"
	@echo "# MINIO AISTOR CORE ENV. VARIABLES\n\
MINIO_BRONZE_BUCKET_NAME=bronze\n\
MINIO_SILVER_BUCKET_NAME=silver\n\
MINIO_GOLD_BUCKET_NAME=gold\n\
\n\
#MINIO AISTOR CREDENTIALS (ROOT_USER >= 3 CHARACTERS)\n\
MINIO_ROOT_USER=airflow" > ./minio-volumes/minio_variables.env
	@echo "Successfully done"

superset-dotenv: ## Generates all required .env files for Apache Superset containers
	@echo "Creation of new './superset-volumes/superset_metadata_postgres_variables.env' file"
	@echo "# SUPERSET POSTGRES METADATA DATABASE ENV. VARIABLES\n\
\n\
# database configurations (do not modify)\n\
POSTGRES_USER=superset\n\
POSTGRES_DB=superset\n\
# Cypress testing db credentials\n\
EXAMPLES_DB=examples\n\
EXAMPLES_USER=examples\n\
EXAMPLES_PASSWORD=examples" > ./superset-volumes/superset_metadata_postgres_variables.env
	@echo "Creation of new './superset-volumes/superset_core_variables.env' file"
	@echo "# SUPERSET CORE ENV. VARIABLES\n\
\n\
# Allowing python to print() in docker\n\
PYTHONUNBUFFERED=1\n\
# Allowing development environment mode\n\
DEV_MODE=true\n\
# Superset Admin credentials\n\
ADMIN_USER=mca-adm29\n\
ADMIN_EMAIL=mca.admin@superset.com\n\
ADMIN_FIRSTNAME=Mattheo\n\
ADMIN_LASTNAME=Polnareff\n\
# Superset metadata postgres database configurations\n\
SUPERSET_DATABASE_DB=superset\n\
SUPERSET_DATABASE_HOST=superset-metadata-db\n\
DATABASE_USER=superset\n\
# Cypress example DB credentials\n\
EXAMPLES_DB=examples\n\
EXAMPLES_HOST=superset-metadata-db\n\
EXAMPLES_USER=examples\n\
# Make sure you set this to a unique secure random value on production\n\
EXAMPLES_PASSWORD=examples\n\
EXAMPLES_PORT=5432\n\
# database engine specific environment variables\n\
# change the below if you prefer another database engine\n\
DATABASE_PORT=5432\n\
DATABASE_DIALECT=postgresql\n\
\n\
# Add the mapped in /app/pythonpath_docker which allows devs to override stuff\n\
PYTHONPATH=/app/pythonpath:/app/docker/pythonpath_dev\n\
REDIS_HOST=superset-cache-database\n\
REDIS_PORT=6379\n\
\n\
FLASK_DEBUG=true\n\
SUPERSET_ENV=development\n\
SUPERSET_LOAD_EXAMPLES=no\n\
CYPRESS_CONFIG=false\n\
SUPERSET_PORT=8088\n\
MAPBOX_API_KEY=''\n\
\n\
# Make sure you set this to a unique secure random value on production\n\
SUPERSET_SECRET_KEY=TEST_NON_DEV_SECRET\n\
\n\
ENABLE_PLAYWRIGHT=false\n\
PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true\n\
BUILD_SUPERSET_FRONTEND_IN_DOCKER=true\n\
SUPERSET_LOG_LEVEL=info" > ./superset-volumes/superset_core_variables.env
	@echo "Successfully done"


dotenv: ## Generates the project's .env file blueprint
	@echo "Creation of a new main '.env' file blueprint"
	@echo "# ==================================== DATA ORCHESTRATION COMPONENTS ENVIRONMENT VARIABLES ====================================\n\
#Base path to which all the files will be volumed | Default: .\n\
AIRFLOW_PROJ_DIR=./airflow-volumes\n\
#User ID in Airflow containers. Automatically generated through the command \"id -u\" when running the commande \"make dotenv\"  | Default: 50000\n\
AIRFLOW_UID=$$(id -u)\n\
#Path to the local directory where raw json files will be uploaded for ingestion in the Bronze bucket. Mount as a volume to "/opt/airflow/local-data" internal directory inside airflow containers\n\
LOCAL_DATA_DIR=./data\n\
# Exposed port for Airflow's Postgres metadata database\n\
AIRFLOW_POSTGRES_PORT=5432\n\
\n\
# ==================================== DATA STORAGE COMPONENTS ENVIRONMENT VARIABLES ====================================\n\
#Base path to which all the files will be volumed\n\
MINIO_PROJ_DIR=./minio-volumes\n\
# Exposed port for MinIO's API\n\
MINIO_API_PORT=9008\n\
# Exposed port for MinIO's web console\n\
MINIO_CONSOLE_PORT=9009\n\
\n\
# ==================================== BI COMPONENTS ENVIRONMENT VARIABLES ====================================\n\
# Apache Superset docker image's version used\n\
SUPERSET_IMAGE_TAG=6.0.0\n\
# Exposed port for Superset's Postgres metadata database\n\
DATABASE_PORT=5432\n\
# Exposed port for Superset's Redis cache database\n\
REDIS_PORT=6379" > .env
	@echo "Successfully done"