# Spec Delta

## ADDED Requirements

### Requirement: Platform D1/D7 return
Course under the Android, Telegram and iPhone PWA filters SHALL report `return_retention` D1 and D7. The cohort is each account's first verified use of that platform. A return is that platform's verified use 24–48 hours (D1) or 168–192 hours (D7) later. Client-writable starts and rows tagged before the platform boundary MUST NOT anchor a cohort or count as a return. Overall `return_retention` MUST stay unchanged.

#### Scenario: Second platform
- **WHEN** an account that learns in Telegram first opens the PWA later
- **THEN** it enters the PWA cohort at its first PWA open, not at its registration or its Telegram start

#### Scenario: Return on another platform
- **WHEN** an account's only use in its Telegram D1 window is on the PWA or Android
- **THEN** it is counted as eligible for Telegram but not as returned

#### Scenario: Immature cohort
- **WHEN** an account's first use is less than 48 hours (D1) or 8 days (D7) old
- **THEN** it is not in that window's cohort

#### Scenario: Before the boundary
- **WHEN** a tagged row predates the platform boundary, or the row is a client-writable start
- **THEN** it never anchors a cohort
