# Project readiness and usefulness audit

**Project:** Australian transport emissions decision support  
**Assessment:** PRT661 Data Science Practice, Assessment 3  
**Reviewed:** 3 October 2026, local revision `f8fb27f`  
**Basis:** the assessment brief supplied in chat, source code, raw workbooks, saved outputs, SQLite database, Git history, and browser inspection. The full marking rubric and Assessment 2 submission were not supplied, so this is a readiness assessment, not a predicted mark.

## Overall judgement

The project has a substantial analytics foundation but does not yet establish that its decision support is reliable or useful to a defined user. Its strongest route to a high distinction is to demonstrate one complete, trustworthy task and provide evidence that the task is easier or more accurate than the user's current process.

The immediate priorities are correctness and reproducibility, followed by a usable analyst workflow and honest evaluation. Additional technologies would contribute less than resolving the contradictions already present.

Assessment 3 is a progress demonstration, not a requirement to finish the entire final product. Demonstrate a coherent working slice, show meaningful changes since Assessment 2, explain challenges with evidence, and identify credible work before Assessment 4. The individual summary accounts for 15 of the 30 marks and deserves the same preparation as the group presentation.

## What is already valuable

- Seven named government data sources resolve to raw files. The current source manifest exists.
- The stored annual table contains 98 observations: seven jurisdictions across FY2010-11 to FY2023-24. ACT is excluded from the merged table because the selected fuel source lacks a separate ACT series.
- The monthly petrol-plus-diesel sales table contains 1,344 observations: 192 months per jurisdiction, July 2010 to June 2026.
- Financial-year alignment, population normalization, data processing modules, a SQLite database, a forecast experiment, an API, and two dashboard surfaces are implemented.
- The static dashboard renders charts and supports state and metric selection in the browser.
- Existing tests and multi-author Git history provide a starting point for quality assurance and individual contribution evidence.
- The documentation already recognizes that a near-perfect emissions regression is not, by itself, a novel predictive achievement.

These assets are worth retaining. SQLite is adequate for the present scale. The brief does not require deploying the project to Amazon Redshift; the required lab reflection should explain actual transferable learning.

## Confirmed findings, ordered by impact

