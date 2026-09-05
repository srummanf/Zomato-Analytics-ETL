# Walkthrough — Running Every File Yourself

This doc is a **hands-on demo script**. Follow it top to bottom on a fresh
checkout and you'll go from "empty folder" to "full dashboard with real
data" — the same order a professor would want to see in a live demo.

Every command assumes you're in the project root (the folder with
`docker-compose.yml` in it) unless stated otherwise.

---

## 0. One-time setup

```bash
# Python 3.11 specifically — see README's Known Issues for why not 3.12
python -m venv .venv
.venv/Scripts/activate          # Windows
# source .venv/bin/activate     # macOS/Linux

pip install -r requirements.txt
```

You'll also need Kaggle API credentials once:
`~/.kaggle/kaggle.json`, or set `KAGGLE_USERNAME`/`KAGGLE_KEY` (see
`.env.example`).

---

## 1. `01_download_data.py` — get the real dataset

```bash
python 01_download_data.py
```

**What you should see:**
```
Downloaded to kagglehub cache: C:\Users\...\.cache\kagglehub\...
Copied to data\raw_restaurants.csv
```

Run it again and it'll just say `Already downloaded` — it's a one-time step,
by design. Check the file landed:

```bash
wc -l data/raw_restaurants.csv   # should be tens of thousands of lines
```

---

## 2. `03_profile_data.py` — look before you clean

```bash
python 03_profile_data.py
```

**What you should see:** a printout of null counts per column, sample
"messy" values in `rate`/`approx_cost(for two people)`/`cuisines`/`phone`.
This is exploratory — nothing gets written to disk. Read the output; it's
*why* the rules in the next step exist.

---

## 3. `02_generate_synthetic_data.py` — invent one day of transactions

```bash
python 02_generate_synthetic_data.py --date 2026-01-01
```

**What you should see:**
```
Generated 500 orders for 2026-01-01 (1252 items, 500 payments, 474 deliveries)
```

Run it again with a **different** date and watch the row counts in
`data/raw_orders.csv` grow (it appends, not overwrites) — try:

```bash
python 02_generate_synthetic_data.py --date 2026-01-02
wc -l data/raw_orders.csv   # bigger than before
```

`data/raw_customers.csv`, on the other hand, will look identical every time
— it's regenerated fresh from a fixed random seed on purpose (a stable
"dimension" without needing a does-this-exist check).

---

## 4. `04_validate_data.py` — the gatekeeper

```bash
python 04_validate_data.py
```

**What you should see:**
```
restaurants: 51717 valid, 0 rejected (0.00%)
customers: 5000 valid, 0 rejected (0.00%)
orders: 900 valid, 0 rejected (0.00%)
order_items: 2248 valid, 0 rejected (0.00%)
payments: 900 valid, 0 rejected (0.00%)
deliveries: 861 valid, 0 rejected (0.00%)

All entities within rejection rate threshold.
```

Check what got written:

```bash
ls data/valid_*.csv data/rejected_*.csv
```

**To see the failure path on purpose:** open `data/raw_orders.csv`, set one
row's amount column to a negative number, save, and rerun. You'll see that
row show up in `data/rejected_orders.csv` with `reject_reason =
non_positive_order_total` — and if you corrupt enough rows to cross 2%, the
script exits with code 1 instead of printing "All entities within
threshold."

> This step also writes to Postgres (`pipeline_validation_runs`) — but only
> if Postgres is already running. If you haven't started Docker yet (next
> section), this step will error trying to connect. That's expected at this
> point in the walkthrough; just bring up Docker first if you want this part
> to succeed too.

---

## 5. Bring up the infrastructure

```bash
docker compose up -d
docker compose ps   # wait until all 4 show "healthy" (or "Up" for airflow)
```

| Service | URL | Login |
|---|---|---|
| Airflow | http://localhost:8080 | see `doc/PASSWORD.md` |
| Metabase | http://localhost:3030 | see `doc/PASSWORD.md` |

