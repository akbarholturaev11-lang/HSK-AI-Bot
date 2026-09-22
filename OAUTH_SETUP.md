# Google / Apple kirishni yoqish

Kod tayyor va productionda. Faqat credential'lar yo'q, shuning uchun tugmalar
ko'rinmaydi (fail-closed). Quyidagilarni to'ldirgach o'zi ochiladi.

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

Bu muhim: Android va desktop **bir xil client ID ishlatmasligi kerak**. Aks
holda Android uchun chiqarilgan token desktop endpointida qayta ishlatilishi
mumkin bo'ladi (cross-client replay). Kod buni ataylab ajratgan.

**Web client A — "HSK AI Android"**
- Create credentials → OAuth client ID → **Web application**
- Redirect URI kerak emas
- Olingan Client ID →

```
GOOGLE_ANDROID_WEB_CLIENT_ID=<A ning Client ID>
```

**Web client B — "HSK AI Desktop"**
- Create credentials → OAuth client ID → **Web application**
- Authorized redirect URIs → yuqoridagi Google redirect URI'ni qo'shing
- Olingan Client ID va Client secret →

```
GOOGLE_DESKTOP_CLIENT_ID=<B ning Client ID>
GOOGLE_DESKTOP_CLIENT_SECRET=<B ning Client secret>
```

### 1.2 Ikkita Android client yarating

Bular env qiymat bermaydi — ular Google'ga "shu ilova so'ray oladi" deb
aytadi. Ikkalasi ham kerak: relizga chiqqan ilova va debug build.

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

`GOOGLE_ANDROID_WEB_CLIENT_ID` ilovaga **kompilyatsiya paytida** kiradi.
`android/gradle.properties`:

```
POMP_GOOGLE_WEB_CLIENT_ID=<Web client A ning Client ID — server bilan AYNAN bir xil>
```

Keyin yangi versiya chiqarish kerak (1.6.3). Bu qiymat maxfiy emas.

**Desktop va Apple uchun ilovani yangilash shart emas** — ular brauzer orqali
ishlaydi, faqat server sozlamasi yetadi.

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
> manzilida ko'rsatishni talab qiladi. Hozir bu fayl serverda YO'Q. Apple
> shuni so'rasa ayting — men uni serverga qo'shib beraman (kichik ish).

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

Railway o'zgaruvchilarni saqlaganda o'zi qayta deploy qiladi. Bir daqiqadan
keyin:

```bash
curl -s "https://telegram-chinese-bot-production.up.railway.app/api/v3/native-auth/providers?platform=android"
```

- `{"ok":true,"providers":[]}` → hali sozlanmagan, biror qiymat bo'sh yoki xato
- `{"ok":true,"providers":["google"]}` → Google tayyor
- `{"ok":true,"providers":["google","apple"]}` → ikkalasi tayyor

Keyin Mini App profilida **Sozlamalar → Kirish usullari** bo'limi o'zi
paydo bo'ladi. Desktop kirish ekranida ham tugmalar chiqadi.

Android'dagi Google tugmasi uchun 1.6.3 chiqarish kerak.

---

## 4. Nimani hech qachon git'ga qo'ymaslik kerak

- `AuthKey_*.p8` fayli va `APPLE_PRIVATE_KEY` qiymati
- `GOOGLE_DESKTOP_CLIENT_SECRET`

Client ID'lar maxfiy emas — ular baribir klientga chiqadi.
