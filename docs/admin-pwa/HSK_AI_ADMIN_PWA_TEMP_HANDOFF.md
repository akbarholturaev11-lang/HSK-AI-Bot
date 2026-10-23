# Admin PWA — RESUME HERE (temporary cross-chat handoff)

> **SCOPE: HSK AI ADMIN PWA ONLY** — temporary task file. Work branch: `codex/admin-pwa`.
> Not a repository-wide policy. Does not modify or supersede root `AGENTS.md` / `AI_RULES.md` / `PROJECT_MEMORY.md`.
> All development and progress records for this task remain under `docs/admin-pwa/`.


**Read this first on every new chat.** Then read `HSK_AI_ADMIN_PWA_TEMP_RULES.md`, `HSK_AI_ADMIN_PWA_TEMP_CONTEXT.md`, `HSK_AI_ADMIN_PWA_TEMP_FINAL_RESULT.md`, `IMPLEMENTATION_PLAN.md` and `PHASE_0_API_INVENTORY.md`. Root `AGENTS.md`, `AI_RULES.md` and `PROJECT_MEMORY.md` still apply. All references are relative to `docs/admin-pwa/` except root files.

## Verified checkpoint — 2026-10-23

- Repo: `akbarholturaev11-lang/HSK-AI-Bot`.
- Working branch: `codex/admin-pwa`; original `main` head at audit: `e935e4315df42037d6aab4ab38b2c4e5d9bbb681`. **Re-fetch both branch heads before editing; do not treat these historical SHAs as current.**
- Previously committed architecture plan: `docs/admin-pwa/IMPLEMENTATION_PLAN.md` (latest then `d5f93b20c96f6961beb287171561a8d4d1d7014c`).
- Previously committed API analysis: `docs/admin-pwa/PHASE_0_API_INVENTORY.md`.
- This turn creates scoped rules/context/target/handoff files only. **No Admin PWA application code, WebAuthn auth logic, Google-admin onboarding, DB migration, frontend integration, real API wiring, production deployment, domain/TLS verification or real-device biometric testing has been completed.**
- Initial API inventory contains 44 existing admin-miniapp POST routes, some mutation-heavy. The native Android bug-report path sends to Telegram and has no durable inbox insert in inspected handler.
- The approved order is domain/contract audit → Google + once Telegram link → **passkey-only returning login** → protected PWA shell/V10 real-data dashboard → stats → durable inbox → transaction-bound passkey for dangerous actions → admin writes → read-only AI export/MCP → staging/release.

## Verified completed tasks

- [x] Found existing project repo and separated working branch from `main`.
- [x] Reviewed main Telegram admin auth and service/feedback model inventory.
- [x] Recorded long implementation plan including Google/TG link, passkey-first login, domain choice and staged sequencing.
- [x] Recorded endpoint risk inventory and data-persistence gaps.
- [x] Created temporary scoped project documentation (this set).
- [ ] Verified live `https://hskai.app` TLS, reverse proxy, Google OAuth redirect, PWA scope and RP ID on real target.
- [ ] Detailed API read/write/danger inventory signed off with current code as opposed to stale branch snapshot.
- [x] Verified actual V10 HTML demo bytes in conversation workspace (184,575 bytes; SHA-256 `8cd9375dd2ef7c27e9f17904000629060139ffb21c667a83c60b282ec321a9b9`); mapped components in `ADMIN_PWA_V10_UI_REFERENCE.md`. Source is **not** in GitHub and must be explicitly made accessible to future implementation environments.
- [ ] Any code for browser identity, cookie sessions, Google link, Telegram approval challenge or WebAuthn.
- [ ] Any real PWA frontend/API, real-data stats/inbox, MCP/export service or staging deployment.
- [ ] Any automated E2E, security test, manually tested iPhone biometric, or production release.

## NEXT ACTION — Phase 0 closeout, then Phase 1A

1. Check `codex/admin-pwa` HEAD vs `main` and diff; verify no unexpected changes.
2. Inspect actual host mappings, bot login/challenge callbacks and existing Google ID linking; verify target hostname HTTPS/route or explicitly log an unavailable live verification.
3. Extend the admin endpoint matrix as needed, define exact `AdminActor` contract, browser-session threat model and DB schema; review against `PHASE_0_API_INVENTORY.md`.
4. Obtain V10 demo bytes before converting frontend; treat design only.
5. Implement minimal isolated server-side admin session and one-time Google+Telegram link with disabled-by-default route/flag and unit/security tests. Preserve Telegram initData handler. **Do not create a passkey UI button until server assertion verification is real.**
6. Update this file with exact commits, tested commands/results, unresolved risks and next smallest unit of work after *each* genuine implementation step.

