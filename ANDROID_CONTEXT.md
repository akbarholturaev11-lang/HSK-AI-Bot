# Android — AI uchun kontekst

Bu fayl yangi chat boshlanganda AI kontekstni tez tiklashi uchun. Jarayon
(release qanday chiqariladi) — alohida faylda: `ANDROID_RELEASE_CHECKLIST.md`.

Batafsil tarix `PROJECT_MEMORY.md` da, sanalar bo'yicha. Bu yerda faqat
hozirgi holat va hali ochiq muammolar.

---

## 1. Ilova nima va qayerda

Native Kotlin/Compose klient, `android/` papkasida. Bot, Mini App, macOS va
Windows bilan **bir xil backend**, bir xil Telegram akkaunt, bir xil obuna va
progress. Kirish — Telegram orqali ulash kodi bilan (`LinkScreen`).

**Ikkita flavour, va bu farq muhim:**

| | `direct` | `play` |
|---|---|---|
| Kanal | bot, sayt, Telegram | Google Play |
| Tashqi to'lov yo'li | bor | **yo'q** |
| O'zini yangilash | bor | **yo'q** |

Farq runtime flag emas, **alohida source set**: `src/direct/` va `src/play/`.
Ya'ni Play build'da u kod umuman **kompilyatsiya qilinmaydi**, yashirilgan emas.
Google ikkalasini ham taqiqlaydi, shuning uchun shunday.

`android/tools/check_flavor_parity.py` ikkala flavour bir xil nomlarni bir xil
parametrlar bilan e'lon qilishini majburlaydi — `src/main` ularni qaysi
build'da ekanini bilmay chaqiradi.

## 2. Hozirgi holat

- Versiya: `android/app/build.gradle.kts` tepasidagi `appVersionName` /
  `appVersionCode`. **Har release'da `appVersionCode` +1 bo'lishi SHART** —
  yangilanish faqat shu raqamni solishtiradi.
- Imzo kaliti: `~/.pomp-hskai/pomp-hskai-release.jks`, parol shu papkadagi
  `MUHIM-OQING.txt` da. Repodan tashqarida. Yo'qolsa yangilanish chiqmaydi.
- Tarqatish: bot orqali (APK chatga tushadi) + R2 dagi fayl.
  `hsk-ai-releases` bucket, `android/v<versiya>/`, public base
  `https://pub-9b135bd734b04a5e9fe059a4dfd7d804.r2.dev`.
- Yo'l bitta: bot profilidagi «📱 HSK AI ilovalari» → Mini App profilidagi
  karta (`?tab=profile&desktop_download=1`, karta fokuslanadi) → Android
  chipi (`POST /api/miniapp/event` → `android_apk_to_chat`) → Mini App
  yopiladi, APK chatga tushadi. `/android` buyrug'i va eski xabarlardagi
  `android_app:get` tugmasi ham ishlayveradi. Saytdagi (`/desktop-download`)
  Android tugmasi esa faylni to'g'ridan-to'g'ri yuklaydi — u R2 linkini talab
  qiladi.
- Yangilanishdan xabar berish (faqat `direct`): ilova ochilganda va kuniga bir
  marta fonda `…/android-update/check` so'raladi (`UpdateWatch`). Har release
  uchun **bitta** bildirishnoma (`app_updates` kanali, `UpdateNotices`), va
  `versionCode` farqi ≥ 2 bo'lsa tab paneli ustida yopib bo'lmaydigan qator
  (`AppUpdateBanner`). Bitta release qoldirilsa — faqat profildagi karta.
- Release avtomati: `.github/workflows/android-release.yml` (qo'lda ishga
  tushiriladi). 2026-09-20 holatiga ko'ra **to'rt marta muvaffaqiyatli
  o'tgan**, hammasi `main` dan. Ya'ni imzo va R2 sirlari GitHub'da sozlangan
  va ishlaydi. Release faqat `main` dan chiqariladi: manifest versionCode
  orqaga ketishini rad etadi, shuning uchun boshqa branch'dan chiqarilgan
  release keyingi `main` release'ini bloklaydi.
- Play Market: yo'q. Akkaunt ham ochilmagan.

