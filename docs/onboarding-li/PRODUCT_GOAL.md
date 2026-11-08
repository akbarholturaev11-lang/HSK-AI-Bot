# HSK AI — Li Panda Onboarding | PRODUCT GOAL

> **Maqom:** implementation uchun tasdiqlangan maqsad/acceptance contract. Bu hujjat bajarilgan ishlar ro'yxati EMAS. Haqiqiy progress: [IMPLEMENTATION_CONTEXT.md](IMPLEMENTATION_CONTEXT.md).
>
> **Qamrov:** PWA (iPhone/browser) + Telegram Mini App uchun **bitta umumiy web onboarding**, har bir platformaning xavfsiz auth adapteri bilan. Android native onboarding UI shu taskda qayta chizilmaydi. Shared backend/schema o'zgarishlari barcha clientlarga mos kelishi kerak.
>
> **Audit bazasi (updated 2026-11-08):** `main` commit `ffbff9492e0713686f57a76443bef17a45c4041c` (includes PWA inline Pro and verified 20% exit offer, migration 0153, Dockerfile and Railway build fix). **Railway production SUCCESS for this exact SHA** on 2026-11-08; this confirms deploy, not onboarding implementation or new feature tests.

## Updated 2026-11-08 integration contract — new main 401de151

The existing learner PWA now has a **PWA-only inline Pro limit paywall** with compact panda hero, server-priced 1-month and 12-month choices (3-/6-month and manual payment under other tariffs), real Lava provider checkout, authenticated per-attempt funnel, 24-hour single-use provider-configured **20% exit_offer**, and content-hashed route injection. This code is **not** the onboarding trial screen. Reuse its authenticated billing/entitlement services where appropriate; do not copy its paywall modal onto Telegram Mini App or let onboarding show the exit offer without a separate approved product rule. Payment success remains server/webhook-owned.

- New PWA limit module: `app/static/course_v3_data/iphone-pwa-inline-pro.{js,css}`, `iphone-pwa-inline-pro-bridge.js`. `app/api/pwa_auth.py::_pwa_inline_html` injects them only in authenticated course/practice/checkout routes. `/iphone-pwa/onboarding` is NOT injected. Shared `course-v3.html` and Mini App static HTML were deliberately left unchanged in new main.
- New PWA funnel: `/api/v3/pwa/subscription/inline-event` CSRF+allowlisted stage/source, `inline_preview` to avoid counting mere price display as checkout, and server-only verified Lava paid event. **Onboarding events must use their own event namespace**, not falsely be counted as `pwa_pro_opened` from a limit hit.
- New schema head: `0153_pwa_inline_funnel`, after `0152_pwa_exit_offer`; onboarding migrations branch from the current real head, NEVER from the previously audited `0151`.
- **Important public entry gap:** `/iphone-pwa/onboarding` currently requires a PWA session, and `/iphone-pwa` redirects already authenticated users to course. The new panda-first `account` → `signup/login` flow therefore needs a safely served public shell and a verified auth-return/draft bridge. Do not simply remove route authentication from private onboarding endpoints.
- Current PWA-only inline paywall keeps its strings in inline `WORDS` JS despite the repository's canonical-localization rule. Do NOT copy that pattern into onboarding; canonical UZ/RU/TJ catalogs remain mandatory. Avoid unrelated paywall refactor unless its actual integration requires it.
- New main doesn't change the existing trial PWA endpoint gap, 48h push/reminder code, Smart Reminder policy, scalar goal, streak target absence, or original book JPEGs. The existing onboarding task remains necessary.

## First implementation slice (in progress; not final)

- An additive migration `0154_li_onboarding_choices` and server PWA/Mini App onboarding adapters now accept optional `goals[]`, `streak_target_days`, `preferred_focus`; older scalar `goal` clients remain valid. This does NOT yet provide 23-state UI or Smart Reminder integration.
- The existing shared onboarding HTML now paints an honest server-owned course-track loading/error/retry state on its version screen. This is only the first global loading use, NOT completion of the 23-state loading contract.
- Associated unit/PWA API/Playwright tests are authored but require actual CI run; test status recorded in `IMPLEMENTATION_CONTEXT.md`.
- Production code stays unchanged until a future tested merge; do not silently promote partial onboarding.

