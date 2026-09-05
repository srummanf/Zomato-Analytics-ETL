"""Step 6: Load to Staging — bulk-load 05_transform_data.py's clean_*.csv output
into PostgreSQL staging tables.

Uses COPY (via psycopg2 copy_expert) to stream each CSV straight into its
table — orders of magnitude faster than row-by-row INSERT for the
multi-million-row reviews table, and Postgres's CSV parser already handles
the embedded newlines/quotes in review text. Each table is dropped and
recreated on every run, matching the ELT idea: staging always mirrors the
latest clean data; dbt (Step 7) does the durable modeling on top of it.
"""
import csv
import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path(__file__).parent / "data"

PG_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": os.getenv("POSTGRES_PORT", "5439"),
    "dbname": os.getenv("POSTGRES_DB", "zomato"),
    "user": os.getenv("POSTGRES_USER", "zomato"),
    "password": os.getenv("POSTGRES_PASSWORD", "zomato"),
}

# table -> (source data/clean_<name>.csv, CREATE TABLE column definitions)
TABLES = {
    "stg_restaurants": ("restaurants", """
        restaurant_id INTEGER PRIMARY KEY,
        restaurant_name TEXT,
        url TEXT,
        address TEXT,
        area TEXT,
        restaurant_type TEXT,
        meal_type TEXT,
        rating NUMERIC,
        vote_count INTEGER,
        avg_cost_for_two NUMERIC,
        online_order_enabled BOOLEAN,
        table_booking_enabled BOOLEAN
    """),
    "stg_restaurant_cuisines": ("restaurant_cuisines", """
        restaurant_id INTEGER,
        cuisine TEXT
    """),
    "stg_reviews": ("reviews", """
        restaurant_id INTEGER,
        review_rating NUMERIC,
        review_text TEXT
    """),
    "stg_customers": ("customers", """
        customer_id TEXT PRIMARY KEY,
        name TEXT,
        email TEXT,
        phone TEXT,
        signup_date DATE,
        customer_order_count INTEGER
    """),
    "stg_orders": ("orders", """
        order_id TEXT PRIMARY KEY,
        customer_id TEXT,
        restaurant_id INTEGER,
        order_date DATE,
        order_time TEXT,
        party_size INTEGER,
        order_total NUMERIC,
        order_status TEXT,
        order_hour INTEGER
    """),
    "stg_order_items": ("order_items", """
        order_item_id TEXT PRIMARY KEY,
        order_id TEXT,
        item_name TEXT,
        item_price NUMERIC
    """),
    "stg_payments": ("payments", """
        payment_id TEXT PRIMARY KEY,
        order_id TEXT,
        payment_method TEXT,
        amount NUMERIC,
        payment_status TEXT
    """),
    "stg_deliveries": ("deliveries", """
        delivery_id TEXT PRIMARY KEY,
        order_id TEXT,
        delivery_partner_id TEXT,
        delivery_partner_name TEXT,
        delivery_time_minutes INTEGER,
        delivery_status TEXT
    """),
}


def find_csv(name):
    path = DATA_DIR / f"clean_{name}.csv"
    if not path.exists():
        raise FileNotFoundError(f"{path} not found — run 05_transform_data.py first")
    return path


def csv_columns(csv_path):
    with open(csv_path, newline="", encoding="utf-8") as f:
        return next(csv.reader(f))


def load_table(cur, table_name, source_name, columns_sql):
    csv_path = find_csv(source_name)
    columns = csv_columns(csv_path)
    cur.execute(f"DROP TABLE IF EXISTS {table_name}")
    cur.execute(f"CREATE TABLE {table_name} ({columns_sql})")

    copy_sql = (
        f"COPY {table_name} ({', '.join(columns)}) "
        "FROM STDIN WITH (FORMAT csv, HEADER true, NULL '')"
    )
    with open(csv_path, newline="", encoding="utf-8") as f:
        cur.copy_expert(copy_sql, f)
    print(f"{table_name}: {cur.rowcount} rows loaded from clean_{source_name}.csv")


def main():
    conn = psycopg2.connect(**PG_CONFIG)
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            for table_name, (source_name, columns_sql) in TABLES.items():
                load_table(cur, table_name, source_name, columns_sql)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