## 3. HOZIR OCHIQ MUAMMOLAR

### 3.1 ~~Mashq savollari buzuq~~ — TUZATILDI 2026-09-15

`PracticeScreen.kt` uch joyda `question.sentence.ifBlank { question.audioText }`
yozardi. Ya'ni tinglash savolida javob ekranga chiqardi («Eshiting va to'g'ri
javobni tanlang» + 您 yozilgan holda), gapsiz savolda esa hech nima chiqmasdi.

Endi Mini App qoidasi qo'llanadi (`course-v3.html:4014, 4979`): **`audio_text`
bo'lsa — bu tinglash savoli**, karnaycha ko'rsatiladi va ovoz avtomatik
chalinadi, matn **hech qachon** ko'rsatilmaydi. Server ovozi ishlatiladi
(`playReviewAudio` → `/api/v3/android/tts`), chunki UZ/TJ telefonlarida xitoy
ovozi ko'pincha yo'q.

`ListeningQuestionTest` buni mixlab qo'ydi: 您 ekranda faqat bitta variant
sifatida uchraydi, ikkita bo'lsa — xato qaytgan.

### 3.2 Mini App va ilova bitta akkauntda boshqa-boshqa narsa ko'rsatadi

Bir foydalanuvchi, bir payt, ikki klient:

| | Mini App | Android |
|---|---|---|
| Kunlik maqsad | 45 / **40** XP | 45 / **50** XP |
| Qoldi | **−5** | 5 |
| Liga | **朱雀** | **Bronze** |
| Holat | Sayohat | Bepul rejim |

Uchta alohida sabab:

**(a) ~~Kunlik maqsad sinxronlanmaydi~~ — TUZATILDI 2026-09-15.** Server
profilda `daily_goal_xp` saqlaydi va Mini App uni o'qib-yozardi; Android esa
faqat telefon ichida saqlardi va hech qachon yubormasdi. Endi:

- `AndroidStudyPreferencesRequest` va `set_study_preferences` `daily_goal_xp`
  qabul qiladi va Mini App bilan **bitta setter**ga beradi
  (`CourseMiniAppProfileService.set_daily_goal_xp`), ya'ni ikkalasi boshqacha
  qisqartira olmaydi.
- Android kurs xaritasi kelganda `studySetup.dailyGoalXp` ni lokal
  DataStore'ga ko'chiradi — lokal qiymat endi manba emas, **oyna**.
- Maqsad tanlanganda serverga yuboriladi (`chooseDailyGoalXp`).
- `DailyGoal.CHOICES` Mini App bilan tenglashtirildi: `[20,30,40,50,80]`.
  Ilgari `[10,20,30,50]` edi — **40 ni tanlashning iloji yo'q edi**.
- `DailyGoal.sanitize` endi ro'yxat emas, serverning chegarasi (10..500).
  Ilgari ro'yxatda yo'q qiymatni jimgina 50 ga aylantirardi — muammoning
  yarmi aynan shu edi.

**(b) ~~«−5 qoldi»~~ — TUZATILDI 2026-09-15.** `course-v3.html:5303` da
`(dailyGoal-todayXp)` to'g'ridan-to'g'ri chop etilardi. Endi
`Math.max(0,...)`. `tests/test_miniapp_daily_goal_left.py` mixlab qo'ydi.

**(c) Liga nomi — Mini App qattiq yozib qo'yilgan.** Server haqiqiy pog'ona
nomlarini beradi (`app/services/course_gamification_service.py`: `Bronze`,
...). Android o'shani ko'rsatadi. Mini App esa serverникini e'tiborsiz
qoldirib, i18n ichidagi `league:"朱雀 ligasi"` ni va `course-v3.html:5132`
dagi qattiq `朱雀` nishonini chiqaradi.

Qaysi biri to'g'ri ekani — mahsulot qarori. Agar 朱雀 brend bo'lsa, Android
ham shuni ko'rsatishi kerak; agar pog'ona nomi bo'lsa, Mini App serverdan
o'qishi kerak. Hozir ikkalasi bir-biriga zid.

### 3.3 ~~Ilova sekin ochiladi~~ — TUZATILDI 2026-09-15

