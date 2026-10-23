# HSK AI ADMIN PWA ONLY — authoritative continuation handoff

> **Task scope:** ONLY HSK AI Admin PWA on `codex/admin-pwa`. This is a temporary task-specific handoff, NOT a global repo policy.
> **Last independently inspected branch head before this handoff update:** `86e8b5afee08be12fd330e3e67da433f5568794a` on 2026-10-23. **Always fetch branch HEAD again before coding.**

## Read first in every new chat (in this order)

1. `docs/admin-pwa/HSK_AI_ADMIN_PWA_TEMP_HANDOFF.md` (this file; current checkpoint).
2. `docs/admin-pwa/HSK_AI_ADMIN_PWA_TEMP_RULES.md`.
3. `docs/admin-pwa/HSK_AI_ADMIN_PWA_TEMP_CONTEXT.md`.
4. `docs/admin-pwa/HSK_AI_ADMIN_PWA_TEMP_FINAL_RESULT.md`.
5. `docs/admin-pwa/IMPLEMENTATION_PLAN.md`.
6. `docs/admin-pwa/PHASE_0_API_INVENTORY.md`.
7. `docs/admin-pwa/ADMIN_PWA_V10_UI_REFERENCE.md`.
8. Root `AGENTS.md`, `AI_RULES.md`, `PROJECT_MEMORY.md` and relevant source/test files; for UI/i18n also `localization/README.md` and repo skills.

## Desired final result (user-approved)

Build a separate **real-data**, responsive, installable HSK AI Admin PWA at **`https://hskai.app/admin`**, preserving the existing **Telegram Admin Mini App** at `/admin.html` and its verified Telegram initData login. Use V10 HTML only as UI/UX design reference; remove ALL fabricated data and mock actions. Reuse existing backend/services and canonical user identity; real stats, users, payments, HSK3.0, feedback and notifications must be correctly authorized.

First-time browser onboarding: verified **Google account + one-time Telegram admin approval** to link to the canonical admin, followed by registering a discoverable WebAuthn passkey. Later: **passkey-only login** (Face ID/Touch ID/Windows Hello/device PIN depending on authenticator) or direct open if session is valid, **without repeating Google every visit**. Google/Telegram are audited recovery methods. Sensitive financial/user-management operations need fresh action-bound passkey confirmation.

AI/ChatGPT/Cloud/local development analytics: build bounded, privacy-preserving **read-only** metrics+feedback export APIs (JSON/CSV), then optionally scoped MCP gateway, **never** AI write access to admin actions/production DB credentials.

## Current verified repository status

- Repo: `akbarholturaev11-lang/HSK-AI-Bot`.
- Work branch: `codex/admin-pwa`. Last inspected HEAD: `86e8b5afee08be12fd330e3e67da433f5568794a`. Inspect again when resuming.
- `main` was `e935e4315df42037d6aab4ab38b2c4e5d9bbb681` and **unchanged** at the verification before this handoff update.
- Branch was **23 commits ahead, 0 behind** `main` before this docs commit. Differences were task-scoped: 18 files, namely app bootstrap/session/models/migration/tests/env + `docs/admin-pwa`. Refresh this comparison next time.
- **No production deployment, no `main` merge, no real OAuth/passkey, no real PWA dashboard or real-data API** has been performed.

### Actual code already committed — DO NOT IMPLEMENT AGAIN

