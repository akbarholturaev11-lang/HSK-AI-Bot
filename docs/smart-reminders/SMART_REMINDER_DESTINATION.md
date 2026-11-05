# Smart Reminder destination proposals

`app/services/smart_reminder_destination.py` implements the D06 choice core.
The authoritative decisions and executed acceptance remain in
`SMART_REMINDER_MASTER_PLAN.md` §§17.57, 17.77–17.80. This is a component contract, not a
second progress tracker or evidence that production dispatch is enabled.

## One eligible destination

The service reads an owned, current-revision/current-epoch, unselected and
unattempted shadow job inside a caller-owned transaction. It takes the existing
User-first preference lock and does no writes, commit, provider IO or admission.
Selected, leased, attempted, stale or expired intents cannot be retargeted.

Candidates require current canonical channel/device study consent. Android
additionally requires an owned unrevoked device, active native session, present
push token, matching frozen timezone and fresh protocol-1 capability with study
permission and autonomous study posting disabled. Token values are never
selected. Multiple sessions on one phone remain one destination. Telegram
requires its existing unblocked transport and study consent. Account-notice
permission and legacy preference mirrors do not create Smart study consent.

Master OFF suppresses choice. A manual channel lock filters candidates first;
an unavailable locked channel cannot silently switch to another. If exactly one
destination remains, select it immediately without querying study history or
requiring a confidence threshold/warm-up. Unsupported iOS/desktop notification
hosts are excluded until their actual adapters exist.

## More than one eligible destination

The pure core ranks candidates by distinct verified study results, then latest
verified result, then recent reachability and stable identity for exact ties.
An app open is not a study result; neither are reward XP, duplicate awards,
foreign/unbound results or future/out-of-window evidence. Conflicting endpoint
bindings for the same canonical result are discarded for all affected devices.

The current SQL reader uses existing server-generated `android_course` terminal
lesson events: `payload.device_id`, original nonduplicate awarded-XP metadata
and completed lesson must agree with canonical positive XP/current progress.
The original XP identity and acceptance time survive replay. Existing history
before Smart activation can therefore contribute immediately. The caller must
provide an explicit aware observation window; this component does not invent
a new history duration or change D17's approved policy.

**Coverage is partial:** the real reader currently attributes native Android
lessons in the frozen course only. It does not establish Telegram, practice,
desktop or unbound historical device usage. `native_android_lesson_attribution_only`
is always carried with multi-destination SQL evidence. A typed internal reader
interface can supply later verified sources without changing the choice core;
no client can submit destination votes through an HTTP endpoint.

An empty/over-limit history uses
`recent_reachable_destination_fallback`, with `observed_results=None`, rather
than claiming a measured zero or a proven most-used endpoint. Positive counts
mean observed verified results within the stated coverage only. Device last-seen
and capability-observed times are fallback reachability, not learning or
provider reliability. Work limits of 128 destinations and 512 evidence rows are
technical bounds, not product confidence or inactivity thresholds.

## Proposal does not authorize delivery

The immutable result binds job, preference revision, grant epoch, version,
finite validity, reason and coverage limits, with `dispatch_allowed=False`.
It is rechecked against the clock after history reading. It does not change the
job's selected endpoint, create an attempt or issue an Android posting grant.

