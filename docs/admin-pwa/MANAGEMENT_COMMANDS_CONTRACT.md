# First-party management commands

Only the standalone Admin PWA uses these `/api/admin/v1` routes. Existing
Telegram guards and shared business services remain separate entry points.
External MCP has no management capability. Rollout defaults remain OFF.

Every command requires an active canonical allowlisted WebAuthn cookie, strict
same-origin HTTPS POST and a validated bounded body. Prepare returns the exact
operation for the native passkey ceremony; the browser passes it unchanged
through that ceremony directly from the original editor. Save validates the canonical payload again, locks
the target, compares the prepared revision, rechecks current actor/expiry, and
commits the shared-service change, one-use proof consumption and immutable
0126 command audit together. No mutation is automatically retried after an
uncertain response.

Owner interaction rule (2026-10-25): every management editor uses one contextual
action such as Send, Save, Delete, Grant subscription or Accept payment. That
tap prepares the exact payload, invokes native WebAuthn and executes; there is
no intermediate before/after confirmation window and no generic passkey button.
The editor remains visible with frozen inputs throughout the ceremony. Native
cancellation restores the same form and its drafts. Loaded revisions/visible
state are compared before signing where available, and server-side proof,
revision, receipt and audit checks still run at the write boundary. Closing
an old ceremony cannot clear the controller/lock for a newer editor. Existing
scope-reducing stop/revoke buttons execute directly under their original
cookie/CSRF contracts; this UI change adds no new management permission.

| Command | Routes | Scope and existing owner |
| --- | --- | --- |
| `payments.review` | `/payments/prepare-review`, `/payments/review` | Existing payment review and entitlement services; receipt confirmation required |
| `users.grant_access` | `/users/prepare-access`, `/users/grant-access` | Shared manual subscription grant, 1–365 days, no fake Payment/revenue/AI budget |
| `course.access_policy` | `/course-access/read`, `/prepare`, `/save` | Global subscription/free-until policy, explicit timezone, maximum 365-day free deadline |
| `hsk30.settings` | `/hsk30/read`, `/prepare`, `/save` | Global rollout, canonical live levels, checkout switch, 1–10000 TJS price; no direct permanent grants |
| `subscription.prices` | `/subscription-prices/read`, `/prepare`, `/save` | Nine fixed payment-method/plan targets; shared Visa normalization and currencies |
| `subscription.qr_media` | `/payment-qr/read`, `/prepare`, `/media/save` | One existing subscription QR image for a fixed Alipay/WeChat plan; does not edit price |
| `settings.update` | `/settings/read`, `/prepare`, `/save` | Fixed bank details, allowed AI models, support contact and UZ/RU/TJ help videos |
| `marketing.update` | `/marketing/read`, `/prepare`, `/save`, `/media/save`; `/campaigns/read`, `/prepare`, `/save` | Signed creative creation/media/settings, paused ad drafts, bounded one-round ad/release delivery and discount offer configuration |
| `users.block` / `users.delete` | `/users/prepare-management`, `/users/manage` | Canonical block/unblock or typed-ID-confirmed removal through shared UserRepository |
| `broadcast.send` / `broadcast.control` | `/messages/read`, `/prepare`, `/save`, `/run`, `/prepare-control`, `/control`, `/stop` | Exact signed text/audience, durable pre-IO claims, owner-only bounded delivery and cancellation |
| `payments.delivery_reconcile` | `/payment-deliveries/read`, `/prepare`, `/save` | Audited human resolution for uncertain or stale attempts; never resend or change finance |
| `partners.payout` | `/partner-payouts/read`, `/prepare`, `/save` | Shared reserve/release/reject/deadline plus owned proof-bound completion and one durable recipient notice; no money transfer |
| `partners.update` | `/partners/read`, `/prepare`, `/save` | Partner application approve/reject with one durable notice, and partnership block/unblock via shared PartnerService |
| `notifications.update` | `/notifications/read`, `/prepare`, `/save` | Five fixed reminder templates, enabled state and canonical UZ/RU/TJ text/defaults |
| `portfolio.add` | `/portfolio/read`, `/prepare`, `/save` | Manual profit/expense through shared PortfolioService; no payment synchronization or entitlement mutation |
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
validated local basename. Settings/creative changes do not send messages.
Course/System/Marketing navigation itself performs no settings read;
editors fetch only after an explicit tap. Every editor has one contextual
action and a direct native passkey ceremony, with read-current recovery on lost
responses. These controls and bounded creative pages are localized in UZ/RU/TJ.

