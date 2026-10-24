# ChatGPT MCP compatibility and security audit — 2026-10-24

**Status: not compatibility-verified; not staged or deployed.** This is an evidence-based code audit for Draft PR #201, not a real ChatGPT connection.

## Current implementation

- The feature-gated Python OAuth server implements one configured client and callback, S256 PKCE, explicit WebAuthn-browser consent, hashed one-use code, 300-second bearer token and statistics-only MCP JSON-RPC subset.
- New first-party owner-only consent history/revoke logic in app/admin_api/pwa_mcp_management.py invalidates unredeemed codes and issued grants. It is not an external MCP tool.
- All three feature flags stay OFF. No access to Users, feedback, payment, delete, broadcast or other MCP mutations.

## Release-blocking client compatibility findings

1. **Client registration.** OAuth metadata currently advertises client_id_metadata_document_supported=false, and has no DCR registration endpoint. Static server client ID and callback are blank by default. Official ChatGPT now uses CIMD or DCR according to the connector configuration. Obtain its *actual* permitted client identity and callback in an isolated test workspace and implement a verified registration scheme; do not invent IDs, fetch arbitrary URLs, or infer approval.
2. **Issuer identification — IMPLEMENTED, source tested.** As of code SHA 7ee2f5ca70caf20a26763540589d02948ce639e9, authorization-server metadata advertises RFC 9207 authorization_response_iss_parameter_supported=true, and success/denial callbacks append the exact issuer as iss while preserving client state. The exact ChatGPT callback and client identity still require controlled staging verification; this change alone does not prove ChatGPT connection compatibility.
3. **Token lifecycle.** The five-minute access token has no refresh mechanism. Expiry returns a 401 protected-resource challenge, but automatic reauthorization in ChatGPT is untested. Do not assume it works or simply lengthen token life. Only add rotated one-use refresh tokens if needed and separately security-reviewed.
4. **Protocol versions.** The custom subset accepts 2025-06-18 and 2025-11-25. Modern MCP 2026-07-28 adds stateless server/discover and per-call metadata and routing headers; current code does not implement this era. Test a maintained SDK/Inspector with the actual ChatGPT client version.
5. **Audit/quota.** Database-backed consent/grant states are not a complete per-tool audit trail. No persistent distributed request quota exists. Add minimal privacy-preserving audit records (no token, state, PKCE, payload or statistics response), retention rules and quotas in a later migration.
6. **Logout/revocation.** Browser logout prevents further code redemption but does not currently revoke a token previously issued for up to 300 seconds. Explicit connection revoke immediately invalidates affected grants. Define whether logout should also terminate OAuth connections and test racing requests.
7. **Network.** No actual DNS, TLS, trusted proxy, staging OAuth or real ChatGPT consent/tool-call verification is evidenced. Verify only in isolated staging after explicit owner approval, never by activating production flags.

## Verification gate

Require latest branch-head Admin PWA Python tests, real disposable PostgreSQL lock/migration tests, UZ/RU/TJ catalog checks and mobile/desktop browser tests. Management and issuer callback tests passed at code SHA 7ee2f5ca70caf20a26763540589d02948ce639e9 in Admin PWA CI run https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/40080708288 (288 passed / 13 skipped + 61 legacy + 13 real PostgreSQL, browser/locale QA passed). Preserve V10 design and named in-repo hsk-ai-ui and webapp-testing skills for any new UI.

## Official references

- https://developers.openai.com/plugins/build/auth
- https://developers.openai.com/plugins/changelog
- https://blog.modelcontextprotocol.io/posts/2026-07-28/
- https://ts.sdk.modelcontextprotocol.io/v2/protocol-versions

No PR merge, production deployment, flag activation, external credentials or live DB migration is authorized.
