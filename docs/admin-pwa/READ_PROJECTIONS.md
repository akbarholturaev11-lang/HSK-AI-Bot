# Admin PWA real-data read projections

Branch-only, `ADMIN_PWA_ENABLED=false`. `app/admin_api/pwa_read.py` registers
bounded POST JSON read endpoints; they share the existing HTTPS/Origin/Fetch
Metadata/body/cookie guards and revalidate current canonical admin privileges.
No Telegram initData bypass, provider linking, session issuance or management
command is included. Responses are no-store and contain no session secrets.

On PostgreSQL each database phase uses a REPEATABLE READ, READ ONLY transaction and a
5-second SQL statement timeout. An accidental write fails in the database;
transaction settings do not leak into subsequent payment requests. SQLite
fixtures also verify all projection statements are SELECTs.

| Endpoint | Input | Actual source and meaning |
|---|---|---|
| `/api/admin/v1/statistics` | `period`: weekly/monthly/all_time; `platform`: overall/telegram/android/macos/windows/iphone_pwa | Private daily aggregate snapshot; original generated_at and expiry; scopes below |
| `/api/admin/v1/users/search` | optional `query` (≤80 chars), `limit` (1–100), `before_id` | Canonical User rows, descending ID keyset; shared entitlement resolver and payment-owner join |
| `/api/admin/v1/users/detail` | required canonical `user_id` | Shared entitlement resolver; CourseProgress/track snapshots, referral owner aggregates, native device platform aggregates, Mini App presence, feedback counts and first ten payments |
| `/api/admin/v1/users/payments` | required canonical `user_id`, optional `limit`, `before_id` | All statuses, canonical-first payment ownership, descending ID keyset; no receipt references |
| `/api/admin/v1/feedback/list` | required `source`: bot/release; optional canonical `user_id`, `limit`, `before_id` | Existing durable source rows; no new inbox/triage state |
| `/api/admin/v1/inbox/list` | `source`: all/bot/release/android/payment; optional canonical `user_id`, priority, bounded search, `limit` 1–50, compound `before` cursor | Four bounded projections with persisted triage metadata; no attachment bytes or MCP |
| `/api/admin/v1/payments/list` | status, bounded limit, before_id | Live canonical-first payment queue; no receipt references |

All IDs and limits are strict integers, unknown fields are denied. Numeric user
search names only `users.id`; it never also guesses a Telegram ID. Text search
escapes SQL wildcards. Names/username/feedback are untrusted data and must be
escaped by the V10 UI. No raw attachments, email, Telegram IDs, or device
identifiers are returned. Feedback list excerpts cap each text at 2,000
characters and report truncation. Cursors are source-specific IDs, not offsets.

## Metric grains and limits

- Overall population is actual canonical User rows, not a sum of platform
  counts. New accounts use `created_at`; activity uses `last_active_at`, with an
  explicit rolling 30-day activity scope for all-time. Payment state counts and
  review/submission time selection reuse `AdminMiniAppService`. Approved
  amounts remain separate by exact stored currency; mixed-currency sums from
  legacy status aggregations are deliberately omitted.
- Android registry/active/funnel use `AndroidAnalyticsService.snapshot`.
  Registry means currently linked device records; activity is actual opens
  within the existing 1/7/30-day windows; funnel uses the chosen period. No
  widget online timestamp is relabeled as a human app open or an install.
- macOS/Windows reuse the existing desktop platform detail metrics. They are
  **rolling 30-day** counters regardless of selected period; the response says
  `period_filter_applied=false`. No all-time platform claim is made, and only
  rolling cohorts are loaded. A single account can occur on both platforms.
- iPhone PWA instrumentation is absent. Telegram-only course/event attribution
  has not yet been audited. Both return `available=false`, `metrics=null` and a
  machine reason; neither gets fabricated zeros or all-platform counts.

## Feedback identity and history

