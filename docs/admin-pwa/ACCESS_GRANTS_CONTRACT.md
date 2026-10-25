# First-party manual subscription grants

Implemented on the feature branch, default-OFF with Admin PWA. No external MCP
tool/scope, legacy Telegram guard or paid entitlement policy changes.

## Exact confirmation and transaction

`POST /api/admin/v1/users/prepare-access` takes only canonical `user_id` and
strict integer `duration_days` (1–365 for Admin PWA, owner decision).
Both prepare and execute validate the bound independently of frontend controls.
The existing shared/Telegram administrative duration helper is unchanged; this
scoped PWA policy does not silently alter legacy admin behavior.
The current allowlisted WebAuthn cookie is mandatory. A single unlocked User
read prepares the snapshot; no aggregate query, background polling or cache.

The returned `users.grant_access` operation binds the exact canonical target,
days, current status/payment/start/end/preview fields and paid-active predicate.
The V10 profile drawer limits days to 365 and displays the target, days and existing expiry before a
separate explicit passkey confirmation. Five canonical UZ/RU/TJ labels use the
existing generator. Repo hsk-ai-ui and webapp-testing skills were read/applied;
the new confirmation reuses existing V10 form/drawer/focus/cancel patterns.

`POST /api/admin/v1/users/grant-access` accepts that validated payload and one
verified, session/credential/action/target/hash-bound step-up ID. The same DB
transaction consumes it, locks/refreshes the target, rechecks current actor,
flag and proof/session expiry after lock waits, compares the snapshot, calls
`SubscriptionService.grant_manual_paid_access` and inserts the audit. PostgreSQL
lock/statement limits are 5/8 seconds. Any failure rolls back all three effects.
Competing proofs for one snapshot apply at most once. A paid term expiring
between confirmation and execution changes the predicate and requires reread.

The shared service extends an existing approved unexpired term; otherwise it
starts from current server time. It creates no Payment/revenue/AI budget and
does not replenish a spent receipt preview. Target namespace never falls back
to a numerically equal Telegram ID. Blocked targets require a separately
authorized unblock; this grant cannot silently unblock an account.

Current canonical HTTPS/Origin/Fetch Metadata/JSON-body limits and no-store
headers apply. No bearer, initData substitution, client-selected fields, generic
mutation executor or automatic retry. Cancellation/stale drawer guards follow
the existing passkey pattern. An uncertain lost response opens the profile for
reread; only committed success displays the granted expiry. No claim of outbound
notification delivery is made; this increment adds no external message sender.

## Audit and migration

0126 follows 0125 and creates `admin_pwa_command_audit`: unique step-up ID,
canonical actor/target, action/target, exact payload hash, sanitized before/after
access fields and applied result. No password, cookie, credential key, email,
feedback, bank data or receipt is stored. Identity/session FKs do not cascade
away command evidence. Nonempty downgrade refuses destruction. The standalone
empty-QA initializer defers this table to its real migration and pins 0126;
no live schema was changed. Scoped CI checks 0110–0126, not the broken legacy
0011 cold-start path.

Unit/ASGI and real disposable PostgreSQL tests cover signatures, replay/tamper,
current rights/revocation, native targets, paid extension, preview/budget rules,
atomic audit rollback, competing grants, expiry while waiting on target lock,
and real upgrade/nonempty downgrade protection. Browser QA covers UZ/RU/TJ
1440/390 confirmation/cancel, real virtual WebAuthn, changed state and committed
lost-response without resend. Physical passkey/device acceptance stays separate.
