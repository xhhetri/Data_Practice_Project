"""
model.py
--------
Three models, matching the project's Theme 2 (Predictive Analytics and
Forecasting) brief:

1. train_emissions_regression() -- regression predicting annual state
   Transport-sector emissions from fuel, VKT and vehicle registrations.
   Cross-validated (not a single train/test split) since this table is
   small either way -- see clean.py: build_annual_master() for the
   current row count and coverage, which depends on what data (fixture
   or real) is loaded.

2. forecast_fuel_consumption() -- time-series baseline forecasting
   monthly petroleum consumption for a given state. Uses the full
   monthly series (far more points than the annual table), so this is
   the model worth trusting most once real data is loaded.

3. forecast_nsw_traffic() -- same forecasting method, applied to hourly
   NSW traffic volume instead of monthly fuel sales.

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

def train_emissions_regression() -> dict:
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
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(train.index, train.values, label="train")
    ax.plot(test.index, test.values, label="actual", marker="o")
    ax.plot(test.index, forecast.values, label="forecast", marker="x", linestyle="--")
    ax.set_title(f"Monthly fuel consumption forecast -- {state} ({method})")
    ax.set_ylabel("Consumption (ML)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(REPO_ROOT / "reports" / "figures" / f"06_forecast_{state}.png", dpi=150)
    plt.close(fig)

    result = {
        "state": state,
        "method": method,
        "test_months": test_months,
        "mae_ml": round(mae, 2),
        "mape_pct": round(mape, 2),
        "_caveat": _data_source_caveat(),
    }
    log.info("Forecast (%s, %s): MAE=%.1f ML, MAPE=%.1f%%", state, method, mae, mape)
    return result


def forecast_nsw_traffic(station: str = "NSW-STN-001", test_hours: int = 24) -> dict:
    """
    Hourly traffic volume forecast for one station, 24-hour seasonality.
    Different data shape from forecast_fuel_consumption (hourly not
    monthly, single-state not multi-state) but same method, for
    consistency and to reuse the same fallback logic.
    """
    _ensure_processed()
    df = pd.read_csv(PROCESSED_DIR / "nsw_traffic_hourly.csv", parse_dates=["timestamp"])
    series = (
        df[df["station_id"] == station]
        .sort_values("timestamp")
        .set_index("timestamp")["vehicle_count"]
    )

    if len(series) < test_hours + 48:
        log.warning(
            "Only %d hours of data for %s -- forecast may be unreliable",
            len(series), station,
        )

    train, test = series.iloc[:-test_hours], series.iloc[-test_hours:]

    try:
        from statsmodels.tsa.holtwinters import ExponentialSmoothing
        model = ExponentialSmoothing(
            train, trend="add", seasonal="add", seasonal_periods=24
        ).fit()
        forecast = model.forecast(test_hours)
        method = "holt_winters"
    except Exception as e:
        log.warning("statsmodels forecast failed (%s) -- using seasonal-naive fallback", e)
        forecast = train.iloc[-24:-24 + test_hours]
        forecast.index = test.index
        method = "seasonal_naive_fallback"

    mae = mean_absolute_error(test, forecast)
    mape = float(np.mean(np.abs((test - forecast.values) / test.replace(0, np.nan))) * 100)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(train.index[-72:], train.values[-72:], label="train (last 72h)")
    ax.plot(test.index, test.values, label="actual", marker="o")
    ax.plot(test.index, forecast.values, label="forecast", marker="x", linestyle="--")
    ax.set_title(f"Hourly traffic forecast -- {station} ({method})")
    ax.set_ylabel("Vehicle count")
    ax.legend()
    fig.tight_layout()
    fig.savefig(REPO_ROOT / "reports" / "figures" / f"08_traffic_forecast_{station}.png", dpi=150)
    plt.close(fig)

    result = {
        "station": station,
        "method": method,
        "test_hours": test_hours,
        "mae_vehicles": round(mae, 2),
        "mape_pct": round(mape, 2),
        "_caveat": _data_source_caveat(),
    }
    log.info("Traffic forecast (%s, %s): MAE=%.1f vehicles, MAPE=%.1f%%",
              station, method, mae, mape)
    return result


def run() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    all_results = {
        "emissions_regression": train_emissions_regression(),
        "fuel_forecast_NSW": forecast_fuel_consumption("NSW"),
    }

    traffic_path = PROCESSED_DIR / "nsw_traffic_hourly.csv"
    if traffic_path.exists():
        all_results["nsw_traffic_forecast"] = forecast_nsw_traffic()

    with open(RESULTS_DIR / "metrics.json", "w") as f:
        json.dump(all_results, f, indent=2)
    log.info("All model results written to %s", RESULTS_DIR / "metrics.json")


if __name__ == "__main__":
    run()