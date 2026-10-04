import importlib
import importlib.util
from pathlib import Path

import pandas as pd
import pytest

RAW = Path('data/market/raw')


def market():
    assert importlib.util.find_spec('src.market_review'), 'The market evidence module is required'
    return importlib.import_module('src.market_review')


def test_real_price_workbook_has_separate_fuels_locations_and_positive_values():
    data = market().parse_prices(RAW / 'aip-tgp.xlsx')
    assert set(data.fuel) == {'Petrol', 'Diesel'}
    assert {'Sydney', 'Darwin', 'National'} <= set(data.location)
    assert not data.duplicated(['date', 'fuel', 'location']).any()
    assert data.value.gt(0).all()
    assert data.date.min() == pd.Timestamp('2004-01-01')


def test_weekly_stocks_keep_actual_obligation_and_national_scope():
    data = market().parse_stocks(RAW / 'mso-weekly.xlsx')
    first = data[(data.fuel == 'Diesel') & (data.date == pd.Timestamp('2026-02-24'))].iloc[0]
    assert first.required_ml == 2742
    assert first.held_ml == 3101
    assert first.days_equivalent == 34
    assert first.scope == 'National'
    reduced = data[(data.fuel == 'Diesel') & (data.date == pd.Timestamp('2026-03-24'))].iloc[0]
    assert reduced.required_ml == 2197


def test_current_sales_are_fuel_specific_and_all_state_months_are_complete():
    data, context = market().parse_petroleum(RAW / 'aps-july-2026.xlsx')
    assert set(data.fuel) == {'Petrol', 'Diesel'}
    assert len(data) == 7 * 193 * 2
    assert data.date.max() == pd.Timestamp('2026-07-01')
    assert set(context.metric) == {'imports_ml', 'refinery_ml', 'stocks_ml', 'cover_days'}
    assert set(context.scope) == {'National'}


def test_duplicate_negative_or_nonfinite_evidence_is_rejected():
    validate = market().validate_observations
    data = pd.DataFrame({'date': pd.to_datetime(['2026-01-01', '2026-01-01']), 'fuel': ['Diesel'] * 2, 'value': [2., 3.]})
    with pytest.raises(ValueError, match='Duplicate'):
        validate(data, ['date', 'fuel'], ['value'])
    for value in [-1, float('inf'), float('nan')]:
        data = pd.DataFrame({'date': [pd.Timestamp('2026-01-01')], 'value': [value]})
        with pytest.raises(ValueError):
            validate(data, ['date'], ['value'])


def test_failed_download_does_not_replace_last_valid_cache(tmp_path):
    module = market()
    cache = tmp_path / 'cached.xlsx'
    cache.write_bytes(b'previous valid evidence')
    def invalid_fetch(url):
        return b'invalid new workbook'
    def parser(path):
        raise ValueError('Unrecognised schema')
    result = module.update_cached_source('https://example.org/source.xlsx', cache, parser, invalid_fetch)
    assert result['status'] == 'failed'
    assert cache.read_bytes() == b'previous valid evidence'


def test_unchanged_refresh_reports_no_new_evidence(tmp_path):
    module = market()
    cache = tmp_path / 'cached.xlsx'
    cache.write_bytes(b'same evidence')
    result = module.update_cached_source('https://example.org/source.xlsx', cache, lambda p: None, lambda u: b'same evidence')
    assert result['status'] == 'unchanged'
    assert not result['changed']


def test_older_source_cannot_replace_more_recent_cached_observations(tmp_path):
    module = market()
    cache = tmp_path / 'cached.xlsx'
    cache.write_bytes(b'recent')
    def parser(path):
        return pd.DataFrame({'date': [pd.Timestamp('2026-10-02' if path.read_bytes() == b'recent' else '2026-09-01')]})
    result = module.update_cached_source('https://example.org/source.xlsx', cache, parser, lambda url: b'older')
    assert result['status'] == 'failed'
    assert cache.read_bytes() == b'recent'


def test_short_horizon_uncertainty_caveat_matches_actual_test_period():
    from src.analysis.model import evaluate_fuel_series
    dates = pd.date_range('2010-01-01', periods=120, freq='MS')
    series = pd.Series([100 + month % 12 for month in range(120)], index=dates)
    result = evaluate_fuel_series(series, horizon=3, min_train=60, step=3)
    assert result['test_months'] == 3
    assert '3-month holdout' in result['interval_caveat']
    assert all(f['test_end'] < result['series']['actual'][0]['date'] for f in result['folds'])


def test_actual_snapshot_forecasts_have_untouched_holdouts_and_upcoming_months():
    import json
    snapshot = json.loads(Path('reports/market_review/snapshot.json').read_text(encoding='utf-8'))
    assert len(snapshot['forecasts']) == 14
    for result in snapshot['forecasts'].values():
        assert result['unit'] == 'ML'
        assert result['test_months'] == 6
        assert len(result['series']['future']) == 6
        assert result['series']['future'][0]['date'] > result['series']['actual'][-1]['date']
        assert all(fold['test_end'] < result['series']['actual'][0]['date'] for fold in result['folds'])
        assert len(result['series']['actual']) == 6


@pytest.mark.parametrize('failure', ['single_date', 'mismatched_fuels'])
def test_price_feed_requires_matching_fuels_and_enough_history(monkeypatch, failure):
    module = market()
    dates = pd.date_range('2026-08-01', periods=20, freq='B')
    def read_excel(path, sheet_name):
        selected = dates[-1:] if failure == 'single_date' else dates[:-1] if sheet_name == 'Petrol TGP' else dates
        return pd.DataFrame({'Date': selected, **{location: [200.] * len(selected) for location in [*module.CITY.values(), 'National\nAverage']}})
    monkeypatch.setattr(module.pd, 'read_excel', read_excel)
    with pytest.raises(ValueError, match='history|coverage'):
        module.parse_prices('partial.xlsx')


def test_stock_feed_requires_prior_weeks(monkeypatch):
    module = market()
    def read_excel(path, sheet_name):
        return pd.DataFrame({'Obligation Date': [pd.Timestamp('2026-09-22')], 'Stocks required under MSO (ML)': [1000.],
                             'Stock held under MSO (ML)': [1500.], 'Stock held under MSO (Days equivalent) [2]': [30.]})
    monkeypatch.setattr(module.pd, 'read_excel', read_excel)
    with pytest.raises(ValueError, match='history'):
        module.parse_stocks('partial.xlsx')
