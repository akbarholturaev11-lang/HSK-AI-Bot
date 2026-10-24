# Admin PWA Apple-first Web Push — implementation and acceptance contract

Owner scope update, 2026-10-24: prioritize **iPhone Home Screen PWA and macOS
Safari / Add to Dock web app**. Do not spend this increment implementing
Android/Windows-specific Admin PWA push. Keep Telegram Admin Mini App and
all learner apps unchanged.

## Separate the two products

- **Inbox:** already receives and displays stored BotFeedback, release feedback
  and retained Android bug reports, with first-party triage actions. This is
  visible only after the admin opens the PWA.
- **Web Push:** not implemented yet. A server-initiated *opt-in* alert wakes the
  device notification UI when a qualified event arrives. Push must never be
  mistaken for completed inbox delivery or replace durable inbox history.

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

## Security-first backend contract — not implemented

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

## Implementation order

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
