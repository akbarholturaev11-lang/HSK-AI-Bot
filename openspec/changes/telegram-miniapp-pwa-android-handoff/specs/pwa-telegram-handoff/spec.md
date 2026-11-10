# Spec Delta

## Purpose

Lets a learner who is verified inside the Telegram Mini App continue in the
learner PWA as the same canonical account, through a short-lived single-use
transfer, without weakening the existing PWA session, CSRF and approval rules.

## ADDED Requirements

### Requirement: Handoff is issued only to a verified, eligible Telegram learner
The system SHALL issue a handoff only for a request carrying fresh, correctly
signed Telegram Mini App data, for an existing non-blocked learner, while the
learner PWA sign-in is enabled and the admin iPhone routing switch is on. The
client SHALL NOT be able to choose the account.

#### Scenario: Verified learner requests a handoff
- **WHEN** a signed-in Mini App learner taps the iPhone PWA offer and all gates are open
- **THEN** the system returns one external landing address bound to that learner and valid for at most 120 seconds

#### Scenario: Missing, forged or stale Telegram proof
- **WHEN** the request has no Telegram data, a wrong signature, or data older than the freshness bound
- **THEN** no handoff is created and the response is an authentication error

#### Scenario: Routing or PWA sign-in is off
- **WHEN** the admin iPhone switch is off or learner PWA sign-in is disabled
- **THEN** no handoff is created

#### Scenario: Blocked learner
- **WHEN** the verified learner is blocked
- **THEN** no handoff is created

#### Scenario: Repeated requests
- **WHEN** the same learner requests another handoff
- **THEN** any earlier unused handoff of that learner stops working, and requests beyond the per-learner limit are refused

### Requirement: The transfer secret is never exposed to servers, logs or third parties in transit
The transfer secret SHALL travel only in the address fragment, SHALL be stored
only as a keyed hash, and the landing page SHALL be first-party, non-cacheable,
referrer-free, script-restricted and SHALL remove the secret from the visible
address before any network request. The address SHALL contain no user id,
cookie, session token or entitlement.

#### Scenario: Landing page is opened
- **WHEN** the external browser opens the landing address
- **THEN** the server receives no secret in the path or query, and the page removes the fragment from history before redeeming

### Requirement: A handoff can be redeemed exactly once
Redemption SHALL be a same-origin request that atomically verifies an
unexpired, unused handoff, the same non-blocked owner and open gates, and only
then issues the existing HttpOnly learner PWA session.

#### Scenario: First valid redemption
- **WHEN** an unused, unexpired handoff is redeemed from the PWA origin
- **THEN** exactly one PWA session for the bound learner is issued and the handoff becomes used

#### Scenario: Replay
- **WHEN** a used handoff is redeemed again
- **THEN** no session is issued

#### Scenario: Parallel redemption
- **WHEN** two redemptions of the same handoff arrive concurrently
- **THEN** at most one session is issued

#### Scenario: Expired or unknown secret
- **WHEN** the handoff is expired or the secret matches nothing
- **THEN** no session is issued and the page offers the existing sign-in

#### Scenario: Cross-origin or wrong transport
- **WHEN** the redemption is not a same-origin JSON request
- **THEN** it is refused before any lookup

#### Scenario: Owner changed after issue
- **WHEN** the learner was blocked or lost that Telegram identity after issue
- **THEN** no session is issued

### Requirement: An existing browser account is never replaced silently
If the browser already holds a valid PWA session of a different learner, the
system SHALL NOT replace it without an explicit switch chosen by the person.

#### Scenario: Same learner already signed in
- **WHEN** the browser session belongs to the handoff owner
- **THEN** the session is kept, the handoff is used up and the learner continues

#### Scenario: Different learner signed in
- **WHEN** the browser session belongs to another learner and no switch was chosen
- **THEN** no session changes, the handoff stays unused and the page asks to switch or stay

#### Scenario: Explicit switch
- **WHEN** the person chooses to switch
- **THEN** only this browser's previous PWA session is revoked and the handoff owner's session is issued

### Requirement: Existing account state and flows are preserved
A redeemed handoff SHALL grant nothing beyond a normal PWA sign-in: level,
progress, Pro, trial, referral and language remain server-owned. Completed
onboarding SHALL NOT be shown again; the existing Home Screen install guide is
shown once to eligible browsers, then the existing course opens. Other sign-in
flows (bot approval, Google/Apple, native link) SHALL behave as before.

#### Scenario: Learner with completed onboarding
- **WHEN** the handoff is redeemed for a learner whose onboarding is complete
- **THEN** the install guide is shown if not yet seen on that browser and the course opens without onboarding

#### Scenario: Handoff row offered to another sign-in path
- **WHEN** a handoff identifier or secret is presented to bot approval, native polling, Telegram claim or an OAuth callback
- **THEN** that path refuses it

#### Scenario: Browser cannot install
- **WHEN** the page opens in an in-app browser that cannot add to the Home Screen
- **THEN** the existing guide shows the manual "open in Safari" hint and never reports an installation
