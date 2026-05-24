import json
from typing import Any


def _parse(value: Any, default: Any = None):
    if value is None:
        return default
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value)
    except Exception:
        return default


def _parse_title(raw: str) -> str:
    """lesson.title oddiy string yoki JSON bo'lishi mumkin.
    JSON bo'lsa — xitoycha (zh) qismini, yo'q bo'lsa uz ni qaytaradi."""
    if not raw:
        return ""
    if raw.strip().startswith("{"):
        try:
            d = json.loads(raw)
            if isinstance(d, dict):
                return d.get("zh") or d.get("uz") or raw
        except Exception:
            pass
    return raw


def _uz_fallback(lang: str, value: Any) -> Any:
    return value if lang == "uz" else None


def _lesson_word(lang: str) -> str:
    return {"uz": "Dars", "ru": "Урок", "tj": "Дарс"}.get(lang, "Урок")


def _lesson_blocks(lesson) -> list[dict]:
    dialogues = _parse(getattr(lesson, "dialogue_json", None), [])
    if not isinstance(dialogues, list):
        return []
    return [
        block
        for block in dialogues
        if isinstance(block, dict) and block.get("block_no")
    ]


def _block_by_no(lesson, n: int) -> dict:
    for block in _lesson_blocks(lesson):
        if int(block.get("block_no") or 0) == n:
            return block
    return {}


def _block_words(lesson, block: dict) -> list[dict]:
    vocab = _parse(getattr(lesson, "vocabulary_json", None), [])
    if not isinstance(vocab, list):
        return []

    word_nos = block.get("word_nos") or []
    if not isinstance(word_nos, list) or not word_nos:
        return []

    wanted = {int(no) for no in word_nos if str(no).isdigit()}
    return [
        word
        for word in vocab
        if isinstance(word, dict) and int(word.get("no") or 0) in wanted
    ]


def _block_grammar_items(lesson, block: dict) -> list[dict]:
    grammar = _parse(getattr(lesson, "grammar_json", None), [])
    if not isinstance(grammar, list):
        return []

    grammar_nos = block.get("grammar_nos") or []
    if not isinstance(grammar_nos, list) or not grammar_nos:
        return []

    wanted = {int(no) for no in grammar_nos if str(no).isdigit()}
    return [
        item
        for item in grammar
        if isinstance(item, dict) and int(item.get("no") or 0) in wanted
    ]


def _block_label(lang: str, n: int, total: int) -> str:
    labels = {
        "uz": "Qism",
        "ru": "Часть",
        "tj": "Қисм",
    }
    return f"{labels.get(lang, labels['ru'])} {n}/{max(total, n)}"


_NARRATION_SPEAKERS = {"", "旁白", "narrator", "narration", "matn", "text", "文本"}


def _is_narration_line(line: dict) -> bool:
    speaker = str(line.get("speaker") or "").strip()
    return speaker.lower() in _NARRATION_SPEAKERS or speaker in _NARRATION_SPEAKERS


def _is_narration_block(block: dict) -> bool:
    dialogue_lines = block.get("dialogue") or block.get("lines") or []
    real_lines = [line for line in dialogue_lines if isinstance(line, dict)]
    return bool(real_lines) and all(_is_narration_line(line) for line in real_lines)


def _append_text_line(lines: list[str], line: dict, lang: str) -> None:
    zh = line.get("zh", "")
    pinyin = line.get("pinyin", "")
    translation = (
        _uz_fallback(lang, line.get("translation"))
        or line.get(lang)
        or _uz_fallback(lang, line.get("uz"))
        or ""
    )
    if zh:
        lines.append(f"<b>{zh}</b>")
    if pinyin:
        lines.append(f"<i>{pinyin}</i>")
    if translation:
        lines.append(translation)
    lines.append("")


# ─── Emoji raqamlar ────────────────────────────────────────────────────────
_NUMS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]


