# NEXTATION — HSK AI kelgusi ishlar

Bu fayl loyiha egasi kelajakda bajarish uchun saqlagan g‘oya va vazifalarning yagona ro‘yxati. Admin PWA, yangi server, avtomatik eslatma yoki doimiy monitoring talab qilinmaydi.

**Ochiq repo:** bu fayl hammaga ko‘rinadi. Tokenlar, shaxsiy ma'lumotlar va maxfiy biznes g‘oyalarini yozmang.

## Agentlar uchun qoidalar

1. Har yangi ish sessiyasida `AGENTS.md`, `AI_RULES.md` va `PROJECT_MEMORY.md` bilan birga ushbu faylni o‘qing.
2. Egasi yangi topshiriqni aniq bermagan bo‘lsa, ochiq vazifalarni qisqacha aytib, qaysisini boshlashni taklif qiling. Joriy topshiriq aniq bo‘lsa, uni bo‘lmang; faqat tegishli yozuvlarni kontekst sifatida ishlating.
3. Yangi g‘oyani faqat egasining aniq «saqlab qo‘y» yoki boshqa tasdig‘idan keyin yozing. Qisqa maqsad, scope, asosiy xavf va qabul mezonini qayd eting; takror yozuv yaratmang.
4. Taklif va qayd **implementatsiyaga ruxsat emas**. Egasi ruxsat bermasa, ishni boshlamang.
5. Vazifa boshqa agentga topshirilganda uni o‘chirmang: `IN_PROGRESS` holatiga o‘tkazing. Natija tayyor bo‘lgach `VERIFY` ga o‘tkazing. Tekshiruv muvaffaqiyatli va egasi yopishga rozi bo‘lgach, yozuvni faol ro‘yxatdan olib tashlang. Git tarixi qaydni saqlaydi.
6. `main` dagi branch protection, CI va egasi ruxsati talablariga amal qiling. Lokal agent GitHub’dagi eng yangi ro‘yxatni ko‘rishi uchun repozitoriyni sinxronlashtirish kerak.

## Statuslar

- `PLANNED` — tasdiqlangan, hali boshlanmagan.
- `IN_PROGRESS` — egasi ruxsat bergan, amalga oshirilmoqda.
- `VERIFY` — bajarilgan, tekshiruv/yakuniy tasdiq kutilmoqda.

## Kelgusi vazifalar

### NXT-001 — HSK AI optimizatsiyasi (PWA + Android + Backend)
- Status: IN_PROGRESS
- Added: 2026-11-18
- Priority: current
- Goal: HSK AI ilovasining tezligi va ishlash samaradorligini yaxshilash.
- Scope: Avval kelishilgan umumiy PWA + Android + Backend optimizatsiyasi; [talablar](docs/PERFORMANCE_BACKEND_PWA_GOALS_REQUIREMENTS.md) va [performance qoidalari](docs/PERFORMANCE_PWA_PROGRESSIVE_LOADING.md) bo‘yicha. Desktop rivojlantirish hozircha scope'dan tashqarida.
- Risks / open questions: Tezlikni yaxshilash auth, kurs, progress, Pro va to‘lov oqimlarini buzmasligi kerak. Realizatsiya bosqichi egasining 2026-11-18 dagi xabariga asoslangan; aniq bajarilgan qismlar va testlar bu qaydda hali tasdiqlanmagan.
- Acceptance: Tegishli performance talablari, platformalararo regression testlari va real o‘lchovlar tekshirilgach `VERIFY` bosqichiga o‘tkaziladi.
- Implementation: Reja — [OpenSpec perf-pwa-android-backend](openspec/changes/perf-pwa-android-backend/tasks.md). 2026-11-22: PWA chetdan svayp 2 bo‘lim orqaga qaytishi va lug‘at so‘z sahifasi shaffofligi tuzatildi (1.1–1.2), Android lug‘at scroll joyi saqlanadi (2.1), doimiy guard Android va svayp regressiyasini qamraydi (5.1). Qolgani: root-tab svayp ko‘rinishi (egasi tanlovi), qatlamlar auditi, Android start/jank, `lesson/complete`/`lesson/start`/`pwa/profile` backend yo‘llari, real o‘lchovlar va qurilma QA.


