# Universal native accounts

Android and desktop share one canonical `users.id` account model. Telegram,
Google and Apple can each be a first sign-in method. Provider availability
still depends on existing server credentials and the registered application
and redirect configuration in `OAUTH_SETUP.md`.

## Release hold

The owner requires all seven acceptance conditions below to be verified before
merging or pushing this feature to `main`, deploying it to production, or opening registration
to general use. Passing isolated tests does not waive missing product behavior
or real provider/staging checks. Keep the feature on `codex/universal-sign-in`
until the evidence is complete.

| Required condition | Current evidence and remaining gate |
| --- | --- |
| Existing Telegram Pro, XP, lessons, rating and payments stay unchanged | Backend/Android regressions and real-copy migration digests pass: all legacy billing, progress and XP/rating values are preserved. Real installed-client walkthroughs remain required. |
| Google/Apple users without Telegram can register, start a lesson, use AI Voice and buy Pro | Signup/learning/AI/voice and canonical manual Pro checkout/approval have integration coverage. Direct Android and desktop need no Telegram for Pro; real provider, upstream Voice and purchase walkthroughs remain required. Play still has no in-app billing. |
| Parallel registration for one Google/Apple identity creates one `users.id` | Railway staging PostgreSQL 18 passes four concurrent Google attempts and four Apple attempts: one account per exact provider identity, with no email merge. Retain this check in CI. |
| Linking cannot grant access to another learner's Pro or progress | Ownership and identity/session revocation regressions cover isolation; verify the complete staged client flow as well. |
| A blocked account cannot evade its restriction through Google/Apple | Google/Apple identities already linked to a blocked canonical account cannot sign in, consume approved proof, refresh or attach another login. Both-provider regressions pass; real staged provider walkthroughs remain required. An unrelated new provider subject cannot be inferred to belong to the same person from email. |
| Android, desktop and Telegram Mini App show the same account data | A backend integration test checks explicitly linked Android/Windows/macOS logins plus MiniApp profile data share Pro, lesson progress, XP and rating. Installed-client comparison remains required. A Telegram-free account cannot authenticate a Telegram Mini App without a real Telegram identity. |
| Migrations pass on a staging copy matching the real schema, and backup restore succeeds | PASS: isolated Railway PostgreSQL 18 copy matching `0102_payment_review_preview` passed upgrades through `0106`, with exact pre/post-backup restores over 61 tables and 190,155 legacy rows. Evidence below; this does not clear other release gates. |

Railway now has an isolated staging PostgreSQL service. No app or bot was
deployed, and no application environment or shared variables were cloned;
the database copy contains private learner data and must stay restricted. This
task made no production deployment. Independent upstream receipt-preview work
has since advanced main and production to `0102_payment_review_preview`. Do not run feature migrations or test
registrations against production. Do not describe the feature as launch-ready
until all rows have dated, reproducible evidence.

Read-only production inspection found PostgreSQL 18 at
`0102_payment_review_preview` after upstream `3fffa42e`. Production still
requires Telegram on users/devices/payments and has no canonical payment
owner column. The universal-account changes remain confined to this branch
and isolated staging.

### Completed database rehearsals

The production-schema copy passed the full `0102 → 0106` chain on 2026-10-17:
61 data tables, 190,155 legacy rows, 2,118 users and 100 payments. All 835
source column descriptors, 682 constraints and 301 indexes matched the
restored baseline. Exact migration and pre/post-backup restore comparisons
preserved billing, progress, XP/rating, account keys and sequences. All 13,905
expected owners were backfilled, including 97 existing payments; the remaining
historical financial records were preserved. Receipt-preview flags and pointers
were unchanged. The source backup came from the earlier verified `0102` copy;
the production schema head was rechecked read-only before this fresh rehearsal.
See [current sanitized evidence](UNIVERSAL_NATIVE_ACCOUNTS_STAGING_PAYMENTS_2026-10-17.json).

The earlier
[`0102 → 0105` evidence](UNIVERSAL_NATIVE_ACCOUNTS_STAGING_PREVIEW_2026-10-17.json)
and [`0101 → 0104` evidence](UNIVERSAL_NATIVE_ACCOUNTS_STAGING_2026-10-16.json)
remain historical records of those exact revisions.

Backups are retained privately outside Git. Staging runs no app or bot;
these rehearsals make no production writes, production deployment or main
push. Database preservation does not prove real OAuth, upstream AI Voice,
installed-client parity or successful bank/store purchases.

`scripts/rehearse_native_account_migration.py` only reads and compares; it never
migrates or restores a database. It requires an explicit approved staging
host/port/database, a production endpoint deny check, TLS, the read-only source
catalog inventory and one private random HMAC key shared by the run. Reports
are created with mode `0600` and never overwrite previous evidence. Migration
and `pg_dump`/`pg_restore` remain separate operator actions; always target a new,
empty staging database for restore. Run `snapshot` before and after, then
`compare --mode migration`; compare each backup restore to its own source with
`compare --mode restore`.

