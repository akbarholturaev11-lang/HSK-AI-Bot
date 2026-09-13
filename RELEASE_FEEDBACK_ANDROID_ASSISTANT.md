# Release feedback draft — Android HSK AI yordamchi

Holat: **DRAFT. Avtomatik YUBORILMAYDI.** Deploy va real qurilma sinovidan
keyin admin tasdiqlasagina mavjud `Release feedback` moduli orqali yuboriladi.

## Release nomi

**HSK AI yordamchi — ilova ichida "mana buni tushuntir"**

## Userga yuboriladigan qisqa matn

> HSK AI Android ilovasiga yangi yordamchi qo'shildi.
>
> Endi dars, lug'at, mashq yoki reyting ichida pastdagi **AI** tugmasini
> bossangiz, chat aynan ochiq turgan ekraningizdagi materialni tushunadi.
>
> Matn yozing, ovoz bilan so'rang yoki rasm yuboring. Imtihon va bellashuv
> paytida AI javobni aytib bermaydi, lekin qanday foydalanishni tushuntiradi;
> yakundan keyin xatolarni tahlil qiladi.

## Aynan nima yangilandi

1. Har asosiy Android bo'limida doimiy **AI** tugmasi.
2. 80% balandlikda ochiladigan chat, kerak bo'lsa to'liq ekran.
3. Dars kartasi, lug'at so'zi, talaffuz, xatolar va reyting holatidan aniq
   kontekst oladigan yordamchi.
4. Matn, ovozli savol va rasm yuborish.
5. Internet uzilsa qayta tiklanadigan, bir marta hisoblanadigan yuborish.
6. Bot QA bilan umumiy limitlar, lekin Android chat tarixi alohida.
7. Imtihon/bellashuv davomida javobni ochib bermaydigan server nazorati.

## User qayerda sinashi kerak

1. Android ilovasida **Mashq → Ieroglif lug'ati**ni oching.
2. Bir so'zga kiring va pastdagi **AI** tugmasini bosing.
3. "Buni soddaroq tushuntir" deb yozing.
4. **Talaffuz mashqi** yoki **Ieroglif tanish**ga o'tib, AI chatni ochib
   yopib ko'ring: eski natija yangi mashqqa ko'chmasligi kerak.
5. Reytingdagi bir user profilini ochib, "farqim qancha?" deb so'rang.

## `Sinab ko'rish` tugmasi

Tugma Android ilovasida **Mashq** bo'limini ochsin:
`pomp-hsk-ai://practice`

Agar deep link ochilmasa, matnda: "Android ilovasida Mashq bo'limiga o'ting va
pastdagi AI tugmasini bosing."

## Baholash matni

> AI yordamchi sizga dars yoki mashqni tushunishda yordam berdimi?
> 1 — foydasiz, 5 — juda foydali.

## Reward — oldindan aytiladi

> Baho va qisqa izoh qoldirsangiz, obunaga **20% chegirma** beramiz.

Bahodan keyingi tasdiq matni:

> Rahmat! Aytganimizdek, sizga 20% chegirma berildi — obuna bo'limida ko'rasiz.

## Target segment

- Android ilovasini oxirgi 14 kunda ochgan foydalanuvchilar.
- Kamida 1 ta dars yoki mashq boshlaganlar.
- Birinchi bosqichda test segment: admin/test accountlar va faol Android
  foydalanuvchilarning kichik guruhi.

## Statsda kuzatiladigan metrikalar

| Metrika | Nega |
|---|---|
| `android_assistant_opened` | Tugma topilyaptimi |
| `android_assistant_message_sent` turi bo'yicha | Matn/ovoz/rasm qaysi biri ishlatilmoqda |
| Javob vaqti p50/p95 | Chat sekinlashmayaptimi |
| `assistant_timeout` / provider error | AI barqarorligi |
| Chatdan darsga qaytish | AI dars oqimini uzmayaptimi |
| Assessment paytidagi bloklangan yechimlar | Imtihon cheklovi ishlayaptimi |
| Limit sarfi va AI cost | Xarajat nazoratdami |

## Yuborishdan oldin tekshirilsin

- [ ] Backend deployda `alembic upgrade head` muvaffaqiyatli o'tdi.
- [ ] Android `test lint assembleDebug` o'tdi.
- [ ] Real qurilma yoki emulatorda matn yuborish ishladi.
- [ ] Foto tanlash, preview va yuborish ishladi.
- [ ] Mikrofon ruxsati berilgan/rad qilingan holatlar tekshirildi.
- [ ] Imtihon/bellashuv davomida AI yechim bermadi.
- [ ] Talaffuz -> ieroglif tanish -> AI -> yopish oqimida eski natija ko'chmadi.
- [ ] UZ/RU/TJ matnlar joyida.
