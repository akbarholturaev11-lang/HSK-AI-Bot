# HSK AI — Li Panda Onboarding | IMPLEMENTATION CONTEXT

> **BU FAYL — YAGONa LIVE TASK HANDOFF/JURNAL.** Yangi chat yoki Codex agent shu faylni o'qib real davom ettiradi. Bajarilmagan ishni bajarilgan deb belgilash TAQIQLANADI.
>
> **Sister document:** [PRODUCT_GOAL.md](PRODUCT_GOAL.md) — final product behavior, fixed scope, 23-state demo, acceptance criteria. Maqsad bu yerda qayta ixtiro qilinmaydi.
>
> **Last verified:** 2026-11-08; **branch:** `feature/li-onboarding-handoff-20261108`; **branch baseline:** `main@4ca0d2d1c7e89e517f6d9e6ab781c12963287b9a`; **source:** GitHub `akbarholturaev11-lang/HSK-AI-Bot`.
>
> **REAL IMPLEMENTATION STATUS: NOT STARTED.** 2026-11-08 kuni faqat source audit va task hujjatlari tayyorlangan. **0 ta runtime/DB/API/UI file o'zgargan; 0 ta migration; 0 ta app/test command bajarilgan.** Boshqa agent hech bir bosqichni "done" deb taxmin qilmasin.

## 0. Yangi chatni boshlash — shu tartib majburiy

1. Repository `akbarholturaev11-lang/HSK-AI-Bot`ni och, **branch `feature/li-onboarding-handoff-20261108`** mavjudligini va uning remote HEAD SHA'sini tekshir. Default `main`dan ko'r-ko'rona davom etma. Local workspace allaqachon dirty bo'lsa user o'zgarishlarini saqla; rebase/reset/force yo'q.
2. `AGENTS.md`, `AI_RULES.md`, `PROJECT_MEMORY.md`, **shu fayl**, [`PRODUCT_GOAL.md`](PRODUCT_GOAL.md), `localization/README.md`, `.agents/skills/hsk-ai-ui/SKILL.md` va scoped auth/Smart Reminder rules ni o'qi.
3. **Current branch HEAD'ni `main` bilan solishtir:** code diff/commits, migrations current head, related tests; loggi statusga emas real diffga ishonsin. Boshqa agent allaqachon o'zgartirgan bo'lsa hammasini qayta ko'rib, shu jurnalni real holatga mosla.
4. Demo reference: oldingi chatdagi `HSK_AI_CODEX_HANDOFF(1).zip`dan `DEMO_REFERENCE_ONLY.html`ni topib SHA-256 `767c2de59116229dab9304e3036ae589399379340013f1d137eae7df82644b30` bilan solishtir. Undagi `SCREEN_MAP.md`, `CODEX_TASK.md` foydali audit attachment; repo runtime manbasi emas. **Demo hozir GitHub branch'ida yo'q.** Manba topilmasa exact copy/visual fidelity done deb aytma.
5. Quyi `CURRENT STATUS` va `NEXT ACTION`ni tekshir. Faqat undan keyin code ishlari davom etsin. Yangi session avvalgi xatolarni takrorlamasin.
6. Har bir **haqiqiy** muhim code slice/migration/test tugagach `CURRENT STATUS`, `VERIFIED CODE CHANGES`, `TEST EVIDENCE`, `NEXT ACTION`, `OPEN RISKS`ni **shu fayl ichida** yangila va kod bilan **o'sha branch commit**da saqla. Har bir token/CSS micro-editni emas, tekshiriladigan fayl/behavior bo'lagini qayd et.
7. Yangi chatga qisqa topshiriq: **"`feature/li-onboarding-handoff-20261108` branch'da `docs/onboarding-li/PRODUCT_GOAL.md` va `docs/onboarding-li/IMPLEMENTATION_CONTEXT.md`ni o'qi. Hozirgi HEAD/diff/testlarni tekshir, jurnalning NEXT ACTION joyidan davom et, har verified code slice'dan so'ng jurnalni actual sha va test evidence bilan yangila. `main`ni o'zgartirma, release qilma."**

## 1. CURRENT STATUS — faqat tekshirilgan holat

