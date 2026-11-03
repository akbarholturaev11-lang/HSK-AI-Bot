# Smart delivery analysis contract

The execution ledger is `SMART_REMINDER_MASTER_PLAN.md`, §§17.55–17.72. This
contract defines P6 6.1a, optional 6.1b integration, bounded 6.1c reconciliation,
6.1d terminal shadow observations, 6.1e reservation observations and 6.1f
committed runtime guard reasons, the 6.1g internal target-learning projection
6.1h authenticated client-reported opens, 6.1i verified temporal completed-unit
outcomes, 6.1j scored active-study days, the separate 6.1k 24-hour window and
6.1l retained scored practice completions, 6.1m completed voice activity and
6.1n optional server-bound repeats,
not a live rollout.

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
without its matching receipt. Independently verified shown/read/opened and attributed server learning
remain **unavailable**; these counters are not fabricated zeros or inferred from
FCM acceptance, widget/app opens or XP. Transient real-dispatch guards without committed source evidence,
trusted open/learning linkage, complete coverage, denominator/experiment
and model evaluation remain separate parent 6.1/6.2/P7 work.

Migration `0137_smart_analysis` adds two tables; `0138_smart_shadow_analysis`
extends only their stage constraints for explicit shadow observations. Migration
`0139_smart_reservation_analysis` adds job-independent reservation detail and two
explicit anonymous shadow-reservation stages. `0140_smart_open_analysis` extends
only raw/monthly stage constraints for the separate `client_reported_open` fact:

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
are unknown. This job-bound adapter does not supply refusals before a durable
job exists; the optional reservation adapter below covers actual reserve
outcomes. Auth/deletion refusals, uncommitted dispatch choices and unimplemented
source coverage remain unavailable. Current normal runtime cadence is unconfigured
and therefore cannot produce a positive cadence candidate. Positive candidate
QA uses explicitly synthetic complete coverage/calibration; it is not evidence
that runtime activation or ML admission is ready.

Migration 0138 preserves all existing delivery/raw/monthly/source rows and FKs;
it changes two CHECK constraints only. Downgrade keeps old-stage rows but refuses
if either table contains new shadow stages, including anonymous-only retained
counts. No remote migration or existing QA initializer is run by merging this
source. Disabling analysis leaves original queue behavior and retained evidence
unchanged.

## Committed runtime guard reasons

Reviewed selected v1 Android/Telegram cancelled/expired jobs retain their fixed
original source reason in the existing terminal analysis fact. Examples include
verified goal completion, inaccessible target, D1, study OFF, source expiry,
legacy-contact guard or invalid Telegram template. The source channel, terminal
time, owner and policy still come from committed SQL under the User-first lock.
No request-body/response text becomes a fact. A channel-specific reviewed catalog
withholds arbitrary/unknown or wrong-channel text through the existing generic
`stored_cancelled`/`stored_expired` reason.

Native reviewed mutating claim refusals schedule the same bounded background
capture after source commit/session close and after the HTTP response body.
GET/auth/foreign/malformed requests and default-OFF, missing-calibration,
capability/admission/not-due or other nonmutating guards do not gain a new
capture path. Telegram captures a reviewed terminal dispatch refusal only after
its source transaction closes; accepted/unknown provider hooks stay unchanged,
with no analysis inside provider IO or a duplicate wrapper capture.

These are the existing one-job/terminal-stage facts, with no schema, new stage,
attempt, grant, provider call or retry. Existing captured facts remain immutable:
old generic reasons are not rewritten from later mutable source text. Replays
cannot increment counts or extend expiry. A cancellation reason alone never
proves non-display, inactivity or learning; matching immutable receipt/attempt
proof is still required for the separate outcome stages. Reconciliation can
recover missed committed terminal facts. Transient refusals with no persisted
terminal evidence remain unavailable, and do not form a complete denominator.
Failure/timeout leaves source results unchanged; disabling analysis preserves
normal protocol/provider behavior. Schema remains 0139 and no migration is run.

## Pre-reservation shadow observations

The actual `SmartReminderShadowQueue.reserve` source constructs immutable
internal metadata only after verified owner/preference locking and actual
policy/reservation execution. Its transaction commits and closes before the
optional observer runs in a separate User-first transaction, rechecking owner
existence and submitted deletion. A rollback or auth failure creates no
observation. The existing strict default-false analysis flag gates the injected
observer; the existing shadow worker supplies it to its queue. No producer,
endpoint, cohort, sender or new background task is introduced.

