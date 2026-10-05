# FuelScope: Assessment 3 recording runbook

Aim: a 19-minute professional technical demonstration. Each person presents work they actually performed and understand. Verify meaningful progress against the group's actual Assessment 2 submission; no contribution or authorship is invented here.

## Before recording

Open FuelScope at http://127.0.0.1:8766/ using Start-FuelScope.cmd. Use a normal browser at a readable desktop size, ideally 1440 × 900 or 1920 × 1080. Open the generated market technical results and architecture_v5/workflow_v5 figures. Check official sources before recording, then use one frozen snapshot during the demo. Have `reports/market_review/example_NSW_Diesel_briefing.md` as a fallback. The complete briefing also appears under **Preview complete briefing**. Rehearse downloads and printing in the browser used for recording. Disable unrelated notifications and check audio and link access.

## Suggested 19-minute sequence

| Time | Explain and demonstrate |
|---|---|
| 0:00–1:20 | Problem: an analyst checks weekday prices and prepares a weekly fuel-market briefing from separate sources. Intended benefit: faster review with fewer interpretation errors; real benefit evaluation remains Assessment 4 work. |
| 1:20–3:00 | Existing six government source files and two added recurring sources. Explain city wholesale prices, state monthly sales and national MSO stocks. Point to their different dates and boundaries. |
| 3:00–4:30 | Show architecture_v5 and workflow_v5. Explain validation, cached failure retention, forecast evaluation, evidence snapshot and dashboard. |
| 4:30–8:00 | Market review: choose NSW/Diesel, inspect dated weekly price change, switch jurisdiction and fuel, inspect price history and review queue. Show national holdings and effective obligation, and explain source age and days equivalent. |
| 8:00–12:00 | Sales outlook: separate petrol/diesel modelling, seasonal-naive/Holt-Winters candidates, earlier rolling origins, untouched final holdout and six-month after-cutoff outlook. Show a model win and a baseline win using the actual generated results. Explain revised-data backtests, publication lag and approximate interval coverage. |
| 12:00–14:40 | Evidence & briefing: observation versus retrieval dates, official source link, original transport analysis and source checksum. Add a clearly identified demo analyst note, download the briefing and CSV, and open the briefing to show scope, units, uncertainty and sources. |
| 14:40–16:00 | Mark the review complete, revisit the same evidence, and show that unchanged data produces an unchanged checkpoint. Explain that real daily/weekly value depends on new relevant observations and actual analyst demand. |
| 16:00–17:30 | Technical challenges: source lag, changing stock obligations, different geographic boundaries, model underperformance and retained cache on network failure. Show verification evidence, not an unsupported production-grade claim. |
| 17:30–19:00 | Assessment 4: lagged predictor experiments, stronger uncertainty checks, real analyst pilot over weekly cycles, improved refresh/deployment operations and evidence-based refinements. |

## Lines worth saying accurately

- “The daily prices are wholesale terminal benchmarks, not pump prices.”
- “National MSO stocks do not tell us whether a particular depot will run out.”
- “Recorded monthly diesel sales include non-road uses.”
- “Method selection uses earlier periods; the final holdout can still favour the simpler baseline.”
- “The forecast starts after its observation cutoff. Source lag means some forecast months have already passed.”
- “These intervals come from historical errors; six held-out months cannot establish calibrated probabilities.”
- “We have implemented a repeatable workflow. Actual time savings and voluntary recurring use are still to be measured.”

Use the separate contribution-evidence guide for the required two-page-per-student PDF and genuine Redshift Lab 2 screenshot. This runbook does not replace either submission or the recorded video link.
