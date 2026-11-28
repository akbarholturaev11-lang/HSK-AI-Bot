# Spec Delta

## Purpose
Compose a coherent teach, apply and evidence cycle within existing lessons while preserving required objectives and each client's established continuation behavior.

## ADDED Requirements

### Requirement: Coherent bounded learning cycle
Treatment SHALL connect teaching, application, verified evidence and at most one relevant existing next action. Optional contextual/review work MUST fit the session budget; not every part is required to receive a contextual item when eligible material or budget is absent.

#### Scenario: Short session lacks optional capacity
- **WHEN** protected teaching consumes the available planned budget
- **THEN** the lesson retains teaching and required retention/exit objectives rather than append unlimited tasks
- **AND** it uses the base safe path without pretending the selected daily minutes guarantee actual duration

### Requirement: Protect curriculum and retention objectives
Composition MUST preserve required vocabulary, grammar, source teaching, foundations, retention objectives, official pass/homework rules and lesson order. Canonical material references and existing completion/XP deduplication SHALL remain unchanged.

#### Scenario: Candidate conflicts with required content
- **WHEN** a new task would displace a protected objective or use an unadmitted source
- **THEN** it is omitted or replaced with an eligible bounded task
- **AND** the original required content and access decision remain available

### Requirement: Personalization uses verified context and shown history
Optional selection SHALL use saved goals/time, verified weakness and recent shown-format history. Where multiple safe formats fit, short-session trimming MUST avoid always retaining the same first-ranked format. Missing history SHALL use a bounded cold-start mix without invented mastery.

#### Scenario: Repeated short sessions
- **WHEN** several eligible formats address the same objective within budget
- **THEN** selection rotates them under the frozen policy while necessary objective repetition remains permitted
- **AND** planned, hidden or failed-to-load items do not count as shown; one-format eligibility records a safe limitation

### Requirement: Existing resume and shared performance delivery
The change SHALL preserve original local resume and use shared performance entry/readiness/Back/cleanup owners without synchronized cross-device course attempts. Owned receipts MUST remain retry-safe; optional plan/media failure MUST NOT block first usable teaching or mix accounts. Per-turn loaders and competing history handlers MUST NOT be introduced.
#### Scenario: Reload or device switch
- **WHEN** an account resumes on the same or another client
- **THEN** its arm remains stable while each client's existing course position behavior remains intact
- **AND** accepted supplemental results replay idempotently or safely expire to base continuation without skipped teaching, duplicate rewards or a promise of synchronized cursors

#### Scenario: Fast entry or a scene turn advances
- **WHEN** PWA preparation finishes within its 300 ms delay or a learner advances an already open scene
- **THEN** no new panda/loading interruption is introduced; slow starts reuse the shared 300 ms minimum after showing
- **AND** Telegram retains its own timing; continuation frames keep verified actor/first-paint/error/retry handling

#### Scenario: Back during a mission
- **WHEN** a learner swipes Back during an active PWA scene or mission
- **THEN** the existing flow remains stationary and asks once through its existing exit owner
- **AND** cancel retains the turn/response state, confirmed exit keeps the established resume promise and cleanup stops obsolete audio without duplicate navigation

### Requirement: Control and treatment configuration is explicit
Control SHALL retain the pinned existing composition; treatment requires committed server allocation and supported capabilities. Common measurement changes MUST be identified explicitly, with identical bounded policy in both arms, rather than described as an untouched control.

#### Scenario: Measurement is newly added
- **WHEN** both arms receive a new probe
- **THEN** the comparison is labelled existing-plus-probes versus bundle-plus-probes
- **AND** client-supplied arm fields cannot enable treatment and unrelated reminder/paywall/reward policies remain pinned equally
