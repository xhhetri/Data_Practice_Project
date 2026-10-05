# FuelScope: Australian fuel-market review

An analyst workspace for **daily wholesale-price checks and weekly fuel-market briefings**. Choose a jurisdiction and fuel, inspect dated price and national-stock changes, evaluate the separate petrol/diesel sales outlook, save a local review checkpoint and export a cited briefing. The original transport/emissions analysis remains available through the dashboard's link and Streamlit.

The intended benefit is faster, more accurate recurring review. Actual adoption and time savings are **not yet demonstrated by participant research**. The [market-review pilot](docs/evaluation/market_review_pilot.md) defines the Assessment 4 evaluation. Statistical changes are investigation prompts, not shortage forecasts or policy effects.

## Use it

On Windows, double-click **Start-FuelScope.cmd**, or start the local review service:

```powershell
.venv\Scripts\python.exe -m scripts.serve_review --port 8766
```

Open **http://127.0.0.1:8766/**. Use **Check for updates** to check the official publication pages; validated caches remain available if a feed fails. Nothing downloads automatically on page load. Wholesale prices update on working days; weekly MSO publication is currently temporary; monthly sales retain their reporting lag.

The [standalone dashboard](dashboard/index.html) also works offline with its adjacent `plotly.min.js`. Its refresh control explains how to open the local service. Notes, selected jurisdiction/fuel and a review checkpoint are stored only in this browser. Markdown and evidence CSV downloads work offline; **Print / save PDF** opens the browser's print workflow.

The [original transport dashboard](dashboard/transport.html), [original technical results](reports/evaluation/technical_results.md), and [market model results](reports/market_review/technical_results.md) remain directly readable.

