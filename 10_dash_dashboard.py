"""Step 10 (alternative frontend) — a local Plotly Dash dashboard.

Reads the exact same KPIs and charts the 4 Metabase dashboards show (see
doc/DASHBOARD.md) straight from Doris and Postgres, and renders them as a
red, Zomato-branded local web app.

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
from dash import Dash, Input, Output, dash_table, dcc, html
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
# Zomato-red theme
# ---------------------------------------------------------------------------

RED = "#E23744"
RED_DARK = "#B71C2B"
PINK = "#E85D75"
PAGE_BG = "#F5F1EE"
CARD_BG = "#FFFFFF"
SIDEBAR_BG = "#E23744"
TEXT_DARK = "#2B2B2B"
TEXT_MUTED = "#8A8A8A"
RED_PALETTE = [RED, RED_DARK, PINK, "#FF8C69", "#B22222", "#D2691E", "#F08080"]
FONT_FAMILY = "'Poppins', 'Helvetica Neue', Arial, sans-serif"

CHART_LAYOUT = dict(
    plot_bgcolor=CARD_BG,
    paper_bgcolor=CARD_BG,
    font=dict(color=TEXT_DARK, family=FONT_FAMILY),
    title_font=dict(color=RED_DARK, size=16, family=FONT_FAMILY),
    margin=dict(l=40, r=20, t=50, b=40),
)


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
        "kpis": [
            ("Total Orders", f"{orders:,.0f}"),
            ("Total Revenue", f"₹{revenue:,.0f}"),
            ("Avg Order Value", f"₹{aov:,.2f}"),
            ("Active Restaurants", f"{active_restaurants:,.0f}"),
        ],
        "charts": [
            ("Revenue Trend", px.line(revenue_trend, x="order_date", y="revenue", markers=True,
                                       color_discrete_sequence=[RED])),
            ("Orders by Area", px.bar(orders_by_area, x="area", y="orders",
                                       color="area", color_discrete_sequence=RED_PALETTE)),
            ("Top Cuisines by Order Volume", px.bar(top_cuisines, x="cuisine", y="orders",
                                                      color="cuisine", color_discrete_sequence=RED_PALETTE)),
        ],
        "tables": [("Top Restaurants", top_restaurants)],
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

    return {
        "title": "Customer Insights",
        "kpis": [
            ("Total Customers", f"{total_customers:,.0f}"),
            ("New Customers (30d)", f"{new_customers:,.0f}"),
            ("Repeat Rate", f"{repeat_rate:.1f}%"),
            ("Avg Orders / Customer", f"{avg_orders:.2f}"),
        ],
        "charts": [
            ("Orders by Payment Method", px.bar(by_payment, x="payment_method", y="orders",
                                                  color="payment_method", color_discrete_sequence=RED_PALETTE)),
        ],
        "tables": [("Customer Value Tiers", value_tiers)],
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
        "kpis": [
            ("Avg Delivery Time", f"{avg_delivery:.1f} min"),
            ("Cancellation Rate", f"{cancellation_rate:.2f}%"),
            ("Avg Rating", f"{avg_rating:.2f} ★"),
            ("On-Time %", f"{on_time_pct:.1f}%"),
        ],
        "charts": [
            ("Order Volume by Hour of Day", px.bar(by_hour, x="hour_id", y="orders",
                                                     color_discrete_sequence=[RED])),
        ],
        "tables": [
            ("Delivery Partner Leaderboard", leaderboard),
            ("Online Order Enabled vs Not", online_vs_not),
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
    trend = query_pg(
        "SELECT run_at, rejection_rate FROM pipeline_validation_runs ORDER BY run_at")

    total_valid = scalar(latest_validation, "total_valid")
    total_rejected = scalar(latest_validation, "total_rejected")
    rejection_rate = scalar(latest_validation, "rejection_rate")
    total_tests = scalar(latest_dbt, "total_tests")
    passed_tests = scalar(latest_dbt, "passed_tests")

    return {
        "title": "Pipeline Health",
        "kpis": [
            ("Rows Ingested (latest run)", f"{(total_valid or 0) + (total_rejected or 0):,.0f}"),
            ("Rejected Rows (latest run)", f"{total_rejected or 0:,.0f}"),
            ("Rejection Rate (latest run)", f"{float(rejection_rate or 0) * 100:.2f}%"),
            ("dbt Tests (latest run)", f"{passed_tests or 0}/{total_tests or 0}"),
        ],
        "charts": [
            ("Rejection Rate Trend", px.line(trend, x="run_at", y="rejection_rate", markers=True,
                                              color_discrete_sequence=[RED])),
        ],
        "tables": [],
    }


def fetch_all_sections():
    return [
        fetch_business_overview(),
        fetch_customer_insights(),
        fetch_delivery_operations(),
        fetch_pipeline_health(),
    ]


# ---------------------------------------------------------------------------
# Dash layout
# ---------------------------------------------------------------------------

def style_chart(fig, title):
    fig.update_layout(**CHART_LAYOUT, title=title, showlegend=False)
    return fig


def kpi_card(label, value, hero=False):
    if hero:
        return html.Div(
            [
                html.Div(label, style={"fontSize": "15px", "fontWeight": "600", "color": "white"}),
                html.Div(value, style={"fontSize": "34px", "fontWeight": "800", "color": "white",
                                        "marginTop": "10px"}),
            ],
            style={
                "background": f"linear-gradient(135deg, {RED}, {RED_DARK})",
                "borderRadius": "18px",
                "padding": "24px 26px",
                "boxShadow": f"0 8px 20px rgba(226,55,68,0.35)",
                "flex": "1.4",
                "minWidth": "220px",
            },
        )
    return html.Div(
        [
            html.Div(value, style={"fontSize": "26px", "fontWeight": "700", "color": TEXT_DARK}),
            html.Div(label, style={"fontSize": "13px", "color": TEXT_MUTED, "marginTop": "6px"}),
        ],
        style={
            "background": CARD_BG,
            "borderRadius": "18px",
            "padding": "22px 24px",
            "boxShadow": "0 4px 14px rgba(0,0,0,0.06)",
            "flex": "1",
            "minWidth": "180px",
        },
    )


def card_wrap(children):
    return html.Div(
        children,
        style={
            "background": CARD_BG,
            "borderRadius": "18px",
            "padding": "20px",
            "boxShadow": "0 4px 14px rgba(0,0,0,0.06)",
            "marginBottom": "20px",
        },
    )


def data_table(title, df):
    return card_wrap([
        html.H4(title, style={"color": TEXT_DARK, "marginTop": "0", "marginBottom": "14px"}),
        dash_table.DataTable(
            data=df.to_dict("records"),
            columns=[{"name": c, "id": c} for c in df.columns],
            style_header={"backgroundColor": RED, "color": "white", "fontWeight": "600", "border": "none"},
            style_cell={"padding": "10px", "fontFamily": FONT_FAMILY, "border": "none",
                        "borderBottom": "1px solid #f0e9e9"},
            style_data={"backgroundColor": CARD_BG},
            style_table={"overflowX": "auto"},
            page_size=10,
        ),
    ])


def render_section(section):
    kpis = section["kpis"]
    kpi_row = html.Div(
        [kpi_card(label, value, hero=(i == 0)) for i, (label, value) in enumerate(kpis)],
        style={"display": "flex", "gap": "18px", "flexWrap": "wrap", "marginBottom": "22px"},
    )
    charts = [card_wrap(dcc.Graph(figure=style_chart(fig, title), config={"displaylogo": False}))
              for title, fig in section["charts"]]
    tables = [data_table(title, df) for title, df in section["tables"]]
    return html.Div([kpi_row, *charts, *tables])


SECTIONS = fetch_all_sections()

app = Dash(__name__, external_stylesheets=[
    "https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&display=swap",
])
app.title = "Zomato Data ETL Dashboard"

SIDEBAR = html.Div(
    [
        html.Img(src="/assets/zomato_logo.svg", style={"width": "150px", "marginBottom": "40px"}),
        dcc.Tabs(
            id="tabs",
            value=SECTIONS[0]["title"],
            vertical=True,
            children=[
                dcc.Tab(
                    label=s["title"], value=s["title"],
                    style={
                        "background": "transparent", "border": "none", "color": "#FFD8DC",
                        "fontWeight": "600", "fontSize": "15px", "padding": "14px 12px",
                        "textAlign": "left",
                    },
                    selected_style={
                        "background": "rgba(255,255,255,0.16)", "border": "none", "color": "white",
                        "fontWeight": "700", "fontSize": "15px", "padding": "14px 12px",
                        "borderRadius": "10px", "textAlign": "left",
                    },
                )
                for s in SECTIONS
            ],
        ),
    ],
    style={
        "background": SIDEBAR_BG, "width": "240px", "minHeight": "100vh",
        "padding": "30px 18px", "boxSizing": "border-box", "flexShrink": "0",
    },
)

TOPBAR = html.Div(
    [
        html.Div("Welcome back \U0001f44b", style={"fontSize": "22px", "fontWeight": "700", "color": TEXT_DARK}),
        html.Div(f"Data as of {datetime.now().strftime('%B %d, %Y  %H:%M')}",
                 style={"fontSize": "13px", "color": TEXT_MUTED, "marginTop": "4px"}),
    ],
    style={"marginBottom": "26px"},
)

app.layout = html.Div(
    [
        SIDEBAR,
        html.Div(
            [TOPBAR, html.Div(id="tab-content")],
            style={"flex": "1", "padding": "30px 34px", "minWidth": "0"},
        ),
    ],
    style={"background": PAGE_BG, "minHeight": "100vh", "display": "flex", "fontFamily": FONT_FAMILY},
)


@app.callback(Output("tab-content", "children"), Input("tabs", "value"))
def render_tab(selected_title):
    section = next(s for s in SECTIONS if s["title"] == selected_title)
    return render_section(section)


if __name__ == "__main__":
    app.run(debug=True)
