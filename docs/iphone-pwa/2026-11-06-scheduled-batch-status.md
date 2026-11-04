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
- 17: the intro tour is flagged as seen when it starts, not only when it ends.
- 18: pull-to-refresh on Course/Rating/Profile (`iphone-pwa-refresh.js`).
- 23 (last line): favicon/Now-Playing icon switched from the panda avatar to the red-gold knot logo.

## Needs owner/config
- 12 Live voice: code path is wired. It stays off unless `PWA_VOICE_LIVE_ENABLED=true`, `ANDROID_VOICE_LIVE_ENABLED=true`,
  a Gemini key, model `gemini-3.8-live`, a positive session budget, and `ANDROID_VOICE_LIVE_ALLOWED_USERS="*"`
  (PWA-only accounts have no real Telegram ID, so a numeric allowlist never matches them).
- 11 Smart reminders over PWA: needs `PWA_PUSH_ENABLED`, `PWA_PUSH_SEND_ENABLED` and a real device receipt.

## Not started
3 (plan once a day), 8 (shake report parity), 9 (dictionary stall), 10 (settings rebuild/channels), 15 (streak/overtake effects audit),
19 (native launch screen / startup images), 20 (profile name/avatar: needs new PWA endpoint + UZ/RU/TJ catalog keys), 21 (review parity check),
22/23 (centre-block minimalist audit).
