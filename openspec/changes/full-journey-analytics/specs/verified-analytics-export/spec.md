# Spec Delta

## Purpose

**Phase 1: reuse existing R2 aggregate snapshots, extend public GitHub verified export, preserve the existing 16-counter overview mirror.** No runtime instrumentation, account-level user journey, Smart Reminder modifications or new business logic in this phase. Source freshness and original coverage MUST remain truthful.

## ADDED Requirements

### Requirement: The bridge exports only verified source-specific aggregates

The system SHALL read from a fixed, server-reviewed allowlist of supported R2 source kinds, approved section-specific namespaces and period/platform variants. Each section SHALL be identified by a validated source signature and its original scope; no arbitrary R2 object or user-provided path shall be accepted. The public analytics repository MUST contain only schema-allowlisted, nonidentifying aggregates.

#### Scenario: Existing course and checkout aggregates

- **WHEN** a valid R2 `course` or `funnel` aggregate is present and fresh for a supported period
- **THEN** GitHub publishes a separate, source-identified safe aggregate section with its original grain, scope, generation time and exact window, independently of the legacy overview slices

#### Scenario: Arbitrary private field

- **WHEN** any upstream payload contains a new unreviewed identifier, raw feedback text, payment screenshot reference, token, per-user timeline, trace or arbitrary dimension
- **THEN** that field is not published or logged; unknown/unsafe source schemas are rejected without replacing previously safe history

### Requirement: Current overview compatibility is unchanged

The system SHALL preserve the existing 16 allowlisted overview counts, compatibility paths and meanings while adding independent source-derived sections in distinct paths.

#### Scenario: Previously supported GitHub consumer

- **WHEN** an existing reader accesses `overview/latest.json`, `users/latest.json`, `sales/latest.json`, `payments/latest.json` or `courses/latest.json`
- **THEN** it obtains the same overview-derived compatibility schema, not newly redefined `money` or `course` metrics

### Requirement: Cache presence is separate from source completeness

The system SHALL distinguish present, missing, expired, invalid, partially recorded and uninstrumented section-period variants. Source-side warming SHALL reuse existing projections and respect real supported periods and fixed execution/cooldown budgets. A scheduled GitHub mirror MUST remain a read-only R2 consumer and SHALL NOT force SQL reads.

#### Scenario: Demand-driven cache never generated

- **WHEN** a supported `sources/monthly` aggregate has never been requested or generated
- **THEN** GitHub reports `missing` or `not_cached` and never fabricates a zero or silently substitutes another period

#### Scenario: Expired feedback aggregate

- **WHEN** only an expired `feedback/all_weekly` R2 object is available
- **THEN** the source is not marked fresh; any approved owner refresh produces a new verified snapshot before it may be published as fresh

#### Scenario: Bounded owner refresh fails halfway

- **WHEN** an authorized multisection source refresh exceeds its budget or a section cannot be computed
- **THEN** it reports per-section success/failure separately, never falsely claims complete success and preserves last known safe history

### Requirement: Coverage, grain and historical windows are explicit

Every aggregate SHALL retain or supply section, original generated/expiry times, period, window, population/denominator where measurable, source, observation date and actual coverage. A metric based on capped rows SHALL be marked partial or unavailable and MUST NOT be generalized to complete history. Overlapping 7-day and 30-day snapshots SHALL NOT be interpreted as independent daily counts.

#### Scenario: 5,000-row detail cap

- **WHEN** `course`, `funnel` or `experiments` projections cannot calculate a complete detail metric within their existing row cap
- **THEN** the export marks that field unavailable/limited instead of supplying a guessed count or total

#### Scenario: Limited feedback classification

- **WHEN** `feedback` only scanned at most 500 most recent records per source
- **THEN** the output retains source coverage, scanned count and truncation metadata and never claims full-population categories

#### Scenario: Mixed all-time metrics

