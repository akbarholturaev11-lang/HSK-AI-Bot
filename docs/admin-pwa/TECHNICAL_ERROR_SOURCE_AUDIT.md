# Admin PWA — technical error source inventory (2026-10-24)

This is source-code evidence, **not** proof of production retention, alert delivery or complete historical capture. All work remains on `feat/admin-pwa-mcp-readonly-20261024`; `main`, deployment and feature flags are unchanged.

## Inspected real producers

- **Android report (connected):** `POST /api/v3/android/bug-report` through `app/services/admin_pwa_native_reports.py` creates a private durable `AdminPwaNativeReport` when Admin PWA is enabled, preserving the legacy notification path. `pwa_inbox.py` exposes bounded redacted text, source, canonical account and attachment presence; pending private screenshot bytes are not returned. Payment-receipt and Android report events already default to important. Do not claim historical Android reports that were Telegram-only are recoverable.
- **Mini App error context (NOT an approved admin alert feed):** `app/services/app_error_context_service.py::record_miniapp_error` writes `Message(role='assistant', content_type='app_error_context')` for a known Telegram-linked user. `_format_context` includes freeform message, URL, stack and extra context. This is **user/AI diagnostic history**, not sanitized durable admin event metadata. Never directly copy its `content` into Inbox, notification payloads, logs, MCP or JSON/CSV export. Source eligibility and dedup/retention for a new **separate** redacted technical event must be reviewed first.
- **Telegram admin notifications (not independently persisted):** `app/services/admin_notify_service.py` sends various admin Telegram messages. Successful `send_message`/`send_photo` is not a durable generalized system-alert row. Telegram delivery cannot be treated as full Inbox history.
- **Backend exceptions:** logger/exception paths are not a validated, rate-limited durable event source. Do not infer criticality from arbitrary exception strings and do not send exception bodies to Apple Web Push.

## Increment delivered here

Authorized `inbox/list` now accepts a **strict optional 3–80-character search**, only over text already visible from BotFeedback, ReleaseFeedbackResponse and retained Android reports, plus exact numeric **payment ID**. SQL uses parameters and literal %/_ escaping; text search is limited to the most recent 30 days and each source is capped at `limit+1` for keyset merging. Source/status/important/account filters and no-store WebAuthn guards remain. Search does not access file references, receipt contents, bank/payment notes, stack traces or message history. Normal Inbox browsing still includes older records.

## Attachment boundary (new separate increment)

The standalone Admin PWA native JPEG attachment route is authenticated and
strictly read-only, allowing a retained Android screenshot only with a current
allowlisted WebAuthn admin cookie. Its provider-free read path does not import
Mini App diagnostic history, old Telegram attachment references, payment receipts,
or AI/MCP tools. No UI viewing action is enabled yet; Bot/Release files need
independently reviewed Telegram-media access with ownership/source revalidation.

## Next safe technical-error work

1. Inventory the actual inbound Mini App error API/router and trust boundary (not merely the storage helper).
2. Define a separate privacy-minimized, source-validated, explicitly allowlisted `system`/technical event schema, bounded retention and per-source deduplication/rate-limits. No raw stack, URL query string, exception body, cookies, token or student text.
3. Add atomic intake and independently tested migration, then source/rank/triage/unread/outbox inclusion with strict platform/actor guards; update UZ/RU/TJ canonical UI and real iPhone/Mac notification QA.
4. Perform separate security and device staging acceptance before activating any push or technical alert ingestion.

## Owner-requested technical Inbox display — 2026-10-25

The first-party Inbox now reads bounded, last-30-day Mini App technical event
markers from existing stored `messages`, and the unread bell counts them.
Only canonical user ID, time, and a **fixed** label are displayed. The original
AI diagnostic text/stack/URL never leaves the source table or enters the
response. These diagnostic rows are currently **read-only** within Admin PWA;
no new triage mutation, provider push or arbitrary server exception collection
is implied. UZ/RU/TJ Inbox filter and label are canonical/generated.

To satisfy the owner's request for notifications for **each** error on an
opted-in Apple device, a separately audited default-OFF durable push producer
still needs source-specific event/triage schema and sender checks. Existing
Android error notifications remain independent. Avoid sending raw diagnostics
or misleadingly claiming that every server exception is captured.

## Safe onboarding explanations — 2026-10-27

The Admin PWA Inbox derives **fixed allowlisted outcome codes** from the
already-stored `app_error_context` messages, using server-side SQL CASE
predicates. This is read-only: no migration, ingestion, backfill mutation or
raw diagnostic-field serialization. Existing <=30-day onboarding records can
be categorized when they have the canonical producer signature; unknown or
malformed content still displays only a generic safe description.

The onboarding producer (`course_v3_onboarding`) posts an
`OnboardingSaveResponseError` event after the client rechecks whether a
failed/timed-out save actually persisted. `extra.recovered=true` confirms
the locally submitted level and preference fields matched the persisted
profile; an HTTP 200 from the status endpoint **alone does not** establish
recovery. In the Admin UI, allowlisted codes distinguish recovered response
errors (including HTTP 409 level-change rejection and timeout) from
unrecovered placement conflicts, timeouts and unconfirmed saves, with
UZ/RU/TJ explanations. A recovered 409 does not assert that the user's
HSK level was changed.

Private message content, stack traces, URL/query parameters and learner
text remain excluded from JSON responses, push alerts, raw detail panes
and exports. Classification is **not** a general error monitor and it
does not infer root causes for unknown Mini App error types.
