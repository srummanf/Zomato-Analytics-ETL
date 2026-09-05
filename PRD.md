# PRD — Zomato Analytics ETL

## 1. Overview

An academic data engineering project that builds a local, fully-free, end-to-end
analytics platform modeled on a Zomato-style food-delivery business. The project
combines a real Kaggle restaurant dataset with synthetically generated
transactional data, processes it through a modern ELT stack (extract → validate →
transform → stage → model → warehouse → dashboard), and demonstrates real data
engineering practices: schema-aware ingestion, data quality gating, dimensional
modeling, and orchestrated daily runs — without using any paid cloud service.

## 2. Goals

- Build a working, demonstrable ETL/ELT pipeline covering ingestion, validation,
  transformation, warehousing, and visualization.
- Learn and demonstrate practical experience with PySpark, Apache Airflow, dbt,
  and Apache Doris.
- Produce a dashboard that answers realistic business/customer/delivery/ops
  questions for a food-delivery company.
- Avoid the failure mode of a prior project: catch bad data early instead of
  discovering it after the pipeline is "done."
- Keep the entire stack free and runnable locally via Docker.

## 3. Non-goals

- No real-time/streaming ingestion (Kafka, etc.) in the initial scope — batch/daily
  only. May be considered as a future enhancement (see §10).
- No use of paid cloud infrastructure or managed SaaS data platforms (AWS, GCP,
  Azure, Snowflake, Databricks paid tiers, etc.).
- No multi-city analysis using fabricated city data — the real dataset is
  Bangalore-only, and the project will not misrepresent that.
- No ML/predictive modeling (e.g. delivery time prediction, churn prediction) in
  the initial scope — purely descriptive analytics.

## 4. Users / audience

- **Primary**: the project author (student), both as builder and as the person
  being evaluated academically on the pipeline's design and correctness.
- **Secondary**: an academic evaluator/grader, who will assess the pipeline's
  architecture, data quality handling, and the resulting dashboard.

## 5. Data sources

