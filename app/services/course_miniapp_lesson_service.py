import json

from sqlalchemy import select

from app.bot.utils.course_miniapp import normalize_miniapp_lang
from app.db.models.course_lessons import CourseLesson


_QUIZ_TEXT = {
    "uz": {
        "cat": "Lug'at",
        "hint": "Dars {lesson} yangi so'zi",
        "hanzi_to_meaning": "“{zh}” nimani anglatadi?",
        "meaning_to_hanzi": "“{meaning}” qaysi so'z?",
        "pinyin_to_hanzi": "“{pinyin}” qaysi so'z?",
        "hanzi_to_pinyin": "“{zh}” pinyin qaysi?",
        "gap_fill": "Gapni to'ldiring: 我今天学习了“____”这个词。",
        "meaning_hint": "ma'nosi: {meaning}",
        "correct": "To'g'ri javob: {zh} — {meaning}.",
    },
    "ru": {
        "cat": "Слова",
        "hint": "Новые слова урока {lesson}",
        "hanzi_to_meaning": "Что означает “{zh}”?",
        "meaning_to_hanzi": "Какое слово означает “{meaning}”?",
        "pinyin_to_hanzi": "Какое слово читается “{pinyin}”?",
        "hanzi_to_pinyin": "Какой pinyin у “{zh}”?",
        "gap_fill": "Заполните пропуск: 我今天学习了“____”这个词。",
        "meaning_hint": "значение: {meaning}",
        "correct": "Правильный ответ: {zh} — {meaning}.",
    },
    "tj": {
        "cat": "Калимаҳо",
        "hint": "Калимаҳои нави дарси {lesson}",
        "hanzi_to_meaning": "“{zh}” чӣ маъно дорад?",
        "meaning_to_hanzi": "Кадом калима маънои “{meaning}”-ро дорад?",
        "pinyin_to_hanzi": "Кадом калима “{pinyin}” хонда мешавад?",
        "hanzi_to_pinyin": "Pinyin-и “{zh}” кадом аст?",
        "gap_fill": "Ҷойи холиро пур кунед: 我今天学习了“____”这个词。",
        "meaning_hint": "маъно: {meaning}",
        "correct": "Ҷавоби дуруст: {zh} — {meaning}.",
    },
}


