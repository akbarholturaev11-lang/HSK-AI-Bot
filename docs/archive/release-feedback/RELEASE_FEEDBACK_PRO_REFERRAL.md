# Release feedback draft — Pro checkout va do‘st taklifi

Holat: draft. Deploy va ichki testdan keyin admin tasdiqlasa, mavjud Release feedback moduli orqali yuboriladi. Avtomatik jo‘natilmaydi.

## Release nomi

HSK AI Pro: soddaroq obuna va telefonga mos do‘st taklifi

## Userga yuboriladigan qisqa matn

Pro obuna oynasi soddalashdi: tariflar darhol ko‘rinadi, matn dars tilingizga mos. “Chegirmani ochish” tugmasi do‘st taklifini boshlaydi; havola yoki ulash oynasida Android va iPhone uchun kerakli qadamlar ko‘rsatiladi. Androidda do‘st taklifni botda qayd etadi, APK faylini shu chatdan oladi va o‘sha Telegram hisobini ilovaga ulaydi; iPhone’da botdagi 2 savol yo‘li ishlaydi.

## Nima yangilandi va qayerda sinash

Android ilovasini 1.6.15 ga yangilang yoki Telegram Mini App’ni oching → Pro → “Chegirmani ochish” tugmasini bosing. Ochilgan ulash oynasida Android/iPhone qadamlarini ko‘ring. Androidda taklifni botda qayd eting → bot chatidan APK faylini o‘rnating → ilovada o‘sha Telegram hisobini ulang. iPhone’da botdagi 2 savol yo‘lini tekshiring. Test hisoblarda haqiqiy ulanishdan keyin 20% hisoblagichi yangilanishini ko‘ring.

## “Sinab ko‘rish” tugmasi

Mavjud modulda `Obuna/Chegirma` yo‘nalishini tanlang: u Pro Mini App oynasini ochadi. Foydalanuvchi “Chegirmani ochish” orqali Android/iPhone yo‘riqnomasini ko‘radi va ulashni boshlaydi.

## Baho va mukofot

Savol: “Pro oynasi va do‘st taklif qilish shartlari tushunarlimi?” 1 — tushunarsiz, 5 — juda tushunarli.

Taklif oldidan: “Fikr qoldirsangiz, obunangiz bo‘lmasa sizga 24 soatlik 20% chegirma beriladi.” Mukofot yozilgach: “Rahmat. Aytganimizdek, sizga 24 soatlik 20% chegirma berildi.”

## Target va statistikalar

Target: Pro oynasini ochgan Android va Mini App bepul foydalanuvchilari, dastlab kichik test guruhi.

Kuzatish: Pro sahifasi ochilishi → tarif tanlash → chek yuborish; 20% taklif boshlanishi, Android/iOS taklif havolasi, `discount_referral_count` 0→3, chegirma ishlatilishi; feedback baholari va mukofotlar.
