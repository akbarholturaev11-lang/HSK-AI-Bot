# Smart Reminder Operations — Spec Delta

## Purpose

Govern safe rollout, reversible delivery, privacy, source-backed learning outcomes and protected administration of Smart Reminders. These requirements describe proposed observable behavior, not a deployed service or a claim that real-client acceptance has passed.

## ADDED Requirements

### Requirement: Evidence-gated cutover
The system SHALL move eligible accounts from legacy study senders to Smart dispatch only after their consent sources, client capabilities and competing senders are reconciled. A shadow or disabled rollout MUST create no user-visible Smart notification. An account MUST NOT run both independent old and new study paths during cutover.

#### Scenario: Shadow evaluation
- **WHEN** a cohort is selected for policy comparison while Smart dispatch is disabled
- **THEN** decisions and suppression reasons can be compared without a Smart provider attempt or Android local post authorized by the new service

#### Scenario: Unsupported older installation
- **WHEN** an account may still have an offline old Android installation able to post locally without a server claim
- **THEN** that account stays out of cross-channel cutover until verified fencing or another safe migration condition is met; the system reports no physical-display guarantee for the old installation

#### Scenario: Two workers during canary
- **WHEN** two scheduler processes evaluate one eligible account and local day concurrently
- **THEN** at most one new study job gains delivery authority and the prior server study sender cannot independently dispatch for that migrated account

### Requirement: Fail-safe rollback
The system SHALL have a server-controlled Smart dispatch stop that prevents new attempts, expires pending jobs and invalidates outstanding new grants without deleting explicit OFF, consent provenance or revisions. Legacy senders MUST resume only after a fresh account/channel eligibility and day-budget check; uncertain attempts MUST NOT be replayed.

#### Scenario: Rollback after account opt-out
- **WHEN** a learner turns study OFF and an operator later disables Smart dispatch
- **THEN** no old or new study sender re-enables or sends to that learner; the OFF revision remains visible on all compatible clients

#### Scenario: Rollback with unconfirmed provider attempt
- **WHEN** an FCM provider accepted a job but client display is unknown before rollback
- **THEN** rollback records an ambiguous outcome and authorizes no replacement Telegram study send for that job

#### Scenario: Schema reversal would lose consent evidence
- **WHEN** a downgrade would drop nonempty Smart preference, job, attempt or opt-out history
- **THEN** the downgrade is refused until a separately reviewed, non-destructive preservation procedure exists

### Requirement: Data minimization and account deletion
Smart Reminder SHALL retain only necessary personal learning, consent, job and outcome data with finite class-specific retention. Expired detail MUST be removed or reduced to privacy-safe aggregates. Account deletion or device revocation MUST cancel applicable queued jobs and derived personal features; financial retention and transactional notices remain separately governed.

#### Scenario: Retention expiry
- **WHEN** the approved retention period for a raw attempt or learning-response class expires
- **THEN** identifiable detail is deleted or irreversibly minimized while only permitted summary data remains; no indefinite raw clickstream accumulates

#### Scenario: Deletion submitted before dispatch
- **WHEN** a learner has a pending account-deletion request or completed purge while a study job is queued
- **THEN** that account receives no later new Smart attempt, and purge removes personal jobs, attempts, capabilities, tokens and derived habit features under the account-deletion contract

#### Scenario: Device revoked during claim
- **WHEN** a device is revoked, logged out or transferred before it uses a study grant
- **THEN** its grant and receipt authority fail, no wrong-account post is authorized, and no personal capability remains eligible

### Requirement: Truthful delivery and learning attribution
Operations SHALL distinguish scheduled, suppressed, provider attempted/accepted, verified client action, OS display when independently evidenced, opened and server-confirmed learning. Missing evidence MUST remain unknown. A notification open or existing Mini App open proxy MUST NOT be counted as causal study return or lesson completion.

#### Scenario: Provider accepted without display proof
- **WHEN** FCM accepts a hint or Telegram accepts a send but no credible display/read signal exists
- **THEN** the result is accepted or unconfirmed, not shown, read or learned

#### Scenario: Open without studying
- **WHEN** a learner opens the Mini App from a reminder but makes no server-confirmed study progress
- **THEN** open is reported separately and learning-reactivation/completion counts do not increase

#### Scenario: Late or repeated learning event
- **WHEN** the same canonical lesson result is replayed or recorded after its attribution window
- **THEN** results remain deduplicated by canonical account and are attributed only within the documented cohort and window

