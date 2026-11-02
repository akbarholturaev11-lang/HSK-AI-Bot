# iPhone Course PWA — single continuation context

**Status:** OpenSpec planning only; no runtime code, production change, merge or deploy.
**Branch/PR:** `feat/iphone-course-pwa-planning-20261102`, draft PR #256.
**Verified source baseline:** `main@f791613c4377ffec2018cce3764cf81e80a6a765` (2026-11-02); re-read current `main` before implementation.
**Plan authority:** `openspec/changes/iphone-course-pwa/` — proposal, five scoped capability specs, design, and **one tasks checklist**. This file only navigates; do not duplicate the checklist.
**Validation:** the updated plan including Smart Reminder V2, essential notices, Figma and feedback **passed** official `openspec validate iphone-course-pwa` on [Actions run #41449083222](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/41449083222), source commit `0d8b200c2f094bae060895dc1e856cb9cec20d67` (2026-11-02). The temporary validation workflow was then removed; only the repository's existing OpenSpec planning workflow remains. This is **planning schema validation only**, not backend tests, real iPhone QA, enabled push or a production release.

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

## Notifications and feedback integration — source-backed

The **current** Smart Reminder authority is `docs/smart-reminders/SMART_REMINDER_MASTER_PLAN.md`, especially D01/D03/D05/D06/D07/D10/D14 and P5. It expressly plans learner iPhone PWA Web Push as **V2**, after Telegram/Android. Keep one canonical `users.id` account, current Smart preferences, real OS/channel consent, server-selected one study job/account/local day, verified destination and conservative unknown-delivery handling. **PWA v1 has no Web Push, no PWA subscription and no second scheduler.** Prepare the interface/route/permission states now; **later V2** will actually require an iPhone Home Screen Web Push service worker, real user-gesture permission, owner-bound subscription, backend delivery adapter, revocation, selected job and tests. The existence of a manifest or Figma design alone does not make push operational.

Preserve important HSK AI messages separately:
- `app/services/notification_delivery_service.py` controls existing subscription/limit/account notices with Android acknowledgements and Telegram fallback. Do NOT route them through the Smart study 1/day limit or change delivery by introducing PWA.
- `app/services/course_notification_service.py` owns existing course/rating/motivation feed items and safe targets. PWA should show verified account-scoped available records. Not every transaction notice is proven to exist in this feed; P0 audits gaps, while canonical subscription/payment state remains available.
- `app/services/bot_feedback_service.py` owns normal bot feedback prompt limits and free-user one-time reward; `app/services/release_feedback_service.py` owns distinct 1–5 release campaigns. Preserve Telegram chat flow. In PWA, show **only eligible existing** prompts as compact centered dismissible dialogs with shared canonical response/dedupe/bonus rules; no second scheduler, forced new prompt or duplicate reward. For Telegram-less users, review current Telegram-only eligibility filters before adding a minimal browser adapter.

## Figma design-first handoff — drafts awaiting user review

**File:** [HSK AI iPhone PWA — Notifications & Feedback](https://www.figma.com/design/89fCM5GdjfBqcx0B9aQHOI). 4 editable iPhone screen examples and 6 reusable local components prepared from `app/static/course_v3_data/design-tokens.css`:

| Purpose | Figma canvas node |
| --- | --- |
| Authenticated notifications inbox sample | [node 3:2](https://www.figma.com/design/89fCM5GdjfBqcx0B9aQHOI?node-id=3-2) |
| Smart-account settings and future PWA push state | [node 3:48](https://www.figma.com/design/89fCM5GdjfBqcx0B9aQHOI?node-id=3-48) |
| Compact ordinary bot feedback dialog | [node 4:24](https://www.figma.com/design/89fCM5GdjfBqcx0B9aQHOI?node-id=4-24) |
| Release-feedback 1–5 rating dialog | [node 4:40](https://www.figma.com/design/89fCM5GdjfBqcx0B9aQHOI?node-id=4-40) |
| Reusable `feedback/quick-question` and `feedback/release-rating` | [nodes 4:8 / 4:16](https://www.figma.com/design/89fCM5GdjfBqcx0B9aQHOI?node-id=4-8) |
| Reusable `notification/item`, `setting/row`, `button/primary`, `button/secondary` | [nodes 2:20 / 2:24 / 2:16 / 2:18](https://www.figma.com/design/89fCM5GdjfBqcx0B9aQHOI?node-id=2-20) |

**Important:** These are Figma design **drafts**, not implemented, interactive or owner-approved PWA UI. Copy is illustrative and must be reconciled with canonical UZ/RU/TJ sources and real existing bot prompts. The Figma environment lacked the source system SF Pro font, so components use editable Inter fallback; fix typography for final implementation. Do not create another duplicate component library or UI context document. Review and approve the relevant Figma screen/components **before** writing any net-new PWA UI; reuse the unchanged Mini App pages without redesign.

## Figma source alignment — 2026-11-02 (EDITED, P0 READY; pending device acceptance)

**Figma file:** [HSK AI · iPhone PWA Notifications & Feedback](https://www.figma.com/design/89fCM5GdjfBqcx0B9aQHOI). All four editable mockups and their source components were edited on 2026-11-02 **after** the discrepancy audit. The reference source remains the exact `main@f791613c4377ffec2018cce3764cf81e80a6a765` Mini App; no product code was edited.

**Changes applied and visually inspected (page screenshot):**
- Restored current five-tab course/mashq/voice/rating/profile navigation in inbox/settings designs using **actual Tabler vector SVG icon paths** (`ti-map-2`, `ti-cards`, `ti-microphone`, `ti-trophy`, `ti-user`) and a raised 60px cinnabar center mic. Figma approximates the current source Liquid Glass presentation; actual PWA shall reuse the real `.nav` CSS/markup, not implement the approximation.
- Rebound Figma light source colors to `app/static/course_v3_data/design-tokens.css`; 17 semantic token names now have both **light and dark source values**. Figma account limitation: a variable collection only supports **one mode**, so dark values reside in a separate **dark token collection** and are **not** functional automatic light/dark variants. The implementation MUST use the existing source CSS `:root[data-hsk-theme="dark"]` instead.
- Changed global primary CTA from invented jade+white (3.30:1 contrast) to the existing Mini App `--hsk-cinnabar:#E04A40` with `--hsk-on-cinnabar:#160C09`; source jade-on-jade uses dark text, not white. Existing color semantics take precedence.
- Converted draft labels to consistent **Uzbek Latin**, removed fake product-roadmap wording from end-user settings and replaced fake enabled toggle with **OFF/unknown sample**. Runtime copy is NOT approved until actual UZ/RU/TJ canonical keys are wired and real data replaces examples.
- Centered modal visual follows existing `#sheet.hsk30-promo-center` envelope, with source paper color, 24px radius, dark scrim and small bounded panel. Replaced invented generic yes/no with the existing **five** `BotFeedbackService` like-option codes in `app/bot/keyboards/feedback.py`; release-feedback uses actual **1–5 numeric rating choice** and try action rather than made-up stars/submit. Paid-user and follow-up variants remain future P2 behavior gates and must follow real server eligibility.
- Removed excess Bold/10px text in the draft; retained editor-only **Inter fallback** because the Figma runtime lacks SF Pro. Actual browser must use existing `--hsk-font-ui` system/SF Pro stack, not import Inter.
- The `unslop` audit guidance was applied in **light-polish mode** (structure, rhythm, consistency, icons, contrast, accurate source copy); do **not** erase HSK AI's purposeful Liquid Glass or course visual identity. Reference credit: [unslop by Damir Sokolovsky](https://github.com/heydamir/unslop), CC BY 4.0.

**Source design direction (for future minimal changes):** Product: HSK AI Chinese learning course; character: calm, focused, educational; world: paper/ink and course progress; moments: current lesson/progress and earned results; signature: existing HSK course trail and lifted microphone. These derive from current code, not from a template or external palette.

**Acceptance boundary:** Source styles and actual component structures were audited and visually inspected in Figma, but **pixel-perfect live iPhone parity, SF Pro rendering, real dark-theme screen screenshots, interaction/permission behavior, installed Home Screen context, bot prompt eligibility, canonical three-locale validation and accessibility in a real browser are NOT tested**. Design is **ready for P0 source/route inventory and owner review**, not production-approved or fully 1:1 certified.

## Minimal four-stage plan

1. **P0** — trace actual Mini App API/SDK dependencies; review available auth/account services and risks, no speculative architecture.
2. **P1** — minimal secure browser login/session + explicit account linking if necessary; no new auth database if existing model suffices.
3. **P2** — tiny Telegram/browser adapter, reuse identical learner UI/server services, add verified in-app notices and eligible centered feedback via existing sources; inspect Figma first.
4. **P3** — iPhone Home Screen entry/icon, real Safari/installed device and notice/feedback QA, Smart V2 unsupported-channel guard, focused regressions and reversible launch.

See [tasks](../openspec/changes/iphone-course-pwa/tasks.md) for the **only** detailed phase checklist and [design](../openspec/changes/iphone-course-pwa/design.md) for constraints.

## Hard acceptance constraints

Secure/HttpOnly browser session, CSRF/expiry/logout/revocation; Google/Apple verification where configured; no fake Telegram ID, no auto-merge or duplicate referral/trial; no private/grade/payment cache leakage; original Telegram/native clients and lesson grading intact. Confirm original learner's Pro/progress after explicit linking. Pending receipt != paid Pro. iPhone Safari/Home Screen, mic/audio, sign-in return and payment return need real-device evidence.

## P0 kickoff — minimal first-step handoff

**Ready to start P0; tasks 0.1–0.4 are NOT marked complete.** Do not add a new progress file, generic audit framework or runtime code. Work from the current `main` source and leave this PR as draft.

1. **P0.1 route map:** `app/static/course-v3.html`, existing child `course_v3_*.html`, `app/main.py`, `app/api/miniapp_*.py`. Produce ONE concise route/API dependency table: screen, client fetch, Telegram SDK/initData assumption, verified server actor, user-owned service, PWA adapter needed/NOT needed and regression test. Explicit checks: `_apiGet/_apiPost`, `X-Telegram-Init-Data`, `App.goPay`, feedback/source screens, in-app list, safe-area/nav reuse. Do not build a new frontend.
2. **P0.2 identity/payment:** `app/api/native_oauth.py`, `app/services/{native_oauth_service,identity_link_service,desktop_auth_service}.py`, existing user identity/session model, relevant OAuth tests and `docs/UNIVERSAL_NATIVE_ACCOUNTS.md`. Confirm missing browser-session primitives rather than assuming migrations, a new token store or fake Telegram identity.
3. **P0.3 messages:** compare `app/services/course_notification_service.py` vs `notification_delivery_service.py`, current Pro/payment/limit handlers, and account-scoped feed coverage. Keep transactional notices separate from Smart study delivery.
4. **P0.4 future Smart/feedback:** inspect **latest** Smart Reminder master plan P5, user/channel/consent/dedupe contracts and `bot_feedback_service.py`/`release_feedback_service.py` real eligibility and bonus state. Record the minimal PWA read/response bridge; no Web Push v1 or second scheduler.

**P0 exit gate:** a source-verified compact table and list of **only demonstrably missing** browser adapter APIs and UI surfaces, all associated existing tests, code risk/rollback. Reconcile with the current `main` HEAD; update `openspec/changes/iphone-course-pwa/tasks.md` only after evidence and do not check boxes prematurely. P1 coding starts under a **separately approved implementation branch**, not from this planning PR.

**Execution status:** Figma design corrected and visually checked; first P0 audit is ready to start. **P0 not completed**, no runtime implementation started, no `main` merge or deploy. iOS device, live OAuth/payment behavior, actual dark-theme screens and localized running app remain unverified.