| Slice | Status at last verification | Evidence / note |
| --- | --- | --- |
| P0 — repo audit/documentation | **Docs prepared; CLI baseline NOT run** | 2026-11-08 GitHub main SHA audit + two handoff files only |
| P1 — 23-state shared visual UI | **NOT STARTED** | Demo reference is separate attachment |
| P2 — real loading state everywhere | **NOT STARTED** | Global rule specified, no runtime edits |
| P3 — PWA/Telegram auth/draft | **NOT STARTED** | Existing endpoints audited |
| P4 — multi-goal/time/focus/streak schema | **NOT STARTED** | Existing profile has scalar `goal`; no migration |
| P5 — real HSK track/lesson | **NOT STARTED** | Existing course routes audited |
| P6 — Pro offer/trial activation | **NOT STARTED** | Existing Telegram trial endpoint, PWA gap |
| P7 — 48h PWA trial push | **NOT STARTED** | Existing push engine; actual flags unknown |
| P8 — streak ↔ Smart Reminder | **NOT STARTED** | Existing Smart planner; integration gap |
| P9 — analytics + canonical locales | **NOT STARTED** | Current analytics/i18n infra audited |
| P10 — regression, screenshot, device QA | **NOT STARTED** | No app tests executed in this docs-only session |

### VERIFIED CODE CHANGES

- **Runtime code, schema, migrations, endpoints:** none.
- **Documentation-only commits:** `docs/onboarding-li/PRODUCT_GOAL.md` created in this branch by commit `6a09d036e7c785d8f4d3df846fa42e7c8b5700a4`; this journal created subsequently. Confirm GitHub branch diff/commit SHA before relying on this metadata.
- Do **not** conflate audit findings, source references, earlier chat task prose, fake/demo UI, or planned designs with written/tested production code.

### TEST EVIDENCE

- Executed unit/API/Playwright/i18n commands in this documentation session: **none**.
- GitHub `fetch_file`/read-only code inspection conducted; reading test names does **not** mean tests passed.
- User device/iOS Home Screen push, env credentials, VAPID readiness and production delivery: **not verified**.
- Documentation can be manually checked via remote GitHub `fetch_file` + compare commits after creation; that does not test app behavior.

## 2. Audited current code — facts from `main@4ca0d2d`

The paths below existed and were reviewed **read-only** on 2026-11-08; recheck fresh code before editing.

### Frontend / identity / onboarding
- `app/static/course_v3_onboarding.html`: existing shared Mini App + PWA course onboarding (welcome plus track/level/one goal); book image handling includes actual JPEGs.
- `app/static/course-v3.html`: checks `onboarding_completed === false` on course entry; after-first-lesson setup asks `daily_minutes` and `preferred_focus`. It also has a prior explicit rule suppressing Pro/trial immediately after onboarding, so the demo offer changes this behavior intentionally; avoid second overlapping paywall.
- `app/static/iphone-pwa-login.html`, `app/static/iphone-pwa-login.js`: real login/provider browser flows; PWA auth cookies/callback and return destination must be preserved.
- `app/api/pwa_auth.py`: `/iphone-pwa/onboarding`, PWA auth `PwaAuthService.actor` vs `mutation_actor` (cookie + CSRF); POST `/api/v3/pwa/onboarding`; existing provider and push endpoints.
- `app/main.py`: `/api/miniapp/onboarding` POST and `/api/miniapp/onboarding/status` GET with signed `X-Telegram-Init-Data` check. Common `CourseMiniAppOnboardingService.complete`; status GET helps reconcile uncertain writes. PWA and Mini App share frontend but **not authentication trust mechanism**.
- Telegram already verified account should not be asked for fake signup; existing account/Pro/progress should never be reset on a mere revisit.

### Course / goal / daily plan / streak
- `app/db/models/course_miniapp_profile.py`: scalar `goal`, `daily_minutes`, `preferred_focus`, `goal_chosen_at`, `current_streak`, `longest_streak`; **no confirmed `goals_json` or `streak_target_days` yet**.
- `app/services/course_miniapp_profile_service.py`, `app/api/miniapp_preferences.py`, `app/services/learning_signals.py`: scalar goal consumers; migration and serialization backward compatibility needed.
- `app/services/daily_plan_service.py`: goal-specific weighting; frozen daily-plan keys/schema; do not retroactively rebuild user's already-frozen current plan.
- `app/services/course_gamification_service.py`: XP award drives canonical `current_streak`, `longest_streak`, `last_activity_date`; missed/future day streak is display-corrected. Goal selection must not award activity.
- `app/services/course_track_service.py` / course track endpoints: server `live_levels`, allowed state, HSK3.0 preview vs real lesson entitlement; trial does not automatically unlock HSK 3.0. Do not route old users to destructive `lesson_1` start.
- Book assets **actual repo images**: `app/static/assets/hsk20-course-books.jpg`, `app/static/assets/hsk30-course-books.jpg` (runtime cache version `v=20261003c` observed). Fake demo CSS book should be removed.