The separate signed campaign-draft command accepts text with optional owned photo/video, explicit
UZ/RU/TJ copy, selected audience languages, optional HSK track and a bounded
duration. It creates an existing `ad_campaigns` row as paused (`is_active=false`,
`next_send_at=NULL`) with one round; it performs no recipient scan, provider
call, automatic translation or delivery. The transaction-bound operation
signs a compact hash of all three copies, while the immutable audit stores only
that hash and the created campaign ID. Starting this draft now uses the separate
bounded campaign command below; this draft operation itself never delivers.

Desktop-promo media accepts only one decoded JPEG/PNG/WebP raster (2 MiB and
8-million-pixel bounds). The browser previews the file locally, then signs its
SHA-256 and byte count together with the current promo-settings revision. The
binary endpoint streams at most the bound, requires the same-origin PWA cookie,
and rechecks the exact one-use passkey operation before publishing a random
server-named asset. Settings and content-free audit commit together; a failed
or uncertain commit re-reads the setting before cleanup so a referenced file
is never removed. Replaced/cleared files are removed after commit. No image
BLOB, DB migration, Bot upload, AI call or campaign delivery is introduced.
The public media route allowlists only server-generated legacy/PWA filenames.

Existing course-ad image replacement is a separate signed `replace_image`
operation on one creative ID. It accepts a decoded JPEG/PNG/WebP image up to
1 MiB and 8 million pixels, signs the content hash and byte count with the
creative revision, and stores a random server-named file on the existing
course-ad media volume. The current media row and content-free audit commit in
the same transaction; no image BLOB, backup BLOB metadata or migration is
created. A shared old file is retained, and an unreferenced old file is removed
only after commit. This changes an existing creative's image only; it does not
create or deliver campaigns, upload video, or authorize QR/other media.

Existing course-ad video replacement is a distinct signed `replace_video`
operation on one creative ID. It accepts one MP4, MOV, WebM or M4V upload up to
25 MiB and binds the exact source SHA-256/byte count plus creative revision to
one passkey. The server requires that exact verified receipt before invoking
FFmpeg, uses one concurrent video-encode slot per worker, and converts to a
WebView-safe H.264/AAC MP4 with the existing 720-pixel scaling and 120-second
process timeout. Encoding and filesystem staging run outside the database
write transaction. The final short transaction consumes the proof, rechecks
the current creative revision, attaches the server-named MP4 path and records
content-free audit evidence atomically; an unreferenced staged file is cleaned
up after rollback, while uncertain commit state preserves referenced media.
Only the existing creative's media changes. No new DB BLOB or migration is
introduced; campaign delivery remains separate.

New course-ad creation is a distinct `course_ad_create` signed command. The
original V10 editor accepts either one selected language or explicit UZ/RU/TJ
copy, one photo/video, allowed type/placements, 5–120 second duration and an
optional HTTPS/Telegram link. It defaults to paused and performs no AI
translation or recipient delivery. Exact copy hash, media hash/size and all
settings participate in the proof. The shared creation service, one-use proof
and content-free audit commit atomically. Raster limits/storage match image
replacement; videos use the same single-slot encoder outside the DB
transaction. Same-session proof ownership is checked before encoding, including
when two sessions belong to the same admin. No media BLOB or migration.

Binary marketing saves encode UTF-8 JSON as base64url in
`X-Admin-PWA-Command` with `X-Admin-PWA-Command-Encoding: base64url`; the existing
8192-character header limit is unchanged. Strict decoding, duplicate-key
rejection and canonical payload validation precede proof consumption. Legacy
ASCII JSON commands remain accepted. This allows authored RU/TJ/Chinese copy
without invalid HTTP-header characters.

Subscription QR replacement is a separate `subscription.qr_media` operation for
the six fixed Alipay/WeChat plan targets in the existing `subscription` scope.
The exact current price/QR revision and one JPEG/PNG/WebP file hash/size (1 MiB,
8 million pixels, single frame) are bound to one passkey confirmation. It cannot
create a QR for Visa, HSK 3.0, discount or campaign scopes, and cannot change a
price, payment, subscription or access grant. The image is sent once to the
current admin's private Telegram chat because existing checkout consumes a Bot
`file_id`; the DB stores that ID and content-free revision audit only, never an
image BLOB or a new migration. No DB transaction is held during Bot IO. A short
write transaction rechecks proof, target and exact revision; a failed write
best-effort deletes the Bot message only after a fresh DB read proves its ID is
unreferenced. An uncertain DB read preserves the provider message. The provider
upload is not retried automatically.

