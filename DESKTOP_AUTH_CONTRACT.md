# Pomp Desktop Acquisition and Auth Contract

## Product boundary

The Telegram Mini App, bot, backend and desktop client use one canonical
account, subscription, referral, course-progress and analytics system. The
desktop client does not create a second account or payment system.

Future Google OAuth or passwordless email login must be modeled as additional
identities linked to the same internal user. A provider login must never create
a parallel subscription/progress account when the person already uses
Telegram; linking or merging requires explicit ownership confirmation.

No public Pomp DMG, EXE or GGUF artifact is enabled yet. Their source, build
configuration and release metadata remain in this repository. A local ARM64
macOS test DMG exists outside Git; public artifacts will be stored on approved
release storage/CDN.

## Direct-download acquisition

1. The user selects macOS or Windows inside the authenticated Telegram Mini App.
2. The backend verifies fresh Telegram `initData`, release availability,
   platform, placement and rate limits.
3. The backend returns an opaque tracked HTTPS `download_page_url` and a safe
   `file_name`.
4. The Mini App opens the branded `/desktop-download` page with
   `Telegram.WebApp.openLink(url)`.
5. The branded page downloads through `/downloads/{platform}`. A valid optional
   request token preserves idempotent click analytics.

No installer/download message is sent to the Telegram bot chat. The bot is used
after installation only for device-link approval.

Opening the branded page does not prove that the installer finished downloading
or was installed. The Mini App must not close automatically. Mobile users must
confirm before opening a desktop installer page on their phone.

Release UI and download endpoints fail closed while
`DESKTOP_DOWNLOADS_ENABLED=false`, an artifact URL is absent, or the URL is not
approved HTTPS. Only authenticated `desktop_first_open` counts as a verified
installation.

The current tracked download token is replayable and its click analytics are
deduplicated. Token expiry or deliberate one-time consumption must be chosen
and implemented before public installer release.

The final artifact response, including the response after any redirect, must
send `Content-Disposition: attachment` and
`Access-Control-Allow-Origin: https://web.telegram.org`. These headers are
release-storage/CDN configuration, not proof that a download or install
finished.

## Native security boundary

The native app never receives Telegram `initData`, and the webview never
receives access or refresh tokens. Rust owns desktop authentication, OS
credential storage and authenticated network calls.

JavaScript may invoke only named native operations. It cannot provide an
arbitrary URL, host, authorization header, token, shell command or filesystem
path.

Production transport is HTTPS to the compile-time allowlisted API origin.
Redirects to a different origin are rejected. Secrets and tokens must never be
placed in URLs, logs, analytics, local/session storage or JavaScript responses.

## Device-link flow

1. Rust creates a random installation key and stores it in the OS credential
   store.
2. `POST /api/v3/desktop-auth/link/start` accepts the platform, app version and
   installation key. It returns a short display code, opaque polling secret and
   Telegram bot deep-link. The default link lifetime is 10 minutes.
3. Rust retains the polling secret in native memory. The webview receives only
   display-safe fields.
4. The user opens `https://t.me/<bot>?start=desktop_<code>`. The bot shows
   platform, app version and code, then requires an explicit
   `Approve / Cancel` action. Opening the link reserves the pending code to the
   first Telegram user who views this confirmation, but does not bind the
   account. Only that user can approve or cancel it.
5. Approval atomically binds the pending code to the current Telegram account;
   cancellation invalidates it.
6. Rust calls `POST /api/v3/desktop-auth/link/status`. It is a POST request so
   the polling secret cannot leak through URL/access logs.
7. The first valid approved poll atomically consumes the code and returns one
   short-lived access token and one rotating refresh token. Later polls never
   return the tokens again.

## Token lifecycle

- Access token: HMAC-SHA256 signed, 15-minute default lifetime, containing
  session/device/user identifiers plus token type, issued/expiry timestamps
  and a random `jti`.
- Refresh token: high-entropy opaque value, 30-day default lifetime, stored only
  as a keyed hash on the server and only in OS secure storage on the client.
- Refresh rotates on every use. Immediate reuse of the previous refresh token
  revokes the session.
- Every authenticated request verifies token signature, expiration and current
  session/device revocation state.
- Online logout revokes the session. The native client always clears its local
  refresh/access credentials even when the revoke request cannot reach the
  server; in that offline case the unreachable server session remains
  unusable from that installation and expires by its normal TTL. Explicit
  unlink also revokes the device and permits a deliberate link to a different
  Telegram account.

## Replay and binding rules

- Display code, polling secret and link request are single-use and expire.
- Approval uses a database row lock; concurrent approval cannot bind two users.
- Polling secrets are compared in constant time.
- An active installation key cannot silently move from account A to account B.
  The device must first be explicitly unlinked.
- `desktop_first_open` is emitted once per device; regular launches emit
  deduplicated `desktop_app_opened` analytics.

## Fail-closed rules

- `DESKTOP_AUTH_SIGNING_SECRET` must be a private deployment secret of at least
  32 characters. Desktop auth is unavailable when it is absent or weak.
- Link start has per-installation and global server caps. Production ingress
  should additionally rate-limit the public endpoint. The current global
  database `count → insert` guard is not atomic under a parallel burst.
- Auth JSON bodies are capped and validation errors return only stable codes
  with `Cache-Control: no-store`; production ingress should mirror the body-size
  limit.
- Expired link/session cleanup and a tracked-download token expiry policy are
  required before public release.
- Direct-download work must not enable `DESKTOP_DOWNLOADS_ENABLED` before signed
  installers and real release URLs exist.
- Server errors return stable codes and never include raw secrets or tokens.
- Download intent, redirect click and verified installation remain distinct
  analytics stages.

## Phase 1 endpoints

- `GET /api/v3/desktop-download/status`
- `POST /api/v3/desktop-download/request`
- `POST /api/v3/desktop-download/started`
- `GET /downloads/{platform}?request=<opaque-token>`
- `POST /api/v3/desktop-auth/link/start`
- `POST /api/v3/desktop-auth/link/status`
- `POST /api/v3/desktop-auth/refresh`
- `POST /api/v3/desktop-auth/revoke`
- `GET /api/v3/desktop/bootstrap`
- `GET /api/v3/desktop/course/map`
- `GET /api/v3/desktop/course/lesson/{lesson_order}`
- `POST /api/v3/desktop/course/complete`
- `POST /api/v3/desktop/preferences/language`

Handled desktop auth responses, including request-validation errors, use stable
error codes, `Cache-Control: no-store`, and never echo secret input.
Mini App download status/request/started calls use fresh
`X-Telegram-Init-Data`; redirect URLs use their opaque request token.
Desktop link start/status/refresh calls use bounded body secrets. Only revoke
and bootstrap accept `Authorization: Bearer <access-token>`.
