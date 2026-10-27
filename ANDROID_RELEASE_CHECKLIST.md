# Android — nima qilish kerak

Bu fayl esdan chiqmasligi uchun. Har safar ochib, ustidan yurib chiqing.

---

## 0. JORIY RELEASE HOLATINI TEKSHIRISH

Universal akkaunt o‘zgarishlari `codex/universal-sign-in`da ushlab turiladi.
Kod va `docs/UNIVERSAL_NATIVE_ACCOUNTS.md`dagi qabul tekshiruvlari tugamaguncha
ularni `main`ga push/merge qilmang, production backend yoki yangi ilovani
tarqatmang. Hozirgi Play release uchun xarid talab qilinmaydi: u mavjud
entitlement’ni o‘qiydi; Direct APK chek/admin orqali xaridni qo‘llaydi.

Bu faylda jonli release holati saqlanmaydi. Release yoki muammoni tekshirishdan
oldin:

- GitHub Actions’dagi eng so‘nggi **Android release** run natijasini tekshiring;
  workflow `workflow_dispatch` orqali qo‘lda boshlanadi.
- R2’dagi `android/latest.json` manifestini va uning `version_code` qiymatini
  ko‘ring; fayl mavjudligi yoki serverga deploy qilinganini checkoutning o‘zi
  tasdiqlamaydi.
- `ANDROID_RELEASE_MANIFEST_URL` konfiguratsiyasi production’da yoqilganmi va
  botning hozirgi APK holatini deployed server/admin paneldan tasdiqlang.

Quyidagi release qadamlarida source code va workflow kontrakti berilgan; bu
jonli release yoki ishlab turgan server holati deb talqin qilinmasin.

## 1. HAR SAFAR yangi versiya chiqarganda

Asosiy yo‘l — GitHub release workflow: uni har release’da qo‘lda ishga tushiring
(1.2), sozlamalarini 2-bo‘limdan tekshiring. `ANDROID_RELEASE_MANIFEST_URL`
ishlatilmasa yoki manifest o‘qilmasa, pastdagi bot-panel fallback’iga o‘ting.
Har ikki yo‘ldan keyin 1.3 dagi qurilma tekshiruvini bajaring.

### 1.1 Versiya raqamini oshiring — BU ENG KO'P UNUTILADIGANI

