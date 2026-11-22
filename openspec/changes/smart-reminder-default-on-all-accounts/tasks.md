# Tasks

The owner approved D34 on 2026-11-22 (default ON for every sign-in method, Telegram users who turned the old reminder off included, iPhone PWA push switch and Android phone permission as the consent signal, 30-day activity bound). Evidence goes into the Master Plan checkpoint.

## 1. Decision record

- [x] 1.1 Add the D34 DECISION row to Master Plan §13, noting the D01/D14/§17.89 text it supersedes, and a new checkpoint; update the current-checkpoint line in `docs/smart-reminders/NEXT_CHAT_CONTEXT.md`; verify `openspec validate smart-reminder-default-on-all-accounts --strict` passes.

## 2. Consent defaults

- [x] 2.1 `smart_reminder_preferences.py`: default rule for Telegram consent and per-phone Android consent, Mini App/PWA switch as OFF, `pwa_study_consent` per design 2; verify with focused preference tests (no rows, legacy OFF, explicit OFF, switch off, Android allowed/denied/unknown).
- [x] 2.2 `smart_reminder_destination.py`: use the same per-phone rule; verify a default-ON phone with permission allowed is a destination and an explicit OFF phone is not.

## 3. PWA-only and Android-only admission

- [x] 3.1 PWA actor in preferences `_lock`/`_mutate` and in `SmartReminderShadowWorker.actor_for`; verify a revoked device or expired session is refused and `study_enabled` is refused.
- [x] 3.2 Migration `0160_smart_routing_pwa_state` and model constraints; verify upgrade/downgrade on SQLite and PostgreSQL and that downgrade refuses with a `pwa` row.
- [x] 3.3 Routing hold/review/refresh for `pwa` in `smart_reminder_telegram.py`; admission paths, Android pre-hold, candidate sets and the 30-day bound in `smart_reminder_rollout.py`; verify with rollout tests (PWA-only admitted after drain, Android-only held then reviewed after permission, dormant default-only account skipped, old-reminder user still admitted, old APK still fenced).
- [x] 3.4 Planner `_reviewed`/`prepare` and runtime page for `pwa`; verify an end-to-end PWA-only account gets one Web Push and zero Telegram sends.

## 4. Verification

- [x] 4.1 Run the Smart reminder suites on SQLite and the storage/migration suites on PostgreSQL; record counts in the checkpoint with Analytics Impact and Monitoring Impact.
- [x] 4.2 Confirm no Android, Mini App or PWA client file and no localized string changed.

## Workflow follow-up

- Production readout after deploy (Admin PWA review count and rollout health) needs the owner's go-ahead for read-only observation.
