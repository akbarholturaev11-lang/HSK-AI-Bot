# Smart preference API contract

This is the P1 task 2.3 interface; execution evidence belongs only to the
[Master Plan](SMART_REMINDER_MASTER_PLAN.md). No client settings screen uses it
yet. `dispatch_allowed` and channel `eligible` remain false;
Server OFF/lifecycle guards are implemented, but `legacy_delivery_controlled`
remains false until compatible-client/cutover acceptance. Backend suppression
does not establish control of unknown offline Android installations.

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
labels stay compatible. Typed time input uses the same server revision fence; rejection clears setup
and returns the existing cancellation message instead of a saved-ON confirmation.
Legacy repository/device-sync guards cannot clear OFF or advance Smart consent.
Old Android sync still returns its supported response and updates independent
zone/account-notice fields; it cannot set the study flag ON under a veto.

Migration 0134 adds only minimal user-owned mutation receipts. Account purge
removes them; application rollback must retain Smart state and migration
knowledge. Empty receipt-table downgrade is supported; populated downgrade
refuses before dropping it. D13's numeric transactional-receipt retention policy
is still unresolved; this API invents no raw behavior retention period.

## OFF, lifecycle and rollback

- Global OFF advances revision/epoch once, disables existing Telegram-course and
  Android study flags and invalidates pending Smart authorizations atomically.
  Endpoint OFF disables only that endpoint's legacy flag; the account epoch
  conservatively invalidates all old planning snapshots. Time, motivation,
  weekly summary, app-update and account/payment notice settings are independent.
- Active leases are cleared, prepared attempts are cancelled and unattempted
  active jobs are cancelled. Account/day and attempt keys remain reserved.
  Accepted, in-flight, posted, shown and unknown outcomes are never relabelled as
  non-display; there is no timeout-based alternative send or physical recall.
- Logout/device revoke, first detected refresh-token reuse, explicit push
  unregister and identity-disconnect session revocation invalidate existing
  state without enrolling a non-Smart account or changing durable consent.
  Affected capability observations are removed and must be observed again;
  identity disconnect conservatively removes the account's observations while
  preserving its permitted current login. Successful refresh does not opt out.
- First submitted deletion invalidates before the existing commit. Repeated
  confirmation is idempotent, and canonical purge still removes all owned rows.
- Legacy server study paths recheck current block/deletion, global/endpoint OFF
  and known Android study-OS denial. These are vetoes on the existing path,
  independent of new-dispatch flags. Already-admitted old provider operations
  and uncontrolled offline posts remain outside a truthful recall guarantee.
  P2/P4 must establish the durable authorization/provider boundary before
  enabling new dispatch.

Feature rollback must retain these mandatory vetoes, epochs and reviewed schema
knowledge. A pre-guard server binary is not a safe rollback image for Smart
accounts. Disabling the new dispatcher must never bypass legacy OFF guards.
Minimal preferences/consent/receipt state survives feature rollback until
canonical deletion; finite job/attempt expiry stops authorization, not evidence
retention. Capability observations are removed at lifecycle invalidation. D21 approves future Smart analysis raw-detail retention of 90 days and anonymous
aggregate retention of 12 months. Job/attempt/consent/retry-proof retention is
separate and still needs class-specific decisions. No cleanup or additional
behavioral history is implemented by this API.

## P4 task 5.1a: Android capability observation

GET/PATCH `/api/v3/android/smart-reminder/capability` uses the same native-only
bearer authentication, current User/device/session/deletion rechecks, bounded
strict JSON parsing and no-store responses. There is one existing capability
row per authenticated device; the client cannot supply owner, device/session,
observation timestamps, expiry, cohort generation or posting authority.

GET creates nothing. Missing state is generation/protocol `0`, unknown nullable
flags, no timestamps and `fresh=false`. The response always includes
`observation_only=true` and `dispatch_allowed=false`. `fresh` means the
observation is within its auth-bounded interval, not that a device is eligible
for new study delivery. No device IDs or credentials are returned.

PATCH requires all four fields:

| Field | Meaning |
| --- | --- |
| `expected_generation` | Strict nonnegative integer from this device's GET. CAS observation counter; distinct from preference revision, grant epoch and operator cohort generation. |
| `protocol_version` | Strict integer 0 (unknown/unsupported) or 1 (reported contract version); never proves a signed build or historical-client fencing. |
| `autonomous_study_disabled` | JSON boolean or null reporting this install's current state; not a trusted fleet attestation. |
| `study_notifications_allowed` | JSON boolean or null reporting study-channel capability separately from account notices and study consent. |

The server increments observation generation and sets `observed_at` and
`expires_at`; expiry is the earlier of the verified access-bearer deadline and
current native-session deadline. No arbitrary product TTL is introduced.
Stale/saturated generation returns `409 smart_capability_generation_conflict`.
An unknown permission cannot replace a known denial (`409
smart_capability_denial_unresolved`); a fresh explicit boolean observation is
required. Expiry does not erase stored denial. On a lost acknowledgement,
read GET and reconcile; there is no blind write retry or posting grant to replay.

Losing a protocol/autonomous-disable/study-permission prerequisite invalidates
pending authority through the existing User-first lifecycle service. Preference
revision/grant epoch may advance, so clients refresh preferences before a later
intent CAS. Explicit master/channel ON/OFF and native account-notice settings
are not rewritten. Already externalized/unknown attempts keep their truth;
invalidation grants no alternate send. A positive observation cannot restore
OFF or enroll a cohort. Removing this adapter for rollback must retain the
stored denial, existing P1 guards and schema knowledge.

No Android client invokes this new adapter yet. Selected-job due/claim/receipt
routes and session/install-bound posting grants are still task 5.1b; this
observation row alone must never be used as authorization to post. Existing
account-notice `/notices/{id}/ack` and its fallback remain independent.
