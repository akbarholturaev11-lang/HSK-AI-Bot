# Pomp HSK AI Desktop — canonical handoff

## Goal

`HSK AI bot` is the only canonical project. Telegram bot, Mini App, backend,
subscription, referral, progress, analytics and the future macOS/Windows client
share one account and one backend.

The desktop source lives in `desktop/`. Built DMG, EXE and GGUF files do not
belong in Git; they will be published to release storage/CDN such as R2.

## Current result

### Telegram acquisition — implemented

1. The authenticated Mini App asks the backend for release status.
2. Profile, home prompt, lesson-end promo and ad promo can show Mac/Windows
   actions when a real release is enabled.
3. A click sends fresh Telegram `initData`, platform, placement and a stable
   retry `event_id` to `/api/v3/desktop-download/request`.
4. The backend returns an opaque tracked branded `download_page_url` and safe
   `file_name`.
5. The Mini App opens `/desktop-download` with `Telegram.WebApp.openLink`.
6. The branded page downloads the current artifact through
   `/downloads/{platform}`; the optional request token preserves click analytics.
7. Mobile users must confirm that a desktop installer link will be opened on
   their phone.
8. No installer message is sent to the bot chat and the Mini App is not closed
   automatically.

The repository default and `.env.example` keep
`DESKTOP_DOWNLOADS_ENABLED=false` until real signed artifacts exist. The UI
stays hidden in any deployment with that setting. The deployed Railway
environment was not verified or changed in this task.

### Telegram device approval — implemented on the backend/bot

The bot is used only after installation. Opening a `desktop_CODE` deep link
shows platform, app version and code, then requires an explicit
`Tasdiqlash / Bekor qilish` action. Merely opening the link never connects the
account.

The backend supports single-use link codes, device binding, rotating refresh
tokens, access-token verification, revoke and bootstrap. The native Rust client
stores refresh credentials in macOS Keychain or Windows Credential Manager.

### Analytics/admin — implemented

The direct funnel is:

`request → download accepted/opened → tracked URL → account linked → first open`

Only authenticated `desktop_first_open` is an install. A click or accepted
download dialog is not an install. Admin Mini App and bot statistics include
funnel, DAU/WAU/MAU, platform, version, AI Pack and sync placeholders for future
runtime events.

### Desktop Phase A — implemented

The Tauri v2 source and lock files are in `desktop/`. The dedicated
`desktop/ui` application now implements:

- explicit Telegram device-link UI;
- adaptive Variant A course workspace;
- server-authoritative course map, lessons, access and completion;
- renderers for every checked-in Course v3 card type;
- profile and UZ/RU/TJ language switching;
- right-edge circular AI launcher/drawer;
- truthful local model state without fake inference;
- strict CSP and named native commands only.

Rust owns tokens, secrets, allowlisted HTTP and credential storage. The
webview has no direct network transport. Phase A is online-first; offline
course cache/sync and real local AI inference are not implemented. The updater,
release endpoint and build pipeline are implemented but remain fail-closed
until real artifacts and clean-machine tests exist.

## Release configuration

`DESKTOP_AUTH_SIGNING_SECRET` is required for desktop auth. An artifact URL is
required per enabled platform; version labels are optional but recommended.
`DESKTOP_DOWNLOAD_BASE_URL` may fall back to the HTTPS origin of
`MINI_APP_BASE_URL`.

```text
DESKTOP_DOWNLOADS_ENABLED=false
DESKTOP_DOWNLOAD_BASE_URL=
DESKTOP_MAC_DOWNLOAD_URL=
DESKTOP_WINDOWS_DOWNLOAD_URL=
DESKTOP_MAC_VERSION=
DESKTOP_WINDOWS_VERSION=
DESKTOP_AUTH_SIGNING_SECRET=
```

The signing secret must be private and at least 32 characters. The final CDN
artifact response, after redirects, must include:

