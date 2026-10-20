# HSK AI Local-First i18n — RESUME NEXT CHAT

Updated: 2026-10-20. **This is the short authoritative checkpoint, not evidence of production release.**

## Git and protected scope

- Repository: `akbarholturaev11-lang/HSK-AI-Bot`.
- **ONLY active work branch:** `codex/p3-main-integration-20261020`.
- Current committed feature head before this local batch: `ce427ab2e21b4dbcd2c4ea15b7cc66caf46e77e2`. Exact-head [P0 run 39411930645](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39411930645) is SUCCESS; Android run `39411943307` is in progress (backend adapter job passed; Android unit tests and lint passed; emulator/build steps were still running at last check).
- `origin/main` at latest fetch: `16cc47cddbed62f75850db41b89b8be2ec6709d7`, **one commit ahead**. It adds public-site traffic analytics and migration `0109`; dry merge reports no content conflict, but the feature branch still needs synchronization and re-testing. **Do NOT push/merge into `main`, force-push, rebase, deploy production or run real production migrations.**
- Old source branch `codex/i18n-local-first-foundation-20261017` is already merged into the integration branch; **do not redo the merge**. Historical Draft PR #179 is not a release authorization.
- The current local P2 batch has not been pushed; its exact-head GitHub CI must be checked after the feature-branch push. Never reuse `ce427ab2` results for the changed worktree.
- New agent **must re-read actual integration HEAD and its latest exact-head CI**: docs-only commits may advance the SHA. Do not call backend/native/live-device tests passed solely from P0.

## Implemented local-first i18n

- **P0/P1:** source baselines and deterministic UZ/RU/TJ catalogs/generators; per-string translations do not require AI requests or runtime server fetches. Generated bundle parity checks are green.
- **P2 ongoing:** current local catalogs contain **874 course UI keys per language**. The prior committed 31-key slice (835 → 866) is followed by a local eight-key repair-copy batch for guided/foundation repair and lesson encouragement. Static/local bundles are generated for Android, Mini App, Desktop and Bot; original Mini App copy remains the fallback. No assessment, access, payment or account logic changed.
- All **12 HTML consumers** of `hsk-course-i18n.js` currently use `?v=20261020-ed284a21dc2c`, matching the generated bundle Git blob prefix. Local batch is still uncommitted/unpushed at this checkpoint.

- **P3 protected display-only:** `localization/lessons/nhsk2_grammar_uz_ru_tj.tsv` stores 136 unique Chinese-context rows × 3 locales = 408 independent translations, projected into 272 original plus 136 mirrored grammar display maps across 48 nHSK2 lessons. Chinese, pinyin, answers, score, XP and original lesson JSON are never rewritten by these translations.
- P3 source-bound tests check all patch locations and additional precise semantics (G001/G003 experience/negation; G013/G015/G017 movement direction). Source-verified corrections also cover G019/G023/G135 and G066/G069/G130. The agent has checked all 136 Chinese grammar contexts and all 408 UZ/RU/TJ strings; this is documented agent QA, not third-party or native-speaker certification. Do not ask the user to review Chinese. Real authenticated/device QA remains separate.
- Mini App P3 local patch may be sent **only after** signed `POST /api/v3/lesson/start` authorization. Ordinary allowed start: `consume=True`; already completed `review_only`: existing server progress and `consume=False`; explicit 401/403/denial must never return translation data. Native Android/Desktop read path applies verified display-only localization only after entitlement.

## Current working batch (local checks passed; feature push and exact-head CI pending)

- Added 8 UZ/RU/TJ course UI keys and same-line `courseMessage` lookups for guided repair, foundation repair reminder and lesson encouragement in `app/static/course-v3.html`. All six generated artifacts are current; all 12 cache URLs now pin `20261020-ed284a21dc2c`; exact-count/hash tests, reviewed source SHA (`fb0a874ba8a2235924c3ac3a6c2d7ff799fcd13d`) and triage were updated. HTML remains 8,858 lines.
- Exact P0 workflow unittest list: **356 tests passed**. Read-only audit scripts report 811 frozen sources, 746 lessons, 0 baseline blockers, 874 UI keys and six current generated artifacts. Mobile Chromium at 390×844 exercised the affected states in UZ/RU/TJ: no horizontal overflow or console errors. Local Android `testPlayDebugUnitTest` and `testDirectDebugUnitTest` both passed. These are local results only; new batch has no remote run yet.
- P3 language work: the agent has read all 136 distinct Chinese grammar contexts and checked all 408 UZ/RU/TJ strings; the prior G019/G023/G135 and G066/G069/G130 corrections remain source-bound. This is documented agent QA, not native-speaker certification. Runtime translations are already delivered as display-only overlays after the authenticated access boundary; source lesson JSON, answers and grading stay unchanged.
- P0 still flags 48 source lessons with incomplete locale maps (272 original display maps plus 136 mirrors, backed by 2,094 overlays), public lesson JSON/curriculum routes for entitlement review, and unscoped Mini App lesson/resume caches for account-switch review. The staging HTTP probe was not run (0 requests). These are not resolved by P0 or local UI smoke.

