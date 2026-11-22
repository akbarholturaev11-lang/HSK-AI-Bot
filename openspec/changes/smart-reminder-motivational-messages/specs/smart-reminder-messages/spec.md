# Spec Delta

## Purpose

Makes each Smart study reminder fit the learner's current situation with varied, non-repeating UZ/RU/TJ copy, and stops reminding a learner who does not respond, the same way on every channel.

## ADDED Requirements

### Requirement: Situation-aware reminder message
Each Smart study reminder SHALL be classified from verified server data at render time as `daily`, `streak`, `comeback` or `last_call`, and SHALL use copy from that situation's pool. No situation may assert a fact the server has not verified.

#### Scenario: Live streak not yet extended today
- **WHEN** the account's current streak is 2 or more and its last verified study was on the previous local day
- **THEN** the reminder uses the `streak` pool and its `{streak}` value equals the streak shown in the app

#### Scenario: Break of two or more days
- **WHEN** the last verified study is two or more local days ago
- **THEN** the reminder uses the `comeback` pool and states no specific number of missed days

#### Scenario: Recent learner without a streak
- **WHEN** neither `streak`, `comeback` nor `last_call` applies
- **THEN** the reminder uses the `daily` pool pointing to the server-selected next lesson

### Requirement: Non-repeating variant rotation
The variant SHALL be chosen without randomness from the situation's pool: a variant this account has never received first, then the least recently received; variants received in the last 14 local days are skipped while another remains. Once chosen, the variant is fixed for that reminder.

#### Scenario: Consecutive reminders
- **WHEN** an account receives reminders from the same pool on consecutive days
- **THEN** no variant repeats until every variant of that pool has been used or is older than 14 days

#### Scenario: Retry or feed after language change
- **WHEN** the same reminder is retried, claimed again or shown in the in-app feed after the learner switches UZ/RU/TJ
- **THEN** the same variant key is used and rendered in the requested language

### Requirement: Canonical localized copy with safe placeholders
Every variant SHALL exist in UZ, RU and TJ with the same placeholders, using only `{lesson}` and `{streak}`, and SHALL fit the Telegram, Web Push and Android limits. Copy MUST be grammatical for any streak number without plural rules.

#### Scenario: Catalog check
- **WHEN** the localization build runs
- **THEN** it fails if any variant is missing in a language, uses another placeholder, differs in placeholders between languages or exceeds a channel limit

### Requirement: Admin custom text keeps precedence
When the Admin Smart template has custom text for a language, that text SHALL be used for every situation in that language with today's `{lesson}` rule; an empty field SHALL mean the rotating library. Disabling the template SHALL still stop all Smart reminders.

#### Scenario: Owner sets custom text
- **WHEN** the owner saves custom RU text and leaves UZ/TJ empty
- **THEN** RU learners receive that text every time and UZ/TJ learners receive rotating variants

### Requirement: Same message on every channel
Telegram, iPhone PWA and Android SHALL show the server-selected situation and variant for the job. Android clients that cannot display it MUST keep their current local text without failing the reminder.

#### Scenario: Compatible Android build
- **WHEN** a compatible APK claims a Smart job
- **THEN** it posts the server-rendered title and body with the situation's panda icon and keeps the existing open-proof link

#### Scenario: Older Android build
- **WHEN** an APK without message support receives a claim with the new field
- **THEN** it ignores the field and posts its existing local reminder text exactly as before

### Requirement: Unanswered reminder sequence and pause
After the account's personal study gap, unanswered Smart reminders SHALL go out on consecutive eligible days for the first three, then every second day; the fifth uses `last_call` and nothing more is sent until a verified study. A reminder is unanswered once the provider accepted it, or its outcome is unknown, and no verified study followed. OFF, pause, quiet hours, one per local day and the weekly ceiling keep precedence.

#### Scenario: Daily learner stops studying
- **WHEN** a learner who studies daily stops after local day D and never responds
- **THEN** reminders go out on D+1, D+2, D+3, D+5 and D+7 at the personal time, the D+7 one uses `last_call`, and nothing is sent after it

#### Scenario: Learner returns
- **WHEN** a verified study is recorded during the sequence or weeks after `last_call`
- **THEN** the unanswered count resets to zero and reminders follow the normal rhythm with no catch-up messages

#### Scenario: Unknown delivery
- **WHEN** a provider attempt ends with an unknown outcome
- **THEN** it counts as sent for the sequence but never authorizes a second channel or a replay

#### Scenario: Weekly ceiling reached
- **WHEN** the sequence would send on a day that exceeds the approved weekly ceiling
- **THEN** that reminder waits for the next allowed day and the sequence position does not advance

### Requirement: Measurable variants without exposing learners
Each sent Smart reminder SHALL record its situation and variant key with the job. The Admin readout SHALL show only anonymous monthly counts per situation of sent reminders and verified returns within 24 hours.

#### Scenario: Owner reviews results
- **WHEN** the owner opens the Smart study readout
- **THEN** each situation shows sent and 24-hour return counts without account identifiers, message bodies or per-learner detail
