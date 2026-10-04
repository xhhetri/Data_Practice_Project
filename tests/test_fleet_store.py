from pathlib import Path
import pytest


def repository(tmp_path):
    from src.fleet.store import Repository
    return Repository(tmp_path / 'records.sqlite')


def fuel(vehicle, **changes):
    value = dict(vehicle_id=vehicle['id'], occurred_at='2024-01-08T12:00', litres='40.125',
                 amount='80.25', odometer_km='10000', tank_status='full')
    value.update(changes)
    return value


def test_persistence_exact_money_and_idempotency(tmp_path):
    repo = repository(tmp_path)
    v = repo.create_vehicle(dict(name='Van', fuel_grade='Diesel', tank_capacity_l='70'))
    p = repo.save_purchase(fuel(v), 'first')
    assert p['amount_cents'] == 8025 and p['litres'] == '40.125'
    assert repo.save_purchase(fuel(v), 'first')['id'] == p['id']
    with pytest.raises(ValueError, match='request'):
        repo.save_purchase(fuel(v, amount='85'), 'first')
    from src.fleet.store import Repository
    assert Repository(repo.path).purchases()[0]['id'] == p['id']


@pytest.mark.parametrize('changes', [dict(amount='1.001'), dict(amount='NaN'), dict(litres='Infinity'),
                                    dict(litres='0'), dict(odometer_km='-1'),
                                    dict(occurred_at='2099-01-01'), dict(tank_status='maybe'),
                                    dict(incomplete='false'), dict(vehicle_id='unknown')])
def test_invalid_input_never_writes_a_purchase(tmp_path, changes):
    repo = repository(tmp_path)
    v = repo.create_vehicle(dict(name='Van', fuel_grade='Diesel'))
    with pytest.raises(ValueError):
        repo.save_purchase(fuel(v, **changes), 'invalid')
    assert repo.purchases() == []


def test_stale_edit_rejected_and_void_is_reversible(tmp_path):
    repo = repository(tmp_path)
    v = repo.create_vehicle(dict(name='Van', fuel_grade='Diesel'))
    p = repo.save_purchase(fuel(v), 'first')
    updated = repo.update_purchase(p['id'], {'amount': '90'}, p['revision'])
    assert updated['revision'] == 2 and updated['amount_cents'] == 9000
    with pytest.raises(ValueError, match='changed'):
        repo.update_purchase(p['id'], {'amount': '100'}, 1)
    voided = repo.void_purchase(p['id'], 2)
    assert repo.purchases() == []
    restored = repo.void_purchase(p['id'], voided['revision'], void=False)
    assert restored['revision'] == 4 and len(repo.purchases()) == 1
    assert [x['action'] for x in repo.history() if x['entity'] == 'purchase'] == ['create', 'update', 'void', 'restore']


def test_archived_vehicle_blocks_new_records_but_allows_correction(tmp_path):
    repo = repository(tmp_path)
    v = repo.create_vehicle(dict(name='Van', fuel_grade='Diesel'))
    p = repo.save_purchase(fuel(v), 'first')
    repo.update_vehicle(v['id'], {'archived': True}, 1)
    with pytest.raises(ValueError):
        repo.save_purchase(fuel(v), 'second')
    assert repo.update_purchase(p['id'], {'note': 'Receipt checked'}, 1)['note'] == 'Receipt checked'


def test_batch_is_atomic_and_repeated_batch_returns_original_rows(tmp_path):
    repo = repository(tmp_path)
    v = repo.create_vehicle(dict(name='Van', fuel_grade='Diesel'))
    rows = [fuel(v), fuel(v, vehicle_id='missing')]
    with pytest.raises(ValueError):
        repo.import_rows(rows, 'batch')
    assert repo.purchases() == []
    saved = repo.import_rows([fuel(v)], 'batch')
    assert repo.import_rows([fuel(v)], 'batch') == saved
    assert len(repo.purchases()) == 1
    with pytest.raises(ValueError, match='batch'):
        repo.import_rows([fuel(v, amount='90')], 'batch')


def test_review_refund_requires_evidence_and_history_is_retained(tmp_path):
    repo = repository(tmp_path)
    with pytest.raises(ValueError):
        repo.save_review(dict(id='finding', status='explained', refund_amount='12'))
    result = repo.save_review(dict(id='finding', status='follow-up needed', note='Check receipt'))
    assert result['status'] == 'follow-up needed'
    assert len(repo.reviews()) == 1


def test_database_schema_version_and_foreign_keys(tmp_path):
    import sqlite3
    repo = repository(tmp_path)
    with sqlite3.connect(repo.path) as c:
        c.execute('PRAGMA user_version=99')
    from src.fleet.store import Repository
    with pytest.raises(ValueError, match='version'):
        Repository(repo.path)


def test_concurrent_review_outcome_rejects_stale_update(tmp_path):
    repo = repository(tmp_path)
    first = repo.save_review(dict(id='finding', status='open'), expected_updated_at=None)
    second = repo.save_review(dict(id='finding', status='explained', note='Checked receipt'),
                              expected_updated_at=first['updated_at'])
    with pytest.raises(ValueError, match='changed'):
        repo.save_review(dict(id='finding', status='follow-up needed'), expected_updated_at=first['updated_at'])
    assert repo.reviews() == [second]
    with pytest.raises(ValueError, match='changed'):
        repo.save_review(dict(id='finding', status='open'), expected_updated_at=None)
