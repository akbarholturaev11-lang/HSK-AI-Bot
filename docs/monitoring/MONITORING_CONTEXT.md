# Unified error monitoring — context

The single context file for this work: state, decisions and session log.
The checklist is only `openspec/changes/unified-error-monitoring/tasks.md`;
goals are in `docs/monitoring/REQUIREMENTS.md`; the design (D1–D11) is in the
same OpenSpec change. A checked task is not proof of passing tests, promotion
or production acceptance.

## Current state

- **Branch:** `feat/unified-error-monitoring-20261113`, from `main` `33dca055`.
  Owner instruction (2026-11-13): push each finished part to this branch; tests
  and verification run together at the end (task 5.1), then promotion.
- **Done in code:** task 1.1 (catalog, registry block in `declare` mode, checker,
  workflow, `AGENTS.md` rule); task 1.2 (migration `0156_diagnostic_monitoring`,
  models, `ingest`, retention, switches); task 1.3 (intake routes, backend
  middleware and reporter, Lava and AI/voice sites, chain helper, `server` cells
  `partial`); task 2.1 (Android reporter in `core/diagnostics`, both flavours;
  `android` cells `partial` for the instrumented features); task 2.2 (learner
  browser reporter and PWA transport, content-pinned assets, Live Voice and
  priority flow hooks, PostgreSQL PWA chain). Next: task 3.1, Admin Inbox.
- **Local validation:** PWA Node, Chromium/WebKit diagnostics, asset budget and
  authenticated PostgreSQL chain passed. The existing 320 px Practice
  skeleton geometry cases fail on both the baseline `e7e6641a` and this work;
  keep them visible at the task 5.1 gate. Full integration validation,
  Android release builds and the Direct DTO smoke remain for 5.1.
- **Not on `main`.** No migration, intake, reporter or Admin change is deployed.
  All switches will default off.

## Drift check (task 1.1)

- `main` `33dca055` differs from the audited `5ea7c22f` only by the plan
  documents; no `app/`, `android/`, `.github/` or `scripts/` change.
- Voice V8 (`origin/feat/ai-voice-v8-pwa-android-20261111`) is still at
  `680761f1` and not on `main`, so the `live_*` codes in the catalog follow the
  current `main` sources. Re-check them if V8 lands before task 2.1/2.2.
- Graphify was not re-run; nothing in the monitored code moved.

## Implementation decisions (within the design)

- **Checker layout.** Monitoring checks live in `scripts/monitoring_coverage.py`,
  imported by `scripts/check_analytics_coverage.py`. One registry, one checker
  run, one workflow; the module only keeps the Analytics file readable.
- **Catalog loading.** The checker executes `app/services/monitoring/catalog.py`
  by path (stdlib only), never importing the app package.
- **Which registry cell each source checks.** Learner routes check the feature's
  `server` cell (backend capture), Android feature packages the `android` cell,
  learner pages the `iphone_pwa` cell. The `telegram` cell is checked through its
  entries only (Mini App compatibility).
- **Critical-path consistency.** A route in an Analytics critical-path file maps
  to one of that path's flows or a monitoring-only ID. For a symbol-scoped path
  (`app/main.py`, `miniapp_practice.py`) only the listed handlers are bound.
  This is why, for example, `/api/v3/pwa/push/*` maps to `app_shell` and the
  `/api/v3/trial/*` routes in `miniapp_entitlements.py` map to `lessons`.
- **Sites.** `site_code` is validated against one bounded catalog set
  (`ALL_SITES`: client sites, integration sites and one site per learner route).
- **Severity.** `severity_for()`: the failure's default, one step up in
  `CRITICAL_FEATURES` (checkout, PWA Pro checkout, auth session), one step down
  for a client-confirmed recovery.
- **Runtime chain proof.** `covered` entries need a row
  `platform|feature|failure` written by `tests/monitoring_chain.py` (task 1.3)
  into `MONITORING_CHAIN_PROOF`; the post-pytest `--chain-proof` step checks it.

- **Receipts store more than D2 lists, all content-free:** `build` (comparable
  Android versionCode / PWA token date), `category` (a catalog category),
  `client_time_untrusted` and `occurrences` (coalesced backend writes). Incidents
  add `last_build`, `resolved_build`, `reopened_at` and `reopened_version` for the
  version-aware reopen and the "came back" line.
- **Client time** is epoch milliseconds. Outside ±7 days it is not stored and the
  receipt is flagged untrusted; ordering uses the server receive time.
- **`owners` stage** admits client events only from accounts whose Telegram ID is
  in `ADMIN_IDS`. Owner-free backend rows are admitted in `owners` and `all`.
- **Account deletion** deletes receipts explicitly in `UserRepository._delete_account`
  (the repository does not rely on FK cascades), besides the FK `ON DELETE CASCADE`.
