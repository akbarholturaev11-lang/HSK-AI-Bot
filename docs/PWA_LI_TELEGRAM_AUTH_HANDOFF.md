# iPhone PWA Li onboarding — direct Telegram sign-in

## Contract and ownership

Final guest Li onboarding stays on the original “Progressingizni yo'qotmang! Keling, sizga profil ochamiz.” progress-preservation bubble and book-holding panda, with **Telegram and Google** buttons directly underneath. Original UZ/RU/TJ canonical copy remains unchanged. Do **not** route Telegram through the unrelated `/iphone-pwa?login=1` Welcome selector. The official Telegram bot **approval** still occurs and is mandatory.

Source of truth: `app/static/course_v3_li_onboarding.html`, `app/static/course_v3_data/li-onboarding-runtime.js`, `app/api/pwa_auth.py`, `app/services/desktop_auth_service.py`, `tests/e2e/test_li_onboarding_runtime.py`. The separate `app/static/iphone-pwa-login.js` stays in place for ordinary PWA sign-in, but is not an intermediate Li step.

## Verified browser-bound flow

1. A PWA guest completes Li choices. The same-tab private draft is saved and `POST /api/v3/pwa/onboarding/li/resume` sets the existing short-lived HttpOnly browser handoff marker. This does **not** log the learner in or create a profile.
2. Telegram button calls the actual `POST /api/v3/pwa-auth/telegram/start`, passing the UZ/RU/TJ language. The server returns `link_request_id` and an official bot `authorize_url`. The client validates a UUID, `https://t.me` hostname, and exact `pwa_link_<UUID>` start token with optional `_uz`, `_ru` or `_tj` suffix. Never accept arbitrary origins/redirects.
3. Pending ID and validated bot URL remain only in same-tab `sessionStorage`. Navigate directly to Telegram. Its private bot confirmation is **not** a duplicate HSK AI Welcome screen.
4. On Safari return, back, focus, pageshow or reload, restore the original guest progress screen if its short-lived same-tab handoff and draft remain valid. Poll `POST /api/v3/pwa-auth/telegram/claim` only in the original visible browser; at most one claim at a time, 2.5-second interval, 20-second bound. Stop timers on pagehide and retry transient network failures without fabricating success.
5. Only server `complete` may issue the HttpOnly PWA session. Client then navigates to canonical `/iphone-pwa` for verified Li resume. `pending` gives no access. Denied/expired clears local pending and old handoff and allows a new official request; never attach an unrelated identity or replay an old proof.
6. The server-authoritative `GET /api/v3/pwa/onboarding/status` determines subsequent routing. Existing learner (`saved=true`): go to own course without overwriting guest choices, Pro/Trial, or lesson progress. New/incomplete verified learner: revalidate HSK 3.0/track eligibility and allow the original authenticated save once. No guest draft is authority for account identity, trial, payment or course access.
7. Back or switching to Google stops the old Telegram poll; avoid concurrent provider claims taking over a different verified session. Google OAuth, Mini App Telegram SDK and the normal login route are otherwise unchanged. Telegram identities are matched by proof, Google by subject: never merge on email/name.

## Failure, privacy and analytics rules

- Keep canonical UZ/RU/TJ pending/success/expired/denied/error text from `hsk-common-i18n.js`; do not add inline translations or assume a pending result is success.
- Never put request IDs, auth cookies, launch fragments, Telegram credentials or session tokens into query parameters, localStorage, URLs or public analytics. The session cookie remains HttpOnly and server-owned. Li writes require the existing authenticated PWA session and CSRF.
- The original PWA Li release flag `PWA_LI_ONBOARDING_ENTRY_ENABLED`, PWA push, Smart Reminder, payments, subscriptions, production account data and database schema are outside this change and must remain unchanged.
- **Analytics Impact:** reuse the existing verified server-owned account/onboarding completion. Telegram `start`, a bot-link click, `pending`, returning to Safari and `claim` are not independently successful onboarding, Pro conversions or payments. No invented analytics counters.

## Release readiness and rollback

- Before merge, re-fetch latest PR head and `main`, check mergeability and **all mandatory** exact-SHA GitHub Actions statuses. Running, skipped or cancelled checks are not success.
- Verify Chromium and WebKit Li E2E: original bubble, direct Telegram start, language suffix, browser back/reload, pending/complete, denied/expired, verified existing account with **zero guest writes**, new verified account with one saved draft; Google OAuth and account-link policy; HSK 3.0 guard; localized UI, API/auth and PostgreSQL regressions.
- After merge confirm exact main SHA, Railway deploy/build, Alembic startup, `/health`, 5xx and PWA/auth errors; do not silently change feature flags.
- **Manual QA still required:** real iPhone Safari ↔ official Telegram bot approval ↔ returning same Safari tab, existing owner and new user, denial/expiry, and lossless course progress. Playwright WebKit with stubbed bot is **not** real-device acceptance.
- Rollback via ordinary reviewed revert of the exact merge; do not delete sessions/user data, modify backend auth endpoints or disable unrelated production features.

Related: `AGENTS.md`, `AI_RULES.md`, `localization/README.md`, `docs/analytics/ANALYTICS_INTEGRITY_IMPLEMENTATION_PLAN.md`.
