"""Step 10 (alternative frontend) — a local Plotly Dash dashboard.

Reads the exact same KPIs and charts the 4 Metabase dashboards show (see
doc/DASHBOARD.md) straight from Doris and Postgres, and renders them with a
Zomato-red "Zomato ETL Analytics" design system based on doc/COMPONENTS.md
(three-column app shell, Be Vietnam Pro, Eva icons). The per-component CSS
lives in assets/style.css; icons in assets/icons/.

This is a standalone tool, not part of the daily Airflow DAG — it's meant to
be run by hand, locally, whenever you want to look at the current numbers.

Local only, no deployment:
    pip install dash plotly
    python 10_dash_dashboard.py
    # then open http://127.0.0.1:8050
"""
import os
import warnings
from datetime import datetime

import pandas as pd
import psycopg2
import pymysql
import plotly.express as px
from dash import Dash, Input, Output, ctx, dcc, html
from dotenv import load_dotenv

load_dotenv()
warnings.filterwarnings("ignore", message="pandas only supports SQLAlchemy")

# ---------------------------------------------------------------------------
# Config — same env vars, same defaults, as every other script in this repo
# ---------------------------------------------------------------------------

PG_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": os.getenv("POSTGRES_PORT", "5439"),
    "dbname": os.getenv("POSTGRES_DB", "zomato"),
    "user": os.getenv("POSTGRES_USER", "zomato"),
    "password": os.getenv("POSTGRES_PASSWORD", "zomato"),
}

DORIS_CONFIG = {
    "host": os.getenv("DORIS_HOST", "localhost"),
    "port": int(os.getenv("DORIS_QUERY_PORT", "9030")),
    "user": os.getenv("DORIS_USER", "root"),
    "password": os.getenv("DORIS_PASSWORD", ""),
    "database": os.getenv("DORIS_DB", "zomato"),
}

# ---------------------------------------------------------------------------
# Theme — tokens mirror assets/style.css / doc/COMPONENTS.md
# ---------------------------------------------------------------------------

GRAY_600 = "#3a2a2d"
ZOMATO = "#e23744"
RED_BRIGHT = "#ff5964"
AMBER = "#ff9f45"
FONT_FAMILY = '"Be Vietnam Pro", "Helvetica Neue", Arial, sans-serif'
CHART_COLORS = ["#e23744", "#ff8a5c", "#ffc24b", "#c8506b", "#8e2b3f", "#ff5964", "#f5a3ac"]

MAIN_CHART_H = 340
SIDE_CHART_H = 230


def style_fig(fig, height=MAIN_CHART_H):
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#f1f1f1", family=FONT_FAMILY, size=12),
        margin=dict(l=12, r=12, t=10, b=10),
        height=height,
        showlegend=False,
        colorway=CHART_COLORS,
    )
    fig.update_xaxes(gridcolor=GRAY_600, zerolinecolor=GRAY_600, title=None)
    fig.update_yaxes(gridcolor=GRAY_600, zerolinecolor=GRAY_600, title=None)
    return fig


# ---------------------------------------------------------------------------
# Data access
# ---------------------------------------------------------------------------

def query_doris(sql):
    with pymysql.connect(**DORIS_CONFIG) as conn:
        return pd.read_sql(sql, conn)


def query_pg(sql):
    with psycopg2.connect(**PG_CONFIG) as conn:
        return pd.read_sql(sql, conn)


def scalar(df, col, default=0):
    if df.empty or pd.isna(df[col].iloc[0]):
        return default
    return df[col].iloc[0]


# ---------------------------------------------------------------------------
# Section 1: Business Overview (Doris)
# ---------------------------------------------------------------------------

