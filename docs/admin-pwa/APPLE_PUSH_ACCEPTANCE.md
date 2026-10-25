# Admin PWA Apple-first Web Push — implementation and acceptance contract

Owner scope update, 2026-10-24: prioritize **iPhone Home Screen PWA and macOS
Safari / Add to Dock web app**. Do not spend this increment implementing
Android/Windows-specific Admin PWA push. Keep Telegram Admin Mini App and
all learner apps unchanged.

## Owner operation decision — 2026-10-26

The owner wants important Admin PWA Apple Web Push **on by default**, with no
database-side preference/configuration and no repeated in-app enable steps.
The current behavior supersedes the historic default-OFF rollout description
below:

- Backend enrollment and sender **default ON when** private Admin PWA, valid
  persistent VAPID key pair, encrypted subscription storage key and valid HTTPS
  origin are configured. Explicit environment flags can still disable delivery
  during incidents. Never mint ephemeral secrets, log subscriptions or bypass
  allowlisted passkey administration.
- On an authenticated iPhone Home Screen PWA or eligible Mac browser/web app,
  an **existing OS permission grant** allows best-effort automatic subscription
  repair and authenticated registration during launch. No browser permission
  dialog appears without direct interaction. If OS consent has not been granted,
  the ready-to-subscribe header action requires **one tap**. On permission denial,
  respect OS settings instead of asking repeatedly or presenting fake success.
- Once enrolled, the first-party event outbox/scheduler works with the PWA
  closed, provided the production worker remains active; do not enable Railway
  App Sleeping for the worker-bearing web service.
- Per-install server subscriptions still use the private database as durable
  delivery routing state. The owner does **not** need to edit those rows.
- Physical iPhone + Mac acceptance is still required before claiming real
  notifications displayed. Provider-accepted HTTP responses alone do not
  establish user-visible delivery.

## Implemented, behind default-OFF flag (2026-10-24)

- **Inbox badge and priority filter:** `/api/admin/v1/inbox/unread-count`
  returns an authenticated, **bounded server-side** `99+` badge instead of
  counting just the first page. `inbox/list` has a real `priority=important`
  query on all four current sources (Bot, Release, Android and pending payments). Current message triage and the badge stay
  independent of Push delivery.
- **Push subscription foundation:** Alembic `0124_admin_pwa_push_subscriptions`,
  canonical-admin per-install encrypted PushSubscription storage (Fernet;
  endpoint SHA-256 uniqueness, active-device cap, no endpoint in API responses),
  and `/api/admin/v1/push/list|subscribe|revoke` behind
  `ADMIN_PWA_PUSH_ENABLED=false`. Server config additionally needs a valid
  public VAPID key and private Fernet storage key. Existing authentication,
  Origin, CSRF and active WebAuthn admin guards are reused. Apple
  `*.push.apple.com` delivery endpoints are strictly validated.
- **Apple UI:** iPhone standalone PWA / Mac Safari-capability detection,
  explicit opt-in button, synchronous gesture-driven permission request and
  per-device revoke UI; canonical UZ/RU/TJ translations.
- **Service Worker:** basic privacy-safe visible `push` handler and fixed
  same-origin `/admin/?inbox=1` click destination. Deep-link opening
  requires current verified passkey admin session. No private content is
  embedded in notification payload.
- **Implemented in later branch-only commits (through `171fc3ef`):** payment/Android
  default-important events and per-device deduplicated outbox (`0125`), VAPID
  private signing, RFC 8291 encrypted generic Web Push payload, leased worker,
  bounded retries, 404/410 device revocation, and independent guarded server
  scheduler plus worker CLI. `sending_enabled` now reflects validated sender
  configuration; all rollout flags default OFF. `app.js` shows the previous
  not-sending message only when the server says sender is not ready.
- **NOT YET VERIFIED/RELEASED:** actual Apple Push service acceptance,
  notification display on physical iPhone/Mac, production VAPID/secrets,
  operator-approved isolated HTTPS staging, proxy/TLS and live migrations.
  Provider tests use mocked responses. Sender readiness is **not** evidence
  of a displayed or received notification.
- Testing: isolated SQLite/real disposable PostgreSQL/virtual Chromium
  regressions are run in GitHub CI for branch-only increments; check each
  latest head before calling it verified. No live migration or permission
  request was performed on the owner's hardware.

## Separate the two products

- **Inbox:** already receives and displays stored BotFeedback, release feedback
  and retained Android bug reports, with first-party triage actions. This is
  visible only after the admin opens the PWA.
- **Web Push:** server-side sender is implemented behind default-OFF flags,
  but live Apple delivery remains untested and disabled. Once separately
  configured and verified, an opted-in alert may wake the device. Web Push
  never replaces durable Inbox history.

## Supported Apple clients

