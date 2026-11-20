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
| Ready phrases/search/categories/saved/copy | 🟡 | `hsk-gaplar.html` `createPhraseCard`. Existing saving/filtering stays; compact single expansion and independent audio remain absent. |
| Recognition and results/limit | 🔍 | `course_v3_recognition.html`. Check answer/retry, quota and return navigation. |
| Memorization and its learning steps/results | 🔍 | `course_v3_memorize.html`. Verify required text, natural scroll and progression. |
| Pronunciation/mic/skip/done | 🔍 | `course_v3_pronunciation.html`. Check permission/failure and reachable controls. |
| Mistakes overview/review/builder/results/limit | 🔍 | `course_v3_mistakes.html`. Keep latest format fix; verify empty/error, submit and completion. |
| Test centre/placement/exam/results | 🔍 | `course_v3_test.html`. Check long questions, submit pending/error and saved result. |
| AI Voice root/quota | 🔍 | `renderVoice`. Check quota loading/error geometry independently of immersive conversation. |
| AI Voice V8/conversation/topics/settings/hints/end/restart | 🔍 | `iphone-pwa-voice.html`. Preserve Orb; independently check keyboard, safe areas, audio and state changes. |
| Rating/league/Friends/referrals/user detail/challenges/invite | 🔍 | `course-v3.html` rating functions. Rating/Friends chrome aligned in the second Stage 1 slice below; long-name/device and other nested-flow checks remain open. |
| Profile/accuracy/streak/achievements | 🟡 | `renderProfile`. Root header alignment accepted in PR #335; streak calendar plus separate 30-day achievement repeats information. Keep real 100-lesson/access data. |
| XP/Streak detail destinations | 🟡 | Course header has passive chips; approved full-screen destinations are absent on main. Existing goal picker is not an XP detail page. |
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
- **Status:** scoped checks passed; final full suites/current-head CI and main promotion must still be verified. Whole Rating/Friends screens remain partial/unverified for untouched detail, real-device and full accessibility states.
- **Analytics Impact:** CSS-only, no measurement change. **Monitoring Impact:** no new route or failure path. **Performance Impact:** no request/caching/mount changes; only header geometry. No backend/SQL/native runtime change.
- **Next:** finish this slice’s checks and promotion, then measure existing Settings/resource/detail chrome individually. Keep completed headers intact and preserve each screen’s distinct task.
