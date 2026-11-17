# Proposal

## Why

`return_retention` (D1/D7 return, audit row D5) is Overall-only. Its signup cohort has no platform of registration. This is requirement 4 of the next stage in `docs/analytics/ANALYTICS_INTEGRITY_IMPLEMENTATION_PLAN.md`, the single context file for this work (section "Next stage", R4).

A registration-platform column would change the auth paths, which is out of bounds. `user_client_presences` cannot date first use either: only the desktop-download status route writes it.

## What Changes

- **Reader only. No writer, no schema change.**
- **Cohort:** each account's **first verified use** of the platform:
  - **Android:** `android_first_open` or `android_app_opened`, or an `android_course` completion (all history). Android-tagged learning outcomes, including R1 `android_lesson_started`, count from the Android boundary.
  - **iPhone PWA:** a course-map open with the route-owned `pwa-course-v3:` key (all history). PWA-tagged learning outcomes count from the PWA boundary.
  - **Telegram:** a Telegram-tagged learning outcome from the Telegram boundary. Mini App opens have no exclusive signal (A3), so Telegram is a learning return.
- **Return:** the same platform's verified use 24–48 hours (D1) or 168–192 hours (D7) after first use. Use on another platform never counts.
- **Rules shared with Overall:** mature cohorts only, and the same period window (`_cohort_returns`). `attributed_since.return_retention` is the earliest first use.
- **Admin UI:** the existing D1/D7 return cards and cohort rows become available under each mobile filter. One line, in UZ/RU/TJ, states the cohort rule and its start date.
- **Registry and CI:** `return_retention` is `covered` on Android, Telegram and the PWA, with a route chain test in `analytics-integrity.yml`.

Overall impact: none. Overall `return_retention` is unchanged; the golden test pins it.

## Capabilities

### Modified Capabilities
- `admin-real-analytics`: D1/D7 return becomes a platform-scoped Course metric.
