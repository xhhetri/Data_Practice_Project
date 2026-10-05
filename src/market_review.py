"""Validated daily/weekly market evidence alongside monthly sales forecasts."""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd

from src.analysis.model import evaluate_fuel_series
from src.provenance import sha256

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data/market/raw'
OUTPUT = ROOT / 'reports/market_review'
MANIFEST = ROOT / 'data/market/source_manifest.json'
CITY = {'NSW': 'Sydney', 'VIC': 'Melbourne', 'QLD': 'Brisbane', 'SA': 'Adelaide',
        'WA': 'Perth', 'NT': 'Darwin', 'TAS': 'Hobart'}
SOURCES = {
    'prices': {'name': 'AIP terminal gate prices', 'file': 'aip-tgp.xlsx', 'cadence': 'Weekdays',
               'url': 'https://aip.com.au/resources/historical-ulp-and-diesel-tgp-data/',
               'download_url': 'https://aip.com.au/wp-content/uploads/2026/09/AIP_TGP_Data_02-Oct-2026.xlsx',
               'scope': 'Major city terminals and published national average', 'unit': 'cents/L, including GST',
               'boundary': 'Wholesale terminal benchmark; excludes delivery and retail-specific costs.'},
    'stocks': {'name': 'DCCEEW weekly MSO stocks', 'file': 'mso-weekly.xlsx', 'cadence': 'Weekly (temporary publication)',
               'url': 'https://www.dcceew.gov.au/energy/security/australias-fuel-security/minimum-stockholding-obligation/statistics',
               'download_url': 'https://www.dcceew.gov.au/sites/default/files/documents/mso-weekly-snapshot-timeseries.xlsx',
               'scope': 'National', 'unit': 'ML and days equivalent',
               'boundary': 'National reported holdings under MSO; days equivalent are not a countdown to shortage.'},
    'sales': {'name': 'Australian Petroleum Statistics', 'file': 'aps-july-2026.xlsx', 'cadence': 'Monthly',
              'url': 'https://www.energy.gov.au/publications/australian-petroleum-statistics-2026',
              'download_url': 'https://www.energy.gov.au/sites/default/files/2026-09/australian-petroleum-statistics-data-extract-july-2026.xlsx',
              'scope': 'Seven reported jurisdictions; national supply context', 'unit': 'ML',
              'boundary': 'Petrol and total diesel sales separately; total diesel includes non-road uses. ACT has no separate series.'},
}


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def validate_observations(data, keys, values, *, allow_zero=False):
    if data.empty or data[keys].isna().any().any():
        raise ValueError('Empty evidence or missing observation keys')
    if data.duplicated(keys).any():
        raise ValueError('Duplicate observation keys')
    for column in values:
        numbers = pd.to_numeric(data[column], errors='coerce')
        valid = numbers.ge(0) if allow_zero else numbers.gt(0)
        if not np.isfinite(numbers).all() or not valid.all():
            raise ValueError(f'Invalid observations in {column}')
    if 'date' in data and data.date.max() > pd.Timestamp.now().normalize():
        raise ValueError('Future-dated source observations')
    return data


def parse_prices(path):
    frames = []
    for fuel, sheet in [('Petrol', 'Petrol TGP'), ('Diesel', 'Diesel TGP')]:
        frame = pd.read_excel(path, sheet_name=sheet)
        frame = frame.rename(columns={frame.columns[0]: 'date', 'National\nAverage': 'National'})
        locations = [*CITY.values(), 'National']
        if not set(locations).issubset(frame.columns):
            raise ValueError('Price source is missing required terminals')
        frame['date'] = pd.to_datetime(frame.date, errors='coerce')
        frame = frame.dropna(subset=['date'])
        frame = frame.melt(id_vars='date', value_vars=locations, var_name='location', value_name='value')
        frame['fuel'] = fuel
        frames.append(frame)
    result = pd.concat(frames, ignore_index=True)
    validate_observations(result, ['date', 'fuel', 'location'], ['value'])
    if result.date.nunique() < 12 or (result.date.max() - result.date.min()).days < 14:
        raise ValueError('Price history needs at least twelve dates spanning two weeks')
    if not result.groupby('date').size().eq(16).all():
        raise ValueError('Price coverage must match across both fuels and every terminal')
    return result.sort_values(['fuel', 'location', 'date']).reset_index(drop=True)


