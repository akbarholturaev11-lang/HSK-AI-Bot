# HSK AI iPhone learner PWA — ACTIVE HANDOFF

**Updated:** 2026-11-03 · **Status:** IN DEVELOPMENT — NOT ACCEPTED · **Next task:** finish secure browser transport on seven child pages and graded-result/voice/checkout; validate course-host CI.

This is the **only** PWA continuation/context file. Source-level history and detailed earlier audits remain in [this file's Git history](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/commits/feat/iphone-course-pwa-planning-20261102/docs/IPHONE_PWA_CONTEXT.md). The **only** acceptance checklist is [OpenSpec tasks.md](../openspec/changes/iphone-course-pwa/tasks.md). Do not create another status file, worktree, tracker, PR, or architecture plan.

## 1. Where to work — verified refs

| Role | Ref / status |
| --- | --- |
| Repo | `akbarholturaev11-lang/HSK-AI-Bot` |
| Current `main` (outside PWA scope) | `df8e6de5dceb77284f2b361f760e8ee01f31d78c` at last check; advanced independently, not merged into PWA in this phase |
| Implementation | [Draft PR #257](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/pull/257), branch `feat/iphone-pwa-browser-auth-p1-20261102`, HEAD `4880819f17fdf01e26a7cbbc516a1be7c10046d6` |
| Planning & this file | [Draft PR #256](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/pull/256), branch `feat/iphone-course-pwa-planning-20261102` |
| Recovery backup | `backup/iphone-pwa-before-main-sync-20261103` → `d19acf7e562073326d77e733c869d22be6bfb097` |
| Design | [Figma iPhone PWA](https://www.figma.com/design/89fCM5GdjfBqcx0B9aQHOI) · login node `24:38` |
| Historical reference, NOT active | [PR #186](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/pull/186), old 2026-10-19 install-only draft on `codex/universal-sign-in` (1,785 commits behind main at audit). Marked **HISTORICAL — DO NOT MERGE**; branch/commit preserved, no cherry-pick. |

**Main sync:** non-force, two-parent merge [`626424a`](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/commit/626424a78df8336fbc54faea47dc393b1b7ac8c4), parents `d19acf7` and `2b56ac6`. Three-way tree check: 31 main-side file changes, 29 independent PWA file changes, **zero overlapping changed paths**. All new main blobs (including Smart Reminder, migrations, public site, user repo) have exact matching SHAs in the feature tree. That merge was **0 behind at the time**; current main has since advanced independently. A new merge requires another clean 3-way comparison; do not assume feature is up-to-date or force-push/reset.

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

**P2 canonical map bridge — code committed, focused PWA tests were failing on CI configuration:** In implementation `app/main.py`, `d2915fc` moves the exact existing /api/v3/map level/progress, HSK30, Pro, XP, streak, policy, notices, today, analytics, offer and commit body into one `_course_v3_map_for_user` helper. The signed Telegram GET still acquires the same User lock. New **POST /api/v3/pwa/map** requires verified PWA cookie, same Origin and CSRF, refetches canonical `users.id` under lock, rejects blocked or fake Telegram headers, passes nullable actual `telegram_id` and source `pwa_course_v3`, returns no-store; GET is disallowed because the map has progress/timezone write effects. `d8dd986`, `b4bc15f`, `e4f289b` add focused auth/forgery/shared-engine and Google-only-null-Telegram regression tests. `fe4a40e` fixes PWA source attribution to server `pwa_course_v3` so an unverified browser URL cannot spoof Smart Reminder or sales campaign sources; original Telegram signed-source behavior is unchanged. `b97cb47` guards that source isolation. Focused [Backend #41511423441](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/41511423441) failed **2 map tests** because importing `app.main` in CI initialized aiogram with an empty BOT_TOKEN, before the map was exercised. `ed8e9ee` patches the two tests to supply only a syntactically valid disposable token during import; production Bot configuration is unchanged. **Latest host-bridge [Backend #41568545581](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/41568545581) is queued/pending at the last check**; do not claim current HEAD green.

**P2 original-course browser host scaffold — map and bounded routes now connected, NOT feature-complete:** `70ef6f0` adds a PWA-session-protected `GET /iphone-pwa/course` that serves the original `app/static/course-v3.html` unchanged in structure (no duplicate UI); anonymous users redirect to existing PWA login, disabled flag fails closed. `78ba0b2` makes that original JS detect only its explicit course path; it fetches verified PWA session/CSRF and calls **POST /api/v3/pwa/map** while Telegram retains signed GET `/api/v3/map`. `aa3b8b2` adds an **explicit allowlist** for PWA course-track status/switch/promo, limit status and lesson start, and keeps all unmapped browser operations fail-closed instead of faking `initData`. `7d3bccc` navigates to the real course after a confirmed Google/Apple/Telegram PWA session. `24a05fa`, `5a2fe43` isolate lesson/foundation/mastery browser caches by **verified canonical user ID**, with a verified owner header and cross-tab account-switch mismatch guard. `847eb96`, `44ad049`, `4880819` add route, CSRF, legacy-transport and cache-ownership tests. **Unmapped graded-result/quiz, most practice, seven child pages, voice, onboarding, checkout/receipt and notifications UI remain incomplete; never report full course parity or ready for device QA.** Existing unscoped browser preferences need follow-up account isolation review.

**P2 backend adapter partially coded, not all frontend actions connected:**
- `app/api/course_tracks.py`: PWA track status/switch/promo, existing `CourseTrackService` and analytics.
- `app/api/miniapp_entitlements.py`: PWA foundation, lesson content/start, current access/limit/lesson completion proof.
- `app/api/miniapp_practice.py`: PWA mastery words and drill report, shared existing mastery/mistake services.
- `app/api/pwa_auth.py`: PWA course notification inbox and persisted transactional account notice read, canonical owner only; **read is not push acknowledgement** and must not modify Android→Telegram fallback.
- The original course **map and bounded allowlisted calls** now have an independent PWA entry; **all seven child pages and many direct Telegram-only fetch/multipart/query operations still lack PWA adapters.** No fake `initData`, client-only access decision or separate frontend rewrite. PWA checkout/receipt/voice/graded quiz/homework and several progress/analytics routes and UI remain incomplete.

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

1. **Critical: finish course host adapter beyond its now-connected map/track/lesson-start foundation.** Existing PWA path/session, CSRF map POST and bounded track/limit/lesson-start wrapper are implemented; do not duplicate them. Audit each of the **seven child pages** and every remaining original Telegram-only request (headers, JSON, multipart, query), then add narrow canonical-user PWA service adapters. Preserve real server grading/entitlement, course progression, UZ/RU/TJ and checkout/receipt semantics. Never downgrade the write-capable map to GET, invent Telegram `initData` or reuse old PR #186 broad-root service worker.
2. Finish missing server-authoritative PWA operations (quiz/test/homework/XP/progress, voice, user profile, payment/receipt return) through existing services; add focused auth/CSRF/grade/free/pending/paid test matrix.
3. Before new UI, review existing Figma screens/variants; reuse canonical UZ/RU/TJ sources and existing Mini App components. Add appropriate in-app notices, eligible feedback dialogs and future Smart capability boundary only, without altering actual transactional delivery.
4. Finish standalone safe areas, keyboard, back/resume and owner-visible rollback checklist; check security + code/CI against latest main and original Telegram/native behavior.
5. **LAST:** owner tests real iPhone Safari and installed PWA (providers, Telegram handoff, account/progress/Pro, voice/mic, graded lesson, payment, suspend/reopen, writing focus/double-tap no-auto-zoom). Only then discuss release; never merge to main without explicit approval.

## 6. Continuation rules

Read actual current `main`, PR #256/#257, `AGENTS.md`, `AI_RULES.md`, `PROJECT_MEMORY.md`, `.agents/skills/hsk-ai-openspec-planning/SKILL.md`, `.agents/skills/hsk-ai-ui/SKILL.md`, `docs/UNIVERSAL_NATIVE_ACCOUNTS.md`, and the five existing OpenSpec specs before any new implementation. For UI changes follow Figma-first and existing locale catalog generation; do not manually edit generated i18n. All runtime code stays on PR #257 branch; update this **same** file on PR #256 after each meaningful phase with **verified HEAD, CI and next blocker**. Preserve branch backup, history and both Draft PRs; do not delete unrelated branches. **Keep the active section accurate rather than appending a day-by-day diary.**
