import json
import re

from scripts.block_context_grammar import normalize_block_grammar


_CJK_RE = re.compile(r"[\u4e00-\u9fff]+")
_GRAMMAR_LABELS = {
    "助动词",
    "程度副词",
    "概数的表达",
    "介词",
    "副词",
    "结构助词",
    "动态助词",
    "语气助词",
    "连词",
    "补语",
    "结果补语",
    "程度补语",
    "趋向补语",
    "比较句",
    "把字句",
    "被字句",
    "疑问句",
    "选择疑问句",
    "正反疑问句",
    "兼语句",
    "连动句",
}

_WORD_MAP_OVERRIDES = {
    1: {
        1: [1, 2, 3, 4, 5],
        2: [6, 7, 8],
        3: [9, 10],
        4: [11, 12, 13],
    },
    2: {
        1: [1, 2, 3, 4, 5],
        2: [6, 7, 8, 9],
        3: [10, 11, 12],
        4: [13, 14, 15],
    },
    3: {
        1: [1, 2],
        2: [3, 4, 5, 6],
        3: [7, 8, 9, 10, 11, 12, 13],
        4: [14, 15, 16],
    },
    4: {
        1: [1, 2, 3],
        2: [4, 5, 6],
        3: [7, 8, 9],
        4: [10, 11, 12, 13],
    },
    5: {
        1: [1, 2, 3, 4, 5],
        2: [6, 7, 8, 9],
        3: [10, 11],
        4: [12, 13, 14],
    },
    6: {
        1: [1, 2, 3],
        2: [4, 5, 6],
        3: [7, 8, 9, 10, 11, 12],
        4: [13],
    },
    7: {
        1: [1],
        2: [2, 3],
        3: [4, 5, 6, 7, 8, 9, 10],
        4: [11, 12, 13],
    },
    8: {
        1: [1, 2, 3],
        2: [4, 5, 6, 11, 12],
        3: [7],
        4: [8, 9, 10, 13],
    },
    9: {
        1: [1],
        2: [2, 3, 4, 5, 6, 7],
        3: [8],
        4: [9, 10, 11],
    },
    10: {
        1: [1, 2, 3, 12],
        2: [10, 11, 13],
        3: [4, 5, 6, 7],
        4: [8, 9],
    },
    11: {
        1: [1, 2],
        2: [3, 4, 5, 6],
        3: [7],
        4: [8, 9, 10, 11],
    },
    12: {
        1: [1, 10, 12],
        2: [2, 11],
        3: [3, 4, 5, 6, 7, 13],
        4: [8, 9],
    },
    13: {
        1: [1],
        2: [2, 3, 4],
        3: [5, 6, 7],
        4: [8, 9, 10, 11],
    },
    14: {
        1: [1, 2],
        2: [3, 4, 5],
        3: [6, 8, 9, 10],
        4: [7, 11, 12, 13],
    },
    15: {
        1: [1, 2, 3, 4, 9, 11],
        2: [5, 6],
        3: [7],
        4: [8, 10, 12, 13],
    },
}


def _parse(value, default):
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except Exception:
        return default


def _meaning(word: dict, lang: str) -> str:
    return word.get(lang) or word.get("uz") or word.get("ru") or word.get("tj") or ""


def _word_by_no(vocab: list[dict], no: int) -> dict:
    for word in vocab:
        if isinstance(word, dict) and int(word.get("no") or 0) == no:
            return word
    return {}


def _grammar_by_no(grammar: list[dict], no: int) -> dict:
    for item in grammar:
        if isinstance(item, dict) and int(item.get("no") or 0) == no:
            return item
    return {}


def _options(answer: str, pool: list[str]) -> list[str]:
    values = [answer]
    for value in pool:
        if value and value not in values:
            values.append(value)
        if len(values) == 4:
            break
    return values


def _dialogue_text(block: dict) -> str:
    lines = block.get("dialogue") or []
    return "".join(str(line.get("zh") or "") for line in lines if isinstance(line, dict))


