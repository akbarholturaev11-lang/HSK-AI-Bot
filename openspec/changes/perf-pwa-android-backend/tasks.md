# Tasks

## 1. Learner PWA navigation and screen stability

- [x] 1.1 One edge swipe = one back step: claim the left 16 px strip in the browser PWA, keep a one-gesture token, and close before resetting the transform (`app/static/course-v3.html`). Verify:
  - `tests/e2e/test_pwa_swipe_back.py` passes on Chromium and WebKit, and fails on the pre-fix code;
  - in the iOS Simulator, three Safari edge swipes go word → list → Practice → Course;
  - the `goBack()` call-site count is unchanged.
- [x] 1.2 The dragged dictionary word page is opaque, with its scene art, and the list keeps its scroll (`app/static/hsk-lugat.html`). Verify: `test_dragged_word_page_is_opaque_and_closes_before_it_snaps_back`, plus a Chromium mid-drag screenshot.
- [ ] 1.3 Root-tab swipe peek: dragging Practice/Rating/Profile back to Course shows empty paper. The owner picks (a) a live peek of the previous tab or (b) no drag on root tabs (an edge swipe still goes back, without a peek). Then implement it and extend `test_pwa_swipe_back.py`. Verify with an iOS Simulator recording at 390 px.
- [ ] 1.4 Layer audit, one layer at a time: Settings, Friends, Inbox/notifications, Pro checkout, lesson dialogs, mistakes and practice iframes.
  - Each must close in one step by edge swipe, browser back and Telegram BackButton, with no blank frame and the previous scroll kept.
  - Add each layer to `test_pwa_swipe_back.py`, and fix only the defects found.
  - This merges contract lines "every screen at 320/390/430" and "audit embedded resources/Settings/Friends…" for back and scroll; loading geometry stays under 4.1.
- [ ] 1.5 Rating first load: use layout-faithful podium and leaderboard placeholders (contract open item "Current Rating example"). Verify with a `tests/pwa_layout_geometry.py` anchor check (≤8 px) on Chromium and WebKit.

## 2. Native Android

- [x] 2.1 The dictionary list keeps its scroll when returning from a word (`DictionaryScreen.kt`: `LazyListState` hoisted above the list/detail branch). Verify:
  - `DictionaryScrollRestoreTest` passes on Pixel_8, direct flavour, and fails on the pre-fix code;
  - `testPlayDebugUnitTest` passes (700 tests);
  - the 9 Android static checks pass.
- [ ] 2.2 Startup baseline:
  - Measure cold and warm start for the `play` and `direct` release builds on Pixel_8 and one weak real device (`adb shell am start -W`, 10 runs, median).
  - Add `reportFullyDrawn()` after the first useful Course frame.
  - Add a Baseline Profile (`profileinstaller`) only if the cold-start median exceeds the warm median by more than about 40% and a trace shows JIT/class loading dominating.
  - Record before/after numbers here.
- [ ] 2.3 Back and scroll audit of the other detail screens: Practice → Mistakes and Word drill, Rating → user, Profile pages and settings, lesson exit. Expect one `BackHandler` step with state retained. Add an instrumentation test for each defect found. The Course map re-centring on the current lesson is intended behaviour, not a defect.
- [ ] 2.4 Jank and ANR: owner exports Play Console vitals and the existing crash/monitoring data for the top screens. Fix only the top offenders, each with a regression test.

## 3. Backend learner paths (production 7-day evidence)

- [ ] 3.1 `POST /api/v3/lesson/complete` (p50 ≈215 ms, p95 ≈490–670 ms, p99 ≈1.0–1.5 s):
  - In a real-Postgres test, record the SQL statement count and the time of each synchronous side effect (XP, streak, reminders, analytics).
  - Move only proven non-critical work after commit, using the existing worker pattern; keep progress and XP atomic.
  - Verify with the query-count test before and after, plus production p50/p95 after deploy.
- [ ] 3.2 `POST /api/v3/lesson/start` (p50 ≈62 ms, p90 ≈400 ms): find the slow mode (content or cache miss); use the existing course content/template cache only if proven. Verify with a cold/warm timing test and production p90.
- [ ] 3.3 `GET /api/v3/pwa/profile` (p99 spike 3.4 s): find the slow call in `railway logs --http` and fix it, or record that the cause is external. Verify with the existing profile tests.
- [ ] 3.4 Keep fast paths unchanged: session p95 ≈43 ms, course HTML p95 ≈93 ms, `/api/v3/map` p95 ≈310–370 ms. The existing `tests.test_course_map_template_cache` and `tests.test_course_today_service` remain the guard; no new work.

## 4. Measurement and owner acceptance

- [ ] 4.1 PWA field-like measurements before and after:
  - slow-4G filmstrip plus LCP, CLS and INP at 390 px for Course, Practice, Dictionary and Profile, on Chromium trace and WebKit;
  - record them in `docs/PERFORMANCE_PWA_PROGRESSIVE_LOADING.md` (closes the open "filmstrip / LCP/CLS/INP" items).
- [ ] 4.2 Owner device QA on a real iPhone Home Screen PWA and a real Android phone: edge swipe from word, list, Practice and Settings goes back one step with no white flash. Android dictionary returns to the same row.

## 5. Permanent workflow

- [x] 5.1 Extend the existing guard rather than adding a new system. Verify that `tests.test_backend_pwa_performance_contract` passes and that the checker passes on this branch with `--enforce-change-tests`. The extension:
  - `check_backend_pwa_performance_contract.py` requires an Android `*Test.kt` co-change and the swipe-back regression;
  - the workflow runs the regression on Chromium and WebKit;
  - `AGENTS.md` and the contract doc gain the Android and navigation rules.

## Workflow follow-up

- Archive this change once groups 1–4 are complete and owner QA (4.2) is recorded.
