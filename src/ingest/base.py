"""
BaseConnector: shared retry/backoff/logging/fixture-switching behaviour for
every source connector. Each concrete connector only needs to declare a
`source_name`, the `fixture_filename` to fall back to, and either a
`fetch_live()` override (to hit the real URL) or rely on the default
`requests.get` behaviour against `config.SOURCE_URLS[source_key]`.

Every connector writes its raw output, unmodified, into
    data/bronze/<source_name>/<ingest_date>/<original_filename>
which is the immutable Bronze landing zone.

Retry/backoff is implemented with stdlib only (no `tenacity` dependency) so
this module has zero third-party requirements beyond `requests`.
"""
from __future__ import annotations

import abc
import functools
import shutil
import time
from datetime import date
from pathlib import Path

import requests

from src.common import config
from src.common.logging_setup import get_logger


class ConnectorError(RuntimeError):
    """Raised when a connector cannot obtain data from either live source or fixture."""


def retry_with_backoff(max_attempts: int, backoff_seconds: float):
    """Simple exponential-backoff retry decorator (stdlib only)."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exc: Exception | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except (requests.RequestException, ConnectorError) as exc:
                    last_exc = exc
                    if attempt == max_attempts:
                        break
                    wait = backoff_seconds * (2 ** (attempt - 1))
                    logger = get_logger("ingest.retry")
                    logger.warning(
                        "Attempt %d/%d failed (%s); retrying in %.1fs",
                        attempt, max_attempts, exc, wait,
                    )
                    time.sleep(wait)
            assert last_exc is not None
            raise last_exc
        return wrapper
    return decorator


class BaseConnector(abc.ABC):
    #: short, unique key used for logging and the Bronze subdirectory
    source_name: str = "base"
    #: key into config.SOURCE_URLS for the live endpoint (optional)
    source_url_key: str | None = None
    #: filename (under FIXTURES_DIR) used when config.USE_FIXTURES is True
    fixture_filename: str | None = None

    def __init__(self) -> None:
        self.logger = get_logger(f"ingest.{self.source_name}")

    # ------------------------------------------------------------------ #
    # Public entrypoint
    # ------------------------------------------------------------------ #
    def run(self) -> Path:
        """Fetch (live or fixture) and land the raw file in Bronze. Returns the output path."""
        out_dir = config.BRONZE_DIR / self.source_name / date.today().isoformat()
        out_dir.mkdir(parents=True, exist_ok=True)

        if config.USE_FIXTURES:
            out_path = self._land_fixture(out_dir)
            self.logger.info("Loaded FIXTURE data -> %s", out_path)
        else:
            out_path = self._land_live(out_dir)
            self.logger.info("Loaded LIVE data -> %s", out_path)
        return out_path

    # ------------------------------------------------------------------ #
    # Fixture path (default dev/sandbox mode)
    # ------------------------------------------------------------------ #
    def _land_fixture(self, out_dir: Path) -> Path:
        if not self.fixture_filename:
            raise ConnectorError(f"{self.source_name}: no fixture_filename configured")
        src = config.FIXTURES_DIR / self.fixture_filename
        if not src.exists():
            raise ConnectorError(
                f"{self.source_name}: fixture not found at {src}. "
                "Run scripts/generate_fixtures.py first."
            )
        dst = out_dir / self.fixture_filename
        shutil.copyfile(src, dst)
        return dst

    # ------------------------------------------------------------------ #
    # Live path — retried with exponential backoff
    # ------------------------------------------------------------------ #
    def _land_live(self, out_dir: Path) -> Path:
        retrying_fetch = retry_with_backoff(
            max_attempts=config.HTTP_MAX_RETRIES,
            backoff_seconds=config.HTTP_RETRY_BACKOFF_SECONDS,
        )(self.fetch_live)
        return retrying_fetch(out_dir)

    def fetch_live(self, out_dir: Path) -> Path:
        """Default live fetch: GET the configured URL and save the raw response body.

        Override in a subclass if a source needs bespoke handling (e.g. the
        OData API, or a ZIP that must be extracted).
        """
        if not self.source_url_key:
            raise ConnectorError(f"{self.source_name}: no source_url_key configured")
        url = config.SOURCE_URLS[self.source_url_key]
        self.logger.info("GET %s", url)
        resp = requests.get(url, timeout=config.HTTP_TIMEOUT_SECONDS)
        resp.raise_for_status()
        filename = url.rstrip("/").split("/")[-1] or f"{self.source_name}.raw"
        out_path = out_dir / filename
        out_path.write_bytes(resp.content)
        return out_path

