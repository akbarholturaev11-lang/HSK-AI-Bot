# PWA Inline Pro — implementation context (2026-11-08)

Source of truth: GitHub `main` commit `4ca0d2d1c7e89e517f6d9e6ab781c12963287b9a`.
Scope: learner **PWA only**. Telegram Mini App, Android Direct/Play, and existing standalone subscription UI must not change behavior.
This is the **single context/handoff file** for this work. Update status here as implementation advances.

## Product contract
1. A limit paywall offers the two Lava plans `1_month` and `12_months` immediately, with an explicit CTA. Prices/currency/term availability are server-owned, not hardcoded; missing products must not show a fake price or a dead CTA.
2. `Другие тарифы` opens the other Lava terms (`3_months`, `6_months`) plus existing manual checkout choices (bank Visa, Alipay, WeChat) **inside the paywall context**. Existing receipt/manual-review logic is reused, not forked.
3. A user dismissing via X may see a **real 20% exit offer**. It is account-scoped, server-validated, time-limited, idempotent; never stack with other discounts. Claim must cause a genuine Lava promo-code-discounted invoice; fail closed without configured `exit_offer:20` provider promo mapping. Declining closes the UI. Renewal is at the regular provider price and this needs to be disclosed.
4. Default price view: actual pay amount plus a presentational 30%-higher `.99` comparison figure (nearest `.99` above the actual price). Comparison must never enter API, invoice, DB, analytics as a payment amount, or be described as a verified former price. Real discounts replace that comparison with the actual base price crossed out and actual discounted price displayed. Revert when no server discount is active.
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

## UI refinement — 2026-11-08 (owner-approved)
- Applied `.agents/skills/hsk-ai-ui/SKILL.md` (mobile-first, one primary CTA, premium and compact) and `.agents/skills/webapp-testing/SKILL.md` (mobile Playwright verification).
- Default limit sheet opens synchronously, before API returns: panda SVG art at top, bold limit headline, three concise Pro benefits, immediate two-card skeleton for Lava 1-month and 12-month plans, one primary checkout button and short «Другие тарифы» link. No redundant explanatory paragraphs.
- Motion: 190ms backdrop and 330ms spring-like rising sheet; no artificial timeout or wait for API to display sheet. Reduced-motion preference disables all animations.
- Current server price and UI-only higher comparison (rounded to a .99 ending) appear next to each other inside each plan. True discount replaces visual comparison with the real base amount, and the provider invoice remains the source of truth.
- X flow still checks server entitlement and offers real 20% only when configured. Existing manual/Lava alternate navigation remains.
- PWA route injects version-pinned CSS and JS without modifying source-reviewed Telegram/Mini App HTML. Update both blob-hash URLs when either asset changes.
- PWA E2E now asserts headline, panda SVG, exactly 3 benefit lines, entry animation, 2/4 plans and exit discount.
- QA not yet finalized; inspect latest PR #279 checks before merge; production Lava promo and actual mobile browser checkout must be verified.


## Audit follow-up — all PWA limit surfaces and analytics

**Not verified complete. Do not merge based on the 7 route wrappers alone.**
- PWA inline Pro bridge wraps the course `App.openPaywall`, voice `showPaywall`, and 5 independent practice gates (`recognition`, `memorize`, `pronunciation`, `test`, `mistakes`). In practice pages, `showLimitNow` currently calls the original UI before opening the new overlay: verify that dismissing leaves no duplicate legacy limit modal or broken navigation. Other internal PWA gates must be enumerated and checked.
- Existing `/api/v3/pwa/subscription/overview` writes `SubscriptionEntryEvent` and generic `checkout_opened`. The new inline JS/bridge writes no specific UI telemetry: `paywall_seen`, plan selection, other plans, payment-method selection, X/dismiss, offer shown/declined/claimed, return or checkout failure. The one-time `pwa_exit_offers` row records offered/accepted/consumed state but is **not** a complete analytics funnel.
- Critical: inline offer claim reloads `overview` with the same `attempt_id`, and overview writes `checkout_opened` again. Check and enforce session/attempt deduplication before counting conversion. Conversely, the course wrapper bypasses legacy `App.openPaywall` tracking, potentially missing `paywall_seen`. Do not report funnel percentages as accurate without this correction.
- The manual iframe URL sets `embedded=1` but the checkout bridge listens for `inline_manual=1`: verify intended bank/QR landing and eliminate double/navigation fallback.
- Only the synthetic course-host Playwright test was exercised; it does not establish functional coverage of all practice routes, PWA Safari/iOS native screens, analytics aggregations, checkout provider callbacks, or production settings.
- Follow-up implementation must add server-attributed, deduplicated, per-account events with distinct source, session/attempt, plan and payment method; preserve existing conversion counters and ensure dashboard/statistics consumers can surface them correctly. Add end-to-end tests for all 7 entry routes, return/retry, payment success/failure and analytics counts before declaring finished.


## Follow-up implementation: coherent PWA UI and server analytics

