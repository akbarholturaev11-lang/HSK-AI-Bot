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

**Verified checkpoint before handoff:** At GitHub commits `7e7e2bb9c6792958d2e5d0e39a4a173ea4a4ab56` (approval model), `8bc5763f859bc6bb9a122ea23fc91e18466cc315` (atomic Google identity finalizer) and `229abc12f6f4f14cae7f1d0ea611ef21d51f19b3` (tests), the auth foundation progressed. Read the authoritative HANDOFF tail before coding. `ADMIN_PWA_ENABLED=false` by default; **no** verified browser OAuth callback, Bot approval callback or login session issuer exists, and `/admin` is not usable. The latest isolated SQLite harness checks passed 7 tests and 4 subtests using reduced service/model stubs; **not full repository CI**, PostgreSQL, live server or device verification.

**Next actual implementation:** run `tests/test_admin_pwa_enrollment.py` from a real checkout and review PostgreSQL/Alembic compatibility. Then implement the next **browser Google OIDC state/nonce/PKCE + HttpOnly browser-proof lifecycle and trusted Telegram Bot approval transport**, using `app/admin_api/pwa_enrollment.py` only after verified provider and Bot proof. Do not mint any session or expose data until all bindings and permissions are tested. Keep flag OFF; no `main` or production deploy.

**Final required product:** `https://hskai.app/admin` as installable real-data Admin PWA built with V10 UI/UX (demo fixtures removed); first login Google + one-time Telegram admin approval → enroll passkey; returning login Face ID/Touch ID/Windows Hello passkey alone (or existing session); separate per-action passkey verification for dangerous admin commands. Full accurate stats/users/feedback, auditable read-only JSON/CSV AI analytics then optional scoped MCP. Telegram Admin Mini App must remain unchanged.

**Original V10 demo HTML:** `hsk-ai-admin-ux-demo-v10.html`, SHA-256 `8cd9375dd2ef7c27e9f17904000629060139ffb21c667a83c60b282ec321a9b9`. The file is **not in the GitHub repo**; I will upload it to the new chat if needed. Check `ADMIN_PWA_V10_UI_REFERENCE.md` and never use its mock `v6Demo` values as real data.

**On finish:** commit only to `codex/admin-pwa`, run and report actual scoped tests, update `HSK_AI_ADMIN_PWA_TEMP_HANDOFF.md` with exact SHA/tests/status and what comes next. Do not merely generate another plan; implement the next safe increment.

---
