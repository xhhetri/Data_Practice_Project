from _future_ import annotations

import logging
import re
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(_name_)

REPO_ROOT = Path(_file_).resolve().parents[2]
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