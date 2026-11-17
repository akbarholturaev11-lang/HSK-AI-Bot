# Tasks

Status and evidence are logged in `docs/TELEGRAM_PWA_ANDROID_HANDOFF_CONTEXT.md`.
A checked box means the stated verification was actually run.

## 1. Admin configuration

- [x] 1.1 Add validated `android_play_url` to `DesktopAppPromoSettings` (raw/payload/storage, legacy partial write keeps it); verify with unit tests in `tests/test_app_routing_settings.py`
- [x] 1.2 Add the field to `DesktopPromoChange` and the setting payload in `app/admin_api/pwa_marketing.py`; verify signed save, CAS refusal and invalid URL rejection in `tests/test_admin_pwa_marketing.py`
- [x] 1.3 Add the Play URL input to the existing promo editor in `app/static/admin-pwa/app.js` with canonical UZ/RU/TJ `ui.admin_pwa.*` labels; verify `scripts/i18n_build_all_catalogs.py --check` and the Admin PWA source/browser tests

## 2. Secure handoff

- [x] 2.1 Implement `issue_handoff`/`redeem_handoff` in `PwaAuthService` on `desktop_link_requests` (`flow="miniapp"`), and exclude that flow from the `start_link` global limiter; verify with `tests/test_pwa_telegram_handoff.py` (expiry, replay, wrong secret, blocked, owner change, gates off, mismatch, switch, supersede, rate limit, other flows refuse the row)
- [x] 2.2 Add `POST /api/v3/pwa-auth/handoff/start`, `POST /api/v3/pwa-auth/handoff/redeem`, `GET /iphone-pwa/handoff`, `GET /iphone-pwa-handoff.js`; verify headers, origin/transport refusal and cookie issuance through the API tests
- [x] 2.3 Verify atomic single consumption under real concurrency on PostgreSQL (separate test database) or record why it could not be run

## 3. Clients

- [x] 3.1 Extend promo decision/status for `ios` and `downloads.android_play`; verify `tests/test_desktop_download_api.py` and new decision tests
- [x] 3.2 Wire `desktop-download.js`: iPhone promo/profile action → handoff + `openLink`; Android action → Play or APK-to-chat; canonical UZ/RU/TJ copy; verify with JS execution tests and existing `tests/test_android_contextual_app_promo.py`
- [x] 3.3 Build the landing page (redeem → mismatch prompt → install guide → course; failure → existing sign-in); verify with Playwright WebKit/Chromium test `tests/e2e/test_pwa_telegram_handoff_page.py`

## 4. Analytics, regression and handover

- [x] 4.1 Record `pwa_handoff_issued`, `pwa_handoff_completed`, `android_play_opened`; expose `android_play_opened` as the Android funnel stage `play_opened` (statistics reader, export, MCP cache; the frozen legacy `admin.html` is left as on `main`); verify with focused tests
- [x] 4.1b Expose the iPhone handoff counts (`telegram_handoff.issued/completed`, install/activity stay `not_instrumented`) in the statistics reader, export and MCP cache; verify `tests/test_admin_pwa_read.py`, `tests/test_admin_pwa_statistics_export.py`. The Admin PWA dashboard card is a separate UI follow-up (see the context file)
- [x] 4.2 Run regressions: PWA browser auth, desktop download, Android APK delivery, Admin PWA marketing/settings, Li install/onboarding, i18n guards, iPhone PWA asset versions
- [x] 4.3 `openspec validate telegram-miniapp-pwa-android-handoff`; update the context file with branch, commits, test evidence and remaining gates

## Workflow follow-up

- **Owner manual acceptance: PASSED (reported 2026-11-11).** The owner confirms testing the user-facing flow and that everything works. This is owner-reported device/end-to-end QA, **not** a fresh independent device-matrix, staging, CI or provider verification run. See `docs/TELEGRAM_PWA_ANDROID_HANDOFF_CONTEXT.md` for the acceptance record and remaining operational evidence.
- **Merge: DONE.** PR #300 is in `main`, with follow-up UI changes from PR #302. The exact live Admin PWA switch/Play URL state is **not independently known** from this QA confirmation; do not assume OFF or ON or change any production setting as part of documentation updates.
- If later code or rollout is changed, follow `AGENTS.md` Git/CI rules and re-run focused regression tests. Preserve reversible settings and existing sessions, accounts, Pro and progress.
