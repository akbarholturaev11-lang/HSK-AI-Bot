# Design

## Context

See proposal.md (Why) for motivation, and the three specs for the
requirements. The audit was run on main `50231bee` on 2026-11-22.

### How the code is shaped today

- **PWA back.**
  - `NavBack` in `app/static/course-v3.html` is the single back path. It has a
    layer list, an in-page edge drag, one history guard and the Telegram
    BackButton.
  - Embedded pages (dictionary, phrases, practice) are same-origin iframes
    created by `RESOURCE.ensure()`.
  - Until the iframe's `load` event, the parent shows a centred text status
    ("Yuklanmoqda…").
  - In the PWA, iframes are created on open. Telegram pre-warms them
    (`RESOURCE.warm()` runs only when `!PWA_COURSE_HOST`).
- **PWA delivery.**
  - The course HTML (843 KB raw, 238 KB gzip) is served `private, no-cache`
    with an ETag. A warm launch is a 304 (verified in production), but every
    deploy changes the ETag, so the next launch downloads it in full.
  - Versioned `?v=` assets are `immutable` and service-worker cache-first.
  - The service worker warms the dependencies of the embedded pages after the
    course is idle.
- **PWA root tabs.**
  - Course, Practice, Voice, Rating and Profile are `.scr` screens swapped by
    `display`; all of them use the one document scroll.
  - Back from a root tab returns to `SCREEN_HISTORY.pop()`, or Course when the
    history is empty, so the destination is not always Course.
  - `App.show` re-centres Course on the current lesson (the node sits at 42%
    of the viewport height, after `drawTrails()`). Other tabs scroll to 0.
  - Today the drag only moves the current tab. After release the destination
    slides in from `translateX(-22%)`. The code comment says a live peek was
    avoided because two visible tabs would break the document scroll.
- **PWA panda preparing screens.**
  - Practice pages open in an iframe that stays hidden until the child says
    it is ready (`revealPracticeFrame`). Until then the parent entry shows
    the panda (`renderStudyPreparing()`), so only one panda is visible at a
    time.
  - `iphone-pwa-practice-boot.js` keeps its own panda overlay inside the
    frame. It becomes visible only when a session starts after the frame is
    shown: Test `openExam(...)` and Mistakes `startReview(...)`. A 20 s
    fallback shows an error with Back only.
  - Recognition, Pronunciation and Memorize start a session on open
    (`gateStart`), and their gate error already offers retry.
  - Test and Mistakes open on a hub. `#ex-list` and `#content` start empty
    behind the panda. Mistakes then shows a spinner with "Yuklanmoqda…".
  - Lesson entry (`HSKLessonPresentation.beginLessonEntry`) shows the panda
    at once and keeps it **at least 720 ms** (120 ms under reduced motion),
    then fades for 430 ms. It also waits up to 1.8 s for the first card's
    sound.
- **Android.**
  - Screens are swapped by `if/else` in `MainActivity.kt` (no NavHost).
  - The course map is cache-first.
  - `HskSkeleton` exists and is used by Rating and Dictionary.
  - There is no `reportFullyDrawn` and no baseline profile.
  - The shared OkHttp client has 15 s connect, 30 s read and write, and a
    call timeout, with no silent retry (`HskAiApplication.kt`). Live voice has
    its own client.
  - Reliability flows already tested: `OfflineModeTest`, `DeepLinkRouterTest`,
    `AuthRepositoryOauthTest`, `ExternalAuthLaunchTest`,
    `MandatoryUpdateStatesTest`, `PlayUpdateMigrationTest`, and logout cache
    clearing in `CourseRepositoryTest`. No test covers process death and
    restore, or switching accounts without a restart.
- **Backend external calls.**
  - Gemini (primary AI) uses `AI_PRIMARY_TIMEOUT_SECONDS`. The OpenAI fallback
    client is built with no timeout, so the SDK default applies (600 s, 2
    retries) (`app/services/ai_provider.py`).
  - TTS has bounded timeouts (9 s, 35 s with 5 s connect, 5 s). Push, currency
    and OIDC calls use 5–6 s.
  - No learner endpoint streams AI output today.
