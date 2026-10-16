# Release feedback draft — HSK AI bilan ilk qadam

Holat: DRAFT. Yuborilmagan. Deploy va admin tasdig'idan keyin mavjud
`Release feedback` moduli orqali yuboriladi.

## Release nomi

HSK AI bilan ilk qadam — yangi onboarding

## Qisqa e'lon

> HSK AI'ga kirish ekrani yangilandi. Li ustoz bilan darajangiz va maqsadingizni
> tanlang, keyin birinchi darsni boshlang. Katta tanlovlar va aniq progress
> boshlashni osonlashtiradi.
>
> Baho va izoh qoldirsangiz, faol obunangiz bo'lmasa, obuna uchun 24 soatlik
> 20% chegirma beriladi.

## Nima yangilandi

- Daftar va qalam ushlagan HSK AI pandasi, suhbat pufagi va botning qizil/krem ranglari.
- Panda salomlashuvi, tanlovda tabassum va bosh qimirlatish, ekran almashuvi,
  tugma bosilishi va tanlangan belgi effektlari. Reduced-motion sozlamasi hurmat qilinadi.
- Daraja va maqsad uchun yengil shriftli, 1px chegarali tanlov kartalari;
  qalin soyalar va takroriy izohlar qisqartirilgan, progress ixchamlashtirilgan.
- Telefonning xavfsiz chetlarini hisobga oladigan, doim ko'rinadigan CTA.
- Saqlash paytida takror bosish himoyasi, xato/12 soniyalik timeoutdan keyin retry.
- O'zbek, rus va tojik tillari. Mavjud 3 ekran va Starter 0 yo'nalishi saqlangan.

## Qayerda va qanday sinash

Yangi foydalanuvchi hisobida: bot → Kurs → Boshlash → daraja → maqsad →
Birinchi darsni boshlash. Orqaga qaytib, tanlov saqlanganini tekshiring.
Noldan boshlovchi uchun Starter 0 ochilishi kerak.

`Sinab ko'rish` tugmasi kursga olib borsin:
`course-v3.html?tab=course&source=release_onboarding_ui`.
Yangi userga onboarding mavjud kirish tekshiruvi orqali avtomatik ochiladi.
Tugma parametr qabul qilmasa: «Botdagi Kurs tugmasini bosing» instruktsiyasi.
Mavjud o'quvchining progressini yoki onboarding holatini qayta boshlamang.

## Target segment

Deploydan keyin yangi onboardingdan o'tgan yangi foydalanuvchilar.
Avvaldan kurs o'qiyotganlar bu onboarding sinoviga kiritilmaydi.

## 1–5 baholash matni

> Kursni boshlash qanchalik tushunarli bo'ldi? 1 — juda chalkash, 5 — juda oson.
> Qaysi joyni yaxshilashimiz kerak?

## Reward tasdig'i

Chegirma haqiqatan berilganidan keyin:
> Rahmat! Aytganimizdek, sizga obuna uchun 24 soatlik 20% chegirma berildi.

Faol obunachiga mavjud moduldagi oddiy rahmat matni yuboriladi.

## Kuzatiladigan metrikalar

- `onboarding_started` → `onboarding_completed` konversiyasi.
- Onboarding → birinchi dars boshlanishi ≤2 daqiqa.
- Beginner → Foundation boshlanishi va tugatilishi.
- Birinchi bo'lim ≤15 daqiqa, birinchi dars ≤24 soat.
- D1 qaytish, feedback baholari va tushunarsiz joylar haqidagi izohlar.
