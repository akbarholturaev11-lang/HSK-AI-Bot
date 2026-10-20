# HSK AI Local-First i18n — RESUME NEXT CHAT

Updated: 2026-10-20. **This is the short authoritative checkpoint, not evidence of main/production release.**

## Git and protected scope

- Repository: `akbarholturaev11-lang/HSK-AI-Bot`.
- **ONLY active work branch:** `codex/p3-main-integration-20261020`.
- Latest pushed code is `10cff3b60ad0a84b430449b9cd19c61d879af50f`; `origin/main` `66ac3d4e94ead8a3c34d45910ffe60f988bf1cf5` is an ancestor, so this branch is 504 commits ahead and 0 behind. Continue only on this branch; do not push/merge `main`, force-push, rebase or deploy production.
- Old source branch `codex/i18n-local-first-foundation-20261017` is integrated. Do not redo the merge. Draft PR #179 is not release authorization.
- Exact-head GitHub P0 [`39429482563`](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39429482563) **SUCCESS** on `10cff3b6` (368 tests). Backend targeted [`39427932361`](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39427932361) **SUCCESS** on preceding security commit `b887fe08`; this UI-only commit did not trigger Backend CI. The P2 batch adds two HSK1 pronunciation UI labels. Read-only audits found 811 frozen sources, 746 lessons, 0 baseline blockers, 894 UI keys per locale and 6 generated artifacts with 0 stale. Mobile Chrome smoke rendered UZ/RU/TJ labels at 390×844 with no console or HTTP errors.

## Implemented local-first i18n

- **P0/P1:** source baselines and deterministic UZ/RU/TJ catalogs/generators; no per-string AI/server calls. Current course UI catalog has **894 keys per locale**, with six generated local artifacts for Android, Mini App, Desktop and Bot. All 12 HTML bundle consumers use `?v=20261020-eaff685fb700`.
- **Latest P2 commits:** `df004ba6` adds nine localized plural messages for dictionary word/result/stroke counts; `c9edc41c` localizes three subscription close accessible names; `2f9a818e` localizes the ready-phrases list name. The `0a3e21a0` follow-up scopes Mini App lesson cache and in-flight fetches by `localUserScope`; an identity change rejects a pending fetch before it can return or cache. Local Chromium smoke for the dictionary, subscription and ready phrases passed previously; this cache change has a Node runtime regression but not device account-switch QA.
- **P3 display-only:** `localization/lessons/nhsk2_grammar_uz_ru_tj.tsv` holds 136 unique Chinese grammar contexts × 3 locales = 408 agent-checked translations, projected into 272 original + 136 mirror maps across 48 `nhsk2` lessons. Original Chinese, pinyin, answers, score, XP and lesson JSON remain unchanged. Mini App patch is returned only after signed `POST /api/v3/lesson/start` approval; native Android/Desktop use existing entitlement-gated service.

## Implemented security checkpoint

- Mini App full lesson content now comes from signed `GET /api/v3/lesson/content/{level}/{lesson_order}`. The endpoint verifies the Telegram identity and canonical account, selected course level, lesson sequence, required HSK1 foundation and shared lesson entitlement; it never consumes quota and sends `Cache-Control: no-store`.
- The old `/course_v3_data/{level}/lesson_*.json` route now returns 404; root JSON access is restricted to the seven curriculum maps. Sales preview, foundation and skip-test use separate projections. Skip-test returns at most six randomized questions, denies skip-ahead and does not grant progress or consume quota. Source/review manifests and contract audits were updated.
- Commit `b887fe08` contains the route change; its GitHub P0 and Backend targeted runs both succeeded. Latest `10cff3b6` P0 passed 368 tests. The current foundation-label Chrome smoke is documented above.

## Main-readiness blockers and next work