BotFeedback's stored canonical user ID takes precedence; an orphan never falls
back to its Telegram metadata. Release feedback has only a genuine positive
Telegram ID, joined to its current canonical User. Source ID, campaign ID,
original status/rating, timestamp and attachment presence retain their source
meaning. Unknown/deleted ownership is null. There is no invented severity,
read/assigned/resolved status or reply action. The earlier single-source `feedback/list` response retains its historical
`unavailable_sources` compatibility marker; it has not been extended to native
reports. The newer `inbox/list` reads only retained reports written after
Android intake was enabled. Historical Telegram-only Android reports cannot be
reconstructed. Persisted triage and V10 controls are now implemented. The private
retained Android JPEG and Bot/Release raster-image proxies reuse the V10 preview. Unsupported formats remain unavailable.

Only aggregate statistics are shared with the current statistics-only MCP.
Account, inbox, feedback and payment projections remain first-party browser
reads; they do not grant external MCP permission. First-party statistics JSON/CSV
exports are implemented below; sanitized feedback exports remain separate work.
See [current handoff](MCP_NEXT_CHAT_HANDOFF.md) for exact
SHA/test evidence; no real-device/provider E2E or rollout is established.

## First-party bounded feedback categories (2026-10-25)

Two separate WebAuthn-cookie-only POST routes implement a **limited recent-record
feedback category export**: `/api/admin/v1/feedback/categories` and
`/api/admin/v1/feedback/categories/export` (format `json|csv`). They are not
external MCP tools, do not expose raw feedback or extend OAuth scope, and do not
add background refreshing or any new tables. Existing canonical HTTPS/Origin,
same-origin Fetch Metadata, strict 2 KiB JSON input, no-store and read-only SQL
transaction with current admin allowlist/auth checks all apply.

Selector `period=weekly|monthly`, `source=all|bot|release|android`.
Each enabled source reads at most 501 indexed, recent records; only the first
500 contribute to category counts. `truncated=true` means records exist beyond
the bound, **not** that all source feedback was counted. Output includes the
per-source scanned count, original date column, date window and explicit
historical Android incompleteness. Bot uses completed `disliked_code` values
only from fixed keyboard codes; unknown becomes `unclassified`. Release groups
1-2, 3, and 4-5 star ratings without parsing private comments. Android counts
stored, still-retained bug reports as `reported_issue`, no guessing from raw
private descriptions. Android's 30-day expiry is written from created_at and
the query orders by indexed `expires_at` to avoid an unindexed created_at sort.
Current data sources have bounded row scans; 500 is per source, not a total.

Both export formats are capped at 128 KiB and contain code-controlled labels,
integer counts, typed source/date metadata and privacy-preserving definitions.
No user IDs, Telegram identifiers, free-form text, media bytes, attachment
references, raw conversations, profile rows or sensitive strings are selected.
CSV receives only fixed labels, so free-form formula payloads cannot be copied.
Android older Telegram-only reports remain unavailable. This is not full
historical sentiment analysis or a future-ChatGPT feedback permission. V10 UI
buttons and localization are separate pending tasks; the first-party JSON/CSV
endpoints exist server-side only. See `MCP_NEXT_CHAT_HANDOFF.md` for latest exact
CI evidence and rollout limits.

## Bounded first-party statistics files (2026-10-24)

`POST /api/admin/v1/statistics/export` accepts only `format=json|csv`, the existing
six platform values and `weekly|monthly|all_time` (default overall/weekly).
No arbitrary dates, URLs, SQL, user IDs or force-refresh. Same canonical HTTPS,
strict Origin/Fetch Metadata/JSON body (2 KiB maximum), HttpOnly session and
current allowlisted admin guards apply. Exports require a WebAuthn session and
recheck the actor/rollout after cache IO, with no auth connection held while
waiting. Small live auth SELECTs remain necessary; exports write no DB records.

The router reuses the same reader instance as dashboard/MCP. A warm export adds
no aggregate SQL; cold/expired variants use the existing daily refresh and
failure/cooldown rules. No export worker, server file, retention job, new cache,
R2, dependency, schema or configuration. Files are generated in bounded memory.

