
# Changelog

## [Unreleased] - 2026-09-09

### Changed — Architecture simplified: Bronze/Silver/Gold → single clean/EDA/model pipeline

**Previous state:** A layered "medallion" architecture (Bronze → Silver → Gold),
with per-source ingestion connector classes (`src/ingest/*.py`), a shared
`BaseConnector` with retry/backoff, an orchestration scheduler, a Silver
transform layer writing Parquet, and a Gold star-schema warehouse
(SQLite/DuckDB), feeding a separate ML layer and Streamlit dashboard.

**Current state:** A single `src/analysis/` module with three files —
`clean.py` (load + standardise + merge the 9 sources into analysis-ready
tables), `eda.py` (distributions, trends, correlations, all saved as
figures), and `model.py` (regression + time-series forecast, with
evaluation metrics). Run end-to-end with `python run_pipeline.py`.

**Justification:**

1. The connector/orchestration code for the previous architecture was lost
   in commit `d2942ca` (ingestion connectors, Silver parquet outputs, and
   the Gold warehouse were deleted; only `scheduler.py` remained). Rather
   than rebuilding equivalent complexity from scratch under time pressure,
   the team re-scoped the architecture to match what a 4-person student
   project can realistically build, test, and maintain for the remainder
   of the semester.
2. The assessment rubric requires evidence of data acquisition, cleaning,
   EDA, and predictive modelling — it does not require a layered warehouse
   architecture. The simplified pipeline satisfies every required rubric
   item with less surface area for things to break.
3. A single, flat, well-documented module is easier for four people to
   review and extend than five architectural layers, given the team's
   size and the remaining timeline.

**What was removed:** `src/ingest/` connector classes, `BaseConnector`,
the Silver Parquet layer, the Gold SQLite/DuckDB warehouse, the
FastAPI scoring endpoint, and the Streamlit dashboard scaffold. None of
these had been demonstrated working end-to-end in this repo before removal.

**What replaced it:** `src/analysis/clean.py`, `src/analysis/eda.py`,
`src/analysis/model.py`, orchestrated by `run_pipeline.py`. Verified
to run end-to-end from a clean checkout, producing:

- `data/processed/` — cleaned, merged CSVs
- `reports/figures/` — 6 EDA/forecast figures
- `reports/model_results/metrics.json` — cross-validated regression
  metrics + monthly fuel forecast metrics, with a trained model `.pkl`

### Removed (commit `d2942ca`, prior to this entry — documented retroactively)

- All `src/ingest/*.py` connector modules
- `data/silver/*.parquet`
- `data/gold/warehouse.sqlite`

This removal was not documented in a changelog at the time it happened.
This entry exists to bring the project change record up to date and
establish going-forward practice: every architecture/scope change from
here on gets an entry here before the next assessment is submitted.

## [Unreleased] - 2026-09-09 (later same day)

### Removed — legacy `src/ingest/` layer and its Silver/Gold outputs, permanently

After the above decision, `src/ingest/*.py` and the Silver/Gold artefacts
were briefly restored via `git revert` while the team confirmed the
decision. On inspection, the restored code turned out to be non-functional:
every connector imports `src.common.config` and
`src.common.logging_setup`, and **`src/common/` does not exist in this
repository's history on any branch** — it was never committed. The
Silver `.parquet` files and `data/gold/warehouse.sqlite` that *were*
committed are valid, populated data (verified: correct schema, correct
row counts against the fixtures) — but there is no working code in this
repo that can regenerate them.

**Decision:** remove `src/ingest/`, `data/silver/`, and `data/gold/`
permanently rather than reconstruct `src/common` from scratch. Rebuilding
it would only resurrect a pipeline that produces output nothing else in
the repo consumes — `src/analysis/` already covers acquisition (via
`data/bronze/`), cleaning, EDA, and modelling end-to-end. Keeping
non-runnable code in the repo actively works against the assessment's
"reproducibility artefacts" and "execution instructions" requirements:
anyone following the setup instructions and running the legacy path
would hit an `ImportError` on the first import.

