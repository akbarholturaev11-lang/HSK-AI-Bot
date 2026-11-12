# Tasks

This is the only checklist for this work. Task 1.1 creates the single shared context file (state, decisions, session log). Do not create any other progress or handoff file. A checked box is not proof of passing tests, promotion or production acceptance. Decision IDs (D1–D11) refer to `design.md`.

**Test conventions:**
- Python: run tests with `.venv/bin/python`, and write async tests as `unittest.IsolatedAsyncioTestCase`.
- PostgreSQL: local TCP PostgreSQL, a fresh database per module, `LC_ALL=en_US.UTF-8`.
- Playwright: compare runs with a pre-change baseline worktree, and report skipped runs as skipped.
- Android: JVM tests run for both flavours; instrumentation runs on Direct only.

**Scope reminders:**
- Desktop is frozen: no Desktop code, tests or CI.
- No vendor SDK and no new infrastructure.
- Nothing merges to `main` without the owner's approval.

## 1. Foundation: catalog, coverage guard, intake

- [ ] 1.1 Re-audit on the then-current `main`, with Analytics PR #285 merged or this work stacked on it. Confirm or correct the design.md Context: signals, Inbox/triage/push, transports, migration head, route inventory. Create `docs/monitoring/MONITORING_CONTEXT.md` as the single context file, and apply any deltas to design.md. Verify: every Context row cites code, and `openspec validate unified-error-monitoring --strict` passes.
- [ ] 1.2 Land the P0 coverage guard in `declare` mode (D1, D10):
  - add `app/services/monitoring/catalog.py`;
  - generate the registry `monitoring` block once from the source inventory, then review it, with honest statuses and the frozen `legacy_baseline`;
  - extend `scripts/check_analytics_coverage.py` and `analytics-integrity.yml`;
  - add the `AGENTS.md` Monitoring Impact rule, with its enforcement status stated as it exists.

  Verify `tests/test_monitoring_coverage_contract.py`. Each of these fails and names its cause:
  - an unmapped new route (route and file);
  - an unmapped Android package or PWA page;
  - an unknown reporter literal;
  - baseline growth, or a lowered status without an exemption;
  - a directory-wide or empty-reason exemption;
  - `covered` with a test outside the workflow or missing the intake/Inbox literals;
  - a duplicate feature ID;
  - `declare` mode while the `diagnostic` Inbox source exists.

  A cosmetic-only change passes. A scratch push shows the job failing on an unmapped route.
- [ ] 1.3 Add the migration, models and the `ingest` service (D2, D3, D8):
  - the tables and source CHECKs, with the downgrade guard;
  - advisory-lock admission and the receipt/incident upserts;
  - refused counts;
  - `MONITORING_MODE`;
  - the purge in the hourly loop.

  Verify:
  - **Migration:** upgrade and downgrade on local PostgreSQL.
  - **Unit tests:** forbidden, unknown and oversized events are rejected; a retry is idempotent; a skewed client time is flagged; `off` pauses and `owners` admits only owners.
  - **PostgreSQL module:** two workers produce one incident with count 2; the cap holds under parallel requests; account deletion cascades the receipts and lowers the affected count; the purge is bounded.
  - **Query plans:** `EXPLAIN` on 1M receipts for the admission and affected-count queries.
- [ ] 1.4 Add the intake routes and the backend reporter (D3, D4):
  - Android bearer and PWA cookie + CSRF routes;
  - the ASGI middleware over `route_map`;
  - `report_server_failure` at the Lava and AI/voice provider sites;
  - self-incidents;
  - registry `server` entries.

  Verify:
  - **Route tests:** auth is required; a client owner ID, fingerprint or severity is rejected; blocked and revoked accounts are refused; `off` returns the paused response.
  - **Middleware tests:** a 5xx or an exception is recorded once and the response is unchanged; a 4xx is not recorded; saturation drops are counted; no body is read.
  - **Performance:** the backend part of `backend-pwa-performance-contract` passes.

## 2. Android and PWA reporters

- [ ] 2.1 Add the Android reporter (D5) in `core/diagnostics`, for both flavours:
  - the crash handler;
  - exit reasons on API ≥ 30;
  - tagged `apiCall` failures for login, lesson open/complete, practice, progress, subscription/payment and handoff;
  - the owner-bound AtomicFile queue with WorkManager flush;
  - `channel`;
  - R8 keep rules.

  Registry Android entries are `partial` with "Admin consumer pending 3.1".

  Verify:
  - **JVM tests** (`testPlayDebugUnitTest testDirectDebugUnitTest`): offline, 4xx, limit and paywall are not reported; a crash record is written without network and the previous handler still runs; an exit reason is reported once; queue cap, TTL and backoff hold, and drops become one `queue_dropped` event; an account switch purges the queue; 401/403 drops it.
  - **Release builds:** `bundlePlayRelease bundleDirectRelease`, plus a Direct release smoke that the DTO serializes.
  - **Chain test:** `tests/test_monitoring_android_chain.py`, bearer intake → PostgreSQL incident.
