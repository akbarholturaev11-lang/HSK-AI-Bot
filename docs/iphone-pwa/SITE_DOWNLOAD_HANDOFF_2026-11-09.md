# HSK AI public website — mobile navigation and iPhone PWA (2026-11-09)

## Intent and boundaries

- The **only** header redesign is for mobile widths (`@media (max-width:850px)` in `app/static/public-site-navigation.css`).
- The mobile header keeps **brand + globe icon + three-line menu**. The two menus are mutually exclusive, close on Escape/outside click, and use the mobile-scoped shared `/public-assets/language.js?v=4` controller; desktop language-menu dismissal behavior remains unchanged. Language options remain UZ/RU/TJ; menu links are the existing courses, features, guide and download routes. Do not change desktop header layout.
- The browser download page's `ios` platform is now **PWA**, linking to `/iphone-pwa?lang=uz|ru|tj` rather than the bot. Anonymous UTM/source tags are forwarded only from the allowlist; referral and device-link secrets are not forwarded. This is the product download route on any viewport.
- Preserve macOS DMG, Windows EXE and Android APK downloads, status API contract, device detection and download attribution. Social-browser Android fallback to the Telegram APK delivery bot remains separate from the iOS CTA.
- If an iPhone referral link arrives, primary action remains PWA. A **separate secondary Telegram referral link** retains the existing `ri_` code/2-message verification, because PWA referral credit is not independently established. Do not claim PWA referrer credit without proof.
- Copy ownership: `localization/ui/{uz,ru,tj}/course.json` owns the existing `downloadPage.iosDownload`, `iosStatus`, `iosSecurity`, `iosSecurityTitle` keys; regenerate bundled course resources and browser cache versions with `scripts/i18n_build_all_catalogs.py --write`. The existing iOS three-step fallback arrays in the download-page JS must remain accurate in all three locales.

## Install guidance and asset

PWA entry: `https://hskai.app/iphone-pwa` (optionally `?lang=uz|ru|tj` when a language is already selected). The login page and, when enabled, the guest Li onboarding must preserve that chosen language. Only allowlisted bounded UTM/source tags survive the Li redirect; referral codes, device-link secrets, duplicate tags and unrecognized query parameters do not. A signed-in session retains its own server-owned profile language. For Home Screen installation, open in **Safari**, tap Share, choose Add to Home Screen, confirm Add, and open the new icon. Use the existing account's linked login to retain progress and Pro. Do not imply that an App Store app is published or that Apple login is already supported.

Reuse exactly `/assets/onboarding/iphone-home-screen.mp4` (the same file as the PWA onboarding). The download page plays it with `controls playsinline preload="none"` and keeps text instructions visible if playback fails. It is shown only for the iOS platform choice. See `app/static/assets/onboarding/README.md` for codec and original-video review.

**Known release risk:** The existing video reportedly shows part of the older Railway hostname on Safari's Home Screen sheet. The text steps must always display the official `hskai.app/iphone-pwa` URL. Check the actual video on an iPhone Safari device and replace/redact an obsolete address before public release; reusing the file does not prove the hostname is correct.

## Regression checks

1. At 390px: navigation row hidden, globe only, accessible three-line menu with four working links, RU/TJ/UZ language changes, no horizontal overflow.
2. At desktop 1280px: original inline navigation and language-name selector remain; no visible mobile menu.
3. iOS on mobile and desktop: primary CTA `/iphone-pwa?lang=<selected>`, Safari three-step guide and video. Validate guest Li onboarding redirects and language continuity, including invalid `lang` query rejection. The video must never auto-play.
4. iOS referral: optional bot link with the `ri_` start payload; main CTA remains PWA. Android in-app social APK fallback must still say Telegram and deliver `apk_web` payloads.
5. Android, macOS, Windows: existing download URLs, install guides and mobile transfer stay intact.
6. JavaScript-disabled and SEO consumers: `iOS (PWA)` is a `WebApplication`, with `installUrl` and **no** fake native `downloadUrl`.
7. Run `python3 scripts/i18n_build_all_catalogs.py --check`, `python3 -m unittest tests.test_download_page_is_readable_without_js tests.test_public_site tests.test_i18n_all_catalogs tests.test_i18n_build_course_catalogs`, and Playwright `tests/e2e/test_desktop_download_page.py` on an environment with required dependencies.

Analytics Impact: iOS CTA remains on the public download page; changed destination is a PWA navigation, not a binary download or Telegram-bot conversion. Do not count it as `telegram_bot_cta_clicked` or a confirmed native installation. Existing release binary analytics and server-owned authorizations are untouched.
