# Spec Delta

## Purpose

Provide reusable contextual practice from verified existing Chinese course material while preserving source, locale, grading and access contracts.

## ADDED Requirements

### Requirement: Three reusable initial formats
The treatment SHALL support dialogue pause, bounded scenario response and find-and-repair formats. Translation, missing-turn selection, repetition and character-role response SHALL be modes of those formats, selected only when verified material and client capabilities support them.

#### Scenario: Two-character dialogue pause
- **WHEN** an eligible source dialogue is presented
- **THEN** two identifiable characters take ordered turns, with a challenge at a meaningful configured boundary
- **AND** the challenge asks for translation, a missing turn, repetition or a role response using that dialogue's verified context
- **AND** resuming the scene does not skip or duplicate a required source teaching objective

#### Scenario: Independent scenario response
- **WHEN** a learner receives a bounded real-life situation based on taught vocabulary and grammar
- **THEN** the learner can answer in the character's place before seeing the model answer
- **AND** feedback distinguishes the accepted response, a correctable error and an unassessed open response
- **AND** a fixed recognition answer is not reported as independent production

#### Scenario: Find and repair an error
- **WHEN** a verified repair item is available for a taught objective
- **THEN** the learner identifies the erroneous part and supplies or selects its correction
- **AND** feedback shows the canonical correction with its Chinese meaning
- **AND** an ambiguous or unverified distractor is rejected before delivery

### Requirement: Source-grounded material eligibility
Every delivered item SHALL reference an admitted source lesson, objective and content revision. The system MUST preserve original Chinese, canonical material identities, source SHA guards, answer keys, official grading and private-course access. New supplemental material MUST pass the existing agent-owned semantic and safety QA before delivery.

#### Scenario: Material has not passed QA
- **WHEN** source content is absent, ambiguous, stale, untranslated or fails a source guard
- **THEN** the new item is not delivered
- **AND** the learner receives the existing safe exercise or source lesson path
- **AND** a bounded fallback reason is recorded without copying answers or private content into telemetry

#### Scenario: Supplemental content is necessary
- **WHEN** a lesson lacks a verified scene or repair item
- **THEN** an offline authored supplement can be admitted only after Chinese-context, level, objective and UZ/RU/TJ meaning checks
- **AND** an unchecked live AI output cannot become an official answer key or block lesson completion

#### Scenario: Vocabulary gating removes a dialogue turn
- **WHEN** a source exchange is filtered to previously taught material
- **THEN** a delivered scene uses contiguous source turns or agent-verified contextual continuity
- **AND** unrelated speakers or fragments are not stitched together to satisfy structural eligibility
- **AND** missing source phonetics cannot be invented as purported original pinyin

### Requirement: Shared course and locale coverage
The contract SHALL apply to all currently admitted HSK 2.0 and 3.0 levels and UZ/RU/TJ clients. Every item MUST retain Chinese characters, pinyin and verified localized meaning with reveal timing appropriate to the task. Unsupported or unpublished levels MUST keep their existing access/release state.

#### Scenario: A locale or level lacks eligible material
- **WHEN** a supported course/locale has no safe item for one of the new formats
- **THEN** the learner continues through a safe compatible exercise
- **AND** coverage is reported as fallback rather than fabricated format coverage
- **AND** no other course or future level is unlocked by that fallback

#### Scenario: Language changes during a session
- **WHEN** the learner changes between UZ/RU/TJ
- **THEN** persisted answers retain their original source and grading revision
- **AND** newly delivered display content uses verified local resources without changing the correct answer

### Requirement: Bounded audio and response fallback
Audio playback and optional speech assessment SHALL respect learner settings, platform permissions and existing quotas. Media, microphone, network or provider failure MUST preserve a usable text/choice path. Missing audio or unavailable speech assessment MUST NOT be treated as a wrong answer.

#### Scenario: Audio cannot play
- **WHEN** a two-character scene cannot load or autoplay is blocked
- **THEN** the learner can retry playback or continue with ordered transcript and a comparable text task
- **AND** the result records the delivered mode and fallback reason
- **AND** the learner is not trapped behind repeated permission or playback prompts

#### Scenario: Speech cannot be assessed
- **WHEN** speech permission is declined, speech is unintelligible or the provider times out
- **THEN** the learner can use the existing supported response alternative
- **AND** the attempt is marked unassessed where appropriate rather than scored incorrect
- **AND** no independent-speaking success is claimed from a text-choice substitute

### Requirement: All-platform capability negotiation
Supported PWA, Mini App, Android Direct/Play, paired macOS/Windows and legacy bot entry paths SHALL use the same versioned content identities and capability rules. Clients MUST receive only renderable tasks; an old client SHALL retain its existing course path and canonical result contract.

#### Scenario: An installed client lacks a renderer
- **WHEN** an account uses a client that cannot render a new format
- **THEN** the account keeps its assigned experimental arm and receives the base compatible path
- **AND** delivery is reported as unsupported-client fallback, not treatment exposure
- **AND** progress, subscription and account identity remain shared

#### Scenario: Existing picture cards are available
- **WHEN** verified picture-pronunciation material supports the session objective
- **THEN** the existing picture-card capability is reused
- **AND** the initial release does not require a separate image-generation system
