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
# Per-source loaders. Each returns a clean, typed DataFrame.
# ---------------------------------------------------------------------

def load_population() -> pd.DataFrame:
    """
    Real: ABS wide-format quarterly ERP export ('Data1' sheet) -- one
    column per state x sex combination, dates down the rows. Only the
    'Persons' (both-sex total) columns are kept.
    Fixture fallback: flat state,year,quarter,population CSV.
    """
    path = _locate("abs_population")
    is_real = path.suffix.lower() in (".xlsx", ".xls") and "Data1" in pd.ExcelFile(path).sheet_names

    if is_real:
        raw = pd.read_excel(path, sheet_name="Data1", header=None)
        header_row = raw.iloc[0]
        state_names = {
            "New South Wales": "NSW", "Victoria": "VIC", "Queensland": "QLD",
            "South Australia": "SA", "Western Australia": "WA",
            "Tasmania": "TAS", "Northern Territory": "NT",
            "Australian Capital Territory": "ACT",
        }
        records = []
        for col in raw.columns[1:]:
            label = str(header_row[col])
            if "Persons" not in label:
                continue
            state = next((code for name, code in state_names.items() if name in label), None)
            if state is None:
                continue  # the "Australia" national total column
            block = raw.iloc[10:, [0, col]].copy()
            block.columns = ["date", "population"]
            block["state"] = state
            records.append(block)
        df = pd.concat(records, ignore_index=True)
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"])
        df["year"] = df["date"].dt.year
        df["quarter"] = df["date"].dt.quarter
        df["fy_year"] = df["date"].apply(_fy_start_from_date)
        df = df[["state", "year", "quarter", "fy_year", "population"]]
    else:
        df = _read_tabular(path)
        df["fy_year"] = df["year"]  # fixture has no real dates; treat as already FY-aligned

    df = _standardise_state(df)
    df["population"] = pd.to_numeric(df["population"], errors="coerce")
    df = df.dropna(subset=["population"])
    return df


def load_bitre_yearbook() -> pd.DataFrame:
    """
    Real: BITRE Yearbook 'Table 4.3' -- total VKT by state/territory,
    wide format (states as columns, financial years as rows), in BILLION
    vehicle-km (converted to million here to match this project's unit).
    Fixture fallback: flat state,year,mode,vkt_million_km CSV.
    """
    path = _locate("bitre_yearbook")
    is_real = path.suffix.lower() in (".xlsx", ".xls") and "Table 4.3" in pd.ExcelFile(path).sheet_names

    if is_real:
        raw = pd.read_excel(path, sheet_name="Table 4.3", header=None)
        state_cols = raw.iloc[3]
        col_map = {c: state_cols[c] for c in raw.columns if state_cols[c] in VALID_STATES}
        records = []
        for col, state in col_map.items():
            block = raw.iloc[5:, [0, col]].copy()
            block.columns = ["fy", "vkt_billion_km"]
            block["state"] = state
            records.append(block)
        df = pd.concat(records, ignore_index=True)
        df = df.dropna(subset=["fy", "vkt_billion_km"])
        df["year"] = df["fy"].astype(str).str.split("-").str[0].astype(int)
        df["vkt_million_km"] = pd.to_numeric(df["vkt_billion_km"], errors="coerce") * 1000
        df = df[["state", "year", "vkt_million_km"]]
    else:
        df = _read_tabular(path)

    df = _standardise_state(df)
    df["vkt_million_km"] = pd.to_numeric(df["vkt_million_km"], errors="coerce")
    df = df.dropna(subset=["vkt_million_km"])
    return df


def load_petroleum_statistics() -> pd.DataFrame:
    """
    Real: Australian Petroleum Statistics 'Sales by state and territory'
    sheet -- wide format, one column per fuel product. Only the two
    road-relevant totals are kept (automotive gasoline, diesel oil);
    aviation turbine fuel and other non-road products are excluded.
    Note: ACT is genuinely absent from this source's state breakdown --
    not a parsing gap, confirmed against the raw file's own State column.
    Fixture fallback: flat state,year,month,product,consumption_ml CSV.
    """
    path = _locate("petroleum_statistics")
    is_real = (
        path.suffix.lower() in (".xlsx", ".xls")
        and "Sales by state and territory" in pd.ExcelFile(path).sheet_names
    )

    if is_real:
        raw = pd.read_excel(path, sheet_name="Sales by state and territory")
        raw = raw.rename(columns={"State": "state", "Month": "date"})
        gasoline = raw[["state", "date", "Automotive gasoline: total (ML)"]].rename(
            columns={"Automotive gasoline: total (ML)": "consumption_ml"}
        )
        gasoline["product"] = "Gasoline"
        diesel = raw[["state", "date", "Diesel oil: total"]].rename(
            columns={"Diesel oil: total": "consumption_ml"}
        )
        diesel["product"] = "Diesel oil"
        df = pd.concat([gasoline, diesel], ignore_index=True)
        df["date"] = pd.to_datetime(df["date"])
        df["year"] = df["date"].dt.year
        df["month"] = df["date"].dt.month
        df["fy_year"] = df["date"].apply(_fy_start_from_date)
    else:
        df = _read_tabular(path)
        df["date"] = pd.to_datetime(dict(year=df["year"], month=df["month"], day=1))
        df["fy_year"] = df["date"].apply(_fy_start_from_date)

    df = _standardise_state(df)
    df["consumption_ml"] = pd.to_numeric(df["consumption_ml"], errors="coerce")
    df = df.dropna(subset=["consumption_ml"])
    return df


