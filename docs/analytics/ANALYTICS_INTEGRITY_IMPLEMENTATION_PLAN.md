# HSK AI — Analytics Integrity: shared context

> **This is the single shared context file for this work.** It is used by Codex, Claude and cloud agents alike.
> - Read it at session start. At session end, update "Current state", the audit table and the session log.
> - Do not create any other progress, context or handoff file for this work.
> - The checklist lives only in [`openspec/changes/hsk-ai-analytics-integrity/tasks.md`](../../openspec/changes/hsk-ai-analytics-integrity/tasks.md). Requirements live in its `specs/`, technical decisions in its `design.md`.
> - The permanent per-feature rule lives in root `AGENTS.md` ("Permanent analytics integrity and feature coverage").

## Goal

Connect the existing analytics of Android (Play/Direct), the Telegram Mini App and the iPhone PWA to the matching Admin PWA Analytics V10 sections (Overview, Course, Platforms, Funnel, Finance, Sources, Report).
- The connection must be complete and accurate, and proven by tests.
- Each platform must be viewable separately. Overall must count each canonical account once.
- Future features must not fall outside analytics: the `AGENTS.md` rule, the coverage registry and CI enforce this, and a justified `not_applicable` is allowed.

## Constraints

- Keep the existing V10 architecture. Do not build a new analytics system or duplicate working parts.
- No PostHog, no new Redis use and no other infrastructure without evidence of need. No schema change unless a reviewed task proves it necessary.
- Do not label anything a defect until real code confirms it. Unproven items stay `to_verify`.
- Do not change payment, Pro entitlement, access, grading, auth or privacy behavior. Telemetry must never block a user flow.
- A stored event or a passing unit test is not integration evidence. Only a chain test (event → API → PostgreSQL → aggregation → Admin PWA UI) is.
- macOS/Windows Desktop is under a development freeze (`AGENTS.md`). Keep its existing metrics and give it registry statuses only: no desktop code, tests or CI.
- Performance: new reads stay bounded aggregates inside the existing 24-hour snapshot. Writer changes add only a payload key to a write that already happens. See `docs/PERFORMANCE_PWA_PROGRESSIVE_LOADING.md` and `backend-pwa-performance-contract.yml`.

## Where things are

| Item | Location | Status |
|---|---|---|
| OpenSpec change | `openspec/changes/hsk-ai-analytics-integrity/` | Re-audited on `main` `680761f1`; passes `openspec validate --strict` |
| Checklist | `.../tasks.md` | Only checklist; audit, baseline and coverage guard done |
| Coverage registry | [FEATURE_ANALYTICS_COVERAGE.json](FEATURE_ANALYTICS_COVERAGE.json) | Present; schema, event inventory and projection checks pass |
| CI guard | [analytics-integrity.yml](../../.github/workflows/analytics-integrity.yml) | Verified on the scratch branch (2.3); not promoted to main |
| Agent rule | `AGENTS.md` | Active; lists the registry and check, with main enforcement verified separately |
| Admin readers | `app/admin_api/pwa_analytics*.py`, `pwa_metrics.py` | V10 emits per-metric states; values unchanged in 3.1 |
| Monitoring requirements | `docs/monitoring/REQUIREMENTS.md` | Follows this work; reuses its identifiers (§7, §11) |

## Current state — 2026-11-12

