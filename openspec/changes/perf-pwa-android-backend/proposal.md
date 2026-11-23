# Proposal

## Why

`docs/PERFORMANCE_BACKEND_PWA_GOALS_REQUIREMENTS.md` asks for one coordinated
PWA + Android + Backend effort, measured before and after, with every future
feature meeting the same bar. The owner also reported navigation defects on the
learner PWA (double back on an edge swipe, a white or see-through frame on
dictionary swipe-back, unstable layers).

The existing contract, `docs/PERFORMANCE_PWA_PROGRESSIVE_LOADING.md`, covers
PWA section skeletons and Backend checks in depth. Three gaps remain open in it:

- no real-user or repeatable lab timing;
- no navigation rules;
- no Android coverage.

This change closes those gaps with the smallest set of evidence-backed packages.
It runs in the owner's order: PWA first, then Android, then Backend.

Authoritative sources, not restated here:
- the two documents above;
- `AGENTS.md` ("Permanent Backend / learner PWA performance contract");
- `NEXTATION.md` NXT-001;
- `ANDROID_CONTEXT.md`.

## What Changes

**Already solved (evidence in design.md, §Audit):**
- PWA section skeletons, independent loading and retry for Course, Practice,
  Voice, Rating, Friends and Profile.
- ETag revalidation of the course HTML.
- Immutable, service-worker-cached static assets.
- Gzip delivery and the course-map template cache.
- Dictionary virtual list.
- One edge swipe = one back step; an opaque dictionary detail page while it is
  dragged.
- Android dictionary scroll restore.
- Android cache-first Course and offline start.
- The CI guard extended to Android and navigation.

**Done in this change so far:** the repeatable PWA lab profile (task 1.1).

**To do, PWA first:**
1. Privacy-safe real-user timing through the existing `/api/v3/clientlog`
   diagnostics. No new telemetry stack.
2. Baselines and targets (one rule by action type, design decision 12) for
   the key learner actions, plus what each parser-blocking `<head>` resource
   costs the PWA launch and the Telegram SDK's cost in the PWA child pages
   (it is already removed from the PWA course route):
   - navigation;
   - login and onboarding;
   - lesson open, exercise advance and lesson finish;
   - session starts;
   - dictionary search;
   - swipe-back.
3. Inbox: a layout-faithful loading state and an in-place retry. Today the
   loading state is text only and an error has no retry.
4. Embedded layers (Dictionary, Phrases):
   - **Today:** the parent's "Yuklanmoqda…" cover hides the child's own
     skeleton until the full iframe load. The cover has no Back and no
     error, so a page that never loads stays on that text.
   - **Fix (owner rule: no loading text):** until the child paints, the
     parent shows the layer's title, Back and a skeleton matching the
     child's own skeleton. The child is revealed at its first paint. After
     20 s, an error with Retry uses existing reviewed copy.
5. Root-tab drag: a live peek of the back destination (owner choice a),
   behind a performance gate.
6. Panda only when a session start is slow (over 300 ms). The Test and
   Mistakes centres use skeletons. These are owner decisions; today the
   panda shows on every practice open and lesson entry, with a 720 ms
   minimum.
7. A back and scroll audit of the remaining layers, then the §7 condition
   matrix. During an active lesson, test exam or Mistakes review, the swipe
   does not drag and opens an exit confirmation (owner decision). The test
   and the review get new UZ/RU/TJ copy that promises no resume.
8. Launch (owner): the first frame stays the course skeleton until the
   course is ready. Parser-blocking resources the skeleton does not need,
   measured in 1.3, move off the PWA first-frame path. Cold launch target:
   ≤1500 ms to the skeleton on both lab engines.
9. Pull-to-refresh (owner): one exact distance arms it, a 🔄 ring spins
   until the data settles, and the refreshed regions show their skeletons in
   place instead of a full page reload. A changed HTML still reloads once,
   so new versions keep arriving.
10. Answers in a session (owner): the in-lesson personal review and the
    Mistakes review wait for the server on every answer today. They are
    graded on the device and recorded in the background, as lessons are.
    The server still re-grades every answer. The owner chose this for the
    Mistakes review too (a), accepting the same exposure as lessons.
11. Pro, trial and limit windows (owner): no loading text, one request
    instead of two, instant repeat opens, a skeleton cover for the checkout
    and trial layers, and no height jump.

**To do, Android (same initiative, same regression matrix):**
- Startup baseline and `reportFullyDrawn`, with memory and network bytes,
  for both flavours on Pixel_8 and the low-end emulator profile.
- Layout-matched loading for the two full-screen loaders: first-ever Course
  open and Ready Phrases.
- A back, scroll and action-state audit.
- Jank, ANR and duplicate requests from frame stats and vitals data.
- Tests for the three uncovered reliability flows: real process death, an
  account switch without a restart, and automatic reconnect.
- A mandatory low-end emulator profile, plus the owner's phone when
  provided.

**To do, Backend:**
- `lesson/complete`: the full-league leaderboard is computed twice inside the
  user's lock.
