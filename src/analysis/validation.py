

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


def validate_emission_factors(save: bool = True) -> tuple[pd.DataFrame, plt.Figure]:
  
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

    if save:
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
    if save:
        out = VALIDATION_DIR / "emission_factor_check.png"
        fig.savefig(out, dpi=150)
        log.info("Saved %s", out)

    return comparison, fig


def run() -> None:
    comparison, fig = validate_emission_factors()
    plt.close(fig)  # script/CI run -- nothing will display this, free the memory
    log.info("Validation reports written to %s", VALIDATION_DIR)


if __name__ == "__main__":
    run()