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
