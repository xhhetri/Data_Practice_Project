# Transport briefing tool implementation plan

**Goal:** Deliver a reproducible analyst workflow that produces a cited state emissions briefing, with honest forecasting experiments and Assessment 3 preparation material.

**Spec:** `reports/project_audit_2026-10-03.md`, accepted by the user's instruction to continue.

**Architecture:** Retain the Python data layers, SQLite, FastAPI, Streamlit and standalone dashboard. Share briefing calculations and export content between the two interfaces. Bind all generated results to a hashed source manifest and pipeline run.

**Execution:** Inline implementation with a final independent review. Keep changes in this checkout for the user to review; no publishing, pushing or fabricated research evidence.

## Constraints

- Government transport inventories remain distinct from petrol plus total diesel sales.
- Vehicle stock comes from historical BITRE Table 4.6b; its published calendar-year label is associated with the financial year beginning in that year as an explicitly documented approximation.
- All forecast evaluation uses training data earlier than the evaluated month. Hold out the final six months for an untouched evaluation after model selection.
- Select seasonal naive or Holt-Winters using earlier rolling origins. Operational forecasts refit on all available data.
- Intervals are empirical absolute-error quantiles by horizon; report actual holdout coverage and small-sample limitations.
- User benefit is an evaluation question. Supply a pilot protocol, never invented participant results.

## Tasks and verification

### 1. Repair source semantics and historical inputs

Files: `src/analysis/silver.py`, `gold.py`, `validate.py`, `bronze.py`; tests in `tests/test_readiness.py`.

- [x] Write and run failing checks for varying historical fleet stock, signed reconciliation differences and complete monthly source periods.
- [x] Parse the existing historical workbook, reject snapshot substitution, validate keys/positive values and complete financial years.
- [x] Add source URLs, SHA256 hashes, observation boundaries and table descriptions to the source manifest.
- [x] Run the source checks and existing tests.

### 2. Replace optimistic evaluation with useful forecast outputs

Files: `src/analysis/model.py`; tests in `tests/test_forecasting.py`.

- [x] Write failing checks for seasonal-naive forecasts, incomplete dates, strictly chronological folds, future dates and interval ordering.
- [x] Evaluate annual regression on expanding whole-year folds versus previous-year emissions, report per-state errors, and save an explicitly associative model for the API.
- [x] Compare fuel forecast candidates on multiple earlier rolling origins, evaluate the selected candidate on an untouched six-month holdout, then emit a six-month future forecast and empirical 80/95% intervals.
- [x] Save candidate metrics, fold dates, holdout predictions and actual future series in the output contract.
- [x] Run focused and existing tests.

### 3. Implement the complete briefing task

Files: `src/briefing.py`, `scripts/build_dashboard.py`, `dashboard/template.html`, `app/streamlit_app.py`, `app/api.py`; tests in `tests/test_briefing.py`.

- [x] Write failing checks for financial-year filters, per-capita comparisons, missing selection, export source/run identifiers and invalid API inputs.
- [x] Implement pure briefing calculations and plain-language exports, with transparent limitations and seven-jurisdiction coverage.
- [x] Build accessible state/year controls, summary, peer comparison, tables, downloadable briefing/CSV and forecast interpretation in both surfaces.
- [x] Show source cutoffs, run identifier and unresolved reconciliation prominently.
- [x] Verify the static build and API contract; inspect the dashboard and Streamlit in a browser.

### 4. Make one command reproducible

Files: `run_pipeline.py`, `src/provenance.py`, `src/db.py`, `monitoring/monitor.py`, `scripts/generate_diagrams.py`, `.github/workflows/ci.yml`, dependency files and guides.

- [x] Correct file and directory names, restore the template and actual diagram generator.
- [x] Write manifest/run metadata, hash outputs, store run identity with database results, integrate dashboard/diagrams/monitoring in the pipeline.
- [x] Add completeness/freshness reporting without treating stale annual inventories as live observations.
- [x] Reduce unused dependencies and lock the tested environment.
- [x] Run the full tests, full pipeline, repeat the dashboard build and check that artifacts agree.

### 5. Prepare assessment and research evidence

Files: `docs/assessment3/`, `docs/evaluation/`, `README.md`, `GUIDE.md`, `CHANGELOG.md`.

- [x] Write the research question, baseline comparison, pilot tasks, counterbalanced procedure, blank results sheet and success criteria.
- [x] Prepare a 19-minute demonstration runbook, slide outline and contribution evidence instructions using actual Git links.
- [x] State which evidence still requires the students: lab screenshots, genuine participant sessions, Assessment 2 comparison and final video.
- [x] Obtain independent code review, address material findings and record fresh test/runtime evidence.

## Progress record

- 3 October: Implementation, independent review repairs, the full pipeline, 55 Python tests, dashboard export checks and browser inspection completed. The editable 14-slide presentation, 19-minute runbook, pilot protocol and individual evidence guide are prepared. Release run: `982d7cbfcc4474d3`. See `reports/upgrade_verification_2026-10-03.md` for observed results and validation limits.

The completed checkboxes describe implementation and preparation tasks. Genuine pilot sessions, the actual Assessment 2 comparison, student contribution/lab evidence and final video are still required from the team.