def load_quarterly_ghg_update() -> pd.DataFrame:
    """
    Real: NGGI Quarterly Update 'Data Table 1A' -- national quarterly
    emissions by sector (Mt CO2-e, converted to kt here). National only,
    no state dimension -- loaded for reference/future nowcasting, not
    currently merged into any state-level table (see README).
    Fixture fallback: flat state,year,sector,ghg_kt_co2e CSV -- note the
    fixture has a fake state dimension the real data doesn't have; this
    is a known simplification of the fixture, not a real capability.
    """
    path = _locate("quarterly_ghg_update")
    is_real = path.suffix.lower() in (".xlsx", ".xls") and "Data Table 1A" in pd.ExcelFile(path).sheet_names

    if is_real:
        raw = pd.read_excel(path, sheet_name="Data Table 1A", header=None)
        quarters = raw.iloc[6:, 1]
        transport_mt = pd.to_numeric(raw.iloc[6:, 4], errors="coerce")
        df = pd.DataFrame({"date": pd.to_datetime(quarters, errors="coerce"),
                            "ghg_kt_co2e": transport_mt * 1000})
        df = df.dropna(subset=["date", "ghg_kt_co2e"])
        df["year"] = df["date"].dt.year
        df["sector"] = "Transport"
        df["state"] = "AUSTRALIA"  # explicit marker: national, not a real state code
    else:
        df = _read_tabular(path)
        df["ghg_kt_co2e"] = pd.to_numeric(df["ghg_kt_co2e"], errors="coerce")

    df = df.dropna(subset=["ghg_kt_co2e"])
    return df


def load_state_territory_ghg() -> pd.DataFrame:
    """
    Real: 'State & Territory Inventories 2024 - Emission Data Tables' --
    one sheet per state, IPCC sector rows, financial-year columns. Uses
    the '3.  Transport' row -- the WHOLE transport sector (road + rail +
    domestic aviation + shipping combined). This dataset does not break
    transport down further by mode at the state level, so this is the
    finest granularity genuinely available -- treat results as "state
    transport sector emissions", not "road transport emissions"
    specifically. Units: Gg CO2-e, numerically identical to kt CO2-e
    (1 Gg = 1 kt), so no conversion needed.
    Fixture fallback: flat state,year,sector,ghg_kt_co2e CSV.
    """
    path = _locate("state_territory_ghg")
    is_real = path.suffix.lower() in (".xlsx", ".xls") and "NSW" in pd.ExcelFile(path).sheet_names

    if is_real:
        sheet_to_state = {"NSW": "NSW", "Vic": "VIC", "Qld": "QLD", "SA": "SA",
                           "WA": "WA", "Tas": "TAS", "NT": "NT", "ACT": "ACT"}
        fy_pattern = re.compile(r"^\d{4}-\d{2}$")
        records = []
        for sheet, state in sheet_to_state.items():
            raw = pd.read_excel(path, sheet_name=sheet, header=None)
            row0 = raw[0].astype(str).str.strip()
            transport_row = raw[row0 == "3.  Transport"]
            if transport_row.empty:
                log.warning("'%s' sheet: '3.  Transport' row not found, skipping", sheet)
                continue
            year_header = raw.iloc[6]
            vals = transport_row.iloc[0]
            for col in raw.columns[1:]:
                fy = year_header[col]
                if not isinstance(fy, str) or not fy_pattern.match(fy.strip()):
                    continue
                emissions = pd.to_numeric(vals[col], errors="coerce")
                if pd.notna(emissions):
                    records.append({
                        "state": state,
                        "year": _parse_financial_year(fy),
                        "sector": "Transport",
                        "ghg_kt_co2e": emissions,
                    })
        df = pd.DataFrame(records)
    else:
        df = _read_tabular(path)

    df = _standardise_state(df)
    df["ghg_kt_co2e"] = pd.to_numeric(df["ghg_kt_co2e"], errors="coerce")
    df = df.dropna(subset=["ghg_kt_co2e"])
    return df


