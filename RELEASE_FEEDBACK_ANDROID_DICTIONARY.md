# Release feedback draft — Android lug‘ati: yangi ieroglif sahifasi va yozish mashqi

Holat: draft. Android 1.7.0 R2’ga chiqib, ichki telefonda sinalgandan keyin
admin ko‘rib chiqib, mavjud Release feedback moduli orqali qo‘lda tasdiqlasa
yuborilsin. Userlarga avtomatik yuborilmaydi.

## Release nomi

Android 1.7.0: internetsiz lug‘at, ieroglif yozish mashqi va qidiruv tarixi

## Userga yuboriladigan qisqa matn

Android ilovasidagi Ieroglif lug‘ati yangilandi. Endi har bir ieroglif
sahifasida uni eshitish, yozilish tartibini ko‘rish va ekranda barmog‘ingiz
bilan o‘zingiz yozib mashq qilish mumkin — ilova har bir chiziqni tekshiradi.
Ieroglif qaysi qismlardan tuzilgani va real gaplardagi misollar ham qo‘shildi.
Lug‘at to‘liq internetsiz ishlaydi. Fikr qoldirsangiz, obunangiz bo‘lmasa sizga
24 soatlik 20% chegirma beriladi.

## Nima yangilandi va qayerda sinash

Android ilovasini 1.7.0 versiyasiga yangilang. `Mashq` → `Ieroglif lug‘ati`:

- istalgan so‘zni qidirib oching: katta ieroglif, tarjima, «Eshitish»,
  «Tartibi», «Yozish» tugmalari;
- «Yozish» — ilova avval yozib ko‘rsatadi, keyin 3 bosqichda o‘zingiz
  yozasiz (iz bo‘ylab → ishora bilan → xotiradan);
- sahifa pastida «Qismlari» va «Misollar»;
- qidiruv maydoniga bosing — oxirgi 5 ta qidiruvingiz chiqadi;
- telefonni samolyot rejimiga qo‘yib ham sinab ko‘ring: so‘zlar, ovoz,
  misollar va yozish ishlashi kerak.

## “Sinab ko‘rish” tugmasi

Android’da lug‘at uchun deep link yo‘q, shuning uchun tugma bot orqali Android
ilovasini olish yo‘liga (`/android`) olib borsin; xabarda aniq instruksiya
bo‘lsin: «Ilovani 1.7.0 ga yangilang → Mashq → Ieroglif lug‘ati → biror so‘zni
oching → Yozish». Kampaniyani ishga tushirishdan oldin admin ichki test
akkauntida yangilanish kelishini va lug‘atni tekshiradi.

## Baho va mukofot

Savol: “Yangi lug‘at sahifasi va ieroglif yozish mashqi ieroglifni eslab
qolishga yordam berdimi?” 1 — umuman yo‘q, 5 — juda yordam berdi.

Fikr qoldirish taklifi: “Fikr qoldirsangiz, obunangiz bo‘lmasa sizga 24 soatlik
20% chegirma beriladi.” Tizim mukofotni bergach: “Rahmat. Aytganimizdek,
sizga 24 soatlik 20% chegirma berildi.”

## Target va o‘lchovlar

Target: Android ilovasi o‘rnatilgan faol o‘quvchilar, ayniqsa HSK1–HSK2
darajadagilar (yozishni endi o‘rganayotganlar).

Kuzatish: kampaniya yetkazilishi va `Sinab ko‘rish` bosilishi; 1–5 baholar va
izohlar; 20% chegirma berilishi/ishlatilishi; 1.7.0 ga yangilanganlar soni
(`android/latest.json` va yangilanish tekshiruvlari). Hozir lug‘at ichidagi
harakatlar (yozish mashqi, tarix) uchun alohida analitika yo‘q — izohlar va
ichki test bilan baholansin.