class CourseMiniAppLessonService:
    def __init__(self, session):
        self.session = session

    def _parse(self, value, default):
        if value is None or value == "":
            return default
        if isinstance(value, (dict, list)):
            return value
        try:
            return json.loads(value)
        except Exception:
            return default

    def _localized(self, item: dict, lang: str, *keys: str, default: str = "") -> str:
        for key in keys:
            localized_key = f"{key}_{lang}"
            if item.get(localized_key):
                return str(item[localized_key])
            if item.get(key):
                return str(item[key])
        for fallback_lang in ("uz", "ru", "tj"):
            for key in keys:
                fallback_key = f"{key}_{fallback_lang}"
                if item.get(fallback_key):
                    return str(item[fallback_key])
        return default

    def _title(self, raw: str, lang: str) -> str:
        data = self._parse(raw, None)
        if isinstance(data, dict):
            return str(data.get("zh") or data.get(lang) or data.get("uz") or raw)
        return raw or ""

    def _dialogue_blocks(self, lesson: CourseLesson) -> list[dict]:
        blocks = self._parse(lesson.dialogue_json, [])
        if not isinstance(blocks, list):
            return []
        return [block for block in blocks if isinstance(block, dict) and block.get("block_no")]

    def _block_by_no(self, lesson: CourseLesson, block_no: int | None) -> dict | None:
        if not block_no:
            return None
        for block in self._dialogue_blocks(lesson):
            if int(block.get("block_no") or 0) == int(block_no):
                return block
        return None

    def _vocabulary(self, lesson: CourseLesson, lang: str, block: dict | None = None) -> list[dict]:
        vocab = self._parse(lesson.vocabulary_json, [])
        if not isinstance(vocab, list):
            return []
        wanted = None
        if block and isinstance(block.get("word_nos"), list):
            wanted = {int(no) for no in block["word_nos"] if str(no).isdigit()}
        items = []
        for index, item in enumerate(vocab, 1):
            if not isinstance(item, dict):
                continue
            item_no = int(item.get("no") or index)
            if wanted is not None and item_no not in wanted:
                continue
            meaning = (
                item.get(lang)
                or item.get("uz")
                or item.get("ru")
                or item.get("tj")
                or item.get("meaning")
                or ""
            )
            items.append(
                {
                    "no": item.get("no"),
                    "zh": item.get("zh") or "",
                    "pinyin": item.get("pinyin") or item.get("p") or "",
                    "pos": item.get("pos") or "",
                    "meaning": meaning,
                }
            )
        return items

    def _grammar(self, lesson: CourseLesson, lang: str, block: dict | None = None) -> list[dict]:
        grammar = self._parse(lesson.grammar_json, [])
        if not isinstance(grammar, list):
            return []
        wanted = None
        if block and isinstance(block.get("grammar_nos"), list):
            wanted = {int(no) for no in block["grammar_nos"] if str(no).isdigit()}
        items = []
        for index, item in enumerate(grammar, 1):
            if not isinstance(item, dict):
                continue
            item_no = int(item.get("no") or index)
            if wanted is not None and item_no not in wanted:
                continue
            examples = []
            for example in item.get("examples", []) if isinstance(item.get("examples"), list) else []:
                if not isinstance(example, dict):
                    continue
                examples.append(
                    {
                        "zh": example.get("zh") or "",
                        "pinyin": example.get("pinyin") or "",
                        "translation": example.get(lang) or example.get("uz") or example.get("ru") or example.get("tj") or "",
                    }
                )
            items.append(
                {
                    "no": item_no,
                    "title": self._localized(item, lang, "title", default=item.get("title_zh") or ""),
                    "title_zh": item.get("title_zh") or "",
                    "rule": self._localized(item, lang, "rule"),
                    "formula": item.get("formula") or item.get("pattern") or item.get("title_zh") or "",
                    "examples": examples,
                }
            )
        return items

    def _homework(self, lesson: CourseLesson, lang: str) -> list[dict]:
        homework = self._parse(lesson.homework_json, [])
        if not isinstance(homework, list):
            return []
        tasks = []
        for index, item in enumerate(homework, 1):
            if not isinstance(item, dict):
                tasks.append({"title": f"{index}", "instruction": str(item), "words": [], "topic": ""})
                continue
            tasks.append(
                {
                    "title": str(index),
                    "instruction": self._localized(item, lang, "instruction"),
                    "words": item.get("words") if isinstance(item.get("words"), list) else [],
                    "topic": self._localized(item, lang, "topic"),
                    "example": item.get("example") or "",
                }
            )
        return tasks

    def _distractors(self, values: list[str], answer: str, count: int = 3) -> list[str]:
        seen = {answer}
        result = []
        for value in values:
            if not value or value in seen:
                continue
            seen.add(value)
            result.append(value)
            if len(result) >= count:
                break
        return result

    def _shuffle_options(self, options: list[str], answer: str, seed: str) -> tuple[list[str], int]:
        items = list(options)
        if len(items) <= 1:
            return items, 0

        value = sum((index + 1) * ord(char) for index, char in enumerate(seed))
        for index in range(len(items) - 1, 0, -1):
            swap_index = value % (index + 1)
            items[index], items[swap_index] = items[swap_index], items[index]
            value = (value * 31 + index) % 1_000_003
        return items, items.index(answer) if answer in items else 0

    def _quiz_questions(self, vocab: list[dict], lesson_order: int, lang: str, block_no: int | None = None) -> list[dict]:
        text = _QUIZ_TEXT[lang]
        questions = []
        meanings = [item["meaning"] for item in vocab]
        hanzis = [item["zh"] for item in vocab]
        pinyins = [item["pinyin"] for item in vocab]
        types = ("hanzi_to_meaning", "meaning_to_hanzi", "pinyin_to_hanzi", "hanzi_to_pinyin", "gap_fill")

        for word in vocab:
            zh = word["zh"]
            pinyin = word["pinyin"]
            meaning = word["meaning"]
            if not zh or not meaning:
                continue

            for question_type in types:
                if question_type == "hanzi_to_meaning":
                    answer = meaning
                    options = [answer] + self._distractors(meanings, answer)
                    question = text[question_type].format(zh=zh, meaning=meaning, pinyin=pinyin)
                    hint = text["hint"].format(lesson=lesson_order)
                elif question_type == "meaning_to_hanzi":
                    answer = zh
                    options = [answer] + self._distractors(hanzis, answer)
                    question = text[question_type].format(zh=zh, meaning=meaning, pinyin=pinyin)
                    hint = text["hint"].format(lesson=lesson_order)
                elif question_type == "pinyin_to_hanzi":
                    answer = zh
                    options = [answer] + self._distractors(hanzis, answer)
                    question = text[question_type].format(zh=zh, meaning=meaning, pinyin=pinyin)
                    hint = text["hint"].format(lesson=lesson_order)
                elif question_type == "hanzi_to_pinyin":
                    answer = pinyin
                    options = [answer] + self._distractors(pinyins, answer)
                    question = text[question_type].format(zh=zh, meaning=meaning, pinyin=pinyin)
                    hint = text["hint"].format(lesson=lesson_order)
                else:
                    answer = zh
                    options = [answer] + self._distractors(hanzis, answer)
                    question = text[question_type].format(zh=zh, meaning=meaning, pinyin=pinyin)
                    hint = f"{text['hint'].format(lesson=lesson_order)} · {text['meaning_hint'].format(meaning=meaning)}"

                options, answer_index = self._shuffle_options(options, answer, f"{zh}:{question_type}:{lang}")
                questions.append(
                    {
                        "lesson": lesson_order,
                        "block_no": block_no,
                        "type": question_type,
                        "q": question,
                        "hint": hint,
                        "cat": text["cat"],
                        "opts": options,
                        "ans": answer_index,
                        "expl": text["correct"].format(zh=zh, meaning=meaning, pinyin=pinyin),
                    }
                )
        return questions

    async def get_payload(self, lesson_order: int, lang: str, level: str = "hsk3", block_no: int | None = None) -> dict | None:
        lang = normalize_miniapp_lang(lang)
        level = (level or "hsk3").strip().lower()
        if level not in {"hsk1", "hsk2", "hsk3"}:
            level = "hsk3"
        result = await self.session.execute(
            select(CourseLesson)
            .where(CourseLesson.level == level)
            .where(CourseLesson.lesson_order == lesson_order)
            .where(CourseLesson.is_active.is_(True))
            .limit(1)
        )
        lesson = result.scalar_one_or_none()
        if not lesson:
            return None

        block = self._block_by_no(lesson, block_no)
        vocab = self._vocabulary(lesson, lang, block)
        grammar = self._grammar(lesson, lang, block)
        homework = self._homework(lesson, lang)
        return {
            "lesson_id": lesson.lesson_order,
            "lesson_code": lesson.lesson_code,
            "level": level,
            "block_no": int(block.get("block_no")) if block else None,
            "lang": lang,
            "title": self._title(lesson.title, lang),
            "vocabulary": vocab,
            "grammar": grammar,
            "homework": homework,
            "quiz_questions": self._quiz_questions(vocab, lesson.lesson_order, lang, int(block.get("block_no")) if block else None),
        }