- **Backend.**
  - `_v3_complete_lesson_for_canonical_actor` (`app/main.py`) calls
    `gamification.leaderboard(user)` twice per completion. The first call
    gets the rank before XP; the second gets the rank and the neighbour rows
    after it.
  - Each call aggregates the whole league's weekly XP and returns every row.
    Both run inside the transaction that holds the user's row.
  - Analytics and mistake writes are also synchronous before commit.
- **Diagnostics.**
  - `POST /api/v3/clientlog` accepts an event, a message and up to 14 context
    keys, and writes one log line.
  - `clog()` in the course page already sends to it via `sendBeacon`.
  - No navigation or paint timing is reported today.

### Measurements (2026-11-22)

**Lab conditions:**
- 390 px viewport, slow 4G (150 ms, 1.6 Mbps), 4× CPU, Chromium;
- e2e fixtures over HTTP, with gzip, ETag and immutable headers that mirror
  production.

| Flow | Result |
|---|---|
| Cold course launch (1.1 harness, 390 px, median of 6) | Chromium FCP 1238 ms, LCP 3790 ms, course ready 3578 ms; WebKit FCP 2178 ms, course ready 3658 ms. 608–647 KB. Largest: course HTML 238, `hsk-course-i18n.js` 59, `hsk-miniapp-i18n.js` 38, `tabler-icons.min.css` 32, `desktop-download.js` 23, logo PNG 21 KB |
| Warm course launch (1.1 harness, 390 px) | Chromium FCP 296 ms, course ready 686 ms; WebKit 260 / 682 ms; 4.4 KB transferred (HTML 304) |
| Tab switch (action → ready) | Practice 212, Voice 133, Profile 211–278, Course 232 ms. Practice first visit has one 0.008 shift; others have none |
| Dictionary layer | Rows painted by 150 ms; search "xue" 15 ms, "学习" 84 ms. A translation query was not measured reliably (harness timeout) |
| Phrases layer | Parent text status at 150 ms, its own row skeleton by 400 ms, categories by 800 ms |
| Practice pages, lesson open, exercise advance | Not measured: the fixture serves stub practice pages and has no `lesson/start` |
| Production server (Railway, 7 days) | session p95 ≈43 ms; course HTML p95 ≈93 ms; map p95 ≈310–370 ms; `lesson/start` p50 ≈62 ms, p90 ≈400 ms; `lesson/complete` p50 ≈215 ms, p95 ≈490–670 ms, p99 1.0–1.5 s; `pwa/profile` p99 spike 3.4 s |
| Production network, one Mac | TLS 0.7–1.8 s, TTFB 1.2–2.5 s, one 33.8 s outlier. Railway edge `ams1`, no CDN. Probably a proxy or VPN, so not conclusive |

**Corrections:**
- An earlier lab run served files without gzip and reported a 9.9 s LCP and
  a ≥3.5 s blank dictionary. Neither number holds under the production
  headers, and neither is used.
- The launch rows above come from the 1.1 harness, which replaced the
  first audit run. The audit run did not shape the cdnjs icon stylesheet
  and re-fetched warm launches in a new page. All widths are in
  `docs/PERFORMANCE_PWA_PROGRESSIVE_LOADING.md`.

### Audit inventory: already solved / to do / unnecessary

