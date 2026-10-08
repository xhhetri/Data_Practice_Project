"""Render the actual architecture and user workflow for the demonstration."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def diagram(path, title, rows):
    fig, ax = plt.subplots(figsize=(13, 9))
    ax.axis('off')
    ax.set_title(title, fontsize=18, weight='bold', pad=25)
    for index, text in enumerate(rows):
        y = 1 - (index + .6) / len(rows)
        ax.text(.5, y, text, ha='center', va='center', fontsize=12,
                bbox={'boxstyle': 'round,pad=.7', 'facecolor': '#e8f2f4', 'edgecolor': '#286c76'})
        if index < len(rows)-1:
            ax.annotate('', xy=(.5, y-.085), xytext=(.5, y-.045),
                        arrowprops={'arrowstyle': '->', 'color': '#286c76'})
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160, bbox_inches='tight')
    plt.close(fig)


def run():
    diagram(ROOT/'docs/architecture/architecture_v5.png', 'FuelScope — implemented evidence architecture', [
        'Original six government source files → validated transport pipeline\nRetained annual analysis, Gold warehouse and historical run identity',
        'AIP weekday prices + DCCEEW weekly MSO + current petroleum extract\nExplicit refresh → temporary download → schema, value and date checks',
        'Validated market cache + source manifest\nObservation cutoffs, retrieval dates, source hashes and failed-feed retention',
        'Separate petrol/diesel state sales → seasonal naive vs Holt-Winters\n41 earlier rolling origins → untouched six-month holdout → refit outlook',
        'Market evidence snapshot + model identity\nNational stocks stay national; city prices and state sales remain distinct',
        'FuelScope browser dashboard + loopback refresh service\nCached daily/weekly context • monthly outlook • retained transport analysis',
        'Analyst review → local checkpoint and notes → cited Markdown/CSV/print\nAssessment 4: added predictors and real repeated-use evaluation'])
    diagram(ROOT/'docs/workflow/workflow_v5.png', 'FuelScope — daily check and weekly briefing workflow', [
        'Open the workspace → select jurisdiction and petrol/diesel',
        'Check official source updates; retain prior evidence if a feed fails',
        'Daily: inspect dated wholesale-price changes and the source',
        'Weekly: inspect national holdings, effective obligation and source age',
        'On sales release: inspect fuel-specific outlook and baseline performance',
        'Record questions and interpretation → export a cited briefing',
        'Save a browser checkpoint → next visit compare actual evidence changes',
        'Assessment 4: evaluate review time, interpretation and voluntary return'])
    diagram(ROOT/'docs/architecture/architecture_v4.png', 'Australian transport briefing tool — actual architecture', [
        'Government workbooks → Bronze source manifest\nOfficial URLs, file hashes, explicit boundaries',
        'Silver: typed source tables in Parquet\nHistorical BITRE stock • monthly fuel SALES • whole-transport inventories',
        'Gold: annual state/FY table + population • monthly sales series\nCompleteness checks • documented calendar-year stock alignment',
        'EDA + chronological regression + rolling fuel forecast evaluation\nUntouched holdout • beyond-cutoff outlook • empirical uncertainty',
        'Signed reconciliation + hashed provenance → quality gate → SQLite\nRejected data retain the prior database snapshot',
        'Shared briefing calculations → Streamlit / FastAPI\nSame pipeline artifacts → standalone HTML dashboard',
        'Analyst selects state and period → comparison → cited briefing export\nMonitoring: completeness, cutoff age and pooled distribution diagnostics'])
    diagram(ROOT/'docs/workflow/workflow_v4.png', 'Analyst and development workflow', [
        'Download and retain government sources; document origin and boundary',
        'Run the pipeline → validate sources → clean → analyze → evaluate',
        'Reconcile boundaries → bind run → quality gate → publish SQLite → build interfaces',
        'Analyst: select jurisdiction and financial-year range',
        'Read total and per-capita changes → compare peers → inspect limits',
        'Inspect beyond-cutoff sales outlook → export briefing and selected data',
        'Evaluate task time, accuracy and traceability against manual workflow',
        'Review code, run tests and CI → record individual contribution evidence'])


if __name__ == '__main__':
    run()