- [ ] 2.2 Add the learner web reporter `course_v3_data/hsk-diagnostics.js` (D5) with the PWA transport. Include it with a `?v=` token in `course-v3.html` and the PWA practice, checkout and voice pages. Registry PWA entries are `partial` with "Admin consumer pending 3.1".

  Verify:
  - **Node test:** category mapping; no message, stack or URL in the payload; loop guard; coalescing; owner-mismatch discard; TTL and the `queue_dropped` event.
  - **Playwright, Chromium and WebKit:**
    - an error or rejection sends one POST with CSRF;
    - offline → online sends once with the same `event_id`;
    - an account switch discards the queue;
    - 401 drops it.
  - **Performance and assets:** the performance-contract browser suites match the baseline; the asset-version tests pass.
  - **Chain test:** `tests/test_monitoring_pwa_chain.py`.

## 3. Admin Inbox and Apple Push

- [ ] 3.1 Add the Inbox `diagnostic` source (D6):
  - projection, platform filter, affected state;
  - triage mapping, the resolve hook, and auto-reopen with a system audit row;
  - list and drawer UI with UZ/RU/TJ catalog text (`i18n_build_all_catalogs.py --write` and `--check`; `BROWSER_UI_CONTRACT.md`);
  - the Report freshness `diagnostics` family, latest receipt per platform (D11).

  Extend the 1.4, 2.1 and 2.2 chain tests to read `/api/admin/v1/inbox/list`. Flip the priority flows on Android, PWA and server to `covered`; they leave the baseline.

  Verify:
  - **Projection:** one item per incident; no forbidden field or account ID in the response or the page; `partial` and `unknown` states; unauthorized reads refused.
  - **Triage:** new → assigned → resolved, each step audited; reopen on the same or a newer version; an older version stays resolved; a backend incident reopens.
  - **Analytics:** the golden test changes only the freshness shape.
  - **Browser:** Admin PWA Playwright at 390 px in three languages.
  - **Registry:** the checker passes with the flipped entries.
- [ ] 3.2 Add bounded push (D7):
  - outbox and dispatcher allowlists, with the epoch key;
  - the alert decision in an intake savepoint;
  - per-incident cooldown and global cap;
  - the `sw.js` label and the `/admin/?inbox=diagnostic` link, applied after auth.

  Set registry `mode` to `require_covered` in the same change.

  Verify:
  - 100 identical critical events give at most one outbox row per device;
  - a non-critical incident sends no push;
  - a `high` incident reaching the account threshold, and a critical reopen, alert once each;
  - the global cap holds;
  - payment and Android alerts still dispatch during a diagnostic flood;
  - an enqueue failure does not fail intake;
  - the payload is `{kind, source}` only;
  - the `sw.js` test passes;
  - the coverage contract passes in `require_covered`.

## 4. Mini App compatibility

- [ ] 4.1 Add the Mini App adapter (D9):
  - the `diag.v1` path to `ingest`;
  - the legacy onboarding mapping;
  - the per-row `technical` push is skipped for admitted events;
  - the single `MONITORING_MINIAPP_CUTOVER_AT` switch and the `technical` listing filter;
  - the Telegram transport in `hsk-diagnostics.js`;
  - the `clog` audio/mic mapping;
  - registry `telegram` entries, with the chain test, `covered`.

  Verify:
  - legacy onboarding `app_error` still writes its `messages` row, and the bot AI context is unchanged;
  - with the adapter on, no `technical` push for admitted events;
  - with the mode `off`, or for a non-owner in `owners`, the `technical` item and push stay as today;
  - with the cutover unset, the current behavior returns;
  - `diag.v1` writes no `messages` row, and a caller `user_id` is ignored;
  - the existing Telegram tests pass for `/api/miniapp/event`, onboarding, lesson flow, login, Pro and referral.

## 5. Validation and staged acceptance

- [ ] 5.1 Integration validation, compared with the baseline:
  - `openspec validate --strict`;
  - the checker in push and PR modes;
  - the full unit suite (only known baseline failures);
  - every PostgreSQL module on a fresh DB;
  - the Analytics CI list and the golden test;
  - the Admin PWA Playwright suites;
  - the performance contract;
  - Android unit tests, lint and release bundles;
  - a scratch-branch CI proof: a new learner route and Android package without monitoring fail, and pass once `covered`.

  Verify by recording the commands and results in the context file.
- [ ] 5.2 Staged rollout and real-device acceptance, recorded separately from CI:
  1. The migration deploys alone.
  2. Staging, then `owners` on production.
  3. Android Direct and Play: a crash, an ANR if it can be reproduced, an API 5xx, offline → retry, an account switch.
  4. iPhone Safari home-screen PWA: a JS error, a rejection, offline → retry, an owner switch.
  5. Mini App onboarding regression; a forced backend 5xx on staging.
  6. Admin PWA push on iPhone and Mac, and the tap opens the diagnostic Inbox; resolve → reopen.
  7. The kill switch stops writes.
  8. Push on, adapter on, then `all`, each with owner approval.

  Verify by recording the evidence. A push accepted by the provider is not proof that it was displayed.
- [ ] 5.3 Joint Analytics/Monitoring integration audit (REQUIREMENTS §11), then promotion. Audit:
  - both Impact rules and the one workflow;
  - KPI event → Analytics versus incident → Inbox, with no double counting;
  - privacy, dedup and non-blocking behavior;
  - regressions.

  Set the `AGENTS.md` enforcement status only for mechanisms on `main`. Promote with owner approval. Verify the `main` commit through the remote ref.

## Workflow follow-up

- Archive with `openspec archive unified-error-monitoring` only after verified completion.