Rebuild with Python 3.12 and the tracked government files:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.venv\Scripts\python.exe run_pipeline.py
.venv\Scripts\python.exe -m pytest tests/ -q
.venv\Scripts\python.exe -m scripts.serve_review --port 8766
```

On macOS/Linux, use `.venv/bin/python` in place of `.venv\Scripts\python.exe`. Run commands from the repository root. This checkout already has a local `.venv`; its environment is not committed. See [GUIDE.md](GUIDE.md) for API, troubleshooting and verification.

## What the data means

The retained annual comparison covers seven jurisdictions, FY2010-11 to FY2023-24, with 98 rows. The original combined monthly-sales release retains its 1,344 observations through June 2026. The new market module uses a separately retained July 2026 petroleum extract with **2,702 fuel/state/month observations**, AIP price history from 2004 through 2 October 2026, and national weekly MSO observations through 22 September 2026. Observation cutoffs shown in the app are authoritative after refresh. Capital-city terminal prices are not state-average prices; national stocks are not local-depot holdings.

The original six government source files remain intact. Additional source files, hashes, retrieval/check times and status are in `data/market/source_manifest.json`; processed evidence is in `data/market/processed/`. Added price/stock measures supply recurring context. They are not yet fitted as predictors of monthly sales.

| Source | Use and boundary |
|---|---|
| [DCCEEW state/territory inventories](https://www.dcceew.gov.au/climate-change/publications/national-greenhouse-accounts/state-and-territory-greenhouse-gas-inventories-data-tables-methodology) | Official financial-year whole-transport inventory; all transport modes |
| [Australian Petroleum Statistics](https://www.energy.gov.au/energy-data/australian-petroleum-statistics) | Automotive gasoline plus TOTAL diesel sales; includes non-road diesel use |
| [BITRE Yearbook 2025](https://www.bitre.gov.au/sites/default/files/documents/bitre-yearbook-2025.pdf) | Road VKT Table 4.3 and historical vehicle stock Table 4.6b, originally thousands of vehicles |
| [ABS population](https://www.abs.gov.au/statistics/people/population/national-state-and-territory-population/latest-release) | Mean of four unique quarterly population observations in each financial year |
| [DCCEEW quarterly inventories](https://www.dcceew.gov.au/climate-change/publications/national-greenhouse-gas-inventory-quarterly-updates) | National context retained separately; not substituted for state observations |
| [NGA factors 2025](https://www.dcceew.gov.au/climate-change/publications/national-greenhouse-accounts-factors-2025) | Simple combustion-factor boundary diagnostic; not the state inventory methodology |

Six physical source files produce seven logical cleaned tables because BITRE supplies VKT and historical fleet stock. The separate downloaded manufacturing-year vehicle CSV is not a historical fleet series and is not used. Actual file names, SHA256 hashes and source boundaries are in `data/bronze/_manifest.csv` and `reports/run_metadata.json`. Original source retrieval dates are unknown; file modification times are not retrieval evidence.

Financial years use their start year (`2023` means FY2023-24). Historical BITRE vehicle stock uses the published calendar-year label associated with the FY starting in that year; this is an approximation, not a financial-year average. The legacy CSV field `fuel_consumption_ml` means petrol plus total diesel **sales** in this project. It must not be quoted as measured road-only consumption.

## Evaluation and limitations

Fuel forecasts compare seasonal naive with additive Holt-Winters on expanding earlier windows with at least 60 training months and six-month horizons. The retained combined-sales analysis uses six-month steps; FuelScope's separate petrol/diesel series use three-month steps. The selected candidate is then evaluated on the untouched last six observed months and refitted on all available months to produce the next six. Candidate failure is recorded; the simple method is the operational fallback. Model selection does not use the last holdout error.

Approximate 80/95% bands use horizon-specific absolute historical forecast-error quantiles. Actual final-holdout coverage is disclosed in the interfaces and exports. The bands are not guaranteed probabilities; six holdout months and changing historical conditions cannot establish calibration. A forecast begins after the source cutoff, which may already precede today.

Annual linear regression and random forest use expanding **whole-year** folds against previous-year emissions, with per-state errors. Regression receives actual same-year activity covariates, while the previous-year benchmark uses only earlier emissions. This is an association comparison, not an operational emissions forecast. High pooled R² can reflect state size and accounting relationships; it does not establish causality, intervention effects, or inventory reconciliation.

The signed fuel-times-factor diagnostic remains unresolved. It exceeds official transport inventory values in most matched state-years; the old explanation that other transport modes necessarily make it lower was incorrect. See the generated technical results for current discrepancy counts. Use the official inventory for an emissions briefing.

ACT is absent because the selected sales source has no separate ACT series. Per-capita comparisons improve comparability but do not adjust for economic structure, geography, freight demand or policy exposure. The tool supports investigation, not a ranking of policy success.

## Architecture and reproducibility

`run_pipeline.py` performs the existing validated transport pipeline and then builds fuel-specific market outlooks and interfaces from cached real public data. Market refresh is separate and explicit: official-page discovery → download to temporary files → schema/value/date checks → atomic cache replacement → evidence snapshot → dashboard. Invalid or older downloads retain the prior cache. Missing source/product periods, incomplete population quarters and invalid core values are rejected. Database publication is transactional.

The retained transport dashboard and Streamlit/API use the same transport briefing calculation and historical run identity. The database stores structured model results and run metadata, and its readers use one snapshot. SHA256 checks bind processed/model/diagnostic artifacts to a run before loading or building. Run identity includes raw-source hashes and relevant code/dependency-lock content; timestamps describe builds, not source observation dates.

| Output | Location |
|---|---|
| Analyst dashboard | `dashboard/index.html` |
| Interactive app / local API | `app/streamlit_app.py` / `app/api.py` |
| Processed tables / warehouse | `data/processed/` / `data/gold/warehouse.sqlite` |
| Model results and predictions | `reports/model_results/metrics.json` |
| Source/run evidence | `data/bronze/_manifest.csv`, `reports/run_metadata.json` |
| Structural quality, source age and descriptive KS drift | `reports/monitoring/drift_report.json` |
| Technical results and sample exports | `reports/evaluation/technical_results.md`, `reports/briefings/` |
| Current market diagrams | `docs/architecture/architecture_v5.png`, `docs/workflow/workflow_v5.png` |
| Daily/weekly review evidence | `reports/market_review/snapshot.json`, `reports/market_review/technical_results.md` |

The market snapshot has its own evidence and model identities plus a reference to the original historical run. The current sales backtest compares seasonal naive and Holt-Winters across 41 earlier rolling origins per fuel/state, then evaluates six held-out months. It uses the revised current extract; original historical publication vintages are not reconstructed. Adjacent evaluation windows overlap, and empirical error bands are not calibrated guarantees.

The dependency lock describes the tested environment. CI is correctly located under `.github/workflows/ci.yml`; it rebuilds from tracked government files, tests, regenerates the dashboard and uploads outputs. A local successful run is not evidence of a completed remote CI run. SQLite is the tested default; PostgreSQL/Redshift deployment is not demonstrated here.

## PRT661 Assessment 3

Use the current [19-minute FuelScope runbook](docs/assessment3/fuelscope_video_runbook.md) and [individual evidence guide](docs/assessment3/contribution_evidence_guide.md). The older v2 presentation in `docs/assessment3/presentation/` covers the retained transport analysis and needs revision before a FuelScope recording. The required submission remains a video of at most 20 minutes plus one PDF of exactly two pages per student (font size at least 10). Each student's second page needs one genuine screenshot of the specified Redshift Lab 2 with the lab name, mark and completion date/time, plus reflection.

The team must still establish progress against its actual Assessment 2 submission, conduct genuine benefit evaluation, provide truthful personal evidence and record the presentation. See [the readiness audit](reports/project_audit_2026-10-03.md) for the original defects and rationale for this revision.