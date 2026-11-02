# iPhone PWA installation and lifecycle

## ADDED Requirements

### Requirement: Installable independent learner application
The system SHALL provide a dedicated HTTPS learner PWA entry, valid web manifest, install icons, standalone display metadata, correct scope/start URL and responsive iPhone safe-area behavior. It SHALL not reuse privileged Admin PWA scope, cookies or service worker authority.

#### Scenario: Safari install to Home Screen
- **WHEN** a user adds the course site to their iPhone Home Screen
- **THEN** the icon and standalone launch target open the learner course/sign-in shell rather than the bot, marketing site or Admin PWA

#### Scenario: Standalone layout
- **WHEN** the PWA runs on supported notched and non-notched iPhones
- **THEN** navigation, keyboard, scroll and fixed bottom controls remain usable within safe areas in portrait mode

### Requirement: Private and versioned caching
The system SHALL define a narrowly scoped service worker and asset-cache update strategy. Public, versioned, non-sensitive UI/assets MAY be cached as permitted; private/protected course responses, exam answers, auth/session, billing data and per-user payloads SHALL NOT be served cross-account or from an unrestricted public cache. Offline use SHALL be limited to explicitly tested supported features.

#### Scenario: Offline entry
- **WHEN** the Home Screen PWA is reopened without network access
- **THEN** only demonstrably safe cached UI/content is available, or a clear offline state appears
- **AND** the app does not claim full offline lessons, sync or grading that it cannot perform

#### Scenario: Login, logout and update
- **WHEN** a learner changes account or a new PWA version activates
- **THEN** stale private state is not exposed, cache versions do not trap the learner on a broken shell and a safe update/recovery path exists

### Requirement: iOS capabilities and graceful degradation
The implementation SHALL explicitly test iOS Safari versus installed PWA restrictions for mic capture, audio playback, speech/voice, upload, external OAuth/payment redirects and optional Web Push. An unavailable OS capability SHALL have a supported fallback or a truthful localized disabled state; no untested push guarantee is allowed.

#### Scenario: Microphone denied
- **WHEN** iOS denies microphone permission or voice capture is unsupported in the current context
- **THEN** the app reports that limit and preserves available non-voice learning paths without corrupting lesson state

#### Scenario: Notification permission unsupported or refused
- **WHEN** web push is unavailable, not installed, or permission is denied
- **THEN** the system does not claim push was registered and does not substitute Telegram transport without a real linked Telegram account and consent

### Requirement: Measurable device acceptance
Release acceptance SHALL use real-device iPhone Safari and installed-PWA checks, including initial install, cold launch, page reload, background/foreground, standalone login callback, session expiry, offline, voice permission and payment return, in addition to automated checks.

#### Scenario: CI-only validation
- **WHEN** OpenSpec validation or desktop-browser E2E succeeds but real iPhone verification has not been run
- **THEN** the PWA is still marked not device-accepted and not production-ready
