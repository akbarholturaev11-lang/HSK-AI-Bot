# HSK AI P3 — ACTIVE handoff for a new ChatGPT agent
Updated: 2026-10-19. **Current working status is here; historical log remains in `localization/NEXT_CHAT_HANDOFF.md`.**

## 2026-10-20 P3 complete-patch guard and CI evidence

- Code HEAD before this documentation commit: 41b3c8b7023267017c6051eeb4092f7e327b8706. PR #179 remains Draft/dirty; main and production untouched.
- Fix 1df63c4: Mini App JS now derives ALL originally blank grammar and genuine _grammar mirror paths from the loaded lesson; any missing, extra or wrong-card pointer rejects the entire P3 overlay without touching cached/graded source.
- Tests aeefdc7 (partial/misplaced patch) and 3bb4456 (Node-runtime real source + server patch for all 48 lessons, 408 locale display targets). The latter is committed, but its GitHub Actions result is NOT confirmed green.
- Direct GitHub source audit: 48 affected lessons, 272 root blank translation maps + 136 _grammar mirror maps = 408 expected patch rows. Repeated checkpoint lessons may have zero mirror cards.
- Local Node 22 verified exact Git blob a90dfa1a07b585bcb236d85dc815612415417e8c: syntax, complete grant, missing mirror, wrong card, mismatched Chinese and source-cache immutability PASS. Prevention recorded in localization/AI_CONTENT_QA_POLICY.md at 41b3c8b.
- Actions evidence: older P0 39280097210 @62672af and 39281706410 @34d3db0 SUCCESS. Backend run 39281476374 @abddd4b: targeted-tests job 118156968244 and all listed steps SUCCESS, including authenticated native P3 and Mini App ASGI gates; run header still in_progress when observed. P0 run 39283978059 @41b3c8b QUEUED at last check. No full-new-head CI claim.
- Merge conflict still requires coherent reconciliation of main's account_identity.py, 0103–0108 migrations, nullable CourseMiniAppEvent.telegram_id, owner_clause event reads and analytics; no isolated partial cherry-pick or main merge.
- NEXT: check exact-head P0 for 48-case JS test, fix failures, then native/Telegram WebView device E2E, old/Google/Apple/Free/Pro auth, independent 408-text semantic QA and safe identity-schema conflict resolution before merge.

## Follow-up: P3 API regressions and main identity-integration blocker

- Source ref checked: PR #179 HEAD `abddd4b9c76153c115b6bc217c77beb0e5fafdbe`, base main `160a51d69f3324e3162375213ec61b5587b19533`; still Draft, mergeable=false. Keep branch; do not merge/deploy.
- Pushed shared **real** `LessonAccessService.status` test `46ada872` in `tests/test_hsk30_lesson_limits.py`: for a server-completed nhsk2 lesson, a spent free quota remains read-only reviewable when HSK3 track is authorized, but revoked track/disabled level denies P3; `consume=False`, no quota event, no locking SQL.
- Pushed bearer-authenticated FastAPI + in-memory SQLite native Desktop P3 integration test `0ef33a24` (fixture refinement `abddd4b9`) in `tests/test_desktop_course_api.py`: authenticated Pro nhsk2 lesson 16 with completed=15 must return six grammar examples and equivalent localized `_grammar` mirror; anonymous lesson request and lesson-17 skip-ahead must be denied.
- `backend-ci.yml` commit `53fffbd9` adds these targeted real native/entitlement regressions and push path coverage for shared access/native course service changes. This is a **configured gate**, NOT a verified passing CI run. Current connector returns zero workflows/statuses for HEAD (even historical successful commits); obtain actual Actions jobs before declaring green.
- **Identity/merge blocker:** Current `main` added `app/services/account_identity.py` (`owner_clause`) plus `alembic/versions/0103_native_identity_accounts.py` through `0108_native_audit_ownership.py`; its `CourseMiniAppEvent.telegram_id` is nullable and has a new owner+dedupe unique constraint. Feature branch currently lacks that helper/migrations and retains non-null Telegram event metadata and three Telegram-only equality lookups in `DesktopCourseService`. Simply copy-pasting `owner_clause` would crash or violate DB compatibility. Resolve **schema, auth, analytics writes and exact event read/dedupe semantics together**, preserving P3 post-entitlement localization hook; do not transplant only a single source method.
- Read-only comparison also found 119 main-only commits and 27 same-path edit candidates (not all textual conflicts). No main merge, migration or deploy attempted. Exact production/old-account device behavior remains unverified.
- Next: inspect actual new CI jobs; fix real failures if present; run authenticated API integration on genuine old/Google/Apple/Pro/Free fixtures after reconciling identity architecture in a safe integration stage. Follow with Android/Desktop/WebView device QA and source-semantic completion; preserve Draft.

## Session delta: authenticated completed-review hardening + targeted semantic QA

