# Release feedback draft — «Bugungi reja»

Holat: **DRAFT. Avtomatik YUBORILMAYDI.** Deploydan va sinovdan keyin admin
tasdiqlasagina mavjud `Release feedback` moduli orqali yuboriladi.
Branch: `codex/local-ai` (Railway sinovi uchun). `main` ga chiqmagan.

---

## Release nomi

**Bugungi reja — ilova endi bugun nima qilishni aytadi**

## Userga yuboriladigan qisqa matn

> 🎯 **HSK AI yangilandi**
>
> Endi kursni ochganingizda ilova bugun aynan nima qilishni aytadi:
> davom etadigan qism, takrorlash kerak bo'lgan xatolar va sizga mos mashq.
>
> Reja kun davomida o'zgarmaydi — ertalab ko'rgan ro'yxatingiz kechqurun
> ham o'sha bo'lib qoladi.
>
> Yana: mashqlardagi xatolaringiz endi saqlanadi va «Xatolarim» bo'limiga
> tushadi, ya'ni takrorlash haqiqatan sizning zaif joyingizdan quriladi.

## Aynan nima yangilandi

1. **Kurs ekranida «Bugungi reja» tasmasi** — kunlik XP va 1-4 vazifa.
   Bajarilgani belgilanadi, qulflangani ochiq aytiladi.
2. **Onboarding maqsadni so'raydi** (HSK imtihoni / kundalik muloqot /
   sayohat / ish / o'qish). Maqsad reja tarkibini o'zgartiradi.
3. **Birinchi darsdan keyin** kunlik vaqt va "nimaga urg'u beraylik"
   so'raladi. Javob kunlik reja uzunligini belgilaydi.
4. **Kunlik XP maqsadi endi saqlanadi** — ilgari ilova qayta ochilganda
   tanlov yo'qolardi.
5. **Mashq natijalari saqlanadi**: talaffuz, ieroglif tanish va yodlash
   bo'limlaridagi xatolar «Xatolarim» ga tushadi.
6. **Mashq savollari faqat o'rganilgan darslardan** keladi (ilgari hali
   ochilmagan darslardan ham kelardi).
7. **Telegram Desktop / brauzerda** ilova ekran kengligidan foydalanadi:
   chapda kurs yo'lakchasi, o'ngda kunlik reja va seriya kalendari.

## User qayerda sinashi kerak

1. Kursni oching — tepada, progress chizig'i ostida **«Bugun …»** tasmasini
   ko'rasiz.
2. Tasmadagi **«Xatolar»** yoki **«Ieroglif»** chipini bosing — tegishli
   bo'lim ochilishi kerak.
3. Bitta qismni tugating — reja o'sha vazifani bajarilgan deb belgilaydi.
4. Talaffuz mashqida bitta so'zni ataylab noto'g'ri ayting, so'ng
   **Mashq → Xatolar** ni oching: o'sha so'z ro'yxatda bo'lishi kerak.
5. Kompyuterda Telegram orqali oching — o'ng tomonda reja ustuni chiqadi.

## «Sinab ko'rish» tugmasi

Tugma **kurs xaritasini** ochsin (reja tasmasi aynan o'sha ekranda):
`course-v3.html?tab=course&source=release_daily_plan`

Agar tugma parametr qabul qilmasa — matnda: «Kursni oching va tepadagi
"Bugun" qatoriga qarang».

## Baholash matni (1-5)

> Bugungi reja sizga foydali bo'ldimi? 1 — umuman yo'q, 5 — juda foydali.

## Reward — OLDINDAN aytiladi

> Baho va qisqa izoh qoldirsangiz, obunaga **20% chegirma** beramiz.

Bahodan keyingi tasdiq matni:

> Rahmat! Aytganimizdek, sizga 20% chegirma berildi — obuna bo'limida
> ko'rasiz.

## Target segment

- Kurs rejimidagi faol foydalanuvchilar (oxirgi 14 kunda kamida 1 dars).
- Bepul ham, obunachi ham — reja ikkalasiga ham ko'rinadi.
- Yangi ro'yxatdan o'tganlar CHIQARIB TASHLANSIN: ular hali reja
  ko'rmagan (birinchi darsdan keyin ko'rinadi).

## Statsda kuzatiladigan metrikalar

| Metrika | Nega |
|---|---|
| `miniapp_opened` → reja tasmasi bosilishi | reja umuman ishlatilyaptimi |
| Kunlik reja `done/total` o'rtachasi | reja bajarib bo'ladigan hajmdami |
| **Bepul userda reja `0/N` bilan tugagan kunlar ulushi** | «Qaror B» xavfi: reja "reklama ro'yxati"ga aylanmadimi |
| `mistake_review_started` soni | signal ulangach takrorlash o'sdimi |
| `course_mistakes` yangi yozuvlar manbasi bo'yicha (`pronunciation` / `recognition` / `memorize`) | mashq signali haqiqatan oqyaptimi |
| D1 / D7 retention | reja ushlab qolishga ta'sir qildimi |
| Obunaga o'tish (kurs ekranidan) | reja konversiyaga zarar qilmadimi |

## Yuborishdan oldin tekshirilsin

- [ ] Railway'da `alembic upgrade head` muvaffaqiyatli o'tdi (`0071`).
- [ ] Kurs ekranida reja tasmasi chiqdi (bepul va obunachi hisobda).
- [ ] Chiplar to'g'ri bo'limlarni ochdi.
- [ ] Talaffuz xatosi «Xatolarim» ga tushdi.
- [ ] Telegram Desktop'da ikki ustunli ko'rinish buzilmagan.
- [ ] Uch tilda (uz/ru/tj) matnlar joyida.
