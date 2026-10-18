# HSK AI Local-First i18n — next-chat execution handoff

## Ready Phrases + App Downloads — 94 exact UZ/RU/TJ labels (2026-10-19)

- `app/static/hsk-gaplar.html` now preloads one local static generated `hsk-course-i18n.js?v=20261019-phrases-download-v17` and uses **15 exact original UZ/RU/TJ UI labels** through `readyPhrases.*` with complete inline fallbacks. Existing phrase corpus, user-selected saved phrases, localStorage, search index, Chinese/pinyin/translation data and navigation are unchanged.
- `app/static/desktop-download.html` preloads that same JS asset, **deferred before** the existing `desktop-download-page.js` (strict `script-src 'self'` CSP compatible). `desktop-download-page.js` hydrates **79 existing flat display-only COPY labels per locale** via `downloadPage.*`; original strings and nested platform install/referral step arrays remain untouched, with instant local language switch. No new runtime network path. Referral validation, API release fetching, installer URLs, user platform selection and download actions unchanged.
- Course UI source catalog **427 → 521 per locale** (+94, 282 exact original values), 9 placeholder-bearing keys total, all 6 Android/Mini App/Desktop/Bot static generated outputs updated; original HTML Git blobs pinned in reviewed manifest, strict P0 contracts updated. New `tests/test_i18n_phrases_download_ui_adoption.py` validates source literal parity, static load order, untouched flows and Node-executed override/offline fallback; included in P0 CI.
- Current work branch `codex/i18n-local-first-foundation-20261017`, Draft PR #179, **no main merge or production deployment**. Verify resulting commit's CI (P0, Android, Backend, Desktop, TTS); **device/manual QA is still required**. Prior `9a71f612` was 6/6 CI green; head `474c8a58` had P0/Backend/Desktop/TTS green and Android pending when this batch began.

## Voice, Memorize and Dictionary UI runtime adoption — 65 keys (2026-10-19)

- 47 exact UZ/RU/TJ AI Voice labels, 4 Memorize daily-limit sheet labels and 14 Dictionary practice-card / character-memory UI labels now resolve from a single synchronous **static local** JS bundle `hsk-course-i18n.js?v=20261019-voice-dictionary-v16`, preserving all original inline per-language strings as fallback. Dictionary adopts the labels for all UZ/RU/TJ dictionaries once on load so its existing client-side instant language switch works normally.
- The strict `course` catalog rises from **362 to 427 keys/locale**, all **six** generated Mini App/Desktop/Bot/Android assets must match. Reviewed original Git blob SHAs: `course_v3_voice.html`, `course_v3_memorize.html`, `hsk-lugat.html` with an explicit new reviewed source SHA each. New `tests/test_i18n_voice_memorize_dictionary_adoption.py` covers 195 exact literal values, static load order, untouched voice/access/search code and Node-based fallback/override execution; included in P0 workflow.
- Strictly display-only: no voice recording/STT/TTS, voice session lifecycle, graded answers, XP, app entitlement, paywalls, daily-gate, dictionary words/filter/index/search, offline character/audio files, per-text API fetches or locale preference semantics changed. PR #179 still Draft and on `codex/i18n-local-first-foundation-20261017`. **Verify CI on the commit SHA and manual device QA before any merge or production claim**. Prior commit `9a71f612` has 6/6 green CI including Android and Backend, P0 168 tests.

**CI follow-up:** First 75-label commit `bad8cdc5` failed P0 only because original `mistakes.sub` normalized to the already present Android resource name `hsk_course_mistakes_sub` (from `mistakesSub`) and because four new genuine placeholders raised the reviewed signature count 3→7. Corrected by renaming the *new* namespace `mistakes.*` to `mistakesPage.*` (all 53 labels, original values intact), updating the two source/test contracts and regenerating six artifacts. The previous HEAD's tests for original 75×3 strings and Node fallback already passed; verify the correction commit's full CI before marking completed.

## Mistakes + Pronunciation: 75 exact display labels (2026-10-18)

- `course_v3_mistakes.html`: **53 exact UZ/RU/TJ display-only labels**, including 4 nested category labels and 8 source labels; original inline dictionaries remain synchronous fallback. `course_v3_pronunciation.html`: **22 exact UZ/RU/TJ display-only labels**, same fallback. Both preload `/course_v3_data/hsk-course-i18n.js?v=20261018-practice-ui-v15` once as a local static asset, no per-label backend call.
- Catalog **287 → 362 keys per locale** (+75, 225 original locale values). All **six** generated browser/Desktop/Bot/Android resource files updated. Source SHA review manifest pins both HTML files; new `tests/test_i18n_practice_ui_adoption.py` verifies 75×3 exact parity, JS override/fallback (Node optional), and source invariants. `i18n-p0.yml` includes new test.
- Unchanged: server-owned mistake records and answers, mistake review/start/answer/complete, question scoring, phonetic voice/STT recording and scores, audio cache, trial/Pro, ads, daily gate, XP and network endpoints. **Verify commit P0 and all CI, then manually QA paid/free/offline paths before merging.**
- Prior `b7cb274` Recognition update: all six GitHub CI workflows SUCCESS; 165 P0 tests; Android emulator CI SUCCESS. No device QA confirmation. Work branch only; PR #179 Draft; `main` and production unmodified.

