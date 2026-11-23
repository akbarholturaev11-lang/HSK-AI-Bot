# HSK AI — Performance audit acceptance: Backend and PWA

Historical scope **of the completed/older Backend + PWA-only work**: canonical backend, API, PostgreSQL, Cloudflare, Telegram Mini App shared assets and authenticated learner PWA. The older phase excluded `android/` changes, **but this restriction does not apply to the current owner-directed joint PWA + Android + Backend optimization initiative**. Use the evergreen goals/requirements document for current scope and plan all three together. Preserve native/Telegram shared API contracts.

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

- [x] **Current Rating/Reyting example:** replace the sparse first-rating loading blocks with layout-faithful podium/leaderboard placeholders and verify in-place crossfade by Chromium/WebKit filmstrip. This is **not** marked implemented by adding the policy/CI guard. **Filmstrip, task 1.3 (2026-11-23):** on both engines the placeholders show from the tab's first frame, pulse as one wave and settle in place. The podium stays at the same position in every frame, then fades in over 200 ms, and settles at once under reduced motion. Repeat opens show the placeholders again for about 160 ms: a finding for the owner (1.3 section below).

## Mandatory retrofit: ALL EXISTING learner PWA functions

This requirement is **retroactive**: every currently implemented learner PWA screen, widget, list, form, in-place layer and future feature must use its OWN layout-matched loading state, not a generic card. Specifically review Course, Practice (six cards), Voice (Panda, quota and CTA), Rating podium/Top 5/ranks, Friends, Profile avatar/accuracy/calendar/achievements, Settings, dictionary, mistakes, tests, lessons, checkout and notifications. Preserve all existing functions during this retrofit.

- [x] The newest Chromium 320px run still measured 9.4px for Practice row 6 after the earlier first-group fix; the second-group first row had also wrapped beyond its 68px reserve. At <=340px it now reserves 80px for that row. Keep the exact <=8px acceptance and check Chromium/WebKit on the new HEAD before signing off.
- [x] WebKit at 320px independently measured two additional 10px position differences with 80px reserved rows (ready rows were 77–78px). Adjusted only 320px first-group rows 1/2/4 to 78px (390px still reserves 80px on row 2, 430px remains 68px). Preserve the strict 8px acceptance and verify both engines on latest HEAD; no additional framework/feature changes.
- [x] First real Chromium geometry result exposed additional measured Practice text-wrap mismatches: at 320px the fourth-to-sixth card positions moved up to 39.4px, and at 390px 8.1px. Reserved measured 80px slots on the first Practice group only for rows whose verified text wraps at 320/390px, preserving 68px on the others and 430px. Geometry limit remains 8px; newest-head Chromium/WebKit rerun still pending.
- [x] Verified that three Practice placeholder CSS rules targeted a nonexistent `.pwa-practice-shell` parent while the actual element is `.pwa-mashq-shell`. Corrected the scope so six placeholders receive the same 68px row reserve and padding as the real Practice cards; added browser computed-style assertion. Real geometry acceptance still requires newest-head Chromium/WebKit CI.
- [x] Practice skeleton rows are explicitly NOT real `.row-card` interactive cards; six geometry-matched PWA placeholders remain static until the first verified Practice visit. Existing PWA first-visit deferred-card regression remains strict.
- [x] Replaced the four existing generic **initial** Practice, Voice, Rating and Profile loading shells with non-personalized visual compositions shaped like their ready screens. Rating also uses the captured podium/row geometry during its independent API pending phase and retains reserved slots on error/retry. No verified account/progress/Pro data is emitted by the shell. Browser first-paint structural and real Rating-geometry/regression assertions added. **CI and real-device geometry signoff still pending.**
- [x] Profile analytics pending/ready/error/retry now preserves the same two-ring grid geometry; verified PWA response updates only the independent accuracy region, not Profile header, settings or carousel. Added real-browser box/identity regression; newest-head CI pending.
- [x] Added real Playwright geometry coverage for existing Practice screen: hold authenticated map unresolved, show six separate non-private placeholders, settle the first actual six cards, compare title, header, both sections, each card and nav at 320/390/430 px in Chromium/WebKit and reduced-motion. Test added; newest-head CI remains pending.
- [x] Measured Voice ready-panel mismatches in Chromium: first-paint heading was 8px taller because nested `.htop` missed the real-screen 6px top padding; Call placeholder width/height 190×48 differed from actual ~167×45. Corrected both only for PWA initial shell. The existing 620ms Panda entrance is retained; visual transform is measured after completion and reduced-motion immediately. Strict 8px geometry remains unchanged; newest-head CI pending.
- [x] Added real Voice static→verified-panel geometry regression at 320/390/430px (Chromium/WebKit, reduced-motion), capturing title/Panda/description/quota/Call button/nav while independent quota GET is pending and then verified. No static placeholder visibility or unverified owner data shortcuts; CI validation pending.
- [x] Added measured Profile static→verified DOM anchor regression (320/390/430, Chromium/WebKit, reduced motion): header, avatar, hero, friends row, two-ring accuracy container, calendar, achievements, bottom nav. Analytics GET stays pending to prove parent Profile settles independently and trial access remains correct; newest-head CI pending.
- [x] Real Chromium/WebKit initial Profile geometry exposed calendar 72px too tall and achievement cards 18–26px too short at 320/390/430px. Matched ONLY the unverified PWA skeleton calendar and achievement reserves to the existing ready DOM heights; left real calendar content and Pro/Trial/profile API behavior untouched. Latest geometry CI still pending.
- [x] Push Settings CI identified JS truthy-object coercion (`pushSupported()` could return the `Notification` object) in a strict Node DOM harness. Normalize capability result to a boolean; browser-disabled/pending guard, session owner verification and permission flow unchanged. Added pending synthetic click no-mutation checks; update content-addressed PWA script version to avoid stale Service Worker assets. Latest CI pending.
- [x] Short (1–4 person) verified PWA Rating lists preserve the already-reserved Top-5 header before the first real leaderboard row; Telegram Mini App keeps its prior five-user threshold. Added Chromium/WebKit 320/390/430px first-row geometry regression; zero-user empty state still needs independent acceptance, and newest CI is pending.
- [x] Authenticated PWA Rating at **zero users** now keeps the actual podium/Top-5/empty-result layout with a 305px reserved neutral content region (no fabricated users, no infinite spinner). Telegram Mini App retains its prior empty state. Extended 320/390/430px real browser geometry regression for 0/1/4 users; newest CI pending.
- [x] Verify EVERY existing PWA screen at 320/390/430px on Chromium/WebKit, reduced motion, slow/failed requests, partial/ready transitions, account switch and real mobile Safari. Compare actual DOM anchors and CLS; mere presence of placeholder does not close a screen. **Closed by task 1.3 (2026-11-23), with the rest owned:**
  - Timed on Chromium and WebKit on the slow-network lab profile: the launch and every root tab at 320/390/430 px; every layer, practice page and session at 390 px (baselines below). The geometry regressions hold the DOM anchors at the three widths.
  - Reduced motion, failed requests and account switch, per screen: the condition matrix (OpenSpec task 2.13) names each one's test or owning task.
  - Real mobile Safari: owner device QA (task 5.1).
