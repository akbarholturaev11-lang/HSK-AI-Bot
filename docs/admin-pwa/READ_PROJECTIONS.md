# Admin PWA real-data read projections

Branch-only, `ADMIN_PWA_ENABLED=false`. `app/admin_api/pwa_read.py` registers
three POST JSON read endpoints; they share the existing HTTPS/Origin/Fetch
Metadata/body/cookie guards and revalidate current canonical admin privileges.
No Telegram initData bypass, provider linking, session issuance or management
command is included. Responses are no-store and contain no session secrets.

On PostgreSQL each request uses a REPEATABLE READ, READ ONLY transaction and a
5-second SQL statement timeout. An accidental write fails in the database;
transaction settings do not leak into subsequent payment requests. SQLite
fixtures also verify all projection statements are SELECTs.

| Endpoint | Input | Actual source and meaning |
|---|---|---|
| `/api/admin/v1/statistics` | `period`: weekly/monthly/all_time; `platform`: overall/telegram/android/macos/windows/iphone_pwa | Shared admin/native analytics; scopes below |
| `/api/admin/v1/users/search` | optional `query` (≤80 chars), `limit` (1–100), `before_id` | Canonical User rows, descending ID keyset; shared entitlement resolver and payment-owner join |
| `/api/admin/v1/feedback/list` | required `source`: bot/release; optional canonical `user_id`, `limit`, `before_id` | Existing durable source rows; no new inbox/triage state |

All IDs and limits are strict integers, unknown fields are denied. Numeric user
search names only `users.id`; it never also guesses a Telegram ID. Text search
escapes SQL wildcards. Names/username/feedback are untrusted data and must be
escaped by the future UI. No raw attachments, email, Telegram IDs, or device
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
read/assigned/resolved status or reply action. Android bug reports are not a
durable table in this source snapshot; `unavailable_sources` explicitly records
that historical gap. Secure attachment viewing and durable Android intake
remain separate work.

These are browser-admin projections, **not** the future AI/MCP or sanitized
CSV export contract. No service-account/write tool or live DB access is added.
No UI, real device/provider E2E, production rollout or synthetic production data
is included. See CODEX_RESUME and the handoff for exact CI SHA/results.
