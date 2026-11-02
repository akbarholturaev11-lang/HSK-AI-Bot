# Proposal: standalone iPhone learner Course PWA

## Why

The existing learner course is a Telegram Mini App, not an independently authenticated iPhone application. Its `app/static/course-v3.html` reads `Telegram.WebApp.initData`, and current course APIs authenticate a Telegram-signed `X-Telegram-Init-Data` and resolve users by real `telegram_id`. Merely adding a web manifest or hiding Telegram chrome would leave browser login, course progression and paid access unusable or unsafe. The user requests an installable, Telegram-independent iPhone PWA with the existing course UI/functions as close to 1:1 as platform constraints permit.

This is new cross-client, identity- and billing-sensitive behavior, so `$hsk-ai-openspec-planning` is justified. This change is a **plan**, not a code or release authorization. The sole continuation navigator is [IPHONE_PWA_CONTEXT.md](../../../docs/IPHONE_PWA_CONTEXT.md); repository policies and current code remain authoritative.

## What Changes

- Plan a minimal learner iPhone Safari/Home Screen entry with suitable icons/metadata, reusing current course markup/assets. No new offline caching or service worker is required for v1.
- Plan a secure independent browser login/session with Google/Apple where configured, optional explicit Telegram account linking/handoff, canonical `users.id`, logout/revocation, CSRF and correct iOS standalone callback/return handling.
- Plan a thin browser-vs-Telegram frontend platform adapter and authenticated backend transport that shares established course, progress, scoring, grading, trial/Pro, access, subscriptions and referral services without weakening Telegram signed-initData requirements.
- Audit UI and learning parity across course tabs, HSK 2.0/3.0 tracks, lessons, tests, homework, practice, pronunciation/voice, mistakes, progress, settings, paywall and localized UZ/RU/TJ strings. Document any iOS differences and capability gating instead of promising unavailable features.
- Plan focused auth/course/billing/iPhone physical-device tests and reversible rollback; do not deploy during planning.
- Preserve important account/transactional notices and the existing course/ranking inbox as distinct from Smart study reminders; prepare a future **Smart Reminder V2 iPhone PWA channel** against its canonical policy without prematurely enabling Web Push.
- Reuse existing bot feedback and release-feedback eligibility/reward records for small centered PWA dialogs; leave Telegram chat behavior intact.
- Design **new** PWA UI in editable Figma components first; link them from the single context file rather than duplicating the Mini App screen designs.

## Capabilities

### New Capabilities

- `iphone-pwa-identity`: independent browser session, verified provider sign-in, explicit Telegram linking, lifetime/revocation and request ownership.
- `iphone-pwa-course-parity`: shared course UI and user-scoped Mini App functionality via safe browser adapters, original backend authority and Telegram preservation.
- `iphone-pwa-install-lifecycle`: iOS Home Screen learner entry, safe session/navigation recovery and media capability checks; no v1 offline cache, Service Worker or Web Push requirement.
- `iphone-pwa-payments-entitlements`: canonical Pro/trial/payment/referral/receipt flows for browser users, without unauthorized commercial-policy changes.
- `iphone-pwa-messages-feedback`: service notices/in-app inbox, future Smart Reminder adapter seam and compact original bot/release feedback flows; design-first review gate.

### Modified Capabilities

None proposed yet: the existing `openspec/specs/` inventory is admin-focused. Learner PWA requirements are isolated; no unrelated admin spec is redefined.

## Impact

- Source baseline: `main@f791613c4377ffec2018cce3764cf81e80a6a765` (2026-11-02). Revalidate newer HEAD before implementation.
- Authoritative sources: `AGENTS.md`, `AI_RULES.md`, `PROJECT_MEMORY.md`, `docs/UNIVERSAL_NATIVE_ACCOUNTS.md`, `OAUTH_SETUP.md`, `localization/README.md`, `openspec/config.yaml`, `.agents/skills/hsk-ai-openspec-planning/SKILL.md`, `.agents/skills/hsk-ai-ui/SKILL.md`.
- Current paths: `app/static/course-v3.html` plus `course_v3_*.html` and `app/static/course_v3_data/`; `app/main.py` and `app/api/miniapp_{entitlements,practice,preferences}.py`; `app/api/native_oauth.py`, existing identity/user/session repositories; course/payment/access services and focused tests.
- Notification/feedback boundaries: `docs/smart-reminders/SMART_REMINDER_MASTER_PLAN.md` D10/P5; `app/services/notification_delivery_service.py` account notices; `app/services/course_notification_service.py` learner feed; `app/services/bot_feedback_service.py` and `app/services/release_feedback_service.py` campaign/reward state.
- Figma source: [iPhone PWA notifications and feedback](https://www.figma.com/design/89fCM5GdjfBqcx0B9aQHOI), draft mockups requiring review before implementation.
- Verified boundary: `app/api/native_oauth.py` OAuth start supports `android|macos|windows`, not browser PWA. Mini App identity-link support is **not** browser authentication. `docs/UNIVERSAL_NATIVE_ACCOUNTS.md` states learner PWA is not yet implemented.
- Consumers: Telegram bot/Mini App, Android Direct/Play, Desktop, existing web/API clients must remain compatible; shared data stays keyed by canonical `users.id`.
- Risks: fabricated Telegram IDs, forgery of browser actor/session, CSRF and OAuth callback/session fixation, cross-account state leaks, exposure of private or graded lesson responses, payment/receipt mistakes, duplicated sign-up benefits, broken Telegram SDK or lesson flow, Safari/Home Screen session isolation, unsupported media/notification capability.
- Rollback: disable or withdraw only learner PWA entry/browser-auth adapters, expire/revoke PWA sessions, preserve existing Telegram/native routes and user-linked account/payment/progress records. No destructive migration or production trial during planning.
- Out of scope: runtime code, production database, live OAuth secrets, paid external API, existing Admin PWA, a rewritten UI framework, changes to course content/scoring/business policy, offline downloads, new Web Push/notifications, new analytics pipeline, app-store native iOS release, main merge or deployment.

## Acceptance for this planning change

OpenSpec proposal/specs/design/tasks exist as CLI-instructed files and `openspec validate iphone-course-pwa` passes in GitHub Actions; the context file links the check and presents unverified external/device constraints honestly. This validates **planning structure only**. Actual browser/security tests and a real iPhone remain future implementation gates.
