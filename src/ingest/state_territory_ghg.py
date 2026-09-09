"""
Source 2: State & Territory GHG Inventories — Energy>Transport activity table.
Real endpoint: dcceew.gov.au/.../state-and-territory-greenhouse-gas-inventories
(downloads activity-table-1990-2024-energy-transport.xlsx).
"""
from __future__ import annotations

from src.ingest.base import BaseConnector


class StateTerritoryGhgConnector(BaseConnector):
    source_name = "state_territory_ghg"
    source_url_key = "state_territory_ghg"
    fixture_filename = "state_territory_ghg.SAMPLE.csv"


if __name__ == "__main__":
    StateTerritoryGhgConnector().run()