def format_vocab(lesson, lang: str, lesson_total_steps: int = 6) -> str:
    vocab = _parse(lesson.vocabulary_json, [])
    title = _parse_title(lesson.title or "")

    label = {"uz": "Yangi so'zlar 🇨🇳", "tj": "Калимаҳои нав 🇨🇳", "ru": "Новые слова 🇨🇳"}
    lines = [f"【1/{lesson_total_steps}】 {title} · {label.get(lang, label['ru'])}", ""]

    hint = {
        "uz": f"✨ Bugun {len(vocab)} ta so'z — darsni tugatgach ishlatishni bilasiz!",
        "tj": f"✨ Имрӯз {len(vocab)} калима — пас аз дарс истифода карда метавонед!",
        "ru": f"✨ Сегодня {len(vocab)} слов — после урока сможете их использовать!",
    }
    lines.append(hint.get(lang, hint["ru"]))
    lines.append("")

    nums = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

    for i, word in enumerate(vocab):
        if not isinstance(word, dict):
            continue
        zh = word.get("zh", "")
        pinyin = word.get("pinyin", "")
        meaning = word.get(lang) or _uz_fallback(lang, word.get("uz")) or word.get("meaning") or ""
        example_zh = word.get("example_zh", "")
        example_pinyin = word.get("example_pinyin", "")
        example_lang = word.get(f"example_{lang}") or word.get("example") or ""

        num = nums[i] if i < len(nums) else f"{i+1}."

        lines.append("━━━━━━━━━━━━━━")
        lines.append(f"{num}  {zh}")
        lines.append(f"     {pinyin}")
        lines.append(f"     👉 {meaning}")

        if example_zh:
            lines.append("")
            lines.append(f"     💬 {example_zh}")
            if example_pinyin:
                lines.append(f"        {example_pinyin}")
            if example_lang:
                lines.append(f"        {example_lang}")

        lines.append("")

    lines.append("━━━━━━━━━━━━━━")
    return "\n".join(lines)


def format_dialogue(lesson, lang: str, lesson_total_steps: int = 6) -> str:
    dialogues = _parse(lesson.dialogue_json, [])
    title = _parse_title(lesson.title or "")

    step_label = {"uz": "Jonli dialog 🎭", "tj": "Муколамаи зинда 🎭", "ru": "Живой диалог 🎭"}
    lines = [f"【2/{lesson_total_steps}】 {title} · {step_label.get(lang, step_label['ru'])}", ""]

    for block in dialogues:
        if not isinstance(block, dict):
            continue

        # section label (课文 1, 课文 2 ...)
        section = block.get("section_label", "")
        scene = (
            block.get(f"scene_{lang}")
            or block.get("scene_label_zh")
            or ""
        )

        header = " · ".join(filter(None, [section, scene]))
        if header:
            lines.append(f"📍 {header}")
            lines.append("")

        lines.append("━━━━━━━━━━━━━━")

        # actual key is "dialogue", fallback to "lines"
        dialogue_lines = block.get("dialogue") or block.get("lines") or []
        for line in dialogue_lines:
            if not isinstance(line, dict):
                continue
            if _is_narration_line(line):
                _append_text_line(lines, line, lang)
                continue
            speaker = line.get("speaker", "")
            zh = line.get("zh", "")
            pinyin = line.get("pinyin", "")
            # actual key is "translation", fallback to lang key
            translation = (
                _uz_fallback(lang, line.get("translation"))
                or line.get(lang)
                or _uz_fallback(lang, line.get("uz"))
                or ""
            )

            icon = "👤" if speaker == "A" else "👥"
            lines.append(f"{icon} {speaker}:  {zh}")
            lines.append(f"       {pinyin}")
            lines.append(f"       {translation}")
            lines.append("")

        lines.append("━━━━━━━━━━━━━━")

        notes = block.get("notes", [])
        if notes:
            lines.append("")
            tip = {"uz": "💡 Bilasizmi?", "tj": "💡 Медонед?", "ru": "💡 Знаете ли вы?"}
            lines.append(tip.get(lang, tip["ru"]))
            for note in notes:
                note_text = note.get(lang) or _uz_fallback(lang, note.get("uz")) or ""
                if note_text:
                    lines.append(note_text)

        lines.append("")

    return "\n".join(lines).rstrip()