Sababi birinchi kadr emas edi: sovuq ishga tushish emulyatorda 460–530 ms,
ya'ni normal. Kechikish undan **keyin** edi.

`CourseRepository.courseMap()` diskdagi keshni **faqat tarmoq yiqilganda**
o'qirdi. Ya'ni har ochilishda ilova to'liq borib-kelishni kutardi — aynan o'sha
ekranning tayyor nusxasi diskda turgani holda. O'lchov: production API'ga
borib-kelish 0.9–3.5 s (tez internetda, autentifikatsiyasiz; telefonda 4G'da
sekinroq). Shuncha vaqt bo'sh ekran.

Endi `cachedCourseMap()` bor: kesh darhol chiziladi, yangilanish orqadan
keladi. Kesh «stale» deb belgilanmaydi — «stale» degani *yangilash yiqildi*,
yangilash hali ketayotganda buni hech kim bilmaydi. Yiqilsa, eski
`cached(error)` yo'li uni baribir belgilaydi va banner chiqadi.

**Diqqat:** bu faqat kurs xaritasiga tegishli. `FeatureRepository` da kesh
hali ham yo'q — profil, mashq, testlar, reyting har ochilishda tarmoqni
kutadi.

### 3.4 ~~AI Voice ekrani buzuq~~ — TUZATILDI 2026-09-20

Suhbat ekrani to'liq ekran uchun yozilgan edi, lekin `MainScaffold` ichiga
qo'yilgan. Scaffold allaqachon status bar va pastki panel joyini ajratardi,
`VoiceCallScreen` esa ustidan yana `statusBarsPadding()` va dock'da
`navigationBarsPadding()` qo'shardi — tepada ham, dock ustida ham ikkinchi
bo'sh joy ochilardi, pastda esa tab tugmalari suhbat ostida ko'rinib turardi.

Endi:

- suhbat faol bo'lganda `MainScaffold(bottomBarVisible = false)` — tab paneli
  yo'q, Mini App'dagi `course_v3_voice.html` kabi. Chiqish — Close tugmasi
  yoki «orqaga» (`BackHandler` → `onEndSession`);
- `VoiceCallScreen` endi hech qanday system inset qo'shmaydi, dock esa
  klaviatura va gesture panelini **bitta** inset sifatida oladi
  (`WindowInsets.ime.union(WindowInsets.navigationBars)`), ikkitasini ustma-ust
  emas.

**Panel endi kontent ustida suzadi.** Shisha effekti ortida ko'rinadigan narsa
bo'lishini talab qiladi — ilgari Scaffold kontentni panel ustida to'xtatardi va
yarim shaffof panel qattiq plitaday ko'rinardi. Narxi: har bir asosiy ekran o'z
pastki padding'iga `LocalMainBottomInset` ni qo'shishi shart, aks holda oxirgi
karta panel ostida qolib ketadi. Qo'shilgan joylar: Course, Practice (ro'yxat,
`QuestionShell`, yakun), Rating, Profile, Voice va `SectionLimitOverlay`.

Suzuvchi AI tugmasining pastki chegarasi qattiq yozilgan `72.dp` edi — haqiqiy
panel 98 dp. Endi `MainBottomBarHeight` dan olinadi, ya'ni panel balandligi
o'zgarsa tugma ham ergashadi. Suhbat vaqtida esa dock balandligi
(`VOICE_DOCK_HEIGHT`) qo'shiladi — tugma mikrofon ustiga o'tirmaydi.

**Tekshirilmagan:** bu yerda Android SDK yo'q, ya'ni faqat beshta statik
tekshiruv o'tkazildi. Kompilyatsiya, lint va real ko'rinish (light/dark,
360–390 dp, katta font, uz/ru/tg) telefonda tasdiqlanishi kerak.

### 3.5 ~~Profil va Reyting chrome'i~~ — TUZATILDI 2026-09-20

Uchta alohida narsa, foydalanuvchi suratlaridan (1.3.1):

**Profil sarlavhasi uch qator edi.** `ProfileHero` da ism, `HSK2 · Bronze`
pilli va kirish holati (`Bepul rejim`) bitta ustunda ketma-ket turardi. Holat
endi kartaning o'ng yuqori burchagida alohida pill (`AccessPill`) — ism bilan
pill ikki qatorda qoladi. Ism `maxLines = 1` bo'ldi, aks holda uzun ism pillni
kartadan chiqarib yuborardi.

