# iPhone PWA — scheduled batch status (23-item list)

Checked with: `tests.test_iphone_pwa_asset_versions`, `tests.test_iphone_pwa_navigation_contract`,
`tests.test_rating_podium_ui_contract`, `tests.test_course_v3_static_data`, `i18n_build_all_catalogs --check`,
`node --check` on the new/changed scripts and every inline course script.
`tests/test_pwa_feedback_ui.js` and `tests/test_pwa_shake_report_ui.js` already failed on the parent commit.
Not run: Playwright E2E, real iPhone (haptics, push prompt, pull-to-refresh, audio icon).

## Done in code
- 1/2 (partial): inbox already had approved/rejected payment rows and Apple push; unchanged.
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

## Needs owner/config
- 12 Live voice: code path is wired. It stays off unless `PWA_VOICE_LIVE_ENABLED=true`, `ANDROID_VOICE_LIVE_ENABLED=true`,
  a Gemini key, model `gemini-3.8-live`, a positive session budget, and `ANDROID_VOICE_LIVE_ALLOWED_USERS="*"`
  (PWA-only accounts have no real Telegram ID, so a numeric allowlist never matches them).
- 11 Smart reminders over PWA: needs `PWA_PUSH_ENABLED`, `PWA_PUSH_SEND_ENABLED` and a real device receipt.

## Not started
8 (shake report parity), 10 (settings rebuild/channels), 15 (code reviewed, no defect found: the overtake effect needs server `rank_before`>0, so learners outside the ranked list never see it),
19 (native launch screen / startup images), 20 (profile name/avatar: needs new PWA endpoint + UZ/RU/TJ catalog keys), 21 (review parity check),
22/23 (centre-block minimalist audit).