def format_grammar(lesson, lang: str, lesson_total_steps: int = 6) -> str:
    grammar = _parse(lesson.grammar_json, [])
    title = _parse_title(lesson.title or "")

    step_label = {"uz": "Grammatika 📐", "tj": "Грамматика 📐", "ru": "Грамматика 📐"}
    lines = [f"【3/{lesson_total_steps}】 {title} · {step_label.get(lang, step_label['ru'])}", ""]

    for i, g in enumerate(grammar, 1):
        if not isinstance(g, dict):
            continue

        g_title = g.get(f"title_{lang}") or _uz_fallback(lang, g.get("title_uz")) or g.get("title_zh") or ""
        rule = (
            g.get(f"rule_{lang}") or
            _uz_fallback(lang, g.get("rule_uz")) or
            g.get("explanation") or
            g.get("rule") or ""
        )

        lines.append("━━━━━━━━━━━━━━")
        lines.append(f"📌 {i}. {g_title}")
        lines.append("")
        if rule:
            for rule_line in rule.split("\n"):
                lines.append(f"   {rule_line}")
        lines.append("")

        examples = g.get("examples", [])
        if examples:
            eg_label = {"uz": "Misollar:", "tj": "Мисолҳо:", "ru": "Примеры:"}
            lines.append(f"   {eg_label.get(lang, eg_label['ru'])}")
            for ex in examples:
                zh = ex.get("zh", "")
                pinyin = ex.get("pinyin", "")
                meaning = ex.get(lang) or _uz_fallback(lang, ex.get("uz")) or ex.get("meaning") or ""
                lines.append(f"   • {zh} ({pinyin}) — {meaning}")
        lines.append("")

    lines.append("━━━━━━━━━━━━━━")
    return "\n".join(lines)


def format_exercise(lesson, lang: str, lesson_total_steps: int = 6) -> str:
    exercises = _parse(lesson.exercise_json, [])
    title = _parse_title(lesson.title or "")

    step_label = {"uz": "Test vaqti! 🧠", "tj": "Вақти санҷиш! 🧠", "ru": "Время теста! 🧠"}
    lines = [f"【5/{lesson_total_steps}】 {title} · {step_label.get(lang, step_label['ru'])}", ""]

    hint = {
        "uz": "Siz tayyor deb o'ylaymiz... Isbotlang! 😄",
        "tj": "Мо фикр мекунем шумо омодаед... Исбот кунед! 😄",
        "ru": "Думаем, вы готовы... Докажите! 😄",
    }
    lines.append(hint.get(lang, hint["ru"]))
    lines.append("")

    answer_hint = {
        "uz": "Javobingizni yozing ⬇️",
        "tj": "Посухатонро нависед ⬇️",
        "ru": "Напишите ответ ⬇️",
    }

    for ex in exercises:
        if not isinstance(ex, dict):
            continue

        instruction = (
            ex.get(f"instruction_{lang}")
            or _uz_fallback(lang, ex.get("instruction_uz"))
            or ex.get("instruction", "")
        )
        items = ex.get("items", [])

        lines.append("━━━━━━━━━━━━━━")
        if instruction:
            lines.append(f"📝 {instruction}")
            lines.append("")

        for i, item in enumerate(items, 1):
            if not isinstance(item, dict):
                continue
            prompt = (
                item.get(f"prompt_{lang}")
                or _uz_fallback(lang, item.get("prompt_uz"))
                or item.get("prompt", "")
            )
            if prompt:
                lines.append(f"  {i}. {prompt}")

        lines.append("")

    lines.append("━━━━━━━━━━━━━━")
    lines.append(answer_hint.get(lang, answer_hint["ru"]))

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# V2 formatters — vocab_1 / vocab_2 / dialogue_N
# ─────────────────────────────────────────────────────────────────────────────

def _format_word_block(word: dict, index: int, lang: str, lines: list):
    """Bitta so'z blokini lines ga qo'shadi (V2 style HTML)."""
    zh      = word.get("zh", "")
    pinyin  = word.get("pinyin", "")
    meaning = word.get(lang) or _uz_fallback(lang, word.get("uz")) or word.get("meaning") or ""
    ex_zh   = word.get("example_zh", "")
    ex_pin  = word.get("example_pinyin", "")
    ex_lang = word.get(f"example_{lang}") or word.get("example") or ""

    num = _NUMS[index] if index < len(_NUMS) else f"{index + 1}."
    lines.append("─────────────")
    lines.append(f"{num}  <b>{zh}</b>")
    lines.append(f"     <i>{pinyin}</i>")
    lines.append(f"     👉 {meaning}")
    if ex_zh:
        lines.append("")
        lines.append(f"     💬 <b>{ex_zh}</b>")
        if ex_pin:
            lines.append(f"        <i>{ex_pin}</i>")
        if ex_lang:
            lines.append(f"        {ex_lang}")
    lines.append("")


