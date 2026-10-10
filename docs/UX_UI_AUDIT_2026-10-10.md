# HSK AI — Profile and limit UI/UX audit (2026-10-10)

Base: `main` at `5ed2984ef709440bb2f7d57a9f1399ee029c1cf0`. This audit is source-level. No mobile build, emulator, or Telegram WebView visual test was performed in the cloud environment.

## Main observations

1. **Android Profile composition**: `android/app/src/main/java/com/pomp/hskai/feature/profile/ProfileScreen.kt` originally rendered `ProfileSubscriptionCard` immediately after `ProfileHero`, ahead of the daily goal, statistics, calendar and achievements. The learner's own progress should lead; subscription remains discoverable via `AccessPill` and the lower subscription card.
2. **Mini App Profile composition**: `app/static/course-v3.html` -> `renderProfile()` renders header/settings, hero, daily goal, streak calendar, three achievements, `proProfileCard()`, mistakes/friends, social links. Android has a 3-metric stats card; Mini App's own `renderProfile()` currently has no equivalent despite global `.stats` CSS being defined for another user profile. Do not fabricate a mistakes count: verify the server response first.
3. **Profile's Pro state management**: Mini App's `proProfileCard()` contains paid, temporary, active trial and free paths with different CTAs. Android's `ProfileSubscriptionCard` has analogous but not identical paths. Keep renewal and status information visible; do not make a generic promotional banner override entitlement information.
4. **Different purchase channels**: `app/static/course_v3_data/ads.js` -> `showLimitPromo()` creates the Mini App paywall. Android Direct uses `feature/limit/SectionLimitBlock.kt` under `src/direct`; Android Play uses a distinct `src/play` implementation. These paths MUST preserve different allowed payment actions. Server-side access and trial eligibility are authoritative.
5. **Potentially misleading Android benefit**: the 3 language `limit_benefit_lessons` resource strings claimed that all lessons were open. The separate HSK 3.0 entry payment can make this false without qualification. Updated the strings to distinguish Pro lessons and HSK 3.0 entry. Confirm business/legal wording before release.
6. **Responsive layout**: both limit components scroll, but rendered safe-area, text wrap, bottom navigation and accessibility need on-device verification. Source alone cannot establish that every mobile size fits.

## Changes included in this branch

- Android profile order: Hero → Daily goal → Stats → Calendar → Achievements → Subscription → Mistakes/Friends → Social.
- Android Pro benefit line: clarify separate HSK 3.0 entry in Uzbek (default), Russian and Tajik.
- **No** changes to pricing, trial status, quota policy, API endpoints, server entitlements or Google Play checkout logic.
- **No** changes to the Mini App UI code in this first patch.

## Follow-up tasks (priority and acceptance criteria)

### P0 — Paywall accuracy / access regression

- Check free (trial eligible/ineligible), trial active, paid, temporary and expired accounts on Mini App, Android Direct and Android Play.
- Confirm the wording and actual HSK 3.0 entitlement: separate entry fee does not imply Pro lessons are unlimited/free; Pro purchase alone should not silently bypass a required entry payment.
- Verify the limit modal is closable, its reason is readable, its primary CTA is unambiguous, and it never offers a second trial.
- Verify all three language layouts at narrow screen sizes and with larger font settings.

### P1 — Profile information architecture parity

- Match **hierarchy**, not necessarily identical native component implementation: progress/goal first, compact subscription status/renewal accessible, achievements and mistakes grouped, social links last.
- Add a Mini App stats group only after confirming real API fields for XP, lessons and mistakes (or choose a truthfully available metric). Avoid duplicating streak in several equally prominent blocks.
- Mini App 320px/375px/390px Telegram, Android small screen and tablet; test tap targets (minimum 44x44), scrolling and bottom-safe-area.
- Profile CTA accessibility: free user can find subscribe; paid user can find renewal; no over-prominent hard sell above learning progress.

### P2 — Component cleanup after smoke verification

- Factor repeated Profile metric tile styles and limit CTA hierarchy where possible, without rewriting the large monolithic `course-v3.html`.
- Remove confirmed dead/stale UI paths only after validating references; e.g. `maybeShowPlanChoice` is defined but no direct invocation was found in `course-v3.html` at this snapshot.
- Review UI token consistency (spacing, radius, font weights, responsive typography) without introducing extra animation layers.

## Required local validation before merge to main

1. Android Direct + Play compile; run Profile and limit-related unit/UI tests.
2. Smoke HSK 2.0 and HSK 3.0 flows for free, paid, and trial accounts; ensure navigation back and subscription renewal still work.
3. Browser Telegram Mini App screenshot comparisons at 320/375/390px with RU/TJ/UZ, keyboard and safe area.
4. Verify no unexpected traffic, payments, ads or policy bypass. Compare visual snapshots and check all CTA routes.

Risk notes: Subscription card moving lower may reduce visibility; assess with UX review and events before release. Android string lengths increase, so wrapping must be tested. **Do not merge untested cloud changes directly into `main`.**
