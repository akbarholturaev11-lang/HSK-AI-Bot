# Codex AI Prompt — HSK Course v3 Lesson Data Files

## Vazifa

`app/static/course_v3_data/` papkasi ichiga HSK kurs darslarining JSON data fayllarini yarating.

### Yaratilishi kerak bo'lgan fayllar

```
app/static/course_v3_data/
  hsk1/
    lesson_01.json   (15 ta dars)
    lesson_02.json
    ...
    lesson_15.json
  hsk2/
    lesson_01.json   (15 ta dars)
    ...
    lesson_15.json
  hsk3/
    lesson_01.json   (20 ta dars)
    ...
    lesson_20.json
  hsk4/
    lesson_01.json   (20 ta dars)
    ...
    lesson_20.json
```

---

## JSON Schema (har bir fayl uchun)

```json
{
  "schema_version": 2,
  "level": "hsk1",
  "lesson_id": 1,
  "title": "你好",
  "subtitle": {
    "uz": "...",
    "ru": "...",
    "tj": "..."
  },
  "active_words": [
    {
      "no": 1,
      "zh": "你",
      "pinyin": "nǐ",
      "pos": "pron.",
      "meaning": {
        "uz": "sen (birlik)",
        "ru": "ты (единственное число)",
        "tj": "ту (яккашумора)"
      }
    }
  ],
  "grammar": [
    {
      "no": 1,
      "title": { "uz": "...", "ru": "...", "tj": "..." },
      "title_zh": "...",
      "rule": { "uz": "...", "ru": "...", "tj": "..." },
      "examples": [
        {
          "zh": "...",
          "pinyin": "...",
          "translation": { "uz": "...", "ru": "...", "tj": "..." }
        }
      ]
    }
  ],
  "dialogues": [
    {
      "scene": { "uz": "...", "ru": "...", "tj": "..." },
      "dialogue": [
        {
          "speaker": "A",
          "zh": "你好！",
          "pinyin": "Nǐ hǎo!",
          "text": { "uz": "Salom!", "ru": "Привет!", "tj": "Салом!" }
        },
        {
          "speaker": "B",
          "zh": "你好！",
          "pinyin": "Nǐ hǎo!",
          "text": { "uz": "Salom!", "ru": "Привет!", "tj": "Салом!" }
        }
      ]
    }
  ],
  "sections": [
    {
      "section_no": 1,
      "section_title": { "uz": "Yangi so'zlar", "ru": "Новые слова", "tj": "Калимаҳои нав" },
      "section_purpose": "intro",
      "cards": [
        {
          "type": "active_word",
          "word": {
            "zh": "你",
            "pinyin": "nǐ",
            "pos": "pron.",
            "meaning": { "uz": "sen", "ru": "ты", "tj": "ту" }
          }
        }
      ]
    },
    {
      "section_no": 2,
      "section_title": { "uz": "Mashq", "ru": "Упражнение", "tj": "Машқ" },
      "section_purpose": "practice",
      "cards": [
        {
          "type": "meaning_guess",
          "prompt": { "uz": "Quyidagi so'zning ma'nosini tanlang:", "ru": "Выберите значение слова:", "tj": "Маънои калимаро интихоб кунед:" },
          "title": { "uz": "Ma'nosi nima?", "ru": "Что означает?", "tj": "Маъно чист?" },
          "options": [
            { "uz": "sen", "ru": "ты", "tj": "ту" },
            { "uz": "u", "ru": "он", "tj": "вай" },
            { "uz": "biz", "ru": "мы", "tj": "мо" },
            { "uz": "siz", "ru": "вы", "tj": "шумо" }
          ],
          "correct_index": 0,
          "explanation": { "uz": "你 = sen (birlik)", "ru": "你 = ты (единственное)", "tj": "你 = ту (яккашумора)" }
        },
        {
          "type": "pinyin_choice",
          "prompt": { "uz": "Talaffuzini tanlang:", "ru": "Выберите произношение:", "tj": "Талаффузро интихоб кунед:" },
          "title": { "uz": "Qanday o'qiladi?", "ru": "Как читается?", "tj": "Чӣ хел хонда мешавад?" },
          "options": ["nǐ", "nī", "nì", "níng"],
          "correct_index": 0,
          "explanation": { "uz": "你 — nǐ (3-ton)", "ru": "你 — nǐ (3-й тон)", "tj": "你 — nǐ (садои 3)" }
        },
        {
          "type": "translation_choice",
          "prompt": { "uz": "'Sen' xitoycha nima?", "ru": "'Ты' по-китайски?", "tj": "'Ту' ба чинӣ чист?" },
          "title": { "uz": "Xitoycha qanday?", "ru": "Как по-китайски?", "tj": "Ба чинӣ чӣ тавр?" },
          "options": ["你", "我", "他", "她"],
          "correct_index": 0,
          "explanation": { "uz": "'Sen' = 你 (nǐ)", "ru": "'Ты' = 你 (nǐ)", "tj": "'Ту' = 你 (nǐ)" }
        },
        {
          "type": "sentence_builder",
          "sentence": { "uz": "Salom! (Sizga nisbatan)", "ru": "Привет! (к одному человеку)", "tj": "Салом! (ба як нафар)" },
          "tokens": ["你", "好", "吗", "我"],
          "answer_tokens": ["你", "好"],
          "explanation": { "uz": "你好 = Salom!", "ru": "你好 = Привет!", "tj": "你好 = Салом!" }
        },
        {
          "type": "pronunciation",
          "phrase": "你好",
          "pinyin": "nǐ hǎo",
          "translation": { "uz": "Salom!", "ru": "Привет!", "tj": "Салом!" }
        }
      ]
    },
    {
      "section_no": 3,
      "section_title": { "uz": "Dialog", "ru": "Диалог", "tj": "Муколама" },
      "section_purpose": "dialog",
      "cards": [
        {
          "type": "quick_quiz",
          "prompt": { "uz": "Dialogda A nima deydi birinchi?", "ru": "Что говорит A в начале диалога?", "tj": "Дар муколама A аввал чӣ мегӯяд?" },
          "title": { "uz": "Dialogdan savol:", "ru": "Вопрос по диалогу:", "tj": "Савол аз муколама:" },
          "options": ["你好！", "谢谢！", "对不起！", "再见！"],
          "correct_index": 0,
          "explanation": { "uz": "A birinchi 你好 (Salom) deydi", "ru": "A говорит 你好 (Привет)", "tj": "A аввал 你好 (Салом) мегӯяд" }
        }
      ]
    }
  ]
}
```

