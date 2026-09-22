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
  tushiriladi). 2026-09-20 holatiga ko'ra **besh marta muvaffaqiyatli
  o'tgan** (oxirgisi 1.3.4, versionCode 9), hammasi `main` dan. Ya'ni imzo va R2 sirlari GitHub'da sozlangan
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

**Diqqat:** bu yechim 3.12 da bekor qilindi — chegara emas, doiraning o'zi
ortiqcha edi. `HskGlassIconButton` endi faqat ikona chizadi.

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

### 3.7 Mashq yakunida ham alanga ekrani — 2026-09-20

Dars bayrami qilingach, o'sha effekt mashqqa ham moslandi. Umumiy qismlar
`core/design/components/HskCelebration.kt` ga chiqarildi:
`HskCelebrationStage` (qora sahna + oltin nurlar + konfetti),
`HskStreakCelebration` (alanga, raqam, matn, 7 kunlik qator, haftalik maqsad),
`HskCelebrationPanda`, `HskRayBurst`, `HskConfettiField`. Dars ham, mashq ham
**bitta** manbadan foydalanadi — ikkitasi vaqt o'tib bir-biridan ajralmasin.

**Tartib Mini App'dagidek:** avval natija, keyin alanga. Mashq natijasi
(tavsiya, xato savollar, imtihon bo'limlari, qolgan xatolar) o'z joyida
qoladi — u yo'qotilmadi. `hasStreakEvent` bo'lsa tugma «Davom etish» bo'ladi
va alanga ekraniga olib boradi; bo'lmasa to'g'ridan-to'g'ri yopadi, bo'sh
ekran chiqmaydi.

Ulangan joylar: `CompletionSummaryShell` (Mashq va Testlar) va
`MistakesCompletionResult` (Xatolarim).

**Reyting sahnasi mashqda yo'q va bu ataylab.** `rank_before`/`rank_after`
faqat dars yakunida keladi (`android_course_service.py:122-136`); mashq,
imtihon va xato takrori javoblarida bunday maydon yo'q. Ko'tarilishni XP'dan
taxmin qilishdan ko'ra sahnani umuman ko'rsatmaslik to'g'ri.

Ieroglif mashqlari (`RECOGNITION`/`PRONUNCIATION`) da gamification umuman
yo'q (`drillCompletionOutcome` bo'sh DTO qaytaradi), ya'ni alanga ekrani u
yerda o'zidan-o'zi chiqmaydi.

**Tekshirilmagan:** SDK yo'q. Beshta statik tekshiruv o'tdi.

### 3.8 Yopiq darsni ochish: o'tish testi — 2026-09-20

Androidda yopiq dars tugunini bosganda hech narsa bo'lmasdi. Mini App esa
`offerSkipTest` ni ochadi: «Bu dars hali qulflangan. Uni ochish uchun qisqa
test topshiring.»

Endi Androidda ham shunday. Oqim Mini App tartibini takrorlaydi:

1. Taklif ekrani (`SkipTestScreen`)
2. Darsning **o'z kartalaridan** 6 ta savol (`SkipTestViewModel.drawQuestions`)
3. ≥60% — darhol ochiladi; <60% — «Baribir ochish» so'raladi
4. Ochilish **natijadan oldin** bo'ladi (`completeSkipUnlock` ham shunday),
   natija esa «Darsni boshlash» bilan tugaydi

**Savollar o'ylab topilmaydi** — darsning graded kartalari olinadi. Kartasi
yo'q dars shunchaki ochiladi, Mini App'da `buildTestQueue` bo'sh qaytganda
ham shunday.

**Urug' — dars raqami.** Yopiq darsni yopib-ochish savollarni qayta
aralashtirmaydi, aks holda oson chiqquncha qayta urinish mumkin bo'lardi.

**Server:** `POST /api/v3/android/lesson/unlock` (bearer) →
`DesktopCourseService.unlock_lesson`. Sarflangan kunlik limit bu yo'lni ham
yopadi — aks holda keyingi dars rad etilganda undan keyingisini test bilan
ochish mumkin bo'lardi, ya'ni paywall'ni aylanib o'tish. Band so'rovda yo'q:
server foydalanuvchining o'zinikini o'qiydi.

