# Design

## Context

See proposal.md (Why) for motivation and the specs for requirements.

- **PWA back.** `NavBack` in `app/static/course-v3.html` is the single back
  path. It has a layer list, an in-page edge drag (start/move/end), a popstate
  handler with one history guard entry, and the Telegram BackButton. The
  dictionary is a same-origin iframe inside `#resourceov`; `RESOURCE` forwards
  its touches to `NavBack` and exposes its detail page as a nested drag target.
- **Root cause of the double back.**
  - In the browser PWA, a swipe near the left edge started both the in-page
    drag and the browser's own history swipe.
  - The in-page drag called `goBack()` 200 ms after release.
  - The browser's popstate called `goBack()` again, so the app went back two
    levels.
  - iPhone also painted its blank history snapshot during the native swipe.
  - The detail page had no background of its own, so list rows showed through
    it while it was dragged.
  - The drag reset its transform before closing, so the page flashed back at
    x=0 for a frame.
- **Android.** Screens are swapped by `if/else` in `MainActivity.kt` (no
  NavHost). `DictionaryList` created its `LazyListState` inside the branch that
  leaves composition when a word opens, so the scroll was lost on return.
- **Backend.** Production metrics (Railway, 7 days) show that session, course
  HTML and map are fast. The slowest common learner write is
  `lesson/complete`.

## Goals / Non-Goals

**Goals:**
- Fix the reported navigation defects at their root, with tests that fail on
  the old code.
- Schedule only measured work, in independently verifiable packages.
- Make the existing CI guard enforce the bar for Android and navigation.

**Non-Goals:**
- A new navigation framework.
- NavHost migration on Android.
- New infrastructure (Redis, queues, telemetry stack).
- Desktop.
- Changing Telegram Mini App back semantics.

## Decisions

1. **Claim the edge touch instead of only deduplicating popstate.**
   - The fix calls `preventDefault()` on a non-passive `touchstart` within
     16 px of the left edge, browser PWA only (`PWA_COURSE_HOST`). This stops
     the native history swipe, verified in iOS Simulator Safari.
   - That removes both the second step and the blank snapshot.
   - Deduplication alone would still show the blank snapshot.
   - Buttons, links and inputs inside the strip are exempt, so their taps
     still work.
   - Telegram's in-app path is untouched because it never takes this branch.
2. **Keep a one-gesture token as defence in depth.**
   - A completed drag stores `{handled, until: now + 800 ms}`.
   - Whichever comes first, the drag timeout or a popstate, performs the
     single `goBack()`. The other only re-syncs the history guard.
   - This covers browsers that still deliver popstate.
   - The code keeps exactly four `goBack()` call sites, already asserted by
     `tests/test_course_v3_static_data.py`.
3. **Close before resetting the transform**, and ignore a new drag while the
   previous one is still settling. Otherwise the second drag grabs the layer
   that is still closing.
4. **Paint the dragged page, not the parent.** The dictionary detail gets its
   own opaque background and the existing scene art, as CSS on the drag
   classes in `hsk-lugat.html`, so no JS is needed. Using the shared versioned
   asset URL means no new cache entry.
5. **Android: hoist state, don't add a saver.** The `LazyListState` moves up
   to `DictionaryScreen`, which outlives the list and detail branches. That is
   simpler than `rememberSaveable` and enough, because the ViewModel already
   keeps query and filters.
6. **Extend the existing guard rather than adding a new one.**
   - `scripts/check_backend_pwa_performance_contract.py` gains an Android rule
     (main-set `*.kt` needs a changed `test`/`androidTest` `*Test.kt`).
   - It also gains a required-file entry for `tests/e2e/test_pwa_swipe_back.py`.
   - The workflow runs that test on Chromium and WebKit.
   - Android instrumentation stays local (direct flavour), because CI only
     runs the JVM suite.
7. **Root-tab swipe peek is not fixed by guesswork.**
   - Dragging Practice back to Course shows empty paper, because tab screens
     are swapped with `display`.
   - A live peek needs the course scroll, sticky header and trail art painted
     underneath.
   - That is a visual decision for the owner: live peek, or no drag on root
     tabs. It is task 1.3.

## Risks / Trade-offs

- [Edge claim blocks a native gesture someone relies on] → Only the 16 px strip
  in the browser PWA, where the app already owns back; covered by
  `test_edge_claim_spares_controls_and_inner_touches`.
- [The 800 ms window swallows a deliberate hardware back right after a swipe]
  → The window starts only after a completed drag; a second back within 0.8 s
  is rare and harmless.
- [The Android rule makes small Kotlin refactors heavier] → Same strictness the
  PWA rule has had; build scripts, resources and docs are exempt.
- [Backend changes touching progress/XP atomicity] → Each backend task first
  records SQL counts in a real-Postgres test and moves only non-critical side
  effects after commit.

## Migration Plan

- No data migration.
- Deploy is a normal main merge.
- Rollback: revert the commit. The HTML is network-first (not cached by the
  service worker), so a revert takes effect on the next page load.
- Android ships with the next release cut per `ANDROID_RELEASE_CHECKLIST.md`.
