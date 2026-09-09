# AI-Powered Decision Support System — Road Transport Emissions (Australia)

Predictive analytics on Australian road transport emissions, built from
nine public government datasets: cleaning, EDA, and forecasting/regression
models over a single, flat pipeline.

## Status

**Implemented and verified working end-to-end** (as of this commit):
- Data loading + cleaning for all 9 sources (`src/analysis/clean.py`)
- Merged, analysis-ready tables (annual state-level, and monthly fuel
  series for forecasting)
- Exploratory data analysis — 6 figures (`src/analysis/eda.py`)
- Two models — annual emissions regression and monthly fuel forecast
  (`src/analysis/model.py`)
- Single command to run all of the above (`run_pipeline.py`)

**Not implemented / explicitly out of scope right now** — see
[CHANGELOG.md](./CHANGELOG.md) for why:
- Layered Bronze/Silver/Gold warehouse
- Streamlit dashboard
- FastAPI scoring endpoint
- CI/CD

**Running on fixture data.** Every source currently resolves to the small
synthetic sample files in `fixtures/` (copied into `data/bronze/` on
`2026-09-01`). This is clearly logged every time you run the pipeline.
See [Switching to live data](#switching-to-live-data) below — no code
changes needed, only real files dropped into `data/bronze/`.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python run_pipeline.py
```

That's it — one command runs cleaning, EDA, and model training in
sequence. Outputs land in:

| Output | Location |
|---|---|
| Cleaned, merged tables | `data/processed/*.csv` |
| EDA + forecast figures | `reports/figures/*.png` |
| Model metrics (JSON) | `reports/model_results/metrics.json` |
| Trained regression model | `reports/model_results/emissions_regression.pkl` |

Run any stage on its own if you only need part of it:

```bash
python -m src.analysis.clean    # just cleaning
python -m src.analysis.eda      # just EDA (builds processed data first if missing)
python -m src.analysis.model    # just modelling (builds processed data first if missing)
```

## Data sources

| # | Source | Loader function |
|---|---|---|
| 1 | Australian Petroleum Statistics | `clean.load_petroleum_statistics()` |
| 2 | State & Territory GHG Inventories | `clean.load_state_territory_ghg()` |
| 3 | National GHG Accounts OData API | not yet wired into the pipeline |
| 4 | National GHG Accounts Factors 2025 | `clean.load_nga_factors()` |
| 5 | BITRE Yearbook 2025 (VKT) | `clean.load_bitre_yearbook()` |
| 6 | Registered Road Vehicles, Australia | `clean.load_vehicle_registrations()` |
| 7 | Quarterly Update of National GHG Inventory | `clean.load_quarterly_ghg_update()` |
| 8 | ABS Population (ERP) | `clean.load_population()` |
| 9 | NSW Road Traffic Volume Counts API | not yet wired into the pipeline |

Sources 3 and 9 have fixture files (`fixtures/nga_odata_api.SAMPLE.json`,
`fixtures/nsw_traffic_counts.SAMPLE.csv`) but no loader in `clean.py` yet —
they're not used by any current model. Add a loader following the same
pattern as the others if/when they're needed.

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

Built by `clean.py`, one row per (state, year) unless noted:

- **`annual_master.csv`** (n=48: 8 states × 2020–2025) — fuel consumption,
  road VKT, registered vehicles, and road transport emissions (the
  regression target). The main modelling table.
- **`annual_master_with_population.csv`** (n=16: 8 states × 2024–2025
  only — population data doesn't currently go back further) — adds
  per-capita features for the Kaya-style decomposition view. Treat as
  illustrative given the small N, not as a training set on its own.
- **`monthly_fuel_series.csv`** (state × month, 2020–2025) — the
  forecasting target; far more observations per state (~72) than the
  annual table, so this is the series worth trusting once it's live data.

## Models

**`train_emissions_regression()`** — predicts annual state road-transport
emissions from fuel, VKT, and vehicle registrations. Linear regression and
random forest, both 5-fold cross-validated (not a single train/test split
— 48 rows is too few to trust one split). Reports CV R², CV MAE, and
random-forest feature importances.

**`forecast_fuel_consumption(state, test_months)`** — Holt-Winters
exponential smoothing (trend + seasonal) on monthly fuel consumption for
one state, with a dependency-free seasonal-naive fallback if
`statsmodels` isn't available. Reports MAE and MAPE on a held-out tail of
the series.

> **Read before citing any number from `reports/model_results/`:** all
> current metrics are computed on synthetic fixture data (randomly
> generated for pipeline development, not real emissions patterns). The
> regression's negative R² is expected and actually a good sign — it
> confirms the fixture data has no real signal to overfit to. On live
> data, expect the opposite failure mode: road transport emissions are
> *constructed* from fuel sales via published emission factors, so a
> regression against fuel consumption will show a near-tautological
> R² ≈ 0.98. That's not a genuine predictive finding — it's the
> accounting identity the data was built from. See the project's Kaya
> decomposition discussion for the correct way to attribute *why*
> emissions differ between states.

## Repository layout

```
src/analysis/
  clean.py     # load, standardise, merge -> data/processed/
  eda.py       # figures -> reports/figures/
  model.py     # train + evaluate -> reports/model_results/
run_pipeline.py  # runs all three in order
fixtures/        # small synthetic sample data, one file per source
data/bronze/     # raw landed data (currently = fixtures, dated)
data/processed/  # cleaned/merged output (generated, not committed raw)
reports/         # figures + model results (generated)
```

## Known gaps & next steps

- Sources 3 (OData API) and 9 (NSW traffic API) aren't wired into
  `clean.py` yet.
- No automated tests. `run_pipeline.py` has been run manually end-to-end
  and verified to produce all expected outputs, but there's no `pytest`
  suite guarding against regressions.
- No CI/CD.
- Dashboard/API layer from the original architecture — descoped, see
  [CHANGELOG.md](./CHANGELOG.md).

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
