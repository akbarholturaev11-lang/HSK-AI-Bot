# PROJECT_MEMORY.md

## 1. Project Identity

Project name: Unknown / needs inspection  
Project type: Telegram Bot / Mini App / Website / Backend / Other  
Main purpose: Unknown / needs inspection  
Target users: Unknown / needs inspection  
Current status: Unknown / needs inspection  

Short description:
- This project is built to: Unknown / needs inspection
- Main user problem: Unknown / needs inspection
- Main business goal: Unknown / needs inspection

---

## 2. Core Architecture

Frontend:
- Unknown / needs inspection

Backend:
- Unknown / needs inspection

Database:
- Unknown / needs inspection

Hosting:
- Unknown / needs inspection

Bot framework:
- Unknown / needs inspection

AI provider/model:
- Unknown / needs inspection

Payment system:
- Unknown / needs inspection

External services:
- Unknown / needs inspection

---

## 3. Important Project Rules

- Do not redesign the whole architecture without explicit request.
- Do not remove working logic unless there is a clear reason.
- Make minimal safe changes.
- Keep user/payment/subscription logic stable.
- If database schema changes, document the migration.
- If environment variables change, update `.env.example`.
- Never write secrets, API keys, tokens, passwords, or private URLs in this file.
- Before changing payment, subscription, or access logic, check the current flow first.
- If something is unclear, inspect the code first instead of guessing.

---

## 4. Memory Update Policy

This file is NOT a daily diary and must NOT become a dump of every small change.

Only update this file when the change is important for future AI assistants to understand, debug, or safely continue the project.

Update this file only for:
- Architecture changes
- Database schema changes
- Payment logic changes
- Subscription logic changes
- User access logic changes
- Important user flow changes
- Deployment or environment changes
- AI prompt behavior changes
- Course or lesson logic changes
- Important business logic decisions
- Major bug fixes
- Security-sensitive changes

Do NOT update this file for:
- Small text edits
- Emoji changes
- Typo fixes
- Minor UI/CSS changes
- Console log cleanup
- Small refactoring with no logic change
- Temporary experiments
- Changes already obvious from the code

Before updating memory, ask internally:

> Will this help another AI assistant understand, debug, or safely continue this project later?

If the answer is no, do not update this file.

When updating memory, keep it short and useful:
- What changed
- Why it changed
- Files touched
- Risk / follow-up if needed

Never turn this file into a long changelog.

---

## 5. Key Files and Folders

Main files:
- `main.py` — Unknown / needs inspection
- `bot.py` — Unknown / needs inspection
- `database.py` — Unknown / needs inspection
- `config.py` — Unknown / needs inspection
- `handlers/` — Unknown / needs inspection
- `keyboards/` — Unknown / needs inspection
- `services/` — Unknown / needs inspection
- `miniapp/` — Unknown / needs inspection
- `.env.example` — Unknown / needs inspection

Important note:
- Do not rename or delete important files unless necessary.

---

## 6. Database Schema Summary

### users
Purpose: stores Telegram users and access status.

Important fields:
- `telegram_id`
- `language`
- `status`
- `payment_status`
- `subscription_until`
- `question_limit`
- `questions_used`

### payments
Purpose: stores payment requests and confirmations.

Important fields:
- `payment_id`
- `telegram_id`
- `amount`
- `payment_code`
- `status`
- `created_at`
- `confirmed_at`

### logs / history
Purpose: stores important user actions or AI interactions.

Important fields:
- Unknown / needs inspection

---

## 7. Current Business Logic

### User onboarding
Current flow:
1. Unknown / needs inspection

### Subscription logic
Current logic:
- Free trial: Unknown / needs inspection
- Paid plans: Unknown / needs inspection
- Question limits: Unknown / needs inspection
- Expiration logic: Unknown / needs inspection
- Access blocked when: Unknown / needs inspection

### Payment logic
Current logic:
- Payment method: Unknown / needs inspection
- Manual approval: Unknown / needs inspection
- Auto approval: Unknown / needs inspection
- Admin notification: Unknown / needs inspection

### AI logic
Current logic:
- Unknown / needs inspection

---

## 8. Current Features

Working:
- Unknown / needs inspection

Partially working:
- Unknown / needs inspection

Not built yet:
- Unknown / needs inspection

---

## 9. Important Decisions

### Decision 1
Date: 2026-07-22
Decision: Course material must teach useful, real Chinese first. Sessions should be short and interactive, with honest immediate feedback, visible progress, XP/streak/challenge rewards, and mistake recovery providing appropriate motivation without replacing learning.
Reason: Product quality and retained knowledge are the goal; engagement mechanics exist to prevent boredom, not to inflate fake progress.
Risk: Never expose answer keys, award repeatable/fake XP, or use rewards that are disconnected from verified learning activity.

---

## 10. Recent Important Changes

### 2026-08-11 — Course v3 lesson access policy is admin-controlled

Changed:
- Course v3 protected lessons now use a stored `course_lesson_access_policy`
  bot setting instead of a hardcoded subscription-only gate.
- Admin Mini App has a `Kurs access` management panel with three modes:
  existing subscription paywall, ad-required access, and temporary free access
  until a selected expiry.
- Lesson ad authorization is bound to `feature=lesson`, server user level,
  lesson order, and opaque `access_ref`; replaying a practice ad or another
  lesson's ad authorization must not unlock the lesson.

Why:
- Admin needs to run paywall, ad-supported, or short free campaigns without
  code changes while preserving the original subscription behavior as default.

Files touched:
- `app/services/course_access_policy_service.py`
- `app/services/course_miniapp_access_service.py`
- `app/main.py`
- `app/static/course-v3.html`
- `app/static/course_v3_data/ads.js`
- `app/static/admin.html`
- `app/services/admin_miniapp_service.py`

Risk:
- Ads mode requires at least one active Course v3 ad creative; otherwise free
  users cannot complete protected lessons via the ad path.

Follow-up:
- After deploy, admin should switch modes once in the real Admin Mini App and
  smoke-test protected lesson 3 as a free user in subscription, ads, and
  temporary free modes.

### 2026-08-11 — Desktop updater is manual-install only

Changed:
- Desktop app still checks for available updates and shows the update banner,
  but it no longer downloads/installs automatically after a delay.
- Installation starts only from the visible update action button.

Why:
- Local/dev and production users must not lose the current app window or have a
  new version downloaded unless they explicitly choose to install it.

Files touched:
- `desktop/ui/js/app.js`
- `desktop/ui/js/i18n.js`
- `desktop/ui/test-contract.mjs`

Risk:
- Update availability still depends on the existing updater endpoint. Manual
  install still restarts the app after the user clicks install.

Follow-up:
- In a real signed build, verify that an available update shows the banner and
  does not start download progress until the install button is clicked.

### 2026-08-11 — Mini App ad surfaces show desktop download CTA

Changed:
- Telegram Mini App course/ad completion surfaces now mount the existing
  Mac/Windows desktop download CTA inline after ad completion, independent of
  modal promo cooldown.
- The inline CTA still respects download availability, recent download request,
  and already-installed desktop state.

Why:
- Desktop app promotion must be visible exactly where free users already see
  course/practice ads, without blocking lesson, quiz, or homework logic.

Files touched:
- `app/static/course_v3_data/desktop-download.js`
- `app/static/course_v3_data/ads.js`
- `app/static/course-v3.html`
- `app/static/course_v3_*.html`
- `tests/e2e/test_miniapp_smoke.py`
- `tests/test_course_v3_static_data.py`

Risk:
- No subscription/payment/access rules changed. Risk is limited to Mini App
  ad completion UI and desktop download CTA visibility.

Follow-up:
- After deploy, test one real Telegram Mini App lesson-end ad and one practice
  ad on a phone with Mac/Windows downloads enabled.

### 2026-08-11 — Desktop AI context-aware suggestions

Changed:
- Desktop local AI drawer now builds context from the active app screen and
  shows matching prompt suggestions for Today, open lessons, Practice,
  Vocabulary, AI Voice, Subscription, Profile, and Rating.
- Local AI prompts now include bounded visible app context and explicitly avoid
  claiming access outside the HSK AI window or revealing unchecked lesson,
  quiz, or practice answer keys.

Why:
- AI should support the current course workflow instead of behaving like a
  generic standalone chat.

Files touched:
- `desktop/ui/js/app.js`
- `desktop/ui/js/lesson.js`
- `desktop/ui/js/practice.js`
- `desktop/ui/js/vocabulary.js`
- `desktop/ui/js/voice.js`
- `desktop/ui/js/i18n.js`
- `desktop/ui/css/workspace.css`
- `desktop/ui/test-contract.mjs`

Risk:
- No payment/subscription/access rule changed. Context is gathered from local
  UI state only and is bounded before being sent to the local AI runtime.

Follow-up:
- After deploy, test the drawer inside a real desktop build with AI Pack
  installed on one open lesson, one practice question, and one vocabulary card.

### 2026-08-11 — Course notification feed for Telegram and Desktop

Changed:
- Added `course_user_notifications` storage for user-facing course/subscription
  notices that were actually sent by the bot, with dedupe by
  `telegram_id + key + dedupe_key`.
- Subscription expiry, expired/discount offer, scheduled lesson-time, unfinished
  lesson/day-end, daily goal, streak-risk, and rating-overtaken reminders now
  write in-app notification rows after successful Telegram delivery.
- Desktop course map payload now includes recent notifications, and Desktop
  shows them both in the bell panel and on the Today/home screen.

Why:
- Telegram reminders must stay visible inside the product after delivery so the
  user can reopen the app and see the same important action on desktop.

Files touched:
- `app/db/models/course_user_notification.py`
- `alembic/versions/0067_course_user_notifications.py`
- `app/services/course_notification_service.py`
- `app/services/*reminder*_service.py`
- `app/services/desktop_course_service.py`
- `app/main.py`
- `desktop/ui/js/app.js`
- `desktop/ui/css/workspace.css`

Risk:
- Medium. New table/migration and write-after-send hooks touch reminder flows,
  but no lesson order, grading, payment activation, referral attribution, or
  access rules changed.

Follow-up:
- Run migration before deploy and smoke-test one real reminder plus desktop map
  fetch with a real user.

### 2026-08-11 — Desktop lesson full-stage with docked AI tutor

Changed:
- Desktop lesson dialog now opens as a full workspace study stage instead of a
  narrow centered modal with blurred background.
- On wide screens, the existing local AI drawer auto-opens as a right-side
  tutor panel during a lesson; users can hide it with the existing close button
  or toggle it with `Cmd/Ctrl+K`. When hidden, the lesson expands to full width.
- Mobile keeps the lesson full-screen and moves the AI launcher above the footer
  action so it does not cover the quiz button.

Why:
- Learners need to see the full lesson/question context while using AI help,
  especially hanzi, pinyin, translation, and prompt text in one study flow.

Files touched:
- `desktop/ui/css/workspace.css`
- `desktop/ui/js/app.js`
- `desktop/ui/js/lesson.js`
- `desktop/ui/index.html`

Risk:
- UI/state-only change. Lesson order, course data, quiz grading, homework,
  payment/subscription/access logic, and backend result flow are unchanged.

Follow-up:
- Smoke-test inside the real Tauri desktop shell with a real lesson session
  after the next build, especially `Esc`, `Cmd/Ctrl+K`, and AI Pack installed/not
  installed states.

### 2026-08-11 — Desktop Practice static v3 fallback

Changed:
- Desktop/shared Practice service now falls back to checked-in
  `app/static/course_v3_data/<level>/lesson_*.json` cards when DB-backed
  `CourseLesson` quiz data is empty, so placement/mock/training drills can open
  even if course seeding is missing or delayed.
- Desktop bridge now preserves `practice_*`, `invalid_practice_session`, and
  `unknown_training_skill` error codes instead of collapsing them into a generic
  failure.

Why:
- Desktop Course reads static v3 JSON, but Practice previously depended only on
  DB lessons. That made Practice cards fail while the Course screen still worked.

Files touched:
- `app/services/course_miniapp_practice_service.py`
- `desktop/ui/js/bridge.js`
- `tests/test_course_miniapp_practice.py`
- `desktop/ui/test-contract.mjs`

Risk:
- No payment/subscription/access rule changed. Practice still uses the shared
  daily-use gate, server grading, mistake recording, and gamification; only the
  question source fallback changed when DB quiz data is unavailable.

Follow-up:
- After deploy, smoke-test Desktop Practice against production auth/session once
  with a real free user and a paid user.

### 2026-08-11 — Desktop referral invite modal restored

Changed:
- Desktop Profile referral card now opens a real invite modal with Telegram,
  WhatsApp, system share/Mac share, QR code, and copy-link actions. If the
  referral overview endpoint fails, the desktop UI falls back to the referral
  code already present in the course map user payload instead of leaving the
  card as a dead error state.

Why:
- Inviting friends is part of the referral growth and premium bonus flow; a
  failed extras request should not remove the user's invite action when the
  local user payload still has enough data to build the deep link.

Files touched:
- `desktop/ui/js/app.js`
- `desktop/ui/css/workspace.css`
- `desktop/ui/js/i18n.js`
- `desktop/ui/test-contract.mjs`

Risk:
- UI-only desktop change. Referral attribution format, backend referral service,
  subscription/payment logic, lesson order, quiz flow, and course data are
  unchanged.

Follow-up:
- Before desktop release, smoke-test the modal inside the packaged macOS and
  Windows shells because external URL handling is OS/WebView dependent.

### 2026-08-11 — Desktop course map Duolingo-style vertical path

Changed:
- Desktop Course screen lesson trail was changed from a horizontal row/grid into a
  vertical zig-zag path with large lesson nodes, current-location bubble,
  completed/current/locked states, and HSK lesson text below each node.

Why:
- The course screen should make the next lesson feel obvious and motivating while
  keeping Chinese characters, pinyin, and translation visible.

Files touched:
- `desktop/ui/js/app.js`
- `desktop/ui/css/workspace.css`

Risk:
- UI-only change. Lesson order, access checks, subscription/payment logic,
  backend completion flow, and course data are unchanged.

Follow-up:
- Before desktop release, visually smoke-test the course map on desktop and
  mobile-width preview with real user progress.

### 2026-08-09 — Desktop 1.3: real local AI + stable automatic release/update

Changed:
- Desktop AI drawer now uses an optional verified Qwen3-4B Q4 model and a
  version-pinned llama.cpp runtime. Model/runtime integrity is checked before
  execution; inference binds to a random authenticated loopback port and prompt
  text is not sent to the backend. After the pack is installed, this chat can
  work without internet. Course/auth/subscription bootstrap is still online-first.
- Desktop updater checks at startup and installs automatically only when the
  workspace is idle. It defers during a lesson, model install, AI generation or
  subscription action, emits real progress, then restarts the application.
- `DESKTOP_RELEASE_MANIFEST_URL` is the single Railway pointer to R2
  `desktop/latest.json`. The backend strictly validates HTTPS/media type/schema/
  size, keeps a last-known-good manifest and rejects downgrade or same-version
  artifact mutation. Legacy per-platform env values are fallback only.
- `.github/workflows/desktop-release.yml` builds universal macOS DMG/updater and
  Windows x64 NSIS EXE/updater in parallel from `desktop-v*`, verifies pinned AI
  runtime hashes and V4 updater signatures, uploads immutable versioned objects,
  updates stable installer aliases, and publishes `latest.json` last.
- The public download page preserves the browser's real DMG/EXE action, then
  opens accessible UZ/RU/TJ install instructions. Anti-framing CSP is delivered
  as an HTTP header, and mobile share/copy never includes the tracked token.
- Native link-start admission is atomic across PostgreSQL workers via a
  transaction advisory lock. Download POST JSON is capped at 2 KiB, tracked
  download tokens expire after 24 hours by default, and an isolated hourly job
  removes expired link/session rows after the retention window. Devices remain
  intact. Railway/Cloudflare still need outer request-size and per-IP/WAF limits.

Important boundaries:
- App binaries, updater archives, signatures and GGUF models stay outside Git
  in R2. Repository and Railway flags remain fail-closed until public artifacts
  pass clean macOS/Windows install and real `1.3.0 → 1.3.1` updater tests.
- Apple notarization and Windows Authenticode are intentionally absent in the
  $0 signing plan, so Gatekeeper/SmartScreen guidance is part of the download UX.
- Updater private key/password are external secrets; never write them here,
  commit them or print them in CI logs.

### 2026-08-09 — Android auth-session va deep-link/audio lifecycle himoyasi

Changed:
- Link, course va lesson ViewModel'lari endi bitta auth branchga tegishli alohida
  `ViewModelStore` ichida yashaydi; logout/relinkda store tozalanadi. Eski hisobning
  link kodi, kurs xaritasi yoki dars holati boshqa sessionga o'tmaydi.
- Har deep-link delivery noyob request ID oladi. Muvaffaqiyatsiz fresh-map
  tekshiruvi bir request uchun loop qilmaydi, lekin aynan shu URI qayta ochilsa
  yangi server authorization urinishini boshlaydi va pending intent yo'qolmaydi.
- Darsdan chiqish pending TTS jobni bekor qiladi, urinishni invalid qiladi va
  kech qaytgan audio eski dars/akkauntda o'ynamaydi.

Files touched:
- `android/.../MainActivity.kt`, `core/navigation/NavigationSession.kt`,
  `feature/lesson/LessonViewModel.kt` va unit testlar.

Risk / follow-up:
- Backend, kurs access/XP, obuna va to'lov logikasi o'zgarmadi. JVM unit test,
  Android lint va debug APK build o'tdi; real qurilmada logout → boshqa accountga
  relink va sekin TTS paytida darsdan chiqish smoke-test qilinsin.

### 2026-08-08 — Android native klient: auth adapteri + loyiha poydevori (Phase A-C)

Changed:
- **Android auth = mavjud yadro, dublikat YO'Q.** `DesktopAuthService` o'zgarmadi;
  faqat `NATIVE_PLATFORMS = DESKTOP_PLATFORMS | {"android"}` qo'shildi va
  `start_link` shunga qaraydi. `DESKTOP_PLATFORMS` eski ma'nosida qoldi
  (downloads / release manifest / admin desktop statistikasi Android'ni sanab
  yubormasligi uchun). **MIGRATSIYA YO'Q** — `platform` allaqachon `String(16)`.
