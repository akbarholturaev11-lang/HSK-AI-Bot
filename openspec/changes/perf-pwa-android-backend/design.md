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
- **Android.**
  - Screens are swapped by `if/else` in `MainActivity.kt` (no NavHost).
  - The course map is cache-first.
  - `HskSkeleton` exists and is used by Rating and Dictionary.
  - There is no `reportFullyDrawn` and no baseline profile.
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
| Cold course launch | FCP 0.9–1.1 s, course ready 2.9–3.1 s, LCP 3.1–3.9 s, CLS ≈0. 555 KB in 42–45 requests: course HTML 238, `hsk-course-i18n.js` 59, `hsk-miniapp-i18n.js` 38, `tabler-icons.min.css` 32, `desktop-download.js` 23, logo PNG 21 KB |
| Warm course launch | FCP ≈0.4 s, course ready ≈1.9 s, assets from cache. The lab browser re-fetched the HTML; production answers 304 |
| Tab switch (action → ready) | Practice 212, Voice 133, Profile 211–278, Course 232 ms. Practice first visit has one 0.008 shift; others have none |
| Dictionary layer | Rows painted by 150 ms; search "xue" 15 ms, "学习" 84 ms. A translation query was not measured reliably (harness timeout) |
| Phrases layer | Parent text status at 150 ms, its own row skeleton by 400 ms, categories by 800 ms |
| Practice pages, lesson open, exercise advance | Not measured: the fixture serves stub practice pages and has no `lesson/start` |
| Production server (Railway, 7 days) | session p95 ≈43 ms; course HTML p95 ≈93 ms; map p95 ≈310–370 ms; `lesson/start` p50 ≈62 ms, p90 ≈400 ms; `lesson/complete` p50 ≈215 ms, p95 ≈490–670 ms, p99 1.0–1.5 s; `pwa/profile` p99 spike 3.4 s |
| Production network, one Mac | TLS 0.7–1.8 s, TTFB 1.2–2.5 s, one 33.8 s outlier. Railway edge `ams1`, no CDN. Probably a proxy or VPN, so not conclusive |

**Correction:** an earlier lab run served files without gzip and reported a
9.9 s LCP and a ≥3.5 s blank dictionary. Neither number holds under the
production headers, and neither is used.

### Audit inventory: already solved / to do / unnecessary

| Area | Status | Evidence |
|---|---|---|
| PWA course first paint: real shell, nav, path skeleton | Solved | Contract checkpoints; FCP 0.9–1.1 s cold, ≈0.4 s warm |
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
| Repeatable lab profile and real-user timing | To do | No harness or RUM in repo; requirement §7 |
| Key action baselines: lesson open, exercise advance, search, swipe-back | To do | Not measured (above) |
| Inbox loading and error states | To do | `iphone-pwa-notices.js`: text-only loading, error without retry |
| Embedded-layer parent text status | To do if measured | Visible ≈150–400 ms warm; cold unknown on WebKit |
| Remaining layer back/scroll audit; root-tab drag peek | To do | Contract open item; owner report |
| Practice pages' panda boot overlay | Measure only | Owner design; changes need an owner decision |
| Android startup, first-drawn report | To do | No `reportFullyDrawn`; no measurement |
| Android full-screen loaders (first Course open, Ready Phrases) | To do | `CourseScreen.kt` `HskBrandLoader()` when `map == null`; `ReadyPhrasesScreen.kt` centred spinner |
| Android back/scroll audit, jank and ANR | To do | No data yet |
| `lesson/complete` double full-league leaderboard | To do | Code above; p95 ≈490–670 ms |
| `lesson/start` p90 tail; `pwa/profile` p99 spike | Investigate | Production metrics |
| Per-language i18n split | Unnecessary now | Cold-only 97 KB gzip, cached afterwards; four i18n guards and 13 pages depend on the shared files |
| Splitting inline JS out of the course HTML | Unnecessary now | 238 KB gzip re-downloads only after a deploy; reopen only if RUM shows post-deploy launches dominate slow launches |
| Removing `desktop-download.js` from the PWA | Unnecessary | 23 KB gzip cold-only; promos already inert without Telegram; it carries the Profile apps impression event; desktop is frozen (§6) |
| WebP/AVIF conversion | Unnecessary now | Largest image in the cold launch is the 21 KB logo PNG, immutable-cached |
| Redis, new queue, OpenTelemetry, SSR, CDN migration, AI streaming, course-map API split | Unnecessary now | Server p95 is fast for read paths; pages are private; the client network gap is unproven until RUM; no AI latency evidence |

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
| PWA practice pages (5) | Exercise | Title | Session items | Panda boot overlay (owner design) |
| PWA Lesson flow, writer | Exercise | Frame | Lesson items | Not measured; writer has spinner + text |
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
- Changing Telegram Mini App behaviour.
- Redesigning checkout or the practice boot overlay without the owner.

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
6. **Root-tab drag: the owner chooses.**
   - (a) A live peek of the Course underneath, or (b) no drag on root tabs,
     with the edge swipe still going back one step.
   - Both satisfy the back-navigation spec.
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
- **Made conditional:**
  - The embedded-layer text fix and the baseline profile, each behind a
    measured threshold.
  - The `lesson/start` and `pwa/profile` investigations, fixed only if the
    cause is inside the app.
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

## Migration Plan

- No data migration.
- Each package lands as its own pull request to main after its own checks.
- PWA reverts take effect on the next launch, because the HTML is ETag
  revalidated.
- Android ships only with a release cut per `ANDROID_RELEASE_CHECKLIST.md`.
- Backend reverts are a normal main revert.

## Open Questions

- Which root-tab drag behaviour the owner prefers, (a) or (b). The task and
  its test exist either way.
- Whether the owner wants the practice boot overlay changed if the baseline
  shows it is visible for more than 1 s warm. Until then it is measured only.
