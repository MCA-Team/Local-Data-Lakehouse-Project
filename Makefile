.PHONY: help create-binded-volumes dotenv setup-infra shutdown-infra
.DEFAULT_GOAL = help


help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-24s\033[0m %s\n", $$1, $$2}'

create-binded-volumes: ## Automatically create the containers binded volumes
	@for directory_name in "airflow-volumes/dags" \
							"airflow-volumes/logs" \
							"airflow-volumes/config" \
							"airflow-volumes/plugins" \
							"airflow-volumes/postgresql-volume" \
							"minio-volumes/data" \
							"minio-volumes/certs"; \
	do \
		if [ ! -d "$$directory_name" ]; then \
			echo "Creation of $$directory_name directory"; \
			mkdir -p $$directory_name; \
			echo "Successfully done"; \
		else \
			echo "$$directory_name directory already exists"; \
		fi \
	done
	
	
setup-infra: ## Automatically set up the infra by creating the containers, the volumes and the network(s)
	@docker compose -f docker-compose.yaml up -d
	@echo "Wait a moment...\n"
	@sleep 5
	@docker compose rm -f superset-init minio-create-buckets
	@echo "Infrastructure successfully set up !"

shutdown-infra:	## Automatically shutdown the infra removing the containers and the network(s)
	@docker compose down

create-docker-secrets:
	@if [ ! -d "docker-secrets" ]; then\
		mkdir ./docker-secrets;\
	fi

	@touch ./docker-secrets/airflow_sql_alchemy_connection_string.secrets\ 
		  ./docker-secrets/aiflow_www_user_password.secrets\
		  ./docker-secrets/aiflow_postgres_password.secrets \
		  ./docker-secrets/ 
	@echo "postgresql+psycopg2://<AIRFLOW_POSTGRES_USER>:$<AIRFLOW_POSTGRES_PASSWORD>@airflow-postgres/<AIRFLOW_POSTGRES_DB>" >> ./docker-secrets/airflow_sql_alchemy_connection_string.secrets
	@echo "Docker secrets successfully created !"


dotenv: ## Generate the project .env file blueprint
	@echo "Creation of a new '.env' file blueprint"
	@echo "AIRFLOW_UID=1000\n\
AIRFLOW_PROJ_DIR=./airflow-volumes\n\
LOCAL_DATA_DIR=./data\n\
# AIRFLOW WEBSERVER CREDENTIALS\n\
_AIRFLOW_WWW_USER_USERNAME=\n\
_AIRFLOW_WWW_USER_PASSWORD=\n\
# POSTGRES DATABASE CREDENTIALS\n\
AIRFLOW_POSTGRES_USER=\n\
AIRFLOW_POSTGRES_PASSWORD=\n\
AIRFLOW_POSTGRES_DB=airflow\n\
AIRFLOW_POSTGRES_PORT=5432\n\
#MINIO AISTOR CREDENTIALS (ROOT_USER >= 3 CHARACTERS, ROOT_PASSWORD >= 8 CHARACTERS)\n\
MINIO_ROOT_USER=\n\
MINIO_ROOT_PASSWORD=\n\
# MINIO PORTS AND BUCKETS NAME\n\
MINIO_API_PORT=9008\n\
MINIO_CONSOLE_PORT=9009\n\
MINIO_BRONZE_BUCKET_NAME=bronze\n\
MINIO_SILVER_BUCKET_NAME=silver\n\
MINIO_GOLD_BUCKET_NAME=gold\n\
\n\
\n\
#\n\
# Licensed to the Apache Software Foundation (ASF) under one or more\n\
# contributor license agreements.  See the NOTICE file distributed with\n\
# this work for additional information regarding copyright ownership.\n\
# The ASF licenses this file to You under the Apache License, Version 2.0\n\
# (the "License"); you may not use this file except in compliance with\n\
# the License.  You may obtain a copy of the License at\n\
#\n\
#    http://www.apache.org/licenses/LICENSE-2.0\n\
#\n\
# Unless required by applicable law or agreed to in writing, software\n\
# distributed under the License is distributed on an "AS IS" BASIS,\n\
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.\n\
# See the License for the specific language governing permissions and\n\
# limitations under the License.\n\
#\n\
\n\
# Allowing python to print() in docker\n\
PYTHONUNBUFFERED=1\n\
\n\
COMPOSE_PROJECT_NAME=local-data-lakehouse-project\n\
DEV_MODE=true\n\
\n\
# database configurations (do not modify)\n\
SUPERSET_DATABASE_DB=superset\n\
SUPERSET_DATABASE_HOST=superset-metadata-pgsql\n\
# Make sure you set this to a unique secure random value on production\n\
DATABASE_PASSWORD=superset\n\
DATABASE_USER=superset\n\
\n\
EXAMPLES_DB=examples\n\
EXAMPLES_HOST=superset-metadata-pgsql\n\
EXAMPLES_USER=examples\n\
# Make sure you set this to a unique secure random value on production\n\
EXAMPLES_PASSWORD=examples\n\
EXAMPLES_PORT=5432\n\
\n\
# database engine specific environment variables\n\
# change the below if you prefer another database engine\n\
DATABASE_PORT=5432\n\
DATABASE_DIALECT=postgresql\n\
SUPERSET_POSTGRES_DB=superset\n\
SUPERSET_POSTGRES_USER=superset\n\
# Make sure you set this to a unique secure random value on production\n\
SUPERSET_POSTGRES_PASSWORD=superset\n\
#MYSQL_DATABASE=superset\n\
#MYSQL_USER=superset\n\
#MYSQL_PASSWORD=superset\n\
#MYSQL_RANDOM_ROOT_PASSWORD=yes\n\
\n\
# Add the mapped in /app/pythonpath_docker which allows devs to override stuff\n\
PYTHONPATH=/app/pythonpath:/app/apache-superset-files/pythonpath_dev\n\
REDIS_HOST=redis\n\
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
SUPERSET_LOG_LEVEL=info" > t.env
	@echo "Successfully done"