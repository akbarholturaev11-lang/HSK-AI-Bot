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
  - For the cold launch, what each parser-blocking `<head>` resource costs
    the first frame: the Telegram SDK, the four character scripts and the
    stylesheets (design decision 13). With a held map request, the
    filmstrip from the first paint to course ready must show the shell
    skeleton, never a blank or "…" frame.
  - Today's pull-to-refresh on Course, Rating and Profile: release to the
    first new frame, and release to settled content (the before numbers for
    2.10).
  - Answer tap to feedback in the in-lesson personal review and in the
    Mistakes review, with the server held (the before numbers for 2.11).
  - The limit and Pro sheet, first and repeat open: tap to its first frame,
    and tap to plans with an active pay button. The checkout and trial
    layers: tap to the child's first paint (the before numbers for 2.12).
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
  - For Dictionary and Phrases: when the child first paints, whether that
    first paint shows content, a skeleton or an empty list, and when the
    parent cover is removed.
  - The main-thread time of `telegram-web-app.js` before FCP, cold and warm.
    If it exceeds 50 ms on Chromium 4×, that is evidence for a follow-up to
    defer it on the PWA path; nothing is changed in 1.3.
  - The console and page errors per action.

  Verify:
  - the table lists both engines;
  - every action has a number or is marked "unmeasured" with the reason;
  - every action has a target set by the rule in design decision 12;
  - the error count per action is recorded as the baseline for "no new
    error".
- [ ] 1.4 Real-user launch timing (PWA only) through the existing `clog()`
  beacon to `/api/v3/clientlog`.
  - One beacon per launch after the course is ready.
  - Fields: navigation timing, FCP, LCP, CLS, the slowest event duration,
    course-ready time, cold/warm, 200/304, viewport class, standalone or
    browser.
  - No account, text or token. No retry.
  - It fits the endpoint's limits: at most 14 context keys, each value at
    most 220 characters. The keys are named in the contract doc.

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
  feed is pending. On an error, keep the existing error text and add an
  in-place retry labelled `courseLoadError.btn` (reviewed UZ/RU/TJ; no new
  copy). Owner-switch checks stay unchanged.
  Verify:
  - a held-request test in `tests/test_pwa_notices_ui.js` covers
    pending → rows, fail → error → retry → ready, and an owner switch;
  - a Chromium/WebKit geometry check at 320, 390 and 430 px shows ≤8 px;
  - the i18n guard passes;
  - lab Inbox open before/after from 1.1.
- [ ] 2.4 Embedded layers (Dictionary, Phrases): a matching skeleton, never a
  loading text, with Back and Retry (design decision 5, owner rule; PWA path
  only).
  - Before the child paints, the parent cover shows the real title, a working
    Back icon and, after 150 ms, bars shaped like the child's first viewport.
    It shows no "Yuklanmoqda…" or other loading text.
  - Each parent skeleton is drawn from a small table of the child's own
    measurements.
  - `hsk-lugat.html` gains static row placeholders in `#list` under
    `html.hsk-pwa-browser`, so its first paint is the same skeleton.
    Phrases keeps its `.phrase-skeleton`.
  - `hsk-lugat.html` and `hsk-gaplar.html` signal their first paint to the
    parent. The parent removes its skeleton then, with `load` as the
    fallback.
  - After 20 s without the signal, the skeleton gives way to
    `courseLoadError.body` with Retry and Back. Retry reloads the frame.
  - The Test and Mistakes hubs use the same cover through the practice boot
    (2.8).

  Verify, on Chromium and WebKit:
  - no frame of any open shows a loading text, fast, held or failing;
  - a held child page shows the title, Back and the skeleton bars, and Back
    works;
  - the parent and child skeletons agree within 2 px for the header and the
    first three rows at 320, 390 and 430 px;
  - a fast child page shows no skeleton-bar flash;
  - a never-loading page shows the error after 20 s, and Retry recovers;
  - `test_pwa_swipe_back.py` still passes, the i18n guard passes, and the
    lab before/after from 1.3 is recorded;
  - Telegram is unchanged (`test_miniapp_smoke.py`).
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
    - **Lesson:** the existing "Darsdan chiqasizmi?" sheet. Verify that the
      promised resume holds on both paths (`saveLessonResume()` and
      `Foundation.pause()`).
    - **Test exam and Mistakes review (owner choice a):**
      - a confirmation sheet in each page's own style, with the copy in
        design.md (approved by the owner on 2026-11-22);
      - their ✕, the swipe and browser back all open it;
      - PWA only (`html.hsk-pwa-practice`); Telegram is unchanged.
    - **Tests** (WebKit and Chromium) for the lesson, the test exam and the
      Mistakes review:
      - during the gesture the session screen's transform stays 0;
      - after release the sheet is open and the question index is unchanged;
      - cancel returns to the same question with the same answers so far;
      - a confirmed exit leaves through the existing path (`confirmExitFlow`,
        `exitExam`, `closeReview`), with one history step;
      - outside a session (the hub, a list), the swipe still drags as today;
      - Telegram: `test_miniapp_smoke.py` passes, and the test page's ✕
        still exits at once there.

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
    - Until then, the parent entry is the decision-5 skeleton (title, Back,
      exam-card or target-row bars), with no loading text and no panda.
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

