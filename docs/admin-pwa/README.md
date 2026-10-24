# HSK AI Admin PWA — current guide

Work only on `feat/admin-pwa-mcp-readonly-20261024`, [Draft PR #201](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/pull/201).
PR #200 is already merged. No main push/merge, deployment, live migration,
secret configuration or flag activation is authorized. Keep
`ADMIN_PWA_ENABLED=false`, `ADMIN_PWA_MCP_ENABLED=false` and
`ADMIN_PWA_MCP_TRANSPORT_ENABLED=false`.

## Start here

1. [Current handoff](MCP_NEXT_CHAT_HANDOFF.md): verified runtime, tests, CI and remaining work. Read it in full before continuing; verify remote HEAD again.
2. [Scoped rules](HSK_AI_ADMIN_PWA_TEMP_RULES.md) and [context](HSK_AI_ADMIN_PWA_TEMP_CONTEXT.md), alongside root `AGENTS.md`, `AI_RULES.md` and `PROJECT_MEMORY.md`.
3. [Final product / acceptance](HSK_AI_ADMIN_PWA_TEMP_FINAL_RESULT.md) and [active implementation plan](IMPLEMENTATION_PLAN.md).
4. The relevant contracts and real source/tests before changing code.

[Copy/paste next-chat prompt](HSK_AI_ADMIN_PWA_NEXT_CHAT_START.md).

## Statistics load policy

Runtime `4709c66024f568e3e9ce40ecec0019bd6d1535eb` adds private server-side
statistics snapshots shared by Admin PWA and the statistics-only MCP tool.
Each requested platform/period refreshes on the first authorized request after
its rolling 24-hour expiry. There is no nightly cron or unused-variant scan.
The UI keeps the original `generated_at`; statistics can be up to 24 hours old.

Existing Redis / `REDIS_URL` coordinates healthy workers. If Redis is unavailable,
the bounded daily memory fallback is per worker and can calculate again after
restart; it does not guarantee one calculation for the whole deployment.
Authentication, revocation, audit and quotas remain current on every request.
User profiles, billing/payment lists, receipts, access decisions and commands
remain uncached. This reduces aggregate SQL work, not all database traffic.
Private browser/API responses remain no-store; the service worker caches only
the public shell. R2 is not integrated or configured.

The Statistics screen now offers explicit JSON/CSV downloads through cookie-only
`POST /api/admin/v1/statistics/export`. Both use that same daily reader, retaining
original timestamps, ranges, source/scope, metric definitions and separate
currencies. Only allowlisted aggregate values leave the server (128 KiB maximum);
no users, IDs, feedback text or payment records. No background job or forced SQL
refresh is added. A cold/expired variant still follows the existing daily policy.
Sanitized feedback exports remain a separate review; MCP permissions are unchanged.

## Contracts

| Subject | Guide |
|---|---|
| Metric definitions, daily expiry, coordination/failure limits | [Read projections](READ_PROJECTIONS.md) |
| Browser V10, localization, private-data handling | [Browser UI contract](BROWSER_UI_CONTRACT.md), [V10 reference](ADMIN_PWA_V10_UI_REFERENCE.md) |
| OAuth lifecycle, statistics-only tools, protocol and staging gates | [MCP contract](MCP_CONNECTION_CONTRACT.md), [compatibility audit](MCP_CHATGPT_COMPATIBILITY_AUDIT_20261024.md) |
| Live financial review and exact-operation WebAuthn | [Payment review contract](PAYMENT_REVIEW_CONTRACT.md) |
| Manual Pro grant, exact snapshot and command audit | [Access grants](ACCESS_GRANTS_CONTRACT.md) |
| Durable native intake and historical-data boundary | [Native inbox intake](NATIVE_INBOX_INTAKE.md) |

Inbox read/triage/search and default-OFF Apple Push code have since arrived from
GitHub at `d93b75fe468c217dee66e2c4fe277ccfeabadb4f`. The retained Android
JPEG proxy and the Bot/Release JPEG/PNG/WebP proxies share the first-party
V10 preview. Images load only on demand with metadata-only source queries,
two active downloads and 30 attempts/minute per worker, without new quota DB
writes. Unsupported formats and privacy-safe technical event intake remain open.
Remaining management, sanitized feedback exports and separately approved staging/real ChatGPT acceptance are
still open. Commit/push each completed, tested increment to the feature branch.
Synthetic QA is not physical-device, staging or real ChatGPT evidence.

## Historical references

[Original implementation record](HSK_AI_ADMIN_PWA_TEMP_HANDOFF.md),
[PR #200 resume](CODEX_RESUME.md), [PR #200 merge preparation](MERGE_READINESS.md)
and [Phase 0 API inventory](PHASE_0_API_INVENTORY.md) preserve earlier evidence.
Their old branch names, test counts and next-step instructions do not supersede
the current handoff. Do not recreate completed OAuth/passkey/payment foundations.

These documents apply only to Admin PWA. The existing Telegram `/admin.html`
and other platform/business contracts remain preserved. Source code and test
results do not establish live DNS/TLS, provider or deployment configuration.
