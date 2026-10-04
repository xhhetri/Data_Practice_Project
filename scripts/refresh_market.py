"""Explicitly refresh public feeds; preserve validated caches on failure."""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path
from urllib.parse import urljoin, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src import market_review as market


def discover_download(key, previous):
    if key == 'stocks':
        return market.SOURCES[key]['download_url']
    page = market.download_bytes(market.SOURCES[key]['url']).decode('utf-8', errors='replace')
    links = re.findall(r'href=["\']([^"\']+\.xlsx(?:\?[^"\']*)?)["\']', page, re.I)
    pattern = r'AIP_TGP_Data_' if key == 'prices' else r'petroleum.statistics.*data.extract'
    candidates = [urljoin(market.SOURCES[key]['url'], link) for link in links if re.search(pattern, link, re.I)]
    if not candidates:
        raise ValueError('No current workbook link found on the official publication page')
    url = candidates[0]
    parsed = urlparse(url)
    if parsed.scheme != 'https' or parsed.hostname not in {'aip.com.au', 'www.aip.com.au', 'energy.gov.au', 'www.energy.gov.au'}:
        raise ValueError('The workbook link is outside the approved official source domains')
    return url


def run():
    manifest = market.source_manifest()
    parsers = {'prices': market.parse_prices, 'stocks': market.parse_stocks, 'sales': market.parse_petroleum}
    for key, details in market.SOURCES.items():
        previous = manifest.get(key, {})
        try:
            url = discover_download(key, previous)
            result = market.update_cached_source(url, market.RAW / details['file'], parsers[key])
        except Exception as error:
            result = {'status': 'failed', 'changed': False, 'checked_at': market.now_iso(), 'message': str(error)[:180]}
            url = previous.get('download_url', details['download_url'])
        manifest[key] = {**details, **previous, **result}
        if result['status'] != 'failed':
            manifest[key]['download_url'] = url
            manifest[key].pop('message', None)
        print(f'{key}: {result["status"]}', flush=True)
    market.MANIFEST.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    snapshot = market.build_snapshot()
    from scripts.build_market_dashboard import run as build_dashboard
    build_dashboard(snapshot)
    return {'evidence_id': snapshot['evidence_id'], 'feeds': {key: value['status'] for key, value in manifest.items()},
            'updated': any(value.get('changed') for value in manifest.values()), 'completed_at': market.now_iso()}


if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
