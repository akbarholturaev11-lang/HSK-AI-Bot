# HSK AI — Telegram to PWA / Android routing: cross-chat context

> **Single continuation file for this proposed feature.** Read this file in every new chat before changing the feature. Keep it short and factual; update this file in place, not with new handoff copies.
>
> **Status:** implementation in progress on a feature branch — see **Current state** at the end. No production switch has been changed and nothing is released.
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

- **Branch:** `feat/telegram-pwa-android-handoff-20261110` (worktree `.claude/worktrees/telegram-pwa-android-handoff`), based on `main@675f6244`. Nothing pushed.
- **Plan of record:** `openspec/changes/telegram-miniapp-pwa-android-handoff/` (proposal, design, two spec deltas, `tasks.md`); `openspec validate` passes. `tasks.md` is the only checklist; this section is the status log.
- **Audit corrections to sections 2–4 above (verified in source):**
  - Independent iPhone/Android ON/OFF already exist: `desktop_app_promo_settings.platforms.ios/android`, edited by the signed Admin PWA `desktop_promo` command. **No new flags.** Only `android_play_url` is added to that setting/editor.
  - **No new table/migration.** Handoff reuses `desktop_link_requests` with `flow="miniapp"`, `platform="pwa"`, `intent="signin"`, pre-approved, 120 s TTL; secret hashed under its own HMAC purpose. Existing bot approval, native poll, Telegram claim and OAuth callback already refuse such a row.
  - Server hard-coded `ios: False` and the decision service knew only native platforms — both must be extended; an active PWA session counts as "already has it".
  - Transfer secret travels in the URL **fragment** only (never query/path), cleared by the landing script before the same-origin redeem.
  - A different account already signed in on the browser is never replaced without an explicit switch; a signed-out browser is signed in directly (login-CSRF residual risk accepted and documented in `design.md`).
- **Done:** audit, OpenSpec plan.
- **In progress / next:** see the log below.

### Work log (append newest last)

| Step | Commit | Evidence |
| --- | --- | --- |
| Audit + OpenSpec plan | (this commit) | `openspec validate telegram-miniapp-pwa-android-handoff` → valid; baseline before changes: `tests/test_pwa_browser_auth.py tests/test_desktop_download_api.py tests/test_admin_pwa_marketing.py tests/test_android_contextual_app_promo.py` → 180 passed; `scripts/i18n_build_all_catalogs.py --check` → 0 stale |
