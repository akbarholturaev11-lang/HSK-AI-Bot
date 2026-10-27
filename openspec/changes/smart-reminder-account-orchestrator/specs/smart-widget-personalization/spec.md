# Smart Widget Personalization — Spec Delta

## Purpose

Present truthful, personal study context through one reusable account contract, using Android widgets first and later iOS, macOS and Windows adapters without duplicating learning or reminder policy.

## ADDED Requirements

### Requirement: Shared personal widget context
Widgets SHALL consume a versioned platform-neutral account projection of verified learning, personal study rhythm, current goal and accessible continuation. Platform adapters MUST NOT independently learn conflicting habits or use platform-specific layout fields as the shared policy contract.

#### Scenario: Same learner on different widget platforms
- **WHEN** supported Android and later iOS/macOS/Windows adapters consume the same valid account context
- **THEN** they present equivalent goal and personal study-phase meaning, adapted to each OS layout and refresh capability

#### Scenario: Unsupported projection version
- **WHEN** an installed adapter cannot interpret a projection version
- **THEN** it retains a safe compatible or neutral view without inventing personal state, granting access or enabling study sends

### Requirement: Personal rhythm and restrained presentation
Widget presentation SHALL use reliable personal rhythm and deliberate time/quiet/pause choices instead of universal urgency hours. Sparse history MUST receive an honest neutral or genuine existing-time fallback. Adaptation MUST NOT require a separate AI activation or per-refresh generative request.

#### Scenario: Night learner and daytime learner
- **WHEN** reliable study windows differ, including a learner who normally studies at 02:00
- **THEN** widget urgency follows each valid personal context and does not label both overdue solely at a fixed 22:00 boundary

#### Scenario: Cold start or personal pause
- **WHEN** history is insufficient or the account is quiet/paused
- **THEN** the widget uses a restrained fallback and does not fabricate a learned habit, comeback or failure

### Requirement: Truthful goal and course state
Widgets MUST distinguish real plan completion, displayed XP totals and engagement. Completed study SHALL produce a calm completed view. Reward-only XP, a widget tap, an app open or missing activity MUST NOT become completed learning, a broken streak or proof of inactivity.

#### Scenario: Goal completed on another client
- **WHEN** a fresh authenticated projection confirms today's relevant plan is complete
- **THEN** the widget becomes calm/completed rather than continuing time-based escalation

#### Scenario: Reward XP without accepted study
- **WHEN** only reward XP or exposure/open events exist
- **THEN** the widget does not claim the learner completed a lesson or the actual daily plan

### Requirement: Passive rendering and consent separation
Widget install, refresh, timeline, rendering and tap MUST NOT create notification consent, reserve a study intent or send a reminder. Existing study master/channel OFF and OS denial SHALL remain effective; ordinary permitted progress rendering remains independent of notification permission.

#### Scenario: Widget present with study notifications OFF
- **WHEN** a linked learner has a widget but study notifications are OFF or OS-denied
- **THEN** permitted progress can still render without enabling a channel, posting a notification or adding an activation prompt

#### Scenario: Widget tap
- **WHEN** the learner taps a widget action
- **THEN** it requests normal authorized navigation and is recorded only as engagement if collected, never as a completed study or send receipt

### Requirement: Freshness and account isolation
Personal context SHALL be bound to the authenticated account/session, course, authoritative day/zone and validity window. Adapters MUST reject expired, future, wrong-context or replayed old-session updates; logout, relink and deletion MUST remove the previous learner's visible/cache state.

#### Scenario: Offline or changed day and zone
- **WHEN** context expires, refresh fails, or its day/zone/course binding no longer matches
- **THEN** the adapter shows a neutral/stale view with no newly asserted habit, urgency, completion or target authority

#### Scenario: Late response after account switch
- **WHEN** a previous account's delayed response arrives after logout/relink
- **THEN** it cannot restore that account's progress, image state or continuation action

### Requirement: Safe localized continuation
Widget actions MUST preserve normal foundation, course-track and entitlement checks at the destination. Fixed copy SHALL use canonical UZ/RU/TJ resources; snapshots MUST contain only necessary presentation facts, without credentials, raw learning history or private lesson content.

#### Scenario: Course switched or target becomes locked
- **WHEN** a cached action refers to another course or newly inaccessible lesson
- **THEN** navigation revalidates current access and does not bypass foundation, Pro or lesson order

### Requirement: Native adapter capability and parity
Android Direct/Play SHALL share the same semantic contract. Later iOS and paired macOS/Windows adapters MUST verify real host, account bridge, privacy and lifecycle support before being advertised. An installed PWA or desktop app alone MUST NOT be reported as a working OS widget.

#### Scenario: Host unavailable or OS defers refresh
- **WHEN** a platform lacks a supported widget host or defers its refresh budget
- **THEN** support and freshness remain honest; no exact-time widget update or hidden notification fallback is promised

#### Scenario: Widget personalization rollback
- **WHEN** the personalized renderer is disabled or an adapter is rolled back
- **THEN** it returns to a neutral/compatible view while preserving study OFF, consent revisions and job ownership without restoring a second sender