The internal default-disabled `SmartReminderPlanner` now joins reservation,
selection and one pending destination. It accepts only already reviewed routing
(operator or, since 2026-11-05, the production runtime's automatic admission)
with current inventory/revision/epoch and explicit cadence/complete-learning
readers; a `telegram` row uses the Telegram ownership fence and a `held` row the
native fresh-capability fence. Android additionally requires the existing privileged job/device/session
admission reader; Telegram requires its activated cohort and feature setting.
No review or consent is inferred from a capability/client field.

After the existing queue freezes account/day ownership, the planner locks User
before its job, reuses transport policy/completion/access/cadence/D1 checks,
then rechecks destination, context, review and expiry before an atomic pending
binding. A repeated pending selection is acknowledged without reranking;
leased/attempted/terminal work is never retargeted. Planning creates no attempt,
grant, provider call or fallback to another endpoint. Only the existing native
authenticated claim or committed Telegram attempt can proceed toward delivery.

The production host has an explicit internal registration hook but no configured runtime or authoritative admission/complete-learning factory,
new flag, schema, poller, client behavior or transactional-notice change.
Rollback leaves the planner disabled; existing pending ownership and the original
claim/receipt guards stay intact. Local integration does not prove live fencing
or provider/installed canary acceptance.

## Verification

`tests/test_smart_reminder_destination.py` exercises pure selection and real
SQLite/PostgreSQL source reads, actual gamification/terminal-event payload
shapes, ownership/consent/capability/session guards, conflict/replay, expiry,
single-endpoint history bypass and the lack of any claim authority or writes.
The Smart regression workflow includes these paths and tests. Local test
results do not establish production usage, physical display or provider
delivery; exact executed results are recorded only in the Master Plan.
`tests/test_smart_reminder_planner.py` also exercises real reservation/binding,
native authenticated claim/receipt, committed Telegram claim with fake provider,
most-used selection, concurrency, final-read changes and transactional rollback
on SQLite/PostgreSQL. Disabled/missing configuration returns before SQL/IO.

## Reviewed runtime host

`SmartReminderRuntime` connects the planner to the main lifespan and native
factory only through an explicit server-owned `app.state.smart_reminder_runtime`
object with the exact same settings and session factory. Production configures
no such object. There is no HTTP registration, new environment flag or implicit
cohort enrollment. Caller-supplied cadence calibration, positive history window
and authoritative learning reader are required; Android also needs its existing
reviewed admission callback (including the explicit persisted native review
source in the Android protocol), and Telegram its current switch and explicit trusted
transport. No reader can turn partial legacy results into complete coverage.

The bounded rotating loop scans already reviewed unexpired routing accounts,
rechecks canonical actor/course/IANA calendar and uses the planner. Existing
pending/claimed selected work is handled before new reservation: a due Telegram
job can resume after its planning time through the original committed claim and
dispatch. Started/unknown attempts never replay; only an expired unstarted lease
can resume through the same attempt. Native requires no provider hint: its own
authenticated polling/claim path uses the same runtime dependencies and guards.
The injected Telegram callback receives the existing envelope and runs after
SQL authorization commits, with no open runtime DB session.

A ready registered runtime replaces the shadow-only evaluator in that host.
Absent/incomplete/disabled registration starts no runtime polling; existing
shadow configuration and disabled native defaults remain. Wrong settings/session
identity cannot enable a host. Runtime pause/removal suppresses readers and new
transport at fresh boundaries; shutdown cancels/awaits its independent task.
Committed external IO cannot be recalled; original receipts and uncertain
account/day ownership remain. Technical batch/timeout/cursor limits confer no
product confidence or permission. Actual feed completeness, calibration,
fencing and real provider/installed staging acceptance remain separate gates.

## Early-return eligibility

An ended historical unknown contact cannot veto a separate later nonoverlapping
study day. Its original attempt, unknown evidence and weekly cost remain intact;
it is neither retried/fallen back nor counted as an unsuccessful shown job.
Current/overlapping account-day ownership and a still-live unknown window retain
their veto. Shared rolling budgets remain authoritative, so three prior contacts
can still suppress another intent within seven local days.

Before a verified unsuccessful exposure, a whole-day learning rhythm permits the
local date obtained from the last verified study date plus that rhythm. Its UTC
midnight is a cadence eligibility boundary; the existing personal time is the
actual notification clock. A daily ~20:20 learner can therefore be eligible on
the first missed local day despite a previous 20:24 completion or a 23-hour DST
day. Fractional-day medians retain their original elapsed-time anchor. Actual
verified-shown observation/factor-two backoff and stop remain unchanged; unknown
contacts are not failed responses. Authoritative learning coverage and all
permission/goal/access/quiet/review guards are still required. No fixed week-long
wait, new campaign, extra message budget or production activation is introduced.