### Requirement: Protected minimal administration
The existing Admin PWA SHALL offer one simple Smart control and statistics surface with an authorized kill switch, existing localized template edit/preview and real counts for sent, suppressed, opted out and verified learning return. It MUST follow the existing passkey, audit, minimal-action and private analytics contracts; absent or immature data MUST be shown as unavailable, not zero or invented success.

#### Scenario: Authorized operator stops dispatch
- **WHEN** an authorized operator executes the existing protected command for the Smart kill switch
- **THEN** the stop takes effect on live dispatch authority, is audited and does not depend on a 24-hour analytics cache refresh

#### Scenario: Uninstrumented metric
- **WHEN** there is no mature Smart learning-outcome cohort or reliable display signal
- **THEN** the UI shows an explicit unavailable/collecting state with population, time-window and snapshot age; it does not present a fabricated rate

#### Scenario: Unauthorized read or edit
- **WHEN** an admin session is missing, revoked or lacks the required role during a read, cache wait, template change or kill-switch action
- **THEN** private metrics and control are denied without revealing learner records or command authority

#### Scenario: Learner and administrator push separation
- **WHEN** the Admin PWA's own notification capability exists
- **THEN** it is not treated as learner Web Push consent, learner device eligibility or a Smart delivery adapter

### Requirement: Baseline-grounded experimentation
Before enabling a Smart experiment, operations MUST measure actual eligible traffic and learning baseline, define cohort origin, denominators, observation window, guardrails and a powered MDE/sample-size/duration plan. Account-level assignment MUST be stable; existing D1 recovery holdouts and controls MUST never receive a treatment study send through another channel. Underpowered results MUST NOT be called a win.

#### Scenario: Insufficient baseline or traffic
- **WHEN** eligible cohort volume or mature learning observations cannot support a target or duration
- **THEN** no invented uplift percentage, fixed trial length or positive experiment result is displayed or used to enable rollout

#### Scenario: Existing D1 holdout intersects pilot
- **WHEN** a canonical account is in the existing D1 recovery control or another registered study holdout
- **THEN** the Smart policy respects the applicable exclusion consistently across Telegram and Android without reassigning by device or Telegram ID

#### Scenario: Valid comparison
- **WHEN** a registered treatment/control experiment reaches its planned observation point
- **THEN** reporting uses all assigned eligible accounts, server-confirmed learning outcomes, real denominators and uncertainty; delivered-only responder selection is labeled diagnostic

#### Scenario: Technical personal-device canary
- **WHEN** an owner-selected account/device passes delivery, navigation and duplicate checks
- **THEN** operations records technical acceptance only; efficacy still requires a preregistered stable account-level randomized comparison and original all-assigned learning denominators

#### Scenario: Device changes during an A/B experiment
- **WHEN** an assigned canonical account reinstalls, changes devices or uses another eligible channel
- **THEN** its original arm/entry/version remain fixed, a protected holdout cannot receive treatment through an alternate or legacy sender, and unknown/absent response does not remove it from the denominator

### Requirement: Safe automatic optimizer progression
Eligible new and sparse-history learners SHALL receive useful deterministic rules immediately. ML decisions SHALL activate automatically for a user only after a globally validated model is safely enabled and that user's evidence satisfies a versioned quality gate. Stale evidence, model failure, regression or any conflict with consent, access, day budget or manual override MUST revert to rules without an extra notification.

#### Scenario: New learner without a model
- **WHEN** study consent and channel eligibility exist but no reliable model or sufficient personal evidence exists
- **THEN** the functioning rule policy decides the reminder without an AI activation prompt

#### Scenario: Quality gate crossed
- **WHEN** a validated model is released and a learner's verified data crosses the approved eligibility gate
- **THEN** optimization can switch to the model automatically, while existing consent and one-per-day limits still govern every decision

#### Scenario: Model degraded after activation
- **WHEN** model quality, freshness, availability or a safety guard fails
- **THEN** decisions fall back to rules for that user, preserving already reserved jobs and avoiding a second same-day attempt

#### Scenario: Habit estimate exists but ML calibration does not
- **WHEN** the rule estimator has three initial or five stable active days, but the model lacks validated admission thresholds
- **THEN** the habit estimate remains usable by rules and does not activate ML

#### Scenario: Incomplete model admission manifest
- **WHEN** a model lacks calibrated minimum usable days/results, maximum feature age, prediction confidence/uncertainty, learning advantage or applicable cohort coverage
- **THEN** ML remains unavailable; every missing threshold is an explicit blocker, not an invented universal day count or probability

#### Scenario: One prediction dimension is unproven
- **WHEN** the selected model has no reliable personal prediction or validated advantage for a time/content/channel/cadence dimension
- **THEN** that dimension keeps rules under the unchanged product guards, even if another dimension is eligible


