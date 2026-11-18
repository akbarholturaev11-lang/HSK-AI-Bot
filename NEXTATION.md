# NEXTATION — HSK AI kelgusi ishlar

Bu fayl loyiha egasi kelajakda bajarish uchun saqlagan g‘oya va vazifalarning yagona ro‘yxati. Admin PWA, yangi server, avtomatik eslatma yoki doimiy monitoring talab qilinmaydi.

**Ochiq repo:** bu fayl hammaga ko‘rinadi. Tokenlar, shaxsiy ma'lumotlar va maxfiy biznes g‘oyalarini yozmang.

## Agentlar uchun qoidalar

1. Har yangi ish sessiyasida `AGENTS.md`, `AI_RULES.md` va `PROJECT_MEMORY.md` bilan birga ushbu faylni o‘qing.
2. Egasi yangi topshiriqni aniq bermagan bo‘lsa, ochiq vazifalarni qisqacha aytib, qaysisini boshlashni taklif qiling. Joriy topshiriq aniq bo‘lsa, uni bo‘lmang; faqat tegishli yozuvlarni kontekst sifatida ishlating.
3. Yangi g‘oyani faqat egasining aniq «saqlab qo‘y» yoki boshqa tasdig‘idan keyin yozing. Qisqa maqsad, scope, asosiy xavf va qabul mezonini qayd eting; takror yozuv yaratmang.
4. Taklif va qayd **implementatsiyaga ruxsat emas**. Egasi ruxsat bermasa, ishni boshlamang.
5. Vazifa boshqa agentga topshirilganda uni o‘chirmang: `IN_PROGRESS` holatiga o‘tkazing. Natija tayyor bo‘lgach `VERIFY` ga o‘tkazing. Tekshiruv muvaffaqiyatli va egasi yopishga rozi bo‘lgach, yozuvni faol ro‘yxatdan olib tashlang. Git tarixi qaydni saqlaydi.
6. `main` dagi branch protection, CI va egasi ruxsati talablariga amal qiling. Lokal agent GitHub’dagi eng yangi ro‘yxatni ko‘rishi uchun repozitoriyni sinxronlashtirish kerak.

## Statuslar

- `PLANNED` — tasdiqlangan, hali boshlanmagan.
- `IN_PROGRESS` — egasi ruxsat bergan, amalga oshirilmoqda.
- `VERIFY` — bajarilgan, tekshiruv/yakuniy tasdiq kutilmoqda.

## Kelgusi vazifalar

### NXT-001 — HSK AI optimizatsiyasi (PWA + Android + Backend)
- Status: IN_PROGRESS
- Added: 2026-11-18
- Priority: current
- Goal: HSK AI ilovasining tezligi va ishlash samaradorligini yaxshilash.
- Scope: Avval kelishilgan umumiy PWA + Android + Backend optimizatsiyasi; [talablar](docs/PERFORMANCE_BACKEND_PWA_GOALS_REQUIREMENTS.md) va [performance qoidalari](docs/PERFORMANCE_PWA_PROGRESSIVE_LOADING.md) bo‘yicha. Desktop rivojlantirish hozircha scope'dan tashqarida.
- Risks / open questions: Tezlikni yaxshilash auth, kurs, progress, Pro va to‘lov oqimlarini buzmasligi kerak. Realizatsiya bosqichi egasining 2026-11-18 dagi xabariga asoslangan; aniq bajarilgan qismlar va testlar bu qaydda hali tasdiqlanmagan.
- Acceptance: Tegishli performance talablari, platformalararo regression testlari va real o‘lchovlar tekshirilgach `VERIFY` bosqichiga o‘tkaziladi.
- Implementation: Realizatsiya jarayonida; aniq PR/commit havolalari keyin qo‘shiladi.

<!-- Yozuv namunasi (vazifa emas):

### NXT-001 — Qisqa nom
- Status: PLANNED
- Added: YYYY-MM-DD
- Priority: normal
- Goal: Kutilgan natija
- Scope: Kiritiladigan va kiritilmaydigan ishlar
- Risks / open questions: ...
- Acceptance: Qanday tekshiriladi
- Implementation: PR yoki commit havolasi (agar mavjud bo‘lsa)

Birinchi haqiqiy vazifa qo‘shilganda "Hozircha saqlangan vazifa yo‘q." satrini olib tashlang.
-->
