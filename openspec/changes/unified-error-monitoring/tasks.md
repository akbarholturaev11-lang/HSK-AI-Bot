# Tasks

This is the only checklist for this work. Task 1.1 creates the single shared context file (state, decisions, session log). Do not create any other progress or handoff file. A checked box is not proof of passing tests, promotion or production acceptance. Decision IDs (D1–D11) refer to `design.md`.

**Test conventions:**
- Python: run tests with `.venv/bin/python`, and write async tests as `unittest.IsolatedAsyncioTestCase`.
- PostgreSQL: local TCP PostgreSQL, a fresh database per module, `LC_ALL=en_US.UTF-8`.
- Playwright: compare runs with a pre-change baseline worktree, and report skipped runs as skipped.
- Android: JVM tests run for both flavours; instrumentation runs on Direct only.

**UI work** (task 3.1 Admin list and drawer; the `/privacy` sentence in 5.2): load the `hsk-ai-ui` skill and follow `BROWSER_UI_CONTRACT.md` and the localization rule. Before editing, state the weak points, the exact patch, the files and the risk (`AGENTS.md` risk-based UI audit), then make small patches.

**Scope reminders:**
- Desktop is frozen: no Desktop code, tests or CI.
- No vendor SDK and no new infrastructure.
- Nothing merges to `main` without the owner's approval.

## 1. Foundation: catalog, coverage guard, intake

- [x] 1.1 Context file and the P0 coverage guard in `declare` mode (D1, D10):
  - Create `docs/monitoring/MONITORING_CONTEXT.md` as the single context file, starting from the 2026-11-13 audit in design.md.
  - Before coding, check drift since `5ea7c22f` with `git diff --stat` over the Context paths. Check the voice `live_*` codes if Voice V8 has landed. Use read-only Graphify only after the graph matches `HEAD`. Apply any delta to design.md.
  - Add `app/services/monitoring/catalog.py`.
  - Generate the registry `monitoring` block once from the source inventory, then review it, with honest statuses and the frozen `legacy_baseline`.
  - Extend `scripts/check_analytics_coverage.py`: optional `monitoring` in `validate_schema`, a route-parameterized `validate_chain`, prefix-aware route inventory, the critical-path consistency rule and the `--chain-proof` mode. Extend `analytics-integrity.yml` with `MONITORING_CHAIN_PROOF` and the post-pytest proof step.
  - Add the `AGENTS.md` Monitoring Impact rule, with its enforcement status stated as it exists.

  Verify:
  - `tests/test_analytics_coverage_contract.py` passes unchanged.
  - `tests/test_monitoring_coverage_contract.py`: each of these fails and names its cause:
    - an unmapped new route (route and file), including one added through a router prefix or `add_api_route`;
    - an unmapped Android package or PWA page;
    - an unknown reporter literal;
    - a route mapped against its Analytics critical-path flows;
    - baseline growth, or a lowered status without an exemption;
    - a directory-wide or empty-reason exemption;
    - `covered` with a test outside the workflow or missing the intake/Inbox literals;
    - `covered` without a proof row (a skipped or literal-only chain test);
    - a duplicate feature ID;
    - `declare` mode while the `diagnostic` Inbox source exists.
  - A cosmetic-only change passes.
  - A scratch push shows the job failing on an unmapped route.
  - `openspec validate unified-error-monitoring --strict` passes.
- [x] 1.2 Add the migration (next number after `0155`), models and the `ingest` service (D2, D3, D8):
  - the tables and source CHECKs, with the downgrade guard;
  - advisory-lock admission and the receipt/incident upserts;
  - refused counts;
  - `MONITORING_MODE`;
  - the purge in `_desktop_auth_retention_scheduler`, in its own `try`.

  Verify:
  - **Migration:** upgrade and downgrade on local PostgreSQL.
  - **Unit tests:** forbidden, unknown and oversized events are rejected; a retry is idempotent; a skewed client time is flagged; `off` pauses and `owners` admits only owners.
  - **PostgreSQL module:** two workers produce one incident with count 2; the cap holds under parallel requests; account deletion cascades the receipts and lowers the affected count; the purge is bounded, and a purge failure does not skip the native-report purge (`test_admin_pwa_retention_links.py` stays green).
  - **Query plans:** `EXPLAIN` on 1M receipts for the admission and affected-count queries.
- [x] 1.3 Add the intake routes and the backend reporter (D3, D4):
  - Android bearer and PWA cookie + CSRF routes;
  - the ASGI middleware over `route_map`;
  - `report_server_failure` at the Lava and AI/voice provider sites, next to the Lava Telegram `admin_alert`, never replacing it;
  - self-incidents;
  - the shared chain helper `tests/monitoring_chain.py` (intake → PostgreSQL, then the proof row);
  - registry `server` entries.

  Verify:
  - **Route tests:** auth is required; a client owner ID, fingerprint or severity is rejected; blocked and revoked accounts are refused; `off` returns the paused response.
  - **Middleware tests:** a 5xx or an exception is recorded once and the response is unchanged; a 4xx is not recorded, including the 403 from `BlockedUserApiMiddleware`; saturation drops are counted; no body is read.
  - **Lava test:** a Lava activation failure records one incident and still sends its Telegram `admin_alert` with the same code, throttle and recipients.
  - **Performance:** the backend part of `backend-pwa-performance-contract` passes.

