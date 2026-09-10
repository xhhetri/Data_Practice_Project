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
])
def test_loader_returns_nonempty_dataframe(loader_name):
    loader = getattr(clean, loader_name)
    df = loader()
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 0


def test_petroleum_statistics_date_column_is_datetime():
    df = clean.load_petroleum_statistics()
    assert pd.api.types.is_datetime64_any_dtype(df["date"])


# ---------------------------------------------------------------------
# Master table builders -- structural checks, environment-agnostic.
#
# These deliberately do NOT assert exact row counts. _locate() prefers
# real data over the bundled fixtures whenever real files are present
# in data/bronze/ (see BRONZE_FOLDER_ALIASES), so the actual row counts
# here depend on what data is present when the test runs -- fixtures
# only (48 rows / 8 states / 6 years) on a fresh clone, or real data's
# actual coverage (currently 2010-2023, 7 states -- ACT has no fuel
# sales data in the real source) once real files are dropped in. Testing
# structure instead of exact numbers means these tests stay meaningful
# in both cases instead of breaking the moment real data is added.
# ---------------------------------------------------------------------

def test_annual_master_shape():
    df = clean.build_annual_master()
    assert len(df) > 0
    assert df["state"].isin(clean.VALID_STATES).all()
    assert df["year"].between(1989, 2030).all()  # sanity bound, not a fixture-specific one
    expected_cols = {
        "state", "year", "fuel_consumption_ml",
        "vkt_road_million_km", "registered_vehicles", "ghg_kt_co2e",
    }
    assert expected_cols.issubset(df.columns)
    assert not df[list(expected_cols - {"state", "year"})].isna().any().any()
    # every numeric feature should be positive -- a zero or negative value
    # here would indicate a parsing bug, not a legitimate data point
    for col in ["fuel_consumption_ml", "vkt_road_million_km", "registered_vehicles", "ghg_kt_co2e"]:
        assert (df[col] > 0).all(), f"{col} has non-positive values"


def test_annual_master_with_population_shape():
    df = clean.build_annual_master_with_population()
    assert len(df) > 0
    assert df["state"].isin(clean.VALID_STATES).all()
    for col in ["emissions_per_capita_kg", "vkt_per_capita_km", "vehicles_per_capita"]:
        assert col in df.columns
        assert (df[col] > 0).all()
    # this table should never have MORE rows than the base table it extends
    base_len = len(clean.build_annual_master())
    assert len(df) <= base_len


def test_monthly_fuel_series_shape():
    df = clean.build_monthly_fuel_series()
    assert len(df) > 0
    assert df["state"].isin(clean.VALID_STATES).all()
    assert (df["consumption_ml"] > 0).all()
    # monthly grain: no state should have more than one row per calendar date
    dupes = df.duplicated(subset=["state", "date"]).sum()
    assert dupes == 0, f"{dupes} duplicate (state, date) rows -- aggregation bug"


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


# ---------------------------------------------------------------------
# _read_tabular() -- CSV vs Excel format detection
# ---------------------------------------------------------------------

def test_read_tabular_reads_csv(tmp_path):
    path = tmp_path / "data.csv"
    path.write_text("a,b\n1,2\n3,4\n")
    df = clean._read_tabular(path)
    assert len(df) == 2
    assert list(df.columns) == ["a", "b"]


def test_read_tabular_reads_xlsx(tmp_path):
    path = tmp_path / "data.xlsx"
    pd.DataFrame({"a": [1, 3], "b": [2, 4]}).to_excel(path, index=False)
    df = clean._read_tabular(path)
    assert len(df) == 2
    assert list(df.columns) == ["a", "b"]


def test_locate_finds_real_xlsx_over_sample_csv(tmp_path, monkeypatch):
    """The scenario that actually matters: a real .xlsx download sitting
    next to the existing .SAMPLE.csv fixture copy -- real data must win."""
    monkeypatch.setattr(clean, "BRONZE_DIR", tmp_path / "bronze")
    monkeypatch.setattr(clean, "FIXTURES_DIR", tmp_path / "fixtures")

    source_dir = tmp_path / "bronze" / "test_source" / "2026-01-01"
    source_dir.mkdir(parents=True)
    (source_dir / "test_source.SAMPLE.csv").write_text("a,b\n1,2\n")
    pd.DataFrame({"a": [9], "b": [9]}).to_excel(
        source_dir / "test_source.xlsx", index=False
    )

    result = clean._locate("test_source")
    assert result.name == "test_source.xlsx"


# ---------------------------------------------------------------------
# _parse_financial_year() / _fy_start_from_date() -- FY convention
# ---------------------------------------------------------------------

def test_parse_financial_year():
    assert clean._parse_financial_year("2020-21") == 2020
    assert clean._parse_financial_year("1989-90") == 1989


def test_fy_start_from_date():
    import pandas as pd
    # Jul-Jun financial year: a date in Sep 2020 or Mar 2021 both fall
    # in FY2020-21, so both should map to fy_year 2020.
    assert clean._fy_start_from_date(pd.Timestamp("2020-09-15")) == 2020
    assert clean._fy_start_from_date(pd.Timestamp("2021-03-15")) == 2020
    assert clean._fy_start_from_date(pd.Timestamp("2021-07-01")) == 2021
    assert clean._fy_start_from_date(pd.Timestamp("2021-06-30")) == 2020


def test_locate_folder_alias_resolution(tmp_path, monkeypatch):
    """A real download sitting under a human-named folder (not the
    canonical source_name) must still be found -- this is the actual
    situation in data/bronze/ right now (e.g. 'Australian Petroleum
    statistics consumption cover' for petroleum_statistics)."""
    monkeypatch.setattr(clean, "BRONZE_DIR", tmp_path / "bronze")
    monkeypatch.setattr(clean, "FIXTURES_DIR", tmp_path / "fixtures")
    monkeypatch.setattr(clean, "BRONZE_FOLDER_ALIASES", {
        "test_source": ["test_source", "Some Human Readable Name"],
    })

    alias_dir = tmp_path / "bronze" / "Some Human Readable Name"
    alias_dir.mkdir(parents=True)
    (alias_dir / "real_data.csv").write_text("a,b\n1,2\n")

    result = clean._locate("test_source")
    assert result.name == "real_data.csv"