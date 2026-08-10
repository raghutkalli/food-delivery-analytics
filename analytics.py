"""Pure data-cleaning + KPI-computation logic — no Streamlit dependency.
Same logic as the notebook's Sections 3-K, refactored into functions so the
Streamlit app (and any other consumer) can call it directly and so it can be
unit-tested outside of Streamlit.
"""
import datetime as dt
import numpy as np
import polars as pl
from scipy import stats


# ---------------------------------------------------------------------
# Section 3 — Cleaning
# ---------------------------------------------------------------------
def _parse_date(df: pl.DataFrame, col: str) -> pl.Expr:
    if df.schema[col] == pl.Utf8:
        return pl.col(col).str.strptime(pl.Date, strict=False)
    return pl.col(col).cast(pl.Date, strict=False)


def _parse_datetime(df: pl.DataFrame, col: str) -> pl.Expr:
    if df.schema[col] == pl.Utf8:
        return pl.col(col).str.strptime(pl.Datetime, strict=False)
    return pl.col(col).cast(pl.Datetime, strict=False)


def clean_data(users, restaurants, riders, orders, events, nps):
    """Returns (users_clean, orders_clean, events_clean, nps_clean, restaurants, riders)."""

    # ---- USERS ----
    if users.schema["signup_date"] == pl.Utf8:
        signup_expr = (
            pl.col("signup_date").str.strptime(pl.Date, format="%Y-%m-%d", strict=False)
            .fill_null(pl.col("signup_date").str.strptime(pl.Date, format="%d/%m/%Y", strict=False))
            .alias("signup_date")
        )
    else:
        signup_expr = pl.col("signup_date").cast(pl.Date, strict=False).alias("signup_date")

    users_clean = (
        users.unique(subset=["user_id"], keep="first")
        .with_columns([
            pl.col("city").str.strip_chars().str.to_titlecase(),
            signup_expr,
            pl.col("device_type").fill_null("Unknown"),
            pl.col("age").fill_null(pl.col("age").median()),
        ])
    )

    # ---- ORDERS ----
    ts_cols = ["order_placed_time", "order_accepted_time", "promised_delivery_time",
               "ready_time", "pickup_time", "delivered_time"]
    orders_clean = (
        orders.unique(subset=["order_id"], keep="first")
        .with_columns([pl.col("payment_method").str.to_titlecase()]
                      + [_parse_datetime(orders, c).alias(c) for c in ts_cols]
                      + [pl.col("delivery_fee").abs()])
        .filter(pl.col("order_value").is_not_null())
    )
    q1, q3 = orders_clean["order_value"].quantile(0.25), orders_clean["order_value"].quantile(0.75)
    upper_fence = q3 + 1.5 * (q3 - q1)
    orders_clean = orders_clean.with_columns(
        pl.when(pl.col("order_value") > upper_fence).then(upper_fence).otherwise(pl.col("order_value")).alias("order_value")
    ).with_columns([
        pl.col("order_placed_time").dt.date().alias("order_date"),
        pl.col("order_placed_time").dt.strftime("%Y-%m").alias("order_month"),
    ])

    for c in ["complaint_flag", "wrong_item_flag", "is_promo_used", "is_scheduled_order"]:
        if c in orders_clean.columns and orders_clean.schema[c] != pl.Boolean:
            orders_clean = orders_clean.with_columns(pl.col(c).cast(pl.Int64, strict=False).cast(pl.Boolean).alias(c))
    if "is_subscriber" in users_clean.columns and users_clean.schema["is_subscriber"] != pl.Boolean:
        users_clean = users_clean.with_columns(pl.col("is_subscriber").cast(pl.Int64, strict=False).cast(pl.Boolean).alias("is_subscriber"))

    # ---- APP EVENTS ----
    events_clean = events.unique().with_columns(_parse_datetime(events, "event_time").alias("event_time"))

    # ---- NPS ----
    nps_clean = (
        nps.unique(subset=["response_id"], keep="first")
        .with_columns(_parse_date(nps, "response_date").alias("response_date"))
        .filter(pl.col("nps_score").is_between(0, 10))
    )

    return users_clean, orders_clean, events_clean, nps_clean, restaurants, riders


