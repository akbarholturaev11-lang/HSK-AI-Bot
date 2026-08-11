# Desktop profil ekrani — topshiriq va reja

Bu fayl bitta ishning davomi uchun yozilgan. Yangi chatda ishlayotgan AI
yordamchi shu faylni va `CLAUDE.md`, `PROJECT_MEMORY.md`, `AI_RULES.md` ni
o'qib, kod yozishdan oldin hisobot berishi shart.

Sana: 2026-08-10 · Branch: `feat/desktop-voice` · Baza commit: `0acc2ae8`

---

## 1. Maqsad — bu ishning asosiy talabi

> **Desktop ilovaning profil ekrani va onboardingi demoga 1:1 o'xshashi
> shart.** Bloklarning tartibi, tugmalar, ularning joylashuvi, kartalarning
> tuzilishi, grafiklar, teglar — barcha mayda detallargacha.

**Demo fayli loyihaga ko'chirildi:**

```
desktop/design/hsk-ai-mac-demo_4.html
```

Profil ekrani demoning `<section id="screen-profile">` bloki, onboarding esa
`<div class="onboard" id="startOnboarding">` bloki. Ishni boshlashdan oldin
shu ikki blokni o'qib chiqing.

### To'rt qat'iy tamoyil

1. **1:1 ko'rinish.** Har bir demo bloki o'z joyida, o'z tartibida, o'z
   tugmalari bilan bo'ladi. Blokni olib tashlash yoki soddalashtirish mumkin
   emas.
2. **Raqam o'ylab topilmaydi.** Serverda ma'lumot bo'lmasa `—` ko'rsatiladi.
   Demo'dagi namunaviy raqamlar (326, 684, 82 min, +18%, 53%) **hech qachon**
   ko'chirilmaydi.
3. **Yo'q funksiya ishlayotgandek ko'rinmaydi.** Blok demo'dagi to'liq
   ko'rinishini saqlaydi, lekin boshqaruvlari o'chirilgan va **ustiga
   borilganda** "Tez orada" pardasi chiqadi (`soonBlock()`).
4. **Demo'da yo'q, bizda bor bo'limlar** profil ekranining **eng pastiga**
   ko'chiriladi — hech qanday funksiya yo'qolmaydi.

### Demo ↔ ilova mosligi jadvali

Har bir qator tekshirilishi kerak. "Holat" ustuni hozirgi vaziyat.

