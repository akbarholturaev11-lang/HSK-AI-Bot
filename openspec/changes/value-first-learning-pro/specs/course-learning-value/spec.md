# Course Learning Value

## Purpose

Help a learner interpret a confirmed course result, choose a practical follow-up and understand the extra access available through Pro on their platform.

## ADDED Requirements

### Requirement: A confirmed first learning result
The PWA and Android SHALL use the existing completion screen for the first newly saved real course part in the active level. It SHALL identify the part using its authenticated title and present measured accuracy as attempt feedback when available. If a reported error was verified against course material and saved, the result SHALL show one bounded, localized example to review.

#### Scenario: Saved with a verified error
- **WHEN** the server saves ordered course progress and records a verified incorrect response
- **THEN** the learner sees the topic and a course-sourced correction with a review cue
- **AND** the response contains no raw user answer or grading identifiers in the optional display block

#### Scenario: Evidence is incomplete
- **WHEN** no usable verified mistake exists, a save was rejected, or a retry yields a historical result
- **THEN** optional correction evidence is omitted
- **AND** a failed save keeps its existing retry path
- **AND** absence of a correction never implies mastery or perfect recall

### Requirement: Continue through existing learning destinations
The existing result action SHALL lead through the current, guarded next-part or course navigation. Learners SHALL be able to identify where to revisit errors and resume daily study using the existing destinations. Next-part availability SHALL reflect verified access. Activity, review and memory indicators SHALL preserve their distinct meanings.

#### Scenario: The daily plan was issued before the first attempt
- **WHEN** a verified error was saved after the day's task identities were issued
- **THEN** the learner can find the existing Mistakes destination
- **AND** access to that destination is checked normally and the day's task identities remain stable

#### Scenario: A free learner used the last available lesson
- **WHEN** the completion advances course progress and the next part is restricted
- **THEN** the learner can return to the course with its existing review and access controls without a claim of unlocked access

### Requirement: Contextual verified Pro value
The PWA and Android SHALL explain a specific relevant Pro benefit using current access and client capabilities at the existing access decision. A positive learning result itself SHALL remain available to eligible Free learners. Trial, pending and paid status and the applicable checkout channel SHALL remain server-authoritative.

#### Scenario: Learner reaches a server-confirmed limit
- **WHEN** the next lesson or mistake review reaches a subscription-eligible limit on a checkout-capable client
- **THEN** the existing access surface describes the confirmed benefit for that action and retains its existing continue or dismiss path

#### Scenario: Checkout unavailable or access already granted
- **WHEN** the client cannot offer checkout or the learner has an active entitlement
- **THEN** the UI preserves the applicable existing access path without a duplicate offer, assumed payment or new link

### Requirement: Interpretable learning and commercial evaluation
The system SHALL use existing canonical aggregate analytics and diagnostic paths with explicit eligibility, platform, time windows and unavailable states. Historical `sales_value_v1` assignment and attribution SHALL retain their current scope. Any future rollout SHALL be reversible independently of persisted progress and billing.

#### Scenario: No valid comparison data
- **WHEN** exposure ownership, cohort maturity or a baseline measure is missing
- **THEN** the affected effect is unavailable and no causal recommendation is made from unrelated totals

#### Scenario: Rollback after a completed lesson
- **WHEN** only the optional learner presentation is rolled back
- **THEN** lesson progress, recorded review data and existing payment and access history remain usable
