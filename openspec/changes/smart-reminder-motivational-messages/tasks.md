# Tasks

Implementation starts only after the owner approves D31–D33 and gives the go-ahead (`AGENTS.md`). Evidence goes into the Master Plan checkpoint, not into this file.

## 1. Owner decisions and documents

- [ ] 1.1 Turn the PROPOSED D31–D33 rows in Master Plan §13 into DECISION rows with the owner's actual answers (adjust D31's number and the D32 days if the owner changes them, and the spec/design text with them); update the current-checkpoint line in `docs/smart-reminders/NEXT_CHAT_CONTEXT.md` to §17.101 and this change; verify each row keeps the D08/D19/D20 text it supersedes for ordinary mode and no second progress list is created.
- [ ] 1.2 Reconcile "Adaptive time and cadence", "Personal reactivation" and "Safe localized content" in `openspec/changes/smart-reminder-account-orchestrator/specs/smart-reminder-orchestration/spec.md` with D31–D33 by reference to this change; verify `openspec validate smart-reminder-account-orchestrator --strict` still passes.

## 2. Copy library (UZ/RU/TJ)

- [ ] 2.1 Add `smart.msg.<situation>.<nn>.title|body` to `localization/ui/{uz,ru,tj}/notifications.json` (daily 8, streak 6, comeback 8, last_call 2), plural-safe for `{streak}`, no day counts in comeback, then run `python3 scripts/i18n_build_all_catalogs.py --write` and `--check`; verify the generated catalog diff contains only these keys.
- [ ] 2.2 Extend `tests/test_notification_catalog_runtime.py` to fail on a missing language, placeholder other than `{lesson}`/`{streak}`, placeholder mismatch between languages, or length above the Telegram text/caption limit and the Web Push/Android title/body limits; verify it fails on a seeded bad key and passes on the real catalog.
- [ ] 2.3 Agent semantic QA of all variants under `localization/AI_CONTENT_QA_POLICY.md` (natural UZ Latin, RU, TJ Cyrillic; warm, honest tone); record the reviewed key list in the Master Plan checkpoint.

## 3. Backend selection and storage

- [ ] 3.1 Add the Alembic revision after the current head with nullable `smart_reminder_jobs.content_key VARCHAR(48)` and matching ORM field; verify upgrade → downgrade → upgrade on PostgreSQL and SQLite and identical migration/ORM columns.
- [ ] 3.2 Create `app/services/smart_reminder_messages.py`: pure situation precedence (`last_call` → `comeback` → `streak` → `daily`), 14-day recency rotation with stable hash tie-break, and rendering with only verified `{lesson}`/`{streak}` (reusing `PolicyContext.streak_current`); add `tests/test_smart_reminder_messages.py` covering the spec scenarios, including no repeat across a full pool and a pool smaller than 14 days.
- [ ] 3.3 Add a bounded loader for unanswered count and keys sent in the last 14 local days to `SmartReminderPolicyContextService`; verify with a SQL test that another account's jobs never affect the result.
- [ ] 3.4 Add `smart-rules-observed-v2` to `smart_reminder_cadence.py` (D31 weekly ceiling, D32 sequence, `reactivation_stopped` at 5) without touching native complete-coverage mode; extend `tests/test_smart_reminder_cadence.py` for D+1/2/3/5/7 then stop, reset on verified study, weekly ceiling deferral and personal-gap start; check whether the calibration version is bound into job/review digests and record the deploy consequence.

## 4. Channels

- [ ] 4.1 Telegram: `render_telegram_content` uses the selector when the Admin text for the language is empty, writes `content_key` once in the authorization transaction, keeps button, media and open-proof unchanged; extend `tests/test_smart_reminder_telegram_content.py` and `tests/test_smart_reminder_telegram.py` (custom text precedence, retry reuses key, inbox params carry `content_key`).
- [ ] 4.2 PWA: `SmartReminderPwaDispatcher` renders the same selected variant into title/body; extend `tests/test_smart_reminder_pwa.py` for variant rendering and one push per job.
- [ ] 4.3 Android claim: add optional `message {situation, content_key, title, body}` to the grant response; extend `tests/test_smart_reminder_android.py` for presence, reuse of the job's key on re-claim and Admin custom text arriving as the rendered body.
- [ ] 4.4 Inbox feed renders the stored `content_key` in the learner's current language; verify with a language-switch test (Telegram, PWA and Android receipts all store the key).

## 5. Android client

- [ ] 5.1 `AndroidSmartReminderApi.kt`: optional `message` on `SmartStudyClaim`; `SmartStudyBridge`/`StudyReminderCoordinator`/`StudyNotifications` post it with the situation's panda icon and fall back to existing `DAILY_GOAL` text when absent or invalid; add JVM tests for decode, fallback, icon mapping and an old-shape payload. Direct and Play variants both build.
- [ ] 5.2 APK version bump only when the owner asks for a release (D28); verify no release artifact is produced by this change otherwise.

## 6. Admin readout and coverage

- [ ] 6.1 `app/admin_api/pwa_notifications.py` adds anonymous `by_situation {sent, returned_24h}` for the current month; Admin PWA shows four compact rows in the existing results block and the updated folded hint in UZ/RU/TJ; extend `tests/test_admin_pwa_notifications.py` and run `admin_pwa_smart_browser.py` at 390 and 1440 px in all three languages.
- [ ] 6.2 Update `docs/analytics/FEATURE_ANALYTICS_COVERAGE.json` (Analytics Impact: reuse `contact_study_24h`, add situation/variant dimension) and monitoring mapping (Monitoring Impact: selector failure falls back to the default copy and logs a catalog reason code without message text); verify the `analytics-integrity` check passes.

## 7. Integration and acceptance

- [ ] 7.1 Run the Smart suites (`tests/test_smart_reminder_*.py`, motivation, Admin notifications, notification catalogs) on PostgreSQL and SQLite and the Android unit suite; record counts in the Master Plan checkpoint.
- [ ] 7.2 Owner test accounts: over 7 days confirm different texts on Telegram, iPhone PWA and Android (new APK, if released), and one simulated lapse on a test account ending with `last_call` and silence; record server job/attempt evidence separately from what the owner saw on the phone.
- [ ] 7.3 First production week: watch Admin per-situation counts, bot blocks, OFF changes and rollout pause reasons; record them before calling the feature done.
