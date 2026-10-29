# Android selected-study protocol v1

Execution evidence is in the [Master Plan](SMART_REMINDER_MASTER_PLAN.md).
This is P4 task 5.1b's dormant backend protocol. The real router constructs a
disabled service. No production job producer, Android admission reader,
authoritative complete-learning reader or enabled delivery factory is wired.
Positive capability, an environment switch, client fields or a pending job
alone cannot activate it. Android trigger integration is implemented within
task 5.2's synthetic/isolated acceptance boundary; signed,
mixed-build, actual fencing and canary acceptance remain tasks 5.3–5.4.

## Android migration observation and triggers

GET `/api/v3/android/smart-reminder/mode` uses the same native authentication,
User-first rechecks and no-store response. It creates nothing and returns only
`ok=true`, integer `version=1`, `dispatch_allowed=false` and a Boolean
`server_claim_required`. An existing sticky routing row or this device's
recorded autonomous-disable observation makes it true, even after observation
expiry. It is neither consent, a cohort attestation nor posting authority.

The client persists true in WidgetStore's current link epoch before reporting
its autonomous sender disabled. False/missing/expired answers cannot undo that
local latch. Unknown mode fails closed; a fresh explicit false allows the old
non-migrated path. Logout/relink clears local account state and requires a new
live observation. A call already beyond its legacy veto still needs actual
hold/drain review; this is not a physical recall guarantee.

New data-only FCM hints use `kind=smart_study_reminder`, `version="1"`, a
canonical lowercase UUID `job_id` and ISO `local_day`. The handler enqueues
unique network-constrained WorkManager work; it does not perform posting IO
inside the FCM callback. Periodic and hinted workers share one bridge and the
same server due/claim identity. A hint cannot select a different due job;
old-day, malformed and legacy study hints never trigger a new Smart job.
Cancel removes both periodic and pending hinted work. Payment/account/update
notice routing is independent.

A per-link durable journal reserves the request before HTTP and records a
possible unknown outcome before OS IO. The current auth generation, epoch,
local OFF, observed completed goal, OS study permission, strict version/types,
job/fence/target binding, day/zone, wall expiry and elapsed-time deadline are
rechecked before notify. A persisted grant is historical evidence and cannot
be replayed. Lost responses, crashes, notify exceptions and receipt failures
never restore the request/day or create another posting attempt. Receipts use
one immutable ID/outcome and retry under the original current link/session,
including after OFF/permission loss. Local logout/relink clears this private
journal; remote deletion follows ordinary auth/session cleanup and cannot
physically erase an offline device. Automatic authority-evidence pruning
remains unspecified.

The native transport explicitly serializes required default fields and rejects
quoted Boolean/integer authority fields. Existing canonical notification copy
and fresh-access open behavior are reused. The adapter makes no claim of
shown/read/learning, actual provider delivery or two-device installed acceptance.

## Authentication and admission

Every route requires the existing Android native bearer. Cookie, query/body
identity, Telegram proof, Desktop sessions and duplicate/mixed proof are
refused. User-first locking rechecks current account/status/submitted deletion,
session/device ownership and revocation/expiry. Responses use `no-store` and
`no-referrer`; failures expose stable codes, not credentials or SQL.

Issuance requires all of the following:

- Current explicit device study consent and no account OFF/manual other-channel
  choice; fresh supported capability with autonomous posting disabled and
  study OS permission allowed. Account-notice permission is independent.
- An already reserved pending job selecting exactly this canonical account
  and device, current policy version, preference revision/grant epoch and frozen
  IANA day/window/course/accessible continuation target.
- Sticky routing quarantine (`held`) followed by a separately privileged
  `AndroidAdmission` for this job/device/session and held generation. The hold
  itself grants nothing. Review binds the current bounded inventory digest,
  explicit drain/outcome/other-sender fencing evidence and validity. New device,
  session, version or capability/inventory drift invalidates the old review.
  A second hold changes generation and revokes the previous proof. No HTTP
  caller can submit these attestations; the production reader is absent.
- Fresh D1/holdout, goal/access/quiet/pause/course/time and cadence checks plus
  trusted complete learning coverage. Existing best-effort history cannot
  prove no learning. Known overlapping legacy Telegram/Android contact vetoes
  issuance. Unknown old/offline installations still require external fencing.

## Routes

### GET `/api/v3/android/smart-reminder/due`

No query parameters. Returns at most one selected pending job with its
`job_id`, `preference_revision`, `grant_epoch` and `capability_generation`.
It is read-only and always has `dispatch_allowed=false`. A due candidate
requires a fresh claim; its existence is no permission to post. The actual
default router returns `android_dispatch_disabled` with no job/grant.

### POST `/api/v3/android/smart-reminder/jobs/{job_id}/claim`

Strict JSON, at most 4096 bytes, no duplicate or extra keys:

| Field | Requirement |
| --- | --- |
| `version` | Integer 1; JSON boolean/string is refused. |
| `request_id` | Lowercase canonical UUID, persisted for this operation. |
| `local_epoch` | Lowercase UUID from the current local account link; response fence, not server authentication. |
| `capability_generation` | Current own-device observation generation. |
| `preference_revision`, `grant_epoch` | The selected server job's fences, rechecked against current authority. |