| Area | Status | Evidence |
|---|---|---|
| PWA course first paint: real shell, nav, path skeleton | Solved | Contract checkpoints; 1.1 harness FCP 1.2–2.2 s cold, ≈0.3 s warm |
| PWA Practice, Voice, Rating, Friends, Profile layout-faithful loading and independent retry | Solved, filmstrip pending | Contract retrofit items with 320/390/430 geometry tests; lab CLS ≈0 |
| PWA Settings push status pending/error/retry | Solved | Contract items; Node held-request tests |
| In-flight dedupe, bounded Voice request, deferred offscreen Practice/Profile work | Solved | Contract checkpoints with Chromium/WebKit tests |
| HTML ETag/304, immutable assets, SW cache-first, gzip | Solved | Production headers checked on 2026-11-22 |
| Course-map template cache | Solved | `tests.test_course_map_template_cache` |
| Dictionary virtual list | Solved | `dictionary-performance-guard.yml` |
| One edge swipe = one step; opaque dragged word page | Solved | PR #346, `tests/e2e/test_pwa_swipe_back.py` |
| Android dictionary scroll restore | Solved | `DictionaryScrollRestoreTest` |
| Android Rating/Dictionary skeletons; cache-first Course; offline start | Solved | `HskSkeleton` use; `ANDROID_CONTEXT.md` |
| CI guard covers Android and navigation | Solved | `check_backend_pwa_performance_contract.py` |
| Repeatable lab profile | Solved (1.1) | `scripts/measure_pwa_lab.py`, `tests/test_measure_pwa_lab.py` in CI |
| Real-user timing | To do | No RUM in repo; requirement §7 |
| Key action baselines: lesson open, exercise advance, search, swipe-back | To do | Not measured (above) |
| Inbox loading and error states | To do | `iphone-pwa-notices.js`: text-only loading, error without retry |
| Embedded-layer parent text status | To do if measured | Visible ≈150–400 ms warm; cold unknown on WebKit |
| Remaining layer back/scroll audit; root-tab drag peek | To do | Contract open item; owner report |
| Panda vs skeleton (hubs show the panda; lesson entry has a 720 ms minimum) | To do | Owner decision below; code above |
| Root-tab drag shows the empty paper under the tab | To do | Owner report; `goBack` comment above |
| Lesson finish → result: CTA hidden, no feedback while `lesson/complete` runs | Measure | `flowDone()`; server p95 ≈490–670 ms |
| Text fonts | Not applicable | System font stacks only (`design-tokens.css`); no text `@font-face` on learner pages |
| Icon font (Tabler 3.30.0 from cdnjs) | Measure | Non-blocking in the PWA (`media=print` swap); time to visible icons recorded in 1.3 |
| Debounced search, optimistic rollback, pagination | Solved | Dictionary filters bundled data locally and debounces only the history save; daily goal restores `previous` on save failure; Mistakes pages by `limit=30&offset` |
| OpenAI fallback client without a timeout | To do | `ai_provider.py` (above) |
| AI time to first useful response | Unmeasured | No learner AI endpoint timing recorded |
| Android process death, account switch without restart, memory, network bytes | To do | No test or measurement (above) |
| Backend replicas, capacity | Unmeasured | No saturation evidence; reopen only if production CPU, memory or pool waits show saturation |
| Android startup, first-drawn report | To do | No `reportFullyDrawn`; no measurement |
| Android full-screen loaders (first Course open, Ready Phrases) | To do | `CourseScreen.kt` `HskBrandLoader()` when `map == null`; `ReadyPhrasesScreen.kt` centred spinner |
| Android back/scroll audit, jank and ANR | To do | No data yet |
| `lesson/complete` double full-league leaderboard | To do | Code above; p95 ≈490–670 ms |
| `lesson/start` p90 tail; `pwa/profile` p99 spike | Investigate | Production metrics |
| Per-language i18n split | Unnecessary now | Cold-only 97 KB gzip, cached afterwards; four i18n guards and 13 pages depend on the shared files |
| Splitting inline JS out of the course HTML | Unnecessary now | 238 KB gzip re-downloads only after a deploy; reopen only if RUM shows post-deploy launches dominate slow launches |
| Removing `desktop-download.js` from the PWA | Unnecessary | 23 KB gzip cold-only; promos already inert without Telegram; it carries the Profile apps impression event; desktop is frozen (§6) |
| WebP/AVIF conversion | Unnecessary now | Largest image in the cold launch is the 21 KB logo PNG, immutable-cached |
| Redis, new queue, OpenTelemetry, SSR, CDN migration, course-map API split | Unnecessary now | Server p95 is fast for read paths; pages are private; the client network gap is unproven until RUM |
| AI streaming | Decide after 4.5 | Only if 4.5 shows the time to first useful response is the user's wait |

