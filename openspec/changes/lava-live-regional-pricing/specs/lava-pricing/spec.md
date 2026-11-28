## Purpose

Keep learner subscription prices aligned with the merchant's verified Lava catalog without requiring an Admin Save for every price change, while preserving currency policy and canonical billing ownership.

## ADDED Requirements

### Requirement: Prices refresh independently of settings saves
The server SHALL obtain sellable subscription prices from Lava automatically. A successful cached catalog SHALL expire within 60 seconds; concurrent refreshes SHALL share one read. Merchant reads SHALL hold no SQL transaction and SHALL finish within a bounded deadline.

#### Scenario: Merchant changes a price
- **WHEN** Lava changes a configured offer's USD or RUB price and the cache expires
- **THEN** the next overview uses the new verified price without Admin Save or a database settings write

#### Scenario: Concurrent cold requests
- **WHEN** multiple learners request prices while the cache is cold
- **THEN** they share one bounded catalog read and retain separate identity, entitlement and discount decisions

### Requirement: One selector controls enabled currencies
The existing signed Admin settings editor SHALL offer USD, RUB and USD + RUB. The selected policy SHALL be enforced by overviews and new invoice requests. Existing region selection rules SHALL remain unchanged. A missing provider price SHALL never be estimated locally.

#### Scenario: Both currencies enabled
- **WHEN** USD + RUB is selected and valid provider prices exist
- **THEN** Russia can choose RUB and the other supported card route can choose USD through the existing regional behavior

#### Scenario: Currency disabled
- **WHEN** an authenticated client requests a currency excluded by the saved policy
- **THEN** the server refuses it before creating a provider invoice

### Requirement: Existing clients retain their default
Clients omitting currency SHALL retain the configured legacy USD/RUB default. Existing configuration without the new policy SHALL preserve its current two-currency availability. No request shape required by an installed APK SHALL become mandatory.

#### Scenario: Old APK starts checkout
- **WHEN** an authenticated supported old caller omits currency
- **THEN** its configured default currency is used with a live verified offer price

### Requirement: Catalog failure cannot fabricate payment authority
Expired, failed or invalid catalog data SHALL NOT become a newly payable price. Provider errors SHALL retain bounded recovery, existing manual-mode permissions and content-free monitoring. An invoice POST SHALL never be automatically retried.

#### Scenario: Provider is unavailable
- **WHEN** a fresh catalog cannot be verified by the deadline
- **THEN** no invoice is created from an old stored price and the existing permitted recovery path remains usable

### Requirement: Historical billing and attribution stay fixed
New invoice amounts SHALL be tied to the chosen verified offer/currency and actual provider total. Existing invoices, refunds, renewals, webhook-only access, discounts, canonical owner and attempt/source deduplication SHALL remain unchanged.

#### Scenario: Price changes after a paid invoice
- **WHEN** the merchant changes the catalog after an invoice was paid
- **THEN** historical revenue, refund matching and paid access still use that invoice's recorded currency and amount

#### Scenario: Invoice response supplies the actual total
- **WHEN** Lava returns a valid total for a new invoice
- **THEN** that total is recorded under the reserved canonical owner and no conversion or Pro grant is inferred from the client redirect
