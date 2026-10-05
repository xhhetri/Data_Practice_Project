# Fuel-market review implementation plan

> Execute inline in the current approved feature checkout. The user's explicit GO supersedes additional planning handoffs; preserve scope and verify before reporting completion.

**Goal:** Deliver a polished, repeatable daily/weekly fuel-market review demonstration using real evidence and evaluated sales forecasts.

**Architecture:** A focused market module validates cached official spreadsheets and builds a versioned review snapshot. Existing modelling and briefing functions are reused. A generated browser dashboard consumes this snapshot, and an optional loopback server performs explicit refreshes.

**Tech stack:** Existing Python/pandas/openpyxl/statsmodels, standard-library HTTP/downloads, existing local Plotly, HTML/CSS/JavaScript.

**Spec:** ../specs/2026-10-04-fuel-market-review-design.md

## Global constraints

- Preserve original source datasets and annual research; introduce additional sources with explicit provenance.
- Real observations only; no fabricated weekly sales, benefit results or shortage predictions.
- Retain valid cached evidence on source failure; no forced refresh on page load.
- Work locally without publishing, pushing or messaging external people.

## Review focus

Malformed/partial spreadsheets; missing fuel/location observations; unchanged refreshes; stale data mistaken for current observations; unsupported forecast or national-stock interpretations.

## Tasks

1. [x] Read actual additional source schemas, write failing parser/validation/change tests, implement `src/market_review.py` and cached source refresh, then verify parser and failure behaviours.
2. [x] Add product-specific six-month rolling evaluation using `evaluate_fuel_series`; validate chronology, units and baseline comparisons; build the real evidence snapshot with hashes and source cutoffs.
3. [x] Build the polished dashboard and generator. Verify fuel/state changes, dated price/stock context, evidence detail, checkpoint persistence, notes, filtered Markdown/CSV exports and print briefing.
4. [x] Add loopback demonstration serving and explicit refresh; check unavailable-feed retention, host/origin boundaries and dashboard availability.
5. [x] Rebuild research evidence, run relevant and existing tests, inspect desktop/mobile in the browser, repair identified defects, and add the video runbook plus Assessment 4 roadmap.

## Execution record

Ruling: Use the existing feature checkout — the user wants the current project and local video demonstration updated. No additional worktree or repeated scope approval is needed.

Ruling: Added price and weekly stock series supply actual recurring inputs; the principal sales forecast remains monthly. Daily/weekly adoption requires a later real-user pilot.

Ruling: The verified latest official sales release ends in July. Extend the original three-month scope to six months so upcoming months remain visible despite publication lag; evaluate the same six-month horizon and disclose elapsed outlook months.

Completed: real public source refresh, all 14 product/state evaluations, live checkpoint and notes persistence, scoped export checks, desktop and narrow mobile inspection, and the 19-minute recording runbook. Independent review findings were repaired. See reports/market_review/verification.md for checks and remaining limitations.
