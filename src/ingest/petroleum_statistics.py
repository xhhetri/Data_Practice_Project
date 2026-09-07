"""
Source 1: Australian Petroleum Statistics (monthly petroleum consumption).
Real endpoint: energy.gov.au/energy-data/australian-petroleum-statistics
(published monthly on data.gov.au; download link varies by release, so a
live implementation would first resolve the current month's resource URL
from the data.gov.au dataset API before downloading it).
"""
from __future__ import annotations

from src.ingest.base import BaseConnector


class PetroleumStatisticsConnector(BaseConnector):
    source_name = "petroleum_statistics"
    source_url_key = "petroleum_statistics"
    fixture_filename = "petroleum_statistics.SAMPLE.csv"


if __name__ == "__main__":
    PetroleumStatisticsConnector().run()
