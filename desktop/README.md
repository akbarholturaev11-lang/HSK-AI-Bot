# HSK AI Desktop

This directory is the canonical Tauri v2 desktop client inside the shared
`HSK AI bot` repository. Telegram bot, Mini App, backend, subscription,
progress, referrals, analytics and desktop remain one product ecosystem.

## Desktop 1.3 result

- Product identity: `HSK AI` / `com.pomp.hskai`
- Main window: `1180x780`, minimum `720x560`
- Dedicated frontend: `desktop/ui`
- Adaptive course workspace with left lesson navigation
- Right-edge circular AI launcher and focused drawer
- Explicit Telegram device-link approval UI
- Server-authoritative course map, access, progress and completion
- Free-course parity: two full parts, then a non-rewarding half-preview boundary
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

The Mini App requests a tracked installer page and opens the branded
`/desktop-download` site with `Telegram.WebApp.openLink`. The user then downloads
the current macOS or Windows installer directly from `/downloads/{platform}`.
No installer or link is sent into bot chat, and the Mini App is not closed.

After installation, the desktop app shows a short code. The bot displays the
device information and requires an explicit approve/cancel action. Opening the
deep-link alone never links an account.

Future Google/email login must be added as another identity provider linked to
the same internal user, not as a second progress/subscription account.

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

## Release status

Version `1.3.0` includes the signed-updater client/backend, native local-AI
commands and a tag/manual GitHub Actions pipeline for universal macOS DMG and
Windows x64 NSIS artifacts. Release CI fetches the pinned llama.cpp `b10223`
runtime and fails closed unless every upstream archive matches its exact
SHA-256. Runtime binaries and installers remain outside Git. Before public
release the following still remain:

- offline course cache, durable action queue and conflict-safe sync;
- GitHub/R2 secrets, real public artifact URLs and updater metadata;
- universal macOS and Windows builds from the release workflow;
- clean-machine install/uninstall tests;
- clean-machine automatic-update tests;
- free-plan unsigned macOS/Windows warning instructions;
- public link-start hardening/cleanup gates documented in
  `../DESKTOP_AUTH_CONTRACT.md`.

Installer downloads and updates remain disabled until verified HTTPS artifacts
and release metadata are configured. Built DMG, EXE, updater and GGUF files must
stay outside Git on approved release storage/CDN.

The release workflow intentionally reads only
`TAURI_SIGNING_PRIVATE_KEY_V4` and
`TAURI_SIGNING_PRIVATE_KEY_PASSWORD_V4`. The corresponding private key stays
outside the repository; never commit or print it. The same workflow requires
the bucket-scoped `R2_*` secrets and `R2_PUBLIC_BASE_URL` Actions variable when
`publish_to_r2=true`.
