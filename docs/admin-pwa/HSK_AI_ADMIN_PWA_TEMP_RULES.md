# Admin PWA — scoped AI work rules (temporary)

> **SCOPE: HSK AI ADMIN PWA ONLY** — temporary task file. Work branch: `codex/admin-pwa`.
> Not a repository-wide policy. Does not modify or supersede root `AGENTS.md` / `AI_RULES.md` / `PROJECT_MEMORY.md`.
> All development and progress records for this task remain under `docs/admin-pwa/`.


**Project:** HSK AI standalone Admin PWA
**Working branch:** `codex/admin-pwa`
**Scope:** Only this Admin PWA initiative. These rules supplement, but do not replace, root `AGENTS.md`, `AI_RULES.md`, `PROJECT_MEMORY.md`, security invariants and localization policy.
**State:** Temporary project-scoped handoff. Reconcile or archive when the initiative is finished. Do not copy these rules into unrelated platforms.

## Required startup sequence (every new chat/agent)

1. Read `docs/admin-pwa/HSK_AI_ADMIN_PWA_TEMP_HANDOFF.md` for the verified checkpoint.
2. Read this file, `docs/admin-pwa/HSK_AI_ADMIN_PWA_TEMP_CONTEXT.md`, `docs/admin-pwa/HSK_AI_ADMIN_PWA_TEMP_FINAL_RESULT.md`.
3. Read `docs/admin-pwa/IMPLEMENTATION_PLAN.md` and `docs/admin-pwa/PHASE_0_API_INVENTORY.md`.
4. Read root `AGENTS.md`, `AI_RULES.md`, `PROJECT_MEMORY.md` and relevant code/tests. When adding user-visible copy read `localization/README.md`.
5. Check branch HEAD, diff versus `main`, existing files and current code before making claims or changes. Never trust an outdated handoff over the current repository.

## Scope and Git safety

- **All implementation stays on `codex/admin-pwa` until the owner explicitly approves promotion.** Do not push/merge to `main`, deploy to production, switch live routes, change secrets, or touch public site / existing Telegram Admin Mini App except an indispensable backward-compatible adapter explicitly reviewed and tested.
- No force push, history rewrite or destructive cleanup. Do not edit outside task scope or silently import unrelated changes.
- Use small, reviewable commits after scoped verification. Log every completed change and its exact validation in `HSK_AI_ADMIN_PWA_TEMP_HANDOFF.md`. Never label a planned, mocked or untested feature as done.
- If an existing repo-wide rule recommends `main` by default, this **user-selected project branch and no-production requirement** override the destination for this initiative; all other repository protections remain in force.
- Work from existing service abstractions, not duplicate payment, entitlement, account or statistics logic.

## Functional invariants

- Keep Telegram Admin Mini App `/admin.html` and `X-Telegram-Init-Data` flows fully operational. No spoofed initData and no bypass in existing admin guards.
- Admin PWA public target is `https://hskai.app/admin` **subject to real DNS, TLS, proxy and collision verification**. Do not claim it is live or that OAuth callback/RP ID is configured without evidence.
- First onboarding: verified Google OIDC identity + one-time explicit approval by an authorized Telegram admin + secure canonical admin link + passkey enrollment. Returning login is **passkey-first without repeating Google/Telegram**. Valid existing session should reopen directly. Linked Google and audited Telegram recovery are fallbacks, not each-open requirements.
- WebAuthn (FIDO2) is platform authentication (Face ID, Touch ID, Windows Hello, PIN/passcode depending on device), **not a guaranteed Face-ID-only API**. Relying-party ID: `hskai.app` for production; origin `https://hskai.app`. Browser/server never receive biometric templates.
- For payments, deletion, granting paid access, broadcast and other high-risk mutations require an **action/target/payload-bound, one-time WebAuthn step-up**, explicit confirmation, audit trail and server-side authorization; normal statistics browsing should not require per-view biometric prompts.
- Tokens in Secure HttpOnly cookie only; no browser JS-readable session secrets, no tokens in URLs/localStorage, strict Origin/CSRF/session expiry/revocation/CSP/rate limits. PWA SW only caches public shell; **never** accounts, authenticated API, reviews/attachments, payments or tokens.
- Canonical user ID is `users.id`; never confuse it with Telegram transport ID. Demo data must never enter production datasets.
- A browser/Cloud/ChatGPT/MCP client receives no production database credentials. AI analytics are **read-only** with metrics definitions, bounded ranges, redaction, explicit authorization, audit and limits; no billing/user mutations.
- Platform user counts can overlap. Do not sum them as all-users totals. Counts, visits, installs, retention, revenue and spend must retain clear server-side definitions; missing/untracked platforms render unavailable rather than artificial zero.

