"""Structural data quality, observation freshness and descriptive KS drift checks.

Run python monitoring/monitor.py. The saved baseline is deliberately persistent;
remove reference_annual_master.csv only when an upstream change has been reviewed.
KS comparisons pool states/years and cannot establish model accuracy or independence.
"""
from __future__ import annotations
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import ks_2samp
from sqlalchemy import text

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
from src import db
from src.briefing import load_metadata

log = logging.getLogger(__name__)
PROCESSED_DIR = REPO_ROOT / 'data/processed'
MONITORING_DIR = REPO_ROOT / 'reports/monitoring'
REFERENCE_PATH = MONITORING_DIR / 'reference_annual_master.csv'
DRIFT_REPORT_PATH = MONITORING_DIR / 'drift_report.json'
NUMERIC_COLUMNS_TO_CHECK = ['fuel_consumption_ml', 'vkt_road_million_km', 'registered_vehicles', 'ghg_kt_co2e']


def check_quality(annual, monthly, now=None, annual_population=None):
    dates = pd.to_datetime(monthly.date, errors='coerce')
    valid_dates = dates.dropna()
    expected = pd.date_range(valid_dates.min(), valid_dates.max(), freq='MS') if len(valid_dates) else []
    missing = {str(state): [d.strftime('%Y-%m-%d') for d in expected if d not in set(pd.to_datetime(group.date, errors='coerce'))]
               for state, group in monthly.groupby('state')}
    years = range(int(annual.year.min()), int(annual.year.max())+1)
    missing_years = {str(state): [y for y in years if y not in set(group.year)] for state, group in annual.groupby('state')}
    annual_values = annual[NUMERIC_COLUMNS_TO_CHECK].apply(pd.to_numeric, errors='coerce').to_numpy()
    monthly_values = pd.to_numeric(monthly.consumption_ml, errors='coerce').to_numpy()
    invalid_values = int((~np.isfinite(annual_values) | (annual_values <= 0)).sum() +
                         (~np.isfinite(monthly_values) | (monthly_values <= 0)).sum())
    report = {'duplicate_annual_keys': int(annual.duplicated(['state', 'year']).sum()),
              'duplicate_monthly_keys': int(monthly.duplicated(['state', 'date']).sum()),
              'missing_months': missing, 'missing_annual_years': missing_years,
              'invalid_or_nonpositive_values': invalid_values, 'missing_cells': int(annual.isna().sum().sum()+monthly.isna().sum().sum()),
              'invalid_or_non_monthstart_dates': int((dates.isna() | (dates.dt.day != 1)).sum()),
              'mismatched_state_coverage': sorted(set(annual.state) ^ set(monthly.state))}
    report['unexpected_state_coverage'] = sorted(set(annual.state) ^ {'NSW', 'VIC', 'QLD', 'SA', 'WA', 'TAS', 'NT'})
    if annual_population is not None:
        base_keys = set(zip(annual.state, annual.year))
        population_keys = set(zip(annual_population.state, annual_population.year))
        values = annual_population[['population', 'emissions_per_capita_kg', 'vkt_per_capita_km', 'vehicles_per_capita']].to_numpy()
        report['population_key_mismatch'] = len(base_keys ^ population_keys)
        report['invalid_population_rows'] = int((~np.isfinite(values) | (values <= 0)).any(axis=1).sum()) + int(annual_population.duplicated(['state', 'year']).sum())
    failures = (report['duplicate_annual_keys'] or report['duplicate_monthly_keys'] or invalid_values or
                report['missing_cells'] or report['invalid_or_non_monthstart_dates'] or report['mismatched_state_coverage'] or
                report['unexpected_state_coverage'] or report.get('population_key_mismatch') or report.get('invalid_population_rows') or
                any(missing.values()) or any(missing_years.values()))
    report['status'] = 'failed' if failures else 'passed'
    current_date = pd.Timestamp(now or datetime.now(timezone.utc)).tz_localize(None).normalize()
    sales_period_end = valid_dates.max() + pd.offsets.MonthEnd(0) if len(valid_dates) else pd.NaT
    annual_period_end = pd.Timestamp(year=int(annual.year.max())+1, month=6, day=30)
    sales_age = max(0, (current_date-sales_period_end).days) if pd.notna(sales_period_end) else None
    report['freshness'] = {'sales_period_end': str(sales_period_end.date()) if pd.notna(sales_period_end) else None,
                           'sales_age_days': sales_age, 'inventory_period_end': str(annual_period_end.date()),
                           'inventory_age_days': max(0, (current_date-annual_period_end).days),
                           'status': 'review_source_release_lag' if sales_age is None or sales_age > 90 else 'recent_sales_period',
                           'interpretation': 'Age measures the observation cutoff, not the retrieval date. Annual inventories have publication lags. This tool does not provide live observations.'}
    return report


def run(log_to_db=True):
    MONITORING_DIR.mkdir(parents=True, exist_ok=True)
    current = pd.read_csv(PROCESSED_DIR / 'annual_master.csv')
    monthly = pd.read_csv(PROCESSED_DIR / 'monthly_fuel_series.csv')
    quality = check_quality(current, monthly, annual_population=pd.read_csv(PROCESSED_DIR / 'annual_master_with_population.csv'))
    metadata = load_metadata()
    report = {'checked_at': datetime.now(timezone.utc).isoformat(), 'run_id': metadata['run_id'],
              'quality': quality, 'columns': {},
              'interpretation': 'Pooled descriptive KS checks; no significant drift does not prove data correctness or model accuracy.'}
    if not REFERENCE_PATH.exists():
        current.to_csv(REFERENCE_PATH, index=False)
        report['status'] = 'baseline_created'
    else:
        reference = pd.read_csv(REFERENCE_PATH)
        threshold = float(os.environ.get('MONITORING_DRIFT_PVALUE', '.05'))
        if not 0 < threshold < 1:
            raise ValueError('MONITORING_DRIFT_PVALUE must be between 0 and 1')
        for col in NUMERIC_COLUMNS_TO_CHECK:
            statistic, pvalue = ks_2samp(reference[col].dropna(), current[col].dropna())
            report['columns'][col] = {'ks_statistic': round(float(statistic), 4),
                                     'p_value': round(float(pvalue), 6), 'drifted': bool(pvalue < threshold)}
        report.update({'status': 'drift_detected' if any(v['drifted'] for v in report['columns'].values()) else 'no_drift',
                       'pvalue_threshold': threshold, 'reference_rows': len(reference), 'current_rows': len(current)})
    DRIFT_REPORT_PATH.write_text(json.dumps(report, indent=2, allow_nan=False), encoding='utf-8')
    if quality['status'] == 'failed':
        raise ValueError('Structural data quality failed; inspect reports/monitoring/drift_report.json')
    if log_to_db:
        engine = db.get_engine()
        try:
            with engine.begin() as conn:
                conn.execute(text('CREATE TABLE IF NOT EXISTS monitoring_runs (checked_at TEXT, status TEXT, report_json TEXT)'))
                conn.execute(text('INSERT INTO monitoring_runs VALUES (:checked_at, :status, :report_json)'),
                             {'checked_at': report['checked_at'], 'status': report['status'], 'report_json': json.dumps(report)})
        finally:
            engine.dispose()
    return report


if __name__ == '__main__':
    run()
