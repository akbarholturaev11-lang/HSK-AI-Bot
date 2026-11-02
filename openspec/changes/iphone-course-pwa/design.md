# Design: independent iPhone Course PWA without Telegram regression

## Context and verified source boundary

The user requests an iPhone standalone learner PWA that replicates the Telegram Course Mini App, not a distinct course product or a visual redesign. The planning baseline is `main@f791613c4377ffec2018cce3764cf81e80a6a765` (2026-11-02); refresh HEAD before any runtime work.

- `app/main.py` serves `/course-v3(.html)`, `/course_v3_{page}.html`, related assets and many course endpoints, and mounts specialized routers.
- `app/static/course-v3.html` includes Telegram SDK and sends `X-Telegram-Init-Data`; existing course frontend assumes an initData-backed user.
- `app/api/miniapp_entitlements.py`, `app/api/miniapp_practice.py` validate Telegram-signed initData and resolve `user.telegram_id`; they cannot be safely opened by a mere PWA flag.
- `app/api/native_oauth.py` starts OAuth for Android/macOS/Windows, and its Mini App identity-link flow is not a browser sign-in session.
- `docs/UNIVERSAL_NATIVE_ACCOUNTS.md` makes canonical `users.id`, verified identity linking and no fake Telegram transport IDs mandatory, and explicitly marks iPhone Course PWA unimplemented.
- `app/static/admin-pwa/` includes an independent administrative web app, but its privileged security/session model is not a learner login shortcut.
- Localized learner content/catalogs and authoritative server grading/access exist; preserve their source/consumer boundaries.

Read and apply `AGENTS.md`, `AI_RULES.md`, `PROJECT_MEMORY.md`, `OAUTH_SETUP.md`, `localization/README.md`, `.agents/skills/hsk-ai-ui/SKILL.md` and the canonical [context](../../../docs/IPHONE_PWA_CONTEXT.md) on implementation entry. No actual provider secrets, deployment origin, installed browser version, payment provider callback, iPhone behavior, migration head or test result has been verified by this plan.

## Goals / non-goals

**Goals:** one shared real learner account; independent login and installable iPhone entry; common course UI/business logic, familiar navigation, progress/Pro parity, safe media and lifecycle behavior; no regressions for Telegram/native clients; clear stage gates and rollback.

**Non-goals:** separate course database, inventing a Telegram ID, replacing native auth with browser tokens, changing Pro/prices/referral economics, rewriting lessons, admin PWA changes, blanket offline/full-web-push promises, guaranteed native iOS API parity, runtime code/deployment in this planning task.

## Decisions and architecture

### D1 — One shared UI, two explicit platform transports

**Recommended:** provide a thin platform adapter around actual Mini App host-specific features, not a fork of 9k-line course markup. The adapter separates:
- `telegram`: verified initData, real `Telegram.WebApp` navigation, open/close and Telegram-only actions.
- `browser-pwa`: secure cookie-backed session, regular browser navigation, standalone safe-area/lifecycle and browser API availability.
- Shared course presentation, localization, state machine and access UX remain the single implementation as much as regression testing supports.

Before choosing exact files, inventory all URLs and functions used by `course-v3.html`, `course_v3_*.html`, `lesson_gate*.js`, audio, settings, paywall, referrals, achievements and downstream course/navigation. Enumerate SDK calls, API request headers/body actor assumptions, localStorage/sessionStorage keys, origin/return URL and asset cache scope. Avoid broad refactor; extract the smallest stable adapters in audited slices.

**Rejected:** serving the same HTML with `INIT_DATA=""` and permissive backend fallback; rewriting the entire Mini App in React/Swift; removing Telegram SDK from its original entry.

### D2 — Canonical learner account and browser-specific auth boundary

