import json

from sqlalchemy import select

from app.bot.utils.course_miniapp import normalize_miniapp_lang
from app.db.models.course_lessons import CourseLesson
from app.repositories.course_pilot_event_repo import is_course_pilot_lesson


_QUIZ_TEXT = {
    "uz": {
        "cat": "Lug'at",
        "hint": "Dars {lesson} yangi so'zi",
        "hanzi_to_meaning": "“{zh}” nimani anglatadi?",
        "meaning_to_hanzi": "“{meaning}” qaysi so'z?",
        "pinyin_to_hanzi": "“{pinyin}” qaysi so'z?",
        "hanzi_to_pinyin": "“{zh}” pinyin qaysi?",
        "listening_choice": "Eshiting va to'g'ri javobni tanlang",
        "fill_blank": "Bo'sh joyni to'ldiring",
        "fill_blank_choice": "Gapdagi bo'sh joyga mos so'zni tanlang",
        "choose_meaning_in_context": "Gapdagi so'z ma'nosini tanlang",
        "grammar_in_context": "Gapdagi grammatikani tanlang",
        "listen_and_fill": "Eshiting va bo'sh joyni to'ldiring",
        "build_sentence_chips": "Xitoycha gapni tuzing",
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
        "listening_choice": "Послушайте и выберите правильный ответ",
        "fill_blank": "Заполните пропуск",
        "fill_blank_choice": "Выберите слово для пропуска в предложении",
        "choose_meaning_in_context": "Выберите значение слова в предложении",
        "grammar_in_context": "Выберите грамматику в предложении",
        "listen_and_fill": "Послушайте и заполните пропуск",
        "build_sentence_chips": "Соберите китайское предложение",
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
        "listening_choice": "Гӯш кунед ва ҷавоби дурустро интихоб кунед",
        "fill_blank": "Ҷои холиро пур кунед",
        "fill_blank_choice": "Калимаи мувофиқро барои ҷои холии ҷумла интихоб кунед",
        "choose_meaning_in_context": "Маънои калимаро дар ҷумла интихоб кунед",
        "grammar_in_context": "Грамматикаро дар ҷумла интихоб кунед",
        "listen_and_fill": "Гӯш кунед ва ҷои холиро пур кунед",
        "build_sentence_chips": "Ҷумлаи чиниро созед",
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

    def _first_sentence_pair(self, grammar: list[dict]) -> tuple[str, str]:
        for item in grammar:
            if not isinstance(item, dict):
                continue
            example = self._first_grammar_example(item)
            zh = str(example.get("zh") or "").strip()
            translation = str(example.get("translation") or "").strip()
            if zh and translation:
                return zh, translation
        return "", ""

    def _order_tokens(self, value: str, *, chinese: bool = False) -> list[str]:
        text = str(value or "").strip()
        if not text:
            return []
        if chinese:
            tokens = []
            current = ""
            for char in text:
                if char.isspace():
                    if current:
                        tokens.append(current)
                        current = ""
                    continue
                if "\u4e00" <= char <= "\u9fff":
                    if current:
                        tokens.append(current)
                        current = ""
                    tokens.append(char)
                    continue
                if char in "，。！？,.!?;；:：":
                    if current:
                        tokens.append(current)
                        current = ""
                    continue
                current += char
            if current:
                tokens.append(current)
            return tokens

        cleaned = (
            text.replace(".", "")
            .replace(",", "")
            .replace("?", "")
            .replace("!", "")
            .replace(";", "")
            .replace(":", "")
        )
        return [part.strip() for part in cleaned.split() if part.strip()]

    def _shuffled_tokens(self, tokens: list[str], seed: str) -> list[str]:
        if len(tokens) <= 1:
            return tokens
        shuffled, _ = self._shuffle_options(tokens, tokens[0], seed)
        if shuffled == tokens:
            return [*tokens[1:], tokens[0]]
        return shuffled

    def _sample_options(self, answer: str, candidates: list[str], seed: str, count: int = 4) -> tuple[list[str], int]:
        options = self._option_values(answer, candidates, count=count - 1)
        return self._shuffle_options(options, answer, seed)

    def _sentence_pairs(self, grammar: list[dict]) -> list[tuple[str, str]]:
        pairs: list[tuple[str, str]] = []
        for item in grammar:
            if not isinstance(item, dict):
                continue
            for example in item.get("examples") if isinstance(item.get("examples"), list) else []:
                if not isinstance(example, dict):
                    continue
                sentence = str(example.get("zh") or "").strip()
                translation = str(example.get("translation") or "").strip()
                if sentence and translation:
                    pairs.append((sentence, translation))
        return pairs

    @staticmethod
    def _blank_sentence(sentence: str, target: str) -> str:
        sentence = str(sentence or "").strip()
        target = str(target or "").strip()
        if len(target) < 2 or not sentence or sentence.count(target) != 1:
            return ""
        blanked = sentence.replace(target, "____", 1)
        return blanked if blanked != sentence and "____" in blanked else ""

    @staticmethod
    def _highlight_sentence(sentence: str, target: str) -> str:
        sentence = str(sentence or "").strip()
        target = str(target or "").strip()
        if not sentence or not target or target not in sentence:
            return sentence
        return sentence.replace(target, f"【{target}】", 1)

    def _sentence_word_candidates(
        self,
        vocab: list[dict],
        sentence_pairs: list[tuple[str, str]],
    ) -> list[tuple[dict, str, str]]:
        candidates: list[tuple[dict, str, str]] = []
        for sentence, translation in sentence_pairs:
            for word in vocab:
                zh = str(word.get("zh") or "").strip()
                if len(zh) >= 2 and zh in sentence:
                    candidates.append((word, sentence, translation))
        return candidates

    def _chinese_sentence_chips(self, sentence: str, vocab: list[dict]) -> list[str]:
        sentence = str(sentence or "").strip()
        if not sentence:
            return []
        remaining = sentence
        tokens: list[str] = []
        vocab_words = sorted(
            [str(item.get("zh") or "").strip() for item in vocab if str(item.get("zh") or "").strip()],
            key=len,
            reverse=True,
        )
        while remaining:
            if remaining[0] in "，。！？,.!?;；:：":
                remaining = remaining[1:]
                continue
            match = next((word for word in vocab_words if remaining.startswith(word)), "")
            if match:
                tokens.append(match)
                remaining = remaining[len(match) :]
                continue
            char = remaining[0]
            if "\u4e00" <= char <= "\u9fff":
                tokens.append(char)
            remaining = remaining[1:]
        return tokens

    def _choice_payload(
        self,
        *,
        question_type: str,
        lesson_order: int,
        block_no: int | None,
        prompt: str,
        answer: str,
        options: list[str],
        seed: str,
        explanation: str,
        cat: str,
        sentence: str = "",
        target: str = "",
        word: str = "",
        source: str = "",
        audioText: str = "",
    ) -> dict | None:
        answer = str(answer or "").strip()
        if not answer:
            return None
        option_values = [str(item or "").strip() for item in options if str(item or "").strip()]
        option_values = list(dict.fromkeys(option_values))
        if answer not in option_values:
            option_values.insert(0, answer)
        if len(option_values) < 2:
            return None
        shuffled, answer_index = self._shuffle_options(option_values[:4], answer, seed)
        return {
            "lesson": lesson_order,
            "block_no": block_no,
            "type": question_type,
            "subtype": question_type,
            "q": prompt,
            "prompt": prompt,
            "cat": cat,
            "opts": shuffled,
            "ans": answer_index,
            "expl": explanation,
            "explanation": explanation,
            "sentence": sentence,
            "target": target,
            "word": word,
            "source": source,
            "audioText": audioText,
        }

    def _pilot_experience(self, *, lesson: CourseLesson, lang: str, title: str) -> dict:
        lesson_order = int(getattr(lesson, "lesson_order", 0) or 0)
        variant = {
            1: "word_game",
            2: "roleplay",
            3: "sentence_builder",
        }.get(lesson_order, "word_game")
        copy = {
            "uz": {
                "start": "Start",
                "learn": "Learn",
                "practice": "Practice",
                "explain": "AI Explain",
                "win": "Win",
                "next": "Next",
                "today": "Bugun qisqa dars: {title}",
                "promise": "3-5 minutda bitta aniq natija olasiz.",
                "win_text": "Bugun asosiy so'z/qoida va bitta amaliy mashqni tugatdingiz.",
                "next_text": "Keyingi darsda shu bilimni yangi vaziyatda ishlatasiz.",
            },
            "ru": {
                "start": "Start",
                "learn": "Learn",
                "practice": "Practice",
                "explain": "AI Explain",
                "win": "Win",
                "next": "Next",
                "today": "Сегодня короткий урок: {title}",
                "promise": "За 3-5 минут получите один понятный результат.",
                "win_text": "Сегодня вы закрепили ключевое слово/правило и одну практику.",
                "next_text": "В следующем уроке вы примените это в новой ситуации.",
            },
            "tj": {
                "start": "Start",
                "learn": "Learn",
                "practice": "Practice",
                "explain": "AI Explain",
                "win": "Win",
                "next": "Next",
                "today": "Имрӯз дарси кӯтоҳ: {title}",
                "promise": "Дар 3-5 дақиқа як натиҷаи равшан мегиред.",
                "win_text": "Имрӯз калима/қоидаи асосӣ ва як машқи амалӣ анҷом шуд.",
                "next_text": "Дар дарси навбатӣ инро дар вазъияти нав истифода мебаред.",
            },
        }.get(lang, {})
        return {
            "pilot": True,
            "variant": variant,
            "skeleton": [
                copy.get("start", "Start"),
                copy.get("learn", "Learn"),
                copy.get("practice", "Practice"),
                copy.get("explain", "AI Explain"),
                copy.get("win", "Win"),
                copy.get("next", "Next"),
            ],
            "today": copy.get("today", "{title}").format(title=title),
            "promise": copy.get("promise", ""),
            "win_text": copy.get("win_text", ""),
            "next_text": copy.get("next_text", ""),
        }

    def _pilot_vocab(self, vocab: list[dict]) -> list[dict]:
        return [item for item in vocab if item.get("zh") and item.get("meaning")][:5]

    def _pilot_grammar(self, grammar: list[dict]) -> list[dict]:
        return [item for item in grammar if item.get("title") or item.get("rule")][:1]

    def _pilot_reinforcement_tasks(
        self,
        *,
        lesson: CourseLesson,
        vocab: list[dict],
        grammar: list[dict],
        lesson_grammar: list[dict],
        lang: str,
    ) -> list[dict]:
        lesson_order = int(getattr(lesson, "lesson_order", 0) or 0)
        base_tasks = self._reinforcement_tasks(
            vocab,
            grammar or lesson_grammar,
            lesson_order,
            lang,
        )
        if lesson_order == 1:
            priority = {"match_pairs": 0, "listening_choice": 1, "stroke_preview": 2}
        elif lesson_order == 2:
            priority = {"build_chinese_sentence": 0, "word_order": 1, "match_pairs": 2}
        else:
            priority = {"build_chinese_sentence": 0, "listening_choice": 1, "word_order": 2, "match_pairs": 3}
        return sorted(base_tasks, key=lambda item: priority.get(str(item.get("type") or ""), 9))[:3]

    def _reinforcement_tasks(
        self,
        vocab: list[dict],
        grammar: list[dict],
        lesson_order: int,
        lang: str,
        block_no: int | None = None,
    ) -> list[dict]:
        tasks: list[dict] = []
        zh_sentence, translated_sentence = self._first_sentence_pair(grammar)
        scope = str(block_no) if block_no else "all"

        answer_tokens = self._order_tokens(translated_sentence)
        if zh_sentence and len(answer_tokens) >= 2:
            tasks.append(
                {
                    "id": f"{lesson_order}:{scope}:reinforce:1",
                    "type": "word_order",
                    "prompt": {
                        "uz": "Tarjimani so'zlardan tuzing",
                        "ru": "Соберите перевод из слов",
                        "tj": "Тарҷумаро аз калимаҳо созед",
                    }.get(lang, "Tarjimani so'zlardan tuzing"),
                    "source": zh_sentence,
                    "tokens": self._shuffled_tokens(answer_tokens, f"wo:{lesson_order}:{scope}:{lang}"),
                    "answer": answer_tokens,
                    "explanation": f"{zh_sentence} = {translated_sentence}",
                }
            )

        pair_words = [item for item in vocab if item.get("zh") and item.get("meaning")][:3]
        if len(pair_words) >= 2:
            pairs = [[item["zh"], item["meaning"]] for item in pair_words]
            tasks.append(
                {
                    "id": f"{lesson_order}:{scope}:reinforce:2",
                    "type": "match_pairs",
                    "prompt": {
                        "uz": "Mos juftliklarni toping",
                        "ru": "Найдите пары",
                        "tj": "Ҷуфтҳои мувофиқро ёбед",
                    }.get(lang, "Mos juftliklarni toping"),
                    "pairs": pairs,
                    "explanation": " · ".join(f"{left} = {right}" for left, right in pairs),
                }
            )

        listening_word = next((item for item in vocab if item.get("zh") and item.get("meaning")), None)
        if listening_word:
            hanzis = [item["zh"] for item in vocab if item.get("zh")]
            options, answer_index = self._sample_options(
                listening_word["zh"],
                hanzis,
                f"listen:{lesson_order}:{scope}:{lang}",
            )
            if len(options) >= 2:
                tasks.append(
                    {
                        "id": f"{lesson_order}:{scope}:reinforce:3",
                        "type": "listening_choice",
                        "prompt": _QUIZ_TEXT[lang]["listening_choice"],
                        "audioText": listening_word["zh"],
                        "options": options,
                        "answer": listening_word["zh"],
                        "ans": answer_index,
                        "explanation": f"{listening_word['zh']} = {listening_word['meaning']}",
                    }
                )

        stroke_word = next((item for item in vocab if item.get("zh") and any("\u4e00" <= char <= "\u9fff" for char in item.get("zh", ""))), None)
        if stroke_word:
            tasks.append(
                {
                    "id": f"{lesson_order}:{scope}:reinforce:4",
                    "type": "stroke_preview",
                    "prompt": {
                        "uz": "Iyeroglif shaklini ko'ring",
                        "ru": "Посмотрите форму иероглифа",
                        "tj": "Шакли иероглифро бинед",
                    }.get(lang, "Iyeroglif shaklini ko'ring"),
                    "chars": [char for char in stroke_word["zh"] if "\u4e00" <= char <= "\u9fff"],
                    "word": stroke_word["zh"],
                    "pinyin": stroke_word.get("pinyin") or "",
                    "meaning": stroke_word.get("meaning") or "",
                    "answer": "seen",
                    "explanation": f"{stroke_word['zh']} · {stroke_word.get('pinyin') or ''} · {stroke_word.get('meaning') or ''}",
                }
            )

        if len(tasks) < 3 and zh_sentence:
            chinese_tokens = self._order_tokens(zh_sentence, chinese=True)
            if len(chinese_tokens) >= 2:
                tasks.insert(
                    0,
                    {
                        "id": f"{lesson_order}:{scope}:reinforce:0",
                        "type": "build_chinese_sentence",
                        "prompt": {
                            "uz": f"Xitoycha gapni tuzing: {translated_sentence}",
                            "ru": f"Соберите китайское предложение: {translated_sentence}",
                            "tj": f"Ҷумлаи чиниро созед: {translated_sentence}",
                        }.get(lang, f"Xitoycha gapni tuzing: {translated_sentence}"),
                        "tokens": self._shuffled_tokens(chinese_tokens, f"zh:{lesson_order}:{scope}:{lang}"),
                        "answer": chinese_tokens,
                        "explanation": zh_sentence,
                    },
                )

        return tasks[:4]

    def _unique_questions(self, questions: list[dict]) -> list[dict]:
        seen = set()
        unique = []
        for question in questions:
            if not isinstance(question, dict):
                continue
            key = (
                str(question.get("type") or ""),
                str(question.get("q") or question.get("prompt") or ""),
                str(question.get("sentence") or question.get("source") or ""),
                str(question.get("target") or question.get("word") or ""),
                json.dumps(question.get("answer") or question.get("ans") or "", ensure_ascii=False),
            )
            if key in seen:
                continue
            seen.add(key)
            unique.append(question)
        return unique

    def _word_quiz_questions(self, vocab: list[dict], lesson_order: int, lang: str, block_no: int | None = None) -> list[dict]:
        text = _QUIZ_TEXT[lang]
        questions = []
        meanings = [item["meaning"] for item in vocab]
        hanzis = [item["zh"] for item in vocab]
        pinyins = [item["pinyin"] for item in vocab]
        types = ("hanzi_to_meaning", "meaning_to_hanzi", "pinyin_to_hanzi", "hanzi_to_pinyin")

        def build_question(word: dict, question_type: str) -> dict | None:
            zh = word["zh"]
            pinyin = word["pinyin"]
            meaning = word["meaning"]
            if not zh or not meaning:
                return None

            ui_type = "multiple_choice"
            sentence = ""
            audio_text = ""

            if question_type == "hanzi_to_meaning":
                answer = meaning
                options = [answer] + self._distractors(meanings, answer)
                question = text[question_type].format(zh=zh, meaning=meaning, pinyin=pinyin)
            elif question_type == "meaning_to_hanzi":
                answer = zh
                options = [answer] + self._distractors(hanzis, answer)
                question = text[question_type].format(zh=zh, meaning=meaning, pinyin=pinyin)
            elif question_type == "pinyin_to_hanzi":
                if not pinyin:
                    return None
                ui_type = "listening_choice"
                audio_text = zh
                answer = zh
                options = [answer] + self._distractors(hanzis, answer)
                question = text["listening_choice"]
            elif question_type == "hanzi_to_pinyin":
                if not pinyin:
                    return None
                answer = pinyin
                options = [answer] + self._distractors(pinyins, answer)
                question = text[question_type].format(zh=zh, meaning=meaning, pinyin=pinyin)
            else:
                return None

            options = list(dict.fromkeys(value for value in options if value))
            if len(options) < 2:
                return None

            options, answer_index = self._shuffle_options(options, answer, f"{zh}:{question_type}:{lang}")
            return {
                "lesson": lesson_order,
                "block_no": block_no,
                "type": ui_type,
                "subtype": question_type,
                "word": zh,
                "q": question,
                "hint": text["hint"].format(lesson=lesson_order),
                "cat": text["cat"],
                "opts": options,
                "ans": answer_index,
                "expl": text["correct"].format(zh=zh, meaning=meaning, pinyin=pinyin),
                "audioText": audio_text,
                "sentence": sentence,
            }

        for pass_index in range(len(types)):
            for word_index, word in enumerate(vocab):
                question_type = types[(word_index + pass_index) % len(types)]
                question = build_question(word, question_type)
                if question:
                    questions.append(question)
        return self._unique_questions(questions)

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

    def _interactive_quiz_questions(
        self,
        vocab: list[dict],
        grammar: list[dict],
        grammar_pool: list[dict],
        lesson_order: int,
        lang: str,
        block_no: int | None = None,
    ) -> list[dict]:
        text = _QUIZ_TEXT[lang]
        questions: list[dict] = []
        scope = str(block_no) if block_no else "all"
        sentence_pairs = self._sentence_pairs(grammar or grammar_pool)
        sentence_candidates = self._sentence_word_candidates(vocab, sentence_pairs)
        hanzis = [item["zh"] for item in vocab if item.get("zh")]
        meanings = [item["meaning"] for item in vocab if item.get("meaning")]

        if sentence_candidates:
            word, sentence, translation = sentence_candidates[0]
            blank_sentence = self._blank_sentence(sentence, word["zh"])
            if blank_sentence:
                question = self._choice_payload(
                    question_type="fill_blank_choice",
                    lesson_order=lesson_order,
                    block_no=block_no,
                    prompt=text["fill_blank_choice"],
                    answer=word["zh"],
                    options=self._option_values(word["zh"], hanzis),
                    seed=f"fill:{lesson_order}:{scope}:{lang}:{word['zh']}",
                    explanation=f"{sentence} = {translation or word['meaning']}",
                    cat=text["cat"],
                    sentence=blank_sentence,
                    target=word["zh"],
                    word=word["zh"],
                )
                if question:
                    questions.append(question)

        if sentence_candidates:
            word, sentence, translation = sentence_candidates[min(1, len(sentence_candidates) - 1)]
            question = self._choice_payload(
                question_type="choose_meaning_in_context",
                lesson_order=lesson_order,
                block_no=block_no,
                prompt=text["choose_meaning_in_context"],
                answer=word["meaning"],
                options=self._option_values(word["meaning"], meanings),
                seed=f"meaning-context:{lesson_order}:{scope}:{lang}:{word['zh']}",
                explanation=f"{word['zh']} = {word['meaning']}",
                cat=text["cat"],
                sentence=self._highlight_sentence(sentence, word["zh"]),
                target=word["zh"],
                word=word["zh"],
                source=translation,
            )
            if question:
                questions.append(question)

        grammar_items = [item for item in grammar if isinstance(item, dict)]
        grammar_titles = [
            str(item.get("title") or item.get("formula") or item.get("title_zh") or "").strip()
            for item in (grammar_pool or grammar_items)
            if isinstance(item, dict)
        ]
        for index, item in enumerate(grammar_items, 1):
            title = str(item.get("title") or item.get("formula") or item.get("title_zh") or "").strip()
            target = str(item.get("title_zh") or item.get("formula") or "").strip()
            example = self._first_grammar_example(item)
            example_zh = str(example.get("zh") or "").strip()
            if title and target and example_zh and target in example_zh:
                question = self._choice_payload(
                    question_type="grammar_in_context",
                    lesson_order=lesson_order,
                    block_no=block_no,
                    prompt=text["grammar_in_context"],
                    answer=title,
                    options=self._option_values(title, grammar_titles),
                    seed=f"grammar-context:{lesson_order}:{scope}:{lang}:{index}",
                    explanation=text["grammar_correct"].format(title=title, rule=self._short_rule(item.get("rule") or target)),
                    cat=text["grammar_cat"],
                    sentence=self._highlight_sentence(example_zh, target),
                    target=target,
                    source=str(example.get("translation") or ""),
                )
                if question:
                    questions.append(question)
                    break

        if sentence_candidates:
            word, sentence, translation = sentence_candidates[min(2, len(sentence_candidates) - 1)]
            blank_sentence = self._blank_sentence(sentence, word["zh"])
            if blank_sentence:
                question = self._choice_payload(
                    question_type="listen_and_fill",
                    lesson_order=lesson_order,
                    block_no=block_no,
                    prompt=text["listen_and_fill"],
                    answer=word["zh"],
                    options=self._option_values(word["zh"], hanzis),
                    seed=f"listen-fill:{lesson_order}:{scope}:{lang}:{word['zh']}",
                    explanation=f"{sentence} = {translation or word['meaning']}",
                    cat=text["cat"],
                    sentence=blank_sentence,
                    target=word["zh"],
                    audioText=word["zh"],
                    word=word["zh"],
                )
                if question:
                    questions.append(question)

        for sentence, translation in sentence_pairs:
            tokens = self._chinese_sentence_chips(sentence, vocab)
            if len(tokens) >= 2 and translation:
                questions.append(
                    {
                        "lesson": lesson_order,
                        "block_no": block_no,
                        "type": "build_sentence_chips",
                        "q": text["build_sentence_chips"],
                        "prompt": text["build_sentence_chips"],
                        "cat": text["cat"],
                        "translation": translation,
                        "source": translation,
                        "tokens": self._shuffled_tokens(tokens, f"quiz-build:{lesson_order}:{scope}:{lang}"),
                        "answer": tokens,
                        "expl": f"{sentence} = {translation}",
                        "explanation": f"{sentence} = {translation}",
                    }
                )
                break

        return self._unique_questions(questions)

    def _quiz_questions(
        self,
        vocab: list[dict],
        grammar: list[dict],
        lesson_grammar: list[dict],
        lesson_order: int,
        lang: str,
        block_no: int | None = None,
        target_count: int = 5,
    ) -> list[dict]:
        word_questions = self._word_quiz_questions(vocab, lesson_order, lang, block_no)
        grammar_pool = lesson_grammar or grammar
        grammar_questions = self._unique_questions(
            self._grammar_quiz_questions(grammar, grammar_pool, lesson_order, lang, block_no)
        )
        try:
            interactive_questions = self._interactive_quiz_questions(
                vocab,
                grammar,
                grammar_pool,
                lesson_order,
                lang,
                block_no,
            )
        except Exception:
            interactive_questions = []

        grammar_target = min(len(grammar_questions), 1 if block_no or target_count < 5 else 2)
        word_target = max(0, target_count - grammar_target)
        pool = self._unique_questions([*interactive_questions, *word_questions, *grammar_questions])
        result: list[dict] = []

        def take(type_names: tuple[str, ...]) -> None:
            if len(result) >= target_count:
                return
            used = {id(item) for item in result}
            for question in pool:
                if id(question) in used:
                    continue
                if str(question.get("type") or "") in type_names:
                    result.append(question)
                    return

        take(("fill_blank_choice", "tap_missing_word"))
        take(("choose_meaning_in_context", "grammar_in_context"))
        take(("listen_and_fill", "listening_choice"))
        take(("build_sentence_chips", "build_chinese_sentence", "word_order"))
        take(("multiple_choice", "grammar_example_to_pattern", "grammar_pattern_to_example"))

        for question in pool:
            if len(result) >= target_count:
                break
            if question not in result:
                result = self._unique_questions([*result, question])

        if len(result) < target_count:
            filler = word_questions + grammar_questions
            for question in filler:
                if len(result) >= target_count:
                    break
                result = self._unique_questions([*result, dict(question)])

        result = result[:target_count]
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
        title = self._title(lesson.title, lang)
        pilot = is_course_pilot_lesson(level, lesson.lesson_order)
        if pilot:
            vocab = self._pilot_vocab(vocab)
            grammar = self._pilot_grammar(grammar or lesson_grammar)
            quiz_target_count = 3 if lesson.lesson_order == 1 else 4
            reinforcement_tasks = self._pilot_reinforcement_tasks(
                lesson=lesson,
                vocab=vocab,
                grammar=grammar,
                lesson_grammar=lesson_grammar,
                lang=lang,
            )
            experience = self._pilot_experience(lesson=lesson, lang=lang, title=title)
        else:
            quiz_target_count = 5
            reinforcement_tasks = self._reinforcement_tasks(
                vocab,
                grammar or lesson_grammar,
                lesson.lesson_order,
                lang,
                int(block.get("block_no")) if block else None,
            )
            experience = None

        quiz_questions = self._quiz_questions(
            vocab,
            grammar,
            lesson_grammar,
            lesson.lesson_order,
            lang,
            int(block.get("block_no")) if block else None,
            target_count=quiz_target_count,
        )
        return {
            "lesson_id": lesson.lesson_order,
            "lesson_code": lesson.lesson_code,
            "level": level,
            "block_no": int(block.get("block_no")) if block else None,
            "lang": lang,
            "title": title,
            "experience": experience,
            "vocabulary": vocab,
            "grammar": grammar,
            "homework": homework,
            "quiz_questions": quiz_questions,
            "reinforcement_tasks": reinforcement_tasks,
        }
