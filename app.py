"""
Food Delivery Product Analytics — Live Dashboard
Deploy free on Streamlit Community Cloud (share.streamlit.io) or
Hugging Face Spaces (huggingface.co/spaces) — this file works unchanged on either.
"""
import datetime as dt
import os

import plotly.graph_objects as go
import polars as pl
import streamlit as st
from plotly.subplots import make_subplots

from analytics import clean_data, compute_all_kpis, filter_data, get_filter_options
from data_gen import generate_synthetic_data
from db_loader import ensure_bool, load_from_database

st.set_page_config(page_title="Food Delivery Analytics", layout="wide", page_icon="🍔", initial_sidebar_state="expanded")

REFRESH_TTL_SECONDS = 600  # data is re-pulled from the DB at most every 10 minutes

# ---------------------------------------------------------------------
# Design tokens — one place to tweak the look
# ---------------------------------------------------------------------
PALETTE = {
    "primary": "#6366F1", "primary_dark": "#4F46E5", "violet": "#8B5CF6", "teal": "#14B8A6",
    "amber": "#F59E0B", "rose": "#F43F5E", "sky": "#0EA5E9", "slate": "#475569",
    "bg": "#F8FAFC", "card": "#FFFFFF", "text": "#0F172A", "muted": "#64748B", "border": "#E2E8F0",
}
CHART_COLORWAY = [PALETTE["primary"], PALETTE["teal"], PALETTE["amber"], PALETTE["rose"],
                  PALETTE["sky"], PALETTE["violet"], PALETTE["slate"]]
PLOTLY_TEMPLATE = go.layout.Template(
    layout=go.Layout(
        font=dict(family="Inter, -apple-system, Segoe UI, sans-serif", color=PALETTE["text"], size=13),
        colorway=CHART_COLORWAY,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=48, b=10),
        title=dict(font=dict(size=15)),
        legend=dict(bgcolor="rgba(0,0,0,0)", orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(gridcolor=PALETTE["border"], zeroline=False),
        yaxis=dict(gridcolor=PALETTE["border"], zeroline=False),
        hoverlabel=dict(bgcolor="white", font_size=12, bordercolor=PALETTE["border"]),
        hovermode="x unified",
    )
)

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {{ font-family: 'Inter', -apple-system, sans-serif; }}
.block-container {{ padding-top: 2.6rem; padding-bottom: 2rem; max-width: 1400px; }}

/* ---- Header ---- */
.app-header {{ display:flex; align-items:center; justify-content:space-between; margin-bottom: 0.6rem; }}
.app-title {{ font-size: 26px; font-weight: 800; color: {PALETTE['text']}; margin:0; letter-spacing:-0.02em; }}
.app-subtitle {{ font-size: 13px; color: {PALETTE['muted']}; margin-top: 2px; }}
.status-chip {{
  display:inline-flex; align-items:center; gap:6px; background:{PALETTE['card']}; border:1px solid {PALETTE['border']};
  border-radius: 999px; padding: 6px 14px; font-size: 12.5px; font-weight:600; color:{PALETTE['slate']};
  box-shadow: 0 1px 2px rgba(0,0,0,0.04);
}}
.dot {{ width:8px; height:8px; border-radius:50%; display:inline-block; }}

/* ---- Section headers ---- */
.section-head {{ display:flex; align-items:center; gap:10px; margin: 4px 0 12px 0; }}
.section-head .bar {{ width:5px; height:22px; border-radius: 4px; }}
.section-head h3 {{ margin:0; font-size:17px; font-weight:750; color:{PALETTE['text']}; }}

