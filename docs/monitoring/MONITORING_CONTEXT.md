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
  `partial`).
- **Not yet run:** PostgreSQL tests (chain and intake) — they run in task 5.1.
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

## Session log

- 2026-11-13: task 1.1 implemented on the feature branch (256 learner routes
  mapped, 22 features, 86 baseline pairs, 2 justified `not_applicable`).
- 2026-11-13: task 1.2 implemented (migration after `0155`, intake service).
- 2026-11-13: task 1.3 implemented (two intake routes, middleware, reporter,
  Lava/AI sites, chain helper and server chain test).