1. `app/admin_api/pwa_bootstrap.py`: isolated `GET /admin` and `GET /api/admin/v1/me` behind `ADMIN_PWA_ENABLED`. Default OFF returns 404. With flag ON and valid configured HTTPS origin, `/admin` still returns 503 until genuine login/UI exist; `me` authenticates only a valid existing DB session and returns minimal actor identity; it NEVER issues cookies.
2. `app/admin_api/pwa_sessions.py`: session verification checks SHA-256 hash of opaque cookie, DB row, revocation, expiry, valid auth method, current canonical `users.id` owner, blocked status and Telegram `ADMIN_IDS` allowlist. Cookie name `__Host-hskai_admin`. No session issuer and no browser login exists yet.
3. `app/db/models/admin_pwa.py`: `AdminPwaSession` table (user ID, token hash, auth method, creation/expiry/revocation).
4. `alembic/versions/0110_admin_pwa_sessions.py`: new migration, down revision `0109_public_site_traffic_daily`. **Real PostgreSQL migration not yet tested.** Check migration graph/current head before extending schema.
5. `app/db/models/__init__.py`: table registration.
6. `app/main.py`: includes new isolated router with existing DB session factory; does not edit legacy Telegram route handlers.
7. `app/config.py` and `.env.example`: `ADMIN_PWA_ENABLED=false`, `ADMIN_PWA_PUBLIC_ORIGIN=` (blank). **Do not enable in production.**
8. `tests/test_admin_pwa_bootstrap.py` and `tests/test_admin_pwa_sessions.py`: isolated tests, not a complete full-repo QA pass.
9. `docs/admin-pwa/ADMIN_PWA_V10_UI_REFERENCE.md`: reviewed demo structure, data traps, hash.

### Tests independently rerun 2026-10-23 in isolated local mirrors

- `PYTHONPATH=/mnt/data/admin-pwa-phase1-code python -m pytest /mnt/data/admin-pwa-phase1-code/tests/test_admin_pwa_bootstrap.py -q` → **4 passed, 17 subtests passed**.
- `PYTHONPATH=/mnt/data/admin_pwa_stage python -m pytest /mnt/data/admin_pwa_stage/tests/test_admin_pwa_sessions.py -q` → **9 passed, 5 subtests passed**.
- `python -m py_compile` on staged bootstrap, sessions, model and migration → success.
- These use **isolated, local staged code mirrors**; they do **not** prove that full GitHub checkout CI passed or that real Postgres/HTTPS/iPhone PWA works. Earlier staged SQLite ORM/migration smoke was reported, but has **not** been independently rerun in this handoff task.

## Exact V10 UI reference

- Original local reference file: `hsk-ai-admin-ux-demo-v10.html` (184,575 bytes).
- SHA-256: `8cd9375dd2ef7c27e9f17904000629060139ffb21c667a83c60b282ec321a9b9` (rechecked in the current container).
- It is **NOT committed to GitHub**. The user should attach this file in a new chat if not mounted. Do not invent a GitHub path or port the mock `v6Demo` data into production. More in `ADMIN_PWA_V10_UI_REFERENCE.md`.

## Outstanding work, accurately scoped

- [ ] Confirm **real** DNS, TLS, proxy, routing and Google OAuth callback settings for `https://hskai.app/admin`; WebAuthn RP ID `hskai.app`. These were **not confirmed live**.
- [ ] Reconcile existing auth architecture, canonical admin linking and threat model with the new session table and Alembic chain. Run real backend checkout/static checks before implementation.
- [ ] Build **first-time verified Google OIDC + one-time Telegram Bot admin approval** (persistent challenge, browser binding, nonce/state/PKCE/replay/CSRF/expiry/rate-limit), then trusted session issuance, logout/revocation. Preserve current Telegram initData auth.
- [ ] Build and test registered **WebAuthn passkey enrollment and passkey-only login**; physical-device PWA support cannot be claimed from mocks.
- [ ] Implement real secure PWA shell and V10 UI without mock data; connect read-only `me/summary` first, then metrics/users.
- [ ] Durable universal feedback inbox: BotFeedback and ReleaseFeedback already stored; Android bug report currently sent to Telegram, not stored in durable inbox; do not claim historical completeness.
- [ ] Fresh transaction-bound passkey step-up before exposing dangerous admin mutation routes.
- [ ] Scoped read-only JSON/CSV analytics and optional MCP; staging security/regression/real-device QA; owner-approved release only.

## Immediate next coding task (continue from here; DO NOT restart planning)