- **Retention** runs in `_desktop_auth_retention_scheduler` in its own `try`.
- **503 is not captured** by the middleware: the codebase answers 503 for a
  switched-off feature (for example `pwa_auth_unavailable`). Captured: 500, 502,
  504 and unhandled exceptions. Integration failures behind a 503 report through
  `report_server_failure`.
- **Lava sites.** Only processing-failure alert codes become incidents
  (`LAVA_FAILURE_SITES` in `lava/notify.py`: webhook auth and retries →
  `lava_webhook`; activation, amount, unmatched, review, renewal, promo →
  `lava_ledger`). Refund/chargeback/partner-credit alerts are business outcomes,
  not failures. Every code still sends its Telegram alert unchanged.
- **AI provider.** `AIProviderChain.chat_completion` serves several features; a
  final failure is filed as `chat_ai` at the `ai_provider` site (the site is what
  identifies the provider). STT failures are `voice_practice` / `voice_provider`.
- **Blocked accounts on Android.** A bearer access token outlives a block until
  it expires (`authenticate` does not check the status), so the Android intake
  refuses blocked accounts itself. The PWA actor already refuses them.
- **Registry `server` cells** are `partial` with an "Admin consumer pending"
  reason. The baseline stays: pairs leave it only when they become `covered`
  (task 3.1).
- **Chain helper.** `assert_monitoring_chain(case, platform, feature, failure,
  site, sessions, …)` requires a PostgreSQL bind. Client platforms post through
  their real intake; the server chain runs through a `BackendReporter`, with an
  optional `trigger` (a real middleware request or `report_server_failure`).

- **Android owner stamp.** The Android client never learns its `users.id`; the
  queue is stamped with the bootstrap device session ID (`device.id`), which
  belongs to exactly one account. Sign-in binds it (events queued before sign-in
  are adopted by that account); logout, expiry or an account switch purges the
  queue. The server still takes the owner only from the bearer session.
- **Android 503.** `apiCall` reports `api_5xx` for every 5xx except 503, the
  backend's "switched off" answer, matching the server middleware.
- **Android cancellation.** `apiCall` keeps mapping a cancelled call to
  `ApiError.Unknown` as before, but never reports it.
- **Android AtomicFile.** The queue and crash record use write-temp, fsync,
  rename in plain Java I/O (same guarantee as `android.util.AtomicFile`), so the
  queue logic runs in JVM tests; files live in `noBackupFilesDir/diagnostics`.
- **Android crash feature** comes from the selected main tab (Course → lessons,
  Practice → practice, Voice → voice_practice, Rating → learning_rewards,
  Profile → app_shell). Exit reasons are `app_shell` / `process`; a `REASON_CRASH`
  within 60 s of a recorded JVM crash is not reported twice; the first run only
  sets the last-seen mark.
- **Android tagged calls.** Sign-in (link start/poll, OAuth start/assert) →
  `auth_session/login`; refresh and bootstrap → `auth_session/session_restore`;
  course map → `lessons/progress`; lesson open/unlock → `lessons/lesson_open`;
  completion → `lessons/lesson_complete`; onboarding → `onboarding_activation`;
  practice and drills → `practice`; subscription overview → `subscription_entries/
  subscription`; legacy subscription open → `subscription_entries/handoff`;
  checkout and Lava (Direct) → `checkout_payments/payment`.
- **Android flush.** Unique work `diagnostics_flush` (KEEP, network required,
  exponential backoff from 30 s, at most 3 attempts), scheduled after the first
  frame and after each queued event while signed in. Batches of 20. A `paused`
  answer stops queueing for 24 h and empties the queue; 401/403 drops it; other
  4xx drop the batch; 5xx and transport errors retry.

- **Browser queue.** Bind each open document to its verified account. A stale
  document cannot append to a replacement account's queue. Pre-verification
  errors stay in memory while verification is pending and are discarded on a
  signed-out reply; no anonymous report is sent. Session CSRF is used only in
  the request header. The worker's 40-asset limit is unchanged; it does not warm
  the course document, which is already open when warm-up starts.

## Session log

- 2026-11-13: task 1.1 implemented on the feature branch (256 learner routes
  mapped, 22 features, 86 baseline pairs, 2 justified `not_applicable`).
- 2026-11-13: task 1.2 implemented (migration after `0155`, intake service).
- 2026-11-13: task 1.3 implemented (two intake routes, middleware, reporter,
  Lava/AI sites, chain helper and server chain test).
- 2026-11-13: task 2.1 implemented (Android reporter, JVM tests, Android chain test).
- 2026-11-13: resumed at task 2.2 from `e7e6641a`, with the reporter draft and
  Live Voice edits present locally. Completed the PWA integration and focused
  verification; diagnostic visibility and full coverage proof wait for 3.1.
