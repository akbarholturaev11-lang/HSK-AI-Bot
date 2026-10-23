# HSK AI Admin PWA — Codex resume (current, authoritative)

**Purpose:** One concise entry point for Codex to continue the existing implementation on the feature branch. This file is a current-state index, not a replacement for project rules, source-code audit, or tests. Historical append-only notes remain in `HSK_AI_ADMIN_PWA_TEMP_HANDOFF.md`.

## 1. Repository and exact checkpoint

- Repo: `akbarholturaev11-lang/HSK-AI-Bot`
- **ONLY working branch:** `codex/admin-pwa`
- Historical feature-branch HEAD at preparation: `e5cf9273cec25db286d5f0d7a4715a020a98bcab`. The HEAD will advance when this documentation is committed; **always inspect current HEAD before any implementation**.
- At that checkpoint: feature branch was **161 commits ahead and 3 behind `main`**; it is diverged. **Do not merge, rebase, reset, cherry-pick, or resolve drift automatically**. Review relevant `main` differences when required, propose a bounded integration separately.
- Default: `ADMIN_PWA_ENABLED=false`. Keep it **OFF**. No production deployment, no merge to `main`, no changes to secrets or public site, no changes to the existing Telegram `/admin.html`, `X-Telegram-Init-Data`, native APK billing/update behavior, or normal user authentication.
- Do not treat stale status summaries near the top of `IMPLEMENTATION_PLAN.md` or old sections of `NEXT_CHAT_START.md` as current; consult source and this verified checkpoint.

## 2. Read first — in order

1. `docs/admin-pwa/CODEX_RESUME.md` (this document).
2. `docs/admin-pwa/HSK_AI_ADMIN_PWA_TEMP_RULES.md` (binding scoped safety and UI rules).
3. **Latest tail**, not only top, of `docs/admin-pwa/HSK_AI_ADMIN_PWA_TEMP_HANDOFF.md` (historical commits, test evidence and exceptions).
4. `docs/admin-pwa/PHASE_0_API_INVENTORY.md`, `IMPLEMENTATION_PLAN.md`, `HSK_AI_ADMIN_PWA_TEMP_FINAL_RESULT.md`, `ADMIN_PWA_V10_UI_REFERENCE.md`.
5. Root `AGENTS.md`, `AI_RULES.md`, `PROJECT_MEMORY.md` and real source/tests. Read `localization/README.md` before editing permanent UI text.
6. Before implementing missing V10 browser UI, read **actual** `.agents/skills/hsk-ai-ui/SKILL.md`, `.agents/skills/webapp-testing/SKILL.md` and any available `frontend-design` skill. Never claim use without reading.

## 3. What EXISTS in feature-branch source

**Auth/onboarding:** Google OIDC callback with state/nonce/PKCE and provider subject hash; private Telegram Bot one-time approve/deny handler; canonical Google identity link; short-lived dual HttpOnly cookie passkey enrollment grant; server WebAuthn registration and stored public-key credentials. Key modules: `app/admin_api/pwa_oidc.py`, `pwa_google_transport.py`, `pwa_bot_approval.py`, `pwa_enrollment.py`, `pwa_enrollment_grants.py`, `pwa_webauthn_registration.py`, `pwa_webauthn_transport.py`, `app/bot/handlers/admin_pwa.py`.

**Returning auth:** Discoverable WebAuthn passkey login with verified signature, challenge/origin/RP ID/UV/credential counter, server-backed 8-hour revocable `__Host-hskai_admin` Secure HttpOnly cookie and logout. Key modules: `app/admin_api/pwa_webauthn_login.py`, `pwa_webauthn_login_transport.py`, `pwa_sessions.py`.

**Sensitive action authorization (FOUNDATION ONLY):** `app/admin_api/pwa_step_up.py` and `pwa_step_up_transport.py` create and cryptographically verify per-operation step-up challenges for **`payments.review`, `users.delete`, `broadcast.send`**. SHA-256 commitment covers canonical `{version,action,target,payload}`; 2-minute challenge, max 60-second verified receipt; internal `consume_step_up_in_mutation()` requires the **same DB transaction** as a future real write. It re-checks current admin session and unrevoked passkey. Schema `app/db/models/admin_pwa_step_up.py`, Alembic `0116_admin_pwa_step_ups.py`. **Payment review now has a dedicated adapter (see below); delete/broadcast remain unwired. No public generic consume endpoint should ever be added.**

**Payment review (new, branch-only):** shared commit-free unit in `app/services/admin_payment_review_service.py`; dedicated strict prepare/review HTTP adapter `pwa_payment_review_transport.py`; transactional step-up + canonical owner/amount/currency/receipt snapshot + existing entitlement/preview/partner writes + durable audit/outbox (`0117`). The Telegram wrapper retains its own commit and existing post-commit transports. See `PAYMENT_REVIEW_CONTRACT.md` for exact payload and at-most-once delivery limitations. No browser confirmation UI or production payment is claimed. New GitHub CI verification is pending for this increment.

