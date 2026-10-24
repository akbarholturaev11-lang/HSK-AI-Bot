# HSK AI — Admin PWA implementation plan

Status (updated 2026-10-24): **Current entry: [MCP_NEXT_CHAT_HANDOFF.md](MCP_NEXT_CHAT_HANDOFF.md). Auth/passkeys, payment review, V10 UI, scoped OAuth/MCP controls, profiles, activity metrics, daily statistics cache, native intake, inbox read/triage/search and default-OFF Apple Push sender code exist. Android/Bot/Release raster previews and bounded first-party statistics JSON/CSV exports are implemented. Unsupported media, technical events, retention/audit follow-ups, remaining management/sanitized feedback exports and real staging/provider/device/ChatGPT acceptance remain open. The old 0011 cold-start migration failure remains separate.**

Target public URL: `https://hskai.app/admin` (owner-designated; live routing/TLS not verified).
Branch: `feat/admin-pwa-mcp-readonly-20261024`, Draft PR #201; PR #200 foundations are already merged. No main push/merge, deploy or flag activation.

## Active continuation — owner instruction, 2026-10-24

Work only on `feat/admin-pwa-mcp-readonly-20261024`, Draft PR #201. Commit and
push each completed, tested increment to that branch. Never merge/push main or
deploy. Historical `codex/admin-pwa` status below describes PR #200 foundations;
`MCP_NEXT_CHAT_HANDOFF.md` supersedes its implementation counts.

1. **Implemented statistics and accounts**: canonical read-only user profile, paginated
   billing history, course/referral/device/feedback summaries; then defined AI
   spend, engagement and conversion metrics. Preserve unavailable attribution.
2. **Unified inbox continuation**: read/triage/search/badge and native intake
   and Android/Bot/Release image preview are implemented. Technical sources,
   unsupported media and retention/audit gaps still require separate review.
3. **Implemented cached statistics exports**: first-party JSON/CSV and metric
   definitions from the existing 24-hour reader; original generation/expiry,
   source/range/scope and separate currencies retained. Explicit V10 downloads,
   128 KiB / 96-row / 32-currency bounds, WebAuthn cookie/current-admin recheck,
   no force-refresh, new aggregate SQL on cache hits, disk job or R2. Sanitized
   feedback export still needs separate privacy/schema review. External MCP
   remains statistics-only; exports do not add an external tool or scope.
4. **First-party management**: shared course/access/pricing/marketing/settings
   commands with exact WebAuthn payload binding, confirmation and audit; keep
   unsupported high-risk operations disabled until independently verified.
   Manual Pro grants now use the shared subscription service and atomic 0126
   command audit, with exact snapshot/target/day confirmation in V10. Remaining
   course/HSK unlock/configuration/marketing operations still need their own adapters.
5. **Staging acceptance**: isolated provider/device/TLS/proxy/migrations and
   actual ChatGPT E2E, then owner review. Needs real staging configuration and
   available hardware; never count synthetic tests as that evidence.

Progress: profiles `996ea058`, activity metrics `a7f0a5d1`, native intake
`5304cb7a` and daily shared statistics `4709c660` are implemented. Subsequent
GitHub updates through `d93b75fe` add inbox/triage/search, default-OFF Apple Push
sender and the Android attachment proxy. Exact SHA-specific CI evidence belongs
in the current handoff; do not infer live provider/device acceptance.

Each increment records its actual checks in the current handoff before commit.
No release completion claim until the final acceptance contract is satisfied.

## Daily-statistics decision — owner clarification, 2026-10-24

Primary purpose is to reduce unnecessary DB work. The owner selected daily
updates after discussing R2. Reuse the existing Redis dependency/configuration
for private 24-hour aggregate snapshots shared by Admin PWA and MCP; refresh
only requested, expired variants on first authorized demand after 24 hours
from `generated_at`, not at a fixed nightly time. R2 integration is not required to achieve
this read-load reduction and is not implemented here. No periodic all-platform
full scans are added. Keep current timestamps and live billing/access commands;
cache no identities/permissions. Redis outage fallback is per worker and may
recalculate after restart; auth/revoke/audit/quotas still use current DB facts. `READ_PROJECTIONS.md` records coordination,
failure limits and the private-Redis staging gate. This temporal contract
supersedes the previous per-open aggregate calculation for these two surfaces.

## Fixed decisions

