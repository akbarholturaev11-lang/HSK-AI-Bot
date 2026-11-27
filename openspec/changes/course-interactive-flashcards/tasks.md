# Tasks

## 1. Backend plan

- [x] 1.1 Flags `COURSE_LESSON_PLAN_ENABLED`, `_ROLLOUT_PERCENT`, `_ALLOWLIST` in `app/config.py`
- [x] 1.2 Curated `app/services/data/lesson_picture_words.json` (hanzi → emoji, levels) with a guard test
- [x] 1.3 `app/services/course_lesson_plan_service.py`: candidates, budget, goal/focus selection, anchor
- [x] 1.4 Attach plan in `_lesson_content_for_user` (Mini App/PWA) and `AndroidCourseService.lesson`; failure → no plan
- [x] 1.5 Empty transcript → `unclear`, no mastery/mistake write (`voice_practice_service.py`)
- [x] 1.6 Unit tests: budget per minutes/goal, protected cards, learned-only words, determinism, flag off

## 2. PWA / Mini App (`course-v3.html`)

- [x] 2.1 Apply `omit` after `material_ref`, insert `_picture_review` step at the anchor (skip on preview_half)
- [x] 2.2 Stacked deck renderer: 3D settle, picture front, existing mic + Skip markup, flip 160°, pass/fail motion, requeue, reduced motion
- [x] 2.3 UZ/RU/TJ copy in `localization/ui/*/course.json`, regenerate catalogs
- [x] 2.4 Browser smoke: mobile viewport, three languages, no console errors, completion unchanged

## 3. Android

- [x] 3.1 Apply `lesson_plan` after `LessonParser` in `data/lesson/LessonPlan.kt` (omit + `PictureReviewCard` at anchor; ignored for stale copies and previews, after the `total_cards` check)
- [x] 3.2 ViewModel deck state (queue, requeue, skip, unclear, limit) reusing the pronunciation scorer
- [x] 3.3 Compose deck UI matching PWA (stack, flip, motion, same Skip look), glyph check
- [x] 3.4 New strings come from the shared course catalog (`hsk_course_picture_review_*` in generated `hsk_course_i18n.xml`, uz/ru/tg)
- [ ] 3.5 Unit tests (parser, ViewModel), static gates, `assembleDirectDebug`, emulator run

## 4. Acceptance (not automated)

- [ ] 4.1 Real voice check on an iPhone PWA and an Android phone (owner)
- [ ] 4.2 Rollout: allowlist → percent; flag-off rollback verified on staging