## 2026-11-09 — iPhone PWA Home Screen video requirement

- On iPhone/iPad browser ONLY after verified first-time PWA OAuth account signup AND successful server onboarding save: offer a short optional Home Screen install guide before Pro eligibility. Never show to returning learners, Telegram Mini App, native Android, or already installed standalone PWA.
- The original 23 demo scenes and words remain unchanged. This is an optional post-registration sheet, not a parallel auth/progress/trial service. Close and Continue must both lead to the existing real course/Pro path. Never automatically request OS notification permission.
- Reserve the reviewed portrait 9:16 screencast at app/static/assets/onboarding/iphone-home-screen.mp4; serve only that exact public file from /assets/onboarding/iphone-home-screen.mp4. **Actual approved MP4 absent as of this checkpoint.** Show RU/UZ/TJ step instructions immediately; never display an empty or fake video while loading or after 404. Show video only after real metadata.
- Textual steps verified against https://support.apple.com/en-gb/guide/iphone/iph42ab2f3a7/27/ios/27 : Safari Page Menu → Share → Add to Home Screen → Add. Review the eventual video against current iOS Safari UI, scrub personal data, and check on real iPhone.
- Per-account local device prompt state may prevent repeat suggestions, but cannot imply installation actually happened. Keep Pro, PWA push, payment, streak, auth, trial and course state unchanged.
- Acceptance: actual Safari non-installed signup = prompt; installed PWA/Mini App/desktop/Android/returning user = no prompt; no video asset = immediate 3-step fallback; approved MP4 = functional native player with controls/playsinline; Close/Continue = expected next onboarding step; safe user switch, accessibility, reduced-motion and static asset cache version validated.

## 1. Bosh maqsad

Foydalanuvchi HSK AI'ga birinchi kirganda **Li panda qatnashgan 23-state interaktiv demo**ga imkon qadar **1:1 mos** UI/UX ko'radi. Ekranlarning joylashuvi, animatsiyasi, panda pozasi, tanlovga javobi, matni (RU/UZ/TJ), visual ierarxiya va Pro slaydlari demodagidek bo'ladi. Lekin login, data loading, HSK access, lesson start, Pro/trial, reminder, analytics va save **mock emas — real server kontraktlari** bilan ishlaydi. Mavjud kurs/progress/to'lov xavfsizligi buzilmaydi.

### Manbalar ustuvorligi

1. **Visual va ko'rsatiladigan matn:** foydalanuvchi bergan `Hsk ai onboarding li demo.html`, handoff paketida `DEMO_REFERENCE_ONLY.html` nomi bilan. **SHA-256 verified from the local original user upload** (99,339 bytes): `767c2de59116229dab9304e3036ae589399379340013f1d137eae7df82644b30`. Ilgari chatda yaratilgan `HSK_AI_CODEX_HANDOFF(1).zip` ichida `DEMO_REFERENCE_ONLY.html`, `SCREEN_MAP.md`, `CODEX_TASK.md` bor. **The full exact demo is now pinned in this same branch at [`docs/onboarding-li/DEMO_REFERENCE_ONLY.html`](DEMO_REFERENCE_ONLY.html).** Coding agent must preserve this file as visual/copy reference; it is NOT a live UI route. Before claiming 1:1 production fidelity, compare source, rendered states and catalog strings to this pinned file.
2. **Real capability/behavior/security:** shu vaqtdagi repository `main`, mavjud services/API/tests; demo'dagi soxta behavior ishlab chiqarishga ko'chirilmaydi.
3. **Repository qoidalari:** `AGENTS.md`, `AI_RULES.md`, `PROJECT_MEMORY.md`, `.agents/skills/hsk-ai-ui/SKILL.md`, `localization/README.md`. HSK AI OpenSpec faqat talab qilinadigan yuqori xavfli delta uchun va mavjud scoped handoffga bog'liq holda.

