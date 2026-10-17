# Serverless ETL Pipeline on AWS (S3 → Lambda → Parquet → Glue → Athena)

An event-driven pipeline that ingests nested JSON order data, flattens and cleans it, stores it as Parquet in an S3 data lake, and makes it queryable with SQL in Amazon Athena. No servers to manage, and near-zero cost at small scale.

![Architecture](images/architecture.png)

## How it works

1. **Ingest:** a JSON file of orders is uploaded to an S3 bucket.
2. **Transform (AWS Lambda, Python + pandas):** an S3 event triggers the function, which
   - flattens nested `order → customer → products` JSON into one row per product,
   - drops rows with a missing or blank `product_name`,
   - enforces consistent column types, so every Parquet file matches the table schema,
   - writes a timestamped Parquet file to `orders_parquet_datalake/`.
3. **Catalog (AWS Glue):** a Glue Crawler ran **once** to create the table schema in the Glue Data Catalog.
4. **Query (Amazon Athena):** SQL runs directly on the Parquet files in S3. New incremental files show up immediately, with no re-crawl needed.

## My additions beyond the tutorial

- **Data-quality rules** in the Lambda (missing-value handling, type casting, row-count logging to CloudWatch).
- **Removed the Glue Crawler from the automated flow.** The schema is stable and the table points at the folder, so new files are read at query time. This saves about $0.15 per upload.
- **Debugged a schema-drift failure** (`HIVE_BAD_DATA: BINARY incompatible with bigint`) caused by inconsistent Parquet column types, and fixed it with explicit type enforcement.
- Cost analysis of each service, and the limits of Parquet tables (no `DELETE`; Apache Iceberg as the next step).

## Repository structure

```
lambda/lambda_function.py   # transform logic (flatten, clean, write Parquet)
sql/athena_queries.sql      # analysis queries
sample_data/                # example input JSON
images/                     # architecture diagram & screenshots
```

## Tech stack

AWS S3 · AWS Lambda (Python, pandas, pyarrow) · AWS Glue Data Catalog & Crawler · Amazon Athena · Amazon CloudWatch · IAM

## Cost

| Service | Usage in this project | Approx. cost |
|---|---|---|
| S3 | a few MB | < $0.01 |
| Lambda | a few invocations | free tier |
| Glue Crawler | 1 run (10-min minimum × 2 DPU) | about $0.15 |
| Athena | $5/TB scanned, 10 MB minimum per query | < $0.01 |

## Key learnings

- Athena is a schema-on-read engine. It needs table metadata from the Glue Data Catalog, but it reads the actual files at query time.
- Every Parquet file under a table's location must match the table schema, or all queries on the table fail.
- Plain Parquet tables are append-only from Athena's point of view; row-level deletes need a table format like **Apache Iceberg**.

## Acknowledgements

Based on the tutorial [AWS ETL Pipeline Project For Beginners](https://www.youtube.com/watch?v=yHHCV3Q13Fo) by **Ankit Bansal**, extended with the changes listed above.
