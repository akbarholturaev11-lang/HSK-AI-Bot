# Tasks

Order: PWA → Android → Backend, as the owner asked. Android stays in the same
initiative and regression matrix.

Each package is its own pull request with its own tests. Every completion note
carries an "Analytics Impact:" and a "Monitoring Impact:" line. Every PWA HTML
edit re-anchors the i18n line counts and `reviewed_sha1` once, by exact line
identity.

## 1. PWA measurement baseline (no product code)

- [ ] 1.1 Add `scripts/measure_pwa_lab.py`, built on the existing `ScreenPage`
  e2e fixture.
  - It serves the fixture over HTTP with production-like gzip, ETag and
    immutable headers, and fails if the first response lacks them.
  - It runs cold and warm, at 320, 390 and 430 px, on Chromium and WebKit,
    with slow 4G and 4× CPU, and prints JSON.
  - Document the command and the profile in
    `docs/PERFORMANCE_PWA_PROGRESSIVE_LOADING.md`.
  - Verify: the documented command runs as written, and two consecutive runs
    agree within 15% on FCP and course-ready.
- [ ] 1.2 Extend the harness fixture to drive a real lesson open, one exercise
  advance and the real practice pages, reusing the lesson fixtures already in
  `tests/e2e/`. Verify: the harness reports time to the first usable exercise,
  time to the next exercise, and each practice page's first useful frame.
- [ ] 1.3 Record the before baselines with 1.1 on both engines, and set a
  target per action from them. Record them in the contract doc, which closes
  its open items "every screen at 320/390/430", "filmstrip LCP/CLS/INP" and the
  Rating filmstrip.
  - Cold and warm launch.
  - Tab switches.
  - First open of each layer: Dictionary, Phrases, five practice pages, Inbox,
    Settings.
  - Dictionary search with hanzi, pinyin and a translation query.
  - Swipe-back.
  - Lesson open and exercise advance.

  Verify: the table lists both engines, and every action has a number or is
  marked "unmeasured" with the reason.
- [ ] 1.4 Real-user launch timing (PWA only) through the existing `clog()`
  beacon to `/api/v3/clientlog`.
  - One beacon per launch after the course is ready.
  - Fields: navigation timing, FCP, LCP, CLS, the slowest event duration,
    course-ready time, cold/warm, 200/304, viewport class, standalone or
    browser.
  - No account, text or token. No retry.

  Verify:
  - an e2e test asserts exactly one beacon per launch, with only the allowed
    keys, and none when the course fails;
  - the analytics and monitoring checker passes;
  - after deploy, 7 days of beacons are read with `railway logs` and their
    p50/p75 recorded in the contract doc.

## 2. PWA fixes (each its own pull request, after 1.3)

- [x] 2.1 One edge swipe = one back step: claim the left 16 px strip, keep a
  one-gesture token, and close before resetting the transform
  (`course-v3.html`). Verified on Chromium and WebKit
  (`tests/e2e/test_pwa_swipe_back.py`, which fails on the old code) and with
  iOS Simulator Safari. Merged in PR #346.
- [x] 2.2 The dragged dictionary word page is opaque, with its scene art
  (`hsk-lugat.html`). Verified by
  `test_dragged_word_page_is_opaque_and_closes_before_it_snaps_back`. Merged in
  PR #346.
- [ ] 2.3 Inbox loading and error states (`iphone-pwa-notices.js`, the Inbox
  layer in `course-v3.html`). Show notice-shaped placeholder rows while the
  feed is pending. On an error, show the error with an in-place retry using an
  existing reviewed UZ/RU/TJ retry string. Owner-switch checks stay unchanged.
  Verify:
  - a held-request test in `tests/test_pwa_notices_ui.js` covers
    pending → rows, fail → error → retry → ready, and an owner switch;
  - a Chromium/WebKit geometry check at 320, 390 and 430 px shows ≤8 px;
  - the i18n guard passes;
  - lab Inbox open before/after from 1.1.
- [ ] 2.4 Embedded-layer text status: only if 1.3 shows the parent
  "Yuklanmoqda…" for more than 300 ms when the layer is warm-opened on WebKit.
  Delay the text with an anti-flash window so a fast frame paints its own
  skeleton first. Verify: lab before/after for Phrases and the practice pages,
  and `test_pwa_swipe_back.py` still passes. If the threshold is not crossed,
  record "not needed" with the numbers.
- [ ] 2.5 Root-tab drag: the owner chose (a), a live Course peek underneath. Verify: `test_pwa_swipe_back.py` gains a
  root-tab case asserting no empty frame and one step back, plus an iOS
  Simulator recording at 390 px.
- [ ] 2.6 Back and scroll audit, one layer at a time:
  - Settings, Friends, Inbox and checkout;
  - lesson dialogs, the writer overlay and the five practice pages.

  Each layer must close in one step by edge swipe, browser back and Telegram
  BackButton, with no blank frame and the previous scroll kept. Fix only the
  defects found, adding each layer to `test_pwa_swipe_back.py`. Verify:
  Chromium and WebKit pass, and the swipe test's checker entry is unchanged.
- [ ] 2.7 Lesson open and exercise advance: if 1.3 shows either misses its
  target, trace it in Chromium and WebKit and fix only the top cause. Lesson
  grading, progress and payment code are not changed. Verify: lab before/after,
  and the existing lesson e2e and unit suites pass. Otherwise record "meets
  target".

