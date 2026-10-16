# Universal native accounts

Android and desktop share one canonical `users.id` account model. Telegram,
Google and Apple can each be a first sign-in method. Provider availability
still depends on existing server credentials and the registered application
and redirect configuration in `OAUTH_SETUP.md`.

## Release hold

The owner requires all seven acceptance conditions below to be verified before
merging or pushing this feature to `main`, deploying it, or opening registration
to general use. Passing isolated tests does not waive missing product behavior
or real provider/staging checks. Keep the feature on `codex/universal-sign-in`
until the evidence is complete.

| Required condition | Current evidence and remaining gate |
| --- | --- |
| Existing Telegram Pro, XP, lessons, rating and payments stay unchanged | Backend/Android regressions and real-copy migration digests pass: all legacy billing, progress and XP/rating values are preserved. Real installed-client walkthroughs remain required. |
| Google/Apple users without Telegram can register, start a lesson, use AI Voice and buy Pro | Signup/learning/AI/voice have integration coverage. Provider-only Pro checkout is currently unavailable (`payment_telegram_required`); real provider and purchase tests remain required. |
| Parallel registration for one Google/Apple identity creates one `users.id` | Railway staging PostgreSQL 18 passes four concurrent Google attempts and four Apple attempts: one account per exact provider identity, with no email merge. Retain this check in CI. |
| Linking cannot grant access to another learner's Pro or progress | Ownership and identity/session revocation regressions cover isolation; verify the complete staged client flow as well. |
| A blocked account cannot evade its restriction through Google/Apple | Both-provider API tests cover blocking before verification and between approval and token consumption; refresh/revoked-proof protections also pass. Real staged provider walkthroughs remain required. |
| Android, desktop and Telegram Mini App show the same account data | A backend integration test checks explicitly linked Android/Windows/macOS logins plus MiniApp profile data share Pro, lesson progress, XP and rating. Installed-client comparison remains required. A Telegram-free account cannot authenticate a Telegram Mini App without a real Telegram identity. |
| Migrations pass on a staging copy matching the real schema, and backup restore succeeds | Historical `0101 → 0104` rehearsal passed with exact pre/post-migration restores. Production has since advanced to `0102_payment_review_preview`; integrate the new main and repeat against that current baseline before clearing this gate. |

Railway now has an isolated staging PostgreSQL service. No app or bot was
deployed, and no application environment or shared variables were cloned;
the database copy contains private learner data and must stay restricted. This
task made no production deployment. Independent upstream receipt-preview work
has since advanced main and production to `0102_payment_review_preview`. Do not run feature migrations or test
registrations against production. Do not describe the feature as launch-ready
until all rows have dated, reproducible evidence.

Read-only production schema inspection on 2026-10-16 found PostgreSQL 18 and
Alembic revision `0101_account_deletion_requests`. `users.telegram_id` and
`desktop_devices.telegram_id` are still required. `payments` still requires
`user_telegram_id` and has no canonical `user_id`. This is schema inventory,
not a staging migration or a backup-restore test.

### Completed database rehearsal

The later rehearsal on 2026-10-16 passed for the original `0101` baseline.
Final verification then found upstream `3fffa42e` and production revision
`0102_payment_review_preview`; the current-baseline database gate is open again
until integration and a fresh rehearsal. The historical
[sanitized evidence](UNIVERSAL_NATIVE_ACCOUNTS_STAGING_2026-10-16.json)
records the migration, both restores, concurrency results and outstanding
release gates without row values, credentials or database endpoints.

- The real `0101` backup was restored into two newly created staging databases.
  The baseline matched all 833 source column descriptors, 681 constraints and
  301 indexes. PostgreSQL's proven lossless literal-array cast rewrite in ten
  CHECKs and one partial index is normalized only for this inventory match.
- `0101 → 0104` passed over 61 data tables and 189,368 legacy rows, including
  2,113 accounts and 98 payment records. All existing rows and values were
  preserved except the declared canonical backfills and pending-link expiry.
  All 13,782 expected AI/voice owners were filled correctly; no owner or dedupe
  conflicts were found.
