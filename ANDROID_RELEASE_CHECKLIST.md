# Android — nima qilish kerak

Bu fayl esdan chiqmasligi uchun. Har safar ochib, ustidan yurib chiqing.

---

## 0. HOZIR

Bajarilgan:

- [x] APK botga yuklandi
- [x] R2'ga qo'yildi
- [x] Yangilanish havolasi botga berildi
- [x] Server jonli tekshirildi — eski versiya so'raganda yangilanish beradi,
      hozirgi versiya so'raganda hech narsa bermaydi, `/downloads/android` ishlaydi

Qolgan:

- [ ] **Botdagi APK'ni almashtirish.** Botdagi fayl R2 dagidan boshqa
      (3 766 687 bayt ≠ 3 784 820 bayt). Botdagisi — yangilanish kodi
      yozilishidan OLDINGI build. Ya'ni botdan yuklab olgan odamda
      yangilanish kartasi bo'lmaydi.

      **Admin panel → 📱 Android ilova → ⬆️ Yangi APK yuklash** → yangi faylni
      yuboring. Keyin havola avtomatik o'chadi, shuning uchun
      **🔗 Yangilanish havolasini qo'shish** ni qaytadan bosib, o'sha havolani
      qayta tashlang:

      ```
      https://pub-9b135bd734b04a5e9fe059a4dfd7d804.r2.dev/android/v1.1.0/hsk-ai-1.1.0-2-direct-release.apk
      ```

- [ ] **📤 O'zimga yuborib ko'rish** — kelgan faylni telefonga o'rnating
- [ ] Ilovani ochib, Profilga kiring — hammasi joyidami?

## 1. HAR SAFAR yangi versiya chiqarganda

Ikki yo'l bor. Avtomat yoqilgan bo'lsa (2-bo'limga qarang) — faqat 1.1 va 1.2.

### 1.1 Versiya raqamini oshiring — BU ENG KO'P UNUTILADIGANI

`android/app/build.gradle.kts` faylida, tepada:

```kotlin
val appVersionName = "1.2.0"   // odamlar ko'radigan raqam
val appVersionCode = 3         // ← BUNI HAR SAFAR +1 QILING
```

**`appVersionCode` oshmasa, hech kim yangilanishni ko'rmaydi.** Ilova faqat shu
raqamni solishtiradi, nomni emas.

### 1.2 AVTOMAT: GitHub'da tugmani bosing

**Actions → Android release → Run workflow.**

Bo'ldi. U o'zi: testlardan o'tkazadi, imzolaydi, R2'ga qo'yadi va
`android/latest.json` ni yangilaydi. Server bir daqiqada yangi versiyani
ko'radi. **Havolani hech qayerga tashlash kerak emas.**

Botdagi fayl ham o'zi yangilanadi: birinchi odam `/android` so'raganda bot
faylni R2'dan olib yuboradi, Telegram nusxasini saqlab qo'yadi, keyingilarga
bir zumda ketadi.

---

### QO'LDA (avtomat yoqilmagan bo'lsa)

**Yig'ish:**

```bash
cd "/Users/kaijimima1234/Projects/HSK AI bot/android" && ./gradlew assembleDirectRelease
```

Fayl: `android/app/build/outputs/apk/direct/release/hsk-ai-<versiya>-<kod>-direct-release.apk`

**Fayl nomini o'zgartirmang** — bot nomdan versiyani o'qiydi va `play` yoki
`debug` build'ni shu nom orqali rad etadi.

**R2'ga qo'yish:** `dash.cloudflare.com` → R2 → `hsk-ai-releases` → `android/` →
**Добавить папку** → `v1.2.0` → ichiga kirib **Upload**.

> Safari sahifani tarjima qilsa, fayl nomi ekranda rus tilida ko'rinishi mumkin
> (`прямой-релиз`). Bu faqat ko'rinish — haqiqiy fayl to'g'ri nom bilan turadi.

**Botga berish:**

1. **Admin panel → 📱 Android ilova → ⬆️ Yangi APK yuklash** → faylni yuboring
2. **🔗 Yangilanish havolasini qo'shish** → R2 havolasini tashlang

⚠️ Yangi APK chiqarganingizda eski havola **avtomatik o'chadi** — yangi versiya
eski fayl bilan reklama qilinib qolmasin. Ya'ni havolani **har safar qaytadan**
qo'yish kerak.

### 1.3 Tekshirish

- [ ] **📤 O'zimga yuborib ko'rish** — fayl keldimi, versiyasi to'g'rimi?
- [ ] Eski versiyali telefonda Profilga kiring — «Yangi versiya» kartasi chiqdimi?

## 2. BIR MARTA: GitHub avtomatini yoqish

Yoqsangiz, 1.2 va 1.3 qadamlar kerak bo'lmaydi — GitHub o'zi yig'adi va R2'ga qo'yadi.

Qayerga: GitHub → repo → **Settings → Secrets and variables → Actions →
New repository secret**. To'rtta qiymat:

| Nomi | Qiymati |
|---|---|
| `POMP_ANDROID_KEYSTORE_BASE64` | pastdagi buyruq natijasi |
| `POMP_ANDROID_KEYSTORE_PASSWORD` | `~/.pomp-hskai/MUHIM-OQING.txt` faylida |
| `POMP_ANDROID_KEY_ALIAS` | `pomp-hskai` |
| `POMP_ANDROID_KEY_PASSWORD` | parol bilan bir xil |

Birinchisi uchun (natija clipboard'ga tushadi):

```bash
base64 -i ~/.pomp-hskai/pomp-hskai-release.jks | tr -d '\n' | pbcopy
```

Keyin serverga manifest qayerdaligini ayting. Railway → Variables:

```
ANDROID_RELEASE_MANIFEST_URL=https://pub-9b135bd734b04a5e9fe059a4dfd7d804.r2.dev/android/latest.json
```

⚠️ Bu qiymatni **workflow birinchi marta muvaffaqiyatli o'tgandan keyin** qo'ying —
aks holda server yo'q faylni so'rab turadi. (Zarari yo'q: manifest topilmasa
server eski qo'lda qo'yilgan yo'lga qaytadi.)

Keyin: GitHub → **Actions → Android release → Run workflow**.

R2 parollari allaqachon GitHub'da (desktop uchun qo'shilgan) — ularga tegmaysiz.

Bu workflow hali bir marta ham ishlamagan. Birinchi ishga tushirish sinov.

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

**Yangilanish jim emas.** Android sideload qilingan ilovada har doim o'z
o'rnatish dialogini ko'rsatadi. Bir bosish + dialog. Foydalanuvchiga «avtomatik
yangilanadi» deb aytmang. Jim yangilanishni faqat Play Market beradi.
