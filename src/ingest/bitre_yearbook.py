"""
Source 5: BITRE Yearbook 2025 — Passengers/Freight/Road chapters, VKT by
mode & vehicle type. Real endpoint: bitre.gov.au/publications/2025/...
(a "Download ZIP" button; a live implementation would download the ZIP and
extract the relevant chapter files before landing them in Bronze).
"""
from __future__ import annotations

from pathlib import Path
import zipfile

import requests

from src.common import config
from src.ingest.base import BaseConnector


class BitreYearbookConnector(BaseConnector):
    source_name = "bitre_yearbook"
    source_url_key = "bitre_yearbook"
    fixture_filename = "bitre_yearbook.SAMPLE.csv"

    def fetch_live(self, out_dir: Path) -> Path:
        url = config.SOURCE_URLS[self.source_url_key]
        self.logger.info("GET %s (zip)", url)
        resp = requests.get(url, timeout=config.HTTP_TIMEOUT_SECONDS)
        resp.raise_for_status()
        zip_path = out_dir / "bitre_yearbook.zip"
        zip_path.write_bytes(resp.content)
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(out_dir)
        return zip_path


if __name__ == "__main__":
    BitreYearbookConnector().run()
