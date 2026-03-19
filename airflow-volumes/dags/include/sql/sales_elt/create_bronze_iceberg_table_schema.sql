CREATE SCHEMA IF NOT EXISTS minio_warehouse.{{ params.schema }}
WITH (location = 's3a://{{ params.warehouse_name }}/{{ params.schema }}')