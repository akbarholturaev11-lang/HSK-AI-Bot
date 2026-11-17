# Spec Delta

## Purpose

Shows a learner up to three personal review questions, built from their own server-verified mistakes, between the cards of an ordinary PWA or Android lesson, and schedules each weak skill with the existing spaced-review intervals without changing official lesson results.

## ADDED Requirements

### Requirement: Only server-verified mistakes create adaptive review
The system SHALL consider a mistake for adaptive review only when the server graded the answer against its own canonical key (`lesson`, `test`, `training`, `challenge` or `adaptive` sources). Client-graded drills (`recognition`, `memorize`), LLM judgements (`voice`), ASR scores (`pronunciation`) and self-assessment SHALL NOT create or advance adaptive review.

#### Scenario: Client-graded drill is ignored
- **WHEN** a learner's only evidence for a target comes from the `memorize` or `recognition` source
- **THEN** no adaptive question is planned for that target

#### Scenario: Forged lesson mistake grants nothing
- **WHEN** a client reports a lesson selection that is the correct option
- **THEN** the canonical re-grade discards it and no adaptive review is created

### Requirement: Skills are tracked separately
Each weak target SHALL be tracked per skill (meaning, hanzi, pinyin/tone, listening, grammar), derived from the format of the verified mistake. One random mistake in one skill SHALL NOT mark the other skills of the same word as weak.

#### Scenario: Pinyin mistake schedules pinyin only
- **WHEN** the learner chose a wrong `pinyin_choice` option for 收到
- **THEN** the adaptive question for 收到 checks pinyin or listening, not the meaning

### Requirement: At most three adaptive questions inside an ordinary lesson
When an ordinary lesson opens and the feature is enabled for the learner, the server SHALL return a plan with zero to three questions from previously learned verified weak material of the same HSK track. The client SHALL place them between ordinary cards, not before the second card, not in exit-ticket, checkpoint exit-check or repair-bank sections, and not in tests, challenges or locked previews. The lesson JSON, `material_ref`, base queue order and resume cursor SHALL NOT change.

#### Scenario: Questions interleaved
- **WHEN** a learner with two due weak skills opens the next ordinary lesson
- **THEN** two personal questions appear between ordinary cards, each labelled as personal review

#### Scenario: Nothing due
- **WHEN** the learner has no verified weak material due
- **THEN** the lesson runs exactly like the base lesson

#### Scenario: HSK track isolation
- **WHEN** the learner opens an HSK 3.0 lesson
- **THEN** only HSK 3.0 weak targets are used, and HSK 2.0 targets are not

### Requirement: Stable, versioned plan per lesson attempt
The server SHALL persist the plan with its answer keys, contract version and the learner, level, lesson and local day it belongs to. Repeated requests for the same learner, lesson, day, language and client format set SHALL return the same questions and their answered state. The client SHALL never receive an answer key before answering.

#### Scenario: Retry returns the same plan
- **WHEN** the client requests the plan twice for the same lesson on the same day
- **THEN** both responses contain the same item IDs, questions and option order

#### Scenario: Resume after interruption
- **WHEN** the app closes after one of two adaptive questions was answered
- **THEN** on reopening, the answered question is not shown again and the other appears at the next eligible boundary

### Requirement: Separate server grading with no official side effects
An adaptive answer SHALL be graded only against the stored snapshot. It SHALL NOT change the lesson score, graded count, XP, rewards, hearts, streak, unlock, course progress, `CourseAttempt`, completion, lesson analytics or limits. For identical base answers, official lesson results SHALL be identical with the feature ON or OFF.

#### Scenario: Wrong adaptive answer
- **WHEN** the learner answers an adaptive question wrongly
- **THEN** the feedback shows the correct answer, hearts and lesson score stay unchanged, and the lesson continues

#### Scenario: ON/OFF equivalence
- **WHEN** the same base answers are given once with the feature ON and once OFF
- **THEN** completion payload, XP, progress and lesson counters are identical

### Requirement: Answer submission is authenticated and idempotent
The server SHALL accept an adaptive answer only for a plan owned by the authenticated learner, of the learner's current HSK track, not older than the previous local day, for an item in that plan, with a well-formed answer. The first answer is final; repeats SHALL return the stored feedback without a second state change.

#### Scenario: Another account's plan
- **WHEN** a request names a plan ID owned by a different learner
- **THEN** it is rejected and no state changes

#### Scenario: Duplicate submission
- **WHEN** the same answer is sent twice after a network retry
- **THEN** the second response is marked duplicate and the review state changed once

#### Scenario: Forged question ID or answer
- **WHEN** a request names an item not in the plan, or an out-of-range option
- **THEN** it is rejected without a state change

### Requirement: Spaced review with independent correct answers
Adaptive review SHALL use the existing 1 → 3 → 7 → 21 day box rule. A correct answer SHALL count as independent only when the skill was due and no correct answer was counted for that skill on the same local day. A skill SHALL leave active review after three independent correct days, or four when it has two or more verified wrong answers. A new verified mistake in that skill SHALL restart its cycle. Retired skills SHALL stay in long-term review.

#### Scenario: Same-day repeats
- **WHEN** a learner answers the same skill correctly in two lessons on one day
- **THEN** only one independent correct answer is counted

#### Scenario: Repeated difficult mistake
- **WHEN** a skill had two verified wrong answers
- **THEN** four independent correct days are required to retire it

#### Scenario: New mistake restarts
- **WHEN** a skill with two counted correct days receives a new verified mistake
- **THEN** its counted days reset and it is due again

### Requirement: Xatolarim final check
When the learner clears a target through the existing Xatolarim review, the system SHALL show one final adaptive check for it in an ordinary lesson no earlier than three days later. A correct answer SHALL retire the target's skills from active review; a wrong answer SHALL reopen the target and restart the skill's cycle. Xatolarim XP, clearing and progress rules SHALL stay unchanged.

#### Scenario: Final check after three days
- **WHEN** a target was cleared in Xatolarim four days ago
- **THEN** the next ordinary lesson may include one final check for it

#### Scenario: Final check failed
- **WHEN** the learner answers that final check wrongly
- **THEN** the target is active in Xatolarim again and its skill cycle restarts

### Requirement: Never a gate, with instant rollback
Adaptive failure, timeout, disabled flag, unsupported format or missing renderer SHALL NOT block or delay the base lesson. Turning `COURSE_ADAPTIVE_ENABLED` off SHALL return the original non-adaptive lesson on PWA and Android without a client release or reverse migration.

#### Scenario: Plan request fails
- **WHEN** the plan request times out or errors
- **THEN** the lesson continues with only base cards

#### Scenario: Flag off
- **WHEN** the flag is turned off
- **THEN** the plan endpoint returns `enabled: false` and no adaptive card appears
