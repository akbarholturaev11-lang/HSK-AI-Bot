# Smart preference API contract

This is the P1 task 2.3 interface; execution evidence belongs only to the
[Master Plan](SMART_REMINDER_MASTER_PLAN.md). No client settings screen uses it
yet. `dispatch_allowed` and channel `eligible` remain false;
`legacy_delivery_controlled` remains false until task 2.4's sender/invalidation
integration. Persisting Smart OFF alone does not establish old-client fencing.

## Authentication and transactions

- Telegram: GET/PATCH `/api/v3/smart-reminder/preferences` requires
  `X-Telegram-Init-Data`, with the existing HMAC verifier, a positive integer
  transport ID and authentication age at most 86400 seconds (60-second future
  skew). Proof is accepted only in the header; duplicate proof fields/headers,
  mixed bearer proof and unknown accounts are denied.
- Android: GET/PATCH `/api/v3/android/smart-reminder/preferences` requires the
  existing bearer token and an owning Android session/device. Desktop bearer
  contexts cannot use this adapter. No cookies, query parameters or body fields
  choose canonical owner, Telegram ID or device.
- Both adapters recheck fresh ownership, session/device revocation/expiry,
  canonical account block/status and submitted deletion. All responses are
  `no-store`. The service locks user first, then preferences; the adapter owns
  commit/rollback. It never changes payment/access/course results or sends.

## Read

GET is non-persisting. Before Smart state exists it projects genuine legacy
Telegram ON/time and unknown Android evidence; it creates no profile, consent
or enrollment. Afterwards it reads stored source consent with current endpoint
availability. Response fields include `revision`, `migration_version`, nullable
explicit `master_enabled`, consent-derived `effective_master_enabled`,
time/channel modes and values, cold-start legacy time/offset, quiet/pause,
and channel consent/availability. Android exposes its authenticated device's
consent and known study-OS permission separately, without listing device IDs.
`effective_master_enabled` describes consent configuration, **not** delivery
eligibility or an OS permission. Explicit master ON grants no channel consent.

## Mutation

PATCH requires JSON of at most 4096 bytes, no duplicate/unknown fields, a
canonical lowercase UUID `request_id`, integer `expected_revision` from GET,
and at least one change. Booleans must be JSON booleans; null/string/numeric
booleans are rejected. A successful initial import plus explicit change is one
committed revision (0 → 1). Each new mutation advances one revision; exact retry
never advances it. OFF also advances the grant epoch.

| Optional change | Contract |
| --- | --- |
| `master_enabled` | Explicit global boolean; ON retains endpoint OFF/unknown. |
| `study_enabled` | Explicit consent for this authenticated Android device or Telegram channel only; no OS/protocol capability is inferred. |
| `time_mode` | `auto` or `manual_locked`; manual requires a valid `manual_time_local` and `timezone_name` in the resulting state. Auto clears the manual time. |
| `manual_time_local` | `HH:MM`, requires manual mode. Null is allowed only when clearing the lock. |
| `timezone_name` | Known IANA zone, non-null. Legacy coarse offset is never converted into an invented zone. |
| `channel_mode` | `auto` or `manual_locked`; manual requires `preferred_channel` (`telegram`/`android`). Auto clears that value. |
| `quiet_start`, `quiet_end` | Both supplied, both valid `HH:MM` or both null to clear. Equal/half-defined endpoints are rejected; no preset night rule. |
| `pause_until` | Timezone-aware ISO-8601 timestamp or null to clear; stored in UTC. |

PATCH returns only `{ok, request_id, applied_revision, dispatch_allowed}`.
Clients GET again for current settings. The receipt stores canonical request
SHA-256, actor binding and applied revision, never raw request/proof or a settings
snapshot. Same actor/UUID/body returns the original acknowledgement, even after
a later OFF; changed content or actor conflicts and cannot restore old state.
A fresh intentional endpoint ON can resolve its own legacy mirror, while
independent unknown/OFF sources remain conservative. Master ON never rewrites
channel consent or capability.

## Errors and bot compatibility

- 401: missing/invalid/stale/ambiguous proof, revoked/expired/foreign session.
- 403: wrong native platform, blocked or unknown account status.
- 404: verified proof has no canonical account.
- 409: stale revision (`revision` supplies the current revision for a fresh
  GET), reused request identity, pending deletion or exhausted epoch.
- 413/415/422: oversized body, wrong media type or invalid typed/merged values.
- 503: bounded-state inventory refusal or unavailable storage; no credentials,
  raw SQL or provider error details are returned.

For existing Smart accounts, reminder picker callbacks carry a server-FSM-bound
owner/revision/nonce and use the same CAS service. Old/unbound/stale callbacks,
current global OFF and explicit manual time locks refuse mutation. Exact
callback retries cannot replay legacy ON. Cancel clears only setup/interaction,
without changing consent/revision. Non-Smart callback data and visible UZ/RU/TJ
labels stay compatible. Typed legacy time input and other legacy writers remain
task 2.4 integration work; they receive no Smart authority here.

Migration 0134 adds only minimal user-owned mutation receipts. Account purge
removes them; application rollback must retain Smart state and migration
knowledge. Empty receipt-table downgrade is supported; populated downgrade
refuses before dropping it. D13's numeric transactional-receipt retention policy
is still unresolved; this API invents no raw behavior retention period.
