import importlib
import importlib.util
import pandas as pd
import pytest


def briefing_module():
    assert importlib.util.find_spec('src.briefing'), 'An exportable analyst task is required'
    return importlib.import_module('src.briefing')


def test_briefing_calculates_change_and_compares_per_capita():
    module = briefing_module()
    annual = pd.DataFrame([
        {'state': 'NSW', 'year': 2020, 'ghg_kt_co2e': 100, 'emissions_per_capita_kg': 10},
        {'state': 'NSW', 'year': 2021, 'ghg_kt_co2e': 120, 'emissions_per_capita_kg': 12},
        {'state': 'VIC', 'year': 2021, 'ghg_kt_co2e': 80, 'emissions_per_capita_kg': 20},
    ])
    result = module.build_briefing(annual, 'NSW', 2020, 2021)
    assert result['change_pct'] == 20
    assert result['per_capita_rank'] == 2
    assert result['end_fy'] == 'FY2021-22'
    with pytest.raises(ValueError): module.build_briefing(annual, 'ACT', 2020, 2021)
    with pytest.raises(ValueError): module.build_briefing(annual, 'NSW', 2021, 2020)


def test_export_contains_units_sources_and_run_identity():
    module = briefing_module()
    annual = pd.read_csv('data/processed/annual_master_with_population.csv')
    result = module.build_briefing(annual, 'NSW', 2010, 2023)
    text = module.render_briefing(result, {'run_id': 'test-run', 'sources': [
        {'source': 'inventory', 'url': 'https://example.org/inventory'}]})
    assert 'test-run' in text
    assert 'https://example.org/inventory' in text
    assert 'kt CO2-e' in text
    assert 'FY2023-24' in text


def test_dashboard_can_be_regenerated_from_pipeline_contract():
    from scripts import build_dashboard
    data = build_dashboard.build_data()
    html = build_dashboard.build_html(data)
    assert '/*__DASHBOARD_DATA__*/' not in html
    assert 'download-briefing' in html
    assert data['briefings']['NSW']['2010:2023']['end_fy'] == 'FY2023-24'