### Requirement: Reconcile committed analysis independently of delivery
The system SHALL recover available committed Smart outcome facts after a missed observer callback through bounded source reconciliation and the existing source-stage deduplication. It MUST NOT resend, change delivery authority, erase original sources or infer complete coverage, display or learning from an analysis scan.

#### Scenario: Process interruption after committed native receipt
- **WHEN** a reviewed v1 receipt commits but its optional analysis callback is lost before capture
- **THEN** enabled reconciliation can recover the original source-time fact once without issuing a new posting grant or incrementing an already captured stage

#### Scenario: One owner is locked while other jobs await reconciliation
- **WHEN** a source capture exceeds the bounded reconciliation tick budget
- **THEN** its transaction is cancelled safely, later ticks can progress past that job, and a later pass can retry it without changing delivery or claiming the gap was measured

#### Scenario: Late outcome belongs to an old parent
- **WHEN** a retained reviewed job has expired reservation detail but a recent valid original attempt outcome or receipt
- **THEN** reconciliation considers that recent source and cannot recreate expired reservation detail or extend its retention


### Requirement: Distinguish observed shadow decisions from delivery
The system SHALL record available committed terminal shadow decisions with their fixed server reasons using explicit shadow stages. It MUST preserve existing source-stage deduplication and retention without treating a simulation as a real send, complete candidate denominator or permission to dispatch.

#### Scenario: Repeated observation of a completed shadow candidate
- **WHEN** multiple analysis workers observe the same committed unattempted shadow candidate
- **THEN** its terminal shadow fact and anonymous stage total are counted once without recording a delivery stage or creating an attempt

#### Scenario: Actual shadow refusal after scheduling
- **WHEN** goal completion, OFF, access, cadence or another reviewed guard commits a terminal refusal on an owned shadow job
- **THEN** analysis can record that original reason as shadow suppression without inventing a display/nonresponse outcome

#### Scenario: Refusal occurred before any durable job
- **WHEN** policy refuses a candidate before a source job exists
- **THEN** missing shadow-job analysis remains unavailable and cannot be used as measured zero or a complete denominator


### Requirement: Observe pre-reservation shadow refusals without creating a job
The system SHALL optionally record an actual verified shadow reservation/refusal after the source transaction commits, using minimal finite-retention data and fixed server reasons. Observation MUST NOT create a study intent for a refusal, change the source result or authorize delivery.

#### Scenario: OFF or D1 refuses before reservation
- **WHEN** a verified owned reserve operation returns an actual OFF, D1 or other reviewed guard refusal before creating a job
- **THEN** enabled analysis may retain that reason once in its documented account/day/revision/course grain with no job, attempt or provider operation

#### Scenario: Analysis fails after reservation commits
- **WHEN** optional observation fails or times out after a shadow job commits
- **THEN** the original source result remains successful, no reserve retry occurs and missing capture remains unavailable

#### Scenario: Repeated reserve checks on the same scope
- **WHEN** callers repeat the same observed outcome/reason within the same frozen scope
- **THEN** capture does not increment anonymous totals again or extend the first observation's retention


### Requirement: Preserve committed runtime guard reasons without changing dispatch
The system SHALL retain reviewed original reasons for committed selected-job cancellation/expiry in analysis, using existing terminal stage identity/time and source ownership. It MUST NOT infer non-display from a cancellation reason, expose arbitrary source text, change delivery or count a retry twice.

#### Scenario: Goal completed before native claim or Telegram send
- **WHEN** current server learning causes a reviewed runtime job to commit a guard cancellation before authorized posting/provider IO
- **THEN** optional post-commit capture can retain the original guard reason once and no additional grant, attempt or provider call is created by observation

#### Scenario: Unknown or mismatched terminal reason
- **WHEN** stored terminal text has no reviewed reason for the selected channel
- **THEN** analysis retains only its fixed generic stage reason without copying arbitrary text or inventing display evidence

#### Scenario: Transient refusal without terminal source evidence
- **WHEN** auth, admission, not-due or another transient guard returns without a committed terminal decision
- **THEN** that response does not become a measured terminal suppression or complete denominator


### Requirement: Separate temporal server learning from notification attribution
The system SHALL support an internal bounded source projection of original verified target learning after an evidenced study contact attempt, without representing temporal proximity as notification opening, display, causal return or complete negative-learning coverage.

#### Scenario: Original target lesson completed after an evidenced contact
- **WHEN** the same canonical account has a successful original server-confirmed target lesson result strictly after a reviewed accepted/posted contact attempt and within its frozen local day
- **THEN** internal analysis may return the original result time with explicit partial source coverage and without changing or persisting delivery state