**Nega past ball ham ochadi.** Serverda rad etish faqat testni qayta
topshirishga o'rgatardi. Ball yoziladi, tasdiqni klient so'raydi.

Qamrov: `SkipTestViewModelTest` (6 ta) + backendda 7 ta. Android testlari bu
muhitda ishlamaydi (SDK yo'q) — ularni release workflow tekshiradi.

### 3.9 ~~Lug'atdagi yozish tartibi besifat~~ — TUZATILDI 2026-09-20

Ikkita alohida sabab bor edi, va kattarog'i tezlik emas.

**Sifat: chiziq noto'g'ri chizilardi.** hanzi-writer chizig'i — bu to'ldirilgan
**konturi**, ya'ni cho'tkaning izi shakli, chiziladigan chiziq emas.
`StrokeAnimation` esa o'sha konturning **perimetridan** ulush kesib, qolganini
to'ldirardi (`PathMeasure.getSegment`). Bu yarim yozilgan chiziq emas —
chetning bir parchasi, va aynan shunday ko'rinardi ham.

Endi cho'tka chiziqning **markaz chizig'i** (median) bo'ylab yuradi: qalin
dumaloq chiziq median bo'ylab o'sadi va chiziqning o'z shakliga qirqiladi
(`clipPath`). hanzi-writer ham shunday qiladi.

**Medianlar allaqachon kelayotgan edi.** Server hanzi-writer faylini o'zi
qanday bo'lsa shunday uzatadi, `StrokeDataDto` esa faqat `strokes` ni o'qib,
`medians` ni tashlab yuborardi. Serverga tegilmadi.

**Tezlik.** Ilgari butun ieroglif bitta `LinearEasing` sweep edi, har chiziq
qat'iy 420 ms, chiziqlar orasida pauza yo'q. Endi har chiziq **o'z uzunligiga**
qarab vaqt oladi (hanzi-writer formulasi: `(uzunlik + 600) / 3`) va orasida
280 ms pauza bor — Mini App'dagi `delayBetweenStrokes` qiymati.

**Kontur ham tuzatildi:** ilgari 2 **piksel** (dp emas) simli ramka edi, ya'ni
zich ekranda soch tolasidek. Endi hanzi-writer'dagidek xira to'ldirilgan shakl.

`strokes()` endi `CharacterStrokes` (kontur + median) qaytaradi — ikkisi
alohida ma'noga ega emas, shuning uchun birga yuradi. Lug'at ham, darsdagi
yozish varag'i ham shu bitta chizuvchidan foydalanadi.

Qamrov: `CourseRepositoryTest` — medianlar DTO'dan o'tishini mixlaydi.

**Tekshirilmagan:** ko'rinish telefonda ko'rilishi kerak — ayniqsa cho'tka
kengligi (`BRUSH_WIDTH_RATIO = 0.22`) eng yo'g'on chiziqni qoplayaptimi.

### 3.10 Lug'at endi internetsiz to'liq ishlaydi — 2026-09-20

Lug'at APK bilan kelmasdi. So'zlar serverdan yuklanib Room'ga keshlanardi,
chiziqlarning esa **keshi umuman yo'q** edi — har ochilishda tarmoqqa borardi.
Ya'ni mobil internetda o'rnatib, keyin metroda ochgan odam bo'sh lug'at
ko'rardi; ilgari ishlatgan odam ham yozish tartibini ko'rmasdi.

Ikkalasi ham repoda allaqachon bor edi — Mini App lug'at sahifasi ularni
o'zi bilan olib yuradi (`hsk-words.js`, `hsk-extra.js`). Endi o'sha fayllardan
Android assetlari yasaladi:

```
android/app/src/main/assets/hsk-words.js         1247 so'z, uch tilda
android/app/src/main/assets/strokes/<kod>.json   1055 ieroglif
```

**Bu ish ikki marta, mustaqil qilingan** va 2026-09-20 da birlashtirildi.
`172bcb5` so'zlarni bundle qildi (`AssetBundledDictionarySource` +
`DictionaryRepositoryTest`) va `SEARCH_LIMIT` ni 200 dan 2000 ga ko'tardi —
200 lik chegara ro'yxat HSK2 da tugaganday ko'rsatardi. Chiziqlar esa alohida
ishda qo'shildi. Birlashtirishda **so'zlar tomoni o'sha ishniki** qoldi
(interfeys, testi va tuzatishi bilan), chiziqlar ustiga qo'shildi. Ikkinchi
nusxa (`dictionary.json`) olib tashlandi — bir xil so'zlar ikki joyda
turmasligi uchun.

