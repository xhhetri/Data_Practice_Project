"""
validate.py
------------
Two independent data-quality checks that use the two sources loaded but
never consumed by clean.py's master tables: nga_factors_2025 and
nga_odata_api.

1. validate_emission_factors() -- checks whether reported road transport
   emissions are consistent with (fuel consumed x published emission
   factor). This is the accounting identity referenced throughout this
   project's docs: real emissions inventories are *constructed* this way,
   so on real data this should match closely. A large, systematic gap
   would mean either a units error in this pipeline, or that road
   transport emissions include fuel types/sources not captured in
   petroleum_statistics (e.g. LPG, biodiesel blending) -- both worth
   knowing before citing the regression in model.py.

2. validate_ghg_cross_source() -- compares the published inventory table
   (state_territory_ghg.csv) against the same inventory pulled via the
   OData API (nga_odata_api.json). These should be near-identical since
   they're meant to be the same underlying data via two extraction
   paths; a mismatch flags a data pipeline bug or a vintage/version
   mismatch between the two pulls.

Both are diagnostic reports, not models -- they write CSVs + a plot to
reports/validation/, and log a plain-English summary.
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
    load_nga_odata_api,
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
    road transport emissions for the same state/year.
    """
    fuel = (
        load_petroleum_statistics()
        .groupby(["state", "year", "product"], as_index=False)["consumption_ml"]
        .sum()
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
        "Emission factor check: mean %% difference between implied and "
        "reported emissions = %.1f%% (n=%d state-years). "
        "NOTE: only 'Automotive Diesel Oil' is covered by the current "
        "petroleum_statistics fixture -- real data should include petrol, "
        "LPG etc. too, or this check will systematically under-count.",
        mean_pct, len(comparison),
    )

    fig, ax = plt.subplots(figsize=(6, 6))
    ax.scatter(comparison["ghg_kt_co2e"], comparison["implied_kt_co2e"])
    lims = [0, max(comparison["ghg_kt_co2e"].max(), comparison["implied_kt_co2e"].max()) * 1.05]
    ax.plot(lims, lims, linestyle="--", color="gray", label="perfect agreement")
    ax.set_xlabel("Reported emissions (kt CO2-e)")
    ax.set_ylabel("Implied emissions: fuel x factor (kt CO2-e)")
    ax.set_title("Emission factor validation (fixture data)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(VALIDATION_DIR / "emission_factor_check.png", dpi=150)
    plt.close(fig)

    return comparison


def validate_ghg_cross_source() -> pd.DataFrame:
    """Compare the CSV inventory table against the OData API extract."""
    csv_source = (
        load_state_territory_ghg()
        .query("sector == 'Transport'")
        .groupby(["state", "year"], as_index=False)["ghg_kt_co2e"]
        .sum()
    )
    api_source = load_nga_odata_api().query("sector == 'Transport'")

    comparison = csv_source.merge(api_source, on=["state", "year"], how="outer", indicator=True)
    only_csv = (comparison["_merge"] == "left_only").sum()
    only_api = (comparison["_merge"] == "right_only").sum()
    both = (comparison["_merge"] == "both").sum()

    comparison["abs_diff_kt"] = (
        comparison["ghg_kt_co2e"] - comparison["ghg_kt_co2e_odata"]
    ).abs()

    VALIDATION_DIR.mkdir(parents=True, exist_ok=True)
    comparison.to_csv(VALIDATION_DIR / "ghg_cross_source_check.csv", index=False)

    log.info(
        "GHG cross-source check: %d state-years in both sources, "
        "%d only in CSV table, %d only in OData API. "
        "Mean absolute difference where both exist: %.1f kt CO2-e.",
        both, only_csv, only_api,
        comparison.loc[comparison["_merge"] == "both", "abs_diff_kt"].mean(),
    )
    return comparison


def run() -> None:
    validate_emission_factors()
    validate_ghg_cross_source()
    log.info("Validation reports written to %s", VALIDATION_DIR)


if __name__ == "__main__":
    run()
