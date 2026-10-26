# Admin PWA receipt alerts must cover every intake

- Cause: shared Mini App/Android/Desktop checkout created payments directly
  through `PaymentRepository`, bypassing the optional alert hook used by Bot
  screenshot intake. A real stored receipt appeared in Inbox but produced no
  Web Push outbox event. An already-open Inbox also kept its original snapshot.
- Fix: call the existing savepoint-isolated receipt alert hook after Telegram
  delivery, screenshot assignment and preview claim, before commit. Refresh
  foreground unread counts and an open Inbox head every 15 seconds through the
  existing private APIs; keep details, receipts, focused rows and scrolled
  keyset pages stable. Cancel refresh when the private session is cleared.
- Risk: push-service acceptance does not establish lock-screen display. Missing
  OS consent, live VAPID configuration or active device enrollment still require
  operational evidence. Optional push failures must never roll back a payment,
  alter preview/access policy or expose receipt content in notification payloads.
- Prevention: exercise actual shared checkout for Android/Desktop native-only
  accounts and Telegram Mini App owners. Assert durable Inbox plus one outbox
  row per enrolled device, retry deduplication, disabled/failed push isolation
  and Telegram-failure rollback. Browser QA advances its clock to verify new
  receipts without reopening, stable details/pagination, stale-response
  rejection and no polling after offline/session clearing.
