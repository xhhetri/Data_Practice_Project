"""
validate.py
------------
One data-quality check that uses a source loaded but never consumed by
clean.py's master tables: nga_factors_2025.

validate_emission_factors() -- checks whether reported transport-sector
emissions are consistent with (fuel consumed x published emission
factor). This is the accounting identity referenced throughout this
project's docs: real emissions inventories are *constructed* this way,
so on real data this should match reasonably closely. A gap far outside
the expected range would mean either a units error in this pipeline, or
that transport emissions include fuel types/sources not captured in
petroleum_statistics (e.g. LPG, biodiesel blending) -- both worth
knowing before citing the regression in model.py.

This is a diagnostic report, not a model -- it writes a CSV + a plot to
reports/validation/, and logs a plain-English summary.

(A second check, validate_ghg_cross_source(), previously compared this
project's CSV-sourced emissions against a National Greenhouse Accounts
OData API pull. That data source has been descoped -- see CHANGELOG.md
-- and the check removed along with it, rather than left as a
half-working reference to a source no longer in scope.)
"""

from __future__ import annotations

import logging

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from src.analysis.clean import (
    PROCESSED_DIR,
    REPO_ROOT,
    load_nga_factors,
    load_petroleum_statistics,
    load_state_territory_ghg,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

VALIDATION_DIR = REPO_ROOT / "reports" / "validation"


def validate_emission_factors() -> pd.DataFrame:
    """
    implied_kt_co2e = annual fuel consumption (ML) x factor (kg CO2e / L)
    -- the ML->L and kg->kt conversions cancel exactly (both 1e6), so no
    extra scaling constant is needed. Compared against the reported
    state Transport-sector emissions for the same state/financial-year.

    Uses fuel's fy_year (not its calendar 'year') to match
    state_territory_ghg's financial-year convention -- see
    clean.py's _fy_start_from_date(). Grouping by calendar year here
    would silently misalign roughly half of each year's transactions
    against the wrong financial year.

    A gap between implied and reported is EXPECTED, not necessarily a
    bug: state_territory_ghg's "Transport" row is the whole transport
    sector (road + rail + domestic aviation + shipping -- see that
    loader's docstring), while this implied figure only covers
    road fuel (petrol + diesel). Implied should therefore run LOWER
    than reported, roughly in proportion to road's typical ~85-90%
    share of transport-sector fuel use nationally. A gap far outside
    that range is worth investigating; a gap within it is exactly what
    this methodology predicts.
    """
    fuel = (
        load_petroleum_statistics()
        .groupby(["state", "fy_year", "product"], as_index=False)["consumption_ml"]
        .sum()
        .rename(columns={"fy_year": "year"})
    )
    factors = load_nga_factors().rename(columns={"fuel_type": "product"})
    fuel = fuel.merge(factors, on="product", how="left")

    missing_factor = fuel["factor_kg_co2e_per_l"].isna()
    if missing_factor.any():
        log.warning(
            "%d rows have no matching emission factor for product(s): %s -- "
            "these are excluded from the implied-emissions total",
            missing_factor.sum(),
            fuel.loc[missing_factor, "product"].unique().tolist(),
        )
    fuel = fuel.dropna(subset=["factor_kg_co2e_per_l"])
    fuel["implied_kt_co2e"] = fuel["consumption_ml"] * fuel["factor_kg_co2e_per_l"]

    implied = fuel.groupby(["state", "year"], as_index=False)["implied_kt_co2e"].sum()

    reported = (
        load_state_territory_ghg()
        .query("sector == 'Transport'")
        .groupby(["state", "year"], as_index=False)["ghg_kt_co2e"]
        .sum()
    )

    comparison = implied.merge(reported, on=["state", "year"], how="inner")
    comparison["abs_diff_kt"] = (comparison["implied_kt_co2e"] - comparison["ghg_kt_co2e"]).abs()
    comparison["pct_diff"] = (
        comparison["abs_diff_kt"] / comparison["ghg_kt_co2e"].replace(0, pd.NA) * 100
    )

    VALIDATION_DIR.mkdir(parents=True, exist_ok=True)
    comparison.to_csv(VALIDATION_DIR / "emission_factor_check.csv", index=False)

    mean_pct = comparison["pct_diff"].mean()
    log.info(
        "Emission factor check: implied road-fuel emissions run %.1f%% "
        "below reported whole-transport-sector emissions on average "
        "(n=%d state-years). This is expected, not necessarily an error -- "
        "see this function's docstring: reported figures include rail, "
        "aviation and shipping that this road-fuel-only calculation "
        "doesn't cover. A gap outside roughly 10-20%% is worth "
        "investigating further; within that range is consistent with "
        "road's typical share of transport-sector fuel use.",
        mean_pct, len(comparison),
    )

    fig, ax = plt.subplots(figsize=(6, 6))
    ax.scatter(comparison["ghg_kt_co2e"], comparison["implied_kt_co2e"])
    lims = [0, max(comparison["ghg_kt_co2e"].max(), comparison["implied_kt_co2e"].max()) * 1.05]
    ax.plot(lims, lims, linestyle="--", color="gray", label="perfect agreement")
    ax.set_xlabel("Reported transport-sector emissions (kt CO2-e)")
    ax.set_ylabel("Implied road-fuel emissions: fuel x factor (kt CO2-e)")
    ax.set_title(f"Emission factor validation (n={len(comparison)})")
    ax.legend()
    fig.tight_layout()
    fig.savefig(VALIDATION_DIR / "emission_factor_check.png", dpi=150)
    plt.close(fig)

    return comparison


def run() -> None:
    validate_emission_factors()
    log.info("Validation reports written to %s", VALIDATION_DIR)


if __name__ == "__main__":
    run()