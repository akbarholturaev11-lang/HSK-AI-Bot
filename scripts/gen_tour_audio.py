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
Tashqi servissiz macOS fallback: python scripts/gen_tour_audio.py --local f01 ... f10
DISPLAY_TEXT course-v3.html dagi runTour() bilan bir xil bo'lishi shart.
AUDIO_TEXT esa talaffuz uchun alohida yoziladi va UI'da ko'rinmaydi.
"""
import asyncio
import os
import re
import subprocess
import sys
import tempfile

OUT_DIR = "app/static/audio/tour"

VOICES = {
    "uz": "uz-UZ-MadinaNeural",
    "ru": "ru-RU-SvetlanaNeural",
    "tj": "ru-RU-SvetlanaNeural",
}

# Tashqi TTS xizmatiga matn yubormaydigan macOS fallback. UZ uchun turk ovozi
# lotin yozuvini, TJ uchun esa rus ovozi fonetik kirill matnini o'qiydi.
LOCAL_VOICES = {"uz": "Yelda", "ru": "Milena", "tj": "Milena"}

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

# Starter 0 kartalari. Kalitlar scripts/gen_course_v3_from_seed.py dagi
# FOUNDATION_CARDS `narrate` qiymatlari bilan bir xil bo'lishi shart.
FOUNDATION_DISPLAY = {
    "ru": {
        "f01": "Сначала послушайте. Сейчас вы поймёте и сами соберёте эту фразу.",
        "f02": "Что означает 你好?",
        "f03": "Китайское слово может состоять из одного или нескольких ханцзы — письменных знаков. Пиньинь показывает произношение и тон латинскими буквами.",
        "f04": "你 — ты, 好 — хорошо. Вместе 你好 — обычное приветствие.",
        "f05": "Соберите приветствие в правильном порядке.",
        "f06": "Знак в пиньине показывает движение голоса; смена тона может изменить значение.",
        "f07": "Пишется nǐ hǎo. Когда рядом стоят два третьих тона, первый в естественной речи звучит как второй: ní hǎo.",
        "f08": "Какую запись вы услышали?",
        "f09": "Послушайте образец и повторите. Если микрофон не работает, урок продолжится.",
        "f10": "Теперь вы понимаете приветствие, узнаёте его на слух и можете собрать сами.",
    },
    "uz": {
        "f01": "Avval tinglang. Hozir bu iborani tushunib, o'zingiz tuzasiz.",
        "f02": "Ni hao nimani anglatadi?",
        "f03": "Xitoycha so'z bir yoki bir nechta hanzi, ya'ni yozuv belgilaridan tuzilishi mumkin. Pin-yin esa lotin harflari bilan talaffuz va ohangni ko'rsatadi.",
        "f04": "Ni, sen degani. Hao, yaxshi degani. Birga ni hao kundalik salomlashuv bo'ladi.",
        "f05": "Salom iborasini to'g'ri tartibda tuzing.",
        "f06": "Pin-yindagi belgi ovoz yo'nalishini ko'rsatadi. Ohang o'zgarsa, ma'no ham o'zgarishi mumkin.",
        "f07": "Yozilishi ni hao. Ikki uchinchi ohang yonma-yon kelganda birinchisi tabiiy nutqda ikkinchi ohangdek aytiladi: ni hao.",
        "f08": "Qaysi yozuvni eshitdingiz?",
        "f09": "Namunani eshitib takrorlang. Mikrofon ishlamasa, dars davom etadi.",
        "f10": "Endi siz salomlashuvni tushunasiz, eshitib taniysiz va o'zingiz tuza olasiz.",
    },
    "tj": {
        "f01": "Аввал гӯш кунед. Ҳоло ин ибораро мефаҳмед ва худатон месозед.",
        "f02": "你好 чӣ маъно дорад?",
        "f03": "Калимаи чинӣ метавонад аз як ё якчанд ханзӣ, яъне аломати хаттӣ таркиб ёбад. Пинйин талаффуз ва оҳангро бо ҳарфҳои лотинӣ нишон медиҳад.",
        "f04": "你 — ту, 好 — хуб. Якҷоя 你好 саломи ҳаррӯза мешавад.",
        "f05": "Ибораи саломро бо тартиби дуруст созед.",
        "f06": "Аломати пинйин самти овозро нишон медиҳад. Бо иваз шудани оҳанг маъно ҳам метавонад дигар шавад.",
        "f07": "nǐ hǎo навишта мешавад. Вақте ду оҳанги сеюм паи ҳам меоянд, аввалӣ дар гуфтори табиӣ мисли оҳанги дуюм садо медиҳад: ní hǎo.",
        "f08": "Кадом навиштро шунидед?",
        "f09": "Намунаро гӯш карда такрор кунед. Агар микрофон кор накунад, дарс идома меёбад.",
        "f10": "Акнун шумо саломро мефаҳмед, бо шунидан мешиносед ва худатон сохта метавонед.",
    },
}
for _lang, _steps in FOUNDATION_DISPLAY.items():
    DISPLAY_TEXT[_lang].update(_steps)

AUDIO_TEXT = {
    "ru": dict(DISPLAY_TEXT["ru"]),
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
        "f01": "Avval tinglang. Hozir bu iborani tushunib, o'zingiz tuzasiz.",
        "f02": "Ni hao nimani anglatadi?",
        "f03": "Xitoycha so'z bir yoki bir nechta hanzi, ya'ni yozuv belgilaridan tuzilishi mumkin. Pin-yin esa lotin harflari bilan talaffuz va ohangni ko'rsatadi.",
        "f04": "Ni, sen degani. Hao, yaxshi degani. Birga ni hao kundalik salomlashuv bo'ladi.",
        "f05": "Salom iborasini to'g'ri tartibda tuzing.",
        "f06": "Pin-yindagi belgi ovoz yo'nalishini ko'rsatadi. Ohang o'zgarsa, ma'no ham o'zgarishi mumkin.",
        "f07": "Yozilishi ni hao. Ikki uchinchi ohang yonma-yon kelganda birinchisi tabiiy nutqda ikkinchi ohangdek aytiladi: ni hao.",
        "f08": "Qaysi yozuvni eshitdingiz?",
        "f09": "Namunani eshitib takrorlang. Mikrofon ishlamasa, dars davom etadi.",
        "f10": "Endi siz salomlashuvni tushunasiz, eshitib taniysiz va o'zingiz tuza olasiz.",
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
        "f01": "Аввал гуш кунед. Холо ин ибораро мефахмед ва худатон месозед.",
        "f02": "Ни хао чи маъно дорад?",
        "f03": "Калимаи чини метавонад аз як ё якчанд ханзи, яъне аломати хатти таркиб ёбад. Пинйин талаффуз ва охангро бо харфхои лотини нишон медихад.",
        "f04": "Ни, ту. Хао, хуб. Якчоя ни хао саломи харруза мешавад.",
        "f05": "Ибораи саломро бо тартиби дуруст созед.",
        "f06": "Аломати пинйин самти овозро нишон медихад. Бо иваз шудани оханг маъно хам метавонад дигар шавад.",
        "f07": "Ни хао навишта мешавад. Вакте ду оханги сеюм пайи хам меоянд, аввали дар гуфтори табии мисли оханги дуюм садо медихад: ни хао.",
        "f08": "Кадом навиштро шунидед?",
        "f09": "Намунаро гуш карда такрор кунед. Агар микрофон кор накунад, дарс идома меёбад.",
        "f10": "Акнун шумо саломро мефахмед, бо шунидан мешиносед ва худатон сохта метавонед.",
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
    # Ixtiyoriy: faqat berilgan kalitlarni qayta yaratish, masalan
    #   python3 scripts/gen_tour_audio.py f01 f02
    # Argumentsiz ishga tushirilsa — hammasi (avvalgi xatti-harakat).
    only = {k for k in sys.argv[1:] if not k.startswith("-")}
    local = "--local" in sys.argv
    edge_tts = None
    if not local:
        import edge_tts as edge_tts_module

        edge_tts = edge_tts_module
    total = 0
    for lang, steps in AUDIO_TEXT.items():
        if set(steps) != set(DISPLAY_TEXT[lang]):
            missing = sorted(set(DISPLAY_TEXT[lang]) - set(steps))
            extra = sorted(set(steps) - set(DISPLAY_TEXT[lang]))
            raise RuntimeError(f"{lang} audio keys mismatch; missing={missing}, extra={extra}")
        if only:
            unknown = sorted(only - set(steps))
            if unknown:
                raise RuntimeError(f"{lang} unknown keys: {unknown}")
        voice = LOCAL_VOICES[lang] if local else VOICES[lang]
        d = os.path.join(OUT_DIR, lang)
        os.makedirs(d, exist_ok=True)
        for key, raw in steps.items():
            if only and key not in only:
                continue
            text = clean(raw)
            ext = "wav" if local else "mp3"
            out = os.path.join(d, f"{key}.{ext}")
            if local:
                with tempfile.TemporaryDirectory(prefix="hsk-starter-audio-") as tmp:
                    aiff = os.path.join(tmp, f"{key}.aiff")
                    subprocess.run(
                        ["say", "-v", voice, "-r", "172", "-o", aiff, text],
                        check=True,
                    )
                    subprocess.run(
                        [
                            "afconvert", aiff, "-o", out, "-f", "WAVE",
                            "-d", "LEI16@22050", "-c", "1",
                        ],
                        check=True,
                    )
            else:
                comm = edge_tts.Communicate(text, voice, rate="-4%")
                await comm.save(out)
            total += 1
            print(f"  {lang}/{key}.{ext}  ({voice})")
    print(f"Tayyor: {total} ta audio fayl -> {OUT_DIR}")


if __name__ == "__main__":
    asyncio.run(main())
