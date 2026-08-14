# Release feedback draft — sales_value_v1

> **Status: QORALAMA.** Hech kimga yuborilmagan. A/B test davomida yuborilmaydi;
> faqat g‘olib 100% rollout qilingach admin tasdiqlasa mavjud `Release feedback`
> moduli orqali yuboriladi.

## Release nomi

**HSK yo‘lingiz — birinchi real natijadan keyingi aniq qadam**

## Foydalanuvchiga qisqa matn

| Til | Matn |
|---|---|
| UZ | Birinchi xitoycha dialogingizni tugatganingizdan keyin endi o‘rgangan natijalaringiz va navbatdagi HSK qadamingiz aniq ko‘rinadi. Kursni tartibli yo‘l bo‘yicha davom ettiring. |
| RU | После первого диалога на китайском вы увидите подтверждённый результат и следующий шаг к своей цели HSK. Продолжайте обучение по понятному маршруту. |
| TJ | Пас аз гуфтугӯи аввалини чинӣ натиҷаи омӯхтаатон ва қадами навбатӣ то ҳадафи HSK равшан нишон дода мешавад. Омӯзишро бо роҳи тартибнок идома диҳед. |

## Aynan nima yangilandi

- HSK1 birinchi checkpointdan keyin hanzi, pinyin va tarjima bilan natija ko‘prigi.
- Keyingi darsdan olinadigan real natija va bepul namuna oldindan ko‘rsatiladi.
- Premium taklifi feature ro‘yxati o‘rniga HSK maqsadigacha yo‘l, speaking tuzatishi va xatolarni qayta mashq qilishni tushuntiradi.
- Bepul namuna chegarasi kutilmagan blok emas, oldindan tushunarli yakun sifatida chiqadi.

## Qayerda sinash kerak

Telegram Mini App → **Kurs** → HSK1 Starter 0 → 1–3-qismlar → birinchi checkpoint.

`Sinab ko‘rish` tugmasi Course Mini Appni HSK1 joriy qismida ochishi kerak. Deep link
mavjud bo‘lmasa, yuqoridagi aniq yo‘l matni ko‘rsatiladi.

## 1–5 baholash matni

| Til | Matn |
|---|---|
| UZ | Yangi HSK yo‘li keyingi qadamingizni tushunishga yordam berdimi? 1 dan 5 gacha baholang. |
| RU | Новый маршрут HSK помог понять следующий шаг? Оцените от 1 до 5. |
| TJ | Роҳи нави HSK барои фаҳмидани қадами навбатӣ кумак кард? Аз 1 то 5 баҳо диҳед. |

## Feedback mukofoti — oldindan ko‘rsatiladigan matn

> Mukofot qiymati admin kampaniya yaratishda mavjud `Release feedback` sozlamasi
> bilan bir xil bo‘lishi shart. Tarif yoki chegirma bu relizda o‘zgartirilmaydi.

| Til | Matn |
|---|---|
| UZ | Baho va qisqa izoh qoldirsangiz, admin panelda ko‘rsatilgan feedback mukofotini olasiz. Mukofot turi va muddati baho berishdan oldin aniq ko‘rsatiladi. |
| RU | За оценку и короткий комментарий вы получите награду, указанную в панели feedback. Её вид и срок будут показаны до отправки оценки. |
| TJ | Барои баҳо ва шарҳи кӯтоҳ мукофоти дар панели feedback нишондодашударо мегиред. Навъ ва муҳлати он пеш аз баҳодиҳӣ равшан нишон дода мешавад. |

## Target segment

- Faqat `sales_value_v1` g‘olib varianti 100% rollout qilingach HSK1 checkpointni tugatgan foydalanuvchilar.
- A/B test davridagi control/treatment cohortlariga release xabari yuborilmaydi.
- Paid, pending payment va faol maxsus kampaniya foydalanuvchilari chiqariladi.
- Til: foydalanuvchi profili bo‘yicha UZ/RU/TJ.

## Statsda kuzatiladigan metriclar

- assigned → checkpoint → bridge → paywall → checkout → payment submitted → approved;
- 7 kun matured assigned user boshiga approved payment;
- assigned user boshiga tushum, currency bo‘yicha;
- Starter 0 va birinchi checkpoint completion;
- D1 meaningful return;
- payment rejection/pending va frontend xatolari;
- release xabar ochilishi, `Sinab ko‘rish`, 1–5 baho va izoh ulushi.

## Admin checklist

- [ ] Test kamida 14 kun va qaror minimumlariga yetgan.
- [ ] G‘olib 7 kun 90/10 bosqichidan xatosiz o‘tgan.
- [ ] Treatment 100% rollout qilingan.
- [ ] UZ/RU/TJ matnlari tekshirilgan.
- [ ] Feedback mukofoti va muddati matnda oldindan aniq ko‘rsatilgan.
- [ ] Admin yuborishni tasdiqlagan.

Admin rad etsa yoki javob bermasa, xabar yuborilmaydi.
