# HSK AI Local-First i18n — RESUME NEXT CHAT

Updated: 2026-10-20. **This is the short authoritative checkpoint, not evidence of production release.**

## Git and protected scope

- Repository: `akbarholturaev11-lang/HSK-AI-Bot`.
- **ONLY active work branch:** `codex/p3-main-integration-20261020`.
- **Last verified CODE HEAD before this handoff update:** `c864b311977c84c4330f38694e9a3f73221f63d1` (P2 recovery and P3 language corrections). The later documentation commit will advance branch HEAD; verify its exact-head workflow separately..
- `main` HEAD at audit: `055de820db10b32fadffa942938a16e2070f0d52`. **Do NOT push/merge `main`, force-push, rebase, deploy production or run real production migrations.**
- Old source branch `codex/i18n-local-first-foundation-20261017` is already merged into the integration branch; **do not redo the merge**. Historical Draft PR #179 is not a release authorization.
- GitHub Actions: [exact-code-head P0 SUCCESS run 39386882825](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39386882825) **352 tests, 0 failures**, 811 frozen source files / 746 lessons, 13 exact current-main SHA exceptions, 0 blockers, 6 classified Mini App lesson-load callsites, 0 stale generated local catalogs.
- New agent **must re-read actual integration HEAD and its latest exact-head CI**: docs-only commits may advance the SHA. Do not call backend/native/live-device tests passed solely from P0.

## Implemented local-first i18n

- **P0/P1:** source baselines and deterministic UZ/RU/TJ catalogs/generators; per-string translations do not require AI requests or runtime server fetches. Generated bundle parity checks are green.
- **P2 ongoing:** `localization/ui/{uz,ru,tj}/course.json` has **829 course UI keys per language**. Static/local bundles exist for Android, Mini App, Desktop and Bot. Current scoped migrations include provider-specific avatar help, login verification time, referral and Pro receipt copy, lesson-settings dialog accessibility, and **8 rating/social/duel messages across 9 Mini App locations, plus 6 foundation/load/retry/error-recovery keys at Mini App lines 3762/3768/3769/4073/4127**. Legacy locale strings remain fallbacks; auth/payment/rating/duel/scoring logic is untouched.
- All **12 HTML consumers** of `hsk-course-i18n.js` use content-addressed query `?v=20261020-1f256761e2c5`. New regression asserts this matches the real bundled blob; bump **all 12** when changing the course locale catalog.
- **P3 protected display-only:** `localization/lessons/nhsk2_grammar_uz_ru_tj.tsv` stores 136 unique Chinese-context rows × 3 locales = 408 independent translations, projected into 272 original plus 136 mirrored grammar display maps across 48 nHSK2 lessons. Chinese, pinyin, answers, score, XP and original lesson JSON are never rewritten by these translations.
- P3 source-bound tests check all patch locations and additional precise semantics (G001/G003 experience/negation; G013/G015/G017 movement direction). Source-verified corrections now additionally cover G066/G069 (waiting does not guarantee arrival) and G130 (Li Wen sees Yang Tongle, not a reciprocal meeting); 3 Russian cells, 2 new focused regressions. Earlier whole-catalog first-pass review is documented in AI_CONTENT_QA_POLICY.md; a new full Chinese-source, all-408-cell independent certification plus real-client QA are **not** yet complete.
- Mini App P3 local patch may be sent **only after** signed `POST /api/v3/lesson/start` authorization. Ordinary allowed start: `consume=True`; already completed `review_only`: existing server progress and `consume=False`; explicit 401/403/denial must never return translation data. Native Android/Desktop read path applies verified display-only localization only after entitlement.

## Verified batches since the previous handoff

- `5df10c73ba7bcb40efdbad323e6db1d007978571`: P2 six foundation/retry/error UI keys, 829 per locale, six deterministic generated client artifacts, 12 cache-pinned HTML pages, reviewed Mini App source SHA and triage anchor. Initial CI `39385983079` **FAILED** because 14 existing test modules still pinned the former key count and asset cache.
- `708bf36f06eaa1e7bf542a4360359d5b858a85d9`: updated those 14 existing test modules to the exact reviewed 829-key catalog and content-hash asset. P0 [39386418096](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39386418096) **SUCCESS, 350 tests**. Failure above is superseded, NOT silently ignored.
- `c864b311977c84c4330f38694e9a3f73221f63d1`: P3 independent Chinese-source check of `G066`/`G069`/`G130`, Russian translation semantics fix in the 136-row canonical TSV, two source-specific regressions, and AI-content QA policy root-cause notes. P0 [39386882825](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39386882825) **SUCCESS, 352 tests**, with six generated resource targets current. No Chinese source, pinyin, answer, lesson access or live deployment change.
- Do not mistake the GitHub-only checks for real Google/Apple/Telegram login, Free/Trial/Pro/payment, Android/Mini App/Desktop offline or migration E2E success. Run applicable authenticated tests before release.

## Next precise tasks (in this order)

1. Continue P2 beyond the **completed** foundation/retry/error recovery slice: audit remaining inline UZ/RU/TJ texts in `app/static/course-v3.html` (use `localization/review/miniapp_course_hotspot_triage.json`), then Android/native, Desktop and Bot consumers. For every new batch, use exact source-context + `courseMessage(key, exactLegacyFallback)`, update reviewed source blob/SHA and triage classification; preserve physical line anchors.
2. On every changed UI catalog, regenerate the same six artifacts with `scripts/i18n_build_course_catalogs.py`, update all 12 HTML content-addressed asset URLs and ALL affected exact-count/cache regression tests. Run P0 CI on the exact branch SHA until green.
3. Continue independently cross-checking the actual Chinese grammar, 136 unique P3 contexts and all UZ/RU/TJ rows, including repeat/mirror pointers. The documented `G066/G069/G130` RU fixes and earlier focused corrections are verified by source-bound tests, not proof of complete independent 408-value certification. Keep source SHA, mirror/entitlement and protected-answer guards.
4. Run separate approved QA against Google/Apple/Telegram provider-only and old users; Free/Trial/Pro, referral/payment, real Mini App/WebView, Android, Windows/macOS offline and isolated production-shaped migrations. No release or `main` merge without the owner authorizing it and those acceptance gates passing.
5. Update this file and `P3_ACTIVE_HANDOFF.md` after each verified batch, including actual CI run numbers. Never reuse an earlier workflow conclusion for a newer SHA.

## Read before coding

`AGENTS.md`, `AI_RULES.md`, `PROJECT_MEMORY.md`, `localization/AI_CONTENT_QA_POLICY.md`, `localization/P3_ACTIVE_HANDOFF.md`, `localization/PLAN_SCHEMA_ORDER.md`, `localization/surface_registry.json`. `localization/NEXT_CHAT_HANDOFF.md` is historical, not latest.

**Do not infer a clean local working tree, deployment, migration success, or production availability from GitHub-only commit/CI inspection.**