## 2. Android and PWA reporters

- [x] 2.1 Add the Android reporter (D5) in `core/diagnostics`, for both flavours:
  - the crash handler;
  - exit reasons on API ≥ 30;
  - tagged `apiCall` failures for login, lesson open/complete, practice, progress, subscription/payment and handoff, hooked inside `apiCall` (`ApiResult.kt`) and reusing the `toApiError()` result;
  - the `LiveVoiceSocket.fail` client-side reason allowlist;
  - the owner-bound AtomicFile queue with WorkManager flush;
  - `channel`;
  - R8 keep rules.

  Registry Android entries are `partial` with "Admin consumer pending 3.1".

  Verify:
  - **JVM tests** (`testPlayDebugUnitTest testDirectDebugUnitTest`): offline, timeout, 4xx, limit and paywall are not reported; a 5xx and a 2xx decode failure are reported once, and the error body is read only once; an unexpected live-voice connection loss is reported once, while a learner close, a server limit code or backpressure is not; a crash record is written without network and the previous handler still runs; an exit reason is reported once; queue cap, TTL and backoff hold, and drops become one `queue_dropped` event; an account switch purges the queue; 401/403 drops it.
  - **Release builds:** `bundlePlayRelease bundleDirectRelease`, plus a Direct release smoke that the DTO serializes.
  - **Chain test:** `tests/test_monitoring_android_chain.py`, bearer intake → PostgreSQL incident.
- [x] 2.2 Add the learner web reporter `course_v3_data/hsk-diagnostics.js` (D5) with the PWA transport. Include it with a `?v=` token in `course-v3.html`, `course_v3_li_onboarding.html` and the PWA practice, checkout and voice pages. Report the `voice-live.js` client-side failure codes, and hook the D5 priority call sites. Registry PWA entries are `partial` with "Admin consumer pending 3.1".

  Verify:
  - **Node test:** category mapping; no message, stack or URL in the payload; loop guard; coalescing; owner-mismatch discard; TTL and the `queue_dropped` event; the voice allowlist reports client-side codes only.
  - **Playwright, Chromium and WebKit:**
    - an error or rejection sends one POST with CSRF;
    - offline → online sends once with the same `event_id`;
    - an account switch discards the queue;
    - 401 drops it.
  - **Performance and assets:** the performance-contract browser suites match the baseline; the asset-version tests pass; each page stays within the 40-asset warm limit of `iphone-pwa-sw.js`.
  - **Chain test:** `tests/test_monitoring_pwa_chain.py`.

## 3. Admin Inbox and Apple Push

- [x] 3.1 Add the Inbox `diagnostic` source (D6):
  - projection, platform filter, affected state;
  - triage mapping, the resolve hook, and auto-reopen with a system audit row;
  - the D6 list row and drawer, with the existing "Тузатилди ✅" button (one tap, plain `resolve`, no prompt) and the "🔁 fixed error came back" line; strings in `localization/ui/*/miniapp.json` (`i18n_build_all_catalogs.py --write` and `--check`);
  - `diagnostic` in the `app.js` source allowlists (rows, icon and label, `data-inbox-open`) and the `?inbox=diagnostic` deep link;
  - the Report freshness `diagnostics` source, latest client receipt per platform, inside the Analytics snapshot (D11).

  Extend the shared chain helper, and with it the 1.3, 2.1 and 2.2 chain tests, to read `/api/admin/v1/inbox/list`. Flip the priority flows on Android, PWA and server to `covered`; they leave the baseline.

  Verify:
  - **Projection:** one item per incident; no forbidden field or account ID in the response or the page; `partial` and `unknown` states; unauthorized reads refused.
  - **Triage:** opening an incident moves it from new to read, and "Fixed" resolves it in one tap with no prompt and no learner notice, each step audited; reopen on the same or a newer version shows the "came back" line in all three languages; an older version stays resolved; a backend incident reopens.
  - **Analytics:** `test_admin_pwa_report_freshness.py` covers the `diagnostics` rows; `test_admin_pwa_v10_regression.py` changes only the freshness shape.
  - **Browser:** Admin PWA Playwright at 390 px in three languages, with screenshots of the row, the drawer and the "came back" line; the contract tests show no new control.
  - **Registry:** the checker passes with the flipped entries.