**Not built:** real installable V10 Admin PWA frontend, actual read-only real-data dashboard/users/feedback endpoints for browser sessions, physical biometric/device E2E, production Google/OAuth/Telegram E2E, audit/outbox adapters for delete/broadcast, pending-delivery recovery/reconciliation, action-specific confirmation UI, and any safe read-only AI/MCP integration.

The V10 HTML `hsk-ai-admin-ux-demo-v10.html` is **not committed to GitHub**; the design reference is `docs/admin-pwa/ADMIN_PWA_V10_UI_REFERENCE.md` with SHA-256 `8cd9375dd2ef7c27e9f17904000629060139ffb21c667a83c60b282ec321a9b9`. Ask for the actual HTML only when visual porting cannot proceed without it. Never copy `v6Demo` arrays or synthetic fixtures into production.

## 4. Last VERIFIED test checkpoint

GitHub Actions run: https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/40029175593 (source commit `1cccbd0b677e3b965d8b591b3a9487983d380470`):
- Python 3.12 full checkout: **152 passed, 3 PostgreSQL-only skipped**; compileall and single Alembic head succeeded.
- Separate isolated **real PostgreSQL 16** job: **3 passed** (advisory-lock admission, concurrent one-time passkey login/logout, concurrent one-time exact-action step-up consume); migrations **0110–0116 upgraded**, `0116` downgraded to `0115` and upgraded again.
- Separate genuine **synthetic ES256** verifier vectors test signature, wrong RP/origin/challenge, missing UV, tampering, counter replay; **not** physical Touch ID/Face ID/Windows Hello E2E.
- **Known unrelated baseline blocker:** an entirely empty PostgreSQL database fails the **legacy** full-history Alembic path at `0011_add_course_workflow_fields` (missing `course_progress`). Existing Admin PWA CI tests 0110–0116 from a *synthetically stamped 0109 baseline* only. Do not claim the complete cold-start migration chain is fixed, or change old migrations without a separate review.

CI: `.github/workflows/admin-pwa-security.yml`. Run `python -m pytest -q tests/test_admin_pwa_*.py` in Python 3.12 and check **both** GitHub jobs. Always inspect latest run's exact SHA; cancelled/older green runs are not proof of new code.

## 5. NEXT work in safe increments (do not repeat already done work)

**Payment adapter implementation is complete on this branch; verify the latest CI SHA before resuming.** Do not redo the shared financial refactor. Read `PAYMENT_REVIEW_CONTRACT.md`, the latest handoff and actual source/tests. Keep the flag OFF; the human confirmation UI and real device/provider E2E are still absent. Pending delivery recovery/reconciliation must preserve the at-most-once claim policy; never auto-retry attempting/uncertain sends.

**Next implementation:** protected read-only real-data projections for overview/platform-filtered stats, users and feedback, using existing services and bounded canonical identity queries. Then the original V10 installable browser UI and explicit exact-payment confirmation, followed by staging/device QA. Delete/broadcast remain disabled until separately audited adapters exist.

**Subsequent priorities:** protected read-only real-data projections for overview/platform-filtered stats, users and feedback; V10 installable PWA browser UI (obtain original HTML and apply repo UI/test skills); real permission/CSRF/session and device QA; gradually other sensitive adapters (delete and broadcast) only after the payment flow pattern is audited. Keep read-only AI analytics/MCP separate and default to no write privileges.

## 6. Codex execution & completion contract

- Continue **implementation**, not a new speculative multi-page plan.
- Review actual code, current branch/HEAD, latest changed commits and the difference from `main`; branch is diverged, **do not merge or rebase** without explicit owner consent.
- Make small, reviewed commits **ONLY to `codex/admin-pwa`**. Never enable flag, touch production, rewrite git history, edit live deployment/secrets, or alter legacy `/admin.html` auth. Reuse shared business services and preserve semantics.
- For UI messages, author all new UZ/RU/TJ text in canonical sources, run `python3 scripts/i18n_build_all_catalogs.py --write` then `--check`, and commit generated outputs.
- For each increment: report changed files, exact commit SHA, tested scope (unit/real PG/real FIDO/real device), CI link, regressions/limitations and next task; append factual results to `HSK_AI_ADMIN_PWA_TEMP_HANDOFF.md` and update THIS short resume file when the authoritative checkpoint changes.
- Do not generate fake success statuses, dummy users/payments, unauthorized write tools or promises of live functionality. Ask the owner before any main promotion or production deployment.