### Screen inventory by layout type

Known = real text available before any request. Async = pending data.

| Surface | Layout type | Known before request | Async | Loading state today |
|---|---|---|---|---|
| PWA Course | Path/mixed | Header, nav, level frame | Lessons, XP, streak | Path skeleton ✔ |
| PWA Practice | Card list | Six card titles | Counts and locks | Six geometry placeholders ✔ |
| PWA Voice | Mixed | Title, panda, description | Quota | Reserved quota slot ✔ |
| PWA Rating | Podium + rows | Headings, labels | Users, scores | Podium/rows ✔ (filmstrip open) |
| PWA Friends | Rows | Invite text | Friends, summary | Rows with retry ✔ |
| PWA Profile | Mixed | Labels, settings | Rings, calendar, achievements | Per-region ✔ |
| PWA Settings | Form | All labels | Push status | Pending/error/retry ✔ |
| PWA Inbox | Rows | Header, close | Notices | Text only ✘, no retry ✘ |
| PWA Dictionary | Virtual rows | Header, search | Word list (bundled) | Parent text before frame paint |
| PWA Phrases | Rows | Header, search, tabs | Categories | Parent text, then own skeleton |
| PWA Test centre hub | Card list | Header, title | Exams, results | Empty `#ex-list` behind the panda ✘ |
| PWA Mistakes centre hub | Rows | Header, title, tabs | Mistake targets (paged) | Empty, then spinner + text, behind the panda ✘ |
| PWA session start: Recognition, Pronunciation, Memorize (on open), Test exam, Mistakes review | Exercise | Frame | Session items | Panda at once, even when fast (owner: only if slow) |
| PWA Lesson entry | Exercise | Frame | Lesson items, first sound | Panda, 720 ms minimum ✘ |
| PWA Lesson flow, writer | Exercise | Frame | Lesson items | Not measured; writer has spinner + text |
| PWA Lesson finish → result | Result | Last card | Saved XP, rank, streak | CTA hidden, no state while saving (measure) |
| PWA Voice live page | Action | Title, topics | Connection, replies | Not measured |
| PWA Login | Form | Everything (static, 3.8 KB gzip) | Provider redirect | Static ✔ (first paint measured in 1.3) |
| PWA Onboarding | Form/steps | Step copy | Course tracks | Own skeleton + `aria-busy` ✔ (measured in 1.3) |
| PWA Handoff | Static | Everything (1.8 KB gzip) | — | Static ✔ |
| PWA Checkout | Form | — | — | Out of scope (owner keeps design) |
| Android Course | Path | Header | Map | Cache-first; first-ever open full-screen loader ✘ |
| Android Dictionary, Rating | Rows / podium | Header | Data | `HskSkeleton` ✔ |
| Android Profile | Mixed | Header | Profile data | Compact inline loader (audit) |
| Android Ready Phrases | Rows | Header | Phrases | Full-screen spinner ✘ |
| Android Lesson, Voice, Assistant | Exercise / action | Frame | Items, replies | Button-level spinners (action state, audit only) |

## Goals / Non-Goals

**Goals:**
- Measure first, on a fixed profile, then fix only what the measurement or the
  code shows is broken.
- Close the PWA gaps first; then Android; then Backend.
- Keep every package independently testable and revertible.

**Non-Goals:**
- A new navigation, skeleton or telemetry framework.
- A NavHost migration.
- New infrastructure.
- Desktop.
- Changing Telegram Mini App behaviour. Shared files (`course-v3.html`, the
  practice pages, the panda components) change only behind
  `PWA_COURSE_HOST`, the PWA boot's `html.hsk-pwa-practice` class or a
  PWA-only caller option. Telegram keeps today's timing and loaders, checked
  by the existing Mini App e2e smoke tests.