### NXT-002 — AI Voice: ustozdek tabiiy gapirish va uzilishlarni kamaytirish
- Status: PLANNED
- Added: 2026-11-18
- Priority: normal (NXT-001 dan keyin, egasi o‘zgartirmasa)
- Goal: HSK AI ovozli mashg‘ulotlari haqiqiy xitoy tili ustoziga o‘xshab tabiiy, izchil, tez va uzilishlarsiz o‘tishi; o‘quvchi gapiga moslashib, xatosini foydali tuzatishi.
- Scope: Avval PWA va Android Live Voice kechikishi, gap o‘rtasidagi audio uzilishlari, turn-taking, uzilib-qayta ulanish va audioni buferlashni o‘lchash; keyin ustoz roli va javob uzunligi bo‘yicha prompt/UX yaxshilash; shundan keyin joriy Live modelni kuchliroq muqobil bilan bir xil ssenariylarda solishtirish. Model almashishi oldindan qabul qilingan qaror emas.
- Risks / open questions: Uzilishlarning ildiz sababi hozircha isbotlanmagan; server, tarmoq, VAD, audio playback va model kechikishini ajratish kerak. Kuchliroq model narx yoki kechikishni oshirishi mumkin. Joriy Live kod konfiguratsiyasi production konfiguratsiyasini tasdiqlamaydi.
- Acceptance: Real qurilmada davomli nutq, javob boshlanish kechikishi, audio uzilishlar, noto‘g‘ri interruptlar, qayta ulanish, pedagogik sifat va bir suhbat narxi solishtirilib, regressiya testlari o‘tgach `VERIFY`ga o‘tadi.
- Implementation: Hozircha faqat rejalashtirilgan; kod o‘zgartirilmagan.


## UI/UX rejadagi tugallanmagan ishlar (2026-11-18 main auditi)

Manba: [HSK_AI_UI_UX_IMPROVEMENTS.md](HSK_AI_UI_UX_IMPROVEMENTS.md); kod ko‘rilgan `main` HEAD: `5bbbf707ad5874284d1a509561abb54ceee48055`.
Bu yozuvlar **takror implementatsiya qilish buyrug‘i emas**. Boshlashdan avval hozirgi `main`, tegishli OpenSpec va loyiha qoidalarini qayta tekshiring. `VERIFY` — asosan amalga oshirilgan, ammo real qurilma/rollout tekshiruvi tugamagan; `PLANNED` — kelishilgan yakuniy UX hali bajarilmagan (qisman mavjud kod qayta ishlatiladi).

### NXT-003 — UIUX-007: Adaptive Learning'ni qurilmada tasdiqlash va rollout
- Status: VERIFY
- Added: 2026-11-18
- Priority: UI/UX rejadagi 1
- Goal: Oddiy dars ichida avvalgi xatolar bo‘yicha shaxsiy tekshiruvlarni xavfsiz ishga tushirish.
- Implemented: Server, PWA va Android oqimlari `main`ga PR #325 orqali qo‘shilgan; `openspec/changes/course-adaptive-lesson-engine/tasks.md` dagi 1–3.5 bandlari bajarilgan deb qayd etilgan.
- Remaining: Shu checklistdagi **3.6** — Safari/Home Screen PWA, Android Play/Direct, HSK 2.0/3.0, UZ/RU/TJ real qurilma QA; **3.7** — shadow → allowlist → percent rollout va egasining production flag yoqish qarori.
- Risks / open questions: Feature flag default OFF; XP, oddiy dars natijasi, xatolar va progressga aralashmasin. Real qurilma va production yoqilishi tekshirilmagan.
- Acceptance: Device QA natijalari, regressiya va xavfsiz rollback isboti; egasi tasdig‘idan keyin yopilsin.
- Implementation: [OpenSpec tasks](openspec/changes/course-adaptive-lesson-engine/tasks.md), PR #325.