**Murosasiz copy qoidasi:** demo matnini parafraz qilma, qisqartirma yoki mayda izohlar bilan to'ldirma. 3 tildagi barcha ekran/option/Panda reaction/slayd matnlari aynan olinadi va **canonical localization** orqali tarqatiladi; HTML demo runtime tarjima lug'ati sifatida ko'chirilmaydi. Faqat "Demo: bu yerda kirish bajarilmaydi" turidagi mock-only matnlar, unavailable provider va dalil bilan qo'llab bo'lmaydigan push/access va'dalariga zarur safe runtime exception ruxsat etiladi; har bir exception `IMPLEMENTATION_CONTEXT.md`da qayd etilsin.

## 2. 23 visual state va ma'lum ketma-ketlik

| # | State | Yakuniy ko'rinish/harakat |
| --- | --- | --- |
| 1 | `account` | O'ylanib qolgan **Li panda**; faqat "birinchi marta" / "hisobim bor" asosiy tanlovlari va RU/UZ/TJ til; keraksiz izohsiz |
| 2 | `login` | Oldingi akkauntga **haqiqiy** Google/Telegram (Apple faqat ishlasa) provider login, login-only matn |
| 3 | `hello` | Li ustoz salomi |
| 4 | `intro` | 5 qisqa savolga o'tish |
| 5 | `loadCourse` | Kurs ma'lumotlari olinayotganda shu ekran darhol ochilib, load progress ko'rinadi; javob bo'lsa o'tadi |
| 6 | `version` | Server-confirmed HSK 2.0 / 3.0 tanlash, **haqiqiy hozirgi HSK kitob rasmlari** |
| 7 | `level` | Track'ga mos faqat live/allowed darajalar, Li reaction |
| 8 | `goal` | 5 goal; **multi-select**, tanlangan har biriga Li reaction; serverda barcha tanlovlar saqlanadi |
| 9 | `time` | 5/10/15/20/30 minut, Li reaction |
| 10 | `focus` | speaking/listening/vocabulary/grammar/none, Li reaction |
| 11 | `ready` | Birinchi dars oldi encouraging state |
| 12 | `loadLesson` | Dars data/handoff uchun real loading state, fake delay yo'q; unga mos intro / preview UI |
| 13 | `habit` | Har kuni o'qish odati haqidagi Li nutqi |
| 14 | `streak` | 7 / 14 / 30 / 50 **target day**, haqiqiy current streakdan mustaqil |
| 15 | `profile` | Progressni saqlash uchun profil taklifi |
| 16 | `signup` | Haqiqiy provider signup; anonim draft authenticated canonical userga xavfsiz bog'lanadi |
| 17 | `pro` | Server trial eligibility'ga asoslangan 7-day Pro taklif; skip/close mavjud |
| 18 | `trialIntro` | Pro introducton visual |
| 19 | `trial1` | Demo dark benefit slide 1 |
| 20 | `trial2` | Demo dark benefit slide 2 |
| 21 | `trial3` | Demo dark benefit slide 3 |
| 22 | `trialDone` | **Faqat** server successful trial activation/statusdan keyin |
| 23 | `end` | Demo `restart()` emas, mavjud course'ning **real birinchi darsi**ga o'tish |

Visual state soni server route soni degani emas: bitta robust state machine ishlatish mumkin. Telegram launch mavjud signed `initData` bilan allaqachon authenticated bo'lsa, `login/signup`da ortiqcha qayta login talab qilinmaydi; demo ketma-ketligi real account state'ga mantiqan moslanadi. Existing user `onboarding_completed` va real progress asosida to'g'ri resume'ga ketadi, kurs boshidan majburan boshlamaydi.

## 3. UI/UX majburiy qoidalari

### A. Har bir server-dependent UI — immediate shell + honest loading

**Global qoida, faqat `loadCourse` emas.** Onboarding ichidagi auth/provider availability, account status, HSK track/levels, course/lesson, entitlement/trial, push status, saved goals/time/focus/streak va other remote resources quyidagi modelga amal qiladi:

1. **Immediate paint:** route/state bosilishi bilan ekran ochiladi; API tugaguncha oq/bo'sh/qotgan viewport bo'lmaydi.
2. **Visible loading:** Li animation yoki mos skeleton/progress, aynan ma'lumot keladigan joyda; geometrik joy oldindan band — layout shift kamayadi. Demo loading grafikasini saqla, yangi ortiqcha copy qo'shma.
3. **Real network handshake:** barcha loading server/cache readiness'ga bog'liq; demo `setTimeout(2200)` va majburiy sun'iy delay'lar yo'q. Cache ma'lumot `stale` bo'lsa background refresh indicator bilan ajrat.
4. **Safe completion:** successda yengil fade/transform (reduced-motion hisobga olinadi), data bir marta render; 401/403/timeout/offline/retry holatlari shell ichida paydo bo'ladi.
5. **Race safety:** ketma-ket HSK track/level, back/forward va OAuth return eski request response'ini yangi state ustiga yozmasin; AbortController/request version guard.
6. **Interaction:** asossiz bloklangan tugma/spinner; double-submit guard; retry faqat idempotent yoki status reconciliation bilan; ekran local selection'ni ushlab qoladi.
7. **PWA/Telegram:** Telegram safe area, iOS Safari/Home Screen, kichik viewport, no horizontal overflow, clean header/progress, soft keyboard va prefers-reduced-motion.

### B. Visual fidelity

- Li panda **`think/wave/point/read/write/cheer/hug`** pozalari va demo selection reactions **1:1**.
- Character source tekshir: `app/static/assets/characters/hsk-character-pack.js` va hozirgi `course_v3_onboarding.html`. Duplicated character runtimes bo'lmasin.
- Pro dark slides, icons, shape, CTA, illustration, spacing, color va transitions demo visual bilan mos.
- **Yagona rasm istisnosi:** demo fake book graphics o'rniga mavjud real originallar:
  - `app/static/assets/hsk20-course-books.jpg`, runtime `/assets/hsk20-course-books.jpg?v=20261003c`;
  - `app/static/assets/hsk30-course-books.jpg`, runtime `/assets/hsk30-course-books.jpg?v=20261003c`.
- Mobile-first, bitta aniq primary action/ekran; birinchi ekranda panda va ikki tanlov markazda.
- Demo'dagi real bo'lmagan dars/test/voice artwork faqat preview ko'rinishi, real natija va reward deb taqdim qilinmaydi.

## 4. Haqiqiy ma'lumot va account kontrakti

### Auth, draft, access
- PWA — real same-origin cookie + CSRF, `PwaAuthService`, Google/Telegram OAuth callbacks; Apple faqat provider configured va end-to-end ishlayotgan bo'lsa ko'rsatilsin. Mini App — har server actionda verified Telegram `initData`; anonim/browser draft auth o'rnini bosa olmaydi.
- Signup oldi `{language, track, level, goals[], daily_minutes, focus, streak_target_days, step}` temporary nonsecret draft saqlansin; authenticated canonical `users.id`ga **bir marta** va qayta kirishda moslanib yozilsin. Cancel/callback/retry/back/device/account switch no account collision.
- Existing login / onboarding already done / incomplete case'lari ajratilsin; account merge, progress reset, subscription overwrite, payment/referral overwrite yo'q.
- HSK 2.0/3.0 `CourseTrackService` server status va entitlement'ga amal qiladi. UI allowed level bilan access'ni adashtirmaydi; demo yangi HSK 3.0 Pro unlock bermaydi. Real `lesson_1` navigatsiyasi oldingi user progressini buzmasin.

