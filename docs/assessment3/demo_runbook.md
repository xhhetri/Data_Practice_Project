# PRT661 Assessment 3: 19-minute technical demonstration

The current default demonstration is FuelScope. Use [the updated market-review recording runbook](fuelscope_video_runbook.md). The retained sequence below documents the original transport briefing workflow, which remains accessible through the dashboard link.

Based on the assessment brief supplied by the team. The supplied document specifies submission requirements rather than an HD grade-band rubric. This preparation supports a strong submission; it cannot establish or guarantee a grade.

## Preparation

Build the project, run the tests, and record the run identifier. Open `dashboard/index.html`, the Streamlit app, the generated technical results report and the updated architecture/workflow figures. Keep the same data snapshot throughout the recording. Prepare a downloaded NSW briefing as a fallback if a live app fails. Disable unrelated notifications and verify readable capture/audio. Check the final recording's actual duration and video-link access before submission.

Each person should explain work they actually understand and performed. Assign presenters using the team's real contribution record; no role allocation or authorship is invented here.

## Timed sequence

| Time | Topic | Evidence to show |
|---|---|---|
| 0:00–1:15 | User problem and objective: prepare a correct, cited state briefing | Intended analyst task; research question and measurable benefit criteria |
| 1:15–2:30 | Scope and source boundaries | Whole-transport inventories vs petrol + total diesel sales; ACT exclusion; FY and calendar-stock alignment |
| 2:30–4:00 | Updated architecture | Bronze/Silver/Gold, models, quality gate, SQLite, shared calculations, static/Streamlit/API outputs |
| 4:00–5:00 | Workflow and progress | One-command build and run metadata; verified comparison against the actual Assessment 2 submission |
| 5:00–8:30 | Complete briefing task | NSW, FY2016-17→FY2023-24; total/per-capita values, peer comparison, annual evidence table, cited Markdown and CSV exports |
| 8:30–11:30 | Forecast demonstration | Selected method; earlier candidate comparison; final Jan–Jun 2026 holdout; Jul–Dec 2026 outlook; interval coverage and source lag |
| 11:30–13:00 | Annual ML evaluation | Whole-year chronological folds, previous-year baseline, per-state errors, actual same-year covariates and association caveat |
| 13:00–14:30 | Technical challenges and safeguards | Historical fleet repair, unresolved signed reconciliation, missing-quarter/product gates, failed database reload rollback |
| 14:30–16:00 | Evidence of implementation | Fresh tests, repeat build, matching run identifiers across API/database/static app; corrected CI path, locked dependencies |
| 16:00–17:30 | Benefit evaluation | Counterbalanced pilot tasks, identical data in both conditions, timed completion and interpretation-error measures; current evidence status |
| 17:30–19:00 | Future work before Assessment 4 | Conduct pilot, revise observed usability failures, investigate data-boundary reconciliation, refresh sources and review uncertainty under structural change |

One minute remains below the 20-minute maximum. Rehearse; shorten narration if needed.

## Live demonstration checklist

1. Select NSW and FY2016-17→FY2023-24. Read the headline and units, then switch total/per-person trends. Explain the denominator and peer comparison.
2. Expand the evidence table. Download the briefing and selected CSV; open the briefing and show its source links, cutoffs, limits and run identifier.
3. Open Fuel-sales outlook. Show that annual filters do not select the forecast training period. Distinguish observed sales, held-out predictions and after-cutoff months. State that some after-cutoff months may already precede today.
4. Show the earlier candidate scores and held-out score. Explain why a simpler method can be selected. Open evaluation dates and interval coverage; do not call empirical bands guaranteed probabilities.
5. Open Methods & sources. Show selected-state annual errors and the unresolved sales/inventory diagnostic. Explain which quantity is safe to cite for emissions.
6. Demonstrate the same state/range in Streamlit or `/briefing`; compare the run identifier and one numeric value. API docs are at `http://127.0.0.1:8000/docs` when the service runs.

## What must be completed by the team

- Compare this revision against the actual Assessment 2 submission. The starting Git revision is an implementation baseline, not proof of what was submitted for Assessment 2.
- Supply actual group names, student IDs, speaking allocations, contribution links and next-work commitments.
- Conduct and report real participant sessions before making benefit claims. Until then show the protocol as future work.
- Record and submit a video link no longer than 20 minutes. A deck or this runbook does not replace the video.
- Compile the exact two-pages-per-student individual PDF using the evidence guide. Verify readability and clickable links.
