# Dashboard Guide

This doc explains **what's on the Metabase dashboard, why each chart exists,
and how to read it** — written for someone seeing this project for the first
time, not for someone who already knows what a "repeat rate" metric means.

Open it yourself at **http://localhost:3030** (see `doc/PASSWORD.md` for the
login) and follow along.

---

## Why a dashboard at all?

A pipeline that cleans data and loads it into a warehouse is only half the
job — nobody in a real business opens a SQL client to check "how much money
did we make yesterday." A **BI (Business Intelligence) dashboard** turns raw
tables into charts a non-technical person can glance at and understand in
five seconds. That's the entire job of Metabase in this project: it sits on
top of Apache Doris (our warehouse) and PostgreSQL (our pipeline-health
tables) and turns SQL queries into visuals.

## Why 4 separate dashboards instead of 1 giant one?

Different people care about different things, and cramming everything onto
one page just makes all of it harder to read:

| Dashboard | Who'd actually look at this |
|---|---|
| **Business Overview** | A founder/manager asking "how's the business doing?" |
| **Customer Insights** | Marketing/growth, asking "who are our customers and are they coming back?" |
| **Delivery & Operations** | Ops team, asking "are deliveries going well?" |
| **Pipeline Health** | You (the data engineer), asking "did last night's pipeline run actually work?" |

This is a standard pattern in real BI tooling — you'll see the same
"one dashboard per audience" idea in Tableau, Power BI, Looker, etc.

---

## Chart types used, and when each one makes sense

Before going page by page, it helps to know *why* a given card is a number,
a bar chart, a line chart, or a table — Metabase calls these
"visualizations," and picking the right one is half the job of building a
useful dashboard:

- **Scalar (a big single number)** — for a single headline metric you want
  someone to see instantly, no interpretation needed. e.g. "Total Orders: 2,283".
- **Line chart** — for a metric measured *over time*, where the trend
  (going up? down? flat?) matters more than any single value.
- **Bar chart** — for comparing a metric *across categories* (areas,
  cuisines, hours of the day) where you want to rank or compare, not track
  time.
- **Table** — when you need more than one number per row (e.g. a restaurant's
  order count *and* revenue *and* name together), or when the raw rows
  themselves are the useful output (a leaderboard).

Keep this in mind as you read below — it's why, say, "Revenue Trend" is a
line and "Top Restaurants" is a table, not the other way around.

---

## Page 1 — Business Overview

The "how's the business doing" page. All queries here run against **Apache
Doris** (`fact_orders`, `dim_restaurant`, `dim_location`, `dim_cuisine`,
`bridge_restaurant_cuisine`).

### Total Orders (scalar)
Count of all orders with `order_status = 'Delivered'`. We deliberately
exclude cancelled orders — a cancelled order isn't really "business done,"
so counting it would overstate how much the platform is actually delivering.

### Total Revenue (scalar)
`SUM(order_total)` for delivered orders only, same reasoning as above — a
cancelled order's `order_total` was never actually collected.

### Avg Order Value (scalar)
`AVG(order_total)` for delivered orders. Also called **AOV** in e-commerce —
one of the most-watched metrics in any delivery/e-commerce business, because
it tells you whether people are ordering small snacks or full family meals.

### Active Restaurants (scalar)
`COUNT(DISTINCT restaurant_id)` from `fact_orders` — i.e. restaurants that
received *at least one order*, not just every restaurant in the Kaggle
dataset (most of which never got a synthetic order at all).

### Revenue Trend (line chart)
Daily revenue, `SUM(order_total)` grouped by `date_id`. Since our synthetic
data generator (`02_generate_synthetic_data.py`) adds one new simulated day
every time it runs, this line naturally grows a new data point per pipeline
run — exactly what you'd want in a real daily-DAG business.

