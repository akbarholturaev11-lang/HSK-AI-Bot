# HSK AI Desktop 1.3.x — production release runbook

Maqsad: macOS DMG, Windows EXE va ikkala platforma updater fayllarini bitta
release orqali avtomatik build qilish. Har versiyada R2 yoki Railway'dagi
fayl URL'larini qo'lda almashtirish kerak emas.

## Bir marta sozlanadi

GitHub → **Settings → Secrets and variables → Actions**:

### Repository secrets

- `TAURI_SIGNING_PRIVATE_KEY_V4`
- `TAURI_SIGNING_PRIVATE_KEY_PASSWORD_V4`
- `R2_ACCESS_KEY_ID`
- `R2_SECRET_ACCESS_KEY`
- `R2_ACCOUNT_ID`
- `R2_BUCKET`

### Repository variable

- `R2_PUBLIC_BASE_URL=https://<public-r2-domain>`

`R2_PUBLIC_BASE_URL` public HTTPS manzil bo'lishi, login/parol, query va
fragment saqlamasligi kerak. Updater private key'ini repoga, logga yoki
runbookka yozmang.

Railway'da bir marta:

```env
DESKTOP_DOWNLOAD_BASE_URL=https://telegram-chinese-bot-production.up.railway.app
DESKTOP_RELEASE_MANIFEST_URL=https://<public-r2-domain>/desktop/latest.json
DESKTOP_DOWNLOADS_ENABLED=false
DESKTOP_UPDATES_ENABLED=false
```

Legacy `DESKTOP_MAC_*` va `DESKTOP_WINDOWS_*` URL/signature/version
o'zgaruvchilarini bo'sh qoldirish mumkin. Stable `latest.json` ularning o'rnini
bosadi.

## Har bir yangi versiya

### 1. Versiyani bir xil ko'taring

Masalan `1.3.0` uchun quyidagilar aynan bir xil bo'lishi shart:

- `desktop/package.json`
- `desktop/package-lock.json`
- `desktop/src-tauri/tauri.conf.json`
- `desktop/src-tauri/Cargo.toml`
- `desktop/src-tauri/Cargo.lock`

Lokal minimum tekshiruv:

```bash
cd desktop
npm ci
npm run test:ui

cd src-tauri
cargo fmt --check
cargo test --locked
cargo clippy --locked --all-targets --all-features -- -D warnings
```

### 2. Release commitni `origin/main` ga chiqaring

Tag faqat `origin/main` tarixida mavjud commitga qo'yiladi. Dirty yoki boshqa
branchdagi commitdan release qilmang.

```bash
git fetch origin main
git merge-base --is-ancestor HEAD origin/main
```

Ikkinchi buyruq `0` bilan tugashi kerak.

### 3. Tagni yuboring

Workflow versiyani tagdan emas, repodagi desktop fayllaridan o'qiydi va tagni
aniq tekshiradi:

```bash
git tag -a desktop-v1.3.0 -m "HSK AI desktop v1.3.0"
git push origin desktop-v1.3.0
```

Tag formati majburiy: `desktop-v<SemVer>`. Masalan desktop versiya `1.3.0`
bo'lsa, tag faqat `desktop-v1.3.0` bo'ladi.

## Workflow avtomatik bajaradigan ishlar

GitHub Actions → **Desktop release**:

1. Tag `origin/main` ichida ekanini va barcha desktop versiyalari mosligini
   tekshiradi.
2. Pinned, SHA-256 bilan tekshirilgan local-AI runtime'ni macOS va Windows uchun
   tayyorlaydi.
3. UI, Rust test, format va clippy tekshiruvlarini bajaradi.
4. Universal macOS DMG/updater va Windows x64 NSIS EXE/updaterni build qiladi.
5. Checksum va V4 updater imzolarini tekshiradi.
6. Immutable fayllarni R2'ga `desktop/v1.3.0/` ostida yuklaydi.
7. Stable installer aliaslarini yangilaydi:
   - `desktop/latest/Pomp-HSK-AI-universal.dmg`
   - `desktop/latest/Pomp-HSK-AI-x64-setup.exe`
8. Public fayllarning checksum/imzosini qayta tekshiradi.
9. Faqat hammasi muvaffaqiyatli bo'lgach, eng oxirida
   `desktop/latest.json` manifestini almashtiradi.

Shu sabab yarim release foydalanuvchilarga tarqalmaydi: publish oldin yiqilsa,
oldingi `latest.json` ishlashda davom etadi.

## Release'dan keyingi tekshiruv

Actions'da `prepare`, `macos`, `windows`, `publish` joblari yashil bo'lishi
shart.

```bash
curl -fsSL https://<public-r2-domain>/desktop/latest.json | jq .
curl -fsSI https://<public-r2-domain>/desktop/latest/Pomp-HSK-AI-universal.dmg
curl -fsSI https://<public-r2-domain>/desktop/latest/Pomp-HSK-AI-x64-setup.exe
curl -fsSL https://telegram-chinese-bot-production.up.railway.app/api/v3/desktop-download/public-status | jq .
```

Manifestda quyidagilarni tekshiring:

- `version` yangi versiya;
- macOS `download_url` `.dmg`, `update_url` `.app.tar.gz` bilan tugaydi;
- Windows `download_url` va `update_url` `.exe` bilan tugaydi;
- checksumlar 64 belgili SHA-256;
- ikkala updater signature mavjud.

Toza Mac va Windows qurilmada:

- sayt va Mini App'dagi Mac/Windows tugmalari real faylni yuklaydi;
- DMG/EXE o'rnatiladi va ochiladi;
- 8 belgili Telegram ulash kodi ishlaydi;
- obuna va progress bitta hisobdan keladi;
- oldingi desktop versiya yangi versiyani topadi, dars faol bo'lmaganda
  avtomatik o'rnatadi.

Shundan keyin Railway'da:

```env
DESKTOP_DOWNLOADS_ENABLED=true
DESKTOP_UPDATES_ENABLED=true
```

Keyingi `desktop-v1.3.1`, `desktop-v1.4.0` va hokazo releaslarda Railway env yoki
R2 fayllarini qo'lda almashtirmaysiz; yangi tag stable alias va `latest.json`ni
o'zi yangilaydi.

## Xato yoki rollback

- Tagni boshqa commitga ko'chirmang va versioned R2 faylini ustidan yozmang.
- Workflow eski versiyaga downgrade va boshqa kontentli immutable key'ni
  avtomatik bloklaydi.
- Build publishgacha yiqilsa, xatoni tuzating va jobni qayta ishga tushiring.
- Release allaqachon publish qilingan bo'lsa, rollback o'rniga tuzatilgan yuqori
  patch versiya (`1.3.1`) chiqaring.
- Authenticode va Apple notarization yo'q bepul rejada OS ogohlantirishi normal;
  foydalanuvchiga download sahifasidagi xavfsiz ochish qo'llanmasini ko'rsating.
