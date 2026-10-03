# Fleet Fuel Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a durable daily fuel ledger and weekly review application with honest calculations, protected records and deployable single-workspace packaging.

**Architecture:** A separate operational SQLite database serves shared validation/storage, pure analysis and transfer functions. A Streamlit app handles the operational workflow; the government warehouse and historical app remain research context. Reuse installed packages and implement inline in the existing feature checkout, followed by one independent review.

**Tech Stack:** Python 3.12, sqlite3, Decimal, pandas, Plotly, Streamlit, pytest; Docker packaging for deployment.

**Spec:** `docs/superpowers/specs/2026-10-04-fleet-fuel-review-design.md`, approved by the user's instruction to continue and make it production grade.

## Global Constraints

- One workspace, AUD, litres, kilometres; local transaction dates in Australia/Sydney by default.
- Real and fictional demonstration databases are separate; operational records/backups are ignored by Git and never rebuilt by the government pipeline.
- Store financial amounts as integer cents; purchases do not equal weekly consumption.
- Efficiency requires complete, valid full-to-full intervals; no inferred odometers, tank levels or employee scores.
- Imports are previewed before atomic confirmation; repeated requests/imports are idempotent; corrections retain history and detect stale writes.
- Production mode fails closed without password configuration; local mode binds to loopback. Shared multi-tenant hosting is outside this release.
- No invented research results, refunds, adoption, grades or financial benefits.

## Review Focus

- Concurrent stale corrections must be rejected without losing either user's saved revision.
- Date-only/same-day ambiguous fills and missing purchase declarations must not generate invented efficiency.
- Reordered/remapped CSV retries must not silently duplicate records or silently discard legitimate similar purchases.
- Corrupt or malicious backup restores must leave the current workspace intact and cannot choose arbitrary server paths.
- Authentication attempts/session expiry/configuration changes must not expose private records; a production configuration missing a credential must fail closed.

## Files and public interfaces

- `src/fleet/store.py`: `Repository(path, timezone='Australia/Sydney')`, validated vehicles/purchases, transactions, revisions, reviews and import batches. Dictionaries are the shared record format; `amount_cents` is integer, `litres`/`odometer_km` use decimal strings.
- `src/fleet/analytics.py`: `efficiency_intervals(records)`, `weekly_review(records, vehicles, week, today)`, `exceptions(records, vehicles)`, `scenario(km, rate, prices)` and `render_weekly_report(review)`; pure functions.
- `src/fleet/transfers.py`: `preview_csv(content, mapping, vehicles, existing)`, `import_preview(repository, preview)`, `export_csv(records)`, `backup(repository)`, `restore(content, directory)`; limits 5 MiB / 10,000 rows.
- `src/fleet/security.py`: password hashing/verification, production configuration validation and authentication/session gate helpers.
- `src/fleet/demo.py`: explicit fictional fixtures in a separate workspace.
- `app/fleet_app.py`: real Streamlit workflow and authentication gate; no raw SQL or independent calculations in the UI.
- Tests: `tests/test_fleet_store.py`, `test_fleet_analytics.py`, `test_fleet_transfers.py`, `test_fleet_security.py`, `test_fleet_app.py`.
- Release: `.streamlit/config.toml`, `Dockerfile.fleet`, `compose.fleet.yml`, `.dockerignore`, `.env.example`, `.github/workflows/ci.yml`, `GUIDE.md`, `README.md`, `docs/assessment3/fleet_demo_runbook.md`, `docs/evaluation/fleet_pilot_protocol.md`.

### Task 1: Durable validated records

**Files:** Store module, package init, store tests, `.gitignore`.

**Interfaces:** `Repository.vehicles()`, `create_vehicle(payload)`, `update_vehicle(id,payload,expected_revision)`, `purchases(include_void=False)`, `save_purchase(payload,request_id)`, `update_purchase(id,payload,expected_revision)`, `void_purchase(id,expected_revision,void=True)`, `history()`, `reviews()`, `save_review(payload)`.

- [ ] Write failing tests: exact cents/decimal validation; idempotent save; invalid vehicle/future/non-finite values; stale correction; reversible void with history; persistence on reopen; invalid transaction rollback.
- [ ] Run `python -m pytest tests/test_fleet_store.py -q`; expected missing operational implementation.
- [ ] Implement schema versioning, foreign keys, WAL/busy timeout, parameterised writes, explicit transactions, per-connection lifecycle and optimistic revision checks. Bound text/numeric fields and reject precision loss.
- [ ] Run the store tests; expected pass. Add ignored `data/operational/` and private upload/backup patterns.
- [ ] Commit only Task 1 files and record observed tests in the ledger.

### Task 2: Truthful weekly analysis

**Files:** Analytics module and analysis tests.

