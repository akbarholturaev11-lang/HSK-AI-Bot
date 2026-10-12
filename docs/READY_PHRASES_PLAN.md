# Tayyor gaplar — Android va Telegram Mini App

Holat: 2026-10-12 da reja amalga oshirildi. Quyidagi arxitektura va qabul
mezonlari yakuniy implementatsiyaga moslashtirildi.

Sana: 2026-10-12. Holat: reja; dastur kodi va kontent hali o‘zgartirilmagan.

## 1. Natija va doira

Ikkala platformada **Mashqlar → Lug‘at → Tayyor gaplar** tartibi bo‘ladi.
Yangi bo‘lim mavjud Lug‘atdan darhol keyin, shu menyuning oddiy qatori sifatida joylashadi.
Bo‘lim bepul va foydalanish soni bo‘yicha limitsiz: obuna, reklama ko‘rish yoki kunlik kvota talab qilmaydi.

Android’da barcha gaplar APK ichida keladi; bo‘limga kirishdan oldin kontentni yuklab olish shart emas.
Mini App’da shu jamlanma alohida yengil sahifada, statik fayldan ishlaydi.
Qidiruv, saralash, o‘qish va saqlash ikkala platformada ham lokal bajariladi.

Birinchi versiya: matn, pinyin, tarjima, qidiruv, mavzular, saqlangan gaplar va nusxalash.
AI javobi, quiz, XP/streak va bulut orqali audio birinchi versiyaga kirmaydi.

## 2. Mavjud holat auditi

| Zaif joy | Ta’siri | Aniq yechim | Risk |
|---|---|---|---|
| Lug‘at so‘z va ieroglif markazida | Vaziyatga mos tayyor gapni topish qiyin | Lug‘atni o‘zgartirmasdan alohida tematik jamlanma | Past |
| Android’da HSK 3.0 uchun butun Mashqlar tabi umumiy access gate bilan yopilishi mumkin | Bepul lokal bo‘limga ham yetib bo‘lmaydi | Menyuga kirish va pulli mashqni boshlash gate’larini ajratish; paid entry pointlarda mavjud access qoidalarini saqlash | O‘rta |
| Android offline xabari hozir faqat Lug‘atni sanaydi | Yangi bo‘lim ishlashi userga tushunarsiz qoladi | Uz/ru/tg offline matnida Lug‘at va Tayyor gaplarni ko‘rsatish | Past |
| Mini App Lug‘at detail ochilganda TTS so‘rovini yuboradi | Har gapni ochish server yukini oshirishi mumkin | Yangi ekranda avtomatik audio va `/api/v3/tts` chaqiruvi bo‘lmasin | Past |
| Mini App’da maxsus service worker/cache implementation mavjud emas | Telegram ichidan internetsiz qayta ochilishni kafolatlab bo‘lmaydi | Android offline va Mini App lokal ishlash va’dalarini aniq farqlash | Past, MVP chegarasida |

Audit dalillari: `PracticeScreen.kt`, `MainActivity.kt`, `DictionaryRepository.kt`,
`DictionaryViewModel.kt`, `AuthRepository.kt`, `course-v3.html`, `hsk-lugat.html`, `app/main.py`.
Graph hisobot o‘qildi; `graphify-out/wiki/index.md` mavjud emas.

## 3. Kontent va tartib

Boshlang‘ich jamlanma: **300 ta tekshirilgan amaliy gap**, 12 mavzu.
Gaplar soni mavzuning foydasiga qarab taqsimlanadi; har mavzuda bir xil son bo‘lishi shart emas.

Mavzular tartibi:

1. Salomlashish va tanishish
2. Kundalik suhbat
3. Oila va uy
4. Vaqt va uchrashuv
5. Ovqat va restoran
6. Xarid va pul
7. Yo‘l va transport
8. Sayohat va mehmonxona
9. O‘qish va dars
10. Ish va muloqot
11. Sog‘liq
12. Muammo va yordam so‘rash

Har mavzu ichida avval eng zarur sodda gaplar, keyin savol-javoblar va kengroq gaplar keladi.
Tartib alifbo yoki tasodifiy tanlovga emas, oldindan belgilangan `sort_order`ga asoslanadi.
Jamlanma kursni kundalik muloqot bilan mustahkamlaydi; dars tartibi va kurs materiallari o‘zgarmaydi.

Har kartada:

- Xitoycha gap katta va o‘qilishi oson matnda.
- Ohang belgili pinyin.
- Ilova tilidagi tarjima: o‘zbek, rus yoki tojik.
- Saqlash tugmasi va nusxalash amali.

Uzun izohlar qo‘shilmaydi. Zarur bo‘lsa qisqa vaziyat izohi ishlatiladi.
Mavjud kurs/dialog/misol gaplari boshlang‘ich material bo‘lishi mumkin; ular alohida saralanadi.
Tabiiy xitoycha, pinyin va uchala tarjima ma’nosi tekshirilgach jamlanmaga olinadi.

## 4. Ekran va qidiruv

