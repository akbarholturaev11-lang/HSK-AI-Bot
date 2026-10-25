# Spec Delta

## Purpose

Provide source-bound aggregate analytics for the standalone administrator control center without exposing private learner records or repeatedly loading database history.

## ADDED Requirements

### Requirement: Source-bound section metrics
The system SHALL serve real metrics for the selected analytics section, period and platform, with captured generation time and explicit population/date/measurement definitions. It MUST distinguish missing or immature observations from real zero and MUST NOT substitute fixtures, guessed growth or unrelated platform totals.

#### Scenario: Empty mature cohort
- **WHEN** no eligible mature retention or conversion cohort exists
- **THEN** the rate is null or collecting with its real denominator, never a fabricated percentage

### Requirement: Canonical aggregate ownership
Overall counts SHALL deduplicate canonical accounts across transports. Legacy transport ownership SHALL be used only where no canonical owner exists. Event counts, distinct users, lessons, visits, devices and payments MUST retain their separate grains.

#### Scenario: Two client events for one account
- **WHEN** the same canonical account records activity through two clients on one day
- **THEN** that day's distinct-account activity counts the account once

### Requirement: Private daily on-demand reads
Each requested section/platform/period snapshot SHALL be reused for 24 hours from its original generation time. Unopened sections MUST perform no aggregate work. Reads and exports MUST enforce live administrator/session checks around cache IO and MUST NOT cache current command authority.

#### Scenario: Warm section
- **WHEN** an authorized administrator reopens an unexpired section
- **THEN** the same generated timestamp and metrics are returned without another aggregate calculation

### Requirement: Honest financial and source attribution
Exact revenue SHALL remain separated by currency. Any USD-equivalent or model-cost estimate SHALL identify its basis and unknown-price exclusions. Source attribution MUST use recorded evidence with its observation window and MUST NOT claim causal credit or derive conversion from unrelated event populations.

#### Scenario: Unknown payment currency
- **WHEN** an approved payment has no supported price basis
- **THEN** it contributes to applicable payment counts and explicit unknown-pricing coverage, but not to a fabricated converted sum

### Requirement: Bounded private analytics
Analytics SHALL use bounded outputs and bounded computation deadlines, expose only typed aggregate data and fail closed on unavailable/invalid work. Browser files MUST contain no learner identifiers, raw feedback, credentials, provider references or raw event payloads. External MCP permission MUST remain unchanged.

#### Scenario: Expired administrator during snapshot wait
- **WHEN** the session is revoked while an aggregate snapshot is being obtained
- **THEN** the protected response is denied after cache IO and no metrics file is returned
