.PHONY: help add-helm-repos install-minio-charts install-trino-charts install-hue-modified-charts uninstall-minio-charts install-trino-charts uninstall-hue-modified-charts
.DEFAULT_GOAL = help


help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

add-helm-repos: ## Adds all required Helm repos (MinIO AIStor, Trino, ...)
	@echo "============ Adding Minio AIStor Helm repo ============"
	@helm repo add minio https://helm.min.io/
	@echo "\n============ Adding Trino Helm repo ============"
	@helm repo add trino https://trinodb.github.io/charts
	@echo "\n============ Adding Hue Helm repo ============"
	@helm repo add gethue https://helm.gethue.com

install-minio-charts: ## Automatically installs MinIO AIStor charts (aistor-operator and aistor-objectstore charts) and deploy a server
	@echo "=========== Installation of aistor-operator charts ==========="
	@helm install minio-operator minio/aistor-operator --set license="xxxxxx"
	@sleep 2
	@echo "=========== Done ! ===========\n"
	
	@echo "=========== Installation of aistor-objectstore charts ==========="
	@helm install minio-objectstore minio/aistor-objectstore -f aistor-objectstore-values.yaml
	@sleep 2
	@echo "=========== Done ! ===========\n"

uninstall-minio-charts: ## Automatically uninstalls MinIO AIStor charts
	@echo "=========== Uninstallation of aistor-objectstore charts ==========="
	@helm uninstall minio-objectstore
	@sleep 2
	@echo "=========== Done ! ===========\n"
	
	@echo "=========== Uninstallation of aistor-operator charts ==========="
	@helm uninstall minio-operator
	@sleep 2
	@echo "=========== Done ! ===========\n"

install-trino-charts: ## Automatically installs Trino charts
	@echo "=========== Installation of trino/trino charts ==========="
	helm install trino trino/trino -f trino-values.yaml
	@sleep 2
	@echo "=========== Done ! ===========\n"

uninstall-trino-charts: ## Automatically uninstalls Trino charts
	@echo "=========== Uninstallation of trino/trino charts ==========="
	helm uninstall trino
	@sleep 2
	@echo "=========== Done ! ===========\n"

install-hue-modified-charts: ## Automatically installs Hue modified charts within the 'hue-helm-chart-modified' directory
	@echo "=========== Installation of Hue modified charts ==========="
	helm install hue hue-helm-chart-modified/ -f hue-values.yaml
	@sleep 2
	@echo "=========== Done ! ===========\n"

uninstall-hue-modified-charts: ## Automatically uninstalls Hue modified charts
	@echo "=========== Uninstallation of Hue modified charts ==========="
	helm uninstall hue
	@sleep 2
	@echo "=========== Done ! ===========\n"
