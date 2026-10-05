"""
gold.py
-------
The Gold tier: joins and aggregates Silver's per-source tables into the
business/analytics-ready tables the rest of the project (eda.py,
model.py, the dashboard, src/db.py) actually consumes. Written to
data/processed/*.csv -- from there, src/db.py loads them into the
queryable Gold warehouse (data/gold/warehouse.sqlite).
"""

from __future__ import annotations

import logging

import pandas as pd

from src.analysis.clean import PROCESSED_DIR
from src.analysis.silver import (
    load_bitre_yearbook,
    load_petroleum_statistics,
    load_population,
    load_state_territory_ghg,
    load_vehicle_registrations,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)


def _complete_product_sales():
    fuel = load_petroleum_statistics()
    products = fuel.groupby(['state', 'date'])['product'].agg(set)
    if fuel.duplicated(['state', 'date', 'product']).any() or not products.map(lambda p: p == {'Gasoline', 'Diesel oil'}).all():
        raise ValueError('Fuel sales require exactly one Gasoline and one Diesel oil record in every state-month')
    if not fuel.consumption_ml.gt(0).all():
        raise ValueError('Fuel sales must be positive')
    return fuel


def build_annual_master() -> pd.DataFrame:
    """
    State x financial-year table. Every source below reports on an
    Australian financial year basis (or is aligned to one here) for
    consistency -- see silver._fy_start_from_date() / _parse_financial_year().
    A financial year is labelled by its start calendar year throughout
    (e.g. "2020" means FY2020-21).

    registered_vehicles is historical BITRE calendar-year stock associated
    with the FY starting in that year, an approximate alignment, not a FY mean.
    """
    fuel_raw = _complete_product_sales()
    periods = fuel_raw.groupby(["state", "fy_year", "product"])["month"].nunique()
    complete = periods.groupby(level=[0, 1]).min()
    valid = complete[complete == 12].reset_index()[["state", "fy_year"]]
    fuel_raw = fuel_raw.merge(valid, on=["state", "fy_year"], validate="many_to_one")
    fuel = (
        fuel_raw
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
    if "year" not in veh_raw:
        raise ValueError("Annual analysis requires historical fleet stock, not a snapshot")
    vehicles = veh_raw.groupby(["state", "year"], as_index=False)["count"].sum()
    vehicles = vehicles.rename(columns={"count": "registered_vehicles"})
    master = master.merge(vehicles, on=["state", "year"], how="inner", validate="one_to_one")
    if master.empty or master.duplicated(["state", "year"]).any():
        raise ValueError("Empty or duplicate annual state-year table")

    log.info("Gold: annual_master -- %d rows (%d states x %d years, %s to %s)",
              len(master), master["state"].nunique(), master["year"].nunique(),
              master["year"].min(), master["year"].max())
    return master


def build_annual_master_with_population() -> pd.DataFrame:
    """
    Same as build_annual_master(), plus population and per-capita
    features. Population is aggregated to the same FY convention as
    every other source (see silver.load_population()'s fy_year column).
    """
    base = build_annual_master()
    population = load_population()
    required = base[['state', 'year']].rename(columns={'year': 'fy_year'})
    quarters = population.merge(required, on=['state', 'fy_year'], how='inner', validate='many_to_one')
    counts = quarters.groupby(['state', 'fy_year'])['quarter'].agg(lambda q: set(q) == {1, 2, 3, 4})
    if (quarters.duplicated(['state', 'fy_year', 'quarter']).any() or
            len(counts) != len(base) or not counts.all() or not quarters.population.gt(0).all()):
        raise ValueError('Every annual briefing row requires four unique positive population quarters')
    pop = (
        quarters
        .groupby(["state", "fy_year"], as_index=False)["population"]
        .mean()  # average of the quarters within that financial year
        .rename(columns={"fy_year": "year"})
    )
    merged = base.merge(pop, on=["state", "year"], how="left", validate='one_to_one')
    merged["emissions_per_capita_kg"] = (
        merged["ghg_kt_co2e"] * 1_000_000 / merged["population"]
    )
    merged["vkt_per_capita_km"] = (
        merged["vkt_road_million_km"] * 1_000_000 / merged["population"]
    )
    merged["vehicles_per_capita"] = merged["registered_vehicles"] / merged["population"]
    log.info("Gold: annual_master_with_population -- %d rows (%s to %s)",
              len(merged), merged["year"].min(), merged["year"].max())
    return merged


def build_monthly_fuel_series() -> pd.DataFrame:
    """State x month petrol plus total diesel SALES -- the time-series forecasting
    target (see model.py: forecast_fuel_consumption)."""
    df = _complete_product_sales()
    monthly = (
        df.groupby(["state", "date"], as_index=False)["consumption_ml"]
        .sum()
        .sort_values(["state", "date"])
    )
    return monthly


def run() -> None:
    """Builds all Gold tables and writes them to data/processed/."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    annual = build_annual_master()
    annual.to_csv(PROCESSED_DIR / "annual_master.csv", index=False)

    annual_pop = build_annual_master_with_population()
    annual_pop.to_csv(PROCESSED_DIR / "annual_master_with_population.csv", index=False)

    monthly_fuel = build_monthly_fuel_series()
    monthly_fuel.to_csv(PROCESSED_DIR / "monthly_fuel_series.csv", index=False)

    log.info("Gold tables written to %s", PROCESSED_DIR)


if __name__ == "__main__":
    run()
