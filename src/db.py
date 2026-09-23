# from _future_ import annotations

# import json
# import logging
# import os
# from datetime import datetime, timezone
# from pathlib import Path

# import pandas as pd
# from dotenv import load_dotenv
# from sqlalchemy import create_engine, text

# logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
# log = logging.getLogger(_name_)

# REPO_ROOT = Path(_file_).resolve().parents[1]
# PROCESSED_DIR = REPO_ROOT / "data" / "processed"
# RESULTS_DIR = REPO_ROOT / "reports" / "model_results"

# load_dotenv(REPO_ROOT / ".env")

# DEFAULT_DATABASE_URL = f"sqlite:///{(REPO_ROOT / 'data' / 'gold' / 'warehouse.sqlite').as_posix()}"


# def get_database_url() -> str:
#     return os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)


# def get_engine():
#     url = get_database_url()
#     if url.startswith("sqlite:///"):
#         db_path = Path(url.replace("sqlite:///", "", 1))
#         db_path.parent.mkdir(parents=True, exist_ok=True)
#     log.info("Using database: %s", url)
#     return create_engine(url)


# _SKIP_KEYS = {"series", "_figure"}


# def _flatten(prefix: str, value, rows: list, group: str) -> None:
#     """Recursively flattens nested dicts (e.g. emissions_regression ->
#     random_forest -> feature_importance -> fuel_consumption_ml) into
#     dot-separated metric names, one row per leaf scalar value."""
#     if isinstance(value, dict):
#         for key, sub_value in value.items():
#             if key in _SKIP_KEYS:
#                 continue
#             new_prefix = f"{prefix}.{key}" if prefix else key
#             _flatten(new_prefix, sub_value, rows, group)
#     elif isinstance(value, (int, float, str, bool)):
#         rows.append({"result_group": group, "metric": prefix, "value": str(value)})
#     # lists (e.g. train/actual/forecast series, already excluded above) are skipped


# def _flatten_metrics(metrics: dict) -> pd.DataFrame:
#     """metrics.json -> one row per (result_group, dotted metric path).

#     Handles arbitrary nesting -- e.g. emissions_regression.random_forest
#     .feature_importance.fuel_consumption_ml -- not just one level deep,
#     so per-model metrics and feature importances both make it into the DB.
#     """
#     rows: list = []
#     for group, payload in metrics.items():
#         _flatten("", payload, rows, group)
#     return pd.DataFrame(rows)


"""
db.py
-----
The "Gold" storage layer: loads the analysis-ready tables produced by
clean.py, plus the model/validation results, into a real DBMS instead of
leaving them as loose CSV/JSON files.

Default DBMS: SQLite (file-based, zero setup, ships with Python). Set
DATABASE_URL in .env to point at Postgres or any other SQLAlchemy-
supported database instead -- no code change needed, only the connection
string. See .env.example for both options.

Tables written:
  annual_master                cleaned annual state-level table
  annual_master_with_population  same, + population/per-capita features
  monthly_fuel_series           monthly fuel consumption per state
  model_metrics                 one row per metric, flattened from metrics.json
  pipeline_runs                 one row per pipeline execution (for monitoring)

Usage:
    python -m src.db              # load current data/processed + reports into the DB
    from src.db import get_engine, run
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = REPO_ROOT / "data" / "processed"
RESULTS_DIR = REPO_ROOT / "reports" / "model_results"

load_dotenv(REPO_ROOT / ".env")

DEFAULT_DATABASE_URL = f"sqlite:///{(REPO_ROOT / 'data' / 'gold' / 'warehouse.sqlite').as_posix()}"


def get_database_url() -> str:
    return os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)


def get_engine():
    url = get_database_url()
    if url.startswith("sqlite:///"):
        db_path = Path(url.replace("sqlite:///", "", 1))
        db_path.parent.mkdir(parents=True, exist_ok=True)
    log.info("Using database: %s", url)
    return create_engine(url)


_SKIP_KEYS = {"series", "_figure"}


def _flatten(prefix: str, value, rows: list, group: str) -> None:
    """Recursively flattens nested dicts (e.g. emissions_regression ->
    random_forest -> feature_importance -> fuel_consumption_ml) into
    dot-separated metric names, one row per leaf scalar value."""
    if isinstance(value, dict):
        for key, sub_value in value.items():
            if key in _SKIP_KEYS:
                continue
            new_prefix = f"{prefix}.{key}" if prefix else key
            _flatten(new_prefix, sub_value, rows, group)
    elif isinstance(value, (int, float, str, bool)):
        rows.append({"result_group": group, "metric": prefix, "value": str(value)})
    # lists (e.g. train/actual/forecast series, already excluded above) are skipped


def _flatten_metrics(metrics: dict) -> pd.DataFrame:
    """metrics.json -> one row per (result_group, dotted metric path).

    Handles arbitrary nesting -- e.g. emissions_regression.random_forest
    .feature_importance.fuel_consumption_ml -- not just one level deep,
    so per-model metrics and feature importances both make it into the DB.
    """
    rows: list = []
    for group, payload in metrics.items():
        _flatten("", payload, rows, group)
    return pd.DataFrame(rows)


def load_processed_to_db(engine=None) -> dict:
    """Writes every processed CSV + flattened model metrics into the DB.
    Returns a small summary dict (also used by monitoring/monitor.py)."""
    engine = engine or get_engine()
    summary = {}

    csv_tables = {
        "annual_master": PROCESSED_DIR / "annual_master.csv",
        "annual_master_with_population": PROCESSED_DIR / "annual_master_with_population.csv",
        "monthly_fuel_series": PROCESSED_DIR / "monthly_fuel_series.csv",
    }
    for table, path in csv_tables.items():
        if not path.exists():
            log.warning("Skipping %s -- %s not found (run the pipeline first)", table, path)
            continue
        df = pd.read_csv(path)
        df.to_sql(table, engine, if_exists="replace", index=False)
        summary[table] = len(df)
        log.info("Loaded %d rows -> table '%s'", len(df), table)

    metrics_path = RESULTS_DIR / "metrics.json"
    if metrics_path.exists():
        with open(metrics_path) as f:
            metrics = json.load(f)
        metrics_df = _flatten_metrics(metrics)
        if not metrics_df.empty:
            metrics_df.to_sql("model_metrics", engine, if_exists="replace", index=False)
            summary["model_metrics"] = len(metrics_df)
            log.info("Loaded %d rows -> table 'model_metrics'", len(metrics_df))

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS pipeline_runs (
                    run_at TEXT,
                    tables_loaded TEXT,
                    row_counts TEXT
                )
                """
            )
        )
        conn.execute(
            text(
                "INSERT INTO pipeline_runs (run_at, tables_loaded, row_counts) "
                "VALUES (:run_at, :tables_loaded, :row_counts)"
            ),
            {
                "run_at": datetime.now(timezone.utc).isoformat(),
                "tables_loaded": ",".join(summary.keys()),
                "row_counts": json.dumps(summary),
            },
        )
    log.info("Recorded run in 'pipeline_runs' audit table")
    return summary


def run() -> None:
    load_processed_to_db()


if __name__ == "__main__":
    run()

