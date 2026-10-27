# Android — AI uchun kontekst

Bu fayl Android kodi, oqimlari va hozir tekshirilishi kerak bo‘lgan holatlar
uchun kontekst beradi. Release amallari alohida `ANDROID_RELEASE_CHECKLIST.md`
da. Sana bilan yozilgan bo‘limlar tarixiy yozuv: eski branch, release,
production config yoki taskga berilgan ruxsatni bugungi holat deb olmang; yangi
ishdan oldin tegishli source va amaldagi policy’ni tekshiring. Doimiy project
kontekst `PROJECT_MEMORY.md`da saqlanadi, u sanali changelog emas.

---

## 1. Ilova nima va qayerda

Native Kotlin/Compose klient, `android/` papkasida. Bot, Mini App, macOS va
Windows bilan **bir xil backend** va yagona `users.id` akkaunti, obuna va
progress. Google/Apple orqali Telegramsiz hisob ochiladi; boshqa kirish usuli
mavjud hisob profilidan aniq ulanadi. Email tengligi hisoblarni birlashtirmaydi.
Kirish — `LinkScreen` dagi uchta karta: Telegram (kodsiz,
botdagi bitta tasdiq), Google va Apple (server taklif qilsa).

Google/Apple bilan ochilgan hisobga profilidan Telegram keyin ulanishi mumkin:
ilovadagi sessiya va o‘rnatishga bog‘langan so‘rov bot shaxsiy chatida alohida
tasdiqlanadi. Boshqa hisobning Telegram’i ko‘chirilmaydi; ulangan Telegram
o‘qish uchun ko‘rsatiladi. Yangi user yoki sessiya yaratilmaydi, mavjud Pro,
progress va Voice/AI sarfi saqlanadi. Oynani yopish kutilayotgan so‘rovni bekor qiladi.

Direct APK’da Pro va alohida HSK 3.0 xaridi mavjud chek/admin oqimi bilan
`users.id`ga yoziladi. Referral kodi yangi hisob yaratilishidan oldin qabul
qilinadi; bonus va chegirmaning mavjud shartlari saqlanadi. Play hozircha
xaridsiz, shu hisobdagi kirish holatini o‘qiydi. Universal o‘zgarishlarni
`main`/production’ga chiqarish hali bloklangan; qabul shartlari
`docs/UNIVERSAL_NATIVE_ACCOUNTS.md`da.

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

## 2. Source holati (live release tasdig‘i emas)

- Source versiya: `android/app/build.gradle.kts` tepasidagi `appVersionName` /
  `appVersionCode`. Yangi release uchun `appVersionCode` oshiriladi. Workflow
  past code’ni rad etadi, lekin teng code’ga faqat byte-identical mavjud
  artifact rerun’iga ruxsat beradi; yangi build’da teng code’ni oldini
  oladigan alohida qat’iy guard yo‘q. Chiqarishdagi aniq qadamlar
  `ANDROID_RELEASE_CHECKLIST.md`da.
- Release signing: workflow himoyalangan GitHub Actions secrets orqali
  keystore va parol kutadi; kutiladigan secret nomlari va release tekshiruvi
  `ANDROID_RELEASE_CHECKLIST.md`da. Source fayllar secret qiymatlari mavjud
  yoki to‘g‘ri sozlanganini isbotlamaydi; credential qiymati yoki joylashuvini
  kontekst hujjatlariga yozmang.
- APK tarqatish workflow’da optional R2 publish va backend release manifesti
  orqali boshqariladi. Manifest sozlanmagan yoki yaroqsiz bo‘lsa, hujjatdagi
  bot-admin fallback ishlatilishi mumkin. Joriy bucket, public URL va
  production manifest qiymatini repo kodi tasdiqlamaydi; release holatini
  `ANDROID_RELEASE_CHECKLIST.md` va hosting sozlamalaridan tekshiring.
- Yo'l bitta: bot profilidagi «📱 HSK AI ilovalari» → Mini App profilidagi
  karta (`?tab=profile&desktop_download=1`, karta fokuslanadi) → Android
  chipi (`POST /api/miniapp/event` → `android_apk_to_chat`) → Mini App
  yopiladi, APK chatga tushadi. `/android` buyrug'i va eski xabarlardagi
  `android_app:get` tugmasi ham ishlaydi. Saytdagi `/desktop-download` sahifasi
  Android uchun direct linkni faqat joriy release’da download URL mavjud
  bo‘lsa ko‘rsatadi; u Telegram `file_id`ning o‘zi bilan link yasamaydi va
  URL albatta R2 bo‘lishi shart emas. Backendning stable route’i
  `/downloads/android`; joriy release manbasi `ANDROID_RELEASE_CHECKLIST.md`da.
