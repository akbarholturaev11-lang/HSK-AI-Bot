# Tasks

## 1. Configuration and schema

- [ ] 1.1 Add `LAVA_*` settings to `app/config.py` and `.env.example`; verify `tests/test_lava_config.py` covers defaults (sales off, no secrets).
- [ ] 1.2 Add `LavaInvoice` and `LavaWebhookEvent` models, migration `0151_lava_top_payments` (refusing lossy downgrade) and bootstrap registration; verify upgrade/downgrade on local Postgres and model import test.
- [ ] 1.3 Add `SUBSCRIPTION_PLAN_DURATIONS` (6/12 months) used by activation, preview restore and PWA metrics while manual allowlists stay unchanged; verify activation +180/+365 and manual endpoints still rejecting 6/12 months.

## 2. lava client, config and preflight

- [ ] 2.1 Implement `app/services/lava/client.py` (create/get invoice, products, subscription get/cancel; no POST retry; secrets never logged); verify with httpx MockTransport tests.
- [ ] 2.2 Implement `config_service.py` (bot_settings JSON, validation, `effective_mode`); verify fallback matrix tests.
- [ ] 2.3 Implement `preflight_service.py` + `scripts/lava_preflight.py`; verify 401/no product/wrong periodicity/missing currency price tests.

## 3. Checkout, activation and webhook

- [ ] 3.1 Implement checkout start/status/cancel with refusal reasons (disabled term, active subscription, pending manual receipt, open chargeback); verify unit tests.
- [ ] 3.2 Implement verified idempotent activation and renewal through `review_locked_payment`; verify single Payment under duplicate delivery and Postgres concurrency test.
- [ ] 3.3 Implement webhook endpoint (auth, size limit, dedupe, queued pause, unmatched); verify auth/dedupe/pause tests.
- [ ] 3.4 Implement refund/chargeback matching and revocation plus cancellation handling; verify end_date arithmetic and needs_review tests.

## 4. Reconciliation worker

- [ ] 4.1 Implement reconcile worker (open invoices, renewals, queued drain, missing-renewal alert) with advisory lease and lifespan wiring; verify missed-webhook and race tests.

## 5. Mini App and iPhone PWA

- [ ] 5.1 Add Mini App and PWA lava endpoints and overview `lava` block (only with `supports_lava`); verify manual_only overview unchanged.
- [ ] 5.2 Update `subscription.html`: Visa question, lava terms, email, open payment, waiting, cancel auto-renew; UZ/RU/TJ catalogs; verify UI contract tests and mobile smoke.
- [ ] 5.3 Add return page and bot/user notices (refund, renewal failed, cancelled) in UZ/RU/TJ; verify i18n build `--check`.

## 6. Admin PWA

- [ ] 6.1 Add `pwa_lava.py` read + `lava.settings`, `lava.recheck`, `lava.link`, `lava.cancel`, `lava.chargeback` commands with step-up, CAS and audit; verify `tests/test_admin_pwa_lava.py`.
- [ ] 6.2 Add V10 System → payments "lava.top" row and drawer following BROWSER_UI_CONTRACT; verify shell tests and browser e2e.
- [ ] 6.3 Update `docs/admin-pwa/MANAGEMENT_COMMANDS_CONTRACT.md`.

## 7. Privacy and documentation

- [ ] 7.1 Clear `lava_invoices.buyer_email` on account purge; verify purge test.
- [ ] 7.2 Write `docs/payments/LAVA_TOP.md` runbook and update `PROJECT_MEMORY.md` payment section.

## 8. Phase 2 and 3 (separate delivery)

- [ ] 8.1 Android direct lava checkout (Play excluded) with tests and release checklist.
- [ ] 8.2 Desktop macOS/Windows lava checkout with Tauri allowlist and parity tests.
- [ ] 8.3 Promo-code mapping after verifying lava renewal semantics.

## 9. Integration acceptance

- [ ] 9.1 Full regression of existing payment/subscription/admin PWA tests passes locally.
- [ ] 9.2 Staging acceptance scenarios 1–11 from the plan executed with real lava payments and evidence in `docs/payments/LAVA_TOP_STAGING_<date>.md`.
