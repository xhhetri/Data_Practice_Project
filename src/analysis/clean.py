"""
clean.py
--------
Shared Bronze-tier utilities (source resolution: real file > SAMPLE file
> fixtures/ fallback), plus a backward-compatible facade re-exporting the
Silver (silver.py) and Gold (gold.py) tiers -- so every existing caller
(eda.py, model.py, validate.py, tests/test_clean.py) can keep importing
`from src.analysis.clean import ...` unchanged.

Design history (see CHANGELOG.md): a layered Bronze/Silver/Gold
architecture was tried, its connector code was lost, and the team
rescoped to this single flat module in 2026-09-09. It has since been
rebuilt as three focused modules (bronze.py / silver.py / gold.py)
sharing the same tested primitives below, rather than reintroducing the
per-source connector classes that broke last time -- see the
"Bronze/Silver/Gold, rebuilt" CHANGELOG entry.

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


def _locate(name: str, exts: tuple[str, ...] = ("csv", "xlsx", "xls")) -> Path:
    """
    Find the best available file for a given source name. Checks every
    folder alias for this source, both files directly inside that folder
    and files inside any dated subfolder within it -- real downloads have
    been placed both ways in practice. Prefers a non-SAMPLE (real) file;
    among several real matches, uses the most recently modified.
    """
    real_matches: list[Path] = []
    sample_matches: list[Path] = []

    for alias in BRONZE_FOLDER_ALIASES.get(name, [name]):
        folder = BRONZE_DIR / alias
        if not folder.exists():
            continue
        direct = [c for ext in exts for c in folder.glob(f"*.{ext}")]
        nested = [
            c
            for sub in folder.iterdir()
            if sub.is_dir()
            for ext in exts
            for c in sub.glob(f"*.{ext}")
        ]
        for c in direct + nested:
            (sample_matches if "SAMPLE" in c.name else real_matches).append(c)

    if real_matches:
        chosen = max(real_matches, key=lambda p: p.stat().st_mtime)
        log.info("Using real data for '%s': %s", name, chosen)
        return chosen
    if sample_matches:
        chosen = max(sample_matches, key=lambda p: p.stat().st_mtime)
        log.info("Using sample data for '%s': %s", name, chosen)
        return chosen

    for ext in exts:
        fallback = FIXTURES_DIR / f"{name}.SAMPLE.{ext}"
        if fallback.exists():
            log.info("Falling back to fixture for '%s': %s", name, fallback)
            return fallback

    raise FileNotFoundError(f"No source file found for '{name}' (tried: {exts})")


def _read_tabular(path: Path, **kwargs) -> pd.DataFrame:
    """Read CSV or Excel transparently based on file extension."""
    if path.suffix.lower() in (".xlsx", ".xls"):
        return pd.read_excel(path, **kwargs)
    return pd.read_csv(path, **kwargs)


def _parse_financial_year(fy: str) -> int:
    """'2020-21' -> 2020. Every FY-labelled source in this project uses
    the START calendar year as its 'year' value, for consistency."""
    return int(str(fy).split("-")[0])


def _fy_start_from_date(date: pd.Timestamp) -> int:
    """Calendar date -> Australian financial year start (Jul-Jun). E.g.
    Sep 2020 and Mar 2021 both -> 2020 (both fall in FY2020-21)."""
    return date.year if date.month >= 7 else date.year - 1


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
# Backward-compatible re-exports.
#
# The per-source cleaning (Silver) and aggregation (Gold) logic that used
# to live here now lives in silver.py / gold.py -- both import the Bronze
# utilities defined above, so clean.py cannot import them back at module
# load time without a circular import (whichever of the two is imported
# FIRST would find the other only half-initialised). Resolved lazily
# instead, via PEP 562 module __getattr__: clean.py itself has no
# dependency on silver.py/gold.py until one of these names is actually
# accessed, by which point both modules load cleanly regardless of which
# module a caller imported first.
#
# Every existing caller (eda.py, model.py, validate.py,
# tests/test_clean.py) keeps working with
# `from src.analysis.clean import <name>` / `clean.<name>(...)` unchanged.
# ---------------------------------------------------------------------
_SILVER_EXPORTS = {
    "load_population",
    "load_bitre_yearbook",
    "load_petroleum_statistics",
    "load_quarterly_ghg_update",
    "load_state_territory_ghg",
    "load_vehicle_registrations",
    "load_nga_factors",
}
_GOLD_EXPORTS = {
    "build_annual_master",
    "build_annual_master_with_population",
    "build_monthly_fuel_series",
}


def __getattr__(name: str):
    if name in _SILVER_EXPORTS:
        from src.analysis import silver
        return getattr(silver, name)
    if name in _GOLD_EXPORTS:
        from src.analysis import gold
        return getattr(gold, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def run() -> None:
    """Runs the full pipeline -- Bronze (validate raw sources) -> Silver
    (clean + persist each source) -> Gold (join/aggregate to
    data/processed/*.csv). Kept as a single entry point since eda.py and
    model.py both call this (as `run_clean`) to build data/processed/ on
    demand if it doesn't exist yet."""
    from src.analysis import bronze, silver, gold  # local import: these
    # modules import Bronze utilities back from this one at their own
    # top level, so importing them here (not at module load time) avoids
    # a circular import.

    bronze.run()
    silver.run()
    gold.run()


if __name__ == "__main__":
    run()
