# Learner PWA navigation

## Purpose

Keep the current learning screen and its controls usable while secondary screens load on an intermittent connection.

## ADDED Requirements

### Requirement: Return to the active learning screen
The PWA SHALL preserve the active course view during checkout and leave Back usable regardless of data-loading state.

#### Scenario: Back while checkout is waiting
- **WHEN** an authenticated learner enters checkout from the course and goes back before the price overview finishes
- **THEN** the same course screen and selection are interactive without waiting for another map
- **AND** checkout actions still require the existing server authentication and access decisions.

### Requirement: Start under the current session
The PWA SHALL skip sign-in for a verified returning session and retain new-user onboarding when required.

#### Scenario: Home Screen launch
- **WHEN** the server verifies the browser's current session
- **THEN** the learner proceeds to the course without a flash of the sign-in UI.
