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
        "meaning_hint": "ma'nosi: {meaning}",
        "correct": "To'g'ri javob: {zh} — {meaning}.",
        "grammar_cat": "Grammatika",
        "grammar_hint": "Dars {lesson} grammatikasi",
        "grammar_example_to_pattern": "Quyidagi gapda qaysi grammatika ishlatilgan?\n{example}",
        "grammar_pattern_to_example": "“{title}” grammatikasiga qaysi gap mos?",
        "grammar_correct": "To'g'ri javob: {title}. {rule}",
        "grammar_example_correct": "To'g'ri javob: {example}\nBu gapda {title} ishlatilgan.",
    },
    "ru": {
        "cat": "Слова",
        "hint": "Новые слова урока {lesson}",
        "hanzi_to_meaning": "Что означает “{zh}”?",
        "meaning_to_hanzi": "Какое слово означает “{meaning}”?",
        "pinyin_to_hanzi": "Какое слово читается “{pinyin}”?",
        "hanzi_to_pinyin": "Какой pinyin у “{zh}”?",
        "meaning_hint": "значение: {meaning}",
        "correct": "Правильный ответ: {zh} — {meaning}.",
        "grammar_cat": "Грамматика",
        "grammar_hint": "Грамматика урока {lesson}",
        "grammar_example_to_pattern": "Какая грамматика используется в этом предложении?\n{example}",
        "grammar_pattern_to_example": "Какое предложение подходит к грамматике “{title}”?",
        "grammar_correct": "Правильный ответ: {title}. {rule}",
        "grammar_example_correct": "Правильный ответ: {example}\nВ этом предложении используется {title}.",
    },
    "tj": {
        "cat": "Калимаҳо",
        "hint": "Калимаҳои нави дарси {lesson}",
        "hanzi_to_meaning": "“{zh}” чӣ маъно дорад?",
        "meaning_to_hanzi": "Кадом калима маънои “{meaning}”-ро дорад?",
        "pinyin_to_hanzi": "Кадом калима “{pinyin}” хонда мешавад?",
        "hanzi_to_pinyin": "Pinyin-и “{zh}” кадом аст?",
        "meaning_hint": "маъно: {meaning}",
        "correct": "Ҷавоби дуруст: {zh} — {meaning}.",
        "grammar_cat": "Грамматика",
        "grammar_hint": "Грамматикаи дарси {lesson}",
        "grammar_example_to_pattern": "Дар ин ҷумла кадом грамматика истифода шудааст?\n{example}",
        "grammar_pattern_to_example": "Кадом ҷумла ба грамматикаи “{title}” мувофиқ аст?",
        "grammar_correct": "Ҷавоби дуруст: {title}. {rule}",
        "grammar_example_correct": "Ҷавоби дуруст: {example}\nДар ин ҷумла {title} истифода шудааст.",
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
        wanted = None
        if block and isinstance(block.get("grammar_nos"), list):
            wanted = {int(no) for no in block["grammar_nos"] if str(no).isdigit()}
        items = []
        if isinstance(grammar, list):
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
        if items:
            return items

        if not block or not isinstance(block.get("grammar_notes"), list):
            return []

        for note in block["grammar_notes"]:
            if not isinstance(note, dict):
                continue
            pattern = self._localized(note, lang, "pattern")
            base_pattern = note.get("pattern") or pattern
            explanation = self._localized(note, lang, "explanation")
            examples = []
            if note.get("example_zh"):
                examples.append(
                    {
                        "zh": note.get("example_zh") or "",
                        "pinyin": note.get("example_pinyin") or "",
                        "translation": (
                            note.get(f"example_{lang}")
                            or note.get("example_uz")
                            or note.get("example_ru")
                            or note.get("example_tj")
                            or ""
                        ),
                    }
                )
            items.append(
                {
                    "no": len(items) + 1,
                    "title": pattern,
                    "title_zh": base_pattern,
                    "rule": explanation,
                    "formula": base_pattern,
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

    def _short_rule(self, value: str, limit: int = 130) -> str:
        text = " ".join(str(value or "").split())
        if len(text) <= limit:
            return text
        return f"{text[:limit].rstrip()}..."

    def _option_values(self, answer: str, candidates: list[str], count: int = 3) -> list[str]:
        seen = {answer}
        result = [answer]
        for value in candidates:
            value = str(value or "").strip()
            if not value or value in seen:
                continue
            seen.add(value)
            result.append(value)
            if len(result) >= count + 1:
                break
        return result

    def _first_grammar_example(self, item: dict) -> dict:
        examples = item.get("examples") if isinstance(item.get("examples"), list) else []
        for example in examples:
            if isinstance(example, dict) and example.get("zh"):
                return example
        return {}

    def _word_quiz_questions(self, vocab: list[dict], lesson_order: int, lang: str, block_no: int | None = None) -> list[dict]:
        text = _QUIZ_TEXT[lang]
        questions = []
        meanings = [item["meaning"] for item in vocab]
        hanzis = [item["zh"] for item in vocab]
        pinyins = [item["pinyin"] for item in vocab]
        types = ("hanzi_to_meaning", "meaning_to_hanzi", "pinyin_to_hanzi", "hanzi_to_pinyin")

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
                    continue

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

    def _grammar_quiz_questions(
        self,
        grammar: list[dict],
        grammar_pool: list[dict],
        lesson_order: int,
        lang: str,
        block_no: int | None = None,
    ) -> list[dict]:
        text = _QUIZ_TEXT[lang]
        questions = []

        titles = [
            item.get("title") or item.get("formula") or item.get("title_zh") or ""
            for item in grammar_pool
            if isinstance(item, dict)
        ]
        examples = [
            self._first_grammar_example(item).get("zh") or ""
            for item in grammar_pool
            if isinstance(item, dict)
        ]

        for index, item in enumerate(grammar, 1):
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or item.get("formula") or item.get("title_zh") or "").strip()
            formula = str(item.get("formula") or item.get("title_zh") or title).strip()
            rule = self._short_rule(item.get("rule") or "")
            example = self._first_grammar_example(item)
            example_zh = str(example.get("zh") or "").strip()
            if not title or not example_zh:
                continue

            pattern_options = self._option_values(title, titles)
            if len(pattern_options) >= 2:
                options, answer_index = self._shuffle_options(
                    pattern_options,
                    title,
                    f"grammar-pattern:{lesson_order}:{block_no}:{index}:{lang}",
                )
                questions.append(
                    {
                        "lesson": lesson_order,
                        "block_no": block_no,
                        "type": "grammar_example_to_pattern",
                        "q": text["grammar_example_to_pattern"].format(example=example_zh),
                        "hint": text["grammar_hint"].format(lesson=lesson_order),
                        "cat": text["grammar_cat"],
                        "opts": options,
                        "ans": answer_index,
                        "expl": text["grammar_correct"].format(title=title, rule=rule or formula),
                    }
                )

            example_options = self._option_values(example_zh, examples)
            if len(example_options) >= 2:
                options, answer_index = self._shuffle_options(
                    example_options,
                    example_zh,
                    f"grammar-example:{lesson_order}:{block_no}:{index}:{lang}",
                )
                questions.append(
                    {
                        "lesson": lesson_order,
                        "block_no": block_no,
                        "type": "grammar_pattern_to_example",
                        "q": text["grammar_pattern_to_example"].format(title=title),
                        "hint": text["grammar_hint"].format(lesson=lesson_order),
                        "cat": text["grammar_cat"],
                        "opts": options,
                        "ans": answer_index,
                        "expl": text["grammar_example_correct"].format(example=example_zh, title=title),
                    }
                )
        return questions

    def _quiz_questions(
        self,
        vocab: list[dict],
        grammar: list[dict],
        lesson_grammar: list[dict],
        lesson_order: int,
        lang: str,
        block_no: int | None = None,
    ) -> list[dict]:
        word_questions = self._word_quiz_questions(vocab, lesson_order, lang, block_no)
        grammar_pool = lesson_grammar or grammar
        grammar_questions = self._grammar_quiz_questions(grammar, grammar_pool, lesson_order, lang, block_no)

        target_count = 10
        grammar_target = min(len(grammar_questions), 4)
        questions = grammar_questions[:grammar_target]
        questions.extend(word_questions[: max(0, target_count - len(questions))])

        remaining = word_questions[max(0, target_count - grammar_target):] + grammar_questions[grammar_target:]
        cursor = 0
        while len(questions) < target_count and remaining:
            questions.append(remaining[cursor % len(remaining)])
            cursor += 1

        if len(questions) < target_count:
            filler = word_questions + grammar_questions
            cursor = 0
            while len(questions) < target_count and filler:
                questions.append(dict(filler[cursor % len(filler)]))
                cursor += 1

        result = questions[:target_count]
        scope = str(block_no) if block_no else "all"
        for index, question in enumerate(result, 1):
            question["id"] = f"{lesson_order}:{scope}:{index}"
        return result

    async def get_payload(self, lesson_order: int, lang: str, level: str = "hsk3", block_no: int | None = None) -> dict | None:
        lang = normalize_miniapp_lang(lang)
        level = (level or "hsk3").strip().lower()
        if level not in {"hsk1", "hsk2", "hsk3", "hsk4"}:
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
        lesson_grammar = self._grammar(lesson, lang)
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
            "quiz_questions": self._quiz_questions(
                vocab,
                grammar,
                lesson_grammar,
                lesson.lesson_order,
                lang,
                int(block.get("block_no")) if block else None,
            ),
        }
