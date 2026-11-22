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
    clearing in `CourseRepositoryTest`. No test covers real process death
    and restore, switching accounts without a restart, or the automatic
    reconnect (`OfflineModeTest` covers only the tap retry).
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

### Re-check after syncing with main and PR #352 (2026-11-23)

This branch now contains main `caaae35c` (PRs #348–#351) and PR #352
(NXT-011, Smart Reminder D35). The plan was re-read against that code:

- **Launch path: unchanged.** The only change on the course launch path is
  the deferred `hsk-diagnostics.js` token. The 1.1 baselines stay
  representative; 1.3 re-measures on the current head anyway.
- **"Knot Thread" launch mark and the Pro panda (#348):** shipped as
  components and not wired (`docs/design/LAUNCH_MARK_AND_PRO_PANDA.md`). They
  change nothing today. If the owner later wires them, decisions 13 and 16
  apply to them (below).
- **Trial colours (#348):** the trial layer and its page moved from ink
  `#211D17` to the paper and gold palette (`--hsk-pro-*`, theme colour
  `#FDF9F0`). Decision 16 follows that.
- **Monitoring (NXT-011, #352):** learner JS incidents are now grouped by
  exception name, reason and first-party asset (`catalog.DEBUG_ASSETS`). The
  four character scripts and `iphone-pwa-refresh.js` are on that list, so
  2.9 and 2.10 keep their paths.
- **Smart reminders (#349):** the Inbox feed now resolves the template once
  per Smart row (one `notification_templates` query per row, up to 20 per
  page) instead of once per key. This is new evidence for the Inbox and is
  measured in 4.6.
- Nothing else in the merged changes touches a screen, route or rule in
  this plan.

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
| Embedded-layer cover (Dictionary, Phrases) | To do | The cover stays until the full iframe `load` and hides the child's own skeleton; it has no Back and no error/retry, so a page that never loads leaves "Yuklanmoqda…" forever. Owner rule: no loading text, a matching skeleton instead (decision 5) |
| Launch path to the first frame | Measure, then to do | The first paint is already the shell skeleton, but four character scripts, the Telegram SDK and ten stylesheets block it on a cold launch (decision 13) |
| In-lesson personal review and Mistakes review wait for the server on every answer | To do | `adaptiveSubmit` waits up to 8 s; review `pickOption` waits and blocks on failure; server p50 ≈37–51 ms, so the wait is the network (decision 15) |
| Pro, trial and limit windows | To do | Sheet: "Tariflar yuklanmoqda…" text and two sequential requests; checkout and trial layers: empty until the child paints (decision 16) |
| Pull-to-refresh (Course, Rating, Profile) | To do | `iphone-pwa-refresh.js` reloads the whole page; no armed state at the threshold, no spinning ring, no region skeletons (decision 14) |
| Telegram SDK in the PWA head | Measure | `telegram-web-app.js` (19 KB gzip, 120 KB raw) is parser-blocking in `<head>` on every PWA launch; 1.3 records its main-thread time before FCP |
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
| Inbox feed: one template query per Smart row since #349 | Measure | `resolve_for_feed` calls `NotificationTemplateService.resolve` per row, up to 20 per page (4.6) |
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
| PWA Dictionary | Virtual rows | Header, search | Word list (bundled) | Parent text cover until full `load`, then an empty list; no Back/retry ✘ (2.4) |
| PWA Phrases | Rows | Header, search, tabs | Categories | Parent text cover until full `load`, then own skeleton; no Back/retry ✘ (2.4) |
| PWA pull-to-refresh | Root tabs | Header, nav | The tab's data | Full page reload, ring vanishes ✘ (2.10) |
| PWA in-lesson personal review, Mistakes review | Exercise | Question, options | Verdict | Waits for the server on every answer ✘ (2.11) |
| PWA limit and Pro sheet | Sheet | Header, benefits, buttons | Plans, prices | Skeleton plus loading text; two round trips ✘ (2.12) |
| PWA checkout and trial layers | Full screen | Child header | Child page | Empty until the child paints ✘ (2.12) |
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
   - The error state keeps its existing error text and gains an in-place
     retry labelled with the reviewed `courseLoadError.btn` (UZ/RU/TJ). No
     new copy.
   - Owner-switch checks stay as they are.
5. **Embedded layers: a matching skeleton, never a loading text, with Back
   and Retry (owner rule, 2026-11-22).**
   - **Defect, found in code:** `RESOURCE.ensure` covers Dictionary and
     Phrases with an opaque "Yuklanmoqda…" status until the iframe's `load`
     event. That event waits for every subresource, so the child's own header
     and skeleton paint underneath and stay hidden. The status has no Back
     button and no error state. If the page never loads, the text stays
     forever and only an edge swipe leaves.
   - **Owner rule:** these layers show no "Yuklanmoqda…" or any other
     loading text. The skeleton itself tells the learner the page is
     loading.
   - **Fix (PWA path, `PWA_COURSE_HOST`):**
     - **Before the child paints,** the parent's cover is a skeleton of that
       layer:
       - the real localized title (`resourceLabel(k)`) and a working Back
         icon, at the positions of the child's own header controls;
       - bars shaped like the child's first viewport: search field and rows
         for Dictionary, tabs and rows for Phrases, exam cards for the Test
         centre, target rows for the Mistakes centre;
       - no other visible text. The screen-reader status keeps the existing
         `state.loading` label, which is not visible.
     - The title, Back and paper background are there at once. The bars
       appear after a 150 ms anti-flash window, so a fast open never flashes
       them. The 1.3 warm-open filmstrip confirms that window.
     - **The child's first paint is the same skeleton,** so the handoff is
       invisible:
       - `hsk-lugat.html` gains static row placeholders in `#list`, under
         `html.hsk-pwa-browser` only. Today the list is empty until the data
         renders.
       - Phrases already has `.phrase-skeleton`.
       - The Test and Mistakes hubs get theirs in 2.8.
     - **One geometry source:** each parent skeleton is drawn from a small
       table of the child's own measurements (header height, field, row
       height and gap), not from a free copy of its markup.
       - A Chromium/WebKit test at 320, 390 and 430 px compares the parent
         skeleton with the child's skeleton. The header and the first three
         rows must agree within 2 px.
       - If a child's layout changes, that test fails until the table
         follows.
       - This replaces the earlier rejection of a duplicated skeleton. The
         owner rule needs a skeleton before the child exists, and the test
         removes the drift risk.
     - **Reveal:** the child signals its first paint through the existing
       same-origin parent call pattern, as the practice boot does with
       `revealPracticeFrame`. The parent removes its skeleton then; `load`
       stays as the fallback.
     - **Error:** after 20 s without the signal, the skeleton gives way to
       `courseLoadError.body` with Retry (`courseLoadError.btn`, which
       reloads the frame) and Back.
       - This is the only text the cover can show, and it reports an error,
         not loading.
       - The timeout is the same as the practice boot's. No new copy.
   - **First useful frame (for targets, decision 12):** still the child's
     first paint. The parent skeleton covers the wait but does not count as
     the layer being open.
   - The same rule covers the Test and Mistakes hubs (decision 9).
   - Telegram keeps its pre-warm and its current cover (non-goals).
   - **Rejected for now:** pre-warming the iframe in the PWA.
     - It costs memory and bytes on every launch.
     - Reopen only if 1.3 shows that the child's first paint on warm WebKit
       opens commonly exceeds 300 ms. Then measure the memory cost and bring
       it to the owner.
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
    - **Learner AI endpoints measured in 4.5:**
      - `/api/v3/pwa/voice/message` and `/api/v3/android/voice/message`;
      - `/api/v3/pwa/voice/pronounce` and `/api/v3/android/voice/pronounce`;
      - `/api/v3/android/assistant/conversations/{id}/messages`;
      - the connect time of the live sockets `/api/v3/pwa/voice/live` and
        `/api/v3/android/voice/live`.
    - **No DB lock across external IO (§5.3):** 4.5 checks that no learner
      path holds a row lock (`with_for_update`) or an open transaction while
      it waits on AI or TTS. A violation found is fixed with a test.
    - Streaming is decided only from the 4.5 measurement (§5.6). It is not
      built speculatively.
11. **Android reliability matrix.**
    - The flows §4 calls reliability-critical are mapped to the tests that
      already exist (listed above).
    - New tests are added only for the three uncovered flows:
      - **Real process death and restore,** on Course and in a lesson. The
        app is sent to the background with `UiDevice.pressHome()`, killed
        with `am kill`, and relaunched. `ActivityScenario.recreate()` is not
        enough: it keeps the process and its in-memory state.
      - **Switching accounts without a restart,** with no leak of the
        previous account's cached course, profile or rating.
      - **Automatic reconnect:** when the network returns, the
        `OfflineMode` network callback clears the offline state without a
        tap. Today `OfflineModeTest` covers only the tap retry.
    - Rotation is not applicable as a reliability flow. `MainActivity`
      declares `configChanges` for orientation and size, so it is not
      recreated. The 3.4 audit checks the layout only.
    - Memory (`dumpsys meminfo`) and network bytes per Course open are
      recorded with the 3.2 startup runs, on the same devices.
    - **Weak device (§4):**
      - **Mandatory:** a low-end profile on the installed API 36 emulator
        image: 2 GB RAM, 2 cores, the slow-network profile.
      - **Also used:** the owner's real low-end phone when the owner
        provides one.
      - **Owner approval needed:** downloading an older OS image (API
        26–29), because it is a large download.
    - **ANR and crash data:**
      - the owner's Play Console vitals export when provided;
      - otherwise the app's own exit-reason diagnostics
        (`reportExitReasons()`, API 30+) from production logs. These are
        already reported for both flavours.

12. **Target rule for every measured action (§7, no universal 400 ms).**
    Targets are set from each action's own lab baseline (Chromium 4× and
    WebKit, warm and cold), by action type:
    - **Interactions** (tab switch, search keystroke, exercise advance,
      swipe-back start): action to next paint ≤200 ms, the Web Vitals
      "good" INP bound.
    - **Openings** (first open of a layer, lesson open, session start,
      lesson finish → result): action to first useful frame ≤1000 ms on a
      warm open.
    - **Launch:** a warm launch keeps its baseline. A cold launch reaches
      the shell skeleton within 1500 ms on both lab engines (decision 13).
      Real users judge the rest: if the 1.4 p75 LCP exceeds 2.5 s, the
      cold-path items marked "Unnecessary now" are reopened with that
      evidence.
    - **Pull-to-refresh:** release to the first skeleton frame is an
      interaction (≤200 ms). Release to settled content keeps the 1.3
      baseline of today's full reload, or improves on it.
    - **An action already inside its bound** has the target "no regression
      beyond 10%".
    - **An action outside its bound** has the bound as its target. The
      task that owns the action fixes it: 2.4 or 2.8 for layers and
      sessions, 2.7 for the lesson, 2.3 for Inbox, 2.9 for launch, 2.10
      for pull-to-refresh, 2.11 for answers in a session, 2.12 for the
      Pro, trial and limit windows.
    - **Exception:** if the bound cannot be reached because the cause is
      outside the app (network or provider), it is recorded with the
      evidence and approved by the owner, as for the 8 px geometry rule.
    - **Every PWA package** must also add no new console or page error in
      the lab run for the actions it touches (§7, route and browser errors).

13. **Launch: the first frame is the skeleton, and the path to it is short
    (owner, 2026-11-22).**
    - **Today, in code:**
      - On the PWA route the first page paint is already the
        layout-faithful shell: `.pwa-initial-shell` in each root tab, the
        real nav labels and the pulsing path skeleton. The shell starts about
        37 KB (gzip) into the 244 KB document. The Telegram launch splash is
        removed at once on this route, and `#s-course>.loading` ("…") is
        hidden.
      - Before that paint, iOS shows its launch image (logo on paper,
        `/assets/startup/`) and Android shows the manifest splash.
      - Parser-blocking in `<head>` before the shell:
        - `telegram-web-app.js`;
        - four character scripts: `hsk-character-pack.js`,
          `hsk-character-motion.js`, `hsk-study-preparing.js`,
          `hsk-lesson-presentation.js`;
        - ten stylesheets.

        Warm launches read them from the service-worker cache; cold
        launches fetch them.
      - Lab (1.1): warm FCP ≈0.3 s and course ready ≈0.7 s. Cold FCP
        1.24 s (Chromium) and 2.18 s (WebKit), course ready ≈3.6 s.
    - **Rule:** from the first page paint until the course is ready, the
      learner sees the shell skeleton pulsing (static under reduced motion).
      Never a blank page, "…" or a spinner. A failed map keeps the existing
      `courseLoadError` with retry. A test with a held map request locks this
      on both engines.
    - **Faster first frame:**
      - 1.3 measures what each parser-blocking resource costs the cold first
        frame.
      - A resource the shell does not need, costing at least 100 ms on
        either engine, moves off the PWA first-frame path in 2.9. On the PWA
        route it loads after the first paint; Telegram keeps today's order.
      - The character scripts are needed only at session starts, so they
        are the first candidates. Before a move, every call site must be
        shown not to run before the script arrives.
    - **Target (decision 12):** cold time to the shell ≤1500 ms on both lab
      engines.
      - Chromium (1238 ms) is already inside: no regression beyond 10%.
      - WebKit (2178 ms) must reach 1500 ms, or carry an owner-approved
        exception with the evidence.
      - A warm launch keeps its baseline.
    - **Launch mark (#348, not wired):** if the owner replaces the Golden
      Logo with the "Knot Thread" mark, the PWA route keeps removing the
      splash at once, so the mark never delays the shell. Its own design
      note sets the same rule.
    - **Not in this change:** serving the course HTML from the service
      worker on a slow network.
      - It would let the shell appear before the server answers.
      - But it reverses the documented rule that HTML always goes to the
        network, and it could open an old version.
      - Reopened only if 1.4 shows a real-user p75 response start above
        1000 ms. The owner then decides with that data.
14. **Pull-to-refresh: a spinning ring, skeleton regions and one exact
    threshold (owner, 2026-11-22).**
    - **Today, in code (`iphone-pwa-refresh.js`, PWA course route only):**
      - It covers the Course, Rating and Profile tabs.
      - A pull starts only at the top of the page, with no scrolled
        ancestor. It is blocked while a flow, sheet, paywall, layer or the
        splash is open.
      - A 34 px circle with the `ti-refresh` icon follows the finger at 0.6×
        (at most 120 px) and turns with it. Nothing marks the threshold,
        which is 84 px of circle travel, or 140 px of finger travel.
      - Released past the threshold, the whole page reloads
        (`location.replace`). The ring vanishes at unload and the page is
        rebuilt from its first frame.
      - That reload is also how a learner whose PWA stays in memory picks
        up a newly deployed version.
    - **Exact threshold:** one constant, 140 px of finger travel (today's
      value; it can be tuned once in the 5.1 device QA).
      - While pulling, an arc around the icon fills in proportion to the
        distance.
      - At exactly the threshold the arc closes and the ring takes the
        accent colour: "release to refresh". No extra animation.
      - Pulling back short of the threshold un-arms it. Releasing un-armed
        springs back with no request.
    - **Released armed:** the ring stays where it armed and spins (one turn
      per 0.8 s) until every refreshed region has settled, then fades out.
      - Minimum visible time is 600 ms, so even a fast refresh reads as a
        refresh.
      - The maximum is the regions' own deadlines (10 s for the map).
    - **Regions become skeletons in place.** Regions whose data is
      re-requested switch to their existing placeholders. The header, tab
      title, bell, settings and nav stay real and usable.
      - **Course:** `refreshCourseProgress()`. The course body below the
        header shows the `.pwa-initial-shell` body, taken once at boot from
        the page's own initial shell. There is no second copy of it.
      - **Rating:** the active sub-tab's request, shown with
        `ratingLoadingHtml()` (`PWA_RATING_SKELETON_BODY` or
        `PWA_FRIENDS_SKELETON_BODY`).
      - **Profile:** the course map, and `loadProfileDetail()` forced past
        its 30 s guard. The accuracy rings and the map-driven sections show
        their existing placeholders. The name and avatar stay real, because
        they are known locally.
    - **Settle:**
      - Success replaces each region's skeleton with the new content.
      - The tab stays at the top, where the pull started. `renderCourse()`
        does not scroll; only `App.show` scrolls Course to the current
        lesson, and a refresh does not call it.
      - Failure or timeout puts back the previous verified content
        unchanged, with one toast: `courseLoadError.body` (reviewed
        UZ/RU/TJ). No new copy.
    - **A new version still arrives:**
      - In parallel, the page revalidates its own HTML (`cache:
        "no-cache"`, the URL the reload would use). It compares the
        response's `Last-Modified` with `document.lastModified`.
      - If the server copy is newer, the page reloads as today, and the ring
        keeps spinning until the page leaves.
      - If it is equal, or the check fails, nothing more happens. It is one
        conditional request, normally a 304.
    - **Dedupe and scope:**
      - Another pull while refreshing is ignored.
      - Leaving the tab hides the ring; its regions still settle.
      - PWA only. The Telegram Mini App has no pull-to-refresh and is
        unchanged.
      - Reduced motion: no spin, a static full ring and static skeletons.
    - **Disclosed exception:** the 600 ms minimum is the one place a fast
      response shows placeholders. The refresh is the learner's own
      request, so the anti-flash rule does not apply to it (loading-states
      spec).
    - **Rejected:**
      - Keeping the full reload: it rebuilds the whole page and the ring
        vanishes at unload.
      - A new refresh component: the existing script and the tabs' own
        loaders are enough.

15. **Answers in a learning session are graded on the device and recorded
    later, as in lessons (owner, 2026-11-23).**
    - **Today, in code:**
      - **In-lesson personal review (UIUX-007, `course-v3.html`
        `adaptiveSubmit`; Android `LessonAdaptiveReview`):** the plan
        arrives without answer keys (`public_question`). Every tap waits
        for `POST adaptive/answer`, up to 8 s, before right or wrong shows.
        On a failure the learner sees "saved offline" and no feedback.
      - **Mistakes review (`course_v3_mistakes.html` `pickOption` and
        `submitBuilder`; Android review screens):** every answer waits for
        `POST mistakes/review/answer`. On a failure the options unlock and
        a system `alert` (a toast in the Telegram copy) asks the learner to
        try again; the session cannot go on.
      - **The server is not the slow part.** Production, 7 days:
        `adaptive/answer` p50 ≈51 ms, p95 ≈121–153 ms;
        `mistakes/review/answer` p50 ≈37 ms, p95 ≈313 ms. The wait is the
        network round trip, 1.2–2.5 s from one measured network.
      - Lessons, the Test exam, Recognition and Memorize already grade on
        the device and record at the end.
    - **Change (the lesson format):**
      - When the client declares local grading (a new request field;
        older clients get today's shape), the plan response and the review
        start response carry each question's key: `answer_index` or
        `answer_tokens`, plus `correct_answer` and `explanation`.
      - The client grades with the server's exact rule: the option index
        must equal `answer_index`; tokens must equal `answer_tokens` in
        order, after the same whitespace normalisation. Feedback shows at
        once.
      - **Recording, in the background:**
        - Personal review: the answer is posted at once; a failure goes
          into the existing outbox (10 answers, 36 h). The outbox is
          flushed at the next plan load, as today, and also once
          `lesson/complete` has settled.
        - Mistakes review: answers are posted in order in the background.
          `review/complete` is already the end-of-session wait, like
          `lesson/complete`. It first waits until the queued answers are
          committed. If one cannot be committed, completion shows its
          existing error with retry, and the session stays on the device
          until it succeeds or the learner leaves.
      - **The server stays the judge:**
        - it re-grades every recorded answer against its own snapshot;
        - the first answer per item stays final;
        - it never trusts a verdict sent by the client.
      - **Parity:** a test grades every question format that
        `mistake_drill_factory` produces on both sides and requires the
        same verdict. A mismatch in production is logged as a server
        diagnostic. The server's verdict counts for learning state, and the
        feedback already shown is not changed afterwards.
    - **Integrity trade-off:**
      - The personal review gives no XP (`adaptive` is not a trusted
        reward source). A key on the device changes nothing there.
      - The Mistakes review awards XP (base 5 per session for targets from
        trusted sources), and today it commits each answer before it
        reveals the feedback. With the key on the device, a technically
        skilled user could read the answers from the network, as is already
        possible in lessons. The owner chose (a) on 2026-11-23: the
        Mistakes review is graded on the device too, like lessons.
    - **Server waits that stay, with the reason:**
      - Pronunciation scoring (lesson speaking cards, the Pronunciation
        practice): speech is scored on the server. It keeps its checking
        state and its skip.
      - AI coach and AI Voice replies: the AI runs on the server.
      - Session start and finish (`lesson/start`, `lesson/complete`,
        `exams/complete`, `review/start`, `review/complete`): covered by
        2.7, 2.8, 4.1 and 4.2.
    - The plan request at lesson start is already asynchronous (6 s
      timeout) and never delays the first card. It is unchanged.
    - **Telegram:** the shared `course-v3.html` keeps server grading for
      the Mini App in this change (non-goals). It can adopt the same request
      field later.
16. **Pro, trial and limit windows open at once and settle without a jump
    (owner, 2026-11-23).**
    - **Today, in code:**
      - **Limit and Pro sheet (`iphone-pwa-inline-pro.js`, opened by
        `iphone-pwa-inline-pro-bridge.js`):**
        - The sheet, its header, benefits and two plan skeletons show at
          once, together with a visible "Tariflar yuklanmoqda…" text.
        - Its data needs two requests, one after the other:
          `pwa-auth/session`, then `subscription/overview`. The session
          request repeats after every return to the app, because
          `visibilitychange` resets it.
        - The server is fast (overview p50 ≈163–224 ms, p95 ≈233–335 ms;
          session p50 ≈16 ms), so the wait is two network round trips.
        - The skeleton always shows two plans. If the server returns
          another number, the sheet's height jumps.
        - Overview writes on every call (`ensure_referral_code`,
          `sync_referral_discount_progress`, then a commit). It must not be
          fetched in advance on every launch.
      - **Full checkout (`/iphone-pwa/checkout?embedded=1`, "Boshqa
        tariflar") and the trial offer (`/iphone-pwa/onboarding/li?
        embedded=1&offer=trial`):** iframes created on tap. Until the child
        paints, the layer is empty paper, with no control. Since #348 the
        trial layer also uses the paper and gold palette.
    - **Change (PWA only; the owner's checkout design, colours, copy and
      payment logic stay as they are):**
      - **No visible loading text** in the sheet (the decision-5 rule). The
        plan skeleton count is the count the server last returned on this
        device. Only that number is stored; the default is two.
      - **One request instead of two:** the sheet reuses the course page's
        verified PWA actor (user ID and CSRF). The owner-switch check stays.
        If no actor is available, it falls back to its own session request.
      - **Repeat opens are instant:** the last overview for this actor
        shows at once from memory and is revalidated quietly, through the
        existing `load(true)`. The pay button activates only when the fresh
        answer arrives, and a changed price updates in place. Memory only,
        cleared when the actor changes, because it holds the email.
      - **Fetched early only when the opening is certain:** a preview
        lesson always opens the sheet at its half (`previewHalfAt`). At
        that lesson's start, the overview is requested in the background
        with `inline_preview`, which records no analytics. Its writes are
        the same ones the opening would make.
      - **Checkout and trial layers** follow decision 5:
        - until the child paints, the layer shows the child's header, with
          its close control at the child's position, and bars shaped like
          its first screen, on the paper background both layers now use;
        - the child is revealed at its first paint;
        - after 20 s, the existing error with Retry and close appears.
      - **Warm-up:** the service worker already warms the checkout page's
        assets. The trial page (`/iphone-pwa/onboarding/li?embedded=1&
        offer=trial`) joins `WARM_PAGES`.
      - **Smooth:** the sheet keeps its existing entrance (`hip-page-in`)
        and gets no new animation. The plan area keeps its reserved height
        and the button row stays fixed, so the swap from skeleton to plans
        moves anchors by at most 8 px. Nothing synchronous runs between the
        tap and the sheet's first frame.
    - **Targets (decision 12):** tap to the sheet's first frame is an
      interaction (≤200 ms). Tap to plans with an active pay button is an
      opening (≤1000 ms warm). The checkout and trial layers are openings
      measured to the child's first paint.
    - **The Pro panda module (#348, not wired):** if the owner wires
      `HSKProPanda` into the sheet, its CSS and script load with the
      sheet's existing assets (`_PWA_INLINE_PRO_HTML`), and its one-time
      effect must not delay the sheet's first frame.
    - **Android** gets the same rules for its native Pro, trial and limit
      screens (`SectionLimitOverlay.kt`, `LiOnboardingChoices`) in 3.7.

### Condition matrix (§7)

Each condition maps to an existing test, or to the task that adds the missing
check. "Existing" means the test is in the repository today.

| Condition | PWA | Android | Backend |
|---|---|---|---|
| Cold / warm start | Lab 1.1 ✔ | 3.2 | — |
| Slow network | Lab profile 1.1 ✔ | 3.2 (emulator network profile) | — |
| Background, process death, resume | — (the browser owns the page lifecycle) | Real process-death test in 3.6 | — |
| Intermittent network, timeout | Existing held-request tests (Settings push, Friends retry); Inbox in 2.3; embedded-layer 20 s timeout in 2.4 | `OfflineModeTest` ✔ (tap retry); automatic reconnect in 3.6 | Client timeouts in 4.5 |
| Request failure → retry | Practice, Friends, Settings ✔; Inbox 2.3; Dictionary/Phrases 2.4; practice boot 2.8 | 3.3, 3.4 | — |
| Offline recovery | Course cached shell (contract) ✔ | `OfflineModeTest` ✔ | — |
| Large lists | Dictionary virtual list guard ✔; Mistakes paging ✔ | Dictionary list ✔ (`DictionaryScrollRestoreTest`) | 4.1 league of 500 |
| Session / account change | Practice actor check, Inbox owner switch ✔ (kept in 2.3) | Logout clears cache ✔; switch without restart 3.6 | Existing owner tests run in 4.x |
| Reduced motion | Root-tab peek 2.5; panda rule 2.8 | System animator scale off in 3.3 tests | — |
| Weak device | 4× CPU lab ✔ | Low-end emulator profile (mandatory) plus the owner's phone if provided, in 3.2 and 3.5 | — |

### Second-pass scope reduction (§8.5)

The draft was challenged item by item:

- **Merged:**
  - The contract's open items "every screen at 320/390/430", "filmstrip
    LCP/CLS/INP", "record before/after" and "Rating filmstrip" become one lab
    baseline task (1.3).
  - Inbox loading and Inbox retry become one task (2.3).
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
- [HTML edits trip the i18n line anchors, `reviewed_sha1` and, since NXT-011,
  the monitoring token-only exemption] → Re-anchor
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
- [The parent layer skeleton drifts from the child's skeleton, so rows jump
  at the handoff] → The 2.4 geometry test (2 px at 320, 390 and 430 px) fails
  until the measurement table follows the child.
- [Moving a character script off the first-frame path breaks a session start
  or Telegram] → 2.9 moves a script only after its call sites are shown not
  to run earlier. It is PWA-only, and the lesson, practice and Mini App smoke
  tests run on both engines.
- [In-place refresh stops new versions from reaching learners whose PWA stays
  in memory] → The `Last-Modified` check reloads when the HTML is newer. An
  e2e test changes the fixture's HTML date and expects the reload.
- [A refresh failure wipes good content] → Failure restores the previous
  verified content; a held-then-failed request test covers each tab.
- [The device and the server grade one answer differently] → The 2.11 parity
  test covers every factory format; the server's verdict counts, and a
  mismatch is logged.
- [A Mistakes review answer is never committed, so completion fails] →
  Completion waits for the queue and keeps its existing error with retry;
  the session stays on the device until it succeeds.
- [A cached overview shows an old price] → The pay button activates only
  after the fresh answer, and changed prices update in place.

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
  - **Test exam and Mistakes review: owner chose (a), a confirmation as in
    the lesson.**
    - Today their ✕, the swipe and browser back all exit at once
      (`exitExam()` to the hub, `closeReview()`).
    - After 2.6, all three exits go through one confirmation sheet while a
      session is active, the same as the lesson, where every exit goes
      through `NavBack.goBack()` → `App.requestExitFlow()`.
    - It is PWA only (`html.hsk-pwa-practice`). Telegram keeps today's
      immediate exit (non-goals).
    - **What is really kept, checked in code (2026-11-22):**
      - Test: answers live only in memory (`eans`) until
        `/api/v3/exams/complete`.
      - Mistakes: each answer is only an analytics event
        (`mistake_review_answered`). Mistake progress is written by
        `complete_review`.
      - Neither session can be resumed.

      So the copy must promise no resume and must say the attempt is not
      saved.
    - **Copy, approved by the owner on 2026-11-22:**

      | | UZ | RU | TJ |
      |---|---|---|---|
      | Test, title | Testdan chiqasizmi? | Выйти из теста? | Аз тест мебароед? |
      | Test, body | Javoblaringiz saqlanmaydi. | Ваши ответы не сохранятся. | Ҷавобҳои шумо нигоҳ дошта намешаванд. |
      | Test, keep | Testni davom ettirish | Продолжить тест | Идома додани тест |
      | Review, title | Xatolar ustida ishlashni to‘xtatasizmi? | Прервать работу над ошибками? | Кор бар хатоҳоро қатъ мекунед? |
      | Review, body | Bu urinish natijasi saqlanmaydi. | Результат этой попытки не сохранится. | Натиҷаи ин кӯшиш нигоҳ дошта намешавад. |
      | Review, keep | Davom ettirish | Продолжить | Идома додан |
      | Exit button (both) | existing `common.action.exit` | | |

      The new keys go into the canonical i18n catalog with all three
      languages, and the i18n baseline guard passes.

- **Three requirements added by the owner after the copy was accepted:**
  - Dictionary and Phrases (and the hubs) show no loading text at all: a
    skeleton instead (decision 5).
  - The PWA opens fast, and a slow open shows the skeleton so the learner
    feels it loading (decision 13).
  - Pull-to-refresh: a spinning 🔄 ring, the refreshed regions as
    skeletons, and one exact distance that arms the refresh (decision 14).
- **Two more requirements (2026-11-23):**
  - Answers in the in-lesson personal review do not wait for the server:
    graded on the device, recorded later like a lesson. The same for any
    similar section, which is the Mistakes review (decision 15).
  - The Pro, trial and limit windows open as fast and smoothly as possible
    (decision 16).
  - **Mistakes review integrity: option (a), 2026-11-23.** The review is
    graded on the device like lessons. The owner accepts that a technically
    skilled user could read the answers from the network, as in lessons.
    The server still re-grades every answer and awards XP only by its own
    verdict.

## Open questions

None. The Mistakes review integrity question was answered with (a) on
2026-11-23 (owner decisions above).

Gates that can send work back to the owner are named in their tasks:
the root-tab peek performance gate (2.5), the baseline profile (3.2), the
edge or CDN evidence (4.4), and any owner-approved exception to a target
(decision 12).
