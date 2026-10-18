# Google / Apple kirishni yoqish

Provider tugmalari serverdagi konfiguratsiya to'liq bo'lgandagina ko'rinadi
(fail-closed). Quyida sozlash tartibi keltirilgan; bu hujjat production
credential'lari yoki real callback hozir tekshirilganini bildirmaydi.

Universal akkaunt yaratish, migratsiya va release tekshiruvlari:
[`docs/UNIVERSAL_NATIVE_ACCOUNTS.md`](docs/UNIVERSAL_NATIVE_ACCOUNTS.md).

Google va Apple birinchi tasdiqlangan kirishda Telegramsiz yangi HSK AI hisobini
yaratadi. Avvaldan progress yoki obuna bor bo‘lsa, o‘sha hisobga kirib, boshqa
provider’ni profilidan ulang; bir xil email hisoblarni birlashtirmaydi. Pro,
HSK 3.0 xaridi va referral hisobning `users.id` kalitiga tegishli. Native
registratsiyadagi ixtiyoriy taklif kodi faqat yangi hisobga biriktiriladi.

Google/Apple bilan ochilgan hisobga keyin Telegram ulash uchun Android yoki
desktop profilidagi Telegram ulash amalidan foydalaniladi. Bot shaxsiy chatida
aynan ko‘rsatilgan akkauntga ulash alohida tasdiqlanadi. Telegram boshqa HSK AI
hisobiga tegishli bo‘lsa, ulash rad etiladi; hisoblar avtomatik birlashmaydi.
Bu yo‘l yangi akkaunt ochmaydi va Pro, progress yoki AI limitini yangilamaydi.

Hozirgi Play ilovasida xarid yo‘q. Saytdagi Direct APK va desktop mavjud
chek/admin tasdiqlash oqimidan foydalanadi. Bu branch `main`/production’ga
qabul tekshiruvlari tugamaguncha chiqarilmaydi. Staging OAuth tekshiruvida
staging’ning o‘z origin/callback va provider client sozlamalaridan foydalaning;
production konfiguratsiyasini sinov uchun o‘zgartirmang.

Production domeni: `telegram-chinese-bot-production.up.railway.app`

---

## 0. Ikkalasi uchun umumiy

Railway → `telegram-chinese-bot` → Variables:

```
OAUTH_REDIRECT_BASE_URL=https://telegram-chinese-bot-production.up.railway.app
```

Faqat origin. Oxirida `/` YO'Q, path yo'q, query yo'q — aks holda kod uni rad
etadi va provider "sozlanmagan" bo'lib qoladi.

Kod redirect manzillarini shundan quradi:

| Provider | Redirect URI (konsolga aynan shuni yozing) |
|---|---|
| Google | `https://telegram-chinese-bot-production.up.railway.app/api/v3/native-auth/oauth/callback/google` |
| Apple | `https://telegram-chinese-bot-production.up.railway.app/api/v3/native-auth/oauth/callback/apple` |

---

## 1. Google

