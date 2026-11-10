# HSK AI — Backend & Learner PWA Performance: Goals and Requirements

> **Document type:** Product objective and permanent requirements contract — **NOT** an implementation plan, sprint backlog, task log or assertion of completed work.
>
> **Baseline reviewed:** Current `main` project rules and performance contract on 2026-11-10.
>
> **Authority:** `AGENTS.md`, `AI_RULES.md`, `PROJECT_MEMORY.md`, and `docs/PERFORMANCE_PWA_PROGRESSIVE_LOADING.md` remain authoritative for their existing invariants. Follow the latest versions when work begins; resolve any conflict in favor of security, active product priorities, and current verified code/contracts. This document defines the **desired outcome**, not the mechanism or implementation sequence.

## 1. Core objective

Make HSK AI feel **immediately usable, visually stable, fast, resilient and economical** on real phones and unstable networks, without degrading Chinese learning, user trust, revenue flows or account security.

- Opening the learner PWA must not feel like a blank, frozen or endlessly spinning application.
- Real UI structure should be visible early; real data fills **its predetermined place**, independently and smoothly.
- Slow requests, large data, third-party APIs and avoidable backend work must not hold unrelated user interactions hostage.
- Real measured user experience — not a count of added optimization techniques — determines success.
- Improve the existing architecture first. Avoid technology additions, unrelated refactors and unnecessary token/infrastructure spending.

## 2. Scope and product direction

**Current implementation scope:** Learner PWA on iPhone/iPad Safari and supported browsers; canonical FastAPI/backend APIs, PostgreSQL, existing Cloudflare/CDN/cache/R2 infrastructure and shared web assets consumed by the PWA.

**Shared-code boundary:** Existing Telegram Mini App, Telegram bot, Android, auth, payments, course and Admin PWA consumers must retain their valid API/domain contracts. Backend improvements may benefit these consumers, but must not silently change their behavior. Admin PWA needs separate UX work only where an affected shared backend contract requires it.

**Explicitly outside this performance work:**
- Android native UI/app-specific performance optimization: a later dedicated stage, without changing `android/` now. Shared backend contracts must remain Android-compatible.
- macOS/Windows Desktop feature development, parity, packaging and desktop-only tests: currently frozen by `AGENTS.md`. Keep generic contracts reusable; create no speculative desktop adapter or code.
- Immediate Telegram-bot teaching shutdown or migration. Future direction is bot handoff to PWA/Android, but existing Telegram education, referral, payment, account and progress flows must keep working now.
- Replacing the frontend framework, database, queue infrastructure or deployment topology without a demonstrated need.

**Scope rule:** This document does **not** authorize work in every listed area. It describes acceptance requirements for a future expanded plan. Actual implementation should be scoped and evidence-driven.

## 3. User-visible PWA loading and interaction requirements

**PWA-01 — Shell before slow data.** Display the real approved HSK AI page shell, title, navigation, background, layout and safe placeholders as early as possible; never show a blank/black viewport or fullscreen network spinner during ordinary load. Session verification must precede private content or active protected controls.

**PWA-02 — True layout-matched skeletons.** **Every existing and future** learner screen, section, card, profile panel, image area, modal, sheet, list and embedded widget must reserve the positions and approximate dimensions of its actual final UI. A generic two-line box is unacceptable for a multi-element final view. Reserve headings, art, cards, buttons, rows, gutters and bottom navigation consistently; avoid large empty gaps.

**PWA-03 — Rating is an explicit reference.** The `Reyting` loading view must reserve the final heading, **three league trophies/podium positions**, league-name labels, participant count/countdown, weekly Top-5 heading, and visible rank/avatar/name/XP rows. Existing artwork and fixed bottom nav remain stable while the leaderboard request is unresolved. Apply the same fidelity to every other screen's actual design, not to a copied Rating layout.

**PWA-04 — Independent loading boundaries.** Course, Practice, AI Voice, Rating, Friends, Profile, Settings, dictionary, mistakes, lessons/tests, checkout, notices/push and future features have their own `loading | ready | empty | error | retry` handling where data is asynchronous. A slow/erroring secondary endpoint must not blank a loaded screen or prevent unrelated ready sections from functioning.

**PWA-05 — In-place progressive settlement.** Replace each skeleton **only within its reserved visual slot** as independently **verified** data arrives. No full-page rerender, nav displacement, visible jump, unrelated skeleton reset or content reordering solely because a slower API finished. Results of unknown length may extend below initially reserved rows without moving stable first-viewport anchors.

**PWA-06 — Subtle and accessible transitions.** Prefer a brief `opacity` transition of roughly 150–250 ms inside fixed geometry; do not animate `height`, `top`, `margin` or position to conceal layout instability. Under `prefers-reduced-motion: reduce`, settle immediately. Keep loading status accessible; decorative bars must not become focusable controls.

