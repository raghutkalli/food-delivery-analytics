---
title: Food Delivery Product Analytics
emoji: 📊
colorFrom: blue
colorTo: orange
sdk: streamlit
sdk_version: "1.61.1"
app_file: app.py
pinned: false
---

# Food Delivery — Product Analytics Dashboard

Interactive product-analytics dashboard for a food-delivery marketplace,
running entirely on synthetic data (no database required). Computes 50+ KPIs
(acquisition, engagement, revenue, retention, operations, marketplace/supply,
CLV modeling, RFM segmentation, cohort analysis, demographic segmentation,
and an A/B testing framework).

**Key features:**
- Sidebar filters (date range, city, cuisine, channel, device, A/B group,
  gender, profession, income bracket, age group) that genuinely recompute
  every KPI and chart on the filtered slice — real drill-down, not cosmetic.
- Demographic segmentation tab: GMV/AOV/user-count by gender, age group,
  profession, and income bracket, plus a two-factor Gender × Age Group
  GMV cross-tab heatmap.
- Synthetic data auto-refreshes once every 24 hours (date-seeded generator +
  automatic page reload), so the dashboard is never static — or click
  "🔄 Refresh synthetic data" in the sidebar to force an immediate refresh.
- All timestamps shown in IST (Asia/Kolkata), regardless of the server's
  own clock/timezone.

Built with **Streamlit + Polars + Plotly + SciPy**.

See `DEPLOYMENT_GUIDE.md` (Streamlit Community Cloud), `HUGGINGFACE_DEPLOYMENT.md`
(this platform), or `STREAMLIT_GITHUB_DEPLOYMENT.md` (fully browser-based GitHub
+ Streamlit Cloud walkthrough) for setup steps.
