"""Generate the default market dashboard and preserve the annual briefing."""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def build_html(snapshot):
    template = (ROOT / 'dashboard/market_template.html').read_text(encoding='utf-8')
    marker = '/*__MARKET_DATA__*/'
    if template.count(marker) != 1:
        raise ValueError('Market dashboard needs exactly one data placeholder')
    payload = json.dumps(snapshot, allow_nan=False).replace('</', '<\\/')
    return template.replace(marker, f'let DATA = {payload};')


def run(snapshot=None):
    if snapshot is None:
        snapshot = json.loads((ROOT / 'reports/market_review/snapshot.json').read_text(encoding='utf-8'))
    html = build_html(snapshot)
    temporary = ROOT / 'dashboard/index.html.tmp'
    temporary.write_text(html, encoding='utf-8')
    os.replace(temporary, ROOT / 'dashboard/index.html')
    print(f'FuelScope dashboard built: evidence {snapshot["evidence_id"]}', flush=True)


if __name__ == '__main__':
    run()
