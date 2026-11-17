# Spec Delta

## ADDED Requirements

### Requirement: Route-set subscription entry client
Each subscription entry SHALL store the client of the route that recorded it: `telegram`, `iphone_pwa` or `android`. A caller MUST NOT be able to choose it. Desktop entries and entries recorded before this change MUST keep it empty, so only Overall reads them.

#### Scenario: Forged source prefix
- **WHEN** a Telegram caller opens the subscription overview with source `android_subscription`
- **THEN** the entry's client is `telegram`, and it counts under Telegram only

#### Scenario: Desktop
- **WHEN** a Desktop route records an entry
- **THEN** its client stays empty and no platform view reads it

### Requirement: Platform Subscription Sources
Sources under the Android, Telegram and iPhone PWA filters SHALL report `entries` from that platform's entries, from its first one. `attribution` SHALL match each payment of that platform to the nearest earlier entry of the same account on the same platform, else `unknown`. Public-site traffic MUST NOT be a platform value. Overall Sources MUST stay unchanged.

#### Scenario: Nearer entry on another platform
- **WHEN** an account's nearest entry before a PWA payment was recorded by Telegram or has no client
- **THEN** the payment is attributed to the account's nearest earlier PWA entry, or `unknown`

#### Scenario: Before the first entry
- **WHEN** a platform has no entry with its client yet
- **THEN** `entries` and `attribution` are null and the Admin UI shows "no data", not an empty table or zero

#### Scenario: Payment before the boundary
- **WHEN** a platform's payment was submitted before its first entry
- **THEN** it is left out of that platform's attribution
