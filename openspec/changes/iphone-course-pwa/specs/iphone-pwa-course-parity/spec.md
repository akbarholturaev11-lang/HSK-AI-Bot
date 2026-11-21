# iPhone PWA learner course parity

## ADDED Requirements

### Requirement: Shared learner interface and functional parity
The standalone iPhone PWA SHALL reuse the existing learner Course Mini App UI and functionality as closely as iOS permits. Telegram-specific SDK behaviors SHALL be encapsulated behind a platform adapter rather than deleted. Existing Telegram Mini App screen/lesson/quiz/homework rendering and controls SHALL continue to work.

#### Scenario: Comparable authenticated course views
- **WHEN** an authenticated learner opens the same track, level and lesson in Telegram and in the PWA
- **THEN** the PWA renders the same supported core content, navigation hierarchy, visual tokens, locale and progress actions
- **AND** documented OS-specific differences do not silently remove a working course function

#### Scenario: Telegram client preserved
- **WHEN** the existing Telegram Mini App is launched with valid signed initData
- **THEN** its SDK-specific back/close/deep-link and initialization integration continue to function as before

### Requirement: Distinct transport, shared business authority
The system SHALL inventory every Mini App frontend route required by the learner journey and provide a securely authenticated browser transport or audited common actor adapter for each needed path. Business decisions SHALL stay in existing server-owned services rather than duplicated JS, and Telegram-authenticated legacy endpoints SHALL remain protected.

#### Scenario: Browser-only account opens course
- **WHEN** an authenticated browser-only account with no Telegram ID opens supported course screens
- **THEN** server-backed learner data and mutations resolve the canonical `users.id`
- **AND** no request requires a fake `X-Telegram-Init-Data` header

#### Scenario: Unauthenticated or conflicting account request
- **WHEN** a PWA user requests another account's progress, purchase, exercise attempt or lesson result
- **THEN** the API denies the request with no disclosure or mutation

### Requirement: Learning and assessment correctness
The PWA SHALL preserve authorized HSK 2.0/3.0 course-track selection, lesson content/sequence, vocabulary/grammar, practices, tests, homework, progress persistence, XP, mistakes, AI limits and completion proofs under existing server-side grading and access guards. No client bundle, public cache or PWA-specific endpoint SHALL expose protected answer keys or bypass Pro restrictions.

#### Scenario: Continuity across clients
- **WHEN** a learner completes an allowed lesson in PWA and later opens Telegram, Android or Desktop with the linked canonical account
- **THEN** the verified result, current track/level and progress are consistent with the same server record
- **AND** the action has not generated duplicate XP or completion credit

#### Scenario: Forged completion or inaccessible lesson
- **WHEN** a PWA request contains a forged grade, replayed completion proof or an unauthorized paid lesson
- **THEN** the same canonical server rules reject it as for other clients

### Requirement: Navigation, state and localization continuity
The PWA SHALL restore applicable course routes, selected track/level, scroll/navigation and in-progress states only when bound to the correct signed-in account. Fixed new UI strings SHALL come from canonical UZ/RU/TJ catalogs and not a new handwritten per-client dictionary.

#### Scenario: App resumes after termination
- **WHEN** the learner returns to the installed PWA after backgrounding or termination
- **THEN** a valid session returns to the correct supported route with appropriate state
- **AND** an expired session requests reauthentication without exposing previous-account content

#### Scenario: Change account or language
- **WHEN** the learner logs out, signs in as a different user or changes locale
- **THEN** prior user-specific client state is cleared or appropriately namespaced and current UI matches the user's selected supported language