---

## Card turlari (type)

| type | Tavsif |
|------|---------|
| `active_word` | Yangi so'z kartochkasi — faqat `word` fieldi kerak |
| `meaning_guess` | So'z beriladi, tarjimani topish kerak. `prompt` (zh yoki matn), `options` (4 ta), `correct_index` |
| `pinyin_choice` | Ieroglif beriladi, pinyin tanlash. `options` — 4 ta pinyin string |
| `translation_choice` | Tarjima beriladi, ieroglif tanlash. `options` — 4 ta zh string |
| `hanzi_choice` | Pinyin beriladi, to'g'ri ieroglif tanlash |
| `sentence_builder` | Tokenlarni to'g'ri tartibda joylashtirish. `tokens`, `answer_tokens` |
| `match_pairs` | Juftliklar. `pairs`: `[["zh", {"uz":...,"ru":...,"tj":...}], ...]` — 3-4 ta juft |
| `pronunciation` | Talaffuz mashqi. `phrase` (zh), `pinyin`, `translation` |
| `gap_fill` | Bo'sh joy to'ldirish. `sentence` (zh, ____ bilan), `options`, `correct_index` |
| `listening_choice` | Eshitib tanlash. `audio_text` (zh), `options`, `correct_index` |
| `quick_quiz` | Umumiy savol-javob. `prompt`, `options`, `correct_index`, `explanation` |

---

## Til talabi

Barcha matnli maydonlar **uchta tilda** bo'lishi SHART:
- `uz` — O'zbek
- `ru` — Rus
- `tj` — Tojik (lotin emas, kirill: Тоҷикӣ)