- Staging HTTP probe was not executed (0 requests). Real Telegram account-switch, Free/Trial/Pro, old-client refresh, offline and installed Android/WebView/Windows/macOS QA remain open. Do not claim these from source or mocked browser checks.
- P2 UI adoption remains in progress across the remaining classified Mini App/native/Desktop/Bot surfaces. Continue from the surface registry and existing triage; keep exact UZ/RU/TJ legacy fallbacks and do not redo completed slices.
- Continue the remaining P2 adoption and applicable client QA on this feature branch; exact-head P0 is green at `10cff3b6`. Keep `main` and production untouched.

## Verified batches since the previous handoff

- `5df10c73ba7bcb40efdbad323e6db1d007978571`: P2 six foundation/retry/error UI keys, 829 per locale, six deterministic generated client artifacts, 12 cache-pinned HTML pages, reviewed Mini App source SHA and triage anchor. Initial CI `39385983079` **FAILED** because 14 existing test modules still pinned the former key count and asset cache.
- `708bf36f06eaa1e7bf542a4360359d5b858a85d9`: updated those 14 existing test modules to the exact reviewed 829-key catalog and content-hash asset. P0 [39386418096](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39386418096) **SUCCESS, 350 tests**. Failure above is superseded, NOT silently ignored.
- `c864b311977c84c4330f38694e9a3f73221f63d1`: P3 independent Chinese-source check of `G066`/`G069`/`G130`, Russian translation semantics fix in the 136-row canonical TSV, two source-specific regressions, and AI-content QA policy root-cause notes. P0 [39386882825](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39386882825) **SUCCESS, 352 tests**, with six generated resource targets current. No Chinese source, pinyin, answer, lesson access or live deployment change.
- `13eec08465835b7bc0f17b93dbfdaa7b9b2ca5fb`: further P2 Mini App **6 locale keys** (829 → 835 per UZ/RU/TJ) for practice preparing/checking access, foundation save-in-progress/retry/save-error, resource iframe loading; reuse existing `foundation.zeroTitle` for the foundation step label. Seven same-line `courseMessage(key, exactLegacyFallback)` changes in `course-v3.html` at 3196/3202/3836/3844/3846/4950/6970. All 6 generated Android/Mini App/Desktop/Bot resources current, 12 HTML bundle consumers pin `20261020-b147eef277fe`, source review blob and triage updated. New source-bound regression test and 14 existing UI test count/cache expectations updated atomically. [P0 run 39403629877](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39403629877) **SUCCESS, 353 tests, 0 failures**, six generated artifacts 0 stale. No grading, XP, auth, entitlement, payment, or original lesson changes.
- Do not mistake the GitHub-only checks for real Google/Apple/Telegram login, Free/Trial/Pro/payment, Android/Mini App/Desktop offline or migration E2E success. Run applicable authenticated tests before release.

## Next precise tasks (in this order)

1. Finish and push the tested main-sync/P0-hardening batch to the feature branch only; check exact-head Actions.
2. Continue P2 after the 8-key slice: audit remaining Mini App expressions, then inspect Android/native, Desktop and Bot consumers for untranslated UI. Use exact source context plus local catalog lookups and exact inline fallbacks.
3. On each catalog batch regenerate six artifacts, update all 12 cache URLs and exact-count/hash tests, then rerun P0 on the exact SHA.
4. Resolve or formally classify public lesson-data access and account-scoped cache findings without weakening Pro/free checks or breaking legacy clients; complete applicable staging and installed-client QA.
5. Continue source-context QA for all 136 P3 contexts and 408 values, and keep source SHA, mirror, entitlement and protected-answer guards.
6. Update this file and `P3_ACTIVE_HANDOFF.md` with each actual commit and Actions result. Never reuse earlier CI for a newer SHA.

## Read before coding

`AGENTS.md`, `AI_RULES.md`, `PROJECT_MEMORY.md`, `localization/AI_CONTENT_QA_POLICY.md`, `localization/P3_ACTIVE_HANDOFF.md`, `localization/PLAN_SCHEMA_ORDER.md`, `localization/surface_registry.json`. `localization/NEXT_CHAT_HANDOFF.md` is historical, not latest.

**Do not infer a clean local working tree, deployment, migration success, or production availability from GitHub-only commit/CI inspection.**
