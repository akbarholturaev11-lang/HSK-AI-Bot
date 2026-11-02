# iPhone Course PWA — single continuation context

**Status:** OpenSpec planning only; no runtime code, production change, merge or deploy.
**Branch/PR:** `feat/iphone-course-pwa-planning-20261102`, draft PR #256.
**Verified source baseline:** `main@f791613c4377ffec2018cce3764cf81e80a6a765` (2026-11-02); re-read current `main` before implementation.
**Plan authority:** `openspec/changes/iphone-course-pwa/` — proposal, four scoped capability specs, design, and **one tasks checklist**. This file only navigates; do not duplicate the checklist.
**Validation:** official `openspec validate iphone-course-pwa` passed on [Actions run #41446061294](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/41446061294) for the original plan. **A new run is required for later simplified commits.** Planning validation is not runtime/iPhone testing.

## Exact product goal

Launch the **same HSK AI Telegram learner Mini App** independently as a website that can be added to an iPhone Home Screen. Keep as close to 1:1 in UI, lessons, tests, homework, progress, practice/voice, account/profile and Pro/paywall as iOS actually supports. Telegram Mini App must not regress.

**No separate frontend rewrite, course engine, user database, billing system, Admin PWA or new design framework. No v1 Web Push, full offline cache, analytics pipeline, new reminders or Service Worker unless a specific new requirement is approved.**

## Actual current integration boundary

- `app/static/course-v3.html` plus `app/static/course_v3_*.html`/assets: existing learner UI and Telegram SDK.
- `app/static/course-v3.html` sends signed `X-Telegram-Init-Data` to learner APIs, including `app/main.py` and `app/api/miniapp_*.py`; independent browser has no such verified Telegram launch data.
- `app/api/native_oauth.py` and `app/services/{native_oauth_service,identity_link_service,desktop_auth_service}.py` already provide identity primitives but no general PWA browser cookie sign-in. `docs/UNIVERSAL_NATIVE_ACCOUNTS.md` confirms PWA unimplemented.
- `users.id` owns original Pro, payments, XP, progress, history and identities; `users.telegram_id` must remain a **real** Telegram ID or NULL. Use the existing verified provider/explicit linking contract, never silently merge by email.
- Reuse existing course/progress/grade/entitlement/payment/referral services. Browser session must securely establish the canonical actor; legacy Telegram endpoints must keep verifying initData.
- Localization follows `localization/README.md` for UZ/RU/TJ. Also obey `AGENTS.md`, `AI_RULES.md`, `PROJECT_MEMORY.md`, `OAUTH_SETUP.md`, and `.agents/skills/{hsk-ai-openspec-planning,hsk-ai-ui}/SKILL.md`.

## Minimal four-stage plan

1. **P0** — trace actual Mini App API/SDK dependencies; review available auth/account services and risks, no speculative architecture.
2. **P1** — minimal secure browser login/session + explicit account linking if necessary; no new auth database if existing model suffices.
3. **P2** — tiny Telegram/browser adapter, reuse identical learner UI and server services; preserve all verified course/Pro/payment flows.
4. **P3** — iPhone Home Screen entry/icon, real Safari and installed device QA, focused regressions and reversible launch.

See [tasks](../openspec/changes/iphone-course-pwa/tasks.md) for the **only** detailed phase checklist and [design](../openspec/changes/iphone-course-pwa/design.md) for constraints.

## Hard acceptance constraints

Secure/HttpOnly browser session, CSRF/expiry/logout/revocation; Google/Apple verification where configured; no fake Telegram ID, no auto-merge or duplicate referral/trial; no private/grade/payment cache leakage; original Telegram/native clients and lesson grading intact. Confirm original learner's Pro/progress after explicit linking. Pending receipt != paid Pro. iPhone Safari/Home Screen, mic/audio, sign-in return and payment return need real-device evidence.

**Execution status:** plan drafted, compacted for minimal scope. Implementation **not started**. Current main, migration head, provider callbacks, actual iPhone behavior and production configuration remain to be verified in P0–P3.
