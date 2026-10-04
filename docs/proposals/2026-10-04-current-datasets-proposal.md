# Australian Fuel Outlook: forecasting and transport-emissions monitoring

Date: 4 October 2026. Status: earlier research-direction proposal. The user subsequently selected the government/industry market-review application and authorised implementation. See the implemented FuelScope design in ../superpowers/specs/2026-10-04-fuel-market-review-design.md and the current recording runbook in ../assessment3/fuelscope_video_runbook.md. Those documents supersede the provisional workflow below.

## Project purpose

Develop and evaluate a data-science system that forecasts Australian state-level petroleum sales, explains forecast uncertainty and relevant supply indicators, and places the results alongside official transport-emissions and activity evidence. Deliver the results through a concise recurring review application for transport/energy analysts.

The current Australian government datasets remain the foundation. Additional datasets are allowed when they address a specific modelling or recurring-use need. A different-domain application and wholesale replacement of the existing pipeline are outside this proposal.

The intended benefit is less effort preparing recurring evidence reviews and better understanding of changing forecasts and their limitations. This benefit and the proposed audience remain unvalidated until a real pilot. Aggregate state/national observations support analysts' tasks; they do not predict an individual driver's consumption or a local depot's stock requirements.

## Central research question

**Can fuel-specific models and information available at the forecast date improve one-to-three-month state petroleum-sales forecasts over seasonal baselines, while supporting clearer weekly evidence reviews?**

The core prediction target is monthly recorded fuel sales, initially automotive gasoline and total diesel separately. Total diesel includes non-road uses. The target must be called sales, not measured road-only consumption or unconstrained demand.

Research hypotheses are testable, not promised outcomes:

- Modelling gasoline and diesel separately may improve accuracy or explainability over the existing combined-sales outlook.
- Suitable lagged supply/price indicators may add predictive information beyond seasonal sales history.
- Explicit uncertainty, freshness and forecast-revision explanations may improve users' review tasks compared with consulting separate source files.

## Existing datasets and their roles

| Current source | Role in the revised project | Boundary |
|---|---|---|
| Australian Petroleum Statistics | Main forecast targets; candidate supply indicators and quality analysis | Monthly state sales and national supply series have different geographic scopes |
| State/territory greenhouse-gas inventories | Historical transport-emissions monitoring and comparison | Annual official inventory covering all transport modes |
| BITRE road travel and vehicle stock | Activity/intensity context and carefully selected lagged structural features | Road activity and vehicle stock are not the same boundary as all-mode transport emissions |
| ABS population | Per-person comparisons and structural context | Use period-appropriate observations; do not treat future releases as known |
| National quarterly greenhouse-gas update | National sector context alongside the state analysis | National quarterly totals cannot be substituted for state observations |
| NGA emission factors | Existing accounting-boundary diagnostic with explicit assumptions | Fuel-times-factor estimates cannot replace the official transport inventory or establish intervention savings |

The existing processed release has 1,344 monthly state observations and 98 annual state-year observations. The larger monthly panel is the principal modelling dataset. The small annual panel supports cautious descriptive/association analysis, not a highly parameterised causal model. Preserve the exclusion of ACT where the chosen sales source lacks a separate series.

### Useful information already in the petroleum workbook

A read-only inspection of the existing June 2026 extract confirmed sheets for imports, refinery production, product stock volumes, consumption cover, and Australian quarterly fuel prices. These provide candidate research extensions before obtaining another dataset.

The current sales parser extracts automotive gasoline totals and diesel totals from the state-sales sheet. That sheet also exposes gasoline grade categories and sales-to-retailer columns. Inspect their completeness, definitions and reporting changes before expanding targets. A column's presence does not establish consistent historical coverage.

National stock/import series may be contextual predictors, but they are not state-specific measurements. Stock levels, consumption-cover measures, in-transit stocks and IEA import coverage use distinct definitions and units. The research must preserve those distinctions. Import value divided by volume is an import unit-value measure, not a retail pump price.

## Additional data, introduced in stages

