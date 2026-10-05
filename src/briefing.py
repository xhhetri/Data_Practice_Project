"""Shared, deterministic analyst summaries and portable briefing exports."""
import json
from pathlib import Path
import pandas as pd
from src.analysis.clean import REPO_ROOT

LIMITATIONS = [
    'Official emissions cover the whole transport sector; petrol plus total diesel sales have a different boundary.',
    'ACT is excluded from the merged comparison because the selected sales source has no separate ACT series.',
    'Historical vehicle stock uses BITRE calendar-year labels associated with the financial year starting in that year; it is not a financial-year average.',
    'State comparisons indicate where to investigate; they do not establish which policy caused a change.',
    'Source release dates differ. Forecasts start after the latest observed sales month, which may precede today.',
]


def financial_year(year):
    return f'FY{int(year)}-{str(int(year) + 1)[-2:]}'


def build_briefing(annual: pd.DataFrame, state: str, start_year: int, end_year: int) -> dict:
    if start_year > end_year:
        raise ValueError('The start year must not follow the end year')
    selected = annual[(annual.state == state) & annual.year.between(start_year, end_year)].sort_values('year')
    if selected.empty or selected.year.iloc[0] != start_year or selected.year.iloc[-1] != end_year:
        raise ValueError('The selected state and financial-year endpoints are not available')
    if len(selected) != end_year - start_year + 1:
        raise ValueError('The selected annual period contains missing years')
    first, last = selected.iloc[0], selected.iloc[-1]
    peers = annual[annual.year == end_year].sort_values('emissions_per_capita_kg', ascending=False)
    rank = int((peers.emissions_per_capita_kg > last.emissions_per_capita_kg).sum() + 1)
    change = float((last.ghg_kt_co2e / first.ghg_kt_co2e - 1) * 100)
    per_capita_change = float((last.emissions_per_capita_kg / first.emissions_per_capita_kg - 1) * 100)
    return {'state': state, 'start_year': int(start_year), 'end_year': int(end_year),
            'start_fy': financial_year(start_year), 'end_fy': financial_year(end_year),
            'emissions_kt': round(float(last.ghg_kt_co2e), 2),
            'change_pct': round(change, 2), 'change_kt': round(float(last.ghg_kt_co2e-first.ghg_kt_co2e), 2),
            'per_capita_kg': round(float(last.emissions_per_capita_kg), 2),
            'per_capita_change_pct': round(per_capita_change, 2),
            'per_capita_rank': rank, 'peer_count': len(peers),
            'headline': f'{state} transport emissions {"rose" if change > 0 else "fell" if change < 0 else "were unchanged"} '
                        f'{abs(change):.1f}% between {financial_year(start_year)} and {financial_year(end_year)}.',
            'interpretation': f'Per-capita emissions changed {per_capita_change:+.1f}%. '
                              'Check both total and per-capita changes before deciding what to investigate.',
            'peers': peers[['state', 'ghg_kt_co2e', 'emissions_per_capita_kg']].round(2).to_dict('records')}


def load_metadata():
    path = REPO_ROOT / 'reports' / 'run_metadata.json'
    if not path.exists():
        raise FileNotFoundError('No completed pipeline run; run python run_pipeline.py first')
    return json.loads(path.read_text(encoding='utf-8'))


def render_briefing(report: dict, metadata: dict, forecast: dict | None = None) -> str:
    lines = [f'# {report["state"]} transport emissions briefing', '', report['headline'], '',
             f'Latest selected emissions: **{report["emissions_kt"]:,.2f} kt CO2-e** ({report["end_fy"]}).',
             f'Per capita: **{report["per_capita_kg"]:,.2f} kg CO2-e per person**; '
             f'rank {report["per_capita_rank"]} of {report["peer_count"]} jurisdictions (highest first).',
             '', report['interpretation'], '', '## Peer comparison', '',
             '| Jurisdiction | Total kt CO2-e | kg CO2-e/person |', '|---|---:|---:|']
    lines.extend(f'| {p["state"]} | {p["ghg_kt_co2e"]:,.2f} | {p["emissions_per_capita_kg"]:,.2f} |' for p in report['peers'])
    if forecast:
        lines.extend(['', '## Fuel-sales outlook', '',
                      f'Method: {forecast["method"]}; selected using {forecast["rolling_windows"]} earlier rolling windows.',
                      f'Untouched holdout MAPE: {forecast["mape_pct"]:.2f}%.',
                      f'Same-holdout seasonal-naive baseline MAPE: {forecast["holdout_baseline"]["mape_pct"]:.2f}%. '
                      'This score is reported after selection; it does not choose the operational method.',
                      f'Holdout interval coverage: 80% band {forecast["holdout_interval_coverage_pct"]["80"]}% and '
                      f'95% band {forecast["holdout_interval_coverage_pct"]["95"]}% across {forecast["test_months"]} months only.',
                      forecast['interval_caveat'], '', '| Month | Sales ML | Approximate 95% band ML |', '|---|---:|---:|'])
        lines.extend(f'| {r["date"]} | {r["value"]:,.2f} | {r["lower_95"]:,.2f} to {r["upper_95"]:,.2f} |'
                     for r in forecast['series']['future'])
    lines.extend(['', '## Interpretation limits', ''] + [f'- {line}' for line in LIMITATIONS])
    lines.extend(['', '## Sources and provenance', '', f'Pipeline run: `{metadata.get("run_id", "unknown")}`',
                  f'Built at: {metadata.get("built_at", "unknown")}',
                  f'Observation cutoffs: {json.dumps(metadata.get("coverage", {}))}', ''])
    for source in metadata.get('sources', []):
        lines.append(f'- [{source["source"]}]({source["url"]}); file SHA256 `{source.get("sha256", "unknown")}`')
    return '\n'.join(lines) + '\n'
