# Admin PWA — final product and acceptance contract (temporary)

> **SCOPE: HSK AI ADMIN PWA ONLY** — temporary task file. Work branch: `feat/admin-pwa-minimal-inbox-passkey-20261025`, PR #204.
> Not a repository-wide policy. Does not modify or supersede root `AGENTS.md` / `AI_RULES.md` / `PROJECT_MEMORY.md`.
> All development and progress records for this task remain under `docs/admin-pwa/`.


**Final product:** Secure, installable, fully functional, **real-data** HSK AI Admin PWA at `https://hskai.app/admin`, with unchanged Telegram Admin Mini App and shared business rules, plus a controlled read-only path for AI-driven analytics/feedback analysis.

This checklist describes full product acceptance, not a list of wholly missing
code. Read [current handoff](MCP_NEXT_CHAT_HANDOFF.md) for implemented increments
and their evidence; uncompleted staging/device/provider acceptance remains open.
The current branch's external MCP permission is statistics-only. Keep all three
feature defaults false; no main promotion or deployment is authorized here.

## Required end-user result

### A. Identity and admin access
- [ ] Existing Telegram Admin Mini App works identically at its present endpoint with signed initData; no admin guard/flow regression.
- [ ] First standalone Admin PWA onboarding: verified Google OAuth **AND** one-time Telegram approval by an allowlisted admin → canonical identity binding → passkey enrollment.
- [ ] Returning PWA login: require a fresh **registered passkey** on each launch/resume after revoking the old browser session, with no mandatory repeated Google/Telegram; fail closed when cleanup is unavailable. Google or audited Telegram recovery is secondary.
- [ ] WebAuthn verification is implemented **server-side** using correct origin `https://hskai.app`, RP ID `hskai.app`, fresh one-use challenges, verified credential ID/public key, user verification and admin allowlist re-checks.
- [ ] Face ID / Touch ID / Windows Hello / PIN fallback explained truthfully and manually checked on available devices; inability to force Face-ID-only is documented.
- [ ] Secure session expiry/revocation, HttpOnly Secure cookies, CSRF/origin protection, same-origin policy and accessible sign-in/error/recovery UI.

### B. Installable PWA and V10 UX
- [ ] Existing HSK AI public site continues to work; PWA published only under isolated admin route and install scope.
- [ ] V10 visual design integrated as maintained frontend code and reviewed, **without** shipping synthetic users, data arrays or fake action outcomes.
- [ ] Responsive on installed iPhone Home Screen PWA, mobile browser, Mac and Windows; navigation, collapsed filters and single top toolbar work.
- [ ] Installation manifest/icons/versioning, shell-only offline behavior, proper update UI; **zero** private admin data/API credentials cached by service worker.
- [ ] Clear loading, no-data, offline, expired-session, access-denied and error/retry states; no duplicate meaningless prose.
- [ ] New permanent UI strings sourced centrally for UZ/TJ/RU.

### C. Real statistics and users

Owner clarification (2026-10-24): reuse each aggregate snapshot for 24 hours
from `generated_at`, then refresh on first authorized demand. No fixed-time
cron or unused-variant scans. Keep original refresh time visible; current
profiles/billing/receipts/access/commands and auth/revoke/audit/quotas stay live.
Use private server-side Redis and the optional private R2 aggregate mirror;
bounded outage fallback is daily per worker, not a cluster-wide once-only
guarantee. R2 adapter code exists and remains default OFF. This preserves
browser/SW no-store and real-data/metric-definition requirements. Details:
[read projections](READ_PROJECTIONS.md).

- [ ] Daily aggregate snapshots expose original generation/expiry time; healthy-worker refreshes are coordinated and outage/restart/failure behavior is verified without caching current permissions or billing decisions.
- [ ] Real overall dashboard: defined account totals, activity, conversion, payments, revenue, AI spend, course engagement with date source and last-refresh metadata.
- [ ] Period options: 7 days, 30 days and all-time. Platform options: overall, Telegram Mini App, Android, Mac, Windows; future iPhone PWA is marked unavailable until instrumented.
- [ ] No platform-user double counting when computing overall, no misleading site visits / installs / unique account substitutions, no mixed-currency totals.
- [ ] Real user search/profile and appropriate billing/entitlement, referral, devices and feedback details, with pagination, authorization and bounded queries.
- [ ] All fields traceable to existing service/API and tested against fixture results, not inferred from demo.

