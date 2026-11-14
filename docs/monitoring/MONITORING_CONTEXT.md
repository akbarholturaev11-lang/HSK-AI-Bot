# Unified error monitoring — context

The single context file for this work: state, decisions and session log.
The checklist is only `openspec/changes/unified-error-monitoring/tasks.md`;
goals are in `docs/monitoring/REQUIREMENTS.md`; the design (D1–D11) is in the
same OpenSpec change. A checked task is not proof of passing tests, promotion
or production acceptance.

## Current state

- **Merged:** feature head `224d9f0b3e8798832210bb27601ae79347be61af` was merged
  by PR #308. On 2026-11-14, the remote ref was verified at
  `ba499cd38c1c6105a348ee9a5436cabc3c7880be`.
- **Done in code:** task 1.1 (catalog, registry block in `declare` mode, checker,
  workflow, `AGENTS.md` rule); task 1.2 (migration `0156_diagnostic_monitoring`,
  models, `ingest`, retention, switches); task 1.3 (intake routes, backend
  middleware and reporter, Lava and AI/voice sites, chain helper, `server` cells
  `partial`); task 2.1 (Android reporter in `core/diagnostics`, both flavours;
  `android` cells `partial` for the instrumented features); task 2.2 (learner
  browser reporter and PWA transport, content-pinned assets, Live Voice and
  priority flow hooks, PostgreSQL PWA chain); task 3.1 (Admin Inbox and
  audit, resolve/reopen, diagnostic freshness); task 3.2 (bounded Apple Push
  on the existing outbox); task 4.1 (signed Mini App transport and additive
  legacy adapter). The English public privacy copy for 5.2 is prepared.
- **Promotion CI:** PR #308 completed with 29 successful checks. Pinned
  Chromium and WebKit checks passed. The macOS native-auth check was cancelled
  because its runner configuration is unsupported; one duplicate
  progressive-browser check was skipped. Both Analytics runs passed 322 tests,
  skipped 30, and proved 20 runtime chain pairs: [PR run](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/43577080310),
  [feature branch push run](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/43577075893).
- **Production deployment:** Railway reported deployment
  `d5a9c7f5-88db-46b5-ab10-2e1f557fc377` for commit `ba499cd3` successful and
  online (1/1 replicas), created 2026-11-14 09:35 UTC. This was the normal app
  deployment triggered by the merge, not an isolated migration-only rollout.
  The production DB revision was not independently read. Railway exposed the
  names of the monitoring switches but redacted their values, so their
  effective production state is unknown. Their source defaults are off.
- **Still open (task 5.2):** no isolated Railway staging environment was
  available; Android Direct/Play physical acceptance, iPhone Safari and
  Apple Push display/tap on iPhone and Mac, Mini App staging regression, and
  Play Data safety filing remain unverified. Production deployment and CI do
  not substitute for those checks.

## Independent audit (2026-11-13–14)

Compared the implementation at `b0bd6778` with the verified remote
`main` at `33dca055`. Graphify's report matched the audit starting commit.
The extracted graph identifies `ingest → decide_alert → enqueue_automatic_alert`
and `unified_inbox → _diagnostic_rows`. The outbox table and network/credential
edges were checked in source and tests: graph paths crossing test imports or
inferred matching names are not runtime evidence.

Coverage repair: the shared registry's `monitoring.critical_paths` maps
important dependencies to exact feature/platform pairs. The same required
check evaluates their Git diff even when entry points are unchanged. New shared
dependencies need explicit bindings; the checker does not infer dynamic calls.
The two historical diagnostic-only exceptions for AI provider and the signed
onboarding runtime are pinned to their source contents. Later edits do not
inherit them.

Retention repair: hourly housekeeping can commit up to eight batches of
1,000 receipts instead of one, releasing database locks and its diagnostic
pool slot after each batch. The public notice distinguishes the 30-day
affected-account window from physical cleanup. The PostgreSQL backlog test
seeds 8,003 expired receipts, verifies the first pass deletes 8,000, and
checks that the next pass removes the remainder and preserves a fresh
receipt and the open incident.
Resolved incidents also wait for their last receipt to be purged. A locked
receipt cannot cause cascade deletion or hold up the resolved-incident pass.

