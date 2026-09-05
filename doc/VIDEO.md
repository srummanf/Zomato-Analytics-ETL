# Watch These If a Doc Isn't Enough

Reading about a concept and *seeing* someone build it are different kinds of
learning — sometimes a 20-minute video makes something click faster than any
README. This doc lists solid, freely available YouTube videos for **every
tool and concept this project uses**, in the **same order as the pipeline
itself** — so you can watch a video, then go read (or run) the matching
step, then move to the next one.

None of these are made by us — they're just good explainers we'd point a
junior teammate to.

---

## 0. The Big Picture — Data Engineering & ETL

Watch this before anything else. Everything below is one small piece of
this bigger idea.

- **[What Is ETL (Extract, Transform, Load)? — Simplilearn](https://www.youtube.com/watch?v=Z4hTkPjZ8Z0)**
  The shortest, clearest "what is ETL and why does it exist" explainer.
- **[ETL Full Course 2026 — Simplilearn](https://www.youtube.com/watch?v=D18PQG7Ae34)**
  Free full course if the short video leaves you wanting more depth.
- **[How I Would Learn Data Engineering in 2026 (if I could start over)](https://www.youtube.com/watch?v=iiV_O4Uqj9Q)**
  A working data engineer's roadmap — useful context for *why* this project
  touches so many tools (Spark, dbt, Airflow, a warehouse, a BI tool)
  instead of just one.

> ETL (Extract, Transform, Load) is a key process in data engineering that
> prepares raw data for analysis. It involves extracting data from one or
> more sources, transforming it into a clean and consistent format, and
> loading it into a place where it can be queried — a database, a
> warehouse, or a data lake.

---

## Infrastructure — Docker & Docker Compose

Before Step 1 even runs, know what's actually running this project: 4
services (Postgres, Doris, Airflow, Metabase), each in its own container,
all started with one command (`docker compose up -d`).

- **[Docker Tutorial for Beginners — freeCodeCamp](https://youtu.be/fqMOX6JJhGo)**
  Covers images, containers, and Docker Compose — everything needed to
  understand `docker-compose.yml` in this repo.

---

## Step 1 — Data Acquisition (Kaggle / `kagglehub`)

`01_download_data.py` pulls the real restaurant dataset once, via Kaggle's
API.

- **[Download Kaggle Datasets via API in Python](https://www.youtube.com/watch?v=hzcV0hDkfzs)**
  Same mechanism `kagglehub.dataset_download(...)` uses under the hood.
- **[How to Use and Download Kaggle Dataset](https://www.youtube.com/watch?v=tUSRvV8bTMQ)**
  A second walkthrough if the first moves too fast.

---

## Step 2 — Synthetic Data Generation (Faker)

`02_generate_synthetic_data.py` invents customers, orders, payments, and
deliveries with the Python **Faker** library, anchored to real restaurant
signals (rating, votes, cost).

- **[Create Fake Data Instantly with Python!](https://www.youtube.com/watch?v=b-oZjSbLFfo)**
  Faker + pandas, the exact combination this script uses.
- **[Generate Dummy Data Using Faker Library For Projects](https://www.youtube.com/watch?v=nI3Ff32mRDI)**
  Framed specifically around data-engineering use cases, not just testing.

---

## Step 3 — Data Profiling

`03_profile_data.py` looks at the raw data (nulls, weird formats,
duplicates) *before* anyone writes a single validation rule. Our script does
this by hand with plain pandas, but the concept is identical to what
dedicated profiling tools automate:

- **[Fast and Effective EDA With Python and Pandas Profiling](https://www.youtube.com/watch?v=cy9Jrm6u07w)**
  Shows the automated version of what `03_profile_data.py` does manually —
  useful to see the full picture of what "profiling" can surface.
- **[How to Begin Profiling Your Data with Pandas Profiling](https://www.youtube.com/watch?v=K_Fflmx4ndE)**
  A shorter, beginner-friendly follow-up.

---

## Step 4 — Data Validation & Data Quality

`04_validate_data.py` is the pipeline's gatekeeper — reject bad rows with a
reason code, fail loudly if too many rows are bad.

- **[Data Quality Fundamentals: Beginner Guide](https://www.youtube.com/watch?v=GYw8Rkq19qo)**
  Covers accuracy, completeness, consistency — the same vocabulary used
  throughout this project's docs.
- **[Diagnose Data for Cleaning — DataCamp](https://www.youtube.com/watch?v=hDtQZWL-3uk)**
  Practical look at spotting bad data before writing rules for it.

---

## Step 5 — Data Transformation (PySpark)

`05_transform_data.py` cleans, explodes, and parses the data at scale.

- **[PySpark Tutorial — Full Course](https://www.youtube.com/watch?v=96phpxJOFdU)**
  DataFrames, schemas, transformations — the exact building blocks used
  here.
- **[PySpark Tutorial | Full Course (From Zero to Pro!)](https://www.youtube.com/watch?v=94w6hPk7nkM)**
  A second full course with a different teaching style/pace.

> **What is PySpark used for?** PySpark lets you use Python to process and
> analyze datasets too large (or too slow) to comfortably handle on one
> machine with plain pandas. It runs your code across multiple worker
> processes — in a real cluster, multiple machines — which is what makes
> big-data transformations fast. Typical uses: batch and real-time
> processing, running SQL over distributed data, scalable machine
> learning, and streaming data from sources like Kafka.

---

## Step 6 — Load to Staging (PostgreSQL)

`06_load_postgres.py` bulk-loads the cleaned CSVs into Postgres staging
tables using `COPY`.

- **[Learn PostgreSQL Tutorial — Full Course for Beginners (freeCodeCamp)](https://www.youtube.com/watch?v=qw--VYLpxG4)**
  Everything from installation to `SELECT`/`GROUP BY` to more advanced
  querying — enough to comfortably read every SQL query in this project.

---

## Step 7 — Data Modeling (dbt + Star Schema)

`dbt_project/` turns staging tables into a proper star schema
(dimensions + facts) and runs 37 automated data-quality tests.

- **[dbt Course for Beginners to Advanced](https://www.youtube.com/watch?v=ziyFbdHaoxc)**
  Models, sources, refs, and tests — the 4 concepts `dbt_project/` is built
  from.
- **[Getting Started With dbt](https://www.youtube.com/watch?v=anZkGCFK87Y)**
  Shorter, good if you already know SQL and just want the dbt-specific
  mental model.
- **[Data Warehouse Schema Design — Dimensional Modeling and Star Schema](https://www.youtube.com/watch?v=fpquGrdgbLg)**
  Explains fact tables vs. dimension tables — the exact shape of
  `dbt_project/models/dims/` and `models/facts/`.
- **[Data Modeling Explained: Star vs. Snowflake Schema](https://www.youtube.com/watch?v=4dEKvxEy9Oo)**
  Why we picked a star schema (simpler, fewer joins) over a snowflake
  schema (more normalized).

---

## Step 8 — Load to Warehouse (Apache Doris)

`08_load_doris.py` copies the finished star schema into Doris — the
database that actually serves the dashboard's queries.

- **[Apache Doris: A Real-Time Data Warehouse](https://www.youtube.com/watch?v=Y_AHSTDB8Zs)**
  What an OLAP (analytical) database is and where Doris fits — explains
  *why* this project loads data into Doris instead of querying Postgres
  directly (see `doc/FLOWCHART.md` Step 8 for the short version).

---

## Step 9 — Orchestration (Apache Airflow / DAGs)

`09_dag.py` is what actually runs Steps 2 and 4–8, automatically, once a
day.

- **[Apache Airflow Tutorial for Data Engineers](https://www.youtube.com/watch?v=y5rYZLBZ_Fw)**
  What a DAG is, the Airflow UI, and writing your first pipeline.
- **[Airflow Tutorial 4: Writing Your First Pipeline](https://www.youtube.com/watch?v=43wHwwZhJMo)**
  Hands-on: writing a `DAG` object with tasks and `>>` dependencies — the
  exact pattern used in `09_dag.py`.

---

## Step 10 — Visualization (Metabase)

Metabase reads Doris and Postgres, live, and turns them into the 4
dashboards described in `doc/DASHBOARD.md`.

- **[Metabase Concepts — Getting Started with Metabase](https://www.youtube.com/watch?v=7esMaFvKGqo)**
  Official intro to Metabase's core ideas (questions, dashboards, data
  browsing).
- **[Metabase Tutorial: Everything You Need to Know in Under 40 Min](https://www.youtube.com/watch?v=LJ0l2HZ8Lp8)**
  Full walkthrough — connecting a database, building charts, and putting
  them on a dashboard, start to finish.

---

## Step 11 — Monitoring (Pipeline Health)

`04_validate_data.py` and `07_record_dbt_test_results.py` log rejection
rates and dbt test results to Postgres — the Pipeline Health dashboard reads
those tables directly.

- **[Data Observability Explained: The Key to Trusted Data Pipelines](https://www.youtube.com/watch?v=HDNPI0vegwI)**
  The bigger idea our Pipeline Health dashboard is a small version of —
  knowing whether your pipeline (and the data inside it) is actually
  healthy, not just "did it not crash."

---

## Suggested watch order

Just go top to bottom — that's the whole point of this doc being ordered by
pipeline step instead of by topic. Watch a section, then go open the
matching file (`0X_*.py`, `dbt_project/`, etc.) and read it side by side.