# ---------------------------------------------------------------------
# Sections A-K — All KPIs, condensed into one function.
# Returns (kpi: dict of scalars, charts: dict of supporting DataFrames)
# ---------------------------------------------------------------------
def compute_all_kpis(users_clean, orders_clean, events_clean, nps_clean, restaurants, riders):
    kpi = {}
    charts = {}

    # ---- A. Acquisition & Activation ----
    channel_acq = (
        users_clean.group_by("acquisition_channel").agg(pl.len().alias("new_users"))
        .sort("new_users", descending=True)
        .with_columns((pl.col("new_users") / pl.col("new_users").sum() * 100).round(1).alias("share_%"))
    )
    users_with_order = orders_clean["user_id"].unique().to_list()
    kpi["activation_rate"] = len(users_with_order) / users_clean.height * 100

    first_order = orders_clean.group_by("user_id").agg(pl.col("order_date").min().alias("first_order_date"))
    ttfo = (
        users_clean.join(first_order, on="user_id", how="inner")
        .with_columns((pl.col("first_order_date") - pl.col("signup_date")).dt.total_days().alias("ttfo_days"))
        .filter(pl.col("ttfo_days") >= 0)
    )
    kpi["avg_ttfo"] = ttfo["ttfo_days"].mean()

    ASSUMED_MONTHLY_MARKETING_SPEND = 50_000
    months_covered = (
        users_clean.with_columns(pl.col("signup_date").dt.strftime("%Y-%m").alias("signup_month"))["signup_month"].n_unique()
    )
    cac = (ASSUMED_MONTHLY_MARKETING_SPEND * months_covered) / len(users_with_order)
    kpi["cac"] = cac
    charts["channel_acq"] = channel_acq

    # ---- B. Engagement & Usage ----
    daily_active = orders_clean.group_by("order_date").agg(pl.col("user_id").n_unique().alias("dau")).sort("order_date")
    weekly_active = (
        orders_clean.with_columns(pl.col("order_date").dt.strftime("%Y-W%V").alias("order_week"))
        .group_by("order_week").agg(pl.col("user_id").n_unique().alias("wau")).sort("order_week")
    )
    monthly_active = orders_clean.group_by("order_month").agg(pl.col("user_id").n_unique().alias("mau")).sort("order_month")
    kpi["avg_dau"] = daily_active["dau"].mean()
    kpi["avg_wau"] = weekly_active["wau"].mean()
    kpi["avg_mau"] = monthly_active["mau"].mean()
    kpi["stickiness"] = kpi["avg_dau"] / kpi["avg_mau"] * 100
    kpi["orders_per_user"] = orders_clean.height / orders_clean["user_id"].n_unique()

    sessions_per_user = events_clean.group_by("user_id").agg(pl.col("session_id").n_unique().alias("sessions"))
    kpi["avg_session_frequency"] = sessions_per_user["sessions"].mean()

    session_duration = (
        events_clean.group_by("session_id").agg([pl.col("event_time").min().alias("start"), pl.col("event_time").max().alias("end")])
        .with_columns((pl.col("end") - pl.col("start")).dt.total_seconds().alias("duration_sec"))
    )
    kpi["avg_session_duration_sec"] = session_duration["duration_sec"].mean()
    charts["monthly_active"] = monthly_active

    # ---- C. Conversion & Funnel ----
    funnel_order = ["app_open", "menu_view", "add_to_cart", "checkout_started", "payment_completed"]
    funnel_counts = (
        events_clean.group_by("event_name").agg(pl.col("session_id").n_unique().alias("sessions"))
        .with_columns(pl.col("event_name").cast(pl.Enum(funnel_order))).sort("event_name")
    )
    top = funnel_counts["sessions"][0]
    funnel_counts = funnel_counts.with_columns((pl.col("sessions") / top * 100).round(1).alias("conversion_from_top_%"))
    total_sessions = events_clean["session_id"].n_unique()
    kpi["visitor_to_order_conv"] = orders_clean.height / total_sessions * 100

    menu_view_sessions = funnel_counts.filter(pl.col("event_name") == "menu_view")["sessions"][0]
    cart_sessions = funnel_counts.filter(pl.col("event_name") == "add_to_cart")["sessions"][0]
    kpi["menu_to_cart_rate"] = cart_sessions / menu_view_sessions * 100
    checkout_sessions = funnel_counts.filter(pl.col("event_name") == "checkout_started")["sessions"][0]
    kpi["cart_abandonment"] = (1 - checkout_sessions / cart_sessions) * 100

    total_orders_placed = orders_clean.height
    delivered = orders_clean.filter(pl.col("order_status") == "Delivered")
    kpi["order_completion_rate"] = delivered.height / total_orders_placed * 100
    charts["funnel_counts"] = funnel_counts

    # ---- D. Revenue & Monetization ----
    gmv = delivered["order_value"].sum()
    commission_revenue = (delivered["order_value"] * delivered["commission_rate"]).sum()
    delivery_fee_revenue = delivered["delivery_fee"].sum()
    platform_gross_revenue = commission_revenue + delivery_fee_revenue
    aov = delivered["order_value"].mean()
    kpi["gmv"] = gmv
    kpi["aov"] = aov
    kpi["arpu"] = platform_gross_revenue / users_clean.height
    kpi["arppu"] = platform_gross_revenue / orders_clean["user_id"].n_unique()
    kpi["take_rate"] = commission_revenue / gmv * 100

    delivered_econ = delivered.with_columns(
        (pl.col("order_value") * pl.col("commission_rate") + pl.col("delivery_fee")
         - pl.col("delivery_cost_to_rider") - pl.col("payment_gateway_fee") - pl.col("discount_amount")).alias("contribution_margin")
    )
    avg_contribution_margin = delivered_econ["contribution_margin"].mean()
    kpi["avg_contribution_margin"] = avg_contribution_margin

    gmv_trend = delivered.group_by("order_month").agg(pl.col("order_value").sum().alias("gmv")).sort("order_month")
    charts["gmv_trend"] = gmv_trend

    # ---- E. Retention & Loyalty ----
    oc = orders_clean.join(first_order, on="user_id").with_columns(
        (pl.col("order_date") - pl.col("first_order_date")).dt.total_days().alias("day_offset")
    )
    base_users = users_clean.height

    def retention_at(lo, hi):
        return oc.filter((pl.col("day_offset") > 0) & (pl.col("day_offset") <= hi) & (pl.col("day_offset") >= lo))["user_id"].n_unique() / base_users * 100

    kpi["d7"] = retention_at(1, 7)
    kpi["d30"] = retention_at(1, 30)
    kpi["churn_d30"] = 100 - kpi["d30"]

    orders_per_customer = orders_clean.group_by("user_id").agg(pl.col("order_id").n_unique().alias("n_orders"))
    kpi["repeat_rate"] = orders_per_customer.filter(pl.col("n_orders") >= 2).height / orders_per_customer.height * 100

    active_months_per_user = orders_clean.group_by("user_id").agg(pl.col("order_month").n_unique().alias("active_months"))
    retained_users = active_months_per_user.filter(pl.col("active_months") >= 2)["user_id"]
    retained_orders = orders_clean.filter(pl.col("user_id").is_in(retained_users))
    kpi["order_frequency_retained"] = retained_orders.height / retained_users.len() if retained_users.len() else 0.0

    user_ltv = (
        orders_clean.with_columns(
            (pl.col("order_value") * pl.col("commission_rate") + pl.col("delivery_fee")
             - pl.col("delivery_cost_to_rider") - pl.col("payment_gateway_fee") - pl.col("discount_amount")).alias("net_rev")
        ).group_by("user_id").agg(pl.col("net_rev").sum().alias("ltv"))
    )
    kpi["avg_ltv"] = user_ltv["ltv"].mean()
    kpi["ltv_cac_ratio"] = kpi["avg_ltv"] / cac

    promoters = nps_clean.filter(pl.col("nps_score") >= 9).height
    detractors = nps_clean.filter(pl.col("nps_score") <= 6).height
    total_resp = nps_clean.height
    kpi["nps_score"] = (promoters / total_resp - detractors / total_resp) * 100 if total_resp else 0.0

    # ---- F. Operational & Delivery ----
    kpi["cancellation_rate"] = orders_clean.filter(pl.col("order_status") == "Cancelled").height / total_orders_placed * 100
    ops = delivered.with_columns([
        (pl.col("delivered_time") - pl.col("order_placed_time")).dt.total_minutes().alias("delivery_time_min"),
        (pl.col("delivered_time") <= pl.col("promised_delivery_time")).alias("on_time"),
        (pl.col("ready_time") - pl.col("order_accepted_time")).dt.total_minutes().alias("prep_time_min"),
    ])
    kpi["avg_delivery_time"] = ops["delivery_time_min"].mean()
    kpi["on_time_rate"] = ops["on_time"].mean() * 100
    kpi["avg_prep_time"] = ops["prep_time_min"].mean()
    kpi["order_accuracy_rate"] = (1 - delivered["wrong_item_flag"].mean()) * 100
    kpi["cost_per_delivery"] = delivered["delivery_cost_to_rider"].sum() / delivered.height

    cancel_reasons = (
        orders_clean.filter(pl.col("order_status") == "Cancelled")
        .group_by("cancel_reason").agg(pl.len().alias("count")).sort("count", descending=True)
    )
    charts["cancel_reasons"] = cancel_reasons

    # ---- G. Marketplace / Supply-side ----
    active_restaurants = orders_clean["restaurant_id"].n_unique()
    total_restaurants = restaurants["restaurant_id"].n_unique()
    kpi["active_restaurants"] = active_restaurants
    kpi["total_restaurants"] = total_restaurants
    kpi["restaurant_utilization"] = delivered.height / active_restaurants

    orders_clean_h = orders_clean.with_columns(
        pl.when(pl.col("order_date") < dt.date(2025, 7, 1)).then(pl.lit("H1")).otherwise(pl.lit("H2")).alias("half")
    )
    h1 = set(orders_clean_h.filter(pl.col("half") == "H1")["restaurant_id"].unique().to_list())
    h2 = set(orders_clean_h.filter(pl.col("half") == "H2")["restaurant_id"].unique().to_list())
    lost = h1 - h2
    kpi["restaurant_churn_rate"] = (len(lost) / len(h1) * 100) if h1 else 0.0
    kpi["overall_avg_rating"] = delivered.filter(pl.col("rating").is_not_null())["rating"].mean()

    restaurant_gmv = delivered.group_by("restaurant_id").agg(pl.col("order_value").sum().alias("restaurant_gmv")).sort("restaurant_gmv", descending=True)
    kpi["top10_share"] = restaurant_gmv.head(10)["restaurant_gmv"].sum() / restaurant_gmv["restaurant_gmv"].sum() * 100
    charts["restaurant_gmv"] = restaurant_gmv

    cuisine_perf = (
        delivered.join(restaurants.select(["restaurant_id", "cuisine_type"]), on="restaurant_id")
        .group_by("cuisine_type").agg([pl.len().alias("orders"), pl.col("order_value").sum().round(0).alias("gmv")])
        .sort("gmv", descending=True)
    )
    city_perf = (
        delivered.group_by("city").agg([pl.len().alias("orders"), pl.col("order_value").sum().round(0).alias("gmv")])
        .sort("gmv", descending=True)
    )
    charts["cuisine_perf"] = cuisine_perf
    charts["city_perf"] = city_perf

    # ---- H. Product / Feature ----
    active_users_set = orders_clean["user_id"].unique()
    scheduled_order_users = orders_clean.filter(pl.col("is_scheduled_order") == True)["user_id"].n_unique()
    kpi["scheduled_order_adoption"] = scheduled_order_users / active_users_set.len() * 100

    subscriber_active_users = users_clean.filter(pl.col("is_subscriber") == True).join(
        orders_clean.select("user_id").unique(), on="user_id", how="inner"
    ).height
    kpi["subscriber_adoption"] = subscriber_active_users / active_users_set.len() * 100
    kpi["promo_dependency"] = orders_clean.filter(pl.col("is_promo_used") == True).height / total_orders_placed * 100
    kpi["avg_basket_size"] = orders_clean["items_count"].mean()

    # ---- I. Cohort, RFM & Segmentation ----
    cohort = (
        orders_clean.join(users_clean.select(["user_id", "signup_date"]), on="user_id")
        .with_columns([
            pl.col("signup_date").dt.strftime("%Y-%m").alias("cohort_month"),
            ((pl.col("order_date").dt.year() - pl.col("signup_date").dt.year()) * 12 +
             (pl.col("order_date").dt.month() - pl.col("signup_date").dt.month())).alias("month_offset")
        ]).filter(pl.col("month_offset") >= 0)
        .group_by(["cohort_month", "month_offset"]).agg(pl.col("user_id").n_unique().alias("active_users"))
    )
    cohort_size = (
        users_clean.with_columns(pl.col("signup_date").dt.strftime("%Y-%m").alias("cohort_month"))
        .group_by("cohort_month").agg(pl.len().alias("cohort_size"))
    )
    cohort_pct = (
        cohort.join(cohort_size, on="cohort_month")
        .with_columns((pl.col("active_users") / pl.col("cohort_size") * 100).round(1).alias("retention_%"))
        .sort(["cohort_month", "month_offset"])
    )
    cohort_matrix = cohort_pct.pivot(values="retention_%", index="cohort_month", on="month_offset").sort("cohort_month")
    heat_cols = [c for c in cohort_matrix.columns if c != "cohort_month"]
    heat_data = cohort_matrix.select(heat_cols).to_numpy().astype(float)
    charts["cohort_matrix"] = cohort_matrix
    charts["heat_cols"] = heat_cols
    charts["heat_data"] = heat_data

    snapshot_date = orders_clean["order_date"].max()
    rfm = orders_clean.group_by("user_id").agg([
        (snapshot_date - pl.col("order_date").max()).dt.total_days().alias("recency_days"),
        pl.col("order_id").n_unique().alias("frequency"),
        pl.col("order_value").sum().alias("monetary"),
    ])
    rfm = rfm.with_columns([
        pl.col("recency_days").rank(descending=True, method="ordinal").qcut(5, labels=["1", "2", "3", "4", "5"]).alias("R_score"),
        pl.col("frequency").rank(method="ordinal").qcut(5, labels=["1", "2", "3", "4", "5"]).alias("F_score"),
        pl.col("monetary").rank(method="ordinal").qcut(5, labels=["1", "2", "3", "4", "5"]).alias("M_score"),
    ])

    def label_segment(r, f, m):
        r, f, m = int(r), int(f), int(m)
        if r >= 4 and f >= 4:
            return "Champions"
        if r >= 4 and f <= 2:
            return "New / Promising"
        if r <= 2 and f >= 4:
            return "At Risk (was loyal)"
        if r <= 2 and f <= 2:
            return "Lost / Hibernating"
        return "Regular"

    rfm = rfm.with_columns(
        pl.struct(["R_score", "F_score", "M_score"]).map_elements(
            lambda s: label_segment(s["R_score"], s["F_score"], s["M_score"]), return_dtype=pl.Utf8
        ).alias("segment_label")
    )
    segment_summary = (
        rfm.group_by("segment_label")
        .agg([pl.len().alias("users"), pl.col("monetary").mean().round(0).alias("avg_spend"), pl.col("recency_days").mean().round(0).alias("avg_recency_days")])
        .sort("users", descending=True)
    )
    charts["segment_summary"] = segment_summary

    # ---- J. CLV Modeling ----
    observation_days = (orders_clean["order_date"].max() - orders_clean["order_date"].min()).days
    observation_years = max(observation_days / 365.25, 1 / 365.25)
    purchase_frequency_per_year = orders_per_customer["n_orders"].mean() / observation_years
    gross_margin_pct = avg_contribution_margin / aov
    ASSUMED_CUSTOMER_LIFESPAN_YEARS = 2.0
    kpi["clv_formulaic"] = aov * purchase_frequency_per_year * gross_margin_pct * ASSUMED_CUSTOMER_LIFESPAN_YEARS
    kpi["assumed_lifespan_years"] = ASSUMED_CUSTOMER_LIFESPAN_YEARS

    # ---- K. A/B Testing ----
    ab = orders_clean.group_by("ab_test_group").agg([
        pl.len().alias("n_orders"), (pl.col("order_status") == "Delivered").sum().alias("n_delivered"),
    ])
    control_row = ab.filter(pl.col("ab_test_group") == "Control")
    treat_row = ab.filter(pl.col("ab_test_group") == "Treatment")
    n1, x1 = control_row["n_orders"][0], control_row["n_delivered"][0]
    n2, x2 = treat_row["n_orders"][0], treat_row["n_delivered"][0]
    p1, p2 = x1 / n1, x2 / n2
    p_pool = (x1 + x2) / (n1 + n2)
    se = np.sqrt(p_pool * (1 - p_pool) * (1 / n1 + 1 / n2))
    z = (p2 - p1) / se
    p_value_completion = 2 * (1 - stats.norm.cdf(abs(z)))

    control_aov = delivered.filter(pl.col("ab_test_group") == "Control")["order_value"].to_numpy()
    treat_aov = delivered.filter(pl.col("ab_test_group") == "Treatment")["order_value"].to_numpy()
    t_stat, p_value_aov = stats.ttest_ind(treat_aov, control_aov, equal_var=False)

    kpi["ab_p1"], kpi["ab_p2"] = p1, p2
    kpi["ab_p_value_completion"] = p_value_completion
    kpi["ab_control_aov_mean"] = control_aov.mean()
    kpi["ab_treat_aov_mean"] = treat_aov.mean()
    kpi["ab_p_value_aov"] = p_value_aov

    # ---- Rating distribution (used by dashboard) ----
    rated = delivered.filter(pl.col("rating").is_not_null())
    rating_dist = rated.group_by("rating").agg(pl.len().alias("count")).sort("rating")
    charts["rating_dist"] = rating_dist

    return kpi, charts
