# Android foydalanuvchi feedbackini tuzatish rejasi

Sana: 2026-10-01. Holat: 1A, 1B, 2, 3, 4A va 4B implementatsiya qilindi;
yakuniy QA qoldi.
Asos: [Android audit](USER_FEEDBACK_AUDIT_2026-10-01.md).

Maqsad: foydalanuvchi tarif narxini tushunsin, valyutani o'zgartira olsin,
obuna joyini topsin va Android AI xizmatidan foydalanishda jim to'siq qolmasin.
Kurs, quiz/homework, referral va mavjud tarif/chegirma qoidalari saqlanadi.

Asosiy scope — Android `direct` APK. Play buildga tashqi payment CTA
kiritilmaydi. Backend umumiy bo'lgani uchun eski APK, Mini App va desktop
contract'lari uchun regression kerak. Native Android UX haqiqiy telefon
yoki emulator bilan tekshiriladi; Playwright uning o'rnini bosmaydi.

## Bajarish tartibi

| Navbat | Patch | Risk | Tugash mezoni |
|---|---|---|---|
| 1A | Serverda currency preference va mos API | O'rta | Tanlov akkauntga saqlanadi; eski klientlar ishlaydi | Bajarildi |
| 1B | Native tarifda currency selector/dialog; country qadamisiz oqim | O'rta | Tarif birinchi ochiladi; valyuta o'zgaradi; bank/narx jim o'zgarmaydi | Bajarildi |
| 2 | To'liq Profil ekrani va ichida obuna boshqaruvi | O'rta | Sozlamalar ikonka bo'ladi; obuna/uzaytirish Profil ichida | Bajarildi |
| 3 | AI status tiklanishi, Voice retry va to'g'ri xato matni | O'rta | Vaqtinchalik xatodan keyin ekrandan chiqmasdan qayta urinish mumkin | Bajarildi; Android build va testlar o'tdi |
| 4A | Paid renewal muddat/byudjet kontrakti | Yuqori | Qolgan to'langan kun va AI budget yo'qolmaydi; duplicate approval qo'shmaydi | Bajarildi; backend testlari muhit kutubxonalari yo'qligi sabab ishlamadi |
| 4B | Renewal tugmasi va native paid guard | O'rta | Faol paid user direct Androidda xavfsiz uzaytiradi | Bajarildi; end-to-end payment hali sinalmadi |
| 5 | Kichik UI/copy tozalash va release QA | Past | To'liq user yo'li real Androidda o'tadi; APK/backend mos | Qisman; login kerak bo'lgan Profile UI smoke qoldi |

Har patch alohida tekshiriladi va kichik commitga ajratiladi. Currency va
renewal biznes qoidalari bitta patchga aralashtirilmaydi. 4B faqat 4A
testlari o'tgandan keyin bajariladi; 2 va 3 renewalni kutmaydi.

## 1A — Akkaunt bo'yicha currency preference

- User uchun nullable `subscription_currency`: TJS/UZS/RUB/CNY/USD.
  `null` — hali serverda tasdiqlangan tanlov yo'q.
- Authenticated akkaunt nomidan preference saqlash; boshqa user ID va
  noma'lum currency qabul qilinmaydi. Overview tanlovni qaytaradi.
- Server preference truth source; Android DataStore cache bo'ladi.
  Eski telefon regioni serverdagi tanlovni jim bosib ketmaydi.
- Birinchi markaziy dialog server preference yo'qligiga qarab ochiladi.
  Yangi qurilma yoki logout/login tanlovni bekor qilmaydi.
- Display currency bilan payment method/bank va to'lanadigan currency
  alohida contract sifatida yuradi. Eski `card_country/card_bank`, `prices`,
  `card_prices` maydonlari eski klientlarga saqlanadi.
- Yangi `display_currency` request modeli, server adapteri va Android
  DTO bo'ylab qo'llanadi. Shared model `extra="forbid"` bo'lgani uchun
  maydon backendda tan olinmaguncha yangi APK uni yubormaydi.
