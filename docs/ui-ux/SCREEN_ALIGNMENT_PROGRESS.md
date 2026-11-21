# HSK AI screen alignment — continuation record

Baseline audit: **2026-11-20**, `origin/main` **00c1e596**. Design entrypoint: [hsk-ai-ui](../../.agents/skills/hsk-ai-ui/SKILL.md), its 45-page reference index and applicable detailed guidance. This is a scoped implementation tracker, not another design rulebook or a claim of complete device QA.

## Evidence and integration boundary

- Compared main with `feat/pwa-professional-45-design-real-source-20261116` **5cdb0cbc**; merge base **c1fccb45**, **155 main-only / 86 old-only commits** at this baseline. Do not merge or replace files from the old branch wholesale.
- Keep main's newer adaptive lessons (#325), picture review/lesson header (#326), picture-word mappings (#328), value-first/contextual Pro (#332) and mistake-format repair (#333). Historical documents calling these unimplemented are not current source evidence.
- The old branch prepared Professional45 styling, XP/Streak pages, saved-word integration, compact phrase cards/audio, profile hierarchy and checkout refinements. They are candidates for selective recovery, not accepted production work. Its `docs/ui-ux/PROFESSIONAL45_REAL_PWA_QA_AUDIT.md` explicitly excludes native Android and leaves device/CI checks open.
- **Saved-word migration conflict:** old `0158_course_saved_words` and main `0158_course_adaptive_lessons` both follow `0157_diagnostic_precision`. Recovering bookmarks needs deliberate migration/security/account reconciliation in a separate slice; copying the migration creates two heads.
- Old minimal-shell tests and real-source previews with synthetic APIs do not establish live account retention, payment correctness or installed-iPhone acceptance. Existing source and historical test files alone cannot earn a ready status.

## Status key

**✅ Ready:** relevant design and behavior checks have evidence; no redesign needed. **🟡 Partial:** concrete source gap; fix only that gap. **🔴 Unadapted:** confirmed lack of relevant adaptation. **🔍 Verify:** implementation exists, current visual/runtime acceptance unconfirmed. No entire screen is marked ✅ or 🔴 from this source-only inventory.

## PWA inventory

Paths below are under `app/static/` unless stated otherwise. Related states are grouped to keep the inventory usable; acceptance remains specific to the state and platform tested.

