"""
Source 4: Australian National Greenhouse Accounts Factors 2025 (Tables 8 & 9).
Real endpoint: dcceew.gov.au/.../national-greenhouse-accounts-factors-2025
(direct XLSX download; static for the 2025-26 reporting year).
"""
from __future__ import annotations

from src.ingest.base import BaseConnector


class NgaFactors2025Connector(BaseConnector):
    source_name = "nga_factors_2025"
    source_url_key = "nga_factors_2025"
    fixture_filename = "nga_factors_2025.SAMPLE.csv"


if __name__ == "__main__":
    NgaFactors2025Connector().run()
