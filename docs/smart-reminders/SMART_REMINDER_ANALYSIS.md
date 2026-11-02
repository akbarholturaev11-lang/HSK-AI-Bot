# Smart delivery analysis contract

The execution ledger is `SMART_REMINDER_MASTER_PLAN.md`, §§17.55–17.59. This
contract defines P6 6.1a, optional 6.1b integration, bounded 6.1c reconciliation
and 6.1d terminal shadow observations, not a live rollout.

`SmartReminderAnalysisService.capture_job(user_id, job_id)` is an internal,
explicit operation over a committed owned job and its attempts/Android grants.
It owns a separate User-first transaction. A delivery transaction never calls
or depends on it; analytics failure cannot erase an already committed outcome.
There is no capture endpoint, provider, learner input or automatic inventory
scan. Source hooks, reconciliation and independent retention default OFF.
Reviewed v1 Android/Telegram policy families require matching selected channels.
Exact terminal shadow jobs have separate stages below; mutable/unknown policy
jobs are excluded. Source timestamps must be neither future nor older than 90 days.

| Analysis stage | Required source | Interpretation |
| --- | --- | --- |
| `reserved` | Owned selected v1 job's creation | Logical reservation, not a send |
| `in_flight` | Attempt's stored start | IO boundary may have been crossed |
| `provider_accepted` | Accepted attempt and resolution time | Provider acceptance, no display/read/learning proof |
| `client_posted_unverified` | Matching Android attempt and original immutable posted receipt | Client reports OS posting, still unverified display |
| `confirmed_not_displayed` | Matching Android attempt and original pre-call-decline receipt | This attempt did not reach the OS call; no alternate or budget refund |
| `outcome_unknown` | Resolved unknown attempt or matching unknown receipt | Uncertain; never infer failure, non-display or fallback eligibility |
| `cancelled`, `expired` | Terminal job and transition time | Job state, not proof that an earlier external attempt disappeared |
| `definite_failure` | Explicit resolved attempt state | Only the recorded boundary's failure |
| `shadow_candidate` | Exact completed, unselected, unattempted shadow job with fixed `shadow_candidate` reason | Policy simulation only; no reserved/delivered/display/learning claim |
| `shadow_suppressed` | Exact unselected/unattempted terminal shadow job with a reviewed reason | Its stored guard/cadence/expiry reason; no nonresponse or display inference |

The existing attempt enum alone cannot prove `verified_shown` or a client post
without its matching receipt. Shown, read, opened and attributed server learning
remain **unavailable**; these counters are not fabricated zeros or inferred from
FCM acceptance, widget/app opens or XP. Pre-reservation/real-dispatch candidate and suppression instrumentation,
trusted open/learning linkage, complete coverage, denominator/experiment
and model evaluation remain separate parent 6.1/6.2/P7 work.

Migration `0137_smart_analysis` adds two tables; `0138_smart_shadow_analysis`
extends only their stage constraints for explicit shadow observations:

- `smart_reminder_analysis_events`: owner/job FKs, a hash of immutable
  source-and-stage identity, a fixed stage/reason/channel and source time/expiry.
  No token, device/session identifier, body, copy, lesson, address or arbitrary
  payload. The owner lock and unique owner/key prevent duplicate/racing capture.
- `smart_reminder_analysis_monthly`: UTC month, stage, channel and fact count
  only. An inserted raw fact increments its bucket in the same transaction;
  duplicate capture increments nothing. These are stage facts, not unique
  learners/messages, a causal learning effect or a denominator.

## Committed terminal shadow decisions

The same source capture/reconciliation records the already committed queue
reason. Only exact `smart-queue-shadow-v1` jobs with no selected channel/device,
lease or attempt qualify. Completed cadence `shadow_candidate` maps to that
explicit shadow stage. Other reviewed completed cadence reasons, reviewed
cancelled guard reasons and exact expiry map to `shadow_suppressed`. Each raw
fact retains the original fixed server reason and terminal update timestamp,
channel `none`, with no added personal fields or job mutation. Unknown codes,
impossible state/reason combinations and selected/attempted jobs are withheld.

Grain is one terminal shadow stage per canonical source job. Repeated scans,
parallel workers and process restart cannot increment it again. Monthly counts
retain the same month/stage/channel grain, not unique learners, attempts or a
suppression rate; reasons remain only in private retained detail. Missing facts
are unknown. Refusals before a durable job exists, D1 before reservation,
auth/deletion refusals, real dispatch choices and unimplemented source coverage
are not supplied by this adapter. Current normal runtime cadence is unconfigured
and therefore cannot produce a positive cadence candidate. Positive candidate
QA uses explicitly synthetic complete coverage/calibration; it is not evidence
that runtime activation or ML admission is ready.

Migration 0138 preserves all existing delivery/raw/monthly/source rows and FKs;
it changes two CHECK constraints only. Downgrade keeps old-stage rows but refuses
if either table contains new shadow stages, including anonymous-only retained
counts. No remote migration or existing QA initializer is run by merging this
source. Disabling analysis leaves original queue behavior and retained evidence
unchanged.

## Retention and privacy boundary

