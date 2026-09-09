"""
Source 8: ABS Population, States and Territories (Estimated Resident
Population). Real endpoint: abs.gov.au, direct XLSX download, refreshed
quarterly.
"""
from __future__ import annotations

from src.ingest.base import BaseConnector


class AbsPopulationConnector(BaseConnector):
    source_name = "abs_population"
    source_url_key = "abs_population"
    fixture_filename = "abs_population.SAMPLE.csv"


if __name__ == "__main__":
    AbsPopulationConnector().run()
