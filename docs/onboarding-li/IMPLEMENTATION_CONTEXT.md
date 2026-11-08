# HSK AI — Li Panda Onboarding | IMPLEMENTATION CONTEXT

> **BU FAYL — YAGONa LIVE TASK HANDOFF/JURNAL.** Yangi chat yoki Codex agent shu faylni o'qib real davom ettiradi. Bajarilmagan ishni bajarilgan deb belgilash TAQIQLANADI.
>
> **Sister document:** [PRODUCT_GOAL.md](PRODUCT_GOAL.md) — final product behavior, fixed scope, 23-state demo, acceptance criteria. Maqsad bu yerda qayta ixtiro qilinmaydi.
>
> **Last verified:** 2026-11-08; **active new-main branch:** `feature/li-onboarding-mainffbff9-20261108`; **branch baseline:** `main@ffbff9492e0713686f57a76443bef17a45c4041c`; **source:** GitHub `akbarholturaev11-lang/HSK-AI-Bot`. Prior docs-only branch `feature/li-onboarding-handoff-20261108` is archival (based on old 4ca0d2d); **do not implement there**.
>
> **REAL ONBOARDING IMPLEMENTATION STATUS: PARTIAL ON FEATURE BRANCH.** See first checkpoint above. New 0154 schema/API/loader code is committed on feature branch, but 23-state UI, Smart/PWA trial, E2E and test execution remain incomplete. Production is still base main ffbff949.

## 0. Yangi chatni boshlash — shu tartib majburiy

1. Repository `akbarholturaev11-lang/HSK-AI-Bot`ni och, **branch `feature/li-onboarding-mainffbff9-20261108`** mavjudligini va uning remote HEAD SHA'sini tekshir. Default `main`dan ko'r-ko'rona davom etma. Local workspace allaqachon dirty bo'lsa user o'zgarishlarini saqla; rebase/reset/force yo'q.
2. `AGENTS.md`, `AI_RULES.md`, `PROJECT_MEMORY.md`, **shu fayl**, [`PRODUCT_GOAL.md`](PRODUCT_GOAL.md), `localization/README.md`, `.agents/skills/hsk-ai-ui/SKILL.md` va scoped auth/Smart Reminder rules ni o'qi.
3. **Current branch HEAD'ni `main` bilan solishtir:** code diff/commits, migrations current head, related tests; loggi statusga emas real diffga ishonsin. Boshqa agent allaqachon o'zgartirgan bo'lsa hammasini qayta ko'rib, shu jurnalni real holatga mosla.
4. Demo reference: current branch `docs/onboarding-li/DEMO_REFERENCE_ONLY.html`ni o'qi va SHA-256 `767c2de59116229dab9304e3036ae589399379340013f1d137eae7df82644b30` bilan solishtir. Undagi `SCREEN_MAP.md`, `CODEX_TASK.md` foydali audit attachment; repo runtime manbasi emas. **Demo now exists in this GitHub branch as reference-only.** Original SHA-256 locally verified; preserve it. Its presence alone does NOT prove live UI copy/visual fidelity.
5. Quyi `CURRENT STATUS` va `NEXT ACTION`ni tekshir. Faqat undan keyin code ishlari davom etsin. Yangi session avvalgi xatolarni takrorlamasin.
6. Har bir **haqiqiy** muhim code slice/migration/test tugagach `CURRENT STATUS`, `VERIFIED CODE CHANGES`, `TEST EVIDENCE`, `NEXT ACTION`, `OPEN RISKS`ni **shu fayl ichida** yangila va kod bilan **o'sha branch commit**da saqla. Har bir token/CSS micro-editni emas, tekshiriladigan fayl/behavior bo'lagini qayd et.
7. Yangi chatga qisqa topshiriq: **"`feature/li-onboarding-mainffbff9-20261108` branch'da `docs/onboarding-li/PRODUCT_GOAL.md` va `docs/onboarding-li/IMPLEMENTATION_CONTEXT.md`ni o'qi. Hozirgi HEAD/diff/testlarni tekshir, jurnalning NEXT ACTION joyidan davom et, har verified code slice'dan so'ng jurnalni actual sha va test evidence bilan yangila. `main`ni o'zgartirma, release qilma."**

## 2026-11-08 VERIFIED WORK RESUMPTION — 23-screen UI, multi-goal planning, PWA trial push

**Current branch:** `feature/li-onboarding-mainffbff9-20261108`, draft PR #282; do **not** merge into `main` until all CI jobs, UI regression and migration contracts pass. Main was fast-forward merged **into the feature branch only** at `8ffe7d556e716a8f554ef8adf1ddbe4eea9c015f` with shared PWA Pro Safari/Lava changes. It did not modify production.

