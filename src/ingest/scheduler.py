"""
Lightweight local scheduler standing in for Airflow/Azure Data Factory in
this dev environment. Maps each source to its real-world update cadence.
For a production deployment, translate this mapping directly into an Airflow
DAG (one task per connector, `schedule_interval` per the cadence below).

Run: python -m src.ingest.scheduler
"""
from __future__ import annotations

import time

import schedule

from src.common.logging_setup import get_logger
from src.ingest.abs_population import AbsPopulationConnector
from src.ingest.bitre_yearbook import BitreYearbookConnector
from src.ingest.nga_factors_2025 import NgaFactors2025Connector
from src.ingest.nga_odata_api import NgaODataApiConnector
from src.ingest.nsw_traffic_counts import NswTrafficCountsConnector
from src.ingest.petroleum_statistics import PetroleumStatisticsConnector
from src.ingest.quarterly_ghg_update import QuarterlyGhgUpdateConnector
from src.ingest.state_territory_ghg import StateTerritoryGhgConnector
from src.ingest.vehicle_registrations import VehicleRegistrationsConnector

logger = get_logger("ingest.scheduler")

# cadence documented per the original dataset catalogue
CADENCE = {
    PetroleumStatisticsConnector: "monthly",
    StateTerritoryGhgConnector: "annual",
    NgaODataApiConnector: "daily",       # polled; underlying data changes ad hoc
    NgaFactors2025Connector: "annual",    # static per reporting year
    BitreYearbookConnector: "annual",
    VehicleRegistrationsConnector: "annual",
    QuarterlyGhgUpdateConnector: "quarterly",
    AbsPopulationConnector: "quarterly",
    NswTrafficCountsConnector: "hourly",
}


def _run_connector(connector_cls) -> None:
    try:
        connector_cls().run()
    except Exception as exc:  # noqa: BLE001
        logger.error("%s scheduled run failed: %s", connector_cls.__name__, exc)


def build_schedule() -> None:
    for connector_cls, cadence in CADENCE.items():
        if cadence == "hourly":
            schedule.every().hour.do(_run_connector, connector_cls)
        elif cadence == "daily":
            schedule.every().day.at("02:00").do(_run_connector, connector_cls)
        elif cadence == "monthly":
            schedule.every(30).days.do(_run_connector, connector_cls)
        elif cadence == "quarterly":
            schedule.every(90).days.do(_run_connector, connector_cls)
        elif cadence == "annual":
            schedule.every(365).days.do(_run_connector, connector_cls)
        logger.info("Scheduled %s @ %s", connector_cls.__name__, cadence)


def main() -> None:
    build_schedule()
    logger.info("Scheduler running. Ctrl+C to stop.")
    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