## Verified batches since the previous handoff

- `5df10c73ba7bcb40efdbad323e6db1d007978571`: P2 six foundation/retry/error UI keys, 829 per locale, six deterministic generated client artifacts, 12 cache-pinned HTML pages, reviewed Mini App source SHA and triage anchor. Initial CI `39385983079` **FAILED** because 14 existing test modules still pinned the former key count and asset cache.
- `708bf36f06eaa1e7bf542a4360359d5b858a85d9`: updated those 14 existing test modules to the exact reviewed 829-key catalog and content-hash asset. P0 [39386418096](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39386418096) **SUCCESS, 350 tests**. Failure above is superseded, NOT silently ignored.
- `c864b311977c84c4330f38694e9a3f73221f63d1`: P3 independent Chinese-source check of `G066`/`G069`/`G130`, Russian translation semantics fix in the 136-row canonical TSV, two source-specific regressions, and AI-content QA policy root-cause notes. P0 [39386882825](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39386882825) **SUCCESS, 352 tests**, with six generated resource targets current. No Chinese source, pinyin, answer, lesson access or live deployment change.
- `13eec08465835b7bc0f17b93dbfdaa7b9b2ca5fb`: further P2 Mini App **6 locale keys** (829 → 835 per UZ/RU/TJ) for practice preparing/checking access, foundation save-in-progress/retry/save-error, resource iframe loading; reuse existing `foundation.zeroTitle` for the foundation step label. Seven same-line `courseMessage(key, exactLegacyFallback)` changes in `course-v3.html` at 3196/3202/3836/3844/3846/4950/6970. All 6 generated Android/Mini App/Desktop/Bot resources current, 12 HTML bundle consumers pin `20261020-b147eef277fe`, source review blob and triage updated. New source-bound regression test and 14 existing UI test count/cache expectations updated atomically. [P0 run 39403629877](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39403629877) **SUCCESS, 353 tests, 0 failures**, six generated artifacts 0 stale. No grading, XP, auth, entitlement, payment, or original lesson changes.
- Do not mistake the GitHub-only checks for real Google/Apple/Telegram login, Free/Trial/Pro/payment, Android/Mini App/Desktop offline or migration E2E success. Run applicable authenticated tests before release.

## Next precise tasks (in this order)

1. Finish and push the current local batch to the feature branch only; check exact-head Actions. Then synchronize `origin/main`'s `0109` traffic migration into the feature branch and rerun applicable CI.
2. Continue P2 after the 8-key slice: audit remaining Mini App expressions, then inspect Android/native, Desktop and Bot consumers for untranslated UI. Use exact source context plus local catalog lookups and exact inline fallbacks.
3. On each catalog batch regenerate six artifacts, update all 12 cache URLs and exact-count/hash tests, then rerun P0 on the exact SHA.
4. Resolve or formally classify public lesson-data access and account-scoped cache findings without weakening Pro/free checks or breaking legacy clients; complete applicable staging and installed-client QA.
5. Continue source-context QA for all 136 P3 contexts and 408 values, and keep source SHA, mirror, entitlement and protected-answer guards.
6. Update this file and `P3_ACTIVE_HANDOFF.md` with each actual commit and Actions result. Never reuse earlier CI for a newer SHA.

## Read before coding

`AGENTS.md`, `AI_RULES.md`, `PROJECT_MEMORY.md`, `localization/AI_CONTENT_QA_POLICY.md`, `localization/P3_ACTIVE_HANDOFF.md`, `localization/PLAN_SCHEMA_ORDER.md`, `localization/surface_registry.json`. `localization/NEXT_CHAT_HANDOFF.md` is historical, not latest.

**Do not infer a clean local working tree, deployment, migration success, or production availability from GitHub-only commit/CI inspection.**
