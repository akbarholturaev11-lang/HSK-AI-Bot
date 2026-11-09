# iPhone PWA Li onboarding — direct Telegram authentication

## Status and ownership

Source of truth: `app/static/course_v3_data/li-onboarding-runtime.js`, `app/static/course_v3_li_onboarding.html`, `app/api/pwa_auth.py`, `app/services/desktop_auth_service.py`, and `tests/e2e/test_li_onboarding_runtime.py`.

This document describes the scoped Li onboarding login handoff implemented in PR #292, rather than claiming real-device acceptance or an independently enabled rollout. The existing production `PWA_LI_ONBOARDING_ENTRY_ENABLED` flag must not be changed by this patch. Its current configured value must be checked separately when releasing.

## Required UX

The original Uzbek/Russian/Tajik progress-preservation bubble and book-holding panda remain unchanged. On a guest iPhone PWA, the final profile step contains the actual Telegram and Google sign-in buttons. There is no duplicate account-creation step and Telegram MUST NOT navigate to the unrelated `/iphone-pwa?login=1` Welcome screen.

The **Google** button continues the existing browser OAuth start and callback with the same-tab, short-lived Li draft/resume cookie. The **Telegram** button launches the official bot approval process directly from the final profile screen. Both sign-in and first registration use verified provider identity; the button label itself never proves an account. A different unlinked Google identity must not silently merge with a Telegram-owned account.

## Telegram browser-bound handoff (PWA guest only)

1. The user reaches the last Li guest step. The browser keeps the choices in the existing same-tab Li draft and initiates the pre-existing `POST /api/v3/pwa/onboarding/li/resume` handoff (server-owned HttpOnly cookie; not a login).
2. The user taps **Telegram**. `LiRuntime.authenticate("telegram")` uses `POST /api/v3/pwa-auth/telegram/start` with the selected language. No Welcome/login page is opened and no account permission or Pro entitlement is granted.
3. The server issues a browser-bound request ID and a Telegram `https://t.me/...` bot link with a `pwa_link_<UUID>` start parameter, optionally suffixed `_uz`, `_ru` or `_tj`. The client validates HTTPS, host, UUID and exact start token before navigating. Never construct a bot URL from an untrusted redirect target.
4. The same-tab request ID and bot URL are kept only in `sessionStorage`. The client attempts `POST /api/v3/pwa-auth/telegram/claim` with the request ID after returning to the original browser tab. Polling is bounded to one in-flight claim, 2.5-second intervals and a 20-second request timeout; it is stopped during `pagehide` and resumed on foreground/focus/pageshow or after Safari reload.
5. A `pending` result leaves the original Li progress screen and provider buttons intact. A verified `complete` is the **only** successful Telegram sign-in outcome; the server sets the PWA session cookie. Client-side storage and the Telegram deep link are never treated as identity proof. The browser then navigates to canonical `/iphone-pwa`, which verifies the session and consumes the Li handoff to return to onboarding or course.
6. A previously completed account (`status.saved=true`) goes to `/iphone-pwa/course` without writing the new guest choices, restarting Pro trial, changing subscriptions or resetting lesson progress. A verified new/unfinished account revalidates track/HSK 3.0 permissions, resumes its own eligible draft and saves only through the existing authenticated onboarding endpoint.
7. Explicit back navigation, switching to Google, denial or expiry clears the local pending Telegram state and stale handoff marker. Unverified, stale, malformed or expired requests must never be accepted, replayed, used to attach another account or turned into a successful login. Existing Google OAuth and Mini App Telegram SDK flows are not replaced.

The separate Telegram bot approval is still necessary. The UX requirement removes the extra **HSK AI Welcome** screen; it does **not** bypass the bot's explicit approval or the server's ownership checks.

## Key invariants / error handling

- Canonical ownership is `users.id`. Telegram must be a verified unique Telegram identity, and Google matches by the verified provider subject, **not** email/display name.
- All Li writes require the existing authenticated PWA session and CSRF. Reading or saving a guest draft grants nothing. The server controls profile persistence, course access, trial eligibility, Pro/subscription and HSK 3.0 unlock.
- The pending browser ID and Li handoff are short-lived and same-tab. Never move them to URL query, `localStorage`, public analytics payloads or a different device. No token/session cookie is read by JavaScript.
- Telegram approval statuses and failures reuse the shared UZ/RU/TJ local-first catalog (`hsk-common-i18n.js`); no new inline translations or fabricated success state.
- A failed server response/network error must not mark a user logged in. Expired/rejected requests require a fresh approval start; a transient failure may be retried safely without treating an unknown result as complete. Back-to-Safari must restore the existing progress bubble, not restart onboarding.
- Preserve the already deployed login options, existing draft/resume policies, Google callback, Mini App, payments and all existing entitlement checks. Do not change the PWA Li feature switch, push, Smart Reminder, or production user/payment data in this change.

## Analytics Impact

Reuse existing verified server-owned auth/onboarding completion attribution. Telegram `start`, pending polling and `claim` are not new course/profile completions, Pro conversions or payment events. No new unverified client counter is required. Do not infer successful signup from Telegram deep-link clicks or returned browser focus; the account/session and authenticated onboarding result are authoritative. Dashboard coverage remains subject to the separate analytics integrity plan.

## Release checks (must be evidenced, not inferred)

- Run CI against the **exact latest PR head** and verify any updated docs-only SHA. Mandatory checks: Li PWA Playwright on Chromium and WebKit; existing Google OAuth callback; Telegram direct start/claim pending, approved, expired/rejected, Safari reload/back; completed existing account with zero overwrite; new account draft and one authenticated save; locked HSK 3.0; local-first translation contracts; relevant backend PWA auth, native Postgres and other required checks. A cancelled, skipped or pending job is not a pass.
- Check repository `AGENTS.md`, `AI_RULES.md`, `PROJECT_MEMORY.md`, latest `main` and branch mergeability. Do not merge unrelated commits or force-push; use PR merge only when all applicable gates are green and no blocker remains.
- For production, verify the exact merge SHA on `main`, Railway deploy state, DB migration startup, `/health`, HTTP 5xx and relevant PWA/auth errors. Leave feature flag unchanged. A successful server healthcheck does not demonstrate that iOS actually completed Telegram's native-app roundtrip.
- **Manual still required:** one real iPhone/Safari → Telegram bot approval → same Safari tab, for both an existing completed learner and a new account; also denial/expiry, no extra Welcome page, correct UZ/RU/TJ content and no draft/progress loss. Do not claim this gate passed based solely on Playwright WebKit or stubbed Telegram pages.
- Rollback: revert the exact merge through normal Git review while leaving server-owned authentication endpoints and migration/data intact. The previous canonical Welcome-page handoff remains the separately reviewable fallback; do not disable or alter account access globally.

Related: `docs/analytics/ANALYTICS_INTEGRITY_IMPLEMENTATION_PLAN.md`, `localization/README.md`.
