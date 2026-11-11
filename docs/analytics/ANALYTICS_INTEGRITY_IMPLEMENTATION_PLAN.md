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
| OpenSpec change | `openspec/changes/hsk-ai-analytics-integrity/` | Re-planned on `main` `334368cc`; passes `openspec validate --strict` |
| Checklist | `.../tasks.md` | Only checklist; 1.1 done |
| Coverage registry | `docs/analytics/FEATURE_ANALYTICS_COVERAGE.json` | Not created (task 2.1) |
| CI guard | `.github/workflows/analytics-integrity.yml` | Not created (task 2.3) |
| Agent rule | `AGENTS.md` | Active; enforcement status still "planned" |
| Admin readers | `app/admin_api/pwa_analytics*.py`, `pwa_metrics.py` | Unchanged |
| Monitoring requirements | `docs/monitoring/REQUIREMENTS.md` | Follows this work; reuses its identifiers (§7, §11) |

## Current state — 2026-11-11

- Planning only. No runtime code has changed.
- The plan was re-audited and adapted on `main` `334368cc` (2026-11-11). Task 1.1 is done: the audit table, the V10 metric key list and the decisions are below.
- **Ready to start implementation.** Next step: task 1.2, the V10 regression fixture on unchanged `main`. Then tasks 2.1–2.3, the registry, checker and CI, before any metric repair.
- PR [akbarholturaev11-lang/HSK-AI-Bot#285](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/pull/285) carries the planning artifacts only.

## Platform scope

| Platform | Admin filter | Role in this work |
|---|---|---|
| Android Play + Direct | `android` | Target. No Play/Direct split: the channel is not in analytics rows (audit row A9) |
| Telegram Mini App | `telegram` | Target |
| iPhone PWA | `iphone_pwa` | Target |
| macOS / Windows | `macos`, `windows` | Development freeze. Existing metrics kept; registry status only |

## Audit — task 1.1, `main` `334368cc`, 2026-11-11

**Status values:**
- `verified`: code and test cited.
- `to_verify`: code cited, test still missing. The test is added by the task named in the row.
- `gap`: verified in code that no trustworthy platform signal exists.

`course_miniapp_events` is abbreviated to CME. The default CME source is `course_miniapp` (`course_miniapp_analytics_service.py:65`).

### Activity and learning

| # | Flow / metric | Platform | Writer (code) | Platform signal | Admin reader → section | Status |
|---|---|---|---|---|---|---|
| A1 | App open | Android | `desktop_auth_service.py:1392-1420` `android_first_open` / `android_app_opened`, source `android_app` | event-name prefix | `pwa_analytics_platforms.py` → Platforms | `verified`: `test_android_analytics_service.py`, `test_admin_pwa_read.py` |
| A2 | Mini App presence | Telegram | `desktop_download.py:159` → `user_client_presence` surface `telegram_miniapp` | surface | Platforms | `verified`: `test_user_device_inventory_service.py` |
| A3 | Course map open | Telegram | `main.py:2909-2931` `miniapp_opened`, source = query `source` or `course_v3`; `main.py:5706` source `course_miniapp` | none exclusive: query text is free | Course `retention` (mixed with A4) | `gap` |
| A4 | Course map open | PWA | `/api/v3/pwa/map` (`main.py:2994`) → `main.py:2745,2921-2931` `miniapp_opened`, source `pwa_course_v3`, dedupe prefix `pwa-course-v3:` | source, server-fixed on the PWA route | Not read per platform (`iphone_pwa` → `not_instrumented`); counted in Course `retention` | `to_verify`: source seeded in `test_pwa_learning_parity_postgres.py`, no reader test (3.2) |
| A5 | PWA sign-in device | PWA | `pwa_auth_service.py:338-352` `desktop_devices.platform='pwa'`; `last_seen_at` set only at mint | platform `pwa` | Not read by V10 | `gap` as activity: sign-in time, not use |
| A6 | Lesson started | Telegram + PWA | `course_miniapp_lesson_flow_service.py:1596`, default source; routes `miniapp_entitlements.py:742` (Telegram), `:761` (PWA) | none | `COURSE_EVENTS`, features, activation → Overview, Course | `gap` |
| A7 | Lesson started | Android | No writer. Android loads lessons by GET `/api/v3/android/course/lesson/{order}`. Readers list `android_lesson_started`, which has no writer in `app/` or `android/` | — | Counted in `COURSE_EVENTS`, never written | `gap` → `not_instrumented` |
| A8 | Lesson completed | Android | `desktop_course_service.py:727-731` `lesson_completed`, source `android_course` | source | Overview, Course completed accounts and lessons | `verified`: `test_android_course_api.py:405` |
| A9 | Lesson completed | Telegram + PWA | Shared `main.py:3495-3498`, source hard-coded `course_v3` | none | Overview, Course | `gap` |
| A10 | Starter 0 / foundation | all three | `miniapp_entitlements.py:294` (`pwa_course_v3` / `course_v3`), `android_course_service.py:394` (`android_course`) | source | Course `foundation` | `verified`: `test_pwa_learning_parity_postgres.py`, `test_android_foundation_api.py` |
| A11 | Lesson-flow telemetry | PWA | `/api/v3/pwa/event` `miniapp_entitlements.py:307-340`, source `pwa_course_v3`, payload `transport: iphone_pwa` set by the server | server-set transport | Course activation | `verified`: `test_pwa_learning_parity.py` |
| A12 | Lesson-flow telemetry | Telegram | `/api/miniapp/event` `main.py:6628-6735`: client-supplied source, payload copied by `trusted_client_payload` (`course_miniapp_analytics_service.py:39-44`) | none trusted; client can send `pwa_course_v3` / `transport` | Course activation | `gap` |
| A13 | Practice training / test | Android + Telegram | `course_miniapp_practice_service.py:87,635,800,825` (default source / `smart_practice_v2`). Android routes `android_features.py:1379,1414` call the same service | none | Course `features.practice` / `tests` | `gap`. Readers also list `android_practice_*`: no writer |
| A14 | HSK exam | all three | `course_hsk_exam_service.py:474,688`, source `course_hsk_exam`; routes `android_features.py:1458,1496`, `pwa_auth.py:928`, Telegram `/api/v3/exams/*` | none | Course `features.tests` | `gap` |
| A15 | Mistake review | all three | `course_mistake_service.py:1315,1501,1705,1935`, default source; routes `android_features.py:1568-1616`, `pwa_auth.py:820` | none | Course `features.mistakes` | `gap` |
| A16 | Voice minutes | all three | `voice_practice_service.py:759` `voice_practice_sessions`, no platform column. PWA voice CME rows carry `transport: iphone_pwa` | none on the session | Course `voice`, `voice_minutes` | `gap` |
| A17 | AI usage, chat | all three | `ai_usage_events.source` is the feature (`qa`, …); `messages` has no platform column | none | Course `ai`, `chat`; Finance AI cost | `gap` |
| A18 | Telegram → PWA / Play handoff | Telegram | `pwa_auth.py:2181-2239` `pwa_handoff_issued` / `_completed`; `main.py:6762` `android_play_opened` | event name | Existing basic Statistics: `pwa_read.py:120`, `android_analytics_service.py:48`. Not V10 | `verified`: `test_pwa_telegram_handoff.py`, `test_android_analytics_service.py`. Keep in the existing consumer |
| A19 | Android Play / Direct channel | Android | `android_app_opened` payload is only `platform`, `app_version`, `device_id` (`desktop_auth_service.py:1405-1420`); `desktop_devices` has no channel column | none | — | `gap` → combined Android only |
| A20 | Desktop activity | macOS, Windows | `desktop_*` events, `DesktopAnalyticsService._row_platform` | payload / source | Platforms | Existing, frozen: registry status only |

### Funnel, Finance and Sources

| # | Flow / metric | Platform | Writer (code) | Platform signal | Admin reader → section | Status |
|---|---|---|---|---|---|---|
| F1 | `checkout_opened` | PWA | `pwa_auth.py:1700-1715,1853`, payload `transport: iphone_pwa` | server-set transport | Funnel `attempt_funnel` | `verified`: `test_pwa_browser_auth.py:3370` |
| F2 | `checkout_opened` | Android | `desktop_subscription_service.py:151-166` (source `android_subscription` or `android_*` origin, attempt prefix `android-`); `lava_checkout.py:165` (attempt `android-lava-<id>`) | source and attempt prefix | Funnel | `verified`: `test_android_lava_checkout.py:84`, `test_android_features_api.py` |
| F3 | `checkout_opened` | Telegram | `main.py:6335,6486`, source `subscription_miniapp` or client mode/source | none; only by elimination (not F1, not `android_` / `desktop_`) | Funnel | `to_verify` (3.2) |
| F4 | Payments (Finance, funnel paid) | all | `payments.source`: `miniapp` (`subscription_miniapp_service.py:316,416`); `iphone_pwa` (`pwa_auth.py:1912`); `android` / `desktop` (`desktop_subscription_service.py:399`); Lava copies the invoice source `miniapp` / `pwa` / `android` (`lava_checkout.py:202,248,338` → `lava/ledger.py:194`); bot default `telegram_bot` | source. PWA has two values: `iphone_pwa` and `pwa` | Finance `money_metrics`: no platform predicate today | `to_verify` (3.2) |
| F5 | Lava lifecycle | all | `lava_invoices.source` `miniapp` / `pwa` / `android` | source | Finance `lava` | `to_verify` (3.2) |
| F6 | Subscription entries | Android | `android_features.py:1348` `android_subscription`; `ANDROID_CHECKOUT_ORIGIN_SOURCES` (`android_*`) | source prefix | Sources (`source_group` `android_%`) | `verified`: `test_android_features_api.py` |
| F7 | Subscription entries | PWA, Telegram | `pwa_auth.py:1689` `data.source or "iphone_pwa"` and `main.py:6322`, both client-supplied; `subscription_entry_events` has no payload column | none | Sources | `gap` (a fix needs a schema change: out of scope) |
| F8 | PWA Pro inline funnel | PWA | inline events, `lava_checkout._start` `pwa_pro_checkout_started`, `lava/ledger.py` `pwa_pro_checkout_paid`, `lava_invoices.pwa_inline_attempt_id` | PWA-only | No reader | `to_verify` (task 4) |

### V10 metric keys on `334368cc` (registry seed for 2.1)

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
- **experiments:** out of scope (overall only)
- Home and overview under a non-overall filter currently return the platform projection.

### Planned platform outcome per section (drives 3.2)

| Section | Android | Telegram | iPhone PWA |
|---|---|---|---|
| Platforms | existing (A1) | existing (A2) | new card from A4, after A3/A12 spoofing is closed |
| Course | completions and foundation (A8, A10). `lesson_started` → `not_instrumented` (A7). Practice, exam and mistakes after the `client` key (A13–A15) | lesson, practice, exam and mistakes after the `client` key (A6, A9, A12–A15). Foundation now (A10) | the same as Telegram, plus flow telemetry (A11) |
| Funnel | F2 | F3 after test | F1 |
| Finance | F4/F5 `android` | F4/F5 `miniapp`, `telegram_bot` | F4/F5 `iphone_pwa` + `pwa` |
| Sources | F6 | `not_instrumented` (F7) | `not_instrumented` (F7) |
| AI, chat, voice minutes | `not_instrumented` (A16, A17) | the same | the same |
| Ledger, marketing, traffic | `not_applicable` (company-wide) | the same | the same |

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

## Session log (newest first, one or two lines each)

- 2026-11-11 — Merged `main` `334368cc` and re-audited the platform × V10 chain (task 1.1). Adapted proposal, design, specs and tasks to the findings, the Desktop freeze and the Analytics → Monitoring order. The plan is ready for task 1.2.
- 2026-11-09 — Created and validated the OpenSpec change, added the owner's platform requirements, simplified the plan to 6 task groups, and turned this file into the shared context.

## History

The original long plan (phases 0–5, OpenSpec authoring handoff, per-feature contract) is preserved in git at `8ff505b3`. Its content now lives in the OpenSpec change and in `AGENTS.md`.

## Analytics → Monitoring → joint integration order

- **First:** deliver the Analytics Impact rule, coverage registry and scoped CI guard; continue metric repair in bounded packages. This prerequisite does **not** require finishing every Analytics report.
- **Then:** Monitoring reuses verified canonical user/platform/feature identifiers and compatible coverage/CI conventions. Keep business/KPI events separate from privacy-safe diagnostic incidents; no duplicate pipelines.
- **Finally:** one joint integration audit (not a third rebuild) checks both Impact/CI obligations, end-to-end Admin Analytics/Inbox coverage, dedup/privacy, nonblocking flows and affected regressions. Recheck the latest `main` and integrate tested changes sequentially.
