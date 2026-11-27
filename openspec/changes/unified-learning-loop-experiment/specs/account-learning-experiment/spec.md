# Spec Delta

## Purpose

Test the unified learning treatment through stable canonical-account randomization, comparable learning evidence and reversible global delivery.

## ADDED Requirements

### Requirement: Persistent canonical-account allocation
The server SHALL assign each eligible authenticated account once with equal 50/50 probability to control or treatment under an immutable experiment version. Allocation MUST persist by canonical account, independent of device, Telegram identity, locale, track, subscription or client capabilities. Client claims MUST NOT select an arm.

#### Scenario: Account switches platforms
- **WHEN** the same canonical account signs in on another supported platform or changes course or locale
- **THEN** it keeps its original arm
- **AND** concurrent first requests resolve to one durable assignment
- **AND** the report counts one participant rather than one per installation

#### Scenario: Separate or linked identities
- **WHEN** a verified provider identity is attached to the same canonical account
- **THEN** its arm remains unchanged
- **AND** the experiment does not merge separately created accounts or promise identity equivalence without existing verification

#### Scenario: Expected split differs from an exact half
- **WHEN** a finite set of accounts is randomized
- **THEN** the intended assignment probability is 50/50 rather than a promise of identical arm counts
- **AND** the report evaluates sample-ratio mismatch using the frozen protocol

### Requirement: Frozen new and existing cohorts
Accounts SHALL be classified once as new or existing against the frozen global enrollment start, using canonical account creation time. Assignment time, cohort and baseline measurement version MUST remain immutable. Dormant existing accounts SHALL enroll on an eligible authenticated opportunity, without being relabelled new.

#### Scenario: Existing learner returns after launch
- **WHEN** an account created before the enrollment cutoff first returns during the experiment
- **THEN** it is randomized in the existing cohort
- **AND** its outcome clock starts from its recorded enrollment opportunity
- **AND** its earlier inactivity is not counted as experimental nonreturn

#### Scenario: Anonymous preview precedes authentication
- **WHEN** a visitor completes an anonymous preview and later authenticates
- **THEN** only the verified canonical account can receive the durable assignment
- **AND** anonymous local activity is not used to forge account age or learning success

### Requirement: Global launch after internal QA
Public experiment delivery SHALL remain default-OFF until the frozen protocol and internal source/content, synthetic, security, supported-client and device QA gates pass. Activation SHALL then cover all eligible new and existing accounts across admitted courses, locales and supported surfaces under one 50/50 experiment, without a recruited-learner or rewritten-pilot-lesson phase.

#### Scenario: Internal gate fails for a supported surface
- **WHEN** required source safety, grading, access, measurement or device acceptance fails
- **THEN** global treatment activation remains OFF
- **AND** passing OpenSpec validation or unit tests alone does not establish release or experiment readiness

### Requirement: Assignment delivery and exposure are separate
Reports SHALL retain all assigned eligible accounts for intention-to-treat analysis and separately identify treatment eligibility, delivery, actual exposure and fallback. Unsupported clients or missing media MUST preserve assignment and base flow rather than cause reassignment or post-randomization exclusion.

#### Scenario: Treatment account uses an old client
- **WHEN** a treatment account opens a client without the required capabilities
- **THEN** it receives the compatible base lesson
- **AND** remains in the treatment intention-to-treat denominator
- **AND** the report records capability fallback without claiming a shown new format

#### Scenario: Scene was planned but never shown
- **WHEN** a learner leaves before a planned scene or the media fails
- **THEN** planning is not counted as exposure
- **AND** first exposure and fallback are measured separately from assignment

### Requirement: Comparable outcome and attempt definitions
Both arms SHALL use identical server-owned outcome definitions, attempt windows and common-assessment policy. Completion, abandonment, independent task success, recall and satisfaction MUST expose denominators and maturity. Resumes, retries and platform switches MUST NOT create duplicate attempts or imply that legacy completion proves mastery.

#### Scenario: Attempt is unfinished
- **WHEN** a started eligible attempt has no completion
- **THEN** it is in-progress until its frozen outcome window matures and only then enters the specified abandonment measure
- **AND** access refusal, technical failure and ordinary abandonment remain distinguishable
- **AND** a resumed cross-device attempt is not counted as another learner start

### Requirement: Preregistered primary and secondary metrics
The primary SHALL be D7 qualified learning return, estimated separately for new and existing cohorts with Holm family-wise alpha 0.05. D1 and D14 SHALL be secondary. Return windows MUST be measured from enrollment at 24–48, 168–192 and 336–360 hours respectively; qualified return MUST require verified active learning evidence, not passive exposure.

#### Scenario: Passive events occur in the return window
- **WHEN** assignment, notification, media prefetch, automatic prompt or animation events occur without qualified learning
- **THEN** they do not establish a qualified return
- **AND** ordinary app-open return remains a separately labelled secondary measure
- **AND** neither event frequency nor longer screen time alone proves learning