| Finding | Correction and regression evidence |
| --- | --- |
| Android could send account A's queue with account B's bearer; a device ID is reusable. Late requests and stale uploader results could also cross sessions. | Fence capture and upload by the server-issued session ID, keep the worker out of auth refresh, and scope queue removal to the originating session. Keep the JVM owner-switch and late-response cases. |
| A PWA diagnostic session probe could adopt unverified events as another account, and storage errors discarded reports. | Bind to the app's verified document actor, never adopt pre-auth events, fence the delivery response, and keep bounded in-memory fallback. |
| Monitoring could occupy the shared pool; the legacy Mini App mirror could hold up the original event reply. | Limit diagnostic writers before they open a session, bound PostgreSQL statements/locks, and move the additive legacy mirror after commit to bounded background work. Preserve the existing technical message, Push and AI context. |
| Intake admitted overly broad version text; refused events could create empty incidents; recovered or delayed pre-Fixed observations could reopen incidents. | Platform version grammar and client-only sites, no incident creation on refusal, and timestamp/outcome checks at the existing locked triage transition. Accepted UUIDs remain idempotent; refused UUIDs are not persisted and refused counts represent observed attempts. |
| Scope escalation depended on the Push toggle; failed reopen enqueue had no retry; a paused outbox could later deliver stale alerts. | Escalate the Inbox independently using failed distinct owners only, retry an unsent reopen on a new occurrence, and cancel diagnostic outbox rows older than 30 minutes before sending. The payment and legacy priority and transport stay unchanged. |
| A populated DB with receipts but no triage/outbox could silently lose data on downgrade. | Migration 0156 refuses downgrade while any diagnostic data remains. Operational rollback is flags off with the additive schema retained. |
| CI missed three mounted Voice WebSockets and flavour-only Android packages, and an unchanged URL could hide a materially changed handler. A green push-only check might have compared only its last push. | Inventory all 261 mounted learner routes, include Direct/Play packages, require coverage or a fresh exact exemption on changed surfaces, and compare feature push checks against the default-branch fork point. Android and learner browser workflows also trigger on this feature branch. |
| GitHub had no rule requiring CI on `main`. | [Active main ruleset](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/rules/27213316) requires the GitHub Actions `analytics-integrity` check, up to date with main, with no bypass actors. At the time of this original audit, the remote main ref had not changed; promotion was later completed through PR #308 as recorded above. |

Independent verification on the implementation commit:

- Local CI suite: 273 passed, 470 subtests and 20 runtime-proven pairs.
  Separate focused login, checkout/Pro, analytics and shell run: 184 passed;
  Lava, block, Voice and migration regression run: 74 passed. These suites overlap.
- PostgreSQL 0156: clean upgrade/downgrade/upgrade, populated downgrade refusal,
  and real app `off → owners → off` with one authorized receipt and no push.
  The synthetic 1M-receipt plans used the owner and incident indexes (about
  0.36 ms admission, 21.72 ms five-incident aggregate, 57.45 ms retention
  candidate lock locally; these are not production latency).
- Android API 36: both debug QA flavours ran Keystore refresh → actual HTTPS
  bearer bootstrap → controlled Course 502 → WorkManager → PostgreSQL →
  authenticated Inbox. Direct 725 and Play 667 JVM tests passed; the first
  Play attempt hit a transient pre-existing Voice coroutine teardown error.
  Local lint and both R8 release bundles passed.
- Learner Chromium and WebKit against local HTTPS and migrated PostgreSQL:
  real PWA session and map, uncaught error, offline retry with the same
  UUID, cross-tab account replacement, authenticated checkout and Voice
  pages, signed Telegram Mini App error and authenticated Inbox all passed.
  The Telegram SDK ran in a browser; no physical Telegram WebView was tested.
- Admin Chromium: bearer intake, real PostgreSQL, virtual WebAuthn and
  UZ/RU/TJ Fixed → reopen passed. The real Web Push encoder produced an
  encrypted, VAPID-signed request; decryption yielded only `kind` and
  `source`. The test intercepts HTTP before it leaves the machine.
- The GitHub [Analytics run](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/43461334435)
  and [Backend/PWA run](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/43461333953)
  passed for `c0468aaf`. The [Android run](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/43461334201)
  caught a short-name collision in the static checker: the new queue's
  test-only `size()` was mistaken for Compose `Modifier.size(width, height)`.
  Renamed the queue helper to `queuedCount()` so the guard stays intact.
  At `c2bd8dd8`, both Android JVM suites, lint and R8 release bundles passed
  again locally. [Analytics CI](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/43550687853)
  passed 273 tests and 20 runtime chains on that commit. Its
  [Android CI](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/43550687823)
  is separate from the local evidence.
