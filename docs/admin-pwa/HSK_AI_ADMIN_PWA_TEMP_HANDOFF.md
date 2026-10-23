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
