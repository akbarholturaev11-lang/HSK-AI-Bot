# HSK AI — iPhone PWA | ACTIVE HANDOFF

**Last verified:** 2026-11-04. **Status:** WIP / NOT accepted / NOT released.
**THIS IS THE ONLY ACTIVE PWA CONTEXT FILE.** Read this section first in every new chat. The formal acceptance checklist is `openspec/changes/iphone-course-pwa/tasks.md` (planning branch); **4/18 checked, 14 pending**. Earlier verbose handoff (≈136k chars) is preserved unmodified in Git history at planning commit `9d3deaab31c494f1a2f9648b1c80adb3d2fb4823`: `git show 9d3deaab:docs/IPHONE_PWA_CONTEXT.md`. No second context or new task list is authorized.

## 1. GitHub refs — verified before this documentation update

| Ref | SHA / status |
| --- | --- |
| `main` | `6eda30e79ea48d9306aa86e52ceaa1e90e729e80` |
| Implementation `feat/iphone-pwa-browser-auth-p1-20261102` | `a620d0f900c16512e5964ca883e1a81bc6311825`; [Draft PR #257](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/pull/257); NOT merged |
| Planning `feat/iphone-course-pwa-planning-20261102` | `9d3deaab31c494f1a2f9648b1c80adb3d2fb4823` *before this docs-only commit*; [Draft PR #256](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/pull/256); NOT merged |

Always re-read actual HEADs at the start of the next chat; they may advance independently. Do NOT merge/push `main`, deploy, enable `PWA_AUTH_ENABLED`, close Draft PRs, release or trigger product user rollout without separate owner approval. Original Telegram Mini App, Android, Desktop and Smart Reminder must be preserved. Final physical Safari/Home Screen QA belongs to owner and is performed **last**.

## 2. Working scope and user-approved design

Owner supplied a screenshot of the Figma login screen (warm paper/cream, panda holding a book, dark charcoal type, restrained cinnabar red, jade/gold accents) and approved implementing other screens **directly in existing code** because the Figma Starter MCP read/edit quota is exhausted. Do NOT invent a second UI framework or misrepresent the screenshot-based work as editable Figma components. Reuse original Mini App styles/tokens, UZ/RU/TJ localization, short one-action centered dialogs, 16px iOS inputs, safe areas, keyboard, opt-in reduced transparency/motion and subtle optical *Liquid Glass* (CSS approximation, not native iOS renderer). Do not replace the approved login screen or add tutorial-heavy explanatory copy.

Relevant rules: `AGENTS.md`, `AI_RULES.md`, `PROJECT_MEMORY.md`, `.agents/skills/hsk-ai-ui/SKILL.md`, `openspec/changes/iphone-course-pwa/` and `$hsk-ai-openspec-planning`. Read these and inspect original source before editing.

## 3. What is already implemented (feature PR #257; verify against actual source)

- Reuses original course and checkout HTML: `app/static/course-v3.html`, `app/static/subscription.html`. PWA-only browser auth and account services in `app/api/pwa_auth.py`, `app/services/pwa_auth_service.py`, `app/static/iphone-pwa-login.html`, `app/static/iphone-pwa-login.js`. Google/Apple/Telegram identity paths share canonical `users.id`, course/progress, Pro/free, payment and receipts; no new account/checkout authority. All claims require actual integration tests before release.
- Warm scoped optical-glass presentation `app/static/course_v3_data/iphone-pwa-glass.css`; profile access to `iphone-pwa-notices.js` and `iphone-pwa-feedback.js`. Notice endpoints `GET /api/v3/pwa/notifications`, `GET /api/v3/pwa/account-notices` read server-owned course/account sources. No push delivery, inbox-read acknowledgment or new scheduler. Central alert is permitted **only** for latest reviewed rejected `payment_action`, owner-scoped by `users.id+payment_id`; Pro vs HSK3.0 checkout routing and selected plan preserved. Must never interrupt active lesson, feedback, checkout, splash or focused text input. Account switch/session must not leak other user's notices.
- Ordinary feedback uses canonical available/prepare/submit endpoints with server choice labels, eligibility and one-time rewards; release feedback reuses server campaign response with 1–5 rating and mandatory comment at 1–2. Browser mutation is protected by verified owner and CSRF. Fixes at latest head include stale async session/closed-dialog generation guard and correct focus/reset on reopen. No client-side reward grant. Service feedback/Pro policies unchanged.
- Scoped asset allowlist in `app/main.py` contains only the three approved CSS/JS assets (no broad private lesson/answer mount). UI source review baseline `localization/baselines/reviewed_ui_changes.json` was updated against exact source blobs after provenance audit, not disabled.
- Regressions: `tests/test_pwa_notices_ui.js` 16 scripted DOM/transport cases; `tests/test_pwa_feedback_ui.js` 9 cases; `tests/e2e/test_iphone_pwa_glass.py` Chromium visual/behavior tests. Plus `tests/test_pwa_browser_auth.py`, `tests/test_pwa_telegram_bot.py`, `tests/test_telegram_sdk_asset.py`, backend PostgreSQL, Mini App, Android and Smart regression suites. The newly added Chromium case `test_rejected_payment_never_interrupts_feedback` is **not proven green on latest HEAD**.

## 4. VERIFIED CI — strictly distinguish SHAs

Last positively verified `Backend targeted` workflow run: [41663587599](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/41663587599), associated with **older** implementation HEAD `04edc5d2666df695f3229ea0840368127b9057af`; latest fetched jobs: `targeted-tests` SUCCESS, `native-postgres` SUCCESS, `miniapp-ui` SUCCESS. Previous logs included 72 PostgreSQL tests + 64 subtests, five Chromium iPhone checks, legacy Mini App browser and lesson/checkout checks. This was not all-project CI.

For current implementation HEAD `a620d0f9...`, `fetch_commit_workflow_runs` returned an empty list and `get_commit_combined_status` returned zero statuses. **Important:** those connector endpoints only surface some PR-triggered/status results, and may omit push-triggered Actions runs. Empty ≠ FAIL and empty ≠ PASS. Use the GitHub Actions run/job pages or a connected git/CI environment to verify **exact SHA**. Never reuse older pass results for new HEAD.

## 5. Main divergence — do not blind merge

At check, `main` vs implementation feature has common ancestor `df8e6de5dceb77284f2b361f760e8ee01f31d78c`; **feature ahead 365 / behind 25**. Main contains independent Smart Reminder runtime/Android widget/Admin work (**at least 107 main-only changed paths** at earlier diff; re-evaluate with full git tree).

Seven overlapping paths exist, of which both Android instrumentation test blobs are exactly **identical** at the current heads:
- `.github/workflows/smart-reminder-p0.yml` (content differs)
- `android/app/src/androidTest/java/com/pomp/hskai/core/notify/SmartStudyProtocolTest.kt` (identical)
- `android/app/src/androidTest/java/com/pomp/hskai/core/notify/SmartStudyTwoDeviceTest.kt` (identical)
- `app/config.py` (content differs; preserve default-OFF `PWA_AUTH_ENABLED` and independent Smart flag)
- `app/main.py` (content differs; preserve BOTH Smart runtime lifespan/router and PWA auth/grade/progress routes)
- `app/static/admin-pwa/app.js` (content differs; preserve all original Smart and PWA behavior)
- `localization/baselines/reviewed_ui_changes.json` (content differs; regenerate/verify hashes after integration, never bypass the audit)

**Required safe approach:** Use a real connected git workspace for COMPLETE **main→feature only** semantic merge/rebase (not partial patching of five overlapping files). Create rollback reference, preserve main-only files, resolve actual content conflicts, inspect full diff, run relevant tests. A connector-only manual update to five paths would silently omit main-only runtime and Android files and is NOT a safe sync. Never force-push `main`; do not merge PRs.

## 6. Next actions in priority order — do real work, not a plan-only answer

1. Re-fetch heads, full OpenSpec, current files and exact-SHA CI (including push-run jobs). Investigate actual failure logs; fix root causes in feature branch only. Ensure latest Chromium test and signed API/browser auth regressions run.
2. Verify current committed implementation in genuine Chromium UI: font/readability, centered dialogs/focus, same Mini App course page/checkout, safe area (320/390/430 px), font >=16px on inputs, swipe/pinch, BFCache/refresh/session restore, multi-account owner isolation, locale UZ/RU/TJ, consent/accessibility and keyboard zoom. Update only minimal current components. Real physical iOS test stays last.
3. Audit browser Google/Apple/Telegram identity linking, session/CSRF/revocation, `users.id`, course/grade/progress/XP, AI Voice, Pro/free/trial/pending, checkout receipt/rejected and idempotent feedback/bonus. Check risk of cross-account state after logout/switch and stale in-flight network.
4. Reconcile complete independent `main` Smart Reminder + Android + Admin integration **on implementation feature branch only** in full git checkout. Verify Smart storage/runtime (including prior cancelled job), Android, Admin PWA, catalog integrity and original Mini App/Desktop. If connected git environment unavailable, explicitly block integration; don't fake or replace with partial cherry-picks.
5. On **merged feature-only** SHA run actual targeted backend, native PostgreSQL, Mini App E2E, Admin, Smart, Android, localization baseline and security checks. Close OpenSpec entries only with concrete evidence; otherwise leave unchecked. Keep both PRs Draft and feature OFF.
6. **Last gate:** owner-led physical iPhone Safari + installed Home Screen auth/lesson/voice/receipt/keyboard/pinch/BFCache tests. Then request separate approval for merge/release. Do not skip this gate.

## 7. Handoff and cleanliness rules

All progress belongs in **this exact file** (`docs/IPHONE_PWA_CONTEXT.md`) on the **planning branch**, with its exact new SHA, completed tests/results, blockers and one concise next step. Keep this file compact; **do not append chronological history dumps again**. This concise handoff replaced the ≈136k-char accumulated archive; historical material remains retrievable at planning commit `9d3deaab31c494f1a2f9648b1c80adb3d2fb4823` and parent commits. Do not create additional context files, remove tests, mark artificial PASS, change deployed runtime settings, open parallel systems, or merge/push to `main` without direct owner authorization.
