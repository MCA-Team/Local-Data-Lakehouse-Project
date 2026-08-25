# MinIO

[MinIO](https://min.io) is a High Performance Object Storage. It is API compatible
with Amazon S3 cloud storage service. Use MinIO to build high performance infrastructure for machine learning, analytics
and application data workloads.

For more detailed documentation please visit [here](https://docs.minio.io/)

Introduction
------------

This chart bootstraps MinIO Object Store on a [Kubernetes](http://kubernetes.io) cluster using the [Helm](https://helm.sh) package manager.

Configure MinIO Helm repo
--------------------

```bash
helm repo add minio https://helm.min.io/
```

Creating an Object Store with Helm Chart
-----------------

Once the [AIStor Operator Chart](https://github.com/miniohq/aistor-operator/tree/master/helm/operator) is successfully installed, create a MinIO Object Store using:

```bash
helm install --namespace myminio-ns \
  --create-namespace my-minio minio/object-store
```

This creates a 4 Node MinIO Object Store (cluster). To change the default values, take a look at various [values.yaml](https://github.com/miniohq/aistor-operator/blob/master/helm/object-store/values.yaml).