Pinyin, zh, pos — faqat bitta (universal).

---

## HSK 1 darslar ro'yxati (15 ta)

| # | title (zh) | Mavzu |
|---|-----------|-------|
| 01 | 你好 | Salomlashish, uzr so'rash |
| 02 | 谢谢你 | Minnatdorchilik, xayrlashuv |
| 03 | 你叫什么名字 | Ismni so'rash, tanishish |
| 04 | 你是哪国人 | Millat, davlat, kasb |
| 05 | 这是什么 | Narsalarni nomlash, 这/那 |
| 06 | 多少钱 | Narx va sonlar 1–100 |
| 07 | 现在几点 | Vaqt va soat |
| 08 | 今天星期几 | Hafta kunlari, sana |
| 09 | 你家在哪儿 | Manzil, yo'l ko'rsatish |
| 10 | 你吃什么 | Taom, ovqatlanish |
| 11 | 你喝什么 | Ichimliklar, buyurtma |
| 12 | 你有几个 | Miqdor, 有/没有 |
| 13 | 天气怎么样 | Ob-havo, fasllar |
| 14 | 你身体好吗 | Salomatlik, his-tuyg'ular |
| 15 | 复习 — HSK 1 | Takror va umumiy test |

---

## HSK 2 darslar ro'yxati (15 ta)

| # | title (zh) | Mavzu |
|---|-----------|-------|
| 01 | 你去哪儿 | Transport, yo'nalish |
| 02 | 怎么走 | Yo'l ko'rsatish, chapga/o'ngga |
| 03 | 我想买 | Xarid qilish, ranglar, o'lcham |
| 04 | 你喜欢什么 | Sevimli narsalar, dam olish |
| 05 | 我会说中文 | Mahorat, 会/能/可以 |
| 06 | 你在做什么 | Hozirgi harakatlar, 在+动词 |
| 07 | 昨天你做了什么 | O'tgan zamon, 了 yuklamasi |
| 08 | 我比你高 | Taqqoslash, 比 |
| 09 | 你看过吗 | Tajriba, 过 yuklamasi |
| 10 | 快点儿 | Tezlik, intensivlik, 一点儿 |
| 11 | 工作和学习 | Ish, maktab, kasblar |
| 12 | 家庭成员 | Oila a'zolari |
| 13 | 身体部位 | Tananing a'zolari |
| 14 | 我的爱好 | Mashg'ulotlar, sport |
| 15 | 复习 — HSK 2 | Takror va umumiy test |

---

## HSK 3 darslar ro'yxati (20 ta)

| # | title (zh) | Mavzu |
|---|-----------|-------|
| 01 | 预订房间 | Mehmonxona, bron qilish |
| 02 | 看病 | Shifokor, kasallik |
| 03 | 打电话 | Telefon suhbati |
| 04 | 购物中心 | Savdo markazi, chegirmalar |
| 05 | 中国文化 | Xitoy madaniyati, bayramlar |
| 06 | 学习汉字 | Ieroglif yozish qoidalari |
| 07 | 出行计划 | Sayohat rejasi |
| 08 | 餐厅点菜 | Restoran, ovqat buyurtma |
| 09 | 租房子 | Uy ijarasi, ko'chish |
| 10 | 工作面试 | Ish intervyu |
| 11 | 网络购物 | Onlayn xarid |
| 12 | 环境保护 | Ekologiya, tabiat |
| 13 | 运动健康 | Sport va salomatlik |
| 14 | 节日习俗 | Bayram odatlari |
| 15 | 交通出行 | Transport, yo'l qoidalari |
| 16 | 银行业务 | Bank, pul o'tkazma |
| 17 | 新闻资讯 | Yangiliklar, OAV |
| 18 | 社交媒体 | Ijtimoiy tarmoqlar |
| 19 | 旅游景点 | Turistik joylar |
| 20 | 复习 — HSK 3 | Takror va umumiy test |

---

## HSK 4 darslar ro'yxati (20 ta)

