"""
Orchestrates all 9 ingestion connectors. In production this logic maps onto
Airflow tasks/DAG schedule (monthly / quarterly / hourly cadences per source);
here it's a simple sequential runner suitable for local dev and for wiring
into `schedule` (see src/ingest/scheduler.py) for lightweight cron-style runs.
"""
from __future__ import annotations

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

logger = get_logger("ingest.run_all")

ALL_CONNECTORS = [
    PetroleumStatisticsConnector,
    StateTerritoryGhgConnector,
    NgaODataApiConnector,
    NgaFactors2025Connector,
    BitreYearbookConnector,
    VehicleRegistrationsConnector,
    QuarterlyGhgUpdateConnector,
    AbsPopulationConnector,
    NswTrafficCountsConnector,
]


def run_all() -> dict[str, str]:
    results: dict[str, str] = {}
    failures: list[str] = []
    for connector_cls in ALL_CONNECTORS:
        connector = connector_cls()
        try:
            out_path = connector.run()
            results[connector.source_name] = str(out_path)
        except Exception as exc:  # noqa: BLE001 - we want to continue past a single failure
            logger.error("Connector %s failed: %s", connector_cls.__name__, exc)
            failures.append(connector_cls.__name__)

    logger.info("Ingestion complete: %d/%d sources landed", len(results), len(ALL_CONNECTORS))
    if failures:
        logger.warning("Failed connectors: %s", ", ".join(failures))
    return results


if __name__ == "__main__":
    run_all()
