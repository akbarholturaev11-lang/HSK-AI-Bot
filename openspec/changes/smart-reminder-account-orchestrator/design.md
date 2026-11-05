# Design

## Context

See [proposal.md](proposal.md) for the problem and [the authoritative Master Plan](../../../docs/smart-reminders/SMART_REMINDER_MASTER_PLAN.md) §§3, 11, 13 and 17 for approved D01–D15 scope, phase gates and evidence. The core proposal originally used `origin/main@6693901cca909189313dbb1b2747499206114598`; the D15 extension uses the refreshed source below. Executed bridge/test/operational evidence belongs to the Master Plan, while central dispatch and personal widget rendering remain proposed. Before each implementation slice, refresh affected source and Alembic head. Remaining fleet/topology/provider acceptance is scoped to activation gates; do not repeat completed reads or expand the owner-deferred historical audit during dispatch-OFF P1.

**D15 extension source refresh:** widget planning is audited against `origin/main@d897f65b9ca89f4936d6a58ad27e6283115dc6db`. Earlier operational unknowns are historical: bounded live reads are in Master Plan §17.29, signed-APK inspection/current offline regressions in §17.30, and the widget delta in §17.31. The implemented legacy evidence bridge grants no dispatch. This extension changes the proposed design only; it does not implement a widget API, new renderer or transport.

**P1 source refresh (2026-10-28):** `origin/main@bedd14addc9e98ec9952c61d5e4b28685ed72fd1` includes PR #247: Direct and Play use one admin-selected window (source default 4) over separate confirmed published-release histories. Play uses Play Core; unknown/incomplete history yields no cutoff. Direct/Play refresh on foreground resume. The former fixed-gap/Play-pass-through description in historical Master Plan §17.33 applies only to its old source pin. This foreground update gate still is not a study-worker claim/fence. Current source Alembic head remains `0132_admin_pwa_campaign_schedule`. The owner's deferred historical audit does not block dispatch-OFF P1; it remains a P4/P8 activation gate. New private R2/advisory-lock analytics changes remain aggregate-only, never Smart consent or live job authority.

**P1 preference refresh (2026-10-28):** verified `origin/main@a784ea4127502faf5c97404064c5a4314fcad516` already contains 0133 storage and the internal version-1 backfill. This slice adds 0134 retry receipts and authenticated preference adapters (§3.3); the 0132 head above belongs to its earlier pinned refresh. No new client settings screen, dispatch, old-sender cutover or production acceptance is implied.

Current call paths relevant to the design:

| Current path | Verified source behavior and resulting constraint |
| --- | --- |
| `app/main.py::_background_scheduler` | A per-process 60-second loop runs Admin PWA due campaigns, motivation, Android study, transactional account-notice fallback, Telegram course reminders, weekly summaries and other senders sequentially under one outer exception boundary. A slow/failing earlier step can miss a later narrow study window. Bounded production observations are in Master Plan §17.29; a one-replica observation never removes overlap/restart requirements. |
| `app/services/course_reminder_service.py`, bot `app/bot/handlers/course.py`, `CourseProgress` | Telegram course study uses saved ON/time and an integer time-zone offset, checks `last_reminder_sent_at` by local day, sends through the Bot API, then records/commits. The save-time callback enables study; setup Cancel clears only workflow state. There is no account-wide reservation before Bot IO. |
| `app/main.py:/api/v3/notify`, `CourseMiniAppProfile`, `MotivationReminderService` | The Mini App toggle controls motivation; the profile field defaults True, and the old route coerces a missing `enabled` to True. Motivation also owns existing D1 holdout and ranking/streak intents. None is proof of a new study-channel grant. |
| `app/services/android_realtime_push_service.py`, `app/api/android_push.py`, `AndroidPushToken` | Server FCM study hints use per-device ON/time zone and a fixed hour; an accepted provider result is written as `last_study_push_day` only after IO. `notifications_allowed` currently reflects the account-notice channel, not study-channel permission. Existing account-notice acknowledgement and ten-minute fallback are separate. |
| Android `MainActivity.kt`, `WidgetStore.kt`, `StudyReminderCoordinator.kt`, `StudyReminderWorker.kt`, `HskAiMessagingService.kt` | The current Profile switch is per-install local study ON. FCM and WorkManager both call a local coordinator; `WidgetStore.remindOnce` protects one installation/day/epoch, but no server job is consulted. §17.30 identifies stale-cache refusal in three inspected signed APKs; uninspected/unknown installed senders remain unfenced. Repo version metadata does not identify the installed fleet. |
| `DesktopAuthService.authenticate()`, account deletion | Native bearer authentication verifies session/device ownership but does not itself reject a blocked user in the inspected method; new Smart routes need their own blocked/deletion guard. `UserRepository._delete_account` already performs explicit dependent cleanup; new Smart rows/caches require integration. |
| Localization, feed and admin | `localization/README.md` owns UZ/RU/TJ fixed copy and generated clients. Existing `CourseNotificationService.record()` persists params only when `template` exists, while motivation sends `template_service`; future inbox re-rendering needs a focused persistence test and separately scoped fix. Existing Admin PWA metrics/cache are not a live consent or job store. |
| Android `widget/WidgetCoordinator.kt`, `WidgetState.kt`, `WidgetVisualState.kt`, `WidgetRefreshWorker.kt`, `HskAiSmartWidget.kt` | The existing authenticated map projects personal level/current lesson/XP/streak/today completion/goal into an epoch-bound cache. Freshness checks age, local day and device zone. Panda urgency still uses fixed 05/10/14/18/20/22 hour boundaries; stable per-install art variants are not learned habits. Refresh/render and study-notification authorization are separate responsibilities. |

The proposed system is V1 Telegram bot/Mini App plus Android, with a channel-neutral core so learner iPhone PWA and macOS/Windows can be added as V2 adapters. The future V2 transport cannot be treated as available during V1 routing.

## Goals / Non-Goals

**Goals:** make canonical account consent and one logical study job the only authority for *new* Smart dispatch; retain each source's category and channel permission; bound retries conservatively; provide reversible cutover gates, truthful delivery evidence and privacy-safe outcomes. Keep one user-visible settings state without equating global ON to permission on every channel.

**Non-Goals:** guarantee physical exactly-once display on unknown old/offline APKs; change account/payment/receipt notice escalation, source lesson content, grading, Pro/Play access, the Telegram SDK or existing D1 experiment assignment; choose unapproved numeric weekly caps, global quiet hours, reactivation thresholds, retention periods, ML eligibility or KPI uplift. No runtime code is changed by this plan.

## Decisions

### 1. One policy owner, category-aware coordination

Use `users.id` for policy, job uniqueness, attribution and experiment allocation. Telegram ID remains a positive real transport identifier, while Android device ID must belong to that canonical user. A server-side policy service reads canonical lesson/progress, daily plan, actual study events, access and account state; a deterministic decision returns a reason-coded candidate/suppression. It coordinates study with ranking/weekly motivation to avoid collisions, yet preserves their distinct category rules. D03's hard one-study-intent/account/local-day ceiling does not silently become a one-message limit for weekly results; transactional notices keep their existing delivery system. The engine has a provider adapter boundary (`eligible`, `prepare`, `send`, `receipt`) and no V2 adapter is selectable before implementation/capability testing.

Alternative considered: keep independently scheduled Telegram/Android senders and add a shared counter after sends. This cannot prevent simultaneous sends or provider-success-before-commit replay. The new owner therefore reserves before IO and every server-controlled old study sender must honor cohort ownership before new dispatch is enabled.

### 2. Authenticated account preference with monotonic OFF

Proposed platform adapters are Android bearer and verified Telegram init-data read/patch operations backed by one preference service; bot callbacks call the same service internally. The route names and response fields sketched in Master Plan §17.18.1 are **proposed**, not existing public API. Reads expose revision, explicit/derived master state, effective channel eligibility, provenance, time mode, zone, pause and suppression without PII, tokens or fake Telegram transport. New writes accept only typed allowlisted changes plus `expected_revision` and idempotency identity. Lock and refresh the canonical `User` first, then preference/consent rows in a fixed order; compare revision in the same transaction. Stale writes return 409 and a fresh read path. A successful explicit global OFF advances both revision and a grant epoch, cancels unattempted jobs and invalidates device grants; it survives migration reruns and feature rollback. Re-enable is a current intentional action and does not add permission to a channel that remains OFF.

The Android bearer context must additionally enforce active/not-blocked account, non-revoked owning device/session and absence of an active deletion request for reads, mutations, claims and sends. Telegram init-data is verified and mapped to `users.id`. Bodies never choose `user_id`, `telegram_id` or owner device. Bot callbacks for migrated cohorts carry a server-stored interaction/revision fence; legacy callbacks without such proof may retain legacy response shape but cannot re-enable Smart after OFF. The old Mini App `/api/v3/notify` and Android motivation preferences keep their motivation meaning; `/android/push/preferences` may update legacy per-device snapshots, never the Smart master or explicit channel OFF. Old supported response shapes remain stable.

Alternative considered: last-write-wins across old/new endpoints. That allows stale APK sync or a delayed bot callback to resurrect an explicit OFF, so it is rejected.

### 3. Additive durable model and source-aware backfill

After verifying actual Alembic head at implementation time (the original pre-P1 audit ended at `0132_admin_pwa_campaign_schedule`; reviewed P1 added `0133` storage and `0134` mutation receipts, so re-read the real head before later DDL), add the smallest reviewed schema that supports:

- A per-user preferences row with monotonic revision/grant epoch, nullable explicit global override, derived legacy state, auto/manual time and channel modes, validated IANA zone, explicit quiet/pause settings and action provenance.
- Per-channel/per-device study consent with explicit ON/OFF/unknown, source category, migration key and evidence timestamp **only when actually known**. Separate a device capability row or equivalent bound observation for tested protocol generation, study-specific OS/channel permission and freshness. A client-reported app version alone is not trusted capability proof.
- One `study` logical job ledger with unique `(user_id, account_local_day, category)` or equivalent invariant, frozen zone/day window, schedule/expiry, target/access snapshot identifiers, policy/grant epoch, selected channel/device, state and suppression reason. An attempt ledger records one provider/client action, opaque attempt key, bounded lease and truthful outcome. A unique attempt idempotency key prevents retry from minting another logical job. Whether outcomes need their own table is decided from existing canonical events before migration; avoid duplicating source learning records.

Backfill is idempotent, additive and evidence-preserving. `CourseProgress.reminder_enabled=True` plus saved time is Telegram study evidence; picker Cancel is not OFF. Android `WidgetStore.reminderEnabled` is local per-install study evidence; `AndroidPushToken.study_reminders_enabled` is only a potentially stale device mirror. `CourseMiniAppProfile.notifications_enabled` (default True) and old Android `/preferences/notifications` are motivation only. `AndroidPushToken.notifications_allowed` represents account notices, not study permission. An OS study-channel denial is a separate eligibility veto. Missing/contradictory evidence remains unknown with no new study grant. A legacy selected time supplies cold-start time, not an inferred forever-manual lock. Migration never infers consent on a second channel from first-channel ON.

Alternative considered: copy all existing booleans into a single `enabled` field. The fields have different meanings/defaults and would falsely opt in learners or erase an OFF; source-aware records are required.

### 3.1 Reviewed P1 storage slice, no runtime consumers

Add migration `0133_smart_reminder_storage` after the verified source head. Five tables: `smart_reminder_preferences` (canonical user PK, nullable explicit master, nonnegative revision/epoch, auto/manual time/channel, optional genuine legacy time/offset and personal quiet/pause); `smart_reminder_consents` (unique user/channel/source key, ON/OFF/unknown, optional device, source/version, nullable actual action time); `smart_reminder_capabilities` (owned device observation, protocol generation, nullable autonomous-disable/study-OS facts and observation/expiry); `smart_reminder_jobs` (unique user/local-day/study category, frozen IANA zone/UTC window, schedule/expiry, shadow default, preference/epoch/policy, selected endpoint and lease); `smart_reminder_attempts` (job FK, unique opaque attempt key, selected endpoint, epoch, explicit expiry and truthful outcome).

User deletion cascades all five tables, including attempts through jobs. Device deletion removes capabilities; SET NULL retains consent provenance and attempt/job history, with future consumers required to reject a missing/revoked/unowned endpoint. FK existence is not ownership or eligibility proof. Storage alone validates no token, IANA zone, blocked/deletion state, consent precedence or claim; those require the subsequent authenticated services and tests. No backfill, API, worker/scheduler caller or provider IO is added in this slice. Unknown consent/capability has no affirmative default; a new job defaults to shadow. Unique logical ownership survives cancellation/retry, and unknown attempts are not converted into non-display.

The migration creates empty tables without updating legacy state or enrolling accounts. Finite job/attempt expiry is supplied explicitly by future policy; no numeric cadence/retention threshold is invented. Source action timestamps remain nullable. Empty-schema downgrade is supported; downgrade refuses if **any** new table contains data, before dropping anything. SQLite and isolated PostgreSQL checks cover preservation, constraints, uniqueness, deletion and this refusal. The QA-only empty initializer must skip these migration-owned tables and advance its reviewed head. Application rollback leaves the new tables/state intact.

### 3.2 Reviewed P1 legacy backfill boundary

An internal per-account service reads fresh evidence through the existing read-only bridge after locking the canonical user, then locks preferences. The caller owns authorization and the transaction; no startup, API, batch CLI or sender calls this service yet. Version 1 imports only into a missing/pristine preference row, advances its revision once, and leaves master consent nullable. Any explicit master value, nonzero revision/epoch, action provenance or personal time/channel/quiet/pause setting fences the entire import. Existing consent for a channel fences all legacy inserts for that channel. Replay and a newer migration version are zero-write operations. Future OFF/deletion writers must use the same user-first lock order; PostgreSQL tests exercise concurrent import and OFF.

Telegram saved ON/time becomes source-labelled historical ON; a disabled legacy flag becomes source-labelled OFF without inventing an action timestamp. Missing/incomplete evidence remains unknown. Bot blocking remains a separate live veto, never a send grant. A native-only account receives no invented Telegram transport. Genuine saved time/offset supplies cold-start evidence only, without overwriting existing time or inferring an IANA zone/manual lock. Android mirrors produce device-bound unknown records labelled ON/OFF/missing provenance; they cannot establish current local consent, OS study permission or protocol capability. Motivation defaults are ignored. Capabilities, jobs and attempts remain untouched and dispatch stays false. No schema change is needed; rollback of an uncommitted import removes only its additive rows, while application rollback must retain committed Smart OFF/state.

### 3.3 Reviewed P1 authenticated preferences / retry boundary

V1 adds GET/PATCH `/api/v3/smart-reminder/preferences` (fresh signed Telegram header) and `/api/v3/android/smart-reminder/preferences` (existing native bearer, Android-only). Bodies never select an owner/device. Authentication is checked again from fresh account/session/device columns under the canonical-user lock; blocked/unknown/submitted-deletion states are denied. Reads perform a bounded, non-persisting legacy dual-read; writes compare the observed account revision before importing initial evidence and commit the import plus one intentional revision atomically. All new delivery remains disabled; these endpoints have no client settings UI yet. Actual legacy sender/grant cancellation is task 2.4 and remains an activation prerequisite.

PATCH requires a UUID retry identity, strict integer expected revision and at least one typed allowlisted change: explicit master, the authenticated endpoint's study consent, auto/manual time and channel, known IANA zone, paired personal quiet window or timezone-aware pause. Null booleans, duplicate JSON keys, unknown/owner fields and incomplete locks are rejected. Endpoint consent is distinct from global ON and from OS/protocol proof. Android cannot grant another device or Telegram transport. Global ON retains endpoint OFF. OFF advances the grant epoch; no jobs/grants/provider IO are created by the mutation. Time/channel locks require deliberate mode plus valid values, with no preset night restriction.

