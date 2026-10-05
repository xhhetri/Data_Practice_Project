"""Analyst workflow: select a state and period, compare peers, export a cited briefing."""
import sys
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.briefing import build_briefing, financial_year, render_briefing, LIMITATIONS
from src.serving import load_snapshot

st.set_page_config(page_title='Australian transport briefing', layout='wide')


@st.cache_data(ttl=10)
def snapshot():
    return load_snapshot()


st.title('Australian transport briefing')
st.write('Prepare a source-backed state comparison for an analyst or policy briefing.')
try:
    annual, monthly, results, metadata = snapshot()
except Exception:
    st.error('The project data is unavailable. Build the project with python run_pipeline.py, then reload.')
    st.stop()

coverage = metadata['coverage']
st.caption(f"Official inventories: {financial_year(coverage['annual_start'])} to {financial_year(coverage['annual_end'])}. "
           f"Fuel sales observed through {coverage['sales_end'][:7]}. Run {metadata['run_id']}.")
st.info('Compare official transport inventories here. Petrol plus total diesel sales describe a different boundary; '
        'the outlook is a sales forecast. ACT is absent from this seven-jurisdiction comparison.')

with st.sidebar:
    st.header('Build a briefing')
    state = st.selectbox('Jurisdiction', sorted(annual.state.unique()), index=sorted(annual.state.unique()).index('NSW'), key='state')
    years = sorted(int(y) for y in annual.year.unique())
    start = st.selectbox('From financial year', years, format_func=financial_year, key='start_year')
    end_options = [y for y in years if y >= start]
    end = st.selectbox('To financial year', end_options, index=len(end_options)-1, format_func=financial_year, key='end_year')
    st.caption('Use the same endpoint when comparing peers. Per-capita rankings run from highest to lowest.')

briefing = build_briefing(annual, state, start, end)
st.session_state['briefing'] = briefing
forecast = results[f'fuel_forecast_{state}']
selected = annual[(annual.state == state) & annual.year.between(start, end)].sort_values('year').copy()
selected['financial_year'] = selected.year.map(financial_year)
selected['pipeline_run_id'] = metadata['run_id']
markdown = render_briefing(briefing, metadata, forecast)
with st.sidebar:
    st.download_button('Download cited briefing', markdown, f'{state}_transport_briefing.md', 'text/markdown', key='briefing_export')
    st.download_button('Download selected data', selected.to_csv(index=False), f'{state}_annual_data.csv', 'text/csv', key='data_export')

brief_tab, outlook_tab, methods_tab = st.tabs(['State briefing', 'Fuel-sales outlook', 'Methods and sources'])
with brief_tab:
    st.subheader(briefing['headline'])
    a, b, c = st.columns(3)
    a.metric(f"Transport inventory ({briefing['end_fy']})", f"{briefing['emissions_kt']:,.0f} kt CO2-e", f"{briefing['change_pct']:+.1f}% across selected period", delta_color='off')
    b.metric('Per person', f"{briefing['per_capita_kg']:,.0f} kg CO2-e", f"{briefing['per_capita_change_pct']:+.1f}% across selected period", delta_color='off')
    c.metric('Per-capita rank', f"{briefing['per_capita_rank']} of {briefing['peer_count']}")
    st.write(briefing['interpretation'])
    for column, label in [('ghg_kt_co2e', 'Official transport inventory (kt CO2-e)'),
                          ('emissions_per_capita_kg', 'Transport inventory per person (kg CO2-e)')]:
        figure = px.line(selected, x='financial_year', y=column, markers=True, labels={column: label, 'financial_year': 'Financial year'}, title=label)
        figure.update_yaxes(rangemode='tozero')
        st.plotly_chart(figure, width='stretch')
    st.subheader(f"Peers in {briefing['end_fy']}")
    peers = pd.DataFrame(briefing['peers'])
    st.plotly_chart(px.bar(peers, x='state', y='emissions_per_capita_kg',
                          labels={'state': 'Jurisdiction', 'emissions_per_capita_kg': 'kg CO2-e per person'}), width='stretch')
    st.dataframe(peers.rename(columns={'ghg_kt_co2e': 'Inventory (kt CO2-e)', 'emissions_per_capita_kg': 'kg CO2-e/person'}), hide_index=True)
    with st.expander('Annual observations and export fields'):
        st.dataframe(selected, hide_index=True)