- Live PR HEAD before this documentation write: `f3e343e3e00eb622362858ca1f3f4fd4a5ed00b1`. The doc write advances HEAD; **always re-read** PR before further edits. Draft PR #179 remains `mergeable=false`, main/production untouched.
- API fix `ed9984e`: completed Mini App P3 `review_only` now invokes shared `LessonAccessService.status(..., consume=False)` after signed-auth/server-completion checks, rejecting blocked or unauthorized HSK 3.0 accounts without quota spending. Non-object JSON returns 400 rather than 500.
- Browser fix `f7a46ac`: completed P3 review accepts only explicit `HTTP ok && body.ok && body.allowed`; rejects HTTP errors/malformed success and resets stale P3 patch. True rejected fetch promises retain existing completed-lesson offline reading, without P3.
- Regressions: `73fef49` ASGI auth/quota/revocation/malformed payload; `35032db` Node HTTP denial/stale patch/offline; `4cb2edb`, `f165963`, `78365ec` source-bound semantic checks. Prevention recorded in `localization/AI_CONTENT_QA_POLICY.md` (`f77e216`, `f3e343e`).
- Chinese-context translation fixes: `G030` RU family-vs-house (`3e623de`); `G131` `烤鸭` duck rather than chicken and proper roast UZ/RU/TJ, `G128` natural TJ repeated-visit expression (`bc36689`). All are in canonical TSV; original Chinese/pinyin/lesson JSON untouched.
- Read-only Android/Desktop routing check: Android's `AndroidCourseService.lesson` requires foundation completion and then calls `super().lesson`; the shared Desktop service performs entitlement before `apply_native_grammar_locales`. Both route responses have `Cache-Control:no-store`. This is **source-verified, not emulator/device verified**.
- Current HEAD workflow run query AND combined status query returned **no records**, including on earlier previously successful `c98a04d` code HEAD. This tool's result CANNOT establish CI success/failure for new commits. Do not mark this batch tested green without obtaining actual Actions P0 + Backend run/job results. Real authenticated test account/device/WebView QA remains OPEN.
- Merge prep: compare with `main` found 119 main-only commits and 27 same-path edits across sides, **potential collision candidates only**; the PR reports dirty. No merge, main overwrite, reset, rebase, force-push or deployment was attempted.
- NEXT: obtain and evaluate latest `i18n-p0.yml` and `backend-ci.yml` runs (including synthetic ASGI/Node regressions), fix any failure; finish independent semantic checks against Chinese source for **all 136 contexts**, then run live signed-auth/Free/Pro/HSK30/old account/API and Android/Desktop/WebView/offline tests; resolve the actual merge hunks conservatively and rerun all release gates before main.

## Later same-session source-check and executable runtime evidence

- After the first handoff delta, additional semantic fixes were pushed:
  `G051` Russian preserves the observer `我看` without adding unsupported
  masculine gender; `G109` Uzbek preserves indefinite `一本中文书`.
  Source catalog commits `4c8fa02`, `f5bce78`; targeted regression
  `cfbc37d`, preventive note `14e20ca`.
- The exact committed P3 reservation JS blob `ab2956e4b6a7da339ddb6531b0b5a8acfa8cd291`
  was reconstructed and `git hash-object` checked, then passed Node 22
  syntax and **nine executable isolated VM scenarios** (allow, 401,
  403, HTTP 500, denied/malformed HTTP 200, genuine network offline,
  localized isolated copy, changed-Chinese fail closed).
  This **does not establish latest Actions CI or native device QA**.
- Current main/P3 branch integration is still blocked by Draft PR dirty
  state and new full CI/device/E2E prerequisites. Always re-read HEAD
  before writes; this documentation commit advances it.

## Source of truth and scope

