# HSK AI Local-First i18n — next-chat execution handoff

**Repository:** `akbarholturaev11-lang/HSK-AI-Bot`  
**Feature branch:** `codex/i18n-local-first-foundation-20261017`  
**Draft PR:** https://github.com/akbarholturaev11-lang/HSK-AI-Bot/pull/179  
**State:** source/UI catalog migration in progress; **not merged to main; not deployed**.  
**Last handoff update:** 2026-10-18.

## START HERE

1. Check PR #179 head SHA **live**, branch fast-forward and CI. Do not assume the SHA from this document remains current: other agents may update the same branch.
2. Read `AGENTS.md`, `AI_RULES.md`, `PROJECT_MEMORY.md`, this file, and `localization/PLAN_SCHEMA_ORDER.md`. Read `graphify-out/GRAPH_REPORT.md` as a navigation reference; it is stale (built from `2523e381`). Run `graphify update .` in an actual local repo checkout when available; do not claim an update via GitHub API alone.
3. Locate `app/static/course-v3.html` (8,712 source newline segments), `localization/ui/{uz,ru,tj}/course.json`, `scripts/i18n_course_ui_catalog_guard.py`, `scripts/i18n_build_course_catalogs.py`, `tests/test_i18n_common_ui_adoption.py`, `localization/baselines/reviewed_ui_changes.json`.
4. **Latest intended change:** a single 30-new-key batch for UI-only part sections, lesson-completion panels, XP/time badges, streak copy, next lesson CTA and writer-loading label. Expected canonical course catalog **172 keys per locale** and **6 derived generated assets**. Run and inspect `Local-first localization P0 guards` (expected 148 Python regression tests only if no further concurrent changes), Android CI, Backend targeted tests, Desktop and both TTS workflows. Repair all genuine CI failures before more feature work.
5. Keep `courseMessage(key, fallback)` synchronous and local. No per-string server requests, no lesson JSON/quiz marking changes, no new account/payment/entitlement logic. Preserve UZ/RU/TJ exact legacy text, Android Tajik `values-tg` adapter, cache-busting script version, and reviewed source SHA guard.

## LARGE BATCH APPROACH — NOT 5-MINUTE MICRO-COMMITS

- Work in **cohesive 20–40 reviewed UI labels per batch**, scoped by screen/component and risk, with one source catalog update, all 6 deterministic generated resources, focused 3-locale parity regression, approved HTML source SHA, and one commit. Do not repeat a new 5-string slice every chat.
- First complete a focused **inventory** of remaining inline dicts for onboarding, settings, notifications, profile, mistakes/recognition/practice, desktop and Android. Mark each field as `exact-safe`, `locale-mismatch`, `feature-local-context`, `dynamic`, or `business-logic`. Only batch exact-safe display strings.
- Course catalog `trialTitle,trialBody,trialActive,trialUsed,done,here,finishPrev,lessonDoneSub,unlockTitle,unlockSub,unlockBtn,learner,premium,rank,goal,on,b1,b2,b3` were intentionally unadopted after review: most have no matching active source use; `done` is feature-context dependent, and `lessonDoneSub` Russian punctuation differs from legacy text. Do not force-wrap them to inflate completion.
- Android/Desktop/Bot files **contain generated catalog resources**; that is NOT proof that every native runtime UI actually reads every resource. A separate runtime adoption audit is required.
- After UI source completion, implement the **versioned local lesson-content overlays** (lesson translations for UZ/RU/TJ) with explicit content IDs, consistent grading, offline asset bundling and native/Mini App/Desktop parity. Do not mistake course UI key coverage for lesson translation completeness.

## REQUIRED RELEASE GATES (NOT YET PROVEN)

- Real Telegram Mini App WebView on iOS/Android: fresh install and cached-upgrade, UZ/RU/TJ locale switch, responsive/safe-area screens, onboarding, Pinyin settings and notification settings.
- Device offline/online, app restart and cache update; no per-string HTTP fetch.
- Login/account switching (Telegram, Google, Apple where supported); Free/Trial/Pro status, 10 TJS unlock, pending payment, approved/rejected payment, disabled/expired entitlement, HSK 2.0/3.0 level selection.
- Quiz correct/incorrect grading and XP/progress, lesson 5 deep-link, practice/voice flow, leaderboard/profile, errors and retry screens.
- Android CI has occasionally failed `VoiceScreenBackTest` emulator focus/root-window assertions; verify against newest HEAD and differentiate test infrastructure from real voice regressions. Audit old anonymous lesson JSON exposure separately as an unresolved security concern.
- Do not merge PR #179 or deploy production until explicit integration/release gates are met and user confirms promotion.

## BRANCH HYGIENE

- Preserve PR #179 and its source commits. **Do not squash/rebase/force-push/delete** the working branch merely to shorten a 250+ commit history; doing so risks orphaning concurrent work. Do not merge PR #179 just for cleanliness.
- Keep implementation notes in `localization/PLAN_SCHEMA_ORDER.md`; use this file as the single compact next-chat index. Avoid redundant daily diary or repeated full audits. Use optimistic SHA/lease checks on writes.
- At the end: report live commit SHA, actual CI conclusions, exact changed files and count, outstanding risks, next concrete large batch. Do not claim Android build/device deployment from source-only tests.
