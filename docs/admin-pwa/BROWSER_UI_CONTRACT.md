# Admin PWA browser increment — branch-only, flag OFF

## Owner single-window action update — 2026-10-25

All management operations have one editor and one contextual action button
(Send, Save, Delete, Accept payment, etc.), followed directly by native WebAuthn
and execution. There is no second confirmation screen or generic passkey CTA.
Payout operations follow the same rule.
Keep amounts/destination and protected uploaded proof visible in that editor;
do not add a second before/after confirmation window. Preparing the exact
server command and opening native WebAuthn are sequential backend operations
behind the same click. A changed original payout revision requires reread.
Disable completion until its owned proof image loads; freeze input during the
ceremony, preserve the draft on native cancellation and never auto-retry a
submitted uncertain result. Other existing command/auth security guards remain.


The owner supplied `/Users/kaijimima1234/Downloads/hsk-ai-admin-ux-demo-v10 2.html`
on 2026-10-24: 182,765 bytes, SHA-256
`1ff92bf82126ea65672ed703f9fff6553982db2f08f7c1ed2a06396cb6c89566`.
Its document title still says V9. This replaces the previously unavailable
184,575-byte visual reference; it is not a data or behavior contract. Only CSS
and fixed SVG icon paths are reused. No demo arrays, users, payments, charts,
mutation handlers or fabricated success statuses are shipped.

## Current owner-approved baseline — 2026-10-25

Merged baseline: `feat/admin-pwa-minimal-inbox-passkey-20261025`, PR #204. Follow-up: `feat/admin-pwa-seamless-passkey-20261025`. Preserve
its title-only unread-first Inbox, automatic priority/red state, explicit
read-on-open detail, separate receipt review and return to originating inbox.
Keep the single close control and one-step iPhone left-zone back gesture with
native Safari/scroll/text-selection exclusions. Existing audited triage/Push
transport remains compatible; manual priority/assignment controls are absent.
On launch/resume, first revalidate the Secure HttpOnly cookie with /me.
An unexpired, non-revoked session with current admin rights opens directly;
after a 401, try one automatic passkey assertion per foreground visit.
iOS/macOS/WebKit may reject gesture-free modal assertions, so retain the
manual passkey action without recurring prompts. Logout explicitly revokes
the server session; private browser memory clears on hide/pagehide/offline.
High-risk actions still require their own fresh transaction-bound proof from
the original editor, even when the login session is reused.

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
  marketing, settings, account, access and broadcast command coverage is defined
  in `MANAGEMENT_COMMANDS_CONTRACT.md`; external MCP remains statistics-only.

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
4. From that same receipt editor, the contextual payment action requests step-up for exactly
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


## Mobile controls during sign-in completion

The mobile More button stays disabled while the sign-in action finishes boot's
last existing server read. The authenticated shell can render before that read
returns; a visible button must not silently lose a tap to the busy guard.
Browser QA holds the unread-count response and verifies disabled → enabled →
More/logout, without adding requests, weakening auth or increasing timeouts.

## MCP connection controls and reauthorization (2026-10-24)

- Verified `/me` exposes `mcp_available` only when the WebAuthn actor, all three gates and exact registered configuration are ready. Desktop sidebar and mobile More open the existing V10 drawer; disabled rollout exposes no connection action.
- History is a bounded server projection of the current admin's last 30 consents. Actual expiry/status, empty/error/offline/auth and uncertain-response states are explicit. The contextual revoke button performs the existing scope-reducing command directly under its cookie/CSRF contract. Successful revoke reloads history; lost response requires reread rather than claiming success.
- OAuth sign-in opens `/admin/` in another tab; retry reloads the original GET. An expired/replayed consent POST instructs a fresh external-client authorization instead of resubmitting old proof. No token/state is stored in browser storage or embedded in the error screen.
- New patterns were absent from the V10 demo, so the actual repository `hsk-ai-ui` and `webapp-testing` skills were read/applied. Existing slate cards/drawers, focus handling, mobile safe areas and one main action were reused; canonical UZ/RU/TJ source and generator own copy.
- Browser QA extended `tests/e2e/admin_pwa_browser.py` with actual session/DB history, cancellation, revoke and bearer rejection; 1440/390 UZ/RU/TJ screenshots. `admin_pwa_mcp_consent_browser.py` covers native form Origin/Referer, sign-in/retry and expired states. The latter bridge supplies synthetic Fetch Metadata omitted by interception, after checking actual browser Origin; it is not HTTPS proxy/physical-device evidence.

