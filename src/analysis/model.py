"""Chronological evaluation and operational fuel-SALES forecasts.
Annual regression is associative; it cannot estimate causal policy effects.
"""
from __future__ import annotations
import json
import logging
import pickle
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from src.analysis.clean import PROCESSED_DIR, REPO_ROOT, run as run_clean
from src.analysis.eda import FEATURE_COLS, TARGET_COL

log = logging.getLogger(__name__)
RESULTS_DIR = REPO_ROOT / 'reports' / 'model_results'
METHODS = ('seasonal_naive', 'holt_winters')


def _ensure_processed():
    if not (PROCESSED_DIR / 'annual_master.csv').exists():
        run_clean()


def _validated_series(series):
    series = series.sort_index().astype(float)
    if len(series) < 24:
        raise ValueError('Need at least 24 unique, consecutive month-start observations')
    expected = pd.date_range(series.index.min(), periods=len(series), freq='MS')
    if not series.index.equals(expected):
        raise ValueError('Need at least 24 unique, consecutive month-start observations')
    if not np.isfinite(series.values).all() or (series <= 0).any():
        raise ValueError('Fuel sales must be finite and positive')
    return series.asfreq('MS')


def predict_fuel(series: pd.Series, method: str, horizon: int) -> np.ndarray:
    series = _validated_series(series)
    if not 1 <= horizon <= 24:
        raise ValueError('Forecast horizon must be 1 to 24 months')
    if method == 'seasonal_naive':
        return np.resize(series.iloc[-12:].to_numpy(), horizon)
    if method == 'holt_winters':
        fitted = ExponentialSmoothing(series, trend='add', seasonal='add',
                                      seasonal_periods=12).fit(use_brute=False)
        if not fitted.mle_retvals.get('success', True):
            raise ValueError('Holt-Winters optimizer did not converge')
        values = np.asarray(fitted.forecast(horizon))
        if not np.isfinite(values).all() or (values <= 0).any():
            raise ValueError('Forecast contains invalid fuel sales')
        return values
    raise ValueError(f'Unknown forecast method: {method}')


def _errors(actual, predicted):
    actual, predicted = np.asarray(actual), np.asarray(predicted)
    return {'mae_ml': round(float(np.mean(abs(actual - predicted))), 4),
            'mape_pct': round(float(np.mean(abs(actual - predicted) / actual) * 100), 4)}


def _records(index, values):
    return [{'date': date.strftime('%Y-%m-%d'), 'value': round(float(value), 4)}
            for date, value in zip(index, values)]


def evaluate_fuel_series(series: pd.Series, horizon: int = 6,
                         min_train: int = 60, step: int = 6) -> dict:
    """Select on earlier rolling origins, test on untouched final months.
    Bands are empirical horizon-specific errors, not guaranteed probabilities.
    """
    series = _validated_series(series)
    if not 1 <= horizon <= 24 or min_train < 24 or step < 1:
        raise ValueError('Invalid evaluation configuration')
    cutoff = len(series) - horizon
    origins = list(range(min_train, cutoff - horizon + 1, step))
    if len(origins) < 3:
        raise ValueError('Need at least three earlier rolling evaluation windows')
    folds = [{'train_end': series.index[o - 1].strftime('%Y-%m-%d'),
              'test_start': series.index[o].strftime('%Y-%m-%d'),
              'test_end': series.index[o + horizon - 1].strftime('%Y-%m-%d')}
             for o in origins]
    candidates, residuals = {}, {}
    for method in METHODS:
        actuals, forecasts, errors = [], [], []
        try:
            for origin in origins:
                actual = series.iloc[origin:origin + horizon].values
                predicted = predict_fuel(series.iloc[:origin], method, horizon)
                actuals.extend(actual)
                forecasts.extend(predicted)
                errors.append(actual - predicted)
            residuals[method] = np.array(errors)
            candidates[method] = {'status': 'ok', **_errors(actuals, forecasts)}
        except (ValueError, RuntimeError, FloatingPointError) as exc:
            candidates[method] = {'status': 'unavailable', 'reason': str(exc)}
    method = min(residuals, key=lambda m: (round(candidates[m]['mape_pct'], 2), METHODS.index(m)))
    train, actual = series.iloc[:cutoff], series.iloc[cutoff:]
    try:
        heldout = predict_fuel(train, method, horizon)
        future = predict_fuel(series, method, horizon)
    except (ValueError, RuntimeError, FloatingPointError) as exc:
        candidates[method]['operational_failure'] = str(exc)
        method = 'seasonal_naive'
        heldout = predict_fuel(train, method, horizon)
        future = predict_fuel(series, method, horizon)
    future_dates = pd.date_range(series.index[-1] + pd.offsets.MonthBegin(1), periods=horizon, freq='MS')
    future_rows = _records(future_dates, future)
    coverage = {}
    for level in (80, 95):
        width = np.quantile(abs(residuals[method]), level / 100, axis=0, method='higher')
        coverage[str(level)] = round(float(np.mean(abs(actual.values - heldout) <= width) * 100), 2)
        for row, band in zip(future_rows, width):
            row[f'lower_{level}'] = round(max(0., row['value'] - float(band)), 4)
            row[f'upper_{level}'] = round(row['value'] + float(band), 4)
    return {'method': method, 'test_months': horizon, **_errors(actual, heldout),
            'holdout_baseline': {'method': 'seasonal_naive',
                                 **_errors(actual, predict_fuel(train, 'seasonal_naive', horizon))},
            'selection_metric': 'Earlier rolling-origin MAPE; simpler method wins near ties',
            'candidates': candidates, 'folds': folds, 'rolling_windows': len(origins),
            'interval_method': 'Empirical absolute error quantiles by horizon from earlier rolling windows',
            'holdout_interval_coverage_pct': coverage,
            'interval_caveat': 'Approximate bands from a small, changing historical sample. '
                               'Six-month holdout coverage is coarse; future shocks may fall outside bands.',
            'series': {'train': _records(train.index, train), 'actual': _records(actual.index, actual),
                       'forecast': _records(actual.index, heldout), 'future': future_rows}}