### NXT-004 — UIUX-008: Rasmli talaffuz kartochkalarini tasdiqlash va rollout
- Status: VERIFY
- Added: 2026-11-18
- Priority: UI/UX rejadagi 2
- Goal: O‘tilgan xitoycha so‘zni aniq rasm/emoji orqali aytib tekshiradigan kartochkalarni ishonchli ishlatish.
- Implemented: Server reja, PWA/Android deck va kuratsiya qilingan mapping `main`ga PR #326 va #328 orqali qo‘shilgan. `lesson_picture_words.json`ni qayta yaratish shart emas.
- Remaining: `openspec/changes/course-interactive-flashcards/tasks.md` **3.5** — Android parser/ViewModel unit test, static gates, Direct debug build va emulator; **4.1** — iPhone PWA + Android real ovoz sinovi; **4.2** — allowlist → percent rollout va staging'da flag-off rollback. O‘rganilgan so‘zlar, aniq tasvir semantikasi va HSK darajalari qamrovi ham real darslarda tekshirilsin.
- Risks / open questions: Noto‘g‘ri emoji/so‘z ma'nosi, mikrofondagi aniqlash xatosi, Android emoji glyph va mavjud talaffuz kvotasi; tugallanmagan device acceptance.
- Acceptance: Checklistdagi ochiq bandlar sinov dalili bilan yopilib, egasi tasdiqlasin.
- Implementation: [OpenSpec tasks](openspec/changes/course-interactive-flashcards/tasks.md), PR #326 / #328.

### NXT-005 — UIUX-012: Checkout'dan chiqishda aniq 20% taklif UX'ni yakunlash
- Status: PLANNED
- Added: 2026-11-18
- Priority: UI/UX rejadagi 3
- Goal: Eligible foydalanuvchi checkout'ni yopmoqchi bo‘lsa bir marta markaziy 20% taklif berish, rad etgach esa keyingi X'da bevosita chiqish.
- Existing: `app/services/pwa_exit_offer_service.py` va Android Lava'da 20% exit-offer ning qismi bor; PWA inline checkout X hozir to‘g‘ridan-to‘g‘ri qaytishga ulanadi, Android Direct manual X ham bevosita yopadi.
- Remaining: PWA va Android qo‘llaydigan checkout yo‘llarida bir xil bir-attempt X → offer → X dismiss → keyingi X exit oqimi; qadamli Back va checkout tanlovlari saqlansin; real server quote bilan chegirma aktivatsiyasi; owner tasdiqlagan **never paid OR never redeemed discount** tarixiy eligibility va repeat-attempt semantikasi, invoice/paid/refund test matritsasi; RU/TJ/UZ va accessibility.
- Risks / open questions: Hozirgi 24 soatlik/consumed offer modeli talab etilgan eligibility bilan bir xil emas. `OR` iqtisodiy jihatdan avval to‘lagan, lekin chegirma ishlatmaganlarga ham 20% berishi mumkin — owner qarori o‘zgarmasdan `AND`ga aylantirilmasin. Play payment policy, double offer va pending invoice saqlansin.
- Acceptance: [UIUX-012](HSK_AI_UI_UX_IMPROVEMENTS.md) dagi 1–8 qabul ssenariysi va server-paid tasdiqlari o‘tsin.
- Implementation: Mavjud checkout/offer kodi; yangi to‘liq UX hali tasdiqlanmagan.

