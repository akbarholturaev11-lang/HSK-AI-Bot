# Universal native accounts

Android and desktop share one canonical `users.id` account model. Telegram,
Google and Apple can each be a first sign-in method. Provider availability
still depends on existing server credentials and the registered application
and redirect configuration in `OAUTH_SETUP.md`.

The owner confirmed on 2026-10-17 that this Play release has no purchases.
Play reads existing account entitlements; Billing implementation and Console
products/testers are a future phase. Direct APK and desktop retain the existing
manual Pro and HSK 3.0 checkout for all three sign-in methods. Friend referrals
and referral discounts also use canonical account ownership.

## Release hold

The owner requires all seven acceptance conditions below to be verified before
merging or pushing this feature to `main`, deploying it to production, or opening registration
to general use. Passing isolated tests does not waive missing product behavior
or real provider/staging checks. Keep the feature on `codex/universal-sign-in`
until the evidence is complete.

| Required condition | Current evidence and remaining gate |
| --- | --- |
| Existing Telegram Pro, XP, lessons, rating and payments stay unchanged | Backend/Android regressions and real-copy migration digests pass: all legacy billing, progress and XP/rating values are preserved. Real installed-client walkthroughs remain required. |
| Google/Apple users without Telegram can register, start a lesson, use AI Voice and buy Pro | Signup/learning/AI/voice and canonical manual Pro/HSK 3.0 checkout/approval have integration coverage. Direct Android and desktop need no Telegram; real provider, upstream Voice, referral and purchase walkthroughs remain required. Play consumes existing access without a purchase test in this release. |
| Parallel registration for one Google/Apple identity creates one `users.id` | Railway staging PostgreSQL 18 passes four concurrent Google attempts and four Apple attempts: one account per exact provider identity, with no email merge. Retain this check in CI. |
| Linking cannot grant access to another learner's Pro or progress | Ownership and identity/session revocation regressions cover isolation; verify the complete staged client flow as well. |
| A blocked account cannot evade its restriction through Google/Apple | Google/Apple identities already linked to a blocked canonical account cannot sign in, consume approved proof, refresh or attach another login. Both-provider regressions pass; real staged provider walkthroughs remain required. An unrelated new provider subject cannot be inferred to belong to the same person from email. |
| Android, desktop and Telegram Mini App show the same account data | A backend integration test checks explicitly linked Android/Windows/macOS logins plus MiniApp profile data share Pro, lesson progress, XP and rating. Installed-client comparison remains required. A Telegram-free account cannot authenticate a Telegram Mini App without a real Telegram identity. |
| Migrations pass on a staging copy matching the real schema, and backup restore succeeds | PASS: isolated Railway PostgreSQL 18 copy matching `0102_payment_review_preview` passed upgrades through `0107`, with exact pre/post-backup restores over 61 tables and 190,155 legacy rows, including 214 referrals. Evidence below; this does not clear other release gates. |

Railway has an isolated staging PostgreSQL service. This feature uses fresh,
separate migration/restore/test databases there. The universal application has
not been deployed. A separate `hsk-ai-p0-qa` service from the i18n branch now
exists in staging; its presence is not universal-account/provider acceptance
evidence. Its existing build was refreshed only to apply a staging credential
rotation. This task made no production deployment. The database copies contain
private learner data and must stay restricted. Do not run feature migrations
or test registrations against production. Do not describe the feature as
launch-ready until all required rows have reproducible evidence.

Read-only production inspection found PostgreSQL 18 at
`0102_payment_review_preview` after upstream `3fffa42e`. Production still
requires Telegram on users/devices/payments and has no canonical payment
owner column. The universal-account changes remain confined to this branch
and isolated staging.

### Completed database rehearsals