Yuqorida sarlavha, orqaga tugmasi va qidiruv bo‘ladi.
Qidiruv ostida `Barchasi` va `Saqlanganlar`; mavzular ixcham ro‘yxat sifatida ko‘rsatiladi.
Mavzu tanlanganda faqat shu mavzudagi gaplar chiqadi. `Barchasi` barcha mavzular bo‘yicha qidiradi.
Qidiruv bo‘sh bo‘lsa, mavzular va tavsiya tartibi ko‘rinadi.

Qidiruv xitoycha, pinyin va uchala tildagi tarjimalarni qamraydi:

- `你好`, `nǐ hǎo`, `ni hao`, `nihao` bir xil gapni topadi.
- Katta-kichik harf, ortiqcha bo‘shliq va o‘zbek apostrof variantlari normallashtiriladi.
- `ü`/`v` hamda raqamli pinyin variantlari uchun kichik sinovlar belgilanadi.
- Ustuvorlik: aniq moslik → so‘z boshi → barcha qidiruv so‘zlari mosligi → qisman moslik.
- Teng natijada joriy til tarjimasi va belgilangan kontent tartibi ishlatiladi.
- Tayyor qidiruv indekslari lokal hisoblanadi; har harf uchun server so‘rovi yo‘q.

Android’da mavjud `PinyinSearch` normalizeri mos joylarda qayta ishlatiladi.
Mini App va Android bir xil qidiruv misollari bilan tekshiriladi; og‘ir qidiruv kutubxonasi kerak emas.
Saqlanganlarda faqat barqaror gap IDlari turadi: Android DataStore, Mini App localStorage.
Saqlanganlar qurilmada qoladi, platformalararo sinxronlash bo‘lmaydi.
Android’da logout/tozalashda tozalanadi; yangilanishda IDlar saqlanadi.

## 5. Texnik arxitektura va server yuki

**Bitta kontent manbasi → generator → Android JSON + Mini App JSON.**

Taklif etiladigan manba: `scripts/ready_phrases/phrases.json`.
Model: kontent versiyasi, tarjima qilingan mavzu nomlari va gaplar.
Har gapda `id`, `category_id`, `sort_order`, `zh`, `pinyin`, `translations.{uz,ru,tj}` bo‘ladi.
Backend/kontent til kodi `tj`; Android resource katalogi mavjud qoida bo‘yicha `values-tg`.
IDlar matn tuzatilganda o‘zgarmaydi.

Android:

- `assets/ready-phrases-v1.json` birinchi ochishda IO oqimida o‘qiladi; qidiruv katalog xotiraga tushgach lokal bajariladi.
- `ReadyPhrasesScreen` DataStore’dan sevimlilarni o‘qiydi va saqlaydi; yangi Room jadvali yoki DB migration kerak emas.
- Lug‘atning `sync()` oqimi ko‘chirilmaydi. Bo‘limning kontent/search/favorites API so‘rovlari: **0**.
- Direct va Play build bir xil bo‘limni oladi.
- Offline’da yangi qator Lug‘at kabi faol bo‘ladi; internet talab qiladigan mashqlar avvalgi qoidada qoladi.

Mini App:

- Alohida `/hsk-gaplar.html` sahifasi; menyudagi yangi tugma `lang` va kerakli mavjud tema holatini uzatadi.
- Sahifa kurs xaritasi, obuna holati yoki practice limitini olishga bog‘lanmaydi.
- Faqat bo‘lim ochilganda `/course_v3_data/ready-phrases-v1.json` yuklanadi.
- Versiyalangan asset mavjud public static whitelist orqali `application/json` va cache header bilan beriladi.
- Kontent o‘zgarsa asset versiyasi ham o‘zgaradi; eski `immutable` fayl boshqa baytlar bilan almashtirilmaydi.
- Qidiruv, mavzu almashtirish va saqlash `/api/`ga so‘rov yubormaydi; polling yoki yangi analytics oqimi qo‘shilmaydi.
- Telegram SDK yo‘q holatda ham sahifa ochiladi; safe-area, orqaga qaytish va klaviatura holati saqlanadi.
- Kontentni ko‘rsatish tashqi shrift yoki ikonka CDN ishlashiga bog‘lanmaydi.

Mini App’ning ilk HTML/JSON yuklanishi statik trafikdir. Ilovaning mavjud global
bootstrap/yangilanish so‘rovlari alohida qoladi; «butun ilova serverga umuman murojaat qilmaydi» degan va’da berilmaydi.

## 6. Offline chegarasi

Android’da gaplar o‘rnatilgan zahoti telefonda bor, oldindan shu bo‘limni online ochish shart emas.
Ammo mavjud ilova shell’i offline ochilishi uchun **oldin bir marta hisobga kirish va muvaffaqiyatli bootstrap** talab qiladi.
Fresh install yoki logoutdan keyin offline kirish mavjud auth siyosati bilan ishlamaydi.
Ushbu reja Lug‘atdagi mavjud kirish tartibini saqlaydi; guest kirish qo‘shilmaydi.

