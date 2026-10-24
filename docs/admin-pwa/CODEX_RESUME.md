# HSK AI Admin PWA — Codex resume (current, authoritative)

**Purpose:** One concise entry point for Codex to continue the existing implementation on the feature branch. This file is a current-state index, not a replacement for project rules, source-code audit, or tests. Historical append-only notes remain in `HSK_AI_ADMIN_PWA_TEMP_HANDOFF.md`.

## 1. Repository and exact checkpoint

- Repo: `akbarholturaev11-lang/HSK-AI-Bot`
- **ONLY working branch:** `codex/admin-pwa`
- Last verified code SHA: `8edd9ccfc0a244f0b4893d7251113818bfe3cc7a`. The head advances with later code/docs commits; always inspect current HEAD and the latest handoff before implementation.
- At the latest remote comparison the feature branch remained **3 commits behind `main`** and diverged. **Do not merge, rebase, reset, cherry-pick, or resolve drift automatically**. Review relevant `main` differences separately.
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

**Sensitive action authorization:** `app/admin_api/pwa_step_up.py` and `pwa_step_up_transport.py` create and cryptographically verify per-operation step-up challenges for **`payments.review`, `users.delete`, `broadcast.send`**. SHA-256 commitment covers canonical `{version,action,target,payload}`; 2-minute challenge, max 60-second verified receipt; internal `consume_step_up_in_mutation()` requires the **same DB transaction** as a future real write. It re-checks current admin session and unrevoked passkey. Schema `app/db/models/admin_pwa_step_up.py`, Alembic `0116_admin_pwa_step_ups.py`. **Payment review now has a dedicated adapter (see below); delete/broadcast remain unwired. No public generic consume endpoint should ever be added.**

**Payment review (new, branch-only):** shared commit-free unit in `app/services/admin_payment_review_service.py`; dedicated strict prepare/review HTTP adapter `pwa_payment_review_transport.py`; transactional step-up + canonical owner/amount/currency/receipt snapshot + existing entitlement/preview/partner writes + durable audit/outbox (`0117`). The Telegram wrapper retains its own commit and existing post-commit transports. See `PAYMENT_REVIEW_CONTRACT.md` for exact payload and at-most-once delivery limitations. A branch-only exact confirmation UI now uses this adapter; no production payment is claimed. Verified payment CI: `68f34cd7f6a6fca4e8d90c81abf2b8312b4a445c`, run 40031936102 (both jobs green).

**Read projections (new):** `app/admin_api/pwa_read.py` provides protected real-data statistics, bounded canonical users search and durable bot/release feedback lists. PostgreSQL READ ONLY/REPEATABLE READ transactions; no attachment secrets or management actions. See `READ_PROJECTIONS.md` for period/grain/history limits. Telegram-only attribution and iPhone metrics remain unavailable; desktop platform counters explicitly remain rolling 30 days. Verified read CI: `f24aff4dc534a1e19648918294d094fd64c37e3d`, run 40032878724, both jobs green.

**Browser UI (new, current increment awaiting exact-SHA CI):** `app/static/admin-pwa/`, gated `/admin/` shell/manifest/worker, real projections + bounded payments list and authenticated receipt preview, Google callback continuation, passkey enrollment/login, exact one-use payment confirmation. Public-only SW scope `/admin/` excludes legacy `/admin.html`. Canonical UZ/RU/TJ catalog, no demo data. `BROWSER_UI_CONTRACT.md` documents privacy, recovery and browser/device limits. Chromium synthetic virtual-authenticator registration/login/approval/rejection/cancel tests and actual loopback SW/installability/update tests pass locally; this is not physical biometrics or production provider evidence.

**Not built:** physical biometric/device E2E, production Google/OAuth/Telegram E2E, audit/outbox adapters for delete/broadcast, pending-delivery recovery/reconciliation, remaining attribution/history gaps and safe read-only AI/MCP integration.

The owner supplied the actual revised V10 reference on 2026-10-24:
`/Users/kaijimima1234/Downloads/hsk-ai-admin-ux-demo-v10 2.html`, 182,765 bytes,
SHA-256 `1ff92bf82126ea65672ed703f9fff6553982db2f08f7c1ed2a06396cb6c89566`.
Its title still says V9; the previous 8cd937… hash is historical. Source visual
components were inspected and ported; never copy its demo records/handlers.

