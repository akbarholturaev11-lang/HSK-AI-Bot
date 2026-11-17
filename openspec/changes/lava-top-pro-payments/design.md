# Design

## Context

See proposal.md for motivation and specs/lava-pro-subscription/spec.md for behavior. Current source facts that shape the approach (origin/main `1bc69dee`, Alembic head `0150_smart_reminder_rollout`):

- Every approval path ends in `app/services/admin_payment_review_service.py`: `lock_pending_payment` (User row, then Payment row) and `review_locked_payment(decision="approve")`, which calls `PaymentRepository.approve` (pending-only guarded UPDATE), `SubscriptionService.activate_plan` (extends from an unexpired `end_date`), preview restore, AI budget, portfolio profit and partner credit. Post-commit delivery/analytics is `_emit_admin_payment_review_effects` in `app/main.py`.
- `payments.payment_status == "pending"` feeds admin queues, inbox, counts and the "one pending checkout" rule. `Payment.amount` is an integer; `local_amount`/`local_currency` are free strings.
- Mini App and learner iPhone PWA share `app/static/subscription.html` (`/api/subscription-miniapp/*` vs `/api/v3/pwa/subscription/*` in `app/api/pwa_auth.py`). Android direct/desktop have separate adapters over the same services.
- Admin PWA commands: `pwa_step_up._ACTIONS`, prepare → WebAuthn → execute with `consume_step_up_in_mutation`, advisory-locked `bot_settings` CAS, content-free `AdminPwaCommandAudit`. Every `/api/admin/v1/*` route 404s when the PWA flag is off.
- lava.top (OpenAPI v1.22.0): server creates invoices (`POST /api/v3/invoice`), `GET /api/v2/invoices/{id}` is authoritative, webhooks carry `contractId`/`parentContractId` but no merchant metadata; refund/chargeback payloads carry no contract id. Webhook auth is a static `X-Api-Key` chosen by the merchant; retries for ~5 h; order not guaranteed.

## Goals / Non-Goals

**Goals:** reuse the single approval unit of work; make every grant API-verified and idempotent under concurrency; never lose a taken payment (kill-switch, pause, lost webhook); keep manual checkout behavior and data unchanged when the mode is `manual_only`.

**Non-Goals:** Play billing; HSK 3.0 via lava; replacing manual prices/QR/receipts; email-based account matching; automatic mass cancellation; promo-code discounts before phase 3 verification.

## Decisions

