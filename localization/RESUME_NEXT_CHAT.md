# HSK AI Local-First i18n — RESUME NEXT CHAT

Updated: 2026-10-20. **This is the short authoritative checkpoint, not evidence of main/production release.**

## Git and protected scope

- Repository: `akbarholturaev11-lang/HSK-AI-Bot`.
- **ONLY active work branch:** `codex/p3-main-integration-20261020`.
- Local integration HEAD before the current docs/P0-fix batch: `569e321e3c28238880c57793ba5f5bf3ee6dc5f`, merging feature `4b6d52122f55f7886e47ff5e2bbe6f3331628370` with fetched `origin/main` `66ac3d4e94ead8a3c34d45910ffe60f988bf1cf5`. Remote feature still points at `4b6d5212`; do not assume the merge or local edits are pushed.
- Main added public-site traffic analytics and migration `0109`; local `tests.test_public_site_analytics` and `tests.test_main_imports` passed (7 tests) and Alembic reports a single `0109_public_site_traffic_daily` head. Main Android CI `39413938035` and TTS both succeeded on `66ac3d4`. Earlier feature P0 `39413799147` passed on `4b6d5212` (356 tests), Android CI `39411943307` passed on `ce427ab2`.
- **Do NOT push/merge into `main`, force-push, rebase, deploy production or run real production migrations.**
- Old source branch `codex/i18n-local-first-foundation-20261017` is already merged into the integration branch; **do not redo the merge**. Historical Draft PR #179 is not a release authorization.
- The feature merge and current P0 fix batch have not been pushed. Local exact workflow suite passed **358 tests / 64 modules**; exact-head Actions is pending the feature push. Never reuse older SHA results.
- New agent **must re-read actual integration HEAD and its latest exact-head CI**: docs-only commits may advance the SHA. Do not call backend/native/live-device tests passed solely from P0.

## Implemented local-first i18n

- **P0/P1:** source baselines and deterministic UZ/RU/TJ catalogs/generators; per-string translations do not require AI requests or runtime server fetches. Generated bundle parity checks are green.
- **P2 ongoing:** current local catalogs contain **874 course UI keys per language**. The committed eight-key repair-copy batch covers guided/foundation repair and lesson encouragement. Static/local bundles are generated for Android, Mini App, Desktop and Bot; original Mini App copy remains the fallback. No assessment, access, payment or account logic changed.
- All **12 HTML consumers** of `hsk-course-i18n.js` use `?v=20261020-ed284a21dc2c`, matching the generated bundle Git blob prefix.

- **P3 protected display-only:** `localization/lessons/nhsk2_grammar_uz_ru_tj.tsv` stores 136 unique Chinese-context rows × 3 locales = 408 independent translations, projected into 272 original plus 136 mirrored grammar display maps across 48 nHSK2 lessons. Chinese, pinyin, answers, score, XP and original lesson JSON are never rewritten by these translations.
- P3 source-bound tests check all patch locations and additional precise semantics (G001/G003 experience/negation; G013/G015/G017 movement direction). Source-verified corrections also cover G019/G023/G135 and G066/G069/G130. The agent has checked all 136 Chinese grammar contexts and all 408 UZ/RU/TJ strings; this is documented agent QA, not third-party or native-speaker certification. Do not ask the user to review Chinese. Real authenticated/device QA remains separate.
- Mini App P3 local patch may be sent **only after** signed `POST /api/v3/lesson/start` authorization. Ordinary allowed start: `consume=True`; already completed `review_only`: existing server progress and `consume=False`; explicit 401/403/denial must never return translation data. Native Android/Desktop read path applies verified display-only localization only after entitlement.

## Current P0 hardening batch (local verification and feature push pending)

- The committed 8-key P2 batch is `4b6d52122f55f7886e47ff5e2bbe6f3331628370`; exact-head [P0 run 39413799147](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39413799147) succeeded with 356 tests. Mobile Chromium at 390×844 exercised the affected states in UZ/RU/TJ without horizontal overflow or console errors. Local Android Play/Direct unit-test tasks passed.
- This follow-up registers `tests.test_i18n_miniapp_lesson_settings_ui_adoption` in P0 and corrects its stale expected count from 823 to 874. It also advances the reviewed-main exact-source manifest and guard to current `origin/main` `66ac3d4` after verifying `admin.html` is byte-identical to that main blob. The 64-module/358-test local workflow and read-only checks pass; verify Actions at the exact pushed SHA.
- P3 language work: the agent has read all 136 distinct Chinese grammar contexts and checked all 408 UZ/RU/TJ strings; the prior G019/G023/G135 and G066/G069/G130 corrections remain source-bound. This is documented agent QA, not native-speaker certification. Runtime translations are already delivered as display-only overlays after the authenticated access boundary; source lesson JSON, answers and grading stay unchanged.
- P0 still flags 48 source lessons with incomplete locale maps (272 original display maps plus 136 mirrors, backed by 2,094 overlays), public lesson JSON routes that expose answer fields and are not tied to the signed reservation, and unscoped Mini App lesson/resume caches. Curriculum maps expose navigation metadata but no assessment keys. The staging HTTP probe was not run (0 requests). These are not resolved by catalog tests or local UI smoke.

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