- Redesigning checkout.
- Changing the panda or skeleton artwork, copy or colours. Only when they
  appear changes.

## Decisions

1. **Edge claim plus a one-gesture token.** Done in PR #346; see the
   back-navigation spec. Kept because deduplication alone still showed
   iPhone's blank history snapshot.
2. **Lab harness reuses the e2e fixtures.**
   - A single script `scripts/measure_pwa_lab.py` serves the existing
     `ScreenPage` fixture over HTTP with production-like gzip, ETag and
     immutable headers.
   - It drives Chromium and WebKit with the fixed profile and prints JSON.
   - Rejected alternatives: Lighthouse and a new framework, both of which
     duplicate harnesses (§7).
   - The procedure is recorded in `docs/PERFORMANCE_PWA_PROGRESSIVE_LOADING.md`,
     not in a new document.
3. **Real-user timing through `clog()` → `/api/v3/clientlog`.**
   - One `sendBeacon` per launch, after the course is ready.
   - Contents: navigation timing, FCP, LCP, CLS, the slowest event duration,
     course-ready time, cold/warm and 304/200 from `transferSize`, viewport
     class, standalone or browser.
   - No account, text or token.
   - Read with `railway logs` (memory: `railway-logs-debugging`).
   - Rejected alternatives: a new analytics event, which touches funnel
     integrity, and OpenTelemetry, which is a new stack.
   - Monitoring impact: log volume of at most one line per launch.
4. **Inbox: reuse the existing row geometry and retry label.**
   - Placeholder rows are shaped like notice rows.
   - The error state gets an in-place retry using an existing reviewed UZ/RU/TJ
     retry string.
   - Owner-switch checks stay as they are.
5. **Embedded-layer text status is gated by a threshold, not rewritten.**
   - If WebKit warm opening shows the parent text for more than 300 ms, the
     preferred fix is to give that text an anti-flash delay, so a fast frame
     paints its own skeleton first.
   - Pre-warming the iframe in the PWA is rejected: it costs memory and bytes
     on every launch.
   - Duplicating the child's skeleton in the parent is rejected: it duplicates
     copy.
   - The same rule covers the Test and Mistakes hubs once they stop using the
     panda (decision 9).
6. **Root-tab drag: a live peek of the back destination (owner choice a).**
   - The peek shows the screen that back will open: the top of
     `SCREEN_HISTORY`, or Course when it is empty. Showing Course and then
     landing on another tab would be a wrong peek.
   - **At drag start** (the touch is in the claimed edge strip on a root tab
     with no layer open), the destination screen is shown as a fixed,
     `inert`, `aria-hidden`, non-scrolling underlay. It sits under the
     dragged tab, at the scroll position `App.show` would give it: the
     current-lesson position for Course, 0 for other tabs. The document scroll
     and the dragged tab do not change.
   - The dragged tab is opaque (paper background), as for the word page in
     2.2.
   - **On release past the threshold:** the dragged tab finishes off-screen,
     the underlay is removed, and the existing `goBack()` runs `App.show`.
     The destination's anchor (the current-lesson node for Course, the first
     card otherwise) must land within 8 px of where the underlay showed it,
     so nothing jumps. The old `translateX(-22%)` slide-in is dropped for
     this path.
   - **On cancel:** the tab snaps back and the underlay is removed. History
     and `SCREEN` are unchanged.
   - **Reduced motion:** no follow and no peek. A completed edge swipe still
     goes back one step. Spec: "or no follow with one step back".
   - **Performance gate:** on Chromium with 4× CPU, showing the underlay must
     not create a long task over 50 ms, and drag frames must stay at p95 ≤
     16.7 ms. If Course is too heavy to lay out at drag start, the underlay
     is prepared at `touchstart` inside the edge strip, before the move
     threshold. If the gate still fails, the peek is not shipped. The numbers
     go to the owner, and the fallback is option (b) (no follow, one step
     back).
   - Rejected: a screenshot or a stored DOM snapshot of Course. It goes stale,
     and the requirements forbid runtime layout snapshots (§2).
