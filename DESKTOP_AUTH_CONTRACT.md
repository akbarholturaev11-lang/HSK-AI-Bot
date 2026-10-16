# Pomp Desktop Acquisition and Auth Contract

## Product boundary

The Telegram Mini App, bot, backend and desktop client use one canonical
account, subscription, referral, course-progress and analytics system. The
desktop client does not create a second account or payment system.

Google and Apple resolve an existing verified provider subject or create a new
canonical user on first sign-in. To reuse an existing account through another
provider, sign in to that account and explicitly connect the provider first.
Email equality never merges accounts. Linked identities share that user's
subscription and progress and are never reassigned between users.

Release availability depends on deployment configuration and release storage.
Source defaults keep desktop downloads and updates disabled and leave the
release-manifest URL blank. This contract describes the implementation; it does
not assert which artifacts are currently published or enabled in production.

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
deduplicated. Its configured lifetime defaults to 24 hours and is bounded to
5 minutes–7 days; the download endpoint rejects expired tokens with HTTP 410.

The `/downloads/{platform}` link uses normal browser navigation, and the API
redirect adds `Content-Disposition` plus
`Access-Control-Allow-Origin: https://web.telegram.org`. The final artifact
response must also send `Content-Disposition: attachment` with a safe filename
so the browser downloads the file. CORS on the artifact host is not required
for this navigation flow; add it if a future client fetches the bytes
cross-origin. Headers do not prove that a download or install finished.

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

   **Android is the one platform whose deep link carries its request id**
   (`?start=android_link_<request id>`), so the bot asks for no code at all:
   it shows device and app version with the same `Approve / Cancel`, over
   `link_request_confirmation` / `approve_link_request` /
   `cancel_link_request`. Opening that link reserves the request to the first
   Telegram user the same way, so only that chat can approve or cancel it, and
   the row is still single-use and still expires with the link TTL. The
   trade-off is deliberate and Android-only: a forwarded link can reach a
   confirmation screen, which is why the screen names the device and version
   and why the desktop code path is unchanged. The id is not a secret that
   mints a session — the token pair is still handed only to the client holding
   the polling secret.
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
- Link start enforces a per-installation cap (5 requests per 5 minutes) and a
  configurable global cap (120 per 60 seconds by default). On PostgreSQL, a
  transaction-scoped advisory lock serializes the global count/check and insert
  across application processes. An ingress-level limit can provide additional
  defense in depth; it is deployment configuration, not this service guard.
- Auth JSON bodies are capped and validation errors return only stable codes
  with `Cache-Control: no-store`; production ingress should mirror the body-size
  limit.
- The hourly retention task deletes expired link requests and expired or
  revoked sessions after the configured retention period (30 days by default,
  bounded to 1–365 days). Cleanup failure is logged and retried on the next
  hourly run; authentication continues to reject expired/revoked records.
- Direct-download work must not enable `DESKTOP_DOWNLOADS_ENABLED` before signed
  installers and real release URLs exist.
- Server errors return stable codes and never include raw secrets or tokens.
- Download intent, redirect click and verified installation remain distinct
  analytics stages.

## Provider identity

Google and Apple can create a canonical account on first verified sign-in or
prove an existing account by provider subject. Explicit linking still requires
an authenticated account. OAuth callbacks do not mint their own sessions.

- `user_identities` holds one row per `(provider, subject)`. `UNIQUE (provider,
  subject_hash)` makes an identity belong to at most one internal user,
  globally; `UNIQUE (user_id, provider)` allows one account per provider per
  user. The provider `sub` is stored only as a keyed HMAC, so a database dump
  does not expose usable, cross-service-linkable provider identifiers.
- `desktop_link_requests` carries `flow` (`telegram` | `google` | `apple`),
  `intent` (`signin` | `link`) and `bind_user_id`. Existing rows default to
  `telegram`/`signin`, so the Telegram flow is byte-for-byte unchanged.
- **One token path.** A provider flow only marks the link row approved. The
  client then calls the unchanged `link/status`, and `poll_link` mints the same
  device + session + token pair. No OAuth endpoint returns a token.
