# Step-by-Step Guide — Setup, Run, DBMS & Tools

This guide covers everything needed to run this project locally end to
end: environment setup, which database to use and why, how to run the
pipeline / dashboard / API / monitoring, and which other applications
are worth installing alongside it — mapped to the 8-stage data science
lifecycle this project follows.

Everything below runs **entirely on your own machine**. Nothing here
pushes to GitHub or touches the original repo.

---

## 1. Prerequisites

| Tool | Why | Check you have it |
|---|---|---|
| Python 3.11 or 3.12 | Runs everything in this project | `python3 --version` |
| pip | Installs dependencies | `pip --version` |
| git | Only needed if you want version history locally | `git --version` |
| A code editor | VS Code recommended (free, great Python + SQLite extensions) | — |

You do **not** need to install a separate database server for the
default setup — see Section 3.

---

## 2. Environment setup

```bash
# 1. Unzip the project folder you were given, then cd into it
cd Data_Practice_Project

# 2. Create an isolated Python environment (keeps this project's
#    packages separate from anything else on your machine)
python3 -m venv .venv

# 3. Activate it
source .venv/bin/activate        # macOS/Linux
# .venv\Scripts\activate         # Windows (Command Prompt / PowerShell)

# 4. Install all dependencies
pip install -r requirements.txt

# 5. Create your local config file from the template
cp .env.example .env
```

Open `.env` in your editor. The defaults work as-is for a first run —
you only need to change anything if you want to switch to Postgres
(Section 3) or change a port that's already in use on your machine.

---

## 3. Which DBMS to use

**Use SQLite — it's already the default, no action needed.**

| | SQLite (default) | Postgres (optional upgrade) |
|---|---|---|
| Setup | None — it's a single file, ships with Python | Install Postgres, or run one line of Docker |
| Good for | One person, a laptop, a project this size | A shared team DB, concurrent writers, production-like setup |
| Where data lives | `data/gold/warehouse.sqlite` (one file) | A running Postgres server |
| Config | Nothing to do | Set `DATABASE_URL` in `.env` |

For this project — a solo run or a small team pipeline, not a
production system with concurrent users — **SQLite is the right
choice**, not a simplification you'll need to "graduate" from. The
project's `src/db.py` is written against SQLAlchemy, so if you ever do
need Postgres (e.g. your team wants one shared database everyone reads
from), it's a one-line config change, not a rewrite:

```bash
# Only if you want Postgres instead of SQLite:
docker run -d --name transport-emissions-db -p 5432:5432 \
  -e POSTGRES_PASSWORD=postgres postgres:16

# Then in .env:
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/transport_emissions

# And uncomment this line in requirements.txt, then re-run pip install:
# psycopg2-binary>=2.9
```

**To look inside the database** (either engine), pick one:
- Command line: `sqlite3 data/gold/warehouse.sqlite ".tables"` (SQLite only, no install needed on macOS/Linux)
- A GUI browser: **DB Browser for SQLite** (free, sqlitebrowser.org) for SQLite, or **DBeaver** (free, works with both SQLite and Postgres) — recommended if you'd rather click through tables than type SQL.

---

## 4. Running the project

Make sure your virtual environment is activated (`source .venv/bin/activate`) before every step below.

### 4.1 Run the full pipeline

```bash
python run_pipeline.py
```

This runs, in order: clean & merge source data → exploratory data
analysis → train & evaluate models → data-quality validation → **load
everything into the DBMS**. Takes a few minutes on real data. Outputs land in:

| Output | Location |
|---|---|
| Cleaned tables | `data/processed/*.csv` |
| EDA figures | `reports/figures/*.png` |
| Model metrics + trained model | `reports/model_results/` |
| Validation checks | `reports/validation/` |
| **Database** | `data/gold/warehouse.sqlite` |

### 4.2 Run the automated tests

```bash
pytest tests/ -v
```

30 tests (~3–4 minutes): 24 for the data pipeline, 6 for the new
database/monitoring code.

### 4.3 Run the interactive dashboard (Streamlit)

```bash
streamlit run app/streamlit_app.py
```

Opens automatically in your browser at `http://localhost:8501`. Tabs:
Historical trends, Monthly fuel, Models, and Monitoring. Reads live
from the database, so run 4.1 first if any tab looks empty. Press
`Ctrl+C` in the terminal to stop it.