1. **Check GitHub current HEAD/diff**, existing files and global/task rules (do not rely on old SHA).
2. Inspect `app/api/native_oauth.py`, `app/services/google_auth.py`, `app/services/identity_link_service.py`, bot link callbacks and `app/admin_api/pwa_sessions.py`. Reuse verified Google subject primitives; NEVER use email as admin privilege.
3. Design and implement *one small reviewed increment*: persistent one-time **browser-admin approval challenge** bound to browser state and canonical admin; no session minting until linked Google subject and real Telegram Bot approval are verified. Add replay/cross-browser/non-admin/expiry/CSRF tests.
4. Keep `ADMIN_PWA_ENABLED=false` by default and `/admin` disabled until implementation/QA; do not change `/admin.html`.
5. After each increment, **update this file** with exact commit, code changed, test commands/actual results, blockers, and next task. Do not merge or deploy without the user's authorization.

## Release and reporting invariant

All scoped changes stay on `codex/admin-pwa` until explicit owner approval. Do not force push, rewrite history, remove unrelated files or silently alter other platforms. Only claim passing tests/deployment/device support with current evidence. Do not treat planning documents as proof of features.

### Historical note

Earlier `RESUME_NEXT_CHAT` messages and early status paragraphs stated no session model existed. Those described **earlier snapshots** and have been superseded by the verified session migration at `86e8b5af...`. This file is the current canonical continuation checkpoint.

## Implementation checkpoint — 2026-10-23, one-time approval component

- **Branch commit:** `7e7e2bb9c6792958d2e5d0e39a4a173ea4a4ab56` on `codex/admin-pwa`.
- **Changed code:** `app/admin_api/pwa_approval.py`, `app/db/models/admin_pwa_approval.py`, model registry import, `alembic/versions/0111_admin_pwa_approvals.py` and `tests/test_admin_pwa_approval.py`.
- **What it actually does:** stores an opaque 5-minute approval request with only SHA-256 of the high-entropy browser proof and a keyed Google subject hash provided by a **future verified OIDC callback**; verifies currently allowlisted Telegram admin IDs and canonical User rows in a **future trusted Bot update**; rejects Google-sub collisions; uses conditional SQL UPDATE for one-time approval and consumption; rechecks admin rights on consumption. Returns a typed approval result **but does not mint a session or provider linkage**.
- **Security boundary:** no route calls this module, no Bot callback is connected, and no OAuth OIDC callback is connected. Calling these functions with an unverified Google subject or browser-controlled Telegram ID would be unsafe; never wire directly to anonymous requests. The consumer must perform verified Google OIDC state/nonce/PKCE and canonical account provider linkage before a browser cookie can be issued. The module contains no bypass to existing Telegram Admin Mini App.
- **Tests actually run:** isolated SQLAlchemy SQLite prototype at `/mnt/data/admin-pwa-auth-increment/sandbox/tests/test_pwa_approval.py`: **6 passed** after fixing SQLAlchemy timezone comparison via `synchronize_session=False`; `python -m py_compile` of prototype files passed. Full checked-out repository unit tests, PostgreSQL concurrency, Alembic migration, staging, and real Google/Telegram approvals **have not been executed**. Source file committed to repository is `tests/test_admin_pwa_approval.py` and requires full repo test execution.
- **Next task:** inspect and run full repository tests for new model/migration; implement verified Google OIDC callback + session-bound HttpOnly pending proof, trusted Bot approval handler, atomic canonical Google identity linking, and secure cookie issuance **behind disabled-by-default feature flag**. Keep `/admin` blocked until all auth invariants pass. Then implement discoverable WebAuthn/passkey.
- **Main/production:** no changes; code committed only to `codex/admin-pwa`.


## Implementation checkpoint — 2026-10-23, atomic Google identity finalization

