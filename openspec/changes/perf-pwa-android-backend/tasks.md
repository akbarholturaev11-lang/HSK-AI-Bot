# Tasks

Order: PWA → Android → Backend, as the owner asked. Android stays in the same
initiative and regression matrix.

Each package is its own pull request with its own tests. Every completion note
carries an "Analytics Impact:" and a "Monitoring Impact:" line. Every PWA HTML
edit re-anchors the i18n line counts and `reviewed_sha1` once, by exact line
identity.

## 1. PWA measurement baseline (no product code)

- [x] 1.1 Add `scripts/measure_pwa_lab.py`, built on the existing `ScreenPage`
  e2e fixture.
  - It serves the fixture over HTTP with production-like gzip, ETag and
    immutable headers, and fails if the first response lacks them.
  - It runs cold and warm, at 320, 390 and 430 px, on Chromium and WebKit,
    with slow 4G and 4× CPU, and prints JSON.
  - Document the command and the profile in
    `docs/PERFORMANCE_PWA_PROGRESSIVE_LOADING.md`.
  - Verify: the documented command runs as written, and two consecutive runs
    agree within 15% on FCP and course-ready.
  - Result (2026-11-22):
    - two full runs agreed within 7.5%;
    - the launch baseline is in the contract doc;
    - the network is shaped on the server, so both engines see the same
      network;
    - WebKit runs without a CPU slowdown, which Playwright cannot apply to it;
    - `tests/test_measure_pwa_lab.py` runs in the CI guard.
- [ ] 1.2 Extend the harness fixture, reusing the lesson and practice
  fixtures already in `tests/e2e/`, to drive:
  - a real lesson open, one exercise advance, and lesson finish → result;
  - the five real practice pages and the Voice live page, plus a Test exam
    start and a Mistakes review start;
  - the login and onboarding first paint.

  Verify: the harness reports, per action:
  - time to the first usable exercise, the next exercise and the result
    screen;
  - each practice page's first useful frame;
  - how long the parent entry is the only thing visible;
  - whether and how long the panda was visible.
- [ ] 1.3 Record the before baselines with 1.1 on both engines, and set a
  target per action from them. Record them in the contract doc, which closes
  its open items "every screen at 320/390/430", "filmstrip LCP/CLS/INP" and the
  Rating filmstrip.
  - Cold and warm launch, with the LCP element named per engine and the time
    until the Tabler icons are visible.
  - Login and onboarding first paint.
  - Tab switches.
  - First open of each layer: Dictionary, Phrases, five practice pages, the
    Voice live page, Inbox, Settings.
  - For every skeleton surface, the filmstrip of a warm (fast) open:
    - whether placeholder bars flash before content;
    - whether the shimmer runs as one synchronized sweep.

    A flash or competing waves becomes a fix inside the task that owns that
    surface (2.3, 2.8), or a new item with the filmstrip as evidence.
  - Dictionary search with hanzi, pinyin and a translation query, with the
    slowest event duration (INP proxy).
  - Swipe-back, from a layer and from a root tab.
  - Lesson open, exercise advance, and lesson finish → result.
  - Session starts: Test exam and Mistakes review.

  Verify:
  - the table lists both engines;
  - every action has a number or is marked "unmeasured" with the reason;
  - every action has a target derived from its baseline (§7; no universal
    400 ms).
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
- [ ] 2.4 Embedded-layer text status, only if 1.3 shows the parent
  "Yuklanmoqda…" for more than 300 ms when the layer is warm-opened on WebKit.
  - It covers Dictionary, Phrases, and the Test and Mistakes hubs after 2.8.
  - Delay the text with an anti-flash window, so a fast frame paints its own
    skeleton first.

  Verify:
  - lab before/after for Phrases and the hubs;
  - `test_pwa_swipe_back.py` still passes.

  If the threshold is not crossed, record "not needed" with the numbers.
- [ ] 2.5 Root-tab live peek, per design decision 6 (owner choice a).
  - At drag start, the back destination is shown as a fixed, inert underlay
    at its `App.show` scroll position.
  - The dragged tab is opaque.
  - Release lands through `goBack()`; cancel restores the tab.
  - Reduced motion: no follow, and the edge swipe still goes back one step.

  Verify:
  - `test_pwa_swipe_back.py` gains root-tab cases on Chromium and WebKit:
    - mid-drag, the uncovered strip shows the destination's painted content
      (never empty paper), for Course and for a tab-to-tab history;
    - release is one history step, and the destination anchor is within
      8 px of its underlay position at 320, 390 and 430 px;
    - cancel leaves `SCREEN` and history unchanged;
    - under reduced motion there is no underlay, and it is one step back.
  - The performance gate on Chromium with 4× CPU: no long task over 50 ms
    at drag start, and drag frames at p95 ≤ 16.7 ms. If it fails, stop and
    report to the owner (decision 6).
  - An iOS Simulator recording at 390 px.
