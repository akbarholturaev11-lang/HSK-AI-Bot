# HSK AI — Telegram Mini App + iPhone PWA shared-web handoff

**Read this FIRST in a new chat.** This is the continuity contract for building
the PWA incrementally in the EXISTING HSK AI project, without rewriting the
mobile course or duplicating payment, progress, entitlement or translation logic.

## User-approved product decision

- One WEB learner UI: `app/static/course-v3.html` and existing
  `course_v3_*.html` plus their current static modules. The same screens serve
  the Telegram Mini App and standalone iPhone/Safari PWA.
- Keep Android native (direct APK / Play product flavors), desktop Tauri
  (macOS/Windows), bot, FastAPI backend, PostgreSQL, canonical `users.id`.
- The PWA is a distribution/host adapter, **NOT** a second course app.
- Continue Local-First UZ/RU/TJ catalogs from the localization work branch.
  Never restore hard-coded UI text or fetch translations individually per call.
- Existing Google/Apple/Telegram canonical identity model from
  `codex/universal-sign-in` must be reused. Do not create fake Telegram
  IDs, trust emails for merging accounts, or spoof WebApp initData.
- Reuse server-owned lesson grading, XP, progress, access/Pro decisions,
  subscription receipts and admin review. No new payment rules.
- Do not update `main`/Railway production or unlock public registration until
  the universal sign-in, localization and PWA acceptance gates are met.

## Git coordination

Repository: `akbarholturaev11-lang/HSK-AI-Bot`

PWA working branch: `codex/pwa-miniapp-shared-foundation-20261019`.
Based on `codex/universal-sign-in` at
`12759a3658470a00f88bc6e0fa79b65ad1126e61` at creation.
Source account PR: https://github.com/akbarholturaev11-lang/HSK-AI-Bot/pull/182
Localization PR: https://github.com/akbarholturaev11-lang/HSK-AI-Bot/pull/179
PWA PR: check this branch's open Draft PR on GitHub before making changes.
**Read current remote HEAD and CI; the SHAs above are historical anchors.**

Localization branch:
`codex/i18n-local-first-foundation-20261017`.
Handoff: `localization/NEXT_CHAT_HANDOFF.md` and
`localization/PLAN_SCHEMA_ORDER.md`.
It has been concurrently editing `app/static/course-v3.html`,
`subscription.html`, other practice pages, and Desktop i18n.
**Do not hard reset, rebase, force push, replace a large HTML file with an
old version or blindly merge either draft PR.** Integrate final branches
with scoped conflict resolution and regression QA after both are ready.

Read `AGENTS.md`, `AI_RULES.md`, `PROJECT_MEMORY.md`,
`OAUTH_SETUP.md`, `docs/UNIVERSAL_NATIVE_ACCOUNTS.md` and
`docs/UNIVERSAL_NATIVE_ACCOUNT_QA.md` before touching auth/DB.

## Phase 1 — IMPLEMENTED ON THIS PWA BRANCH: install foundation only

- Existing Mini App course HTML now references one PWA manifest, the existing
  PNG app icon, and `pwa-bootstrap.js` (no cloned frontend).
- `app/api/pwa.py` exposes only three versioned-install resources at
  `/pwa.webmanifest`, `/pwa-bootstrap.js`, `/pwa-sw.js`.
- Manifest launch uses existing `/course-v3.html?source=pwa`; source query
  is NOT authentication, user identity, nor authorization.
- Read-only host detector exports `window.HSKAI_WEB_HOST` with mode
  `telegram-miniapp` when verified Telegram initData is *present on the client*,
  otherwise `browser`. Client detection is UI context only, **never proof of
  identity**; server still verifies initData.
- Bootstrap does NOT register a service worker in an authenticated Telegram
  Mini App. Browser-only service worker intercepts strictly two public image
  paths (logo/avatar). No auth, lessons, paid JSON, API, checkout, HTML,
  offline exercises, profiles, progress or audio cached.
- Existing Mini App still requires Telegram initData to load the course.
  **A Safari-installed PWA will currently show the existing auth gate.**
  Phase 1 is NOT independent PWA login or usable offline learning.
- Initial PNG icon is the existing 256px branding asset; before public
  release verify installed icon quality and add proper 192/512 PNG assets if
  needed. Manifest scope is root due to existing cross-page routes; audit
  future web/navigation scoping before release.
