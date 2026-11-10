# HSK AI — Performance Goals & Requirements: PWA, Android, Backend

> **Purpose:** A stable, technology-neutral statement of desired outcomes and non-negotiable requirements. **This is not an implementation plan, historical progress report or fixed snapshot of repository code.**
>
> These requirements apply to existing functionality and all relevant future additions. How to meet them must be decided by inspecting the **latest `main`** at planning/implementation time, never by assuming an old code structure, branch or prior task remains current.

## 1. Main goal

HSK AI must be **fast to open, responsive to interact with, visually stable, reliable on poor networks and economical to operate** without sacrificing functionality, access rules, privacy or learning accuracy.

What matters is the actual experience of a learner, not the number of technologies or optimizations installed. Improve the proven bottlenecks and preserve what already works. Do not make the product more complex or expensive without measurable benefit.

**Target product:** learner PWA (iPhone/iPad and supported browsers), **native Android** (Play and direct distribution), and the shared backend/API, database, network and relevant infrastructure supporting them. These platforms are part of the **same overall performance objective**, but do not need to be changed simultaneously.

## 2. Shared user-experience requirements

1. **Fast first useful screen.** Show a real application shell and usable non-sensitive navigation promptly; do not leave users watching a blank page, full-screen network spinner or frozen launch screen while optional data loads.
2. **Layout-faithful skeletons.** Every async screen, card, dialog, section, form, image and long-list region must reserve the final content's approximate position, dimensions, spacing and visual hierarchy before data arrives. A generic short grey rectangle cannot stand in for a complex real screen.
3. **True progressive loading.** Independent data areas load independently. As soon as one response is verified, that area settles into its **already reserved position** without moving the header, fixed navigation, nearby content or previously settled sections. Another slow/failed API must not block or erase the completed area.
4. **Smooth and restrained transitions.** Replace placeholders through a subtle, short fade within the reserved dimensions, without animating layout dimensions to conceal shifts. Respect reduced-motion settings and platform conventions. Loading, empty, error and retry are distinct, usable states.
5. **Real visuals at the right time.** Essential first-viewport HSK AI logo/mascot and visible images have priority. Offscreen resources load on demand. Use supported, correctly sized modern image formats where they actually reduce cost while keeping the original official assets/fallbacks. Reserve image geometry to avoid jumps.
6. **Responsive interactions.** Avoid repeated renders, duplicate equivalent in-flight reads and serial loading of independent work. Cancel stale reads when appropriate; debounce searches and autocomplete after typing pauses, but never delay or merge separate payment/lesson writes as if they were reads.
7. **Bounded information display.** Avoid loading/rendering enormous datasets upfront. Use appropriate pagination, incremental loading and virtualization when real list length, device capability or measurements justify them.
8. **Trustworthy cache and recovery.** Caches should improve perceived speed but must not expose other accounts' data or stale access rights. Under offline, timeouts and partial outages, keep safe, already verified UI usable and give local recovery/retry instead of false data or endless loading.
9. **Whole-product coverage.** The requirements apply to **all existing and newly added** learner surfaces (learning course, exercises, voice/AI, ratings, profile, dictionary, tests, results, onboarding, settings, notifications and future sections). A parent screen having a skeleton is insufficient if nested widgets still jump or block.

**Reusable, page-type-aware loading templates — not generic placeholders.** Before adding or changing a skeleton system, inspect the **current** pages/screens and existing loading components, classify their principal data shape (rows/tables, cards/media, charts/metrics, form/settings, or feature-specific mixed layouts), and record for each which visible elements are **known before the request** versus **derived from the response**. Reuse **one lightweight template per genuinely shared layout type**, composed of existing design primitives; retain a screen-specific composition when its geometry or content hierarchy is materially different. Do not force every page into a universal skeleton or create unnecessary abstractions.

**Keep known content real.** Static titles, tabs, section headings, column headers, field labels, navigation and other already-known **authorized, localized** copy should appear as real text immediately. Grey bars and reserved media shapes represent only genuinely pending data (names, scores, counts, values, user-specific content, unavailable media), never arbitrary replacements for fixed text. Protected labels or actions that imply verified identity/access still obey session and entitlement gates. Source all dimensions, spacing, copy and responsive variants from the **real current page/components**, not invented widths, placeholder text or guessed dataset lengths.

**Resolve the intended template without waiting for data.** Where multiple screens can share a shape, a route/section may declare a stable loading-template identifier **from known route/component metadata** before fetching. Reuse existing component contracts instead of introducing a mandatory new registry or framework. Nested asynchronous regions can have their own template, and partial/failed sections must settle or retry independently. A template name alone is never evidence of correct geometry.

**Concrete visual acceptance example:** A rating screen with three trophies, league labels, participant/time indicators, leaderboard title and ranked user rows must show placeholders in **each of those final slots** while loading. They become the real elements smoothly **in place**. This is a general rule for every screen's own design, not a requirement to copy the rating screen elsewhere.

