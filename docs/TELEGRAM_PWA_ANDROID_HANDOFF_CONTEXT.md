# HSK AI — Telegram to PWA / Android routing: cross-chat context

> **Single continuation file for this proposed feature.** Read this file in every new chat before changing the feature. Keep it short and factual; update this file in place, not with new handoff copies.
>
> **Status:** merged to `main` (PR #300, merge `75795da5`, 2026-11-10); production switches unchanged and not device-tested — see **Current state** at the end.
>
> **Baseline read:** `main@3d4f14fa1ef39311998eb5d59d32c7598b17296d` (2026-11-10 review). **Re-read latest `origin/main` and changed files before any implementation.** This SHA is not a fixed implementation base.

## 1. Owner-approved outcome

When a learner opens HSK AI Telegram Mini App, offer a device-appropriate path without forcing the user to leave the Mini App.

- **iPhone:** A user-initiated PWA button leads to the external browser. If a Telegram account exists, a **secure one-time session handoff** signs that *same canonical user* into the PWA without repeating account registration or completed onboarding. Show the **existing** iPhone Home Screen installation video/guide after verified login, then continue to the existing course. Preserve server-owned level, progress, subscription, Pro, trial and locale. If mandatory onboarding data is genuinely missing, resume only the missing authenticated steps; never invent completion.
- **Android:** Offer Google Play if the admin configured a valid and verified Play listing URL; otherwise use the existing Direct APK/bot delivery. Preserve the existing native Direct-versus-Play payment/update policies and the Telegram Mini App option.
- **Admin PWA:** Independent iPhone PWA and Android ON/OFF routing controls, plus editable Google Play URL. OFF disables **new Telegram routing offers**, not the installed PWA, Android app, existing sessions, course or subscriptions. URL must refer to `com.pomp.hskai`.
- **No duplicate promo modal:** reuse the existing promotion placement, per-platform eligibility, 14-day cooldown and dismissal where applicable; one offer per existing session rule. Avoid competing legacy/new prompts.
- **iOS limits:** A web page cannot programmatically install a Home Screen PWA, and Telegram cannot guarantee Safari rather than another external browser. Provide a concise Safari/manual-open fallback. Do not claim a completed install based on a button click.

The four implementation workstreams are: (1) Admin/config/routing, (2) secure one-time PWA handoff, (3) minimal Mini App/PWA/Android UX, (4) focused security, regression, staged release and analytics checks. **Avoid extra frameworks and overlapping tasks.**

## 2. Actual code and existing authorities

Read current versions first; these were verified at the baseline above:

| Concern | Existing owner / entry |
| --- | --- |
| Repo-wide invariants | `AGENTS.md`, `AI_RULES.md`, `PROJECT_MEMORY.md`, `openspec/config.yaml` |
| Project planning skill | `.agents/skills/hsk-ai-openspec-planning/SKILL.md` |
| Admin settings proof/CAS/audit | `app/admin_api/pwa_settings.py`; UI: `app/static/admin-pwa/app.js` |
| Promo platforms/ON/OFF | `app/services/desktop_app_promo_settings_service.py`; Admin marketing: `app/admin_api/pwa_marketing.py` |
| Placement/cooldown | `app/services/app_promo_decision_service.py`, `app/services/desktop_download_service.py` |
| Mini App promo UI | `app/static/course_v3_data/desktop-download.js` (iOS automatic target previously absent) |
| PWA browser session, Telegram approval and auth gates | `app/services/pwa_auth_service.py`, `app/api/pwa_auth.py`, `app/services/desktop_auth_service.py` |
| Telegram signature verification | `app/services/telegram_webapp_auth.py` |
| Install-guide view/video | `app/static/course_v3_data/li-onboarding-install.js`, `/assets/onboarding/iphone-home-screen.mp4` |
| Android Direct APK | `app/bot/handlers/android_app.py`, `app/services/android_release_service.py` |
| Native Play package and flavor | `android/app/build.gradle.kts` — `com.pomp.hskai` |

**Important separations:**
- `docs/PWA_LI_TELEGRAM_AUTH_HANDOFF.md` covers **PWA guest → Telegram bot confirmation → PWA**. This new feature is **Telegram Mini App → external browser PWA**, not that same protocol. Preserve the original approval flow.
- `docs/iphone-pwa/SITE_DOWNLOAD_HANDOFF_2026-11-09.md` covers **public site → PWA**. Preserve public `/download` and referral behavior.
- `docs/onboarding-li/RELEASE_READINESS.md` and `docs/onboarding-li/IMPLEMENTATION_CONTEXT.md` cover existing onboarding and device readiness. Do not clone them.
- `openspec/changes/iphone-pwa-learner-navigation-and-delivery/` has a different scope; cross-link rather than overwrite.
- `PWA_AUTH_ENABLED` and `PWA_LI_ONBOARDING_ENTRY_ENABLED` are independent existing server flags. Admin routing ON cannot bypass these gates.
- `desktop_app_promo_settings` already has `platforms.ios` and `platforms.android`. Prefer extending this *existing* configuration; do not create three competing flags, another promo service or another video engine. **Preserve the actual existing Android promo state at migration/rollout.**

## 3. Minimal secure handoff contract — to be implemented

1. Mini App presents the offer only to a currently verified signed Telegram user. Validate fresh, signed `initData` on the server (never trust client-supplied `user_id`); re-check account restriction and current PWA/routing readiness.
2. The server creates a strong, short-lived, single-use authorization for the canonical owner. It conveys **no cookie, user ID, refresh token, Pro grant, or auth data in the URL/query**. A browser transfer token is still a bearer secret: minimize lifetime and exposure, use a first-party isolated landing page, no third-party JS, safe referrer/caching/logging, bounded rate limits and token hashing at rest.
3. The external browser redeems the authorization once via a same-origin server request. Under an atomic database transaction/lock, verify unexpired/unused token, exact intended user, no block/revocation, feature/readiness gates, and account/session mismatch. An existing **different** browser owner must **not** be silently replaced; require a clear explicit switch or fail safely.
4. Reuse the existing `PwaAuthService` session issuance, HttpOnly/Secure cookie, owner access and CSRF rules. A replay, concurrent consume or failed exchange never issues a second session. Do not extend the existing Telegram approval's privileges or fabricate provider identity.
5. After verified PWA session, route completed learners **directly to the existing install guide**, not Li onboarding. Show video with four-line failure fallback as currently implemented; honor already-installed/seen state. If Safari does not receive a usable session or a token expires, use the existing authenticated login fallback, never a false success.
6. Prefer the smallest persistence extension that preserves the *existing* `desktop_link_requests` flow/intent invariants. Only add a dedicated TTL table/Alembic migration **if safe reuse cannot prove ownership, expiry, and atomic one-time consumption**. Do not pick schema before reviewing these constraints.

A successful PWA login is not a confirmed PWA installation; Play-link opens are not Play installs.

## 4. Lean task list

- [ ] **A — Config/UX:** verify latest source, extend existing platform settings and Admin PWA editor with `android_play_url` (allowlisted HTTPS/Play package). Preserve WebAuthn, CAS, audit and Admin's one-primary-action UI. Add minimal focused settings and existing promo tests.
- [ ] **B — Handoff auth:** implement issuance and atomic redemption using signed Telegram proof + current PWA cookie/session owner. Include expiry, replay, stolen-link, blocked user, parallel requests, mismatched owner, and fail-closed tests.
- [ ] **C — Client:** wire the existing Mini App promo on a real user tap; iPhone secured browser landing and install guide; Android Play/Direct fallback. No extra onboarding or installation UI framework; UZ/RU/TJ canonical localization only.
- [ ] **D — Acceptance/release:** run focused API/DB auth tests, Admin WebAuthn/CAS tests, Play/Direct regression, real Telegram/Safari iPhone and installed Home Screen QA, slow/offline fallback, account/progress/Pro checks, then CI/staging. Record Analytics Impact through actual event → dedupe/store → Admin consumer or explicitly mark unavailable; do not invent conversion counts. Roll out default OFF and enable only after real acceptance. Roll back by switching off new offers/handoff, **not** deleting users, Pro or existing sessions.

## 5. Blockers and non-goals

- **Do not promise one-tap iOS installation or guaranteed automatic Safari switching.**
- The existing install video might show an obsolete Railway hostname; visually review against official `hskai.app` before public exposure.
- Confirm the real Google Play listing rather than equating a syntactically valid URL with availability.
- No new Redis, general-purpose routing service, second promo modal, duplicate documentation, broader auth refactor, unrelated Android rewrite, or subscription/payment policy change.
- A previously logged-in Safari account and credentials leaked in URL/analytics are security blockers; never work around them to achieve automatic login.
- No push/deploy/production activation from planning alone.

## 6. Continuation and upkeep (update this **same** file)

At the start of every new coding chat:
1. Read `AGENTS.md`, `AI_RULES.md`, `PROJECT_MEMORY.md`, this context, the specific existing handoffs above, and the *live* `main` plus relevant tests. Check whether an OpenSpec change for this exact feature exists; avoid creating duplicates.
2. Follow `.agents/skills/hsk-ai-openspec-planning/SKILL.md` for real CLI scaffold: `openspec context`, `new change`, artifact instructions and `validate`. **As of this file's creation no such CLI run or OpenSpec files are claimed.** Proposed slug: `telegram-miniapp-pwa-android-handoff`.
3. Before changes, update the **Current state** below with current branch/SHA and open conflicts. Implement only one bounded workstream; report exact files, tests, outcomes and rollout gates, not guessed completion. After changes, update this section in the **same commit** as corresponding work and keep it concise.
4. If a prior task partially completed, continue the remaining tasks rather than resetting or reimplementing them. Preserve unrelated user commits. For handoff between chats, point directly to this path.

### Current state

- **Branch:** `feat/telegram-pwa-android-handoff-20261110` (worktree `.claude/worktrees/telegram-pwa-android-handoff`), based on `main@675f6244`; merged into `main` by PR #300 (`75795da5`).
- **Plan of record:** `openspec/changes/telegram-miniapp-pwa-android-handoff/` (proposal, design, two spec deltas, `tasks.md`); `openspec validate` passes. `tasks.md` is the only checklist; this section is the status log.
- **Audit corrections to sections 2–4 above (verified in source):**
  - Independent iPhone/Android ON/OFF already exist: `desktop_app_promo_settings.platforms.ios/android`, edited by the signed Admin PWA `desktop_promo` command. **No new flags.** Only `android_play_url` is added to that setting/editor.
  - **No new table/migration.** Handoff reuses `desktop_link_requests` with `flow="miniapp"`, `platform="pwa"`, `intent="signin"`, pre-approved, 120 s TTL; secret hashed under its own HMAC purpose. Existing bot approval, native poll, Telegram claim and OAuth callback already refuse such a row.
  - Server hard-coded `ios: False` and the decision service knew only native platforms — both must be extended; an active PWA session counts as "already has it".
  - Transfer secret travels in the URL **fragment** only (never query/path), cleared by the landing script before the same-origin redeem.
  - A different account already signed in on the browser is never replaced without an explicit switch; a signed-out browser is signed in directly (login-CSRF residual risk accepted and documented in `design.md`).
- **Done (code + automated tests):** all four workstreams; every `tasks.md` item is checked. Production switches untouched: `platforms.ios` stays as stored, no Play URL entered.
- **Not done — owner gates before any rollout (in this order):**
  1. ~~Merge~~ done: PR https://github.com/akbarholturaev11-lang/HSK-AI-Bot/pull/300 → `main` `75795da5`. The production `platforms.ios` value was **not** read before the merge (Railway CLI login expired): the owner must confirm the iPhone PWA switch is OFF in Admin PWA.
  2. Real-device QA on staging, with `platforms.ios` ON there only: Telegram iOS → "Safari’da ochish" → does `openLink(…, {try_browser:"safari"})` really open Safari, and does the `#t=…` fragment survive? → same account, no onboarding repeat, install video, course, Pro/progress intact. Then Add to Home Screen: iOS gives the Home Screen app its own storage, so the learner signs in there once with the existing sign-in (expected, not a bug).
  3. Android: enter the real Play listing on staging, confirm `openLink` opens the Play Store app; empty URL → APK in chat.
  4. Check the install video still shows `hskai.app`, not an old hostname (section 5).
  5. Only then switch ON in production via Admin PWA; roll back by switching OFF (sessions, Pro and progress are untouched).
- **Follow-up (not in this change):** the Admin PWA dashboard card (`pwa_analytics_*` stack) still says iPhone PWA is not instrumented; the handoff counts are in the statistics reader, export and MCP only.

### Work log (append newest last)

| Step | Commit | Evidence |
| --- | --- | --- |
| Audit + OpenSpec plan | `81044433` | `openspec validate telegram-miniapp-pwa-android-handoff` → valid; baseline before changes: `tests/test_pwa_browser_auth.py tests/test_desktop_download_api.py tests/test_admin_pwa_marketing.py tests/test_android_contextual_app_promo.py` → 180 passed; `scripts/i18n_build_all_catalogs.py --check` → 0 stale |
| 1. Admin: `android_play_url` in `desktop_app_promo_settings` + signed `desktop_promo` command + editor field (`ui.admin_pwa.promoPlayUrl*`, iOS switch relabelled "iPhone PWA") | `029aa17d` | `tests/test_app_routing_settings.py` + `tests/test_admin_pwa_marketing.py` → 35 passed; real-SQL + virtual-WebAuthn browser run `python -m tests.e2e.admin_pwa_settings_browser` → passed (invalid listing never reaches the passkey sheet, valid one stored canonically, empty clears); i18n/catalog selection with CI synthetic env → 607 passed, 14 skipped. Field is optional in the command so an older cached editor cannot clear it. |
| 2. Secure handoff: `PwaAuthService.issue_handoff/redeem_handoff` on `desktop_link_requests` (`flow="miniapp"`, pre-approved, 120 s, `HMAC("pwa-handoff")` hash, PG advisory lock per learner, 5 per 10 min, newest supersedes); routes `POST /api/v3/pwa-auth/handoff/start` (fresh initData only), `POST .../handoff/redeem` (same-origin, 409 on other learner unless `switch`), `GET /iphone-pwa/handoff` (no-store, strict CSP, server-derived `?v=` tokens), `GET /iphone-pwa-handoff.js`; events `pwa_handoff_issued/completed` (+ `android_play_opened` name reserved); Li catalog `handoff.*` (6 keys, UZ/RU/TJ); CI lists updated | `21e74b00` | `tests/test_pwa_telegram_handoff.py` SQLite → 19 passed; same file on disposable PostgreSQL 15 (`NATIVE_ACCOUNT_TEST_DATABASE_URL`, port 55439, own DB) `HandoffPostgresConcurrencyTests` → 4 passed (8 parallel redeems → 1 session; 8 parallel issues → 5 rows/1 live/3×429; issue∥redeem no deadlock; two learners keep own accounts); PWA auth + Li catalog → 159 passed; i18n guards + desktop auth + iPhone PWA assets/navigation → 623 passed, 18 skipped, 1 failed = known `main` baseline `test_returning_user_skips_login_welcome_on_server` (login route untouched); `i18n_build_all_catalogs.py --check` → 0 stale. Landing page not yet browser-tested (task 3.3). |
| 3–4. Mini App routing + analytics: promo/status gain `ios` (needs `platforms.ios` **and** the PWA gates; "already has it" = a live PWA session; own 14-day cooldown) and `downloads.android_play` (Android is offered with a Play listing even without an APK); `desktop-download.js` iPhone sheet → one-time link → `openLink(url,{try_browser:"safari"})`, link reused while valid, strict URL checks; Android → Play listing (only `play.google.com/store/apps/details?id=com.pomp.hskai`) else APK to chat; 12 `ui.desktop_download.iphone.*`/`android.play` messages UZ/RU/TJ; `android_play_opened` → Android cooldown + funnel stage `play_opened` (reader, export, MCP cache); `iphone_pwa` statistics/export → `telegram_handoff.issued/completed`, install/activity stay `not_instrumented`; landing CSP `manifest-src 'self'` (bug found by WebKit), no forced focus; CI steps added | `29c85dcf` | New Playwright `tests/e2e/test_miniapp_app_routing.py` + `tests/e2e/test_pwa_telegram_handoff_page.py` → 17/17 Chromium and 17/17 WebKit; focused unit set (admin PWA, analytics, handoff, routing events, download API, inventory, settings, browser auth) → 899 passed, 77 skipped; PG 15 race tests → 4 passed; broad unit regression → 802 passed, 14 skipped, 1 failed = known baseline; e2e regression → 73 passed, 6 failed in `test_limit_and_release_regressions.py` — the same 6 fail on `main@675f6244` (checked in a clean worktree), so not a regression; `i18n_build_all_catalogs.py --check` → 0 stale; `openspec validate` → valid. Real Telegram/Safari/Play behaviour is **not** verified (no device). |
| Install guide e2e: intro → «Qanday?» → video, forward only, once per learner | `597dc310` | `tests/e2e/test_pwa_telegram_handoff_page.py` → 9/9 Chromium, 9/9 WebKit |
| CI fix: PR #300 `source-contract` failed with `source_bytes_changed app/static/admin.html` (frozen i18n source). The one legacy funnel row was reverted; `play_opened` stays in the statistics reader, export and MCP cache | `a0fea755` | Local run of the CI step `Read-only P0 source checks` → exit 0, review blockers 0; `tests/test_i18n_*.py` and Android analytics tests re-run |
| Merge: smoke test accepts Chromium `flow-end` (Playwright 1.65 reports `flex-end` that way; `main` failed the same; card-bottom geometry still checked); `miniapp-ui` re-run after a GitHub 15-min timeout during browser install | `63982255` → merge `75795da5` | PR #300 checks: 23 passed, 1 failed = `Native auth (macos-14)` GitHub runner "configuration not supported" (same on merged PRs #296/#297). `codex/local-ai`/`codex/cloud-ai` not synced: 84/92 commits not in `main` and 579 behind, so only a force/reset could align them — left untouched |
