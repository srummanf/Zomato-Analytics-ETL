# Zomato Analytics ETL

An end-to-end, fully self-hosted analytics pipeline for a Zomato-style food-delivery
business. Real Bangalore restaurant data (Kaggle) is combined with synthetic
transactional data (Faker), cleaned and modeled through a complete ELT stack, and
served through a Plotly dashboard — all on free, self-hosted tooling with **no paid
cloud services**.

---

## Table of Contents

- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Status](#project-status)
- [Repository Structure](#repository-structure)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
- [Running the Pipeline](#running-the-pipeline)
- [Data Model (Star Schema)](#data-model-star-schema)
- [Dashboards](#dashboards)
- [Data Quality & Testing](#data-quality--testing)
- [Environment Variables](#environment-variables)
- [Known Issues & Troubleshooting](#known-issues--troubleshooting)
- [Project Docs](#project-docs)

---

## Architecture

```mermaid
flowchart TD
    START(["START"])

    START --> KAGGLE["01_download_data.py<br/>One-time"]
    KAGGLE --> RAW_R["data/raw_restaurants.csv"]

    FAKER["02_generate_synthetic_data.py<br/>Daily"] --> RAW_T["raw_customers/<br/>orders/<br/>items/<br/>payments/<br/>deliveries.csv"]

    RAW_R --> VALIDATE["04_validate_data.py<br/>Step 4"]
    RAW_T --> VALIDATE

    VALIDATE -->|valid_*.csv| TRANSFORM["05_transform_data.py<br/>Step 5 (PySpark)"]
    VALIDATE -.->|rejected_*.csv +<br/>Postgres pipeline_validation_runs| HEALTH[("Pipeline Health")]

    TRANSFORM -->|clean_*.csv| LOAD_PG["06_load_postgres.py<br/>Step 6"]
    LOAD_PG --> PG[("PostgreSQL<br/>staging: stg_*")]

    PG --> DBT_RUN["dbt run<br/>staging → dims → facts"]
    DBT_RUN --> DBT_TEST["dbt test<br/>37 tests"]

    DBT_TEST -.-> RECORD["07_record_dbt_test_results.py<br/>→ pipeline_dbt_test_runs"]
    DBT_TEST --> LOAD_DORIS["08_load_doris.py<br/>Step 8"]

    LOAD_DORIS --> DORIS[("Apache Doris<br/>star schema")]

    DORIS --> METABASE["Metabase<br/>4 dashboards"]
    HEALTH --> METABASE

    METABASE --> PLOTLY["Plotly Dashboard"]
    PLOTLY --> STOP(["STOP"])

    AIRFLOW(["Airflow DAG<br/>@daily"]) -.orchestrates.-> FAKER
    AIRFLOW -.orchestrates.-> VALIDATE
    AIRFLOW -.orchestrates.-> TRANSFORM
    AIRFLOW -.orchestrates.-> LOAD_PG
    AIRFLOW -.orchestrates.-> DBT_RUN
    AIRFLOW -.orchestrates.-> DBT_TEST
    AIRFLOW -.orchestrates.-> LOAD_DORIS
```

`01_download_data.py` (Step 1) and `03_profile_data.py` (Step 3) are one-time/manual —
not part of the daily DAG.

---

## Tech Stack


| Layer               | Technology                           | Notes                                                |
| --------------------- | -------------------------------------- | ------------------------------------------------------ |
| Language            | Python 3.11                          | 3.12 breaks PySpark 3.5.3 workers on Windows         |
| Real data source    | Kaggle`rajeshrampure/zomato-dataset` | via`kagglehub`, one-time seed                        |
| Synthetic data      | Faker                                | orders, customers, order items, payments, deliveries |
| Transform           | PySpark 3.5.3                        | runs inside the`airflow` container (bundled JVM)     |
| Staging store       | PostgreSQL 16                        | port`5439` on host                                   |
| Warehouse modeling  | dbt Core 1.8.8 (`dbt-postgres`)      | builds star schema directly in Postgres              |
| Analytics warehouse | Apache Doris (`all-in-one` image)    | FE+BE in one container; serves BI queries            |
| Orchestration       | Apache Airflow 3.3.1 (`standalone`)  | LocalExecutor, SQLite metadata (not persisted)       |
| Dashboard           | Metabase                             | port`3030` on host                                   |
| Containers          | Docker / Docker Compose              | 4 services: postgres, doris, airflow, metabase       |
| Version control     | Git + GitHub                         |                                                      |

Full rationale for each choice (why Doris over Snowflake, why dbt over Great
Expectations, etc.) is in [`doc/PROJECT_OVERVIEW.md`](doc/PROJECT_OVERVIEW.md).

---

## Project Status

**All 10 pipeline steps are implemented, wired into Airflow, and verified with a
real end-to-end run.**


| Step                         | File                                                          |  Runs in daily DAG?  | Status                 |
| ------------------------------ | --------------------------------------------------------------- | :---------------------: | ------------------------ |
| 1. Data Acquisition          | `01_download_data.py`                                         |  No (one-time seed)  | ✅                     |
| 2. Synthetic Data Generation | `02_generate_synthetic_data.py`                               |          Yes          | ✅                     |
| 3. Data Profiling            | `03_profile_data.py`                                          | No (manual, one-time) | ✅                     |
| 4. Data Validation           | `04_validate_data.py`                                         |          Yes          | ✅                     |
| 5. Data Transformation       | `05_transform_data.py` (PySpark)                              |          Yes          | ✅                     |
| 6. Load to Staging           | `06_load_postgres.py`                                         |          Yes          | ✅                     |
| 7. Data Modeling             | `dbt_project/`                                                |          Yes          | ✅ 37/37 tests passing |
| 8. Load to Warehouse         | `08_load_doris.py`                                            |          Yes          | ✅                     |
| 9. Orchestration             | `09_dag.py` (Airflow)                                         |          —          | ✅                     |
| 10. Visualization            | Metabase (4 dashboards)                                       |    No (always-on)    | ✅                     |
| 11. Monitoring               | Postgres`pipeline_validation_runs` / `pipeline_dbt_test_runs` |     Yes (passive)     | ✅                     |

Last verified full-DAG run: `generate_synthetic_data → validate_data →
transform_data → load_postgres → dbt_run → dbt_test → record_dbt_test_results

+ load_doris`, all green, ~4 minutes end to end.

---

## Repository Structure

Kept flat by design — one small script per pipeline step, no `src/`-style
package layout. The only exception is `dbt_project/`, whose internal layout
(`models/`, `target/`) is required by dbt itself.

```
data etl/
├── 01_download_data.py             # Step 1 — one-time Kaggle download
├── 02_generate_synthetic_data.py   # Step 2 — Faker-generated daily transactions
├── 03_profile_data.py              # Step 3 — one-time manual data profiling
├── 04_validate_data.py             # Step 4 — schema/business-rule validation + quarantine
├── 05_transform_data.py            # Step 5 — PySpark cleaning, explode, review parsing
├── 06_load_postgres.py             # Step 6 — bulk COPY into Postgres staging tables
├── 07_record_dbt_test_results.py   # records dbt test pass/fail to Postgres for Step 11
├── 08_load_doris.py                # Step 8 — Stream Load star schema into Doris
├── 09_dag.py                       # Step 9 — single Airflow DAG wiring steps 2,4-8
├── 10_dash_dashboard.py            # standalone local Plotly Dash frontend (not in the DAG)
├── assets/                         # Dash static assets (the Zomato logo SVG)
├── dbt_project/                    # Step 7 — dbt models (dims/facts) + tests
│   ├── dbt_project.yml
│   ├── profiles.yml
│   └── models/
│       ├── sources.yml             # declares Postgres stg_* tables as dbt sources
│       ├── schema.yml              # not_null/unique/relationships tests
│       ├── dims/                   # dim_restaurant, dim_location, dim_cuisine,
│       │                           # dim_customer, dim_delivery_partner, dim_date,
│       │                           # dim_time, bridge_restaurant_cuisine
│       └── facts/                  # fact_orders, fact_order_items, fact_deliveries,
│                                    # fact_payments, fact_reviews
├── Dockerfile                      # image for ad-hoc script runs (PySpark + JVM)
├── Dockerfile.airflow              # Airflow image: apache/airflow + JVM + dbt + scripts
├── docker-compose.yml              # postgres, doris, airflow, metabase services
├── requirements.txt
├── .env.example                    # template for every env var the scripts read
├── data/                           # gitignored — raw/valid/rejected/clean CSVs
├── doc/                            # all other docs — see below
│   ├── PROJECT_OVERVIEW.md         # architecture, diagrams, dashboard wireframe
│   ├── PRD.md                      # requirements, data dictionary, acceptance criteria
│   ├── FLOWCHART.md
│   ├── DASHBOARD.md
│   ├── WALKTHROUGH.md
│   ├── VIDEO.md
│   └── PASSWORD.md                 # gitignored — never pushed
├── CLAUDE.md                       # hard constraints for AI-assisted work in this repo
└── README.md                       # this file (kept at root on purpose — GitHub renders it automatically)
```

---

## Prerequisites

- **Docker Desktop** (with at least ~6–8 GB memory allocated — see
  [Known Issues](#known-issues--troubleshooting))
- **Python 3.11** (not 3.12 — see Known Issues) for running scripts locally outside Docker
- **Kaggle API credentials** for the one-time dataset download: place `kaggle.json`
  at `~/.kaggle/kaggle.json`, or set `KAGGLE_USERNAME` / `KAGGLE_KEY` env vars

---

## Setup

```bash
# 1. Create and activate a Python 3.11 virtual environment
python -m venv .venv
.venv/Scripts/activate        # Windows
# source .venv/bin/activate   # macOS/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. One-time: download the real Kaggle dataset
python 01_download_data.py

# 4. One-time (optional but recommended): profile the raw data before trusting
#    04_validate_data.py's rules
python 03_profile_data.py

# 5. Bring up the infrastructure
docker compose up -d
```

`docker compose up -d` starts 4 services: `postgres`, `doris`, `airflow`
(builds from `Dockerfile.airflow` on first run), and `metabase`. Wait for all
four to report healthy:

```bash
docker compose ps
```


| Service  | Host port(s)                                                              | Purpose                                                                                               |
| ---------- | --------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| postgres | `5439` → 5432                                                            | Staging store                                                                                         |
| doris    | `8030` (FE HTTP), `9030` (MySQL protocol), `8040` (BE HTTP / Stream Load) | Analytics warehouse                                                                                   |
| airflow  | `8080`                                                                    | Airflow UI (`standalone` mode; admin password printed to `docker compose logs airflow` on first boot) |
| metabase | `3030` → 3000                                                            | BI dashboard UI                                                                                       |

---

## Running the Pipeline

### Via Airflow (recommended)

```bash
docker compose exec airflow airflow dags unpause zomato_analytics_pipeline
```

The DAG (`@daily`, `catchup=False`) runs automatically once unpaused. To
trigger it manually for today:

```bash
docker compose exec airflow airflow dags trigger zomato_analytics_pipeline
```

Check progress:

```bash
docker compose exec airflow airflow tasks states-for-dag-run \
  zomato_analytics_pipeline "scheduled__<date>T00:00:00+00:00"
```

> Airflow's `standalone` mode uses SQLite with no persisted volume — its own
> run history resets on every `docker compose up`/container recreate. The
> actual pipeline data (Postgres, Doris, `data/`) is unaffected.

### Running steps manually (for debugging)

Each script can be run directly inside the `airflow` container, which has the
JVM, dbt, and all Python dependencies:

```bash
docker compose exec airflow bash -c "cd /opt/project && python 02_generate_synthetic_data.py --date 2026-09-05"
docker compose exec airflow bash -c "cd /opt/project && python 04_validate_data.py"
docker compose exec airflow bash -c "cd /opt/project && python 05_transform_data.py"
docker compose exec airflow bash -c "cd /opt/project && python 06_load_postgres.py"
docker compose exec airflow bash -c "cd /opt/project/dbt_project && dbt run && dbt test"
docker compose exec airflow bash -c "cd /opt/project && python 07_record_dbt_test_results.py"
docker compose exec airflow bash -c "cd /opt/project && python 08_load_doris.py"
```

### Accessing Metabase

Open `http://localhost:3030`. Four dashboards live under **Our analytics**:
Business Overview, Customer Insights, Delivery & Operations, Pipeline Health.

### Alternative: local Plotly Dash frontend

`10_dash_dashboard.py` is a standalone, local-only frontend (not part of the
DAG) that reads the same Doris/Postgres tables and shows the same four pages
in a custom Zomato-branded UI (red sidebar, real Zomato logo, Poppins font).
No Docker/Metabase login needed — just:

```bash
pip install dash plotly
python 10_dash_dashboard.py
```

Then open `http://127.0.0.1:8050`. See [`doc/DASHBOARD.md`](doc/DASHBOARD.md#alternative-frontend--the-local-plotly-dash-dashboard)
for what it looks like and [`doc/WALKTHROUGH.md`](doc/WALKTHROUGH.md) step 13
for more detail.

---

## Data Model (Star Schema)

**Fact tables**


| Table              | Grain                                                        |
| -------------------- | -------------------------------------------------------------- |
| `fact_orders`      | one row per order                                            |
| `fact_order_items` | one row per order line item                                  |
| `fact_deliveries`  | one row per delivery                                         |
| `fact_payments`    | one row per payment                                          |
| `fact_reviews`     | one row per parsed review (from Kaggle's real`reviews_list`) |

**Dimension tables**

`dim_customer`, `dim_restaurant`, `dim_delivery_partner`, `dim_location`,
`dim_date`, `dim_time`, `dim_cuisine` + `bridge_restaurant_cuisine`
(many-to-many restaurant↔cuisine).

Geography uses `dim_location.area` (Bangalore neighborhood), **not** a fake
multi-city field — the Kaggle dataset's `listed_in(city)` column is a
scrape-region label within Bangalore only. See `CLAUDE.md` for this and other
known data-shape gotchas.

Full data dictionary (raw Kaggle column → star-schema column mapping) is in
[`doc/PRD.md`](doc/PRD.md#53-data-dictionary--raw-kaggle-columns--star-schema).

---

## Dashboards


| Page                      | Highlights                                                                                                                                       |
| --------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Business Overview**     | Total orders/revenue/AOV/active restaurants, revenue trend, orders by area, top cuisines, top restaurants                                        |
| **Customer Insights**     | Total/new customers, repeat rate, avg orders/customer, customer value tiers, orders by payment method                                            |
| **Delivery & Operations** | Avg delivery time, cancellation rate, avg rating, on-time %, order volume by hour, delivery partner leaderboard, online-order-enabled comparison |
| **Pipeline Health**       | Rows ingested/rejected/rejection rate (latest run), dbt test pass rate, rejection rate trend                                                     |

Business Overview/Customer Insights/Delivery & Operations query **Doris**
directly. Pipeline Health queries **Postgres** (`pipeline_validation_runs` /
`pipeline_dbt_test_runs`), since that monitoring data isn't part of the star
schema loaded into Doris.

---

## Data Quality & Testing

Data quality is front-loaded, not bolted on (see `CLAUDE.md`):

- **`04_validate_data.py`** enforces explicit business rules (missing keys,
  orphaned foreign keys, non-positive amounts, duplicates) on every raw file.
  Invalid rows are quarantined to `data/rejected_*.csv` with a `reject_reason`
  column instead of being silently dropped. The pipeline **fails loudly**
  (`sys.exit(1)`) if any entity's rejection rate exceeds 2%.
- **dbt tests** (37 total, in `dbt_project/models/schema.yml`): `not_null` and
  `unique` on every primary key, `relationships` on every foreign key across
  all dims, bridge, and facts.
- Both feed the **Pipeline Health** dashboard: `04_validate_data.py` appends a row
  to `pipeline_validation_runs` on every run; `07_record_dbt_test_results.py`
  appends to `pipeline_dbt_test_runs` after every `dbt test` — even on
  failure, so a bad run is visible rather than silently missing.

---

## Environment Variables

All scripts default to the values `docker-compose.yml` sets for
inter-container networking, and fall back to host-side defaults (matching the
mapped ports) when run locally outside Docker. Override via a `.env` file
(gitignored) or real environment variables — never commit real credentials.


| Variable                                              | Default (local/.env)                  | Default (inside`airflow` container) |
| ------------------------------------------------------- | --------------------------------------- | ------------------------------------- |
| `POSTGRES_HOST`                                       | `localhost`                           | `postgres`                          |
| `POSTGRES_PORT`                                       | `5439`                                | `5432`                              |
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` | `zomato`                              | `zomato`                            |
| `DORIS_HOST`                                          | `localhost`                           | `doris`                             |
| `DORIS_QUERY_PORT`                                    | `9030`                                | `9030`                              |
| `DORIS_STREAM_LOAD_PORT`                              | `8040`                                | `8040`                              |
| `DORIS_USER` / `DORIS_PASSWORD`                       | `root` / *(empty)*                    | `root` / *(empty)*                  |
| `DBT_PROFILES_DIR`                                    | `dbt_project` (pass `--profiles-dir`) | `/opt/project/dbt_project`          |

---

## Known Issues & Troubleshooting

**PySpark on Windows (if running `05_transform_data.py` outside Docker):**
PySpark 3.5.3 needs Python 3.11 (not 3.12 — worker crashes), a Java 8 JRE, and
a project-local `winutils.exe`/`hadoop.dll` for any local-filesystem write.
Inside the `airflow` container this is a non-issue (Linux + bundled JVM);
these fixes only matter for local/native runs on Windows.

**CSV quoting mismatches between tools** — hit and fixed twice in this
project, worth knowing about if you touch `05_transform_data.py` or
`08_load_doris.py` again:

- Postgres's `COPY (FORMAT csv)` and pandas both follow RFC4180: an embedded
  quote is escaped by **doubling** it (`""`).
- Spark's CSV writer/reader **defaults to backslash-escaping** (`\"`) instead.
  Reading a pandas-written CSV in Spark needs `.option("escape", '"')`;
  writing a CSV from Spark for Postgres to `COPY` needs the same
  (`05_transform_data.py`'s `write_csv_native` sets this explicitly).
- Apache Doris's Stream Load API needs an explicit `enclose` header to handle
  quoted fields at all, and its `escape` header — if set — expects backslash
  escaping, which broke on review text that legitimately contains a literal
  backslash (e.g. `:-\` emoticons). Fixed by using `enclose` **without**
  `escape` in `08_load_doris.py`.

**`05_transform_data.py` memory usage:** the reviews table (1.3M+ rows) is
written via `write_csv_native()` (Spark's own CSV writer) rather than
`.toPandas()` — collecting that much text through Py4J into a pandas
DataFrame roughly doubles memory usage (JVM objects + Python objects held at
once) and was observed to crash the Spark JVM under memory pressure, which in
turn destabilized the whole Docker Desktop VM. If you reintroduce
`.toPandas()` for a large table, watch memory closely.

**Docker Desktop resource allocation:** running Postgres + Doris (JVM) +
Airflow (Spark) + Metabase (JVM) simultaneously is memory-heavy. Give Docker
Desktop as much memory as you reasonably can (Settings → Resources); under
7–8 GB, the whole VM can become unresponsive during `05_transform_data.py`'s
review-parsing step.

**`dbt-doris` risk:** never used — the architecture avoids it entirely.
`dbt-postgres` builds the star schema in Postgres; `08_load_doris.py` then
copies the finished tables into Doris via Stream Load. This sidesteps the
community `dbt-doris` adapter's unverified maturity, which was flagged as a
risk during planning (see `CLAUDE.md`).

---

## Project Docs

- [`CLAUDE.md`](CLAUDE.md) — hard constraints (no paid cloud, flat structure,
  data-quality-first) for anyone (human or AI) working in this repo. Kept at
  the root on purpose — Claude Code auto-loads it as project instructions
  from there.

Everything else lives in [`doc/`](doc/):

- [`doc/PROJECT_OVERVIEW.md`](doc/PROJECT_OVERVIEW.md) — architecture
  rationale, full pipeline diagram, dashboard wireframe, folder-structure
  philosophy
- [`doc/PRD.md`](doc/PRD.md) — goals/non-goals, full data dictionary,
  functional and non-functional requirements, acceptance criteria
- [`doc/FLOWCHART.md`](doc/FLOWCHART.md) — the entire pipeline, step by step,
  with a diagram and a real code snippet for every stage
- [`doc/DASHBOARD.md`](doc/DASHBOARD.md) — what every chart on every
  dashboard page means and why it's there
- [`doc/WALKTHROUGH.md`](doc/WALKTHROUGH.md) — hands-on demo script: exact
  commands to run every file yourself, with expected output
- [`doc/VIDEO.md`](doc/VIDEO.md) — curated YouTube videos for every concept
  and tool used (ETL, Airflow/DAGs, PySpark, dbt, Doris, Docker, Metabase)
- [`doc/PASSWORD.md`](doc/PASSWORD.md) — local credentials for every service
  (gitignored — never pushed to GitHub)

> Built an end-to-end ELT analytics pipeline (Zomato-style food delivery data) using PySpark, PostgreSQL, dbt, Apache Doris, and Airflow, processing 51.7K real restaurants and 1.3M+ parsed reviews; cut warehouse load time from 20+ min to 6.6s by replacing batched INSERTs with native COPY, and fixed a Spark memory bug that cut transform runtime by ~65% (9 min → 2.5 min)
