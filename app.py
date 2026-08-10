"""
Food Delivery Product Analytics — Live Dashboard
Deploy free on Streamlit Community Cloud (share.streamlit.io) or
Hugging Face Spaces (huggingface.co/spaces) — this file works unchanged on either.
"""
import datetime as dt
import os

import numpy as np
import plotly.graph_objects as go
import polars as pl
import streamlit as st
from plotly.subplots import make_subplots

from analytics import clean_data, compute_all_kpis
from data_gen import generate_synthetic_data
from db_loader import ensure_bool, load_from_database

st.set_page_config(page_title="Food Delivery Product Analytics", layout="wide", page_icon="📊")

REFRESH_TTL_SECONDS = 600  # data is re-pulled from the DB at most every 10 minutes


def _get_db_credentials():
    """Reads DB credentials from environment variables.

    Both Hugging Face Spaces and Streamlit Community Cloud expose secrets this
    way: HF natively as env vars, and Streamlit mirrors any *root-level*
    secrets.toml key (e.g. DB_HOST = "...") to os.environ automatically. Using
    flat root-level keys (not nested under a [db] section) keeps one code path
    working unchanged on either host. Falls back to st.secrets directly in
    case that env-var mirroring behavior ever changes.
    Returns a dict, or None if no credentials are configured anywhere.
    """
    if os.environ.get("DB_HOST"):
        return {
            "host": os.environ["DB_HOST"],
            "port": int(os.environ.get("DB_PORT", 3306)),
            "database": os.environ.get("DB_NAME", ""),
            "user": os.environ.get("DB_USER", ""),
            "password": os.environ.get("DB_PASSWORD", ""),
        }
    try:
        return {
            "host": st.secrets["DB_HOST"],
            "port": int(st.secrets.get("DB_PORT", 3306)),
            "database": st.secrets["DB_NAME"],
            "user": st.secrets["DB_USER"],
            "password": st.secrets["DB_PASSWORD"],
        }
    except Exception:
        return None


# ---------------------------------------------------------------------
# Data loading (cached — this is what makes the dashboard "dynamic"
# without hammering the database on every click)
# ---------------------------------------------------------------------
@st.cache_data(ttl=REFRESH_TTL_SECONDS, show_spinner=False)
def load_data():
    creds = _get_db_credentials()
    try:
        if not creds:
            raise ValueError("No DB credentials found in environment variables or st.secrets.")
        users, restaurants, riders, orders, events, nps = load_from_database(
            creds["host"], creds["port"], creds["database"], creds["user"], creds["password"]
        )
        users = ensure_bool(users, ["is_subscriber"])
        orders = ensure_bool(orders, ["complaint_flag", "wrong_item_flag", "is_promo_used", "is_scheduled_order"])
        source = f"Live MySQL database ({creds['database']} @ {creds['host']})"
    except Exception as e:
        users, restaurants, riders, orders, events, nps = generate_synthetic_data()
        source = f"Synthetic fallback data (DB unavailable: {type(e).__name__})"

    users_clean, orders_clean, events_clean, nps_clean, restaurants_c, riders_c = clean_data(
        users, restaurants, riders, orders, events, nps
    )
    kpi, charts = compute_all_kpis(users_clean, orders_clean, events_clean, nps_clean, restaurants_c, riders_c)
    return kpi, charts, source, dt.datetime.now()


# ---------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------
st.sidebar.title("📊 Controls")
if st.sidebar.button("🔄 Refresh data now", use_container_width=True):
    load_data.clear()

kpi, charts, data_source, last_loaded = load_data()

st.sidebar.markdown(f"**Data source:**  \n{data_source}")
st.sidebar.markdown(f"**Last refreshed:**  \n{last_loaded.strftime('%Y-%m-%d %H:%M:%S')}")
st.sidebar.caption(f"Auto-refreshes at most every {REFRESH_TTL_SECONDS // 60} minutes, or on demand via the button above.")

# ---------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------
st.title("🍔 Food Delivery — Product Analytics Dashboard")
st.caption(f"Data source: {data_source} · Last refreshed: {last_loaded.strftime('%Y-%m-%d %H:%M:%S')}")