### Implemented code (real files, not inferred)
- `app/static/course_v3_li_onboarding.html`: independent full 23-state visual shell based on user HTML. All original visual and text copy comes from canonical localized sources below. `app/static/course_v3_data/li-onboarding-runtime.js`: one web interface for PWA and signed Telegram Mini App, live course-track fetch, retry/loading, original course-book JPGs, browser actor/cookie CSRF or Telegram signed initData, multi-goal save with POST response reconciliation, no fake login/trial or client Pro grant.
- Served at **`/iphone-pwa/onboarding/li`** with verified PWA cookie (protected preview) and **`/course_v3_li_onboarding.html`** Mini App preview. The deployed default onboarding and native Android remain untouched. Do not activate until visual/API/device acceptance.
- `localization/ui/{uz,ru,tj}/li_onboarding.json`: all **66** original demo text keys per locale and options/reactions (**127** keys total/locale), `scripts/i18n_build_li_onboarding.py` owns a generated `app/static/course_v3_data/hsk-li-onboarding-i18n.js` bundle. `scripts/i18n_build_all_catalogs.py` includes this generated artifact. CI catalog artifact count is now **76** (previously 75). `tests/test_li_onboarding_catalog.py` verifies original copy and pinned supplied demo.
- `docs/onboarding-li/DEMO_REFERENCE_ONLY.html` **RESTORED byte-for-byte to user-supplied original**: source had lost two newline characters during original GitHub upload (at the `trial2`→`trial3` split and trailing EOF); this was corrected without changing wording or UI. Pinned SHA-256 should now match original `767c2de59116229dab9304e3036ae589399379340013f1d137eae7df82644b30`; confirm on CI.
- `app/services/learning_signals.py` and `app/services/daily_plan_service.py`: carry canonical ordered `goals`, compute deterministic primary-weighted 60% / remaining 40% multi-goal task preference. Scalar-only learners preserve identical build behavior; existing daily-plan IDs remain frozen. `tests/test_daily_plan_service.py` covers both.
- `app/services/smart_reminder_policy.py`, `app/services/smart_reminder_policy_context.py`: add read-only actual `current_streak` (valid last activity) and `streak_target_days` to Smart policy context. **No** new consent/sending/scheduling authority, no false progress grant. `tests/test_smart_reminder_policy.py` ensures policy outcome unchanged.
- `app/services/trial_reminder_service.py` integrates PWA opt-in subscriber into existing `CourseNotificationService` + `learner_pwa_push.enqueue_event` outbox for genuine T-48h (limited 12h late grace window). Existing Android/Telegram fallback remains when no PWA event queued. Dedupe via existing per-trial reminder key; `app/services/learner_pwa_push.py` prevents stale sends after trial revoked/expired/converted. `tests/test_trial_reminder_service.py` exercises due-time and push queue. Push receipt/provider success, install consent, and cross-device delivery still require CI/manual QA.
- `alembic/versions/0154_li_onboarding_choices.py` safe additive goals/streak schema on existing metadata QA. No production migration applied.
- Browser UI coverage `tests/e2e/test_li_onboarding_runtime.py` added to Mini App UI workflow; `tests/test_pwa_browser_auth.py` includes PWA protected preview/trial endpoints.

### CI traceability and current blockers
- Prior workflow `42480653632`: `targeted-tests`=**SUCCESS** and `native-postgres`=**SUCCESS**. `miniapp-ui`=failure because reference HTML was 2 newlines shorter than the user's original SHA-256; fixed in commit `2e0e0bcb`, with original pinned hash preserved.
- Prior `42480653535` local-first i18n failure: generator produced 76 artifacts, test still expected 75. Fixed in `a6cdbeb2` (never hide or omit new catalog artifact). Prior Admin PWA `42480653547` only failed same two stale artifact count assertions; its postgres migration job was **SUCCESS**.
- Current branch head after fixes: `a6cdbeb213b4a3c81631225a461d62a71be436ba`. CI workflow `42483948401` (backend), `42483948302` (i18n) were **pending when last checked**; do NOT mark green before rechecking their actual results.
- Distinguish committed/source syntax from validated features: user-visible 23 screens are on isolated preview routes only; exact live click flow, PWA/Telegram signed actor, push receipt and all device Safari/Android compatibility are **not yet proven**. Do not call launch-ready until verified.

### NEXT ACTION after context loss
1. Check latest feature-branch HEAD and GitHub Actions. Fix the actual new failing CI logs, especially `tests/e2e/test_li_onboarding_runtime.py`, with minimal patches and honest tests.
2. Review `app/static/course_v3_data/li-onboarding-runtime.js` against demo's inline function contracts, particularly login, course loading, 23-state stepping and server POST payload response; no fake authenticated progression.
3. Verify `/course_v3_li_onboarding.html` Mini App and `/iphone-pwa/onboarding/li` PWA manually, 3 languages, 390px screen, HSK3.0 locked/live, returning account and trial consent/expiry/revocation.
4. Ensure original onboarding routes still work. Update both journal and product goal when needed, no merge/main deploy without acceptance.
5. PWA T-48h Web Push: user requested exact reminder, but notification permission and active PWA push subscription are necessary; clearly communicate that unreachable users cannot be guaranteed a push.

## 2026-11-08 NEW MAIN AUDIT — latest 401de151 (read-only source + Railway logs)

**Delta evidence:** GitHub compare from `4ca0d2d1` to `401de151`: **1 merged/squashed commit, 29 changed files**. Main is new code, but production isn't. Its Railway deployment `dee3fc58-678d-4ec9-8dc6-83100fd72014` FAILED in **BUILD_IMAGE**, logs repeat `failed to download build driver` for GitHub `nixpacks-v1.41.0`. No Python runtime exception, app migration failure, or test failure demonstrated by that build. Railway production service still **Online** on prior successful deployment `70cf40e4-7ad2-45d3-9b00-2be043be424e`, commit `4ca0d2d1`. New code runtime on production **NOT VERIFIED/NOT DEPLOYED**. GitHub combined status showed Railway failure; GitHub PR workflow-runs query for this SHA returned none, so **test success was not established**.