def format_vocab_1(lesson, lang: str) -> str:
    """V2: birinchi 8 ta so'z (vocab_1 step)."""
    vocab = _parse(lesson.vocabulary_json, [])
    total = len(vocab)
    page  = vocab[:8]
    title = _parse_title(lesson.title or "")

    hdr = {
        "uz": "📖 Yangi so'zlar 🇨🇳",
        "tj": "📖 Калимаҳои нав 🇨🇳",
        "ru": "📖 Новые слова 🇨🇳",
    }
    hint_tpl = {
        "uz": "✨ Bugun <b>{}</b> ta yangi so'z — darsni tugatgach amalda ishlata olasiz!",
        "tj": "✨ Имрӯз <b>{}</b> калимаи нав — пас аз дарс онҳоро истифода карда метавонед!",
        "ru": "✨ Сегодня <b>{}</b> новых слов — после урока сможете их использовать!",
    }

    lines = [
        f"<b>【{_lesson_word(lang)} {lesson.lesson_order}】 {title}</b>",
        hdr.get(lang, hdr["ru"]),
        "",
        hint_tpl.get(lang, hint_tpl["ru"]).format(total),
        "",
    ]
    for i, word in enumerate(page):
        if isinstance(word, dict):
            _format_word_block(word, i, lang, lines)
    lines.append("─────────────")
    return "\n".join(lines)


def format_vocab_2(lesson, lang: str) -> str:
    """V2: 9+ so'zlar (vocab_2 step). Bo'sh bo'lsa, bo'sh string qaytaradi."""
    vocab = _parse(lesson.vocabulary_json, [])
    page  = vocab[8:]
    if not page:
        return ""
    title = _parse_title(lesson.title or "")

    hdr = {
        "uz": "📖 Yangi so'zlar — davomi 🇨🇳",
        "tj": "📖 Калимаҳои нав — давом 🇨🇳",
        "ru": "📖 Новые слова — продолжение 🇨🇳",
    }

    lines = [
        f"<b>【{_lesson_word(lang)} {lesson.lesson_order}】 {title}</b>",
        hdr.get(lang, hdr["ru"]),
        "",
    ]
    for i, word in enumerate(page):
        if isinstance(word, dict):
            _format_word_block(word, i, lang, lines)
    lines.append("─────────────")
    return "\n".join(lines)


def format_block_vocab(lesson, lang: str, n: int) -> str:
    """Dialogga bog'langan kichik qism so'zlari."""
    block = _block_by_no(lesson, n)
    words = _block_words(lesson, block)
    if not block or not words:
        return ""

    title = _parse_title(lesson.title or "")
    total = len(_lesson_blocks(lesson))
    section = block.get("section_label", "") or f"课文 {n}"
    scene = block.get(f"scene_{lang}") or block.get("scene_label_zh") or ""
    header = " · ".join(filter(None, [section, scene]))

    hdr = {
        "uz": "📖 Shu dialogdagi yangi so'zlar",
        "tj": "📖 Калимаҳои нави ҳамин муколама",
        "ru": "📖 Новые слова этого диалога",
    }
    hint_tpl = {
        "uz": "Avval <b>{}</b> ta so'zni yengil olamiz, keyin dialogga o'tamiz.",
        "tj": "Аввал <b>{}</b> калимаро сабук мегирем, баъд ба муколама мегузарем.",
        "ru": "Сначала спокойно берём <b>{}</b> слова, затем переходим к диалогу.",
    }

    lines = [
        f"<b>【{_lesson_word(lang)} {lesson.lesson_order} · {_block_label(lang, n, total)}】 {title}</b>",
        hdr.get(lang, hdr["ru"]),
        "",
    ]
    if header:
        lines.append(f"📍 <b>{header}</b>")
        lines.append("")
    lines.extend([hint_tpl.get(lang, hint_tpl["ru"]).format(len(words)), ""])

    for i, word in enumerate(words):
        _format_word_block(word, i, lang, lines)
    lines.append("─────────────")
    return "\n".join(lines)


