# HSK AI account deletion

## Ownership and confirmation

Android Profile / Security uses the existing bearer session to prepare a
10-minute, account-bound deletion capability. It submits only when the learner
explicitly confirms. Signed Telegram Mini App initData is also accepted by
`/api/account-deletion/prepare`; stale/tampered data is refused.

The public `/account-deletion` page works without reinstalling the app:
Google/Apple authorization-code verification reuses the existing registered
`/api/v3/native-auth/oauth/callback/{provider}` redirects and the existing
provider verifier's issuer/audience/nonce/PKCE checks. A separate `delete.`
state namespace and an HTTPOnly initiating-browser cookie prevent a sign-in
callback or a different browser from becoming deletion authorization. Apple
form_post requires the Secure/SameSite=None cookie. Telegram uses an opaque
bot deep link and explicit confirmation in the account's private chat, then
the learner returns to the web page for final submission. The legacy bot
request also persists in the same queue after explicit confirmation.

Only the verified provider subject HMAC or verified Telegram ID resolves
`users.id`. Email/display name/user-supplied account IDs never select an account.
No deletion endpoint creates accounts, links identities or issues login tokens.
Blocked users can use these narrowly scoped deletion routes; normal learning,
authentication, payment and access restrictions remain in force.

Capabilities are POST-only, stored hashed server-side and kept only in client
memory. Request bodies, cookies, OAuth codes and provider tokens must not be
logged. A confirmed request remains valid beyond the 10-minute verification
window. The public receipt can check completion while its page session remains
open; it is cleared by reload/close. The browser binding cookie lasts at most
60 days to cover the processing target plus completed-receipt retention. A
request reference alone is a support reference, never proof of ownership.

## Processing queue

`account_deletion_requests` (migration `0101_account_deletion_requests`) stores
verified, explicitly submitted requests. Railway's existing `init_db()` also
creates the new table through registered ORM metadata. Requests have a 30-day
processing target. One active queue row per account is enforced by a unique
`active_user_id`; duplicate confirmations keep the original due date and usable
receipts. Admin bot notification is best effort after commit: failed delivery
cannot discard a saved request. Check the durable queue at least daily and
prioritize entries whose `overdue` field is true.

On the trusted backend host, using its configured environment:

```sh
python scripts/process_account_deletion.py list
```

This lists request reference, internal user ID, verification method and target
date; it never prints credentials or performs deletion. Confirm the request is
submitted and review the retention obligations below. Account deletion affects
all clients and sessions. Do not delete another account based on a matching
email or a new Telegram contact. If support receives a reference without proof,
ask the user to use the authenticated in-app/public flow; do not ask for passwords
or identity documents.

After reviewing the exact queued account, process that confirmed request:

```sh
python scripts/process_account_deletion.py complete \
  --request-id REQUEST_UUID --user-id INTERNAL_USER_ID --confirm DELETE_ACCOUNT
```

This is destructive and runs only by explicit operator action. The receipt and
expected account ID must match. Admin accounts remain protected. The shared
repository purge and receipt completion commit together; a failure rolls back
the transaction. Repeating a completed receipt is idempotent. Account rows are
locked before receipt rows to serialize duplicate processing and respect legacy
admin deletion ordering. Submitted receipts for the same account become
completed together. Auth/identity rows are removed, so existing tokens cease to
authenticate. Telegram block caches are invalidated after successful commit.

The public receipt shows completion through `/api/account-deletion/status`.
For requests initiated only in Telegram, notify that verified private chat of
completion and any retention exception through the existing support procedure.
If a user asks from another channel, verify ownership before disclosing data.
Android acknowledgment confirms submission; it does not claim immediate purge.

## Existing retention rules

`UserRepository.delete_by_user_id` is the common purge; the existing admin/bot
`delete_by_telegram_id` entrypoint uses the same implementation. It deletes
account/profile/learning/mistake/voice/AI state, sign-in identities, devices,
sessions, push/presence, referrals and personalized discount campaigns. A null
Telegram ID never matches unrelated null rows or global campaigns/ledger data.
Friend referrals are removed by either canonical inviter/invited owner, including
provider-only accounts; their optional Telegram metadata is not the owner key.
Canonical owners also take precedence over stale/conflicting Telegram metadata
on devices, AI/Voice history, notices, analytics, diagnostics and personal
offers. Only unowned legacy rows use the real Telegram fallback. A personal
discount is deleted with its canonical target; it cannot become a global offer.
Portfolio rows associated with another account's payment are preserved even
if their old Telegram metadata matches the account being deleted.