### Pro trial / PWA push — the exact implementation gap
- `app/services/trial_reminder_service.py`: `REMINDER_DAYS=(2,0)`; due check uses `days_left=max(0,(ends_at-now).days)`, i.e. floor, **not precise 48-hour due**; existing Inbox row uses `dedupe_key="trial_reminder:{ends_at.date()}:{days_left}"` and `pwa_push_suppressed=True`.
- `app/services/notification_delivery_service.py`: Android-first, Telegram fallback; learner PWA outbox may be additionally enqueued on existing notice rows. **Do not simply remove `pwa_push_suppressed=True` blindly**: inspect overlapping `NotificationDeliveryService.deliver` enqueue, duplicate channels and return status; design exactly-once user-visible 48h PWA notice.
- `app/services/learner_pwa_push.py`: opt-in PWA subscribers, outbox, dedupe, dispatch; generic lock-screen notice by default; end user auth/endpoint binding and session checks.
- `app/api/pwa_auth.py`: GET `/api/v3/pwa/push/status`, POST `/push/subscribe`, POST `/push/revoke`; subscription requires cookie + CSRF + same origin; proper device binding.
- `app/static/iphone-pwa-sw.js`: PWA service worker push handling, click-to-open authenticated Inbox; cache versioning must be updated with changed asset references.
- `app/main.py` `_background_scheduler`: every ~60s checks trial reminders; `_admin_pwa_apple_push_scheduler` dispatches learner outbox about every 60s if configured.
- `app/config.py`: `PWA_PUSH_ENABLED=False` and `PWA_PUSH_SEND_ENABLED=False` as defaults; **production configuration not audited**, so no guarantee that push is active.
- `app/api/miniapp_entitlements.py`: trial status/start uses real signed Telegram identity; **PWA needs its cookie + CSRF authenticated service adapter** (not insecure Telegram initData mimic).
- Trial eligibility, paid and previously used trials must obey existing services. Provider acceptance != notification displayed.

### Smart Reminder / legacy motivation collision
- `app/services/smart_reminder_policy.py`: `PolicyContext` has verified `studies`, `daily_goal_xp`, `plan_completed`, IANA timezone, quiet hours, manual/auto time and consent; **no explicit streak-target field**.
- `app/services/smart_reminder_policy_context.py`: verified XP/progress, scoped history and plan context; extend here rather than compute stale client-only streak.
- `app/services/smart_reminder_planner.py`, `smart_reminder_destination.py`, `smart_reminder_pwa.py`, `smart_reminder_preferences.py`: per-user/day ownership, PWA delivery, consent and routing. PWA subscription alone is not Smart Reminder consent.
- `app/db/models/smart_reminder.py`: source consent accepts 'telegram'/'android' with additional PWA transport based on Smart ON + subscriber; do not silently invent a conflicting third user opt-in state.
- `app/services/motivation_reminder_service.py`: existing Telegram evening streak/goal reminders; today's verification uses `last_activity_date` and current streak, with special D1 recovery and routing holds. Must avoid duplicate reminders with new Smart cross-channel state.

### Analytics/i18n/testing audit
- `app/services/course_miniapp_analytics_service.py` and `app/db/models/course_miniapp_event.py`: existing tracked event list/dedupe (PWA needs cookie+CSRF transport).
- `localization/ui/{ru,uz,tj}/{course,common,miniapp}.json`: canonical copy sources; `scripts/i18n_build_all_catalogs.py --write` then `--check` required for actual UI changes.
- Inspected test paths: `tests/test_pwa_browser_auth.py`, `tests/test_course_miniapp_onboarding.py`, `tests/test_course_track_service.py`, `tests/test_daily_plan_service.py`, `tests/test_pro_trial_service.py`, `tests/test_trial_risk_service.py`, `tests/test_trial_reminder_service.py`, `tests/test_smart_reminder_policy.py`, `tests/test_smart_reminder_pwa.py`, `tests/test_course_gamification_service.py`, `tests/test_motivation_reminder_service.py`, `tests/test_iphone_pwa_asset_versions.py`, `tests/test_iphone_pwa_navigation_contract.py`.
- **No tests were executed as part of this audit**, including no full local baseline (GitHub tool reading only).

## 3. NEXT ACTION — immediate planned work

