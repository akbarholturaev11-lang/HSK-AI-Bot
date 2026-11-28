## Why
Android Pro checkout uses unrelated Material provider controls, a separate manual layout and an obsolete limit sheet. Existing PWA context (`docs/iphone-pwa/PWA_INLINE_PRO_CONTEXT.md`) is PWA-scoped; this delta records the authorized Android adaptation and browser-return regression without changing that handoff or PWA.

## What Changes
- Share centered Pro header, native stepwise Back, paper palette, plan cards and bottom action across Android Direct checkout routes.
- Present Direct limits with the actual PWA inline offer anatomy and compact/all-plan navigation, reusing existing manual receipts and provider APIs.
- Match ordinary PWA manual sequence: skip the repeated inline tariff, then TJ bank / China wallet / other-country requisites; preserve More and selected plans on Back.
- Refresh pending Lava status on foreground return and bounded foreground polling; success requires server confirmation.
- Preserve Play consumption-only access, all pricing, discounts, receipt preview, auth and course rules.

## Capabilities
### New Capabilities
- `android-pro-checkout`: coherent native Pro presentation and verified payment return.
### Modified Capabilities
None.

## Impact
Android checkout/limit Compose and ViewModels, canonical Android UZ/RU/TJ copy, focused tests. The learner PWA, store policy and access/price decisions remain unchanged. Android-specific analytics adds a native authenticated event route, two nullable invoice attribution columns and allowed event names; the Admin analytics consumer gains a separate Android Pro metric. Main baseline: 6bc754ea. Risk: nested Back, process recreation, delayed webhook and manual fallback. Rollback: revert application code and retain additive schema/history; revision 0161 downgrade refuses populated native attribution. Analytics Impact: reuse authenticated overview/start/receipt writers and canonical payment outcomes; no client-created paid events. Monitoring Impact: retain DiagTags.PAYMENT intake and checkout_payments/payment mapping; styling adds no failure signal, status failures retain retry.

## Android analytics parity
The existing PWA Pro attempt calculation is the reference for the native limit offer: account + attempt cohort, max reached stage, 30-day lookback, server invoice start and ledger-confirmed paid/refund truth. Android UI observations, server start/paid correlation and the Admin Android/Overall projection must ship together. The previous generic subscription-entry counter is not a substitute for that funnel. Reuse existing local catalogs, first-party event store, native bearer/installation validation and diagnostics. UI telemetry must never mint payment success, change prices/access, delay checkout or cross an account switch.
