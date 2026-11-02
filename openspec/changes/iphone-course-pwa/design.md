# Design — reuse the existing Telegram Mini App as an iPhone PWA

## Baseline and goal

Source audit: `main@f791613c4377ffec2018cce3764cf81e80a6a765` (2026-11-02). Recheck HEAD before implementation. The learner UI lives in `app/static/course-v3.html` and child `course_v3_*.html`; `app/main.py` and `app/api/miniapp_*.py` contain learner routes. Existing Mini App auth relies on Telegram-signed `initData`. `app/api/native_oauth.py` already provides verified Google/Apple identity components for native clients but not a standalone browser session. Canonical `users.id`, account linking, course, payment and entitlements services already exist. `docs/UNIVERSAL_NATIVE_ACCOUNTS.md` documents the boundary.

**Outcome:** same Mini App learner screens and server state, launched and installed independently through iPhone Safari/Home Screen. Preserve working Telegram/native clients and server authority. No new course implementation or visual redesign.

## Minimal decisions

### 1. Keep one course frontend

Reuse current HTML, CSS, course JS and localization. Add the smallest browser-versus-Telegram adapter required by the audited API calls: authenticated request context, navigation/back action, Telegram-only SDK calls and host environment. Prefer shared code and isolated small patches; never clone thousands of lines into a second PWA course.

### 2. Secure browser login with existing identity services

Use existing verified Google/Apple subject resolution and account linking; add only the browser session/redirect handling that is currently missing. A purpose-limited cookie session must be Secure/HttpOnly, bound to canonical `users.id`, protected from CSRF, bounded by expiry/revocation and cleared on logout. Check OAuth state/redirect binding and installed PWA callback behavior. Do not pass native bearer refresh tokens into browser localStorage, fabricate Telegram IDs, auto-merge by email or accept unverified Telegram initData.

Telegram account owners with Pro/progress must be able to link their login explicitly with proper ownership proof and no duplicate reward; reuse the current identity-link service. Prefer no DB migration unless the reviewed session contract cannot represent browser state safely.

### 3. Shared course and billing services, not copied endpoints

Audit the **actual PWA-used** Mini App routes (some are defined directly in `app/main.py`), then add the smallest browser-authenticated adapter that calls the same existing lesson, practice, grade, access, subscription and account services. Existing Telegram endpoints must still verify Telegram initData. Browser-only users can have `telegram_id=NULL`; Telegram-only sends remain unavailable for such accounts.

Keep grading, completion proofs, protected content and entitlement checks on the server. Preserve free/trial/paid/pending receipt distinctions, payment review/dedupe, referral ownership and cross-platform progress. Adapt only browser-specific checkout/receipt return; do not redesign payment policy. Clear account-specific browser state on logout/switch.

### 4. Simple iPhone install surface; extras excluded

Serve a dedicated learner HTTPS entry. Use existing branding, safe-area layout and a small manifest/icon where useful. Apple/WebKit confirms iPhone Home Screen web apps **do not require a service worker**; therefore no new offline storage infrastructure is necessary in v1. Do not implement Web Push, new reminders or an analytics pipeline as part of this task. No Admin PWA authentication or service-worker scope reuse.

Test Safari vs Home Screen, login return, audio and mic permission, backgrounding, navigation, paywall return and session expiry. If a browser API is unavailable, report the limitation without pretending parity. Reuse UZ/RU/TJ canonical localization rules for any new fixed copy.


### 5. Preserve notification classes; defer only the Smart Web Push transport

The Smart Reminder canonical [Master Plan](../../../docs/smart-reminders/SMART_REMINDER_MASTER_PLAN.md) D10/P5 expressly defines iPhone learner PWA as **future V2** over the shared `users.id` engine. Prepare an adapter boundary, NOT a second scheduler or premature study send:

| Source/class | v1 PWA when open | Future background transport / policy |
| --- | --- | --- |
| `CourseUserNotification` course/ranking/motivation feed (`app/services/course_notification_service.py`) | Authenticated account-scoped inbox or existing safe read adapter; no inference that inbox read means push delivered | Existing category policy; Smart study coordination stays separate |
| Subscription/payment/limit/account notices (`notification_delivery_service.py` and current server account state) | Show canonical status plus any verified in-app notice actually stored. **Audit source coverage**: not every transactional message is necessarily in the course inbox | Preserve existing Android acknowledgement and Telegram fallback semantics, independently of D03 daily study limit. Future PWA transactional delivery requires its own reviewed adapter and eligibility |
| Smart study reminders | Settings may show the actual canonical account Smart preference and unsupported/not-registered iPhone channel; no PWA study sending in v1 | V2: installed Home Screen, genuine user-gesture OS permission, own subscription, service worker, server-owned job and chosen eligible channel; D01/D03/D05/D06/D07/D14 guards. No second scheduler, auto opt-in or fallback on unknown delivery |
| Ordinary bot feedback and release-feedback rating | Small server-eligible center dialog while learner is in PWA; no background push requirement | Keep original Telegram bot chat send/response path; never duplicate campaign or grant |

