# HSK AI ADMIN PWA — ONLY THIS TASK (temporary project files)

**Continue implementation:** [HSK_AI_ADMIN_PWA_TEMP_HANDOFF.md](HSK_AI_ADMIN_PWA_TEMP_HANDOFF.md) — authoritative current code checkpoint and next task.

**Copy into a new chat:** [HSK_AI_ADMIN_PWA_NEXT_CHAT_START.md](HSK_AI_ADMIN_PWA_NEXT_CHAT_START.md) — concise, ready-to-paste instruction.

Read in order:
1. [HSK_AI_ADMIN_PWA_TEMP_HANDOFF.md](HSK_AI_ADMIN_PWA_TEMP_HANDOFF.md) — current checkpoint, what is / is not implemented
2. [HSK_AI_ADMIN_PWA_TEMP_RULES.md](HSK_AI_ADMIN_PWA_TEMP_RULES.md) — scoped working rules, branch discipline, auth/data/UX invariants
3. [HSK_AI_ADMIN_PWA_TEMP_CONTEXT.md](HSK_AI_ADMIN_PWA_TEMP_CONTEXT.md) — owner requirements, repository facts, design choices
4. [HSK_AI_ADMIN_PWA_TEMP_FINAL_RESULT.md](HSK_AI_ADMIN_PWA_TEMP_FINAL_RESULT.md) — final production behavior, detailed acceptance checklist
5. [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) — phases and dependency order
6. [PHASE_0_API_INVENTORY.md](PHASE_0_API_INVENTORY.md) — existing endpoints and security risks

> **NOT GLOBAL RULES.** These files are temporary and apply **only to the HSK AI Admin PWA work on `codex/admin-pwa`**. Do not apply them to Android, courses, public site, Telegram Bot or other projects. Root rules still apply.

**Project branch:** `codex/admin-pwa`. **Public target (not yet verified live):** `https://hskai.app/admin`.

**Current state (checked 2026-10-23):** first-phase **fail-closed route bootstrap AND DB-backed revocable hashed-cookie session verification**, admin session model and migration committed (`app/admin_api/pwa_bootstrap.py`, `app/admin_api/pwa_sessions.py`, `app/db/models/admin_pwa.py`, `alembic/versions/0110_admin_pwa_sessions.py`). **Feature flag OFF by default; no trusted cookie issuer, Google+Telegram pairing, passkey login, usable PWA frontend, real-data dashboard, staging deployment or production release yet.** Isolated staged tests rerun: 4 bootstrap + 9 session tests passed (17 + 5 subtests); full-repo E2E not run. The handoff file is the source of truth; do not trust an older README snapshot.

Global `AGENTS.md`, `AI_RULES.md`, `PROJECT_MEMORY.md` and `localization/README.md` remain authoritative alongside the user's requirement to work solely on the selected project branch until explicitly authorized to promote.

These are **temporary task-scoped documents**. Keep them synchronized during work; archive only after final acceptance, without deleting useful evidence or overwriting unrelated rules.

**Verified V10 reference:** [ADMIN_PWA_V10_UI_REFERENCE.md](ADMIN_PWA_V10_UI_REFERENCE.md). Original demo HTML is a conversation-mounted file, **not a GitHub copy**; upload it to a new chat before porting. Existing Telegram Admin Mini App and `main` remain unchanged.

## Latest scoped checkpoint (2026-10-23)

New `app/admin_api/pwa_enrollment.py` atomically consumes the already-approved browser challenge and links a verified Google subject to the canonical admin using the existing identity service. `tests/test_admin_pwa_enrollment.py` is committed. See the bottom of `HSK_AI_ADMIN_PWA_TEMP_HANDOFF.md` for commit IDs, a **7 passed + 4 subtests** isolated SQLite stub-harness result and unexecuted full-checkout/Postgres validation. This is not a browser OAuth flow, a Bot transport, a session issuer or a working PWA UI. **Flag remains OFF**, existing `/admin.html` and `main` unchanged. Next: wire rate-limited verified OAuth HTTP callback with HttpOnly proof cookies, trusted Telegram Bot approval, and full-repository/PostgreSQL tests.

## Browser-bound Google OIDC checkpoint (2026-10-23)

Added `app/admin_api/pwa_oidc.py`, `app/db/models/admin_pwa_oauth.py`, migration `0112_admin_pwa_oauth_attempts.py` and `tests/test_admin_pwa_oidc.py` (plus model registry). This is an **unwired, disabled-by-default service component**, not a browser login, session issuer or Google Console configuration. See the end of [HSK_AI_ADMIN_PWA_TEMP_HANDOFF.md](HSK_AI_ADMIN_PWA_TEMP_HANDOFF.md) for exact commits, scoped SQLite-stub tests and unverified production/CI gates. The new mandatory UI-skills rule in [HSK_AI_ADMIN_PWA_TEMP_RULES.md](HSK_AI_ADMIN_PWA_TEMP_RULES.md) applies whenever V10 HTML lacks a requested UI/UX element. Existing Telegram Mini App and `main` are untouched.

## OAuth HTTP transport checkpoint (2026-10-24)

`app/admin_api/pwa_google_transport.py` is mounted in `app/main.py` with strict origin/CSRF/HTTPS gating, Secure HttpOnly browser-bound cookies, pending Google verification and transfer to **pending Telegram approval only**; a PostgreSQL-serialized global admission cap was added in `pwa_oidc.py`. **No admin cookie/session issued. `ADMIN_PWA_ENABLED=false` remains default**, so the routes remain unreachable in production by default. See current authoritative [handoff](HSK_AI_ADMIN_PWA_TEMP_HANDOFF.md) for all commits, tests and limitations. Telegram Bot approval, passkeys, dashboard and real data still remain. UI gap rule remains mandatory.

## Bot approval proof and status checkpoint (2026-10-24)

`app/admin_api/pwa_bot_approval.py` now validates trusted private Bot dispatcher events and handles one-time approval/denial; `GET /api/admin/v1/auth/telegram/status` exposes **only** the cookie-bound pending/approved/denied state and a comparison code. `tests/test_admin_pwa_bot_approval.py` and HTTP status regression tests were added. See the current handoff for SHAs and limitations: isolated tests only (**42 passed, 26 subtests**), not full CI/real PostgreSQL/Bot. **No Bot router, UI, passkey, admin session issuer, staging or deploy is done.** Required next work: localized UZ/RU/TJ Bot confirmation and explicit callback, then canonical identity link and secure session. Existing `/admin.html` and `main` are unchanged.
