# Android / Mini App qayta auditi — 2026-10-02

**Xulosa: barcha o'zgarishlar hali mos emas.** Profilning yangi Mini App
ko'rinishi shu checkoutda ishlaydi, ammo `codex/local-ai`ga yetmagan.
Voice audio oqimi, Mini App valyuta oqimi va bir nechta UI holati qolgan.
Ushbu audit mahsulotdagi kamchiliklarni tuzatdi degani emas.

## Tekshirilgan nusxalar

- Joriy checkout: `e185`, detached `1cc31fd0`, Mini App profil patchi dirty.
- Lokal va GitHub `codex/local-ai`: `d72144a76b97971c88ed34125eb0e2ad0f30a99c`.
  Remote ref `git ls-remote` bilan qayta tekshirildi.
- GitHub `main`: `a348fb169f57113056b74a70276f7d49d57cbe64`.
- Emulator: o'rnatilgan `com.pomp.hskai.debug`, `1.8.0-debug`, versionCode 35.
  Joriy e185 APK versionCode 34; install downgrade sabab rad etildi.
  Ma'lumotlar o'chirilmadi va downgrade majburlanmadi. Emulator UI natijasi
  o'rnatilgan v35ga tegishli; u e185 APKning aniq runtime isboti emas.

e185 va local-ai tarixlari 1 / 479 commitga ajralgan. local-ai'da HSK 3.0
va boshqa keyingi funksiyalar bor. e185 fayllarini to'liq uning ustiga
ko'chirish mumkin emas; faqat kerakli patchlarni ajratib o'tkazish kerak.

## Talablar holati

| Talab | Android | Mini App | Baho |
|---|---|---|---|
| Profil sarlavhasi, qarama-qarshi tomonda Sozlamalar gear | Bor | e185 dirty patchda bor; local-ai'da eski | Branchga o'tkazish qoldi |
| To'liq Profil va ichida obuna/uzaytirish | Bor; emulator v35da ko'rildi | Tugma bor; juda pastda | Joylashuv farqi bor |
| Til tanlovini bosib ochish | Login dropdown yopiq boshlanadi | Telegram login; Settings til picker bosib ochiladi | Mos vazifa, alohida Mini login talab qilinmaydi |
| AI Voice ichida umumiy AI FAB yo'qligi | `showButton=false` | Voice overlayda FAB ko'rinmadi | Mos |
| Panda orqasida real uy foni | Bor | Bambuk SVG | Mos emas |
| Chatni yopib pandani kattalashtirish | Bor | Yo'q | Mos emas |
| Chap/o'ng chat pufakchalari | To'liq kenglikdagi kartalar | Bor | Android patchi qolgan |
| Markazlangan suhbat yakuni | Bor | O'z result overlay'i bor | Asosiy joylashuv bor |
| Asl xatolar va foydalanuvchi javobi | Server correction ko'rsatiladi | Correction, kategoriya, so'zlar va transcript | Natija tafsilotlari farq qiladi |
| Tarifdan boshlash, ko'rinadigan valyuta tanlovi | Bor | Hali karta davlati birinchi | Mos emas |
| Ilk valyuta dialogi va akkauntga saqlash | Bor | Region localStorageda; shared preference ishlatilmaydi | Mos emas |
| Qolgan paid kun/budget bilan renewal | Shared backend testlari o'tdi | Shu backenddan foydalanadi | Server contracti umumiy |
| Feedback draftini har release'da tayyorlash qoidasi | Olib tashlangan | Repo umumiy qoida | Bajarilgan |

Feedback haqidagi so'rov draft yaratish **qoidasini** olib tashlash edi.
`fc925aad` shu talabni AGENTS/AI_RULES/ARCHITECTUREdan olib tashlagan.
Mavjud feedback kampaniyasi, referral va chegirma mahsulot funksiyasini
o'chirish bu so'rovga kirmagan.

## Topilmalar va minimal tuzatish tartibi

### 1. P1 — Android AI javoblari salomlashuvdan keyin ovozsiz

- Sabab: `VoiceViewModel.kt:198` opening uchun `speak()` chaqiradi,
  `applyTurn():253` esa keyingi javob uchun chaqirmaydi.
  Mini `course-v3.html:6866` har javobni o'qiydi.
- Ta'sir: Voice suhbat matnli chatga aylanadi; o'quvchi AI javobini eshitmaydi.
- Fix: normal turn uchun speech; recording/text/end/reset/swap/clear oldidan
  eski speechni to'xtatish. `speakJob.cancel()` bilan birga
  `LessonAudioPlayer.release()` kerak: `play()` audio boshlangach qaytadi.
- Qo'shimcha sabab: `toggleRecording():208` ovozni to'xtatmaydi.
  Panda ovozi user transkriptiga tushishi mumkin; Mini `startRecording()`
  allaqachon `stopSpeak()` ishlatadi.
- Fayllar: `android/.../feature/voice/VoiceViewModel.kt`, audio regression test.
- Risk: o'rta. Prevention: greeting + ikki turn ovozi, speaking paytida mic,
  eski TTS response, end/resetdan keyin playback testlari.

