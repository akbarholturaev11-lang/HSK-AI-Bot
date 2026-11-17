# Spec Delta

## Purpose

Offers a Telegram Mini App learner the client that fits their phone — the
iPhone PWA or the Android app — through the existing promotion rules, with the
destinations controlled by the administrator.

## ADDED Requirements

### Requirement: Independent admin switches control new routing offers
The existing per-platform iPhone and Android switches SHALL independently
control whether new Mini App routing offers are made. Switching one off SHALL
NOT affect installed apps, existing sessions, course access or subscriptions.

#### Scenario: iPhone switch off
- **WHEN** the iPhone switch is off
- **THEN** no iPhone PWA offer is shown and no new handoff can be issued, while existing PWA sessions keep working

#### Scenario: Android switch off
- **WHEN** the Android switch is off
- **THEN** no automatic Android offer is shown

### Requirement: The Google Play destination is admin-owned and validated
The administrator SHALL be able to set or clear one Google Play address through
the existing passkey-confirmed, change-checked and audited editor. Only the
official listing address of package `com.pomp.hskai` SHALL be accepted.

#### Scenario: Valid listing address
- **WHEN** the admin saves the listing address of `com.pomp.hskai`
- **THEN** it is stored in canonical form and audited without changing other promo options

#### Scenario: Invalid address
- **WHEN** the address has another host, package, scheme, credentials or extra path
- **THEN** it is rejected and nothing is stored

#### Scenario: Stale editor
- **WHEN** the setting changed after the editor loaded
- **THEN** the save is refused as changed

### Requirement: Offers follow the existing promotion rules
Routing offers SHALL reuse the existing placements, per-platform eligibility,
14-day cooldown, dismissal and one-offer-per-session rules. No second modal or
competing prompt SHALL be introduced.

#### Scenario: iPhone learner eligible
- **WHEN** an iPhone Mini App learner is eligible and the iPhone switch and PWA sign-in are on
- **THEN** the existing promo shows one iPhone PWA action

#### Scenario: Learner already uses the PWA
- **WHEN** the learner has an active PWA browser session
- **THEN** no automatic iPhone offer is shown

#### Scenario: Recently seen or dismissed
- **WHEN** the learner saw, dismissed or used the offer within the cooldown
- **THEN** no automatic offer is shown

### Requirement: Android routes to Google Play only when a valid address exists
On Android the existing offer SHALL open Google Play when a valid address is
configured, and otherwise SHALL keep the existing Direct APK delivery in chat.

#### Scenario: Play address configured
- **WHEN** an Android learner accepts the offer and a valid Play address is stored
- **THEN** Google Play opens and no APK is sent

#### Scenario: No Play address
- **WHEN** no valid Play address is stored
- **THEN** the existing APK-to-chat delivery runs unchanged

### Requirement: Routing is measured without inventing outcomes
The system SHALL record handoff issue, handoff completion and Play opening as
deduplicated events of the canonical account and expose them to the admin
statistics reader. An opened link SHALL NOT be reported as an installation.

#### Scenario: Statistics are read
- **WHEN** an admin reads platform statistics
- **THEN** recorded routing counts are returned and installation metrics that are not measured stay unavailable
