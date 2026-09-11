"""
model.py
--------
Two models, matching the project's Theme 2 (Predictive Analytics and
Forecasting) brief:

1. fit_emissions_regression() -- regression predicting annual state
   Transport-sector emissions from fuel, VKT and vehicle registrations.
   Cross-validated (not a single train/test split) since this table is
   small either way -- see clean.py: build_annual_master() for the
   current row count and coverage, which depends on what data (fixture
   or real) is loaded.

2. forecast_fuel_consumption() -- time-series baseline forecasting
   monthly petroleum consumption for a given state. Uses the full
   monthly series (far more points than the annual table), so this is
   the model worth trusting most once real data is loaded.

CAVEAT, stated once here rather than scattered as comments: whether
these results mean anything depends entirely on whether real or
fixture data is currently loaded -- check the "Using real data" /
"Using sample data" log lines clean.py prints when you run this. On
fixture data (synthetic, randomly generated per source independently)
these metrics demonstrate the code runs correctly end-to-end and
nothing more -- they are NOT evidence about real Australian emissions
patterns. On real data, expect near-tautological regression scores
(R^2 close to 1) since reported emissions are *constructed from* fuel
sales via published factors -- that's expected structure, not a
genuine predictive achievement, and doesn't need re-verifying every run.
"""

from __future__ import annotations

import json
import logging
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import KFold, cross_val_predict
from sklearn.metrics import mean_absolute_error, r2_score

try:
    from src.analysis.clean import PROCESSED_DIR, REPO_ROOT, run as run_clean
    from src.analysis.eda import FEATURE_COLS, TARGET_COL
except ModuleNotFoundError as exc:
    if exc.name != "src":
        raise
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from src.analysis.clean import PROCESSED_DIR, REPO_ROOT, run as run_clean
    from src.analysis.eda import FEATURE_COLS, TARGET_COL

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

RESULTS_DIR = REPO_ROOT / "reports" / "model_results"


def _ensure_processed() -> None:
    if not (PROCESSED_DIR / "annual_master.csv").exists():
        run_clean()


def _data_source_caveat() -> str:
    """
    Deliberately does NOT assert whether real or fixture data produced
    this result -- that depends entirely on what was in data/bronze/
    when clean.py last ran (see its "Using real data" / "Using sample
    data" / "Falling back to fixture" log lines for the actual answer
    on this specific run). A hardcoded caveat here would be right half
    the time and silently wrong the other half.
    """
    return (
        "Whether this reflects real or synthetic fixture data depends on "
        "this run's sources -- check the 'Using real data' / 'Using sample "
        "data' / 'Falling back to fixture' log lines clean.py printed "
        "during Step 1 of this pipeline run before citing this number."
    )


# ---------------------------------------------------------------------
# Model 1: annual emissions regression (cross-validated)
# ---------------------------------------------------------------------

def fit_emissions_regression() -> dict:
    _ensure_processed()
    df = pd.read_csv(PROCESSED_DIR / "annual_master.csv")
    X = df[FEATURE_COLS].values
    y = df[TARGET_COL].values

    cv = KFold(n_splits=5, shuffle=True, random_state=42)
    results = {}

    for name, model in [
        ("linear_regression", LinearRegression()),
        ("random_forest", RandomForestRegressor(n_estimators=200, random_state=42)),
    ]:
        preds = cross_val_predict(model, X, y, cv=cv)
        r2 = r2_score(y, preds)
        mae = mean_absolute_error(y, preds)
        results[name] = {"cv_r2": round(r2, 4), "cv_mae_kt_co2e": round(mae, 2)}
        log.info("%s -- CV R2=%.3f, CV MAE=%.1f kt CO2-e", name, r2, mae)

    # Fit the random forest on all data for a feature-importance view
    # (this is exploratory, not a trained/deployed model -- honest labelling)
    rf_full = RandomForestRegressor(n_estimators=200, random_state=42)
    rf_full.fit(X, y)
    importances = dict(zip(FEATURE_COLS, rf_full.feature_importances_.round(4)))
    results["random_forest"]["feature_importance"] = importances
    log.info("Random forest feature importances: %s", importances)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_DIR / "emissions_regression.pkl", "wb") as f:
        pickle.dump(rf_full, f)

    results["_caveat"] = f"n={len(df)}. {_data_source_caveat()}"
    return results


