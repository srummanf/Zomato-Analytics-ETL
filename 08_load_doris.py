"""Step 8: Load to Warehouse — copy the dbt-built star schema from Postgres
into Apache Doris, the analytics warehouse that actually serves BI queries.

For each table: exports it from Postgres with COPY (fast, streams straight
to a temp file, same approach as load_postgres.py's bulk load) and ingests
it into Doris with Stream Load (Doris's bulk-ingest HTTP API — row-by-row
INSERT is an anti-pattern for an OLAP engine like Doris). Each table is
dropped and recreated on every run, mirroring load_postgres.py's full-reload
ELT approach.
"""
import os
import tempfile
import time
from pathlib import Path

import psycopg2
import pymysql
import requests
from dotenv import load_dotenv

load_dotenv()

PG_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": os.getenv("POSTGRES_PORT", "5439"),
    "dbname": os.getenv("POSTGRES_DB", "zomato"),
    "user": os.getenv("POSTGRES_USER", "zomato"),
    "password": os.getenv("POSTGRES_PASSWORD", "zomato"),
}

DORIS_HOST = os.getenv("DORIS_HOST", "localhost")
DORIS_QUERY_PORT = int(os.getenv("DORIS_QUERY_PORT", "9030"))
DORIS_STREAM_LOAD_PORT = os.getenv("DORIS_STREAM_LOAD_PORT", "8040")
DORIS_DB = os.getenv("DORIS_DB", "zomato")
DORIS_USER = os.getenv("DORIS_USER", "root")
DORIS_PASSWORD = os.getenv("DORIS_PASSWORD", "")

# doris table -> (source Postgres table, CREATE TABLE column defs, key column(s), bucket count)
TABLES = {
    "dim_location": (
        "dim_location",
        "location_id INT, area VARCHAR(255)",
        "location_id", 1,
    ),
    "dim_cuisine": (
        "dim_cuisine",
        "cuisine_id INT, cuisine VARCHAR(100)",
        "cuisine_id", 1,
    ),
    "dim_restaurant": (
        "dim_restaurant",
        """restaurant_id INT, restaurant_name STRING, url STRING, address STRING,
        location_id INT, restaurant_type VARCHAR(100), meal_type VARCHAR(100), rating DOUBLE,
        vote_count INT, avg_cost_for_two DOUBLE, online_order_enabled BOOLEAN,
        table_booking_enabled BOOLEAN""",
        "restaurant_id", 3,
    ),
    "bridge_restaurant_cuisine": (
        "bridge_restaurant_cuisine",
        "restaurant_id INT, cuisine_id INT",
        "restaurant_id, cuisine_id", 3,
    ),
    "dim_customer": (
        "dim_customer",
        """customer_id VARCHAR(64), name VARCHAR(255), email VARCHAR(255), phone VARCHAR(50),
        signup_date DATE, customer_order_count INT""",
        "customer_id", 1,
    ),
    "dim_delivery_partner": (
        "dim_delivery_partner",
        "delivery_partner_id VARCHAR(64), delivery_partner_name VARCHAR(255)",
        "delivery_partner_id", 1,
    ),
    "dim_date": (
        "dim_date",
        """date_id DATE, full_date DATE, year INT, quarter INT, month INT, month_name VARCHAR(20),
        day INT, day_of_week INT, day_name VARCHAR(20), is_weekend BOOLEAN""",
        "date_id", 1,
    ),
    "dim_time": (
        "dim_time",
        "hour_id INT, hour_of_day INT, time_period VARCHAR(30)",
        "hour_id", 1,
    ),
    "fact_orders": (
        "fact_orders",
        """order_id VARCHAR(64), customer_id VARCHAR(64), restaurant_id INT, location_id INT,
        date_id DATE, hour_id INT, party_size INT, order_total DOUBLE, order_status VARCHAR(50)""",
        "order_id", 3,
    ),
    "fact_order_items": (
        "fact_order_items",
        "order_item_id VARCHAR(64), order_id VARCHAR(64), item_name VARCHAR(255), item_price DOUBLE",
        "order_item_id", 3,
    ),
    "fact_deliveries": (
        "fact_deliveries",
        """delivery_id VARCHAR(64), order_id VARCHAR(64), delivery_partner_id VARCHAR(64),
        delivery_time_minutes INT, delivery_status VARCHAR(50)""",
        "delivery_id", 3,
    ),
    "fact_payments": (
        "fact_payments",
        """payment_id VARCHAR(64), order_id VARCHAR(64), payment_method VARCHAR(50),
        amount DOUBLE, payment_status VARCHAR(50)""",
        "payment_id", 3,
    ),
    "fact_reviews": (
        "fact_reviews",
        "review_id BIGINT, restaurant_id INT, review_rating DOUBLE, review_text STRING",
        "review_id", 3,
    ),
}


def export_from_postgres(pg_cur, source_table, tmp_path):
    with open(tmp_path, "w", newline="", encoding="utf-8") as f:
        pg_cur.copy_expert(
            f"COPY {source_table} TO STDOUT WITH (FORMAT csv, NULL '\\N')", f
        )


def create_doris_table(doris_cur, table_name, columns_sql, key_columns, buckets):
    doris_cur.execute(f"DROP TABLE IF EXISTS {table_name}")
    doris_cur.execute(f"""
        CREATE TABLE {table_name} ({columns_sql})
        DUPLICATE KEY({key_columns})
        DISTRIBUTED BY HASH({key_columns.split(',')[0].strip()}) BUCKETS {buckets}
        PROPERTIES ("replication_num" = "1")
    """)


def stream_load(table_name, tmp_path):
    url = f"http://{DORIS_HOST}:{DORIS_STREAM_LOAD_PORT}/api/{DORIS_DB}/{table_name}/_stream_load"
    with open(tmp_path, "rb") as f:
        resp = requests.put(
            url,
            data=f,
            auth=(DORIS_USER, DORIS_PASSWORD),
            headers={
                "Expect": "100-continue",
                "format": "csv",
                "column_separator": ",",
                "enclose": '"',
                "label": f"{table_name}_{int(time.time() * 1000)}",
            },
        )
    result = resp.json()
    if result.get("Status") not in ("Success", "Publish Timeout"):
        raise RuntimeError(f"Stream load failed for {table_name}: {result}")
    return result.get("NumberLoadedRows", 0)


def main():
    pg_conn = psycopg2.connect(**PG_CONFIG)
    doris_conn = pymysql.connect(
        host=DORIS_HOST, port=DORIS_QUERY_PORT, user=DORIS_USER, password=DORIS_PASSWORD,
        autocommit=True,
    )
    try:
        with doris_conn.cursor() as doris_cur:
            doris_cur.execute(f"CREATE DATABASE IF NOT EXISTS {DORIS_DB}")
            doris_cur.execute(f"USE {DORIS_DB}")

            with pg_conn.cursor() as pg_cur:
                for table_name, (source_table, columns_sql, key_columns, buckets) in TABLES.items():
                    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
                        tmp_path = tmp.name
                    try:
                        export_from_postgres(pg_cur, source_table, tmp_path)
                        create_doris_table(doris_cur, table_name, columns_sql, key_columns, buckets)
                        loaded = stream_load(table_name, tmp_path)
                        print(f"{table_name}: {loaded} rows loaded from {source_table}")
                    finally:
                        Path(tmp_path).unlink(missing_ok=True)
    finally:
        pg_conn.close()
        doris_conn.close()


if __name__ == "__main__":
    main()
