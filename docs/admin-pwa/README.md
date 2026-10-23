# HSK AI ADMIN PWA — ONLY THIS TASK (temporary project files)

**Start here:** [HSK_AI_ADMIN_PWA_TEMP_HANDOFF.md](HSK_AI_ADMIN_PWA_TEMP_HANDOFF.md) — latest verified progress and next executable task.

Read in order:
1. [HSK_AI_ADMIN_PWA_TEMP_HANDOFF.md](HSK_AI_ADMIN_PWA_TEMP_HANDOFF.md) — current checkpoint, what is / is not implemented
2. [HSK_AI_ADMIN_PWA_TEMP_RULES.md](HSK_AI_ADMIN_PWA_TEMP_RULES.md) — scoped working rules, branch discipline, auth/data/UX invariants
3. [HSK_AI_ADMIN_PWA_TEMP_CONTEXT.md](HSK_AI_ADMIN_PWA_TEMP_CONTEXT.md) — owner requirements, repository facts, design choices
4. [HSK_AI_ADMIN_PWA_TEMP_FINAL_RESULT.md](HSK_AI_ADMIN_PWA_TEMP_FINAL_RESULT.md) — final production behavior, detailed acceptance checklist
5. [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) — phases and dependency order
6. [PHASE_0_API_INVENTORY.md](PHASE_0_API_INVENTORY.md) — existing endpoints and security risks

> **NOT GLOBAL RULES.** These files are temporary and apply **only to the HSK AI Admin PWA work on `codex/admin-pwa`**. Do not apply them to Android, courses, public site, Telegram Bot or other projects. Root rules still apply.

**Project branch:** `codex/admin-pwa`. **Public target (not yet verified live):** `https://hskai.app/admin`.

**Current state:** phase-one **fail-closed backend route bootstrap** committed (`app/admin_api/pwa_bootstrap.py`), feature flag still off by default, and isolated route tests passed. **No functional browser sign-in, Google/TG pairing, Passkey, real-data frontend, staging deployment or production release yet.**

Global `AGENTS.md`, `AI_RULES.md`, `PROJECT_MEMORY.md` and `localization/README.md` remain authoritative alongside the user's requirement to work solely on the selected project branch until explicitly authorized to promote.

These are **temporary task-scoped documents**. Keep them synchronized during work; archive only after final acceptance, without deleting useful evidence or overwriting unrelated rules.

**Verified V10 reference:** [ADMIN_PWA_V10_UI_REFERENCE.md](ADMIN_PWA_V10_UI_REFERENCE.md). Original demo HTML is a conversation-mounted file, not a GitHub copy.
