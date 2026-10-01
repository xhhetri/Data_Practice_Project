"""
monitoring/monitor.py
----------------------
Stage 8 of the project lifecycle: Monitoring & Improvement.

Lightweight, dependency-free data-drift check (no external monitoring
service required): compares the *current* `annual_master.csv` against a
saved *reference* snapshot, column by column, using a two-sample
Kolmogorov-Smirnov test (scipy.stats.ks_2samp). A column is flagged as
"drifted" when its KS p-value falls below MONITORING_DRIFT_PVALUE
(default 0.05, see .env).

First run: no reference snapshot exists yet, so this run's data becomes
the reference (baseline) and is saved to
`reports/monitoring/reference_annual_master.csv`. Every later run is
compared against that baseline.

To re-baseline deliberately (e.g. after a real, expected upstream change
to the source data), delete `reports/monitoring/reference_annual_master.csv`
and re-run this script.

Usage:
    python monitoring/monitor.py

Optional, heavier alternative: Evidently AI (`pip install evidently`)
produces a full interactive HTML drift report with the same idea, more
detail, and less custom code -- worth adopting if a browser-based report
is preferred over this JSON summary. Not included by default here to
keep the dependency list small; the KS-test approach above already
satisfies "detect data/model drift" without pulling in an extra library.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from scipy.stats import ks_2samp

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src import db  # noqa: E402  (after sys.path insert)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

load_dotenv(REPO_ROOT / ".env")

PROCESSED_DIR = REPO_ROOT / "data" / "processed"
MONITORING_DIR = REPO_ROOT / "reports" / "monitoring"
REFERENCE_PATH = MONITORING_DIR / "reference_annual_master.csv"
DRIFT_REPORT_PATH = MONITORING_DIR / "drift_report.json"

NUMERIC_COLUMNS_TO_CHECK = [
    "fuel_consumption_ml",
    "vkt_road_million_km",
    "registered_vehicles",
    "ghg_kt_co2e",
]


def _pvalue_threshold() -> float:
    return float(os.environ.get("MONITORING_DRIFT_PVALUE", "0.05"))


def run() -> dict:
    MONITORING_DIR.mkdir(parents=True, exist_ok=True)
    current_path = PROCESSED_DIR / "annual_master.csv"
    if not current_path.exists():
        raise FileNotFoundError(
            f"{current_path} not found -- run the pipeline first "
            "(python run_pipeline.py)"
        )
    current = pd.read_csv(current_path)

    if not REFERENCE_PATH.exists():
        current.to_csv(REFERENCE_PATH, index=False)
        log.info(
            "No reference snapshot found -- saved this run as the baseline: %s",
            REFERENCE_PATH,
        )
        report = {
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "status": "baseline_created",
            "columns": {},
        }
        DRIFT_REPORT_PATH.write_text(json.dumps(report, indent=2))
        return report

    reference = pd.read_csv(REFERENCE_PATH)
    threshold = _pvalue_threshold()
    columns_report = {}
    any_drift = False

    for col in NUMERIC_COLUMNS_TO_CHECK:
        if col not in current.columns or col not in reference.columns:
            continue
        stat, pvalue = ks_2samp(reference[col].dropna(), current[col].dropna())
        drifted = bool(pvalue < threshold)
        any_drift = any_drift or drifted
        columns_report[col] = {
            "ks_statistic": round(float(stat), 4),
            "p_value": round(float(pvalue), 6),
            "drifted": drifted,
        }
        level = log.warning if drifted else log.info
        level(
            "%s -- KS=%.4f, p=%.6f -- %s",
            col, stat, pvalue, "DRIFT DETECTED" if drifted else "no significant drift",
        )

    report = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "status": "drift_detected" if any_drift else "no_drift",
        "pvalue_threshold": threshold,
        "reference_rows": len(reference),
        "current_rows": len(current),
        "columns": columns_report,
    }
    DRIFT_REPORT_PATH.write_text(json.dumps(report, indent=2))
    log.info("Drift report written to %s", DRIFT_REPORT_PATH)

    # Best-effort: also log this check into the DB's pipeline_runs-style
    # audit trail so the dashboard's Monitoring tab has something to show.
    try:
        engine = db.get_engine()
        with engine.begin() as conn:
            from sqlalchemy import text

            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS monitoring_runs (
                        checked_at TEXT,
                        status TEXT,
                        report_json TEXT
                    )
                    """
                )
            )
            conn.execute(
                text(
                    "INSERT INTO monitoring_runs (checked_at, status, report_json) "
                    "VALUES (:checked_at, :status, :report_json)"
                ),
                {
                    "checked_at": report["checked_at"],
                    "status": report["status"],
                    "report_json": json.dumps(report),
                },
            )
        log.info("Logged this check into the 'monitoring_runs' DB table")
    except Exception as e:  # pragma: no cover -- monitoring must not crash the pipeline
        log.warning("Could not log to DB (non-fatal): %s", e)

    return report


if __name__ == "__main__":
    run()
