# Admin PWA — project context (temporary)

> **SCOPE: HSK AI ADMIN PWA ONLY** — temporary task file. Work branch: `codex/admin-pwa`.
> Not a repository-wide policy. Does not modify or supersede root `AGENTS.md` / `AI_RULES.md` / `PROJECT_MEMORY.md`.
> All development and progress records for this task remain under `docs/admin-pwa/`.


Last context capture: 2026-10-23. This is a **design and repository-source snapshot**, NOT live production verification.

## Why this work exists

Owner needs a real Admin PWA accessible on iPhone, Mac and Windows **in addition to, never replacing**, the existing Telegram admin panel. It must use the locally reviewed professional Admin V10 UI/UX demo as a design starting point; strip synthetic numbers/users/notifications/actions; and connect to **actual HSK AI services and database**.

The owner also wants a reliable way for ChatGPT, Cloud agents and local tools to analyze **complete platform statistics and user feedback** to prioritize product improvement. Source code on GitHub is distinct from runtime DB. Start with restricted read-only JSON/CSV exports; evaluate an MCP gateway only after consent, scope and security are ready.

## Owner-approved user flows

1. Public destination: `https://hskai.app/admin`. Domain is owner-specified, not yet evidenced as configured for Admin PWA OAuth or WebAuthn.
2. First-time admin: Google verified OAuth → Telegram Bot one-time allowlisted admin approval → Google identity linked to canonical admin → register discoverable passkey.
3. Later visit with valid session: opens directly without login. Otherwise: **passkey-only sign-in** using Face ID / Touch ID / Windows Hello / PIN depending on device, without Google each time. Linked Google / Telegram recovery available under stringent audit.
4. Sensitive action: show explicit target/decision summary and request a fresh transaction-bound passkey verification.
5. Existing Telegram Admin Mini App and bot retain their own verified Telegram entry path.

## Verified repo inventory (at initial source inspection)

- GitHub repository: `akbarholturaev11-lang/HSK-AI-Bot`.
- Working branch: `codex/admin-pwa`; original `main` base at `e935e4315df42037d6aab4ab38b2c4e5d9bbb681`. Always re-read live HEAD and main.
- Existing Telegram frontend `app/static/admin.html`, served by `GET /admin.html` in `app/main.py`.
- Existing Telegram auth `app/services/telegram_webapp_auth.py` and `app/main.py::_admin_miniapp_user_id / _admin_auth_error`; existing admin APIs require fresh `X-Telegram-Init-Data` with `settings.ADMIN_IDS`.
- Existing `/api/admin-miniapp/*` has 44 POST routes at time of inventory, even read operations; see `PHASE_0_API_INVENTORY.md`. Some multipart requests authenticate with form `initData` and need special review, not a blanket web-cookie bypass.
- Existing Google OIDC pieces: `app/services/google_auth.py`, `app/services/native_oauth_service.py`, `app/services/identity_link_service.py`, `app/api/native_oauth.py`. These implement native-client flows/identity linking; they are NOT yet proven to support Admin PWA cookie authentication.
- No dedicated Admin PWA WebAuthn credential storage/registration/login/server assertion implementation was found during the initial repo path scan. Existing dependency `cryptography` alone is not a complete WebAuthn relying-party implementation.
- User and account authority: canonical `users.id` must be kept distinct from historical `telegram_id`; see `app/services/admin_user_target.py`.
- Stats services: `app/services/admin_miniapp_service.py`, `app/services/admin_finance_stats_service.py`, `app/services/admin_stats_service.py`, Android/Desktop/public-site analytics services. Public-site traffic measures **visits**, not unique people.
- Bot feedback: `app/db/models/bot_feedback.py` durable feedback. Release reviews: `app/db/models/release_feedback.py` responses and ratings.
- Native Android `POST /api/v3/android/bug-report` in `app/api/android_features.py` sends report to Telegram admins; at time of inspection did **not** write a durable inbox row, meaning historical bug reports may be unrecoverable from application DB.
- `app/services/admin_notify_service.py` sends Telegram admin notifications, but sending does not by itself create a durable universal inbox.
- Source-local skills: `.agents/skills/hsk-ai-ui/SKILL.md`, `.agents/skills/webapp-testing/SKILL.md`; root `AGENTS.md` additionally recommends `frontend-design` when available.

## UX decisions already settled

- Responsive app with premium restrained design; minimum clutter, no redundant headings/explanatory paragraphs.
- Statistics global `Общий` is a platform filter value, not a duplicate set of tabs. When selected platform changes, metrics and top title/icon must reflect that filter.
- Header contains compact period selector (7 days / 30 days / entire period), compact collapsed platform funnel filter and bell on the same row.
- User profile, revenue, subscriptions, one-time HSK 3.0 unlock, campaigns, settings and permissions should come from shared backend contracts.
- Notifications: universal inbox for user feedback, release feedback, Android bugs and alerts; crucial items grouped/highlighted, all filters collapsed by default, search, read/assigned/resolved and detail.
- Demo HTML V10 was produced as a downloadable file in conversation history, **not committed into GitHub in this branch**. Obtain/verify it before taking production UI bytes; do not invent a repository path.

## Do not conflate

- **Defined design** ≠ implemented code.
- **Repo code** ≠ live production state.
- **Browser WebAuthn API capability** ≠ tested Face ID on a real installed PWA.
- **Telegram notification** ≠ durable feedback history.
- **Google email match** ≠ authenticated/admin-authorized canonical account.
- **MCP tool enabled** ≠ permission to retrieve identifiable user data.
- **One click UI demo** ≠ a real, server-validated payment or account operation.

## References

- `docs/admin-pwa/IMPLEMENTATION_PLAN.md`: architecture, order and acceptance.
- `docs/admin-pwa/PHASE_0_API_INVENTORY.md`: specific read/write/danger endpoints and source gaps.
- `docs/admin-pwa/HSK_AI_ADMIN_PWA_TEMP_RULES.md`: non-negotiable project constraints.
- `docs/admin-pwa/HSK_AI_ADMIN_PWA_TEMP_FINAL_RESULT.md`: definition of done.
- `docs/admin-pwa/HSK_AI_ADMIN_PWA_TEMP_HANDOFF.md`: actual work and verification checkpoint.
