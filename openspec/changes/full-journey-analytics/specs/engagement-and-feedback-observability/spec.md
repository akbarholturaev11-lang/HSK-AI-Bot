# Spec Delta

## Purpose

This capability defines trustworthy aggregate learning, retention, notification, feedback and technical-error observations while retaining sensitive material in existing protected services.

## ADDED Requirements

### Requirement: Notification lifecycle states are not conflated
The system SHALL report only verified stages of each available notification channel and SHALL distinguish queued, provider accepted, client shown, opened, actioned, failed and unknown states according to source evidence.

#### Scenario: Accepted without display
- **WHEN** FCM accepts a message but the Android client provides no display acknowledgement
- **THEN** the system may count provider acceptance but MUST NOT count a verified display or user open

#### Scenario: Telegram fallback
- **WHEN** an existing notice uses its authorized Telegram fallback after unknown Android display
- **THEN** analytics records distinct observed delivery paths without creating a duplicate notification or changing retry behavior

### Requirement: Retention uses matured eligible cohorts
The system SHALL compute D1/D7 returning learners using a defined account/cohort, timestamp boundary and completed observation maturity. The numerator MUST NOT include ineligible or not-yet-matured accounts.

#### Scenario: Immature D7 cohort
- **WHEN** fewer than seven complete days of return opportunity have elapsed for an account
- **THEN** that account is excluded from the matured D7 denominator

#### Scenario: Multiple visits
- **WHEN** an eligible learner opens the product several times in the D1 return interval
- **THEN** the numerator increases by one eligible account, not by the visit count

### Requirement: Learning and AI usage report original grains
The system SHALL distinguish distinct engaged learners, completed user-lessons, session duration, AI requests/tokens and model-level cost estimates by verified unit, scope and original data availability.

#### Scenario: Lesson and learner are different
- **WHEN** one learner completes several lessons
- **THEN** unique completed learners and completed user-lessons remain separate metrics

#### Scenario: Unavailable duration
- **WHEN** an incomplete or capped event stream prevents session-duration calculation
- **THEN** duration is unavailable or partial rather than inferred from total events

### Requirement: Feedback is categorized without raw content release
The system SHALL report aggregate feedback categories and status from verified allowlisted fields and SHALL keep respondent IDs, freeform user text, attachments and administrative replies out of the public analytics mirror.

#### Scenario: Explicit disliked code
- **WHEN** feedback carries a recognized disliked code
- **THEN** the aggregate categorizes it under the documented code and group, without including private freeform text

#### Scenario: Unknown category
- **WHEN** feedback contains only unclassified free text
- **THEN** the aggregate counts an unknown category as supported and does not invent a sentiment or topic

### Requirement: Technical error reporting is bounded and redacted
The system SHALL publish only source-verified error codes/categories, platform, version and coarse screen context where available; private stack traces, URL parameters, student content and identifiers MUST NOT leave the protected system.

#### Scenario: Diagnostic stack contains secrets
- **WHEN** an existing Mini App error context contains arbitrary URLs, stack traces or embedded student data
- **THEN** public reports contain no such content and diagnostic categorization fails closed when no safe classification exists

### Requirement: Notifications, errors and feedback cannot actuate the system
The system SHALL treat observational analytics as read-only evidence that does not send notifications, issue discounts, grant lessons, change payments or auto-contact learners.

#### Scenario: Analyst views high dropout rate
- **WHEN** an analytical report identifies many checkout drop-offs
- **THEN** no notification campaign or paid entitlement is created without an independent authorized operational action
