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
