# AI-Powered Decision Support System —  Transport Emissions (Australia)

Predictive analytics on Australian road transport emissions, built from
nine public government datasets: cleaning, EDA, and forecasting/regression
models over a single, flat pipeline.

## Status

**Implemented and verified working end-to-end** (as of this commit):
- Data loading + cleaning for all 9 sources (`src/analysis/clean.py`)
- Merged, analysis-ready tables (annual state-level, monthly fuel series,
  and NSW hourly traffic)
- Exploratory data analysis — 8 figures (`src/analysis/eda.py`)
- Three models — annual emissions regression, monthly fuel forecast, and
  NSW hourly traffic forecast (`src/analysis/model.py`)
- Data quality validation — emission-factor cross-check and dual-source
  GHG consistency check (`src/analysis/validate.py`)
- 22 automated tests (`tests/test_clean.py`, run with `pytest tests/`)
- CI on every push/PR — tests + full pipeline smoke test
  (`.github/workflows/ci.yml`)
- Single command to run the whole pipeline (`run_pipeline.py`)
- Architecture and workflow diagrams (`docs/architecture/`, `docs/workflow/`)

**Not implemented / explicitly out of scope** — see
[CHANGELOG.md](./CHANGELOG.md) for why:
- Layered Bronze/Silver/Gold warehouse
- Streamlit dashboard
- FastAPI scoring endpoint
- A `src/ingest/` connector layer was tried, found to depend on a
  `src/common/` module that was never committed anywhere in this repo's
  history, and removed rather than rebuilt — full details in
  [CHANGELOG.md](./CHANGELOG.md).