- [x] Push status owner revalidation changed `iphone-pwa-notices.js` bytes; the Service Worker cache-first script reference in `course-v3.html` now includes the exact new Git-blob content digest (`?v=20261109-43bdd79d0370`) so installed PWA clients cannot keep stale script bytes. Existing asset-version CI contract retained.
- [x] Confirmed existing iPhone PWA Push status had a late-response owner-switch gap (unlike Inbox feed). After reading Push status, revalidate current cookie session owner before setting any Push UI; redirect on changed owner. Added deterministic delayed-status account-switch regression to `tests/test_pwa_notices_ui.js`. Latest-head CI pending.
- [x] Push Settings status GET failure now leaves a localized error in the reserved Push panel, with a working in-place retry CTA that only rechecks owner/Push state (no automatic permission prompts, subscribe or payment write). Held-status/fail-once Node regressions cover pending→error→retry→verified ready; newest-head CI pending.
- [x] Confirmed Push Settings initially rendered `Off` from an unset/stale local state before authenticated server status arrived. It now shows a localized pending status and disabled, reserved CTA slot until the owner-verified GET settles, without requesting iOS system permissions automatically. Added held-request Node UI regression; checkout/entitlements unchanged. Latest-head CI pending.
- [ ] Audit the current in-place embedded resources, Settings, Friends, notifications, Pro checkout, lesson dialogs, long lists and dynamically added widgets separately: they are not covered just because parent tab has a skeleton.
- [x] Record actual before/after filmstrip, LCP/CLS/INP and API/SQL p50/p95 measurements. Keep unverified product-wide acceptance open. **Before: task 1.3 (below):** filmstrip, LCP, CLS and the INP proxy. Each group 2 task records its after with the same harness and targets. API p50/p95 is in the backend tasks (4.1–4.4).

## Implementation / verification checkpoints

- [x] Identified course startup blocker: original shared source has a full-screen splash and a single `…` placeholder, and waits for the authenticated map before calling `renderAll`.
- [x] Reconciled against main `e5026949` and later `9b75f132` (Foundation audio success and PWA transient map retry retained): **one authoritative native PWA first paint** remains in shared `app/static/course-v3.html`, guarded by PWA path/CSS, while Telegram retains its original splash. Removed the redundant response-side injected skeleton from `pwa_auth.py`. The authenticated backend route still owns session/CSRF and never injects user/Pro state into static shell. Main Li Onboarding and runtime scripts are preserved. Latest reconciled HEAD requires new Chromium/WebKit, Mini App, auth, Postgres and Android CI.
- [x] Replace PWA-only course placeholder with layout-sized neutral skeletons and visible brand/nav; don't show account or Pro data before the map verifies owner.
- [x] PWA-only splash no longer hides the authenticated shell while waiting for the map, and nav remains inert until verified map or terminal auth/error state settles.
- [x] Unit regression tests check source isolation, ETag revalidation, 304, and non-course screens.
- [x] Browser slow-network filmstrip and LCP/CLS measurements (baseline and after). Baseline: task 1.3 (below). After: each group 2 task.
- [x] Verified Friends API failure discarded reserved invite/summary/row placeholders on PWA; now failed Friends GET and local Retry retain the same independent geometry while preserving Telegram's existing error UI. Added Chromium/WebKit mock-503 → error-anchor → retry → success regression. Latest-head CI pending.
- [x] Independent Rating and Friends loading boundaries: in-flight deduplication, no premature empty state on locale re-render, per-section skeletons, and separate failure/retry paths.
- [x] Profile accuracy placeholder while its own API is pending; on successful response replace the placeholder without blocking the profile header, navigation, account controls or Pro gate.
- [x] Verified duplicate PWA Voice quota GET on locale re-render while the first request is pending; reuse a single in-flight Promise, then fetch fresh quota on a later visit. Chromium and WebKit mocked-route regression covers both cases; Telegram transport is unchanged.
- [x] Verified the Course XP goal ring previously called both `App.show('profile')` and `renderProfile()`, even though navigation already renders Profile; now the click performs one render. Added a real Chromium/WebKit synchronous call-count and screen-navigation regression; no access/Pro/Trial code changed. Latest-head CI pending.
- [x] Confirmed offscreen Profile repaint via course-progress refresh and post-onboarding Trial callback despite PWA lazy-render contract. PWA now defers both Profile paints until the Profile tab is active; Telegram Mini App behavior remains eager. Added Chromium/WebKit regression for initial onboarded Course and progress refresh. Run latest-head CI before release.
- [x] Source-verified account-switch failure: authenticated Voice status responses now identify the owner and both inline/standalone PWA Voice clients reject changed owner or 401 before displaying quota. Added API and Chromium/WebKit regression cases; latest-head CI is pending.
- [x] Code-confirmed PWA Voice empty-status failure: HTTP 503, malformed/missing quota and network rejection no longer leave the quota area silently hidden. It now has a localized independent loading/error/retry state; only browser PWA behavior changes, existing Telegram Voice requests stay untouched. Added Chromium/WebKit mocked HTTP failure-and-recovery regressions (latest-head CI pending).
- [x] Confirmed unbounded pending Voice GET after stalled network: PWA Voice quota now uses the existing 10-second `boundedSectionRequest` with an abortable fetch and the same section-local retry. Chromium/WebKit stalled-route regression advances a virtual browser clock, verifies retry, and confirms the next owner-verified response renders. Telegram Voice unchanged; latest-head CI pending.
- [x] Verified unnecessary initial PWA Practice DOM work: `renderAll()` previously built six offscreen Practice cards on the Course first paint, although `App.show("mashq")` already has a first-visit renderer. PWA now defers these cards until that first visit, retains Telegram eager behavior and locale refresh for previously mounted Practice, with real Chromium/WebKit behavioral assertions. This establishes avoided DOM work, not a measured LCP/p95 improvement.
- [ ] Split **additional optional course-map sub-sections** into independent API boundaries only after access/query dependency and row-lock analysis.
- [ ] Audit and convert genuinely offscreen images to responsive WebP/AVIF without regressing visible mascot/brand.
- [ ] All affected iPhone Safari flows with live-like latency, including auth replacement and Pro/lesson updates.