**Verified after removal:** `python run_pipeline.py` still runs
end-to-end with no errors — `src/analysis/` never depended on
`src/ingest/`, `data/silver/`, or `data/gold/` in the first place.

From this point on, `src/analysis/` (via `run_pipeline.py`) is the
single, sole data pipeline for this project.

## [Unreleased] - 2026-09-09 (hardening pass)

### Added

- Loaders for the two previously-unused sources: `load_nga_odata_api()`
  and `load_nsw_traffic_counts()` in `clean.py`. All 9 sources now have
  a loader (source 7, quarterly GHG update, is loaded/tested but not yet
  consumed by a table — noted as a next step in README).
- `src/analysis/validate.py` — two data-quality checks that were
  previously just "future work": an emission-factor cross-check
  (fuel × published factor vs. reported inventory) and a dual-source GHG
  consistency check (published CSV table vs. the same data via the
  OData API).
- NSW hourly traffic EDA figure and a 24-hour-seasonality forecast model
  (`forecast_nsw_traffic()`), using the same method as the existing fuel
  forecast for consistency.
- `tests/test_clean.py` — 22 tests: state-code standardisation, every
  loader, exact row counts for every master table, and `_locate()`'s
  fallback ordering (tested in isolation via `tmp_path`, not against the
  real `data/bronze/`).
- `.github/workflows/ci.yml` — runs the test suite and a full pipeline
  smoke test on every push/PR to `main`, uploads generated outputs as a
  build artifact.
- `docs/architecture/architecture_v2.png` and
  `docs/workflow/workflow_v2.png`, generated by
  `scripts/generate_diagrams.py`, matching the current pipeline exactly.

### Changed

- `requirements.txt` trimmed from 24 packages to the 6 actually imported
  anywhere in `src/analysis/`, `run_pipeline.py`, or `tests/` (pandas,
  numpy, matplotlib, scikit-learn, statsmodels, pytest) — verified by
  grepping every import statement against the file. `openpyxl` and
  `requests` kept as commented-out "anticipated" entries for when real
  `.xlsx` sources and a download script are added.
- `run_pipeline.py` now runs 4 stages (clean → EDA → model → validate),
  was 3.

### Verified

- Full pipeline re-run end-to-end after every change in this pass
  (`python run_pipeline.py`, exit 0, all expected output files present).
- All 22 tests pass (`pytest tests/`).

## [Unreleased] - 2026-09-10 (real data integration)

### Changed — clean.py rewritten to parse real government files, not just fixtures

Every loader that has a real file available (7 of 9 sources) now branches
on the actual file's structure instead of assuming the fixture's flat,
pre-cleaned shape. Real government spreadsheets are genuinely different
from the fixtures in ways that needed real code changes, not just format
detection:

- **Folder resolution**: real downloads sit in human-named folders
  (`"Australian Petroleum statistics consumption cover"`, not
  `petroleum_statistics`), with no dated subfolder. Added
  `BRONZE_FOLDER_ALIASES` and rewrote `_locate()` to search every known
  alias, both directly in the folder and in any dated subfolder within
  it.
- **Financial year alignment**: state emissions (`state_territory_ghg`)
  and VKT (`bitre_yearbook`) are natively financial-year data; petroleum
  sales and population are calendar-dated. Added `_fy_start_from_date()`
  and `_parse_financial_year()` so every source aggregates to the same
  FY convention before joining — previously (see bug below) these were
  silently misaligned.
