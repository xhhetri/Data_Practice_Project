import pytest


def test_salted_password_verification_and_bounded_hash_parameters():
    from src.fleet.security import hash_password, verify_password
    first = hash_password('example-test-password-123')
    second = hash_password('example-test-password-123')
    assert first != second
    assert verify_password('example-test-password-123', first)
    assert not verify_password('wrong', first)
    assert not verify_password('anything', first.replace('$16384$', '$1073741824$'))
    assert not verify_password('anything', 'malformed')
    with pytest.raises(ValueError):
        hash_password('short')


def test_production_configuration_fails_closed():
    from src.fleet.security import validate_config, hash_password
    with pytest.raises(ValueError):
        validate_config('production', '')
    with pytest.raises(ValueError):
        validate_config('production', 'invalid')
    with pytest.raises(ValueError):
        validate_config('unknown', '')
    assert validate_config('local', '') is False
    assert validate_config('production', hash_password('example-test-password-123')) is True


def test_failed_logins_are_persistently_throttled(tmp_path):
    from src.fleet.security import AuthGate, hash_password
    value = hash_password('example-test-password-123')
    gate = AuthGate(tmp_path / 'auth.sqlite', value)
    for _ in range(5):
        assert not gate.attempt('wrong', now=1000)['ok']
    recreated = AuthGate(tmp_path / 'auth.sqlite', value)
    blocked = recreated.attempt('example-test-password-123', now=1001)
    assert not blocked['ok'] and blocked['retry_after'] > 0
    assert recreated.attempt('example-test-password-123', now=1301)['ok']


def test_sessions_expire_and_credential_changes_revoke_access(tmp_path):
    from src.fleet.security import AuthGate, hash_password
    value = hash_password('example-test-password-123')
    gate = AuthGate(tmp_path / 'auth.sqlite', value)
    session = gate.new_session(now=1000)
    assert gate.session_valid(session, now=1100)
    assert not gate.session_valid(session, now=3001)
    session = gate.new_session(now=1000)
    changed = AuthGate(tmp_path / 'auth.sqlite', hash_password('another-test-password-123'))
    assert not changed.session_valid(session, now=1100)
    assert not gate.session_valid({}, now=1100)
def test_authentication_closes_database_connections(tmp_path, monkeypatch):
    import sqlite3
    import src.fleet.security as security
    opened = []
    connect = sqlite3.connect
    def track(*args, **kwargs):
        connection = connect(*args, **kwargs)
        opened.append(connection)
        return connection
    monkeypatch.setattr(sqlite3, 'connect', track)
    gate = security.AuthGate(tmp_path / 'auth.sqlite', security.hash_password('example-test-password-123'))
    gate.attempt('incorrect')
    for connection in opened:
        with pytest.raises(sqlite3.ProgrammingError, match='closed'):
            connection.execute('SELECT 1')

