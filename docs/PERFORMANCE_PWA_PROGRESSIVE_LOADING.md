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

## Implementation / verification checkpoints

- [x] Identified course startup blocker: original shared source has a full-screen splash and a single `…` placeholder, and waits for the authenticated map before calling `renderAll`.
- [x] Keep the canonical shared `app/static/course-v3.html` byte-for-byte unchanged. Inject a PWA-only shell only after the existing verified browser-session gate.
- [x] Replace PWA-only course placeholder with layout-sized neutral skeletons and visible brand/nav; don't show account or Pro data before the map verifies owner.
- [x] PWA-only splash no longer hides the authenticated shell while waiting for the map, and nav remains inert until verified map or terminal auth/error state settles.
- [x] Unit regression tests check source isolation, ETag revalidation, 304, and non-course screens.
- [ ] Browser slow-network filmstrip and LCP/CLS measurements (baseline and after).
- [x] Independent Rating and Friends loading boundaries: in-flight deduplication, no premature empty state on locale re-render, per-section skeletons, and separate failure/retry paths.
- [x] Profile accuracy placeholder while its own API is pending; on successful response replace the placeholder without blocking the profile header, navigation, account controls or Pro gate.
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
