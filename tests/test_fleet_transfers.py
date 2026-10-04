import json
import pytest
from src.fleet.store import Repository


@pytest.fixture
def repo(tmp_path):
    r = Repository(tmp_path / 'original.sqlite')
    r.create_vehicle(dict(name='Van', fuel_grade='Diesel'))
    return r


def preview(repo, content=None):
    from src.fleet.transfers import preview_csv
    content = content if content is not None else b'Car,Date,Litres,Cost,Full\nVan,2024-01-01,40,80,true\n'
    mapping = dict(vehicle_id='Car', occurred_at='Date', litres='Litres', amount='Cost', tank_status='Full')
    return preview_csv(content, mapping, repo.vehicles(), repo.purchases(True))


def test_preview_has_no_writes_and_confirm_is_idempotent(repo):
    from src.fleet.transfers import import_preview
    p = preview(repo)
    assert not p['errors'] and repo.purchases() == []
    first = import_preview(repo, p)
    assert first[0]['amount_cents'] == 8000
    second = import_preview(repo, preview(repo))
    assert first == second and len(repo.purchases()) == 1


def test_bad_row_makes_import_atomic_and_duplicate_is_a_warning(repo):
    from src.fleet.transfers import import_preview
    bad = preview(repo, b'Car,Date,Litres,Cost,Full\nVan,2024-01-01,40,80,true\nVan,2024-01-02,NaN,20,false\n')
    assert bad['errors']
    with pytest.raises(ValueError):
        import_preview(repo, bad)
    assert repo.purchases() == []
    import_preview(repo, preview(repo))
    candidate = preview(repo, b'Car,Date,Litres,Cost,Full\nVan,2024-01-01,40,80,true\nVan,2024-01-02,20,40,false\n')
    assert candidate['warnings']
    with pytest.raises(ValueError, match='review'):
        import_preview(repo, candidate)
    assert len(repo.purchases()) == 1
    assert len(import_preview(repo, candidate, acknowledge_duplicates=True)) == 2


def test_preview_is_invalidated_when_workspace_changes(repo):
    from src.fleet.transfers import import_preview
    p = preview(repo)
    repo.create_vehicle(dict(name='Second', fuel_grade='Diesel'))
    with pytest.raises(ValueError, match='changed'):
        import_preview(repo, p)


def test_concurrent_change_at_commit_boundary_rejects_stale_preview(repo, monkeypatch):
    from src.fleet.transfers import import_preview
    p = preview(repo)
    original = repo.import_rows
    def concurrent(rows, batch_id, **kwargs):
        repo.create_vehicle(dict(name='Concurrent', fuel_grade='Diesel'))
        return original(rows, batch_id, **kwargs)
    monkeypatch.setattr(repo, 'import_rows', concurrent)
    with pytest.raises(ValueError, match='changed'):
        import_preview(repo, p)
    assert repo.purchases() == []


@pytest.mark.parametrize('content', [b'Car,Car\nVan,Van\n', b'\xff', b'x' * (5 * 1024 * 1024 + 1), b''],
                         ids=['duplicate-columns', 'invalid-encoding', 'oversized', 'empty'])
def test_invalid_files_fail_safely(repo, content):
    with pytest.raises(ValueError):
        preview(repo, content)


def test_utf8_bom_and_unknown_vehicle(repo):
    p = preview(repo, b'\xef\xbb\xbfCar,Date,Litres,Cost,Full\nVan,2024-01-01,40,80,true\n')
    assert not p['errors']
    p = preview(repo, b'Car,Date,Litres,Cost,Full\nMissing,2024-01-01,40,80,true\n')
    assert p['errors']


def test_backup_roundtrip_retains_revisions_and_restore_is_separate(repo, tmp_path):
    from src.fleet.transfers import import_preview, backup, restore
    p = import_preview(repo, preview(repo))[0]
    repo.update_purchase(p['id'], dict(note='Receipt checked'), 1)
    repo.save_review(dict(id='finding', status='explained', note='Known workload'))
    content = backup(repo)
    path = restore(content, tmp_path / 'restored')
    restored = Repository(path)
    assert restored.purchases() == repo.purchases()
    assert restored.history() == repo.history()
    assert restored.reviews() == repo.reviews()
    assert path.parent == (tmp_path / 'restored').resolve()
    assert path != repo.path


def test_corrupt_or_malicious_restore_leaves_original_intact(repo, tmp_path):
    from src.fleet.transfers import backup, restore, import_preview
    import_preview(repo, preview(repo))
    original = repo.purchases()
    data = json.loads(backup(repo))
    data['tables']['purchases'][0]['vehicle_id'] = '../../other'
    with pytest.raises(ValueError):
        restore(json.dumps(data).encode(), tmp_path / 'restored')
    assert repo.purchases() == original
    with pytest.raises(ValueError):
        restore(b'{"schema_version":99}', tmp_path / 'restored')
    from src.fleet.store import fingerprint
    data.pop('checksum')
    data['checksum'] = fingerprint(data)
    with pytest.raises(ValueError):
        restore(json.dumps(data).encode(), tmp_path / 'restored')
    assert repo.purchases() == original


def test_formula_safe_csv_keeps_original_record_unchanged(repo):
    from src.fleet.transfers import export_csv, import_preview
    purchase = import_preview(repo, preview(repo))[0]
    repo.update_purchase(purchase['id'], dict(note='=HYPERLINK("bad")'), 1)
    rows = repo.purchases()
    exported = export_csv(rows, repo.vehicles())
    assert "'=HYPERLINK" in exported
    assert rows[0]['note'].startswith('=')
