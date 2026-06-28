#!/usr/bin/env python3
"""Course v3 tour narration -> oldindan tayyorlangan audio fayllar.

edge-tts (Microsoft Edge bepul TTS, API kalitsiz) yordamida har bir tour
qadami uchun MP3 yaratadi. Natija: app/static/audio/tour/<lang>/<key>.mp3

Ovozlar:
  uz -> uz-UZ-MadinaNeural  (haqiqiy o'zbek neural ovozi)
  ru -> ru-RU-SvetlanaNeural
  tj -> ru-RU-SvetlanaNeural (native tojik TTS yo'q; audio matn rus voice uchun
        fonetik kirillga moslangan)

Ishga tushirish:  .venv/bin/python3.14 scripts/gen_tour_audio.py
DISPLAY_TEXT course-v3.html dagi runTour() bilan bir xil bo'lishi shart.
AUDIO_TEXT esa talaffuz uchun alohida yoziladi va UI'da ko'rinmaydi.
"""
import asyncio
import os
import re

import edge_tts

OUT_DIR = "app/static/audio/tour"

VOICES = {
    "uz": "uz-UZ-MadinaNeural",
    "ru": "ru-RU-SvetlanaNeural",
    "tj": "ru-RU-SvetlanaNeural",
}

DISPLAY_TEXT = {
    "ru": {
        "c": "Вот ваш курс! Каждый кружок — это урок. Нажми на узел и начни учиться.",
        "cNode": "Это твой текущий урок — нажми и начни! Внутри урока появится кнопка ✏️ — нажми, чтобы увидеть как пишется иероглиф.",
        "m": "Раздел практики — тут всё для закрепления знаний.",
        "mDict": "Словарь иероглифов 字 — все знаки HSK 1–4: написание, пиньинь, значение. Можно искать по иероглифу или значению.",
        "mRecog": "Распознавание — слышишь и видишь слово, выбираешь нужный иероглиф. Тренирует чтение знаков.",
        "mPron": "Произношение — слушай эталон, повторяй вслух, а ИИ проверит твоё произношение и тон.",
        "mTest": "Тест-центр — официальные экзамены HSK 1–4 и тест для определения твоего уровня с нуля.",
        "mMist": "Мои ошибки — здесь собираются все слова, где ты ошибся. Повторяй слабые места!",
        "v": "AI Voice — живой разговор с пандой 阿宝 на китайском. Говори — получай мгновенные исправления!",
        "r": "Лига 朱雀 — твоё место среди учеников. Набирай XP каждый день и поднимайся в рейтинге!",
        "p": "Профиль: стрик, дневная цель, кубки и достижения. Настрой язык, уведомления и XP-цель.",
    },
    "uz": {
        "c": "Mana kursingiz! Har bir doira — bitta dars. Tugmachani bosing va o'qishni boshlang.",
        "cNode": "Bu hozirgi darsingiz — bosing va boshlang! Dars ichida ✏️ tugmasi paydo bo'ladi — ieroglif yozilishini ko'rish uchun bosing.",
        "m": "Mashq bo'limi — bilimlarni mustahkamlash uchun hamma narsa.",
        "mDict": "Ieroglif lug'ati 字 — HSK 1–4 barcha belgilar: yozilishi, pinyin va ma'nosi. Ieroglif yoki ma'no bo'yicha qidirish mumkin.",
        "mRecog": "Ieroglifni tanish — so'zni eshitib, ko'rib, to'g'ri ieroglifni tanlaysiz. Belgilarni o'qishni mashq qiladi.",
        "mPron": "Talaffuz mashqi — namunani eshiting, ovoz chiqarib takrorlang, AI talaffuz va ohangni tekshiradi.",
        "mTest": "Test markazi — HSK 1–4 rasmiy imtihon savollari va noldan daraja aniqlash testi.",
        "mMist": "Xatolarim — xato qilgan so'zlar shu yerda yig'iladi. Zaif joylarni takrorlang!",
        "v": "AI Voice — panda 阿宝 bilan jonli xitoycha suhbat. Gapiring — darhol tuzatish oling!",
        "r": "朱雀 ligasi — o'quvchilar orasidagi o'rningiz. Har kuni XP to'plang va yuqoriga chiqing!",
        "p": "Profil: streak, kunlik maqsad, kuboklar va yutuqlar. Til, bildirishnoma va XP maqsadini sozlang.",
    },
    "tj": {
        "c": "Ин ҷо курси шумо! Ҳар доира — як дарс. Тугмачаро пахш кунед ва омӯзишро оғоз кунед.",
        "cNode": "Ин дарси ҷории шумо — пахш кунед ва оғоз кунед! Дар дарс тугмаи ✏️ пайдо мешавад — барои дидани навиштани иероглиф пахш кунед.",
        "m": "Бахши машқ — ҳама чиз барои мустаҳкам кардани дониш.",
        "mDict": "Луғати иероглиф 字 — ҳамаи аломатҳои HSK 1–4: навишт, пинйин, маъно. Ҷустуҷӯ мумкин аст.",
        "mRecog": "Шинохти иероглиф — калимаро шунида ва дида, иероглифи дурустро интихоб мекунед. Хонданро машқ мекунад.",
        "mPron": "Машқи талаффуз — намунаро гӯш кунед, бо овоз такрор кунед, AI талаффуз ва оҳангро месанҷад.",
        "mTest": "Маркази тест — имтиҳонҳои расмии HSK 1–4 ва тести муайянкунии сатҳ аз сифр.",
        "mMist": "Хатоҳои ман — калимаҳое ки хато кардед. Ҷойҳои заифро такрор кунед!",
        "v": "AI Voice — сӯҳбати зиндаи чинӣ бо панда 阿宝. Гӯед — ислоҳи фаврӣ гиред!",
        "r": "Лигаи 朱雀 — ҷойгоҳи шумо миёни донишҷӯён. Ҳар рӯз XP ҷамъ кунед ва боло равед!",
        "p": "Профил: streak, ҳадафи рӯзона, ҷомҳо ва дастовардҳо. Забон, огоҳиҳо ва XP-ро танзим кунед.",
    },
}

