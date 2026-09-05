"""Step 4: Data Validation — explicit business rules on top of the raw files.

Valid rows are written to data/valid_*.csv for 05_transform_data.py to consume.
Invalid rows are quarantined to data/rejected_*.csv with a reason code instead
of being dropped silently or crashing the pipeline.

Exits non-zero if any entity's rejection rate exceeds REJECTION_RATE_THRESHOLD,
so a bad run fails loudly instead of flowing downstream. Also appends one row
per run to Postgres (pipeline_validation_runs) so the Metabase Pipeline
Health page can chart rejection rates over time without a separate script.
"""
import os
import sys
from pathlib import Path

import pandas as pd
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path(__file__).parent / "data"
REJECTION_RATE_THRESHOLD = 0.02

PG_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": os.getenv("POSTGRES_PORT", "5439"),
    "dbname": os.getenv("POSTGRES_DB", "zomato"),
    "user": os.getenv("POSTGRES_USER", "zomato"),
    "password": os.getenv("POSTGRES_PASSWORD", "zomato"),
}


def split(df, is_valid_mask, reason_series):
    valid = df[is_valid_mask].copy()
    rejected = df[~is_valid_mask].copy()
    rejected["reject_reason"] = reason_series[~is_valid_mask]
    return valid, rejected


def validate_restaurants(df):
    reasons = pd.Series("", index=df.index)
    reasons[df["url"].isna() | (df["url"] == "")] = "missing_url"
    reasons[df["name"].isna() | (df["name"] == "")] = "missing_name"
    reasons[df["votes"] < 0] = "negative_votes"
    is_valid = reasons == ""
    return split(df, is_valid, reasons)


def validate_customers(df):
    reasons = pd.Series("", index=df.index)
    reasons[df["customer_id"].isna()] = "missing_customer_id"
    is_dup = df["customer_id"].duplicated() & (reasons == "")
    reasons[is_dup] = "duplicate_customer_id"
    is_valid = reasons == ""
    return split(df, is_valid, reasons)


def validate_orders(df, valid_restaurant_ids, valid_customer_ids):
    reasons = pd.Series("", index=df.index)
    reasons[df["order_total"] <= 0] = "non_positive_order_total"
    reasons[(reasons == "") & ~df["customer_id"].isin(valid_customer_ids)] = "orphan_customer_id"
    reasons[(reasons == "") & ~df["restaurant_id"].isin(valid_restaurant_ids)] = "orphan_restaurant_id"
    is_dup = df["order_id"].duplicated() & (reasons == "")
    reasons[is_dup] = "duplicate_order_id"
    is_valid = reasons == ""
    return split(df, is_valid, reasons)


def validate_order_items(df, valid_order_ids):
    reasons = pd.Series("", index=df.index)
    reasons[df["item_price"] < 0] = "negative_item_price"
    reasons[(reasons == "") & ~df["order_id"].isin(valid_order_ids)] = "orphan_order_id"
    is_valid = reasons == ""
    return split(df, is_valid, reasons)


def validate_payments(df, valid_order_ids):
    reasons = pd.Series("", index=df.index)
    reasons[df["amount"] <= 0] = "non_positive_amount"
    reasons[(reasons == "") & ~df["order_id"].isin(valid_order_ids)] = "orphan_order_id"
    is_valid = reasons == ""
    return split(df, is_valid, reasons)


def validate_deliveries(df, valid_order_ids):
    reasons = pd.Series("", index=df.index)
    reasons[df["delivery_time_minutes"] <= 0] = "non_positive_delivery_time"
    reasons[(reasons == "") & ~df["order_id"].isin(valid_order_ids)] = "orphan_order_id"
    is_valid = reasons == ""
    return split(df, is_valid, reasons)


def report(name, valid, rejected):
    total = len(valid) + len(rejected)
    rate = len(rejected) / total if total else 0
    print(f"{name}: {len(valid)} valid, {len(rejected)} rejected ({rate:.2%})")
    return rate


def record_pipeline_health(total_valid, total_rejected, rejection_rate):
    conn = psycopg2.connect(**PG_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS pipeline_validation_runs (
                    run_at TIMESTAMP DEFAULT now(),
                    total_valid INTEGER,
                    total_rejected INTEGER,
                    rejection_rate NUMERIC
                )
            """)
            cur.execute(
                "INSERT INTO pipeline_validation_runs (total_valid, total_rejected, rejection_rate) "
                "VALUES (%s, %s, %s)",
                (total_valid, total_rejected, rejection_rate),
            )
        conn.commit()
    finally:
        conn.close()


def main():
    restaurants = pd.read_csv(DATA_DIR / "raw_restaurants.csv")
    customers = pd.read_csv(DATA_DIR / "raw_customers.csv")
    orders = pd.read_csv(DATA_DIR / "raw_orders.csv")
    order_items = pd.read_csv(DATA_DIR / "raw_order_items.csv")
    payments = pd.read_csv(DATA_DIR / "raw_payments.csv")
    deliveries = pd.read_csv(DATA_DIR / "raw_deliveries.csv")
    restaurants["restaurant_id"] = restaurants.index

    valid_restaurants, rejected_restaurants = validate_restaurants(restaurants)
    valid_customers, rejected_customers = validate_customers(customers)
    valid_orders, rejected_orders = validate_orders(
        orders, set(valid_restaurants["restaurant_id"]), set(valid_customers["customer_id"])
    )
    valid_order_ids = set(valid_orders["order_id"])
    valid_items, rejected_items = validate_order_items(order_items, valid_order_ids)
    valid_payments, rejected_payments = validate_payments(payments, valid_order_ids)
    valid_deliveries, rejected_deliveries = validate_deliveries(deliveries, valid_order_ids)

    results = [
        ("restaurants", valid_restaurants, rejected_restaurants),
        ("customers", valid_customers, rejected_customers),
        ("orders", valid_orders, rejected_orders),
        ("order_items", valid_items, rejected_items),
        ("payments", valid_payments, rejected_payments),
        ("deliveries", valid_deliveries, rejected_deliveries),
    ]

    worst_rate = 0.0
    total_valid = 0
    total_rejected = 0
    for name, valid, rejected in results:
        valid.to_csv(DATA_DIR / f"valid_{name}.csv", index=False)
        rejected.to_csv(DATA_DIR / f"rejected_{name}.csv", index=False)
        worst_rate = max(worst_rate, report(name, valid, rejected))
        total_valid += len(valid)
        total_rejected += len(rejected)

    overall_rate = total_rejected / (total_valid + total_rejected) if (total_valid + total_rejected) else 0
    record_pipeline_health(total_valid, total_rejected, overall_rate)

    if worst_rate > REJECTION_RATE_THRESHOLD:
        print(f"\nFAILED: rejection rate {worst_rate:.2%} exceeds threshold {REJECTION_RATE_THRESHOLD:.0%}")
        sys.exit(1)

    print("\nAll entities within rejection rate threshold.")


if __name__ == "__main__":
    main()
