"""Step 9: Orchestration — single Airflow DAG wiring Steps 2, 4, 5, 6, 7, 8
into one daily run. Steps 1 (01_download_data.py) and 3 (03_profile_data.py)
are one-time/manual, so they're intentionally left out (per doc/PROJECT_OVERVIEW.md).

Runs inside the airflow container (see Dockerfile.airflow), which bundles a
JVM for 05_transform_data.py's PySpark job and dbt for the modeling step
alongside the plain pipeline scripts.
"""
from datetime import datetime

from airflow import DAG
from airflow.operators.bash import BashOperator

PROJECT_DIR = "/opt/project"

with DAG(
    dag_id="zomato_analytics_pipeline",
    schedule="@daily",
    start_date=datetime(2026, 1, 1),
    catchup=False,
) as dag:
    generate_synthetic_data = BashOperator(
        task_id="generate_synthetic_data",
        bash_command="python " + PROJECT_DIR + "/02_generate_synthetic_data.py --date {{ ds }}",
    )
    validate_data = BashOperator(
        task_id="validate_data",
        bash_command="python " + PROJECT_DIR + "/04_validate_data.py",
    )
    transform_data = BashOperator(
        task_id="transform_data",
        bash_command="python " + PROJECT_DIR + "/05_transform_data.py",
    )
    load_postgres = BashOperator(
        task_id="load_postgres",
        bash_command="python " + PROJECT_DIR + "/06_load_postgres.py",
    )
    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=f"cd {PROJECT_DIR}/dbt_project && dbt run",
    )
    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=f"cd {PROJECT_DIR}/dbt_project && dbt test",
    )
    record_dbt_test_results = BashOperator(
        task_id="record_dbt_test_results",
        bash_command="python " + PROJECT_DIR + "/07_record_dbt_test_results.py",
        trigger_rule="all_done",
    )
    load_doris = BashOperator(
        task_id="load_doris",
        bash_command="python " + PROJECT_DIR + "/08_load_doris.py",
    )

    (
        generate_synthetic_data
        >> validate_data
        >> transform_data
        >> load_postgres
        >> dbt_run
        >> dbt_test
        >> load_doris
    )
    dbt_test >> record_dbt_test_results
