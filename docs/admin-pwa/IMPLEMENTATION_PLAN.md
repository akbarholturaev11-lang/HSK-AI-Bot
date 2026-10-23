# HSK AI — Admin PWA implementation plan

Status: **Phase 0 — repository audit / architecture baseline recorded; application implementation not started**.
Branch: `codex/admin-pwa` (branched from `main` at `e935e4315df42037d6aab4ab38b2c4e5d9bbb681`).
Scope: deliver a separate secure browser-installable Admin PWA without disrupting the existing Telegram Admin Mini App, admin Bot, Android, Desktop, production or main.

## Fixed decisions

1. **One backend, two authenticated entry points.** Keep the current `/admin.html` and `X-Telegram-Init-Data` flow unchanged. Add an isolated `/admin-pwa/` UI route and new browser-session auth. Reuse existing services and business logic, **not** copy and fork their business rules.
2. **UI source of layout:** locally reviewed HTML demo V10 (`hsk-ai-admin-ux-demo-v10.html`) is a DESIGN REFERENCE, not production code. Remove all synthetic users, sample metrics, browser-only financial changes, sample notifications, placeholder actions, and unsafe `file://` assumptions. Do not import demo fixture arrays into deployed code. Preserve clear UX sections and a single top-row period selector, platform filter, and notification bell.
3. **Server authority.** Stats, permissions, subscriptions, user account identity, payment decisions, HSK 3.0 unlock and price changes remain server-authoritative. Both admin surfaces must resolve to the same canonical admin actor.
4. **Telemetry semantics.** Overall = deduplicated canonical accounts where possible. Platform views must be defined explicitly as platform usage and can overlap; **do not sum** platform-user counts as total users. Label registration, activity, install, exposure, attribution and payment metrics separately. Show unsupported/untracked future platform metrics as "not available", never zero.
5. **Risk / privacy.** Browser admin pages, API responses, personalized feedback and files use `Cache-Control: no-store`. PWA service worker may cache only public, versioned application-shell assets; NEVER cache authenticated JSON, token responses, PII, payment screenshots, feedback attachments or application credentials. Offline admin data returns a clear unavailable state.
6. **Local-first localization.** Author any new permanent UI copy in canonical UZ/RU/TJ catalogs following `localization/README.md`, then generate and check bundles; demo-only prose is not a localization source.
7. **Security:** no token in localStorage, sessionStorage, URL, deep-link query or GitHub; use HttpOnly Secure cookie, HTTPS, narrow SameSite, origin/CSRF protection for mutation, CSP, no framing, short/rotated sessions, idle timeout, login rate limits and server-side revocation. Sensitive operations require confirmation, audit log and **WebAuthn passkey user-verification step-up** (Face ID / Touch ID / Windows Hello / device PIN as supported), plus server-side operation authorization.
8. **Do not touch main or deploy** for this initiative until independent phase acceptance and explicitly planned release. No new Cloud / MCP integration may have admin write privileges by default.

## Verified repository sources (Phase 0)

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

## Architecture

```text
Telegram Bot Admin --> Existing Telegram Admin Mini App (/admin.html)
                                      | verified Telegram initData
Browser / installable PWA --> /admin-pwa/ --> Browser admin login & secure cookie
                                      | shared admin actor + permission guard
                                      v
                           Admin query / command services
                                      |
                       Existing analytics, billing, users, feedback
                                      |
                                  PostgreSQL
                                      |
                         read-only analytics / feedback API
                                      |
                          export JSON/CSV --> AI use by file
                                      |
                       later: scoped external MCP gateway
```

Browser admin login MVP: one-time Telegram Bot approval challenge. Server generates strong random, short-lived login challenge bound to the browser session and stores **hashed** challenge, expiry, attempt budget and used state. User opens a Telegram deep link and confirms on the authorized Bot account; server verifies the authenticated Telegram update, matching allowlisted `ADMIN_IDS`, and atomically marks the challenge approved. Same browser polls status then exchanges **once** for a short-lived cookie session. Do not mint tokens in Telegram messages or callback URLs. Explicitly test account confusion, replay, cross-browser challenge theft, timeout, race, and denied admin. Consider Google/Apple **later** only with verified provider identity explicitly linked to an admin identity; an email match is never sufficient.

