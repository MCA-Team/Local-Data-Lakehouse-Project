.PHONY: help 
		install-local-lakehouse-dev-stack
		uninstall-local-lakehouse-dev-stack


help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

install-local-lakehouse-dev-stack: ## Install local lakehouse development stack
	@echo "\nInstalling local lakehouse development stack...\n"
	@helm upgrade --install local-lakehouse-dev-stack ./dev -f dev/values.yaml

uninstall-local-lakehouse-dev-stack: ## Uninstall local lakehouse development stack
	@helm uninstall local-lakehouse-dev-stack