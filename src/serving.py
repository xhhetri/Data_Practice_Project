"""Read one consistent database snapshot for the app and API."""
import json
import pandas as pd
from src import db


def load_snapshot():
    engine = db.get_engine()
    try:
        with engine.begin() as conn:
            db.begin_sqlite_transaction(conn)
            annual = pd.read_sql('SELECT * FROM annual_master_with_population', conn)
            monthly = pd.read_sql('SELECT * FROM monthly_fuel_series', conn)
            records = pd.read_sql('SELECT * FROM analysis_results', conn)
            metadata = json.loads(pd.read_sql('SELECT payload FROM pipeline_metadata', conn).iloc[0].payload)
        results = {row.result_group: json.loads(row.payload) for row in records.itertuples()}
        if annual.empty or monthly.empty or results['_run']['run_id'] != metadata['run_id']:
            raise ValueError('The database does not contain a complete, matching run')
        return annual, monthly, results, metadata
    finally:
        engine.dispose()
