# Tasks — iPhone learner Course PWA

All boxes below denote **future implementation and verified acceptance**, not completion of this OpenSpec planning task. Do not check any item merely because a file exists, GitHub Actions passed, or a mock ran. The single continuation context is [IPHONE_PWA_CONTEXT.md](../../../docs/IPHONE_PWA_CONTEXT.md). Refresh live `origin/main` and actual source/tests before each slice. Work on an isolated implementation branch, keep original Telegram Mini App usable, and do not merge/deploy without the repository's applicable security, Git and device QA gates.

## 0. P0 — architecture and route inventory (no runtime changes)

- [ ] 0.1 Refresh `origin/main`, existing feature handoffs, production/staging **documented** schema/Alembic head; inspect `AGENTS.md`, `AI_RULES.md`, `PROJECT_MEMORY.md`, `localization/README.md`, `OAUTH_SETUP.md`. Report changed assumptions and actual test baselines (no production credentials).
- [ ] 0.2 Enumerate `app/static/course-v3.html`, `course_v3_*.html`, `course_v3_data/*`, direct `app/main.py` endpoints, `app/api/miniapp_*.py`, JavaScript fetch calls and Telegram SDK APIs. Record each path's auth, canonical owner, access/grade proof, consumer and PWA parity disposition.
- [ ] 0.3 Audit current Google/Apple first-signin, identity linking, session, revocation, deletion, trial/referral, paywall/receipt, public lesson data and service worker exposures. Identify necessary new backend contracts and migration need, if any.
- [ ] 0.4 Produce a signed-off source-backed parity grid: all course tabs/screens, HSK 2.0/3.0, lessons, quiz/homework, progress, AI/voice/practice, history/mistakes, profile, paywall, locale, notifications and deep links. Distinguish compatible parity, iOS capability-gated and non-goal features.
- [ ] 0.5 Establish focused baseline unit/API/browser tests on a safe isolated environment, preserving Telegram/native behaviors; record commands and baseline failures (no claimed acceptance without evidence).

## 1. P1 — browser authentication, canonical owner and logout

- [ ] 1.1 Build reviewed learner-only browser auth/session service and persistence only if justified by the existing session model; define bounded cookie lifetime, Secure/HttpOnly/SameSite/Path, CSRF/origin/referer, session rotation and revocation. Preserve `users.id` owner and nullable real `telegram_id`.
- [ ] 1.2 Integrate verified configured Google/Apple browser OAuth entry/callback with bound state, nonce/PKCE where applicable, exact redirect allowlist, rate limiting and provider unavailability UX. Never copy Android/Desktop token storage or use Admin PWA auth.
- [ ] 1.3 Provide optional Telegram account linking via verified explicit consent/handoff with ownership conflict refusal. Test existing Telegram-only account, browser-only account, duplicate email/name and already-linked identity; never silently merge or re-credit rewards.
- [ ] 1.4 Create browser `/me`/session/bootstrap/logout/refresh (actual names after route audit), with blocked/deleting-user and revoked session denial. Test cross-user reads/mutations, CSRF, session fixation/replay, stale cookie, multiple devices and account switching.
- [ ] 1.5 Run original Telegram initData/Android/Desktop auth regressions; prove browser session is **not** accepted as Telegram initData and no fake Telegram ID is generated.

## 2. P2 — one frontend UI, channel-specific adapters

- [ ] 2.1 Add a minimal host transport adapter for Telegram vs standalone browser in/around `app/static/course-v3.html` and related pages; keep the existing Telegram WebApp SDK path intact and do not fork the UI/lesson engine.
- [ ] 2.2 Add a dedicated learner PWA entry/auth shell and constrained course route, handling normal Safari and installed standalone navigation, deep link, error and sign-in-return states. Exclude Admin PWA and public marketing scope.
- [ ] 2.3 Convert course API calls by audited route group to verified actor-backed browser endpoints/shared service calls, preserving Telegram signed-initData legacy routes. Implement by small groups: bootstrap/track/profile; lesson/content/start/result; practice/quiz/homework; history/mistakes/XP/AI.
- [ ] 2.4 Make client-local draft/route/level/session state account-aware; clear on logout/switch and reject private stale responses. Test refresh, bfcache, deep link, expired browser session and no data from a previously signed-in user.
- [ ] 2.5 Run target UI + course regressions, including `tests/test_course_miniapp_lesson_flow.py`, `tests/test_course_miniapp_practice.py`, `tests/test_course_miniapp_profile_preferences.py`, `tests/test_course_v3_mobile_practice_contract.py`, and live route/answer/score proof tests where actual source supports them.

## 3. P3 — access, Pro, payments, trials and referrals