The source-schema copy passed the full `0102 → 0107` chain on 2026-10-17:
61 data tables, 190,155 legacy rows, 2,118 users, 100 payments and 214 referrals.
All 835 source column descriptors, 682 constraints and 301 indexes matched the
restored baseline. Exact migration and pre/post-backup restore comparisons
preserved billing, progress, XP/rating, referral reward/discount flags, account
keys and sequences. All 14,333 expected owner backfills were verified, including
97 payments and 428 referral endpoints. Receipt-preview flags/pointers were
unchanged. The trusted backup/catalog came from the verified `0102` copy made
earlier on the same date; no new production connection was needed for `0107`.
See [current sanitized evidence](UNIVERSAL_NATIVE_ACCOUNTS_STAGING_REFERRALS_2026-10-17.json).

The prior [`0102 → 0106` payment evidence](UNIVERSAL_NATIVE_ACCOUNTS_STAGING_PAYMENTS_2026-10-17.json)
is retained as the exact earlier revision's record.

The earlier
[`0102 → 0105` evidence](UNIVERSAL_NATIVE_ACCOUNTS_STAGING_PREVIEW_2026-10-17.json)
and [`0101 → 0104` evidence](UNIVERSAL_NATIVE_ACCOUNTS_STAGING_2026-10-16.json)
remain historical records of those exact revisions.

Backups are retained privately outside Git. No universal app or bot was deployed;
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
The separate HSK 3.0 one-time checkout now uses the same canonical payment
owner and existing configurable price (default 10 TJS). Its first-receipt
provisional access, permanent grant and rejection are independent of Pro:
approval does not change subscription dates, grant a paid AI budget or restore
the subscription receipt-preview ticket. Another account's pending or approved
payment cannot grant access. Blocked owners cannot purchase or receive a grant.

Android Play remains consumption-only without a purchase UI or external
payment steering. A future Billing phase would require store verification,
account binding, acknowledgement, restore and lifecycle reconciliation through
canonical entitlements; it is outside this release's acceptance scope.

### Canonical invitations

`referrals.referrer_user_id` and `invited_user_id` own friend attribution;
real Telegram IDs are optional transport metadata. One canonical invited owner
is unique. Trial links use `/apps?ref=CODE&mode=trial`; the existing discount
link omits `mode=trial`. Raw/ref-prefixed codes remain trial invitations and
`ra_`/`ri_` keep their Android/iOS discount requirements. Desktop is not silently
treated as an Android discount installation.

An optional code is captured before native sign-in and stored on that pending
attempt. It attaches only when verified Google, Apple or Telegram sign-in
creates a new user. Returning sign-in and explicit provider linking never
replace an inviter. Legacy Telegram `/start` eligibility remains unchanged.
The public page shows a copyable code and Android installed-app handoff; a
new installation or desktop accepts pasted code before account creation.

Existing two-question qualification, five-question bonus, five-active-friend
trial counter, three-day/$2 trial reward and three-qualified-friend discount
rules are preserved, including their current counting-window behavior.
Successful native Assistant messages provide equivalent two-question evidence;
procedural help, failed answers and request replay do not count. No daily
quota or `questions_used` policy changes. Server-owned installation ownership
still gates Android discount qualification. The authenticated overview shows
reward state; bot notifications are sent only for a real Telegram identity.
Offline desktop AI turns are not server-verifiable and do not count as
qualifying questions; the same canonical account's successful online Android
Assistant or Telegram AI questions count.

Telegram chat handoff and the separate bot-operated affiliate partner program
still need their actual Telegram transport. They do not block native manual
purchases or friend referrals, and no synthetic Telegram ID is used.

## Identity and access

- Google/Apple creation follows the existing signature, issuer, audience,
  nonce, freshness, state and PKCE verification. The server resolves the exact
  provider/subject HMAC. An unknown verified subject creates a new user and
  identity atomically; a known subject reuses its owner.
- Email is display metadata. To add another login to an existing account,
  authenticate that account and explicitly connect the provider from Profile.
  Matching email never merges accounts or moves progress/subscriptions.
