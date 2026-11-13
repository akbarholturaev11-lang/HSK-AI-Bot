# Tasks

Only checklist for R1. Context, decisions and the next step live in `docs/analytics/ANALYTICS_INTEGRITY_IMPLEMENTATION_PLAN.md` ("Next stage", R1). Stacked on PR #285; nothing merges to `main` without the owner's permission.

## 1. Writer

- [x] 1.1 `AndroidCourseService.lesson` records `android_lesson_started` (source `android_course`, client `android`, day dedupe) after the lesson is returned; failure isolated in its own commit.
- [x] 1.2 Unit tests: one tagged row, same-day dedupe, refused lesson writes none, writer failure keeps the lesson, no `lesson_started` row.

## 2. Reader, registry and UI

- [x] 2.1 Course > Android `features.lessons` from tagged `android_lesson_started` with its own `attributed_since.features_lessons`.
- [x] 2.2 Registry: declared event, Android reasons, critical path for `android_course_service.py` `lesson`; checker passes in push and pull-request modes.
- [x] 2.3 Admin feature panel shows the lessons boundary with existing UZ/RU/TJ strings.

## 3. Proof

- [x] 3.1 Route → PostgreSQL → `/api/admin/v1/analytics` chain test for Android `features.lessons`, listed in `analytics-integrity.yml`.
- [x] 3.2 Overall: golden test unchanged; a test pins Android starts in Overall `features.lessons` with one count per account.
- [x] 3.3 Full unit suite, PostgreSQL modules, analytics CI list and Admin PWA browser suites; results recorded in the context file. Result on the final head `1c5162ed` (local PostgreSQL 15): full unit suite 5193 passed with only the 8 known baseline failures; all 52 PostgreSQL modules 748 passed, 12 skipped, 0 failed; Admin PWA browser harness passed; checker passes in push and pull_request modes.
- [ ] 3.4 Owner acceptance on an Android device (6.2 style) after deploy.
