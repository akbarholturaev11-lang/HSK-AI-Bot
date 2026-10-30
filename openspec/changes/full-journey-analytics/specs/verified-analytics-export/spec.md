# Spec Delta

## Purpose

This capability delivers verifiable, time-scoped and privacy-safe aggregate reports from a controlled first-party R2 cache to a public GitHub history, without opening protected personal records.

## ADDED Requirements

### Requirement: GitHub receives aggregates only
The system SHALL export only verified schema-allowlisted aggregate metrics and dimensions to the public analytics mirror. It MUST reject identifiers, receipts, raw text, chat content, feedback bodies, error traces, bearer tokens and unapproved fields.

#### Scenario: Attempt to export private data
- **WHEN** an upstream analytics JSON contains an unexpected user ID, screenshot reference, raw feedback text or token
- **THEN** validation rejects that export without publishing the value, including in logs or immutable history

#### Scenario: Tiny segments
- **WHEN** a combination of approved dimensions produces an individual-identifiable or below-threshold small segment
- **THEN** public output suppresses that segment with a labeled suppression state rather than exposing its value or implying zero

### Requirement: Every report exposes provenance and reporting grain
The system SHALL supply schema version, verified source, section, platform, generated and expiry timestamps, observation date, reporting period, window start, unit, numerator/denominator where applicable, and source coverage.

#### Scenario: Seven-day rolling report
- **WHEN** the consumer opens a weekly report observed on a particular date
- **THEN** it sees `rolling_7_days` with its exact `since` and `generated_at`, and the report is not described as one day's results

#### Scenario: Missing field
- **WHEN** a source metric was not measured for a requested platform
- **THEN** the section states `not_instrumented` or `unavailable` with a reason instead of emitting an invented count

### Requirement: An expired cache is not live data
The system SHALL expire convenient latest aliases according to source timestamps while retaining explicitly historical immutable snapshots and manifest evidence.

#### Scenario: Cache expiration
- **WHEN** the clock exceeds an aggregate `expires_at` without new source data
- **THEN** the GitHub consumer must see history-only or expired status rather than a fresh live claim

### Requirement: Archive synchronization remains a validated mirror
The system SHALL preserve source-locked, versioned R2 objects, strict section-specific field validation, immutability of historical snapshots and idempotent synchronization on a fixed schedule.

#### Scenario: New section fails validation
- **WHEN** a new R2 section includes invalid timestamps, unknown enum values, unexpected content or inconsistent counters
- **THEN** the archive rejects the invalid section and does not overwrite a safe historical snapshot

#### Scenario: Repeated sync
- **WHEN** the R2 objects have not changed since the previous successful sync
- **THEN** repeated GitHub synchronization does not duplicate historical observations

### Requirement: Owner-authorized refresh remains controlled
The system SHALL permit only an authorized owner to trigger recomputation of approved source aggregates, preserve current bounded/serialized refresh and the independent R2→GitHub mirror, and report both stages separately.

#### Scenario: Unauthorized refresh
- **WHEN** a nonowner attempts to request source recomputation
- **THEN** the system rejects the request before any analytics database refresh or secret disclosure

#### Scenario: Source refreshed, mirror failed
- **WHEN** server recomputation succeeds but the downstream GitHub mirror fails
- **THEN** monitoring reports partial completion rather than claiming a new GitHub snapshot exists

### Requirement: User-level detail stays behind first-party authorization
The system SHALL expose owned account journeys only through existing or equivalent audited, authenticated administrative interfaces with least privilege and bounded redacted results. No user-level data SHALL be made available to generic GitHub, public JSON, or unrestricted MCP.

#### Scenario: Public GitHub reader
- **WHEN** a GitHub-only reader accesses any report in the analytics repository
- **THEN** it can inspect summary trends but cannot identify or reconstruct any individual learner's journey

#### Scenario: Unauthorized administrative request
- **WHEN** an unauthenticated or insufficiently authorized caller requests an account timeline
- **THEN** the request is rejected without returning any account data
