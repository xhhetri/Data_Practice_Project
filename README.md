# Data_Practice

**Project:** Predictive Analytics and Forecasting of Australian Greenhouse Gas Emissions
**Unit:** Data Science Practice (PRTG61)
**Status:** Currently entering Week 5 (Acquisition & Integration phases complete per Table 3)

## Suggested Role Assignments (from Table 2 workstreams)

| Role | Assigned To | Accountable For |
|---|---|---|
| Data Lead | Bhuwan Sharma (S396374) | Ingestion, data dictionary, provenance, licensing |
| Data Engineering Lead | Mohamed Hatem Moneir Mansour Elshekh (S393891) | Storage, validation, joins, pipeline automation |
| Modelling Lead | Oshan Thapa Chhetri (S395087) | Baseline/SARIMAX/ML models, walk-forward evaluation |
| Visualization & QA Lead | Upendra Bhandari (S396842) | Dashboard, documentation, final QA |
| Coordination & Reporting Lead | Vamsha Palja Tamu (S393518) | GitHub Projects board, milestones, report assembly |
| **All members** | Everyone | PR review (1 approval minimum before merge), weekly stand-up, scope-change log |

*Adjust names to actual preference — this maps 1:1 onto your Table 2 roles plus a 5th coordination role for board/report ownership, since Table 2 lists "All members" for review only.*

---

## Weeks 1–4 (Completed — for reference)

| Week | Milestone | Evidence |
|---|---|---|
| 1–2 | Acquisition & architecture | Source audit, repo scaffolding, Figure 1/2 diagrams, raw snapshots |
| 3–4 | Integration | Cleaning scripts, schemas, quarterly feature table in PostgreSQL |

---

## Weeks 5–12 (Forward Plan)

### Week 5 — Baseline Modelling
**Lead:** Modelling Lead | **Support:** Data Engineering Lead
- Finalize quarterly feature table (lags, rolling windows for electricity/transport/weather/commodities).
- Build Seasonal-naive and regularized regression baselines.
- Set up walk-forward validation harness (chronological splits, no leakage).
- **GitHub:** Issues for each model type; Milestone "Forecasting" opened.
- **Report:** Draft Section — "Baseline Modelling Approach."

### Week 6 — Candidate Models
**Lead:** Modelling Lead | **Support:** Data Lead (variable interpretation)
- Implement SARIMAX and constrained Gradient Boosting candidates.
- Run first-pass MAE/RMSE/MAPE comparisons against baselines.
- Document publication-aware lag choices to guard against temporal leakage (Risk table item).
- **GitHub:** PRs reviewed by at least one teammate; merge only after review.
- **Report:** Draft Section — "Candidate Models & Rationale."

### Week 7 — Walk-Forward Validation
**Lead:** Modelling Lead | **Support:** Visualization/QA Lead
- Run full walk-forward validation across all candidate models.
- Begin ablation tests (remove one data source group at a time: electricity, transport, weather, commodities, carbon market).
- Log results in a reproducible results table (CSV + notebook).
- **GitHub:** Milestone "Validation & visualization" opened; issues per ablation test.
- **Report:** Draft Section — "Validation Methodology."

### Week 8 — Ablation & Model Selection
**Lead:** Modelling Lead | **Support:** All members (review)
- Complete ablation analysis; identify which data sources add genuine predictive value.
- Select final model(s) for the dashboard/report based on walk-forward performance.
- Address geographic mismatch risk (NEM vs national coverage) in write-up.
- **GitHub:** Close "Forecasting" and "Validation" milestone issues.
- **Report:** Draft Section — "Results & Ablation Findings."

### Week 9 — Dashboard Build
**Lead:** Visualization/QA Lead | **Support:** Data Engineering Lead
- Build dashboard (forecast vs actual, scenario toggles, source contribution view).
- Connect dashboard to the quarter feature table / model outputs.
- QA pass: check chart accuracy, labels, units, refresh reliability.
- **GitHub:** Diagrams updated (Draw.io → PNG) if architecture changed since Figure 1/2.
- **Report:** Draft Section — "Dashboard & Delivery Design," with screenshots.

### Week 10 — Report Drafting & Integration
**Lead:** Coordination & Reporting Lead | **Support:** All members
- Assemble full report draft: Overview → Methods → Results → Ablation → Dashboard → Ethics/Risk.
- Each lead reviews and edits their own section for accuracy.
- Update README with links to latest dashboard and report.
- **GitHub:** Report PDF + source Markdown/Word tagged with a Git release.
- **Report:** First complete full-draft assembled.

### Week 11 — Review, QA & Risk Revisit
**Lead:** Visualization/QA Lead | **Support:** Coordination Lead
- Full QA pass on report (consistency, references, figures) and on the codebase (reproducibility check — one-command pipeline run end-to-end).
- Revisit Table 4 risks: confirm mitigations actually held (e.g., no leakage found, schema stable).
- Peer review round: every section gets at least one non-author review.
- **GitHub:** Reproducibility check via GitHub Actions on final PR.
- **Report:** Incorporate reviewer feedback; near-final draft.

### Week 12 — Finalization & Submission
**Lead:** All members (joint) | **Coordination:** Coordination & Reporting Lead
- Final proofread, formatting, and reference check (APA, per your reference list style).
- Tag final Git release matching submission date.
- Confirm ethics/privacy statement and licensing attributions are current.
- Submit report + working dashboard link + repository link.
- **GitHub:** Close all remaining Milestone issues; board moved to "Done."
- **Report:** Final submitted version.
