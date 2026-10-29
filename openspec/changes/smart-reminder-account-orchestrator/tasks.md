# Tasks

Checked boxes require the bounded task's source/test evidence; OpenSpec validation alone is planning evidence, not implementation or release acceptance. Master Plan §17.27 records the P0 source-audit acceptance and its external limits. Use the [Master Plan](../../../docs/smart-reminders/SMART_REMINDER_MASTER_PLAN.md) as the sole phase and decision ledger. Refresh `origin/main`, actual Alembic head and affected source before each implementation slice.

## 1. P0 — source and cutover proof

- [x] 1.1 Inventory all current Telegram course/motivation/weekly, Android FCM and WorkManager, campaign and transactional senders in `app/main.py`, service paths and client callbacks; deliver a source-linked ownership/category/claim diagram in the Master Plan and verify its paths against the refreshed HEAD.
- [x] 1.2 Trace Telegram saved-time ON, setup Cancel and any actual OFF action; Mini App `/api/v3/notify`; Android current Profile/onboarding local switch, legacy motivation API, `/push/preferences`, study OS channel and real user-action evidence. Deliver a source-cited ON/OFF/unknown/time/provenance matrix and verify the existing focused preference/notification tests match the stated bindings.
- [ ] 1.3 Inventory historical Direct/Play installed APK versions, local autonomous WorkManager behavior, backend worker/replica configuration, FCM study flag and live Alembic stamp through authorized staging/release evidence; record unknowns and a testable migration exclusion rule in the Master Plan. Verify no old offline sender is called fenced merely from `app_version` or inactivity.

  Evidence: Master Plan §§17.29–17.33 records the completed live reads, signed-artifact audit, anonymous inventory and bounded two-APK entry checks. **Owner-deferred:** remaining installed/mixed-build/fencing acceptance stays open for P4 tasks 5.3–5.4 before canary. Do not expand this audit or repeat finished inventory reads; proceed with dispatch-OFF P1. Counts/update screens do not prove fencing.
- [x] 1.4 Audit canonical lesson/practice/daily goal, timezone/deep-link/access, D1 holdout, bot block and account-deletion paths; deliver an event-trust/deletion map with source and focused existing-test identifiers. Run the affected baseline tests and record exact outputs in the Master Plan before marking P0 complete.

## 2. P1 — additive storage and consent bridge, dispatch off

- [x] 2.1 Add reviewed SQLAlchemy/Alembic preference, source consent/capability, account-day job and attempt storage after the actual head; verify unique user/day study ownership, FK cleanup and non-destructive upgrade/downgrade with SQLite and PostgreSQL migration checks. Record the schema/data preservation rule in the Master Plan.
- [x] 2.2 Implement a read-only legacy evidence bridge with idempotent versioned backfill; verify Telegram course ON/time, setup Cancel, Android local/device mirror conflict, motivation default True, OS study denial, all OFF and native-only cases in focused migration tests. Verify no new study send occurs while dispatch remains off.
- [x] 2.3 Add Android bearer and verified Telegram init-data Smart preference read/CAS write adapters plus bot callback revision binding; verify strict booleans, IANA zones, idempotent retry, stale r versus r+1 OFF conflict, forged device, blocked/pending-deletion account and legacy API response compatibility in focused API tests. Document the request/error contract beside the implementation.
- [x] 2.4 Wire account OFF/grant epoch, channel OFF and deletion/revocation invalidation across new pending jobs; verify OFF survives old API sync, migration rerun and rollback, and that unrelated motivation, subscription and payment decisions retain their existing tests. Document the opt-out/retention hook and currently unresolved D13 TTL class values.

## 3. P2 — deterministic policy, shadow jobs and due worker