1. **iPhone (iOS >=16.4):** install `https://hskai.app/admin/` to **Home Screen**,
   launch the installed icon, then press an explicit in-app enable button.
   Safari browser-tab permission alone does not fulfill the iOS Home Screen
   Web Push acceptance test. Test screen lock, Notification Center, Focus,
   tap-to-open the admin inbox and optional app icon badge.
2. **Mac (Safari >=16 on macOS >=13):** use Safari permission after a direct
   user gesture, and test with a Safari **Add to Dock** web app as the preferred
   admin experience. Test delivery with the PWA/tab closed, Notification Center,
   Dock app badge and notification click/re-auth behavior.
3. **Independent subscriptions:** one canonical allowlisted admin may own
   multiple device/browser subscriptions, including one iPhone and one Mac.
   Revoking or reinstalling one device must not unexpectedly revoke the other.
   Both devices require explicit per-install opt-in.
4. Do not show onboarding permission prompts, attempt silent permission,
   assume Mac Touch ID/Face ID permission applies to notifications, or fake
   notifications in UI fixtures as live pushes.

## Security-first backend contract — code implemented; staging/device acceptance pending

- Dedicated first-party push registration and revocation API under
  `/api/admin/v1/push/*`. Requires current canonical Admin PWA session,
  same-origin/CSRF checks, bounded schema and verified allowlist. Never an MCP
  capability or a legacy Telegram `initData` bypass.
- Server-generated **VAPID** key pair managed in environment secrets and
  rotated deliberately. Never embed the private key in app JS, generated
  resources, Git commits or logs. Public key may be delivered to the client.
  HTTPS/TLS and outgoing Apple `*.push.apple.com` connectivity are staging gates.
- Persist only encrypted or equivalently protected endpoint/key material
  with per-admin/device ownership, created/last-seen/disabled timestamps.
  Treat a PushSubscription endpoint as a sensitive bearer-like delivery target.
  On 404/410 push service response, revoke only that stale subscription.
- Subscription API distinguishes registration/update/revocation from send.
  Delivery queue uses immutable event/source dedup keys, bounded retries,
  rate limiting, logs without secrets or message content, and idempotent
  dispatch. A 2xx push response means acceptance by push service, not proven
  presentation to the user.
- Default **no push**. Start with one essential class: **new important inbox
  event** or critical admin/system alert; avoid notifications for every normal
  comment, read/unread changes, refresh and dashboard statistics. Criticality
  must be derived from verified server state, not a spoofable client value.
- Push payloads must contain **no student name, payment, message text, raw
  Telegram ID, screenshot, access token or private data**. Prefer generic
  localized `HSK AI Admin — new important message` and an internal inbox URL
  on the same origin. Re-authenticate before displaying any private details.
- Keep notification click inside app scope and use the existing
  `/admin/` launch/deep-link contract; never include an arbitrary URL from
  feedback in the notification.
- Do not cache endpoints/push payloads/private API content in service worker.
  Handle Safari/WebKit's requirement that a received push results in a visible
  user-facing notification rather than silent background work.
- Icon badge uses a **server-authoritative unread count**, not an estimate
  from the first inbox page. Empty/offline/error states must never erase an
  established badge based on a fabricated zero.

## Implementation and acceptance order (code through E; physical F pending)

A. Finish current Inbox triage controls + canonical UZ/RU/TJ, iPhone-sized
   touch controls and browser regressions. This work does NOT deliver Web Push.
B. Inventory/admin-system notice producers and select explicit alert class
   definitions. Create bounded unread-count projection and one consistent
   event identity, accounting for native retention and per-source triage.
C. Add protected per-device PushSubscription storage, migration, ownership
   guards, VAPID public-key/config/registration/revoke endpoints and tests.
D. Add explicit opt-in and settings panel for iPhone/Mac. Register through
   installed PWA's existing public Service Worker, direct tap permission request,
   PushManager subscription, and an opt-out control. Do not block normal login.
E. Add server-side encrypted Web Push sender, durable outbox/dedupe,
   per-subscription throttling, provider 404/410 handling, generic visible
   payload, notificationclick and badge behavior; tests mock push providers.
F. Deploy to an isolated, owner-authorized HTTPS staging domain with approved
   DNS/TLS/VAPID config and physical iPhone + Mac. Check Focus/permission
   denial, lock screen, app closed, reconnect/reinstall, expired auth,
   cross-device revocation, provider outages and rollback. Do not enable
   production pushes or notifications until owner approves real tests.

## External references

- Apple Developer: https://developer.apple.com/documentation/usernotifications/sending-web-push-notifications-in-web-apps-and-browsers
- WebKit iOS home-screen Web Push: https://webkit.org/blog/13878/
- Apple Support Mac web apps: https://support.apple.com/en-gb/104996