Migration `0134_smart_reminder_mutations` adds a minimal user-owned retry receipt keyed by user/UUID, containing only actor binding, canonical request digest, applied revision and observed creation time. No raw request, credential, Telegram ID or response snapshot is retained. Repeating the same actor/identity/body returns the original acknowledgement even after a later OFF, without mutation; changed content/actor yields conflict. PATCH returns an acknowledgement/revision, never an old settings snapshot; clients re-read for current state. Caller owns commit/rollback; purge cascades receipts, empty downgrade roundtrips and populated downgrade refuses. Transactional receipt retention remains in D13's unresolved class policy rather than inventing a numeric TTL.

For accounts with Smart state, existing bot time pickers carry a random nonce bound in server FSM state to canonical owner/revision; callbacks recheck it and CAS through the same service. A legacy/unbound/stale callback cannot advance Smart consent or clear OFF. A valid picker can update Telegram intent/cold-start time but cannot clear global OFF, override an existing manual lock or infer an IANA manual lock. Setup Cancel invalidates the interaction only. Non-Smart callback data/response and all visible UZ/RU/TJ copy remain unchanged. New writes lock user before preferences; native session/device are freshly checked without introducing a reverse lock order against refresh. This slice grants no dispatch authority; future claims/revocation invalidation retain their stricter activation gates.

### 3.4 Reviewed P1 OFF and lifecycle invalidation boundary

Continue from verified `main@58cb5987d5721148358684b60a5835b4e742c417`. Global/endpoint OFF invalidates outstanding Smart authorizations in the same user-first transaction: advance the already reviewed preference revision/epoch once, clear active leases, cancel prepared attempts and unattempted active jobs without changing accepted/in-flight/unknown outcomes or unique day/attempt identities. Lifecycle deletion/revocation uses the same helper and advances an existing preference only; it creates no new enrollment. Account OFF disables existing course/device study booleans without changing time, motivation, account-notice permission, subscription or payment state. Endpoint OFF changes only that endpoint's legacy flag; account epoch invalidation conservatively makes all old planning snapshots unusable. Future policy must reconcile the same logical day/job rather than minting a second intent.

Deletion confirmation invalidates once before its existing commit; repeated confirmation remains idempotent. Logout/device revocation, refresh-token reuse and explicit push unregister invalidate pending state and remove the affected capability observation without rewriting durable source ON/OFF. Native refresh/revoke must acquire canonical user before session/device mutations; fresh ownership is rechecked after lookup to avoid introducing reverse locks or transferring old-account state to a reused device. Expired/blocked/unowned endpoints remain ineligible at later claim checks; no new claim API is added here.

Legacy course/FCM study senders gain fresh blocked/deletion/master/endpoint-OFF vetoes at their existing dispatch path. Existing weekly/motivation, updates and transactional providers remain independent. Typed Telegram time inputs use the same server interaction/revision fence as callbacks for Smart accounts; unbound/stale/OFF/manual-lock inputs cannot write ON or produce a saved-ON confirmation. Repository/device-sync guards prevent a stale legacy ON from bypassing that protection; legacy Android preference responses and unrelated notice/zone fields remain compatible, with no Smart consent/revision bump. Unknown Android mirror evidence alone never establishes central eligibility or verified old-client fencing.

These are suppression/invalidation guards while new dispatch stays OFF, not a new reservation engine: old provider operations already admitted before a veto and uncontrolled offline Android posts cannot be recalled or declared exactly once. `legacy_delivery_controlled=false` remains until the complete compatible-client/cutover gate; P2/P4 must establish the durable authorization/provider boundary before activation. Tests use synthetic SQLite/PostgreSQL jobs, real preference/revocation/deletion paths and mocked provider entry only; no production inventory, provider sends or unapproved retention/behavior thresholds are required.

### 4. Time, progression and deterministic policy

Use verified lesson/practice work rather than app-open, raw FCM acceptance or read absence as learning evidence. Low-data users receive useful rule-based choices immediately, retaining a genuine old time until reliable habit evidence permits adaptation. A manual time lock and explicit user quiet/pause override the estimator; no global nighttime blackout exists. Reactivation compares a user's own learning rhythm, reduces unsuccessful reminders and eventually stops without imposing a universal 3/7/14-day schedule. Fixed thresholds and weekly absolute cap await measurement/owner decision per Master Plan, not an invented constant in this design.

At job creation freeze canonical owner, validated IANA zone, local date and its UTC day window. Evaluate late ticks against explicit policy-valid expiry: safely plan inside the window or expire; never send at an arbitrary later hour. If travel/zone changes make the next proposed local-day window overlap an already reserved study interval, suppress until reconciled. Recompute goal completion, HSK track, actual lesson/CTA entitlement, auth/consent, personal quiet/pause and endpoint eligibility immediately before claim/send; a completed goal or blocked Pro target cancels the job. Existing legacy integer offsets are cold-start evidence only and cannot model fractional zones/DST precisely; backfill must not silently shift an old scheduled time when zone is uncertain.

Alternative considered: use each device's local `lastReminderDay` as the account guard or enforce a universal quiet window. Device days disagree under travel, and D04 explicitly rejects global time bans; use server-frozen day windows and personal constraints.

### 5. Atomic reservation, claims and honest outcomes

The scheduler/planner uses a bounded durable due queue and an account-local-day uniqueness constraint. Transaction one locks canonical user then preference/job state, checks the current epoch and policy, reserves a single logical job and selected endpoint, commits, and only then performs provider IO. A bounded worker lease/claim can be recovered after expiry, but a crash after initiating provider IO produces an **unknown** outcome unless a definitive rejection or authenticated client non-display exists. Unknown/FCM accepted/no ACK/timeout cannot authorize an alternate provider, even after a lease expires. Successful Telegram Bot API return is provider acceptance, not user read. Android FCM `send_batch` acceptance is a wake-up hint, not notification display.

For an eligible compatible Android client, both FCM and WorkManager first retrieve/claim the *same* unexpired, pre-reserved server job bound to the current session/device/epoch. The server grants at most one selected device, and the client keeps its local epoch/day guard. A claim is rechecked for current consent, owner, goal and expiry before `StudyNotifications.postReminder`. Authenticated receipts distinguish client-declined before OS call, `notify()` invoked but display unverified, and genuinely verifiable display where possible. A definite provider rejection or authenticated pre-display decline may permit one alternative attempt **inside the same job**, after revoking the old grant and rechecking D01/D03/D04/D06. A late original hint must fail a fresh claim after that revocation. The existing account-notice `/notices/{id}/ack` and its ten-minute fallback are not reused.

Alternative considered: mark success as displayed when FCM accepts or `notify()` returns and fallback when ACK times out. Neither event proves the user saw a notification; timeout-driven alternate sends create avoidable duplicates.

### 6. Version-fenced Android and Telegram cutover

Introduce a tested new Android protocol with an explicit signal that autonomous local study posting is disabled, plus a server-controlled cohort generation and fresh study-channel permission observation. Validate the Direct and Play builds, both FCM and WorkManager routes, logout/account-switch epoch fences, offline behavior and authenticated claim/receipt. The new binary must fail closed offline after migration. Unknown/prior/offline APKs that can still schedule local WorkManager are **cohort blockers** for new cross-channel dispatch; neither version metadata nor lack of recent activity proves they are fenced. Preserve the legacy path for non-migrated accounts without running new and old server study senders for the same account. The precise installed fleet and viable upgrade gate require real staging/release evidence before enabling multi-device canary.

Telegram uses the existing bot route and approved template infrastructure behind cohort ownership. Guard the old course sender before activating the new one; retain the D1 holdout and motivation/ranking category semantics. New CTA targets resolve current available lesson/track/access at dispatch and on open; no private lesson URL or Pro bypass. Mini App Telegram SDK launch fragment/auth rules remain intact. New visible notification/settings copy is centrally authored in UZ/RU/TJ per `localization/README.md`, generated for clients, and tested through actual consumers. Feed re-rendering must preserve template arguments and DB-backed admin edit precedence; the existing `template_service` persistence mismatch is a focused future regression/fix, not a reason to alter runtime here.

Alternative considered: turn on server dispatch for all linked accounts once a new APK exists. Older installed offline binaries could still post; cohort proof is necessary before cross-channel rollout.

### 7. Metrics, admin control and optimizer boundary

Record reason-coded evaluated/suppressed/reserved/attempted/provider-accepted/client-posted-unverified/verified-shown/opened/verified-learning/opt-out events at their true grain. Only canonical server learning progress proves reactivation/completion; existing Admin PWA `miniapp_opened` proxies cannot be relabeled as causal study outcomes. Preserve D1 experiment assignment and use stable account-level control/treatment. Measure real baseline and eligible traffic, then version proposed MDE, sample/power, observation window and stop guardrails for owner review before experiment exposure. Use existing guarded Admin PWA command/auth/audit/editor pattern for one minimal kill-switch/template/readout surface; live consent, jobs and command authority cannot come from its 24-hour Redis/R2 aggregate snapshot. Cache only privacy-safe aggregate metrics with generation/window/denominator, with `null` or insufficient data where appropriate.

The V1 rule policy remains functioning independent of ML. After separate validation, a versioned shared model may automatically serve users with sufficient reliable personal evidence; degradation/invalid evidence/model unavailable returns to rules while all consent, daily cap, access and channel guards still execute. No new user feature-permission prompt or expensive per-message LLM dependency is introduced. Raw behavioral details receive finite class-specific retention and deletion handling; exact TTL values are set only after the D13 privacy inventory, never guessed from the 24-hour admin snapshot duration.

### 8. Shared personalization context, platform-specific widget adapters

Reuse the core's canonical learning signals, personal time source/confidence, current course/today plan and accessible continuation target. Do not run a separate habit estimator in Android, a widget extension or a desktop frontend. Prefer an additive optional versioned projection on the existing authenticated course-map response, with backward-compatible DTO/cache defaults; add no public learner-data endpoint. Core semantic output is independent of Android/Glance, SwiftUI/WidgetKit, Windows cards and widget size.

The proposed projection carries only the versioned policy/contract, generated/expiry instants, authoritative day/zone/course context, real progress/goal state, personal study-window phase and a reason-coded safe action. Exact field names and expiry/confidence values are reviewed during implementation, without adding new numeric product thresholds here. Authentication binds the canonical owner and device; local adapters bind updates to the current session/epoch and reject old revisions, wrong track/day/zone, future or expired context. Do not persist account identifiers, tokens, private lesson content or raw behavioral history in widget snapshots.

Completed real plan/goal state produces a calm/completed presentation; reward XP alone, widget opens and app foreground cannot prove completion. A reliable 02:00 habit must not become "late/critical" merely at a universal 22:00 boundary. Sparse history uses genuine existing time/goal or a neutral rules fallback; user manual time and personal quiet/pause constraints prevail. New/comeback/streak-broken states require actual typed evidence. Reuse the existing art/layout and canonical UZ/RU/TJ resources, with no invented mood, lesson duration, new settings prompt or per-refresh LLM call.

Rendering is passive: refresh, pin, timeline and tap do not reserve a study job, change consent or invoke notification delivery. Global notification OFF/OS denial blocks study sends while ordinary permitted course-progress rendering can remain. A paused/quiet account receives neutral presentation, not escalation through the widget. A widget tap requests normal authenticated navigation, never completes a lesson or bypasses foundation/Pro/track access. Existing widget telemetry remains exposure/open evidence only, subject to the shared privacy/retention rules.

