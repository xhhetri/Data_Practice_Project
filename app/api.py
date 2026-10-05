"""Local analyst API. Start with: python -m uvicorn app.api:app --port 8000."""
from __future__ import annotations
import json
import pickle
import sys
from pathlib import Path
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
from src.briefing import build_briefing, render_briefing
from src.serving import load_snapshot
from src.provenance import sha256

MODEL_PATH = REPO_ROOT / 'reports/model_results/emissions_regression.pkl'
DRIFT_REPORT_PATH = REPO_ROOT / 'reports/monitoring/drift_report.json'
app = FastAPI(title='Australian transport briefing API', version='2.0.0',
              description='Cited historical briefings and evaluated fuel-sales outlooks. Local demonstration service.')


class PredictRequest(BaseModel):
    fuel_consumption_ml: float = Field(gt=0, allow_inf_nan=False, description='Annual petrol plus total diesel SALES, ML')
    vkt_road_million_km: float = Field(gt=0, allow_inf_nan=False, description='Annual road VKT, million km')
    registered_vehicles: int = Field(gt=0, description='Historical calendar-year vehicle stock')


def _snapshot():
    try:
        return load_snapshot()
    except (OSError, ValueError, KeyError, IndexError, pd.errors.DatabaseError) as error:
        raise HTTPException(503, 'A completed database run is required. Run python run_pipeline.py.') from error
    except Exception as error:
        # SQLAlchemy driver failures also mean that the local data service is unavailable.
        from sqlalchemy.exc import SQLAlchemyError
        if isinstance(error, SQLAlchemyError):
            raise HTTPException(503, 'The database is unavailable. Run python run_pipeline.py.') from error
        raise


@app.get('/health')
def health():
    *_, metadata = _snapshot()
    return {'status': 'ready', 'run_id': metadata['run_id'], 'coverage': metadata['coverage']}


@app.get('/states')
def states():
    annual, *_ = _snapshot()
    return sorted(annual.state.unique().tolist())


@app.get('/provenance')
def provenance():
    return _snapshot()[3]


@app.get('/briefing')
def briefing(state: str = 'NSW', start_year: int = Query(2010, ge=1900, le=2100),
             end_year: int = Query(2023, ge=1900, le=2100)):
    annual, _, results, metadata = _snapshot()
    try:
        summary = build_briefing(annual, state.upper(), start_year, end_year)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    forecast = results.get(f'fuel_forecast_{state.upper()}')
    return {'run_id': metadata['run_id'], 'summary': summary,
            'markdown': render_briefing(summary, metadata, forecast)}


@app.get('/forecast/{state}')
def forecast(state: str):
    _, _, results, metadata = _snapshot()
    key = f'fuel_forecast_{state.upper()}'
    if key not in results:
        raise HTTPException(404, 'No separate fuel-sales forecast for this jurisdiction')
    return {'run_id': metadata['run_id'], **results[key]}


@app.get('/metrics')
def metrics(result_group: str | None = None):
    from src.db import _flatten_metrics
    _, _, results, _ = _snapshot()
    selected = {result_group: results[result_group]} if result_group in results else results if result_group is None else {}
    return _flatten_metrics(selected).to_dict('records')


@app.get('/monitoring/drift')
def monitoring_drift():
    if not DRIFT_REPORT_PATH.exists():
        raise HTTPException(503, 'No monitoring report; run the pipeline first')
    report = json.loads(DRIFT_REPORT_PATH.read_text(encoding='utf-8'))
    if report.get('run_id') != _snapshot()[3]['run_id']:
        raise HTTPException(503, 'Monitoring report does not match the database run')
    return report


@app.post('/predict')
def predict(payload: PredictRequest):
    metadata = _snapshot()[3]
    expected = metadata['outputs'].get('reports/model_results/emissions_regression.pkl')
    if not MODEL_PATH.exists() or sha256(MODEL_PATH) != expected:
        raise HTTPException(503, 'Model does not match this database run; rebuild the pipeline')
    with MODEL_PATH.open('rb') as source:
        artifact = pickle.load(source)  # Only the local pipeline's trusted artifact is loaded.
    inputs = payload.model_dump()
    for feature, (lower, upper) in artifact['ranges'].items():
        if not lower <= inputs[feature] <= upper:
            raise HTTPException(422, f'{feature} is outside the observed training range [{lower}, {upper}]')
    frame = pd.DataFrame([inputs], columns=artifact['features'])
    prediction = float(artifact['model'].predict(frame)[0])
    return {'run_id': metadata['run_id'], 'method': artifact['method'],
            'predicted_ghg_kt_co2e': round(prediction, 2),
            'caveat': 'Associative estimate using contemporaneous inputs. It does not establish causation, '
                      'predict future emissions, or estimate the effect of a policy. Individual feature '
                      'ranges do not guarantee that their combination was observed.'}
