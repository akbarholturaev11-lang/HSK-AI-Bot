# iPhone PWA Li onboarding — Telegram authentication handoff

## Purpose and authority

The last guest Li onboarding screen remains the original progress-preservation
speech bubble and book-holding panda, with **Telegram** and **Google** provider
buttons immediately available. It must not send the learner through the separate
`/iphone-pwa?login=1` “Welcome” selection screen. The separate Telegram bot
**approval** is still mandatory: this document does not authorize silent login.

The browser may preserve **choices**, but it cannot create an identity, attach a
Telegram account, issue Pro, claim HSK 3.0 access, begin a trial or mutate course
progress. All identity and account decisions remain server-owned. A Telegram
account and an unlinked Google identity must never be merged by name/email.

Canonical sources:
- `app/static/course_v3_li_onboarding.html`: existing profile speech, panda,
  provider buttons, common UZ/RU/TJ status catalog and cache-busted runtime.
- `app/static/course_v3_data/li-onboarding-runtime.js`: Li guest draft,
  real provider handoff, Telegram start/claim and Safari resume.
- `app/static/iphone-pwa-login.js`: existing normal PWA login UI; remains
  available outside the guest Li flow, but is **not** an intermediate Li step.
- `app/api/pwa_auth.py` and existing PWA/desktop auth services: actual
  HttpOnly cookie, Telegram approval, session and account ownership.
- `tests/e2e/test_li_onboarding_runtime.py`: browser regressions.

## Direct Telegram journey

1. Anonymous PWA learner completes the Li choices and reaches the original
   “Progressingizni yo'qotmang! Keling, sizga profil ochamiz.” screen; the
   original RU/TJ copy is kept unchanged. The Telegram/Google buttons are on
   that **same** screen, with no intermediate account-creation CTA.
2. Telegram click saves the same-tab anonymous draft and requests the existing
   `POST /api/v3/pwa/onboarding/li/resume` HttpOnly, Secure, SameSite=Lax
   handoff marker. It then calls
   `POST /api/v3/pwa-auth/telegram/start` (selected UZ/RU/TJ language).
3. The server returns the actual `link_request_id` and bot
   `authorize_url`. Client checks a UUID-shaped ID, HTTPS `t.me`, and the
   exact `pwa_link_<id>` token, optionally with `_uz`, `_ru` or `_tj`.
   It stores only this short-lived **same-tab** pending ID and validated link
   in `sessionStorage`; no identity or session token is fabricated.
4. The browser opens that official Telegram deep link directly. The learner
   approves the request in the bot. This bot screen is a security proof, not
   an extra HSK AI registration screen.
5. On returning/focusing/reloading the original Safari page, the guest draft
   restores the final progress screen, while the client polls the existing
   `POST /api/v3/pwa-auth/telegram/claim` with the request ID. Poll only
   while the original tab is visible, avoid concurrent claims and bound each
   call to 20 seconds; the pending interval is 2.5 seconds. A reload or
   browser back must not send the learner back to the beginning merely
   because approval is still pending.
6. **Only** a server-confirmed `complete` grants the regular HttpOnly PWA
   session. The client clears local pending state and navigates to
   `/iphone-pwa` for the existing verified Li-resume routing:
   - Existing learner with completed onboarding: directly to their own
     course, without overwriting choices, progress or Pro/Trial.
   - Verified new/incomplete learner: restore the own in-tab choices; write
     an onboarding completion only through the existing authenticated action
     and original validation/entitlement gates.

## Failure and ownership boundaries

- `pending`: keep the original final screen and existing localized pending
  message; **never** treat it as authenticated.
- Expired/denied: clear pending/link/handoff markers, display the existing
  localized status and allow the learner to retry.
- Temporary HTTP/network error: show the canonical error; no fabricated
  success, forced auto-registration or payment/trial activation.
- Browser back or switching to Google: clear the pending Telegram poll and
  obsolete handoff; do not let an earlier pending Telegram claim take over
  a newer Google identity. A claim already in flight must not authorize
  simultaneous provider switching.
- `sessionStorage` is **not** identity proof: the server must verify the
  approval and original browser/session binding. The existing Google OAuth
  path and Telegram Mini App SDK path remain separate, untouched flows.
- Preserve the original UZ/RU/TJ canonical text and generated catalog;
  do not insert another “Create account” or “Welcome” screen.
- Li rollout/feature flag, payment and production user data must not be
  changed merely to ship this UI fix.

## Release and regression checks

The exact PR head and latest `main` must be compatible; all mandatory CI
checks must finish with `success`, not merely start. Check:
- Chromium **and** WebKit mobile browser flows: last bubble/panda, directly
  starting Telegram, correct language-suffixed deep link and Safari back.
- Pending-to-approved existing owner: normal course without profile/Trial
  write; new owner: saved draft restored and committed once after proof.
- Expired/denied/retry, unrelated login/no cross-account draft adoption,
  Google OAuth, HSK 3.0 gate and onboarding-install handoff.
- Existing PWA auth/API tests, PostgreSQL and local-first localization
  contracts; observe Android/other required branch protections.
- Merge without force, confirm merged `main` SHA, production Railway deploy,
  `/health` and HTTP 5xx. Keep pre-existing production switches unchanged.

Automated browser/API regressions **do not** prove a real iPhone-to-Telegram
approval, a native app switch/back or real-provider availability. Those require
explicit physical-device QA. Do not claim them completed from CI alone.

**Analytics Impact:** provider start/claim is not a completed onboarding or
Pro conversion. Reuse the existing server-confirmed authenticated onboarding
completion; no new conversion event or inferred successful registration from
a pending bot approval.
