.PHONY: help


help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

install-argocd: ## Install ArgoCD Agent in your K8S cluster. This will create a new namespace, argocd, where Argo CD services and application resources will live.
	@echo "\nInstalling ArgoCD Agent...\n"
	@kubectl create namespace argocd
	@kubectl apply -n argocd --server-side --force-conflicts -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
	@echo "\n ArgoCD Agent added\n"

add-helm-repos: ## Adds all required Helm repos (MinIO AIStor, Trino, ...)
	@echo "============ Adding Minio AIStor Helm repo ============"
	@helm repo add minio https://helm.min.io/
	@echo "\n============ Adding Trino Helm repo ============"
	@helm repo add trino https://trinodb.github.io/charts
	@echo "\n============ Adding Apache Superset Helm repo ============"
	@helm repo add superset https://apache.github.io/superset

install-minio-operator-charts: ## Automatically installs MinIO AIStor Operator charts for Objectstore deployment
	@echo "=========== Installation of aistor-operator charts ==========="

	@helm install minio-operator minio/aistor-operator --set license=$$(cat ../minio-volumes/minio.license)
	@sleep 2
	@echo "=========== Done ! ===========\n"
	
install-minio-objectstore-charts: ## Automatically installs MinIO AIStor Objectstore charts and deploy a server
	@echo "=========== Installation of aistor-objectstore charts ==========="
	@helm install minio-objectstore minio/aistor-objectstore -f aistor-objectstore-values.yaml
	@sleep 2
	@echo "=========== Done ! ===========\n"

uninstall-minio-charts: ## Automatically uninstalls MinIO AIStor helm release (aistor-operator and aistor-objectstore charts)
	@echo "=========== Uninstallation of aistor-objectstore helm release ==========="
	@helm uninstall minio-objectstore
	@sleep 2
	@echo "=========== Done ! ===========\n"
	
	@echo "=========== Uninstallation of aistor-operator helm release ==========="
	@helm uninstall minio-operator
	@sleep 2
	@echo "=========== Done ! ===========\n"

install-trino-charts: ## Automatically installs Trino charts
	@echo "=========== Installation of trino/trino charts ==========="
	@helm install trino trino/trino -f trino-values.yaml
	@sleep 2
	@echo "=========== Done ! ===========\n"

uninstall-trino-charts: ## Automatically uninstalls Trino helm release
	@echo "=========== Uninstallation of Trino helm release ==========="
	@helm uninstall trino
	@sleep 2
	@echo "=========== Done ! ===========\n"

install-hue-modified-charts: ## Automatically installs Hue modified charts within the 'hue-helm-chart-modified' directory
	@echo "=========== Installation of Hue modified charts ==========="
	@helm install hue hue-helm-chart-modified/ -f hue-values.yaml
	@sleep 2
	@echo "=========== Done ! ===========\n"

uninstall-hue-modified-charts: ## Automatically uninstalls Hue helm release
	@echo "=========== Uninstallation of Hue helm release ==========="
	@helm uninstall hue
	@sleep 2
	@echo "=========== Done ! ===========\n"

install-superset-charts: ## Automatically installs Superset charts
	@echo "=========== Installation of Superset charts ==========="
	@helm install superset superset/superset -f ./superset-values.yaml
	@sleep 2
	@echo "=========== Done ! ===========\n"

uninstall-superset-charts: ## Automatically uninstalls Superset helm release
	@echo "=========== Uninstallation of Superset helm release ==========="
	@helm uninstall superset
	@sleep 2
	@echo "=========== Done ! ===========\n"