**Adapters and staged delivery:** Android Direct/Play remains the first implementation, preserving epoch/cache decoding and WorkManager limits. Apple later needs a real host/extension and protected shared-container/session bridge; [Apple's WidgetKit guide](https://developer.apple.com/documentation/widgetkit/creating-a-widget-extension) documents extension-based widgets and OS presentation/privacy behavior. Windows later needs a supported provider integration; [Microsoft documents Win32 and PWA widget providers](https://learn.microsoft.com/en-us/windows/apps/develop/widgets/widget-providers), not automatic rendering of an existing Tauri/PWA page. Evaluate packaging/auth/update budgets on the actual target OS before selecting that adapter. iPhone learner PWA push remains a separate V2 feature and is not treated as a native iOS widget. macOS and Windows ship equivalent account behavior together, with explicit OS capability limits. OS widget timelines/refresh budgets do not promise exact-time delivery.

Use shared golden input/output fixtures for personal phases, real completion, sparse history, midnight/DST/travel, manual time, pause/OFF, denied OS notifications, stale/replayed account context, course switching, logout/deletion, unsupported versions and inaccessible targets. Android resolver/store plus real launcher checks come first; later adapters must satisfy the same fixtures and real install/lock-screen/privacy/lifecycle tests. Keep widget personalization rollout independently reversible to a neutral/legacy view, preserving reminder OFF, revisions and existing jobs; no rollback may restore a second study sender.

Alternative considered: teach each widget platform its own hours/habit model. It would drift from account-level scheduling and repeat the current fixed-clock problem; keep rules and signals shared, with native rendering and refresh scheduling at the edges.

## Bounded implementation slices

### Bounded task 3.1 implementation boundary

On the reviewed P1 baseline `19d71b50`, add a pure shadow evaluator and an
internal read-only context adapter, without an API, scheduler consumer, schema
change, job reservation or provider call. The adapter reuses the verified-actor
preference reader's current account/session/deletion checks and user-first lock;
readers must not flush, initialize a profile/plan, consume access or commit.
Current course progress and `LessonAccessService.status(consume=False)` own the
continuation target. Starter 0 remains a separate prerequisite. Course/day
mismatch, inaccessible targets and ambiguous/nonexistent local times suppress.

Learning inputs are a bounded observation window supplied explicitly by the
internal caller, not a newly invented retention/inactivity threshold. Corroborate
canonical lesson XP refs with server-only `lesson_completed` receipts and
accepted current progress; corroborate practice XP with server-only
`test_completed`/`training_completed` session refs. Deduplicate by the original
XP ref and instant, including cross-client replay. Reward XP, opens, provider
acceptance and uncorroborated activity are not study. Missing best-effort events,
unsupported study types and window overflow remain explicit coverage limits;
absence is never an inactivity finding. Positive verified XP and a matching
stored plan are separate completion signals; do not create a new frozen plan.

D09's minimum confident learning days is still undecided. Default evaluation
therefore preserves a genuine saved time or returns unknown. A supplied,
versioned calibration is an internal simulation input only, with no runtime
configuration/caller enabling adaptation in this slice. Test distinct learning
days (one vote per day), ambiguous habits, sparse history and a genuine 02:00
mode without a universal night blackout. Exact observed minutes avoid invented
hour bins or circular midnight averages. Manual locks and personal quiet/pause
always prevail. All decisions unconditionally carry `dispatch_allowed=False`;
permitted channel configuration is not an endpoint grant or old-client fencing.

Test the pure evaluator and actual persisted XP/event/progress/access reader on
SQLite and PostgreSQL, including reward-only/replay, canonical owner isolation,
course switches, completed goals/plans, denied access, stale sessions/OFF and
zero writes. Task 3.2 cadence, 3.3 reservations/DST travel ownership, 3.4 category
coordination and 3.5 widget projection remain separate. Rollback removes these
unused shadow modules; retain P1 consent, lifecycle guards and schema.

### Bounded task 3.2 cadence simulation

Extend the unused shadow boundary with a pure account-level cadence evaluator
and a bounded read-only job/attempt projection under the same P1 User lock.
No schema, scheduler, runtime configuration, provider, UI or client change.
Evaluate existing eligibility first. A logical job already owning this local
day or overlapping its frozen UTC interval prevents a new intent, including
cancelled/expired ownership. Deduplicate by canonical job, never by attempts,
channel, device or preference revision. Actual uniqueness/concurrent reservation
and safe travel ownership still belong to 3.3.

Use the median completed gap between distinct verified local study days as the
observed personal rhythm. Compare elapsed local days with that rhythm times an
explicit calibration factor, rather than universal 3/7/14-day triggers. A
versioned simulation calibration must explicitly supply minimum learning days,
abnormal-gap and observation multipliers, increasing-gap factor, finite
unsuccessful-series limit and weekly cap; **none has a production default**.
For simulation, the proposed weekly cap is a rolling seven local-calendar-day
window and includes non-shadow live reservations/possibly externalized jobs;
cancelled/expired unattempted jobs do not consume that weekly budget. Present
this interpretation with D03/D08/D09's still-open values in the Master Plan
before any runtime enabling decision; QA values do not approve a product policy.

Only independently verified shown evidence can mature into an observed
no-learning outcome, and only with explicitly complete authoritative learning
coverage through a personal-rhythm observation window. Provider acceptance,
post invocation, opens, missing ACKs and timeouts never imply ignored or shown.
Count one unsuccessful outcome per logical job after its observation window;
increase intervals from the last real exposure and eventually stop the series.
A later original server learning receipt resets the unsuccessful streak;
replayed XP/original timestamps, reward XP and opens do not restart it. This is
observational sequence evidence, not a causal conversion/uplift claim.
Definitive non-display/rejection is a separate transport outcome, never a
failed learner response. Mixed/unknown attempts remain uncertain. A newer study
cannot clear unresolved display timing just by comparing an old schedule;
verified late exposure uses its actual shown instant. Reconciliation/expiry
fencing remains a protocol gate. A cooldown is an earliest eligibility bound,
not permission to post at that instant outside the personal clock/quiet checks.

The actual legacy source reader explicitly declares **incomplete negative
learning coverage**: best-effort events and deterministic practice replays can
undercount learning even with no row overflow. It may expose observed positive
rhythm and real account budget, but cannot assert abnormal inactivity or failed
reactivation. Do not add a caller-controlled complete-coverage flag to an API or
infer completeness from an empty query. Complete-coverage cases are synthetic
pure-policy fixtures pending an authoritative outcome feed. Missing historical
zone provenance also blocks operational habit/cadence adaptation after travel.

Test daily versus twice-weekly histories, decreasing cadence, eventual stop and
learning restart; exact same-day/overlapping-window and rolling-week boundaries;
unknown provider outcomes; replay/dedup; missing coverage, sparse history and
current OFF/access/manual/quiet restrictions. Read actual persisted job/attempt
rows on SQLite and PostgreSQL without writes/flush/commit and without loading
tokens or raw endpoint data. All decisions remain dispatch-OFF. Rollback drops
these unused modules only and preserves P1 consent/epochs/ledger/legacy guards.

### Bounded task 3.3 durable shadow queue

Reuse frozen 0133/0134 storage; no schema or migration. An internal service owns
short transactions, locks canonical User then preference/job state, and inserts
at most one account/day study row. Refuse any same-label or overlapping frozen
UTC day, including cancelled/expired ownership. Compute midnight boundaries with
the chosen IANA zone (23/25-hour DST days and fractional/date-line zones), never
an offset guess or UTC start plus 24 hours. Supply an explicit expiry strictly
after the chosen personal clock and no later than day end; choose no production
TTL, cadence threshold or global night rule.

Reservation is **shadow evaluation ownership only**. It requires fresh 3.1
account/consent/access/goal/personal eligibility and records the 3.2 cadence
reason, including unconfigured/unknown coverage. Recording that suppressed
cadence result is not a delivery grant. Use a distinct queue policy version,
state `shadow`, NULL selected channel/device and zero attempts. This shadow row
still owns its unique account/day; later rollout must reuse/recheck it or skip
that day, never mint a parallel live intent. No API, main scheduler, cohort,
endpoint selection, old-sender cutover or provider caller is enabled here.
Insert directly in the owned outer transaction: a first-write savepoint under
SQLite legacy transaction handling can release before the outer commit. The
unique constraint refuses inconsistent concurrent writers; ordinary PostgreSQL
reservation retries serialize on User. Claim/close use conditional lease/state
updates as an additional stale-writer guard. Sample the clock after the User
lock and recheck lease/expiry and current quiet state after validation IO; a
pre-lock timestamp must not hide learning committed during the wait or revive
an expired window. Bounded expiry-only maintenance
locks User first and can close expired shadow jobs even for blocked accounts,
without granting client/session authority; external attempts are quarantined.

Bounded indexed due discovery yields only opaque owner/job handles and holds no
job-first locks. Claim under a fresh verified actor/User-first lock; use a fresh
opaque lease token, explicit technical lease duration capped by job expiry, and
CAS/fresh checks on completion. Keep state `shadow` while leased so simulated
work does not consume a live weekly send budget. An expired lease can be
reclaimed; old tokens cannot finish. Expiry, OFF/epoch/revision, course/zone/
personal-clock changes, completed goal or lost access suppress without changing
the frozen window or creating another job. A due-window-only evaluator option
allows the original clock to have elapsed while retaining *current* learning/
goal/quiet/pause checks; never rewind evidence to the scheduled timestamp.

Finish commits the shadow decision before an optional observational sink runs
outside all SQL contexts. Sink failure leaves a durable completed row and does
not re-run that effect; a process crash before finish can retry after lease
expiry. The sink receives `dispatch_allowed=False` and no selected endpoint or
provider adapter. Actor resolution is a trusted internal boundary, including
native-only accounts; no session credential is stored in jobs. Existing P1
session/revocation/deletion checks remain current on each claim/finish. Future
autonomous cohort/claim/provider integration remains separately gated.

Any unexpected attempt on an owned shadow job forbids shadow execution. Preserve
external in-flight/accepted/unknown facts, quarantine ambiguous ownership and
never create an alternate. Test a committed in-flight marker, a synthetic
provider acceptance outside SQL and a crash rolling back its acceptance update;
recovery must retain uncertainty and make no second call. This is a real DB
fault-injection model, **not real provider/device acceptance or an enabled live
dispatcher**. Known accepted/unresolved jobs are never recovered as pending.

Verify SQLite and PostgreSQL, with real PostgreSQL two-reserver/two-claimer,
restart/stale lease, completion-versus-OFF/learning races; missed tick and expiry;
DST/fractional/date-line overlap; commit failure, sink boundary and external
crash model. Rollback keeps ledger uniqueness/windows, P1 consent/epochs/guards
and uncertainty; no destructive downgrade, live migration or legacy resume.

### Bounded task 3.4 coordination and independent shadow worker

Add pure, channel-neutral study/rank/weekly collision simulation and an
authenticated read-only source adapter. Keep transactional routing outside this
budget. Candidates carry stable account-level identities, explicit windows and
source eligibility; no body, endpoint or provider credential. An explicit
versioned simulation calibration supplies spacing/priority with no production
default (D05 remains OPEN). Defer a useful weekly candidate with its identity and
window intact, or retain it as pending/unknown if no valid later slot is known;
do not silently discard it or promise posting at an unvalidated quiet time.
Proposed later times require fresh eligibility. Deferred weekly simulation
outputs are not a new durable weekly delivery queue or consumed send cursor.

Read existing canonical D1 assignment events, with fallback only for unowned
historical events on this account's real positive Telegram identity. Preserve
the existing 48-hour window for both arms; never hash/reassign by device or
invent an assignment. Unknown/future/overflow assignment evidence fails closed.
Apply this exclusion to new study and ranking simulation consistently with the
existing motivation holdout. Existing weekly/transactional routing remains
outside that motivation holdout. Add the mandatory D1 veto to shadow reservation
and fresh queue checks, including an assignment arriving after claim. No new
experiment exposure follows from a shadow candidate.

The source adapter projects only notification keys/dedupe/instants, existing
course weekly provider-return timestamps and verified progress delta. Feed rows
are possible contacts, not display proof; shadow job completion is never a
contact or learning signal. Legacy/offline contact coverage is partial. Do not
query message bodies, rank peers' identities or tokens, mutate legacy counters,
generate summaries, assign experiments, or call senders. Compare actual legacy
fake-transport scenarios to the new simulation in tests; no live causal metrics.

Run the existing shadow queue through a separate lifespan task, behind a single
`SMART_REMINDER_SHADOW_ENABLED=False` technical flag. Disabled means zero Smart
polling/SQL. It processes only already reserved versioned shadow jobs and has no
producer enrollment, endpoint grant or provider callback. Resolve fresh trusted
internal actors from canonical User/real Telegram or current owned Android
session metadata; no fake Telegram identity or credential storage. Isolate the
worker from the existing financial/legacy scheduler and Admin PWA poller, with
bounded technical batches/timeouts, clean cancellation and no raw identifiers
in logs. Do not reorder existing transaction/fallback/legacy routing. No flag is
changed in production and no public/admin UI is added.

Verify source-bound D1 control/treatment/expiry and native/unowned/conflicting
ownership, zero-write reader, useful weekly defer/retention, duplicate and
cross-category collision, unchanged transactional behavior and no provider IO.
Use SQLite/PostgreSQL and actual scheduler source to demonstrate failing/slow
Admin PWA does not block the separate shadow task; test disabled zero SQL,
cancellation, timeout/restart, actor revocation and current D1 after claim.
Rollback disables only shadow processing; retain P1 OFF/epoch/uncertainty and
frozen job ownership. D05 thresholds, registered experiments and physical
cutover acceptance stay open for subsequent phases.

### Bounded task 3.5 shared passive widget context

On reviewed main `1b9ff214`, implement one strict version-1 platform-neutral
projection and golden fixtures over the existing 3.1 verified policy context.
Reuse its habit/time/goal derivation, extracting reusable IANA day/clock helpers
without changing reminder decisions. No separate widget habit estimator or
production habit-confidence default. Semantic phases are neutral, before-study,
study-time-reached, completed, paused, quiet and unavailable; no fixed urgency,
overdueness, broken-streak or comeback assertion. Verified learning XP and plan
completion remain distinct from existing map display/reward XP. Unknown day/zone
or mismatched progress cannot assert daily completion. Global OFF/pause/quiet
restrain presentation while ordinary permitted progress stays available;
notification-channel consent and OS denial do not authorize or prevent passive
progress. Inaccessible/foundation targets never become a lesson access grant.

Add an opt-in `widget_context` field to the existing authenticated Android map,
requested with version 1 and a canonical per-link epoch UUID. Legacy requests
retain their existing response and perform no new Smart reads. Validate the new
parameter pair/duplicates/allowlist and native platform, use the real canonical
account/device/session with fresh P1 block/deletion/revocation checks before map
work and again for the projection. The existing native map and normal navigation
remain the only content/access authorities. No public learner endpoint, desktop
consent expansion, new schema, flag, telemetry or notification send is added.
Later native adapters reuse the pure contract with their own verified bridge;
no iOS/macOS/Windows host or Android renderer is claimed in this slice.

The envelope carries only semantic facts, canonical level/track, IANA day/zone,
revision, generated/expiry instants, the caller's epoch and an opaque non-auth
SHA-256 binding of the verified canonical owner/device/session. Raw IDs,
credentials, names, lesson bodies and behavioral history are excluded. Expiry
is capped by the already verified bearer expiry, actual IANA midnight and the
next relevant personal-time/quiet/pause transition. This introduces no arbitrary
product TTL, refresh promise or retention policy. Unknown zone remains neutral
and never invents an IANA zone from the legacy coarse offset. Re-sample time
after User locking and validation; an expired proof cannot mint valid context.

Publish the request/response, reason codes and minimal cache allowlist beside
implementation. A strict reference acceptance function/golden fixtures reject
unknown versions, future/expired/invalid envelopes, mismatched local epoch or
opaque binding, wrong course/day/zone, regressed revision and older generation.
These are contract tests, not installed adapter acceptance or a cryptographic
snapshot access token. Adapters clear state on logout/relink/deletion, keep only
this minimal envelope, bind each in-flight response to its captured current
local epoch and apply known-current revision/generation fences. Offline cannot
promise immediate remote revocation; expiry restricts presentation and every
action reauthorizes normally. Rollback omits the opt-in field or renders neutral,
without changing consent, P1 guards or shadow job ownership.

Verify shared sparse/manual/02:00/daytime/quiet/pause/OFF/OS-denied/completed/reward
fixtures, DST/fractional zones/day rollover, unknown progress/access/foundation,
strict malformed snapshots and old-session replay. Exercise source SQLite and
PostgreSQL readers with zero new writes/consent/jobs/attempts, fresh ownership,
blocked/deletion/revocation and native-only accounts; test the actual optional
Android map route and regular Android/desktop course regressions. Android art,
render/store and physical launcher acceptance stay with P4 tasks 5.5–5.6.

### Bounded task 4.1 Telegram ownership and internal dispatch boundary

On reviewed main `dbc49900`, add minimal additive 0135 routing ownership storage,
not a learner migration or activated dispatcher. A canonical User-owned row is
sticky: held/Telegram ownership suppresses existing server study paths even
when the new switch is off or proof expires. Add a send-only check alongside the existing
configuration OFF veto, preserving deliberate time/consent writes; weekly/motivation/transactional behavior is unchanged.
No row is created from a preference read, device/version inventory or absence
of Android tokens. A bounded non-secret Android device/session/capability hash
binds the hold/review and refuses later inventory drift. Present active Android
installs additionally need fresh autonomous-disabled protocol proof through the
review window; missing/revoked rows never replace external fencing review. Keep all P1 OFF, current session/account/deletion and epoch
checks. Canonical purge and the empty-QA migration registry include the row;
populated downgrade refuses destructive removal.

Use an internal two-step operator boundary: hold under User first, cancelling
unattempted work without resetting day/attempt ownership; then accept a strict
versioned, generation/account-bound review attestation created AFTER that hold.
It explicitly confirms legacy IO has drained, old-day/uncertain outcomes are
reconciled and other autonomous study senders are fenced, with a SHA-256 evidence reference and finite explicit validity.
This is a privileged internal review input, never client telemetry, a body/API
field or an inference from inventory. All backend replicas must run the guard
before holding; an old legacy call already past its veto can still be in IO.
Actual quiescence/install/fleet verification is a future 4.3/P4 gate, not proven
by a Boolean or a synthetic test. No production cohort, review or flag change
is performed. There is no automatic legacy resume; rollback disables dispatch
and retains held ownership, schema, OFF and ambiguous attempts for review.

Implement the internal Telegram queue/attempt protocol behind
`SMART_REMINDER_TELEGRAM_ENABLED=False`, with no scheduler/producer/provider
wiring. It also requires explicit cadence calibration and a separately registered
authoritative learning-coverage reader (neither supplied in runtime), fresh
active cohort evidence, current consent/master/real Telegram and P1 account
checks, existing D1 scope and 3.1/3.2 goal/access/quiet/cadence gates. Reuse/adopt
only an unleased, unattempted existing 3.3 shadow reservation under the same
frozen account/day identity, otherwise skip that day. Completed/cancelled rows
and another policy's ownership are never replaced. Shared fresh frozen-job
validation is reused; channel selection here is Telegram-only in an externally
reviewed cohort, not D06 Android ranking or a new fallback decision.

User-first transactions issue finite token leases and one deterministic initial
Telegram attempt. Commit prepared ownership and revalidate before committing
an in-flight marker; only then call an injected internal transport OUTSIDE SQL.
No production transport is passed in this slice. Successful trusted Telegram
receipt means provider accepted, never shown/read/learned. Exceptions, timeout,
process death or acceptance-update rollback preserve in-flight/unknown state
and refuse all retries/alternates for that intent. Prepared work can recover
only with a new finite lease after expiry and fresh proof. OFF/hold committed
before the in-flight authorization boundary denies sending; a change after
that boundary cannot recall provider IO, but cannot authorize a second send.
Record external outcomes even if OFF/block occurred meanwhile, under User and
without minting new permission. Rendering/inbox/CTA/localization is task 4.2;
this task uses synthetic fake-Bot payloads and adds no visible copy.

Verify SQLite/PostgreSQL schema/up/down refusal/purge; strict hold/review and
stale generation/identity/revision proof; disabled zero SQL/provider behavior;
actual legacy guard and current master OFF, stale callback, D1 control/treatment,
bot block/native-only exclusion, unique same-day ownership, lease recovery,
learning/expiry/OFF after claim, IO after commit and accepted-before-DB-failure
no replay. PostgreSQL two-worker and waiting OFF/hold/learning races must use
real transactions. Actual legacy non-cohort scheduling remains unchanged; do
not claim a global legacy dedupe or physical exactly-once guarantee. Record
source/CI/limits only in the Master Plan and advance to 4.2 after acceptance.

## Bounded task 4.2 — Telegram content and inbox (main refresh 2026-10-29)

Base: `origin/main@5e9a34f6b60bd49dc8f544e4dc4b4fdf3faa9f90` and Master
Plan §17.44. Extend the dormant 4.1 dispatch boundary, without a scheduler,
producer, live provider, cohort activation or new authorization/defaults.

Use one canonical UZ/RU/TJ `smart_study` template with a validated lesson number,
existing notification title/CTA adapter and `course_study_miniapp_url`. Expose
it through the existing template editor/service and passkey/CAS boundary; keep
the five motivation triggers separate. The current allowed frozen target is
rechecked by 4.1 under User before rendering and in-flight commit. The normal
authenticated destination retains current course/foundation/lesson/access
checks without autostart, tokens or private content in the URL.

Render the current account language and DB custom/default/disabled/media
snapshot before external authorization, re-evaluate current policy and the finite lease after these
reads (including a quiet/day boundary crossed while rendering), then pass the immutable content to an injected Bot adapter outside SQL.
The helper is not registered in runtime. Invalid placeholders, excessive
provider text or disabled templates cancel before IO. Only provider acceptance
may record a canonical account-owned, job-deduplicated inbox item in the same
outcome transaction. Unknown outcomes create no success/feed claim or retry.
A DB rollback retains the existing uncertain in-flight boundary.

First reproduce `template_service` parameter loss with an actual DB roundtrip,
then fix only that persistence predicate. Inbox language resolution must return
presentation data without assigning `_rendered` into tracked ORM JSON; test
commit/reload, repeated language changes, custom fallback/disabled/broken copy,
legacy rows, canonical owner isolation and duplicate recording. Never rewrite
historical stored sent text or invent learning/read evidence.

Verify actual renderer/dispatch/fake Bot and inbox roundtrips on SQLite and
owned PostgreSQL, fresh access/track/OFF/D1 and current language after claim,
admin signed template compatibility, URL/locale/escaping/length/media behavior,
P1–P3 regressions and all canonical catalog generation/guards. Record actual
source/CI evidence only in the Master Plan. Native widgets and real canary
acceptance remain separate. Rollback retains 4.1 routing/day/attempt ownership;
no new consent, schema, settings screen or redundant editor control is added.

## Bounded task 5.5 — Android passive widget adapter (2026-10-29)

Base: `origin/main@4213c37cd8deed4fa3eb24ed386f1b524c759585`, Master Plan
§17.45 and the shared v1 widget contract. Source confirms 4.3 is not ready:
runtime cadence/authoritative learning coverage and producer are absent, and
no staging/cutover proof is recorded. Keep 4.3 unchecked and dispatch OFF.
D15 passive rendering is explicitly independent of notification permission;
its existing Android consumer task may proceed while these live-send gates
remain open. This changes execution order only, not D01–D15 or canary acceptance.

Use a dedicated passive map GET through the existing Retrofit transport,
without changing ordinary CourseRepository/Room map contracts. Capture the
actual AuthRepository bearer/session generation and widget link epoch before
request, recheck both before accepting, and conditionally clear only that
same generation on session expiry. No credential enters widget storage.
Before replacement sign-in credentials persist, a widget-only callback clears
old visible/cache state and pending study presentation. Keep existing post-token
`onSessionLinked`, token durability, AI/payment callbacks and auth decisions
unchanged. This closes process death between credential persistence and the
later widget epoch reset; a failed credential write cannot restore old data.
A small injectable refresh bridge makes delayed-response/auth races testable;
foreground map publication for an installed widget requests this live bridge
rather than adopting an arbitrary Room/cached context. Refresh failures are
stale/neutral and cannot restore a previous account.

Parse the complete shared v1 allowlist strictly and preserve only permitted
fields. Unsupported/malformed cached personalization defaults to neutral while
legacy session/snapshot JSON remains readable. Establish opaque binding only
from a confirmed-current authenticated response, never an envelope echo;
retain revision/generated floors across failed refreshes. Validate course,
day/IANA zone, local epoch, real JSON booleans, future/expiry and semantic
completion/target consistency. Newer authenticated course changes may replace
context; old responses/revisions cannot move it back. Known device zone/day
changes neutralize old presentation. No epoch is an auth credential.

Extend existing snapshot/store/resolver/art copy and layout in place. Map
before/reached/completed to existing calm/waiting/completed art families; no
fixed 22:00 escalation, new habit estimator, invented duration or LLM request.
Use corroborated learning/goal facts only for goal copy and completion; reward
XP or old `dayComplete` alone is insufficient. Neutral/quiet/paused/unknown
keeps ordinary permitted progress, not a fake failure. Preserve the 28 art
assets, deterministic variants and normal CurrentLesson/foundation access
navigation. New fixed labels are canonical UZ/RU/TJ native resources in a new
bundle, with existing frozen XML intact. Direct/Play share all code.

Validate decoder/store/refresh-generation/resolver against actual shared
backend golden envelopes and adverse clock/zone/owner/replay cases; add only a
small deterministic exporter if existing fixtures lack complete envelopes.
Run relevant Android JVM tests on Direct/Play, compilation and canonical
catalog/guard checks. Real launcher/installed refresh/layout acceptance remains
5.6, with OS timing limits explicit; no APK release or iOS/Desktop widget
support is implied. Rollback uses neutral/compatible rendering, preserving
all notification flags, day guards and Smart consent/ownership.

### 9. Automated four-stage server rollout and admission

Use one durable singleton rollout row for Smart study: generation, stage
(1–4), stage start, last heartbeat, paused/completed status and one fixed
sanitized failure code/time. Do not persist learner IDs in rollout state.
Stable cohort assignment is derived from the canonical account ID, and each
stage is cumulative.

The owner-directed D30 outcome (Smart for every eligible learner after four
stages, no manual per-account review) is reached by **automatic admission**
inside the open cohorts, using the existing routing records:

1. **Eligibility.** Only an existing Smart preference with an IANA zone and a
   channel already allowed by that preference (Android this-device consent, or
   Telegram consent with a reachable bot). Admission never creates or infers
   consent. A bot-only learner with the legacy lesson reminder ON but no Smart
   zone receives a fixed `Etc/GMT±N` zone derived from the legacy whole-hour
   offset the legacy reminder already uses, through the journaled
   timezone-only preference writer; the Mini App treats such a zone as
   provisional and replaces it with the real device zone. Android inventory must be fenced. For Telegram/PWA
   ownership every active Android device either durably reported server-only
   Smart (protocol 1, autonomous posting off) or runs a Smart-capable release
   (1.7.29/60 and newer, public since 2026-11-05): its study worker asks the
   server before any local post and stops posting once the account is held,
   also offline. An active device on an older APK can still post its own local
   reminder, so that account stays on the legacy senders and is not held. A
   device silent for 14 days (no token refresh, `last_seen_at`) is dormant: an
   app posts locally only from a freshly fetched course map, and a woken device
   becomes active again at once, closing the Telegram cohort. The native
   Android path additionally needs a fresh capability (posting authority).
2. **Hold.** The existing sticky routing hold. Every server legacy study sender
   (Telegram lesson time, motivation evening study, Android FCM) already
   vetoes held accounts. `quiesced_at` keeps the first veto time.
3. **Drain.** 24 hours after the first hold, so legacy work already started
   that day cannot produce a second reminder.
4. **Review.** An evidence-bound automatic `RoutingReview` (hash of version,
   generation, path, quiesce time, inventory, revision, epoch and review time)
   through the existing `activate`/`review_android` writers. Telegram reviews
   last 7 days; Android reviews are capped by the device capability (one native
   access token), so expiring reviews are visited before the rotation.
5. **Refresh.** While the owner (state, transport binding, generation) is
   unchanged, a new preference revision, epoch or Android inventory is
   re-attested in place by `refresh`, cancelling no work. A changed owner needs
   a re-hold, which waits until no study work is active. Consent OFF or a newly
   unfenced device is never re-attested; the sticky hold does not revive legacy.

Advance a stage only after 48 hours of observed runtime heartbeats. Time
without a heartbeat (deploy, crash) does not count, and send authority fails
closed while the heartbeat is stale. Systemic failures pause the rollout and
turn the existing Smart template OFF: at least 5 unknown outcomes that are at
least 30% of the attempts started in the stage (a learner who blocked the bot,
an expired PWA subscription and an Android receipt still pending are not
systemic), three unexpected per-account exceptions within an hour, or three
consecutive tick timeouts. A Telegram "blocked" refusal marks the learner
blocked; the attempt stays unknown and is never retried. Every route that
authorizes a provider send or native posting grant (Telegram claim/dispatch,
Android final grant, PWA dispatch, planner) checks the current stage in its
fresh transaction, so pending work from a formerly wider stage cannot escape
after a restart. The existing signed Admin PWA Smart-template enable is the
only resume action: re-enable increments generation and starts at stage one.
The Mini App's automatic IANA-zone setup also opens for accounts of an open
cohort, which lets Telegram learners become eligible.

**Learner iPhone PWA.** PWA is a third channel of the same account/day job on
a `telegram`-state routing row: the destination selector offers it only when
the Smart preference is exactly ON (`master_enabled` true), the device has a
live owned PWA session and push subscription, and the PWA Web Push sender is
configured. PWA dispatch rechecks the template, cohort and preference before
the provider, records one attempt and never mirrors to Telegram; an unknown
result is terminal. The PWA's own study switch controls the legacy motivation
flag, not Smart consent, so a PWA learner without an explicit Smart ON is
served on Telegram instead.

This is operational error containment, not proof that all errors are observed
or that every eligible learner receives exactly one physical display. Accounts
with an Android APK older than 1.7.29/60 reach Smart only after they update.
The inventory digest binds stable device facts; the capability generation and
timestamps that change on every phone report are excluded, because the native
claim checks them itself.

## Risks / Trade-offs

- **Old offline APK can display outside the ledger** → Do not migrate accounts with unknown/unsupported autonomous sender state into new cross-channel dispatch. Test historical binaries and describe the remaining physical display limit honestly; no server-only “exactly once” claim.
- **Provider success followed by crash leaves uncertain outcome** → Reserve/commit before IO, persist an attempt before send, classify uncertain result as unknown and suppress alternate delivery. Reconciliation never treats timeout alone as non-display.
- **A single unique `(user, local_day)` may be bypassed during travel** → Freeze account zone/day/UTC window, compare overlapping proposed day intervals and suppress ambiguous transitions; include date-line, fractional zone and DST tests.
- **A stale client or migration rerun can resurrect OFF** → Monotonic CAS revision/epoch and source-scoped legacy adapters; preserve OFF through rollback and dry-run replay.
- **Missing blocked/deletion checks in a reused auth context** → Re-evaluate account/device/session/deletion eligibility on every Smart read/write/claim/send; test logout, revocation, relink and purge races.
- **Scheduler head-of-line blocking or two replicas** → Durable due jobs, bounded worker execution and DB uniqueness/lease; fault-inject a slow/failing Admin poller and simultaneous claims without changing unrelated financial job semantics.
- **Display/open metrics can overclaim effectiveness** → Separate provider acceptance, client API invocation, verifiable display, open and server-confirmed learning; protected admin reports show denominators and unknowns.
- **Schema downgrade/data purge may lose consent or jobs** → Use additive migration and staged backfill; a downgrade that would delete active/newer consent state must refuse destructive removal. Stop dispatch first and retain data until a reviewed archival plan exists.
- **Rollout telemetry loss could falsely advance users** → Unobserved time never counts toward a stage and stale observation removes send authority; systemic failures pause and disable the existing Smart template. Final claim/grant paths enforce cohort again, including old pending jobs after an Admin restart.
- **Automatic admission could silence a learner** → Hold only accounts already eligible for a Smart channel (preference zone, consent, fenced inventory); never hold old-APK accounts. A paused rollout leaves held accounts without study reminders until the operator re-enables Smart; this is the owner-chosen stop behavior.

## Migration Plan

1. **P0 audit before code:** refresh `origin/main`, source/test inventory and Alembic head; build a source-cited matrix for Telegram picker/actual OFF actions, Mini App motivation, Android local ON, device mirrors, study OS channel and historical Direct/Play APKs. Verify deployment scheduler replicas/flags and current DB stamp in authorized staging. Record unresolved sources as unknown. Accepted source audits/live reads are in Master Plan §§17.27–17.34. Per owner direction, remaining installed/mixed-build acceptance is deferred to P4/P8 and does not block dispatch-OFF P1. OpenSpec validation itself is not acceptance.
2. **P1 additive, dispatch OFF:** add reviewed schema and strict authenticated read/CAS APIs, idempotent source-aware backfill and deletion hooks. Verify old API response compatibility, concurrent OFF/stale ON, migration rerun, account purge, SQLite/Postgres up/down safety and no newly sent reminder.
3. **P2 shadow:** introduce deterministic rules, job/attempt reservation and reason codes with external sending disabled. Compare planned outcomes against current senders, exercise two workers, crash windows, late ticks, time zones, completed goals, D1 holdout and account status. Fix source-specific feed localization separately if its DB roundtrip test reproduces the mismatch.
4. **P3 Telegram cutover:** guard old server Telegram study sender per verified cohort *before* enabling new delivery. Start with permitted Telegram-only canary; confirm opt-out, weekly/ranking coordination, D1 holdout, real UZ/RU/TJ, Bot accepted versus read distinction and rollback. Keep motivation and account notices on their own policy.
5. **P4 Android cutover:** release and verify Direct/Play protocol binary first with server Smart dispatch OFF. Prove both WorkManager and FCM use claims, no autonomous post, study-channel permission report, logout/epoch fence and offline fail-closed behavior. Enable single-device then verified multi-device cohorts only after old-client exclusion/cutover evidence, mixed-build and real FCM/OS/device tests.
6. **P6/P7/V2:** instrument source-backed outcomes and minimal protected Admin controls, baseline and experimental power before optimizer gates. Only validated ML with per-user evidence switches automatically from rules; learner PWA/Desktop adapters follow as V2 on the existing core after real platform capability checks. D15 widget work shares the P2 context, lands Android rendering with P4 and adds iOS plus paired macOS/Windows widget adapters later against the same versioned projection and golden fixtures. Passive widget release never authorizes new notification rollout.
7. **P8 release/rollback:** exercise staging migration with backup restore and a dispatch kill drill; inspect every remaining legacy sender ownership path. On rollback, turn new dispatch OFF, expire pending grants/jobs, keep explicit OFF/revisions/channel provenance, and resume a legacy sender only for an individually verified eligible cohort without replaying ambiguous work. Record automated, real Telegram, two-Android-device, OS permission, provider, staging and monitored canary evidence in the Master Plan before claiming production acceptance.
8. **Automated rollout:** start the first stable cohort when the protected Admin Smart template is enabled; hold, drain 24 hours and automatically review eligible fenced accounts of the open cohorts; advance cumulatively every 48 observed hours, pause on a systemic failure, and restart at stage one only through the existing signed Admin PWA enable after repair. Old-APK accounts stay on legacy senders until a Smart-capable APK reports its capability.

## Open Questions

Later owner decisions D19–D22 settle the study cap (3 per rolling week, still 1/day), backoff (factor 2, stop after 5 verified unsuccessful messages), future Smart analysis retention (raw details 90 days, anonymous aggregates 12 months) and learning-category spacing (6 hours). Their runtime activation and authoritative outcome/cutover proof remain separate. Individual abnormal-gap calibration, class-specific job/attempt/consent retention, D09 numerical ML confidence/admission gates and D12 powered experiment targets still require actual evidence. Master Plan §17.50 makes D09 gate fields explicit; missing calibration keeps ML unavailable.


## Owner follow-up: widget typography and interval habit evidence

Authoritative scope and decisions: Master Plan §17.47, D16 (60-minute circular
sliding interval) and D17 (recent 30 calendar days, extend to 90 if insufficient).
The previous task source has not reached main. Before publishing, remove the
dark widget panel and secondary XP/lesson clutter, place the actual permitted
streak at upper center with brief canonical UZ/RU/TJ copy beneath it, and keep
panda art visible. Select readable per-art text styling without a panel; preserve
normal tap/auth/expiry and retained assets. Verify real RemoteViews at all three
sizes/languages/themes, including text fitting and unobscured art.

Replace exact-minute habit votes with versioned explicit circular sliding-window
calibration. Keep one first accepted verified sample per local day, no hour-bin
boundary artifact, no arithmetic midnight average, no replays/outliers overriding
a real cluster, and fail closed for comparable disjoint modes or limited coverage.
The representative is an observed minute. Confidence/day thresholds stay explicit
until D18 owner choice; no production default or provider wiring is inferred.

Use existing trusted pre-Smart history with canonical owner/course/server-result
proof; never gate it on preference creation or Smart activation date. Observation
selection is 30 recent calendar days with a bounded 90-day extension when useful
personal evidence is insufficient, not a raw-data retention policy. Prove this in
read-only SQLite/PostgreSQL fixtures, including old history, duplicate clients,
reward/open exclusions, midnight/DST, jitter, sparse and mixed-mode cases. Reuse
shared widget goldens and preserve manual/saved fallback and dispatch OFF.


D18 is now approved: minimum 3 matching active days, at least 2/3 of observed
eligible days in the interval, stable from 5 matches. Define one named approved
habit preset and explicitly pass it only to the authenticated passive widget
bridge; pure callers may still request no calibration. Query recent 30 days
first, extend to 90 only if fewer than 3 eligible distinct days exist; filter
actual local calendar dates in the pure evaluator. Historical habit selection
must not reduce today's verified XP used for completion. No Smart activation
cutoff, new write, dispatch, cadence default or purge is introduced. D19–D21
configure future cadence/retention work in the Master Plan; they are not an
instruction to activate providers or delete existing XP.


D23 supersedes the earlier full-scene overlay and first rejected flat-bear draft.
The owner selected the modern broad-headed, expressive-eyed original panda and
asked for Duolingo-like rounded count typography, colors and flame details.
Use three consistent generated transparent poses in separate header/art cells,
with a bundled open Nunito font/OFL, an orange-contoured completed counter and
coordinated unfinished foregrounds. No panda pixels may sit beneath text. Share
the native header with Compose preview, keep old scene assets unchanged for
recovery and inspect only fresh per-run instrumentation images. Native decorative
outline layers do not add accessible duplicate text. This UI delta changes no
wire, auth, cadence, consent, grant, lesson or provider contract.


## Bounded 5.6 launcher/lifecycle acceptance and D24 deferral

Authority: Master Plan §17.48 and owner D24. Expanded streak/emotion artwork is
last task 9.4; retain the selected current baseline and do not generate new poses
in this slice. Existing 5.6 proceeds on refreshed main 4c986c09, with QA-only
instrumentation and actual isolated host/launcher evidence. Bind fixtures only
to the reserved QA app/origin, with no real account, provider or production DB.
Exercise pin/host sizing, normal tap/auth, offline/expiry/future/day-zone,
permission/OFF and logout epoch fences. Keep exact OS observations separate
from renderer/unit results and fix only reproduced functional lifecycle issues.
No new runtime module, dispatch/calibration/consent or signed release is inferred.


## P4 task 5.1a — authenticated capability observation, dispatch OFF

Baseline: refreshed `origin/main@392c90d14ec105ff87ddd180bea7238deed7ad12`;
actual source Alembic head 0135. Reuse existing capability storage, native
bearer authentication and User-first lifecycle guard; no schema addition.
This bounded slice adds own-device GET/PATCH capability observations only.
Full selected-job due/claim/receipt authorization remains 5.1b and must not be
marked implemented by capability telemetry. No Android client or sender is
changed in 5.1a.

The body carries strict protocol/autonomous-disabled/study-OS-permission facts
and an expected observation generation. Owner/device/session come only from
verified bearer auth. Generation CAS prevents an old allow observation from
replacing a newer denial. The server supplies observation time and bounds its
expiry by the verified bearer and current session deadlines. An unknown
permission cannot clear a known denial. Lost capability makes pending grants
invalid through existing lifecycle handling; external/unknown attempts retain
their original truth. GET never writes/imports consent. A capability report,
including all-positive facts, grants no consent, cohort admission or dispatch;
account-notice permission and its existing acknowledgement remain separate.

Test real auth/HTTP, strict and duplicate payloads, generation conflicts,
expiry, blocked/deletion/revoked ownership, permission loss, OFF preservation,
notice independence and zero jobs/attempts created on isolated SQLite and
PostgreSQL. Rollback removes the client adapter while retaining stored denial,
OFF/epoch guards and the existing schema. The router never exposes jobs or a
posting grant in this slice.

## D09 — operational ML admission criteria

Master Plan §17.50 owns this clarification. The 3/5-day habit rule is not an ML
admission threshold. Evaluate a dimension (time/content/channel/cadence) only
when all gates pass: released validated model; eligible, fresh and verified
personal features; calibrated prediction confidence; measured advantage over
the functioning rules baseline; current consent/access/cadence/holdout guards.
A shared model can use pre-Smart history; no per-person training or activation
wait is required. Missing or invalid gate inputs keep functioning rules.

A versioned model manifest must specify `minimum_usable_active_days`,
`minimum_verified_results`, `maximum_feature_age`, `minimum_confidence`,
`maximum_prediction_uncertainty`, `minimum_learning_advantage` and applicable
platform/language/feature coverage, with evaluation source/version. Values
come from held-out calibration plus the powered, owner-reviewed D12 experiment;
no arbitrary universal days/count/probability is a production default. Missing
numeric calibration is an explicit ML blocker, not a completed decision.


## P4 task 5.1b — selected-job claim and truthful receipt

Baseline `origin/main@3052ad72`, source head 0135. Add 0136 grant tombstones and
an Android-specific service/HTTP adapter. Existing capability remains an
observation; there is no job producer, Android admission reader, authoritative
learning reader or enabling runtime factory installed by this slice. The
production constructor is disabled and cannot mint authority from client facts.
QA supplies explicit trusted account/job/device/session-bound admission and
complete synthetic coverage. Sticky routing must be held before admission;
existing Telegram ownership and unknown historical APKs cannot pass it.
Review also pins the bounded current Android inventory digest; new installations,
sessions or capability/version drift invalidate it. The earliest all-present
fencing deadline bounds issuance. Hold alone is quarantine, not Android admission.

GET due is non-persisting and returns at most one selected pending job for the
authenticated device, with no posting grant. POST claim rechecks User-first
native/account/deletion/consent/OFF, capability generation/freshness, frozen
job window/epoch/revision/course/target, D1, verified learning/cadence, legacy
contact and reviewed fencing. Admission and learning attestations are privileged
inputs, not request flags. A grant binds job, attempt, owner/device/session,
opaque local epoch, claim request ID, capability/cohort generation and current
preference epoch/revision. Deadline is bounded by job, auth/session, capability,
review and known semantic boundaries; no arbitrary product TTL.

Issuance commits an `in_flight` attempt and one unique job grant BEFORE the HTTP
response can authorize a client OS call. A repeated or lost-response claim does
not return another grant, even for the same request ID. No automatic reclaim,
timeout fallback or second-device/channel grant is implemented. The client must
persist its local guard and recheck local epoch/OS permission/expiry immediately
before notify; distributed OFF/OS timing cannot guarantee physical display.

POST receipt accepts only original-session/epoch-bound `client_declined_before_post`,
`client_posted_unverified` or `client_outcome_unknown`. The first receipt is
immutable and exact retries acknowledge it; conflicting receipts are refused.
Expired/OFF grants may still record authenticated historical outcome, but never
renew authority. Revoked sessions/blocked/deletion accounts cannot write. No
client assertion can become `verified_shown`, read or canonical learning.

0136 retains one grant per job and request uniqueness, User/job/attempt cleanup,
nullable device/session FKs for retained tombstones and refuses populated
downgrade. Update model registration and standalone empty-QA head/deferred table
list; tests validate the real migration, schema parity, account purge, races,
commit/response-loss, OFF/revoke/permission loss, receipt conflict/replay, DST/day,
D1/access/goal and current account-notice regressions on SQLite and PostgreSQL.
Rollback disables admission but retains schema, issuance/outcomes and OFF guards.

### P4 5.2 client integration delta

Continue from main `bc7578af` and the canonical Master Plan §17.51. Add a native-auth read-only `mode` response exposing only whether the existing sticky routing hold or own disabled-autonomous capability requires server claims. It creates no consent/enrollment or posting authority and works while dispatch is OFF. Unreachable/unknown mode never permits legacy fallback. A current authenticated positive mode is persisted per local link epoch before reporting autonomous posting disabled; once set, false/expired/absent responses cannot restore autonomous posting. Non-migrated accounts with a fresh explicit false response retain the existing legacy path. Hold/drain review must still reconcile an old call already beyond its veto.

Both periodic WorkManager and strict versioned FCM hints use one shared client bridge, native auth-generation fence, same due/claim API and durable per-job request journal. Persist request before IO, possible grant/unknown outcome before notify and local day guard before OS call. Never replay a cached grant, claim again after a lost response, reset a consumed day, or infer display from notify. Retry only immutable receipts for the original epoch/session. Recheck session/link, local OFF, known completed goal, OS permission, response bindings, server day/zone, monotonic elapsed deadline and wall-clock expiry immediately before post. Old/delayed hints cannot choose another due job. Local denial may record only pre-call decline; notify success is posted-unverified and exceptions/crash remain unknown. Account/payment/update notice routes are unchanged.

Run real HTTP/native SQL mode regressions, injected-network JVM bridge/store races, recreation/crash/receipt retry, stale/invalid frames, clock changes, local permission/OFF/relink and both Direct/Play builds. Isolated Android OS checks may establish permission/notification invocation only; signed/real-account/two-device/FCM/fencing/canary acceptance remain 5.3–5.4. Do not enable a producer/factory or change production. No new fixed copy is needed.

### P4 5.3 bounded execution

Continue from main `b8d9ef09` / canonical Master Plan §17.53. Verify actual unpublished signed Direct/Play release package/version/certificate and release artifact guard without publishing or treating existing version metadata as a new release. Private signing configuration stays outside Git/logs. Extend synthetic same-account two-install native HTTP/SQL coverage to selected-device authority, unknown/legacy inventory exclusion, changed session/install, and OFF/relink fences. Exercise real Android work/notification behavior only in an owned isolated QA package with unusable production configuration and explicit synthetic fixture IO. Keep unknown/historical autonomous clients quarantined, and distinguish trusted fencing from client flags, version strings, installed debug fixtures and absence of sends. Real signed installed/mixed-build/canary acceptance remains separately unverified where not executed; no enabling producer/factory/readers, live account, FCM provider or release publishing is introduced.

### P4 5.3b isolated staging execution

Canonical checkpoint: Master Plan §17.54, main `42b0f21a`. The prior QA project is no longer found by full inventory; create a new private project/default `qa` environment and bind the initializer and runtime to its actual project/environment/service identifiers. Never wildcard/bypass the old isolation guard. PostgreSQL is private-only; native HTTPS is the only public app surface. The one-time reviewed empty-schema initializer is an operator action, not startup. Reuse native bearer verification and Smart mode/capability/due/claim/receipt; no production factory/producer/workers or bot/payment/AI/provider secret is copied. Synthetic fixtures are finite, private operator-seeded, explicitly marked and cannot be created/reset over public HTTP or prove real fleet fencing. Test boot refusal for wrong project/environment/service/database/origin, missing/revoked/foreign auth, unexpected schema or data and ordinary OFF/access/expiry/ownership vetoes before deploying. Signed QA builds must keep a separate install identity, trusted HTTPS and no production Firebase registration. No artifact publish or canary follows from provisioning staging.

After an interrupted unused seed expires, one explicit operator-only window may append a new day job with fresh synthetic native proof. Require the exact bound QA schema/account/devices, initial revisions, expired sessions and zero auth use/grants/attempts; refuse changed intent, any issued outcome or replay. Retain all old jobs, advance preference/grant/capability/routing generations and cap the new window to the current UTC day. Never rerun initialization, delete/reset history or enable a runtime producer. Reconcile implementation with refreshed main `12480fbb`; production entrypoint and normal release variants stay unchanged.
The signed QA host keeps only its shared test/runtime ABI and explicit test entry points; normal release shrinking is unchanged. A bounded roster of three explicitly identified synthetic accounts may be appended privately, with no HTTP enrollment. New independent cases require every prior grant to have a confirmed pre-call decline; preserve all prior day/grant/attempt rows and refuse unknown outcomes or replay. Use ordinary acknowledged logout/relink, never a local journal reset. Measure server/emulator UTC and retain QA-only non-sensitive veto evidence without changing any authorization predicate. Distinguish positive OS posting from truthful declines and leave real fleet/canary gates open.

### P6 6.1a retained-delivery analysis, following the owner scope correction

Continue from main `fab44d0d` and Master Plan §17.55. Old-APK expansion is deferred; proceed independently with current-client implementation. Add migration 0137 for minimal account-owned analysis facts and anonymous monthly totals. Internal capture reads existing owned jobs/attempts/Android receipts after their transaction commits, rather than accepting outcome assertions from an API or making an external-delivery commit depend on analytics. Keep the component dormant: no production sender/route/worker activation, provider IO or automatic fixture reset.

Deduplicate by owner and a hash of the immutable source/stage; require source timestamps, reject future/expired facts and count only inserted facts. Never turn reserved/in-flight/provider-accepted/client-posted-unverified into shown/read/learning. Shown, opened and attributed learning stay unavailable until a trustworthy implemented source exists. Do not add arbitrary payload/copy/device/session/token columns. Raw detail expires after D21's 90 days; a bounded explicit retention operation deletes only this analysis detail. Anonymous totals contain only UTC month, channel, stage and count, expire after twelve calendar buckets and remain separate from private actor/day/grant/OFF guards. No R2 snapshot/public endpoint or production sampling is introduced. Account purge explicitly removes own raw facts with FK cascade as backup; anonymous totals cannot identify an account. Downgrade refuses populated analysis tables. Verify real SQLite/PostgreSQL DDL, duplicate/racing capture, forged/foreign source, ambiguous/display semantics, deletion, retention boundary/late replay and unchanged issuance evidence. Register models and advance the reviewed standalone empty-QA head without running it against an existing database.

### P6 6.1b bounded source integration and retention scheduling

Continue from main `bb6d1878`, schema 0137 and canonical Master Plan §17.56. Reuse the existing analysis service with no new schema or provider. Add a default-false `SMART_REMINDER_ANALYSIS_ENABLED` switch. Android schedules only owner/job metadata in a bounded post-response background callback after a successful claim/receipt transaction closes; GET/auth/error/disabled paths create no analysis work. Telegram observes only after its committed terminal boundary, never within provider IO or the delivery transaction. A shared observer catches analytics failure/timeout without changing the committed grant, receipt, HTTP response or Telegram outcome. Parent cancellation remains cancellation. Disabled means no analysis SQL or cleanup task.

Wire one independent bounded analysis-only retention task into lifespan, gated by the same explicit switch and cancelled on shutdown. It creates no jobs, cohorts, attempts, fallback or feature authority and never blocks the legacy/shadow/Admin PWA scheduler. It uses D21's existing batch/expiry operations only. No flag is enabled remotely. Source hooks are best-effort observations: a process interruption can miss capture; never infer full coverage, non-display or negative learning from absence. Candidate/suppression instrumentation, durable reconciliation and trustworthy open/server-learning attribution remain parent 6.1 work before a meaningful baseline. Verify actual HTTP post-response ordering, PostgreSQL visibility/lock release, failure/timeouts/cancellation, duplicate receipts, Telegram known/unknown results, disabled zero-SQL, retention without source deletion and independent startup/shutdown. Keep dispatch and all provider/canary gates off.

### D06 current-device selection clarification

Continue from main `99028875` and Master Plan §17.57. Add a shared proposal-only destination selector for an owned unselected/unattempted shadow intent. Reuse canonical preference reduction, owner-first authentication/locking, current study-specific capability, active native session and token-presence checks; never read token values or mistake account-notice permission for study permission. Recheck intent revision/epoch/window and refuse already selected/attempted intents rather than moving an unknown send elsewhere. No cohort admission, producer, grant, provider or new endpoint is introduced.

One eligible destination is selected immediately without history warm-up. Multiple candidates use distinct server-verified learning references and last verified learning time, with explicit recent-reachability/stable-identity tie-breaking when evidence is absent/equal. Manual channel lock and global/channel/device OFF win. Unsupported hosts remain excluded. The selection stays non-authorizing and holds only one endpoint. The activity read window is explicitly supplied, not an invented product threshold.

Existing native `android_course` lesson-completion receipts already contain a server-bound device ID and server-produced result/gamification metadata. Read these with original canonical XP and accepted current-course progress, requiring nonduplicate positive matching XP and valid original timestamps; deduplicate original XP references and discard conflicting attribution. Existing history can qualify immediately. Unbound/replayed/reward/open/practice/Telegram history that lacks a trustworthy device/award binding remains explicitly unproven; partial positive observations do not prove absence on another endpoint. A privileged reader contract allows later verified source adapters without changing selection policy. Verify pure ranking and actual SQLite/PostgreSQL single-device, multiple-session, two-device, permission/OFF/revocation/expiry, forged attribution, frozen intent, read-only and current native producer-shape cases. Record limits honestly and leave runtime activation/source-coverage gates open.


### P6 6.1c bounded source reconciliation

Continue from main `73d0181b`, schema 0137 and Master Plan §17.58. Existing post-response/post-commit hooks can miss capture across interruption. Reuse the same source-derived capture/deduplication transaction to recover committed facts without touching delivery. Add an internal keyset source-page reader for current reviewed v1 Android/Telegram jobs with a nonexpired source timestamp (job reservation/terminal transition, attempt start/resolution or Android receipt). Include recent child outcomes even if the parent is older than 90 days. Bound page size and SQL duration; read only owner/job IDs and release the page transaction before per-owner capture. Revalidate owner/deletion/policy inside capture, preserving current lock order and D21 source-time expiry.

An independently gated/cancelled reconciliation task shares the existing default-false analysis switch with retention. Each tick has a finite total time budget, advances its in-memory cursor only after each completed or timed-out capture attempt, and isolates a failing/locked owner so other jobs progress on later ticks. End-of-pass and process restart rescan durable sources; source-stage uniqueness prevents duplicate totals. Cursor progress is not proof of complete measurement, and failed/purged/expired sources cannot be fabricated. No new table, flag, metric stage, provider, cohort, sender, account enrollment or source mutation is added. Existing callbacks and retention stay independent. Verify actual SQLite/PostgreSQL missed-hook recovery, late receipt/old parent, page/restart/idempotence, failure starvation/cancellation, real owner-lock timeout, deletion, source preservation and exact lifespan start/stop. Candidate/suppression and trusted open/learning linkage remain parent 6.1 work. Rollback disables the existing analysis switch; production dispatch remains OFF.


### P6 6.1d committed shadow decision facts

Continue from main `7ed0b161` and Master Plan §17.59. Existing shadow jobs retain terminal decision reason/state/time but delivery analysis intentionally excludes them. Extend the existing analysis stage constraints through additive migration 0138 for explicit `shadow_candidate` and `shadow_suppressed` facts, preserving job FKs and the existing raw/anonymous schemas. Reuse owner-first source capture, original terminal source time, D21 expiry, source-stage uniqueness and atomic monthly totals. Only exact shadow policy, unselected/unattempted terminal jobs with reviewed fixed reason codes qualify. A completed `shadow_candidate` is a policy simulation outcome; cancelled/expired or other completed reviewed reasons are shadow suppression. Never count these as reserved/delivered/shown, enroll a cohort or issue a grant. Mutable/pending shadows, unknown reasons/policies and any attempted/selected shadow job remain excluded.

Extend existing default-OFF source reconciliation to discover these committed terminal decisions. No new scheduler, endpoint, source mutation or callback inside delivery transactions is needed. Repeated/parallel scans count each job's terminal shadow stage once. Reasons come from a fixed server catalog; no arbitrary payload, token, message or feature is stored. Initial policy refusals without a durable reserved job remain unobserved, explicitly not zero or a complete denominator. Later real candidate/pre-reservation suppression and trusted learning attribution remain parent 6.1 work. Upgrade/downgrade preserve existing delivery analysis; populated new shadow stages refuse downgrade. Verify real populated SQLite/PostgreSQL DDL/model parity, actual shadow queue candidate/suppression, OFF/goal/access/cadence/D1, attempted/foreign/unknown exclusion, concurrent recovery, retention/deletion and unchanged delivery semantics. Advance only the empty-QA reviewed head; never initialize or migrate an existing remote database. Rollback disables analysis without dropping evidence. Production dispatch remains OFF.


### P6 6.1e pre-reservation shadow observations

Continue from main `d32224e3` and Master Plan §17.60. Existing terminal-job analysis cannot represent a refusal before a job exists. Add a minimal disposable reservation-observation table (owner FK, opaque dedupe key, explicit `shadow_reserved`/`shadow_refused` stage, fixed reason, original observation/expiry), with no fake job, device/session/token/payload/feature fields. Migration 0139 extends only the anonymous monthly stage constraint and creates this table; keep the job-bound event contract unchanged. D21 raw 90-day/source-time and monthly twelve-bucket retention plus canonical purge apply; populated new detail or monthly stages refuse downgrade. Advance only the empty-QA reviewed head.

The actual shadow queue reserve path constructs privileged immutable observation metadata from its verified locked owner/current preference revision, server course, actual result and post-lock clock. After its source transaction commits/closes, an optional strict/default-OFF bounded observer captures in a separate User-first transaction with fresh owner/deletion validation. Disabled creates no observation SQL. A rollback/auth error produces no observation. Capture failure/timeout does not alter reservation/refusal or retry it. Parent cancellation propagates. Reuse the existing analysis boolean and explicit observer dependency, including the existing shadow worker's queue; no producer/cohort/provider/endpoint is added.

Grain is one distinct reservation outcome/reason per canonical owner, frozen valid IANA local day (or explicitly technical UTC observation day when zone unknown), source version, preference revision and canonical course. Store only the opaque digest, not those personal scope inputs. Repeat checks are deduplicated and not a complete candidate denominator, unique learner count or send count. `shadow_reserved` means an actual shadow reservation, not cadence eligibility or real dispatch; `shadow_refused` preserves the actual refusal reason, not an unrelated existing job's earlier cadence reason. Initial D1/OFF/goal/access refusals can now be observed without a job, while untrusted/auth/deletion cases remain unavailable. Capture remains best-effort across commit/callback interruption; no source reconciliation can recreate an observation that never persisted. Verify exact post-commit visibility/lock release, real reserve outcomes, default-OFF zero SQL, replay/races, failure/timeouts/cancellation, unknown/future/expired/deletion refusal, retention/purge and populated SQLite/PostgreSQL migration/model parity. Rollback disables analysis while preserving evidence. Production dispatch stays OFF; real-dispatch/open/learning attribution and full coverage remain unfinished.


### P6 6.1f committed runtime guard reasons

Continue from main `78233efe`, schema 0139 and Master Plan §17.61. Reuse current job-bound cancelled/expired analysis and durable source reconciliation; no schema or new stage is needed. For reviewed current-v1 Android/Telegram jobs, preserve fixed approved original terminal guard reasons from committed source state/time. Keep channel-specific reason mapping and withhold arbitrary/unknown text through the existing generic stage reason. Existing captured facts remain immutable; do not rewrite earlier generic reasons or increment totals on enrichment/replay. A cancellation reason alone is not proof of non-display, inactivity or learning.

Android successful HTTP claim responses that actually return a reviewed mutating guard refusal can schedule existing capture only after source commit/session close and response body completion. Gate-only/unowned/auth/malformed/GET and transient nonmutating refusals create no new observation path. Telegram dispatch can observe its reviewed terminal guard result only after the source transaction closes, outside provider IO; accepted/unknown provider hooks remain unchanged. Source capture always rechecks current owner/deletion/policy and derives reasons from SQL, never from a learner request or arbitrary response text. Reconciliation recovers missed committed terminal facts. Default-OFF/failure/timeout/cancellation semantics preserve the original API/result/job/attempt/grant/provider behavior; no sender/producer/cohort/canary is enabled. Verify actual native goal/expiry/D1 and Telegram pre-provider refusal, original source reason/time, post-response/commit lock release, replay/unknown-text/channel mismatch, no non-display inference, existing receipt/provider truth and real PostgreSQL races. Rollback disables the existing analysis switch. Transient guards without committed terminal evidence, real candidate denominator and open/server-learning linkage remain unfinished.


### P6 6.1g bounded target-learning source projection

Continue from main `96ca00ae`, schema 0139 and Master Plan §17.62. Current Smart clients carry no job-bound notification-open proof. Add an internal non-persisting analysis projection for an owned reviewed v1 job: a positive original server-confirmed target-lesson result strictly after an evidenced contact attempt, within that job's frozen IANA local day and the original 90-day analysis window. Reuse `read_native_lesson_destinations` (original XP + current progress + successful nonduplicate server Android completion receipt). Its incomplete native-lesson coverage must remain explicit; unsupported Telegram/practice/open sources cannot become fabricated zeros or inactivity findings. The learning endpoint can differ from the notification endpoint: attribution is account-level, with no same-device or causal claim.

Require an actual Telegram provider-accepted attempt or Android posted-unverified attempt paired with its immutable matching grant/receipt. Unstarted, refused, declined or unknown contacts cannot establish this projection. The lower bound is the original attempt start (not a late receipt/replay timestamp); upper bound is the earlier of current time and frozen day end, exclusive at the day boundary. Validate original source order, owner, policy/channel, target and frozen IANA window; reject missing/conflicting/expired evidence. Deduplicate original lesson reference, not receipt arrival or repeated analysis. Return only fixed reason, optional original learning/boundary timestamps and explicit source limits, without retaining device, payload or arbitrary text.

Keep this method out of dispatch, cadence, observer/reconciliation and public/admin metrics. No schema, storage/stage, endpoint, flag, provider or product attribution window is added. Use a separate User-first transaction, current deletion/block checks and bounded existing source queries; no DML/autoflush. Alternatives of labelling nearby XP as notification-attributed learning, inferring opens from generic app telemetry or persisting a new funnel stage are rejected until direct attribution and cohort/window policy exist. Verify real SQLite/PostgreSQL source pairing, late/replayed XP, wrong course/target/owner/time, reward/open-only evidence, missing/over-limit observations, accepted versus unknown contact, source immutability, owner-lock order and deletion. Rollback removes the unused projection; delivery and retained evidence stay unchanged. Parent 6.1 and all experiment/canary gates remain open.


### P6 6.1h authenticated client-reported opens

Continue from main `d05c6ea1`, schema 0139 and Master Plan §17.63. Add optional opaque HMAC-SHA256 open proofs scoped separately to Android original grant/owner/device/session and Telegram original attempt/owner. Reuse configured native-auth and bot signing secrets with a dedicated namespace; no new key, credential in a URL/query, posting authority or consent. Issue only behind strict default-false analysis and an available key: pure optional Android successful-claim response metadata and Telegram authorized content fragment metadata. Keep provider IO outside SQL and metadata failure/absence independent of delivery. No token is persisted server-side or logged.

Consume only in authenticated own-job JSON POST adapters, with native bearer or fresh signed Telegram header and existing User-first current session/block/deletion checks. Re-read matching reviewed v1 job and original grant/attempt; require native original posted receipt or Telegram accepted attempt, valid chronology and the real frozen IANA day. Validate constant-time proof binding; wrong identity/channel/session, arbitrary open payloads and expired/unconfirmed sources cannot create facts. Request body has only strict version/proof; no user-selected owner, time, state or redirect. Missing early/offline receipts stay unknown rather than triggering a send or extending authority. A report is explicitly `client_reported_open`, not independently verified display/open, learning or causal return.

Migration 0140 extends only existing raw/monthly stage constraints. Reuse owner/stage source identity, atomic anonymous monthly increment, first report server time, D21 original-time 90-day retention, twelve month buckets and canonical purge. Replay cannot increment or extend expiry; populated downgrade refuses raw or anonymous-only open facts. Bump the reviewed empty-QA head without running remote migration/initialization. Rollback disables analysis and keeps operational evidence.

Android forwards optional proof through the live grant/post callback into explicit notification Intent extras, with local link epoch binding and strict parsing; legacy/widget entries carry no proof. Only actual notification entry attempts an authenticated best-effort report after current auth/link checks, outside locks. Do not persist/retry across accounts or block navigation. Telegram uses only fragment metadata on the existing validated course link; its visible authenticated Mini App entry sends one best-effort same-origin header-authenticated report, with strict duplicate/shape checks and no localStorage, generic-open fallback, or awaited navigation. Preserve signed Telegram launch data and existing routing/access. No fixed copy or visual/layout change.

Verify actual SQLite/PostgreSQL HTTP auth/claim/receipt and synthetic Telegram dispatch/open; proof transplant/forgery/session change, source ordering/unknown state, boundary/replay/race, failure rollback, default-OFF, retention/purge and populated migration/model parity. Verify Android optional decode/live forwarding/link fences and both Direct/Play JVM/compile paths; verify Mini App fragment/auth/visibility/duplicate/failure cases in JS/browser smoke. Real installed/provider acceptance and complete attribution/cohort/negative-learning coverage remain separate; dispatch/producer/admission/canary stay OFF and D24 stays last.


### P6 6.1i verified temporal study outcomes

Continue from main `d902c0af`, schema 0140 and Master Plan §17.64. Reuse the existing internal target-learning source scope and default-OFF post-commit capture/reconciliation. Add a bounded account-level reader for reviewed `course_v3`, `android_course`, `desktop_course` lesson completion and canonical `course_miniapp` mock/placement/training completion. Corroborate original positive unique XP reference/time against current matching course progress and trusted server terminal receipts; native lesson result metadata must still prove successful nonduplicate awarding. Practice requires its canonical owner-bound session, matching mode/event and valid scored result. Client telemetry, bonuses, unsupported/exam/legacy sources and incomplete/over-limit evidence cannot establish a positive result. Do not change existing policy/habit/destination readers or learning writers.

Extend the internal projection additively with partial account study count/first time and the original retained `client_reported_open` time, bound by the same original attempt's server-derived hash/channel/reason. Count only original verified results strictly after confirmed contact and before frozen IANA day end, capped by now and D21; a separate marker requires original XP strictly after the first server-received report. This is temporal source evidence, not causal attribution, verified human opening or a cohort window. Missing data remains unavailable, not zero/negative learning. Do not infer same-device study.

Migration 0141 extends only existing raw/monthly stage constraints for `verified_study_after_attempt` and `verified_study_after_report`. Reuse one job/original canonical study-reference/stage hash, original XP time/90-day expiry and atomic anonymous month/stage/contact-channel increment. Store no result payload, lesson/practice reference, device/session or XP amount in analytics. Capture remains separate from delivery commits and optional; existing bounded reconciliation recovers later available canonical source/results, with no new producer/hook/poller or cadence input. Raw/monthly replay is immutable. Populated downgrade refuses either new raw or anonymous-only stage; bump the reviewed empty-QA head, never a remote initializer/migration.

Verify real SQLite/PostgreSQL source pairing and current native/Telegram report flows, original/replayed/late/equal/future/cross-day results, malformed/forged/foreign/unsupported sources, partial bounds, missing/late/wrong-attempt report, atomic failures, races, retention/purge and populated migration/model parity. Preserve old target-only fields and delivery/protocol tests; no client/UI or fixed-copy change. Disable analysis for rollback while retaining operational/new observed evidence. Parent 6.1, full negative/causal/cohort coverage, numeric D09 and provider/cutover gates remain open; D24 stays last.


Owner clarification during 6.1i (2026-11-02): notification tapping is never required for study return. A learner may see the reminder and independently enter the app; original verified study after the attempt still counts. Keep click/report data secondary and leave primary retention/learning cohort measures independent of click gates. Causal benefit still requires the reviewed account-level control/treatment comparison; do not attribute every temporally later result to the message.


### P6 6.1j scored active-study day evidence

Continue from main `aceba08f`, schema 0141 and Master Plan §17.65. Original positive-XP completed units miss genuine repeated or failed graded work. Add an analysis-only bounded reader over existing server-only section_attempt_scored/course_miniapp, test_completed/course_hsk_exam and canonical course_attempts quiz rows marked miniapp_server_graded. Require canonical owner/course/lesson binding, strict scored pairs and reviewed server identity; do not treat client section_completed, opens, reward XP, AI/homework or percent-only payloads as study. Preserve every learning/XP/grading writer and the existing completed-unit interpretation. Missing deterministic repeat-practice events and voice remain explicit gaps.

Union reviewed scored timestamps with existing verified completed-unit times, under the current evidenced contact/frozen IANA local-day source scope. Expose separate optional first active-study times, never fake inactivity/zero. Record at most one study_day_after_attempt and one study_day_after_report per owned job/day, independent of question, attempt or XP count; a later graded attempt after a report may establish the secondary day even when the first activity preceded the report. Notification tapping never gates the primary day. Facts are immutable first-observed evidence, not a guaranteed earliest all-source timestamp. 0142 extends only existing raw/monthly stage constraints; D21 original-time expiry, deduplication, anonymous counters, reconciliation and account purge remain unchanged. No new poller/endpoint/flag/send authority. Finite source limits return unavailable for the affected class; independently verified other classes may still prove a positive day, never a complete count.

Verify SQLite/PostgreSQL source provenance, failed/repeated/no-XP work, day dedupe, manual return, temporal/report order, invalid/foreign/over-limit sources, source immutability, concurrency, atomic rollback, retention/purge and populated migration/model parity. Advance only the empty local-QA initializer head. Rollback disables analysis and refuses populated new-stage downgrade; no live query/configuration/migration or provider operation. No client/UI change. Owner selected a future 24-hour return measurement window on 2026-11-02, including midnight crossover; its cohort dedupe/overlap protocol belongs to 6.2 and is not silently applied to these technical local-day source facts.


### P6 6.1k owner-selected 24-hour study window

Continue from main `f791613c`, schema 0142 and Master Plan §17.66. Implement the owner's 24 elapsed UTC hours after an evidenced original contact-attempt start, crossing IANA midnight/DST. Keep existing frozen-local-day facts, open-proof validity and all learning/grade/access/dispatch writers unchanged. Reuse identical owner/contact/grant/frozen-day validation; a separate internal projection reads reviewed original completed units and scored activity in `(contact_start, contact_start + 24h]`, capped at observation time. Original completed-unit time has the 24-hour cutoff; a later observed server receipt can corroborate that original unit without moving its time. Existing readers retain their default evidence cutoff. Contact start must still lie inside the valid frozen source day. A positive result can appear before window end; elapsed time never proves complete source coverage, no study or causal benefit. Missing evidence remains None. Clicking is not required.

Minimal 0143 extends only existing raw/monthly constraints for `contact_study_24h` (one positive contact window per owned job) and `study_unit_24h` (one original canonical owner/activity-type/reference across ALL overlapping contacts, courses and channels). The first successfully captured qualifying job/contact-channel is immutable provenance, not latest-contact or causal assignment. Owner-first transactions and an owner/global-unit hash prevent duplicate units even under reverse-order/concurrent capture or late contact proof; do not move facts to a newly discovered contact. Two overlapping contacts may each have a positive window, but they do not become two unique learners, study returns or completed units. Monthly contact counters and canonical unit counters must never be added together or used as a cohort denominator/conversion rate. Primary learning/retention KPIs must independently deduplicate canonical account learning, including no-contact/control learners, in later 6.2.

Reuse default-OFF capture/reconciliation, original study time/D21 expiry, atomic counters and purge. No new flag, table, personal column, endpoint, poller, cohort, provider, client UI or learning-writer hook. Bounded reviewed sources only; limits/unknown outcomes/block/deletion remain unavailable. Existing local-day stage identities and times remain untouched. Verify both engines for 23:50→00:10 manual return, exact/just-after 24h, DST 23/25-hour days, failed/no-XP study, source/time/replay/foreign guards, overlapping/reverse/concurrent/late-proof capture, source preservation, failure/reconciliation, retention/purge and populated migration/model/empty-QA parity. Rollback disables analysis, preserves operational evidence and refuses populated new-stage downgrade. No live query, operator migration/configuration or activation; D09, real cohort baseline and D24 last remain separate.


### P6 6.2a first-ready baseline cohort and observed learning

Continue from main `bcf67edf`, schema 0143 and Master Plan §17.67. The owner rejected another routine technical-choice prompt; implementation uses first reviewed readiness as the origin, without another approval request. Record the first reviewed base-policy-ready shadow reservation per canonical account/protocol, independently of provider attempts or clicks. This is observed base-policy readiness, not full transport/cadence/admission eligibility or a complete traffic census. Reuse default-OFF analysis post-commit capture and reconciliation; never create consent, assignments, jobs or sends. Resolve the earliest retained reviewed owned shadow source before insertion. Original source time is immutable; expired first source cannot re-enroll after D21 deletion.

0144 adds minimal 90-day owned baseline membership (protocol, opaque source job, original entry time, frozen IANA zone/course, expiry) and anonymous UTC-entry-month totals (original enrollment count and latest D7 end). Counters increment only with first member insertion, atomically. User purge removes personal membership, preserving original anonymous denominators; raw expiry must not permit enrollment replay. Monthly totals retain twelve calendar buckets. Populated downgrade refuses raw or anonymous-only data. No job FK cascade is used to erase membership; source job is opaque provenance and operational evidence remains retained.

A bounded internal readout groups by entry UTC month, not contacts/responders/devices. Day 0 starts at the verified entry instant; week covers its first seven local dates; D7 is the full frozen local date +7, ending at +8. No pre-entry study counts; DST uses real IANA midnights. Final observed means/fractions require a closed entry month and completed follow-up, while immature/censored/over-limit states remain explicit. Retain all original enrolled accounts in denominators, including missing/purged/blocked/deletion cases; do not read protected personal learning. Source-backed positives are observed lower bounds, not complete retention, inactivity proof, causal lift or model readiness. No-contact/manual-entry study contributes. Later D1 overlap is annotated, never excluded by outcome or reassigned.

Use bounded canonical original-XP plus reviewed server-completion receipts account-wide across courses; historical completion must not disappear merely because current progress moved to another level. Extract/reuse the existing strict receipt validator; ordinary policy/target readers keep current-progress corroboration unchanged. Reviewed scored activity also spans canonical courses, without requiring fresh XP/pass. Dedupe original unit reference and active local dates per canonical account. Generic opens, rewards, client telemetry, unsupported/bad scores remain excluded. No answers/identities/features persist in anonymous results.

Verify SQLite/PostgreSQL actual queue reservation/post-commit/reconciliation, earliest/reverse/concurrent source capture, OFF/D1 refusal, deletion/purge/no re-enrollment, cohort original denominator/maturity, no-tap/no-contact/cross-course/failed work, source bounds/privacy, atomic failure and populated migration/model/empty-QA parity. Advance only the empty local-QA reviewed head. No UI/client/fixed-copy/provider/config/live migration or activation. Actual real baseline traffic, statistical calibration, randomized trial protocol and P6 6.2 remain open; D24 stays last.

### P6 6.2b bounded mature baseline aggregation

Continue from refreshed main `9a9ec6b8` (its public privacy-policy fix is preserved), schema 0144 and Master Plan §17.68. Replace the 128-member whole-cohort live read with incremental mature-member observation and a constant-query anonymous report. Reuse the existing default-OFF reconciliation loop, with an independent bounded membership cursor/budget so job traffic or an unavailable owner cannot starve baseline work. Restart/replay is safe; no new poller, flag, producer, API or contact authority is added. Every page is at most 128 IDs; learning sources retain their existing 512-row sentinels and each owner uses User-first locks and fresh deletion/block/expiry checks. Only completed D7 follow-up is materialized; partial live-week reads are no longer report results.

0145 adds minimal raw per-member observation time/counts/flags and anonymous monthly outcome totals. Under the same transaction, compare the locked raw snapshot with newly proven counts, preserve monotonic lower bounds, and add only nonnegative deltas to the original month. First observation increments observed-account count once; active-day/unit maxima and D7/D1/source-limit flags never lose previously proven evidence. A maximum is a conservative lower bound if source availability changes, not a union of unavailable historical references. Later retained server proof may improve these lower bounds without recounting an account. Source-limit flags remain conservative/sticky. Failure rolls back both snapshot and totals; concurrent workers serialize on User/member then total. No individual identifiers or payloads enter monthly totals.

The read-only report queries anonymous totals plus SQL-counted retained/valid/unobserved membership; it never fetches all owners or learning rows. Original denominator and maximum follow-up remain immutable. Preserve anonymous outcomes through raw expiry and personal purge, without decrementing a published count or recreating removed membership. Report pending/unobserved/censored counts explicitly; maturity counters now describe successfully observed mature accounts, not a census of all retained windows. Final lower-bound means/fractions still require closed month/latest follow-up, at least one observed account and no source-limit flag. Missing observation never becomes verified inactivity, true retention or causal/ML/dispatch readiness.

Test >128 members across bounded pages, late evidence/restart/reverse/concurrent aggregation, atomic rollback/recovery, fixed IANA windows, source-limit positives, protected owner zero reads, independent loop fairness/default-OFF zero SQL, read-only constant-query reports, expiry/purge retention, no replay resurrection and populated migration/model/empty-QA parity on SQLite/PostgreSQL. Rollback disables analysis and retains 0145 if it contains observations; empty-outcome downgrade preserves existing 0144 memberships/denominators. No real database, provider, configuration or activation action. Real baseline/traffic, complete sources, statistical calibration and D09 remain open; D24 stays last.

### P6 6.2c explicit read-only baseline report

Continue from main `96dc3361`, schema 0145 and Master Plan §17.69. The internal report has no operator entry point; expose only that existing anonymous one-month projection through `scripts/smart_reminder_baseline_report.py`. Require exact `--month YYYY-MM` and an explicit `SMART_REMINDER_BASELINE_DATABASE_URL`, without application settings/.env fallback, arbitrary SQL, account arguments, historical clock override, migration, retention or aggregation writes. No API/UI, new dependency/schema/flag/scheduler or change to baseline semantics.

Use a dedicated short-lived engine: PostgreSQL startup read-only defaults, statement/lock/connect timeouts and the service's transaction read-only guard; existing SQLite file in driver read-only mode plus connection query-only. Reject missing/unsupported targets, SQLite memory/missing files and URL options that could override reviewed connection policy. Bound the whole operation and always dispose the engine; errors output stable codes only, never credentials, SQL, driver messages or tracebacks. Stdout is the source report JSON, preserving missing/immature/limited/censored states and false readiness/dispatch flags. OS/database access remains the operator boundary; this is not a public unauthenticated endpoint.

Verify strict input/target validation before connection, no app configuration dependency, actual SQLite/PostgreSQL read-only enforcement, original anonymous projection/no source writes, unavailable/missing schema, timeout/cancellation/disposal and scrubbed CLI errors. Existing baseline/outcome/privacy regressions remain required; no unrelated client rebuild. After tests, an already authorized explicitly identified database may receive this bounded anonymous read only if a valid configured target is available; do not relabel synthetic or unidentified data as production, repeat old inventory/login/unlock work, enable Smart or invent baseline/power results. Missing access/data is an explicit measurement gap. Rollback removes the CLI only and preserves all existing schema, authority and sources.

### P6 6.1l existing scored practice completion source

Continue from main `2b56ac64`, schema 0145 and Master Plan §17.70. The shared Mini App/Android/paired Desktop practice service grades answers server-side and already writes canonical `test_completed`/`training_completed` events. Its deterministic completion/XP dedupe can leave a valid stored graded result without new in-window XP. Extend only the analysis-only scored-activity reader to that existing source; do not change graders, access, rewards, original completed-unit/habit readers, API/client payloads or source writers. This is stored-completion coverage, not a new repeat-attempt writer or complete practice history.

Require canonical owner and legacy HSK course, exact `course_miniapp` source, matching mock/placement/training event/mode/skill, version-1 canonical session scope and writer dedupe key, strict integer score/positive total within the existing bounds. Pin the actual audited protocol; reject future/mismatched sessions, client/native telemetry, generic opens, percent-only/bool scores and unrelated sources. Reuse the existing finite scored-event query/sentinel and existing positive local-day/24-hour/baseline consumers. Retain deterministic repeat-practice/voice coverage limits; source absence or overflow cannot become inactivity, a successful original unit or causal uplift.

Verify actual shared grading with an already rewarded original session, no fresh XP, all three modes and native-only ownership; original first result/time/dedupe must remain immutable. Test reader boundaries/source/course/session/skill/version/score/privacy and over-limit behavior, no-tap day/24-hour and baseline D7 consumption, existing strict completed-unit/habit/dispatch guards and actual Mini App/native practice API regressions. No new persistence, schema, retention class, flag, hook or poller is required. Rollback removes only this reader branch; retained facts and original learning sources stay intact. Real baseline access, complete repeat/voice/display sources, D09 and activation remain open; no live read/login/inventory or provider/configuration action. D24 stays last.


### P6 6.1m existing completed voice activity

Continue from main `95721817`, schema 0145 and Master Plan §17.71. The shared voice service persists canonical ownership and a positive turn counter only after server reply generation or its authenticated server-side Live provider relay; end_session stores completed status/end time. Extend only the analysis activity reader with a separate bounded query over those minimal fields, without loading transcripts, corrections, words, audio or usage/billing rows. Require canonical user_id (no legacy NULL-owner fallback), canonical UUID-v4 session, exact reviewed HSK course and turn/live mode, completed status, positive integer turns and ordered start/end wholly inside the requested window. The original end time is a conservative completed-session activity marker, not a per-turn, passing-grade or acoustic-quality claim. This also excludes closing an older pre-window conversation as new in-window activity.

Reuse existing positive local-day/24-hour/baseline/D21 consumers. One 512+1 voice sentinel marks only that source unavailable; independently verified quiz/practice can still establish activity. Rename the internal incomplete-voice limit to reflect partial coverage. Original XP/completed-unit, learning habit, access, source writers and seven-turn UI milestone stay unchanged. No new schema, telemetry, API/client or delivery authority. Legacy ownerless/band/unfinished/standalone pronunciation evidence remains unknown. Verify actual turn/end persistence with stubbed external AI, live provider-source regression, empty/failed/foreign/boundary/future/overflow/privacy and downstream replay on both engines. Rollback removes only this reader branch; existing sources and retained facts remain. Actual baseline access/calibration, fresh repeats, other voice/display coverage, D09 and activation remain open; D24 stays last.


### P6 6.1n optional repeat-practice traces

Continue from main `df8e6de5`, schema 0145 and Master Plan §17.72. Existing v1 practice IDs and canonical terminal/XP dedupe must remain: changing the reward reference to a random session would grant repeat XP. Current Mini App, Android and both Desktop consumers treat returned session IDs opaquely. With the existing analysis flag explicitly true, record a minimal server-only Smart start receipt before returning a compact v2 owner/nonce ID; fall back to v1 if optional start capture failed. Bind exact reviewed source, owner, mode/course/skill/language, original max-part (including unrestricted None) and a digest of server questions. New technical event names stay separate from canonical completions and the unrelated profile accuracy's general attempt consumer. No questions/answers are stored by the new trace.

Completion recognizes either unchanged v1 or an exact owned v2 receipt, with original ordered timestamp/90-day D21 lifetime, strict metadata and unchanged question digest. Rebuild from frozen language/window; no client-stated grade or scope can replace receipt evidence. Preserve all existing admission/ad/daily-use gates, grading/mistakes, canonical v1 terminal and XP identity. Optional nonce-scored capture happens after grading/reward and before source commit, deduplicates retained retries and cannot roll back learning on observation failure. Missing best-effort original capture remains incomplete history, not a guarantee about first human work time. An in-flight v2 receipt can still be read for grading after flag OFF; no new trace is captured then. Disabled new starts have zero trace SQL.

Read only exact owned reviewed scored traces with strict bounded scores, mode/skill/course/nonce/version/dedupe and source-time validation; reuse the finite event query, positive local-day/24-hour/baseline consumers and D21 facts. New Smart traces expire after 90 days via one additional narrowly scoped bounded deletion in existing retention; canonical learning/XP/profile source rows remain unchanged. Receipt hard expiry prevents resurrecting an old attempt after retention. Existing account purge removes these owned course-event rows. No schema, new flag, hook, poller or client/UI field. Rollback disables capture while retaining v2 completion compatibility through the normal receipt lifetime.

Verify both engines and actual shared start/grade flow, independent repeats with original reward once, retained retry/concurrent dedupe, failed/empty/foreign/forged/scope/content/TTL cases, capture failure/OFF, source privacy, bounded retention/account purge and profile isolation, plus actual Mini App/native API regressions. Parent 6.1 partial other practice/voice/display sources, actual baseline/access/calibration, D09 and real canary remain open; D24 artwork stays last.


### Owner simplification and P6 6.3 shared Admin control

Master Plan §17.73 supersedes directions to keep expanding tiny source traces. Retain accepted bounded V1 observations and explicit unknown coverage; defer pronunciation/drill/per-turn/display expansion. Do not delete functioning code or weaken actual baseline, D09, consent or provider gates. Proceed with the already scoped Admin control/readout using main `f109cb2d`, schema 0145.

Reuse the current `smart_study` notification template enabled field as the single cross-channel permission veto. Existing notification read/prepare/save, exact passkey content hash, raw CAS and audit remain the only mutation protocol. Add no second setting/router/command or activation mechanism. A common fresh template read vetoes queue/Telegram/Android preparation; Android rechecks immediately before new issuance. Already externalized outcomes/receipts remain valid. Enabling only removes this veto within all existing guards; it cannot manufacture consent, admission, jobs, grants or provider calls. Preserve compatible missing-row defaults and record reviewed `admin_study_disabled` reason. Rollback keeps this common guard and the original template contract.

Move the existing Smart editor to one System entry and exclude its duplicate generic-notices row. Add one anonymous current-UTC-month grouped read over reviewed study-day/contact-24h/original-unit counters and read-only analysis status in the existing authenticated read transaction. Missing rows stay null, stored zero stays zero and no personal/raw job fields are queried. Render partial observation definitions, no OS display, unique-user, causal or rollout claim. Reuse current components, canonical UZ/RU/TJ, one dirty-state Save/passkey, X/swipe and verified-success animation. Test admin security/proof/CAS, source-backed aggregation/privacy, cross-channel pause/final checks and receipt/OFF regressions, plus real mobile/desktop/locales browser acceptance. Keep no-data and unavailable states truthful. No schema/new flag/poller/tracing or provider activation.

### P7 offline comparison, main 538a7781

Master Plan §17.75 scopes the offline model tool. Reuse `smart_reminder_policy.evaluate` and approved habit calibration as the functioning baseline. A shared fixed-version circular nearest-neighbor regressor is an initial inspectable candidate: it needs no numerical library or production model service, respects midnight wrap, and can learn from past feature/target pairs. Choose it over a per-message LLM or a new training stack to keep this stage bounded. Fixed features contain personal rule-clock phase, weekday phase, distinct active-day count, gap and concentration; no account/platform/locale or outcome features. Fit only training rows whose original label was known before the explicit temporal cutoff. Evaluate later rows without refitting or tuning.

Strict bounded local input includes pseudonymous owner, original/as-of context, proof-availability times and optional original positive outcome; expired, future, limited, manual, protected or unobserved data cannot become an optimistic comparison. Reuse all real rule guards; no rows/predictions may authorize delivery. Fixed aggregate circular errors use paired model/rules on the same positive observations; ambiguous model output falls back to the rule clock. Explicit cohort privacy floor, unsupported/cohort coverage and seen/unseen counts prevent false overall generalization. Input data/model records are transient and not published. Only anonymous diagnostics/versions/input hash leave the process; no retention/causal/readiness claim, real export, schema/flag/provider or runtime wiring. Rollback removes the standalone tool without changing current rules or guards. Tests cover time leakage, expiry, guards, clock/DST, actual learning, reproducibility and scrubbed CLI boundaries.

### Current-rule personal-time integration

Master Plan §17.76 records the source-level disconnect: shared pure habit rules are used by the passive widget but omitted by queue and transport evaluations. Add an explicit personal-history option to the current context/cadence readers; align its start to IANA calendar dates (30 recent, sparse 90) and never shorten the original cadence history window or assert negative coverage. Manual/default explicit-window callers remain unchanged. Reuse this option in the widget, queue and adapters and explicitly pass the approved habit calibration to each integrated pure evaluation, including final pre-IO rechecks. Prefer this existing-service patch over another orchestrator or training/source system.

Frozen job/day/clock/target guards reject changed personal times instead of rescheduling old ownership. Externalized/issued/unknown facts and receipts retain their existing paths; no compatibility/schema version changes or new factory/producer activation. Verify real SQL learned-vs-saved progression, 30→90/calendar DST, manual/source/consent/goal and old-job rejection on both engines, preserving native wire/widget contracts. This accepts local rule-path integration only; real staging/canary/fencing and calibrated live cadence remain separate.

### Internal account planner, main 400ddb08

Master Plan §17.77 joins existing reservation, D06 selection and pending transport ownership in one opt-in service. Default OFF/missing cadence or coverage returns before sessions/IO. Preflight only already reviewed fresh routing metadata, current epochs/inventory, account state and Admin permission; do not create a review from client facts. Existing held Android versus activated Telegram ownership remains authoritative. Reserve the frozen shadow with the current queue, then in a new User-first transaction select/recheck D06 and bind one compatible pending intent. Reuse Telegram cohort/fresh validation and factor the current Android fresh-policy block for planning/claim without moving the grant boundary. Prefer this single orchestrator over new settings, schema, adapters or a parallel scheduler.

The actual selected Android endpoint gets an owned current session and must pass the existing privileged admission callback, capability/consent and canonical coverage/cadence checks. No native auth/grant is synthesized. Telegram uses its real feature setting/cohort. Recheck destination identity, Admin/D1, review expiry and frozen context after callback reads, then compare-and-set unselected/unleased/unattempted state. No provider, grant/attempt, endpoint fallback or new auth endpoint. Retry acknowledges an existing pending selection without reranking; terminal/foreign/attempted ownership remains immutable. Rollback disables the planner while existing pending jobs continue through unchanged live claim/receipt safeguards. Production factory/feed and real external activation remain separate. Test actual SQL both transports, selection/races/rollback and defaults/source privacy.

### Reviewed runtime host, main 9186945c

Master Plan §17.78 closes the missing host caller/factory with a single internal runtime. Bind explicit code-owned registration to the same settings/session factory; use existing typed admission/coverage interfaces and caller-supplied cadence/history, without defaults that assert real evidence. Rotate bounded reviewed-routing pages and reuse canonical actor/current course/calendar plus accepted planner. Process existing active selected work separately so a restart after scheduled time does not require another reservation. Native polls use the same configured factory; Telegram uses only existing claim/committed dispatch and an explicit trusted transport. No new schema, flag, HTTP registration, FCM hint or provider stack.

The main lifespan starts/cancels/awaits only a ready registered runtime; otherwise it preserves disabled native behavior and existing shadow-only configuration. Do not run the shadow-only evaluator beside an active runtime on the same host. Disable checks around trusted readers/provider, finite technical timeouts, sanitized per-account failures, rotating cursors and existing irreversible attempts bound work and prevent replay. A restarted host may continue an unstarted expired lease through existing Telegram checks, never replay started IO. Rollback removes registration/disables runtime while preserving native original receipts, account/day and uncertain evidence. Actual source completeness, calibration/fencing review and external canary remain unavailable; registration is absent in production.

### Early-return cadence correction, main c9898f7e

Master Plan §17.79 records the owner-authorized correction. Scope the unknown-outcome veto to an intent whose frozen window is still live; ended historical unknown intents retain their original state and weekly cost but cannot indefinitely suppress a new eligible day. Keep same-day/UTC-overlap ownership first, and never infer a miss, retry/fallback or confirmed display. Before any verified unsuccessful exposure, compare whole-day study rhythm against a local eligibility date. Preserve the original elapsed-time anchor for fractional-day medians to avoid rounding a 3.5-day rhythm into four days. The boundary is local midnight converted to UTC; the unchanged personal-clock policy remains the only actual send time. This avoids timestamp/minute and 23-hour DST drift without a new timer or daily campaign. Mature verified-shown observation/factor-two/stop behavior stays unchanged.

Regression tests cover the first missed day, unknown prior contacts, rolling three/week/day ownership, DST/jitter and actual SQL/transport integration. Production registration and authoritative feed/calibration/fencing gates stay open. Rollback retains all original day/attempt/receipt records; no migration or rewrite is needed. Do not restore a blanket historical veto as a substitute for same-intent ownership.

### Native persisted review/admission, main 94dbd9f1

Master Plan §17.80 closes the missing native review writer/read source in the existing routing service and Android service module. Reuse current held rows, native P1 User-first ownership and typed three-True operator review; a distinct account-native binding in the existing hash column separates native proof from Telegram activation. Native-only accounts need no invented Telegram identity. No new state/schema/API or review framework is needed. A new hold clears proof/increments generation and preserves historical attempts; a native review leaves held ownership and cannot replace differing reviewed evidence without another hold. Preserve existing Telegram behavior.

The explicit-window read-only callback binds stored native proof to an actual owned unattempted shadow or selected pending native job/session, current consent/revision/epoch, capability and unchanged inventory. It caps all known deadlines and performs no autoflush/commit/provider or evidence writes. The real claim still authenticates and issues grants independently; the callback is not posting permission. A caller may explicitly inject this source into the existing runtime/factory after external review; no production registration or fabricated complete-learning source is supplied. Verify actual SQL and HTTP flows, expiry/drift/OFF/attempt/identity guards, zero writes/privacy and unchanged Telegram/receipt behavior.

### V1 finishing order, main b8c1c55f

Master Plan §17.81 scopes today's remaining work. Reuse existing canonical learning XP and the already reviewed bounded `read_scored_activity` validation for a read-only observed-learning adapter. It preserves original times, owned context, explicit scope/overflow limits and privacy, and supplies no complete-negative-history claim. No new source trace, model, schema or scheduler is needed. Test real SQL positive/no-XP/foreign/reward/future/replay/overflow behavior and zero writes.

D25 now explicitly approves ordinary reminders from current progress/observed positive activity without complete negative history. Keep old strict calibration/source behavior unchanged, and opt in only through a distinct observed calibration/source pair. Preserve every day/weekly/permission/review/source/access/quiet and irreversible attempt guard. Latest actual graded/learning activity can suppress return work without changing habit/unit/statistical truth; missing coverage cannot label abnormal inactivity or failed exposure, and an unresolved verified-shown series is suppressed. Use approved D16–D20 values and no unapproved inactivity multiplier. Reuse extended positive history independently of the unchanged negative/ledger window. Construct the existing runtime/native SQL reader/post-commit Telegram boundary behind one new explicit `SMART_REMINDER_ENABLED=false` startup switch; the shadow-only and Telegram switches retain their separate meaning. No automatic operator hold/review or schema change. Local tests/publication do not satisfy actual canary/fencing/display/ML evidence. Finish functional checks before D24 artwork; V2 adapters and model validation remain conditional.

### D26 A/B evidence and final D24 source work

Master Plan §17.82 distinguishes the owner-selected technical canary from account-randomized efficacy. Reuse §10.3's proposed reminder/holdout experiment; persist canonical assignment/entry/version and preserve D1, original denominators, consent/fencing and outcome uncertainty. Existing baseline has no arm evidence and cannot silently become a randomized report. Actual source coverage/traffic and D12-reviewed numerical protocol precede exposure. Do not build another trace/report framework while those inputs are absent.

While physical/server access is unavailable, finish the existing D24 final source task after accepted functional wiring, keeping real canary/A/B/rollout acceptance open. Extend only the approved original panda atlas and local visual mapping from verified displayed streak plus current authenticated personal phase. Neutral/quiet/paused/stale stay calm, completed stays celebratory, and playful waiting cannot invent late/broken/comeback signals. Preserve separate header/art cells and canonical existing typography/copy/flame; check Direct/Play and existing widget fixtures.

### D27 complete reference widget delta

Master Plan §17.83 replaces the limited atlas-only D24 draft with the owner's full reference scope. Preserve v1 shape; explicitly requested v2 adds one owned last-observed-positive timestamp, with existing source/privacy bounds, no negative-history claim, no schema/trace/scheduler. Android accepts both supported envelopes and uses authenticated personal timing/local-day expiry to select expanded panda/caption/palette/flame presentation. Zero-streak return artwork uses optional known positive-time age; unknown/quiet/paused/stale stay calm. Existing canonical XML stays frozen; a registered UZ/RU/TJ sibling bundle supplies reference-style short captions. Art/mapping/UI must be checked on both Android variants before publication; live canary and randomized effectiveness remain distinct.


### D29 actual V1 client preference integration

Master Plan §17.87 records the source audit and owner code-first instruction. Reuse P1 GET/PATCH through one native epoch/auth-generation-fenced adapter; explicit current-device intent never changes global or another channel's OFF. Unknown legacy state is not imported as ON. Missing IANA initialization is a separate authenticated explicit write from actual OS/browser zone, without consent and without overwriting existing zone/manual time. Retain exact UUID/body retries and revision CAS; uncertain ON cannot rebase over intervening OFF. Durable latest intent/local immediate OFF survives offline refresh and is erased on account replacement. Existing native profile/primer controls and foreground/widget refresh share the adapter; OS denial remains capability rather than intent. Mini App initializes only a missing zone using verified Telegram headers. Test real uninitialized consumer flows before final private APK; no new schema/worker, A/B, public rollout or provider authority.

### Operator-controlled production dispatch and public cutover

The existing signed Smart editor remains the runtime permission surface. Show live runtime registration for Android and Telegram and an anonymous count of unexpired routing reviews. A routing count describes review records only. Effective account delivery still requires fresh consent, destination and fencing checks.

Serialize final Android grant and Telegram attempt authorization with the existing template setting transaction lock. Readers share the lock. The admin writer acquires it exclusively. Once the save commits, a later authorization must observe the new value. Previously committed authorizations remain governed by their original attempt and expiry.

The Telegram motivation scheduler checks sticky routing before its evening goal, streak and unfinished-lesson decision. The check applies to existing held accounts. D1 and rating keep their separate paths. A scheduler that already passed the check remains part of the legacy drain.

Public cutover requires a server-owned barrier covering every competing study sender, followed by a drain of outstanding legacy delivery and a verifiable migration condition for older Android clients. A version string, missing device rows or a startup flag alone supplies no proof. Reuse the existing review and account-day ledger only after those conditions are established. Preserve explicit learner OFF and keep unknown outcomes in their original day budget.