Schema v1 `hskai_statistics`: original UTC `generated_at`, `expires_at`, `since`,
period/platform, 86400-second interval, source/scope, overlap/availability/reason
and a list of numeric-or-null metric rows (`metric`, `value`, `unit`, `definition`,
`date_basis`). JSON also carries the shared overall metric dictionary; CSV embeds
each relevant shared definition in its row, alongside repeated source metadata.
Fixed allowlists select scalar metric paths and metadata; unknown nested fields,
user/profile IDs, names, contacts, raw feedback, prompts, provider references,
receipt/payment rows and credentials never enter files. Currency totals are
separate, with strict uppercase three-letter codes; no arbitrary spreadsheet
strings or formulas. Invalid/nonfinite values and malformed snapshots fail closed.

Maximum 96 metric rows, 32 currencies and 128 KiB per file. Unavailable Telegram/
iPhone produces no fake zeros: JSON has an empty metric list and reason; CSV has
one explicit unavailable status row with no metric/value. Desktop remains rolling
30 days regardless of period; Android registry/activity/funnel retain their
different grains. `all_time` is the existing bounded selector, not a bounded row
scan or a promise to avoid the first daily historical aggregate calculation.

Responses use attachment disposition, no-store/no-cache/nosniff and fixed safe
filenames. First-party exports do not create a new MCP tool or accept a bearer.
Broader sanitized feedback exports still require a separate privacy review.

## User profile increment (2026-10-24)

The V10 user drawer loads only after a user opens an account. It reuses the
cookie-admin read guard and SQL read-only snapshot. A nonexistent canonical ID
returns 404; a numeric Telegram ID never resolves as an alternative namespace.
Payment history is paginated (initial ten, further pages of ten). Native device
records are aggregated into the fixed Android/macOS/Windows grain: linked/total
and last server contact. Contact is not labeled foreground activity. Mini App
presence retains its own foreground timestamp. No installation keys, raw device
IDs, Telegram IDs, feedback contents or receipt file references enter the
profile response. Feedback opens the existing paginated inbox filtered to that
account, retaining the filter across source and next-page controls. No profile
read initializes progress, changes access, sends notifications or issues MCP
permissions. Android history and secure attachments remain separate increments.

## Overall activity increment (2026-10-24)

`pwa_metrics.py` adds SQL aggregates only; no historical event arrays are loaded.
Every new metric is bounded through `generated_at`, with optional 7/30-day lower
bound. The response includes the metric dictionary alongside the values:

- AI: stored usage-row count, total tokens and `cost_usd` snapshots, rounded to
  eight USD decimals. Includes orphaned historical costs; no repricing, model
  prompts, current FX conversion or invoice claim. Non-finite cost fails closed.
- Course: distinct current canonical accounts engaged/starting/completing in
  the period, canonical owner precedence and positive legacy Telegram fallback.
  Completion event aliases and Android overlap deduplicate at account grain;
  these are not completed lesson counts. Unmatched event count is explicit.
- Registration → Pro: denominator = accounts created in the chosen period by
  refresh time. Numerator = those same accounts with at least one approved
  recognized Pro-plan payment dated from registration through refresh time.
  Effective approval timestamp is reviewed_at, falling back to submitted_at.
  Repeat payments deduplicate; HSK 3.0 unlock, unknown plans, orphan payments and
  bonus/manual access do not convert. Empty cohort percentage is null. This is
  an observed cohort-to-date, not a mature trial/fixed-duration attribution rate.

The V10 dashboard labels the estimates, numerator/denominator and timing caveat
in all three locales. The existing statistics-only MCP can read these aggregate
fields and dictionary; no account/profile/payment/feedback tool was added.
Telegram attribution stays unavailable until independently audited.

## Owner-selected daily snapshots (2026-10-24)

The owner prioritizes avoiding repeated database work and selected daily
statistics. `pwa_statistics_cache.py` reuses a snapshot for 86,400 seconds from
its original `generated_at`. Each validated period/platform is computed on
first authorized demand after expiry; unused variants create no scheduled SQL.
It is a rolling 24-hour cache, not a fixed-time nightly cron or a claim of
current-day live counters. The response keeps source timestamps and adds
`snapshot.refresh_interval_seconds` and `snapshot.expires_at`. The existing V10
last-update timestamp remains the visible data age.

