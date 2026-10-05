# FuelScope: Australian fuel-market review

The user approved the three-view prototype and explicitly instructed immediate implementation on 4 October 2026. Work continues in the existing feature checkout so the local demonstration receives the changes. Existing research and datasets remain available.

## User and repeated task

An industry or government analyst checks current wholesale prices on working days and prepares a weekly market briefing. They identify material changes, inspect national stock evidence, compare state petrol/diesel sales with history and forecasts, and export a cited report. Actual adoption and time savings remain hypotheses for Assessment 4; no fabricated users or savings appear in the demonstration.

## Scope

- A polished default browser dashboard with Market review, Sales outlook, and Evidence views. Existing annual transport analysis remains accessible.
- Real AIP daily wholesale price history and official DCCEEW weekly national stock observations, with download timestamps, source links and observation cutoffs. Refresh is an explicit local action; cached evidence remains usable if a feed fails.
- Separate petrol and diesel monthly state-sales models using the existing seasonal-naive/Holt-Winters chronological evaluation, six-month horizons, historical error bands, honest baseline comparisons and exact train/test dates. The verified latest release ends in July; six months retain upcoming months despite that publication lag. Monthly observations never become synthetic weekly targets.
- Watchlist entries explain measured changes and suggest verification tasks; they do not predict shortages or prescribe government intervention. National stocks are never assigned to a state.
- Save a local review checkpoint, compare material evidence with it, record analyst notes and export Markdown/CSV and a print-ready briefing. Local browser persistence is clearly described and resettable.
- A safe loopback-only demonstration server provides explicit source refresh without exposing source files or arbitrary commands. A standalone generated dashboard also works offline; refresh controls explain when a server is needed.
- Presentation runbook and technical evidence document implemented capabilities, current limits and Assessment 4 work.

## Evidence and failure handling

Validate schemas, unique dates/keys, finite positive observations, and source horizons before replacing any cached feed. Failed downloads retain prior valid files and publish visible feed status; observation age differs from retrieval time. Changes in an unchanged snapshot do not manufacture alerts. Forecasts begin after their source cutoff, even if the calendar has moved ahead. Stocks measured under different definitions remain distinct. New model and market artifacts carry their own hashes and reference the existing historical run identity.

## Visual direction

An instrument-panel layout: deep blue navigation (#122B45), cool white workspace (#F4F7FB), cobalt links/price lines (#2857D9), petrol teal (#087C83), amber review emphasis (#A66612), slate text (#24354A). Segoe UI Variable/Segoe UI for headings and body; Consolas for dates and numerical labels. The signature is a paired petrol/diesel price strip with dated changes and a compact weekly evidence timeline. Use restrained motion, clear focus, table alternatives, large controls and mobile layouts.

## Acceptance

Real source-backed daily and weekly values; separate fuel forecasts with untouched holdouts; accurate scope-labelled exports; cached refresh failure handling; meaningful checkpoint comparison; no browser errors; usable desktop/mobile layout; relevant unit/integration checks plus existing regression tests. Capture the working interface and supply a recording walkthrough. Higher-complexity models, automatic notifications and participant benefit evaluation belong to Assessment 4.