## Daily aggregate data age (owner direction, 2026-10-24)

Statistics reuse private server-side 24-hour snapshots. The existing updated
label displays original `generated_at`; locale/navigation changes do not force
an aggregate SQL refresh. The response includes snapshot expiry and refresh
interval. Current profile/billing/access operations remain live. This is not a
browser or service-worker private cache; no-store/offline rules are unchanged.

## Private Inbox image previews (2026-10-24)

V10 offers the existing inline image toggle for retained Android JPEGs and
source-owned Bot/Release image candidates. Inbox returns only a preview
eligibility boolean for Bot/Release; no provider reference/URL is returned.
Source plus internal ID identifies the DOM region and fixed first-party route,
so equal IDs from different source tables cannot address the wrong preview.
Unknown media/source types, orphans and payment receipts do not use this path.
Payment review retains its separately confirmed route and WebAuthn contract.

Images load only on an explicit tap, without preload, polling or automatic
retry. Fetch uses same-origin cookies, no-store, redirect rejection and a
15-second browser abort bound. Android remains JPEG / 550 KiB; Bot/Release
accept verified JPEG/PNG/WebP / 8 MiB / 20 million pixels through the existing
shared Bot client and bounded image loader. Source metadata SELECTs omit
feedback text. DB sessions close before provider IO. Current WebAuthn admin,
canonical source owner, file/type and source binding are checked before and
after IO; replacement/rebinding/removal, revocation or disabling rollout denies
old bytes. Original Bot canonical ownership never falls back to Telegram metadata;
Release resolves a positive Telegram identity to its current canonical account.

Provider IO has a 10-second deadline, two simultaneous loads and 30 attempts
per minute **per worker**, held only in constant-sized process memory. There
are no additional quota DB writes, distributed-limit claims, media cache,
background copy/backfill or R2 upload. Edge/global operational limits still
belong to separately approved staging.

One preview is held in memory. Close/toggle, drawer/source/account/page
navigation, locale change, offline/pagehide and session invalidation abort the
request and revoke its object URL. Generation checks reject late responses,
including a native response arriving after a different-source preview opened.
A 401 clears private UI; failures show unavailable. CSP/private no-store/SW and
external MCP permissions stay unchanged. Existing V10 cards, 44px buttons,
focus/escape and canonical UZ/RU/TJ toggle/alt text are reused; no new UI text.
Repository hsk-ai-ui and webapp-testing skills were read/applied.

Browser regression uses real SQLite/ASGI routes and the actual Telegram image
decoder with only Bot transport mocked: native JPEG, Bot WebP, Release PNG,
1440/390px UZ/RU/TJ, equal source IDs, retention/revocation, media/network errors,
late cancellation/reopen and URL cleanup. Intercepted requests omit Chromium's
network-generated Fetch Metadata; API tests separately prove explicit cross-site
rejection. This remains synthetic QA, not live Telegram/TLS/physical-device
acceptance. Other image formats remain unavailable rather than guessed.

## Explicit statistics file downloads (2026-10-24)

The Statistics screen reuses a V10 toolbar row with two 44px actions, JSON and
CSV, above the existing metrics. Repo hsk-ai-ui and webapp-testing skills were
read/applied for this new interaction. Canonical UZ/RU/TJ owns the two labels;
no learner UI resource or navigation redesign. Unavailable platforms can export
their explicit missing-data reason, without invented zero metrics.

Only a direct tap POSTs the selected platform/period/format to the fixed
first-party export route. Same-origin cookies, no-store, redirect rejection,
15-second abort and a streaming 128 KiB browser bound apply. Both controls stay
disabled while the single download is pending. No preload/poll/retry, saved URL,
private browser/SW cache or success claim for an unconfirmed filesystem save.
The user-initiated file save is explicit; server-side files/jobs are not created.

Epoch/view/locale guards discard late responses. Route/filter/locale changes,
offline/pagehide and session clearing abort the request and release any Blob URL.
Successful download URLs are released after a short one-second browser-consumption
window; a 401 clears private UI. Filenames come from fixed client constants and
allowlisted selected filters, never arbitrary server text.

Browser QA downloads real JSON/CSV bytes via actual SQLite/ASGI routes at
1440/390px in UZ/RU/TJ, checks source timestamps/PII omission/definitions, 44px
controls and no overflow, error/type/size rejection, URL cleanup and delayed
cancellation. This does not establish physical iPhone download/share behavior.
