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

### 3.1 Mashq savollari buzuq — bitta qator, ikkita xato

`feature/practice/PracticeScreen.kt` uch joyda (451, 507, 525):

```kotlin
QuestionText(question.prompt, question.sentence.ifBlank { question.audioText }, ...)
```

Bu bitta fallback ikkita ko'rinadigan xatoni keltirib chiqaradi:

- **Tinglash savoli javobni ko'rsatib qo'yadi.** «Eshiting va to'g'ri javobni
  tanlang» deydi, lekin `sentence` bo'sh bo'lgani uchun `audioText` ekranga
  chiqadi — ya'ni 您 yozib qo'yiladi va tanlash ma'nosiz bo'ladi. Ovoz
  umuman chalinmaydi.
- **Bo'shliq savolida gap yo'q.** Ikkalasi ham bo'sh bo'lsa hech nima
  chiqmaydi — ekranda faqat `___` chizig'i qoladi.

Telefonda 2026-09-15 da ikkalasi ham ko'rilgan (skrinshot bor edi).

`PROJECT_MEMORY.md` da bu 2026-09-14 dan beri «ochiq» deb turibdi. Tuzatish
savol turiga qarab boshqacha bo'lishi kerak: tinglashda `audioText` **hech
qachon** ko'rsatilmasligi va **chalinishi** kerak; bo'shliq savolida gap
yo'q bo'lsa savolning o'zi yaroqsiz.

### 3.2 Mini App va ilova bitta akkauntda boshqa-boshqa narsa ko'rsatadi

Bir foydalanuvchi, bir payt, ikki klient:

| | Mini App | Android |
|---|---|---|
| Kunlik maqsad | 45 / **40** XP | 45 / **50** XP |
| Qoldi | **−5** | 5 |
| Liga | **朱雀** | **Bronze** |
| Holat | Sayohat | Bepul rejim |

Uchta alohida sabab:

**(a) Kunlik maqsad umuman sinxronlanmaydi.** Server profilda `daily_goal_xp`
saqlaydi; Mini App uni o'qiydi va yozadi (`STUDY_SETUP.daily_goal_xp`,
`savePreferences({daily_goal_xp:v})`). Android esa uni **faqat telefon ichida**
saqlaydi — `core/settings/AppSettings.kt`, DataStore kaliti `daily_goal_xp`,
`DailyGoal.DEFAULT = 50`. `AndroidStudyPreferencesApi` serverga `goal`,
`daily_minutes`, `preferred_focus` yuboradi — **`daily_goal_xp` ni emas**, va
Android profil DTO'sida bunday maydon **umuman yo'q**.

Ya'ni: Mini App'da 40 tanlansa server 40 ni biladi, Android esa buni hech
qachon o'qimaydi va o'z lokal 50 sini ko'rsatadi. Teskarisi ham shunday.

Ustiga tanlovlar ham har xil: Mini App `[20,30,40,50,80]`, Android
`[10,20,30,50]` — ya'ni **40 ni Android'da tanlashning iloji yo'q**. Ikkalasi
hech qachon kelisha olmaydi.

**(b) «−5 qoldi» — Mini App xatosi.** `goal - xp` noldan pastga tushishi
cheklanmagan: 45 − 40 = −5. Android'da bunday emas.

**(c) Liga nomi — Mini App qattiq yozib qo'yilgan.** Server haqiqiy pog'ona
nomlarini beradi (`app/services/course_gamification_service.py`: `Bronze`,
...). Android o'shani ko'rsatadi. Mini App esa serverникini e'tiborsiz
qoldirib, i18n ichidagi `league:"朱雀 ligasi"` ni va `course-v3.html:5132`
dagi qattiq `朱雀` nishonini chiqaradi.

Qaysi biri to'g'ri ekani — mahsulot qarori. Agar 朱雀 brend bo'lsa, Android
ham shuni ko'rsatishi kerak; agar pog'ona nomi bo'lsa, Mini App serverdan
o'qishi kerak. Hozir ikkalasi bir-biriga zid.

### 3.3 Ilova sekin ochiladi

Foydalanuvchi aytgan, hali o'lchanmagan. `LessonCache` va `CourseCache` bor,
lekin ochilishdagi kechikish sababi aniqlanmagan.

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
