# Native activity feedback

## Purpose

Let verified Android learners answer the same bot questions as the latest PWA after actual learning activity, preserving feedback ownership and reward safety.

## ADDED Requirements

### Requirement: Canonical sequential questions
Android SHALL use server-localized bot choices and show one distinct question at a time. Free learners SHALL answer liked/disliked questions; paid learners SHALL answer value/reason questions. Required detail and original answer codes SHALL be preserved.

#### Scenario: Paid and free answers
- **WHEN** the server offers a due feedback prompt for a verified learning context
- **THEN** Android renders the appropriate full question flow, and stores the same canonical bot codes in the existing feedback row.

### Requirement: Shared eligibility and reward safety
PWA and Android SHALL share account locking, actual-context checks, cooldown, pending-answer compatibility, validation and reward rules. A client SHALL grant no access or reward.

#### Scenario: Missing context or another owner
- **WHEN** there is no proven activity or the feedback belongs to another account
- **THEN** the server refuses the request without creating a completed answer or reward.

#### Scenario: Subscription changes or duplicate submit
- **WHEN** a saved partial answer is incompatible with the current paid/free state, or an answer is submitted twice
- **THEN** the pending answer is preserved, a second reward is refused, and paid subscription dates remain intact.