Existing financial exceptions remain:

- Pending/rejected payments are deleted. Approved Pro and one-time HSK 3.0
  payment facts remain with an anonymous negative internal ID; canonical
  `payments.user_id`, screenshots, comments and Telegram message references
  are cleared. No User FK cascades approved accounting facts.
- Portfolio transactions retain accounting facts under that anonymous ID.
  Their freeform ledger notes may contain personal information; review these
  for a justified accounting/legal exception or redact them before closing
  the support case.
- Affiliate partner/referral financial records are anonymized and partner identity/access fields
  are redacted. Existing partner payout evidence, payout/account details,
  holder/bank information, proofs and notes are retained by the current purge.
  Review personal details and retain only those required for a documented
  accounting/legal purpose; explain that reason and applicable period to the
  requester. Do not describe every retained financial record as fully anonymous.

The repository does not define a fixed legal period for these financial
exceptions. The operator must determine/document the applicable reason and
period; this patch does not invent one. Review configured infrastructure/AI
service providers and backups for associated data, request provider deletion
where applicable, and ensure deleted account data is not restored from backups.
Do not report provider/backup deletion as complete without verification.

Account deletion does not itself cancel external-store subscription renewal.
The UI tells learners to cancel it in the store separately; no existing payment
or entitlement behavior is modified.

Expired/unsubmitted challenges are removed after 30 days. Completed anonymous
receipts and hashed status capabilities are kept for 30 days after completion.
Submitted/overdue requests never disappear through retention cleanup. The
existing hourly auth retention scheduler performs deletion housekeeping; it
also reconciles receipts whose account was removed by a legacy admin purge.

## Release verification

1. Deploy backend/schema first, then the tested Android Direct/Play builds.
2. Verify real Google web callback, Apple form_post when enabled, and Telegram
   private-chat confirmation on mobile browsers; use the existing provider
   configuration and redirect registrations.
3. Verify native requests after each supported sign-in method, public access
   without the app, final confirmation, retry and receipt status.
4. On a disposable test account, process the exact queued request, check shared
   data purge/session rejection, unrelated accounts and retained payment facts.
   Never use a production learner as a test deletion.
5. Assign an operator for daily queue/overdue review, retention explanations and
   verified-channel completion handling before submitting the Play listing.

Regression commands:

```sh
python -m pytest tests/test_account_deletion_api.py tests/test_account_deletion_cleanup.py \
  tests/test_account_deletion_request.py tests/test_native_oauth_api.py \
  tests/test_public_site.py tests/e2e/test_account_deletion.py
```

Policy reference: [Google Play account deletion requirements](https://support.google.com/googleplay/android-developer/answer/13327111).

## Verification performed on 2026-10-15

- The isolated deletion patch was integrated onto `main` baseline `49ad44fb`;
  unrelated universal signup work is excluded.
- Combined deletion/security/auth/course/access/payment/public-page/browser
  regression suite: 289 passed, 84 subtests; formal migration/schema parity and
  provider-only account purge included.
- The exact account-deletion CI unittest command passed all 44 tests; CI now
  includes ownership, retention and migration regressions.
- Android Direct: 514/514 unit tests passed; Play: 469/469 passed. All 18 deletion
  unit tests passed. Both app and instrumentation APKs built successfully.
  Three deletion Compose tests plus the existing profile compatibility test
  passed in each flavor on the Pixel_8 emulator (8/8).
- All nine Android static gates passed. The earlier settings status-bar
  screenshot failure was reproduced on unchanged `01dd7258`; that unrelated
  test was not modified. The full instrumentation suite is not claimed green.
- Python syntax/imports, JS syntax, diff whitespace and `graphify update .`
  verified. No production account was deleted and no deployment was performed.
