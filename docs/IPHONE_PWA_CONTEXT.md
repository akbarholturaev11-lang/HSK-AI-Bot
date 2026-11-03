# HSK AI — iPhone PWA | ACTIVE HANDOFF

**Last verified:** 2026-11-04. **Status:** WIP / NOT accepted / NOT released.
**THIS IS THE ONLY ACTIVE PWA CONTEXT FILE.** Read this section first in every new chat. The formal acceptance checklist is `openspec/changes/iphone-course-pwa/tasks.md` (planning branch); **4/18 checked, 14 pending** while current exact-SHA Actions complete. Earlier verbose handoff (≈136k chars) is preserved unmodified in Git history at planning commit `9d3deaab31c494f1a2f9648b1c80adb3d2fb4823`: `git show 9d3deaab:docs/IPHONE_PWA_CONTEXT.md`. No second context or new task list is authorized.

## 1. GitHub refs — verified before this documentation update

| Ref | SHA / status |
| --- | --- |
| `main` | `17387c4917e4c8175fe493238aeb16f2999860aa` |
| Implementation `feat/iphone-pwa-browser-auth-p1-20261102` | `d6740e5fa9525a9952fc7882b726fac528e9bd4e`; [Draft PR #257](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/pull/257); OPEN, NOT merged |
| Planning `feat/iphone-course-pwa-planning-20261102` | `49fcf63b66c1561c9f8c3374727fdeee78eedfae` *before this docs-only commit*; [Draft PR #256](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/pull/256); OPEN, NOT merged |

Always re-read actual HEADs at the start of the next chat; they may advance independently. Do NOT merge/push `main`, deploy, enable `PWA_AUTH_ENABLED`, close Draft PRs, release or trigger product user rollout without separate owner approval. Original Telegram Mini App, Android, Desktop and Smart Reminder must be preserved. Final physical Safari/Home Screen QA belongs to owner and is performed **last**.

## 2. Working scope and user-approved design

Owner supplied a screenshot of the Figma login screen (warm paper/cream, panda holding a book, dark charcoal type, restrained cinnabar red, jade/gold accents) and approved implementing other screens **directly in existing code** because the Figma Starter MCP read/edit quota is exhausted. Do NOT invent a second UI framework or misrepresent the screenshot-based work as editable Figma components. Reuse original Mini App styles/tokens, UZ/RU/TJ localization, short one-action centered dialogs, 16px iOS inputs, safe areas, keyboard, opt-in reduced transparency/motion and subtle optical *Liquid Glass* (CSS approximation, not native iOS renderer). Do not replace the approved login screen or add tutorial-heavy explanatory copy.

Relevant rules: `AGENTS.md`, `AI_RULES.md`, `PROJECT_MEMORY.md`, `.agents/skills/hsk-ai-ui/SKILL.md`, `openspec/changes/iphone-course-pwa/` and `$hsk-ai-openspec-planning`. Read these and inspect original source before editing.

## 3. What is already implemented (feature PR #257; verify against actual source)

- Reuses original course and checkout HTML: `app/static/course-v3.html`, `app/static/subscription.html`. PWA-only browser auth and account services in `app/api/pwa_auth.py`, `app/services/pwa_auth_service.py`, `app/static/iphone-pwa-login.html`, `app/static/iphone-pwa-login.js`. Google/Apple/Telegram identity paths share canonical `users.id`, course/progress, Pro/free, payment and receipts; no new account/checkout authority. All claims require actual integration tests before release.
- Warm scoped optical-glass presentation `app/static/course_v3_data/iphone-pwa-glass.css`; profile access to `iphone-pwa-notices.js` and `iphone-pwa-feedback.js`. Notice endpoints `GET /api/v3/pwa/notifications`, `GET /api/v3/pwa/account-notices` read server-owned course/account sources. No push delivery, inbox-read acknowledgment or new scheduler. Central alert is permitted **only** for latest reviewed rejected `payment_action`, owner-scoped by `users.id+payment_id`; Pro vs HSK3.0 checkout routing and selected plan preserved. Must never interrupt active lesson, feedback, checkout, splash or focused text input. Account switch/session must not leak other user's notices.
- Ordinary feedback uses canonical available/prepare/submit endpoints with server choice labels, eligibility and one-time rewards; release feedback reuses server campaign response with 1–5 rating and mandatory comment at 1–2. Browser mutation is protected by verified owner and CSRF. Fixes at latest head include stale async session/closed-dialog generation guard and correct focus/reset on reopen. No client-side reward grant. Service feedback/Pro policies unchanged.
- Scoped asset allowlist in `app/main.py` contains only the three approved CSS/JS assets (no broad private lesson/answer mount). UI source review baseline `localization/baselines/reviewed_ui_changes.json` was updated against exact source blobs after provenance audit, not disabled.
- PWA-only course settings now expose the existing server-backed logout/account-switch path. It clears the same-tab pending Telegram link request after server-confirmed logout; Telegram Mini App SDK/login transport and Telegram account behavior remain unchanged. A regression source audit classifies this cleanup.
- Regressions: `tests/test_pwa_notices_ui.js` 17 DOM/transport/accessibility cases; `tests/test_pwa_feedback_ui.js` 9 cases; `tests/e2e/test_iphone_pwa_glass.py` 6 Chromium visual/behavior tests, including `test_rejected_payment_never_interrupts_feedback`. The test-only source remap after main integration passed 461 localization P0 tests; course catalog generation (6 artifacts), all localization catalogs (75 artifacts) and frozen-source guard (812 sources/746 lessons/0 blockers) are clean. Lesson-fetch audit: 3 calls, 0 regressions; storage audit: 9 classified literal keys/18 calls, 0 regressions.

## 4. VERIFIED CI — strictly distinguish SHAs

Feature contains complete `main` through `17387c49` (0 behind, 370 ahead); `main`'s latest-only Android private APK QA note was retained. Merge was a real connected-git merge, with rollback ref `codex/backup-iphone-pwa-before-main-sync-20261104`; no force push, `main` push, deploy or PR merge. Earlier static localization tests had stale physical-line anchors; they were corrected to use source/content anchors and the source-review registries were remapped against the merged HTML blob. No Mini App/runtime content changed in that repair.

Actions are attached to exact implementation HEAD `d6740e5fa9525a9952fc7882b726fac528e9bd4e` (verify again before next work). Passed: [Local-first localization P0 guards](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/41724588210), [Desktop auth and UI contracts](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/41724588585), [Mandarin lesson TTS regression](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/41724588191), [persistent local TTS cache](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/41724588185), and `miniapp-ui`, `native-postgres`, PWA browser-auth, PWA inbox/payment/feedback, and Android adapter regression jobs in [Backend targeted tests](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/41724588312). Also passed: Admin PostgreSQL locks/migrations, Smart baseline/consent and Android JVM Direct/Play jobs. Still running: remaining backend billing/Pro jobs, Android lint and course/checkout/Voice emulator regressions, Admin legacy payment contracts, Smart storage migration. Do not mark their OpenSpec checks until complete.

On the exact source tree, `python3 -m unittest` for the 461-test i18n P0 contract set passed. Local disposable PostgreSQL credentials were not configured for the Admin/Smart standalone suites; exact-SHA GitHub PostgreSQL jobs cover those suites. Local Android Direct/Play unit tests previously passed 656/605 tests and both instrumentation APKs compiled; no local Android device was available (`adb` missing). No physical iPhone test has been run.

## 5. Main synchronization

At current check, `main` is an ancestor of feature (0 behind). The full main→feature merge retained main-only runtime, Android, Admin, Smart Reminder and the latest Android QA note. Smart Reminder and Admin Postgres regressions are still being verified on exact head; keep `SMART_REMINDER_ENABLED` and `PWA_AUTH_ENABLED` OFF.

## 6. Next actions in priority order — do real work, not a plan-only answer

1. Finish and inspect every GitHub Actions job for exact `d6740e5f…`; repair any genuine failures in feature only and verify their new SHA.
2. Complete Admin/Smart integration audit, rollback checklist and OpenSpec evidence update after CI. Keep Telegram Mini App, Android, Desktop and existing payment/account services intact.
3. Owner's final real-device pass in Safari **and** Home Screen: safe-area on compact/large devices; focus every text/select field (no keyboard zoom); typing at 16px+; writing/stroke view; horizontal swipe and normal vertical scroll; user-initiated pinch; BFCache back/forward; refresh/background/reopen/session restore; logout/account switch with no stale profile/notices/progress; Google/Apple return and existing Telegram account link; lesson result, voice/mic, rejected payment/receipt; UZ/RU/TJ; disabled-feature rollback. Capture iOS version and supported limitations.
4. Keep both PRs Draft, feature flags OFF, no deploy or `main` push. Owner iPhone test stays the last gate.

## 7. Handoff and cleanliness rules

All progress belongs in **this exact file** (`docs/IPHONE_PWA_CONTEXT.md`) on the **planning branch**, with its exact new SHA, completed tests/results, blockers and one concise next step. Keep this file compact; **do not append chronological history dumps again**. This concise handoff replaced the ≈136k-char accumulated archive; historical material remains retrievable at planning commit `9d3deaab31c494f1a2f9648b1c80adb3d2fb4823` and parent commits. Do not create additional context files, remove tests, mark artificial PASS, change deployed runtime settings, open parallel systems, or merge/push to `main` without direct owner authorization.