### NXT-006 — UIUX-002: Alohida XP va Streak ekranlari
- Status: PLANNED
- Added: 2026-11-18
- Priority: UI/UX rejadagi 4
- Goal: Kurs tepasidagi 🔥 Streak va 💎 XP ko‘rsatkichlaridan har biri alohida **to‘liq ekran** ochsin.
- Existing: Backend real XP/streak hisoblaydi, onboarding'da 7/14/30/50 kunlik maqsad mavjud, profilda haftalik kalendar bor. Android `CourseScreen.kt` statistik chip'lari faqat son ko‘rsatmoqda.
- Remaining: PWA + Android full-screen Streak (serverdagi oy kalendari, haqiqiy shaxsiy target, o‘zgartirish) va XP (jami/kun/hafta, tekshirilgan award qoidalari, mavjud bo‘lsa xavfsiz event tarixi) ekranlari; kurs indikatorlari bosiladigan bo‘lsin; haqiqiy ma'lumot bo‘lmagan davr to‘ldirib ko‘rsatilmasin.
- Risks / open questions: XP valyuta emas; server anti-dedupe va timezone saqlansin. Oldingi `showStreakScreen` level-up ko‘rinishi yangi target detail ekranining o‘rnini bosmaydi.
- Acceptance: [UIUX-002](HSK_AI_UI_UX_IMPROVEMENTS.md) 1–6 mezonlari UZ/RU/TJ va real PWA/Android'da o‘tsin.
- Implementation: Rejalashtirilgan; tayyor progress servislari qayta ishlatilsin.

### NXT-007 — UIUX-003: Smart Dictionary filter va akkauntga bog‘langan saqlangan so‘zlar
- Status: PLANNED
- Added: 2026-11-18
- Priority: UI/UX rejadagi 5
- Goal: Lug‘at avtomatik joriy HSK 2.0/3.0 versiyasini olsin, yagona level qatori va ⭐ Saved filtri bo‘lsin.
- Existing: PWA `hsk-lugat.html`da versiya/level ikkita filter, Android `DictionaryScreen.kt`da versiya bottom sheet va `DictionaryViewModel.kt`da qo‘lda filtrlash bor; tayyor iboralarda mahalliy favorites mexanizmi mavjud.
- Remaining: Joriy account/course versiyasi asosida default `All levels`, versiyani oddiy lug‘at ekranida qayta tanlamaslik; har so‘zga ☆/★; saved filter; PWA↔Android account-scoped sync uchun minimal xavfsiz API/store (agar mavjud bo‘lmasa), stable word identity va user-switch xavfsizligi.
- Risks / open questions: Tayyor iboralar localStorage'ini so‘zlarga server authority deb ko‘chirmang. HSK 2.0/3.0 kesishadigan so‘zlar yo‘qolmasin.
- Acceptance: [UIUX-003](HSK_AI_UI_UX_IMPROVEMENTS.md) bo‘yicha qayta login, ikki qurilma, HSK switch, qidiruv va empty/error tekshiruvi.
- Implementation: Yakuniy UX hali kodda yo‘q.

### NXT-008 — UIUX-004: Tayyor iboralarni yig‘iladigan audio kartochkalarga o‘tkazish
- Status: PLANNED
- Added: 2026-11-18
- Priority: UI/UX rejadagi 6
- Goal: Tayyor iboralar default yopiq: faqat hanzi + ☆/★ + 🔊 + chevron; bosilganda pinyin, tarjima, kategoriya, kichik copy.
- Existing: `hsk-gaplar.html` va Android `ReadyPhrasesScreen.kt`da iboralar, qidiruv va favorites ishlashi yozilgan, ammo hozir pinyin/tarjima doimo ko‘rinadi, hammasi collapsed emas va 🔊 har kartada yo‘q.
- Remaining: Bir vaqtning o‘zida faqat bitta kartani ochish, alohida save/audio harakatlari, Chinese-only TTS'ni mavjud servis orqali tekshirish, audio loading/play/stop/error va UZ/RU/TJ/VoiceOver/TalkBack.
- Risks / open questions: Ovoz xizmati narxi, PWA playback ruxsati, Android audio lifecycle va skroll tezligi; mavjud favorites va qidiruv regressiyasi bo‘lmasin.
- Acceptance: [UIUX-004](HSK_AI_UI_UX_IMPROVEMENTS.md) da aniq berilgan yopiq/ochiq ko‘rinish va qurilma testlari.
- Implementation: Asosiy iboralar funksiyasi tayyor, UX o‘zgarishi rejalashtirilgan.