1. **One backend, two authenticated entry points.** Keep current Telegram `/admin.html` and `X-Telegram-Init-Data` behavior unchanged. Use public browser URL `https://hskai.app/admin` with isolated shell/assets under `/admin/` and auth `/api/admin/v1/auth/*`. Check all route collisions, reverse-proxy mapping and HTTPS before exposing. Reuse services and business logic; don't fork entitlement/payment rules.
2. **UI source of layout:** locally reviewed HTML demo V10 (`hsk-ai-admin-ux-demo-v10.html`) is a DESIGN REFERENCE, not production code. Remove all synthetic users, sample metrics, browser-only financial changes, sample notifications, placeholder actions, and unsafe `file://` assumptions. Do not import demo fixture arrays into deployed code. Preserve clear UX sections and a single top-row period selector, platform filter, and notification bell.
3. **Server authority.** Stats, permissions, subscriptions, user account identity, payment decisions, HSK 3.0 unlock and price changes remain server-authoritative. Both admin surfaces must resolve to the same canonical admin actor.
4. **Telemetry semantics.** Overall = deduplicated canonical accounts where possible. Platform views must be defined explicitly as platform usage and can overlap; **do not sum** platform-user counts as total users. Label registration, activity, install, exposure, attribution and payment metrics separately. Show unsupported/untracked future platform metrics as "not available", never zero.
5. **Risk / privacy.** Browser admin pages, API responses, personalized feedback and files use `Cache-Control: no-store`. PWA service worker may cache only public, versioned application-shell assets; NEVER cache authenticated JSON, token responses, PII, payment screenshots, feedback attachments or application credentials. Offline admin data returns a clear unavailable state.
6. **Local-first localization.** Author any new permanent UI copy in canonical UZ/RU/TJ catalogs following `localization/README.md`, then generate and check bundles; demo-only prose is not a localization source.
7. **Security:** no session token in localStorage, sessionStorage, URL, deep-link query or GitHub; use HttpOnly Secure cookies, HTTPS, strict origin/CSRF checks, CSP, no framing, idle/absolute timeout, revocation and rate limits. **Onboarding only:** verified Google OAuth OIDC identity + one-time approval by a Telegram account currently in `ADMIN_IDS` + verified binding to canonical admin + create discoverable WebAuthn passkey. **Returning sign-in priority:** WebAuthn passkey FIRST (without requiring Google again), verifying server challenge, RP ID, origin, credential ownership, user verification and current admin privileges; a still-valid browser session needs no new sign-in. Linked Google is a fallback, as is explicitly approved Telegram recovery. **High-risk mutations:** additional fresh WebAuthn transaction-bound re-verification, confirmation and audit logs. Passkey may invoke Face ID, Touch ID, Windows Hello, fingerprint or device PIN/passcode; web code cannot demand Face-ID-only.
8. **Do not touch main or deploy** until acceptance and planned release. Browser/SW must not cache private data; only the private server aggregate cache above is permitted. External MCP remains statistics-only without profile/feedback/payment-list or mutation tools.

## Historical repository sources (Phase 0)

The initial inventory below predates current auth/UI/inbox code; it is not a
missing-feature list. Use the current handoff and source before implementation.

