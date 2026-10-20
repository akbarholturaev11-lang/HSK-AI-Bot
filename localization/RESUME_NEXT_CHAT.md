# HSK AI Local-First i18n — RESUME NEXT CHAT

Updated: 2026-10-21. **This is the short authoritative checkpoint, not evidence of main/production release.**

## Git and protected scope

- Repository: `akbarholturaev11-lang/HSK-AI-Bot`.
- **ONLY active work branch:** `codex/p3-main-integration-20261020`; latest code commit: `f3e2bddfb9833a1960bff3884b4491fb2a1a1ade`; latest pushed handoff HEAD: `678978baa6266fa05973c58bc8011b2800c2bc47`.
- `origin/main` is `ed527c55eaf8d63acd04902b570c6a66aef8fe3c`, an ancestor of this branch. No main merge/push, force-push or production deployment. Draft PR #179 still targets the old `codex/i18n-local-first-foundation-20261017` head and is conflicting; it is not this integration branch or release authorization.
- Exact-head GitHub Actions at `678978baa6266fa05973c58bc8011b2800c2bc47`: P0 [39473731653](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39473731653), Backend [39473732052](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39473732052), Android [39473840883](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39473840883), and Desktop [39473841418](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39473841418) all **SUCCESS**.
- Local P0 workflow-equivalent after `f3e2bddf`: **386 tests passed**; **25 read-only audits passed**. Inventory: 2,717 files, 71,125 locale maps, 0 parse/read errors; 812 frozen sources, 746 lessons, 0 baseline blockers; 48 source gaps all covered by 2,094 valid locale overlays. No staging, authenticated-user or installed-device QA is inferred from these checks.
- Unrelated local `graphify-out/GRAPH_REPORT.md` and `graphify-out/graph.json` changes are user-owned; keep them out of commits.


## Implemented local-first i18n

- **P0/P1:** source baselines and deterministic UZ/RU/TJ catalogs/generators; no per-string AI/server calls. Current course UI catalog has **895 keys per locale**, and the common UI catalog has **126 keys per locale**; each generator writes six local artifacts for Android, Mini App, Desktop and Bot. All 12 course HTML bundle consumers use `?v=20261020-57ce728d755d`; six common and six course artifacts are current.
- **Latest Android P2:** `f6234483` switches three remaining exact UZ/RU/TJ Android label copies—profile lesson count, Telegram identity label and Voice call accessibility label—to existing generated local resources. The old XML translations remain exact fallbacks; a 40-entry parity/call-site regression guards reuse. Earlier commits `df004ba6`, `c9edc41c`, and `2f9a818e` cover dictionary plural messages, subscription close names and the ready-phrases list. The `0a3e21a0` follow-up scopes Mini App lesson cache and in-flight fetches by `localUserScope`; account-switch behavior still needs real-client QA.
- **P3 display-only:** `localization/lessons/nhsk2_grammar_uz_ru_tj.tsv` holds 136 unique Chinese grammar contexts × 3 locales = 408 agent-checked translations, projected into 272 original + 136 mirror maps across 48 `nhsk2` lessons. Original Chinese, pinyin, answers, score, XP and lesson JSON remain unchanged. Mini App patch is returned only after signed `POST /api/v3/lesson/start` approval; native Android/Desktop use existing entitlement-gated service.
- **Latest UI batches (`7dedd1d8`, `7fc9dc82`, `f3e2bddf`):** existing Bot promo/course/menu/practice/onboarding labels and Android badges remain centralized. The last six Bot subscription button labels now resolve from the common local catalog with exact UZ/RU/TJ wording and callbacks preserved. No UI screens were rebuilt and no account, course, access, payment, score or progress behavior changed.

## Implemented security checkpoint

- Mini App full lesson content now comes from signed `GET /api/v3/lesson/content/{level}/{lesson_order}`. The endpoint verifies the Telegram identity and canonical account, selected course level, lesson sequence, required HSK1 foundation and shared lesson entitlement; it never consumes quota and sends `Cache-Control: no-store`.
- The old `/course_v3_data/{level}/lesson_*.json` route now returns 404; root JSON access is restricted to the seven curriculum maps. Sales preview, foundation and skip-test use separate projections. Skip-test returns at most six randomized questions, denies skip-ahead and does not grant progress or consume quota. Source/review manifests and contract audits were updated.
- Commit `b887fe08` contains the route change; its GitHub P0 and Backend targeted runs both succeeded. Latest `10cff3b6` P0 passed 368 tests. The current foundation-label Chrome smoke is documented above.

## Main-readiness blockers and next work

- Staging HTTP probe was not executed (0 requests). Real Telegram account-switch, Free/Trial/Pro, old-client refresh, offline and installed Android/WebView/Windows/macOS QA remain open. Do not claim these from source or mocked browser checks.
- The registered Mini App sweep checked all 18 selected UZ/RU/TJ page-local dictionaries: locale key counts match, with 0 parser or placeholder drift. Existing pages load local catalogs before applying copy and set accessibility attributes from the selected locale; the P0 adoption tests cover these paths. No further exact-copy Mini App patch was identified in this pass.
- **Remaining release gates:** the user’s real Telegram bot test, staging HTTP/authenticated account and Free/Trial/Pro/payment/referral checks, old-client refresh, offline and installed Android/WebView/Windows/macOS QA remain. The user plans an independent linguistic audit after code work; this must not be confused with source CI. Keep `main` and production untouched.

## Verified batches since the previous handoff

