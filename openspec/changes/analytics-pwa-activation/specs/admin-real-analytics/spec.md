# Spec Delta

## ADDED Requirements

### Requirement: PWA activation
The onboarding routes SHALL tag `onboarding_completed` and its choice rows with a route-set client: PWA `iphone_pwa`, Telegram `telegram`, Android `android`. The caller's payload MUST NOT set it. Course > iPhone PWA SHALL report `activation` and `direct_activation` from the PWA-tagged onboarding cohort. It SHALL also report `handoff_activation` from the Telegram → PWA handoff cohort. Only PWA-tagged steps count in either cohort.

#### Scenario: New PWA learner
- **WHEN** a learner finishes onboarding on the PWA and starts a lesson there within 2 minutes
- **THEN** Course > iPhone PWA `activation` counts that learner as eligible and started, from `attributed_since.activation` on

#### Scenario: Learner onboarded elsewhere
- **WHEN** an account finished onboarding in the Telegram Mini App or on Android, even with a caller `client` value
- **THEN** it is not in the PWA onboarding cohort, and Overall activation is unchanged

#### Scenario: Telegram to PWA handoff
- **WHEN** an account redeems a Telegram → PWA handoff at least 24 hours ago
- **THEN** `handoff_activation` counts it as eligible, and as activated only if a PWA-tagged lesson start or completion followed within 24 hours

#### Scenario: Before the boundary
- **WHEN** no PWA-tagged onboarding or PWA boundary row exists yet
- **THEN** the PWA values are `null` with state `no_data`, never zero

#### Scenario: Too many rows
- **WHEN** a cohort's rows exceed the detail row limit
- **THEN** that value is `null` and `detail_limited` is true
