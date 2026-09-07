"""
Source 3: National Greenhouse Accounts OData API.
Real endpoint: greenhouseaccounts.climatechange.gov.au/OData/$metadata

A real implementation queries a specific entity set (e.g. .../OData/Emissions)
with OData $filter/$select query params for the transport sector, rather than
just the $metadata document. fetch_live() is overridden here to show that
shape; USE_FIXTURES=true (default) bypasses it entirely.
"""
from __future__ import annotations

from pathlib import Path

import requests

from src.common import config
from src.ingest.base import BaseConnector, ConnectorError


class NgaODataApiConnector(BaseConnector):
    source_name = "nga_odata_api"
    source_url_key = "nga_odata_api"
    fixture_filename = "nga_odata_api.SAMPLE.json"

    def fetch_live(self, out_dir: Path) -> Path:
        base_url = config.SOURCE_URLS[self.source_url_key].replace("/$metadata", "")
        # Real query would target a concrete entity set, e.g.:
        #   f"{base_url}/Emissions?$filter=Sector eq 'Transport'&$format=json"
        query_url = f"{base_url}/Emissions?$filter=Sector eq 'Transport'&$format=json"
        self.logger.info("GET %s", query_url)
        resp = requests.get(query_url, timeout=config.HTTP_TIMEOUT_SECONDS)
        resp.raise_for_status()
        if not resp.content:
            raise ConnectorError("nga_odata_api: empty response body")
        out_path = out_dir / "nga_odata_api.json"
        out_path.write_bytes(resp.content)
        return out_path


if __name__ == "__main__":
    NgaODataApiConnector().run()