**PWA-07 — Images and visual priority.** First-viewport real brand/logo/Panda and useful above-the-fold imagery must load eagerly and not be hidden by offscreen lazy-loading. Reserve intrinsic dimensions/aspect ratio. Load genuinely offscreen pictures/embeds lazily, favor appropriately sized modern WebP/AVIF when quality/size/support justify them, preserve exact official mascot/artwork and provide safe fallbacks. Avoid blocking initial UI on decorative asset loads.

**PWA-08 — Fast, bounded interactions.** Search/autocomplete must debounce after typing pauses and cancel superseded reads. Equivalent in-flight reads must be deduplicated per user/session/parameters. Stale requests cannot overwrite later state. Independent queries may run concurrently with sensible limits; writes such as checkout and lesson submission must **not** be debounced/deduplicated as if they were reads.

**PWA-09 — Efficient views.** Large API-backed lists use bounded paging and virtualization where profiling indicates benefit; screens not currently needed must avoid unnecessary initial DOM creation. Reduce duplicate renders and excessive JS/CSS work. Split bundles/routes and delay noncritical third-party scripts when this measurably improves real load, without harming auth/learning.

**PWA-10 — Reliable offline/cache behavior.** Use browser/CDN/Service Worker caches for safe static resources, with content-addressed versions and coherent invalidation. Reuse trusted current-session data appropriately, but never show stale account-specific or protected states before owner/session validation. Offline or failed requests show a usable, local recovery state rather than invented content or infinite loading.

**PWA-11 — Preserve entry and localization.** Preserve existing iPhone Safari/Home Screen install and onboarding flows, PWA browser auth, verified language authority and UZ/RU/TJ canonical UI localization. Keep safe areas, responsive layout, navigation and back behavior functioning on mobile WebKit.

## 4. Backend and infrastructure requirements

**BE-01 — Measure before changing.** Identify actual slow routes and cost centers, capture baseline timings, SQL counts, payload size and query plans. Prefer remedies backed by a verified bottleneck.

**BE-02 — No wasteful requests or N+1.** Remove redundant equivalent API calls, repeated database reads, synchronous duplicate work and demonstrated N+1 queries while preserving request ownership, cache keys, user intent and write semantics. Avoid broad ORM changes without evidence.

**BE-03 — Efficient PostgreSQL.** Fetch only needed columns/rows; use bounded pagination; inspect filters, sorting, joins and `EXPLAIN (ANALYZE)` before adding indexes. Avoid long-running transactions, leaked sessions and N+1 fetch patterns. Maintain safe pooling and protect row-lock/idempotency/concurrency behavior.

**BE-04 — Predictable API payloads.** Provide bounded result sets and payload sizes appropriate to the user view. Pagination must be deterministic and not break course order, progress semantics, rankings or user identity.

**BE-05 — External reliability.** Apply appropriate timeouts, cancellation, bounded concurrency and safe/idempotent retries with backoff for external APIs and expensive tasks. Errors must be contained and reflected in the affected UI only; never claim success on an uncertain write.

**BE-06 — Parallel and background work.** Run independent safe operations concurrently when beneficial; move confirmed long noninteractive tasks to an **existing appropriate** background/queue mechanism with idempotency, retry and failure visibility. Do not add queues or new servers without evidence.

**BE-07 — Caching without leaks.** Prefer current Cloudflare CDN/cache/R2, browser and bounded process-memory capabilities before adding Redis. Cache public/static templates safely; retain invalidation, bounded memory/TTL, and owner-aware private data policies. Never publicly cache tokens, payment results, Pro/Trial entitlement decisions, private lesson progress or user payloads.

**BE-08 — Static delivery and network efficiency.** Review CDN routing, `Cache-Control`, immutable hashed assets, ETag and correct MIME; enable Brotli/Gzip where supported and beneficial. Avoid pointless double compression or caching mutable authenticated responses.

**BE-09 — AI responsiveness.** Where the provider/API supports it and UX benefits, stream genuine model output incrementally with safe cancellation and error handling. Never fake token streaming or leak incomplete unverified billing/access state.

**BE-10 — Sustainable infrastructure.** Avoid unnecessary packages, unused imports, event-loop blocking and excessively distant backend–database placement. Do not introduce Redis, extra replicas, load balancing, SSR/SSG, OpenTelemetry or architectural rewrites by default; require proof of a concrete performance/capacity gap. SSR/SSG is only an option for eligible **public** pages, never as an unauthorized shortcut for private course data.

## 5. Business, security and cross-platform invariants

**SAFE-01.** Authentication, verified owner/session boundaries, cookies/CSRF, account switching, logout, login recovery and privacy remain authoritative; an old request must not render another user's content.

**SAFE-02.** Trial/Free/Pro rights, expiry, payments/refunds, checkout, limits, course progress, tests, answers/grades, streaks, referrals and notification preferences stay correct. Optimistic UI is restricted to reversible, non-sensitive actions; no optimistic subscription or payment success.

**SAFE-03.** Existing Android/Mini App/shared API contracts, Telegram WebApp compatibility and currently working learning flows must not regress during PWA/backend performance changes.