- VISA/Xitoy to'lov usullarining alohida baza tariflari saqlanadi.
  Ko'rsatish currency o'zgarishi boshqa payment tariffini jim tanlamaydi.
- Bank/QRning haqiqiy qabul qiladigan currency'si server tomonidan
  tekshiriladi. Client hisoblagan summa paymentga ishonchli manba bo'lmaydi.

**Fayllar:** `app/db/models/user.py`, `app/repositories/user_repo.py`, yangi
Alembic migratsiya, `app/api/android_features.py`,
`app/api/desktop_subscription.py` shared request modeli,
`app/services/desktop_subscription_service.py`,
`app/services/subscription_miniapp_service.py`, kerak bo'lsa
`app/services/subscription_currency_service.py`, Android DTO/API/repository.

**Tekshiruv:** yangi/eski user, bir akkaunt ikki client, boshqa akkaunt,
valid/invalid preference, auth va eski request/response mosligi; migratsiya
bo'sh bo'lmagan bazaning test nusxasida tekshiriladi.

## 1B — Tarif birinchi, valyuta aniq

- Checkout birinchi ekrani `PLANS`; `Karta davlati` alohida qadami chiqariladi.
- Tarif ustida ko'rinadigan **`Valyuta: RUB — Rossiya rubli ▾`** tugmasi.
- Ilk tanlov — tarif markazida Compose dialog. Kod + to'liq currency nomi,
  tanlanganda narxlar yangilanadi va 1A orqali saqlanadi.
- Dialog ma'lumot kelgandan keyin ochiladi. Loading/error paytida soxta
  narx/variant yo'q. Save xatosi aniq ko'rsatiladi va qayta urinish mumkin.
- To'lov usuli/bank alohida aniq tanlanadi; mos variant bittagina bo'lsa
  qo'shimcha ekran chiqarilmaydi. Mavjud DC City/Alif/Alipay/WeChat yo'li saqlanadi.
  RUB ko'rishni tanlagan foydalanuvchi avtomatik xorijiy karta egasi deb
  hisoblanmaydi: DC City/Alif tanlovi display currencydan kelib chiqmaydi.
- Display qiymat konversiya ekvivalenti bo'lsa baza summa va izoh aniq
  chiqadi. To'lov ekranida server quote'ining actual amount/currency'si
  ko'rsatiladi. Method o'zgarsa yangi summa yuborishdan oldin ko'rsatiladi.
- Currency narxi topilmasa TJSga jim o'tish o'rniga sabab va ishlaydigan
  tanlov ko'rsatiladi. Xorijiy transferning muhim instruktsiyasi yashirilmaydi.

**Fayllar:**
`android/app/src/direct/java/com/pomp/hskai/feature/subscription/SubscriptionCheckoutHost.kt`,
`SubscriptionCheckoutViewModel.kt` shu katalogda,
`android/app/src/main/java/com/pomp/hskai/core/settings/AppSettings.kt`,
Android feature DTO/repository, `android/app/src/direct/res/values*/strings.xml`.

**Tekshiruv:** ilk kirish/qayta ochilish/currency almashtirish, ikki akkaunt,
local price yo'qligi, API/save failure, DC City/Alif/QR, discount, receipt,
pending; light/dark, UZ/RU/TJ, 320/390 dp va katta shrift.
Eski REGION-first unit testlari yangi oqimga mos yangilanadi.

## 2 — To'liq Profil ekrani va obuna boshqaruvi

- Profil to'liq ekran sifatida ochiladi; yuqori chetda `Profil` sarlavhasi,
  qarama-qarshi chetda sozlamalarni ochadigan ikonka turadi.
- Profil ichidagi obuna kartasi free, expired, trial/temporary va paid
  holatlarini ko'rsatadi; paid uchun tugash sanasi ham ko'rinadi.
- Direct APK'da `Obuna olish`, `Obunani tiklash` yoki `Obunani uzaytirish`
  shu ekrandan native checkoutga olib boradi. Play buildda tashqi checkout
  tugmasi ko'rinmaydi.