### 5.1 Real data
- **Source**: Kaggle dataset `rajeshrampure/zomato-dataset` ("Zomato Bangalore
  Restaurants"), downloaded via `kagglehub.dataset_download`. ~500MB.
- **Scope**: restaurant listing data only (no transactional/order data). Bangalore
  city only, despite the presence of a `listed_in(city)` column (which is a
  scrape-region label, not a real city field).
- **Retrieval cadence**: one-time seed download, not part of the daily pipeline run.

### 5.2 Synthetic data
- **Generated with**: Faker.
- **Entities**: customers, orders, order_items, payments, deliveries.
- **Anchoring rule**: synthetic values must stay statistically consistent with
  real restaurant signals — e.g. order values distributed around a restaurant's
  real `approx_cost(for two people)`, order volume weighted by a restaurant's
  real `rate`/`votes` (more popular/higher-rated restaurants get proportionally
  more synthetic orders).
- **Cadence**: regenerated per simulated "day" — this is what gives the daily
  Airflow DAG something meaningful to process on each run.

### 5.3 Data dictionary — raw Kaggle columns → star schema

| Raw column | Target | Required transform |
|---|---|---|
| `name` | `dim_restaurant.restaurant_name` | trim/dedupe |
| `url`, `address` | `dim_restaurant` | pass-through |
| `location` | `dim_location.area` | used as the geography grain (neighborhood, not city) |
| `phone` | *(dropped)* | low analytical value, inconsistent multi-number formatting |
| `rate` | `dim_restaurant.rating` | parse `"4.1/5"` → float; null out `"NEW"`/`"-"` |
| `votes` | `dim_restaurant.vote_count` | numeric, used as popularity weight for synthetic order generation |
| `online_order` | `dim_restaurant.online_order_enabled` | `"Yes"/"No"` → boolean |
| `book_table` | `dim_restaurant.table_booking_enabled` | `"Yes"/"No"` → boolean |
| `rest_type` | `dim_restaurant.restaurant_type` | may contain multiple comma-separated values; take primary or explode if needed |
| `cuisines` | `dim_cuisine` + bridge table | explode comma-separated list into many-to-many relationship |
| `approx_cost(for two people)` | `dim_restaurant.avg_cost_for_two` | strip commas, cast to numeric; also used as anchor for synthetic order amounts |
| `reviews_list` | `fact_reviews` | parse stringified list of (rating, review_text) tuples into real review rows |
| `listed_in(type)` | `dim_restaurant.meal_type` | category (Buffet/Cafes/Delivery/Dine-out/etc.) |
| `listed_in(city)` | *(not used as city)* | scrape-region artifact, not real multi-city data |

## 6. Architecture

See `PROJECT_OVERVIEW.md` for the full Mermaid pipeline diagram and dashboard
wireframe. Summary of the data flow:

```
Kaggle (real restaurants) ─┐
                            ├─→ validate → PySpark transform → Postgres (staging)
Faker (synthetic orders) ──┘                                       │
                                                                    ▼
                                                    dbt (staging → dims → facts) → dbt test
                                                                    │
                                                                    ▼
                                                        Apache Doris (warehouse)
                                                                    │
                                                                    ▼
                                                             Metabase Dashboard

Apache Airflow orchestrates the daily run of: synthetic generation → validate →
transform → load-postgres → dbt run/test → load-doris.
```

## 7. Data model (star schema)

**Fact tables**
- `fact_orders` — one row per order; FKs to customer, restaurant, date, time, location
- `fact_order_items` — one row per line item within an order
- `fact_deliveries` — delivery time, delivery partner, status
- `fact_payments` — payment method, amount, status
- `fact_reviews` — parsed from real `reviews_list`, FK to restaurant

**Dimension tables**
- `dim_customer`, `dim_restaurant`, `dim_delivery_partner`, `dim_location`,
  `dim_date`, `dim_time`, `dim_cuisine` (+ restaurant↔cuisine bridge table)

## 8. Functional requirements

| # | Component | Requirement |
|---|---|---|
| FR1 | `download_data.py` | Download the Kaggle dataset once via `kagglehub`; must not re-download on every run |
| FR2 | `generate_synthetic_data.py` | Generate customers/orders/order_items/payments/deliveries for a given simulated date, anchored to real restaurant signals |
| FR3 | `validate_data.py` | Enforce an explicit schema; reject rows failing schema or business rules (negative amounts, orphaned FKs, invalid timestamps/ratings, duplicate keys) into a quarantine file with a reason code |
| FR4 | `transform_data.py` | PySpark job: clean types, explode `cuisines`/`rest_type`, parse `reviews_list`, derive metrics (`order_total`, `delivery_time`, `customer_order_count`, etc.) |
| FR5 | `load_postgres.py` | Load cleaned/transformed data into Postgres staging tables |
| FR6 | dbt project | Build staging models → dimension models → fact models; enforce not-null/unique/relationship tests |
| FR7 | `load_doris.py` | Load the finished star schema from Postgres/dbt output into Apache Doris |
| FR8 | `dag.py` | Single Airflow DAG orchestrating FR2–FR7 daily |
| FR9 | Metabase dashboard | 4 pages: Business Overview, Customer Insights, Delivery & Operations, Pipeline Health (see `PROJECT_OVERVIEW.md` wireframe) |
| FR10 | Pipeline health monitoring | Track and surface rows ingested, rows rejected, rejection rate, and dbt test pass/fail counts per run |

## 9. Non-functional requirements

- **Cost**: $0. No paid cloud services or SaaS tiers at any point.
- **Data quality gate**: pipeline run must fail (not silently continue) if the
  rejection rate for any entity exceeds a defined threshold (default: 2%).
- **Reproducibility**: the full stack must be startable via `docker-compose up`
  with no manual per-service configuration beyond credentials/env vars.
- **Scale**: must comfortably handle the ~500MB real dataset plus a growing
  volume of daily synthetic data without loading the full dataset into memory
  via Pandas (PySpark handles the real ingestion/transform path).
- **Simplicity**: flat file/script structure (see `CLAUDE.md`), no premature
  abstraction, no dependencies beyond what's actively used.

## 10. Out of scope / future enhancements

- Streaming ingestion via Kafka (order events as a live feed) — would sit
  alongside the existing batch synthetic-data step rather than replace it.
- Multi-city simulation — deliberately rejected in favor of honest single-city
  (Bangalore, neighborhood-level) analysis.
- ML-based forecasting or recommendation features on top of the warehouse.
- Great Expectations for data quality — deliberately dropped in favor of dbt
  tests alone, to avoid redundant tooling for this scope.

## 11. Risks & mitigations

| Risk | Mitigation |
|---|---|
| `dbt-doris` community adapter may be immature/buggy | Verify early with a trivial model; fall back to plain SQL load scripts against Doris if needed |
| Encoding/malformed values in scraped Kaggle data (`rate`, `approx_cost`, non-UTF8 text) | Data profiling pass before finalizing schema; explicit schema + permissive read mode with corrupt-record capture |
| Synthetic data feels unrealistic if not properly anchored | Weight synthetic order generation by real `rate`/`votes`/`approx_cost` signals |
| Doris self-hosting complexity (FE/BE nodes, resource usage) | Validate Docker Compose setup early in a spike before building dependent steps on top of it |
| Bad data silently breaking the pipeline late (prior project's failure mode) | Explicit schemas, quarantine tables, rejection-rate gate in the DAG (FR3, FR10) |

## 12. Acceptance criteria

- `docker-compose up` brings up Postgres, Airflow, Doris, and Metabase with no
  manual intervention beyond initial credentials.
- The Airflow DAG runs end-to-end daily without manual triggering, producing
  fresh synthetic data, passing validation/dbt tests, and refreshing Doris.
- All dbt tests pass (or documented, justified exceptions exist).
- Rejection rate stays under the defined threshold on a normal run, and the
  pipeline visibly fails/alerts when it doesn't.
- The Metabase dashboard renders all 4 pages from `PROJECT_OVERVIEW.md` using
  live data from Doris.
- The `cuisines` and `reviews_list` fields are demonstrably used (bridge table
  and real review rows respectively), not discarded.