**Privacy/ownership:** A PWA cookie belongs to canonical `users.id`, but a Telegram bot DM requires a real linked `telegram_id`. Unsupported Safari/Web Push must remain unknown or unavailable, never silently selected by Smart. A PWA study adapter added in V2 must honor one logical account/day job, selection/dedup, explicit channel OFF, OS denial, revocation, verified target/deep link and existing conservative attempt/fallback ledger. Do not infer receipt/open from an inbox view.

### 6. Compact feedback center modal — reuse existing bot rules

Two separate **existing** families were reviewed: `app/services/bot_feedback_service.py` (feedback prompts, eligibility, bounded retries and one-time 30-minute access reward for eligible free accounts), and `app/services/release_feedback_service.py` (specific release campaign and 1–5 rating, optional comment and controlled reward/discount). These are not interchangeable.

For a PWA user, first audit whether the current record is eligible via canonical user ID. Telegram's current sender filters on a genuine `telegram_id`; a browser-only account needs a **small shared eligibility/response bridge** if required, NOT a recreated prompt scheduler or artificial Telegram ID. A linked account cannot receive duplicate claims or duplicate rewards from answering in Telegram and PWA. Do not force a feedback overlay during an active quiz/payment/lesson, or open just because the bot already sent a chat message.

The initial card stays centered, compact, dismissible and accessible (dialog role, focus restore, keyboard/escape, readable overlay and safe-area). Ordinary feedback first step offers appropriate positive/negative choices and moves to existing follow-up questions; release campaign uses actual rating and optional comment. Persist and rate-limit using current server services, observe paid-vs-free differences, and restore the course after dismissal/submission. New fixed copy still comes from canonical UZ/RU/TJ catalogs, not the sample Figma text.

### 7. Figma-first for **new** UI only

Editable [HSK AI PWA notifications and feedback Figma](https://www.figma.com/design/89fCM5GdjfBqcx0B9aQHOI) contains drafts of an inbox, settings presentation and both centered feedback dialogs with reusable `notification/item`, `setting/row`, `feedback/quick-question`, `feedback/release-rating` and button components. The palette comes from `app/static/course_v3_data/design-tokens.css`. **Figma used Inter because the system SF Pro font was unavailable in this editor; its font/copy/interaction samples need review before being used as code.** These Figma screens are NOT a separate app/UI redesign or approved runtime behavior. Use the exact approved component mapping saved in the single context handoff; reuse current Mini App screens with no redundant redraw. No Figma work counts as backend/code tests.

## Four implementation gates

- **P0 — focused code inventory:** verify actual frontend API, auth/account, notice/feedback source eligibility and Smart V2 policy boundaries, not a broad repo audit.
- **P1 — browser identity:** verified OAuth and secure session bridge, explicit account linking where needed, auth/CSRF/logout/ownership regressions.
- **P2 — frontend and API parity:** thin host adapter and only necessary browser routes; same business services, lessons, grading, Pro, required inbox and eligible compact feedback. Review new Figma UI before code.
- **P3 — iPhone and release QA:** Home Screen entry/icon/manifest, Safari/installed iPhone tests including in-app notifications, dialogs, voice/login/payment return; verify future Smart V2 channel remains OFF/unsupported and rollback works.

Detailed bounded implementation tasks are solely in [tasks.md](tasks.md); this design does not create another task ledger.

## Minimum test and rollback contract

| Area | Required proof |
| --- | --- |
| Security | Real provider sign-in/link, cookie + CSRF, expiry/logout/revocation, forged actor/Telegram initData denied, cross-user isolation |
| Course | Lesson/tests/homework/progress/grade, HSK tracks, Pro/free/pending/paid, no duplicate XP/referral |
| UI | Same Mini App rendering on Telegram and iPhone; UZ/RU/TJ; voice permission/fallback |
| iPhone | Safari and installed Home Screen: open, login return, resume, logout, course, payment return, keyboard/safe areas |
| Isolation | Telegram native initData works; Android/Desktop sessions and server rules remain unchanged |

Rollback should disable the new learner entry/browser session only. Never delete account, progress, purchase, identity or payment records. Preserve existing live client routes. Treat any schema migration, new provider setup, feature flags or dependencies as conditional on verified need, not automatic requirements.

## Explicit unknowns

Actual production origin/provider redirect configuration, live migration head, exact PWA iOS device behavior and provider payment return must be checked during implementation; this design is not device/test or production acceptance. Follow `AGENTS.md`, `AI_RULES.md`, `PROJECT_MEMORY.md`, `localization/README.md`, the `hsk-ai-ui` skill and [the single context](../../../docs/IPHONE_PWA_CONTEXT.md).
