# Release feedback draft — Pro checkout va do‘st taklifi

Holat: draft. Deploy va ichki testdan keyin admin tasdiqlasa, mavjud Release feedback moduli orqali yuboriladi. Avtomatik jo‘natilmaydi.

## Release nomi

HSK AI Pro: soddaroq obuna va telefonga mos do‘st taklifi

## Userga yuboriladigan qisqa matn

Pro obuna oynasi soddalashdi: tariflar darhol ko‘rinadi, matn dars tilingizga mos. 20% chegirma uchun do‘st taklif qilsangiz, havola do‘stingiz telefoniga mos qadamlarni ko‘rsatadi. Androidda do‘st avval botda taklifni qayd etadi, APK faylini shu chatdan oladi va o‘sha Telegram hisobini ilovaga ulaydi; iPhone’da botdagi 2 savolni ishlatadi.

## Nima yangilandi va qayerda sinash

Android ilovasini 1.6.14 ga yangilang yoki Telegram Mini App’ni oching → Pro → tarif va yordam tugmasini tekshiring. “Do‘stlarni chaqirish” havolasini Androidda oching → Telegram tugmasi → botda Start → chatga yuborilgan APK faylini o‘rnatish → ilovada o‘sha hisobni ulash. iPhone’da botdagi 2 savol yo‘lini tekshiring. Test hisoblarda haqiqiy ulanishdan keyin 20% hisoblagichi yangilanishini ko‘ring.

## “Sinab ko‘rish” tugmasi

Mavjud modulda `Obuna/Chegirma` yo‘nalishini tanlang: u Pro Mini App oynasini ochadi. Agar Android ilovasiga to‘g‘ridan to‘g‘ri ochish qo‘llanmasa, xabardagi “Android ilovasi → Pro” yo‘riqnomasi ko‘rinadi.

## Baho va mukofot

Savol: “Pro oynasi va do‘st taklif qilish shartlari tushunarlimi?” 1 — tushunarsiz, 5 — juda tushunarli.

Taklif oldidan: “Fikr qoldirsangiz, obunangiz bo‘lmasa sizga 24 soatlik 20% chegirma beriladi.” Mukofot yozilgach: “Rahmat. Aytganimizdek, sizga 24 soatlik 20% chegirma berildi.”

## Target va statistikalar

Target: Pro oynasini ochgan Android va Mini App bepul foydalanuvchilari, dastlab kichik test guruhi.

Kuzatish: Pro sahifasi ochilishi → tarif tanlash → chek yuborish; 20% taklif boshlanishi, Android/iOS taklif havolasi, `discount_referral_count` 0→3, chegirma ishlatilishi; feedback baholari va mukofotlar.
