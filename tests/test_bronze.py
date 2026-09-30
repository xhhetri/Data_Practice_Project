"""
tests/test_bronze.py
---------------------
Tests for src/analysis/bronze.py. Run with: pytest tests/

Structural checks only, not exact values -- like test_clean.py's builder
tests, this runs against whatever data/bronze/ actually contains (real
downloads on a machine that has them, fixtures/ fallback otherwise), so
it must stay meaningful in both cases rather than asserting one of them.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd

from src.analysis import bronze


def test_build_manifest_covers_every_known_source():
    manifest = bronze.build_manifest()
    assert isinstance(manifest, pd.DataFrame)
    assert set(manifest["source"]) == set(bronze.SOURCE_NAMES)
    assert len(manifest) == len(bronze.SOURCE_NAMES)


def test_build_manifest_status_values_are_valid():
    manifest = bronze.build_manifest()
    assert manifest["status"].isin({"real", "sample", "missing"}).all()


def test_build_manifest_resolved_rows_have_path_and_size():
    manifest = bronze.build_manifest()
    resolved = manifest[manifest["status"] != "missing"]
    # every fixture/sample source resolves via clean._locate()'s own
    # fallback chain, so on a fresh checkout with no real data this
    # should still be non-empty (fixtures/ ships in the repo).
    assert len(resolved) > 0
    assert resolved["path"].notna().all()
    assert (resolved["size_bytes"] > 0).all()
    assert resolved["modified_at"].notna().all()


def test_run_writes_manifest_csv(tmp_path, monkeypatch):
    manifest_path = tmp_path / "_manifest.csv"
    monkeypatch.setattr(bronze, "BRONZE_DIR", tmp_path)
    monkeypatch.setattr(bronze, "MANIFEST_PATH", manifest_path)

    result = bronze.run()

    assert manifest_path.exists()
    on_disk = pd.read_csv(manifest_path)
    assert list(on_disk["source"]) == list(result["source"])