- Both the pre-migration and post-migration backups were restored into fresh
  databases. Exact schema, row multiset, account-key and sequence comparisons
  passed, including billing, progress, XP and rating digests. Live before/after
  hashes preserve defaults, widths, precision, constraints and indexes exactly
  except the explicitly permitted migration changes.
- Backups are retained privately outside Git. Staging has no running app or bot
  and this rehearsal made no production writes, production deployment or main
  push. This proves the database gate; it does not prove live OAuth, AI Voice,
  installed-client parity or Pro purchasing.

`scripts/rehearse_native_account_migration.py` only reads and compares; it never
migrates or restores a database. It requires an explicit approved staging
host/port/database, a production endpoint deny check, TLS, the read-only source
catalog inventory and one private random HMAC key shared by the run. Reports
are created with mode `0600` and never overwrite previous evidence. Migration
and `pg_dump`/`pg_restore` remain separate operator actions; always target a new,
empty staging database for restore. Run `snapshot` before and after, then
`compare --mode migration`; compare each backup restore to its own source with
`compare --mode restore`.

### Outstanding purchase implementation

Provider-only purchase requires an end-to-end canonical ownership change;
simply removing the Telegram guard is unsafe. Payment drafts/history/status,
admin approval/rejection, paid-term activation, paid AI budgets and device
notifications must all resolve the same authenticated `users.id`. A NULL
Telegram field must never select another provider-only user's payment or
notification device. Preserve prices, discounts, approval policy, renewal
dates and financial retention; financial records must not disappear through
a new cascading account-owner FK.

Android Play is currently consumption-only, with no BillingClient, backend
purchase-token verification or configured store-product integration. Direct
and desktop manual payment support does not prove Play in-app purchasing.
Play purchase acceptance requires configured products/testers, real store
verification and acknowledgement, replay/account-binding checks and
subscription lifecycle reconciliation. See the official
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
- Manual Telegram checkout and referral rewards retain their current policy.
  Provider-only accounts can read their subscription state, but these actions
  return `payment_telegram_required` / `referral_telegram_required` instead of
  fabricating an ID, payment or invitation. This change does not add store
  billing, email merging or a Telegram-attachment feature.

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

1. Apply `alembic upgrade head` through `0104_native_ai_voice_ownership` using
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

- `0102`: nullable real Telegram metadata on users/devices, selected language
  and identity/session proof snapshots on link requests. Existing pending link
  proofs without a session snapshot expire and must be started again.
- `0103`: nullable transport metadata, canonical-owner backfill and canonical
  event/notification dedupe keys.
- `0104`: canonical AI budget/event/voice ownership, backfill and deletion FKs.

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
  tests.test_native_account_acceptance
python -m unittest tests.test_native_account_concurrency
python -m unittest tests.test_native_account_rehearsal
```

Validation on 2026-10-16, integrated source commit `2b6d87ed`:

- Backend regression selection: 933 tests and 679 subtests passed.
- New backend CI selection against isolated PostgreSQL: 44 tests passed,
  including concurrent registration and identity-change tests.
- Additional acceptance/security selection: 65 tests and 15 subtests passed,
  including both-provider block boundaries and legacy paid-account data
  shared across native APIs and the MiniApp profile service. OIDC verification
  is mocked in this selection.
- Staging helper, migration and acceptance selection: 25 tests passed. The
  PostgreSQL 18 staging concurrency selection passed three tests and two
  provider subtests. CI uses PostgreSQL 18 to match the deployed database major.
- Android Direct/Play: 1009 unit tests, 26 native Compose checks, nine static
  gates and four app/test APK builds passed.
- Shared desktop: 29 JavaScript contracts, 24 Rust tests and five focused
  browser authentication checks passed. Five unrelated failures in the full
  desktop browser suite also reproduce on the previous deletion baseline;
  the full desktop browser suite is not green.

These checks do not satisfy the outstanding release gates above. In
particular, a safe error for unsupported checkout is not a successful Pro
purchase, and a mocked voice/provider response is not a real service test.

Native and browser fixtures do not prove real provider console configuration,
deployed migration status or signed store/installer release. Those checks
remain part of the rollout above.