def fetch_business_overview():
    orders = scalar(query_doris(
        "SELECT COUNT(*) AS v FROM fact_orders WHERE order_status = 'Delivered'"), "v")
    revenue = scalar(query_doris(
        "SELECT SUM(order_total) AS v FROM fact_orders WHERE order_status = 'Delivered'"), "v")
    aov = scalar(query_doris(
        "SELECT AVG(order_total) AS v FROM fact_orders WHERE order_status = 'Delivered'"), "v")
    active_restaurants = scalar(query_doris(
        "SELECT COUNT(DISTINCT restaurant_id) AS v FROM fact_orders"), "v")

    revenue_trend = query_doris("""
        SELECT date_id AS order_date, SUM(order_total) AS revenue
        FROM fact_orders WHERE order_status = 'Delivered'
        GROUP BY date_id ORDER BY date_id
    """)
    orders_by_area = query_doris("""
        SELECT l.area, COUNT(*) AS orders
        FROM fact_orders o
        JOIN dim_restaurant r ON r.restaurant_id = o.restaurant_id
        JOIN dim_location l ON l.location_id = r.location_id
        GROUP BY l.area ORDER BY orders DESC LIMIT 10
    """)
    top_cuisines = query_doris("""
        SELECT c.cuisine, COUNT(*) AS orders
        FROM fact_orders o
        JOIN bridge_restaurant_cuisine b ON b.restaurant_id = o.restaurant_id
        JOIN dim_cuisine c ON c.cuisine_id = b.cuisine_id
        GROUP BY c.cuisine ORDER BY orders DESC LIMIT 10
    """)
    top_restaurants = query_doris("""
        SELECT r.restaurant_name AS restaurant, COUNT(*) AS orders, SUM(o.order_total) AS revenue
        FROM fact_orders o
        JOIN dim_restaurant r ON r.restaurant_id = o.restaurant_id
        WHERE o.order_status = 'Delivered'
        GROUP BY r.restaurant_name ORDER BY revenue DESC LIMIT 10
    """)
    top_restaurants["revenue"] = top_restaurants["revenue"].round(2)

    return {
        "title": "Business Overview",
        "subtitle": "Orders, revenue and where demand is coming from",
        "kpis": [
            ("shopping-bag", "Total Orders", "Delivered", f"{orders:,.0f}"),
            ("credit-card", "Total Revenue", "Delivered orders", f"₹{revenue:,.0f}"),
            ("trending-up", "Avg Order Value", "Per delivered order", f"₹{aov:,.2f}"),
            ("home", "Active Restaurants", "With >= 1 order", f"{active_restaurants:,.0f}"),
        ],
        "charts": [
            ("Revenue trend", "Delivered ₹", px.line(
                revenue_trend, x="order_date", y="revenue", markers=True,
                color_discrete_sequence=[ZOMATO])),
            ("Orders by area", "Top 10", px.bar(
                orders_by_area, x="area", y="orders", color="area",
                color_discrete_sequence=CHART_COLORS)),
            ("Top cuisines", "By order volume", px.bar(
                top_cuisines, x="cuisine", y="orders", color="cuisine",
                color_discrete_sequence=CHART_COLORS)),
        ],
        "tables": [("Latest restaurant performance", "Top restaurants by revenue", top_restaurants)],
    }


# ---------------------------------------------------------------------------
# Section 2: Customer Insights (Doris)
# ---------------------------------------------------------------------------