- [ ] 2.8 Panda vs skeleton split, per the owner's decision in design.md.
  - Map each practice page's hub view and session start.
  - Hubs (Test centre, Mistakes centre, and the Dictionary and Phrases
    layers) get layout-faithful skeletons.
  - The panda preparing screen shows only at a real session start, with no
    artificial delay and an error retry.

  Verify:
  - Chromium/WebKit tests show the hub opens with a skeleton and no panda, and
    a session start shows the panda until the session is ready;
  - the hubs pass the 320/390/430 geometry check (≤8 px);
  - lab before/after from 1.1.

## 3. Native Android (same initiative, after group 2)

- [x] 3.1 The dictionary list keeps its scroll when returning from a word
  (`DictionaryScreen.kt`). Verified by `DictionaryScrollRestoreTest` (Pixel_8,
  direct flavour; it fails on the old code) and by `testPlayDebugUnitTest`.
  Merged in PR #346.
- [ ] 3.2 Startup baseline and first-drawn report.
  - Call `reportFullyDrawn()` once when the first useful Course frame (cached
    map or skeleton) is shown.
  - Measure cold and warm start for the play and direct release builds on
    Pixel_8 and on the owner's weak device: `adb shell am start -W`, 10 runs,
    median `TotalTime` and fully-drawn time.
  - Add a baseline profile only if the cold median exceeds warm by more than
    40% and a trace shows JIT or class loading dominating.

  Verify: a test asserts the report fires once; the before/after numbers are
  recorded in `ANDROID_CONTEXT.md`.
- [ ] 3.3 Replace the two full-screen loaders with `HskSkeleton` compositions
  shaped like the ready screens: first-ever Course open (`CourseScreen.kt`,
  `map == null`) and Ready Phrases (`ReadyPhrasesScreen.kt`). Verify:
  instrumentation tests on the direct flavour show the header plus
  placeholders with no centred spinner, and the header and first row move by
  ≤8 dp when data lands. `testPlayDebugUnitTest` passes.
- [ ] 3.4 Back and scroll audit:
  - Practice → Mistakes and Word drill;
  - Rating → user;
  - the Profile pages and settings;
  - lesson exit.

  Expect one back step with state retained. Add an instrumentation test for
  each defect found. Course re-centring on the current lesson is intended
  behaviour. Verify: the new tests pass on the direct flavour.
- [ ] 3.5 Jank and ANR.
  - Record frame stats (`adb shell dumpsys gfxinfo`) for Course and Dictionary
    scrolling on Pixel_8.
  - Read the owner's Play Console vitals export.
  - Fix only the top offenders, each with a regression test.

  Verify: before/after frame stats are recorded in `ANDROID_CONTEXT.md`.

## 4. Backend (after group 3)

- [ ] 4.1 `POST /api/v3/lesson/complete`.
  - In a real-Postgres test, record the statement count and the time of each
    step: rank before, award, rank after, analytics, mistakes.
  - If the leaderboard dominates, replace both calls with one bounded query
    that returns the user's rank and the neighbour rows. A snapshot test
    asserts identical rank, rank-up flag and neighbour rows for leagues of 1,
    5 and 500 users with ties.
  - Progress, XP and streak stay in one transaction.

  Verify:
  - the query-count test before and after;
  - `tests.test_course_map_template_cache`, `tests.test_course_today_service`
    and the Mini App and Android lesson contract tests pass;
  - production p50/p95 after deploy.
- [ ] 4.2 `POST /api/v3/lesson/start` p90 ≈400 ms against p50 ≈62 ms. Find the
  slow mode (content load, cache miss or lock) from `railway logs --http` and a
  cold/warm timing test. Fix only if the cause is in the app. Verify:
  production p90 after deploy, or a recorded external cause.
- [ ] 4.3 `GET /api/v3/pwa/profile` p99 spike of 3.4 s. Find the slow call in
  the HTTP logs. Fix it, or record that the cause is external. Verify: the
  existing profile tests pass, and production p99 after deploy.
- [ ] 4.4 Network gap. With 7 days of 1.4 beacons, compare client TTFB p75 to
  server p95 per platform. Record the result in the contract doc. If the gap
  exceeds 500 ms for most launches, write the evidence for an edge or CDN
  decision for the owner. There is no infrastructure change in this change.
  Verify: the recorded numbers.

## 5. Owner acceptance

- [ ] 5.1 Owner device QA on a real iPhone Home Screen PWA and a real Android
  phone. An edge swipe from word, list, Practice and Settings goes back one
  step with no white flash. Inbox shows rows, then the feed, or an error with
  a working retry. The Android dictionary returns to the same row. Record the
  result in the contract doc.
- [x] 5.2 Record the owner's decisions: root-tab drag (a or b); whether the
  practice boot overlay changes. Verify: decisions are recorded in design.md
  before 2.5 starts.

## 6. Permanent workflow

- [x] 6.1 The existing guard now covers Android and navigation:
  - `check_backend_pwa_performance_contract.py` requires an Android `*Test.kt`
    co-change and the swipe-back regression;
  - the workflow runs that regression on Chromium and WebKit;
  - `AGENTS.md` and the contract doc carry the rules.

  Verified by `tests.test_backend_pwa_performance_contract` and the checker
  with `--enforce-change-tests`. Merged in PR #346.

## Workflow follow-up

- Archive this change once groups 1–5 are complete and owner QA (5.1) is
  recorded.
