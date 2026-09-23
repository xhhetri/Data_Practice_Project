"""
app/streamlit_app.py
---------------------
Stage 7 of the project lifecycle: Deployment & Visualization.

An interactive Streamlit dashboard that reads from the project's DBMS
(src/db.py) rather than loose CSVs -- a second, Python-native
visualization surface alongside the existing static `dashboard/index.html`
(which stays as-is; this doesn't replace it, it adds the "enable user
interaction" piece the lifecycle diagram calls for via a live app instead
of a pre-baked HTML file).

Run:
    streamlit run app/streamlit_app.py

If this is the first run and the database is empty, run the pipeline
first:
    python run_pipeline.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src import db  # noqa: E402

st.set_page_config(page_title="Transport Emissions (Australia)", layout="wide")

DRIFT_REPORT_PATH = REPO_ROOT / "reports" / "monitoring" / "drift_report.json"


@st.cache_resource
def get_engine():
    return db.get_engine()


@st.cache_data(ttl=60)
def load_table(table: str) -> pd.DataFrame:
    engine = get_engine()
    try:
        return pd.read_sql(f"SELECT * FROM {table}", engine)
    except Exception:
        return pd.DataFrame()


st.title("🚗 Transport Emissions (Australia) — Dashboard")
st.caption(
    "Reads live from the project's DBMS. If tables are empty, run "
    "`python run_pipeline.py` first to populate them."
)

annual = load_table("annual_master_with_population")
monthly = load_table("monthly_fuel_series")
metrics_df = load_table("model_metrics")

if annual.empty:
    st.warning(
        "No data in the database yet. Run `python run_pipeline.py` in a "
        "terminal, then reload this page."
    )
    st.stop()

tab_trends, tab_monthly, tab_models, tab_monitoring = st.tabs(
    ["Historical trends", "Monthly fuel", "Models", "Monitoring"]
)

with tab_trends:
    states = sorted(annual["state"].unique())
    selected_states = st.multiselect("States", states, default=states)
    metric = st.selectbox(
        "Metric",
        ["ghg_kt_co2e", "fuel_consumption_ml", "vkt_road_million_km",
         "registered_vehicles", "emissions_per_capita_kg"],
        format_func=lambda c: c.replace("_", " ").title(),
    )
    plot_df = annual[annual["state"].isin(selected_states)]
    fig = px.line(
        plot_df, x="year", y=metric, color="state", markers=True,
        title=f"{metric.replace('_', ' ').title()} by state",
    )
    st.plotly_chart(fig, width="stretch")

    if metric == "registered_vehicles":
        st.info(
            "Registered vehicles is sourced from BITRE Yearbook Table 4.6b "
            "(genuine annual state vehicle stock, 1982-2025) -- see README.md."
        )

with tab_monthly:
    if monthly.empty:
        st.info("No monthly_fuel_series table found.")
    else:
        states_m = sorted(monthly["state"].unique())
        selected_m = st.multiselect("States ", states_m, default=states_m[:3], key="monthly_states")
        fig2 = px.line(
            monthly[monthly["state"].isin(selected_m)], x="date", y="consumption_ml",
            color="state", title="Monthly fuel consumption (ML)",
        )
        st.plotly_chart(fig2, width="stretch")

with tab_models:
    if metrics_df.empty:
        st.info("No model_metrics table found -- run `python run_pipeline.py` first.")
    else:
        st.subheader("Regression (annual emissions)")
        reg = metrics_df[metrics_df["result_group"] == "emissions_regression"]
        st.dataframe(reg[["metric", "value"]], hide_index=True, width="stretch")

        st.subheader("Per-state fuel forecast (MAPE %)")
        forecast_rows = metrics_df[
            metrics_df["result_group"].str.startswith("fuel_forecast_")
            & (metrics_df["metric"] == "mape_pct")
        ].copy()
        if not forecast_rows.empty:
            forecast_rows["state"] = forecast_rows["result_group"].str.replace("fuel_forecast_", "")
            forecast_rows["value"] = forecast_rows["value"].astype(float)
            fig3 = px.bar(
                forecast_rows, x="state", y="value",
                title="Fuel forecast MAPE % by state (lower is better)",
                labels={"value": "MAPE %"},
            )
            st.plotly_chart(fig3, width="stretch")

        st.caption(
            "CV R² near 1 reflects the accounting identity behind official "
            "emissions figures, not a novel predictive result — see README.md."
        )

with tab_monitoring:
    st.subheader("Data drift (KS-test vs. baseline)")
    if not DRIFT_REPORT_PATH.exists():
        st.info("No drift report yet — run `python monitoring/monitor.py` first.")
    else:
        report = json.loads(DRIFT_REPORT_PATH.read_text())
        status = report.get("status", "unknown")
        badge = {"no_drift": "🟢", "drift_detected": "🔴", "baseline_created": "⚪"}.get(status, "⚪")
        st.markdown(f"**Status:** {badge} `{status}`  \n**Checked at:** {report.get('checked_at', '-')}")
        cols = report.get("columns", {})
        if cols:
            drift_df = pd.DataFrame.from_dict(cols, orient="index").reset_index()
            drift_df = drift_df.rename(columns={"index": "column"})
            st.dataframe(drift_df, hide_index=True, width="stretch")
        st.caption(
            "Re-run `python monitoring/monitor.py` after each new pipeline "
            "run to refresh this. Delete "
            "`reports/monitoring/reference_annual_master.csv` to re-baseline."
        )