1. **Separate pre-payment state (`lava_invoices`) instead of a `payments` row in a new status.** A pending lava row in `payments` would leak into admin queues, pending counts, preview claims and checkout blocking. Alternative (filtering every consumer by method) touches many queries and is easy to miss. The `Payment` row is created only inside the activation transaction: lock User → lock `lava_invoices` row (FOR UPDATE) → `PaymentRepository.create(payment_status="pending", payment_method="lava")` → `review_locked_payment("approve")` → mark invoice paid with `payment_id` and granted window → commit → `_emit_admin_payment_review_effects(source_prefix="lava")`. The pending row is never visible to other transactions.
2. **Webhook is a trigger, the API is the proof.** Success events are verified with `GET /api/v2/invoices/{id}` outside any DB transaction (10 s timeout). Status must be COMPLETED, currency must match; renewals must be `SUBSCRIPTION_RENEWAL` with `parentInvoice.id` equal to a known first contract. API unavailable → 503 so lava retries; the reconcile worker also covers it.
3. **Idempotency keys.** `lava_invoices.contract_id` UNIQUE, `lava_invoices.payment_id` UNIQUE, `lava_webhook_events.dedupe_key` UNIQUE (`<eventType>:<contractId>` for payment events, `event_id` for refund/chargeback). Apply checks invoice status under its row lock; `repo.approve` is pending-only. Renewal rows are inserted with `ON CONFLICT DO NOTHING` semantics (unique contract) before locking.
4. **Terms.** `PLAN_DURATIONS` (manual) is untouched. `SUBSCRIPTION_PLAN_DURATIONS = {**PLAN_DURATIONS, "6_months": 180, "12_months": 365}` is used by activation, preview restore and PWA metrics so 6/12-month lava payments are first-class subscription payments, while manual give-access and manual checkout keep their existing allowlists.
5. **Money fields.** `Payment.amount` = rounded provider amount, `local_amount` = exact decimal string, `local_currency` = lava currency, `currency` = lava currency. `base_amount` = TJS equivalent via existing `SubscriptionCurrencyService.live_or_manual_usd_rates` so AI budget/portfolio work for RUB too. Exact amounts also live in `lava_invoices` (`Numeric(12,2)`). Phase 1 currencies: USD, RUB.
6. **Configuration.** Secrets and kill-switches in env (`LAVA_*`). Business settings in `bot_settings["lava_top_config_v1"]` JSON (mode, four terms with enabled/offer/periodicity/price snapshot, currency), written only by the passkey-bound `lava.settings` command with CAS. `effective_mode()` falls back to `manual_only` on any unsafe/unsupported state.
7. **Refund/chargeback matching.** No contract id in payload → match on our own stored invoice data: normalized buyer email (the one the user typed on our checkout, stored for the provider's cancel API), `tier_id == offer_id`, currency, full refund amount; pick the latest paid, non-revoked invoice. Exactly one → automatic revocation (end_date minus granted days, Payment → `refunded`/`chargeback`, portfolio profit removed, payment AI budget expired). Partial/none → `needs_review`. Chargeback outcome is closed by admin command because lava documents no resolution event.
8. **Revocation arithmetic.** Store `granted_days`. Revoke subtracts exactly those days from the current `end_date` (later renewals stay intact); if the result is not in the future the user becomes `expired`. Chargeback "won" adds the same days back via the normal extension rule.
9. **Kill-switch vs pause.** `LAVA_ENABLED`/mode gate only `start`. Webhook ingestion depends only on `LAVA_WEBHOOK_SECRET`. `LAVA_PROCESSING_PAUSED` stores events as `queued` (2xx) and the worker drains them after the pause.
10. **Reconciliation.** One asyncio worker in `lifespan`, Postgres advisory-lock lease per tick (single runner across replicas): every 5 min open invoices < 48 h; hourly active subscriptions via `GET /api/v1/subscriptions/{parent}`; daily unmatched sweep; drains `queued` events. ≤ 5 provider requests/s.
11. **Clients declare support.** `supports_lava=1` in the overview request; Play and old clients never send it. Phase 1 adds it only to `subscription.html`.

## Risks / Trade-offs

- [Provider amount differs from expected] → still grant (money taken), flag `needs_review`, alert admin.
- [Refund cannot be linked deterministically] → no silent revocation; admin review list + Telegram alert.
- [lava MONTHLY renews on calendar months while Pro adds 30 days] → renewal extends from current end or from now if expired; small gaps are visible to the user as an ordinary expiry; no paid days are lost.
- [Webhook secret leak] → API verification prevents fake grants even with a forged authenticated webhook; rotate secret in lava + env.
- [Buyer email is personal data] → stored only on our invoice rows (needed for lava cancel/refund matching), hashed in event rows, cleared by account purge.
- [Promo code renewal semantics unknown] → promo mapping stays empty until verified (phase 3).

## Migration Plan

1. Migration `0151_lava_top_payments` creates `lava_invoices` and `lava_webhook_events` (no change to existing tables). Downgrade refuses when either table has rows. Bootstrap model registration added for QA initializer.
2. Deploy with `LAVA_ENABLED=false`, mode `manual_only` → zero behavior change.
3. Staging acceptance with real lava payments (tasks group 9) before main promotion.
4. Production: set `LAVA_API_KEY`, `LAVA_WEBHOOK_SECRET`, configure lava webhook, run preflight, then the owner switches mode in Admin PWA.
5. Rollback: mode `manual_only` + `LAVA_ENABLED=false` (processing of taken payments continues). Emergency: `LAVA_PROCESSING_PAUSED=true`.

## Open Questions

- Does lava send a chargeback resolution signal? (Admin command covers it meanwhile.)
- Do lava promo codes apply to renewals? (Blocks phase 3 only.)
