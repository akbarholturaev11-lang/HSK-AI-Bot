# Smart first-ready baseline

Execution and acceptance: `SMART_REMINDER_MASTER_PLAN.md`, §§17.67–17.68. This is
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
fresh XP or a passing score. Reviewed stored version-1 mock/placement/training
completions from the shared canonical server grader also count at their original
retained result time without a new award. Deterministic result dedupe still
cannot establish later repeated attempts or move an old result to retry time.
Deduplicate original units and distinct frozen
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

A read-only report uses anonymous materialized totals and SQL membership counts,
without reading individual learning/contact rows. It reports original accounts,
retained/censored detail, mature observed accounts, unobserved accounts and
pending retained observations. Mature-window counters describe successfully
observed accounts, not all retained follow-up windows. Pending includes immature
members. Censoring describes currently missing/expired/protected detail and may
overlap already observed anonymous outcomes; these counts are not additive.
Final fractions/means require a closed entry month and completed latest follow-up. Empty/unreadable cohorts
remain unavailable, not zero retention. A fully read reviewed source with zero
positives may report **zero observed positives**, explicitly not no learning or
a verified unsuccessful reminder. Source-limit cases keep proven positives but
withhold unknown zeros/derived rates. All resulting counts/fractions are lower
bounds over reviewed sources, not complete primary retention KPIs or causal
lift. `d7_learning_retention` stays unavailable; `primary_kpis_available`,
`experiment_ready` and `dispatch_allowed` remain false.

`0145_smart_baseline_outcomes` adds first-observed time and minimal raw mature
counts/flags to membership, plus anonymous month outcomes. Collection requires
the complete frozen D7 follow-up and fresh User-first block/deletion/expiry
checks. The existing optional reconciliation loop has a separate baseline
cursor/budget: at most 128 owner IDs per page, with the existing 512-row source
sentinels per account. An unavailable owner advances the cursor and is retried
on a later pass. Restart rescans safely. Job traffic/failure cannot consume the
baseline budget. Disabled analysis does no baseline SQL; there is no new loop,
flag, sender or production activation.

First observation increments the anonymous observed-account count once. Raw
snapshot and anonymous nonnegative deltas commit together. Repeated/reverse/
concurrent work cannot double-count. Later retained proof can improve counts;
previously proven active-day/unit counts use monotonic maxima and D7/D1/source-
limit flags are sticky. If source availability changes, a maximum is a safe
lower bound rather than an invented union of unavailable individual references.
The original first-observed time stays immutable; a no-change observation does
no writes. Source exceptions/timeouts roll back the whole account observation.

Reports have no whole-cohort size cap and use one aggregate SELECT regardless
of cohort size. Unprocessed members never disappear from the original denominator
or become verified failures. Previously observed anonymous outcomes survive
personal purge/90-day expiry, even though those owners cannot be read again.
There is no personal history in the month totals. Real baseline traffic,
cohort/coverage audit, MDE/power, statistical uncertainty and owner-reviewed
experiment calibration remain parent 6.2 work. There is no arbitrary model-
success/sample threshold.

## Retention and rollback

D21 raw expiry is original entry +90 days. Anonymous entry-month totals retain
the current UTC month and eleven previous buckets. Existing analysis retention
adds separate bounded member/total pages and count keys without removing old
keys, learning/progress/XP, preferences or operational jobs. Canonical account
purge explicitly removes owned membership, with FK cascade as an additional
guard; anonymous denominators and observed outcomes survive. Expired source
replay cannot recreate an entry/counter. Disabling analysis stops capture/recovery/cleanup without
changing sending or deleting source evidence. Populated raw or anonymous-only
0144 downgrade refuses. Populated 0145 outcome downgrade also refuses, including
anonymous-only observations; unobserved populated 0144 entries survive an empty-
outcome 0145 roundtrip. Retain schema knowledge when rolling back. The reviewed empty local-QA initializer head is 0145. No existing remote
initializer, operator-run migration/configuration or provider action is implied.

## Explicit anonymous operator report

`scripts/smart_reminder_baseline_report.py` reads one existing cohort month.
Use the project Python environment and run from the repository root after
supplying an explicitly authorized database
URL in the secured `SMART_REMINDER_BASELINE_DATABASE_URL` environment variable:

```sh
python -m scripts.smart_reminder_baseline_report --month 2026-10
```

The URL is never a command argument and there is no application settings or
`.env` fallback. PostgreSQL URLs (`postgres`, `postgresql` or
`postgresql+asyncpg`) require an explicit host/database; the only optional URL
query is `ssl=require`, `ssl=verify-ca` or `ssl=verify-full`. Non-loopback targets
default to required TLS. SQLite requires an existing absolute file using the
`sqlite+aiosqlite` driver and no caller-supplied URL options. It opens through
driver `mode=ro` plus connection `query_only`. PostgreSQL uses startup read-only
defaults plus the existing report transaction guard. OS/database access is the
operator boundary; this command is not a public API.

Connections use a dedicated unpooled engine and finite connect/statement/lock
timeouts, with a ten-second operation timeout and cleanup on error/cancellation.
Output is the existing anonymous JSON projection only. It reads baseline totals
and SQL-counted membership/owner/deletion status; it never fetches individual
learning, contact, device, token or answer records. Missing/immature/expired/
limited/censored data keep their original unavailable/lower-bound meanings.
No request IDs, member identities or source job IDs enter output. Generic
failure codes replace raw URLs, driver exceptions, SQL and tracebacks.

This command does not run aggregation, retention, initialization or migration;
it cannot fill missing observations or create a cohort. Analysis/sender settings
and source records remain untouched. A missing target or schema is an explicit
measurement gap, not a measured zero or a reason to use synthetic results as
production evidence. Real baseline, statistical calibration and activation
remain separate acceptance steps in the Master Plan.