**Recommended:** add a narrowly scoped browser session/auth transport that resolves an authorized actor to `users.id`, sharing the existing identity and account services. Evaluate a server-managed cookie with Secure/HttpOnly, reviewed SameSite/Domain/Path, CSRF protection for writes, strict Origin/Referer where applicable, expiry and revocation, rate limits, security headers and bounded login attempts. OIDC state/nonce/PKCE and verified provider subject must be bound to the login flow and intended browser context. Never accept user_id from client body.

Use currently configured Google/Apple providers only after validating iPhone browser-origin and callback handling. Implement a browser-only learner without `telegram_id`; optional Telegram linking requires proof of both accounts and explicit informed action. No same-email merge. Where safe login to an existing Telegram-only account requires a Telegram-confirmed link, state that as a supported explicit handoff rather than silently creating a new identity or copying old entitlements. PWA installed-container storage isolation must be tested; browser callback alone may not restore Home Screen state.

**Rejected:** putting native refresh tokens in localStorage, using a fake Telegram initData, trusting arbitrary OAuth redirect URLs, reusing Admin PWA cookies/passkeys without a new authorization contract.

**Unresolved implementation decision:** concrete browser OIDC callback/session and optional Telegram handshake design must be audited against actual provider configuration/redirects and existing linking tokens before exact endpoint/schema is fixed. Proposed `/api/pwa/*` namespace is illustrative, not an existing route or approval to create it.

### D3 — Transport adapters call canonical course services

Retain existing signed Telegram endpoints and existing user linkage. For PWA-specific routes, authenticate browser actor once and call the same service-level lesson, practice, track, results, assessment, user-access and subscription policies. Review `app/main.py` direct endpoints in addition to `app/api/miniapp_*.py`; many use Telegram ID directly, not only the router modules. Factor shared service entrypoints only when backed by focused parity tests.

Map endpoint / method / actor / client dependency / server service / access/proof guard / consumer / PWA disposition for every important path. Preserve result/grade source hashes, lesson start grant, completion proof, Pro gating, trial, AI budget, and progress `users.id`. Legacy Telegram requests with PWA cookies and no signed initData stay unauthorized. Cross-user access must be denied by the server, not JS.

Session-local client storage and cache must be namespaced/cleared on user switch. Existing private course JSON and exam assets need exposure review; public static pre-cache cannot become a backdoor into paid answer keys.

### D4 — Billing and referral parity without commercial-policy drift

Reuse current `app/services/entitlements/`, `subscription_miniapp_service.py`, payment review/receipt services and canonical payment owner. Audit the entire paywall/provider/receipt UI flow for hard-coded Telegram SDK, chat ID, QR and success return assumptions. Make browser status refresh source-of-truth server-confirmed, including pending receipt preview vs approved subscription. No frontend-set Pro, no duplicate one-time trial, referral or view bonus from linking. Preserve existing subscription/payment variants and only adapt navigation, not economics or access policy. If an external provider return cannot safely restore installed PWA context, reauthorize and reconcile payment with the canonical user.

### D5 — Constrained iPhone install, caching and media

A dedicated HTTPS learner start URL, valid manifest, suitable iOS icons and standalone display metadata are required. Preserve `viewport-fit=cover` and safe-area inset handling. A dedicated narrowly scoped service worker may cache only vetted versioned non-sensitive shell/assets; never store cookies, API secrets, graded answers, personal course responses, billing/progress state in public cross-account CacheStorage. Test reload/soft-update and offline failure behavior; do not promise full offline lessons.

iOS needs two matrices: normal Safari and installed standalone. Check install, first launch, account login redirect round-trip, cold launch, foreground/resume, keyboard focus/scroll, voice TTS/autoplay, microphone permissions, upload/camera, payment return and updated shell. Push support and permissions are optional and evidence-gated; do not route Telegram notifications without a genuine Telegram account/consent. Unknown iOS capability becomes a documented localized fallback, not false UI success.

### D6 — Localization, telemetry and privacy