- Repo: `akbarholturaev11-lang/HSK-AI-Bot`.
- Continue existing working branch: `codex/i18n-local-first-foundation-20261017`. Draft PR: https://github.com/akbarholturaev11-lang/HSK-AI-Bot/pull/179.
- Code HEAD inspected when this snapshot was written: `c98a04d8dd778dd255d78e27f091a785938ce983` (**re-read GitHub HEAD** before any write; this handoff's documentation commit will advance it).
- At snapshot: PR #179 **open, Draft, mergeable=false / dirty**. `main` and production have **NOT** received P3. Do not mistake an isolated branch for deployment.
- Exact code-head [P0 run 39274927929](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39274927929): **SUCCESS, 333 tests**, 746 lesson sources / 811 baseline source paths / 0 frozen-source blockers, 3 UI locales / 6 generated course UI assets / 0 stale. Backend targeted workflow [39273584144](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/39273584144): **SUCCESS on older code commit `0265b742`**, not proof of exact-head backend E2E. Latest native/device functional QA is NOT verified here.

## Implemented on the P3 branch (do not rebuild)

1. `localization/lessons/nhsk2_grammar_uz_ru_tj.tsv` contains **136 unique Chinese/grammar-context source-hash-pinned entries × 3 locales = 408 independent UZ/RU/TJ translations**. `scripts/i18n_canonical_grammar_catalog.py` verifies source-context SHA-256, original lesson SHA, exact context reuse, mirror consistency. **48 nHSK2 lessons; 272 blank original grammar display maps; 136 blank `_grammar` mirror maps; 1,224 localized display placements (272+136)*3.** Original lesson JSONs intentionally remain byte-identical under frozen P0 baseline.
2. `app/services/course_p3_grammar_localization.py` provides cached source-checked `apply_native_grammar_locales` and `miniapp_reserved_grammar_patch`. `app/services/desktop_course_service.py` adopts translations for authorized native/Desktop+Android lesson payloads **only AFTER existing progress/unlock and consuming entitlement checks**. No extra remote per-string API or public grammar pack.
3. Mini App `app/api/miniapp_entitlements.py` uses the EXISTING authenticated `POST /api/v3/lesson/start` reservation response to return display-only P3 patch **after signed Telegram initData verification, current unlock, consuming lesson-access decision and transaction commit**. For completed lessons, `review_only:true` must be signed and server-completed; it must NOT consume quota. Denied 401/403 never return P3. `Cache-Control:no-store`.
4. `app/static/course_v3_data/p3-grammar-reservation.js` applies the localized grammar patch to an **isolated cloned lesson**, validates level/lesson, Chinese+pinyin, pointer allowlist and all UZ/RU/TJ values, discards any partial/bad patch atomically. Explicit 401/403 or `allowed:false` completed-lesson denial MUST NOT silently become allowed. True network failure may fall back to existing OFFLINE **already-completed** reading, without adopting P3. Do not open unauthorized content.
5. Real-source parity regression verifies **all 48 affected lessons** produce equivalent original+mirror translations for native and Mini App, with no changes to original source/grade, answers, Pro, auth or user data. `tests/test_i18n_miniapp_grammar_reservation.py` has Node JS atomic/cache/denial/fallback smoke; `tests/test_i18n_miniapp_reservation_asgi.py` has synthetic authenticated ASGI scenarios. P0 run above passes.

## Critical non-negotiable constraints

- **USER DIRECTION:** Agent owns Chinese↔UZ/RU/TJ meaning and grammar QA, self-correction, source-safe centralization, tests, and bug/root-cause prevention. NEVER ask the owner to verify translations or require a third-party editor. Follow `localization/AI_CONTENT_QA_POLICY.md`; AI self-check is not native-speaker certification.
- Preserve signed auth, entitlement/quota, lesson sequencing, old users, Pro/paywall, scoring/answers, Chinese/pinyin and frozen source baseline. A source mismatch must fall back safely; do NOT commit raw gated lesson JSONs or publish translation packs through anonymous static APIs.
- Keep `app/static/course-v3.html` at **8712 physical lines**: P0's line-anchored access/fetch classifications are sensitive. JS helper is a separate script; edit same-line hooks only if strictly necessary.
- Do not merge `main`, deploy production, or mark work finished while Draft PR #179 has unresolved conflicts, current relevant CI fails, or end-to-end platform/security checks are missing.
- Avoid redundant proposals, additional draft tools or new branches unless essential. Act in the existing branch; write a narrow regression test for every bug and record prevention rule.

## NEXT executable steps (in this order)

1. Fresh-read branch HEAD/PR #179 and applicable GitHub Actions (P0, backend, Android, Desktop). Inspect `app/api/miniapp_entitlements.py`, `app/services/desktop_course_service.py`, `app/services/course_p3_grammar_localization.py`, `p3-grammar-reservation.js` and existing tests; do not assume historical SHA still current.
2. Run/expand **actual authenticated native and Mini App API integration tests**: allowed/denied/unlocked/current/completed/offline, quota consumption vs read-only completed revisit, new and existing user, correct locale + mirrored grammar, wrong/stale SHA fail-closed, cache isolation, level boundaries, P3 not leaked by public GET. Use existing backend CI to verify—not just source-text search. Fix issues and add targeted regression tests.
3. Verify Android shared-service path and Desktop actual consumer contract; run Android/desktop CI and realistic WebView/device QA as tools allow. Be explicit about any unavailable emulator/hardware rather than claiming device tests.
4. Review PR #179's **dirty merge conflicts** against CURRENT `main`. Reconcile code/tests/baseline manifests on the feature branch in small verified commits; do not overwrite unrelated main changes or bypass frozen source/audit gates. When green and release-safe, prepare merge/deployment, no premature production changes.
5. Keep this concise active handoff and `localization/NEXT_CHAT_HANDOFF.md` updated with **exact** pushed SHA + CI evidence, remaining blockers and next single task. Preserve private archives and older handoff history separately.

## Relevant files

`AGENTS.md`, `AI_RULES.md`, `PROJECT_MEMORY.md`, `localization/PLAN_SCHEMA_ORDER.md`, `localization/AI_CONTENT_QA_POLICY.md`, `localization/NEXT_CHAT_HANDOFF.md`, `.github/workflows/i18n-p0.yml`, `.github/workflows/backend-ci.yml`, `tests/test_i18n_native_grammar_localization.py`, `tests/test_i18n_miniapp_grammar_reservation.py`, `tests/test_i18n_miniapp_reservation_asgi.py`.
