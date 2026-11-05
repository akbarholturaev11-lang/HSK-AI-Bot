# iPhone PWA — scheduled batch status (23-item list)

Checked with: `tests.test_iphone_pwa_asset_versions`, `tests.test_iphone_pwa_navigation_contract`,
`tests.test_rating_podium_ui_contract`, `tests.test_course_v3_static_data`, `i18n_build_all_catalogs --check`,
`node --check` on the new/changed scripts and every inline course script.
`tests/test_pwa_feedback_ui.js` and `tests/test_pwa_shake_report_ui.js` already failed on the parent commit.
Not run: Playwright E2E, real iPhone (haptics, push prompt, pull-to-refresh, audio icon).

## Done in code
- 4: separate floating back row removed from the checkout layer; the in-page header back arrow and right-swipe remain.
- 5: back controls are bare icons (no white card/ring) in course, practice and checkout pages.
- 7: one-time notification permission request on the first tap after open (iOS needs a gesture). Later changes stay in Settings.
- 13: `iphone-pwa-fx.js` gives practice pages and lessons a browser haptic (Safari switch tick / vibrate) and answer tones.
- 14: lesson pronunciation steps used the Telegram endpoint and showed "open in Telegram"; they now use `/api/v3/pwa/voice/pronounce`.
- 16/6: swipe-back no longer starts on the profile carousel, rating cups or any horizontal scroller; cups use `touch-action:pan-y`.
- 17: root cause: `/api/v3/hints/dismiss` had no PWA route, so closing a section hint was never saved and it returned on every open.
  Added `POST /api/v3/pwa/hints/dismiss` (CSRF + verified session) and the client mapping. The intro tour is also flagged as seen when it starts.
- 3: the plan is frozen per level per day (unchanged). Root cause of "a different plan on each open": the Android app syncs
  `daily_goal_xp` on open through `set_study_preferences`, which cleared the shared plan every time; the Mini App/PWA
  preferences POST did the same even for unchanged values. Both now clear it only when goal/minutes/focus really change
  (daily XP goal is not part of the frozen plan). Tests: `tests/test_miniapp_preferences_api.py`, `tests/test_course_today_service.py`.
- 9: dictionary stroke order failed after a 3.5 s timeout while the 2.8 MB bundled stroke data was still loading; it now waits for it.
  Audio uses public `/api/v3/tts` and was not changed; a freeze was not reproduced.
- 18: pull-to-refresh on Course/Rating/Profile (`iphone-pwa-refresh.js`).
- 23 (last line): favicon/Now-Playing icon switched from the panda avatar to the red-gold knot logo.

## Second pass (re-verification + fixes)
- Regression found: `/course_v3_data/{filename}` serves an allowlist only, so the new `iphone-pwa-fx.js` and
  `iphone-pwa-refresh.js` (and the older `iphone-pwa-invite.js`) returned 404. Added to the allowlist; a test now
  fails for any unlisted `iphone-pwa-*` asset.
- Swipe-back: only pure horizontal scrollers own the gesture (a vertical lesson body computes overflow-x:auto too).
- Checkout layer focuses its iframe on open; dictionary requests stroke data from the server at most once.
- 1/2: Inbox payment rows and the urgent dialog show plan, amount, method, receipt number, date and a localized coded
  rejection reason (free-text admin notes stay hidden). Tapping a rejected receipt opens checkout at the receipt step
  (`step=pay`, method/country restored; TJ card stops at the bank step). Payment pushes say approved/rejected
  (4 new notification keys, no amount/reason). The service worker counts pushes on the app-icon badge; opening the
  Inbox or the sign-in page clears it (iOS 16.4+, installed app, permission granted).
- 11: Smart PWA dispatch sent a reminder as soon as it was planned, ignoring `scheduled_at` (Telegram already waited).
  It now waits for the frozen send time; regression test in `tests/test_smart_reminder_pwa.py`.
- 12: Live mode switch and the Live websocket accepted only `pwa_origin`, while every other PWA mutation also accepts
  `redirect_base_url`; opened from that origin, Live failed with 403 while turn mode worked. Both now use
  `pwa_allowed_origins`. `voice-live.js` no longer waits forever on a pending iOS `AudioContext.resume()`; it falls
  back to turn mode instead.

- 19: iOS shows `apple-touch-startup-image` before the first paint of an installed web app; none existed, so a
  blank (often black) screen appeared. Added 11 portrait launch images (paper background, knot logo, gold "HSK AI",
  `app/static/assets/startup/`, served by `/assets/startup/{filename}`), linked statically on the sign-in page and
  injected on the PWA course page. iOS reads them at install time: an already-installed app needs to be removed and
  added to the Home Screen again to pick them up.

- 21/23 stars: lesson feedback in the PWA already uses the bot's canonical ordinary-feedback flow. Bot release-feedback
  campaigns (1-5 stars) were never shown in the PWA (`open()` always passed `release:[]`). The course now calls
  `HskPwaFeedback.openRelease()` 6 s after load on a calm course screen: one star form per delivered, unanswered
  campaign per device. Only accounts that received the campaign (Telegram/Android delivery row) are eligible.
