# Proposal

## Why

Smart Reminder is live for every eligible learner (rollout 4/4; the owner's real-use test passed on 2026-11-22), but it sends one fixed message. Telegram and the iPhone PWA always render the single `smart_study` template ("continue lesson N"). The Android Smart path always posts the `DAILY_GOAL` text and rotates three local strings by date. Accounts moved to Smart also stop receiving the varied legacy evening texts (streak, daily goal, unfinished lesson), because those senders are vetoed for held accounts. A learner on a break therefore gets the same text, at most three times a week (D19).

The owner asked on 2026-11-22 to raise this to the level of Duolingo's reminder system. That means varied, situation-aware messages that keep inviting the learner back. The owner observed that Duolingo still sends daily reminders after more than a month without practice. Duolingo's published system ([Yancey & Settles, KDD 2020](https://research.duolingo.com/papers/yancey.kdd20.pdf); [Duolingo blog](https://blog.duolingo.com/hi-its-duo-the-ai-behind-the-meme/); [former CPO on growth](https://www.lennysnewsletter.com/p/how-duolingo-reignited-user-growth)) uses hand-written template pools with eligibility rules (for example "3+ day streak"), avoids recently seen templates because novelty fades (a "recovering" penalty with a ~15-day half-life), and sends a streak-saver message. Its bandit-learned template scores came later and need far more traffic than our ~100 Smart accounts.

This needs OpenSpec rather than a direct task. It changes owner decisions D08/D19/D20, the shared Telegram/PWA/Android delivery contract, a database column and UZ/RU/TJ copy. The authoritative sources remain [the Smart Reminder Master Plan](../../../docs/smart-reminders/SMART_REMINDER_MASTER_PLAN.md) (decisions and evidence) and the in-flight [`smart-reminder-account-orchestrator`](../smart-reminder-account-orchestrator/) change (consent, routing, one job per account/day, rollout). This change adds only the message layer and the daily cadence on top of them.

## What Changes

- **Situation-aware messages.** At render time the server classifies the day's single reminder as `daily`, `streak` (live streak of 2+ days), `comeback` (2–7 days since the last verified study) or `long_break` (8+ days). Each situation has a pool of canonical UZ/RU/TJ variants that use only the verified `{lesson}` and `{streak}` values.
- **No repeats.** The variant is chosen deterministically. A never-sent variant goes first, then the least recently sent; variants received in the last 14 days are skipped, and a stable per-account/day tie-break settles the rest. The chosen key is stored on the job, so retries and the in-app feed reuse the same message and later analysis can compare variants.
- **One message source for all channels.** Telegram and PWA render the variant on the server. The existing Android claim response gains an optional rendered `message` (situation, key, title, body). A new APK displays it with the matching panda icon, while older APKs ignore the field and keep today's local text.
- **Daily during a break, no automatic stop (D31–D33).** Up to 7 per rolling week (still 1 per day). Reminders continue on every eligible day without study until the learner returns, turns reminders off, blocks the bot or loses the push channel. **BREAKING (policy):** replaces the D19 ceiling and the D08/D20 back-off and stop for ordinary mode.
- **Admin stays minimal.** The existing "Message text" field keeps working: when it is empty the rotating library is used, and when it is filled that single text goes out for the language, exactly as now. Only the field's hint and confirmation wording change. No new control is added; a per-situation readout is left for later (the stored key keeps it possible).

## Capabilities

### New Capabilities
- `smart-reminder-messages`: situation classification, variant pools and rotation, cross-channel rendering, and daily cadence during a break for Smart study reminders.

### Modified Capabilities
- None under `openspec/specs/`. The related "Personal reactivation" and "Safe localized content" requirements live in the unarchived `smart-reminder-account-orchestrator` change. Their wording there now points to this change rather than being duplicated here.

## Impact

- **Backend:** `smart_reminder_cadence.py` (observed calibration v2, weekly 7), a new `smart_reminder_messages.py` (situation, variant and rendering), `smart_reminder_telegram_content.py`, `smart_reminder_pwa.py`, `smart_reminder_android.py` (claim payload and receipt inbox row), the inbox/PWA re-render paths, and the Admin confirmation preview in `app/admin_api/pwa_notifications.py`.
- **Database:** an additive Alembic revision adds nullable `smart_reminder_jobs.content_key`. Downgrade drops only that column.
- **Localization:** new `smart.msg.*` keys in `localization/ui/{uz,ru,tj}/notifications.json` plus the generated catalogs. The Admin hint copy changes in UZ/RU/TJ.
- **Android:** `AndroidSmartReminderApi.kt`, `StudyReminderCoordinator.kt`, `StudyNotifications.kt` and their tests. A new APK is needed, released only on owner instruction (D28).
- **Unchanged:** consent, OFF/pause/quiet hours, one study reminder per account/local day (D03), personal time selection, channel choice, rollout/admission, legacy D1 recovery and rating, payments and entitlements. Desktop stays frozen.
- **Excluded:** bandit/ML template scoring (D09/D26; too little traffic), a second same-day streak-saver, email, learner names in copy, streak freeze/repair, and the iOS widget.
- **Risk:** daily messages can raise bot blocks and spam reports. The rollout's systemic pause, the Admin pause and watching bot blocks and OFF changes in the first weeks are the safeguards.
- **Rollback:** fill the Admin text field to return to one message per language, or revert the deploy to restore calibration v1. The new column is nullable and ignored by older code. The owner pause (Smart template OFF) still stops everything.