- [ ] 2.6 Back and scroll audit, one layer at a time:
  - Settings, Friends, Inbox and checkout;
  - lesson dialogs, the writer overlay and the five practice pages.
  - During an active lesson, test or Mistakes review, edge swipe must **not
    drag the screen**; a completed back gesture opens the existing exit
    confirmation flow instead. Cancel keeps the same question; confirmed exit
    follows existing save rules (no false resume promise). Other screens retain
    their swipe behavior. Cover this in iPhone WebKit regression tests.

  Outside those active sessions, each layer must close in one step by edge
  swipe, browser back and Telegram BackButton, with no blank frame and the
  previous scroll kept. Fix only the defects found, adding each layer to
  `test_pwa_swipe_back.py`. Verify: Chromium and WebKit pass, and the swipe
  test's checker entry is unchanged.
- [ ] 2.7 Lesson open, exercise advance and lesson finish → result.
  - If 1.3 shows one misses its target, trace it in Chromium and WebKit and
    fix only the top cause.
  - For finish → result, the only allowed change is the save state: the
    existing button's pending state while `lesson/complete` runs. No
    optimistic XP, rank or streak.
  - Lesson grading, progress and payment code are not changed.

  Verify: lab before/after, and the existing lesson e2e and unit suites pass
  (`test_lesson_streak_celebration.py`, `test_pwa_learning_parity.py`).
  Otherwise record "meets target".

- [ ] 2.8 Panda only for a slow session start; skeletons for the hubs (design
  decision 9).
  - **Session starts:**
    - Lesson entry, Recognition, Pronunciation and Memorize on open, Test
      `openExam(...)`, Mistakes `startReview(...)`, and in-frame restarts.
    - They show the panda only if preparation passes 300 ms. Once shown, it
      stays at least 300 ms.
    - It is passed as a PWA-only option to `beginLessonEntry` and to the
      practice boot. The 720 ms lesson minimum stays for Telegram only.
  - **Hubs:**
    - Test centre (`#ex-list`) and Mistakes centre (`#content`) get
      layout-faithful skeletons in the child page, under
      `html.hsk-pwa-practice` only.
    - The boot reveals the frame at the child's first paint.
    - The Mistakes spinner and text become row placeholders on first load and
      on category change.
  - **Errors:** the 20 s boot fallback gains Retry, using
    `practiceGateError.retry`.

  Verify, on Chromium and WebKit:
  - a held request past 300 ms shows the panda, and a request answered
    within 300 ms opens the session with no panda frame;
  - the hubs open with a skeleton and never show the panda;
  - the parent entry and the child loader are never visible together;
  - the boot fallback's Retry reloads and recovers;
  - the hubs pass the 320/390/430 geometry check (≤8 px);
  - reduced motion uses the same timing with no animation;
  - Telegram is unchanged: `test_miniapp_smoke.py` passes, and a Telegram
    lesson entry still shows the panda;
  - the i18n guard passes, and the lab before/after from 1.2 is recorded.

- [ ] 2.9 PWA condition matrix (design.md, §7).
  - For every PWA cell marked ✔, run the named test once on this branch and
    record it.
  - For every PWA cell pointing at a task, confirm that task's verification
    covers it.
  - No new test is added outside 2.3, 2.5 and 2.8.

  Verify: the matrix in the contract doc shows each PWA cell with a test
  name or the task that owns it.

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
  - In the same runs, record:
    - memory after Course is drawn (`dumpsys meminfo`, PSS);
    - network bytes and request count for one Course open, from the OkHttp
      event log on a debug build of each flavour.

    Two identical requests for the same resource in one open count as a
    duplicate repository request. That is a defect for 3.5.
  - The emulator also runs with a slow-network profile
    (`-netspeed`/`-netdelay`) matching the PWA lab.
  - Add a baseline profile only if the cold median exceeds warm by more than
    40% and a trace shows JIT or class loading dominating.

  Verify: a test asserts the report fires once; the before/after numbers are
  recorded in `ANDROID_CONTEXT.md`. If the owner's weak device is not
  available, its rows are marked "unmeasured".
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
  behaviour.

  Loading criteria in the same pass:
  - **Profile:** its compact inline loader must sit inside the final section
    bounds. The header and the first section move by ≤8 dp when data lands.
  - **Lesson, Voice, Assistant:** an action spinner stays inside its button
    or row. The screen stays usable while it runs, and a failed action
    leaves an error with retry in the same place, not a full-screen block.

  Verify: the new tests pass on the direct flavour.