### Canonical Pro purchasing

Manual Pro purchases belong to `users.id`, independently of the login provider.
Direct Android and both desktop platforms reuse the existing prices, discounts,
bank/card details, QR payloads, receipt upload and human admin review. New
payments carry the canonical owner and optional real Telegram metadata;
migration `0106` backfills existing positive Telegram owners. Bare numeric
service arguments remain real Telegram IDs, never canonical IDs.

Checkout locks the canonical user before checking pending payments. Both admin
review surfaces use the same lock order and the existing one-time status
transition, so replay cannot extend paid terms twice. Bot receipt edits use the
same order, check failed status transitions and recheck the fresh selected plan;
a late screenshot cannot reopen a reviewed payment or claim a new preview.
Receipt approval cannot unblock a blocked owner; the separate explicit manual
admin grant keeps its existing behavior. Approval updates only the
owner's existing 10/30/90-day period, paid AI budget and preview ticket. Rejection
revokes only that receipt's preview without refunding the ticket or changing a
paid term. Status, history, discounts, finance and Android push targets use the
same owner; matching NULL Telegram metadata grants no access to another user.

Approved financial facts do not cascade with account deletion. Purge removes
receipt evidence and positive account association while preserving the existing
anonymous accounting grouping and totals. Other payment state is deleted.
The separate HSK 3.0 one-time checkout and Telegram referral/handoff paths remain
explicitly Telegram-specific; this Pro change does not silently open them.