| Requirement / capability | Existing source and behavior | Gap |
|---|---|---|
| Telegram Admin frontend | `app/static/admin.html`, served by `GET /admin.html` in `app/main.py` | Telegram WebApp-based; not browser PWA login |
| Telegram verification | `app/services/telegram_webapp_auth.py`; `_admin_miniapp_user_id` + `_admin_auth_error` in `app/main.py` | Admin APIs currently need fresh Telegram initData, not a browser session |
| Admin authorization | `settings.ADMIN_IDS`, `app/services/admin_access.py` | Must bind browser identity to allowlisted admin and canonical account |
| Admin read models | `app/services/admin_miniapp_service.py`, `app/services/admin_finance_stats_service.py`, Android/Desktop analytics services | Provide versioned, paginated, filtered API projections to PWA; preserve existing schema/contracts |
| Existing API | `/api/admin-miniapp/overview`, `finance-stats`, `management`, `android-stats`, `desktop-stats`, user/payment/admin settings endpoints | Cannot simply reuse Telegram header from standalone browser; shared authorization adapter required |
| User identity | `app/services/admin_user_target.py` and canonical `users.id` contracts | Do not confuse canonical user IDs with legacy Telegram IDs |
| Bot feedback | `app/db/models/bot_feedback.py`: feedback content, language, replied-by, attachment file ID | Universal inbox projection and statuses/triage needed |
| Release feedback | `app/db/models/release_feedback.py`: campaign, rating, comment, attachment | Join into read-only universal inbox without losing source IDs |
| Bug reports | Native authenticated `/api/v3/android/bug-report` and existing Telegram admin delivery documented in `PROJECT_MEMORY.md` | Some delivered reports are not a durable moderation queue: add persistence before claiming a complete inbox |
| Admin notices | `app/services/admin_notify_service.py` | Telegram sending does not equal durable PWA inbox storage |
| Public-site stats | `app/services/public_site_analytics_service.py` | Page visits are not unique people; preserve source definition |
| Localization / skills | `localization/README.md`, `AGENTS.md` including hsk-ai-ui / frontend-design constraints | Mobile-first, safe area, no duplicate copy, no independent inline translation dictionaries |
| Existing Google OAuth / identity linking | `app/services/google_auth.py`, `app/services/native_oauth_service.py`, `app/services/identity_link_service.py` | Reuse verified subject / OIDC primitives, but implement distinct admin browser OAuth callback + session; no email-based admin allowlist. |
| WebAuthn authenticator | No current Admin PWA WebAuthn server verification/credential table or routes confirmed | Implement FIDO2/WebAuthn registration and passwordless assertion backend; never read biometric data. |
| Domain | `hskai.app` is owner-designated | Check actual live HTTPS/TLS, public route mappings, service-worker scope, OAuth redirect registration and WebAuthn origin / RP ID. |

## Architecture: existing Telegram + passkey-first browser PWA

```text
https://hskai.app/                  Public HSK AI site (unchanged)
https://hskai.app/admin             Protected Admin PWA (new)
    ├─ First use: Google OIDC + one-time Telegram admin approval + enroll passkey
    ├─ Returning: existing valid session OR Face ID / Touch ID / Windows Hello passkey
    ├─ Recovery: linked Google or audited Telegram-approved recovery
    └─ Sensitive mutation: transaction-bound passkey confirmation
                         │
                         ▼
            Verified browser admin session
                         │
                         ▼
                 Shared Admin API
                         ▲
                         │ Telegram initData guard (unchanged)
https://.../admin.html  Existing Telegram Admin Mini App
                         │
                  Shared services / DB
                         │
                 Read-only export API
                         │
                ChatGPT / local / later MCP
```

**Passkey sign-in is a FULL login**, not merely a second factor. Registration creates a **discoverable/resident credential**, requiring the user's verification. Returning login must accept a server-generated random one-use challenge with optional username-less credential discovery; resolve the verified credential to an actual linked admin account **on the server**, recheck privileges and disabled/revoked credentials, then mint the scoped HttpOnly browser session. A Google login must not be demanded every time. If session cookie remains valid, normal reopening does not trigger authentication.

**Domain binding:** production HTTPS origin = `https://hskai.app`; configured WebAuthn relying-party ID = `hskai.app`; `/admin` is a page path, NOT the RP ID. Verify DNS/TLS/reverse proxy, canonical redirect, PWA scope, and registered Google redirect URIs **before** real enrollment. Staging origins use separate explicit RP/origin policy. Never assume credentials registered on a temporary Railway host can be used on this domain.

**WebAuthn UI wording:** on a Face ID-capable iPhone the device ordinarily offers Face ID; WebAuthn can also use device passcode/PIN or another passkey/security key. Do not promise Face ID exclusively or try to access any biometric template. Use platform feature detection and manual iOS installed-PWA smoke testing.

**Google/TG binding:** verify OAuth authorization code + PKCE/state/nonce, issuer, audience, expiry and stable subject. Initial browser linking requires a Telegram Bot confirmation sent/approved by an actual allowlisted admin; match canonical admin identity and prevent provider collisions. Email/username is not admin authority. Deny auto-provisioning an admin from a new Google account. Revoke sessions/passkeys/provider binding when removing privileges.

**Recovery:** losing one passkey must not lock out the last admin. Enroll an additional passkey/security key where possible and implement a carefully audited emergency recovery using linked Google and fresh Telegram approval when needed. Recovery is not a bypass for sensitive actions.

API layering: dedicated routes `/api/admin/v1/auth/*` for browser sign-in/out/status; admin data endpoints use a common service and guard that accepts **verified** Telegram transport OR verified PWA session, with explicit route-specific CSRF checks on cookie-authenticated mutations. Prefer new `/api/admin/v1/*` projection routes over broad mechanical edits of every `/api/admin-miniapp/*` handler. Existing Telegram endpoints must stay backward-compatible. Never accept an arbitrary user ID from a client to establish admin privileges.