| Class | Policy |
| --- | --- |
| New analysis detail | D21: expires at original source time + 90 days |
| Anonymous monthly totals | D21: current UTC month and eleven preceding buckets |
| Existing course progress, XP, canonical learning | Unchanged; analysis retention never deletes them |
| Consent/OFF, account-day jobs, attempts, grant/receipt tombstones | Separate operational evidence; no new TTL or replay/reset authority |
| Account deletion | Canonical purge explicitly removes own raw analysis; FK cascade is a second guard. Anonymous totals contain no account/source link. Submitted deletion prevents new capture. |

The monthly interpretation retains at most twelve complete/calendar buckets;
expiry is not extended by late capture. This is a minimal class review under
the approved D21 scope, with no new clickstream or personal feature store.
No private job state is exported into Redis/R2 or public metrics. Future small
cohort/experiment exposure requires its own reviewed read projection.

## Optional source integration

`SMART_REMINDER_ANALYSIS_ENABLED=false` is the default. Setting it true requires
the reviewed 0138 schema and enables observation/analysis-only retention, never
study dispatch, admission, enrollment or a provider. Android's successful claim
or receipt schedules only owner/job metadata in a Starlette background callback:
the source transaction/session has closed and the complete HTTP body is sent
before capture. GET, malformed/foreign/unauthenticated requests and refused
claims schedule no capture. No request, bearer or claim body is retained.

Telegram captures only after the terminal source transaction commits. Provider
IO never calls analysis. The shared observer bounds work (two-second technical
timeout by default), logs a fixed content-free warning on failure and returns
no invented count. Capture cannot change the committed grant/receipt, HTTP
response or accepted/unknown Telegram outcome. Parent cancellation propagates.
Disabled hooks make no analysis SQL; due/preference reads remain non-persisting.

Capture is best-effort: interruption between commit/response and observation can
miss a fact. Bounded idempotent reconciliation can recover available committed
source facts as described below; source history is still not complete coverage. No complete measurement coverage, non-display,
negative learning or learning lift follows from missing analysis. These gaps
must be addressed before a meaningful cohort baseline or ML admission.

When explicitly enabled, lifespan starts a separate bounded retention task;
the legacy scheduler, shadow evaluation and Admin PWA poller do not await it.
It processes one existing analysis page each technical interval (60 seconds by
default), retries cleanup after failure and is cancelled/awaited on shutdown.
It creates no jobs, attempts or alternate sends. No remote flag or schedule is
enabled merely by merging this source.

## Bounded source reconciliation

The same default-false analysis switch starts a separate reconciliation task.
Its source-page transaction reads only owner/job IDs from reviewed v1 selected
Android/Telegram jobs or exact terminal shadow jobs, closes before any owner capture and holds no delivery
lock. Pages use stable job-ID keyset ordering, a 128-job technical maximum and
bounded SQL duration. A source qualifies within D21's original 90-day window:
reservation, terminal cancel/expiry, attempt start/resolution or native receipt.
A recent child outcome can therefore qualify even if its parent creation is
older; expired parent facts cannot be recreated or extend their retention.

Each tick has a total technical time budget (two seconds by default). It calls
the existing User-first capture transaction for each source, preserving fresh
ownership/deletion/policy and receipt validation. A failed/locked owner is
cancelled safely and its cursor position advances so later jobs can progress
on subsequent ticks. The next pass retries it. A page-query failure keeps the
position; parent cancellation propagates and leaves unfinished capture for a
safe retry. Fixed warnings contain no actor, SQL, exception or credential data.
Retention and reconciliation do not await each other or the delivery scheduler;
lifespan cancels and awaits both on shutdown. Disabled means zero scan SQL.

The cursor is process-local scheduling state, never an authorization or
measurement watermark. End-of-pass and restart rescan durable source records;
existing source-stage uniqueness makes concurrent callbacks/replicas/restarts
idempotent. Returned examined/inserted/unavailable counts describe that tick
only; `pass_finished` is traversal progress, not evidence that all outcomes were
captured or that a learner did not study. Source loss, mutation, expiry or
unimplemented instrumentation can still leave gaps. There is no token/device
inventory read, new metric stage, schema, provider, retry/fallback send or
operational source write. No production flag or reconciliation run is enabled
by this source change. Rollback uses the existing analysis boolean; retained
delivery guards and original timestamps remain intact.

`python -m scripts.smart_reminder_analysis_retention` returns anonymous expiry
counts only. `--purge-expired --limit 128` explicitly removes at most one raw
page and one monthly page; valid limits are 1–128. It never deletes a source
job, attempt, grant, preference, course/XP record or another non-analysis class.
The enabled task or operator must run enough pages to drain a backlog; no live
production execution is implied. Source-time checks refuse expired replay after raw
deletion, and never recreate an old fact to increment totals again.

No initializer is run against an existing database. The reviewed empty-QA
initializer advances to 0138 and leaves both new tables to real migrations.
Downgrade refuses either populated analysis table rather than deleting data.
Disabling capture changes no delivery authority; preserve all consent/day/grant
guards and operational evidence during rollback.