## Repeatable lab profile (learner PWA)

One command measures the learner PWA under the same conditions every time.
Use it for every before/after claim (OpenSpec `perf-pwa-android-backend`,
task 1.1):

```bash
.venv/bin/python scripts/measure_pwa_lab.py --out lab.json
```

- **Fixture:** `flow_fixture`, the existing e2e `ScreenPage` (UZ, onboarded,
  Free) extended for task 1.2, served over real local HTTP.
  - The course, practice and Voice HTML are built by production's own
    builders in `app/api/pwa_auth.py`; the exam by the exam service.
  - `--parts` selects what runs; the default `all` takes about 41 minutes.
    - `launch`, `flows` (the 1.2 learner actions at `--flow-widths`, 390)
      and `entry` (the entry pages);
    - the task 1.3 parts: `tabs` (at `--tab-widths`, 320/390/430),
      `layers`, `search`, `swipe`, `answers`, `pro`, `refresh`, `blocking`
      (lab-only removal of each `<head>` resource, `--blocking-runs` cold
      loads each), `film` and `sdk`.
  - Every action records the console errors and uncaught exceptions it
    raised.
  - No production account or secret is used.
  - The only outside request is one fetch per run of the cdnjs icon
    stylesheet. It is then served like every other file.
- **Network:**
  - One shared link, shaped on the server: 150 ms to the first byte of each
    response, 1.6 Mbps down. Chromium and WebKit see the same network.
  - TLS setup is not modelled. Real-user launch timing (task 1.4) covers it.
- **Delivery mirrors production** (`app/main.py`, `app/api/pwa_auth.py`):
  - gzip for every body of 1 KB or more;
  - HTML: `private, no-cache` plus ETag/304;
  - `immutable` for versioned files, `/assets/` and the offline word-audio
    scripts;
  - `no-store` for API answers;
  - the real service worker.

  The run stops if the browser does not receive these headers.
  `tests/test_measure_pwa_lab.py` pins the rules in the CI guard. On
  2026-11-22, all 38 static URLs of a cold launch matched production's
  `Cache-Control` and `Content-Encoding`.
- **Browsers:**
  - Chromium with a 4× CPU slowdown. Playwright cannot slow WebKit's CPU,
    so WebKit runs at full speed.
  - 320, 390 and 430 × 844 px, DPR 2, touch.
- **Cold and warm:**
  - Cold is a new browser context.
  - Warm re-navigates the same page, so the HTTP cache and the service
    worker apply. Playwright's WebKit keeps its HTTP cache only within one
    page.
  - The warm launch is measured after the worker's warm-up and after the
    first launch under the worker's control, which is reported as the
    takeover.
  - An action part starts in a first session. The worker's warm-up is held
    back, so the files it would cache are not cached yet. `layers` and
    `pro` also open their layers as a returning learner, after the warm-up;
    `refresh` runs only that way.
- **Metrics:**
  - Recorded inside the page from navigation start: FCP, LCP, CLS
    (`unsupported` where the engine has no entry type), course-ready
    (`MAP.authenticated`) and response end.
  - Recorded at the server: network KB and requests.
  - Each figure is the median of three cold/warm pairs.
- **Not covered:** a real iPhone, a weak Android phone and production
  latency. Real-user timing and owner device QA cover those.

**Launch baseline, 2026-11-22.** Measured at `fbbdfde9` (main `50231bee`
plus plan docs only). Each figure is the median of 6 launches (two full
runs). Times in ms, sizes in KB.

| Engine | Width | Cold FCP | Cold LCP | Cold course-ready | Cold KB | Warm FCP | Warm course-ready | Warm KB |
|---|---|---|---|---|---|---|---|---|
| Chromium 153 (4× CPU) | 320 | 1282 | 3682 | 3432 | 608–646 | 288 | 665 | 4.4 |
| Chromium 153 (4× CPU) | 390 | 1238 | 3790 | 3578 | 608–646 | 296 | 686 | 4.4 |
| Chromium 153 (4× CPU) | 430 | 1242 | 3844 | 3618 | 646 | 302 | 702 | 4.4 |
| WebKit 26.6 | 320 | 2190 | 2470 | 3697 | 647 | 266 | 682 | 4.4 |
| WebKit 26.6 | 390 | 2178 | 3683 | 3658 | 647 | 260 | 682 | 4.4 |
| WebKit 26.6 | 430 | 2156 | 3712 | 3682 | 647 | 256 | 665 | 4.4 |

- **Repeatability:** the two runs agree within 7.5% on FCP and course-ready.
- **CLS:**
  - Chromium: ≤0.011 in all 36 launches.
  - WebKit: has no layout-shift entries, so the WebKit geometry regressions
    remain its stability check.
