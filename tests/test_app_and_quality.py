import pandas as pd
from pathlib import Path
from streamlit.testing.v1 import AppTest


def test_app_completes_a_state_briefing_selection():
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / 'app/streamlit_app.py', default_timeout=30).run()
    assert not app.exception
    app.selectbox(key='state').set_value('NT').run()
    assert not app.exception
    assert app.session_state['briefing']['state'] == 'NT'
    assert app.session_state['briefing']['end_fy'] == 'FY2023-24'
    assert len(app.get('download_button')) == 2


def test_quality_detects_missing_month_and_duplicate_keys():
    from monitoring.monitor import check_quality
    annual = pd.DataFrame([{'state': 'NSW', 'year': 2023, 'ghg_kt_co2e': 10,
                            'fuel_consumption_ml': 50, 'vkt_road_million_km': 100,
                            'registered_vehicles': 1000}] * 2)
    monthly = pd.DataFrame({'state': ['NSW', 'NSW'], 'date': ['2024-01-01', '2024-03-01'],
                            'consumption_ml': [10, 20]})
    report = check_quality(annual, monthly, now='2024-04-01')
    assert report['duplicate_annual_keys'] == 1
    assert report['missing_months']['NSW'] == ['2024-02-01']
    assert report['status'] == 'failed'
