# Spec Delta

## Purpose

Defines how HSK AI Pro is sold through lava.top recurring subscriptions as a second, automated path beside the unchanged manual receipt checkout, including admin control, verified activation, renewal, cancellation, refunds, chargebacks and reconciliation.

## ADDED Requirements

### Requirement: Checkout mode selection
The system SHALL expose an admin-selected checkout mode of `manual_only` (default), `lava_only` or `both`, and SHALL compute an effective mode on the server that falls back to `manual_only` whenever lava sales are disabled, unconfigured, have no enabled term, or the requesting client does not support lava.

#### Scenario: Default mode keeps the manual checkout unchanged
- **WHEN** the mode is `manual_only`
- **THEN** the checkout overview contains no lava offer and the manual flow, prices and plans are identical to the current behavior

#### Scenario: Both mode asks about a Visa card
- **WHEN** the effective mode is `both` and the buyer opens Pro checkout
- **THEN** the buyer is asked whether they have a Visa card; "No" opens the current manual flow and "Yes" opens the lava flow

#### Scenario: Unsupported client falls back
- **WHEN** the mode is `lava_only` but the request comes from a client without lava support (Play, an older Android/desktop build)
- **THEN** the overview returns the manual checkout as if the mode were `manual_only`

#### Scenario: Discount and HSK 3.0 flows stay manual
- **WHEN** the buyer opens a referral, admin or feedback discount offer, or the HSK 3.0 unlock
- **THEN** the manual flow is used regardless of the checkout mode until promo-code mapping is enabled

### Requirement: Admin-controlled lava terms
The system SHALL offer lava terms of 1, 3, 6 and 12 months mapped to lava periodicities MONTHLY, PERIOD_90_DAYS, PERIOD_180_DAYS and PERIOD_YEAR and granting 30, 90, 180 and 365 Pro days, and SHALL show and accept only the terms the admin enabled.

#### Scenario: Disabled term is hidden and rejected
- **WHEN** the admin disables the 3-month term
- **THEN** it disappears from the lava overview and a start request for it is rejected; re-enabling it shows it again

#### Scenario: Manual checkout rejects lava-only terms
- **WHEN** a manual quote or receipt submission names a 6- or 12-month plan
- **THEN** the manual endpoint rejects it as before

### Requirement: Server-created invoice owns the purchase
The system SHALL create every lava invoice server-side for the authenticated canonical account and an enabled term, and SHALL treat the returned contract id (and, for renewals, its parent contract id) as the only link between a lava payment and an account. Buyer email SHALL never identify or merge accounts.

#### Scenario: Unknown contract is not granted automatically
- **WHEN** a lava payment arrives for a contract the system did not create (for example a direct profile purchase)
- **THEN** no access is granted, the event is recorded as unmatched and admins are alerted

#### Scenario: One active lava subscription per account
- **WHEN** an account with an active lava subscription, a pending manual receipt or an open chargeback starts a lava checkout
- **THEN** the start request is refused with a specific reason and the manual flow remains available

### Requirement: Verified, idempotent activation
The system SHALL grant or extend Pro for a lava payment only after the lava API reports that contract COMPLETED in the expected currency (and, for renewals, as a renewal of a known parent), and SHALL grant each contract at most once.

#### Scenario: Webhook without API confirmation does not grant
- **WHEN** a success webhook arrives but the lava API reports the contract as not completed, missing or unreachable
- **THEN** no Pro is granted and the webhook receives a non-2xx response when the provider should retry

#### Scenario: Duplicate or concurrent deliveries grant once
- **WHEN** the same success event is delivered several times or concurrently with a reconciliation or admin recheck
- **THEN** exactly one approved payment record exists and Pro is extended exactly once

#### Scenario: Renewal extends from the current end
- **WHEN** a verified renewal arrives while Pro is still active
- **THEN** Pro is extended from the current end date by the term's days and the user is notified

#### Scenario: Forged webhook is rejected
- **WHEN** a webhook arrives without the configured secret key
- **THEN** it is rejected with 401 and nothing is recorded as a payment

### Requirement: Cancellation keeps the paid term
The system SHALL record lava subscription cancellations (by the user in the app, by an admin, by lava, or after a failed renewal) without changing the account's paid end date or payment records.

#### Scenario: User cancels auto-renewal
- **WHEN** the buyer turns off auto-renewal in the app
- **THEN** the lava subscription is cancelled and the app shows that Pro stays active until the current end date

### Requirement: Refund and chargeback revocation
The system SHALL, on a full refund or an initiated chargeback that matches exactly one paid lava payment of the system's own invoices, automatically remove that payment's granted days, mark the payment refunded or chargeback-open and notify the user and admins; otherwise it SHALL flag the event for admin review without changing access.

#### Scenario: Exact full refund shortens Pro
- **WHEN** a full refund matches one paid lava payment
- **THEN** Pro is shortened by that payment's days, the payment is no longer counted as approved and the user is notified

#### Scenario: Ambiguous or partial refund needs review
- **WHEN** a refund is partial or matches zero or several payments
- **THEN** access is unchanged and the event appears in the admin review list

#### Scenario: Chargeback outcome is closed by the admin
- **WHEN** an admin records a chargeback as won
- **THEN** the removed days are restored and the payment counts as approved again; when recorded as lost it stays revoked

### Requirement: Lost-webhook reconciliation
The system SHALL periodically check its open lava invoices and active subscriptions against the lava API and apply any completed payment or renewal through the same idempotent activation.

#### Scenario: Missed webhook is repaired
- **WHEN** a payment completes but its webhook was rejected or lost
- **THEN** the reconciliation grants Pro once within its next cycle

### Requirement: Sales kill-switch and processing pause
The system SHALL stop only new lava checkouts when lava sales are disabled, while continuing to process payments, renewals, refunds and chargebacks of existing contracts; a separate processing pause SHALL durably queue incoming events and apply them once after the pause ends.

#### Scenario: Payment after sales were disabled
- **WHEN** an invoice created before sales were disabled is paid afterwards
- **THEN** Pro is granted while new lava checkouts stay unavailable

#### Scenario: Paused processing loses nothing
- **WHEN** events arrive while processing is paused and the pause is later lifted
- **THEN** each queued payment is applied exactly once

### Requirement: Admin lava control
The Admin PWA SHALL let an authenticated admin, with a per-operation passkey proof and an audit record, view the lava connection preflight and payment state and change mode, terms, offers and currency, recheck a contract, link an unmatched contract to an explicit account, cancel an account's auto-renewal and close a chargeback; secrets SHALL never be displayed or editable.

#### Scenario: Unsafe mode is refused
- **WHEN** the admin tries to save `lava_only` or `both` while the preflight fails or no term is enabled
- **THEN** the save is refused and the current settings remain
