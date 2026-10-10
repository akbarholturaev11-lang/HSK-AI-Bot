# HSK AI — Profile and limit UI/UX audit (2026-10-10)

Base: `main` at `5ed2984ef709440bb2f7d57a9f1399ee029c1cf0`. This audit is source-level. No mobile build, emulator, or Telegram WebView visual test was performed in the cloud environment.

## Main observations

1. **Android Profile composition**: `android/app/src/main/java/com/pomp/hskai/feature/profile/ProfileScreen.kt` originally rendered `ProfileSubscriptionCard` immediately after `ProfileHero`, ahead of the daily goal, statistics, calendar and achievements. The learner's own progress should lead; subscription remains discoverable via `AccessPill` and the lower subscription card.
2. **Mini App Profile composition**: `app/static/course-v3.html` -> `renderProfile()` renders header/settings, hero, daily goal, streak calendar, three achievements, `proProfileCard()`, mistakes/friends, social links. Android has a 3-metric stats card; Mini App's own `renderProfile()` currently has no equivalent despite global `.stats` CSS being defined for another user profile. Do not fabricate a mistakes count: verify the server response first.
3. **Profile's Pro state management**: Mini App's `proProfileCard()` contains paid, temporary, active trial and free paths with different CTAs. Android's `ProfileSubscriptionCard` has analogous but not identical paths. Keep renewal and status information visible; do not make a generic promotional banner override entitlement information.
4. **Different purchase channels**: `app/static/course_v3_data/ads.js` -> `showLimitPromo()` creates the Mini App paywall. Android Direct uses `feature/limit/SectionLimitBlock.kt` under `src/direct`; Android Play uses a distinct `src/play` implementation. These paths MUST preserve different allowed payment actions. Server-side access and trial eligibility are authoritative.
5. **Correct HSK 3.0 entitlement**: `CourseTrackAccess.allowed` accepts `UserAccessStateService.is_paid(user)` as sufficient access when HSK 3.0 is enabled; an active paid Pro subscriber must NOT pay the one-time HSK 3.0 entry fee. The one-time entry payment provides permanent track access to non-Pro users but does not remove lesson-start limits. Android benefit copy now describes HSK 2.0 and currently available HSK 3.0 levels. Check feature enablement and live level filters before advertising access.
6. **Mini App limit was using an ad carousel as its paywall**: `app/static/course_v3_data/ads.js` used the same rotating promo presentation for the limit as for advertisements. The limit now has a compact title, a server-supplied reason where available, Pro CTA, and server-controlled optional trial CTA. Carousel remains in ad flows only. The code used `if(!why)` after assigning a generic fallback `why`, making the precise limit-status fetch unreachable. It now fetches when no specific reason was passed.
7. **Responsive layout**: both limit components scroll, but rendered safe-area, text wrap, bottom navigation and accessibility need on-device verification. Source alone cannot establish that every mobile size fits.

## Changes included in this branch

- Android profile order: Hero → Daily goal → Stats → Calendar → Achievements → Subscription → Mistakes/Friends → Social.
- Android Pro benefit line: describe automatic Pro access to HSK 3.0's available levels in Uzbek (default), Russian and Tajik. One-time fee is relevant only to non-Pro permanent track access.
- **No** changes to pricing, trial status, quota policy, API endpoints, server entitlements or Google Play checkout logic.
- Mini App profile: added a compact 2-metric row for actual `MAP.progress.xp` and `MAP.progress.completed`, localized RU/TJ/UZ. Deliberately did not fabricate a Mini App mistakes count without a confirmed response field.
- Mini App limit: specific `.limit` CSS hides the ad promo carousel, supplies a readable heading and uses the existing Pro + trial + close handlers without changing entitlement or purchase logic.
- Limit CTA hierarchy (2026-10-10 follow-up): remove the redundant **Later** button from Android Direct. If the server marks trial eligible, show exactly **7 days free trial** as primary and **View Pro plans** as secondary; otherwise show **View Pro plans** only. The top-right X always dismisses the full-screen overlay. Mini App follows the same two-option hierarchy, keeping its existing trial eligibility check and X close. Keyboard focus follows visual order.
- Google Play distribution retains its separate, payment-safe flow (trial/recheck/support); do **not** add a noncompliant external checkout link or pretend its second button buys Pro.
- Regression source-contract tests: `tests/test_profile_limit_ui_contract.py` (not executed against a full runtime in this environment).

## Follow-up tasks (priority and acceptance criteria)

### P0 — Paywall accuracy / access regression

- Check free (trial eligible/ineligible), trial active, paid, temporary and expired accounts on Mini App, Android Direct and Android Play.
- Confirm the correct entitlement matrix: paid Pro can access enabled/live HSK 3.0 without a separate unlock payment; free users may buy permanent track entry separately but still face configured lesson limits. Verify Pro expiry and unlocked_at combinations.
- Verify the limit modal is closable, its reason is readable, its primary CTA is unambiguous, and it never offers a second trial.
- Verify all three language layouts at narrow screen sizes and with larger font settings.

### P1 — Profile information architecture parity

- Match **hierarchy**, not necessarily identical native component implementation: progress/goal first, compact subscription status/renewal accessible, achievements and mistakes grouped, social links last.
- Mini App now shows XP and completed lessons from existing `MAP.progress` values; verify that both totals match the Android profile for the same account. The Android mistakes figure remains native-only until a confirmed equivalent payload is available. Avoid duplicating streak in several equally prominent blocks.
- Mini App 320px/375px/390px Telegram (including short screens), Android small screen and tablet; test tap targets (minimum 44x44), scrolling and bottom-safe-area. For the compact limit ensure the reason is not obscured by the X, long Tajik/Russian lines wrap, and returning from subscription still works.
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