#### Scenario: Missing or replayed learning evidence
- **WHEN** only generic app opens, bonus XP, a pre-attempt original result replayed later, another target or unsupported/missing sources exist
- **THEN** the projection returns unavailable evidence rather than zero learning, an attributed completion or a reason to send again


### Requirement: Authenticated job-bound client-reported opens
The system SHALL optionally record a client-reported reminder open only with a valid original delivery-bound proof and current owning authentication. It MUST distinguish that report from independent display/open proof, server learning and causal return, preserve delivery authority and minimize retained data.

#### Scenario: Owning native notification or Telegram link is opened
- **WHEN** an authenticated owning client reports the original accepted/posted reminder proof within its frozen local day
- **THEN** one explicit client-reported-open fact and anonymous bucket may be recorded without a new send, access grant or lesson completion

#### Scenario: Repeated, forged or transferred proof
- **WHEN** a proof is replayed, forged, used by another owner/native session, or lacks a confirmed contact source
- **THEN** it cannot increase the count again, extend retention, cross account boundaries or authorize any delivery

#### Scenario: Missing or disabled observation
- **WHEN** analysis is disabled, metadata is absent, or best-effort reporting fails
- **THEN** existing navigation and delivery continue and open/learning coverage remains unknown


### Requirement: Source-verified temporal learning facts
The system SHALL optionally count deduplicated original server-confirmed study units after an evidenced reminder attempt and, separately, after its retained client report. It MUST preserve original result time, partial coverage and account ownership without treating order as causal return, granting delivery or inferring inactivity.

#### Scenario: Real lesson or practice result after contact and report
- **WHEN** a canonical original positive XP result matches a reviewed server completion source after a confirmed contact within its frozen local day
- **THEN** one temporal study fact may be recorded, with a separate after-report fact only when the same attempt's original server-received report precedes the result

#### Scenario: Replayed, unsupported or missing evidence
- **WHEN** an old result arrives again, source pairing fails, the report is missing/late/unrelated, or coverage exceeds finite bounds
- **THEN** no false later completion or after-report fact is created, retries cannot inflate counts and missing coverage cannot authorize another message


#### Scenario: Learner returns manually without tapping the reminder
- **WHEN** a learner sees a reminder, opens the app independently and completes original server-confirmed study without any notification-open report
- **THEN** the verified study-after-attempt result still counts; tapping/reporting is only an optional secondary sequence signal and must not gate actual learning or primary cohort KPIs


### Requirement: Scored activity days without fresh XP
The system SHALL optionally record separate temporal active-study-day evidence from reviewed server-graded work, including failed or repeated attempts without fresh XP. It MUST preserve completed-unit semantics, source ownership, bounded partial coverage and existing delivery authority.

#### Scenario: Manual return followed by repeated or failed study
- **WHEN** an owning learner performs a reviewed server-graded attempt after an evidenced contact within the frozen source day, without tapping or earning new XP
- **THEN** one primary study-day fact may be recorded without inventing a successful completed unit, and further attempts in the same job/day cannot inflate that day

#### Scenario: Activity before and after the optional report
- **WHEN** one verified activity precedes a retained owning report and another follows it
- **THEN** the primary day remains independent of reporting and the later activity may establish one separate after-report day

#### Scenario: Untrusted or incomplete activity coverage
- **WHEN** only client telemetry, AI/homework, malformed scores, foreign sources or unavailable source classes exist
- **THEN** those rows do not prove a study day or inactivity; source gaps remain explicit and cannot authorize delivery


### Requirement: A distinct 24-hour temporal study window
The system SHALL observe reviewed study strictly after an evidenced original contact-attempt start and at or before 24 elapsed hours later, independently of local midnight, DST and notification tapping. It MUST preserve older local-day source facts and distinguish positive contact windows from globally deduplicated original completed units and future account-level cohort KPIs.

#### Scenario: Manual return after midnight
- **WHEN** an owning learner receives an evidenced contact at 23:50 and performs verified study at 00:10 within 24 elapsed hours without an open report
- **THEN** the separate 24-hour projection and optional positive contact fact can count that study while older local-day facts keep their original scope

#### Scenario: Overlapping contacts observe the same completed unit
- **WHEN** two qualifying contact windows include the same original canonical study result and capture runs in either order or concurrently
- **THEN** each contact may have a positive window but the canonical completed unit increments once globally; the first captured contact is immutable descriptive provenance, never causal or latest-contact attribution

