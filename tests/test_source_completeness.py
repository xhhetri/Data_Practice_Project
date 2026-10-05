import pandas as pd
import pytest
from src.analysis import gold


@pytest.mark.parametrize('missing', ['quarter', 'state'])
def test_population_requires_all_four_quarters_for_every_briefing_row(monkeypatch, missing):
    base = pd.DataFrame([{'state': 'NSW', 'year': 2023, 'ghg_kt_co2e': 10,
                          'vkt_road_million_km': 100, 'registered_vehicles': 1000}])
    population = pd.DataFrame({'state': ['NSW']*4, 'fy_year': [2023]*4,
                               'quarter': [1, 2, 3, 4], 'population': [100]*4})
    population = population.iloc[:3] if missing == 'quarter' else population.iloc[:0]
    monkeypatch.setattr(gold, 'build_annual_master', lambda: base)
    monkeypatch.setattr(gold, 'load_population', lambda: population)
    with pytest.raises(ValueError, match='population'):
        gold.build_annual_master_with_population()


def test_sales_aggregation_requires_both_products_each_month(monkeypatch):
    raw = pd.DataFrame({'state': ['NSW']*12, 'date': pd.date_range('2023-07-01', periods=12, freq='MS'),
                        'fy_year': [2023]*12, 'month': list(range(1, 13)),
                        'product': ['Diesel oil']*12, 'consumption_ml': [10]*12})
    monkeypatch.setattr(gold, 'load_petroleum_statistics', lambda: raw)
    with pytest.raises(ValueError, match='Gasoline.*Diesel'):
        gold.build_monthly_fuel_series()
