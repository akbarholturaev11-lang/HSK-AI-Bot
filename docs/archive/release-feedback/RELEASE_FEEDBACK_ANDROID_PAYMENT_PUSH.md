# Release feedback draft — Android obuna va to‘lov bildirishnomalari

Holat: draft. Deploy va ichki Android sinovidan keyin admin ko‘rib chiqib,
mavjud Release feedback moduli orqali qo‘lda tasdiqlasa yuborilsin.

## Release nomi

Android 1.6.13: Mini App bilan mos obuna va to‘lov holati bildirishnomalari

## Userga yuboriladigan qisqa matn

Android ilovasidagi Obuna bo‘limi Mini App’dagi tarif va to‘lov ko‘rsatmalariga
moslashtirildi. To‘lov so‘rovingiz admin tomonidan tasdiqlansa yoki rad etilsa,
ilova holatni tezkor bildirishnoma bilan yuboradi. Bildirishnomani ekran
yuqorisida va blokirovka ekranida ko‘rish uchun telefon sozlamalarida HSK AI
bildirishnomalariga ruxsat bering. Fikr qoldirsangiz, obunangiz bo‘lmasa sizga
24 soatlik 20% chegirma beriladi.

## Nima yangilandi va qayerda sinash

Android ilovasini 1.6.13 versiyasiga yangilang. `Obuna` bo‘limida tarif,
mamlakat/to‘lov usuli, to‘lov ko‘rsatmasi va chek yuborishni tekshiring.
Haqiqiy to‘lov qilish shart emas. To‘lov holati push’ini sinash uchun avval
ichki test akkauntida chek yuborib, admin tasdiqlash va rad etishni tekshirsin;
oddiy foydalanuvchi esa obuna so‘rovi bo‘yicha admin qaroridan keyin kelgan
bildirishnomani, notification shade va lock screen’da ko‘rish ruxsat berilgan
bo‘lsa, tekshirishi mumkin.

## “Sinab ko‘rish” tugmasi

Mavjud modulda kampaniyaning sinash joyini `Obuna/Chegirma` tanlang. Tugma bot
orqali obuna Mini App’ini ochadi; xabardagi yuqoridagi qadamlar Android
1.6.13’dagi oqimni alohida tekshirishni tushuntiradi. Kampaniyani ishga
tushirishdan oldin admin ichki test akkauntida Android deep link va push
yetib borishini tekshiradi.

## Baho va mukofot

Savol: “Android’da obuna yuborish va admin qarori haqidagi bildirishnoma
tushunarlimi?” 1 — tushunarsiz, 5 — juda tushunarli.

Fikr qoldirish taklifi: “Fikr qoldirsangiz, obunangiz bo‘lmasa sizga 24 soatlik
20% chegirma beriladi.” Tizim mukofotni bergach: “Rahmat. Aytganimizdek,
sizga 24 soatlik 20% chegirma berildi.”

## Target va o‘lchovlar

Target: Android ilovasida obuna bo‘limini ochgan foydalanuvchilarning kichik
test guruhi; imkon bo‘lsa yaqinda to‘lov yuborgan foydalanuvchilar.

Kuzatish: kampaniya yetkazilishi va `Sinab ko‘rish` bosilishi; 1–5 baholar va
izohlar; 20% chegirma berilishi/ishlatilishi; Android FCM tokenlari ro‘yxatdan
o‘tishi; admin qaroridan keyin push yuborishdagi muvaffaqiyat/xatolar; Android
obuna sahifasini ochish va chek yuborish. Hozir push delivery/open uchun
alohida analitika yo‘q, shuning uchun server loglari va test akkauntidagi
qurilma tekshiruvi bilan kuzatilsin.