- [ ] 2.9 Launch: a shorter path to the first frame (design decision 13).
  - Move off the PWA first-frame path only the `<head>` resources that 1.3
    shows cost at least 100 ms of the cold first frame and the shell does
    not need. The character scripts are the first candidates.
  - Before a move, show that none of the resource's call sites run before
    it arrives.
  - On the PWA route the resource loads after the first paint. Telegram
    keeps today's order.
  - If 1.3 shows no such resource, record that and close the task without a
    code change.

  Verify, on Chromium and WebKit:
  - a held map request shows the shell skeleton from the first paint until
    course ready, with no blank or "…" frame;
  - cold time to the shell ≤1500 ms on both engines, or the owner-approved
    exception is recorded; a warm launch is within 10% of its baseline;
  - the lesson entry and the five practice starts still work (the 1.2
    flows);
  - Telegram is unchanged (`test_miniapp_smoke.py`), and the lab
    before/after is recorded.
- [ ] 2.10 Pull-to-refresh: a spinning ring, region skeletons and one exact
  threshold (design decision 14), in `iphone-pwa-refresh.js` and the tabs'
  existing loaders.
  - The threshold is one constant: 140 px of finger travel. The arc fills
    with the distance, closes and takes the accent colour at exactly the
    threshold, and un-arms if pulled back short of it.
  - A release short of the threshold springs back with no request.
  - A release past it keeps the ring spinning until every refreshed region
    settles, for at least 600 ms.
  - Refreshed regions show their existing placeholders in place:
    - Course: the initial shell body;
    - Rating: the active sub-tab's skeleton;
    - Profile: the rings and the map-driven sections.

    The header, bell, settings and nav stay real.
  - Failure or timeout restores the previous content, with one
    `courseLoadError.body` toast.
  - The `Last-Modified` check reloads the page when the HTML is newer.
  - Another pull while busy is ignored. Reduced motion: no spin.

  Verify, on Chromium and WebKit, with held and failing requests:
  - a pull to 139 px does nothing, and a pull to 140 px arms;
  - after release, the ring spins and each tab's regions show skeletons
    within one frame, then settle with anchors moving ≤8 px;
  - a failure puts the old content back and shows the toast;
  - the tab stays at the top after the refresh;
  - a newer fixture HTML date causes exactly one reload, and an equal one
    none;
  - no refresh starts over a flow, sheet, paywall or layer;
  - release to first skeleton frame ≤200 ms, and release to settled content
    within the 1.3 baseline;
  - the i18n guard passes.
- [ ] 2.11 Answers graded on the device in the in-lesson personal review and
  the Mistakes review (design decision 15). Ships after the owner answers
  open question 1; with (b), only the personal review changes.
  - **Server:** when the request declares local grading, the adaptive plan
    and the review start responses carry each question's key. Older
    clients get today's shape. Recording, re-grading, "first answer is
    final" and all learning-state and XP rules stay unchanged.
  - **PWA (`course-v3.html` overlay, `course_v3_mistakes.html`):**
    - grade with the server's exact rule and show feedback at once;
    - post the answer in the background;
    - personal review: a failure goes into the existing outbox, flushed at
      the next plan load and after `lesson/complete` settles;
    - Mistakes review: answers are queued in order, and `review/complete`
      waits for them, keeping its existing error with retry.
  - Telegram keeps server grading.

  Verify:
  - a parity test grades every `mistake_drill_factory` format on the
    server and on the client and gets the same verdict;
  - on Chromium and WebKit with the answer request held, feedback appears
    within one frame (≤200 ms) and the lesson or review continues;
  - with the request failing, the personal review continues and the answer
    reaches the server on the next flush, and the review completes once the
    queue is committed;
  - real-Postgres tests show unchanged mistake-target, box, XP and
    duplicate-answer results;
  - an old client request without the field gets no key;
  - the analytics and monitoring checker and the Mini App smoke tests pass.
- [ ] 2.12 Pro, trial and limit windows (design decision 16; PWA only).
  - Sheet: no loading text; as many skeleton plans as the server last
    returned; the course page's actor is reused; a repeat open shows the
    remembered overview at once, and the pay button waits for the fresh
    one.
  - At the start of a preview lesson, the overview is fetched in the
    background with `inline_preview`.
  - Checkout and trial layers: the decision-5 skeleton cover, reveal at the
    child's first paint, a 20 s error with Retry and close.
  - The trial page joins the service worker's `WARM_PAGES`.

  Verify, on Chromium and WebKit:
  - no frame of the sheet shows a loading text;
  - the first open makes one request, not two, and an owner switch still
    closes the sheet;
  - a repeat open shows the plans within one frame, the pay button is
    disabled until the fresh answer, and a changed price updates in place;
  - the skeleton-to-plans swap and the layer handoff move anchors ≤8 px at
    320, 390 and 430 px;
  - a preview-lesson prefetch records no analytics entry;
  - payment start, return, polling and the exit offer behave as before (the
    existing checkout tests pass), and the i18n guard passes;
  - the lab before/after from 1.3 is recorded.