with outlook_tab:
    st.subheader(f'{state}: six-month fuel-sales outlook')
    st.warning('Petrol plus total diesel sales include non-road uses. Forecast months follow the data cutoff and may already be in the past today. They are not an emissions or policy-impact forecast.')
    st.write(f"Selected method: **{forecast['method']}**. Earlier rolling windows: **{forecast['rolling_windows']}**. "
             f"Untouched final-six-month MAPE: **{forecast['mape_pct']:.2f}%**.")
    st.write(f"Same-holdout seasonal-naive baseline: **{forecast['holdout_baseline']['mape_pct']:.2f}% MAPE**. "
             'This comparison is reported after method selection; a selected model can underperform the baseline on the final holdout.')
    fig = go.Figure()
    observations = monthly[monthly.state == state].sort_values('date').tail(24)
    fig.add_scatter(x=observations.date, y=observations.consumption_ml, name='Observed sales', mode='lines')
    for key, label in [('forecast', 'Untouched holdout prediction'), ('future', 'After-cutoff forecast')]:
        rows = forecast['series'][key]
        fig.add_scatter(x=[r['date'] for r in rows], y=[r['value'] for r in rows], name=label, mode='lines+markers', line={'dash': 'dash'})
    future = forecast['series']['future']
    fig.add_scatter(x=[r['date'] for r in future], y=[r['upper_95'] for r in future], mode='lines', line={'width': 0}, showlegend=False)
    fig.add_scatter(x=[r['date'] for r in future], y=[r['lower_95'] for r in future], mode='lines', line={'width': 0}, fill='tonexty', name='Approximate 95% band')
    fig.update_layout(yaxis_title='Petrol plus diesel sales (ML)', xaxis_title='Month')
    fig.update_yaxes(rangemode='tozero')
    st.plotly_chart(fig, width='stretch')
    st.caption(forecast['interval_caveat'])
    st.caption(f"Holdout coverage across {forecast['test_months']} months only: "
               f"80% band {forecast['holdout_interval_coverage_pct']['80']}%; "
               f"95% band {forecast['holdout_interval_coverage_pct']['95']}%.")
    st.dataframe(pd.DataFrame(future), hide_index=True)
    st.write('Candidate comparison uses earlier windows, before the final six months are evaluated.')
    st.dataframe(pd.DataFrame([{'method': name, **values} for name, values in forecast['candidates'].items()]), hide_index=True)
    with st.expander('Chronological evaluation windows'):
        st.dataframe(pd.DataFrame(forecast['folds']), hide_index=True)

with methods_tab:
    st.subheader('Interpretation limits')
    for limitation in LIMITATIONS:
        st.write(f'- {limitation}')
    st.warning('The simple sales-times-factor diagnostic remains unresolved: it is not a validated conversion from fuel sales to official transport inventories. Use the official inventory for emissions briefings.')
    regression = results['emissions_regression']
    st.write(regression['_caveat'])
    st.dataframe(pd.DataFrame([{'method': name, 'Chronological MAE (kt CO2-e)': regression[name]['cv_mae_kt_co2e'],
                              'MAPE (%)': regression[name]['mape_pct']} for name in ['previous_year', 'linear_regression', 'random_forest']]), hide_index=True)
    st.caption(regression['evaluation'])
    st.write(f'Errors for {state}, avoiding the pooled state-size effect:')
    st.dataframe(pd.DataFrame([{'method': name, **regression[name]['per_state'][state]}
                              for name in ['previous_year', 'linear_regression', 'random_forest']]), hide_index=True)
    st.subheader('Sources and run evidence')
    st.write(f"Run: `{metadata['run_id']}`. Built: {metadata['built_at']}. Source download dates were not recorded in the original project.")
    for source in metadata['sources']:
        st.markdown(f"[{source['source']}]({source['url']}) — {source['boundary']}")
        st.caption(f"File SHA256: {source['sha256']}")
    st.subheader('Data quality and monitoring')
    report_path = ROOT / 'reports/monitoring/drift_report.json'
    if report_path.exists():
        import json
        report = json.loads(report_path.read_text(encoding='utf-8'))
        if report.get('run_id') == metadata['run_id']:
            st.json(report)
        else:
            st.info('Monitoring report is from a different run; rebuild the pipeline to refresh it.')
    st.caption('Pooled KS comparisons describe distribution changes, not model accuracy or policy effects.')
