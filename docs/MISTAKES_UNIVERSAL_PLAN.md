# Xatolarim — universal takror (reja)

Holat: 2026-09-28 da boshlandi. Branch: `codex/mistakes-universal`
(`codex/local-ai` dan). `main` ga push faqat to'liq tekshiruvdan keyin.

## Muammo (kodda tasdiqlangan)

1. AI Voice xatosida savol ham, "sizning javobingiz" ham o'quvchining noto'g'ri
   gapi — review uni variantga qo'shadi (savol matni = variant), ko'rsatma yo'q.
2. Mashq bo'limi tinglash savolida `sentence = audio_text` — javob ekranda yozilib turadi.
3. Tinglash savolida ovoz o'zi chalinmaydi; Mini App darsdagi TTS blob-kesh yo'lini ishlatmaydi.
4. `match_pairs`, talaffuz, eski materialsiz xatolar, `sentence_builder` (100%) va
   `reverse_builder` (84%) review'ga hech qachon chiqmaydi, lekin sanoqda turaveradi.
5. Faqat eng zaif 30 ta xato ko'riladi; hammasi yaroqsiz bo'lsa "Boshlash" sahifani qayta yuklaydi.
6. Android DTO'da `format`/`tokens` yo'q — builder savol variantsiz chiqadi.
7. Bitta to'g'ri javob xatoni yopadi (o'sha shakl, o'sha variantlar).
8. Kategoriya bo'yicha takror yo'q.

## Yechim g'oyasi

**Savol emas, "nishon" takrorlanadi.** Nishon — o'quvchi bilmagan narsa:

| Tur | Kalit | Qayerdan |
|---|---|---|
| `word` | lug'at so'zi (`你`) | ieroglif/ma'no/pinyin/tinglash/juftlik/drill xatolari |
| `sentence` | to'g'ri xitoycha gap | bo'sh joy, dialog, gap tuzish, AI Voice tuzatishi, imtihon gapi |
| `question` | eski savolning o'zi | faqat nishon ajratib bo'lmagan kamdan-kam holat (1 format) |

Server har safar nishondan **yangi, tekshirilgan** savol yasaydi — eski buzuq
snapshot qayta o'ynatilmaydi.

### Mashq zinapoyasi (kategoriya bo'yicha)

| Kategoriya | Mashqlar (kamida 3 tasi olinadi) |
|---|---|
| So'zlar | `meaning_choice` · `hanzi_choice` · `listening_choice` · `pinyin_choice` |
| Ieroglif | `hanzi_from_pinyin` · `pinyin_choice` · `hanzi_choice` · `listening_choice` |
| Talaffuz | `listening_choice` · `listening_pinyin` · `pinyin_choice` · `meaning_choice` |
| Grammatika (gap) | `gap_fill`/`dialog_choice` (muallif variantlari) · `correct_choice` (o'z xato gapi) · `sentence_builder` · `sentence_meaning` · `sentence_listening` · `listen_builder` |

### Yopilish qoidasi

- Nishon **3 xil** mashqda to'g'ri javob berilganda yopiladi
  (mavjud format 3 tadan kam bo'lsa — hammasi).
- Xato javob progressni nolga tushiradi; nishon keyingi sessiyada qaytadi.
- Yopilganda unga bog'langan `course_mistakes` qatorlari `resolved` bo'ladi
  (LearningSignals / kunlik reja / voice konteksti izchil qoladi).
- Yangi xato yopilgan nishonni qayta ochadi.
- So'z nishoni yopilganda mavjud interval takroriga (`course_word_mastery`) beriladi.

### "Bagsiz" kafolati — universal tekshirgich

Har savol klientga ketishidan oldin:
- savol matni hech bir variantga teng emas;
- tinglash savolida ovoz bor, ekranda javobni ochadigan gap/pinyin yo'q;
- ko'rinadigan matnda to'g'ri javob yozilmagan;
- variantlar takrorlanmaydi, to'g'ri javob aynan bitta, distraktor ma'nosi/o'qilishi
  to'g'ri javob bilan bir xil emas (omofon/sinonim himoyasi);
- builder: bo'laklar = javob bo'laklari, aralashtirilgan tartib javobga teng emas;
- ko'rsatma uchala tilda;
- klient chiza olmaydigan format berilmaydi (`formats` ro'yxati; eski klient = faqat variantli).

Test: lug'atdagi **har so'z × har format × 3 til** va gap havzasidagi
**har gap × har format** shu tekshirgichdan o'tadi.

## Bosqichlar

0. [x] GitHub bilan solishtirish, worktree, reja.
1. [x] **Ma'lumot qatlami** — `course_mistake_targets` jadvali, `course_mistakes.target_key`,
   Alembic `0091`, model testlari.
2. [x] **Drill banki** — lug'at indeksi, gap havzasi, segmentatsiya (kesh).
3. [x] **Nishon aniqlovchi** — barcha manbalardan nishon; dars/imtihon kartalari bo'yicha qamrov testi.
4. [x] **Mashq generatori + tekshirgich** — formatlar, 3 tilda ko'rsatma, xususiyat testi.
5. [x] **Sessiya dvigateli (v3)** — `record_items` nishon yozadi, lazy backfill, `overview.targets`,
   `start_review(category, formats)`, aralashtirish, `complete_review` v3; v1/v2 sessiyalar tugatiladi.
6. [x] **API** — Mini App va Android endpointlari `category`/`formats` qabul qiladi.
7. [x] **Mini App** — chiplar takror doirasini tanlaydi, ro'yxatda nishonlar + progress,
   tinglashda avto-ovoz (blob-kesh), yangi formatlar, natijada "yopildi" soni.
8. [x] **Android** — DTO (`format`, `tokens`), kategoriya, avto-ovoz, builder, uz/ru/tg,
   5 statik tekshiruv, unit test, emulyator.
9. [x] **Tekshiruv** — to'liq pytest (e2e'siz), brauzerda Mini App oqimi, PROJECT_MEMORY.

## Qarorlar (foydalanuvchi ishonib topshirdi)

- Yopilish: 3 xil format, xato — progress nolga.
- UI: yangi ekran qurilmaydi; mavjud chiplar takror doirasini ham tanlaydi,
  CTA shunga mos yoziladi; ro'yxatda progress segmentlari va `1/3` (nuqtalar "⋯" menyuga o'xshab qolgani uchun).
- "O'zi aytish" mashqi keyingi bosqichga qoldirildi (AI/mikrofon talab qiladi).
- Bepul/reklama qoidalari va XP o'zgarmaydi.
