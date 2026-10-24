> **Current next-chat entry (MCP PR #201, 2026-10-24):** [MCP_NEXT_CHAT_HANDOFF.md](MCP_NEXT_CHAT_HANDOFF.md). Work ONLY on `feat/admin-pwa-mcp-readonly-20261024` (Draft PR #201); PR #200 already merged. The older resume and handoff below describe historical PR #200 milestones and must not be used as current instructions. MCP transport and Admin PWA flags remain OFF; no real ChatGPT connection has been verified.

# Admin PWA — CURRENT CODEx HANDOFF

**Codex should start from [`CODEX_RESUME.md`](CODEX_RESUME.md), not from dated checkpoints lower in this README.** Read scoped rules and the most recent `HSK_AI_ADMIN_PWA_TEMP_HANDOFF.md` section. GitHub feature branch only; default flag OFF. Latest verified CI: [run 40029175593](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/40029175593) (152 passed + 3 real PostgreSQL tests). The per-action WebAuthn step-up exists, but payment/delete/broadcast adapters and frontend remain unwired. Audited `app/main.py::_review_admin_payment` internally commits — refactor safely before trying atomic PWA mutations.

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

## Localized Telegram Bot approval router — 2026-10-24

Task-only `app/bot/handlers/admin_pwa.py` is registered before generic `/start` and uses canonical generated UZ/RU/TJ copy. Private-chat one-time Approve / Deny callback, pairing-only code, forwarded-message guard and aiogram-focused tests are committed. The existing reduced backend suite was rerun: **42 passed + 26 subtests**, but new real aiogram handler tests, full-repo localization builder, PostgreSQL, staging and E2E have **not** run. The Google verified-subject continuity gap is a **release blocker**, documented in the authoritative handoff. This is not a working browser PWA login; `ADMIN_PWA_ENABLED=false` and `main`/legacy `/admin.html` unchanged.

## OIDC-to-Telegram identity continuity (2026-10-24)

`app/admin_api/pwa_enrollment.py` now atomically uses the approved DB row's **server-OIDC-verified keyed Google subject hash**, exact web-client audience, current Telegram admin authority and HttpOnly browser-proof hash to link the canonical user. No raw Google `sub`, second OAuth prompt or extra migration is needed. Service-chain regression test `tests/test_admin_pwa_identity_chain.py` added; staged SQLite tests **49 passed + 22 subtests**. This is NOT an exposed browser completion route or admin session issuer, and has NOT run in full repo CI / PostgreSQL / real Google + Telegram. Next work: reviewed one-use enrollment grant and WebAuthn server verification, then guarded completion integration; keep flag OFF. Details in the handoff tail.

## Browser-bound passkey enrollment grant (2026-10-24)

Atomic canonical Google link + Telegram approval consumption + a **3-minute dual-cookie passkey-enrollment grant** have been added on `codex/admin-pwa`. Files: `app/admin_api/pwa_enrollment_grants.py`, `app/db/models/admin_pwa_enrollment_grant.py`, migration `0113_admin_pwa_enrollment_grants.py`, and guarded `app/admin_api/pwa_enrollment_transport.py` mounted in `app/main.py`. `POST /api/admin/v1/auth/telegram/complete` accepts only same-origin CSRF-checked JSON and issues **only** Secure HttpOnly host-only enrollment/proof cookies, no admin login session. Local mirrored SQLite/FastAPI tests: **86 passed, 22 subtests**; full checkout, PostgreSQL, WebAuthn, CI and real devices **not verified**. WebAuthn attestation, grant consumption, passkey-only login, session/revocation and actual Admin PWA UI are still missing. See the authoritative handoff. Production feature flag remains OFF.

## Server-side WebAuthn registration checkpoint (2026-10-24)

New challenge and credential DB models, Alembic `0114_admin_pwa_webauthn_registration`, pinned `webauthn==3.0.1`, `app/admin_api/pwa_webauthn_registration.py` and `app/admin_api/pwa_webauthn_transport.py` implement origin/RP/challenge/user-verification-enforced passkey **registration** under short-lived dual-cookie grants. New routes: `POST /api/admin/v1/auth/passkey/register/options` and `/verify`. These never mint a normal admin login cookie. New test modules have been committed but NOT EXECUTED in a full repository environment; see handoff for exact facts. Passkey sign-in, session issuer, WebAuthn step-up, real-data UI and staging/E2E remain. Feature flag OFF, no production or `main` impact.

### CI evidence for WebAuthn registration — 2026-10-24

The dedicated `admin-pwa-security.yml` workflow succeeded on the feature branch: [run 40026176016](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/40026176016), **110 tests passed in 6.46s**, Python 3.12 dependency installation and compileall succeeded, with one Alembic head at `0114_admin_pwa_webauthn_registration`. This tests mocked FIDO attestation, not real hardware signatures or PostgreSQL migration upgrades. Not a production release sign-off; passkey sign-in and session issuer remain unfinished. `ADMIN_PWA_ENABLED=false`.

### Passkey sign-in and real PostgreSQL verification (2026-10-24)

WebAuthn passkey login now verifies a stored public key, challenge, origin/RP ID and UV, then atomically creates a revocable 8-hour Secure HttpOnly Admin PWA session; logout revokes it in the DB. The session guard denies blocked status in any letter case. The dedicated [GitHub Actions run 40028060236](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/40028060236) passed **134 regular tests (2 PostgreSQL-only skipped)** and **2 real PostgreSQL lock/concurrency tests**, upgraded revisions 0110–0115 and verified rollback/reapply of 0115. The older global migration cold-start chain fails at 0011 because `course_progress` is missing; this was NOT silently repaired. No production enablement, physical Face ID test or per-operation passkey step-up yet; details in handoff.

### Exact-operation step-up foundation (2026-10-24)

Passkey login alone does not authorize sensitive operations. New dedicated POST `/api/admin/v1/auth/step-up/options` and `/verify` plus `app/admin_api/pwa_step_up.py` store an SHA-256 commitment to the EXACT action/target/payload, verify a one-time WebAuthn assertion and allow only INTERNAL one-use receipt consumption within the same DB transaction as a *future* admin mutation. **No actual PWA payment/delete/broadcast route is wired**; all legacy Telegram admin routes remain unchanged. [GitHub CI run 40029175593](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/40029175593): 152 full-repo tests passed (3 PG-only skipped), 3 real PostgreSQL tests passed, scoped 0110–0116 migration/rollback passed. `ADMIN_PWA_ENABLED=false`, no main/production deployment; see handoff for explicit release blockers.