## Original implementation phases (design reference)

The active continuation above supersedes old phase order and incomplete
checkboxes below. Acceptance still requires actual staging/device evidence.

### Phase 0 — Audit and contract (initial inspection)
- [x] Document public address target `https://hskai.app/admin`, first-run Google + Telegram link and passkey-first returning login.
- [ ] Verify actual `hskai.app` HTTPS certificate, DNS, proxy/route, OAuth redirects, PWA scope and RP ID behavior before writing hostname-bound live auth.
- [ ] Make the read/write/danger API inventory a signed-off gate; existing endpoint list is documented in `PHASE_0_API_INVENTORY.md`.

- [x] Identify current branch, Telegram admin authorization path, admin APIs, statistics sources and feedback persistence gaps.
- [x] Record design reference and non-negotiable Telegram/backward-compatibility/security constraints.
- [ ] Map all existing admin endpoints into read-only vs mutation vs dangerous operations, with response schema, source, and authorization contract.
- [x] Inspect/hash actual conversation-mounted V10 HTML and record view component map in `docs/admin-pwa/ADMIN_PWA_V10_UI_REFERENCE.md`. Original demo bytes are **not** stored in GitHub; re-obtain before UI porting.
**Acceptance:** reviewed API inventory, auth threat model, data dictionary and initial regression list. No production change.

### Phase 1A — Browser identity foundation + one-time Google/Telegram link
- Reserve `https://hskai.app/admin` after confirming host TLS/route mapping, with isolated browser auth endpoints and disabled-by-default rollout flag.
- Implement short-lived, server-stored Bot approval challenge bound to the initiating browser and approved by a Telegram identity present in `ADMIN_IDS`.
- Integrate existing verified Google OIDC subject primitives for browser redirects with PKCE/state/nonce. New Google identity only enters an admin binding after the one-time Telegram approval. Do NOT create admin authority from an email match or Google sign-in alone.
- Implement server sessions using Secure/HttpOnly scoped cookies, revocation, expiry, CSRF/origin protection, rate limits, audit trail and a read-only `/api/admin/v1/me` probe; preserve legacy Telegram Mini App route and auth exactly.
**Acceptance:** denial for anonymous/non-admin/collision/replay/stale/bad-origin cases, Google linking succeeds only with real Bot approval, old admin Telegram workflow passes.

### Phase 1B — Register passkey + passwordless returning login (core requirement)
- Post-onboarding passkey setup: server challenge and registration; store credential ID, public key, canonical admin owner, backup/sync flags, sign count and lifecycle metadata. Request `residentKey:"required"` and `userVerification:"required"` where supported.
- Sign in by passkey alone on later browser visits without Google or Telegram: verify assertion challenge/expiry, RP ID `hskai.app`, exact allowed origin(s), signature, account ownership, user-verification flag, revocation and up-to-date admin permission. Issue a new HttpOnly browser session only after proof.
- Open PWA without prompts when existing session is valid; otherwise present **“Passkey / Face ID билан кириш”** first and linked Google/Telegram as recovery options. Do not call it guaranteed Face-ID-only.
- Verify manual Safari vs standalone Home Screen PWA, Mac Touch ID, Windows Hello, Android supported-device cases and browser failure/recovery states.
**Acceptance:** user can log out, return and log in solely with registered passkey; cross-account, replay, wrong domain/origin, revoked credential and missing verification fail closed.

### Phase 1C — Fresh transaction-bound passkey confirmation for dangerous commands
- For payment approvals/rejections, delete/block/grant access, bulk messaging, pricing/bank/payout edits: explicit human-readable transaction summary → one-time WebAuthn user-verified challenge **bound to action + target + payload hash + active session** → server-side atomic authorization and execution with audit.
- Never accept a previously verified generic login as authorization for a different sensitive transaction. Keep legacy Telegram commands and safeguards unchanged.
- Support multiple enrolled passkeys/security keys and secure recovery/revocation; biometrics never leave device, and PIN/passcode may be offered by the OS.
**Acceptance:** cross-action replay and amount/target tampering fail; only verified admin can execute with fresh per-action step-up. Implement before exposing dangerous PWA commands.