| Screen / existing states | Status | Source and next necessary check |
| --- | --- | --- |
| Course/map, daily plan, foundation entry, track/level picker, access gate | 🔍 | `course-v3.html` `renderCourse`, course picker/access functions. Keep sticky `.ctop`; verify narrow/large widths, map scroll and loading/ready/error. |
| Lesson/part sheets, locked lesson, skip test | 🔍 | `openLessonSheet`, skip flow. Check Hanzi/pinyin, Back, required content and access states. |
| Foundation/Starter 0 | 🔍 | `startFoundationFromMap`. Verify answer feedback, completion/retry and return destination. |
| Lessons: vocabulary, grammar, listening, ordering, pronunciation, homework/exit check | 🔍 | `startLesson`, `renderFlowCard`. Preserve grading and reactions; verify long UZ/RU/TJ, reveal timing and result persistence. |
| Adaptive review and picture deck | 🔍 | Current main lesson implementation. Retain its server contracts; check reveal/recording/results without old flashcard replacement. |
| Lesson completion, streak/rank celebrations, next-part handoff | 🔍 | Existing course lesson-end flow. Verify saved-result retry and next-part CTA. |
| Practice root and loading shell | 🟡 | `renderMashq`, `.pwa-mashq-shell`. Root header/loading geometry accepted in PR #335; keep the recorded device/theme checks open. Reuse existing resource/practice entries. |
| Dictionary search/list/filter/empty | 🟡 | `hsk-lugat.html`. Reuse version/level/search/history; approved course-aware saved words are incomplete. |
| Dictionary word detail, examples, grammar/mnemonic, strokes/writer | 🟡 | `hsk-lugat.html` detail/writer functions. Check restoration and audio; `.audio-btn.small` is 26px in source, requiring actual hit-area review. |
| Ready phrases/search/categories/saved/copy | 🟡 | `hsk-gaplar.html` `createPhraseCard`. Prepared compact single expansion and independent audio are being recovered from old branch 5cdb0cbc in the slice below. Existing saving/filtering stays; scoped browser checks are required before acceptance. |
| Recognition and results/limit | 🔍 | `course_v3_recognition.html`. Check answer/retry, quota and return navigation. |
| Memorization and its learning steps/results | 🔍 | `course_v3_memorize.html`. Verify required text, natural scroll and progression. |
| Pronunciation/mic/skip/done | 🔍 | `course_v3_pronunciation.html`. Check permission/failure and reachable controls. |
| Mistakes overview/review/builder/results/limit | 🔍 | `course_v3_mistakes.html`. Keep latest format fix; verify empty/error, submit and completion. |
| Test centre/placement/exam/results | 🔍 | `course_v3_test.html`. Check long questions, submit pending/error and saved result. |
| AI Voice root/quota | 🔍 | `renderVoice`. Check quota loading/error geometry independently of immersive conversation. |
| AI Voice V8/conversation/topics/settings/hints/end/restart | 🔍 | `iphone-pwa-voice.html`. Preserve Orb; independently check keyboard, safe areas, audio and state changes. |
| Rating/league/Friends/referrals/user detail/challenges/invite | 🔍 | `course-v3.html` rating functions. Rating/Friends chrome aligned in the second Stage 1 slice below; long-name/device and other nested-flow checks remain open. |
| Profile/accuracy/streak/achievements | 🟡 | `renderProfile`. Root header alignment accepted in PR #335; streak calendar plus separate 30-day achievement repeats information. Keep real 100-lesson/access data. |
| XP/Streak detail destinations | 🟡 | Selective recovery below adds the approved destinations with real map values and strict goal persistence; final-head remote CI/promotion and installed-device acceptance remain to be verified. |
| Settings/study/notifications/profile editor/identities/help/logout | 🔍 | `renderPwaSettings` and existing App methods. Keep dedicated detail header; check drafts/save/revert/Back/account switch. |
| Inbox/push settings/payment notice | 🔍 | `iphone-pwa-notices.js`. Check permissions, local states and truthful payment outcomes. |
| Lesson/activity/release feedback | 🟡 | `iphone-pwa-feedback.js` `close` clears draft without a busy guard. Reproduce submission/dismiss behavior before fixing. |
| Technical report/attachment/consent/sent/error | 🔍 | `iphone-pwa-shake-report.js` already guards submitting-close and retains textarea during rerender. Recheck historical defect claims against current behavior. |
| Login/provider return/account handoff | 🔍 | `iphone-pwa-login.*`, `iphone-pwa-handoff.*`. Verify failed/return/account-conflict states; preserve server identity. |
| Course onboarding/welcome/track/level/goal/save | 🔍 | `course_v3_onboarding.html`. Keep real stepper/footer; check pending/save-reconciliation and localization. |
| Li guest onboarding, study choices, signup, Pro/trial and install scenes | 🔍 | `course_v3_li_onboarding.html`, `li-onboarding-runtime/install.*`. Check each active step and Safari guide; preserve character identity and native entry differences. |
| Contextual Pro/paywall/value-first outcome bridge | 🔍 | Course sales bridge/paywall, inline Pro. Preserve recent main behavior and actual Free/Trial/Temporary/Pro states. |
| Checkout/plan/method/requisites/QR/receipt/pending/provider/exit offer | 🔍 | `subscription.html`, `iphone-pwa-inline-pro.*`, `app/api/pwa_auth.py`. Separate protected Back/X/resume/payment checks required. |

