# Design

## Context

See proposal.md (Why) for the problem and the Duolingo evidence. Facts from the current code that shape this design (main `50231be`):

- **One job per account and local day** already exists (`smart_reminder_jobs`, D03). Telegram renders inside the authorization transaction before the attempt is committed (`SmartReminderTelegramDispatcher._dispatch` → `render_telegram_content`). PWA renders in `SmartReminderPwaDispatcher.dispatch` via `NotificationTemplateService.resolve(KEY_SMART_STUDY)` and `push_copy`. Android receives only a grant from `SmartReminderAndroidService.claim` and posts `Reminder.DAILY_GOAL` with `ReminderDecision.variant(day)` (`StudyReminderCoordinator.kt:30`).
- **Cadence** lives in `smart_reminder_cadence.evaluate_cadence` with `OBSERVED_RULES = ('smart-rules-observed-v1', min days 3, backoff 2, max unsuccessful 5, weekly 3)`. In ordinary (observed) mode `learning_complete_since` is always `None` and no path sets attempt state `verified_shown`, so `shown` is always empty: the back-off/stop branch never runs and the effective rule is already "every eligible day after the personal gap, capped by the weekly maximum". The daily, no-stop cadence of D32 therefore needs only a new weekly maximum.
- **Verified learning** for cadence comes from `SmartReminderPolicyContextService.load_cadence` plus `ObservedLearning.latest_activity_at` (XP lessons/tests/training, scored practice, voice). Streak truth is `course_miniapp_profile.current_streak` + `last_activity_date`, the same values the app and the legacy `streak_risk` sender use.
- **Copy** is canonical in `localization/ui/{uz,ru,tj}/notifications.json`, generated into `app/services/generated/notification_i18n.py`. The notification namespace has no plural support.
- **Results**: Smart analysis already records `contact_study_24h` facts per job (`SmartReminderAnalysisEvent`, 90-day detail, D21) and the Admin readout shows monthly totals (`app/admin_api/pwa_notifications.py`, `result['smart']`).

## Goals / Non-Goals

**Goals:** reuse the existing job, attempt, review, analysis and Admin structures; add one selection module and one column; keep each channel's transport, authorization and open-proof code unchanged except for where the text comes from.

**Non-Goals (design level; product exclusions are in proposal.md):** a per-channel copy path, Android-side copy catalogues, any change to personal-time or channel selection code.

## Decisions

### 1. One pure selector, called by all three channels
New `app/services/smart_reminder_messages.py` holds pure `situation(facts)` and `choose(pool, user_id, local_day, last_sent)` plus one entry point, `smart_study_content(session, user_id, job, lang, now)`, which Telegram, PWA and the Android claim call where they resolved the `smart_study` template before. Streak and the last study day come from `course_miniapp_profile.current_streak`/`last_activity_date`, the same source the app shows and the legacy `streak_risk` sender uses (a streak older than yesterday counts as 0). One bounded `GROUP BY` returns the latest local day per variant this account was actually sent (jobs with a started attempt), inside the caller's transaction. The returned text keeps `{lesson}`, so each channel's existing formatting and safety checks run unchanged.
*Alternative:* a separate per-channel copy table. Rejected: three copies drift, and Android would need an APK for every copy change.

### 2. Situation precedence
First match wins: `long_break` (8+ days) → `comeback` (2–7 days) → `streak` → `daily`. Copy names no day count because observed sources can undercount learning (D25); the 8-day boundary only switches tone.

