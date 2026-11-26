# HSK 3.0 — N4 maqsad va ish rejasi

Holat: BLOCKED — PDF binary access zarur. Tayyorlangan source darslar: 0.
Kontekst: [NHSK4_CONTEXT.md](NHSK4_CONTEXT.md).

## Maqsad

HSK 4 上 va 下 jildlaridagi amaldagi N1–N3 kurslariga kerak bo'lgan manba ma'lumotlarini to'liq, sahifagacha traceable, tekshiriladigan shaklda yig'ish. N3'dagi normalized va translations formatini qayta ishlatish. Ushbu task yakuni — verified source dataset; runtime release alohida task.

## 0. Ish muhiti va manba tekshiruvi

- [ ] AGENTS.md, AI_RULES.md, PROJECT_MEMORY.md, NEXTATION.md va tegishli extraction/verify fayllarni o'qi; current main SHA, branch va #358 holatini qayta tekshir.
- [ ] Ikkala LFS PDF binary'ni lokal checkout'da ol; mavjud yuklangan LFS obyektlarini qayta push qilish kerak emas. Masalan ushbu branch checkout qilingach:
  ```bash
  git lfs pull --include="HSK 3.0 PDF/新HSK教程4上 hanyu_uz.pdf,HSK 3.0 PDF/新HSK教程4下.pdf" --exclude=""
  shasum -a 256 "HSK 3.0 PDF/新HSK教程4上 hanyu_uz.pdf" "HSK 3.0 PDF/新HSK教程4下.pdf"
  ```
- [ ] SHA-256 va hajmni source manifest bilan solishtir. PDF ochilishini, muqova, ISBN/edition, jild tartibi, page count va printed/PDF pagination'ni aniqlash.
- [ ] Agar access yo'q yoki hash mos kelmasa, shu yerda to'xta; manifestda blocker yoz. Qisman noma'lum qiymatlarni taxminan to'ldirma.

## 1. Mundarija va coverage xaritasi

- [ ] Ikkala jildning haqiqiy mundarijasini o'qi; jilddagi dars raqami, global dars ID, sarlavha, PDF va printed page ranges, grammar labels va review bo'limlarini qayd et.
- [ ] Jildlarning raqamlashi davom etadimi yoki qayta boshlanadimi tekshir. Global ID deterministik, takrorsiz bo'lsin; jilddagi raqam saqlansin.
- [ ] `nhsk4_source_manifest.json`ni verified metadata bilan yangila. `nhsk4_toc_map.json` yarat (N3 TOC modeli, ikki jild uchun volume-specific page refs).
- [ ] Mundarijani real lesson first/last page bilan tekshir. Dars soni faqat shu bosqichdan keyin belgilanadi.

## 2. Pilot — bitta to'liq dars

- [ ] Birinchi haqiqiy darsni barcha tegishli sahifalaridan ajrat.
- [ ] `normalized/nhsk4/lesson_01.json` yarat; N3 contract maydonlari:
  - `track: hsk30`, `level: nhsk4`, `lesson`, `source` (volume, pdf_path, ref, pages), `title` (hanzi/pinyin);
  - `objectives` (kitobda mavjudlari);
  - `vocabulary` (hanzi, pinyin, part_of_speech, source_page; optional source flags);
  - `grammar` (label, source_page, examples: hanzi/pinyin);
  - `dialogues` (scene, source_page, turns: speaker/hanzi/pinyin).
- [ ] Asl Chinese, punctuation, proper names, ohang belgilarini PDF'ga solishtir. Manbada bo'lmagan pinyin yoki boshqa izohni alohida derived provenance bilan belgilash; noaniq matnni flag qilish.
- [ ] `translations/nhsk4/lesson_01.json` yarat: N3 translation contract asosida goal, intro_text, vocabulary, grammar explanations/examples, dialogue scene/turn translations. UZ Latin, RU/TJ Cyrillic. Source identity va tartib aynan mos.
- [ ] Pilotni source va translation bilan qo'lda tekshir; aniqlanmagan kamchiliklar qolsa qolgan darslarga ommaviy tatbiq etma.

