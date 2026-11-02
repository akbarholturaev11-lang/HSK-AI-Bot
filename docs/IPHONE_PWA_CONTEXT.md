# iPhone Course PWA — canonical planning context

> State: **PLANNING ONLY**. Implementation, device QA, rollout, merge, and deployment are not authorized by this file.
> Working branch: `feat/iphone-course-pwa-planning-20261102`.
> Audited `main` starting commit: `f791613c4377ffec2018cce3764cf81e80a6a765` (2026-11-02 UTC).
> OpenSpec proposal: `openspec/changes/iphone-course-pwa/`. This context is the **single continuation navigator**; the OpenSpec files own proposed requirements/design/tasks and must not become a second progress ledger.

## Owner's goal (locked scope)
Produce a standalone, installable iPhone Home Screen **learner Course PWA** with Telegram Mini App interface and learner functionality as close to **1:1** as applicable, without requiring Telegram to launch. Existing Mini App must continue to work unchanged. Favor reuse of the existing frontend/shared FastAPI/course, account and billing services over a parallel implementation. Initial target is iPhone Safari/Home Screen; Android/Desktop and Admin PWA redesign are out of scope.

## Verified current source
- `app/static/course-v3.html` is an existing Telegram Mini App entry: loads `/assets/telegram-web-app.js`, obtains `Telegram.WebApp.initData`, and sends `X-Telegram-Init-Data` to course/practice/preferences/payment-related APIs. Browser access without a verified Telegram identity is **not** equivalent to a logged-in app.
- `app/api/miniapp_entitlements.py` and `app/api/miniapp_practice.py` authenticate Telegram-signed initData and look up `users.telegram_id`; they are NOT standalone browser-auth endpoints.
- `app/api/native_oauth.py` permits `android|macos|windows` for native OAuth start; `miniapp` appears in identity linking but is not a browser login session. Native flow does not return browser cookies.
- `docs/UNIVERSAL_NATIVE_ACCOUNTS.md` expressly marks the learner iPhone Course PWA **not implemented** and prescribes shared `users.id`, independent safe browser login/session and Telegram handoff.
- Existing standalone `app/static/admin-pwa/` is for **administrators**, not a learner PWA. Do not reuse privileged admin authentication for learners.
- `app/main.py` composes existing course, account, payment and native transport routers. `app/static/course_v3_data/` supplies existing course assets/localizations.
- OpenSpec skill `.agents/skills/hsk-ai-openspec-planning/SKILL.md`; UI skill `.agents/skills/hsk-ai-ui/SKILL.md`; repository constraints `AGENTS.md`, `AI_RULES.md`, `PROJECT_MEMORY.md`, `openspec/config.yaml`, `localization/README.md`.

## Non-negotiable invariants
1. Server canonical `users.id` owns progress, payments, access, XP, history and identities. `users.telegram_id` remains a **real** Telegram ID or NULL; never fake it for a browser account.
2. Authenticate via verified provider identity and explicitly authorized account linking. No automatic merge based on matching email/name; never duplicate referral, trial or purchase benefits from linking.
3. Browser must have a purpose-built session (secure, HttpOnly, appropriate SameSite cookie), CSRF and origin controls, expiration/revocation, replay/rate-limiting and explicit logout. Do not place Android/Desktop native refresh tokens in localStorage or bypass Telegram initData verification.
4. Existing Telegram routes continue using verified initData. Add separate browser transport/adapter backed by canonical services or an audited shared auth context. Preserve canonical result, answer, access, pending receipt, subscription, lesson-source and language invariants.
5. PWA UI must account for iOS standalone display, safe-area insets, install state, browser vs Home Screen session differences, camera/microphone/voice permissions, app lifecycle and navigation recovery. Push and offline are **capabilities to verify**, not promises; do not cache private answers/auth responses publicly.
6. All new fixed UI strings follow `localization/README.md` UZ/RU/TJ canonical catalog, build and checks. Use `hsk-ai-ui`; preserve current Mini App UI, lessons, quizzes, homework, language, errors, subscriptions and the Telegram SDK in the Telegram client.
7. Billing/entitlements remain server-controlled; pending-receipt preview is not paid Pro, and payment paths must be reviewed for browser-specific return/receipt handling and platform constraints. Never make unreviewed commercial-policy changes.
8. No production credentials, user data, DB reset, paid external APIs or live accounts in planning/CI. No runtime implementation, `main` push or deploy in this planning task.