def format_block_quiz(lesson, lang: str, n: int) -> str:
    block = _block_by_no(lesson, n)
    title = _parse_title(lesson.title or "")
    total = len(_lesson_blocks(lesson))
    questions = block.get("mini_quiz") or []

    hdr = {
        "uz": "📝 Kichik test",
        "tj": "📝 Тести хурд",
        "ru": "📝 Мини-тест",
    }
    intro = {
        "uz": "Keyingi qismga o'tishdan oldin shu dialogni tez tekshiramiz.",
        "tj": "Пеш аз қисми навбатӣ ҳамин муколамаро зуд месанҷем.",
        "ru": "Перед следующей частью быстро проверим этот диалог.",
    }
    answer_hint = {
        "uz": "Mini App ochilmasa, javoblarni shu yerga yozishingiz mumkin.",
        "tj": "Агар Mini App кушода нашавад, ҷавобҳоро ҳамин ҷо нависед.",
        "ru": "Если Mini App не откроется, можно написать ответы здесь.",
    }

    lines = [
        f"<b>【{_lesson_word(lang)} {lesson.lesson_order} · {_block_label(lang, n, total)}】 {title}</b>",
        hdr.get(lang, hdr["ru"]),
        "",
        intro.get(lang, intro["ru"]),
        "",
    ]

    if isinstance(questions, list) and questions:
        for index, item in enumerate(questions, 1):
            if not isinstance(item, dict):
                continue
            prompt = (
                item.get(f"prompt_{lang}")
                or _uz_fallback(lang, item.get("prompt_uz"))
                or item.get("prompt")
                or item.get("question")
                or ""
            )
            if prompt:
                lines.append(f"{index}. {prompt}")
        lines.append("")

    lines.append(answer_hint.get(lang, answer_hint["ru"]))
    return "\n".join(lines).rstrip()


def format_block_grammar(lesson, lang: str, n: int) -> str:
    block = _block_by_no(lesson, n)
    if not block:
        return ""

    title = _parse_title(lesson.title or "")
    total = len(_lesson_blocks(lesson))
    section = block.get("section_label", "") or f"课文 {n}"
    scene = block.get(f"scene_{lang}") or block.get("scene_label_zh") or ""
    header = " · ".join(filter(None, [section, scene]))
    grammar_notes = block.get("grammar_notes") or []
    grammar_items = _block_grammar_items(lesson, block)
    if grammar_items:
        grammar_notes = []

    if not grammar_notes and not grammar_items:
        return ""

    hdr = {
        "uz": "📐 Shu dialog grammatikasi",
        "tj": "📐 Грамматикаи ҳамин муколама",
        "ru": "📐 Грамматика этого диалога",
    }

    lines = [
        f"<b>【{_lesson_word(lang)} {lesson.lesson_order} · {_block_label(lang, n, total)}】 {title}</b>",
        hdr.get(lang, hdr["ru"]),
        "",
    ]
    if header:
        lines.append(f"📍 <b>{header}</b>")
        lines.append("")

    for note in grammar_notes:
        if not isinstance(note, dict):
            continue
        pattern = note.get(f"pattern_{lang}") or note.get("pattern", "")
        explanation = (
            note.get(f"explanation_{lang}")
            or _uz_fallback(lang, note.get("explanation_uz"))
            or note.get("explanation", "")
        )
        ex_zh = note.get("example_zh", "")
        ex_pin = note.get("example_pinyin", "")
        ex_tr = (
            note.get(f"example_{lang}")
            or _uz_fallback(lang, note.get("example_uz"))
            or note.get("example_translation", "")
        )
        lines.append("━━━━━━━━━━━━━━")
        if pattern:
            lines.append(f"📌 <b>{pattern}</b>")
        if explanation:
            lines.append(f"   {explanation}")
        if ex_zh:
            lines.append("")
            lines.append(f"   💬 <b>{ex_zh}</b>")
            if ex_pin:
                lines.append(f"      <i>{ex_pin}</i>")
            if ex_tr:
                lines.append(f"      {ex_tr}")
        lines.append("")

    for index, item in enumerate(grammar_items, 1):
        g_title = item.get(f"title_{lang}") or _uz_fallback(lang, item.get("title_uz")) or item.get("title_zh") or ""
        rule = (
            item.get(f"rule_{lang}")
            or _uz_fallback(lang, item.get("rule_uz"))
            or item.get("explanation")
            or item.get("rule")
            or ""
        )

        lines.append("━━━━━━━━━━━━━━")
        lines.append(f"<b>📌 {index}. {g_title}</b>")
        lines.append("")
        if rule:
            for rule_line in rule.split("\n"):
                lines.append(f"   {rule_line}")
        examples = item.get("examples", [])
        if examples:
            eg_label = {"uz": "💬 Misollar:", "tj": "💬 Мисолҳо:", "ru": "💬 Примеры:"}
            lines.append("")
            lines.append(f"   {eg_label.get(lang, eg_label['ru'])}")
            for ex in examples[:3]:
                if not isinstance(ex, dict):
                    continue
                zh = ex.get("zh", "")
                pinyin = ex.get("pinyin", "")
                meaning = ex.get(lang) or _uz_fallback(lang, ex.get("uz")) or ex.get("meaning") or ""
                lines.append(f"   • <b>{zh}</b> <i>({pinyin})</i> — {meaning}")
        lines.append("")

    lines.append("━━━━━━━━━━━━━━")
    return "\n".join(lines).rstrip()


