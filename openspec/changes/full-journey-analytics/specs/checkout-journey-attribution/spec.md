# Spec Delta

> **DEFERRED PHASE 2:** These behavioral requirements are retained for a later, separately authorized implementation after Smart Reminder source maturity. Do not implement, deploy, migrate, instrument clients or change business logic under the Phase 1 R2→GitHub export scope. Phase 1 only applies to `verified-analytics-export`.

## Purpose

This capability reveals the observed checkout journey and its recorded entry sources while preserving server-authoritative payment state and avoiding unsupported causal claims.

## ADDED Requirements

### Requirement: Checkout steps are linked to one account and attempt
The system SHALL represent the supported ordered stages of each checkout attempt and its selected plan, offer and method when actually recorded. A completion MUST be verified by authoritative payment state.

#### Scenario: Completed checkout
- **WHEN** an owned account opens checkout, chooses a plan, views payment instructions, submits a receipt and an administrator later approves that exact payment
- **THEN** the attempt shows each recorded step and the server-confirmed approval, with per-step UTC times, duration coverage and selected plan

#### Scenario: Plan switch
- **WHEN** a user switches plans within a checkout attempt
- **THEN** the plan history and final selected plan are distinguishable, subject to the telemetry version's evidence

#### Scenario: Unsubmitted receipt or rejected payment
- **WHEN** an attempt stops before submission or the linked payment is rejected
- **THEN** the final stage is represented as abandoned or rejected, not successful

### Requirement: Checkout funnel calculations are auditable
The system SHALL publish counted attempts and unique accounts as different grains, with step denominators, documented observation windows and clear drop-off rules.

#### Scenario: Repeated attempts by one user
- **WHEN** the same user starts multiple legitimate checkout attempts in the window
- **THEN** attempt counts and unique-account counts are reported separately and approval is not double-counted

#### Scenario: Rolling windows
- **WHEN** a 7-day report and a neighboring 7-day report overlap
- **THEN** the report exposes both boundaries and does not label their difference as daily net growth

### Requirement: Recorded source and payment linkage is descriptive
The system SHALL expose first-known and last-known eligible entry sources before checkout/submission with a stated attribution window and explicit unknown states. The system MUST label proximity as descriptive, not proven causation.

#### Scenario: Most recent tracked entry
- **WHEN** multiple legitimate entry events precede a payment submission
- **THEN** source attribution uses the documented ordering/window rule, and the result is labeled last recorded entry rather than reason for purchase

#### Scenario: No tracked source
- **WHEN** a payment has no eligible owned entry within the selected source window
- **THEN** attribution is reported as `unattributed` rather than guessed from platform or registration

### Requirement: Website traffic cannot impersonate identified users
The system SHALL keep anonymous tagged website visits distinct from known authenticated accounts and registered conversion cohorts.

#### Scenario: Instagram click with no login
- **WHEN** anonymous Instagram-tagged visits are recorded without an authenticated identity join
- **THEN** visit counts may be reported as anonymous traffic but no individual purchase is attributed to those visits

### Requirement: Conversion experiment claims require valid evidence
The system SHALL distinguish an observational funnel improvement from a controlled experiment result and preserve exposure, assignment, eligible cohort and outcome definitions.

#### Scenario: Nonexperimental purchase pattern
- **WHEN** more approved payments follow a particular paywall variant in observational data
- **THEN** the report describes the association and does not claim the variant caused the payments