def fetch_customer_insights():
    total_customers = scalar(query_doris("SELECT COUNT(*) AS v FROM dim_customer"), "v")
    new_customers = scalar(query_doris(
        "SELECT COUNT(*) AS v FROM dim_customer WHERE signup_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)"), "v")
    repeat_rate = scalar(query_doris("""
        SELECT ROUND(100.0 * SUM(CASE WHEN customer_order_count > 1 THEN 1 ELSE 0 END)
            / NULLIF(SUM(CASE WHEN customer_order_count >= 1 THEN 1 ELSE 0 END), 0), 1) AS v
        FROM dim_customer
    """), "v")
    avg_orders = scalar(query_doris(
        "SELECT ROUND(AVG(customer_order_count), 2) AS v FROM dim_customer WHERE customer_order_count >= 1"), "v")

    value_tiers = query_doris("""
        WITH spend AS (
            SELECT c.customer_id, COALESCE(SUM(o.order_total), 0) AS lifetime_spend
            FROM dim_customer c
            LEFT JOIN fact_orders o ON o.customer_id = c.customer_id AND o.order_status = 'Delivered'
            GROUP BY c.customer_id
        )
        SELECT
            CASE
                WHEN lifetime_spend = 0 THEN 'No orders'
                WHEN lifetime_spend >= 5000 THEN 'High value'
                WHEN lifetime_spend >= 1500 THEN 'Mid value'
                ELSE 'Low value'
            END AS value_tier,
            COUNT(*) AS customers,
            SUM(lifetime_spend) AS tier_revenue
        FROM spend
        GROUP BY value_tier
    """)
    by_payment = query_doris("""
        SELECT payment_method, COUNT(*) AS orders
        FROM fact_payments GROUP BY payment_method ORDER BY orders DESC
    """)
    new_by_day = query_doris("""
        SELECT signup_date, COUNT(*) AS new_customers
        FROM dim_customer
        WHERE signup_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
        GROUP BY signup_date ORDER BY signup_date
    """)

    return {
        "title": "Customer Insights",
        "subtitle": "Who is ordering and how often they come back",
        "kpis": [
            ("people", "Total Customers", "All time", f"{total_customers:,.0f}"),
            ("person-add", "New Customers", "Last 30 days", f"{new_customers:,.0f}"),
            ("refresh", "Repeat Rate", "More than 1 order", f"{repeat_rate:.1f}%"),
            ("pie-chart", "Avg Orders / Customer", "Among buyers", f"{avg_orders:.2f}"),
        ],
        "charts": [
            ("Orders by payment method", "Count", px.bar(
                by_payment, x="payment_method", y="orders", color="payment_method",
                color_discrete_sequence=CHART_COLORS)),
            ("New customers", "Last 30 days", px.line(
                new_by_day, x="signup_date", y="new_customers", markers=True,
                color_discrete_sequence=[ZOMATO])),
        ],
        "tables": [("Customer value tiers", "By lifetime spend", value_tiers)],
    }


# ---------------------------------------------------------------------------
# Section 3: Delivery & Operations (Doris)
# ---------------------------------------------------------------------------

def fetch_delivery_operations():
    avg_delivery = scalar(query_doris(
        "SELECT ROUND(AVG(delivery_time_minutes), 1) AS v FROM fact_deliveries"), "v")
    cancellation_rate = scalar(query_doris(
        "SELECT ROUND(100.0 * SUM(CASE WHEN order_status = 'Cancelled' THEN 1 ELSE 0 END) / COUNT(*), 2) AS v FROM fact_orders"), "v")
    avg_rating = scalar(query_doris(
        "SELECT ROUND(AVG(rating), 2) AS v FROM dim_restaurant WHERE rating IS NOT NULL"), "v")
    on_time_pct = scalar(query_doris(
        "SELECT ROUND(100.0 * SUM(CASE WHEN delivery_status = 'Delivered' THEN 1 ELSE 0 END) / COUNT(*), 1) AS v FROM fact_deliveries"), "v")

    by_hour = query_doris("""
        SELECT hour_id, COUNT(*) AS orders FROM fact_orders GROUP BY hour_id ORDER BY hour_id
    """)
    delivery_buckets = query_doris("""
        SELECT
            CASE
                WHEN delivery_time_minutes < 20 THEN '< 20 min'
                WHEN delivery_time_minutes < 30 THEN '20–30 min'
                WHEN delivery_time_minutes < 45 THEN '30–45 min'
                ELSE '45+ min'
            END AS bucket,
            COUNT(*) AS deliveries
        FROM fact_deliveries
        GROUP BY bucket ORDER BY bucket
    """)
    leaderboard = query_doris("""
        SELECT dp.delivery_partner_name AS partner, COUNT(*) AS deliveries,
               ROUND(AVG(d.delivery_time_minutes), 1) AS avg_minutes
        FROM fact_deliveries d
        JOIN dim_delivery_partner dp ON dp.delivery_partner_id = d.delivery_partner_id
        GROUP BY dp.delivery_partner_name ORDER BY deliveries DESC LIMIT 10
    """)
    online_vs_not = query_doris("""
        SELECT r.online_order_enabled AS online_order_enabled,
               ROUND(AVG(o.order_total), 2) AS avg_order_value, COUNT(*) AS orders
        FROM fact_orders o
        JOIN dim_restaurant r ON r.restaurant_id = o.restaurant_id
        WHERE o.order_status = 'Delivered'
        GROUP BY r.online_order_enabled
    """)

    return {
        "title": "Delivery & Operations",
        "subtitle": "Delivery speed, reliability and partner performance",
        "kpis": [
            ("clock", "Avg Delivery Time", "End to end", f"{avg_delivery:.1f} min"),
            ("close-circle", "Cancellation Rate", "All orders", f"{cancellation_rate:.2f}%"),
            ("star", "Avg Rating", "Restaurants", f"{avg_rating:.2f}"),
            ("checkmark-circle", "On-Time %", "Deliveries", f"{on_time_pct:.1f}%"),
        ],
        "charts": [
            ("Order volume by hour", "Hour of day", px.bar(
                by_hour, x="hour_id", y="orders", color_discrete_sequence=[ZOMATO])),
            ("Delivery time distribution", "All deliveries", px.bar(
                delivery_buckets, x="bucket", y="deliveries", color="bucket",
                color_discrete_sequence=CHART_COLORS)),
        ],
        "tables": [
            ("Delivery partner leaderboard", "Top partners by volume", leaderboard),
            ("Online order enabled vs not", "Delivered orders", online_vs_not, "table"),
        ],
    }