# ---------------------------------------------------------------------
# KPI Scorecards
# ---------------------------------------------------------------------
kpi_groups = [
    ("Acquisition & Activation", [
        ("Activation Rate", f"{kpi['activation_rate']:.1f}%"),
        ("Avg Time to First Order", f"{kpi['avg_ttfo']:.1f} d"),
        ("Illustrative CAC", f"{kpi['cac']:,.0f}"),
    ]),
    ("Engagement & Usage", [
        ("Avg DAU", f"{kpi['avg_dau']:.0f}"),
        ("Avg WAU", f"{kpi['avg_wau']:.0f}"),
        ("Avg MAU", f"{kpi['avg_mau']:.0f}"),
        ("Stickiness (DAU/MAU)", f"{kpi['stickiness']:.1f}%"),
        ("Orders / Active User", f"{kpi['orders_per_user']:.2f}"),
        ("Session Frequency", f"{kpi['avg_session_frequency']:.2f}"),
        ("Avg Session Duration", f"{kpi['avg_session_duration_sec']/60:.1f} min"),
    ]),
    ("Conversion & Funnel", [
        ("Visitor -> Order Conv.", f"{kpi['visitor_to_order_conv']:.1f}%"),
        ("Menu View -> Cart Rate", f"{kpi['menu_to_cart_rate']:.1f}%"),
        ("Cart Abandonment", f"{kpi['cart_abandonment']:.1f}%"),
        ("Order Completion Rate", f"{kpi['order_completion_rate']:.1f}%"),
    ]),
    ("Revenue & Monetization", [
        ("GMV", f"{kpi['gmv']:,.0f}"),
        ("Take Rate", f"{kpi['take_rate']:.1f}%"),
        ("AOV", f"{kpi['aov']:,.2f}"),
        ("ARPU", f"{kpi['arpu']:,.2f}"),
        ("ARPPU", f"{kpi['arppu']:,.2f}"),
        ("Avg Contribution Margin", f"{kpi['avg_contribution_margin']:,.2f}"),
    ]),
    ("Retention & Loyalty", [
        ("D7 Retention", f"{kpi['d7']:.1f}%"),
        ("D30 Retention", f"{kpi['d30']:.1f}%"),
        ("Churn Rate (D30)", f"{kpi['churn_d30']:.1f}%"),
        ("Repeat Order Rate", f"{kpi['repeat_rate']:.1f}%"),
        ("Order Freq. (Retained)", f"{kpi['order_frequency_retained']:.2f}"),
        ("Avg Empirical LTV", f"{kpi['avg_ltv']:,.0f}"),
        ("LTV : CAC Ratio", f"{kpi['ltv_cac_ratio']:.2f}"),
        ("NPS", f"{kpi['nps_score']:.0f}"),
    ]),
    ("Operational & Delivery", [
        ("Cancellation Rate", f"{kpi['cancellation_rate']:.1f}%"),
        ("On-Time Delivery Rate", f"{kpi['on_time_rate']:.1f}%"),
        ("Avg Delivery Time", f"{kpi['avg_delivery_time']:.1f} min"),
        ("Order Accuracy Rate", f"{kpi['order_accuracy_rate']:.1f}%"),
        ("Avg Prep Time", f"{kpi['avg_prep_time']:.1f} min"),
        ("Cost / Delivery", f"{kpi['cost_per_delivery']:,.2f}"),
    ]),
    ("Marketplace / Supply-side", [
        ("Active Restaurants", f"{kpi['active_restaurants']} / {kpi['total_restaurants']}"),
        ("Restaurant Utilization", f"{kpi['restaurant_utilization']:.2f} ord."),
        ("Restaurant Churn Rate", f"{kpi['restaurant_churn_rate']:.1f}%"),
        ("Overall Avg Rating", f"{kpi['overall_avg_rating']:.2f} / 5"),
        ("Top-10 Restaurant GMV Share", f"{kpi['top10_share']:.1f}%"),
    ]),
    ("Product / Feature", [
        ("Scheduled-Order Adoption", f"{kpi['scheduled_order_adoption']:.1f}%"),
        ("Subscriber Adoption", f"{kpi['subscriber_adoption']:.1f}%"),
        ("Promo Dependency", f"{kpi['promo_dependency']:.1f}%"),
        ("Avg Basket Size", f"{kpi['avg_basket_size']:.2f} items"),
    ]),
    ("CLV Modeling", [
        ("Empirical LTV", f"{kpi['avg_ltv']:,.0f}"),
        ("Formulaic CLV", f"{kpi['clv_formulaic']:,.0f}"),
        ("Assumed Lifespan", f"{kpi['assumed_lifespan_years']:.0f} yrs"),
    ]),
]

st.subheader("KPI Scorecards — All Metrics at a Glance")
for section_title, metrics in kpi_groups:
    st.markdown(f"**{section_title}**")
    cols = st.columns(len(metrics))
    for col, (label, value) in zip(cols, metrics):
        col.metric(label, value)

st.divider()

# ---------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------
gmv_trend = charts["gmv_trend"]
monthly_active = charts["monthly_active"]
fig_trends = make_subplots(rows=1, cols=2, subplot_titles=("Monthly GMV Trend", "Monthly Active Users (MAU) Trend"))
fig_trends.add_trace(go.Bar(x=gmv_trend["order_month"], y=gmv_trend["gmv"], marker_color="#F18F01", name="GMV"), row=1, col=1)
fig_trends.add_trace(go.Scatter(x=monthly_active["order_month"], y=monthly_active["mau"], mode="lines+markers",
                                 line=dict(color="#A23B72", width=3), name="MAU"), row=1, col=2)
fig_trends.update_layout(height=380, showlegend=False, template="plotly_white")
st.plotly_chart(fig_trends, use_container_width=True)

