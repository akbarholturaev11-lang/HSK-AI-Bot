# Tasks — lean implementation plan for iPhone Course PWA

**Planning checklist only.** Continue from [the single context](../../../docs/IPHONE_PWA_CONTEXT.md) and read the OpenSpec specs. P0.1–0.4 completed as source analysis (2026-11-02), **not runtime verification**. The P1 login-only prototype is in separate [draft PR #257](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/pull/257). P1.1–1.3 stay **unchecked until code review and automated security/functional tests pass**; actual provider/device acceptance is the **last separate QA gate**, performed by the product owner only after P1/P2/P3 code and automated checks are complete. Before further code changes reconcile with current `main`; no runtime code, automatic merge, deploy or extra task ledger in this planning PR.

## P0 — small, targeted source audit (source review complete 2026-11-02; runtime tests not executed)
- [x] 0.1 Trace the existing Mini App's API calls and Telegram-only assumptions from `app/static/course-v3.html`, related course pages, `app/main.py` and `app/api/miniapp_*.py`. Identify the **minimum** host-dependent browser/API adapter points; document the compact route-to-service map.
- [x] 0.2 Review existing Google/Apple/Telegram identity-linking, session services, account owner `users.id`, course/progress/Pro/payment services and focused test baseline. Reuse existing services; do not create new DB tables, endpoints, dependencies or screen rewrites unless a specific gap is verified.

- [x] 0.3 Audit `CourseNotificationService`/existing inbox and `NotificationDeliveryService` account notices by canonical user: which statuses/messages are available in PWA and which have no persistent in-app record. Preserve Android→Telegram escalation and subscription/payment/limit state; do not assume all are in one feed.
- [x] 0.4 Read current `docs/smart-reminders/SMART_REMINDER_MASTER_PLAN.md` P5/D01/D03/D05/D06/D07/D10/D14 and actual APIs; record the future browser adapter boundary (owner, selected job, consent, capability, deep link, revoke, ack). Audit `BotFeedbackService` and `ReleaseFeedbackService` eligibility/bonus/Telegram-only gating for smallest PWA read/response adapter.

## P1 — independent login and shared account
- [ ] 1.1 Add the minimum safe browser login/session bridge using already verified identity services (Google/Apple only as supported by current configuration); Secure/HttpOnly cookie, CSRF protection, bounded session lifetime, logout/revocation and correct iPhone callback. Do **not** reuse a native bearer token in localStorage or an admin session.
- [ ] 1.2 Reuse the existing **explicit** Telegram account-link path as needed to preserve the original learner's Pro and progress. No fake Telegram ID, automatic email match/merge, duplicate trial/referral or cross-account session.
- [ ] 1.3 Test actual existing/new user flows, blocked/revoked/forged actor, CSRF and original Telegram/native login isolation before enabling any PWA course mutation.

## P2 — same Mini App, browser-safe transport

**Figma-first gate:** Editable drafts/components exist at [HSK AI iPhone PWA Figma](https://www.figma.com/design/89fCM5GdjfBqcx0B9aQHOI). Before coding any **new** inbox/settings/dialog, review variants against the real Mini App and `hsk-ai-ui`; align SF Pro/system typography and canonical UZ/RU/TJ copy; record approved component IDs in `docs/IPHONE_PWA_CONTEXT.md`. Do not redesign unchanged screens.
- [ ] 2.1 Reuse **the existing** course UI/JS/CSS. Introduce only a small Telegram-vs-PWA host adapter (navigation, auth headers, SDK-only actions). Avoid a parallel frontend, new UI framework or complete rewrite.
- [ ] 2.2 Adapt only the Mini App API paths actually used by PWA. Resolve verified browser `users.id` and call current course/grade/progress/access services; leave signed Telegram initData endpoints secure and working.
- [ ] 2.3 Preserve lesson/test/homework, HSK 2.0/3.0 track, XP/history, voice/practice where supported, profile, UZ/RU/TJ and current Pro/trial/subscription/receipt policies. Reuse existing checkout with browser-safe return and server payment confirmation; no billing redesign.
- [ ] 2.4 Run focused Mini App and PWA regression checks: course result/grade/source protection, Pro/free/pending/paid states, linking, logout/account switch and no Telegram/native regression. Use canonical localization catalogs when new UI copy is required.

- [ ] 2.5 Display available important account/service notices plus verified course/ranking messages inside authenticated PWA, reusing their canonical sources and server-confirmed subscription/limit state. Do not alter transactional delivery or treat inbox-read as push received; fill source gaps only after audit.
- [ ] 2.6 Reuse **eligible** ordinary bot feedback and release-feedback prompts as compact centered PWA dialogs (positive/negative, 1–5 rating, required follow-up), dismiss/focus-safe; same server prompt limits and one-time rewards across bot and PWA. Keep Telegram chat UX and active lesson/checkout uninterrupted.
- [ ] 2.7 Keep a future Smart PWA adapter boundary using canonical user, Smart preference/capability and safe target contracts. Unsupported iPhone channel stays disabled; no new sender/scheduler/subscription or consent request in v1.

**Execution order:** finish all P1/P2/P3 implementation and automated tests before asking the product owner to perform real Safari and Home Screen device tests. Physical device acceptance is the **final gate**, not a prerequisite for starting P2/P3 development. Never deploy, enable the feature or merge to `main` before both code completion and explicit approval.

## P3 — iPhone install and real acceptance
- [ ] 3.1 Add a dedicated learner HTTPS Home Screen entry, application name/icon/manifest as useful, responsive safe areas, mobile keyboard and standalone navigation. **Service Worker and offline lessons are not v1 requirements**; add caching only for a separately proven need and never cache private/graded content.
- [ ] 3.2 **Last QA gate, performed by the owner only after P1/P2/P3 code and CI are complete:** Test on a real iPhone in Safari **and** as a Home Screen app: first login, Google/Apple return as configured, existing Telegram account link, reopen/background/resume, expired session, lesson result, paywall/receipt return and audio/microphone behavior. Verify that tapping the writing/stroke area or focusing **any** text/select field does **not** auto-zoom; verify swipe between characters, normal vertical scrolling and user-initiated pinch accessibility still work. Document any supported iOS limitation. **No background Web Push in v1; in-app service notices and feedback dialogs are in scope.**
- [ ] 3.3 Verify security, relevant focused backend tests, targeted browser E2E, locale and original Telegram Mini App. Provide a reversible PWA-only disable/rollback and release checklist; implementation/release approvals remain separate.

- [ ] 3.4 Verify transactional account notices are not subjected to Smart study cap, existing Telegram/Android delivery stays unchanged, unsupported PWA channel is never selected, and V2 can add genuine installed-PWA service worker, push subscription/permission and selected-job adapter without a second Smart engine. Test feedback eligibility, dismiss, duplicate response and reward suppression.

## Acceptance and scope boundary
- Original Telegram Mini App must remain unchanged in behavior.
- Browser-only verified learners must use the **same canonical account services**, not a duplicate dataset.
- Existing account's progress, Pro, history and payment ownership must remain intact.
- Existing important account/transactional notices and course/ranking messages remain available through their authorized source and PWA in-app view where supported; feedback uses a centered dialog and existing canonical state.
- Smart Reminder V2 PWA transport attaches to existing account policy and one selected job, never a second scheduler.
- No separate Admin PWA, offline sync, **v1 Web Push**, new analytics pipeline, new courses, Android/Desktop changes, forced migrations or major redesign. V2 Web Push needs a verified installed-PWA SW/permission/subscription adapter.
- Plan validation (GitHub Actions) confirms only OpenSpec document structure; real runtime/physical iPhone QA is unverified until P3 executes.