def load_vehicle_registrations() -> pd.DataFrame:
    """
    Real: current registered-fleet CSV, broken down by year of
    MANUFACTURE, not year of registration -- this is a single snapshot
    of today's fleet composition, not a historical annual time series.
    (Filename suffix 'yom' = year of manufacture, confirming this.)

    Returns state, vehicle_type, year_of_manufacture, count -- deliberately
    NOT renamed to a 'year' column, so it can't be silently misused as if
    it were a real per-year time series. See build_annual_master() for
    how this gets folded in (as a constant current-fleet-size per state,
    not a genuine year-varying feature).
    Fixture fallback: flat state,vehicle_type,year,count CSV (the fixture
    *is* shaped as a real annual time series -- a simplification the real
    data doesn't support).
    """
    path = _locate("vehicle_registrations")
    is_real = "year_of_manufacture" in _read_tabular(path, nrows=0).columns

    if is_real:
        df = _read_tabular(path)
        df = df.rename(columns={"state_abb": "state", "no_vehicles": "count"})
    else:
        df = _read_tabular(path)

    df = _standardise_state(df)
    df["count"] = pd.to_numeric(df["count"], errors="coerce")
    df = df.dropna(subset=["count"])
    return df


def load_nga_factors() -> pd.DataFrame:
    """
    Real: NGA Factors 2025 workbook, 'Table 9' (transport fuels by
    equipment type) -- multi-row header, 'Transport type' forward-filled
    down merged cells. Only 'Cars and light commercial vehicles' x
    Gasoline/Diesel oil are extracted -- the two fuels petroleum_statistics
    actually reports at state level. Factor = energy content (GJ/kL) x
    combined Scope 1 factor (kg CO2-e/GJ) / 1000 -- the two-step real
    calculation, not a single looked-up number.
    (Table 8, stationary energy factors, exists in the same workbook but
    isn't used -- not relevant to a transport emissions model.)
    Fixture fallback: flat fuel_type,factor_kg_co2e_per_l CSV.
    """
    path = _locate("nga_factors_2025")
    is_real = path.suffix.lower() in (".xlsx", ".xls") and "Table 9" in pd.ExcelFile(path).sheet_names

    if is_real:
        raw = pd.read_excel(path, sheet_name="Table 9", header=None, skiprows=3)
        raw.columns = ["transport_type", "fuel_type", "energy_content", "sc1_co2",
                       "sc1_ch4", "sc1_n2o", "sc1_combined", "sc3"]
        raw["transport_type"] = raw["transport_type"].ffill()
        target = raw[
            (raw["transport_type"] == "Cars and light commercial vehicles")
            & (raw["fuel_type"].isin(["Gasoline", "Diesel oil"]))
        ].copy()
        target["energy_content"] = pd.to_numeric(target["energy_content"], errors="coerce")
        target["sc1_combined"] = pd.to_numeric(target["sc1_combined"], errors="coerce")
        target["factor_kg_co2e_per_l"] = target["energy_content"] * target["sc1_combined"] / 1000
        df = target[["fuel_type", "factor_kg_co2e_per_l"]]
    else:
        df = _read_tabular(path)

    df["factor_kg_co2e_per_l"] = pd.to_numeric(df["factor_kg_co2e_per_l"], errors="coerce")
    return df.dropna(subset=["factor_kg_co2e_per_l"])


# ---------------------------------------------------------------------
# Analysis-ready master tables
# ---------------------------------------------------------------------

def build_annual_master() -> pd.DataFrame:
    """
    State x financial-year table. Every source below reports on an
    Australian financial year basis (or is aligned to one here) for
    consistency -- see _parse_financial_year() / _fy_start_from_date().
    A financial year is labelled by its start calendar year throughout
    (e.g. "2020" means FY2020-21).

    registered_vehicles is a special case: the real source is a current
    fleet snapshot by manufacture year, not an annual time series, so
    it's broadcast as a constant per state across every year rather than
    genuinely varying year to year -- see load_vehicle_registrations().
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
            "vehicle_registrations has no 'year' column (it's a "
            "manufacture-year fleet snapshot, not an annual time series) "
            "-- broadcasting each state's current total fleet size across "
            "all years instead. This feature does NOT vary within a "
            "state across years -- keep that in mind interpreting any "
            "feature-importance result for it."
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


if __name__ == "__main__":
    run()