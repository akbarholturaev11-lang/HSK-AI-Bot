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

### 1.1 Versiya raqamini oshiring — BU ENG KO'P UNUTILADIGANI

`android/app/build.gradle.kts` faylida, tepada:

```kotlin
val appVersionName = "1.2.0"   // odamlar ko'radigan raqam
val appVersionCode = 3         // ← BUNI HAR SAFAR +1 QILING
```

**`appVersionCode` oshmasa, hech kim yangilanishni ko'rmaydi.** Ilova faqat shu
raqamni solishtiradi, nomni emas. Hozircha buni eslatadigan hech narsa yo'q.

### 1.2 Yig'ish

```bash
cd "/Users/kaijimima1234/Projects/HSK AI bot/android" && ./gradlew assembleDirectRelease
```

Fayl shu yerda paydo bo'ladi:
`android/app/build/outputs/apk/direct/release/hsk-ai-<versiya>-<kod>-direct-release.apk`

**Fayl nomini o'zgartirmang** — bot nomdan versiyani o'qiydi, va `play` yoki
`debug` build'ni shu nom orqali rad etadi.

### 1.3 R2'ga qo'yish

`dash.cloudflare.com` → R2 → `hsk-ai-releases` bucket → `android/` papkasi →
**Добавить папку** → `v1.2.0` → ichiga kirib **Upload**.

Havolasi shunday bo'ladi:

```
https://pub-9b135bd734b04a5e9fe059a4dfd7d804.r2.dev/android/v1.2.0/hsk-ai-1.2.0-3-direct-release.apk
```

Brauzerda ochib tekshiring — yuklana boshlashi kerak.

> Safari sahifani tarjima qilsa, fayl nomi ekranda rus tilida ko'rinishi mumkin
> (`прямой-релиз`). Bu faqat ko'rinish — haqiqiy fayl to'g'ri nom bilan turadi.

### 1.4 Botga berish

1. **Admin panel → 📱 Android ilova → ⬆️ Yangi APK yuklash** → faylni yuboring
2. **🔗 Yangilanish havolasini qo'shish** → R2 havolasini tashlang

⚠️ Yangi APK chiqarganingizda eski havola **avtomatik o'chadi**. Bu ataylab —
yangi versiya eski fayl bilan reklama qilinib qolmasin. Ya'ni havolani
**har safar qaytadan** qo'yish kerak.

### 1.5 Tekshirish

- [ ] **📤 O'zimga yuborib ko'rish** — fayl keldimi?
- [ ] Eski versiyali telefonda Profilga kiring — «Yangi versiya» kartasi chiqdimi?

---

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

## 4. Play Market — keyinroq

Tartibi shu, chunki eng uzun qism kod emas, kutish:

- [ ] **Play Console akkauntini oching** ($25, bir marta). Buni birinchi qiling —
      shaxsiy akkaunt bo'lsa, production'dan oldin **12 ta tester bilan 14 kun
      yopiq test** talab qilinadi. Bu kalendar vaqti, ishlash vaqti emas.
      (Tashkilot akkauntiga bu talab tegishli emas. Qoidalar o'zgargan bo'lishi
      mumkin — Play Console'da o'zingiz tasdiqlang.)
- [ ] **Play App Signing'ga BIZNING kalitimizni yuklang** —
      `~/.pomp-hskai/pomp-hskai-release.jks`. Google o'z kalitini yaratishni
      taklif qiladi; rozi bo'lsangiz, botdan o'rnatgan odamlar Play versiyasiga
      **yangilana olmaydi**. Bu qaror bir marta qilinadi va keyin tuzatib
      bo'lmaydi.
- [ ] Store listing: nom, tavsif, skrinshotlar — uch tilda (uz/ru/tj)
- [ ] Maxfiylik siyosati sahifasi (URL kerak bo'ladi)
- [ ] Data safety formasi
- [ ] AAB yig'ish: `cd android && ./gradlew bundlePlayRelease`

**Play chiqqandan keyin ham `direct` kanal kerak bo'ladi:** Play Services yo'q
telefonlar, botdan o'rnatganlar, va Play moderatsiyada turganda tezkor tuzatish
chiqarish uchun.

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