### D. Universal feedback and notifications
- [ ] Durable ingest/read model includes Telegram bot feedback, release ratings/comments, native Android bug reports and admin/system alerts (where those events exist).
- [ ] New bug reports stored durably **before** or independently of Telegram notification delivery, without breaking existing Android report API semantics.
- [ ] Severity/priority, read/new, assigned, resolved, platform/source/time filters and search; critical unresolved notices are prominent without clutter.
- [ ] Events deduplicated, linked to canonical accounts where available, secure attachment access, retention/privacy rules and proper empty/missing-history behavior.
- [ ] If previously unpersisted legacy reports are not recoverable, show history boundary rather than falsely claim complete past data.

### E. Real management actions
- [ ] Course, subscription, HSK 3.0 unlock, access grants, payments, marketing, settings and other scoped admin operations call shared validated backend commands; Telegram UI still works.
- [ ] High-risk actions are disabled in PWA until **fresh, transaction-bound WebAuthn step-up** exists and is tested (exact action/target/payload, expiry, signature, replay/CSRF, confirmation and audit).
- [ ] Financial approvals and rejections cannot double-process; canonical account identity and existing payment-preview/Pro business rules preserved.

Implemented management code now includes signed direct/self-test and bounded
text broadcasts, durable pre-provider claims, explicit cancellation and
pending-only signed resume. Owned payout proof/completion and durable recipient notice also exist, using
the owner-requested single payout window. Text-only campaign drafts can now be
created signed and paused. Desktop-promo JPEG/PNG/WebP media can now be added,
replaced or removed with one exact passkey confirmation. Campaign
activation/delivery, feedback/discount campaigns, course-ad media and payment
QR uploads remain code work. Partner application notices are implemented; see
[management contract](MANAGEMENT_COMMANDS_CONTRACT.md).
This paragraph records scope and does not mark the entire acceptance list done.

### F. Cloud/ChatGPT/Local analytics without exposing admin credentials
- [ ] Publish authorized **read-only** metrics dictionary and scoped statistics/feedback query with server-side filtering, pagination and PII-minimization.
- [ ] JSON/CSV export with bounded ranges and source lineage. Useable by local tools or as ChatGPT-uploaded sanitized file.
  Statistics export code/browser QA now exists: see [file contract](READ_PROJECTIONS.md#bounded-first-party-statistics-files-2026-10-24).
  Bounded first-party feedback category JSON/CSV and localized V10 downloads
  also exist; raw feedback text stays private. This is not a full-product
  completion mark.
- [ ] Revocable, audited, scoped MCP uses **only** the approved statistics tool; actual ChatGPT/OAuth/protocol/reconnect acceptance is evidenced. User profiles, raw feedback, payment lists and mutation tools remain excluded from external MCP. Broader sanitized feedback exports are a separate first-party requirement, not permission to expand MCP.
- [ ] An AI agent can explain a platform conversion change and top complaint categories citing datasets/metric definitions, but cannot approve payments, delete accounts, broadcast or execute arbitrary SQL.

### G. Staging, release and operability
- [ ] HTTPS DNS and reverse proxy for `hskai.app` verified; Google redirect registered; WebAuthn origin/RP tested on target hostname; staging auth uses separate isolation.
- [ ] CI/regression for app auth, Telegram unaffected, metrics, user/finance APIs, inbox, PWA UX, installation/offline, CSRF, challenge replay and payload tampering.
- [ ] Physical-device passkey verification on supported phones/desktop browsers where available; explicitly document devices untested.
- [ ] Production feature flag, rollback route, logging, audit, revocation and alerting documented. No unreviewed deploy or push to `main`.
- [ ] Owner reviews completed staging version and authorizes release before promotion.

## Completion evidence to record

For each checkbox, include: the exact code/route or migration, commit SHA, associated test commands/results, whether production/staging was actually exercised, and links/evidence where safe.

**Only mark the project complete when the full product matches this contract.** A partial read-only PWA milestone should be labeled exactly that, not “complete Admin PWA.” If an optional MCP gateway is deferred, disclose its status and keep the independent JSON/CSV AI export requirement.

## Deliberate non-goals

- Do not remove or redesign Telegram Admin Mini App as a side effect.
- Do not turn the entire public HSK AI app into an admin PWA.
- Do not grant admin powers to arbitrary Google users, shared emails or AI agents.
- Do not ship dummy metrics or require the browser to hold DB access keys.
- Do not release directly from a planning document.
