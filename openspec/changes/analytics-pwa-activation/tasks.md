# Tasks

Only checklist for R2. Context, decisions and the next step live in `docs/analytics/ANALYTICS_INTEGRITY_IMPLEMENTATION_PLAN.md` ("Next stage", R2). Stacked on R1 and PR #285; nothing merges to `main` without the owner's permission.

## 1. Writer

- [x] 1.1 Consumer check of `onboarding_completed`: readers use only the name and time, or `activation_variant`.
- [x] 1.2 `CourseMiniAppOnboardingService.complete(..., analytics_client)` tags `onboarding_completed` and its choice rows on both the HSK 2.0 and HSK 3.0 paths. The PWA, Telegram and Android routes pass `iphone_pwa`, `telegram` and `android`.
- [x] 1.3 Unit tests: the key on every row, no key by default, the HSK 3.0 path, and the Android route's stored row.

## 2. Reader, registry and UI

- [x] 2.1 Course > iPhone PWA `activation`, `direct_activation` and `handoff_activation`, bounded, with `attributed_since.activation` and `attributed_since.handoff_activation`. Overall shares the same activation helper and is unchanged.
- [x] 2.2 Registry: the `iphone_pwa` filter for `activation` and `direct_activation`, a new PWA-only `handoff_activation`, updated reasons, and the `onboarding_activation` flow covered on the PWA. The checker passes.
- [x] 2.3 Admin cohort table: one «Telegram → PWA» row and two boundary lines, UZ/RU/TJ, with the catalog regenerated.

## 3. Proof

- [x] 3.1 Route → PostgreSQL → `/api/admin/v1/analytics` chain test: PWA onboarding, a Telegram onboarding with a caller `client`, and two handoffs. Listed in `analytics-integrity.yml`. It fails on the old writer and on the old reader.
- [x] 3.2 Stored-row tests: Telegram and nested lookalike onboardings stay outside, a handoff with only Telegram learning is not activated, an anchor before the boundary is never read, a young handoff is not eligible, the detail limit, and `no_data` before attribution. The golden test is unchanged.
- [x] 3.3 Full unit suite, PostgreSQL modules, the analytics CI list and the Admin PWA browser suites; results recorded in the context file. Result on the final head `1c5162ed` (local PostgreSQL 15): full unit suite 5193 passed with only the 8 known baseline failures; all 52 PostgreSQL modules 748 passed, 12 skipped, 0 failed; Admin PWA browser harness passed; checker passes in push and pull_request modes.
- [ ] 3.4 Owner acceptance on the iPhone PWA (6.2 style) after deploy.
