"""
bronze.py
---------
The Bronze tier: lands and validates raw source files as-is. No cleaning,
no parsing of business columns -- that's Silver's job (silver.py). This
module only answers "is the raw data present, and which file wins?" and
writes that answer to disk as a manifest, so a fresh checkout can be
audited without re-running the whole pipeline.

Reuses clean.py's `_locate()` (source-resolution order: real file >
SAMPLE file > fixtures/ fallback) rather than duplicating it -- that
logic is unit-tested in tests/test_clean.py and must stay the single
source of truth for "which file did we actually load".
"""

from __future__ import annotations

import logging
import hashlib
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src.analysis.clean import BRONZE_DIR, BRONZE_FOLDER_ALIASES, REPO_ROOT, _locate
from src.catalog import SOURCES

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

MANIFEST_PATH = BRONZE_DIR / "_manifest.csv"

# The canonical source names Silver's loaders resolve via _locate(). Kept
# here (not re-derived from BRONZE_FOLDER_ALIASES.keys()) so a source that
# doesn't need an alias -- folder name == source name -- still gets
# catalogued.
SOURCE_NAMES = [
    "abs_population",
    "bitre_yearbook",
    "petroleum_statistics",
    "quarterly_ghg_update",
    "state_territory_ghg",
    "nga_factors_2025",
]


def build_manifest() -> pd.DataFrame:
    """Resolves every known source against data/bronze/ and records what
    was found: which file, whether it's real data or a bundled fixture,
    size, and last-modified time. A row with status='missing' means
    Silver will fall back to fixtures/ (or fail) when it runs."""
    rows = []
    for name in SOURCE_NAMES:
        try:
            path = _locate(name)
        except FileNotFoundError:
            rows.append({
                "source": name,
                "status": "missing",
                "path": None,
                "is_sample": None,
                "size_bytes": None,
                "modified_at": None,
            })
            log.warning("Bronze: no file found for '%s'", name)
            continue

        is_fixture = REPO_ROOT / "fixtures" in path.parents
        is_sample = "SAMPLE" in path.name or is_fixture
        stat = path.stat()
        rows.append({
            "source": name,
            "status": "sample" if is_sample else "real",
            "path": str(path.relative_to(REPO_ROOT)),
            "is_sample": is_sample,
            "size_bytes": stat.st_size,
            "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "url": SOURCES[name][0],
            "boundary": SOURCES[name][1],
            "retrieval_date": "Not recorded in original download; file modification time is not retrieval evidence",
        })
    return pd.DataFrame(rows)


def run() -> pd.DataFrame:
    """Builds the manifest and writes it to data/bronze/_manifest.csv.
    Called first by clean.run() -- Silver/Gold don't read the manifest
    back (they call _locate() themselves), it exists purely as a
    reproducibility artefact: proof of what raw data a given pipeline
    run actually saw."""
    manifest = build_manifest()
    BRONZE_DIR.mkdir(parents=True, exist_ok=True)
    manifest.to_csv(MANIFEST_PATH, index=False)
    real = (manifest["status"] == "real").sum()
    sample = (manifest["status"] == "sample").sum()
    missing = (manifest["status"] == "missing").sum()
    log.info(
        "Bronze manifest: %d real, %d sample/fixture, %d missing -> %s",
        real, sample, missing, MANIFEST_PATH,
    )
    return manifest


if __name__ == "__main__":
    run()