- **Working branch:** \`codex/admin-pwa\`. Code commit \`8bc5763f859bc6bb9a122ea23fc91e18466cc315\`; isolated tests commit \`229abc12f6f4f14cae7f1d0ea611ef21d51f19b3\`.
- **New code:** \`app/admin_api/pwa_enrollment.py\` exports \`finalize_google_admin_enrollment\`, a **non-route, non-session-issuing** helper. It requires a separately verified Google OIDC identity, an approved request and the matching browser-only proof. It checks the server-keyed Google subject hash and exact audience, current canonical Telegram admin ownership/allowlist, blocked status and expiration. Within one database transaction it calls existing \`IdentityLinkService.link_to_user\` and conditionally consumes the one-time approval. A link collision or conditional consumption race rolls back both writes.
- **New tests:** \`tests/test_admin_pwa_enrollment.py\` covers canonical-user binding, browser replay, mismatched proof/subject/audience/provider, expiry, permission revocation, owner Telegram ID change, pre-bound Google subject, malformed request ID and atomic rollback on simulated conditional-update race.
- **Executed locally:** \`python -m py_compile\` on new staged code and tests passed; isolated SQLAlchemy **SQLite** harness with reduced stubs of the existing models/services: \`PYTHONPATH=. pytest -q test_admin_pwa_enrollment.py\` -> **7 passed, 4 subtests passed**. **Important limitation:** this was NOT run from a full checkout against real repository dependencies; neither full-repo pytest, live PostgreSQL transaction/concurrency, Alembic, GitHub CI, Google OAuth nor real Telegram callback were verified. Repo test file is committed for proper CI/full-checkout execution.
- **Security boundary:** this function must ONLY receive \`VerifiedIdentity\` from a trusted callback after Google signature/issuer/audience/state/nonce/PKCE checks. Never accept user-supplied provider attributes or Telegram IDs. Caller must enforce feature flag, canonical origin, CSRF, HTTP-only proof cookie, rate limits and session issuance separately. Previous standalone \`consume_pwa_approval\` remains unused by routes and must NOT become a production login shortcut.
- **Still NOT built:** persistent browser Google OAuth state/start/callback, Bot deep link/callback, session-cookie issuance/logout, passkeys, PWA UI, analytics, staging/release. \`ADMIN_PWA_ENABLED=false\` unchanged; \`main\` and \`/admin.html\` untouched.
- **NEXT:** first execute the committed enrollment tests in a full checkout with current dependencies and PostgreSQL; then implement separately verified browser-bound Google OIDC state + callback and authenticated Telegram Bot approval transport, calling this transaction-safe finalizer. Never enable PWA admin sessions before all proofs and identity linking are verified.

- **Test correction commit:** `d167e534011453068344a788dcfaaafd0e39e64d` aligns the SQLite adapter with existing repo test style (`Session(self.engine)`), so ORM state expires after separate approval/finalization commits. The reduced local harness was rerun after this correction: **7 passed, 4 subtests passed**. Full checkout/CI/PostgreSQL remains unverified.


## Implementation checkpoint — 2026-10-23, browser-bound Google OAuth state (service only)

- **Working branch:** `codex/admin-pwa`. New rule commit `d4ba5353ddd47ed07816601a1ca8de5b9ba1d93f`; model `0b44ea84737d4931f25fb57556e6c8159f0e9f6d`; state service `7c3b1f76a495a3d57c23b9276ddfd9162049d421`; migration `bdc6b17a29cdf575d3dd6ad3005727c12d95ef4f`; model registration `3c7aa7fcae4b85bb8fd07889291bada2e3f87661`; tests `cddd6ff905905d80e402db513b9d1cbaa6072f8b` + provider/audience cases `ee9912043bd5e7510e9f2556e9b0a1debec79196`.
- **New task rule:** For UI/UX missing from verified V10 demo, **read and apply available repo design skills first**, at least `.agents/skills/hsk-ai-ui/SKILL.md`; use `frontend-design` if installed and `webapp-testing`/Playwright for QA. Keep V10 style and original metrics isolation. The repository `hsk-ai-ui` and `webapp-testing` skills were actually read for this task, but **no frontend/UI was implemented in this increment**; no visual QA claimed.
- **New files:** `app/db/models/admin_pwa_oauth.py`; `alembic/versions/0112_admin_pwa_oauth_attempts.py` (down revision `0111_admin_pwa_approvals`); `app/admin_api/pwa_oidc.py`; `tests/test_admin_pwa_oidc.py`; `app/db/models/__init__.py` registration.
- **Implemented (NOT exposed as routes):** `start_admin_pwa_google` reserves a ten-minute, one-time DB request with only a SHA-256 browser proof; HMAC-derived random-state MAC, OIDC nonce and PKCE verifier use the existing server secret under separated Admin PWA purposes. The Google authorization URL uses the *desktop web OAuth client audience* and pinned `ADMIN_PWA_PUBLIC_ORIGIN + /api/admin/v1/auth/google/callback`. `finish_admin_pwa_google` verifies state MAC, HttpOnly-browser proof, TTL and one-time status before calling existing `google_auth.exchange_code` and `verify_desktop_id_token`; rejects different provider/audience; conditional SQL UPDATE and same-session `start_pwa_approval` commit transfer into pending Telegram approval exactly once. Google network exchange is performed with no open DB transaction. This module NEVER creates a cookie, identity link, passkey or Admin PWA session.
- **Feature gates:** `ADMIN_PWA_ENABLED=false` stays default and rejects both new service operations; canonical HTTPS origin, existing Google web client configuration and 32+ byte signing secret are required. No DNS, Google Console callback, redirect, webhook or production settings were changed.
- **Local validation:** `python -m py_compile` on isolated new model and OIDC service succeeded. A locally staged SQLite/SQLAlchemy harness that stubs native `google_auth`, `DesktopAuthService` and `IdentityLinkService`, exercises `start_admin_pwa_google` / `finish_admin_pwa_google` with mocked Google verification: **9 passed, 7 subtests passed** (`PYTHONPATH=. python -m pytest -q test_admin_pwa_oidc.py` in `/mnt/data/admin_pwa_increment`). The checked-in repo tests use mocks for the real Google token exchange/verification but **have not been executed from a full GitHub checkout**. NOT verified: real PostgreSQL, real Alembic upgrade/rollback, real Google OIDC, concurrency under PostgreSQL, bot callback, production HTTP/cookie/CSRF, or full CI.
- **Security boundary / next:** No HTTP endpoints for these functions exist yet, so nothing can log in. A future **rate-limited** Admin PWA HTTPS route must enforce exact `Origin` and CSRF on start and deliver its `browser_proof` only through a `Secure; HttpOnly; SameSite=Lax; Path=/` `__Host-` host-only cookie, never in JSON or URL. Callback must validate cookie on canonical origin, then set returned Telegram-approval proof in a separate HttpOnly cookie; a trusted private Bot confirmation route must explicitly verify the allowlisted admin and bind identity via `pwa_enrollment.finalize_google_admin_enrollment` before separately reviewed session issuance. Add rate-limit/flood controls, negative tests and full repo/PG tests **before wiring routes**. Use the repo UI skills for any missing login/approval screen. Do NOT expose `/admin`, mint a cookie or enable the feature flag yet.
- **Unchanged:** `main`, `/admin.html`, existing Telegram initData guard, native Google/Apple login code, production services and routes, `ADMIN_PWA_ENABLED=false`.

- **Origin validation hardening:** service commit `c0bdb7fba7b799021006e7ec17ff51510b8af5c5` handles malformed `urlsplit()` inputs fail-closed; test commit `a89d1ca1bdf1f7f69aae6fb3b3939c7059cfb1e5` adds the malformed-URL case. Local staged regression command `PYTHONPATH=. pytest -q test_admin_pwa_oidc.py test_admin_pwa_enrollment.py` in `/mnt/data/admin_pwa_increment` => **16 passed, 11 subtests passed**, with patched Google and reduced model/service stubs; full repo/CI/PostgreSQL still NOT run.


## Implementation checkpoint — 2026-10-24, guarded Google OAuth HTTP transport

- **Working branch:** `codex/admin-pwa` only. Added SQL-backed global admission control to `app/admin_api/pwa_oidc.py` in `330a7013ea412f55df3ce143c4490459d91ff7db`; new browser HTTP adapter `app/admin_api/pwa_google_transport.py` at `4250fdef84e009c2bb7cdeb94183321c82211475`; registered router in `app/main.py` at `3ab59559ebb7b5ba79756f69266d97f3134ad4af`; extended state tests `7789a4c4210298a4223ed1c90c39b40bd3ab5411`; created HTTP contract tests `2c31547ff9d7498d61ca02d2fc1089efbb397a5a`.
- **Routes now mounted, BUT disabled by default:** `POST /api/admin/v1/auth/google/start` and `GET /api/admin/v1/auth/google/callback`. They require `ADMIN_PWA_ENABLED=true` *and* exact configured HTTPS host; flag remains `false` in project configuration and `.env.example`. Existing `/admin` remains unavailable, and `/admin.html` with Telegram signed `initData` was not changed.
- **What start does when deliberately enabled in a safe environment:** requires exact nonempty same-origin `Origin`, rejects non-same-origin Fetch Metadata and cross-site-form content types, creates a 10-minute DB-backed OAuth state and exchanges browser-generated secret **only through** `__Host-hskai_admin_oidc` (Secure, HttpOnly, SameSite=Lax, Path=/, host-only) cookie. JSON response only includes Google authorization URL. No client-supplied Google subject, Telegram ID or account privilege accepted.
- **What callback does:** requires canonical HTTPS host and top-level navigation, rejects duplicated query parameters and provider errors; calls the previously written OIDC verifier using browser-bound proof, Google state/nonce/PKCE and exact configured audience. Returns a pending Telegram approval request identifier and transfers the **different** short-lived browser proof to `__Host-hskai_admin_approval` Secure HttpOnly cookie, never JSON. Does **NOT** link the account, approve Telegram, mint `__Host-hskai_admin` session, show dashboard or grant permissions. Unsuccessful/invalid callbacks clear OAuth state cookie; server responses are `no-store` and `no-referrer`.
- **Rate limiting:** global ceiling 60 OAuth starts per 10-minute window, using real SQLAlchemy `COUNT` of attempt rows and a PostgreSQL advisory transaction lock so replicas cannot all pass one limit simultaneously. This is an initial *global* limiter only: malicious clients could exhaust it and deny legitimate admin starts. Add per-client/server-edge rate-limits and operational backoff before staging/production release. DB attempt retention/cleanup is not implemented.
- **Local verification actually executed:** `python -m py_compile` on new transport and staged security services/tests succeeded. Local isolated mirrors, with mocked provider, SQLAlchemy SQLite models/services and FastAPI TestClient: `PYTHONPATH=. python -m pytest -q test_admin_pwa_google_transport.py test_admin_pwa_oidc.py test_admin_pwa_enrollment.py` under `/mnt/data/admin_pwa_increment` -> **29 passed, 19 subtests passed**. The checked-in HTTP test module and amended OIDC tests have equivalent coverage but were **NOT** run in a full GitHub checkout. No real PostgreSQL advisory-lock contention, Alembic upgrade, Google Console callback, Bot, CI, staging, live HTTPS, PWA or physical-device verification was performed.
- **Remaining auth gates:** real Telegram private callback and allowlist verified for each approval; browser-only approval polling/consumption; atomic canonical identity-link finalizer; thoroughly checked Secure HttpOnly *admin session issuer*; logout/revocation; WebAuthn credential registration/standalone passkey sign-in and sensitive-action step-up. Never turn on Admin PWA production flag before these and dedicated negative/regression tests.
- **Next safe increment:** inspect bot handlers, add an isolated, private one-time Telegram Admin PWA Bot approval deep-link + callback (not `tg_identity` native flow), with explicit allowlist, privacy, expiry/replay and negative tests. Implement read-only pending status without leaking proof; session issuance remains separate. Verify end-to-end Google callback → Bot approval → canonical link on staging before any session. Preserve the UI rule: if implementing UI not in V10 demo, apply in-repo UI/UX skills and visual tests first.