- `e8ba499949a18ea6a13b9aa97cf20bb9f79966be`: Bot account-deletion flow now uses the saved account language and local common catalog; focused backend tests passed, with no deletion/retention flow changes.
- `7dedd1d8f5ae86ab16f5e88e72525cebd607ef79`: localized Bot promo course fallback and stale-button alert; routed two Android badges through the existing course resource; added local/runtime/P0 regressions. Local P0 **383 tests** and 25 read-only audits passed; GitHub P0 39454276931, Backend 39454276998 and Desktop UI 39454355280 passed. Android run 39454355696 first failed because an instrumentation test still referenced the removed unused `newBadge` property.
- `7fc9dc8249816565750d1ac3f629003e2a90ef03`: updated that instrumentation test to use the localized resource. Exact-head P0 39455687320, Android 39455710809 (build/test/lint, Direct/Play emulator regressions and unsigned release bundles), Backend 39458523003 and Desktop UI 39458522328 all **SUCCESS**. Local Gradle could not run here because this worktree has no Android SDK; GitHub Android CI compiled and verified both variants.

- `f62344838cf18884c1809e262469ee0f273bcacc`: Android profile lessons, Telegram identity and Voice call labels now use existing generated local catalog resources; exact legacy UZ/RU/TJ resources are retained. P0-equivalent local run: **370 tests passed**; Play and Direct Kotlin compile succeeded. Exact-head GitHub P0 [39438909149](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39438909149) **SUCCESS**. No account, access, lesson, grading or payment behavior changed.

- `baa0baaa7e92732fd22cf6ada6c00d7a32eabf69`: Desktop P2 local-first migration for 24 exact existing UZ/RU/TJ sign-in labels. Desktop `t()` now resolves them from the generated common bundle and retains its original locale dictionaries as fallback; no auth state/API changes. Common catalog grows 20 → 44 keys per locale; six artifacts regenerated. Exact-source parity tests and reviewed Desktop source SHA updated. Local P0 equivalent: **368 tests passed**; all read-only audits passed with 0 baseline blockers and 0 stale artifacts. Exact-head GitHub P0 [39430791418](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39430791418) **SUCCESS**.

- `5df10c73ba7bcb40efdbad323e6db1d007978571`: P2 six foundation/retry/error UI keys, 829 per locale, six deterministic generated client artifacts, 12 cache-pinned HTML pages, reviewed Mini App source SHA and triage anchor. Initial CI `39385983079` **FAILED** because 14 existing test modules still pinned the former key count and asset cache.
- `708bf36f06eaa1e7bf542a4360359d5b858a85d9`: updated those 14 existing test modules to the exact reviewed 829-key catalog and content-hash asset. P0 [39386418096](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39386418096) **SUCCESS, 350 tests**. Failure above is superseded, NOT silently ignored.
- `c864b311977c84c4330f38694e9a3f73221f63d1`: P3 independent Chinese-source check of `G066`/`G069`/`G130`, Russian translation semantics fix in the 136-row canonical TSV, two source-specific regressions, and AI-content QA policy root-cause notes. P0 [39386882825](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39386882825) **SUCCESS, 352 tests**, with six generated resource targets current. No Chinese source, pinyin, answer, lesson access or live deployment change.
- `13eec08465835b7bc0f17b93dbfdaa7b9b2ca5fb`: further P2 Mini App **6 locale keys** (829 → 835 per UZ/RU/TJ) for practice preparing/checking access, foundation save-in-progress/retry/save-error, resource iframe loading; reuse existing `foundation.zeroTitle` for the foundation step label. Seven same-line `courseMessage(key, exactLegacyFallback)` changes in `course-v3.html` at 3196/3202/3836/3844/3846/4950/6970. All 6 generated Android/Mini App/Desktop/Bot resources current, 12 HTML bundle consumers pin `20261020-b147eef277fe`, source review blob and triage updated. New source-bound regression test and 14 existing UI test count/cache expectations updated atomically. [P0 run 39403629877](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39403629877) **SUCCESS, 353 tests, 0 failures**, six generated artifacts 0 stale. No grading, XP, auth, entitlement, payment, or original lesson changes.
- Do not mistake the GitHub-only checks for real Google/Apple/Telegram login, Free/Trial/Pro/payment, Android/Mini App/Desktop offline or migration E2E success. Run applicable authenticated tests before release.

## Next precise tasks (in this order)

1. Run the user’s real Telegram bot test and fix any reproducible issue it reveals; rerun the affected tests and P0. The latest registered Mini App source-to-catalog sweep found no additional exact-copy migration in the 18 reviewed page dictionaries.
2. After code work, run the independent linguistic audit the user plans for all 136 source-pinned grammar contexts; fix any findings, keep mirror/source guards intact, and rerun P0.
3. Complete authenticated staging/account/access, old-client, offline and installed Android/WebView/Windows/macOS QA when the test environment and identities are available. These remain outside the verified GitHub CI.
4. Before any main release, recheck current main ancestry and exact-head Actions. Keep main and production untouched until the user separately authorizes the release.

## Read before coding

`AGENTS.md`, `AI_RULES.md`, `PROJECT_MEMORY.md`, `localization/AI_CONTENT_QA_POLICY.md`, `localization/P3_ACTIVE_HANDOFF.md`, `localization/PLAN_SCHEMA_ORDER.md`, `localization/surface_registry.json`. `localization/NEXT_CHAT_HANDOFF.md` is historical, not latest.

**Do not infer a clean local working tree, deployment, migration success, or production availability from GitHub-only commit/CI inspection.**