- [x] 3.1 Implement pure server policy over verified learning signals, current progress and accessible lesson targets; verify completed-goal, course switch, blocked Pro target, sparse history, manual override, personal quiet/pause and real 02:00 habit cases in focused tests. Record actual source coverage and reason codes in the Master Plan.
- [x] 3.2 Implement adaptive cadence and individual reactivation using server-confirmed learning, with a hard one-study-intent/account/local-day bound; verify distinct daily versus twice-weekly inactivity, decreasing ineffective cadence, eventual stop and restart without fixed 3/7/14-day assumptions. Submit any new weekly/stop thresholds to the Master Plan decision process before enabling those policies.
- [x] 3.3 Build account-scoped job reservation, frozen IANA day/UTC window, leases and durable due processing with all external IO after commit; verify two replicas, worker restart, missed tick, DST/fractional zone/date-line travel and provider-accepted-before-commit crash tests. Document suppression/expiry semantics and the physical-display limitation.
- [x] 3.4 Add shadow-only category coordination for study/rank/weekly while preserving transactional routing; verify D1 holdout and study/rank/weekly collisions, useful weekly defer, fail/slow Admin PWA poller isolation and no provider sends from shadow. Record comparison evidence and unresolved cross-category values in the Master Plan.
- [x] 3.5 Define the D15 platform-neutral widget projection from shared verified learning/time/goal/access context, with an additive authenticated map contract, version/expiry/owner-day-zone-course binding and minimal cache fields. Verify shared golden fixtures for sparse/02:00 habits, manual time, completion versus reward XP, pause/OFF, inaccessible targets, native-only and blocked/deletion accounts; publish the contract and reason codes beside the implementation without sending notifications.

## 4. P3 — Telegram ownership and canary

- [x] 4.1 Make the legacy Telegram course sender consult verified cohort ownership and current master OFF before activating the new study adapter; verify one Telegram study send under two schedulers, old callback/stale OFF, bot block and native-only exclusion with fake Bot integration tests. Document exact cutover/rollback cohort checks.
- [x] 4.2 Add Telegram Smart rendering/inbox/CTA through canonical UZ/RU/TJ sources and existing admin template precedence; run catalog `--write` and `--check`, then focused DB roundtrip/language-switch and deep-link/access tests. Reproduce and separately fix the existing `template_service` persistence mismatch only if confirmed by the test; record the finding without changing source lesson/scoring data.
- [ ] 4.3 Enable only a verified Telegram-only allowlisted canary after shadow evidence; run real Telegram account/opt-out/D1/locale and rollback checks in authorized staging, record provider acceptance separately from read/learning and save results in the Master Plan. Do not count a code test as real send acceptance.

## 5. P4 — Android protocol and mixed-build cutover

- [ ] 5.1 Add authenticated study-specific capability, selected-job due/claim and truthful receipt routes without reusing `/android/notices/{id}/ack`; verify ownership, blocked/deletion, revoked device, stale epoch, OS study channel denial and account-notice channel independence in focused backend tests. Document the versioned protocol.
- [ ] 5.2 Update `StudyReminderCoordinator`, `StudyReminderWorker`, FCM handler and `WidgetStore` so both triggers claim the same server job and compatible clients fail closed offline; verify same-install races, delayed FCM, logout/relink epoch, master OFF and local permission revocation in Android JVM/instrumented checks. Keep local durable guard and direct/Play parity.
- [ ] 5.3 Verify actual signed Direct/Play compatible builds and historical APK behavior before per-account migration. Run two-device mixed-build/old offline APK tests; keep unknown old-autonomous accounts excluded from central cross-channel dispatch and record the precise physical-display limit in the Master Plan.
- [ ] 5.4 Canary one compatible Android device, then eligible Telegram plus two-device accounts only after capability/consent/fencing evidence; run real FCM/OS permission/late hint/unknown ACK/definite non-display fallback checks. Verify one authorized logical job and no blind alternate, and record real-device results and rollback in the Master Plan.
- [x] 5.5 Consume the shared D15 projection in existing Android WidgetCoordinator/WidgetSnapshot/WidgetStore/WidgetVisualResolver and layout, preserving Direct/Play parity, installed cache decoding, art and normal navigation. Verify resolver/store tests for personal phase, completed-day calm, neutral cold/stale/quiet state, reward-XP exclusion, track/zone changes, late old-account responses and logout; record mapping to shared golden fixtures.
- [ ] 5.6 Validate Android widget pin/resize/refresh/tap, offline/future/expired context, midnight/DST, notification OFF and denied permission, canonical UZ/RU/TJ and rollback in an isolated launcher. Verify passive rendering creates no study intent, provider attempt, permission prompt or learning receipt; document OS refresh limits and distinguish JVM results from real widget/device acceptance.

