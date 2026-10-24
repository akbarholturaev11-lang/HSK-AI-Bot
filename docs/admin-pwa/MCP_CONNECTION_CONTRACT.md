# HSK AI ↔ ChatGPT MCP — connection and security contract (NOT LIVE)

**Status 2026-10-24:** Only an internal read-only Python adapter exists in
`app/admin_api/pwa_mcp_readonly.py` with fail-closed unit tests.
This is **not** a discoverable MCP server, not a ChatGPT plugin, and NOT an
activation of Admin PWA. Current default `ADMIN_PWA_ENABLED=false`.
No HTTPS `/mcp` endpoint has been registered. No OAuth server, token endpoint,
ChatGPT client registration, consent screen, or production credential exists.

## What the user will do AFTER implementation and approval

1. Owner signs in to HSK AI as a verified canonical Telegram-allowlisted
   admin. The existing WebAuthn passkey session does NOT become a ChatGPT API
   bearer token; it can only facilitate owner-controlled consent in a separate
   OAuth 2.1 flow.
2. In ChatGPT on web, an eligible account/workspace adds an **authorized custom
   MCP server** using the ChatGPT Plugins directory or workspace settings,
   enters its final HTTPS MCP endpoint and authenticates with our separate OAuth
   flow. ChatGPT discovers tools; the owner selects the HSK AI integration
   when requesting stats. Availability varies by plan/workspace; do not
   advertise mobile or Plus availability without official verification.
3. ChatGPT sends bounded, schema-validated read requests carrying scoped OAuth
   credentials; HSK AI MCP resource server checks token **issuer, signature,
   audience/resource, expiration, consented scopes, revocation** and the current
   canonical admin rights per request. Tool parameters may NEVER supply admin
   identity, scopes, cookies or bearer-token overrides.
4. HSK AI's adapter calls existing **Admin PWA read-only projections** using a
   PostgreSQL READ ONLY transaction. Only consented fields are returned;
   statistics missing attribution remain clearly unavailable instead of 0.
   Neither payment mutations, user deletion nor broadcast actions are exposed.

## Proposed read-only tools (not currently installed in ChatGPT)

| Tool | Required narrow scope | Existing data service |
| ---- | --------------------- | --------------------- |
| `hskai_statistics` | `admin:analytics:read` | `pwa_read.statistics` |
| `hskai_users_search` | `admin:users:read` | `pwa_read.users` |
| `hskai_feedback_list` | `admin:feedback:read` | `pwa_read.feedback` |

**Privacy recommendation:** launch stats-only first. Explicit separate
consent, audit and retention review are required before user profiles or
free-form feedback are remotely exposed. Feedback is untrusted text, NOT
instructions for the MCP server to execute. Never expose attachments, secrets,
Google subject hashes, access tokens or Telegram initData.

## Remaining implementation gates — MUST remain disabled until complete

- Decide final HTTPS endpoint under controlled HSK AI domain (for example a
  `/mcp` path is a proposal, **NOT a deployed or existing URL**); implement a
  maintained MCP Streamable HTTP transport with proper initialization, tools
  discovery and call handling. Use secure ingress and **do not** expose a DB
  session-based test function directly on the public internet.
- Implement/spec-test dedicated OAuth authorization-server discovery,
  PKCE/authorization code, consent, short-lived scoped access tokens, refresh
  token rotation and revocation as applicable; validate audiences and avoid
  token forwarding to third parties.
- Introduce an audited **MCP-specific authorization context**, not a browser
  `__Host-hskai_admin` cookie in the ChatGPT request. The existing internal
  adapter takes server-owned session proof; it deliberately has no public MCP
  transport. Any remote adapter should accept a separately VERIFIED grant and
  re-check current admin allowlist and source-specific scope; do not copy
  cookies into ChatGPT or access-token strings into tool arguments.
- Add per-admin tool call audit (access without storing raw feedback), quota,
  short timeouts, pagination and data-minimization/redaction. Probe OAuth
  misbinding, SSRF, SQL injection and prompt-injection from feedback.
- Validate ChatGPT discovery and OAuth interaction with a test workspace using
  official UI. Do not promise eligibility on any plan; current documentation:
  https://help.openai.com/en/articles/12584461-connecting-custom-mcp-servers-in-chatgpt
- Run main Admin PWA CI and new MCP integration/real PostgreSQL security tests.
  Do not merge the branch or enable Admin PWA without explicit owner approval.
  Existing Telegram Admin Mini App and direct APK business logic unchanged.

**Branch:** `feat/admin-pwa-mcp-readonly-20261024`, created at main merge
commit `891d9d9b6ffda5fba114d9c5c169eeb2f8a7836f`.