AUDIO_TEXT = {
    "ru": DISPLAY_TEXT["ru"],
    "uz": {
        "c": "Mana kursingiz. Har bir doira bitta dars. Tugmachani bosing va o'qishni boshlang.",
        "cNode": "Bu hozirgi darsingiz. Bosing va boshlang. Dars ichida qalam tugmasi paydo bo'ladi. Ieroglif yozilishini ko'rish uchun bosing.",
        "m": "Mashq bo'limi. Bilimlarni mustahkamlash uchun hamma narsa shu yerda.",
        "mDict": "Ieroglif lug'ati. Birinchi darajadan to'rtinchi darajagacha barcha belgilar: yozilishi, pin-yin va ma'nosi. Ieroglif yoki ma'no bo'yicha qidirish mumkin.",
        "mRecog": "Ieroglifni tanish. So'zni eshitib, ko'rib, to'g'ri ieroglifni tanlaysiz. Belgilarni o'qishni mashq qiladi.",
        "mPron": "Talaffuz mashqi. Namunani eshiting, ovoz chiqarib takrorlang. Sun'iy intellekt talaffuz va ohangni tekshiradi.",
        "mTest": "Test markazi. Birinchi darajadan to'rtinchi darajagacha rasmiy imtihon savollari va noldan daraja aniqlash testi.",
        "mMist": "Xatolarim. Xato qilgan so'zlar shu yerda yig'iladi. Zaif joylarni takrorlang.",
        "v": "Sun'iy intellekt ovozli suhbat. Panda bilan jonli xitoycha gaplashing. Gapiring va darhol tuzatish oling.",
        "r": "Liga. O'quvchilar orasidagi o'rningiz. Har kuni tajriba balli to'plang va yuqoriga chiqing.",
        "p": "Profil. Ketma-ketlik, kunlik maqsad, kuboklar va yutuqlar. Til, bildirishnoma va tajriba maqsadini sozlang.",
    },
    "tj": {
        "c": "Ин джо курси шумо. Хар доира як дарс. Тугмачаро пахш кунед ва омузишро огоз кунед.",
        "cNode": "Ин дарси джории шумо. Пахш кунед ва огоз кунед. Дар дарс тугмаи калам пайдо мешавад. Барои дидани навиштани иероглиф пахш кунед.",
        "m": "Бахши машк. Хама чиз барои мустахкам кардани дониш.",
        "mDict": "Лугати иероглиф. Хамаи аломатхои аш эс ка аз як то чор: навишт, пинйин ва маъно. Джустуджу мумкин аст.",
        "mRecog": "Шинохти иероглиф. Калимаро шунида ва дида, иероглифи дурустро интихоб мекунед. Хонданро машк мекунад.",
        "mPron": "Машки талаффуз. Намунаро гуш кунед, бо овоз такрор кунед. Зехни сунъи талаффуз ва охангро месанчад.",
        "mTest": "Маркази тест. Имтихонхои расмии аш эс ка аз як то чор ва тести муайянкунии сатх аз сифр.",
        "mMist": "Хатохои ман. Калимахое ки хато кардед. Джойхои заифро такрор кунед.",
        "v": "Эй ай войс. Сухбати зиндаи чини бо панда. Гуед ва ислохи фаври гиред.",
        "r": "Лига. Джойгохи шумо миёни донишчуён. Хар руз тачриба балл чамъ кунед ва боло равед.",
        "p": "Профил. Пайдарпайи, хадафи рузона, джомхо ва дастовардхо. Забон, огохихо ва хадафи тачрибаро танзим кунед.",
    },
}

# CJK ieroglif va emoji-larni audiodan olib tashlash (vizual matnда qoladi)
_STRIP = re.compile(r"[一-鿿　-〿️✀-➿\U0001F000-\U0001FAFF]")


def clean(text: str) -> str:
    text = _STRIP.sub("", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s+([—,.!?])", r" \1", text)
    return text


async def main():
    total = 0
    for lang, steps in AUDIO_TEXT.items():
        if set(steps) != set(DISPLAY_TEXT[lang]):
            missing = sorted(set(DISPLAY_TEXT[lang]) - set(steps))
            extra = sorted(set(steps) - set(DISPLAY_TEXT[lang]))
            raise RuntimeError(f"{lang} audio keys mismatch; missing={missing}, extra={extra}")
        voice = VOICES[lang]
        d = os.path.join(OUT_DIR, lang)
        os.makedirs(d, exist_ok=True)
        for key, raw in steps.items():
            text = clean(raw)
            out = os.path.join(d, f"{key}.mp3")
            comm = edge_tts.Communicate(text, voice, rate="-4%")
            await comm.save(out)
            total += 1
            print(f"  {lang}/{key}.mp3  ({voice})")
    print(f"Tayyor: {total} ta audio fayl -> {OUT_DIR}")


if __name__ == "__main__":
    asyncio.run(main())
