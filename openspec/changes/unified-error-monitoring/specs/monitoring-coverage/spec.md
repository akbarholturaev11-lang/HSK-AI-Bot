# Spec Delta

## Purpose

Makes error monitoring a permanent obligation of every future important feature. An agent rule and a CI merge-block keep new PWA, Android and Backend features connected to failure intake, incidents and the Admin Inbox from their first version.

## ADDED Requirements

### Requirement: Durable Monitoring Impact rule
The root agent instructions SHALL require, for every new or materially changed PWA, Android or Backend feature, a stated Monitoring Impact in the same task. The statement covers failure signals, feature and failure codes, the intake used, the incident mapping, the Admin Inbox consumer and test coverage, or gives a concrete `not_applicable` reason. Its enforcement status MUST describe only mechanisms that exist on the main branch.

#### Scenario: Agent adds a feature
- **WHEN** a coding agent adds a new learner feature with a server route
- **THEN** the same change states its Monitoring Impact and updates the coverage registry without being reminded

#### Scenario: Cosmetic change
- **WHEN** a change only edits copy, styling or localization resources
- **THEN** no telemetry is invented, and the change passes without a Monitoring Impact entry

### Requirement: Monitoring section of the shared coverage registry
The existing Analytics coverage registry SHALL gain one monitoring section. It records, per feature and platform: error source, reporter, authenticated intake, incident mapping, Admin consumer and tests, with status `covered`, `partial`, `not_instrumented` or `not_applicable` and evidence or a reason. Features SHALL use the Analytics flow IDs and platform keys. A monitoring-only ID is allowed only where no Analytics flow exists.

#### Scenario: Duplicate identifier
- **WHEN** a monitoring entry defines a feature ID or platform key that duplicates an existing Analytics flow or platform under another name
- **THEN** the coverage check fails and names the entry

#### Scenario: Mapping disagrees with Analytics
- **WHEN** a route in an Analytics critical path is mapped to a feature that is neither one of that path's flows nor a monitoring-only ID
- **THEN** the check fails and names the route and both mappings

#### Scenario: Analytics registry unaffected
- **WHEN** the monitoring section is added or changed
- **THEN** the existing Analytics schema, chain-test and diff checks give the same results as before

#### Scenario: Status without evidence
- **WHEN** an entry is `partial`, `not_instrumented` or `not_applicable` without a reason, or `covered` without its tests
- **THEN** the check fails and names the entry

### Requirement: Covered requires a real chain test
A monitoring entry SHALL be `covered` only with two tests, both executed by CI. A client-side test proves the reporter emits the event on the failure. An integration test sends it through the real authenticated intake into PostgreSQL, deduplicates it, and reads it from the authenticated Admin Inbox API. The integration test SHALL leave a runtime proof in the same CI run. An enum, registry row, mocked intake or stored row alone MUST NOT count.

#### Scenario: Test not run by CI
- **WHEN** a `covered` entry names a test that the CI workflow does not execute
- **THEN** the check fails

#### Scenario: Chain test skipped
- **WHEN** a `covered` entry's chain test is skipped, or never reaches the shared chain helper, in the CI run
- **THEN** no proof row exists for it, and the check fails

#### Scenario: Test does not reach the Inbox
- **WHEN** a named integration test does not call the real intake route and the Admin Inbox API with the entry's failure code
- **THEN** the check fails and reports the missing link

### Requirement: CI blocks unmonitored important features
From the first monitoring work package, the existing analytics integrity workflow SHALL fail on pushes and pull requests when a change adds a learner-facing backend route, Android feature package or learner PWA page with no monitoring entry, or with an entry neither `covered` nor justified `not_applicable`. Until the diagnostic Inbox source exists, `partial` with a pending-consumer reason is also accepted; after that, the weaker mode MUST fail.

#### Scenario: New unmonitored route
- **WHEN** a change adds a learner API route and no monitoring entry covers it
- **THEN** CI fails, naming the route and the file that introduced it

#### Scenario: New monitored feature
- **WHEN** a change adds an Android feature package with a `covered` entry and both tests passing
- **THEN** CI passes

#### Scenario: Justified not applicable
- **WHEN** a new route only serves static, cosmetic or monitoring-irrelevant content and its entry is `not_applicable` with a concrete reason
- **THEN** CI passes, and the reason is visible in the reviewed diff

#### Scenario: Weaker mode left on
- **WHEN** the diagnostic Inbox source exists in code but the registry still uses the pre-Inbox declaration mode
- **THEN** the coverage check fails

### Requirement: Frozen legacy baseline
Existing features without full monitoring coverage SHALL be listed in a frozen baseline. The baseline MAY only shrink. An entry's status MUST NOT be lowered without a reviewed exemption.

#### Scenario: Baseline grows
- **WHEN** a change adds a feature to the legacy baseline or lowers an entry from `covered` to `partial`
- **THEN** CI fails unless a reviewed exact exemption with a reason is part of the change

#### Scenario: Legacy flow covered later
- **WHEN** a change brings a baseline feature to `covered`
- **THEN** CI passes, and the entry leaves the baseline

### Requirement: Guard against bypass
The check SHALL detect learner routes, Android feature packages, PWA pages and reporter code literals from source, not from a hand-written list. Route detection SHALL include router prefixes and programmatic registration. Exemptions MUST name exact paths or feature IDs with a concrete reason. Directory-wide or empty-reason exemptions MUST fail.

#### Scenario: Route added through a router prefix
- **WHEN** a change adds a learner route through an `APIRouter` prefix or `add_api_route`, with no monitoring entry
- **THEN** the check fails and names the full route path

#### Scenario: Directory exemption
- **WHEN** an exemption names a whole directory or has an empty reason
- **THEN** the check fails and reports the invalid exemption

#### Scenario: Unknown reporter code
- **WHEN** Android or PWA reporter code uses a failure code that is not in the server catalog
- **THEN** the check fails, naming the file and the code

### Requirement: Monitor self-checks
The CI suite SHALL include regression tests for the monitor itself. They cover schema compatibility of the intake, auth and privacy rejection, deduplication under concurrency, rate limits, offline retry and account switch, and the Admin projection. CI results SHALL be reported separately from staging and real-device acceptance.

#### Scenario: Intake contract broken
- **WHEN** a change makes the intake accept a forbidden field or lose idempotency
- **THEN** a self-check test fails in CI and blocks the merge