`app/main.py` injects one reader into browser statistics and the MCP transport.
The existing pinned redis-py 6.4.0 / `REDIS_URL` provides a private shared cache;
no dependency, feature flag, schema migration or R2 adapter was added. Each
request first revalidates its current cookie/OAuth actor. The auth transaction
ends before Redis IO or refresh waits, releasing the DB connection. A miss
alone opens a separate read-only aggregate snapshot. MCP audit and shared
security quotas still run for cached hits. They and authentication deliberately
remain small DB operations.

Memory caches contain at most the 18 allowlisted query variants. A global
45-second Redis refresh lease serializes heavy refreshes across healthy workers,
including different variants; a per-reader mutex coalesces local misses. Loads
are capped at eight seconds, cache/wait work at nine seconds. Publication and
lease release compare the unique owner token in Lua, so a delayed writer cannot
overwrite another owner's snapshot or release its lease. Redis keys include a
versioned hash of public origin and password-hidden DB identity, never admin
identifiers, cookies or credentials. Redis values use bounded JSON (128 KiB),
validate scope/version/expiry and contain the existing aggregate projection only.
Increment cache version when changing the projection/metric contract.

Redis failure retains a bounded per-worker daily memory fallback and a
30-second connection circuit breaker with content-free logging. That degraded
mode can calculate once per active worker/variant; it does not promise cluster
coordination during Redis outage or restart. Failed/cancelled SQL refreshes
back off locally for 30 seconds and leave the shared lease to expire, preventing
per-request retries. Expired snapshots are not served. No manual browser
refresh parameter bypasses the daily period.

Browser/HTTP/SW still use no-store for private responses; Redis is server-side
and must be private and isolated before rollout. No browser offline/private
cache was enabled. User profiles, current billing/payment lists, receipt/review,
access decisions and all commands remain uncached. Current payment/access
facts can change immediately while the dashboard waits until its next snapshot.
R2 snapshots/archives remain optional future work; nothing is uploaded to R2.

