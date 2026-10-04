from pathlib import Path
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


def app(monkeypatch, tmp_path):
    monkeypatch.setenv('FLEET_DATA_DIR', str(tmp_path))
    monkeypatch.setenv('FLEET_MODE', 'local')
    monkeypatch.delenv('FLEET_PASSWORD_HASH', raising=False)
    return AppTest.from_file(ROOT / 'app/fleet_app.py', default_timeout=30).run()


def test_real_workspace_starts_empty_and_accepts_daily_records(monkeypatch, tmp_path):
    a = app(monkeypatch, tmp_path)
    assert not a.exception
    assert any('Add your first vehicle' in i.value for i in a.info)
    a.radio(key='page').set_value('Vehicles').run()
    a.text_input(key='vehicle_name').set_value('Test van')
    a.button(key='create_vehicle').click().run()
    assert not a.exception
    a.radio(key='page').set_value('Record fuel').run()
    a.text_input(key='new_litres').set_value('40')
    a.text_input(key='new_amount').set_value('80')
    a.button(key='save_purchase').click().run()
    assert not a.exception
    from src.fleet.store import Repository
    repo = Repository(tmp_path / 'records.sqlite')
    assert repo.purchases()[0]['amount_cents'] == 8000
    a.radio(key='page').set_value('This week').run()
    assert not a.exception
    assert any('80.00' in m.value for m in a.metric)
    assert len(a.get('download_button')) >= 1


def test_demo_is_explicit_and_does_not_populate_real_records(monkeypatch, tmp_path):
    a = app(monkeypatch, tmp_path)
    a.radio(key='workspace_mode').set_value('Fictional demo').run()
    assert not a.exception
    assert any('Fictional demonstration data' in w.value for w in a.warning)
    from src.fleet.store import Repository
    assert Repository(tmp_path / 'records.sqlite').purchases() == []
    assert Repository(tmp_path / 'demo.sqlite').purchases()


def test_unconfigured_production_fails_before_private_records(monkeypatch, tmp_path):
    monkeypatch.setenv('FLEET_DATA_DIR', str(tmp_path))
    monkeypatch.setenv('FLEET_MODE', 'production')
    monkeypatch.delenv('FLEET_PASSWORD_HASH', raising=False)
    a = AppTest.from_file(ROOT / 'app/fleet_app.py', default_timeout=30).run()
    assert not a.exception
    assert a.error
    assert not a.get('download_button') and not a.metric


def test_configured_production_requires_login(monkeypatch, tmp_path):
    from src.fleet.security import hash_password
    monkeypatch.setenv('FLEET_DATA_DIR', str(tmp_path))
    monkeypatch.setenv('FLEET_MODE', 'production')
    monkeypatch.setenv('FLEET_PASSWORD_HASH', hash_password('example-test-password-123'))
    a = AppTest.from_file(ROOT / 'app/fleet_app.py', default_timeout=30).run()
    assert not a.exception and not a.get('download_button')
    a.text_input(key='login_password').set_value('example-test-password-123')
    a.button(key='sign_in').click().run()
    assert not a.exception
    assert a.radio(key='page')
    a.button(key='sign_out').click().run()
    assert not a.get('download_button')


def test_validation_error_preserves_entered_receipt(monkeypatch, tmp_path):
    a = app(monkeypatch, tmp_path)
    a.radio(key='page').set_value('Vehicles').run()
    a.text_input(key='vehicle_name').set_value('Van')
    a.button(key='create_vehicle').click().run()
    a.radio(key='page').set_value('Record fuel').run()
    a.text_input(key='new_litres').set_value('40')
    a.text_input(key='new_amount').set_value('invalid')
    a.button(key='save_purchase').click().run()
    assert a.error and not a.exception
    assert a.text_input(key='new_litres').value == '40'
    assert a.text_input(key='new_amount').value == 'invalid'


def test_switching_workspaces_clears_unsaved_private_form_values(monkeypatch, tmp_path):
    a = app(monkeypatch, tmp_path)
    a.radio(key='workspace_mode').set_value('Fictional demo').run()
    a.radio(key='page').set_value('Record fuel').run()
    a.text_area(key='new_note').set_value('Demo-only draft')
    a.text_input(key='new_litres').set_value('12').run()
    a.radio(key='workspace_mode').set_value('My records').run()
    a.radio(key='page').set_value('Vehicles').run()
    a.text_input(key='vehicle_name').set_value('Real van')
    a.button(key='create_vehicle').click().run()
    a.radio(key='page').set_value('Record fuel').run()
    assert not a.exception
    assert a.text_input(key='new_litres').value == ''
    assert a.text_area(key='new_note').value == ''


def test_receipt_correction_void_and_restore_through_actual_app(monkeypatch, tmp_path):
    from src.fleet.store import Repository
    repo = Repository(tmp_path / 'records.sqlite')
    v = repo.create_vehicle(dict(name='Van', fuel_grade='Diesel'))
    p = repo.save_purchase(dict(vehicle_id=v['id'], occurred_at='2024-01-08', litres='40', amount='80'), 'seed')
    a = app(monkeypatch, tmp_path)
    a.radio(key='page').set_value('History and backups').run()
    a.text_input(key=f"edit_{p['id']}_1_amount").set_value('85')
    next(b for b in a.button if b.label == 'Save correction').click().run()
    assert not a.exception and repo.purchases()[0]['amount_cents'] == 8500
    a.checkbox(key=f"edit_{p['id']}_2_confirm").check().run()
    next(b for b in a.button if b.label == 'Void record').click().run()
    assert not a.exception and repo.purchases() == []
    a.checkbox(key=f"edit_{p['id']}_3_confirm").check().run()
    next(b for b in a.button if b.label == 'Restore record').click().run()
    assert not a.exception and repo.purchases()[0]['revision'] == 4