API layering: dedicated routes `/api/admin-pwa/auth/*` for browser sign-in/out/status; admin data endpoints use a common service and guard that accepts **verified** Telegram transport OR verified PWA session, with explicit route-specific CSRF checks on cookie-authenticated mutations. Prefer new `/api/admin/v1/*` projection routes over broad mechanical edits of every `/api/admin-miniapp/*` handler. Existing Telegram endpoints must stay backward-compatible. Never accept an arbitrary user ID from a client to establish admin privileges.

## Implementation phases

### Phase 0 — Audit and contract (current)
- [x] Identify current branch, Telegram admin authorization path, admin APIs, statistics sources and feedback persistence gaps.
- [x] Record design reference and non-negotiable Telegram/backward-compatibility/security constraints.
- [ ] Map all existing admin endpoints into read-only vs mutation vs dangerous operations, with response schema, source, and authorization contract.
- [ ] Capture current HTML demo V10 as a **read-only design reference** and define individual components; do not copy all inline demo logic.
**Acceptance:** reviewed API inventory, auth threat model, data dictionary and initial regression list. No production change.

### Phase 1 — Secure browser admin sign-in (highest priority)
- Implement `/admin-pwa/` entry in a separate UI path with unauthenticated sign-in screen.
- Implement Telegram Bot confirmation challenge, server-stored browser session, logout/revocation, idle/absolute expiration, CSRF, origin and no-store response headers.
- Author a reusable verified-admin context across both transports; keep `_admin_miniapp_user_id` and Telegram access unaffected.
- First secure read endpoint: `GET /api/admin/v1/me`; then a light `GET /api/admin/v1/summary`.
**Acceptance:** valid admin only; forged/stale initData, non-admin, missing/expired/replayed cookie and cross-origin mutation are rejected. Telegram Mini App regression passes.

### Phase 1B — WebAuthn passkeys for high-risk action confirmation
- Enrollment: only after verified admin identity and first successful Telegram Bot-approved linkage (a linked Google account may be used for later browser sign-ins). Store credential ID, public key, signature counter/backup flags, owning canonical admin identity, registered timestamp and revocation status. Do not store face/fingerprint or platform biometric data.
- High-risk operations (payment approval/rejection, granting paid access, account delete/block, bulk messaging, changing prices, payout or sensitive settings) require a fresh WebAuthn assertion with `userVerification="required"`, as supported by the authenticator. This invokes **Face ID on compatible iPhones**, Touch ID where available, Windows Hello on Windows, and may fall back to device PIN/passcode. Do **not** label WebAuthn as Face-ID-only or try to read biometrics from JavaScript.
- Server generates a one-use short-lived challenge tied to the active session **and canonical operation parameters** (actor, action, target, amount/plan/decision, request payload digest). Verify challenge, RP ID, origin, signature, user-verification flag, credential ownership, expiry and replay protection **inside the same guarded command authorization path**; do not treat a prior generic step-up as approval to perform a different transfer, deletion or payment decision.
- Show a human-readable transaction summary immediately before verification and require explicit final confirmation. All sensitive commands keep existing server validation, permission guard, idempotency and immutable audit logs.
- Do not prompt for biometric verification for every statistics page or safe read-only navigation. Standard signed-in session remains usable for normal browsing.
- Recovery: permit revocation/re-enrollment only through a separate, robust, audited recovery process; support a second passkey/security key registered in advance. Loss of Face ID / device / passkey must not create a bypass via mere email ownership or unverified Telegram request.
- PWA requirements: HTTPS with consistent configured RP ID (production/admin domain), real browser WebAuthn support detection, fallback messaging for unsupported platforms. Never cache authenticator assertions, cookies, secrets or sensitive data in a service worker.
**Acceptance:** two different admins' credentials cannot be substituted; replay, wrong origin/RP ID, absent user verification, changed transaction payload, expired or missing challenge and revoked credential fail closed. iPhone Safari/Add-to-Home-Screen, macOS Touch ID, Windows Hello and Android credential flows are manually tested as applicable, with no guarantee of Face-ID-only availability.

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
- Dangerous commands require explicit confirmation, **transaction-bound WebAuthn passkey step-up** under Phase 1B, idempotency keys where relevant and elevated authorization; demo buttons must never silently succeed.
**Acceptance:** same backend outcomes for Telegram and PWA, regression tests for approvals/rejections and access grants, no double writes.