### 29 changed files — relevance grouping
- **High / direct contract impact:** `app/api/pwa_auth.py` (+ PWA inline UI injection and CSRF event/exit-offer APIs), `app/api/lava_checkout.py`, `app/services/lava/{checkout,config,ledger}.py`, `app/services/pwa_exit_offer_service.py`, `app/db/models/{pwa_exit_offer,lava,conversion_funnel_event}.py`, `alembic/versions/0152_pwa_exit_offer.py`, `alembic/versions/0153_pwa_inline_funnel.py`, `app/static/course_v3_data/iphone-pwa-inline-pro.{js,css}`, `iphone-pwa-inline-pro-bridge.js`, `app/services/{conversion_funnel_service,subscription_entry_analytics_service}.py`.
- **Routing/quality and secondary:** `app/main.py` adds explicit new asset allowlist (CSS/JS) without changing onboarding routes; `app/admin_api/pwa_lava.py`, `app/static/admin-pwa/app.js` map provider promo; `app/db/models/__init__.py` registers new model; `scripts/qa_standalone_bootstrap.py` and `tests/test_qa_standalone_bootstrap.py` advance reviewed head to **`0153_pwa_inline_funnel`**; `.github/workflows/backend-ci.yml` includes new PWA tests; `tests/test_pwa_browser_auth.py`, `tests/test_pwa_exit_offer.py`, `tests/e2e/test_pwa_inline_pro.py`, `tests/e2e/test_pwa_inline_pro_routes.py` cover portions; `docs/iphone-pwa/PWA_INLINE_PRO_CONTEXT.md` documents module (its header still refers to prior 4ca baseline, so treat that header as historical).
- **Unrelated to our runtime goal:** native Android Compose UI test geometry changes in `android/app/src/androidTest/java/com/pomp/hskai/feature/profile/ProfilePromoCarouselTest.kt`; Android production onboarding code was not changed in this delta.
- **Unchanged** between old/main: `app/static/course_v3_onboarding.html`, `app/static/course-v3.html`, `app/static/subscription.html`, `app/services/course_miniapp_onboarding_service.py`, `app/db/models/course_miniapp_profile.py`, `app/services/trial_reminder_service.py`, Smart Reminder policy and PWA reminder services, `app/static/iphone-pwa-sw.js` and original book JPG files. Old proposed implementation remains unimplemented.

### Exact behavior of NEW PWA Pro module — preserve and separate
- `app/api/pwa_auth.py::_pwa_inline_html` injects content-addressed `iphone-pwa-inline-pro.{css,js}` + bridge into **authenticated PWA course, voice, five practice and checkout HTML routes**. It does **not** inject into `/iphone-pwa/onboarding`; it keeps shared original Mini App static HTML unchanged. The inline JS itself is guarded to `/iphone-pwa/(course|practice/...)` only.
- New UI opens instantly on **real limit** through `App.openPaywall`, `App.goPay` and practice bridge, with instant 2-plan skeleton, panda and animated sheet. Actual price/terms from `/api/v3/pwa/subscription/overview`; 1/12 month default, 3/6 and real manual/Alipay/WeChat in additional tariffs. No fake pricing API values. Display-only higher comparison ~30% with .99 ending is **NOT historical/former price**.
- `PwaExitOfferService` creates one account-scoped 20% exit offer for 24h; depends on actual `exit_offer:20` Lava provider mapping, sellable terms, eligibility and claim; only consumed on verified paid invoice. Its API uses PWA cookie+CSRF + same origin; note **it authenticates an account but does not cryptographically prove a physical X click**, despite the docstring saying verified X. Never treat that as a general trial entitlement.
- New funnel: 11 `pwa_pro_*` events, CSRF + event_id/attempt scoped UI reporting for allowlisted limit sources, `inline_preview=true` prevents a price preview from counting checkout, Lava invoice-start event comes after provider invoice, paid event only inside verified payment-grant ledger. Source values are allowlisted but from client UI: they are **telemetry**, not proof of a genuine server limit. Reuse backend payment flow where appropriate; onboarding trial/Pro impressions should use **separate source/event namespace**, not forge a limit funnel.
- Schema: new `pwa_exit_offers` table at Alembic 0152, new `lava_invoices.pwa_inline_attempt_id/source` and funnel CHECK at Alembic 0153. All future onboarding schema migrations MUST start from the **new current head**, verify actual Alembic graph, follow migration QA, and do not assume production has applied 0152/0153.
- New paywall `WORDS` holds RU/UZ/TJ inline even though `AGENTS.md` requires canonical `localization/ui/` authoring. Don't copy that into onboarding; separate future cleanup from this scope unless necessary.

### Two newly clarified HIGH-RISK integration gaps
1. **Public PWA first state / login flow:** `GET /iphone-pwa/onboarding` requires `PwaAuthService.actor` before returning HTML. Meanwhile `GET /iphone-pwa` redirects an already authenticated session to `/iphone-pwa/course`. Demo requires panda `account` before provider signup/login. Implement a **safe public first-screen shell** with temporary non-secret draft and a protected authenticated completion API, restoring draft only to the verified actor after OAuth; never unlock existing private API by simply removing auth.
2. **Pro trial differs from new inline paid paywall:** `app/api/miniapp_entitlements.py` has signed Telegram `/api/v3/trial/{start,status}`. `app/api/pwa_auth.py` exposes **no matching authenticated PWA trial start/status endpoint** as of main 401de. The PWA inline paid exit offer API does not solve this; add a secure account-cookie+CSRF trial adapter reusing canonical trial service, observing eligibility/risk/expiry/cancel/no-auto-charge contracts. Keep paid checkout source/path separate.

### Existing PWA push + Smart Reminder remains unchanged
- `TrialReminderService.REMINDER_DAYS=(2,0)`, `days_left=(ends_at-now).days` (floor), `pwa_push_suppressed=True`; real 48-hour PWA push still needs work with existing outbox and duplicate/fallback control.
- `CourseMiniAppProfile` still only scalar `goal`; `streak_target_days` absent, `current_streak` server-owned. Smart policy still has daily XP/plan/time/consent but no target. Existing legacy motivation streak notifications still present and may duplicate; onboarding shouldn't enable reminders without consent.
- `app/static/iphone-pwa-sw.js` unchanged; any new JS/i18n assets must be content-hashed and tested against PWA cache.
- Production `PWA_PUSH_ENABLED`/`PWA_PUSH_SEND_ENABLED` values and real iOS Home Screen push are **NOT inspected/NOT verified**.