### 4.4 Run the scoring API (FastAPI)

```bash
uvicorn app.api:app --reload --host 0.0.0.0 --port 8000
```

Then open `http://localhost:8000/docs` in a browser — an interactive
page where you can try every endpoint by clicking "Try it out," no
separate tool needed. To test from the command line instead:

```bash
curl http://localhost:8000/health
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"fuel_consumption_ml": 10000, "vkt_road_million_km": 70000, "registered_vehicles": 6000000}'
```

Press `Ctrl+C` to stop it. If you'd rather use a GUI than curl, install
**Postman** (free) or use the VS Code **REST Client** extension.

### 4.5 Run the data-drift monitoring check

```bash
python monitoring/monitor.py
```

First time you run this, it saves today's data as the baseline to
compare future runs against. Run it again any time after re-running
the pipeline with new data to see whether anything drifted — the
result also shows up in the Streamlit dashboard's Monitoring tab and at
the API's `/monitoring/drift` endpoint.

### 4.6 Regenerate the static dashboard (optional, unchanged from before)

```bash
python scripts/build_dashboard.py
```

Then just open `dashboard/index.html` directly in any browser — no
server needed for this one.

### 4.7 Run the notebook (optional)

```bash
pip install jupyter   # if not already installed
jupyter notebook src/analysis/analysis.ipynb
```

---

## 5. Recommended applications, mapped to the project lifecycle

The diagram this project follows has 8 stages. Here's what's already
wired up in this repo for each, and what else is worth having installed
locally:

| Stage | Already in this repo | Extra apps worth having |
|---|---|---|
| 1. Problem understanding | `README.md`, `CHANGELOG.md` | A code editor (VS Code) to read/write markdown |
| 2. Data acquisition | `data/bronze/` (downloaded government files) | A browser, for re-downloading source files if needed |
| 3. Data preparation | `src/analysis/clean.py` | — |
| 4. Exploratory data analysis | `src/analysis/eda.py`, `src/analysis/analysis.ipynb` | **Jupyter** (`pip install jupyter`) for interactive exploration |
| 5. Modelling | `src/analysis/model.py` | — |
| 6. Evaluation & interpretation | `src/analysis/validate.py`, **`src/db.py`** (new) | **DBeaver** or **DB Browser for SQLite** to inspect `model_metrics` |
| 7. Deployment & visualization | `dashboard/index.html` (static) + **`app/streamlit_app.py`** and **`app/api.py`** (new) | **Postman** for exercising the API by hand |
| 8. Monitoring & improvement | **`monitoring/monitor.py`** (new) | Nothing extra needed — this project's monitoring is dependency-light on purpose (see the note in `monitoring/monitor.py` about Evidently AI as an optional, heavier alternative) |

Everything marked **(new)** is what this update adds on top of the
repo as you found it — the previous version stopped at Stage 6
(Evaluation), with the pipeline's output living only in loose CSV/JSON
files, no database, dashboard app, API, or monitoring.

---

## 6. Everyday workflow, once set up

```bash
source .venv/bin/activate     # every new terminal session
python run_pipeline.py        # after any change to data or code
python monitoring/monitor.py  # check for drift after re-running the pipeline
streamlit run app/streamlit_app.py   # in one terminal, for browsing results
uvicorn app.api:app --reload --port 8000   # in another terminal, if serving the API
```

## 7. Troubleshooting

- **"No module named X"** — your virtual environment isn't activated, or
  `pip install -r requirements.txt` hasn't been re-run since this
  update. Re-run both.
- **Dashboard/API says tables are empty** — run `python run_pipeline.py`
  first; both apps read from the database, not the raw source files.
- **Port already in use** (8501 or 8000) — change `STREAMLIT_PORT` /
  `API_PORT` in `.env`, or pass `--server.port` / `--port` directly on
  the command line.
- **Want to start the database over** — delete
  `data/gold/warehouse.sqlite` and re-run `python run_pipeline.py`; it
  gets recreated automatically.
- **Want to re-baseline monitoring** — delete
  `reports/monitoring/reference_annual_master.csv` and re-run
  `python monitoring/monitor.py`.
