# HSK 3.0 — N4 source extraction context

Holat: 2026-11-27 | Scope: faqat HSK 3.0 4-daraja manba kontenti.
Branch: `feat/hsk30-nhsk4-source-extraction`.

## 1. Vazifa va qarorlar

Egasi HSK 4 ning ikki jildidan amaldagi N1–N3 kurslarida ishlatilgan turdagi ma'lumotlarni ajratib, mavjud formatda yig'ishni topshirdi. N3 normalized + translations modeli N4 uchun namuna. Bu bosqich yangi kursni production'da yoqish yoki UI/backend funksiyalarini o'zgartirish emas.

- HSK 4 上 — birinchi jild; HSK 4 下 — ikkinchi jild. Ikkinchisi dastlab `新 HSK 5.pdf` nomi bilan yuklangan; egasi aniqlashtirgach nomi tuzatildi. Jild identifikatsiyasini muqova va bibliografiya orqali qayta tekshirish kerak.
- PDF'lar #358 PR branch'ida yuklangan; ushbu extraction branch PDF commitidan yaratilgan. PR merge holatini ish boshlanishida qayta tekshir.
- LFS pointer va metadata tasdiqlangan, PDF sahifalari hali bevosita tekshirilmagan. Ajratilgan va tasdiqlangan N4 darslari: **0**. Dars soni, mavzular, so'zlar soni yoki betlarni taxmin qilma.

## 2. Canonical manbalar

| Jild | Repo yo'li | LFS hajmi (bytes) |
|---|---|---:|
| 上 | `HSK 3.0 PDF/新HSK教程4上 hanyu_uz.pdf` | 89498459 |
| 下 | `HSK 3.0 PDF/新HSK教程4下.pdf` | 101472153 |

SHA-256:
- 上: `5c903efa408e5378632c3fbe25b19b5d6d2768a0e1abda1a7df2f44f97781c68`
- 下: `ca041a0ff1cad6ec64bbceb7eb89dde0c8e9907e1fc5bb05d8b1d574ef0f562f`

Manba commit: `dca7937f8c3e88bdf350993b10a6a2f4a8f5885d`.
Canonical reestr: [nhsk4_source_manifest.json](nhsk4_source_manifest.json).
Manba haqiqiyligini yuklangan binary SHA-256 bilan tekshir; pointer matnining SHA'si PDF SHA'si emas.

## 3. Mavjud N1–N3 modeli

| Daraja | Kitob darslari | Vocabulary rows | Grammar | Dialogue blocks | Runtime parts |
|---|---:|---:|---:|---:|---:|
| N1 | 15 | 333 | 40 | 45 | 103 |
| N2 | 15 | 211 | 45 | 60 | 73 |
| N3 | 18 | 491 | 63 | 55 | 145 |

Vocabulary rows takror va maxsus yozuvlarni o'z ichiga olishi mumkin; syllabus unique so'z soniga teng deb hisoblama. N3 da 379 dialogue turn, 203 grammar example va 61 objective mavjud.

O'qilishi shart bo'lgan amaldagi fayllar:
- [Extraction rules](README.md)
- [N1 manifest](generated/nhsk1/manifest.json), [N2 manifest](generated/nhsk2/manifest.json)
- [N3 TOC](nhsk3_toc_map.json), [N3 normalized sample](normalized/nhsk3/lesson_01.json), [N3 translation sample](translations/nhsk3/lesson_01.json)
- [N3 validator](verify_nhsk3_normalized.py), [N3 adapter](nhsk3_adapter.py)
- [Course V3 generator](../gen_course_v3_from_seed.py)
- [Runtime parts manifest](../../app/static/course_v3_data/parts_manifest.json)
- [Project course design](../../docs/HSK_3.0_VERSIYASI.md)
- [AGENTS](../../AGENTS.md), [AI_RULES](../../AI_RULES.md), [PROJECT_MEMORY](../../PROJECT_MEMORY.md), [NEXTATION](../../NEXTATION.md).

## 4. Source va authored layer chegarasi

Kitobdan: dars tartibi va sarlavha, maqsadlar (mavjud bo'lsa), yangi so'zlar, hanzi, pinyin, so'z turkumi, grammatika mavzulari va manbadagi misollar, dialog sahnasi, speaker va replikalar, bet provenance. Proper nouns va beyond-syllabus belgilarini saqla; asl manbada pinyin yo'q bo'lsa, keyin alohida derived sifatida yoz.

AI/editor: UZ (lotin), RU va TJ (kirill) tarjimalari, tushuntirishlar, mavjud format talab qiladigan qo'shimcha izohlar. Original Chinese qatlam bilan aralashtirma.

Kitobdagi tayyor mashqlar mavjud bo'lsa, ularning turlari va sahifalarini inventarizatsiya qilish mumkin; amaldagi README qoidasi bo'yicha original mashq sahifalarini runtime'ga ko'chirma. Mashqlarni import qilish yoki nashr huquqi bo'yicha alohida owner qarori talab qilinadi. Kitobdagi rasmlar, audio yoki to'liq mashq sahifalari scope'ga avtomatik kirmaydi. Manba materiallari bo'yicha foydalanish huquqi doirasini tekshir.

## 5. Texnik chegaralar

N4 normalizatsiyasi N3 schema'ga mos bo'lsin: `track, level, lesson, source, title, objectives, vocabulary, grammar, dialogues`. Ikki jild uchun source ichida volume, pdf_path, pages va barqaror source commit; global lesson ID va jilddagi lesson raqami alohida saqlanadi. N3 validatorida source.ref='main' bo'lishi N4 uchun avtomatik shart emas; N4 provenance ikki faylni farqlashi kerak.

Mavjud N1–N3, HSK 2.0, progress, entitlement, payment, PWA/Android runtime, dictionary va release flag'lariga tegma. N4 live/selectable bo'lmasin. Faqat source/translation/validator scope. Hech qanday uydirma yoki placeholder darssiz verified status berilmaydi.

Keyingi ish tartibi va acceptance: [NHSK4_PLAN.md](NHSK4_PLAN.md).