**Qayerda:** [console.cloud.google.com](https://console.cloud.google.com) →
loyiha yarating → APIs & Services → Credentials.

Avval OAuth consent screen'ni to'ldiring (External, ilova nomi, support email).

### 1.1 Ikkita Web client yarating — bitta emas

Muhim: native Android Credential Manager orqali olingan ID token uchun A
audience ishlatiladi. Android/desktop browser authorization-code oqimi esa B
web client ID + serverdagi secret + PKCE'dan foydalanadi. Native ID token
faqat `oauth/assert`'da A audience bilan tekshiriladi; browser ID token
faqat server callback'ida B audience bilan tekshiriladi. Bu ikkisini bitta
audience ro'yxati qilib qo'shmang (cross-client replay xavfi).

**Web client A — "HSK AI Android Credential Manager (legacy/native)"**
- Create credentials → OAuth client ID → **Web application**
- Redirect URI kerak emas
- Olingan Client ID →

```
GOOGLE_ANDROID_WEB_CLIENT_ID=<A ning Client ID>
```

**Web client B — "HSK AI Browser (Android + Desktop)"**
- Create credentials → OAuth client ID → **Web application**
- Authorized redirect URIs → yuqoridagi Google redirect URI'ni qo'shing
- Olingan Client ID va Client secret →

```
GOOGLE_DESKTOP_CLIENT_ID=<B ning Client ID>
GOOGLE_DESKTOP_CLIENT_SECRET=<B ning Client secret>
```

Mini App ham Google ulash uchun brauzer redirect/code-exchange oqimidan
foydalanadi. Shu sabab `/api/v3/native-auth/providers?platform=miniapp` Google’ni
faqat `GOOGLE_DESKTOP_CLIENT_ID` va `GOOGLE_DESKTOP_CLIENT_SECRET` ikkalasi ham
mavjud bo‘lsa ko‘rsatadi. Faqat Android Web client A sozlangani Mini App uchun
yetarli emas. Android native discovery esa mustaqil ravishda
`GOOGLE_ANDROID_WEB_CLIENT_ID`ni tekshiradi; token audience tekshiruvlari
birlashtirilmaydi.

### 1.2 Ikkita Android client yarating

Bular native Credential Manager oqimi uchun Google'ga "shu ilova so'ray oladi"
deb aytadi. Browser OAuth uchun Android SHA-1 talab qilinmaydi. Legacy/native
yo'lni keyin qayta yoqish mumkin bo'lishi uchun A client va SHA-1 sozlamalarini
o'chirib yubormang.

| Package name | SHA-1 sertifikat barmoq izi |
|---|---|
| `com.pomp.hskai` | `69:3B:EC:24:17:57:65:31:83:AD:C1:ED:D3:17:67:E5:0E:89:B6:CA` |
| `com.pomp.hskai.debug` | `65:D0:2C:E2:C6:C3:BC:DB:4A:C8:50:14:10:82:EF:E6:AA:F8:93:62` |

Birinchisi R2'dagi haqiqiy `1.6.2` APK'dan olindi, ikkinchisi shu Mac'dagi
debug keystore'dan. `play` va `direct` bir xil `applicationId` ishlatadi,
shuning uchun ular uchun alohida client kerak emas.

> Agar kelajakda Play App Signing yoqilsa, Play o'z kaliti bilan qayta
> imzolaydi va **yana bitta** SHA-1 qo'shish kerak bo'ladi (Play Console →
> Setup → App integrity).

### 1.3 Yoqish

```
GOOGLE_OAUTH_ENABLED=true
```

### 1.4 Android ilovasiga ham kerak

`GOOGLE_ANDROID_WEB_CLIENT_ID` eski native Credential Manager oqimi uchun
ilovaga **kompilyatsiya paytida** kiradi. Yangilangan Android login/profil Google
brauzer orqali B web client'ga o'tadi; undan foydalanish uchun APK'ga A client
ID'ni qo'shish shart emas. Eski native yo'lni saqlash kerak bo'lsa
`android/gradle.properties`:

```
POMP_GOOGLE_WEB_CLIENT_ID=<Web client A ning Client ID — server bilan AYNAN bir xil>
```

Yangilangan Android APK tarqatilmaguncha foydalanuvchilarda eski Google
Credential Manager logikasi qoladi. Client ID maxfiy emas.

**Android browser handoff:** Google yoki Apple tasdiqlangach HTTPS callback
`pomp-hsk-ai://oauth-return` orqali avvalgi Android ilovasini ochishga
urinadi. Android Manifest allaqachon bu scheme'ni qabul qiladi,
`MainActivity` esa `singleTask`; yangi session browser URL orqali emas,
faqat oldingi pending link polling secret'iga ega ilovaga yuboriladi.
Chrome/Custom Tabs avtomatik handoff'ni cheklasa, sahifada
`HSK AI ↗` qo'lda bosiladigan havola bor. Desktop callback app'ni
avtomatik ochmaydi; desktop avvalgi polling holatini yakunlaydi.

**Deployment:** Bu o'zgarishlar faqat `codex/universal-sign-in` branch'ida.
Provider callback va klient eski production bilan birga yangilanmasdan ishlaydi
deb taxmin qilmang. Real Google callback, Android return va Apple testlari
izolatsiyalangan staging ilova muhitida o'tkazilmaguncha production yoki
`main`'ga chiqarmang.

---

## 2. Apple

**Qayerda:** [developer.apple.com](https://developer.apple.com/account) →
Certificates, Identifiers & Profiles. Pullik Apple Developer akkaunti kerak.

### 2.1 Team ID

O'ng yuqorida yoki Membership sahifasida, 10 belgi:

```
APPLE_TEAM_ID=<10 belgili Team ID>
```

### 2.2 App ID va Services ID

1. Identifiers → **App IDs** → yangi App ID (masalan `com.pomp.hskai.app`),
   Capabilities'da **Sign in with Apple** ni belgilang.
2. Identifiers → **Services IDs** → yangi (masalan `com.pomp.hskai.web`),
   **Sign in with Apple** ni yoqing → Configure:
   - Primary App ID: yuqoridagi App ID
   - Domains: `telegram-chinese-bot-production.up.railway.app`
   - Return URLs: yuqoridagi Apple redirect URI

```
APPLE_SERVICE_ID=<Services ID, masalan com.pomp.hskai.web>
```

> **Diqqat — domen tasdiqlash.** Apple domenni tasdiqlash uchun fayl beradi va
> uni `https://<domen>/.well-known/apple-developer-domain-association.txt`
> manzilida ko'rsatishni talab qilishi mumkin. Fayl production'da
> mavjudligi bu hujjatdan ma'lum emas: kerak bo'lsa hosting route'ini va
> Apple Developer konfiguratsiyasini amaldagi deployment'da tekshiring.

### 2.3 Kalit

Keys → yangi kalit → **Sign in with Apple** ni belgilang → Continue →
Register → `AuthKey_XXXXXXXXXX.p8` faylini yuklab oling.

**Bu faylni bir marta yuklab olasiz.** Yo'qotsangiz yangisini yasashga to'g'ri
keladi. Git'ga QO'YMANG.

```
APPLE_KEY_ID=<10 belgili Key ID — fayl nomidagi XXXXXXXXXX>
APPLE_PRIVATE_KEY=<.p8 faylining ICHIDAGI matn>
```

`.p8` ichi ko'p qatorli:

```
-----BEGIN PRIVATE KEY-----
MIGTAgEAMBMGByqGSM49...
-----END PRIVATE KEY-----
```

Railway'ga qo'yganda qatorlarni `\n` bilan bitta qatorga yozsangiz ham bo'ladi
— kod ikkalasini ham tushunadi.

### 2.4 Yoqish

```
APPLE_OAUTH_ENABLED=true
```

---

## 3. Tekshirish

Universal kirish release hold tugamaguncha alohida staging muhitini ishlating.
Railway o'zgaruvchilarini saqlash deploy boshlashi mumkin; production xizmatini
o'zgartirmang. Staging backend ishga tushgach browser oqimini tekshiring:

```bash
curl -s "https://YOUR-STAGING-HOST/api/v3/native-auth/providers?platform=macos"
```

- `{"ok":true,"providers":[]}` → hali sozlanmagan, biror qiymat bo'sh yoki xato
- `{"ok":true,"providers":["google"]}` → Google browser konfiguratsiyasi tanildi
- `{"ok":true,"providers":["google","apple"]}` → ikkala browser konfiguratsiyasi tanildi

Mini App uchun alohida `?platform=miniapp` bilan tekshiring: Android uchun
Google ko‘rinishi Mini App browser konfiguratsiyasi tayyorligini bildirmaydi.
Profil karuselida faqat sozlangan va hali ulanmagan Google/Apple uchun alohida
ulash kartalari ko‘rinadi. Ulangan provider kartasi qayta chiqmaydi;
**Sozlamalar → Kirish usullari** bo‘limida mavjud bog‘lanishlarni boshqarish
saqlanadi. Desktop kirish ekranida ham sozlangan provider tugmalari chiqadi.
Bu javoblar real callback muvaffaqiyatini tasdiqlamaydi.

Android browser UI ham shu web client juftligini ishlatadi; eski ichki
Credential Manager uchun `platform=android` discovery alohida qoladi.

Google/Apple success callback Android, macOS va Windows ilovasini qayta
ochishga urinadi va `HSK AI` tugmasini ham ko'rsatadi. URI login natijasi yoki
token olib yurmaydi; natijani ilovaning avvalgi proof polling oqimi oladi.
Production default `OAUTH_NATIVE_RETURN_SCHEME=pomp-hsk-ai`; alohida QA
backendida `pomp-hsk-ai-qa` ishlating. Boshqa yoki bo'sh qiymat ilovani
avtomatik ochishni o'chiradi. Har ikkala OS/client uchun mos QA build kerak.
[Amaliy test yo'riqnomasi](docs/UNIVERSAL_NATIVE_ACCOUNT_QA.md) va client
README'larida origin, alohida paket/bundle hamda updater sozlamalari bor.

---

## 4. Nimani hech qachon git'ga qo'ymaslik kerak

- `AuthKey_*.p8` fayli va `APPLE_PRIVATE_KEY` qiymati
- `GOOGLE_DESKTOP_CLIENT_SECRET`

Client ID'lar maxfiy emas — ular baribir klientga chiqadi.