## Signed campaign delivery and discount offers

`/campaigns/read` returns one explicit campaign or a 30-row PK-keyset metadata
page for ads, release feedback or discounts. List queries omit full copy and
provider IDs; section navigation performs no read. Detail/prepare/save use live
cookie/CSRF/authority checks, never daily aggregate caches. The original V10
editor retains the contextual Send/Create/Save → native passkey interaction.

- `ad_send` accepts one paused, explicit UZ/RU/TJ text/photo/video draft with one
  unsent round and a current time window. It signs the exact stored copy,
  revision, filters and at most 1000 eligible canonical recipients. Save
  reserves the shared round and legacy delivery evidence, consumes proof,
  writes content-free audit and enqueues the reviewed body atomically. It
  keeps `is_active=false` and `next_send_at=NULL`, so the legacy scheduler
  cannot take over or repeat an uncertain attempt. Round reservation denotes
  authorization of one attempt, not device delivery; the queue owns outcomes.
- `release_create` signs authored UZ/RU/TJ text, fixed localized prompt/rating
  markup, chosen existing feature, filters and exact bounded audience. It
  creates the shared campaign directly in `sending` with one claimed queue;
  it never leaves a `scheduled` row for the legacy sender. Existing try/rating
  callbacks and reward policy remain: 30-minute trial, 20% for 24 hours after
  feedback, with their original user-side eligibility checks. Sending alone
  does not grant access, discount or payment. Durable legacy delivery evidence
  records pending/attempting/sent/uncertain/skipped and provider message IDs
  where acknowledged. A stopped in-flight call may finish once; counters and
  receipts retain its actual outcome.
- `discount_create` uses the existing shared repository and checkout policy:
  explicit three-language plain title/reason, 1–90%, 1–720 hours, optional
  canonical personal account or existing segment, existing payment/plan rules,
  optional quota/repeat interval. New offers default off. `discount_state`
  binds the raw current revision to activation/deactivation. Notifications
  stay off and no recipient scan, Bot/AI call, Payment or entitlement is
  created. Activation of a legacy notification-enabled offer is refused, so
  this path cannot start an unbounded legacy sender. Native personal accounts
  retain `target_user_id` with no invented Telegram ID.

Signed ad drafts now accept one optional existing promotion action: subscription,
partner, course, reminder, help, contact, profile or a strict HTTPS/Telegram
username link. Browser callback JSON and provider IDs remain forbidden. Labels
use the existing shared localized defaults or explicit UZ/RU/TJ text together
(maximum 64 UTF-16 units each). Shared legacy single-label decoding is preserved.
The original V10 editor has one contextual creation/send action, retains fields
on native cancellation and shows the real button/destination with loaded copy.

Prepare renders all three buttons through the shared builder and binds their
full markup to the command content hash. Detail revisions include the rendered
buttons, so a changed loaded contact is rejected before native signing. Save
repeats rendering under the contact setting's shared lock, then atomically
stores that reviewed markup with the claimed queue. A later setting edit cannot
replace an already signed destination; dispatch performs no per-recipient
contact lookup. Immutable audit contains hashes, never destination URLs or
custom button copy. Unsafe legacy button formats remain read-only in this path.

Campaign jobs share the existing two drainer slots, ten-recipient batches,
committed pre-provider claim, one-hour private body retention, Stop and signed
pending-only resume. No DB connection spans provider IO. Each claim rechecks
session, current recipient, campaign revision/time and the selected filters.
An original transport snapshot prevents an identity change from leaving a
legacy reservation pointing at the wrong person. Unknown attempts never retry
automatically. Expiry/cancellation closes unclaimed work; content-free audit
outlives private job retention. No new schema, cron, media BLOB, translation
request, aggregate refresh or external MCP capability is introduced.

These commands intentionally accept the formats above. Arbitrary provider
references and long-lived unattended campaign scheduling is not accepted by these standalone commands. Media is limited to the owned staging contract below.
Existing course-ad photo/video, desktop-promo images, subscription QR and owned
payout proof each retain their separate signed asset contract. A legacy route
is not an implicit standalone permission.