**Interfaces:** Consumes Task 1 record dictionaries; returns serialisable weekly summaries, intervals and exception dictionaries with stable IDs tied to source revisions.

- [ ] Write failing tests: full/partial/unknown boundaries, opening volume exclusion, missing-data declaration, ambiguous same-day ordering, odometer conflict, price/volume identity, no-purchase periods and elapsed-day comparisons.
- [ ] Run `python -m pytest tests/test_fleet_analytics.py -q`; expected missing calculations.
- [ ] Implement Decimal totals/decomposition, Monday–Sunday local periods, supported intervals and evidence-linked exceptions. Require six strictly earlier intervals before an efficiency alert; threshold exceeds both 20% and three scaled MADs; zero spread uses the percentage criterion.
- [ ] Test baseline exclusion, reviewed/stale evidence keys, negative/future scenario inputs and no guaranteed savings language. Implement low/base/high user-assumption scenarios and readable reports.
- [ ] Run the complete analysis tests, then commit and ledger results.

### Task 3: Safe imports, exports and recovery

**Files:** Transfers module and transfer tests; store batch transaction methods where required.

**Interfaces:** Preview dictionaries contain parsed rows/errors/warnings, file/mapping identity and target vehicle references; import revalidates against the current database snapshot.

- [ ] Write failing tests: arbitrary column mapping, UTF-8 BOM, malformed/oversized files, unknown vehicles, same-file retry, changed mapping, atomic failure and concurrent preview changes.
- [ ] Run `python -m pytest tests/test_fleet_transfers.py -q`; expected missing transfer implementation.
- [ ] Implement preview with no writes, confirmation with current validation and transactional idempotency. Potential duplicates require review rather than automatic deletion.
- [ ] Write/run failing recovery tests: round trip retains revisions/reviews, invalid references/values/schema rejected, current database unchanged, restore path stays in managed directory; text beginning spreadsheet formulas is safe in CSV output.
- [ ] Implement versioned backup/validated restore to a new managed workspace, download templates and safe exports. Pass the transfer suite, commit and ledger.

### Task 4: Operational interface and access protection

**Files:** Security, demo and app modules; security/app tests; Streamlit config.

**Interfaces:** App uses only the Task 1–3 shared interfaces. `FLEET_DATA_DIR` selects the private storage root, `FLEET_MODE=local|production`; production requires `FLEET_PASSWORD_HASH`.

- [ ] Write failing security tests: salted scrypt round trip, malformed/cost-abusive hashes, fail-closed production configuration, failed-login throttling, session expiry and credential changes.
- [ ] Implement bounded scrypt verification with constant-time comparison, configured single-workspace login, persistent throttling and expiring server-side sessions. Keep CSRF/CORS protections enabled.
- [ ] Write failing actual-AppTest flows: empty real workspace; create vehicle, record purchase, select week, export and correct/void; explicit demo mode; unauthenticated production access blocked.
- [ ] Implement navigation, concise forms, import mapping/preview/confirmation, vehicle management, review outcomes, scenarios, history/export/restore and persistent fiction banner. Include logout and actionable error states; display private data only after the gate.
- [ ] Pass focused app/security checks; inspect desktop/mobile and the actual browser flow. Commit and ledger.

### Task 5: Deployment, evaluation and full release verification

**Files:** Docker/Compose/config, CI, operating guides, updated assessment/evaluation docs, verification report.

**Interfaces:** Container runs as a non-root user; persistent operational volume, healthcheck, required production password, loopback published port and no credentials or personal records in the build context.

- [ ] Package locked dependencies, healthcheck and restart configuration; document TLS reverse-proxy requirements, backups, restore, password setup and upgrade procedure. Verify container execution when Docker is available; otherwise explicitly record the untested packaging boundary.
- [ ] Write the recurring-workflow pilot protocol and demonstration runbook. Update README primary entry point and distinguish operational evidence from the historical research baseline.
- [ ] Run full `python -m pytest tests/ -q`, the full government pipeline, repeat dashboard export checks and confirm operational records survive the pipeline. Run syntax/build/config checks and inspect generated evidence for matching provenance.
- [ ] Dispatch one fresh whole-change reviewer as required by executing-plans/requesting-code-review. Address material findings with failing-then-passing tests and rerun affected/full checks.
- [ ] Record exact observed verification, remaining deployment/user-study limits and screenshots. Commit release files without the user's unrelated pilot-protocol edit; keep branch local.

## Execution record

Authorisation: user approved the written design and requested continuation to production grade. Execution remains inline in the existing feature checkout. Preserve the user's uncommitted `docs/evaluation/pilot_protocol.md` edit. No publication, remote deployment or merge is authorised by this plan.

Production grade here means a tested, durable, protected single-workspace release with recovery and deployment instructions. Real-world demand, measured benefit, production-host operation and multi-tenant isolation require their own evidence.