Additional cross-screen findings: the isolated WebKit dark Practice preview exposes pre-existing pale glass-card backgrounds with low-contrast text; review the actual theme surface separately before full-screen acceptance. `RESOURCE.url()` also has a theme handoff gap.

Source detail: `course-v3.html` `RESOURCE.url()` passes `theme:"light"` to dictionary/phrases although both accept dark mode. Handle theme propagation separately from root header alignment.

## Native Android inventory

Sources below are under `android/app/src/main/java/com/pomp/hskai/feature/` unless a flavor is named. The old Professional45 branch has no native screen implementation to restore; its Android delta consists of generated localization resources. PWA QA never proves native parity.

| Screen / existing states | Status | Source and next necessary check |
| --- | --- | --- |
| Main tab navigation, Course/map, daily plan, setup/next-part sheets | 🔍 | `MainActivity.kt`, `course/`. Check insets, tab/title anchors and Back; preserve native navigation. |
| Foundation, skip test, lesson/answer/result/celebration, adaptive/picture review, Hanzi writer | 🔍 | `foundation/`, `course/SkipTestScreen.kt`, `lesson/`. Preserve current main learning logic; check large text and answer/result states. |
| Practice hub, word drill, mistakes/review and tests | 🔍 | `practice/PracticeScreen.kt`, `WordDrillScreen.kt`, `MistakesScreen.kt` and existing practice routes. Verify local loading/error, controls and outcomes. |
| Dictionary/list/filter/detail/writer | 🟡 | `dictionary/`. Existing filters remain editable; approved course-aware bookmarks absent. Review full-screen bottom inset and state restoration on device. |
| Ready phrases/search/categories/saved | 🟡 | `practice/ReadyPhrasesScreen.kt`. Existing saved/search stay; compact expansion/audio absent. |
| Profile/accuracy/streak/achievements/settings/identities/deletion | 🟡 | `profile/`, especially `StreakCalendar.kt`. Calendar plus 30-day achievement duplicates streak; validate hierarchy, actual data and scalable text. |
| XP/Streak progress detail | 🟡 | Dedicated approved destinations are absent from native routing; current course stat chips are informational. Recover separately using real data, not invented history. |
| Rating/Friends/user/challenges | 🟡 | `rating/`. Root uses 20dp horizontal gutters versus shared 16dp elsewhere; measure before changing vertical offsets. |
| Voice home/V8, topics/settings, text/mic/end states | 🔍 | `voice/`. Preserve Orb and native permission/IME behavior; independently test keyboard/audio/Back. |
| AI assistant/text/image flow | 🔍 | `assistant/AssistantHost.kt` and native hosts. Check IME, draft and error/limit states; do not invent PWA feature parity. |
| Sign-in/link, Li guest, course onboarding, notification primer | 🔍 | `auth/`, `onboarding/`. Verify guest/resume, account ownership and pending/error states. |
| Pro/limits/manual/Lava checkout; Play alternative | 🔍 | `src/direct/.../subscription/`, `src/play/.../subscription/`. Preserve flavor separation and actual access/payment rules. |
| Activity feedback/report intro/report form | 🔍 | `feedback/`. Verify drafts, attachment consent, submit/error and system Back. |
| Ads/update/mandatory gate/widget installation and other support layers | 🔍 | `ad/`, flavor-specific `update/`, `widget/WidgetInstallPromptScreen.kt`, native notification hosts. Preserve purpose-specific/platform-native behavior. |

## Six-phase plan — only demonstrated gaps

1. **Shared layout:** first measure and align Practice/Profile root headers plus their loading shells. Then separately measure Rating/title and detail gutters/insets. Keep content height natural; leave course, lesson, Voice, checkout and onboarding exceptions intact.
2. **Course and lessons:** validate current main's map/sheets/Hanzi/pinyin/meaning/answer/result readability; fix reproduced presentation defects only. Never recover old lesson files over newer learning logic.
3. **Practice:** preserve current dictionary/phrase filters and saves; separately reconcile bookmark architecture before recovery. Validate compact phrases/audio and each exercise's empty/error/result states in small slices.
4. **Profile and results:** remove demonstrated streak duplication after before/after QA; verify real accuracy/XP/Streak/rating sources and needed detail destinations without fabricated history.
5. **Special screens:** inspect onboarding/auth, contextual Pro/checkout and Voice independently; recover only evidenced gaps with their actual navigation/payment/keyboard constraints.
6. **Android:** compare accepted PWA decisions with native source, fix one small native group at a time, then verify Direct/Play as applicable, system Back, IME and font scaling. Do not copy browser code.