## Recognition 10-label exact-copy runtime adoption (2026-10-18)

- Recognition Mini App `app/static/course_v3_recognition.html` now preloads local `hsk-course-i18n.js?v=20261018-recognition-v14` and overlays **10 original UZ/RU/TJ display labels** onto the existing inline `L` dictionary. Legacy literal copy remains a synchronous fallback when the bundled catalog is absent, and no per-text network request is introduced.
- Catalog **277 → 287 keys per locale**; browser Mini App + Desktop, Bot Python, and Android UZ/RU/TJ generated resources refreshed (six files). Source manifest pins HTML SHA `8cef3be7fb76c6bee286449a3ffb6c7930b6867e`; P0 test includes new exact-locale-parity and fallback regression.
- Unchanged: recognition answer/grading selection, word gating, free/Pro practice permission, subscription flow, advertisements, server APIs, audio cache, progress and lesson content. Separate practice-gate-error copy is not part of this batch.
- PR #179 stays Draft, working branch only; **verify the new SHA's CI before reporting success**, then device QA as needed. Previous head `20566a7f`: Backend, Desktop, both TTS and i18n P0 green; Android CI red, needs job-log isolation and follow-up.

## Test Center exact-copy local-first runtime — 49 UI labels (2026-10-18)

- Exact UZ/RU/TJ display-only copy moved into `course` UI catalog: Test Center hub 19, exam runner 17, exam section titles 3, placement UI 6, HSK 3.0 placeholder 3 and current-level badge 1 = **49 keys × 3 locales**. Catalog **228 → 277 keys per locale**, all **six local generated resources** regenerated.
- Mini App `course_v3_test.html` preloads the **single static** `hsk-course-i18n.js?v=20261018-test-center-v13` bundle, then hydrates existing inline `L`, `EM`, `EM.sec`, `PT`, `HSK30_SOON`, `MINE_T` display-only strings by exact catalog key. Original literals remain synchronous fallback, including when offline/static resource absent.
- Intentionally untouched: `QP` placement-question array and option correctness, HSK server exam answers/session/marking, paid/free access check, placement algorithm, grade, progress, XP and TTS. No per-string fetch or server translation.
- New `tests/test_i18n_test_center_adoption.py` checks all 147 literal pairs, source/use-site/fallback and JS bundle asset parity; existing schema tests updated to 277, P0 CI includes the regression; HTML source Git-blob SHA approved. **Check exact new commit's P0, Android, backend and desktop CI before claiming success.**
- Previous `c0a272e2` P0 passed 161 unit tests, Backend/Desktop/TTS passed; Android's emulator instrumentation failed only two `VoiceScreenBackTest` root-window focus cases. Do not silently treat entire Android CI as pass. PR #179 remains Draft, no main or production deploy.

## Android choice runtime: 17 additional exact-copy strings (2026-10-18)

- Compose `LevelChoices` and `GoalChoices` now read bundled XML for seven HSK option subtitles and ten study-goal titles/subtitles. Original maps/lists remain safe fallbacks; beginner titles/subtitles stay native because they differ from Mini App. The in-app language controls XML resolution (tj → tg).
- Stable option ID values (`hsk_exam`, `daily_communication`, etc.), callback handlers, HSK access and progress, Pro, payment and scoring remain unchanged. Source regressions validate native UZ/RU/TJ parity and use sites. Verify Android CI separately.

## New P2 onboarding 25-key batch — 2026-10-18

- Centralized **9 HSK level descriptors, 10 learning-goal labels and 6 native Android notification primer labels**: 25 exact original UZ/RU/TJ copies. Source catalogs now **228 keys/locale**, all six generated resources updated.
- Mini App `LV20/LV30/GOALS` display values prefer local preloaded catalog with original inline dictionaries as synchronous fallback. Android adds six generated XML lookup fields on the existing app-language `OnboardingCopy` adapter with native fallback. No IDs, HSK gating, score/progress, payment, trial or access changes. Static JS cache version `onboarding-options-v12`.
- `tests/test_i18n_onboarding_options.py` verifies all three languages, unchanged selectable identities and resource call sites. P0 CI includes the new tests; reviewed HTML Git blob updated. CI for this new commit and real device/WebView/offline QA require independent confirmation.
- Previous `28ce15b4` HEAD had all six workflows **SUCCESS** including Android, Backend, Desktop, both TTS, Localization P0 (156 tests). PR #179 remains Draft, no main/production deploy.

