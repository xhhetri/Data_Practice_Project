# Revised proposal direction: data science as the core

Date: 4 October 2026. Status: brainstorming draft for selection; no new direction has been approved or implemented.

**Scope update:** The user has clarified that the current datasets must remain the foundation, with extra datasets permitted. The unrelated retail/footfall directions below are therefore no longer the recommended scope. See [the revised proposal using the current datasets](2026-10-04-current-datasets-proposal.md).

## Agreed requirements

The project is for PRT661 Data Science Practice. The user requires a predominantly data-science project with supporting software engineering, and an application that has a credible daily or weekly purpose. The initial comparison allowed any domain; the latest requirement is to retain the current datasets as the foundation and add relevant data where needed. No specific end user or participant has yet been recruited.

The Assessment 3 brief requires a technical demonstration of objectives, architecture, workflow, implementation, challenges and future work, plus truthful individual contribution/lab evidence. It does not supply an HD grade-band rubric or guarantee marks for adding particular models.

The previous record-entry application places much of its work in software engineering. The revised proposal should make a research question, observed prediction target, comparative experiments and decision evaluation central. The interface should deliver those results to users. A design target is roughly three quarters of the project's research effort on data preparation, modelling, evaluation and interpretation; this is a proposed emphasis, not a university marking allocation.

## What every candidate must contain

1. An identifiable user who already faces the recurring decision.
2. Historical observations suitable for training and testing, with an explicit target and data dictionary.
3. A practical source of fresh data for ongoing use. A historical benchmark alone cannot make a live application.
4. Simple baselines that represent what the user could already do.
5. A chronological evaluation that prevents future information entering training, feature construction or model selection.
6. Evaluation of the resulting decision, separately from prediction accuracy.
7. Useful uncertainty estimates and a fallback when data are sparse, stale or the model does not improve on the baseline.
8. Evidence from real users; simulated outcomes must remain labelled simulations.

## Candidate 1: Retail sales forecasting and weekly replenishment support

**Provisional academic preference, conditional on access to a retailer.**

User: an owner or stock coordinator who exports sales and orders stock each week.

Recurring decision: how much to order for selected products over the next replenishment period, given current stock, lead time and uncertainty. Daily use can check incoming sales against the outlook; weekly use prepares an order review. The first scope should be one retailer and a manageable subset of products.

Research question: **Does uncertainty-aware sales forecasting improve weekly replenishment decisions compared with recent-average and seasonal-baseline methods?**