/* ---- KPI cards ---- */
.kpi-grid {{ display:flex; flex-wrap:wrap; gap:12px; margin-bottom: 22px; }}
.kpi-card {{
  flex: 1 1 175px; min-width: 165px; background:{PALETTE['card']}; border:1px solid {PALETTE['border']};
  border-radius: 14px; padding: 14px 16px; position:relative; overflow:hidden;
  box-shadow: 0 1px 3px rgba(15,23,42,0.04); transition: transform .15s ease, box-shadow .15s ease;
}}
.kpi-card:hover {{ transform: translateY(-2px); box-shadow: 0 8px 20px rgba(15,23,42,0.08); }}
.kpi-card .accent {{ position:absolute; left:0; top:0; bottom:0; width:4px; }}
.kpi-value {{ font-size: 22px; font-weight: 800; color:{PALETTE['text']}; line-height:1.15; }}
.kpi-label {{ font-size: 11.5px; color:{PALETTE['muted']}; margin-top: 4px; font-weight:600; text-transform:uppercase; letter-spacing:.03em; }}

/* ---- Tabs ---- */
.stTabs [data-baseweb="tab-list"] {{ gap: 4px; border-bottom: 1px solid {PALETTE['border']}; }}
.stTabs [data-baseweb="tab"] {{
  height: 40px; border-radius: 10px 10px 0 0; padding: 0 16px; font-weight:600; font-size: 13.5px;
  color: {PALETTE['muted']};
}}
.stTabs [aria-selected="true"] {{ color:{PALETTE['primary_dark']} !important; background: rgba(99,102,241,0.08); }}

/* ---- Sidebar ---- */
section[data-testid="stSidebar"] {{ border-right: 1px solid {PALETTE['border']}; }}
.filter-head {{ font-size:12px; font-weight:700; text-transform:uppercase; letter-spacing:.04em; color:{PALETTE['muted']}; margin: 14px 0 4px 0; }}