7. **Android first-drawn and skeletons.**
   - Call `reportFullyDrawn()` once, when the first useful Course frame
     (cached map or skeleton) is shown.
   - Replace the two full-screen loaders with `HskSkeleton` compositions shaped
     like the ready screens.
   - Add a baseline profile only if cold-start median exceeds warm by more
     than ~40% and a trace shows JIT or class loading dominating.
8. **Bounded leaderboard read in `lesson/complete`.**
   - The first measurement is a real-Postgres test of the statement count and
     time.
   - If the leaderboard dominates, replace both calls with one bounded query:
     the user's rank plus the neighbour rows.
   - A snapshot test asserts that the rank, the rank-up flag and the
     neighbour rows match the old code for leagues of 1, 5 and 500 users,
     including ties.
   - Progress, XP and streak writes stay in the same transaction.
9. **Panda only for a slow session start; skeletons for hubs (owner
   decisions).**
   - **One rule, PWA only:**
     - When a session starts, nothing new is drawn for the first 300 ms.
     - If the session is ready by then, it opens directly, with no panda and
       no wait.
     - If it is not ready, the panda appears and stays until the session is
       ready.
     - Once shown, it stays at least 300 ms so it never flashes for one or
       two frames. That is the only minimum.
     - The 720 ms minimum on lesson entry is removed for the PWA. Telegram
       keeps it.
     - The rule is passed as a caller option (`showAfterMs`,
       `minVisibleMs`) to the two existing components,
       `HSKLessonPresentation.beginLessonEntry` and the practice boot. No new
       component.
   - **Session starts:**
     - lesson entry;
     - opening Recognition, Pronunciation or Memorize;
     - Test `openExam(...)`;
     - Mistakes `startReview(...)`;
     - in-frame restarts: retry and "again".
   - **What counts as preparation:** the real work before the first usable
     card. For a lesson that is the reserve, the data and up to 1.8 s for the
     first card's sound (unchanged). A slow sound therefore shows the panda
     after 300 ms, and does not delay a fast start.
   - **During the first 300 ms** the user sees the screen they tapped from.
     For an iframe practice page, they see the parent entry's paper with the
     Back button. Back works throughout.
   - **Hubs (Test centre, Mistakes centre):**
     - No panda.
     - Each child page owns a layout-faithful skeleton in its own markup:
       exam cards in `#ex-list`, target rows in `#content`.
     - The boot reveals the frame at the child's first paint, not when the
       data lands.
     - The Mistakes spinner and "Yuklanmoqda…" become target-row
       placeholders for the first load and for category changes. "Yana
       ko'rsatish" keeps its button state.
     - Both hub skeletons apply only under the PWA boot
       (`html.hsk-pwa-practice`). Telegram opens the same pages and keeps its
       current spinner.
     - Before the child paints, the parent entry follows decision 5, the same
       as for Dictionary and Phrases.
   - **One visible loader at a time:** the parent entry before reveal, the
     child afterwards. A test asserts that the two are never visible
     together.
   - **Errors:**
     - The 20 s boot fallback gains a Retry next to Back, using the reviewed
       `practiceGateError.retry` string. Retry reloads the frame.
     - The per-page gate errors already offer retry and stay as they are.
   - **Unchanged:** grading, gates, limits, attempts, analytics events and
     the panda artwork and copy.
10. **External call bounds.**
    - The OpenAI fallback client gets an explicit timeout and retry count
      matching the primary client's settings. This happens only after the
      task 4.5 log read shows what fallback calls take today.
    - A test asserts the client's configured timeout.
    - Streaming is decided only from the 4.5 measurement (§5.6). It is not
      built speculatively.