#### Scenario: Boundary or missing evidence
- **WHEN** a result is at/before contact start, after 24 hours, in the future, unsupported, or absent from partial sources
- **THEN** no false positive unit/contact or negative-learning claim is created; window elapsed is distinct from complete coverage and cannot authorize delivery


### Requirement: First-ready canonical baseline cohorts
The system SHALL optionally record one first reviewed policy-ready entry per canonical account/protocol independently of notification sending or opening, and measure observed learning over versioned frozen local-calendar windows. It MUST preserve original anonymous enrollment denominators through personal deletion/expiry and cannot treat the resulting partial observations as causal lift or delivery authority.

#### Scenario: Existing learner first becomes policy ready
- **WHEN** an existing learner obtains a reviewed committed base-policy-ready shadow reservation
- **THEN** optional analysis may retain the earliest reviewed entry once and count subsequent verified learning without a contact/open requirement, while leaving consent and dispatch unchanged

#### Scenario: Purged, immature or incomplete cohort
- **WHEN** a member is purged/blocked, follow-up is unfinished, or bounded source coverage is unavailable
- **THEN** the original anonymous denominator remains intact and unavailable/censored states are explicit; missing data cannot become a favorable exclusion, inactivity finding or model-ready result

#### Scenario: Courses change and reminders are ignored
- **WHEN** a member studies another canonical course or enters manually without touching a reminder
- **THEN** original reviewed server-completed units and scored study can contribute account-wide without relying on notification clicks or mutable current-course progress

### Requirement: Bounded durable mature baseline outcomes
The system SHALL incrementally observe mature baseline members in bounded independent pages and atomically preserve anonymous monthly lower-bound outcomes beyond personal-detail expiry. Reports MUST retain the original denominator, disclose unobserved/limited coverage and remain independent of cohort size, contacts and taps.

#### Scenario: A cohort exceeds one page
- **WHEN** more than 128 accounts belong to a baseline month
- **THEN** repeated bounded passes can observe them all without truncating the original denominator, while a read-only report uses aggregate counts rather than unbounded personal learning reads

#### Scenario: Retry, later proof or concurrent observation
- **WHEN** an account is observed again, including by concurrent workers or after a later retained server receipt
- **THEN** anonymous totals add only newly proven nonnegative lower-bound deltas and count the mature observed account once, with snapshot/counter failure rolling back atomically

#### Scenario: Personal detail is removed
- **WHEN** observed membership expires or its account is purged
- **THEN** original anonymous enrollment and already recorded outcomes survive their twelve-month retention without membership resurrection, personal learning reads or any claim of complete retention, causal lift or delivery authority

### Requirement: Explicit read-only operator baseline report
The system SHALL provide an explicit one-month anonymous operator report with database-enforced read-only connections, bounded execution and secret-free failures. It MUST preserve unavailable/partial baseline states and cannot initialize storage, aggregate personal outcomes or activate sending.

#### Scenario: Explicit target and valid month
- **WHEN** an authorized operator supplies a supported database target separately from command arguments and an exact cohort month
- **THEN** the report returns only the existing anonymous projection through a dedicated read-only connection, preserving original denominators and false experiment/dispatch readiness

#### Scenario: Missing target, schema or observation
- **WHEN** target access, required storage or recorded cohort evidence is absent
- **THEN** no application database fallback, migration, invented zero retention or success claim occurs; errors expose stable codes without URLs, credentials, SQL or tracebacks

#### Scenario: Accidental write or interrupted report
- **WHEN** a reporting operation attempts a database write, times out or is cancelled
- **THEN** the read-only database policy refuses writes and the dedicated resources are released without changing operational or personal learning sources

### Requirement: Existing graded practice can prove activity without fresh XP
The system SHALL count a reviewed stored server-graded practice completion as positive study activity independently of a new XP award or notification tap. It MUST preserve original-unit/reward semantics, strict source/session validation and explicit incomplete repeat-practice coverage.

#### Scenario: Graded completion after the original reward
- **WHEN** canonical mock, placement or training completion is server-verified after contact while its original XP is older
- **THEN** positive study-day/window evidence may be observed without inventing a new completed unit, rewriting the original result or requiring a click

#### Scenario: Missing or untrusted practice evidence
- **WHEN** only a deduplicated older completion, client telemetry, malformed score or mismatched owner/course/session exists
- **THEN** it cannot create a new in-window positive result or prove inactivity, causal learning, complete practice coverage or dispatch readiness


### Requirement: Completed server voice activity remains private and partial
The system SHALL recognize reviewed nonempty canonical server voice completions as positive activity without a notification tap or fresh XP. It MUST use original conservative completion times, preserve source/reward rules and leave incomplete voice coverage explicit without exposing conversation content.

