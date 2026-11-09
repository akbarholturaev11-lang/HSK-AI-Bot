# HSK AI — Performance audit acceptance: Backend and PWA

Scope: canonical backend, API, PostgreSQL, Cloudflare, Telegram Mini App shared assets and authenticated learner PWA. `android/` native implementation is out of scope. Preserve native/Telegram shared API contracts.

## Required: Initial Render & Progressive Loading (PWA)

This is a **release acceptance criterion**, not an optional visual enhancement.

1. **Shell first:** On an authenticated course document, show the real HSK AI brand, navigation, layout and non-personalized placeholders before the slow map POST resolves. Do not cover the full viewport with a splash or leave a blank black screen. Never reveal a cached protected screen before verifying the current session.
2. **Independent sections:** Course, Practice, Voice, Rating and Profile have their own loading/empty/error states. Slow secondary requests must not prevent the course shell or other ready sections from displaying; fill each section when its verified response arrives. The first implementation provides PWA-only static shell and existing per-tab rendering; independent API boundaries remain a separate measured task.
3. **Prioritize first viewport:** Render the header, navigation and first course cards first. Critical logo/mascot imagery must not use offscreen lazy-loading. Consider preload and `fetchpriority="high"` only after measuring a real LCP bottleneck.
4. **Defer offscreen assets:** Use `loading="lazy"` for genuinely offscreen images and embedded content, reserve width/height or aspect ratio, prefer appropriately sized WebP/AVIF if supported and demonstrably smaller.
5. **Stable geometry:** Skeletons must approximate actual cards with reserved heights; measure and keep CLS low; respect `prefers-reduced-motion`. No spinner-only screen during network latency.
6. **Safe cached data:** Current authorized in-memory state may be reused while refreshing. Persisted account-bound data, trial/Pro status, lesson rights and progress **must not** be displayed without session/owner revalidation; don't cache payment results or tokens. If no trusted cache exists, show skeleton instead.
7. **Progressively settle:** While a request is pending, each area displays only its own skeleton. Replace it immediately after that area's verified response. Network failures must preserve functional navigation, a retry option and isolation of already loaded sections.
8. **Verify behavior:** Audit full-screen blocking pages and synchronous JavaScript. Test authenticated and unauthenticated entry, account changes, stale CSRF, slow/failed/timeout map, Safari WebKit, screen dimensions, reduced-motion and above-the-fold image priority. Protect Pro, login, sessions, subscriptions and lesson state.

## Mandatory: Layout-matched skeletons and smooth in-place settlement (all future learner PWA sections)

**Reference case: Rating/Reyting iPhone PWA.** A sparse generic two-line card is NOT an acceptable loading state if the loaded view contains a three-trophy league podium, league labels, participant/countdown row, weekly Top 5 heading, avatar/rank/name/score rows and fixed bottom navigation. The real screenshot currently demonstrates this mismatch; mark the Rating geometry remediation as **pending** until verified, not completed.

- **Reserve the real visual composition from first paint.** Draw the screen's non-private static layout immediately: title at its final top position, three aligned trophy/league slots (their exact positions and relative sizes), the member/countdown area, weekly heading and at least the first visible leaderboard rows, including rank, avatar, name and score placeholders. For other sections, skeleton structure must match **their own** actual UI, not be a recycled generic card.
- **No empty middle of the page.** Placeholder heights, grid columns, gaps, margins, paddings, border radii, visual anchors and breakpoints should closely match the intended populated layout. Preserve the existing artwork/background and fixed bottom navigation. Use realistic reserved dimensions for pictures/avatars/text, including the first viewport; do not block on network just to construct placeholders.
- **Independent in-place settlement:** once one section's verified data arrives, replace only its corresponding placeholder **in the exact reserved slot**; leave all sibling skeletons and loaded elements stable. The whole page, other ready sections and bottom nav must not rerender or visibly jump. Unknown list lengths may expand **below** the initially reserved rows without moving the top anchors.
- **Smooth but minimal:** use a short opacity cross-fade (approximately 150–250 ms) on content within the reserved geometry; avoid animating size, margins, top, left or global layout position. Do not make the user wait for the animation or use a fade that briefly hides the page. Under `prefers-reduced-motion: reduce`, settle instantly.
- **Security and accessibility:** skeleton content contains no unverified username, score, Pro status, lesson rights or private cached data. Mark loading regions with `aria-busy` / accessible status as appropriate; decorative placeholders are hidden from assistive technology. Errors must retain the stable shell and local retry without implying data was received.
- **Acceptance with real browsers:** run throttled Chromium and iPhone WebKit loading→partial→ready→error/retry tests. Capture geometry of matching anchors before/after: title, league podium, participant bar, Top 5 heading, first visible rows and fixed nav. As a starting acceptance threshold, strive for ≤8 px displacement at stable anchors and CLS ≤0.1 over the measured interaction; investigate any excess rather than hiding it with animation. Assert there are no duplicate API requests while re-rendering. Test 320/390/430 px mobile widths and reduced motion. Real content with unpredictable size may require justified exceptions documented alongside screenshots/filmstrip.
- **Every new feature inherits this:** new sections, cards, tables, search results, lists, profiles and image blocks must use their own layout-faithful skeleton from the initial implementation. Add a focused Playwright geometry test for the new screen using `tests/pwa_layout_geometry.py`, not just a check that any grey box is visible.

