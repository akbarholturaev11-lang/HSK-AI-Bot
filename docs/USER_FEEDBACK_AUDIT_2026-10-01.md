# Android foydalanuvchi fikri: audit va tuzatish rejasi

Sana: 2026-10-01. Kod: `fa1d9c76`; Android source versiyasi `1.7.3 / 34`.
Bu hujjat boshlang'ich auditni saqlaydi; undan keyin tegishli native kod va
obuna oqimi tuzatildi.

Bajariladigan patchlar va ularning tugash mezonlari:
[Android tuzatish rejasi](ANDROID_FEEDBACK_FIX_PLAN.md).

## Qamrov va aniqlashtirish

Loyiha egasi tasdiqladi: rasmlardagi foydalanuvchi **Android qurilmada
ilovani sinagan**. Uning o'rnatgan APK versiyasi va aniq xato vaqti noma'lum.
Quyidagi asosiy audit native Kotlin/Compose ekranlari va umumiy backendga tegishli.

Rasmlarda ilova UI yoki xato kodi yo'q; foydalanuvchi interfeysni shablon,
AI ochilishini tushunarsiz, obuna uzaytirishini qiyin va valyutani noaniq deb
baholagan. Bu fikrlar aynan bitta texnik nosozlikni isbotlamaydi.

Oldingi Mini App brauzer auditi solishtirish uchun saqlanadi. Undagi
`barcha 403 -> paywall`, botdagi `Oddiy rejim` nomi va Mini Appdagi yasama
username **Androiddagi tasdiqlangan xatolar emas**. Android native
UI uchun Playwright bilan tekshirilgan deb xabar berilmaydi.

Android `direct` buildida checkout bor; `play` buildida tashqi checkout yo'q.
Narx/valyuta oqimini tuzatish birinchi navbatda `src/direct/`ga tegishli.
Play cheklovini tasodifan ochmaslik kerak. Foydalanuvchining aynan qaysi
APK/builddan foydalangani aniqlanmagan.

`AGENTS.md`, `AI_RULES.md`, relevant `PROJECT_MEMORY.md`, `ANDROID_CONTEXT.md`
va graphify asosiy tugun/communitylari o'qildi. Graph eski `acf35522`dan;
topilmalar joriy kod bilan qayta tekshirildi. Native ilova qurilmada/emulatorda
ishga tushirilmadi; production log, real to'lov va jonli provider tekshirilmadi.

## Fayl qisqartmalari

- `CheckoutHost`: `android/app/src/direct/java/com/pomp/hskai/feature/subscription/SubscriptionCheckoutHost.kt`
- `CheckoutVM`: `android/app/src/direct/java/com/pomp/hskai/feature/subscription/SubscriptionCheckoutViewModel.kt`
- `Settings`: `android/app/src/main/java/com/pomp/hskai/core/settings/AppSettings.kt`
- `Profile`: `android/app/src/main/java/com/pomp/hskai/feature/profile/ProfileScreen.kt`
- `AssistantHost`: `android/app/src/main/java/com/pomp/hskai/feature/assistant/AssistantHost.kt`
- `AssistantController`: `android/app/src/main/java/com/pomp/hskai/feature/assistant/AssistantController.kt`
- `VoiceVM`: `android/app/src/main/java/com/pomp/hskai/feature/voice/VoiceViewModel.kt`
- Native tarjimalar: `android/app/src/direct/res/values*/strings.xml`,
  `android/app/src/main/res/values*/strings.xml` (UZ/RU/TJ).

## 1-qism — Tarif va valyuta

### Sabab va ta'sir

- `PlansContent` faqat sarlavha, tarif va chegirmani chizadi; valyutani
  almashtirish control yo'q (`CheckoutHost:333`). Tanlovga `Orqaga` bilan
  karta davlati ekraniga qaytiladi.
- Birinchi oqim `REGION -> PLANS -> METHOD/PAY` (`CheckoutVM:30`, `:50`, `:82`).
  Foydalanuvchi narxlarni ko'rishdan oldin karta davlatini tanlashi kerak.