def forecast_fuel_consumption(state: str = 'NSW', test_months: int = 6) -> dict:
    _ensure_processed()
    df = pd.read_csv(PROCESSED_DIR / 'monthly_fuel_series.csv', parse_dates=['date'])
    series = df[df.state == state].set_index('date')['consumption_ml']
    result = {'state': state, **evaluate_fuel_series(series, horizon=test_months)}
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(10, 5))
    for key, style in [('actual', '-'), ('forecast', '--'), ('future', '--')]:
        rows = result['series'][key]
        ax.plot(pd.to_datetime([r['date'] for r in rows]), [r['value'] for r in rows], style, label=key)
    rows = result['series']['future']
    ax.fill_between(pd.to_datetime([r['date'] for r in rows]),
                    [r['lower_95'] for r in rows], [r['upper_95'] for r in rows], alpha=.15)
    ax.set(title=f'{state}: fuel sales ({result["method"]})', ylabel='Petrol + diesel sales (ML)')
    ax.legend()
    figure_dir = REPO_ROOT / 'reports' / 'figures'
    figure_dir.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(figure_dir / f'06_forecast_{state}.png', dpi=150)
    plt.close(fig)
    return result


def train_emissions_regression() -> dict:
    _ensure_processed()
    df = pd.read_csv(PROCESSED_DIR / 'annual_master.csv').sort_values(['year', 'state'])
    years = sorted(df.year.unique())
    models = {'linear_regression': LinearRegression(),
              'random_forest': RandomForestRegressor(n_estimators=100, random_state=42)}
    predictions = {name: [] for name in models}
    predictions['previous_year'] = []
    folds = []
    for year in years[5:]:
        train, test = df[df.year < year], df[df.year == year]
        folds.append({'train_end': int(train.year.max()), 'test_year': int(year)})
        for name, prototype in models.items():
            fitted = clone(prototype).fit(train[FEATURE_COLS], train[TARGET_COL])
            preds = fitted.predict(test[FEATURE_COLS])
            predictions[name].extend({'state': s, 'actual': float(a), 'prediction': float(p)}
                                     for s, a, p in zip(test.state, test[TARGET_COL], preds))
        previous = df[df.year == year - 1].set_index('state')[TARGET_COL]
        predictions['previous_year'].extend(
            {'state': row.state, 'actual': float(getattr(row, TARGET_COL)),
             'prediction': float(previous[row.state])} for row in test.itertuples())
    if not folds:
        raise ValueError('Need at least six complete annual observation years')
    results = {}
    for name, records in predictions.items():
        observations = pd.DataFrame(records)
        actual, predicted = observations.actual, observations.prediction
        results[name] = {'cv_r2': round(float(r2_score(actual, predicted)), 4),
                         'cv_mae_kt_co2e': round(float(mean_absolute_error(actual, predicted)), 2),
                         'mape_pct': round(float(np.mean(abs(actual - predicted) / actual) * 100), 2),
                         'per_state': {state: {'mae_kt_co2e': round(float(np.mean(abs(g.actual-g.prediction))), 2),
                                              'mape_pct': round(float(np.mean(abs(g.actual-g.prediction)/g.actual)*100), 2)}
                                       for state, g in observations.groupby('state')}}
    chosen = min(models, key=lambda m: results[m]['cv_mae_kt_co2e'])
    fitted = clone(models[chosen]).fit(df[FEATURE_COLS], df[TARGET_COL])
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with (RESULTS_DIR / 'emissions_regression.pkl').open('wb') as output:
        pickle.dump({'model': fitted, 'features': FEATURE_COLS, 'method': chosen,
                     'ranges': {c: [float(df[c].min()), float(df[c].max())] for c in FEATURE_COLS}}, output)
    results.update({'evaluation': 'Expanding whole-year folds; contemporaneous inputs, associative only',
                    'folds': folds, 'n': len(df), 'selected_model': chosen,
                    '_caveat': 'High pooled R2 reflects state scale and accounting relationships. '
                               'This is not a causal intervention model or a forecast of future emissions.'})
    return results


def run() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    results = {'emissions_regression': train_emissions_regression()}
    monthly = pd.read_csv(PROCESSED_DIR / 'monthly_fuel_series.csv')
    for state in sorted(monthly.state.unique()):
        log.info('Rolling evaluation and future fuel sales forecast: %s', state)
        results[f'fuel_forecast_{state}'] = forecast_fuel_consumption(state)
    (RESULTS_DIR / 'metrics.json').write_text(json.dumps(results, indent=2, allow_nan=False), encoding='utf-8')


if __name__ == '__main__':
    run()