## 6. P6 — outcomes, experiments and protected administration

- [ ] 6.1 Instrument reason-coded candidate/suppressed/reserved/provider-accepted/client-posted/verified-shown/opened/server-learning outcomes with deduplication, finite retention and purge hooks; verify replay, missing display proof, opt-out, account deletion and privacy-safe aggregate tests. Document class-specific TTLs after a privacy review, with no personal job state in 24-hour R2 snapshots.
- [ ] 6.2 Measure real eligible cohort baseline and traffic; version D7 learning retention, active study days, completions, MDE, sample/power, observation period and guardrails for owner decision. Verify low-traffic/immature cohorts remain unavailable and D1/control assignment never receives treatment on another channel; record actual evidence in the Master Plan.
- [ ] 6.3 Add one minimal Admin PWA Smart control/readout using existing protected passkey/audit/template paths and real source-backed aggregates; verify role/session revocation, kill-switch live authority, null/unknown metrics, UZ/RU/TJ and the Admin PWA minimal-action contract in focused API/browser tests. Document metric grains and never label accepted/opened as shown or learned.

## 7. P7 — evidence-gated optimizer

- [ ] 7.1 Build privacy-minimized, versioned model features and offline validation against the functioning rule baseline; verify stale/low-quality signals, leakage and underrepresented platform/locale cohorts in reproducible evaluation artifacts. Record approved eligibility, retention and experiment gates before ML can dispatch.
- [ ] 7.2 Add automatic per-user rules-to-validated-ML selection with reversible fallback under all consent, access, manual lock and account-day guards; verify threshold crossing, model outage/regression and reserved-job replay in focused tests. Report actual randomized lift and safety evidence, or keep rules active if unproven.

## 8. P5 — later learner PWA and desktop adapters

- [ ] 8.1 Add learner iPhone Home Screen PWA push only after real install, HTTPS, service-worker scope, user-gesture permission and account binding checks; verify unsupported browser/denied/offline cases suppress safely and shared account-day tests pass. Document browser capability and cleanup evidence.
- [ ] 8.2 Add paired macOS/Windows desktop OS adapters with equivalent account preference/claim/receipt/deep-link behavior; verify parity, logout/device revocation and multi-platform single-job cases on both installed clients. Record OS-specific limitations in the Master Plan.
- [ ] 8.3 Add an iOS widget adapter only after a real supported host/WidgetKit extension, protected account/session bridge and refresh/privacy capability are implemented. Verify the same D15 projection/golden fixtures, stale/offline/locked-device rendering, safe navigation and logout/deletion on an installed target; do not count iPhone PWA push or an Android build as iOS widget support.
- [ ] 8.4 Add paired macOS/Windows widget adapters using supported OS providers and the unchanged D15 account projection, without duplicating habit rules. Verify shared fixtures and real installation, auth/storage, refresh budget, privacy, safe targets and removal/rollback on both OSes; preserve DMG/EXE feature parity and document any supported equivalent when an OS host is unavailable.

## 9. P8 — integration and release evidence

- [ ] 9.1 Run affected backend, Android, localization, Admin PWA and account-notice regressions plus staging migration backup/restore; verify source lesson, scoring, auth, entitlement, payment, Play/direct and Telegram SDK contracts remain intact. Record command outputs and refs in the Master Plan.
- [ ] 9.2 Drill kill-switch rollback during pending, accepted-unknown and explicit-OFF states; verify pending grants expire, no ambiguous replay or blind legacy resume, consent revisions persist and a destructive schema downgrade is refused. Record observed provider/device behavior and remaining limitations.
- [ ] 9.3 Complete monitored staged canary and real Telegram/two-Android-device acceptance, reconcile all old study senders, experiment guardrails and owner acceptance; record exact commit, CI, staging, device and rollout evidence in the Master Plan before marking P8 or the feature complete.

## Workflow follow-up

- Archive this OpenSpec change only after implementation and the project's acceptance gates have actually passed. Update `PROJECT_MEMORY.md` only for durable implemented architecture, schema and business invariants.