| Priority | Finding and evidence | Why it matters | Required response |
|---|---|---|---|
| P1 | The emission-factor explanation has the wrong direction. In `reports/validation/emission_factor_check.csv`, implied emissions exceed reported transport emissions in **93 of 98** observations. The mean absolute gap is **29.71%**. `src/analysis/validate.py:113` logs that implied emissions run below reported emissions; `dashboard/template.html:560` explains the gap by omitted non-road modes. | The product supplies an explanation contradicted by its own results. Users could draw an incorrect conclusion about emissions coverage. | Preserve signed differences, investigate comparable activity boundaries, and replace the unsupported explanation. Treat this as an unresolved reconciliation diagnostic until the methods agree. |
| P1 | `src/analysis/silver.py:157` selects **total diesel sales**, not road-only diesel consumption. The official petroleum statistics describe petroleum product sales. Diesel is also used in mining and agriculture, as the department explicitly states. | Petrol plus total diesel sales cannot automatically be labelled road fuel consumption or converted into a validated road emissions inventory. The selected NGA factors also represent cars/light commercial vehicles rather than a proven whole-fleet mix. | Distinguish sales, end-use consumption, whole-transport emissions, and physical fuel factors. Validate the boundary and factor choice before calculating transport-specific savings. The direction of the discrepancy is consistent with a boundary mismatch, but its full cause has not been established. |
| P1 | The current pipeline and saved CSVs use a **2025 vehicle fleet snapshot repeated across all 14 historical years**, confirmed by rebuilding the annual table from raw sources without writing outputs. Each state's vehicle column has one distinct value. The embedded HTML instead contains 14 varying values, and README claims a historical BITRE series. | The dashboard, model and documentation represent different versions of the data. Using current fleet size for earlier years also uses information unavailable at the historical date. | Source the genuine historical series from the existing BITRE workbook, define its annual alignment, and regenerate all dependent artifacts together. If retained only as a snapshot, label it and exclude it from historical predictive evaluation. |
| P1 | The static dashboard reports regression R² **0.9966** and random-forest MAE **368.81 kt**. The saved metrics and database report R² **0.9949** and MAE **456.21 kt**. | A presenter cannot substantiate a single result consistently across the system. | Use one versioned run for tables, models, metrics, database and dashboard. Show the run identifier and data cutoff. |
| P1 | Calling the existing builder's `build_data()` reproduces **`KeyError: 'series'`**. `scipts/buld_dashboard.py:76` expects forecast series, but `src/analysis/model.py` returns metrics without those series. Independently, `build_html({})` reproduces **`ValueError`** because the template lacks the required data placeholder and already contains embedded data. | The visible dashboard is a saved artifact that cannot currently be rebuilt by the documented process. | Establish an explicit forecast output contract, restore a true template, and verify regeneration from the current pipeline. |
| P1 | Documented paths `app/streamlit_app.py`, `scripts/build_dashboard.py`, and `scripts/generate_diagrams.py` do not exist. Actual paths are misspelled. The supposed diagram generator is byte-for-byte identical to the dashboard builder. The CI file is tracked under `github/workflows/ci.yml`, without the leading dot. | Teammates and assessors following the guide encounter failures. The checked-in CI file is outside GitHub Actions' required directory. | Correct names and instructions, provide a working diagram generator, place CI in `.github/workflows`, and produce a fresh successful run as evidence. |
| P1 | There is no identified stakeholder, observed user problem, end-to-end decision task, or user evaluation in the reviewed materials. Current screens primarily expose charts, model metrics and technical monitoring. | The project does not yet demonstrate the benefit asserted by “decision support.” | Identify a user, validate a recurring task, add a task output, and measure its benefit. |
| P2 | Regression uses shuffled five-fold cross-validation on state-year rows (`model.py:95`) and contemporaneous fuel/VKT inputs. Its 98 rows are repeated observations of seven states, not 98 independent contexts. | This is not evidence of future forecasting ability. State size, temporal dependence and feature availability can dominate pooled scores. | Evaluate by whole-year blocks and, if geographic generalization is claimed, leave out entire states. Define when inputs become available. Report per-state errors and simple baselines. |
| P2 | Fuel forecast evaluation uses one six-month holdout. The visible forecast dates are **January-June 2026**, which are already observed. No future forecast beyond June 2026 or prediction interval is emitted by the current model function. | The forecast display demonstrates a backtest; it does not provide an operational planning forecast or its uncertainty. | Separate historical evaluation from an actual future forecast. Refit after evaluation, forecast a justified horizon, and evaluate interval coverage. |
| P2 | The architecture image depicts a single flat pipeline and omits the rebuilt Bronze/Silver/Gold modules, database, API and applications. The workflow diagram still ends in Assessment 2 and assumes CI operates. | Assessment 3 explicitly asks for updated architecture and workflow. | Draw the actual executed paths, distinguish static from live surfaces, and show monitoring as a separate step unless it is integrated. |
| P2 | Monitoring compares pooled historical columns with a reference snapshot. It does not assess source freshness, missing monthly periods, state-specific failures, or realized forecast error. | A healthy status can conceal the operational problems that matter to a user. | Prioritize data completeness, freshness, schema checks and forecast outcomes. Keep distribution checks as supporting diagnostics. |

