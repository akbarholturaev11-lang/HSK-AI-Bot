# Android checkout screen review

Reviewed 2026-11-29 against learner PWA source at `6bc754ea` and the
`hsk-ai-ui` professional-first, layout, spacing, typography, icon, button,
modal, dropdown, radio, stepper and text-field contracts. This is a native
adaptation, not a claim of identical browser pixels. Android dp/sp, system
insets, IME, system Back and native receipt picking remain native.

The owner’s overrides are intentional: centered **HSK AI PRO**, left X only
on the first checkout page, subsequent Back, right headphones; no small
limit/exit footer; short country names; and “buy Pro now / 20% on the first
payment” exit copy. Existing server prices, offer eligibility and paid access
remain authoritative. The owner deferred these PWA additions to another PR.
The learner PWA JS/CSS, checkout HTML, generated learner catalog and PWA auth
renderer are byte-identical to the main baseline. Shared Mini App canonical
changes contain only the two Android analytics labels for Admin.

## Individual window checks

Screenshots below are in the local evidence directory
`/tmp/hsk-checkout-audit-final/`; names omit `direct-checkout-` and `.png`.
Source references: `NativeLavaCheckout.kt`, `CheckoutChrome.kt`,
`SubscriptionCheckoutHost.kt`, `SectionLimitOverlay.kt`; reference assets:
`iphone-pwa-inline-pro.{js,css}`, its bridge and `subscription.html`.

| Window/state | Inspected behavior and visual result | Screenshot evidence |
| --- | --- | --- |
| Limit, first page | PWA panda, two primary terms, prices/selection, compact country control, primary action and More. No renewal footer. Centered brand, X/headphones. | `limit-primary`, `limit-ru`, `limit-tg` |
| Limit, More | All four available provider terms; selected term and country persist; one Back returns to the compact offer. | `limit-more` |
| Country menu | Short PWA labels, flags, chevron, selected check; selection preserves More. | `country-menu`, `country-pwa-parity` |
| Ordinary provider plans | Shared chrome, same plan anatomy and country control; actual provider/manual route remains selectable. | `provider-plans` |
| Email, empty/filled | Persistent accessible Email label, one-line term/amount summary, email keyboard, reachable CTA above IME. Back retains the plan. Billing terms stay at this purchase step. | `email`, `email-filled` |
| Email, invalid | Localized field error on IME/blur/CTA; zero start calls. Valid model guard remains authoritative. | `email-error` |
| Lava pending | Honest server-pending state; foreground return polls the same invoice. Background stops polling. No redirect-created success. | `provider-pending` |
| Lava paid | Celebrating PWA pose and return action only after acknowledged server status. | `provider-paid` |
| Lava failed | Explicit failed state and recovery/support actions, with Back. No invented paid result. | `provider-failed` |
| Exit offer | PWA gift pose, owner marketing in UZ/RU/TJ, claim and decline, no small footer. One Back preserves draft; explicit decline closes without claim/start. | `exit-offer-uz-1.0`, `exit-offer-ru-1.0`, `exit-offer-tg-1.0` |
| Active automatic subscription | Actual renewal status and formatted paid-through date; no raw ISO timestamp or repeated brand heading. | `renewal-active` |
| Cancellation confirmation | Same paper/ink/accent palette; Back makes zero cancellation calls, confirmation makes one. | `renewal-confirm` |
| Cancelled renewal | Paid term retained; no further automatic renewal is claimed. | `renewal-cancelled` |
| Manual tariff page | Shared header/cards/country. One initial X; selected inline tariff skips this repeated picker. | `manual-plans`, `manual-plans-ru-1.0`, `manual-plans-tg-1.0` |
| TJ bank step | PWA DC City/Alif choice before quote; fixed next action; Back preserves tariff. | `manual-bank-ru-1.0`, `manual-bank-tg-1.0` |
| China wallet step | Existing Alipay/WeChat choice; selected wallet is carried into the exact quote. | `manual-wallet` |
| Manual requisites | Amount, term, bank/QR and immutable receipt upload. Submit disabled until a receipt is ready. No redundant footer Back. | `manual-pay`, `manual-pay-ru-1.0`, `manual-pay-tg-1.0`, `manual-qr` |
| QR enlargement | Same full-screen header, square enlarged image, no duplicate footer dismissal. Back restores the same quote; enlargement geometry has a regression assertion. Fixture is a checkerboard, not a payable QR. | `manual-qr-preview` |
| Receipt selected | Visible selected-file state and enabled submit; selection does not submit or grant Pro. Stale picker/quote and delayed submission guards retained. | `manual-receipt-ready` |
| Manual pending/rejected | Pending remains pending until server decision; rejection offers retry and returns to plans. Existing HSK 3.0 provisional-access/stale-response tests also pass. | `manual-pending`, `manual-rejected` |
| Support sheet | Shared surface/typography and single contextual contact action; Back restores unchanged manual draft with zero submissions. Missing configured contact cannot become a fabricated destination. | `manual-support` |
| Play limit | Consumption-only neutral gate, always-visible headphones and no Direct purchase action; configured-contact/unavailable behavior covered. | `play-neutral-debug-uz`, `play-neutral-debug-ru`, `play-neutral-debug-tg` |
| Large text | 200% title/body/amount/action text remains scrollable and actionable; header stays centered and controls reachable. Native text reflow is intentional. | `limit-large-text`, `exit-offer-uz-2.0`, `manual-plans-uz-2.0`, `manual-bank-uz-2.0`, `manual-pay-uz-2.0` |

