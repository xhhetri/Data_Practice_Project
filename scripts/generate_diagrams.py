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
