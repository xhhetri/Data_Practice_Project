"""
eda.py
------
Exploratory data analysis on the processed tables built by clean.py.
Every figure is saved to reports/figures/ rather than shown interactively,
so this can run headless (CI, or this sandbox) and the outputs are
committable evidence for the report/repo.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # headless backend -- no display needed
import matplotlib.pyplot as plt
import pandas as pd

# Allow both `python -m src.analysis.eda` and direct script execution.
try:
    from src.analysis.clean import PROCESSED_DIR, REPO_ROOT, run as run_clean
except ModuleNotFoundError as exc:
    if exc.name != "src":
        raise
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from src.analysis.clean import PROCESSED_DIR, REPO_ROOT, run as run_clean

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

FIGURES_DIR = REPO_ROOT / "reports" / "figures"

FEATURE_COLS = ["fuel_consumption_ml", "vkt_road_million_km", "registered_vehicles"]
TARGET_COL = "ghg_kt_co2e"


def _load_processed() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load processed tables, building them first if they don't exist yet."""
    annual_path = PROCESSED_DIR / "annual_master.csv"
    if not annual_path.exists():
        log.info("Processed tables not found -- running clean.run() first")
        run_clean()

    annual = pd.read_csv(PROCESSED_DIR / "annual_master.csv")
    annual_pop = pd.read_csv(PROCESSED_DIR / "annual_master_with_population.csv")
    monthly_fuel = pd.read_csv(
        PROCESSED_DIR / "monthly_fuel_series.csv", parse_dates=["date"]
    )
    return annual, annual_pop, monthly_fuel


def plot_distributions(annual: pd.DataFrame) -> None:
    """Histogram of each numeric feature and the target."""
    cols = FEATURE_COLS + [TARGET_COL]
    fig, axes = plt.subplots(2, 2, figsize=(10, 8))
    for ax, col in zip(axes.flat, cols):
        ax.hist(annual[col], bins=12, edgecolor="black")
        ax.set_title(col)
        ax.set_xlabel(col)
        ax.set_ylabel("count")
    fig.suptitle("Distributions -- annual state-level features (n=48)")
    fig.tight_layout()
    out = FIGURES_DIR / "01_distributions.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    log.info("Saved %s", out)


def plot_state_trends(annual: pd.DataFrame) -> None:
    """Road transport emissions over time, one line per state."""
    fig, ax = plt.subplots(figsize=(9, 6))
    for state, grp in annual.groupby("state"):
        grp = grp.sort_values("year")
        ax.plot(grp["year"], grp[TARGET_COL], marker="o", label=state)
    ax.set_title("Road transport GHG emissions by state, 2020-2025")
    ax.set_xlabel("Year")
    ax.set_ylabel("kt CO2-e")
    ax.legend(ncol=2, fontsize=8)
    fig.tight_layout()
    out = FIGURES_DIR / "02_emissions_trend_by_state.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    log.info("Saved %s", out)


def plot_correlation_heatmap(annual: pd.DataFrame) -> None:
    """
    Correlation matrix across features and target.

    Caveat (state this in the report): the current data behind this figure
    is synthetic fixture data, not the live government sources, so these
    correlations are not evidence of a real relationship -- they only
    prove the pipeline computes correlations correctly. Re-run against
    live data before citing any correlation figure.
    """
    corr = annual[FEATURE_COLS + [TARGET_COL]].corr()
    fig, ax = plt.subplots(figsize=(7, 6))
    im = ax.imshow(corr, cmap="coolwarm", vmin=-1, vmax=1)
    ax.set_xticks(range(len(corr.columns)))
    ax.set_yticks(range(len(corr.columns)))
    ax.set_xticklabels(corr.columns, rotation=45, ha="right")
    ax.set_yticklabels(corr.columns)
    for i in range(len(corr.columns)):
        for j in range(len(corr.columns)):
            ax.text(j, i, f"{corr.iloc[i, j]:.2f}", ha="center", va="center")
    fig.colorbar(im, label="Pearson correlation")
    ax.set_title("Feature correlation matrix (fixture data -- see caveat in docstring)")
    fig.tight_layout()
    out = FIGURES_DIR / "03_correlation_heatmap.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    log.info("Saved %s", out)


def plot_monthly_fuel_series(monthly_fuel: pd.DataFrame, state: str = "NSW") -> None:
    """Monthly fuel consumption for one state -- the forecasting target."""
    sub = monthly_fuel[monthly_fuel["state"] == state].sort_values("date")
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(sub["date"], sub["consumption_ml"])
    ax.set_title(f"Monthly petroleum consumption -- {state}")
    ax.set_xlabel("Month")
    ax.set_ylabel("Consumption (ML)")
    fig.tight_layout()
    out = FIGURES_DIR / f"04_monthly_fuel_{state}.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    log.info("Saved %s", out)


def plot_per_capita(annual_pop: pd.DataFrame) -> None:
    """
    Per-capita emissions vs per-capita VKT -- the Kaya-decomposition-style
    view. n=16 (2024-2025 only, population data doesn't go back further
    in the current sources) -- treat as illustrative, not conclusive.
    """
    fig, ax = plt.subplots(figsize=(7, 6))
    for state, grp in annual_pop.groupby("state"):
        ax.scatter(grp["vkt_per_capita_km"], grp["emissions_per_capita_kg"], label=state)
    ax.set_xlabel("VKT per capita (km)")
    ax.set_ylabel("Emissions per capita (kg CO2-e)")
    ax.set_title("Per-capita emissions vs travel demand (n=16 -- illustrative only)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    out = FIGURES_DIR / "05_per_capita_scatter.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    log.info("Saved %s", out)


def run() -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    annual, annual_pop, monthly_fuel = _load_processed()

    plot_distributions(annual)
    plot_state_trends(annual)
    plot_correlation_heatmap(annual)
    plot_monthly_fuel_series(monthly_fuel, state="NSW")
    plot_per_capita(annual_pop)

    log.info("EDA complete -- figures in %s", FIGURES_DIR)


if __name__ == "__main__":
    run()