### Orders by Area (bar chart)
Order count grouped by `dim_location.area` (the restaurant's neighborhood),
top 10. This answers "which parts of Bangalore are we strongest in?" —
useful for deciding where to add more delivery partners.

### Top Cuisines by Order Volume (bar chart)
Order count grouped by cuisine, via the `bridge_restaurant_cuisine` table
(a restaurant can have multiple cuisines, so this is a many-to-many join,
not a simple `GROUP BY` on one column).

### Top Restaurants (table)
Restaurant name, order count, and revenue, sorted by revenue, top 10 — a
classic leaderboard. This is a table (not a bar chart) specifically because
we want *two* numbers side by side (orders **and** revenue) per restaurant,
which a single bar chart can't show cleanly.

---

## Page 2 — Customer Insights

The "who's buying, and are they loyal?" page. Also queries Doris
(`dim_customer`, `fact_orders`, `fact_payments`).

### Total Customers (scalar)
Every row in `dim_customer` — including the ones who signed up but never
ordered. (Compare this to "Active Restaurants" above, which *does* filter
to only the ones with activity — the two metrics are asking different
questions on purpose.)

### New Customers (30d) (scalar)
`COUNT(*)` where `signup_date` is within the last 30 days. A classic growth
metric — is the customer base still growing, or flat?

### Repeat Rate (scalar)
Of the customers who ordered **at least once**, what percentage ordered
**more than once**? This is the single most important loyalty metric for
any delivery app — acquiring a customer is expensive, so what matters is
whether they come back.

```sql
ROUND(100.0 * SUM(CASE WHEN customer_order_count > 1 THEN 1 ELSE 0 END)
    / NULLIF(SUM(CASE WHEN customer_order_count >= 1 THEN 1 ELSE 0 END), 0), 1)
```
(The `NULLIF(..., 0)` guards against a divide-by-zero if literally nobody
has ordered yet.)

### Avg Orders per Customer (scalar)
`AVG(customer_order_count)`, only among customers who've ordered at least
once (so a customer with zero orders doesn't drag the average down and hide
how loyal your *actual* customers are).

### Customer Value Tiers (table)
Every customer is bucketed into **No orders / Low / Mid / High value**
based on their lifetime spend, with a customer count and total revenue per
tier. This is the exact same idea as **RFM segmentation** used everywhere
in marketing analytics (Recency/Frequency/**M**onetary — we're only doing
the "M" part here, keeping it simple). It typically reveals the classic
80/20 pattern: a small "High value" group contributing a disproportionate
share of revenue.

### Orders by Payment Method (bar chart)
Order count grouped by `payment_method` (UPI, Card, Cash on Delivery,
Wallet) — useful for a payments/finance team deciding where to focus
integration or promo effort.

---

## Page 3 — Delivery & Operations

The "is the operational side working well?" page. Queries Doris
(`fact_deliveries`, `fact_orders`, `dim_restaurant`, `dim_delivery_partner`,
`dim_time`).

### Avg Delivery Time (scalar)
`AVG(delivery_time_minutes)` across all deliveries — the headline number any
delivery ops team lives or dies by.

### Cancellation Rate (scalar)
Percentage of **all** orders (this time including cancelled ones in the
denominator, on purpose — you need the full set to calculate a rate) with
`order_status = 'Cancelled'`.

### Avg Rating (scalar)
`AVG(rating)` from `dim_restaurant` — this is the *real* Kaggle rating data
for each restaurant, not synthetic.

### On-Time % (scalar)
Percentage of deliveries with `delivery_status = 'Delivered'` (as opposed to
`'Delayed'`) — the flip side of a "late delivery rate."

### Order Volume by Hour of Day (bar chart)
Order count grouped by `hour_id` (0–23). This is the classic "when are we
busiest" chart every restaurant/delivery business needs — usually shows
clear lunch and dinner peaks, which is exactly the kind of pattern you'd use
to schedule delivery partner shifts around.

### Delivery Partner Leaderboard (table)
Each delivery partner's total deliveries and average delivery time, sorted
by delivery count, top 10 — same "leaderboard needs a table" logic as
"Top Restaurants" above.

### Online Order Enabled vs Not (table)
Compares average order value and order count between restaurants that do
vs. don't support online ordering (`dim_restaurant.online_order_enabled`) —
a quick way to see whether enabling online ordering actually correlates
with bigger or more frequent orders.

---

## Page 4 — Pipeline Health

The "did the pipeline actually run correctly?" page — and the odd one out:
it queries **PostgreSQL**, not Doris, because this is monitoring data about
the pipeline itself, not business data about restaurants and orders. See
`04_validate_data.py` and `07_record_dbt_test_results.py` for where these
numbers come from.

### Rows Ingested (latest run) (scalar)
`total_valid + total_rejected` from the most recent row in
`pipeline_validation_runs` — how many raw records the last pipeline run
processed, in total.

### Rejected Rows (latest run) (scalar)
`total_rejected` from that same latest row — how many of those records
failed a validation rule (see `04_validate_data.py` for the exact rules:
missing keys, orphaned foreign keys, non-positive amounts, duplicates).

### Rejection Rate (latest run) (scalar)
The rejected fraction as a percentage. `04_validate_data.py` will actually
**fail the whole pipeline run** (`sys.exit(1)`) if any single entity's
rejection rate goes over 2% — this card is the visual version of that same
threshold. If this number is ever surprisingly high, go check
`data/rejected_*.csv` for the `reject_reason` column.

### dbt Tests (latest run) (scalar)
`passed/total` from the most recent `dbt test` run (e.g. `37/37`) — a
quick "did the data model hold up?" check. This includes every `not_null`,
`unique`, and `relationships` test defined in `dbt_project/models/schema.yml`.

### Rejection Rate Trend (line chart)
Rejection rate over time, one point per pipeline run. In a real production
system this is the chart you'd put an alert on — a sudden spike means
something upstream (a source system, an API, a schema change) broke.

---

## Where to look next

- **`doc/FLOWCHART.md`** — how data actually gets from Kaggle/Faker into
  these charts, step by step.
- **`doc/WALKTHROUGH.md`** — exact commands to run the pipeline yourself and
  see these numbers populate/change.
