# Smart first-ready baseline

Execution and acceptance: `SMART_REMINDER_MASTER_PLAN.md`, §17.67. This is
bounded observed-baseline infrastructure, not real measured traffic, a
randomized experiment, model readiness or production activation.

## Source and first entry

The origin is the first reviewed **base-policy-ready** account observation,
not signup, notification delivery or a click. Current evidence is a committed
owned `smart-queue-shadow-v1` reservation (use the actual `QUEUE_VERSION` constant).
Its producer has already checked canonical consent/OFF, policy context, course
access/goal and existing D1 ownership. A reservation may still have unconfigured
cadence or lack transport admission: this cohort does not certify full dispatch
readiness or count all eligible accounts. No cohort assignment or send follows.

The existing optional post-commit reservation sink and bounded reconciliation
capture the earliest retained reviewed shadow job by original creation time,
under the User-first lock and current block/deletion guard. Mutable shadow jobs
are now also traversed for membership recovery; they produce no fabricated
terminal candidate/delivery facts. Existing capture counters continue to count
only their original analysis fact classes. Source errors/timeouts cannot roll
back or retry the real reservation. Disabled analysis does zero new polling.

`0144_smart_baseline` adds:

- `smart_reminder_baseline_members`: canonical owner/protocol key, opaque first
  source job, original entry time, frozen IANA zone/course and 90-day expiry.
  There is no device, contact, token, answer, feature payload or assignment arm.
  The source job is opaque provenance rather than a deletion-cascading FK.
- `smart_reminder_baseline_totals`: protocol/UTC entry month, original enrolled
  account count and maximum frozen D7 end only. It contains no owner identity.
  Count/maturity update atomically only when the owned member first inserts.

Entry is immutable and retries/concurrent/reverse capture cannot count an
account twice. The earliest retained operational source is considered even
when old; if its original time is expired, a new job cannot reset entry after
raw cleanup. Retain original operational source/day evidence during rollback.
Future protocol versions require a separate reviewed measurement definition.

## Windows and learning source

`SmartReminderBaselineService.report(cohort_month)` is internal and returns
anonymous results only. Any future API must supply protected operator auth.
The month is a UTC entry-month group, not a notification/respondent/device
sample. Day 0 begins at the original entry instant. The first week ends at the
frozen local date +7 midnight (at most seven distinct local dates, including
its partial entry day); D7 is the complete local date +7 through +8 midnight.
Intervals exclude their upper boundary. Existing IANA day-window logic handles
DST; later account timezone/course changes cannot move entry or the D7 window.
These windows define the metric, not an experiment's duration or stopping rule.

Actual account study counts independently of sends and clicks. Original lesson/
mock/placement/training units require unique positive canonical XP and reviewed
server terminal receipts, using the same strict receipt validator as other
analysis. The baseline reads account-wide canonical courses and original refs;
late receipts or a practice result just before its XP can corroborate that
original unit without moving its time. For this historical reader, mutable
current-course progress does not invalidate an older server-confirmed result.
Existing policy/target readers retain their current-progress corroboration.

Reviewed server-graded section, legacy quiz and HSK exam activity counts without
fresh XP or a passing score. Deduplicate original units and distinct frozen
local study dates per account. Generic app opens, reward XP, client terminal
telemetry, malformed/boolean scores and unpaired/unsupported evidence do not
prove study. Repeat-practice/voice and legacy capture gaps remain explicit.

## Denominators and unavailable values

Always retain original anonymous enrollment count as the denominator. Personal
purge removes membership but does not decrease it. Blocked/submitted-deletion,
expired or missing members are censored; their personal learning is not read.
Do not remove nonresponders, OFF users or later D1-overlap accounts to improve
a result. Both existing D1 arms veto new source reservations; later D1 overlap
is annotated, never reassigned and never authorizes Smart treatment.

A live projection reports retained/censored counts, window maturity, observed
active dates/units and D7-positive accounts. Final fractions/means require a
closed entry month and completed latest follow-up. Empty/unreadable cohorts
remain unavailable, not zero retention. A fully read reviewed source with zero
positives may report **zero observed positives**, explicitly not no learning or
a verified unsuccessful reminder. Source-limit cases keep proven positives but
withhold unknown zeros/derived rates. All resulting counts/fractions are lower
bounds over reviewed sources, not complete primary retention KPIs or causal
lift. `d7_learning_retention` stays unavailable; `primary_kpis_available`,
`experiment_ready` and `dispatch_allowed` remain false.

The current retained-member detail work bound is 128 members, with 512-row source-class
sentinels per account. An over-limit cohort returns its original anonymous
count and an unavailable result; it never silently samples a denominator.
Larger-cohort bounded aggregation, real baseline traffic, cohort/coverage audit,
MDE/power, statistical uncertainty and owner-reviewed experiment calibration
remain parent 6.2 work. There is no arbitrary model-success/sample threshold.

## Retention and rollback

D21 raw expiry is original entry +90 days. Anonymous entry-month totals retain
the current UTC month and eleven previous buckets. Existing analysis retention
adds separate bounded member/total pages and count keys without removing old
keys, learning/progress/XP, preferences or operational jobs. Canonical account
purge explicitly removes owned membership, with FK cascade as an additional
guard; anonymous denominators survive. Expired source replay cannot recreate
an entry/counter. Disabling analysis stops capture/recovery/cleanup without
changing sending or deleting source evidence. Populated raw or anonymous-only
0144 downgrade refuses; empty-new-table roundtrip preserves older source/facts.
The reviewed empty local-QA initializer head is 0144. No existing remote
initializer, operator-run migration/configuration or provider action is implied.
