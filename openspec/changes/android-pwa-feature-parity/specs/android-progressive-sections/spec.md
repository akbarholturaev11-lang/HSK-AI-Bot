# Native progressive sections

## Purpose

Keep native profile and checkout responsive while independent authenticated requests settle without implying account or entitlement facts.

## ADDED Requirements

### Requirement: Independent profile settlement
Profile and optional trial status SHALL load and retry independently with generation-safe updates. Known profile content SHALL remain usable while trial is pending or failed.

#### Scenario: Slow trial
- **WHEN** profile succeeds while trial status is unresolved
- **THEN** profile renders immediately and trial alone retains a reserved loading region.

#### Scenario: Stale account response
- **WHEN** a newer load or session supersedes an earlier request
- **THEN** the earlier response cannot overwrite the current state.

### Requirement: Stable affected loading slots
Affected native checkout/onboarding loading states SHALL reserve the actual heading, card and action geometry, retain a visible exit/retry and respect disabled animation settings.

#### Scenario: Loading and retry
- **WHEN** an affected read is slow or fails
- **THEN** its native shell remains navigable and retry replaces only the relevant region.
