from src.analysis import clean, eda, model, validate
from src import db, provenance
from scripts import build_dashboard, generate_diagrams, build_evidence
from monitoring import monitor


def main():
    for name, action in [
        ('Clean and validate government sources', clean.run),
        ('Exploratory analysis', eda.run),
        ('Chronological evaluation and beyond-cutoff forecasts', model.run),
        ('Signed boundary reconciliation', validate.run),
        ('Bind source, code and output provenance', provenance.write_metadata),
        ('Data quality gate and drift diagnostics', lambda: monitor.run(log_to_db=False)),
        ('Publish quality-checked artifacts to SQLite', db.run),
        ('Build analyst dashboard', build_dashboard.run),
        ('Generate architecture and workflow figures', generate_diagrams.run),
        ('Generate technical evidence and example briefings', build_evidence.run),
    ]:
        print(f'\n{name}', flush=True)
        action()
    print('\nCompleted. Open dashboard/index.html or run Streamlit; see reports/run_metadata.json.', flush=True)


if __name__ == '__main__':
    main()
