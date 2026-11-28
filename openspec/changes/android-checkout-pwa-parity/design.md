## Context
See proposal.md. PWA references are subscription.html and iphone-pwa-inline-pro.{js,css}; no PWA edits. Direct currently renders provider FilterChips independently of manual checkout and refreshes status once on resume. Shared SectionLimitOverlay renders the old Telegram sheet.

## Goals / Non-Goals
Use current Compose/ViewModels and native dp/sp/insets for the authorized PWA adaptation. No payment-policy, entitlement, provider-integration or Play purchase expansion. The Android-only analytics attribution migration is specified below.

## Decisions
- Extract a small Direct checkout chrome/plan component shared by both real routes; reuse existing palette, native receipt picker and quote/result model. Avoid WebView or duplicated manual payment engine.
- Direct limit presentation owns an ephemeral checkout ViewModel store in a full-screen dialog; Play keeps its neutral channel gate. Close rechecks existing account/learning access.
- Keep UI selection state local/saveable, invoice recovery server-owned. Lifecycle-aware pending polling uses the existing status API, serialized by the model busy guard, stops on background/terminal status and caps each foreground visit at 15 minutes.
- Existing overview/manual receipt/ledger authority stays intact. Native analytics adds the bounded Direct event intake below; apiCall(DiagTags.PAYMENT) retains diagnostics and no client can assert payment success.

## Risks / Trade-offs
- Delayed webhooks → foreground polling plus explicit retry; pending never becomes paid locally.
- Nested dialog/system Back → one handler per visible step and overlay-first dismissal tests.
- Small displays/large UZ/RU/TJ text → scrollable body, fixed reachable action, 48dp controls and emulator geometry tests.
- Server-disabled provider/manual recovery → reuse original route decisions and provider_entry_id; preserve one opening receipt.
- Real provider/3DS acceptance cannot be simulated by unit tests → report separately from fixture UI evidence.

## Migration Plan
Apply additive revision 0161 before running the new backend: two nullable attribution columns and expanded analytics CHECK only. Existing rows are unchanged. Roll back application code independently and leave additive schema/history intact; downgrade refuses populated new attribution/events. Run focused native/PostgreSQL/browser/coverage checks and required CI before promotion.


## Android analytics extension
- Reference: `app/admin_api/pwa_analytics_pwa_pro.py`, PWA inline-event route, Lava invoice attribution and ledger paid event. Keep learner PWA writers/reader behavior unchanged; mirror its SQL cohort/max-stage/refund rules in an Android-only projection.
- Add `android_pro_*` event names and nullable `android_inline_attempt_id` / `android_inline_source` invoice attributes via revision 0161 after 0160. This is attribution only. No existing row is rewritten; downgrade refuses populated new attribution/events rather than deleting history.
- Native Direct limit offers own one saveable attempt ID across provider/manual/details/Back. Ordinary manual checkout matches PWA: a confirmed inline tariff advances directly to TJ bank, China wallet or other-country requisites; no repeated plan selection. More state is shared across provider/manual routing, and Back returns to the exact parent. Special HSK 3.0 checkout retains its existing route. A bounded application-scope reporter drains immutable event DTOs, uses the original authenticated session generation and drops work on account replacement. No raw token/email/price/body is stored in telemetry. UI never waits for telemetry.
- Provider overview advertises `pro_analytics_version=1`; native clients attach correlation only after that version and the original bearer are confirmed. An older backend keeps its existing invoice body, so optional analytics cannot break payment during rollout.
- Exit offers use the same full-screen chrome/PWA gift pose, a Back action and canonical native UZ/RU/TJ copy with the owner’s explicit “buy Pro now / 20% on the first payment” marketing override; no second modal X. Back preserves the checkout draft; explicit decline closes without claim or invoice.
- Native bearer/capability validation authenticates the event route. Account locking/idempotent event IDs follow PWA; the server fixes transport, validates source/plan/method and rejects forged start/paid events. Invoice start persists correlation before provider IO; idempotent reused invoices keep their original attribution. The ledger writes paid beside the approved payment, excluding renewals.
- Admin reader adds `android_pro_attempt_funnel` only for Android/Overall, retains existing PWA metric, and uses the same compact read-only panel/stage labels. No new management controls. Native route/critical paths keep existing checkout/payment monitoring and route-to-Inbox chain coverage.
- Validate migration upgrade/refusal, UI/auth/replay/owner/Play guards, current PWA regression, delayed/native lifecycle tests, PostgreSQL route→event→ledger→Admin chain, refund/chargeback/cohort isolation and catalog/coverage CI. Use an isolated local PostgreSQL schema; never production data.

## Final screen audit
See [verification.md](verification.md) for each inspected window, the PWA reference and native/owner adaptations. The owner explicitly deferred learner PWA implementation to a separate PR; preserve its runtime files here.