Fayl nomi ieroglifning kod nuqtasi — server o'z keshini ham shunday nomlaydi
(`{ord(char)}.json`), ya'ni ikki tomonni solishtirish uchun tarjima kerak emas.

**Narxi: chiziqlar APK'da ~+1.3 MB** (o'lchandi). Har ieroglif alohida fayl
bo'lgani uchun bitta katta fayldan ~344 KB ko'proq — evaziga bitta ieroglifni
o'qish uchun 2.4 MB JSON parse qilinmaydi.

**Bundle — manba emas, poydevor.** So'zlar ro'yxati kesh bo'sh bo'lsa
bundle'dan to'ldiriladi, keyin server baribir so'raladi: deploy ro'yxatni
o'zgartirsa bundle ilovani eski nusxaga mixlab qo'ymasligi kerak.

**Chiziqlar** (`BundledStrokes`) avval bundle'dan o'qiladi, topilmasa
tarmoqdan — darsda uchraydigan, lug'atda yo'q ieroglif uchun.

**Yasash va tekshirish:**

```bash
python3 android/tools/build_stroke_assets.py   # Mini App ma'lumotidan yasaydi
python3 android/tools/check_stroke_assets.py   # eskirib qolmaganini tekshiradi
```

Ikkinchisi statik tekshiruv sifatida CI va release workflow'ga
qo'shildi. Ikki nusxa ajralib ketadi: Mini App ma'lumoti o'zgaradi, generator
qayta ishga tushirilmaydi, va telefonda yozib bo'lmaydigan ieroglif qoladi —
jimgina, chunki yo'q chiziq fayli hech qachon bo'lmaganidan farq qilmaydi.

**Ovoz baribir to'liq offline emas.** Faqat ilgari eshitilgani ishlaydi
(`ttsCache`). 1247 so'zning audiosi bir necha MB, telefonning o'z TTS'i esa
yaramaydi — 3.1 ga qarang.

**Ikkita mashq — so'z bazasi endi offline, lekin eshik yopiq.**
`WordDrillViewModel` savollar hovuzini `DictionaryRepository` dan oladi, ya'ni
u endi bundle'dan keladi va internetsiz ham to'ladi. Lekin mashq birinchi
`repository.drillGate(...)` ni so'raydi va offline'da o'sha yiqiladi. Bu
ataylab: gate — server qarori (bepul o'quvchi bo'limni bir marta oladi,
reklama uni qayta ochadi), va uni qurilmada hal qilish huquqni klientga
berish bo'lardi. Ya'ni mashqlar online qolishi — e'tiborsizlik emas, qoida.

### 3.12 Uch xato foydalanuvchi suratlaridan (1.3.4) — TUZATILDI 2026-09-20