First boot builds the `airflow` image (bundles PySpark's JVM + dbt), which
takes a minute or two.

---

## 6. `05_transform_data.py` — PySpark, inside the container

PySpark needs a JVM and (on Windows) some annoying native setup — that's
already handled inside the `airflow` container, so run it there:

```bash
docker compose exec airflow bash -c "cd /opt/project && python 05_transform_data.py"
```

**What you should see** (takes ~2–3 minutes, mostly spent on the reviews
table):
```
Wrote /opt/project/data/clean_restaurants.csv (51717 rows)
Wrote /opt/project/data/clean_restaurant_cuisines.csv (126819 rows)
Wrote /opt/project/data/clean_reviews.csv
Wrote /opt/project/data/clean_customers.csv (5000 rows)
Wrote /opt/project/data/clean_orders.csv (900 rows)
Wrote /opt/project/data/clean_order_items.csv (2248 rows)
Wrote /opt/project/data/clean_payments.csv (900 rows)
Wrote /opt/project/data/clean_deliveries.csv (861 rows)
```

If this instead takes 5–9+ minutes or the container seems to hang, see the
README's Known Issues — that used to be a real memory bug, now fixed.

---

## 7. `06_load_postgres.py` — bulk load into staging

```bash
docker compose exec airflow bash -c "cd /opt/project && python 06_load_postgres.py"
```

**What you should see** (this should be *fast* — a handful of seconds):
```
stg_restaurants: 51717 rows loaded from clean_restaurants.csv
...
stg_reviews: 1320051 rows loaded from clean_reviews.csv
```

Peek at the result yourself:

```bash
docker exec dataetl-postgres-1 psql -U zomato -d zomato -c "\dt"
docker exec dataetl-postgres-1 psql -U zomato -d zomato -c "SELECT COUNT(*) FROM stg_orders;"
```

---

## 8. dbt — build and test the star schema

```bash
docker compose exec airflow bash -c "cd /opt/project/dbt_project && dbt run"
docker compose exec airflow bash -c "cd /opt/project/dbt_project && dbt test"
```

**`dbt run`** should report `Completed successfully` with 13 models built.
**`dbt test`** should report `PASS=37 WARN=0 ERROR=0 SKIP=0 TOTAL=37`.

If a test fails, dbt tells you exactly which one and gives you a compiled
SQL query you can run yourself to see the offending rows — that's the whole
point of `dbt test` over a hand-rolled assertion script.

---

## 9. `07_record_dbt_test_results.py` — log the test outcome

```bash
docker compose exec airflow bash -c "cd /opt/project && python 07_record_dbt_test_results.py"
```

**What you should see:**
```
Recorded dbt test run: 37/37 passed
```

This reads `dbt_project/target/run_results.json` (dbt's own output from the
`dbt test` you just ran) and appends a row to Postgres — this is what
"dbt Tests (latest run)" on the Pipeline Health dashboard is actually
reading.

---

## 10. `08_load_doris.py` — populate the warehouse

```bash
docker compose exec airflow bash -c "cd /opt/project && python 08_load_doris.py"
```

**What you should see:**
```
dim_location: 93 rows loaded from dim_location
dim_cuisine: 107 rows loaded from dim_cuisine
dim_restaurant: 51717 rows loaded from dim_restaurant
...
fact_reviews: 1320051 rows loaded from fact_reviews
```

Verify with a MySQL client (Doris speaks the MySQL wire protocol):

```bash
mysql -h 127.0.0.1 -P 9030 -u root -e "USE zomato; SELECT COUNT(*) FROM fact_orders;"
```

---

## 11. `09_dag.py` — do it all again, automatically

Everything from Step 6 onward (`02_generate_synthetic_data.py` through
`08_load_doris.py`) is exactly what Airflow runs for you, daily, once you
unpause the DAG:

```bash
docker compose exec airflow airflow dags unpause zomato_analytics_pipeline
docker compose exec airflow airflow dags trigger zomato_analytics_pipeline
```

Watch it progress:

```bash
docker compose exec airflow airflow tasks states-for-dag-run \
  zomato_analytics_pipeline "scheduled__<todays-date>T00:00:00+00:00"
```

(Airflow auto-creates a `scheduled__...` run once unpaused — you may not
even need `dags trigger`; check `airflow dags list-runs
zomato_analytics_pipeline` first.)

You should see all 7 tasks turn `success` in order, roughly 4–6 minutes
total.

---

## 12. Metabase — see the result

Open **http://localhost:3030**, log in (`doc/PASSWORD.md`), and open **Our
analytics** → any of the 4 dashboards. See `doc/DASHBOARD.md` for what every
chart means.

If you ran Step 11 more than once (or ran Steps 6–10 manually a few times
before that), the numbers will reflect all of that accumulated data — that's
expected, since `02_generate_synthetic_data.py` *appends* new days rather
than replacing old ones.

---

## 13. `10_dash_dashboard.py` — the local Plotly Dash frontend (optional)

Metabase is the "real" BI tool here, but there's also a lightweight local
frontend built with [Dash](https://dash.plotly.com/) that reads the exact
same Postgres/Doris tables and renders the same KPIs in a custom
Zomato-branded UI — dark red sidebar, the real Zomato logo, Poppins font,
hero KPI cards. Good for a quick local look without opening Metabase.

```bash
pip install dash plotly
python 10_dash_dashboard.py
```

Then open **http://127.0.0.1:8050**. It's local-only, no deployment — just a
dev server on your machine, same as any other script in this repo.

**What you should see:** a sidebar with four vertical tabs — Business
Overview, Customer Insights, Delivery & Operations, Pipeline Health — each
showing the same KPI cards and charts as the matching Metabase dashboard
(see `doc/DASHBOARD.md`), just in a different frontend. Data is fetched once
at startup, so re-run the script after loading new data to refresh it.

---

## Cheat sheet — every command in one place

```bash
# One-time
python 01_download_data.py
python 03_profile_data.py

# Local, before Docker is up (or repeat any time to add a new simulated day)
python 02_generate_synthetic_data.py --date 2026-01-01
python 04_validate_data.py

# Bring up infra
docker compose up -d

# Inside the airflow container (has the JVM + dbt)
docker compose exec airflow bash -c "cd /opt/project && python 05_transform_data.py"
docker compose exec airflow bash -c "cd /opt/project && python 06_load_postgres.py"
docker compose exec airflow bash -c "cd /opt/project/dbt_project && dbt run && dbt test"
docker compose exec airflow bash -c "cd /opt/project && python 07_record_dbt_test_results.py"
docker compose exec airflow bash -c "cd /opt/project && python 08_load_doris.py"

# Or let Airflow do all of the above for you, daily
docker compose exec airflow airflow dags unpause zomato_analytics_pipeline
docker compose exec airflow airflow dags trigger zomato_analytics_pipeline

# Optional: local Plotly Dash frontend, alternative to Metabase
pip install dash plotly
python 10_dash_dashboard.py   # open http://127.0.0.1:8050
```
