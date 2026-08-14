from datetime import date, datetime, timedelta, timezone

from app.services.course_v3_vocab import words_for_level


class DailyPracticeService:
    def __init__(self, session):
        self.session = session

    def today(self) -> date:
        return datetime.now(timezone.utc).date()

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _level_key(self, user) -> str:
        raw = str(getattr(user, "level", "") or "beginner").lower().replace("_", "").replace(" ", "")
        if raw in {"hsk1", "hsk2", "hsk3", "hsk4"}:
            return raw
        return "beginner"

    def is_completed_today(self, user) -> bool:
        if not user:
            return False
        return getattr(user, "daily_practice_last_day", None) == self.today()

    async def mark_started(self, user) -> None:
        user.daily_practice_started_at = self._now()
        await self.session.flush()

    async def mark_completed(self, user) -> None:
        today = self.today()
        last_day = getattr(user, "daily_practice_last_day", None)
        current_streak = int(getattr(user, "daily_practice_streak", 0) or 0)

        if last_day == today:
            streak = max(1, current_streak)
        elif last_day == today - timedelta(days=1):
            streak = current_streak + 1
        else:
            streak = 1

        user.daily_practice_completed_at = self._now()
        user.daily_practice_last_day = today
        user.daily_practice_streak = streak
        await self.session.flush()

    def _copy(self, lang: str) -> dict[str, str]:
        copies = {
            "uz": {
                "entry_title": "⏱ <b>Bugungi 3 daqiqalik mashq</b>",
                "entry_body": (
                    "<blockquote>3 ta yangi so'z, 2 ta tez quiz va 1 ta oddiy gap. "
                    "Tugagach savol-javob rejimida kunlik limit bilan davom etasiz.</blockquote>"
                ),
                "words": "1) Yangi so'zlar",
                "quiz": "2) Tez quiz",
                "sentence": "3) Oddiy gap",
                "ready": "Tayyor bo'lsangiz, javoblarni ko'ring.",
                "done": "✅ <b>Bugungi mashq tugadi</b>",
                "result": (
                    "<blockquote>Siz 3 ta so'z ko'rdingiz, 2 ta quizni tekshirdingiz "
                    "va bitta sodda gapni mustahkamladingiz.</blockquote>"
                ),
                "answers": "Javoblar:",
                "next": "Endi savolingizni yozing yoki kursni o'zingiz boshlang.",
            },
            "ru": {
                "entry_title": "⏱ <b>Сегодняшняя 3-минутная практика</b>",
                "entry_body": (
                    "<blockquote>3 новых слова, 2 быстрых quiz и 1 простая фраза. "
                    "После этого можно продолжить в вопрос-ответ с дневным лимитом.</blockquote>"
                ),
                "words": "1) Новые слова",
                "quiz": "2) Быстрый quiz",
                "sentence": "3) Простая фраза",
                "ready": "Когда будете готовы, посмотрите ответы.",
                "done": "✅ <b>Сегодняшняя практика завершена</b>",
                "result": (
                    "<blockquote>Вы увидели 3 слова, проверили 2 quiz-вопроса "
                    "и закрепили одну простую фразу.</blockquote>"
                ),
                "answers": "Ответы:",
                "next": "Теперь напишите вопрос или откройте курс самостоятельно.",
            },
            "tj": {
                "entry_title": "⏱ <b>Машқи 3-дақиқаи имрӯз</b>",
                "entry_body": (
                    "<blockquote>3 калимаи нав, 2 quiz-и зуд ва 1 ҷумлаи одӣ. "
                    "Баъд метавонед дар савол-ҷавоб бо лимити рӯзона давом диҳед.</blockquote>"
                ),
                "words": "1) Калимаҳои нав",
                "quiz": "2) Quiz-и зуд",
                "sentence": "3) Ҷумлаи одӣ",
                "ready": "Вақте тайёр шудед, ҷавобҳоро бинед.",
                "done": "✅ <b>Машқи имрӯз анҷом шуд</b>",
                "result": (
                    "<blockquote>Шумо 3 калимаро дидед, 2 саволи quiz-ро санҷидед "
                    "ва як ҷумлаи соддаро мустаҳкам кардед.</blockquote>"
                ),
                "answers": "Ҷавобҳо:",
                "next": "Акнун савол нависед ё курсро худатон оғоз кунед.",
            },
        }
        return copies.get(lang, copies["ru"])

    def _payload(self, user, lang: str) -> dict:
        meanings = {
            "uz": {
                "hello": "salom",
                "thanks": "rahmat",
                "goodbye": "xayr",
                "today": "bugun",
                "study": "o'qimoq",
                "friend": "do'st",
                "important": "muhim",
                "habit": "odat",
                "influence": "ta'sir qilmoq",
                "although": "garchi",
                "but": "lekin",
                "solve": "hal qilmoq",
            },
            "ru": {
                "hello": "привет",
                "thanks": "спасибо",
                "goodbye": "до свидания",
                "today": "сегодня",
                "study": "учиться",
                "friend": "друг",
                "important": "важный",
                "habit": "привычка",
                "influence": "влиять",
                "although": "хотя",
                "but": "но",
                "solve": "решать",
            },
            "tj": {
                "hello": "салом",
                "thanks": "раҳмат",
                "goodbye": "хайр",
                "today": "имрӯз",
                "study": "хондан",
                "friend": "дӯст",
                "important": "муҳим",
                "habit": "одат",
                "influence": "таъсир кардан",
                "although": "гарчанде",
                "but": "аммо",
                "solve": "ҳал кардан",
            },
        }
        meaning = meanings.get(lang, meanings["ru"])

        level_payloads = {
            "beginner": {
                "words": [("你好", "nǐ hǎo", meaning["hello"]), ("谢谢", "xièxie", meaning["thanks"]), ("再见", "zàijiàn", meaning["goodbye"])],
                "quiz": [("你好 = ?", meaning["hello"]), ("谢谢 = ?", meaning["thanks"])],
                "sentence": "你好，我学习中文。",
                "sentence_meaning": {
                    "uz": "Salom, men xitoy tilini o'rganyapman.",
                    "ru": "Привет, я учу китайский.",
                    "tj": "Салом, ман забони чиниро меомӯзам.",
                }.get(lang, "Привет, я учу китайский."),
            },
            "hsk1": {
                "words": [("今天", "jīntiān", meaning["today"]), ("学习", "xuéxí", meaning["study"]), ("朋友", "péngyou", meaning["friend"])],
                "quiz": [("今天 = ?", meaning["today"]), ("朋友 = ?", meaning["friend"])],
                "sentence": "我今天学习中文。",
                "sentence_meaning": {
                    "uz": "Men bugun xitoy tilini o'qiyman.",
                    "ru": "Я сегодня учу китайский.",
                    "tj": "Ман имрӯз забони чиниро мехонам.",
                }.get(lang, "Я сегодня учу китайский."),
            },
            "hsk2": {
                "words": [("今天", "jīntiān", meaning["today"]), ("学习", "xuéxí", meaning["study"]), ("朋友", "péngyou", meaning["friend"])],
                "quiz": [("学习 = ?", meaning["study"]), ("朋友 = ?", meaning["friend"])],
                "sentence": "我和朋友一起学习中文。",
                "sentence_meaning": {
                    "uz": "Men do'stim bilan xitoy tilini o'qiyman.",
                    "ru": "Я учу китайский вместе с другом.",
                    "tj": "Ман бо дӯстам забони чиниро мехонам.",
                }.get(lang, "Я учу китайский вместе с другом."),
            },
            "hsk3": {
                "words": [("重要", "zhòngyào", meaning["important"]), ("习惯", "xíguàn", meaning["habit"]), ("影响", "yǐngxiǎng", meaning["influence"])],
                "quiz": [("重要 = ?", meaning["important"]), ("习惯 = ?", meaning["habit"])],
                "sentence": "好习惯很重要。",
                "sentence_meaning": {
                    "uz": "Yaxshi odat juda muhim.",
                    "ru": "Хорошая привычка очень важна.",
                    "tj": "Одати хуб бисёр муҳим аст.",
                }.get(lang, "Хорошая привычка очень важна."),
            },
            "hsk4": {
                "words": [("虽然", "suīrán", meaning["although"]), ("但是", "dànshì", meaning["but"]), ("解决", "jiějué", meaning["solve"])],
                "quiz": [("虽然 = ?", meaning["although"]), ("解决 = ?", meaning["solve"])],
                "sentence": "虽然很难，但是我会解决。",
                "sentence_meaning": {
                    "uz": "Qiyin bo'lsa ham, men hal qilaman.",
                    "ru": "Хотя это сложно, я решу.",
                    "tj": "Гарчанде душвор аст, ман ҳал мекунам.",
                }.get(lang, "Хотя это сложно, я решу."),
            },
        }
        return level_payloads.get(self._level_key(user), level_payloads["beginner"])

    def _challenge_copy(self, lang: str) -> dict[str, str]:
        copies = {
            "uz": {
                "title_meaning": "💬 <b>Keling, birinchi savoldan boshlaymiz</b>",
                "title_pinyin": "🔊 <b>Talaffuzdan boshlaymiz</b>",
                "title_sentence": "🎮 <b>Kichik mashq</b>",
                "q_meaning": "Bu so'z nima degani?",
                "q_pinyin": "Bu so'z qanday o'qiladi?",
                "q_sentence": "Shu so'zlardan bitta gap tuzing.",
                "hint": "Javobingizni yozing — tekshirib beraman. Yoki o'z savolingizni bering.",
            },
            "ru": {
                "title_meaning": "💬 <b>Давайте начнём с первого вопроса</b>",
                "title_pinyin": "🔊 <b>Начнём с произношения</b>",
                "title_sentence": "🎮 <b>Небольшое упражнение</b>",
                "q_meaning": "Что означает это слово?",
                "q_pinyin": "Как читается это слово?",
                "q_sentence": "Составьте одно предложение из этих слов.",
                "hint": "Напишите ответ — я проверю. Или задайте свой вопрос.",
            },
            "tj": {
                "title_meaning": "💬 <b>Биёед аз саволи аввал сар мекунем</b>",
                "title_pinyin": "🔊 <b>Аз талаффуз сар мекунем</b>",
                "title_sentence": "🎮 <b>Машқи хурд</b>",
                "q_meaning": "Ин калима чӣ маъно дорад?",
                "q_pinyin": "Ин калима чӣ тавр хонда мешавад?",
                "q_sentence": "Аз ин калимаҳо як ҷумла созед.",
                "hint": "Ҷавобатонро нависед — месанҷам. Ё саволи худро диҳед.",
            },
        }
        return copies.get(lang, copies["ru"])

    _CHALLENGE_KINDS = ("meaning", "sentence", "pinyin")

    def first_challenge(self, user, lang: str, seed: int = 0) -> dict[str, str] | None:
        """QA rejimiga kirishda beriladigan ixtiyoriy mini-savol.

        Manba — kurs darslaridagi tayyor `active_words` lug'ati
        (`course_v3_vocab`), ya'ni yangi kontent yozilmaydi.

        `seed` har kirishda o'zgaradi (chaqiruvchi uzatadi), shuning uchun
        bir kunda bir necha marta kirgan user har safar boshqa savol oladi.

        Qaytadi yoki `None` (lug'at topilmasa — chaqiruvchi eski matnga tushadi):
        - `text`: userga ko'rinadigan savol
        - `context`: `qa_service` AI promptiga qo'shiladigan challenge tavsifi
        """
        words = words_for_level(getattr(user, "level", None))
        if not words:
            return None

        base = int(getattr(user, "id", 0) or 0) + int(seed or 0)
        kinds = self._CHALLENGE_KINDS
        total = len(words)
        # So'z har kirishda 7 qadam siljiydi — 7 lug'at hajmi bilan deyarli
        # doim o'zaro tub, shuning uchun butun lug'at aylanadi va ketma-ket
        # kirishlarda bir so'z takrorlanmaydi.
        start = (base * 7) % total
        # Vazifa turi aylanish raqami + so'z o'rnidan hisoblanadi: qo'shni
        # kirishlarda o'rin 7 ga siljigani uchun tur ham har safar o'zgaradi,
        # bir so'z esa har aylanishda boshqa formatda qaytadi. Davr = 3 x hajm.
        kind = kinds[(base // total + start) % len(kinds)]
        copy = self._challenge_copy(lang)
        meaning_lang = lang if lang in ("uz", "ru", "tj") else "ru"

        def pick(offset: int) -> dict:
            return words[(start + offset) % len(words)]

        if kind == "sentence" and len(words) >= 3:
            chosen = [pick(i) for i in range(3)]
            shown = " · ".join(f"<b>{w['zh']}</b>" for w in chosen)
            gloss = "\n".join(
                f"{w['zh']} <i>{w['pinyin']}</i> — {w['meaning'][meaning_lang]}"
                for w in chosen
            )
            text = "\n".join([
                copy["title_sentence"],
                "",
                f"<blockquote>{shown}\n\n{gloss}\n\n{copy['q_sentence']}</blockquote>",
                copy["hint"],
            ])
            listed = ", ".join(
                f"{w['zh']} ({w['pinyin']}) = {w['meaning'][meaning_lang]}" for w in chosen
            )
            context = (
                f"Challenge words: {listed}. "
                "The user was asked to build one sentence using these words."
            )
            return {"text": text, "context": context}

        word = pick(0)
        if kind == "pinyin":
            body = f"<b>{word['zh']}</b>\n{copy['q_pinyin']}"
            title = copy["title_pinyin"]
            context = (
                f"Challenge word: {word['zh']} = {word['meaning'][meaning_lang]}. "
                f"Correct pinyin: {word['pinyin']}. "
                "The user was asked how this word is pronounced."
            )
        else:
            body = f"<b>{word['zh']}</b> <i>{word['pinyin']}</i>\n{copy['q_meaning']}"
            title = copy["title_meaning"]
            context = (
                f"Challenge word: {word['zh']} ({word['pinyin']}). "
                f"Correct meaning in the user's language: {word['meaning'][meaning_lang]}. "
                "The user was asked what this word means."
            )

        text = "\n".join([title, "", f"<blockquote>{body}</blockquote>", copy["hint"]])
        return {"text": text, "context": context}

    def entry_text(self, user, lang: str) -> str:
        copy = self._copy(lang)
        return f"{copy['entry_title']}\n\n{copy['entry_body']}"

    def practice_text(self, user, lang: str) -> str:
        copy = self._copy(lang)
        payload = self._payload(user, lang)
        word_lines = [
            f"• <b>{word}</b> <i>{pinyin}</i> — {meaning}"
            for word, pinyin, meaning in payload["words"]
        ]
        quiz_lines = [
            f"{idx}. {question}"
            for idx, (question, _) in enumerate(payload["quiz"], 1)
        ]
        return "\n".join([
            copy["entry_title"],
            "",
            copy["words"],
            *word_lines,
            "",
            copy["quiz"],
            *quiz_lines,
            "",
            copy["sentence"],
            f"<blockquote><b>{payload['sentence']}</b>\n{payload['sentence_meaning']}</blockquote>",
            copy["ready"],
        ])

    def completion_text(self, user, lang: str) -> str:
        copy = self._copy(lang)
        payload = self._payload(user, lang)
        answer_lines = [
            f"{idx}. {answer}"
            for idx, (_, answer) in enumerate(payload["quiz"], 1)
        ]
        streak = int(getattr(user, "daily_practice_streak", 0) or 0)
        streak_line = {
            "uz": f"🔥 Streak: {streak} kun",
            "ru": f"🔥 Серия: {streak} дн.",
            "tj": f"🔥 Пайдарпай: {streak} рӯз",
        }.get(lang, f"🔥 Серия: {streak} дн.")
        return "\n".join([
            copy["done"],
            "",
            copy["result"],
            "",
            f"{copy['answers']}",
            *answer_lines,
            "",
            streak_line,
            copy["next"],
        ])