Account management binds canonical ID, current identity/subscription/status hash,
the specific operation and (for deletion) repeated numeric ID confirmation.
Actor/self and current allowlisted-admin targets are protected. A target-row
wait is followed by fresh authority/expiry checks. Shared deletion preserves
anonymous approved payment/finance facts and removes personal account state.
Audit/proof and the command commit or roll back together. Telegram guard cache
is invalidated only after commit; the optional unblock notice is attempted
once outside the DB transaction, with no automatic retry or claim of device
delivery. UI uses the existing profile overflow menu and a single editor whose
contextual action signs the exact operation. Test-generated account/creative deletions never touch
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

Manual ledger reads project at most 31 manual-source rows by primary key, with
bounded note previews and original monetary precision. They never call the
legacy summary/history helpers that synchronize approved payments. New entries
accept integer minor units (1..100000000), USD/TJS/CNY and a bounded note. The
confirmation binds the exact shared internal-rate USD conversion; a changed
rate rejects before append. Append, proof consumption and hash-only note audit
commit atomically. No Payment, subscription, access or AI budget is created.
One proof cannot append twice across PostgreSQL workers.

Reminder-template list reads select only five fixed keys and enabled states;
opening an editor loads that template's three custom/effective/default texts
without file paths. Empty custom text restores the shared localized default.
Only known placeholders are accepted; field traversal, conversions and format
specifiers are rejected. Telegram UTF-16 text/caption limits apply to every
effective locale. Prepare returns the reviewed full copy separately from a
compact digest operation. The existing 4096-byte step-up limit is unchanged;
its digest binds all custom and effective fallback text plus enabled/revision.
Save reconstructs that commitment from the full validated copy, takes the same
key/row locks as legacy text/media writers and atomically commits proof, shared
service update and hash-only audit. Media/default changes invalidate review.
The browser preserves unsaved language drafts and inline validation errors;
text previews are escaped, with accessible per-language disclosure controls.

Partner application pages select only ID/status/bounded contact in 30-row
keysets; details are loaded explicitly. Approve/reject require pending state,
block requires active partnership and unblock requires blocked partnership.
The reviewed revision binds the full application, bonus setting and existing
signup-credit evidence. A shared setting-key lock and partner-row lock prevent
stale approval or a rate/bonus edit; authority/expiry is rechecked after waiting.
The shared service grants its existing locked signup bonus at most once. No
learner block, subscription, payment or AI budget is changed. Immutable audit
stores decision/status/bonus/hash only, without contact or promotion copy.
Approval and rejection prepare a fixed UZ/RU/TJ recipient notice from the
canonical user's language snapshot. The exact canonical recipient and notice
hash are bound to the same `partners.update` passkey operation. Partner status,
bonus, immutable command audit and one-recipient outbound job commit atomically;
the existing bounded drainer attempts delivery after commit. A missing
canonical Telegram account does not fabricate a recipient or block the status
decision. Provider uncertainty is not retried automatically. Block/unblock
remain status-only operations. This records a send attempt workflow, not device
delivery evidence.

Payout metadata pages use 30-row primary-key keysets. Details load bounded
account information but no Telegram QR/proof file IDs. Full raw payout state,
including amounts/rate/destination and processing owner, participates in CAS.
Deadline confirmation binds the actual UTC instant, never a save-time shifted
"N days". Shared conditional repository updates preserve closed-row and
reservation-owner guards. Post-lock current authority/expiry, immutable
content-free audit and proof consumption are atomic. Reserving does not move
money or mark paid; a provider-verified proof workflow is required separately.

Orphan triage cleanup is operator-only, not an MCP or browser management API.
`python -m scripts.admin_pwa_inbox_retention --limit 100` previews a bounded
primary-key page; `--purge-orphans` deletes only metadata whose original source
no longer exists. Continue via the returned source/ID cursor. No COUNT or
full-source query, background scheduler, raw content/BLOB, source deletion or
audit removal. Each page uses existing indexes and at most five bounded source
ID checks; active metadata locks are skipped and revisited on a later sweep.