11. **Android reliability matrix.**
    - The flows §4 calls reliability-critical are mapped to the tests that
      already exist (listed above).
    - New tests are added only for the two uncovered flows:
      - process death and restore on Course and in a lesson;
      - switching accounts without a restart, with no leak of the previous
        account's cached course or profile.
    - Memory (`dumpsys meminfo`) and network bytes per Course open are
      recorded with the 3.2 startup runs, on the same devices.

### Condition matrix (§7)

Each condition maps to an existing test, or to the task that adds the missing
check. "Existing" means the test is in the repository today.

| Condition | PWA | Android | Backend |
|---|---|---|---|
| Cold / warm start | Lab 1.1 ✔ | 3.2 | — |
| Slow network | Lab profile 1.1 ✔ | 3.2 (emulator network profile) | — |
| Intermittent network, timeout | Existing held-request tests (Settings push, Friends retry); Inbox in 2.3 | `OfflineModeTest` ✔; reconnect in 3.6 | Client timeouts in 4.5 |
| Request failure → retry | Practice, Friends, Settings ✔; Inbox 2.3; practice boot 2.8 | 3.3, 3.4 | — |
| Offline recovery | Course cached shell (contract) ✔ | `OfflineModeTest` ✔ | — |
| Large lists | Dictionary virtual list guard ✔; Mistakes paging ✔ | Dictionary list ✔ (`DictionaryScrollRestoreTest`) | 4.1 league of 500 |
| Session / account change | Practice actor check, Inbox owner switch ✔ (kept in 2.3) | Logout clears cache ✔; switch without restart 3.6 | Existing owner tests run in 4.x |
| Reduced motion | Root-tab peek 2.5; panda rule 2.8 | System animator scale off in 3.3 tests | — |
| Weak device | 4× CPU lab ✔ | Owner's weak device in 3.2 and 3.5 | — |

### Second-pass scope reduction (§8.5)

The draft was challenged item by item:

- **Merged:**
  - The contract's open items "every screen at 320/390/430", "filmstrip
    LCP/CLS/INP", "record before/after" and "Rating filmstrip" become one lab
    baseline task (1.3).
  - Inbox loading and Inbox retry become one task (2.1).
  - Android jank and ANR become one vitals-driven task.
- **Dropped with evidence:**
  - The dictionary "blank first open" (a no-gzip artifact).
  - The Practice first-visit shift (0.008, under the 0.1 limit, already
    geometry-tested).
  - The i18n split, HTML JS split, desktop script removal and image
    conversion (table above).
  - A separate RUM dashboard: logs are enough.
  - The non-production Loading/Data comparison view (§7). No shared template
    system is introduced or redesigned. Each new skeleton is screen-specific
    and checked by the existing 320/390/430 geometry tests.
- **Made conditional:**
  - The embedded-layer text fix and the baseline profile, each behind a
    measured threshold.
  - The `lesson/start` and `pwa/profile` investigations, fixed only if the
    cause is inside the app.
  - Lesson finish → result (inside 2.7), AI streaming (after 4.5), and
    backend replicas (on saturation evidence only).
- **Merged in the third pass:**
  - The §7 conditions are one matrix (above) instead of a test task per
    condition. Only the uncovered cells became work, inside 2.3, 2.8, 3.6
    and 4.5.
  - Memory and network bytes on Android join the 3.2 runs.
  - Payload sizes join 4.4.
- **Kept:** every item that maps to a spec scenario and has code or
  measurement evidence.

## Risks / Trade-offs

- [The lab harness drifts from production headers] → It asserts
  `Content-Encoding: gzip` and the cache headers on the first response, and
  fails otherwise.
- [The real-user beacon adds noise or cost] → One beacon per launch, timing
  fields only, `sendBeacon`, no retry; removable by reverting one function.
- [The bounded leaderboard query changes the rank on ties] → A snapshot
  equality test with ties runs before the swap; the old path is kept until it
  passes on real Postgres.
- [Android skeletons shift layout when the data lands] → An instrumentation
  bounds check on the header and first row, as in the loading spec.
