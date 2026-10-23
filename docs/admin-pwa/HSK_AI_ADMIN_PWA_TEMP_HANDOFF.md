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
- [ ] Obtained/verified the actual V10 HTML demo source for conversion into production frontend components.
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