### Phase 5 — Unified durable feedback and notifications
- Add a canonical inbox event/triage projection for (a) bot feedback, (b) release feedback responses, (c) Android/native bug reports, (d) administrator/system alerts.
- Persist previously ephemeral bug submissions, with source, canonical actor, source ID, event time, platform, app version, language, category, severity, lifecycle status and attachment reference.
- Deduplicate events, retain original source records and Telegram notification delivery. Protect attachments via permission-checked endpoints; sensitive payloads stay out of generic analytics/export.
- UI: header bell unread count, critical/urgent section, collapsed filter, search, read / assigned / resolved states, links to the user's canonical detail.
**Acceptance:** each source arrives exactly once; critical alerts first; missing media, no Telegram ID, failed delivery, pagination and restricted attachment tests.

### Phase 6 — AI / Cloud data access (read-only first)
**Quickest path:** authenticated, admin-only JSON + CSV exports from the same trusted analytics/feedback query layer, bounded date ranges, audit logs, sanitized defaults. ChatGPT or local tools can work from a downloaded export without database credentials.

**Later:** dedicated HTTPS MCP server (remote Cloud/ChatGPT) and/or local stdio MCP bridge pointing to the same read-only API. Candidate tools:
- `get_metrics_dictionary`
- `get_statistics(period, platform, dimensions)`
- `compare_platforms(period)`
- `get_conversion_funnel(period)`
- `get_feedback_summary(period, category, platform, severity)`
- `list_feedback(period, status, limit, cursor)` (redacted by default)
- `get_feedback_detail(id)` (explicitly scoped to admin with access)
- `export_analysis_data(period, kind)`

Use separately issued, revocable short-lived machine credentials with **read scopes**, audience binding, throttling, row and date limits, data minimization, access auditing and explicit PII opt-in. Do not expose write, billing, delete, broadcast or account-control endpoints to AI agents. GitHub connector alone can inspect code, **not runtime production database statistics**. Local workspace access to a staging clone is not production access.

**Acceptance:** read-only AI client can answer a conversion drop or frequent complaint question with consistent sources and field definitions, without PII leakage or mutation rights.

### Phase 7 — Staging, rollout, regression and monitoring
- Separate staging DB/credentials and test accounts; no production payment approvals, notifications or broadcasts during tests.
- CI: Python auth/unit tests; Telegram Mini App unchanged; API contract; security; browser E2E desktop/mobile; offline/installation; seeded feedback and payment state.
- Deploy under explicit feature flag / isolated route; verify logs, page-cache headers, rate limits, origin/CSP, and rollback path.
- Promote only after manual admin acceptance and rollback verification.

## Ordered first tasks

1. Finish Phase 0 endpoint inventory and `read/write/danger` matrix.
2. Implement and test Phase 1 browser Bot challenge + cookie guard behind an explicit disabled-by-default feature flag.
3. Implement the no-data PWA login shell and first secure `me/summary` endpoint.
4. Attach V10 UI to real server projections section by section, starting with read-only overview.
5. Complete feedback persistence and AI data export *before* promising a complete unified inbox or ChatGPT live telemetry.

## Explicit open questions to resolve from code before implementing Phase 1

- Which deployment host/origin and bot username are canonical in staging, and what callback/deep-link contract does the existing bot router already support?
- How should a browser-authenticated admin actor map to canonical user ID while existing audit `created_by_telegram_id` fields remain backwards compatible?
- How are Android bug-report attachments stored and retained, and which current app variants generate them?
- Which platform events are authoritative for Mac vs Windows, and which prospective iPhone PWA events have no instrumentation yet?
- Which admin services unexpectedly commit on read? Extract read-only projections without importing these side effects into AI access.

## Test and release notes

This document records source-code observations; it is not evidence of an active PWA, deployment, user-session security testing, database migration, or production end-to-end QA. No production endpoint is enabled by this planning change.
