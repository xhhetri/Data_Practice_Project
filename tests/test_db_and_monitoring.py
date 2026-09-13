"""
tests/test_db_and_monitoring.py
--------------------------------
Tests for the DBMS layer (src/db.py) and the drift-monitoring module
(monitoring/monitor.py) added on top of the existing clean/EDA/model/
validate pipeline. Uses a temporary SQLite file so it never touches the
project's real data/gold/warehouse.sqlite.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import create_engine, text

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src import db  # noqa: E402


@pytest.fixture()
def tmp_engine(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'test_warehouse.sqlite'}")
    yield engine
    engine.dispose()


def test_load_processed_to_db_writes_expected_tables(tmp_engine):
    summary = db.load_processed_to_db(engine=tmp_engine)

    assert "annual_master" in summary
    assert summary["annual_master"] > 0

    with tmp_engine.connect() as conn:
        tables = {
            row[0]
            for row in conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
        }
    assert "annual_master" in tables
    assert "pipeline_runs" in tables


def test_load_processed_to_db_records_audit_row(tmp_engine):
    db.load_processed_to_db(engine=tmp_engine)
    df = pd.read_sql("SELECT * FROM pipeline_runs", tmp_engine)
    assert len(df) == 1
    assert "annual_master" in df.iloc[0]["tables_loaded"]


def test_flatten_metrics_handles_nested_feature_importance():
    metrics = {
        "emissions_regression": {
            "linear_regression": {"cv_r2": 0.99},
            "random_forest": {
                "cv_r2": 0.99,
                "feature_importance": {"fuel_consumption_ml": 0.4},
            },
            "_caveat": "some text",
        }
    }
    flat = db._flatten_metrics(metrics)
    assert (flat["metric"] == "random_forest.feature_importance.fuel_consumption_ml").any()
    assert (flat["metric"] == "linear_regression.cv_r2").any()


def test_get_database_url_defaults_to_sqlite(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert db.get_database_url().startswith("sqlite:///")


def test_monitor_creates_baseline_on_first_run(tmp_path, monkeypatch):
    from monitoring import monitor

    monkeypatch.setattr(monitor, "MONITORING_DIR", tmp_path)
    monkeypatch.setattr(monitor, "REFERENCE_PATH", tmp_path / "reference_annual_master.csv")
    monkeypatch.setattr(monitor, "DRIFT_REPORT_PATH", tmp_path / "drift_report.json")

    report = monitor.run()
    assert report["status"] == "baseline_created"
    assert (tmp_path / "reference_annual_master.csv").exists()


def test_monitor_detects_no_drift_on_identical_rerun(tmp_path, monkeypatch):
    from monitoring import monitor

    monkeypatch.setattr(monitor, "MONITORING_DIR", tmp_path)
    monkeypatch.setattr(monitor, "REFERENCE_PATH", tmp_path / "reference_annual_master.csv")
    monkeypatch.setattr(monitor, "DRIFT_REPORT_PATH", tmp_path / "drift_report.json")

    monitor.run()  # creates baseline
    report = monitor.run()  # compares current data against itself

    assert report["status"] == "no_drift"
    for col_report in report["columns"].values():
        assert col_report["drifted"] is False
