# HSK AI iPhone learner PWA — ACTIVE CONTEXT / HANDOFF

**Updated:** 2026-11-03 · **Status:** WIP, NOT accepted, NOT released.
**This is the single active context file.** Preserve prior detailed history through Git commits; do not create another context file or parallel plan. The only formal acceptance list is [OpenSpec tasks](../openspec/changes/iphone-course-pwa/tasks.md).

## 1. Exact repository, branch and safety state

| Item | Verified status |
| --- | --- |
| Repository | \`akbarholturaev11-lang/HSK-AI-Bot\` |
| Production \`main\` | \`df8e6de5dceb77284f2b361f760e8ee01f31d78c\` (advanced independently) |
| Implementation | [Draft PR #257](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/pull/257), \`feat/iphone-pwa-browser-auth-p1-20261102\`, HEAD last observed \`0a390aecea9299419c86ac8995f12d27b1119658\` (**moving branch; re-fetch immediately before modifications**) |
| Planning, OpenSpec, this file | [Draft PR #256](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/pull/256), \`feat/iphone-course-pwa-planning-20261102\` |
| Pre-main-sync backup | \`backup/iphone-pwa-before-main-sync-20261103\` -> \`d19acf7e562073326d77e733c869d22be6bfb097\`; preserve |
| Historical only | [PR #186](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/pull/186) marked DO NOT MERGE; old and stale |
| Figma | [iPhone PWA design](https://www.figma.com/design/89fCM5GdjfBqcx0B9aQHOI), login node \`24:38\`; previous read blocked by Figma Starter MCP quota |

**Main synchronization:** former main \`2b56ac6\` was safely merged **into implementation only** by two-parent \`626424a\`. Since then, \`main\` advanced **4 commits** (Smart Reminder practice/voice activity and docs). Latest compare at \`edc8d0f\` is **140 ahead, 4 behind**. These four commits have **not** been merged here. Before next sync, inspect actual merge base, file overlap, side effects and CI; backup and integrate latest main into **working branch only**. Do not reset/force-push or blindly import historical PR #186.

**NON-NEGOTIABLE RELEASE HOLD:** absolutely no PWA code to \`main\`, no merge of PR #256/#257, no deployment, no enabling \`PWA_AUTH_ENABLED\` (default \`False\`) until **all coding and automated checks are finished AND user explicitly approves**. PRs stay Draft. **Physical Safari/Home Screen iPhone testing is done by the user at the very end**, not during intermediary coding.

## 2. CI evidence, exact limitations

- Most recent observed head \`0a390ae\`: [Backend targeted #41569923674](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/41569923674) **pending** at inspection. DO NOT mark green. A separate implementer has pushed multiple commits since \`edc8d0f\`; previous runs were cancelled/superseded. Inspect final CURRENT HEAD CI before making any PASS claim.
- Earlier head \`430f2c7\`: [Backend #41569221895](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/41569221895) failed before isolated PWA step on separate course contract verification and was superseded; not proof the latest PWA tests pass.
- Earlier \`b97cb47\`: [Backend #41511423441](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/41511423441) isolated PWA step failed two tests from importing \`app.main\` with blank CI BOT_TOKEN (aiogram token format). \`ed8e9ee\` changed **only the test import** to use a disposable syntactically valid token; no production token-guard change. Await actual rerun.
- Verified former merged head \`626424a\`: [Backend #41506184745](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/41506184745) isolated PWA tests, Mini App UI and native-postgres PASS, but overall backend locale inventory FAIL. Other red Android/Admin/localization steps cannot be waived merely because some were existing baseline failures. Inspect real logs and current main source.
- No physical Safari acceptance or live provider callbacks have been run.

## 3. Scope and protected source-of-truth

Create an **independent iPhone Safari / Home Screen client for the existing HSK AI learner Mini App**, preserving the same \`users.id\`, progress, grade/XP, course track, real Pro/trial, payment/receipt, voice and messages. Reuse original \`app/static/course-v3.html\` and its seven child course pages; **no duplicate UI/system**, fabricated Telegram \`initData\` or invented \`telegram_id\`. Original Telegram routes remain signed-\`initData\` only; native Android/Desktop tokens stay out of browser localStorage. For new UI, follow existing \`.agents/skills/hsk-ai-ui/SKILL.md\`, Figma-first and canonical RU/TJ/UZ catalog generation; no manually hacked generated locales.

**P0:** four source audits completed.

**P1 partly accepted in code, not formally closed:** \`app/api/pwa_auth.py\`, \`app/services/pwa_auth_service.py\`, \`app/static/iphone-pwa-login.{html,js}\`, Google/Apple OAuth callback and Telegram private-bot verification. Browser-bound one-time proof, secure HttpOnly session cookie, CSRF+Origin checks, expiry/revoke, cancellation, cross-provider checks. Explicit existing-account linking and provider/device acceptance still open. Never merge identities by email.

**P2 browser entry and course core, code present but not complete:**
- \`GET /iphone-pwa/course\` is PWA-session-guarded and serves **the same** \`course-v3.html\`, rather than a rewritten second course.
- Original course JS distinguishes exact browser host path \`/iphone-pwa/course\`, resolves PWA session and CSRF, uses write-safe \`POST /api/v3/pwa/map\`; Telegram still uses signed \`GET /api/v3/map\`. Both share \`_course_v3_map_for_user\` in \`app/main.py\`. Source attribution fixed server-side to \`pwa_course_v3\`; no fake Smart / sales campaign attribution. Map response includes verified owner header.
- Explicit allowlist adapter for PWA course track status/switch/promo, lesson start, limit status; extra read adapter for lesson content and HSK1 foundation. All unsupported browser requests fail closed instead of silently using Telegram endpoints.
- Owner-bound \`users.id\` local cache scope for lesson/foundation/mastery/resume, cross-tab map owner mismatch + rotated CSRF guard. Existing preferences/cache still need account-switch/privacy review.
- PWA-only API adapters already exist in \`app/api/course_tracks.py\`, \`app/api/miniapp_entitlements.py\`, \`app/api/miniapp_practice.py\`, \`app/api/pwa_auth.py\`; reusing canonical services for lessons, access, progress, mastery, course and account inbox.
- **Newest commits** \`b2fb158\` and \`edc8d0f\` extract shared Telegram/PWA lifetime-free practice consumption and add PWA \`POST /api/v3/pwa/practice/daily-gate\`. It requires Origin, CSRF, locked current \`users.id\`, bounded JSON and rejects forged identity; old signed Telegram endpoint preserved. **Latest CI pending**; not accepted.
- **Still missing:** the seven child course pages' browser transports, secure scored quiz/result/homework/progress parity, many practice endpoints, complete voice, onboarding, profile/languages, Pro checkout/receipt return, ratings/feedback/dialogs and active notices UI. Current main course screen can display a map and parts of a lesson, but **is not a complete usable PWA course**.

**Concurrent implementation warning (2026-11-03):** while preparing this handoff, the implementation branch advanced **at least 7 commits** from \`edc8d0f\` through \`0a390ae\`, touching \`app/api/miniapp_practice.py\`, \`app/api/pwa_auth.py\`, original \`course-v3.html\`, child \`course_v3_recognition.html\` and PWA tests. This appears to be **recognition practice browser transport** work, but has **not yet passed confirmed focused CI**. Treat active code and its Git history as source of truth: inspect these new changes and their test results, do not blindly reimplement or overwrite them. Since the branch was moving during context maintenance, exact HEAD above is a **snapshot, not an immutable claim**.

**P2 notification/Smart boundary:** persisted course notices and separate transactional account notices are only read for the verified canonical owner. Reading an inbox **does not ACK** Android→Telegram delivery or mean that all ephemeral notices were stored. Reuse current feedback eligibility, one-time bonus and release-feedback prompts; do not invent prompts/rewards. V1 does **not** add Web Push or a parallel Smart scheduler. Future PWA Smart only through canonical account/capability/selected-job adapter with unsupported iPhone channel disabled.

**P3 partial:** feature-flagged Home Screen manifest/icon and existing brand tokens implemented. Safari typing/focus auto-zoom reduction: select font >=16px, Hanzi writing zone \`touch-action: pan-y pinch-zoom\`; preserve horizontal character swipe, vertical scroll and deliberate accessibility pinch. Do not add \`user-scalable=no\`, \`maximum-scale=1\` or disable global zoom. Still need full browser-only shell, standalone navigation, safe-area/keyboard, back/background/reopen, rollback and final user device QA. No V1 service worker/offline lessons required.

## 4. Formal acceptance count (do not inflate)

[OpenSpec tasks](../openspec/changes/iphone-course-pwa/tasks.md) **18 total, 4 checked P0 audits, 14 open**: P1=3, P2=7, P3=4. A partly implemented item stays unchecked until the entire acceptance criterion is verified. **One of the 14 is the final user-led iPhone device gate**; the other 13 contain code, QA and review work. This is **not** a claim that only 14 small coding actions remain.

## 5. Next verified workflow (one branch, one context file)

1. **FIRST REFRESH HEAD:** another implementer may still be pushing. Compare live PR #257/branch HEAD against the snapshot above and inspect the newest recognition practice patches; avoid stale SHA updates and wait for meaningful current-head CI evidence. Then inspect latest main, this file, OpenSpec, PRs, project \`AGENTS.md\`, \`AI_RULES.md\`, \`PROJECT_MEMORY.md\`, planning/UI skills and \`docs/UNIVERSAL_NATIVE_ACCOUNTS.md\`. Verify latest focused CI results; fix real test failures, not tests by suppression.
2. Compare current main's four new Smart activity commits against feature changes and bring new main code **safely INTO ONLY the implementation branch** if clean. Inspect branch HEAD again before mutation, preserve backup and history, run CI. No merge to main.
3. Finish missing server-authoritative PWA grading/completion, seven child-page API routes and browser host adapter. Preserve signed native/Telegram routes and actual Pro/free/blocked/payment policies, XP, grade/idempotence, RU/TJ/UZ; tests for actor switching, forged requests and bounded input. No fake data or duplicate implementation.
4. Finish notifications/feedback, checkout/receipt/voice/onboarding/profile, Figma-approved UI, P3 standalone/lifecycle, security and full automatic parity. Keep one code branch and this exact context file freshly updated with verified commit/CI/remaining blocker after each meaningful phase.
5. **LAST:** user tests actual iPhone Safari and installed PWA — Google/Apple/Telegram linking, progress/Pro, graded results, payment receipt, audio/mic, background resume, and **NO automatic zoom** on writing/tap/focus while natural swipes and pinch remain. Only then request release approval.

**No deployment, no main mutation, no feature flag enable in this task.** Do not ask user for the device QA earlier. Existing Draft PR #256 planning / Draft PR #257 implementation remain the only active PRs.
