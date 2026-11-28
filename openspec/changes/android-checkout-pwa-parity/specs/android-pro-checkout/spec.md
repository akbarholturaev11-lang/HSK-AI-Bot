## Purpose
Keep native Android Pro and limit checkout visually coherent while preserving server-owned payment outcomes and channel restrictions.

## ADDED Requirements

### Requirement: Unified checkout navigation
Android Direct SHALL center the Pro heading between a left navigation action and right support action. Only the first step SHALL show X; subsequent steps SHALL provide one-step Back and retain selections.

#### Scenario: Email and manual payment Back
- **WHEN** a learner opens an email or manual payment step and presses the header or system Back
- **THEN** the previous checkout step appears with the selected plan and country intact and no duplicate exit control.

#### Scenario: Manual tariff handoff
- **WHEN** a learner confirms the manual tariff already displayed in the limit offer
- **THEN** checkout uses that authenticated sellable plan without repeating plan selection, asks for TJ bank or China wallet where applicable, and proceeds to requisites; Back preserves the exact main/More parent.

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


### Requirement: Android Pro attempts use the PWA counting method
The Android Pro funnel SHALL group by canonical account and attempt ID, count the maximum verified stage within the attempt cohort, and expose opened, plan selected, invoice created and paid under Android and Overall only. Client observations MUST NOT write invoice-created or paid stages.

#### Scenario: Retries and user switching
- **WHEN** a UI event is replayed or an account is replaced while telemetry waits
- **THEN** a replay is idempotent and no queued observation is attributed to the replacement account.

#### Scenario: Financial truth and platform separation
- **WHEN** a provider payment is confirmed, refunded or loses a chargeback
- **THEN** server-owned invoice/payment facts determine paid and reversed counts, and neither Android nor PWA attempts enter the other platform's metric.

#### Scenario: Manual and unavailable telemetry
- **WHEN** a learner chooses manual checkout or an analytics request fails
- **THEN** the existing manual receipt funnel continues, the Android inline provider funnel does not fabricate a paid conversion, and checkout remains usable.