## Baseline audit checkpoints / likely implementation boundaries
- Entrypoint and shared UI: `app/static/course-v3.html`, child `course_v3_*.html`, JS/CSS/static assets, FastAPI static routes in `app/main.py`.
- Identity: `app/api/native_oauth.py`, `app/api/desktop_auth.py`, `app/services/native_oauth_service.py`, `app/services/identity_link_service.py`, `app/services/desktop_auth_service.py`, `app/db/models/user.py`, `app/db/models/user_identity.py`; review native session model and Alembic state.
- Learner APIs: `app/api/miniapp_entitlements.py`, `miniapp_practice.py`, `miniapp_preferences.py`, `app/api/course_tracks.py`, `app/services/course_miniapp_*`, subscriptions and payment review; enumerate EVERY browser-facing route before changing shared frontend.
- QA: existing relevant `tests/test_*native*auth*.py`, `test_*miniapp*.py`, `test_*course*.py`, `test_*payment*.py`, and `tests/e2e/`; select actual filenames after fresh repo scan.
- Candidate architecture (decision pending code audit): reuse the actual learner UI and separate Telegram vs authenticated-browser platform adapters. Keep existing transport routes secure and share service-level business logic.
- iOS matrix: Safari vs Home Screen; fresh install, reload, tab background/foreground, session expiry, Google/Apple identity return, optional Telegram linkage, microphone/audio, error/offline/recovery, safe areas/notches, keyboard, payment/receipt return, device logout and push eligibility.

## Planning stages (proposed, not completed)
1. Baseline feature/route/security inventory and iOS constraints.
2. Browser identity/session, explicit account-linking and revocation design.
3. Common Mini App/PWA frontend platform adapter and route parity.
4. Canonical course/progress/paywall/entitlement/payment/referral API parity.
5. Web manifest, icons, service worker/cache privacy, iOS install + voice/media behavior.
6. Localization, telemetry, privacy, migration/rollout/rollback.
7. Focused backend security, browser E2E, iPhone physical QA and release gates.

## Current state and next action

- [x] Owner's goal and Telegram-independent iPhone learner-PWA scope locked.
- [x] Existing Mini App/backend, shared identity, UI and OpenSpec constraints source-audited from baseline `main`.
- [x] **Official OpenSpec CLI executed on GitHub Actions** and generated the `iphone-course-pwa` scaffold.
- [x] Four new capability specifications, plus proposal, design and stage-by-stage tasks written on the isolated planning branch.
- [x] `openspec validate iphone-course-pwa` completed successfully in the planning GitHub Actions workflow, using the committed artifacts.
- [ ] Owner review of design/plan; future implementation deliberately not started.
- [ ] Real OAuth/provider callback and physical iPhone tests remain unverified, as does deployment.

**CLI validation evidence:** [GitHub Actions run #41446061294](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/41446061294), outcome **success**, validated source commit `28df29f5bb14c17cf80e0f604346b006ab028508` (2026-11-02 UTC). That run executed `openspec context --json`, `openspec status --change iphone-course-pwa --json`, the official CLI artifact instructions and `openspec validate iphone-course-pwa`. A short-lived downloadable evidence artifact is attached to the run. **CLI success proves only spec structure, not backend tests, iPhone/browser QA or production readiness.**

**Plan entry points:** [proposal](../openspec/changes/iphone-course-pwa/proposal.md), [design](../openspec/changes/iphone-course-pwa/design.md), [tasks](../openspec/changes/iphone-course-pwa/tasks.md), and [capability specs](../openspec/changes/iphone-course-pwa/specs/). This context is the only continuation navigator; task checkboxes are for future code/device work, not planning.

**Next work when owner approves implementation:** refresh `origin/main`; run tasks P0 source/route inventory first; then P1 secure browser session and linking. Do not write runtime code, merge or deploy merely because this plan was validated.

If a new `main` HEAD appears, reconcile the affected source/contracts before implementation instead of assuming this snapshot is current.
