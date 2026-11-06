# Tasks

## 1. Configuration and schema

- [x] 1.1 Add `LAVA_*` settings to `app/config.py` and `.env.example`; verified by effective-mode fallback tests in `tests/test_lava_payments.py` (sales off/no keys → manual_only).
- [x] 1.2 Add `LavaInvoice` and `LavaWebhookEvent` models, migration `0151_lava_top_payments` (refusing lossy downgrade) and QA bootstrap registration; verified upgrade → refused downgrade with rows → downgrade → re-upgrade on an isolated local PostgreSQL 15 cluster.
- [x] 1.3 Add `SUBSCRIPTION_PLAN_DURATIONS` (6/12 months) for activation, preview restore and PWA metrics while manual allowlists stay unchanged; verified by `test_twelve_month_term_grants_365_days` and `test_manual_allowlist_does_not_gain_lava_terms`.

## 2. lava client, config and preflight

- [x] 2.1 Implement `app/services/lava/client.py`; verified through the httpx MockTransport double in `tests/lava_fakes.py`.
- [x] 2.2 Implement `config.py` (bot_settings JSON, validation, `effective_mode`); verified fallback matrix tests.
- [x] 2.3 Implement `preflight.py` + `scripts/lava_preflight.py`; verified `tests/test_lava_preflight.py` (401, non-subscription product, missing currency price, missing flags).

## 3. Checkout, activation and webhook

- [x] 3.1 Checkout start/status/cancel with refusal reasons; verified `tests/test_lava_payments.py` and `tests/test_lava_checkout_api.py`.
- [x] 3.2 Verified idempotent activation and renewal through `review_locked_payment`; verified duplicate delivery tests and `tests/test_lava_postgres.py` (5 concurrent deliveries → one Payment).
- [x] 3.3 Webhook endpoint (auth, size limit, dedupe, queued pause, unmatched); verified auth/dedupe/pause tests.
- [x] 3.4 Refund/chargeback matching, revocation and cancellation handling; verified end_date arithmetic and needs_review tests.

## 4. Reconciliation worker

- [x] 4.1 Reconcile worker (open invoices, renewals, queued drain, overdue alert) with lease and lifespan wiring; verified missed-webhook, missed-renewal tests and PostgreSQL lease/SQL test. Daily unknown-subscription sweep deferred until lava confirms subscription id semantics.

## 5. Mini App and iPhone PWA

- [x] 5.1 Mini App and PWA lava endpoints and overview `lava` block (only with `supports_lava`); verified overview tests.
- [x] 5.2 `subscription.html`: centered Visa gateway (owner wording), lava terms, email, payment page, polling, auto-renew cancel, brand palette; verified UI contract test, i18n guards and mobile browser smoke (preview mode, UZ/RU/TJ).
- [x] 5.3 Return page and bot notices (refund, renewal failed, cancelled, chargeback) in UZ/RU/TJ; verified `i18n_build_all_catalogs.py --check` and `tests/test_lava_notifications.py`.

## 6. Admin PWA

- [x] 6.1 `pwa_lava.py` read/catalog + `lava.settings`, `lava.recheck`, `lava.link`, `lava.cancel`, `lava.chargeback`; verified `tests/test_admin_pwa_lava.py`.
- [x] 6.2 Finance → payment methods lava.top drawers and finance analytics channel split; verified shell/analytics tests. Authenticated browser e2e of the drawers not yet executed.
- [x] 6.3 `docs/admin-pwa/MANAGEMENT_COMMANDS_CONTRACT.md` updated.

## 7. Privacy and documentation

- [x] 7.1 Purge clears lava owner/email and retains refunded/chargeback payments anonymously; verified `test_account_purge_keeps_lava_money_facts_and_drops_email`.
- [x] 7.2 `docs/payments/LAVA_TOP.md` runbook, `PROJECT_MEMORY.md`, public subscription guide/FAQ (UZ/RU/TJ).

## 8. Phase 2 and 3 (separate delivery)

- [ ] 8.1 Android direct lava checkout (Play excluded) with tests and release checklist.
- [ ] 8.2 Desktop macOS/Windows lava checkout with Tauri allowlist and parity tests.
- [x] 8.3 Promo-code mapping (owner asked to do it now): admin-mapped codes per discount source+percent, server-resolved discount, first contract only; verified `tests/test_lava_promo_codes.py`. Renewal promo semantics still to be confirmed with lava support.

## 9. Integration acceptance

- [x] 9.1 Full non-e2e regression locally (CI synthetic env): branch 4934 passed / 28 failed vs clean `origin/main` 4893 passed / 28 failed — identical pre-existing failure set, no new failures.
- [ ] 9.2 Staging acceptance scenarios 1–11 from `docs/payments/LAVA_TOP.md` executed with real lava payments and evidence in `docs/payments/LAVA_TOP_STAGING_<date>.md`.
