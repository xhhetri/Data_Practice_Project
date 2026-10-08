"""Generate reviewable technical results and cited example briefings."""
import json
import sys
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.briefing import build_briefing, render_briefing, load_metadata
from src.provenance import verify_outputs


def run():
    metadata = load_metadata()
    verify_outputs(metadata)
    results = json.loads((ROOT / 'reports/model_results/metrics.json').read_text(encoding='utf-8'))
    annual = pd.read_csv(ROOT / 'data/processed/annual_master_with_population.csv')
    briefings = ROOT / 'reports/briefings'
    briefings.mkdir(parents=True, exist_ok=True)
    lines = ['# Technical evaluation results', '', f'Run `{metadata["run_id"]}`; built {metadata["built_at"]}.', '',
             'These are computed results, not participant-study findings. See docs/evaluation/pilot_protocol.md for the benefit evaluation.', '',
             '## Monthly sales forecasts', '',
             'Candidates are selected on earlier rolling windows. The final six months are held out of selection; all available observations are then used to refit the after-cutoff forecast. Percent errors are MAPE; lower is better.', '',
             '| State | Earlier seasonal-naive MAPE % | Earlier Holt-Winters MAPE % | Selected | Final holdout MAPE % | Same-holdout naive MAPE % | Holdout 95% band coverage % |',
             '|---|---:|---:|---|---:|---:|---:|']
    for state in sorted(annual.state.unique()):
        forecast = results[f'fuel_forecast_{state}']
        hw = forecast['candidates']['holt_winters']
        hw_score = f'{hw["mape_pct"]:.2f}' if hw['status'] == 'ok' else f'Unavailable: {hw["reason"]}'
        lines.append(f'| {state} | {forecast["candidates"]["seasonal_naive"]["mape_pct"]:.2f} | {hw_score} | {forecast["method"]} | {forecast["mape_pct"]:.2f} | {forecast["holdout_baseline"]["mape_pct"]:.2f} | {forecast["holdout_interval_coverage_pct"]["95"]:.2f} |')
        summary = build_briefing(annual, state, int(annual.year.min()), int(annual.year.max()))
        (briefings / f'{state}_briefing.md').write_text(render_briefing(summary, metadata, forecast), encoding='utf-8')
    forecast = results[f'fuel_forecast_{state}']
    lines.extend(['', f'{forecast["rolling_windows"]} earlier windows per state. Final holdout: {forecast["series"]["actual"][0]["date"]} to {forecast["series"]["actual"][-1]["date"]}.',
                  f'After-cutoff outlook: {forecast["series"]["future"][0]["date"]} to {forecast["series"]["future"][-1]["date"]}.',
                  forecast['interval_caveat'], '',
                  'The 80/95% labels describe empirical error quantiles, not guaranteed future coverage. Six held-out observations cannot establish calibrated uncertainty. Candidate selection has not used the final holdout error. The same-holdout baseline is reported after selection, so selected Holt-Winters can underperform it on this test.', '',
                  '## Annual association benchmark', '',
                  '| Method | Chronological pooled R² | MAE kt CO2-e | MAPE % |', '|---|---:|---:|---:|'])
    regression = results['emissions_regression']
    for name in ['previous_year', 'linear_regression', 'random_forest']:
        row = regression[name]
        lines.append(f'| {name} | {row["cv_r2"]:.4f} | {row["cv_mae_kt_co2e"]:.2f} | {row["mape_pct"]:.2f} |')
    lines.extend(['', regression['evaluation'], regression['_caveat'], '',
                  'The previous-year benchmark uses only earlier emissions, while regression receives actual same-year activity. This is an association benchmark, not a like-for-like operational emissions forecast.', '',
                  '### Per-state annual MAPE (%)', '', '| State | Previous year | Linear regression | Random forest |', '|---|---:|---:|---:|'])
    for state in sorted(annual.state.unique()):
        scores = [f'{regression[name]["per_state"][state]["mape_pct"]:.2f}' for name in ['previous_year', 'linear_regression', 'random_forest']]
        lines.append('| ' + ' | '.join([state, *scores]) + ' |')
    diagnostic = pd.read_csv(ROOT / 'reports/validation/emission_factor_check.csv')
    lines.extend(['', '## Unresolved boundary diagnostic', '',
                  f'Mean absolute relative gap: {diagnostic.pct_diff.mean():.2f}%. Sales-based implied emissions exceed the official transport inventory in {(diagnostic.signed_pct_diff > 0).sum()} of {len(diagnostic)} state-years.',
                  'This is not a passed inventory validation. Total diesel sales include different uses, and the simple factors are not the state transport inventory methodology. Use official inventory values for the briefing.', '',
                  '## Reproduction', '', 'Run python run_pipeline.py, then python -m pytest tests/. Source and core-output hashes are in reports/run_metadata.json. The standalone and database-backed interfaces carry the same run identifier.'])
    destination = ROOT / 'reports/evaluation'
    destination.mkdir(parents=True, exist_ok=True)
    (destination / 'technical_results.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')


if __name__ == '__main__':
    run()
