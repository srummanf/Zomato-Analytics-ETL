"""Step 6: Load to Staging — bulk-load transform_data.py's clean_*.csv output
into PostgreSQL staging tables.

Reads each CSV with the stdlib csv module (handles the embedded
newlines/quotes in review text the same way pandas does) and inserts in
batches, so the full file is never held in memory at once. Each table is
dropped and recreated on every run, matching the ELT idea: staging always
mirrors the latest clean data; dbt (Step 7) does the durable modeling on
top of it.
"""
import csv
import glob
import os
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path(__file__).parent / "data"
BATCH_SIZE = 5000

PG_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": os.getenv("POSTGRES_PORT", "5439"),
    "dbname": os.getenv("POSTGRES_DB", "zomato"),
    "user": os.getenv("POSTGRES_USER", "zomato"),
    "password": os.getenv("POSTGRES_PASSWORD", "zomato"),
}

# table -> (source folder under data/, CREATE TABLE column definitions)
TABLES = {
    "stg_restaurants": ("clean_restaurants", """
        restaurant_id INTEGER PRIMARY KEY,
        restaurant_name TEXT,
        url TEXT,
        address TEXT,
        area TEXT,
        votes INTEGER,
        online_order_enabled BOOLEAN,
        table_booking_enabled BOOLEAN,
        restaurant_type TEXT,
        avg_cost_for_two NUMERIC,
        meal_type TEXT,
        rating NUMERIC
    """),
    "stg_restaurant_cuisines": ("clean_restaurant_cuisines", """
        restaurant_id INTEGER,
        cuisine TEXT
    """),
    "stg_restaurant_reviews": ("clean_restaurant_reviews", """
        restaurant_id INTEGER,
        review_rating NUMERIC,
        review_text TEXT,
        review_id BIGINT
    """),
    "stg_customer_metrics": ("clean_customer_metrics", """
        customer_id TEXT PRIMARY KEY,
        order_count INTEGER,
        lifetime_spend NUMERIC
    """),
    "stg_customers": ("clean_customers", """
        customer_id TEXT PRIMARY KEY,
        name TEXT,
        email TEXT,
        phone TEXT,
        signup_date DATE
    """),
    "stg_orders": ("clean_orders", """
        order_id TEXT PRIMARY KEY,
        customer_id TEXT,
        restaurant_id INTEGER,
        order_date DATE,
        order_time TEXT,
        party_size INTEGER,
        order_total NUMERIC,
        order_status TEXT
    """),
    "stg_order_items": ("clean_order_items", """
        order_item_id TEXT PRIMARY KEY,
        order_id TEXT,
        item_name TEXT,
        item_price NUMERIC
    """),
    "stg_payments": ("clean_payments", """
        payment_id TEXT PRIMARY KEY,
        order_id TEXT,
        payment_method TEXT,
        amount NUMERIC,
        payment_status TEXT
    """),
    "stg_deliveries": ("clean_deliveries", """
        delivery_id TEXT PRIMARY KEY,
        order_id TEXT,
        delivery_partner_id TEXT,
        delivery_partner_name TEXT,
        delivery_time_minutes INTEGER,
        delivery_status TEXT
    """),
}


def find_csv_part(folder_name):
    matches = glob.glob(str(DATA_DIR / folder_name / "part-*.csv"))
    if not matches:
        raise FileNotFoundError(f"No part CSV found in data/{folder_name}/")
    return matches[0]


def stream_batches(csv_path):
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        columns = reader.fieldnames
        batch = []
        for row in reader:
            batch.append(tuple(row[c] if row[c] != "" else None for c in columns))
            if len(batch) >= BATCH_SIZE:
                yield columns, batch
                batch = []
        if batch:
            yield columns, batch


def load_table(cur, table_name, folder_name, columns_sql):
    csv_path = find_csv_part(folder_name)
    cur.execute(f"DROP TABLE IF EXISTS {table_name}")
    cur.execute(f"CREATE TABLE {table_name} ({columns_sql})")

    total = 0
    for columns, batch in stream_batches(csv_path):
        insert_sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES %s"
        execute_values(cur, insert_sql, batch)
        total += len(batch)
    print(f"{table_name}: {total} rows loaded from {folder_name}")


def main():
    conn = psycopg2.connect(**PG_CONFIG)
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            for table_name, (folder_name, columns_sql) in TABLES.items():
                load_table(cur, table_name, folder_name, columns_sql)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
