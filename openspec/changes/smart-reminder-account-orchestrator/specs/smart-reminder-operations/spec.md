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