- **Warm launch:** the HTML answers 304, and every asset comes from cache.
- **Chromium's cold size varies by 38.5 KB.** The icon stylesheet is a
  non-blocking `media=print` load with low priority, and it sometimes
  finishes after the measurement window.
- **Per-action baselines** (tab switch, layers, search, swipe-back, lesson
  open, exercise advance) are recorded in task 1.3, below.

**Action readings, 2026-11-23 (task 1.2).** Measured at `ff244e04` with
`--parts flows,entry`, at 390 px, as the median of 3 runs per engine. These
are the first readings. Task 1.3 adds a second run and the targets.

How the actions are timed:
- **Ready:** from the tap (pointerdown) to the ready state, plus one frame,
  so the change is painted.
- **Parent only:** how long the practice entry was the only thing visible,
  before the page frame was revealed.
- **Panda:** how long the lesson-entry or study-preparing panda was
  visible. Every run that waits showed it.

Times in ms; Chromium has the 4× CPU slowdown.

| Action | Chromium ready | Chromium parent only | Chromium panda | WebKit ready | WebKit parent only | WebKit panda |
|---|---|---|---|---|---|---|
| Lesson open → first card | 828 | — | 804 | 826 | — | 812 |
| Exercise advance | 27 | — | 0 | 26 | — | 0 |
| Lesson finish → result | 385 | — | 0 | 228 | — | 0 |
| Recognition, first / repeat | 1733 / 947 | 1731 / 933 | 1718 / 920 | 1934 / 950 | 1913 / 933 | 1898 / 918 |
| Pronunciation, first / repeat | 1004 / 831 | 990 / 819 | 975 / 806 | 1047 / 834 | 1031 / 817 | 1015 / 802 |
| Memorize, first / repeat | 1115 / 716 | 1112 / 708 | 1105 / 691 | 3053 / 747 | 3020 / 730 | 3017 / 719 |
| Test centre, first / repeat | 285 / 203 | 271 / 190 | 257 / 176 | 283 / 201 | 268 / 189 | 252 / 174 |
| Test exam start | 241 | — | 222 | 279 | — | 250 |
| Mistakes, first / repeat | 604 / 522 | 596 / 507 | 581 / 493 | 612 / 556 | 597 / 538 | 581 / 522 |
| Mistakes review start | 190 | — | 170 | 196 | — | 165 |
| Voice → opening line, first / repeat | 1818 / 906 | 804 / 300 | 793 / 286 | 1763 / 879 | 790 / 338 | 775 / 323 |

First paint of pages opened directly. Ready means:
- **Login:** the provider buttons are shown.
- **Li onboarding:** the first scene and its button are shown.
- **Course onboarding:** the start button is shown.

| Page | Chromium FCP / ready, cold | Chromium warm | WebKit FCP / ready, cold | WebKit warm |
|---|---|---|---|---|
| Login | 432 / 819 | 396 / 751 | 476 / 864 | 378 / 749 |
| Li onboarding | 528 / 770 | 264 / 483 | 771 / 796 | 288 / 500 |
| Course onboarding | 744 / 1021 | 220 / 260 | 1049 / 1049 | 279 / 278 |

What the readings show, as input for 1.3 and group 2:
- **Practice pages reveal only when ready.** The parent-only time is almost
  the whole wait, and the panda shows for all of it. That includes the Test
  centre (≈0.25 s) and both session starts (0.17–0.25 s), which are under
  the 300 ms panda bar (task 2.5).
- **Lesson open:** the panda shows for ≈0.8 s, which includes the 720 ms
  minimum.
- **Slowest first opens:**
  - Recognition: 1.7–1.9 s.
  - Memorize on WebKit: 3.1 s, against 1.1 s on Chromium. It has no PWA
    tile today.
  - Voice: 1.8 s to the opening line. The frame is revealed at 0.8 s; the
    rest is the microphone and the session start.
- **Not modelled:**
  - first-time TTS synthesis (a cached phrase is served);
  - CSP on the three entry pages;
  - the live voice relay (fake microphone, `live_available: false`).

**Baselines and targets, 2026-11-23 (task 1.3).** Measured on the app code
of `ad11cc71` with `--parts all` in two full runs, plus two runs of
`--parts refresh,pro` (below). Each figure is the median of 6 runs (3 per
run), at 390 px unless stated. The launch and the tabs were also measured at
320 and 430 px. These readings replace the 1.2 table above as the baseline.

How the runs were set up:
- **First session:** each action part starts from a cold launch whose icon
  font has arrived. Its context drops the service worker's background
  warm-up, so a first open means "files not cached yet" on a quiet link.
  - In 1.2, the icon font and the warm-up shared the link with the actions.
    That is why 1.2 shows WebKit Memorize at 3.1 s and Recognition at
    1.7–1.9 s: on a quiet link they take 1.04 s and 1.43–1.60 s.
- **Returning learner:** the warm-up is done, and one launch has already run
  under the worker's control. Dictionary, Phrases, checkout and trial are
  opened in this state too. Pull-to-refresh is measured only in this state.
- Times are in ms. Chromium has the 4× CPU slowdown.
- **Repeatability:** the two full runs agree within 12.6% on every reading of
  100 ms or more, and most agree within 5%. Readings under 100 ms agree
  within 10 ms. The two `refresh,pro` runs agree within 4.1%.
- **Errors:** no console or page error in any action, launch or part, on
  either engine. This is the "no new error" baseline for every group 2
  package.
  - One earlier run, which did not wait for the worker to take control, logged
    a WebKit error `…/iphone-pwa/sw.js due to access control checks.` A pull
    had reloaded the page while the worker was registering.
  - The registration already catches its failure; WebKit still reports the
    aborted fetch.

How each target is set (design decision 12). The harness computes it for
every action and engine (`with_targets` in `scripts/measure_pwa_lab.py`):
- **Bounds:**
  - an interaction (tap to the first visible response): 200 ms;
  - an opening (tap to a usable screen): 1000 ms;
  - a cold launch to the shell: 1500 ms;
  - a warm launch and refresh-to-settled have no bound: they keep their
    baseline.