- Sozlamalar mavjud sheet'ini ikonka orqali ochadi; profilning asosiy
  ma'lumotlarini va obunani ko'rish uchun alohida sozlamalar qadamiga
  o'tish talab qilinmaydi.

**Fayllar:** `ProfileScreen.kt`, `MainActivity.kt`, direct checkout hosti,
native strings. **Tekshiruv:** direct/play build va test source compile o'tdi;
emulatorda APK o'rnatilib ochildi. Emulator login ekranida bo'lgani uchun
akkaunt talab qiladigan Profil holatlari UI'da to'liq bosib ko'rilmadi.

## 3 — AI jim ishlamay qolishini tuzatish — bajarildi

- Assistant statusga loading/ready/unavailable/error holati; failed status
  chat qayta ochilganda yoki `Qayta urinish` bosilganda qayta olinadi.
  Status failure kontekstli AI actionni butun sessiyaga yo'qotmaydi.
- `AI yordamchi` va `AI Voice` vazifasi/kirish joyi aniq tushuntiriladi.
  Dars/practice'da tugmani ataylab yashirish qarori saqlanadi.
- `assistant_disabled`, auth, network, timeout, paid cooldown/depleted,
  pending payment, blocked va free limit uchun mos matn/harakat.
  Serverning `limit_text` va `reset_at` maydonlari xatoda saqlanib ko'rsatiladi.
- Voice status xatosi shu ekranda `Qayta urinish` orqali qayta yuklanadi;
  Start sababi ko'rinadi.
- Voice call'da umumiy AI tugmasi yashiriladi. Uy foni, chat ko'rinishi
  tugmasi va chat berkitilganda kattalashadigan panda qo'shildi.
- Yakun natijasi markazda; server qaytargan correction bo'lgan javoblar
  “Siz aytdingiz / Tuzatish” ko'rinishida chiqadi.
- Kirish ekranidagi til tanlovi bosilmaguncha yopiq turadi.

**Fayllar:** Android `feature/assistant/AssistantController.kt`,
`AssistantHost.kt`, `AssistantApi.kt`; `feature/voice/VoiceViewModel.kt`,
`VoiceScreen.kt`; `core/network/ApiError.kt`, native `assistant.xml/strings.xml`.

**Tekshiruv:** direct/play debug test va build o'tdi; static strings,
flavor parity va source checks o'tdi. Voice account flow hamda AI retry
real akkaunt bilan emulatorda bosib tekshirilmagan. Access yoki AI limit
sonlari o'zgartirilmadi.

## 4A — Renewalni xavfsiz qilish — bajarildi

- Faol paid: yangi tugash sanasi mavjud paid expiry + xarid qilingan kun.
  Expired/free/trial: boshlanish hozirdan; temp bonus paid muddat deb
  avtomatik qo'shilmaydi. Sana UTC bo'yicha normalizatsiya qilinadi.
- Eski sarflanmagan AI budget va yangi payment budget qanday saqlanishi
  aniq contract bilan belgilanadi. Eski sarf tarixi va revenue qayta yozilmaydi.
  Faqat `end_date`ni uzaytirib eski budgetni expire qilish mumkin emas.
- Activation user row lock va payment idempotency bilan tekshiriladi:
  parallel ikki alohida to'lov ketma-ket qo'shiladi; bitta paymentning
  takror approval'i ikkinchi marta kun/budget/profit yozmaydi.
- Bot admin va admin Mini App approval yo'llari bir xil qoidaga o'tadi.

**Fayllar:** `app/services/subscription_service.py`,
`app/services/ai_usage_budget_service.py`, tegishli user/payment repository,
bot/admin approval yo'llari va regression testlari.

**Tekshiruv:** paid 20 kun + 30 kun = 50 kun; expired/trial yangi davr;
paid qisqa/uzun tarif; oldingi budget qoldig'i va cooldown; UTC/naive sana;
duplicate va concurrent approvals. Mavjud fresh-period test yangi
kelishilgan renewal contract'iga mos yangilanadi.