### 2. P1 — Mini App valyuta/to'lov oqimi eski

- Sabab: `subscription.html:211` birinchi ekran `country`; `flow():890`
  ham country-first. `:869` narx valyutasi regionga bog'langan.
  Mustaqil currency selector/dialog va akkaunt preference API yo'q.
- Ta'sir: foydalanuvchi valyutani tarifdan almashtira olmaydi; Androiddagi
  tanlov Mini Appga o'tmaydi, ortiqcha qadam qoladi.
- Fix: plans-first; doim ko'rinadigan currency tugmasi; ilk markaziy dialog;
  Telegram-auth bilan shu `user.subscription_currency`ga saqlash.
  Display currency bank/usulni jim o'zgartirmasin.
- Fayllar: `app/static/subscription.html`, `app/main.py`,
  `subscription_miniapp_service.py`, umumiy currency service va testlar.
- Risk: o'rta. Prevention: barcha 5 currency, akkauntlar/qurilmalar,
  save failure, pending, bank/QR/discount/receipt va eski klientlar.

### 3. P1 — local-ai HSK 3.0 checkoutida currency save noto'g'ri narxlarni yozadi

- Faqat d721/local-ai'da: `SubscriptionCheckoutViewModel.kt:220` response
  pricesni overviewga almashtiradi. Backend `android_features.py:1093`
  preference response narxlarini doim `mode="subscription"` bilan oladi.
- Ta'sir: `hsk30_unlock` narxi yo'qoladi; HSK 3.0 kartasi/Continue yo'qolishi
  koddan kelib chiqadi. Joriy e185 bu mahsulot funksiyasini o'z ichiga olmaydi.
- Fix: preference savedan keyin original origin/mode bo'yicha overviewni
  qayta olish; subscription price bilan boshqa mahsulotni almashtirmaslik.
- Fayllar: direct `SubscriptionCheckoutViewModel.kt`, mode regression test.
- Risk: o'rta. Prevention: ilk dialog va keyingi currency change holatida
  `hsk30_unlock`, narx, mode va Continue saqlanishi.
- Dalil: source trace; runtime'da bu xarid bajarilmadi.

### 4. P1 — Mini profil patchi intended branchga yetmagan

- d721 `course-v3.html:5738/5753` eski Profil pill va pastki Settings qatorini,
  `:5566` paid kartani renewal tugmasisiz saqlaydi.
- e185 yangi gear/title/renewal patchi commit/push qilinmagan.
- Fix: faqat shu Mini patch va testlarni local-ai'ga o'tkazish; uning HSK 3.0
  va boshqa o'zgarishlarini saqlash. `main`ga push bu auditda bajarilmadi.
- Risk: o'rta (branch divergence). Prevention: yakuniy branchdan native build,
  Mini smoke, diff va remote commitni tekshirish.

### 5. P2 — Android chat yopilganda xato ham yashirinadi

- `VoiceCallScreen.kt:186–191` faqat ochiq chatda `CallChat`ni chizadi;
  xato `:417` ichida. Yopiq chat statusida error branch yo'q.
- Fix: umumiy ko'rinadigan error/retry hududi; har ikkala chat rejimida
  server, mic, timeout va auth xatosi chiqsin.
- Fayl: `VoiceCallScreen.kt`. Risk: past.
- Prevention: transcriptVisible=false + har bir failure uchun UI test.

### 6. P2 — Voice ko'rinishi va tuzatish joyi mos emas

- Mini `course-v3.html:6593` bambuk SVG ishlatadi; chat toggle yo'q.
  Haqiqiy Chromium DOM auditida toggle soni 0, room asset yo'q.
- Android `VoiceScreen.kt:453–470` ikkala speaker uchun fillMaxWidth karta
  ishlatadi. Mini chap/o'ng, max-width 84% pufakcha ishlatadi.
- Android `VoiceViewModel.kt:267–278` user correctionni AI line'ga qo'shadi;
  Mini `:6862–6864` uni user pufakchasiga biriktiradi.
- Fix: Mini'ga uy asseti va chat toggle; Androidga chap/o'ng pufakcha va
  correctionni tegishli user line'ga ko'chirish.
- Fayllar: `course-v3.html`, Mini room asset, `VoiceScreen.kt`, `VoiceViewModel.kt`.
- Risk: past/o'rta. Prevention: uzun xabar, subtitles, keyboard, toggle,
  correction, 320/390 px, UZ/RU/TJ va safe area.

### 7. P2 — Android result tafsilotlari kam

- `AndroidFeatureDto.kt:1014–1043` error_type, errors_by_type, target_used
  maydonlarini olmaydi. Mini `course-v3.html:6914–6929` ularni ko'rsatadi.
- Fix: existing server maydonlarini olish va yakunda kategoriya/so'zlar,
  asl user gapi hamda tuzatishni ko'rsatish.
- Fayllar: DTO, `VoiceScreen.kt`, tarjimalar. Risk: past/o'rta.
- Ikkala klient bir `VoicePracticeService`dan foydalanadi. Correction asl
  user phrase bilan Xatolarimga saqlanadi. Akustik/ton tahlili yo'q; baholash
  transkript asosida. Barcha talaffuz xatosi aniqlanadi deb tasdiqlanmadi.