- **WHEN** an `all_time` section includes an existing recent 30-day detail measure
- **THEN** both current-stock and recent-detail grains remain distinguished and the 30-day metric is never called lifetime activity

### Requirement: Expired data is history, not live truth

The system SHALL retain immutable, timestamped, idempotent histories but expire latest aliases/status as prescribed; malformed inputs MUST NOT overwrite valid existing history.

#### Scenario: Stale data

- **WHEN** the current time is beyond source `expires_at`
- **THEN** the manifest reports expired/history-only as appropriate and does not label the object fresh

#### Scenario: Repeated R2 sync

- **WHEN** a six-hour mirror run sees the same source timestamps and content
- **THEN** it does not create duplicate history entries or update unrelated reports

### Requirement: Public aggregates resist identification

The system SHALL permit only fixed safe grouped dimensions and bounded categories; low-count/rare combinations with re-identification risk SHALL be suppressed or not published. Hashing identifiers is not sufficient sanitization. Private feedback bodies and protected account-specific data remain outside GitHub.

#### Scenario: Single-account segment

- **WHEN** a platform/plan/source combination reveals a single account
- **THEN** the detailed segment is suppressed, rather than being published with a hashed key or disguised identifier

### Requirement: Exported aggregate evidence supports actionable, code-grounded weekly improvement analysis

The system SHALL make available a versioned index and source-specific safe aggregate projections that a read-only weekly HSK AI improvement agent can discover and interpret with section, exact time window, freshness, grain, denominator where measured, completeness and source definition. This SHALL enable the agent to inspect the **current HSK-AI-Bot main code and relevant tests independently** before proposing a specific, minimal, user-visible product improvement. Neither the export nor the agent SHALL assert an unverified code defect, causal uplift or unsupported drop-off, nor perform autonomous product/code changes.

#### Scenario: Genuine checkout friction observation

- **WHEN** a fresh, correctly attributed source-derived checkout funnel contains complete stage counts with verified denominators and a documented observation window
- **THEN** a weekly agent can identify the specific observed dropout stage, inspect the matching current checkout flow code and tests, and propose a ranked, testable improvement with affected files, user-visible behavior, relevant guardrails, rollback and a measurable outcome; descriptive association is not presented as causation

#### Scenario: Missing or partial journey evidence

- **WHEN** the requested platform has no instrumented event, an aggregate is expired, or an existing projection refuses to calculate detail beyond its source cap
- **THEN** the index/report marks that limitation and the agent is able to present a specific measurement or data-quality gap instead of fabricating a bug, conversion loss or improvement percentage

#### Scenario: Legacy overview-only reader

- **WHEN** only the old 16 overview counts are available
- **THEN** the weekly agent can still provide source-qualified observations and inspect relevant code, but MUST NOT claim that complete payment, lesson or user-journey drop-off was measured without an independent verified funnel

#### Scenario: Recommendation must not change production

- **WHEN** an agent proposes a priority improvement based on the latest published statistics and reviewed source code
- **THEN** its output is a read-only implementation brief requiring separate owner approval for any commits, deployment, notifications, payment changes or other actions

### Requirement: Cross-repository validation and rollback

The rollout SHALL preserve the existing owner-only authorized refresh, locked/idempotent publisher and six-hour R2-only GitHub sync. It SHALL provide source/R2/GitHub parity checks for identical sections, periods and observation timestamps, plus focused regression and privacy tests, before any `main` merge or production deployment.

#### Scenario: Source and mirror disagree

- **WHEN** Admin PWA, R2 and GitHub disagree for the same verified projection timestamp and period
- **THEN** the mismatch is reported and the new section rollout is held while existing 16-counter overview compatibility remains available

#### Scenario: Unsafe publishing discovered

- **WHEN** testing detects any prohibited personal datum in GitHub output or logs
- **THEN** the new section publication is disabled and the old verified 16-counter bridge continues unchanged