- The independent full-suite run found seven Smart Reminder lifespan failures
  from an unbound shutdown dependency in the extracted-lifespan contract
  test. Bind the same production reporter locally in the shutdown block and
  run the Smart Reminder observer and runtime modules in the shared CI suite.
- Unrelated, reproducible on both `33dca055` and the branch: the local
  Playwright 1.63 Practice layout shifts about 38–44 px at 320 px in normal
  and reduced motion. Neither engine showed it on pinned GitHub CI. This
  audit did not change Practice layout. Also reproduced on both revisions:
  the Mini App requests `/assets/hsk-launch-gold.mp3` and receives 404, even
  though the file is in the repository under `app/static/assets/`.
- Residuals: no client attestation (authenticated clients can still fabricate
  bounded diagnostics); lost/refused reports make impact partial. A hard
  process stop may lose in-memory reports, and an unusually large backlog can
  delay physical receipt cleanup even though projections exclude expired data.
  Signed-out browser failures are never assigned to the next account. Main's
  Railway deployment succeeded, but that does not verify production switch
  values, physical clients, or push display/tap.

**Analytics Impact:** no KPI writer or entitlement authority changes.
Diagnostic freshness remains an additive source and the V10, checkout,
learning and Telegram separation tests verify the existing projections.

**Monitoring Impact:** account binding, admission, triage, alert delivery and
coverage proof are hardened in the existing chain. The merged code has a
successful Railway production app deployment. A Chromium virtual passkey and
a locally decrypted VAPID Web Push request are not physical Apple Push
acceptance. Device/browser/provider and rollout gates below are still required.

## Task 5.1 evidence (local unless specified)

- Shared checker in push and pull-request mode, and the backend/PWA policy
  with `--enforce-change-tests`, passed. The [feature Analytics integrity
  run](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/43412786216)
  passed. The [follow-up Analytics run](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/43414811984)
  passed 222 tests and proved 20 feature/platform pairs through the real
  intake and authenticated Inbox. The [final code commit’s CI run](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/43417721339)
  passed the expanded suite. Its matching local run passed 255 tests and 463
  subtests, with the same 20 runtime-proven pairs.
- Scratch CI [rejected both an unmapped learner route and Android
  package](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/43412956667)
  and [passed once they mapped to covered Lessons and the scratch route was
  proved end to end](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/43413255740).
  The synthetic route and package are only on the scratch branch.
- Admin PWA Playwright: main Inbox/Statistics browser suite plus MCP consent,
  minimal Inbox, settings, outbound, campaigns and payout passed. Diagnostic
  list, one-tap Fixed and reopened detail verified at 390 px in UZ/RU/TJ.
  PostgreSQL Admin lock/regression list: 75 passed; the separately configured
  Smart Reminder suite passed 270 tests (12 skips), and the dedicated
  native account/Lava PostgreSQL suite passed 182 tests. Focused monitoring,
  retention and dispatch: 63 passed. Onboarding, PWA auth, Pro, referrals,
  legacy push and standalone QA bootstrap: 254 passed. Three targeted
  Telegram Mini App browser onboarding regressions also passed. Compared
  all 132 cases in `test_miniapp_smoke.py`, `test_miniapp_app_routing.py` and
  `test_pwa_telegram_handoff_page.py` with the same Chromium runtime and
  synthetic fixtures on `e7e6641a` and `fb0865a8`: 105 passed and the exact
  same 27 failed on each, with zero feature-only failures. This comparison
  records local test behavior; it does not certify a deployed Mini App.
- Learner Node, focused Chromium/WebKit diagnostics, cache versions and
  worker asset budget passed. The [GitHub Linux performance workflow](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/43414756219)
  passed all 68 tests per browser with the pinned tools, plus backend and
  policy jobs. Local macOS Chromium/WebKit (Playwright 1.63)
  showed the same two Russian Practice skeleton geometry failures at 320 px
  on both `e7e6641a` and the monitoring feature. An isolated repeat of the
  Chromium reduced-motion case gave the same 43.4 px group shift on both.
  This is a local comparison, not evidence of a prior CI or production
  failure; it did not reproduce on GitHub CI. A timing-dependent
  partner/Postgres test also varied locally;
  it passed in the dedicated Admin Postgres run.
