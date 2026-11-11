# PWA engagement

## Purpose
Deliver existing advertising and feedback services through the authenticated learner PWA.

## ADDED Requirements

### Requirement: Existing advertising policy
PWA SHALL reuse the two Mini App placements and their server-owned audience, language and canonical daily caps; ads SHALL NOT interrupt required foundation or block study on failure.

#### Scenario: PWA impression
- **WHEN** an eligible learner sees an enabled ad in PWA
- **THEN** its view counts toward the same account cap in Mini App and Android.

### Requirement: Brief contextual feedback
PWA SHALL reuse its existing centered feedback dialog and canonical BotFeedback persistence on relevant lesson, practice and Voice exits. Feedback SHALL be optional, short and limited by existing server eligibility plus per-session dismissal suppression.

#### Scenario: Contextual exit
- **WHEN** a learner leaves an eligible lesson, practice or Voice activity
- **THEN** a brief context-specific question appears only on a calm foreground screen and submits once through the existing feedback service and Admin inbox.

#### Scenario: Dismissed or unavailable
- **WHEN** the learner dismisses feedback or its request fails
- **THEN** navigation continues and no positive answer or reward is fabricated.
