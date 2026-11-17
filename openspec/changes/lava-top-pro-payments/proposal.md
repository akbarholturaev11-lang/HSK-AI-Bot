# Proposal

## Why

HSK AI Pro is sold only through the manual receipt flow (transfer/QR → screenshot → admin approval). The owner wants a second, automated path through lava.top recurring subscriptions while the manual path stays byte-for-byte unchanged. This touches payments, entitlements, a new external provider, a schema change and several clients, so it needs an explicit delta instead of a direct task (AGENTS.md "Selective OpenSpec planning"). Authoritative sources: `AGENTS.md`, `AI_RULES.md`, `PROJECT_MEMORY.md` (payments/access sections), `docs/admin-pwa/MANAGEMENT_COMMANDS_CONTRACT.md`, `docs/admin-pwa/BROWSER_UI_CONTRACT.md`, and the official lava.top OpenAPI v1.22.0 (`https://gate.lava.top/docs/documentation.yaml`).

## What Changes

- New server-owned lava.top checkout: the server creates the lava invoice for a configured offer, keeps the returned contract id as the only ownership link, and grants Pro only after the lava API itself reports the contract COMPLETED (webhook is a trigger, never proof).
- Separate lava Pro terms: 1, 3, 6 and 12 months (lava MONTHLY / PERIOD_90_DAYS / PERIOD_180_DAYS / PERIOD_YEAR). Each term can be shown or hidden by the admin. The manual 10/30/90-day plans, prices and validation stay unchanged.
- Admin checkout mode: `manual_only` (default, current behavior), `lava_only`, `both`. In `both`, the buyer first answers "Do you have a Visa card?": No → current manual flow, Yes → lava flow. Unsafe or unsupported states always fall back to `manual_only`.
- Recurring renewals extend Pro; cancellation keeps the paid term; full refund and chargeback automatically shorten Pro by the days of the matched payment (ambiguous cases go to admin review); chargeback outcome is closed by the admin.
- Reconciliation worker repairs lost webhooks; sales kill-switch and processing pause never drop already-taken payments.
- Admin PWA lava.top section: connection preflight, settings (mode, terms, offers, currency), recheck, link unmatched contract, cancel auto-renewal, chargeback outcome.
- Phase 1 clients: Telegram Mini App and learner iPhone PWA (shared `subscription.html`) plus bot notices. Android direct and macOS/Windows desktop follow in phase 2 against the same API; Play never receives lava. In-app discounts map to lava promo codes only after renewal behavior is verified (phase 3).

## Capabilities

### New Capabilities

- `lava-pro-subscription`: Automated HSK AI Pro sale through lava.top recurring subscriptions: checkout mode selection, invoice ownership, verified activation and renewal, cancellation, refund/chargeback revocation, reconciliation, kill-switch and admin control.

### Modified Capabilities

None. Existing manual checkout/review behavior is preserved and has no OpenSpec capability yet.

## Impact

- Backend: new `app/services/lava/`, `app/api/lava_webhook.py`, lava endpoints beside the Mini App/PWA subscription routes, `SubscriptionService.PLAN_DURATIONS` gains 6/12-month terms (manual plans unchanged), reuse of `admin_payment_review_service.review_locked_payment` and `_emit_admin_payment_review_effects`.
- Schema: migration `0151_lava_top_payments` (`lava_invoices`, `lava_webhook_events`); new terminal payment statuses `refunded`/`chargeback` for lava-originated payments only.
- Admin PWA: new `pwa_lava.py` router, step-up actions, V10 System → payments row, UZ/RU/TJ copy.
- Clients: `app/static/subscription.html` (Mini App + iPhone PWA). Phase 2: Android direct flavor, desktop (Tauri allowlist + UI).
- Config: `LAVA_ENABLED`, `LAVA_API_KEY`, `LAVA_WEBHOOK_SECRET`, `LAVA_API_BASE`, `LAVA_PROCESSING_PAUSED`, `LAVA_WEBHOOK_ALLOWED_IPS`.
- Excluded: Play billing, HSK 3.0 unlock, manual price/QR/receipt logic, email-based account matching.
- Risks: double grant, forged webhook, lost webhook, wrong-user grant, refund mismatch. Mitigations are specified in design.md.
- Rollback: `LAVA_ENABLED=false` + mode `manual_only` stops new sales while processing of taken payments continues; `LAVA_PROCESSING_PAUSED=true` queues events durably; migration downgrade refuses to drop non-empty financial evidence.