### Testing/QA evidence on new main
- New **test SOURCE** inspected: `tests/test_pwa_exit_offer.py` (one-time offer/provider/verified grant), `tests/test_pwa_browser_auth.py` (PWA event auth/CSRF/dedupe/preview), `tests/e2e/test_pwa_inline_pro.py` (synthetic visual), `tests/e2e/test_pwa_inline_pro_routes.py` (limit routes + manual iframe), `tests/test_qa_standalone_bootstrap.py` (head 0153). `backend-ci.yml` includes related jobs.
- Before this feature, no tests executed; see CI evidence at top for the new branch. Do not call PR checks PASS until a completed CI run confirms it. Railway build didn't reach app startup. **NOT VERIFIED; no PASS claim**.
- Recommend targeted baseline: `python -m unittest tests.test_pwa_browser_auth tests.test_pwa_exit_offer tests.test_lava_promo_codes tests.test_course_miniapp_onboarding tests.test_course_track_service tests.test_trial_reminder_service tests.test_smart_reminder_policy tests.test_smart_reminder_pwa tests.test_qa_standalone_bootstrap`; i18n `python3 scripts/i18n_build_all_catalogs.py --check`; `python -m pytest -q tests/e2e/test_pwa_inline_pro.py tests/e2e/test_pwa_inline_pro_routes.py` (assuming environment deps available); plus migration single-head and synthetic/real-device PWA behavior. Record exact results; these are **proposed commands, not completed tests**.

### Audit conclusion and agreed work boundary
- **Recommend implementing from new main 401de, NOT the obsolete docs branch on 4ca.** This new docs branch was created exactly from 401de, with PRODUCT_GOAL and this context only; no runtime changed. On next task, refresh remote main for further commits and compare before coding.
- **Not started:** user requested AUDIT FIRST, coding NEXT; do not begin P1 without new user instruction. Production Railway failed to deploy new main due Nixpacks driver download; the prior live app stays online. No automatic deployment/merge on this audit.

## 2026-11-08 LATEST CHECKPOINT — implemented PWA trial adapter + real CI evidence

**Active implementation branch:** `feature/li-onboarding-mainffbff9-20261108` based on deployed `main@ffbff949`. Draft PR **#282** open; **not merged, not deployed, no production migration**.

### Additional committed feature behavior
- `app/api/pwa_auth.py`: **GET `/api/v3/pwa/trial/status`** returns canonical `ProTrialService.eligibility` + `TrialRiskService` evaluation for the cookie-verified PWA account; status never grants rights. **POST `/api/v3/pwa/trial/start`** requires PWA enabled, same-origin and cookie+CSRF; rejects Telegram initData spoof, evaluates existing risk and calls the existing one-time `ProTrialService.start`. Only successful start records risk, commits and returns `ends_at`. No independent trial/entitlement/payment engine created, no client-side Pro grant.
- `tests/test_pwa_browser_auth.py`: tests for PWA status auth/risk, trial start unauthorized/wrong-origin/no-CSRF/cross-channel, risk denial, failed eligibility and confirmed server result. **Do not claim these tests passed until full targeted-tests job finishes.**
- `tests/test_course_v3_static_data.py`: updated legacy assertion that demanded silent HSK2.0 fallback on remote failure. Now asserts server-known disabled fallback and **honest retry on failed network**; did not reintroduce a fake access status.
- `tests/test_iphone_pwa_asset_versions.py`: updated allowlist test to inspect actual route `public_assets` membership with both literal keys and existing `dict.fromkeys` JS group; former brittle test falsely rejected five JS assets already in deployed main.
- `app/static/course_v3_onboarding.html`: restored CTA to enabled on successful metadata response; forced deadline for old WebViews without AbortController. No full 23-state activation yet.

### GitHub Actions evidence (NOT ALL GREEN)
- First attempted PR run `42472514663`: Playwright failed due CTA still disabled; old Mini App save confirmation test failed due additive profile shape. Both fixed in commits `0048e1cf` and `2062aa8f`.
- Subsequent run `42472859223`: old static string assertion failed, corrected without weakening fail-closed logic in commit `bbbe3554`.
- Subsequent `42473153502` PWA asset test failed because deployed main had switched to `dict.fromkeys`; updated test in commit `8aa67b91`.
- **Latest specifically inspected completed jobs on commit `6c446b6f`, workflow `42473482755`:** `native-postgres` = **SUCCESS**, `miniapp-ui` = **SUCCESS** (includes `tests/e2e/test_li_onboarding_loading.py`). `targeted-tests` was **IN PROGRESS** as last checked (running `tests.test_pwa_browser_auth`). It must not be marked passed. Other workflows (Smart Reminder, localization, Android) are not fully assessed here; use full current CI before release.
- Tests authored + remote CI actual, but **no dedicated physical iPhone/Telegram device run**, **no manual PostgreSQL production migration**, **no visual 23-screen screenshot regression** and no proof PWA trial UI started from demo.

### Explicit scope not yet delivered
1. User demo 23-state pixel/text fidelity live PWA+Telegram UI (reference-only HTML pinned, current live UI still legacy three-question flow).
2. Public PWA panda-first registration, OAuth return/temporary drafts, signed Telegram auth UX and real first-lesson launch.
3. Bind `goals[]`, time, focus, streak target selections from 23-screen UI; deterministic multi-goal daily-plan weighting and no post-first-lesson duplicate questions.
4. PWA 48-hour trial-expiry Web Push, platform permission/consent, exact dedupe and push receipt evidence.
5. Smart Reminder canonical streak target context and legacy notification cross-channel dedupe.
6. Onboarding event funnel/canonical RU/UZ/TJ source catalogs + builder, full device regression and release safety.