Migration 0139 adds `smart_reminder_reservation_observations`: owner FK, opaque
deduplication key, stage, fixed actual reserve reason and original time/expiry
only. There is no job FK, fake study intent, device/session/token identifier,
message, arbitrary payload or personal feature column. `shadow_reserved` means
an actual shadow reservation, not cadence eligibility or delivery.
`shadow_refused` means its actual source reason, including OFF, D1, completed
goal, access, unknown timezone or an already-owned day. An existing job's old
cadence reason cannot replace the current reserve refusal reason. The existing
job-bound event stages/constraints stay unchanged.

Deduplication grain is distinct owner/source-version/current-preference-revision/
canonical-course/day/outcome/reason, where available course comes from server
state. A valid IANA local day survives UTC midnight; an unknown zone uses an
explicit technical UTC observation day. Only the digest persists. Repeat checks
do not extend the first observation's expiry or increment its monthly stage
bucket again. A different revision, day or reason is a distinct condition;
counts are not calls, unique learners, a send count or a complete denominator.

The bounded observer logs only a fixed content-free warning on failure/timeout
and preserves the original reservation/refusal without retrying it. Detail and
anonymous increment commit atomically; parent cancellation propagates. Like
other post-commit hooks, interruption before capture can lose an observation.
Job reconciliation cannot recreate a pre-job observation that never persisted.
Missing capture stays unknown. Initial auth/deletion errors and real dispatch/
open/learning attribution remain outside this source. The raw class uses D21's
original-time 90-day expiry, bounded retention and explicit canonical purge;
monthly stage counts retain twelve buckets and have no owner link. Retention
adds `expired_reservations`/`removed_reservations` counts while preserving old
keys, and removes at most one bounded page per analysis class. Downgrade 0139
refuses any reservation detail or retained new-stage monthly count.

## Authenticated client-reported opens

`client_reported_open` means an authenticated owning client reports opening an
original accepted/posted reminder. It is neither independently verified human
opening/OS display nor server learning or causal study return. It changes no
job, attempt, grant, consent, budget, access, cadence or delivery state.

The same strict default-false analysis flag enables optional opaque HMAC-SHA256
metadata. Android's successful live claim response can include `open_proof`,
bound to original grant/job/account/device/session. Telegram's authorized
content can include job/proof **fragment** parameters on its existing validated
course link, bound to original attempt/account. Separate domain/channel bindings
reuse configured native-auth and bot signing keys; no new key or auth credential
is exposed. Missing keys/metadata and metadata failures preserve delivery.
Rotation can make an old report unavailable and grants no fallback authority.
Proofs are not stored in SQL, URIs/queries for native intents, localStorage or
logs. They never replace existing authentication or authorize a lesson/send.

Only header-authenticated own-job JSON POST is accepted:
`/api/v3/android/smart-reminder/jobs/{job_id}/open` uses native Android bearer;
`/api/v3/smart-reminder/jobs/{job_id}/open` uses fresh signed Telegram init-data
in `X-Telegram-Init-Data`. Cookie/query/body ownership and ambiguous headers are
not accepted. Body contains only strict integer `version: 1` and a 64-character
lowercase hex `proof`; no client timestamp, owner, stage, outcome or redirect.
The existing bounded JSON parser and current User-first session/block/deletion
checks apply, with a two-second PostgreSQL statement timeout for observation.

Constant-time verification binds committed selected v1 source, original epoch/
revision/device/session/policy and chronology. Android needs the matching
immutable original posted-unverified receipt; Telegram needs its original
provider-accepted attempt. Declined/unstarted/unknown or mismatched sources are
unconfirmed. The server must receive the report within the original frozen IANA
local day, checked against real boundaries. This is a technical proof-acceptance
scope, not an experiment or causal-attribution window. Late/offline reports or
reports arriving before a confirmed receipt can be lost; missing data stays
unknown rather than proving no open or permitting a second send.

Android passes optional proof only from the live grant into explicit notification
Intent extras with the original local link epoch. Notification entry parses it
strictly, validates current auth generation/link, and makes one best-effort API
call outside auth/store locks. The original navigation does not await it; old,
widget or malformed entries do not become reports. There is no cross-account
persistence/retry. Telegram's visible signed Mini App entry sends one best-effort
same-origin POST, with cookies omitted, redirects refused and no referrer. Its
consumer rejects missing/duplicate/malformed metadata, preserves Telegram launch
fragments and does not reinterpret generic Mini App opens as reminder opens.

