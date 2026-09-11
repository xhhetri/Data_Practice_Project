"""
scripts/build_dashboard.py
----------------------------
Assembles a self-contained, interactive dashboard (dashboard/index.html)
from the pipeline's real output -- reads the processed CSVs and
reports/model_results/, reports/validation/, and embeds them directly
as JSON inside the HTML. No server, no fetch(), no CORS issues -- open
the file directly in a browser.

Run after the pipeline: python run_pipeline.py && python scripts/build_dashboard.py
Regenerate any time the underlying data changes -- this doesn't run
automatically as part of run_pipeline.py, since the dashboard is a
presentation layer on top of the pipeline's output, not part of the
pipeline itself.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = REPO_ROOT / "data" / "processed"
RESULTS_DIR = REPO_ROOT / "reports" / "model_results"
VALIDATION_DIR = REPO_ROOT / "reports" / "validation"
DASHBOARD_DIR = REPO_ROOT / "dashboard"
TEMPLATE_PATH = DASHBOARD_DIR / "template.html"
OUTPUT_PATH = DASHBOARD_DIR / "index.html"


def _require(path: Path, hint: str) -> None:
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. {hint}"
        )


def build_data() -> dict:
    _require(PROCESSED_DIR / "annual_master.csv",
              "Run `python run_pipeline.py` first.")
    _require(RESULTS_DIR / "metrics.json",
              "Run `python run_pipeline.py` first.")

    annual = pd.read_csv(PROCESSED_DIR / "annual_master.csv")
    annual_pop = pd.read_csv(PROCESSED_DIR / "annual_master_with_population.csv")
    monthly = pd.read_csv(PROCESSED_DIR / "monthly_fuel_series.csv")
    metrics = json.loads((RESULTS_DIR / "metrics.json").read_text())

    states = sorted(annual["state"].unique().tolist())

    def group_by_state(df: pd.DataFrame, cols: list[str]) -> dict:
        out = {}
        for state, grp in df.groupby("state"):
            grp = grp.sort_values(grp.columns[1] if "year" not in grp.columns else "year")
            out[state] = grp[cols].to_dict("records")
        return out

    annual_cols = ["year", "fuel_consumption_ml", "vkt_road_million_km",
                    "registered_vehicles", "ghg_kt_co2e"]
    per_capita_cols = ["year", "emissions_per_capita_kg", "vkt_per_capita_km",
                        "vehicles_per_capita", "population"]
    monthly_cols = ["date", "consumption_ml"]

    data = {
        "meta": {
            "states": states,
            "year_min": int(annual["year"].min()),
            "year_max": int(annual["year"].max()),
        },
        "annual": group_by_state(annual, annual_cols),
        "per_capita": group_by_state(annual_pop, per_capita_cols),
        "monthly_fuel": group_by_state(monthly, monthly_cols),
        "regression": {
            k: v for k, v in metrics.get("emissions_regression", {}).items()
        },
        "forecasts": {},
        "validation": None,
    }

    for state in states:
        key = f"fuel_forecast_{state}"
        if key in metrics:
            f = metrics[key]
            data["forecasts"][state] = {
                "method": f["method"],
                "mae_ml": f["mae_ml"],
                "mape_pct": f["mape_pct"],
                "series": f["series"],
            }

    val_path = VALIDATION_DIR / "emission_factor_check.csv"
    if val_path.exists():
        val = pd.read_csv(val_path)
        data["validation"] = {
            "rows": val[["state", "year", "implied_kt_co2e", "ghg_kt_co2e", "pct_diff"]]
                .round(2).to_dict("records"),
            "mean_pct_diff": round(val["pct_diff"].mean(), 1),
        }

    return data


def build_html(data: dict) -> str:
    _require(TEMPLATE_PATH, "template.html should be committed alongside this script.")
    template = TEMPLATE_PATH.read_text()
    data_json = json.dumps(data, indent=None)
    if "/*__DASHBOARD_DATA__*/" not in template:
        raise ValueError("template.html is missing the /*__DASHBOARD_DATA__*/ placeholder")
    return template.replace("/*__DASHBOARD_DATA__*/", f"const DATA = {data_json};")


def run() -> None:
    data = build_data()
    html = build_html(data)
    OUTPUT_PATH.write_text(html)
    size_kb = OUTPUT_PATH.stat().st_size / 1024
    print(f"Wrote {OUTPUT_PATH} ({size_kb:.0f} KB) -- "
          f"{len(data['meta']['states'])} states, "
          f"{data['meta']['year_min']}-{data['meta']['year_max']}, "
          f"{len(data['forecasts'])} forecasts, "
          f"validation: {'included' if data['validation'] else 'skipped (no file)'}")


if __name__ == "__main__":
    run()
