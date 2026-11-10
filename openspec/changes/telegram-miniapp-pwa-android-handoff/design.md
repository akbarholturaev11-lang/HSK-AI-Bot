# Design

## Context

Audited on `main@675f6244`. Canonical handoff and status log:
`docs/TELEGRAM_PWA_ANDROID_HANDOFF_CONTEXT.md`. Facts that shape the design:

- `DesktopAppPromoSettings.platforms` already has `ios`/`android`, edited by the
  signed Admin PWA command `DesktopPromoChange` (`app/admin_api/pwa_marketing.py`,
  editor in `app/static/admin-pwa/app.js`). Default `ios=False`, `android=True`.
- `DesktopDownloadService._promo_status` hard-codes `ios: False`;
  `AppPromoDecisionService` accepts only native platforms;
  `desktop-download.js` lists `macos/windows/android`.
- `PwaAuthService._mint_session` issues the HttpOnly `__Host-hskai-pwa` session
  from a `DesktopLinkRequest` row and revokes only the same browser's previous
  session. `claim_telegram` requires `flow="telegram"`, OAuth requires
  `flow=provider`, `poll_link` refuses `platform="pwa"`, bot approval requires a
  pending Telegram row.
- `HSKAILiInstallGuide.open({userId, lang}, done)` is a self-contained module
  (video, three text steps, non-Safari hint, per-user "seen" key).
- `/iphone-pwa/course` already sends an authenticated learner without completed
  onboarding to the existing onboarding route; completed learners see the course.

## Goals / Non-Goals

**Goals:** smallest change that makes the routing real and safe; reuse existing
settings, promo, session and install-guide code; fail closed everywhere.

**Non-Goals:** new flags/tables/services, Redis, changing bot `/android`, the
public download page, native Android code, Desktop, Li onboarding or payments.

## Decisions

1. **Settings.** Add `android_play_url` to `DesktopAppPromoSettings`
   (storage/public payload, `from_raw`, `from_payload` preserving the previous
   value on partial legacy writes) and to `DesktopPromoChange`. One validator
   `normalize_android_play_url` accepts only `https://play.google.com/store/apps/details`
   with `id=com.pomp.hskai` (no credentials/port/fragment) and stores the
   canonical form `https://play.google.com/store/apps/details?id=com.pomp.hskai`.
   *Alternative rejected:* a separate `settings.update` kind — it would create a
   second editor and a second revision for the same promo object.
2. **Handoff persistence.** Reuse `desktop_link_requests`: `platform="pwa"`,
   `flow="miniapp"`, `intent="signin"`, `status="approved"` at creation with
   `approved_user_id/approved_telegram_id`, `expires_at = now + 120 s`.
   `polling_secret_hash = HMAC("pwa-handoff", secret)` (unique index gives the
   lookup; the native `"polling"` namespace can never match),
   `installation_key_hash` and `display_code_hash` are HMACs of server-only
   random values. Issuing cancels the learner's earlier unused handoffs and is
   limited to 5 per 10 minutes per learner. `start_link`'s anonymous global
   limiter excludes `flow="miniapp"`. *Alternative rejected:* new TTL table —
   ownership, expiry and atomic consumption are already provable on this row.
3. **Transport.** `POST /api/v3/pwa-auth/handoff/start` (header
   `X-Telegram-Init-Data`, freshness 3600 s) returns
   `{pwa_origin}/iphone-pwa/handoff#t=<secret>&lang=<uz|ru|tj>`. Fragment keeps
   the secret out of access logs and `Referer`. `GET /iphone-pwa/handoff` serves
   a static shell (`no-store`, `no-referrer`, strict CSP, `X-Frame-Options: DENY`)
   and `GET /iphone-pwa-handoff.js`; the script clears the fragment with
   `history.replaceState` first, then `POST /api/v3/pwa-auth/handoff/redeem`
   (`require_same_origin`, bounded JSON).
4. **Redemption.** Row `FOR UPDATE` by secret hash → checks (`platform/flow/
   intent`, `approved`, unused, unexpired) → user `FOR UPDATE` (not blocked,
   same Telegram id) → gates (PWA enabled, `platforms.ios`) → existing session
   comparison: same owner → burn the row, keep the cookie; other owner without
   `switch` → `409 pwa_handoff_account_mismatch`, row untouched; otherwise
   `_mint_session(replace_cookie=…)`. Lock order row→user matches `claim_telegram`.
5. **Promo.** `available_targets["ios"] = platforms.ios and pwa_enabled`.
   `AppPromoDecisionService` gets promo targets `native ∪ {ios}`; for `ios`,
   "installed" means an unrevoked, unexpired PWA session of that user.
   `mark()` accepts `ios`. Status adds `platforms.ios` and
   `downloads.android_play`. Client: `ios` joins the promo platform list with
   one copy block; the action requests a handoff and calls
   `Telegram.WebApp.openLink`; after success the button turns into a synchronous
   "open again" link for the remaining lifetime. Android action opens the Play
   URL when present, else `sendAndroidToChat`.
6. **Landing UX.** Loads only the Li catalog, install-guide CSS/JS and character
   pack. States: redeeming → (mismatch prompt) → install guide (if eligible and
   unseen) → `/iphone-pwa/course`; failure → existing sign-in `/iphone-pwa?login=1`.
7. **Analytics Impact.** Reuse `desktop_promo_seen/dismissed` (already carry
   `target_platform`). Add server-written `pwa_handoff_issued`,
   `pwa_handoff_completed` (dedupe = link request id) and client-reported,
   server-authenticated `android_play_opened` (dedupe = event id). Consumer:
   the basic statistics reader (`pwa_read.statistics`, its export and the MCP
   cache) — the Android funnel gains the first stage `play_opened` (the frozen
   legacy `admin.html` is left unchanged); `iphone_pwa` returns `telegram_handoff.{issued,
   completed}` counts and explicitly keeps install and activity metrics
   `not_instrumented`. The Admin PWA dashboard card (`pwa_analytics_*` stack)
   still shows iPhone PWA as not instrumented; showing the handoff counts there
   is a separate UI follow-up. Telemetry failure never blocks the flow.

## Risks / Trade-offs

- [Bearer link can be forwarded] → fragment only, 120 s, single use, newest
  wins, hash at rest, no auto-redeem over a different account.
- [Login CSRF: a signed-out victim opening an attacker's link lands in the
  attacker's account] → accepted residual risk of any link sign-in; bounded by
  the 120 s single-use window; explicit prompt when any account is present.
- [Telegram opens an in-app browser] → session lands there; the install guide's
  non-Safari hint tells the learner to open `hskai.app/iphone-pwa` in Safari,
  where the existing sign-in works. Never reported as installed.
- [Home Screen web app has its own storage on iOS] → existing behaviour of the
  current install guide; needs real-device QA, not solvable server-side.
- [Stolen Mini App data → 7-day session] → 1-hour freshness bound, per-learner
  limit, blocked/gate re-checks at redeem.
- [Play URL valid but listing not live] → admin responsibility; rollout gate.

## Migration Plan

No schema migration. Deploy is inert: `platforms.ios` defaults off and the Play
URL is empty. Enable only after real-device QA. Rollback: turn the switch off /
clear the URL in Admin PWA (stops new offers and new handoffs; sessions stay),
or revert the merge.
