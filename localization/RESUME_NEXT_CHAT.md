# HSK AI Local-First i18n — RESUME NEXT CHAT

Updated: 2026-10-20. **This is the short authoritative checkpoint, not evidence of production release.**

## Git and protected scope

- Repository: `akbarholturaev11-lang/HSK-AI-Bot`.
- **ONLY active work branch:** `codex/p3-main-integration-20261020`.
- **Last verified integration HEAD before this docs-only handoff commit:** `33e14d811b96cbcb11288628bc2aa368622bf69e`.
- `main` HEAD at audit: `055de820db10b32fadffa942938a16e2070f0d52`. **Do NOT push/merge `main`, force-push, rebase, deploy production or run real production migrations.**
- Old source branch `codex/i18n-local-first-foundation-20261017` is already merged into the integration branch; **do not redo the merge**. Historical Draft PR #179 is not a release authorization.
- GitHub Actions: [exact-head P0 SUCCESS run 39373684091](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39373684091) **349 tests, 0 failures**, 811 frozen source files / 746 lessons, 13 exact current-main SHA exceptions, 0 blockers, 6 classified Mini App lesson-load callsites, 0 stale generated local catalogs.
- New agent **must re-read actual integration HEAD and its latest exact-head CI**: docs-only commits may advance the SHA. Do not call backend/native/live-device tests passed solely from P0.

## Implemented local-first i18n

- **P0/P1:** source baselines and deterministic UZ/RU/TJ catalogs/generators; per-string translations do not require AI requests or runtime server fetches. Generated bundle parity checks are green.
- **P2 ongoing:** `localization/ui/{uz,ru,tj}/course.json` has **823 course UI keys per language**. Static/local bundles exist for Android, Mini App, Desktop and Bot. Current scoped migrations include provider-specific avatar help, login verification time, referral and Pro receipt copy, lesson-settings dialog accessibility, and **8 rating/social/duel messages across 9 Mini App locations**. Legacy locale strings remain fallbacks; auth/payment/rating/duel/scoring logic is untouched.
- All **12 HTML consumers** of `hsk-course-i18n.js` use content-addressed query `?v=20261020-1fee76a7803b`. New regression asserts this matches the real bundled blob; bump **all 12** when changing the course locale catalog.
- **P3 protected display-only:** `localization/lessons/nhsk2_grammar_uz_ru_tj.tsv` stores 136 unique Chinese-context rows × 3 locales = 408 independent translations, projected into 272 original plus 136 mirrored grammar display maps across 48 nHSK2 lessons. Chinese, pinyin, answers, score, XP and original lesson JSON are never rewritten by these translations.
- P3 source-bound tests check all patch locations and additional precise semantics (G001/G003 experience/negation; G013/G015/G017 movement direction). A full independent 136-context semantic audit is **not** yet certified.
- Mini App P3 local patch may be sent **only after** signed `POST /api/v3/lesson/start` authorization. Ordinary allowed start: `consume=True`; already completed `review_only`: existing server progress and `consume=False`; explicit 401/403/denial must never return translation data. Native Android/Desktop read path applies verified display-only localization only after entitlement.

## Next precise tasks (in this order)

1. Continue **P2 scoped, context-exact UI migration**, starting with Mini App foundation/retry/error-recovery messages in `app/static/course-v3.html` (roughly source lines 3762–3769, 4073, 4127). Map each UZ/RU/TJ literal to a new stable `courseMessage(key, exactLegacyFallback)`, preserving behavior. The existing line-anchored triage `localization/review/miniapp_course_hotspot_triage.json` and reviewed baseline Git SHA must remain exact. Prefer minimal same-line edits.
2. Regenerate ALL six course artifacts using `scripts/i18n_build_course_catalogs.py`, keep 3-locale parity; update 12 HTML bundle URLs to the new content SHA and associated exact tests. **Do not overwrite mismatched context text.** Run `Local-first localization P0 guards` GitHub Actions on the integration branch until green; verify exact SHA.
3. Continue source-bound **P3 linguistic review** by comparing the actual Chinese example/rule and each UZ/RU/TJ row independently under `localization/AI_CONTENT_QA_POLICY.md`. Preserve duplicate/mirror identity; add a focused regression for each documented correction, no source/answer mutation or unreviewed public locale pack. User has delegated linguistic QA to the agent.
4. Audit full backend/account and entitlement pathways against the latest integration HEAD and run authenticated provider-only Google/Apple/Telegram + old user, Free/Trial/Pro, payment/referral tests where approved QA identities/infrastructure are available. Request/verify real Android, Mini App WebView, Windows/macOS offline rendering and production-schema-like isolated migration rehearsal before any release claim. **P0 green is NOT real-device or provider-E2E success.**
5. Update this checkpoint and `P3_ACTIVE_HANDOFF.md` after verified code + CI. Keep `main` untouched.

## Read before coding

`AGENTS.md`, `AI_RULES.md`, `PROJECT_MEMORY.md`, `localization/AI_CONTENT_QA_POLICY.md`, `localization/P3_ACTIVE_HANDOFF.md`, `localization/PLAN_SCHEMA_ORDER.md`, `localization/surface_registry.json`. `localization/NEXT_CHAT_HANDOFF.md` is historical, not latest.

**Do not infer a clean local working tree, deployment, migration success, or production availability from GitHub-only commit/CI inspection.**