```text
Content-Disposition: attachment
Access-Control-Allow-Origin: https://web.telegram.org
```

## Recommended desktop UI

### Variant A — adaptive course workspace (recommended)

- Left: compact course/lesson navigation.
- Center: current lesson and practice.
- Right edge: the requested circular AI button.
- AI button opens a focused chat drawer; it is not a large separate section.
- Profile, subscription and progress remain the same shared product.
- On narrow windows the left navigation collapses and AI becomes a bottom
  sheet.

This is the best balance: familiar to current users, comfortable on a computer
and does not make AI compete with the course.

### Variant B — enlarged Telegram layout

Keep the current single-column Mini App and only widen spacing. It is fastest,
but wastes desktop space and will feel like a phone app inside a window.

### Variant C — full three-panel dashboard

Always-visible navigation, lesson and AI panels. It is powerful for large
screens but too dense for the first release and requires more UX/testing work.

Decision: build Variant A.

## Next implementation phase

1. Add local course cache, entitlement snapshot, offline progress queue and
   conflict-safe sync.
2. Implement local AI runtime and signed/checksummed optional model download.
3. Run the signed updater flow on clean macOS and Windows machines and document
   recovery behavior.
4. Make public link-start limiting atomic, enforce ingress request-body limits
   and schedule expired link/session retention cleanup. Add an expiry or
   deliberate one-time policy for tracked download tokens.
5. Add optional Google OAuth and passwordless email login as identities linked
   to the same internal user; implement explicit account-link/merge protection
   so subscription and progress never split.
6. Run the release workflow for macOS universal DMG and Windows x64 NSIS EXE.
7. Test unsigned free-plan install/uninstall instructions on clean machines.
8. Upload artifacts, verify final headers, set URLs/versions/signatures, then enable the
   release flag.

## Acceptance gates before public download

- Desktop login works only after explicit Telegram confirmation.
- Same Telegram account, subscription and progress appear on both clients.
- Logout revokes the server device/session.
- Offline course works after first sync.
- Offline actions sync exactly once after reconnect.
- Local AI works without internet and never leaks prompts to the network.
- No arbitrary URL, token, shell or filesystem control is exposed to webview
  JavaScript.
- Free-plan Gatekeeper and SmartScreen instructions are verified.
- Checksums, updater signatures and recovery path are tested.
- Public link-start uses an atomic limiter; ingress body-size and expired-link
  retention controls are active.
- Tracked installer URLs have an explicit, tested expiry/consumption policy.
- Admin first-open and DAU/WAU/MAU receive real runtime events.
- `DESKTOP_DOWNLOADS_ENABLED=true` is the final release action, not an early
  development step.

## Verification already completed

- Python non-E2E suite: `305 passed`, plus `112 subtests`.
- Focused desktop/backend/static suite: `74 passed`, plus `4 subtests`.
- Direct-download Playwright: `5 passed` for branded page, link opening, mobile
  confirmation and short-viewport behavior.
- Final static desktop integration: `9 passed`, plus `4 subtests`.
- Existing practice Playwright checks affected by the new shared module:
  `2 passed`.
- Rust: `cargo fmt --check`, `cargo check --locked --offline`,
  `cargo test --locked --offline`, `cargo clippy --locked --offline
  --all-targets -- -D warnings` passed.
- Desktop UI contract tests: `6 passed`.
- Desktop Chromium preview flows: `8 passed`, covering link, course, lesson,
  profile, AI drawer, `720x560`, half-preview, dialog blank, unsupported cards
  and stale-request protection.
- Desktop course/auth/download/static focused regression: `73 passed`, plus
  `4 subtests`.
- Alembic has one head: `0066_desktop_foundation`.

The full pre-existing Playwright file still contains unrelated baseline
assertion failures around changed lesson copy/resume, admin access UI and
subscription copy. They are outside the desktop acquisition change; do not
misreport the entire file as green until those existing expectations are
updated or fixed separately.
