from app.bot.utils.i18n import bot_locale_map
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
    return bot_locale_map('inline.utils.course_formatter.helper_lesson_word.copy1').get(lang, "Урок")


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
    labels = bot_locale_map('inline.utils.course_formatter.helper_block_label.copy1')
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


_GRAMMAR_DETAIL_LABELS = {
    "meaning": bot_locale_map('inline.utils.course_formatter.module.copy1'),
    "use": bot_locale_map('inline.utils.course_formatter.module.copy2'),
    "pattern": bot_locale_map('inline.utils.course_formatter.module.copy3'),
    "example": bot_locale_map('inline.utils.course_formatter.module.copy4'),
    "analysis": bot_locale_map('inline.utils.course_formatter.module.copy5'),
    "attention": bot_locale_map('inline.utils.course_formatter.module.copy6'),
}


def _detail_label(key: str, lang: str) -> str:
    labels = _GRAMMAR_DETAIL_LABELS.get(key, {})
    return labels.get(lang, labels.get("ru", key))


def _lesson_level(lesson) -> str:
    return str(getattr(lesson, "level", "") or "").strip().lower()


def _lesson_code(lesson) -> str:
    return str(getattr(lesson, "lesson_code", "") or "").strip().upper()


def _is_hsk4_lesson(lesson) -> bool:
    return _lesson_level(lesson) == "hsk4" or _lesson_code(lesson).startswith("HSK4")


def _grammar_title(item: dict, lang: str) -> str:
    return item.get(f"title_{lang}") or _uz_fallback(lang, item.get("title_uz")) or item.get("title_zh") or ""


def _grammar_meaning(item: dict, lang: str) -> str:
    title_zh = item.get("title_zh") or ""
    title_lang = item.get(f"title_{lang}") or _uz_fallback(lang, item.get("title_uz")) or ""
    if title_lang and title_lang != title_zh:
        return title_lang
    return ""


def _grammar_rule(item: dict, lang: str) -> str:
    return (
        item.get(f"rule_{lang}")
        or _uz_fallback(lang, item.get("rule_uz"))
        or item.get("explanation")
        or item.get("rule")
        or ""
    )


def _grammar_formula(item: dict) -> str:
    return item.get("formula") or item.get("pattern") or item.get("title_zh") or ""


def _grammar_examples(item: dict) -> list[dict]:
    examples = item.get("examples") or []
    return [example for example in examples if isinstance(example, dict)]


def _hsk4_grammar_analysis(title_zh: str, lang: str) -> str:
    title = (title_zh or "").replace(" ", "")
    texts = {
        "emphasis": bot_locale_map('inline.utils.course_formatter.helper_hsk4_grammar_analysis.copy1'),
        "condition": bot_locale_map('inline.utils.course_formatter.helper_hsk4_grammar_analysis.copy2'),
        "contrast": bot_locale_map('inline.utils.course_formatter.helper_hsk4_grammar_analysis.copy3'),
        "sequence": bot_locale_map('inline.utils.course_formatter.helper_hsk4_grammar_analysis.copy4'),
        "topic": bot_locale_map('inline.utils.course_formatter.helper_hsk4_grammar_analysis.copy5'),
        "complement": bot_locale_map('inline.utils.course_formatter.helper_hsk4_grammar_analysis.copy6'),
        "generic": bot_locale_map('inline.utils.course_formatter.helper_hsk4_grammar_analysis.copy7'),
    }

    if any(marker in title for marker in ("连", "甚至", "都/也")):
        key = "emphasis"
    elif any(marker in title for marker in ("即使", "尽管", "虽然", "无论", "不管", "再", "只有", "只要", "一……就", "否则", "如果")):
        key = "condition"
    elif any(marker in title for marker in ("然而", "却", "相反", "不过", "而不是", "而")):
        key = "contrast"
    elif any(marker in title for marker in ("同时", "另外", "并且", "接着", "首先", "其次", "除此以外", "总的来说")):
        key = "sequence"
    elif any(marker in title for marker in ("对于", "在于", "说起", "V+起", "方面", "上")):
        key = "topic"
    elif any(marker in title for marker in ("起来", "出来", "下去", "上", "受不了", "V+着+V+着")):
        key = "complement"
    else:
        key = "generic"

    return texts[key].get(lang, texts[key]["ru"])


