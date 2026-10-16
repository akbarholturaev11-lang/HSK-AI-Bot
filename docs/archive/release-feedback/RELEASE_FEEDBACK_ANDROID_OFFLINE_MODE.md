# Release feedback draft — Android: ilova internetsiz ochiladi

Holat: draft. Android 1.7.1 R2’ga chiqib, ichki telefonda samolyot rejimida
sinalgandan keyin admin ko‘rib chiqib, mavjud Release feedback moduli orqali
qo‘lda tasdiqlasa yuborilsin. Userlarga avtomatik yuborilmaydi.

## Release nomi

Android 1.7.1: ilova internetsiz ham ochiladi

## Userga yuboriladigan qisqa matn

Android ilovasi endi internet yo‘q joyda ham ochiladi. Metroda yoki
samolyotda Ieroglif lug‘ati — so‘zlar, ovoz, misollar va yozish mashqi — hamda
kurs xaritasi ishlaydi. Tepada «Internet yo‘q» yozuvi turadi, aloqa tiklansa
ilova o‘zi ulanadi. Fikr qoldirsangiz, obunangiz bo‘lmasa sizga 24 soatlik 20%
chegirma beriladi.

## Nima yangilandi va qayerda sinash

Android ilovasini 1.7.1 versiyasiga yangilang va **bir marta internet bilan
oching** (ilova hisobingizni shu paytda eslab qoladi). Keyin:

- telefonni samolyot rejimiga qo‘ying, ilovani yopib qayta oching;
- tepada «Internet yo‘q» yozuvi chiqadi, kurs xaritasi ko‘rinadi;
- `Mashq` → `Ieroglif lug‘ati` — qidiruv, ovoz, yozish ishlaydi;
- AI Voice, Reyting, Profil «Bu bo‘lim uchun internet kerak» deydi;
- samolyot rejimini o‘chiring — yozuv o‘zi yo‘qoladi, hamma bo‘lim ochiladi.

## “Sinab ko‘rish” tugmasi

Offline rejim uchun deep link yo‘q, shuning uchun tugma bot orqali Android
ilovasini olish yo‘liga (`/android`) olib borsin; xabarda aniq instruksiya
bo‘lsin: «Ilovani 1.7.1 ga yangilang → bir marta internet bilan oching →
samolyot rejimida qayta oching → Mashq → Ieroglif lug‘ati». Kampaniyadan oldin
admin ichki test akkauntida shu ketma-ketlikni tekshiradi.

## Baho va mukofot

Savol: “Ilova internetsiz ochilishi va lug‘at ishlashi siz uchun foydali
bo‘ldimi?” 1 — umuman yo‘q, 5 — juda foydali.

Fikr qoldirish taklifi: “Fikr qoldirsangiz, obunangiz bo‘lmasa sizga 24 soatlik
20% chegirma beriladi.” Tizim mukofotni bergach: “Rahmat. Aytganimizdek,
sizga 24 soatlik 20% chegirma berildi.”

## Target va o‘lchovlar

Target: Android ilovasi o‘rnatilgan faol o‘quvchilar, ayniqsa lug‘atdan
foydalanadiganlar va internet sekin/uzilib turadigan hududdagilar.

Kuzatish: kampaniya yetkazilishi va `Sinab ko‘rish` bosilishi; 1–5 baholar va
izohlar; 20% chegirma berilishi/ishlatilishi; 1.7.1 ga yangilanganlar soni
(`android/latest.json` va yangilanish tekshiruvlari). Offline ochilishlar
serverga yetib bormaydi, shuning uchun alohida analitika yo‘q — izohlar va ichki
test bilan baholansin.