- [ ] 3.1 Connect PWA learner actor to current server `entitlements`, access, course track and AI budget services; verify free/trial/paid/unlocked/inaccessible combinations and no public grade/answer exposure.
- [ ] 3.2 Audit `subscription_miniapp_service.py`, QR/receipt/paywall UI and payment services for Telegram-only dependencies. Add only bounded browser checkout and receipt/return adapters with canonical owner and status refresh.
- [ ] 3.3 Test pending receipt vs approved paid access, rejected/review/refund, duplicate receipt, URL return spoof, unexpected logout/reauth and differing Safari/Home Screen containers. Never treat a client callback as payment verification.
- [ ] 3.4 Prove existing-account linking and PWA signup cannot duplicate trial/referral/feedback/HSK 3.0 unlock/XP bonus; actual Telegram messaging only when a genuine linked Telegram ID and consent exist.
- [ ] 3.5 Run targeted existing billing/referral/progress/privacy tests and document any required backend schema migration with upgrade/downgrade safeguards.

## 4. P4 — install, iOS lifecycle, audio and privacy-safe caching

- [ ] 4.1 Add HTTPS learner PWA manifest, valid start/scope, properly sized icons, Apple-specific metadata where needed, install help and full iPhone safe-area/viewport/keyboard layout, preserving `hsk-ai-ui` visual rules.
- [ ] 4.2 Build narrowly scoped, versioned service worker only after auditing public/static paid course assets, auth and user-response caching. Never public-cache protected lesson keys, session/receipt/grade/progress or other private responses. Verify safe update/unregister/recovery.
- [ ] 4.3 Handle Safari vs Home Screen independent storage and redirect return; test cold launch, reinstall, background/foreground, account logout/switch, expiry, network loss and controlled restoration without cross-account leaks.
- [ ] 4.4 Test microphone capture, TTS/voice playback, autoplay policy, file/camera upload, external provider/payment navigation and accessible non-voice fallbacks on real iOS devices. Promise push only if supported and deliberately permissioned.
- [ ] 4.5 Run security checks for SW scope, cache headers, CSP, OAuth callback and XSS/CSRF/CORS as applicable; review static lesson access before any offline catalog expansion.

## 5. P5 — localization, observability, privacy and rollout controls

- [ ] 5.1 Reuse canonical UZ/RU/TJ UI keys per `localization/README.md`; run `python3 scripts/i18n_build_all_catalogs.py --write` and `--check`, commit canonical sources and generated consumer outputs together.
- [ ] 5.2 Add minimally necessary real `pwa` source/session/funnel analytics with canonical account dedupe; never log OAuth tokens, initData, receipts or secrets. Ensure existing provider/platform metrics are not silently reclassified.
- [ ] 5.3 Preserve account deletion, identity unlink, sign-out and legal/privacy notice semantics across all browser sessions and existing clients; test data boundaries and restoration policy.
- [ ] 5.4 Implement an isolated learner-PWA release/enablement switch and safe rollback procedure (revoke PWA sessions; leave Telegram/native and canonical payments/progress intact); run disable/re-enable smoke checks.

## 6. P6 — QA acceptance and release review (separate from OpenSpec validation)

- [ ] 6.1 Automated auth/security and payment regression suite passes on the exact implementation branch, including error/negative cases and the original Telegram/native clients; record commands, commit and unaddressed failures.
- [ ] 6.2 Browser E2E proves screen/route/lesson/quiz/homework/paywall/locale parity and no console/API errors, as well as logout, stale state and failed network recovery; include representative HSK 2.0/3.0 lessons.
- [ ] 6.3 Real iPhone Safari + installed Home Screen QA passes fresh install, Google/Apple return, optional Telegram explicit link, navigation/safe areas, background/resume, session expire, lesson result, voice/microphone denial and payment return. Record device/iOS versions, screenshots/steps and any unsupported behavior.
- [ ] 6.4 Reconcile required configuration, TLS/domain/redirect settings, database migration and change isolation; approve only a staged rollout with working disable/rollback, not automatic full production promotion.
- [ ] 6.5 After user implementation/release approval, follow `AGENTS.md` Git/test/main policy. Recheck remote `main` and intended commit. Never equate this checklist, OpenSpec validation or PR creation to production success.

## Planning-only completion gate (current task)

The **planning task**, not the implementation tasks above, is complete when:
1. `openspec status --change iphone-course-pwa --json` reports all four artifacts present.
2. `openspec validate iphone-course-pwa` succeeds on the repository's actual GitHub Actions runner.
3. The official CI run URL, branch HEAD and any limitations are noted in the canonical `docs/IPHONE_PWA_CONTEXT.md`.
4. The user receives links to proposed OpenSpec files and the check outcome. **No runtime code changes, main merge, live production verification or iPhone device tests are claimed.**
