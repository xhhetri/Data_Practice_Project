import importlib
import importlib.util


def test_refresh_only_accepts_loopback_host_and_same_origin():
    assert importlib.util.find_spec('scripts.serve_review'), 'A loopback review server is required'
    module = importlib.import_module('scripts.serve_review')
    assert module.local_request('127.0.0.1:8765', 'http://127.0.0.1:8765', 8765)
    assert module.local_request('localhost:8765', None, 8765)
    assert not module.local_request('attacker.example:8765', None, 8765)
    assert not module.local_request('127.0.0.1:8765', 'https://attacker.example', 8765)
    assert not module.local_request('127.0.0.1:8765', 'http://127.0.0.1:9999', 8765)