## UI/UX rules and skills

- V10 standalone HTML demo is **visual/interaction reference only**, not a trusted data model and not automatically present in repository. Before integration, make its exact bytes available and verify source. Never rebuild dummy fixtures as live content.
- Use repo skills `.agents/skills/hsk-ai-ui/SKILL.md` and `.agents/skills/webapp-testing/SKILL.md` when applicable; `AGENTS.md` also names `frontend-design` if actually available. Do not claim a skill was read when unavailable.
- **MANDATORY for UI/UX not covered by the supplied V10 demo HTML:** before inventing or implementing a screen, component, empty/loading/error state, responsive behavior or interaction not represented in the verified demo, inspect and apply the relevant in-repository UI/UX skills (at minimum `hsk-ai-ui`; also `frontend-design` or any other actual repository design skill if available). Use `webapp-testing` / Playwright for the resulting visual and interaction QA. Document which skills were actually read, the uncovered design gap, the chosen pattern and applicable test evidence in the Admin PWA handoff. Never improvise an inconsistent UI because a component is missing from the demo; never claim a skill was used unless its instructions were read. Existing V10 elements stay the visual reference, not an excuse to copy demo mock data. This applies to all future Admin PWA UI work on the task branch.
- Design must be mobile-first, responsive (iPhone home-screen PWA, Mac, Windows), accessible, premium/professional, compact and clear. No repeated titles, decorative explanations or duplicate filters. The notification bell is in the top right; folded filter icon, time-period control and bell share one toolbar row. Important/unresolved reports rank above ordinary inbox entries.
- Keep explicit loading/empty/offline/error/auth-expired/no-permission states. Never fake a successful mutation.
- Permanent UI text is authored in canonical UZ/RU/TJ i18n sources, then generated with required repository checks; avoid new unmanaged inline dictionary.

## Test/acceptance and truthful reporting

- Auth: test forged/stale Telegram initData, non-admin, unlinked Google subject, OAuth state/nonce/PKCE, CSRF/origin, challenge replay/cross-browser, expiring/revoked session, passkey wrong RP ID/origin/credential, recovery and privilege revocation.
- Separate **passkey login** tests from **per-transaction passkey authorization** tests; validate actual payload binding for payment/delete actions.
- APIs: verify server-owned values, pagination, caching, source semantics, overlapping platform users, correctness of billing/entitlements and identity isolation.
- Regression: unchanged Telegram webapp/bot admin path, existing mobile/desktop user flows affected by modified backend and DB migrations.
- UI: Playwright desktop + narrow mobile tests; manual physical/real-device installed iPhone PWA Face ID, Mac Touch ID, Windows Hello where available. Simulator/browser-only tests are not evidence of real biometric flow.
- Use staging with separate credentials and seeded data. Never test live payment approvals, deletion or bulk notifications on production.
- Always report: changed paths, commit, exact tests actually run, failures/risks, remaining work and next step. If only docs changed, say plainly **no app code implemented**.

## Change control

- No new broad refactor, deployment or speculative credentials. Do not open write APIs to AI or skip owner approval for production.
- Preserve current product scope, constraints and phase order. Any architectural change requires an explicit rationale and corresponding edits to this rule set, target/plan and handoff.