**Running on fixture data — this is the main remaining gap.** Every
source currently resolves to the small synthetic sample files in
`fixtures/` (copied into `data/bronze/` on `2026-09-01`). This is clearly
logged every time you run the pipeline. See
[Switching to live data](#switching-to-live-data) below — no code changes
needed, only real files dropped into `data/bronze/`.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

pytest tests/          # 22 tests, ~0.5s
python run_pipeline.py  # clean -> EDA -> model -> validate
```

Outputs land in:

| Output | Location |
|---|---|
| Cleaned, merged tables | `data/processed/*.csv` |
| EDA figures | `reports/figures/*.png` |
| Model metrics (JSON) | `reports/model_results/metrics.json` |
| Trained regression model | `reports/model_results/emissions_regression.pkl` |
| Data quality checks | `reports/validation/*.csv`, `*.png` |

Run any stage on its own if you only need part of it:

```bash
python -m src.analysis.clean     # just cleaning
python -m src.analysis.eda       # just EDA (builds processed data first if missing)
python -m src.analysis.model     # just modelling (builds processed data first if missing)
python -m src.analysis.validate  # just the data quality checks
```

## Data sources

| # | Source | Loader function | Used by |
|---|---|---|---|
| 1 | Australian Petroleum Statistics | `clean.load_petroleum_statistics()` | annual master, monthly forecast, validation |
| 2 | State & Territory GHG Inventories | `clean.load_state_territory_ghg()` | annual master (regression target), validation |
| 3 | National GHG Accounts OData API | `clean.load_nga_odata_api()` | validation (cross-source check) only |
| 4 | National GHG Accounts Factors 2025 | `clean.load_nga_factors()` | validation (emission-factor check) only |
| 5 | BITRE Yearbook 2025 (VKT) | `clean.load_bitre_yearbook()` | annual master |
| 6 | Registered Road Vehicles, Australia | `clean.load_vehicle_registrations()` | annual master |
| 7 | Quarterly Update of National GHG Inventory | `clean.load_quarterly_ghg_update()` | loaded, not yet consumed by any table — candidate for a nowcast/reconciliation feature |
| 8 | ABS Population (ERP) | `clean.load_population()` | annual master with population |
| 9 | NSW Road Traffic Volume Counts API | `clean.load_nsw_traffic_counts()` | NSW traffic EDA + forecast |

All 9 sources now have a loader. Source 7 is loaded and tested but not
yet wired into a table or model — the natural next step is comparing it
against `annual_master.csv`'s year-end figures as a nowcast check,
similar in spirit to `validate.py`.

## Switching to live data

`clean._locate()` looks for real data automatically — no code changes
needed:

1. Download the real source file (see the assessment report's dataset
   table for exact links).
2. Drop it into `data/bronze/<source_name>/<YYYY-MM-DD>/`, with a filename
   that does **not** contain `SAMPLE`.
3. Re-run `python run_pipeline.py` — the loader logs which file it picked
   up for each source, so you can confirm it switched from fixture to
   real data.

## Analysis-ready tables

Built by `clean.py`:

- **`annual_master.csv`** (n=48: 8 states × 2020–2025) — fuel consumption,
  road VKT, registered vehicles, and road transport emissions (the
  regression target). The main modelling table.
- **`annual_master_with_population.csv`** (n=16: 8 states × 2024–2025
  only — population data doesn't currently go back further) — adds
  per-capita features for the Kaya-style decomposition view. Treat as
  illustrative given the small N, not as a training set on its own.
- **`monthly_fuel_series.csv`** (state × month, 2020–2025) — the fuel
  forecasting target; far more observations per state (~72) than the
  annual table.
- **`nsw_traffic_hourly.csv`** (station × hour, NSW only, ~1 week) — a
  different grain entirely (hourly, single-state), used for its own EDA
  and forecast rather than merged into the state-year tables.

## Models

**`train_emissions_regression()`** — predicts annual state road-transport
emissions from fuel, VKT, and vehicle registrations. Linear regression and
random forest, both 5-fold cross-validated. Reports CV R², CV MAE, and
random-forest feature importances.

**`forecast_fuel_consumption(state, test_months)`** — Holt-Winters
exponential smoothing on monthly fuel consumption for one state, with a
seasonal-naive fallback if `statsmodels` isn't available.

**`forecast_nsw_traffic(station, test_hours)`** — same method, 24-hour
seasonality, on hourly station-level traffic volume.

> **Read before citing any number from `reports/model_results/` or
> `reports/validation/`:** all current metrics are computed on synthetic
> fixture data (randomly generated for pipeline development, independently
> per source file). Two consequences worth knowing before you write these
> up: the regression's negative R² is expected — it confirms the fixture
> data has no real cross-variable signal, which is correct behaviour for
> random data, not a bug. And `validate.py`'s emission-factor and
> cross-source checks currently show large mismatches (~150%+) for the
> same reason — the different source fixtures were generated
> independently of each other, so they don't actually agree, whereas real
> government data should. On live data, expect the opposite pattern:
> emissions should correlate strongly with fuel sales (they're
> *constructed* from it via published factors), and `validate.py`'s checks
> should show close agreement — a large mismatch on real data would be a
> genuine finding worth investigating, not an artefact of synthetic
> fixtures.

## Data quality validation

`src/analysis/validate.py` — two checks that don't fit as "models" or
"EDA":

- **`validate_emission_factors()`** — computes implied emissions
  (fuel consumed × published NGA emission factor) and compares against
  the reported inventory figure for the same state/year. This is the
  accounting identity real emissions inventories are built from; on real
  data it should match closely, and doesn't yet cover fuel types besides
  diesel in the current data.
- **`validate_ghg_cross_source()`** — compares the published CSV
  inventory table against the same data pulled via the OData API,
  flagging any state/year present in one but not the other, and the size
  of any numeric disagreement.

## Testing

```bash
pytest tests/ -v
```

22 tests covering: state-code standardisation, every individual loader,
exact row counts for every master table (given the fixed fixture files),
and the `_locate()` source-resolution logic (real data vs. sample vs.
fixture fallback, using `tmp_path` so it doesn't touch the real
`data/bronze/`).

## Continuous Integration

`.github/workflows/ci.yml` runs on every push and PR to `main`: installs
`requirements.txt`, runs the test suite, then runs the full pipeline
against the fixture data as a smoke test, and uploads the generated
`data/processed/` and `reports/` as a downloadable build artifact.

## Diagrams

`docs/architecture/architecture_v2.png` and `docs/workflow/workflow_v2.png`
— regenerate after any structural change with:

```bash
python scripts/generate_diagrams.py
```

## Repository layout

```
src/analysis/
  clean.py       # load, standardise, merge -> data/processed/
  eda.py         # figures -> reports/figures/
  model.py       # train + evaluate -> reports/model_results/
  validate.py    # data quality checks -> reports/validation/
tests/
  test_clean.py  # 22 tests, run with `pytest tests/`
scripts/
  generate_diagrams.py  # regenerates docs/architecture/, docs/workflow/
.github/workflows/
  ci.yml         # tests + pipeline smoke test on every push/PR
run_pipeline.py  # runs clean -> eda -> model -> validate, in order
fixtures/        # small synthetic sample data, one file per source
data/bronze/     # raw landed data (currently = fixtures, dated)
data/processed/  # cleaned/merged output (generated, not committed raw)
reports/         # figures + model results + validation (generated)
docs/            # architecture and workflow diagrams
```

## Known gaps & next steps

- **Real data isn't loaded yet** — this is the main outstanding item; see
  [Switching to live data](#switching-to-live-data).
- Source 7 (Quarterly GHG Update) is loaded and tested but not yet used
  in any table or model.
- No CI/CD *deployment* step (dashboard/API were descoped, so there's
  nothing to deploy) — CI here means test+smoke-test only.
- Individual per-teammate git commits — adopt the branch/PR flow below
  from here forward so each person has linkable commit evidence.

## Git Workflow

**Model: GitHub Flow** — one protected `main` + short-lived feature branches.

```
main ──●────────●────────●────────●──── (always working, protected)
        \        \        \        \
         feature/ feature/ feature/ feature/
         clean-   eda-     model-   docs-
         merge    figures  cv       readme
         ●──●──●  ●──●     ●──●──●  ●──●
              ↑ PR + review + squash-merge, then delete branch
```

### Branch naming

`<type>/<epic-slug>-<task-slug>`:

| Type | When | Example |
|---|---|---|
| `feature/` | New functionality | `feature/model-forecast-cv` |
| `fix/` | Bug fix | `fix/clean-null-state-codes` |
| `test/` | Tests-only change | `test/model-regression-cv` |
| `docs/` | README/docs only | `docs/readme-quickstart` |
| `chore/` | Tooling, config, deps | `chore/pin-statsmodels-version` |

### Commit messages — Conventional Commits

```
feat(clean): add population loader and per-capita features
fix(model): guard against short series in forecast fallback
docs(readme): document live-data switchover
```

### PR workflow

1. `git checkout main && git pull`
2. `git checkout -b feature/<epic>-<task>`
3. Commit in small chunks, not one batch per epic — this matters for
   Assessment 2 Section 4, where each teammate links their own commits
4. Push early, open a draft PR for visibility
5. One approving review before merge
6. Squash-merge into `main`, delete the branch

> **Note on this repo's history:** commits before this point were made
> directly to `main` while the project was rebuilt solo after the
> architecture change (see CHANGELOG.md). Adopt the branch/PR flow above
> for all work from here forward, so each team member has individual,
> linkable commit evidence for their contribution page.
