# Tasks

The owner approved D31–D33 and implementation on 2026-11-22. Evidence goes into the Master Plan checkpoint, not into this file.

## 1. Owner decisions and documents

- [x] 1.1 Turn the PROPOSED D31–D33 rows in Master Plan §13 into DECISION rows with the owner's actual answers (adjust D31's number and the D32 days if the owner changes them, and the spec/design text with them); update the current-checkpoint line in `docs/smart-reminders/NEXT_CHAT_CONTEXT.md` to §17.101 and this change; verify each row keeps the D08/D19/D20 text it supersedes for ordinary mode and no second progress list is created.
- [x] 1.2 Reconcile "Adaptive time and cadence", "Personal reactivation" and "Safe localized content" in `openspec/changes/smart-reminder-account-orchestrator/specs/smart-reminder-orchestration/spec.md` with D31–D33 by reference to this change; verify `openspec validate smart-reminder-account-orchestrator --strict` still passes.

## 2. Copy library (UZ/RU/TJ)

- [x] 2.1 Add `smart.msg.<situation>.v<n>.title|body` to `localization/ui/{uz,ru,tj}/notifications.json` (daily 8, streak 6, comeback 8, long_break 10), plural-safe for `{streak}`, no day counts, then run `python3 scripts/i18n_build_all_catalogs.py --write` and `--check`; verify the generated catalog diff contains only these keys.
- [x] 2.2 Extend `tests/test_notification_catalog_runtime.py` to fail on a missing language, placeholder other than `{lesson}`/`{streak}`, placeholder mismatch between languages, or length above the Telegram text/caption limit and the Web Push/Android title/body limits; verify it fails on a seeded bad key and passes on the real catalog.
- [x] 2.3 Agent semantic QA of all variants under `localization/AI_CONTENT_QA_POLICY.md` (natural UZ Latin, RU, TJ Cyrillic; friendly, informal and honest tone per the owner's 2026-11-22 request; every title and body unique per language); record the reviewed key list in the Master Plan checkpoint.

## 3. Backend selection and storage

- [x] 3.1 Add the Alembic revision after the current head with nullable `smart_reminder_jobs.content_key VARCHAR(48)` and matching ORM field; verify upgrade → downgrade → upgrade on PostgreSQL and SQLite and identical migration/ORM columns.
- [x] 3.2 Create `app/services/smart_reminder_messages.py`: pure situation precedence (`long_break` → `comeback` → `streak` → `daily`), least-recently-sent rotation with stable hash tie-break, and rendering with only verified `{lesson}`/`{streak}` (profile streak and last activity day, as the app shows them); add `tests/test_smart_reminder_messages.py` covering the spec scenarios, including no repeat across a full pool.
- [x] 3.3 Add a bounded loader for the latest day per variant this account was actually sent (in `smart_reminder_messages.py`, inside the caller's transaction); verify with a SQL test that another account's, unsent and current jobs never affect the result.
- [x] 3.4 Add `smart-rules-observed-v2` (weekly maximum 7) to `smart_reminder_cadence.py` and select it where `OBSERVED_RULES` is used, without touching native complete-coverage mode; extend `tests/test_smart_reminder_cadence.py` for one reminder on each of 30 break days, no reminder on a studied day, the personal-gap start and one per day; check whether the calibration version is bound into job/review digests and record the deploy consequence.

## 4. Channels

- [x] 4.1 Telegram: `render_telegram_content` uses the selector when the Admin text for the language is empty, writes `content_key` once in the authorization transaction, keeps button, media and open-proof unchanged; extend `tests/test_smart_reminder_telegram_content.py` and `tests/test_smart_reminder_telegram.py` (custom text precedence, retry reuses key, inbox params carry `content_key`).
- [x] 4.2 PWA: `SmartReminderPwaDispatcher` renders the same selected variant into title/body; extend `tests/test_smart_reminder_pwa.py` for variant rendering and one push per job.
- [x] 4.3 Android claim: add optional `message {situation, content_key, title, body}` to the grant response; extend `tests/test_smart_reminder_android.py` for presence, reuse of the job's key on re-claim and Admin custom text arriving as the rendered body.
- [x] 4.4 Inbox feed renders the stored `content_key` in the learner's current language; verify with a language-switch test (Telegram, PWA and Android receipts all store the key).

## 5. Android client

- [x] 5.1 `AndroidSmartReminderApi.kt`: optional `message` on `SmartStudyClaim`; `SmartStudyBridge`/`StudyReminderCoordinator`/`StudyNotifications` post it with the situation's panda icon and fall back to existing `DAILY_GOAL` text when absent or invalid; add JVM tests for decode, fallback, icon mapping and an old-shape payload. Direct and Play variants both build.
- [ ] 5.2 APK version bump only when the owner asks for a release (D28); verify no release artifact is produced by this change otherwise.

## 6. Admin readout and coverage

- [x] 6.1 Admin Smart editor: UZ/RU/TJ hint that an empty field means the rotating library, no old default as placeholder, and the confirmation names empty languages as the library (`proposed.library_languages`); extend `tests/test_admin_pwa_notifications.py`. The per-situation readout is deferred (design §7): the readout reads only anonymous monthly aggregates.
- [x] 6.2 Analytics/monitoring: no changed file is an analytics critical path, so the registry is unchanged (existing `contact_study_24h` stays; the job's `content_key` is the new variant dimension). A missing catalog variant falls back to the default copy and logs `smart_catalog_missing` without message text; verify the `analytics-integrity` check passes.

## 7. Integration and acceptance

- [ ] 7.1 Run the Smart suites (`tests/test_smart_reminder_*.py`, motivation, Admin notifications, notification catalogs) on PostgreSQL and SQLite and the Android unit suite; record counts in the Master Plan checkpoint.
- [ ] 7.2 Owner test accounts: over 7 days confirm different texts on Telegram, iPhone PWA and Android (new APK, if released), and that a test account on a break moves from `comeback` to `long_break` copy; record server job/attempt evidence separately from what the owner saw on the phone.
- [ ] 7.3 First two production weeks: watch Admin per-situation counts, bot blocks, OFF changes and rollout pause reasons; report them to the owner and record them before calling the feature done.
