# Design

## Context

- Consent is read in `SmartReminderPreferencesService.read`. Telegram consent today comes from explicit `user_intent` rows or, without them, from the legacy snapshot (`legacy_on` → on, `not_enabled` → off). Android `this_device_consent` is only an explicit per-phone intent. `pwa_study_consent` needs master ON, or no master choice plus Telegram consent ON.
- The only learner-facing OFF on Telegram and PWA is the Mini App/PWA study switch `CourseMiniAppProfile.notifications_enabled` (`/api/v3/notify`, `/api/v3/pwa/notify`); Smart does not read it today. The Android Profile switch writes the per-phone Smart intent.
- Admission (`smart_reminder_rollout.SmartReminderAdmissionService`) pages three candidate sets (`new`: preference with a zone; `legacy`: Telegram users with the old reminder ON and no zone; `routed`) and computes one path: `android` (fresh native capability and phone consent ON) or `telegram`. Actors come only from a native Android session or a Telegram link.
- Routing rows allow `state IN ('held','telegram')`; `held` is the native Android owner, `telegram` the server sender owner (Telegram, and PWA for Telegram-linked accounts with a Telegram binding).
- An Android 1.7.29+ app reports its capability (protocol, autonomous posting off, OS permission) only once the account is held (`mode.server_claim_required`). It reconciles its local reminder switch from the server `this_device_consent` and shows the end-of-onboarding notification screen only while that switch is off.
- The shared course map handler stores the device offset from `tz` in `CourseProgress.reminder_tz_offset` for Telegram and PWA callers.

## Goals / Non-Goals

**Goals:** default ON per D34; PWA-only and Android-only admission; 30-day activity bound for default-only accounts; no client release.

**Non-Goals:** new UI, copy or settings; changing cadence, content, budget, quiet hours or the drain; the old-APK expansion; backfilling consent rows.

## Decisions

1. **Defaults are computed at read time, nothing is written.** A new rule replaces the legacy fallback: explicit `user_intent` for that source wins (other non-legacy sources keep their conservative effect); otherwise the default applies. Telegram default: `off` when `notifications_enabled` is false, else `on`; for Telegram the switch being off also overrides an older explicit ON, because the bot's reminder-time picker writes ON as a side effect. Android default per phone: explicit phone intent wins; else `off` when the switch is off; else `on` only when that phone's last capability report says notifications are allowed, otherwise `unknown`. Destination selection uses the same per-phone helper. *Alternative:* backfill ON consent rows. Rejected: irreversible, mixes defaults with real intent, and would hide the OS prompt.
2. **`pwa_study_consent` keeps its formula: explicit master ON, or no master choice and account study consent ON.** With decision 1 the account study consent is ON unless an explicit OFF or the Mini App/PWA switch applies, so this now means "no explicit OFF"; an explicit master ON still lets PWA serve a learner who turned Telegram off. The live push subscription stays separately required by the destination and dispatch, as today.
3. **PWA actor.** `SmartReminderActor(kind="pwa", device_id, session_id)` for a live PWA device session. `_lock` verifies the device is a non-revoked `pwa` device with a live session, like Android. It can read and set the zone only; a `study_enabled` write is refused. Runtime actor order: native Android, Telegram bot, then PWA.
4. **Routing state `pwa`.** A PWA-only owner gets `state='pwa'` with an account-wide binding `sha256(["smart-pwa-review-v1", user_id])`, the Telegram-style ownership fence (`native=False`: every active phone runs 1.7.29+ or reported server-only mode), and a review that requires PWA consent and a live subscription. Migration `0160` widens `ck_smart_reminder_routing_state` to include `pwa` and makes `review_required` apply to every non-`held` state. *Alternative:* reuse `telegram` with a different binding. Rejected: the state name would no longer say who owns sending, and `telegram` checks would need special cases.
5. **Android-only pre-hold.** Without a fresh capability the native path cannot be reviewed, and the app reports only after a hold. Admission therefore holds an unrouted account with a native session when every active phone is 1.7.29+, the phone is not explicitly OFF and a zone exists. The hold already vetoes the server legacy senders and stops 1.7.29+ local posting, so no double reminder is possible; the normal native review follows after the 24-hour drain once permission is reported allowed.
6. **Path order:** native Android (fresh, ON) → Telegram → PWA → Android pre-hold. A later better owner takes over through the existing re-hold, which cancels unattempted work.
7. **Candidates and the 30-day bound.** The `legacy` set no longer requires the old reminder ON or a Telegram link (it needs a course progress row, no zone, master not OFF, unrouted). Both `new` and `legacy` sets require: last learner activity or an Android/PWA device sign-in refresh within 30 days, or an earlier ON (old reminder ON, master ON, or an explicit `user_intent` ON). The zone for a PWA-only account derives from `reminder_tz_offset` as for bot-only learners.
8. **Planner and runtime.** `_reviewed` accepts `pwa` rows only for the PWA channel; `prepare` refuses a non-PWA destination for a `pwa` row. The runtime page includes `pwa` rows when the Web Push sender is configured.

## Risks / Trade-offs

- [Many more accounts at once] → admission is already bounded (8 per set per tick) and staged by the existing rollout health pause; the 30-day bound limits volume.
- [Learners with notifications off in Mini App lose Smart they had via the old reminder] → intended: that switch is their visible OFF.
- [Android-only phone never reports after the hold] → the account gets no reminder; before, it got one only if the local switch was on, and a 1.7.29+ app reports on its next periodic run. Dormant phones (14 days) drop out of the fence.
- [PWA-only zone is a fixed offset] → same as bot-only learners; Uzbekistan, Tajikistan and Russia keep no DST.
- [Bot reminder-time picker after a switch OFF] → the switch OFF wins on Telegram and PWA until the learner turns it back on.

## Migration Plan

Deploy server code with migration `0160` (constraint-only, SQLite batch and PostgreSQL). Rollback: revert code; delete routing rows in state `pwa` (they own no consent and only veto legacy senders), then downgrade `0160`, which refuses while such rows exist. The Admin PWA Smart template switch remains the immediate stop.

## D35: default send time

- `_personal_time` falls back in this order: manual time, learned habit, saved legacy time, then `PolicyContext.default_time`, with time source `default`. Only `SmartReminderPolicyContextService.load` sets `default_time` (21:00), so every dispatch path (reservation, claim, Android due, Telegram, PWA) and the widget see the same time, while pure simulations and the offline evaluator stay unchanged.
- The widget wire contract allows only `manual/saved/habit/unknown`, and installed Android apps reject other values. The widget therefore reports the default as `saved` with its real time.