- **Wide-to-long reshaping**: petroleum sales (`Sales by state and territory` sheet), BITRE VKT (`Table 4.3`), and population (`Data1`
  sheet, ABS's standard wide export) are all wide-format in the real
  files (states or sex/state combinations as columns) and needed melting
  to the long shape the rest of the pipeline expects.
- **Multi-sheet, multi-row-header parsing**: `state_territory_ghg` is
  one sheet per state with a merged-cell IPCC category hierarchy;
  `nga_factors_2025`'s Table 9 has a 3-row header with a
  forward-filled "Transport type" column. Both needed explicit
  `skiprows`/`header=None` parsing rather than a direct `read_excel`.
- **Real emission factors are two-step, not a single lookup**: Table 9
  gives Energy Content (GJ per unit of fuel) and a separate Combined
  Scope 1 factor (kg CO2-e/GJ) — `load_nga_factors()` now computes
  `factor_kg_co2e_per_l = energy_content * combined_factor / 1000`
  instead of reading a single pre-computed column, which only existed in
  the fixture's simplified shape.

### Fixed — FY-alignment bug in validate.py

`validate_emission_factors()` was grouping fuel consumption by calendar
year while `state_territory_ghg`'s `year` is a financial-year start —
misaligning up to ~6 months of transactions per state-year before this
fix. Now groups by fuel's `fy_year` (computed the same way as every
other source) before comparing. Same class of bug as the earlier
`-N:-N+test_len` slicing issue in `model.py` — an unstated unit/convention
mismatch between two pieces of code that individually looked correct.

### Fixed — three "_caveat" fields that would have been actively false

`model.py`'s three result caveats unconditionally said "synthetic
fixture data," left over from before real data was loaded. On a real-data
run this claim is simply wrong. Replaced with `_data_source_caveat()`,
which points to that run's actual log output instead of asserting either
case — correct regardless of which data was loaded. Same fix applied to
a matching false claim in `eda.py`'s correlation heatmap docstring/title.

### Findings from real data — significant enough to change how results are described

- **State-level emissions cover the whole transport sector** (road +
  rail + domestic aviation + shipping) — the published Emission Data
  Tables don't break this down further by mode at the state level. Every
  place that used to say "road transport emissions" now says
  "transport-sector emissions."
- **ACT has no state-level entry in the petroleum sales source** —
  confirmed against the file's own `State` column. `annual_master` covers
  7 states, not 8.
- **Vehicle registrations is a fleet-by-manufacture-year snapshot**, not
  an annual registrations time series (filename contains `yom`).
  `build_annual_master()` now explicitly broadcasts each state's current
  total as a constant across all years, with a runtime warning, rather
  than silently treating manufacture year as if it were registration
  year.
- **The activity table originally downloaded for source 2 was the wrong
  file** — it's the national fuel-consumption Activity Table (PJ by
  vehicle category, no state breakdown), not the state-level Emission
  Data Tables. The correct file was located and re-downloaded (see
  `data/bronze/State & Territory Inventories 2024 - Emission Data Tables/`); the original activity table remains in the repo but is not
  currently used by any loader.

### Verified — real numbers sanity-checked against independent published figures

- ACT transport-sector emissions ~1,080–1,130 kt CO2-e (2019–2023) —
  same order of magnitude as ACT's total reported emissions from an
  independent source (~1.1–1.4 Mt across all sectors), consistent with
  transport being roughly 60% of ACT's total per that same source.
- NSW VKT ~77.5 billion km (2024-25) — consistent with NSW's share of
  the ~264 billion km national total reported by BITRE.
- Real-vs-fixture regression comparison: CV R² went from **-0.29**
  (synthetic, expected for independently-random data) to **0.995**
  (real, expected for accounting-identity-derived data) — the
  theoretically-predicted direction in both cases, which is stronger
  evidence the pipeline is correct than either number alone.
- Full pipeline (`python run_pipeline.py`) and full test suite (28
  tests, `pytest tests/`) both verified passing against the real-data
  environment, not just fixtures, before this entry was written.

### Test suite changed — structural checks instead of hardcoded fixture counts

`test_annual_master_shape()` and related tests previously asserted exact
numbers (48 rows, 8 states, 6 years) that were only ever true for the
fixture-only case. Since `_locate()` now prefers real data whenever
present, these numbers are environment-dependent by design. Rewrote
these tests to check structure (row count > 0, valid state codes, no
nulls, positive values) instead — meaningful in both the fixture-only
and real-data cases, rather than passing on a fresh clone and failing
the moment real data is added. Added dedicated tests for
`_parse_financial_year()`, `_fy_start_from_date()`, and folder-alias
resolution. 28 tests total, up from 22.

## [Unreleased] - 2026-09-10 (scope decisions)

### Changed — project renamed from "Road Transport Emissions" to "Transport Emissions"