# ---------------------------------------------------------------------------
# Section 4: Pipeline Health (Postgres)
# ---------------------------------------------------------------------------

def fetch_pipeline_health():
    latest_validation = query_pg(
        "SELECT * FROM pipeline_validation_runs ORDER BY run_at DESC LIMIT 1")
    latest_dbt = query_pg(
        "SELECT * FROM pipeline_dbt_test_runs ORDER BY run_at DESC LIMIT 1")
    trend = query_pg("""
        SELECT run_at, total_valid, total_rejected, rejection_rate
        FROM pipeline_validation_runs ORDER BY run_at
    """)
    dbt_trend = query_pg("""
        SELECT run_at, total_tests, passed_tests
        FROM pipeline_dbt_test_runs ORDER BY run_at
    """)

    total_valid = int(scalar(latest_validation, "total_valid") or 0)
    total_rejected = int(scalar(latest_validation, "total_rejected") or 0)
    rejection_rate = float(scalar(latest_validation, "rejection_rate") or 0)
    total_tests = int(scalar(latest_dbt, "total_tests") or 0)
    passed_tests = int(scalar(latest_dbt, "passed_tests") or 0)
    run_at = scalar(latest_validation, "run_at", default=None)
    pass_rate = (100.0 * passed_tests / total_tests) if total_tests else 0.0

    ingested = trend.assign(ingested=trend["total_valid"] + trend["total_rejected"])

    recent = trend.sort_values("run_at", ascending=False).head(8).copy()
    recent["run"] = pd.to_datetime(recent["run_at"]).dt.strftime("%b %d, %H:%M")
    recent["rejection %"] = (recent["rejection_rate"].astype(float) * 100).round(2).astype(str) + "%"
    recent = recent.rename(columns={"total_valid": "valid", "total_rejected": "rejected"})
    recent = recent[["run", "valid", "rejected", "rejection %"]]

    return {
        "title": "Pipeline Health",
        "subtitle": "Validation rejection rates and dbt test results over time",
        "kpis": [
            ("download", "Rows Ingested", "Latest run", f"{total_valid + total_rejected:,}"),
            ("slash", "Rejected Rows", "Latest run", f"{total_rejected:,}"),
            ("pie-chart", "Rejection Rate", "Latest run", f"{rejection_rate * 100:.2f}%"),
            ("checkmark-circle", "dbt Pass Rate", "Latest run", f"{pass_rate:.0f}%"),
        ],
        "charts": [
            ("Rejection rate trend", "Per run", px.line(
                trend, x="run_at", y="rejection_rate", markers=True,
                color_discrete_sequence=[ZOMATO])),
            ("Rows ingested per run", "Valid + rejected", px.bar(
                ingested, x="run_at", y="ingested", color_discrete_sequence=[ZOMATO])),
            ("dbt tests passed per run", "Out of total", px.line(
                dbt_trend, x="run_at", y="passed_tests", markers=True,
                color_discrete_sequence=[AMBER])),
        ],
        "tables": [("Recent validation runs", "Last 8 runs", recent, "table")],
        "raw": {
            "ingested": total_valid + total_rejected,
            "valid": total_valid,
            "rejected": total_rejected,
            "rejection_rate": rejection_rate,
            "passed": passed_tests,
            "total_tests": total_tests,
            "pass_rate": pass_rate,
            "run_at": run_at,
        },
    }


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def fmt_num(v, col=""):
    if isinstance(v, str):
        return v
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    if isinstance(v, bool):
        return "Yes" if v else "No"
    if col.lower().endswith("_enabled") and v in (0, 1):
        return "Yes" if v == 1 else "No"
    money = any(k in col.lower() for k in ("revenue", "spend", "order_value"))
    try:
        f = float(v)
    except (TypeError, ValueError):
        return str(v)
    if money and abs(f) >= 1000:
        return f"₹{f:,.0f}"
    if f.is_integer():
        return f"{int(f):,}"
    return f"{f:,.2f}"