`android/app/build.gradle.kts` dagi `appVersionName` va `appVersionCode` —
build versiyasining source of truth’i. Yangi release’da nomni yangilang va
`appVersionCode` ni R2’dagi eng so‘nggi e’lon qilingan qiymatdan kattaroq
qiling; aniq `+1` shart emas. Teng yoki past code bilan yangi artifact
chiqarmang. Workflow past code’ni rad etadi, ammo teng code’li boshqa
artifact’ni alohida to‘xtatmaydi — publishdan oldin `android/latest.json`
bilan qo‘lda solishtiring. Aynan bir xil APK’ni rerun qilish mumkin.
Android’ning keyingi release uchun kattaroq qiymat talab qiladigan
[rasmiy versiya qoidasiga](https://developer.android.com/studio/publish/versioning)
ham amal qiling. Bu hujjatdagi eski raqamlarni yangi release uchun ko‘chirmang.

### 1.2 GitHub release workflow

**Actions → Android release → Run workflow.**

Workflow faqat qo‘lda ishga tushadi. U statik tekshiruvlar, Android test/lint
va emulator regressiyalarini bajaradi, APK imzosini tekshiradi va artifact
yaratadi. `publish_to_r2` default `true`; uni `false` qilsangiz APK R2’ga
chiqmaydi. Muvaffaqiyatli publish `android/latest.json` ni ham yangilaydi.
Run summary’da publish natijasini, Actions run’dagi Artifacts bo‘limida esa APK’ni
tekshiring.

Production’da `ANDROID_RELEASE_MANIFEST_URL` sozlangan bo‘lsa, server manifestni
o‘qiydi; default cache muddati 60 soniya. Sozlama/deploy holatini Actions run
yoki checkout kodi tasdiqlamaydi. Bot manifestdagi APK’ni `/android` so‘ralganda
R2’dan bir marta olib Telegram `file_id` sini saqlaydi; keyin shu buildni
Telegram’dan qayta yuboradi.

---

### Manual fallback — manifest ishlatilmayotganda

Production `ANDROID_RELEASE_MANIFEST_URL` bo‘sh bo‘lsa yoki manifestni o‘qib
bo‘lmasa, bot admin panelidagi release ishlatiladi. Yaroqli manifest mavjud
bo‘lsa u ustun turadi; panelga yuklangan APK amalda tarqatilayotgan buildni
almashtirmaydi. Bunday holatda GitHub release workflow’dan foydalaning.

**Yig‘ish:**

```bash
cd android && ./gradlew assembleDirectRelease
```

`direct` + `release` imzolangan APK’ni yuboring. Build fayli
`hsk-ai-<versiya>-<kod>-direct-release.apk` ko‘rinishida chiqadi; nomini
o‘zgartirmang. Admin panel `play` yoki `debug` build’ni rad etadi.

**Bot admin panelida chiqarish:**

1. Android ilova panelida **Yangi APK yuklash**ni tanlab, APK’ni siqmasdan,
   hujjat sifatida yuboring va chiqish tasdig‘ini bering.
2. Ilova ichidagi yangilash kerak bo‘lsa, **Yangilanish havolasini qo‘shish**ni
   tanlang va aynan shu APK’ning to‘g‘ridan-to‘g‘ri `https://...apk` URL’ini
   kiriting (masalan, public R2 URL).
3. **O‘zimga yuborib ko‘rish** bilan Telegram faylini, avvalgi versiyadagi
   qurilmada esa yangi-versiya kartasi va o‘rnatishni tekshiring.

Yangi APK chiqarilganda oldingi release yozuvi va update URL o‘rniga yangi
release yoziladi. O‘z-o‘zini yangilash havolasi kerak bo‘lsa, yangi build uchun
uni qayta kiriting.

### 1.3 Tekshirish

- [ ] **📤 O'zimga yuborib ko'rish** — fayl keldimi, versiyasi to'g'rimi?
- [ ] Eski versiyali telefonda Profilga kiring — «Yangi versiya» kartasi chiqdimi?

## 2. GitHub release workflow sozlamalari

`.github/workflows/android-release.yml` allaqachon mavjud va har release’da
Actions’dan qo‘lda ishga tushadi. Repo checkouti GitHub’dagi secret/variable
qiymatlari borligini yoki workflow avval muvaffaqiyatli ishlaganini ko‘rsatmaydi;
release’dan oldin Settings va eng so‘nggi Actions run’ni tekshiring.

**Actions → Settings → Secrets and variables → Actions** ichida:

| Turi | Nomi | Qachon kerak |
|---|---|---|
| Secret | `POMP_ANDROID_KEYSTORE_BASE64` | Har run; release `.jks` faylining base64 qiymati |
| Secret | `POMP_ANDROID_KEYSTORE_PASSWORD` | Har run |
| Secret | `POMP_ANDROID_KEY_ALIAS` | Har run |
| Secret | `POMP_ANDROID_KEY_PASSWORD` | Har run |
| Variable | `POMP_FIREBASE_APP_ID`, `POMP_FIREBASE_SENDER_ID`, `POMP_FIREBASE_PROJECT_ID`, `POMP_FIREBASE_API_KEY` | Har run; payment push build configuration |
| Secret | `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_ACCOUNT_ID`, `R2_BUCKET` | Faqat `publish_to_r2=true` bo‘lsa |
| Variable | `R2_PUBLIC_BASE_URL` | Faqat R2 publish uchun |

Local release keystore uchun base64 qiymatni quyidagicha olasiz; command
natijasi secret bo‘lgani uchun uni hujjatga, chatga yoki logga qo‘ymang:

```bash
base64 -i ~/.pomp-hskai/pomp-hskai-release.jks | tr -d '\n' | pbcopy
```

Serverdagi `ANDROID_RELEASE_MANIFEST_URL` default bo‘yicha bo‘sh. Production
server manifestni avtomatik ishlatishi kerak bo‘lsa, deployment variable’ni
R2’dagi `android/latest.json` URL’iga sozlab, deployed serverdan manifest
o‘qilishini tekshiring. Variable yoki live deployment holati bu repo’dan
tasdiqlanmaydi; bo‘sh bo‘lsa botning manual admin-panel release yo‘li ishlaydi.

---

## 3. YO'QOTIB QO'YMANG

**Imzo kaliti:** `~/.pomp-hskai/pomp-hskai-release.jks`
**Paroli:** `~/.pomp-hskai/MUHIM-OQING.txt`

Bu ikkisi yo'qolsa — ilovaga **boshqa hech qachon yangilanish chiqara olmaysiz**.
Har bir foydalanuvchi eski ilovani o'chirib, yangisini qaytadan o'rnatishga
majbur bo'ladi.

Ikkalasini ham parol menejerida zaxiralang. Bugun.

---

## 4. Google Play — 2026-10-14 tayyorgarlik

Google tekshiruvi boshlangan, ammo akkaunt va ilova hali tasdiqlangan deb
hisoblanmaydi. Eskirgan qisqa checklist o‘rniga quyidagi hujjatdagi aniq
release va policy talablarini tekshiring:

**[Google Play launch readiness](docs/GOOGLE_PLAY_LAUNCH_READINESS_2026-10-14.md)**

Muhim:

- Mavjud direct APK signing key'ini birinchi Play App Signing uchun
  **app signing key** sifatida import qilish kerak. Bu upload key bilan bir
  xil tushuncha emas; Google yangi app signing key yaratsa, eski APK
  o‘rnatmalari ustiga Play yangilanishi ishlamasligi mumkin.
- Play Console ruxsatisiz chiqarishni boshlamang. Yangi personal developer
  akkauntlarda 12 tester / 14 kun closed testing talabi bo‘lishi mumkin.
- Play kanalida hali Google Play Billing yo‘q: hozircha consumption-only.
- Google/Apple orqali kirgan, Telegramga ulanmagan foydalanuvchi uchun
  account deletion oqimini tekshirish va to‘ldirish kerak.
- **Actions -> Android Play preflight** signed direct APK va Play AAB
  sertifikatlarini solishtiradi, lekin Google'ga avtomatik yuklamaydi.

---

## Nima nima uchun

**Ikkita build bor.** `direct` — bot va sayt orqali tarqatiladi, ichida to'lov
yo'li bor, o'zini yangilay oladi. `play` — Play Market uchun, ichida tashqi
to'lov yo'li ham, yangilanish kodi ham **umuman yo'q** (Google ikkalasini ham
taqiqlaydi). Bu farq kodda emas, alohida papkalarda — ya'ni Play build'da u
kodning o'zi yo'q, yashirilgan emas.

