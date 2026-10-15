# Course v3 dars ma'lumotlari: manba va qayta yaratish qoidalari

Bu faylning oldingi matni HSK 1–4 uchun eski formatda qo'lda JSON yaratishni va har darajaga 15/15/20/20 ta fayl yozishni so'rardi. Hozirgi kurs mini-darslarga bo'lingan va seed ma'lumotidan generator orqali chiqariladi; eski promptni kontent yaratish uchun ishlatmang.

## Manba tartibi

- Runtime fayllari `app/static/course_v3_data/{level}/lesson_XX.json` — generator chiqargan mini-darslar. Ularning soni darslikdagi source lesson soniga teng emas.
- Kanonik generator: `scripts/gen_course_v3_from_seed.py`. HSK 2.0 kontenti `scripts/seed_hsk*_lesson_*.py` va tegishli seed builder'laridan olinadi. HSK 3.0 source extraction tartibi `scripts/hsk30/README.md` va `docs/HSK_3.0_VERSIYASI.md`da.
- Seed va PDF manba sahifalari tekshirilmasdan yangi so'z, grammatika, tarjima yoki dars yaratmang. Mavjud UZ/RU/TJ tarjimalarini va kitobdan olingan xitoycha matnni asossiz qayta yozmang.
- `card_id`, `objective_id`, karta/bo'lim tartibi va `material_ref` pozitsiyalari mastery, xato tuzatish va progress bilan bog'langan. Kontent o'zgarishida ularni saqlash kerak.

## Generatorni ishlatish

Avval faqat dry-run qiling:

```bash
venv_311/bin/python3.11 scripts/gen_course_v3_from_seed.py --track hsk20 --dry
venv_311/bin/python3.11 scripts/gen_course_v3_from_seed.py --track hsk30 --dry
```

Bitta source lesson uchun daraja va track'ni aniq ko'rsating; `--lesson` runtime mini-dars raqamini emas, darslikdagi source lesson raqamini oladi:

```bash
venv_311/bin/python3.11 scripts/gen_course_v3_from_seed.py --track hsk20 --level hsk2 --lesson 3 --dry
venv_311/bin/python3.11 scripts/gen_course_v3_from_seed.py --track hsk30 --level nhsk1 --lesson 1 --dry
```

`--dry` olib tashlansa fayllar yoziladi. Bitta darajani to'liq qayta yaratishdan oldin seedlarni va dry-run natijasini tekshiring: generator tanlangan darajadagi eski `lesson_*.json` fayllarini o'chirib, keyin hammasini qayta yaratadi. `--lesson` bilan qisman qayta yaratish eski ortiqcha mini-dars fayllarini tozalamaydi; natijadagi fayl ro'yxatini alohida tekshiring.

## Tekshiruv

O'zgarishdan keyin `git diff` orqali faqat kutilgan kontent yangilangani, fayllar yo'qolmagani yoki ortiqcha qolmagani va indekslar siljimaganini tekshiring. So'ng `venv_311/bin/python -m pytest tests/test_course_v3_static_data.py -q` ni ishlating; source extraction o'zgarsa tegishli `scripts/hsk30/verify_*.py` tekshiruvini ham bajaring. Test o'tishi source matnining to'g'riligini yoki pedagogik sifatini o'zi isbotlamaydi — PDF/seed bilan ko'rib chiqing.