### NXT-009 — UIUX-005: Profilni ixchamlashtirish, dublikat bloklarni olib tashlash
- Status: PLANNED
- Added: 2026-11-18
- Priority: UI/UX rejadagi 7
- Goal: PWA va Android profilda bitta haqiqiy Pro holati/CTA, bitta aniqlik bloki, haftalik streak, bitta «100 dars» achievement va do‘stlar bo‘lsin.
- Existing: Ikkala client'da profil, accuracy, haftalik kalendar va achievement'lar mavjud. Lekin PWA `renderProfile()`da alohida Pro link, «30 kun» dublikati va promo root; Android profilida Pro CTA, achievements va promo carousel alohida qo‘shiladi.
- Remaining: Tasdiqlangan UIUX-005 tartibiga moslashtirish; dublikat «30 kun» va takror Pro CTA'larni olib tashlash; Free/Trial/Temporary/Pro state va haqiqiy ma'lumotni saqlash; Liquid Glass pastki panel va safe-area'ga tegmaslik; yangi UIUX-002 detail ekranga ulash.
- Risks / open questions: Checkout, notification, settings, account va scrolling yo‘qolmasin. UIUX-002 tayyorlanishi bilan mos bog‘lash.
- Acceptance: [UIUX-005](HSK_AI_UI_UX_IMPROVEMENTS.md) profil acceptance va client parity, barcha access state'lar tekshirilsin.
- Implementation: Mavjud profil kodini minimal qayta joylash; final UX hali to‘liq qilinmagan.

### NXT-010 — UIUX-009: Ikkinchi darajali ikonkalarning ortiqcha fonlarini tozalash
- Status: PLANNED
- Added: 2026-11-18
- Priority: UI/UX rejadagi 8
- Goal: PWA va Android lesson/course/practice/profile da utility ikonkalarning ikki qavat kartochka, qalin doira, takroriy border/dekor fonlarini bir xil qoida asosida kamaytirish.
- Existing: Alohida ekranlarda minimalistik o‘zgarishlar bor, ammo [UIUX-009](HSK_AI_UI_UX_IMPROVEMENTS.md) dagi **ilova bo‘ylab tekshirilgan yagona cleanup** uchun tugallangan acceptance dalili topilmadi.
- Remaining: Aniq screenshot/component inventari, faqat ortiqcha dekorni olib tashlash, touch target va focus/contrast/VoiceOver/TalkBack saqlanishi, PWA/Android visual regression.
- Risks / open questions: Primary CTA va Liquid Glass pastki navigatsiyani bekor qilmang; hamma ikonkalardan fonni ko‘r-ko‘rona olib tashlamang.
- Acceptance: Katta ekranlarda izchil dizayn, mos contrast/press/focus/safe area sinovlari.
- Implementation: Vizual QA talab qilinadi; avtomatik universal CSS almashtirish emas.


