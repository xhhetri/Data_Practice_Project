# Predictive Analytics and Forecasting of Australian Greenhouse Gas Emissions

A multi-source forecasting system integrating energy, transport, household, weather, commodity, and carbon-market data to predict Australian quarterly GHG emissions.

**Group:** Sydn9 – Theme 2
**Unit:** Data Science Practice (PRTG61)
**Theme:** Theme 2 – Predictive Analytics and Forecasting

---

## Overview

This project builds a reproducible framework for forecasting Australian greenhouse gas emissions by integrating electricity production, residential energy use, road transport, weather, commodity prices, carbon market signals, and policy data — rather than relying on emissions history alone.

**Research question:**
> Can Australian quarterly greenhouse gas emissions be forecast more accurately by integrating multi-source energy, transport, household, weather, commodity-price, and policy data than by using emissions history alone?

---

## Objectives

- Collect and categorize heterogeneous public data sources.
- Build a scalable, analysis-ready quarterly feature dataset.
- Evaluate models using walk-forward validation and ablation tests.
- Deliver a reproducible automated pipeline and an interactive dashboard.

---

## Data Sources

| Source | Frequency | Role / Variables |
|---|---|---|
| DCCEEW National Greenhouse Gas Inventory | Quarterly | Target: quarterly CO₂-e |
| AEMO National Electricity Market | 5-min / monthly | Demand, price, fuel mix, renewables |
| ABS Energy Account, Australia | Annual | Household/economy energy use |
| BITRE road and vehicle statistics | Monthly / annual | Registrations and vehicle-km |
| Bureau of Meteorology climate data | Daily / monthly | Temperature, rainfall, wind, solar |
| World Bank Commodity Markets (Pink Sheet) | Monthly | Oil, coal, and gas prices |
| Clean Energy Regulator QCMR | Quarterly | ACCU supply, demand, and prices |
| Existing Global Climate & Energy Transition files | Daily / event / annual | `carbon_prices_daily.csv`, `climate_events.csv`, `energy_mix_yearly.csv` (auxiliary) |

Raw data files are **not** committed to this repository (see `.gitignore`). Only scripts, schemas, and metadata needed to reproduce the processed data are version-controlled.

---

## Repository Structure

```
.
├── ingestion/        # Source acquisition scripts (API/CSV/XLSX)
├── processing/        # Cleaning, validation, resampling, feature engineering
├── models/             # Baseline, SARIMAX, and ML forecasting models
├── dashboard/       # Dashboard app and delivery layer
├── tests/                # Automated tests (run via GitHub Actions)
├── docs/
│   ├── diagrams/     # Architecture & workflow diagrams (Draw.io source + PNG exports)
│   └── planning/      # Task allocation, roadmaps, meeting notes
├── reports/          # Assessment reports (PDF + source Markdown/Word), Git-tagged per submission
└── README.md
```

---

## Pipeline / Architecture

**Flow:** Data Sources → Acquire + Storage (API/CSV/XLSX) → Process + Integrate (clean, validate, resample, engineer features) → Forecast + Deliver (baseline + ML models) → Dashboard + Report

**Storage design:** Raw CSV/XLSX/JSON → cleaned Parquet → PostgreSQL quarterly feature table.

**Stages:**
1. **Acquire** – version source data
2. **Profile** – schema, gaps, units
3. **Harmonize** – quarter and geography alignment
4. **Engineer** – lags, rolling features
5. **Model** – baseline, SARIMAX, ML
6. **Validate** – walk-forward validation, metrics (MAE, RMSE, MAPE)
7. **Explain** – ablation, SHAP
8. **Deliver** – dashboard, report

See `docs/diagrams/` for the full architecture (Figure 1) and workflow (Figure 2) diagrams.

---

## Getting Started

> Update this section once the pipeline entry point is finalized.

```bash
# Clone the repository
git clone https://github.com/xhhetri/Data_Practice_Project.git
cd Data_Practice_Project

# Install dependencies
pip install -r requirements.txt

# Run the full pipeline (single documented command)
python run_pipeline.py
```

GitHub Actions runs tests, linting, and reproducibility checks on every pull request.

---

## Models

- Seasonal-naive (baseline)
- Regularized regression
- SARIMAX
- Constrained Gradient Boosting

Deep learning approaches are excluded due to the limited sample size of the quarterly dataset. Models are evaluated using walk-forward (chronological) validation with MAE, RMSE, and MAPE.

---

## Project Management

- **Board:** GitHub Projects (Backlog → In Progress → Review → Done)
- **Milestones:** Five two-week milestones aligned to the delivery roadmap below
- **Task tracking:** Every workstream is broken into GitHub Issues with acceptance criteria, an assignee, and a workstream label
- **Definition of done:** An issue moves to Done only once its linked pull request has been reviewed and merged
- **Scope changes:** Raised as `scope-change` labelled issues, discussed at weekly stand-up, and logged with rationale

### Delivery Roadmap

| Weeks | Milestone | Evidence |
|---|---|---|
| 1–2 | Acquisition & architecture | Source audit, repo, diagrams, raw snapshots |
| 3–4 | Integration | Cleaning, schemas, quarterly feature table |
| 5–6 | Forecasting | Baselines and candidate models |
| 7–8 | Validation & visualization | Walk-forward results, ablation, dashboard |
| 9–12 | Finalization | Risk review, documentation, report, reproducible release |

---

## Team & Roles

| Role | Member |
|---|---|
| Data Lead | Bhuwan Sharma (S396374) |
| Data Engineering Lead | Mohamed Hatem Moneir Mansour Elshekh (S393891) |
| Modelling Lead | Oshan Thapa Chhetri (S395087) |
| Visualization / QA Lead | Upendra Bhandari (S396842) |
| Coordination & Reporting Lead | Vamsha Palja Tamu (S393518) |

All members participate in PR review, testing, and scope decisions.

---

## Ethics, Privacy & Security

- Only public, aggregated data is used — no identifiable records are ingested.
- Licenses and attributions for all sources are respected.
- Results are reported as **predictive, not causal**.
- NEM coverage limits (WA/NT exposure) and any synthetic Kaggle components are disclosed.
- API keys are managed via environment variables / GitHub Secrets; dependencies are pinned and inputs validated.

---

## References

- Australian Bureau of Statistics — [Energy Account, Australia](https://www.abs.gov.au/statistics/industry/energy/energy-account-australia/latest-release)
- Australian Energy Market Operator — [National Electricity Market data](https://www.aemo.com.au/energy-systems/electricity/national-electricity-market-nem/data-nem)
- Bureau of Infrastructure and Transport Research Economics — [Road statistics](https://www.bitre.gov.au/publications/2025/australian-infrastructure-and-transport-statistics-yearbook-2025/road)
- Bureau of Meteorology — [Climate Data Online](https://www.bom.gov.au/climate/data/)
- Clean Energy Regulator — [Quarterly carbon market reports](https://cer.gov.au/markets/reports-and-data/quarterly-carbon-market-reports)
- DCCEEW — [National Greenhouse Gas Inventory: Quarterly updates](https://www.dcceew.gov.au/climate-change/publications/national-greenhouse-gas-inventory-quarterly-updates)
- Nefedov, S. (2026). [Global Climate & Energy Transition 2000–2026](https://www.kaggle.com/datasets/sergionefedov/global-climate-and-energy-transition-2000-2026) [Data set]. Kaggle.
- World Bank — [Commodity Markets: Pink Sheet](https://www.worldbank.org/en/research/commodity-markets)

---

## License
