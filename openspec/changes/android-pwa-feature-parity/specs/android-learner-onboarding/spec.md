# Native onboarding

## Purpose

Provide native Android learning choices through canonical account and course services without implicitly activating a web rollout.

## ADDED Requirements

### Requirement: Preserve rollout and account ownership
Android SHALL retain its current onboarding when the native Li switch is off. Enabled native choices SHALL save only through verified bearer ownership and server course eligibility.

#### Scenario: Disabled native rollout
- **WHEN** PWA Li is enabled but the native Li switch is disabled
- **THEN** Android retains its existing four-step onboarding and sends no Li-only selection.

#### Scenario: New learner saves choices
- **WHEN** an authenticated new learner submits goals, time, focus and streak target
- **THEN** the canonical service validates and persists them with legacy primary goal compatibility and existing onboarding analytics.

#### Scenario: Existing learner or locked course
- **WHEN** a saved learner resumes or a locked HSK 3.0 level is selected
- **THEN** saved progress is preserved and the server rejects unauthorized track entry.

### Requirement: Match PWA choice navigation on Android
Li choice screens SHALL use the PWA hierarchy of header back, compact mascot and speech bubble, scrollable choices, and one fixed primary action. Android system back SHALL remain available for returning to a prior choice.

#### Scenario: Narrow and short viewport
- **WHEN** the learner opens the daily time question in UZ, RU or TJ on a narrow screen
- **THEN** the choices remain readable and selectable, the footer never covers them, and the header back control is the only visible back action.

### Requirement: Native auth and trial remain authoritative
Native auth SHALL reuse original provider proof polling and cancellation. Native Pro introduction SHALL use actual server trial eligibility and activation, and SHALL offer free continuation without granting local access.

#### Scenario: Provider or trial response is delayed
- **WHEN** provider approval or trial activation is pending
- **THEN** the native Panda waiting state remains dismissible and only verified server completion advances the flow.