After all guards, the caller-owned transaction creates one grant tombstone and
one `in_flight` study attempt, then commits before the HTTP response can reach
the client. Grant binds job/attempt/owner/device/session/local epoch, request,
capability/cohort generation, policy, revision/epoch and evidence hash. Deadline
is the minimum of job/auth/session/capability/all-present-fence/review validity
and known quiet/day boundaries. SQL waiting past expiry withholds the response
grant and retains a cancelled-attempt tombstone. No arbitrary product TTL is
introduced. Client code must independently reject an expired response.

Only that first response can contain `dispatch_allowed=true`, opaque `grant_id`,
issue/expiry times and minimal current course/target/day facts. There are no
private lesson contents, credentials, access tickets or embedded authorized
lesson URLs. Every open uses the ordinary fresh-auth/access destination.

Exact or changed-request repeats never return posting authority again, even
after expiry or a lost response. One unique job grant and account/request
uniqueness backstop User-first serialization. A client must persist its local
day/epoch guard, verify current OS permission/account epoch and expiry just
before notify, and never start an autonomous fallback after offline/error.
FCM is a job hint, not authority; wake-only hint telemetry must not pre-create a
study posting attempt or reuse the legacy `last_study_push_day` as new display
proof. Both FCM and WorkManager participate in the same claim in task 5.2.

### POST `/api/v3/android/smart-reminder/jobs/{job_id}/receipt`

Strict JSON fields: integer `version=1`, UUID `grant_id`, UUID `receipt_id`,
original `local_epoch` and one `outcome`:

| Client outcome | Stored attempt truth |
| --- | --- |
| `client_declined_before_post` | `confirmed_not_displayed`, explicitly an authenticated client's pre-OS declaration. |
| `client_posted_unverified` | Notification call reported; display/read is unverified. |
| `client_outcome_unknown` | Unknown; no alternate or retry authority follows. |

The same original native session/device/epoch must own the issued grant. The
first receipt is immutable. Exact retries acknowledge it; another receipt ID
or outcome returns `409 android_receipt_conflict`. Client `verified_shown`, read
and learning outcomes are rejected. No course/XP writes or notification inbox
record are created by these receipts.

An expired grant, master OFF or disabled dispatcher may still record a fresh
authenticated historical receipt, without renewing authority. Revoked/expired
native sessions and blocked/deletion accounts remain refused. Device/session
cleanup retains the issuance tombstone with nullable FKs; it cannot restore a
posting grant. Posted/unknown outcomes close the job as `unknown`; a reported
pre-post decline closes it as `cancelled`. All retain account-day ownership.

## Storage, rollout and limits

`0136_smart_android_grants` adds the User/job/attempt-owned grant table with
unique job/attempt and account/request constraints. Canonical account purge
explicitly deletes its grants before attempts/jobs, even without FK cascades;
other accounts retain their outcomes. Populated downgrade refuses removal. The empty-QA initializer registers the
model but defers its DDL to the actual migration. Apply the migration before
installing any reviewed enabling factory. Do not run the initializer on an
existing DB or treat local migration tests as a staging backup/restore drill.

Rollback disables admission/dispatch while preserving schema, issuance,
outcomes and P1 OFF/revision/epoch guards. D21 analysis-detail cleanup does not
silently delete authority/dedup evidence. A claim loss/timeout/unknown receipt
does not allow another device or Telegram attempt. Controlled same-job
fallback is not implemented here; task 5.4 must separately prove any extension
revokes the old authority and cannot replay a late original hint.

No atomic transaction spans the server, network and Android notification OS
call. An already authorized in-flight client cannot be physically recalled by
a later OFF/hold. Provider acceptance or a successful notify call proves no
display/read/learning. Real signed builds, two devices, offline client behavior,
legacy-client fencing, provider delivery and monitored rollout remain open.

## Repeatable two-device QA acceptance

`tests/e2e/smart_android_two_device.py` drives only two explicitly named
`Codex_Smart_Mixed_` emulators containing the separate `.qa` app/test package.
It requires an owned disposable loopback `smart_reminder_qa` PostgreSQL DSN,
an ephemeral loopback SAN certificate/key and an outside-Git output folder.
It starts a loopback-only TLS FastAPI router with the existing synthetic native
SQL fixtures and explicit test-only delivery factory. Real production remains
disabled. No endpoint/fixture reads real accounts or real provider credentials.

The driver writes synthetic bearer input into the private QA app cache through
`run-as`, removes it after each test, counts HTTP paths without logging proof,
and checks committed grants/attempts/outcomes. `SmartStudyTwoDeviceTest` pins
only that fixture certificate, keeps hostname validation and the normal origin
guard, and uses no global TLS or production auth bypass. Real API/native auth,
Retrofit scalar decoding, PostgreSQL and Android durable/OS boundaries run.

One compatible Direct QA and one Play QA installation share a canonical
synthetic account: only the selected installation can claim/post/receipt.
A second scenario leaves the other synthetic inventory record without trusted
capability and requires zero new authority/notify. This negative inventory
case does not execute or attest a real historical APK/account. Separate signed
artifact/cold-start evidence likewise does not prove an authenticated signed
study flow. See Master Plan §17.53; parent 5.3 and canary remain open.
