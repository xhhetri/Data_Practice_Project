from __future__ import annotations

import logging
import re
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
BRONZE_DIR = REPO_ROOT / "data" / "bronze"
FIXTURES_DIR = REPO_ROOT / "fixtures"
PROCESSED_DIR = REPO_ROOT / "data" / "processed"

# The 8 official Australian state/territory codes. Anything outside this
# set after cleaning is a data quality problem, not a new category.
VALID_STATES = {"NSW", "VIC", "QLD", "SA", "WA", "TAS", "NT", "ACT"}

# Real government downloads land in whatever folder name the person who
# downloaded them used, not the machine-readable source_name keys used
# below. Add to this list when a new folder name shows up -- no other
# code needs to change.
BRONZE_FOLDER_ALIASES: dict[str, list[str]] = {
    "petroleum_statistics": [
        "petroleum_statistics",
        "Australian Petroleum statistics consumption cover",
    ],
    "state_territory_ghg": [
        "state_territory_ghg",
        "State & Territory Inventories 2024 - Emission Data Tables",
    ],
    "nga_factors_2025": [
        "nga_factors_2025",
        "Australian National Greenhouse Accounts Factors",
    ],
    "bitre_yearbook": ["bitre_yearbook", "bitre-yearbook-2025"],
    "vehicle_registrations": [
        "vehicle_registrations",
        "Registered motor vehicles by vehicle type",
    ],
    "quarterly_ghg_update": [
        "quarterly_ghg_update",
        "National Greenhouse Gas Inventory Quarterly Update",
    ],
    "abs_population": [
        "abs_population",
        "National, state and territory population",
    ],
}

def _parse_financial_year(fy: str) -> int:
    """'2020-21' -> 2020. Every FY-labelled source in this project uses
    the START calendar year as its 'year' value, for consistency."""
    return int(str(fy).split("-")[0])


def _fy_start_from_date(date: pd.Timestamp) -> int:
    """Calendar date -> Australian financial year start (Jul-Jun). E.g.
    Sep 2020 and Mar 2021 both -> 2020 (both fall in FY2020-21)."""
    return date.year if date.month >= 7 else date.year - 1

def build_annual_master() -> pd.DataFrame:
    """
    State x financial-year table. Every source below reports on an
    Australian financial year basis (or is aligned to one here) for
    consistency -- see _parse_financial_year() / _fy_start_from_date().
    A financial year is labelled by its start calendar year throughout
    (e.g. "2020" means FY2020-21).

    registered_vehicles now comes from a genuine annual state-level
    series (BITRE Yearbook, "Table 4.6b") -- see
    load_vehicle_registrations(). The broadcast-constant fallback below
    only triggers if that real file isn't available and the loader
    falls back to the old manufacture-year-snapshot CSV shape instead
    -- not the normal path, but handled rather than left to crash.
    """
    fuel = (
        load_petroleum_statistics()
        .groupby(["state", "fy_year"], as_index=False)["consumption_ml"]
        .sum()
        .rename(columns={"consumption_ml": "fuel_consumption_ml", "fy_year": "year"})
    )

    vkt = (
        load_bitre_yearbook()
        .groupby(["state", "year"], as_index=False)["vkt_million_km"]
        .sum()
        .rename(columns={"vkt_million_km": "vkt_road_million_km"})
    )

    target = (
        load_state_territory_ghg()
        .query("sector == 'Transport'")
        .groupby(["state", "year"], as_index=False)["ghg_kt_co2e"]
        .sum()
    )

    master = (
        fuel.merge(vkt, on=["state", "year"], how="inner")
        .merge(target, on=["state", "year"], how="inner")
    )

    veh_raw = load_vehicle_registrations()
    if "year" in veh_raw.columns:
        vehicles = (
            veh_raw.groupby(["state", "year"], as_index=False)["count"]
            .sum()
            .rename(columns={"count": "registered_vehicles"})
        )
        master = master.merge(vehicles, on=["state", "year"], how="inner")
    else:
        log.warning(
            "vehicle_registrations has no 'year' column -- this means "
            "it fell back to the old manufacture-year fleet snapshot CSV "
            "instead of the real annual BITRE series (Table 4.6b). This "
            "is NOT the normal path -- check why bitre_yearbook's real "
            "file wasn't found. Broadcasting each state's current fleet "
            "size across all years as a fallback; this feature will NOT "
            "vary within a state across years while this fallback is active."
        )
        current_fleet = (
            veh_raw.groupby("state", as_index=False)["count"]
            .sum()
            .rename(columns={"count": "registered_vehicles"})
        )
        master = master.merge(current_fleet, on="state", how="inner")

    log.info("Annual master table: %d rows (%d states x %d years, %s to %s)",
              len(master), master["state"].nunique(), master["year"].nunique(),
              master["year"].min(), master["year"].max())
    return master


def build_annual_master_with_population() -> pd.DataFrame:
    """
    Same as build_annual_master(), plus population and per-capita
    features. Population is aggregated to the same FY convention as
    every other source (see load_population()'s fy_year column).
    """
    base = build_annual_master()
    pop = (
        load_population()
        .groupby(["state", "fy_year"], as_index=False)["population"]
        .mean()  # average of the quarters within that financial year
        .rename(columns={"fy_year": "year"})
    )
    merged = base.merge(pop, on=["state", "year"], how="inner")
    merged["emissions_per_capita_kg"] = (
        merged["ghg_kt_co2e"] * 1_000_000 / merged["population"]
    )
    merged["vkt_per_capita_km"] = (
        merged["vkt_road_million_km"] * 1_000_000 / merged["population"]
    )
    merged["vehicles_per_capita"] = merged["registered_vehicles"] / merged["population"]
    log.info("Annual master (with population): %d rows (%s to %s)",
              len(merged), merged["year"].min(), merged["year"].max())
    return merged


def build_monthly_fuel_series() -> pd.DataFrame:
    """State x month petroleum consumption -- the time-series forecasting
    target (see model.py: forecast_fuel_consumption)."""
    df = load_petroleum_statistics()
    monthly = (
        df.groupby(["state", "date"], as_index=False)["consumption_ml"]
        .sum()
        .sort_values(["state", "date"])
    )
    return monthly


def run() -> None:
    """Build all processed tables and write them to data/processed/."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    annual = build_annual_master()
    annual.to_csv(PROCESSED_DIR / "annual_master.csv", index=False)

    annual_pop = build_annual_master_with_population()
    annual_pop.to_csv(PROCESSED_DIR / "annual_master_with_population.csv", index=False)

    monthly_fuel = build_monthly_fuel_series()
    monthly_fuel.to_csv(PROCESSED_DIR / "monthly_fuel_series.csv", index=False)

    log.info("Processed tables written to %s", PROCESSED_DIR)