### Next exact action
Review **latest** branch HEAD and `targeted-tests` CI conclusion; fix actual failures. Then implement P1 23-state shared UI from `docs/onboarding-li/DEMO_REFERENCE_ONLY.html` with same copy/poses but **no fake timers/auth/trial**, original course book JPGs and canonical localizations. Continue updating this journal after tested code slices.

## CI evidence — first test cycle and bug fixes (2026-11-08)

- Draft PR [#282](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/pull/282) opened on the feature branch to run tests; **DRAFT, no merge or deploy**.
- GitHub Actions run `42472514663` DID execute tests; `miniapp-ui` failed in `tests/e2e/test_li_onboarding_loading.py::test_track_loading_is_visible_retryable_and_server_authoritative`: after server success, `#cta` stayed disabled. **Actual root cause:** loading render disabled CTA; successful remote render did not re-enable it. **Fix committed:** `app/static/course_v3_onboarding.html` now restores CTA on verified ready state (`0048e1cff92e989a8b5891d4606e39578a9b99b2`).
- Same run `targeted-tests` failed `tests/test_miniapp_onboarding_save_confirmation.py::test_completed_hsk30_choice_is_confirmed_without_any_write` due newly additive `goals/streak_target_days/preferred_focus` status fields. **Fix committed:** adjusted exact expected response for old legacy profile while preserving read-only/no-write requirement (`2062aa8faa9473114de089ec43c1ab84c4279614`).
- A new PR CI cycle began after fixes: GitHub workflow run `42472708714` (backend targeted). **At this journal write it is IN PROGRESS; not PASS**. Check workflow jobs and logs before advancing claims.
- Original demo `docs/onboarding-li/DEMO_REFERENCE_ONLY.html` was compared character-by-character to the attached original through GitHub + Files tools: **identical, all 23 cases present**. Local SHA-256 already matched. This is reference QA only, not a visual browser pass.

## 2026-11-08 IMPLEMENTATION CHECKPOINT — first partial code slice on deployed main ffbff949

**Source:** base `main@ffbff9492e0713686f57a76443bef17a45c4041c`, feature `feature/li-onboarding-mainffbff9-20261108`. Railway production deploy for base ffbff949 verified **SUCCESS**. Source code changes below **only on feature branch**, no production deployment or main merge.

**Exact original demo source now located and pinned:** `docs/onboarding-li/DEMO_REFERENCE_ONLY.html`, original 1038-line, 99,339-byte user-provided HTML. Local container SHA256 computed and matched `767c2de59116229dab9304e3036ae589399379340013f1d137eae7df82644b30`. Source file is REFERENCE-ONLY; it is **not** live 23-screen onboarding, and its fake auth/trial/timers must never be shipped as-is.

### Verified code changes (GitHub source writes, not executed runtime)
- `alembic/versions/0154_li_onboarding_choices.py`: additive nullable profile columns `goals_json` and `streak_target_days`, PostgreSQL CHECK for 7/14/30/50, Alembic named-constraint `op.f`; down-revision `0153_pwa_inline_funnel`. Old goal/progress untouched by migration.
- `app/db/models/course_miniapp_profile.py`: ORM mapping and matching CHECK.
- `app/services/onboarding_goal_selection.py`: strict ordered primary-first multi-goal input, valid streak target and backwards read fallback. Uses no reward/activity data.
- `app/services/course_miniapp_profile_service.py`: optional `goals`, `streak_target_days` accepted and stored, existing scalar goal preserved, old scalar-change clears a mismatched legacy JSON array, verified focus optional. Current streak and XP not touched.
- `app/services/course_miniapp_onboarding_service.py`: pass choices through both legacy HSK2.0 and live HSK3.0 completion paths; profile return includes all choices without resetting server-owned XP.
- `app/api/pwa_auth.py`: authenticated same-origin/CSRF optional request schema, invalid goal array returns 422 before course mutation, status reads persisted choices.
- `app/main.py`: verified Telegram `X-Telegram-Init-Data` onboarding request and status support optional choices, invalid input 400 with existing semantics.
- `app/static/course_v3_onboarding.html`: version screen now shows immediate panda loading shell/skeleton while real track API unresolved, error+retry without inventing HSK3.0 access; 12s abort timeout, request-sequence guard; success replaces skeleton with real version and original book JPG. **Existing UI is still 3-question flow, not 23-state demo.**
- Tests authored: `tests/test_li_onboarding_choices.py`, additions to `tests/test_pwa_browser_auth.py`, `tests/e2e/test_li_onboarding_loading.py`; `.github/workflows/backend-ci.yml` includes new unit and Playwright steps. QA bootstrap/test reviewed expected head advanced to `0154_li_onboarding_choices`.

### Current status (do not overclaim)
- P0 baseline: **PARTIAL**. Source/main/deployment SHA and demo hash verified, but no fully local project checkout or CLI migration/test baseline.
- P1 23-state 1:1 UI: **NOT STARTED** (exact demo pinned as source, not live).
- P2 universal loading UX: **PARTIAL** (only first course-track metadata request path; lesson, auth, Pro, trial, push etc remain).
- P3 public/auth draft: **NOT STARTED**.
- P4 goals/time/focus/streak persistence: **PARTIAL** (DB + server endpoints exist in branch, demo UI not connected, plan weighting not migrated).
- P5 real HSK course/lesson integration: **NOT STARTED** (legacy behavior preserved).
- P6 Pro trial new PWA adapter: **NOT STARTED**.
- P7 exact 48h PWA trial push: **NOT STARTED**.
- P8 Smart Reminder streak-context integration and duplicate-notice owner: **NOT STARTED**.
- P9 onboarding-specific analytics and canonical RU/UZ/TJ copy: **NOT STARTED**.
- P10 acceptance/visual/iOS E2E: **NOT STARTED**.

### Test evidence
- Authored files and new CI steps: **YES**.
- GitHub Actions DID execute targeted unittest and synthetic Playwright in PR #282: first run failures described in CI evidence; fixes are committed and the new CI run is pending. Direct local test/physical-device QA and migration rehearsal remain **NOT RUN**.
- Do not mark migration safe or production ready before sandboxed database migration+regression and CI proof.
- Source-driven checks performed: GitHub read-after-write and source-anchor validation; these are **not** test execution.

### New risk / review before next code
1. First check `0154` single Alembic head + PostgreSQL physical CHECK naming, migrate existing sample profile, downgrade rehearsal without deleting real data; do NOT run this on prod just to test.
2. Review PWA/Telegram profile request actor boundaries, potential retry-after-lost-POST progress mutations, and prompt/post-first-lesson suppression.
3. Verify profile goal lists integrate into versioned daily-plan weighting without mutating frozen plan.
4. Current loader uses existing canonical `onboarding.progress` and `courseLoadError` strings; for exact demo `loadCourse` copy, add canonical RU/UZ/TJ keys and generate resources in a real checkout before final UI.
5. No PWA public panda-first account route yet, no PWA trial status/start, and no 48h push. Never claim user-visible full onboarding.
6. Do not overwrite PWA-only inline Pro limit module, Lava attribution, or existing Mini App plan gating.

### Next action
**Run branch CI/targeted tests, fix failures, then P1 implement the hash-verified 23-state UI using the pinned demo CSS/copy/panda and real course book JPEGs, with secure per-platform account adapters.** Continue from `PRODUCT_GOAL.md`, not an invented redesign.

## 1. CURRENT STATUS — faqat tekshirilgan holat

| Slice | Status at last verification | Evidence / note |
| --- | --- | --- |
| P0 — source baseline | **PARTIAL; CLI baseline NOT run** | deployed ffbff949 confirmed, original demo pinned |
| P1 — 23-state shared visual UI | **NOT STARTED** | Demo reference is separate attachment |
| P2 — real loading state everywhere | **PARTIAL** | track metadata load state + retry added in shared HTML; other remote flows pending |
| P3 — PWA/Telegram auth/draft | **NOT STARTED** | Existing endpoints audited |
| P4 — multi-goal/time/focus/streak schema | **PARTIAL** | additive 0154 + PWA/Telegram endpoint support, UI and daily-plan consumers pending |
| P5 — real HSK track/lesson | **NOT STARTED** | Existing course routes audited |
| P6 — Pro offer/trial activation | **NOT STARTED** | Existing Telegram trial endpoint, PWA gap |
| P7 — 48h PWA trial push | **NOT STARTED** | Existing push engine; actual flags unknown |
| P8 — streak ↔ Smart Reminder | **NOT STARTED** | Existing Smart planner; integration gap |
| P9 — analytics + canonical locales | **NOT STARTED** | Current analytics/i18n infra audited |
| P10 — regression, screenshot, device QA | **NOT RUN** | tests authored, CI step added; no pass evidence yet |

### VERIFIED CODE CHANGES

- **Runtime code, schema, migrations, endpoints:** partial; see 2026-11-08 IMPLEMENTATION CHECKPOINT above. This older section describes the initial docs-only point-in-time, not the current branch.
- **Documentation-only commits in NEW branch:** `docs/onboarding-li/PRODUCT_GOAL.md` created in `a241f6c434a30d0115514384f8980cee06b47ece`; this journal created subsequently. Previous archived branch commits (`6a09d036`, `666c9922`) are not the active implementation base. Confirm latest branch diff/commit SHA.
- Do **not** conflate audit findings, source references, earlier chat task prose, fake/demo UI, or planned designs with written/tested production code.

### TEST EVIDENCE

- Executed unit/API/Playwright/i18n commands in the current implementation session: **none yet**. See latest checkpoint above.
- GitHub `fetch_file`/read-only code inspection conducted; reading test names does **not** mean tests passed.
- User device/iOS Home Screen push, env credentials, VAPID readiness and production delivery: **not verified**.
- Documentation can be manually checked via remote GitHub `fetch_file` + compare commits after creation; that does not test app behavior.

## 2. Audited current code — facts from `main@4ca0d2d`

The paths below existed and were reviewed **read-only** on 2026-11-08; recheck fresh code before editing.

### Frontend / identity / onboarding
- `app/static/course_v3_onboarding.html`: existing shared Mini App + PWA course onboarding (welcome plus track/level/one goal); book image handling includes actual JPEGs.
- `app/static/course-v3.html`: checks `onboarding_completed === false` on course entry; after-first-lesson setup asks `daily_minutes` and `preferred_focus`. It also has a prior explicit rule suppressing Pro/trial immediately after onboarding, so the demo offer changes this behavior intentionally; avoid second overlapping paywall.
- `app/static/iphone-pwa-login.html`, `app/static/iphone-pwa-login.js`: real login/provider browser flows; PWA auth cookies/callback and return destination must be preserved.
- `app/api/pwa_auth.py`: `/iphone-pwa/onboarding`, PWA auth `PwaAuthService.actor` vs `mutation_actor` (cookie + CSRF); POST `/api/v3/pwa/onboarding`; existing provider and push endpoints.
- `app/main.py`: `/api/miniapp/onboarding` POST and `/api/miniapp/onboarding/status` GET with signed `X-Telegram-Init-Data` check. Common `CourseMiniAppOnboardingService.complete`; status GET helps reconcile uncertain writes. PWA and Mini App share frontend but **not authentication trust mechanism**.
- Telegram already verified account should not be asked for fake signup; existing account/Pro/progress should never be reset on a mere revisit.

### Course / goal / daily plan / streak
- `app/db/models/course_miniapp_profile.py`: scalar `goal`, `daily_minutes`, `preferred_focus`, `goal_chosen_at`, `current_streak`, `longest_streak`; **no confirmed `goals_json` or `streak_target_days` yet**.
- `app/services/course_miniapp_profile_service.py`, `app/api/miniapp_preferences.py`, `app/services/learning_signals.py`: scalar goal consumers; migration and serialization backward compatibility needed.
- `app/services/daily_plan_service.py`: goal-specific weighting; frozen daily-plan keys/schema; do not retroactively rebuild user's already-frozen current plan.
- `app/services/course_gamification_service.py`: XP award drives canonical `current_streak`, `longest_streak`, `last_activity_date`; missed/future day streak is display-corrected. Goal selection must not award activity.
- `app/services/course_track_service.py` / course track endpoints: server `live_levels`, allowed state, HSK3.0 preview vs real lesson entitlement; trial does not automatically unlock HSK 3.0. Do not route old users to destructive `lesson_1` start.
- Book assets **actual repo images**: `app/static/assets/hsk20-course-books.jpg`, `app/static/assets/hsk30-course-books.jpg` (runtime cache version `v=20261003c` observed). Fake demo CSS book should be removed.

### Pro trial / PWA push — the exact implementation gap
- `app/services/trial_reminder_service.py`: `REMINDER_DAYS=(2,0)`; due check uses `days_left=max(0,(ends_at-now).days)`, i.e. floor, **not precise 48-hour due**; existing Inbox row uses `dedupe_key="trial_reminder:{ends_at.date()}:{days_left}"` and `pwa_push_suppressed=True`.
- `app/services/notification_delivery_service.py`: Android-first, Telegram fallback; learner PWA outbox may be additionally enqueued on existing notice rows. **Do not simply remove `pwa_push_suppressed=True` blindly**: inspect overlapping `NotificationDeliveryService.deliver` enqueue, duplicate channels and return status; design exactly-once user-visible 48h PWA notice.
- `app/services/learner_pwa_push.py`: opt-in PWA subscribers, outbox, dedupe, dispatch; generic lock-screen notice by default; end user auth/endpoint binding and session checks.
- `app/api/pwa_auth.py`: GET `/api/v3/pwa/push/status`, POST `/push/subscribe`, POST `/push/revoke`; subscription requires cookie + CSRF + same origin; proper device binding.
- `app/static/iphone-pwa-sw.js`: PWA service worker push handling, click-to-open authenticated Inbox; cache versioning must be updated with changed asset references.
- `app/main.py` `_background_scheduler`: every ~60s checks trial reminders; `_admin_pwa_apple_push_scheduler` dispatches learner outbox about every 60s if configured.
- `app/config.py`: `PWA_PUSH_ENABLED=False` and `PWA_PUSH_SEND_ENABLED=False` as defaults; **production configuration not audited**, so no guarantee that push is active.
- `app/api/miniapp_entitlements.py`: trial status/start uses real signed Telegram identity; **PWA needs its cookie + CSRF authenticated service adapter** (not insecure Telegram initData mimic).
- Trial eligibility, paid and previously used trials must obey existing services. Provider acceptance != notification displayed.

### Smart Reminder / legacy motivation collision
- `app/services/smart_reminder_policy.py`: `PolicyContext` has verified `studies`, `daily_goal_xp`, `plan_completed`, IANA timezone, quiet hours, manual/auto time and consent; **no explicit streak-target field**.
- `app/services/smart_reminder_policy_context.py`: verified XP/progress, scoped history and plan context; extend here rather than compute stale client-only streak.
- `app/services/smart_reminder_planner.py`, `smart_reminder_destination.py`, `smart_reminder_pwa.py`, `smart_reminder_preferences.py`: per-user/day ownership, PWA delivery, consent and routing. PWA subscription alone is not Smart Reminder consent.
- `app/db/models/smart_reminder.py`: source consent accepts 'telegram'/'android' with additional PWA transport based on Smart ON + subscriber; do not silently invent a conflicting third user opt-in state.
- `app/services/motivation_reminder_service.py`: existing Telegram evening streak/goal reminders; today's verification uses `last_activity_date` and current streak, with special D1 recovery and routing holds. Must avoid duplicate reminders with new Smart cross-channel state.

### Analytics/i18n/testing audit
- `app/services/course_miniapp_analytics_service.py` and `app/db/models/course_miniapp_event.py`: existing tracked event list/dedupe (PWA needs cookie+CSRF transport).
- `localization/ui/{ru,uz,tj}/{course,common,miniapp}.json`: canonical copy sources; `scripts/i18n_build_all_catalogs.py --write` then `--check` required for actual UI changes.
- Inspected test paths: `tests/test_pwa_browser_auth.py`, `tests/test_course_miniapp_onboarding.py`, `tests/test_course_track_service.py`, `tests/test_daily_plan_service.py`, `tests/test_pro_trial_service.py`, `tests/test_trial_risk_service.py`, `tests/test_trial_reminder_service.py`, `tests/test_smart_reminder_policy.py`, `tests/test_smart_reminder_pwa.py`, `tests/test_course_gamification_service.py`, `tests/test_motivation_reminder_service.py`, `tests/test_iphone_pwa_asset_versions.py`, `tests/test_iphone_pwa_navigation_contract.py`.
- **No tests were executed as part of this audit**, including no full local baseline (GitHub tool reading only).

## 3. NEXT ACTION — immediate planned work

**P0 before P1 code:**

1. Refresh repo SHA and branch diff, confirm two docs and original demo availability/checksum, check local working tree and migration head.
2. Read required project rules/UI skill and `localization/README.md`; examine `course_v3_onboarding.html` vs demo side by side, create a concise 23-state-to-source mapping **within this journal or implementation PR** (do not add a competing progress file).
3. Run and record baseline targeted tests as environment permits; record the actual command, result and blockers (especially Auth, course track, preferences, PWA push, Smart Reminder and i18n).
4. Implement **P1** shared visual shell/state machine, source-verified demo copy/assets and **P2** universal loading states in small reviewable commits. Avoid changing real account/Pro/trial while only UI renders.
5. Then implement P3–P8 in dependency order, keeping migration/consent/auth/legacy guards; update this file after **every verified code slice**.
6. Commit updated journal together with code, not minutes later, and verify remote branch state. Do **not** treat a successful commit as tested/released.

## 4. Open risks / facts still to verify (not invented)

- Exact demo asset is a prior conversation artifact, not yet committed to repo. Its availability/hash must be checked in next agent session. **If absent, visual/text "1:1" acceptance is blocked**.
- Current database Alembic head, local dependency/test environment and working-tree conflicts have **not** been checked.
- PWA Web Push is feature-flagged; production VAPID/config and actual installed iOS permission unknown.
- Trial 48-hour scheduler and durable send are **not** confirmed; old `.days` logic has a boundary bug; dual push/inbox delivery may duplicate without carefully unified ownership.
- PWA auth trial start may not exist under cookie+CSRF; do not reuse Telegram endpoint insecurely.
- Multi-goal + streak target requires additive schema and downstream consumer tests; analytics/event allowlist may need migration/validation.
- Existing Pro onboarding suppression and legacy motivation delivery overlap new demo behavior; test both.
- Smart Reminder has careful rollout/shadow/admission/consent/quiet/no-retry semantics: never turn ON or bypass them just to send streak notices.
- PWA push device eligibility and service worker cache update may require real-device QA; failed provider doesn't prove failed display and accepted provider doesn't prove success.
- Some `main` code may move before implementation; compare current code and update this audit section if materially changed.

## 5. Checkpoint format — update AFTER implemented code, not merely a plan

Append **one checkpoint per meaningful verified slice** and update sections 1/3/4:

```text
### YYYY-MM-DD HH:MM (+timezone) — P# <slice name>
Base HEAD: <sha>; working branch: <name>; new commit: <sha or UNCOMMITTED>
Actual changed files: <exact paths>
Actual behavior in runtime: <specific observed behavior and API/schema contract>
Migration: <revision or none>; rollback: <how>; existing user impact: <facts>
Tests EXECUTED: <exact command> -> PASS / FAIL / NOT RUN + counts/output
Manual/visual/device evidence: <proof or NOT VERIFIED>
Regressions/risks: <remaining exact risks>
Next single action: <specific file/step to work on>
```

**Rules:** Mark PASS only after command output, NOT RUN when not executed, distinguish unit/CI/device/prod. Every feature claim must be tied to an actual committed file and test/evidence. Do not copy secrets, endpoints, user data, raw auth tokens or private admin credentials. Small CSS/typo changes can share a checkpoint; do not duplicate full Git history. Important stable architectural decisions go to `PROJECT_MEMORY.md` according to `AI_RULES.md`, not as competing diary. If a test fails or rollback occurs, revise CURRENT STATUS rather than keeping false done.

## 6. CHRONOLOGICAL CHECKPOINTS

### 2026-11-08 — NEW MAIN audit refresh and docs-only transfer

- Confirmed `main` moved from `4ca0d2d1` to `401de151` (29 changed paths). Read route-level PWA inline-Pro and payment/analytics/DB diffs; verified unchanged onboarding/trial/Smart sources.
- Railway deployment for `401de151` failed in build driver download, previous `4ca0d2d1` stays Online. No evidence of new app/runtime or tests succeeding.
- Created docs-only `feature/li-onboarding-mainffbff9-20261108` from exact `401de151` and transferred the two handoff files with this refreshed audit. Old docs-only branch is archival.
- **Actual onboarding runtime implementation: NONE. Tests: NOT RUN. No main merge or deployment.**
- Next: after user requests coding, establish P0 test/migration/demo baseline, then implement shared UI plus safe public PWA entry and new billing/analytics adapter separation.

### 2026-11-08 — Documentation/structure only (historical, old base)

- Base main HEAD verified: `4ca0d2d1c7e89e517f6d9e6ab781c12963287b9a`.
- Created initial archival docs-only branch `feature/li-onboarding-handoff-20261108` from that SHA. This was replaced with a new latest-main docs-only branch, see checkpoint above.
- Added `docs/onboarding-li/PRODUCT_GOAL.md` — explicit 23-state final goal, original book JPG exception, all server loading UX, real PWA+Mini App auth, multi-goal/time/focus/streak, 48h PWA push and Smart Reminder integration, DoD/test scopes.
- Added **this** `docs/onboarding-li/IMPLEMENTATION_CONTEXT.md` — factual audit, not code implementation, current status, next session instructions.
- Real code changed: **NONE**. App migrations/tests/visual QA: **NOT RUN**. Production deployment: **NO**. Main push/merge: **NO**.
- **Next:** P0 environment/test baseline + SHA-verified demo, then P1/P2 implementation.