# ---------------------------------------------------------------------
# Model 2: monthly fuel consumption forecast (per state)
# ---------------------------------------------------------------------

def forecast_fuel_consumption(state: str = "NSW", test_months: int = 6) -> dict:
    _ensure_processed()
    df = pd.read_csv(PROCESSED_DIR / "monthly_fuel_series.csv", parse_dates=["date"])
    series = (
        df[df["state"] == state]
        .sort_values("date")
        .set_index("date")["consumption_ml"]
    )

    if len(series) < test_months + 12:
        log.warning(
            "Only %d months of data for %s -- forecast may be unreliable",
            len(series), state,
        )

    train, test = series.iloc[:-test_months], series.iloc[-test_months:]

    try:
        from statsmodels.tsa.holtwinters import ExponentialSmoothing
        model = ExponentialSmoothing(
            train, trend="add", seasonal="add", seasonal_periods=12
        ).fit()
        forecast = model.forecast(test_months)
        method = "holt_winters"
    except Exception as e:
        # Dependency-free fallback: naive seasonal (repeat same month last year)
        log.warning("statsmodels forecast failed (%s) -- using seasonal-naive fallback", e)
        forecast = train.iloc[-12:-12 + test_months]
        forecast.index = test.index
        method = "seasonal_naive_fallback"

    mae = mean_absolute_error(test, forecast)
    mape = float(np.mean(np.abs((test - forecast.values) / test)) * 100)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(train.index, train.values, label="train")
    ax.plot(test.index, test.values, label="actual", marker="o")
    ax.plot(test.index, forecast.values, label="forecast", marker="x", linestyle="--")
    ax.set_title(f"Monthly fuel consumption forecast -- {state} ({method})")
    ax.set_ylabel("Consumption (ML)")
    ax.legend()
    fig.tight_layout()
    out = REPO_ROOT / "reports" / "figures" / f"06_forecast_{state}.png"
    fig.savefig(out, dpi=150)
    log.info("Saved %s", out)

    result = {
        "state": state,
        "method": method,
        "test_months": test_months,
        "mae_ml": round(mae, 2),
        "mape_pct": round(mape, 2),
        "_caveat": _data_source_caveat(),
        "_figure": fig,  # not JSON-serialisable -- run() pops this before dumping to
                          # metrics.json; a notebook can grab it directly to display inline
        "series": {
            # Full series as {date, value} lists -- used by scripts/build_dashboard.py
            # to draw the actual train/actual/forecast lines interactively, not just
            # report the summary MAE/MAPE numbers. Dates as ISO strings so this stays
            # JSON-serialisable (unlike the pandas Timestamp index itself).
            "train": [{"date": d.strftime("%Y-%m-%d"), "value": round(v, 1)}
                      for d, v in train.items()],
            "actual": [{"date": d.strftime("%Y-%m-%d"), "value": round(v, 1)}
                       for d, v in test.items()],
            "forecast": [{"date": d.strftime("%Y-%m-%d"), "value": round(v, 1)}
                         for d, v in forecast.items()],
        },
    }
    log.info("Forecast (%s, %s): MAE=%.1f ML, MAPE=%.1f%%", state, method, mae, mape)
    return result


def run() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    all_results = {
        "emissions_regression": fit_emissions_regression(),
    }

    _ensure_processed()
    monthly = pd.read_csv(PROCESSED_DIR / "monthly_fuel_series.csv")
    states = sorted(monthly["state"].unique())
    log.info("Forecasting fuel consumption for all %d states: %s", len(states), states)
    for state in states:
        result = forecast_fuel_consumption(state)
        fig = result.pop("_figure")  # script/CI run -- nothing will display this, free the memory
        plt.close(fig)
        all_results[f"fuel_forecast_{state}"] = result

    with open(RESULTS_DIR / "metrics.json", "w") as f:
        json.dump(all_results, f, indent=2)
    log.info("All model results written to %s", RESULTS_DIR / "metrics.json")


if __name__ == "__main__":
    run()