## First accepted slice — PR #335

- **Stage 1 scope:** Practice/Profile root headers and Practice's existing loading geometry. No other screen was redesigned.
- **Before:** at 390px the Practice ready header was 40px and Profile 60px; Practice title moved 8px on shell settlement, Profile 7px. A source-baseline check also reproduced Practice's 320px recognition-row reserve mismatch (68px placeholder versus approximately 99–100px ready content).
- **Implemented:** shared 64px **minimum** header row, 8/16px token padding, common 20px title role and wrapping, 44px Profile actions and matched placeholders. Long titles grow normally; content/page heights remain natural. The existing noninteractive Practice shell now shows already-known localized headings and row text with the ready rows’ typography and chevron geometry. Natural wrapping replaces font-dependent pixel presets; locale changes update the pending shell. Real cards remain deferred until the authenticated map arrives.
- **Scoped result:** header/title/nav geometry passed 36 Chromium/WebKit cases (320/390/430px × UZ/RU/TJ × light/dark), including Profile pending/error/retry, tab navigation, 200% title stress, 44px targets and no page errors. Header and title slots settle within 1px. This is browser-layout evidence only; **whole screens remain 🟡** for their other documented gaps.
- **Regression coverage:** expanded the existing Practice shell/card geometry test to all three locales, both motion settings and three widths; retain the <=8px anchor limit, verify pending locale switches and compare shell/ready copy. The final full browser suites and remote CI must be checked against the final commit before promotion. No auth/backend/payment/lesson/result logic changed.
- **Evidence limits:** local tests use actual assets/renderers with synthetic account/API responses. External icon-font requests are omitted by the isolated fixture; glyph appearance, live accounts, installed-iPhone safe areas, real keyboard/audio, native Android and production deployment are not certified by these tests. Existing body/theme/other-screen QA remains open.
- **Analytics Impact:** header geometry and public static shell labels only, no measurement change or new event. **Monitoring Impact:** no new route/failure contract; existing diagnostics remain intact. **Performance Impact:** same requests/lazy mounting; corrected reserved geometry, no claimed network/LCP improvement. Backend/SQL changes are not applicable to this presentation-only slice; the repository’s native PostgreSQL CI also remains required when triggered.
- **Source guards:** preserve the original 10,553 physical source lines and the exact existing locale/lesson-call anchors. Reviewed source fingerprints are refreshed only for the audited header CSS and public-shell display helper; original Chinese/grade/access baseline hashes and guard assertions stay intact.
- **Promotion:** PR #335 merged and remote main verified at `572d560e`; tested head `aaaebf97`, 114 local cases per browser engine and all nine PR workflows passed. Installed-device/production acceptance remains separate.
- **Next:** continue Stage 1 with measured Rating/title and detail chrome, retaining all existing functional controls. Close remaining checks screen by screen before moving to the next phase.

## Second Stage 1 slice — Rating/Friends chrome (2026-11-21)

