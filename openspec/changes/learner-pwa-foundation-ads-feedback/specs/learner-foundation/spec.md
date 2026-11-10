# Foundation completion

## Purpose
Keep foundation completion durable and consistent across authenticated learner clients.

## ADDED Requirements

### Requirement: Acknowledged completion
Clients SHALL show foundation completion only after the server commits a valid current foundation result for the authenticated canonical owner.

#### Scenario: PWA without Telegram
- **WHEN** a verified PWA learner finishes all foundation steps
- **THEN** completion is committed and visible in Android and subsequent course maps.

#### Scenario: Failed or lost response
- **WHEN** completion fails or the response is lost
- **THEN** the learner retains answers and can retry without false success or duplicate completion records.

### Requirement: Shared ownership and analytics
Foundation start, interaction and completion SHALL use existing canonical account event storage and existing Admin foundation metrics, with version and event deduplication.

#### Scenario: Cross-client replay
- **WHEN** the same account retries the same foundation from different clients
- **THEN** one completion remains and other accounts remain incomplete.
