import json
import boto3
import pandas as pd
import io
from datetime import datetime

s3 = boto3.client('s3')


def flatten(data):
    orders_data = []
    for order in data:
        customer = order.get("customer", {}) or {}
        for product in order.get("products", []) or []:
            row_orders = {
                "order_id": order.get("order_id"),
                "order_date": order.get("order_date"),
                "total_amount": order.get("total_amount"),
                "customer_id": customer.get("customer_id"),
                "customer_name": customer.get("name"),
                "email": customer.get("email"),
                "address": customer.get("address"),
                "product_id": product.get("product_id"),
                "product_name": product.get("name"),   # .get() -> None instead of KeyError
                "category": product.get("category"),
                "price": product.get("price"),
                "quantity": product.get("quantity"),
            }
            orders_data.append(row_orders)
    return pd.DataFrame(orders_data)


def clean(df):
    rows_before = len(df)

    # Rule: drop the row if product_name is missing (absent key, null, or empty/blank string)
    df["product_name"] = df["product_name"].astype("string").str.strip()
    df = df[df["product_name"].notna() & (df["product_name"] != "")]

    # Keep column types identical across every file, otherwise Athena can fail
    # with a type-mismatch error when it reads old + new Parquet files together.
    # Match these to the column types shown in your Glue table.
    df["order_id"] = pd.to_numeric(df["order_id"], errors="coerce").astype("Int64")       # bigint in Glue
    df["customer_id"] = pd.to_numeric(df["customer_id"], errors="coerce").astype("Int64") # bigint in Glue
    df = df.astype({
        "order_date": "string",
        "customer_name": "string",
        "email": "string",
        "address": "string",
        "product_id": "string",
        "category": "string",
    })
    df["total_amount"] = pd.to_numeric(df["total_amount"], errors="coerce").astype("float64")
    df["price"] = pd.to_numeric(df["price"], errors="coerce").astype("float64")
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").astype("Int64")

    print(f"Rows before: {rows_before}, after: {len(df)}, dropped: {rows_before - len(df)}")
    return df.reset_index(drop=True)


def lambda_handler(event, context):
    bucket_name = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']

    response = s3.get_object(Bucket=bucket_name, Key=key)
    data = json.loads(response['Body'].read().decode('utf-8'))

    df = clean(flatten(data))

    if df.empty:
        print(f"No valid rows in {key}, nothing written.")
        return {"statusCode": 200, "rows_written": 0}

    parquet_buffer = io.BytesIO()
    df.to_parquet(parquet_buffer, index=False, engine='pyarrow')

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    key_staging = f'orders_parquet_datalake/orders_ETL_{timestamp}.parquet'
    s3.put_object(Bucket=bucket_name, Key=key_staging, Body=parquet_buffer.getvalue())
    print(f"Wrote s3://{bucket_name}/{key_staging}")

    # Crawler removed: the Glue table already exists and points to the
    # orders_parquet_datalake/ folder, so Athena reads new files automatically.
    return {"statusCode": 200, "rows_written": len(df), "output": key_staging}