| Demo bloki | Ilovadagi funksiya | Holat |
|---|---|---|
| `.profileHero` avatar, ism, HSK·%·streak | `renderProfile` | Haqiqiy |
| `.chips` — so'z / daqiqa | hero chiplari | **Veyl** (V3) |
| `.profilePanda` | `.profile-panda` img | Haqiqiy |
| Maqsad kartasi: sarlavha, "Faol" tegi, matn | maqsad kartasi | Haqiqiy |
| Maqsad kartasi: progress + "15 daq / kun" | `profile-goal-daily` | **Veyl** (V3) |
| `.inviteCard` eyebrow + sarlavha + matn | `renderInviteCard` | Haqiqiy |
| `.inviteMorph` morph tugma | `inviteMorph` | Haqiqiy |
| Tray: `⌘C` | nusxalash | Haqiqiy |
| Tray: `TG`, `WA` | ulashish | **Veyl** (V1) |
| Tray: `QR` | QR kod | **Veyl** (V2) |
| `.inviteStatus` mini avatarlar + hisoblagich | `invite-status` | Haqiqiy |
| `.syncCard` | `renderSyncCard` | **Veyl** (V7) |
| Stat karta: Seriya + "Eng yaxshi: N kun" | `profileStatCard` | Haqiqiy |
| Stat karta: O'rganilgan so'zlar | `comingSoonStatCard` | **Veyl** (V3) |
| Stat karta: Tugallangan darslar | `profileStatCard` | Haqiqiy |
| Stat karta: O'qish daqiqalari | `comingSoonStatCard` | **Veyl** (V3) |
| `#barChart` haftalik faollik | `weekBarChart` | Qisman — ustun balandligi kun-faolligi, daqiqa emas (V3) |
| `#levelProgress` HSK darajalar | `levelProgressCard` | **Veyl** (V5) |
| `#weakAreas` zaif joylar | `weakAreasCard` | **Veyl** (V4) |
| Aniqlik trendi SVG | `accuracyTrendCard` | **Veyl** (V5) |
| `.progressInsight` 3 chip | `insightChips` | **Veyl** (V5) |
| Bildirishnomalar kartasi (5 qator) | `renderNotificationsCard` | **Veyl** (V6) |
| Til `<select>` | `selectControl` | Haqiqiy |
| Kurs darajasi `<select>` | `comingSoonSettingRow` | **Veyl** (V8) |
| Audio avtoijro switch | `comingSoonSettingRow` | **Veyl** (V8) |
| Pinyin switch | `comingSoonSettingRow` | **Veyl** (V8) |
| Animatsiyani kamaytirish switch | `toggleButton` | Haqiqiy |
| "Start onboarding" qatori | `onboardingReopen` | Haqiqiy |
| Onboarding 1-bosqich: 3 maqsad kartasi | `onboardingGoalStep` | Haqiqiy |
| Onboarding 2-bosqich: Smart Widget | `onboardingWidgetStep` | **Veyl** (V9) |
| Onboarding: bosqich indikatori, Orqaga / Keyinroq / Davom etish | `renderOnboarding` | Haqiqiy |
| — (demo'da yo'q) | Akkaunt bloki: obuna, yangilanish, chiqish, versiya | Haqiqiy, eng pastda |

