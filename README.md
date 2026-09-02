# AI-Powered Decision Support System — Road Transport Emissions (Australia)

A tiered (medallion) data pipeline and anomaly-detection dashboard for Australian
road transport emissions, built from nine public government datasets.

```
Sources (9) → Ingestion → Bronze (raw) → Silver (cleaned) → Gold (star schema)
            → EDA → ML (anomaly detection + forecasting + explainability)
            → Dashboard + Alerting, with experiment tracking throughout
```

## Status

This repo covers **feature implementation only** (Epics 1–6 of the project plan):
setup, ingestion, storage, transformation, warehouse, ML, and dashboard. Formal
integration/UAT/security sign-off and the written assessment report are tracked
separately — see [Known Gaps & Next Steps](#known-gaps--next-steps). For how
the team should branch, commit, and merge going forward, see
[Git Workflow](#git-workflow).

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # defaults run entirely on bundled fixtures, no keys needed

# 1. Ingest all 9 sources into Bronze
python -m src.ingest.run_all

# 2. Transform Bronze → Silver
python -m src.transform.run_all

# 3. Load Silver → Gold warehouse
python -m src.storage.load_gold

# 4. Train models (also logs the run — see Experiment Tracking below)
python -m src.models.train

# (optional) run exploratory data analysis — figures land in reports/figures/
python -m src.eda.generate_eda

# (optional) rebuild the pre-executed EDA notebook from those figures
python scripts/build_eda_notebook.py

# 5. Run tests
pytest -q

# 6. Launch dashboard
streamlit run src/dashboard/app.py

# (optional) run the anomaly-scoring API
uvicorn src.models.scoring_api:app --reload
```

## Architecture

See `docs/architecture_diagram.png` (medallion architecture) and
`docs/workflow_diagram.png` (project workflow) carried over from the project
proposal.

| Layer | Location | Format |
|---|---|---|
| Bronze | `data/bronze/<source>/<ingest_date>/` | raw (csv/xlsx/json as received) |
| Silver | `data/silver/<entity>.parquet` | cleaned, harmonised, typed |
| Gold | `data/gold/warehouse.sqlite` (default; DuckDB/Postgres optional) | star schema |

## Data sources

| # | Source | Connector module |
|---|---|---|
| 1 | Australian Petroleum Statistics | `src/ingest/petroleum_statistics.py` |
| 2 | State & Territory GHG Inventories | `src/ingest/state_territory_ghg.py` |
| 3 | National GHG Accounts OData API | `src/ingest/nga_odata_api.py` |
| 4 | National GHG Accounts Factors 2025 | `src/ingest/nga_factors_2025.py` |
| 5 | BITRE Yearbook 2025 (VKT) | `src/ingest/bitre_yearbook.py` |
| 6 | Registered Road Vehicles, Australia | `src/ingest/vehicle_registrations.py` |
| 7 | Quarterly Update of National GHG Inventory | `src/ingest/quarterly_ghg_update.py` |
| 8 | ABS Population (ERP) | `src/ingest/abs_population.py` |
| 9 | NSW Road Traffic Volume Counts API | `src/ingest/nsw_traffic_counts.py` |

All connectors share a common `BaseConnector` (`src/ingest/base.py`) providing
retry/backoff, logging, and fixture-vs-live switching via `USE_FIXTURES`.

## Gold schema

- `dim_state`, `dim_vehicle_type`, `dim_time` — conformed dimensions
- `fact_emissions` — unions `state_territory_ghg`, `nga_odata_api` (year grain) and
  `quarterly_ghg_update` (quarter grain), tagged by `source`
- `fact_traffic_counts` — `nsw_traffic_counts`, hourly grain
- `fact_vehicle_registrations` — `vehicle_registrations`, joins `dim_vehicle_type`
- `fact_vkt`, `fact_fuel_consumption` — `bitre_yearbook`, `petroleum_statistics`
- `ref_emission_factors`, `ref_population` — reference tables (`nga_factors_2025`, `abs_population`)

All 9 Silver sources load into Gold. `src/storage/load_gold.reconcile()` checks
Gold aggregates against Silver source totals after every load and is covered
by tests (including a deliberately-corrupted-row test proving the check
actually catches mismatches, not just passes by construction).

## ML

- `src/models/features.py` — generic rolling-window time-series feature
  engineering (mean/std, lag delta, pct-change, rolling z-score), grouped by
  entity (state+sector, or station_id).
- `src/models/anomaly_isolation_forest.py` — unsupervised Isolation Forest
  over those features; scores 0–1, `is_anomaly` flag, save/load via pickle.
- `src/models/forecast_baseline.py` — uses **Prophet** if installed;
  otherwise falls back to a small dependency-free seasonal-trend model
  (linear trend + per-season residual mean) with the same fit/predict
  interface, so forecast-residual features work either way.
- `src/models/evaluate.py` — injects synthetic anomalies (magnitude ×
  group std-dev) into held-out data and reports precision/recall/F1.
- `src/models/train.py` — trains + evaluates + persists both detectors
  (emissions, traffic) in one run.
- `src/models/scoring.py` — framework-agnostic scoring wrapper used by both
  the dashboard and the API.
- `src/models/scoring_api.py` — FastAPI `/score` endpoint wrapping
  `scoring.py` for the dashboard/alerting layer (requires
  `pip install fastapi uvicorn`; not runnable in this offline sandbox but
  included and syntax-checked — see Known Gaps).

## Exploratory Data Analysis

`src/eda/generate_eda.py` — distributions, state-level trends, and a
cross-source correlation check (emissions vs. VKT, fuel, vehicle counts)
against the Gold warehouse. Figures save to `reports/figures/`.
`notebooks/01_eda.ipynb` is a **pre-executed** notebook (figures embedded,
no need to re-run) built by `scripts/build_eda_notebook.py` — hand-constructed
valid Jupyter JSON since `nbformat`/`jupyter` aren't installable in this
offline sandbox; regenerate it with `python scripts/build_eda_notebook.py`
once a fresh pipeline run has completed.

> Note: on the bundled fixture data, cross-source correlations are near zero
> by construction (the fixtures are synthetic/random) — the notebook flags
> this explicitly. Re-run against live data before citing correlation figures.

## Explainability

`src/models/explain.py` closes the proposal's ethics-section commitment to
explainable anomaly flags:
- **Global**: `global_feature_importance()` — permutation-style importance
  (shuffle one feature, measure how much the model's own scores change),
  model-agnostic, always available (no extra dependency).
- **Local**: `explain_record()` — uses **SHAP** `TreeExplainer` if installed;
  otherwise falls back to a z-score deviation ranking (how many standard
  deviations a flagged record's features sit from their training
  distribution) — simpler, but transparent and fully tested.
- `explain_top_alerts()` — convenience wrapper explaining the top-N
  highest-scoring anomalies in one call.

## Experiment Tracking

`src/models/tracking.py`, wired into `train.py`. Uses **MLflow** if
installed (logs to `./mlruns`, viewable with `mlflow ui`); otherwise falls
back to a dependency-free JSONL logger
(`artifacts/tracking/runs.jsonl`) capturing the same run_id/params/metrics
shape. `load_run_history()` reads either back as a flat, comparable
DataFrame — so you can compare training runs over time either way.

## Dashboard

Split into two layers, deliberately:
- `src/dashboard/data.py` — all filtering/scoring logic, pure pandas, **no
  Streamlit import**, so it's fully unit-tested without Streamlit installed.
- `src/dashboard/app.py` — thin Streamlit UI (state / time-range / vehicle-
  type filters, emissions & traffic trend charts, vehicle-registration view,
  and an alert banner + Alerts tab for anomalies above
  `ALERT_SCORE_THRESHOLD`) that only calls into `data.py` — no business logic
  duplicated in the UI layer. Requires `pip install streamlit`; not runnable
  in this offline sandbox but syntax-checked (see Known Gaps and
  `tests/test_dashboard.py::TestAppModuleSyntax`).

## Known Gaps & Next Steps

These are intentionally **out of scope** for this repo and are called out here
rather than silently skipped:

- **Live data access.** This sandboxed dev environment has no outbound network
  access, so `USE_FIXTURES=true` by default and every connector reads a small,
  clearly-labelled sample fixture from `./fixtures/`. Each connector's
  docstring notes the real endpoint it targets; set `USE_FIXTURES=false` with
  real credentials/network access to hit live sources.
- **NSW Traffic Volume API key.** Requires registration at
  opendata.transport.nsw.gov.au; not obtained here — fixture only.
- **Packages unavailable in this sandbox** (no `pip install` network access
  either): `pytest`, `pyarrow`, `duckdb`, `sqlalchemy`, `prophet`,
  `statsmodels`, `fastapi`/`uvicorn`, `streamlit`, `shap`, `mlflow`,
  `jupyter`/`nbformat`. The code targets all of them per `requirements.txt`
  for a real deployment, but was built and verified here using stdlib/
  fallback implementations so every phase could actually be run and tested
  end-to-end:
  - Tests are written as `unittest.TestCase` (stdlib) instead of plain
    `pytest` functions — `pytest -q` still discovers and runs them unchanged
    in a full environment; `python -m unittest discover tests` works here.
  - Silver writer uses parquet if `pyarrow`/`fastparquet` is present, else
    falls back to CSV (`src/transform/harmonise.write_silver`).
  - Gold warehouse defaults to stdlib `sqlite3` instead of DuckDB; DuckDB/
    Postgres backends are implemented in `src/storage/warehouse.py` and
    activate automatically once those packages are installed.
  - Forecast baseline uses Prophet if installed, else a small dependency-free
    seasonal-trend fallback (`src/models/forecast_baseline.py`).
  - Local explanations use SHAP `TreeExplainer` if installed, else a
    z-score deviation fallback (`src/models/explain.py`).
  - Experiment tracking uses MLflow if installed, else a JSONL fallback
    logger (`src/models/tracking.py`).
  - `notebooks/01_eda.ipynb` was built without `nbformat`/`jupyter` — it's
    hand-constructed valid Jupyter JSON (`scripts/build_eda_notebook.py`),
    with real figure outputs embedded so it's genuinely pre-executed, not
    just written.
  - `scoring_api.py` (FastAPI) and `dashboard/app.py` (Streamlit) are written
    against their real APIs but could only be syntax-checked
    (`python -m py_compile` / `ast.parse`), not executed, in this sandbox.
- **CI/CD.** No GitHub Actions configured yet.
- **Cloud deployment.** Warehouse defaults to local SQLite; Postgres/Synapse
  config exists in `src/common/config.py` but isn't deployed anywhere.
- **Formal security hardening & sign-off.** Secrets are read from `.env`
  (gitignored) and never hardcoded, but no formal security review has been
  done — tracked as a separate project task (Epic 7).
- **Integration/UAT testing and the final written report** are tracked as
  separate project tasks (Epics 7–8), not part of this repo's scope.

## Testing

```bash
pytest -q               # unit + integration tests
pytest --cov=src -q     # with coverage
```

Each phase (ingest / transform / storage / models / dashboard) has its own
test module under `tests/`, written alongside the corresponding feature.

## Git Workflow

**Model: GitHub Flow** — one protected `main` + short-lived feature branches.
Full GitFlow (`main`/`develop`/`release`/`hotfix`) is overkill for a 6-week,
5-person project with no versioned production releases; GitHub Flow gives the
same branch/PR/review evidence with far less overhead.

```
main ──●────────●────────●────────●────────●──── (always working, protected)
        \        \        \        \        \
         feature/ feature/ feature/ feature/ feature/
         ingest-  silver-  gold-    ml-      dashboard-
         petrol   dedup    schema   isoforest filters
         ●──●──●  ●──●     ●──●──●  ●──●──●   ●──●
              ↑ PR + review + squash-merge, then delete branch
```

### Branch naming

`<type>/<epic-slug>-<task-slug>`, mapped to the Jira epics above:

| Type | When | Example |
|---|---|---|
| `feature/` | New functionality | `feature/ingest-nsw-traffic-connector` |
| `fix/` | Bug fix | `fix/silver-null-state-codes` |
| `test/` | Tests-only change | `test/gold-reconciliation-checks` |
| `docs/` | README/docs only | `docs/readme-quickstart` |
| `chore/` | Tooling, config, deps | `chore/add-shap-dependency` |
| `refactor/` | No behaviour change | `refactor/extract-time-key-builder` |

### `main` branch protection

- Require a pull request before merging — no direct pushes, including from
  the project lead
- Require at least 1 approving review
- Require status checks (`pytest`) to pass once CI is added
- Require branches to be up to date before merging
- No force-pushes to `main`

### Commit messages — Conventional Commits

`<type>(<scope>): <what changed>`, scope = the layer touched (`ingest`,
`silver`, `gold`, `models`, `dashboard`):

```
feat(ingest): add NSW traffic volume connector
fix(silver): handle null state codes in entity resolution
test(models): add synthetic anomaly injection edge case
docs(readme): document experiment tracking fallback
chore(deps): add shap and mlflow to requirements.txt
```

### PR workflow

1. `git checkout main && git pull`
2. `git checkout -b feature/<epic>-<task>`
3. Commit in small chunks as you go, not one batched commit per epic
4. Push early, open a **draft PR** immediately for visibility
5. Mark ready for review once tests pass locally
6. Review from the person on the *adjacent* layer (e.g. the ML engineer
   reviews the Data Modeller's Silver→Gold PR — that's the actual dependency)
7. **Squash-merge** into `main` — keeps history as one clean commit per
   feature rather than a stream of "wip" commits
8. Delete the branch

### Merge order

Layers are dependent (Silver needs Bronze, Gold needs Silver, ML needs
Gold), so **merge to `main` in dependency order**, not whoever finishes
first. If a downstream branch (e.g. ML) was based on an older upstream
schema (e.g. Gold) that has since changed on `main`, rebase the downstream
branch onto `main` after the upstream merge, rather than resolving the same
conflict twice.

### Release tags

Tag `main` at each Sprint Overview milestone so the tag list doubles as
progress evidence:

```bash
git tag -a v0.1-bronze -m "Ingestion complete: all 9 sources landing in Bronze"
git tag -a v0.2-silver -m "Silver layer: validation, harmonisation, dedup"
git tag -a v0.3-gold -m "Gold warehouse: star schema + reconciliation"
git tag -a v0.4-ml -m "ML: anomaly detection, forecasting, explainability"
git tag -a v0.5-dashboard -m "Dashboard: filters, trends, alerts"
git tag -a v1.0 -m "Final: feature-complete, tested, ready for report"
git push --tags
```

> **Note on this repo's own history:** the current commits on `main` were
> made directly (one per phase) while this was built solo in a single
> session, not through the feature-branch/PR flow above. Adopt the flow
> above going forward for all new work.