- [ ] 2.13 PWA condition matrix (design.md, §7). It runs last in group 2.
  - For every PWA cell marked ✔, run the named test once on this branch and
    record it.
  - For every PWA cell pointing at a task, confirm that task's verification
    covers it.
  - No new test is added outside 2.3, 2.4, 2.5, 2.6, 2.8, 2.9,
    2.10, 2.11 and 2.12.

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
  - Measure cold and warm start for the play and direct release builds with
    `adb shell am start -W`: 10 runs, median `TotalTime` and fully-drawn
    time. Run on:
    - Pixel_8;
    - the mandatory low-end emulator profile (design decision 11: API 36
      image, 2 GB RAM, 2 cores);
    - the owner's real low-end phone, if the owner provides one.
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
  recorded in `ANDROID_CONTEXT.md` for Pixel_8 and the low-end profile. The
  owner's phone rows are filled in if one was provided; otherwise they are
  marked "not provided".
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
    scrolling on Pixel_8 and the low-end profile.
  - Read ANR and crash data:
    - from the owner's Play Console vitals export when provided;
    - otherwise from the app's own exit-reason diagnostics in production
      logs (`reportExitReasons()`, API 30+).
  - Fix only the top offenders and any duplicate request found in 3.2, each
    with a regression test.

  Verify: before/after frame stats are recorded in `ANDROID_CONTEXT.md`.
- [ ] 3.6 Reliability flows (design decision 11).
  - Record the mapping from each §4 flow to its existing test.
  - Add three tests:
    - **Real process death:** on Course and in a lesson, do Home, then
      `am kill`, then relaunch (UiAutomator). The app restores the screen and
      the lesson position, or returns to Course with progress intact. It
      never shows a blank screen or crashes.
    - **Account switch without a restart:** signing out and signing in as
      another account never shows the first account's cached course,
      profile or rating.
    - **Automatic reconnect:** with the network off, then on, the offline
      state clears without a tap.
  - Rotation is recorded as not applicable (`configChanges`; design
    decision 11).
  - Fix only what those tests find.

  Verify: the tests pass on the direct flavour, `testPlayDebugUnitTest`
  passes, and the mapping is recorded in `ANDROID_CONTEXT.md`.
- [ ] 3.7 Android: the same rules as 2.11 and 2.12 (design decisions 15
  and 16).
  - `LessonAdaptiveReview` and the Mistakes review screens grade with the
    key and record in the background, using the existing in-memory outbox.
  - The native Pro, trial and limit screens show their structure at once,
    with no loading text, and no blank screen while data loads.

  Verify: unit tests for the grading parity and the background recording,
  an instrumentation test with a held answer request (feedback without
  waiting), and the 1.3-style before/after on Pixel_8 and the low-end
  profile.

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
  - If the p50 gap between client TTFB and server time exceeds 500 ms,
    write the evidence for an edge or CDN decision for the owner.
  - There is no infrastructure change in this change.

  Verify: the numbers are recorded in the contract doc.
- [ ] 4.5 External calls and AI responsiveness (design decision 10).
  - From `railway logs --http`, record p50/p95 for the learner AI endpoints
    named in design decision 10 (voice message, pronounce, Android
    assistant messages, live-socket connect), and the fallback-path share.
  - Check that no learner path holds a row lock or an open transaction
    while it waits on AI or TTS. Fix any violation with a test.
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
  Mistakes centres open with skeletons. During a lesson, a test or a Mistakes
  review, a swipe does not drag and asks for confirmation first. Inbox shows
  rows, then the feed, or an
  error with a working retry. Dictionary and Phrases never show a loading
  text, only their skeleton. A launch on a slow network shows the skeleton
  until the course is ready. Pull-to-refresh arms at a clear point, the ring
  spins and the regions show skeletons until the new content lands. On a
  slow network, personal review and Mistakes review answers show right or
  wrong at once, and the Pro, trial and limit windows open at once. The
  Android dictionary returns to the same row.
  Record the result in the contract doc.
- [x] 5.2 Record the owner's decisions in design.md before 2.5 starts:
  - root-tab drag (a);
  - panda only at a session start, with skeletons for the hubs;
  - the panda only when preparation takes over about 300 ms;
  - in an active session, a swipe does not drag and asks for confirmation;
  - the Test exam and the Mistakes review also get a confirmation (a);
  - no loading text on Dictionary and Phrases, a skeleton instead;
  - a fast launch, with the skeleton when it is slow;
  - pull-to-refresh with a spinning ring, region skeletons and one exact
    threshold;
  - answers in a learning session graded on the device and recorded later;
  - fast, smooth Pro, trial and limit windows.

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