**AI chatda surat jo'natilmasdi.** Xabar `assistant_network` edi — ya'ni
server rad etmagan (u `assistant_unavailable` bo'lardi), balki **istisno**
chiqqan. Surat so'rov tanasi ichida base64 bo'lib ketadi, 3 MB gacha, ya'ni
base64 dan keyin ~4 MB; umumiy OkHttp client'da esa `writeTimeout = 30s`,
`callTimeout = 60s`. Telefon uplinkida 4 MB shuncha vaqtga sig'maydi.

Ikki tomondan tuzatildi:

- Assistant o'z timeout'ini oldi (`writeTimeout = 120s`, `callTimeout = 180s`).
  `httpClient.newBuilder()` orqali, ya'ni connection pool va dispatcher
  umumiy qoladi. Qolgan ekranlar 60 soniyada tushadigan javobni uch daqiqa
  kutmaydi.
- Surat byudjeti 3 MB → 1.5 MB, sifat 88 → 82. Server baribir 2048px va
  sifat 88 ga qayta kodlaydi (`assistant_service.py`), ya'ni bundan og'iri
  telefon sarflab, server tashlaydigan bayt. Zich surat (ko'pincha matn
  sahifasi) eng past sifatda ham sig'masa, endi «yomon surat» demaydi —
  1400px ga tushadi.

**Tinglash savoli javobni o'zi yozib qo'yardi.** `LessonCards.kt` da
`ChoiceKind.LISTENING` kartasi, pinyin yoqilgan bo'lsa, audio pinyinini
variantlar tepasiga chop etardi — ya'ni to'g'ri javobni. Mini App
(`course-v3.html`, `cardChoice`) tinglash kartasida faqat audio tugmasini
ko'rsatadi. Olib tashlandi. `audioPinyin` modelda qoladi — yozish varag'i
uni sarlavha sifatida ishlatadi.

**Yozish varag'i butun gapni bitta katakka chizardi.** Tinglash kartasida
qalam nishoni — eshitilgan **butun gap** (Mini App'da ham shunday). Lekin
chiziq ma'lumoti bitta ieroglifga tegishli, shuning uchun varaq bir
belgidan uzun narsani 128sp matn qilib katakka tiqardi — ieroglif ustma-ust
tushardi.

Endi Mini App'ning `hsk-lugat.html` sahifasi qanday qilsa shunday: nishon
belgilarga ajraladi (`WriterTarget.characters`, tinish belgilari tashlanadi,
chunki ularda chiziq yo'q) va birma-bir yoziladi — `‹ 2 / 7 ›`. Strelkalar
lug'atdagi bilan bir xil glif. Kechikib kelgan javob boshqa belgiga
tushmaydi: `writerIndex` tekshiriladi.

Qamrov: `LessonViewModelTest` — gap bo'ylab yurish, tinish belgisi
sanalmasligi, chegaradan tashqari indeks.

**Qalam tugmasi javob panelining ustida turardi.** `WriterButton` pastdan
qat'iy `152.dp` da edi; javob paneli esa izohiga qarab o'sadi. Endi panel
`onSizeChanged` bilan o'lchanadi va tugma uning ustida 16 dp turadi.

**Mayda ikonalar dumaloq blok ichida edi.** `HskGlassIconButton` har doim
`HskGlassSurface` (doira + soya) ichiga o'rardi. Oq-oq Paper ustida doira
tugmaga emas, glif atrofidagi xira dog'ga o'xshardi. Endi u oddiy
`IconButton` — faqat ikona, tegish maydoni o'sha-o'sha. Reyting
qo'ng'irog'i va `RatingScreenHeader` orqaga tugmasi ham shunga o'tdi, ya'ni
3.5 dagi «chegara qo'shish» yechimi bekor qilindi: chegara emas, blokning
o'zi ortiqcha edi.

Kartalardagi `HskGlassSurface` ga tegilmadi — u yerda to'g'ri ishlaydi.

### 3.13 Ilova umuman kompilyatsiya qilmasdi — TUZATILDI 2026-09-21

`main` 2026-09-20 dan beri **ikkala flavourda ham yiqilardi**, ya'ni yangi
APK chiqarib bo'lmasdi:

```
LessonLimitCompat.kt:54:13  No value passed for parameter 'limit'
```

Sabab — bir xil nomli **ikkita** `LessonScreen` composable'i. Asli
`LessonScreen.kt` da, ikkinchisi `LessonLimitCompat.kt` da: u chegara
overlay'ini qo'shish uchun birinchisini o'rab turardi (`458ee7a7`,
`67a937ac` — main sinxronidan keyin tiklangan edi).

3.12 dagi yozish varag'i ishi `LessonScreen.kt` ga `onShowWriterCharacter`
parametrini qo'shdi, o'rovchiga esa qo'shmadi. Shundan keyin:

- `MainActivity` yangi parametrni uzatgani uchun Kotlin **asl** funksiyani
  tanladi — ya'ni o'rovchi chetlab o'tildi va **chegara bloki jim
  yo'qoldi** (dars limitida trial/obuna tugmalari o'rniga quruq matn);
- o'rovchining ichidagi chaqiruv esa endi o'zini chaqirardi — kompilyatsiya
  xatosi.

`LessonLimitCompat.kt` o'chirildi, `SectionLimitOverlay` esa
`LessonScreen.kt` ning o'z ichiga ko'chirildi — Kurs xaritasi, Mashq va AI
Voice qanday qilsa shunday. `limit` endi rostdan ishlatiladi, ilgari u
`ignoredLimit` deb chetga surib qo'yilgan edi.

**Qoida:** bitta paketda bir xil nomli ikkita composable qilmang. Overload
tanlovi jim o'zgaradi — `check_named_arguments.py` ham,
`check_unresolved_references.py` ham buni ko'rmaydi, chunki ikkala nom ham
mavjud.

Yon ta'sir: `tests/test_trial_entry_points.py` dagi
`test_the_profile_offers_the_trial` 3.5.1 dan beri eskirgan edi (profildan
`TrialCard` ataylab olib tashlangan, test esa uni talab qilardi). Endi test
yangi haqiqatni qotiradi: profilda karta yo'q, lekin `startTrial`
`LimitGate` ga ulangan.

### 3.14 Personajlar mashqqa ham chiqdi, murabbiy qatori qayta ishlandi — 2026-09-21

Dars 2026-09-20 da Mini App personajlar to'plamini oldi (5 personaj, 8
kayfiyat, 11 reaksiya). Mashq esa olmadi: savollarda personaj umuman yo'q
edi, yakunda esa hali ham **widget'ning statik `widget_panda_*` rasmi**
turardi. Ya'ni bitta ilova ichida ikki xil dunyo edi.

