"""
Source 6: Registered Road Vehicles, Australia (motor vehicles by
state/territory, vehicle type, year of manufacture). Real endpoint: a direct
CSV download from data.gov.au.
"""
from __future__ import annotations

from src.ingest.base import BaseConnector


class VehicleRegistrationsConnector(BaseConnector):
    source_name = "vehicle_registrations"
    source_url_key = "vehicle_registrations"
    fixture_filename = "vehicle_registrations.SAMPLE.csv"


if __name__ == "__main__":
    VehicleRegistrationsConnector().run()