**SAFE-04.** No personal information, auth tokens, prompts, private learning details or payment secrets in public CDN caches, telemetry labels, logs, test fixtures or generated static HTML.

**SAFE-05.** Any user-visible behavior change must evaluate **Analytics Impact** under the permanent analytics rule; connect real measurement to its trusted backend/Admin consumer when applicable. Telemetry must never block a lesson, payment or login.

**SAFE-06.** Follow existing localization and product design policy; no invented user-facing text or duplicated localization source and no unrelated redesign or feature removal.

## 6. Real performance evidence and acceptance

**MEASURE-01.** Report before/after comparable data, not statements such as “faster” based only on code inspection: backend p50/p95, request count, SQL count/duration, payload sizes; mobile first usable render, LCP, CLS, INP and error/retry rates where observable.

**MEASURE-02.** Use real or production-like mobile conditions: iPhone Safari/WebKit and Chromium; 320/390/430 px widths; slow and intermittent network, throttled CPU/low-end device, cold and warm caches, reduced motion, background/foreground, timed-out/failed requests.

**MEASURE-03.** Confirm visual geometry on `loading → partial → ready → error → retry`. Measure stable heading, primary artwork, cards/first rows and fixed navigation anchor positions. Investigate shifts greater than **8 px** in stable anchors and target **CLS ≤ 0.1**; do not hide jumps with animation. Where content is inherently variable, justify exceptions with real screenshots/filmstrips.

**MEASURE-04.** Test account switch, stale session/CSRF, unsigned/unauthenticated entry, Pro/Trial boundary, payment state, slow leaderboard and concurrent requests under realistic timing. False “Pro” badges or other account data are release blockers.

**MEASURE-05.** Add privacy-safe real-user monitoring/diagnostics when appropriate, use existing monitoring where adequate and add OpenTelemetry only for a proven blind spot. Measured improvement and acceptable cost/regression risk are the outcomes; no fabricated p95 or production claims.

## 7. Permanent future-feature and CI acceptance

**FUTURE-01 — Applies automatically to new work.** Every newly added or materially changed learner PWA screen, route, card, image, list, dialog and backend endpoint inherits the requirements above **from its first implementation**. Do not defer this to a later optimization sprint.

**FUTURE-02 — AI must remember.** Any coding agent must read `AGENTS.md`, `AI_RULES.md`, this goals/requirements file and the canonical detailed performance contract when the task affects Backend/PWA. New features must explicitly evaluate loading geometry, independent fetching, queries, cache, permissions and operational metrics; mark a requirement “not applicable” only with a reason.

**FUTURE-03 — Evidence-bearing regression tests.** Every substantial new Backend/PWA feature or change needs focused tests for affected request lifecycle, layout, identity and error conditions. For visual PWA work, verify real loading-vs-ready element geometry in Chromium **and** WebKit, using the shared geometry assertion helper where appropriate; a grey-box selector alone is not sufficient.

**FUTURE-04 — CI prevents silent regression.** Keep and evolve `.github/workflows/backend-pwa-performance-contract.yml` and its policy guard to cover new routes/components, not only the original Course/Rating fixtures. Ensure meaningful tests run on relevant changes; report skip/failure explicitly. Presence of a test file or a green generic policy job **does not prove** new UI/endpoint performance.

**FUTURE-05 — Honest completion criterion.** A feature is complete only when the relevant behavior, security, slow-network response, browser/SQL regression, shared-client compatibility and available performance evidence have passed. Do not mark missing measurement or incomplete coverage as verified. Keep failing checks and unresolved regressions visible.

**FUTURE-06 — Low-friction maintenance.** Prefer a small permanent contract plus focused reusable tests, not large duplicate documentation, forced infrastructure changes or expensive end-to-end runs for unrelated doc-only edits. Whenever the product adds a genuinely new surface, update its own test coverage rather than weakening the global guard.

## 8. What this file intentionally does NOT specify

This is **not** the implementation sequence: no phases, effort/time estimates, task assignment, backlog checkboxes, commit checklist, or instruction to refactor the entire repository. No technique is mandated merely by its popularity.

The later expanded implementation plan must begin from **fresh `main`**, current measured evidence and applicable project rules, then map work back to the requirement IDs above. The existing detailed performance document remains the source of historical checkpoints and current acceptance notes; do not copy stale “done” states from it into this goal contract.

---
**Canonical related documents**
- [Agent rules](../AGENTS.md)
- [AI rules](../AI_RULES.md)
- [Project memory](../PROJECT_MEMORY.md)
- [Existing performance acceptance and implementation history](PERFORMANCE_PWA_PROGRESSIVE_LOADING.md)
- [Backend/PWA performance CI](../.github/workflows/backend-pwa-performance-contract.yml)
- [Analytics integrity policy and plan](analytics/ANALYTICS_INTEGRITY_IMPLEMENTATION_PLAN.md)
