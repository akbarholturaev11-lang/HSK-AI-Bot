# HSK AI iPhone learner PWA — ACTIVE HANDOFF

**Updated:** 2026-11-03 · **Status:** IN DEVELOPMENT — NOT ACCEPTED · **Next task:** browser-safe Mini App host adapter.

This is the **only** PWA continuation/context file. Source-level history and detailed earlier audits remain in [this file's Git history](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/commits/feat/iphone-course-pwa-planning-20261102/docs/IPHONE_PWA_CONTEXT.md). The **only** acceptance checklist is [OpenSpec tasks.md](../openspec/changes/iphone-course-pwa/tasks.md). Do not create another status file, worktree, tracker, PR, or architecture plan.

## 1. Where to work — verified refs

| Role | Ref / status |
| --- | --- |
| Repo | `akbarholturaev11-lang/HSK-AI-Bot` |
| Production baseline `main` | `2b56ac6488ee40114644a1452f91af16bc74271e`, unchanged by PWA work |
| Implementation | [Draft PR #257](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/pull/257), branch `feat/iphone-pwa-browser-auth-p1-20261102`, HEAD `626424a78df8336fbc54faea47dc393b1b7ac8c4` |
| Planning & this file | [Draft PR #256](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/pull/256), branch `feat/iphone-course-pwa-planning-20261102` |
| Recovery backup | `backup/iphone-pwa-before-main-sync-20261103` → `d19acf7e562073326d77e733c869d22be6bfb097` |
| Design | [Figma iPhone PWA](https://www.figma.com/design/89fCM5GdjfBqcx0B9aQHOI) · login node `24:38` |

**Main sync:** non-force, two-parent merge [`626424a`](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/commit/626424a78df8336fbc54faea47dc393b1b7ac8c4), parents `d19acf7` and `2b56ac6`. Three-way tree check: 31 main-side file changes, 29 independent PWA file changes, **zero overlapping changed paths**. All new main blobs (including Smart Reminder, migrations, public site, user repo) have exact matching SHAs in the feature tree. Branch currently **0 commits behind main**. If main advances, re-inspect before any further integration; do not force-push or reset.

**Critical user release hold:** NO merge/push/cherry-pick **to main**, NO deploy, NO enabling `PWA_AUTH_ENABLED` (default `False`). Even once code and automatic checks pass, obtain **explicit final owner approval**. The **very last QA gate** is real iPhone Safari + installed Home Screen testing by the owner, after **all P1/P2/P3 code** is finished.

## 2. Actual CI evidence, not assumptions

For current implementation HEAD [Backend #41506184745](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/41506184745):
- **PASS:** dedicated isolated PWA browser+Telegram auth regression step, Mini App UI job, native-postgres job.
- **FAIL (overall targeted tests):** separate multilingual inventory / Mini App locale step; do not label the entire backend workflow green.
- **Other PASS:** [Desktop auth](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/41506184565), [Mandarin local TTS](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/41506184858), [Mandarin lesson TTS](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/41506184371).
- **Other FAIL/unresolved:** [localization](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/41506184782), [Android CI](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/41506184478), [Admin PWA](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/41506184374); [Smart Reminder regression](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/41506184384) was still in progress at last check. Match each failure against its real main/baseline contract; do not disable or weaken unrelated tests.
- Locale-line/source inventory failures reference unchanged source blobs shared by main and feature. Existing brittle snapshots are **not** grounds to waive semantic locale guards; investigate separately.

**Testing scope:** source/CI results are not physical iOS or live Google/Apple provider acceptance. Latest runtime head is not fully green.

## 3. Product invariant and implemented code

Goal: **the existing HSK AI learner Telegram Mini App** as an independent iPhone Safari/Home Screen PWA; same canonical `users.id` for progress, Pro, grades, trial, subscription/receipt, XP, voices and messages. Never duplicate account/course/billing systems or synthesize `telegram_id`. Telegram Mini App remains signed-`initData` only; native Desktop/Android bearer tokens stay out of browser localStorage. No new Admin PWA, web push sender, offline course/SW, or Smart scheduler in V1.

**P0 complete (source audit only):** existing UI and seven related `course_v3_*.html` pages, account/payment architecture, notification sources and future Smart policy boundary examined.

**P1 largely coded, NOT accepted:** `app/api/pwa_auth.py`, `app/services/pwa_auth_service.py`, `app/static/iphone-pwa-login.{html,js}`, existing OAuth/Telegram bot adapters, focused `tests/test_pwa_browser_auth.py`/`tests/test_pwa_telegram_bot.py`. Google/Apple verification uses a browser-bound one-time proof; Telegram requires private bot confirmation; cookie is Secure+HttpOnly, CSRF+Origin apply to mutations, sessions have expiry/revocation; callback and pending cancellation/denial handling and same-browser session replacement tested. Apple cross-site POST binds previous verified PWA session at OAuth start. Explicit existing-account linking and live provider/device returns still require closure; no automatic email merge. Source Android `LinkScreen.kt` informs login; Figma visual review was blocked by Starter MCP call quota, so unapproved new variants must not be guessed.

**P2 backend adapter partially coded, but the frontend NOT connected:**
- `app/api/course_tracks.py`: PWA track status/switch/promo, existing `CourseTrackService` and analytics.
- `app/api/miniapp_entitlements.py`: PWA foundation, lesson content/start, current access/limit/lesson completion proof.
- `app/api/miniapp_practice.py`: PWA mastery words and drill report, shared existing mastery/mistake services.
- `app/api/pwa_auth.py`: PWA course notification inbox and persisted transactional account notice read, canonical owner only; **read is not push acknowledgement** and must not modify Android→Telegram fallback.
- The **real** `course-v3.html` and **all seven** child pages still use Telegram-specific signed data in headers, JSON, query and multipart; do not claim a completed host adapter because some PWA APIs exist. No fake `initData`, client-only access decision or separate frontend rewrite. PWA checkout/receipt/voice/quiz/homework/progress routes and UI remain incomplete.

**P3 partly coded, NOT install-accepted:** flag-gated manifest and iOS metadata reuse existing HSK AI logo, brand palette and login entry. No complete learner shell/standalone back navigation/resume yet. iPhone writing auto-zoom requirement: login locale selector now 16px; `hsk-lugat.html` writing surfaces use `touch-action: pan-y pinch-zoom`, keeping swipe, vertical scroll and intentional accessibility pinch. Existing course writing button still opens fast writer iframe. `user-scalable=no` and `maximum-scale=1` must never be added. Owner performs real Safari/Home Screen no-auto-zoom QA **at the very end**.

**Messages/feedback/Smart limits:** only genuinely persisted canonical course/account notices available for inbox. Do not assert ephemeral Telegram notices were captured. PWA inbox must not ACK Android delivery. Feedback uses existing eligibility/one-time reward rules; no invented new reward. Future Smart PWA capability remains a disabled adapter to the **same** account engine and one selected job, not independent scheduling or V1 Web Push.

## 4. Formal remaining acceptance items

**[OpenSpec tasks](../openspec/changes/iphone-course-pwa/tasks.md): 18 total; 4 P0 source-audit boxes checked; 14 unchecked.**

| Stage | Unchecked | Acceptance still required |
| --- | ---: | --- |
| P1 | 3 | Verified identity/account linking; provider/cookie/security review; automatic auth regression coverage |
| P2 | 7 | Existing Mini App host adapter to seven pages; lesson/quiz/voice/grade/payment/progress/locale, notifications/feedback, Smart boundary, automated parity |
| P3 | 4 | Full installed learner shell/lifecycle, rollback & CI, transactional/Smart/feedback guards, **last owner-led real iPhone QA** |

**14 unchecked ≠ 14 unimplemented features.** Backend parts have code/targeted tests, but the acceptance criteria are not all closed. Of the 14, one is specifically the final owner-operated device gate; the other 13 still include development, review and automated proof.

## 5. Next executable steps, in order

1. **Critical:** implement the **smallest** browser host adapter to reuse the original `course-v3.html` plus its seven child pages. Inspect each original `initData` transport before mapping to verified PWA routes; preserve original Telegram paths and access/grade/receipt contracts. Do not ship a login-only PWA as finished.
2. Finish missing server-authoritative PWA operations (quiz/test/homework/XP/progress, voice, user profile, payment/receipt return) through existing services; add focused auth/CSRF/grade/free/pending/paid test matrix.
3. Before new UI, review existing Figma screens/variants; reuse canonical UZ/RU/TJ sources and existing Mini App components. Add appropriate in-app notices, eligible feedback dialogs and future Smart capability boundary only, without altering actual transactional delivery.
4. Finish standalone safe areas, keyboard, back/resume and owner-visible rollback checklist; check security + code/CI against latest main and original Telegram/native behavior.
5. **LAST:** owner tests real iPhone Safari and installed PWA (providers, Telegram handoff, account/progress/Pro, voice/mic, graded lesson, payment, suspend/reopen, writing focus/double-tap no-auto-zoom). Only then discuss release; never merge to main without explicit approval.

## 6. Continuation rules

Read actual current `main`, PR #256/#257, `AGENTS.md`, `AI_RULES.md`, `PROJECT_MEMORY.md`, `.agents/skills/hsk-ai-openspec-planning/SKILL.md`, `.agents/skills/hsk-ai-ui/SKILL.md`, `docs/UNIVERSAL_NATIVE_ACCOUNTS.md`, and the five existing OpenSpec specs before any new implementation. For UI changes follow Figma-first and existing locale catalog generation; do not manually edit generated i18n. All runtime code stays on PR #257 branch; update this **same** file on PR #256 after each meaningful phase with **verified HEAD, CI and next blocker**. Preserve branch backup, history and both Draft PRs; do not delete unrelated branches. **Keep the active section accurate rather than appending a day-by-day diary.**