**Qo'ng'iroqcha yarmi ko'rinardi.** `ChallengeBell` da «1» nishoni ikona bilan
**bitta 44 dp qutida**, `TopEnd` ga tekislangan edi. Ikona markazda 21 dp —
ya'ni nishon uning o'ng-yuqori choragini bosib turardi. Quti 52 dp bo'ldi,
doira `BottomStart` ga, nishon esa doiradan tashqariga chiqdi.

**Dumaloq tugmalar tugmaga o'xshamasdi.** `HskGlassSurface` yorug' rejimda
`oq @ 0.72`, chegarasi `oq @ 0.92`, fon `#FDF9F0` — ya'ni doira ham, chegara
ham ko'rinmaydi. Reyting qo'ng'irog'i va `RatingScreenHeader` dagi orqaga
tugmasi endi `borderColor = PompColors.Divider` oladi, ya'ni `VoiceCallScreen`
dagi `RoundIconButton` bilan bir xil. Umumiy `HskGlassSurface` ga tegilmadi —
u kartalarda to'g'ri ishlaydi.

**Diqqat:** boshqa `HskGlassIconButton` ishlatadigan joylar (Mashq, ovozli
suhbat) hali ham chegarasiz, ya'ni yorug' rejimda xira. Kerak bo'lsa
`HskGlassIconButton` ga standart chegara berilsa hammasi bir xil bo'ladi.

### 3.5.1 Profildan olib tashlangan uchta blok — 2026-09-20

`TrialCard`, `SubscriptionCard` va `ReferralCard` olib tashlandi:

- **Do'st taklif qilish** — `RatingScreen` dagi `FriendInviteCard` ayni havola
  va tugmalarni beradi. Toza dublikat edi.
- **Obuna** — matni `profile_subscription_play_blocked`:
  «Google Play Billing sozlamalari repo tashqarisida…». Bu dasturchi izohi
  bo'lib, foydalanuvchiga chiqib qolgan edi.
- **7 kun Pro bepul** — dublikat emas, lekin trial yo'qolgani yo'q: limit
  tugaganda chiqadigan paywall (`SectionLimitBlock`, `direct` va `play`)
  uni baribir taklif qiladi.

`ProfileScreen` va `ProfileWidgetCompat` dan `onStartTrial` parametri ham
olib tashlandi. `ProfileViewModel.startTrial` o'z joyida qoladi —
`MainActivity:472` dagi `LimitGate` uni ishlatadi.

`profile_trial_*`, `profile_subscription_*` va `profile_referral_*` satrlari
resurslarda qoldi (uch tilda), chunki ular qaytarilishi mumkin.

### 3.6 Dars yakuni bayrami Mini App darajasiga chiqarildi — 2026-09-20

`LessonCompletionCelebration.kt` da uchala sahna bor edi, lekin ikkitasi
yalang'och: streak ekrani faqat «🔥 N» va «0 → 1» ko'rsatardi, reyting ekrani
esa «🏆 #6» va «#7 → #6». Mini App'da esa hafta kunlari, haftalik maqsad va
ismli reyting jadvali bor.

Endi:

- **Sahna qora** (`--ink`, Mini App'dagi `.levelup` kabi) va orqasida 24 ta
  oltin nur sekin aylanadi (`RayBurst`, Canvas bilan chiziladi — `#lu-rays`
  JS'da ham xuddi shunday quriladi).
- **Streak ekrani**: katta alanga + panda, raqam, «kun ketma-ket!», holatga
  mos matn, 7 kunlik alanga/muz qatori va «Sizning haftangiz N/7» progressi.
- **Reyting ekrani**: «Reytingda ko'tarildingiz!», o'zib ketilgan o'quvchining
  ismi va uch qatorli jadval (yuqoridagi, siz, o'zib ketilgan).

**Ma'lumot qayerdan keladi.** Hafta uchun serverga tegilmadi —
`CourseGamificationDto` allaqachon `week_start`, `week_activity_dates` va
`local_date` ni beradi. `StreakCalendar.kt` dagi `weekCalendarMeta()` endi
`internal` va ikkala joy ham (profil kalendari va bayram) **bitta**
implementatsiyadan o'qiydi — bir hafta haqida ikki xil javob bo'lmasligi uchun.

**Reyting jadvali bitta qo'shimcha so'rov qiladi.** `rank_before`/`rank_after`
serverdan keladi va ko'tarilish faktini **faqat o'sha** hal qiladi (XP'dan
taxmin qilinmaydi). Qo'shnilarning ismi va XP'si esa kelmaydi, shuning uchun
dars tugagach `FeatureRepository.rating()` bir marta so'raladi. So'rov yiqilsa
yoki o'zida ism bo'lmasa — sahna oddiy «#7 → #6» qatoriga tushadi, Mini App
ham tasdiqlay olmasa bayram oynasini ochmaydi.

`LessonViewModel` endi `featureRepository` oladi (testlarda `null`, ya'ni
so'rov umuman qilinmaydi).

**Matnlar** Mini App'dagi `streakCopy()` va `skWeekGoalHtml()` dan so'zma-so'z
ko'chirildi, uch tilda — o'ylab topilmadi.

**Tekshirilmagan:** bu muhitda Android SDK yo'q. Beshta statik tekshiruv
o'tdi, kompilyatsiya va ko'rinish telefonda tasdiqlanishi kerak. Ayniqsa:
streak ekrani past ekranda sig'yaptimi (aylanadigan qilingan), panda alanga
yonida to'g'ri turibdimi, jadval uzun ismda kesilyaptimi.

### 3.7 Boshqa ochiqlar

- Android'da `Yodlash` ekrani yo'q.
- Darsni tugatish hali ham internet talab qiladi; offline'da retry CTA'ga
  tushadi. Navbatga qo'yib keyin yuborish yo'q.
- `versionCode` qo'lda yoziladi va oshirilmaganini hech narsa ushlamaydi.

## 4. YAQINDA TUZATILGAN — lekin hali tarqatilmagan

### R8 `@Serializable` modellarni o'chirib yuborgan (1.1.0 dagi eng katta xato)

`android/app/proguard-rules.pro` ga qo'shilgan:

```proguard
-keep,allowobfuscation @kotlinx.serialization.Serializable class ** { *; }
```

Qoidasiz **oltita** model APK'dan butunlay yo'qolgan va ularni qaytaradigan
har bir so'rov **tarmoqqa chiqmasdan** yiqilgan:

| Model | Qaysi so'rov | Foydalanuvchi nima ko'rgan |
|---|---|---|
| `AndroidHintDismissResponse` | `/android/hints/dismiss` | tushuntiruvchi yozuv har kirganda qaytadi |
| `DrillReportResponse` | `/android/practice/report` | mashq natijasi yozilmaydi → Xatolar/Testlar sonlari zid |
| `DrillGateResponse` | `/android/practice/gate` | «Ieroglif tanish» ochilmaydi |
| `AndroidAdViewResponse` | `/android/ad/view` | reklama hisoblanmaydi |
| `OkResponse` | `/preferences/language`, `/preferences/notifications` | til va bildirishnoma sozlamasi saqlanmaydi |
| `RevokeResponse` | `/android-auth/revoke` | akkauntni uzish ishlamaydi |

**Qanday tekshirilgan:** qoida bilan va qoidasiz ikkita release build yig'ilib,
dex ichidagi serial nomlari solishtirilgan — qoidasiz `DrillGateResponse` 0
marta, qoida bilan 2 marta uchraydi; `data.api` modellari 127 ga qarshi 133.
Qoidasiz yig'ilgan APK hajmi **3 784 820 bayt** — bu R2 va botdagi hozirgi
1.1.0 faylning aynan hajmi, ya'ni **tarqatilayotgan build o'sha buzuq build**.

Tekshirishni takrorlash:

```bash
unzip -p app.apk 'classes*.dex' | strings | grep -c "DrillGateResponse"
```

**Nega `-if` ishlamaydi:** R8 da `-if` sharti faqat allaqachon «tirik» deb
topilgan klassga qaraladi. O'chirilgan klassni u qaytara olmaydi. Shuning
uchun shartsiz `-keep` kerak. `allowobfuscation` nom o'zgarishiga ruxsat
beradi, ya'ni APK kichik qoladi.

## 4.5 Saytdagi yuklab olish

`/download` (va `/apps`, `/desktop-download` — hammasi bir sahifa). Uchala
platforma bir joyda.

Sahifa o'zi JS bilan ishlaydi, lekin **server tomonida ham to'ldiriladi**:
`<!--APP-DOWNLOADS-->` belgisi o'rniga oddiy HTML ro'yxat va JSON-LD
(`SoftwareApplication` har bir chiqarilgan platforma uchun) qo'yiladi. Sababi:
qidiruv va AI robotlari JS ishlatmaydi — ular sahifani «Versiya
tekshirilmoqda…» holida ko'rardi va nima borligini bilmasdi.

Ma'lumot manbai: `GET /api/v3/apps/public-status` →
`app/services/app_downloads_service.py`. Chiqarilmagan platforma haqida **hech
narsa da'vo qilinmaydi** — yo'q buildni e'lon qilish, uni topa olmaydigan
odamga AI takrorlaydigan yolg'on.

Bo'lim matni `data-i18n` bilan belgilangan, ya'ni sahifaning o'z til
almashtirgichi uni ham tarjima qiladi. Yangi kalit qo'shsangiz —
`desktop-download-page.js` dagi uchala tilga ham qo'shing.

**CSS/JS keshda bir yil turadi** (`immutable`). O'zgartirsangiz
`desktop-download.html` dagi `?v=` ni oshiring, aks holda hech kim yangisini
ko'rmaydi.

### Sahifa tuzilishi

Yuqorida qurilma tanlash (iOS · macOS · Android · Windows), o'rtada karta
(nom, versiya, sana, tugma), pastda **tanlangan qurilmaga qarab o'zgaradigan**
tushuntirishlar va xavfsizlik izohi.

**iOS'da alohida ilova yo'q.** U ro'yxatda qoladi va tugmasi Telegram botni
ochadi; pastdagi matn buni ochiq aytadi. Qurilma userAgent'dan aniqlanadi —
Android telefondan kirgan odam darhol APK kartasini ko'radi.

«Linkni kompyuterga yuboring» bloki faqat telefondan macOS/Windows tanlanganda
chiqadi: APK'ni telefonning o'zi ocha oladi, iOS'da esa uzatadigan fayl yo'q.

Matnlar `desktop-download-page.js` dagi `COPY` da, platforma prefiksi bilan:
`iosTitle`, `androidSteps`, `macSecurity` va h.k. (`macos` tarixan `mac`).
Yangi platforma qo'shsangiz — `COPY_KEY` ga ham qo'shing.

## 4.6 Mini App ichidagi ilova reklamasi

Ikkita joyda Android bor:

**Profildagi promo karta** (`course_v3_data/desktop-download.js`). Android
`APP_PROMO_PLATFORMS` ga qo'shildi; mavjudligi `/api/v3/apps/public-status`
dan olinadi — desktop statusidan emas, chunki u boshqa pipeline va
autentifikatsiya talab qilmaydi. Uning yiqilishi desktop tugmalarini
o'ldirmaydi.

Android **qisqa yo'ldan** ketadi: havola to'g'ridan-to'g'ri ochiladi. Pastdagi
butun mashina (request token, «faylni qayerda ochamiz?» oynasi, boshqa
qurilmaga uzatish) DMG/EXE telefonda ishlamagani uchun qurilgan. APK ishlaydi —
o'quvchi allaqachon o'rnatadigan qurilmani ushlab turibdi.

**Dars yakunidagi reklama oynasi ichidagi ilova bloki** (`ads.js` →
`PompDesktopDownload.mountAdPromoTrigger`). 2026-09-16 da `app` reklama turi
olib tashlandi: ilovani endi FAQAT `desktop_app_promo` reklama qiladi, ya'ni
bu blok ham profil kartasi bilan bir xil platforma chiplari va bir xil
`platform_targets` javobiga bo'ysunadi. `COURSE_AD_APP_VISIBLE_PLATFORMS`,
`_desktop_auto_download_links` va roliknining o'z platforma havolalari endi
yo'q.

**iOS ikkalasida ham yo'q** — unga alohida ilova yo'q, o'lik tugma esa
foydalanuvchini chalg'itadi. Tayyor bo'lganda ro'yxatlarga qo'shish yetarli.

**Diqqat — kesh.** `ads.js` va `desktop-download.js` `immutable`, bir yillik
cache bilan beriladi (`app/main.py`, `STATIC_ASSET_HEADERS`). Bu fayllarni
o'zgartirsangiz, `app/static/*.html` dagi `?v=` ni HAM ko'taring, aks holda
o'zgarish eski keshdagi nusxa ostida qoladi va hech kimga yetib bormaydi.
`tests/test_course_v3_static_data.py` dagi hash testi buni ushlaydi.

## 4.7 Botga fayl qanday yetib boradi (va nima turadi)

Bot APK'ni **o'zi o'qiydi** va baytlarini yuboradi. Ilgari Telegramga URL
berilardi — ya'ni faylga yetib borishi kerak bo'lgan yana bitta tomon bor edi,
va u yiqilganda foydalanuvchi faqat «fayl yuborilmadi» ni ko'rardi, sabab esa
allaqachon aylanib ketgan logda qolardi. 2026-09-15 da aynan shunday bo'ldi.

**Narxi: har release uchun bir marta 3.7 MB.** Foydalanuvchi boshiga emas —
birinchi so'ragandan keyin Telegram bergan `file_id` saqlanadi va qolganlarga
Telegram serverlaridan ketadi, biz orqali hech narsa o'tmaydi.
R2'dan chiqish bepul, Railway'ga kirish ham. Hisob: ~$0.0002 bir release,
yiliga 12 ta release ≈ yarim sentdan kam.

**Kuzatish kerak bo'lgan yagona narsa:** logdagi
`Reading the Android APK once for version …` qatori. U har release'da BIR
MARTA chiqishi kerak. Har foydalanuvchida chiqsa — `file_id` saqlanmayapti va
har biri yuklab olishga tushyapti.

Yuklab olishda hajm manifestdagi bilan solishtiriladi: mos kelmasa fayl
yuborilmaydi. Hech kim o'lchamagan buildni tarqatgandan ko'ra yubormaslik
yaxshi.

## 5. Qayerga qarash kerak

| Nima | Qayerda |
|---|---|
| Ekranlar | `android/app/src/main/java/com/pomp/hskai/feature/*/` |
| Tarmoq modellari | `data/api/AndroidFeatureDto.kt` |
| Retrofit interfeyslari | `data/api/Android*Api.kt` |
| Flavour farqlari | `src/direct/`, `src/play/` |
| Statik tekshiruvlar | `android/tools/check_*.py` — **Gradle'dan oldin ishga tushiring** |
| Server tomoni | `app/api/android_*.py`, `app/services/android_*.py` |
| Rang palitrasi | Mini App bilan bir xil bo'lishi shart, `check_palette_matches_miniapp.py` tekshiradi |

## 6. Ishlash qoidalari

- **Har o'zgarishdan keyin:** beshta statik tekshiruv, keyin
  `./gradlew testDirectDebugUnitTest testPlayDebugUnitTest lintDirectDebug lintPlayDebug`.
- **Matn qo'shsangiz** — uchta tilda (uz/ru/tg). `check_strings_translated.py`
  buni majburlaydi. Backend kodlari `uz/ru/tj`, Android qualifierlari
  `values/values-ru/values-tg` — `tj` va `tg` farqini `core/i18n/AppLanguage`
  boshqaradi.
- **Release build'ni ishonmang** — R8 kodni o'chiradi. Yangi `@Serializable`
  model yoki reflectiv chaqiruv qo'shsangiz, release APK'da ham sinang.
- **Emulyator:** `Pixel_8` AVD shu Mac'da bor.
  `connectedDirectDebugAndroidTest` har safar ilovani o'chirib qayta
  o'rnatadi — ya'ni ulangan Telegram sessiyasi yo'qoladi va qayta ulash kerak.