Mini App’da birinchi yuklash internet bilan bajariladi. Jamlanma ochilgach internet uzilsa,
qidiruv/o‘qish/saqlash ishlaydi. Telegram’ni yopib, bo‘limni internetsiz yangidan ochish
Android APK’dagidek kafolatlanmaydi. MVP umumiy service worker kiritmaydi.

Bu tanlov mahalliy manbadan o‘qish tamoyiliga mos
([Android Developers](https://developer.android.com/topic/architecture/data-layer/offline-first)).
Telegram Mini App URL orqali ochiladi
([Telegram hujjatlari](https://core.telegram.org/bots/webapps)); web sahifani offline qayta yuklash
alohida cache mexanizmini talab qiladi
([MDN Service Worker API](https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API)).

## 7. Rejalashtirilgan fayllar

Mavjud fayllarga minimal tahrir:

- `app/static/course-v3.html`: uch tildagi nom, subtitle, yangi qator va navigatsiya.
- `app/main.py`: public HTML route va versiyalangan JSON whitelist.
- `android/app/src/main/java/com/pomp/hskai/feature/practice/PracticeScreen.kt`: Lug‘atdan keyingi faol qator.
- `android/app/src/main/java/com/pomp/hskai/feature/practice/ReadyPhrasesScreen.kt`: APK assetdan lokal ekran.
- `android/app/src/main/java/com/pomp/hskai/MainActivity.kt`: bo‘lim navigatsiyasi va lokal/pulli entry gate ajratilishi.
- `android/app/src/main/java/com/pomp/hskai/core/settings/AppSettings.kt` va `HskAiApplication.kt`: sevimlilar DataStore’i va logout tozalashi.
- `android/app/src/main/res/values/strings.xml`, `values-ru/strings.xml`, `values-tg/strings.xml`: nomlar, qidiruv, bo‘sh holat, offline matni.
- Android CI/release workflow’lari va mavjud smoke/offline testlari: kontent tekshiruvini ulash.

Yangi fayllar:

- `scripts/ready_phrases/phrases.json`: yagona saralangan kontent manbasi.
- `scripts/build_ready_phrases.py`: deterministic generator va `--check` tekshiruvi.
- `app/static/hsk-gaplar.html`: mustaqil Mini App ekran.
- `app/static/course_v3_data/ready-phrases-v1.json`: yaratilgan web asset.
- `android/app/src/main/assets/ready-phrases-v1.json`: yaratilgan APK asset.
- `android/app/src/test/java/com/pomp/hskai/feature/practice/ReadyPhrasesAssetsTest.kt`: offline katalog yaxlitligi testi.
- `tests/e2e/test_ready_phrases.py`: 390px Mini App oqimi, pinyin qidiruvi, sevimlilar va API so‘rovi yo‘qligi.

## 8. Amalga oshirish tartibi va qabul mezonlari

1. Model, 12 mavzu va 300 gapni tayyorlash; xitoycha/pinyin/uch til tarjimalarini tekshirish.
2. Generator va validator: unique ID, kategoriya, tartib, bo‘sh tarjima, duplicate gap, asset versiyasi va ikki platforma kontenti tengligini tekshirish.
3. Mini App standalone ekran va Android lokal repository/ekranni ulash.
4. Ikkala Mashqlar menyusiga Lug‘atdan keyin qo‘shish; Android paid entry gate regressionlarini tekshirish.
5. Offline, qidiruv, saqlanganlar, mobil UI va mavjud kurs oqimlarini tekshirish.

Qabul mezonlari:

- Android va Mini App’da bir xil 300 gap, mavzular va tartib.
- Uz/ru/tj kontent va UI tarjimalari to‘liq.
- HSK 2.0/3.0, bepul/pulli hisoblarda Tayyor gaplar ochiq; dars va pulli mashq access’i buzilmagan.
- Android samolyot rejimida cold start: oldin kirilgan hisob bilan bo‘lim ochiladi; gaplar, qidiruv va saqlash ishlaydi.
- Bo‘lim Android’da hali online ochilmagan bo‘lsa ham APK assetdan ishlaydi.
- Mini App 360/390 px ekranda, SDK bor/yo‘q holatda va klaviatura ochilganda ishlaydi.
- Mini App kontent yuklangach internet uzilsa qidiruv/o‘qish davom etadi; cache yo‘q ilk yuklashda tushunarli xabar chiqadi.
- Qidiruv/ro‘yxat/saqlash davrida practice gate, start/complete, TTS yoki boshqa yangi API so‘rovi yo‘q.
- Saqlangan IDlar ilova yangilanishida saqlanadi; buzilgan/yopiq localStorage sahifani qulatmaydi.
- Lug‘at, lesson navigation, quiz/homework natija yuborish va Telegram back flow regression smoke’dan o‘tadi.
- Android sakkizta statik tekshiruvdan, Direct/Play Kotlin kompilyatsiyasidan va katalog unit testidan o‘tdi.

Umumiy risk: **past–o‘rta**. Asosiy e’tibor kontent sifati va Android’dagi
umumiy Mashqlar gate’ini toraytirganda pulli mashqlar access’ini saqlashga qaratiladi.
Keyingi ish: shu reja asosida kontent manbasi va generatorni tayyorlash.