- Tanlov telefondagi DataStore `payment_region:v1`ga yoziladi
  (`Settings:174`, `:304`, `CheckoutHost:142`). Logoutda tozalanadi
  (`HskAiApplication.kt:295`, `MainActivity.kt:831`). Bu akkaunt umrida
  bir marta tanlash emas: boshqa qurilma yoki logoutdan keyin yana so'raladi.
- Country narx valyutasi, to'lov usuli va bankni birga boshqaradi
  (`CheckoutVM:40`, `:48`, `:58`, `:61`). `cn` Alipay/WeChatga; `tj`
  DC City/Alif tanloviga; boshqa region Alifga olib boradi.
- Region local narxi yo'q bo'lsa baza narx/valyutaga jim fallback bor
  (`CheckoutHost:550`). RUB tanlagan odam TJS ko'rishi mumkin.

Natija: foydalanuvchi valyutani o'zgartirishni sezmaydi, narxni tashqaridan
so'raydi va xaridni to'xtatadi.

### Fix

1. Checkout darhol tarifdan ochiladi; alohida `Karta davlati` qadami chiqariladi.
2. Tarif ustida doim ko'rinadigan **`Valyuta: RUB — Rossiya rubli ▾`** tugmasi.
3. Serverda tasdiqlangan currency preference yo'q bo'lsa, tarif ustida
   markaziy Compose dialog: **`Narxlarni qaysi valyutada ko'rsatamiz?`**.
   Mavjud narx/usullar yuklanmaguncha yolg'on variantlar chiqarilmaydi.
4. Variantlarda to'liq nom: TJS — Tojik somonisi, UZS — O'zbek so'mi,
   RUB — Rossiya rubli, CNY/¥ — Xitoy yuani, USD — AQSH dollari.
5. Preference serverda akkauntga saqlanadi; native DataStore faqat cache.
   Nullable currency preference, migration, bearer-auth bilan saqlash va
   overview DTO kerak. Saqlash yiqilsa muvaffaqiyat deb ko'rsatilmaydi.
6. Display currency bank/usulni yashirin o'zgartirmaydi. Mavjud VISA va
   Xitoy tariflari saqlanadi; CNY tanlash boshqa baza tarifini jim tanlamaydi.
   Eski APK uchun `card_country/card_bank` contract'i saqlanadi.
7. Yagona mos payment usuli bo'lsa ortiqcha qadam chiqmaydi; muhim xorijiy
   o'tkazma yo'riqnomasi ochiq ko'rinadi. Narx yo'q bo'lsa ochiq sabab/yo'l ko'rsatiladi.

Android ruscha region matni allaqachon `Эквивалент в RUB` deydi
(`direct/res/values-ru/strings.xml:65`); Mini Appdagi `Оплата в RUB`ni
Android xatosi deb hisoblamaslik kerak. Ammo tarifda faqat kod, pay ekranida
`Сумма к оплате` va RUB chiqadi (`CheckoutHost:440`, strings `:73`). Display
equivalent, baza summa va haqiqiy transfer valyutasi izchil tushuntiriladi.

Server kursi bank komissiyasini hisoblamaydi. Real qabul qilinadigan valuta
va rekvizit tekshirilmasdan `pay_amount/pay_currency` o'zgartirilmaydi.
Overview/quote/submit kursni alohida olishi sababli local summa farqlanishi
mumkin; bu mijozda yuz bergani isbotlanmagan, payment testida tekshiriladi.

**Fayllar:** CheckoutHost, CheckoutVM, Settings, native strings,
`FeatureRepository.kt`, checkout API/DTO,
`app/api/android_features.py`, `app/services/desktop_subscription_service.py`,
`app/services/subscription_miniapp_service.py`, kerakli currency service,
User model/repository va Alembic migration.

**Risk: o'rta.** Native currency UI hozir bank routing bilan bog'langan.
**Prevention:** direct unit/Compose testlari; bir akkaunt ikki qurilma,
logout/login, boshqa akkaunt, preference save error; 320/390 dp,
katta shrift, light/dark, UZ/RU/TJ; bank/QR/chegirma/receipt/pending/approval;
eski APK va Play flavour contract'i. Mavjud baza:
`android/app/src/testDirect/java/com/pomp/hskai/feature/subscription/SubscriptionCheckoutFlowTest.kt`.