- **Baseline:** fresh main `572d560e`. At 390px, Practice text begins at y=20px, Rating at y=5px and Friends at y=9px. Rating has only a 24px title box plus margins, Friends a 36px heading; comparable root headers reserve 64px.
- **Change:** CSS-only, PWA-scoped Rating/Friends headings use the same 64px minimum row, token-based 8/16px padding, 20px/1.2 title role and natural wrapping. They retain the root sticky-header/safe-area behavior. No new controls, cards, animations or fixed page heights.
- **Preserved:** podium/list/referrals/results, ranking values, all API/navigation callbacks, Course/Lesson/Voice/checkout, Telegram and Android. All runtime changes fit the existing CSS line 588; the 10,553 source lines and locale/lesson anchors stay unchanged. Three reviewed-source fingerprints reflect only that audited CSS change.
- **Checked:** new 18-case matrix in each Chromium and WebKit engine (320/390/430 × UZ/RU/TJ × light/dark), comparing real text/header/nav anchors across initial/loading/error/retry/empty Rating and Friends states. Header anchors match Practice within 1px; long 200% localized titles wrap without horizontal clipping. API fixtures preserve owner checks and real renderers; no production accounts used.
- **Status:** PR #336 merged; remote main verified at `a25f6c68`, tested head `f3fd98ea`. All nine PR workflows passed; full local suites passed 132 cases per Chromium/WebKit engine. Whole Rating/Friends screens remain partial/unverified for untouched detail, real-device and full accessibility states.
- **Analytics Impact:** CSS-only, no measurement change. **Monitoring Impact:** no new route or failure path. **Performance Impact:** no request/caching/mount changes; only header geometry. No backend/SQL/native runtime change.
- **Next:** finish this slice’s checks and promotion, then measure existing Settings/resource/detail chrome individually. Keep completed headers intact and preserve each screen’s distinct task.


## Selective old-branch recovery — ready phrases (2026-11-21)

The owner clarified the continuation priority: preserve the substantial prepared work in `feat/pwa-professional-45-design-real-source-20261116` and progressively promote reviewed pieces. Do not let minor chrome work replace this recovery. The original local and remote source refs remain at `5cdb0cbc`; no old branch is deleted, reset or merged wholesale.

### Recovery queue

| Prepared old work | Disposition against current main |
| --- | --- |
| Compact ready-phrase cards, single expansion, separate save/audio | Recover first, using existing search/categories/favorites and UIUX-004. Scope and evidence below. |
| XP/Streak destinations and compact Profile hierarchy | Review next as one related group; reconcile real main XP/results and existing achievement data before porting. Do not claim historical mock values as live results. |
| Dictionary saved words | Preserve source; reconcile old `0158_course_saved_words` with main's `0158_course_adaptive_lessons`, owner isolation and API before porting. Existing dictionary search/filter/audio remain. |
| Checkout, onboarding and AI Voice refinements | Inspect individually after the earlier groups, preserving main's newer value-first Pro, auth/payment flow and Voice Orb/audio behavior. |
| Global Professional45 course/lesson styles | Inspect by screen; retain main adaptive/picture lesson improvements and grading. Importing the global old stylesheet would affect untouched screens and is excluded. |
| Android | Old branch has generated labels, not native screen implementations. Compare prepared PWA behavior with actual Compose screens; native acceptance remains separate. |

### Ready-phrase recovery scope