Migration 0140 adds no table or personal column. Existing owner/source-stage
hash identity deduplicates one original attempt's first server-received report;
raw fact and anonymous UTC-month increment commit atomically. Replay extends
neither count nor expiry. Fixed reason is `authenticated_client_report`, with no
proof/body/device/session/copy retained in analysis. Existing D21 raw 90-day,
twelve-month aggregate retention and canonical purge cover this stage. Downgrade
refuses raw or anonymous-only open facts before changing constraints. The empty
QA initializer's reviewed head becomes 0140; no remote migration/initializer or
flag is run by this task. Disable analysis for rollback, preserving operational
and already recorded evidence. Source reconciliation cannot recreate a report
that never persisted, and incomplete reports are not a denominator.

## Internal target-learning source projection

`SmartReminderAnalysisService.target_learning(user_id, job_id)` is an explicit
internal non-persisting read, outside dispatch, cadence and public/admin
metrics. Capture/reconciliation reuse its private validated source reader. It validates a current owned reviewed v1 target job in
a separate User-first transaction, refusing blocked/submitted-deletion accounts.
The public projection performs no DML; source reads use finite row bounds and
a PostgreSQL statement timeout. The later optional capture stages are described
below. Removing the projection changes no delivery.

Positive evidence requires an actual started/resolved Telegram provider-accepted
attempt or Android posted-unverified attempt with matching immutable original
grant/receipt, policy/revision/epoch/device and timestamps. Reservation, declined,
unstarted, unknown or arbitrary attempt state is insufficient. Existing source
contact facts remain accepted/posted-unverified; this projection proves neither
OS display nor notification opening.

The source scope is **strictly after original attempt start and before the
job's frozen IANA local-day end**, capped by current time and original 90-day
analysis validity. Frozen boundaries are checked against the real IANA day.
This is a technical positive-evidence scope, not an experiment attribution
window or a product restart/cooldown rule. Original positive XP and reviewed server completion receipts must corroborate
one another through the bounded account-learning reader; lesson results also
require matching canonical course progress. Native/Desktop lesson metadata must
still prove successful nonduplicate awarding, Mini App lessons require their
server target/order, and practice needs its canonical scored session/mode.
Bonus XP, generic opens, another lesson/course, missing/malformed/unsupported
receipts, future results and old XP replayed later do not qualify. Original XP
time is retained; late receipt arrival cannot create a new completion. Repeated
reads/receipts return the same target result without a new count or stored fact.

The result contains only a fixed target-lesson reason, optional original
boundary/learning/report timestamps, a partial verified-unit count and explicit
source limitations, with no device, lesson text, token or payload. Account-level learning may occur on a different endpoint from the
contact; no same-device claim is made. Reviewed lesson/practice coverage is partial; generic opens, unsupported
study sources and complete negative outcomes remain unknown.
Missing/over-limit evidence returns unavailable rather than zero, inactivity or
permission to send again. This temporal link is not causal or notification-attributed learning, a
funnel/cohort denominator, recovery rate or D09 ML gate.
Trustworthy job-bound opening, other learning sources, complete measurement
and reviewed cohort/window policy remain parent 6.1/6.2 work.

## Verified temporal study outcomes

**Tapping a notification is never required to count actual study.** A learner
may see a reminder and independently open the app: original verified study after
the contact still counts. Client-report data is optional secondary evidence and
cannot gate primary learning/retention cohort KPIs. An ordinary app open alone
is not a completed study unit. Causal benefit requires the reviewed account-level
control/treatment evaluation under D12, independently of clicks.

The bounded account reader covers reviewed `course_v3`, `android_course` and
`desktop_course` lesson completions, plus canonical `course_miniapp` mock,
placement and training completions. Existing original positive unique XP must
match trusted server terminal receipts by canonical account/course/reference.
Lesson progress must corroborate completion; native result metadata must agree
with the original award, and practice mode/session/score must be valid. Terminal
completion events cannot be submitted through the client telemetry endpoint.
Bonus XP, generic opens, unowned/unsupported sources, malformed or unpaired
results, late old XP and over-limit windows do not become new completed units.
Practice may record its server result before awarding XP; the original XP time
remains authoritative. Existing learning writers, policy, habit and destination
readers are unchanged. These sources remain incomplete, especially for repeated
study with an already-deduplicated lifetime reference; absence never proves no
study or permits another reminder.

Migration `0141_smart_study_analysis` extends only existing raw/monthly stage
constraints for two explicit temporal facts:

| Stage | Meaning |
| --- | --- |
| `verified_study_after_attempt` | Original verified completed unit strictly after an evidenced accepted/posted contact and before its frozen local-day end; **no open report is required** |
| `verified_study_after_report` | The same unit also follows that original attempt's retained authenticated client report, using the report's first server-received time |

The original frozen IANA day and D21 age are technical source scopes, not an
experiment attribution window. Facts use original XP time and an opaque hash of
job/original canonical study reference/stage. Repeat capture cannot move time,
extend expiry or increment again. Monthly grain is verified unit/stage/UTC month/
**reminder contact channel**, not a unique learner, learning device, causal return
or complete recovery rate. Store no XP amount, lesson/practice reference, result
payload, device/session or report proof in analysis.

The existing optional default-OFF source capture and bounded reconciliation call
the same validated projection after delivery commits. No new learning-writer hook,
producer, poller, endpoint, cadence input or provider is introduced. Missing/later
or wrong-attempt/channel/reason/future report cannot create an after-report fact;
it does not suppress the study-after-attempt fact. The projection keeps its old
target-only `reason`/`learned_at`, and adds `reported_open_at`, `first_study_at`,
`first_study_after_report_at`, and `verified_study_count`. Missing evidence is
`None`, never a fabricated zero or negative-learning outcome.

D21 original-time 90-day raw expiry, twelve-month anonymous totals, atomic
increment and canonical purge cover both stages. Submitted deletion prevents
recreation and blocked accounts gain no new study detail. Populated downgrade
refuses either new raw or anonymous-only stage before changing constraints;
old facts/source survive empty-new-stage roundtrips. The reviewed empty-QA head
is 0141; no remote initializer/migration or activation is performed. Existing
source facts can recover later, but incomplete coverage/causal/cohort policy and
D09 calibration remain open. Disable analysis for rollback while retaining all
operational and already recorded evidence.

## Positive scored active-study days

`0142_smart_activity_analysis` adds only `study_day_after_attempt` and
`study_day_after_report` to existing raw/monthly stage constraints. These are
positive activity-day facts, distinct from original-XP completed-unit counts.
A failed graded attempt or genuine repeated study without fresh XP can prove
activity; merely opening a client cannot. Notification tapping is optional.

The analysis-only bounded reader covers server-only `section_attempt_scored`
from `course_miniapp` (owned canonical lesson/course/order, server UUID key and
strict correct/total), `test_completed` from `course_hsk_exam` (owned canonical
session/dedupe/material and strict score/total), and owned `course_attempts`
quiz rows joined to their course lesson, marked `miniapp_server_graded` with
strict score/total. It also covers retained `test_completed`/`training_completed`
from the shared `CourseMiniAppPracticeService` used by Mini App, Android and
both Desktop platforms. These require canonical owner/legacy course, exact
`course_miniapp` source, matching mock/placement/training event/mode/skill,
version-1 session scope and original writer dedupe, with strict score/total.
No passing threshold or fresh XP is required for this activity source. It
uses the original retained server result time; it does not create a new
completed unit or alter existing XP/habit/progress verification. Future
protocol versions and noncanonical session scopes remain unreviewed.
Boolean/string scores, zero/invalid totals, percent-only,
client section completion, AI/homework, foreign sources and mismatched lessons
are excluded. No passing threshold or fresh XP is required. The existing
completed-unit reader/writers, grades, access, habit and cadence are unchanged.

Union scored times with independently verified completed-unit times in the
existing evidenced contact/frozen IANA local-day scope. Optional projection
fields `first_active_study_at` and `first_active_study_after_report_at` remain
`None` when unavailable. Each source query has a 512-row sentinel bound;
over-limit classes are withheld, while an independently verified other class
can still prove a positive day. Payload reads are finite (8K server events,
64K quiz JSON); no answers, scores, source IDs or payloads persist in analysis.
Untraced deterministic v1 repeat completions still lack fresh-attempt proof;
the general profile event `practice_attempt_scored` still has no writer. Other voice and
unreviewed sources remain unavailable. A previously missing stored completion
can establish activity when the actual grader later persists it even though
the original award is older; an already deduplicated old result cannot move
to a later retry time. This is retained-completion coverage, not complete
repeat-practice history. Absence never proves inactivity.