- A real Telegram user ID stays unique and optional. Google/Apple users have
  `telegram_id = NULL` until explicit attachment; internal numeric account IDs are never substituted
  into Telegram columns or sent as Telegram chat IDs.
- The existing starter policy is reused (`status=trial`, five initial
  questions, no paid or Pro-trial dates). This is distinct from the explicitly
  started seven-day Pro trial. Paid periods, budgets, eligibility, daily caps
  and anti-abuse rules are unchanged.
- Native ownership uses authenticated canonical users, refreshed from the
  database. Legacy integer service callers still mean real Telegram IDs.
  Canonical backfilled rows and narrowly scoped legacy fallbacks remain
  compatible; a missing Telegram ID never authorizes other NULL-owner rows.
- Direct/desktop Pro, HSK 3.0 and friend referrals work for canonical
  provider-only accounts. Telegram chat handoff still needs a real Telegram
  identity. No synthetic Telegram ID, automatic email merge or store billing
  is introduced.

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
availability, optional signup invitations and the remaining Telegram transport actions.

### Attaching Telegram after Google/Apple signup

Android and the shared macOS/Windows desktop profile expose an explicit Telegram
connect action while no Telegram identity is attached. It starts a native
bearer-authenticated request using the existing identity endpoint with
`provider="telegram"`, `mode="telegram_approval"`, installation key and platform.
The existing `intent="link"`, `bind_user_id` and `bind_session_id` columns keep
the target canonical account and originating session fixed; no migration is needed.

The allowlisted `https://t.me/<bot>?start=tg_identity_<uuid>` URL opens a
dedicated private-chat confirmation before ordinary onboarding. The bot shows
the canonical account ID and requesting device; the Telegram user must explicitly
approve. Opening the link alone never attaches an identity or creates a learner.
An existing Telegram owner cannot be moved or merged, even when the email,
display name or person appears to match. An attached Telegram remains immutable.

Approval rechecks target ownership, current block state, expiry, reservation,
originating session and installation under database locks. Ordinary Telegram
signin/code callbacks cannot approve identity-link rows. Polling never mints
tokens. Explicit cancellation or dismissal cancels a pending proof; late client
responses are ignored and abandoned proof starts are cancelled. A cancellation
that loses to an already committed approval reports linked and does not detach
the approved identity. Revoked origin proofs cannot approve later.

Adding Telegram keeps canonical payments, HSK 3.0 grants, referrals, progress,
XP, AI budgets and Voice usage intact. Real-Telegram integer callers resolve
the same `users.id`, including historical native rows with NULL transport
metadata; another canonical owner's stale Telegram metadata grants no access.
No historical transport metadata rewrite or new user/session is needed.

The owner will test real provider/Voice/installed-client behavior after code
verification. Extra person-level detection across unrelated new provider
identities is outside scope by the owner's decision; existing linked-account
blocks remain enforced. The release hold stays active until real acceptance.

### Profile account-link cards

The existing profile promo slot now contains separate swipeable cards. Mini App
keeps Apps, HSK 3.0 and Pro, followed by each configured, unlinked Google/Apple
method. It already authenticates Telegram and does not advertise attaching it.
Android offers an unlinked Telegram method plus configured, unlinked Google/Apple
methods; Play still excludes the Pro purchase/trial promo.

Link cards appear only after successful server provider and identity reads.
Connected methods are omitted, including after a completed link refresh; failed
or incomplete discovery does not guess that a method is unlinked. Existing
settings retain identity management and disconnect safeguards. Cards invoke the
same authenticated link flows and server-owned HSK 3.0, trial and checkout actions.
Native swipes, dots and keyboard navigation change cards without activating them.
Pending link actions cannot duplicate a start; leaving and returning to the Mini
App profile resumes the same proof, and late replies cannot restart a completed
or replaced attempt. This presentation change adds no migration or access rule.

## Schema and rollout

Use an isolated staging application and the dedicated staging databases for
pre-release provider/client checks. The following production rollout runs only
after all release gates above are satisfied; it does not authorize a production
migration or release during the hold.

