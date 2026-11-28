# Spec Delta

## Purpose
Measure comparable independent application and recall while showing only gains that the learner's verified evidence supports.

## ADDED Requirements

### Requirement: Comparable bounded measurement
Both arms SHALL use the same assessment version, taught-objective eligibility, equivalent tasks, assistance policy and timing. Existing comparable probes SHALL be reused where possible; new probes MUST have equal bounded burden and be recognized as retrieval interventions. Common assessment MUST NOT alter official course completion, grades, homework or rewards.

#### Scenario: A new transfer or recall probe is necessary
- **WHEN** existing tasks cannot establish the required comparable evidence
- **THEN** both arms receive the frozen equivalent probe policy and the analysis states the changed control condition
- **AND** recognition, independent production and optional formative speech remain distinct; a speech model does not become the common grader

### Requirement: Authoritative first-response and help state
A neutral exercise receipt SHALL bind account, UUID, purpose, admitted source/grading snapshot, expiry, help state and first accepted result. Common-grading answers MUST remain withheld before response; help/reveal MUST be recorded before serving it. Missing assistance evidence MUST remain unknown rather than unassisted.

#### Scenario: Assistance or retry occurs
- **WHEN** the learner requests help, submits a response twice or supplies a caller correctness flag
- **THEN** the server grades the owned frozen receipt, preserves help-before-answer and returns the original result for exact retries
- **AND** an assisted result cannot overwrite the independent first result; cross-account/stale mismatches are rejected without blocking the base lesson

### Requirement: Honest delayed recall and missingness
Delayed assessment SHALL use frozen windows and unseen equivalent items. Reports MUST show mature assigned, eligible, offered, responded and missing counts, all-assigned demonstrated success, responder accuracy and missing-outcome bounds. Nonresponse MUST NOT become verified failure, success or silent exclusion.

#### Scenario: Learner does not supply a delayed answer
- **WHEN** a recall window matures without a valid response
- **THEN** demonstrated-success receives no success but knowledge remains unobserved
- **AND** the report shows worst/best-case missing-outcome bounds and does not claim retention improvement from selected responders alone

### Requirement: Specific truthful progress and one existing next action
Feedback SHALL identify a verified objective and require comparable prior evidence for improvement claims. Results SHALL reuse canonical Mistakes, adaptive review, flashcards/mastery and Daily Plan identities; at most one relevant existing next action is offered. Optional AI Voice MUST preserve quotas/access and remain nonblocking.

#### Scenario: Verified result is available
- **WHEN** a learner demonstrates an objective or makes a source-verified mistake
- **THEN** feedback describes that evidence and links the appropriate existing continuation without duplicate targets or conflicting schedules
- **AND** absent baseline yields present achievement, not invented growth; visual/sound feedback honors mute and reduced-motion settings

### Requirement: Equal rewards and optional satisfaction
Both arms SHALL retain identical official XP/streak economics, access and completion dedupe. Celebrations MUST use server-confirmed success. Optional satisfaction SHALL use identical trigger, scale and frequency cap with prompt/response denominators; it MUST NOT be inferred from XP, animations or time spent.

#### Scenario: Reopen or unanswered prompt
- **WHEN** a completed result reopens or a learner ignores satisfaction
- **THEN** no duplicate reward or fresh streak is awarded and no rating is fabricated
- **AND** the learner continues through the existing flow without a mandatory survey or unavailable Voice step