#### Scenario: Nonempty server conversation completed inside the window
- **WHEN** the owned reviewed session has verified server turns and ordered start/end entirely inside the observation window
- **THEN** positive day/window evidence may be observed without inventing a completed unit, passing grade or exact per-turn timestamp

#### Scenario: Empty or ambiguous conversation
- **WHEN** a session is empty, unfinished, foreign, legacy ownerless, outside the window or exceeds the finite source bound
- **THEN** it cannot establish fresh in-window activity, inactivity or delivery readiness and no transcript/audio is read or persisted by analysis


### Requirement: Repeat study activity preserves original rewards
The system SHALL optionally distinguish a newly server-started and server-graded practice attempt from a retained retry without granting another original reward. New observation must remain private, bounded and separate from existing learning/profile/delivery contracts.

#### Scenario: Genuine repeat after the original reward
- **WHEN** the owner starts another supported practice and the server verifies its bound questions and answers
- **THEN** positive study activity may be observed once for that attempt while original terminal/XP identity and access checks remain intact

#### Scenario: Disabled, untrusted or expired attempt
- **WHEN** optional capture is disabled or fails, or a supplied attempt is foreign, missing, expired or mismatched
- **THEN** capture cannot create consent, delivery, another reward or a false complete-history claim, and invalid identities cannot establish fresh verified activity

#### Scenario: Technical trace retention
- **WHEN** an owned technical practice trace reaches its ninety-day lifetime or its account is purged
- **THEN** only that scoped detail is removed without deleting canonical course, XP or anonymous retained analysis totals


### Requirement: One protected Admin Smart control
The system SHALL provide one protected Smart editor using existing template consent, passkey, revision and audit rules. Disabling it MUST veto new Android and Telegram Smart attempts without erasing existing outcomes or enabling another sender.

#### Scenario: Fresh disabled permission
- **WHEN** a prepared Smart attempt encounters the current disabled admin permission before externalization
- **THEN** new issuance/send is refused while original receipts, account OFF, day ownership and unknown outcomes remain protected

#### Scenario: Anonymous partial readout
- **WHEN** an authenticated admin opens Smart management
- **THEN** only reviewed anonymous month counters and observation status are shown, missing values stay unknown, real zero stays zero and no display, unique-user, causal or activation claim is invented

#### Scenario: Minimal editor interaction
- **WHEN** the persisted permission or copy changes
- **THEN** the existing single Save performs exact passkey verification and audit, reversion disables Save, and only confirmed success dismisses after the existing success animation

### Requirement: Offline model comparison preserves temporal and product boundaries
The system SHALL compare a versioned candidate with functioning personalized rules using only earlier available features and training labels, and report later held-out observations as private aggregate diagnostics. It MUST preserve product guards and unknown outcomes and cannot grant model or dispatch authority.

#### Scenario: Later proof cannot improve an earlier prediction
- **WHEN** a study proof or target label becomes available after the snapshot or training cutoff
- **THEN** it cannot enter that earlier feature/training set, and later evaluation is not refit using its outcomes

#### Scenario: Sparse or unsupported coverage
- **WHEN** data is expired, limited, manual, unobserved, too small or absent for a platform/language cohort
- **THEN** exclusions and unknown metrics remain explicit without identifying learners, inventing inactivity, lifting guards or claiming validated learning benefit

#### Scenario: Reproducible local diagnostic
- **WHEN** an operator runs the same bounded reviewed snapshot and fixed candidate configuration
- **THEN** the aggregate comparison is reproducible, model records remain transient, and no application data, settings or provider is changed

### Requirement: Integrated rules use the approved personal clock consistently
The system SHALL use the same approved personal-time rules and bounded calendar history for passive projection and integrated reminder validation, preserving manual locks and existing frozen day/clock ownership.

#### Scenario: Reliable existing personal history
- **WHEN** recent or approved extended verified history establishes a personal time different from the saved fallback
- **THEN** new rule-path decisions and their transport rechecks use that personal time without granting cadence, consent, admission or dispatch authority

#### Scenario: A pending job has a different frozen clock
- **WHEN** fresh personal history changes an unattempted job's validated clock
- **THEN** the existing context guard cancels it without moving its clock, refunding its day, replaying an externalized attempt or rejecting an original historical receipt

### Requirement: Planning binds one existing account intent without issuing delivery authority
The system SHALL reserve and bind one reviewed eligible destination using existing account-day ownership, personal rules and destination policy. Planning MUST NOT grant consent, enroll a cohort, send a provider request, create a posting grant or retarget selected/attempted work.

