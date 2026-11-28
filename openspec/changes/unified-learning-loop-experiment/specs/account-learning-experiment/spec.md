# Spec Delta

## Purpose
Evaluate one coherent learning treatment through stable account-level randomization, honest measurement and reversible global delivery.

## ADDED Requirements

### Requirement: Durable server-only equal allocation
Each eligible authenticated canonical account SHALL receive one immutable 50/50 assignment in the existing canonical event store, unique by owner and experiment version. Assignment MUST commit authoritatively before treatment, remain passive/server-only and survive device, locale, track, entitlement and OFF/restart changes. Invalid allocation evidence MUST fail closed without rerandomization.

#### Scenario: Concurrent enrollment or device switch
- **WHEN** requests race or the same account signs in elsewhere
- **THEN** one committed assignment is reused; client arm claims, null-owner rows and separately created accounts cannot establish its arm
- **AND** failure continues the safe base flow; OFF/restart does not renew assignment time, seed or cohort

### Requirement: Frozen enrollment cohorts and global QA gate
New/existing cohorts SHALL be frozen against canonical creation time at launch; outcome time starts at eligible enrollment. Default-OFF activation MUST await evidence review, calibrated protocol and internal source/content/security/device QA, then cover all admitted courses/locales/supported surfaces globally without recruited pilots. Old-client fallback MUST retain assignment and ITT membership.

#### Scenario: Dormant account or unsupported client
- **WHEN** an old account returns after launch or treatment lacks a compatible renderer
- **THEN** it remains existing and follows its assigned arm, with unsupported delivery recorded as fallback
- **AND** assignment, delivered task and actual exposure stay separate; no post-randomization removal hides nonexposure

### Requirement: Qualified learning days primary
The primary SHALL be mean qualified-learning days, zero to seven elapsed 24-hour buckets in [24,192) hours after enrollment. Only pinned symmetric existing ordinary-outcome sources SHALL qualify. New and existing cohort effects SHALL be tested separately as a Holm family at alpha 0.05.

#### Scenario: Several actions or no return
- **WHEN** an account acts repeatedly in one bucket, switches platforms or never returns
- **THEN** the bucket contributes at most one day, cross-platform evidence deduplicates and mature nonreturn contributes zero
- **AND** app-open return remains distinct; a pooled estimate cannot override an unsupported or harmful cohort result

#### Scenario: New receipt endpoints create more observations
- **WHEN** either arm records ordinary lesson completion, existing server-scored practice/review/exam work or a confirmed learner Voice turn under equivalent source coverage
- **THEN** it may qualify under the same frozen source definition
- **AND** app opens, passive events, measurement-only probes and treatment-only formative receipts cannot manufacture a qualified day

### Requirement: Secondary outcomes and honest maturity
D1/D7/D14 exact returns SHALL use [24,48), [168,192) and [336,360) elapsed-hour windows. Completion, bounded abandonment, common transfer/recall, satisfaction, latency/failure and cost SHALL remain secondary or guardrail measures with fixed grains, denominators and maturity. Legacy completion MUST NOT establish independent mastery.

#### Scenario: Outcome is immature or only partly observed
- **WHEN** a window remains open, an attempt has no matched outcome or instrumentation is missing
- **THEN** the report distinguishes immature, unknown/technical, fallback and mature outcomes
- **AND** absent evidence is not silently zero; first-response measurement and delayed-nonresponse limits remain visible

### Requirement: Calibration before activation
Baseline mean/variance, eligible traffic, meaningful effect, cost ceiling, power/sample size and observation horizon SHALL remain UNCALIBRATED until measured under the primary definition and frozen in a versioned preregistration. Private aggregate snapshots MUST NOT substitute for raw sequence/cohort evidence or justify invented lift, sample size or a fixed proof duration.

#### Scenario: Available aggregates lack the primary baseline
- **WHEN** existing reports provide registration returns or active-account stocks without enrollment-bucket outcomes
- **THEN** activation remains OFF until the missing same-definition evidence and decision thresholds are obtained
- **AND** historical comparisons remain descriptive; no monotony cause, sample-size adequacy or causal win is asserted

### Requirement: Valid complete aggregate analysis
The existing authorized Admin report SHALL expose full assigned denominators, effect uncertainty, coverage/loss, safety and sample-ratio checks without private answers, audio or identity. Snapshot/platform overlaps MUST NOT be summed. Frozen interference and stopping rules SHALL govern concurrent feature changes and repeated inspection; telemetry MUST remain nonblocking.

#### Scenario: Detail cap or integrity failure
- **WHEN** detail limits, attribution gaps, arm imbalance or prespecified guardrails invalidate interpretation
- **THEN** the report uses a complete bounded aggregate or marks the metric unavailable, withholds a win and follows the frozen stop/investigation rule
- **AND** control-plus-probes is explicitly distinguished from an untouched control

### Requirement: Bounded stop and preserved state
An authorized stop SHALL prevent new online treatment issuance within 60 seconds across workers and connected clients. Treatment requires a monotonic bounded lease; expired/unverifiable leases MUST fall back before another task. OFF MUST preserve accepted results, original resume behavior, assignment and business invariants without adding synchronized course cursors or deleting populated evidence.

#### Scenario: Stop while connected or offline
- **WHEN** the operator stops treatment while a client is connected or disconnected
- **THEN** online checks honor the 60-second bound and disconnected clients cannot start another treatment task after lease expiry
- **AND** already-started offline work follows saved safe settlement/base fallback; no instantaneous remote-offline claim or duplicate XP is made
- **AND** account deletion still purges owned assignment/receipt state under existing policy