## 2-qism — Obunani topish va uzaytirish

**Sabab:** native profildagi `AccessPill` faqat status, bosilmaydi
(`Profile:537`); profil callbacklarida checkout kirishi yo'q (`Profile:99`).
Faol paid checkout esa `HSK AI Pro активен` + `Проверить ещё раз` ko'rsatadi
(`CheckoutHost:204`, direct ruscha strings `:33`, `:38`). Bu foydalanuvchiga
qayerdan uzaytirishni tushuntirmaydi.

Bu faqat tugma muammosi emas. Android adapteri umumiy
`DesktopSubscriptionService`dan foydalanadi (`app/api/android_features.py:963`).
U faol paid xaridni 409 bilan bloklaydi (`desktop_subscription_service.py:78`).
Sabab: `SubscriptionService.activate_plan()` qolgan paid kunlarni saqlamasdan
`end_date = now + duration` qiladi (`subscription_service.py:62`, `:71`).
20 kun qolgan odam 30 kun olsa, kutgan 50 kun o'rniga bugundan 30 kun chiqadi.
Bu reset mavjud testda ham saqlangan (`tests/test_subscription_service.py:163`).

Yangi to'lov AI budgetni ham yangidan yaratib, eski active budgetni expire
qiladi va qoldiqni o'tkazmaydi (`ai_usage_budget_service.py:93`, `:105`, `:172`).
Resolver bir nechta active budgetdan yangisini saqlaydi (`:227`). Shuning
uchun faqat expiry sanasini yoki faqat UI tugmasini o'zgartirish yetarli emas.

**Fix tartibi:** markaziy paid renewal + AI budget qoidasi, transaction,
parallel/takror approval testlari; keyin profilda aniq obuna kirishi,
expiry va holatga mos `Obuna olish / Uzaytirish / Tiklash`; shundan keyin
native active-paid guard ochiladi. Guardni oldindan ochish mumkin emas.

**Fayllar:** Profile, MainActivity navigation, CheckoutHost,
`subscription_service.py`, `ai_usage_budget_service.py`, approval oqimi,
`desktop_subscription_service.py`, tests.
**Risk: yuqori backend, past UI. Prevention:** paid/expired/trial/temp,
qolgan kunlar/budget, cooldown, ikki approval va eski klientlar regressioni.

## 3-qism — Android AI kirishi va xato holatlari

Androidda ikki oqim bor: suzuvchi **AI yordamchi chat** va alohida
**AI Voice tab**. Botdagi `Oddiy rejim` Android kirishi emas.

Tasdiqlangan topilmalar:

- FAB faqat authenticated va assistant ruxsat etilgan ekranda chiqadi
  (`AssistantHost:185`, `:195`). Darsda `showButton=false` ataylab qo'yilgan
  (`MainActivity.kt:1377`, `:1381`; `ANDROID_CONTEXT.md:999`). Offline holatda
  ham yashirin (`ANDROID_CONTEXT.md:1121`). Mavjud qarorni bilmasdan tugmani
  hamma ekranga qaytarish tavsiya qilinmaydi.
- Assistant status so'rovi xatosi `attach()`da yutiladi
  (`AssistantController:157-160`); `enabled=false` qolishi mumkin. Status
  auth o'zgarganda so'raladi (`AssistantHost:186`), lekin chat open/retry
  uni qayta so'ramaydi (`AssistantController:205`, `:331`). Darsdagi
  kontekstli AI action `enabled=false`da berilmaydi (`MainActivity.kt:1385`).
  Bu aynan mijozdagi nosozlik sababi ekani tasdiqlanmagan.
- Limit/subscription/budget xatolari bitta `assistant_limit`ga, qolgan
  kodlar ko'pincha `assistant_network`ga tushadi (`AssistantHost:928-935`).
  Serverning `ai_budget_cooldown`, `ai_budget_depleted`,
  `access_payment_pending_review`, `access_blocked` sabablarini yo'qotishi
  mumkin (`app/services/assistant_service.py:205`). Error transport
  `limit_text/reset_at`ni saqlamaydi (`AssistantController:32`).