**P0 before P1 code:**

1. Refresh repo SHA and branch diff, confirm two docs and original demo availability/checksum, check local working tree and migration head.
2. Read required project rules/UI skill and `localization/README.md`; examine `course_v3_onboarding.html` vs demo side by side, create a concise 23-state-to-source mapping **within this journal or implementation PR** (do not add a competing progress file).
3. Run and record baseline targeted tests as environment permits; record the actual command, result and blockers (especially Auth, course track, preferences, PWA push, Smart Reminder and i18n).
4. Implement **P1** shared visual shell/state machine, source-verified demo copy/assets and **P2** universal loading states in small reviewable commits. Avoid changing real account/Pro/trial while only UI renders.
5. Then implement P3–P8 in dependency order, keeping migration/consent/auth/legacy guards; update this file after **every verified code slice**.
6. Commit updated journal together with code, not minutes later, and verify remote branch state. Do **not** treat a successful commit as tested/released.

## 4. Open risks / facts still to verify (not invented)

- Exact demo asset is a prior conversation artifact, not yet committed to repo. Its availability/hash must be checked in next agent session. **If absent, visual/text "1:1" acceptance is blocked**.
- Current database Alembic head, local dependency/test environment and working-tree conflicts have **not** been checked.
- PWA Web Push is feature-flagged; production VAPID/config and actual installed iOS permission unknown.
- Trial 48-hour scheduler and durable send are **not** confirmed; old `.days` logic has a boundary bug; dual push/inbox delivery may duplicate without carefully unified ownership.
- PWA auth trial start may not exist under cookie+CSRF; do not reuse Telegram endpoint insecurely.
- Multi-goal + streak target requires additive schema and downstream consumer tests; analytics/event allowlist may need migration/validation.
- Existing Pro onboarding suppression and legacy motivation delivery overlap new demo behavior; test both.
- Smart Reminder has careful rollout/shadow/admission/consent/quiet/no-retry semantics: never turn ON or bypass them just to send streak notices.
- PWA push device eligibility and service worker cache update may require real-device QA; failed provider doesn't prove failed display and accepted provider doesn't prove success.
- Some `main` code may move before implementation; compare current code and update this audit section if materially changed.

## 5. Checkpoint format — update AFTER implemented code, not merely a plan

Append **one checkpoint per meaningful verified slice** and update sections 1/3/4:

```text
### YYYY-MM-DD HH:MM (+timezone) — P# <slice name>
Base HEAD: <sha>; working branch: <name>; new commit: <sha or UNCOMMITTED>
Actual changed files: <exact paths>
Actual behavior in runtime: <specific observed behavior and API/schema contract>
Migration: <revision or none>; rollback: <how>; existing user impact: <facts>
Tests EXECUTED: <exact command> -> PASS / FAIL / NOT RUN + counts/output
Manual/visual/device evidence: <proof or NOT VERIFIED>
Regressions/risks: <remaining exact risks>
Next single action: <specific file/step to work on>
```

**Rules:** Mark PASS only after command output, NOT RUN when not executed, distinguish unit/CI/device/prod. Every feature claim must be tied to an actual committed file and test/evidence. Do not copy secrets, endpoints, user data, raw auth tokens or private admin credentials. Small CSS/typo changes can share a checkpoint; do not duplicate full Git history. Important stable architectural decisions go to `PROJECT_MEMORY.md` according to `AI_RULES.md`, not as competing diary. If a test fails or rollback occurs, revise CURRENT STATUS rather than keeping false done.

## 6. CHRONOLOGICAL CHECKPOINTS

### 2026-11-08 — Documentation/structure only

- Base main HEAD verified: `4ca0d2d1c7e89e517f6d9e6ab781c12963287b9a`.
- Created temporary work branch `feature/li-onboarding-handoff-20261108` from that SHA.
- Added `docs/onboarding-li/PRODUCT_GOAL.md` — explicit 23-state final goal, original book JPG exception, all server loading UX, real PWA+Mini App auth, multi-goal/time/focus/streak, 48h PWA push and Smart Reminder integration, DoD/test scopes.
- Added **this** `docs/onboarding-li/IMPLEMENTATION_CONTEXT.md` — factual audit, not code implementation, current status, next session instructions.
- Real code changed: **NONE**. App migrations/tests/visual QA: **NOT RUN**. Production deployment: **NO**. Main push/merge: **NO**.
- **Next:** P0 environment/test baseline + SHA-verified demo, then P1/P2 implementation.