### 3. Deterministic rotation with a recency window
Order the pool's keys by (last sent day, never sent first; then `sha256(user_id, local_day, key)`) and take the first. Least-recently-sent order already skips every variant received in the last 14 days while another remains, and no variant repeats before the whole pool has been used. This mirrors Duolingo's "recovering" penalty (~15-day half-life) without learned scores, is reproducible in tests and needs no randomness source.
*Alternative:* uniform random (Duolingo's control arm). Rejected: not reproducible and allows repeats.

### 4. Persist the choice on the job
Additive nullable `smart_reminder_jobs.content_key VARCHAR(48)` (e.g. `comeback.v3`). It is written under the job row lock in the transaction that renders and authorizes the attempt, and only if still null, so retries, the Android claim and receipt, and the inbox reuse it. Custom Admin text stores no key. The inbox record keeps `params={"template_service": "smart_study", "lesson": n}` and adds `content_key` and `streak`; the two existing re-render paths (inbox feed, PWA push copy) resolve the same variant in the reader's language. A variant missing from the catalog falls back to the default text and logs `smart_catalog_missing` without message text.
*Alternative:* store full rendered text. Rejected: language switch would show the stale language, and it duplicates catalog data.

### 5. Daily cadence as calibration v2, not a new engine
`OBSERVED_RULES` becomes `smart-rules-observed-v2` with `weekly_maximum=7`; the constant keeps its name, so the runtime and tests select it unchanged. Nothing else in `evaluate_cadence` changes: the personal-gap start, one-per-day ownership, OFF/pause/quiet, the unknown-outcome window and frozen windows stay. The unused back-off/stop branch remains only for native complete-coverage mode, so no ordinary account stops automatically (D32). The calibration version is not persisted in jobs, reviews or digests (it labels in-memory decisions only), so the deploy cancels no frozen job.
*Alternative:* a separate reactivation scheduler, or counting unanswered sends to stop after N. Rejected: duplicates ownership and budget rules, and the owner wants reminders to continue daily (D32).

### 6. Android receives rendered text, not keys
The claim response adds optional `message: {situation, content_key, title, body}`. The claim already happens online immediately before posting, so the server can render in the account language. The APK posts title/body when present and valid (non-blank, length-capped), uses `widget_panda_worried` for streak/comeback/long_break and `widget_panda_cheer` for daily, and otherwise falls back to today's `DAILY_GOAL` strings. The app's `Json { ignoreUnknownKeys = true }` keeps old APKs compatible; a decoder test pins this.

### 7. Admin: reuse the existing editor
`resolve()` now also reports whether the text is custom. The library is used only when the stored text for that language is empty; custom text is rendered as today on all three channels (Android receives it as the rendered body). The Smart editor's hint explains this in UZ/RU/TJ, the empty field no longer shows the old default as a placeholder, and the confirmation step names empty languages as the rotating library instead of the old default text.
*Deferred:* a per-situation Admin readout. The existing readout deliberately reads only the anonymous monthly aggregates and never the job or analysis-event tables; a per-situation count would need new monthly analysis stages. `content_key` on the job keeps that analysis possible later.

## Risks / Trade-offs

- [Daily messages with no stop raise bot blocks, OFF changes and Telegram spam reports] → one per day, varied copy, OFF/pause, the rollout's systemic pause and the Admin pause remain; watch bot blocks, OFF changes and per-situation counts in the first weeks and bring the numbers to the owner.
- [Observed learning undercounts (e.g. study on an untracked path) → a false `comeback`/`long_break`] → copy never claims a specific absence, and any verified study switches the situation back.
- [Android language may differ from the account language] → server uses the account language as Telegram/PWA do; verify on the owner's devices.
- [Calibration version change cancels frozen jobs or re-attests reviews at deploy] → checked: the cadence calibration version is not persisted or digested, so the deploy changes no frozen job.
- [Copy quality across 3 languages] → agent-owned QA per `localization/AI_CONTENT_QA_POLICY.md`; tone stays warm and honest, no guilt-tripping beyond Duolingo-style playfulness.
- [Too little traffic to judge which variants work] → no per-variant effectiveness claim; the stored key allows a later readout or D26 A/B.

## Migration Plan

1. Alembic revision after the current head adds the nullable column; downgrade drops it. No backfill.
2. Deploy backend: Telegram/PWA switch to the library immediately; Android keeps local text until the new APK.
3. Owner test accounts (`SMART_REMINDER_EARLY_USER_IDS`) observe a week on all three channels.
4. Release the APK only on owner instruction (D28).
5. Rollback as in proposal.md; the nullable column needs no rollback step.

## Open Questions

- Exact wording of the 32 variants per language is written during implementation and reviewed by the agent under the localization QA policy; it does not change the specs or tasks.
