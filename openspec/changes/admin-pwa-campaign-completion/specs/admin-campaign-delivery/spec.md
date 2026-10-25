# Spec Delta

## Purpose

Complete first-party campaign delivery controls while preserving exact passkey authorization, bounded recipient work and existing learner access and notification rules.

## ADDED Requirements

### Requirement: Exact promotion buttons
The PWA SHALL support only existing promotion actions and validated HTTPS or Telegram username links. The signed commitment MUST include the exact rendered button for every language; neither a changed contact setting nor a browser-supplied callback can substitute a destination after authorization.

#### Scenario: Changed destination
- **WHEN** a stored contact destination changes after preparation
- **THEN** saving the command is rejected without spending its proof or creating delivery work

#### Scenario: Authored localized button
- **WHEN** an admin authors a label for a promotion button
- **THEN** explicit UZ/RU/TJ labels are required together, or existing localized defaults are used for all three languages

### Requirement: Bounded scheduled authority
Scheduled work SHALL retain the existing session-bound grant, one-hour private payload lifetime, recipient cap and no uncertain retry policy. The UI MUST expose the allowed send window. Indexed due-work reads MUST be bounded and disabled when the PWA boundary is disabled.

#### Scenario: Revoked or expired schedule
- **WHEN** a queued send becomes due after its authorizing session is revoked or expires
- **THEN** no unclaimed recipient is sent and a new exact signed action is required

### Requirement: Explicit discount notices
An offer notice SHALL require a fresh commitment to current offer, exact eligible audience and localized rendered notice. It MUST preserve existing native channel and Play restrictions and MUST NOT create payment, grant access or change offer eligibility.

#### Scenario: Offer changes before save
- **WHEN** the offer changes after notice preparation
- **THEN** saving is rejected atomically without recipient work

### Requirement: One original editor action
All new controls SHALL use the original V10 editor with a contextual action followed by one native passkey ceremony. Cancellation MUST preserve the draft and a lost write response MUST NOT cause an automatic retry.

#### Scenario: Native cancellation
- **WHEN** the native passkey request is cancelled
- **THEN** the original copy, selected button, media and scheduling inputs remain available in the editor
