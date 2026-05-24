# From docker-compose to Kubernetes depployment

<image src="../doc/migration.png" width=1000 center>

[<img src="https://img.shields.io/badge/Helm-v3.20.0-blue.svg?logo=helm   ">](https://helm.sh/docs)
[<img src="https://img.shields.io/badge/Kubernetes-cyan.svg?logo=kubernetes">](https://kubernetes.io/docs/home/) 
[<img src="https://img.shields.io/badge/kubectl-2.10.5-blue.svg?logo=kubernetes">](https://kubernetes.io/fr/docs/tasks/tools/install-kubectl/) 
[<img src="https://img.shields.io/badge/Minikube-v1.36.0-cyan.svg?logo=kubernetes">](https://minikube.sigs.k8s.io/docs/)

## Table of contents
[Overiew](#overiew)

[Prerequisites](#prerequisites)

[Setting up](#setting-up)



[Troubleshooting](#troubleshooting)

[Resources](#resources)

---

# Overview
This section is oriented on moving the architecture to the next level: **the Production**. With the `docker-compose.yaml` file, the architecture runs on development mode without scalability, fault tolerance, strong credentials confidentiality,... By bringing the architecture to a Kubernetes cluster, we end up with latter problems.

# Prerequisites
For this migration, the following tools are required:
- **A kubernetes Cluster**: where the architecture will be orchestrated and managed.

> [!NOTE]
> For simplicity, we use Minikube which is a local single node Kubernetes cluster.

- **kubectl**: It's the Kubernetes CLI which allows a client to interact with the Kubernetes cluster (create pods, create deployments...)
- **Helm**: It is the package manager for Kubernetes.

# Setting up
We have to deploy each architecture component one ny one. They are:
- **[-] MinIO AIStor**
- **[] Trino**
- **[] Hue**
- **[] Superset**

    ## MinIO AIStor
    1. Let's add MinIO AIStor's Helm repo
    ```bash
    helm repo add minio https://helm.min.io/
    ```

    2. The `minio/aistor-operator` chart contains the necessary Kubernetes resources for deploying MinIO AIStor Server resources through the `minio/aistor-objectstore` chart. Let's install the `minio/aistor-operator` chart (replace **'xxxxx'** by the content of the `minio.license` file):
    ```bash
    helm install aistor minio/aistor-operator --set license="xxxxx"
    ```

    3. Make sure everything is running well. Then, tweak the `aistor-objectstore-values.yaml` file in order to customize your MinIO AIStor deployment (a full version of `aistor-objectstore-values.yaml` file is available in the `values-templates/aistor-objectstore-template-values.yaml` file). The following command deploys an MinIO AIStor with the name of **minio-object-store** :
    ```bash
    helm install minio-object-store minio/aistor-objectstore -f aistor-objectstore-values.yaml
    ```

    ## Trino
    1. Let's add Trino's Helm repo
    ```bash
    helm repo add trino https://trinodb.github.io/charts
    ```
    2. Then, tweak the `trino-values.yaml` file in order to customize your Trino deployment (a full version of `trino-values.yaml` file is available in the `values-templates/trino-template-values.yaml` file). The following command deploys a Trino with the name of **trino** :
    ```bash
    helm install trino trino/trino -f trino-values.yaml
    ```
    Make sure everything is running well.




# Troubleshooting


# Resources

Helm docs: [click here](https://helm.sh/docs)

Kubernetes docs: [click here](https://kubernetes.io/docs/home/)