- The branch has the PostgreSQL baseline, the coverage guard and per-metric V10 states in the API and the Admin UI. It also has per-platform scoping, route chain tests, the PWA Pro funnel, `return_retention` and Report freshness.
- An independent audit of PR #285 (55 findings) confirmed 17. The code and process defects among them are fixed on this branch; see [Audit remediation](#audit-remediation--pr-285-2026-11-12). Every V10 value still matches the baseline except two Overall Finance averages, which were wrong on `main` too (#34).
- **Open: 6.2 real-client acceptance** (owner devices and a deployment of this branch; checklist below) and **6.3 promotion** (owner approval). No merge to `main` without the owner's permission.
- **Next stage (implemented, not merged):** R1, R2, R4 and R3 from [Next stage](#next-stage--mandatory-requirements-not-implemented) are implemented on `feat/analytics-next-stage-20261112`, stacked on this PR, with one OpenSpec change each. Open there: final verification on the final head, the R4 performance numbers, the owner's approval of the R3 migration, and owner acceptance on real clients.
- PR [akbarholturaev11-lang/HSK-AI-Bot#285](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/pull/285) is the integration branch for this work.

## Platform scope

| Platform | Admin filter | Role in this work |
|---|---|---|
| Android Play + Direct | `android` | Target. No Play/Direct split: the channel is not in analytics rows (audit row A19) |
| Telegram Mini App | `telegram` | Target |
| iPhone PWA | `iphone_pwa` | Target |
| macOS / Windows | `macos`, `windows` | Development freeze. Existing metrics kept; registry status only |

## Audit — task 1.1, `main` `334368cc`, 2026-11-11

**Status values:**
- `verified`: code and test cited for the exact claim; this does not imply a PostgreSQL-to-UI chain test.
- `to_verify`: code cited, test still missing. The test is added by the task named in the row.
- `gap`: verified in code that no trustworthy platform signal exists.

`course_miniapp_events` is abbreviated to CME. The default CME source is `course_miniapp` (`course_miniapp_analytics_service.py:65`).

### Activity and learning

| # | Flow / metric | Platform | Writer (code) | Platform signal | Admin reader → section | Status |
|---|---|---|---|---|---|---|
| A1 | App open | Android | `desktop_auth_service.py:1392-1420` `android_first_open` / `android_app_opened`, source `android_app` | event-name prefix | `pwa_analytics_platforms.py` → Platforms | `verified`: `test_android_analytics_service.py`, `test_admin_pwa_read.py` |
| A2 | Mini App presence | Telegram | `desktop_download.py:159` → `user_client_presence` surface `telegram_miniapp` | surface | Platforms | `verified`: `test_user_device_inventory_service.py` |
| A3 | Course map open | Telegram | `main.py:2909-2931` `miniapp_opened`, source = query `source` or `course_v3`; `main.py:5706` source `course_miniapp` | none exclusive: query text is free | Course `retention` (mixed with A4) | `gap` |
| A4 | Course map open | PWA | `/api/v3/pwa/map` (`main.py:2994`) → `main.py:2745,2921-2931` `miniapp_opened`, source `pwa_course_v3`, dedupe prefix `pwa-course-v3:` | route-owned dedupe prefix `pwa-course-v3:` (the source text is forgeable on old Telegram rows) | Platforms PWA card (DAU/WAU/MAU) under the PWA filter (3.2); counted in Course `retention` | `verified`: [platform scope test](../../tests/test_admin_pwa_platform_scope.py) excludes the Telegram `pwa_course_v3` lookalike |
| A5 | PWA sign-in device | PWA | `pwa_auth_service.py:338-352` `desktop_devices.platform='pwa'`; `last_seen_at` set only at mint | platform `pwa` | Not read by V10 | `gap` as activity: sign-in time, not use |
| A6 | Lesson started | Telegram + PWA | Legacy Telegram flow: `course_miniapp_lesson_flow_service.py:1596`. V3 emits client observations via `course-v3.html` → Telegram/PWA event routes. V3 lesson/start writes an internal authorization grant, not a second `lesson_started`. | none on the baseline | `COURSE_EVENTS`, features, activation → Overview, Course | `verified` (3.2): route-set final `client` key from `attributed_since` on; Course `features.lessons` per Telegram/PWA; [platform scope test](../../tests/test_admin_pwa_platform_scope.py) |
| A7 | Lesson started | Android | No writer. Android loads lessons by GET `/api/v3/android/course/lesson/{order}`. Readers list `android_lesson_started`, which has no writer in `app/` or `android/` | — | Counted in `COURSE_EVENTS`, never written | `gap` → `not_instrumented` |
| A8 | Lesson completed | Android | `desktop_course_service.py:727-731` `lesson_completed`, source `android_course` | source | Overview, Course completed accounts and lessons | `verified`: `test_android_course_api.py:405`; Android Course `completed_user_lessons` by source (3.2), [platform scope test](../../tests/test_admin_pwa_platform_scope.py); chain: [route → Admin API](../../tests/test_analytics_platform_chain.py) (3.4) |
| A9 | Lesson completed | Telegram + PWA | Shared `main.py:3495-3498`, source hard-coded `course_v3` | none | Overview, Course | `verified` (3.2): route-set final `client` key; Telegram/PWA `completed_user_lessons` from `attributed_since`; [platform scope test](../../tests/test_admin_pwa_platform_scope.py); chain: [route → Admin API](../../tests/test_analytics_platform_chain.py) (3.4) |
| A10 | Starter 0 / foundation | all three | Start: client telemetry `foundation_started` via the Telegram and PWA event routes, which append the route-set final `client` key (`ATTRIBUTED_CLIENT_EVENTS`). Completion: `miniapp_entitlements.py:294` (`pwa_course_v3` / `course_v3`), `android_course_service.py:394` (`android_course`) | final `client` key on the start | Course `foundation`: Telegram/PWA cohort = learners whose start is tagged for that client, from `attributed_since` on (3.2); Android `not_instrumented` (no start writer) | `verified` (3.2): [platform scope test](../../tests/test_admin_pwa_platform_scope.py); `test_pwa_learning_parity_postgres.py`, `test_android_foundation_api.py` |
| A11 | Lesson-flow telemetry | PWA | `/api/v3/pwa/event` `miniapp_entitlements.py:307-340`, source `pwa_course_v3`, payload `transport: iphone_pwa` set by the server | server-set transport on new rows only; old Telegram rows can carry a forged `transport` | Course activation, direct activation, sessions: PWA `not_instrumented` (3.2) — the cohort anchor `onboarding_completed` and most session rows carry no route-set `client` key | `verified` writer; `gap` for platform attribution (3.2) |
| A12 | Lesson-flow telemetry | Telegram | `/api/miniapp/event` `main.py:6628-6735`: client-supplied source, payload copied by `trusted_client_payload` (`course_miniapp_analytics_service.py:39-44`) | none trusted; client can send `pwa_course_v3` / `transport` | Course activation | `gap` |
| A13 | Practice training / test | Android + Telegram | `course_miniapp_practice_service.py:87,635,800,825` (default source / `smart_practice_v2`). Android routes `android_features.py:1379,1414` call the same service | none | Course `features.practice` / `tests` | `verified` (3.2): route-set final `client` key; `features.tests` / `practice` per platform from `attributed_since`; [platform scope test](../../tests/test_admin_pwa_platform_scope.py). `android_practice_*` reader names have no writer |
| A14 | HSK exam | all three | `course_hsk_exam_service.py:474,688`, source `course_hsk_exam`; routes `android_features.py:1458,1496`, `pwa_auth.py:928`, Telegram `/api/v3/exams/*` | none | Course `features.tests` | `verified` (3.2): route-set final `client` key; `features.tests` per platform; [platform scope test](../../tests/test_admin_pwa_platform_scope.py) |
| A15 | Mistake review | all three | `course_mistake_service.py:1315,1501,1705,1935`, default source; routes `android_features.py:1568-1616`, `pwa_auth.py:820` | none | Course `features.mistakes` | `verified` (3.2): route-set final `client` key; `features.mistakes` per platform; [platform scope test](../../tests/test_admin_pwa_platform_scope.py) |
| A16 | Voice minutes | all three | `voice_practice_service.py:759` `voice_practice_sessions`, no platform column. PWA voice CME rows carry `transport: iphone_pwa` | none on the session | Course `voice`, `voice_minutes` | `gap` |
| A17 | AI usage, chat | all three | `ai_usage_events.source` is the feature (`qa`, …); `messages` has no platform column | none | Course `ai`, `chat`; Finance AI cost | `gap` |
| A18 | Telegram → PWA / Play handoff | Telegram | `pwa_auth.py:2181-2239` `pwa_handoff_issued` / `_completed`; `main.py:6762` `android_play_opened` | event name | Existing basic Statistics: `pwa_read.py:120`, `android_analytics_service.py:48`. Not V10 | `verified`: `test_pwa_telegram_handoff.py`, `test_android_analytics_service.py`. Keep in the existing consumer |
| A19 | Android Play / Direct channel | Android | `android_app_opened` payload is only `platform`, `app_version`, `device_id` (`desktop_auth_service.py:1405-1420`); `desktop_devices` has no channel column | none | — | `gap` → combined Android only |
| A20 | Desktop activity | macOS, Windows | `desktop_*` events, `DesktopAnalyticsService._row_platform` | payload / source | Platforms | Existing, frozen: registry status only |

### Funnel, Finance and Sources

| # | Flow / metric | Platform | Writer (code) | Platform signal | Admin reader → section | Status |
|---|---|---|---|---|---|---|
| F1 | `checkout_opened` | PWA | `pwa_auth.py:1700-1715,1853`, payload `transport: iphone_pwa` | server-set transport | Funnel `attempt_funnel`, PWA filter (3.2) | `verified`: `test_pwa_browser_auth.py:3370`, [platform scope test](../../tests/test_admin_pwa_platform_scope.py) |
| F2 | `checkout_opened` | Android | `desktop_subscription_service.py` `_record_checkout_opened` (now payload `transport: android`); `lava_checkout.py:165` (payload `transport: android`) | server-set transport. Source and `android-` prefix are not trusted: a Telegram caller can send both | Funnel, Android filter (3.2); earlier manual rows Overall-only | `verified`: `test_android_lava_checkout.py:84`, [marker test](../../tests/test_checkout_transport_marker.py), [platform scope test](../../tests/test_admin_pwa_platform_scope.py) |
| F3 | `checkout_opened` | Telegram | `/api/subscription-miniapp/overview` and `/event` in `main.py`: source and attempt ID are caller text (`_checkout_text`, `_checkout_attempt_id`); payload now `transport: telegram` | server-set transport (3.2). Elimination rejected: a caller can forge `android_subscription` / `android-…` | Funnel, Telegram filter; earlier rows Overall-only (`attributed_since`) | `verified`: [marker test](../../tests/test_checkout_transport_marker.py), [platform scope test](../../tests/test_admin_pwa_platform_scope.py) |
| F4 | Payments (Finance, funnel paid) | all | `payments.source`: `miniapp` (`subscription_miniapp_service.py:316,416`); `iphone_pwa` (`pwa_auth.py:1912`); `android` / `desktop` (`desktop_subscription_service.py:399`); Lava copies the invoice source `miniapp` / `pwa` / `android` (`lava_checkout.py:202,248,338` → `lava/ledger.py:194`); bot default `telegram_bot` | source. PWA has two values: `iphone_pwa` and `pwa` | Finance `money_metrics` payment keys per platform (3.2); renewal order stays canonical across platforms | `verified` on stored rows: [platform scope test](../../tests/test_admin_pwa_platform_scope.py); chain test pending (3.4) |
| F5 | Lava lifecycle | all | `lava_invoices.source` `miniapp` / `pwa` / `android` | source | Finance `lava` per platform (3.2) | `verified` on stored rows: [platform scope test](../../tests/test_admin_pwa_platform_scope.py); chain test pending (3.4) |
| F6 | Subscription entries | Android | `android_features.py:1348` `android_subscription`; `ANDROID_CHECKOUT_ORIGIN_SOURCES` (`android_*`) | none trusted: the Telegram overview route stores caller `source` (`main.py` `_checkout_text` → `record_entry`, `normalize_source` keeps `android_subscription`) and the table has no platform column | Sources (`source_group` `android_%`), Overall only | `verified` writer; `gap` for platform attribution (re-checked in 3.2) |
| F7 | Subscription entries | PWA, Telegram | `pwa_auth.py:1689` `data.source or "iphone_pwa"` and `main.py:6322`, both client-supplied; `subscription_entry_events` has no payload column | none | Sources | `gap` (a fix needs a schema change: out of scope) |
| F8 | PWA Pro inline funnel | PWA | UI events via the cookie + CSRF route (`pwa_auth.py` `PwaProUiEvent`), `lava_checkout._start` `pwa_pro_checkout_started` after the invoice exists, `services/lava/ledger.py` `pwa_pro_checkout_paid` in the verified grant, `lava_invoices.pwa_inline_attempt_id` | PWA-only (no other writer of these names) | Funnel `pwa_pro_attempt_funnel` under Overall and PWA (4.1); Conversion-tab panel (4.2) | `verified`: [F8 test](../../tests/test_admin_pwa_pro_funnel.py) on stored rows; [route chain](../../tests/test_pwa_pro_funnel_chain.py) (4.2) |

### Delta audit — `334368cc..680761f1`, 2026-11-12

`git diff --exit-code 334368cc..680761f1 -- app/admin_api app/db/models alembic app/static/admin-pwa` found no reader, model, migration or Admin UI changes. No V10 key changed. The changed user actions and writer below affect what some existing metrics can observe.

| Flow / scope | Code and test evidence | Status and impact |
|---|---|---|
| Android Li guest entry (A7, activation) | [Public preview](../../app/api/android_course.py#L378) returns course metadata; [guest resume](../../app/services/android_course_service.py#L464) uses [the existing canonical completion writer](../../app/services/course_miniapp_onboarding_service.py#L384). [Preview/resume tests](../../tests/test_android_course_api.py#L1058) cover default-off metadata, one completion and no overwrite. [V10 activation](../../app/admin_api/pwa_analytics_learning.py#L106) reads `onboarding_completed`; `direct_activation` remains `direct_start_v1` only. | `verified` for public metadata and one canonical completion; `to_verify` for the new variant's V10 activation output (1.2). `gap` for pre-sign-in preview/abandonment and Android lesson starts. The variant is supplied by the client, not a general platform predicate. |
| Voice V8 (A16) | [PWA entry](../../app/static/iphone-pwa-voice.html#L399) and [Android entry](../../android/app/src/main/java/com/pomp/hskai/feature/voice/VoiceV8Screen.kt#L586) start the existing session when allowed. [PWA V8 browser tests](../../tests/e2e/test_iphone_pwa_voice_v8.py#L301), [Android UI test](../../android/app/src/androidTest/java/com/pomp/hskai/feature/voice/VoiceV8FlowTest.kt#L63) and [PWA owner test](../../tests/test_pwa_browser_auth.py#L2970) cover entry/transport, using mocked responses where applicable. [V10 Voice](../../app/admin_api/pwa_analytics_learning.py#L76) counts started session owners; minutes require completed sessions with positive turns. | `verified` for entry behavior and the existing owner contract. `to_verify` for changes to Overall participation, elapsed duration and generic CME session metrics in practice. A visit need not insert a row; the service can reuse a session. A16 remains a `gap` for per-platform minutes. Bare start/end rows cannot establish return to practice after auto-start (5.1). |
| PWA / Android pending Telegram feedback | [Server reservation](../../app/services/activity_feedback_service.py#L132) writes `app_telegram_feedback_reserved` once per existing invite. [Route tests](../../tests/test_pwa_learning_parity.py#L302) and [PostgreSQL concurrency test](../../tests/test_pwa_learning_parity_postgres.py#L94) cover continuation and one reservation. [V10 Report](../../app/admin_api/pwa_analytics_cache.py#L49) counts every CME row; [the separate feedback projection](../../app/admin_api/pwa_feedback_analytics.py#L79) counts completed feedback. | `verified` for reservation behavior; `to_verify` for its exact raw Report count/freshness output (1.2); `gap` for platform attribution. Register the internal event in group 2. Keep it in the legacy raw Report, outside new per-platform activity/freshness. It is neither an impression nor a return. |
| Learner PWA push | [Push rendering](../../app/services/learner_pwa_push.py#L540) and [reminder transport](../../app/services/smart_reminder_pwa.py#L201) reuse owned sources; [copy tests](../../tests/test_learner_pwa_push_copy.py) and [worker browser test](../../tests/e2e/test_pwa_push_worker.py) cover copy/delivery. No V10 reader consumes these delivery rows. | `verified` for reuse of source data. No new V10 metric or learner-activity event. Push delivery is outside the return signal. |
| Existing V10 filter gates | [Section composition](../../app/admin_api/pwa_analytics_cache.py#L32) checks the section before its PWA check; [analytics tests](../../tests/test_admin_pwa_analytics.py) cover projections, but not the full matrix. | `to_verify` on the complete fixture (1.2): PWA Home/Overview/Platforms/Report report `not_instrumented`; PWA Course/Funnel/Finance/Sources/Experiments report `attribution_not_audited`. This main delta did not close those attribution or funnel gaps. |

### Baseline evidence — task 1.2

- [PostgreSQL fixture/test](../../tests/test_admin_pwa_v10_regression.py) and [snapshot](../../tests/fixtures/admin_pwa_v10_main_680761f1.json) pin all 162 section × filter × period responses on the unchanged `680761f1` runtime, including both PWA unavailable reasons. The fixed clock, canonical and legacy owners, synthetic payments and overlapping devices make the comparison deterministic. This verifies stored-row projections; it does not establish event-to-UI coverage.
- `verified` on stored rows: Overall weekly Li activation is 2 eligible / 1 started while `direct_start_v1` is 1 / 1; zero-turn Voice contributes to participation but leaves the fixture at 2.0 voice minutes; the internal feedback reservation is the latest of 39 raw CME rows in Report without adding Course engagement.
- Fresh local TCP PostgreSQL via `ANALYTICS_TEST_DATABASE_URL`: `python -m pytest -q -rs tests/test_admin_pwa_v10_regression.py tests/test_admin_pwa_analytics.py::CompleteAnalyticsTests tests/test_admin_pwa_analytics.py::AnalyticsDefinitionTests` → **15 passed, 162 subtests passed, no skips**, on both the unchanged base and the merged planning branch.
- Delta regression suites (Android course API, PWA learning parity including PostgreSQL, browser auth, Voice V8 page, push copy and Smart Reminder PWA) → **240 passed, 303 subtests passed**. Installed clients and Playwright were not run in this baseline step.

### V10 metric keys on `680761f1` (registry seed for 2.1)

- **home:** `users_total`, `new_accounts`, `active_accounts`, `active_today`, `active_pro`, `expiring_pro`, `bot_blocked`, `blocked_current`, `payments_by_status`, `pending_current`, `paying_accounts`, `activity`
- **overview:** the home keys, plus `course_engagement`, `levels`, `languages`
- **platform:** `platforms[]` (`devices`, `accounts`, `online_devices_30d`, `active_dau` / `wau` / `mau`; Telegram: `accounts`, `foreground_accounts_30d`), `versions`, `desktop_detail_limited`, `iphone_pwa_available`
- **course:** `ai_usage`, `course_engagement`, `registration_conversion`, `retention` (`d1`, `d7`), `features` (`lessons`, `tests`, `practice`, `mistakes`, `ai`, `voice`), `feature_denominators`, `activation`, `direct_activation`, `completed_user_lessons`, `foundation`, `chat`, `voice_minutes`, `session_seconds`, `sessions`, `lesson_seconds`, `timed_lessons`, `detail_limited`
- **funnel:** `ai_usage`, `course_engagement`, `registration_conversion`, `attempt_funnel`
- **money:**
  - revenue and payments: `revenue_usd`, `payments`, `paying_histories`, `canonical_payers`, `new_paying_accounts`, `first_payments`, `renewal_payments`, `renewal_percent`, `first_payment_seconds`, `unpriced_payments`, `currencies`, `unknown_currency_payments`, `channels`, `lava`
  - AI cost: `ai_usd`, `ai_requests`, `tokens`, `ai_models`
  - ledger and marketing: `manual_profit_usd`, `expense_usd`, `net_usd`, `tagged_marketing_usd`, `tagged_cac_usd`
  - per-account: `arpu_usd`, `active_denominator`, `arppu_usd`, `average_payment_usd`
- **sources:** `entries`, `attribution`, `traffic`
- **report:** `quality` (`accounts`, `payments`, `learning`, `ai`, `subscription`)
- Projection metadata (for example `detail_since`, `detail_row_limit`, `usd_basis`, `grains`, `attribution_basis`, `traffic_grain`, `traffic_since`, `traffic_timezone` and cache/scope descriptors) is preserved in the fixture; it is not a platform metric.
- **experiments:** out of scope (overall only)
- Home and overview under a non-overall filter currently return the platform projection.

### Planned platform outcome per section (drives 3.2)

| Section | Android | Telegram | iPhone PWA |
|---|---|---|---|
| Platforms | existing (A1) | existing (A2) | card from A4 under the PWA filter (done); Overall list unchanged |
| Course | completions and foundation (A8, A10). `lesson_started` → `not_instrumented` (A7). Practice, exam and mistakes after the `client` key (A13–A15) | lesson, practice, exam and mistakes after the `client` key (A6, A9, A12–A15). Foundation now (A10) | the same as Telegram, plus flow telemetry (A11) |
| Funnel | F2 | F3 after test | F1 |
| Finance | F4/F5 `android` | F4/F5 `miniapp`, `telegram_bot` | F4/F5 `iphone_pwa` + `pwa` |
| Sources | `not_instrumented` (F6: forgeable prefix) | `not_instrumented` (F7) | `not_instrumented` (F7) |
| AI, chat, voice minutes | `not_instrumented` (A16, A17) | the same | the same |
| Ledger, marketing, traffic | `not_applicable` (company-wide) | the same | the same |

## Validation — task 6.1, 2026-11-12

Branch vs baseline `680761f1` (= `origin/main`). The baseline is a detached worktree on the same machine. Both use the same scratch PostgreSQL on TCP `127.0.0.1:55439`, `LC_ALL=en_US.UTF-8` and a synthetic `BOT_TOKEN`.

| Check | Command | Branch | Baseline |
|---|---|---|---|
| OpenSpec | `openspec validate hsk-ai-analytics-integrity --strict` | valid | — |
| Registry | `python scripts/check_analytics_coverage.py` | valid: 118 projection keys, 20 flows | no registry |
| Full unit | `pytest -q tests --ignore=tests/e2e` | 5168 passed, 8 failed, 872 skipped | 5150 passed, 8 failed, 839 skipped |
| Real PostgreSQL | every `*_TEST_DATABASE_URL` module, one fresh DB each | 52 modules, all passed | 45 modules, all passed |
| Analytics CI list | tests in `.github/workflows/analytics-integrity.yml` | 102 passed, 196 subtests | — |
| i18n + static | catalog `--check` + i18n/static suites | 551 passed, 15 skipped | — |
| Admin PWA Playwright | `python -m tests.e2e.<suite>`: `admin_pwa_browser` and 7 other `admin_pwa_*_browser` suites | 8 of 8 passed | — |
| Performance contract | policy, perf/geometry unittests, course-cache regression, progressive browser | policy OK; 11 OK; 45 OK; 64 passed, 2 failed per engine (Chromium, WebKit) | the same 2 failed |

- **Full unit:** the 8 failures are the same tests on both sides, and none is in analytics:
  - `test_miniapp_product_name` (2 tests);
  - `test_android_live_voice_relay` (3 languages);
  - `test_course_character_assets` (3 pages).
- **Real PostgreSQL, first pass:** 4 branch modules and 1 baseline module failed only on database-name guards (analytics requires `*_test`, Smart Reminder requires `smart_reminder_qa*`). They were rerun with `smart_reminder_qa_<tag>_<n>_test`. All passed:
  - platform scope 20;
  - V10 regression 1 test, 162 subtests;
  - coverage contract 10;
  - course map concurrency 5 + 5.
- **Progressive browser:** the 2 failures are the 320 px practice-loading geometry case. They are known baseline failures.
- **Remote CI on `f993a3fa`:** every workflow passed except Desktop. In Desktop, the macOS job was cancelled before a runner was assigned (no steps ran). Windows and the UI contract passed. Desktop code is unchanged.
- **CI e2e fix:** on `c7aa43b6` the Admin PWA security workflow failed in the 3.3 platform loop.
  - Cause: the Report check accepted the loading panel, which is also a `.state-panel`. The read then finished after the next platform menu opened, and its render closed the menu.
  - Fix: the test now waits for each read to settle (`f993a3fa`). No UI change. A pending read closing an open header menu is pre-existing behavior.

### Re-validation after the audit remediation — 2026-11-12

Same machine; disposable PostgreSQL 15 on TCP `127.0.0.1:55441`, `LC_ALL=en_US.UTF-8`, synthetic `BOT_TOKEN`.

| Check | Result |
|---|---|
| OpenSpec `--strict` | valid |
| Registry | valid, 118 projection keys, 20 flows; the diff guard passes in `push` mode (`70759cd0..HEAD`) and `pull_request` mode (`origin/main`) |
| Full unit (`pytest -q tests --ignore=tests/e2e`) | 5183 passed, 8 failed, 876 skipped; the same 8 known failures as above |
| Real PostgreSQL | 52 modules, each in a fresh `*_test` database: all passed (729 tests, 548 subtests; 12 Smart Reminder skips) |
| Analytics CI list | 117 passed, 196 subtests |
| Refresh, writer and R2 cache modules | 34 passed |
| Admin PWA Playwright | 8 of 8 suites passed; `admin_pwa_browser` now writes its Telegram completion through the real route |
| i18n catalogs | `--check`: 0 stale |
| Benchmark | `return_retention` with Voice turn evidence on 50k accounts, 1M course events and 300k AI usage rows: weekly 0.14 s, all time 1.06 s (limit 8 s) |

Each reader fix has a test that fails on the previous reader (checked by swapping in the old file).

## Real-client acceptance — task 6.2

**Open.** It needs the owner's installed clients (Android Play and Direct builds, the Telegram Mini App, an iPhone home-screen PWA) and an Admin PWA that runs this branch. Production runs `main`; no staging deployment of this branch exists.

Each platform filter is its own 24-hour snapshot. To see an action at once, refresh that filter's snapshot through the internal endpoint (machine-only bearer secret; 60 s cooldown per platform), or wait for the next daily snapshot:

```
POST /api/internal/admin-pwa/analytics/refresh
Authorization: Bearer <ADMIN_PWA_MANUAL_AGGREGATE_REFRESH_TOKEN>
{"section": "course", "period": "weekly", "platform": "telegram"}
```

`platform` is `overall`, `android`, `telegram` or `iphone_pwa` (default `overall`); `section` is `course`, `funnel`, `money`, `sources` or `report`. Overall Home/Overview use the existing empty-body refresh.

Owner checklist, after deploy, with one account on every client:
1. Complete one lesson each on Android Play, Android Direct, the Telegram Mini App and the iPhone PWA.
2. Refresh `course`/`weekly` for `overall`, `android`, `telegram` and `iphone_pwa`. Admin PWA → Statistics → Course, Weekly: under each platform filter «completed lessons» grows only by that client's lessons. Android = Play + Direct combined (A19).
3. Overall: the account counts once.
4. Refresh `report`/`weekly` (`overall`). Report → freshness: each platform's learning time is the time of its action.
5. On the iPhone PWA, open the Pro offer → choose a plan → start checkout (no payment needed). Refresh `funnel`/`weekly` for `iphone_pwa`. The «iPhone PWA Pro» panel in Conversion counts the attempt.

## Audit remediation — PR #285, 2026-11-12

The audit (`Audit-Analitika.md`, 55 findings) was verified independently: 17 confirmed, 8 partial, 25 intentional limitations, 2 false positives, 3 need runtime evidence. Fixed here:

| # | Defect | Fix | Evidence |
|---|---|---|---|
| 13 | Other clients' Starter 0 rows filled a Telegram/PWA `foundation` detail limit | Non-start rows are read only for accounts whose start carries this client | `CourseFoundationDetailLimitTests` (fails on the old reader) |
| 28 | All-time PWA Pro funnel became `detail_limited` | Aggregated per attempt in SQL; PostgreSQL and SQLite paths | 2 600 extra attempts counted exactly; SQLite suite |
| 31 | A Voice session started before the window could not count as a return; one ending after it could | Voice counts by a spoken-turn usage row in the window, or a session wholly inside it | `test_return_retention_dates_a_voice_return_by_its_turn` |
| 34 | Average payment and ARPPU divided by unpriced payments (a `main` defect) | Priced payments and payers with a priced payment only | Golden test pins the two corrected Overall values; unit test |
| 37 | Freshness accepted a caller `client` lookalike before tagging was live | Same per-client boundary as Course | Freshness lookalike test |
| 40 | Report quality looked platform-scoped | One-line UZ/RU/TJ note «all platforms; independent of filter and period» | i18n catalogs; browser suite |
| 44 | Manual refresh was Overall-only, so 6.2 could not refresh a platform filter | Optional `platform` per snapshot, per-platform cooldown; Report refreshable | Cache and endpoint tests |
| 6 | A description-only flow edit satisfied the diff guard | Only events or per-platform status, chain test or reason count | Contract tests |
| 7 | `covered` was checked only for a test's existence | The test must run in `analytics-integrity.yml` and read the metric from `/api/admin/v1/analytics` for that platform | Contract tests |
| 8 | Attribution in `app/main.py` and `app/api/miniapp_practice.py` was unguarded | Critical paths with per-function `symbols` (AST compare); the writer service added | Contract tests |
| 9 | Registry reasons said shared writes lack a client | Reasons describe the route-set key and the missing scoped readers | Registry |
| 42 | 6.2 marked done while not performed | 6.2 reopened | `tasks.md` |
| 43 | No single route → browser run | Browser QA writes its Telegram completion through the real signed lesson routes | `tests/e2e/admin_pwa_browser.py` |

Also: the writer drops a caller `client` key before tagging, so the route key is always final, and logs when a tag is omitted for size.

Remaining from the audit (not code defects in this change):
- #26 PWA Pro attempt split on resume: needs learner PWA JS and service-worker changes plus runtime evidence. Left for a separate task.
- #45/#46: CI and full-suite results are recorded in the validation table, including known baseline failures.
- #47: few `covered` cells. More route chains are follow-up work, not a defect.
- #48/#49: real devices and staging are 6.2.
- #24/#51/#53: need production-scale or production-data evidence. Local 1M-row runs stayed far below the 8 s limit.

## Analytics Impact summary — task 6.3

Branch `planning/analytics-integrity-openspec-20261109` (PR #285) on runtime base `680761f1`. Registry: [`FEATURE_ANALYTICS_COVERAGE.json`](FEATURE_ANALYTICS_COVERAGE.json), 118 projection keys, 20 flows.

**Metric cells per platform.**
- `covered`: a route → PostgreSQL → Admin API chain test exists. The checker requires that `analytics-integrity.yml` runs it and that it reads the metric from `/api/admin/v1/analytics` for that platform.
- `partial`: the value is shown under the filter from verified stored-row predicates, with stored-row tests but no route chain yet.

| Platform | covered | partial | not_instrumented | not_applicable |
|---|---|---|---|---|
| Android (Play + Direct combined) | 1 | 35 | 33 | 18 |
| Telegram Mini App | 1 | 28 | 38 | 20 |
| iPhone PWA | 2 | 34 | 32 | 19 |
| macOS / Windows (frozen) | 0 | 6 | 64 | 17 |

- **Route chains:**
  - `course.completed_user_lessons` on all three clients ([test](../../tests/test_analytics_platform_chain.py));
  - `funnel.pwa_pro_attempt_funnel` on PWA ([test](../../tests/test_pwa_pro_funnel_chain.py)).
- **Browser:** `tests/e2e/admin_pwa_browser.py` writes its Telegram completion through the real signed lesson routes, then reads it under the Telegram filter (SQLite).
- **Corrected values:** Overall Finance `average_payment_usd` and `arppu_usd` now exclude unpriced payments (#34, a `main` defect). The golden test pins both new values.
- **New series:** other V10 values are unchanged, and the golden test ignores only these keys:
  - `funnel.pwa_pro_attempt_funnel` (Overall + PWA);
  - `course.return_retention` (Overall);
  - `report.platform_freshness` (one global list).
- **Admin UI:**
  - Every tab reads `metric_states`. An unavailable metric shows its reason, never a number or zero.
  - Per-platform panels show `attributed_since`.
  - New: the PWA Pro panel, separate «return» and «course open» labels, and the Report freshness table.
  - All new text is in UZ/RU/TJ.
- **Overall:** canonical accounts are deduplicated. Platform groups overlap (`platform_counts_overlap`).
- **Tests and CI:** the 6.1 table above. `analytics-integrity.yml` runs the coverage checker and the analytics suite on every PR.

**Known gaps** (registry reasons carry the detail):
- Telegram course opens (A3) and Telegram lesson-flow telemetry (A12) have no exclusive client signal. Course open, activation and sessions per platform stay unavailable.
- Android lesson starts have no writer (A7).
- Play vs Direct is not in analytics rows (A19), so one combined Android value is shown.
- These stay `not_instrumented` per platform:
  - PWA device inventory (A5);
  - voice, chat and AI usage (A16, A17);
  - subscription entry sources (F6, F7; they need a schema change).
- `return_retention` per platform has no platform-of-registration signal.
- Rows written before the route-set `client` key count only in Overall (`attributed_since`).
- A resumed PWA Pro checkout can split into two attempts (#26); it needs a learner PWA change.
- Desktop: registry statuses only (freeze).

**Monitoring handoff:** reuse, do not copy, the registry identifiers:
- platform keys `android`, `telegram`, `iphone_pwa`, `macos`, `windows`;
- metric IDs `section.key`;
- flow IDs and `critical_paths`;
- the reasons `no_data`, `not_instrumented`, `attribution_not_audited`, `detail_limited`, `not_applicable`.

**Promotion:** waits for the owner's approval. This work has not changed `main`.

## Next stage — mandatory requirements (not implemented)

The owner set these four as mandatory for the next stage. **None is implemented in this change.**

1. **Android Lesson Start.** Android writes no lesson start (A7), so Course > Android has no lessons entry and no start-based cohort. Needed: a server-written, deduplicated lesson start from the authenticated Android course route with the route-set client `android` (Play + Direct combined until the channel is recorded, A19), read by the Android Course features.
2. **PWA Activation.** PWA activation, direct activation and sessions are `not_instrumented` per platform (A11): their anchor and most rows carry no route-set client. Needed: a defined PWA activation (signup or handoff → first meaningful learning action) from route-owned rows only, with its own cohort and window.
3. **Subscription Sources.** Sources is Overall-only (F6, F7): `subscription_entry_events` has no platform column and entry sources on the Telegram route are caller text. Needed: a server-set platform on each entry (reviewed schema change), then Sources and source → payment attribution per platform.
4. **Platform D1/D7 Retention.** `return_retention` is Overall-only (D5): the signup cohort has no platform of registration. Needed: a defined platform cohort (platform of registration or first verified open) and per-platform return evidence, with D1/D7 windows matching the Overall series.

### Implementation plan — 2026-11-12 (reviewed; R1 started)

Written from the code on this branch.
- On approval, each requirement becomes its own OpenSpec change and its own PR.
- That change's `tasks.md` is its only checklist; this section stays the context.
- Nothing merges to `main` without the owner's permission.

**Prerequisite:** PR #285 merged to `main`. All four reuse its pieces:
- the route-set `client` key;
- the registry and coverage guard;
- the chain-test rule;
- the per-platform snapshots and manual refresh.

**Rules for all four:**
- **Platform source.** The platform comes only from the route that wrote the row, as a route-set `client` key or column. Caller text (`source`, `transport`, `client`) never decides a platform.
- **Telemetry never blocks.** It never blocks or changes a learner, payment or auth response. Writes are best-effort, in a savepoint.
- **Before the boundary.** Rows written before a writer goes live count only in Overall. The platform value reports `attributed_since`; before that date the cell stays `not_instrumented`.
- **Desktop freeze.** No desktop code or behavior changes. In shared services the new write is gated on the Android namespace.
- **Per-cell requirements.** Every new or changed metric cell needs:
  - a registry row with an honest status;
  - a route → PostgreSQL → `/api/admin/v1/analytics` chain test listed in `analytics-integrity.yml`;
  - the golden test pinning Overall. An intended Overall change is pinned explicitly, as #34 was.
- **Admin UI.**
  - New Admin text is in UZ/RU/TJ, and the Admin PWA browser suite asserts it.
  - UI changes are small and follow `AGENTS.md` and the `hsk-ai-ui` skill.
- **Performance.** Reads stay bounded aggregates inside the 24-hour per-platform snapshot.
- **Acceptance.** Real-client acceptance runs on the owner's devices, as in 6.2. It uses the manual refresh with `platform`.

**Order:**

| Step | Requirement | Schema | Client release | Size | Reason |
|---|---|---|---|---|---|
| 1 | R1 Android Lesson Start | no | no (server only) | S | Smallest. Unblocks Android `features.lessons` and gives R4 an Android learning signal. **Implemented 2026-11-12** on `feat/analytics-android-lesson-start-20261112` (stacked on PR #285; not merged) |
| 2 | R2 PWA Activation | no | no | M | The writer gets one argument; the reader reuses the activation funnel. **Implemented 2026-11-12** on `feat/analytics-next-stage-20261112` (stacked on R1; not merged) |
| 3 | R4 Platform D1/D7 Retention | no | no | M | Reader only; uses R1 and R2 rows as evidence. **Implemented 2026-11-12** on `feat/analytics-next-stage-20261112` (stacked on R2; not merged) |
| 4 | R3 Subscription Sources | **yes** (one nullable column) | no | M–L | The only migration, so it deploys alone. **Implemented 2026-11-13** on `feat/analytics-next-stage-20261112` (stacked on R4; not merged; the migration needs the owner's approval at the PR) |

#### R1. Android Lesson Start

**Definition.** The server writes one `android_lesson_started` per Android account, level, lesson and UTC day.
- It is written when the authenticated `GET /api/v3/android/course/lesson/{order}` has passed the access check and returns the lesson.
- A refused lesson (lock, limit or foundation) writes nothing.
- Play and Direct stay combined (A19).

**Why not `lesson_started`.** `motivation_reminder_service.py` reads `lesson_started` for the D1 recovery and the unfinished-lesson reminder. An Android start under that name would send new Telegram messages to Android learners: a behavior change. `android_lesson_started` has these properties:
- **Server-only.** It is not in `CLIENT_COURSE_MINIAPP_EVENT_NAMES`, and `/api/v3/android/events` accepts only widget and notification names. No caller can write a lookalike.
- **Already expected by the Admin readers.** Overall V10 reads it in `features.lessons`, `started_accounts` and `COURSE_EVENTS`; bot-block diagnostics read it too. These readers were written for it and simply had no writer.
- **Not read by product flows.** Reminders, the activation funnel and lesson durations do not read it. Overall `activation` and `lesson_seconds` stay unchanged.

**Writer.**
- **Location:** `AndroidCourseService.lesson` (`app/services/android_course_service.py`), after `super().lesson()` returns. The shared `DesktopCourseService.lesson` is not changed.
- **Call:** `record_server_event(event_name="android_lesson_started", source="android_course", analytics_client="android", level=…, lesson_order=…)`, with `dedupe_key=f"android-lesson-start:{level}:{order}:{utc_date}"`.
- **Commit:** the write has its own commit after the lesson's commit (`desktop_course_service.py` commits before returning). A failure is logged, and the lesson is returned unchanged.
- **Activity:** like every learner-facing Android server event, it updates `users.last_active_at`. The Android app-open event of the same session already does this.

**Readers.**
- **Course > Android.** In `pwa_analytics_course_platform.py`, Android `features.lessons` reads `android_lesson_started` with the `client: android` tag.
- **Boundary.** It has its own boundary: the first tagged row, reported as `attributed_since.features_lessons`. The Admin feature panel shows that date under the table, reusing existing UZ/RU/TJ strings. Until the first row exists, the lessons entry is omitted, as it is today.
- **Registry.** The name changes from `no_writer` to a declared event of the `lessons` flow.

**Overall impact (intended).** From the deploy date, Android starts enter Overall `features.lessons` and Overview `started_accounts` / course engagement. Until now, Android learners never counted as started. The golden fixture has no Android start, so it stays unchanged. A new test pins the Overall change.

**Status — 2026-11-12: implemented, not merged.** OpenSpec change `analytics-android-lesson-start`.
- **Writer and reader:** as above. `android_lesson_started` is also a server-only boundary row for Android (`SERVER_ONLY_TAGGED`), so Android features are no longer missing when an account has no tagged practice rows yet.
- **Side effect:** Report freshness dates Android learning by these opens too. They are Android learning actions.
- **Evidence:** writer unit tests (4), stored-row tests (2) and a bearer route chain test. Each fails on the old code.
- **Remaining:** owner acceptance on an Android device (task 3.4).

**Registry and tests.**
- **Registry.** The Android `course.features` reason drops "lessons omitted". Flow `lessons` on Android is `covered` once the chain test runs in CI. Add the critical path `app/services/android_course_service.py` with symbol `lesson`.
- **Unit tests:**
  - one tagged row;
  - a refetch on the same day is deduplicated;
  - a refused lesson writes nothing;
  - a writer failure still returns the lesson;
  - no `lesson_started` row is written, so reminders see nothing new.
- **PostgreSQL chain.** Android route → `course` / `android` → `features.lessons`.
- **Overall.** `features.lessons` counts an account that starts on Telegram and on Android once.

#### R2. PWA Activation

**Definition (default taken).** Two cohorts, both from route-owned rows only:
- **New PWA learner.**
  - Anchor: `onboarding_completed` written by `POST /api/v3/pwa-auth/onboarding/finish`, tagged `client: iphone_pwa`.
  - Steps reuse the existing activation windows: lesson start within 2 minutes, section completed within 15 minutes, lesson completed within 24 hours.
  - Only PWA-tagged steps count.
  - Onboarding is deduplicated per profile, so an account onboarded on Telegram is not in this cohort.
- **Telegram → PWA handoff.** Anchor: `pwa_handoff_completed`, which the PWA handoff redeem route writes on the server. Activated means a first PWA-tagged lesson start or completion within 24 hours.
- **Direct activation.** PWA `direct_activation` comes from the same anchor with variant `direct_start_v1`.
- **Sessions.** PWA `sessions` stay `not_instrumented`. Most session rows (card views, interactions) carry no route-set client. They are not part of R2.
- **Open decision.** An existing account that signs in on the PWA without onboarding or a handoff is in neither cohort. Its anchor would be the PWA sign-in (A5).

**Status — 2026-11-12: implemented, not merged.** OpenSpec change `analytics-pwa-activation`.
- **Writer:** as above, on both the HSK 2.0 and HSK 3.0 onboarding paths, including the choice rows.
- **Reader:**
  - The handoff cohort starts at the PWA boundary (`attributed_since.handoff_activation`). Before it, PWA lesson rows carried no tag, so an earlier handoff would look like a missed activation.
  - The onboarding cohort starts at the first PWA-tagged onboarding (`attributed_since.activation`).
  - Overall and the PWA view share one activation helper; the golden test is unchanged.
- **UI:** one cohort row («Telegram → PWA → dars · 24 soat», RU/TJ too) and two boundary lines, PWA only.
- **Evidence:**
  - writer unit tests (3);
  - stored-row tests (5);
  - a route chain test covering the PWA onboarding, a Telegram onboarding with a caller `client`, and two handoffs.
  The chain test fails on the old writer and on the old reader.
- **Remaining:** owner acceptance on the iPhone PWA (task 3.4).

**Writer.**
- `CourseMiniAppOnboardingService.complete(..., analytics_client=None)` passes the key to `onboarding_completed` and its step rows. The PWA route passes `iphone_pwa`.
- The Telegram and Android onboarding routes also pass `telegram` and `android` (default taken). This is writer-only; their readers come later.

**Reader.**
- `course_platform_metrics` for `iphone_pwa` returns:
  - `activation`;
  - `direct_activation`;
  - a new key `handoff_activation` `{eligible, activated, percent}`.
- It is bounded by `bounded_rows` on the 30-day detail window.
- `attributed_since` is the first tagged PWA `onboarding_completed`.
- Overall activation is unchanged: it reads the same rows, which now carry one more payload key.

**UI.** On the Course tab under the PWA filter: the existing activation card plus one «Telegram → PWA» row, in UZ/RU/TJ.

**Tests.**
- A unit test for the writer key.
- Cohort tests:
  - a Telegram-onboarded account stays outside the PWA cohort;
  - a handoff with no PWA learning is not activated;
  - a caller `client` on the Telegram route never enters.
- A PostgreSQL chain from the PWA routes to `course` / `iphone_pwa`.
- A label check in the browser suite.
- The golden test stays unchanged.

#### R3. Subscription Sources

**Definition.** Each subscription entry stores the client of the route that recorded it. The source text stays descriptive only.

**Schema (needs owner approval).**
- Alembic `0155` adds a nullable `client VARCHAR(16)` to `subscription_entry_events`, with an index on `(client, created_at)`.
- No backfill: old rows stay Overall-only.
- The column is additive and nullable, so PostgreSQL does not rewrite the table.
- The migration is tested with the local PostgreSQL routine: create_all + stamp + upgrade/downgrade.

**Writers** (`record_entry(..., client=...)`):
- **`main.py` (Telegram subscription overview route, the only Telegram entry writer):** `telegram`. A caller that sends `source=android_subscription` still stays Telegram.
- **`android_features.py` and the Android Lava overview route in `lava_checkout.py`:** `android`.
- **The PWA entry in `pwa_auth.py`:** `iphone_pwa`.
- **`desktop_subscription_service.py` (shared):** `android` only for the Android namespace. Desktop leaves the column empty (freeze).

**Reader.** `platform_sources_metrics(db, platform=...)` (Overall keeps `sources_metrics`):
- **`entries`:** rows with that `client`, from its `attributed_since`.
- **`attribution`** (default taken): payments of that platform (F4 `PAYMENT_PLATFORM_SOURCES`) are attributed to the nearest earlier entry **on the same platform**, else to `unknown`. Overall keeps the current any-platform rule.
- **`traffic`:** stays `not_applicable` (company-wide).
- The Sources section gets per-platform composition and snapshot variants.
- **As built (2026-11-13):** `record_entry` stores only `telegram`/`iphone_pwa`/`android`, anything else NULL. Payments before a platform's first entry are left out (no entry could match them). Both values are null before the first entry. Registry: `entries` `covered` (route chain test); `attribution` `partial`, because its payment side has projection evidence only, as in Finance. OpenSpec change `analytics-subscription-sources-platform`.

**Tests:**
- migration upgrade and downgrade;
- each writer sets the column, and a caller cannot choose it;
- the per-platform reader;
- a PostgreSQL chain from each route to `sources` / platform;
- the golden test with Overall unchanged;
- an EXPLAIN for the nearest-entry subquery.

#### R4. Platform D1/D7 Retention

**Definition (default taken).**
- **No registration signal.** `users` has no platform-of-registration column, and adding one would change the auth paths, which is out of bounds.
- **Proposed cohort.** The account's **first verified use of the platform**.
- **Windows.** D1 is evidence 24–48 hours after that first use; D7 is 168–192 hours after it.
- **Maturity.** The matured-cohort rule is the same as Overall `_cohort_returns`.

| Platform | First-use anchor | Return evidence |
|---|---|---|
| Android | first `android_first_open` / `android_app_opened` (A1) | `android_app_opened`; Android-tagged learning rows, including R1 |
| iPhone PWA | first `miniapp_opened` with dedupe prefix `pwa-course-v3:` (A4), or the first PWA-tagged learning row | the same two signals |
| Telegram | the first Telegram-tagged row (route-set `client: telegram`) at or after the Telegram boundary. `user_client_presences` is not used: only `/api/v3/desktop-download/status` writes it, so its `first_seen_at` is not first use | Telegram-tagged learning rows only. Telegram opens have no exclusive signal (A3), so this is a learning return and is labelled as one |

- **Exclusions.** Voice and AI have no per-platform attribution (A16, A17), so they are left out.
- **Boundary.** Cohorts before each anchor's `attributed_since` are left out.
- **Overall.** Overall `return_retention` is unchanged.
- **Overlap.** An account can be in several platform cohorts (`platform_counts_overlap`).

**Reader.**
- `platform_return_retention(db, platform, since, now)`, next to `return_retention`.
- Per-account first use is computed in one grouped subquery.
- Performance gate: an EXPLAIN on a 1M-row fixture stays within the current `return_retention` budget (all-time 1.06 s locally).

**UI.** A retention card under a platform filter, with a one-line cohort note «first use on this platform», in UZ/RU/TJ.

**Tests:**
- an account that is on Telegram and first opens the PWA on day 10 enters the PWA cohort on day 10;
- a return on another platform does not count;
- immature cohorts are excluded;
- lookalike rows before the boundary never become an anchor;
- a PostgreSQL chain;
- a performance test.

**Status — 2026-11-12: implemented, not merged.** OpenSpec change `analytics-platform-return-retention`.
- **Reader:** `platform_use` and `platform_return_retention` in `pwa_analytics_course_platform.py`.
  - Evidence is the same as Overall D5 (opens and server-written learning outcomes), restricted to one platform.
  - Client-writable starts are excluded, as in Overall.
  - Both windows come from one statement.
- **UI:** the existing D1/D7 return cards and cohort rows under each mobile filter, plus one UZ/RU/TJ line giving the cohort rule and its start date.
- **Side effect:** none on Overall (golden test).
- **Evidence:**
  - stored-row tests (4);
  - a route chain test on all three mobile routes, which fails on the old reader;
  - the Admin PWA browser suite.
- **Remaining:** the performance numbers on an idle machine (task 2.3), and owner acceptance.

**Plan review — 2026-11-12.** The owner asked for the plan to be confirmed as complete, or strengthened and started. It could not be confirmed as written. Checking the code changed three points:
1. **R1 event name.** `lesson_started` drives Telegram reminders (`motivation_reminder_service.py`), so R1 writes the server-only `android_lesson_started`. Details are in R1.
2. **R4 Telegram anchor.** `user_client_presences` is written only by the desktop-download status route, so it cannot date first use. The anchor is the first Telegram-tagged row.
3. **New rule for all four.** Before adding a write, list every consumer of that event name or table, not only the Admin readers: reminders, bot handlers, entitlements, diagnostics. A write that a product flow reads is a behavior change and is not allowed.

**Decisions (defaults taken 2026-11-12).** The owner delegated these. The owner can change each one before its PR merges.

| # | Decision | Default |
|---|---|---|
| R1 | Start dedupe; effect on Overall | One start per account, level, lesson and UTC day. Overall `features.lessons` and `started_accounts` rise from the deploy date; activation and lesson time do not change |
| R2 | Cohorts | New PWA onboarding, plus Telegram → PWA handoff |
| R2 | Telegram/Android onboarding tag | Tagged in the same change (writer only); their readers come later |
| R2 | PWA sign-in without onboarding or handoff | Outside both cohorts; listed as a gap |
| R3 | Schema change | Prepared in its own PR. **The migration merges only with the owner's explicit approval at that PR** |
| R3 | Source → payment rule | Nearest earlier entry on the same platform; Overall keeps today's rule |
| R4 | Cohort and Telegram return | First verified use of the platform; Telegram counts learning returns only |

**Definition of done (each requirement):**
- **Routes and writers:**
  - the writer is server-built;
  - an exhaustive consumer check shows no product-flow change;
  - unit tests cover dedupe, refusal and failure isolation.
- **Readers and states:**
  - the reader returns the value from `attributed_since` on, and `null` with a reason before that;
  - the registry is updated;
  - the coverage checker passes in push and pull-request modes.
- **Tests:**
  - a route → PostgreSQL → `/api/admin/v1/analytics` chain test runs in `analytics-integrity.yml`;
  - the golden test passes, with any intended Overall change pinned explicitly;
  - the full unit suite shows only the known baseline failures;
  - every PostgreSQL module passes on a fresh database;
  - the Admin PWA browser suites pass;
  - the CI workflows are green, apart from the known runner-side Desktop macOS cancel.
- **Docs:** UZ/RU/TJ text, `READ_PROJECTIONS.md`, this file and the change's `tasks.md` are updated.
- **Release:**
  - the owner accepts the result on a real client (6.2 style);
  - nothing merges to `main` without the owner's permission.

**Risks and rollback:**

| Risk | Guard | Rollback |
|---|---|---|
| A new event changes a product flow | Consumer check; R1 uses a name no flow reads | Revert the writer; the rows are inert |
| An analytics write breaks a learner response | Savepoint, separate commit, failure test | — |
| Double counting on refetch | Dedupe key per day; unit test | — |
| Overall values move | Golden test; intended moves pinned and listed in Impact | Revert the reader commit |
| A per-platform read is slow | `bounded_rows`; EXPLAIN on a 1M-row fixture before merge | Hide the cell (`not_instrumented`) |
| R3 migration on production | Additive nullable column, upgrade/downgrade test | `alembic downgrade` drops the column; old readers ignore it |

## Decisions log

- 2026-11-09 — Single context file is this document. OpenSpec `tasks.md` is the only checklist.
- 2026-11-09 — Registry format is JSON, not YAML, because PyYAML is not a project dependency.
- 2026-11-09 — Removed from scope on owner request: client telemetry retry, intake counters, campaign attribution, error/performance analytics, D30, PR template.
- 2026-11-11 — PWA foreground proof: reuse the existing `miniapp_opened` row with source `pwa_course_v3` (A4). No `pwa_active_day` event. First, the Telegram routes must stop accepting `pwa_course_v3` and `transport` from the client (A3, A12).
- 2026-11-11 — Android Play/Direct: the channel is not in analytics rows (A19), so only the combined Android value is shown.
- 2026-11-11 — Shared writers (A6, A9, A12–A15) get one server-set payload key, `client` ∈ `telegram` / `iphone_pwa` / `android`, on their existing write. It is passed from the route; no migration. Rows written before it carry no key, so those per-platform values report `attributed_since`.
- 2026-11-11 — The existing `retention` counts both Mini App and PWA opens (A3 + A4). Its label is `course_open`, not `miniapp_open`.
- 2026-11-11 — `android_lesson_*` and `android_practice_*` names in the readers have no writer (A7, A13). They are kept so values stay unchanged; the registry marks them `no_writer`.
- 2026-11-11 — AI usage, chat and voice minutes (A16, A17), and PWA/Telegram Sources entries (F7), have no platform field. They stay `not_instrumented` per platform. No schema change in this work.
- 2026-11-11 — Handoff events (A18) keep their existing basic Statistics consumer. No V10 duplicate.
- 2026-11-11 — Desktop freeze: macOS/Windows get registry statuses only.
- 2026-11-11 — The registry's platform keys and feature IDs are stable. Monitoring will reference them instead of duplicating them.
- 2026-11-12 — Course per platform reads the route-set `client` key only as the payload's final key (`endswith`), so a nested caller object cannot match. `attributed_since` = first server-built tagged completion per client (a data-derived post-guard boundary); client-writable starts count only from it. No tagged row yet → `no_data`, never zero. Android completions use the Android-only source `android_course` for all history. AI, chat and voice entries are omitted (A16/A17); Android has no lessons entry (A7).
- 2026-11-12 — PWA Platforms card: DAU/WAU/MAU from `miniapp_opened` rows whose dedupe key starts with the route-owned `pwa-course-v3:` (only `/api/v3/pwa/map` builds it; callers cannot write `miniapp_opened`). No device inventory (A5). It appears under the PWA filter in Platforms/Home/Overview; the Overall card list and `iphone_pwa_available` stay as pinned.
- 2026-11-12 — Sources stays Overall-only on every platform. F6 was planned for Android, but entry sources on the Telegram route are caller text, so `android_*` can be forged; `subscription_entry_events` has no platform column and a schema change is out of scope.
- 2026-11-12 — Funnel per platform uses the route-set payload `transport` of the base `checkout_opened` row (existing on PWA and Android Lava; added to the two Telegram writes and the Android manual opening; desktop rows unchanged). Stage, receipt and approval rows attach to that attempt. Caller `source` and attempt text never attribute. `attributed_since.attempt_funnel` is the first marked opening; earlier rows stay in Overall. Funnel activity families (AI, engagement, registration) are not computed for a platform.
- 2026-11-12 — Finance per platform uses the server-set `payments.source`: Android `android`; Telegram `miniapp` + bot `telegram_bot`; PWA `iphone_pwa` + Lava `pwa`. Lava lifecycle uses `lava_invoices.source`. The first-payment/renewal order stays canonical across platforms, so a later payment on another client is a renewal. AI cost, ledger, marketing and ARPU are not computed for a platform (`not_instrumented` / `not_applicable`). Desktop `desktop` payments stay out of the three mobile filters.
- 2026-11-12 — Course `foundation` per platform: the Starter 0 cohort is anchored on the start, so only `foundation_started` must carry the route-set final `client` key (from `attributed_since` on); that learner's completion, objective and paywall rows follow it. Android has no start writer → `not_instrumented`. PWA activation, direct activation and sessions stay `not_instrumented`: their anchor and most rows have no `client` key, and `transport` is forgeable on old Telegram rows.
- 2026-11-12 — PWA Pro funnel (F8) reading rules: attempt = (canonical account, `attempt_id`); steps opened → plan selected → checkout started → paid, each counting attempts that reached it or later; paid only with the ledger row and a once-approved payment; reversed = invoice `refunded` / `chargeback_lost`; `unlinked` = verified first-invoice PWA Lava payments no attempt reached; 30-day lookback before the window. It is computed in the funnel section under Overall and PWA only (Android/Telegram `not_applicable`), beside the unchanged `attempt_funnel`.
- 2026-11-12 — Report freshness (D7) is one global list under every filter, like `quality`: Android/Telegram/PWA × learning/payments with `latest_at` and `unresolved_owners`. Android learning excludes the `android_*` prefix rule because the Telegram client writes `android_play_opened`; it uses `android_app_opened`, `android_course` completions and the `client` key. An owned row whose account is gone counts as unresolved, as in the analytics owner rule.
- 2026-11-12 — `return_retention` (D5) is Overall-only. Per-platform opens are verifiable for Android (A1) and PWA (A4), but the signup cohort has no platform-of-registration signal, so a per-platform cohort is not defined; every platform filter shows `not_instrumented`. The allowlist is server-written events only (none of `CLIENT_COURSE_MINIAPP_EVENT_NAMES`), plus Voice sessions with `turn_count > 0`.

- 2026-11-12 — Audit remediation (#13): Course `foundation` per platform reads non-start rows only for accounts whose `foundation_started` carries this client (a semi-join), so other clients' history never fills its detail limit. Values are unchanged; the reducer already ignored those rows.
- 2026-11-12 — Audit remediation (#28): `pwa_pro_attempt_funnel` is a SQL aggregate per (account, `attempt_id`). PostgreSQL extracts the token with a text match on the server-built payload; SQLite (browser QA) uses JSON1. It no longer depends on the 5 000-row detail limit.
- 2026-11-12 — Audit remediation (#31): Voice return evidence is the time of a spoken turn: `voice_practice_reply`, `voice_live_audio` or `voice_live_evaluation` usage rows (written before `turn_count` increments), or a session with turns that started and ended inside the window. No schema or Voice behavior change.
- 2026-11-12 — Audit remediation (#34): Finance average payment and ARPPU exclude unpriced payments and payers with no priced payment. This corrects a `main` defect; only these two Overall keys differ from the golden, and the test pins their new values. The legacy basic statistics service is unchanged.
- 2026-11-12 — Audit remediation (#37): Report freshness uses the Course boundary per client (first server-built tagged completion), computed in one grouped scan.
- 2026-11-12 — Audit remediation (#44): the internal section refresh takes an optional `platform` and refreshes that filter's own snapshot; the cooldown is per platform; Report is refreshable. The empty-body Overall overview refresh is unchanged. There is still no Admin UI refresh button.
- 2026-11-12 — Audit remediation (#6–#8): the diff guard ignores flow `description` and whitespace; `covered` needs a CI-run test that reads the metric from the Admin analytics route for that platform; large shared modules are guarded per function through `symbols`.

## Session log (newest first, one or two lines each)
- 2026-11-13 — R4 performance on local PostgreSQL 15, 1M CME rows / 20k accounts, idle machine (second run, seconds): weekly Overall 0.84, Android 0.19, Telegram 0.11, PWA 0.15; monthly Overall 2.20, platforms 0.11–0.19; all-time Overall 18.1, Android 10.7, Telegram 8.6, PWA 9.7. Before the fix the first-use subquery joined users through `owner`'s OR and looped over every account (weekly 1.1–1.8 s, slower than Overall); it now takes the owned and legacy branches separately, as Overall return_retention does. Same cohorts and counts; R4 scope, chain and golden tests pass. These reads run in the 24-hour snapshot, not per request.
- 2026-11-13 — R3 Subscription Sources implemented on `feat/analytics-next-stage-20261112` (stacked on R4): migration `0155` (nullable `client` + index, upgrade/downgrade tested on local PostgreSQL), five route writers, `platform_sources_metrics`, registry, UI (same-platform note in UZ/RU/TJ, traffic Overall-only), OpenSpec change `analytics-subscription-sources-platform`. Writer, stored-row, chain and golden tests pass and the new ones fail on the old code; the Admin PWA browser suite passes with R1–R4. The migration merges only with the owner's approval.
- 2026-11-12 — R4 Platform D1/D7 Retention implemented on `feat/analytics-next-stage-20261112` (stacked on R2): first-use cohort per platform, same-platform returns, registry covered, one UI line, OpenSpec change `analytics-platform-return-retention`. The Admin PWA browser suite passes with R1, R2 and R4. Its Report freshness check now expects Android and PWA learning dates, from the R1/R2 rows.
- 2026-11-12 — R2 PWA Activation implemented on `feat/analytics-next-stage-20261112` (stacked on R1): onboarding rows carry the route-set client on all three routes; Course > iPhone PWA gets `activation`, `direct_activation` and `handoff_activation`. Registry, UI row, OpenSpec change `analytics-pwa-activation` and tests are done.

- 2026-11-12 — R1 Android Lesson Start implemented on `feat/analytics-android-lesson-start-20261112` (writer, reader, registry, UI boundary line, tests). Fixed a wall-clock dependence in the V10 golden fixture (user 4 `last_active_at`), which made the money/overall cases fail after 12:00 UTC on unchanged code; that fix is on the PR #285 branch.
- 2026-11-12 — Plan review: R1 writes the server-only `android_lesson_started`, because `lesson_started` drives Telegram reminders. The R4 Telegram anchor is the first tagged row, since presence is not first use. Added defaults, definition of done and risks. R1 started.
- 2026-11-12 — Wrote the implementation plan for the four next-stage requirements (order R1 → R2 → R4 → R3, rules, per-requirement writer/reader/tests, owner decisions) from the code on this branch. Nothing implemented; waits for owner approval.

- 2026-11-12 — Audit remediation for PR #285: fixed confirmed findings #6–#9, #13, #28, #31, #34, #37, #40, #42–#44 (table in [Audit remediation](#audit-remediation--pr-285-2026-11-12)); writer keeps the route key final. 6.2 reopened. Four next-stage requirements recorded, not implemented. Re-validation table above; no merge to `main`.

- 2026-11-12 — Tasks 6.1–6.3: validation matches the baseline. Branch and baseline have the same 8 unit failures; all PostgreSQL modules pass on both; 8 of 8 Admin Playwright suites pass; the perf contract has only the known 320 px failures. The CI e2e flake in the platform loop is fixed in the test (`f993a3fa`); Admin PWA security CI is green. 6.2 was not performed (reason and owner checklist above). The Impact summary is written. Promotion waits for the owner.

- 2026-11-12 — Task 5.2: `app/admin_api/pwa_analytics_freshness.py` adds `platform_freshness` to the Report (registry row; V10 golden ignores only this key). [Test](../../tests/test_admin_pwa_report_freshness.py): stale Android stays visible with its 10-day-old timestamp, Telegram counts an orphan event and a payment of a deleted account as unresolved, a PWA lookalike, `android_play_opened`, a feedback reservation, Desktop payments and future rows are excluded, an empty platform is `null`, and no IDs/payloads appear. On 1M CME rows it takes 154 ms (one grouped scan). The Report tab shows the table (UZ/RU/TJ); the browser suite checks rows, dashes and absence of IDs. Analytics CI suite **102 passed, 196 subtests**; browser suite passed.

- 2026-11-12 — Task 5.1: `retention` keeps its values and is labelled «course open» (UZ/RU/TJ); new Overall `return_retention` D1/D7 beside it (cards + cohort rows, distinct labels; registry row, per-platform `not_instrumented`). Tests: one account in two apps once, passive/client-writable rows, feedback reservation, bare Voice and a day-0 open excluded, confirmed Voice turn and server learning outcome counted, same cohort as the legacy series, allowlist ∩ client-writable names = ∅; V10 golden ignores only the added key. `EXPLAIN ANALYZE` on local PostgreSQL with 50k accounts / 1M CME rows / 20k Voice sessions: weekly D1 legacy 10 ms, return 24 ms; all-time legacy 113 ms, return 4.0 s with `owner()`'s OR (planner AND-ed the `created_at` index per account) → **433 ms** after splitting ownership into two EXISTS. Analytics CI suite **99 passed, 196 subtests**; browser suite passed.

- 2026-11-12 — Task 4.2: [route chain](../../tests/test_pwa_pro_funnel_chain.py) on PostgreSQL — PWA Google sign-in, inline-event route (browse + buy attempts; a forged `pwa_pro_checkout_paid` is 422), PWA Lava start with `attempt_id`, provider webhook → ledger paid; a Telegram Mini App Lava payment in the same window stays out. Admin API: Overall and PWA 2 → 1 → 1 → 1, reversed 0, unlinked 0, no IDs or email; Android/Telegram `not_applicable`; a full refund webhook keeps paid and sets reversed 1. Conversion tab gains the «iPhone PWA Pro» panel (4 steps + reversed/unlinked rows, one-line note; 8 UZ/RU/TJ keys). Registry F8 metric → `covered`; flow stays `partial` (more/method/exit/dismiss/failed rows are stored, not projected). Analytics CI suite **96 passed, 196 subtests**; Lava + PWA auth **157 passed**; i18n + static **551 passed, 15 skipped**; browser suite passed (Overall UZ/RU/TJ × 390/1440 and the platform loop: panel under PWA only).

- 2026-11-12 — Task 4.1: `pwa_pro_attempt_funnel` reader + registry row; the V10 baseline test ignores only this added key (`ADDED_METRICS`) so legacy funnel values stay byte-identical. [F8 test](../../tests/test_admin_pwa_pro_funnel.py) covers matching-attempt paid, failed webhook/click/forged paid, two invoices, refund, unlinked, cohort window, ID-free output, row cap and per-filter states. Analytics + cache suites **110 passed, 5 skipped (Redis), 196 subtests**.

- 2026-11-12 — Task 3.4: [chain test](../../tests/test_analytics_platform_chain.py) completes 1/2/3 lessons through the signed Telegram, PWA cookie + CSRF and Android bearer routes on PostgreSQL and reads Course through the cookie-authenticated Admin API: each filter shows only its own count, Overall 6. Registry `course.completed_user_lessons` → `covered` on all three; `READ_PROJECTIONS.md` gains the per-platform definitions. UI half in `tests/e2e/admin_pwa_browser.py` (Telegram-tagged completion: Telegram 1, Android real 0, PWA no data). Analytics CI suite **90 passed, 196 subtests**; browser suite passed.

- 2026-11-12 — Task 3.3: Admin `app.js` renders `metric_states` (state label instead of value; unavailable cohort rows omitted; section reason + «Overall» hint), `attributed_since` per panel, the iPhone PWA card (opens only) and hides `not_applicable` version tables. Before this, Course and Funnel under a platform filter threw on missing Overall-only objects. 8 UZ/RU/TJ keys in `localization/ui/*/miniapp.json`; catalogs `--check` clean; i18n + static suites **551 passed, 15 skipped, 4065 subtests**; `tests/e2e/admin_pwa_browser.py` passes with a new 390 px loop over Android/Telegram/PWA × 7 tabs × UZ/RU/TJ (no overflow, state labels only).

- 2026-11-12 — Task 3.2 closed: Course `foundation` scoped for Telegram/PWA by the tagged start (A10), Android and PWA activation/sessions `not_instrumented` (A11); closing checks added (one account on three platforms counts once overall; two Android devices = one account, two devices). Analytics CI suite **94 passed, 196 subtests**; statistics cache/export and course analytics **38 passed, 5 skipped (Redis), 24 subtests**.

- 2026-11-12 — Task 3.2 step 3, Course: new `pwa_analytics_course_platform.py` scopes `features` and `completed_user_lessons`; tests cover the final-key rule, a nested lookalike, a pre-boundary lookalike, an untagged oversized completion and pre-key `no_data`. Analytics, baseline and cache suites **146 passed, 5 skipped (Redis), 196 subtests**.

- 2026-11-12 — Task 3.2 step 3, Platforms: PWA card under the PWA filter from the route-owned map dedupe prefix; registry adds `iphone_pwa` to the 21 platform-projection rows. Analytics suite **107 passed, 196 subtests**.

- 2026-11-12 — Task 3.2 step 3, Sources: code re-check found the F6 Android prefix forgeable from the Telegram route; registry Sources (entries, attribution) and the `subscription_entries` flow now report Android `not_instrumented`. No runtime change.

- 2026-11-12 — Task 3.2 step 3, Funnel: `transport` marker on the Telegram overview/event and Android manual openings; attempt funnel scoped per platform with `attributed_since`; a Telegram row with source `android_subscription` stays Telegram. Analytics CI suite **76 passed, 191 subtests**; checkout/funnel writer suites **177 passed, 3 skipped (PG-gated), 98 subtests**.

- 2026-11-12 — Task 3.2 step 3, Finance (Claude, continuing Codex's uncommitted patch): money payment keys and Lava lifecycle scoped per platform; registry filters/reasons updated (`partial` until 3.4 chain tests); `NEWLY_ATTRIBUTED` in the baseline test allows only the nine former `attribution_not_audited` money cells to change. The new [platform scope test](../../tests/test_admin_pwa_platform_scope.py) pins values and checks that the three platforms add up to Overall. CI analytics suite **72 passed, 191 subtests**; cache/refresh/read **60 passed, 5 Redis skipped** (no local `redis-server`). The `_v2` cache scope is not on main yet, so no new bump.

- 2026-11-12 — Task 3.2 step 2: verified adapters add a `client` payload field to existing lesson, practice, exam and mistake review writes. No new event, SQL operation, dedupe or learner response; omit the optional key if it would truncate a previously valid grading snapshot. Focused suites: **222 passed, 180 subtests passed**, two asyncpg cleanup warnings. Reader predicates and chain evidence are still pending.
- 2026-11-12 — Task 3.2 step 1: [Telegram map and event](../../app/main.py) reject caller PWA attribution at persistence, preserving ordinary campaign sources and dedupe; [PWA telemetry](../../app/api/miniapp_entitlements.py#L307) still writes its own transport and drops caller client claims. Focused route/parity/sales regressions: **34 passed, 29 subtests passed**. Old rows were not rewritten; the platform predicates must still reject historical lookalikes.
- 2026-11-12 — Task 3.1 added registry-driven `metric_states` and isolated eight V10 section scopes as `_v2`; experiments and basic/MCP contracts stayed unchanged. PostgreSQL/analytics/manual refresh/cache suite: **74 passed, 165 subtests passed**; five local Redis tests initially skipped and **all five passed** in a separate disposable Redis run. The original 162 snapshots remained identical after removing only the new additive state map. The [2.3 push](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/43132748403) and [PR](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/43132755458) workflows passed.
- 2026-11-12 — Task 2.3: the scratch [cosmetic push passed](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/43132137627) (`a74af1f4`); the [unmapped event push failed as intended](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/43132150012) (`5c2dcc2b`), naming `app/db/models/conversion_funnel_event.py` and `conversion_funnel_events:analytics_ci_unmapped_proof`. With both PostgreSQL test settings populated, the workflow suite passed locally (**65 tests, 171 subtests, no skips**). The scratch event is not in the PR.
- 2026-11-12 — Task 2.2 added the [stdlib checker](../../scripts/check_analytics_coverage.py) and [contract tests](../../tests/test_analytics_coverage_contract.py). It matched all 138 qualified event names and required exact flow changes or reviewed exemptions for scoped diffs. Coverage and baseline suites on fresh TCP PostgreSQL: **11 passed, 165 subtests passed**, no skips.
- 2026-11-12 — Task 2.1 added 84 metric keys, 29 projection metadata keys and 20 flow IDs. Schema validation passed; all 144 in-scope baseline responses match their declared keys. No `covered` status is asserted before the chain tests.
- 2026-11-12 — Task 1.2 froze the V10 matrix from unchanged `680761f1` and reproduced it in the planning worktree. Next: registry, task 2.1.
- 2026-11-12 — Re-audited and merged `origin/main` `680761f1`, including Li guest, Voice V8, feedback reservation and push. No analytics runtime patch. Strict OpenSpec validation passed; continue at 1.2.
- 2026-11-11 — Merged `main` `334368cc` and re-audited the platform × V10 chain (task 1.1). Adapted proposal, design, specs and tasks to the findings, the Desktop freeze and the Analytics → Monitoring order. The plan is ready for task 1.2.
- 2026-11-09 — Created and validated the OpenSpec change, added the owner's platform requirements, simplified the plan to 6 task groups, and turned this file into the shared context.

## History

The original long plan (phases 0–5, OpenSpec authoring handoff, per-feature contract) is preserved in git at `8ff505b3`. Its content now lives in the OpenSpec change and in `AGENTS.md`.

## Analytics → Monitoring → joint integration order

- **First:** deliver the Analytics Impact rule, coverage registry and scoped CI guard; continue metric repair in bounded packages. This prerequisite does **not** require finishing every Analytics report.
- **Then:** Monitoring reuses verified canonical user/platform/feature identifiers and compatible coverage/CI conventions. Keep business/KPI events separate from privacy-safe diagnostic incidents; no duplicate pipelines.
- **Finally:** one joint integration audit (not a third rebuild) checks both Impact/CI obligations, end-to-end Admin Analytics/Inbox coverage, dedup/privacy, nonblocking flows and affected regressions. Recheck the latest `main` and integrate tested changes sequentially.
