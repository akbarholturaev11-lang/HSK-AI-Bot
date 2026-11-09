# iPhone PWA Li onboarding — direct Telegram auth and safe return

## Source of truth

The Li guest flow uses `app/static/course_v3_li_onboarding.html` and
`app/static/course_v3_data/li-onboarding-runtime.js`. Server authority
is in `app/api/pwa_auth.py` and existing PWA/desktop Telegram auth
services. Browser regression: `tests/e2e/test_li_onboarding_runtime.py`.

This is a scoped onboarding handoff, not permission to enable/disable
`PWA_LI_ONBOARDING_ENTRY_ENABLED` or change live payment/progress data.

## Exact UI contract

Keep the existing UZ/RU/TJ “do not lose progress” speech bubble and
book-holding panda. The **Telegram** and **Google** choices are already
on that same final profile screen. Do **not** introduce an additional
“Create account” button or redirect to `/iphone-pwa?login=1`, which
would display an unrelated second “Welcome” login screen.

The explicit Telegram **bot approval** is still necessary: removing the
extra HSK AI screen must not skip proof of account ownership.

## Browser-bound Telegram handoff

1. Anonymous learner completes choices. The original short-lived guest
   draft stays in the same Safari tab. `POST /api/v3/pwa/onboarding/li/resume`
   issues a Secure, HttpOnly, SameSite=Lax handoff cookie, **not** a login.
2. Tapping Telegram calls existing
   `POST /api/v3/pwa-auth/telegram/start` with the selected language.
   The server returns a browser-bound `link_request_id` and the official
   `https://t.me/...` bot deep link. Accept only a UUID-shaped ID and an
   HTTPS `t.me` URL with the matching `pwa_link_<UUID>` start token,
   optionally suffixed `_uz`, `_ru` or `_tj`.
3. Store the pending ID and validated link only in this tab's
   `sessionStorage`; launch the official Telegram bot link **directly**.
   Do not embed private tokens in a URL, copy state into `localStorage`,
   invent an account, or grant trial/Pro/HSK 3.0 access.
4. When Safari returns/reloads/focuses, restore the final progress screen
   from the original eligible guest draft while approval is pending.
   Poll existing `POST /api/v3/pwa-auth/telegram/claim` with the ID,
   one in-flight request at a time, every 2.5 seconds while visible, with
   a 20-second request timeout. Suspend on `pagehide`; resume on page
   visibility/focus/pageshow. Neither `pending` nor browser focus means
   that login succeeded.
5. **Only** server-confirmed `complete` issues an authenticated HttpOnly
   PWA session. Clear local pending state, then visit the canonical
   `/iphone-pwa` route, which verifies that session and consumes the Li
   handoff. A completed existing account goes to its own course with
   no onboarding overwrite, no Pro/Trial reset or lost progress. A
   verified new/incomplete account restores its own choices and saves
   once through the existing authenticated onboarding/entitlement gates.
6. Denied or expired approval clears pending/handoff state and uses the
   existing UZ/RU/TJ local-first error message; a new attempt requires a
   fresh request. Other network/server errors never imply authentication.
   Explicit back or switching to Google terminates the old local pending
   poll; a concurrent Telegram claim must not overwrite Google identity.

Google OAuth, Telegram Mini App SDK login, server-owned `users.id`,
CSRF/session checks, HSK 3.0 entitlement and trial/payment policy remain
unchanged. Unlinked Google and Telegram identities must not be silently
merged on email/name similarity.

## Verification / release gate

- Test the original final bubble/panda, two providers and no extra HSK AI
  Welcome screen in Chromium and WebKit.
- Validate real language-suffixed Telegram links, pending/approved/denied/
  expired outcomes, Safari back/reload, Google OAuth, saved existing account
  with **zero** guest progress/trial writes and a new account with exactly
  one authenticated save. Include HSK 3.0 locked-track and install handoff.
- Require **success** on all applicable tests for the exact latest PR
  commit, including PWA auth backend, PostgreSQL and localization guards.
  Cancelled, missing, queued or skipped mandatory tests are not green.
- Compare latest `main`, merge without force, verify exact `main` SHA,
  Railway startup/migration, `/health` and related PWA/auth logs. Leave
  production flags and payment/account data untouched.
- Real iPhone Safari → Telegram native approval → back to the same Safari
  tab requires separate device QA. Stubbed browser WebKit tests cannot
  substantiate a physical-device acceptance claim.

**Analytics Impact:** existing server-confirmed login/onboarding results
remain authoritative. Telegram start, polling, approval link open or
foreground return are not profile completions, Pro conversions or
payment events. No new fabricated conversion counters.