Official context for the fuel boundary: [Australian Petroleum Statistics](https://www.energy.gov.au/energy-data/australian-petroleum-statistics) describes the source as product sales; [DCCEEW's fuel security explanation](https://www.dcceew.gov.au/energy/security/australias-fuel-security/minimum-stockholding-obligation) identifies diesel use across transport, mining and agriculture. This supports investigating the boundary mismatch; it does not prove the proportion of each state's excess attributable to any particular sector.

GitHub documents the required workflow directory in its [workflow documentation](https://docs.github.com/en/actions/concepts/workflows-and-actions/workflows).

## Does the model currently add value?

### A simple fuel forecasting benchmark

I calculated a seasonal-naive benchmark directly from the stored monthly table: predict January-June 2026 using the same months of 2025. The comparison below uses **saved Holt-Winters metrics**, not a fresh fit of that model.

| State | Same month last year: MAPE % | Saved Holt-Winters: MAPE % | Lower error at displayed precision |
|---|---:|---:|---|
| NSW | 3.09 | 3.84 | Seasonal naive |
| NT | 16.32 | 12.92 | Holt-Winters |
| QLD | 4.63 | 5.68 | Seasonal naive |
| SA | 4.53 | 4.53 | Approximately equal |
| TAS | 5.89 | 4.71 | Holt-Winters |
| VIC | 3.65 | 3.45 | Holt-Winters |
| WA | 4.46 | 2.71 | Holt-Winters |

The existing method does not uniformly improve on a trivial baseline. This is a useful research finding, not a reason to conceal the benchmark. Select methods using multiple historical evaluation windows and report when the simpler method is preferable. [Forecasting: Principles and Practice](https://otexts.com/fpp3/simple-methods.html) explains these benchmark methods; its [time series cross-validation chapter](https://otexts.com/fpp3/tscv.html) explains rolling evaluation.

### Why pooled emissions R² is insufficient

As a separate diagnostic, I fitted an ordinary least-squares model to the stored FY2010-11 to FY2020-21 rows, using the same three features, and evaluated the 21 rows for FY2021-22 to FY2023-24. This is an illustrative chronological holdout, not a rerun of the project's sklearn cross-validation.

- Linear regression using actual same-year covariates: pooled R² **0.9937**, MAE **585.38 kt**, MAPE **9.10%**.
- Previous year's observed emissions as a one-year benchmark: MAE **566.08 kt**, MAPE **3.66%**.
- Linear-model MAPE reaches **34.13% for NT** and **14.11% for TAS**, despite the impressive pooled R².

The previous-year benchmark uses each preceding observed year, so this is not a fixed three-year forecast-origin comparison. The regression also has the favorable advantage of actual contemporaneous inputs; those would not generally be known for a true future forecast. The result shows why per-state errors, timing and baselines matter. It does not establish a final model ranking.

The project's feature set is small, correlated and partly used in emissions accounting. Demonstrate useful forecasting or workflow improvement rather than claiming novelty from rediscovering an accounting relationship. Changing fuel or vehicle inputs in a random forest does not establish the causal effect of an intervention.

## Recommended useful product

**Working concept: Australian state transport emissions briefing tool.**

**Primary user:** a state-level transport or climate analyst preparing a recurring briefing. This is a proposed user to validate, not an established project stakeholder. State aggregate data supports this scope better than local fleet, council or route decisions.

**Job:** “Help me identify important changes in my jurisdiction, compare them fairly with peers, understand how reliable the evidence is, and produce a traceable briefing without manually joining government spreadsheets.”

**Concrete benefit to test:** reduce preparation time and interpretation errors while improving source traceability. Avoid claiming that use of the dashboard itself reduces emissions; actual emissions reduction would require later evidence of decisions and interventions.

### Smallest complete user journey

1. Select a jurisdiction and financial-year range. A first visit supplies a worked example.
2. Read a concise summary of total emissions, change over time and per-capita comparison. Clearly label FY2023-24 rather than only “2023.” Describe rising emissions as an investigation prompt, not a policy recommendation inferred from state rank.
3. Inspect relevant charts and supporting tables. Clearly distinguish official transport emissions from petrol-plus-diesel sales, with separate coverage dates and boundaries.
4. Review a genuinely future fuel-sales forecast, selected against benchmarks, with uncertainty and an explanation of when it should be used cautiously.
5. Export a briefing and data table containing the chosen filters, units, sources, latest observation dates, assumptions, limitations and pipeline run identifier.

For a stronger Assessment 3 slice, implement steps 1-3 and 5 reliably, and demonstrate forecasting as an explicitly labelled experiment if operational forecasts are not ready.

**Strategic insight:** the defensible contribution is the time saved and mistakes prevented by integrating fragmented sources into a traceable analyst task. Official dashboards and emissions projections already exist. [DCCEEW publishes projections and their methodology](https://www.dcceew.gov.au/climate-change/publications/australias-emissions-projections-2025), so “we display government data and predict emissions” is insufficient differentiation.

### Scenario analysis, only after the data boundary is repaired

An optional later feature can compare explicit analyst assumptions with a baseline. For example, estimate combustion emissions associated with a stated reduction in an appropriate fuel volume using validated factors. Describe the result as conditional arithmetic, not a causal policy forecast.

A road or transport scenario requires suitable end-use activity data. An EV scenario also needs a justified activity share, energy efficiency and electricity emissions assumptions. Budget optimization requires costs and intervention effectiveness data. None of these should be invented from the present regression.

The existing but unused workbook `data/bronze/Australia fuel consumption in transport/activity-table-1990-2024-energy-transport.xlsx` contains national transport activity by mode/fuel. It is a useful candidate for national reconciliation. It is not a verified state-level allocation source, and national shares should not silently be imposed on every state.

## UX changes tied to task completion

| Severity | Finding | User impact | Recommendation and rationale |
|---|---|---|---|
| Major | Charts and model scores lead; no briefing task or takeaway leads. | The user must decide what every chart means and how to use it. | Lead with the selected state's summary and the next task. Progressive disclosure keeps model diagnostics available without making them the entry point. |
| Major | Fuel sales and emissions have different latest dates; the overall header emphasizes only 2010-2023. | A user can mistake the entire application for a current, aligned snapshot. | Show an observation cutoff for each measure plus a run timestamp. Visibility of system status supports informed interpretation. |
| Major | Selecting “None” gives blank axes and a total of zero. Reproduced in the browser. | Zero can be mistaken for a real emissions result. | Show “Select at least one state” and suppress derived totals while no states are selected. Error prevention distinguishes missing selection from real zero data. |
| Major | Faint text `#6B7480` has contrast **3.34:1** against panel `#1D232B` and **3.69:1** against background `#151A21`. | Instructions and limitations are harder to read. | Use a lighter text token for ordinary small text. WCAG AA requires 4.5:1 for normal text; see [W3C's contrast explanation](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html). |
| Major | Chart interpretation depends heavily on color and there is no equivalent task-oriented table. Select labels also lack explicit association in the static template. | Users with vision impairments or keyboard/screen-reader workflows face unnecessary friction. | Provide a data table, stable text labels, named controls, visible focus and deliberate keyboard order. Recognition and equivalent information improve access. |
| Minor | The live app shows machine-oriented metric names and terminal instructions; database read exceptions become empty tables. | A user may be asked to diagnose deployment failures and cannot distinguish missing data from connection failure. | Use readable labels and actionable service messages; preserve error details for developers. Match language to the user's task and distinguish system states. |

The visual styling is already adequate for a student demonstration. Prioritize interpretation, contrast, empty states and outputs over a visual redesign. Chart-image downloads exist through Plotly, but a cited briefing/data export does not.

## What makes this master's-level work

1. **A specific research question:** “Does an integrated state-level briefing workflow improve task accuracy, traceability and preparation time compared with the current spreadsheet or public-dashboard process?” A secondary question can assess which forecasting method provides the most reliable short-horizon fuel-sales forecasts.
2. **A justified contribution:** compare the tool with the real alternative, including government dashboards. Explain what integration and interpretation add, and what cannot be concluded.
3. **A reproducible experiment:** preserve dataset versions, retrieval dates, sheet mappings, hashes, units, preprocessing decisions, code revision, model parameters and run identifiers. Bind results to those artifacts rather than only log messages.
4. **Appropriate evaluation:** use seasonal naive and other simple baselines, multiple rolling origins, errors by state and horizon, residual checks, disruption-period analysis and uncertainty coverage. For annual panel evaluation, split by whole years rather than randomly ordered state-year rows. The [sklearn TimeSeriesSplit documentation](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html) explains the future-to-past leakage problem, but a panel needs year-grouped folds rather than blindly applying that class to state-sorted rows.
5. **Evidence of utility:** interview 2-3 relevant practitioners if accessible; conduct a small pilot with 5-8 representative users completing the same tasks in both workflows. Record time, correct answers, errors, source traceability and uncertainty interpretation. Counterbalance task order. If classmates are proxies, label the evidence exploratory and report recruitment limitations. A small pilot does not establish population-wide benefit.
6. **Critical reflection:** describe data scope mismatches, observational versus causal claims, short annual coverage, ACT omission, non-road diesel use, revised official series and model limitations. Discuss why a simple method can be the appropriate choice.

Example acceptance targets to agree *before* testing: at least 90% completion of the defined briefing tasks, a 30% median preparation-time reduction against the baseline workflow, and correct identification of the data cutoff and major limitations. These are proposed goals, not achieved findings or universal grading requirements.

## Assessment 3 preparation

### Group presentation: suggested 19-minute structure

| Time | Demonstrate |
|---|---|
| 0:00-2:00 | The intended user, recurring problem, objectives and claimed benefit. |
| 2:00-4:00 | Updated architecture and the actual data-to-user workflow. Explain what each component contributes. |
| 4:00-6:00 | Evidence of progress since Assessment 2: compare the submitted baseline with current commits, artifacts and functionality. |
| 6:00-12:00 | One complete live briefing task, including state selection, fair comparison, a real data-quality limitation and the final output. |
| 12:00-15:00 | Analytics and model evaluation, including a simple benchmark and why pooled R² is insufficient. |
| 15:00-17:00 | Two substantive technical challenges: what failed, evidence of the cause, the implemented resolution or clearly stated remaining limit. |
| 17:00-19:00 | Prioritized Assessment 4 work, validation criteria, owners and dependencies. |

Keep the final recording within 20 minutes, with readable text and rehearsed transitions. Have a checked demo dataset and a backup recording of the same flow. Confirm the submitted video link is accessible to the assessor. Do not call an exported HTML file a live model connection.

### Individual summary: half the assessment

One combined PDF must contain exactly **two pages per student**, font size **at least 10**.

- **Page 1:** name and ID; actual responsibilities and work completed since Assessment 2; clickable links to relevant GitHub commits/PRs, Jira or equivalent tasks and other evidence; planned work before Assessment 4.
- **Page 2:** exactly one screenshot of the specified **Lab 2, week 4, Module 8, Amazon Redshift lab**, showing lab name, mark, completion date and time, followed by a brief reflection explaining learning and its actual application to the project.

The local repository has multiple contributor identities, but authorship counts do not establish assessed contributions since Assessment 2. Each student should link particular work and explain its effect. Do not fabricate lab evidence or imply the SQLite project runs on Redshift. Explain legitimate transfer of learning such as organizing analytical tables, ETL decisions, queryable storage and data checks.

No presentation recording, combined contribution PDF, grading descriptors or Assessment 2 baseline was present in the reviewed project files. They may exist elsewhere; this audit does not assume they have never been created.

## Prioritized delivery order

Effort estimates are approximate engineering time, not deadline commitments. Research recruitment and obtaining evidence add elapsed time.

| Order | Work | Effort | Completion evidence |
|---|---|---|---|
| 1 / P1 | Correct data interpretation, restore historical vehicle data and reconcile every artifact. | L, 1-2 working days | One documented source/run produces matching CSV, DB, model and dashboard values. Signed discrepancies are explained or visibly unresolved. |
| 2 / P1 | Repair launch paths, dashboard regeneration, template contract, diagram generation and CI. | L, 0.5-1 day | A teammate follows the guide successfully; a fresh CI run and repeatable dashboard build are captured. |
| 3 / P1 | Define the analyst, task and meaningful benefit; add a worked state briefing and export. | L, 1-2 days plus stakeholder contact | An unfamiliar user completes a full task and obtains a cited output. |
| 4 / P1 for submission | Update diagrams; prepare progress evidence, contribution pages and specified lab evidence; rehearse the recording. | L, 1-2 days across the group | All explicit Assessment 3 requirements are checked, including page counts, links and video duration. |
| 5 / P2 | Evaluate forecasts against baselines over rolling windows; add future outputs, per-state errors and intervals. | L, 1-3 days | Reproducible comparison tables and uncertainty checks; operational forecasts distinguished from backtests. |
| 6 / P2 | Run the utility pilot and improve the workflow from observed failures. | L, 1-2 days plus recruitment | Paired task-time and accuracy results, changes made, and candid limitations. |
| 7 / P3 | Add justified scenario analysis, automation or other extensions. | Dependent on validated data and user need | The extension solves a confirmed task and has defensible assumptions. |

Keep optional dependency-heavy tools, additional dashboards, a chatbot, extra model families and a database migration out of the immediate critical path unless they solve a measured need. An honest negative model result with a useful, well-evaluated workflow is academically stronger than an unsupported “AI-powered” claim.

## Verification performed and limits

- Inspected all 20 Python source files for syntax; no parsing errors found.
- Read raw workbook structure and the sources used by the loaders.
- Rebuilt the annual master in memory with persistence disabled. All 98 rows matched the saved values across the four modeled numeric fields.
- Read the SQLite database in read-only mode and compared its metrics with the saved JSON and embedded HTML.
- Reproduced both dashboard-builder failures without writing dashboard output.
- Calculated signed validation gaps, seasonal-naive forecast errors, the illustrative chronological regression diagnostic, and CSS contrast ratios.
- Opened the static dashboard in a browser, checked chart rendering and metric selection, and reproduced the empty-selection behavior.
- Checked tracked paths, Git history, architecture and workflow images.

The full automated test suite, model refitting, API serving and Streamlit runtime were **not** verified. Required packages were absent from the available Python runtimes; an isolated package installation attempt could not reach the package registry under the session's network restrictions. Existing passing-test claims in README/CHANGELOG were therefore not treated as fresh verification. No implementation source files were changed by this audit.
