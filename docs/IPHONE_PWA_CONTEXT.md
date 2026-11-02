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

## P0 verified inventory — code-only audit, 2026-11-02

**Read-only P0 result:** assessed real `main@f791613c4377ffec2018cce3764cf81e80a6a765`, current frontend, direct `main.py` endpoints and routers, native identity/linking, persistent notices, Smart V1/V2 contracts and bot feedback. **No code, migration, secrets, provider configuration, test execution or physical iPhone environment was changed or validated.**

### Actual frontend and request-actor route map

Mini App has **one main learner page plus seven separate practice/onboarding HTML pages**: `course-v3.html`, `course_v3_{mistakes,test,pronunciation,voice,memorize,onboarding,recognition}.html`, all served by [`app/main.py`](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/blob/main/app/main.py#L2136-L2140) and [`#L2363`](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/blob/main/app/main.py#L2363). Reuse actual HTML/CSS and current `.nav`; no copied PWA frontend.

| Client feature | Current routes / owner | Existing auth transport | Minimum browser gap |
| --- | --- | --- | --- |
| Initial account, profile, course map, streak, inbox | `GET /api/v3/map`, `GET /api/miniapp/profile`, `/gamification`; `main.py`, `CourseNotificationService` | signed Telegram header, `get_by_telegram_id` | authenticated `users.id` actor and existing service invocation; source-owned feed scope |
| HSK2/HSK3 track and onboarding | `/api/v3/course-tracks[/*]`, `/api/miniapp/onboarding[/status]` | Telegram header; switch may also accept body `initData` | browser user actor and same track/onboarding rules; do NOT fake Telegram |
| Lesson source and access | `/api/v3/lesson/{content,foundation,start,unlock,complete,skip-test}`, `/api/miniapp/course-lesson*`; `miniapp_entitlements.py` + `main.py` | Telegram header / selected body; actual server proof and grade | browser-auth adapter to same service/lesson proof; never expose protected answers |
| Quizzes, exam, daily gate and drills | `/api/v3/exams/{start,complete}`, `/api/v3/practice/{daily-gate,words,report,start,complete}`, `/api/miniapp/practice/*` | mixed Telegram header/body | authenticated actor and original server limits, grading, attempts |
| Mistakes/review, achievements, challenges | `/api/miniapp/mistakes[/review/*]`, `/gamification`, `/reward-chest/open`, `/challenges*` | Telegram header; several service entrypoints take Telegram ID | same canonical account services; Telegram-only challenge routing must be unavailable or separately verified when `telegram_id=NULL` |
| Voice, pronunciation, speech | `/api/voice-practice/me`, `/session/*`, `/message`, `/pronounce` in `main.py`; child pages | `initData` in **URL query, JSON body or multipart form**, passed to `VoicePracticeService` as Telegram ID | real browser-session actor and canonical user service path; validate mic/AI entitlement; no fake TG or URL token |
| Preferences, locale, trial, limits | `/api/v3/{preferences,language,notify,trial/*,limits/status,hints/dismiss}` | signed Telegram header/body, user by `telegram_id` | browser account route and differentiated legacy notifications vs Smart consent |
| Checkout and receipt | `subscription.html`, `/api/subscription-miniapp/{overview,payment-status,discount-start,quote,event,submit}` in `main.py` | Telegram header; `subscription.html` treats missing initData as **preview** | browser checkout auth + return/receipt ownership/confirmed server state; no second billing system |
| Analytics, referral & bot-specific intents | `/api/miniapp/event`, `/api/v3/invite`, `/api/v3/exit`, `/api/miniapp/challenges` | Telegram header, some event handlers send bot chat | classify event vs bot-only actions; PWA events by `user_id`, cannot send to missing Telegram ID |
| Read-only/public assets | existing public static course shell, `/api/v3/tts`, `/api/v3/lesson/sales-preview` | currently public | no new auth adapter unless actual asset access review requires one |
| Existing course feed | `CourseNotificationService.list_for_user(user)`, returned inside `GET /api/v3/map` | map header verifies Telegram; `owner_clause` already supports canonical owner | expose existing authorized inbox through shared map/service, no new feed database |
| Existing account transaction notice | `NotificationDeliveryService`, `AccountNoticeDelivery`, current account/payment state | Android FCM with shown-ack and delayed Telegram fallback | preserve external delivery, verify which notice records are persistently stored; PWA must not claim history/receipt for unrecorded Telegram-only notices |
| Smart reminders | `/api/v3/smart-reminder/preferences` (TG), `/api/v3/android/smart-reminder/*` | separate signed Telegram / Android-native bearer actor | **future V2 only**: add explicit browser actor/channel only when approved, never current cookie fallback into TG/Android handlers |
| Bot and release feedback | `BotFeedbackService`, `ReleaseFeedbackService` and bot callbacks | Telegram ID/chat delivery; canonical feedback rows | PWA needs eligible account-scoped **read + submit** bridge; no new campaign scheduler or duplicate rewards |

**Concrete frontend seam:** `course-v3.html` [lines 2167–2211](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/blob/main/app/static/course-v3.html#L2167-L2211) binds `Telegram.WebApp.initData` and `_apiHeaders/_apiGet/_apiPost`, but other pages and checkout construct their own `fetch` requests. A single change to main `_apiHeaders` would **not** cover those pages. Audit/patch only the actual callers, preferably a tiny reusable client transport plus verified backend actor. Existing Telegram signed-initData endpoints remain unchanged.

### Identity and cross-account constraints — verified

- [`app/api/native_oauth.py`](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/blob/main/app/api/native_oauth.py#L73-L104) accepts only `android|macos|windows` for **signin**, while `miniapp` is permitted for **link only**. `NativeOAuthService` already has Google/Apple verification, OAuth state/nonce/callback, and `IdentityLinkService` resolves signed-in provider subject to `users.id`, rejects email-based merge and blocked users. **PWA cookie browser session/signin transport is genuinely missing**, not an opportunity to reuse Admin PWA or native refresh tokens.
- `DesktopAuthService` [declares Mini App link-only](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/blob/main/app/services/desktop_auth_service.py#L38-L56), no native installation/session. A previously Telegram-only learner must **link Google/Apple to their already authenticated account** before a provider-based PWA sign-in can map to that same Pro/progress account, or follow a separately verified explicit ownership handoff. Never auto-create a second account then merge by email.
- Current main client `localUserScope()` at [line 3624](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/blob/main/app/static/course-v3.html#L3624) returns **`preview`** when there is no Telegram user, used for foundation and resume/mastery local keys. The standalone PWA must not share a global preview cache across signed-in accounts. `subscription.html` similarly sets `preview:!INIT_DATA`; do not show an authenticated PWA as unpaid preview.
- Telegram-specific profile avatars, referral bot links, challenge opponents and exit/chat events need graceful supported behavior without a Telegram ID. A dummy TG ID would break canonical ownership and delivery.

### Notifications, Smart V2 and feedback — verified

- `GET /api/v3/map` [populates `data["notifications"]`](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/blob/main/app/main.py#L2746) through `CourseNotificationService.list_for_user(user)` with `owner_clause` on canonical owner. Reuse it rather than adding an inbox table.
- `NotificationDeliveryService.deliver` persists `AccountNoticeDelivery` **when Android targets exist**; without them it can send straight to Telegram. Therefore **not every transactional notice is guaranteed to appear in `CourseUserNotification` or in a persisted `AccountNoticeDelivery` row**. Do not display imaginary historical account notices. For v1, show server-confirmed current subscription/payment/limit state and only actual authorized stored feed/notice events.
- Smart [Master Plan](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/blob/main/docs/smart-reminders/SMART_REMINDER_MASTER_PLAN.md) D10: iPhone PWA Web Push **V2**. Current `SmartReminderActor` kinds = `telegram|telegram_bot|android`, `SmartReminderPatch.preferred_channel` only `telegram|android`; [Smart API](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/blob/main/app/api/smart_reminder.py#L61-L114) deliberately rejects ambient cookies and mixed auth. `smart_reminder_policy.py` is **shadow / dispatch_allowed=False** and main scheduler currently describes Smart dispatch as OFF by default. PWA v1 reads/correctly displays *real* consent status only if shared read API is intentionally added; no hidden ON toggle. V2 will require **explicit additive browser actor, channel preference/capability, user-granted Home Screen Push subscription, one scheduler/job, delivery receipt and safe target**; not just a Figma toggle or front-end icon.
- Bot feedback `BotFeedbackService`: join delay 1 day, two prompts max, 24h retry, 30-day repeat exclusion, one 30-minute reward only where eligible; paid questions differ from free and subsequent negative details matter. Current due-send scan requires a **real Telegram ID**. PWA must reuse existing campaign/response records with a dedicated verified browser-eligible read/write path, not pretend every PWA visitor has a pending chat prompt.
- Release feedback `ReleaseFeedbackService` targets Telegram-reachable users, uses 1–5 rating and optional try/comment/discount; some reward paths take a real `telegram_id`. The Figma card illustrates only a campaign's **initial step**. Browser-only reward eligibility and later stages are a **confirmed service boundary to inspect/extend**, not proof of parity.

### Focused existing test baseline (identified, NOT executed)

- Auth/provider/owner: `tests/test_native_oauth_api.py`, `test_native_oauth_lifecycle.py`, `test_identity_link_service.py`, `test_desktop_auth_service.py`.
- Course/voice/paywall: `tests/test_course_miniapp_lesson_flow.py`, `test_course_miniapp_practice.py`, `test_miniapp_practice_api.py`, `test_miniapp_preferences_api.py`, `test_course_v3_mobile_practice_contract.py`, `test_subscription_miniapp_submit.py`, `test_miniapp_profile_status.py`, `test_miniapp_live_voice.py`.
- Messages/feedback/Smart: `tests/test_course_notification_language.py`, `test_limit_notification_service.py`, `test_bot_feedback_service.py`, `test_bot_release_feedback_localization.py`, `test_smart_reminder_preferences.py`, `test_smart_reminder_capabilities.py`, `test_smart_reminder_coordination.py`, `test_smart_reminder_p0_regression.py`.

These tests exist on `main` and demonstrate existing boundaries; **no pytest or browser/iPhone tests were run in this read-only audit**. Run the focused tests on the actual future implementation branch, then add PWA negative tests before release. Existing OpenSpec GitHub Actions "Success" is NOT backend QA.

**P0 risk priorities (not extra feature work):** (1) **HIGH** secure browser identity and consistent canonical owner; (2) **HIGH** mixed transport in child pages, native-only account and preview storage; (3) **HIGH** voice/graded lesson/pending payment entitlements; (4) **MEDIUM** preserving real in-app vs transactional messages and review incentives; (5) **MEDIUM / deferred** future Smart V2 channel/OS permission and real-device UI parity.

**Minimal verified P1/P2 delta:** (a) one browser session/auth actor/CSRF service using existing provider-subject identity resolution; (b) shared actor-to-business-service entrypoints only where existing functions currently insist on Telegram ID; (c) one very small client host request/navigation adapter reused by actual learner pages; (d) only necessary inbox/current-account and eligible feedback read/write transport; (e) optional account linking proof and PWA-specific checkout return. **No duplicate course UI, user table, billing engine, notification scheduler, data warehouse or compulsory SW.** Schema migration necessity and exact endpoint names remain **unverified**, to be decided by P1 code after owner approval.

## Gate after P0

**P0.1–P0.4 source review is complete** against the verified 2026-11-02 `main` SHA. See the source-linked table, security boundaries and named tests above. No test execution, browser sign-in, live database/provider access, iPhone QA or deployment has happened. The P0 checkboxes in [OpenSpec tasks](../openspec/changes/iphone-course-pwa/tasks.md) represent **code inspection only**.

**Next gated step: P1 secure browser identity/session**, with existing verified Google/Apple identity service reuse, explicit Telegram account linking, canonical `users.id`, HttpOnly/Secure/CSRF/session expiry, and new negative tests before course writes. Implement only on a separate implementation branch after explicitly resolving the P1 authorization/design gate; keep this draft PR planning-only and leave `main` untouched.