- [ ] **Current Rating/Reyting example:** replace the sparse first-rating loading blocks with layout-faithful podium/leaderboard placeholders and verify in-place crossfade by Chromium/WebKit filmstrip. This is **not** marked implemented by adding the policy/CI guard.

## Implementation / verification checkpoints

- [x] Identified course startup blocker: original shared source has a full-screen splash and a single `…` placeholder, and waits for the authenticated map before calling `renderAll`.
- [x] Reconciled against main `e5026949` and later `9b75f132` (Foundation audio success and PWA transient map retry retained): **one authoritative native PWA first paint** remains in shared `app/static/course-v3.html`, guarded by PWA path/CSS, while Telegram retains its original splash. Removed the redundant response-side injected skeleton from `pwa_auth.py`. The authenticated backend route still owns session/CSRF and never injects user/Pro state into static shell. Main Li Onboarding and runtime scripts are preserved. Latest reconciled HEAD requires new Chromium/WebKit, Mini App, auth, Postgres and Android CI.
- [x] Replace PWA-only course placeholder with layout-sized neutral skeletons and visible brand/nav; don't show account or Pro data before the map verifies owner.
- [x] PWA-only splash no longer hides the authenticated shell while waiting for the map, and nav remains inert until verified map or terminal auth/error state settles.
- [x] Unit regression tests check source isolation, ETag revalidation, 304, and non-course screens.
- [ ] Browser slow-network filmstrip and LCP/CLS measurements (baseline and after).
- [x] Independent Rating and Friends loading boundaries: in-flight deduplication, no premature empty state on locale re-render, per-section skeletons, and separate failure/retry paths.
- [x] Profile accuracy placeholder while its own API is pending; on successful response replace the placeholder without blocking the profile header, navigation, account controls or Pro gate.
- [x] Verified duplicate PWA Voice quota GET on locale re-render while the first request is pending; reuse a single in-flight Promise, then fetch fresh quota on a later visit. Chromium and WebKit mocked-route regression covers both cases; Telegram transport is unchanged.
- [x] Confirmed offscreen Profile repaint via course-progress refresh and post-onboarding Trial callback despite PWA lazy-render contract. PWA now defers both Profile paints until the Profile tab is active; Telegram Mini App behavior remains eager. Added Chromium/WebKit regression for initial onboarded Course and progress refresh. Run latest-head CI before release.
- [x] Source-verified account-switch failure: authenticated Voice status responses now identify the owner and both inline/standalone PWA Voice clients reject changed owner or 401 before displaying quota. Added API and Chromium/WebKit regression cases; latest-head CI is pending.
- [x] Code-confirmed PWA Voice empty-status failure: HTTP 503, malformed/missing quota and network rejection no longer leave the quota area silently hidden. It now has a localized independent loading/error/retry state; only browser PWA behavior changes, existing Telegram Voice requests stay untouched. Added Chromium/WebKit mocked HTTP failure-and-recovery regressions (latest-head CI pending).
- [x] Confirmed unbounded pending Voice GET after stalled network: PWA Voice quota now uses the existing 10-second `boundedSectionRequest` with an abortable fetch and the same section-local retry. Chromium/WebKit stalled-route regression advances a virtual browser clock, verifies retry, and confirms the next owner-verified response renders. Telegram Voice unchanged; latest-head CI pending.
- [x] Verified unnecessary initial PWA Practice DOM work: `renderAll()` previously built six offscreen Practice cards on the Course first paint, although `App.show("mashq")` already has a first-visit renderer. PWA now defers these cards until that first visit, retains Telegram eager behavior and locale refresh for previously mounted Practice, with real Chromium/WebKit behavioral assertions. This establishes avoided DOM work, not a measured LCP/p95 improvement.
- [ ] Split **additional optional course-map sub-sections** into independent API boundaries only after access/query dependency and row-lock analysis.
- [ ] Audit and convert genuinely offscreen images to responsive WebP/AVIF without regressing visible mascot/brand.
- [ ] All affected iPhone Safari flows with live-like latency, including auth replacement and Pro/lesson updates.

## Backend course-map template cache