**Chizuvchi umumiy joyga chiqarildi.** `LessonCharacters.kt` dagi renderer
`core/design/components/HskCharacters.kt` ga ko'chdi (`HskCharacter`,
`HskCharacterMood`, `HskCharacterReaction`, `HskCharacterStage`,
`hskReactionFor`). Dars fayli typealias qoldirdi — `LessonScreen.kt` va yangi
kelgan `LessonCharacterParityTest` **o'zgarishsiz** ishlaydi. Sabab 3.7 dagi
bilan bir xil: ikki nusxa vaqt o'tib bir-biridan ajraladi.

**Qaysi ekranga qaysi personaj** — `feature/practice/PracticeCharacters.kt`.
Tanlov ta'mga emas, paketdagi **rolga** asoslanadi
(`hsk-character-pack.js` dagi `CAST`):

| rol | personaj | nimani oladi |
|---|---|---|
| `main_coach` | Panda | o'qiladigan savol |
| `grammar_precision` | Crane | grammatika, ieroglif tanish |
| `drill_dialogue` | Monkey | tinglash, talaffuz |
| `memory_warning` | Rabbit | xato takrori |
| `energy_milestone` | Dragon | kuchli natija bilan yakun |

**HSK imtihonlarida personaj ATAYLAB yo'q.** Imtihon to'g'ri javobni oxirigacha
yashiradi (`ExamRun` ikkala holat uchun ham `false` uzatadi); javobga
reaksiya qiladigan murabbiy esa javobni oshkor qilardi. Daraja aniqlash
testida bor, chunki u har savoldan keyin javobni va izohni o'zi ko'rsatadi.

**Mashqda `hearts` yo'q**, ya'ni "oxirgi yurak" pog'onasiga yetib bo'lmaydi —
zinapoya ayri emas, umumiy. `practiceStreak` / `reviewStreak` /
`answerStreak` faqat 4 ketma-ket to'g'ri javobdagi bayram uchun; ball
serverda hisoblanadi.