def _infer_word_nos(vocab: list[dict], dialogues: list[dict]) -> dict[int, list[int]]:
    block_texts = {
        int(block.get("block_no") or 0): _dialogue_text(block)
        for block in dialogues
        if isinstance(block, dict)
    }
    block_nos = [no for no in block_texts if no]
    result = {no: [] for no in block_nos}
    if not block_nos:
        return result

    last_block_index = 0
    for word in vocab:
        if not isinstance(word, dict):
            continue
        word_no = int(word.get("no") or 0)
        zh = str(word.get("zh") or "")
        if not word_no or not zh:
            continue

        matched_block = next(
            (
                block_no
                for block_no in block_nos[last_block_index:]
                if zh and zh in block_texts.get(block_no, "")
            ),
            None,
        )
        if matched_block:
            last_block_index = block_nos.index(matched_block)
        result.setdefault(block_nos[last_block_index], []).append(word_no)
    return result


def _grammar_keys(item: dict) -> list[str]:
    text = " ".join(
        str(item.get(key) or "")
        for key in ("title_zh", "formula", "example")
        if item.get(key)
    )
    keys = []
    for value in _CJK_RE.findall(text):
        if value in _GRAMMAR_LABELS:
            continue
        if len(value) <= 3:
            keys.append(value)
        elif len(value) > 3:
            keys.extend(ch for ch in value if ch not in "的地得")
    return list(dict.fromkeys(keys))


def _infer_grammar_nos(grammar: list[dict], dialogues: list[dict]) -> dict[int, list[int]]:
    block_texts = {
        int(block.get("block_no") or 0): _dialogue_text(block)
        for block in dialogues
        if isinstance(block, dict)
    }
    result = {block_no: [] for block_no in block_texts if block_no}
    if not result:
        return result

    for item in grammar:
        if not isinstance(item, dict):
            continue
        grammar_no = int(item.get("no") or 0)
        if not grammar_no:
            continue
        keys = _grammar_keys(item)
        matched = [
            block_no
            for block_no, text in block_texts.items()
            if any(key and key in text for key in keys)
        ]
        if not matched:
            block_nos = list(result)
            index = min(grammar_no - 1, len(block_nos) - 1)
            matched = [block_nos[index]]
        for block_no in matched:
            result.setdefault(block_no, []).append(grammar_no)

    grammar_nos = [int(item.get("no") or 0) for item in grammar if isinstance(item, dict)]
    grammar_nos = [no for no in grammar_nos if no]
    for block_no, nos in result.items():
        if not nos and grammar_nos:
            fallback_index = min(block_no - 1, len(grammar_nos) - 1)
            nos.append(grammar_nos[fallback_index])
        result[block_no] = sorted(set(nos))
    return result


