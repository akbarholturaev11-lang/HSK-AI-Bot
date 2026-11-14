# iPhone PWA payments and entitlement parity

## ADDED Requirements

### Requirement: Canonical subscription and entitlement ownership
The PWA SHALL use existing server-owned subscription, trial, provisional/pending receipt, HSK unlock, AI-budget and access policy semantics keyed by canonical `users.id`; no PWA-only boolean Pro shortcut or unreviewed payment/provider entitlement shall exist.

#### Scenario: Paid account across clients
- **WHEN** a learner with a verified paid subscription opens the PWA through a linked canonical account
- **THEN** the same server-authorized features and remaining limits apply as on the other clients

#### Scenario: Pending payment receipt
- **WHEN** a PWA user submits a receipt pending review
- **THEN** the UI shows only the permitted pending-preview state
- **AND** no paid sale, unlimited AI budget or permanent Pro state is inferred before approval

### Requirement: Browser-safe purchase, return and receipt handling
Existing price, payment method, QR/receipt, review and refund policies SHALL remain authoritative. PWA checkout SHALL have an explicit browser return/failure/retry flow and server-verified payment status, without assuming a Telegram SDK close/back/callback or a persistent Safari-to-Home-Screen session.

#### Scenario: External provider return
- **WHEN** a checkout opens an external browser/payment provider and returns to the learner
- **THEN** the PWA restores or reestablishes a verified current session and reads confirmed server payment state
- **AND** it never treats a client return URL as proof of payment

#### Scenario: Repeat receipt or stale login
- **WHEN** a receipt is resubmitted, duplicated, or arrives after logout/account change
- **THEN** existing idempotent review/ownership safeguards prevent duplicate grants or attribution to the wrong account

### Requirement: Referrals, trials and existing history
The PWA SHALL preserve existing one-time trial/referral/feedback reward restrictions and history across linked identities; optional Telegram linking cannot create a second onboarding signup or duplicate reward, and Telegram-only contact features SHALL require an actual linked Telegram ID.

#### Scenario: Existing Telegram learner links browser identity
- **WHEN** an authenticated existing learner explicitly links a PWA login and revisits the course
- **THEN** existing progress, subscriptions and prior rewards remain on that canonical user
- **AND** no new-user referral, trial or course reward is minted for linking

#### Scenario: Browser-only learner requests Telegram-only messaging
- **WHEN** a browser-only account without a real Telegram ID triggers a Telegram-only notification or referral transport
- **THEN** the system reports transport unavailability rather than inventing a Telegram address
