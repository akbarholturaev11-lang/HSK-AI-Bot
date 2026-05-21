import json


_BLOCK_CONFIG = {
    1: {
        1: {
            "word_nos": [1, 2],
            "grammar_nos": [1, 2],
            "grammar_notes": [
                {
                    "pattern": "你 + 好 → 你好",
                    "explanation_uz": "Ikki 3-ton yonma-yon kelsa, birinchisi talaffuzda 2-tonga yaqinlashadi.",
                    "explanation_ru": "Когда два третьих тона идут рядом, первый произносится ближе ко второму тону.",
                    "explanation_tj": "Вақте ду садои 3 паи ҳам меоянд, аввалӣ дар талаффуз ба садои 2 наздик мешавад.",
                    "example_zh": "你好！",
                    "example_pinyin": "Nǐ hǎo!",
                    "example_uz": "Salom!",
                    "example_ru": "Привет!",
                    "example_tj": "Салом!",
                }
            ],
        },
        2: {
            "word_nos": [3, 4],
            "grammar_notes": [
                {
                    "pattern": "您 / 你们 + 好",
                    "explanation_uz": "您 hurmat shakli, 你们 esa ko'plik. Ikkalasi ham 好 bilan salomlashuv yasaydi.",
                    "explanation_ru": "您 — вежливая форма, 你们 — множественное число. Оба образуют приветствие с 好.",
                    "explanation_tj": "您 шакли эҳтиромӣ аст, 你们 шакли ҷамъ. Ҳар ду бо 好 салом месозанд.",
                    "example_zh": "你们好！",
                    "example_pinyin": "Nǐmen hǎo!",
                    "example_uz": "Hammangizga salom!",
                    "example_ru": "Здравствуйте все!",
                    "example_tj": "Ба ҳамаи шумо салом!",
                }
            ],
        },
        3: {
            "word_nos": [5, 6],
            "grammar_notes": [
                {
                    "pattern": "对不起 → 没关系",
                    "explanation_uz": "Kechirim so'ralganda, 没关系 bilan 'hechqisi yo'q' deb javob beriladi.",
                    "explanation_ru": "На извинение 对不起 обычно отвечают 没关系 — «ничего страшного».",
                    "explanation_tj": "Ба узри 对不起 одатан бо 没关系 — «ҳеҷ гап не» ҷавоб медиҳанд.",
                    "example_zh": "对不起！没关系！",
                    "example_pinyin": "Duìbuqǐ! Méi guānxi!",
                    "example_uz": "Kechirasiz! Hechqisi yo'q!",
                    "example_ru": "Извините! Ничего страшного!",
                    "example_tj": "Бубахшед! Ҳеҷ гап не!",
                }
            ],
        },
    },
    2: {
        1: {"word_nos": [1, 2], "grammar_nos": [1]},
        2: {"word_nos": [3], "grammar_nos": [1, 2]},
        3: {
            "word_nos": [4],
            "grammar_notes": [
                {
                    "pattern": "再 + 见 → 再见",
                    "explanation_uz": "再 'yana', 见 'ko'rishmoq'. Birga xayrlashuv ma'nosini beradi.",
                    "explanation_ru": "再 значит «снова», 见 — «видеться». Вместе это прощание.",
                    "explanation_tj": "再 маънои «боз», 见 «дидан» аст. Якҷоя хайрбод мешавад.",
                    "example_zh": "再见！",
                    "example_pinyin": "Zàijiàn!",
                    "example_uz": "Xayr!",
                    "example_ru": "До свидания!",
                    "example_tj": "Хайр!",
                }
            ],
        },
    },
    3: {
        1: {
            "word_nos": [1, 2, 3, 4, 10],
            "grammar_nos": [3],
            "grammar_notes": [
                {
                    "pattern": "我叫 + ism",
                    "explanation_uz": "Ism aytishda 叫 ishlatiladi: 'men ... deb atalman'.",
                    "explanation_ru": "Для имени используется 叫: «меня зовут ...».",
                    "explanation_tj": "Барои гуфтани ном 叫 истифода мешавад: «номам ... аст».",
                    "example_zh": "我叫李月。",
                    "example_pinyin": "Wǒ jiào Lǐ Yuè.",
                    "example_uz": "Mening ismim Li Yue.",
                    "example_ru": "Меня зовут Ли Юэ.",
                    "example_tj": "Номи ман Ли Юэ аст.",
                }
            ],
        },
        2: {"word_nos": [5, 6, 7, 8], "grammar_nos": [1, 2]},
        3: {
            "word_nos": [9, 11, 12],
            "grammar_nos": [1, 2],
            "grammar_notes": [
                {
                    "pattern": "国家 + 人",
                    "explanation_uz": "Davlat nomidan keyin 人 qo'shilsa, millat/kishilik ma'nosi chiqadi.",
                    "explanation_ru": "Если после страны добавить 人, получится национальность.",
                    "explanation_tj": "Агар баъди номи кишвар 人 ояд, миллатро ифода мекунад.",
                    "example_zh": "美国人",
                    "example_pinyin": "Měiguó rén",
                    "example_uz": "amerikalik",
                    "example_ru": "американец",
                    "example_tj": "амрикоӣ",
                }
            ],
        },
    },
    4: {
        1: {"word_nos": [1, 2, 3, 4], "grammar_nos": [1, 2]},
        2: {
            "word_nos": [5, 6, 7],
            "grammar_nos": [3],
            "grammar_notes": [
                {
                    "pattern": "哪 + 国 + 人",
                    "explanation_uz": "哪国人 'qaysi davlat odami?' degani. Bu millatni so'rashning sodda shakli.",
                    "explanation_ru": "哪国人 значит «человек какой страны?» — простой вопрос о национальности.",
                    "explanation_tj": "哪国人 яъне «одами кадом кишвар?» — саволи содда дар бораи миллат.",
                    "example_zh": "你是哪国人？",
                    "example_pinyin": "Nǐ shì nǎ guó rén?",
                    "example_uz": "Siz qaysi mamlakatdansiz?",
                    "example_ru": "Вы из какой страны?",
                    "example_tj": "Шумо аз кадом кишвар ҳастед?",
                }
            ],
        },
        3: {"word_nos": [8, 9, 10], "grammar_nos": [1, 3]},
    },
    5: {
        1: {"word_nos": [1, 2, 3], "grammar_nos": [1]},
        2: {"word_nos": [4, 5, 6, 7, 8], "grammar_nos": [1, 3]},
        3: {"word_nos": [9, 10], "grammar_nos": [2, 3, 4]},
    },
    6: {
        1: {"word_nos": [1, 2, 3], "grammar_nos": [1]},
        2: {"word_nos": [4, 5, 6, 7], "grammar_nos": [2]},
        3: {"word_nos": [8, 9, 10, 11, 12], "grammar_nos": [1, 3]},
    },
    7: {
        1: {"word_nos": [1, 2, 3, 4, 5, 6], "grammar_nos": [1, 2]},
        2: {"word_nos": [7, 8], "grammar_nos": [1]},
        3: {"word_nos": [9, 10, 11, 12], "grammar_nos": [3]},
    },
    8: {
        1: {"word_nos": [1, 2, 3, 4, 5], "grammar_nos": [1]},
        2: {"word_nos": [6, 7, 8, 9, 10], "grammar_nos": [1, 3]},
        3: {"word_nos": [11, 12, 13, 14, 15], "grammar_nos": [2, 4]},
    },
    9: {
        1: {"word_nos": [1, 2, 3, 4, 5, 6, 7], "grammar_nos": [1, 2]},
        2: {"word_nos": [8, 9, 10, 11, 12, 13], "grammar_nos": [1, 3]},
        3: {"word_nos": [14], "grammar_nos": [2, 4]},
    },
    10: {
        1: {"word_nos": [1, 2, 3, 4, 5, 6], "grammar_nos": [1, 2]},
        2: {"word_nos": [7, 8, 13, 14], "grammar_nos": [2]},
        3: {"word_nos": [9, 10, 11, 12], "grammar_nos": [1, 3, 4]},
    },
    11: {
        1: {"word_nos": [1, 2, 3, 4, 5], "grammar_nos": [1, 2]},
        2: {"word_nos": [6, 7, 8, 9], "grammar_nos": [2]},
        3: {"word_nos": [10, 11, 12], "grammar_nos": [3]},
    },
    12: {
        1: {"word_nos": [1, 2, 3, 4, 5], "grammar_nos": [1, 2, 3]},
        2: {"word_nos": [6, 7, 8], "grammar_nos": [4]},
        3: {"word_nos": [9, 10, 11, 12, 13], "grammar_nos": [1, 2, 3]},
    },
    13: {
        1: {"word_nos": [1, 2, 3, 11], "grammar_nos": [1, 2]},
        2: {"word_nos": [4, 5, 6, 7], "grammar_nos": [2, 3]},
        3: {"word_nos": [8, 9, 10], "grammar_nos": [3, 4]},
    },
    14: {
        1: {"word_nos": [1, 2, 3], "grammar_nos": [1]},
        2: {"word_nos": [4, 5, 6, 7, 8, 9, 10, 17], "grammar_nos": [1, 2]},
        3: {"word_nos": [11, 12, 13, 14, 15, 16], "grammar_nos": [1, 3, 4]},
    },
    15: {
        1: {"word_nos": [1, 2, 3], "grammar_nos": [1, 2]},
        2: {"word_nos": [4, 5, 6], "grammar_nos": [1]},
        3: {"word_nos": [7, 8, 9], "grammar_nos": [1]},
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
        "instruction_tj": "Бо калимаҳои нави ҳамин муколама 1-2 ҷумлаи содда нависед.",
        "words": word_list,
    }


def apply_hsk1_block_metadata(lesson: dict) -> dict:
    lesson_order = int(lesson.get("lesson_order") or 0)
    config = _BLOCK_CONFIG.get(lesson_order)
    if not config:
        return lesson

    vocab = _parse(lesson.get("vocabulary_json"), [])
    grammar = _parse(lesson.get("grammar_json"), [])
    dialogues = _parse(lesson.get("dialogue_json"), [])
    if not isinstance(vocab, list) or not isinstance(grammar, list) or not isinstance(dialogues, list):
        return lesson

    for block in dialogues:
        if not isinstance(block, dict):
            continue
        block_no = int(block.get("block_no") or 0)
        cfg = config.get(block_no)
        if not cfg:
            continue
        block.update(cfg)
        block_words = [_word_by_no(vocab, no) for no in cfg.get("word_nos", [])]
        block_words = [word for word in block_words if word]
        block.setdefault("mini_quiz", _mini_quiz(lesson_order, block_no, vocab, grammar, cfg))
        block.setdefault("mini_homework", _mini_homework(block_no, block_words))

    lesson["dialogue_json"] = json.dumps(dialogues, ensure_ascii=False)
    return lesson
