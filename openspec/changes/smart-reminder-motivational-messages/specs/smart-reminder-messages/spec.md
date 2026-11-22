# Spec Delta

## Purpose

Makes each Smart study reminder fit the learner's current situation with varied, non-repeating UZ/RU/TJ copy, and keeps inviting a learner back every day of a break, the same way on every channel.

## ADDED Requirements

### Requirement: Situation-aware reminder message
Each Smart study reminder SHALL be classified from verified server data at render time as `daily`, `streak`, `comeback` or `long_break`, and SHALL use copy from that situation's pool. No situation may assert a fact the server has not verified, and no copy names a number of missed days.

#### Scenario: Live streak not yet extended today
- **WHEN** the account's current streak is 2 or more and its last verified study was on the previous local day
- **THEN** the reminder uses the `streak` pool and its `{streak}` value equals the streak shown in the app

#### Scenario: Short break
- **WHEN** the last verified study was 2 to 7 local days ago
- **THEN** the reminder uses the `comeback` pool

#### Scenario: Long break
- **WHEN** the last verified study was 8 or more local days ago
- **THEN** the reminder uses the `long_break` pool

#### Scenario: Recent learner without a streak
- **WHEN** none of the above applies, including an account with no verified study yet
- **THEN** the reminder uses the `daily` pool pointing to the server-selected next lesson

### Requirement: Non-repeating variant rotation
The variant SHALL be chosen without randomness from the situation's pool: a variant this account has never received first, then the least recently received; variants received in the last 14 local days are skipped while another remains. Once chosen, the variant is fixed for that reminder.

#### Scenario: Consecutive reminders
- **WHEN** an account receives reminders from the same pool on consecutive days
- **THEN** no variant repeats until every variant of that pool has been used

#### Scenario: Retry or feed after language change
- **WHEN** the same reminder is retried, claimed again or shown in the in-app feed after the learner switches UZ/RU/TJ
- **THEN** the same variant key is used and rendered in the requested language

### Requirement: Canonical localized copy with safe placeholders
Every variant SHALL exist in UZ, RU and TJ with the same placeholders, using only `{lesson}` and, in the `streak` pool only, `{streak}`, and SHALL fit the Telegram, Web Push and Android limits. Copy MUST be grammatical for any streak number without plural rules.

#### Scenario: Catalog check
- **WHEN** the localization build and its tests run
- **THEN** they fail if any variant is missing in a language, uses another placeholder, differs in placeholders between languages or exceeds a channel limit

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

### Requirement: Daily reminders throughout a break
After the account's personal study gap, ordinary Smart reminders SHALL continue on every eligible local day without verified study, with no automatic stop. OFF, pause, quiet hours, one per local day, a blocked bot or a lost push channel SHALL keep precedence.

#### Scenario: Learner away for a month
- **WHEN** a learner who studied daily stops after local day D and does not return for 30 days
- **THEN** one reminder goes out on each of D+1 to D+30 at the personal time, moving from `daily` or `streak` to `comeback` and then `long_break`

#### Scenario: Learner returns
- **WHEN** a verified study is recorded during a break
- **THEN** no reminder is sent for that local day and later reminders follow the normal rhythm and situation rules

#### Scenario: Learner turns reminders off
- **WHEN** the learner turns Smart study reminders OFF or blocks the bot
- **THEN** no further Smart study reminder is sent on that channel or account as today

### Requirement: Measurable variants without exposing learners
Each sent Smart reminder SHALL record its situation and variant key with the job. The Admin readout SHALL show only anonymous monthly counts per situation of sent reminders and verified returns within 24 hours.

#### Scenario: Owner reviews results
- **WHEN** the owner opens the Smart study readout
- **THEN** each situation shows sent and 24-hour return counts without account identifiers, message bodies or per-learner detail