- Android: `testPlayDebugUnitTest testDirectDebugUnitTest`, `lint` and
  `bundlePlayRelease bundleDirectRelease` passed. Actual R8 DEX extracted from
  the Direct release AAB serialized a synthetic `diag.v1` batch on Android ART
  (API 36 emulator) with all nine required wire fields. Physical acceptance
  remains separate.
- PostgreSQL: migration 0156 upgrade/downgrade and the populated downgrade
  guard passed locally. Synthetic 1M-receipt `EXPLAIN (ANALYZE, BUFFERS)`:
  admission used the owner/time index (~0.03 ms); five-incident affected
  counts used the incident/time index (~39 ms with ~67k matching receipts).
  Times describe this fixture, not production.
- OpenSpec strict validation, generated localization catalog, protected-source
  baseline (zero blockers), Python and JS syntax and single Alembic head passed.
- Full non-browser comparison: the starting commit ran
  `pytest -q --ignore=tests/e2e --tb=no tests` with 5,381 passes, 3 failures
  in stale initializer/head checks and 771 skips. The first feature run
  found four source guard failures and one timing-sensitive Postgres case.
  The guards were re-anchored after confirming 62 locale lines/130 predicates
  and all direct/indirect lesson reads still matched byte for byte; the
  isolated partner and initializer checks passed on rerun.
- Final code `fb0865a8`: collected 6,170 tests across all 499 non-browser
  modules, then ran each module once with `pytest -q --tb=short` in six
  parallel groups, each with its own disposable PostgreSQL database.
  **5,399 passed, 771 skipped, zero failed; 85,238 subtests passed.** The
  expanded Analytics CI and staging rehearsal cover the changed runtime.

## Staging readiness (5.2)

- **Local rehearsal, not staging:** from the reviewed empty ORM baseline,
  applied the real Alembic chain to `0155_subscription_entry_client` in a
  disposable loopback PostgreSQL database. Ran
  `python -m alembic upgrade 0156_diagnostic_monitoring` by itself. The stamp
  advanced to `0156_diagnostic_monitoring`; the seeded technical triage row
  was preserved and both new tables started empty. On that schema, the real
  app ASGI intake returned paused in `off`, dropped a non-owner and admitted
  an owner in `owners`, and stopped writing again in `off`. The single owner
  receipt was visible in the authenticated Inbox; push stayed off.
- **Remote target:** Railway lists no `staging` environment for the HSK AI
  app project. The existing separate Smart Reminder QA service is scoped to
  its own synthetic application. Its bootstrap is not an upgrade mechanism
  for an existing database. PR #308 triggered the successful production app
  deployment recorded above; it was not staging or a migration-only deploy.
  The production DB revision was not independently read. Monitoring variable
  values were redacted, so do not infer the effective production switches.
  Identify an approved isolated target before any staging write; the separate
  QA service remains out of scope.
- **If a target becomes available:** record its project, environment, app and
  DB pairing; verify isolated synthetic credentials, no live integrations,
  no production routes and exactly one database revision. From a verified
  0155 database, run the pinned 0156 migration separately with all monitoring
  switches off. Verify the new revision and preserved legacy sources before
  starting the candidate application. The normal startup script upgrades to
  head automatically and launches production workers; it is not the
  migration-only or isolated staging entrypoint. A version mismatch stops
  rollout rather than being corrected by stamping.
- **Acceptance:** run owner/non-owner intake and a controlled staging 5xx,
  then the Android Direct/Play, iPhone Home Screen and Telegram flows. Use
  staging-only accounts and a controlled Admin push receiver; verify the
  actual notification, authenticated tap and Fixed → repeat → reopen on
  iPhone and Mac. A device that already received a paused response can
  suppress reporting for 24 h; use a fresh staging test install/session
  when checking a just-enabled switch. Restore `off` and verify the absence
  of new receipts. Do not infer push display from provider acceptance.
- **Before public enablement:** verify the deployed `/privacy` wording and
  the owner’s Play Console Data Safety filing. The monitoring delta is
  Crash logs and Diagnostics; reconcile it with the existing declaration.
  The local rehearsal and successful app deployment do not establish public
  rollout readiness. Do not change live flags or publish an APK until the
  remaining staged and owner-approval checks are recorded.

