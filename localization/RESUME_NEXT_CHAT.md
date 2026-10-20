# HSK AI Local-First i18n — RESUME NEXT CHAT

Updated: 2026-10-20. **This is the short authoritative checkpoint, not evidence of production release.**

## Git and protected scope

- Repository: `akbarholturaev11-lang/HSK-AI-Bot`.
- **ONLY active work branch:** `codex/p3-main-integration-20261020`.
- **Last committed exact-head CI before this working batch:** `8c708a5e4149973a89650b8bb2a8e58a788c1550`; [P0 run 39403997281](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39403997281) SUCCESS. This handoff’s local P2 code changes are not yet in that run; rerun CI on the pushed exact SHA.
- `origin/main` at latest fetch: `055de820db10b32fadffa942938a16e2070f0d52`; it is an ancestor of this integration branch (0 commits behind). **Do NOT push/merge `main`, force-push, rebase, deploy production or run real production migrations.**
- Old source branch `codex/i18n-local-first-foundation-20261017` is already merged into the integration branch; **do not redo the merge**. Historical Draft PR #179 is not a release authorization.
- GitHub Actions: [exact-code-head P0 SUCCESS run 39403997281](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39403997281) for `8c708a5e`; current working batch still needs its own remote exact-head run.
- New agent **must re-read actual integration HEAD and its latest exact-head CI**: docs-only commits may advance the SHA. Do not call backend/native/live-device tests passed solely from P0.

## Implemented local-first i18n

- **P0/P1:** source baselines and deterministic UZ/RU/TJ catalogs/generators; per-string translations do not require AI requests or runtime server fetches. Generated bundle parity checks are green.
- **P2 ongoing:** `localization/ui/{uz,ru,tj}/course.json` now has **866 course UI keys per language**. Static/local bundles exist for Android, Mini App, Desktop and Bot. Prior provider/auth/referral/Pro/settings/rating/recovery slices remain; this batch adds **31** local-first Mini App messages, including countdown formats for rank movement, lesson labels, exit-ticket and repair prompts, voice quota, referral/invite flows, duel cooldown, profile level and test-limit loading. Existing locale wording stays as fallback; score, answers, auth, entitlement, billing and referral calculations are unchanged.
- All **12 HTML consumers** of `hsk-course-i18n.js` now use content-addressed query `?v=20261020-b5bc4adb441e`, matching the generated bundle’s Git blob hash prefix.

- **P3 protected display-only:** `localization/lessons/nhsk2_grammar_uz_ru_tj.tsv` stores 136 unique Chinese-context rows × 3 locales = 408 independent translations, projected into 272 original plus 136 mirrored grammar display maps across 48 nHSK2 lessons. Chinese, pinyin, answers, score, XP and original lesson JSON are never rewritten by these translations.
- P3 source-bound tests check all patch locations and additional precise semantics (G001/G003 experience/negation; G013/G015/G017 movement direction). Source-verified corrections also cover G019/G023/G135 and G066/G069/G130. The agent has checked all 136 Chinese grammar contexts and all 408 UZ/RU/TJ strings; this is documented agent QA, not third-party or native-speaker certification. Do not ask the user to review Chinese. Real authenticated/device QA remains separate.
- Mini App P3 local patch may be sent **only after** signed `POST /api/v3/lesson/start` authorization. Ordinary allowed start: `consume=True`; already completed `review_only`: existing server progress and `consume=False`; explicit 401/403/denial must never return translation data. Native Android/Desktop read path applies verified display-only localization only after entitlement.

## Current working batch (local checks passed; push/remote CI pending)

- Added 31 UZ/RU/TJ course UI keys and same-line `courseMessage` lookups in `app/static/course-v3.html`; refreshed all six generated artifacts, all 12 cache URLs, exact-count/hash tests, reviewed source SHA (`ab01cb633f5d9587a1ca21f158c766a0a4cdb065`) and locale-condition triage (61 lines / 128 predicates). The course HTML remains 8,858 lines.
- Local P0 source-contract suite: **354 tests passed**. The first run exposed a duplicated date in 12 exact-cache test expectations; corrected the expectations to match the generated bundle URL, then reran the full workflow successfully. Backend P3/auth/ownership regression selection: **208 passed, 17 skipped**. Read-only guards: 811 frozen sources, 746 lessons, 0 baseline blockers; 866 UI keys and 6 generated resources current. Mobile Chromium smoke ran UZ/RU/TJ with invite sheet visible and 0 console/HTTP errors on a local static adapter (unauthenticated fallback only). GitHub exact-head CI for this batch is pending push.
- P3 language work: the agent has read all 136 distinct Chinese grammar contexts and checked all 408 UZ/RU/TJ strings; the prior G019/G023/G135 and G066/G069/G130 corrections remain source-bound. This is documented agent QA, not native-speaker certification. Runtime translations are already delivered as display-only overlays after the authenticated access boundary; source lesson JSON, answers and grading stay unchanged.
- P0 reports still flag 48 lesson source files with incomplete locale maps, 2 source-level static-route findings requiring security review, and staging HTTP not executed. These are tracked separately; source checks do not prove live entitlement protection.

