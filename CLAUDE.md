
# CLAUDE.md

Reference file for Claude Code (or any AI assistant) working in this repository.

## Project

Zomato Analytics ETL — an academic data engineering project that builds a local,
end-to-end analytics pipeline for a Zomato-style food-delivery business. Real
restaurant data (Kaggle) is combined with synthetic transactional data, cleaned
and modeled through a full ELT stack, and served through a BI dashboard.

Full architecture, pipeline diagram, and dashboard wireframe: see `doc/PROJECT_OVERVIEW.md`.
Detailed requirements, data dictionary, and acceptance criteria: see `doc/PRD.md`.

## Hard constraints

- **No paid cloud, ever.** No AWS/GCP/Azure/Snowflake. Every tool must be free and
  either self-hosted (via Docker) or free-tier-forever. This is a strict academic
  budget constraint, not a preference.
- **Keep the folder structure flat.** One small `.py` script per pipeline step at
  the repo root, no `src/`-style package layout, no shared framework/abstraction
  layer. The only allowed exception is `dbt_project/`, because dbt requires its
  own internal folder layout (`models/`, `tests/`, etc.).
- **Keep scripts minimal.** Each script does one job. Don't add abstractions,
  config layers, or error handling for scenarios that can't happen. Don't build
  for hypothetical future requirements — add shared code only once duplication
  actually becomes a real problem, not preemptively.
- **Data quality is front-loaded, not bolted on.** A prior project of the user's
  broke down at the end because of bad data. Always: use explicit schemas (never
  blind `inferSchema`), use defensive/permissive read modes, quarantine invalid
  rows with a reason code instead of silently dropping or crashing on them, and
  gate the pipeline on a rejection-rate threshold rather than letting bad data
  flow downstream silently.
- **Plan before code.** When the user is discussing or exploring ideas, stay in
  discussion mode — propose options, ask clarifying questions, don't scaffold
  files or write pipeline code. Only implement once explicitly told to build.

## Tech stack


| Layer               | Technology                                                                            |
| --------------------- | --------------------------------------------------------------------------------------- |
| Language            | Python                                                                                |
| Real data source    | Kaggle`rajeshrampure/zomato-dataset` via `kagglehub` (~500MB, one-time seed download) |
| Synthetic data      | Faker (orders, customers, order items, payments, deliveries)                          |
| Transform           | PySpark                                                                               |
| Staging store       | PostgreSQL                                                                            |
| Warehouse modeling  | dbt Core                                                                              |
| Analytics warehouse | Apache Doris (chosen over Snowflake to avoid trial expiry and stay fully free)        |
| Orchestration       | Apache Airflow (daily DAG)                                                            |
| Dashboard           | Metabase                                                                              |
| Containers          | Docker / Docker Compose                                                               |
| Version control     | Git + GitHub                                                                          |

## Known risks to keep in mind

- `dbt-doris` is a community-maintained adapter (Doris speaks MySQL wire protocol) —
  unverified maturity. If it proves too rough, fall back to plain SQL scripts
  against Doris instead of dbt models.
- The Kaggle dataset is Bangalore-only; `listed_in(city)` is a scrape-region
  label within Bangalore, not a real multi-city field. Geography analysis uses
  `location` (neighborhood), not city — don't reintroduce fake multi-city data.
- `reviews_list` contains real (rating, review_text) tuples — parse these for
  review data instead of fully synthesizing reviews.

## Current status

Fully implemented and verified end-to-end (all 10 pipeline steps, 4 Metabase
dashboards, a local Plotly Dash frontend). See `README.md` for the current
project status table and `doc/PROJECT_OVERVIEW.md` / `doc/PRD.md` for the
original architecture and requirements this was built against.