First, extract and evaluate useful series already present in the petroleum workbook and refresh the current official sources when new releases become available. The [Australian Petroleum Statistics publication](https://www.energy.gov.au/energy-data/australian-petroleum-statistics) documents its monthly sales, production, trade and stock scope.

Next, consider [NSW FuelCheck price history and live pricing access](https://data.nsw.gov.au/data/en/dataset/fuel-check) for a clearly bounded NSW price-monitoring extension, and [RBA daily exchange-rate history](https://www.rba.gov.au/statistics/historical-data.html) as a candidate indicator. Verify credentials, licence/usage conditions, update frequency, history and geographic coverage. NSW prices cannot be presented as national or other-state measurements.

Add a source only if it improves a defined forecast, interpretation or recurring task. Keep a comparable sales-only baseline so added-data value can be measured. Do not add weather, traffic or EV data merely to enlarge the dataset list.

## Data-science work

1. **Data audit and integration:** document time/geographic boundaries, units, publication lags, missingness, revisions and reporting breaks. Keep annual, quarterly and monthly data at their supported grain. Forward-filling a released annual value does not create new monthly observations.
2. **Exploratory analysis:** investigate seasonality, fuel-specific changes, state differences and supply-series relationships. Distinguish descriptive relationships from causal explanations.
3. **Baselines and candidates:** retain seasonal-naive and the existing Holt-Winters comparison. Test a limited set of lagged statistical/regularised or boosted models where the sample supports them. Choose complexity from evidence, not a requirement to use more algorithms.
4. **Experiment design:** use rolling chronological forecast origins and untouched final evaluation periods. Tune and fit preprocessing only on earlier eligible observations. Match every feature to information that would be available when the forecast is made. Historical release timestamps/vintages may be incomplete; disclose any assumed reporting lag and any evaluation using revised final data.
5. **Uncertainty and robustness:** evaluate forecast errors by state, fuel and horizon, interval coverage/width, sparse periods, reporting breaks and unusual conditions. Explain when the selected model underperforms a baseline.
6. **Added-data experiments:** compare history-only models with candidate supply/price indicators and remove feature groups to measure their contribution. Future exogenous variables require forecasts or labelled assumptions; realised future values cannot be used for an operational forecast test.
7. **Monitoring:** flag unusual observed deviations for human investigation, with source evidence and freshness checks. Missing/outdated feeds must not appear as zero activity. Statistical flags are not verified shortages, fraud or causal events.

Official annual transport-emissions trends remain an integrated context view. An operational emissions forecast would require a separate, fair lagged-feature evaluation; the current contemporaneous annual regression is an association analysis. Conditional scenarios must remain explicitly assumed scenarios and cannot establish the causal impact of a policy or EV adoption.

## Credible recurring use

Proposed primary cadence: **weekly analyst review**.

An analyst opens the application to inspect fresh price/exchange-rate indicators, new official releases, forecast revisions where justified by eligible new inputs, unusual observations, and source age. They compare the next-month/quarter sales outlook with the previous outlook and download a cited review for a meeting or report.

The existing annual/monthly snapshot alone does not create a new reason to return daily or weekly. A static chart cannot become a live monitoring service by refreshing its page. Weekly usefulness therefore requires a verified fresh-input workflow and evidence that the intended user values that review. Daily use would be optional for a separately verified daily price-monitoring need; it is not claimed for annual emissions data.

If no relevant new information arrives, retain the last report with its as-of dates and say nothing material changed. If the fresh indicators do not improve forecasts, they may remain separate contextual information only if users find that context useful. Do not manufacture changing forecasts to encourage visits.

## Benefit evaluation

Evaluate model quality and application benefit separately. Compare prediction accuracy and uncertainty against the same baselines on eligible holdouts. For the application, recruit reachable users who actually prepare transport/energy reviews, compare equivalent review tasks using the app versus separate source files, and measure time, interpretation errors, assistance and task completion.

Observe at least two weekly cycles where relevant new work exists. Record voluntary return and reasons for non-return. Student usability testing can support an initial interface study, but cannot substitute for evidence of professional demand or operational benefit. Report simulated improvements, participant findings and unmeasured claims separately.

## Software-engineering scope and reuse

Reuse source resolution, Bronze/Silver/Gold organisation, validation, the SQLite warehouse, provenance, tests and the existing dashboard/Streamlit framework where appropriate. Extend parsers, feature tables and experiments as the research requires. The interface presents the forecast, comparison, uncertainty, source age and a cited weekly export.

Most academic effort should centre on dataset quality, feature design, comparative modelling, uncertainty, robustness and evaluation. Software engineering supports repeatable ingestion and delivery. A manual fleet ledger, unrelated retail platform or large new account-management system is not required for this research question.

## Success and limits

A successful master's project has reproducible experiments, defensible data boundaries, fair baseline comparisons, explicit uncertainty and an evaluated user task. It does not depend on a complex model necessarily winning or every available dataset becoming a predictive feature. The current results already show cases where simpler baselines perform better; the revised proposal should investigate those limitations honestly.

Before implementation, settle the target user, initial fuel/state scope, source-access feasibility and evaluation protocol. This is a substantial research refocus with selected data extensions, not a replacement of the current dataset collection. The supplied Assessment 3 requirements still need the group video and genuine individual contribution/lab evidence; this proposal cannot guarantee a grade.