- **Inside its bound,** a reading may not get more than 10% worse: the target
  is the baseline + 10%, never above the bound.
- **Outside its bound,** the target is the bound. The owning task reaches it,
  or records an owner-approved exception with the evidence. These readings
  are **bold** below.

**Launch.**

| Engine | Width | Cold shell (FCP) | Cold course ready | Cold icons visible | Warm FCP | Warm course ready | Warm icons | Cold shell target |
|---|---|---|---|---|---|---|---|---|
| Chromium | 320 | 1198 | 3564 | 8338 | 256 | 618 | 285 | 1318 |
| Chromium | 390 | 1194 | 3544 | 8198 | 240 | 602 | 268 | 1313 |
| Chromium | 430 | 1198 | 3579 | 8175 | 252 | 592 | 272 | 1318 |
| WebKit | 320 | **2152** | 3679 | 8744 | 212 | 612 | 251 | 1500 |
| WebKit | 390 | **2157** | 3613 | 8662 | 197 | 591 | 238 | 1500 |
| WebKit | 430 | **2138** | 3666 | 8740 | 209 | 611 | 252 | 1500 |

- **LCP element:** the Foundation card's description
  (`.foundation-entry .ft small`), at ≈3.8 s on Chromium and 3.65–3.70 s
  on WebKit. On WebKit at 320 px it is `body.hsk-scene-page`, at 2.43 s.
- **Warm launch target:** no bound, so each warm reading's target is that
  reading + 10%.
- **CLS:** 0.0001 on Chromium. WebKit has no layout-shift entries.
- **Size:**
  - cold: 662 KB in 46–48 requests;
  - warm: 16.9 KB in 8–9 requests, with the HTML answered 304.
- **Chromium's cold first paint has two modes:** 0.91–0.96 s or
  1.18–1.35 s, with a median of 1.19 s. It is fast only when the four
  character scripts arrive in time (head table below).
- **Warm-up:** after a first launch, the worker's warm-up downloads
  1586 KB (Chromium) or 1879 KB (WebKit). It finishes 24.2–24.4 s or
  30.6–30.7 s after the launch started.
- **Takeover:** the first launch under the worker's control costs 272–280 ms
  and 14 KB on Chromium, and 903–914 ms and 133 KB on WebKit. WebKit fetches the
  course's files again, through the worker. The warm readings above are the
  launches after it.
- **Icons on a first launch:**
  - They appear at 8.2 s (Chromium) and 8.7 s (WebKit), 4.6–5.1 s after the
    course is ready.
  - The icon stylesheet does not block, but its font is one 870 KB woff2 for
    the whole Tabler set. The course uses about 74 of its icons.
  - The `@font-face` has no `font-display`. Until the font arrives, each icon
    slot is empty. After the font's 3 s block period, each one shows a "□"
    box (1.3 screenshots).
  - On a warm launch the icons are visible at 0.24–0.29 s.

**Launch filmstrip, 390 px.** It records the course screen's state on every
frame, with the map request answered at once or held 3 s.

| Engine | Launch | Map | First frame | Shell skeleton | Course content | Icons | Blank or "…" frames |
|---|---|---|---|---|---|---|---|
| Chromium | cold | at once | 194 | 1184 | 3572 | 8190 | none |
| Chromium | cold | held 3 s | 194 | 1142 | 6494 | 8186 | none |
| Chromium | warm | at once | 161 | 234 | 616 | 280 | none |
| Chromium | warm | held 3 s | 164 | 240 | 3646 | 296 | none |
| WebKit | cold | at once | 234 | 2470 | 4747 | 11150 | none |
| WebKit | cold | held 3 s | 240 | 2152 | 6650 | 8648 | none |
| WebKit | warm | at once | 166 | 219 | 576 | 234 | none |
| WebKit | warm | held 3 s | 163 | 208 | 3580 | 226 | none |

- Before the first paint, the browser keeps showing the previous screen:
  blank in Playwright, the launch image on a phone. The filmstrip is judged
  from the first paint.
- From the first paint until the course is ready, every frame shows the
  shell skeleton, on both engines, cold and warm, with the map answered at
  once or held 3 s.

**Actions and targets, 390 px.** The reading is "ready" unless the row says
otherwise.