## How to record subsequent progress

Add under a dated heading:
- **Branch/head:** actual SHA at time.
- **Scope/files changed:** names, whether read-only or mutating.
- **Outcome:** observed behavior and evidence; no estimates declared as fact.
- **Tests actually run:** commands, pass/fail/skip, environment/staging target.
- **Remaining risks/blockers:** distinguish not-tested from broken.
- **Next action:** one narrow build/test task.
- **Main/production:** explicitly state untouched or exact approved change.

Do not write “done”, “tested”, “linked”, “deployed” unless verified in the same task. Do not manufacture status from an earlier assistant reply.

## Implementation checkpoint — 2026-10-23, first code increment

- **Branch:** `codex/admin-pwa`; branch commit for this increment is the commit containing this handoff update (inspect GitHub HEAD).
- **Code:** new `app/admin_api/pwa_bootstrap.py`; route reservation `GET /admin` and `GET /api/admin/v1/me`. Both return 404 while `ADMIN_PWA_ENABLED=false` (the default). When explicitly enabled but origin is not a bare HTTPS origin, both return 503 `admin_pwa_origin_unconfigured`; with valid origin but without a real login verifier, both return 503 `admin_pwa_auth_not_ready`. No user data or session token is minted.
- **Wiring:** `app/main.py` includes only this new router. `app/config.py` + `.env.example` add the disabled-by-default `ADMIN_PWA_ENABLED` and blank `ADMIN_PWA_PUBLIC_ORIGIN` settings. Existing `/admin.html` and `/api/admin-miniapp/*` implementations were not edited.
- **Tests actually run in a local isolated module copy:** `PYTHONPATH=/mnt/data/admin-pwa-phase1-code python -m pytest /mnt/data/admin-pwa-phase1-code/tests/test_admin_pwa_bootstrap.py -q`: **4 passed, 17 subtests passed**. `python -m py_compile` for new files passed. This does not establish a full repository or deployment E2E pass. Test source is committed as `tests/test_admin_pwa_bootstrap.py`.
- **Domain:** `https://hskai.app` was not accessible in the external browser check in this turn, therefore DNS, TLS, proxy, RP ID and Google callback remain **unverified**. Never enable the flag on production based on this work alone.
- **No production authentication:** Google/Telegram one-time linking, passkey registration/sign-in, backend session tables, cookie+CSRF management and protected data endpoints **remain unimplemented**. This is route safety groundwork only, not a usable login.
- **Next action:** define verified AdminActor and one-time Google OIDC + Telegram Bot approval state transitions and persistence schema with replay/cross-browser tests; only after implementation change the 503 guard under an explicit staging gate. Obtain and visually audit the V10 demo bytes (available in conversation workspace) before PWA frontend conversion.
- **Main/production:** unchanged by this branch-only commit.

## UI source reference — 2026-10-23

- Local V10 demo identified and hashed, HTML/view functions mapped. See `docs/admin-pwa/ADMIN_PWA_V10_UI_REFERENCE.md`.
- A later Codex agent must **not infer** that the V10 HTML is committed. The file lives in this conversation's mounted files, so it needs the actual bytes for porting.


## Implementation checkpoint — 2026-10-23, browser-session guard

- **Branch:** `codex/admin-pwa`; inspect current branch HEAD for this commit.
- **Backend files:** `app/db/models/admin_pwa.py` and `alembic/versions/0110_admin_pwa_sessions.py` add revocable hashed-cookie sessions. `app/admin_api/pwa_sessions.py` authenticates only an existing DB session and rechecks the user's *current* Telegram allowlisted admin identity and blocked status. `app/admin_api/pwa_bootstrap.py` now uses this guard for `GET /api/admin/v1/me`, with same-origin HTTPS checks. `app/main.py` passes the existing async session factory. Root `app/db/models/__init__.py` registers the table.
- **Security state:** route flag still defaults **off**. `GET /admin` remains 503 under an enabled flag. No public endpoint can mint a PWA cookie or create a login; no Google/Telegram/Passkey registration, OAuth callback or production admin control has been exposed.
- **Isolated tests actually run:** 9 unit/ASGI tests passed, 5 subtests passed using local isolated module copy. Python compile passed; SQLite ORM table and Alembic migration upgrade/downgrade smoke each passed in isolation. **Full repository CI, real Postgres migration, real-domain HTTPS and physical iPhone passkey testing NOT run.**
- **Next action:** implement verified first-time Google OIDC and one-use Telegram approval challenge with persistent state, explicit browser binding, CSRF and replay tests, then a trusted cookie issuer/logout, still behind disabled-by-default flag; ensure Telegram app regression.
- **Main/production:** unchanged.