**Demo'dan ataylab ko'chirilmagan yagona narsa:** 2-bosqichdagi `<details>`
bloki (WidgetKit Swift yo'riqnomasi) — u ishlab chiquvchi uchun yozilgan izoh,
mahsulot interfeysi emas.

---

## 2. Hozirgi holat

**Bajarildi (commit qilinmagan, ish daraxtida turibdi):**

| Fayl | Qatorlar |
|---|---|
| `desktop/ui/js/app.js` | +827 |
| `desktop/ui/css/workspace.css` | +738 |
| `desktop/ui/js/i18n.js` | +292 |
| `desktop/ui/test-contract.mjs` | +127 |
| `PROJECT_MEMORY.md` | +88 |
| `desktop/ui/index.html` | +40 |
| `desktop/src-tauri/src/lib.rs` | ±27 |
| `desktop/ui/js/preview-mock.js`, `js/bridge.js`, `css/app.css` | kichik |

**Testlar:** `node --test desktop/ui/test-contract.mjs` → 22/22 o'tadi.

**Profil ekrani tartibi (yuqoridan pastga):**

1. `topRow` — hero (avatar, ism, HSK·%·streak, chiplar, panda) + maqsad kartasi
2. `actionsRow` — taklif morph kartasi + sinxronlash kartasi
3. `statsHead` + `stats` — 4 ta stat karta
4. `progressGrid` — chapda haftalik bar chart va HSK darajalar, o'ngda zaif
   joylar va aniqlik trendi
5. `insights` — 3 ta insight chip
6. `settingsHead` + `settingsRow` — bildirishnomalar kartasi + o'qish/interfeys
7. `accountHead` + `accountCard` — **demo'da yo'q**: obuna, yangilanish,
   chiqish, versiya

**Onboarding:** ikki bosqichli modal (`#onboarding-layer`). 1-bosqich — maqsad
turi (`conversation` / `hsk` / `study`), 2-bosqich — Smart Widget tanishtiruvi
(veyl ostida). Maqsad tanlanmagan bo'lsa `enterWorkspace` dan keyin modal o'zi
ochiladi.

---

## 3. Amal qilinishi shart bo'lgan naqshlar

### `soonBlock(node)` — "Tez orada" pardasi

`desktop/ui/js/app.js` dagi asosiy naqsh. Blokni o'rab oladi, ichidagi barcha
`button, input, select, textarea, a[href]` elementlarini `disabled` qiladi,
`tabIndex = -1` va `aria-hidden` qo'yadi, ustiga parda qo'shadi.

```js
return soonBlock(card);          // butun karta
wrap.classList.add("is-row");    // sozlama qatori uchun (comingSoonSettingRow)
```

CSS: `.soon-block`, `.soon-veil`, `.soon-badge` — `css/workspace.css`.

**Endpoint tayyor bo'lgach veylni olib tashlash:** shunchaki `soonBlock(...)`
o'ramini olib tashlang va `NO_VALUE` o'rniga haqiqiy qiymatni bering. Boshqa
hech narsani o'zgartirish shart emas.

### `NO_VALUE = "—"`

Ma'lumot bo'lmaganda faqat shu ishlatiladi. Hech qachon namunaviy raqam emas.

### i18n — uchta til majburiy

`uz`, `ru`, `tj` bloklarida kalitlar to'plami **aynan bir xil** bo'lishi kerak.
Buni contract test tekshiradi (`every user-facing key exists in all three
languages`). Hozir har birida 622 ta kalit.

### `GOAL_KINDS`

`["conversation", "hsk", "study"]` — Rust'da (`lib.rs`) va `bridge.js` da
bir xil whitelist. Maqsad `daily-goal.json` da `{"kind": "..."}` sifatida
saqlanadi, serverda ustun yo'q.

### CSP

Inline style **taqiqlangan**. `element.style.*` ishlatilmaydi — contract test
buni ushlaydi (`assert.doesNotMatch(app, /\.style\./)`). Hamma narsa CSS
klasslari yoki `data-*` atributlari orqali.

---

## 4. Darhol bajarilishi kerak (blokerlar)

Bular tugamaguncha ish yakunlangan hisoblanmaydi.

### 4.1 Rust kompilyatsiyasi

`lib.rs` dagi `desktop_goal_state` / `desktop_goal_save` o'zgargan, lekin
**hech qachon kompilyatsiya qilinmagan**.

```bash
cd desktop/src-tauri
cargo fmt --check
cargo clippy --locked --all-targets -- -D warnings
```

Kutilayotgan xavf: `desktop_goal_save` da `let kind = kind.trim();`
(String'ni shadow qilib &str olish) va `GOAL_KINDS.contains(&kind)`.

### 4.2 Ko'z bilan tekshirish

Ilovani ochib quyidagilarni ko'ring:

- Profil ekrani demo bilan yonma-yon solishtiriladi
- Har bir veyl ostidagi blokka sichqoncha borganda "Tez orada" chiqadimi
- Taklif morph tugmasi ochiladimi, ⌘C haqiqatan nusxalaydimi
- Onboarding birinchi ishga tushishda o'zi ochiladimi
- Til `<select>` orqali almashtirilganda ekran qayta chiziladimi
- Uchala tilda matnlar joyiga sig'adimi (RU eng uzun)

### 4.3 Commit

Hozir hech narsa commit qilinmagan va ish daraxtida boshqa vazifalarning
o'zgarishlari ham bor (voice, practice, rating, vocabulary). **Faqat profil
va onboarding fayllarini** commit qiling:

```
desktop/ui/js/app.js
desktop/ui/js/i18n.js
desktop/ui/js/bridge.js
desktop/ui/js/preview-mock.js
desktop/ui/css/workspace.css
desktop/ui/css/app.css
desktop/ui/index.html
desktop/ui/test-contract.mjs
desktop/src-tauri/src/lib.rs
desktop/design/hsk-ai-mac-demo_4.html
PROJECT_MEMORY.md
DESKTOP_PROFILE_HANDOFF.md
```

`desktop/design/hsk-ai-mac-demo_4.html` — dizayn manbasi, 478 KB. U loyihada
turishi kerak, aks holda keyingi ish nimaga qarab solishtirishni bilmaydi.

`AI_RULES.md` dagi push qoidasiga e'tibor bering: "push" deyilsa yakuniy
maqsad `origin/main`.

---

## 5. Vazifalar ro'yxati

Har bir vazifa alohida bajarilishi va alohida test qilinishi kerak.

### V1 — Ulashish tugmalarini jonlantirish (TG / WA)

**Maqsad:** taklif havolasini Telegram va WhatsApp orqali ulashish.

**Nima kerak:** `tauri-plugin-opener` allaqachon `Cargo.toml` da bor, lekin
tashqi havola ochish uchun named command yo'q. Yangi `desktop_open_share_url`
komandasi kerak — **qat'iy allowlist bilan**: faqat `https://t.me/share/url?...`
va `https://wa.me/?text=...`.

**Fayllar:** `lib.rs`, `bridge.js`, `app.js` (`inviteMorph` da `soonBlock`
o'ramini olib tashlash), `preview-mock.js`, `test-contract.mjs`.

**Tayyorlik mezoni:** ikkala tugma tashqi ilovani ochadi, allowlist testda
tekshiriladi, veyl faqat QR'da qoladi.

**Xavf:** ochiq redirect. Havola faqat serverdan kelgan `referral.link` dan
quriladi, foydalanuvchi kiritgan matndan emas.

---

### V2 — QR kod

**Maqsad:** taklif havolasini QR sifatida ko'rsatish (telefondan skanerlash).

**Nima kerak:** QR generator. CDN **ishlatilmaydi** (CSP va offline talab) —
kutubxona `desktop/ui/vendor/` ga bundle qilinadi, xuddi `hanzi-writer.js`
kabi. `THIRD_PARTY_NOTICES.md` va `desktop/licenses/` yangilanadi.

**Fayllar:** `desktop/ui/vendor/`, `app.js` (`inviteMorph`), CSS, litsenziya
fayllari.

**Tayyorlik mezoni:** QR tugmasi bosilganda tray ichida kod chiziladi
(demo'dagi `.inviteQr` kabi), internetsiz ishlaydi.

---

### V3 — O'rganilgan so'z va o'qish daqiqasi

**Maqsad:** hero chiplari va ikkita stat kartani jonlantirish.

**Nima kerak:** backendda bu ikki ko'rsatkich **umuman hisoblanmaydi**. Avval
qaror kerak: so'z soni nimadan olinadi (yakunlangan darslardagi so'zlarmi yoki
saqlangan lug'atmi), daqiqa qayerda o'lchanadi (dars boshlanish/tugash
vaqtimi). Bu **yangi jadval va migratsiya** talab qilishi mumkin — `AI_RULES.md`
bo'yicha migratsiya hujjatlashtiriladi.

**Fayllar:** `app/services/course_gamification_service.py`,
`app/services/desktop_course_service.py`, alembic migratsiyasi, `app.js`.

**Tayyorlik mezoni:** `map.progress` da yangi maydonlar, hero chiplari va 2 ta
stat kartadan veyl olinadi, "+N shu hafta" deltalari haqiqiy.

**Diqqat:** bu Mini App'ga ham ta'sir qiladi — bir xil servis.

---

### V4 — Zaif joylar

**Maqsad:** "Zaif joylar" kartasini jonlantirish.

**Nima kerak:** xatolar allaqachon yoziladi (`MAX_MISTAKES`, praktika servisi),
lekin agregatsiya endpointi yo'q. `GET /api/v3/desktop/progress/weak-areas`
kerak — mavjud servisni chaqiradigan yupqa adapter, xuddi `desktop_rating.py`
naqshi kabi. **Yangi biznes-mantiq yozilmaydi.**

**Fayllar:** `app/api/desktop_progress.py` (yangi), `app/main.py`, `lib.rs`,
`bridge.js`, `app.js` (`weakAreasCard`).

---

### V5 — Aniqlik trendi va HSK darajalar progressi

**Maqsad:** ikkita grafik kartani jonlantirish.

**Nima kerak:** aniqlik tarixi hech qayerda saqlanmaydi — yangi jadval kerak.
HSK darajalar uchun har bir daraja bo'yicha yakunlangan darslar soni kerak
(hozir faqat joriy daraja kuzatiladi).

**Fayllar:** V4 dagi bir xil adapter, `app.js` (`accuracyTrendCard`,
`levelProgressCard`).

---

### V6 — Bildirishnomalar sozlamalari

**Maqsad:** bildirishnomalar kartasidan veylni olish.

**Nima kerak:** serverda hozir faqat `notify.enabled` (`profile.
notifications_enabled`). Demo 5 ta sozlama so'raydi: eslatma vaqti, jim
soatlar, chastota, ton, streak eslatmasi. Bularning barchasi uchun **yangi
ustunlar va migratsiya** kerak, hamda botning eslatma yuborish mantig'i
ularni hisobga olishi kerak.

**Diqqat:** bu eng katta vazifa va Mini App'ga ham tegadi. Alohida
loyihalashtirilishi kerak.

---

### V7 — Sinxronlash

**Maqsad:** sinxronlash kartasidan veylni olish.

**Nima kerak:** hozir saqlangan so'zlar faqat lokal `vocabulary.json` da,
Mini App bilan sinxronlanmaydi. Server tomonda jadval va migratsiya, konflikt
xavfsiz navbat kerak. `PROJECT_MEMORY.md` da bu allaqachon "keyingi bosqich"
deb yozilgan.

---

### V8 — Kurs darajasi, audio avtoijro, pinyin sozlamalari

**Maqsad:** uchta sozlama qatoridan veylni olish.

- **Kurs darajasi:** hozir server hal qiladi. Foydalanuvchi o'zgartira olishi
  kerakmi — bu mahsulot qarori, avval so'rang.
- **Audio avtoijro va pinyin:** lokal sozlama sifatida qilinishi mumkin
  (`reduceMotion` kabi `localStorage`), lekin dars va lug'at rendererlariga
  ulanishi kerak.

---

### V9 — Menu bar / tray paneli (Smart Widget o'rniga)

**Maqsad:** onboardingning 2-bosqichi va'da qilgan qiymatni haqiqatan berish —
kun davomida yangilanadigan bitta joy: streak, kun so'zi, kunlik reja.

**Nega widget emas:** haqiqiy macOS WidgetKit extension pullik Apple Developer
akkaunti, App Group entitlement va notarization talab qiladi. Hozirgi
`tauri.conf.json` da `signingIdentity: "-"` (ad-hoc) — bunday imzo bilan
extension **umuman yuklanmaydi**. Windows'da bundle `nsis`, widget uchun MSIX
kerak. Ya'ni widget tashqi blokerga bog'liq.

**Tray esa bugun ishlaydi:** Tauri v2 `tray-icon` feature'ini native
qo'llab-quvvatlaydi, Apple akkaunti kerak emas, imzo o'zgarmaydi, macOS va
Windows'da bir xil.

**Fayllar:** `Cargo.toml` (`tauri` features), `lib.rs`, ikonka assetlari,
`i18n.js` (3 til), `tauri.conf.json`.

**Tayyorlik mezoni:** ikkala platformada tray ikonkasi chiqadi, bosilganda
panel ochiladi, DMG/EXE parity buzilmaydi. Onboardingning 2-bosqichi tray
tanishtiruviga aylantiriladi va veyl olinadi.

---

### V10 — Release feedback qoralamasi

`AI_RULES.md` majburiy qiladi: har bir katta ko'rinadigan yangilanishdan keyin
admin uchun qoralama tayyorlanadi. Bu profil qayta qurilishi uchun **hali
yozilmagan**.

Qoralama tarkibi `AI_RULES.md` da to'liq sanab o'tilgan (sarlavha, e'lon
matni, nima o'zgardi, qayerda sinash, `Sinab ko'rish` amali, segment, reyting
so'rovi, mukofot matni, statistika). Foydalanuvchilarga **avtomatik
yuborilmaydi** — admin tasdiqlashi kerak.

**2026-08-11 — qoralama tayyorlandi:**

- Release nomi: `Desktop profil va onboarding yangilandi`
- Userga qisqa matn:
  `HSK AI Desktop profil ekrani yangilandi: endi maqsadingiz, takliflar,
  progress, sozlamalar va akkaunt boshqaruvi bitta tartibli ekranda. Ilova
  birinchi ochilganda o'qish maqsadingizni tanlashni ham so'raydi. Sinab
  ko'rib, 1-5 baho qoldirsangiz, fikringiz uchun chegirma beramiz.`
- Aynan nima yangilandi:
  profil hero bloki, maqsad kartasi, taklif morph tugmasi, real referral
  statusi, sinxronlash/analytics/notification veyllari, 4 stat karta, haftalik
  faollik, HSK darajalar, zaif joylar, aniqlik trendi, uch insight chip,
  til select'i, qayta onboarding tugmasi, akkaunt/yangilanish/chiqish bloki.
- Qayerda sinash kerak:
  Desktop ilova → chap panel → `Profil`. Birinchi ochilishda onboarding o'zi
  chiqishi kerak; keyin `Profil → O'qish va interfeys → Qayta sozlash`.
- `Sinab ko'rish` tugmasi:
  Desktop ilovani ochish deep-linki mavjud bo'lsa shu joyga olib boradi.
  Deep-link bo'lmasa fallback matn: `Desktop ilovani oching va chap paneldan
  Profil bo'limiga kiring.`
- Target segment:
  Desktop app o'rnatgan yoki so'nggi 14 kunda desktop download/link flowdan
  o'tgan foydalanuvchilar.
- 1-5 baholash matni:
  `Yangi Desktop profil ekrani sizga qanchalik tushunarli va foydali? 1 dan
  5 gacha baholang.`
- Reward oldindan aytiladigan matn:
  `Fikr qoldirsangiz, profil yangilanishini sinagani uchun sizga keyingi
  obuna uchun chegirma beramiz.`
- Reward confirmation:
  `Aytganimizdek, fikringiz uchun chegirma berildi. Rahmat — bu Desktop
  profilni tezroq to'g'rilashga yordam beradi.`
- Statsda kuzatiladigan metriclar:
  desktop profile open event, onboarding opened/completed/skipped, goal kind
  distribution, referral copy click, subscription manage click from profile,
  language change from profile, update-check click, release feedback rating
  average, comment rate, discount redemption rate.

---

## 6. Kichikroq ochiq narsalar

- **2026-08-11 verification:** `node --test desktop/ui/test-contract.mjs`
  22/22 o'tdi; `cargo fmt --check` va `cargo clippy --locked --all-targets
  -- -D warnings` o'tdi; localhost mock previewda Playwright smoke o'tdi.
  Screenshotlar `output/playwright/` ostida.
- **2026-08-11 kichik fix:** no-data progress fill'lar 100% qizil bar bo'lib
  ko'rinmasligi uchun `progress-fill is-placeholder` stub ko'rinishiga
  tushirildi. Bu "ma'lumot yo'q bo'lsa —" qoidasini vizual tomondan ham
  saqlaydi.
- **Commit holati:** commit hali qilinmadi. Sabab: indexda voice/practice/
  vocabulary/rating o'zgarishlari staged turibdi, profile patch esa shu
  staged holat ustiga yozilgan. Faqat handoffdagi profile fayllarni commit
  qilish `app.js` import qilgan yangi fayllarni commitdan tashqarida qoldirib
  buildni sindiradi. Kengroq staged commit qilish esa "faqat profil va
  onboarding" qoidasini buzadi. Toza yo'l: avval bu aralash staged
  o'zgarishlar bo'yicha qaror qilish.
- **Onboarding focus-trap:** modal ochiq bo'lganda Tab bilan orqadagi
  elementlarga o'tish mumkin. `lesson.trapFocus` naqshi bor, o'shanga
  o'xshatib qo'shilsa bo'ladi.
- **Eski `daily-goal.json`:** migratsiya qilinmadi. Faylda faqat `minutes`
  bo'lgani uchun mavjud foydalanuvchilarda onboarding bir marta qayta
  ochiladi. Bu ongli qaror, o'zgartirish shart emas.
- **Demo'ning `<details>` bloki** (2-bosqichdagi WidgetKit Swift yo'riqnomasi)
  ataylab ko'chirilmadi — u ishlab chiquvchi izohi, mahsulot UI'si emas.
- **Haftalik bar chart** balandliklari daqiqa emas, kun-faolligi. Server
  daqiqa bermaydi. V3 tugagach haqiqiy daqiqaga o'tkazilishi mumkin.
- **Playwright E2E** desktop uchun yo'q; hozir faqat statik contract test bor.

---

## 7. Tegmaslik kerak

- To'lov, obuna, QA rejimi va ma'lumotlar bazasi mantig'i — vazifa aniq
  talab qilmasa
- Mini App interfeysi — avval so'ralmasa
- `PROJECT_MEMORY.md` ni to'liq qayta yozish
- Bir tilda matn qo'shish — RU/TJ/UZ uchtasi majburiy
- Keraksiz animatsiya, badge, dekorativ element

---

## 8. Yangi chatda boshlash uchun prompt

Quyidagi matnni to'liq nusxalab yangi chatga qo'ying. Oxirgi qatorda `V_`
o'rniga bajarmoqchi bo'lgan vazifa raqamini yozing.

```text
HSK AI bot loyihasida ishlaymiz, branch: feat/desktop-voice.

KOD YOZISHDAN OLDIN quyidagi fayllarni o'qi:
1. CLAUDE.md
2. PROJECT_MEMORY.md (oxiridagi 2026-08-10 yozuvi eng muhimi)
3. AI_RULES.md
4. DESKTOP_PROFILE_HANDOFF.md — bu ishning to'liq rejasi
5. desktop/design/hsk-ai-mac-demo_4.html — dizayn manbasi.
   Profil: <section id="screen-profile">, onboarding: id="startOnboarding"
6. Vazifaga tegishli mavjud fayllar

ASOSIY TALAB: profil ekrani va onboarding demoga 1:1 o'xshashi shart —
bloklar tartibi, tugmalar, ularning joylashuvi, barcha mayda detallar.

To'rt qoida:
- Demo'dagi namunaviy raqamlarni ko'chirma. Ma'lumot yo'q bo'lsa NO_VALUE ("—").
- Ishlamaydigan blokni olib tashlama va soddalashtirma: soonBlock() bilan
  o'ra — ko'rinishi qoladi, boshqaruvlari o'chadi, ustiga borilganda
  "Tez orada" chiqadi.
- Demo'da yo'q, bizda bor bo'limlar profil ekranining eng pastida turadi.
- Har qanday ko'rinadigan matn RU, TJ va UZ uchtasida bo'lishi shart.

O'qib bo'lgach menga qisqacha hisobot ber:
- qaysi fayllarni o'qiding
- vazifaga qaysi mavjud fayllar tegishli
- qanday arxitektura va qoidalarga amal qilasan
- qaysi fayllarni o'zgartirmoqchisan
- qanday xavflar ko'ryapsan

Keyin tasdig'imni kut. Tasdiqlamagunimcha kod yozma.

Tegmaslik kerak: to'lov, obuna, QA rejimi, Mini App interfeysi va DB
mantig'i — vazifa aniq talab qilmasa.

Bajaradigan vazifa: V_ — <nomi>
```

### Har bir vazifadan keyin

```bash
node --test desktop/ui/test-contract.mjs
cd desktop/src-tauri && cargo fmt --check
cargo clippy --locked --all-targets -- -D warnings
```

Yangi ko'rinadigan xatti-harakat qo'shilsa, `test-contract.mjs` ga tekshiruv
qo'shing va `PROJECT_MEMORY.md` ga qisqa yozuv yozing (formati `AI_RULES.md`
da).