## 3. PWA-specific requirements

- Prioritize early rendering of the shell and above-the-fold content, with independent loading for visible sections; avoid synchronous heavy JavaScript and unnecessary first-load DOM construction.
- Use safe browser/CDN/service-worker caching with correct versioning and invalidation. Keep dynamic personal responses private and session-validated.
- Limit expensive scripts, unnecessary dependencies, CSS/JS payloads, font variants and rerenders; evaluate route-based code splitting and delayed third-party loading where beneficial.
- Provide properly sized/lazy-loaded images and sensible WebP/AVIF fallbacks; never defer critical above-the-fold imagery by default.
- Respect mobile Safari/WebKit layout, iOS safe areas, keyboard and navigation, existing PWA install/onboarding flow, multilingual copy and accessibility. Do not break browser auth, device/account handoff, course progress or checkout.
- Test the **actual** loading → partial → ready → error → retry transition, not merely whether a skeleton DOM node exists. Visually fixed anchors should remain stable at narrow widths.

## 4. Native Android-specific requirements

- Native Android is **in scope for the overall performance program**, with its own measured implementation stage if that reduces risk. Cover both Play and direct app variants, preserving their real current feature/payment/update differences.
- Display real app structure promptly without long blank startup or screen-wide network waits. Use **native layout-matched placeholders** for loading elements and stable, smooth in-place settlement; do not force web-only mechanisms or CSS into native UI.
- Reduce unnecessary UI recomposition/rebuilds, heavy work on the main thread, memory churn, oversized images, duplicate repository/API requests and unnecessary startup work. Keep scrolling and input responsive; avoid hangs and ANRs.
- Use appropriate lifecycle-aware cancellation, bounded concurrency, pagination, local data caching and safe background execution; never create speculative queues or services when the existing Android architecture already handles a task.
- Treat foreground/background, network loss/reconnect, rotation where relevant, app resume, push/deep links, login callback, account switching, mandatory updates and offline learning as reliability-critical flows.
- Preserve Google/Telegram account linking and cross-device synchronization, correct course/Pro/Trial access and all supported payment routes. No false optimistic billing/access state.
- Verify performance on actual or representative **weak Android devices**, poor networks and both installed build variants. Measure startup responsiveness, UI frame delays/jank, errors/crashes/ANRs, memory and network usage with available platform-appropriate tools.
- Share backend improvements where appropriate but do not mechanically duplicate the PWA implementation in Android; native behavior should use existing Android architecture.

## 5. Backend, PostgreSQL and infrastructure requirements

1. **Measure real bottlenecks.** Establish request latency (including p50/p95 where available), SQL/query count, payload sizes, errors, network and resource overhead before declaring optimizations necessary or successful.
2. **Avoid duplicated work and N+1.** Remove redundant API calls, avoidable DB/ORM queries, repeated calculations and confirmed N+1 patterns without breaking authorization, idempotency or data correctness.
3. **Efficient database usage.** Select only required rows/columns, bound or paginate responses, inspect query plans before adding indexes, use connections and pools safely, keep transactions/locks short and avoid blocking DB resources on external IO.
4. **Resilient external APIs.** Apply sensible timeouts, cancellation, bounded parallelism, and retry/backoff only when semantics are safe. Separate non-interactive expensive work from user-critical paths when evidence shows need.
5. **Cache and deliver safely.** Prefer existing Cloudflare/static delivery, browser caching and bounded application caches before Redis or new servers. Design invalidation, cache keys, TTL and user ownership correctly. Serve appropriate compressed/static assets and stable cache headers without leaking protected data.
6. **AI responsiveness.** Improve time-to-first-useful-response; use genuine incremental streaming where supported and useful with correct cancellation, safety, auth and error handling. Do not simulate speed while the real backend work remains blocking.
7. **Lightweight architecture.** Reduce unnecessary dependencies and blocking operations. Consider load balancing, regional placement, extra replicas, SSR/SSG for eligible public pages or OpenTelemetry only if verified needs justify them. Do not replace existing services or architecture simply because a technique appears on an optimization checklist.
8. **Resource and cost discipline.** Improve reliability and response time without unnecessary memory, CPU, tokens, database connections, third-party bills or continuous monitoring cost.

## 6. Safety and compatibility requirements

- Authentication, session/CSRF, private data owner checks, account switching and logout remain correct at every stage; late or cached responses cannot cross user boundaries.
- Keep Trial/Free/Pro rights, subscription expiry, checkout/refunds, quota rules, learning progress, answers/grades, referrals, AI Voice and notifications server-authoritative. Never optimistically claim successful payment or unlocked content.
- PWA, Android, existing Telegram/Mini App and relevant Admin/backend clients must not regress due to shared API changes. Preserve currently operating Telegram flows; future Telegram migration is **not** an optimization shortcut.
- Respect the product's active PWA + Android priority. Do not spend time on desktop-only functionality or speculative desktop compatibility features; keep existing shared contracts reasonably stable.
- Follow the project's actual canonical localization, analytics, privacy, testing, security and release rules as they exist at the time of work. Instrumentation must not block user-critical actions or expose sensitive data.

