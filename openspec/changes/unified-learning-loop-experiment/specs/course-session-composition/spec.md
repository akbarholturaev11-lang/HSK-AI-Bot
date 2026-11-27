# Spec Delta

## Purpose

Compose varied, goal-relevant learning sessions within the learner's time budget while preserving required teaching, course order and reliable resume.

## ADDED Requirements

### Requirement: Protected teaching and objectives
Composition SHALL preserve required new vocabulary, grammar, source dialogue teaching, required foundation and existing exit-check objectives. New formats MUST NOT change lesson order, canonical material references, correct answers, official pass rules, homework or access policy.

#### Scenario: A five-minute session is requested
- **WHEN** the learner chooses the shortest available daily time
- **THEN** only eligible optional practice is shortened or substituted
- **AND** protected teaching and the required final objective checks remain available
- **AND** the system does not claim the selected duration is a guaranteed completion time when protected material exceeds it

#### Scenario: No legal composition fits
- **WHEN** an optional new format would remove protected material or exceed the bounded session allowance
- **THEN** the format is omitted or substituted with a smaller eligible task
- **AND** the existing required lesson can still be completed without a new access restriction

### Requirement: Budgeted selection from verified learner context
Treatment composition SHALL use saved goals, time, verified knowledge/mistakes and recent shown-format history. It MUST preserve the lesson's learning goal and bound optional task count and estimated duration. Missing personal history SHALL use a deterministic cold-start mix rather than fabricate weakness or mastery.

#### Scenario: Cold-start account
- **WHEN** an account has no prior verified mistakes or shown-format history
- **THEN** the system composes a bounded mix from eligible source material and saved preferences
- **AND** it does not invent learner mistakes, skill levels or completion history

#### Scenario: A verified weakness exists
- **WHEN** verified prior answers identify a relevant weakness
- **THEN** eligible practice can give that objective additional priority within the same optional budget
- **AND** the existing adaptive-review and mistake schedules remain authoritative
- **AND** adding review does not indefinitely postpone current teaching

### Requirement: Variety across short and long sessions
When at least two safe eligible formats exist, treatment SHALL rotate optional formats across successive sessions using recent actual delivery/exposure history. Time trimming MUST NOT always retain the same format solely because it appears first or has a fixed skill rank. Necessary repeated objective practice SHALL remain allowed.

#### Scenario: Repeated short lessons have multiple candidates
- **WHEN** a learner completes successive short sessions with several equally eligible formats
- **THEN** the selected optional formats vary under the frozen composition policy
- **AND** hidden, undelivered or failed-to-load candidates are not recorded as seen
- **AND** the preserved objective coverage is unchanged

#### Scenario: Only one safe format exists
- **WHEN** only one format is eligible for the current material, locale and capabilities
- **THEN** the safe format can repeat
- **AND** the coverage report records limited eligibility rather than generating unsafe novelty

### Requirement: Stable snapshots and resume
A started session SHALL keep stable task identities, source revision, composition version and grading snapshot across reload, retry and cross-device continuation. Saved progress MUST refer to canonical base positions and separately identified supplemental tasks, so plan changes cannot skip teaching or duplicate completion rewards.

#### Scenario: Retry or second device opens the session
- **WHEN** the same account resumes an existing attempt after retry or on another supported device
- **THEN** completed task responses remain completed and receive their original feedback
- **AND** remaining tasks use the saved session version or a documented compatible base fallback
- **AND** the attempt is not counted as another learner or another completion

#### Scenario: Content revision changes during an attempt
- **WHEN** the installed content or composition policy changes after the attempt started
- **THEN** the attempt retains its admitted grading snapshot until expiry or safely returns to its saved base position
- **AND** a response is not graded against a different source key

### Requirement: Safe progressive delivery
Optional composition and media SHALL not block the first usable lesson screen. Loading, empty, error and retry states MUST settle independently; private plans MUST remain account-bound. Failure SHALL continue through the existing base flow without optimistic progress, entitlements or fabricated numbers.

#### Scenario: Plan service is slow or unavailable
- **WHEN** optional composition times out or returns an invalid plan
- **THEN** required base teaching remains usable
- **AND** the learner sees only a relevant local failure/retry state where needed
- **AND** no duplicate plan requests or cross-account cached items are displayed

### Requirement: Control remains the existing learning format
Control accounts SHALL receive the pinned existing lesson format and existing supporting policies, apart from common measurement delivered identically to both arms. Experimental composition MUST require server-authorized treatment delivery and compatible capabilities.

#### Scenario: Control account advertises new capabilities
- **WHEN** a control account opens a fully capable updated client
- **THEN** it receives the control lesson composition
- **AND** a client-supplied arm or capability field cannot enable treatment
- **AND** common assessments use the same rules as treatment
