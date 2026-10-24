# ChatGPT MCP compatibility and security audit — 2026-10-24

Runtime snapshot: `e0270fb9`, integrated as `5ef02f1f`; official SDK regression commit `4009e903`. No live ChatGPT connection, staging deployment or production activation. All three flags remain OFF.

Daily-cache follow-up (`4709c660`): statistics now reuse private server-side
24-hour snapshots; authorization, expiry/revoke, quotas and audit still run on
every call. Aggregate SQL runs only on cache misses after the auth transaction
ends. See [read projections](READ_PROJECTIONS.md) and the [current handoff](MCP_NEXT_CHAT_HANDOFF.md). The validation below belongs to its stated OAuth
foundation SHA, not every later runtime.

## Verified source contract

- One predefined public OAuth client, exact HTTPS callback/resource, `none` token endpoint authentication with mandatory S256 PKCE, explicit WebAuthn-session consent, RFC 9207 issuer on allow/deny, single-use 60s code and 300s opaque access grant. No refresh or remote client-metadata fetch.
- Owner-only history/revoke UI and APIs cancel codes/all grants without exposing a remote write tool. Revocation blocks subsequent checks; an already authorized snapshot may complete within the 10s call bound. Logout does not silently terminate independent OAuth access; it blocks new code redemption. A previously issued token survives only its remaining <=300s unless explicitly revoked.
- `/mcp` remains statistics-only. Every call revalidates current admin, audience, scope, expiry and revoke state, with DB-shared quota, audit reservation and, on refresh, an isolated READ ONLY statistics transaction. DB/admission/audit failures expose no result.
- Seven-day content-free audit and fixed minute counters live in migration 0121. Admission limits are per endpoint plus 30 statistics calls/min per verified admin across tokens. Repeated anonymous/global limit denials are aggregated. This is application quota, not edge/network denial-of-service protection.
- Strict UTF-8 JSON, duplicate/nonfinite/deep input rejection, Origin 403, exact media Accept/q validation, supported version headers, valid initialize schema/version agreement and correct accepted-notification 202 behavior have regression coverage. Only 2025-06-18 and 2025-11-25 are advertised.
- Native consent form had an actual browser failure: `no-referrer` made Origin null on POST. HTML and response policy now use `strict-origin`, preserving Origin while sending no query/path in Referer. Same-origin + one-use CSRF checks remain enforced. Browser regression asserts the real Origin and origin-only Referer.

## Compatibility findings and remaining gates

1. **Predefined clients are supported by OpenAI.** Current official auth documentation explicitly permits CIMD, DCR and predefined clients. Static registration is therefore not inherently incompatible. Real client ID/callback must still be copied from the permitted connection UI and verified; defaults are empty. No invented OpenAI client, wildcard callback or unverified CIMD URL is accepted. If CIMD/DCR is later selected, it needs its own reviewed identity/SSRF/registration implementation.
2. **RFC 9207 is implemented.** AS metadata advertises issuer identification; successful/denied redirect responses contain exact `iss=https://hskai.app` and preserve client state. The management page’s actual callback remains authoritative; a documented stable callback is not evidence of a configured connection.
3. **Reauthorization is deliberate, refresh absent.** Exact expiry produces 401 with protected-resource metadata, scope and invalid_token. First-party screens handle sign-in/retry and expired/restart. Automatic linking/relinking in real ChatGPT remains untested. Tool-level auth UI may additionally require OpenAI `mcp/www_authenticate` metadata; current resource-wide HTTP challenge must be checked with the chosen real client. Do not claim automatic recovery.
4. **Protocol coverage is bounded.** Supported-version negotiation and JSON Streamable HTTP are source/browser tested. Official Python SDK 1.27.0 was tested end-to-end through the real OAuth/ASGI/database services: initialization, notification, tool discovery, actual statistics, replay rejection, revocation and audit. Inspector, external HTTPS and real ChatGPT negotiation remain untested; modern 2026-07-28 discovery/per-call routing is not implemented. Unknown versions are not falsely advertised.
5. **Operational controls still need staging.** Edge limits, trusted TLS/proxy header behavior, request-body/query/authorization log redaction, retention/backup behavior and physical device handling need evidence in a separately approved isolated environment. Database quotas do not replace edge controls. Consent bridge tests synthesize Fetch Metadata omitted by browser interception; the Origin/Referer assertions themselves use native browser values.
6. **Deployment isolation is unresolved.** Production resource/issuer constants are exact and intentionally unchanged. A separate staging host needs an approved issuer/resource/RP/client isolation design, not wildcarding or enabling production flags.

## Executed validation

Local scoped suite including the SDK test: 298 passed / 16 PG-only skipped; separate real disposable PostgreSQL 15: 16 passed (quota concurrency, redemption/revoke race, read-only data and migration evidence retention); affected legacy: 61 passed; 63 catalogs / 0 stale; Chromium 1440/390 UZ/RU/TJ history/revoke, consent/sign-in/expiry and PWA/SW passed. Exact runtime CI 40081833261 at 5ef02f1f passed both jobs (297 scoped, 61 legacy, 16 PostgreSQL 16, browser/catalogs). SDK test head 4009e903 passed both jobs in CI 40082233884 (298 scoped/16 skipped, 61 legacy, 16 real PostgreSQL 16, migrations/catalogs/browser). TTS, Localization and Desktop passed; remaining head-specific Backend/Android status must be checked before claiming all CI green. SDK 1.27.0 and compatible sse-starlette 3.0.3 are QA-only pins; production requirements remain unchanged.

These fixtures contain synthetic identities/statistics. No production credential, account, provider or real ChatGPT call was used.

## Primary references checked

- [OpenAI authentication](https://developers.openai.com/plugins/build/auth): predefined/CIMD/DCR clients, PKCE, token auth methods, exact callback, issuer identification, OAuth challenges and reconnection.
- [MCP lifecycle, 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle): initialize schema and supported-version agreement.
- [MCP transports, 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports): Origin 403, Accept, notifications and protocol headers.
- [Official Python SDK 1.27.0](https://pypi.org/project/mcp/1.27.0/): controlled protocol-client regression, not proof of ChatGPT-specific UI or provider behavior.
- [Fetch standard — request Origin](https://fetch.spec.whatwg.org/#append-a-request-origin-header): referrer-policy effects on non-CORS form POST Origin.

No merge/deploy/flag enablement/secrets/live DB changes are authorized.