Payment-delivery reconciliation is a human observation, not provider/device
delivery proof. Eligible rows are uncertain or attempts older than ten minutes.
The exact signed revision covers immutable review/decision and current outbox
state/effects hash; concurrent changes or prior reconciliation deny. A single
transaction consumes proof, records reason hash/resolution audit and sets the
nullable reconciliation timestamp. Financial rows, outbox transport outcome and
notification effects are unchanged. The dispatcher never retries these states.
Two indexed exact-status pages (maximum 62 rows) produce the combined 30-row
queue without loading message effects or payment snapshots. Migration 0128
provides partial unresolved-status and command action/target indexes; it refuses
to remove nonempty reconciliation metadata.

## Reviewed text delivery — migration 0129

`pwa_outbound.py` accepts direct canonical account, server-selected self-test or
filtered broadcast. All UZ/RU/TJ copy is validated locally (2–3500 UTF-16 units);
filters are strict fixed enums using the existing UserRepository predicates.
Prepare reads at most 1001 eligible metadata rows; over 1000 recipients is an
explicit error. No unbounded count/load, hidden translation request or native
account/blocked/unreachable/admin targeting. Direct targets use canonical ID;
self-test deliberately selects the current admin.

The exact compact passkey commitment includes copy hash, audience hash/count
and filters. Save locks and rechecks that snapshot and current authority after
waits; proof, immutable hash-only command evidence, one private body and bounded
recipient metadata commit together. Full copy is never duplicated in each
recipient/audit or exposed through MCP. Lost HTTP responses are reread, never
blindly resubmitted.

Migration `0129_admin_pwa_outbound` adds jobs, recipient claims and separate
content-free cancellation events, with expiry/pending/ownership/FK indexes.
Nonempty downgrade is refused. The job payload expires after one hour;
`python -m scripts.admin_pwa_outbound_retention` is a bounded read-only preview,
`--purge-expired --limit 100` explicitly removes one expired private batch.
Command and stop evidence survive that cleanup. Canonical account deletion
removes its recipient/direct private payload through FKs; a deleted broadcast
recipient is reported as removed. No new periodic scan or automatic scheduler.

An in-process drainer has two worker slots and up to 100 batches of ten. Each
recipient is durably marked attempting before a provider call; no connection
spans that call or pacing sleep. Current session/admin/feature/recipient state
is checked before every claim. Existing Bot text sender and reachability
bookkeeping are reused. Acknowledged attempts, uncertain failures and skips
are distinguished; neither means a device read the message. Crash/timeout/
uncertain attempts are never automatically retried. Expired/revoked session
pauses remaining work. A new session needs a fresh exact signed resume, which
selects pending recipients only. A stale worker is fenced by a run token.

Owner-only same-origin `/stop` uses the ordinary live WebAuthn cookie and CSRF
guard to cancel remaining work; it cannot add text, recipients or retry rights.
It records a distinct stop event, without pretending a new FIDO proof. One
already claimed attempt may finish. Signed control closes stale/uncertain
work or resumes pending recipients. UI refresh is explicit; no polling.

Marketing's compact Messages row and profile overflow open the existing V10
editor. One copy editor is visible at a time; filters are collapsed. The same
editor's Send button signs the exact escaped texts and computed audience before
delivery, without an intermediate confirmation window. The owner-approved
notification window, fresh-launch passkey and back gesture remain intact.

## Payout proof and single-window completion — owner update, 2026-10-25

The owner explicitly removed the second payout confirmation window. The
existing payout editor shows destination/amount, operation and the protected
proof image together; its only primary action prepares the exact command and
opens native WebAuthn directly. Other payout state operations use this same
single-window behavior. The original read revision is compared before any
ceremony; changed destinations/state force a reread. Inputs freeze while the
command runs. Closing or native cancellation never submits a payout. A lost
save response exposes only read-current, with no automatic retry. This owner
instruction supersedes the earlier two-window payout examples.

`POST /partner-payouts/{canonical_payout_id}/proof` is a strict same-origin
binary JPEG/PNG/WebP upload, maximum 2 MiB and the existing 20-million-pixel
validator. Only the currently reserved owner may stage it. A DB-shared bounded
20-attempt recent quota and two local IO slots precede the provider request.
The uploading admin's own private Bot chat receives the image; it is not sent
to the partner at this step. Uploading is committed before provider IO, then
authority/session/expiry is checked again. No image bytes, public URL or local
file are stored. No provider or database connection spans the other IO.

