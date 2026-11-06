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

### 4. Simple iPhone install surface and push-only worker

Serve a dedicated learner HTTPS entry. Use existing branding, safe-area layout and a small manifest/icon where useful. Register a push-only Service Worker at `/iphone-pwa/sw.js` with scope `/iphone-pwa/`; no offline cache or navigation interception is needed. Use feature detection and a direct learner action before requesting permission, because iOS Web Push requires an installed Home Screen web app and user gesture. Do not register a worker at `/`, where it could control Telegram or other clients. No Admin PWA auth/session/subscription reuse.

Test Safari vs Home Screen, login return, audio and mic permission, backgrounding, navigation, paywall return and session expiry. If a browser API is unavailable, report the limitation without pretending parity. Reuse UZ/RU/TJ canonical localization rules for any new fixed copy.


### 5. Preserve notification classes and add learner Web Push

The Smart Reminder canonical [Master Plan](../../../docs/smart-reminders/SMART_REMINDER_MASTER_PLAN.md) D01/D03/D05/D06/D07/D10/D14 and shared `users.id` job engine remain authoritative. Add a learner Web Push transport without creating a second notification or reminder scheduler:

| Source/class | v1 PWA when open | Future background transport / policy |
| --- | --- | --- |
| `CourseUserNotification` course/ranking/motivation feed (`app/services/course_notification_service.py`) | Existing authenticated in-app inbox | Queue one privacy-safe push per active learner PWA device/event; click opens the PWA course/inbox |
| Subscription/payment/limit/account notices (`notification_delivery_service.py` and current server account state) | Existing account-notice rows and current authoritative payment state | Additive PWA push; preserve Android acknowledgment and Telegram fallback semantics, independently of D03 study cap |
| Smart study reminders | Existing preference, consent, selected job/channel and attempts | PWA can be selected only with valid Smart consent + explicit OS/PWA capability, existing auto/manual routing and fresh job guards. No second scheduler, auto opt-in or fallback/replay on unknown delivery |
| Ordinary bot feedback and release-feedback rating | Small server-eligible center dialog while learner is in PWA; no background push requirement | Keep original Telegram bot chat send/response path; never duplicate campaign or grant |

**Privacy/ownership:** learner subscriptions bind to the authenticated PWA `DesktopDevice` and canonical `users.id`; Admin subscriptions remain isolated. Store endpoint hashes and encrypted endpoint/key material; push only generic localized text and a same-origin PWA target, then read detail from the authenticated server inbox. Push permission is always user-gesture initiated. For Smart, the general subscription does not create study consent; require the existing Smart preference/consent, selected-channel policy, active session/capability and one existing logical account/day job. Unknown outcomes remain non-replayable. In-app inbox read is never a push receipt.

### 6. Compact feedback center modal — reuse existing bot rules

Two separate **existing** families were reviewed: `app/services/bot_feedback_service.py` (feedback prompts, eligibility, bounded retries and one-time 30-minute access reward for eligible free accounts), and `app/services/release_feedback_service.py` (specific release campaign and 1–5 rating, optional comment and controlled reward/discount). These are not interchangeable.

For a PWA user, first audit whether the current record is eligible via canonical user ID. Telegram's current sender filters on a genuine `telegram_id`; a browser-only account needs a **small shared eligibility/response bridge** if required, NOT a recreated prompt scheduler or artificial Telegram ID. A linked account cannot receive duplicate claims or duplicate rewards from answering in Telegram and PWA. Do not force a feedback overlay during an active quiz/payment/lesson, or open just because the bot already sent a chat message.

The initial card stays centered, compact, dismissible and accessible (dialog role, focus restore, keyboard/escape, readable overlay and safe-area). Ordinary feedback first step offers appropriate positive/negative choices and moves to existing follow-up questions; release campaign uses actual rating and optional comment. Persist and rate-limit using current server services, observe paid-vs-free differences, and restore the course after dismissal/submission. New fixed copy still comes from canonical UZ/RU/TJ catalogs, not the sample Figma text.

### 7. Figma-first for **new** UI only

Editable [HSK AI PWA notifications and feedback Figma](https://www.figma.com/design/89fCM5GdjfBqcx0B9aQHOI) contains drafts of an inbox, settings presentation and both centered feedback dialogs with reusable `notification/item`, `setting/row`, `feedback/quick-question`, `feedback/release-rating` and button components. The palette comes from `app/static/course_v3_data/design-tokens.css`. **Figma used Inter because the system SF Pro font was unavailable in this editor; its font/copy/interaction samples need review before being used as code.** These Figma screens are NOT a separate app/UI redesign or approved runtime behavior. Use the exact approved component mapping saved in the single context handoff; reuse current Mini App screens with no redundant redraw. No Figma work counts as backend/code tests.

## Four implementation gates

- **P0 — focused code inventory:** verify actual frontend API, auth/account, notice/feedback source eligibility and Smart V2 policy boundaries, not a broad repo audit.
- **P1 — browser identity:** verified OAuth and secure session bridge, explicit account linking where needed, auth/CSRF/logout/ownership regressions.
- **P2 — frontend and API parity:** thin host adapter and only necessary browser routes; same business services, lessons, grading, Pro, in-app notices, push subscription controls and eligible compact feedback.
- **P3 — iPhone and release QA:** Home Screen entry/icon/manifest, Safari/installed iPhone tests including push permission/delivery/revoke, dialogs, voice/login/payment return, Smart guards and rollback.

Detailed bounded implementation tasks are solely in [tasks.md](tasks.md); this design does not create another task ledger.

## Minimum test and rollback contract

| Area | Required proof |
| --- | --- |
| Security | Real provider sign-in/link, cookie + CSRF, expiry/logout/revocation, forged actor/Telegram initData denied, cross-user isolation |
| Course | Lesson/tests/homework/progress/grade, HSK tracks, Pro/free/pending/paid, no duplicate XP/referral |
| UI | Same Mini App rendering on Telegram and iPhone; UZ/RU/TJ; voice permission/fallback; notification controls |
| iPhone | Safari and installed Home Screen: open, login return, resume, logout, course, payment return, keyboard/safe areas, push support/permission/subscription/click/revoke |
| Isolation | Telegram native initData works; Android/Desktop sessions and server rules remain unchanged |
| Push security | Same-origin/CSRF, canonical owner/device, encrypted subscription, no private payload, kill switch OFF path, endpoint expiry/revoke and duplicate protection |
| Smart Reminder | Existing master/consent/manual channel/one-day job guards; no PWA auto-enrollment, daily-cap change, duplicate scheduler, or replay after unknown attempt |

Rollback disables the learner PWA push sender and PWA entry independently, revokes/invalidates learner PWA subscriptions as needed, and retains the additive schema until a verified safe downgrade is available. It never disables Android/Telegram delivery or deletes account, progress, purchase, identity, payment, or Smart Reminder evidence. All PWA push flags remain default OFF in code and no deployment configuration is changed here.

## Explicit unknowns

Actual production origin/provider redirect configuration, live migration head, exact PWA iOS device behavior and provider payment return must be checked during implementation; this design is not device/test or production acceptance. Follow `AGENTS.md`, `AI_RULES.md`, `PROJECT_MEMORY.md`, `localization/README.md`, the `hsk-ai-ui` skill and [the single context](../../../docs/IPHONE_PWA_CONTEXT.md).
