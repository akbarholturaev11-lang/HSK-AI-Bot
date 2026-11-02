# iPhone PWA installation and lifecycle

## ADDED Requirements

### Requirement: Independent installed learner surface
The system SHALL provide an HTTPS learner Course PWA entry with suitable icon/app name/metadata and iPhone safe-area layout, reusing the existing Mini App screen UI. It SHALL NOT use privileged Admin PWA session or scope. A service worker, offline lessons and new push notifications are NOT required for the first version.

#### Scenario: Add to Home Screen
- **WHEN** a learner adds the course from iPhone Safari to their Home Screen and launches it
- **THEN** it opens the independent learner course or login rather than Telegram or Admin PWA
- **AND** bottom navigation and fixed controls remain usable within iPhone safe areas

### Requirement: Browser and Home Screen session correctness
The system SHALL ensure that normal Safari and installed Home Screen contexts individually verify session authority and safely handle OAuth return, cold launch, background/foreground, logout and session expiration. It SHALL clear account-specific state on identity change and use a fresh authenticated server read where appropriate.

#### Scenario: Return with expired credentials
- **WHEN** the learner reopens an installed PWA after session expiry
- **THEN** private account/course data is not displayed under stale authority
- **AND** the user is directed through the secure sign-in flow

#### Scenario: Change user
- **WHEN** a user logs out and another verified user logs in
- **THEN** cached or retained UI state from the previous user cannot reveal their progress, payment or protected material

### Requirement: Safe minimal web assets
The system SHALL version and serve only necessary learner shell assets. It SHALL NOT publicly cache private course/graded responses, auth tokens, payment records or account data. A service worker MAY be introduced later only for a demonstrated requirement and with a separate secure cache review; it is not a condition of iPhone Home Screen installation.

#### Scenario: Network unavailable
- **WHEN** network access is unavailable during a protected lesson or payment action
- **THEN** the app shows an accurate network/offline error and does not simulate server grading or payment confirmation

### Requirement: Real iPhone capabilities
The delivered PWA SHALL be verified on a real iPhone in both Safari and installed contexts for lesson navigation, audio playback, mic permission/denial, keyboard, provider sign-in and browser payment return. Unsupported iOS APIs SHALL degrade safely without corrupting learning state; new Web Push is outside initial scope.

#### Scenario: Microphone unavailable
- **WHEN** voice permission is denied or a required browser capability is not supported
- **THEN** an understandable localized error/fallback is shown and non-voice course actions remain available

#### Scenario: Planning-only validation
- **WHEN** GitHub Actions OpenSpec validation passes without running on a real iPhone
- **THEN** the product is still not considered device-accepted or production-ready