def format_dialogue_n(lesson, lang: str, n: int) -> str:
    """V2: n-chi dialog bloki (1-indexed), grammar_notes inline qo'yilgan."""
    dialogues = _parse(lesson.dialogue_json, [])
    if not isinstance(dialogues, list) or n < 1 or n > len(dialogues):
        return ""
    block = dialogues[n - 1]
    if not isinstance(block, dict):
        return ""

    title   = _parse_title(lesson.title or "")
    section = block.get("section_label", "") or f"课文 {n}"
    scene   = (
        block.get(f"scene_{lang}")
        or block.get("scene_label_zh")
        or ""
    )
    header  = " · ".join(filter(None, [section, scene]))

    dlg_hdr = {
        "uz": "🎭 Dialog",
        "tj": "🎭 Муколама",
        "ru": "🎭 Диалог",
    }
    text_hdr = {
        "uz": "📘 Matn",
        "tj": "📘 Матн",
        "ru": "📘 Текст",
    }
    is_text_block = _is_narration_block(block)

    total = len(_lesson_blocks(lesson))
    part = f" · {_block_label(lang, n, total)}" if total else ""

    lines = [
        f"<b>【{_lesson_word(lang)} {lesson.lesson_order}{part}】 {title}</b>",
        f"{(text_hdr if is_text_block else dlg_hdr).get(lang, dlg_hdr['ru'])} {n}",
        "",
    ]
    if header:
        lines.append(f"📍 <b>{header}</b>")
        lines.append("")

    lines.append("━━━━━━━━━━━━━━")

    dialogue_lines = block.get("dialogue") or block.get("lines") or []
    for line in dialogue_lines:
        if not isinstance(line, dict):
            continue
        if _is_narration_line(line):
            _append_text_line(lines, line, lang)
            continue
        speaker     = line.get("speaker", "")
        zh          = line.get("zh", "")
        pinyin      = line.get("pinyin", "")
        translation = (
            _uz_fallback(lang, line.get("translation"))
            or line.get(lang)
            or _uz_fallback(lang, line.get("uz"))
            or ""
        )
        icon = "👤" if speaker == "A" else "👥"
        lines.append(f"{icon} <b>{speaker}:</b>  <b>{zh}</b>")
        lines.append(f"       <i>{pinyin}</i>")
        lines.append(f"       {translation}")
        lines.append("")

    lines.append("━━━━━━━━━━━━━━")

    # ─── Inline grammatika eslatmalari ────────────────────────────
    show_inline_grammar = not (
        block.get("word_nos") or block.get("grammar_nos") or block.get("mini_quiz")
    )
    grammar_notes = block.get("grammar_notes", []) if show_inline_grammar else []
    if grammar_notes:
        gram_hdr = {
            "uz": "📐 Grammatika eslatmasi",
            "tj": "📐 Эзоҳи грамматикӣ",
            "ru": "📐 Грамматическая заметка",
        }
        lines.append("")
        lines.append(f"<b>{gram_hdr.get(lang, gram_hdr['ru'])}</b>")
        lines.append("")
        for note in grammar_notes:
            if not isinstance(note, dict):
                continue
            pattern = note.get(f"pattern_{lang}") or note.get("pattern", "")
            explanation = (
                note.get(f"explanation_{lang}")
                or _uz_fallback(lang, note.get("explanation_uz"))
                or note.get("explanation", "")
            )
            ex_zh  = note.get("example_zh", "")
            ex_pin = note.get("example_pinyin", "")
            ex_tr  = (
                note.get(f"example_{lang}")
                or _uz_fallback(lang, note.get("example_uz"))
                or note.get("example_translation", "")
            )
            if pattern:
                lines.append(f"📌 <b>{pattern}</b>")
            if explanation:
                lines.append(f"   {explanation}")
            if ex_zh:
                lines.append(f"   💬 <b>{ex_zh}</b>")
                if ex_pin:
                    lines.append(f"      <i>{ex_pin}</i>")
                if ex_tr:
                    lines.append(f"      {ex_tr}")
            lines.append("")

    return "\n".join(lines).rstrip()


