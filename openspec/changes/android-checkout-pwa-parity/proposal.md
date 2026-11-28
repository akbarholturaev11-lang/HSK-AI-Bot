## Why
Android Pro checkout uses unrelated Material provider controls, a separate manual layout and an obsolete limit sheet. Existing PWA context (`docs/iphone-pwa/PWA_INLINE_PRO_CONTEXT.md`) is PWA-scoped; this delta records the authorized Android adaptation and browser-return regression without changing that handoff or PWA.

## What Changes
- Share centered Pro header, native stepwise Back, paper palette, plan cards and bottom action across Android Direct checkout routes.
- Present Direct limits with the actual PWA inline offer anatomy and compact/all-plan navigation, reusing existing manual receipts and provider APIs.
- Refresh pending Lava status on foreground return and bounded foreground polling; success requires server confirmation.
- Preserve Play consumption-only access, all pricing, discounts, receipt preview, auth and course rules.

## Capabilities
### New Capabilities
- `android-pro-checkout`: coherent native Pro presentation and verified payment return.
### Modified Capabilities
None.

## Impact
Android checkout/limit Compose and ViewModels, canonical Android UZ/RU/TJ copy, focused tests. No backend, PWA, store policy, schema or dependencies. Main baseline: 6bc754ea. Risk: nested Back, process recreation, delayed webhook and manual fallback. Rollback: revert the Android commit; no data migration. Analytics Impact: reuse authenticated overview/start/receipt writers and canonical payment outcomes; no client-created paid events. Monitoring Impact: retain DiagTags.PAYMENT intake and checkout_payments/payment mapping; styling adds no failure signal, status failures retain retry.
