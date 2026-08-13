# ============================================================================================================================================
# This file contains commonly used commands for working with Helm and Kubernetes in the context of the Local Data Lakehouse Project. 
# It serves as a reference for adding Helm repositories, installing and managing Helm charts, and other related tasks.
# Note: Replace placeholders (e.g., <helm-chart-repo-name>, <release-name>, etc.) with actual values when executing the commands.
# =============================================================================================================================================

#====================================
# HELM SPECIFIC REPOSITORIES COMMANDS
#====================================
# Add MinIO AIStor Helm repo
helm repo add minio https://helm.min.io/

# Add Trino Helm repo
helm repo add trino https://trinodb.github.io/charts

# Add Hue repo
helm repo add gethue https://helm.gethue.com

# Add Superset repo
helm repo add superset https://apache.github.io/superset



#====================================
# UTILITIES
#====================================
# Get the Helm Chart values to configure
helm show values <helm-chart-repo-name> > <helm-chart-name>-values.yaml

# Get the Helm Charts underneath a repo
helm template <helm-chart-repo-name> --output-dir <output-directory>

# Search a Helm Chart repo
helm search repo <helm-chart-repo-name>

# Install a Helm Chart with custom values
helm install <release-name> <helm-chart-repo-name> -f <helm-chart-values-file.yaml>

# Uninstall a Helm release
helm uninstall <release-name>

# Upgrade a Helm release with new values
helm upgrade <release-name> <helm-chart-repo-name> -f <updated-helm-chart-values-file.yaml>

# Show all added Helm Chart repo
helm search repo

# Show all installed Helm Chart
helm list

# Pull a Chart to targ.gz format
helm pull <repo>/<chart>

# Package a helm chart to a tgz format
helm package <repo>/chart --destination <destination_directory>

# Get Kubernetes PVs and PVCs
kubectl get pv
kubectl get pvc