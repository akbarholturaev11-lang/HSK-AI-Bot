# Proposal

## Why

Telegram Mini App learners on a phone have no direct path to the two priority
clients (`AGENTS.md`, "PWA + Android"): an iPhone learner must sign in again in
Safari, and an Android learner is always sent the Direct APK even after a Google
Play listing exists. The owner-approved outcome and continuity log live in
`docs/TELEGRAM_PWA_ANDROID_HANDOFF_CONTEXT.md` (canonical handoff); this change
is the OpenSpec delta required because the work touches auth, sessions and
several clients. The direct Codex workflow is insufficient only for that reason.

## What Changes

Source audit of `main@675f6244` corrected the earlier plan in four places:

- **No new ON/OFF flags.** `desktop_app_promo_settings.platforms.ios/android`
  and their passkey-signed Admin PWA editor (`DesktopPromoChange`) already give
  independent iPhone/Android switches. Only a validated `android_play_url`
  field is added to that same setting and editor.
- **No new table or migration.** The one-time handoff reuses
  `desktop_link_requests` with a new `flow="miniapp"` value (`platform="pwa"`,
  `intent="signin"`, pre-approved for one canonical user). Every existing
  consumer already refuses such a row (bot approval, native poll, Telegram
  claim, OAuth callback); the public link-start global limiter is told to
  ignore it so authenticated handoffs cannot throttle anonymous sign-ins.
- **iPhone becomes a real promo target.** The server hard-codes `ios: False`
  and the decision service only knows native platforms; both are extended so
  the existing placement, 14-day cooldown, dismissal and one-per-session rules
  apply to an iPhone PWA offer. An active PWA browser session counts as
  "already has it".
- **Android routing.** With a valid Play URL the existing Android offer opens
  Google Play; without one the existing APK-to-chat delivery is unchanged.

New behaviour:

- Mini App (iPhone): the existing promo and the profile apps entry open the
  external browser on a first-party landing page that redeems a short-lived,
  single-use handoff into the existing HttpOnly PWA session, shows the existing
  Home Screen install guide, then opens the existing course.
- Admin PWA: Google Play URL field inside the existing app-promo editor.
- Analytics: three server-written events and their statistics consumer.

Excluded: bot `/android` command, public `/download` page, native Android app,
Desktop, payments/Pro policy, Li onboarding flow, PWA push, new feature flags,
Redis, new services. No production switch is changed by this change.

## Capabilities

### New Capabilities
- `telegram-app-routing`: device-appropriate PWA/Android offers inside the
  Telegram Mini App, and the admin-owned Google Play destination.
- `pwa-telegram-handoff`: one-time transfer of a verified Telegram Mini App
  account into a learner PWA browser session.

### Modified Capabilities

None.

## Impact

- Backend: `app/services/desktop_app_promo_settings_service.py`,
  `app/services/app_promo_decision_service.py`,
  `app/services/desktop_download_service.py`,
  `app/services/pwa_auth_service.py`, `app/api/pwa_auth.py`,
  `app/services/desktop_auth_service.py` (one limiter filter),
  `app/admin_api/pwa_marketing.py`, `app/main.py` (event marking),
  analytics event names and the Android/iPhone statistics readers.
- Clients: `app/static/course_v3_data/desktop-download.js`, new
  `app/static/iphone-pwa-handoff.{html,js}`, `app/static/admin-pwa/app.js`.
- Localization: canonical UZ/RU/TJ in `localization/ui/*/{miniapp,li_onboarding}.json`.
- Risks: bearer transfer token (mitigated by fragment transport, 120 s TTL,
  single use, hash at rest), login-CSRF on a signed-out browser (accepted,
  documented), Telegram may open an in-app browser instead of Safari (manual
  Safari fallback). Rollback: switch `platforms.ios` off / clear the Play URL in
  Admin PWA, or revert the merge; no data migration to undo.
