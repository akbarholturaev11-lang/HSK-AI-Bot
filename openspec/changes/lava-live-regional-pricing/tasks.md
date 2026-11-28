# Tasks

## 1. Currency policy and bounded catalog

- [x] 1.1 Add backward-compatible enabled USD/RUB policy to the existing config and signed Admin command; verify legacy defaults, all three selections, CAS/proof binding and disabled-currency rejection with focused config/Admin tests.
- [x] 1.2 Reuse runtime state for one bounded, immutable merchant catalog read with expiry/failure recovery/cancellation isolation; add fake-provider concurrency, expiry, timeout and merchant-isolation tests and document the exact freshness bound in the payment handoff.

## 2. Learner pricing and existing settings UI

- [x] 2.1 Move shared PWA/Mini App and Android Direct overview pricing outside SQL scopes and make invoice preparation use verified live catalog prices; verify no checked-out SQL connection during provider IO, no duplicate POST, unchanged discounts/owner/attempt, fixed historical invoice totals and old APK requests in affected payment/API tests.
- [x] 2.2 Reuse the one Admin currency selector for USD/RUB/both, remove price-refresh-only Save state, retain canonical UZ/RU/TJ field copy and test the actual editor plus regional PWA checkout without adding price controls. Update the scoped handoff and durable architecture facts after verification.

## 3. Integration acceptance

- [ ] 3.1 Run affected payment, auth/session, currency, analytics/monitoring, source/cache and Chromium/WebKit regressions; validate OpenSpec and permanent guards, then commit/push and verify required CI/main/deploy under existing authorization. Report real merchant/device limits separately; never release an APK.
