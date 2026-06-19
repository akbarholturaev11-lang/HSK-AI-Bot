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
        "listening_choice": "Eshiting va to'g'ri javobni tanlang",
        "fill_blank": "Bo'sh joyni to'ldiring",
        "fill_blank_sentence": "Men bugun ____ so'zini o'rgandim.",
        "fill_blank_choice": "Bo'sh joyni to'ldiring",
        "tap_missing_word": "Yetishmayotgan so'zni tanlang",
        "build_sentence_chips": "Gapni to'g'ri tartiblang",
        "choose_meaning_in_context": "Ajratilgan so'z nimani anglatadi?",
        "grammar_in_context": "Ajratilgan qism qanday ma'no beradi?",
        "listen_and_fill": "Eshiting va tanlang",
        "odd_one_out": "Mos kelmaydiganini toping",
        "quick_match": "Mos juftlikni toping",
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
        "fill_blank_sentence": "Сегодня я выучил слово ____.",
        "fill_blank_choice": "Заполните пропуск",
        "tap_missing_word": "Выберите пропущенное слово",
        "build_sentence_chips": "Расставьте слова по порядку",
        "choose_meaning_in_context": "Что означает выделенное слово?",
        "grammar_in_context": "Что означает выделенная часть?",
        "listen_and_fill": "Послушайте и выберите",
        "odd_one_out": "Найдите лишнее слово",
        "quick_match": "Найдите пары",
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
        "fill_blank_sentence": "Ман имрӯз калимаи ____-ро омӯхтам.",
        "fill_blank_choice": "Ҷои холиро пур кунед",
        "tap_missing_word": "Калимаи намерасидаро интихоб кунед",
        "build_sentence_chips": "Калимаҳоро бо тартиби дуруст гузоред",
        "choose_meaning_in_context": "Калимаи ҷудошуда чӣ маъно дорад?",
        "grammar_in_context": "Қисми ҷудошуда чӣ маъно медиҳад?",
        "listen_and_fill": "Гӯш кунед ва интихоб кунед",
        "odd_one_out": "Калимаи номувофиқро ёбед",
        "quick_match": "Ҷуфтҳои мувофиқро ёбед",
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

    def _sentence_pairs(self, grammar: list[dict]) -> list[tuple[str, str]]:
        pairs: list[tuple[str, str]] = []
        for item in grammar:
            if not isinstance(item, dict):
                continue
            examples = item.get("examples") if isinstance(item.get("examples"), list) else []
            for example in examples:
                if not isinstance(example, dict):
                    continue
                zh = str(example.get("zh") or "").strip()
                translation = str(example.get("translation") or "").strip()
                if zh and translation:
                    pairs.append((zh, translation))
        return pairs

    def _sentence_word_candidates(
        self,
        vocab: list[dict],
        sentence_pairs: list[tuple[str, str]],
    ) -> list[tuple[dict, str, str]]:
        candidates: list[tuple[dict, str, str]] = []
        seen = set()
        words = sorted(
            [item for item in vocab if item.get("zh") and item.get("meaning")],
            key=lambda item: len(str(item.get("zh") or "")),
            reverse=True,
        )
        for sentence, translation in sentence_pairs:
            for word in words:
                zh = str(word.get("zh") or "").strip()
                key = (zh, sentence)
                if zh and zh in sentence and key not in seen:
                    seen.add(key)
                    candidates.append((word, sentence, translation))
        return candidates

    def _blank_sentence(self, sentence: str, answer: str) -> str:
        sentence = str(sentence or "").strip()
        answer = str(answer or "").strip()
        if not sentence or not answer or answer not in sentence:
            return ""
        return sentence.replace(answer, "____", 1)

    def _highlight_sentence(self, sentence: str, target: str) -> str:
        sentence = str(sentence or "").strip()
        target = str(target or "").strip()
        if not target:
            return sentence
        if target in sentence:
            return sentence.replace(target, f"【{target}】", 1)
        return f"{sentence} 【{target}】" if sentence else f"【{target}】"

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
        **extra,
    ) -> dict | None:
        clean_options = list(dict.fromkeys(str(value).strip() for value in options if str(value or "").strip()))
        answer = str(answer or "").strip()
        if not answer or answer not in clean_options or len(clean_options) < 2:
            return None
        shuffled, answer_index = self._shuffle_options(clean_options, answer, seed)
        return {
            "lesson": lesson_order,
            "block_no": block_no,
            "type": question_type,
            "q": prompt,
            "prompt": prompt,
            "cat": cat,
            "opts": shuffled,
            "options": shuffled,
            "ans": answer_index,
            "answer": answer,
            "expl": explanation,
            "explanation": explanation,
            **extra,
        }

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

    def _reinforcement_tasks(
        self,
        vocab: list[dict],
        grammar: list[dict],
        lesson_order: int,
        lang: str,
        block_no: int | None = None,
    ) -> list[dict]:
        tasks: list[dict] = []
        sentence_pairs = self._sentence_pairs(grammar)
        zh_sentence, translated_sentence = sentence_pairs[0] if sentence_pairs else ("", "")
        scope = str(block_no) if block_no else "all"

        chinese_tokens = self._order_tokens(zh_sentence, chinese=True)
        if zh_sentence and translated_sentence and len(chinese_tokens) >= 2:
            tasks.append(
                {
                    "id": f"{lesson_order}:{scope}:reinforce:1",
                    "type": "build_sentence_chips",
                    "prompt": _QUIZ_TEXT[lang]["build_sentence_chips"],
                    "translation": translated_sentence,
                    "source": translated_sentence,
                    "tokens": self._shuffled_tokens(chinese_tokens, f"build:{lesson_order}:{scope}:{lang}"),
                    "answer": chinese_tokens,
                    "explanation": f"{zh_sentence} = {translated_sentence}",
                }
            )

        pair_words = [item for item in vocab if item.get("zh") and item.get("meaning")][:3]
        if len(pair_words) >= 2:
            pairs = [[item["zh"], item["meaning"]] for item in pair_words]
            tasks.append(
                {
                    "id": f"{lesson_order}:{scope}:reinforce:2",
                    "type": "quick_match",
                    "prompt": _QUIZ_TEXT[lang]["quick_match"],
                    "pairs": pairs,
                    "explanation": " · ".join(f"{left} = {right}" for left, right in pairs),
                }
            )

        stroke_word = next((item for item in vocab if item.get("zh") and any("\u4e00" <= char <= "\u9fff" for char in item.get("zh", ""))), None)
        if stroke_word:
            tasks.append(
                {
                    "id": f"{lesson_order}:{scope}:reinforce:3",
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

        sentence_candidates = self._sentence_word_candidates(vocab, sentence_pairs)
        if sentence_candidates:
            word, sentence, translation = sentence_candidates[0]
            hanzis = [item["zh"] for item in vocab if item.get("zh")]
            blank_sentence = self._blank_sentence(sentence, word["zh"])
            if blank_sentence:
                options, answer_index = self._sample_options(
                    word["zh"],
                    hanzis,
                    f"reinforce-fill:{lesson_order}:{scope}:{lang}",
                )
                if len(options) >= 2:
                    tasks.append(
                        {
                            "id": f"{lesson_order}:{scope}:reinforce:4",
                            "type": "fill_blank_choice",
                            "prompt": _QUIZ_TEXT[lang]["fill_blank_choice"],
                            "sentence": blank_sentence,
                            "options": options,
                            "opts": options,
                            "answer": word["zh"],
                            "ans": answer_index,
                            "explanation": f"{sentence} = {translation or word['meaning']}",
                        }
                    )

        if len(tasks) < 3 and pair_words:
            listening_word = pair_words[0]
            hanzis = [item["zh"] for item in vocab if item.get("zh")]
            options, answer_index = self._sample_options(
                listening_word["zh"],
                hanzis,
                f"listen:{lesson_order}:{scope}:{lang}",
            )
            if len(options) >= 2:
                tasks.append(
                    {
                        "id": f"{lesson_order}:{scope}:reinforce:fallback-listen",
                        "type": "listening_choice",
                        "prompt": _QUIZ_TEXT[lang]["listening_choice"],
                        "audioText": listening_word["zh"],
                        "options": options,
                        "opts": options,
                        "answer": listening_word["zh"],
                        "ans": answer_index,
                        "explanation": f"{listening_word['zh']} = {listening_word['meaning']}",
                    }
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
            elif question_type == "fill_blank":
                answer = zh
                options = [answer] + self._distractors(hanzis, answer)
                question = text["fill_blank"]
                sentence = text["fill_blank_sentence"]
                ui_type = "fill_blank"
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

        types = (*types, "fill_blank")
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
            tokens = self._order_tokens(sentence, chinese=True)
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
    ) -> list[dict]:
        word_questions = self._word_quiz_questions(vocab, lesson_order, lang, block_no)
        grammar_pool = lesson_grammar or grammar
        grammar_questions = self._unique_questions(
            self._grammar_quiz_questions(grammar, grammar_pool, lesson_order, lang, block_no)
        )
        interactive_questions = self._interactive_quiz_questions(
            vocab,
            grammar,
            grammar_pool,
            lesson_order,
            lang,
            block_no,
        )

        target_count = 5
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

        take(("fill_blank_choice", "tap_missing_word", "fill_blank"))
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
        reinforcement_tasks = self._reinforcement_tasks(
            vocab,
            grammar or lesson_grammar,
            lesson.lesson_order,
            lang,
            int(block.get("block_no")) if block else None,
        )
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
            "reinforcement_tasks": reinforcement_tasks,
        }