### Phase 2 — PWA shell and V10 UX
- Convert demo into maintained assets/components; keep responsive mobile/desktop navigation, top-level title, header notification bell and collapsed top-row selectors.
- Add manifest, real icons, installation UX; service worker **shell-only** cache and safe update UX.
- Core UI states: signed out, loading, error/retry, empty, permissions, expired session, partial datasets, offline.
- User-facing copy comes from canonical UZ/TJ/RU i18n catalog.
**Acceptance:** installable on eligible browsers; no PII in cache/storage; mobile safe-area / screen reader / keyboard navigation and JS errors tested. Telegram UI untouched.

### Phase 3 — Statistics and data semantics
- Expose query adapter of existing analytics/finance services with stable metrics definitions.
- Top-level platform filter choices: Overall / Telegram Mini App / Android / macOS / Windows / future iPhone PWA. Mark future, untracked platforms as unavailable, not fabricated values.
- Period selector: 7 days / 30 days / all time. Each metric defines period bounds, time zone, source, update timestamp, distinct user grain and attribution logic.
- Separate overall account metrics, platform-specific engagement, course completion, activation/cohort retention, subscription conversion, payments, revenue, estimated AI cost and public-site visits.
- No misleading all-platform aggregation of overlapping platform users, no sum of mixed currencies, no confusing launch event with install.
**Acceptance:** compare PWA endpoints to current admin service results with seeded DB fixtures; test platform overlap and date boundaries.

### Phase 4 — Users, finance and controls
- Users list with server-side pagination/search/filters and canonical user ID, profile with payment, device, language, level, activity, referral and feedback detail.
- Payments, pricing by method and duration, HSK 3.0 unlock/payment enabled flags, course access, Free/Trial limits.
- Marketing, broadcast/test-send, ads, partners, channels, help, AI models — migrate one at a time using existing service commands and audit trail.
- Dangerous commands require explicit confirmation, **transaction-bound WebAuthn passkey step-up** under Phase 1C, idempotency keys where relevant and elevated authorization; demo buttons must never silently succeed.
**Acceptance:** same backend outcomes for Telegram and PWA, regression tests for approvals/rejections and access grants, no double writes.

### Phase 5 — Unified durable feedback and notifications
- Add a canonical inbox event/triage projection for (a) bot feedback, (b) release feedback responses, (c) Android/native bug reports, (d) administrator/system alerts.
- Persist previously ephemeral bug submissions, with source, canonical actor, source ID, event time, platform, app version, language, category, severity, lifecycle status and attachment reference.
- Deduplicate events, retain original source records and Telegram notification delivery. Protect attachments via permission-checked endpoints; sensitive payloads stay out of generic analytics/export.
- UI: header bell unread count, critical/urgent section, collapsed filter, search, read / assigned / resolved states, links to the user's canonical detail.
**Acceptance:** each source arrives exactly once; critical alerts first; missing media, no Telegram ID, failed delivery, pagination and restricted attachment tests.

### Phase 6 — AI / Cloud data access (read-only first)
**Quickest path:** authenticated, admin-only JSON + CSV exports from the same trusted analytics/feedback query layer, bounded date ranges, audit logs, sanitized defaults. ChatGPT or local tools can work from a downloaded export without database credentials.

**Current MCP:** only `hskai_statistics` / `admin:analytics:read` is implemented
and approved for external clients. It reuses the private daily aggregate cache.
User/feedback/payment-list tools, arbitrary SQL/URL and mutations remain excluded.
Broader sanitized exports are a separate first-party requirement, not permission
to expand MCP. See [MCP contract](MCP_CONNECTION_CONTRACT.md).

Use separately issued, revocable short-lived machine credentials with **read scopes**, audience binding, throttling, row and date limits, data minimization, access auditing and explicit PII opt-in. Do not expose write, billing, delete, broadcast or account-control endpoints to AI agents. GitHub connector alone can inspect code, **not runtime production database statistics**. Local workspace access to a staging clone is not production access.

**Acceptance:** read-only AI client can answer a conversion drop or frequent complaint question with consistent sources and field definitions, without PII leakage or mutation rights.

### Phase 7 — Staging, rollout, regression and monitoring
- Separate staging DB/credentials and test accounts; no production payment approvals, notifications or broadcasts during tests.
- CI: Python auth/unit tests; Telegram Mini App unchanged; API contract; security; browser E2E desktop/mobile; offline/installation; seeded feedback and payment state.
- Deploy under explicit feature flag / isolated route; verify logs, page-cache headers, rate limits, origin/CSP, and rollback path.
- Promote only after manual admin acceptance and rollback verification.