| Action | Chromium | WebKit | Target Chromium / WebKit | Owner |
|---|---|---|---|---|
| Lesson open → first card | 828 | 810 | 911 / 891 | 2.7 |
| Exercise advance | 29 | 26 | 32 / 29 | 2.7 |
| Lesson finish → result | 337 | 231 | 371 / 254 | 2.7 |
| Recognition, first | **1432** | **1600** | 1000 / 1000 | 2.8 |
| Recognition, repeat | 838 | 854 | 922 / 939 | 2.8 |
| Pronunciation, first | 897 | 918 | 987 / 1000 | 2.8 |
| Pronunciation, repeat | 842 | 848 | 926 / 933 | 2.8 |
| Memorize, first | 972 | **1042** | 1000 / 1000 | 2.8 |
| Memorize, repeat | 678 | 679 | 746 / 747 | 2.8 |
| Test centre, first | 277 | 282 | 305 / 310 | 2.8 |
| Test centre, repeat | 202 | 200 | 222 / 220 | 2.8 |
| Mistakes centre, first | 596 | 614 | 656 / 675 | 2.8 |
| Mistakes centre, repeat | 521 | 517 | 573 / 569 | 2.8 |
| Voice → opening line, first | **1750** | **1723** | 1000 / 1000 | 2.8 |
| Voice → opening line, repeat | 946 | 862 | 1000 / 948 | 2.8 |
| Test exam start | 240 | 280 | 264 / 308 | 2.8 |
| Mistakes review start | 190 | 196 | 209 / 216 | 2.8 |
| Dictionary, first session | **7462** | **8557** | 1000 / 1000 | 2.4 |
| Dictionary, returning learner | 346 | 264 | 381 / 290 | 2.4 |
| Dictionary, repeat | 30 | 32 | 33 / 35 | 2.4 |
| Phrases, first session | 870 | 883 | 957 / 971 | 2.4 |
| Phrases, returning learner | 648 | 624 | 713 / 686 | 2.4 |
| Phrases, repeat | 54 | 31 | 59 / 34 | 2.4 |
| Search 学, slowest keystroke | 88 | 24 | 97 / 26 | 2.4 |
| Search xue, slowest keystroke | 26 | 30 | 29 / 33 | 2.4 |
| Search kitob, slowest keystroke | 27 | 30 | 30 / 33 | 2.4 |
| Inbox, first | 346 | 354 | 381 / 389 | 2.3 |
| Inbox, repeat | 355 | 356 | 391 / 392 | 2.3 |
| Settings, first / repeat | 30 | 30 | 33 / 33 | 2.6 |
| Swipe-back from a layer, drag first frame | 28 | 23 | 31 / 25 | 2.5 |
| Swipe-back from a root tab, drag first frame | 24 | 54 | 26 / 59 | 2.5 |
| Pull-to-refresh, Course: first frame | **420** | **466** | 200 / 200 | 2.10 |
| Pull-to-refresh, Reyting: first frame | **426** | **480** | 200 / 200 | 2.10 |
| Pull-to-refresh, Profil: first frame | **426** | **480** | 200 / 200 | 2.10 |
| Pull-to-refresh, Course: settled | 1936 | 1968 | 2130 / 2165 | 2.10 |
| Pull-to-refresh, Reyting: settled | 2028 | 2132 | 2231 / 2345 | 2.10 |
| Pull-to-refresh, Profil: settled | 2060 | 2160 | 2266 / 2376 | 2.10 |
| Personal review answer, server now | 184 | 190 | 200 / 200 | 2.11 |
| Personal review answer, server held 1 s | **1192** | **1198** | 200 / 200 | 2.11 |
| Mistakes review answer, server now | 192 | 198 | 200 / 200 | 2.11 |
| Mistakes review answer, server held 1 s | **1191** | **1196** | 200 / 200 | 2.11 |
| Limit/Pro sheet, first: plans with an active pay button | 364 | 355 | 400 / 391 | 2.12 |
| Limit/Pro sheet, repeat | 190 | 195 | 209 / 215 | 2.12 |
| Checkout, first session: child first paint | 451 | **1310** | 496 / 1000 | 2.12 |
| Checkout, returning learner: child first paint | 193 | 188 | 212 / 207 | 2.12 |
| Trial, first session: child first paint | 498 | 818 | 548 / 900 | 2.12 |
| Trial, returning learner: child first paint | 270 | 513 | 297 / 564 | 2.12 |
| Login, cold: first paint / ready | 398 / 799 | 434 / 862 | 879 / 948 | new item |
| Login, warm: first paint / ready | 376 / 726 | 364 / 754 | 799 / 829 | new item |
| Li onboarding, cold: first paint / ready | 484 / 787 | 758 / 792 | 866 / 871 | new item |
| Li onboarding, warm: first paint / ready | 270 / 486 | 288 / 514 | 535 / 565 | new item |
| Course onboarding, cold: first paint / ready | 700 / **1008** | 1056 / **1056** | 1000 / 1000 | new item |
| Course onboarding, warm: first paint / ready | 216 / 268 | 278 / 277 | 295 / 305 | new item |

- Every action was measured in all 6 runs on both engines; none is
  unmeasured.
- The entry pages are opened directly. Their target applies to "ready": the
  provider buttons (Login), the first scene and its button (Li onboarding),
  the start button (Course onboarding).
- No task owns the entry pages: "new item" means a reading outside its bound
  becomes a new item, as Course onboarding cold does (findings below).