- No DB migrations, no provider credential changes, no business rules modified.

## Phase 2 — NEXT TASK: independent browser authentication

**Implement safely on this same PWA branch, do not start over.**
Use the existing verified Google/Apple OIDC provider backend without accepting
native tokens into the browser via URL or allowing `miniapp` link-only proofs
to mint sessions. Define a distinct `pwa` sign-in platform/session contract.
Use authorization code + state + PKCE and origin/callback allowlists. Implement
an authenticated secure `HttpOnly` + `Secure` browser cookie session
(`SameSite` policy matched to callback flow) and CSRF defense for mutating
requests; protect against session fixation and logout replay. Refresh and revoke
browser sessions server-side. Do not put access tokens in localStorage,
sessionStorage, query strings, or client telemetry. Apple login requires its
own configured developer credentials; Google can be piloted first.

Do not use `telegram_id=NULL` as a common owner. Canonical `users.id` is
the account key. No automatic email merge. Explicit provider attachment
requires verifying possession of both accounts. Blocked users must remain
blocked. Preserve Mini App's signed `X-Telegram-Init-Data` transport.

## Phase 3 — shared course API/auth adapter

- Introduce a single web actor-resolution contract: real signed Telegram
  initData OR verified PWA browser session -> canonical user.
- Migrate relevant entry points in small batches: `/api/v3/map`,
  `/api/v3/course-tracks`, lesson unlock/complete, exam start/complete,
  practice/daily gates, preferences, onboarding, notifications, rating,
  voice, AI and trial/PRO gates.
- Update the existing `course-v3.html` wrappers and follow-on pages to call
  a shared web transport rather than using `!INIT_DATA` as a generic
  no-account condition. Do not relax entitlements or pretend a session exists.
- Resolve local browser cache keys using confirmed user scope, not
  `tg.initDataUnsafe.user.id` or unscoped `hsk_memo`. Account switch/logout
  clears or partitions private course state. Prevent stale in-flight responses
  from restoring another user's state.
- Keep locale files from localization branch as cached versioned resources,
  but do not publish Pro lesson/answer data to public offline assets.

## Phase 4 — checkout, offline, testing, release

- PWA browser checkout uses allowed **web/direct** payment flow with canonical
  `users.id`, receipt upload and existing admin review, not Apple IAP.
  Google Play direct-vs-play rules remain unchanged.
- Design authenticated offline assets explicitly by entitlement, origin,
  local data encryption/privacy needs and revocation. Do not cache protected
  lesson JSON or answer keys merely because a Service Worker exists.
- Verify on iPhone Safari (Add to Home Screen + standalone), normal Safari,
  Android Chrome, and Telegram Mini App on iOS+Android:
  fresh account Google sign-in; linked Telegram account parity; Free/Trial/
  paid/expired/blocked access; HSK 2.0+3.0; lesson 5; graded answer/XP/
  progress; AI Voice/microphone; purchase pending/approve/reject; logout/
  account-switch; UZ/RU/TJ; offline/online/upgrade; cache and bfcache;
  correct back and deep-link behavior. Also test Android native+Desktop parity.
- Keep staging origin, database, app credentials, Telegram bot and receipts
  isolated. Do not deploy to production without owner acceptance.

## Reproducible phase-1 checks

```bash
python -m unittest tests.test_pwa_foundation
python -m compileall -q app/api/pwa.py tests/test_pwa_foundation.py
node --check app/static/pwa-bootstrap.js
node --check app/static/pwa-sw.js
```

On a **separate staging backend**, check HTTP 200 and Content-Type for the
three PWA files, HTTPS/SW registration, manifest `start_url`, PNG icon, no
Console errors, install behavior, and existing Telegram initData course
flow. `tests/test_pwa_foundation.py` is source/route contract only. It does
NOT prove web PWA login, iOS install quality, live backend behavior or CI
promotion readiness.

## First priority in next chat

Check PWA branch tip and Draft PR, account/localization PR status and
latest CI first. Complete browser-session design/implementation (Phase 2)
without changing Mini App entitlement or canonical user behavior. Work on
PWA branch; document decisions and update this handoff in the same commit.
