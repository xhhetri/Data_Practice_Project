"""
Source 7: Quarterly Update of Australia's National Greenhouse Gas Inventory
(Tables 4, 4A, 5, 11, 12; Data Tables 1A-1C). Real endpoint: dcceew.gov.au,
direct XLSX download, refreshed quarterly.
"""
from __future__ import annotations

from src.ingest.base import BaseConnector


class QuarterlyGhgUpdateConnector(BaseConnector):
    source_name = "quarterly_ghg_update"
    source_url_key = "quarterly_ghg_update"
    fixture_filename = "quarterly_ghg_update.SAMPLE.csv"


if __name__ == "__main__":
    QuarterlyGhgUpdateConnector().run()
