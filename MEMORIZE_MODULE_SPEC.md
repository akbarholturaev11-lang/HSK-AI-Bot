# Iyeroglifni tez eslab qolish — modul spetsifikatsiyasi

> **Format:** `course_v3_memorize.html` + `course_v3_data/memo/*.json`
> **Til:** uz / ru / tj (har bir matn 3 tilda)
> **Status:** dizayn (tasdiqdan keyin data + kod yoziladi)

---

## 0. Asosiy qaror — AI = AVTOMATIK (offline)

Bu modulda **jonli AI (backend model) chaqiruvi yo'q.** Hammasi:

- client-side ishlaydi (boshqa praktikalar kabi),
- har bir iyeroglif uchun **oldindan yozilgan data fayl**dan oziqlanadi,
- "AI tutor" hissi = sifatli yozilgan kontent + **deterministik adaptiv engine**.

Demak:
- Hech qanday `/api/.../ai` endpoint, model latency yoki budjet sarfi yo'q.
- "AI savol berdi / javob qaytardi" deganlari aslida **data'dagi tayyor matnlar**, engine user javobiga qarab to'g'risini tanlaydi.
- **Erkin matn baholash** (user xohlagan gapni AI tekshirishi) **YO'Q.** Uning o'rniga deterministik aktiv ishlab chiqarish:
  - **Cloze** (bo'sh joyni variantdan tanlash),
  - **Jumla yig'ish** (so'z bo'laklarini to'g'ri tartibda terish — kanonik tartib bilan tekshiriladi),
  - **"Tabiiyroq qaysi?"** (2–3 gapdan to'g'risini tanlash).

Bu user'ga "o'zim gap tuzdim" hissini beradi, lekin AI'siz, xatosiz, tez.

---

## 1. Learning formula

```
KO'R → TAXMIN QIL → TUSHUN → ESLAB QOLISH HOOK →
SO'ZDA KO'R → GAPDA ISHLAT → AKTIV TEST → XATO BO'YICHA REVIEW
```

**Balans:** AI tushuntirishi 40% · User aktiv harakati 60%.
Har 1–2 bosqichda user **tanlaydi / taxmin qiladi / teradi**. Faqat o'qish bo'lmaydi.

---

## 2. DATA SXEMA (per-iyeroglif) — modulning "format"i

Har bir iyeroglif bitta JSON obyekt. `t(...)` belgisi — `{uz,ru,tj}` ko'p tilli matn.

```jsonc
{
  "h": "想",
  "p": "xiǎng",
  "m": { "uz": "o'ylamoq / sog'inmoq", "ru": "...", "tj": "..." },   // asosiy tarjima
  "note": { "uz": "fikr, istak yoki sog'inish bilan bog'liq", "ru": "...", "tj": "..." }, // 1 jumlalik izoh
  "difficulty": "complex",            // "simple" | "complex"  → blok soni va flow uzunligi

  // --- 1-BLOK: ko'r va taxmin ---
  "guess": {
    "prompt": { "uz": "Bu iyeroglifga qarab, u nima bilan bog'liq bo'lishi mumkin?", ... },
    "options": [
      { "id": "mind",  "t": { "uz": "fikr / his", ... }, "near": true },
      { "id": "food",  "t": { "uz": "ovqat", ... } },
      { "id": "water", "t": { "uz": "suv / tabiat", ... } },
      { "id": "money", "t": { "uz": "pul / savdo", ... } }
    ]
    // "bilmayman" varianti engine tomonidan avtomatik qo'shiladi
  },

  // --- 3-BLOK: radikal / ma'no kaliti ---
  "radical": {
    "r": "心", "p": "xīn",
    "m": { "uz": "yurak", ... },
    "why_prompt": { "uz": "Nega bu iyeroglifda 心 bor deb o'ylaysiz?", ... },
    "why_options": [
      { "id": "feeling", "t": { "uz": "his / fikr bilan bog'liq", ... }, "near": true },
      { "id": "food", "t": { "uz": "ovqat bilan bog'liq", ... } },
      { "id": "place", "t": { "uz": "joy nomi", ... } }
    ],
    "signal": { "uz": "心 ko'pincha his, fikr, ichki holat bilan bog'liq iyerogliflarda keladi", ... }
  },

  // --- 4-BLOK: qismlarga ajratish ---
  "etymology_honest": false,          // false bo'lsa → engine "bu hook, tarixiy izoh emas" ogohlantirishini qo'shadi
  "breakdown": [
    { "part": "相", "p": "xiāng", "m": { "uz": "qarash / o'zaro", ... }, "role": "hook" },
    { "part": "心", "p": "xīn",   "m": { "uz": "yurak", ... },          "role": "radical" }
  ],

  // --- 5-BLOK: eslab qolish hook (2–3 xil) ---
  "hooks": [
    { "type": "story",   "t": { "uz": "Yurakda bir narsani ko'rish → o'ylamoq / sog'inmoq", ... } },
    { "type": "visual",  "t": { "uz": "Kimdir ko'z oldingda, yuragingda u haqida fikr bor", ... } },
    { "type": "radical", "t": { "uz": "心 bor — demak ichki his yoki fikr bor", ... } }
  ],

  // --- 6-BLOK: o'xshash / adashtiradigan (ixtiyoriy) ---
  "confusables": [
    { "h": "忘", "p": "wàng", "m": { "uz": "unutmoq", ... }, "diff": { "uz": "忘 = unutish", ... } },
    { "h": "忙", "p": "máng", "m": { "uz": "band bo'lmoq", ... }, "diff": { "uz": "忙 = bandlik", ... } }
  ],

  // --- 7-BLOK: real so'zlar (aniq 3 ta) ---
  "words": [
    { "w": "想家",    "p": "xiǎng jiā",      "m": { "uz": "uyni sog'inmoq", ... }, "tier": "simple" },
    { "w": "想起来",  "p": "xiǎng qǐlái",    "m": { "uz": "esga kelmoq", ... },    "tier": "useful" },
    { "w": "想不起来","p": "xiǎng bù qǐlái", "m": { "uz": "eslay olmaslik", ... }, "tier": "hsk" }
  ],

  // --- 8-BLOK: gapda ishlatish ---
  "sentence": {
    "zh": "我想家了。", "p": "Wǒ xiǎng jiā le.",
    "m": { "uz": "Men uyni sog'indim", ... },
    "cloze":  { "text": "我 ___ 家了。", "answer": "想", "distractors": ["忘", "忙", "喝"] },
    "build":  { "tiles": ["我", "想", "家", "了"], "answer": ["我", "想", "家", "了"] }
  },

  // --- 9-BLOK: test puli (engine 2–3 tasini tanlaydi) ---
  "tests": [
    { "type": "meaning",  "q": { "uz": "想 nima degani?", ... }, "answer": "o'ylamoq / sog'inmoq", "distractors": [...] },
    { "type": "pinyin",   "answer": "xiǎng", "distractors": ["xiàng", "shǎng", "jiǎng"] },
    { "type": "radical",  "q": { "uz": "想 ichidagi ma'no kaliti qaysi?", ... }, "answer": "心", "distractors": ["木", "目", "日"] },
    { "type": "translate","zh": "我想家了。", "answer": { "uz": "Men uyni sog'indim", ... }, "distractors": [...] },
    { "type": "cloze",    "ref": "sentence.cloze" },
    { "type": "confusion","options": ["想", "忘", "忙"], "answer": "想", "hint": { "uz": "心 bor — fikr/his", ... } },
    { "type": "reverse",  "q": { "uz": "'sog'inmoq / o'ylamoq' qaysi iyeroglif?", ... }, "answer": "想", "distractors": ["忘", "忙", "喝"] },
    { "type": "speed",    "ms": 3000, "answer": "o'ylamoq / sog'inmoq", "distractors": [...] }
  ]
}
```

Bu sxema = **modulning "to'g'ri format"i.** Data shu format bo'yicha to'ldiriladi.
Asosiy maydonlar (`h, p, m, words`) `hsk-data.js` dan ham olinishi mumkin; qolgani memo data faylida yoziladi.

---

## 3. Bloklar kutubxonasi

| # | Blok | Ekran | User harakati | Engine / data |
|---|------|-------|---------------|---------------|
| 1 | Ko'r & taxmin | Katta iyeroglif, pinyin/tarjima YO'Q | 1 variant tanlaydi (4 + "bilmayman") | `guess.options`; `near` → "Yo'nalish to'g'ri", aks holda → "ma'no kalitiga o'tamiz" |
| 2 | Asosiy ma'no | iyeroglif + pinyin + tarjima + 1 jumla | o'qiydi (qisqa) | `m`, `note` |
| 3 | Radikal | radikal + "nega?" savol | 1 variant tanlaydi | `radical.why_options` → `radical.signal` |
| 4 | Breakdown | 2–3 qism | "qaysi qism ko'proq yordam berdi?" | `breakdown`; `etymology_honest:false` → disclaimer |
| 5 | Hook | 2–3 eslab qolish usuli | "qaysi usul oson?" tanlaydi | `hooks`; tanlov user profiliga yoziladi |
| 6 | Confusion (ixtiyoriy) | o'xshash 2–3 iyeroglif | "qaysini adashtirasiz?" | `confusables`; bo'sh bo'lsa blok o'tkazib yuboriladi |
| 7 | Real so'zlar | 3 ta so'z | "qaysi so'z ko'proq kerak?" | `words`; tanlangan so'z 8-blokda ishlatiladi |
| 8 | Gapda ishlatish | gap + task | cloze / jumla yig'ish / "tabiiyroq qaysi?" | `sentence.cloze`, `sentence.build` |
| 9 | Aktiv test | 2–3 test | javob beradi | `tests` puli (error-adaptiv tanlov) |
| 10| Review | faqat xato joyi | qayta mashq | error-type → action (4-bo'lim) |

**Microcopy qoidasi:** har bir tushuntirish ≤ 1–2 qisqa jumla. Uzun nazariya/tarix yo'q.

---

## 4. Adaptiv engine (deterministik, AI'siz)

### 4.1 Mastery score (har iyeroglif, localStorage)
```
0 yangi · 1 ko'rdi (ishonchsiz) · 2 qisman · 3 yaxshi · 4 mustahkam
```
- to'g'ri test → +1 (max 4); xato → −1 (min 0) va xato turi yoziladi.
- localStorage: `hsk_memo[h] = { score, errors:{meaning,pinyin,radical,breakdown,usage,confusion}, seen, ts }`.

### 4.2 Xato turlari
`meaning_error · pinyin_error · radical_error · breakdown_error · usage_error · confusion_error`

### 4.3 Flow uzunligi (difficulty bo'yicha)
- **simple** → 5–6 blok: `1 → 2 → 3 → 7 → 8 → 9`
- **complex / adashadigan** → 8–10 blok: `1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10`

### 4.4 Format variation (kirish uslubi — 1 tasi tanlanadi)
Engine quyidagi tartibda hal qiladi:
1. user oldin xato qilgan iyeroglif → **error-based** (faqat xato bloki).
2. `confusables` bor + complex → ba'zida **confusion-first**.
3. user hook-uslubi "story" → **story-first**; "visual" → **radical/breakdown-first**; "sentence" → **sentence-first**.
4. default → **guess-first**.

Bir iyeroglifda 4–6 ta format aralashtiriladi, hammasi shart emas. Ketma-ket bir xil sxemani majburlamaslik.

### 4.5 User holatiga moslashish
- **tez & to'g'ri** → tushuntirish qisqaradi, test/gap ko'payadi, keyingi iyeroglif tez ochiladi.
- **sekin / xato** → breakdown + radikal qayta, o'xshash bilan solishtirish.
- **"bilmayman" ko'p** → ochiq savol kamayadi, variantli savol ko'payadi, yo'naltiruvchi savol.

### 4.6 Test tanlash (9-blok)
2–3 test, xato tarixiga qarab:
- pinyin xato → pinyin testi ko'proq
- meaning xato → meaning + translate
- radical xato → radical + breakdown qayta
- usage xato → cloze / build
Yangi iyeroglif → `meaning` + `cloze` + (`pinyin` yoki `reverse`).

---

## 5. Ekranlar ketma-ketligi (state machine)

```
ENTER(h)
  └─ format_variation tanla
     ├─ guess-first     → B1 → B2 → middle(B3..B6) → B7 → B8 → TEST → COMPLETE?
     ├─ radical-first   → B3 → B1 → B2 → B4 → B7 → B8 → TEST → COMPLETE?
     ├─ story-first     → B2 → B5 → B1 → B7 → B8 → TEST → COMPLETE?
     ├─ sentence-first  → B8(ko'r) → B2 → B3 → B7 → TEST → COMPLETE?
     ├─ confusion-first → B6 → B2 → B3 → B7 → B8 → TEST → COMPLETE?
     └─ error-based     → REVIEW(xato bloki) → kichik TEST → COMPLETE?

TEST → har javob mastery'ni yangilaydi
COMPLETE? (3 shart, 7-bo'lim)
  ├─ ha  → "O'rgandingiz" + keyingi iyeroglif tugmasi
  └─ yo'q→ REVIEW(eng zaif blok) → qayta kichik TEST
```

`middle(B3..B6)` — difficulty va format'ga qarab tanlangan 1–3 blok.

---

## 6. "AI feedback" o'rniga — tanlov logikasi (data'dan)

AI'siz bo'lgani uchun har bir feedback **tayyor matn**, engine user javobiga qarab tanlaydi:

**1-blok (taxmin):**
- option.near=true → `fb.near` ("Yo'nalish to'g'ri")
- boshqa option → `fb.off` ("Yaxshi, endi ma'no kalitini ko'ramiz")
- bilmayman → `fb.idk` ("Muammo yo'q, hozir qismlarga ajratamiz")

**Test (9-blok):**
- to'g'ri → `fb.ok` ("Zo'r") + mastery +1
- xato → `fb.err[type]` ("Yaqin, lekin ma'no '...'. Qayta ko'ramiz") + mastery −1 + xato turi yoziladi

**Review (10-blok) — xato turiga mos (umumiy emas):**
| Xato | Engine harakati (data matni bilan) |
|------|-----------|
| meaning_error | gapda qayta ko'rsatadi (B8 ref) |
| pinyin_error | 2 ta tez pinyin mashqi |
| radical_error | radikalni qayta eslatadi (B3) |
| confusion_error | o'xshash bilan 20 soniyalik farqlash (B6) |
| usage_error | cloze / build qayta |

Disclaimer (etymology_honest=false): "Bu qismlar tarixiy izoh emas, eslab qolish uchun yordamchi hook." — 3 tilda, data'da tayyor.

---

## 7. Lesson complete shartlari

Iyeroglif **faqat "Keyingisi" bosilsa** — o'rganish hisoblanmaydi. Tugashi uchun **3 shart**:

1. ✅ **meaning test** to'g'ri
2. ✅ kamida **1 ta word recognition** to'g'ri (7-blok yoki test)
3. ✅ kamida **1 ta sentence/usage task** bajarildi (cloze yoki build)

Shartlar bajarilmasa → engine yetishmagan blokka qaytaradi, "Keyingisi" faollashmaydi.
Bajarilsa → "O'rgandingiz" ekrani + mastery saqlanadi + keyingi iyeroglif.

---

## 8. Microcopy uslubi (3 til)

| Yomon | Yaxshi |
|-------|--------|
| "Bu iyeroglif qadimgi xitoy yozuvida…" | "心 bor — demak ichki his yoki fikr bor." |
| "Quyidagi misollarni o'rganing." | "Endi bu iyeroglifni real so'zda ko'ramiz." |
| "Javobingiz noto'g'ri." | "Yaqin, lekin bu yerda ma'no 'sog'inmoq'. Qayta ko'ramiz." |

Hamma matn uz/ru/tj. Ohang: qisqa, rag'batlantiruvchi, ayblovsiz.

---

## 9. To'liq misol — 想

1. **Ko'r:** katta `想`. "Bu nima bilan bog'liq?" → [fikr/his] [ovqat] [suv] [pul] [bilmayman]
2. user tanlaydi → `near` bo'lsa "Yo'nalish to'g'ri".
3. **Ma'no:** 想 — xiǎng — o'ylamoq / sog'inmoq. "fikr, istak yoki sog'inish bilan bog'liq."
4. **Radikal:** 心 (yurak). "Nega 心 bor?" → tanlaydi → "心 ko'pincha his/fikr bilan keladi."
5. **Breakdown:** 想 = 相 + 心. "Qaysi qism ko'proq yordam berdi?" + (hook disclaimer).
6. **Hook:** [yurak+fikr] [ko'z oldida odam] [gap orqali] → tanlovi profilga yoziladi.
7. **So'zlar:** 想家 · 想起来 · 想不起来 → "qaysi ko'proq kerak?"
8. **Gap:** 我想家了 → **cloze** `我 ___ 家了` [想/忘/忙/喝], keyin **build** [我][想][家][了].
9. **Test:** meaning + cloze + (confusion: 想/忘/忙).
10. **Review (agar xato):** confusion_error → 想 vs 忘 farqi 20 soniyada.

## 9b. Qisqa misol — 不 (simple)
`1 ko'r → 2 ma'no(bù, "yo'q/emas") → 3 eng muhim qism → 7 so'zlar(不是/不要/不客气) → 8 cloze → 9 meaning+pinyin`. Review faqat xato bo'lsa.

---

## 10. Saqlash (storage)
- v1: **localStorage** (`hsk_memo`) — mastery, xato turlari, hook-uslub tanlovi.
- (keyinroq ixtiyoriy: `/api/v3/lesson/complete` ga mastery yuborish — alohida qaror.)

---

## 11. Qarorlar (tasdiqlangan)
1. Data hajmi: **butun HSK1 yopildi** → ✅ `course_v3_data/memo.js` da **87 ta iyeroglif** (HSK1 ning 84 ta yakka iyeroglifining 84/84 tasi + 3 bonus: 们 妈 中). Final audit o'tdi: pinyin to'g'ri, feedback qisqa (<110), breakdown halol (fonosemantik; soxta etimologiya 我/是/们 da disclaimer bilan), 3 til to'liq.
2. 8-blok "build" (jumla yig'ish, tiles): **ha** → ✅ cloze + build ikkalasi ham bor.
3. Mastery: **localStorage (v1)** → ✅ `hsk_memo` (score 0–4 + xato turlari + hook tanlovi).

### Keyingi bosqich (kelajak)
- Memo data'ni HSK1 (170) → keyin HSK2–4 ga kengaytirish.
- Talaffuz / Ajratish sahifalariga `char`-fokus rejimi (hozir `char`ni e'tiborsiz qoldiradi).