**Holat:** service va regression testlari yozildi, Python sintaksisi o'tdi.
Testlarni ishga tushirish uchun lokal muhitda `pytest`, SQLAlchemy va FastAPI
yo'q; ular bajarilgan deb hisoblanmaydi.

## 4B — Uzaytirishni foydalanuvchiga ochish — bajarildi

- Direct Android checkout faol paid foydalanuvchiga ochiladi; Play checkout
  cheklovi saqlanadi.
- Profil `Obunani uzaytirish` tugmasini, joriy expiry'ni ko'rsatadi;
  checkout tanlangan davr amaldagi obuna tugaganidan keyin qo'shilishini aytadi.
- Receipt -> pending -> admin approval mavjud yo'l bilan ishlaydi; backend
  activation muddati va AI budgetini ketma-ket saqlaydi.
- Umumiy adapter faol paid checkout'ni default holatda bloklaydi; faqat
  Android direct checkout renewal uchun bu cheklovni ochadi.

**Fayllar:** `desktop_subscription_service.py`, Android profile/navigation/
CheckoutHost, tegishli DTO/testlar. **Qolgan tekshiruv:** renewal paymentni
yuborish, pending/approval, rad etish, muddati va AI budgeti serverdan
qayta olinishi, eski APK parity.

## 5 — UI va chiqarish

- Haqiqiy native oqimda nomlar, statuslar, loading/error matnlari va bitta
  asosiy harakatni aniqlashtirish. To'liq redesign qilinmaydi.
- Har patchning tegishli unit/backend testlari; native Compose/emulator
  va kamida real Android smoke. Course/quiz/homework/progress, login,
  referral va payment approval regressiyasi.
- Amaldagi CI bilan tekshiruv: flavor parity, ikkala flavor unit tests va
  debug build; release oldidan ikkala flavor lint.
- Additive migratsiya/API backendda yangi APKdan oldin chiqadi.
  Agar legacy payment contract o'zgarsa, release tartibi eski APKni
  buzmasligi testda isbotlanadi. Birinchi yangi-APK testidan oldin
  backend mosligi tekshiriladi.
- Release vaqtida `appVersionCode` oshiriladi; APK update orqali
  yangilanadigan imzo saqlanadi. Reja yaratish push/deploy/release emas.

Tekshiruv buyruqlari implementatsiya bosqichida:

```sh
# android/ katalogida
python3 tools/check_flavor_parity.py
./gradlew --no-daemon testDirectDebugUnitTest testPlayDebugUnitTest
./gradlew --no-daemon assembleDirectDebug assemblePlayDebug
./gradlew --no-daemon lintDirectDebug lintPlayDebug
```

Backend uchun tegishli mavjud testlar: `test_subscription_service.py`,
`test_desktop_subscription_api.py`, `test_subscription_miniapp_card_banks.py`,
`test_subscription_miniapp_admin_discount.py`, `test_subscription_miniapp_submit.py`,
`test_android_assistant_service.py`, `test_voice_practice_error_type.py`.
Yangi regressionlar yuqoridagi real failure/approval holatlarini tekshiradi.

Metriclar: checkout open -> payment instructions -> receipt submit ->
approved conversion; userlarning currency/renewal bo'yicha savollari;
AI status/start success, retry success va error-code taqsimoti.
Mavjud analyticsdan boshlanadi, yetishmaydigan eventlar zarur bo'lsagina qo'shiladi.

**Keyingi ish: yakuniy QA va chiqarish.** Besh Android static check, direct/play
debug unit testlari va APK buildlari o'tdi. Direct APK emulatorga o'rnatildi;
login ochildi, til tanlagichi yopiq holatda ko'rindi va bosilganda UZ/RU/TJ
menyusi ochildi; crash kuzatilmadi. Profil, AI retry va Voice call'ni real
akkaunt bilan bosib ko'rish kerak. Backend Python testlari `pytest`, SQLAlchemy
va FastAPI yo'qligi sabab yugurmadi; migratsiya/backend deploy qilinmadi.
Renewal regression testlari yozilgan, Python sintaksisi tekshirilgan.
