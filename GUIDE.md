# Running and demonstrating the project

FuelScope is the current daily/weekly demonstration. Start it with `Start-FuelScope.cmd` or follow [the current README](README.md), then use [the FuelScope recording runbook](docs/assessment3/fuelscope_video_runbook.md). The instructions below describe the retained transport analysis.

Use Python 3.12 from the repository root. The raw government workbooks are tracked; this pipeline reads a fixed local snapshot rather than downloading live releases.

## Setup and build

On Windows:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.venv\Scripts\python.exe run_pipeline.py
.venv\Scripts\python.exe -m pytest tests/ -q
```

On macOS/Linux:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python run_pipeline.py
.venv/bin/python -m pytest tests/ -q
```

No `.env` is required for the default SQLite database. If customizing settings, copy `.env.example` to `.env`; that file is ignored by Git. The documented local services run on loopback. The optional environment variables do not automatically change the explicit launch arguments below.

The build reads workbooks, so allow time for parsing and model evaluation. A successful final message is required; do not infer completion from partially updated files. Read the displayed observation cutoffs and run identifier before citing figures.

## Standalone interface

Open `dashboard/index.html` in a browser with `dashboard/plotly.min.js` beside it. Or serve the dashboard folder locally:

```powershell
.venv\Scripts\python.exe -m http.server 8765 --bind 127.0.0.1 --directory dashboard
```

Open `http://127.0.0.1:8765`. Select a jurisdiction and start/end financial years. Download a Markdown briefing and CSV, and open them to verify sources, units and the selected period. The sales outlook uses the latest sales cutoff; changing the annual comparison does not change its training window.

## Streamlit and API

In separate terminals:

```powershell
.venv\Scripts\python.exe -m streamlit run app/streamlit_app.py --server.address 127.0.0.1 --server.port 8501 --server.headless true
.venv\Scripts\python.exe -m uvicorn app.api:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8501` and `http://127.0.0.1:8000/docs`. Use `.venv/bin/python` on macOS/Linux. Stop services with Ctrl+C when finished.

Useful API routes:

| Route | Purpose |
|---|---|
| `GET /health` | Database readiness, run identifier and cutoffs |
| `GET /states` | Available jurisdictions |
| `GET /briefing?state=NSW&start_year=2016&end_year=2023` | Shared numeric summary and cited Markdown export |
| `GET /forecast/NSW` | Earlier candidate scores, holdout, next-six-month sales outlook and bands |
| `GET /provenance` | Sources, hashes, dates and package versions |
| `GET /metrics` | Flattened recorded metrics; optional `result_group` filter |
| `GET /monitoring/drift` | Same-run quality/freshness/descriptive drift report |
| `POST /predict` | Associative annual estimate only; positive finite inputs within observed feature ranges |

The API and Streamlit read the database's full structured result snapshot. The scoring model must match the database run's hash. Unknown periods/states and impossible/out-of-range inputs are rejected. Services are local prototypes; public hosting/authentication has not been demonstrated.

## Verification before recording

1. Build and run the full tests. Check every process exits successfully.
2. Repeat `python scripts/build_dashboard.py` using the environment's interpreter; mismatched artifacts should be rejected.
3. Compare the static interface's run identifier with `/health` and `reports/run_metadata.json`.
4. Select NSW FY2016-17→FY2023-24 in both interfaces and compare one total value, percentage change and per-capita value.
5. Download and inspect both exports. Confirm the final-year label is financial-year based, forecast months follow the sales cutoff, and sources/limits are present.
6. Show source-age/quality status. `no_drift` does not prove model accuracy; pooled KS comparisons are descriptive.
7. Use `docs/assessment3/demo_runbook.md` and rehearse within 19 minutes before recording the final video.

## Refreshing sources and handling failures

Replace the relevant raw source only after reviewing its published structure and boundary. Source lookup currently prefers the most recently modified real workbook in recognized folders; remove ambiguity deliberately rather than dropping multiple alternative vintages into one folder. Keep the original file and retrieval evidence in the team's data record. Run the entire pipeline again; do not refresh only the model, database or HTML and call it the same completed run.

A structural quality failure prevents database publication. A database reload interruption rolls back to the prior snapshot. Disk analysis files may already have changed when a build fails, so static and database views can still represent the last completed run until a complete rebuild succeeds. Check run identifiers rather than assuming every file is current. Dashboard generation rejects changed core artifacts; the monitoring API rejects a report from a different database run.

If the app has no data, build the pipeline. If exports/models do not match a run, rebuild rather than editing metadata manually. Streamlit caches a snapshot for up to 10 seconds; wait for a rerun after a rebuild. If a port is busy, select another explicit local port. SQLite is the tested database; an optional other SQLAlchemy URL requires a compatible driver and separate verification.

The persistent drift baseline is `reports/monitoring/reference_annual_master.csv`. Rebaseline only after reviewing an expected source change. Current source freshness describes observation age, not missing retrieval dates or a live feed.

## Before submission

The generated deck and runbook support the group demonstration, but do not replace the video. Supply actual presenter names/contributions and compare against the submitted Assessment 2 version. Follow `contribution_evidence_guide.md` to make one PDF containing exactly two pages per student, with one genuine specified Redshift Lab 2 screenshot on each student's second page. Conduct the planned pilot before asserting measured time savings or user benefit.
