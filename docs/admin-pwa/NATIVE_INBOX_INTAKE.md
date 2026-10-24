# Native inbox intake — branch-only foundation

Enabled only with `ADMIN_PWA_ENABLED=true`; default remains false. No additional
flag was added. External MCP still exposes statistics only. Migration head:
`0122_admin_pwa_native_reports` (after 0121). No live migration/deploy performed.

## Intake and legacy compatibility

`POST /api/v3/android/bug-report` still authenticates the native bearer and
validates its existing schema/body/image bounds. Canonical owner comes only
from the authenticated account. With the flag off, it uses the previous
Telegram-only path and never queries the new report table.

With the PWA flag on, `reserve_native_report` locks the canonical User row and
commits private description/version/screen/optional opt-in JPEG bytes before any
Telegram call. It stores no bearer, fabricated Telegram identity or third-party
URL. A DB error fails closed before notification. Successful API response stays
`{ok:true}`; absent/failed Telegram delivery still returns the existing 503,
while the report remains durable with failed state. Errors log exception class
only, excluding request/SQL parameters and image content.

The DB lock coordinates workers: at most one new attempt per canonical account
per 60 seconds. Exact content is deduplicated within a UTC day; a five-minute
pending lease prevents immediate duplicate delivery after interrupted attempts.
A later retry reuses that row. Already-sent same-day content returns the existing
success without another notification, after the throttle interval. A delayed
failure cannot overwrite a recorded success. Telegram delivery is not exactly
once; a crash after external send can leave the stored outcome pending.

## Privacy, retention and rollback

`admin_pwa_native_reports` stores only the canonical owner, content, delivery
state and timestamps. Attachment is limited to 550 KiB by service and database
constraint. Raw screenshot bytes have no URL or browser/MCP endpoint in this
increment. Rendering requires a separate verified attachment projection.
Deleting the account cascades private reports, including screenshots.

Expiry is 30 days after intake. Operator command (module form from repo root):

```sh
python -m scripts.admin_pwa_native_report_retention
python -m scripts.admin_pwa_native_report_retention --purge-expired --limit 100
```

Default is count-only. Explicit purge deletes one expired batch (maximum 1000)
and prints counts only. Before enabling intake, staging/release operations must
configure daily cleanup, drain remaining batches and alert on backlog/failures.
No cleanup schedule or live deletion was activated here. Expiry alone does not
physically erase bytes; the operator job is a required release gate.

Downgrade refuses to remove a nonempty report table. Preserve an approved
private archive or complete authorized retention before schema rollback; never
silently erase reports for rollback. Application flag-off remains the immediate
safe rollback route.

## Remaining inbox work

Unified bot/release/native read projection and history boundary, severity/read/
assigned/resolved audit, bounded filters/search, secure decoded attachments,
existing admin/system source inventory and V10 UI are not implemented by this
intake foundation. The existing feedback API deliberately still advertises its
Android projection gap. Historical Telegram-only Android reports are not
recoverable from this table. Do not claim a complete universal inbox.
