# HSK AI Admin PWA — current MCP continuation checkpoint

Updated 2026-10-24. Read this first; older checkpoints are historical. Verify remote HEAD and CI before editing.

## Repository and boundaries

- Repository: `akbarholturaev11-lang/HSK-AI-Bot`; ONLY work branch `feat/admin-pwa-mcp-readonly-20261024`; [Draft PR #201](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/pull/201), open and unmerged.
- Current runtime changes: `e0270fb91d0c7e24c629d600964a09eb9816be9e`; integrated with concurrent documentation-only updates at `5ef02f1fc1716be8e9026f02aa41e6d312780e8c`. No history rewrite. Official SDK regression/QA dependency pin: `4009e903bb9ddbdbe7361280e229d4997903988b`. Later documentation commits advance HEAD without changing runtime code.
- Remote `main` verified unchanged at `891d9d9b6ffda5fba114d9c5c169eeb2f8a7836f` after the feature push. PR #200 is already merged; do not repeat its foundation work.
- Keep `ADMIN_PWA_ENABLED=false`, `ADMIN_PWA_MCP_ENABLED=false`, `ADMIN_PWA_MCP_TRANSPORT_ENABLED=false`. Resource/client/callback/public-origin defaults remain empty. Defaults do not prove production environment values.
- No main merge/push, production/staging deployment, live migration, secret configuration, flag activation or real external ChatGPT linking is authorized by this checkpoint.
- External MCP exposes ONLY `hskai_statistics` / `admin:analytics:read`. Users, feedback, payment, delete, broadcast, arbitrary SQL/URL and other write tools stay excluded.

## Broader Admin PWA continuation — user profile increment, 2026-10-24

The owner requested the remaining final-product work in tested parts, committing
and pushing each part only to this feature branch. The active ordered worklist
is in `IMPLEMENTATION_PLAN.md`; PR #200 and the MCP foundations below remain done.

First increment: real read-only user profile and paginated all-status billing
history (`pwa_read.py` users/detail and users/payments); existing V10 drawer,
UZ/RU/TJ, course/track snapshots, canonical referral/device aggregates and
account-filtered feedback. See `READ_PROJECTIONS.md` for field/grain boundaries.
No MCP tool, flag default, schema migration or legacy mutation was changed.

Validation in isolated local fixtures: **300 passed, 16 PostgreSQL-only skipped**
for the Admin PWA/catalog/standalone suite; **16 passed on disposable PostgreSQL
15**, including the extended read-only transaction test for profile/payment
history. Real virtual-WebAuthn/browser and service-worker suites passed, with
profile paging, canonical account filter, XSS, 1440px desktop and 390px UZ/RU/TJ
screenshots in `/tmp/hsk-profile-browser-20261024`; mobile Uzbek and desktop
profile screenshots visually inspected. Synthetic fixtures are not staging or
physical-device evidence. Catalog generation: 63 artifacts, one bundle updated.

Next: bounded AI-spend, course-engagement and clearly defined conversion
statistics; then durable inbox and remaining management/export/staging gates.

## Required reading

Read root `AGENTS.md`, `AI_RULES.md`, `PROJECT_MEMORY.md`; `HSK_AI_ADMIN_PWA_TEMP_RULES.md`, latest `HSK_AI_ADMIN_PWA_TEMP_HANDOFF.md`, `MCP_CONNECTION_CONTRACT.md`, `MCP_CHATGPT_COMPATIBILITY_AUDIT_20261024.md`, `BROWSER_UI_CONTRACT.md`, `ADMIN_PWA_V10_UI_REFERENCE.md`; then real source/tests. Historical `codex/admin-pwa` branch references are superseded by the user-selected feature branch above.

For UI, read actual `.agents/skills/hsk-ai-ui/SKILL.md` and `.agents/skills/webapp-testing/SKILL.md`; these were read and applied in this increment. Read `localization/README.md` before copy changes. Author UZ/RU/TJ `ui.admin_pwa.*` in canonical `localization/ui/*/miniapp.json`, generate/check with `scripts/i18n_build_all_catalogs.py`; never edit generated catalogs directly.

## Implemented — do not rebuild

- `pwa_mcp_oauth.py`: one exact predefined public client/callback, authorization code + S256 PKCE, session-bound three-minute explicit consent, hashed one-use CSRF, 60-second single-use code and 300-second hashed opaque access token. Client-ID shape now matches the resource verifier; configured callbacks cannot preseed/duplicate OAuth response fields. CSRF hash is cleared after allow/deny.
- `pwa_mcp_consent_transport.py`: actual GET/POST `/oauth/authorize`, same-session allow/deny, exact Origin + Fetch Metadata + CSRF, RFC 9207 `iss` on successful/denied redirects, state preservation. New V10 localized sign-in/retry and expired/restart screens contain no reflected OAuth query or credentials.
- **Browser bug fixed:** `no-referrer` caused native form POST to send `Origin: null`, failing CSRF. Consent HTML/header now use `strict-origin`; native browser tests assert real Origin and origin-only Referer, while CSRF checks remain strict. See the Fetch standard reference in the compatibility audit.
- `pwa_mcp_management.py`: mounted owner-only cookie API for last 30 consent records and atomic revocation of outstanding codes plus ALL issued grants. Current canonical WebAuthn admin and same-user ownership required. History includes actual active-access expiry and expires pending records correctly. APIs now use the existing PWA `ok` envelope.
- `pwa_bootstrap.py`, `app.js`, `styles.css`: server-gated MCP availability; V10 existing drawer for history and separate revoke confirmation, accessible focus/close/Escape, mobile More entry, UZ/RU/TJ labels and explicit loading/empty/error/uncertain/offline/auth states. No new MCP write tool. Lost revoke response requires a history reread.
- `pwa_mcp_http.py`: protected-resource/AS metadata, token endpoint and stateless authenticated JSON-RPC. Supported versions remain `2025-06-18`, `2025-11-25`; initialize echoes a supported request or offers the newest supported version. Subsequent calls require a supported version header. Strict UTF-8/JSON, duplicate/nonfinite/deep input rejection, media/Accept quality checks, invalid Origin -> 403 on every MCP method, notifications -> 202, unknown methods/tools rejected, stats timeout 10s, tool OAuth metadata. Expired/revoked access -> 401 with resource metadata, scope and invalid_token challenge.
- **New security module** `pwa_mcp_security.py`, models `admin_pwa_mcp_security.py`, migration `0121_admin_pwa_mcp_security`: DB-shared minute quotas, audit admission BEFORE protected work, safe completion outcome/actor, seven-day audit retention with bounded 100-row cleanup per admitted/over-limit attempt. Failed audit/admission returns 503 without exposing results. Audit remains separate from the analytics READ ONLY transaction.
- Revocation blocks subsequent authorization checks. A statistics snapshot already authorized before revocation may finish within its existing 10s bound; revocation does not cancel an in-flight SQL statement.
- Quotas: authorize GET 60/min, consent POST 60/min, token 60/min, MCP POST 300/min, history 60/min, revoke 30/min; additional statistics cap 30/min per verified canonical admin across all tokens/workers. Endpoint-wide anonymous buckets prevent token/IP-driven bucket growth. 429 includes Retry-After; repeated global denials are aggregated to one audit row per endpoint/window. Edge network/connection limits still required before staging.
- Audit stores only UUID, allowlisted action, outcome, HTTP status, canonical admin ID if verified, timestamp. No IP, URL/query, header, cookie, code/token/hash, state, PKCE, arguments or statistics result. Exceptions use content-free logs. Downgrade refuses to erase nonempty audit evidence.
- Models registered; guarded disposable QA bootstrap and CI migration head updated to 0121. Existing `pwa_mcp_grants.py` is an earlier unmounted helper; the real mounted implementation is `pwa_mcp_management.py`.

## Actual validation

Local Python 3.12 at the current runtime snapshot:

- Full scoped Admin PWA + localization/QA suite with official SDK regression: **298 passed, 16 PostgreSQL-only skipped** (297 before the SDK-only test commit).
- Disposable local PostgreSQL **15**: **16 passed**, including atomic first-use quota under eight connections, simultaneous code redemption/revocation, READ ONLY checks and migration audit-preservation guard. CI independently uses PostgreSQL 16.
- Real disposable 0109 baseline -> 0110–0121 upgrade, 0121 -> 0120 downgrade and re-upgrade passed. Full historical cold-start migration remains independently broken at old 0011 (missing course_progress); do not claim it fixed.
- Affected legacy payment/subscription/preview/affiliate/import regressions: **61 passed**.
- Catalog check: **63 artifacts, 0 stale**; Python compile and git diff checks passed.
- Actual headless Chromium: virtual WebAuthn/PWA/SW suites passed; real cookie/DB management, revoke cancellation/success and token rejection verified; desktop 1440 + iPhone viewport 390, UZ/RU/TJ history screenshots; consent/sign-in/expired screens passed with no script errors or horizontal overflow. Screenshots: `/tmp/hsk-mcp-browser-20261024` on the original host; CI uploads equivalent synthetic evidence.
- Synthetic consent bridge explicitly supplies Fetch Metadata (Chromium route interception omits network-generated headers). It asserts the real browser Origin and Referer first. This does NOT prove actual HTTPS/proxy or physical iPhone behavior.
- Verified runtime CI: [Admin PWA run 40081833261](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/40081833261), exact `5ef02f1f`, **both jobs green**: 297 passed/16 PG-only skipped, 61 legacy, 16 real PostgreSQL 16, scoped migrations and browser/catalog checks passed. Desktop, TTS and Localization were green at this checkpoint; Backend/Android still required completion verification.
- Verified SDK-test head `4009e903` CI: [Admin PWA run 40082233884](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/40082233884) **both jobs green**: 298 passed/16 PG-only skipped, 61 legacy, 16 real PostgreSQL 16, catalogs, migrations and browser QA. TTS/Localization/Desktop also green; Backend/Android still running when recorded.
- Official Python MCP SDK **1.27.0** controlled-client test `tests/test_admin_pwa_mcp_sdk.py` passed locally: real HTTP authorize/approve/PKCE token, replay rejection, SDK initialize/notification/list/call, actual SQLite statistics and owner revoke -> bearer 401, audit actor/outcomes. No OAuth/statistics service mocks. Only ASGI transport replaces external networking. SDK + compatible sse-starlette 3.0.3 are pinned in CI QA installation alongside all application requirements; no runtime dependency was added.

## Next safe work / release gates

1. Runtime/SDK Admin PWA CI is verified; check latest documentation-head and remaining Backend/Android statuses before any new all-CI-success claim. Do not repeat implemented history/revoke/audit/quota/UI or RFC 9207.
2. Official SDK 1.27.0 controlled compatibility is now tested; do not repeat that foundation. Inspector/real ChatGPT and actual network/TLS remain staging checks. Modern `2026-07-28` discovery/routing features are not implemented or advertised; verify whether the chosen real client negotiates the supported protocol before expanding scope.
3. Official OpenAI docs permit CIMD, DCR OR predefined OAuth clients. This implementation deliberately supports only exact predefined public-client `none` + S256. Obtain actual client ID/callback from the owner’s permitted isolated ChatGPT connection page; do not invent them, treat a CIMD URL as a static identity, fetch arbitrary metadata, or add DCR just because static config is blank.
4. Deliberate lifecycle: no refresh token, access lasts at most 300s; reauthorization requires fresh client PKCE/state and explicit owner consent. Browser logout prevents code redemption but existing OAuth access lasts until its own expiry or explicit revoke. Test this separately approved OAuth-session policy and automatic ChatGPT reconnection on isolated staging. If refresh is necessary, design rotated one-use families with replay detection and consent-wide revocation first; never simply lengthen the access token.
5. After separate owner approval and actual isolated environment/client details: stage under verified DNS/TLS/trusted proxy, configure exact resource/issuer/callback without weakening production constants, enforce edge limits and log redaction, test initial consent/denial, expiry/reconnect, owner revoke, quota and a real statistics-only ChatGPT call. Staging host/resource/RP currently need an explicit isolation design; no permissive wildcard was added.
6. No main/production promotion or full-connector-complete claim until the above release gates have actual evidence. Preserve Telegram `/admin.html`, legacy auth, Android Direct/Play, payments/access and lesson data.