def _hsk4_grammar_tip(title_zh: str, lang: str) -> str:
    title = (title_zh or "").replace(" ", "")
    tips = [
        (("不仅", "不但"), bot_locale_map('inline.utils.course_formatter.helper_hsk4_grammar_tip.copy1')),
        (("从来",), bot_locale_map('inline.utils.course_formatter.helper_hsk4_grammar_tip.copy2')),
        (("刚",), bot_locale_map('inline.utils.course_formatter.helper_hsk4_grammar_tip.copy3')),
        (("即使", "尽管", "无论", "不管", "再"), bot_locale_map('inline.utils.course_formatter.helper_hsk4_grammar_tip.copy4')),
        (("否则",), bot_locale_map('inline.utils.course_formatter.helper_hsk4_grammar_tip.copy5')),
        (("然而", "却", "相反", "不过"), bot_locale_map('inline.utils.course_formatter.helper_hsk4_grammar_tip.copy6')),
        (("并且", "同时", "另外", "除此以外"), bot_locale_map('inline.utils.course_formatter.helper_hsk4_grammar_tip.copy7')),
        (("对于", "在于", "说起"), bot_locale_map('inline.utils.course_formatter.helper_hsk4_grammar_tip.copy8')),
        (("是否",), bot_locale_map('inline.utils.course_formatter.helper_hsk4_grammar_tip.copy9')),
        (("把",), bot_locale_map('inline.utils.course_formatter.helper_hsk4_grammar_tip.copy10')),
    ]
    for markers, localized in tips:
        if any(marker in title for marker in markers):
            return localized.get(lang, localized["ru"])
    return ""


def _append_basic_grammar_item(lines: list[str], item: dict, lang: str, index: int) -> None:
    g_title = _grammar_title(item, lang)
    rule = _grammar_rule(item, lang)

    lines.append("━━━━━━━━━━━━━━")
    lines.append(f"<b>📌 {index}. {g_title}</b>")
    lines.append("")
    if rule:
        for rule_line in rule.split("\n"):
            lines.append(f"   {rule_line}")

    examples = _grammar_examples(item)
    if examples:
        eg_label = bot_locale_map('inline.utils.course_formatter.helper_append_basic_grammar_item.copy1')
        lines.append("")
        lines.append(f"   {eg_label.get(lang, eg_label['ru'])}")
        for ex in examples[:3]:
            zh = ex.get("zh", "")
            pinyin = ex.get("pinyin", "")
            meaning = ex.get(lang) or _uz_fallback(lang, ex.get("uz")) or ex.get("meaning") or ""
            lines.append(f"   • <b>{zh}</b> <i>({pinyin})</i> — {meaning}")
    lines.append("")


def _append_hsk4_grammar_item(lines: list[str], item: dict, lang: str, index: int) -> None:
    title_zh = item.get("title_zh") or ""
    g_title = _grammar_title(item, lang)
    meaning = _grammar_meaning(item, lang)
    rule = _grammar_rule(item, lang)
    formula = _grammar_formula(item)
    examples = _grammar_examples(item)
    first_example = examples[0] if examples else {}

    lines.append("━━━━━━━━━━━━━━")
    lines.append(f"<b>📌 {index}. {g_title}</b>")
    lines.append("")

    if formula:
        pattern_line = f"<b>{_detail_label('pattern', lang)}:</b> <code>{formula}</code>"
        if meaning:
            pattern_line += f" — {meaning}"
        lines.append(pattern_line)
    elif meaning:
        lines.append(f"<b>{_detail_label('meaning', lang)}:</b> {meaning}")
    if rule:
        lines.append(f"<b>{_detail_label('use', lang)}:</b> {rule}")

    if first_example:
        zh = first_example.get("zh", "")
        pinyin = first_example.get("pinyin", "")
        meaning = (
            first_example.get(lang)
            or _uz_fallback(lang, first_example.get("uz"))
            or first_example.get("meaning")
            or ""
        )
        lines.append("")
        lines.append(f"<b>{_detail_label('example', lang)}:</b>")
        if zh:
            example_line = f"<b>{zh}</b>"
            if pinyin:
                example_line += f" <i>{pinyin}</i>"
            lines.append(example_line)
        if meaning:
            lines.append(meaning)

    tip = _hsk4_grammar_tip(title_zh or g_title, lang)
    lines.append("")
    lines.append(
        f"<b>{_detail_label('attention', lang)}:</b> "
        f"{tip or _hsk4_grammar_analysis(title_zh or g_title, lang)}"
    )
    lines.append("")