Redis cache-aside/lease reference:
[official Redis cache-aside guide](https://redis.io/docs/latest/develop/use-cases/cache-aside/redis-py/).

## Inbox milestones (historical progression)

Current inbox includes four sources (Bot, Release, retained Android and pending
screenshot payments), V10 triage, important filter, capped unread count and
bounded text search. The private Android JPEG proxy is first-party only. See
[current handoff](MCP_NEXT_CHAT_HANDOFF.md), [native intake](NATIVE_INBOX_INTAKE.md),
[technical source audit](TECHNICAL_ERROR_SOURCE_AUDIT.md) and
[Apple Push acceptance](APPLE_PUSH_ACCEPTANCE.md). Earlier next-step statements
below describe their original checkpoints and are superseded. None of these
features extends the daily statistics cache to live inbox or security state.

### Unified inbox read-only increment (2026-10-24)

`app/admin_api/pwa_inbox.py` reads bot feedback, release responses and retained
private Android reports through three bounded SELECT projections. It reads at
most `limit + 1` rows per selected source, merges by descending UTC timestamp,
source rank and stable source ID, and returns a strict timezone-aware compound
cursor. The optional account filter uses canonical User IDs; release ownership
requires positive stored Telegram ID mapped to a real canonical User. Orphaned
bot/release feedback shows null canonical owner. Expired native reports are never
returned, even if scheduled physical purge has not yet executed.

The V10 notification bell now uses `inbox/list`, default `all`, and has Bot,
Release and Android source filters with next-page support. It reuses existing
UZ/RU/TJ catalog labels; no generated localization files were hand-edited.
Output contains capped 2,000-character excerpts, attachment presence ONLY,
source-owned feedback status or native Telegram-delivery status (distinct from
admin triage state), no file IDs, native screenshot bytes, raw Telegram IDs or MCP
extension. It explicitly returns `historical_android_reports_complete=false`,
`triage_available=true` and `attachment_access=not_exposed`. The later 0123
schema adds separately persisted optional `triage_status`, `triage_priority`,
`triage_assigned_to`, timestamps and `triage_revision` (0 before first mutation). These are API metadata, not a claim that the
UI already displays a completed triage workflow or all historic reports.

Next: V10 triage-action controls/UX and canonical UZ/RU/TJ labels, indexed
search/filters, administrative/system alert sources and secure attachment proxy. Admin/system alert
source inventory precedes claiming universal notifications complete.

### Inbox triage state — 0123 foundation (2026-10-24)

`app/admin_api/pwa_inbox_triage.py` is a protected first-party-only endpoint.
An active WebAuthn Admin PWA session is required for changes; a Google/Telegram
onboarding cookie, missing/blocked admin, forged origin and expired Android source
fail closed. The input has a strict source, integer source ID, one allowlisted
operation, and an expected integer revision. Source-row locking and compare-and-
set revision guard prevent stale writes; triage state and content-free append-only
audit insert commit together. Assigning to another arbitrary user is not offered:
`assign_self` binds the current canonical admin. Source feedback status and
native Telegram-delivery status remain unmodified.

Triage statuses: new, read, assigned, resolved; independent priorities: normal
or important. Operations mark_read, assign_self, resolve, reopen, mark_important,
clear_important. The read endpoint returns status/priority/revision and relevant
timestamps with no private bytes. V10 now offers the six first-party triage controls with canonical UZ/RU/TJ
labels and mobile touch targets. The separate `inbox/unread-count` POST reads at most 100 eligible IDs across sources, returns a 99-plus cap marker rather than an invented exact large total, and excludes read/assigned/resolved records and expired Android reports. Missing triage state counts as new. The `priority=important` filter applies in SQL before pagination, and V10 shows both on iPhone/Mac. It still does **not** deliver actual device Web Push, system/admin alert ingestion, full-text search or attachment viewing.

Migration: `0123_admin_pwa_inbox_triage` after 0122. Two new tables; rollback
refuses nonempty audit/state. Disposable PostgreSQL + browser/test CI green at
`838026d9`; no live migration/flag toggles/deployment. Before release, design
bounded orphan/retention cleanup for expired or erased original source records,
and audit access monitoring without silently deleting audit evidence.

## Android-only attachment proxy — 2026-10-24

A separate GET `/api/admin/v1/inbox/android/{report_id}/attachment` now serves
only still-retained, structurally verified JPEG bytes from the durable Android
private report table to a **current WebAuthn-authenticated allowlisted** Admin
PWA browser session. It checks canonical same-origin Fetch Metadata and denies
cross-site requests, rejects missing/expired/malformed records, caps original
bytes at 550 KiB, and returns no-store/nosniff. Its path is not an Inbox list
field and never appears in external MCP. The existing `attachment_access:
not_exposed` on read-list projections remains accurate: no bytes, Telegram
references or download URLs are returned by the lists. V10 now constructs only
the fixed first-party Android route after an explicit tap, displays the bounded
JPEG through an in-memory object URL, and aborts/revokes it on close, navigation,
offline, pagehide or session invalidation. Reopening rechecks current auth and
retention; late responses cannot repopulate another drawer. The later Bot/Release
image extension below retains this native boundary. CI verified this private
route and flag-OFF 404 behavior at `d93b75fe` (run 40101181445).

## Bot/Release image extension and low-load boundary (2026-10-24)

GET `/api/admin/v1/inbox/{source}/{item_id}/attachment` accepts only Bot/Release
source keys after the rollout guard; the earlier Android-specific route remains
separate. Current WebAuthn cookie/admin is required; bearer/Telegram initData
cannot replace it. Query parameters, arbitrary URLs and client file IDs are
rejected. Canonical Bot owner or positive Release Telegram-to-canonical mapping
must exist. Only stored photo/document candidates are considered. Source/user
rebinding, replacement, deletion or revocation during IO prevents old delivery.

`inbox/list.image_preview_available` is a bounded boolean for eligible Bot/Release
rows from the existing source SELECT, not a file reference, format guarantee or
MCP capability. Real bytes still undergo JPEG/PNG/WebP / 8 MiB / 20 MP checks.
Missing/unknown/unsupported historical formats remain unavailable. Existing
Bot/Release source deletion rules apply; no new time retention is invented.

Only source metadata is selected for download; no feedback bodies or image BLOB
are copied into the read-list response. Database transactions end before the
shared Bot client's bounded IO. At most two loads and 30 attempts/minute per
worker use process memory without quota DB writes; no preload, polling, automatic
retry, media cache, backfill, cron or R2 was added. These are worker-local bounds,
not a cluster-wide rate guarantee. Browser object URLs are revoked on close or
private-state invalidation. See [browser contract](BROWSER_UI_CONTRACT.md).
Statistics still reuse their separate 24-hour cache; current auth/security facts
and all first-party inbox/financial operations remain live.

### Feedback analytics per-worker read admission — 2026-10-25

To bound repeated **first-party** Bot/Release/Android category queries, the
feedback read/JSON/CSV endpoints share a fixed small process-local admission
state: at most 30 authenticated queries per 60 seconds and 2 active aggregate
queries per worker. Excess requests fail fast with private no-store HTTP 429
and a bounded Retry-After; neither the untrusted request body nor cookies,
source text, account IDs or IP addresses are stored in the limiter. The gate
runs only after live allowlisted WebAuthn session validation, so anonymous
requests cannot consume the feedback workload budget. This limits the heavy
aggregate SELECT path rather than generic admin authentication. No background
refresh, new Redis DB dependency or cache of private feedback is added.

These bounds are **per worker**, not shared across a multi-worker deployment:
production deployment-wide admission and real DB indexing/load tests remain
release acceptance items. Other first-party Inbox search and live billing
queries retain their separate behavior and contracts. The external MCP tool
remains statistics-only. Regression tests cover authenticated and forged
requests, a shared export/read quota, overflow 429, reset and concurrent
admission; they do not claim multi-worker enforcement.

## Rolling 24-hour Feedback/Statistics R2 mirror — 2026-10-25

Owner clarified: **never recompute aggregate feedback on every Admin PWA open**.
The feedback categories and JSON/CSV export endpoints now authenticate current
WebAuthn admin sessions and reuse **the SAME rolling 24-hour aggregate snapshot**
for each requested (source, weekly/monthly) variant. Warm reads hit process
memory first, then existing Redis (single cross-worker refresh lease). Cold
reads may hydrate a checked snapshot from a **private Cloudflare R2 bucket**;
only an expired/absent snapshot runs bounded read-only SQL on demand. The existing
Statistics reader also mirrors validated daily snapshots to the same R2 bucket
behind a separate kind/version key. Nothing uses an anonymous R2 URL or lets
browser/MCP read R2 directly. R2 values contain **only privacy-minimized
aggregate projections**, not user IDs, text, media, payment or access records.

The adapter `app/admin_api/pwa_r2_aggregate_store.py` uses private server-side
S3-compatible R2 credentials. It is **disabled by default** until all private
`ADMIN_PWA_R2_* ` variables are supplied in the runtime secrets manager and
staging has verified bucket read/write policy. Never commit or expose credentials,
bucket URLs or signed links to browser/MCP. Without R2 credentials, **Redis +
process-local daily fallback still prevents per-open aggregate SQL**; do NOT
claim R2 is live or configured. Redis outage degrades to per-worker daily cache;
multiple workers can separately refresh during a shared outage. Cloudflare
credentials/production bucket access and cross-worker load tests are not yet verified.

The browser must still call an authenticated first-party API when opening
Statistics (including cache hits); the **heavy source database aggregate queries**,
not authentication/audit/current payment reads, are the once-per-24-hour part.
Changing query period/source yields a separate on-demand daily snapshot. Snapshot
revalidation checks exact query, timestamps, schema, safe category counts and
payload size. Export does NOT trigger independent uncached SQL. No background
polling, early forced refresh, account caches or production rollout are introduced.