## Android onboarding native runtime — 23 exact-copy fields (2026-10-18)

- **23** of the 30 Mini App catalog fields mapped to Android `OnboardingCopy` matched UZ/RU/TJ **exactly**. Android now reads these `R.string.hsk_course_onboarding_*` values using an in-app-language-pinned `Configuration` context, not system locale. The old `OnboardingCopy.forLanguage` values remain fallback.
- Seven source field pairs differ or do not exist on Android; do not adopt without separate review. No account, HSK 2.0/3.0, access, payment, lesson result or notification logic touched. Static regression checks native exact parity; actual Android CI and runtime language-switch/offline QA remain required.

**Repository:** `akbarholturaev11-lang/HSK-AI-Bot`  
**Feature branch:** `codex/i18n-local-first-foundation-20261017`  
**Draft PR:** https://github.com/akbarholturaev11-lang/HSK-AI-Bot/pull/179  
**State:** source/UI catalog migration in progress; **not merged to main; not deployed**.  
**Last handoff update:** 2026-10-18.

## Onboarding local-first 31-key batch — 2026-10-18

- 31 byte-identical three-language (UZ/RU/TJ) onboarding UI values moved to `onboarding.*`, catalog 172 → 203 keys per locale, with six deterministic generated assets.
- Mini App onboarding consumes a synchronous cached static bundle and retains `ONBOARDING_LEGACY` text as fallback; no per-string API call. Auth, track, payment, entitlement, lesson completion, grading and backend requests are untouched.
- Baseline manifest pins the reviewed onboarding HTML blob. Static source tests verify 31×3 parity; local device/WebView and all native Android/Desktop/Bot runtime usage are still open checks, not proven by generation.
- Keep Draft PR #179. Do not merge/main/deploy. Next: Android OnboardingCopy and Desktop parity audit plus remaining UI surfaces, then versioned offline lesson overlays after content/answer security audit.

## VERIFIED STABILIZATION CHECKPOINT — 2026-10-18

- **Implementation commit:** `3adb5d00eee069eef263936e1c3c037dbda7d412` — 30 reviewed finish/streak/parts copy keys in one source-level batch, six generated static targets, new regression and this handoff.
- **CI repair commit:** `de2cdeacfe84707711ddd50c811251c19fd37629` — localized text `levelUp.cpH` correctly introduces a **third** `{n}` placeholder alongside `trialLeft` and `trialLeftHours`. The old test asserted only two; the test now verifies count 3 **and the exact three key names**, preserving placeholder parity across all locales. This was a stale test assertion, not a release runtime failure.
- **Verified P0 localization source CI on `de2cdeac`: SUCCESS, 152 tests, 172 keys per locale, 3 locales, 6 generated assets, 0 stale outputs.** Desktop and both TTS CI also passed. Android and Backend separate workflows must be checked live before any integration/merge; source checks do **not** prove device QA.
- Mini App static lookup key coverage from source: **153/172**, with **19 existing unadopted/semantic exceptions** listed below; this is one UI dictionary, not global i18n completion.
- Working branch contains a long active PR history (**257 commits, 90 changed files at checkpoint**). Preserve history, keep Draft, use a single next-chat handoff and checked source/test evidence rather than force-reset/rebase. Check for concurrent commits and use compare-and-swap branch lease before writing.

## START HERE

1. Check PR #179 head SHA **live**, branch fast-forward and CI. Do not assume the SHA from this document remains current: other agents may update the same branch.
2. Read `AGENTS.md`, `AI_RULES.md`, `PROJECT_MEMORY.md`, this file, and `localization/PLAN_SCHEMA_ORDER.md`. Read `graphify-out/GRAPH_REPORT.md` as a navigation reference; it is stale (built from `2523e381`). Run `graphify update .` in an actual local repo checkout when available; do not claim an update via GitHub API alone.
3. Locate `app/static/course-v3.html` (8,712 source newline segments), `localization/ui/{uz,ru,tj}/course.json`, `scripts/i18n_course_ui_catalog_guard.py`, `scripts/i18n_build_course_catalogs.py`, `tests/test_i18n_common_ui_adoption.py`, `localization/baselines/reviewed_ui_changes.json`.
4. **Latest intended change:** a single 30-new-key batch for UI-only part sections, lesson-completion panels, XP/time badges, streak copy, next lesson CTA and writer-loading label. Expected canonical course catalog **172 keys per locale** and **6 derived generated assets**. Run and inspect `Local-first localization P0 guards` (verified 152 Python regression tests at source+test-fix commit `de2cdeac`), Android CI, Backend targeted tests, Desktop and both TTS workflows. Repair all genuine CI failures before more feature work.
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
