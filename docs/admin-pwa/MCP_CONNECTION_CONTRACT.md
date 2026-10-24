# HSK AI ↔ ChatGPT MCP — connection and security contract (NOT LIVE)

**Status 2026-10-24:** An internal read-only Python adapter exists in
`app/admin_api/pwa_mcp_readonly.py`, alongside an INERT OAuth resource
grant model (`app/db/models/admin_pwa_mcp.py`, Alembic `0118`) and the
server-side validator `app/admin_api/pwa_mcp_resource.py` for **statistics only**.
It requires a SHA-256-backed random OAuth access token in the database, exact
`https://hskai.app/mcp` audience, current canonical admin rights, correct
consent reference, five-minute maximum lifetime, and BOTH feature flags.

This is **NOT** a discoverable MCP server, not a ChatGPT plugin, and NOT an
activation of Admin PWA. Defaults `ADMIN_PWA_ENABLED=false` and independent
`ADMIN_PWA_MCP_ENABLED=false`, with `ADMIN_PWA_MCP_RESOURCE=""`.
The proposed MCP URI is a validation constant only, **NOT a live endpoint**.
No HTTPS `/mcp` route, token issuer, OAuth authorization/token/revocation
endpoints, discovery, client registration, consent screen, audit logs, or
production access credential exists. Do not enable either flag now.

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
- The new **resource-side** validation function is present and requires a
  revocable, audience-bound, client/consent-bound, stats-only five-minute opaque
  access grant. It has no public route and cannot issue tokens. A real remote
  MCP adapter must use this verifier and re-check current admin allowlist,
  not the existing browser-cookie adapter. Do not copy `__Host-hskai_admin`
  into ChatGPT or use a Google ID token as MCP authorization.
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

## Current branch checkpoint (2026-10-24)

- Draft PR #201, branch `feat/admin-pwa-mcp-readonly-20261024`. No main merge.
- Model `AdminPwaMcpAccessGrant`, migration `0118_admin_pwa_mcp_read_grants`, independent kill switch `ADMIN_PWA_MCP_ENABLED` and resource URI configuration were added; all default OFF.
- `verify_readonly_mcp_bearer` checks an opaque token hash, current admin allowance, max five-minute lifetime, exact resource, consent-event ID, registered client ID shape and statistics-only scope. `read_mcp_statistics_with_verified_token` reuses existing PostgreSQL READ ONLY transaction. This module cannot mint tokens or accept cookies as MCP authorization.
- Tests `tests/test_admin_pwa_mcp_readonly.py` and `tests/test_admin_pwa_mcp_resource.py` added; migration workflow expanded to 0118, including downgrade when no grants exist. **Do not claim passing CI until latest PR #201 SHA is green.**
- Next: separate OAuth2.1 authorization-code + PKCE + explicit admin consent issuance and revocation with real audit, then authenticated MCP Streamable HTTP transport; stats only by default. User/feedback privacy needs additional review and separate explicit consent.

## CI verification — GitHub Actions (2026-10-24)

The full code snapshot at commit `e8f09319df8cb197afd53365c6394e4e62ef7e7b` passed both jobs in [Admin PWA isolated security regressions run 40071538466](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/40071538466):

- **249 passed, 12 skipped** in Admin PWA/QA suite. The 12 skipped tests are PostgreSQL-only cases; no failure in this job.
- **61 passed** in legacy payment/subscription/affiliate/route regression suite. UI localization catalogs checked.
- Headless Playwright desktop/mobile/virtual WebAuthn/Service Worker scenarios all passed; these are synthetic browser tests, not real physical Face ID or production OAuth.
- **12 passed** in REAL disposable PostgreSQL 16 suite. Migration `0118_admin_pwa_mcp_read_grants` was applied, downgraded to `0117`, and reapplied. No production database touched.

Earlier failures during development were from out-of-date QA schema head/table fixture expectations after adding `0118` and a test that omitted the required MCP scope. All were fixed and the exact final source SHA above is green. This does NOT prove real ChatGPT connectivity; OAuth authorization code/PKCE/consent, MCP HTTP transport, and activation remain missing.

Draft PR #201 remains intentionally unmerged. Keep both `ADMIN_PWA_ENABLED=false` and `ADMIN_PWA_MCP_ENABLED=false`.

## OAuth authorization-code + explicit consent service (2026-10-24)

- New **inert** module `app/admin_api/pwa_mcp_oauth.py`, DB model `app/db/models/admin_pwa_mcp_authorization.py`, migration `0119_admin_pwa_mcp_authorizations.py`.
- Only one **pre-registered and server-configured** public OAuth client ID and exact HTTPS callback URI are accepted. Both default empty, so no flow may start in production. No untrusted URL fetch/CIMD interpretation and no DCR endpoint.
- The signed-in, currently allowed WebAuthn Admin PWA user may start a 3-minute **pending** request with exact client, callback, resource `https://hskai.app/mcp`, stats-only scope, client state and S256 challenge. It is NOT implicitly approved. A separate browser-bound **explicit approve/deny** service checks the same session and can issue at most one 60-second authorization code stored only as SHA-256 hash. A denial creates no code.
- One-time token exchange verifies S256 PKCE verifier, exact client ID, callback, resource, current unrevoked WebAuthn session and current Telegram admin allowlist; it atomically marks the code redeemed and creates only one 5-minute hashed stats-only access grant. No refresh token.
- **NO public OAuth HTTP routes, browser consent UI, CSRF nonce, authorization server discovery, protected-resource metadata, token endpoint, Streamable HTTP MCP server, ChatGPT client metadata verification/registration, or real ChatGPT connection has been deployed.** All of these are still REQUIRED before either flag can be activated.
- **Verified code SHA:** `4851917a93333f34f010ec9c347e05fff35b1c31`. [GitHub Actions 40072676885](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/40072676885) succeeded in BOTH jobs: **259 passed / 13 PostgreSQL-only skipped** in Admin PWA suite, **61 passed** legacy regressions, desktop/mobile virtual WebAuthn/Service Worker browser QA passed; **13 passed** on disposable real PostgreSQL 16 including two concurrent PKCE exchanges issuing exactly one token. Alembic `0119` upgraded, downgraded to `0118`, and upgraded again. No production DB changes. Existing legacy cold-start migration 0011 gap remains.
- PR #201 stays **Draft**, unmerged. Keep `ADMIN_PWA_ENABLED=false` and `ADMIN_PWA_MCP_ENABLED=false`, as well as default empty `ADMIN_PWA_MCP_CLIENT_ID`, `ADMIN_PWA_MCP_REDIRECT_URI`, and `ADMIN_PWA_MCP_RESOURCE`.
