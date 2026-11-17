# Tasks

## 1. Backend contract and state

- [x] 1.1 Migration `0158_course_adaptive_lessons`: `course_mistake_targets.adaptive_state_json`, `adaptive_due_on` + index; table `course_adaptive_plans`; QA bootstrap head/deferred table list
- [x] 1.2 Extract the shared `schedule_box` rule from `CourseWordMasteryService` without behaviour change
- [x] 1.3 `CourseAdaptiveLessonService`: skill mapping, lazy derivation, selection, plan persistence, answer grading/state transition, final check, word-mastery hand-off
- [x] 1.4 `app/api/course_adaptive.py`: Telegram, PWA and Android plan/answer routes with existing auth helpers
- [x] 1.5 Flags `COURSE_ADAPTIVE_ENABLED`, `_ROLLOUT_PERCENT`, `_ALLOWLIST`, `_SHADOW_ENABLED`; analytics event registry and coverage registry rows

## 2. Clients

- [x] 2.1 PWA `course-v3.html`: async plan load, slot placement, overlay card, separate feedback bar, offline outbox; UZ/RU/TJ course catalog keys
- [x] 2.2 Android: `AndroidAdaptiveApi`, `AdaptiveLessonRepository`, overlay state in `LessonViewModel`, overlay card in `LessonScreen` (`LessonAdaptiveReview`), generated `hsk_course_adaptive_*` strings

## 3. Verification

- [x] 3.1 Unit: skill mapping, derivation, schedule, independence, need 3/4, retirement, final check, selection limits and track isolation
- [x] 3.2 Integration/contract/security: plan stability, ownership, track/lesson checks, forged item, duplicate, stale plan, flag off/rollout/shadow, Xatolarim untouched on correct answers
- [x] 3.3 Regression: lesson completion, Xatolarim, word mastery, i18n, analytics/monitoring guards, asset tokens
- [x] 3.4 ON/OFF equivalence: identical completion payload/counters for identical base answers (PWA flow test and Android ViewModel test)
- [x] 3.5 Android unit tests and compile for play and direct flavours
- [ ] 3.6 Device QA still required before rollout: Safari + Home Screen PWA, Android Play and Direct, HSK 2.0/3.0, UZ/RU/TJ
- [ ] 3.7 Rollout: shadow → allowlist → percentage; owner approval before `main` merge and production flag change