- [HTML edits trip the i18n line anchors and `reviewed_sha1`] → Re-anchor
  once per package, by exact line identity (memory:
  `learner-page-token-change-needs-reanchor`).
- [Shared API changes break the Mini App or Android] → Each Backend task runs
  the existing Mini App and Android client contract tests that touch the
  route.
- [The root-tab underlay costs a long task or jank on Course] → The 2.5
  performance gate. If it fails, the peek is not shipped and the owner gets
  the numbers.
- [The underlay and the real Course disagree, so Course jumps on release] →
  The 8 px anchor check in the 2.5 test, at 320, 390 and 430 px.
- [The slow-only panda leaves a tap with no feedback for 300 ms] → The
  tapped control keeps its existing pressed state, and Back stays usable. The
  lab (1.2) records how often the panda appears before and after.
- [A hub skeleton changes Telegram] → It is gated by
  `html.hsk-pwa-practice`, and the Mini App smoke tests run.

## Migration Plan

- No data migration.
- Each package lands as its own pull request to main after its own checks.
- PWA reverts take effect on the next launch, because the HTML is ETag
  revalidated.
- Android ships only with a release cut per `ANDROID_RELEASE_CHECKLIST.md`.
- Backend reverts are a normal main revert.

## Owner decisions (2026-11-22)

- **Root-tab drag:** option (a), a live peek under Practice, Voice, Rating and
  Profile while dragging back. It is usually Course. When the user came from
  another tab, the peek is that tab, because back returns there (decision 6).
- **Panda preparing screen vs skeleton:**
  - The panda preparing screen shows only when a real session starts: a course
    lesson, a test, a pronunciation exercise, hieroglyph recognition, a
    mistakes review, and (by the same rule) a memorize session. It gives the
    "your lesson is being prepared" feeling.
  - Hub and list screens use layout-faithful skeletons: Dictionary, Ready
    Phrases, the Test centre and the Mistakes centre.
  - Today `iphone-pwa-practice-boot.js` shows the panda on every practice page
    open, including the hubs, so the hubs change.
  - The panda stays only while preparation is really running. There is no
    artificial delay, and an error shows a retry.
- **Slow-only panda (answer "a"):** the panda shows only when preparation
  takes longer than about 300 ms. A fast start goes straight into the
  session. The implementation rule is in decision 9, including the 300 ms
  minimum once shown that keeps it from flashing.

- **Back gesture during an active session (owner commit `10f496fd`, task
  2.6):** during an active lesson, test or Mistakes review, an edge swipe
  must not drag the screen. A completed gesture opens the exit confirmation
  instead. Cancel keeps the same question, and a confirmed exit follows the
  existing save rules, with no false resume promise.
  - **Lesson:** the confirmation already exists (`App.requestExitFlow`,
    "Darsdan chiqasizmi?"). The resume it promises is kept by
    `saveLessonResume()` or `Foundation.pause()`. 2.6 verifies both paths.
  - **Test exam and Mistakes review:** Back exits at once today
    (`exitExam()` to the hub, `closeReview()`). There is no confirmation and
    no reviewed exit copy. See the open question.

## Open questions

1. **Exit confirmation for the Test exam and the Mistakes review.** Today
   there is no confirmation for these two, so the owner chooses:
   - (a) Add a confirmation sheet with the lesson sheet's look. It needs new
     UZ/RU/TJ copy that says truthfully what is kept, checked per page in 2.6
     (an unsubmitted exam is not saved today). It promises no resume, and the
     owner approves the copy.
   - (b) Confirm only the lesson. In the test and the review, the swipe does
     not drag, and a completed gesture runs the existing exit at once.

   Task 2.6 cannot finish those two cases until this is answered. Everything
   else in 2.6 can proceed.

Gates that can send work back to the owner are named in their tasks: the
root-tab peek performance gate (2.5), the baseline profile (3.2), and the
edge or CDN evidence (4.4).
