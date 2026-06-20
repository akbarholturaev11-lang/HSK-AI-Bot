from datetime import date, datetime, timedelta, timezone


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
