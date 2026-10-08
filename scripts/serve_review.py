"""Loopback-only FuelScope server with explicit, cached source refresh."""
from __future__ import annotations
import argparse
import json
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
STATE = {'busy': False, 'result': None, 'error': None}
LOCK = threading.Lock()


def local_request(host, origin, port):
    hosts = {f'127.0.0.1:{port}', f'localhost:{port}'}
    return host in hosts and (not origin or origin == f'http://{host}')


def refresh():
    try:
        from scripts.refresh_market import run
        result = run()
        with LOCK:
            STATE.update(result=result, error=None)
    except Exception as error:
        with LOCK:
            STATE.update(error=f'Refresh could not complete: {str(error)[:160]}')
    finally:
        with LOCK:
            STATE['busy'] = False


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / 'dashboard'), **kwargs)

    def json_response(self, status, data):
        content = json.dumps(data, allow_nan=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(content)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(content)

    def allowed(self):
        return local_request(self.headers.get('Host'), self.headers.get('Origin'), self.server.server_port)

    def do_GET(self):
        if not self.allowed():
            return self.json_response(403, {'message': 'Use the local FuelScope address.'})
        path = self.path.split('?')[0]
        if path == '/api/status':
            with LOCK:
                return self.json_response(200, {'application': 'FuelScope', **STATE})
        if path == '/api/review':
            try:
                data = json.loads((ROOT / 'reports/market_review/snapshot.json').read_text(encoding='utf-8'))
                return self.json_response(200, data)
            except (OSError, ValueError):
                return self.json_response(503, {'message': 'Build the market evidence before starting the review.'})
        if path.startswith('/api/'):
            return self.json_response(404, {'message': 'Unknown review action.'})
        return super().do_GET()

    def do_POST(self):
        if not self.allowed() or self.path != '/api/refresh' or self.headers.get('Content-Type') != 'application/json':
            return self.json_response(403, {'message': 'Refresh must be requested from the local dashboard.'})
        try:
            length = int(self.headers.get('Content-Length', 0))
            if length < 0 or length > 1024:
                raise ValueError('Oversized request')
            self.rfile.read(length)
        except ValueError:
            return self.json_response(400, {'message': 'Invalid refresh request.'})
        with LOCK:
            if STATE['busy']:
                return self.json_response(409, {'message': 'A source refresh is already running.'})
            STATE.update(busy=True, result=None, error=None)
        threading.Thread(target=refresh, daemon=True).start()
        return self.json_response(202, {'message': 'Checking official sources; the last valid review stays available.'})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8766)
    args = parser.parse_args()
    ThreadingHTTPServer.allow_reuse_address = False
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    print(f'FuelScope ready at http://127.0.0.1:{args.port}/', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