def format_vocab(lesson, lang: str, lesson_total_steps: int = 6) -> str:
    vocab = _parse(lesson.vocabulary_json, [])
    title = _parse_title(lesson.title or "")

    label = bot_locale_map('inline.utils.course_formatter.format_vocab.copy1')
    lines = [f"【1/{lesson_total_steps}】 {title} · {label.get(lang, label['ru'])}", ""]

    hint = bot_locale_map('inline.utils.course_formatter.format_vocab.dynamic1', value1=len(vocab))
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

    step_label = bot_locale_map('inline.utils.course_formatter.format_dialogue.copy1')
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
            tip = bot_locale_map('inline.utils.course_formatter.format_dialogue.copy2')
            lines.append(tip.get(lang, tip["ru"]))
            for note in notes:
                note_text = note.get(lang) or _uz_fallback(lang, note.get("uz")) or ""
                if note_text:
                    lines.append(note_text)

        lines.append("")

    return "\n".join(lines).rstrip()




def format_exercise(lesson, lang: str, lesson_total_steps: int = 6) -> str:
    exercises = _parse(lesson.exercise_json, [])
    title = _parse_title(lesson.title or "")

    step_label = bot_locale_map('inline.utils.course_formatter.format_exercise.copy1')
    lines = [f"【5/{lesson_total_steps}】 {title} · {step_label.get(lang, step_label['ru'])}", ""]

    hint = bot_locale_map('inline.utils.course_formatter.format_exercise.copy2')
    lines.append(hint.get(lang, hint["ru"]))
    lines.append("")

    answer_hint = bot_locale_map('inline.utils.course_formatter.format_exercise.copy3')

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

    hdr = bot_locale_map('inline.utils.course_formatter.format_vocab_1.copy1')
    hint_tpl = bot_locale_map('inline.utils.course_formatter.format_vocab_1.copy2')

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

    hdr = bot_locale_map('inline.utils.course_formatter.format_vocab_2.copy1')

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

    hdr = bot_locale_map('inline.utils.course_formatter.format_block_vocab.copy1')
    hint_tpl = bot_locale_map('inline.utils.course_formatter.format_block_vocab.copy2')

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

    hdr = bot_locale_map('inline.utils.course_formatter.format_block_quiz.copy1')
    intro = bot_locale_map('inline.utils.course_formatter.format_block_quiz.copy2')
    answer_hint = bot_locale_map('inline.utils.course_formatter.format_block_quiz.copy3')

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

    hdr = bot_locale_map('inline.utils.course_formatter.format_block_grammar.copy1')

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
        if _is_hsk4_lesson(lesson):
            _append_hsk4_grammar_item(lines, item, lang, index)
        else:
            _append_basic_grammar_item(lines, item, lang, index)

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

    dlg_hdr = bot_locale_map('inline.utils.course_formatter.format_dialogue_n.copy1')
    text_hdr = bot_locale_map('inline.utils.course_formatter.format_dialogue_n.copy2')
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
        gram_hdr = bot_locale_map('inline.utils.course_formatter.format_dialogue_n.copy3')
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
    hdr = bot_locale_map('inline.utils.course_formatter.format_grammar_v2.copy1')

    lines = [
        f"<b>【{title}】</b>",
        f"{hdr.get(lang, hdr['ru'])}",
        "",
    ]

    for i, g in enumerate(grammar, 1):
        if not isinstance(g, dict):
            continue
        if _is_hsk4_lesson(lesson):
            _append_hsk4_grammar_item(lines, g, lang, i)
        else:
            _append_basic_grammar_item(lines, g, lang, i)

    lines.append("━━━━━━━━━━━━━━")
    return "\n".join(lines)


def format_satisfaction_check(lesson, lang: str) -> str:
    title = _parse_title(lesson.title or "")
    labels = bot_locale_map('inline.utils.course_formatter.format_satisfaction_check.copy1')
    questions = bot_locale_map('inline.utils.course_formatter.format_satisfaction_check.copy2')
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

    hdr = bot_locale_map('inline.utils.course_formatter.format_review.copy1')
    vocab_hdr = bot_locale_map('inline.utils.course_formatter.format_review.copy2')
    dialog_hdr = bot_locale_map('inline.utils.course_formatter.format_review.copy3')
    grammar_hdr = bot_locale_map('inline.utils.course_formatter.format_review.copy4')

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

    step_label = bot_locale_map('inline.utils.course_formatter.format_intro.copy1')
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
