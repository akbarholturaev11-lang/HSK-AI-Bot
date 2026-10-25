# First-party management commands

Only the standalone Admin PWA uses these `/api/admin/v1` routes. Existing
Telegram guards and shared business services remain separate entry points.
External MCP has no management capability. Rollout defaults remain OFF.

Every command requires an active canonical allowlisted WebAuthn cookie, strict
same-origin HTTPS POST and a validated bounded body. Prepare returns the exact
operation for confirmation; the browser passes it unchanged through the
existing step-up ceremony. Save validates the canonical payload again, locks
the target, compares the prepared revision, rechecks current actor/expiry, and
commits the shared-service change, one-use proof consumption and immutable
0126 command audit together. No mutation is automatically retried after an
uncertain response.

| Command | Routes | Scope and existing owner |
| --- | --- | --- |
| `payments.review` | `/payments/prepare-review`, `/payments/review` | Existing payment review and entitlement services; receipt confirmation required |
| `users.grant_access` | `/users/prepare-access`, `/users/grant-access` | Shared manual subscription grant, 1–365 days, no fake Payment/revenue/AI budget |
| `course.access_policy` | `/course-access/read`, `/prepare`, `/save` | Global subscription/free-until policy, explicit timezone, maximum 365-day free deadline |
| `hsk30.settings` | `/hsk30/read`, `/prepare`, `/save` | Global rollout, canonical live levels, checkout switch, 1–10000 TJS price; no direct permanent grants |
| `subscription.prices` | `/subscription-prices/read`, `/prepare`, `/save` | Nine fixed payment-method/plan targets; shared Visa normalization and currencies |
| `settings.update` | `/settings/read`, `/prepare`, `/save` | Fixed bank details, allowed AI models, support contact and UZ/RU/TJ help videos |
| `marketing.update` | `/marketing/read`, `/prepare`, `/save` | Sales experiment, app promotion settings, existing creative activation/deletion |
| `users.block` / `users.delete` | `/users/prepare-management`, `/users/manage` | Canonical block/unblock or typed-ID-confirmed removal through shared UserRepository |
| `channels.update` | `/channels/read`, `/prepare`, `/save` | Required-channel mode, add/upsert, state and removal through shared channel service |

Subscription price read returns a fixed nine-row projection, never a paginated
scan. Prepare accepts only `method=visa|alipay|wechat`,
`plan=10_days|1_month|3_months`, integer `amount=1..1000000`. Its operation target
is `method-plan`, with a raw stored-state revision hash. An absent row has its
own revision; normalized legacy currency cannot conceal an intervening write.

PostgreSQL setting/price writers share deterministic transaction advisory locks
through `BotSettingRepository.lock_key`; this covers absent rows as well as
existing row locks. Read paths never acquire these locks or write defaults.
Multi-key callers lock touched keys in sorted order. PWA save transactions bound
lock/statement waits to five/eight seconds and validate proof/session expiry
after the target wait. Legacy Telegram HSK30 updates acquire the same sorted
keys without changing their partial-update semantics.

Regression evidence lives in `test_admin_pwa_course_access.py`,
`test_admin_pwa_subscription_prices.py`, `test_admin_pwa_hsk30_settings.py` and
the UUID-schema-only `test_admin_pwa_settings_postgres.py`. The PostgreSQL suite
covers two admins on an absent setting, legacy-vs-PWA first-row writes and
expiry during a real lock wait. Failure rolls back proof, audit and settings.

Settings read selects exactly 16 allowed keys in one query. It never reads
provider credentials or arbitrary keys and never writes defaults. Canonical
normalization is repeated before hashing/signing. Bank details, contact values
and URLs stay out of audit; evidence stores kind, target and before/after
hashes. AI process cache changes only after the database transaction commits.

Marketing read fetches two fixed settings plus at most 31 creative metadata
rows, without BLOBs, file restoration or media URLs. Each creative is a signed
individual target. Deletion uses the existing shared service, preserves files
still referenced by other creatives and limits postcommit cleanup to a
validated local basename. This adapter does not send messages or create
campaigns. Course/System/Marketing navigation itself performs no settings read;
editors fetch only after an explicit tap. Every editor has a before/after
confirmation and a single passkey save, with read-current recovery on lost
responses. These controls and bounded creative pages are localized in UZ/RU/TJ.

## Explicit code parity still outstanding

These legacy capabilities are not silently proxied by the standalone PWA:
direct messages,
mass messages, campaign creation, partner actions/payouts, manual ledger input,
notice-template management and media/QR/creative uploads. A legacy endpoint or
unused step-up action name is not an implemented standalone command. Each
needs its own strict payload, shared-service transaction and permission/audit
contract before its UI can claim success. Messaging additionally needs durable
claim/delivery evidence and bounded batches. Payment outbox uncertain-delivery
operator reconciliation and non-native orphan triage cleanup remain separate
operability work; immutable financial/command audits must stay intact.

Account management binds canonical ID, current identity/subscription/status hash,
the specific operation and (for deletion) repeated numeric ID confirmation.
Actor/self and current allowlisted-admin targets are protected. A target-row
wait is followed by fresh authority/expiry checks. Shared deletion preserves
anonymous approved payment/finance facts and removes personal account state.
Audit/proof and the command commit or roll back together. Telegram guard cache
is invalidated only after commit; the optional unblock notice is attempted
once outside the DB transaction, with no automatic retry or claim of device
delivery. UI uses the existing profile overflow menu and exact before/after
passkey confirmation. Test-generated account/creative deletions never touch
live records.

Required-channel reads use 30-row PK keysets and never backfill settings.
Commands accept bounded explicit Telegram usernames/numeric channel IDs and
HTTPS `t.me` invitations; private IDs require an invitation. No Telegram call
or arbitrary URL fetch occurs. Alias-aware PWA snapshots reject duplicate
case variants; shared writers lock canonical chat keys before first inserts
and existing rows before updates/deletion. Audits contain only hashes and
operation metadata, never invitation URLs or channel copy. Read-only section
navigation does not fetch the list. The editors use the same localized
confirmation/recovery flow as other configuration commands.
