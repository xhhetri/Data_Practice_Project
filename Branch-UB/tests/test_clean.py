"""
tests/test_clean.py
--------------------
Tests for src/analysis/clean.py. Run with: pytest tests/

These run against the real fixture CSVs in fixtures/ (not mocks) --
deliberately, since the fixtures are small, checked into the repo, and
never change, so the expected row counts below are exact and stable.
If someone edits the fixtures, these tests should fail loudly rather
than silently pass on different data.
"""

import pandas as pd
import pytest

from src.analysis import clean


# ---------------------------------------------------------------------
# _standardise_state
# ---------------------------------------------------------------------

def test_standardise_state_uppercases_and_strips():
    df = pd.DataFrame({"state": [" nsw ", "Vic", "QLD"], "value": [1, 2, 3]})
    out = clean._standardise_state(df)
    assert list(out["state"]) == ["NSW", "VIC", "QLD"]


def test_standardise_state_drops_unrecognised_codes():
    df = pd.DataFrame({"state": ["NSW", "XYZ", "VIC"], "value": [1, 2, 3]})
    out = clean._standardise_state(df)
    assert set(out["state"]) == {"NSW", "VIC"}
    assert len(out) == 2


def test_standardise_state_keeps_all_valid_codes():
    df = pd.DataFrame({"state": sorted(clean.VALID_STATES), "value": range(8)})
    out = clean._standardise_state(df)
    assert len(out) == 8


# ---------------------------------------------------------------------
# Individual loaders -- each should return non-empty, correctly typed data
# ---------------------------------------------------------------------

@pytest.mark.parametrize("loader_name", [
    "load_population",
    "load_bitre_yearbook",
    "load_petroleum_statistics",
    "load_quarterly_ghg_update",
    "load_state_territory_ghg",
    "load_vehicle_registrations",
    "load_nga_factors",
    "load_nga_odata_api",
    "load_nsw_traffic_counts",
])
def test_loader_returns_nonempty_dataframe(loader_name):
    loader = getattr(clean, loader_name)
    df = loader()
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 0


def test_petroleum_statistics_date_column_is_datetime():
    df = clean.load_petroleum_statistics()
    assert pd.api.types.is_datetime64_any_dtype(df["date"])


def test_nsw_traffic_counts_has_hour_and_day_of_week():
    df = clean.load_nsw_traffic_counts()
    assert "hour" in df.columns
    assert df["hour"].between(0, 23).all()
    assert "day_of_week" in df.columns


# ---------------------------------------------------------------------
# Master table builders -- exact row counts, given the fixed fixtures
# ---------------------------------------------------------------------

def test_annual_master_shape():
    df = clean.build_annual_master()
    assert len(df) == 48  # 8 states x 6 years (2020-2025)
    assert df["state"].nunique() == 8
    assert df["year"].nunique() == 6
    expected_cols = {
        "state", "year", "fuel_consumption_ml",
        "vkt_road_million_km", "registered_vehicles", "ghg_kt_co2e",
    }
    assert expected_cols.issubset(df.columns)
    assert not df[list(expected_cols - {"state", "year"})].isna().any().any()


def test_annual_master_with_population_shape():
    df = clean.build_annual_master_with_population()
    assert len(df) == 16  # 8 states x 2 years (2024-2025 -- population's range)
    assert set(df["year"].unique()) == {2024, 2025}
    for col in ["emissions_per_capita_kg", "vkt_per_capita_km", "vehicles_per_capita"]:
        assert col in df.columns
        assert (df[col] > 0).all()


def test_monthly_fuel_series_shape():
    df = clean.build_monthly_fuel_series()
    # 8 states x 6 years x 12 months = 576 source rows, all one product
    # (Automotive Diesel Oil), so after grouping by (state, date) the
    # row count should match the source row count exactly.
    assert len(df) == 576
    assert df["state"].nunique() == 8


def test_nsw_traffic_hourly_only_contains_nsw():
    df = clean.build_nsw_traffic_hourly()
    # Source file only has NSW stations, but assert it explicitly --
    # a regression here would mean the wrong fixture got loaded.
    assert "station_id" in df.columns
    assert df["station_id"].str.startswith("NSW-").all()


# ---------------------------------------------------------------------
# _locate() -- source resolution order (real data > sample > fixture)
# ---------------------------------------------------------------------

def test_locate_prefers_non_sample_over_sample(tmp_path, monkeypatch):
    monkeypatch.setattr(clean, "BRONZE_DIR", tmp_path / "bronze")
    monkeypatch.setattr(clean, "FIXTURES_DIR", tmp_path / "fixtures")

    source_dir = tmp_path / "bronze" / "test_source" / "2026-01-01"
    source_dir.mkdir(parents=True)
    (source_dir / "test_source.SAMPLE.csv").write_text("a,b\n1,2\n")
    (source_dir / "test_source.csv").write_text("a,b\n3,4\n")

    result = clean._locate("test_source")
    assert result.name == "test_source.csv"  # non-SAMPLE wins


def test_locate_falls_back_to_sample_when_no_real_file(tmp_path, monkeypatch):
    monkeypatch.setattr(clean, "BRONZE_DIR", tmp_path / "bronze")
    monkeypatch.setattr(clean, "FIXTURES_DIR", tmp_path / "fixtures")

    source_dir = tmp_path / "bronze" / "test_source" / "2026-01-01"
    source_dir.mkdir(parents=True)
    (source_dir / "test_source.SAMPLE.csv").write_text("a,b\n1,2\n")

    result = clean._locate("test_source")
    assert result.name == "test_source.SAMPLE.csv"


def test_locate_falls_back_to_fixtures_dir_when_bronze_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(clean, "BRONZE_DIR", tmp_path / "bronze")  # doesn't exist
    monkeypatch.setattr(clean, "FIXTURES_DIR", tmp_path / "fixtures")

    (tmp_path / "fixtures").mkdir(parents=True)
    (tmp_path / "fixtures" / "test_source.SAMPLE.csv").write_text("a,b\n1,2\n")

    result = clean._locate("test_source")
    assert result.name == "test_source.SAMPLE.csv"


def test_locate_raises_when_nothing_found(tmp_path, monkeypatch):
    monkeypatch.setattr(clean, "BRONZE_DIR", tmp_path / "bronze")
    monkeypatch.setattr(clean, "FIXTURES_DIR", tmp_path / "fixtures")

    with pytest.raises(FileNotFoundError):
        clean._locate("nonexistent_source")
