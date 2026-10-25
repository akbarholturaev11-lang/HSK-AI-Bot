> **OWNER CORRECTION (2026-10-25):** Current corrective follow-up:
> `fix/admin-pwa-biometric-every-open-20261025` after merged PR #207.
> On every new launch/foreground resume, revoke the old server session and
> attempt fresh WebAuthn automatically without a preliminary button; fallback
> only for WebKit gesture limits/cancellation. Never expose private admin data
> until verified. Preserve accepted minimal Inbox and iPhone swipe-back.
> The previous session-reuse instruction is superseded. No main push or deploy.

> **CURRENT MCP workstream branch clarification (2026-10-24):** Previous `codex/admin-pwa` was merged to `main` in PR #200. All NEW MCP work is intentionally isolated to **`feat/admin-pwa-mcp-readonly-20261024` / Draft PR #201**, as specified in [MCP_NEXT_CHAT_HANDOFF.md](MCP_NEXT_CHAT_HANDOFF.md). Continue obeying every scoped safety/UI/approval rule below; the branch and startup sequence below reflect the current follow-up. No new merge/deploy/flag enablement is authorized.

# Admin PWA — scoped AI work rules (temporary)

> **SCOPE: HSK AI ADMIN PWA ONLY** — temporary task file. Work branch: `feat/admin-pwa-mcp-readonly-20261024`.
> Not a repository-wide policy. Does not modify or supersede root `AGENTS.md` / `AI_RULES.md` / `PROJECT_MEMORY.md`.
> All development and progress records for this task remain under `docs/admin-pwa/`.


**Project:** HSK AI standalone Admin PWA
**Working branch:** `feat/admin-pwa-mcp-readonly-20261024` (Draft PR #201)
**Scope:** Only this Admin PWA initiative. These rules supplement, but do not replace, root `AGENTS.md`, `AI_RULES.md`, `PROJECT_MEMORY.md`, security invariants and localization policy.
**State:** Temporary project-scoped handoff. Reconcile or archive when the initiative is finished. Do not copy these rules into unrelated platforms.

## Required startup sequence (every new chat/agent)

1. Read `docs/admin-pwa/MCP_NEXT_CHAT_HANDOFF.md` in full for the current verified checkpoint. `HSK_AI_ADMIN_PWA_TEMP_HANDOFF.md` and `CODEX_RESUME.md` preserve historical evidence only.
2. Read this file, `docs/admin-pwa/HSK_AI_ADMIN_PWA_TEMP_CONTEXT.md`, `docs/admin-pwa/HSK_AI_ADMIN_PWA_TEMP_FINAL_RESULT.md`.
3. Read `docs/admin-pwa/IMPLEMENTATION_PLAN.md` and `docs/admin-pwa/PHASE_0_API_INVENTORY.md`.
4. Read root `AGENTS.md`, `AI_RULES.md`, `PROJECT_MEMORY.md` and relevant code/tests. When adding user-visible copy read `localization/README.md`.
5. Check branch HEAD, diff versus `main`, existing files and current code before making claims or changes. Never trust an outdated handoff over the current repository.

## Scope and Git safety

- **All implementation stays on `feat/admin-pwa-mcp-readonly-20261024` until the owner explicitly approves promotion.** Commit/push each completed, tested increment there. Do not push/merge to `main`, deploy to production, switch live routes, change secrets, or touch public site / existing Telegram Admin Mini App except an indispensable backward-compatible adapter explicitly reviewed and tested.
- No force push, history rewrite or destructive cleanup. Do not edit outside task scope or silently import unrelated changes.
- Use small, reviewable commits after scoped verification. Keep the current checkpoint and exact validation in `MCP_NEXT_CHAT_HANDOFF.md`; do not append new progress to the historical handoff. Never label a planned, mocked or untested feature as done.
- If an existing repo-wide rule recommends `main` by default, this **user-selected project branch and no-production requirement** override the destination for this initiative; all other repository protections remain in force.
- Work from existing service abstractions, not duplicate payment, entitlement, account or statistics logic.

## Functional invariants

- Keep Telegram Admin Mini App `/admin.html` and `X-Telegram-Init-Data` flows fully operational. No spoofed initData and no bypass in existing admin guards.
- Admin PWA public target is `https://hskai.app/admin` **subject to real DNS, TLS, proxy and collision verification**. Do not claim it is live or that OAuth callback/RP ID is configured without evidence.
- First onboarding: verified Google OIDC identity + one-time explicit approval by an authorized Telegram admin + secure canonical admin link + passkey enrollment. Returning login is **passkey-first without repeating Google/Telegram**. On EACH launch/resume revoke the old cookie session server-side and auto-attempt new WebAuthn, even when the old session has not expired. The browser cannot guarantee an automatic modal prompt; Safari/WebKit may require an explicit passkey fallback, which cannot be removed safely. Never display private UI or consume private data before successful proof. Explicit logout also revokes the server session. Linked Google and audited Telegram recovery are fallbacks, not each-open requirements.
- WebAuthn (FIDO2) is platform authentication (Face ID, Touch ID, Windows Hello, PIN/passcode depending on device), **not a guaranteed Face-ID-only API**. Relying-party ID: `hskai.app` for production; origin `https://hskai.app`. Browser/server never receive biometric templates.
- For payments, deletion, granting paid access, broadcast and other high-risk mutations require an **action/target/payload-bound, one-time WebAuthn step-up**, explicit confirmation, audit trail and server-side authorization; normal statistics browsing should not require per-view biometric prompts.
- Tokens in Secure HttpOnly cookie only; no browser JS-readable session secrets, no tokens in URLs/localStorage, strict Origin/CSRF/session expiry/revocation/CSP/rate limits. PWA SW only caches public shell; **never** accounts, authenticated API, reviews/attachments, payments or tokens.
- Canonical user ID is `users.id`; never confuse it with Telegram transport ID. Demo data must never enter production datasets.
- A browser/Cloud/ChatGPT/MCP client receives no production database credentials. External MCP exposes only `hskai_statistics` / `admin:analytics:read`, with metric definitions, bounded ranges, explicit authorization, audit and limits. No account/feedback/payment-list tools or mutations. Broader first-party reads/exports do not extend MCP scope.
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

## Owner-selected statistics load policy (2026-10-24)

Admin PWA/MCP aggregates use private server-side 24-hour snapshots with explicit
source/expiry timestamps; only requested expired variants refresh on authorized
demand, not a fixed nightly cron. The owner
selected daily updates to avoid unnecessary database calculations. Auth,
revocation, audit and security quotas remain current on every request. Billing,
profiles, receipts, access decisions and commands remain uncached. Browser/SW
private-response no-store rules above are unchanged. See `READ_PROJECTIONS.md`
and the active plan for rationale, Redis coordination/failure behavior and
rollout verification. Redis outage fallback is per worker, with possible
recalculation after restart; never promise zero DB traffic or globally one
refresh during an outage. Keep all three feature defaults false. R2 has not
been configured or activated.

For private Inbox images, reuse the existing explicit V10 toggle and shared Bot
client; select source metadata only and release DB connections before IO. Keep
provider loads bounded (two concurrent / 30 attempts per minute per worker,
10-second IO deadline) without new quota DB writes, automatic preload/retry,
media backfill or R2 upload. Worker-local bounds do not replace staging edge
limits. Recheck live auth and exact source ownership/reference after IO; never
reuse the daily statistics cache for private media or current permissions.
