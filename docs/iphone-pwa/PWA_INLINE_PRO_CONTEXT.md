# PWA Inline Pro — implementation context (2026-11-08)

Source of truth: GitHub `main` commit `4ca0d2d1c7e89e517f6d9e6ab781c12963287b9a`.
Scope: learner **PWA only**. Telegram Mini App, Android Direct/Play, and existing standalone subscription UI must not change behavior.
This is the **single context/handoff file** for this work. Update status here as implementation advances.

## Product contract
1. A limit paywall offers the two Lava plans `1_month` and `12_months` immediately, with an explicit CTA. Prices/currency/term availability are server-owned, not hardcoded; missing products must not show a fake price or a dead CTA.
2. `Другие тарифы` opens the other Lava terms (`3_months`, `6_months`) plus existing manual checkout choices (bank Visa, Alipay, WeChat) **inside the paywall context**. Existing receipt/manual-review logic is reused, not forked.
3. A user dismissing via X may see a **real 20% exit offer**. It is account-scoped, server-validated, time-limited, idempotent; never stack with other discounts. Claim must cause a genuine Lava promo-code-discounted invoice; fail closed without configured `exit_offer:20` provider promo mapping. Declining closes the UI. Renewal is at the regular provider price and this needs to be disclosed.
4. Default price view: actual pay amount plus a presentational 30%-higher `.99` comparison figure (ceiling to next `.99`). Comparison must never enter API, invoice, DB, analytics as a payment amount, or be described as a verified former price. Real discounts replace that comparison with the actual base price crossed out and actual discounted price displayed. Revert when no server discount is active.
5. Safely return focus and resume the same course/practice after dismiss, return, provider failure, or verified Pro activation. Do not treat provider redirect as payment proof.
6. Supported languages `uz`, `ru`, `tj`; iPhone Safari Home Screen, browser PWA, and all PWA limit entry points. Use explicit names and i18n, responsive safe area, back/gesture support.
7. Respect `manual_only`, `lava_only`, `both` server flags; no unauthorized fallback to Lava if disabled. No new Play or Telegram checkout features.

## Existing paths
- Course shell/paywall: `app/static/course-v3.html` `App.openPaywall`, `App.goPay`, `App.openPwaCheckout`, `RESOURCE.openPracticeCheckout`.
- Practice pages: `app/static/course_v3_voice.html` and `course_v3_{recognition,memorize,pronunciation,test,mistakes}.html`; iframe bridge `app/static/course_v3_data/iphone-pwa-practice-boot.js`.
- Shared existing checkout: `app/static/subscription.html` `PWA_CHECKOUT_HOST`, `API.overview`, `lavaStart`, `lavaStatus`, `submit`, `paymentStatus`, `returnToCourseFromCheckout`.
- PWA auth/router: `app/api/pwa_auth.py`; CSRF/session from `/api/v3/pwa-auth/session`.
- Lava: `app/api/lava_checkout.py`, `app/services/lava/{checkout,config,terms,ledger,events}.py`.
- Manual: `app/services/subscription_miniapp_service.py`, `app/services/subscription_price_service.py`.
- Promotions: `app/services/discount_service.py`, `app/db/models/discount_campaign.py`, admin control `app/admin_api/pwa_lava.py`.
- PWA cache: `app/static/iphone-pwa-sw.js`. Version-pinned static assets use cache-first and need updated URL revisions.
- Tests: `tests/e2e/test_pwa_checkout_navigation.py`, `tests/test_pwa_browser_auth.py`, `tests/test_lava_promo_codes.py`, `tests/e2e/test_limit_and_release_regressions.py`.

## Implementation plan
- [x] Audit repository architecture and PWA entry points.
- [x] Create isolated feature branch and this context file.
- [x] Build standalone, PWA-only inline paywall module, server-owned plans and safe checkout state transitions.
- [x] Integrate all PWA limit triggers without modifying Telegram conditions; cover voice separately.
- [x] Implement 20% exit offer eligibility/claim in backend, schema migration, and Lava promo mapping with automated test cases (execution pending).
- [x] Preserve manual checkout in an embedded iframe inside the paywall; no navigation to a standalone subscription section from the limit surface.
- [ ] Verify UI and server behavior in the real browser; locale strings, version-pinned CSS/JS, safe areas and Pro refresh are wired. Exit-offer record provides offer/claim/consumption evidence; aggregated analytics remains future work.
- [ ] Run tests + review diff + create draft PR (do not merge until verified).

## Known constraints / outstanding verification
- GitHub code knows all four Lava periodicities, **but live** enabled terms, two-method mode, and `exit_offer:20` promo code need production configuration checks.
- Lava provider checkout may require external secure browser/3DS. It must not be misrepresented as an internal final payment step.
- Provider webhooks verify invoice status and authorize Pro. Client-side success/return cannot grant entitlement.
- Existing legacy discounts/referral/admin flows must retain current semantics; no unearned discounts.
- iOS popup blocking with asynchronous `window.open` requires direct gesture-safe payment start plus a manual reopen fallback.
- Do not claim automated tests passed before executing them.

## Coding status at last update
- PWA UI: `app/static/course_v3_data/iphone-pwa-inline-pro.{js,css}`; seven limit entry screens wired.
- Backend: PWA CSRF endpoint; per-account `pwa_exit_offers` table (Alembic `0152`), real Lava promo consumption by verified webhook.
- Admin PWA: added `exit_offer:20` promo-code editor; without a real code saved in the provider and admin this offer must remain unavailable.
- Tests authored: `tests/test_pwa_exit_offer.py`, `tests/e2e/test_pwa_inline_pro.py`, a CSRF test in `tests/test_pwa_browser_auth.py`. They have not yet been executed.
- The PWA mode `exit_discount` applies to Lava only, not manual bank/QR; manual checkout keeps its existing discount rules and its full original screens.
- Still must inspect CI, validate 1m and 12m live term enablement, actual payment popup/3DS return, and user account rights after payment; no merge until those checks.
