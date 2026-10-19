# HSK AI P3 — ACTIVE handoff for a new ChatGPT agent
Updated: 2026-10-19. **Current working status is here; historical log remains in `localization/NEXT_CHAT_HANDOFF.md`.**

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
