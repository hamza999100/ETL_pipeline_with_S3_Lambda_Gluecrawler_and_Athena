-- All queries run against the Glue Data Catalog database "etl_pipeline"

-- 1. Preview
SELECT * FROM "etl_pipeline"."orders_parquet_datalake" LIMIT 10;

-- 2. Filter by product OR customer
SELECT *
FROM "etl_pipeline"."orders_parquet_datalake"
WHERE product_name = 'Wireless Mouse'
   OR customer_name IN ('Hamza Nisar', 'Ali Khan');

-- 3. Exclude specific customers (Athena cannot DELETE from plain Parquet tables)
SELECT *
FROM "etl_pipeline"."orders_parquet_datalake"
WHERE customer_name NOT IN ('Hamza Nisar', 'Ali Khan', 'Shakeel', 'Panda')
   OR customer_name IS NULL;

-- 4. Revenue by category
SELECT category,
       SUM(price * quantity) AS revenue,
       COUNT(DISTINCT order_id) AS orders
FROM "etl_pipeline"."orders_parquet_datalake"
GROUP BY category
ORDER BY revenue DESC;

-- 5. Top products by units sold
SELECT product_name, SUM(quantity) AS units_sold
FROM "etl_pipeline"."orders_parquet_datalake"
GROUP BY product_name
ORDER BY units_sold DESC;

-- 6. Cleaned copy of the table (CTAS)
CREATE TABLE etl_pipeline.orders_clean
WITH (format = 'PARQUET',
      external_location = 's3://<your-bucket>/orders_clean/')
AS
SELECT *
FROM etl_pipeline.orders_parquet_datalake
WHERE customer_name NOT IN ('Hamza Nisar', 'Ali Khan', 'Shakeel', 'Panda')
   OR customer_name IS NULL;
