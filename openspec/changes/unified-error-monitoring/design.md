# Design

## Context

Motivation is in `proposal.md`, requirements in `specs/`. These facts were audited on branch `feat/analytics-android-lesson-start-20261112` (2026-11-12). The branch contains `origin/main` `680761f1`, Analytics Integrity (PR #285) and R1. A read-only Graphify pass (2026-11-13, AGENTS.md Graphify rule) added the Lava Telegram alerts, live voice, the `apiCall` classifier and the LI onboarding page; each lead was verified in code.

### Existing failure signals

| Signal | Code | Storage / consumer | Gap against the requirements |
|---|---|---|---|
| Mini App `app_error` | `course_v3_onboarding.html` `reportOnboardingSaveError` → `/api/miniapp/event` (`app/main.py`, verified `initData`) → `AppErrorContextService.record_miniapp_error` | Row in `messages`, `content_type='app_error_context'`. It stores raw message, stack, URL and extra. Consumers: bot AI context (`bot/handlers/messages.py`), Inbox `technical` (fixed `CASE` codes only), `bot_block_cause_service`, the analytics experiments count. Each row enqueues `enqueue_automatic_alert(source='technical')` | Onboarding only; no grouping; one push per row; raw text stored (pre-existing) |
| `/api/v3/clientlog` | `clog()` in `course-v3.html` (Mini App + PWA) | `logging.warning` with event, message and user agent; unauthenticated | No incident; free text in logs |
| Manual reports | `/api/v3/android/bug-report`, `/api/v3/pwa/bug-report` → `reserve_native_report` | `admin_pwa_native_reports`, Inbox `android`, automatic push, Telegram delivery, 30-day purge | Separate manual feature; stays as is |
| Android crashes | none: no `UncaughtExceptionHandler`, no `ApplicationExitInfo` (minSdk 26, targetSdk 36) | — | No automatic capture |
| PWA JS errors | none: no `onerror` / `unhandledrejection`; `/api/v3/pwa/event` allowlist rejects `app_error` | — | No automatic capture |
| Backend 5xx | process logs only; middleware is GZip and `BlockedUserApiMiddleware` | — | No capture |
| Lava admin alerts | `LavaNotifier.admin_alert(code)` in `app/services/lava/notify.py`, called from `lava/checkout.py`, `lava/events.py`, `lava/reconcile.py` (`activation_failed`, `amount_mismatch`, `retry_exhausted`, `renewal_overdue`, `webhook_auth_failed`, …) | Telegram message to each admin, per-code throttle | No incident. **Stays unchanged** (owner decision 2026-11-13): Telegram and Inbox/Push both deliver |
| Live voice failures | Android `feature/voice/LiveVoiceSocket.kt` `fail(reason)`, PWA `voice-live.js` `fail(code)`; fixed `live_*` reason codes. Not routed through `apiCall` | Shown to the learner only | No capture |

### Reusable parts

- **Inbox:** `app/admin_api/pwa_inbox.py`.
  - Sources are `bot`, `release`, `android`, `payment` and `technical`, with bounded per-source keyset paging and a cursor.
  - `/api/admin/v1/inbox/list` lives in `pwa_read.py`.
- **Triage:** `pwa_inbox_triage.py`.
  - Store: `admin_pwa_inbox_triage` (PK `source`, `source_id` int), statuses `new` / `read` / `assigned` / `resolved`.
  - Operations include `reopen`, with revision CAS and an audit table whose `actor_user_id` is nullable.
- **Push:** `pwa_push_outbox.enqueue_automatic_alert` uses a fixed event key per source row. `admin_pwa_push_dispatch` adds lease, retries and a 30 s per-device cooldown, and sends only `{kind, source}`. `sw.js` has fixed per-source labels and a fixed `/admin/?inbox=1` link.
- **Source CHECK constraints** on outbox, triage and audit; migration `0127` extended them for `technical`.
- **Analytics** (Monitoring reuses it):
  - registry `FEATURE_ANALYTICS_COVERAGE.json`: platform keys `android`, `telegram`, `iphone_pwa`, `macos`, `windows`; 20 flow IDs; `critical_paths`; exemptions;
  - stdlib AST checker `scripts/check_analytics_coverage.py` with `push` / `pull_request` diff modes;
  - workflow `analytics-integrity.yml` (PostgreSQL service);
  - Report freshness `pwa_analytics_freshness.platform_freshness`.
- **Transports:**
  - Android bearer: `DesktopAuthService.authenticate`, `device.platform == 'android'`, as in `android_events.py`;
  - PWA: cookie + CSRF + same origin, `PwaAuthService.mutation_actor`. The client knows its owner through `X-HSK-PWA-User-ID` / `PWA_COURSE_USER_ID`;
  - Mini App: verified `initData` in `/api/miniapp/event`.
- **Housekeeping:** the hourly loop in `app/main.py` (lifespan) already purges native reports in bounded batches.
- **Android:**
  - `DISTRIBUTION_CHANNEL` build field (`play` / `direct`);
  - an AtomicFile outbox pattern (`assistant-outbox`) and WorkManager;
  - R8 strips `@Serializable` models in release builds unless they are kept;
  - `core/network/ApiResult.kt`: `apiCall` is the single failure classifier. `toApiError()` reads the error body once, and `ApiError` keeps no HTTP status.
- **Learner PWA:**
  - `course-v3.html` serves both the Mini App and the PWA (`PWA_COURSE_HOST`), plus `course_v3_*.html` practice pages (including the LI guest onboarding page `course_v3_li_onboarding.html`), `subscription.html` checkout and `iphone-pwa-voice.html`;
  - the service worker serves `?v=`-pinned assets Cache First.

### Scope

- The latest migration is `0154`; Analytics R3 plans the next number.
- There are about 420 route decorators: ~77 `/api/v3/android/*`, ~73 PWA and `pwa-auth`, the shared `/api/v3/*`, `/api/miniapp/*`, ~34 Desktop routes (frozen) and the Admin routes.
- Android feature packages: `ad`, `assistant`, `auth`, `course`, `dictionary`, `feedback`, `foundation`, `hint`, `lesson`, `limit`, `offline`, `onboarding`, `practice`, `profile`, `rating`, `update`, `voice`.

## Goals / Non-Goals

**Goals:**
- One automatic, privacy-safe failure → incident → Inbox/Push chain for Android, PWA and Backend, plus a compatible Mini App path.
- Make monitoring coverage a CI-enforced property of every new important feature from the first work package.
- Reuse Analytics identifiers, registry, checker and workflow; keep KPI events and incidents apart.

**Non-Goals:**
- A vendor SDK (Sentry, Crashlytics), Redis, a new worker, queue or second Admin panel.
- Automatic root cause. Raw stacks are never collected, so grouping is by catalog codes and is intentionally coarse.
- Changing manual bug reports, the bot's AI error context, analytics event stores or KPI values.
- Desktop code, adapters, tests or CI (freeze). Admin PWA self-monitoring.
- Sanitizing the legacy `messages` app-error text or retiring `/api/v3/clientlog`. Both are owner follow-ups after acceptance (see Open Questions).

## Decisions

### D1. Server-owned catalog; features reuse Analytics flow IDs
`app/services/monitoring/catalog.py` holds only data:
- **Features.** `feature_code` = an Analytics flow ID, such as `lessons`, `practice`, `checkout_payments` or `onboarding_activation`. Monitoring-only IDs are added only where no flow exists:
  - `app_shell`: a global crash or an unknown screen;
  - `auth_session`: sign-in and session restore failures (the Analytics `client_activity` flow counts activity, not sign-in failures);
  - `monitoring`: self-checks, such as `queue_dropped` and `self_dropped`.
- **Failure codes.** `failure_code` gets a default severity (`critical` / `high` / `normal`) and a localization key. Examples: `crash_uncaught`, `crash_native`, `anr`, `js_uncaught`, `js_rejection`, `api_5xx`, `api_decode`, `load_failed`, `save_unconfirmed`, `restore_failed`, `server_5xx`, `server_exception`, `provider_failed`, plus the onboarding codes that today's `_technical_explanation_code` uses.
- **Site codes.** Bounded `site_code` values per feature: screen, page or route-template IDs.
- **Route map.** `route_map` maps an exact learner route path to a feature. It serves the backend reporter and the CI inventory.

Expected outcomes (limit, paywall, cancel, 401/403/409/429, offline) are deliberately absent, so they cannot be reported.

- *Why:* the backend needs the allowlists at runtime, while the docs JSON registry is CI-only. One runtime source avoids drift.
- *Alternative rejected:* a code list inside the registry JSON read at runtime. It would couple runtime to docs.

### D2. Storage: two tables, one additive migration
- **`diagnostic_incidents`:**
  - `id` int PK (fits the Inbox `RowId`); `fingerprint` char(64) unique; `platform`, `feature_code`, `failure_code`, `site_code`, `severity`;
  - `occurrence_count`, `refused_count`;
  - `first_seen_at`, `last_seen_at`, `first_version`, `last_version`, `resolved_version`;
  - `alert_epoch`, `last_alerted_at`.
- **`diagnostic_receipts`:**
  - `id` bigint PK; `incident_id` FK CASCADE; `user_id` FK `users.id` ON DELETE CASCADE, null for server rows;
  - `event_id`, `received_at`, `client_time` (nullable, flagged when skewed), `app_version`, `channel` (`play` / `direct` / null), `outcome`;
  - unique `(user_id, event_id)` plus a partial unique index on `event_id` for server rows;
  - indexes `(user_id, received_at)`, `(incident_id, received_at)` and `(received_at)`.
- The same migration adds `diagnostic` to the outbox, triage and audit source CHECKs. Its downgrade refuses while `diagnostic` triage or outbox rows exist, as `0127` does. It is tested on local PostgreSQL: create_all + stamp + upgrade/downgrade.
- **Fingerprint:** `sha256("v1|platform|feature|failure|site")`, computed on the server. Version is stored, not grouped (finite fingerprints).
- **Platform:** `android`, `iphone_pwa` or `telegram` (Analytics keys). A backend row uses the route's client when the path prefix fixes it, otherwise the monitoring-only key `server`.
- **Status:** not duplicated. The triage row (`source='diagnostic'`, `source_id=incident.id`) remains the only status.
- *Alternatives rejected:* reusing the `technical` source ID space (it collides with `messages.id` triage rows); one table with occurrences only (no idempotency).

### D3. Intake transaction: idempotent, atomic, bounded
One service function, `ingest(db, owner, transport, events)`, runs one transaction:
1. Validate the bounded schema. Unknown and forbidden keys reject the request. Each event is checked against the catalog.
2. If the owner exists, take `pg_advisory_xact_lock` on the owner and count that owner's receipts of the last hour against the cap. The cap holds across workers without locking `users`, so no contention with lesson writes. SQLite tests skip the lock.
3. `INSERT … ON CONFLICT DO NOTHING RETURNING` the receipts, so only new `event_id`s count.
4. `INSERT … ON CONFLICT (fingerprint) DO UPDATE` on incidents (count, last seen, version).
5. Run the reopen and alert decisions (D6, D7).

Events refused by the cap still have a known fingerprint. They increment only that incident's `refused_count`, which makes its affected count `partial` (D6), and are acknowledged so the client drops them.

**Routes:**
- `POST /api/v3/android/diagnostics` (bearer);
- `POST /api/v3/pwa/diagnostics` (cookie + CSRF + same origin; no query; no `X-Telegram-Init-Data`);
- the Mini App reaches `ingest` from its existing `app_error` branch (D9).

**Bounds:**
- request body ≤ 16 KB and ≤ 20 events;
- `event_id` is a UUID;
- version regex ≤ 40 characters;
- client-time skew ±7 days.

**Mode:** `MONITORING_MODE=off|owners|all`.
- In `off` the route returns `{"accepted":0,"paused":true}` without a DB read. The client then pauses for 24 h.
- `owners` admits only accounts in the existing admin allowlist (`admin_id_list`). No new setting.

Defaults (catalog constants, not owner decisions): cap 60 events per account per hour; receipts kept 30 days.

### D4. Backend reporter: post-response, never in the request transaction
- **Middleware.** A pure ASGI middleware matches the routed path template against `route_map`. It records `server_5xx` for a 5xx response and `server_exception` for an unhandled exception, then re-raises unchanged. 4xx and bodies are never read.
- **Writes.**
  - Writes run in their own session as `asyncio` tasks, behind a process-local semaphore (8).
  - A 10 s per-fingerprint coalescing window sends one `ingest` with `n`.
  - When saturated, the write is dropped and counted in process. The hourly loop flushes the count as the `monitoring/self_dropped` self-incident.
- **Integration failures.** Failures that do not surface as 5xx use `report_server_failure(feature, failure, site)`. V1 call sites: the Lava webhook/ledger processing exceptions and AI/voice provider failures. TTS already returns 502 on allowlisted routes.
- **Lava Telegram alerts stay (owner decision 2026-11-13).** `report_server_failure` is added next to `LavaNotifier.admin_alert`, never instead of it. The admin gets the same failure as a Telegram message and as a diagnostic incident (with push when critical). The monitor never suppresses, deduplicates, throttles or reroutes Telegram alerts.
- *Why:* zero added latency on learner routes, and failures never change responses.

### D5. Client reporters
**Android** (`core/diagnostics`, both flavours):
- **Crash.**
  - The crash handler wraps the default handler. It synchronously writes one ≤ 1 KB record (AtomicFile in `noBackupFilesDir`), then delegates.
  - The record holds a feature from the current navigation route, `crash_uncaught` and a fixed exception-category site.
  - The handler makes no network call.
- **Exit reasons.** On API ≥ 30, `getHistoricalProcessExitReasons` maps crash, native crash and ANR. A stored last-seen timestamp prevents re-reporting.
- **Handled failures.** The shared `apiCall` wrapper reports `api_5xx` and `api_decode` (it also catches R8-stripped models) for call sites tagged with a feature. Offline, 4xx, limit and paywall are not reported.
  - The hook lives inside `apiCall`, because `ApiError` has no HTTP status. `api_5xx` comes from `response.code() >= 500`. `api_decode` comes from the 2xx-without-body branch and the non-IO `unexpected` catch.
  - The reporter reuses the `ApiError` that `toApiError()` returned. It never reads the error body a second time and never adds a second parser.
  - `Offline` and `Timeout` are transient and not reported.
- **Live voice.** `LiveVoiceSocket` does not use `apiCall`. Its `fail(reason)` reports to `voice` only for a fixed allowlist of client-side reasons: `live_connection_lost`, `live_message_invalid`, `live_message_too_large`, `live_send_failed`. Server-sent codes (limits, quota), learner close and backpressure are not reported. The reason becomes a site code, never free text, audio or transcript. Voice V8 (`feat/ai-voice-v8-pwa-android-20261111`) may change these codes, so task 1.1 re-checks them.
- **Queue.**
  - At most 50 events, TTL 72 h, entries stamped with the account ID.
  - Logout or an account switch purges the queue; a crash record of another owner is dropped.
  - Flush runs after first frame and through unique WorkManager work (network constraint, exponential backoff, at most 3 attempts).
- **Dropped events.** When events are dropped for cap or TTL, one content-free `monitoring/queue_dropped` event is queued in their place.
- **Channel.** `channel` = `BuildConfig.DISTRIBUTION_CHANNEL`, so Play and Direct are visible per receipt. Analytics cannot show this split (A19).
- **R8.** Keep rules for the DTOs; verified on release builds.

**Learner web** (one script, `course_v3_data/hsk-diagnostics.js`):
- **Loading.** Loaded with `defer` by `course-v3.html`, `course_v3_li_onboarding.html` and the PWA practice/checkout/voice pages.
- **Capture.**
  - `error` and `unhandledrejection` listeners map `error.name` to a fixed category.
  - The site is a fixed page ID.
  - `HskDiag.report(feature, failure, site, outcome)` reports load, save and restore failures at existing call sites, after their own retry.
  - `voice-live.js` `fail(code)` reports the client-side codes `live_connection_timeout`, `live_response_invalid`, `live_audio_invalid` and an unexpected socket close. Server-sent codes, `live_network_slow` and `live_audio_suspended` are not reported, matching the Android allowlist.
- **Transports.** PWA: `/api/v3/pwa/diagnostics`, `fetch` keepalive with the CSRF header. Telegram mode: `/api/miniapp/event` with `event:"app_error"`, `schema:"diag.v1"` and `initData`.
- **Queue.**
  - `localStorage` per owner, at most 30 events, TTL 24 h.
  - Flush on idle after load, on `online` and on `visibilitychange`, with at most 3 attempts.
  - An owner mismatch discards the queue.
  - Drops are reported as one `monitoring/queue_dropped` event, as on Android.
- **Loop guard.** A re-entrancy flag, at most 10 events per page load, and a 10-minute coalescing window per fingerprint.
- **Assets.** The new asset gets a `?v=` date-blobhash token (service worker Cache First). Nothing runs before first paint.

### D6. Inbox projection and triage
**Projection.** `unified_inbox` gains a `diagnostic` branch.
- **Visibility:** `last_seen_at` within 30 days, or triage not `resolved`.
- **Fields returned:** platform, feature, `failure_code` (the client renders the localized text), first/last version, first/last seen, occurrences, channels, severity → priority (`important` for `critical` / `high`) and triage.
- **Affected accounts:** computed only for the ≤ 51 page rows, by an indexed `count(distinct user_id)` over retained receipts. `affected_state` is:
  - `within_retention`, when the count is reliable for the retained window;
  - `partial`, when events were refused or receipts expired;
  - `unknown`, for an owner-free server-only incident.
- **Filter:** `InboxRequest` gains an optional `platform`, applied to `diagnostic` only. Search matches code substrings only.

**UI.** The existing Inbox list and drawer render the fields with UZ/RU/TJ catalog text. No new button type (`BROWSER_UI_CONTRACT.md`).
- **"Fixed" button (owner request 2026-11-13).** An unresolved incident's drawer shows the existing Android-report primary button "Тузатилди ✅" / "Исправлено ✅" / "Ислоҳ шуд ✅" (`fixLabels.fixed` in `app.js`). For incidents it sends the plain `resolve` operation, so no learner notice is sent. A resolved incident shows the same text as its status, as Android reports do.
- **"Error came back" notice.** An auto-reopened incident shows one line in the list and drawer, with the time and version of the new occurrence:
  - UZ: "🔁 Тузатилган хато яна такрорланди"
  - RU: "🔁 Исправленная ошибка повторилась"
  - TJ: "🔁 Хатои ислоҳшуда боз такрор шуд"

  The text lives in the Admin catalog for all three languages.

**Triage.**
- Mapping: New = `new`, Investigating = `assigned` (existing `assign_self`), Resolved = `resolved` (the "Fixed" button).
- On resolve, the hook stores `resolved_version = last_version` in the same transaction. `resolve_fixed` stays Android-report only, because it notifies a learner.
- Automatic reopen (in `ingest`): when an incident is resolved and a new receipt arrives with a version ≥ `resolved_version` (any version for `server`), the triage moves as the existing `reopen` does. It writes a revision and an audit row with a null actor, and sets the "came back" notice.
- Version order: Android `versionCode`, PWA token date, backend none.

### D7. Bounded push through the existing outbox
- **Allowlists.** `enqueue_automatic_alert` and `_PUSH_SOURCES` accept `diagnostic`. The event key adds `alert_epoch` (`…:diagnostic:{id}:{epoch}`), so client retries never re-alert while reopen and escalation can.
- **When an alert is queued.** Inside `ingest`, in a savepoint that never fails intake, an alert is queued only for one of three cases:
  - a new `critical` incident;
  - a scope escalation: a `high` incident that reaches ≥ 5 distinct accounts in 1 h becomes `critical`, a bounded indexed count;
  - the reopen of any incident the admin marked fixed, at any severity (owner request 2026-11-13). A fixed error that comes back always alerts.

  Further conditions:
  - a 6 h per-incident cooldown;
  - a global cap of 6 distinct diagnostic alerts per hour, counted by `event_key` in the outbox under an advisory lock on a constant key;
  - a reopen alert is exempt from the cooldown and the cap. Each reopen needs a human "Fixed" first, so its rate is bounded, and the epoch key gives one alert per reopen.
- **Dispatcher.** `_relevant` treats a resolved or purged incident as obsolete.
- **Service worker.** `sw.js` gets two fixed `diagnostic` labels, chosen by a fixed `kind` (`new` or `reopened`; reopened uses the "came back" text). It also gets an allowlisted per-source link, `/admin/?inbox=diagnostic`, which the Admin app applies after authentication. The payload still carries no incident detail. iPhone web push has no action buttons, so "Fixed" stays in the authenticated drawer and never goes into the notification.
- **Unchanged:** payment, Android-report, bot and release payloads. The cap protects them from a diagnostic flood.
- **Telegram admin alerts are a separate channel.** Lava `admin_alert` messages keep their codes, throttle and recipients. Diagnostic alert decisions never read, wait for or cancel them, and the reverse also holds.

### D8. Retention and deletion
- **Hourly loop.** Next to `purge_expired_native_reports`, it deletes receipts older than 30 days and resolved incidents unseen for 180 days, together with their triage rows. Both use bounded batches (≤ 1000). Audit rows stay; they hold no telemetry.
- **Account deletion.** Account deletion cascades the receipts through the FK, in the existing deletion transaction; incidents keep aggregates only.
- **Blocked or revoked accounts.** The existing transports refuse them. A 401/403 makes the client drop that owner's queue.

### D9. Mini App compatibility: additive adapter
**Owner decision (2026-11-13): option A.** Fixing errors comes first, so no Mini App alert is removed. The adapter only adds the diagnostic incident. The `technical` Inbox item and its per-error push stay exactly as today. Example: 30 onboarding save errors in a day give 30 `technical` pushes as today, plus one grouped incident card, with its own push under D7.

**Switch.** One boolean setting, `MONITORING_MINIAPP_ADAPTER`, separate from the mode; default off. The adapter acts only on events the current `MONITORING_MODE` admits.

In the `app_error` branch of `/api/miniapp/event`:
- **`schema:"diag.v1"` events from the shared script.** They are new signals, so they go to `ingest` only. No `messages` row is written, so no new rows reach the AI context.
- **Legacy onboarding `app_error`.**
  - It still writes its `messages` row and still enqueues its per-row `technical` push. Bot AI context, `bot_block_cause_service`, the experiments count and the `technical` listing are unchanged.
  - It is also mapped to the onboarding failure codes, mirroring `_technical_explanation_code`, and sent to `ingest`. A recovered variant only lowers severity.
- **Rollback.** Turning the adapter off stops only the incident writes. The `technical` path never changed, so nothing needs restoring.
- **`clog`.** Its known audio/mic events are mapped into `HskDiag.report`. `/api/v3/clientlog` is left untouched.

### D10. Coverage registry and CI: one registry, one checker, one workflow
**Registry.** `FEATURE_ANALYTICS_COVERAGE.json` gains `monitoring`:
- `mode`: `declare` | `require_covered`;
- `features[]`, with the `id` (the Analytics flow ID or a catalog monitoring-only ID) and, per platform (`android`, `iphone_pwa`, `telegram`, `server`):
  - status `covered` / `partial` / `not_instrumented` / `not_applicable` and a `reason`;
  - `reporter` path, `client_test` and `chain_test`;
- `android_packages` and `pwa_pages`, each mapped to features;
- `legacy_baseline` (`feature:platform` pairs);
- `exemptions`, exact and with a reason.

**Checker.** `check_analytics_coverage.py` gains monitoring checks in the same run:
1. **Schema.** IDs must match the Analytics flow IDs or the catalog's monitoring-only IDs; no duplicates.
2. **Source inventory** (AST and regex, stdlib only):
   - learner routes, which are every decorated route except `/api/admin*`, `/admin*` and the frozen Desktop prefixes `/api/v3/desktop*`;
   - Android `feature/*` packages;
   - `app/static/course-v3.html`, `course_v3_*.html`, `iphone-pwa-*.html` and `subscription.html`;
   - reporter code literals (the Kotlin catalog enum and `HskDiag.report(` calls).

   Every route must be in the catalog `route_map`, every package and page must be mapped, and every literal must exist in the catalog.
3. **`covered` evidence.** The chain test exists, runs in `analytics-integrity.yml`, and contains the platform's intake route literal, `/api/admin/v1/inbox/list` and the feature ID with a catalog failure code. The client test exists and is run by CI: `android-ci.yml` `test*UnitTest`, or a node/Playwright step in the workflow.
4. **Diff rules** (reusing the push/PR base resolution):
   - In `require_covered` mode, a new route, package or page must map to a feature that is `covered` or `not_applicable` on its platform.
   - In `declare` mode, `partial` is also allowed, with a pending-consumer reason.
   - The baseline may only shrink, and a lowered status needs an exemption.
5. **Mode tie.** If `pwa_inbox.py` declares the `diagnostic` source, the mode must be `require_covered`.

**Workflow.** `analytics-integrity.yml` runs the same checker step, adds the monitoring test modules to its pytest list, and adds one node step for the JS reporter test. The workflow keeps its name and file, so no required check changes.

**Agent rule.** `AGENTS.md` gets a "Permanent error monitoring coverage" rule next to the Analytics rule. A change's completion note states both `Analytics Impact:` and `Monitoring Impact:`.

- *Why:* the owner asked for no duplicate CI or registry, and the Analytics design (D1) reserved "its own registry section" for Monitoring.
- *Alternative rejected:* a separate registry, checker and workflow. That would be two inventories of the same routes and flows.

### D11. Analytics boundary
- The checker asserts two things: monitoring modules never call the Analytics writers (`record_client_event`, `record_server_event`, conversion `record*`), and catalog codes never appear as analytics event names.
- **Report freshness.** It gains a `diagnostics` family: the latest receipt time per platform. Its `report.platform_freshness` registry entry and the golden test pin the new shape; other Analytics values stay unchanged.
- **Data loss.** A silent reporter shows as a stale freshness row. Refused or dropped events show as `partial` incidents and `monitoring` self-incidents, never as zero.

## Risks / Trade-offs

- [Coarse grouping without stacks] → Fixed categories plus feature and site codes. The Admin view states that root cause needs investigation. The Play/Direct channel and versions narrow it down.
- [Receipt volume] → Per-account cap, client coalescing, 30-day bounded purge and covering indexes. An `EXPLAIN` on a 1M-receipt fixture before rollout.
- [Advisory locks on SQLite tests] → Concurrency and cap tests run on PostgreSQL only, in a fresh DB per module.
- [False reopen from old app versions] → Version-aware reopen; backend reopens on any occurrence.
- [Push fatigue or starvation of payment alerts] → Critical-only, epoch keys, cooldown and global cap, with a test that payment alerts still dispatch during a flood.
- [One Lava failure alerts twice: Telegram and Inbox/Push] → Intended by the owner (2026-11-13). The incident groups repeats, and its push is critical-only. Neither channel suppresses the other.
- [Voice V8 changes the `live_*` codes] → The allowlist is re-checked in task 1.1, and the unknown-reporter-literal CI check fails on an unlisted code.
- [Route-map maintenance cost] → The baseline is generated once (task 1.2) and reviewed; each later route adds one line. CI names exactly the missing route.
- [Bypass by mapping a new route to an existing covered feature] → Its 5xx is still captured by the backend reporter for that feature. New screens and pages are caught separately, and review sees the mapping in the diff.
- [Mini App behavior drift] → None by design. Legacy rows, AI context, the `technical` listing and its per-error push are unchanged. The adapter only adds incidents.
- [More pushes for one Mini App error] → Accepted by the owner (option A, 2026-11-13). Per-error `technical` pushes stay, and the grouped incident adds at most one push per D7 case.
- [R8 strips the Android DTOs] → Keep rules plus a release-build smoke on the Direct flavour (instrumentation runs there only).
- [Reporter slows the PWA] → Deferred script, no work before first paint, idle flush. The existing performance-contract browser tests must stay green.

## Migration Plan

1. **Prerequisite.** Analytics registry, checker and workflow (PR #285) on `main`, or stack on that branch.
2. **Order** (`tasks.md`):
   1. foundation: catalog, registry block in `declare` mode, rule, migration, intake, backend reporter;
   2. Android and PWA reporters;
   3. Inbox and Push, which flips to `require_covered`;
   4. Mini App adapter;
   5. validation, staged rollout and the joint Analytics/Monitoring audit.
3. **Deploy.** The migration deploys alone (additive). All switches stay off. Then:
   1. staging;
   2. `MONITORING_MODE=owners` on production, with owner devices;
   3. diagnostic push on;
   4. Mini App adapter on;
   5. `all`.
4. **Rollback.**
   - `MONITORING_MODE=off` stops all writes, and clients pause.
   - The push switch and the adapter switch revert on their own.
   - The client reporters stay inert once paused.
   - The migration downgrade needs archived diagnostic triage and outbox rows.
   - None of this touches payments, access, grading or existing pushes.
5. **Promotion.** Under the `AGENTS.md` Git rules, with owner approval. CI, staging and device acceptance are recorded separately.

## Open Questions

- **Legacy `messages` app-error text.** Sanitizing the stack and URL in the legacy row changes the bot's AI context. The owner decides after acceptance; Monitoring never reads that text.
- **`/api/v3/clientlog`.** Its retirement or sanitization comes after the reporters cover the audio/mic events. The owner decides.
- **Numeric defaults.** Cap, cooldown, thresholds and retention are catalog constants and can be tuned after the owners stage without spec changes.
