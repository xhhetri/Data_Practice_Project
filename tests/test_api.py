import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient
from app.api import app, PredictRequest


@pytest.mark.parametrize('fuel', [-1, float('inf'), float('nan')])
def test_prediction_rejects_impossible_fuel_inputs(fuel):
    with pytest.raises(ValidationError):
        PredictRequest(fuel_consumption_ml=fuel, vkt_road_million_km=5000, registered_vehicles=500000)


def test_briefing_api_returns_a_cited_export():
    response = TestClient(app).get('/briefing', params={'state': 'NSW', 'start_year': 2010, 'end_year': 2023})
    assert response.status_code == 200
    payload = response.json()
    assert payload['summary']['end_fy'] == 'FY2023-24'
    assert payload['run_id'] in payload['markdown']
    assert 'dcceew.gov.au' in payload['markdown']