| # | title (zh) | Mavzu |
|---|-----------|-------|
| 01 | 经济全球化 | Globallashuv, iqtisodiyot |
| 02 | 科技发展 | Texnologiya, innovatsiya |
| 03 | 教育制度 | Ta'lim tizimi |
| 04 | 文学艺术 | Adabiyot va san'at |
| 05 | 政治社会 | Jamiyat va siyosat |
| 06 | 环境问题 | Ekologik muammolar |
| 07 | 医疗卫生 | Tibbiyot va sog'liqni saqlash |
| 08 | 法律法规 | Qonun va huquq |
| 09 | 商业谈判 | Biznes muzokaralar |
| 10 | 文化交流 | Madaniy almashinuv |
| 11 | 历史传统 | Tarix va an'analar |
| 12 | 心理健康 | Psixologiya va ruhiy salomatlik |
| 13 | 体育竞技 | Musobaqa sporti |
| 14 | 饮食文化 | Ovqat madaniyati |
| 15 | 城乡发展 | Shahar va qishloq rivojlanishi |
| 16 | 人际关系 | Shaxslararo munosabatlar |
| 17 | 哲学思想 | Falsafa va tafakkur |
| 18 | 传统医学 | An'anaviy tibbiyot, akupunktur |
| 19 | 未来展望 | Kelajak rejalar va orzular |
| 20 | 复习 — HSK 4 | Takror va umumiy test |

---

## Har bir darsda bo'lishi kerak bo'lgan minimum

1. **active_words**: 5–8 ta yangi so'z
2. **grammar**: 1–2 ta grammatika qoidasi (misollar bilan)
3. **dialogues**: 1 ta dialog (4–6 qator, A va B o'rtasida)
4. **sections**:
   - Section 1 (`intro`): barcha `active_word` kartochkalari
   - Section 2 (`practice`): kamida 6 ta mashq (`meaning_guess`, `pinyin_choice`, `translation_choice`, `sentence_builder`, `match_pairs`, `pronunciation` aralash)
   - Section 3 (`dialog`): dialog + 2 ta `quick_quiz` dialog bo'yicha

---

## Muhim qoidalar

1. Har bir `options` arrayida **to'g'ri javob** `correct_index` bilan ko'rsatilishi shart
2. `explanation` — har doim 3 tilda
3. `match_pairs` uchun `pairs` arrayi: `[["zh_so'z", {"uz":"...","ru":"...","tj":"..."}]]`
4. Takror darsida (`复习`) — oldingi 14 (yoki 19) darsdan so'zlar qayta keladi, ko'proq test savollari
5. Barcha zh matnlar to'g'ri unicode ieroglif bo'lsin (escape emas)
6. Pinyin — ton belgilari bilan: `nǐ`, `hǎo`, `māo` va h.k.
7. `pos` qisqartmalari: `n.` (ot), `v.` (fe'l), `adj.` (sifat), `adv.` (ravish), `pron.` (olmosh), `num.` (son), `mw.` (o'lchov), `prep.` (predlog), `conj.` (bog'lovchi), `expr.` (ifoda/idiom)

---

## Fayl nomlash

- `lesson_01.json`, `lesson_02.json`, ..., `lesson_15.json` (2 xonali raqam, 0 bilan to'ldirilgan)
- Joylashuv: `app/static/course_v3_data/{level}/lesson_XX.json`

---

## Misol — mavjud lesson_01.json (reference)

Mavjud faylni ko'rish uchun: `app/static/course_content/hsk1/lesson_01.json`
Bu fayl HSK1 dars 1 ning eski formatidagi misoli — undan so'z, grammatika va dialog ma'lumotlarini olib, yuqoridagi yangi schemaga moslang.

Shuningdek `lesson_02.json` va `lesson_03.json` ham mavjud — ularni ham yangi formatga o'tkazing va `app/static/course_v3_data/hsk1/` ga saqlang.

---

## Yakuniy natija

Har bir fayl mustaqil, to'liq dars bo'lishi kerak. Frontend (`course-v3.html`) faylni `fetch("/course_v3_data/hsk1/lesson_01.json")` orqali yuklaydi va `buildQueue(d)` funksiyasi `d.sections[*].cards` dan o'quv oqimini quради.