def format_grammar_v2(lesson, lang: str) -> str:
    """V2: grammatika — step raqamisiz, toza ko'rinish."""
    grammar = _parse(lesson.grammar_json, [])
    if not grammar:
        return ""

    title = _parse_title(lesson.title or "")
    hdr = {
        "uz": "📐 Grammatika",
        "tj": "📐 Грамматика",
        "ru": "📐 Грамматика",
    }

    lines = [
        f"<b>【{title}】</b>",
        f"{hdr.get(lang, hdr['ru'])}",
        "",
    ]

    for i, g in enumerate(grammar, 1):
        if not isinstance(g, dict):
            continue

        g_title = g.get(f"title_{lang}") or _uz_fallback(lang, g.get("title_uz")) or g.get("title_zh") or ""
        rule = (
            g.get(f"rule_{lang}")
            or _uz_fallback(lang, g.get("rule_uz"))
            or g.get("explanation")
            or g.get("rule")
            or ""
        )

        lines.append("━━━━━━━━━━━━━━")
        lines.append(f"<b>📌 {i}. {g_title}</b>")
        lines.append("")
        for rule_line in rule.split("\n"):
            lines.append(f"   {rule_line}")
        lines.append("")

        examples = g.get("examples", [])
        if examples:
            eg_label = {"uz": "💬 Misollar:", "tj": "💬 Мисолҳо:", "ru": "💬 Примеры:"}
            lines.append(f"   {eg_label.get(lang, eg_label['ru'])}")
            for ex in examples:
                zh = ex.get("zh", "")
                pinyin = ex.get("pinyin", "")
                meaning = ex.get(lang) or _uz_fallback(lang, ex.get("uz")) or ex.get("meaning") or ""
                lines.append(f"   • <b>{zh}</b> <i>({pinyin})</i> — {meaning}")
            lines.append("")

    lines.append("━━━━━━━━━━━━━━")
    return "\n".join(lines)


def format_satisfaction_check(lesson, lang: str) -> str:
    title = _parse_title(lesson.title or "")
    labels = {
        "uz": "Dars yakuni",
        "tj": "Анҷоми дарс",
        "ru": "Итог урока",
    }
    questions = {
        "uz": "Darsdagi so'zlar, dialoglar va test tushunarli bo'ldimi?",
        "tj": "Калимаҳо, муколамаҳо ва санҷиши дарс фаҳмо буданд?",
        "ru": "Слова, диалоги и тест урока были понятны?",
    }
    return "\n".join(
        [
            f"<b>【{title}】</b>",
            f"✅ {labels.get(lang, labels['ru'])}",
            "",
            questions.get(lang, questions["ru"]),
        ]
    )


