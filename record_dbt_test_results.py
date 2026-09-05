"""Reads dbt's target/run_results.json after `dbt test` and appends one row
to Postgres (pipeline_dbt_test_runs) so the Metabase Pipeline Health page can
show the latest test pass rate without parsing dbt artifacts itself. Runs
even when dbt test fails, so a bad run shows up on the health page instead
of just silently not updating it.
"""
import json
import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

load_dotenv()

RUN_RESULTS_PATH = Path(__file__).parent / "dbt_project" / "target" / "run_results.json"

PG_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": os.getenv("POSTGRES_PORT", "5439"),
    "dbname": os.getenv("POSTGRES_DB", "zomato"),
    "user": os.getenv("POSTGRES_USER", "zomato"),
    "password": os.getenv("POSTGRES_PASSWORD", "zomato"),
}


def main():
    with open(RUN_RESULTS_PATH) as f:
        results = json.load(f)["results"]
    total = len(results)
    passed = sum(1 for r in results if r["status"] == "pass")

    conn = psycopg2.connect(**PG_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS pipeline_dbt_test_runs (
                    run_at TIMESTAMP DEFAULT now(),
                    total_tests INTEGER,
                    passed_tests INTEGER
                )
            """)
            cur.execute(
                "INSERT INTO pipeline_dbt_test_runs (total_tests, passed_tests) VALUES (%s, %s)",
                (total, passed),
            )
        conn.commit()
    finally:
        conn.close()

    print(f"Recorded dbt test run: {passed}/{total} passed")


if __name__ == "__main__":
    main()