## 3. Barcha darslarni bosqichma-bosqich yig'ish

- [ ] 上 jilddagi barcha darslarni ajrat, review va vocabulary index'ni alohida audit qil.
- [ ] 下 jilddagi barcha darslarni xuddi shu schema'da ajrat.
- [ ] Har darsga source page traceability; bir darsga bitta normalized va bitta translation JSON. Darslar orasida duplicate ID, tushib qolgan sahifa yoki source band bo'lmasin.
- [ ] Kitobdagi lug'at indekslari, proper nouns, beyond-syllabus belgilarini alohida tekshir; raw row counts va unique counts'ni farqla. Rasmiy syllabus bilan tenglikni isbotsiz e'lon qilma.
- [ ] Original mashqlarni runtime'ga ko'chirma. Mavjud mashq turlari va betlarini kerak bo'lsa inventory sifatida qayd et; original exercise import alohida scope.
- [ ] Har batch uchun dars ID'lari, source checks, tarjima checks, open issues va completion status'ni manifestda qayd et. To'liq bo'lmagan datasetni complete deb belgilama.

## 4. Validatsiya

- [ ] `verify_nhsk4_normalized.py` — N3 validator usulida ikki jildni qamrab oluvchi source/TOC/lesson/field/page checks.
- [ ] Translation alignment validator — lesson/source title, vocabulary row identity, grammar label/example identity, dialogue scene/turn identity, UZ/RU/TJ nonempty, script checks; N3 adapter qoidalarini qayta ishlat.
- [ ] Manifestda haqiqiy lesson/vocab/grammar/example/dialogue/turn/objective totals, jildlar kesimi va unresolved issues.
- [ ] Barcha darslar uchun sahifa bo'yicha source review; avtomatik test structural validity'ni isbotlaydi, matnning PDF'ga aynan mosligini o'zi isbotlamaydi.
- [ ] Mavjud N1–N3 source checks va tegishli testlarni o'zgartirmasdan ishga tushir. Test natijalari, commit va tekshiruv cheklovlarini yoz.

## 5. Yakun va PR

- [ ] Faqat N4 source, translation, validation va tegishli hujjatlar commit qilinsin. N4 runtime generation, unlock/selectable va deploy bu taskga kirmaydi.
- [ ] Diff review: N1–N3 runtime, payment, account, progress, UI va admin live-level flag o'zgarmagan.
- [ ] #358 main'ga merge bo'lgach, extraction branch'ni yangi main bilan xavfsiz moslashtir. PR'da PDF'larning o'zi takroriy o'zgarish sifatida chiqmasin.
- [ ] Owner review va tegishli CI. Source va tarjimalar qabul qilingandan keyingina N4 adapter/generator/runtime integration alohida rejalashtiriladi.

## Acceptance mezonlari

1. Ikkala PDF binary hash bilan tekshirilgan; jild va nashr tasdiqlangan.
2. Har bir haqiqiy dars TOC'da va normalized dataset'da mavjud, duplicate yoki missing ID yo'q; lesson count taxmin emas.
3. Har bir source vocabulary/grammar/dialogue materiali original betga bog'langan; asl va authored ma'lumot ajratilgan.
4. Uch tildagi tarjimalar source bilan birma-bir mos va validatsiyadan o'tgan; unresolved errors yashirilmagan.
5. Source/translation validatorlar va tegishli regressiya testlari o'tgan, dalillar keltirilgan.
6. N4 hali live emas; amaldagi kurslar va business logic o'zgarmagan.
7. Manifest final counts va haqiqiy completion status'ni aks ettiradi. Egasi review qilishi uchun PR tayyor.

## Hozirgi next action

Lokal muhitda haqiqiy LFS binary'larni olish va hash tekshiruvi. Shundan keyin mundarija xaritasini tuzish va birinchi dars pilotini ajratish. Connector PDF pointer'larini ko'ra oladi, lekin PDF sahifalari olinmaguncha hech qanday dars verified emas.
