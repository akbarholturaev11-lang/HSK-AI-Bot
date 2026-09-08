# Admin statistics and Gemini free-tier accounting

## Ready locally

- New Gemini free-tier requests retain tokens and log $0; paid-tier Gemini and
  OpenAI fallback retain estimated costs. Usage tier is recorded with each event.
- Admin finance displays model, tier, recorded requests, tokens and cost.
- Telegram revenue separates currencies. Abandoned/empty voice sessions are
  excluded. D1/D7 use fully observed cohorts with explicit bounds.
- Historical costs and budgets have not been rewritten. No production deployment
  or messages to learners were performed.

## Rollout

1. Back up the production DB using the existing provider backup process.
2. Confirm `GEMINI_BILLING_TIER=free` for the owner's current API project. Set
   `paid` if that Google project changes billing tier; the model name alone
   cannot identify its billing tier. OpenAI fallback remains chargeable.
3. Run `python -m alembic upgrade head` before serving the updated code.
   Revision `0080_ai_usage_billing_tier` is additive and bootstrap-safe.
4. Check a new Gemini event: model, tokens, billing_tier=free, cost_usd=0,
   unchanged AI budget. Confirm OpenAI/paid rows are still shown separately.
5. Open admin statistics in Telegram: currency totals, voice, weekly D7,
   free vs paid AI rows and source freshness. Compare with read-only SQL totals.

## Historical reconciliation — still pending

The local environment has no production DB credentials or configured AI keys.
The date range when Gemini was free has not been established. Do not infer that
all past Gemini use was free merely because today's setting is free.

With the verified UTC time range and production environment configured, run:

```sh
python -m scripts.audit_ai_costs --since '<confirmed-start-UTC-ISO>' --until '<exclusive-end-UTC-ISO>'
```

The script enforces read-only transactions and prints grouped model/source/tier,
tokens, recorded cost and count of linked budgets without learner IDs or secrets.
It also works before migration. Capture this output before planning a correction.

After owner confirmation, prepare a separate audited transaction using a backup:
identify only Gemini events in the confirmed free interval, retain their original
values for recovery, correct those costs, and reconcile each linked budget's
segment/current-window spend from its dated event ledger. Do not zero whole
budgets, refund OpenAI costs, or revive expired subscriptions automatically.
Historical budget exhaustion/cooldown may still block access until this is done.
Existing gates are intentionally preserved to prevent unbudgeted paid fallback.

## Verification

- Billing/statistics focused suite: 62 passed and 64 subtests passed.
- Full backend suite: 1194 passed, 14206 subtests passed; three known unrelated
  failures in HSK2 free-part expectations and mistake-review sentence material.
- Mobile admin browser smoke: passed, including free Gemini and paid OpenAI rows.
- Six course/map/lesson/exam/subscription browser smoke scenarios: passed.
- Migration: legacy cost preserved, default legacy tier, repeated upgrade and
  downgrade verified on SQLite. Production PostgreSQL migration not yet run.

## Admin release feedback draft

Release: **Aniq AI xarajati va admin statistikasi**.

Target: admins only. Draft message: “Gemini bepul foydalanishi endi $0 bilan,
token sarfi esa alohida ko'rinadi. Daromad valyutalari, voice sessiyalari va
haftalik D7 hisoblari tuzatildi. Eski AI taxminlari tekshirilmaguncha saqlanadi.”

Test location/button: **Sinab ko'rish → Admin Mini App → Statistika**, with an
instruction to open the statistics tab if no direct tab link is supported.
Rating: “Statistika tushunarlimi? 1–5 baholang.”
Reward disclosed beforehand: “Bu ichki admin tekshiruvi; mukofot yoki chegirma
berilmaydi.” Confirmation: “Tekshiruv fikringiz qabul qilindi.”
Watch: Gemini free rows with nonzero cost (must be zero), billed OpenAI rows,
legacy cost remaining, budget changes, weekly D7 denominator and discarded
abandoned voice sessions. Do not broadcast to learners. Send any feedback request
only after deployment and explicit admin approval through the existing module.
