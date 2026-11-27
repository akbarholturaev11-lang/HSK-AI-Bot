# Proposal

## Why

On 2026-11-22 only about 97 accounts had a current Smart review. The code admits an account only when it already consents through the old Telegram lesson reminder or an explicit Smart choice, and only on the Telegram or native Android path. Learners who never turned on the old reminder, iPhone PWA learners without Telegram, and Android learners signed in with Google/Apple never get Smart. The owner decided (D34, 2026-11-22) that Smart must work for every sign-in method, be ON by default, and rely on the phone's own permission prompt. The existing plan (`smart-reminder-account-orchestrator`, Master Plan D01/D14 and §17.96–§17.100) deliberately says "admission never creates consent" and keeps a legacy OFF as OFF, so it cannot deliver this without a scoped policy change.

Authoritative sources: `docs/smart-reminders/SMART_REMINDER_MASTER_PLAN.md` (D01, D14, D30–D33, §17.96–§17.101), `openspec/changes/smart-reminder-account-orchestrator/`, `openspec/changes/smart-reminder-motivational-messages/`.

## What Changes

- **BREAKING (policy, D34):** Smart study consent is ON by default for every account. An explicit Smart OFF, the account Smart master OFF, and the Mini App/PWA study reminder switch (`notifications_enabled = false`) still stop it. The old Telegram lesson reminder being off (including an old explicit OFF) no longer counts as a Smart OFF (owner chose "Ha, hammaga yoqilsin").
- **Android:** with no explicit choice on that phone, the phone's notification permission is the consent signal: once the phone reports that notifications are allowed, the device counts as ON. The existing end-of-onboarding notification screen keeps asking through the system prompt; no new screen or text.
- **iPhone PWA:** a live push subscription from the existing Notices/Settings push switch is the consent signal unless Smart is OFF. No new onboarding step.
- **Every sign-in method:** automatic admission also admits accounts without Telegram: PWA-only accounts through Web Push, and Android-only (Google/Apple) accounts through the existing native claim path.
- **Activity bound (owner choice 2026-11-22):** the default ON admits only accounts active in the last 30 days. An account with an existing explicit or legacy ON keeps today's admission. A dormant account joins when it is active again. Already admitted accounts are unchanged (D32 keeps daily reminders).
- Unchanged: the old-APK (<1.7.29) fence, OS-denied permission, blocked bot, account deletion, one reminder per account and local day, the Admin PWA pause, and the 24-hour drain before a new owner.

## Capabilities

### New Capabilities
- `smart-reminder-reach`: who Smart study reminders reach by default, which signals count as consent and OFF on each surface, and how accounts without Telegram are admitted.

### Modified Capabilities
<!-- None under openspec/specs/: Smart orchestration requirements live in the unarchived change smart-reminder-account-orchestrator, which this change references. -->

## Impact

- Server only: `app/services/smart_reminder_preferences.py` (consent defaults, PWA actor), `smart_reminder_rollout.py` (candidates, PWA and Android-only paths, 30-day bound), `smart_reminder_telegram.py` (routing hold/review/refresh for PWA), `smart_reminder_planner.py`, `smart_reminder_runtime.py`, `smart_reminder_shadow_worker.py`, `smart_reminder_destination.py`.
- Database: migration `0160` lets a routing row be in state `pwa` (check constraints only, no data change; downgrade refuses while `pwa` rows exist).
- Clients: no Android APK change (existing 1.7.29+ reports permission and follows the server consent), no Mini App/PWA UI or copy change, so no new RU/TJ/UZ text.
- Out of scope: payment, subscription, QA mode, Mini App UI, the old-APK expansion, Admin per-situation statistics, a new PWA settings screen.
- Rollback: revert the server change; routing rows in state `pwa` must be removed (they only veto legacy senders) before the migration downgrade. The Admin PWA Smart template switch still pauses all Smart sends at once.