- Asosiy FAB server statusidagi `enabled`ni tekshirmaydi (`AssistantHost:185`);
  servis o'chirilgan bo'lsa `assistant_disabled` umumiy network xabari bo'ladi.
  Productionda servis bayrog'i o'chiqligi tasdiqlanmagan.
- AI Voice ilk status yuklanmasa Start disabled qoladi
  (`VoiceVM:148`, `VoiceScreen.kt:548`), xato blokida shu ekranning o'zida
  aniq retry yo'q (`VoiceScreen.kt:221`). Tabdan qayta kirish so'rovni
  takrorlashi mumkin; foydalanuvchi buni bilishi kerak emas.
- Native Voice start failure `ApiError` sifatida state'ga uzatiladi
  (`VoiceVM:201`); Mini Appdagi barcha 403 -> paywall xatosini bu oqimga
  ko'chirib xulosa qilishga dalil yo'q.

**Fix:** chat va Voice kirishini alohida aniq nomlash; foydalanuvchi qayerda
AIga kira olishini tushuntirish; status loading/failed/retry holatini
ko'rsatish va failed statusni chat ochilishida qayta tiklash; Voice xato
blokiga `Qayta urinish -> loadStatus()` qo'shish;
network/auth/provider/limit/cooldown holatlarini ajratish.
AI haqiqatan ishlamaganmi yoki topilmaganmi — o'rnatilgan APK va shu
vaqtdagi `/api/v3/android/assistant` yoki voice logi bilan ajratiladi.

**Fayllar:** AssistantHost, AssistantController, AssistantApi,
VoiceVM/VoiceScreen, tegishli ApiError mapping va native strings.
**Risk: o'rta. Prevention:** online/offline, status failure/retry, paid
cooldown, free reset, auth expiry, provider timeout va course context testlari.
Limit yoki access siyosati o'zboshimchalik bilan oshirilmaydi.

## 4-qism — Android interfeys ishonchi

`Shablon` taassuroti subyektiv; yuborilgan rasmlarda native ilova UI yo'q.
Mini Appdagi yasama username Androidga tegishli dalil emas. To'liq redesign
uchun asos yetarli emas.

**Fix:** aniq APKda kurs -> AI -> profil -> obuna yo'lini ko'rish, Android
matn/nomlarining izchilligi va har ekrandagi asosiy harakatni tekshirish;
faqat dalilli, kichik patchlar. Kurs core mahsulotligicha qoladi.
**Risk: past**, payment/accessga tegilmasa. **Prevention:** haqiqiy telefon,
UZ/RU/TJ, katta shrift, light/dark va learning/result regressiyasi.

## Tekshiruv va bajarish tartibi

Boshlang'ich native audit kod o'qish orqali bajarilgan; quyidagi keyingi
tekshiruvlar esa implementationdan keyingi holatni ko'rsatadi.
Oldingi Chromium 320×667 / 390×844 tekshiruvlari faqat Mini App va mock
SDK/API bilan edi. Natija fayli:
`output/playwright/feedback-audit-2026-10-01/audit-results.json`.
U Android AI yoki checkout ishlashining runtime dalili emas.

| Qism | Holat | Natija |
|---|---|---|
| Android audit | Bajarildi | Native manbalar va umumiy backend bo'yicha qayta aniqlashtirildi |
| 1. Valyuta/tarif | Bajarildi | Native selector, birinchi ochilish dialogi, country qadamisiz checkout |
| 2. Uzaytirish | Bajarildi | Profil ichida boshqaruv; muddat va AI budgetini saqlaydigan renewal |
| 3. AI | Bajarildi | Chat status retry, aniq xato holatlari, Voice status retry |
| 4. UI ishonchi | Qisman bajarildi | Login til dropdowni, Voice chat/fon/panda, markazlangan natija va xatolar |

Hozirgi qoldiq — yakuniy, akkaunt talab qiladigan Voice/Profile/payment
oqimlarini real test akkaunti bilan tekshirish va migratsiya/backend deploy
tartibini tasdiqlash. Android unit/build tekshiruvlari holati fix plan'da
yangilanadi.
