## Purpose
Keep native Android Pro and limit checkout visually coherent while preserving server-owned payment outcomes and channel restrictions.

## ADDED Requirements

### Requirement: Unified checkout navigation
Android Direct SHALL center the Pro heading between a left navigation action and right support action. Only the first step SHALL show X; subsequent steps SHALL provide one-step Back and retain selections.

#### Scenario: Email and manual payment Back
- **WHEN** a learner opens an email or manual payment step and presses the header or system Back
- **THEN** the previous checkout step appears with the selected plan and country intact and no duplicate exit control.

### Requirement: Inline limit offer
Direct limit entry SHALL use the PWA inline offer composition with canonical Panda, benefits, server-priced primary terms, other terms, and one primary action. Play SHALL retain consumption-only access checks without checkout.

#### Scenario: Available and unavailable terms
- **WHEN** the server returns available plans or missing prices
- **THEN** only real priced plans are actionable and loading/error states preserve a usable dismissal path.

### Requirement: Verified provider return
A pending invoice SHALL refresh immediately on foreground return and poll only while foregrounded for a bounded interval. Redirect, timeout, or missing acknowledgement MUST NOT grant Pro or create another invoice.

#### Scenario: Delayed confirmation
- **WHEN** the learner returns before the payment webhook arrives
- **THEN** the screen remains pending until a later server response confirms paid, then offers return to refreshed learning access.

#### Scenario: Pending invoice recovery
- **WHEN** the checkout is recreated or a start response was lost
- **THEN** canonical pending invoice recovery precedes any new start and failed reads remain retryable.
