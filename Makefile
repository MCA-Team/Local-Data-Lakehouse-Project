.PHONY: help init dotenv
.DEFAULT_GOAL = help


help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

init: ## Automatically initialize the project
	@echo "Creation of airflow volumes directories"
	@mkdir airflow-volumes
	@mkdir -p airflow-volumes/dags airflow-volumes/logs airflow-volumes/config airflow-volumes/plugins airflow-volumes/postgresql-volume
	@echo "Successfully done"
	@echo "Creation of MinIO volume directory (data and certs directories)"
	@mkdir -p minio-volumes/data minio-volumes/certs
	@echo "Successfully done"



dotenv: ## Generate the project .env file blueprint
	@echo "Creation of .env file blueprint"
	@echo "AIRFLOW_UID=\nAIRFLOW_PROJ_DIR=./airflow-volumes\n# AIRFLOW WEBSERVER CREDENTIALS\n_AIRFLOW_WWW_USER_USERNAME=\n_AIRFLOW_WWW_USER_PASSWORD=\n# POSTGRES DATABASE CREDENTIALS\nPOSTGRES_USER=\nPOSTGRES_PASSWORD=\n#MINIO AISTOR CREDENTIALS (ROOT_USER >= 3 CHARACTERS, ROOT_PASSWORD >= 8 CHARACTERS)\nMINIO_ROOT_USER=\nMINIO_ROOT_PASSWORD=" > .env
	@echo "Successfully done"