### Goals, daily time, focus
- 5 goal ID: `hsk_exam`, `daily_communication`, `travel`, `work_china`, `study_china`.
- Current DB `CourseMiniAppProfile.goal` scalar; multi-select'ni UI only qilma. Additive `goals_json` (yoki auditda asoslangan ekvivalent) + legacy primary `goal` moslik; API/serialization/learning-signals/daily-plan deterministik va versioned bo'lsin. Eski goal'ni yo'qotma, frozen daily plan'ni ortdan mutatsiya qilma.
- `daily_minutes`: 5/10/15/20/30; `preferred_focus`: speaking/listening/vocabulary/grammar/none. Onboardingda to'ldirilgan bo'lsa `course-v3.html` post-first-lesson **yana** so'ramaydi; existing users'ning pending setup'i o'z holida.
- Draft server tasdiqidan oldin `onboarding_completed` va `goal_chosen_at` noto'g'ri yozilmasin. Save exception/retrydan so'ng statusni GET bilan reconciliation qilib, duplicate dangerous writes qilma.

### Streak va Smart Reminder — bir maqsad emas, integratsiyalashgan signal
- `streak_target_days` in {7,14,30,50} **serverda saqlanadigan target**, default old users uchun null; `current_streak` va `longest_streak` haqiqiy learning activity asosida `CourseGamificationService`da hisoblanadi. Targetni tanlash streak yoki XP'ni oshirmaydi.
- Smart Reminder existing verified XP/daily goal/plan/timezone/quiet hours/consent/destination + current streak/last activity/streak target'dan **qo'shimcha planning context** oladi. Suggested fields: actual streak, selected target, verified learned_today, at-risk-if-not-studied, target progress; server-only calculated. Aim: relevant reminder copy/urgency/time judgement; hech qanday fake loss/gain.
- `MotivationReminderService`ning legacy streak/daily reminders bilan bir account/local-day uchun **bitta notification ownership/dedupe**; PWA, Telegram, Android duplicate study reminder chiqmasin. Smart OFF, permission denied, no session, quiet hours, D1 holdout, manual locked destination va cadence budget guardlari o'z kuchida.
- Smart Reminder onboarding orqali **avtomatik ON bo'lmaydi**. Foydalanuvchi consent va OS permission alohida. Data bo'lmasa smart confidence oshirilmaydi yoki inference bilan kunlar to'ldirilmaydi.

## 5. Pro trial va PWA Web Push: 2 kun oldin

- 7-day trial taklifini server `ProTrialService` va actual eligibility boshqaradi. Start only verified, `trialDone` only successful server confirmation; paid/already_used/denied/ineligible/risk-blocked/offline/cancel shows honest state and free continuation.
- **PWA uchun 2 kun oldingi real push**: serverdagi `pro_trial_ends_at - timedelta(hours=48)` threshold bo'yicha durable event, scheduler late/start/retry va duplicate-proof outbox. `TrialReminderService` hozir `REMINDER_DAYS=(2,0)` + floor `.days` qo'llaydi: implementatsiyada bu 48-hour scheduling bilan to'g'rilansin; last-day policy bilan duplicate bo'lmasin.
- Mavjud `learner_pwa_push.py`, PWA subscription API, service worker, one-minute dispatcher qayta ishlatiladi. PWA Home Screen/permission/valid VAPID subscription zarur; `PWA_PUSH_ENABLED` va `PWA_PUSH_SEND_ENABLED` default false, **real production env holati tasdiqlanmagan**.
- Browser push OS/user opt-in bo'lmagan holatda push yuborildi deb da'vo qilma. Demo'dagi "2 kun qolganda eslatma yuboramiz" matni faqat foydalanuvchida real deliverable channel tasdiqlansa ko'rsatilsin; aks holda runtime-safe capability-specific copy/permission step; demo visual/i18n qoladi. Push receipt provider accepted != device displayed.
- Subscription cancelled/revoked, trial expired/ended, Pro paid yoki stale source bo'lsa enqueue/send revalidation. Account/email/Pro copy lock screen'ga sezgir ma'lumot chiqarmaslik: existing generic push + authenticated in-app notification; tailored copy only after security review.
- At most one 48h notice and other existing approved final-day notice; no extra spam; no silent PWA auto-subscribe. Push tap correct authenticated course/Inbox/Pro context'ga olib boradi.
- Google-only PWA users uchun Telegram link majburiy emas; no-PWA cases Android/Telegram fallback'ni buzmasin.