**Admin update policy (PR #247; not live):** `BotSetting.android_update_allowed_versions` defaults to 4; Admin PWA 1/2/3/4 represent *actually published releases*, not versionCode gaps. Direct appends confirmed R2 publications to `android/latest.json` history without changing its APK download and installer. Play's opt-in `.github/workflows/android-play-release-mirror.yml` reads **production** from Google Play Developer API and writes an independent R2 `android/play-releases.json` list (inProgress/completed only; never drafts or halted releases). The Play app checks actual per-user Google Play Core availability before requesting Immediate Update. Enable Play mirror only after setting GitHub var `ANDROID_PLAY_RELEASE_SYNC_ENABLED=true`, secret `ANDROID_PLAY_SERVICE_ACCOUNT_JSON` with Android Publisher API production access and existing R2 credentials. Existing unknown history is never fabricated from code gaps or R2 APK objects: lockout remains OFF when fewer than N verified published releases are available. Releasing an Android update with this feature is required for installed clients to obey it; CI and device QA are mandatory before merge or rollout.

**Yangilanish jim emas.** Android sideload qilingan ilovada har doim o'z
o'rnatish dialogini ko'rsatadi. Bir bosish + dialog. Foydalanuvchiga «avtomatik
yangilanadi» deb aytmang. Jim yangilanishni faqat Play Market beradi.

> **2026-10-22 Play code audit (newer):** [Play release code audit and Data Safety checklist](docs/GOOGLE_PLAY_RELEASE_AUDIT_2026-10-22.md). Follow the new audit's test and signing gates before any Play submission; this older checklist is not proof of live release status.