Migration 0130 stores only private owner/session/payout reference, source hash,
size, status, opaque provider reference and 15-minute expiry. The reference
never enters browser JSON/audit/MCP. Same-session private preview validates
actual raster bytes and rechecks authority/reference after provider IO. A
failed/foreign/used/expired proof cannot authorize completion. The image must
load in the first editor before its completion button becomes available.

`/partner-payouts/prepare-completion` returns a compact commitment to raw payout
revision, owned proof and exact recipient/three-language notice. `/complete`
locks the payout, proof, partner and canonical recipient, checks post-wait
authority/expiry, calls shared `mark_payout_paid`, consumes the asset/proof and
appends immutable content-free command evidence in one transaction. No money
transfer, Payment, subscription or ledger change. Competing commands cannot
complete the same reservation twice.

An eligible current canonical partner receives one durable outbound photo
notice through the existing claimed queue; no missing/unreachable recipient
is invented. The notice content and recipient snapshot are signed. Provider
uncertainty never rolls back the financial fact and never automatically retries
the notification. Session revocation stops unclaimed work; explicit signed
pending-only resume still applies. Text broadcasts retain no browser-supplied
provider reference field. Both entry points share the same two drainer slots.

`python -m scripts.admin_pwa_payout_proof_retention` previews one bounded
metadata page; `--purge-expired --limit 100` opts into removing only expired
staging references. It does not delete the retained paid payout proof, command
audit, notice or Telegram chat image. No scheduler or image BLOB scan is added.
Nonempty metadata prevents destructive 0130 downgrade.

## Owned campaign media (0131)

`POST /campaign-assets` accepts a bounded raw JPEG/PNG/WebP (2 MiB, 8M pixels)
or MP4/MOV/WebM/M4V video (25 MiB, 4K, three minutes). Current cookie,
allowlisted administrator, exact Origin/Fetch Metadata and enabled PWA are
required before processing. Two upload slots, one shared encoder and an
actor-wide database-coordinated 20/hour quota precede expensive provider work.
Forced local container/protocol handling, bounded allocation/threads and
probe/encode/provider deadlines prevent unbounded media work.

Media is staged in the uploading admin's private Bot chat. No binary, public
URL or provider ID is returned to the browser or stored in SQL BLOBs. 0131
stores ownership, source hash/size/type, private provider reference, expiry,
status and command link. `GET /campaign-assets/{id}` returns only ready owned
metadata for the same browser session. The browser previews its selected
local Blob, with `media-src 'self' blob:` and no provider download.

Ready media expires in 15 minutes. Ad draft and release-feedback commands
accept only paired owned `asset_id`/`asset_hash`; prepare/save recheck status,
ownership, hash and expiry. The media and signed proof are consumed atomically
with the campaign/audit/queue, and rollback preserves both. Media captions
including release prompt must fit 1024 escaped UTF-16 units per locale.
Release try/rating markup and ad button markup remain snapshotted.

Upload/encoding hold no SQL connection. An uncertain upload is failed and
never retried automatically. Original-editor cancellation retains the ready
selection; close, clear or session loss aborts requests and releases local URLs.
No second confirmation UI is introduced.

`python -m scripts.admin_pwa_campaign_asset_retention` is a bounded count-only
dry run; `--purge-expired --limit 100` removes eligible expired metadata only.
Rows younger than one hour remain for rolling quota enforcement. No provider
file deletion or campaign media revocation is performed. Nonempty downgrade
refuses deletion. This adds no scheduled retention deployment or external MCP tool.

## Session-bound campaign schedule (0132)

Ad/release send may contain `send_at`, an explicit UTC ISO string ending in Z.
It must be in the future, no more than 30 minutes ahead, before session expiry
and before the ad's own window ends. Save rechecks after lock waits. Absent
time retains immediate delivery. Indexed `not_before` fences manual API and
background drainers before claim. Existing one-hour private job retention and
live session authority remain unchanged; Stop and fresh signed pending-only
resume retain the original due time/expiry.

The existing minute worker does at most one bounded due query (three-second
statement deadline) when PWA is enabled, taking at most two ready jobs with
current live session/admin authority. Two tracked tasks use the existing two
shared drainer slots; transactional claims fence other workers. It never scans
statistics variants or holds the minute worker while provider IO runs. Flag-off
performs zero scheduler SQL. Nonempty scheduled state prevents 0132 downgrade.
