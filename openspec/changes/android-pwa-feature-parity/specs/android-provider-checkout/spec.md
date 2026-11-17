# Native provider checkout

## Purpose

Let Direct Android learners use existing server-configured Pro provider sales while retaining verified billing and channel policy.

## ADDED Requirements

### Requirement: Channel-safe server pricing
Direct SHALL display only sellable server-priced 1/3/6/12-month Lava plans when enabled and retain existing manual receipt checkout. Play SHALL contain no provider checkout consumer or external payment CTA.

#### Scenario: Disabled sales or unsupported product
- **WHEN** Lava sales are off, legacy capability is absent, or checkout is for HSK 3.0 unlock
- **THEN** existing manual behavior remains and no new provider invoice is created.

#### Scenario: Provider checkout
- **WHEN** Direct chooses a priced plan and supplies valid email
- **THEN** a bearer-owned invoice is created with source android and opens only an allowlisted HTTPS provider page in the external browser.

### Requirement: Verified payment and cancellation
Android SHALL grant no access from browser return or client status hints. Status and cancellation SHALL verify canonical owner; payment application, refund and cancellation SHALL retain existing shared transaction semantics and financial analytics.

#### Scenario: Pending or another account invoice
- **WHEN** a browser returns before payment verification or another account asks for the invoice
- **THEN** pending stays pending and another account receives no invoice data.

### Requirement: Real one-time exit offer
An exit offer SHALL use the existing canonical account row, provider promo mapping, 24-hour expiry and consumed state across PWA and Direct. A client-selected exit mode alone SHALL authorize no discount.

#### Scenario: Missing promo or unclaimed offer
- **WHEN** there is no real configured provider promo or no accepted unexpired offer
- **THEN** no 20% claim or discounted checkout succeeds.

#### Scenario: Accepted offer
- **WHEN** Direct accepts a valid offer and completes provider payment
- **THEN** the actual provider promo is applied and server verification consumes the same offer once.