#### Scenario: Only one cohort clears its primary criterion
- **WHEN** one cohort's primary effect satisfies the prespecified corrected test and the other does not
- **THEN** the report makes only the supported cohort claim
- **AND** a pooled result cannot override the separate cohort conclusions
- **AND** estimates include effect sizes, uncertainty and mature assigned denominators

### Requirement: Baseline-powered protocol before activation
Before activation, the protocol SHALL freeze observed baseline, eligible traffic, meaningful effect, sample-size/power calculation, enrollment horizon, outcome maturation, multiplicity and safety stop rules. Evidence MUST support the chosen numbers; the system MUST NOT invent an uplift, arbitrary fixed duration or winner from repeated uncorrected checks.

#### Scenario: Baseline or traffic is insufficient
- **WHEN** validated historical coverage or traffic cannot justify sample size and duration
- **THEN** the report identifies insufficient evidence and the needed preactivation measurement
- **AND** no expected benefit or statistically powered experiment is claimed
- **AND** internal QA does not become a substitute for randomized effectiveness evidence

#### Scenario: Guardrail or allocation integrity fails
- **WHEN** prespecified safety, sample-ratio, event-loss or attribution checks fail
- **THEN** the report withholds a win claim and applies the frozen investigation or stop rule
- **AND** missing instrumentation is labelled unavailable rather than zero

### Requirement: Historical comparison is descriptive
Historical comparisons SHALL use verified common metric definitions, coverage boundaries and comparable calendar/course/platform strata. Reports MUST distinguish descriptive before/after differences from randomized treatment effects, and MUST show unavailable metrics where prior instrumentation cannot establish them.

#### Scenario: Historic recall was not measured
- **WHEN** the operator requests a before/after recall comparison without valid historical assessment evidence
- **THEN** the historical value is unavailable with its coverage reason
- **AND** completion, XP or current responder accuracy is not substituted as historical knowledge retention

### Requirement: Bounded online emergency stop
An authorized global stop SHALL prevent new online treatment task issuance within 60 seconds across workers and connected clients. It MUST preserve arm, official results and saved base positions, and provide compatible base-flow continuation. Treatment MUST require a bounded valid delivery lease; the product MUST disclose that an already offline client cannot receive an instantaneous remote stop.

#### Scenario: Operator stops an active experiment
- **WHEN** the authorized global stop is recorded
- **THEN** online issuance and connected-client lease checks stop new treatment within 60 seconds
- **AND** in-flight work safely settles or continues through the saved base task without duplicate XP or lost official completion
- **AND** restarting the experiment does not rerandomize accounts

#### Scenario: Client remains offline
- **WHEN** a disconnected client cannot refresh its treatment lease
- **THEN** it cannot begin another treatment task after lease expiry and uses its supported base path
- **AND** already started offline work follows its saved safe completion/fallback contract
- **AND** neither the UI nor the operator report claims the offline device was instantly disabled

#### Scenario: Device clock changes or process resumes
- **WHEN** the wall clock moves backward, the app returns from suspension or a process restores saved state
- **THEN** task admission checks verified server lease validity using trustworthy elapsed time rather than an editable wall clock
- **AND** an unverified restored or uncertain suspended lease expires to base flow until server revalidation
- **AND** stale authority cannot extend treatment after the emergency stop bound

### Requirement: Private bounded complete measurement chain
The existing authorized Admin experiment surface SHALL expose aggregate assignment, coverage, outcomes, uncertainty and safety states. Event intake MUST use verified account/attempt context, deduplication and trusted platform attribution; raw answers, audio, tokens and private lesson text MUST NOT enter monitoring/report payloads. Telemetry MUST not block learner progress.

#### Scenario: Detail volume or telemetry is incomplete
- **WHEN** a report exceeds a bounded detail limit or required evidence is missing
- **THEN** it uses a complete bounded aggregate or explicitly reports unavailable/incomplete state
- **AND** it never silently samples an arm denominator or exposes learner identity
- **AND** telemetry failure does not roll back an authorized lesson result

### Requirement: Rollback preserves business and experiment facts
Rollback SHALL keep existing account, source, payment, subscription, referral, lesson, XP and streak invariants. Assignment and accepted evidence MUST remain available for audit; populated experiment state MUST NOT be destructively erased to disable treatment. Concurrent experiments and supporting policies MUST be pinned equally or accounted for in the frozen analysis.

#### Scenario: Supporting feature changes during the test
- **WHEN** reminder, paywall, adaptive-review or reward behavior would change differently between arms
- **THEN** the experiment follows its prespecified interference rule before interpreting effects
- **AND** no favorable learning result is attributed solely to the new formats without accounting for that difference
