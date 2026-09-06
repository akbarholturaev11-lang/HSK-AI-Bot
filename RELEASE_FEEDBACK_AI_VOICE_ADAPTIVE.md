# Release feedback draft — AI Voice sizga moslashadi

Holat: DRAFT. Yuborilmagan. Deploy va admin tasdig'idan keyin mavjud
`Release feedback` moduli orqali yuboriladi.

## Release nomi

AI Voice endi sizga moslashadi

## Qisqa e'lon

> AI Voice yangilandi. Endi suhbatdosh sizning maqsadingizni, zaif tomoningizni
> va takrorlash vaqti kelgan so'zlaringizni biladi — gap shu so'zlar atrofida
> tabiiy quriladi. Suhbat oxirida esa aniq natija ko'rasiz: qaysi xato
> grammatika, qaysi biri so'z tanlash edi va dars so'zlaridan nechtasini
> haqiqatan ishlatdingiz.
>
> Baho va izoh qoldirsangiz, faol obunangiz bo'lmasa, obuna uchun 24 soatlik
> 20% chegirma beriladi.

## Nima yangilandi

- Suhbat so'zlari endi tasodifiy emas: takrorlash jadvalingizdan (SRS) olinadi —
  Tanish/Yodlash mashqlari bilan bir xil manba.
- Suhbatdosh maqsadingizni hisobga oladi (sayohat, ish, o'qish, kundalik
  muloqot, HSK imtihoni) va eng ko'p qiladigan xato turingizni biladi.
- Ilgari qilgan bitta xatoingiz suhbatda tabiiy ravishda qaytadan sinaladi —
  "buni xato qilgansiz" deyilmaydi, shunchaki mavzu shunga olib keladi.
- Xatolar to'g'ri turga ajratiladi: grammatika / so'z / talaffuz. «Xatolarim»
  bo'limi va kunlik reja endi to'g'ri yo'naltiradi (grammatika xatosi uchun
  talaffuz mashqi emas, xatolar takrori beriladi).
- Suhbat yakunida uchinchi ko'rsatkich: dars so'zlaridan nechtasini
  ishlatganingiz. Xatolar turi bo'yicha ajratilgan holda ko'rsatiladi.
- «Nima deyish?» varag'i endi hozirgi savolga mos javoblarni taklif qiladi.
  Ilgari u yerda har doim bir xil 4 ta ibora turardi; endi panda nima
  so'raganiga qarab 2 ta tayyor javob chiqadi — bosing, klaviaturaga tushadi.
- «Bugun nechta suhbat qoldi» endi ko'rinadi (sozlamalar va yakun kartasida).
- Suhbat AI xatosi yoki mikrofon ruxsati sababli boshlanmasa — bepul kunlik
  suhbatingiz SARFLANMAYDI. Ilgari sarflanardi.
- Suhbat hisoblagichi va ekran yorliqlari sizning tilingizda (ilgari xitoycha
  `对话 3 / 7` chiqardi). O'zbek, rus va tojik tillari.
- Tuzatish matni suhbat pufagidan chiqib ketadigan chizilish xatosi tuzatildi.
- Kunlik reja HSK imtihoni uchun 李老师 ni tanlagan bo'lsa, suhbat aynan u
  bilan boshlanadi (ilgari doim 阿宝 ochilardi).

## Qayerda va qanday sinash

Mini App → pastdagi mikrofon tugmasi → «Suhbatni boshlash». Klaviatura yoki
mikrofon orqali 2-3 marta javob bering, keyin ✕ bosib yakuniy kartani ko'ring.

Tekshirish kerak:
- yakundagi uchta ko'rsatkich va xatolar turi bo'yicha ajratma;
- «Nima deyish?» — takliflar har javobdan keyin o'zgarishi;
- sozlamalar (⚙) ichida «Bugun qoldi» qatori;
- suhbatdagi tuzatish matni pufak ichida to'liq ko'rinishi;
- «Bugungi reja» dagi suhbat vazifasidan kirilganda suhbatdosh nomi.

`Sinab ko'rish` tugmasi:
`course-v3.html?tab=voice&source=release_voice_adaptive`.
Tugma parametr qabul qilmasa: «Mini App'ni oching va pastdagi mikrofon
tugmasini bosing» instruktsiyasi.

## Target segment

Deploydan keyin kamida bitta AI Voice suhbati qilgan foydalanuvchilar
(bepul va obunachi). Hech qachon voice ishlatmaganlarga yuborilmaydi.

## 1–5 baholash matni

> Suhbatdosh sizning darajangiz va so'zlaringizga qanchalik mos gapirdi?
> 1 — umuman mos emas, 5 — juda mos. Nimani yaxshilashimiz kerak?

## Reward tasdig'i

Chegirma haqiqatan berilganidan keyin:
> Rahmat! Aytganimizdek, sizga obuna uchun 24 soatlik 20% chegirma berildi.

Faol obunachiga mavjud moduldagi oddiy rahmat matni yuboriladi.

## Kuzatiladigan metrikalar

- `voice_started` → `voice_completed` konversiyasi (deploydan oldin/keyin).
- O'rtacha `turn_count` va 7 ta navbatgacha yetgan sessiyalar ulushi.
- `target_used.used / total` — dars so'zlaridan foydalanish o'sdimi.
- `course_mistakes` da voice manbali `grammar` / `word` ulushi (ilgari 100%
  `pronunciation` edi) va `mistake_review` vazifasi berilish chastotasi.
- Bepul o'quvchilarda: boshlangan lekin gapirilmagan sessiyalar soni —
  bu endi limitni yoqmaydi, shuning uchun AI xarajati o'smasligi kerak.
- `voice_practice_transcribe` / `voice_practice_reply` AIUsageEvent xarajati:
  prompt uzayganiga qaramay sessiya narxi sezilarli o'smasligi kerak.
- Voice limitidan paywall'ga o'tish (`v3_voice_limit`) konversiyasi.

## Deploy oldidan

1. `alembic upgrade head` — `0074_voice_session_plan` (`plan_json` ustuni).
   Eski qatorlar `{}` oladi va moslashuvsiz eski prompt bilan ishlaydi.
2. Rollback kerak bo'lsa: `plan_json` ni `{}` ga qaytarish kifoya — prompt
   avtomatik ravishda o'zgarishdan oldingi holatiga qaytadi.