- **Three guards, all fail-closed.** `poll_link` rejects `intent != "signin"`
  (otherwise "connect Google" would issue a session to whoever owns that Google
  account); the Telegram bot's approve/preview/cancel paths reject
  `flow != "telegram"`; the OAuth callback rejects `flow == "telegram"`.
- **Account resolution never reads an email.** `email_hash` / `email_display`
  are display and abuse-analytics metadata only. An email address is
  attacker-influenceable, provider-scoped and recyclable, so matching on it
  would turn a provider login into subscription takeover.
- **A bound device is not consent.** An unrecognised identity arriving on a
  device already signed in as user X is refused with
  `desktop_device_bound_to_other_user`, never auto-linked. Linking is only ever an
  explicit, bearer-authenticated action.
- **Identities are never reassigned.** A `(provider, subject)` already bound to
  another user returns `oauth_identity_bound_to_other_user`; the row is not
  moved.
- **A blocked account cannot sign in or add a provider.** The Telegram flow
  gets this from `BlockedUserMiddleware`, which stops every bot handler, so a
  blocked user can never reach the approval step. A provider flow has no bot
  step, so `resolve_signin` and `link_to_user` refuse a blocked account
  explicitly with `user_blocked` (403). Without that, a Google account linked
  before the block would remain a way back in.
- **Unlink revokes access.** Removing an identity revokes every other session
  on the account and reports how many, so removed access cannot silently
  persist. The last remaining identity of a user without `telegram_id` cannot
  be removed.
- ID tokens are verified against pinned, hard-coded JWKS URIs with `alg` fixed
  to RS256, the issuer and this client's own audience only (never a union of
  audiences, which would allow cross-client replay), a server-derived nonce
  that must be present, and a maximum `iat` age of 300 seconds.
- `state`, `nonce` and the PKCE `code_verifier` are derived from the link
  request id with the server signing secret, never stored. `state` is therefore
  self-authenticating and single-use; any verification failure burns the row.
- The native clients never see an OAuth secret. Rust holds the authorization
  URL and opens the system browser itself, against a compile-time allowlist of
  `accounts.google.com/o/oauth2/v2/auth` and
  `appleid.apple.com/auth/authorize`.
- A verified Google/Apple sign-in on an unbound installation creates a canonical
  `users.id` and its unique provider identity atomically. Its Telegram ID stays
  NULL. The selected UZ/RU/TJ language initializes only a new account; existing
  preferences remain server-owned. Email equality never merges accounts.
- macOS and Windows share the same provider buttons, pre-auth language selector,
  Rust browser-opening commands and polling/session flow. Only configured
  providers are offered. Provider verification never shows a Telegram code.
- Course, practice, leaderboard, AI and voice ownership use the authenticated
  canonical User. Existing manual payments and referral attribution still
  require a real Telegram identity; provider-only accounts receive explicit
  read-only/unavailable responses rather than synthetic IDs or shared NULL data.
- The Telegram Mini App can attach a provider from Profile, proving identity
  with fresh `initData` instead of a bearer token. `miniapp` is not a native
  platform: it owns no device, is accepted only on `intent="link"` rows, is
  refused outright by the sign-in endpoint, and its installation key is derived
  server-side from the account so the per-installation rate limit still
  applies. It is another client for linking, not another way in.

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
- `GET /api/v3/native-auth/providers`
- `POST /api/v3/native-auth/oauth/start`
- `POST /api/v3/native-auth/oauth/assert`
- `GET /api/v3/native-auth/oauth/callback/google`
- `POST /api/v3/native-auth/oauth/callback/apple`
- `GET /api/v3/native-auth/identities`
- `POST /api/v3/native-auth/identities/link/start`
- `POST /api/v3/native-auth/identities/link/status`
- `POST /api/v3/native-auth/identities/unlink`

The four `identities` endpoints accept either `Authorization: Bearer` (native
clients) or a fresh `X-Telegram-Init-Data` header (Mini App).

Handled desktop auth responses, including request-validation errors, use stable
error codes, `Cache-Control: no-store`, and never echo secret input.
Mini App download status/request/started calls use fresh
`X-Telegram-Init-Data`; redirect URLs use their opaque request token.
Desktop link start/status/refresh calls use bounded body secrets. Only revoke
and bootstrap accept `Authorization: Bearer <access-token>`.
