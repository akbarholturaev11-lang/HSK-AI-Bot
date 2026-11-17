# Proposal

## Why

Android writes no lesson start (audit row A7). Course > Android therefore has no lessons entry, and Overall `features.lessons` / `started_accounts` never count an Android learner as started. This is requirement 1 of the next stage recorded in `docs/analytics/ANALYTICS_INTEGRITY_IMPLEMENTATION_PLAN.md`, the single context file for this work (section "Next stage", R1).

`lesson_started` cannot be reused: `motivation_reminder_service.py` reads it for the D1 recovery and unfinished-lesson Telegram reminders, so an Android row under that name would send new messages. `android_lesson_started` is server-only and is already read by the Overall V10 readers and bot-block diagnostics, but by no product flow.

## What Changes

- **Writer:** the authenticated Android lesson route writes one `android_lesson_started` per account, level, lesson and UTC day, with source `android_course` and the route-set client `android`. Refused lessons write nothing. Telemetry failure never changes the lesson response. Desktop is unchanged.
- **Reader:** Course > Android `features.lessons` counts tagged rows from their own boundary (`attributed_since.features_lessons`). The Admin feature panel shows that date with existing UZ/RU/TJ strings.
- **Registry and CI:** `android_lesson_started` becomes a declared event of the `lessons` flow, the Android reasons are updated, and the route chain test runs in `analytics-integrity.yml`.

Overall impact: from the deploy date, Android starts enter Overall `features.lessons` and Overview `started_accounts`. Activation and lesson time are unchanged.

## Capabilities

### Modified Capabilities
- `admin-real-analytics`: Android lesson starts become a platform-scoped Course metric.
