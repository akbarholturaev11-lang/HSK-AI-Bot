# HSK AI Desktop

This directory is the canonical Tauri v2 desktop client in the HSK AI
multi-platform repository. Telegram bot/Mini App, Android, desktop, public site
and backend form one product ecosystem. Authenticated clients share the same
internal learner identity, subscription, course progress and access decisions.
Google/Apple provider identities may be linked to that internal account;
provider email is not proof for automatic account merging.

## Desktop client capabilities

- Product identity: `HSK AI` / `com.pomp.hskai`
- Main window: `1180x780`, minimum `720x560`
- Dedicated frontend: `desktop/ui`
- Adaptive course workspace with left lesson navigation
- Right-edge circular AI launcher and focused drawer
- Explicit Telegram device-link approval UI
- Server-authoritative course map, access, progress and completion
- Course access: server-side entitlement and configured lesson-limit policy;
  Desktop currently serves the full lesson when access is allowed and does not
  apply a client-side half-lesson preview (`DesktopCourseService.preview_half`
  is false).
- Uzbek, Russian and Tajik profile/language switching
- Renderers for every checked-in Course v3 card type
- Retry-safe lesson completion with stable event IDs
- Optional confirmed-local webview/OS Chinese speech fallback
- Explicit, resumable and checksum-verified optional AI Pack installation
- Loopback-only llama.cpp chat runtime with bounded streaming and cancellation

Course and authentication remain online-first. The local AI runtime works
without internet after the model has been verified, but a cold app start still
requires online bootstrap until an expiry-bounded offline entitlement cache is
implemented.

## Runtime boundary

Rust owns:

- the allowlisted production API origin;
- access-token memory and refresh-token OS credential storage;
- Telegram link secrets/deep-link;
- authenticated HTTP requests and one refresh retry;
- input bounds and native external-link opening.

The webview receives no access/refresh token, polling secret or arbitrary URL.
It can invoke only named commands:

```text
desktop_app_info
desktop_auth_status
desktop_link_start
desktop_link_poll
desktop_link_open_telegram
desktop_bootstrap
desktop_logout
desktop_course_map
desktop_lesson_data
desktop_lesson_complete
desktop_set_language
desktop_tts_speak
desktop_subscription_overview
desktop_subscription_quote
desktop_subscription_submit
local_ai_model_status
local_ai_install_start
local_ai_install_cancel
local_ai_pack_remove
local_ai_chat
local_ai_chat_cancel
desktop_update_check
desktop_update_install
```

The strict CSP permits local application assets, production avatar images and
Tauri IPC only. Frontend code does not use direct `fetch`, `XMLHttpRequest` or
`WebSocket`.

## Shared backend APIs

Desktop course traffic uses the same user, access policy and progress system as
the Telegram product:

```text
GET  /api/v3/desktop/course/map
GET  /api/v3/desktop/course/lesson/{lesson_order}
POST /api/v3/desktop/course/complete
POST /api/v3/desktop/preferences/language
POST /api/v3/desktop/events
```

Completion is server-authoritative and idempotent. Client mistakes contain
only stable material references and selected answers/tokens; the server
rebuilds trusted review material from the checked-in lesson JSON.

## Download and account flow

The Mini App opens the shared branded `/desktop-download` page with
`Telegram.WebApp.openLink`. The backend exposes only currently configured
releases there: macOS and Windows installers use `/downloads/{platform}`, and
Android can use `/downloads/android` when a direct URL exists. Android also has
its separate bot-chat delivery path when the current release is available by
Telegram `file_id`. Desktop installers are downloaded directly; the Mini App
does not close or send a desktop installer through the bot.

After installation, the desktop app shows a short code. The bot displays the
device information and requires an explicit approve/cancel action. Opening the
deep-link alone never links an account.

Desktop has Google and Apple OAuth flows. Provider identities link to the same
internal `users.id`, so course progress and subscription are shared rather than
creating a separate provider account. Email is metadata, not an account lookup
or ownership proof. See `../DESKTOP_AUTH_CONTRACT.md` and `../OAUTH_SETUP.md`.

## Local preview

The mock is deliberately available only on localhost with `mock=1`; production
never silently falls back to fake data.

```bash
cd desktop/ui
python3 -m http.server 8766 --bind 127.0.0.1
```

Open:

```text
http://127.0.0.1:8766/?mock=1
```

Use `&unlinked=1` to preview the explicit Telegram linking screen.

## Development and verification

Prerequisites:

- Node.js LTS
- Rust stable
- Tauri v2 system prerequisites for the target OS

```bash
cd desktop
npm ci
npm run test:ui
npm run dev
```

Native checks:

```bash
cd desktop/src-tauri
cargo fmt --check
cargo check --locked
cargo test --locked
cargo clippy --locked --all-targets -- -D warnings
```

Focused backend/UI checks from the repository root:

```bash
venv_311/bin/python -m pytest -q tests/test_desktop_course_api.py
venv_311/bin/python -m pytest -q tests/e2e/test_desktop_ui_preview.py
```

## Build and release source

Source version is `1.4.3` in `desktop/package.json`,
`desktop/src-tauri/tauri.conf.json`, and `desktop/src-tauri/Cargo.toml`. This
source value does not prove which version is currently published or installed.

`.github/workflows/desktop-release.yml` accepts a `desktop-v<version>` tag
only when it matches the source version and points to a commit contained in
`origin/main`. Manual releases must run from `main`. The workflow builds a
universal macOS DMG and Windows x64 NSIS installer; R2 publishing is controlled
by the workflow input. It pins llama.cpp `b10223` and verifies upstream
archives against recorded SHA-256 values.

Backend download and updater defaults in `app/config.py` are
`DESKTOP_DOWNLOADS_ENABLED=false`, `DESKTOP_RELEASE_MANIFEST_URL` blank, and
`DESKTOP_UPDATES_ENABLED=false`. These are source defaults, not proof of live
production settings. Check the hosting environment and current release
manifest before reporting whether downloads or updates are enabled.

The workflow expects signing material through
`TAURI_SIGNING_PRIVATE_KEY_V4` and
`TAURI_SIGNING_PRIVATE_KEY_PASSWORD_V4`, plus bucket-scoped `R2_*` secrets and
`R2_PUBLIC_BASE_URL` when publishing to R2. Keep values outside the repository.
Generated installers, updater artifacts, and GGUF files stay outside Git on
approved release storage.