## Reproducible evidence

- `android/tools/capture_checkout_audit.py --variant direct`: 43/43 passed
  on the owned Android 16/API 36 emulator; 45 named native screenshots.
- Same command with `--variant play`: 5/5 passed; six retained screenshots.
- `android/tools/audit_checkout_pwa_reference.py --engine chromium|webkit`:
  17 reference states per engine, zero page errors and no horizontal overflow.
  Uses actual shipped assets/renderer, synthetic intercepted responses and no
  DB/provider connection. It writes no learner PWA source.
- Native test coverage also retains manual/HSK 3.0 stale receipt/response,
  duplicate starts, optional offer decline, old-backend capability rollout,
  lost-start recovery, session-bound telemetry and delayed-webhook behavior.
- Final native JVM run: Direct 794/794, Play 719/719, no skips; both variants'
  lint checks passed with zero fatal/error findings.
- Focused latest backend/PostgreSQL/native catalog run: 35 tests and 69
  subtests passed; separate full catalog run: 17 tests and 65 subtests passed.
  Catalog builder: 85 current artifacts; frozen-source guard: 812 source files,
  746 lessons, zero blockers. Migration upgrade and populated-downgrade refusal
  use only isolated disposable PostgreSQL schemas.

Analytics Impact: Android mirrors the existing PWA account+attempt,
first-stage-cohort and maximum-reached-stage calculation. UI events are
authenticated/deduplicated; invoice start and paid are server/ledger-owned.
Actual PG native bearer → event → invoice → ledger/refund → Admin tests cover
this path. Missing attribution, historical invoices and reversals remain
explicit. This does not certify every legacy Android analytics flow.

Monitoring Impact: the new route is mapped to `checkout_payments`; existing
native `DiagTags.PAYMENT`, authenticated intake, incident mapping and Admin
Inbox remain in use. Both affected Android flow mappings have real PG
route-to-Inbox coverage in the required Analytics CI. Cosmetic copy/spacing
changes add no new events or failure-code inventions.

No real charge/3DS, physical-device keyboard/biometric acceptance, production
DB mutation or APK/store publication is represented by these fixture checks.
The required check on the final commit and verified `origin/main` ref are
separate delivery gates.