.chart-card {{ background:{PALETTE['card']}; border:1px solid {PALETTE['border']}; border-radius:16px; padding: 6px 10px 2px 10px; margin-bottom:18px; box-shadow: 0 1px 3px rgba(15,23,42,0.04); }}
.info-note {{ font-size:12.5px; color:{PALETTE['muted']}; background:#F1F5F9; border-radius:10px; padding:10px 14px; margin: 4px 0 18px 0; }}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def section_head(title: str, color: str):
    st.markdown(
        f'<div class="section-head"><div class="bar" style="background:{color};"></div><h3>{title}</h3></div>',
        unsafe_allow_html=True,
    )


def kpi_grid(items, accent):
    """items: list of (label, value) tuples."""
    cards = "".join(
        f'<div class="kpi-card"><div class="accent" style="background:{accent};"></div>'
        f'<div class="kpi-value">{value}</div><div class="kpi-label">{label}</div></div>'
        for label, value in items
    )
    st.markdown(f'<div class="kpi-grid">{cards}</div>', unsafe_allow_html=True)


def chart_card(fig, height=380):
    fig.update_layout(template=PLOTLY_TEMPLATE, height=height)
    st.plotly_chart(fig, width="stretch", config={"displaylogo": False})


# ---------------------------------------------------------------------
# Credentials + data loading
# ---------------------------------------------------------------------
def _get_db_credentials():
    """Reads DB credentials from environment variables.

    Both Hugging Face Spaces and Streamlit Community Cloud expose secrets this
    way: HF natively as env vars, and Streamlit mirrors any *root-level*
    secrets.toml key (e.g. DB_HOST = "...") to os.environ automatically. Using
    flat root-level keys (not nested under a [db] section) keeps one code path
    working unchanged on either host. Falls back to st.secrets directly in
    case that env-var mirroring behavior ever changes.
    """
    if os.environ.get("DB_HOST"):
        return {
            "host": os.environ["DB_HOST"], "port": int(os.environ.get("DB_PORT", 3306)),
            "database": os.environ.get("DB_NAME", ""), "user": os.environ.get("DB_USER", ""),
            "password": os.environ.get("DB_PASSWORD", ""),
        }
    try:
        return {
            "host": st.secrets["DB_HOST"], "port": int(st.secrets.get("DB_PORT", 3306)),
            "database": st.secrets["DB_NAME"], "user": st.secrets["DB_USER"], "password": st.secrets["DB_PASSWORD"],
        }
    except Exception:
        return None


@st.cache_data(ttl=REFRESH_TTL_SECONDS, show_spinner=False)
def load_data():
    """Loads + cleans the 6 raw tables. Filtering/KPI computation happens
    separately (below) so filters can be applied without re-hitting the DB.
    """
    creds = _get_db_credentials()
    try:
        if not creds:
            raise ValueError("No DB credentials found in environment variables or st.secrets.")
        users, restaurants, riders, orders, events, nps = load_from_database(
            creds["host"], creds["port"], creds["database"], creds["user"], creds["password"]
        )
        users = ensure_bool(users, ["is_subscriber"])
        orders = ensure_bool(orders, ["complaint_flag", "wrong_item_flag", "is_promo_used", "is_scheduled_order"])
        source = f"Live MySQL · {creds['database']}"
    except Exception:
        users, restaurants, riders, orders, events, nps = generate_synthetic_data()
        source = "Synthetic (fallback)"

    users_c, orders_c, events_c, nps_c, restaurants_c, riders_c = clean_data(users, restaurants, riders, orders, events, nps)
    return users_c, orders_c, events_c, nps_c, restaurants_c, riders_c, source, dt.datetime.now()


# ---------------------------------------------------------------------
# Sidebar — branding + filters
# ---------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:2px;">'
        f'<div style="font-size:28px;">🍔</div>'
        f'<div><div style="font-weight:800;font-size:16px;color:{PALETTE["text"]};">FoodFlow Analytics</div>'
        f'<div style="font-size:11.5px;color:{PALETTE["muted"]};">Product KPI Dashboard</div></div></div>',
        unsafe_allow_html=True,
    )
    st.divider()

    if st.button("🔄  Refresh data from source", width="stretch"):
        load_data.clear()
        st.rerun()

users_clean, orders_clean, events_clean, nps_clean, restaurants, riders, data_source, last_loaded = load_data()
opts = get_filter_options(orders_clean, users_clean, restaurants)

with st.sidebar:
    dot_color = PALETTE["teal"] if "Live" in data_source else PALETTE["amber"]
    st.markdown(
        f'<div class="status-chip"><span class="dot" style="background:{dot_color};"></span>{data_source}</div>',
        unsafe_allow_html=True,
    )
    st.caption(f"Refreshed {last_loaded.strftime('%H:%M:%S')} · auto-refresh every {REFRESH_TTL_SECONDS//60} min")

    st.markdown('<div class="filter-head">📅 Date range</div>', unsafe_allow_html=True)
    date_range = st.date_input(
        "Date range", value=(opts["date_min"], opts["date_max"]),
        min_value=opts["date_min"], max_value=opts["date_max"], label_visibility="collapsed",
    )

    st.markdown('<div class="filter-head">🏙️ City</div>', unsafe_allow_html=True)
    f_cities = st.multiselect("City", opts["cities"], default=[], placeholder="All cities", label_visibility="collapsed")

    st.markdown('<div class="filter-head">🍜 Cuisine</div>', unsafe_allow_html=True)
    f_cuisines = st.multiselect("Cuisine", opts["cuisines"], default=[], placeholder="All cuisines", label_visibility="collapsed")

    st.markdown('<div class="filter-head">📣 Acquisition channel</div>', unsafe_allow_html=True)
    f_channels = st.multiselect("Channel", opts["channels"], default=[], placeholder="All channels", label_visibility="collapsed")

    st.markdown('<div class="filter-head">📱 Device</div>', unsafe_allow_html=True)
    f_devices = st.multiselect("Device", opts["devices"], default=[], placeholder="All devices", label_visibility="collapsed")

    st.markdown('<div class="filter-head">🧪 A/B test group</div>', unsafe_allow_html=True)
    f_ab = st.multiselect("A/B group", opts["ab_groups"], default=[], placeholder="Both groups", label_visibility="collapsed")

    st.divider()
    if st.button("↺  Reset all filters", width="stretch"):
        st.rerun()

# ---------------------------------------------------------------------
# Apply filters -> recompute KPIs on the filtered slice
# ---------------------------------------------------------------------
date_range_arg = tuple(date_range) if isinstance(date_range, (tuple, list)) and len(date_range) == 2 else None
uf, of, ef, nf = filter_data(
    users_clean, orders_clean, events_clean, nps_clean, restaurants,
    date_range=date_range_arg, cities=f_cities or None, cuisines=f_cuisines or None,
    channels=f_channels or None, devices=f_devices or None, ab_groups=f_ab or None,
)

filters_active = any([f_cities, f_cuisines, f_channels, f_devices, f_ab, date_range_arg != (opts["date_min"], opts["date_max"])])

try:
    kpi, charts = compute_all_kpis(uf, of, ef, nf, restaurants, riders)
except ValueError as e:
    st.warning(f"⚠️ {e}")
    st.stop()

# ---------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------
h1, h2 = st.columns([3, 1])
with h1:
    st.markdown('<p class="app-title">Food Delivery Product Analytics</p>', unsafe_allow_html=True)
    scope = f"{of.height:,} orders · {uf.height:,} users" + (" (filtered)" if filters_active else " (all data)")
    st.markdown(f'<p class="app-subtitle">{scope}</p>', unsafe_allow_html=True)
with h2:
    st.markdown(
        f'<div style="text-align:right;padding-top:8px;">'
        f'<span class="status-chip"><span class="dot" style="background:{PALETTE["primary"]};"></span>'
        f'{last_loaded.strftime("%b %d, %H:%M")}</span></div>',
        unsafe_allow_html=True,
    )

if filters_active:
    st.markdown(
        '<div class="info-note">🔎 Filters applied — every KPI and chart below reflects only the filtered slice, '
        'not the full dataset. Clear filters in the sidebar to see the whole business.</div>',
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------
tab_overview, tab_acq, tab_rev, tab_retention, tab_ops, tab_market, tab_product, tab_ab = st.tabs(
    ["📈 Overview", "🎯 Acquisition & Engagement", "💰 Revenue", "🔁 Retention & Loyalty",
     "🚚 Operations", "🏬 Marketplace", "🧩 Product & Segments", "🧪 A/B Testing"]
)

# ===================== OVERVIEW =====================
with tab_overview:
    kpi_grid([
        ("GMV", f"{kpi['gmv']:,.0f}"), ("AOV", f"{kpi['aov']:,.0f}"),
        ("Active Users", f"{uf.height:,}"), ("Order Completion", f"{kpi['order_completion_rate']:.1f}%"),
        ("On-Time Delivery", f"{kpi['on_time_rate']:.1f}%"), ("D30 Retention", f"{kpi['d30']:.1f}%"),
        ("NPS", f"{kpi['nps_score']:.0f}"), ("LTV : CAC", f"{kpi['ltv_cac_ratio']:.2f}"),
    ], PALETTE["primary"])

    c1, c2 = st.columns([2, 1])
    with c1:
        section_head("Growth Trend", PALETTE["primary"])
        tc1, tc2 = st.columns([1, 1])
        trend_metric = tc1.selectbox("Metric", ["GMV", "Orders"], label_visibility="collapsed")
        trend_grain = tc2.radio("Granularity", ["Daily", "Monthly"], horizontal=True, label_visibility="collapsed")

        if trend_metric == "GMV":
            df = charts["gmv_trend_daily"] if trend_grain == "Daily" else charts["gmv_trend"]
            xcol = "order_date" if trend_grain == "Daily" else "order_month"
            fig = go.Figure(go.Scatter(x=df[xcol], y=df["gmv"], mode="lines", fill="tozeroy",
                                        line=dict(color=PALETTE["primary"], width=2.5),
                                        fillcolor="rgba(99,102,241,0.12)"))
        else:
            if trend_grain == "Daily":
                df, xcol, ycol = charts["orders_trend_daily"], "order_date", "orders"
            else:
                df, xcol, ycol = charts["monthly_active"], "order_month", "mau"
            fig = go.Figure(go.Bar(x=df[xcol], y=df[ycol], marker_color=PALETTE["teal"]))
        with st.container(border=True):
            chart_card(fig, height=320)

    with c2:
        section_head("Funnel", PALETTE["violet"])
        fc = charts["funnel_counts"]
        fig = go.Figure(go.Funnel(
            y=fc["event_name"].to_list(), x=fc["sessions"].to_list(),
            textinfo="value+percent initial", marker=dict(color=CHART_COLORWAY[:5]),
        ))
        with st.container(border=True):
            chart_card(fig, height=320)

# ===================== ACQUISITION & ENGAGEMENT =====================
with tab_acq:
    section_head("Acquisition & Activation", PALETTE["sky"])
    kpi_grid([
        ("Activation Rate", f"{kpi['activation_rate']:.1f}%"), ("Avg Time to First Order", f"{kpi['avg_ttfo']:.1f} d"),
        ("Illustrative CAC", f"{kpi['cac']:,.0f}"),
    ], PALETTE["sky"])

    section_head("Engagement & Usage", PALETTE["teal"])
    kpi_grid([
        ("Avg DAU", f"{kpi['avg_dau']:.0f}"), ("Avg WAU", f"{kpi['avg_wau']:.0f}"), ("Avg MAU", f"{kpi['avg_mau']:.0f}"),
        ("Stickiness", f"{kpi['stickiness']:.1f}%"), ("Orders / Active User", f"{kpi['orders_per_user']:.2f}"),
        ("Session Frequency", f"{kpi['avg_session_frequency']:.2f}"),
        ("Avg Session Duration", f"{kpi['avg_session_duration_sec']/60:.1f} min"),
    ], PALETTE["teal"])

    section_head("Conversion", PALETTE["violet"])
    kpi_grid([
        ("Visitor -> Order", f"{kpi['visitor_to_order_conv']:.1f}%"),
        ("Menu View -> Cart", f"{kpi['menu_to_cart_rate']:.1f}%"),
        ("Cart Abandonment", f"{kpi['cart_abandonment']:.1f}%"),
    ], PALETTE["violet"])

    c1, c2 = st.columns(2)
    with c1:
        ca = charts["channel_acq"]
        fig = go.Figure(go.Bar(x=ca["acquisition_channel"], y=ca["new_users"], marker_color=PALETTE["sky"],
                                text=ca["share_%"].cast(pl.Utf8) + "%", textposition="outside"))
        fig.update_layout(title="New Users by Channel")
        with st.container(border=True):
            chart_card(fig)
    with c2:
        ma = charts["monthly_active"]
        fig = go.Figure(go.Scatter(x=ma["order_month"], y=ma["mau"], mode="lines+markers",
                                    line=dict(color=PALETTE["teal"], width=2.5)))
        fig.update_layout(title="Monthly Active Users")
        with st.container(border=True):
            chart_card(fig)

# ===================== REVENUE =====================
with tab_rev:
    section_head("Revenue & Monetization", PALETTE["amber"])
    kpi_grid([
        ("GMV", f"{kpi['gmv']:,.0f}"), ("Take Rate", f"{kpi['take_rate']:.1f}%"), ("AOV", f"{kpi['aov']:,.2f}"),
        ("ARPU", f"{kpi['arpu']:,.2f}"), ("ARPPU", f"{kpi['arppu']:,.2f}"),
        ("Avg Contribution Margin", f"{kpi['avg_contribution_margin']:,.2f}"),
    ], PALETTE["amber"])

    gt = charts["gmv_trend"]
    fig = go.Figure(go.Bar(x=gt["order_month"], y=gt["gmv"], marker_color=PALETTE["amber"]))
    fig.update_layout(title="Monthly GMV")
    with st.container(border=True):
        chart_card(fig)

# ===================== RETENTION & LOYALTY =====================
with tab_retention:
    section_head("Retention, Loyalty & CLV", PALETTE["rose"])
    kpi_grid([
        ("D7 Retention", f"{kpi['d7']:.1f}%"), ("D30 Retention", f"{kpi['d30']:.1f}%"),
        ("Churn Rate (D30)", f"{kpi['churn_d30']:.1f}%"), ("Repeat Order Rate", f"{kpi['repeat_rate']:.1f}%"),
        ("Order Freq. (Retained)", f"{kpi['order_frequency_retained']:.2f}"), ("Empirical LTV", f"{kpi['avg_ltv']:,.0f}"),
        ("Formulaic CLV", f"{kpi['clv_formulaic']:,.0f}"), ("LTV : CAC", f"{kpi['ltv_cac_ratio']:.2f}"), ("NPS", f"{kpi['nps_score']:.0f}"),
    ], PALETTE["rose"])

    section_head("Cohort Retention Heatmap", PALETTE["rose"])
    heat_data, heat_cols, cohort_matrix = charts["heat_data"], charts["heat_cols"], charts["cohort_matrix"]
    text_labels = [["" if (v != v) else f"{v:.0f}" for v in row] for row in heat_data]  # v != v -> NaN check, blank instead of "NaN"
    fig = go.Figure(go.Heatmap(
        z=heat_data, x=[str(c) for c in heat_cols], y=cohort_matrix["cohort_month"].to_list(),
        colorscale=[[0, "#F1F5F9"], [1, PALETTE["rose"]]], colorbar=dict(title="%"),
        text=text_labels, texttemplate="%{text}", hoverongaps=False,
    ))
    fig.update_layout(xaxis_title="Months since signup", yaxis_title="Signup cohort")
    with st.container(border=True):
        chart_card(fig, height=420)

# ===================== OPERATIONS =====================
with tab_ops:
    section_head("Operational & Delivery Experience", PALETTE["slate"])
    kpi_grid([
        ("Cancellation Rate", f"{kpi['cancellation_rate']:.1f}%"), ("On-Time Delivery", f"{kpi['on_time_rate']:.1f}%"),
        ("Avg Delivery Time", f"{kpi['avg_delivery_time']:.1f} min"), ("Order Accuracy", f"{kpi['order_accuracy_rate']:.1f}%"),
        ("Avg Prep Time", f"{kpi['avg_prep_time']:.1f} min"), ("Cost / Delivery", f"{kpi['cost_per_delivery']:,.2f}"),
    ], PALETTE["slate"])

    c1, c2 = st.columns(2)
    with c1:
        rd = charts["rating_dist"]
        fig = go.Figure(go.Bar(x=rd["rating"].cast(pl.Utf8), y=rd["count"], marker_color=PALETTE["amber"]))
        fig.update_layout(title="Rating Distribution")
        with st.container(border=True):
            chart_card(fig)
    with c2:
        cr = charts["cancel_reasons"]
        fig = go.Figure(go.Bar(x=cr["cancel_reason"], y=cr["count"], marker_color=PALETTE["rose"]))
        fig.update_layout(title="Cancellation Reasons")
        fig.update_xaxes(tickangle=25)
        with st.container(border=True):
            chart_card(fig)

# ===================== MARKETPLACE =====================
with tab_market:
    section_head("Marketplace / Supply-side", PALETTE["teal"])
    kpi_grid([
        ("Active Restaurants", f"{kpi['active_restaurants']} / {kpi['total_restaurants']}"),
        ("Restaurant Utilization", f"{kpi['restaurant_utilization']:.2f}"),
        ("Restaurant Churn", f"{kpi['restaurant_churn_rate']:.1f}%"),
        ("Overall Avg Rating", f"{kpi['overall_avg_rating']:.2f} / 5"),
        ("Top-10 GMV Share", f"{kpi['top10_share']:.1f}%"),
    ], PALETTE["teal"])

    view_by = st.radio("View GMV by", ["Cuisine", "City", "Top Restaurants"], horizontal=True)
    if view_by == "Cuisine":
        d = charts["cuisine_perf"]
        fig = go.Figure(go.Bar(y=d["cuisine_type"], x=d["gmv"], orientation="h", marker_color=PALETTE["teal"]))
    elif view_by == "City":
        d = charts["city_perf"]
        fig = go.Figure(go.Bar(x=d["city"], y=d["gmv"], marker_color=PALETTE["sky"]))
    else:
        d = charts["restaurant_gmv"].head(10)
        fig = go.Figure(go.Bar(x=list(range(1, d.height + 1)), y=d["restaurant_gmv"], marker_color=PALETTE["slate"]))
    fig.update_layout(title=f"GMV by {view_by}")
    with st.container(border=True):
        chart_card(fig, height=420)

# ===================== PRODUCT & SEGMENTS =====================
with tab_product:
    section_head("Product / Feature Adoption", PALETTE["violet"])
    kpi_grid([
        ("Scheduled-Order Adoption", f"{kpi['scheduled_order_adoption']:.1f}%"),
        ("Subscriber Adoption", f"{kpi['subscriber_adoption']:.1f}%"),
        ("Promo Dependency", f"{kpi['promo_dependency']:.1f}%"),
        ("Avg Basket Size", f"{kpi['avg_basket_size']:.2f} items"),
    ], PALETTE["violet"])

    section_head("RFM Customer Segments", PALETTE["primary"])
    ss = charts["segment_summary"]
    fig = go.Figure(go.Pie(labels=ss["segment_label"].to_list(), values=ss["users"].to_list(), hole=0.5,
                            marker=dict(colors=CHART_COLORWAY)))
    with st.container(border=True):
        chart_card(fig, height=380)

# ===================== A/B TESTING =====================
with tab_ab:
    section_head("Checkout Redesign: Control vs Treatment", PALETTE["primary"])
    if not kpi.get("ab_available"):
        st.markdown(
            '<div class="info-note">🧪 Not enough data for an A/B comparison under the current filters '
            '(one of the two groups is empty or has too few delivered orders). Widen your filters — '
            'e.g. clear the A/B test group filter — to see this comparison.</div>',
            unsafe_allow_html=True,
        )
    else:
        def fmt_p(p):
            return "< 0.0001" if p < 0.0001 else f"{p:.4f}"

        kpi_grid([
            ("Control Completion", f"{kpi['ab_p1']*100:.1f}%"), ("Treatment Completion", f"{kpi['ab_p2']*100:.1f}%"),
            ("Completion p-value", fmt_p(kpi['ab_p_value_completion'])),
            ("Control AOV", f"{kpi['ab_control_aov_mean']:,.0f}"), ("Treatment AOV", f"{kpi['ab_treat_aov_mean']:,.0f}"),
            ("AOV p-value", fmt_p(kpi['ab_p_value_aov'])),
        ], PALETTE["primary"])

        sig_completion = kpi["ab_p_value_completion"] < 0.05
        sig_aov = kpi["ab_p_value_aov"] < 0.05
        verdict = "✅ Both metrics show a statistically significant lift for Treatment." if (sig_completion and sig_aov) else \
                  "⚠️ Not all metrics reached statistical significance (p < 0.05) under this filter."
        st.markdown(f'<div class="info-note">{verdict}</div>', unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            fig = go.Figure(go.Bar(x=["Control", "Treatment"], y=[kpi["ab_p1"]*100, kpi["ab_p2"]*100],
                                    marker_color=[PALETTE["slate"], PALETTE["primary"]],
                                    text=[f"{kpi['ab_p1']*100:.1f}%", f"{kpi['ab_p2']*100:.1f}%"], textposition="outside"))
            fig.update_layout(title="Order Completion Rate")
            with st.container(border=True):
                chart_card(fig)
        with c2:
            fig = go.Figure(go.Bar(x=["Control", "Treatment"], y=[kpi["ab_control_aov_mean"], kpi["ab_treat_aov_mean"]],
                                    marker_color=[PALETTE["slate"], PALETTE["amber"]],
                                    text=[f"{kpi['ab_control_aov_mean']:,.0f}", f"{kpi['ab_treat_aov_mean']:,.0f}"], textposition="outside"))
            fig.update_layout(title="Average Order Value")
            with st.container(border=True):
                chart_card(fig)

st.caption("Built with Streamlit + Polars + Plotly + SciPy · Deployed free on Streamlit Community Cloud / Hugging Face Spaces")