- [x] 3.2 Add bounded push (D7):
  - outbox and dispatcher allowlists, with the epoch key;
  - the `_relevant` `diagnostic` branch, and `kind: "reopened"` from `last_alert_reason`;
  - the alert decision in an intake savepoint;
  - per-incident cooldown and global cap, with reopen alerts exempt;
  - the `sw.js` labels for `diagnostic` and its `reopened` kind, and the `/admin/?inbox=diagnostic` link, applied after auth.

  Registry `mode` switches to `require_covered` as soon as the Inbox source exists (D10).

  Verify:
  - 100 identical critical events give at most one outbox row per device;
  - a non-critical incident sends no push;
  - a `high` incident reaching the account threshold alerts once;
  - a reopen of a fixed incident at any severity alerts once with the "came back" label, even during a flood or within the cooldown;
  - the global cap holds;
  - payment and Android alerts still dispatch during a diagnostic flood, and Lava Telegram admin alerts are sent unchanged;
  - an enqueue failure does not fail intake;
  - the payload is `{kind, source}` only, and `reopened` is ignored for any other source;
  - `test_admin_pwa_push_outbox.py`, `test_admin_pwa_push_dispatch.py` and the `sw.js` test in `test_admin_pwa_shell.py` pass;
  - the coverage contract passes in `require_covered`.

## 4. Mini App compatibility

- [x] 4.1 Add the additive Mini App adapter (D9, owner option A):
  - the `diag.v1` path to `ingest`;
  - the legacy onboarding mapping to `ingest`, in addition to today's `technical` path;
  - the `MONITORING_MINIAPP_ADAPTER_ENABLED` switch;
  - the Telegram transport in `hsk-diagnostics.js`;
  - the `clog` audio/mic mapping;
  - registry `telegram` entries, with the chain test, `covered`.

  Verify:
  - legacy onboarding `app_error` still writes its `messages` row and still sends its per-error `technical` push, with the adapter on or off; the bot AI context and the `technical` listing are unchanged;
  - with the adapter on, 30 identical errors give 30 `technical` pushes and one incident with 30 occurrences;
  - with the adapter off, or the mode `off`, no incident is written and everything else is as today;
  - `diag.v1` writes no `messages` row, and a caller `user_id` is ignored;
  - the Analytics experiments count and the `admin_miniapp_service` error counts are unchanged;
  - the existing Telegram tests pass for `/api/miniapp/event`, onboarding, lesson flow, login, Pro and referral.

## 5. Validation and staged acceptance

- [x] 5.1 Integration validation, compared with the baseline:
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
  - Open: PR #308 triggered a normal Railway production app deployment; there was no isolated staging or migration-only deployment. The production database revision was not independently read, and the effective monitoring switch values are redacted. This deployment does not satisfy the checks below.
  1. In isolated staging, deploy the migration alone and verify its revision and preserved legacy rows.
  2. Staging, then `owners` on production.
  3. Android Direct and Play: a crash, an ANR if it can be reproduced, an API 5xx, offline → retry, an account switch.
  4. iPhone Safari home-screen PWA: a JS error, a rejection, offline → retry, an owner switch.
  5. Mini App onboarding regression; a forced backend 5xx on staging.
  6. Admin PWA push on iPhone and Mac, and the tap opens the diagnostic Inbox. Tap "Тузатилди ✅", repeat the error, then confirm the "came back" push and Inbox line arrive.
  7. The kill switch stops writes.
  8. Push on, then adapter on, each with owner approval.
  9. Before `all`: the `/privacy` sentence and the owner's Play Data safety filing, as worded in the design Migration Plan. Then `all`, with owner approval.

  Verify by recording the evidence. A push accepted by the provider is not proof that it was displayed.
- [x] 5.3 Joint Analytics/Monitoring integration audit (REQUIREMENTS §11), then promotion. Completed 2026-11-14.
  - PR #308 merged feature head `224d9f0b3e8798832210bb27601ae79347be61af` into `main` at `ba499cd38c1c6105a348ee9a5436cabc3c7880be`; the remote `main` ref was verified.
  - CI: 29 successful checks; pinned Chromium and WebKit passed. One macOS native-auth check was cancelled because its runner configuration is unsupported; one duplicate progressive-browser check was skipped.
  - Both Analytics runs passed (322 passed, 30 skipped, 20 runtime-proof pairs): [PR](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/43577080310), [main push](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/43577075893).
  - Railway reported the `ba499cd3` production app deployment successful and online; deployment details and unresolved staging/device acceptance are in `MONITORING_CONTEXT.md`.
  - Audit covered both Impact rules and the shared workflow, Analytics event versus incident/Inbox separation, privacy, deduplication, non-blocking behavior and regressions. The merged `main` rule records registry/checker/workflow enforcement.
  - This completes source integration and promotion only. Real staging, physical device, Apple Push display/tap and Play Data safety acceptance remain open in 5.2.

## Workflow follow-up

- Archive with `openspec archive unified-error-monitoring` only after verified completion.