def _mini_quiz(lesson_order: int, block_no: int, vocab: list[dict], grammar: list[dict], cfg: dict) -> list[dict]:
    words = [_word_by_no(vocab, no) for no in cfg.get("word_nos", [])]
    words = [word for word in words if word]
    meaning_pool = [_meaning(word, "uz") for word in vocab if isinstance(word, dict)]
    hanzi_pool = [word.get("zh") for word in vocab if isinstance(word, dict)]
    quiz = []

    if words:
        word = words[0]
        answer = _meaning(word, "uz")
        quiz.append(
            {
                "type": "meaning",
                "prompt_uz": f"“{word.get('zh')}” nimani anglatadi?",
                "prompt_ru": f"Что означает “{word.get('zh')}”?",
                "prompt_tj": f"“{word.get('zh')}” чӣ маъно дорад?",
                "answer": answer,
                "options": _options(answer, meaning_pool),
            }
        )

    if len(words) > 1:
        word = words[1]
        answer = word.get("zh") or ""
        quiz.append(
            {
                "type": "hanzi",
                "prompt_uz": f"“{_meaning(word, 'uz')}” qaysi so'z?",
                "prompt_ru": f"Какое слово означает “{_meaning(word, 'ru')}”?",
                "prompt_tj": f"Кадом калима маънои “{_meaning(word, 'tj')}”-ро дорад?",
                "answer": answer,
                "options": _options(answer, hanzi_pool),
            }
        )

    grammar_nos = cfg.get("grammar_nos") or []
    if grammar_nos:
        item = _grammar_by_no(grammar, grammar_nos[0])
        if item:
            answer = item.get("title_zh") or item.get("title_uz") or ""
            quiz.append(
                {
                    "type": "grammar",
                    "prompt_uz": "Bu qismdagi asosiy grammatika qaysi?",
                    "prompt_ru": "Какая главная грамматика в этой части?",
                    "prompt_tj": "Грамматикаи асосии ин қисм кадом аст?",
                    "answer": answer,
                    "options": _options(answer, [g.get("title_zh") or "" for g in grammar if isinstance(g, dict)]),
                }
            )

    if len(quiz) < 3 and words:
        word = words[0]
        answer = word.get("pinyin") or ""
        quiz.append(
            {
                "type": "pinyin",
                "prompt_uz": f"“{word.get('zh')}” pinyini qaysi?",
                "prompt_ru": f"Какой pinyin у “{word.get('zh')}”?",
                "prompt_tj": f"Pinyin-и “{word.get('zh')}” кадом аст?",
                "answer": answer,
                "options": _options(answer, [w.get("pinyin") or "" for w in vocab if isinstance(w, dict)]),
            }
        )

    for index, item in enumerate(quiz, 1):
        item["lesson_order"] = lesson_order
        item["block_no"] = block_no
        item["no"] = index
    return quiz


def _mini_homework(block_no: int, words: list[dict]) -> dict:
    word_list = [word.get("zh") for word in words if isinstance(word, dict) and word.get("zh")]
    return {
        "block_no": block_no,
        "instruction_uz": "Shu dialogdagi yangi so'zlardan 1-2 ta sodda gap yozing.",
        "instruction_ru": "Напишите 1-2 простых предложения с новыми словами этого диалога.",
        "instruction_tj": "Бо калимаҳои нави ҳамин гуфтугӯ 1-2 ҷумлаи содда нависед.",
        "words": word_list,
    }


def apply_hsk2_block_metadata(lesson: dict) -> dict:
    lesson_order = int(lesson.get("lesson_order") or 0)
    vocab = _parse(lesson.get("vocabulary_json"), [])
    grammar = _parse(lesson.get("grammar_json"), [])
    dialogues = _parse(lesson.get("dialogue_json"), [])
    if not isinstance(vocab, list) or not isinstance(grammar, list) or not isinstance(dialogues, list):
        return lesson

    word_map = _WORD_MAP_OVERRIDES.get(lesson_order) or _infer_word_nos(vocab, dialogues)
    grammar_map = _infer_grammar_nos(grammar, dialogues)

    for block in dialogues:
        if not isinstance(block, dict):
            continue
        block_no = int(block.get("block_no") or 0)
        if not block_no:
            continue
        cfg = {
            "word_nos": word_map.get(block_no, []),
            "grammar_nos": grammar_map.get(block_no, []),
        }
        block.update(cfg)
        block.pop("mini_quiz", None)
        block.pop("mini_homework", None)

    normalize_block_grammar(dialogues)

    for block in dialogues:
        if not isinstance(block, dict):
            continue
        block_no = int(block.get("block_no") or 0)
        if not block_no:
            continue
        block_words = [_word_by_no(vocab, no) for no in block.get("word_nos", [])]
        block_words = [word for word in block_words if word]
        block["mini_quiz"] = _mini_quiz(lesson_order, block_no, vocab, grammar, block)
        block["mini_homework"] = _mini_homework(block_no, block_words)

    lesson["dialogue_json"] = json.dumps(dialogues, ensure_ascii=False)
    return lesson