Optional repeat capture reuses `SMART_REMINDER_ANALYSIS_ENABLED=false` without
adding a flag or enabling delivery. With explicit true, the shared Mini App,
Android and paired Desktop grader records server-only
`smart_practice_attempt_started` / `smart_practice_attempt_scored`, exact source
`smart_practice_v2`. A persisted start returns compact opaque
`practice:{owner}:v2:{32 lowercase hex nonce}`; failed capture returns existing v1.
Disabled new starts do no trace SQL. The receipt binds canonical owner, source,
mode/course/skill, frozen language/max-part (including unrestricted None), question
count/digest and original start time. Completion rejects foreign/missing/future,
90-day-expired or changed-material receipts and regrades server questions. Existing
ad/daily gates, canonical v1 terminal/reward references and XP dedupe remain intact.
An outstanding v2 completion may read its receipt after flag OFF for normal grading;
no new trace is captured then. Current clients roundtrip opaque IDs unchanged.

Scored traces require exact source/event/owner/course, v2 nonce/dedupe, integer
protocol 2, reviewed mode/skill, strict score/total and aware ordered start/score
within the receipt lifetime. Stored same-nonce retries preserve original retained
time/score; actual new starts can establish activity despite zero new XP. Scored
capture remains best effort and cannot undo learning. Missing first capture cannot
reconstruct a first human-attempt timestamp; a later successful server-grading
capture is the first retained proof, and global practice history stays partial.
These names never enter the general profile-accuracy event set. The new minimal
payload contains no questions, submitted answers, mistake text, job or provider
secrets. Both technical trace types expire after D21's 90 days in narrowly scoped
bounded pages of existing analysis retention, including the explicit count-only /
purge operator path. Original learning, XP, anonymous totals and operational
consent/day evidence remain protected; canonical account purge removes own traces.
No schema, client field, UI text, polling loop or source-stage constraint is added.

Completed voice activity additionally reads minimal fields of existing canonical
`voice_practice_sessions`: exact owned `user_id`, UUID-v4 identity, reviewed HSK
course, turn/live mode, completed status and positive server turn count. The
shared service increments turns only after server replies or the authenticated
server-side Live provider relay. It needs neither fresh XP nor the separate
seven-turn UI milestone. The ordered start/end must both be inside the requested
observation window; the original end is a conservative completion timestamp,
not an exact turn time, passing grade or acoustic score. Closing an older
pre-window conversation cannot create new in-window evidence. Canonical ownership
wins over stale Telegram metadata; legacy NULL-owner/band/unfinished/abandoned
sessions and standalone pronunciation remain unavailable. No history, correction,
word, plan, audio, usage/billing or provider-session content is read. A separate
512+1 sentinel sets `completed_voice_over_limit` and withholds that source only;
other reviewed evidence may still prove activity. Internal coverage names now
say `partial_practice_and_voice_unavailable`; this is partial coverage,
never absence or inactivity. The existing day/24-hour/baseline/D21 consumers reuse
these timestamps without adding a completed unit or changing habits/source writers.

