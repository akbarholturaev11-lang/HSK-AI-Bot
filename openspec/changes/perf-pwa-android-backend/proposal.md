# Proposal

## Why

The owner reported, with a screen recording, that the learner PWA goes back two
sections on a swipe that starts at the screen edge, shows a white or overlapping
screen while swiping back from the dictionary, and behaves unstably when layers
open and close. The performance requirements
(`docs/PERFORMANCE_BACKEND_PWA_GOALS_REQUIREMENTS.md`) also require one
coordinated PWA + Android + Backend effort from the start, with every future
feature meeting the same bar. The existing contract
(`docs/PERFORMANCE_PWA_PROGRESSIVE_LOADING.md`) covers PWA loading and Backend
checks in depth, but no plan covered navigation defects or Android. A quick
direct task would leave that gap open.

Authoritative sources: the two documents above, `AGENTS.md` ("Permanent Backend
/ learner PWA performance contract"), `NEXTATION.md` NXT-001,
`ANDROID_CONTEXT.md`. This proposal does not restate them.

## What Changes

- **Done in this change, verified:**
  - PWA: one edge swipe is exactly one back step. The browser's own history
    swipe is claimed at the edge and deduplicated.
  - PWA: a dragged dictionary word page is opaque and closes before it snaps
    back.
  - Android: the dictionary list keeps its scroll position when the learner
    returns from a word.
  - The permanent CI guard now covers Android source and the swipe-back
    regression.
- **Planned, evidence-first:**
  - remaining PWA layers' back and scroll behaviour;
  - the root-tab swipe peek, which needs an owner design choice;
  - Android cold start, jank and back-stack audit;
  - the three measured slow learner API paths;
  - before/after field measurements.
- **Removed from the plan as unproven or duplicate:** Redis, new queues or
  OpenTelemetry, a course-map API split, WebP/AVIF conversion and AI streaming.
  They stay in the contract's master checklist and are pulled in only with
  measured cause.

## Capabilities

### New Capabilities
- `learner-back-navigation`: how learners return to the previous screen on PWA
  and Android. One gesture is one step, there is no blank or see-through frame,
  and the previous position is kept.
- `learner-performance-acceptance`: the measurable acceptance a learner-facing
  PWA, Android or Backend change must meet before it is called done, and the
  gate that enforces it.

### Modified Capabilities
- (none: no existing spec covers learner navigation or performance)

## Impact

- **Platforms:**
  - learner PWA (`app/static/course-v3.html`, `app/static/hsk-lugat.html`);
  - native Android, Play and direct (`feature/dictionary`, plus later screens
    from the audit);
  - Backend lesson routes (`/api/v3/lesson/complete`, `/api/v3/lesson/start`,
    `/api/v3/pwa/profile`).
- **Current evidence:**
  - production 7-day latency: session p95 ≈43 ms, course HTML p95 ≈93 ms,
    `/api/v3/map` p95 ≈310–370 ms, `lesson/start` p90 ≈400 ms against p50
    ≈62 ms, `lesson/complete` p50 ≈215 ms and p95 ≈490–670 ms, `pwa/profile`
    p99 spike 3.4 s;
  - an iOS Simulator Safari recording of the double back before and after the
    fix.
- **Excluded:**
  - desktop (frozen);
  - the Telegram Mini App's own BackButton semantics, which must stay
    unchanged;
  - lesson, grading, payment and entitlement logic;
  - new infrastructure.
- **Risks:**
  - claiming the edge touch could swallow a tap on an edge control (controls
    are exempted and tested);
  - backend work touching progress or XP atomicity.
- **Rollback:** each package is its own commit. The PWA fix is reverted by
  restoring the two HTML files. The Android fix is local to one composable.
  The guard extension is one script and its test.