### 8. P2 — Mini Voice cooldownni obuna yetishmasligi deb ko'rsatadi

- `onStartError()` `course-v3.html:6749` har qanday 403ni paywallga yo'naltiradi.
  `VoicePracticeService._ensure_budget_available():578` cooldown/depleted
  kabi sabablarga ham 403 beradi.
- Fix: code bo'yicha bloklash sababi, kutish/retry va to'g'ri harakatni
  ko'rsatish; faqat haqiqiy free limit uchun upgrade CTA.
- Fayl: `course-v3.html`, failure E2E. Risk: past/o'rta.

### 9. P2 — Obuna topilishi va Settings safe-area

- Android obuna kartasi hero'dan keyin. Mini `renderProfile():5553–5555`
  uni kalendar/achievementlardan keyin qo'yadi.
- Browserda renewal tugmasi y=1233–1303 px; viewport 667/844 px.
  UZ/RU/TJda ham birinchi ekrandan tashqarida.
- Fix: Mini obuna kartasini hero'dan keyinga ko'chirish.
- Native `ProfileScreen.kt:774` Settings body scrollsiz Column.
  Emulatordagi v35da font_scale=1.5 bilan title status bar ostiga chiqdi.
  Default 1.0da logout/unlink ko'rinadi. Sinovdan keyin font 1.0ga tiklandi.
- Fix: sheet uchun safe drawing inset, bounded scrollable content.
- Fayllar: `course-v3.html`, `ProfileScreen.kt`/sheet wrapper. Risk: past.
- Prevention: kichik ekran, 1.0/1.5/2.0 shrift, barcha qatorlar yetib borishi.

### 10. P2 — e185 eski Android trial CTAni saqlagan

- e185 `ProfileScreen.kt:511–535`/`MainActivity.kt:1233` trial CTAga ega;
  d721 uni limit flowda qoldirib, Profildan olib tashlagan.
- `test_trial_entry_points` shu regressiyani ushlaydi. Test zaiflashtirilmadi.
- Fix: yakuniy patchni d721 asosiga o'tkazish; e185 trial CTAni qaytarmaslik.
  Mini'dagi mavjud trial entry ataylab alohida saqlangan; biznes qoidasini
  ushbu audit asosida o'zgartirmaslik.

## Sinov dalillari

- Android 5 static check: passed (interface fakes, named args, flavor parity,
  UZ/RU/TJ strings, Mini palette).
- Gradle direct/play unit-test va APK build tasklari: BUILD SUCCESSFUL;
  o'zgarmagan manbalar uchun cache UP-TO-DATE. Joriy XML natijalari:
  direct 383, play 354 test; 0 failure/error.
- Chromium Mini App focused suite: **21 passed**. App/lesson routing,
  recognition, exam score, subscription quote/receipt yo'li, profil gear,
  renewal navigation, Voice greeting/reply/correction/hints/result/keyboard.
- Qo'shimcha browser: UZ/RU/TJ × 320×667/390×844 — 6 profil holati;
  title/settings ochilishi to'g'ri, pageerror va horizontal overflow yo'q.
  API/SDK mock; bu jonli to'lov yoki AI provider isboti emas.
- Backend/source focused run: 213 passed, 130 subtests passed; 1 e185 trial
  static failure va 3 eski currency-test subfailure. Log:
  `output/playwright/parity-audit-2026-10-02/backend-tests.txt`.
  Currency test yangi explicit-currency contractiga moslandi: til/currency
  mustaqilligi, barcha 5 currency va canonical narxlar saqlanishi tekshiriladi.
  Tuzatilgan currency/auth subset: 4 passed, 57 subtests passed.
  e185 trial static regressiyasi ochiq qolgan; to'liq suite green deyilmaydi.
- `git diff --check`: passed; `graphify update .`: bajarildi.

Auditda faqat test harness tuzatildi: queryli desktop status mocklari,
trial/ad uchun default mock, coach speechga ko'chgan review selektori,
currency GET/PUT route inventory va explicit-currency unit fixture.
Avvalgi 3 E2E failure shular bilan
qayta tekshirib yo'qoldi. Mahsulot kamchiliklari testni yumshatib yashirilmadi.

Browser JSON/screenshot: `output/playwright/parity-audit-2026-10-02/`.
Native Profile/Settings screenshots: `/private/tmp/hsk-audit-*-20261002.png`.
Browser fixture tashqi icon stylesheetni mock qiladi; screenshot icon
glyphlarining production yuklanishini tasdiqlamaydi.

## Yakunlash mezoni

Avval d721 asosida patchlarni yig'ish; audio va HSK30 currency xatosini
tuzatish; Mini currency/Voice parity; profil/settings/result tafsilotlari.
Keyin ikkala klientni bitta backendda test qilish va local-ai'da test/push.
Jonli voice recording/TTS, payment submit → approval → access, migratsiya
va backend deploy ushbu auditda bajarilmadi. Hamma mahsulot oqimlari to'liq
tekshirildi yoki ish 100% tugadi deb xabar berish uchun hali asos yo'q.