## 4. Last VERIFIED test checkpoint

Payment + read projections + delivery-status repair verified at **`8edd9ccfc0a244f0b4893d7251113818bfe3cc7a`**, [GitHub run 40033338435](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/40033338435), both jobs SUCCESS:
- Python 3.12: **185 passed, 11 PostgreSQL-only skipped**, plus **61 passed** legacy payment/subscription/preview/affiliate/main-import regressions; compileall and unique Alembic head succeeded.
- Disposable real PostgreSQL 16: **11 passed**; scoped migrations **0110–0117** upgraded, 0117→0116 downgrade/re-upgrade, columns matched ORM; nonempty financial audit refuses downgrade.
- Actual synthetic ES256 verifier integration covers approval, wrong key/RP/origin/UV/signature; not physical Touch ID/Face ID/Windows Hello or actual provider E2E.
- **Known unrelated baseline blocker:** entirely empty full-history Alembic still fails at legacy `0011_add_course_workflow_fields` (missing `course_progress`). Scoped CI starts from a *synthetically stamped 0109 baseline*. No claim that old migrations are fixed.

CI: `.github/workflows/admin-pwa-security.yml`. Always run all Admin PWA tests, the workflow's legacy payment regression command and real PG job, and inspect the run's exact SHA. Includes PostgreSQL READ ONLY enforcement and transaction-setting reset. The HTTP delivery-status repair returns the actual durable outbox state after partial delivery, or unconfirmed if unavailable; it is covered in the verified 185 + 61 + 11 result above. Inspect the latest handoff before resuming.

## 5. NEXT work in safe increments (do not repeat already done work)

**Payment adapter implementation is complete on this branch; verify the latest CI SHA before resuming.** Do not redo the shared financial refactor. Read `PAYMENT_REVIEW_CONTRACT.md`, the latest handoff and actual source/tests. Keep the flag OFF; the human confirmation UI exists on the branch; real device/provider E2E remains absent. Pending delivery recovery/reconciliation must preserve the at-most-once claim policy; never auto-retry attempting/uncertain sends.

**Next:** verify the browser increment's exact-SHA workflow and perform staging/physical-device QA with separate credentials. Do not enable the flag or deploy without explicit authorization. Exercise installed iPhone PWA, Mac Touch ID, Windows Hello, real Google/Bot callback/recovery, proxy/TLS and session revocation; synthetic Chromium is not that evidence. Registration refresh/expired challenge may require restarting the existing Google/Bot recovery.

**Subsequent priorities:** remaining Telegram-only attribution and durable Android feedback/history gaps; pending-delivery recovery/monitoring with explicit uncertain-send reconciliation, preserving at-most-once claims; separately audited delete/broadcast adapters and their confirmations; sanitized read-only export/MCP. Those management actions remain disabled. Do not redo the financial UoW, read projections or supplied-reference UI.

## 6. Codex execution & completion contract

- Continue **implementation**, not a new speculative multi-page plan.
- Review actual code, current branch/HEAD, latest changed commits and the difference from `main`; branch is diverged, **do not merge or rebase** without explicit owner consent.
- Make small, reviewed commits **ONLY to `codex/admin-pwa`**. Never enable flag, touch production, rewrite git history, edit live deployment/secrets, or alter legacy `/admin.html` auth. Reuse shared business services and preserve semantics.
- For UI messages, author all new UZ/RU/TJ text in canonical sources, run `python3 scripts/i18n_build_all_catalogs.py --write` then `--check`, and commit generated outputs.
- For each increment: report changed files, exact commit SHA, tested scope (unit/real PG/real FIDO/real device), CI link, regressions/limitations and next task; append factual results to `HSK_AI_ADMIN_PWA_TEMP_HANDOFF.md` and update THIS short resume file when the authoritative checkpoint changes.
- Do not generate fake success statuses, dummy users/payments, unauthorized write tools or promises of live functionality. Ask the owner before any main promotion or production deployment.