funnel_counts = charts["funnel_counts"]
fig_funnel = go.Figure(go.Funnel(
    y=funnel_counts["event_name"].cast(pl.Utf8).to_list(), x=funnel_counts["sessions"].to_list(),
    textinfo="value+percent initial",
    marker=dict(color=["#6A4C93", "#8E5FB5", "#A97CC9", "#C49ADD", "#DFB8F1"])
))
fig_funnel.update_layout(height=380, template="plotly_white", title="Sessions by Funnel Stage")
st.plotly_chart(fig_funnel, use_container_width=True)

heat_data, heat_cols, cohort_matrix = charts["heat_data"], charts["heat_cols"], charts["cohort_matrix"]
fig_cohort = go.Figure(data=go.Heatmap(
    z=heat_data, x=[str(c) for c in heat_cols], y=cohort_matrix["cohort_month"].to_list(),
    colorscale="YlGnBu", colorbar=dict(title="Retention %"), text=heat_data, texttemplate="%{text:.0f}"
))
fig_cohort.update_layout(height=420, template="plotly_white", title="Cohort Retention Heatmap (%)",
                          xaxis_title="Months since signup", yaxis_title="Signup cohort")
st.plotly_chart(fig_cohort, use_container_width=True)

segment_summary = charts["segment_summary"]
fig_rfm = go.Figure(go.Pie(
    labels=segment_summary["segment_label"].to_list(), values=segment_summary["users"].to_list(),
    hole=0.45, marker=dict(colors=["#2E86AB", "#A23B72", "#F18F01", "#1B998B", "#6A4C93"])
))
fig_rfm.update_layout(height=380, template="plotly_white", title="Customer Segments (RFM)")
st.plotly_chart(fig_rfm, use_container_width=True)

cuisine_perf, city_perf, restaurant_gmv = charts["cuisine_perf"], charts["city_perf"], charts["restaurant_gmv"]
top_restaurants = restaurant_gmv.head(10)
fig_market = make_subplots(rows=1, cols=3, subplot_titles=("GMV by Cuisine", "GMV by City", "Top 10 Restaurants by GMV"))
fig_market.add_trace(go.Bar(y=cuisine_perf["cuisine_type"], x=cuisine_perf["gmv"], orientation="h", marker_color="#1B998B", showlegend=False), row=1, col=1)
fig_market.add_trace(go.Bar(x=city_perf["city"], y=city_perf["gmv"], marker_color="#457B9D", showlegend=False), row=1, col=2)
fig_market.add_trace(go.Bar(x=list(range(1, top_restaurants.height + 1)), y=top_restaurants["restaurant_gmv"], marker_color="#3B1F2B", showlegend=False), row=1, col=3)
fig_market.update_layout(height=400, template="plotly_white", title_text="Marketplace / Supply-side Performance")
st.plotly_chart(fig_market, use_container_width=True)

rating_dist, cancel_reasons = charts["rating_dist"], charts["cancel_reasons"]
fig_quality = make_subplots(rows=1, cols=2, subplot_titles=("Rating Distribution", "Cancellation Reasons"))
fig_quality.add_trace(go.Bar(x=rating_dist["rating"].cast(pl.Utf8), y=rating_dist["count"], marker_color="#F4A261", showlegend=False), row=1, col=1)
fig_quality.add_trace(go.Bar(x=cancel_reasons["cancel_reason"], y=cancel_reasons["count"], marker_color="#E76F51", showlegend=False), row=1, col=2)
fig_quality.update_layout(height=420, template="plotly_white", title_text="Customer & Order Quality")
fig_quality.update_xaxes(tickangle=30, row=1, col=2)
st.plotly_chart(fig_quality, use_container_width=True)

fig_ab = make_subplots(rows=1, cols=2, subplot_titles=("Order Completion Rate (%)", "Average Order Value"))
fig_ab.add_trace(go.Bar(x=["Control", "Treatment"], y=[kpi["ab_p1"] * 100, kpi["ab_p2"] * 100],
                         marker_color=["#94A3B8", "#2E86AB"],
                         text=[f"{kpi['ab_p1']*100:.1f}%", f"{kpi['ab_p2']*100:.1f}%"],
                         textposition="outside", showlegend=False), row=1, col=1)
fig_ab.add_trace(go.Bar(x=["Control", "Treatment"], y=[kpi["ab_control_aov_mean"], kpi["ab_treat_aov_mean"]],
                         marker_color=["#94A3B8", "#F18F01"],
                         text=[f"{kpi['ab_control_aov_mean']:,.0f}", f"{kpi['ab_treat_aov_mean']:,.0f}"],
                         textposition="outside", showlegend=False), row=1, col=2)
fig_ab.update_layout(height=400, template="plotly_white",
                      title_text=f"A/B Test: Checkout Redesign (Completion p={kpi['ab_p_value_completion']:.4f}, AOV p={kpi['ab_p_value_aov']:.4f})")
st.plotly_chart(fig_ab, use_container_width=True)

st.caption("Built with Streamlit + Polars + Plotly · Deployed free on Streamlit Community Cloud")