Branch-only follow-up to the additional audit. Changes are authored, **not deployed**:
- PWA `overview` now accepts `inline_preview: true`; when true it does **not** write `subscription_entry_events` or legacy `checkout_opened`. Re-fetching after the exit offer therefore cannot double count an attempted checkout.
- New CSRF/session-protected endpoint `/api/v3/pwa/subscription/inline-event` validates source, stage, plan, method and attempt/event IDs; rejects untrusted ownership IDs and server-only payment stages. Account locking and event ID lookup make client retries idempotent.
- Added explicit PWA funnel event names + labels and admin funnel rows for open, plan, other tariffs, payment method, exit 20% shown/claimed/declined, dismissal, actual Lava invoice start, failed checkout and verified payment. Existing `ConversionFunnelService.counts_by_event` and `unique_users_by_event` aggregate these without overwriting the original funnel.
- Lava checkout starts are counted only **after a real provider invoice** exists and only for whitelisted inline sources. Invoice fields `pwa_inline_attempt_id` and `pwa_inline_source` retain attribution through the provider webhook. Successful payment is written in the same DB transaction as Pro granting; retries cannot count again. Other PWA/Telegram checkouts are excluded from inline funnel counters.
- Migration `0153_pwa_inline_funnel` extends the funnel CHECK and adds two nullable invoice attribution fields. It follows historical migration `0076` in discovering physical CHECK names and preserves SQLite skip behavior; QA expected head updated to 0153.
- New tests cover PWA event origin/CSRF, retry deduplication, repeated overview preview, provider verified paid attribution, and Playwright entry from all PWA course/voice/practice routes plus manual iframe navigation.
- The manual iframe now passes `inline_manual=1` to the existing checkout, matching its bridge and preserving bank/QR/receipt business rules.
- A course `App.goPay` bridge intercepts *only* recognized practice-limit sources; profile/onboarding purchases continue along the existing flow.

### Outstanding checks and boundaries
- Wait for GitHub CI on the final commit, **inspect** rather than assume tests pass; fix failing suites before considering merge.
- Distinguish underlying blocked practice state from the one visible Pro modal on each route; an underlying legacy gate is retained as safe fallback when the Pro modal is dismissed.
- Production: validate Lava's live 1m/12m configuration, the actual `exit_offer:20` provider code, Safari popup/3DS return, and manual receipt/Pro refresh.
- Do not claim R2/private analytics exports or admin KPI dashboards have been updated just because the primary admin funnel text now shows new events; audit export pipelines separately.
- Never let UI telemetry grant Pro, affect payment amounts or count an unverified payment as paid.


## 2026-11-08 — production iPhone UX follow-up PR #283

Actual iPhone PWA screenshots exposed six defects in the merged inline paywall. PR #283 fixes PWA-only assets; the original shared Telegram/Mini App HTML is byte-identical.

- **Full screen:** `#hsk-inline-pro` + `.hip-sheet` fill the full dynamic viewport (100dvh), support iPhone safe areas, and keep the content scrollable. Both methods/email/waiting states share a consistent page instead of a half-height bottom sheet. Long headers reserve back/close button space.
- **Colors:** CSS uses HSK's existing `--hsk-paper`, cinnabar, jade, ink and divider tokens with the same fallback hex values as the course UI; removed independently invented green CTA/theme.
- **Mascot:** original distorted inline bear/book replaced with a proportioned panda with feet, body and book. SVG remains local (no network/image/font dependency).
- **No duplicate limit:** PWA practice wrappers intercept `showLimitNow` *before* rendering the original full-page lock. For internal course modules (whose `showLimit` is private), a scoped MutationObserver detects the explicit locked CTA, removes the legacy view and opens the one PWA Pro surface. Dismissing a practice modal navigates to the existing back handler, not the old lock screen. Unmodified Telegram conditions remain as before.
- **Manual path:** selecting manual inside PWA sets `state.path='manual'` and filters the generic `card` choice from the original flow on this PWA iframe only. The user sees manual countries/plans/receipt immediately, without being asked again whether to pay with Visa. Parent sheet header hidden while the complete manual checkout iframe is displayed.
- **Lava URL:** removed the premature `window.open("about:blank")` call that left a blank Safari tab when the asynchronous invoice was returned. A valid HTTPS `lava.top` subdomain URL from the backend appears as a real `<a target="_blank" rel="noopener noreferrer">` only after invoice creation. User taps the link to open payment; cannot produce a pre-opened blank tab. Unexpected hostnames are rejected. Provider webhook remains the only source of Pro access.
- **Tests:** E2E checks viewport dimensions, canonical colors, header button overlap, legible panda, no independent-practice legacy calls, manual card-question suppression, valid/invalid checkout domain, and no preopened popup. Existing auth/analytics, payment, Android and localization CI remain intact.
- Asset SHA references in `app/api/pwa_auth.py` must always match current .css/.js/.bridge blob SHA to invalidate old iPhone PWA caches.
- **Validation boundary:** mocked browser link opening does not prove a real Lava credit-card transaction. Confirm actual provider invoice in the user browser after deployment, and never create a live charge just to test presentation.
