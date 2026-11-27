# Spec Delta

## Purpose

Keeps an ordinary PWA or Android lesson part within the length the learner chose in onboarding, keeping the practice that fits their goals, and adds a stacked picture pronunciation deck of already-learned words that is graded by the existing pronunciation check.

## ADDED Requirements

### Requirement: Server-planned lesson composition
When the rollout flag admits the learner, the lesson payload SHALL carry `lesson_plan` with the cards to omit and the picture review words. The lesson JSON, card order and `material_ref` of every kept card SHALL stay unchanged. With the flag off or the plan absent, both clients SHALL run the original lesson.

#### Scenario: Flag off
- **WHEN** `COURSE_LESSON_PLAN_ENABLED` is false
- **THEN** the lesson payload has no `lesson_plan` and both clients show the original lesson

#### Scenario: Kept card keeps its reference
- **WHEN** card 2 of section 3 is omitted and the learner answers card 3 of section 3 wrongly
- **THEN** the reported mistake uses `…:section:3:card:3`

### Requirement: Length follows onboarding minutes and goal
The plan SHALL fit the lesson into a unit budget derived from `daily_minutes` and shifted by the learner's goals, counting a picture card as half a card. Only `practice` and `retention_review` cards without learning objectives MAY be omitted; teaching, grammar, dialog, N1 learning sections and the exit ticket SHALL always remain.

#### Scenario: Short daily time
- **WHEN** a learner who chose 5 minutes opens an 18-card part
- **THEN** optional practice cards are omitted until the part fits 14 units (plus the goal shift), and every teaching card remains

#### Scenario: Goal decides what stays
- **WHEN** a `daily_communication` learner and an `hsk_exam` learner with the same minutes open the same part
- **THEN** the first keeps speaking/listening practice and more picture cards, the second keeps listening/vocabulary/grammar practice and fewer or no picture cards

### Requirement: Picture deck uses only learned words with exact pictures
The deck SHALL contain 1–10 unique words, first from earlier parts of the current lesson, then from earlier parts of the same level, never from the current part or later parts, and only words with a curated exact picture for that level. No deck SHALL appear when no word qualifies.

#### Scenario: Part 5 of a lesson
- **WHEN** the learner opens part 5 of lesson 1
- **THEN** pictured words of parts 1–4 are used first and earlier lessons fill the rest

#### Scenario: First part
- **WHEN** the learner opens the first part of a level
- **THEN** no picture deck is shown

### Requirement: Stacked, graded picture cards
Each card SHALL show only the picture and a microphone before checking; hanzi always, pinyin per the pinyin setting and translation SHALL appear only after the server verdict, on the back after a 160° flip. A pass (score ≥ 60) SHALL bounce, turn green and leave the stack; a fail SHALL bounce, turn amber, reveal the answer and return to the end of the queue to be asked again. Skip SHALL pass only the current card and SHALL NOT count it as correct.

#### Scenario: Wrong answer returns
- **WHEN** the learner says the wrong word for 🍎
- **THEN** the card turns amber, shows 苹果, and is asked again after the other cards

#### Scenario: Unclear audio
- **WHEN** the recognizer returns an empty transcript or the request fails
- **THEN** no right/wrong verdict is shown, nothing is revealed and the learner can retry or skip

#### Scenario: Quota reached
- **WHEN** a free learner reaches the daily pronunciation quota in the deck
- **THEN** the existing limit UI appears and the lesson continues after the deck

### Requirement: Existing lesson systems unaffected
The deck SHALL NOT change lesson accuracy, hearts, mistakes payload, XP, streak, daily plan, UIUX-007 adaptive review, entitlements or completion. Copy SHALL exist in UZ, RU and TJ.

#### Scenario: Completion
- **WHEN** a learner finishes a part that contained a picture deck
- **THEN** the completion request is identical in shape to a part without it
