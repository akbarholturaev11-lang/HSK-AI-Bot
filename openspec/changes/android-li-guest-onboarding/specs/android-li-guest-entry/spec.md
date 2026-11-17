# Native guest onboarding

## Purpose

Offer native study choices before account creation while preserving verified identity and prior progress.

## ADDED Requirements

### Requirement: Study choices precede account creation

When the Android Li rollout is enabled, a new learner SHALL be able to select a track, level, goals, daily time, focus and streak before choosing a verified provider. Returning learners SHALL have a direct login path.

#### Scenario: First-time learner

- **WHEN** an unauthenticated learner selects the first-time path
- **THEN** native choices precede the provider screen and the client performs no authenticated write before provider proof.

#### Scenario: Disabled or unavailable preview

- **WHEN** the flag is off, the server is old or the public preview cannot be fetched
- **THEN** the existing native login remains usable.

### Requirement: Apply guest choices only to a fresh verified account

A pending local draft SHALL expire and be consumed once after a successful bearer status for the same session used to save. Server course validation and previously saved progress SHALL take precedence.

#### Scenario: Verified fresh account

- **WHEN** the provider confirms a fresh account and the selected track is allowed
- **THEN** the server validates and saves the draft before the existing Pro introduction.

#### Scenario: Existing account or track denied

- **WHEN** a saved account signs in or guest track access cannot be verified
- **THEN** the draft cannot replace saved progress or grant course access.
