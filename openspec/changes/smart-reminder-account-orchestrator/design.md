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

## Risks / Trade-offs

- **Old offline APK can display outside the ledger** → Do not migrate accounts with unknown/unsupported autonomous sender state into new cross-channel dispatch. Test historical binaries and describe the remaining physical display limit honestly; no server-only “exactly once” claim.
- **Provider success followed by crash leaves uncertain outcome** → Reserve/commit before IO, persist an attempt before send, classify uncertain result as unknown and suppress alternate delivery. Reconciliation never treats timeout alone as non-display.
- **A single unique `(user, local_day)` may be bypassed during travel** → Freeze account zone/day/UTC window, compare overlapping proposed day intervals and suppress ambiguous transitions; include date-line, fractional zone and DST tests.
- **A stale client or migration rerun can resurrect OFF** → Monotonic CAS revision/epoch and source-scoped legacy adapters; preserve OFF through rollback and dry-run replay.
- **Missing blocked/deletion checks in a reused auth context** → Re-evaluate account/device/session/deletion eligibility on every Smart read/write/claim/send; test logout, revocation, relink and purge races.
- **Scheduler head-of-line blocking or two replicas** → Durable due jobs, bounded worker execution and DB uniqueness/lease; fault-inject a slow/failing Admin poller and simultaneous claims without changing unrelated financial job semantics.
- **Display/open metrics can overclaim effectiveness** → Separate provider acceptance, client API invocation, verifiable display, open and server-confirmed learning; protected admin reports show denominators and unknowns.
- **Schema downgrade/data purge may lose consent or jobs** → Use additive migration and staged backfill; a downgrade that would delete active/newer consent state must refuse destructive removal. Stop dispatch first and retain data until a reviewed archival plan exists.

## Migration Plan

1. **P0 audit before code:** refresh `origin/main`, source/test inventory and Alembic head; build a source-cited matrix for Telegram picker/actual OFF actions, Mini App motivation, Android local ON, device mirrors, study OS channel and historical Direct/Play APKs. Verify deployment scheduler replicas/flags and current DB stamp in authorized staging. Record unresolved sources as unknown. Accepted source audits/live reads are in Master Plan §§17.27–17.34. Per owner direction, remaining installed/mixed-build acceptance is deferred to P4/P8 and does not block dispatch-OFF P1. OpenSpec validation itself is not acceptance.
2. **P1 additive, dispatch OFF:** add reviewed schema and strict authenticated read/CAS APIs, idempotent source-aware backfill and deletion hooks. Verify old API response compatibility, concurrent OFF/stale ON, migration rerun, account purge, SQLite/Postgres up/down safety and no newly sent reminder.
3. **P2 shadow:** introduce deterministic rules, job/attempt reservation and reason codes with external sending disabled. Compare planned outcomes against current senders, exercise two workers, crash windows, late ticks, time zones, completed goals, D1 holdout and account status. Fix source-specific feed localization separately if its DB roundtrip test reproduces the mismatch.
4. **P3 Telegram cutover:** guard old server Telegram study sender per verified cohort *before* enabling new delivery. Start with permitted Telegram-only canary; confirm opt-out, weekly/ranking coordination, D1 holdout, real UZ/RU/TJ, Bot accepted versus read distinction and rollback. Keep motivation and account notices on their own policy.
5. **P4 Android cutover:** release and verify Direct/Play protocol binary first with server Smart dispatch OFF. Prove both WorkManager and FCM use claims, no autonomous post, study-channel permission report, logout/epoch fence and offline fail-closed behavior. Enable single-device then verified multi-device cohorts only after old-client exclusion/cutover evidence, mixed-build and real FCM/OS/device tests.
6. **P6/P7/V2:** instrument source-backed outcomes and minimal protected Admin controls, baseline and experimental power before optimizer gates. Only validated ML with per-user evidence switches automatically from rules; learner PWA/Desktop adapters follow as V2 on the existing core after real platform capability checks. D15 widget work shares the P2 context, lands Android rendering with P4 and adds iOS plus paired macOS/Windows widget adapters later against the same versioned projection and golden fixtures. Passive widget release never authorizes new notification rollout.
7. **P8 release/rollback:** exercise staging migration with backup restore and a dispatch kill drill; inspect every remaining legacy sender ownership path. On rollback, turn new dispatch OFF, expire pending grants/jobs, keep explicit OFF/revisions/channel provenance, and resume a legacy sender only for an individually verified eligible cohort without replaying ambiguous work. Record automated, real Telegram, two-Android-device, OS permission, provider, staging and monitored canary evidence in the Master Plan before claiming production acceptance.

## Open Questions

The exact weekly cap, category cooldown, reactivation thresholds, retention TTLs, ML quality gate and experiment targets remain deliberately unset by D03/D05/D08/D09/D12/D13. P0/P6 measurement and the Master Plan's owner decision process must settle values before those policies are enabled. The contract and phased implementation path above do not depend on assuming any of these numbers.


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