#### Scenario: One eligible phone
- **WHEN** current account rules and reviewed admission permit a single eligible Android endpoint
- **THEN** the planner binds that device without a destination-history warm-up and only its authenticated claim may subsequently issue posting authority

#### Scenario: Preferred endpoint or review changes
- **WHEN** fresh selection, account intent, routing review or capability changes during planning
- **THEN** no stale selection is bound and no alternate endpoint bypasses the existing review or consent gates

#### Scenario: Concurrent planning and restart
- **WHEN** planners race or repeat after a selected, attempted or terminal intent already owns the day
- **THEN** the original single day/endpoint/attempt evidence stays intact without reranking, refunding ownership or replaying delivery

### Requirement: Runtime registration preserves reviewed single-intent delivery boundaries
The system SHALL run planning and existing transport protocols only with explicit server-owned reviewed runtime dependencies, preserving disabled defaults, finite work and original attempt/receipt ownership.

#### Scenario: No ready registration
- **WHEN** the host has no matching ready runtime or authoritative dependencies
- **THEN** no runtime polling or provider IO starts, and native new posting authority stays disabled

#### Scenario: A due selected intent survives restart
- **WHEN** a reviewed selected intent is due after its original planning time
- **THEN** native retrieval or the existing committed Telegram protocol processes that original intent without another reservation, retargeting or replaying a started attempt

#### Scenario: Shutdown or runtime pause
- **WHEN** the host stops or runtime permission is removed
- **THEN** the runtime task is cancelled and awaited, new authority is suppressed at fresh boundaries, and original receipts and ambiguous attempt facts remain immutable

### Requirement: Eligible early return is not blocked by ended unknown intents
The system SHALL evaluate a new eligible local study day independently of an ended historical intent's unknown display outcome, preserving original intent ownership, weekly costs and evidence semantics.

#### Scenario: Daily learner misses the next habitual session
- **WHEN** verified daily learning history establishes a habitual local time and the next local day's learning is reliably absent
- **THEN** ordinary eligibility can begin on that next day despite small prior completion-time jitter or a DST-shortened day, without waiting a week or bypassing consent, coverage, access or budgets

#### Scenario: A prior day's delivery remains unknown
- **WHEN** the prior frozen intent window has ended and a separate nonoverlapping day is eligible
- **THEN** the original intent remains immutable and budget-counted, its unknown outcome is not an unsuccessful response, and it does not by itself veto the new intent

#### Scenario: Original window or budget still forbids another contact
- **WHEN** current/overlapping day ownership, a live unknown window or the rolling weekly ceiling applies
- **THEN** no duplicate, alternate delivery or additional study intent bypasses that guard

### Requirement: Native admission reads persisted privileged review
The system SHALL bind native admission to current persisted operator-reviewed fencing and actual native account/job/device/session state, without inferring review from client observations or requiring a Telegram identity.

#### Scenario: Native-only reviewed account
- **WHEN** a trusted operator holds and reviews a native-only account under its current owned native context and finite external fencing evidence
- **THEN** a read-only source may bind that stored review to an eligible owned native intent, without creating a Telegram identity, consent, attempt or posting grant

#### Scenario: Review or destination has changed
- **WHEN** review generation, inventory, permission, ownership, window or frozen intent is stale or incompatible
- **THEN** the persisted source supplies no fresh admission and cannot renew or replace that evidence from a capability/client request

#### Scenario: Historical attempt remains irreversible
- **WHEN** a later hold invalidates fresh work after an original native posting attempt
- **THEN** its day/attempt/receipt facts remain immutable and no regrant or alternate follows

### Requirement: Observed learning retains positive-only semantics
The system SHALL expose bounded canonical positive study observations for an owned account/window without asserting complete negative coverage, fresh unit awards or notification authority.

#### Scenario: Real study without new XP or notification tap
- **WHEN** an existing reviewed server-scored or completed voice record establishes actual account study within the observation window
- **THEN** its original positive activity time may contribute without a new XP award or notification tap, preserving existing source validation and private content

#### Scenario: Missing or limited observations
- **WHEN** retained sources are empty, partial, future, foreign or over the technical work bound
- **THEN** no absence/failure/complete-coverage claim is inferred, limits remain explicit, and no new permission or provider operation follows

### Requirement: Explicit ordinary reminder mode does not infer negative outcomes
The system SHALL permit owner-approved ordinary opted-in reminders from current canonical progress and observed positive study activity through an explicit rules/source profile, retaining all permissions, reviewed cohort/device, daily/weekly, access, quiet and irreversible intent guards.

