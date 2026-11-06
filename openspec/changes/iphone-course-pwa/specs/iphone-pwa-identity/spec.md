# iPhone PWA identity

## ADDED Requirements

### Requirement: Independent authenticated entry
The system SHALL permit a learner to use the standalone iPhone Course PWA without opening Telegram, using only provider sign-in methods verified/configured for this browser client. Anonymous or failed OAuth SHALL NOT mint learner privileges or pass through a Telegram Mini App API guard.

#### Scenario: First visit without Telegram
- **WHEN** a learner opens the PWA URL or installed Home Screen application without a session
- **THEN** the application presents an explicit browser sign-in flow, without assuming `Telegram.WebApp.initData` exists
- **AND** protected course/account requests are denied until verified login succeeds

#### Scenario: Unconfigured provider
- **WHEN** the selected provider is unavailable or redirect/origin configuration is incomplete
- **THEN** the application fails closed with a localized actionable message
- **AND** it does not create a dummy identity or silent Telegram fallback

### Requirement: Secure browser session authority
The system SHALL provide a standalone, revocable and short-lived browser session rooted in the authenticated canonical user, using HttpOnly Secure cookies with an appropriate SameSite policy, CSRF protection for mutations, origin checks, token rotation and login/logout boundaries. The design SHALL evaluate OAuth state, PKCE/nonce and redirect binding as applicable, account/session expiry, rate limiting and fixation/replay protection. Native Android/Desktop tokens SHALL NOT be copied to browser localStorage.

#### Scenario: Forged, expired or cross-site mutation
- **WHEN** a browser mutation has an invalid/expired session, missing valid CSRF binding or untrusted origin
- **THEN** the server denies the operation without changing user state

#### Scenario: Logout or revoked identity
- **WHEN** the user logs out, unlinks a necessary credential or revokes a session
- **THEN** the browser cannot continue to use prior session authority, and sensitive in-memory state is cleared

#### Scenario: Browser versus installed PWA container
- **WHEN** the same learner enters through Safari and a Home Screen installation with independent storage/session containers
- **THEN** both contexts independently authenticate or restore only their own verified sessions
- **AND** account identity is never inferred from a shared installation key or local preference

### Requirement: Canonical account and explicit linking
The system SHALL retain `users.id` as the authoritative account key, use verified provider subject mapping, and offer optional explicit Telegram account linking only after secure ownership proof and user confirmation. Email/name matches SHALL NOT cause automatic merges; null `telegram_id` SHALL be valid and a fabricated Telegram ID SHALL never be written.

#### Scenario: Existing learner signs in with a linked provider
- **WHEN** a verified provider subject is already linked to canonical user U
- **THEN** the browser session resolves to U and retains U's existing progress, entitlements and history

#### Scenario: Conflicting Telegram account link
- **WHEN** a signed-in PWA account requests to link a Telegram identity already owned by another canonical user
- **THEN** linking is refused or follows an explicitly approved conflict resolution process
- **AND** neither account's Pro, history or payments are silently moved

#### Scenario: Browser-only learner
- **WHEN** a verified PWA learner has `telegram_id=NULL`
- **THEN** learner services operate by canonical user where supported
- **AND** Telegram-only transport actions cannot send to this user or fabricate a chat ID

### Requirement: Session and lifecycle security regressions
All PWA authentication changes SHALL be tested against blocked/deleting users, session revocation, independent devices, real Telegram Mini App initData and existing Android/Desktop login flows.

#### Scenario: Telegram regression guard
- **WHEN** the new browser transport is deployed but a Telegram Mini App sends missing or forged initData
- **THEN** existing Telegram endpoints still reject that request and cannot accept a PWA cookie as a bypass