def parse_stocks(path):
    frames = []
    for fuel, sheet in [('Petrol', 'Gasoline'), ('Diesel', 'Diesel'), ('Jet fuel', 'Kerosene')]:
        raw = pd.read_excel(path, sheet_name=sheet)
        raw.columns = [str(c).strip() for c in raw.columns]
        dates = pd.to_datetime(raw['Obligation Date'], errors='coerce')
        raw = raw.loc[dates.notna()].copy()
        raw['date'] = dates.loc[dates.notna()]
        columns = {c: 'held_ml' if c.startswith('Stock held under MSO (ML)') else
                   'days_equivalent' if c.startswith('Stock held under MSO (Days') else
                   'baseline_required_ml' if c == 'Stocks required under MSO (ML)' else
                   'reduced_required_ml' if c.startswith('Stocks required under MSO after') else c for c in raw.columns}
        raw = raw.rename(columns=columns)
        base = pd.to_numeric(raw.baseline_required_ml, errors='coerce')
        reduced = pd.to_numeric(raw.get('reduced_required_ml', pd.Series(np.nan, index=raw.index)), errors='coerce')
        frame = raw[['date', 'held_ml', 'days_equivalent']].copy()
        frame['baseline_required_ml'] = base
        frame['required_ml'] = reduced.fillna(base)
        frame['fuel'], frame['scope'] = fuel, 'National'
        frames.append(frame)
    result = pd.concat(frames, ignore_index=True)
    validate_observations(result, ['date', 'fuel'], ['held_ml', 'required_ml', 'baseline_required_ml', 'days_equivalent'])
    if result.date.nunique() < 3:
        raise ValueError('Stock history requires at least three reported weeks')
    if not result.groupby('date').size().eq(3).all():
        raise ValueError('Stock coverage must match across the three fuel series')
    result['headroom_pct'] = (result.held_ml / result.required_ml - 1) * 100
    return result.sort_values(['fuel', 'date']).reset_index(drop=True)


def parse_petroleum(path):
    book = pd.ExcelFile(path)
    raw = pd.read_excel(book, sheet_name='Sales by state and territory')
    if set(raw.State.dropna().unique()) != set(CITY):
        raise ValueError('Unexpected petroleum sales jurisdiction coverage')
    sales = []
    for fuel, column in [('Petrol', 'Automotive gasoline: total (ML)'), ('Diesel', 'Diesel oil: total')]:
        frame = raw[['State', 'Month', column]].rename(columns={'State': 'state', 'Month': 'date', column: 'value'})
        frame['date'] = pd.to_datetime(frame.date)
        frame['fuel'] = fuel
        sales.append(frame)
    sales = pd.concat(sales, ignore_index=True)
    validate_observations(sales, ['state', 'date', 'fuel'], ['value'])
    expected_dates = pd.date_range(sales.date.min(), sales.date.max(), freq='MS')
    if len(expected_dates) < 84:
        raise ValueError('Sales history is too short for the chronological modelling protocol')
    for _, group in sales.groupby(['state', 'fuel']):
        if not group.sort_values('date').date.reset_index(drop=True).equals(pd.Series(expected_dates)):
            raise ValueError('Incomplete state/product monthly sales history')
    context = []
    for sheet, metric, suffix in [('Imports volume', 'imports_ml', 'ML'), ('Refinery production', 'refinery_ml', 'ML'),
                                  ('Stock volume by product', 'stocks_ml', 'ML'), ('Consumption cover', 'cover_days', 'days')]:
        raw = pd.read_excel(book, sheet_name=sheet)
        for fuel, product in [('Petrol', 'Automotive gasoline'), ('Diesel', 'Diesel oil')]:
            column = f'{product} ({suffix})'
            frame = raw[['Month', column]].rename(columns={'Month': 'date', column: 'value'})
            frame['date'] = pd.to_datetime(frame.date)
            frame['fuel'], frame['metric'], frame['scope'] = fuel, metric, 'National'
            context.append(frame)
    context = pd.concat(context, ignore_index=True)
    validate_observations(context, ['date', 'fuel', 'metric'], ['value'], allow_zero=True)
    return sales.sort_values(['state', 'fuel', 'date']), context.sort_values(['metric', 'fuel', 'date'])


def download_bytes(url):
    request = Request(url, headers={'User-Agent': 'FuelScope academic review/1.0'})
    with urlopen(request, timeout=30) as response:
        content = response.read(20 * 1024 * 1024 + 1)
    if len(content) > 20 * 1024 * 1024:
        raise ValueError('Source exceeds the 20 MB download limit')
    return content


