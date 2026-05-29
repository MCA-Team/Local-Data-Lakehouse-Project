# From docker-compose to Kubernetes deployment

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

- **MinIO AIStor**
- **Trino**
- **Hue**
- **Apache Superset**

First of all, add all required Helm CHart repo through the following command:

```bash
make add-helm-repos 
```

Check the added repo with the following command:

```
helm search repo
```
    
## MinIO AIStor

The `minio/aistor-operator` chart contains the necessary Kubernetes resources for deploying MinIO AIStor Server resources through the `minio/aistor-objectstore` chart. Before installing the `minio/aistor-operator` chart, make sure you have the `minio.license` file within the `../minio-volumes` directory. After that, tweak the `aistor-objectstore-values.yaml` file in order to customize your MinIO AIStor deployment (a full version of `aistor-objectstore-values.yaml` file is available in the `values-templates/aistor-objectstore-template-values.yaml` file). The following command deploys an MinIO AIStor with the name of **minio-object-store** :

```bash
make install-minio-charts
```

## Trino

Tweak the `trino-values.yaml` file in order to customize your Trino deployment (a full version of `trino-values.yaml` file is available in the `values-templates/trino-template-values.yaml` file). The following command deploys a Trino server with the name of **trino** :

```bash
make install-trino-charts
```

Make sure everything is running well.

## Hue

Hue Helm chart needed a customization in order to fulfill our project requirements and constraints. So a modified version (hue-helm-chart-modified/) is the one we will use for the Kubernetes deployment. Then, no need to pull a remote repo.
Tweak the `hue-values.yaml` file in order to customize your Hue deployment (a full version of `hue-values.yaml` file is available in the `values-templates/hue-template-values.yaml` file). The following command deploys a Hue server with the name of **hue** :

```bash
make install-hue-modified-charts
```

Make sure everything is running well.

## Apache Superset


## Web UI addresses
We are using Minikube as a Kubernetes cluster. Some services are exposed through a nodePort. Here are the main containers Web UI addresses:

Here are the main containers Web UI addresses:
Address     | Container/service
----------- | ---------
http://{kubernetes-cluster-ip-address}:31000 | MinIO AIStor Console UI
http://{kubernetes-cluster-ip-address}:31205 | Trino Web UI
http://{kubernetes-cluster-ip-address}:31300 | Hue Web UI

## Uninstall the charts

- MinIO charts
```bash
make uninstall-minio-charts
```

- Trino charts
```bash
make uninstall-trino-charts
```

- Hue charts
```bash
make uninstall-hue-modified-charts
```



# Troubleshooting


# Resources

Helm docs: [click here](https://helm.sh/docs)

Kubernetes docs: [click here](https://kubernetes.io/docs/home/)