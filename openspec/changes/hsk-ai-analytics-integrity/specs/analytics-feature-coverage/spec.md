# Spec Delta

## Purpose

Prevents HSK AI features from silently falling outside analytics. Every Admin V10 metric and every critical flow keeps a declared, CI-checked platform coverage status. A status counts as connected only when there is end-to-end test evidence.

## ADDED Requirements

### Requirement: Platform and section coverage registry
The repository SHALL keep a machine-readable registry. It lists every metric shown in the Admin V10 sections (Overview, Course, Platforms, Funnel, Finance, Sources, Report) and every critical business flow. Each gets a status per platform: Android, Telegram Mini App, iPhone PWA, macOS and Windows. A status is `covered`, `partial`, `not_instrumented` or `not_applicable`. Every status other than `covered` needs a concrete reason.

#### Scenario: Metric missing from the registry
- **WHEN** an Admin section returns a metric key that has no registry entry
- **THEN** the coverage check fails and names the section and metric key

#### Scenario: Justified not-applicable platform
- **WHEN** a metric does not concern a platform, such as desktop device inventory for the Telegram Mini App
- **THEN** the entry is `not_applicable` with its reason and the check accepts it

#### Scenario: Status without reason
- **WHEN** an entry is `partial`, `not_instrumented` or `not_applicable` with an empty reason
- **THEN** the check fails and names the entry

### Requirement: Covered requires end-to-end chain evidence
An entry SHALL be `covered` only when it names an existing executable test. That test sends the event through its real API or server path, stores it in PostgreSQL, aggregates it, and shows it in the correct Admin PWA section and platform filter. A stored event, an event enumeration or a passing unit test alone MUST NOT count as integration evidence.

#### Scenario: Stored but not displayed
- **WHEN** an event is persisted, but no Admin projection or view shows its metric
- **THEN** the entry cannot be `covered` and must be `partial` with the reason "no Admin consumer"

#### Scenario: Named chain test missing
- **WHEN** a `covered` entry names a chain test that does not exist in the repository
- **THEN** the coverage check fails

### Requirement: Analytics Impact for every behavior change
Every change that adds or changes a feature, screen or important user action SHALL be preceded by an inspection of the existing analytics for that flow. In the same change it SHALL either wire the event, store, aggregation, Admin view, registry entry and chain test, or record a justified `not_applicable`. Purely cosmetic copy/CSS changes and refactors that leave behavior unchanged need no new telemetry.

#### Scenario: New screen on one platform
- **WHEN** a coding agent adds a new screen with a meaningful user action to the PWA
- **THEN** the same change updates the registry and either connects the metric with its chain test or records `not_applicable` with a concrete reason

### Requirement: CI coverage guard
An `analytics-integrity` CI check SHALL run on pushes and pull requests. It SHALL fail, naming the affected files and event names, when any of these holds:
- a critical-flow path or a recorded event name changes without a matching registry change or reviewed exemption;
- a registered event no longer exists in code;
- a recorded critical event is unregistered.

A change that touches only copy, CSS or localization MUST pass without new telemetry.

#### Scenario: Unmapped new event
- **WHEN** a change adds a recorded event name without a registry entry or exemption
- **THEN** the check fails and reports the event name and the file that introduced it

#### Scenario: Cosmetic-only change
- **WHEN** a change touches only copy, styling or localization resources
- **THEN** the check passes

#### Scenario: Stale registry entry
- **WHEN** an event is removed from code but is still registered
- **THEN** the check fails and identifies the stale entry

### Requirement: Reviewed exemptions
An exemption SHALL name exact paths or event names, carry a concrete reason, and be visible in the reviewed diff. An exemption MUST NOT disable the check globally or for a whole directory.

#### Scenario: Directory-wide exemption
- **WHEN** an exemption names a whole directory or has an empty reason
- **THEN** the check fails and reports the invalid exemption

### Requirement: Durable agent rule
The root agent instructions SHALL keep the permanent analytics coverage rule and point to the registry and CI check once they exist. The rule's enforcement status MUST describe only mechanisms that actually exist on the main branch.

#### Scenario: Guard delivered
- **WHEN** the registry and the CI check land on the main branch
- **THEN** the agent rule names them as active, and no longer calls them planned