- Yangi (PR #247, hali live emas) Android update policy: Admin PWA sozlamasidagi 1–4 tanlov haqiqatan **e’lon qilingan release** sonidir, `versionCode` farqi emas. Direct R2 `android/latest.json` ichidagi `published_version_codes` tarixidan oladi va avvalgi APK installerini saqlaydi. Play esa Google Play Developer API’ning production track ma’lumotidan faqat tasdiqlangan release’larni R2’dagi alohida `android/play-releases.json`ga mirror qiladi (`android-play-release-mirror.yml`, opt-in). Play Core faqat Google Play orqali hozirgi qurilmaga mavjud yangi versiyani tasdiqlasa Immediate Update ochiladi. Eski tarix yetarli bo‘lmasa yoki Play sync yoqilmagan bo‘lsa, noto‘g‘ri lock qilinmaydi. Yangi qoida faqat yangilangan Android binary’dagi mijozlarda ishlaydi.
- Yangilanishdan xabar berish (faqat `direct`): ilova ochilganda va kuniga bir
  marta fonda `…/android-update/check` so'raladi (`UpdateWatch`). Har release
  uchun **bitta** bildirishnoma (`app_updates_alerts` kanali, `UpdateNotices`), va
  `versionCode` farqi ≥ 2 bo'lsa tab paneli ustida yopib bo'lmaydigan qator
  (`AppUpdateBanner`); farq 1 bo'lsa yangilanish faqat profildagi kartada
  ko‘rsatiladi. Threshold sonli farqni ishlatadi, published release sonini
  emas; code increment convention workflow’da qat’iy tekshirilmaydi.
- Release avtomati `.github/workflows/android-release.yml` orqali qo‘lda
  (`workflow_dispatch`) boshlanadi. Workflow’da `main` branch bilan cheklov
  yo‘q; manifestdan past `versionCode` rad etiladi. Release tanlash, publish
  va live holat uchun `ANDROID_RELEASE_CHECKLIST.md`ga qarang — eski Actions
  natijalari, signing secret’lar yoki production sozlamalari bu faylda
  current fact sifatida saqlanmaydi.
- Play flavor va Play release contract kodi repoda bor. Play Console account,
  listing va tarqatilgan release holati tashqi tizimda; source code buni
  tasdiqlamaydi.


## 3. Tarixiy ochiq masalalar — avval qayta tekshiring

Quyidagi holatlar avvalgi auditda ochiq edi. Yangi vazifada ularni bugungi
defect deb taxmin qilmang: main source, test va kerak bo‘lsa haqiqiy release
bilan qayta tasdiqlang. 2026-09/10 tuzatishlar, CI natijalari, eski branch
va push ruxsatlari, APK tarqatish va barcha tafsilotlar
[to‘liq Android tarixida](docs/archive/android/ANDROID_CONTEXT_HISTORY_2026-10-18.md).

### Qayta tekshirilishi kerak bo‘lgan tarixiy bandlar

- Dars yakunidan keyingi reklama oynasida (`AdScreen`) tizim «orqaga»si hali
  ilovani yopadi: oyna Kurs tabi ustida turadi, Kursda back esa chiqish.
  Reklama mantig'iga ataylab tegilmagan (3.20).
- Desktop (`desktop/ui/js/lesson.js`, `selectPair`) juftlik mashqini hali
  eski usulda baholaydi: bitta xato bosish kartani ochkosiz qoldiradi va
  mistake yozadi. Mini App va Android (3.20) bunday qilmaydi.
- Android'da `Yodlash` ekrani yo'q.
- Darsni tugatish hali ham internet talab qiladi; offline'da retry CTA'ga
  tushadi. Navbatga qo'yib keyin yuborish yo'q.
- Egasi tanlagan release qoidasi: har bir yangi release `versionCode`ni oxirgi
  published qiymatdan kattaroq qiladi; aynan `+1` bo‘lishi shart emas. Aynan
  bir xil APK’ni qayta ishga tushirish mumkin. Workflow past code’ni rad etadi,
  ammo teng code bilan boshqa artifact’ni alohida bloklamaydi; shu sabab yangi
  release oldidan published manifest bilan qo‘lda solishtiring.

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
| Offline lug'at | `android/app/src/main/assets/` — so'zlar `hsk-words.js`, chiziqlar `strokes/`, misollar `hsk-examples.json`, qismlar `hanzi-parts.json`, ovoz `audio/words/`. Generatorlar `build_stroke_assets.py`, `build_dictionary_insights.py`, `build_word_audio.py`; tekshiruv `check_stroke_assets.py`, `check_dictionary_assets.py` (3.22) |

## 6. Ishlash qoidalari

- **Statik gate va Gradle tekshiruvlari:** ayni vaqtdagi aniq buyruqlar
  `android/README.md`da. Android CI va release workflow’lari Gradle’dan oldin
  to‘qqizta project-specific statik tekshiruvni ishga tushiradi; CI workflow’lari
  tekshiruvlar ro‘yxati va bajarilish tartibining source of truth’idir. Lokal
  ishda o‘zgarishga mos tekshiruvlarni bajaring, kengroq PR/release gate’larini
  README va workflow’dan oling.
- **Matn qo'shsangiz** — uchta tilda (uz/ru/tg). `check_strings_translated.py`
  buni majburlaydi. Backend kodlari `uz/ru/tj`, Android qualifierlari
  `values/values-ru/values-tg` — `tj` va `tg` farqini `core/i18n/AppLanguage`
  boshqaradi.
- **Release build'ni ishonmang** — R8 kodni o'chiradi. Yangi `@Serializable`
  model yoki reflectiv chaqiruv qo'shsangiz, release APK'da ham sinang.

## 7. Tarixiy material va qabul qilingan qarorlar

Oldingi release'lar, UI, login, dict/offline, botga APK yuborish,
2026-10-04 HSK 3.0/limit regression tafsilotlari **asl matnida**
[arxivda](docs/archive/android/ANDROID_CONTEXT_HISTORY_2026-10-18.md).
Tarixiy operatsion ko‘rsatmalar bugungi production/release holati emas.
Joriy release tartibi: `ANDROID_RELEASE_CHECKLIST.md`; build, source-set
va test: `android/README.md`. Hech qanday dastur kodi bu tozalashda o‘zgarmaydi.