## 7. Acceptance and ongoing prevention

- Prove improvement with **comparable before/after** evidence, distinguishing measurements, code inspection, assumptions and missing data. A passing test or the presence of skeleton code alone is not proof of real speed.
- Test cold/warm starts, slow/intermittent internet, timeout, request failures, offline recovery, large accounts/lists, session changes, reduced motion and weak devices. Use platform-appropriate real browser/device checks.
- For PWA loading geometry, verify representative first-viewport anchors on mobile sizes (including 320/390/430 px where applicable), investigate displacement exceeding about **8 px** and aim for **CLS ≤ 0.1**. Validate visually variable content rather than hiding jumps behind animation. Android uses analogous native view/frame measurements instead of web CLS as its only metric.
- Add meaningful, focused regression checks for new behavior and observed defects. Keep existing CI guards effective and extend coverage to **future new functions and Android** when those scopes are implemented. Avoid dummy tests and massive unrelated CI runs.
- Every new or materially modified PWA/Android/backend feature must meet applicable loading, data efficiency, security and observability requirements **from its first version**. An agent must explicitly explain justified non-applicability; do not leave new features outside monitoring or regression coverage.
- Accept a feature only after relevant measured behavior, functional tests, security and shared contract checks. Unverified results must remain labelled **unverified**.

## 8. Requirements for creating and simplifying the future implementation plan

This section specifies **how a separate plan must be produced**. It is **not the plan**.

1. **Fresh source of truth every time:** before planning, fetch and inspect the **latest `main` HEAD**, the project rules, relevant architecture/configuration, current existing functions, tests, CI and actual blockers. Never build a plan from a frozen commit SHA, an outdated branch, this file's phrasing alone, or historical checked boxes.
2. **Use the real `$hsk-ai-openspec-planning` skill:** read its **current repository instructions** and use its actual OpenSpec workflow/CLI when creating the substantive cross-platform plan. Validate against the repository's current OpenSpec project. Do **not** pretend a manually written Markdown template is a successfully generated OpenSpec plan when CLI setup/validation was not possible.
3. **Audit existing work before creating tasks:** recognize what is already implemented, what is partially implemented and what genuinely remains broken or slow. Reuse valid existing tests, helpers and infrastructure. For skeleton/loading work, inventory actual screens by layout type, distinguish their known static text from asynchronous data, and locate shared placeholders, loading labels and spinners **before** proposing new templates. Don't propose rebuilding already working functionality.
4. **Make only necessary tasks:** every proposed change must map to an unmet requirement **and** to code evidence or a test/measurement gap. Merge duplicate or strongly related tasks; remove ornamental sections, excessive abstraction, speculative technologies, redundant checks and unneeded documentation. Prefer the simplest safe solution. For a substantial new shared skeleton system, assess an **isolated optional Loading/Data preview** before integrating into production screens when it would meaningfully reduce visual risk; do not make a separate demo, blanket owner-approval checkpoint or global theme redesign mandatory for every routine improvement. Existing design/theme/global shared-component changes require explicit scope and compatibility review rather than being smuggled into an optimization.
5. **Perform a deliberate second-pass scope reduction:** after drafting, challenge every item: *Is it needed? Is it duplicative? Can it join another task? Does the benefit justify cost and regression risk?* Revise the plan into fewer, clearer, testable tasks without losing essential security or quality coverage.
6. **Split a large plan into manageable stages:** if a full PWA + Android + Backend change is too broad to do deeply, divide it into **independently testable, deliverable stages** with explicit dependencies and acceptance criteria. A sensible split may separate shared Backend, PWA and Android, but **derive the actual split from current code and bottlenecks** rather than making permanent phase numbers here. Do not do everything superficially at once.
7. **Maintain shared-contract safety:** each stage protects auth/entitlements/progress/payments and existing client compatibility; identify which other platform's tests are affected before implementation. Avoid expanding a stage into unrelated work.
8. **Deliver a separate, concise OpenSpec plan:** record its actual artifacts and acceptance criteria outside this requirements document. Requirements here remain stable while plans/implementations can evolve with `main`. The plan must clearly distinguish **already solved / to do / unnecessary with evidence**, and should not prescribe Redis, SSR, queues, OpenTelemetry, CDN migration or architectural replacement without need.
9. **Verification is not optional:** run available OpenSpec validation and relevant technical tests at the appropriate stages, reporting limits honestly. Do not equate proposal validation with production performance success.

**Permanent principle:** The requirements should not become obsolete because a branch, framework, server location or specific implementation changes. The next plan must adapt to the project — not force the project to match an old plan.
