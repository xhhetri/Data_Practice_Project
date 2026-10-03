# Benefit evaluation: state briefing pilot

Status: protocol prepared; no participant results collected or claimed.

## Research question

Can a source-backed state briefing tool reduce preparation time and interpretation errors compared with consulting the same data in separate files?

The intended users are analysts preparing an initial transport evidence briefing. The tool supports investigation and communication; it does not select transport policies or demonstrate reduced emissions. A useful result is a correct, traceable briefing that a user can take away.

The separate modelling question is whether seasonal-naive or Holt-Winters improves monthly petrol plus total diesel SALES forecasts on chronological evaluation. Model accuracy and user usefulness must be assessed separately.

## Participants and comparison

Recruit 6–8 volunteers with basic spreadsheet skills, preferably including people who prepare evidence briefings. Record role category and prior experience without names. If participants are students rather than professional analysts, report that limitation. Follow the unit's requirements for research participation and consent.

Every participant uses both conditions: (A) the tool, and (B) separate project files. Give both conditions identical information and cutoffs: `annual_master_with_population.csv`, `monthly_fuel_series.csv`, and the model outputs in `metrics.json` / the generated technical results report. Provide a brief field glossary and equivalent forecast information to both conditions. The comparison tests the integrated workflow, not access to extra data. Do not change the source snapshot midway through the study.

Alternate order A→B and B→A across participants. Use a different but equivalent jurisdiction task in each condition to reduce recall. Allocate NSW and WA tasks evenly to both conditions; randomize within these constraints. Allow a two-minute practice with VIC before timing either condition. Record help requests, but do not lead users toward correct answers.

## Two equivalent tasks

Task 1: Prepare an NSW briefing comparing FY2016-17 with FY2023-24.

Task 2: Prepare a WA briefing comparing FY2016-17 with FY2023-24.

For either task, ask the participant to:

1. State the selected end-year official transport inventory in kt CO2-e, its percentage change, and its per-capita change.
2. Identify the highest per-capita jurisdiction at that end year, and explain why total and per-capita rankings can differ.
3. State the selected state's forecast method, first after-cutoff forecast month, final holdout MAPE and approximate 95% band for that month.
4. Explain whether the outlook is a road-emissions forecast and whether it proves that a policy caused a change.
5. Submit a saved briefing with units, source links, observation cutoffs and a run identifier. In the file condition, allow copying values into a supplied blank text document.

Start timing when the task is revealed. Stop when the participant submits the briefing; cap each condition at eight minutes and record a timeout as incomplete. Keep the cap and help policy identical. Score against values computed from the frozen run, using the shared briefing calculation and `metrics.json`; prepare the answer sheet before sessions. Accept rounding within 0.1 percentage point and 1 kg/person; require correct units and dates.

## Measures and predeclared pilot targets

Measure completion time, complete-task success, factual errors, critical interpretation errors, help requests, and a 1–7 ease rating. A critical error is treating total diesel sales as road-only use, treating a sales outlook as official emissions, asserting causation, treating a band as guaranteed, or presenting after-cutoff months as live observations.

Exploratory targets: at least 80% complete tasks in the tool condition, at least 30% median within-participant time reduction, and no increase in critical interpretation errors. These are proposed practical targets, not established performance or statistical significance.

For each participant calculate `(file_time - tool_time) / file_time * 100`. Report the median paired improvement, both conditions' task success and error counts, and individual anonymized results. Do not average completed-task times alone while excluding timeouts; report capped times and completion separately. With this small pilot, use descriptive evidence and disclose order effects, task differences, sample composition and observer bias. Do not generalize to all policy analysts.

## Blank results sheet

Copy this table for genuine sessions. Keep it blank until observations exist.

| Participant code | Role/experience | Order | Tool task | File task | Tool seconds | File seconds | Tool complete | File complete | Tool factual errors | File factual errors | Tool critical errors | File critical errors | Tool help | File help | Tool ease 1–7 | File ease 1–7 |
|---|---|---|---|---|---:|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| | | | | | | | | | | | | | | | | |

After each condition ask: “What was difficult?” and “What would prevent you using this in a real briefing?” Record short anonymized quotes with permission. End the study with concrete changes supported by observed failures and repeat the affected task after those changes. Record incomplete or negative outcomes honestly.

## Evidence to retain

Retain the frozen run identifier and hashes, task/answer sheets, anonymized results, consent record as required by the unit, exported briefings, and the changes made after the pilot. The presentation can show the protocol now; user-benefit findings may be presented only after sessions occur.
