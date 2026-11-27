# Spec Delta

## Purpose

Make specific verified learning gains visible and measure independent transfer and later recall comparably across experimental arms.

## ADDED Requirements

### Requirement: Common independent assessment
Both arms SHALL receive the same versioned assessment policy for taught objectives, equivalent unseen tasks, timing, eligibility, grading and feedback. First unassisted responses MUST be distinguishable from hinted, retried, recognition and speaking responses. These checks MUST NOT alter existing official course pass, completion or homework rules.

#### Scenario: Recognition and production differ
- **WHEN** treatment practices a scene and control practices its existing exercise
- **THEN** the shared transfer assessment tests the same taught objective under equivalent conditions
- **AND** a correct multiple-choice answer is not counted as independent speech or free production
- **AND** results identify assistance and response mode rather than collapse unlike tasks into one accuracy score

#### Scenario: Assessment is unavailable
- **WHEN** a learner cannot load or submit a common assessment
- **THEN** the official lesson retains its existing completion and access behavior
- **AND** assessment coverage reports missing/technical state
- **AND** the attempt is neither silently counted correct nor silently removed from the all-assigned report

### Requirement: Verified and repeat-safe assessment results
Assessment results SHALL be bound to the authenticated account, admitted objective, attempt and frozen grading version. The server MUST verify bounded responses, reject cross-account or stale mismatches and return the same result for an exact retry. Client-reported correctness MUST NOT establish mastery.

#### Scenario: Forged or duplicated result
- **WHEN** a client submits another account's attempt, a spoofed correct flag or repeats a response
- **THEN** unauthorized or unverifiable evidence is rejected and an exact authorized retry remains idempotent
- **AND** no extra XP, streak day, official completion or mastery gain is created

### Requirement: Server-owned assistance and solution reveal
Answer-bearing transcripts, solutions and explanations for unaided checks MUST be withheld until an accepted first answer or explicit authenticated help reveal. Reveal SHALL atomically persist monotonic assistance state before returning the content; assistance and first-answer ordering MUST remain consistent across devices and retries.

#### Scenario: Reveal races an answer on another device
- **WHEN** help reveal and an answer are submitted concurrently for the same owned item
- **THEN** the server serializes them and only an answer accepted before reveal may retain unaided status
- **AND** retry or reopening cannot clear the recorded helped state
- **AND** public pre-answer payloads do not contain the withheld solution or answer-bearing transcript

#### Scenario: Source has no explicit objective tag
- **WHEN** existing admitted material lacks an objective ID
- **THEN** shared source-bound target/skill mappings provide a reviewed versioned objective or explicitly unavailable probe coverage
- **AND** the system does not invent objective equivalence or claim measured learning for an unassessed course

### Requirement: Delayed recall with honest missingness
Recall SHALL be measured using prespecified delayed windows and equivalent unseen items in both arms. Reports MUST show assigned, eligible, offered and responded denominators, immature windows and missing results. Demonstrated recall among all assigned accounts and accuracy among responders MUST remain distinct.

#### Scenario: Learner does not return for recall
- **WHEN** a mature eligible learner supplies no delayed response
- **THEN** the all-assigned demonstration numerator receives no success
- **AND** the missing result is explicitly shown in assessment coverage
- **AND** the learner is not silently dropped or represented as having a verified wrong answer

#### Scenario: Recall window is still immature
- **WHEN** the delayed test window has not finished
- **THEN** that observation is labelled immature
- **AND** it is not included as a mature failure or interpreted as zero retention

### Requirement: Truthful progress feedback
The learner SHALL see feedback tied to a specific verified objective or comparable prior evidence. Improvement claims MUST require comparable baseline and current evidence; sparse data SHALL show the current achievement without invented growth. Animations, sounds and encouragement MUST honor existing mute, accessibility and reduced-motion settings.

#### Scenario: Comparable prior failure and current success
- **WHEN** the learner independently succeeds on an objective previously failed under comparable assessment conditions
- **THEN** feedback can identify that objective and the newly demonstrated ability
- **AND** it does not claim the whole skill, level or language is mastered from one response

#### Scenario: No comparable baseline
- **WHEN** the learner correctly finishes a first assessed task
- **THEN** feedback describes what was demonstrated now
- **AND** it does not invent a prior inability, growth percentage or completed streak

### Requirement: Connect existing learning tools without duplicate state
Verified results SHALL use the established Mistakes, adaptive review, word mastery/flashcards and Daily Plan identities and schedules. A relevant next action SHALL be offered through existing surfaces where eligible. Optional AI Voice MUST preserve its existing access, quota and permission policy and remain nonblocking.

#### Scenario: New format reveals a verified mistake
- **WHEN** a source-bound answer is verified incorrect
- **THEN** the relevant existing mistake target is updated under its canonical identity
- **AND** repeated submissions do not create duplicate targets, conflicting schedules or extra XP
- **AND** later review can reference the same objective without rewriting original source answers

#### Scenario: Voice is unavailable or paid access is absent
- **WHEN** an optional relevant Voice continuation cannot run under current permissions, quota or entitlement
- **THEN** the learner retains a usable course or review next action
- **AND** the new format grants no Voice access or subscription benefit
- **AND** the lesson completion flow remains usable

### Requirement: Preserve reward economics and confirmed success
Both arms SHALL retain identical official XP values, streak rules, lesson completion dedupe and access policy. Celebrations MUST reflect server-confirmed achievements; replay, supplemental content, assessment submission and visual effects MUST NOT independently award duplicate course rewards.

#### Scenario: Session resumes after completion
- **WHEN** a completed lesson or its feedback is reopened on another device
- **THEN** the existing completion remains acknowledged without replaying a fresh reward
- **AND** the same canonical activity cannot create another XP award or streak update

### Requirement: Symmetric optional satisfaction
Both arms SHALL receive the same optional satisfaction scale, eligibility, frequency cap and trigger. Reports MUST show prompts and response rate with the rating, and MUST NOT present release-campaign feedback as lesson satisfaction or infer happiness from animations, time spent or XP alone.

#### Scenario: Learner ignores the prompt
- **WHEN** a satisfaction prompt is shown without a response
- **THEN** the learner continues without penalty or blocking prompt
- **AND** the report records nonresponse rather than a neutral or positive rating
