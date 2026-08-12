# Release feedback draft — Desktop 1.4.0

> **Status: QORALAMA.** AI_RULES.md (66–97-qatorlar) talabiga ko'ra tayyorlandi.
> Hech kimga yuborilmagan. Admin tasdiqlamaguncha yuborilmaydi.
> Yuborish uchun Telegram admin `Release feedback` moduli ishlatiladi.

Reliz: `desktop-v1.4.0` · Oldingi reliz: `desktop-v1.3.8`
Commitlar: `a2d077af` … `b0ac98ed`

---

## 1. Release title

| Til | Matn |
|---|---|
| UZ | HSK AI Desktop 1.4.0 — bildirishnomalar va yangilangan interfeys |
| RU | HSK AI Desktop 1.4.0 — уведомления и обновлённый интерфейс |
| TJ | HSK AI Desktop 1.4.0 — огоҳиномаҳо ва интерфейси навшуда |

---

## 2. Foydalanuvchiga e'lon matni

**UZ**
> HSK AI Desktop 1.4.0 chiqdi. Endi ilova sizga eslatma yuboradi — darsni o'tkazib yubormaysiz. Bildirishnomalarni Profil bo'limidan yoqasiz yoki o'chirasiz. Reyting ekrani internet uzilganda ham sizning natijangizni ko'rsatadi. Interfeys yangilandi va do'stlarni taklif qilish osonlashdi.

**RU**
> Вышел HSK AI Desktop 1.4.0. Теперь приложение напоминает об уроке — вы ничего не пропустите. Уведомления включаются и отключаются в разделе «Профиль». Экран рейтинга показывает ваш результат даже при проблемах с соединением. Интерфейс обновлён, приглашать друзей стало проще.

**TJ**
> HSK AI Desktop 1.4.0 баромад. Акнун барнома ба шумо хотиррасон мекунад — дарсро аз даст намедиҳед. Огоҳиномаҳоро аз бахши «Профил» фаъол ё хомӯш мекунед. Экрани рейтинг натиҷаи шуморо ҳатто ҳангоми мушкилии интернет нишон медиҳад. Интерфейс нав шуд ва даъвати дӯстон осонтар гардид.

---

## 3. Nima o'zgardi

| # | O'zgarish | Kim ko'radi | Fayl |
|---|---|---|---|
| 1 | **Desktop bildirishnomalari** — bildirishnoma markazi, ruxsat so'rash, umumiy yoqish/o'chirish tugmasi, o'qilmaganlar soni | Desktop foydalanuvchilari | `desktop_set_notifications` (lib.rs), `POST /api/v3/desktop/preferences/notifications` |
| 2 | **Panda mascot** — darslarda animatsiyali panda, reaksiyalar bilan | Desktop foydalanuvchilari | `desktop/ui/js/mascot.js` |
| 3 | **Reyting fallback** — leaderboard so'rovi yiqilsa, ekran bo'sh qolmaydi; serverda saqlangan shaxsiy natija ko'rsatiladi | Desktop foydalanuvchilari | `app/api/desktop_rating.py`, `app/js/app.js` |
| 4 | **Do'st taklif qilish** — havolani ulashish va nusxalash tugmasi, xavfsiz tashqi havola ochish | Desktop foydalanuvchilari | `desktop_open_external_url` (lib.rs) |
| 5 | **Dars reklamasi orqali kirish** — obunasiz foydalanuvchi qisqa reklamani oxirigacha ko'rib darsni ochadi | Mini App foydalanuvchilari | `app/static/course-v3.html`, `ads.js` |
| 6 | **Yuklab olish sahifasi** — o'rnatish qo'llanmasi va yangilangan UI | Web (yuklab olish sahifasi) | `desktop_download_service.py` |
| 7 | **Admin promo paneli** — desktop ilova promosini boshqarish (yoqish, kunlik limit, media) | Faqat admin | `desktop_app_promo_settings_service.py` |

**Foydalanuvchiga e'lon qilinadigan:** 1–5.
**E'lon qilinmaydigan:** 6 (web sahifa), 7 (ichki admin vositasi).

---