**Murabbiy qatori qayta ishlandi (ikkala klientda).** Ilgari personaj o'ng
chetda YOLG'IZ turardi va yonida uning ISMI yozilgan yorliq bor edi — bo'sh
joyda osilgan stikerga o'xshardi, yorliq esa foydali hech narsa demasdi.
Endi: chapda personaj, o'ngda gap pufagi, ichida **ekranning o'z ko'rsatma
qatori**. Pufak shakli `.teach-bub` dan olingan (burchagi kesilgan).

**Savol murabbiyning YONIDA turadi** (`HskCoachBeside`): chapda baland
personaj (120×152.dp), o'ngda uning gapi va uning ostida savol materiali.
Javob variantlari pastda, **to'liq enda** — ular ekrandagi eng keng narsa va
tor ustundan birinchi bo'lib aziyat chekadi. Shu sababdan savol kartalari
ikkiga bo'lindi: `ChoiceCardMaterial` / `ChoiceCardOptions` (dars) va
`PracticeQuestionMaterial` / `PracticeQuestionOptions` (daraja testi).

Darsda bu **faqat `ChoiceCard`** uchun — qolgan turlar (o'rgatuvchi kartalar,
quruvchi, juftlik) murabbiyni tepada saqlaydi, chunki ularda yoniga
qo'yadigan narsa yo'q.

Mini App'da ayni narsa: savol kartasi murabbiyning o'ng ustuniga
**ko'chiriladi** (`PracticeCoach.beside`, darsda `syncLessonCoachLine`),
nusxalanmaydi — sahifalar markupni har savolda qaytadan quradi.

**Diqqat — chizma nisbati.** `CharPen` yagona, bir xil masshtab beradi va
chizmani qutiga markazlashtiradi. Eni va bo'yi alohida masshtablanganda
118×150 qutida turnaning bo'yni o'ndan bir uzayib ketgan edi. Shu sababdan
yo'l buyruqlarida absolyut (`px`/`py`) va nisbiy (`w`) o'lchovlar ajratilgan.

Matn **ko'chiriladi, nusxalanmaydi** — shuning uchun yangi satr ham, yangi
tarjima ham yo'q:

| Ekran | Murabbiy nimani aytadi | Qayerdan olindi |
|---|---|---|
| Dars | kartaning `title` si | `CardTitle` (`LocalLessonCoachLine` orqali o'chadi) |
| Xatolarim | `kategoriya · Savol N / M` | savol ustidagi qizil qator |
| Ieroglif/talaffuz | bo'limning ko'rsatmasi | karta ustidagi kulrang qator |
| Daraja testi | `N / M` | `QuestionShell` sarlavhasi |

**Diqqat:** personaj hech qanday kesuvchi quti (`overflow:hidden`, doira
avatar) ichiga solinmasin — sakrash va bayram animatsiyasi chetidan
qirqiladi. Shuning uchun u pufakdan tashqarida turadi.

Mini App tomonida ayni qator `app/static/assets/characters/hsk-practice-coach.{css,js}`
da, uchala mashq sahifasi shundan foydalanadi. **Yangi fayl
`COURSE_CHARACTER_ASSETS` allowlist'iga qo'shilishi SHART** (`app/main.py`),
aks holda 404 bo'ladi va murabbiy jimgina ko'rinmay qoladi — sahifalar
`window.PracticeCoach` ni tekshiradi.

Qamrov: `PracticeCharacterParityTest` (7 ta) va
`tests/test_course_character_assets.py` (imtihonda personaj yo'qligi,
sahifalarning ulanishi, zinapoya va yakun chegaralari).

### 3.16 Google va Apple bilan kirish — 2026-09-22

Kirish endi faqat Telegram emas. Login ekranida Telegram kartasining ostida
"Google bilan davom etish" va "Apple bilan davom etish" tugmalari chiqadi,
profilda esa "Kirish usullari" varag'i bor (ulash/uzish).

**Eng muhim narsa: yangi token yo'li YO'Q.** Google/Apple oqimi serverdagi
`desktop_link_requests` qatorini `approved` qiladi, keyin ilova **o'zgarmagan**
`android-auth/link/status` ni chaqiradi va tokenni o'sha yerdan oladi. Ya'ni
sessiya yaratiladigan joy bitta bo'lib qoldi (`AuthRepository.pollLink`).

Qayerda:
- `core/auth/GoogleIdTokenProvider.kt` — Credential Manager. Interfeys orqali,
  shuning uchun JVM testda emulyatorsiz sinaladi.
- `core/auth/AuthRepository.kt` — `startGoogleSignIn`, `startAppleSignIn`,
  `availableProviders`, `linkedIdentities`, `unlinkIdentity`.
- `data/api/NativeOAuthApi.kt` + `NativeOAuthDto.kt`
- `feature/auth/LinkScreen.kt` + `LinkViewModel.kt` — tugmalar va holat.
- `feature/profile/IdentitiesSheet.kt` + `IdentitiesViewModel.kt`

Bilib qo'yish kerak:
- **`google-services.json` KERAK EMAS** va `google-services` plagini ham yo'q.
  Credential Manager faqat **Web client id** ni oladi
  (`POMP_GOOGLE_WEB_CLIENT_ID` → `BuildConfig.GOOGLE_WEB_CLIENT_ID`).
- Bu qiymat `require()` qilinmagan: bo'sh bo'lsa Google tugmasi **ko'rinmaydi**,
  build yiqilmaydi. Shuning uchun hozirgi build'larda hech narsa o'zgarmaydi.
- Apple'ning native SDK'si yo'q — u Custom Tabs'da ochiladi va natija
  allaqachon ishlab turgan polling orqali qaytadi. **`DeepLinkRouter.kt` ga
  tegilmagan**: allowlist ataylab qattiq, App Links qo'shish hujum yuzasini
  kengaytirardi va hech narsa bermasdi.
- OAuth client'lari uchun 2 ta fingerprint kerak: `com.pomp.hskai` (upload key
  SHA-1 + Play App Signing yoqilgan bo'lsa Play SHA-1) va
  `com.pomp.hskai.debug`. `play` va `direct` bir xil `applicationId` ishlatadi,
  shuning uchun ular uchun alohida client kerak emas.
- Hozircha Telegramsiz akkaunt ochib bo'lmaydi. Noma'lum Google/Apple akkaunt
  `oauth_telegram_account_required` oladi va ilova "avval Telegram orqali
  kiring, keyin profilda ulang" deydi.

Qamrov: `AuthRepositoryOauthTest` (13 ta), `check_strings_translated.py` va
`check_flavor_parity.py` o'tadi.

### 3.15 Widget V2: bitta holat dvigateli, 28 variant — 2026-09-22

Eski widget'da panda **ikki xil qoida** bo'yicha tanlanardi: kunduzgi
90 daqiqalik rotatsiya (`WidgetReaction.DAYTIME_ROTATION`, 09:00–19:00) va
uning ustiga yopishtirilgan istisnolar (19:00 da XP yo'q bo'lsa `worried`,
22:00 dan keyin `sleepy`). Ya'ni bugun darsini qilmagan odamni soat 22:00 da
panda **uxlab** kutib olardi.

**Endi bitta dvigatel bor** — `WidgetVisualResolver`. U faqat ikki narsani
o'qiydi: foydalanuvchining mahalliy soati va bugungi dars bajarilganmi.

| Vaqt | Holat | Urgency |
|---|---|---|
| 05:00–09:59 | `MORNING` | 0 |
| 10:00–13:59 | `DAY` | 1 |
| 14:00–17:59 | `WAITING` | 2 |
| 18:00–19:59 | `EVENING` | 3 |
| 20:00–21:59 | `LATE` | 4 |
| 22:00–23:59 | `CRITICAL` | 5 |
| 00:00–04:59 | yangi kun → `MORNING` | 0 |

Ustuvorlik: `SPECIAL > COMPLETED > vaqt`. Dars bajarilsa — soat nechchi
bo'lishidan qat'i nazar `COMPLETED`. 22:00 da `sleepy` yo'q.

**Kirish holatlari ajratildi.** `WidgetMood` o'rniga `WidgetAccess`
(`UNLINKED`/`STALE`/`FOUNDATION`/`ACTIVE`). Ular kayfiyat emas, shuning uchun
kayfiyat dvigateliga aralashmaydi.

**Rasm tanlovi deterministik.** `FNV-1a(epoch|mahalliy sana|holat) % variants`.
Bir kun ichida bir holat → doim bir xil rasm; widget har soat qayta
chizilganda panda miltillamaydi. `epoch` — `WidgetSession.epoch`, qurilma
o'zi yaratgan UUID; widget xotirasiga foydalanuvchi ID qo'shilmadi.

**Matn rasmdan ajratilgan.** Har variantning o'z string resursi bor
(`widget_morning_01` … `widget_completed_05`), uchchala tilda.

Tafsilot: `ANDROID_SMART_WIDGET.md`.

**Rasmlar:** 28 tasi ham o'rnida —
`res/drawable-nodpi/widget_panda_*.webp`, jami ~500 KB (512px, WebP q90;
manba 2048px, git'dan tashqarida). Hammasi bitta 3D uslubda va **matnsiz**:
yozuv string resursidan keladi, shuning uchun bir rasm uch tilga xizmat
qiladi. Eski 2D vektorlardan faqat `widget_panda_cheer/streak/worried`
qoldi — ular widget'niki emas, bildirishnoma va `HskCelebration` niki.

Rasm tanlashda qoida: avval **kayfiyat**, keyin **rasmdagi yorug'lik**.
Tunggi osmon `DAY` holatida turgani xatodek ko'rinadi, shuning uchun
kunduzgi rasmlar MORNING/DAY/WAITING'da, to'q sariq EVENING'da, tunggilar
LATE'da, qizil dramatiklar CRITICAL'da.

### 3.11 Boshqa ochiqlar

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

Android **qisqa yo'ldan** ketadi: chip bosilganda hech qanday havola
ochilmaydi — `POST /api/miniapp/event` (`android_apk_to_chat`) serverga
boradi, bot APK'ni chatga tashlaydi va Mini App yopiladi. Pastdagi butun
mashina (request token, «faylni qayerda ochamiz?» oynasi, boshqa qurilmaga
uzatish) DMG/EXE telefonda ishlamagani uchun qurilgan. APK ishlaydi —
o'quvchi allaqachon o'rnatadigan qurilmani ushlab turibdi.

**Promo «tarqatadigan narsa bormi?» degan savolni Android'dan ham so'raydi**
(2026-09-20). `DesktopDownloadService._promo_status()` dagi `release_ready`
ilgari faqat `PLATFORMS = ("macos", "windows")` ni ko'rardi, `target_for(
"android")` esa har doim `None` qaytaradi — ya'ni APK nashr qilingan, desktop
relizi esa qilinmagan holatda ilova promosi UCHALA joyda ham o'chib qolardi,
admin Android chipini yoqib qo'ygan bo'lsa ham. Endi `AndroidReleaseService`
ham so'raladi (R2 havolasi shart emas: bot `file_id` bilan beradi — bu
`app_downloads_service` bilan bitta qoida). Shu sababdan
`DESKTOP_DOWNLOADS_ENABLED` ham Android-only promoni o'chira olmaydi: u
DESKTOP yuklab olishning kill switch'i, Android u yo'ldan o'tmaydi.

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

**Narxi: har release uchun bir marta ~4.7 MB** (offline lug'at qo'shilgandan
keyin; ilgari 3.7 MB edi). Foydalanuvchi boshiga emas —
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
| Import qolib ketishi | `check_unresolved_references.py` — chaqirilgan nom import qilinganini tekshiradi |
| Server tomoni | `app/api/android_*.py`, `app/services/android_*.py` |
| Rang palitrasi | Mini App bilan bir xil bo'lishi shart, `check_palette_matches_miniapp.py` tekshiradi |
| Offline lug'at | `android/app/src/main/assets/` — so'zlar `hsk-words.js`, chiziqlar `strokes/`. `build_stroke_assets.py` yasaydi, `check_stroke_assets.py` eskirmaganini tekshiradi |

## 6. Ishlash qoidalari

- **Har o'zgarishdan keyin:** yettita statik tekshiruv, keyin
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