- Cache only seven public, static level templates in bounded process memory. Key on file metadata so changed files invalidate automatically.
- Deep-copy for each request; apply all user data and entitlements **after** copying.
- Keep authenticated PWA POST map `no-store`, owner header and CSRF untouched.
- Do not cache a shared personalized response, payment status, or authentication credentials.
- Synthetic performance tests are useful for algorithmic changes but cannot replace production PostgreSQL p50/p95, query-plan inspection, or Safari timing.

## Release gate

No merge to `main` or production deployment until the latest targeted backend tests, real isolated PostgreSQL integration and PWA WebKit checks pass. Label incomplete UX work as incomplete rather than treating a skeleton alone as fully progressive API loading.


## Mandatory engineering workflow while CI runs

Do not idle while a CI workflow is pending. Inspect all changed code and direct callers/consumers in parallel: authentication and account ownership, Trial/Free/Pro entitlements, session/CSRF boundaries, request deduplication/cancellation, failure/retry and cache invalidation, Mini App and Android shared API contracts, and real frontend lifecycle behavior. Record findings with exact files/functions and add a focused regression test for any confirmed defect. Keep unverified tests **pending** (not passed) and keep all changes on a Draft PR until the final commit has green required checks.

An earlier CI failure traced to a browser test running at `about:blank` instead of `/iphone-pwa/course`; test routing was corrected without weakening PWA path guards.


## Backend performance master checklist

This is the **full scope for Backend + learner PWA**, not an instruction to install every listed technology. Each item requires a code-path audit, evidence of actual need, a minimal fix where justified, and an affected regression test. An unchecked item means **not yet accepted across the product**, even when a narrower course-map optimization has already shipped in this branch. Track measured before/after results and any justified "not needed" decision next to the relevant item; do not mark unchecked work complete based on a passing CI badge.

- [ ] **Baseline and bottlenecks:** map route-to-DB/service dependencies; measure cold/warm API p50/p95, SQL count/latency and relevant request errors, on controlled and production-like environments.
- [ ] **Duplicate and redundant work:** deduplicate equivalent in-flight reads per user/session/parameter, cancel obsolete queries where safe, avoid unnecessary DB/HTTP work on re-render; never dedupe writes across distinct intents.
- [ ] **N+1 SQL:** inspect actual slow endpoints and query plans; batch or eager-load only where the N+1 is demonstrated. Record before/after query counts.
- [ ] **PostgreSQL queries and indexes:** check filters, joins, sort order, SELECT only necessary columns and add indexes only after EXPLAIN ANALYZE / workload evidence; avoid unnecessary write overhead.
- [ ] **Pooling and transaction boundaries:** audit existing database connection pooling, leaked sessions and long-held locks; move network/CPU tasks outside transactions; preserve atomic business logic.
- [ ] **Pagination and bounded responses:** use cursor/keyset or page-based pagination appropriate to list stability; cap page size and response payload for histories, dictionaries, analytics and other long results.
- [ ] **HTTP efficiency and resilience:** validate timeouts, retry/backoff (only for safe/idempotent operations), explicit cancellation and failure states for every external service; independently executable requests should run concurrently with safe bounds.
- [ ] **Compression and static serving:** verify Brotli/Gzip delivery and CDN/browser caching rules, cache-control, compression ratios and correct MIME/ETag behavior; do not compress tiny/already-compressed bodies blindly.
- [ ] **Cache safely:** audit Cloudflare/CDN, browser and bounded in-process caches before suggesting Redis; define cache keys, TTL, owner isolation and invalidation. Never share auth, payments, Pro/Trial entitlements or private progress through public caches.
- [ ] **Deferred/background work:** profile slow synchronous tasks, use the existing safe queue/worker pattern where necessary, and handle retries, idempotency and user-visible status. Do not add a queue with no measured need.
- [ ] **AI response streaming:** evaluate first-token latency and product/client support before token streaming; ensure authorization, cancellation, safe markdown display and failure handling. Do not fake streaming.
- [ ] **Service footprint:** audit unused dependencies, excessive imports, event-loop blocking and server-to-PostgreSQL/network distance; consider load balancing or more app replicas only if capacity evidence demands it.
- [ ] **Observability:** collect route/SQL performance and slow-query diagnostics with bounded, privacy-safe labels; prefer existing instrumentation, adopt OpenTelemetry only if a gap is demonstrated. No tokens, prompts or student data in logs.
- [ ] **Capacity tests:** reproduce likely concurrent user load, check pool limits and lock contention, and verify shared API compatibility for Mini App and Android clients.

## PWA performance master checklist

The existing **Required: Initial Render & Progressive Loading** section remains mandatory. These additional items cover PWA surfaces beyond the initial course shell. Check them individually after validating the actual routes and components; do not claim product-wide coverage from one course test.

