# Telegram study ownership and attempt boundary

Decisions and acceptance evidence belong to the [Master Plan](SMART_REMINDER_MASTER_PLAN.md).
This is the internal protocol/rollback contract for task 4.1. It adds no public
operator endpoint, scheduler, producer, real transport, template or canary.

## Sticky ownership, separate from consent

`0135_smart_reminder_routing` adds one canonical User-owned row: `held` or
`telegram`, monotonic generation, admission revision/epoch, opaque transport
and Android-inventory bindings, hold/review instants and an evidence SHA-256.
There is no raw device inventory, proof body, credential or message content in
this row. A populated downgrade refuses removal; canonical purge explicitly
removes only that owner's routing state. The empty-QA initializer defers this
table to its actual migration.

`legacy_send_veto` suppresses the old Telegram course sender and server Android
study hints for any routing row. Expired proof, a paused new dispatcher or an
invalid cohort never restores legacy sending. `legacy_veto` retains the prior
configuration/OFF checks: legitimate time choices and Android preference mirrors
are not silently rewritten by routing ownership. Weekly progress, motivation,
account/payment notices and their fallback remain on their own existing paths.

No routing row follows from reading preferences, enabling a channel, a widget,
device/version metadata or missing/revoked tokens. No real accounts are enrolled
by this code. Unknown offline Android senders remain a cutover blocker; this
server protocol cannot prove global physical exactly-once delivery.

## Privileged two-step admission

`SmartReminderRoutingService` owns short User-first transactions. Its callers
must already have trusted operator authorization and a real canonical Telegram
actor; it is not a learner/client API.

1. Deploy the guard to **every** relevant backend replica. Call `hold` with the
   exact current generation (0 for absent). It commits sticky suppression,
   increments the generation and invalidates unattempted work without erasing
   day ownership or ambiguous external attempts. It does not change consent.
2. Only after that hold, independently verify old server IO has drained, old
   day/unknown delivery outcomes are reconciled, and all other autonomous study
   senders are safely fenced through an explicit review deadline. An old legacy
   call already past its veto can still be in IO; neither a delay, timeout,
   revoked row nor missing inventory proves it did not send. If uncertain,
   **leave the account held**. This requires real cutover/staging/install proof
   before activation; no live verification is performed by these helpers.
3. Submit `RoutingReview(version=1)` with canonical user, exact held generation,
   aware `verified_at`/`verified_until`, lowercase 64-character evidence SHA-256,
   and three exact True booleans: `legacy_quiesced`,
   `legacy_outcomes_reconciled`, `other_study_fenced`. These are privileged
   attestations about reviewed evidence, not an algorithm proving those facts.
   Their verified instant must follow the hold and not be future; expiry must
   be after now. Current admission revision/epoch, real Telegram identity and
   consent/reachability must still match. A stale review conflicts.

A bounded digest binds canonical Android device/version/revocation, owned
session metadata, study flags and capability generation/observation windows.
It selects no FCM/refresh credential. Overflow is unknown, never fenced. Changes
after hold/review—including a new installation/session, study mirror ON or row
removal—refuse new authority. Existing active Android rows additionally need
fresh protocol-1 autonomous-disabled proof through the review deadline; this
structural requirement is not installed-build acceptance. Historical/revoked
records remain in the digest and need the external fencing review; revocation
is never itself that proof. Account-notice permission is excluded from the
study digest and cannot become study consent.

Active proof records admission revision/epoch for audit; later legitimate
settings changes use current P1 state and frozen job revision/epoch, without
turning a routing row into consent. Every activation/dispatch rechecks current
owner, real transport, block/status, deletion, consent, proof and inventory.
Known legacy provider timestamps also retain their current/overlapping coarse
day ownership at promotion and before IO. An empty legacy timestamp is not
negative delivery proof; reconciliation is still mandatory.

## Internal reservation, lease and transport

`SmartReminderTelegramService` requires all of:

- `SMART_REMINDER_TELEGRAM_ENABLED` is exactly True (default False).
- Explicit cadence calibration; no production numeric configuration is supplied.
- A separately registered authoritative learning-coverage reader. None is
  installed. The incomplete legacy reader cannot manufacture negative coverage.
- Fresh reviewed cohort, actual permitted Telegram and the normal P1/3.1/3.2
  D1/goal/course/access/quiet/pause/budget checks.

Disabled or missing calibration/coverage returns before SQL/provider work.
Protocol tests inject an explicitly complete synthetic learning feed and fake
Bot. This is not evidence of a production outcome feed or experiment readiness.
The missing reviewed numeric/outcome inputs must be resolved before any 4.3
activation; flipping the switch alone is insufficient. D05 category coordination
remains a diagnostic 3.4 layer, not a wired production category producer. Its
reviewed values and actual coordinator/renderer integration are also activation
prerequisites; this attempt boundary is not a complete live orchestrator.

