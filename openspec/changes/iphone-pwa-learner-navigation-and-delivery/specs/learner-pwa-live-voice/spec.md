# Learner PWA Live voice

## Purpose

Make Live voice available to eligible browser learners under the shared voice access and provider policies.

## ADDED Requirements

### Requirement: Authorized Live relay
The PWA SHALL use the existing Live eligibility, time, and budget policies with a browser session bound to the canonical owner.

#### Scenario: Invalid browser relay proof
- **WHEN** a Live connection has a foreign Origin, invalid CSRF or a different session owner
- **THEN** the backend rejects it before claiming the session or opening the upstream provider.

#### Scenario: Live disabled
- **WHEN** the PWA or shared provider policy excludes Live
- **THEN** the PWA leaves turn-based voice and text usable.