- [ ] **First paint / real shell:** visible brand, header, navigation, first viewport and safe geometry without waiting for slow API; only the data-bearing section shows an appropriately sized neutral skeleton.
- [ ] **Independent section lifecycle:** Course, Practice, Voice, Rating, Friends, Profile and every future learner PWA section implement separate loading, empty, error, retry and ready states; one failed/slow request must not blank other ready sections.
- [ ] **First-viewport imagery:** prioritize real HSK AI logo/mascot and visible essential assets; do not lazy-load LCP imagery. Preload/fetchpriority only with a measured LCP benefit.
- [ ] **Images and layout stability:** genuinely offscreen images/embeds lazy-load with reserved dimensions; compare responsive WebP/AVIF against originals for real bytes/quality; prevent CLS and broken mascot paths.
- [ ] **Requests and user input:** no duplicate in-flight GETs across tab/locale rerenders; cancel stale or no-longer-relevant requests, debounce search/autocomplete with abort of superseded work; never debounce payment/lesson submission writes.
- [ ] **Lists and heavy screens:** paginate API-backed data, virtualize long lists if profiling warrants it, and avoid eagerly rendering inactive tabs.
- [ ] **Code and asset delivery:** measure JS/CSS bundle weight, route-based splitting, delayed third-party scripts, self-hosted minimal font weights, static CDN, immutable hashed asset caching and safe service worker update/invalidation behavior. Assess SSR/SSG for eligible public pages only; never send personalized private course data via prerendered static HTML.
- [ ] **Rendering and update behavior:** eliminate unnecessary re-renders; parallelize independent reads, revalidate trusted in-memory cached state without flashing stale private content, use optimistic UI only for reversible non-sensitive changes.
- [ ] **Failures, access and sessions:** navigation is not dead on timeout; per-section retry is possible. Never display another account's data or imply Pro access while ownership/entitlement status is uncertain.
- [ ] **Device and real-user evidence:** test iPhone Safari/WebKit, reduced motion, slow network, low-end device, stale cookies/CSRF, account switching, session expiry; collect LCP/CLS/INP and error rates (with privacy-safe RUM if appropriate).

## Future feature invariant

**Permanent Definition of Done for all new or materially modified Backend APIs and learner PWA features, including features added after this performance project is merged:**

1. Read this document **before designing or coding** a new PWA screen, tab, card, search, list, image or backend API endpoint. New features inherit these constraints automatically; never wait for a later "performance optimization" task.
2. Every new learner PWA view must render a useful authorized shell before its slow data requests settle, with its **own** skeleton and loading/empty/error/retry states. Protect authentication first: an unverified session can show only public/non-personalized shell, not stale account data, Pro badges or lessons.
3. Prioritize visible logo/mascot/above-the-fold assets, defer genuinely offscreen resources, reserve image/card geometry, reduce request duplication and avoid blocking unrelated sections. Add debounce, pagination, virtualization, optimized image formats and code splitting where the usage profile warrants them.
4. Every new API must consider bounded response size, correct SQL/query count, transaction/pool behavior, timeout/cancellation, cache ownership and invalidation, and safe parallel work **at implementation time**. If not applicable, document the reason rather than adding a service or technology.
5. Do not change Android native code in this performance phase; preserve contracts consumed by Android, Telegram bot and Mini App. New shared APIs still require compatibility checks.
6. Preserve user isolation, CSRF/session checks, course progress, Trial/Free/Pro decisions, purchases, refunds and expiry. No optimistic entitlements and no public caching of private data.

## Performance acceptance for every future change

- In each PR changing Backend/PWA behavior, record the **affected routes/sections**, expected performance effect, cache/auth/privacy implications, and chosen measurements. Distinguish "not applicable" from "not checked".
- Include a focused regression test for each new feature or meaningful logic change. PWA tests must verify independent shell/skeleton/ready/failure/retry behavior and avoid extra API calls under slow-network, locale re-render and navigation when relevant. Backend tests must verify query count/ownership/timeout where relevant.
- Run the CI workflow `.github/workflows/backend-pwa-performance-contract.yml`. Its guard requires this document and permanent links in `AGENTS.md` / `AI_RULES.md`, and refuses Backend/PWA implementation changes without accompanying regression tests on pull requests and main integration (intermediate feature-branch pushes check the permanent policy without demanding a test in each small commit). PWA changes also run Chromium and WebKit shell/section regressions; applicable backend changes run targeted course-map tests.
- **CI is a guardrail, not proof of performance:** a test file being modified does not prove it covers every new component. Review the test assertions and use slow-network filmstrips, p50/p95, LCP/CLS/INP and database evidence to sign off the affected behavior.
- Do not silently turn incomplete measurements or failed checks into green checkboxes; a future feature is not finished merely because it renders or its PR CI passes.
