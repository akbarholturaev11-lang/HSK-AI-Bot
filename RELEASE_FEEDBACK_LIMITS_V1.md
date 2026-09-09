# Release feedback draft — limits_v1

> **Status: QORALAMA.** Hech kimga yuborilmagan. Avval admin panelda bepul
> chegaralar tasdiqlanadi (ayniqsa `lesson.start` oynasi — pastdagi checklistga
> qarang), keyin mavjud `Release feedback` moduli orqali yuboriladi.

## Release nomi

**Limitlar endi rost gapiradi — va har kuni yangilanadi**

## Foydalanuvchiga qisqa matn

| Til | Matn |
|---|---|
| UZ | Bepul chegaralar endi hamma joyda bir xil: botda, Mini Appda, Android ilovada va kompyuterda. Ekranda ko‘rsatilgan raqam — aynan amal qiladigan raqam, va u har kuni yangilanadi. |
| RU | Бесплатные лимиты теперь одинаковы везде: в боте, Mini App, Android-приложении и на компьютере. Число на экране — именно то, которое действует, и оно обновляется каждый день. |
| TJ | Маҳдудиятҳои ройгон акнун дар ҳама ҷо як хеланд: дар бот, Mini App, барномаи Android ва компютер. Рақами дар экран — ҳамон рақаме, ки амал мекунад ва ҳар рӯз нав мешавад. |

## Aynan nima yangilandi

- Dars, mashq, AI va speaking chegaralari yagona joydan — admin panelidagi
  «Limitlar» bo‘limidan boshqariladi. Bot, Mini App, Android va kompyuter
  bitta hisobni o‘qiydi: bir joyda ishlatilgan chegara boshqasida qaytmaydi.
- Chegara tugaganda chiqadigan matn serverdan keladi: «Bepul rejimda kuniga 5 ta
  dars. Qoldi: 0» — raqam ilovaga yozib qo‘yilgan emas, adminning sozlamasi.
- Xaritadagi bitta qism = bitta dars. Ochilgan darsni qayta ochish yoki tugatish
  ikkinchi marta chegaradan yemaydi; tugatilgan dars doim qayta ochiladi.
- Yarim dars ko‘rsatish va reklama bilan dars ochish olib tashlandi: dars yo
  to‘liq ochiq, yo yopiq.
- Mini App yoki kompyuterda chegara tugasa botga xabar KELMAYDI — chegara
  ekranning o‘zida ko‘rsatiladi. Telegram xabari faqat Android ilovada
  ishlatilganda keladi.

## Qayerda sinash kerak

Telegram Mini App → **Kurs** → joriy qismni oching va bugungi chegara tugaguncha
darslarni tugating. Chegara oynasidagi matn adminda qo‘yilgan raqam bilan bir xil
bo‘lishi kerak.

`Sinab ko‘rish` tugmasi Course Mini Appni joriy qismda ochishi kerak. Deep link
ishlamasa, yuqoridagi yo‘l matni ko‘rsatiladi.

## 1–5 baholash matni

| Til | Matn |
|---|---|
| UZ | Bepul chegara qancha qolganini tushunish oson bo‘ldimi? 1 dan 5 gacha baholang. |
| RU | Стало ли понятнее, сколько бесплатного лимита осталось? Оцените от 1 до 5. |
| TJ | Фаҳмидани он ки чӣ қадар маҳдудияти ройгон боқӣ мондааст, осонтар шуд? Аз 1 то 5 баҳо диҳед. |

## Feedback mukofoti — oldindan ko‘rsatiladigan matn

> Mukofot qiymati admin kampaniya yaratishda mavjud `Release feedback`
> sozlamasi bilan bir xil bo‘lishi shart. Tarif bu relizda o‘zgartirilmaydi.

| Til | Matn |
|---|---|
| UZ | Baho va qisqa izoh qoldirsangiz, admin panelda ko‘rsatilgan feedback mukofotini olasiz. Mukofot turi va muddati baho berishdan oldin aniq ko‘rsatiladi. |
| RU | За оценку и короткий комментарий вы получите награду, указанную в панели feedback. Её вид и срок будут показаны до отправки оценки. |
| TJ | Барои баҳо ва шарҳи кӯтоҳ мукофоти дар панели feedback нишондодашударо мегиред. Навъ ва муҳлати он пеш аз баҳодиҳӣ равшан нишон дода мешавад. |

## Mukofot berilgandan keyingi matn

| Til | Matn |
|---|---|
| UZ | Rahmat. Mukofotingiz hisobingizga qo‘shildi — profil bo‘limida ko‘rinadi. |
| RU | Спасибо. Награда зачислена — она видна в разделе профиля. |
| TJ | Ташаккур. Мукофот ба ҳисоби шумо илова шуд — дар бахши профил дида мешавад. |

## Target segment

- Bepul va trial foydalanuvchilar (chegara faqat ularga tegishli).
- Obunachilar chiqariladi: ularda chegara yo‘q, xabar ular uchun ma’nosiz.
- Bloklangan va to‘lovi ko‘rib chiqilayotgan foydalanuvchilar chiqariladi.
- Til: foydalanuvchi profili bo‘yicha UZ/RU/TJ.

## Statsda kuzatiladigan metriclar

- Chegaraga urilish soni: dars, AI matn, AI foto, AI ovoz, speaking bo‘yicha alohida;
- chegaraga urilgandan keyin paywall ochilishi → checkout → to‘lov yuborilishi → tasdiqlanishi;
- kunlik faol bepul foydalanuvchi boshiga tugatilgan darslar soni (oyna kunlik
  bo‘lgani uchun bu raqam o‘sishi kutiladi);
- bepul foydalanuvchidan tushum: chegara kunlik bo‘lgani obunani kechiktirmayaptimi;
- Android’dan yuborilgan chegara xabarlari soni (Mini App’dan 0 bo‘lishi shart);
- `/api/v3/lesson/start` va `/api/v3/limits/status` xatolik ulushi.

## Admin checklist

1. **Avval qaror:** «Limitlar» → FREE → `Dars boshlash` oynasi **Kunlik** yoki
   **Umrbod**? Bugungi default — kuniga 2. Ilgarigi xatti-harakat (darajaning
   birinchi N qismi, umrbod) uchun **Umrbod** tanlanadi. Bu daromadga tegadi.
2. AI matn chegarasini tekshiring: ilgari Gemini yoqilganda cheksiz edi, endi
   default kuniga 5. Cheksiz kerak bo‘lsa `Cheksiz` katakchasini belgilang.
3. Har bir chegarani saqlab, Mini Appda va Android’da matn aynan shu raqamni
   ko‘rsatayotganini ko‘ring.
4. Mini App’da chegarani tugatib, botga xabar KELMAGANIGA ishonch hosil qiling.
5. Shundan keyingina release feedbackni yuborishga ruxsat bering.
