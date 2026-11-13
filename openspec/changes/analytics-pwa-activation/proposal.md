# Proposal

## Why

PWA activation and direct activation are `not_instrumented` per platform (audit row A11). Their cohort anchor, `onboarding_completed`, carries no route-set client, and the old `transport` value can be forged on Telegram rows. This is requirement 2 of the next stage in `docs/analytics/ANALYTICS_INTEGRITY_IMPLEMENTATION_PLAN.md`, the single context file for this work (section "Next stage", R2).

Before the change, every consumer of `onboarding_completed` was checked. They read only the event name and time (reminders, activation funnel), or parse `activation_variant`. Adding one payload key does not change a product flow.

## What Changes

- **Writer:** `CourseMiniAppOnboardingService.complete` takes `analytics_client`. The route sets it, never the caller's payload. It becomes the final `client` key of `onboarding_completed` and its choice rows. The routes pass:
  - PWA: `iphone_pwa`;
  - Telegram Mini App: `telegram`;
  - Android: `android`.
  The Telegram and Android tags are writer-only; their readers come later.
- **Reader:** Course > iPhone PWA returns three values:
  - `activation` and `direct_activation`: the cohort is anchored on the PWA-tagged onboarding. Only PWA-tagged steps count. The lesson start must come within 2 minutes.
  - `handoff_activation` `{eligible, activated, percent}`: the anchor is each account's first `pwa_handoff_completed`, from the PWA boundary on. An account is activated by a PWA-tagged lesson start or completion within 24 hours.
  Both cohorts are bounded by the detail row limit. Each has its own `attributed_since` date.
- **Admin UI:** the Course cohort table under the PWA filter gets one row, «Telegram → PWA → dars · 24 soat», in UZ/RU/TJ. Under it, two boundary lines reuse the existing «hisob boshlanishi» text.
- **Registry and CI:**
  - `activation` and `direct_activation` add the `iphone_pwa` filter;
  - a new `handoff_activation` metric is PWA-only;
  - the `onboarding_activation` flow is `covered` on the PWA;
  - the route chain test runs in `analytics-integrity.yml`.

Overall impact: none. Overall activation reads the same rows; they now carry one more payload key. Sessions stay `not_instrumented` per platform.

Known gap: an existing account that signs in on the PWA without onboarding or a handoff is in neither cohort.

## Capabilities

### Modified Capabilities
- `admin-real-analytics`: PWA activation becomes a platform-scoped Course metric.