- [ ] 3.5 Jank, ANR and duplicate requests.
  - Record frame stats (`adb shell dumpsys gfxinfo`) for Course and Dictionary
    scrolling on Pixel_8 and the owner's weak device.
  - Read the owner's Play Console vitals export.
  - Fix only the top offenders and any duplicate request found in 3.2, each
    with a regression test.

  Verify: before/after frame stats are recorded in `ANDROID_CONTEXT.md`.
- [ ] 3.6 Reliability flows (design decision 11).
  - Record the mapping from each §4 flow to its existing test.
  - Add two tests:
    - **Process death:** `ActivityScenario.recreate()` on Course and in a
      lesson keeps the screen and the lesson position.
    - **Account switch without a restart:** signing out and signing in as
      another account never shows the first account's cached course,
      profile or rating.
  - Fix only what those tests find.

  Verify: the tests pass on the direct flavour, `testPlayDebugUnitTest`
  passes, and the mapping is recorded in `ANDROID_CONTEXT.md`.

## 4. Backend (after group 3)

- [ ] 4.1 `POST /api/v3/lesson/complete`.
  - In a real-Postgres test, record the statement count and the time of each
    step: rank before, award, rank after, analytics, mistakes.
  - If the leaderboard dominates, replace both calls with one bounded query
    that returns the user's rank and the neighbour rows. A snapshot test
    asserts identical rank, rank-up flag and neighbour rows for leagues of 1,
    5 and 500 users with ties.
  - Check the new query's `EXPLAIN ANALYZE` on real Postgres before adding
    any index. Add an index only if the plan shows a sequential scan that
    matters at 500 users.
  - Progress, XP and streak stay in one transaction.

  Verify:
  - the query-count test before and after;
  - these pass:
    - `tests.test_course_map_template_cache` and
      `tests.test_course_today_service`;
    - `tests.test_miniapp_lesson_rank_up` and
      `tests.test_miniapp_course_context`;
    - `tests.test_pwa_learning_parity` and
      `tests.test_android_foundation_api`;
    - `tests.test_analytics_platform_chain`;
    - Android `CourseRepositoryTest`.

    `test_miniapp_lesson_rank_up` has a known failure on main
    (2026-11-22), so compare it with main and do not count it as a new
    failure.
  - production p50/p95 after deploy.
- [ ] 4.2 `POST /api/v3/lesson/start` p90 ≈400 ms against p50 ≈62 ms. Find the
  slow mode (content load, cache miss or lock) from `railway logs --http` and a
  cold/warm timing test. Fix only if the cause is in the app. Verify:
  production p90 after deploy, or a recorded external cause.
- [ ] 4.3 `GET /api/v3/pwa/profile` p99 spike of 3.4 s. Find the slow call in
  the HTTP logs. Fix it, or record that the cause is external. Verify: the
  existing profile tests pass, and production p99 after deploy.
- [ ] 4.4 Network gap and payload sizes.
  - With 7 days of 1.4 beacons, compare client TTFB p75 to server p95 per
    platform.
  - Record the gzip size of the launch-path API responses: session, course
    map and profile.
  - A response over 20% of the cold launch bytes becomes a follow-up with
    evidence.
  - If the network gap exceeds 500 ms for most launches, write the evidence
    for an edge or CDN decision for the owner.
  - There is no infrastructure change in this change.

  Verify: the numbers are recorded in the contract doc.
- [ ] 4.5 External calls and AI responsiveness (design decision 10).
  - From `railway logs --http`, record p50/p95 for the learner AI endpoints
    and the fallback-path share.
  - Give the OpenAI fallback client an explicit timeout and retry count, set
    from the primary client's settings, with a unit test on the configured
    values.
  - Confirm that the other external calls on learner paths keep their
    explicit bounds: TTS, push, identity and currency (design.md list).
  - Record the time to first useful response. If it is the user's main wait
    and the provider supports it, write the streaming evidence for the
    owner; nothing is built speculatively.

  Verify:
  - the unit test;
  - the existing AI service tests pass;
  - the numbers are recorded in the contract doc.

## 5. Owner acceptance

- [ ] 5.1 Owner device QA on a real iPhone Home Screen PWA and a real Android
  phone. An edge swipe from word, list, Practice and Settings goes back one
  step with no white flash. Dragging back from a root tab shows the
  destination underneath and lands without a jump. A fast lesson or practice
  start opens with no panda, and a slow one shows the panda. The Test and
  Mistakes centres open with skeletons. Inbox shows rows, then the feed, or an
  error with a working retry. The Android dictionary returns to the same row.
  Record the result in the contract doc.
- [x] 5.2 Record the owner's decisions in design.md before 2.5 starts:
  - root-tab drag (a);
  - panda only at a session start, with skeletons for the hubs;
  - the panda only when preparation takes over about 300 ms.

  Verify: the decisions are recorded in design.md.

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
