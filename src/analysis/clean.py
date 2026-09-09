"""
clean.py
--------
Load and clean the project's source CSVs, and build the analysis-ready
tables used by eda.py and model.py.

Design choice (documented in CHANGELOG.md): this replaces the earlier
Bronze/Silver/Gold connector architecture with a single, flat load->clean
step. For a dataset this size, the layered pipeline added complexity
without adding value -- one clear, testable module is easier for a
4-person student team to maintain and reason about.

Source lookup order, per dataset (so real data drops in automatically,
no code changes needed):
  1. data/bronze/<name>/<most recent dated folder>/<name>*.csv  (real data)
  2. data/bronze/<name>/<most recent dated folder>/<name>.SAMPLE.csv
  3. fixtures/<name>.SAMPLE.csv                                  (fallback)
"""

from __future__ import annotations

import logging
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


def _locate(name: str, ext: str = "csv") -> Path:
    """Find the best available file for a given source name."""
    source_dir = BRONZE_DIR / name
    if source_dir.exists():
        dated_folders = sorted(
            (p for p in source_dir.iterdir() if p.is_dir()), reverse=True
        )
        for folder in dated_folders:
            candidates = sorted(folder.glob(f"*.{ext}"))
            non_sample = [c for c in candidates if "SAMPLE" not in c.name]
            if non_sample:
                log.info("Using real data for '%s': %s", name, non_sample[0])
                return non_sample[0]
            if candidates:
                log.info("Using sample data for '%s': %s", name, candidates[0])
                return candidates[0]

    fallback = FIXTURES_DIR / f"{name}.SAMPLE.{ext}"
    if fallback.exists():
        log.info("Falling back to fixture for '%s': %s", name, fallback)
        return fallback

    raise FileNotFoundError(f"No source file found for '{name}'")


def _standardise_state(df: pd.DataFrame, col: str = "state") -> pd.DataFrame:
    """Uppercase state codes and drop rows with unrecognised values."""
    df = df.copy()
    df[col] = df[col].astype(str).str.strip().str.upper()
    bad = ~df[col].isin(VALID_STATES)
    if bad.any():
        log.warning("Dropping %d rows with unrecognised state codes: %s",
                    bad.sum(), df.loc[bad, col].unique().tolist())
        df = df.loc[~bad]
    return df


# ---------------------------------------------------------------------
# Per-source loaders. Each returns a clean, typed DataFrame.
# ---------------------------------------------------------------------

def load_population() -> pd.DataFrame:
    df = pd.read_csv(_locate("abs_population"))
    df = _standardise_state(df)
    df["population"] = pd.to_numeric(df["population"], errors="coerce")
    df = df.dropna(subset=["population"])
    return df


def load_bitre_yearbook() -> pd.DataFrame:
    df = pd.read_csv(_locate("bitre_yearbook"))
    df = _standardise_state(df)
    df["vkt_million_km"] = pd.to_numeric(df["vkt_million_km"], errors="coerce")
    df = df.dropna(subset=["vkt_million_km"])
    return df


def load_petroleum_statistics() -> pd.DataFrame:
    df = pd.read_csv(_locate("petroleum_statistics"))
    df = _standardise_state(df)
    df["consumption_ml"] = pd.to_numeric(df["consumption_ml"], errors="coerce")
    df = df.dropna(subset=["consumption_ml"])
    df["date"] = pd.to_datetime(
        dict(year=df["year"], month=df["month"], day=1)
    )
    return df


def load_quarterly_ghg_update() -> pd.DataFrame:
    df = pd.read_csv(_locate("quarterly_ghg_update"))
    df = _standardise_state(df)
    df["ghg_kt_co2e"] = pd.to_numeric(df["ghg_kt_co2e"], errors="coerce")
    df = df.dropna(subset=["ghg_kt_co2e"])
    return df


def load_state_territory_ghg() -> pd.DataFrame:
    df = pd.read_csv(_locate("state_territory_ghg"))
    df = _standardise_state(df)
    df["ghg_kt_co2e"] = pd.to_numeric(df["ghg_kt_co2e"], errors="coerce")
    df = df.dropna(subset=["ghg_kt_co2e"])
    return df


def load_vehicle_registrations() -> pd.DataFrame:
    df = pd.read_csv(_locate("vehicle_registrations"))
    df = _standardise_state(df)
    df["count"] = pd.to_numeric(df["count"], errors="coerce")
    df = df.dropna(subset=["count"])
    return df


def load_nga_factors() -> pd.DataFrame:
    df = pd.read_csv(_locate("nga_factors_2025"))
    df["factor_kg_co2e_per_l"] = pd.to_numeric(
        df["factor_kg_co2e_per_l"], errors="coerce"
    )
    return df.dropna(subset=["factor_kg_co2e_per_l"])


# ---------------------------------------------------------------------
# Analysis-ready master tables
# ---------------------------------------------------------------------

def build_annual_master() -> pd.DataFrame:
    """
    State x year table, 2020-2025, from the four sources that all cover
    that full range: petroleum, BITRE VKT, vehicle registrations, and
    state/territory GHG inventory (the prediction target).

    Population is deliberately excluded here -- it's only available for
    2024-2025 in the current data, and including it would shrink this
    table from 48 rows to 16. See build_annual_master_with_population().
    """
    fuel = (
        load_petroleum_statistics()
        .groupby(["state", "year"], as_index=False)["consumption_ml"]
        .sum()
        .rename(columns={"consumption_ml": "fuel_consumption_ml"})
    )

    vkt = (
        load_bitre_yearbook()
        .groupby(["state", "year"], as_index=False)["vkt_million_km"]
        .sum()
        .rename(columns={"vkt_million_km": "vkt_road_million_km"})
    )

    vehicles = (
        load_vehicle_registrations()
        .groupby(["state", "year"], as_index=False)["count"]
        .sum()
        .rename(columns={"count": "registered_vehicles"})
    )

    target = (
        load_state_territory_ghg()
        .query("sector == 'Transport'")
        .groupby(["state", "year"], as_index=False)["ghg_kt_co2e"]
        .sum()
    )

    master = (
        fuel.merge(vkt, on=["state", "year"], how="inner")
        .merge(vehicles, on=["state", "year"], how="inner")
        .merge(target, on=["state", "year"], how="inner")
    )

    log.info("Annual master table: %d rows (%d states x %d years)",
              len(master), master["state"].nunique(), master["year"].nunique())
    return master


def build_annual_master_with_population() -> pd.DataFrame:
    """
    Same as build_annual_master(), plus population and per-capita features.
    Only spans years where population data exists (currently 2024-2025),
    so this table is much smaller (~16 rows). Use it for the Kaya-style
    per-capita analysis, not as the main regression training set --
    16 rows is not enough to fit and evaluate a model responsibly.
    """
    base = build_annual_master()
    pop = (
        load_population()
        .groupby(["state", "year"], as_index=False)["population"]
        .mean()  # average of quarterly estimates for the year
    )
    merged = base.merge(pop, on=["state", "year"], how="inner")
    merged["emissions_per_capita_kg"] = (
        merged["ghg_kt_co2e"] * 1_000_000 / merged["population"]
    )
    merged["vkt_per_capita_km"] = (
        merged["vkt_road_million_km"] * 1_000_000 / merged["population"]
    )
    merged["vehicles_per_capita"] = merged["registered_vehicles"] / merged["population"]
    log.info("Annual master (with population): %d rows -- small N, "
              "interpret with caution", len(merged))
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


if __name__ == "__main__":
    run()
