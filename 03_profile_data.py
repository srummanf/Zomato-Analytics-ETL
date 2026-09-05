"""Step 3: Data Profiling — one-time manual pass over the raw dataset.

Run once, by hand, before writing validate_data.py's rules. Not part of the
daily DAG. Uses pandas since this is a one-off exploratory script, not the
repeatable ingestion path (that's PySpark, in transform_data.py).
"""
from pathlib import Path

import pandas as pd

RAW_FILE = Path(__file__).parent / "data" / "raw_restaurants.csv"


def main():
    df = pd.read_csv(RAW_FILE)

    print(f"Shape: {df.shape}")
    print(f"Columns: {list(df.columns)}\n")

    print("--- Null counts per column ---")
    print(df.isnull().sum())

    print("\n--- Duplicate rows (by url) ---")
    if "url" in df.columns:
        print(f"Duplicate urls: {df['url'].duplicated().sum()}")

    print("\n--- 'rate' column: non-numeric values ---")
    if "rate" in df.columns:
        print(df["rate"].dropna().unique()[:20])

    print("\n--- 'approx_cost(for two people)' sample values ---")
    cost_col = "approx_cost(for two people)"
    if cost_col in df.columns:
        print(df[cost_col].dropna().unique()[:20])

    print("\n--- 'cuisines' sample values ---")
    if "cuisines" in df.columns:
        print(df["cuisines"].dropna().unique()[:10])

    print("\n--- 'phone' sample values (messiness check) ---")
    if "phone" in df.columns:
        print(df["phone"].dropna().unique()[:10])


if __name__ == "__main__":
    main()