## 6. Analytics va i18n

- Existing `CourseMiniAppAnalyticsService` va allowlisted event names/dedupe yo'lidan foydalan; PWA browser cookie+CSRF adapter va Mini App signed adapter alohida. Event types: entry route, new/existing, step view/back/select, track/level, goals count (avoid personal sensitive payload), time/focus/streak target, draft recovered, auth chosen/outcome, onboarding server complete, trial eligible/offered/start/skip/fail, first lesson start, errors and abandonment. No PII, double count, or anonymous-to-other-account attribution.
- Canonical strings `localization/ui/{ru,uz,tj}/{course,common,miniapp}.json`; `python3 scripts/i18n_build_all_catalogs.py --write` and `--check`. Demo RU/UZ/TJ texts and all reactions/slides must match exactly unless logged exception.
- PWA service worker/static version bump and cache freshness for changed JS/CSS/catalogs.

## 7. Out of scope / protected invariants

No wholesale Android native redesign, no new parallel payments/trial system, no fake new streak XP/rewards, no account/progress resets, no invalid HSK 3.0 unlock, no global Smart Reminder opt-in, no duplicate notification engines, no admin PWA behavior changes. Existing lessons/quiz/homework/answer grading, referral/Pro/payment/Play compliance, desktop parity, bot semantics remain working.

## 8. Definition of Done — measurable acceptance

- [ ] Visual regression for **all 23 states** against the hash-verified demo, RU/UZ/TJ and mobile screen widths; all original demo strings checked (documented exceptions only); original book JPGs rendered.
- [ ] PWA and Telegram Mini App complete the same design with platform-safe account entry, OAuth/Telegram trust boundaries; existing users resume without accidental onboarding.
- [ ] Every remote-dependent screen: immediate shell, loading, success, error, retry, race/back/cancel, no fake delay; iOS install/safe-area/reduced-motion; no console errors.
- [ ] Multi-goal and time/focus/streak target are persisted on server and reloaded correctly; old users and daily plans unaffected; no repeated study setup.
- [ ] Server course track/level entitlement and first lesson verified for Free/Trial/Pro, HSK2.0/3.0, original progress safe.
- [ ] Trial offer actual eligibility, verified activation, skip/free path; no unverified success/automatic charge promise.
- [ ] 48-hour PWA trial reminder scheduled, deduped, consented, delivered to permitted subscribers via existing outbox; disabled/denied/revoked/uninstalled paths honest; generic privacy policy preserved; final-day/legacy behavior regression-tested.
- [ ] Smart Reminder receives verified streak context (target distinct), consent/quiet/cadence guards unaffected, cross-channel and legacy duplicate reminders prevented.
- [ ] Analytics funnel and dedupe verified, canonical UZ/RU/TJ catalogs generated, PWA cache updated.
- [ ] Related API/unit/migration, integration and Playwright/browser tests run with explicit results; smoke tested on supported actual PWA/Mini App devices or marked **not verified**. No claim of production validation without evidence.
- [ ] Feature-scoped progress file kept accurate; impactful permanent design/schema decisions reflected in `PROJECT_MEMORY.md` per repository rule.

## 9. Delivery slices / risk

**P0** clean branch, baseline, migration head, demo integrity; **P1** shared UI/state machine and original asset visuals; **P2** global loading contract; **P3** authenticated draft/identity PWA+Telegram; **P4** multi-goal+time+focus+streak schema; **P5** real course/entitlements/lesson; **P6** Pro trial; **P7** PWA 48h push; **P8** Smart Reminder + legacy ownership; **P9** analytics/i18n; **P10** regression/visual/device checks and release decision.

Each slice is incomplete until applicable tests are actually run and its checkpoint recorded in [IMPLEMENTATION_CONTEXT.md](IMPLEMENTATION_CONTEXT.md). Branch/merge/release actions follow `AGENTS.md`; this document authorizes **no automatic production deployment**.