- The `lesson/start` p90 tail.
- The `pwa/profile` p99 spike.
- The network gap and launch payload sizes.
- The OpenAI fallback client has no timeout (SDK default 600 s). AI time to
  first useful response is unmeasured.
- The Inbox feed: since Smart reminders (#349), each Smart row reads its
  template with its own query. It is measured first and fixed only if it
  is slower.

**Unnecessary now, with evidence:**
- Redis, new queues, OpenTelemetry, CDN migration, SSR.
- A per-language i18n split and image format conversion.
- Removing desktop scripts from the PWA.
- Text web fonts (system fonts only).
- Extra backend replicas (no saturation evidence).

AI streaming is decided by the 4.5 measurement. Each item above is reopened
only by the evidence named in design.md.

## Capabilities

### New Capabilities
- `learner-back-navigation`: how learners return to the previous screen on PWA
  and Android. One gesture is one step, there is no blank or see-through frame,
  and the previous position is kept.
- `learner-loading-states`: what a learner sees while a screen, layer or
  section is loading, failing or retrying on PWA and Android. A real structure
  shows from the first frame, followed by an in-place settle and a local retry.
- `learner-performance-acceptance`: the measurable acceptance a learner-facing
  PWA, Android or Backend change must meet before it is called done. It also
  covers the real-user and lab measurements, and the gate that enforces them.

### Modified Capabilities
- (none: no existing spec under `openspec/specs/` covers learner navigation,
  loading or performance)

## Impact

**Platforms and paths:**
- **Learner PWA:**
  - `app/static/course-v3.html`, `app/static/hsk-lugat.html`,
    `app/static/hsk-gaplar.html`;
  - `app/static/course_v3_data/iphone-pwa-notices.js` (Inbox);
  - `app/static/course_v3_data/iphone-pwa-refresh.js` (pull-to-refresh);
  - `app/static/course_v3_data/iphone-pwa-inline-pro.js` and its bridge
    (limit and Pro sheet), `app/static/iphone-pwa-sw.js` (warm-up list);
  - the practice pages under `/iphone-pwa/practice/*`, especially
    `course_v3_test.html` and `course_v3_mistakes.html`;
  - `app/static/course_v3_data/iphone-pwa-practice-boot.js`;
  - `app/static/assets/characters/hsk-lesson-presentation.js` (PWA-only
    option; Telegram default unchanged).
- **Native Android, Play and direct:**
  - `feature/course`, `feature/practice/ReadyPhrasesScreen.kt`,
    `feature/dictionary`;
  - `MainActivity.kt` (first-drawn report);
  - new instrumentation tests for process death and account switch.
- **Backend:**
  - `/api/v3/lesson/complete`, `/api/v3/lesson/start`, `/api/v3/pwa/profile`;
  - `app/services/ai_provider.py` (fallback timeout);
  - `app/services/course_adaptive_lesson_service.py` and the Mistakes
    review start in `app/services/course_mistake_service.py` (answer keys
    for clients that grade locally);
  - `/api/v3/clientlog` (read only for real-user samples).

**Current evidence:** measured on 2026-11-22 against main `50231bee`; details
in design.md. On 2026-11-23 the plan was re-checked after syncing with main
`caaae35c` and PR #352. The launch path did not change; the trial colours,
NXT-011 monitoring and the Smart Inbox feed are reflected.
- Production server-side 7-day latency:
  - session p95 ≈43 ms;
  - course HTML p95 ≈93 ms;
  - map p95 ≈310–370 ms;
  - `lesson/start` p50 ≈62 ms, p90 ≈400 ms;
  - `lesson/complete` p50 ≈215 ms, p95 ≈490–670 ms;
  - `pwa/profile` p99 spike 3.4 s.
- PWA lab (task 1.1 harness, 390 px; slow 4G; 4× CPU on Chromium;
  production-like gzip and cache headers):
  - cold: FCP 1.24 s on Chromium and 2.18 s on WebKit; course ready
    3.6–3.7 s;
  - warm: FCP ≈0.3 s; course ready ≈0.7 s; 4.4 KB transferred.
- From one network, client-side TLS and TTFB to production were 1.2–2.5 s,
  against a server p95 of 39 ms. Real-user timing is needed to tell whether
  this is typical.

**Excluded:**
- desktop (frozen);
- the Telegram Mini App's own BackButton and loading semantics;
- lesson, grading, payment and entitlement logic;
- checkout design (owner keeps the current tokens);
- new infrastructure.

**Risks:**
- an edge-touch claim swallowing an edge control (exempted and tested);
- real-user timing adding log volume (sampled, one beacon per launch);
- Backend changes touching progress or XP atomicity (real-Postgres tests
  first);
- i18n and asset-token guards tripping on HTML edits (re-anchor procedure in
  memory and `AGENTS.md`).

**Rollback:** each package is its own commit and pull request. PWA HTML is
ETag-revalidated, so a revert takes effect on the next launch. Android ships
only with a release cut. Backend changes are reverted by a normal main
revert, with no migration.
