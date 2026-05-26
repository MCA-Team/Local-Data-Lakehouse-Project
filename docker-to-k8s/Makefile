.PHONY: help add-helm-repos install-minio-charts install-trino-charts
.DEFAULT_GOAL = help


help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-24s\033[0m %s\n", $$1, $$2}'

add-helm-repos: ## Adds all required Helm repos (MinIO AIStor, Trino, ...)
	@echo "============ Adding Minio AIStor Helm repo ============"
	@helm repo add minio https://helm.min.io/
	@echo "\n============ Adding Trino Helm repo ============"
	@helm repo add trino https://trinodb.github.io/charts
	@echo "\n============ Adding Hue Helm repo ============"
	@helm repo add gethue https://helm.gethue.com

install-minio-charts: ## Automatically installs MinIO AIStor charts (aistor-operator and aistor-objectstore charts) and deploy a server
	@echo "=========== Installation of aistor-operator chart ==========="
	@helm install minio-operator minio/aistor-operator --set license="xxxxx-xxxx-xxxx-xxxx"
	@sleep 2
	@echo "=========== Done ! ===========\n"
	
	@echo "=========== Installation of aistor-objectstore chart ==========="
	@helm install minio-objectstore minio/aistor-objectstore -f aistor-objectstore-values.yaml
	@sleep 2
	@echo "=========== Done ! ===========\n"

uninstall-minio-charts: ## Automatically uninstalls MinIO AIStor charts (aistor-operator and aistor-objectstore charts) and deploy a server
	@echo "=========== Uninstallation of aistor-objectstore chart ==========="
	@helm uninstall minio-objectstore
	@sleep 2
	@echo "=========== Done ! ===========\n"
	
	@echo "=========== Uninstallation of aistor-operator chart ==========="
	@helm uninstall minio-operator
	@sleep 2
	@echo "=========== Done ! ===========\n"

install-trino-charts: ## Automatically installs MinIO AIStor charts (aistor-operator and aistor-objectstore charts) and deploy a server
	@echo "=========== Installation of trino/trino chart ==========="
	helm install trino trino/trino -f trino-values.yaml
	@sleep 2
	@echo "=========== Done ! ===========\n"

uninstall-trino-charts: ## Automatically installs MinIO AIStor charts (aistor-operator and aistor-objectstore charts) and deploy a server
	@echo "=========== Uninstallation of trino/trino chart ==========="
	helm uninstall trino
	@sleep 2
	@echo "=========== Done ! ===========\n"