1. Apply `alembic upgrade head` through `0107_canonical_referral_owners` using
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
- `0107`: canonical referral inviter/invited owners, their backfills/FKs and
  invited-owner uniqueness; nullable real Telegram metadata and the optional
  signup code on pending sign-ins. Downgrade refuses unrepresentable native
  referrals or pending signup attribution.

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
  tests.test_payment_service_receipt_lock tests.test_native_hsk30_payments \
  tests.test_universal_referrals tests.test_universal_referral_migration
python -m unittest tests.test_native_account_concurrency \
  tests.test_universal_referral_concurrency
python -m unittest tests.test_telegram_identity_link tests.test_telegram_link_acceptance
python -m unittest tests.test_native_account_rehearsal
```

The Pro/HSK 3.0/referral business code is `7685d7d6`, integrated with `main` `160a51d6` at
`5b55cc3d`. The later `116ff346` changes only bounded remote PostgreSQL test
deadlines. Native source files are unchanged by the main localization merge.
Explicit provider-first Telegram attachment follows in backend `618253ff`,
Android `bb6ad356` and shared desktop `df09354a`.

Prior Pro/HSK 3.0/referral validation on 2026-10-17 (before Telegram attachment):

- Integrated backend selection at `5b55cc3d`: **1,189 tests and 814 subtests
  passed**, nine PostgreSQL cases skipped, seven existing configuration/asyncpg
  cleanup warnings. Real PostgreSQL checks cover those skipped cases separately.
- Real local PostgreSQL 15 checks: **12 tests and six subtests passed**, covering canonical payment/receipt races,
  HSK 3.0 first receipt/permanent grant/course-switch races, native identity
  races and simultaneous referral rewards. The course-switch test reproduced
  deadlock and first-state failure before the User-before-state fix, then passed
  for both existing and absent target track states.
- Railway staging PostgreSQL 18: **six tests and six subtests passed** for
  concurrent Google/Apple signup, HSK 3.0 receipt/grant/course-switch races and
  simultaneous referral rewards. All used isolated test databases.
- Android: **534 Direct + 489 Play unit tests**, nine native auth Compose
  checks, nine static gates and four debug/unsigned-release app builds passed.
  This includes the Play consumption-only contract and Direct checkout tests.
- Shared desktop: **31 JavaScript contracts, 25 Rust tests and 13 focused
  auth/referral browser checks** passed. Rendered invite QR codes were decoded
  back to their exact payload for macOS and Windows platform fixtures.
- Public download/provider/referral instructions plus Pro/HSK 3.0 checkout:
  **17 browser checks passed**. HSK 3.0 runs the actual existing profile-setting
  to receipt/pending flow for Google/macOS and Apple/Windows fixtures.
- Mini App affected smoke: **four checks passed** for map/lesson routing,
  subscription receipt flow, HSK 3.0 pending state and AI Voice rendering.
  Backend course/progress/quiz/entitlement regressions also pass.
- Seven broader Mini App expectations still fail identically on the untouched
  `8f1dca88` baseline: old onboarding-step expectations, three paywall-language
  expectations, recognition fallback/result and exam static-resource checks.
  Five older full desktop browser failures were already reproduced on the
  deletion baseline. An unrelated Android profile NEW-badge source assertion
  also predates this task. These suites are not claimed green.

Telegram-attachment validation on 2026-10-17 at `df09354a`:

The [sanitized attachment evidence](UNIVERSAL_NATIVE_ACCOUNTS_TELEGRAM_LINK_2026-10-17.json)
records this source revision and separates code checks from the owner's real tests.

- Integrated backend: **1,224 tests and 832 subtests passed**, no skips,
  seven existing configuration/asyncpg cleanup warnings. The dedicated local
  PostgreSQL 15 database exercised real same-Telegram competing targets,
  ordinary-signup/attachment and originating-session revocation races, plus
  the existing identity/payment/referral races.
- Google-first and Apple-first acceptance fixtures exercise actual API starts,
  private-bot proof services and status without new users or tokens. Exact
  paid/HSK 3.0/referral/progress/XP/budget snapshots stay unchanged; Android,
  Windows, macOS and Mini App resolve the same owner after attachment.
- Two new ownership tests failed against the prior transport-only query and
  pass with canonical resolution: pre-link native budget/Voice history remains
  visible to Telegram, and stale metadata cannot authorize a foreign owner.
- Android: **555 Direct + 510 Play unit tests**, **12 emulator Compose tests**,
  all **nine static checks**, and both release Kotlin compilations passed.
  This includes proof URL/request matching, cancellation, session replacement,
  late responses, existing Google/Apple linking and provider login.
- Desktop: **32 JavaScript and 28 Rust tests**, **17 new attachment browser
  cases** and **16 adjacent login/referral/Pro/HSK 3.0 browser cases** passed.
  Both macOS and Windows fixtures cover success, conflicts, cancellation,
  expiry and late responses. Native proof/token fields never reach the webview.
- Mini App: the same **four affected route/receipt/HSK 3.0/Voice smoke checks**
  passed again. Broader baseline UI gaps listed above remain outside this change.
- Schema stays at `0107_canonical_referral_owners`; no new migration, staging
  application deployment or production write was needed for attachment. The
  earlier full real-copy migration/backup evidence remains revision-specific.

Profile-card validation on 2026-10-17 at `6de94094` and `dfecb272`:

- **32 unique new Mini App browser cases passed** across runs of 29, one and
  two cases. Coverage includes configured/unlinked filtering, discovery failure,
  mobile UZ/RU/TJ layout, real scrolling and mouse drag, keyboard/reduced-motion
  behavior, link start validation, busy state, navigation resume and late replies.
- **141 backend/source/config tests and 36 subtests passed**, including Mini App
  browser-client provider discovery and existing identity/link isolation rules.
- Android: **563 Direct + 518 Play JVM tests (1,081 total)** and **36 emulator
  tests passed**. Cases cover dynamic provider cards, linked-method removal,
  swipe/navigation actions, cancellation and the Play no-purchase contract.
- **Four adjacent Mini App route/receipt/HSK 3.0/Voice smoke checks passed**.
- The old HSK 3.0 NEW-badge source expectation and old Profile Apps download
  smoke fixture also fail on the unchanged prior HEAD. The affected scope above
  is green; the complete older UI suites are not claimed green. Historical
  baseline gaps and real-client release gates remain unchanged.

### Owner's remaining real-client walkthrough

Run on an isolated staging backend with its own configured OAuth callbacks and
matching test clients. This feature has not been deployed as a staging app or
production app; local fixtures are not a substitute for that setup.

1. On fresh Google-first and Apple-first test accounts, record Pro/HSK 3.0,
   lesson progress and XP. From Profile connect an unused Telegram identity,
   verify the bot's target account/device, and explicitly approve. Reopen the
   account on Android, macOS, Windows and Telegram Mini App and compare values.
2. Repeat with bot rejection, closing the app flow before approval, an expired
   request and a Telegram identity already belonging to another test account.
   A foreign identity must stay with its existing owner; accounts never merge.
3. Use the real Voice provider and save a lesson result before/after attachment.
   Check usage/limits stay shared and a blocked linked account stays blocked.
4. On Direct APK and desktop submit a test receipt through the existing admin
   review process and verify only that canonical owner's Pro/HSK 3.0 changes.
   Play must expose existing access without purchases or external payment links.
5. Keep `main`, production migration and public registration held until these
   owner-run checks and the remaining acceptance rows are recorded.

PostgreSQL CI uses a local PostgreSQL 18 service. For an explicitly isolated
remote staging test database, `NATIVE_ACCOUNT_TEST_TIMEOUT_SECONDS=180` allows
network/proxy latency; the override is test-only and bounded at 300 seconds.
Ordinary CI deadlines and production timeouts are unchanged. Do not print full
database-driver locals or rendered connection variables when a test fails.

Native/browser fixtures do not prove real Google/Apple console configuration,
upstream AI Voice, bank payment review with real accounts, signed installed
Android/DMG/EXE parity, or Mini App account-link walkthroughs. Those are the
remaining acceptance checks. Play has no purchase test in the current scope.
The full desktop/older Mini App UI suites also need their baseline gaps reviewed
before claiming all project regressions green. `main` and production remain held.


## 2026-10-17 Android OAuth failure / browser-return audit

**Production evidence (read-only Railway inspection):** current live service is
on `main` commit `160a51d69f3324e3162375213ec61b5587b19533`,
**not** `codex/universal-sign-in`. The app service is healthy (one active
replica), but the separate production PostgreSQL service reports two warnings.
The staging environment has its PostgreSQL service and no universal-login
application deployment. Production variable names contain both Google client
IDs, desktop web secret, Google enable flag and OAuth redirect origin, but
their values were redacted; Apple variable names were absent. These facts
**do not** verify that credentials/callbacks work.

Five Android/OkHttp attempts on 2026-10-17 reached
`POST /api/v3/native-auth/oauth/start` and received HTTP 200; the subsequent
`POST /api/v3/native-auth/oauth/assert` requests all received HTTP 422.
The request/response bodies are not present in available HTTP logs, so the
specific server error code was not recoverable. A concrete contract mismatch
was identified: Kotlin `OAuthAssertRequest.provider = "google"` could be
omitted by `kotlinx.serialization` with default `encodeDefaults=false`,
while the FastAPI assertion requires `provider`. The DTO now has a required
provider field and an explicit serialization regression test. This explains
a plausible direct cause for the 422 responses but is not an E2E replay.

The branch's Android Google sign-in and profile attachment now use the
existing browser redirect/PKCE + confidential web-client exchange instead of
depending on Credential Manager UI/Google Play Services. Legacy native
assertion remains implemented internally; its Android-specific audience is
never accepted for the browser-client token exchange. Android browser Google
start fails closed if the separate web-client ID/secret is missing. The
callback hands control back using only a fixed
`pomp-hsk-ai://oauth-return` link when the successfully verified request is
from Android; token/session credentials never appear in that URL. The callback
page attempts to launch the app and provides a visible link in browsers that
block scripted app launches. The existing singleTask Android MainActivity
accepts that scheme. A live device/browser test is still mandatory (some
browser/OS combinations block automatic handoff and a killed app process may
lose in-memory polling state).