Android Play remains consumption-only, without BillingClient, server purchase
verification or configured store products/testers. Manual Direct/desktop
checkout does not prove Play purchasing. Play requires configured products/base
plans, real store verification and acknowledgement, replay/account binding,
restore and subscription lifecycle reconciliation through the same canonical
entitlements. See the official
[Play Billing integration guide](https://developer.android.com/google/play/billing/integrate.html).

## Identity and access

- Google/Apple creation follows the existing signature, issuer, audience,
  nonce, freshness, state and PKCE verification. The server resolves the exact
  provider/subject HMAC. An unknown verified subject creates a new user and
  identity atomically; a known subject reuses its owner.
- Email is display metadata. To add another login to an existing account,
  authenticate that account and explicitly connect the provider from Profile.
  Matching email never merges accounts or moves progress/subscriptions.
- A real Telegram user ID stays unique and optional. Google/Apple users have
  `telegram_id = NULL`; internal numeric account IDs are never substituted
  into Telegram columns or sent as Telegram chat IDs.
- The existing starter policy is reused (`status=trial`, five initial
  questions, no paid or Pro-trial dates). This is distinct from the explicitly
  started seven-day Pro trial. Paid periods, budgets, eligibility, daily caps
  and anti-abuse rules are unchanged.
- Native ownership uses authenticated canonical users, refreshed from the
  database. Legacy integer service callers still mean real Telegram IDs.
  Canonical backfilled rows and narrowly scoped legacy fallbacks remain
  compatible; a missing Telegram ID never authorizes other NULL-owner rows.
- Direct/desktop Pro checkout works for canonical provider-only accounts.
  Telegram handoff, HSK 3.0 one-time purchase and referral rewards retain their
  real-Telegram requirements with explicit availability errors. No synthetic
  Telegram ID, automatic email merge or store billing is introduced.

## Session and identity safety

Token minting remains on the existing link/status path. Creation, callbacks
and explicit provider linking never return tokens. Device binding, refresh
rotation/reuse detection, TTLs and server-owned entitlement checks remain.

Identity changes take the canonical user lock before checking/removing login
methods. A provider-only account cannot disconnect its last method. Disconnect
revokes other sessions, and an approved sign-in must still reference the exact
existing identity when consumed. A pending native provider-link request must
still have a valid originating session and device. Snapshot IDs are not FKs,
so unlink does not acquire pending-request locks in reverse order. A blocked
user cannot refresh; account deletion retains its narrow blocked-user path.

Android and shared desktop code guard late start/poll replies and competing
provider attempts. Cancellation cannot install credentials from an abandoned
attempt or consume the new attempt's response. UZ/RU/TJ copy describes provider
availability and the remaining Telegram-only actions.

## Schema and rollout

Run these steps only after all release gates above are satisfied. This
checklist does not authorize a production migration or release during the hold.

1. Apply `alembic upgrade head` through `0106_canonical_payment_ownership` using
   the normal deployment migration process before releasing new clients.
2. Deploy the backend and then the tested Android/desktop clients. No new
   provider secret or redirect URI is introduced by this feature.
3. Check configured provider discovery, Google native ID-token sign-in and
   Google/Apple browser callbacks against real disposable test accounts.
4. Verify first signup, repeated signup, sign-out/re-entry, profile/onboarding,
   a saved lesson/practice result, limits/trial and explicit provider linking.
5. Verify provider unlink, revoked/blocked session refusal, final-method
   protection and the public/in-app account-deletion flow.

Migration details:

- `0103` (after `0102_payment_review_preview`): nullable real Telegram metadata on users/devices, selected language
  and identity/session proof snapshots on link requests. Existing pending link
  proofs without a session snapshot expire and must be started again.
- `0104`: nullable transport metadata, canonical-owner backfill and canonical
  event/notification dedupe keys.
- `0105`: canonical AI budget/event/voice ownership, backfill and deletion FKs.
- `0106`: canonical payment ownership and payment/entry Telegram nullability;
  positive Telegram-owner backfills preserve amounts, statuses and dates. The
  financial owner has no cascading FK; purge explicitly anonymizes approved
  facts. Downgrade preflights both payment and entry data.

The existing receipt-preview opportunity and payment pointer survive these
migrations. Its separate capped budget now records canonical ownership while
retaining real Telegram compatibility. The preview remains unpaid, does not
replace an existing paid/referral/Pro-trial window and is claimed only after an owned receipt is submitted. Signup alone never
claims a preview; canonical Pro receipts follow the same one-ticket/$0.50 policy.

Upgrades tolerate an already bootstrapped schema. Downgrades preflight and
refuse provider-only data rather than discarding accounts or progress. Do not
roll back to code that assumes every learner has Telegram once such accounts
exist. Account deletion retains its financial exceptions and operations guide
at `ACCOUNT_DELETION_OPERATIONS.md`.

## Regression checks

The backend CI includes the new signup, migration, ownership/lifecycle and
desktop-provider tests. PostgreSQL concurrency tests use a dedicated test
database and disposable per-test schemas through
`NATIVE_ACCOUNT_TEST_DATABASE_URL`; never point this at a production database.

```sh
python -m unittest tests.test_native_account_signup tests.test_native_account_migration \
  tests.test_native_account_learning tests.test_native_account_ai_voice \
  tests.test_native_account_lifecycle tests.test_desktop_provider_accounts \
  tests.test_native_account_acceptance tests.test_payment_review_preview \
  tests.test_native_account_payments tests.test_native_payment_repository \
  tests.test_native_payment_migration tests.test_native_payment_discounts_finance \
  tests.test_payment_service_receipt_lock
python -m unittest tests.test_native_account_concurrency
python -m unittest tests.test_native_account_rehearsal
```

Validation on 2026-10-17, source `09aa4d48` (backend base `3fffa42e`):

- Final integrated backend selection: 1,070 tests and 766 subtests passed,
  with seven existing configuration/asyncpg cleanup warnings. Four PostgreSQL
  cases are skipped in this SQLite selection and run separately below.
- Isolated Railway PostgreSQL 18 payment concurrency: two tests passed. Parallel
  requests for the same canonical user share one pending payment; another user
  remains independent. The earlier first-signup race also passed one test and
  four subtests, using four concurrent attempts per Google/Apple subject and
  safe starter/preview defaults. External identity verification is mocked.
- Isolated Railway PostgreSQL 18 receipt/admin concurrency: both races passed,
  in addition to the local PostgreSQL 15 run within the 51-test
  receipt/preview/checkout selection, with no skips. Reviewed
  receipt edits cannot claim another preview or open a replacement payment;
  user-before-payment locking prevents the old bot/admin deadlock.
- Current desktop browser checkout: three checks passed, including successful
  receipt submission without Telegram and the server-restricted error state.
  Real bearer Android Direct tests cover overview, quote, currency, receipt,
  duplicate submission, canonical status and other-account refusal.
- Historical Android validation at pre-rebase `2b6d87ed`: 1009 unit tests,
  26 native Compose checks, nine static gates and four app/test APK builds
  passed across Direct/Play. Historical shared desktop validation passed
  29 JavaScript contracts, 24 Rust tests and five focused auth browser checks.
  Five unrelated full desktop browser failures also reproduce on the deletion
  baseline; the full desktop browser suite is not green.

Android/desktop source is unchanged by this canonical payment integration; full
client build/unit suites were not rerun against `09aa4d48`. Current backend and
browser checks do not replace installed-client/provider/purchase acceptance.
Later main `160a51d6` was inspected: its changes since the backend reference are
Mini App localization/inventory and CI, with no auth, payment backend or schema
change. It is not claimed as this feature's fully integrated test baseline.

These checks do not satisfy the outstanding release gates above. In
particular, a safe error for unsupported checkout is not a successful Pro
purchase, and a mocked voice/provider response is not a real service test.

Native and browser fixtures do not prove real provider console configuration,
deployed migration status or signed store/installer release. Those checks
remain part of the rollout above.