- **Baseline/provenance:** fresh main `a25f6c68`; the phrase presentation/functions and phrase-only CSS come from old source `5cdb0cbc` (`hsk-gaplar.html`, the Ready phrases section of `pwa-professional45.css`). The global stylesheet and other old screens are not imported.
- **Behavior:** only `/iphone-pwa/phrases` gets the approved collapsed Hanzi + chevron + independent audio/save actions. One card reveals pinyin, learner translation, category and copy; audio/save keep that expansion. Main's 300-phrase JSON, search normalization/ranking, category filters, local `hsk_ai_ready_phrases:v1` persistence and clipboard remain authoritative. No account-sync claim.
- **Adaptations after review:** audio uses the existing shared Mandarin static/cache/TTS helper, with stale-event protection, a bounded pending/fallback state, local retry feedback and existing `HSKResourcePause` parent-close integration. Save repaint retains expansion, active audio and keyboard focus. Four skeleton rows reserve the first four final row anchors; known All/Saved controls reserve the loading filter row. Missing action-label bundle retains the readable legacy cards. PWA focus/pressed states are local because the global old stylesheet is excluded.
- **Localization:** recover the four old canonical `readyPhrases.expand/collapse/listen/soundError` labels in UZ/RU/TJ and regenerate shared resources/token consumers. Strict catalog size becomes 1,122; exact source fingerprints follow only the reviewed UI/token changes. No Chinese lesson/source, grading/access baseline or locale/fetch anchor is relaxed. Android/bot/Desktop changes are generated catalog output only.
- **Validation:** the focused suite has 26 cases per engine, including an 18-case 320/390/430 × UZ/RU/TJ × light/dark matrix, loading-to-ready geometry, empty/search/category/saved persistence, copy, long Hanzi, keyboard and 44px targets; catalog failure/retry, missing catalog/storage fallback, stale/duplicate media failures, Chinese speech timeout, and real parent iframe pause/reopen/Back. It runs in both engines in the existing performance workflow. Full local suites/current-head CI and main promotion are recorded in the PR; until then this slice remains pending.
- **Analytics Impact:** no score, practice-attempt, progress, XP, payment or authenticated activity writer changes. Public phrase browsing, local favorites/disclosure and on-demand audio are not graded attempts; they have no verified Admin KPI, so do not report them as zero or as learning completions. Existing TTS service/provider usage path is reused, without new instrumentation or attribution claims.
- **Monitoring Impact:** local catalog/storage/media/speech failures retain explicit retry or readable fallback and are exercised in both engines. This public static browse surface has no canonical account owner, so authenticated client incident intake is not applicable to its local disclosure/favorite/audio controls; no content, phrase text, URL or local saved data is sent to diagnostics. Existing server TTS route maps to `lessons/v3_tts` and existing backend/provider failure handling stays unchanged. Other changed pages contain only generated catalog-version refreshes. No new learner API route or native behavior.
- **Performance/impact audit:** browsing makes the one existing static catalog request, never grading/account APIs; audio is user-initiated with existing cache/static/provider fallback. No schema, SQL, migration, new dependency or server is added. Graphify was current at baseline `a25f6c68` but could not uniquely resolve the nested `learner_phrases_page`; direct route/helper/parent call-site review and browser integration tests verify the dependency paths.
- **Open acceptance:** installed iPhone/Safari real-speaker output, screen reader and 200% system-text acceptance remain unverified; source/browser fixture tests do not certify those. Android native is untouched. Theme propagation from the parent resource URL remains the separately recorded existing gap.

## Selective recovery — XP/Streak destinations

- Source: Professional45 `5cdb0cbc`, **first progress IIFE only** and its scoped progress styles. Recovered into `iphone-pwa-progress.js/css`; no second lesson self-assessment IIFE or global Professional45 stylesheet. Current adaptive/picture/value-first lessons remain intact.
- Course header and Profile streak entry open the destination through existing NavBack. Keep natural content scrolling, safe areas, 44px controls, keyboard focus/return and the existing underlying screen. Small/newer iPhone widths and UZ/RU/TJ/light/dark have focused Chromium/WebKit coverage; installed-device, screen-reader and production acceptance remain open.
- Values come from the verified current map: total/daily/weekly XP, streak/record, account-local date and current-week activity. Missing values remain unknown. Only server-known week dates show activity/missed status; today is not labelled missed before the day ends, future days have their own label, and the rest of the month is unknown. No synthetic XP history or month-wide streak inference.
- Recovered the old narrow strict `streak_target_days` preference field, response and `study_setup` read field for existing 7/14/30/50-day aspirations; no migration or XP/scoring/access rule change. Saving waits for an acknowledgement, disables competing selections, bounds pending work to 10 seconds, retains the prior goal on failure and fences obsolete owner/map replies. The PWA route returns 503 after an uncommitted write fails; authenticated owner/origin/CSRF/save/reload/rollback coverage is also included in the existing disposable PostgreSQL CI fixture.
- Repaired prepared-source defects: dark root/header now use the existing semantic paper token; calendar unknown/future/current-day semantics; Russian day plurals; focus restoration after WebKit pointer activation and pending selection; bounded save failure and close/reopen behavior. Canonical 32 UI keys are generated for all three locales, with shared consumer token/count plumbing only.
- **Analytics Impact:** progress browsing does not write learning/reward/payment events. The existing preference changes the learner's aspiration only; no new KPI, attribution or fake activity. **Monitoring Impact:** existing app-shell preference route/server 5xx reporting remains; browser app-shell feature-specific monitoring is still not instrumented. Exact unchanged assessment token consumers retain their reviewed partial status. **Performance Impact:** no new progress API/list query, no polling or history store; reuse the current in-memory verified map and existing bounded refresh. No latency/LCP improvement claimed.
- Final-head CI and promotion are pending until evidenced in the PR. The rest of Profile hierarchy, dictionary bookmarks and native Android remain separate slices.


