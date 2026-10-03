# Upgrade verification — 3 October 2026

The implemented release supports a complete, source-backed state briefing task. The participant benefit evaluation and assessment submissions remain team work; no participant results, lab evidence, student authorship or grade are invented.

## Verified release

- Branch: `feature/useful-briefings`; starting revision: `f8fb27fa8a1eb9eabbde80ab9121df71d9b97b3a`. Changes are local and uncommitted.
- Pipeline run: `982d7cbfcc4474d3`, built at `2026-10-03T10:38:50.605958+00:00`.
- Source and core output hashes: `reports/run_metadata.json`. Real government inputs; 98 annual state-years and 1,344 monthly observations across seven jurisdictions.
- Inventory period: FY2010-11–FY2023-24; fuel-sales cutoff: June 2026. ACT is excluded from the comparison.

## Executed checks

| Check | Observed result |
|---|---|
| Full pipeline | Completed successfully: processed data, models, validation diagnostic, provenance, pre-publication quality gate, database, dashboard, diagrams and technical evidence |
| Full Python test suite | 55 passed, two warnings, 106.59 seconds |
| Repeat dashboard build | Completed successfully against the verified output hashes and run identity |
| Dashboard export handler check | Passed using the generated dashboard; NT FY2020-21–FY2023-24 Markdown and four-row CSV include the expected selection, units and run identity |
| Actual static-dashboard downloads | Both downloaded files inspected: `NT-briefing-2020-2023.md` and `NT-evidence.csv`; matching values and run identity |
| API integration | Healthy current snapshot; matching metadata/briefing values; valid association request succeeds; invalid states, inverted dates and negative inputs rejected; missing forecast returns 404 |
| Streamlit application test | Actual app runs without exceptions and switches to NT; state briefing and both download controls present |
| Browser inspection | Static dashboard tabs, selection, sources, forecasts, evidence and exports inspected; Streamlit NSW FY2016-17–FY2023-24 displays matching totals, per-person change and run identifier |
| Editable presentation | 14 slides with notes, four native tables and one native chart with embedded workbook; package, layout, font-policy, import and native-chart checks pass; rendered slides visually inspected |

The warnings concern Starlette's deprecated httpx adapter and an explicitly handled non-convergent optimizer on a synthetic forecast test. All seven real-data Holt-Winters fits converged in the full pipeline.

The presentation SHA256 is `002d0d05c003788a15e95a0d30444cd22c3af23df8afe95ec97b2d3c019b3f90`. The final file is `docs/assessment3/presentation/PRT661_Technical_Demonstration_v2.pptx`. Native PowerPoint execution was not tested. Linux GitHub Actions execution has not been observed; the corrected workflow is prepared locally. Streamlit's download controls were activated in the in-app browser, but completed native downloads could not be captured there; use the independently verified static dashboard for the recorded export demonstration and rehearse Streamlit downloads in the team's browser if presenting them.

Browser preview: `reports/evaluation/dashboard_verified.jpg`.

## Independent review and fixes

A separate reviewer examined the implementation. Material findings were corrected and covered by failing-then-passing checks:

1. Failed input quality now stops publication before database replacement. Database preflight rejects incomplete data and rollback preserves the preceding usable snapshot.
2. Population requires four unique quarters for each state/year and complete, positive annual denominator coverage.
3. Monthly fuel aggregation requires exactly gasoline and diesel oil with no duplicate product rows, rather than silently summing a missing product.
4. Release checks require the expected seven jurisdictions and complete monthly/annual periods.
5. Forecast uncertainty coverage and the same-holdout seasonal-naive comparison now appear in the exports and database app.

The reviewer confirmed these concrete findings were addressed. This review does not constitute independent validation of the government accounting methodologies.

## Scientific conclusions and remaining evidence

The annual previous-year baseline has lower pooled MAE (494.10 kt CO2-e) than linear regression (541.88) and random forest (563.22). The project reports that result, describes the regression as a contemporaneous association, and avoids claiming causal or operational forecasting value from its high pooled R².

Fuel model selection uses 21 earlier rolling windows and a separate final six-month holdout. Selected Holt-Winters underperforms the same-holdout seasonal-naive baseline for NSW and QLD. Empirical 80/95% bands and actual held-out coverage are disclosed; six observations cannot establish calibration.

Sales-based implied emissions exceed the official inventory in 93 of 98 state-years. The mean absolute gap is 29.71%. Different fuel-sales and transport-inventory boundaries remain unresolved; this is an investigation diagnostic, not a passed inventory validation. Official inventory figures drive the emissions briefing. Historical calendar-year fleet stock is associated with the financial year beginning in that year as a disclosed approximation.

Before strong benefit claims and final assessment submission, the team must:

- Run the genuine counterbalanced pilot in `docs/evaluation/pilot_protocol.md`, report completion, timing and interpretation errors, and fix observed usability failures.
- Compare against the actual Assessment 2 submission and provide genuine individual contribution links and work reflections.
- Provide each student's specified Lab 2 screenshot and compile exactly two pages per student, with minimum font size 10.
- Rehearse and record the group demonstration, verify the final video is no longer than 20 minutes, and check access to the submitted video link.

The supplied Assessment 3 brief is a submission specification, not a high-distinction grade-band rubric. The working system and prepared evidence improve readiness; a grade is not established by this verification.
