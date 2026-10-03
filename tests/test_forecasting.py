import numpy as np
import pandas as pd
import pytest
from src.analysis import model


def seasonal_series(months=84):
    return pd.Series(np.tile(np.arange(100., 112.), 7)[:months],
                     index=pd.date_range('2019-01-01', periods=months, freq='MS'))


def test_seasonal_naive_repeats_observed_season():
    assert hasattr(model, 'predict_fuel'), 'A tested forecast contract is required'
    predicted = model.predict_fuel(seasonal_series(), 'seasonal_naive', 6)
    np.testing.assert_allclose(predicted, [100, 101, 102, 103, 104, 105])


def test_evaluation_keeps_holdout_out_of_selection_and_emits_future_dates():
    assert hasattr(model, 'evaluate_fuel_series'), 'Rolling evaluation is required'
    result = model.evaluate_fuel_series(seasonal_series(), min_train=36)
    assert result['method'] == 'seasonal_naive'
    assert result['mape_pct'] == 0
    assert result['holdout_baseline']['method'] == 'seasonal_naive'
    assert result['holdout_baseline']['mape_pct'] == 0
    assert result['series']['future'][0]['date'] == '2026-01-01'
    holdout_start = result['series']['actual'][0]['date']
    assert all(f['test_end'] < holdout_start for f in result['folds'])
    assert all(f['train_end'] < f['test_start'] for f in result['folds'])
    for row in result['series']['future']:
        assert 0 <= row['lower_95'] <= row['lower_80'] <= row['value']
        assert row['value'] <= row['upper_80'] <= row['upper_95']


@pytest.mark.parametrize('change', ['missing_month', 'negative', 'duplicate'])
def test_invalid_monthly_series_is_rejected(change):
    assert hasattr(model, 'predict_fuel')
    series = seasonal_series()
    if change == 'missing_month': series = series.drop(series.index[5])
    if change == 'negative': series.iloc[3] = -1
    if change == 'duplicate': series.index = list(series.index[:-1]) + [series.index[-2]]
    with pytest.raises(ValueError): model.predict_fuel(series, 'seasonal_naive', 6)