## Installed PWA trial / Profile Pro entry (owner request, 2026-11-21)

- **Observed gap:** Course trial helpers required Telegram initData, so verified browser PWA learners had no trial entry after installing. The existing Li runtime also redirected a saved learner back to Course, and its public guest page prohibited framing. Profile started on the HSK 3.0 card even for current 3.0 learners.
- **Small scoped change:** reuse the existing Course checkout layer and existing Li trial scenes in an authenticated `offer=trial` mode. A first eligible standalone opening presents that mode once per verified owner on this device; the key records presentation only. Explicit Pro entry offers the unused trial first, with an explicit paid option. The server still decides eligibility, risk and the one-time grant; only the final seven-day trial CTA posts to the existing CSRF endpoint. No onboarding choices are resubmitted.
- **Profile:** Pro is the first PWA carousel slide; current HSK 3.0 learners do not receive its redundant promotional slide. Actual paid/trial/temporary states take precedence over a missing legacy plan label. Other hosts keep their previous ordering.
- **Preserved:** existing inline limit offers, manual/Lava checkout, already-used trial behavior, real Pro renewals, foundation/lesson/deep-link intent, saved account choices and legacy onboarding. A late-loading bridge waits at the existing boot continuation; the trial welcome has a visible 44px close control. The foundation continues after dismissal or a confirmed access-map refresh. A new section/sheet or explicit purchase intent supersedes a delayed automatic eligibility read, so it cannot start a foundation or trial above the learner's new action.
- **Safety/performance:** the optional same-origin frame requires a real PWA session; public guest onboarding remains frame-denied. Parent and child verified actors, read-owner headers and the current map fence obsolete responses. Bounded/deduplicated eligibility reads reuse current APIs; no polling, new schema, DB query or cached entitlement. Paid renewal does not depend on the trial read.
- **Analytics Impact:** reuse canonical ProTrialService and route-set `iphone_pwa` / existing `pwa_onboarding` source, then the existing paid checkout source/events. No new event, KPI definition or onboarding completion. Existing analytics cannot distinguish installed/profile trial impressions; those values remain unavailable.
- **Monitoring Impact:** existing session/onboarding/checkout diagnostics and mapped server trial routes remain. Exact reviewed source/route exceptions preserve the partial subscription-entry and Telegram monitoring cells; no broader failure-to-Inbox coverage claim. Retry/timeout/unknown-ack/local error behavior is covered by behavioral tests, without sending private content.
- **Verification:** focused installed/profile cases use real bundled Li/Course assets with synthetic verified actors, UZ/RU/TJ and 320/430px screens in Chromium/WebKit. They cover no automatic grant, final confirmation, used/failed/lost-ack trial, owner switch, paid renewal, pending Back and late-script/foundation continuation. Existing onboarding/install/inline checkout suites and real cookie/CSRF/actor/CSP tests are required before promotion. Current final-head CI and promotion are pending; physical Home Screen Safari, screen-reader, provider payment and production acceptance remain unverified.