## 4. Foydalanuvchi qayerda va qanday sinaydi

| # | Funksiya | Sinash yo'li |
|---|---|---|
| 1 | Bildirishnomalar | Desktop ilova → **Profil** → bildirishnomalar bo'limi → yoqish → tizim ruxsatini berish → ilovani yopmasdan kuting |
| 2 | Panda mascot | Istalgan darsni ochish → javob berish → panda reaksiyasini ko'rish |
| 3 | Reyting fallback | Desktop ilova → **Reyting** → internetni uzib qayta kiring → shaxsiy natija ko'rinishi kerak |
| 4 | Do'st taklif qilish | **Profil** → taklif havolasi → ulashish yoki nusxalash |
| 5 | Dars reklamasi | Telegram Mini App → yopiq darsni ochish → "Reklamani ko'rish" → oxirigacha ko'rish → dars ochilishi kerak |

---

## 5. `Sinab ko'rish` action

**Asosiy:** desktop ilovani 1.4.0 ga yangilash → **Profil** bo'limini ochish (bildirishnomalar shu yerda).

Deep link: `pomp-hsk://profile`

**Fallback (deep link ishlamasa):**

| Til | Matn |
|---|---|
| UZ | Ilovani yangilang, so'ng pastdagi menyudan **Profil** bo'limini oching va bildirishnomalarni yoqing. |
| RU | Обновите приложение, затем откройте раздел **Профиль** в нижнем меню и включите уведомления. |
| TJ | Барномаро нав кунед, сипас аз менюи поён бахши **Профил**-ро кушоед ва огоҳиномаҳоро фаъол созед. |

**Yangilanish o'zi:** ilovada avtomatik updater bor, banner chiqadi. Qo'lda yuklab olish — yuklab olish sahifasi orqali.

---

## 6. Target segment

**Asosiy segment:** desktop ilovani o'rnatgan va oxirgi 30 kunda kamida 1 marta dars bajargan foydalanuvchilar.

**Ikkilamchi segment:** desktop o'rnatgan, lekin oxirgi 14 kunda faol bo'lmagan foydalanuvchilar — bildirishnoma xabari aynan ularni qaytarish uchun mos.

**Chiqarib tashlanadi:**
- desktop o'rnatmagan foydalanuvchilar (ular uchun bu reliz ko'rinmaydi)
- oxirgi 7 kunda boshqa reliz feedback so'rovi yuborilganlar (charchatmaslik uchun)

**Til:** har bir foydalanuvchining profildagi tiliga qarab (uz / ru / tj).

---

## 7. Rating prompt

| Til | Matn |
|---|---|
| UZ | Yangi versiyani sinab ko'rdingizmi? 1 dan 5 gacha baho bering — bu bizga qaysi tomonni yaxshilashni ko'rsatadi. |
| RU | Успели попробовать новую версию? Поставьте оценку от 1 до 5 — так мы поймём, что улучшить. |
| TJ | Версияи навро санҷидед? Аз 1 то 5 баҳо диҳед — ин ба мо нишон медиҳад, ки чиро беҳтар кунем. |

**Izohli savol (baho berilgandan keyin, ixtiyoriy):**

| Til | Matn |
|---|---|
| UZ | Nima yetishmadi yoki nima yoqdi? Bir-ikki jumla yozsangiz ham yetarli. |
| RU | Чего не хватило или что понравилось? Достаточно пары предложений. |
| TJ | Чӣ намерасид ё чӣ маъқул шуд? Ду-се ҷумла кифоя аст. |

---

## 8. Mukofot matni (baho so'rashdan OLDIN ko'rsatiladi)

> ⚠️ AI_RULES.md 95-qatori: mukofot **baho/izoh yig'ishdan oldin** oshkor qilinishi shart.

| Til | Matn |
|---|---|
| UZ | Baho va qisqa izoh qoldirganingiz uchun **obunaga 20% chegirma** beramiz. Chegirma promokodi baho berganingizdan so'ng darrov chiqadi va 7 kun amal qiladi. |
| RU | За оценку и короткий комментарий дарим **скидку 20% на подписку**. Промокод появится сразу после оценки и действует 7 дней. |
| TJ | Барои баҳо ва шарҳи кӯтоҳ ба шумо **20% тахфиф барои обуна** медиҳем. Промокод фавран пас аз баҳодиҳӣ пайдо мешавад ва 7 рӯз эътибор дорад. |