def label_of(col):
    return col.replace("_", " ").title()


# ---------------------------------------------------------------------------
# Component renderers
# ---------------------------------------------------------------------------

def icon(name, extra=""):
    """An Eva icon (assets/icons/<name>-outline.svg) rendered as a masked span."""
    return html.Span(className=f"ic ic-{name} {extra}".strip())


def tile(ic_name, label, sub, value):
    return html.Article(
        [
            html.Div([
                icon(ic_name, "tile-icon"),
                html.H3([html.Span(label), html.Span(sub)]),
            ], className="tile-header"),
            html.Div(value, className="metric"),
            html.A([html.Span("View analytics"),
                    html.Span(icon("arrow-forward"), className="icon-button")],
                   href="#section-charts"),
        ],
        className="tile",
    )


def chart_card(title, subtitle, fig, height=MAIN_CHART_H):
    return html.Article(
        [
            html.Div([html.H3(title), html.Span(subtitle)], className="chart-card-header"),
            dcc.Graph(figure=style_fig(fig, height), config={"displayModeBar": False},
                      style={"width": "100%", "height": f"{height}px"}),
        ],
        className="chart-card",
    )


def transfer_row(row, cols):
    name = str(row[cols[0]])
    mids = list(cols[1:-1])
    last = cols[-1]
    details = [html.Div([html.Dt(name), html.Dd(label_of(cols[0]))])]
    details += [html.Div([html.Dt(fmt_num(row[c], c)), html.Dd(label_of(c))]) for c in mids]
    return html.Div(
        [
            html.Div((name[:1] or "-").upper(), className="transfer-logo restaurant-logo"),
            html.Dl(details, className="transfer-details"),
            html.Div(fmt_num(row[last], last), className="transfer-number"),
        ],
        className="transfer",
    )


def list_section(title, subtitle, df):
    cols = list(df.columns)
    return html.Section(
        [
            html.Div([
                html.H2(title),
                html.Div(html.P(subtitle), className="filter-options"),
            ], className="transfer-section-header"),
            html.Div([transfer_row(r, cols) for _, r in df.iterrows()], className="transfers"),
        ],
        className="transfer-section",
    )


def data_table(title, subtitle, df):
    return html.Section(
        [
            html.Div([
                html.H2(title),
                html.Div(html.P(subtitle), className="filter-options"),
            ], className="transfer-section-header"),
            html.Table(
                [
                    html.Thead(html.Tr([html.Th(label_of(c)) for c in df.columns])),
                    html.Tbody([
                        html.Tr([html.Td(fmt_num(v, c)) for c, v in zip(df.columns, row)])
                        for row in df.itertuples(index=False)
                    ]),
                ],
                className="data-table",
            ),
        ],
        className="transfer-section",
    )


def render_table_block(spec):
    kind = spec[3] if len(spec) > 3 else "rows"
    title, subtitle, df = spec[0], spec[1], spec[2]
    return data_table(title, subtitle, df) if kind == "table" else list_section(title, subtitle, df)