- Yangi yupqa transport: `app/api/android_auth.py` →
  `/api/v3/android-auth/{link/start,link/status,refresh,revoke}` +
  `/api/v3/android/bootstrap`. Validatsiya/bearer/xato konvertlari
  `desktop_auth.py` dan qayta ishlatiladi (3 ta public alias qo'shildi).
  Android `initData` ishlatmaydi, faqat `Authorization: Bearer`.
- **Bot bagi tuzatildi**: `handlers/desktop_auth.py` da `"Mac" if macos else
  "Windows"` yorlig'i Android telefonni "Windows" deb ko'rsatardi. Endi
  `_PLATFORM_LABELS` map + `_copy_key()`; `_COPY` kalitlari `confirm_desktop`/
  `confirm_mobile`/`ok_desktop`/`ok_mobile` ga bo'lindi, 3 tilda parallel.
  `enter_code`/`invalid`/`attempts_exhausted` matnlari neytral qilindi (platform
  hali noma'lum bo'lgan bosqich). `approve_link()` javobiga `platform` qo'shildi.
- **Xavfsizlik xossalari saqlandi**: kod deep-link'ga QO'SHILMAYDI
  (`?start=desktop_link`), qo'lda yuboriladi; single-use, expiry, polling secret,
  row lock, constant-time compare, installation binding, refresh rotatsiya +
  reuse detection — hammasi o'sha yadroda.
- **Analitika ajratildi**: `analytics_prefix(platform)` — Android
  `android_session_linked`/`android_first_open`/`android_app_opened`/
  `android_update_installed` yozadi, dedupe key'lari ham `android-*`.
  Desktop nomlari BAYT-BA-BAYT o'zgarmadi. Allowlist'ga 20 ta `android_*` nomi
  qo'shildi (keyingi fazalar uchun ham).
- **`android/` moduli** (yangi): Kotlin + Jetpack Compose, `compileSdk`/
  `targetSdk` 36, `minSdk` 26, `com.pomp.hskai`. WebView YO'Q. Course v3 dizayn
  tokenlari, UZ default + `values-ru` + `values-tg`, Keystore AES-GCM credential
  store (refresh token hech qachon ochiq saqlanmaydi), single-flight refresh,
  OkHttp origin guard (HTTPS + bitta host + redirect off), deep-link allowlist.
- `.github/workflows/android-ci.yml` (yangi) — desktop-release.yml tegilmadi.

Why:
- Rasmiy Google Play ilovasi kerak, lekin u alohida mahsulot/akkaunt/kurs
  bo'lmasligi shart: bitta Telegram hisobi, bitta obuna, bitta progress.

Files touched:
- `app/services/desktop_auth_service.py`, `app/api/android_auth.py` (yangi),
  `app/api/desktop_auth.py`, `app/bot/handlers/desktop_auth.py`, `app/main.py`,
  `app/db/models/course_miniapp_event.py`, `tests/test_android_auth_api.py` (yangi),
  `android/**` (yangi), `.github/workflows/android-ci.yml` (yangi),
  `ANDROID_IMPLEMENTATION_PLAN.md` (yangi)

Phase D — Bugun + Kurs (qo'shildi):
- `AndroidCourseService(DesktopCourseService)` — 600 qatorlik access policy / XP /
  streak / mistakes / idempotency QAYTA YOZILMADI, meros olindi. Yagona farq:
  `CLIENT_NAMESPACE`. Desktop uchun `desktop-course-complete:` va
  `desktop_course` BAYT-BA-BAYT o'zgarmadi; Android `android-course-complete:` +
  `android_course` ishlatadi, shuning uchun bir xil `event_id` ikkala klientdan
  kelsa ham XP ikki marta berilmaydi.
- Yangi route'lar: `/api/v3/android/course/{map,lesson/{n},complete}` +
  `/api/v3/android/preferences/language`. Request modellari desktop'dan.
  `tz` aniq `None` tekshiruvi bilan — UTC+0 yutilmaydi.
- **MUHIM UI QOIDASI**: `preview_half` darajaning emas, O'QUVCHI JOYLASHUVINING
  xususiyati — faqat `completed == FREE_COURSE_LESSONS_PER_LEVEL` bo'lganda
  paydo bo'ladi. Bepul ruxsat ichidagi, lekin yetib borilmagan dars
  `course_lesson_not_unlocked` beradi va unga **paywall ko'rsatilmaydi**.
  Android'da bu `LessonAccess` tipida muhrlangan (`showsPaywall`).
- Android: Room cache (xom payload snapshot, hech qachon ruxsatni kengaytirmaydi,
  doim `isStale` bilan), Bugun ekrani (bitta ustun harakat), Kurs yo'lakchasi
  (holat rang bilan emas, glif+matn bilan ham), 3 ta tab (Mashq/AI Phase F/G
  gacha UMUMAN yo'q, Obuna hech qachon tab emas).

Deep-link kontrakti (qaror):
- `pomp-hsk-ai://lesson/{n}` QO'LLAB-QUVVATLANADI. Sabab: `motivation_reminder_service`
  allaqachon `target_level` + `target_lesson` + `autostart` bilan aniq darsga
  olib boradigan eslatma yuboradi (D1 recovery, tugallanmagan dars) — Phase H'da
  bular Android bildirishnomasiga aylanadi. Chegara backend'dan: `1..500`
  (`app/api/desktop_course.py`).
- Lekin **resolve ≠ authorize**: `AppDestination.Lesson` faqat raqam olib yuradi;
  navigatsiya server progress/entitlement'ini tekshirmasdan darsni ochmaydi.
- Allowlist ANIQ-ARITY (desktop klientdagi `match path` kabi): ortiqcha segment
  butun URI'ni bekor qiladi (`lesson/current/extra` → null).

Verification (2026-08-08, lokal Mac):
- `pytest tests/test_android_auth_api.py tests/test_desktop_auth_service.py
  tests/test_desktop_course_api.py tests/test_desktop_subscription_api.py`
  → **56 passed, 19 subtests passed**.
- `./gradlew testDebugUnitTest --rerun-tasks` → **BUILD SUCCESSFUL** (26 executed).
- `./gradlew lintDebug` → **BUILD SUCCESSFUL**.
- `./gradlew assembleDebug` → **BUILD SUCCESSFUL**.
- Gradle 8.14.5 + AGP 8.9.1 + JDK 17; wrapper (jar bilan) repoda commit qilingan.

Risk:
- To'lov/obuna/XP/progress/kurs kontenti/Mini App/macOS/Windows tegilmadi.
  Migratsiya yo'q, Alembic head hamon `0066_desktop_foundation`.
- To'liq Playwright e2e to'plami bu ish doirasida yugurtilmadi (unda avvaldan
  4 ta baseline failure bor).
- Qurilmada real Telegram ulash oqimi hali sinalmagan (faqat unit/API darajasi).

Qolgan warninglar (blocker emas, keyin tozalanadi):
- `resourceConfigurations` AGP'da deprecated (`androidResources.localeFilters`).
- `Locale(String, String)` konstruktori testda deprecated.
- Gradle 9.0 deprecation ogohlantirishlari.

Follow-up:
- `DESKTOP_AUTH_CONTRACT.md` ning "Device-link flow" 4-bandi hamon eski
  `?start=desktop_<code>` oqimini yozadi — yangilash kerak.
- Phase D-L qoldi: Bugun/Kurs, native dars renderer (14 karta turi), mashqlar,
  AI Voice, Glance widget + bildirishnomalar, profil, Google Play Billing
  (kodda umuman yo'q), offline, admin statistikasida Android ajratish.
- Play Console product ID, service-account, signing keystore — tashqi bloker,
  kod yo'li fail-closed holatda tayyor.

### 2026-07-26 — Dars yakuni reklamasiga ixtiyoriy tashqi CTA

Changed:
- `dars_yakuni` reklamasi bot obuna yo'lini asosiy CTA sifatida saqlaydi; admin
  `link_url` kiritsa, uning ostida alohida tashqi-link knopkasi ham chiqadi.
- Admin bu tur uchun mavjud `button_text` maydonida tashqi CTA nomini bera oladi;
  nom bo'sh bo'lsa UZ/RU/TJ lokal default ishlaydi. Link bo'lmasa knopka yashiriladi.
- Yangi DB ustuni/migratsiya yo'q: mavjud `link_url` + `button_text` ishlatildi.
  `ads.js` cache versiyasi barcha uni yuklaydigan Course v3 sahifalarda yangilandi.

Files touched:
- `app/static/admin.html`, `app/static/course_v3_data/ads.js`,
  `app/static/course-v3.html`, `app/static/course_v3_{recognition,pronunciation,memorize,test,mistakes}.html`,
  `app/db/models/course_ad.py`, `app/services/course_ad_service.py`, tests.

Risk / follow-up:
- To'lov/obuna huquqi, dars progressi va reklama slot filtri o'zgarmadi.
- Tekshiruv: 260 non-E2E test + 2 maxsus mobil Chromium flow o'tdi; umumiy E2E'dagi
  4 eski baseline failure saqlandi (lesson sheet, D1 resume, HSK test copy, checkout copy).

### 2026-07-25 — Dars yakuni reklamasi (alohida tur) + ostida obuna knopkasi

Changed (foydalanuvchi: "bepul userlarga dars tugagach ham bitta reklama blok chiqsin, uni
boshqalariga aralashtirmaslik kerak — odiy/hamkorlik/bot turlari yonida 'dars yakuni reklamasi'
bo'lsin va u erga botdagi obuna yo'li knopkasi ulansin"):
- **Yangi `ad_type` = `dars_yakuni`** (`COURSE_AD_TYPES`ga qo'shildi; MIGRATSIYA KERAK EMAS —
  mavjud `String(16)` ustunidagi yangi qiymat). Ustun izohi `app/db/models/course_ad.py`da
  yangilandi.
- **ARALASHMASLIK server tomonda**: `CourseAdService._slot_filter(slot)` +
  `normalize_slot` (`practice` | `lesson_end`). `list_active` / `list_active_payloads` /
  `get_active_ad` / `get_active_payload` endi `slot` qabul qiladi:
  `lesson_end` → FAQAT `ad_type == "dars_yakuni"`; `practice` (default) → `dars_yakuni`dan
  tashqari hammasi (`ad_type IS NULL` legacy yozuvlar ham mashq slotida qoladi).
  Ya'ni mashq bo'limlarida dars yakuni roliki chiqmaydi va aksincha.
- **`GET /api/v3/ad`**: yangi `slot` query param. `slot=lesson_end` bo'lsa dars/feature
  validatsiyasi shart emas (dars raqami bilan keladi), javobda `slot` qaytadi va bir nechta
  aktiv reklama bo'lsa BITTASI tanlanadi — `ads[lesson_order % len(ads)]` (har dars navbat bilan
  boshqasi). Obunachiga (`CourseMiniAppAccessService.is_paid_user`) `slot=lesson_end` uchun 404 —
  klient xato hisoblasa ham obunachi reklama ko'rmaydi.
- **`ads.js` (`window.CourseAds`)**: `CFG.slot` + `CFG.lessonOrder` + `CFG.onOffer`.
  `fetchAds` `&slot=&lesson=` uzatadi; `recordView` `lesson_order`ni CFG'dan oladi
  (`startAttempt` ataylab 0 — attempt faqat mashq gate'i uchun). Dars yakuni rejimida matnlar
  boshqacha (3 tilda yangi kalitlar `leLabel`/`leNote`/`leSubTitle`) va ikkilamchi tugma
  "Reklama bilan davom etish" emas, oddiy "Davom etish" (`adReady`).
- **`course-v3.html`**: endi `ads.js`ni ham yuklaydi (`?v=20260725`). `applyLessonDone` bepul +
  Telegram ichidagi userga `window._pendingLessonEndAd = cur.n` qo'yadi; `App.closeLevelUp(dest)`
  esa navigatsiyadan OLDIN `playLessonEndAd(go)` chaqiradi — ya'ni reklama bayram → streak →
  reyting ekranlaridan KEYIN, kurs xaritasiga qaytishdan oldin chiqadi (foydalanuvchi tanlovi).
  Reklama yo'q / yuklanmasa jim o'tib xaritaga qaytadi. Obuna tugmasi → `App.goPay("v3_lesson_end_ad")`
  (bot obuna yo'li = subscription.html). `onOffer` → `paywall_seen` (source `v3_lesson_end_ad`).
- Admin (`admin.html`): "Reklama turi"ga 🎓 Dars yakuni reklamasi qo'shildi (knopka nomi
  o'chirilgan — obuna knopkasi avtomatik), kartada slot qatori ko'rsatiladi.
  `subscription_entry_analytics_service` SOURCE_LABELS'ga `v3_lesson_end_ad` yorlig'i.

Files touched:
- `app/services/course_ad_service.py`, `app/db/models/course_ad.py`, `app/main.py`,
  `app/services/subscription_entry_analytics_service.py`, `app/static/course_v3_data/ads.js`,
  `app/static/course-v3.html`, `app/static/admin.html`,
  `tests/test_course_miniapp_foundation.py`, `tests/test_course_v3_static_data.py`

Risk / follow-up:
- Migratsiya YO'Q. To'lov/obuna huquqi, XP, progress, dars kontenti tegilmadi — reklama
  gating ham qo'shilmadi (bu blok hech narsani qulflamaydi, faqat ko'rsatiladi).
- Chastota: HAR mini-dars oxirida 1 blok (foydalanuvchi shunday tanladi). Agar bepul userlar
  charchasa, birinchi sozlanadigan joy — `applyLessonDone`dagi `_pendingLessonEndAd`.
- Admin dars yakuni reklamasini yuklamasa hech narsa o'zgarmaydi (404 → jim o'tadi).
- Testlar: 253 passed (non-e2e) + yangi 3 test; 4 e2e smoke (course-v3 sheet/d1/support/checkout)
  AVVALDAN yiqiq — `db07fd2e` worktree'da ham aynan shu 4 tasi yiqilishi tasdiqlandi.
- Lokal preview'da 3 tilda tekshirildi: blok bayramdan keyin chiqadi, taymer → "Obuna olish"
  (source `v3_lesson_end_ad`) + "Davom etish" (→ `/api/v3/ad/view` yozadi, xaritaga qaytadi),
  obunachida umuman boshlanmaydi, reklama yo'q bo'lsa jim o'tadi.

### 2026-07-25 — Kinematik kirish: yaqin kadr panda + real parvoz sahnasi (osmon/yer/bulut/shamol)

Changed (foydalanuvchi: "effekt vaqtida yaqin kadrdan pandani olish kerak, hali hech bir ekran
ko'rinmasin; effekt tugab chang o'tirgach qolganlari ochilsin. Uchayotgan mahal shamol, bulut,
osmon, yer, daraxt ko'rinsin — realroq bo'lsin"):
- **`cinePanda(kind,mood,build)`** — bayram oynasi endi kinematik kirish bilan boshlanadi:
  overlay ochiladi, lekin `#lu-stage` BO'SH va `.cine` klassi sahna/CTA/nurlarni yashiradi;
  ko'rinadigan yagona narsa — markazdagi 300px yaqin kadr panda (`#lu-cine > .cine-pd`).
  Effekt tugab chang o'tirgach `build()` sahnani quradi va `.rev` bilan qismlar navbat
  bilan ochiladi. Ekranga tegish effektni o'tkazib yuboradi (skip); `prefers-reduced-motion`
  yoki WAAPI yo'q bo'lsa — effektsiz darhol quriladi.
  Ulangan ekranlar: streak (fly), dars/checkpoint/level bayrami (land), rank-up (zoom), sandiq (roll).
- **Parvoz sahnasi** (`skyScene()` + `#lu-sky`): balandligi 300% bo'lgan "dunyo" — pastida yer
  (yashil tepalik + daraxt/bambuk/buta/pagoda/o't, `scenerySvg` bilan kurs xaritasi uslubida),
  yuqorisiga qarab osmon gradienti (och zangori → to'q ko'k), orasida 7 bulut. Panda deyarli
  o'rnida qoladi, DUNYO pastga siljiydi (`translateY -66.7% → -15.5% → -66.7%`, foizlar
  elementning o'z balandligiga nisbatan) — kamera ko'tarilgandek. Ustiga shamol chiziqlari
  (`.sky-wind i`, ko'tarilish/tushishda kuchayadi, tepada tinchiydi) va yerdagi soya
  (uzoqlashgani sari kichrayadi). Qo'nishda 14 chang zarrasi + kadr silkinishi + past chastotali tovush.
  `fly` davomiyligi 1950 → 2600ms; parvoz vaqtida overlay'ga `.flying` (panda ufq chizig'ida turadi).
- Osmon sahnasi faqat `fly`da ko'rinadi (boshqa effektlarda `#lu-sky` opacity 0 ga qaytariladi);
  `closeLevelUp`/`closeChest` `.cine` holatini tozalaydi.
- **Panda pozalari effektga moslashdi** (`pandaChar` yangi moodlari): `fly` — ikkala qo'l tepaga
  cho'zilgan (mushtlar bilan), orqada hilpiragan qizil plash, oyoqlar cho'zilgan; kadr shu poza
  uchun kengaytiriladi (`viewBox "-22 -16 144 138"`), aks holda katta bosh qo'llarni yopib qoladi.
  `land` — ko'z chirt yumilgan, qo'llar muvozanat uchun yon tomonda, oyoqlar keng. `roll` — qo'llar
  qorinni quchoqlagan ixcham siluet. Animatsiyalar: `.pd-fly`, `.pd-cape`, `.pd-arms`.

Files touched:
- `app/static/course-v3.html`

Risk / follow-up:
- Faqat frontend animatsiya qatlami; dars/XP/to'lov/obuna mantig'i tegilmadi.
- Bayram ketma-ketligi endi ~1.3s (dars) + ~2.9s (streak) — ikkalasi ham tegish bilan o'tkaziladi.
- Testlar: 256 passed (o'sha 4 e2e smoke AVVALDAN yiqiq). Lokal preview'da yer sahnasi, ko'tarilish,
  bulutlar orasidagi apeks, chang bilan qo'nish va skip vizual tekshirildi.
- Real Telegram WebView'da (ayniqsa eski Android) parvoz kadr tezligi tekshirilsin — sekinlashsa
  `PANDA_FX_DUR.fly` qisqartiriladi yoki bulutlar soni kamaytiriladi.

### 2026-07-24 — Motivatsion matnlar, panda effektlari kutubxonasi, alangali hafta kalendari

Changed (foydalanuvchi: "motivatsion gaplar kuchsiz, effektlar kam, 'streak' so'zi tarjima
qilinsin, hech kimdan o'tmasa reyting oynasi ochilmasin"):
- **Motivatsion matnlar qayta yozildi** (uz/ru/tj, umumiy maqtov emas — aniq natijaga bog'liq):
  `streakCopy(n,reset)` — 1/2/3/7/14/30/100 kun bosqichlari + uzilishdan keyingi qaytish matni;
  `lessonMotivation(acc,completed)` — avval marra (1/5/10/25/50/100-dars), bo'lmasa shu darsdagi
  haqiqiy aniqlik (100% / ≥85 / ≥60 / past); `renderCheer` dalda matnlari va checkpoint/rank-up
  matnlari ham kuchaytirildi. Rank-up sub matni endi kimdan o'tganini aytadi (nom `esc()` bilan).
- **"Streak" so'zi ko'rinadigan joylarda tarjima qilindi**: uz "ketma-ket kunlar / seriya",
  tj "рӯзҳои пайдарпай / силсила", ru "серия дней" (`course-v3.html` profil, bildirishnoma
  tavsifi, yutuqlar + `notification_template_service` KEY_STREAK uz matni).
- **Hafta kalendari alangalarga o'tdi** (`miniFlameSvg`): faol kun — yonayotgan alanga
  (miltillash animatsiyasi), o'tkazib yuborilgan o'tgan kun — muzlagan ko'k alanga,
  kelajak kun — so'nik. Avval oddiy ✓ doiralar edi.
- **Panda effektlari kutubxonasi** (`PANDA_FX` + `pandaFx(el,kind)`, WAAPI, `prefers-reduced-motion`
  hurmat qilinadi): `fly` (supermen parvozi — osmonga otiladi, tepada muallaq turadi, changli
  qo'nadi + sahna silkinishi), `land` (osmondan changli qo'nish), `zoom` (uzoqdan otilib chiqish),
  `roll` (dumalab kirish), `pop` (sakrash). Ulangan joylar: streak ekrani (fly), dars/checkpoint/
  level bayrami (land), rank-up taxtasi (zoom), sandiq (roll), dalda ekrani + AI Voice bo'limi (pop).
  Chang zarralari `pandaDust`, silkinish `stageQuake`.
- **Reyting oynasi qat'iylashtirildi**: `renderRankUpBoard` endi o'zi hech kimdan o'tmagan bo'lsa
  (pastda o'yinchi yo'q yoki men ro'yxatda yo'q) umuman ochilmaydi; Telegram tashqarisida
  (initData yo'q) ham ochilmaydi. `closeLevelUp(dest)` — faqat haqiqiy ko'tarilishda reyting
  ekraniga o'tadi, aks holda o'quvchi kurs xaritasiga qaytadi (avval har dars oxirida
  reyting ekrani ochilardi).

Files touched:
- `app/static/course-v3.html`, `app/services/notification_template_service.py`

Risk / follow-up:
- Faqat frontend matn/effekt + 1 bot matni; to'lov/obuna/XP/progress backend tegilmadi.
- Dars tugagach navigatsiya o'zgardi (reyting o'rniga kurs xaritasi) — bu ataylab.
- Testlar: 256 passed (o'sha 4 e2e smoke AVVALDAN yiqiq). Lokal preview'da 3 tilda matnlar,
  alangali kalendar, panda parvozi (11 chang zarrasi) va reyting qat'iyligi tekshirildi.

### 2026-07-24 — Dars oxirida "Aralash takror" + real haftalik streak kalendari

Changed (Codex boshlagan ishning yakuni — dars formati + streak effektlari):
- Har oddiy mini-dars (355 ta) endi yakuniy `retention_review` bo'limi bilan tugaydi:
  2 karta — bittasi OLDINGI qism/dars so'zidan (mc_meaning), bittasi JORIY qism so'zidan
  (mc_translation). Kartalarda `review_mix`/`review_origin` flaglari. Eski oqim-ichidagi
  spaced-review kartasi mashqdan olib tashlandi (RNG legacy chaqiruv saqlangan, lekin fill
  mantiqidagi hisob farqi tufayli mashq kartalari tarkibi baribir qisman o'zgardi — 425 JSON
  atomik qayta generatsiya qilindi, testlar qamrov/gatingni tasdiqladi). 70 checkpoint
  o'zi to'liq takror — ularga qo'shilmadi.
- Frontend: `cardChoice` review kartalarni "kartalar dastasi" ko'rinishida chizadi
  (`.mix-review` + `.mix-badge`, oldingi=oltin/"Oldingi darsdan", joriy=qizil/"Shu darsdan",
  3 tilda). Dars varag'i bosqichlari endi 4 ta: so'zlar/mashq/talaffuz/aralash takror (`partSecs`).
- Streak endi REAL haftalik faollikdan: `CourseGamificationService.snapshot()` `local_date`,
  `week_start`, `week_activity_dates` (CourseXpEvent distinct activity_date), `longest_streak`,
  `last_activity_date`, `streak_updated`, `streak_reset`, ko'rsatiladigan streak esa uzilgan
  bo'lsa 0 qaytaradi; `/api/v3/map` progress payloadiga shu maydonlar qo'shildi.
- Streak ekrani: bugungi kun "shtamp" animatsiyasi (`sk-day.just`), haftalik maqsad paneli
  (`skWeekGoalHtml`, X/7 + progress bar), streak uzilib qayta boshlanganda alohida matn
  (`streak_reset`); profil kalendari (`streakCalHtml`) ham real `week_activity_dates` dan
  (eski javob uchun streak-oynali taxmin fallback qoladi). tj "keep" matni bagi tuzatildi.

Files touched:
- `scripts/gen_course_v3_from_seed.py` (`build_retention_review`, mc_* rng parametri),
  `app/services/course_gamification_service.py`, `app/main.py`,
  `app/static/course-v3.html`, `app/static/course_v3_data/**` (425 JSON regeneratsiya)

Risk / follow-up:
- To'lov/obuna/ruxsat logikasi tegilmadi; migratsiya yo'q (faqat qo'shimcha snapshot maydonlar).
- Data + frontend bitta relizda chiqsin (JSON'lar atomik almashadi). Qurilma-lokal dars resume
  indekslari kontent siljigani uchun eski saqlangan joyga mos kelmasligi mumkin — 7 kunda o'zi tozalanadi.
- Testlar: 256 passed; 4 e2e smoke (course-v3 sheet/d1/support/checkout) AVVALDAN yiqiq (HEAD'da ham),
  bu ishga aloqasiz. Real Telegram'da bitta dars + streak ekrani smoke-test tavsiya.

### 2026-07-22 — Chegirma obunachiga bormaydi + otziv oqimi 2 qadamli, obunachiga alohida

Muammo:
- Faol pullik obunachi chegirma e'lonini olardi (`status="active"` filtri ularni ham qamrardi),
  bu "obunam tugadimi?" degan noto'g'ri signal berardi.
- Admin statistikasi 30 daqiqalik feedback bonusini "Obuna boshlangan/tugaydi" deb ko'rsatardi
  va access turini "✅ Faol (boshqa trial)" deb noaniq yozardi.

Changed (access/obuna klassifikatsiyasi O'ZGARMADI, faqat kimga nima yuborilishi):
- `UserAccessStateService.is_paid()` endi yagona filtr sifatida ishlatiladi:
  `DiscountNotificationService._target_users` (broadcast'dan faol obunachi chiqarib tashlanadi;
  admin `target_telegram_id` bilan bitta userga qo'lda yuborishi saqlanib qoldi),
  `BotFeedbackService.finish_feedback` (obunachiga price offer rejalashtirilmaydi),
  `send_due_price_discount_offers` (yuborishdan oldin qayta tekshiriladi),
  `grant_feedback_reward` (obunachiga 30 daqiqalik bonus berilmaydi — avval u `end_date`ni
  30 daqiqaga uzaytirib, `selected_plan_type`ni `None` qilib yuborardi).
- Otziv oqimi 2 qadamli bo'ldi: "kurs yoqdi" → "aynan qaysi qismi? darslar/mashqlar/AI Voice/boshqa"
  (`LIKE_SUB_OPTIONS`, callback `fb:<id>:lsub:<parent>:<sub>`). Sub-javob `liked_text`ga
  "parent → sub" ko'rinishida qo'shiladi — migratsiya kerak emas.
- Obunachiga butunlay boshqa savol: "Obunani olganingizga hozir qanday qaraysiz?"
  (arzidi / foydasi bor / hali baholay olmadim / kutganimdek chiqmadi) → sababi bo'yicha
  aniqlashtiruvchi savol → rahmat. Kodlar `liked_code="paid_<javob>"`,
  `disliked_code="paid_<sabab>"` — `FEEDBACK_DISCOUNT_OFFER_CODES` ("price"/"limits") bilan
  kesishmaydi, shuning uchun chegirma oqimi ishga tushmaydi. Admin otziv statistikasiga
  "Obunachilar: obuna arzidimi" bloki qo'shildi.
- Otziv so'rovi endi HAMMAGA boradi (`daily_limit_offer_sent_at` filtri olib tashlandi),
  bir tsiklda 60 tadan (`FEEDBACK_SEND_BATCH_LIMIT`) — takror so'rash oralig'i
  `FEEDBACK_PERIOD_DAYS = 30` kunligicha qoldi.
- Admin kartasi (`_admin_user_info_text`): access turi `UserAccessStateService.classify` dan
  olinadi; vaqtinchalik kirish "⏳ Vaqtinchalik kirish (30 daqiqa)" deb yoziladi, sana satrlari
  pullik bo'lmasa "Kirish muddati", chegirma bloki faol obunachida umuman ko'rsatilmaydi.

Files touched:
- `app/services/bot_feedback_service.py`, `app/services/discount_notification_service.py`,
  `app/services/admin_notify_service.py`, `app/bot/handlers/feedback.py`,
  `app/bot/handlers/admin.py`, `app/bot/keyboards/feedback.py`, `app/bot/utils/i18n.py`
  (3 tilda ~40 yangi kalit), `tests/test_bot_feedback_service.py` (yangi)

Risk / follow-up:
- Migratsiya yo'q. To'lov/obuna huquqi (entitlement) tegilmadi — faqat kimga qaysi xabar
  boradi va admin kartasi matni o'zgardi. Deploydan keyin birinchi kunlarda otziv so'rovi
  eski userlarga ommaviy ketadi (60/daqiqa) — Telegram rate limit va otziv oqimini kuzatish kerak.

### 2026-07-22 — HSK tests, challenges, and mistake material V2

Changed:
- HSK 1–4 exams now load strict canonical V2 material for Uzbek/Russian/Tajik, hide answer keys from the browser, grade on the server, preserve immutable attempts, report section scores, record rich mistakes, and cap XP to one award per user/level/UTC day.
- Lesson, HSK, practice, and challenge mistakes persist a versioned `material_json` snapshot (`format`, Chinese sentence/audio, pinyin, language, options, and source). Lesson mistakes are rebuilt from a stable `material_ref`; client-supplied prompts/answers are not trusted.
- Mistake review now uses format/category/language-matched distractors, real server filters/pagination, compact retry-safe snapshots, and XP only for trusted server-graded sources. Each choice is committed server-side before the answer/explanation is revealed, so browser payload inspection cannot forge resolved mistakes or XP. `course_mistakes.material_json` is nullable and bootstrap-added for legacy DB compatibility.
- Challenges use exactly 10 learned-level questions, keep answers server-only until submission, score ties by equal percentage, and show concise correction material after the round.
- HSK and mistake ad continuations require a recent server-recorded authorization bound to `user + ad + feature + access_ref + placement`. A server-timed attempt must reach the creative duration before authorization; client `watched_seconds` and direct `ad_supported=true` cannot bypass access.

Key files:
- `app/services/course_question_material.py`
- `app/services/course_hsk_exam_service.py`
- `app/services/course_lesson_mistake_material_service.py`
- `app/services/course_mistake_service.py`
- `app/services/course_challenge_service.py`
- `app/static/course_v3_test.html`, `app/static/course_v3_mistakes.html`, `app/static/course-v3.html`

Risk / follow-up:
- Medium: access/session and mistake persistence changed, but payment/subscription entitlement classification did not. Run a real Telegram WebView smoke test after deploy for HSK completion, lesson completion, challenge submission, mistake review, and ad continuation.

### 2026-07-21 — Gemini yoqilganda limit tizimi o'zgaradi + bir martalik e'lon

Changed (access/limit logikasi — ehtiyotkorlik bilan):
- Yangi signal `gemini_active()` (`app/services/ai_provider.py`): Railway env'da `GEMINI_API_KEY`
  bor bo'lsa Gemini asosiy provayder. Shu signal qaysi limit tizimi ishlashini tanlaydi.
- Gemini YOQILGANDA (bepul/obunasiz userlar uchun): chatda MATN cheksiz (kunlik text limit
  o'chadi), FOTO kuniga 5 ta (avval 2), OVOZ kuniga 5 ta (avval bepul userga ovoz umuman yopiq
  edi; pullik/trial ovoz mantig'i o'z joyida). Gemini O'CHIQ (OpenAI) bo'lsa hozirgi limit
  tizimi AYNAN qoladi.
- `AccessService`: `_can_use_daily_text_limit` gemini bo'lsa (True,"") qaytaradi;
  `_can_use_daily_image_limit` limiti `GEMINI_FREE_PHOTO_DAILY=5` / `OPENAI_FREE_PHOTO_DAILY=2`;
  yangi `can_use_free_daily_voice` + `count_voice_messages_today` (content_type "voice" +
  "voice_translator", `GEMINI_FREE_VOICE_DAILY=5`).
- `handle_voice_message` (messages.py): gemini yoqilgan + obunasiz + trial emas bo'lsa
  `can_use_free_daily_voice` orqali 5/kun ruxsat; limit tugasa `access_daily_voice_limit_reached`
  (uz/ru/tj). Ovoz soni saqlangan xabarlardan sanaladi (migratsiyasiz).
- Yangi `GeminiSwitchAnnouncementService` (`announce_if_needed`, scheduler har tsiklda chaqiradi):
  Gemini birinchi marta yoqilganda HAMMA bloklamagan userga o'z tilida (uz/ru/tj) bir martalik
  "matn cheksiz, foto/ovoz 5/kun" xabari. `bot_settings.gemini_switch_announced` flagi bilan
  takrorlanmaydi; yetkazish scheduler tsiklini bloklamaslik uchun alohida background task'da.
- **Limit MATNLARI ham provayderga moslashadi** (raqam o'zgarib, matn eski qolib ketmasligi uchun):
  `t()` (`i18n.py`) endi `gemini_active()` bo'lsa AVVAL `<kalit>_gemini` variantini qidiradi,
  topilmasa oddiy kalitga tushadi — ya'ni chaqiruv joylari umuman o'zgarmaydi va faqat limitga
  aloqador matnlar boshqacha chiqadi. 6 kalitga 3 tildan variant qo'shildi (18 ta):
  `free_mode_info`, `onboarding_special_welcome`, `trial_24h_info`, `referral_trial_access_unlocked`,
  `access_daily_image_limit_reached`, `referral_image_limit_offer` — Gemini variantlarida
  "matn cheksiz, rasm/ovoz kuniga 5 tadan" deyiladi. Matndagi raqamlar `access_service`
  konstantalariga (5/5) mos; OpenAI holatida matnlar AYNAN eskicha qoladi.

Files touched:
- `app/services/ai_provider.py`, `app/services/access_service.py`, `app/bot/handlers/messages.py`,
  `app/bot/utils/i18n.py` (`t()` + `_lookup_text` + `_gemini_texts_active`),
  `app/main.py`, `app/services/gemini_switch_announcement_service.py` (yangi),
  `tests/test_gemini_limits.py` (yangi)

Risk:
- Migratsiyasiz. To'lov/obuna/budjet logikasi tegilmadi (pullik userlar budjet bo'yicha ishlaydi).
  Faqat bepul-tier gating o'zgardi va FAQAT `gemini_active()` bo'lganda. E'lon flagi yuborishdan
  OLDIN o'rnatiladi (dublikatsiz; lekin yuborish o'rtasida crash bo'lsa qolganlar xabarni olmaydi).
  `t()` butun bot bo'ylab ishlatiladi — `_gemini` varianti yo'q kalitlar uchun xatti-harakat
  o'zgarmagan (fallback testlari bor). Testlar: `test_gemini_limits` (15 + 54 subtest) +
  to'liq to'plam 240 test o'tdi.

### 2026-07-21 — AI provayder: Gemini asosiy + OpenAI zaxira, admin model tanlash, AI Voice tezlashtirildi

Changed:
- Yangi provayder qatlami `app/services/ai_provider.py` (`AIProviderChain`): Gemini asosiy, OpenAI
  zaxira. `GEMINI_API_KEY` bo'lsa Gemini ishlaydi; bo'lmasa yoki ish vaqtida xato bersa har chaqiruvda
  avtomatik OpenAI'ga o'tadi (log bilan). Matn/vision/JSON Gemini'ning **OpenAI-mos endpointi**
  (`GEMINI_BASE_URL`, xuddi shu `AsyncOpenAI` mijozi) orqali; STT (ovoz->matn) native `google-genai`
  SDK orqali, OpenAI transkripsiyasi zaxira. OpenAI modellari/parametrlari o'zgarmagan.
- `AIService` endi `self.chain` ishlatadi; yangi `complete_messages_with_usage(...)` umumiy metod.
  4 ta ommaviy metod (reply/vision/translate/transcribe) shu zanjirdan o'tadi — imzolar o'zgarmagan.
  `broadcast_translation_service` va `discount_translation_service` endi o'z `AsyncOpenAI`i o'rniga
  `AIService().complete_messages_with_usage`ni ishlatadi. Barcha AI-mavjudlik guardlari
  `settings.OPENAI_API_KEY` -> `settings.ai_enabled` (Gemini yoki OpenAI kaliti).
- **Admin panelda model tanlash**: `admin.html` "Boshqaruv" bo'limida "AI modeli (Gemini)" kartasi
  (3 model: `gemini-2.5-flash-lite`/`gemini-2.5-flash`/`gemini-2.5-pro`). Tanlov `bot_settings`
  (`active_gemini_model`) ga yoziladi (yangi migratsiya YO'Q), `get_active_gemini_model` ~60s keshli.
  Endpoint `POST /api/admin-miniapp/ai-model/save`; management payloadga `gemini` bloki.
- **AI Voice tezlashtirildi**: roleplay javobi va STT eng tez model `gemini-2.5-flash-lite` bilan
  (admin global tanlovidan qat'i nazar). AI Voice logikasi/UI (correction, done-ekran, "Xatolarim",
  subtitr) va JSON sxema O'ZGARMAGAN — faqat model tezroq. `course_v3_voice.html` tegilmagan.
- Narx hisobi: `ai_usage_budget_service.MODEL_PRICING_USD_PER_1M`ga 3 Gemini modeli (taxminiy narx).
- `requirements.txt`: `google-genai==1.75.0`; `.env.example`/`config.py`: `GEMINI_API_KEY`,
  `GEMINI_MODEL` (default `gemini-2.5-flash`), `GEMINI_BASE_URL`, `AI_PRIMARY_TIMEOUT_SECONDS`.

Why:
- Foydalanuvchi: OpenAI turgan hamma joyda Gemini asosiy bo'lsin, ishlamasa OpenAI zaxira; admin
  qaysi Gemini modeli ishlashini o'zi tanlasin; AI Voice suhbati kechikishsizroq bo'lsin.

Files touched:
- Yangi: `app/services/ai_provider.py`, `tests/test_ai_provider.py`
- Edited: `app/config.py`, `app/services/ai_service.py`, `app/services/broadcast_translation_service.py`,
  `app/services/discount_translation_service.py`, `app/services/voice_practice_service.py`,
  `app/services/ai_usage_budget_service.py`, `app/main.py`, `app/static/admin.html`,
  `requirements.txt`, `.env.example`

Risk / follow-up:
- To'lov/obuna/XP/ruxsat va TTS (edge-tts) tegilmagan. Testlar: 176 passed (2 e2e course-v3 dars-oqim
  testi AVVALDAN yiqiq, bu ishga aloqasiz). Deployda `pip install -r requirements.txt` (google-genai);
  Railway env'ga `GEMINI_API_KEY` qo'yilsin. Gemini narxlari va `google-genai` versiyasi tekshirilsin.
- **STT Gemini orqali** — Gemini qo'llamaydigan audio formatlar (mp4/webm) OpenAI'ga fallback bo'ladi;
  talaffuz baholash aniqligi flash-lite'da o'zgarishi mumkin. Real Telegram mikrofon smoke-test tavsiya.
  Muammo bo'lsa `GEMINI_API_KEY`ni olib qo'yish darhol hammani OpenAI'ga qaytaradi.

### 2026-07-20 — DARSLAR MINI-QISMLARGA BO'LINDI (3-4 so'z + checkpoint, flat raqamlash)

Changed (foydalanuvchi: "bitta darsda 40+ mashq charchatadi; 3-4 yangi so'z + mustahkamlash"):
- Har HSK darsligi darsi bir nechta QISQA mini-darsga bo'lindi: har qismda 2-4 yangi so'z
  (flash → darhol tekshiruv → match → gap-kontekst mashqi; har so'z ≥4 kartada), qism
  11-18 karta (~5-7 daqiqa). Dars oxirida CHECKPOINT qismi: yangi so'z yo'q — dialog +
  butun dars so'zlari aralash takror; tugaganda katta bayram ("胜 {n}-dars to'liq yakunlandi").
- Qismlar darajada TEKIS raqamlanadi: lesson_01..lesson_NN.json (hsk1=63, hsk2=72,
  hsk3=109, hsk4=181; jami 425). `completed_lessons_count` endi QISMLARNI sanaydi.
  HSK dars → qismlar xaritasi: `course_v3_data/parts_manifest.json` (GENERATED, yagona manba);
  server o'quvchisi: `app/services/course_v3_parts.py` (total_parts, source_lesson_for_part).
- Generator (`gen_course_v3_from_seed.py`): chunk_words (3-4 talik), assign_grammar (qoida eng
  erta segmentlanadigan qismga, cap 1-2), build_part_intro/practice, build_checkpoint_sections,
  build_split_plan; INTRO_WORD_CAP olib tashlandi — endi HSK4'da ham HAMMA so'z o'rgatiladi
  (avval 31 so'zdan faqat 10 tasi o'rgatilardi).
- Xarita: bitta unit = bitta HSK darsi ("7-dars · 你好" banner), qism tugunlari so'z-preview
  bilan ("你 · 好 · 您" + "1-qism"), checkpoint tuguni bayroq + "Takrorlash"; milestone
  (boss/chest) har 5-darsda qoladi. sync_maps endi units'ni to'liq qayta quradi.
- Trial: `FREE_COURSE_LESSONS_PER_LEVEL = 2` (2 mini-dars to'liq bepul) + 3-qism preview_half
  (`_apply_course_v3_access_policy` konstantadan oladi; frontend flip next.n===3).
- `/api/v3/lesson/complete|unlock`: legacy `course_lessons` qatori endi SHART EMAS (topilmasa
  ham davom etadi); band tugashi parts_manifest chegarasidan; XP ref `v3-part:{level}:{n}`.
- MIGRATSIYA `0065_course_progress_parts`: eski completed (HSK darslari) → yangi (qismlar,
  1..N darslar qismlari yig'indisi) CASE bilan atomik; downgrade teskari. CHECKPOINTS
  konstantasi migration ichida — kurs qayta bo'linsa migration O'ZGARMAYDI.
- Challenge: `source_lesson_for_part` bilan qism → darslik darsi konvertatsiyasi (savol banki
  eski dars tartibida), widen +4 saqlanadi. lesson_gate.js endi so'z → [daraja, QISM raqami].
- Frontend: resume kaliti `hsk_v3_lesson_resume:v2:` (eski raqamlash qoldiqlari mos kelmasin),
  showLevelUp("checkpoint") varianti, dars varag'ida "X-dars · Y-qism" chip + real 3 bosqich.

Files touched:
- `scripts/gen_course_v3_from_seed.py`, `app/static/course_v3_data/**` (425 JSON + maplar +
  gate + manifest), `app/main.py`, `app/services/course_miniapp_access_service.py`,
  `app/services/course_challenge_service.py`, `app/services/course_v3_parts.py` (yangi),
  `alembic/versions/0065_course_progress_parts.py` (yangi), `app/static/course-v3.html`,
  `tests/test_course_v3_static_data.py`, `tests/test_course_miniapp_foundation.py`

Risk / Deploy:
- ATOMIK deploy shart: data + backend + frontend + 0065 migratsiya bitta relizda (aralash
  holat progressni buzadi). Rollback: git revert + `alembic downgrade`.
- Legacy bot kursi (app/bot/handlers/course.py) `completed_lessons_count`ni darslik darsi
  deb o'qiydi — v3 user uchun endi qism soni (skew). Bot kursi legacy, asosiy yuza Mini App.
- Testlar (164) o'tdi; lokal HTTP preview'da xarita/varaq/dars oqimi/checkpoint bayrami/
  trial flip vizual tekshirildi. Real Telegram'da 1-2-3-qism + paywall smoke-test tavsiya.

### 2026-07-20 — Duolingo O'RGATISH USLUBI darslarda + challenge dars-progress gating

Changed (foydalanuvchi: "struktura emas, o'rgatish stili — Duolingo'dan shablon ol"):
- `cardWord`/`cardWordFlash`: YANGI SO'Z bayram-kartasi — sparkle animatsiya, katta hanzi
  karta (nwPop), "YANGI SO'Z / НОВОЕ СЛОВО / КАЛИМАИ НАВ" label, pinyin/ma'no keyin ochiladi
  (nw-info.on), avto-audio. Kartani almashtirganda `.nw*` CSS klasslari.
- `cardPron`: "Li ustozdan keyin takrorlang" — panda `pandaChar("talk")` nutq pufagi
  (`.teach-bub.say-bub`) ichida gap+pinyin+tarjima+audio; pastda jarimasiz o'tkazish
  tugmasi "HOZIR GAPIRA OLMAYMAN" (`_pronSkip`, graded'ga kirmaydi).
- Yangi karta turi `reverse_builder` (generator `make_reverse_builder_card` + frontend
  `cardReverse`): ustoz xitoy gapni aytadi, o'quvchi TARJIMANI ona tili plitkalaridan
  yig'adi. `tokens`/`answer_tokens` HAR TIL uchun alohida ({uz:[],ru:[],tj:[]}),
  chalg'ituvchilar shu darsning boshqa real tarjimalaridan. 69/70 darsda bor.
- Darsdagi BIRINCHI xatodan keyin panda dalda ekrani (`renderCheer`, Flow._wrongPending/
  _cheered, faqat darsda — test/challenge'da emas), Duolingo boyqush daldasi kabi.
- Pinyin sozlamasi dars oqimida (ftop'dagi gear → `App.pinyinSheet`): hammasi / faqat
  yangi so'zlarda / yashirish; `hsk_v3_pinyin` localStorage; `#flow.pyoff/.pynew` CSS.
- Challenge savollari endi har o'yinchining dars progressidan:
  `CourseMiniAppPracticeService._questions(..., max_lesson=)` + `_level_questions` filtri;
  `CourseChallengeService._generate_questions_for` progress'dan max_lesson=tugatilgan+1,
  10 savol yig'ilmasa oynani +4 gacha kengaytiradi, keyin butun-level fallback.

Files touched:
- `app/static/course-v3.html`, `scripts/gen_course_v3_from_seed.py`, 70 dars JSON,
  `app/services/course_challenge_service.py`, `app/services/course_miniapp_practice_service.py`

Risk:
- To'lov/obuna/gate/XP logikasi tegilmadi. Lokal HTTP preview'da 5 mexanika vizual
  tekshirildi; testlar (41) o'tdi. Real Telegram'da bitta to'liq dars smoke-test tavsiya.
- Eslatma: legacy `/api/miniapp/practice/start` (test/training) max_lesson'siz — eski
  xatti-harakat saqlangan; faqat challenge yangi gate'ni ishlatadi.

### 2026-07-19 — Mashqlar dars progressiga ham bog'landi (o'rganilmagan dars so'zlari chiqmaydi)

Changed:
- `course_v3_data/lesson_gate.js` (GENERATED, `gen_course_v3_from_seed.py write_lesson_gate`,
  `--maps-only` ham yozadi): so'z/belgi → [HSK daraja, dars] — birinchi o'rgatilgan joyi
  (1247 so'z, 1055 belgi). Qo'lda tahrirlanmaydi. Avvalgi `memo_lv.js`/`gen_memo_lv.js` O'CHIRILDI.
- `GET /api/voice-practice/me` endi `completed_lessons` ham qaytaradi (progress.level bandi
  user bandiga mos bo'lsa; aks holda 0) — `VoicePracticeService.user_status`.
- Ieroglif tanish / Talaffuz / Yodlash pool tartibi: 1) joriy levelning O'RGANILGAN darslari
  (dars ≤ tugatilgan+1); 2) yetmasa quyi levellar (to'liq o'rganilgan, aralashma sifatida);
  3) faqat HSK1 boshida (quyi level yo'q) yaqin keyingi darslarga minimal kengayish;
  4) gate xarita bo'lmasa eski level-fallback. Ya'ni user 4-darsda bo'lsa o'z darajasining
  7-dars so'zlari mashqqa CHIQMAYDI.
- Test markazi imtihonlari butun-level formatida qoldi (dars bilan cheklanmaydi) — bu HSK
  imtihon simulyatsiyasi. Challenge savollari ham hozircha butun level bo'ylab (follow-up).

Why:
- Foydalanuvchi: "4-darsda bo'lsam 7-dars so'zlari kelmasin" — avval faqat HSK daraja
  filtrlanardi, level ichidagi dars progressi hisobga olinmasdi.

Files touched:
- `scripts/gen_course_v3_from_seed.py`, `app/static/course_v3_data/lesson_gate.js` (yangi),
  `app/static/course_v3_{recognition,pronunciation,memorize}.html`,
  `app/services/voice_practice_service.py`; o'chirildi: `memo_lv.js`, `gen_memo_lv.js`

Risk:
- To'lov/obuna/gate logikasi tegilmadi. Lokal HTTP preview'da tekshirildi: HSK2 4-dars →
  faqat 2:1..2:4 so'zlari; HSK2 1-dars → 2:1 + HSK1 takror; HSK1 1-dars → 1:1..1:3 (minimal
  kengayish); yodlash HSK3 5-dars → faqat 3:1..3:5 belgilari. Real Telegram smoke-test tavsiya.

### 2026-07-19 — Mashq bo'limlari user'ning haqiqiy HSK darajasiga bog'landi

Changed:
- Ieroglif tanish / Talaffuz / Yodlash / Test markazi endi userning haqiqiy darajasida ishlaydi.
  Har sahifada `LV` rezolveri: URL `level` param faqat boshlang'ich qiymat, `GET
  /api/voice-practice/me` (initData) dan kelgan `users.level` USTUN turadi. hsk4a/b → hsk4.
- Ieroglif tanish/talaffuz: WORDS puli userning aynan darajasidagi so'zlar (kam bo'lsa
  <= daraja, keyin hammasi). Yodlash: yangi `course_v3_data/memo_lv.js` (belgi → min HSK
  daraja, `scripts/gen_memo_lv.js` dan generatsiya, hsk-data.js o'zgarsa qayta ishga tushirilsin)
  orqali deck user darajasidagi belgilardan tuziladi.
- Test markazi: user darajasidagi imtihon ro'yxatda birinchi + "Sizning darajangiz" tegi (3 til).
- AI Voice avvaldan /me dan daraja olardi; endi `VoicePracticeService.start_session` hsk4a/b ni
  hsk4 ga normallashtiradi (avval INVALID_LEVEL berardi).
- course-v3.html openRecog/openPron/openTest endi `&level=MAP.level` uzatadi.

Why:
- Foydalanuvchi: "barcha bo'limlar user darajasiga mos chiqsin" — avval sahifalar URL'siz
  default hsk1 bo'lib, WORDS umuman filtrlanmasdi.

Files touched:
- `app/static/course_v3_{recognition,pronunciation,test,memorize}.html`, `app/static/course-v3.html`,
  `app/static/course_v3_data/memo_lv.js` (yangi), `scripts/gen_memo_lv.js` (yangi),
  `app/services/voice_practice_service.py`

Risk:
- To'lov/obuna/gate logikasi tegilmadi (daily-gate oqimi o'z joyida). initData yo'q preview'da
  URL level fallback ishlaydi. Lokal HTTP preview'da 4 sahifa daraja filtri tekshirildi
  (hsk1/2/3/4 pullari to'g'ri); real Telegram'da /me override smoke-test tavsiya.

### 2026-07-19 — Dars arxetiplari (xilma-xillik) + challenge savol bagi + TTS klient cache

Changed:
- `scripts/gen_course_v3_from_seed.py`: har dars endi o'z "arxetipi"da (listen/build/speak/mix,
  level+order bo'yicha deterministik) — mashq to'plami har darsda boshqacha (70/70 noyob
  ketma-ketlik). Intro tekshiruvlari 5 formatda aylanadi (ma'no/ieroglif/pinyin/tarjima/
  so'z-tinglash), yangi so'zdan keyin darhol talaffuz mashqi. Har darsda 3-4 talaffuz kartasi
  (avval 1 ta edi): intro so'z + practice so'z (rotatsiya) + dialog oxirida qisqa gap-talaffuz.
  Yangi karta: so'z-tinglash (`listening_choice` so'z varianti, faqat o'rganilgan so'zlar).
  70 dars JSON regeneratsiya qilindi; test yangilandi (listening opsiyalari endi satr YOKI so'z).
- `course-v3.html` `cardChoice`: server savollaridagi `sentence` maydoni endi kartada ko'rsatiladi
  (challenge/mashqda "Gapdagi so'z ma'nosini tanlang" gapisiz chiqayotgan bag; ____ bo'shliq
  `<u>?</u>` bo'lib chiqadi, listening'da audio ostida).
- `course_challenge_service._payload_map`: legacy FLAT savol ro'yxati endi faqat challenger'ga
  tegishli — opponent start bosganda o'z tilida/darajasida yangi to'plam generatsiya bo'ladi
  (tj user'ga uz savollar chiqish bagi). Eski boshlangan raundlar fallback orqali to'g'ri baholanadi.
- TTS: 7 sahifada (course-v3, memorize, recognition, pronunciation, test, voice, hsk-lugat)
  klient blob-cache — bir marta o'ynagan ovoz qayta bosishda darhol chiqadi; kurs darsida
  keyingi 4 kartaning audiosi oldindan yuklanadi (`prefetchUpcomingAudio`). Server disk cache
  (`/api/v3/tts`) avvaldan bor edi.

Why:
- Foydalanuvchi: darslar hamma levelda bir xil shablon — zeriktiradi; talaffuz mashqlari kam;
  challenge savollari gapisiz/aralash tilda; ovoz kech chiqadi.

Files touched:
- `scripts/gen_course_v3_from_seed.py`, `app/static/course_v3_data/**` (70 dars + 4 map),
  `tests/test_course_v3_static_data.py`, `app/static/course-v3.html`,
  `app/static/course_v3_{memorize,recognition,pronunciation,test,voice}.html`,
  `app/static/hsk-lugat.html`, `app/services/course_challenge_service.py`

Risk:
- To'lov/obuna/ruxsat/XP backend tegilmadi. Dars kontenti seed'dan verbatim, distraktorlar gated.
  Real Telegram WebView smoke-test tavsiya: bitta to'liq dars (intro ichidagi mikrofon kartasi),
  challenge raund (tj user), ovoz tugmasi ikkinchi bosishda darhol chiqishi.

### 2026-07-19 — Course v3 UI yangilanishi: dofamin effektlar + yangi panda + yo'lakcha bezaklari

Changed:
- Course v3 (course-v3.html va barcha course_v3_* sahifalar) yangilangan ko'rinishga o'tdi:
  asl parchment palitra biroz tiniqlashtirildi (--cin #E04A40, --gold #E9A916, --jade #2FA06A,
  --paper #FDF9F0), bo'lim banneri qizil gradient. subscription.html va hsk-lugat.html tegilmagan.
- Panda maskot (`pandaChar`) qayta chizildi: kattaroq, do'mboq, Duolingo maskot uslubi;
  API o'zgarmagan (happy/celebrate/talk, pd-* klasslar). Konteynerlar kattalashtirildi
  (.pmasc 72px, .lu-panda 92px).
- 4 yangi dofamin effekt (hammasi o'z momentida): streak alanga ekrani (`App.showStreakScreen`,
  FAQAT streak oshgan kuni — kuniga 1 marta); kunlik maqsad halqasi headerda (`goalRingHtml` +
  `flyXp` XP uchishi); combo edge-glow (3/5/10 ketma-ket to'g'rida) + haptic eskalatsiya
  (med/heavy); sandiq ochilish overlay (`App.openChest`, mavjud reward-chest backend'iga ulangan,
  yo'ldagi chest nodelar endi bosiladi).
- Yo'lakcha bezaklari: `_DECOR`/`scenerySvg` (daraxt, bambuk, tosh, gulli buta, pagoda, o't) —
  pandasiz qatorlarda node qarshi tomonida, dekorativ (pointer-events:none).
- Backend: `CourseGamificationService.snapshot()` endi `daily_xp` (bugungi XP sum) qaytaradi;
  `/api/v3/map` progress payload'iga `daily_xp` + `reward_chest` qo'shildi. Profil/header
  kunlik halqasi endi haqiqiy kunlik XP'dan (avvalgi soxta `xp % 50` o'rniga, fallback qolgan).

Why:
- Foydalanuvchi Duolingo/HelloChinese darajasidagi dofamin UX so'radi; dark tema variantini
  rad etib, asl ranglarning tiniqroq versiyasini tanladi.

Files touched:
- `app/static/course-v3.html`, `app/static/course_v3_{onboarding,recognition,pronunciation,test,mistakes,voice,memorize}.html`
- `app/main.py`, `app/services/course_gamification_service.py`

Risk:
- Dars/quiz/to'lov/obuna/ruxsat logikasi o'zgarmagan; faqat UI + 2 ta additiv snapshot/payload field.
- Voice sahifasi o'z "xona sahnasi" dizaynida qoldi (faqat tokenlar tiniqlashtirildi).
- HTML sahifalar no-store — foydalanuvchilar deploy'dan keyin darhol yangi ko'rinishni oladi.

Follow-up:
- Real Telegram WebView'da (iOS/Android) bitta to'liq dars + streak ekrani + sandiq smoke-test.

### 2026-07-18 — Subscription checkout stage analytics

Changed:
- Subscription Mini App now records when a user reaches payment instructions and when a receipt image is selected, linked by a short-lived checkout attempt ID.
- Admin payment funnel reconstructs only the same checkout attempt and links screenshot/approval through the payment ID instead of mixing independent users or periods.
- Locked-lesson checkout preserves the user's intent with course-continuation copy in Uzbek, Russian, and Tajik.

Why:
- The old funnel mixed unrelated acquisition sources and could not identify where users dropped between opening checkout and submitting a receipt.

Files touched:
- `app/main.py`, `app/services/admin_miniapp_service.py`, `app/static/subscription.html`, `tests/test_course_v3_static_data.py`

Risk:
- Analytics and UI copy only. Payment creation, approval, subscription, and access logic are unchanged. The new funnel intentionally shows `Ma'lumot yig'ilmoqda` until attempt-aware traffic exists.

Follow-up:
- After enough post-deploy traffic, compare `Obuna sahifasi → Rekvizitni ko'rdi → Skrinshot tanladi → Skrinshot yubordi` and optimize the largest verified drop.

### 2026-07-18 — Direct first-lesson activation and exact retention metrics

Changed:
- Successful Course v3 onboarding now opens the selected lesson immediately instead of sending a user who chose “first lesson” into the 11-step product tour.
- Admin analytics measures onboarding → lesson start within 2 minutes, section completion within 15 minutes, and lesson completion within 24 hours using only cohorts whose measurement window has ended.
- D1/D7 retention now uses exact Mini App open windows; Mini App opens are recorded per course session, not once per calendar day.
- Session and lesson-time metrics report only measurable sessions and real completed lessons. Unfinished-lesson notification attribution is source-specific.
- Motivation reminders exclude users inactive for more than 14 days and users currently marked as bot-blocked.

Why:
- The main CTA promised a first lesson but inserted a long tour before the learning value. Previous retention/session/payment proxy calculations could also hide where users actually dropped.

Files touched:
- `app/static/course_v3_onboarding.html`, `app/static/course-v3.html`, `app/main.py`, `app/services/admin_miniapp_service.py`, `app/services/motivation_reminder_service.py`, `app/bot/utils/course_miniapp.py`, tests.

Risk:
- Course content, lesson order, quiz/homework result flow, payment approval, and subscription access are unchanged. Exact D1/D7 values are not directly comparable to the previous broad proxy.

Follow-up:
- After deploy, monitor a fresh 7-day cohort: onboarding → lesson ≤2m, first section ≤15m, lesson complete ≤24h, exact D1/D7, and checkout attempt stages.

### 2026-07-18 — D1 first-lesson recovery experiment

Changed:
- New users who started lesson 1 during onboarding, did not finish it, and did not return are assigned once to a stable 50/50 treatment/control experiment after 24–36 idle hours.
- Treatment receives one localized text reminder whose CTA opens the exact level/lesson with `source=d1_recovery_v1&autostart=1`; control receives no D1 message.
- Course v3 stores the current lesson-card index locally for seven days, resumes it on the same device, clears it on completion, and consumes `autostart` only once.
- Assignment/sent/failure events are server-only and do not update `User.last_active_at`. Both arms suppress Motivation and CourseReminder messages for the 48-hour outcome window.
- Admin analytics reports matured 48-hour ITT treatment/control return, same-lesson completion, send failure, bot-block guardrail, and percentage-point lift. Results below 30 matured users per arm are directional only.

Why:
- D1 retention is low, and the prior reminder could describe one lesson while opening another or restart a partly completed lesson from the first card.

Files touched:
- `app/services/motivation_reminder_service.py`, `app/services/course_reminder_service.py`, `app/services/notification_template_service.py`, `app/services/admin_miniapp_service.py`, `app/db/models/course_miniapp_event.py`, `app/static/course-v3.html`, `app/main.py`, tests.

Risk:
- No database migration and no course/payment/access logic change. Resume is device-local, so a different device starts from the first card. The experiment must not be judged before both arms have matured 48-hour outcomes.

Follow-up:
- Deploy, then wait for at least 30 matured users in each arm before using lift as more than a directional signal; also watch treatment send rate and bot-block lift.

### 2026-07-16 — To'g'ri bot username + Course Mini App map cold-start retry

Changed:
- Bot username yagona manba `bot_username_value()` (`app/main.py`): env `BOT_USERNAME`,
  sozlanmagan bo'lsa default endi `darsi_chini_bot` (eski xato `hsk_ai_bot` EMAS).
  Referral link fallback shu helperga o'tdi; `/api/v3/map` javobiga `bot_username` qo'shildi.
- `course-v3.html` da 3 joyda qattiq yozilgan `t.me/hsk_ai_bot` (auth-gate "Botga qaytish",
  reyting share matni, do'st chaqirish fallback linki) global `BOT_USERNAME` + `botLinkUrl()`
  bilan almashtirildi; map javobidagi `bot_username` orqali jonli yangilanadi.
- Course Mini App map yuklash (boot + `loadLevel`) endi `loadCourseMap()` orqali: cold-start /
  tranzient 5xx yoki tarmoq xatosida darrov "Telegramga ulanmagan" gate ko'rsatmasdan 3 martagacha
  qayta uriniladi (0.5s/1s/1.5s). Faqat haqiqiy 401 (auth) yoki initData yo'qligida gate chiqadi.

Why:
- Loyiha `@hsk_ai_bot` dan `@darsi_chini_bot` ga o'tgan, lekin frontend/referral fallback hali eski
  botga ishora qilardi ("botga qaytish" boshqa botni ochardi). Birinchi ochilishda Railway cold-start
  birinchi so'rovni yiqitib, "ulanmagan" gate'ni noto'g'ri ko'rsatardi.

Files touched:
- `app/main.py`, `app/static/course-v3.html`, `tests/test_course_v3_static_data.py`

Risk / follow-up:
- Frontend + 1 backend helper. To'lov/obuna/ruxsat mantig'i tegilmadi. `bot_username_value()` default
  `darsi_chini_bot` — deployda `BOT_USERNAME` env aniq shunga (yoki kerakli botga) o'rnatilgani tekshirilsin.
- MUHIM: agar "ulanmagan" HAR ochilishda (faqat birinchi emas) chiqsa, ildiz sabab — server `BOT_TOKEN`
  `@darsi_chini_bot` ники emas: initData shu token bilan tekshiriladi, mos kelmasa doim 401 bo'ladi.

### 2026-07-09 — Subscription Mini App payment UI priority

Changed:
- Subscription Mini App UI now prioritizes Tajikistan cards first, shows foreign Visa/Mastercard as the second option, and groups Alipay/WeChat under one China payment block.
- Plan display order in the Mini App starts with 1 month, then 10 days, then 3 months. Payment prices remain admin-managed and were not changed in code.

Why:
- Main paying users are in Tajikistan; showing VISA first caused confusion for users without Visa cards.

Files touched:
- `app/static/subscription.html`, `tests/e2e/test_miniapp_smoke.py`

Risk:
- UI-only change. Existing payment method codes (`visa`, `alipay`, `wechat`) and subscription/payment approval logic are unchanged.

Follow-up:
- Admin should set desired live prices in the admin Mini App.

### 2026-07-09 — Course v3 analytics funnel/onboarding/hot-user fixes

Changed:
- Course v3 pay CTA now records `CourseMiniAppEvent.checkout_opened` before redirecting to subscription, with a per-click dedupe key and non-blocking redirect fallback.
- Course v3 onboarding HTML now records `onboarding_started` and calls `/api/miniapp/onboarding` on finish; the server `onboarding_completed` payload includes level, goal, daily time, start point, and language.
- Admin hot-user counts now use Course v3 activity sources (`CourseXpEvent` + `CourseMiniAppProfile`) and profile streaks instead of old daily-practice fields.
- Subscription source stats now group raw source aliases for admin display while preserving raw source values in DB.
- `level_completed` and `lesson_jump_selected` were added to Course Mini App event allowlist.

Why:
- Admin analytics had mismatched payment funnel counts, missing onboarding completion, and stale hot-lead/streak inputs.

Files touched:
- `app/static/course-v3.html`, `app/static/course_v3_onboarding.html`, `app/main.py`, `app/services/course_miniapp_onboarding_service.py`, `app/services/admin_miniapp_service.py`, `app/services/subscription_entry_analytics_service.py`, `app/services/admin_finance_stats_service.py`, `app/db/models/course_miniapp_event.py`, tests.

Risk:
- Read/write analytics only. Payment approval, subscription entitlement, lesson order, VOCAB/GRAMMAR, quiz, and homework logic were not changed.

Follow-up:
- After deploy, verify real DB rows for `paywall_seen → checkout_opened → payment_screenshot_submitted → subscription_approved` and onboarding started/completed counts in Asia/Shanghai periods.

### 2026-07-07 — Kurs reklamasiga reklama turi (odiy/hamkorlik/bot) + universal knopka

Changed:
- `course_ad_creatives` ga ikkita ustun (`0064_course_ad_type_button`):
  - `ad_type` (String16, default `odiy`): `odiy` | `hamkorlik` | `bot`.
  - `button_text` (String64, null): universal knopka nomi (hamkorlik/bot uchun).
- Reklama qabul qilish (hamkorlik) va o'z botlarini reklama qilish **alohida
  tizim EMAS** — hammasi mavjud "Kurs reklama videolari" (course-ads) yuklash
  oqumidan o'tadi, faqat `ad_type` bilan farqlanadi. `CourseAdService`:
  `normalize_ad_type` / `normalize_button_text`, `create_video` + `payload` ga
  `ad_type`/`button_text` qo'shildi. `normalize_link` endi `@username` ni
  `t.me/...` ga aylantiradi. Upload endpoint (`/api/admin-miniapp/course-ads/upload`)
  form'dan `ad_type` + `button_text` oladi.
- Admin Mini App (`admin.html` → Boshqaruv → Kurs reklama videolari): "Reklama
  turi" select + "Knopka nomi" input (odiy'da o'chirilgan). Karta turi tegini ko'rsatadi.
- Mini App (`ads.js`): reklama video **ostida** turiga qarab knopka —
  `odiy` = knopka yo'q (avvalgi "Havolaga o'tish" chipi); `hamkorlik` = bitta CTA
  (button_text yoki default "Hamkorlik uchun yozing") → havolani ochadi; `bot` =
  Sinab ko'rish (button_text/"Sinab ko'rish") + Linkni nusxalash + Do'stga yuborish
  (Telegram share). Odiy reklama xatti-harakati o'zgarmadi. `ads.js?v=20260708`.

Why:
- Admin bitta reklama yuklash oqimidan foydalanib, oddiy reklama, hamkorlik
  (reklama qabul qilish) va o'z botlarini reklama qilishni boshqarishi uchun.

History / muhim:
- Bu ish avval alohida `course_promo_sections` jadvali + alohida video-ostidagi
  blok sifatida qilingan edi (birinchi urinish), keyin foydalanuvchi so'roviga
  ko'ra to'liq olib tashlanib, course-ads oqumiga birlashtirildi.

Risk / follow-up:
- Deploydan keyin `alembic upgrade head` (0064) ishga tushirilsin.

### 2026-07-02 — Admin Mini App advanced period statistics

Changed:
- Admin Mini App statistics now include period-aware advanced product metrics for weekly, monthly, and all-time views: D1/D7 retention, Mini App session time, lesson time, QA messages per user, voice minutes, payment abandon step, first payment time, LTV, CAC, paid/free feature adoption, and notification-open proxy.
- The advanced metrics are returned inside `statistics_reports[].advanced` from `AdminMiniAppService.overview()` and rendered as one explanatory block in `app/static/admin.html`.

Why:
- Manual admin statistics were missing product-health, payment-funnel, and paid/free adoption metrics needed to understand what users do inside the selected date window.

Files touched:
- `app/services/admin_miniapp_service.py`, `app/static/admin.html`, `tests/e2e/test_miniapp_smoke.py`

Risk:
- Read-only analytics queries only. Payment, subscription, access approval, course, quiz, and homework write flows are unchanged. CAC is shown only when portfolio expense notes/sources are marked as marketing/reklama/ads/target/CAC; notification open rate is a Mini App open proxy, not a Telegram direct open event.

Follow-up:
- For exact CAC, add a dedicated marketing spend category/source instead of relying on manual expense notes.

### 2026-07-02 — Course ad media DB backup + auto-restore

Changed:
- Course ad uploads now store the transcoded MP4 bytes in `course_ad_creatives.media_blob` with `media_size` and SHA-256 `media_checksum` metadata (`0063_course_ad_media_backup`).
- `CourseAdService` backfills DB backup for existing ads whose media file still exists on disk, and restores a missing media file from the DB backup before serving/listing active ads.
- `/uploads/course_ads/{filename}`, `/api/v3/ad`, and admin course-ad listing use this self-healing path, so deploy/restart no longer forces re-upload for ads that have a DB backup.

Why:
- Railway/runtime disk can be ephemeral. Keeping a DB backup prevents course ads from disappearing after deploy when the DB row survives but the uploaded video file does not.

Files touched:
- `app/db/models/course_ad.py`, `app/db/session.py`, `app/services/course_ad_service.py`, `app/main.py`, `alembic/versions/0063_course_ad_media_backup.py`, `tests/test_course_miniapp_foundation.py`

Risk:
- DB size grows by the uploaded ad MP4 bytes; current upload limit is 25MB per ad. Ads whose disk file was already missing before this change cannot be restored because their bytes are already gone.

### 2026-07-02 — Course ad black-screen fail-safe + persistent media visibility

Changed:
- Course v3 ad player now exits the full-screen ad overlay and falls back to the existing lesson continuation path if a video cannot load/play after retries, preventing users from being stuck on a black screen.
- Admin Mini App course-ad cards now show whether the actual video file is present on server storage. Missing files are labeled with a re-upload / persistent `MEDIA_ROOT` warning.
- `.env.example` documents optional `MEDIA_ROOT` for persistent uploaded media; Railway Volume / `RAILWAY_VOLUME_MOUNT_PATH` remains supported by the service.

Why:
- A DB ad row can survive deploy/restart while its uploaded media file disappears on ephemeral storage, making the admin think an ad exists while users receive no playable ad. Video load failure also previously left the Promise unresolved and could trap users in the ad overlay.

Files touched:
- `app/static/course-v3.html`, `app/static/admin.html`, `app/services/course_ad_service.py`, `.env.example`, `tests/test_course_miniapp_foundation.py`, `tests/test_course_v3_static_data.py`

Risk:
- Frontend/ad-admin/deployment-config only. Payment/subscription/access approval rules are unchanged. If existing ad files are already missing or old pre-transcode files are black, admin must re-upload after deploy with persistent media storage configured.

Follow-up:
- On Railway, attach persistent Volume or set `MEDIA_ROOT`, redeploy, then re-upload course ads and smoke-test one free premium lesson path in Telegram WebView.

### 2026-07-01 — Admin People hot lead + today-active segments

Changed:
- Admin Mini App People segmentida `Issiq mijoz` endi deyarli butun unpaid bazani emas, faqat unpaid (`free/trial/expired` + `none/draft/rejected`) va botni bloklamagan, oxirgi 48 soat ichida aktiv userlarni sanaydi/filtrlaydi.
- `Bugun aktiv` segmenti qo'shildi; backend payload user cardlarga `active_today` va `hot_lead` flaglarini beradi, frontend filterlar shu flaglarga tayanadi.

Why:
- Admin uchun real follow-up segment kerak: har kuni yoki kunora botga kirayotgan, lekin hali to'lamagan userlar alohida ko'rinishi kerak.

Files touched:
- `app/services/admin_miniapp_service.py`, `app/main.py`, `app/static/admin.html`, `tests/test_admin_stats_service.py`, `tests/e2e/test_miniapp_smoke.py`

Risk:
- Faqat admin analytics/filter logikasi o'zgardi. Payment/subscription/access flow tegilmadi. `Issiq mijoz` soni deploydan keyin keskin kamayishi normal, chunki eski hisob broad edi.

Follow-up:
- Agar keyin haqiqiy cadence kerak bo'lsa, `last_active_at` o'rniga activity event history bo'yicha "2 kunda kamida 2 aktiv kun" segmentini alohida hisoblash mumkin.

### 2026-06-30 — Kurs reklamasi tilga moslandi (per-language) + admin filter

Changed:
- `course_ad_creatives` ga `language` ustuni qo'shildi (uz/ru/tj yoki "all" = barcha
  tillar; default "all"). Migration `0061_course_ad_language` + `db/session.py` bootstrap.
- `CourseAdService`: `normalize_language()`, `create_video(language=...)`, payload'da
  `language`. `get_active_ad/list_active/list_active_payloads` endi ixtiyoriy `language`
  qabul qiladi va `language IN (user_lang, "all")` bo'yicha filterlaydi (None = barchasi).
- `/api/v3/ad` foydalanuvchi tiliga mos reklama qaytaradi: initData bo'lsa kanonik
  `user.language`, bo'lmasa query `lang` (frontend `fetchCourseAds` endi `&lang=LANG`
  yuboradi). `/api/v3/lesson/complete` ad-gate ham `get_active_ad(language=user.language)`
  ishlatadi — boshqa tildagi reklama bu til userini bloklamasligi uchun.
- Admin upload formasiga "Til" select qo'shildi; admin reklama ro'yxati ustida til
  bo'yicha filter chiplari (Barcha/UZ/RU/TJ + son) va kartada til tegi.

Files touched:
- `app/db/models/course_ad.py`, `alembic/versions/0061_course_ad_language.py`,
  `app/db/session.py`, `app/services/course_ad_service.py`, `app/main.py`,
  `app/static/course-v3.html`, `app/static/admin.html`,
  `tests/test_course_miniapp_foundation.py`

Risk:
- Access-adjacent: ad-supported dars gate'i endi tilga bog'liq. Mavjud reklamalar (NULL/
  default) "all" sifatida hammaga ko'rinadi — orqaga moslik saqlangan. To'lov/obuna
  mantig'i tegilmadi. Deploy'da migration `0061_course_ad_language` ishga tushsin.
  Real Telegram smoke-test: har til uchun reklama yuklab, mos til userida ko'rinishini
  va boshqa til userida ko'rinmasligini tekshirish.

### 2026-06-30 — Course v3 grammatika "ustoz" + interaktiv dialog (passiv matn olib tashlandi)

Changed:
- Grammatika kartasi (`cardGrammar`, course-v3.html) endi katta matn o'rniga qadam-baqadam
  "ustoz" oqimi: panda 李老师 ("Li ustoz") suhbat pufagi + qoidani bo'laklarga ajratish
  (`parseRule`: lead concept, Tuzilma/Inkor formulalari, izohlar) + misollar bittalab
  "Davom etish" bilan ochiladi (audio bilan). Oxirgi qadamdan keyin global CTA chiqadi.
  3 til kalit so'zlari bilan parse qilinadi (Tuzilma/Структура/Сохтор, Inkor/Отрицание/Инкор,
  Misol/Пример/Мисол); parse bo'lmasa lead = sarlavha (fallback).
- Dialog bo'limi endi to'liq interaktiv, passiv "katta matn" (`_dialogue` reading card)
  butunlay olib tashlandi (buildQueue'dan prepend o'chirildi). Yangi tartib:
  `listening_choice` ("Tinglang — nima dedi?", audio→variant) → `gap_fill` (dialog satridan
  1 ieroglif berkitiladi, `make_char_gap_card`) → `dialog_cloze` → `quick_quiz`.
- `make_char_gap_card`: dialog satridagi bitta (bir marta uchraydigan) ieroglifni berkitadi,
  chalg'ituvchi ierogliflar faqat o'rganilgan so'zlardagi belgilardan (gated).

Files touched:
- `app/static/course-v3.html` (cardGrammar + parseRule + GRT i18n + teach/gstep/gnext CSS,
  buildQueue'dan `_dialogue` olib tashlandi), `scripts/gen_course_v3_from_seed.py`
  (`make_char_gap_card`, `build_dialog_section` qayta yozildi), 70 dars qayta generatsiya.

Risk:
- Faqat statik kontent + frontend; backend (to'lov/obuna/XP/progress) tegilmadi. Barcha matn
  uz/ru/tj. Lokalda flow eval + screenshot bilan tekshirildi; real Telegram smoke-test tavsiya.

### 2026-06-30 — Course v3 Duolingo uslubidagi interaktiv dars formati

Changed:
- Har dars endi 4 bo'lim: `intro` → YANGI `grammar` (interaktiv) → `practice` → interaktiv `dialog`.
  Avval har dars bir xil shablon edi (`intro` + aynan bir xil 7 MC + quick_quiz); grammatika
  va dialog faqat passiv o'qish kartasi edi.
- 3 ta yangi card turi generatsiya qilinadi va frontendda renderlanadi:
  `sentence_builder` (so'z plitkalaridan gap yig'ish, 116 ta), `listening_choice`
  ("eshitganini tanla", har darsda), `dialog_cloze` ("dialogni to'ldir", har darsda).
- Eski MC drillar kamaytirildi (meaning/pinyin/translation/hanzi: 70→~34, har darsda 2 ta,
  dars tartibiga qarab aylanadi), interaktiv turlar bilan aralashtirildi. `gap_fill` endi
  grammatika bo'limida.
- Xitoy gapini so'zlarga bo'lish uchun lug'at-asosidagi greedy-longest-match tokenizer
  (`segment_zh`) qo'shildi; barcha plitka/variant qat'iy level-gated (faqat o'rganilgan so'z/satr).
  HSK4'da 8 ta darsda gap 8 tokendan uzun bo'lgani uchun `sentence_builder` o'tkazib yuborilgan
  (listening + cloze baribir bor).
- `cardBuilder` (course-v3.html) qiymat o'rniga bank-indeksini saqlaydigan qilib qayta yozildi
  (takroriy plitka, masalan 越×2, endi to'g'ri baholanadi).

Files touched:
- `scripts/gen_course_v3_from_seed.py` (tokenizer + 3 yangi builder + grammar/dialog bo'limlari +
  build_practice rotatsiyasi), `app/static/course-v3.html` (buildQueue grammar bo'limi,
  dialog_cloze render, cardBuilder fix, .cloze-gap CSS), 70 ta `course_v3_data/**/lesson_*.json`
  qayta generatsiya, `tests/test_course_v3_static_data.py` (yangi
  `test_interactive_cards_present_and_level_gated`).

Risk:
- Faqat statik kontent + frontend render; to'lov/obuna/ruxsat/XP/progress backend tegilmadi.
- Barcha matn uz/ru/tj to'liq (seed'dan verbatim; tokenizer yangi tarjima yaratmaydi).
- Real Telegram WebView smoke-test tavsiya etiladi (lokalda flow eval orqali tekshirildi).
- Eslatma: `tests/test_course_v3_static_data.py::...real_invite_format` testi AVVALDAN
  yiqilgan (eski `"/course_v3_data/"+lv+...` literalini qidiradi; html endi `lessonDataUrl()`
  ishlatadi) — bu o'zgarishga aloqasiz, alohida tuzatish kerak.

### 2026-06-29 — Voice pronunciation transcript + tolerant pinyin scoring

Changed:
- Pronunciation scoring now keeps exact Hanzi matching but also accepts pinyin-like STT transcripts using normalized pinyin similarity when the frontend sends `target_pinyin`.
- Pronunciation Mini App and in-lesson pronunciation cards send target pinyin and show "heard transcript" feedback, so users can see what STT recognized.
- AI Voice Mini App now shows the user's recognized speech in the subtitle/CC block when CC is enabled.
- STT prompt for pronunciation checks includes a bounded target hint to reduce false mishearing without forcing the target text.

Why:
- Users were getting false "wrong" results because the old scorer only compared exact Chinese characters and hid the STT transcript.

Files touched:
- `app/services/ai_service.py`
- `app/services/voice_practice_service.py`
- `app/main.py`
- `app/static/course_v3_pronunciation.html`
- `app/static/course-v3.html`
- `app/static/course_v3_voice.html`
- `tests/test_voice_practice_course_context.py`

Risk:
- Low/medium: user-facing voice scoring and transcript UX changed. Lesson order, quiz/homework logic, subscription/payment/access logic, and referral logic were not changed.

Follow-up:
- Smoke-test on real Telegram WebView with microphone permission because local browser cannot provide real STT audio.


### 2026-06-29 — Course ad video upload root compatibility fix

Changed:
- Course ad uploads now store ads as browser-safe `.mp4` files. Uploads are transcoded to H.264/AAC/yuv420p with `+faststart`; if `ffmpeg` is missing, upload is rejected instead of saving a video that may show a black screen in Telegram WebView.
- Course ad media responses now set explicit video media types and range support; new uploads are always `.mp4`.
- Added `nixpacks.toml` so Railway/Nixpacks installs `ffmpeg` during deploy.

Why:
- Telegram iOS/WebView can show black video for `.mov`, `.webm`, HEVC/H.265, or MP4 files without WebView-safe encoding. Fixing upload/transcode is the root fix; frontend loading/error UI remains only a fallback.

Files touched:
- `app/main.py`
- `nixpacks.toml`

Risk:
- Existing already-uploaded ad files are not converted automatically. Re-upload ads after deploy to guarantee safe MP4 encoding.

### 2026-06-29 — Course Mini App section entry speedup

Changed:
- `course-v3.html` now caches lesson JSON per level/lesson and prefetches current + next lesson after map load, so lesson start / skip-test reuse already loaded data instead of fetching every click.
- Writer overlay now opens `hsk-lugat.html?fast=1`, a lightweight mode that skips the 2.9MB dictionary script and memo data for single-character writing practice.
- `hsk-lugat.html` full dictionary still works, but `memo.js` loads lazily only when detail/memo content is needed.

Why:
- Telegram WebView was slow when entering sections because dictionary/memo assets and lesson JSON were loaded on demand for every entry.

Files touched:
- `app/static/course-v3.html`
- `app/static/hsk-lugat.html`

Risk:
- Frontend-only performance/navigation change. Course order, quiz scoring, homework, subscription/payment/access backend logic were not changed. Fast writer depends on HanziWriter stroke data CDN with a 2.5s timeout and plain-character fallback.

Follow-up:
- Real Telegram WebView smoke test recommended because local Playwright runtime was unavailable in this session.


### 2026-06-29 — Xatolar ustida ishlash (Mistake Review) frontendi ulandi

Changed:
- `course_v3_mistakes.html` "Xatolar ustida ishlash" CTA'sidagi "Boshlash" tugmasi
  ilgari hech narsa qilmasdi (onclick yo'q edi) — endi to'liq review oqimi ulandi.
- Tugma `POST /api/miniapp/mistakes/review/start` (10 ta savol, ko'p variantli) ni
  chaqiradi, sahifa ichida quiz overlay ochadi: savol → variant tanlash → darhol
  to'g'ri/noto'g'ri + izoh feedback → keyingi → yakunda `POST .../review/complete`
  bilan natija (ball, +XP, qolgan xatolar) ko'rsatiladi. Backend (CourseMistakeService)
  oldindan bor edi va o'zgartirilmadi.
- Kunlik bepul limit (403 `free_feature_limit_reached`) bo'lsa Premium taklif sheet'i
  chiqadi → `subscription.html?source=v3_mistake_review`. Yangi manba yorlig'i
  `subscription_entry_analytics_service.SOURCE_LABELS` ga qo'shildi.
- Barcha yangi matnlar uz/ru/tj 3 tilda.

Files touched:
- `app/static/course_v3_mistakes.html`
- `app/services/subscription_entry_analytics_service.py`

Risk:
- Faqat frontend wiring + 1 ta analytics yorlig'i. To'lov/obuna/ruxsat va review
  scoring/XP backend mantig'i o'zgarmadi. Mavjud `start_review`/`complete_review`
  endpointlari ishlatildi. Statik preview'da 3 ekran (savol/feedback/natija) va
  limit sheet vizual tekshirildi; real Telegram WebView smoke-test tavsiya etiladi.

### 2026-06-29 — New admin Mini App (admin.html) + deep finance stats; old admin-control.html removed

Changed:
- Replaced the old admin Mini App (`admin-control.html`) with a redesigned `admin.html`
  (dark, bot-styled, full-screen on iPhone bottom-nav + Mac sidebar). It reuses ALL existing
  `/api/admin-miniapp/*` endpoints (overview, management, users, payments, prices, channels,
  help, portfolio, broadcast, campaigns, partners, audio, notifications, course-ads) with the
  same payload contracts, so backend mutation logic is unchanged.
- Added `AdminFinanceStatsService` (`app/services/admin_finance_stats_service.py`) and
  `POST /api/admin-miniapp/finance-stats`. Returns 3 periods (weekly 7d / monthly 30d /
  all_time), each with: net profit (revenue − real AI cost from `ai_usage_events.cost_usd` −
  manual portfolio expense, all USD), ARPU/ARPPU/avg check, renewal & churn %, and source→paid
  (which entry source brings real revenue). Every block ships an Uzbek `explain` string.
  Revenue→USD uses the same TJS/USD/CNY constants as PortfolioService (decoupled so the stats
  module does not import the OpenAI chain).
- `/admin` now shows a 2-button entry: "🧭 Admin mini ilova" (WebApp → admin.html) and
  "🛠 Ruchnoy panel" (callback `adm:menu` → in-chat manual admin sections). New callback
  `adm:entry`; manual menu lost its WebApp buttons and gained a "⬅️ Asosiy menyu" back button.
- `admin_miniapp_url()` now points to `admin.html`; `admin_miniapp_v2_url()` removed;
  `/admin-control.html` route and file deleted.

Why:
- Old admin Mini App was hard to use and only showed "revenue", not real "net profit". Admin
  needed net profit, ARPU/ARPPU, churn/renewal, source→revenue, and detailed Uzbek stats split
  by 7d/30d/all-time in one consistent layout.

Files touched:
- New: `app/services/admin_finance_stats_service.py`, `app/static/admin.html`
- Edited: `app/main.py`, `app/bot/utils/course_miniapp.py`, `app/bot/handlers/admin.py`,
  `tests/e2e/test_miniapp_smoke.py`
- Deleted: `app/static/admin-control.html`

Risk:
- Read-only analytics + UI/entry-flow change; no payment/subscription/access logic changed.
  finance-stats verified against a SQLite dataset (net profit, ARPU/ARPPU, churn, source→paid
  all correct). Real Telegram admin smoke-test after deploy still recommended.

### 2026-06-29 — Course Mini App motivation reminder delivery/timezone fix

Changed:
- Course Mini App motivational reminders (`rating_overtaken`, `daily_goal`, `streak_risk`) now target all non-blocked Mini App profile users instead of only `status="active"` users.
- Reminder day/window calculations now use each profile's saved `timezone_offset_minutes` from the Mini App, with UTC+5 only as a fallback when no offset exists.
- `/api/v3/map` stores the client `tz` query value so existing Course v3 users update their profile timezone when opening the Mini App.

Why:
- Course Mini users are often `trial`, `free`, or `expired` after the access-state migration; the old `User.status == "active"` query made the reminder service skip most users.
- Hardcoded Tajikistan time made evening reminders wrong for users outside UTC+5 even though the project already stores Mini App timezone offsets.

Files touched:
- `app/services/motivation_reminder_service.py`
- `app/main.py`
- `app/static/course-v3.html`
- `tests/test_motivation_reminder_service.py`

Risk:
- Low/medium: user-facing notification delivery timing changes. Payment, subscription, lesson, quiz, and access limits are unchanged.

Follow-up:
- After deploy, wait for the 20:00-21:30 Tajikistan-time window or create a controlled test profile to confirm a real Telegram reminder is delivered.

### 2026-06-29 — Course Mini App rating chat notification scope

Changed:
- `rating_passed` chat notification was removed; passing another user should not create a Telegram chat message for the passer.
- `rating_overtaken` remains for the user whose rank drops.
- Course leaderboard now seeds `last_known_rank` the first time the user loads the leaderboard, so future rank changes can be detected.

Why:
- Rank-up copy is better as Mini App post-lesson/result feedback, not as a Telegram chat notification. Without an initial rank baseline, rank-drop notifications still cannot be detected reliably.

Files touched:
- `app/services/motivation_reminder_service.py`
- `app/services/course_gamification_service.py`
- `app/services/notification_template_service.py`
- `tests/test_motivation_reminder_service.py`

Risk:
- Low: chat notification scope restored. No payment, subscription, lesson, quiz, homework, or access-limit logic changed.

Follow-up:
- If rank-up feedback is needed, add it to the Mini App post-lesson/result screen instead of Telegram chat.

### 2026-06-29 — Course Mini App practice/ad daily limits (server-side paywall)

Changed (access/payment logic — handle with care):
- Free users now get **1 full session per day** on each "Mashq" section: Ieroglif tanish (`recognition`), Talaffuz (`pronunciation`), Yodlash (`memorize`), Test markazi (`training_test`/`placement`). Dictionary lookup (`hsk-lugat`) stays free. AI Voice stays at 1 lifetime (`FREE_TOTAL_SESSIONS=1`, unchanged).
- Free users can open at most **2 premium lessons per day via the "Reklama bilan davom etish" path** (`ad_lesson`); after that the ad button is hidden and `adDailyLimit` text is shown until tomorrow.
- Course ads: `/api/v3/ad` now returns **all** active creatives (`ads[]`); `showCourseAd` plays them sequentially (each its mandatory time, `adNext` between them) then shows the subscribe/continue block after the last one.

How it works (no DB migration):
- New `CourseMiniAppAccessService.consume_daily_use(user, feature_key, ref=...)` / `daily_status(...)` count today's rows in the existing `course_miniapp_events` table (`event_name="practice_daily_used"`, `session_id=feature`, per-UTC-day). `ref` makes a use idempotent (reload-safe; `ref`=session token for sections, `ref`=lesson_order for ad lessons). Limits in `COURSE_DAILY_FREE_LIMITS`.
- New endpoint `POST /api/v3/practice/daily-gate` (features recognition/memorize/pronunciation/training_test/placement) is the gate for the section pages; returns 403 → page shows a limit/Premium screen. Server-side, so clearing localStorage / reloading cannot bypass it.
- Authoritative ad-lesson cap is enforced in `POST /api/v3/lesson/complete` (free + premium lesson → `consume_daily_use(feature_key="ad_lesson", ref=lesson_order)`); `/api/v3/map` returns `ad_lessons` status for the UI.
- Pronunciation: `FREE_PRONOUNCE_DAILY` raised 3→25 as a pure STT cost ceiling (the 1/day session gate is the real access control).

Risk/follow-up:
- Legacy `/api/miniapp/practice/start|complete` (CourseMiniAppPracticeService) switched test/training from lifetime-1 to daily-1 too (looser, consistent). Course v3 test page does NOT use that flow (client-side exams + daily-gate).
- All new user-facing strings added in uz/ru/tj.

### 2026-06-29 — Soft subscription-expiry churn flow

Changed:
- Paid users whose subscription expires now receive a softer expiry offer with `Obunani davom ettirish` and `Keyinroq` instead of only a hard course-access notice.
- Expired paid users who do not interact get one 24-hour follow-up asking for a short feedback signal; repeated follow-up spam is prevented with user-level timestamps.
- `Keyinroq` / feedback choices record churn reasons through `BotFeedback`; only price/budget reasons immediately unlock the existing 20% feedback-discount checkout path.

Why:
- Expiry messaging needed to reduce pressure while still capturing why users do not renew and only discounting price-sensitive users.

Files touched:
- `app/services/subscription_churn_service.py`, `app/bot/handlers/subscription_churn.py`, `app/bot/keyboards/subscription_churn.py`
- `app/main.py`, `app/services/access_service.py`, `app/services/subscription_service.py`, `app/db/models/user.py`
- `alembic/versions/0060_subscription_churn_flow.py`

Risk:
- Medium: user-facing subscription/access-adjacent flow changed. Paid activation and payment approval rules are unchanged; a migration adds churn tracking columns on `users`.

Follow-up:
- Deploy migration `0060_subscription_churn_flow`; smoke-test real Telegram expiry message, `Keyinroq`, price/budget discount, non-discount feedback, and 24-hour follow-up.

### 2026-06-29 — Admin Mini App weekly/monthly/all-time statistics

Changed:
- Admin Mini App overview payload now includes `statistics_reports` split into weekly (last 7 days), monthly (last 30 days), and all-time reports.
- Each period report includes users, active users, approved payment users/revenue, pending/rejected payments, current/new bot blocks, and Course Mini App activity for the same period.
- `miniapp_course_stats(session, since=None)` can now filter Course Mini App event analytics by `created_at`.
- `admin-control.html` Statistics tab has period buttons, quick metric cards, period-specific conversion bars, and copies the selected report text.

Why:
- Admin needed weekly, monthly, and full statistics visible inside the admin panel instead of one mixed report.

Files touched:
- `app/services/admin_miniapp_service.py`, `app/services/admin_stats_service.py`, `app/static/admin-control.html`, `tests/test_admin_stats_service.py`

Risk:
- Read-only analytics/UI change. Payment, subscription, access, referral, lesson, quiz, and homework logic are not changed.

Follow-up:
- Real Telegram admin Mini App smoke-test after deploy; local Chromium smoke test is blocked by macOS sandbox permission in this Codex environment.

### 2026-06-29 — Course Mini App referral list + weekly rating reset behavior

Changed:
- `/api/v3/invite` now also returns the current user's referred users for the Course Mini App friends tab: name, Telegram username/id, referral status, weekly XP, total XP, course level, completed lessons, and paid flag.
- Course v3 friends tab now shows invited referrals, opens the same full profile overlay used by rating users, and lets the user open Telegram chat or send a Course challenge from that profile.
- Course leaderboard is now one weekly pool instead of filtering users by lifetime XP league. Weekly rating display uses weekly XP only, so after the weekly reset users show `0` instead of falling back to lifetime XP.

Why:
- Users need to see and re-engage people they invited. The old rating logic made weekly reset look broken because lifetime XP still separated users into league buckets and appeared as the visible score when weekly XP was zero.

Files touched:
- `app/services/referral_service.py`, `app/main.py`
- `app/services/course_gamification_service.py`
- `app/static/course-v3.html`
- `tests/test_course_v3_static_data.py`

Risk:
- Medium: user-facing Mini App referral/rating flow changed. No payment/subscription/access entitlement logic changed. Real Telegram WebView smoke-test with two accounts is still recommended.

Follow-up:
- In Telegram, verify invited-user list, profile overlay, direct Telegram chat behavior for username/no-username users, challenge send/receive, and Monday reset display.

### 2026-06-29 — Access state classifier + Telegram bot block tracking

Changed:
- Added canonical access classification for `paid`, `temporary_trial`, `trial`, `free`,
  `expired`, `blocked` without rewriting the whole subscription system.
- Free/expired users no longer fall into `access_start_first` in QA/image access; they
  use free-tier limits. Expired paid users become `status="expired"`; expired temporary
  trial users become `status="free"`.
- Course trial completion moves a `status="trial"` user to `status="free"` while keeping
  course trial fields as the source of trial entitlement history.
- Added Telegram bot-block tracking fields on `users` and a silent daily `getChat` scan.
  Admin block (`status="blocked"`) remains separate from Telegram bot block.
- Admin Mini App now shows separate `free` and `bot_blocked` segments.

Why:
- Trial/free/paid/expired were mixed across bot, Course Mini App, and admin stats, which
  could make old `free` users look like they had not started the bot.

Files touched:
- `app/services/user_access_state_service.py`, `app/services/access_service.py`
- `app/services/course_trial_service.py`, `app/services/course_miniapp_access_service.py`
- `app/services/bot_block_status_service.py`, `app/db/models/user.py`, `app/db/session.py`
- `app/main.py`, `app/services/admin_miniapp_service.py`, `app/static/admin-control.html`
- `alembic/versions/0059_user_bot_block_tracking.py`

Risk:
- Medium: access/payment-adjacent logic changed. The patch is backward-compatible and
  does not bulk-migrate existing users. Deploy must run migration `0059_user_bot_block_tracking`.

Follow-up:
- Smoke-test real Telegram: free user asks QA, expired paid user asks QA, trial lesson
  completion, admin Mini App free/bot-blocked segments, and bot-block status after a user
  blocks/unblocks the bot.

### 2026-06-29 — Course v3 and QA level/language canonical sync

Changed:
- Course v3 map no longer serves unauthenticated/local preview data when Telegram `initData` is missing, invalid, or the user is not found; the Mini App shows a "return to bot and press /start" gate instead.
- Course v3 uses `users.level` and `users.language` as the canonical source for map loading, ad view recording, skip-test unlock, lesson completion, practice start/complete, and challenge creation. Client URL/query/payload level/lang are ignored for these write paths.
- Finishing the last lesson in a band promotes `users.level` to the next HSK band, so QA and Course stay aligned.

Why:
- QA mode and Course mode must not open at different HSK levels or languages. A failed Mini App API/bot connection must not silently fall back to HSK1 or cached/local preview.

Files touched:
- `app/main.py`, `app/static/course-v3.html`, `app/services/course_challenge_service.py`

Risk:
- Medium: affects course progress, practice/challenge level selection, and unauthenticated Mini App behavior. Smoke-test inside real Telegram WebView after deploy.

Follow-up:
- Verify a user with non-HSK1 level/language in bot opens Course v3 at the same level/language, then completes a lesson and starts practice/challenge without drift.

### 2026-06-29 — Mini App slowness + lesson writer/dictionary deep-link fixes

Changed:
- `hsk-data.js` (2.9 MB) and `course_v3_data/memo.js` (440 KB) were served with
  `no-store` headers, so every Mini App page open and every in-lesson writer iframe
  re-downloaded ~3.4 MB. They are loaded as `file.js?v=YYYYMMDD` (version-busted), so
  they are now served with `Cache-Control: public, max-age=31536000, immutable` via a
  new `static_asset_response()` / `STATIC_ASSET_HEADERS` in `app/main.py`. HTML pages
  stay `no-store`. Bump the `?v=` query when the data content changes.
- `hsk-lugat.html` deep-link `?char=` (used by the lesson pencil ✏️ writer) previously
  only opened a detail on an exact `WORDS[].h` match and otherwise silently fell back to
  the full dictionary list ("opens old dictionary, doesn't open the requested char").
  New `openDeepChar()` tries: exact word → word containing the text → word containing the
  first character → synthesized `{h:deep}` so the stroke writer always shows the requested
  character.
- "Keyingi so'z" (next-word) button in the dictionary detail used to appear only after the
  stroke animation finished. It is now shown at the end of `loadChar()` (self-hides when no
  next word), so it works without waiting for the animation and across multi-char nav.

Why:
- User reported: in-lesson pencil sometimes opens the old dictionary and not the needed
  character; the next-character button sometimes does nothing; HTML sections open slowly.

Files:
- `app/main.py`, `app/static/hsk-lugat.html`

Risk:
- Caching is keyed by the full URL incl. `?v=`; if `hsk-data.js`/`memo.js` content changes
  without bumping `?v=`, clients keep the old cached file. No payment/subscription/access
  logic changed. Real Telegram WebView smoke test still recommended.

### 2026-06-29 — Course ad: admin-controlled duration, end-of-ad subscribe block, advertiser link, no mid-lesson force

Changed:
- Course ad watch duration is now admin-controlled in the 5–120s range (was hard-clamped to 6–7s). `COURSE_AD_MIN_SECONDS=5`, `COURSE_AD_MAX_SECONDS=120` in `app/services/course_ad_service.py`; frontend `adDuration()` in `course-v3.html` uses the same clamp so client watched-seconds match the server gate.
- Each ad now ends with a subscribe block ("Obuna bo'ling — reklamasiz, limitsiz") offering "Obuna olish" (→ paywall) and "Reklama bilan davom etish" (continue). Shown after the countdown for start/middle/end placements.
- `CourseAdCreative.link_url` added (advertiser link). Admin upload form has an optional link field; tapping the ad video in the Mini App asks (Telegram showConfirm) before opening the link via `tg.openLink`.
- Ad-supported lessons no longer force the subscribe sheet mid-lesson: start/middle/end ad errors now just continue the lesson, and a `free_feature_limit_reached` at completion of an ad-supported lesson shows a toast instead of the locked-lesson paywall.
- Admin Mini App can now fully DELETE a course ad (not just toggle): `POST /api/admin-miniapp/course-ads/delete` removes the row and the media file from disk. `CourseAdService.delete()` returns the media path for file cleanup. Toggle button relabeled to Фаолсизлантириш/Фаоллаштириш; a separate red "Бутунлай ўчириш" button does the full delete.

Why:
- Duration was stuck at 7s; advertisers/admin need control. The subscribe block gives a clean upsell at each ad without hard-blocking. Advertiser links monetize the placement. Forcing a paywall mid-lesson after the user chose the ad path was a bad UX bug.

Files:
- `app/db/models/course_ad.py`, `app/services/course_ad_service.py`, `app/main.py` (upload endpoint), `app/db/session.py` (bootstrap column), `alembic/versions/0058_course_ad_link_url.py`, `app/static/admin-control.html`, `app/static/course-v3.html`, `tests/test_course_miniapp_foundation.py`.

Risk:
- Migration `0058_course_ad_link_url` adds nullable `link_url`; runtime bootstrap also patches legacy DBs. Server-side ad gate (`has_completed_required_views`, all 3 placements) is unchanged.

### 2026-06-28 — Challenge invite deep-link and XP rewards

Changed:
- Course challenge invites now use clearer Uzbek/Russian/Tajik duel copy, edit the original invite message after accept/reject, and open Course v3 directly with `tab=rating&challenge_id=...`.
- Course v3 can deep-link into a challenge, accept/reject pending invites, start the shared 10-question round, submit answers, and show result/XP feedback.
- Challenge completion grants XP, and completed rounds grant bonus XP to the winner; exact ties reward both players.
- Practice/challenge question selection now samples across the level more evenly by lesson/type/subtype instead of stopping at the earliest lessons.

Why:
- Telegram challenge messages were mixed-language and the Mini App button opened a generic profile instead of the actual duel.
- Challenge rounds needed a stronger reward loop and fair, same-question gameplay for both users.

Files touched:
- `app/services/course_challenge_service.py`
- `app/services/course_miniapp_practice_service.py`
- `app/bot/handlers/challenge.py`
- `app/bot/utils/course_miniapp.py`
- `app/static/course-v3.html`
- `tests/test_course_challenge_service.py`
- `tests/test_course_miniapp_foundation.py`

Risk:
- Touches user-facing challenge flow, Mini App routing, question selection, and XP award events. Payment/subscription logic is not changed.

Follow-up:
- Smoke test in real Telegram WebApp with two accounts: send challenge, accept/reject, open direct duel, complete both sides, and verify XP/rating updates.

### 2026-06-28 — HSK exam answer hint cleanup

Changed:
- Test Center HSK 1-4 exam renderer no longer shows pinyin or secondary hint labels inside answer options.
- Meaning/listening questions show localized answer choices only; grammar, fill-blank, and writing/order questions show Chinese choices only.

Why:
- Answer options previously exposed pinyin, translations, or labels like `(noto'g'ri tartib)`, making some exam questions answerable without real understanding.

Files touched:
- `app/static/course_v3_test.html`
- `tests/test_course_v3_static_data.py`

Risk:
- Low. Exam data, scoring, result flow, payment, subscription, and access rules are unchanged.

Follow-up:
- Re-test in Telegram WebView after deploy on HSK 1-4 exams, especially meaning and writing/order questions.

### 2026-06-28 — Course v3 reward message correctness

Changed:
- Course v3 lesson-completion rank-up popup now refreshes real leaderboard data before showing and only appears when the user's rank actually improved.
- Mini App rating rows now preserve server-provided rank order, including stable tie handling.
- Motivation reminder ranking uses the same stable tie-breaker and no longer sends `0 XP` as the overtaken gap.
- Course v3 lesson-completion reward overlay now displays the backend `awarded_xp` value instead of hardcoded fake rewards such as `+60 XP`.

Why:
- The old lesson-completion popup could claim the user rose in ranking after every lesson and could name the wrong user because it used stale client leaderboard data.
- The old reward overlay showed fixed XP values that did not match real XP awarded by `CourseGamificationService`.

Files touched:
- `app/static/course-v3.html`
- `app/services/course_gamification_service.py`
- `app/services/motivation_reminder_service.py`

Risk:
- Low. Lesson completion, XP awarding, payment, subscription, and access rules are unchanged.

Follow-up:
- Re-test in real Telegram WebView after deploy because local Playwright Chromium is blocked by sandbox permissions.

### 2026-06-28 — Course v3 analytics, skip-test unlock, and real fallback cleanup

Changed:
- Course v3 now records `miniapp_opened` from `/api/v3/map` and client events for `lesson_started`, `section_started`, `section_completed`, `card_seen`, `interaction_completed`, `test_started`, and `paywall_seen` with source/session/dedupe data.
- Skip-ahead tests in Course v3 now call `/api/v3/lesson/unlock`; backend validates Telegram WebApp auth, lesson existence, and premium/free access before updating `course_progress`.
- Gamification snapshots include real weekly reset time/seconds for the rating countdown.
- Admin course stats count Course v3 `lesson_completed` together with legacy `book_lesson_completed`.
- Subscription Mini App API-error fallback no longer displays preview/mock prices; preview prices remain available only in explicit preview mode.

Why:
- Course v3 traffic was undercounted in admin stats because v3 did not emit the old Mini App analytics events.
- Skip-test unlock was frontend-only, so reload/backend progress could disagree with the UI.
- Rating/profile/subscription UI had fake fallback or hardcoded values that could look like real business data.

Risk:
- This touches course analytics and Course v3 skip-test access/progress. Payment approval and subscription pricing logic are not changed.

Files touched:
- `app/main.py`
- `app/static/course-v3.html`
- `app/static/subscription.html`
- `app/services/course_gamification_service.py`
- `app/services/admin_stats_service.py`
- `app/services/admin_miniapp_service.py`
- `app/db/models/course_miniapp_event.py`
- `tests/test_course_gamification_service.py`
- `tests/test_course_v3_static_data.py`

Follow-up:
- Browser smoke test should be repeated in a normal local/dev environment or Telegram WebApp, because this Codex sandbox blocked localhost port binding and `file://` browser navigation.

### 2026-06-28 — Course v3 tour narration fixed for Uzbek/Tajik

Changed:
- Course v3 onboarding tour now plays pre-generated MP3 narration from
  `app/static/audio/tour/{uz,ru,tj}/{key}.mp3` through `/audio/tour/{lang}/{key}.mp3`.
- Tour UI text and TTS text are separated in `scripts/gen_tour_audio.py`: screen text stays
  clean, while Uzbek/Tajik audio uses TTS-friendly wording.
- Browser speechSynthesis fallback no longer forces Uzbek/Tajik into Turkish/Russian voices;
  fallback runs only when a native matching browser voice exists. Cache version bumped to
  `TOUR_AUDIO_VER="20260628b"`.

Why:
- Device/browser TTS was producing bad Uzbek/Tajik pronunciation in the first Course v3 tour.
  Tajik has no native Edge voice, so the Tajik MP3s use Russian neural voice with phonetic
  Cyrillic text prepared for that voice.

Files touched:
- `app/static/course-v3.html`
- `app/main.py`
- `scripts/gen_tour_audio.py`
- `app/static/audio/tour/`

Risk:
- Frontend/static-audio only. Lesson order, quiz, homework, payment/subscription/access logic
  unchanged.

Follow-up:
- Real Telegram WebView listening check is still useful because autoplay policy can vary by
  client, but local Playwright verified UZ/TJ tour visibility and 2xx `audio/mpeg` requests.

### 2026-06-28 — Course v3 UX fixes: subscription nav, no-ad free fallback, league chat

Changed:
- Subscribe button no longer kicks users to the external browser: `App.goPay()` now
  navigates the same-origin `subscription.html` inside the Telegram Mini App webview
  via `location.href` instead of `tg.openLink`. Paywall/locked-lesson sheets got a clear
  trilingual hint: "Subscribe → after payment confirmed, lessons open right here".
- Ad-supported path when NO admin ad is uploaded: free users now continue the next
  premium lesson for free instead of being blocked. `/api/v3/lesson/complete` checks
  `CourseAdService.get_active_ad()`; if none active, the ad-gate is skipped (ad_supported
  =True). Frontend `_isNoAd()` lets start/middle/end ad failures (course_ad_not_found)
  fall through to the lesson. When admin enables an ad later, the 3-placement gate
  applies again automatically.
- Removed redundant "Keyinroq/Позже/Дертар" ghost close buttons from sheets (paywall,
  locked lesson, skip-test offer, skip-test result) since each sheet already has an X +
  backdrop-tap close.
- Profile streak calendar now reflects real data (current weekday + `progress.streak`)
  instead of a hardcoded week; header shows real streak count, not "Rekord: 23".
- Profile cups/trophies are now derived from real progress (completed lessons / streak)
  and the whole cups section is hidden when the user has earned none.
- League/rating "message" button opens the ranked user's direct Telegram chat
  (`openUserChat` via username/`tg://user?id=`), and "Challenge" now actually POSTs
  `/api/miniapp/challenges` (delivers a real bot notification to the opponent) instead
  of only showing a toast. `ratingUsers` now carries `username`/`tgId` from the
  leaderboard payload.

Files touched:
- `app/static/course-v3.html`
- `app/main.py` (v3 lesson complete ad gate)

Risk / follow-up:
- Access change: free users can now progress through premium lessons one-by-one while NO
  course ad is active. Once admin enables an ad, the watch-required gate returns. Paid
  approval logic unchanged.
- "Do'st qo'sh" (friendAdd) button was REMOVED from the rating profile: there was no
  friend-relationship backend, so it only faked "request sent". Rating profile now shows
  Challenge + direct-chat message, both of which DO reach the other user.
- Real Telegram WebView smoke-test needed: subscribe stays in-app, no-ad free lesson
  completes, challenge notification arrives for opponent, direct chat opens for a ranked
  user with/without username.

### 2026-06-28 — Course free preview gate + ad-supported Premium lesson path

Changed:
- Course v3 free access is now lesson-number based, not level based: every HSK level
  allows lessons 1-3 as free preview; lesson 4+ requires Premium unless the user is
  paid or completes the ad-supported flow for that lesson.
- `FREE_COURSE_LESSONS_PER_LEVEL = 3` lives in `course_miniapp_access_service.py`
  and is used by both `/api/v3/map` and `/api/v3/lesson/complete`.
- Added `course_ad_creatives` and `course_ad_views` tables. Admins can upload and
  enable/disable course ad media from the admin Mini App; free users may unlock a
  next premium lesson after watching required start/middle/end placements for 6-7s.
- Premium users keep full course access and do not need course ads.

Why:
- HSK1 users are the largest segment, so making all HSK1 free blocks monetization.
  The preview should show value without opening the full paid course.

Files touched:
- `app/services/course_miniapp_access_service.py`
- `app/main.py`
- `app/services/course_ad_service.py`
- `app/db/models/course_ad.py`
- `app/static/course-v3.html`
- `app/static/admin-control.html`
- `alembic/versions/0056_course_ad_supported_lessons.py`

Risk / follow-up:
- Run the Alembic migration before using admin ad uploads in production.
- Telegram Mini App ad policy should be checked before connecting external ad networks;
  the current implementation supports in-house/admin-uploaded media first.

### 2026-06-28 — Free-tier monetization limits

Changed:
- New users default to 5 free QA text answers per day (`User.question_limit = 5`).
- Migration `0055_free_tier_monetization_policy` updates existing non-paid trial/free
  users that still had the old 10-question default.
- Free pronunciation assessment is capped at 3 STT attempts per day before calling AI.
- Referral active-friend threshold changed from 10 to 5.
- Subscription analytics labels now include `v3_ad`, `v3_qa_limit`,
  `v3_voice_trial_used`, and `v3_pronunciation_limit`.

Why:
- Static course/language learning surfaces can stay generous, but real-cost AI paths
  need tighter metering so free users do not create unlimited token/STT cost.

Files touched:
- `app/db/models/user.py`
- `app/services/voice_practice_service.py`
- `app/services/referral_service.py`
- `app/services/subscription_entry_analytics_service.py`
- `app/bot/utils/i18n.py`
- `app/static/course_v3_pronunciation.html`
- `alembic/versions/0055_free_tier_monetization_policy.py`

Risk / follow-up:
- Existing paid-user AI budget logic is unchanged.
- After deploy, smoke-test QA daily limit, pronunciation limit, referral milestone,
  and subscription entry analytics.

### 2026-06-28 — Admin Mini App real action center

Changed:
- Admin Mini App now opens internal management panels instead of sending admin section bounce messages to Telegram chat.
- Added admin Mini App APIs for management payload, user search/detail, payment approve/reject, manual access, user delete, subscription prices, payment details, required channels, help links, portfolio transactions, text broadcast, text-first ad/release/discount campaign creation, partner actions, and audio listing.
- Payment approval from Mini App follows the same core flow as Telegram admin approval: marks payment approved, activates subscription, records analytics/portfolio/partner commission, and notifies the user.

Why:
- Admin work should be doable inside the Mini App while keeping old Telegram chat admin sections available as fallback.

Files touched:
- `app/main.py`
- `app/services/admin_miniapp_service.py`
- `app/static/admin-control.html`

Risk:
- Payment/access/user delete/broadcast/campaign actions are real admin mutations; they require Telegram WebApp admin auth and should be smoke-tested inside Telegram after deploy.
- Alipay/WeChat custom QR upload and audio upload still depend on Telegram `file_id` chat flows; Mini App can manage prices and list audio but not replace those file_id upload flows yet.

Follow-up:
- Browser localhost smoke was blocked by environment localhost/usage limits; Python compile, JS syntax check, focused pytest, and dummy-token import passed.

### 2026-06-28 — Legacy Course Mini App URLs now route to Course v3

Changed:
- Bot Mini App URL helpers no longer point to removed V2/static pages (`study.html`, `duo-lesson.html`, `stroke-order.html`, old `hsk*.html` base fallback).
- Course study/quiz/training links now open `course-v3.html`; legacy tabs such as `training`, `quiz`, `words`, `grammar`, and `tests` map to Course v3 `tab=mashq`.
- Stroke/vocab links now open `hsk-lugat.html` with `from=course`.
- `course-v3.html?lesson=N` opens the matching lesson sheet after boot, so bot deep links still land on the intended lesson.
- Default `MINI_APP_BASE_URL` in config/example is now the Course v3 page.

Why:
- The old V2 files were removed, but bot helpers/tests/config still referenced them. That created broken Mini App buttons and failing smoke coverage.

Files touched:
- `app/bot/utils/course_miniapp.py`, `app/static/course-v3.html`, `app/static/hsk-lugat.html`
- `app/config.py`, `.env.example`
- `tests/test_course_miniapp_foundation.py`, `tests/e2e/test_miniapp_smoke.py`

Risk:
- Old separate V2 quiz/homework pages are not restored; legacy entry points intentionally land inside Course v3.
- Real Telegram WebView smoke-test is still needed after deploy for initData/payment/microphone flows.

### 2026-06-28 — Course ad-supported Premium lesson path

Changed:
- Added Course Mini App ad tables: `course_ad_creatives` for admin-uploaded video creatives and `course_ad_views` for per-user lesson placement watch tracking.
- Added migration `0056_course_ad_supported_lessons.py`.
- Admin Mini App Settings can upload/toggle Course ad videos stored under `app/static/uploads/course_ads`.
- Course v3 locked Premium lessons now offer two paths when the lesson is the user's next lesson: subscribe to Premium or continue with ads.
- Ad-supported premium lessons require 6-7s video ads at lesson start, middle, and end. Server completion for unpaid users validates all three placements before allowing the Premium lesson to complete.
- Paid users remain ad-free. Lessons 1-3 free preview stays clean; ads are only for the ad-supported premium path.

Why:
- Most users are in HSK1, so hard-blocking lesson 4+ leaves money on the table. This creates a second monetization route for non-paying users without changing paid subscription approval logic.

Files touched:
- `app/db/models/course_ad.py`, `app/services/course_ad_service.py`, `app/main.py`
- `app/static/course-v3.html`, `app/static/admin-control.html`
- `alembic/versions/0056_course_ad_supported_lessons.py`

Risk:
- Deploy must run migration `0056_course_ad_supported_lessons`.
- Real Telegram smoke-test should verify admin video upload, free user lesson 4 ad flow start/middle/end, server completion after ads, no completion without ads, and paid user sees no ads.
- If no active Course ad exists, the ad path falls back to the Premium sheet.

Follow-up:
- Browser Playwright smoke-test was blocked by environment usage limits; Python compile, JS syntax extraction, and focused pytest passed.

### 2026-06-28 — HSK2-HSK4 memorize data coverage

Changed:
- `course_v3_data/memo.js` now keeps the hand-written HSK1 memo entries and adds a compact HSK2-HSK4 offline generator (`EXTRA_MEMO_ITEMS` + `makeExtraMemo`) built from existing `hsk-data.js` WORDS.
- Generated entries cover every Han character appearing in HSK2, HSK3, and HSK4 word data, so `course_v3_memorize.html?char=...` no longer falls back to HSK1-only decks for higher levels.
- `hsk-lugat.html` and `course_v3_memorize.html` bumped the `memo.js` cache query to `v=20260628`.

Why:
- The HSK character dictionary already exposed HSK2-HSK4 words, but the fast memorize module only had 87 HSK1 character entries.

Files touched:
- `app/static/course_v3_data/memo.js`
- `app/static/course_v3_memorize.html`
- `app/static/hsk-lugat.html`

Risk:
- Data/frontend-only; no payment, subscription, lesson completion, quiz, homework, or backend result logic changed.
- HSK2-HSK4 generated entries are honest word-based hooks, not historical etymology explanations.

Follow-up:
- Browser Playwright smoke test was blocked by local Chromium sandbox/permission limits; JS runtime validation and static data pytest passed.

### 2026-06-28 — Free-tier monetization limits and Course v3 3-lesson preview gate

Changed:
- Free QA text default is 5 questions/day (`User.question_limit`, new-user repo path, and migration/default aligned).
- Free pronunciation scoring is capped at 3 STT attempts/day before OpenAI is called; paid users still use the AI budget gate.
- Referral trial unlock threshold is 5 active friends; per-active-friend +5 bonus question behavior stays.
- Course v3 free course access is no longer level-based. Every HSK level gives lessons 1-3 as free preview and marks lesson 4+ as Premium in both static maps and server access policy.
- Course v3 pronunciation-limit paywall source is tracked as `v3_pronunciation_limit`; new analytics labels include v3 ad/QA/voice/pronunciation sources.

Why:
- Most users are expected to be in HSK1, so making all HSK1 free would block monetization. The new policy gives enough static course preview for learning habit while keeping deeper HSK1+ content behind Premium.

Files touched:
- `app/db/models/user.py`, `app/services/voice_practice_service.py`, `app/services/referral_service.py`, `app/services/course_miniapp_access_service.py`, `app/main.py`
- `app/static/course-v3.html`, `app/static/course_v3_pronunciation.html`, `app/static/course_v3_data/hsk1.json`..`hsk4.json`
- `alembic/versions/0055_free_tier_monetization_policy.py`

Risk:
- Access behavior changed for unpaid users: HSK1 lesson 4+ now requires Premium. Payment approval and paid-user AI budget logic were not changed.
- Deploy should run migration `0055_free_tier_monetization_policy`; Telegram smoke-test should verify free HSK1 lesson 3 completes, HSK1 lesson 4 opens Premium sheet, and paid user can open 4+.

### 2026-06-27 — Course v3 paywall to'siq oynasi tiriltirildi (locked dars → Premium sheet)

Changed:
- Avval Course v3'da qulflangan darsni (HSK 4+, `locked_premium`) bosganda foydalanuvchi
  hech qanday tushuntiruvchi oyna ko'rmay, to'g'ridan-to'g'ri `subscription.html`'ga
  uchib o'tardi. `paywallHtml()` funksiyasi va `#paywall` bottom-sheet HTML'i kodda
  bor edi, lekin hech qayerdan chaqirilmasdi (dead code).
- `App.openPaywall(ctx)` endi `#paywall-body`'ga `paywallHtml(ctx)` quyadi va sheet'ni
  ochadi (会 logo, "Bu dars Premium'da" sarlavha, b1/b2/b3 afzalliklar, narx, "Obuna
  bo'lish" + "Keyinroq" tugmalari). Avvalgidek darrov `goPay` chaqirmaydi.
- Yangi global `PAY_SOURCE` qo'shildi: `openPaywall` kontekstdan manbani saqlaydi
  (`v3_locked_lesson` / `v3_paywall` / `v3_profile`), `goPay` argument berilmasa
  `PAY_SOURCE`'dan oladi. Shu bois sheet'dagi "Obuna bo'lish" tugmasi to'g'ri
  `source=` bilan `/subscription.html?...&mode=subscription` ochadi.
- 3 ta trigger o'zgarmadi: qulflangan dars tap, skip-test, va server
  `free_feature_limit_reached` xatosi — barchasi endi avval sheet'ni ko'rsatadi.

Why:
- Foydalanuvchi qulfni bosganda nima uchun to'lov sahifasi ochilganini bilmasdi;
  endi avval qisqa Premium afzalliklari/narx oynasi chiqib, tushunib obunaga o'tadi.
  Mavjud dead code qayta ishlatildi.

Files touched:
- `app/static/course-v3.html`

Risk:
- Faqat frontend (paywall UX); to'lov/obuna/ruxsat backend mantig'i o'zgarmadi.
  Lock qoidasi (bepul HSK1-3, 4+ Premium) va `subscription.html` o'zi tegilmadi.
- Narx sheet'da faqat server narx datasi yuklangach ko'rinadi (`_priceStr` guard
  bilan); statik preview'da backend yo'qligi sabab narx ko'rinmaydi, real Telegram'da
  chiqadi.
- Real Telegram WebView smoke-test kerak: HSK 4-darsni bosib sheet → "Obuna bo'lish"
  → subscription oqimini tekshirish.

### 2026-06-27 — Motivatsion eslatmalar (reyting / kunlik maqsad / streak) + admin tahriri

Changed:
- Yangi `MotivationReminderService` 3 ta push eslatma yuboradi, har biri real Mini App
  ma'lumotidan: (1) reytingda kimdir ortda qoldirsa, (2) kun oxirida kunlik maqsad
  bajarilmasa, (3) streak uzilish xavfi bo'lsa. Har biri foydalanuvchiga mahalliy
  kun bo'yicha max 1 marta; goal/streak faqat 20:00–21:30 oynasida va bugun
  shug'ullanmagan bo'lsa. `_background_scheduler` (har 60s) ichiga ulandi.
- Reyting o'tib ketishini aniqlash uchun `course_miniapp_profiles` ga `last_known_rank`
  va 3 ta dedupe sanasi (`motivation_overtaken_date/goal_date/streak_date`) qo'shildi.
- Eslatma matnlari endi bazada (`notification_templates`) — admin Mini App'dan UZ/RU/TJ
  alohida tahrirlanadi, yoq/o'chir qilinadi, bitta umumiy surat/video biriktiriladi.
  Matn bo'sh bo'lsa koddagi standart matnga (DEFAULT_TEXTS) qaytadi, shuning uchun
  noto'g'ri sozlash eslatmani jimitib qo'ymaydi.
- Media admin Mini App'dan to'g'ridan-to'g'ri yuklanadi (`/api/admin-miniapp/notifications/media`),
  serverda `app/static/uploads/notifications/` ga saqlanadi, scheduler `FSInputFile`
  bilan yuboradi, preview `/uploads/notifications/{file}` orqali ko'rsatiladi.
  Caption (media bilan) max 1024, mediasiz matn max 4096 belgi.
- Admin Mini App "Sozlash" tabiga "🔔 Motivatsion eslatmalar" bo'limi qo'shildi
  (yangi tab/navigatsiya qo'shilmadi, 5 tab o'zgarmadi).

Why:
- Avval streak/liga/reyting faqat Mini App UI'da bor edi; foydalanuvchi botni ochmasa
  hech qanday motivatsion push kelmasdi (eski `CourseReminderService` faqat oddiy
  kunlik/haftalik eslatma yuborardi).

Files touched:
- `app/db/models/notification_template.py` (new)
- `app/db/models/course_miniapp_profile.py`
- `app/services/notification_template_service.py` (new)
- `app/services/motivation_reminder_service.py` (new)
- `app/main.py` (endpoints + scheduler + media route)
- `app/db/session.py` (bootstrap columns)
- `app/static/admin-control.html`
- `alembic/versions/0054_add_notification_motivation.py` (new head)

Risk:
- Migration `0054_add_notification_motivation` yangi head. `notification_templates`
  jadvali `create_all` bilan startda yaratiladi; profil ustunlari `_BOOTSTRAP_COLUMNS`
  orqali eski Railway DB'ga ham qo'shiladi.
- To'lov/obuna/ruxsat mantig'i o'zgarmadi.
- Eslatmalar `User.status == "active"` va Mini App profili bor foydalanuvchilarga
  yuboriladi; per-user opt-out yo'q (faqat admin template'ni o'chira oladi).
- Deploydan keyin real Telegram'da smoke-test kerak: admin Mini App'da matn tahriri,
  media yuklash/o'chirish, va kechqurun goal/streak push'i.

### 2026-06-27 — HSK lug'at kartasiga strukturali "eslab qolish" bo'limlari

Changed:
- `hsk-lugat.html` belgi detali endi `memo.js` (`window.MEMO_DATA`) dan
  data-driven 5 bo'lim ko'rsatadi: Tarkibi (breakdown), Ma'no/tovush belgisi
  (radikal rollari + signal), Eslab qolish (hooks), O'xshash iyerogliflar
  (confusables), Misol (words). Har bo'lim faqat shu belgi uchun data bo'lsa
  chiqadi, bo'lmasa toza yashiriladi (`.memo-wrap:empty{display:none}`).
- Stroke-order animatsiya va 1-3 bo'lim (hanzi/pinyin/ma'no), mavjud
  misol/grammatika/mashqlar bloklari tegilmadi.
- `etymology_honest:false` belgilarda `MEMO_UI.disclaimer` (3 til) ko'rsatiladi.
- `main.py` ga `GET /course_v3_data/memo.js` route qo'shildi (avval `.json`-only
  route uni 404 qilardi).
- `main.py` `_COURSE_V3_PAGES` ga `"memorize"` qo'shildi → lug'atdagi ⚡ "Tez
  eslab qolish" tugmasi (`/course_v3_memorize.html?char=…`) endi 404 emas, real
  interaktiv yodlash moduli ochiladi.
- Lug'at ⚡/mashq tugmalari endi `from=lugat` (+ `theme`/`level`) uzatadi
  (`goPractice`), va `course_v3_memorize.html` `goBack()` `from=lugat` bo'lsa
  `/hsk-lugat.html?char=FOCUS` ga qaytaradi → mashq tugagach foydalanuvchi
  boshlagan belgisiga (lug'atga) qaytadi, kurs mashq tabiga emas.

Why:
- Lug'at kartasi faqat hanzi/pinyin/ma'no ko'rsatardi; mavjud offline yozilgan
  memo data (HSK1, 87 belgi) shu kartada qayta ishlatildi. Runtime AI yo'q.

Files touched:
- `app/static/hsk-lugat.html`
- `app/main.py`

Risk:
- Faqat frontend + 1 statik route; lesson/quiz/homework/initData/backend/payment
  tegilmadi.
- Memo data hozir faqat HSK1 (87 belgi) uchun bor; qolgan belgilarda 4-8 bo'limlar
  yashirin (lug'at kartasida) va ⚡ modulida deck shu pul ichidan quriladi.

### 2026-06-27 — Legacy V2 Mini App removed, bot opens Course v3, subscription paywall rewritten

Changed:
- Removed the legacy V2 course Mini App surface and its assets: `study.html`,
  `study-v2.js`, `study-v2.css`, `course-miniapp-v2.js`, `voice-practice.html`,
  `stroke-order.html`, `hsk1.html`..`hsk4.html`, `subscription-preview.html`.
  The active course experience is now Course v3 (`course-v3.html` + `course_v3_*`).
- Bot Course entry points now open Course v3: `send_course_miniapp_entry()` and
  `run_course_entry_flow()` use the new `course_v3_miniapp_keyboard(lang)` /
  `course_v3_miniapp_url()` (opens `course-v3.html`) instead of `study.html`.
- `subscription.html` rebuilt as a compact Course v3-styled paywall (~1422 -> ~341
  lines): plan picker (1_month / 10_days), payment method, discount block.
- Subscription entry analytics gained Course v3 sources: `v3_paywall`,
  `v3_locked_lesson`, `v3_level_up` (and `v3_profile` relabeled). Admin control
  Mini App (`admin-control.html`) now shows an "Obuna manbalari" table via the
  existing `/api/admin-miniapp/sub-entry-stats` endpoint.
- `course_v3_voice.html` AI Voice character moods/visuals updated (UI only).

Why:
- Course fully moved to V3; the old V2 Mini App and its duplicate paywall/voice
  pages were dead weight and confused the entry flow.

Files touched:
- `app/bot/handlers/course.py`, `app/bot/keyboards/course_miniapp.py`,
  `app/bot/utils/course_miniapp.py`
- `app/services/subscription_entry_analytics_service.py`, `app/static/admin-control.html`
- `app/static/subscription.html`, `app/static/course_v3_voice.html`
- Deleted: `app/static/{study.html,study-v2.js,study-v2.css,course-miniapp-v2.js,voice-practice.html,stroke-order.html,hsk1.html,hsk2.html,hsk3.html,hsk4.html,subscription-preview.html}`

Risk:
- No payment/subscription/access backend rules changed; only the entry keyboard
  target and the paywall frontend.
- Bug fixed during review: `subscription.html` plan render had a stray `)` that
  broke the entire inline script (paywall would not render); corrected so the
  popular-plan `pop` class concatenates cleanly.
- Legacy bot code still references the deleted `study.html` (course challenge
  notifications, `course_study_miniapp_keyboard`) and `stroke-order.html`
  (`course_vocab_stroke_order_keyboard`), but these paths are only reachable from
  the removed V2 frontend / old in-chat course steps, so there is no live 404 in
  the V3 flow. Follow-up: repoint or remove those legacy references.
- `hsk-lugat.html` `goBackToStudy()` has a dead `study.html` branch; the dictionary
  is only opened from `course-v3.html` with `?theme=light`, so the live path always
  returns to `course-v3.html`.

### 2026-06-27 — Course v3 real pronunciation (microphone) scoring

Changed:
- Replaced the mocked random-score pronunciation checks with real microphone + server speech-to-text scoring in all course v3 sections that need a mic.
- Added `VoicePracticeService.score_pronunciation()` and `POST /api/voice-practice/pronounce`: verifies Telegram initData, gates paid users through the existing AI usage budget, transcribes audio via `transcribe_voice_with_usage`, and scores by CJK character match against the target word (`score>=60` passes). Usage recorded with source `voice_practice_pronounce`.
- `course_v3_pronunciation.html` (standalone Talaffuz mashqi) and the in-lesson `pronunciation` card in `course-v3.html` now record with `MediaRecorder`/`getUserMedia` and call the new endpoint instead of `Math.random()`. UZ/RU/TJ status/error strings added.
- AI Voice (`course_v3_voice.html`) already used a real mic and was left unchanged.

Why:
- The two pronunciation exercises only had the mic UI; they never opened the microphone and returned a fake random score.

Files touched:
- `app/services/voice_practice_service.py`
- `app/main.py`
- `app/static/course_v3_pronunciation.html`
- `app/static/course-v3.html`

Risk:
- No payment/subscription/access rules changed. Pronunciation scoring shares the existing AI budget gate for paid users.
- Scoring is character-match from STT, not per-syllable tone analysis. In-lesson failed attempts do NOT cost a heart and always allow continue (no soft-lock).
- Needs real Telegram WebView smoke test (mic permission + initData + OpenAI key) after deploy; browser preview returns 401 without initData.

### 2026-06-27 — Course v3 HSK exams functional (Test markazi)

Changed:
- Course v3 Test markazi (`course_v3_test.html`) HSK 1-4 imtihonlari endi real
  ishlaydi. Avval kartochkalar har doim "Material tayyorlanmoqda" bo'sh holatini
  ko'rsatardi (savol fayllari yo'q edi).
- Added per-level exam material files `app/static/course_v3_data/exams/hsk{1..4}.json`
  (schema_version 1; `sections` → listening/reading/writing; question types
  `audio_truefalse`, `audio_choice`, `text_choice`; multilingual uz/ru/tj).
- `course_v3_test.html` now loads that JSON and runs a real exam: section-grouped
  questions, TTS playback (`speak()`, `lang=zh-CN`) for listening, client-side
  grading, and a per-section result screen (reuses placement `.pl`/`.opt`/`.res` UI).
- Added route `/course_v3_data/exams/{filename}` in `app/main.py` (filename
  whitelisted to `hsk[1-4].json`).
- Hub exam cards now show real question/duration counts (14/12/12/12) instead of
  placeholder 40/60/80/100.

Why:
- HSK exam cards were dead (always empty state); the interface existed but the
  question material/runner did not.

Files touched:
- `app/static/course_v3_data/exams/hsk1.json` .. `hsk4.json` (new)
- `app/static/course_v3_test.html`
- `app/main.py`

Risk:
- Frontend + static data only; payment/subscription/progress logic unchanged.
- Exam result is client-side and NOT persisted to the server (like placement);
  add an endpoint if admin stats need it.
- Listening uses browser TTS; if device has no zh-CN voice, audio may be silent
  but option text still shows.
- Current scope is a simplified practice exam (~12-14 questions/level), not the
  full 40-100 question real HSK.

### 2026-06-26 — Course v3 static lesson data files

Changed:
- Added schema v2 static lesson JSON files under `app/static/course_v3_data/{hsk1,hsk2,hsk3,hsk4}/`.
- Coverage now includes HSK1 lessons 1-15, HSK2 lessons 1-15, HSK3 lessons 1-20, and HSK4 lessons 1-20.
- Each lesson includes multilingual UZ/RU/TJ subtitles, active words, grammar, dialogue, intro/practice/dialog sections, and frontend-supported card types.

Why:
- `course-v3.html` loads lesson flow content from `/course_v3_data/{level}/lesson_XX.json` and needs complete standalone lesson files for HSK1-HSK4.

Files touched:
- `app/static/course_v3_data/hsk1/lesson_01.json` through `lesson_15.json`
- `app/static/course_v3_data/hsk2/lesson_01.json` through `lesson_15.json`
- `app/static/course_v3_data/hsk3/lesson_01.json` through `lesson_20.json`
- `app/static/course_v3_data/hsk4/lesson_01.json` through `lesson_20.json`

Risk:
- Data-only change; no subscription, payment, backend result, or progress logic changed.

Follow-up:
- After deploy, test HSK level switching once v3 maps expose HSK2-HSK4 paths in the UI.

### 2026-06-26 — Course v3 access and progress hardening

Changed:
- Course v3 map files now expose real HSK1-HSK4 lesson counts with zeroed preview progress, not fake/demo XP.
- `/api/v3/map` keeps unpaid users limited to lessons 1-3 and marks lesson 4+ as premium-locked even when lesson progression would otherwise make the next node current.
- Added `/api/v3/lesson/complete` so Telegram users complete v3 lessons through the backend, with initData auth, sequential progress checks, gamification award, and the same free lesson limit.
- `course-v3.html` now waits for server completion before locally unlocking the next lesson for authenticated Telegram users.
- Fixed static lesson fallback ordering in `CourseMiniAppLessonFlowService` so DB/test payload content is not overwritten by static fallback files.
- Course v3 now respects `?level=` and `localStorage.hsk_v3_level`; onboarding passes the selected level into the main course URL so HSK4 opens HSK4 map and lesson JSON.
- Added Course v3 level picker from the HSK pill.
- Course v3 invite share now uses `/api/v3/invite`, which reuses `ReferralService` and the same referral link format as `/invite`; frontend opens Telegram share with ready text instead of making copy the main flow.
- Lesson intro cards were reshaped into a more Duolingo-like flow: word flash, listening pick, meaning pick, hanzi pick, then grammar.

Why:
- Prevent unpaid users from bypassing the Course v3 paywall by completing lessons locally.
- Remove demo progress data from the user-facing course map.
- Make v3 lesson progress server-authoritative for real Telegram users.
- Preserve selected HSK level across onboarding, reload, and lesson fetches.
- Avoid broken hardcoded referral links and reduce invite friction.

Files touched:
- `app/main.py`
- `app/static/course-v3.html`
- `app/static/course_v3_onboarding.html`
- `app/static/course_v3_data/{hsk1,hsk2,hsk3,hsk4}.json`
- `app/services/course_miniapp_lesson_flow_service.py`
- `tests/test_course_v3_static_data.py`

Risk:
- The v3 completion endpoint assumes course lessons are seeded in the database with level and order matching the static maps.
- Voice/rating/pronunciation demo text is outside this patch and still needs a separate real-backend audit.
- `/api/v3/invite` requires valid Telegram initData; local browser preview falls back to a plain bot link without referral attribution.

### 2026-06-26 — Mode selection required-channel edit resume

Changed:
- Start mode selection forced-channel gate now edits the existing mode message into the channel list instead of sending a separate block.
- After channel subscription is confirmed, the same message is edited into the selected path: Course shows the Course Mini App entry button; QA shows level selection first.
- QA level selection from this path marks the user as QA mode, then sends the normal first-message prompt with the main reply keyboard.

Why:
- New users should not get duplicate stacked bot blocks during mode selection and required-channel verification.

Files touched:
- `app/bot/handlers/course.py`
- `app/bot/handlers/required_channel.py`
- `app/bot/handlers/start.py`
- `app/bot/fsm/onboarding.py`
- `tests/test_course_miniapp_onboarding.py`

Risk:
- Required-channel/payment rules were not changed; this only changes message edit/resume behavior in the mode-selection path.

### 2026-06-25 — Subscription entry source analytics

Changed:
- Added `subscription_entry_events` to track which source brought a user into the Subscription Mini App.
- `/api/subscription-miniapp/overview` records the source from the Mini App URL payload only after the user actually opens the subscription Mini App.
- Admin `Statistika` now shows `OBUNA MANBALARI` with all-time and 7-day unique users/open counts by source.

Why:
- Admin needs to see which bot/Mini App branches drive the most interest toward subscription.

Files touched:
- `app/db/models/subscription_entry_event.py`
- `alembic/versions/0053_add_subscription_entry_events.py`
- `app/services/subscription_entry_analytics_service.py`
- `app/main.py`
- `app/bot/handlers/admin.py`

Risk:
- Requires Alembic migration `0053_add_subscription_entry_events`; payment and access rules were not changed.

### 2026-06-25 — Admin stats legacy blocks removed

Changed:
- Admin `Statistika` panel no longer shows legacy `DAILY 3-MIN`, `COURSE PILOT 1-3`, `TRIAL FUNNEL`, `TRIAL -> PAYMENT`, old `FUNNEL unique`, `O'QISH REJIMI`, or `course_progress` reminder counts.
- Current course analytics are limited to `course_miniapp_events` based `KURS` and `KURS MINI APP` sections plus general real user/payment/referral stats.

Why:
- Legacy course/trial/daily/pilot tables mixed old-version users with current Mini App activity and made admin stats misleading.

Files touched:
- `app/bot/handlers/admin.py`

Risk:
- Historical legacy funnel data is still stored in the database and other services, but it is intentionally hidden from the main admin stats report.

### 2026-06-25 — Admin course statistics Mini App source fix and Uzbek label cleanup

Changed:
- Admin `Statistika` panel keeps the detailed report, but the `KURS` block no longer counts legacy `course_progress` users as current course signups.
- `KURS` block now uses `course_miniapp_events` distinct `telegram_id` counts for Mini App opened, lesson started, and lesson completed users.
- Remaining visible admin/user labels found in bot handlers, admin keyboards, release feedback, help settings, Mini App pilot skeleton, funnel analytics, rich quiz message, and Voice Practice errors were aligned to Uzbek/current wording.

Why:
- Course stats were showing old-version course users together with users who moved to the Mini App; the current report must reflect post-Mini App activity.

Files touched:
- `app/services/admin_stats_service.py`
- `app/bot/handlers/admin.py`
- `app/bot/handlers/commands.py`
- `app/bot/keyboards/admin_broadcast.py`
- `app/bot/keyboards/release_feedback.py`
- `app/services/conversion_funnel_service.py`
- `app/services/course_miniapp_admin_analytics_service.py`
- `app/services/course_miniapp_lesson_service.py`
- `app/services/help_settings_service.py`
- `app/services/rich_message_service.py`
- `app/services/voice_practice_service.py`
- `tests/test_admin_stats_service.py`

Risk:
- Users who used legacy course only and never opened the Mini App are intentionally excluded from the `KURS` Mini App counts.

### 2026-06-26 — Admin control Mini App

Changed:
- Added an admin-only Telegram Mini App at `/admin-control.html`.
- Added `/api/admin-miniapp/overview` for read-only admin dashboard data and `/api/admin-miniapp/open-section` to send existing Telegram admin section buttons back to the admin chat.
- `/admin` and admin `Statistika` now include a WebApp button for the admin Mini App.

Why:
- Admin needs a Mac/iPhone friendly control center without replacing existing Telegram admin FSM flows for payments, QR upload, channels, ads, discounts, and access actions.

Files touched:
- `app/static/admin-control.html`
- `app/services/admin_miniapp_service.py`
- `app/main.py`
- `app/bot/handlers/admin.py`
- `app/bot/utils/course_miniapp.py`

Risk:
- Read-only dashboard data plus Telegram admin section shortcuts; no payment, subscription, access, or course write logic was changed.

### 2026-06-25 — Course Mini App static data split and HSK1 static lesson pilot

Changed:
- `study.html` no longer embeds the full HSK1-4 course data blob; it lazy-loads whitelisted `/course_data/{level}.json` files.
- `CourseMiniAppLessonFlowService` checks `app/static/course_content/{level}/lesson_XX.json` first and falls back to the existing generated/server payload when no static lesson exists.
- HSK1 lessons 1-3 now have static 6-section JSON pilots; HSK2-HSK4 still use the legacy backend flow.

Why:
- Keep Mini App UI files lightweight and separate render/navigation code from course material and lesson card content.

Files touched:
- `app/main.py`
- `app/static/study.html`
- `app/services/course_miniapp_lesson_flow_service.py`
- `app/static/course_data/*.json`
- `app/static/course_content/hsk1/lesson_01.json` through `lesson_03.json`

Risk:
- Legacy generated lesson/card fallback remains active for non-static lessons.
- Graphify AST update was attempted but refused to overwrite because the rebuilt graph had fewer nodes than the existing graph.

### 2026-06-25 — Mini App HSK character dictionary data split

Changed:
- `Training -> Ierogliflar` dictionary flow now has the lightweight `hsk-lugat.html` shell backed by separate `/hsk-data.js`.
- HSK dictionary data includes HSK1-4 words/strokes, 157 HSK4 example sentences from the provided generator, and 100 HSK4 grammar explanations sourced from `hsk4.html`.
- The dictionary supports `?level=` filtering for HSK1/2/3/HSK4 上/下 and `?lang=` for UZ/RU/TJ, with a visible language switch and return to Training.

Why:
- The previous route existed but the static dictionary file/data needed to be connected and HSK4 entries needed examples plus understandable grammar context.

Files touched:
- `app/main.py`
- `app/static/hsk-lugat.html`
- `app/static/hsk-data.js`

Risk:
- Payment/subscription/access rules were not changed.
- HSK4 examples are available for 157 entries; remaining HSK4 entries still show word meaning and may show grammar only when matching an HSK4 grammar rule.

Follow-up:
- After deploy, smoke-test Telegram Mini App `Training -> Ierogliflar` in UZ/RU/TJ and check HSK4 上/下 filtering.

### 2026-06-25 — Mini App rating profile Telegram chat

Changed:
- Mini App leaderboard API now includes safe `username` and `telegram_id` fields for ranked users, so the rating profile sheet can open the user's existing Telegram chat instead of creating an in-app chat.
- Rating UI now shows paid users with a custom premium mark before the nickname and uses CSS-drawn medals for the top ranking positions instead of emoji badges.
- Leaderboard is no longer capped to 25 by default; `CourseGamificationService.leaderboard()` returns all same-league users unless an explicit limit is passed, and `league_size` reflects the real row count.
- Leaderboard rows also include safe course progress summary fields (`course_level`, `completed_lessons`, `total_xp`) for the rating profile sheet.
- Telegram Mini App viewport height is synced from `Telegram.WebApp.viewportHeight/stableHeight` through `study.html` into `study-v2.js`, so the fixed bottom nav stays inside the visible Mini App viewport.

Why:
- User-to-user contact from rating profiles should stay inside Telegram chat UX, and subscription status should be visible without using plain emoji/checkmark text.

Files touched:
- `app/services/course_gamification_service.py`
- `app/static/study-v2.js`
- `app/static/study-v2.css`

Risk:
- No subscription/payment/access rules changed.
- Direct Telegram chat opens only when Telegram username or user deep-link id is available.

Follow-up:
- After deploy, test a real Telegram Mini App rating profile for a user with username and one without username.
- Also test on Telegram iOS after opening the Mini App fresh: bottom nav should be visible without scrolling.

### 2026-06-25 — Mini App user challenge flow

Changed:
- Added `course_challenges` for Mini App user-to-user belashuv/challenge state. A challenge stores a frozen JSON question payload so both users get identical questions even if they complete at different times.
- Challenge lifecycle: `pending` invite, opponent `accept`/`reject`, each user completes once, then winner is calculated by score and tie-broken by faster duration.
- Mini App endpoints: list/create/respond/start/submit under `/api/miniapp/challenges`.
- Bot sends opponent an inline accept/reject notification and also exposes the same incoming challenges in the Mini App profile notification block.
- Rating profile can start a challenge from a ranked user; profile notifications show pending/active/completed challenges.

Risk:
- `Base.metadata.create_all()` creates the new table on startup, but existing DBs should still be tested after deploy for table creation.
- Challenge submit is one-shot per user; there is no rematch button yet.

Follow-up:
- Test with two real Telegram users: start from rating profile, accept from bot and Mini App profile, complete both sides, verify result/winner.

### 2026-06-25 — Mini App lesson material journey

Changed:
- Mini App lesson card generation now builds deterministic section-purpose material from the selected section `active_words` instead of accepting unscoped payload quiz fallbacks.
- Generated cards use indexed source-backed activities such as `activity:meaning:1`, `activity:listening:2`, `activity:gap:1`, so review/listening/usage sections do not all collapse into the same generic question.
- Listening cards keep `audio_text` only for playback; the frontend no longer displays the answer text inside the listening prompt and shows an audio waveform-style button instead.
- Generic fill-blank questions such as “Men bugun ____ so'zini o'rgandim” were removed from Mini App quiz generation; gap-fill cards now require a real lesson/example sentence containing the target word.
- Completing the final book lesson of a level in the Mini App now advances course progress to the next level and returns a server `next_book_lesson` ref plus concrete localized praise text.

Why:
- The previous generated cards could feel random/quiz-like, could produce fake blank prompts where every option fit, and the listening UI could reveal the heard word visually, which made the lesson flow poor despite correct section routing.

Files touched:
- `app/services/course_miniapp_lesson_flow_service.py`
- `app/static/study-v2.js`
- `app/static/study-v2.css`
- `app/static/study.html`
- `tests/test_course_miniapp_lesson_flow.py`
- `tests/test_course_miniapp_lesson_service.py`

Risk:
- Payment/subscription/QA/voice access logic was not changed.
- Graphify code graph was updated after the Mini App lesson logic changes.

Follow-up:
- After deploy, test a real Telegram Mini App lesson `1.3 Tinglash` and confirm the listening card plays audio while hiding the answer text.

### 2026-06-24 — Mini App server section plan source-of-truth

Changed:
- Mini App course path now loads a server-backed `course-section-plan` instead of building visible path nodes from static `COURSE_DATA.VOCAB`.
- Section plan and lesson flow share `CourseMiniAppLessonFlowService._section_plan()`, so path nodes and lesson cards use the same `section_key`, `section_no`, `active_words`, lock/completion status, and next section refs.
- Every book lesson now has six fixed learning-stage sections regardless of vocabulary count: intro, reinforcement, listening/pronunciation CTA, usage, short dialog, and review. Short lessons reuse the same lesson words across stages instead of jumping from `1.2` to `2.1`.

Why:
- Path node labels and opened lesson content previously came from different runtime sources, which could show one section in the path but open different material in the lesson.

Files touched:
- `app/main.py`
- `app/services/course_miniapp_lesson_flow_service.py`
- `app/static/study.html`
- `app/static/study-v2.js`
- `tests/test_course_miniapp_lesson_flow.py`
- `tests/e2e/test_miniapp_smoke.py`

Risk:
- Payment/subscription/QA logic was not changed.
- Graphify update refused to overwrite because the rebuilt graph had fewer nodes than the existing graph; do not force update without checking graph inputs.

Follow-up:
- After deploy, verify a real Telegram Mini App user opens path node `1.2` and lesson header/cards show the same `section_key` and `active_words` from server logs.

### 2026-06-24 — Mini App locked lesson readiness jump

Changed:
- Locked/future course path nodes are no longer ignored in the Mini App; explicit node taps open a short readiness test built from lessons up to the selected lesson.
- After the test, users can continue from the selected section even with a low score, with a short warning that the chosen lesson may be difficult.
- Confirming the jump calls a server endpoint that moves `course_progress.current_lesson_id` to the selected book lesson and records the test result in Mini App analytics.

Why:
- Users who intentionally choose a later lesson need a guided override instead of a dead locked tap, while server progress must still become the source of truth before lesson content opens.

Files touched:
- `app/main.py`
- `app/services/course_miniapp_lesson_flow_service.py`
- `app/static/study.html`
- `app/static/study-v2.js`
- `tests/test_course_miniapp_lesson_flow.py`

Risk:
- Payment/subscription logic was not changed.
- The readiness test uses existing Mini App course quiz material; lesson content itself is still loaded from the server after confirmation.

Follow-up:
- After deploy, test a locked path node such as `1.4`: complete the readiness test, continue despite low score, and verify the opened section header/content match the selected node.

### 2026-06-24 — Mini App lesson section source-of-truth fix

Changed:
- Course lesson flow no longer falls back from an unknown requested `section_key` to section `1`; server now returns `course_section_not_found`.
- Lesson flow response includes server `active_words`; frontend logs `level`, `lesson_order`, `section_key`, `section_no`, `book_lesson_order`, and `active_words` at lesson start.
- Broken lesson-flow microphone and fake stroke-order cards were removed from generated flows; activity generation now validates card count, source words, broken types, and diversity.

Why:
- Path nodes could show one section while the opened lesson used another section's content because local frontend section guesses and server fallback hid section mismatches.

Files touched:
- `app/services/course_miniapp_lesson_flow_service.py`
- `app/static/study-v2.js`
- `tests/test_course_miniapp_lesson_flow.py`
- `tests/e2e/test_miniapp_smoke.py`

Risk:
- Payment/subscription/QA logic was not changed.
- Real stroke order remains available in character dictionary/stroke pages, not inside lesson flow.

Follow-up:
- After deploy, test Telegram WebView path node `1.2`, next `1.2 -> 1.3`, and verify console debug active words match the opened section.

### 2026-06-24 — Mini App tests and character dictionary cleanup

Changed:
- Test Center HSK 1-4 mock exams are visually grouped into one bordered HSK tests block.
- The Pinyin test entry was removed from Test Center; Training no longer shows Writing, Pinyin, or separate Speaking entries.
- Training → Characters now opens `/hsk-lugat.html`, a standalone HSK 1-4 character dictionary with stroke animation, back routing to `study.html?tab=training`, and UZ/RU/TJ meanings sourced from existing course data.

Why:
- The training/test menu needed to be simplified and the user-provided character dictionary needed to be connected to the Mini App flow.

Files touched:
- `app/static/study-v2.js`
- `app/static/study-v2.css`
- `app/static/hsk-lugat.html`
- `app/main.py`

Risk:
- Payment/subscription logic was not changed; the Characters dictionary entry still uses the existing `training_test` feature lock.

Follow-up:
- After deploy, smoke-test in Telegram WebView: Tests tab, Training → Characters dictionary, RU/TJ language switch, and back button to Training.

### 2026-06-24 — AI Voice dialog-count session flow

Changed:
- AI Voice paid call UX no longer auto-closes by a 25-second frontend timer.
- Voice sessions now use a 7-dialog backend limit, where one user voice message plus one bot answer counts as one dialog.
- Session start returns a localized Chinese opening message (`你好`/`嗨`) that the frontend speaks before the user starts.
- The final AI reply is instructed to make a natural excuse and say goodbye; the backend returns `session_should_end` so the frontend ends after playing that reply.
- Voice reply latency was reduced by shortening the transcription prompt, limiting recent chat history, lowering AI reply token budget, and recording audio in smaller lower-bitrate chunks.

Why:
- Users need a longer-feeling practice than 25 seconds, but the product still needs a clear cost/session cap and faster turn response.

Files touched:
- `app/services/voice_practice_service.py`
- `app/services/ai_service.py`
- `app/static/voice-practice.html`
- `tests/test_voice_practice_course_context.py`

Risk:
- Payment/subscription/access logic was not changed.
- Real Telegram WebView should still be smoke-tested for microphone latency, opening speech playback, and automatic final summary after the 7th dialog.

Follow-up:
- If latency remains high in production, the next real improvement is streaming/realtime voice instead of the current transcribe-then-chat pipeline.

### 2026-06-24 — Course section sequence and next-section routing fix

Changed:
- Course Mini App book lesson sections now unlock only when all previous sections in the same book lesson are completed.
- Book lesson access now follows `course_progress.completed_lessons_count`, so manual requests cannot jump to later book lessons before prior book lessons are complete.
- Section completion response now returns structured `next_section` and `next_book_lesson` refs; the frontend next button uses those server refs and only falls back within the current book lesson.

Why:
- Users could finish `1.1` and jump to `1.3`/another section because frontend next/current logic relied too much on local calculation and backend section unlock only checked the immediate previous key.

Files touched:
- `app/services/course_miniapp_lesson_flow_service.py`
- `app/static/study-v2.js`
- `tests/test_course_miniapp_lesson_flow.py`
- `tests/e2e/test_miniapp_smoke.py`

Risk:
- Payment/subscription approval logic was not changed.
- Existing corrupted local section completion can still be rejected server-side with `course_section_not_unlocked`; users may need to reopen the first incomplete section.

Follow-up:
- After deploy, smoke-test in Telegram WebView: complete `1.1`, press next to `1.2`, then verify locked manual taps show the previous-section message/paywall.

### 2026-06-24 — AI Voice paid budget integration

Changed:
- Mini App AI Voice now uses the existing AI usage budget gate for paid users before starting a session and before processing each voice turn.
- Voice transcription and AI reply costs are recorded into `ai_usage_events` with sources `voice_practice_transcribe` and `voice_practice_reply`.
- Frontend handles existing budget cooldown/depleted codes with user-facing RU/TJ/UZ messages instead of treating every 403 as a generic paywall.

Why:
- Paid Voice Practice must share the same payment-derived AI budget rule as text/photo AI: roughly 50% of payment revenue is available for AI costs, with cooldown/depletion handling managed by `AIUsageBudgetService`.

Files touched:
- `app/services/voice_practice_service.py`
- `app/static/voice-practice.html`
- `tests/test_voice_practice_course_context.py`

Risk:
- Payment approval and subscription creation were not changed.
- Existing paid users without an active budget remain allowed because `AIUsageBudgetService.can_use_ai()` already allows no-budget users; users with active budgets now have Voice Practice counted against that budget.

Follow-up:
- Smoke-test one paid Voice Practice call after deploy and verify `ai_usage_events.source` contains `voice_practice_transcribe` and `voice_practice_reply`.

### 2026-06-23 — Course lesson quality, AI Voice access, and duplicate UX cleanup

Changed:
- Course Mini App lesson generation no longer creates sentence-build tasks from single Hanzi fragments like `以` + `前`; fallback sentence tasks now use short natural Chinese phrases.
- Character-writing cards became passive writing-order practice: users see the stroke/order hint and confirm completion instead of being forced to draw.
- Fixed a lesson generation crash caused by an undefined `zh` variable in grammar fallback cards.
- AI Voice paid users now receive subscription-based access (`remaining_voice_limit = -1`) instead of a hard daily session count; free users still keep the existing one-time trial gate.
- AI Voice frontend now exposes only two roles: Chinese friend and Li Laoshi. Unsupported level/settings controls are hidden.
- Profile removed duplicate subscription/league shortcuts and added local avatar upload. League rows are clickable and the League tab owns the main leaderboard/podium entry point.

Why:
- Users reported many lessons failing to open, unnatural dialogs, overly hard word-building tasks, and cluttered AI Voice/Profile/League UX.

Files touched:
- `app/services/course_miniapp_lesson_flow_service.py`
- `app/services/voice_practice_service.py`
- `app/static/study-v2.js`
- `app/static/study-v2.css`
- `app/static/voice-practice.html`
- `tests/test_course_miniapp_lesson_flow.py`

Risk:
- Payment backend and subscription approval flow were not changed.
- Real Telegram WebView should still be smoke-tested after deploy for voice paywall routing, avatar upload, and lesson card rendering.

### 2026-06-23 — Mode selection required-channel gate

Changed:
- Language selection now shows Course/Oddiy mode first, then required-channel subscription is checked when the user chooses either mode.
- If the user is missing required channel subscription, the selected mode is stored in FSM data and resumed after `force_sub:check`: Course sends the Course Mini App entry, Oddiy mode activates QA mode.

Why:
- Forced channel subscription should start after the user chooses Course or Oddiy mode, not before the mode selection screen.

Files touched:
- `app/bot/keyboards/onboarding.py`
- `app/bot/handlers/course.py`
- `app/bot/handlers/required_channel.py`
- `app/bot/middlewares/required_channel.py`
- `tests/test_course_miniapp_onboarding.py`

Risk:
- Telegram bots cannot truly auto-open a WebApp from a subscription check callback; the bot resumes the flow and sends the Course Mini App WebApp button automatically.

Follow-up:
- Smoke-test new `/start` users in Telegram for both Course and Oddiy mode with subscribed and unsubscribed channel states.

### 2026-06-23 — Course Mini App lesson variety and section unlock recovery

Changed:
- Course Mini App section lessons now include varied activity units inside the same path node: word intro, listening/audio choice, character trace, short dialog, sentence build, pronunciation, and review cards.
- Long word-order tasks are filtered out and replaced with short Chinese character/word builds so users are not asked to assemble long RU/TJ translations.
- Short dialog generation now uses natural templates by word type and special handling for awkward verbs like `赚`.
- Lesson open/complete APIs accept same-lesson client-completed section keys as recovery input when server analytics events lag behind local progress.

Why:
- Users were seeing repetitive multiple-choice sections, overly hard word assembly, unnatural dialogs, and locked sections after local completion.

Files touched:
- `app/services/course_miniapp_lesson_flow_service.py`
- `app/main.py`
- `app/static/study.html`
- `app/static/study-v2.js`
- `app/static/study-v2.css`
- `tests/test_course_miniapp_lesson_flow.py`

Risk:
- Client-completed recovery only counts valid previous sections in the same book lesson; payment/subscription/referral logic is unchanged.

Follow-up:
- Replace the current tap-to-confirm character trace MVP with real canvas stroke detection if higher accuracy is needed.

### 2026-06-23 — Mini App reward, league, and AI Voice paywall UX

Changed:
- Course Mini App lesson completion now shows a sequential reward experience: result, streak progress, and league movement using an HSK AI-owned `汉` mascot instead of copied Duolingo-style characters.
- League tab now renders a trophy track and ranked rows with special top-3 medals, while still using existing gamification data/fallback rows.
- AI Voice tab opens even when voice access is exhausted; the paywall appears at call/session start instead of blocking the tab. Voice paywall/subscription buttons route back to the existing Mini App subscription flow through the parent shell.
- AI Voice settings removed the unsupported help/support block and no longer claims limits refresh daily.

Why:
- Course rewards and league movement need Duolingo-like dopamine UX while keeping HSK AI visual identity and preserving existing subscription/payment logic.

Files touched:
- `app/static/study-v2.js`
- `app/static/study-v2.css`
- `app/static/voice-practice.html`

Risk:
- Changes are frontend UX only; payment/subscription backend logic was not changed.
- Real Telegram WebView should be smoke-tested for AI Voice paywall routing and reward screen layout.

Follow-up:
- Add browser/E2E screenshot coverage once local Playwright/Chrome runtime is available.

### 2026-06-23 — Course Mini App migration deploy fix

Changed:
- `0052_course_miniapp_v3_preferences` now drops existing `daily_minutes` check constraints from the Postgres catalog before recreating the canonical constraint with raw SQL.
- `CourseMiniAppProfile` uses naming-convention source names (`goal`, `daily_minutes`, `start_mode`) so SQLAlchemy does not double-prefix generated constraint names.
- Bot help and Mini App profile support now use the configured admin contact URL.

Why:
- Railway deploy failed when production had a naming-convention generated `daily_minutes` constraint name that did not match the migration's static drop list.

Files touched:
- `alembic/versions/0052_course_miniapp_v3_preferences.py`
- `app/db/models/course_miniapp_profile.py`
- `app/services/help_settings_service.py`
- `app/services/study_miniapp_service.py`
- `app/static/study.html`
- `app/static/study-v2.js`

Risk:
- Low. Migration is Postgres-focused and only changes the Course Mini App profile check constraint; payment/subscription logic is untouched.

### 2026-06-23 — Course Mini App section/chapter/book lesson progression

Changed:
- Course Mini App lessons now have three progress levels: section, chapter, and book lesson.
- HSK book material remains in `course_lessons`; Mini App splits each book lesson into deterministic section nodes by vocabulary count, grouped visually into A/B/C chapters.
- Darslar/Course page keeps the Duolingo-style road/path and renders sections as path nodes inside chapter groups instead of converting to a list/table.
- Every section includes a short context dialog card; long textbook dialogue screens are not restored.
- Completion now records `section_completed`, `chapter_completed`, and `book_lesson_completed`; legacy `lesson_completed` is still recorded only when the whole book lesson is complete for admin compatibility.
- XP is server-side at all three levels: section small XP, chapter bonus XP, book lesson bonus XP. Payment/subscription/referral logic was not changed.

Why:
- Large HSK book lessons must feel like small learning steps while preserving HSK material order and the existing Course path UX.

Files touched:
- `app/services/course_miniapp_lesson_flow_service.py`
- `app/db/models/course_miniapp_event.py`
- `app/services/course_miniapp_admin_analytics_service.py`
- `app/main.py`
- `app/static/study-v2.js`
- `app/static/study-v2.css`
- `app/static/study.html`
- `tests/test_course_miniapp_lesson_flow.py`

Risk:
- Completed section state is stored server-side through analytics/dedupe events, while the current frontend also mirrors section completion in local storage for immediate path rendering.
- Browser E2E still depends on Playwright/pytest availability in the local runtime.

### 2026-06-23 — Mini App AI Voice embedded UX fix

Changed:
- Course Mini App V3 AI Voice iframe now uses parent page height instead of subtracting the top/nav chrome twice, so start/call controls stay visible inside Telegram.
- Embedded AI Voice mode uses compact sizing, reduced background motion, direct end-call behavior, and posts `hsk_voice_close` back to the V3 shell instead of trying to close the whole Telegram Mini App from inside the iframe.
- The V3 quiz page no longer shows the visible `Quiz/Квиз` title header; lesson/test quiz routes and filters remain available.

Why:
- On iPhone Telegram WebView, AI Voice entry/call/summary controls could fall below the visible area or sit under the bottom nav, and the summary close action did not reliably return users to the Mini App shell.

Files touched:
- `app/static/study.html`
- `app/static/study-v2.js`
- `app/static/study-v2.css`
- `app/static/voice-practice.html`
- `tests/e2e/test_miniapp_smoke.py`

Risk:
- Browser E2E could not run locally because Playwright/pytest/Chrome are not installed in the available environments; JS syntax and Python compile checks passed.

### 2026-06-23 — Course Mini App V3 navigation, rewards, and training

Changed:
- Course Mini App V3 uses exactly five bottom tabs: Home, Lessons, League, AI Voice, Profile. Test is available from Home as a Test Center, not as a sixth nav tab.
- Free users see one-time access locks for lesson, AI Voice, placement, and training/test features through existing subscription checks; payment backend and entitlement logic were not changed.
- Server gamification now returns non-blocking energy, weekly same-league leaderboard metadata, and reward chest state. Reward chest opens through `/api/miniapp/reward-chest/open` and awards XP only.
- XP rules now match V3 product rules: lesson 20 XP, test 10 XP, training 8 XP, AI Voice 10 XP, mistake review 5 XP, with existing streak bonus.
- Training/Test Center now includes HSK1-HSK4 tests, placement, listening, pronunciation, writing, characters, pinyin, speaking, and mistake review.
- Onboarding daily time supports 10, 15, 20, and 30 minutes. Alembic head is `0052_course_miniapp_v3_preferences`.
- AI Voice Mini App call UI auto-closes paid calls around 25 seconds with a short Chinese goodbye; voice payment/access backend remains unchanged.

Why:
- V3 product decision keeps Course Mode inside the Mini App with Duolingo-style navigation, rewards, and practice while preserving Telegram QA and payments.

Key files:
- `app/static/study-v2.js`
- `app/static/study-v2.css`
- `app/static/study.html`
- `app/static/voice-practice.html`
- `app/services/course_gamification_service.py`
- `app/services/course_miniapp_practice_service.py`
- `app/services/course_miniapp_lesson_flow_service.py`
- `app/services/course_mistake_service.py`
- `app/services/voice_practice_service.py`
- `app/main.py`
- `alembic/versions/0052_course_miniapp_v3_preferences.py`

Risk:
- Migration `0052` must be applied before users select 30-minute onboarding goals.
- Browser E2E depends on Playwright/pytest availability in the runtime; local unit/syntax checks cover backend and script validity.

### 2026-06-23 — Course Mini App entry stays in QA mode

Changed:
- Bot-side Course entry points now send a short Course Mini App message with a WebApp button and keep `users.learning_mode = "qa"`.
- QA daily-limit messaging now shows exactly one block: first-lesson Mini App offer only before course trial usage; text/referral limit block after `trial_course_started_at`, `trial_course_completed_at`, `trial_quiz_explanation_used_at`, or a `quiz_completed` funnel event.
- Automatic post-QA course promo image/text was disabled.
- Course Mini App lesson flow no longer depends on `learning_mode = "course"`; it initializes `course_progress` and trial lesson access from the Mini App request.

Why:
- Course moved fully into Mini App, while Telegram chat should remain normal QA mode.

Files touched:
- `app/bot/handlers/messages.py`
- `app/bot/handlers/course.py`
- `app/bot/handlers/start.py`
- `app/bot/handlers/menu.py`
- `app/bot/handlers/commands.py`
- `app/services/course_miniapp_lesson_flow_service.py`
- `app/services/course_miniapp_onboarding_service.py`
- `app/services/course_miniapp_result_service.py`
- `app/repositories/course_lesson_repo.py`

Risk:
- Existing old Course callback messages may still reach legacy handlers, but all main visible entry points now route to Mini App.

Follow-up:
- In Telegram, smoke-test QA daily limit for users with and without course trial history, plus Course Mini App lesson open/complete from QA mode.

### 2026-06-23 — Course Mini App AI Voice, profile locks, and admin analytics

Changed:
- AI Voice characters now use the current Course Mini App lesson context. `voice_practice_sessions` stores `lesson_id` and `target_words`, and voice prompts receive lesson vocabulary for Lily, Chen, Xiao Mei, Teacher Li, and Manager Wang.
- Course Mini App Profile is server-backed via `/api/miniapp/profile`, including user info, level, subscription status, XP/streak/league, completed lessons, mistakes count, and feature lock state.
- Mini App lock UI now follows server `course_features` for lesson, voice, placement, and training/test access. Payment/subscription entitlement remains in the existing access services.
- Admin stats now include Course Mini App funnel, lesson drop-off, test/training completion, AI Voice usage, mistake review, XP/streak activity, and Mini App paid conversion.
- Payment approval records an idempotent `subscription_approved` Course Mini App analytics event after the existing subscription activation succeeds; payment backend behavior was not changed.
- Alembic head is `0051_connect_voice_to_course`.

Key files:
- `app/services/voice_practice_service.py`
- `app/services/study_miniapp_service.py`
- `app/services/course_miniapp_admin_analytics_service.py`
- `app/bot/handlers/admin.py`
- `app/bot/handlers/commands.py`
- `app/bot/handlers/admin_payments.py`
- `app/static/study-v2.js`
- `app/static/voice-practice.html`
- `alembic/versions/0051_connect_voice_to_course.py`

Risk:
- Migration `0051` must run before course-connected AI Voice traffic reaches production.
- Admin stats depend on `course_miniapp_events` being populated; missing historic events will show as zero rather than inferred.

### 2026-06-23 — Server XP, streak, and weekly league

Changed:
- Added idempotent `course_xp_events` and server-owned XP/streak fields on `course_miniapp_profiles`.
- Server-confirmed lesson, test, training, AI Voice, and mistake review completions now award XP; the first meaningful activity of a local day also awards a streak bonus.
- Added weekly leaderboard data for users in the same XP league and exposed gamification through access and Mini App APIs.
- Alembic head is `0050_add_course_gamification`.

Why:
- XP, streak, and league progression must not be granted by editable browser state.

Risk:
- Migration `0050` must run before the new gamification code receives production traffic.
- Existing payment and subscription approval logic was not changed.

Follow-up:
- Phase 8 connects AI Voice characters to the current course lesson vocabulary.

### 2026-06-23 — Server-backed Course Mistake Engine

Changed:
- Added `course_mistakes`, which aggregates lesson, test/training, and AI Voice corrections by word, grammar, character, and pronunciation weakness.
- Added authenticated mistake overview and idempotent personalized review APIs; review questions are server-graded and tied to server-issued session events.
- Mistake review uses the existing shared `training_test` one-time free entitlement. Paid access still follows the existing subscription check.
- Added `mistake_review_started` and `mistake_review_completed` analytics. Alembic head is `0049_add_course_mistakes`.

Why:
- Personalized mistake review needs persistent cross-feature data instead of browser-only `localStorage`.

Files touched:
- `app/db/models/course_mistake.py`
- `app/services/course_mistake_service.py`
- `app/services/course_miniapp_lesson_flow_service.py`
- `app/services/course_miniapp_practice_service.py`
- `app/services/voice_practice_service.py`
- `app/main.py`
- `app/static/study.html`
- `app/static/study-v2.js`
- `alembic/versions/0049_add_course_mistakes.py`

Risk:
- Migration `0049` must run before mistake collection receives production traffic.
- Payment handlers, payment tables, and subscription approval logic were intentionally not changed.

Follow-up:
- Phase 7 should move XP, streak, and league state from browser storage to the server.

### 2026-06-23 — Course Mini App backend foundation

Changed:
- Added server-side Course Mini App profile preferences, one-time feature usage records, and a dedicated analytics event store.
- Course access payload now exposes lesson, voice, placement, and training/test entitlements without changing payment approval or subscription rules.
- Existing completed lesson trials and voice sessions are treated as already used, so migration cannot reopen free features.
- Trusted completion events are server-only; client analytics events cannot grant progress or access.
- Alembic head is `0048_add_course_miniapp_foundation`.

Why:
- Course onboarding, interactive lessons, tests, gamification, and analytics need one server-side foundation before replacing the prototype's local-only state.

Files touched:
- `app/db/models/course_miniapp_profile.py`
- `app/db/models/course_feature_usage.py`
- `app/db/models/course_miniapp_event.py`
- `app/services/course_miniapp_access_service.py`
- `app/services/course_miniapp_profile_service.py`
- `app/services/course_miniapp_analytics_service.py`
- `app/main.py`
- `app/services/study_miniapp_service.py`
- `alembic/versions/0048_add_course_miniapp_foundation.py`

Risk:
- Migration `0048` must run before the new entitlement and analytics paths receive production traffic.
- Payment handlers and payment tables were intentionally not changed.

Follow-up:
- Phase 2 must persist Mini App onboarding through this profile service and emit the approved onboarding events.

### 2026-06-23 — Course-first HSK AI V2 Mini App and AI Voice

Changed:
- `study.html` now loads the course-first V2 Mini App shell with Home, Course, Tests, Training, AI Voice, Profile, XP, streak, missions, rewards, league, and mistake review while preserving existing lesson query routes.
- AI Voice now has verified Telegram Mini App APIs, capped session/turn/audio usage, OpenAI transcription and structured corrections, RU/TJ/UZ UI localization, and a persistent `voice_practice_sessions` table.
- Passing the exact current V2 lesson now idempotently advances legacy course progress through `CourseEngineService`; free access is limited to the first trial lesson.
- Alembic head is `0047_add_voice_practice_sessions`.

Why:
- The old study surface did not provide the requested unified course-first product experience, and the supplied voice prototype had mock endpoints only.

Files touched:
- `app/static/study.html`
- `app/static/study-v2.css`
- `app/static/study-v2.js`
- `app/static/voice-practice.html`
- `app/main.py`
- `app/services/voice_practice_service.py`
- `app/services/study_miniapp_service.py`
- `app/db/models/voice_practice_session.py`
- `alembic/versions/0047_add_voice_practice_sessions.py`

Risk:
- The V2 lesson score is currently calculated in the client; the server verifies Telegram identity, current lesson, access, pass threshold, and idempotence, but canonical server-side grading is still preferable.
- Production AI Voice requires migration `0047` before traffic and a real Telegram microphone/initData smoke test after deploy.

Follow-up:
- Run Alembic upgrade during deploy, test AI Voice in Telegram, monitor session limits/OpenAI cost, and move canonical V2 quiz grading server-side before expanding high-value rewards.

### 2026-06-21 — Course-first onboarding and Duo Mini App adapter

Changed:
- `/start` no longer sends new users into DailyPractice after language + level; it starts the first available course lesson directly so users see course value immediately.
- Course quiz/homework buttons now open `duo-lesson.html`, which loads real course payload from `/api/miniapp/lesson` and submits quiz/homework results to `/api/miniapp/event`.
- Course/QA onboarding tips are queued with zero delay and sent immediately when possible instead of waiting ~30 seconds.
- Stroke-order Mini App now sends Telegram WebApp init data when loading lesson vocabulary.

Why:
- Conversion issue was users not seeing course value early and getting split between QA/DailyPractice/Course choices.

Files touched:
- `app/bot/handlers/start.py`
- `app/bot/handlers/course.py`
- `app/bot/handlers/messages.py`
- `app/bot/utils/course_miniapp.py`
- `app/main.py`
- `app/static/duo-lesson.html`
- `app/static/stroke-order.html`
- `app/services/course_miniapp_result_service.py`
- `app/services/onboarding_tip_service.py`

Risk:
- Mini App result submission still depends on valid Telegram WebApp `initData`; local browser preview can only test fallback/static behavior.

Follow-up:
- Smoke test in Telegram after deploy: new `/start` onboarding, Duo quiz result, Duo homework result, stroke-order vocabulary open event.

### 2026-06-20 — Course pilot compact first 3 lessons

Changed:
- HSK1-HSK4 lessons 1-3 now return a compact pilot experience payload for Course Mini App quiz/reinforcement: consistent skeleton, shorter task count, and varied activities by lesson order.
- Lessons 4+ keep the existing payload shape and course flow.
- Added `course_pilot_events` for opened/completed/returned telemetry, with admin stats showing pilot open, quiz completion, reinforcement completion, drop signal, and lesson breakdown.

Why:
- Trial course completion was a weak signal; the pilot keeps structure familiar while making the first three lessons lighter and measurable before expanding changes.

Files touched:
- `app/services/course_miniapp_lesson_service.py`
- `app/services/course_miniapp_result_service.py`
- `app/static/course-miniapp-v2.js`
- `app/main.py`
- `app/bot/handlers/admin.py`
- `app/db/models/course_pilot_event.py`
- `alembic/versions/0043_add_course_pilot_events.py`

Risk:
- Pilot telemetry is append-only and should not affect access/payment logic, but Mini App smoke testing is needed with real Telegram `initData`.

Follow-up:
- Watch Course pilot 1-3 stats before applying the compact format to later lessons.

### 2026-06-19 — Daily 3-min onboarding loop

Changed:
- New/free onboarding now starts with `DailyPractice`: 3 words, 2 quick quiz prompts, and 1 simple sentence after language and level selection.
- Course mode remains available from the menu and from DailyPractice, but it is no longer the primary onboarding path.
- Added `users.daily_practice_started_at`, `daily_practice_completed_at`, `daily_practice_streak`, and `daily_practice_last_day`.
- Required-channel subscription is no longer enforced globally or inside course `block_vocab_2`; it is checked only when a free QA user reaches the daily text limit.
- Trial course paywalls include a free QA fallback button, and admin stats show DailyPractice start/completion, D1→D2 return, Daily→Course, Daily→Paid, and QA-limit channel metrics.

Why:
- Trial course-first funnel showed low completion and no payment conversion. The new loop optimizes for quick daily completion and return before pushing full course depth.

Files touched:
- `app/bot/handlers/start.py`
- `app/bot/handlers/messages.py`
- `app/bot/middlewares/required_channel.py`
- `app/bot/handlers/required_channel.py`
- `app/bot/handlers/course.py`
- `app/bot/handlers/admin.py`
- `app/bot/handlers/commands.py`
- `app/bot/keyboards/onboarding.py`
- `app/services/daily_practice_service.py`
- `app/services/course_trial_service.py`
- `app/db/models/user.py`
- `app/db/session.py`
- `alembic/versions/0042_add_daily_practice_fields.py`

Risk:
- `force_sub_required_at` now represents QA-limit channel checkpoint going forward, but old rows may still include historical course checkpoint data.

Follow-up:
- Watch D1 completion, D2 return, and Daily→Course before judging payment conversion.

### 2026-06-19 — Course Mini App release announcement template

Changed:
- Release feedback admin panel now includes a ready Course Mini App update template with localized UZ/RU/TJ text.
- The template preserves selected target filters, defaults to `mode_filter=course`, and reuses the existing release send/test/schedule flow.

Why:
- Course Mini App UI changes need a fast way to show the update to users without manually rewriting the announcement each time.

Files touched:
- `app/bot/handlers/release_feedback.py`
- `app/bot/keyboards/release_feedback.py`

Risk:
- Admin must still confirm/send the campaign; this does not auto-broadcast on deploy.

Follow-up:
- Use admin panel → Release feedback → Course Mini App update → Admin test → Hozir/Schedule.

### 2026-06-19 — Course Mini App quiz and reinforcement UI

Changed:
- Course Mini App quiz payload now serves 5 server-graded questions with backward-compatible `opts/ans/id` plus UI metadata for `multiple_choice`, `listening_choice`, and `fill_blank`.
- Homework user-facing flow was renamed to Mustahkamlash / Закрепление / Мустаҳкамкунӣ while backend `homework` endpoint/state names stay compatible.
- Mini App homework can now complete as interactive reinforcement (`word_order`, `match_pairs`, `listening_choice`, `stroke_preview`) without mandatory written answers or AI grading.
- HSK1-HSK4 static course pages load a shared Mini App v2 renderer only for `mode=quiz/homework`; normal study pages keep their existing code path.

Why:
- Course flow should feel lighter and more interactive after lessons while preserving Lesson → Quiz → Result → Mustahkamlash → Result → Next Lesson.

Files touched:
- `app/services/course_miniapp_lesson_service.py`
- `app/services/course_miniapp_result_service.py`
- `app/static/course-miniapp-v2.js`
- `app/static/hsk1.html`
- `app/static/hsk2.html`
- `app/static/hsk3.html`
- `app/static/hsk4.html`
- `app/bot/utils/i18n.py`
- `app/bot/utils/course_miniapp.py`
- `app/main.py`

Risk:
- Full end-to-end Telegram smoke test still needs real `initData`, active course state, and production DB.

Follow-up:
- Smoke test HSK1-HSK4 quiz and Mustahkamlash from Telegram Mini App, including bot result messages and next lesson unlock.

### 2026-06-14 — Release feedback dashboard

Changed:
- Admin panel now has a Telegram-based Release feedback module for sending localized release announcements, collecting 1-5 ratings, required low-rating comments/screenshots, optional comments, and per-campaign stats.
- Release messages include a "Sinab ko'rish" CTA; non-paid users get temporary 30-minute active test access without changing `payment_status`.
- Completed release feedback from non-paid users creates a per-user 20% / 24-hour `admin_discount` campaign, so checkout reuses the existing Subscription Mini App admin discount flow.
- Added `release_feedback_campaigns`, `release_feedback_deliveries`, and `release_feedback_responses`.
- Admin statistics now includes overall bot feedback and release feedback metrics.

Why:
- Admin needs to announce new bot features, let users test them, collect actionable feedback, and track response/try/discount results.

Files touched:
- `app/bot/handlers/release_feedback.py`
- `app/services/release_feedback_service.py`
- `app/repositories/release_feedback_repo.py`
- `app/db/models/release_feedback.py`
- `app/bot/keyboards/release_feedback.py`
- `app/bot/fsm/release_feedback.py`
- `app/bot/handlers/admin.py`
- `app/main.py`
- `app/bot/create_bot.py`
- `alembic/versions/0041_add_release_feedback.py`

Risk:
- Temporary test access sets non-paid users to `status="active"` for 30 minutes but does not make them paid; paid logic must continue to rely on `payment_status="approved"`.
- Release feedback discounts are stored as normal admin discount campaigns targeted to one Telegram ID.

Follow-up:
- Run migration/deploy, then smoke test release create/test/send, user try access, 1-5 rating, low-rating comment, discount checkout, and admin stats.

### 2026-06-14 — Feedback prompt delay removed

Changed:
- Bot feedback requests are now eligible immediately after the daily limit offer is sent, without the previous 5-minute delay.

Why:
- User requested faster otziv collection after the daily limit is reached.

Files touched:
- `app/services/bot_feedback_service.py`

Risk:
- Feedback prompt may appear sooner after the limit message; retry and 30-day completion throttles still apply.

Follow-up:
- Smoke test a daily-limit user and confirm the otziv prompt is sent on the next scheduler cycle.

### 2026-06-13 — Broadcast and ad campaign CTA buttons

Changed:
- Admin broadcast and ad campaign creation now ask whether to add one inline button under the outgoing message.
- Ready button actions include subscription Mini App, partner, course mode, reminder setup, help, admin contact, profile, plus a custom external URL with optional custom button text.
- Ad campaigns store the optional button as `ad_campaigns.button_config` JSON text, with migration/bootstrap support for existing databases.

Why:
- Marketing messages need direct CTA buttons without manually building separate bot flows for each campaign.

Files touched:
- `app/bot/keyboards/promo_button.py`
- `app/bot/handlers/admin_broadcast.py`
- `app/bot/handlers/admin_ads.py`
- `app/bot/handlers/menu.py`
- `app/db/models/ad_campaign.py`
- `app/repositories/ad_campaign_repo.py`
- `app/services/ad_campaign_service.py`
- `app/db/session.py`
- `alembic/versions/0040_add_ad_campaign_button_config.py`

Risk:
- Button action callbacks send a new message and leave the original broadcast/ad message intact; Telegram smoke testing is needed for each CTA type.

Follow-up:
- Run migration/deploy, then test broadcast and ad campaign with no button, subscription, profile, reminder, admin contact, and external URL buttons.

### 2026-06-13 — AI level ceiling hardened

Changed:
- General QA system prompt now explicitly forbids examples, vocabulary, grammar, sentence patterns, and explanations above the user's current level.
- Course tutor prompts now append the same level-ceiling rule to every step response and homework evaluation.
- Image explainer prompt now requires image explanations/examples to stay at or below the user's level.

Why:
- AI tutor behavior must not teach above the user's HSK level unless the user explicitly asks about higher-level content.

Files touched:
- `app/prompts/qa_system.txt`
- `app/services/course_tutor_service.py`
- `app/services/image_explainer_service.py`

Risk:
- Responses may become simpler and avoid advanced examples even when they would be interesting, which is intentional for level safety.

Follow-up:
- Smoke test HSK1/HSK2 QA, image explanation, and course lesson AI feedback with prompts asking for advanced examples.

### 2026-06-13 — Help links moved to admin-managed bot settings

Changed:
- `/help` and menu Help now build 3-language HTML help text from `bot_settings` video-link keys instead of hardcoded help content/contact.
- Admin panel now has one `Help sozlamalari` section containing 4 help video link types per language (`tj`, `ru`, `uz`) plus one global admin contact link.
- Empty help video links are skipped in user help text; admin contact is shown as an inline button below the help message when configured.

Why:
- Help video URLs and support contact must be editable from the admin panel without code changes.

Files touched:
- `app/services/help_settings_service.py`
- `app/services/support_contact_service.py`
- `app/bot/handlers/admin.py`
- `app/bot/handlers/commands.py`
- `app/bot/handlers/menu.py`
- `app/bot/handlers/messages.py`
- `app/bot/fsm/admin_management.py`
- `app/bot/utils/i18n.py`
- `app/static/subscription.html`

Risk:
- Existing deployments without `admin_contact` in `bot_settings` will show the help text without the contact button until admin sets a contact link.

Follow-up:
- In Telegram, test Admin panel → Help sozlamalari, set one video link for each language, then test `/help` and Help menu in TJ/RU/UZ.

### 2026-06-13 — Admin user deletion flow simplified and hardened

Changed:
- Admin panel delete-user button now starts an FSM flow: admin taps delete, bot waits for Telegram ID, admin sends only the numeric ID, and the bot deletes the user.
- Duplicate `/deleteuser` handler was removed from the broadcast router; the legacy `/deleteuser TELEGRAM_ID` fallback now uses the same repository delete path.
- User deletion now explicitly clears direct internal user-linked rows (`messages`, course progress/attempts, onboarding tip events, bot feedback) before deleting the `users` row.

Why:
- `/deleteuser` was duplicated across routers and admin panel forced command usage instead of a simple ID prompt.
- Delete could fail or behave inconsistently when related user rows existed and DB cascade was not enough.

Files touched:
- `app/bot/fsm/admin_management.py`
- `app/bot/handlers/admin.py`
- `app/bot/handlers/admin_broadcast.py`
- `app/bot/handlers/messages.py`
- `app/repositories/user_repo.py`

Risk:
- Payment/portfolio/partner audit rows are intentionally not deleted; they may still reference the Telegram ID for business history.

Follow-up:
- Deploy and smoke test in Telegram: Admin panel → Foydalanuvchini o'chirish → send numeric Telegram ID → confirm user disappears/restarts cleanly.

### 2026-06-13 — Subscription Mini App card payment display cleanup

Changed:
- Card checkout payment summary no longer shows the card-country row or duplicate bot-price row.
- Card checkout now shows `Dushanbe City` as the TJK bank name and keeps the exchange-rate row only for non-TJ cards.
- Discounted card quotes now include the original local payable amount so the Mini App can show it as a small crossed-out amount above/beside the discounted payable amount.
- Card payment instructions are collapsed by default and expand on tap; Tajik wording was simplified and the `Intiqol` mention was removed.

Why:
- Users saw duplicate pricing and overly long payment instructions on the final card payment screen.

Files touched:
- `app/static/subscription.html`
- `app/services/subscription_miniapp_service.py`

Risk:
- Payment creation still uses the existing final amount; this change mainly affects display and quote payload shape.

Follow-up:
- Smoke test real Telegram Mini App card checkout with TJ and non-TJ cards, including a discount mode.

### 2026-06-13 — HSK1/HSK2 Mini App quiz and homework flow aligned with HSK4

Changed:
- HSK1 and HSK2 Mini App quiz pages now open directly into the lesson quiz, matching the HSK4 flow instead of showing a separate start card.
- HSK1 and HSK2 homework pages now use the same purpose text style as HSK4 and submit homework answers as `vocab_sentences`, `grammar_sentences`, and `translations`.
- Homework submit keeps the return-to-bot button visible after submission, with local/offline fallback and Telegram `sendData` fallback aligned to HSK4-style event handling.
- Mini App asset version was bumped so Telegram opens the updated static files.

Why:
- Quiz and homework Mini Apps needed consistent UI and behavior across all HSK levels.

Files touched:
- `app/static/hsk1.html`
- `app/static/hsk2.html`
- `app/bot/utils/course_miniapp.py`

Risk:
- HSK1/HSK2 direct quiz start removes the previous pre-quiz start screen; course result saving still uses the existing `/api/miniapp/event` path.

Follow-up:
- Smoke test Telegram Mini App links for HSK1 and HSK2: quiz result returns to bot, homework submission shows return button, and bot receives AI homework result.

### 2026-06-12 — Course text AI separated from QA daily text limit

Changed:
- Trial/free course-mode text AI checks now bypass the QA daily text limit and course text AI usage no longer increments `users.questions_used`.
- Normal QA text messages still use `questions_used/question_limit` exactly as before.

Why:
- Course-mode text help should not consume or block the user's QA-mode daily text allowance.

Files touched:
- `app/services/access_service.py`
- `app/bot/handlers/messages.py`

Risk:
- This affects only text AI access accounting; photo and voice limits are unchanged.

Follow-up:
- Smoke test with a trial user: ask course tutor/homework/mistake discussion, then switch to QA and confirm daily text remaining was not reduced.

### 2026-06-12 — Subscription Mini App referral, QR, and help contact fixes

Changed:
- Limit-offer referral buttons use clearer bonus-question wording and update the existing limit block into referral invite/progress text.
- Subscription Mini App referral sheet shows the referral link visibly, improves copy status, and uses a stronger QR download/open fallback.
- Help text is shorter and uses an admin contact inline button backed by configurable `bot_settings.admin_contact`.

Why:
- Users needed clearer referral actions, visible invite links, more reliable QR handling in Telegram WebView, and simpler help/contact access.

Files touched:
- `app/static/subscription.html`
- `app/services/subscription_miniapp_service.py`
- `app/services/support_contact_service.py`
- `app/bot/handlers/referral.py`
- `app/bot/keyboards/help.py`
- `app/bot/utils/i18n.py`

Risk:
- QR download still depends on Telegram WebView/browser behavior; fallback opens the image if direct download is blocked.

Follow-up:
- Smoke test Mini App referral copy/share, QR display/download, and `/help` admin contact button.

### 2026-06-12 — Course grammar and all-level quiz quality tuning

Changed:
- HSK4 grammar blocks render as concise useful blocks: pattern, usage, one lesson example, and one attention note.
- HSK1-HSK4 Mini App quiz selection prioritizes distinct new words before repeating alternate question types, limits grammar repetition, and deduplicates exact questions.
- Backend Mini App quiz questions include word metadata so frontend selection can avoid several early questions from the same word.
- Course quiz intro text was simplified into a direct challenge-style prompt.

Why:
- Quiz users should be tested on more newly learned words, not duplicate-style questions from the first few words.
- HSK4 grammar needed to be useful without becoming a long theory block.

Files touched:
- `app/bot/utils/course_formatter.py`
- `app/bot/utils/course_miniapp.py`
- `app/bot/utils/i18n.py`
- `app/services/course_miniapp_lesson_service.py`
- `app/services/course_tutor_service.py`
- `app/static/hsk1.html`
- `app/static/hsk2.html`
- `app/static/hsk3.html`
- `app/static/hsk4.html`

Risk:
- Small blocks can return fewer than the target count if there are not enough unique valid questions, but this avoids low-quality duplicates.

Follow-up:
- Smoke test HSK1-HSK4 block quiz in Telegram/Mini App and confirm the first questions cover different new words.

### 2026-06-12 — Course trial fallback and homework processing feedback

Changed:
- Course subscription offers shown after course/trial lock now include an "Oddiy rejim" fallback button that switches the user back to `learning_mode="qa"` with existing daily limits and sends a short explanation that no automatic lessons are sent in this mode.
- Mini App homework submission now sends an immediate "AI is checking" chat message and edits that same message into the final AI homework result.
- Text/photo/course/voice AI replies now use a safer send path: empty AI content returns a localized fallback, AI exceptions send a visible retry message, malformed HTML retries without parse mode, and long replies are split into Telegram-safe chunks.
- The temporary "bot is working" edit effect now chooses different emoji sequences by mode (`qa`, `course`, `image`) and a seed based on user question count/text.

Why:
- Trial users who finish the free course lesson need a clear non-paid path back to daily-limited QA instead of only seeing the subscription button.
- Homework AI checks can take time, so the bot should visibly work instead of staying silent.
- AI or Telegram formatting failures should not make the bot appear to ignore a user message when an app-level fallback can still be sent.

Files touched:
- `app/bot/keyboards/subscription.py`
- `app/bot/handlers/course.py`
- `app/main.py`
- `app/bot/handlers/messages.py`
- `app/bot/utils/i18n.py`

Risk:
- Free mode does not grant new access; it only sets `learning_mode="qa"` and existing daily limits still control usage.
- Telegram message edit failures fall back to sending the final result as a new message.
- The fallback cannot fix upstream outages or Telegram delivery failures, but it prevents silent app-level failures for empty AI output, exceptions, bad HTML, and overlong text.

Follow-up:
- Smoke test in Telegram: finish a trial lesson, tap "Oddiy rejim", ask text/photo/course questions, then submit homework from the Mini App and confirm the processing message edits into the final result.

### 2026-06-12 — AI usage budget live-rate calculation

Changed:
- Paid subscription AI usage budgets now try live USD exchange rates when a payment is approved, including TJS and CNY, with admin-set subscription rates as fallback.
- The admin subscription price panel now includes a CNY fallback rate for Alipay/WeChat AI budget conversion.
- AI usage budget profit reserve changed from 40% to 50%.
- The fixed $1 Railway/server deduction was removed from per-payment AI budget calculation.

Why:
- Subscription limits should follow real exchange rates and updated business margin rules, but live-rate failures must fall back to admin-controlled rates instead of hardcoded TJS/CNY values.

Files touched:
- `app/bot/handlers/admin.py`
- `app/services/ai_usage_budget_service.py`
- `app/services/subscription_currency_service.py`

Risk:
- New approved payments will receive smaller AI budgets than before because profit reserve increased to 50%, but no extra $1 deduction is taken.
- Existing active AI budgets are not recalculated automatically.

Follow-up:
- After deploy, approve a small test payment and verify the created `ai_usage_budgets.total_budget_usd` against live/fallback rates.

### 2026-06-11 — Mini App subscription payment/referral repair

Changed:
- Subscription Mini App no longer shows demo/fallback payment data to real Telegram users when quote/overview APIs fail.
- VISA/card checkout now fails with a clear error if admin payment details are not configured.
- Mini App submit creates a pending payment only if at least one admin payment-review notification is delivered; otherwise it rolls back and returns an error.
- Referral 20% discount progress is recalculated from active referral records instead of trusting only `users.discount_referral_count`.
- Referral links for the 3-friend discount use the live bot username when possible, and the Mini App invite flow now supports localized share text plus copy-link-only.
- Legacy chat checkout reads admin-updated card payment details from `bot_settings.subscription_payment_details`.
- Reopening the Subscription Mini App while a payment is still pending shows a localized waiting screen instead of allowing duplicate payment submissions.
- The first Subscription Mini App screen now removes the extra explanatory hero block and keeps only concrete subscription benefits plus plan/payment choices.
- Profile and text/photo limit subscription buttons now open the Subscription Mini App directly with WebApp buttons instead of routing through the legacy `subscription:open` entry block.
- Subscription, referral discount, feedback discount, and admin campaign discount checkout now run through the Subscription Mini App modes (`subscription`, `referral_discount`, `feedback_discount`, `admin_discount`). Chat checkout plan/payment callbacks are legacy fallbacks that redirect to Mini App, and admin campaign notifications use a short Mini App entry instead of chat checkout blocks.
- Users who already used the referral discount no longer receive discount UI or discounted pricing from the Mini App.
- VISA/card payment details are rendered as readable rows with copy buttons for card-like numbers; Tajikistan card payments hide the exchange-rate row.
- The main reply-keyboard subscription button is now a Web App button that opens the Subscription Mini App directly; command/profile flows still send the explanatory Mini App entry block.
- QR payment screens let the user tap the QR to reveal a download button for saving the QR image.
- Card exchange-rate rows shown to users use direct TJS rates, for example `1 TJS = ... RUB`, instead of displaying USD/USDT-style cross-rate chains.
- Subscription Mini App has a top Help button with the public admin contact for payment-confirmation problems and visible errors; it remains available on pending-payment screens.

Why:
- Users were seeing wrong/fallback QR, card details, referral links, and discount state in the subscription Mini App, and payment submits could appear successful even if admin review did not receive the request.

Files touched:
- `app/static/subscription.html`
- `app/services/subscription_miniapp_service.py`
- `app/services/admin_notify_service.py`
- `app/services/discount_service.py`
- `app/services/subscription_progress_service.py`
- `app/bot/handlers/subscription.py`
- `app/bot/utils/course_miniapp.py`
- `app/main.py`

Risk:
- If admin IDs are wrong or blocked, Mini App payment submit now returns an error instead of silently accepting the request.
- Graphify update was attempted but refused to overwrite the existing graph because the rebuilt graph had fewer nodes.

Follow-up:
- After deploy, test inside Telegram with real `initData`: VISA/card quote, Alipay/WeChat QR quote, screenshot submit, admin approval, and referral share/copy in UZ/RU/TJ.

### 2026-06-09 — Subscription flow moved to Mini App

Changed:
- Normal subscription entrypoints now open `subscription.html` as a Telegram Mini App instead of continuing the chat checkout flow.
- Mini App APIs `/api/subscription-miniapp/overview`, `/quote`, and `/submit` calculate prices server-side, apply only the normal referral 20% discount path, and send submitted screenshots to the existing admin payment review queue without AI screenshot verification.
- Admin price panel now includes manual bank-card rates for TJS/UZS/RUB and an AUTO live-rate toggle; Mini App card quotes use admin rates unless AUTO live rates are enabled and available.
- `payments` now stores optional `card_country`, `local_amount`, `local_currency`, and `exchange_rate` for Mini App card payments.

Why:
- Subscription checkout should stay inside the Mini App, avoid chat-return steps for the normal Obuna button, and prevent frontend-side price/rate mistakes.

Files touched:
- `app/static/subscription.html`, `app/main.py`, `app/services/subscription_miniapp_service.py`, `app/services/subscription_currency_service.py`, `app/bot/handlers/*`, `app/bot/keyboards/subscription.py`, `app/db/models/payment.py`, `app/repositories/payment_repo.py`, `alembic/versions/0037_add_miniapp_payment_local_fields.py`

Risk:
- Live exchange rates depend on the external rate provider; if unavailable, backend falls back to admin manual rates.

Follow-up:
- Verify the Mini App inside Telegram with real `initData`, uploaded QR codes for non-default Alipay/WeChat prices, and a real admin approval.

### 2026-06-07 — Price-specific Alipay/WeChat QR codes

Changed:
- Added `payment_qr_codes` storage for uploaded Telegram QR `file_id`s by scope, payment method, plan, amount, and currency.
- Alipay/WeChat custom subscription prices now require admin to upload the matching regular QR and the matching 20% discount QR before the price is saved.
- Admin discount campaigns that target or include Alipay/WeChat now require campaign QR codes per affected method/plan discounted amount.
- Checkout uses old static QR files only for default Alipay/WeChat prices and default 20% referral/feedback discounts; non-default missing QR no longer falls back to an old fixed-price QR.

Why:
- Alipay/WeChat QR codes are amount-specific, so users must never receive a QR for a different price after admin changes prices or creates a discount.

Files touched:
- `app/db/models/payment_qr_code.py`
- `app/repositories/payment_qr_code_repo.py`
- `app/services/payment_qr_code_service.py`
- `app/bot/handlers/admin.py`
- `app/bot/handlers/admin_discount.py`
- `app/bot/handlers/subscription.py`
- `alembic/versions/0036_add_payment_qr_codes.py`

Risk:
- Existing active admin discount campaigns created before this change do not have campaign-scoped QR records; for Alipay/WeChat checkout they may show "QR not ready" instead of the old generic admin discount QR.

Follow-up:
- Run migration/init DB, then smoke test: custom Alipay/WeChat price, 20% referral/feedback checkout, and admin discount campaign checkout.

### 2026-06-06 — Feedback prompt and reward timing

Changed:
- Feedback reward access is now 30 minutes instead of 1 day.
- Feedback requests are sent only after the user is at least 1 day old and has hit the daily text limit; the prompt becomes due 5 minutes after that limit event.

Why:
- Feedback should be requested after real limit friction, not just because the account is old.
- Feedback reward should not give a full day by default.

Files touched:
- `app/services/access_service.py`
- `app/services/bot_feedback_service.py`
- `app/main.py`
- `app/bot/handlers/messages.py`
- `app/bot/utils/i18n.py`

Risk:
- Existing `users.daily_limit_offer_sent_at` is reused as the limit-hit timestamp; no migration.
- Scheduler now checks feedback requests every 60 seconds, relying on pending feedback retry rules to prevent repeated prompts.

Follow-up:
- Smoke test with a user older than 1 day: hit the daily text limit, wait 5 minutes, confirm the feedback prompt appears once and reward activates for 30 minutes.

### 2026-06-06 — Feedback limit discount offer

Changed:
- Bot feedback dislike option `limits` now schedules the same 5-minute 20% subscription discount offer as `price`.
- The limits offer uses a separate user-facing message about bot limits, but reuses the existing feedback discount checkout/payment flow.

Why:
- Users who say bot limits are too low should get the same conversion path as users who say subscription price is high.

Files touched:
- `app/repositories/bot_feedback_repo.py`
- `app/services/bot_feedback_service.py`
- `app/services/discount_service.py`
- `app/bot/utils/i18n.py`

Risk:
- Existing DB fields are reused; no migration. Scheduler still sends due offers from the existing 60-second background loop.

Follow-up:
- Smoke test in Telegram: choose `Limitlar kam`, wait 5 minutes, open the 20% discount flow, and submit a payment screenshot.

### 2026-06-06 — Image caption as AI command

Changed:
- Photo messages now pass Telegram caption text into the image AI flow.
- The image explainer treats caption text as the user's command and uses analyzer output as the image source context.
- Image file IDs are excluded from normal QA chat history; follow-up context should come from stored image context.
- QA AI history now keeps system context messages, so stored image context is available in follow-up questions.

Why:
- Users sending photo + text like "Tarjima qil" need the bot to follow the text instruction instead of only explaining the image.

Files touched:
- `app/bot/handlers/messages.py`
- `app/services/image_qa_service.py`
- `app/services/image_explainer_service.py`
- `app/services/qa_service.py`
- `app/services/ai_service.py`

Risk:
- Prompt-only behavior change; image limits, subscription access, and payment logic are unchanged.

Follow-up:
- Test in Telegram with a photo caption command such as "Tarjima qil".

### 2026-06-05 — Command/menu input cleanup

Changed:
- Private-chat slash commands and main/course reply menu button messages are deleted after their handlers run.

Why:
- Keep Telegram chats clean while preserving command behavior.

Files touched:
- `app/bot/middlewares/cleanup.py`
- `app/bot/create_bot.py`

Risk:
- Delete failures are ignored; group chats are not affected.

Follow-up:
- Verify on production bot that Telegram allows deleting incoming private-chat command messages.

### 2026-06-04 — Localized TJS card subscription blocks

Changed:
- Card/TJS subscription selection and checkout messages now keep one compact format while matching the user's language (TJ/RU/UZ).
- TJS plan prices show `💸 {amount} TJS 🇹🇯` in the plan list and `{amount} TJS 💸` in checkout.
- Alipay/WeChat QR payment flow remains separate.

Why:
- Avoid mixed-language payment instructions and keep card payment instructions easy to read.

Files touched:
- `app/bot/handlers/subscription.py`

Risk:
- Text-only card flow change; payment amount and subscription logic unchanged.

Follow-up:
- Verify rendered Telegram blockquote spacing on production bot after deploy.

### 2026-05-25 — Course narrative text formatting

Changed:
- Course text blocks with narrator-style lines (`旁白` / no speaker) now render as text instead of dialogue: bold Chinese line, pinyin below, translation below.
- Narrative blocks show `Matn/Текст/Матн` in the course message header instead of `Dialog`.

Why:
- Textbook passages without speakers were hard to read when formatted like dialogue lines.

Files touched:
- `app/bot/utils/course_formatter.py`

Risk:
- This is display-only; stored lesson JSON and progress logic are unchanged.

### 2026-05-25 — Referral trial active access

Changed:
- Users can unlock 3 days of non-paid `active` access after collecting 10 active referrals.
- This reward is separate from the existing referral bonus and referral discount flows: +5 bonus questions and 3-referral discount counters still use their existing fields.
- Referral active access does not set `payment_status=approved`; it creates a fixed $2 AI usage budget for the trial active window.
- In trial active, text/course/photo use the fixed $2 AI budget; photo no longer has a separate daily image limit during this reward window.
- If the fixed $2 AI budget is depleted before 3 days, the non-paid active user is downgraded back to `trial`; if 3 days expire first, the user is also downgraded even if budget remains.
- Voice is restricted to real paid subscribers (`status=active` and `payment_status=approved`); non-paid active windows do not unlock voice.
- Profile labels non-paid active as `Sinov muddati`, shows only referral count, and leaves the subscription line empty unless the user has a real paid subscription.
- A new `users.referral_trial_count_started_at` marker resets this feature's referral count after each 3-day reward window.

Why:
- Trial users need a referral path to temporarily become `active` without replacing a real paid subscription.

Files touched:
- `app/services/referral_service.py`
- `app/services/access_service.py`
- `app/services/ai_usage_budget_service.py`
- `app/services/qa_service.py`
- `app/services/image_qa_service.py`
- `app/services/course_miniapp_result_service.py`
- `app/repositories/referral_repo.py`
- `app/db/models/user.py`
- `app/db/session.py`
- `app/bot/handlers/messages.py`
- `app/bot/handlers/referral.py`
- `app/bot/handlers/commands.py`
- `app/bot/handlers/menu.py`
- `app/bot/keyboards/referral.py`
- `app/bot/utils/i18n.py`
- `alembic/versions/0028_referral_trial_activation.py`

Risk:
- Paid users are still identified only by `payment_status=approved`; do not treat `status=active` alone as paid subscription.

Follow-up:
- Run DB migration in deploy environments before relying on referral trial progress display.

### 2026-05-25 — Referral bonus usage is lifetime

Changed:
- Daily trial limit reset now resets only `questions_used`; it does not reset `bonus_questions_used`.
- Referral trial active activation also keeps already-used referral bonus questions spent.

Why:
- Referral +5 questions are a one-time bonus, not a daily renewed allowance.

Files touched:
- `app/services/access_service.py`
- `app/services/referral_service.py`

Risk:
- Users who already reused bonus questions before this fix are not retroactively corrected.

Follow-up:
- If historical correction is required, add a separate data audit instead of mixing it into runtime access logic.

### 2026-05-24 — Dynamic course dialogue audio admin

Changed:
- Admin audio panel now builds required audio types from each lesson's current `dialogue_json` block count, so HSK4 lessons with 5 dialogues show `vocab` plus `dialogue_1` through `dialogue_5`.
- Audio status now distinguishes complete, partial, and missing lessons, and ignores obsolete audio types that no longer match the current lesson format.
- Course audio playback no longer falls back from `dialogue_2+` to `dialogue_1`; missing dialogue-specific audio now stays unavailable instead of playing the wrong old audio.

Why:
- After lessons were split into more dialogue blocks, the old admin/audio logic could hide later dialogues or reuse outdated audio under the wrong dialogue.

Files touched:
- `app/bot/handlers/admin_audio.py`
- `app/bot/handlers/course.py`
- `app/repositories/course_audio_repo.py`
- `app/services/course_engine_service.py`
- `app/services/course_tutor_service.py`

Risk:
- Existing lessons that only have `dialogue_1` uploaded will show missing audio for later dialogue blocks until admin uploads each specific dialogue audio.

Follow-up:
- If obsolete DB audio should be deleted automatically, add an explicit admin cleanup action instead of silently deleting rows.

### 2026-05-24 — HSK4 upper lesson localization quality

Changed:
- HSK4 上 lessons 1-3 now keep PDF-canonical Chinese dialogue/new-word material while adding Uzbek, Russian, and Tajik translations, dialogue pinyin, localized grammar explanations, and localized mini quiz/homework prompts.
- The HSK4 static mini app fallback data now uses language-aware vocabulary, grammar, and quiz strings instead of Uzbek-only strings.

Why:
- Bot course messages and Mini App could show blank or Uzbek-only explanations for Russian/Tajik users because HSK4 seed payload only contained Uzbek fields and empty dialogue pinyin.

Files touched:
- `scripts/hsk4_upper_pdf_materials.py`
- `scripts/hsk4_upper_i18n.py`
- `scripts/verify_hsk4_upper_pdf_materials.py`
- `app/static/hsk4.html`

Risk:
- Dialogue/new words remain source-locked to the textbook data in `scripts/hsk4_upper_pdf_materials.py`; only translations/explanations/pinyin are added in the i18n layer.

Follow-up:
- Use the same localization verifier before enabling HSK4 上 lessons 4-6 in Mini App support.

### 2026-05-24 — Course level completion upgrade flow

Changed:
- When a user finishes the last lesson in a HSK level, the bot now sends a level-completion congratulations message with lesson, vocabulary, dialogue, and study-duration progress.
- The bot then asks whether to move to the next HSK level in Uzbek, Russian, and Tajik. Yes upgrades `users.level`, resets course progress for the next level, and opens lesson 1. No keeps the user on the completed level and shows that level's lesson list.
- Final lessons are now marked completed only once, preventing repeated "next lesson" presses from double-counting progress.

Why:
- The previous final-lesson path only showed a generic "lesson completed" message when no next lesson existed.

Files touched:
- `app/services/course_engine_service.py`
- `app/bot/handlers/course.py`
- `app/bot/handlers/messages.py`
- `app/bot/keyboards/course_context.py`
- `app/bot/utils/i18n.py`

Risk:
- Advancing to the next level resets `CourseProgress.completed_lessons_count` for the new level because the current schema stores one course progress row per user.

Follow-up:
- If global cross-level progress is required later, add a dedicated course completion history table instead of overloading the current per-user progress row.

### 2026-05-24 — Course block AI context

Changed:
- HSK course AI prompts now receive block-level course context for block lessons: dialogue block, block vocabulary, grammar points, mini quiz, and mini homework.
- HSK3 lessons 13-16 were wired through `scripts/hsk3_pdf_materials.py`, so dialogue/new words are PDF canonical instead of synthetic seed content.

Why:
- Mini App quiz/homework review must explain the exact user mistakes using the same block material shown in the course.

Files touched:
- `app/services/course_tutor_service.py`

### 2026-05-24 — HSK3 block lesson completion

Changed:
- HSK3 lessons 17-20 now use PDF canonical dialogue/new-word material through `scripts/hsk3_pdf_materials.py`.
- All HSK3 lessons 1-20 now generate per-dialogue block steps with `block_vocab_N` before `dialogue_N`.

Why:
- Lessons 17-20 were still in the older V2 format, so later parts could start directly with `dialogue_3`/`dialogue_4` and skip the new-word section.

Files touched:
- `scripts/hsk3_pdf_materials.py`
- `scripts/seed_hsk3_lesson_17.py`
- `scripts/seed_hsk3_lesson_18.py`
- `scripts/seed_hsk3_lesson_19.py`
- `scripts/seed_hsk3_lesson_20.py`
- `scripts/verify_hsk3_pdf_materials.py`

Risk:
- Database must run the course seed sync or app restart so existing stored lesson JSON is refreshed.

Follow-up:
- If a deployed bot still shows old HSK3 lesson flow, restart/reseed first before debugging UI step logic.

### 2026-05-24 — Block grammar de-duplication

Changed:
- HSK1, HSK2, and HSK3 block lessons now normalize grammar per lesson so the same book grammar number is not shown repeatedly across multiple blocks.
- Every block still gets a short context grammar note based on the actual dialogue sentence used in that block.
- Telegram formatter and Mini App lesson payload prefer block `grammar_notes` over long book grammar items to avoid duplicate-looking explanations.

Why:
- Users saw repeated grammar material across blocks and some blocks felt like they had no useful grammar.

Files touched:
- `scripts/block_context_grammar.py`
- `scripts/hsk1_block_metadata.py`
- `scripts/hsk2_block_metadata.py`
- `scripts/hsk3_pdf_materials.py`
- `app/bot/utils/course_formatter.py`
- `app/services/course_miniapp_lesson_service.py`
- `app/services/course_tutor_service.py`
- `scripts/verify_course_block_grammar.py`

Risk:
- Existing database lesson JSON must be refreshed by seed sync/app restart before deployed users see the normalized grammar.
- `app/services/course_miniapp_result_service.py`
- `scripts/hsk3_pdf_materials.py`
- `scripts/seed_hsk3_lesson_13.py` to `scripts/seed_hsk3_lesson_16.py`
- `scripts/verify_hsk3_pdf_materials.py`

Why:
- 

Files touched:
- 

Risk:
- 

Follow-up:
- 

### 2026-05-24 — HSK4 上 first 3 lessons block format

Changed:
- HSK4 上 lessons 1-3 now use PDF-derived dialogue and vocabulary material through `scripts/hsk4_upper_pdf_materials.py`.
- Each of those lessons has 5 dialogue blocks, per-block vocabulary, one relevant PDF grammar point, mini quiz, and mini homework.
- HSK4 Mini App support is enabled only for lessons 1-3 for now via `hsk4.html`.

Why:
- HSK4 upper lessons had fewer dialogue blocks than the PDF and some lesson 2/3 grammar/vocabulary was from the wrong older seed format.

Files touched:
- `scripts/hsk4_upper_pdf_materials.py`
- `scripts/seed_hsk4_lesson_01.py` to `scripts/seed_hsk4_lesson_03.py`
- `app/bot/utils/course_miniapp.py`
- `app/static/hsk4.html`

Risk:
- Lessons 4+ are intentionally not enabled in HSK4 Mini App yet; continue in small batches to avoid content errors.

### 2026-05-24 — HSK4 上 lessons 4-6 PDF alignment

Changed:
- HSK4 上 lessons 4-6 now use canonical textbook dialogue/new-word data through `scripts/hsk4_upper_pdf_materials_4_6.py`.
- Each lesson has 5 dialogue blocks, 31 textbook vocabulary items, 5 grammar points, three-language translations, pinyin, per-block mini quiz/homework, and Mini App fallback data.
- Seed files for lessons 4-6 are now thin wrappers so stale non-PDF fallback content cannot leak into runtime data.

Why:
- Lessons 4-6 previously still contained older non-canonical seed material and HSK4 Mini App fallback only covered lessons 1-3.

Files touched:
- `scripts/hsk4_upper_pdf_materials.py`
- `scripts/hsk4_upper_pdf_materials_4_6.py`
- `scripts/seed_hsk4_lesson_04.py` to `scripts/seed_hsk4_lesson_06.py`
- `scripts/verify_hsk4_upper_pdf_materials.py`
- `app/static/hsk4.html`

Risk:
- Database must be reseeded for deployed environments; local DB was updated for HSK4-L04, HSK4-L05, and HSK4-L06 in this session.

### 2026-05-25 — HSK4 上 lessons 7-10 PDF alignment

Changed:
- HSK4 上 lessons 7-10 now use canonical textbook dialogue/new-word data through `scripts/hsk4_upper_pdf_materials_7_10.py`.
- Each lesson has 5 dialogue blocks, per-block vocabulary, one relevant grammar point, three-language translations, pinyin, mini quiz, and mini homework.
- HSK4 static Mini App fallback data now covers lessons 1-10 with grammar-focused quiz questions and no fill-blank style quiz items.

Why:
- Lessons 7-10 still had stale seed JSON and Mini App coverage stopped at lesson 6.

Files touched:
- `scripts/hsk4_upper_pdf_materials.py`
- `scripts/hsk4_upper_pdf_materials_7_10.py`
- `scripts/seed_hsk4_lesson_07.py` to `scripts/seed_hsk4_lesson_10.py`
- `scripts/verify_hsk4_upper_pdf_materials.py`
- `app/static/hsk4.html`

Risk:
- Database must be reseeded for deployed environments; local DB was updated for HSK4-L07 through HSK4-L10 in this session.

### 2026-05-25 — HSK4 下 lessons 11-13 PDF alignment

Changed:
- HSK4 下 lessons 11-13 now use canonical textbook dialogue/new-word data through `scripts/hsk4_lower_pdf_materials.py`.
- Each lesson has 5 blocks, per-block vocabulary, relevant grammar, pinyin, three-language translations, mini quiz, and mini homework.
- HSK4 static Mini App fallback now recognizes lessons 1-13 and includes grammar quiz items for lessons 11-13.

Why:
- HSK4 下 needed to start from the textbook format; older lower seed data had incomplete lesson blocks and stale lesson 11 content.

Files touched:
- `scripts/hsk4_lower_pdf_materials.py`
- `scripts/hsk4_lower_seed_data.py`
- `scripts/seed_hsk4_lesson_11.py`
- `scripts/verify_hsk4_lower_pdf_materials.py`
- `app/static/hsk4.html`

Risk:
- Database must be reseeded for deployed environments; local DB was updated for HSK4-L11 through HSK4-L13 in this session.

### 2026-05-25 — HSK4 Mini App support range

Changed:
- HSK4 Mini App support range is now lessons 1-13.

Why:
- HSK4 上 lessons 4-10 had Mini App content and API payloads, but course buttons were blocked by the stale supported range `1-3`.

Files touched:
- `app/bot/utils/course_miniapp.py`

Risk:
- HSK4 lessons beyond 13 stay unsupported until their lesson data is converted.

### 2026-05-25 — HSK4 下 lessons 14-16 PDF alignment

Changed:
- HSK4 下 lessons 14-16 now use canonical textbook dialogue/new-word data through `scripts/hsk4_lower_pdf_materials_14_16.py`.
- Each lesson has 5 blocks, per-block vocabulary, relevant grammar, pinyin, three-language translations, mini quiz, and mini homework generated through the lower seed pipeline.
- HSK4 static Mini App fallback and support range now cover lessons 1-16 with grammar-focused quiz items and no blank-fill quiz format.

Why:
- Lessons 14-16 needed the same PDF-based format as lessons 11-13 before continuing HSK4 下 in small batches.

Files touched:
- `scripts/hsk4_lower_pdf_materials.py`
- `scripts/hsk4_lower_pdf_materials_14_16.py`
- `scripts/verify_hsk4_lower_pdf_materials.py`
- `app/bot/utils/course_miniapp.py`
- `app/static/hsk4.html`

Risk:
- Runtime database must be reseeded or app restarted in deployed environments before Telegram course messages show HSK4-L14 through HSK4-L16.

### 2026-05-28 — HSK4 下 lessons 17-20 PDF alignment

Changed:
- HSK4 下 lessons 17-20 now use canonical textbook dialogue/new-word data through `scripts/hsk4_lower_pdf_materials_17_20.py`.
- Each lesson has 5 blocks, per-block vocabulary, relevant grammar, pinyin, three-language translations, mini quiz, and mini homework generated through the lower seed pipeline.
- HSK4 static Mini App fallback and support range now cover lessons 1-20 with grammar-focused quiz items and no blank-fill quiz format.

Why:
- Lessons 17-20 complete HSK4 下 in the same PDF-based format as lessons 11-16.

Files touched:
- `scripts/hsk4_lower_pdf_materials.py`
- `scripts/hsk4_lower_pdf_materials_17_20.py`
- `scripts/verify_hsk4_lower_pdf_materials.py`
- `app/bot/utils/course_miniapp.py`
- `app/static/hsk4.html`

Risk:
- Runtime database must be reseeded or app restarted in deployed environments before Telegram course messages show HSK4-L17 through HSK4-L20.

### 2026-06-04 — Localized admin messaging and TJS card subscriptions

Changed:
- Admin broadcast and ad campaign text can be written once in Tajik, then localized to TJ/UZ/RU through AI before sending; users receive the variant matching their language.
- Broadcast and ad campaign confirm flows include an admin test send without clearing the prepared message.
- Visa/Card subscription pricing is TJS-only: 10 days = 29 TJS, 1 month = 89 TJS by default. Alipay/WeChat remain in yuan.
- Stale checkout drafts are recalculated when a screenshot arrives so old USD drafts do not survive after the TJS switch.
- Expired admin/feedback discount buttons edit the original offer message to an expired text instead of only showing an alert.

Why:
- Admins should not send separate messages per language, and card subscription revenue should be priced in somoni.

Files touched:
- `app/services/broadcast_translation_service.py`
- `app/bot/handlers/admin_broadcast.py`
- `app/bot/handlers/admin_ads.py`
- `app/services/ad_campaign_service.py`
- `app/services/subscription_price_service.py`
- `app/bot/handlers/subscription.py`
- `app/services/payment_service.py`

Risk:
- Broadcast/ad translations depend on `OPENAI_API_KEY`; if translation fails, the Tajik source is used as a safe fallback.
- Telegram bot updates do not expose user IP, so non-TJ card users see a general bank-rate TJS payment note instead of IP-based country detection.

---

### 2026-06-11 — Menu subscription WebApp auth fix

Changed:
- Main reply keyboard `Obuna` is a normal text button again; the bot handler sends an inline Mini App button with `mode=subscription`.

Why:
- Reply-keyboard `web_app` launches were not reliably connecting the Subscription Mini App to the bot for some users. Inline WebApp buttons keep the Telegram init data flow stable.

Files touched:
- `app/bot/keyboards/main_menu.py`

Risk:
- The menu subscription path uses one bot message before opening the Mini App instead of opening directly from the reply keyboard.

---

### 2026-06-11 — New user course trial funnel and channel checkpoint

Changed:
- New users start as `status="trial"` instead of 24-hour active access.
- Onboarding keeps language and level selection, then asks which course lesson to start: recommended first lesson or another lesson from the selected level.
- Free users can fully complete one selected `CourseLesson`; access to another lesson, next lesson, or level upgrade shows the subscription Mini App offer.
- Added `users.trial_course_lesson_id`, `trial_course_started_at`, `trial_course_completed_at`, `trial_quiz_explanation_used_at`, and `force_sub_required_at`.
- Required-channel checks are skipped until `force_sub_required_at` is set; the flag is set when a free user reaches `block_vocab_2` (`2-qism yangi so'zlar`). After that, existing required-channel middleware checks every free-user event. Paid approved users bypass this check.
- Course Mini App quiz results also set the checkpoint flag if the next step is `block_vocab_2`.
- Admin stats now show paid users by `payment_status="approved"` plus trial course started/completed, trial AI explanation, channel checkpoint, trial-to-paid, completed-to-paid, checkpoint-to-paid, and post-trial revenue metrics.

Preserved:
- Paid approved users still use the existing `AIUsageBudgetService` structure for text/photo/voice-related AI usage.
- Free text AI and photo AI remain daily-limit based; voice remains subscription-only.
- Existing course lesson internals stay intact: vocab, dialogue, block quizzes, grammar, homework, and Mini App result flow are not rewritten.

Risk:
- Existing old users with course progress but no `trial_course_lesson_id` may get their current lesson assigned as their one free trial lesson when they enter course mode.

Files touched:
- `app/bot/handlers/start.py`
- `app/bot/handlers/course.py`
- `app/bot/handlers/messages.py`
- `app/bot/middlewares/required_channel.py`
- `app/bot/handlers/required_channel.py`
- `app/bot/utils/i18n.py`
- `app/services/course_trial_service.py`
- `app/services/access_service.py`
- `app/services/course_miniapp_result_service.py`
- `app/services/study_miniapp_service.py`
- `app/db/models/user.py`
- `app/db/session.py`
- `alembic/versions/0038_add_user_trial_course_fields.py`

---

### 2026-06-12 — One-time onboarding tips and trial voice sample

Changed:
- Added `onboarding_tip_events` to queue contextual one-time bot tips per user.
- Course vocab/dialogue/grammar sections queue a 30-second tip; the scheduler sends it only if the user is still on that same course step.
- Normal text/photo usage can queue one-time photo and voice feature tips.
- Added `users.trial_voice_used_at`; trial users can try voice once, while paid approved users keep normal voice access.
- Course Mini App quiz results below 60% show an AI mistake-discussion button that sends the latest quiz context to `CourseTutorService` and edits the processing message into the AI explanation.

Files touched:
- `app/services/onboarding_tip_service.py`
- `app/db/models/onboarding_tip_event.py`
- `app/db/models/user.py`
- `app/bot/handlers/course.py`
- `app/bot/handlers/messages.py`
- `app/main.py`
- `alembic/versions/0039_add_onboarding_tip_events.py`

---

### 2026-06-19 — Direct AI message draft

Changed:
- QA text AI replies now call Telegram `sendMessageDraft` directly; no draft feature flag remains.
- New `MessageDraftService` tries Telegram `sendMessageDraft` first and falls back to the existing `ResponseEffect` loader or `sendChatAction("typing")`.
- Final AI replies still use the normal send message flow; draft is only a waiting effect.

Why:
- Allows testing Telegram draft-based AI typing UX without removing the existing emoji/progress loader.

Files touched:
- `app/services/message_draft_service.py`
- `app/bot/handlers/messages.py`
- `app/bot/handlers/commands.py`
- `app/config.py`
- `.env.example`

Risk:
- `aiogram==3.22.0` does not expose `sendMessageDraft`; raw Telegram HTTP is used only when the flag is enabled, and failures fall back safely.

Follow-up:
- Test `/draft_test` and one normal QA text question in Telegram.

---

### 2026-06-21 - Conversion funnel tracking and course-first recovery

Changed:
- Added append-only `conversion_funnel_events` table via `0046_add_conversion_funnel_events.py`.
- Canonical funnel events: `course_cta_seen`, `course_started`, `lesson_started`, `quiz_completed`, `ai_explanation_seen`, `homework_completed`, `paywall_seen`, `checkout_opened`, `payment_screenshot_submitted`, `payment_approved`, `payment_rejected`.
- Added `ConversionFunnelService`; event writes use a separate short transaction and should not block user flow if tracking fails.
- Admin stats now define Paid as `User.payment_status == "approved"` + `User.status == "active"` + `User.end_date > now`; old approved users are shown separately as Historical approved.
- Daily Practice completion now shows Course CTA first, Free QA second.
- QA daily limit now shows a course offer first with `📚 1-darsni bepul boshlash` and `💳 Obuna olish`, then existing required-channel/referral fallback.
- Trial first Mini App lesson keeps existing homework/completion flow; after the full quiz, non-paid users can receive one automatic AI explanation and a soft paywall teaser. Quiz completion itself does not mark the trial lesson completed.

Important:
- Rejected payment funnel event means admin reject callback succeeded. It is not a gateway failure or checkout abandonment signal.
- Prices, subscription plan logic, referral logic, payment approval rules, and Mini App auth were not intentionally changed.
- `course_pilot_events` remains pilot telemetry only; broad conversion stats use `conversion_funnel_events`.

Files:
- `app/db/models/conversion_funnel_event.py`
- `alembic/versions/0046_add_conversion_funnel_events.py`
- `app/services/conversion_funnel_service.py`
- `app/services/course_trial_value_service.py`
- `app/bot/utils/trial_value_flow.py`
- `app/bot/handlers/start.py`
- `app/bot/handlers/messages.py`
- `app/bot/handlers/course.py`
- `app/bot/handlers/payments.py`
- `app/bot/handlers/admin_payments.py`
- `app/bot/handlers/admin.py`
- `app/bot/handlers/commands.py`
- `app/main.py`
- `app/static/subscription.html`

Risk:
- Funnel events are append-only and may contain duplicate raw events; admin funnel uses unique telegram users per event to avoid over-counting repeated opens.
- Auto AI explanation adds one extra AI call only for non-paid users on lesson 1 full quiz, guarded by an `ai_explanation_seen` event check.

---

### 2026-06-23 - Course Mini App onboarding migration

Changed:
- Language selection now ends with two explicit choices: Course Mini App or the existing Telegram QA mode.
- Course onboarding is owned by the Mini App and stores level, goal, daily time, start point and timezone in `course_miniapp_profiles`.
- Start points are `lesson_1`, `continue` and `placement`; existing cross-level progress is never silently reset.
- Existing course users open `study.html` at their current lesson, while the legacy Telegram course flow remains the fallback if the WebApp message cannot be sent.
- Onboarding selection/completion analytics are server-backed and deduplicated.

Important:
- This migration does not change payment, subscription, referral or QA access rules.
- `Beginner` reuses HSK1 content; HSK4 renders through existing `hsk4a`/`hsk4b` assets.

Files:
- `app/services/course_miniapp_onboarding_service.py`
- `app/services/study_miniapp_service.py`
- `app/bot/handlers/start.py`
- `app/bot/handlers/course.py`
- `app/static/study.html`
- `app/static/study-v2.js`

---

### 2026-06-23 - Server-graded interactive lesson flow

Changed:
- Course Mini App lessons now load an authenticated canonical flow generated from existing `course_lessons` HSK material.
- Each flow contains 3-4 active words plus meaning, listening, sentence builder, word order, translation, pronunciation and quick-quiz cards; card order varies by lesson.
- Lesson completion requires every required card response and is graded again on the server. Client-supplied completion percentages are no longer accepted.
- Only a passing server result advances existing `CourseProgress`; homework is not a completion gate.
- Free lesson access uses `CourseMiniAppAccessService` entitlement and the existing assigned trial lesson. Payment/subscription rules were not changed.

Key files:
- `app/services/course_miniapp_lesson_flow_service.py`
- `app/services/course_miniapp_lesson_service.py`
- `app/services/study_miniapp_service.py`
- `app/main.py`
- `app/static/study.html`
- `app/static/study-v2.js`

---

### 2026-06-23 - Server-backed Test and Training

Changed:
- Placement and HSK1-HSK4 mock tests now use canonical questions generated from existing `course_lessons` material and are graded server-side.
- Listening, Writing and Characters training use the same HSK progression with skill filtering. Speaking continues to open AI Voice; Mistakes routes to the Mistake Engine area.
- Placement uses the separate `placement` free entitlement. Mock tests and skill training share the single `training_test` free entitlement.
- A free session is consumed when it starts; the same session can resume, but switching to another mock/training session is blocked after the one free use.
- Server records `test_started`, `test_completed`, `training_started` and `training_completed` events.

Key file:
- `app/services/course_miniapp_practice_service.py`

---

### 2026-06-24 — Referral `/start` onboarding resume fix

Changed:
- New users are now persisted with `learning_mode="onboard_lang"` until they choose language, then `learning_mode="onboard_mode"` until they choose Course/Oddiy mode.
- `/start` resumes incomplete onboarding instead of treating default `language="tj"` and `level="beginner"` as a completed setup.
- Referral payloads can attach for existing incomplete onboarding users, and duplicate referral rows are avoided by checking invited user first.
- Referral payloads also attach for existing unpaid users who do not already have a referrer. If such a user already has `questions_used >= 2`, the referral is activated immediately after attach.
- Existing pending referral rows are also recovered on `/start <referral_code>`: if the invited user has `questions_used >= 2`, the pending referral activates without waiting for another AI question.

Why:
- Referral links created/committed a user before onboarding finished, so later `/start` skipped language/mode selection and looked like the bot ignored the start command.
- Users who opened the bot first and came back through a referral link could lose the referral attribution.
- A user could enter via referral link and use the free QA limit, but still not count if their account looked like an already completed non-referred user before attach.
- A referral row could exist as `pending`, but after the invited user hit the free limit there might be no next successful AI question to trigger activation.

Files touched:
- `app/services/onboarding_service.py`
- `app/bot/handlers/start.py`
- `app/repositories/user_repo.py`
- `app/services/referral_service.py`
- `tests/test_onboarding_service.py`

Risk:
- No database schema, payment, subscription, or access rule changes. Existing completed users keep `learning_mode="qa"` or normal course entry behavior.

Follow-up:
- Smoke test with a clean Telegram user: open `https://t.me/<bot>?start=<referral_code>`, confirm language selection appears, then choose mode and verify the referral row is stored.

---

### 2026-06-29 — Feedback notifications to admin group

Changed:
- Bot feedback, subscription churn feedback, and release feedback ratings/comments now notify both configured admins and configured feedback notification chat IDs.
- `FEEDBACK_NOTIFY_CHAT_IDS` controls extra feedback recipients; `.env.example` documents it.

Why:
- Admin needs reviews, update ratings, and similar feedback visible in the team feedback group, not only private admin chats.

Files touched:
- `app/config.py`
- `app/services/admin_notify_service.py`
- `app/bot/handlers/release_feedback.py`
- `.env.example`
- `tests/test_admin_notify_service.py`

Risk:
- Feedback-only notification routing changed; payment review routing is unchanged.

Follow-up:
- Confirm the bot is a member/admin in the configured feedback group so Telegram accepts messages to that chat.

---

### 2026-06-29 — Course reminder goal and Mini App CTA update

Changed:
- Motivation reminders now support `lesson_unfinished`: if a user starts a lesson but does not finish it before the 20:00-21:30 local evening window, they get one reminder for that local day.
- Daily goal reminders now treat lesson/book-lesson completion as the goal signal instead of closing the goal on any small activity.
- Motivation reminder buttons open the Course Mini App directly, and Telegram course block keyboards include a Mini App button under the normal action row.

Why:
- Users who partly study but do not finish a lesson need a different nudge from users who did not start at all.
- Course CTA should reliably send users back to the Mini App without breaking the old callback-based Telegram lesson flow.

Files touched:
- `app/services/motivation_reminder_service.py`
- `app/services/notification_template_service.py`
- `app/db/models/course_miniapp_event.py`
- `app/bot/keyboards/course.py`
- `app/bot/keyboards/course_context.py`
- `app/bot/keyboards/course_miniapp.py`

Risk:
- No DB migration. The new once-per-day gate uses `course_miniapp_events` with `motivation_lesson_unfinished_sent`.
- More messages can be sent in the evening window, but the unfinished lesson reminder suppresses the daily/streak reminder in the same run to avoid stacking.

Follow-up:
- After deploy, verify one real user with an unfinished lesson receives only one evening reminder and every course block shows the Mini App button.

---

### 2026-06-29 — Challenge level-matched questions

Changed:
- Course Mini App HSK challenges now generate separate question sets for challenger and opponent based on each user's own HSK level.
- Challenge winners are decided by completion percentage, with duration used only as a tie-breaker.
- Legacy challenge payloads that stored one shared question list still work.

Why:
- Users at different HSK levels should compete fairly without one player getting questions too easy or too hard.

Files touched:
- `app/services/course_challenge_service.py`
- `tests/test_course_challenge_service.py`

Risk:
- Existing active challenge rows are backward compatible, but any malformed challenge payload returns a safe error instead of opening a broken duel.

Follow-up:
- Smoke test one challenge between two accounts with different `user.level` values and confirm both receive level-matched questions.

---

### hsk-data.js ikkiga bo'lindi — mashq sahifalari yuklanish tezligi

Changed:
- `app/static/hsk-data.js` (~2.8 MB) ikkiga ajratildi:
  - `hsk-words.js` (~170 KB) — faqat `WORDS`
  - `hsk-extra.js` (~2.7 MB) — `STROKES` + `EXAMPLES` + `HSK4_GRAMMAR`
- `course_v3_recognition.html`, `course_v3_pronunciation.html` va `course-v3.html`'dagi prefetch endi faqat `hsk-words.js` yuklaydi.
- `hsk-lugat.html` ikkalasini ham yuklaydi (unga `STROKES`/`EXAMPLES`/`HSK4_GRAMMAR` kerak).
- `hsk-data.js` va uning route'i saqlanib qoldi, lekin endi hech bir sahifa uni yuklamaydi.

Why:
- Mashq bo'limlari `WORDS`'dan boshqasini ishlatmasa ham, har ochilishda to'liq 2.8 MB JS'ni parse qilardi. Fayl keshlangan bo'lsa ham parse qayta bajariladi — telefonda bu har o'tishda sezilarli kechikish berardi. O'lchov (Mac, desktop): 49.9 ms → 4.8 ms parse; mobil qurilmada farq ancha kattaroq.

Files touched:
- `app/static/hsk-words.js`, `app/static/hsk-extra.js` (yangi)
- `app/static/course_v3_recognition.html`, `app/static/course_v3_pronunciation.html`, `app/static/course-v3.html`, `app/static/hsk-lugat.html`
- `app/main.py` (`/hsk-words.js`, `/hsk-extra.js` route'lari)
- `scripts/split_hsk_data.py` (yangi — qayta bo'lish uchun)

Risk:
- Past. Ma'lumot mazmuni bayt-bayt bir xilligi tekshirildi; UI/flow o'zgarmadi.
- MUHIM: mashq sahifalariga `hsk-data.js` script tegini qaytarib qo'ymang — bu regressiya bo'ladi. `WORDS` kerak bo'lsa `hsk-words.js` ishlating.
- `hsk-data.js` yangilansa, `python3 scripts/split_hsk_data.py` ni qayta yuriting va HTML'lardagi `?v=` raqamini yangilang (fayllar `immutable` keshlanadi).

---

### 2026-07-28 — Pomp HSK AI Desktop original loyihaga birlashtirildi

Architecture:
- `HSK AI bot` yagona canonical repository. Tauri v2 source `desktop/` ichida;
  Telegram bot, Mini App, backend, obuna, referral, progress va analytics bitta
  product/account tizimi bo'lib qoladi.
- Build artifactlar Git'ga kiritilmaydi; approved release storage/CDN'da
  saqlanadi.

Acquisition:
- Botning barcha shared `Profil` kirishlarida full-width `Kompyuter ilovasi`
  Web App CTA bor; u `tab=profile&desktop_download=1` bilan Mini App profilidagi
  download kartasini ochib, kartaga fokuslaydi. Alohida callback/download oqimi
  yaratilmagan — existing authenticated oqim qayta ishlatiladi.
- Mini App profil download kartasi daily goal'dan keyin ko'rinadi va 3 aniq
  o'rnatish qadamini UZ/RU/TJ ko'rsatadi. Release hali yo'q bo'lsa karta
  yashirilmaydi: platforma tugmalari disabled va `tez orada` holati ko'rinadi;
  profilni ochishning o'zi backend download request yaratmaydi.
- Mini App Mac/Windows bosilganda avval destination chooser ko'rsatadi:
  shu qurilmada ochish, AirDrop/Web Share, public linkni nusxalash yoki bekor
  qilish. Bekor qilish backend request yaratmaydi.
- Direct oqim fresh Telegram `initData` bilan backenddan tracked HTTPS
  `download_url` + safe `file_name` oladi. Share/copy faqat tokensiz,
  barqaror `/downloads/macos` yoki `/downloads/windows` `transfer_url`ni
  uzatadi; analytics `web_share`/`copy_link` transport bilan yoziladi.
- Mini App `openLink` orqali branded `/desktop-download` sahifasini ochadi;
  foydalanuvchi u yerdan `/downloads/macos` yoki `/downloads/windows` direct
  redirect bilan faylni oladi. Link bot chatiga yuborilmaydi va Mini App
  avtomatik yopilmaydi.
- Profile, home prompt, lesson-end promo va barcha shared ad/practice
  ekranlariga desktop CTA ulangan. Branded download landing telefonlarda ham
  Web Share/AirDrop, copy va manual-copy fallback beradi; tracked request token
  clipboard yoki share payloadga kirmaydi.
- Release fail-closed: repository default va `.env.example` signed real
  artifact URL'lari tayyor bo'lmaguncha `DESKTOP_DOWNLOADS_ENABLED=false`.
  Railway deployment env bu taskda tekshirilmadi yoki o'zgartirilmadi.

Desktop auth/security:
- Migration `0066_desktop_foundation` uch jadval qo'shadi:
  `desktop_link_requests`, `desktop_devices`, `desktop_sessions`.
- Desktop Telegram URL kodni oshkor qilmaydigan generic
  `?start=desktop_link` payload ishlatadi. Legacy code-bearing URL ham kodni
  avtomatik qabul qilmaydi: user desktop ekrandagi 8 belgili kodni bot chatiga
  qo'lda yuboradi, keyin platform/version/code ko'rsatilgan
  `Tasdiqlash / Bekor qilish` bosqichidan o'tadi.
- Bot FSM bitta manual-entry prompt saqlaydi va 5 ta noto'g'ri urinishdan keyin
  sessiyani yopadi. Desktop Telegram tugmasi ham bir link sessiyasida bir marta
  ochiladi; retry/new code oqimi uni qayta yoqadi.
- Link code single-use; device accountga bound; access token qisqa muddatli;
  refresh token rotate bo'ladi va OS credential store'da turadi.
- Analytics xatosi yaratilgan desktop session/token transactionini rollback
  qilmasligi uchun auth core avval commit qilinadi.
- Desktop auth JSON body 2 KiB bilan cap qilinadi; validation secretni echo
  qilmaydi va `no-store` qaytaradi.
- Public link-startni production scale'da yoqishdan oldin atomik global
  limiter, ingress body-size limiti, expired link/session cleanup va tracked
  download token expiry/consumption policy kerak.
- Online logout server session/device'ni revoke qiladi. Revoke paytida internet
  bo'lmasa ham native client local access/refresh credentiallarni albatta
  o'chiradi; serverdagi yetib bo'lmagan session normal TTL bilan tugaydi.

Desktop application:
- Dedicated frontend `desktop/ui`; Tauri oynasi `1180x780`, minimum
  `720x560`, strict CSP (`connect-src` faqat Tauri IPC).
- Desktop source versiyasi `1.3.0`: demo reference asosidagi premium shell
  `Bugun`, real course map, `Obuna`, `Profil` bo'limlariga ega; o'ng pastda AI
  launcher/drawer. Dars/progress serverdan olinadi, fake AI yoki fake course
  data productionda yo'q.
- Telegram link oqimi explicit:
  `auth status -> link start -> generic Telegram link -> user kodni qo'lda
  yuboradi -> bot approve/cancel -> poll -> bootstrap`. Webview polling
  secret/deep-link/tokenlarni ko'rmaydi.
- Bearer desktop course API:
  `/api/v3/desktop/course/map`,
  `/api/v3/desktop/course/lesson/{lesson_order}`,
  `/api/v3/desktop/course/complete`,
  `/api/v3/desktop/preferences/language`.
  Level, premium access, progress, XP va completion server-authoritative;
  completion event_id bilan idempotent.
- Bearer desktop subscription API:
  `/api/v3/desktop/subscription/overview`, `/quote`, `/submit`. Adapter canonical
  `SubscriptionMiniAppService` narx, chegirma, QR, pending payment va admin
  review logikasidan foydalanadi; user/amount/currency/mode clientdan olinmaydi.
- Desktop receipt PNG/JPEG/WebP bo'lishi, magic bytes mosligi va 8 MB limiti
  Python API hamda Rust IPC'da tekshiriladi. Access token webviewga berilmaydi;
  checkout attempt ID analytics uchun submitga uzatiladi.
- Faol paid user uchun renewal read-only: canonical activation qolgan muddatga
  qo'shmay, yangi muddat boshlagani sabab active subscription qayta sotilmaydi.
  Renewal semantics markaziy tuzatilmaguncha shu guardni ochmang.
- Mini App'dagi access parity saqlandi: bepul user 2 mini-darsni tugatadi,
  3-qismning yarmigacha `preview_half` ko'radi, keyin obuna yo'liga qaytadi;
  preview hech qachon completion/XP yozmaydi. Tugagan premium dars obuna
  tugagandan keyin review qilinsa ham duplicate sifatida ochiladi, yangi XP yo'q.
- Renderer checked-in Course v3'dagi barcha card type'larni qoplaydi. Noto'g'ri
  javob clientdan stable `material_ref` + selection sifatida keladi, trusted
  review materiali server lesson JSON'dan qayta quriladi.
- AI drawer optional verified local model packni yuklaydi va pinned llama.cpp
  orqali loopback-only streaming inference qiladi. Pack o'rnatilgach AI chat
  internetsiz ishlaydi; course/auth/subscription baribir online-first. Chinese
  TTS native runtime bo'lmasa webview/OS local speech fallbackni sinaydi.
- Localhost preview faqat explicit `?mock=1`; production fake data'ga fallback
  qilmaydi.
- Kelajak Google/email loginlari alohida user emas, shu ichki userga ulangan
  identity provider bo'lishi shart; aks holda obuna/progress bo'linadi.

Analytics:
- Direct funnel:
  `desktop_download_requested -> desktop_download_started ->
  desktop_download_link_clicked -> desktop_session_linked ->
  desktop_first_open`.
- Share/copy acquisition `desktop_download_requested ->
  desktop_download_started(transport=web_share|copy_link)` sifatida kuzatiladi;
  public transfer redirect token olmagani uchun fake install/click yozmaydi.
- Faqat authenticated `desktop_first_open` install hisoblanadi.
- Admin Mini App va bot stats desktop funnel/DAU/WAU/MAU/platform/version
  ko'rsatadi. Physical device hisobi session emas, server `device_id` bo'yicha.
- App versiyasi oshganda authenticated bootstrap idempotent
  `desktop_update_installed` eventini yozadi; admin stats o'rnatilgan update
  user/event sonini ko'rsatadi.

Release/update:
- Tauri updater bootda tekshiradi va faqat dars/AI/subscription ishlari bo'lmagan
  idle holatda signed update'ni avtomatik o'rnatib restart qiladi.
  `DESKTOP_UPDATES_ENABLED=false` public artifact va clean-machine updater testi
  o'tmaguncha o'zgarmaydi.
- GitHub Actions `desktop-v*` tag uchun universal macOS DMG/updater va Windows
  x64 NSIS EXE/updaterni parallel build qiladi, checksum/V4 signature'ni
  tekshiradi, immutable R2 objectlarni yozadi va `desktop/latest.json`ni oxirida
  atomik nashr qiladi.
- Updater V4 private key repodan tashqarida va password macOS Keychain'da.
  Workflow `TAURI_SIGNING_PRIVATE_KEY_V4` hamda
  `TAURI_SIGNING_PRIVATE_KEY_PASSWORD_V4` GitHub secretlarini ishlatadi. Secret
  qiymatlarni memory yoki Git'ga yozmang.

Brand:
- Canonical HSK AI panda assetlar:
  `app/static/assets/hsk-ai-avatar.webp`,
  `app/static/assets/hsk-ai-cover.webp` va desktop nusxalari.
- Close-up panda kichik brand/AI/OS iconlarda; full composition katta desktop
  promo visualda ishlatiladi. Real Telegram/user avatarlarini almashtirmang.
- Desktop UI ichida panda mascot kerak bo'lsa `desktop/ui/assets/panda-real.webp`
  ishlatiladi; user avatar slotlarida brand panda emas, Telegram avatar/initials
  ko'rsatiladi.
- Tauri `bundle.icon` PNG/ICNS/ICO fayllariga explicit ulangan; configdan
  olib tashlash Dock/installer icon regressiyasiga olib keladi.

Important files:
- `DESKTOP_IMPLEMENTATION_PLAN.md`
- `DESKTOP_AUTH_CONTRACT.md`
- `app/api/desktop_course.py`, `app/services/desktop_course_service.py`
- `app/api/desktop_download.py`, `app/services/desktop_download_service.py`
- `app/api/desktop_auth.py`, `app/services/desktop_auth_service.py`
- `app/db/models/desktop.py`, `alembic/versions/0066_desktop_foundation.py`
- `app/static/course_v3_data/desktop-download.js`
- `app/static/desktop-download.html`
- `app/services/desktop_update_service.py`, `app/api/desktop_update.py`
- `app/services/desktop_analytics_service.py`
- `.github/workflows/desktop-release.yml`
- `desktop/`

### 2026-08-08 — Desktop 1.2.0: content view CSS to'ldirildi, brend nomi "HSK AI"

- Root sabab: avvalgi sessiya `desktop/ui/js/app.js`'ni sezilarli kengaytirgan
  (Bugun/Kurs/Machq/AI Voice/Lug'at/Reyting/Profil uchun yangi markup), lekin
  mos CSS'ni yozmagan/commit qilmagan holda qoldirgan edi. Natijada 79 ta CSS
  klass umuman stilsiz edi — eng ko'zga tashlanadigani: avatar `<img>`
  elementlarida class yo'qligi sabab mascot rasm original o'lchamida butun
  ekranni bosib turardi (Machq, AI Voice, Reyting, Profil bo'limlarida bir xil
  rasm). Bu 1.2.0 release'ga shu holda kirib ketgan edi.
- Tuzatish: `desktop/ui/css/workspace.css`'ga mavjud dizayn tokenlaridan
  (`--ink`, `--muted`, `--line`, `--cream`, `--jade`, `--red` va h.k.) hamda
  mavjud `.card-panel`/`.avatar` naqshlaridan foydalanib to'liq CSS qo'shildi.
  Yangi dizayn g'oyasi kiritilmadi — faqat mavjud tizim to'ldirildi.
  Responsive breakpoint (`860px`)ga yangi grid/flex bo'limlar ham qo'shildi.
- Barcha 237 ishlatiladigan CSS klass avtomatik skript bilan tekshirildi;
  qasddan qoldirilgan 5 tasi (`lesson-node-pinyin`, `lesson-node-translation`,
  `rail-toggle`, `refresh-button`, `today-lesson-hero`) mavjud generic
  selectorlar orqali allaqachon qoplanadi.
- Brend nomi "Pomp HSK AI" → "HSK AI" ga o'zgartirildi: desktop ilova UI
  (`index.html`, `i18n.js` — uz/ru/tj, `tauri.conf.json` productName/title/
  longDescription, `lib.rs` product_name), bot tasdiqlash xabarlari
  (`desktop_auth.py`, 3 til), yuklab olish sahifasi va Mini App promo
  matnlari (`desktop-download.html/js`, `admin.html`). Mos testlar
  (`test-contract.mjs`, `lib.rs` ichidagi Rust test, `test_desktop_ui_preview.py`)
  ham yangilandi.
- Ataylab O'ZGARTIRILMAGAN (real risk sabab): Tauri `identifier`
  (`com.pomp.hskai`) — allaqachon o'rnatilgan foydalanuvchilar uchun Keychain/
  updater identity buziladi; Cargo/npm paket nomlari (`pomp-hsk-ai`,
  `pomp-hsk-ai-desktop`); CI/R2 installer fayl nomlari
  (`Pomp-HSK-AI_x.x.x_...`) va `DEFAULT_FILE_NAMES` backend fallback —
  o'zgartirish yana Railway/R2 URL qayta sozlashni talab qiladi;
  `window.PompDesktopDownload` JS global nomi — bir nechta static HTML
  fayl shu nomga bog'liq.
- Versiya 1.2.1 ga ko'tarildi (`package.json`, `Cargo.toml`, `tauri.conf.json`,
  `Cargo.lock`). Yangi EXE/DMG qurish va qayta o'rnatish shart — bu server
  tomonidan avtomatik yangilanmaydigan client-side o'zgarish.

Not complete:
- Universal Mac DMG va Windows EXE hali CI'da chiqarilmagan; GitHub auth/secrets
  va R2 bucket/custom-domain config kerak.
- Universal DMG Intel/Apple Silicon Mac'da va EXE clean Windows VM'da o'rnatish,
  keyin `1.3.0 → 1.3.1` real automatic-update testidan o'tmagan.
- Apple/Windows pullik signing yo'q; `$0` rejada macOS/SmartScreen warning
  instruktsiyasi saqlanadi. `DESKTOP_DOWNLOADS_ENABLED=false` va
  `DESKTOP_UPDATES_ENABLED=false` qoladi.
- Offline course cache/sync va conflict-safe progress queue keyingi bosqich.
- Google OAuth/passwordless email va account-link/merge himoyasi keyingi
  ixtiyoriy identity bosqichi.

### 2026-08-09 — macOS AI runtime arm64 slice manbadan quriladi, minimum 13.3

Changed:
- `desktop-release.yml` macOS jobi endi llama.cpp'ning tayyor arm64 arxivini
  ishlatmaydi. arm64 slice pinned commit `11924d4c` (tag `b10223`) dan
  `-DCMAKE_OSX_DEPLOYMENT_TARGET=13.3` bilan quriladi; Intel slice avvalgidek
  SHA-256 tekshirilgan tayyor arxivdan olinadi.
- Runtime'dagi har bir binary uchun `minos <= 13.3` hard gate qo'shildi va
  Intel arxividagi har bir dylib universal runtime'da borligi tekshiriladi.
- `tauri.conf.json` `macOS.minimumSystemVersion`: `11.0` -> `13.3`.
- macOS job timeout 45 -> 90 daqiqa.
- Rust contract testlari yangi pinlarga moslandi: `local_ai.rs` dagi workflow
  contract ro'yxati va `lib.rs` dagi `minimumSystemVersion` asserti.

Why:
- llama.cpp o'z arm64 release'ini `macos-26` runnerida deployment target'siz
  quradi. Natijadagi binary `_posix_spawn_file_actions_addchdir` symbol'ini
  so'raydi va macOS 26 dan past hamma tizimda `Abort trap: 6` beradi. Shu sabab
  `desktop-v1.3.1` release'i `Stage pinned universal local AI runtime`
  qadamida exit 134 bilan yiqildi. Upstream Intel build'i esa allaqachon
  13.3 target'ida quriladi -- yangi minimum shundan olindi.
- Avvalgi `minimumSystemVersion: 11.0` haqiqatga mos emas edi: Intel slice
  allaqachon macOS 13.3 talab qilardi.

Files touched:
- `.github/workflows/desktop-release.yml`
- `desktop/src-tauri/tauri.conf.json`
- `desktop/src-tauri/src/local_ai.rs`
- `desktop/src-tauri/src/lib.rs`

Risk:
- macOS 11 va 12 foydalanuvchilari qo'llab-quvvatlanmaydi. Bu ongli qaror.
- Manbadan build macOS jobiga ~10-20 daqiqa qo'shadi va yangi yiqilish nuqtasi
  (`LLAMA_BUILD_BORINGSSL=ON` Go talab qiladi, macos-14 runnerida mavjud).
- arm64 uchun ta'minot zanjiri kafolati "SHA-256 pinned arxiv" o'rniga
  "pinned tag + commit SHA assertion" ga o'zgardi.
- Windows tomonida o'zgarish yo'q: Windows binary'larida deployment target
  tushunchasi yo'q va o'sha job muvaffaqiyatli o'tgan. DMG/EXE parity qoidasi
  buzilmaydi, farq OS cheklovidan kelib chiqadi.

Follow-up:
- `1.3.1` va `1.3.2` publishgacha yiqilgani uchun qayta chiqarilmaydi; tag
  ko'chirilmaydi, tuzatish `1.3.3` bilan ketadi.
- Download sahifasiga "macOS 13.3+" talabi hali qo'shilmagan; qo'shilsa
  RU/TJ/UZ uchtasida bo'lishi shart.

---

### 2026-08-09 — Desktop AI Voice real ovozli suhbatga ulandi

Changed:
- Desktop'dagi "AI Voice" ekrani statik karta edi: faqat AI chatga o'tish
  tugmasi va joriy darsni TTS bilan o'qish. Endi u haqiqiy ovozli suhbat:
  mikrofondan yozib olish, STT, AI javobi, ichki tuzatish, jonli transkript
  va serverdan kelgan yakuniy natija.
- Yangi Bearer adapter `app/api/desktop_voice.py` mavjud
  `VoicePracticeService` ni chaqiradi. Yangi biznes-mantiq yozilmadi:
  limit, byudjet, paid gating, tuzatish, xatolarni yozish va XP
  o'zgarishsiz canonical servisda qoladi.
- Endpointlar (Mini App'dagi `/api/voice-practice/*` bilan bir xil servis):
  `GET  /api/v3/desktop/voice/status`,
  `POST /api/v3/desktop/voice/session/start`,
  `POST /api/v3/desktop/voice/message`,
  `POST /api/v3/desktop/voice/pronounce`,
  `POST /api/v3/desktop/voice/session/end`.
- Rust'da 5 ta yangi named command: `desktop_voice_status`,
  `desktop_voice_session_start`, `desktop_voice_message`,
  `desktop_voice_pronounce`, `desktop_voice_session_end`. Path allowlist,
  audio signature tekshiruvi va body limitlari subscription adapteridagi
  naqsh bo'yicha.

Why:
- Voice Practice backend allaqachon Mini App uchun ishlab turardi; desktop
  unga ulanmagani uchun mahsulot demo va'dasidan orqada edi. Ikkinchi STT
  yo'li qurish "bitta akkaunt, bitta backend" tamoyilini buzardi.

Files touched:
- `app/api/desktop_voice.py` (yangi), `app/main.py`
- `desktop/src-tauri/src/lib.rs`, `desktop/src-tauri/Info.plist` (yangi)
- `desktop/ui/js/voice.js` (yangi), `app.js`, `bridge.js`, `i18n.js`,
  `preview-mock.js`, `css/workspace.css`, `ui/test-contract.mjs`

Risk:
- Audio webview'dan Rust'ga IPC orqali base64 data URL sifatida o'tadi
  (multipart emas), chunki webview'da tarmoq yo'q — CSP `connect-src ipc:`
  o'zgarmadi. Chegara 5 MB, servisdagi `MAX_AUDIO_BYTES` bilan bir xil.
- **Platforma farqi:** macOS WKWebView `audio/mp4`, Windows WebView2
  `audio/webm` yozadi. Uchala qatlam (JS, Rust, Python) ikkalasini ham
  qabul qiladi; bittasini olib tashlash bitta OS'da AI Voice'ni jimgina
  buzadi. Contract test buni ushlab turadi.
- macOS'da `NSMicrophoneUsageDescription` bo'lmasa OS ilovani birinchi
  `getUserMedia` da o'ldiradi. Info.plist qo'shildi, lekin **haqiqiy Mac'da
  hali sinalmagan**. Bu matn hozircha faqat inglizcha — OS dialogi bo'lgani
  uchun RU/TJ/UZ lokalizatsiyasi `InfoPlist.strings` talab qiladi.
- Bepul foydalanuvchi cheklovi (`FREE_TOTAL_SESSIONS = 1`) desktopda ham
  paywall sifatida ko'rsatiladi; obuna mantig'iga tegilmadi.

Follow-up:
- Toza Mac va toza Windows VM'da mikrofon ruxsati oqimini sinash.
- `desktop_voice_pronounce` backend va Rust'da tayyor, lekin UI'da hali
  ishlatilmayapti — talaffuz baholash keyingi bosqichda ulanadi.
- `⌘F` `desktop/ui/index.html` da hardcoded: Windows'da ham Mac belgisi
  ko'rinadi. `⌘K` platformaga qarab tuzatilgan, `⌘F` yo'q — parity fix kerak.
- Eski voice CSS (`.voice-shell`, `.voice-stage`, `.voice-avatar-wrap`,
  `.voice-microphone-state`, `.voice-mic-button`) endi ishlatilmaydi;
  alohida tozalash taskida olinadi.

---

### 2026-08-09 — Desktop Lug'at, Praktika va Reyting real backendga ulandi

Changed:
- **Reyting**: yangi `app/api/desktop_rating.py` mavjud
  `CourseGamificationService.leaderboard()` ni chaqiradi.
  `GET /api/v3/desktop/rating/leaderboard?tz=`. Endi desktopda haqiqiy
  haftalik liga jadvali bor. `telegram_id` javobdan olib tashlanadi — UI uni
  ishlatmaydi va bu yagona shaxsiy ma'lumot edi.
- **Praktika**: yangi `app/api/desktop_practice.py` mavjud
  `CourseMiniAppPracticeService` ni chaqiradi.
  `POST /api/v3/desktop/practice/start` va `/complete`. 7 ta mashq turi:
  placement, mock va training × (characters, listening, pronunciation,
  pinyin, writing). Savol banki, bepul kunlik gate, baholash va xatolarni
  yozish canonical servisda qoladi. `free_feature_limit_reached` 403 sifatida
  qaytadi va UI'da paywall ko'rsatiladi — crash emas.
- **Lug'at**: darslararo to'liq lug'at. 1247 so'z, 799 misol va 1055 ieroglif
  uchun chiziq ma'lumoti `desktop/ui/data/` ga bundle qilindi. Qidiruv, filtr
  (Hammasi/Saqlangan/Takrorlash), HSK daraja filtri, chiziqlar tartibi
  animatsiyasi (Hanzi Writer 3.7.3, `desktop/ui/vendor/`).
  **CDN ishlatilmaydi** — `charDataLoader` lokal `STROKES` dan o'qiydi,
  shuning uchun CSP o'zgarmadi va internetsiz ishlaydi. `strokes.js` (2.5 MB)
  faqat so'z detali ochilganda dynamic import bilan yuklanadi.
- **EXAMPLES 3 tilga to'ldirildi**: `app/static/hsk-extra.js` dagi 799 ta misol
  jumlasining `m.ru` va `m.tj` maydonlari bo'sh edi — hammasi xitoychadan
  tarjima qilindi. `你` uchun ты/ту registri ishlatildi. `zh`, `uz`, `pos` va
  `STROKES` tegilmadi. Bu umumiy fayl, shuning uchun **Mini App lug'ati ham**
  rus va tojik tarjimalarini oladi.
- `⌘F` parity xatosi tuzatildi: `index.html` da hardcoded edi, Windows'da
  Mac belgisi ko'rinardi. Endi `⌘K` kabi platformaga qarab almashadi.

Why:
- Uchala servis ham Mini App uchun allaqachon ishlab turardi; desktop
  ularga ulanmagani uchun ekranlar bo'sh yoki soxta edi. Ikkinchi
  implementatsiya "bitta akkaunt, bitta backend" tamoyilini buzardi.

Files touched:
- `app/api/desktop_rating.py`, `app/api/desktop_practice.py` (yangi), `app/main.py`
- `app/static/hsk-extra.js` (faqat EXAMPLES qatori)
- `desktop/ui/js/vocabulary.js`, `practice.js` (yangi)
- `desktop/ui/data/vocabulary.js`, `data/strokes.js`,
  `vendor/hanzi-writer.js` (yangi, generatsiya qilingan)
- `desktop/src-tauri/src/lib.rs`, `desktop/ui/js/{app,bridge,i18n,preview-mock}.js`
- `desktop/ui/css/workspace.css`, `desktop/ui/index.html`
- `desktop/THIRD_PARTY_NOTICES.md`, `desktop/licenses/LICENSE-HANZI-WRITER-MIT.txt`

Risk:
- **Saqlangan so'zlar DB'da emas**: `desktop_vocabulary_state/save` komandalari
  ularni ilova ma'lumotlar papkasidagi `vocabulary.json` ga yozadi. Ya'ni
  telefondagi Mini App bilan **sinxronlanmaydi**. Sinxronizatsiya kerak bo'lsa
  yangi jadval va migratsiya kerak — bu ataylab qilinmadi. Yozish
  temp-fayl + rename orqali, ya'ni crash ro'yxatni kesib qo'ymaydi.
- Bundle hajmi ~2.9 MB oshdi (strokes 2.5 MB + words 370 KB). Bu lokal asset,
  tarmoqqa ta'siri yo'q, lekin installer kattalashadi.
- `EXAMPLES` tarjimalari AI tomonidan qilingan, professional tarjimon emas.
  Jumlalar HSK1-3 darajasida sodda; xato topilsa `hsk-extra.js` dan tuzating.
- Praktika savollarida `answer_index` clientga yuboriladi (Mini App'dagi kabi).
  Bu mavjud xulq — o'zgartirilmadi, lekin ballni client hisoblay olishini
  bilib qo'ying; yakuniy natijani baribir server qayta hisoblaydi.

Follow-up:
- Rust hali kompilyatsiya qilinmagan: `cargo fmt --check`, `cargo clippy
  --locked --all-targets -- -D warnings` Mac'da ishlatilishi shart.
- Python testlari ishlatilmagan (venv macOS binary).
- Lug'atdagi "Takrorlash" navbati hozircha shunchaki ro'yxat — SRS
  (intervalli takrorlash) algoritmi yo'q.
- `desktop_voice_pronounce` backend/Rust/bridge tayyor, UI'ga ulanmagan.

---

### 2026-08-10 — Desktop profili demo tartibiga keltirildi, maqsad onboardingga ko'chdi

Changed:
- Profil ekrani `hsk-ai-mac-demo_4.html` ni **blok-bablok takrorlaydi**:
  hero (avatar, ism, HSK·%·streak, chiplar, panda) + maqsad kartasi; taklif
  morph tugmasi (TG/WA/⌘C/QR tray) + sinxronlash kartasi; progress bo'limi
  (4 stat karta, haftalik bar chart, HSK darajalar, zaif joylar, aniqlik
  trendi, insight chiplari); sozlamalarning ikki kartasi.
- **`soonBlock()` naqshi:** ma'lumoti yo'q blok demo'dagi to'liq ko'rinishini
  saqlaydi, ichidagi barcha boshqaruvlar `disabled` qilinadi va **ustiga
  borilganda** (`:hover` / `:focus-within`) "Tez orada" pardasi chiqadi.
  Raqam hech qachon o'ylab topilmaydi — o'rniga `NO_VALUE = "—"`.
  Veyl ostidagilar: hero chiplari, maqsadning kunlik satri, sinxronlash,
  TG/WA/QR ulashish, o'rganilgan so'z va daqiqa kartalari, HSK darajalar,
  zaif joylar, aniqlik trendi, insight chiplari, butun bildirishnomalar
  kartasi, kurs darajasi / audio avtoijro / pinyin qatorlari, onboardingning
  2-bosqichi.
- **Maqsad endi faqat onboardingda so'raladi.** Modal ikki bosqichli
  (demo'dagidek): 1) maqsad turi — `conversation`, `hsk`, `study`;
  2) Smart Widget tanishtiruvi (veyl ostida). `enterWorkspace` dan keyin
  `goal.configured === false` bo'lsa modal o'zi ochiladi; sozlamalardagi
  "Qayta sozlash" qatori uni qo'lda ochadi. Profil kartasi tanlovni faqat
  ko'rsatadi.
- Maqsad sxemasi `minutes: i64` dan `kind: String` ga o'tdi.
  `MIN/MAX_GOAL_MINUTES` o'rniga `GOAL_KINDS` whitelisti (Rust'da ham,
  `bridge.js` da ham). Fayl nomi `daily-goal.json` o'zgarmadi.
- Til tanlash tugmalar ro'yxatidan demo'dagi `<select>` ga o'tdi.
- **Demo'da yo'q, lekin desktopda kerak bo'lgan bloklar** ("Akkaunt va
  ilova": obuna boshqaruvi, yangilanishni tekshirish, chiqish, versiya)
  profil ekranining **eng pastiga**, alohida bo'lim sifatida ko'chirildi.
  Hech qanday funksiya yo'qolmadi.
- `.tag` uchun CSS umuman yo'q edi — profildagi har bir pill oddiy matn
  bo'lib ko'rinardi. Demo'dagi pill uslubi (`.tag`, `.tag.green`, `.tag.red`)
  qo'shildi.
- ~80 ta yangi i18n kaliti RU/TJ/UZ uchtasida qo'shildi; ishlatilmay qolgan
  `interfaceSection`, `inviteLink`, `insightsTitle`, `notificationsSettingsBody`
  o'chirildi. Yangi contract test uchala tilning kalit to'plami aynan bir
  xilligini tekshiradi.
- O'lik CSS tozalandi: `.coming-soon*`, `.profile-activity`, `.language-list`,
  `.profile-stat.is-soon`.

Why:
- Ikkita joyda (profil + onboarding) maqsad so'ralishi foydalanuvchini
  chalkashtirardi va desktopda umuman onboarding yo'q edi — maqsad tanlanmasa
  ilova hech narsa so'ramasdan ishlayverardi.
- Demo'dagi bloklarni soxta raqam bilan to'ldirish "haqiqiy ma'lumot"
  tamoyilini buzardi; uzuq ramka mavjud `coming-soon` naqshini qayta ishlatadi.

Files touched:
- `desktop/src-tauri/src/lib.rs` (`desktop_goal_state/save`, `GOAL_KINDS`)
- `desktop/ui/index.html`, `js/app.js`, `js/bridge.js`, `js/i18n.js`,
  `js/preview-mock.js`, `css/workspace.css`, `test-contract.mjs`

Risk:
- **Eski `daily-goal.json` migratsiya qilinmaydi.** Faylda faqat `minutes`
  bo'lgani uchun `configured: false` qaytadi va onboarding hamma mavjud
  foydalanuvchida bir marta qayta ochiladi. Bu ongli qaror — kunlik daqiqa
  tushunchasi butunlay olib tashlandi.
- To'lov, obuna va DB mantig'iga tegilmadi — faqat Akkaunt bloki DOM'da
  pastroqqa ko'chdi.
- Onboarding "Keyinroq" yoki Escape bilan yopilsa maqsad saqlanmaydi va
  keyingi ishga tushishda modal qaytadi. Bu ataylab.
- Haftalik bar chart balandliklari **daqiqa emas**: server faqat kun faol
  bo'lgan-bo'lmaganini beradi, shuning uchun ustun to'la yoki bo'sh. Teg
  "N / 7 kun" deb yozadi, "82 min" emas.
- `soonBlock` ichidagi boshqaruvlar `disabled` + `tabIndex = -1` +
  `aria-hidden`, ya'ni klaviatura bilan ham ularga tushib bo'lmaydi. Agar
  keyinchalik blok jonlantirilsa, `soonBlock()` chaqiruvini olib tashlash
  yetarli.
- macOS/Windows farqi yo'q: barcha o'zgarish UI qatlamida. Widget bosqichi
  matni ataylab platformaga bog'liq emas ("ish stoliga", "Mac'ga" emas).

Follow-up:
- 2026-08-11 tekshiruvlari o'tdi: `node --test desktop/ui/test-contract.mjs`
  22/22, `cargo fmt --check`, `cargo clippy --locked --all-targets --
  -D warnings`, va localhost mock preview bilan Playwright smoke.
- Playwright screenshotlari `output/playwright/` ostida: onboarding 1/2,
  profil top qismi, invite tray, progress, account, RU/TJ/UZ til holatlari.
- Demo'dagi ishlamaydigan progress barlar real natijadek ko'rinmasligi uchun
  no-data fill'lar `is-placeholder` stubga tushirildi.
- Demo'ning 2-bosqichidagi `<details>` bloki (WidgetKit Swift yo'riqnomasi)
  ko'chirilmadi — u ishlab chiquvchi uchun yozilgan izoh, mahsulot UI'si emas.
- **Smart Widget hali ishlamaydi.** Haqiqiy WidgetKit extension pullik Apple
  Developer akkaunti, App Group entitlement va notarization talab qiladi;
  hozirgi `signingIdentity: "-"` (ad-hoc) bilan extension umuman yuklanmaydi,
  Windows'da esa `nsis` bundle uchun ekvivalenti yo'q. Kelishilgan yo'l —
  o'rniga menu bar / tray panelini qurish, **alohida vazifa sifatida**.

---

### 2026-08-11 — Qolgan desktop bo'limlari demo-parityga yaqinlashtirildi

Changed:
- Today, Course, Practice, AI Voice, Vocabulary, Rating va Subscription ekranlari
  `hsk-ai-mac-demo_4.html` kompozitsiyasiga moslashtirildi.
- Real API oqimlari saqlandi: kurs ochish, lesson progress, practice start,
  voice persona/mic/session, vocabulary save/review/stroke, rating board va
  subscription quote/upload logiciga tegilmadi.
- Backendda ma'lumoti yo'q metrikalar soxta raqam bilan to'ldirilmadi:
  study minutes, word count, rating promotion/history/missions va offline
  course save bloklari `soonBlock()` / `NO_VALUE` orqali ajratildi.
- Vocabulary detail endi alohida word-card ko'rinishiga ega: stroke tartibi,
  darsdagi misol, save/review action va mavjud AI drawerga prompt yuborish bor.

Files touched:
- `desktop/ui/js/app.js`, `desktop/ui/js/practice.js`,
  `desktop/ui/js/vocabulary.js`, `desktop/ui/js/voice.js`,
  `desktop/ui/js/subscription.js`, `desktop/ui/js/i18n.js`,
  `desktop/ui/css/workspace.css`.

Risk:
- O'zgarishlar user-facing layout qatlamida katta, shuning uchun desktop
  responsive regressiya riski bor. Contractlar API/payment/voice/practice/vocab
  oqimlarini himoya qiladi, lekin real device visual QA release oldidan kerak.

Follow-up:
- Agar demo'dagi hozir veyl ostida turgan bloklar jonlantirilsa, backend
  endpointlar kerak: daily study minutes, learned word count, rating league
  thresholds/history/missions, offline course package state.

---

### 2026-08-11 — Desktop native API allowlist AI Voice'ni bloklamasligi tuzatildi

Changed:
- `desktop/src-tauri/src/lib.rs` dagi fail-closed `api_url()` allowlistiga
  Desktop AI Voice endpointlari qo'shildi:
  `/api/v3/desktop/voice/status`, `/session/start`, `/message`, `/pronounce`,
  `/session/end`.
- Shu omissiondan ta'sirlangan desktop practice (`/practice/start`,
  `/practice/complete`), rating (`/rating/leaderboard?tz=`) va referral
  (`/referral/overview?tz=`) pathlari ham allowlistga qo'shildi.
- Transport unit testi yangi desktop endpointlarni va query-injection reject
  holatlarini tekshiradi.

Why:
- Frontend va backend AI Voice tayyor edi, lekin native Rust transport
  `api_url()` allowlistida voice pathlari yo'qligi uchun Tauri command backendga
  chiqmasdan `desktop_api_operation_not_allowed` qaytarardi. UI buni umumiy
  "Ma'lumot olinmadi" xatosi sifatida ko'rsatgan.

Files touched:
- `desktop/src-tauri/src/lib.rs`

Risk:
- Past. Network boundary hali fail-closed: faqat aniq endpointlar va bounded
  timezone querylari ochildi; identity/admin querylari reject bo'lib qoladi.

Follow-up:
- Yangi DMG/EXE buildda AI Voice, Practice, Rating va Referral ekranlarini real
  auth bilan smoke-test qilish.

---

### 2026-08-11 — Android 1.1 native Mini App parity foundation

Changed:
- Android version `1.1.0`ga ko'tarildi va native appga Mini Appdagi asosiy
  yo'nalishlar qo'shildi: Mashq/training/test, Xatolarim review, AI Voice
  recorder/session, Profil dashboard, Reyting, Referral va obuna statusi.
- Yangi bearer adapter `app/api/android_features.py` mavjud canonical servislarni
  chaqiradi: `CourseMiniAppPracticeService`, `CourseMistakeService`,
  `VoicePracticeService`, `CourseGamificationService`, `ReferralService` va
  `StudyMiniAppService`. Yangi progress/payment/account logic yozilmadi.
- Desktop practice adapterdagi transport bug ham tuzatildi: canonical service
  `selected_index` kutadi, adapter endi `selected`ni shu fieldga map qiladi.

Why:
- Android 1.0.0 faqat auth/kurs/lesson poydevor edi; user kursdan tashqari
  mashq, xato takrori, AI Voice va account/gamification qiymatini ko'rmasdi.

Files touched:
- `app/api/android_features.py`, `app/main.py`, `app/api/desktop_practice.py`,
  `android/app/src/main/java/com/pomp/hskai/**`,
  `android/app/src/main/res/values*/strings.xml`,
  `android/app/build.gradle.kts`.

Risk:
- Payment/subscription activation o'zgarmadi. Google Play Billing hali tashqi
  blocker: Play product ID/service-account/release keystore yo'q, shuning uchun
  Android hozir obuna statusini ko'rsatadi, lekin native purchase qilmaydi.

Follow-up:
- Real Android qurilmada Telegram link, practice complete, mistake review,
  microphone permission + AI Voice message, logout/relink smoke-test.
- Play Billing verify endpoint va client purchase flow alohida task.

---

### 2026-08-11 — Desktop 1.3.4 release bump

Changed:
- Desktop release version `1.3.4` ga ko'tarildi: npm package/lock, Cargo,
  Tauri config va preview mock versionlari bir xil qilindi.

Why:
- Demo-parity desktop UI update alohida `desktop-v1.3.4` tag orqali release
  workflowga yuborilishi kerak.

---

## 11. Known Problems

### Problem 1
Problem:
- Desktop public release tashqi R2/GitHub secret konfiguratsiyasiz fail-closed.

Suspected cause:
- R2 bucket/public domain/API token va updater V4 password GitHub secreti hali
  productionda to'liq tasdiqlanmagan.

Status:
- Open — kod tayyor; external credentials va clean-machine release test kerak.

---

## 12. Next Planned Work

Priority 1:
- R2/GitHub release konfiguratsiyasini tugatish va `desktop-v1.3.0` chiqarish.

Priority 2:
- Clean Mac/Windows install hamda real updater smoke-test.

Priority 3:
- Public flaglarni faqat yuqoridagi tekshiruvlar o'tgach yoqish.

---

## 13. Required Environment Variables

Do not write real values here.

Required:
- `BOT_TOKEN`
- `DATABASE_URL`
- `OPENAI_API_KEY`
- `ADMIN_IDS`

Optional:
- `FEEDBACK_NOTIFY_CHAT_IDS`

---

## 14. AI Assistant Instructions

Any AI coding assistant working on this project must:

1. Read this file before changing code.
2. Understand the current architecture before editing.
3. Make minimal changes.
4. Preserve working flows.
5. Never store secrets in this file.
6. Update this file only after important changes.
7. Do not write small cosmetic changes here.
8. If changing database/payment/subscription logic, explain the risk.
9. If unsure, inspect the code before guessing.
10. Do not rewrite this file completely unless explicitly requested.