**Admin diqqatiga:** chegirma foizi va amal qilish muddati mavjud chegirma modulidagi sozlamaga mos bo'lishi kerak. Yuborishdan oldin tekshiring — bu qoralamada 20% / 7 kun **taxminiy** qiymat sifatida yozilgan.

---

## 9. Mukofot berilgandan keyingi tasdiq matni

| Til | Matn |
|---|---|
| UZ | Rahmat! Chegirma promokodingiz tayyor: `{promo_code}` — 7 kun ichida ishlatishingiz mumkin. Fikringiz keyingi yangilanishga kiritiladi. |
| RU | Спасибо! Ваш промокод на скидку готов: `{promo_code}` — можно использовать в течение 7 дней. Ваш отзыв учтём в следующем обновлении. |
| TJ | Ташаккур! Промокоди тахфифи шумо тайёр аст: `{promo_code}` — дар давоми 7 рӯз истифода бурда метавонед. Фикри шумо дар навсозии оянда ба назар гирифта мешавад. |

---

## 10. Kuzatiladigan statistika

**Reliz sog'ligi (birinchi 48 soat):**

| Ko'rsatkich | Nima anglatadi | Xavf signali |
|---|---|---|
| 1.4.0 ga yangilanganlar ulushi | Updater ishlayaptimi | 24 soatda < 30% |
| Ilova ishga tushishida xatolik (crash) | Reliz buzmadimi | 1.3.8 ga nisbatan o'sish |
| Yuklab olish → o'rnatish konversiyasi | Yangi sahifa ishlayaptimi | Oldingi haftaga nisbatan pasayish |

**Yangi funksiyalar:**

| Ko'rsatkich | Nima anglatadi | Kutilgan |
|---|---|---|
| Bildirishnomani yoqganlar ulushi | Funksiya kerakmi | Yangilanganlarning ≥ 25% |
| Tizim ruxsatini bergani (`granted`) | Ruxsat oqimi tushunarlimi | Yoqganlarning ≥ 70% |
| Bildirishnomadan keyin darsga qaytish | Asosiy maqsad — retention | Kuzatib boriladi |
| Reyting ekranida xatolik ko'rsatilishi | Fallback qanchalik ishlayapti | Past bo'lishi kerak |
| Reklama ko'rib dars ochganlar soni | Reklama gate ishlayaptimi | Kuzatib boriladi |
| Reklama boshlandi → oxirigacha ko'rildi | Reklama tugatilyaptimi | ≥ 60% |

**Feedback kampaniyasi:**

| Ko'rsatkich | Kutilgan |
|---|---|
| Xabar yetkazildi / ochildi | — |
| `Sinab ko'rish` bosilgani | ≥ 20% |
| Baho berilgani | ≥ 10% |
| O'rtacha baho | ≥ 4.0 |
| Promokod ishlatilgani | Kuzatib boriladi |
| Chiqib ketish / blok | ≤ 1% — oshsa kampaniyani to'xtatish |

---

## Yuborishdan oldingi tekshiruv ro'yxati

- [ ] `desktop-v1.4.0` relizi GitHub Actions'da muvaffaqiyatli tugagan
- [ ] macOS va Windows build'lari yuklab olinib, o'rnatilib sinalgan
- [ ] Yangilanish banneri 1.3.8 dan 1.4.0 ga o'tishda ishlayotgani tekshirilgan
- [ ] Bildirishnoma ruxsati macOS va Windows'da ikkalasida ham sinalgan
- [ ] Chegirma foizi (20%) va muddati (7 kun) chegirma moduli sozlamasiga mos
- [ ] Uch tildagi matnlar (uz/ru/tj) admin tomonidan o'qib chiqilgan
- [ ] Segment hajmi tekshirilgan
- [ ] **Admin yuborishga ruxsat bergan**

> Admin ruxsat bermasa — yuborilmaydi.