def update_cached_source(url, destination, parser, fetch=download_bytes):
    """Validate a temporary file before atomically replacing any previous cache."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        content = fetch(url)
        digest = hashlib.sha256(content).hexdigest()
        if destination.exists() and sha256(destination) == digest:
            return {'status': 'unchanged', 'changed': False, 'sha256': digest, 'checked_at': now_iso()}
        with tempfile.NamedTemporaryFile(dir=destination.parent, suffix='.xlsx', delete=False) as file:
            temporary = Path(file.name)
            file.write(content)
        candidate = parser(temporary)
        if destination.exists():
            previous = parser(destination)
            candidate_main = candidate[0] if isinstance(candidate, tuple) else candidate
            previous_main = previous[0] if isinstance(previous, tuple) else previous
            if isinstance(candidate_main, pd.DataFrame) and isinstance(previous_main, pd.DataFrame):
                if candidate_main.date.max() < previous_main.date.max():
                    raise ValueError('Downloaded source is older than the retained evidence')
                if candidate_main.date.min() > previous_main.date.min():
                    raise ValueError('Downloaded source would remove retained historical coverage')
        os.replace(temporary, destination)
        return {'status': 'updated', 'changed': True, 'sha256': digest, 'retrieved_at': now_iso(), 'checked_at': now_iso()}
    except Exception as error:
        return {'status': 'failed', 'changed': False, 'checked_at': now_iso(),
                'message': f'{type(error).__name__}: {str(error)[:180]}'}
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def records(frame):
    copy = frame.copy()
    if 'date' in copy:
        copy['date'] = copy.date.dt.strftime('%Y-%m-%d')
    return json.loads(copy.to_json(orient='records', double_precision=4))


def source_manifest():
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8')) if MANIFEST.exists() else {}
    for key, details in SOURCES.items():
        path = RAW / details['file']
        if key not in manifest and path.exists():
            manifest[key] = {**details, 'status': 'downloaded', 'sha256': sha256(path),
                             'retrieved_at': datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
                             'message': 'Public source downloaded for this build; timestamp records file download completion.'}
    return manifest


def build_snapshot(force_models=False):
    OUTPUT.mkdir(parents=True, exist_ok=True)
    prices = parse_prices(RAW / SOURCES['prices']['file'])
    stocks = parse_stocks(RAW / SOURCES['stocks']['file'])
    sales, context = parse_petroleum(RAW / SOURCES['sales']['file'])
    manifest = source_manifest()
    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    model_identity = hashlib.sha256((sha256(RAW / SOURCES['sales']['file']) +
                                    sha256(ROOT / 'src/analysis/model.py') +
                                    hashlib.sha256(pd.util.hash_pandas_object(sales, index=False).values.tobytes()).hexdigest() +
                                    'horizon6-step3-train60').encode()).hexdigest()[:16]
    model_file = OUTPUT / 'sales_models.json'
    models = json.loads(model_file.read_text(encoding='utf-8')) if model_file.exists() else {}
    if force_models or models.get('model_id') != model_identity:
        forecasts = {}
        for (state, fuel), frame in sales.groupby(['state', 'fuel']):
            print(f'Fuel-specific rolling evaluation: {state} / {fuel}', flush=True)
            series = frame.set_index('date').value.sort_index()
            forecasts[f'{state}:{fuel}'] = {'state': state, 'fuel': fuel, 'unit': 'ML',
                                          **evaluate_fuel_series(series, horizon=6, min_train=60, step=3)}
        models = {'model_id': model_identity, 'built_at': now_iso(), 'forecasts': forecasts}
        model_file.write_text(json.dumps(models, allow_nan=False), encoding='utf-8')
    historical = json.loads((ROOT / 'reports/run_metadata.json').read_text(encoding='utf-8'))
    annual = pd.read_csv(ROOT / 'data/processed/annual_master_with_population.csv')
    for key, data in [('prices', prices), ('stocks', stocks), ('sales', sales)]:
        manifest[key]['observed_through'] = data.date.max().strftime('%Y-%m-%d')
        manifest[key]['rows'] = len(data)
        if manifest[key]['sha256'] != sha256(RAW / SOURCES[key]['file']):
            raise ValueError(f'{key} source changed without a validated refresh')
    evidence_id = hashlib.sha256(''.join(manifest[k]['sha256'] for k in sorted(manifest)).encode()).hexdigest()[:16]
    snapshot = {'evidence_id': evidence_id, 'built_at': now_iso(), 'model_id': model_identity,
                'historical_run_id': historical['run_id'], 'sources': manifest,
                'city_by_state': CITY, 'states': list(CITY), 'fuels': ['Petrol', 'Diesel'],
                'prices': records(prices[prices.date >= prices.date.max() - pd.Timedelta(days=400)]),
                'stocks': records(stocks), 'sales': records(sales), 'supply': records(context),
                'forecasts': models['forecasts'], 'annual': annual.to_dict('records'),
                'historical_sources': historical['sources'], 'annual_coverage': historical['coverage'],
                'limitations': ['Market prices are wholesale terminal benchmarks, not pump prices or delivered supplier quotes.',
                                'State sales and capital-city prices cover different geographies. MSO stocks are national.',
                                'Total diesel sales include non-road uses; recorded sales are not unconstrained demand.',
                                'MSO days equivalent, monthly consumption cover and IEA coverage have different definitions.',
                                'Statistical changes identify evidence to review; they do not establish shortages or policy effects.',
                                'Forecasts start after the observation cutoff. Approximate bands cannot guarantee future coverage.',
                                'Backtests use the current revised sales extract; historical publication vintages were not reconstructed.',
                                'This research prototype has no completed participant study; adoption and time savings remain unmeasured.']}
    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    processed = ROOT / 'data/market/processed'
    processed.mkdir(parents=True, exist_ok=True)
    for name, frame in [('prices', prices), ('stocks', stocks), ('sales', sales), ('supply', context)]:
        frame.to_csv(processed / f'{name}.csv', index=False)
    output = OUTPUT / 'snapshot.json'
    temporary = OUTPUT / 'snapshot.json.tmp'
    temporary.write_text(json.dumps(snapshot, allow_nan=False), encoding='utf-8')
    os.replace(temporary, output)
    write_evaluation(snapshot)
    return snapshot


def write_evaluation(snapshot):
    example = next(iter(snapshot['forecasts'].values()))
    series = example['series']
    month = lambda value: pd.Timestamp(value).strftime('%B %Y')
    sales_start = month(min(row['date'] for row in snapshot['sales']))
    sales_end = month(max(row['date'] for row in snapshot['sales']))
    lines = ['# FuelScope: computed market-model evidence', '',
             f'Evidence `{snapshot["evidence_id"]}`; model `{snapshot["model_id"]}`; historical run `{snapshot["historical_run_id"]}`.', '',
             f'Separate monthly petrol and total diesel SALES, in ML. The current extract covers {sales_start}–{sales_end} across {len(snapshot["states"])} jurisdictions.',
             f'Each series compares seasonal naive and additive Holt-Winters on {example["rolling_windows"]} earlier rolling origins (60 initial training months, six-month horizon, three-month steps).',
             f'Method selection precedes the final {example["test_months"]} observed months, {month(series["actual"][0]["date"])}–{month(series["actual"][-1]["date"])}. Refit outlook: {month(series["future"][0]["date"])}–{month(series["future"][-1]["date"])}.', '',
             '| State | Fuel | Selected | Earlier naive MAPE % | Earlier HW MAPE % | Final MAPE % | Final naive MAPE % | 95% band coverage % |',
             '|---|---|---|---:|---:|---:|---:|---:|']
    for key, result in snapshot['forecasts'].items():
        candidates = result['candidates']
        score = lambda name: f'{candidates[name]["mape_pct"]:.2f}' if candidates[name]['status'] == 'ok' else 'unavailable'
        lines.append(f'| {result["state"]} | {result["fuel"]} | {result["method"]} | {score("seasonal_naive")} | {score("holt_winters")} | {result["mape_pct"]:.2f} | {result["holdout_baseline"]["mape_pct"]:.2f} | {result["holdout_interval_coverage_pct"]["95"]:.2f} |')
    lines += ['', '## Interpretation and limitations', '',
              '- The current revised extract is used; original historical publication vintages are not reconstructed.',
              '- Rolling windows overlap. Historical absolute-error quantiles provide approximate bands, not calibrated future probabilities.',
              '- Six final holdout observations make interval coverage coarse. Future shocks may exceed historical errors.',
              '- Candidate selection does not guarantee a win on the final holdout; baseline wins are reported.',
              '- Daily prices and weekly national stocks currently provide review context, not added predictive features.',
              '- Review queue markers are transparent descriptive checks, not a learned shortage classifier.',
              '- Price-change review marker: absolute seven-calendar-day change of at least 5 c/L. Source-age markers: prices more than 4 days old; stocks more than 10 days old.',
              '- National stocks, city wholesale prices, monthly state sales and annual official inventories retain different boundaries.',
              '- Actual participant benefit, professional adoption and policy effects have not been measured.', '', '## Current source evidence', '']
    for source in snapshot['sources'].values():
        lines.append(f'- [{source["name"]}]({source["url"]}): observed through {source["observed_through"]}, {source["rows"]:,} parsed observations; status {source["status"]}; SHA256 `{source["sha256"]}`.')
    (OUTPUT / 'technical_results.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def run():
    snapshot = build_snapshot()
    print(f'Market evidence {snapshot["evidence_id"]}: {len(snapshot["forecasts"])} fuel/state forecasts', flush=True)
    return snapshot