def render_main(key):
    section = SECTION_BY_KEY[key]
    blocks = [
        html.Section(
            [
                html.Div([
                    html.Div([html.H2(section["title"]), html.P(section["subtitle"])]),
                    html.Span(f"Data as of {NOW}", className="analytics-period"),
                ], className="analytics-section-header"),
                html.Div([tile(i, l, s, v) for i, l, s, v in section["kpis"]], className="tiles"),
                html.Div(
                    [chart_card(t, st, fig) for t, st, fig in section["charts"]],
                    className="charts-grid", id="section-charts",
                ),
            ],
            className="analytics-section",
        ),
    ]
    blocks += [render_table_block(spec) for spec in section["tables"]]
    return blocks


def pipeline_card(kind, tag, headline, h3, value):
    return html.Div(
        [
            html.Div([html.Span(tag), html.Span(headline)], className=f"card {kind}"),
            html.Div([html.H3(h3), html.Div(html.Span(value))], className="payment-details"),
        ],
        className="payment",
    )


def sidebar_cards(view):
    raw = SECTION_BY_KEY["pipeline"]["raw"]
    if view == "dbt":
        failed = raw["total_tests"] - raw["passed"]
        return [
            pipeline_card("green", "PASS", f"{raw['passed']}", "dbt tests passed", f"{raw['passed']}"),
            pipeline_card("olive", "FAIL", f"{failed}", "dbt tests failed", f"{failed}"),
            pipeline_card("gray", "RATE", f"{raw['pass_rate']:.0f}%", "Pass rate",
                          f"{raw['pass_rate']:.0f}%"),
        ]
    return [
        pipeline_card("green", "EXTRACT", f"{raw['ingested']:,}", "Rows ingested",
                      f"{raw['ingested']:,}"),
        pipeline_card("olive", "VALIDATE", f"{raw['rejected']:,}", "Rows rejected",
                      f"{raw['rejected']:,}"),
        pipeline_card("gray", "REJECT", f"{raw['rejection_rate'] * 100:.2f}%", "Rejection rate",
                      f"{raw['rejection_rate'] * 100:.2f}%"),
    ]


def render_sidebar():
    section = SECTION_BY_KEY["pipeline"]
    raw = section["raw"]
    healthy = raw["rejection_rate"] < 0.02
    run_at = raw["run_at"]
    run_at_str = run_at.strftime("%b %d, %H:%M") if hasattr(run_at, "strftime") else "—"

    return html.Div(
        html.Section(
            [
                html.H2("Pipeline Health"),
                html.Div([
                    html.P("Latest ETL pipeline run"),
                    html.Div([
                        html.Button("ETL", id="sidebar-etl", className="card-button active"),
                        html.Button("DBT", id="sidebar-dbt", className="card-button"),
                    ]),
                ], className="payment-section-header"),
                dcc.Store(id="sidebar-view", data="etl"),
                html.Div(sidebar_cards("etl"), id="sidebar-cards", className="payments"),
                html.Div([
                    html.P("Data quality summary"),
                    html.Div([html.Label("Valid rows"), html.Strong(f"{raw['valid']:,}")],
                             className="quality-row"),
                    html.Div([html.Label("Rejected rows"), html.Strong(f"{raw['rejected']:,}")],
                             className="quality-row"),
                    html.Div([html.Label("Rejection rate"),
                              html.Strong(f"{raw['rejection_rate'] * 100:.2f}%")],
                             className="quality-row"),
                    html.Div([html.Label("dbt pass rate"),
                              html.Strong(f"{raw['pass_rate']:.0f}%")],
                             className="quality-row"),
                ], className="faq"),
                chart_card(*section["charts"][0][:2], section["charts"][0][2], height=SIDE_CHART_H),
                html.Div([
                    html.Button("Healthy" if healthy else "Degraded",
                                className="save-button" if healthy else "save-button warn"),
                    html.Span(f"Last run: {run_at_str}", className="settings-button"),
                ], className="payment-section-footer"),
            ],
            className="payment-section",
        ),
        className="app-body-sidebar",
    )


# ---------------------------------------------------------------------------
# Data + app
# ---------------------------------------------------------------------------