def format_review(lesson, lang: str) -> str:
    review = _parse(getattr(lesson, "review_json", None), [])
    vocab_fallback = _parse(getattr(lesson, "vocabulary_json", None), [])
    dialogue_fallback = _parse(getattr(lesson, "dialogue_json", None), [])
    grammar_fallback = _parse(getattr(lesson, "grammar_json", None), [])
    title = _parse_title(lesson.title or "")

    if isinstance(review, list) and review and isinstance(review[0], dict):
        item = review[0]
        vocab = item.get("vocabulary") or vocab_fallback[:10]
        dialogues = item.get("dialogues") or dialogue_fallback
        grammar = item.get("grammar") or [
            g.get("title_zh", "")
            for g in grammar_fallback
            if isinstance(g, dict) and g.get("title_zh")
        ]
        review_title = item.get(f"title_{lang}") or _uz_fallback(lang, item.get("title_uz")) or title
    else:
        vocab = vocab_fallback[:10]
        dialogues = dialogue_fallback
        grammar = [
            g.get("title_zh", "")
            for g in grammar_fallback
            if isinstance(g, dict) and g.get("title_zh")
        ]
        review_title = title

    hdr = {
        "uz": "🔁 Qisqa takrorlash",
        "tj": "🔁 Такрори кӯтоҳ",
        "ru": "🔁 Краткое повторение",
    }
    vocab_hdr = {"uz": "Asosiy so'zlar:", "tj": "Калимаҳои асосӣ:", "ru": "Ключевые слова:"}
    dialog_hdr = {"uz": "Dialoglar:", "tj": "Муколамаҳо:", "ru": "Диалоги:"}
    grammar_hdr = {"uz": "Grammatika:", "tj": "Грамматика:", "ru": "Грамматика:"}

    lines = [f"<b>{review_title}</b>", hdr.get(lang, hdr["ru"]), ""]

    if vocab:
        lines.append(f"<b>{vocab_hdr.get(lang, vocab_hdr['ru'])}</b>")
        for word in vocab[:10]:
            if not isinstance(word, dict):
                continue
            zh = word.get("zh", "")
            pinyin = word.get("pinyin", "")
            meaning = word.get(lang) or _uz_fallback(lang, word.get("uz")) or word.get("meaning") or ""
            lines.append(f"• <b>{zh}</b> <i>{pinyin}</i> — {meaning}")
        lines.append("")

    if dialogues:
        lines.append(f"<b>{dialog_hdr.get(lang, dialog_hdr['ru'])}</b>")
        for block in dialogues[:4]:
            if not isinstance(block, dict):
                continue
            section = block.get("section_label", "")
            scene = block.get(f"scene_{lang}") or _uz_fallback(lang, block.get("scene_uz")) or block.get("scene_label_zh") or ""
            lines.append(f"• {' · '.join(filter(None, [section, scene]))}")
        lines.append("")

    if grammar:
        lines.append(f"<b>{grammar_hdr.get(lang, grammar_hdr['ru'])}</b>")
        for item in grammar[:6]:
            lines.append(f"• {item}")

    return "\n".join(lines).rstrip()


def format_step(lesson, lang: str, step: str) -> str | None:
    """Universal dispatcher: har qanday step nomi uchun formatlangan matn qaytaradi.

    Agar step formatter_map da bo'lmasa — None qaytaradi.
    """
    if step == "intro":
        return format_intro(lesson, lang)
    if step == "vocab":
        return format_vocab(lesson, lang)
    if step == "vocab_1":
        return format_vocab_1(lesson, lang)
    if step == "vocab_2":
        return format_vocab_2(lesson, lang)
    if step.startswith("block_vocab_"):
        try:
            n = int(step.split("_", 2)[2])
        except (ValueError, IndexError):
            n = 1
        return format_block_vocab(lesson, lang, n)
    if step == "dialogue":
        return format_dialogue(lesson, lang)
    if step.startswith("dialogue_"):
        try:
            n = int(step.split("_", 1)[1])
        except (ValueError, IndexError):
            n = 1
        return format_dialogue_n(lesson, lang, n)
    if step == "grammar":
        return format_grammar_v2(lesson, lang)
    if step.startswith("block_grammar_"):
        try:
            n = int(step.split("_", 2)[2])
        except (ValueError, IndexError):
            n = 1
        return format_block_grammar(lesson, lang, n)
    if step == "exercise":
        return format_exercise(lesson, lang)
    if step.startswith("block_quiz_"):
        try:
            n = int(step.split("_", 2)[2])
        except (ValueError, IndexError):
            n = 1
        return format_block_quiz(lesson, lang, n)
    if step == "satisfaction_check":
        return format_satisfaction_check(lesson, lang)
    if step == "review":
        return format_review(lesson, lang)
    return None


# ─────────────────────────────────────────────────────────────────────────────
# V1 formatters (original, o'zgarmagan)
# ─────────────────────────────────────────────────────────────────────────────

def format_intro(lesson, lang: str, lesson_total_steps: int = 6) -> str:
    title = _parse_title(lesson.title or "")
    intro_raw = lesson.intro_text or ""

    try:
        intro_data = json.loads(intro_raw) if isinstance(intro_raw, str) else intro_raw
        intro = intro_data.get(lang) or _uz_fallback(lang, intro_data.get("uz")) or str(intro_data)
    except Exception:
        intro = intro_raw

    step_label = {"uz": "Darsga xush kelibsiz! 🎉", "tj": "Хуш омадед ба дарс! 🎉", "ru": "Добро пожаловать на урок! 🎉"}
    lines = [
        f"【{_lesson_word(lang)} {lesson.lesson_order}】 {title}",
        "",
        step_label.get(lang, step_label["ru"]),
        "",
        "━━━━━━━━━━━━━━",
        intro,
        "━━━━━━━━━━━━━━",
    ]

    return "\n".join(lines)
