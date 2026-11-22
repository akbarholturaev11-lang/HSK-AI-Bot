# Proposal

## Why

Smart Reminder is live for every eligible learner (rollout 4/4, owner real-use test passed on 2026-11-22), but it sends one fixed message. Telegram and the iPhone PWA always render the single `smart_study` template ("continue lesson N"). The Android Smart path always posts the `DAILY_GOAL` text, rotating three local strings by date. Accounts moved to Smart also stop receiving the varied legacy evening texts (streak, daily goal, unfinished lesson), because those senders are vetoed for held accounts. In practice a lapsed learner therefore gets the same text up to three times a week indefinitely: D20's backoff and stop never trigger in production, because they count only *verified shown* reminders and no Telegram/PWA/Android path produces that state.

The owner asked (2026-11-22) to raise this to the level of Duolingo's reminder system: varied, situation-aware messages that pull learners back quickly in the first days of a break and then stop. Duolingo's published system ([Yancey & Settles, KDD 2020](https://research.duolingo.com/papers/yancey.kdd20.pdf); [Duolingo blog](https://blog.duolingo.com/hi-its-duo-the-ai-behind-the-meme/); [former CPO on growth](https://www.lennysnewsletter.com/p/how-duolingo-reignited-user-growth)) relies on four ideas: hand-written template pools with eligibility rules (e.g. "3+ day streak"), avoiding recently seen templates (novelty fades, "recovering" penalty with a ~15-day half-life), a streak-saver message, and a back-off that stops reminders after several unanswered ones ("these reminders don't seem to be working"). Its bandit-learned template scores are a later optimisation and need far more traffic than our ~100 Smart accounts.

This needs OpenSpec rather than a direct task: it changes owner decisions D08/D19/D20, the shared Telegram/PWA/Android delivery contract, a database column and UZ/RU/TJ copy. The authoritative sources stay [the Smart Reminder Master Plan](../../../docs/smart-reminders/SMART_REMINDER_MASTER_PLAN.md) (decisions D01–D30 and evidence) and the in-flight [`smart-reminder-account-orchestrator`](../smart-reminder-account-orchestrator/) change (consent, routing, one job per account/day, rollout). This change adds only the message layer and the lapse sequence on top of them.

## What Changes

- **Situation-aware messages.** At render time the server classifies the day's single reminder as `daily`, `streak` (live streak of 2+ days, not studied today), `comeback` (no study for 2+ days) or `last_call` (final message before pausing). Each situation has a pool of canonical UZ/RU/TJ variants using only verified `{lesson}` and `{streak}` values.
- **No repeats.** The variant is chosen deterministically: never-sent or least-recently-sent first, excluding variants this account received in the last 14 days, with a stable per-account/day tie-break. The chosen key is stored on the job, so retries and the in-app feed reuse the same message and later analysis can compare variants.
- **One message source for all channels.** Telegram and PWA render the variant on the server. The existing Android claim response gains an optional rendered `message` (situation, key, title, body); a new APK displays it with the matching panda icon, while older APKs ignore the field and keep today's local text.
- **Lapse sequence (replaces the inert D20 path in ordinary mode).** After the learner's personal gap (existing rhythm logic), unanswered reminders follow a fixed sequence of one per day for the first three, then every other day; the fifth is `last_call`, after which Smart study reminders pause until the next verified study. A reminder counts as unanswered once the provider accepted it and no verified study followed; unknown delivery still never triggers another channel. **BREAKING (policy):** changes D08/D20 semantics and the D19 weekly ceiling (owner decisions D31–D33, approved 2026-11-22).
- **Admin stays minimal.** The existing "Message text" field keeps working: empty means the rotating library, filled means that single text for the language, exactly as now. The existing results section gains an anonymous per-situation count of sends and 24-hour returns. No new control.

## Capabilities

### New Capabilities
- `smart-reminder-messages`: situation classification, variant pools and rotation, cross-channel rendering, and the unanswered-reminder lapse sequence for Smart study reminders.

### Modified Capabilities
- None under `openspec/specs/`. The related "Adaptive time and cadence", "Personal reactivation" and "Safe localized content" requirements live in the unarchived `smart-reminder-account-orchestrator` change; task 1.3 reconciles their wording there once D31–D33 are approved, instead of duplicating them here.

## Impact

- **Backend:** `app/services/smart_reminder_cadence.py` (observed calibration v2 and lapse sequence), a new `app/services/smart_reminder_messages.py` (situation + variant selection and rendering), `smart_reminder_telegram_content.py`, `smart_reminder_pwa.py`, `smart_reminder_android.py` (claim payload), `smart_reminder_policy_context.py` (unanswered count, recent keys), Admin readout in `app/admin_api/pwa_notifications.py`.
- **Database:** additive Alembic revision adding nullable `smart_reminder_jobs.content_key`; downgrade drops only that column.
- **Localization:** new `smart.msg.*` keys in `localization/ui/{uz,ru,tj}/notifications.json` plus generated catalogs; Admin hint copy in UZ/RU/TJ.
- **Android:** `AndroidSmartReminderApi.kt`, `SmartStudyBridge.kt`/`StudyReminderCoordinator.kt`, `StudyNotifications.kt` and tests; needs a new APK, released only on owner instruction (D28).
- **Unchanged:** consent, OFF/pause/quiet hours, one study reminder per account/local day (D03), personal time selection, channel choice, rollout/admission, legacy D1 recovery and rating, payments and entitlements. Desktop stays frozen.
- **Excluded:** bandit/ML template scoring (D09/D26, too little traffic), a second same-day streak-saver, email, learner names in copy, streak freeze/repair, iOS widget.
- **Rollback:** fill the Admin text field to return to one message per language; revert the deploy to restore calibration v1. The new column is nullable and ignored by older code. Owner pause (Smart template OFF) still stops everything.