Desktop macOS/Windows provider sign-in already uses a system-browser redirect,
PKCE and the existing Rust-owned device/session polling, without embedding
credentials in the webview. Telegram device links and subsequent attachment
are separate confirmation flows with an account-binding proof. **However**,
the currently inspected desktop Profile UI renders a Telegram identity
attachment row only, not controls to attach Google or Apple to an already
signed-in desktop account. Those additional Profile controls remain a separate
product gap; backend identity endpoints alone do not provide a finished
desktop flow. Desktop OS protocol registration and automatic window
foregrounding were not added; the desktop app still completes sign-in by
polling. Google/Apple desktop/provider use cannot be marked verified solely
from code inspection.

**New tests were committed but not executed in this audit.** No PR-triggered
workflow run or combined commit status appeared for the inspected HEAD.
Do not count the historic tests recorded earlier in this document as test
results for these new patches. Next release gates: run Python OAuth API tests,
Android JVM/UI/real-device browser tests, desktop Rust/JS regressions; deploy
to an isolated staging application with real provider test credentials;
validate Android Google/Apple auto-return/manual fallback, cancellation,
existing account attachment, Telegram approval, session/entitlement isolation
and installed macOS/Windows flow. Do **not** merge into `main`, deploy
production, migrate its database or claim release-ready before sign-off.