**Previous state:** Project title, README, chart titles, and docstrings
described the target variable as "road transport emissions."

**Current state:** Renamed to "Transport Emissions (Australia)"
throughout — title, README, `scripts/generate_diagrams.py`'s diagram
title, and relevant docstrings/comments in `validate.py` and `clean.py`.

**Justification:** confirmed directly against the real government data
(see the "real data integration" entry above) that the published
state-level Emission Data Tables only break down to whole transport
sector — road + rail + domestic aviation + shipping combined. There is
no further mode split at the state level in this authoritative source.
Continuing to call the project's output "road transport emissions"
would overclaim precision the underlying data doesn't support. The
rename costs nothing scientifically and is the more defensible framing
against the actual source.

Note: predictor variables that genuinely are road-specific (fuel sales,
VKT, vehicle registrations) keep language describing them as road-fuel
or road-vehicle inputs where that's accurate — the rename applies to the
project's overall scope and its target variable, not to inputs that
really are road-specific.

### Removed — National GHG Accounts OData API and NSW Traffic Volume Counts sources

**Previous state:** Both sources had loaders (`load_nga_odata_api()`,
`load_nsw_traffic_counts()`), fixture data, a validation check
(`validate_ghg_cross_source()`), an EDA figure, and a forecast model
(`forecast_nsw_traffic()`) — but neither ever had a real data pull wired
in; both ran on synthetic fixtures throughout the project.

**Current state:** Both removed entirely — loaders, fixture files
(`fixtures/nga_odata_api.SAMPLE.json`, `fixtures/nsw_traffic_counts.SAMPLE.csv`),
the cross-source validation check, the NSW traffic EDA figure, the NSW
traffic forecast model, and their entries in `BRONZE_FOLDER_ALIASES`.
Corresponding tests removed from `tests/test_clean.py` (28 → 24 tests).
Architecture diagram regenerated as v3 to reflect 7 sources instead of 9.

**Justification:** with real data now loaded for the other 7 sources,
team time is better spent deepening and reporting on those than
maintaining two sources that were never going to have real data before
submission. Keeping them in as documented "future work" was considered
and rejected — an honest accounting of remaining scope is better served
by removing incomplete features cleanly than by listing them
indefinitely as pending.

### Verified

- Full pipeline (`python run_pipeline.py`) and full test suite (24
  tests, `pytest tests/`) both pass after both changes.
- Confirmed no orphaned references: grepped for "road transport",
  "nga_odata", and "nsw_traffic" across `.py`/`.md` files after the
  changes; remaining "road" mentions are accurate descriptions of
  road-specific inputs (fuel, VKT), not the project's overall scope.

## [Unreleased] - 2026-09-10 (all-states forecast)

### Fixed — fuel forecast and its EDA chart only covered NSW, despite having all 7 states' data

`model.py: run()` called `forecast_fuel_consumption("NSW")` once,
hardcoded to one state, even though `monthly_fuel_series.csv` has real
data for all 7 states in scope. Same issue in
`eda.py: plot_monthly_fuel_series()`, which only plotted NSW by default.
This was a scope choice made when the function was first written (one
example state to prove the method worked), not a data limitation --
worth being clear about, since the data was never the constraint.

**Changed:**

- `model.py: run()` now loops over every state present in
  `monthly_fuel_series.csv` and forecasts each one. Results land in
  `metrics.json` under `fuel_forecast_<STATE>` per state; each gets its
  own chart, `reports/figures/06_forecast_<STATE>.png`.
- `eda.py: plot_monthly_fuel_series()` rewritten from a single-state
  line chart to a 7-panel small-multiples grid, one panel per state,
  independent y-axis scales per panel (NT and TAS's volumes are roughly
  15x smaller than NSW/VIC's -- a shared scale would flatten them to an
  invisible line).

**Verified:** all 7 states forecast successfully, MAPE ranging 2.7%
(WA) to 12.9% (NT, the smallest and most volatile state by volume) --
sensible variation, not a bug. Every state's monthly chart shows the
same COVID-era dip around early 2020, which is exactly the kind of
cross-state consistency that's reassuring to see in genuinely real data.
