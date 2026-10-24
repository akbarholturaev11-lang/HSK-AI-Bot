# Admin PWA browser increment — branch-only, flag OFF

The owner supplied `/Users/kaijimima1234/Downloads/hsk-ai-admin-ux-demo-v10 2.html`
on 2026-10-24: 182,765 bytes, SHA-256
`1ff92bf82126ea65672ed703f9fff6553982db2f08f7c1ed2a06396cb6c89566`.
Its document title still says V9. This replaces the previously unavailable
184,575-byte visual reference; it is not a data or behavior contract. Only CSS
and fixed SVG icon paths are reused. No demo arrays, users, payments, charts,
mutation handlers or fabricated success statuses are shipped.

## Routes, data and isolation

- `/admin` redirects to `/admin/`; the latter serves an identical public shell
  to every visitor. Dedicated JS/CSS/catalog/brand images, manifest and worker
  are under `/admin/`. These router entries require the flag and canonical
  HTTPS origin. The pre-existing general `/static` mount can still serve public
  files: no secret or actor is ever embedded in the shell/assets.
- Native browser WebAuthn with base64url buffer conversion calls the existing
  server registration, discoverable login and operation-specific step-up.
  Google HTML callbacks use a fixed local 303 destination; the pending request
  ID and proof are separate HttpOnly cookies. The request ID is metadata, never
  authority. The status service still verifies the original browser proof.
- First onboarding uses existing Google/Bot completion and dual-cookie grant.
  The UI holds generated registration options only in memory, allowing native
  prompt cancellation to reuse the same unconsumed challenge. A refresh or
  expired challenge can require restarting Google/Bot recovery. Registration
  itself never issues a login cookie; a separate assertion is required.
- Statistics/users/feedback use existing bounded real-data projections.
  New POST `payments/list` uses the same strict cookie/Origin guard and
  PostgreSQL READ ONLY transaction; status + descending keyset page, max 100.
  Canonical owner has precedence over legacy Telegram ID. Orphans remain
  visible with null owner but cannot be reviewed by the financial adapter.
  No file reference, Telegram ID or notification URL is exported.
- Telegram/iPhone attribution gaps, absent Android feedback history, overlapping
  platform counts, rolling desktop windows and separate currencies remain
  explicit. No invented charts, unread count, triage or reply status. Course,
  marketing, settings, delete, grant-access and broadcast actions stay disabled.

## Exact payment confirmation

1. Prepare the server-owned snapshot, show canonical account/payment IDs,
   product, amount/currency, method/source/date and applicable local amount,
   discount and rejection reason.
2. Load GET `payments/{id}/receipt?receipt_sha256=...` using the HttpOnly
   session. Backend checks current admin, pending payment, canonical owner and
   stored-reference hash; downloads only a bounded verified JPEG/PNG/WebP
   (8 MiB, 20 million pixels, 10 seconds) through the existing bot; repeats
   authorization/reference checks after IO. It returns no-store image bytes,
   never a Telegram URL/token/file ID. The fingerprint binds the stored file
   reference, not the image's content bytes. Other file formats require a
   separate reviewed preview flow and cannot be confirmed in this UI.
3. Approve/reject buttons remain disabled until the receipt image loads.
   Reject requires a reason. Prepare again with the decision/reason and compare
   the exact server snapshot; any change requires viewing it again.
4. Show a separate confirmation, then request step-up for exactly
   `{action,target,payload}`. HTTP envelope `ok` is stripped before signing.
   Only the dedicated financial command with that same payload and step-up ID
   is sent. Closing cancels the native prompt; duplicate clicks are suppressed.
5. No automatic write retry. Lost response is explicitly uncertain; refresh
   the server list without resending. Only a successful committed response
   displays saved status. The existing atomic financial/audit/outbox contract
   and at-most-once delivery limitation remain unchanged.

The receipt-loaded UI check is human-review assistance, not a new server-side
receipt-view attestation. Security rests on server-owned snapshot validation,
current authorization, signed per-operation consent, one-use proof and the
existing atomic financial transaction.

## Public cache, text and accessibility

- SW scope `/admin/` excludes `/admin.html`. A fixed GET-only, same-origin,
  no-query allowlist caches shell + five public assets only. It never handles
  API/auth/receipt/attachment/legacy requests. Private responses are no-store;
  private data lives in memory and is cleared on offline, pagehide and 401.
  Reopening/returning verifies the current session. LocalStorage holds only
  the allowlisted locale. Tokens/proofs stay Secure HttpOnly cookies.
- Shell uses external scripts/styles and strict CSP without unsafe-inline.
  Dynamic server text is HTML escaped. Modal focus trap, inert background,
  Escape/close, mobile safe areas, reduced motion and explicit loading/error/
  empty/offline/auth-expired/unavailable states are present. New SW activation
  requires an explicit update button, followed by reload; no silent replacement
  during a financial confirmation.
- All permanent new UI copy is `ui.admin_pwa.*` in canonical UZ/RU/TJ Mini App
  sources, generated to a separate catalog using the existing builder. Learner
  bundle bytes remain unchanged. Existing brand PNGs are copied unchanged;
  Chromium reports no manifest installability errors with 256/1024 icons.

## Reproducible validation and boundary

`tests/test_admin_pwa_shell.py`, `test_admin_pwa_receipts.py`, extended read/
Google transport cases, and the existing financial/security/legacy suites.
`python -m tests.e2e.admin_pwa_browser --output /tmp/admin-pwa-browser` requires
Playwright 1.56.0 + Chromium. Its HTTPS browser requests run against actual ASGI
routers and isolated SQLite fixtures; real virtual-authenticator registration,
assertion and step-up signatures are verified by py_webauthn. It checks approval,
rejection, cancelled prompt (including delayed old-prompt cleanup across a new prompt), lost response without resend, receipt failures,
strict request shape, desktop/mobile, locales, XSS escaping, errors/empty state,
offline/revocation, logout, and CSP. A separate actual loopback server verifies
SW scope, installability, public-only cache, offline shell and explicit update.
All fixtures/screenshots are synthetic QA evidence, never production records.

The workflow runs the browser checks and keeps synthetic screenshots, in
addition to core tests, 61 legacy regressions and real PostgreSQL 16 concurrency/
scoped migrations. Physical Face ID/Touch ID/Windows Hello, installed real-device
PWA behavior and real Google/Telegram/provider/proxy E2E still require staging.
Keep `ADMIN_PWA_ENABLED=false`; no production/main promotion is authorized.