`prepare` adopts only an unleased, unattempted 3.3 `shadow` reservation with
the same frozen canonical account/day/UTC window. It never creates a parallel
intent, resets a completed/cancelled row or takes another policy's ownership.
The Telegram policy version includes a digest of the explicit calibration;
another policy/calibration cannot claim its work. Early planning and due
processing remain distinct; no producer is wired here.

`claim` commits a finite opaque token lease and one deterministic initial
Telegram attempt in `prepared`. Current proof/consent, preference revision/epoch,
goal, target, D1, history, expiry and explicit cadence are rechecked. A prepared
attempt can recover after lease expiry with a new token; the stale token fails.
Hold cancels prepared work and changes routing generation, so an old lease
cannot survive reactivation. There is no Android destination or alternate.

`dispatch` repeats the checks and conditionally commits `in_flight`/`started_at`
before invoking an injected trusted transport **outside SQL**. The ephemeral
envelope contains only selected real Telegram destination and current safe
course/lesson identity. No production callback is registered. Task 4.2 adds the dormant
`smart_reminder_telegram_content.py` adapter: immediately after fresh target/access
policy, render current account language and the existing DB template snapshot
under User, then re-evaluate current policy and the finite lease before the in-flight marker. The
injected Bot helper receives this content only after SQL commits.

The canonical UZ/RU/TJ `smart_study` default uses only the validated lesson
number. Existing DB custom text, per-language fallback, disabled state and
owned photo/video keep precedence. The sixth template uses the existing
protected editor/Save/CAS/WebAuthn path; it is not a sixth legacy motivation
trigger and enabling its template never starts dispatch. Unsafe fields, provider
UTF-16 length overflow, unowned media paths or malformed configured destinations
cancel before provider IO. Missing owned media falls back to the already
rendered text; a media provider exception never tries another transport call.
The shared URL helper targets the existing course page with normal signed
identity, course/foundation/sequence/access guards on open. No credential,
private lesson data or autostart is added to the URL.

Only a positive provider result records the canonical owner/job-deduplicated
inbox item in the same outcome transaction. Its template key and scalar lesson
argument support later language changes using current DB/default copy; stored
sent text remains historical. Unknown/exception results create no success item.
Inbox commit rollback leaves the durable in-flight attempt, with no retry.
`CourseNotificationService` now retains `template_service` arguments as well as
legacy `template`, and resolves display copy separately without dirtying ORM
JSON. Broken/disabled later translations fall back to stored text. No inbox
read creates a study job, consent, provider receipt or learning evidence.

A trusted positive Telegram `message_id` records `provider_accepted`, not
shown/read/learned. Exception, uncertain return, cancellation/process death or
acceptance-update rollback leaves `unknown` or a durable in-flight marker.
Every externally started attempt refuses retry/reclaim/alternate, including
after lease expiry; the unique day/attempt identities remain. A start-transaction
failure returns no transport authority. A separate DB read sees the committed
in-flight marker before the fake transport executes in tests.

OFF/hold/learning committed before the in-flight authorization boundary wins.
OFF or block after that boundary cannot recall already-authorized provider IO;
record its actual outcome without minting another permission or erasing
uncertainty. Accepted transport updates the historical provider-return clock,
not a display/goal/learning field. Shadow workers ignore this policy version.

## Failure and rollback

Use the switch to stop new authorization, and hold a specific cohort to revoke
prepared work. Keep routing markers, P1 OFF/revision/epochs, schema and all frozen
day/attempt ownership. There is no automatic release-to-legacy API. Before any
future legacy resume, reconcile provider uncertainty, overlapping day ownership,
old/new replica versions, current consent and installed sender fencing. A
pre-guard rollback binary or dropping routing rows can restore a second sender
and is unsafe. Review expiry never authorizes this action.

Internal refusals include `routing_generation_conflict`, `routing_review_stale`,
`telegram_cohort_unavailable`, `telegram_study_unavailable`, disabled/missing-feed
reasons, `telegram_day_not_adoptable`, `foreign_job_policy`, lease/not-due/expiry
reasons, D1/current-policy reasons, `legacy_study_already_attempted`,
`telegram_attempt_not_replayable` and `telegram_unknown`. These are diagnostic
codes, not user-visible notification copy. Synthetic protocol/SQL tests do not
establish real provider, installed-client, staging or canary acceptance.
