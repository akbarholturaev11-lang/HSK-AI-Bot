# Spec Delta

## Purpose

Defines who Smart study reminders reach by default, which learner signals count as consent or OFF on each surface, and how accounts without a Telegram link are admitted (D34).

## ADDED Requirements

### Requirement: Smart study consent is on by default
Every account SHALL count as consenting to Smart study reminders unless an explicit OFF applies. An explicit OFF is: the account Smart master switch OFF; an explicit Smart OFF for that channel or phone; or the Mini App/PWA study reminder switch turned off. An old Telegram lesson-reminder setting, including a past OFF, MUST NOT count as an OFF. No new consent screen, button or text is added.

#### Scenario: Learner who never turned on the old lesson reminder
- **WHEN** an account has no explicit Smart choice, the old lesson reminder is off, and the Mini App/PWA switch is on
- **THEN** Smart study consent is ON for the account

#### Scenario: Mini App or PWA switch is off
- **WHEN** the learner turned off the Mini App/PWA study reminder switch
- **THEN** no Smart study reminder is sent on Telegram or iPhone PWA, and on a phone without its own explicit Smart choice; turning the switch back on restores the default

#### Scenario: Explicit Smart OFF
- **WHEN** the account master switch is OFF or the learner explicitly turned Smart OFF on a channel or phone
- **THEN** that OFF keeps stopping the reminder exactly as before this change

### Requirement: The phone's own permission decides on Android and iPhone PWA
On Android, a phone without an explicit Smart choice SHALL count as ON only after the app reports that the system allows the app's notifications; while permission is unknown or denied it MUST NOT count as ON, so the existing end-of-onboarding notification screen still asks through the system prompt. On iPhone PWA, a live push subscription created by the existing push switch SHALL be the consent signal for Web Push, unless an explicit OFF applies.

#### Scenario: Android permission allowed
- **WHEN** an Android 1.7.29+ phone with no explicit Smart choice reports notifications allowed
- **THEN** the phone counts as ON and the app shows its reminder switch as on

#### Scenario: Android permission not granted
- **WHEN** the phone reports notifications denied or has not reported yet
- **THEN** the phone does not count as ON, nothing is posted, and the existing notification screen can still ask the system prompt

#### Scenario: iPhone PWA push switch turned off
- **WHEN** the learner turns off the PWA push switch, so the subscription is revoked
- **THEN** no Smart Web Push is sent to that PWA

### Requirement: Admission for every sign-in method
Automatic admission SHALL consider accounts of every sign-in method (Telegram, Google, Apple) and route each to one reachable owner: native Android, Telegram, or iPhone PWA Web Push. Accounts without Telegram SHALL be admitted through Web Push or the native Android path. The existing hold, 24-hour drain, review, old-APK fence and one-owner rule MUST stay.

#### Scenario: iPhone PWA account without Telegram
- **WHEN** a Google/Apple PWA account active in the last 30 days has a live push subscription and no explicit OFF
- **THEN** after hold and drain it is reviewed for Web Push, its zone comes from the device offset the PWA already reports, and it receives at most one Smart reminder per local day

#### Scenario: Android account without Telegram
- **WHEN** a Google/Apple Android account on a 1.7.29+ app has no explicit OFF
- **THEN** it is held, the app reports its permission, and after the drain it is reviewed for the native path only if permission is allowed

#### Scenario: Active old APK
- **WHEN** any active phone of the account runs an app older than 1.7.29
- **THEN** the account stays on the legacy senders

### Requirement: Default ON reaches recently active accounts
The default ON SHALL admit an account only when it was active in the last 30 days, measured by the account's last learner activity or a sign-in refresh on an Android or PWA device. An account that already had an explicit Smart ON, master ON or the old lesson reminder ON keeps today's admission. An already admitted account keeps its review and its daily reminders (D32).

#### Scenario: Dormant account
- **WHEN** an account without any earlier ON was last active 31 days ago
- **THEN** it is not admitted; when the learner is active again it becomes a candidate

#### Scenario: Old lesson reminder user
- **WHEN** an account has the old Telegram lesson reminder ON but was last active 60 days ago
- **THEN** it is admitted as before this change

### Requirement: A default send time while no personal time is known
When the account has no manual Smart time, no learned study habit and no saved legacy reminder time, Smart SHALL use 21:00 in the learner's local zone (D35). A manual time, a learned habit and a saved time MUST keep winning in that order, and the learned habit MUST replace the default as soon as it is found. Quiet hours, pause, daily goal, one-per-day and weekly limits still apply. The installed Android widget contract MUST NOT change.

#### Scenario: New learner without a habit
- **WHEN** an admitted learner has studied on fewer than three days, or at scattered times, and never saved a reminder time
- **THEN** the Smart reminder is planned for 21:00 local time on a day the learner has not studied yet

#### Scenario: Habit found later
- **WHEN** the same learner later studies on three days within one hour of 19:30
- **THEN** reminders move to about 19:30 and 21:00 is no longer used

