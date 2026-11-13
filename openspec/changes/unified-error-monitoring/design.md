# Design

## Context

Motivation is in `proposal.md`, requirements in `specs/`.

**Audit history:**
- **2026-11-12.** First audited on `feat/analytics-android-lesson-start-20261112`.
- **2026-11-13.** Re-audited on `origin/main` `5ea7c22f`. That main contains Analytics Integrity (PR #285) and next-stage R1–R4 (PR #307, migration `0155`).
  - Monitored files changed since the first audit only in two places: two `client="telegram"` tags in `app/main.py`, and Pro copy plus asset tokens in `course-v3.html`.
  - A read-only Graphify pass (AGENTS.md Graphify rule) traced the dependencies below. Each lead was verified in code. The graph predates the merge, so Analytics files were read directly.

### Existing failure signals

| Signal | Code | Storage / consumer | Gap against the requirements |
|---|---|---|---|
| Mini App `app_error` | `course_v3_onboarding.html` `reportOnboardingSaveError` → `/api/miniapp/event` (`app/main.py`, verified `initData`) → `AppErrorContextService.record_miniapp_error` | Row in `messages`, `content_type='app_error_context'`. It stores raw message, stack, URL and extra. Consumers: bot AI context (`bot/handlers/messages.py`), Inbox `technical` (fixed `CASE` codes only), triage and push eligibility, `bot_block_cause_service`, the Analytics experiments count (`pwa_analytics_experiments.py`), and per-user error counts in `admin_miniapp_service.py`. Each row enqueues `enqueue_automatic_alert(source='technical')` | Onboarding only; no grouping; one push per row; raw text stored (pre-existing) |
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
  - `InboxRequest` already filters by source, priority and status. The minimal Admin app always sends `all` and has no filter controls.
  - `app.js` hard-codes the five sources (row rendering, icon and label, the `data-inbox-open` regex, `autoImportantSources`). Its deep-link handler accepts only `?inbox=1`.
  - Admin strings come from `localization/ui/{uz,ru,tj}/miniapp.json`, generated into `app/static/admin-pwa/catalog.js`. The Android fix labels are the older inline `fixLabels`.
- **Triage:** `pwa_inbox_triage.py`.
  - Store: `admin_pwa_inbox_triage` (PK `source`, `source_id` int), statuses `new` / `read` / `assigned` / `resolved`.
  - Operations include `reopen`, with revision CAS and an audit table whose `actor_user_id` is nullable.
  - The Admin app has no `assign_self` control. Opening an item's drawer sends an audited `mark_read`, so `read` is the visible "being looked at" state.
- **Push:**
  - `pwa_push_outbox.enqueue_automatic_alert` accepts only `payment`, `android` and `technical`, with the key `automatic-important-v1:{source}:{id}`. Its callers are native reports, payment receipts and Mini App errors.
  - `admin_pwa_push_dispatch` adds lease, retries and a 30 s per-device cooldown. `_webpush` always sends `{"kind":"important","source":…}`. `_relevant` has one eligibility branch per source.
  - `sw.js` accepts only `kind === "important"`. It has fixed Uzbek-Latin per-source labels (the surface's only language) and a fixed `/admin/?inbox=1` link.
- **Source CHECK constraints** on outbox, triage and audit; migration `0127` extended them for `technical`.
- **Analytics on `main`** (Monitoring reuses it):
  - **Registry** `FEATURE_ANALYTICS_COVERAGE.json` (version 1):
    - `metrics` (120), `flows` (20 IDs), `critical_paths` (29) and `exemptions`;
    - the platform keys `android`, `telegram`, `iphone_pwa`, `macos`, `windows`.
    - `validate_schema` rejects unknown top-level keys, and every Analytics platform cell must list all five keys.
  - **Checker** `scripts/check_analytics_coverage.py` (stdlib, `push` / `pull_request` diff modes):
    - `validate_chain` proves `covered` statically. The test must exist, its module must be listed in the workflow (`ci_test_modules`), and it must contain the Admin route, platform and subject literals.
    - Its Admin route is fixed to `/api/admin/v1/analytics`.
  - **Workflow** `analytics-integrity.yml`: a PostgreSQL service, the checker step, then one explicit pytest module list.
  - **Node tests** run as plain `node tests/<name>.js` steps (`backend-ci.yml`, `pwa-shake-report-guard.yml`).
  - **Report freshness** `pwa_analytics_freshness.platform_freshness` returns `{platform, source: learning|payments, latest_at, unresolved_owners}` for `android`, `telegram` and `iphone_pwa`.
    - It is computed inside the 24 h Analytics snapshot (`pwa_analytics_cache.py`).
    - `tests/test_admin_pwa_report_freshness.py` pins the shape.
  - **Open Analytics tasks** are only owner device acceptance and promotion notes. The `hsk-ai-analytics-integrity` change is not archived yet.
- **Transports:**
  - Android bearer: `DesktopAuthService.authenticate`, `device.platform == 'android'`, as in `android_events.py`;
  - PWA: cookie + CSRF + same origin, `PwaAuthService.mutation_actor`. The client knows its owner through `X-HSK-PWA-User-ID` / `PWA_COURSE_USER_ID`;
  - Mini App: verified `initData` in `/api/miniapp/event`.
- **Housekeeping:** `_desktop_auth_retention_scheduler` in `app/main.py`, started by `lifespan`, runs hourly and already purges native reports in bounded batches. "Hourly loop" below means this function.
- **Rollout switches** are booleans in `app/config.py`, set by environment, like `ADMIN_PWA_PUSH_ENABLED` and `PWA_VOICE_LIVE_ENABLED`. On Railway a variable change redeploys the service, which briefly interrupts traffic.
- **Android:**
  - `DISTRIBUTION_CHANNEL` build field (`play` / `direct`);
  - an AtomicFile outbox pattern (`assistant-outbox`) and WorkManager;
  - R8 strips `@Serializable` models in release builds unless they are kept;
  - `core/network/ApiResult.kt`: `apiCall` is the single failure classifier. `toApiError()` reads the error body once, and `ApiError` keeps no HTTP status.
- **Learner PWA:**
  - `course-v3.html` serves both the Mini App and the PWA (`PWA_COURSE_HOST`), plus `course_v3_*.html` practice pages (including the LI guest onboarding page `course_v3_li_onboarding.html`), `subscription.html` checkout and `iphone-pwa-voice.html`;
  - the service worker serves `?v=`-pinned assets Cache First. `iphone-pwa-sw.js` warms at most 40 `?v=` assets per page (`WARM_MAX_ASSETS_PER_PAGE`); `course-v3.html` references 33 today.

### Scope

- The migration head is `0155` (Analytics R3). Monitoring takes the next free number when it is written.
- **Routes.** There are about 549 route decorators:
  - 89 `/api/v3/android/*`, 74 `/api/v3/pwa/*`, 23 `/api/miniapp/*` and 53 other `/api/v3/*`;
  - 34 Desktop routes (frozen), plus Admin, public and static pages.
  - Admin routes are written with full paths. Only `android_assistant.py` uses `APIRouter(prefix=…)`, and three routes are added with `add_api_route`.
- **Android feature packages:** `ad`, `assistant`, `auth`, `course`, `dictionary`, `feedback`, `foundation`, `hint`, `lesson`, `limit`, `offline`, `onboarding`, `practice`, `profile`, `rating`, `update`, `voice`.
- **Learner pages:** `course-v3.html`, nine `course_v3_*.html`, three `iphone-pwa-*.html` and `subscription.html`.
- **Privacy.** `/privacy` (English only) lists "error details or screenshots you voluntarily send", but not automatic error reports. `docs/GOOGLE_PLAY_RELEASE_AUDIT_2026-10-22.md` still has the Play Data safety filing open.

### Dependency and regression map (Graphify, verified)

| Touch point | Depends on it today | Must stay green |
|---|---|---|
| `enqueue_automatic_alert` | `reserve_native_report`, `payment_service._queue_receipt_alert`, `record_miniapp_error` | `test_admin_pwa_push_outbox.py`, `test_admin_pwa_push_dispatch.py` (payment priority, one event per Apple install) |
| `_webpush` / `_relevant` / `sw.js` | every Admin push | the same, plus `test_admin_pwa_shell.py` (`/admin/sw.js`) |
| `platform_freshness` | the Analytics snapshot `_legacy_projection` | `test_admin_pwa_report_freshness.py`, `test_admin_pwa_v10_regression.py` |
| `validate_schema` / `validate_chain` | the Analytics CI step | `test_analytics_coverage_contract.py` |
| `app_error_context` rows | seven readers (Context table) | the Telegram tests in task 4.1 |
| `_desktop_auth_retention_scheduler` | native-report and desktop-auth purge | `test_admin_pwa_native_reports.py`, `test_admin_pwa_retention_links.py` |
| Pure ASGI middleware | `BlockedUserApiMiddleware` answers blocked users with 403 before routes run | `test_account_deletion_api.py` |

**No duplicate component found.** Existing error paths each serve a different consumer and stay:
- Mini App `app_error`;
- `clientlog`;
- manual Android and PWA reports;
- Lava Telegram alerts.

Monitoring reuses the Inbox, triage, outbox, dispatcher, scheduler, registry, checker and workflow. It adds only the catalog, two tables, intake and reporters.

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
- New filter controls in the minimal Inbox. Filters stay in the API, and the diagnostic view opens from the push link (D6).
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
  - `alert_epoch`, `last_alerted_at`, and `last_alert_reason` (`new` / `escalated` / `reopened`, which selects the push label, D7).
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
- request body ≤ 16 KB, checked from `Content-Length` and a capped read before JSON parsing, and ≤ 20 events;
- `event_id` is a UUID;
- version regex ≤ 40 characters;
- client-time skew ±7 days.

**Mode:** `MONITORING_MODE=off|owners|all`.
- It lives in `app/config.py` like the other rollout switches, so a change redeploys. The switch is for sustained problems; the per-account cap, the backend semaphore and the client caps bound bursts without a redeploy.
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
- **Live voice.** `LiveVoiceSocket` does not use `apiCall`. Its `fail(reason)` reports to `voice` only for a fixed allowlist of client-side reasons: `live_connection_lost`, `live_message_invalid`, `live_message_too_large`, `live_send_failed`. Server-sent codes (limits, quota), learner close and backpressure are not reported. The reason becomes a site code, never free text, audio or transcript. Voice V8 work is not on `main` yet (its remote branch still points at `680761f1`) and may change these codes, so task 1.1 re-checks them.
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
  - `HskDiag.report(feature, failure, site, outcome)` reports load, save and restore failures at existing call sites, after their own retry. The V1 call sites match the Android priority flows: sign-in and session restore, onboarding, lesson open and complete, practice, progress save, checkout and payment return, and the PWA → Android handoff.
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
- **Filter:** `InboxRequest.source` gains `diagnostic`, and an optional `platform` applies to `diagnostic` only. Search matches code substrings only.

**UI** (task 3.1 loads the `hsk-ai-ui` skill and follows `BROWSER_UI_CONTRACT.md`). The existing Inbox list and drawer render incidents. No new button type, badge style, color, asset or filter control.
- **List row.** The existing row layout. The title is the localized failure explanation. One secondary line shows platform · feature · "×N" · last seen. `critical` and `high` get the existing important styling from the server `priority`, and an existing sprite icon marks the source.
- **Drawer.** The explanation, then a short facts list in the drawer's existing text style: platform and channel, feature, first → last version, first and last seen, occurrences and affected accounts. A `partial` count reads "at least N" and an `unknown` one reads "unknown".
- **"Fixed" button (owner request 2026-11-13).** An unresolved incident's drawer has one primary action, the existing Android-report button "Тузатилди ✅" / "Исправлено ✅" / "Ислоҳ шуд ✅" (`fixLabels.fixed`). It sends plain `resolve` on one tap. There is no confirmation prompt (no learner is notified) and no second "new version" button; server success shows the existing animated checkmark. A resolved incident shows the same text as its status, as Android reports do.
- **"Error came back" notice.** An auto-reopened incident shows one line in the list and drawer, in the existing secondary text style, with the time and version of the new occurrence:
  - UZ: "🔁 Тузатилган хато яна такрорланди"
  - RU: "🔁 Исправленная ошибка повторилась"
  - TJ: "🔁 Хатои ислоҳшуда боз такрор шуд"
- **Diagnostic view.** `?inbox=diagnostic` opens the Inbox with `source=diagnostic`; leaving it uses the existing navigation.
- **Strings.** All new text goes to `localization/ui/{uz,ru,tj}/miniapp.json` and is generated with `i18n_build_all_catalogs.py --write` and `--check`. No new inline dictionary.

**Triage.**
- Mapping: New = `new`. Investigating = `read`, set by the audited `mark_read` when an admin opens the drawer; an API `assign_self` (`assigned`) also counts, and no control is added. Resolved = `resolved` (the "Fixed" button).
- On resolve, the hook stores `resolved_version = last_version` in the same transaction. `resolve_fixed` stays Android-report only, because it notifies a learner.
- Automatic reopen (in `ingest`): when an incident is resolved and a new receipt arrives with a version ≥ `resolved_version` (any version for `server`), the triage moves as the existing `reopen` does. It writes a revision and an audit row with a null actor, and sets the "came back" notice.
- Version order: Android `versionCode`, PWA token date, backend none.

### D7. Bounded push through the existing outbox
- **Switch.** `MONITORING_PUSH_ENABLED`, default off, is read in the alert decision. The existing `ADMIN_PWA_PUSH_ENABLED` still gates every push.
- **Allowlists.** `enqueue_automatic_alert` and `_PUSH_SOURCES` accept `diagnostic`. The event key adds `alert_epoch` (`…:diagnostic:{id}:{epoch}`), so client retries never re-alert while reopen and escalation can.
- **When an alert is queued.** Inside `ingest`, in a savepoint that never fails intake, an alert is queued only for one of three cases:
  - a new `critical` incident;
  - a scope escalation: a `high` incident that reaches ≥ 5 distinct accounts in 1 h becomes `critical`, a bounded indexed count;
  - the reopen of any incident the admin marked fixed, at any severity (owner request 2026-11-13). A fixed error that comes back always alerts.

  Owner confirmed (2026-11-13, option B): a new non-critical Android, PWA or backend incident stays in the Inbox without a push. Do not widen the new-incident push without a new owner decision.

  Further conditions:
  - a 6 h per-incident cooldown;
  - a global cap of 6 distinct diagnostic alerts per hour, counted by `event_key` in the outbox under an advisory lock on a constant key;
  - a reopen alert is exempt from the cooldown and the cap. Each reopen needs a human "Fixed" first, so its rate is bounded, and the epoch key gives one alert per reopen.
- **Dispatcher.**
  - `_relevant` gains a `diagnostic` branch: the incident exists and its triage is not `resolved`. Priority is not required, so a `normal` reopen is still sent.
  - `_webpush` keeps `kind: "important"` for every source. It sends `kind: "reopened"` only for `diagnostic` when `last_alert_reason = reopened`.
  - The payload stays two fixed enum fields.
- **Service worker.**
  - `sw.js` accepts `reopened` only together with `source: "diagnostic"`.
  - It gets two fixed Uzbek-Latin labels, following the existing ones:
    - `diagnostic`: "🛠 Avtomatik xatolik" / "Muhim xatolik qayd etildi.";
    - reopened: "🔁 Tuzatilgan xato yana takrorlandi" / "Tuzatilgan deb belgilangan xatolik qaytdi."
  - It gets an allowlisted per-source link, `/admin/?inbox=diagnostic`, which the Admin app applies after authentication. Other sources keep `/admin/?inbox=1`.
  - The payload carries no incident detail. iPhone web push has no action buttons, so "Fixed" stays in the authenticated drawer and never goes into the notification.
- **Unchanged:** payment, Android-report, bot and release payloads, and Lava Telegram alerts (D4). The cap protects them from a diagnostic flood.

### D8. Retention and deletion
- **Hourly loop.** In `_desktop_auth_retention_scheduler`, next to `purge_expired_native_reports` and in its own `try`, so one failure never skips the other. It deletes receipts older than 30 days and resolved incidents unseen for 180 days, together with their triage rows. Both use bounded batches (≤ 1000). Audit rows stay; they hold no telemetry.
- **Account deletion.** Account deletion cascades the receipts through the FK, in the existing deletion transaction; incidents keep aggregates only.
- **Blocked or revoked accounts.** The existing transports refuse them. A 401/403 makes the client drop that owner's queue.

### D9. Mini App compatibility: additive adapter
**Owner decision (2026-11-13): option A.** Fixing errors comes first, so no Mini App alert is removed. The adapter only adds the diagnostic incident. The `technical` Inbox item and its per-error push stay exactly as today. Example: 30 onboarding save errors in a day give 30 `technical` pushes as today, plus one grouped incident card, with its own push under D7.

**Switch.** One boolean setting, `MONITORING_MINIAPP_ADAPTER_ENABLED`, separate from the mode; default off. The adapter acts only on events the current `MONITORING_MODE` admits.

In the `app_error` branch of `/api/miniapp/event`:
- **`schema:"diag.v1"` events from the shared script.** They are new signals, so they go to `ingest` only. No `messages` row is written, so no new rows reach the AI context.
- **Legacy onboarding `app_error`.**
  - It still writes its `messages` row and still enqueues its per-row `technical` push. Bot AI context, `bot_block_cause_service`, the experiments count and the `technical` listing are unchanged.
  - It is also mapped to the onboarding failure codes, mirroring `_technical_explanation_code`, and sent to `ingest`. A recovered variant only lowers severity.
- **Rollback.** Turning the adapter off stops only the incident writes. The `technical` path never changed, so nothing needs restoring.
- **`clog`.** Its known audio/mic events are mapped into `HskDiag.report`. `/api/v3/clientlog` is left untouched.

### D10. Coverage registry and CI: one registry, one checker, one workflow
**Registry.** `FEATURE_ANALYTICS_COVERAGE.json` gains an optional top-level `monitoring` key. `validate_schema` accepts it, and the version stays 1. The block holds:
- `mode`: `declare` | `require_covered`;
- `features[]`, with the `id` (the Analytics flow ID or a catalog monitoring-only ID) and, per platform (`android`, `iphone_pwa`, `telegram`, `server`). Unlike Analytics cells, Desktop keys are absent because of the freeze:
  - status `covered` / `partial` / `not_instrumented` / `not_applicable` and a `reason`;
  - `reporter` path, `client_test` and `chain_test`;
- `android_packages` and `pwa_pages`, each mapped to features;
- `legacy_baseline` (`feature:platform` pairs);
- `exemptions`, exact and with a reason.

**Checker.** `check_analytics_coverage.py` gains monitoring checks in the same run:
1. **Schema.** IDs must match the Analytics flow IDs or the catalog's monitoring-only IDs; no duplicates.
2. **Source inventory** (AST and regex, stdlib only):
   - learner routes, which are every `/api/*` route except `/api/admin*` and the frozen `/api/v3/desktop*`. The checker resolves `APIRouter(prefix=…)` and `add_api_route`. Static and public HTML routes are out of scope; pages are covered below;
   - Android `feature/*` packages;
   - `app/static/course-v3.html`, `course_v3_*.html`, `iphone-pwa-*.html` and `subscription.html`;
   - reporter code literals (the Kotlin catalog enum and `HskDiag.report(` calls).

   Every route must be in the catalog `route_map`, every package and page must be mapped, and every literal must exist in the catalog. When a route's file is an Analytics `critical_paths` entry, its feature must be one of that path's flows or a monitoring-only ID, so the two mappings cannot drift apart.
3. **`covered` evidence.** It reuses `validate_chain` and `ci_test_modules`, with the Admin route as a parameter:
   - Analytics keeps `/api/admin/v1/analytics`; Monitoring passes `/api/admin/v1/inbox/list`.
   - The chain test must also contain the platform's intake route literal, and the feature ID with a catalog failure code.
   - The client test must exist and be run by CI: `android-ci.yml` `test*UnitTest`, or a `node tests/…js` step in the workflow.
   - **Runtime proof.** Chain tests call one shared helper, `tests/monitoring_chain.py::assert_monitoring_chain(platform, feature, failure)`, which drives the real intake, PostgreSQL and the Inbox read. After a passing chain it appends that triple to the file named by `MONITORING_CHAIN_PROOF`. A second checker step after pytest (`--chain-proof`) fails when a `covered` entry has no proof row. A skipped, mocked or literal-only test therefore cannot make an entry `covered`.
4. **Diff rules** (reusing the push/PR base resolution):
   - In `require_covered` mode, a new route, package or page must map to a feature that is `covered` or `not_applicable` on its platform.
   - In `declare` mode, `partial` is also allowed, with a pending-consumer reason.
   - The baseline may only shrink, and a lowered status needs an exemption.
5. **Mode tie.** If `pwa_inbox.py` declares the `diagnostic` source, the mode must be `require_covered`.

**Workflow.** `analytics-integrity.yml` changes in four ways, and keeps its name and file, so no required check changes:
- the same checker step runs;
- the monitoring test modules join its pytest list, which runs with `MONITORING_CHAIN_PROOF` set;
- the checker runs again after pytest with `--chain-proof`;
- one `node tests/test_hsk_diagnostics.js` step runs the JS reporter test. The runner image already has `node`, as `backend-ci.yml` relies on.

**Agent rule.** `AGENTS.md` gets a "Permanent error monitoring coverage" rule next to the Analytics rule. A change's completion note states both `Analytics Impact:` and `Monitoring Impact:`.

- *Why:* the owner asked for no duplicate CI or registry, and the Analytics design (D1) reserved "its own registry section" for Monitoring.
- *Alternative rejected:* a separate registry, checker and workflow. That would be two inventories of the same routes and flows.

### D11. Analytics boundary
- The checker asserts two things: monitoring modules never call the Analytics writers (`record_client_event`, `record_server_event`, conversion `record*`), and catalog codes never appear as analytics event names.
- **Report freshness.** `platform_freshness` gains a third source, `diagnostics`, for `android`, `telegram` and `iphone_pwa`.
  - `latest_at` is the newest client receipt, owner-bound, through its incident's platform.
  - `unresolved_owners` is 0 by construction, because intake needs a verified owner. Server-only receipts are excluded.
  - It is served through the 24 h Analytics snapshot, so it detects a reporter silent for a day, not for minutes.
  - The existing "Per-platform source freshness" requirement already covers a new source. Its registry entry and `test_admin_pwa_report_freshness.py` pin the shape; other Analytics values stay unchanged.
- **Mini App counts.** With the additive adapter (D9), `app_error_context` rows are still written once per error. The experiments count and `admin_miniapp_service` counts therefore stay the same, and receipts are never added to them.
- **Data loss.** A silent reporter shows as a stale freshness row. Refused or dropped events show as `partial` incidents and `monitoring` self-incidents, never as zero.

## Risks / Trade-offs

- [Coarse grouping without stacks] → Fixed categories plus feature and site codes. The Admin view states that root cause needs investigation. The Play/Direct channel and versions narrow it down.
- [Receipt volume] → Per-account cap, client coalescing, 30-day bounded purge and covering indexes. An `EXPLAIN` on a 1M-receipt fixture before rollout.
- [Advisory locks on SQLite tests] → Concurrency and cap tests run on PostgreSQL only, in a fresh DB per module.
- [False reopen from old app versions] → Version-aware reopen; backend reopens on any occurrence.
- [Push fatigue or starvation of payment alerts] → New incidents push only when critical, and a reopen pushes once after each human "Fixed". Epoch keys, the cooldown and the global cap apply, with a test that payment alerts still dispatch during a flood.
- [One Lava failure alerts twice: Telegram and Inbox/Push] → Intended by the owner (2026-11-13). The incident groups repeats and pushes only when critical or when it comes back after "Fixed". Neither channel suppresses the other.
- [Voice V8 changes the `live_*` codes] → The allowlist is re-checked in task 1.1, and the unknown-reporter-literal CI check fails on an unlisted code.
- [Route-map maintenance cost] → The baseline is generated once (task 1.1) and reviewed; each later route adds one line. CI names exactly the missing route.
- [A skipped or faked chain test passes CI] → The runtime proof (D10): `covered` needs a proof row that the shared helper wrote in the same CI run.
- [Bypass by mapping a new route to an existing covered feature] → Its 5xx is still captured by the backend reporter for that feature. New screens and pages are caught separately, and review sees the mapping in the diff.
- [Mini App drift or extra pushes] → No drift by design: legacy rows, AI context, the `technical` listing and its per-error push are unchanged. The grouped incident adds at most one push per D7 case, which the owner accepted (option A, 2026-11-13).
- [R8 strips the Android DTOs] → Keep rules plus a release-build smoke on the Direct flavour (instrumentation runs there only).
- [Reporter slows the PWA] → Deferred script, no work before first paint, idle flush. The existing performance-contract browser tests must stay green.
- [Extending the Analytics checker breaks Analytics CI] → `monitoring` is optional in `validate_schema`, and `validate_chain` keeps its default route. `test_analytics_coverage_contract.py` must pass unchanged before the monitoring tests are added.
- [Freshness adds work to the daily Analytics snapshot] → One indexed `max(received_at)` per platform over retained receipts. The snapshot tests stay green.
- [The kill switch needs a redeploy] → It follows the project's `app/config.py` switch pattern. Caps and the semaphore bound bursts without a redeploy; `off` is for sustained problems.
- [Automatic reports are not yet disclosed] → `/privacy` and the Play Data safety declaration are updated before the `all` stage (task 5.2). The `owners` stage covers admin accounts only.

## Migration Plan

1. **Prerequisite: met.** The Analytics registry, checker and workflow, plus R1–R4, are on `main` (`4a647ca5`, recorded at `5ea7c22f`). Work branches start from the current `main`.
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
   5. disclosure. `/privacy` (English-only today) states that the apps send automatic, content-free error reports: codes, app version and time, linked to the account, kept 30 days, deleted with the account and not shared. The owner files Play Data safety: App info and performance → Crash logs and Diagnostics, collected and not shared;
   6. `all`.
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