## Original dependency sequence (historical planning)

1. **Phase 0:** domain and production-route verification, API threat model/inventory, existing Telegram regression baseline and demo UX-component mapping; no live deploy.
2. **Phase 1A:** safe admin cookie session, protected `/api/admin/v1/me`, verified browser Google OAuth and **one-time Telegram Bot admin approval binding**. Separate from current Telegram Mini App.
3. **Phase 1B:** **passkey enrollment AND passkey-only sign-in**, with valid session reuse and linked Google/Telegram recovery; this is the principal day-to-day admin login.
4. **Phase 2:** standalone installable PWA shell and V10 UI conversion; remove demo fixtures; connect first real read-only `me/overview` data.
5. **Phase 3:** full statistics and platform/period definitions, tests and exports without PII by default.
6. **Phase 5 (read-only/inbox first):** persist native bug reports, unify existing bot/release reviews and alerts in a durable inbox so critical messages and feedback actually exist in DB.
7. **Phase 1C:** production-quality per-transaction WebAuthn step-up and backend command authorization; prerequisite for sensitive control endpoints.
8. **Phase 4:** migrate PWA user/account/billing/course/marketing/admin actions one at a time; dangerous controls remain disabled until step 7 passes.
9. **Phase 6:** audited JSON/CSV read-only export first, optional dedicated read-only MCP after scope/privacy testing (AI/Cloud does not get admin mutation privileges).
10. **Phase 7:** staging test (auth/Telegram regressions, PWA Safari standalone, Chrome/Windows Hello, security, accessibility), manual acceptance, documented rollback then controlled production release.

**Parallelizable tasks:** PWA shell/design mapping and metric data dictionary can proceed after protected read session contract is stable. Inbox storage design can begin alongside statistics. Never ship privileged admin writes before Phase 1C.

## Initial Phase 1 questions (historical; recheck current source)

- Owner designates production `https://hskai.app/admin`; verify live DNS, TLS, redirects, configured provider OAuth callback, server reverse-proxy route and whether RP ID is usable from this host. Which staging host/origin and bot username are canonical, and what callback/deep-link contract does the existing bot router already support?
- How should a browser-authenticated admin actor map to canonical user ID while existing audit `created_by_telegram_id` fields remain backwards compatible?
- How are Android bug-report attachments stored and retained, and which current app variants generate them?
- Which platform events are authoritative for Mac vs Windows, and which prospective iPhone PWA events have no instrumentation yet?
- Which admin services unexpectedly commit on read? Extract read-only projections without importing these side effects into AI access.

## Historical test and release notes

This document records source-code observations; it is not evidence of an active PWA, deployment, user-session security testing, database migration, or production end-to-end QA. No production endpoint is enabled by this planning change.


### WebAuthn registration CI (2026-10-24)

Dedicated read-only feature-branch GitHub Actions workflow passed **110 full-checkout Admin PWA tests**, compiled the new Python code and found a unique Alembic head at `0114_admin_pwa_webauthn_registration`; see https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/40026176016. Mock-verifier tests are not proof of genuine FIDO2 attestation, and no database migration was actually applied to PostgreSQL. Passkey-only sign-in, real session issuance and step-up remain not implemented. Keep feature flag disabled.


### PostgreSQL + sign-in evidence (2026-10-24)

`codex/admin-pwa` now includes passkey login and revocable sessions. Verified [CI run 40028060236](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/40028060236): 134 passed/2 skipped main suite, plus 2 passed on disposable real PostgreSQL 16, scoped Admin PWA Alembic 0110–0115 upgrades and 0115 downgrade/re-upgrade. Full legacy cold-start Alembic remains blocked at 0011 (`course_progress` absent), and no physical biometric test / Admin PWA UI / step-up exists. Feature flag OFF, no main/production changes.


### Step-up authorization foundation verified (2026-10-24)

Committed per-action, per-target, payload-digest-bound WebAuthn confirmation and one-time consumption helper on `codex/admin-pwa`. [Full-checkout CI](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/40029175593): 152 passed/3 PG-only skipped; [same run] real PostgreSQL: 3 passed, migration 0110–0116 and rollback/reapply. These functions do NOT yet execute sensitive mutations. Next separately review one dedicated operation adapter and audit/confirmation UX, no blanket reuse of Telegram initData; flag remains OFF.