### NXT-011 — PWA JavaScript incident'larini aniqroq guruhlash (monitoring collision)
- Status: PLANNED
- Added: 2026-11-21
- Priority: high (diagnostika ishonchliligi; joriy release'ni shoshilinch o‘zgartirish uchun ruxsat emas)
- Goal: Bir xil `/iphone-pwa/course` sahifasidagi **turli** `js_uncaught` / `js_rejection` xatolarini bitta incident sifatida noto‘g‘ri birlashtirmaslik; aynan bir xato qaytarilganda esa dedup va occurrence hisobini saqlash.
- Observed: `app/static/course_v3_data/hsk-diagnostics.js` barcha course sahifasi JS xatolarini `feature_code=lessons`, `site_code=course_v3` bilan yuboradi; `app/services/monitoring/intake.py` fingerprint'ni `platform+feature_code+failure_code+site_code` dan hisoblaydi. Natijada boshqa-boshqa JS xatolari bir incident'ga tushishi mumkin. Admin'dagi 2026-11-16 → 2026-11-21 (2 occurrence, 2 account) bitta asl xato qaytganini isbotlamaydi. U yerda exception nomi, sabab va kod manzili qayd etilmagan; ildiz sababni taxmin bilan to‘ldirmang.
- Scope: Avval haqiqiy `DiagnosticReceipt` sample/retention va JS reporter→intake→Admin zanjirini audit qiling, optional source `error_name`, `reason_code`, allowlisted `asset_id`/line yo‘qolish sababini isbotlang. Keyin minimal, server-owned va privacy-safe incident identity strategiyasini tanlang: mavjud qat'iy allowlist bilan tasdiqlangan exception/source dalili bo‘lsa turli xatolar ajralsin; yetarli dalil bo‘lmasa bu holat `unknown/aggregated` sifatida aniq ko‘rsatilsin, soxta aniqlik qo‘shilmasin. `asset_version`/build o‘zgarganda bir xil xatoni keraksiz bo‘lib yubormaslik, eski incident/receipt, reopen/resolve, dedup, rate-limit, Push va Analytics kontraktlarini saqlash shart. PWA ustuvor; Android va Telegram monitoring regressiyasi ham tekshirilsin.
- Risks / open questions: Raw exception message, raw stack, URL, user content, token yoki PII'ni fingerprint, DB, Admin yoki loglarga qo‘shmang. Client yuborgan arbitrary fingerprint'ga ishonmang. Bir xil location'dagi turli runtime sabablar, source-map yo‘qligi va iOS/WebKit inline/cross-origin xatolari uchun aniq fallback siyosatini hujjatlashtiring. Diagnostika sample'ining yo‘qligi production rollout/migration yoki allowlist sababmi — tekshirishsiz taxmin qilmang.
- Acceptance: (1) Bitta PWA route'dagi ikki alohida, allowlist orqali ishonchli ajratiladigan JS exception ikkita incident hosil qiladi; (2) bir xil xato qayta kelganda bitta incident va to‘g‘ri occurrence count; (3) metadata yetishmaganda xavfsiz va ochiq `unknown` holat; (4) resolved/reopened, old-version compatibility, retry/dedup, Admin detail va Apple Push spam cheklovlari buzilmaydi; (5) WebKit/Chromium + backend integration/CI testlari, production'ga chiqishdan oldin staging/device acceptance.
- Implementation: Hozircha faqat navbatga yozildi; kod o‘zgartirilmagan, CI/deploy o'tkazilmagan. Tegishli manbalar: [monitoring talablari](docs/monitoring/REQUIREMENTS.md), [context](docs/monitoring/MONITORING_CONTEXT.md), [PR #317](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/pull/317).



### NXT-013 — Android Widget Events: takrorlanuvchi HTTP 422 va telemetriya navbati bloklanishi
- Status: VERIFY (kod PR #351 da; production 4xx/422 trendini deploydan keyin solishtirish qoldi)
- Added: 2026-11-22
- Priority: high (Android widget/notification telemetriyasining ishonchliligi; asosiy dars/to‘lov serveri nosozligi deb talqin qilinmasin)
- Goal: Android'dan `POST /api/v3/android/events` ga yuboriladigan haqiqiy event'lar qat'iy backend allowlist'iga mos kelsin; noto‘g‘ri eski event boshqa to‘g‘ri event'larni navbatda bloklamasin.
- Confirmed cause in code (2026-11-22 `main`): `android/app/src/main/java/com/pomp/hskai/MainActivity.kt:645` kunlik Widget taklifini ko‘rsatganda `android_widget_daily_prompt_viewed` ni enqueue qiladi; `app/api/android_events.py`dagi `AndroidEventRequest.event_name` Literal allowlist'ida ham, `app/db/models/course_miniapp_event.py` dagi `COURSE_MINIAPP_EVENT_NAMES` registry'da ham bu nom yo‘q. Shunday payload backend validatsiyasidan **422** bilan rad etiladi. `android/app/src/main/java/com/pomp/hskai/widget/WidgetCoordinator.kt` `flushEvents()` xatoda `break` qilib, rad etilgan elementni acknowledgement qilmaydi; navbat saqlangani sabab takroriy 422 va keyingi valid event'larning tiqilishi xavfi bor (`WidgetStore.kt`dagi max queue 32). Bu haqiqiy kod-kontrakt nomuvofiqligi; ammo aniq bitta production 422 so‘rovining body/event nomi logda yo‘q.
- Production evidence: 2026-11-21T18:06:46Z dagi `/api/v3/android/events` `422` (Android `okhttp/4.12.0`); 20–21 noyabr loglarida bu endpoint bo‘yicha avval ham ko‘p 422 bor. Audit paytida oxirgi 24 soat HTTP metrikasida **47 ta POST: 46 ta 4xx, 1 ta 2xx** qayd etildi; har bir 4xx aynan shu event'dan kelganini yoki ularning barchasi 422 ekanini **isbotlangan deb yozmang**.
- Scope / fix gate: Avval current `main` va real deployed Android versiyalari, endpoint 422 response validation details (PII/token saqlamasdan), event ishlab chiqaruvchilar, queue retry tartibi va analytics consumer'larini qayta tekshiring. Minimal fix sifatida tasdiqlangan `android_widget_daily_prompt_viewed` ni backend schema va canonical analytics registry'da mos ravishda ro‘yxatga oling; agar nom va ma'no kontrakti boshqacha ekanligi aniqlansa, avval manbani tuzating. Android queue'da **faqat tasdiqlangan permanent invalid** event boshqalarni bloklamasligi uchun xavfsiz drop/quarantine/ack siyosatini o‘rnating; transient 5xx/network, 401/403 auth, rate-limit va owner/device isolation'ni ko‘r-ko‘rona discard qilmang. Eski ilovalardan allaqachon saqlangan event'lar va yangi server bilan backward compatibility'ni hisobga oling.
- Risks / open questions: User/account spoofing, server-side allowlist, dedupe (`device+event_id`), event UUID, queue max 32, navbatdagi tartib, user activity/DAU metrikalarini sun'iy oshirmaslik, widget onboarding/notification, Android Play/Direct versiyalari va privacy-safe logging saqlansin. Kundalik prompt view'ni passiv observation sifatida hisoblash kerakmi, degan savolni analytics semantikasi bilan tasdiqlang; bu avtomatik `last_active_at` yangilash degani emas.
- Acceptance: (1) `daily_prompt_viewed` qat'iy auth/owner-bound API orqali **200** va DB'da to‘g‘ri event yozadi; (2) unauthorized/forged/unknown event va ortiqcha field'lar rad etilishda davom etadi; (3) valid qayta yuborish bitta yozuv sifatida dedupe bo‘ladi; (4) oldingi invalid item boshqa valid event'ni abadiy bloklamaydi, navbat tiklanadi va transient xatolar yo‘qotilmaydi; (5) backend `tests/test_android_events_api.py`, Android widget queue/coordinator unit testlari, analitika contract va Android CI + production release kuzatuvlari bilan tasdiqlansin. 4xx/422 trendi oldin/keyin bir xil oynada solishtirilsin.
- Implementation: PR #351 (egasi 2026-11-22 da ruxsat berdi). Backend nomni allowlist, `COURSE_MINIAPP_EVENT_NAMES` va coverage registry'ga qo‘shdi; event passiv (`last_active_at` yangilanmaydi). Android `flushEvents()` faqat `desktop_request_invalid`/`desktop_request_too_large` javobini olgan event'ni navbatdan olib tashlaydi, qolgan xatolar qayta yuboriladi. Qolgan tekshiruv: deploydan keyin `/api/v3/android/events` 4xx ulushini oldingi 24 soat bilan solishtirish.

### NXT-014 — Ochilish effekti va Pro panda komponentlarini mavjud joylarga ulash
- Status: PLANNED (komponentlar tayyor, PR #348; ulash egasining alohida ruxsati bilan)
- Added: 2026-11-23
- Priority: normal
- Goal: Tayyor, hozircha ulanmagan vizual komponentlarni haqiqiy ekranlarga joylash: "Knot Thread" ochilish effekti (`app/static/assets/brand/hsk-launch-mark.{js,css}`, Android `core/design/components/HskLaunchMark.kt`), Pro panda + halo + uchqunlar + oltin nur (`app/static/assets/characters/hsk-pro-panda.{js,css}`, Android `feature/limit/ProPanda.kt`, `Modifier.hskProGlint()`), umumiy Pro/Trial ranglari (`assets/brand/hsk-pro-theme.css`, `core/design/ProColors.kt`).
- Scope: (1) PWA inline Pro oynasidagi `pandaSvg()` ni `HSKProPanda.render()` ga almashtirish va CSS'ni `_PWA_INLINE_PRO_HTML` ga qo‘shish; (2) Android `SectionLimitOverlay.kt` va Trial intro (`LiOnboardingChoices.kt`) ga `ProPanda` va `ProColors` ni qo‘yish, literal hex ranglarni tokenlarga almashtirish; (3) Pro faollashgan (server tasdiqlagan) lahzada `celebrate` + uchqunlar, Pro kartochkada bir martalik oltin nur; (4) ochilish effektini Golden Logo o‘rniga qo‘yish — alohida qaror: ovoz/vibratsiya vaqti va `tests/test_launch_feedback_contract.py` ikkala platformada birga yangilanadi, Mini App'ga tegilmaydi (faqat `html.hsk-pwa-browser` + Android). Narx, trial berish, access, matn o‘zgarmaydi.
- Risks / open questions: Golden Logo ovoz/haptic sinxroni; splash birinchi ekranni kechiktirmasligi (`docs/PERFORMANCE_PWA_PROGRESSIVE_LOADING.md`); `course-v3.html` Mini App bilan umumiy; content-addressed `?v=` va i18n reviewed blob qayta anchorlanadi; reduced-motion; Android kodi CI'da kompilyatsiya qilinadi.
- Acceptance: PWA (Chromium + WebKit) va Android'da real ekran screenshotlari, reduced-motion holati, `tests/test_launch_mark_pro_panda_contract.py` "not wired" tekshiruvi ulangan holatga moslab yangilanadi, Pro/Trial e2e va Android CI o‘tadi; `Analytics Impact` / `Monitoring Impact` bahosi.
- Implementation: Komponentlar va ulash yo‘riqnomasi — `docs/design/LAUNCH_MARK_AND_PRO_PANDA.md`, PR #348.

<!-- Yozuv namunasi (vazifa emas):

### NXT-XXX — Qisqa nom
- Status: PLANNED
- Added: YYYY-MM-DD
- Priority: normal
- Goal: Kutilgan natija
- Scope: Kiritiladigan va kiritilmaydigan ishlar
- Risks / open questions: ...
- Acceptance: Qanday tekshiriladi
- Implementation: PR yoki commit havolasi (agar mavjud bo‘lsa)

Birinchi haqiqiy vazifa qo‘shilganda "Hozircha saqlangan vazifa yo‘q." satrini olib tashlang.
-->
