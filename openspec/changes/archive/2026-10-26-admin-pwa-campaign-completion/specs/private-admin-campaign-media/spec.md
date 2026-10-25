# Spec Delta

## Purpose

Allow first-party administrators to attach validated campaign media without exposing provider credentials, accepting foreign media references or storing binary data in SQL.

## ADDED Requirements

### Requirement: Private owned staging
A staged asset SHALL be bound to the current authenticated administrator and browser session, have a short expiry and be unavailable to other sessions or external MCP. Provider references MUST remain server-owned and MUST NOT be accepted from the browser.

#### Scenario: Foreign asset
- **WHEN** another administrator or a different session supplies an asset identifier
- **THEN** preparation, preview and execution deny access without provider work

### Requirement: Bounded validation and provider work
Photo and video inputs SHALL be bounded, decoded or probed, and rejected before publication when invalid. Quotas and limited processing slots MUST precede expensive provider work. No database connection SHALL span provider upload or video encoding, and SQL MUST contain no media bytes.

#### Scenario: Failed upload
- **WHEN** upload times out or its final state is uncertain
- **THEN** it is not automatically retried and cannot authorize campaign delivery

### Requirement: Exact attachment commitment
The campaign proof SHALL bind the owned asset identifier, validated type, source hash, byte count and server provider reference commitment. Changed, failed or expired staging MUST fail atomically with the campaign and audit.

#### Scenario: Changed asset
- **WHEN** the staged media differs from the prepared commitment
- **THEN** no campaign, recipient work or consumed proof is committed

### Requirement: Bounded retention
Expiry cleanup SHALL operate in bounded pages, preserve referenced campaign assets and immutable content-free evidence, and refuse lossy schema rollback with retained data.

#### Scenario: Used asset retention
- **WHEN** an expired staging page contains an asset already attached to a retained campaign
- **THEN** cleanup does not remove the campaign's provider media