#### Scenario: Complete negative history is unavailable
- **WHEN** the explicit observed profile has reliable prior rhythm, valid current target/permission/review and no observed current-day study or completed goal
- **THEN** a regular personal-time reminder may be prepared within the existing budgets without claiming abnormal inactivity or an unsuccessful response

#### Scenario: Actual study returns without tapping or fresh XP
- **WHEN** canonical learning XP or an existing reviewed server-scored/completed voice record proves recent actual account activity
- **THEN** that original positive time can suppress return work without rewriting progress, awarding a unit or requiring a notification tap

#### Scenario: Existing strict behavior and disabled deployment
- **WHEN** ordinary mode is not explicitly selected or the shared runtime switch is disabled
- **THEN** existing strict coverage behavior remains unchanged and no new runtime polling or posting authority is enabled

#### Scenario: Day-one learner has a saved time
- **WHEN** the explicit observed profile has a genuinely saved/manual clock and all current consent/review/target guards pass, but fewer than three verified active days exist
- **THEN** ordinary reminders may use that existing clock immediately under the same daily/weekly limits, with no invented learned gap, inactivity or failed-response estimate; observed current-day learning still suppresses the return reminder

### Requirement: Monitored staged Smart rollout
The system SHALL open Smart study reminders through four stable cumulative cohorts derived from the canonical account ID. It SHALL advance after 48 observed hours per stage, pause on a systemic technical or ambiguous delivery failure, turn the existing Smart template OFF on that pause, and require a protected Admin PWA re-enable to restart at stage one. Unobserved time MUST NOT count toward a stage. Rollout state MUST contain no learner identifiers and MUST NOT create consent.

#### Scenario: First cohort starts
- **WHEN** the Smart study template is enabled and the runtime is ready
- **THEN** the durable rollout begins with the first stable cohort; all existing consent, client, access, daily/weekly budget and legacy-sender guards remain in force

#### Scenario: Healthy stage advances
- **WHEN** the current stage has been observed by runtime heartbeats for 48 hours
- **THEN** the next cohort becomes eligible cumulatively, and the durable stage start and heartbeat are updated atomically

#### Scenario: Unobserved time
- **WHEN** no heartbeat ran for longer than the monitor allowance (deploy, crash)
- **THEN** send authority fails closed until the next heartbeat, and the gap does not count toward the stage

#### Scenario: Systemic failure
- **WHEN** at least 5 started attempts in the stage have unknown outcomes and they are at least 30% of the started attempts, or three unexpected per-account exceptions occur within an hour, or three consecutive ticks time out
- **THEN** the global Smart template is disabled, the rollout is paused with only a fixed sanitized error code, and no new stage or dispatch authority is issued

#### Scenario: Learner refusal is not systemic
- **WHEN** a learner blocked the bot, a PWA subscription is expired, or an Android receipt is still pending
- **THEN** the outcome does not count toward the systemic pause; a Telegram block marks the learner blocked and the attempt is never retried

#### Scenario: Operator resumes after repair
- **WHEN** an authorized operator re-enables the Smart template after reviewing a paused rollout
- **THEN** the rollout generation increments and observation restarts at stage one; cohorts outside stage one are excluded again at every final send boundary, and no audit or attempt evidence is deleted

### Requirement: Automatic admission of eligible accounts
Inside an open cohort the system SHALL move an eligible account from the legacy study senders to Smart without manual review: hold it, wait 24 hours from the first hold, then record an evidence-bound automatic review through the existing routing writers. It MUST NOT create or infer consent, and MUST NOT hold an account that an active device without the Smart capability could still remind locally.

#### Scenario: Eligibility
- **WHEN** an account's Smart preference has no real IANA zone, or allows no channel
- **THEN** it is not held and its legacy reminders continue

#### Scenario: Eligible Telegram learner
- **WHEN** an account in an open cohort has a Smart zone, Telegram consent ON, a reachable bot and no unfenced Android device
- **THEN** it is held (server legacy study senders stop), reviewed after 24 hours, and then served by the existing Smart Telegram path

#### Scenario: Older Android app
- **WHEN** an account has an active Android device without the Smart capability
- **THEN** it is not held and keeps its legacy reminders until a Smart-capable app reports its capability

#### Scenario: Same owner re-attestation
- **WHEN** an admitted account changes its preference revision or Android capability while state, binding and generation are unchanged
- **THEN** the review is refreshed in place after the same consent and fence checks, and no planned work is cancelled

#### Scenario: Consent turned off after admission
- **WHEN** an admitted account turns Smart or its channel OFF
- **THEN** the review is never re-attested, no Smart reminder is sent, and the sticky hold does not revive the legacy sender