SECTION_BY_KEY = {
    "overview": fetch_business_overview(),
    "customers": fetch_customer_insights(),
    "operations": fetch_delivery_operations(),
    "pipeline": fetch_pipeline_health(),
}
NOW = datetime.now().strftime("%b %d, %Y  %H:%M")

TABS = [("overview", "Overview"), ("customers", "Customers"),
        ("operations", "Operations"), ("pipeline", "Pipeline")]
NAV_ITEMS = [("overview", "Dashboard", "grid"), ("customers", "Customers", "people"),
             ("operations", "Operations", "flash"), ("pipeline", "Pipeline Health", "activity")]

app = Dash(__name__, external_stylesheets=[
    "https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@300;400;500;600;700&display=swap",
])
app.title = "Zomato ETL Analytics"

HEADER = html.Header(
    [
        html.Div(
            html.Div([
                html.Img(src="/assets/zomato_logo.svg", className="logo-img", alt="Zomato"),
                html.Span("ETL Analytics", className="logo-sub"),
            ], className="logo"),
            className="app-header-logo",
        ),
        html.Div(
            html.Div([html.Button(lbl, id=f"tab-{key}", n_clicks=0) for key, lbl in TABS],
                     className="tabs"),
            className="app-header-navigation",
        ),
        html.Div(
            html.Div([html.Span("@srummanf"), html.Span("SR", className="avatar")],
                     className="user-profile"),
            className="app-header-actions",
        ),
    ],
    className="app-header",
)

NAV = html.Div(
    [
        html.Nav(
            [
                html.Button([icon(ic_name), html.Span(lbl)], id=f"nav-{key}", n_clicks=0,
                            className="nav-link")
                for key, lbl, ic_name in NAV_ITEMS
            ],
            className="navigation",
        ),
        html.Footer([
            html.H1("Zomato"),
            html.Div(["Zomato ETL Platform", html.Br(), "Analytics Dashboard", html.Br(),
                      "Doris + Postgres"]),
        ], className="footer"),
    ],
    className="app-body-navigation",
)

app.layout = html.Div(
    html.Div(
        [
            dcc.Store(id="active-tab", data="overview"),
            HEADER,
            html.Div(
                [
                    NAV,
                    html.Div(id="main-content", className="app-body-main-content"),
                    render_sidebar(),
                ],
                className="app-body",
            ),
        ],
        className="app",
    )
)


@app.callback(
    Output("active-tab", "data"),
    [Input(f"tab-{key}", "n_clicks") for key, _ in TABS]
    + [Input(f"nav-{key}", "n_clicks") for key, _, _ in NAV_ITEMS],
    prevent_initial_call=True,
)
def pick_tab(*_):
    triggered = ctx.triggered_id or ""
    return triggered.replace("tab-", "").replace("nav-", "") or "overview"


@app.callback(
    [Output("main-content", "children")]
    + [Output(f"tab-{key}", "className") for key, _ in TABS]
    + [Output(f"nav-{key}", "className") for key, _, _ in NAV_ITEMS],
    Input("active-tab", "data"),
)
def render_tab(active):
    active = active or "overview"
    tab_classes = ["active" if key == active else "" for key, _ in TABS]
    nav_classes = ["nav-link active" if key == active else "nav-link"
                   for key, _, _ in NAV_ITEMS]
    return (render_main(active), *tab_classes, *nav_classes)


@app.callback(
    Output("sidebar-view", "data"),
    Input("sidebar-etl", "n_clicks"),
    Input("sidebar-dbt", "n_clicks"),
    prevent_initial_call=True,
)
def pick_sidebar_view(*_):
    return "dbt" if ctx.triggered_id == "sidebar-dbt" else "etl"


@app.callback(
    Output("sidebar-cards", "children"),
    Output("sidebar-etl", "className"),
    Output("sidebar-dbt", "className"),
    Input("sidebar-view", "data"),
)
def render_sidebar_cards(view):
    view = view or "etl"
    etl_cls = "card-button active" if view == "etl" else "card-button"
    dbt_cls = "card-button active" if view == "dbt" else "card-button"
    return sidebar_cards(view), etl_cls, dbt_cls


if __name__ == "__main__":
    app.run(debug=False, port=8050)