The raw identity hashes owned job/day-stage, not individual attempts/questions;
at most one primary and one secondary day fact exists per owned job's frozen
day. Store original first-observed source time and D21 expiry, never rewrite it
when earlier evidence arrives later. Monthly counts are observed job/day/stage/
UTC-month/**reminder channel**, not all-account active days, unique learners,
learning devices, a cohort denominator or causal returns. A first activity
before a report does not prevent a later activity establishing the secondary
day. Missing/late/invalid reports never suppress the primary day.

Existing default-OFF capture/reconciliation, atomic insert/monthly dedupe,
retention and canonical purge apply. Block/deletion guards prevent new detail.
0142 preserves older facts and refuses raw or anonymous-only new-stage
downgrade. The reviewed empty-QA head is 0142; no remote migration/initializer
or activation follows. No new endpoint, flag, poller, grade writer or provider.
Disable analysis for rollback while retaining operational and observed facts.

The owner selected **24 hours after contact**, including midnight crossover.
Local-day technical facts stay separate from the 24-hour contact/global-unit
observation below. Real cohort measurement remains 6.2 work, without a click
gate or timing-only causal attribution.

## Owner-selected 24-hour temporal study window

`return_learning(user_id, job_id)` is a separate internal read-only projection.
It reuses the same User-first owner/block/deletion and original accepted/posted
contact proof as the local-day reader. The contact start must lie inside its
valid frozen IANA day. The interval is **(original attempt start, start + 24
elapsed UTC hours]**, capped at the current observation time. A 23:50 contact
can therefore include 00:10 study; DST's 23/25-hour local days do not alter the
24-hour duration. This is a server-attempt boundary, not an independently
verified display time. Clicking/reporting is never required, and open-proof
validity and older local-day stages remain unchanged.

The projection returns fixed reason, optional `contact_at`, `window_end_at`,
`first_study_at`, `verified_study_count`, `window_elapsed` and coverage limits.
A positive can appear before the window ends. `window_elapsed` describes time
only; it never means complete coverage, zero study or a verified unsuccessful
reminder. Missing results/counts remain None. Reuse reviewed completed-unit and
scored-activity readers, with their separate finite source limits. For original
completed units only, later server receipts observed by now may corroborate
in-window original XP; the XP cutoff/time does not move. Other reader callers
retain their original default evidence cutoff. No new grade/XP source writer,
repeat-practice/voice coverage, cadence input or cohort is invented.

0143 extends only the existing raw/monthly stage constraints:

| Stage | Grain and interpretation |
| --- | --- |
| `contact_study_24h` | One evidenced owned job/contact window with reviewed positive study, including failed/repeated graded work without fresh XP |
| `study_unit_24h` | One original canonical owner/activity-type/reference completed unit across **all** overlapping qualifying jobs/channels |

Contact-window facts hash the original job/stage; global unit facts hash the
canonical owner/type/reference/stage without the job or channel. Owner-first
capture and the existing owner/key conflict guard atomically deduplicate units
under reverse-order, concurrent or later-confirmed contacts. The first captured
qualifying job/channel stays immutable descriptive provenance; it is neither
latest-contact nor causal attribution. Per-window projections can each contain
the same unit, but persisted global unit totals increment once. Two overlapping
contacts may each have positive windows: that is two contact facts, **not two
unique returns/learners or units**. Never sum these grains together, compare
contact-channel counts as causal performance, or use them as a cohort denominator.
Primary 6.2 learning/retention KPIs must independently deduplicate canonical
account learning, including no-contact/control learners, without a click gate.

Original first-observed study time controls raw expiry and anonymous UTC month;
contact counts are bucketed by that study time, not a contact-cohort month. No
plaintext reference, score, answer, payload, device or proof is added. Existing
default-OFF capture/reconciliation, atomic monthly totals, D21 90-day detail and
twelve-month buckets, block/deletion guards and canonical purge apply. Earlier
captured rows/times are not rewritten. The 0143 populated downgrade refuses raw
or anonymous-only new stages; old populated data/model parity survive a clean
roundtrip. Reviewed empty local-QA head is 0143. Disable analysis for rollback,
retain original operational proof/owner/day state, and never delete a contact
source merely to reassign a global fact. No new endpoint, flag, scheduler,
provider, send authority, client change or production activation is introduced.
This implements bounded positive 24-hour source observation; real cohort
baseline, complete coverage and causal benefit remain separate acceptance work.

## Retention and privacy boundary

| Class | Policy |
| --- | --- |
| Optional Smart practice start/scored traces | D21: original trace time + 90 days; source/version/name scoped bounded cleanup, hard start expiry, no canonical learning deletion |
| New analysis / reservation detail | D21: expires at original source time + 90 days |
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
the reviewed 0141 schema and enables observation/analysis-only retention, never
study dispatch, admission, enrollment or a provider. Android's successful claim
or receipt schedules only owner/job metadata in a Starlette background callback:
the source transaction/session has closed and the complete HTTP body is sent
before capture. GET, malformed/foreign/unauthenticated requests and nonmutating
refused claims schedule no capture; reviewed committed guard refusals use the
bounded path described above. No request, bearer or claim body is retained.

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
counts only. `--purge-expired --limit 128` explicitly removes at most one job-detail page,
one reservation-detail page and one monthly page; valid limits are 1–128. It never deletes a source
job, attempt, grant, preference, course/XP record or another non-analysis class.
The enabled task or operator must run enough pages to drain a backlog; no live
production execution is implied. Source-time checks refuse expired replay after raw
deletion, and never recreate an old fact to increment totals again.

No initializer is run against an existing database. The reviewed empty-QA
initializer reviewed head is 0144 and leaves migration-owned tables to real migrations.
Migration 0137 downgrade refuses either populated analysis table rather than
deleting data; 0138 uses the new-stage preservation guard described above.
Disabling capture changes no delivery authority; preserve all consent/day/grant
guards and operational evidence during rollback.


## First-ready baseline cohorts

0144 adds separate minimal first-ready membership and original anonymous cohort
denominators through the existing default-OFF source observer/reconciliation,
retention and canonical purge. Source/metric boundaries, account-wide historical
receipt checks and explicit unavailable/partial states are documented in
`SMART_REMINDER_BASELINE.md`; no contact/open or delivery authority follows.
