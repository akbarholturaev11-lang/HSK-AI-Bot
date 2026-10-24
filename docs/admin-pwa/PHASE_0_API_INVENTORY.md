> **Initial source inventory, not current implementation status.** Current PWA routes, daily aggregate caching and live-read/security boundaries are in [READ_PROJECTIONS.md](READ_PROJECTIONS.md) and [MCP_NEXT_CHAT_HANDOFF.md](MCP_NEXT_CHAT_HANDOFF.md). This inventory does not change legacy Telegram APIs or authorize any listed endpoint as an MCP tool.

# Admin PWA — Phase 0 API inventory and security gates

Source inspected: `app/main.py` in `codex/admin-pwa`, baseline `e935e4315df42037d6aab4ab38b2c4e5d9bbb681`.
Scope: all **44** `/api/admin-miniapp/*` routes found in lines 3391–5158, plus the native Android bug-report producer. Treat classification as a migration **review gate**, not a claim that all endpoints are safe to re-expose.
All 44 routes currently use HTTP **POST**, including read-only operations.

## Current authorization contracts

- Standard admin request: `X-Telegram-Init-Data` → `extract_fresh_verified_webapp_user_id()` → `ADMIN_IDS` allowlist. See `app/main.py::_admin_miniapp_user_id` and `_admin_auth_error`.
- Five media-upload endpoints instead read an `initData` multipart form field and verify Telegram HMAC + allowlisted admin. They are **not open endpoints**. They call `extract_verified_webapp_user_id()` directly rather than the fresh age-limited helper and require separate explicit security review; **do not naively convert multipart upload to cookie authorization.** These five are:
  `desktop-promo/media`, `prices/qr-upload`, `broadcast/upload-media`, `notifications/media`, `course-ads/upload`.
- Browser PWA must have its *own* secure server-side authentication; do not synthesize Telegram initData, and do not weaken current Telegram guard. New browser API routes should use shared service methods with a verified actor and CSRF/origin check; no blanket bypass in legacy handlers.

## Read / summary and search (12 routes; some are not pure reads)

| Endpoint suffix (prefix `/api/admin-miniapp/`) | Existing purpose | PWA consideration |
|---|---|---|
| `overview` | admin metrics / course usage | project from shared stats service |
| `finance-stats` | estimated AI cost, billing, revenue | protect financial details; no mixing currencies |
| `sub-entry-stats` | subscription entry attribution | preserve source definition |
| `public-site-traffic` | acquisition referrer visits | visits ≠ unique visitors |
| `desktop-stats` | desktop activity / app versions | macOS and Windows dimensions not interchangeable |
| `android-stats` | Android activity / releases | separate device connection from unique account |
| `management` | settings and modules snapshot | currently calls `session.commit()` on retrieval; split read projection from side effects |
| `users/search` | account search | canonical ID, paging, masking, query caps |
| `users/detail` | account detail | sensitive PII and payment history |
| `hsk30/stats` | HSK 3.0 funnel | unique users and step-scoped payment attribution |
| `broadcast/count` | audience estimate | protect segmentation side channels |
| `audio/list` | audio inventory | allow only required content |

## Additional read / mixed-action routes (3)

- `notifications`: template listing / configuration, sensitive administrative read.
- `course-ads`: ad inventory; currently contains conditional `session.commit()` for media backup changes. **Not suitable as an unmodified read-only MCP endpoint.**
- `open-section`: triggers navigation/Telegram bot action; **not a pure read** and excluded from AI interface.

## Configuration / content mutations (16)

- `course-access/save` — subscription/free access.
- `course-sales-experiment/save` — sales experiment.
- `desktop-promo/save` — app promotion.
- `desktop-promo/media`, `desktop-promo/media/clear` — promotion media.
- `prices/save`, `prices/qr-upload` — payment pricing and QR.
- `hsk30/settings` — course rollout, levels, one-time unlock fee.
- `payment-details/save` — bank details.
- `ai-model/save` — AI model option.
- `channels/save` — mandatory Telegram channels.
- `help/save` — support links.
- `portfolio/transaction` — manual finance ledger mutation.
- `notifications/save`, `notifications/media`, `notifications/media/clear` — notice templates and media.

## Messaging, campaigns, partners, media / dangerous operations (13)

- `users/give-access` — manual Pro grant (high risk).
- `users/delete` — irreversible user data purge (critical risk).
- `users/block` — account block (high risk).
- `users/message` — direct outbound message (high risk).
- `payments/review` — approve/reject, payment/entitlement mutation (critical risk).
- `broadcast/upload-media` — broadcast media input.
- `broadcast/test` — outbound test message.
- `broadcast/send` — mass messaging (critical risk).
- `campaigns/create` — campaign and potentially scheduled communication.
- `partners/action` — partner approval/block/payout operations.
- `course-ads/upload` — creative media input.
- `course-ads/toggle` — ad state mutation.
- `course-ads/delete` — ad deletion.

Note: the sum of categories includes `open-section` as a mixed-action route; count endpoints using the complete list at the end. There are 44 unique original paths, not more. No route should be automatically mounted as an MCP tool.

## User feedback and bug-report sources

- `app/db/models/bot_feedback.py`: durable `bot_feedbacks`, free-text + coded responses, optional Telegram attachment IDs, reply status.
- `app/db/models/release_feedback.py`: campaign-backed `release_feedback_responses` with rating, comment, attachment file ID. Feedback attribution must retain campaign ID.
- `app/api/android_features.py`, `POST /api/v3/android/bug-report`: authenticated native Android bug-report **currently sends to Telegram admin chats**, with 60-second process-local throttle. Source inspected at lines 2161–2214. No durable DB insert in this handler. A complete PWA inbox requires durable intake and attachment retention before bot sending; preserve Telegram delivery and report response semantics.
- `app/services/admin_notify_service.py`: notification transport is not the same as a long-lived event table.

Proposed inbox event model:
`source_type, source_id, canonical_user_id?, original_transport_id?, platform?, app_version?, event_type, severity, language?, title, body_ref, attachment_ref?, created_at, received_at, read_at?, assigned_to?, status, resolved_at?, dedup_key`.
Unique key `(source_type, source_id)` where present; attachment access is admin-only, paths never returned unsigned to an AI client. Allow Android reports without Telegram identity.

## Immediate coding gate for Phase 1

Create tests **before** opening live admin login:
- Anonymous PWA and non-admin Bot user → forbidden.
- Real allowed admin Bot approval → one browser obtains one HttpOnly session.
- A different browser cannot claim approved challenge; consumed challenge fails on replay.
- Forged/stale initData, expired challenge, forged cookie, CSRF/origin attack → rejected.
- Existing `/admin.html` + all admin API requests with valid Telegram initData continue to behave identically.
- Admin action actor is logged and canonical account target resolution is unchanged.

## MCP and Cloud rule

The GitHub connector can read this source but is **not** a channel to query production PostgreSQL. First expose normalized, date-limited **read-only** JSON/CSV exports; only later connect an authorized MCP server with tools for statistics, conversion and feedback. No raw SQL executor, no account management, no payments, no broadcast and no unbounded PII export. Default redaction and per-tool audit log required.

## Implementation checkpoint

This inventory + the parent implementation plan are the **first Phase 0 deliverables**, not proof that PWA code or login has been built. Next implementation is the isolated Bot-approval sign-in transport and test contract, followed by UI shell and metrics.