## Joint Analytics and Monitoring audit (5.3, merged to main)

- **Analytics Impact:** no new KPI events or writer changes. Diagnostic
  freshness adds only the three client-source rows. The V10 golden test and
  Telegram chain verify the projection boundary and no double counting.
- **Monitoring Impact:** authenticated content-free client failures and
  ownerless backend failures have a separate receipt/incident path to Admin
  Inbox. PostgreSQL and runtime proof cover intake, deduplication, deletion,
  triage and bounded push. A signed Telegram batch writes no Message or KPI
  row; the legacy Message, technical push and AI context remain intact.
  Android, PWA and Telegram diagnostic intake failures do not report
  themselves. Shared CI enforces both registries and the writer boundary.
- This audit covered the feature branch and was completed before PR #308
  promotion. The remote `main` ref and successful production deployment are
  verified above. Staging, physical Apple Push/Safari/Android checks and the
  Play Data safety filing remain separate and open under task 5.2.

## Drift check (task 1.1)

- **Historical preimplementation check:** `main` `33dca055` differed from the
  audited `5ea7c22f` only by plan documents; no `app/`, `android/`, `.github/`
  or `scripts/` change was found at that point. The later feature implementation
  was promoted through PR #308.
- Voice V8 (`origin/feat/ai-voice-v8-pwa-android-20261111`) is still at
  `680761f1` and not on `main`, so the `live_*` codes in the catalog follow the
  current merged `main` sources. Recheck the mappings if Voice V8 is later
  promoted.

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
  switched-off feature (for example `pwa_auth_unavailable`). Other 5xx and
  unhandled exceptions are captured. Integration failures behind a 503 and
  unexpected Live Voice relay failures report through `report_server_failure`.
- **Lava sites.** Only processing-failure alert codes become incidents
  (`LAVA_FAILURE_SITES` in `lava/notify.py`: exhausted webhook retries →
  `lava_webhook`; activation, amount, unmatched, review, renewal, promo →
  `lava_ledger`). Expected webhook auth rejection and business outcomes do
  not enter diagnostics. Every code still sends its Telegram alert unchanged.
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

- **Android owner stamp.** The Android queue is stamped with the verified
  bearer session ID (`sid`), not `device.id`, which may be reassigned.
  A signed-in event can only be delivered using its original session.
  Content-free errors captured before the first verified sign-in may be
  adopted by that initial session, but existing-owner events are purged
  on logout or replacement. The server still derives the canonical account
  only from the verified bearer.
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

- **Browser queue.** Bind each open document to the account verified by its
  application code. A stale document cannot append to a replacement account's
  queue; pre-verification PWA errors are not adopted. Session CSRF is used only in
  the request header. The worker's 40-asset limit is unchanged; it does not warm
  the course document, which is already open when warm-up starts.

- **Inbox and push.** The affected count is a distinct-account count over
  retained receipts, with explicit `partial`/`unknown` states. Resolve and
  reopen lock the incident before triage. Reopens create an audit entry; a
  separate outbox reason identifies the exact epoch even if the incident
  changes later. Existing sources dispatch ahead of new diagnostic alerts.
- **Mini App.** `X-HSK-Diagnostic: diag.v1` selects bounded JSON intake on the
  existing endpoint and requires fresh signed Telegram init data. The browser
  keeps Telegram reports in memory only. Legacy onboarding still writes its
  original Message and sends its technical push before the optional adapter.
- **Analytics separation.** Diagnostics use their own tables and Inbox,
  including no writes to course or conversion KPI stores. Freshness adds
  diagnostic rows only, under the bumped Analytics snapshot key. The shared
  guard checks the writer/event boundary and runs with `require_covered`.

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
- 2026-11-13: completed tasks 3.1–4.1 and began 5.1; the monitoring
  surface is ready for staged acceptance after the remaining gates.
- 2026-11-14: PR #308 merged feature head `224d9f0b` into `main` at
  `ba499cd3`; required Analytics CI passed (322 passed, 30 skipped, 20 runtime
  chain pairs). Railway production app deployment for `ba499cd3` succeeded
  and came online. Task 5.3 is complete; isolated staging, production DB
  revision/switch verification, physical device and Apple Push acceptance,
  and Play Data safety filing remain open in 5.2.
