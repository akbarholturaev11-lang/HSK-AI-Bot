# Universal native accounts

Android and desktop share one canonical `users.id` account model. Telegram,
Google and Apple can each be a first sign-in method. Provider availability
still depends on existing server credentials and the registered application
and redirect configuration in `OAUTH_SETUP.md`.

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
  tests.test_native_account_lifecycle tests.test_desktop_provider_accounts
python -m unittest tests.test_native_account_concurrency
```

Native and browser fixtures do not prove real provider console configuration,
deployed migration status or signed store/installer release. Those checks
remain part of the rollout above.
