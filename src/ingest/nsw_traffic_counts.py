"""
Source 9: NSW Road Traffic Volume Counts API — hourly permanent counts.
Real endpoint: opendata.transport.nsw.gov.au (requires a free API key,
sent as an Authorization header). Highest-frequency source (hourly),
so this is the primary feed for near-real-time operational anomaly detection.
"""
from __future__ import annotations

from pathlib import Path

import requests

from src.common import config
from src.ingest.base import BaseConnector, ConnectorError


class NswTrafficCountsConnector(BaseConnector):
    source_name = "nsw_traffic_counts"
    source_url_key = "nsw_traffic_counts"
    fixture_filename = "nsw_traffic_counts.SAMPLE.csv"

    def fetch_live(self, out_dir: Path) -> Path:
        if not config.NSW_TRAFFIC_API_KEY:
            raise ConnectorError(
                "nsw_traffic_counts: NSW_TRAFFIC_API_KEY not set — see .env.example"
            )
        url = config.SOURCE_URLS[self.source_url_key]
        headers = {"Authorization": f"apikey {config.NSW_TRAFFIC_API_KEY}"}
        self.logger.info("GET %s", url)
        resp = requests.get(url, headers=headers, timeout=config.HTTP_TIMEOUT_SECONDS)
        resp.raise_for_status()
        out_path = out_dir / "nsw_traffic_counts_hourly_permanent.zip"
        out_path.write_bytes(resp.content)
        return out_path


if __name__ == "__main__":
    NswTrafficCountsConnector().run()