## Verified batches since the previous handoff

- `5df10c73ba7bcb40efdbad323e6db1d007978571`: P2 six foundation/retry/error UI keys, 829 per locale, six deterministic generated client artifacts, 12 cache-pinned HTML pages, reviewed Mini App source SHA and triage anchor. Initial CI `39385983079` **FAILED** because 14 existing test modules still pinned the former key count and asset cache.
- `708bf36f06eaa1e7bf542a4360359d5b858a85d9`: updated those 14 existing test modules to the exact reviewed 829-key catalog and content-hash asset. P0 [39386418096](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39386418096) **SUCCESS, 350 tests**. Failure above is superseded, NOT silently ignored.
- `c864b311977c84c4330f38694e9a3f73221f63d1`: P3 independent Chinese-source check of `G066`/`G069`/`G130`, Russian translation semantics fix in the 136-row canonical TSV, two source-specific regressions, and AI-content QA policy root-cause notes. P0 [39386882825](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39386882825) **SUCCESS, 352 tests**, with six generated resource targets current. No Chinese source, pinyin, answer, lesson access or live deployment change.
- `13eec08465835b7bc0f17b93dbfdaa7b9b2ca5fb`: further P2 Mini App **6 locale keys** (829 → 835 per UZ/RU/TJ) for practice preparing/checking access, foundation save-in-progress/retry/save-error, resource iframe loading; reuse existing `foundation.zeroTitle` for the foundation step label. Seven same-line `courseMessage(key, exactLegacyFallback)` changes in `course-v3.html` at 3196/3202/3836/3844/3846/4950/6970. All 6 generated Android/Mini App/Desktop/Bot resources current, 12 HTML bundle consumers pin `20261020-b147eef277fe`, source review blob and triage updated. New source-bound regression test and 14 existing UI test count/cache expectations updated atomically. [P0 run 39403629877](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39403629877) **SUCCESS, 353 tests, 0 failures**, six generated artifacts 0 stale. No grading, XP, auth, entitlement, payment, or original lesson changes.
- Do not mistake the GitHub-only checks for real Google/Apple/Telegram login, Free/Trial/Pro/payment, Android/Mini App/Desktop offline or migration E2E success. Run applicable authenticated tests before release.

## Next precise tasks (in this order)

1. Continue P2 after this 31-key slice: audit remaining localized expressions in `app/static/course-v3.html`, then inspect Android/native, Desktop and Bot consumers for untranslated UI. Use exact source-context plus local catalog lookups with the prior wording as fallback; update source SHA, triage and all exact-count/cache tests per batch.
2. On every changed UI catalog, regenerate the same six artifacts with `scripts/i18n_build_course_catalogs.py`, update all 12 HTML content-addressed asset URLs and ALL affected exact-count/cache regression tests. Run P0 CI on the exact branch SHA until green.
3. Continue independently cross-checking the actual Chinese grammar, 136 unique P3 contexts and all UZ/RU/TJ rows, including repeat/mirror pointers. The documented `G066/G069/G130` RU fixes and earlier focused corrections are verified by source-bound tests, not proof of complete independent 408-value certification. Keep source SHA, mirror/entitlement and protected-answer guards.
4. Run separate approved QA against Google/Apple/Telegram provider-only and old users; Free/Trial/Pro, referral/payment, real Mini App/WebView, Android, Windows/macOS offline and isolated production-shaped migrations. No release or `main` merge without the owner authorizing it and those acceptance gates passing.
5. Update this file and `P3_ACTIVE_HANDOFF.md` after each verified batch, including actual CI run numbers. Never reuse an earlier workflow conclusion for a newer SHA.

## Read before coding

`AGENTS.md`, `AI_RULES.md`, `PROJECT_MEMORY.md`, `localization/AI_CONTENT_QA_POLICY.md`, `localization/P3_ACTIVE_HANDOFF.md`, `localization/PLAN_SCHEMA_ORDER.md`, `localization/surface_registry.json`. `localization/NEXT_CHAT_HANDOFF.md` is historical, not latest.

**Do not infer a clean local working tree, deployment, migration success, or production availability from GitHub-only commit/CI inspection.**