- `tests/test_pwa_feedback_ui.js` and `tests/test_pwa_shake_report_ui.js` were stale (harness ignored the markup
  `hidden` attribute; practice moved from page navigation to an iframe layer). Both pass again.

- 20: Profile name/avatar editor (Android parity: display name + 3 preset pandas). `POST /api/v3/pwa/profile`
  (same validation as Android, CSRF, same-origin); the map `user` adds `display_name`/`avatar_key`. Save is enabled
  only after a real change. The leaderboard already reads the same profile fields.
- 10: PWA Settings is one flat list in three sections (Study / Notifications / Account), no nested cards. Study shows the
  onboarding goal, daily time and focus (edit returns to Settings, no question chain) plus daily XP goal and language.
  Notifications are split into: device push (existing), study reminders (`notifications_enabled`, new
  `POST /api/v3/pwa/notify`, the flag MotivationReminderService already honours) and payment/account notices
  (always on, transactional). No new server policy was invented.
- i18n: 12 new course keys (UZ/RU/TJ), catalog 1021 → 1033 (`scripts/i18n_course_ui_catalog_guard.py`), generated
  bundles/tokens refreshed, reviewed page blobs recorded in `localization/baselines/reviewed_ui_changes.json`,
  line anchors remapped in `localization/review/miniapp_course_hotspot_triage.json` and
  `miniapp_lesson_fetch_calls.json` (diff-mapped from 503730e, anchors verified).

- 8: Shake report form now mirrors Android `BugReportDialog`: tall sheet (96% width / 94% height) where only the
  fields scroll and the single Send stays visible; "Close" text in the header (no duplicate Cancel); `n / 2000`
  counter; screenshot label + switch, 112 px preview and the Android privacy note (`pwaShake.privacy`, catalog 1034).
  The first-run sensor intro and the confirm step match Android's intro sheet.

- 22/23: Centered dialogs (HSK 3.0 promo/book card, lesson-exit confirm, urgent payment notice, feedback/star
  rating, shake intro/confirm/sent) share one PWA-only style per the hsk-ai-ui skill rules: paper card, 28 px radius,
  soft depth, 15 px body text, 54 px primary button, quiet text-only secondary, larger golden stars. CSS only,
  scoped to `html.hsk-pwa-browser`; the Telegram Mini App look is unchanged. Visual smoke (Playwright, iPhone 13):
  profile, profile editor, settings, shake form and star rating rendered with no console errors.

- 10 (v2, owner feedback): Settings is a short iOS-like list (profile identity row, Language, Course version,
  Study, Notifications / sign-in, shake report, Help / Logout) with icon tiles and inset dividers. Study and
  Notifications open as bottom sheets: Study edits goal, daily time, focus and daily XP and returns to the sheet;
  Notifications shows each channel with a switch (device push via the same gesture-safe subscribe path, study
  reminders via `/api/v3/pwa/notify`, payment/account notices locked on). Sheets and centered dialogs use a calm
  entrance animation that respects reduced motion.

- Owner correction (Liquid Glass, scope): Liquid Glass (translucent blur/saturate surface, specular highlight, glass
  chips; solid fallback for prefers-reduced-transparency; dark variant) applies only to PWA-only centered dialogs:
  feedback/star rating, urgent payment notice, shake report. Earlier PWA overrides of Mini App dialogs
  (course-switch cards `hsk30-promo-center`/`hsk30-book-card`, `lesson-exit-confirm`) and of all `#sheet` animations
  were removed; those keep their original look.
- Ordinary feedback keeps the bot's text-variant flow (liked → detail → disliked; subscribers: was it worth it →
  detail), now as tappable variants instead of a select. The app lists its own features
  (`APP_LIKED_OPTIONS`: course, AI Voice, pronunciation, dictionary/stroke order, practice, other;
  `APP_PAID_SUB_POSITIVE` adds pronunciation); the bot keyboards are unchanged and the server accepts the union.
  A first answer already recorded in the bot stays selectable. 4 new bot texts (original 276 bot keys unchanged,
  frozen-hash test extended) and 4 short course questions (catalog 1038).

## Needs owner/config
- 12 Live voice: also requires `PWA_VOICE_LIVE_ENABLED=true`, `ANDROID_VOICE_LIVE_ENABLED=true`, a Gemini key,
  model `gemini-3.8-live`, a positive session budget, and `ANDROID_VOICE_LIVE_ALLOWED_USERS="*"`
  (PWA-only accounts have no real Telegram ID, so a numeric allowlist never matches them).
- 11 Smart over PWA: `PWA_PUSH_ENABLED`, `PWA_PUSH_SEND_ENABLED`, VAPID keys, and a production routing review for the
  account (no production path creates one yet); Google/Apple-only PWA accounts are not admitted by the planner.
- 1/2 pushes: same PWA push switches and VAPID keys.

## Not started
- None of the 23 items is untouched. Not verified on a real iPhone: push receipt, badge, launch images, haptics,
  Live voice, pull-to-refresh feel. Production env flags above are not verified (Railway MCP was unavailable).
