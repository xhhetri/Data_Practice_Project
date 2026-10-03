"""Build the standalone analyst interface from the completed pipeline artifacts."""
import json
import sys
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.briefing import build_briefing, load_metadata, LIMITATIONS
from src.provenance import verify_outputs


def build_data():
    metadata = load_metadata()
    verify_outputs(metadata)
    annual = pd.read_csv(ROOT / 'data/processed/annual_master_with_population.csv')
    monthly = pd.read_csv(ROOT / 'data/processed/monthly_fuel_series.csv')
    metrics = json.loads((ROOT / 'reports/model_results/metrics.json').read_text(encoding='utf-8'))
    if metrics['_run']['run_id'] != metadata['run_id']:
        raise ValueError('Model and source run identifiers differ')
    states = sorted(annual.state.unique())
    years = sorted(int(y) for y in annual.year.unique())
    briefings = {s: {f'{a}:{b}': build_briefing(annual, s, a, b)
                    for a in years for b in years if a <= b} for s in states}
    validation = pd.read_csv(ROOT / 'reports/validation/emission_factor_check.csv')
    monitoring = json.loads((ROOT / 'reports/monitoring/drift_report.json').read_text(encoding='utf-8'))
    if monitoring['run_id'] != metadata['run_id'] or monitoring['quality']['status'] != 'passed':
        raise ValueError('Monitoring must pass for the same pipeline run')
    return {'metadata': metadata, 'states': states, 'years': years,
            'annual': annual.round(4).to_dict('records'),
            'monthly': monthly.round(4).to_dict('records'), 'briefings': briefings,
            'forecasts': {s: metrics[f'fuel_forecast_{s}'] for s in states},
            'regression': metrics['emissions_regression'], 'limitations': LIMITATIONS,
            'quality': monitoring['quality'],
            'reconciliation': {'mean_absolute_gap_pct': float(validation.pct_diff.mean()),
                               'above_reported': int((validation.signed_pct_diff > 0).sum()),
                               'rows': len(validation)}}


def build_html(data):
    template = (ROOT / 'dashboard/template.html').read_text(encoding='utf-8')
    placeholder = '/*__DASHBOARD_DATA__*/'
    if template.count(placeholder) != 1:
        raise ValueError('Dashboard template must have exactly one data placeholder')
    payload = json.dumps(data, allow_nan=False).replace('</', '<\\/')
    return template.replace(placeholder, f'const DATA = {payload};')


def run():
    data = build_data()
    (ROOT / 'dashboard/index.html').write_text(build_html(data), encoding='utf-8')
    print(f'Dashboard built for run {data["metadata"]["run_id"]}; {len(data["states"])} jurisdictions')


if __name__ == '__main__':
    run()