Tab switches at 320, 390 and 430 px (tap to the tab's first frame):

| Tab | Chromium 320 / 390 / 430 | WebKit 320 / 390 / 430 |
|---|---|---|
| Course, first | 48 / 48 / 50 | 60 / 58 / 62 |
| Course, repeat | 46 / 43 / 43 | 48 / 50 / 48 |
| Mashq, first | 54 / 58 / 55 | 32 / 32 / 28 |
| Mashq, repeat | 28 / 26 / 26 | 26 / 26 / 27 |
| AI Voice, first | 29 / 29 / 30 | 31 / 31 / 32 |
| AI Voice, repeat | 30 / 30 / 30 | 32 / 31 / 32 |
| Reyting, first | 30 / 29 / 28 | 35 / 36 / 36 |
| Reyting, repeat | 29 / 30 / 29 | 30 / 31 / 32 |
| Profil, first | 42 / 40 / 40 | 34 / 32 / 33 |
| Profil, repeat | 30 / 28 / 29 | 35 / 34 / 32 |

Every tab is inside the 200 ms bound at every width. Its target is the
reading + 10%, per width (2.5).

**What each parser-blocking `<head>` resource costs the cold first paint**
(390 px; lab-only removal; the median of 10 cold loads per variant, 5 per
full run):

| Removed | Chromium FCP | Saves | WebKit FCP | Saves |
|---|---|---|---|---|
| Nothing | 1210 | — | 2117 | — |
| `hsk-character-pack.js` | 1212 | −2 | 2107 | 10 |
| `hsk-character-motion.js` | 1198 | 12 | 2108 | 9 |
| `hsk-study-preparing.js` | 1192 | 18 | 2116 | 1 |
| `hsk-lesson-presentation.js` | 1200 | 10 | 2114 | 3 |
| Each of the other nine stylesheets | 1148–1240 | −30 to 62 | 2086–2122 | −5 to 31 |
| `desktop-download.css` | 1062 | 148 (see below) | 2100 | 17 |
| The four character scripts | 1012 | **198** | 2038 | 79 |
| The ten stylesheets | 536 | 674 | 1690 | 427 |
| Everything above | 472 | 738 | 2248 | −131 |

- **No single file costs 100 ms.**
  - `desktop-download.css` only looks like it does. Chromium's first paint
    has two modes, and 5 of that variant's 10 loads landed in the fast mode,
    against 3 of 10 with nothing removed.
  - Its download ends at 716 ms, long before the character scripts
    (1160 ms), so it is not what the paint waits for.
- **The four character scripts, together, cost 198 ms on Chromium:**
  without them, 24 of 25 cold loads across the five 1.3 runs paint in the
  fast mode. On WebKit they cost 79 ms. This is the evidence for 2.9: the
  scripts move as one group, or not at all.
- **The stylesheets style the shell,** so they stay on the first-frame path.
- **WebKit's 1500 ms target cannot be reached by moving head resources:**
  - with every stylesheet removed, it still paints at 1.69 s;
  - with everything removed, at 2.25 s;
  - its first paint comes 0.7 s before the HTML finishes (2.9 s), so it is
    not waiting for the whole document either (findings below).

**Embedded layers, first open** (child = the page in the layer's frame):

| Layer | State | Engine | Child's first paint shows | Child first paint | Child content | Cover removed | Ready |
|---|---|---|---|---|---|---|---|
| Dictionary | first session | Chromium | empty list | 604 | 1690 | 7446 | **7462** |
| Dictionary | first session | WebKit | empty list | 2617 | 2617 | 8552 | **8557** |
| Dictionary | returning | Chromium | empty list | 210 | 314 | 334 | 346 |
| Dictionary | returning | WebKit | content | 210 | 210 | 246 | 264 |
| Phrases | first session | Chromium | skeleton | 407 | 779 | 394 | 870 |
| Phrases | first session | WebKit | skeleton | 418 | 876 | 418 | 883 |
| Phrases | returning | Chromium | skeleton | 203 | 586 | 200 | 648 |
| Phrases | returning | WebKit | skeleton | 181 | 620 | 182 | 624 |

- **Dictionary, first session:** the child shows its words at 1.7 s
  (Chromium) and 2.6 s (WebKit). The parent's cover hides them until the
  frame's `load` event at 7.4 s or 8.6 s. That event waits for
  `hsk-extra.js` (strokes and examples, 1.1 MB gzip), which the page loads
  `async` so that the list can show first. This is the cover that 2.4
  replaces.
- **Dictionary's first child paint is an empty list,** not a skeleton.
  The row placeholders that 2.4 adds (decision 5) fill it.
- **Repeat opens** remove the cover in 14–50 ms and are ready in 30–54 ms.
- **The 150 ms anti-flash window (decision 5) holds:**
  - repeat opens never reach it;
  - a returning learner's first open hands over to the child at 180–210 ms,
    so the cover's bars would show for at most 60 ms before the child's
    matching skeleton.
- **Inbox** shows its loading text for 320–328 ms on the first open and
  again on the repeat open. It is ready at 346–356 ms (2.3).

**Skeletons on a fast open** (how long placeholders stay visible, and whether
their pulse is one synchronized wave):
- **Rating:**
  - The first open shows the placeholders for 152–169 ms, at all three
    widths on both engines. The content settles at 193–215 ms.
  - Every repeat open shows them again, for 150–166 ms (findings below).
  - The 28 placeholders pulse as one wave: one animation
    (`hsk-pwa-layout-pulse`) with no phase spread.
  - The content settles in place. In every frame from skeleton to content,
    the podium stays 64 px from the top. Then it fades from 0.82 to full
    opacity over 200 ms, on both engines. Under reduced motion it settles at
    once. (A per-frame probe at 390 px.)
- **Profile:** the first open shows its 2 placeholders for 163–176 ms, as
  one wave. The repeat open shows none.
- **Pro sheet:** its loading state (`.hip-skeleton` or `.hip-loading`) shows for
  286–324 ms on the first open, and again for 146–162 ms on every repeat open
  (2.12, decision 16).
- The Test and Mistakes centres reveal only when they are ready (1.2), so
  there is nothing to flash yet. Their skeletons come in 2.8.

**Other readings:**
- **Search:**
  - the slowest keystroke is ≤30 ms, except the hanzi query on Chromium
    (88 ms);
  - the slowest event, the INP proxy, is ≤64 ms on Chromium and 16 ms on
    WebKit, the smallest duration Event Timing reports;
  - each query returns its results (5, 5 and 2).
- **Swipe-back:**
  - drag frames: p95 18–19 ms on both engines from a layer and on Chromium
    from a root tab; 28 ms on WebKit from a root tab;
  - release to settled: 233–234 ms from a layer, 500–517 ms from a root tab;
  - every release is one history step.
- **Answers:**
  - feedback takes 184–198 ms when the server answers at once;
  - with the server held 1 s it takes 1.19–1.20 s, because the feedback
    waits for the server (2.11).
- **Pull-to-refresh** (as a returning learner):
  - today's pull reloads the whole page: a 238 KB HTML answer with status 200
    on every pull;
  - the first new frame comes 420–480 ms after the release, and the content
    settles at 1.94–2.16 s;
  - in a first session on WebKit, the first pull is also the worker's
    takeover, and its first frame takes 2.25 s.
- **Pro, trial and checkout:**
  - the sheet's first frame comes 62 ms (Chromium) or 91 ms (WebKit) after
    the tap, and 26–38 ms on a repeat open;
  - checkout is one of the warm-up's pages. In a first session WebKit fetches
    its files again through the worker (as in the takeover): 1.31 s against
    0.45 s on Chromium. After the warm-up it takes 0.19 s on both;
  - trial is not a warm-up page: 0.50 s or 0.82 s in a first session, and
    0.27 s or 0.51 s as a returning learner.

**`telegram-web-app.js` in the child pages** (cold and warm, with the script
and with it removed in the lab):

| Page | Engine | Cold FCP with / without | Warm FCP with / without | Main-thread time, cold / warm |
|---|---|---|---|---|
| Dictionary | Chromium | 1090 / 984 | 216 / 204 | 11 / 4 |
| Phrases | Chromium | 1030 / 904 | 212 / 196 | 11 / 5 |
| Dictionary | WebKit | 2862 / 2282 | 203 / 204 | unsupported |
| Phrases | WebKit | 1002 / 920 | 181 / 184 | unsupported |

- **Main-thread time:** 11 ms cold and 4–5 ms warm on Chromium with 4× CPU,
  under the 50 ms rule. So there is no follow-up to defer it.
- **Download:** the cold difference is the extra parser-blocking download on
  this link, not script time:
  - 106–126 ms on Chromium;
  - 82 ms on WebKit Phrases and 580 ms on WebKit Dictionary.
- **Warm:** the difference is ≤16 ms.

**Findings that no task in this change owns yet (for the owner):**
1. **Icon font on a first launch.** Icons appear 4.6–5.1 s after the course
   is ready. Until then their slots are empty, then "□" boxes. The cause is
   one 870 KB font for about 74 icons, with no `font-display`.
2. **The worker's warm-up shares the link with the first session** for
   24–31 s (1.6–1.9 MB). An action in that window waits behind it. For
   example, a WebKit Recognition repeat took 3.4 s in such a run.
3. **WebKit worker takeover.** The first launch under the worker's control
   costs 0.9 s and 133 KB on WebKit, against 0.27 s and 14 KB on Chromium.
   This may be how Playwright's WebKit keeps its cache. A real iPhone (5.1)
   shows whether Safari pays it.
   The same refetch makes a first-session checkout open take 1.31 s on
   WebKit, against 0.45 s on Chromium.
4. **Rating repeat open shows the placeholders again** for about 160 ms;
   Profile's repeat open does not. Evidence: the skeleton readings above.
5. **Course onboarding, cold:** 1.01 s (Chromium) and 1.06 s (WebKit), over
   the 1000 ms bound.
6. **The 2.5 performance gate is below today's baseline.** The gate requires
   drag frames at p95 ≤16.7 ms on Chromium 4×. Today's layer and root-tab
   drags already run at 18–19 ms there, and the root-tab peek is not built
   yet. As written, 2.5 would stop and report on today's code.
7. **WebKit's cold shell (2.15 s) is not held by the head resources** (head
   table above). 2.9 can reach 1500 ms on WebKit only by finding what holds
   that first paint, or by an owner-approved exception. Real-user launch
   timing (1.4) shows whether real iPhones are affected.
8. **The Telegram SDK's download** delays the cold first paint of Dictionary
   and Phrases by 0.08–0.58 s. Its script time is under the 50 ms rule, so
   1.3 opens no follow-up. The owner can open one on the download cost.

**Owner decisions on these findings (2026-11-23),** recorded in the OpenSpec
design ("Decisions on the 1.3 findings"):
1. Icon font: a subset served by the app (task 2.14).
2. Warm-up: it starts after the first launch has finished (2.15).
3. WebKit takeover: no fix now; 1.4 records whether the worker controls
   the launch.
4. Rating repeat open: shows the list it has and refreshes in place (2.16).
5. Course onboarding, cold: an approved exception; its target is the
   reading + 10%.
6. 2.5 frame gate: p95 ≤19.8 ms, today's root-tab drag + 10%.
7. WebKit cold shell: 2.9 moves the four character scripts; the WebKit
   target is decided with 1.4's data.
8. Telegram SDK: removed from Dictionary and Phrases on the PWA path only
   (2.4).

**Still open after 1.3:**
- Real Safari on an iPhone (5.1) and real-user timing (1.4).
- Reduced motion, failed requests and account switch per screen: the
  condition matrix (2.13) names each one's test or owning task.
- Not timed: the Friends sub-tab, and the shimmer inside the Phrases child.
- "After" readings: each group 2 task records its own, with this harness and
  these targets.

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
5. For the **historical Backend/PWA-only implementation phase described in this document**, Android native was not modified. This is **not a prohibition for the current combined PWA + Android + Backend initiative**, which must include Android native work and appropriate client-specific tests. Preserve contracts consumed by Android, Telegram bot and Mini App, and check all shared API changes for compatibility.
6. Preserve user isolation, CSRF/session checks, course progress, Trial/Free/Pro decisions, purchases, refunds and expiry. No optimistic entitlements and no public caching of private data.
7. **Native Android** screens follow the same rules with the existing Compose/ViewModel architecture: useful first frame, per-section loading/empty/error/offline states, lifecycle-aware cancellation, no duplicate reads. State that must survive a detail-and-back round trip (list scroll, search, filters) is owned above the branch that leaves composition, so returning lands where the learner left.
8. **Back navigation is one step per gesture** on every surface: PWA edge swipe, Telegram BackButton, browser/Android history back and the system back all end in one `NavBack.goBack()` (PWA) or one `BackHandler` step (Android). A new PWA layer registers in `NavBack.LAYERS` (or as a nested `RESOURCE` target), is opaque while dragged and closes before its transform resets; extend `tests/e2e/test_pwa_swipe_back.py` when adding one.

## Performance acceptance for every future change

- In each PR changing Backend/PWA behavior, record the **affected routes/sections**, expected performance effect, cache/auth/privacy implications, and chosen measurements. Distinguish "not applicable" from "not checked".
- Include a focused regression test for each new feature or meaningful logic change. PWA tests must verify independent shell/skeleton/ready/failure/retry behavior and avoid extra API calls under slow-network, locale re-render and navigation when relevant. Backend tests must verify query count/ownership/timeout where relevant.
- Run the CI workflow `.github/workflows/backend-pwa-performance-contract.yml`. Its guard requires this document and permanent links in `AGENTS.md` / `AI_RULES.md`, and refuses Backend/PWA/Android implementation changes without accompanying regression tests on pull requests and main integration (Android: a changed `android/app/src/test` or `androidTest` `*Test.kt`; Android CI runs the JVM suite, instrumentation runs locally on the `direct` flavour) (intermediate feature-branch pushes check the permanent policy without demanding a test in each small commit). PWA changes also run Chromium and WebKit shell/section and swipe-back regressions; applicable backend changes run targeted course-map tests.
- **CI is a guardrail, not proof of performance:** a test file being modified does not prove it covers every new component. Review the test assertions and use slow-network filmstrips, p50/p95, LCP/CLS/INP and database evidence to sign off the affected behavior.
- Do not silently turn incomplete measurements or failed checks into green checkboxes; a future feature is not finished merely because it renders or its PR CI passes.