Follow `localization/README.md` source-of-truth for UZ/RU/TJ strings and generator/check commands. No per-string API and no competing inline dictionary. AI/lesson text, source SHA and grading semantics are separate. Ensure analytics marks `pwa` as a real transport/platform without double counting the same user's lesson/subscription events; no raw OAuth tokens, initData or sensitive receipt payloads in telemetry. Preserve account deletion, user revocation and privacy rules. Avoid reusing Admin PWA service-worker/cache scope.

## Implementation slices / dependency ordering

1. **Inventory + baseline:** refresh HEAD/actual migration head, endpoint/UI parity catalog and contract tests; classify host-specific behavior and protected static assets. Record no-code snapshot and risks.
2. **Security foundation:** design/implement browser session + provider callback, session rotation/logout/CSRF, verified canonical user, explicit Telegram link; verify cross-account and old-client isolation before accepting course writes.
3. **UI and API transport:** introduce minimal shared host adapter and browser-authenticated course endpoints; port screen groups incrementally and run focused result/graded/entitlement regressions. Telegram must continue passing.
4. **Billing and history:** browser paywall/receipt/return, trial/referral/linking dedupe, canonical metrics and deletion; test realistic pending/approved/refused cases.
5. **Install and iOS media:** manifest/icons/SW only after private-cache audit; real Safari/Home Screen login callback, deep link, sound/microphone and offline error verification.
6. **Localize, observability and rollout:** canonical catalog build/check; iOS manual device acceptance and controlled staged rollout with feature cutoff/rollback.

## Risk-based test matrix (future work only)

| Gate | Necessary evidence |
| --- | --- |
| Auth/unit/API | Verified Google/Apple subject; OAuth state/nonce/replay; cookies + CSRF; expiry/revocation/logout; forged initData blocked; blocked/deleting account; cross-user denial |
| Existing clients | Telegram Mini App initData, return-to-bot/deep link; Android Direct/Play and Desktop native login session compatibility |
| Course | `tests/test_course_miniapp_lesson_flow.py`, `test_course_miniapp_practice.py`, `test_course_miniapp_profile_preferences.py`, `test_course_v3_mobile_practice_contract.py`, lesson result/grade/proof/XP, both track families and locked lesson |
| Billing | Paid/free/trial, pending/approved/rejected receipts, old payment and refund idempotency, referral duplication prevention; `tests/test_desktop_subscription_api.py` as a cross-platform guard when applicable |
| UI/localization | `hsk-ai-ui` review, targeted Playwright flows, catalog build `--write` + `--check`, UZ/RU/TJ, Voice/mic disabled/allowed |
| Privacy/offline | No user/account state crossing session or cache, no paid answer pre-cache, logout clear, safe update, recovery after offline |
| Physical acceptance | Supported iPhone(s): Safari and Home Screen install, Apple/Google login return, current lesson recovery, mic/audio, paywall return, cold start/background, expiration, safe-area and keyboard |
| Rollback | PWA disabled/removed and its sessions revoked; original Mini App/natives/payments/progress intact, no schema rollback destroying accounts |

The user will approve implementation after this plan; CLI validation does **not** satisfy tests, staging/provider verification, real iPhone QA or permission to merge/deploy.

## Rollback and rollout boundaries

Ship in independent isolated slices, leaving existing Telegram/native routes and account tables unmodified where feasible. Prefer a separate learner-PWA enablement guard and safe session invalidation, not a global switch that disrupts Telegram. Fail closed for unsupported auth/capability. Never delete identities, subscription or progress on rollback. Confirm real provider callback domains, CDN/service worker scope and production flags only during authorized implementation and staging.

## Explicit unknowns (do not mark as facts)

Real PWA origin; provider credentials/redirect allowlists; exact iOS Safari/Home Screen engine behavior on actual target devices; current production Alembic head; existing Android/Desktop/Mini App installed-client compatibility; provider payment return path for a browser-only account; online/offline course security review; availability of opted-in Web Push. These are follow-up investigation gates, not reasons to invent behavior or claim parity.
