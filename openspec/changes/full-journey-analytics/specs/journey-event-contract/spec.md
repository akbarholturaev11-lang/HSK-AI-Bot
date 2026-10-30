# Spec Delta

> **DEFERRED PHASE 2:** These behavioral requirements are retained for a later, separately authorized implementation after Smart Reminder source maturity. Do not implement, deploy, migrate, instrument clients or change business logic under the Phase 1 R2→GitHub export scope. Phase 1 only applies to `verified-analytics-export`.

## Purpose

This capability defines auditable first-party learner journey events and explicitly represents data that cannot be observed, while preserving account authorization and existing business decisions.

## ADDED Requirements

### Requirement: Only owned and allowlisted events are recorded
The system SHALL accept only schema-versioned, allowlisted analytics events associated with a server-verified canonical account or an explicitly anonymous visit. Client-supplied identity, payment and ownership fields MUST NOT authorize a join.

#### Scenario: Authenticated event
- **WHEN** an authenticated client submits a supported event with a valid deduplication key
- **THEN** the server records the owned event once with UTC occurred/received timestamps and a supported source and surface

#### Scenario: Forged owner or unknown event
- **WHEN** a client submits a different user ID, unowned payment reference or unknown event name
- **THEN** the server rejects the forged association without changing payment, account access or course state

### Requirement: Recorded journeys distinguish missing from zero
The system SHALL expose event source and observation coverage, including `recorded`, `partial`, `not_instrumented`, `unknown` and `expired`, rather than treating absence of instrumentation as absence of behavior.

#### Scenario: Old client without time telemetry
- **WHEN** a client version emitted checkout open but no visibility/duration events
- **THEN** analytics labels time on screen unavailable and never reports zero seconds or a fabricated duration

#### Scenario: Capped source coverage
- **WHEN** bounded source reading reaches its published coverage limit
- **THEN** the report is explicitly marked partial and does not claim population-wide completeness

### Requirement: Observable sequence preserves independently repeated attempts
The system SHALL keep distinct attempts/sessions for the same account and deterministically deduplicate retries, late arrivals and cross-device reports without silently merging unrelated transactions.

#### Scenario: Two separate checkouts
- **WHEN** one user leaves a checkout and later starts a different checkout
- **THEN** the two attempt paths remain separate and only the correct payment may be joined to each

#### Scenario: Repeated event upload
- **WHEN** a client resends an accepted event with the same server-scoped idempotency key
- **THEN** the reported event count does not increase

### Requirement: Measured active time excludes background and missing intervals
The system SHALL derive bounded active screen time only from credible foreground/visibility/exit evidence with a documented inactivity timeout, and SHALL expose time coverage.

#### Scenario: User backgrounds app
- **WHEN** an active checkout screen becomes backgrounded before the user returns
- **THEN** analytics excludes background time and records only measured foreground intervals

#### Scenario: Single open event
- **WHEN** no exit, heartbeat or trustworthy duration evidence exists
- **THEN** checkout screen active time is unknown rather than computed from payment submission time

### Requirement: Canonical deletion and purpose limits remain effective
The system SHALL apply the existing account deletion/anonymization boundaries and documented analytics retention to optional account-linked events. Event recording SHALL remain observational and MUST NOT grant subscriptions or alter lesson outcomes.

#### Scenario: Account deletion
- **WHEN** an account is deleted through the supported flow
- **THEN** optional person-linked journey records are purged or unlinked according to the documented policy without reappearing in exports

#### Scenario: Analytics subsystem fails
- **WHEN** an optional analytics write fails or times out
- **THEN** supported course, payment and notification business flows preserve their existing correctness and report telemetry degradation separately
