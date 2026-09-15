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
- Release avtomati: `.github/workflows/android-release.yml` (qo'lda ishga
  tushiriladi). Hali **bir marta ham ishlamagan**.
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

### 3.4 Boshqa ochiqlar

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
