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

**Verified checkpoint before handoff:** At GitHub commits `7e7e2bb9c6792958d2e5d0e39a4a173ea4a4ab56` (approval model), `8bc5763f859bc6bb9a122ea23fc91e18466cc315` (atomic identity finalizer), `7c3b1f76a495a3d57c23b9276ddfd9162049d421` (unwired Google OIDC service), `bdc6b17a29cdf575d3dd6ad3005727c12d95ef4f` (OAuth DB migration) and `ee9912043bd5e7510e9f2556e9b0a1debec79196` (tests), the auth foundation progressed. Read the authoritative HANDOFF tail before coding. `ADMIN_PWA_ENABLED=false` by default; **no** verified browser OAuth callback, Bot approval callback or login session issuer exists, and `/admin` is not usable. Most recent staged SQLite/FastAPI tests: **42 passed, 26 subtests passed** with reduced models and mock Google; **not full repository CI**, real Bot callback, PostgreSQL, live server or device verification.

**Next actual implementation:** the private, localized aiogram Bot handler now exists at `app/bot/handlers/admin_pwa.py`, registered in `app/bot/create_bot.py` before generic `/start`. Its UZ/RU/TJ Bot catalog is generated and canonical; forwarded/group/wrong-chat requests are rejected. **NEW Bot handler tests have not run with real aiogram**; execute `tests/test_admin_pwa_bot_handlers.py` plus full `scripts/i18n_build_all_catalogs.py --check` in a complete checkout. **Critical blocker:** the post-Google DB approval stores only a keyed `google_subject_hash`, but the atomic identity finalizer needs a fresh trusted `VerifiedIdentity` containing the Google subject. Solve verified identity continuity securely (fresh bound OIDC verification or short-lived encrypted envelope), then integrate browser proof, finalize canonical linking and issue cookies only after security review. No feature flag enable, no production or main.

**UI/UX gap rule:** If V10 HTML lacks a requested UI/UX element, first read and use relevant actual repository design skills (at least `.agents/skills/hsk-ai-ui/SKILL.md`, plus any available `frontend-design`), then test with `.agents/skills/webapp-testing/SKILL.md`/Playwright. Document skill use and rationale; do not invent mock data. See `HSK_AI_ADMIN_PWA_TEMP_RULES.md`.

**Final required product:** `https://hskai.app/admin` as installable real-data Admin PWA built with V10 UI/UX (demo fixtures removed); first login Google + one-time Telegram admin approval → enroll passkey; returning login Face ID/Touch ID/Windows Hello passkey alone (or existing session); separate per-action passkey verification for dangerous admin commands. Full accurate stats/users/feedback, auditable read-only JSON/CSV AI analytics then optional scoped MCP. Telegram Admin Mini App must remain unchanged.

**Original V10 demo HTML:** `hsk-ai-admin-ux-demo-v10.html`, SHA-256 `8cd9375dd2ef7c27e9f17904000629060139ffb21c667a83c60b282ec321a9b9`. The file is **not in the GitHub repo**; I will upload it to the new chat if needed. Check `ADMIN_PWA_V10_UI_REFERENCE.md` and never use its mock `v6Demo` values as real data.

**On finish:** commit only to `codex/admin-pwa`, run and report actual scoped tests, update `HSK_AI_ADMIN_PWA_TEMP_HANDOFF.md` with exact SHA/tests/status and what comes next. Do not merely generate another plan; implement the next safe increment.

---

**Latest Bot router checkpoint:** `docs/admin-pwa/HSK_AI_ADMIN_PWA_TEMP_HANDOFF.md` tail (2026-10-24). Local staged backend 42 passed/26 subtests, real aiogram handler tests not yet run. See exact full SHAs there.
