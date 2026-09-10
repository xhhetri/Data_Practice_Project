
# AI-Powered Decision Support System — Road Transport Emissions (Australia)

Predictive analytics on Australian road transport emissions, built from
nine public government datasets: cleaning, EDA, and forecasting/regression
models over a single, flat pipeline.

## Status

**Real government data is now loaded and verified working**, not just
fixtures. 7 of 9 sources currently resolve to real downloaded files (see
[Data sources](#data-sources)); 2 (OData API, NSW traffic) still fall
back to fixtures — no real pull wired in yet for those.

**Implemented and verified end-to-end:**

- Data loading + cleaning for all 9 sources, real-file-aware
  (`src/analysis/clean.py`)
- Merged, analysis-ready tables (annual state-level, monthly fuel series,
  NSW hourly traffic)
- Exploratory data analysis — 8 figures (`src/analysis/eda.py`)
- Three models — annual emissions regression, monthly fuel forecast, NSW
  hourly traffic forecast (`src/analysis/model.py`)
- Data quality validation — emission-factor cross-check and dual-source
  GHG consistency check (`src/analysis/validate.py`)
- 28 automated tests (`tests/test_clean.py`, run with `pytest tests/`)
- CI on every push/PR (`.github/workflows/ci.yml`)
- Single command to run the whole pipeline (`run_pipeline.py`)
- Architecture and workflow diagrams (`docs/`)

**Not implemented / explicitly out of scope** — see
[CHANGELOG.md](./CHANGELOG.md):

- Layered Bronze/Silver/Gold warehouse, Streamlit dashboard, FastAPI
  endpoint — all descoped; a `src/ingest/` layer was tried, found to
  depend on a `src/common/` module never committed anywhere in this
  repo's history, and removed rather than rebuilt.

## What running on real data actually showed

The regression (fuel + VKT + vehicles → transport emissions) scores
**CV R² ≈ 0.995** on real data. That is expected, not a triumph to
celebrate uncritically: state emissions inventories are *constructed
from* fuel sales via published NGA emission factors, so a near-perfect
score here mostly reflects that accounting identity, not a novel
predictive insight. This is exactly what was predicted before any real
data was loaded — see the model-performance discussion in this
project's assessment report.

The **fuel forecast** is the model actually worth trusting: MAPE dropped
from 186% (synthetic fixtures, i.e. noise) to **3.8%** on real monthly
petroleum sales, because Holt-Winters is now fitting genuine seasonal
structure instead of random numbers.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

pytest tests/          # 28 tests (real-file loaders included, ~2 min)
python run_pipeline.py  # clean -> EDA -> model -> validate
```

Outputs land in:

| Output                   | Location                                           |
| ------------------------ | -------------------------------------------------- |
| Cleaned, merged tables   | `data/processed/*.csv`                           |
| EDA figures              | `reports/figures/*.png`                          |
| Model metrics (JSON)     | `reports/model_results/metrics.json`             |
| Trained regression model | `reports/model_results/emissions_regression.pkl` |
| Data quality checks      | `reports/validation/*.csv`, `*.png`            |

Every pipeline run logs, per source, whether it used real data, the
sample fixture, or the bundled fixture fallback — check these lines
before citing any number:

```
INFO: Using real data for 'petroleum_statistics': data/bronze/Australian Petroleum statistics consumption cover/...
INFO: Falling back to fixture for 'nsw_traffic_counts': fixtures/nsw_traffic_counts.SAMPLE.csv
```

## Data sources

| # | Source                                                   | Loader                           | Real file in repo?                               | Used by                                                                                            |
| - | -------------------------------------------------------- | -------------------------------- | ------------------------------------------------ | -------------------------------------------------------------------------------------------------- |
| 1 | Australian Petroleum Statistics                          | `load_petroleum_statistics()`  | ✅`Sales by state and territory` sheet         | annual master, monthly forecast, validation                                                        |
| 2 | State & Territory GHG Inventories (Emission Data Tables) | `load_state_territory_ghg()`   | ✅ per-state sheets, "3. Transport" row          | annual master (regression target), validation                                                      |
| 3 | National GHG Accounts OData API                          | `load_nga_odata_api()`         | ❌ fixture only                                  | validation (cross-source check) —**currently uninformative**, see caveat in `validate.py` |
| 4 | National GHG Accounts Factors 2025                       | `load_nga_factors()`           | ✅`Table 9` (transport fuels)                  | validation (emission-factor check)                                                                 |
| 5 | BITRE Yearbook 2025 (VKT)                                | `load_bitre_yearbook()`        | ✅`Table 4.3`                                  | annual master                                                                                      |
| 6 | Registered Road Vehicles                                 | `load_vehicle_registrations()` | ✅ real CSV (fleet-by-manufacture-year snapshot) | annual master (as a broadcast constant — see caveat below)                                        |
| 7 | Quarterly GHG Update                                     | `load_quarterly_ghg_update()`  | ✅`Data Table 1A` (national only)              | loaded, not merged into any state-level table — no state dimension exists in this source          |
| 8 | ABS Population (ERP)                                     | `load_population()`            | ✅`Data1` sheet                                | annual master with population                                                                      |
| 9 | NSW Traffic Volume Counts                                | `load_nsw_traffic_counts()`    | ❌ fixture only                                  | NSW traffic EDA + forecast                                                                         |

**Real files currently live under human-named folders** (whatever the
person who downloaded them called it), not the canonical `source_name`
keys — e.g. `data/bronze/Australian Petroleum statistics consumption cover/`. `clean.py`'s `BRONZE_FOLDER_ALIASES` maps every folder name
we've seen used to its canonical source; add to that dict if a new
folder name shows up rather than renaming folders to match.

## Real-data caveats — read before writing these into the report

Four genuine data-shape findings from actually loading the real files,
each handled explicitly in code (not silently glossed over):

1. **State emissions = whole transport sector, not road-only.** The
   Emission Data Tables' finest state-level breakdown is `"3. Transport"`
   — road + rail + domestic aviation + shipping combined. There is no
   further mode split at the state level in this published source. Every
   place this number is used is labelled "transport-sector emissions,"
   not "road transport emissions" specifically.
2. **ACT has no state-level fuel sales data.** Confirmed against the raw
   source file's own `State` column — not a parsing gap. `annual_master`
   therefore covers 7 states, not 8.
3. **Vehicle registrations is a snapshot, not a time series.** The real
   file breaks the *current* fleet down by year of *manufacture*
   (`yom` in the filename), not registrations per year. There is no
   genuine year-varying figure available from this source, so
   `build_annual_master()` broadcasts each state's current total fleet
   size as a constant across every year — logged with a warning every
   run. Don't read year-to-year variation into this feature; there isn't
   any.
4. **The emission-factor validation gap (~30%) is expected, not a bug.**
   `validate_emission_factors()` compares *road-fuel-only* implied
   emissions against the *whole-transport-sector* reported figure (see
   point 1) — implied should run lower, roughly in proportion to road's
   share of transport fuel use. See that function's docstring for the
   full reasoning and what a gap outside the expected range would mean.

## Switching remaining sources to real data

Sources 3 (OData API) and 9 (NSW traffic) still use fixtures. Same
mechanism as everything else — `clean._locate()` finds real data
automatically:

1. Download the file.
2. Drop it into `data/bronze/<source_name>/` (or add a new alias to
   `BRONZE_FOLDER_ALIASES` if you'd rather use a human-readable folder
   name), filename must not contain `SAMPLE`.
3. Re-run `python run_pipeline.py` and check the log line confirms
   "Using real data."

Note: neither loader currently branches on real-vs-fixture shape the
way the other 7 do (see e.g. `load_population()`'s `is_real` check) —
whoever wires these up will need to inspect the real file's actual
structure first and add that branch, following the same pattern.

## Analysis-ready tables

Built by `clean.py`, all aligned to Australian financial year (labelled
by its start year, e.g. "2020" = FY2020-21 — see `_parse_financial_year()`
/ `_fy_start_from_date()`):

- **`annual_master.csv`** — fuel consumption, road VKT, registered
  vehicles (broadcast constant, see caveat 3 above), and transport-sector
  emissions (the regression target). Currently 98 rows: 7 states ×
  2010–2023 (limited by fuel data's earliest year and emissions data's
  latest year). The main modelling table.
- **`annual_master_with_population.csv`** — adds population and
  per-capita features. Real ABS population data goes back to 1981, so
  this is no longer meaningfully smaller than the base table the way it
  was on fixtures (where it shrank from 48 rows to 16).
- **`monthly_fuel_series.csv`** — the fuel forecasting target, ~190
  monthly points per state on real data.
- **`nsw_traffic_hourly.csv`** — still fixture-only (source 9).

## Models

**`train_emissions_regression()`** — linear regression and random
forest, 5-fold cross-validated. Reports CV R², CV MAE, and random-forest
feature importances.

**`forecast_fuel_consumption(state, test_months)`** /
**`forecast_nsw_traffic(station, test_hours)`** — Holt-Winters
exponential smoothing with a seasonal-naive fallback if `statsmodels`
fails (this happened on one teammate's environment — a real
`statsmodels` bug, fixed by upgrading to ≥0.15.0, see `requirements.txt`
and `CHANGELOG.md`).

> **Every model result's `_caveat` field is generated at runtime**, not
> hardcoded — it deliberately does not assert whether real or fixture
> data produced it, since that depends on what was in `data/bronze/`
> when the pipeline ran. Check that run's "Using real data" / "Using
> sample data" log lines, not this file, for the actual answer.

## Data quality validation

`src/analysis/validate.py`:

- **`validate_emission_factors()`** — fuel × published NGA factor vs.
  reported emissions. See caveat 4 above for why a ~30% gap is expected
  here, not a bug.
- **`validate_ghg_cross_source()`** — CSV inventory vs. OData API pull.
  **Currently uninformative**: state_territory_ghg is real, but
  nga_odata_api is still the fixture (source 3 above), so this compares
  real data against random numbers. Becomes meaningful once a real
  OData pull replaces the fixture.

## Testing

```bash
pytest tests/ -v
```

28 tests. Master-table shape tests deliberately check structure (row
count > 0, valid state codes, no nulls, positive values) rather than
exact numbers — `_locate()` prefers real data whenever it's present, so
hardcoded fixture-era counts (48 rows, 8 states, 6 years) would make
these tests fail the moment real data was added. Structural checks stay
meaningful in both cases.

## Continuous Integration

`.github/workflows/ci.yml` runs on every push/PR: installs
`requirements.txt`, runs tests, runs the full pipeline, uploads outputs
as a build artifact. Since real files now live in `data/bronze/` and are
committed, CI exercises the same real-data path as local runs — not a
fixture-only smoke test.

## Diagrams

`docs/architecture/` and `docs/workflow/` — regenerate after any
structural change with `python scripts/generate_diagrams.py`.

## Repository layout

```
src/analysis/
  clean.py       # load, standardise, merge -> data/processed/ (real-file-aware)
  eda.py         # figures -> reports/figures/
  model.py       # train + evaluate -> reports/model_results/
  validate.py    # data quality checks -> reports/validation/
tests/
  test_clean.py  # 28 tests, run with `pytest tests/`
scripts/
  generate_diagrams.py
.github/workflows/
  ci.yml
run_pipeline.py
fixtures/        # small synthetic sample data -- fallback only now
data/bronze/     # real downloaded files (human-named folders) + dated fixture copies
data/processed/  # cleaned/merged output (generated)
reports/         # figures + model results + validation (generated)
docs/            # architecture and workflow diagrams
```

## Known gaps & next steps

- Sources 3 (OData API) and 9 (NSW traffic) still fixture-only.
- Source 7 (Quarterly GHG Update) loaded but not merged anywhere — no
  state dimension exists in it to merge on.
- The four real-data caveats above (whole-sector emissions, ACT gap,
  vehicle-registration snapshot, expected validation gap) should be
  stated explicitly anywhere these results are cited in the report.
- Individual per-teammate git commits — adopt the branch/PR flow below.

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

| Type         | When                  | Example                           |
| ------------ | --------------------- | --------------------------------- |
| `feature/` | New functionality     | `feature/model-forecast-cv`     |
| `fix/`     | Bug fix               | `fix/clean-null-state-codes`    |
| `test/`    | Tests-only change     | `test/model-regression-cv`      |
| `docs/`    | README/docs only      | `docs/readme-quickstart`        |
| `chore/`   | Tooling, config, deps | `chore/pin-statsmodels-version` |

### Commit messages — Conventional Commits

```
feat(clean): parse real petroleum sales sheet, road-fuel products only
fix(validate): align fuel to financial year before comparing to emissions
docs(readme): document real-data caveats
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
