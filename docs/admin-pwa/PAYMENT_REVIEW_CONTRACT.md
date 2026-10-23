# Admin PWA payment review contract (branch-only, flag OFF)

## Shared transaction

`app/services/admin_payment_review_service.py` owns only the locked decision.
It never commits/rolls back or sends notifications. Both the existing Telegram
Mini App adapter and the dedicated PWA adapter use this unit of work. Checkout
and review acquire the canonical User before the refreshed Payment; pending
state and ownership are rechecked after waiting. Conditional repository writes
also reject duplicate decisions. Existing Pro duration, preview, budget,
portfolio, partner-credit and HSK 3.0 grant services remain authoritative.

`SubscriptionService.activate_plan(deferred_events=...)` defers trial analytics
when called by this shared decision. Other callers retain the existing default.
The Telegram adapter commits as before, then emits its existing analytics and
notifications. `/admin.html`, the legacy route and Telegram guard are unchanged.

## Browser contract

Both endpoints are JSON POSTs with bounded bodies, duplicate-key rejection,
exact HTTPS host/Origin, Fetch Metadata, a valid HttpOnly browser cookie and
no-store responses. The rollout flag remains `ADMIN_PWA_ENABLED=false`.

1. `/api/admin/v1/payments/prepare-review` accepts exactly `payment_id`,
   `decision` (`approve`/`reject`), `reason` (null or an exact 1–300 character
   rejection reason; no trimming/truncation or approval reason). It requires a
   current WebAuthn admin session and returns the actual server-owned operation.
2. The confirmation UI must display this operation's canonical owner, payment,
   amount/currency, product, decision and reason, then pass its returned
   `{action,target,payload}` to the existing step-up options/verify endpoints.
3. `/api/admin/v1/payments/review` accepts that payload plus `step_up_id`.
   It never accepts a client digest. IDs/amounts are strict integers, not bools,
   strings or floats; unknown fields are rejected. There is no silent approval.

The existing SHA-256 operation commitment covers version 1, action
`payments.review`, target = decimal Payment ID, and the **entire** strict payload:
`payment_id`, `decision`, `reason`, `expected`. The `expected` snapshot contains:

- canonical `user_id`, stored `payment_owner_id`, current `owner_telegram_id`,
  historical `payment_telegram_id` (nulls stay distinct);
- exact positive integer `amount`, exact stored `currency`, `base_amount`;
- `plan_type`, `payment_method`, `source`, `discount_source`, `discount_percent`,
  `discount_campaign_id`;
- `card_country`, `local_amount`, `local_currency`, `exchange_rate`;
- UTC `submitted_at` and `receipt_sha256` of the stored receipt reference
  (the actual attachment reference is not returned or stored in audit).

The execution transaction consumes the receipt using the existing verifier,
then locks/revalidates the payment and canonical owner and requires exact
snapshot equality before calling the shared financial unit. Lock order is
step-up → credential → session → admin User → target User → Payment. Expiry is
rechecked after lock waits. A stale snapshot, nonpending payment, revoked
session/admin/key, signature error, replay or any downstream failure rolls back
receipt consumption and **all** financial/audit/outbox writes. Deadlocks/DB
errors fail closed; no automatic financial retry is introduced.

## Audit and delivery

Migration `0117_admin_pwa_payment_reviews` adds immutable application-written
financial facts (`admin_pwa_payment_reviews`) and a separate mutable delivery
outbox (`admin_pwa_payment_outbox`). Audit records canonical actor/target,
payment, exact decision/payload/hash, step-up, applied status and UTC timestamp.
Unique payment and step-up IDs provide durable deduplication. Records do not
cascade away with session, credential or account deletion. Migration downgrade
refuses a nonempty audit table; explicit financial retention/reconciliation is
required before any operational downgrade. No old migration is changed.

After commit, the request adapter calls an internal dispatcher which durably
claims `pending → attempting` before invoking the existing analytics and
notification transports. Concurrent/repeated dispatch attempts cannot send
again. Success is named **attempted**, not delivered: current transport helpers
are best effort and may suppress downstream delivery failures. An exception
leaves `uncertain`; a process crash after claim leaves `attempting`. Neither is
automatically retried because Telegram/FCM lack an end-to-end idempotency key.
A crash before claim leaves `pending`. Pending recovery/operator reconciliation
and monitoring remain a follow-up; no public resend API is exposed. This is
at-most-once attempted delivery, **not** an exactly-once delivery guarantee.
A post-commit delivery failure never reports the already-applied payment as a
financial failure or re-applies its subscription.

## Evidence boundaries

Tests use disposable fixtures and actual SQL rollback. ES256 integration tests
exercise the real py_webauthn verifier. PostgreSQL tests cover two receipts for
one payment, one receipt twice, rollback/waiting approval, Telegram/PWA races,
outbox contention, lock-wait expiry, actual 0117 DDL and audit retention.
The migration chain is tested only from the synthetic stamped 0109 baseline;
the existing unrelated cold-start failure at 0011 remains.

No browser confirmation UI, installed PWA, physical authenticator, real payment,
Google/Telegram provider E2E, production migration or deployment is claimed.
The financial API is branch-only and disabled by default. Do not enable it
until the real confirmation UI and staging/device acceptance are completed.