Data: [UCI Online Retail II](https://archive.ics.uci.edu/dataset/502/online+retail+ii) provides 1,067,371 historical transaction records from a UK online retailer in 2009–2011, including product, quantity, transaction time and unit price. It has missing values and cancellation records. It is a benchmark for the method, not evidence about present Australian retail demand. Real use requires a participating retailer's continuing sales exports; stock, lead times and relevant costs need separate supplied inputs.

Data-science work:

- Define recorded sales versus returns/cancellations; investigate duplicates, missing values, irregular trading periods and intermittent product sales.
- Forecast next-seven-day units per product. Compare recent averages, seasonal-naive and an appropriate intermittent-sales baseline with statistical/boosted models. Select methods by earlier validation rather than test results.
- Use lagged sales, known calendar variables and genuinely available promotion information. Unobserved future prices/promotions must not become features.
- Evaluate rolling forecast origins, product-level performance and failure cases. Compare point errors with quantile loss and interval coverage; do not let high-volume products conceal weak results elsewhere.
- Simulate a limited replenishment policy under declared stock/lead-time/cost assumptions, then test its usefulness in a real weekly workflow.

Evaluation: forecast accuracy, uncertainty calibration, simulated inventory/service trade-offs under stated assumptions, ordering-review effort, follow-through and voluntary weekly return. Recorded sales are not unconstrained demand; stockouts can censor sales. The benchmark does not supply enough inventory history to claim observed stockout reduction or actual waste savings.

Software role: sales import, quality report, weekly forecast/order-review screen, explanation of assumptions, downloadable report. A full retail-management platform is unnecessary.

Main dependency: obtain a willing retailer and sufficiently long, usable historical exports early. Without that, the work can be a rigorous benchmark study but cannot yet meet the recurring-use claim.

## Candidate 2: Fuel-price forecasting and refuelling timing

**Strong public-data alternative with a clear consumer decision.**

User: a driver who has some flexibility about when to refuel and already checks prices.

Recurring decision: whether to buy now or wait within a safe, user-specified window, and which nearby feasible station to consider. The first scope should be one NSW area, one fuel grade and a short horizon.

Research question: **Can short-horizon station-level price forecasts improve refuelling decisions over current-price-only and simple price-cycle baselines?**

Data: [Data.NSW FuelCheck](https://data.nsw.gov.au/data/en/dataset/fuel-check) publishes historical price resources. The [NSW Fuel API catalogue](https://api.nsw.gov.au/ProductCatalogue?apiCategoryId=3) identifies live pricing access; credentials, usage terms, permitted refresh rate and schema must be verified before promising operation. Inspect sample history for station identity, timestamps, gaps and price-change versus full-snapshot semantics before choosing the modelling resolution.

Data-science work:

- Reconstruct station/grade price series conservatively; distinguish missing observations from unchanged prices.
- Explore local cycles and variation across stations, grades and time.
- Compare last-observed price, seasonal/cycle baselines, and statistical/boosted quantile models at 24–72-hour horizons where observations support them.
- Use rolling-origin evaluation and hold out stations when claiming transfer to unseen stations. Fit preprocessing, feature selection and uncertainty calibration only on eligible earlier data.
- Backtest a constrained buy/wait policy with fixed fuel volume, candidate stations, waiting deadline and explicit detour-cost assumptions. Report price error, interval calibration, regret and worse-outcome frequency.

Evaluation: forecast performance and simulated decision costs against simple policies, followed by a repeated-use pilot. A favourable backtest is not an observed saving. Recommendations must respect the user's stated refuelling deadline and disclose uncertainty/stale feeds.

Software role: refresh prices, select grade/area/time window, display a forecast and uncertainty, compare choices, export evidence. No manual fuel ledger is needed for the primary question.

Competitive requirement: [FuelCheck already provides price comparisons, alerts, route search and trends](https://www.nsw.gov.au/legal-and-justice/consumer-rights-and-protection/advertising-product-packaging-and-pricing-laws/fuel-pricing-discounts-and-signage/check-fuel-prices). The proposed contribution is a tested forecasting/decision method and its measured incremental value. Do not claim that forecasting features are unique without researching competing products. If the method adds no decision value, disclose that result and retain the stronger baseline.

Main dependency: dependable live access, adequate history, and participants who refuel in the selected area. Existing annual emissions and monthly aggregate fuel-sales data cannot substitute for station-level prices.

## Candidate 3: Urban footfall forecasting for weekly planning

**Public-data research option; user benefit needs careful grounding.**

User: a precinct/event coordinator or a nearby business that already considers pedestrian activity when planning operations.

Recurring decision: anticipate busier and quieter periods at selected locations over the next day/week, then review actual activity against the prediction.

Research question: **Do location-aware probabilistic forecasts improve prediction of hourly pedestrian activity over same-hour-last-week baselines?**

Data: the [City of Melbourne pedestrian counting dataset](https://data.melbourne.vic.gov.au/explore/dataset/pedestrian-counting-system-monthly-counts-per-hour/) provides hourly counts and sensor identifiers that can be joined to sensor-location metadata. Confirm recent coverage, publication lag, licence, sensor changes and API limits. Optional weather/event data require verified historical and future availability; observed future weather cannot be used as though it were known at prediction time.

Data-science work: sensor quality/coverage analysis; spatial and temporal feature construction; seasonal/statistical versus boosted count/quantile models; chronological and location-based validation; uncertainty calibration; errors during unusual periods and sensor outages; ablations showing which features contribute.

Evaluation: count errors, interval coverage and practical planning tasks compared with existing methods. Pedestrian counts are not shop sales, staff demand or revenue. Claims about those outcomes require corresponding business observations.

Software role: select a relevant sensor/location, view next-day/week forecasts and uncertainty, inspect data quality, export a planning brief and compare previous predictions with realised counts.

Main dependency: a reachable Melbourne user with an actual planning decision. A forecast map alone does not establish benefit.

## Proposal structure after a direction is selected

Working title → recurring user problem → research question/hypotheses → data sources and access → target and prediction horizon → data-quality/ethical boundaries → baselines and candidate methods → leakage prevention and experiment design → decision evaluation → small delivery application → recurring-use pilot → scope and limitations → member contributions and assessment evidence.

Choose the direction only after checking data access and a reachable user group. Do not make the proposal depend on a method necessarily winning: the scientific contribution includes explaining when a simpler baseline is preferable. Do not build another large interface before establishing the data and evaluation plan.
