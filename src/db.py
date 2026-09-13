from _future_ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(_name_)

REPO_ROOT = Path(_file_).resolve().parents[1]
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