# HSK AI ADMIN PWA — START NEXT CHAT

Copy/paste this task into a fresh ChatGPT/Codex chat:

---

HSK AI **Admin PWA ишини давом эттир**. Умумий режани бошидан ёзма ва тайёр кодни қайта яратма. GitHub'даги реал кодни текшириб, навбатдаги кичик хавфсиз босқични амалга ошир.

**Repo:** `akbarholturaev11-lang/HSK-AI-Bot`  
**Working branch:** `codex/admin-pwa` ONLY  
**Do not touch:** `main`, production, current Telegram Admin Mini App `/admin.html` and its Telegram initData authentication.

**FIRST READ (this order):**
1. `docs/admin-pwa/HSK_AI_ADMIN_PWA_TEMP_HANDOFF.md`
2. `docs/admin-pwa/HSK_AI_ADMIN_PWA_TEMP_RULES.md`
3. `docs/admin-pwa/HSK_AI_ADMIN_PWA_TEMP_CONTEXT.md`
4. `docs/admin-pwa/HSK_AI_ADMIN_PWA_TEMP_FINAL_RESULT.md`
5. `docs/admin-pwa/IMPLEMENTATION_PLAN.md`
6. `docs/admin-pwa/PHASE_0_API_INVENTORY.md`
7. `docs/admin-pwa/ADMIN_PWA_V10_UI_REFERENCE.md`
8. Root `AGENTS.md`, `AI_RULES.md`, `PROJECT_MEMORY.md`, applicable skill files and real implementation/test code.

**Historical checkpoint (superseded by latest handoff):** At GitHub commits `7e7e2bb9c6792958d2e5d0e39a4a173ea4a4ab56` (approval model), `8bc5763f859bc6bb9a122ea23fc91e18466cc315` (atomic identity finalizer), `7c3b1f76a495a3d57c23b9276ddfd9162049d421` (unwired Google OIDC service), `bdc6b17a29cdf575d3dd6ad3005727c12d95ef4f` (OAuth DB migration) and `ee9912043bd5e7510e9f2556e9b0a1debec79196` (tests), the auth foundation progressed. Read the authoritative HANDOFF tail before coding. `ADMIN_PWA_ENABLED=false` by default; **no** verified browser OAuth callback, Bot approval callback or login session issuer exists, and `/admin` is not usable. Most recent staged SQLite/FastAPI tests: **42 passed, 26 subtests passed** with reduced models and mock Google; **not full repository CI**, real Bot callback, PostgreSQL, live server or device verification.

**Next actual implementation:** WebAuthn **per-operation step-up foundation** has been committed and **verified** on `codex/admin-pwa` behind `ADMIN_PWA_ENABLED=false`. Files `app/admin_api/pwa_step_up.py`, `pwa_step_up_transport.py`, model `admin_pwa_step_up.py` and Alembic `0116_admin_pwa_step_ups` implement 2-minute signature challenges bound to canonical admin browser session and SHA-256 of exact action + target + payload, 60-second receipts and INTERNAL transaction-bound single-use consumption. **NOTHING has been connected to real payment approvals, deletes or broadcast mutations**, and no V10 PWA frontend exists. GitHub CI run https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/40029175593: 152 passed/3 skipped in regular Python 3.12 checkout, 3 passed in REAL disposable PostgreSQL 16 with 0110-0116 migration/downgrade/upgrade. Existing legacy `0011` clean-db issue remains. **NEXT:** carefully select one dedicated Admin PWA mutation, validate exact business request via real shared service, require human-visible matching summary and a consumed step-up inside same transaction, and persist audit, without changing Telegram legacy `/admin.html`. Apply in-repo hsk-ai-ui / webapp-testing skills and canonical translations for any new UI; do not enable flag or touch main/production.

**UI/UX gap rule:** If V10 HTML lacks a requested UI/UX element, first read and use relevant actual repository design skills (at least `.agents/skills/hsk-ai-ui/SKILL.md`, plus any available `frontend-design`), then test with `.agents/skills/webapp-testing/SKILL.md`/Playwright. Document skill use and rationale; do not invent mock data. See `HSK_AI_ADMIN_PWA_TEMP_RULES.md`.

**Final required product:** `https://hskai.app/admin` as installable real-data Admin PWA built with V10 UI/UX (demo fixtures removed); first login Google + one-time Telegram admin approval → enroll passkey; returning login Face ID/Touch ID/Windows Hello passkey alone (or existing session); separate per-action passkey verification for dangerous admin commands. Full accurate stats/users/feedback, auditable read-only JSON/CSV AI analytics then optional scoped MCP. Telegram Admin Mini App must remain unchanged.

**Original V10 demo HTML:** `hsk-ai-admin-ux-demo-v10.html`, SHA-256 `8cd9375dd2ef7c27e9f17904000629060139ffb21c667a83c60b282ec321a9b9`. The file is **not in the GitHub repo**; I will upload it to the new chat if needed. Check `ADMIN_PWA_V10_UI_REFERENCE.md` and never use its mock `v6Demo` values as real data.

**On finish:** commit only to `codex/admin-pwa`, run and report actual scoped tests, update `HSK_AI_ADMIN_PWA_TEMP_HANDOFF.md` with exact SHA/tests/status and what comes next. Do not merely generate another plan; implement the next safe increment.

---

**Historical Bot router checkpoint (superseded):** `docs/admin-pwa/HSK_AI_ADMIN_PWA_TEMP_HANDOFF.md` tail (2026-10-24). Local staged backend 42 passed/26 subtests, real aiogram handler tests not yet run. See exact full SHAs there.
