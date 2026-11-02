# Tasks — lean implementation plan for iPhone Course PWA

**Planning only.** All checkboxes are for later, evidence-backed implementation. Continue from [IPHONE_PWA_CONTEXT.md](../../../docs/IPHONE_PWA_CONTEXT.md); OpenSpec specs define acceptance. No separate progress log, no runtime code in this PR, and no automatic main merge/deploy. First refresh the current `main` code.

## P0 — small, targeted source audit
- [ ] 0.1 Trace the existing Mini App's API calls and Telegram-only assumptions from `app/static/course-v3.html`, related course pages, `app/main.py` and `app/api/miniapp_*.py`. Identify the **minimum** host-dependent browser/API adapter points; document the compact route-to-service map.
- [ ] 0.2 Review existing Google/Apple/Telegram identity-linking, session services, account owner `users.id`, course/progress/Pro/payment services and focused test baseline. Reuse existing services; do not create new DB tables, endpoints, dependencies or screen rewrites unless a specific gap is verified.

## P1 — independent login and shared account
- [ ] 1.1 Add the minimum safe browser login/session bridge using already verified identity services (Google/Apple only as supported by current configuration); Secure/HttpOnly cookie, CSRF protection, bounded session lifetime, logout/revocation and correct iPhone callback. Do **not** reuse a native bearer token in localStorage or an admin session.
- [ ] 1.2 Reuse the existing **explicit** Telegram account-link path as needed to preserve the original learner's Pro and progress. No fake Telegram ID, automatic email match/merge, duplicate trial/referral or cross-account session.
- [ ] 1.3 Test actual existing/new user flows, blocked/revoked/forged actor, CSRF and original Telegram/native login isolation before enabling any PWA course mutation.

## P2 — same Mini App, browser-safe transport
- [ ] 2.1 Reuse **the existing** course UI/JS/CSS. Introduce only a small Telegram-vs-PWA host adapter (navigation, auth headers, SDK-only actions). Avoid a parallel frontend, new UI framework or complete rewrite.
- [ ] 2.2 Adapt only the Mini App API paths actually used by PWA. Resolve verified browser `users.id` and call current course/grade/progress/access services; leave signed Telegram initData endpoints secure and working.
- [ ] 2.3 Preserve lesson/test/homework, HSK 2.0/3.0 track, XP/history, voice/practice where supported, profile, UZ/RU/TJ and current Pro/trial/subscription/receipt policies. Reuse existing checkout with browser-safe return and server payment confirmation; no billing redesign.
- [ ] 2.4 Run focused Mini App and PWA regression checks: course result/grade/source protection, Pro/free/pending/paid states, linking, logout/account switch and no Telegram/native regression. Use canonical localization catalogs when new UI copy is required.

## P3 — iPhone install and real acceptance
- [ ] 3.1 Add a dedicated learner HTTPS Home Screen entry, application name/icon/manifest as useful, responsive safe areas, mobile keyboard and standalone navigation. **Service Worker and offline lessons are not v1 requirements**; add caching only for a separately proven need and never cache private/graded content.
- [ ] 3.2 Test on a real iPhone in Safari **and** as a Home Screen app: first login, Google/Apple return as configured, existing Telegram account link, reopen/background/resume, expired session, lesson result, paywall/receipt return and audio/microphone behavior. Document any supported iOS limitation. No push/notification implementation in v1.
- [ ] 3.3 Verify security, relevant focused backend tests, targeted browser E2E, locale and original Telegram Mini App. Provide a reversible PWA-only disable/rollback and release checklist; implementation/release approvals remain separate.

## Acceptance and scope boundary
- Original Telegram Mini App must remain unchanged in behavior.
- Browser-only verified learners must use the **same canonical account services**, not a duplicate dataset.
- Existing account's progress, Pro, history and payment ownership must remain intact.
- No separate Admin PWA, offline sync, Web Push, new analytics pipeline, new courses, Android/Desktop changes, forced migrations or major redesign.
- Plan validation (GitHub Actions) confirms only OpenSpec document structure; real runtime/physical iPhone QA is unverified until P3 executes.
