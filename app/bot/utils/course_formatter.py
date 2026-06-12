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


_GRAMMAR_DETAIL_LABELS = {
    "meaning": {"uz": "Ma'nosi", "ru": "Значение", "tj": "Маъно"},
    "use": {"uz": "Qachon ishlatiladi", "ru": "Когда использовать", "tj": "Кай истифода мешавад"},
    "pattern": {"uz": "Qolip", "ru": "Шаблон", "tj": "Қолаб"},
    "example": {"uz": "Dialogdan misol", "ru": "Пример из диалога", "tj": "Мисол аз муколама"},
    "analysis": {"uz": "Tahlil", "ru": "Разбор", "tj": "Таҳлил"},
    "attention": {"uz": "E'tibor", "ru": "Важно", "tj": "Муҳим"},
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
        "emphasis": {
            "uz": "Gapda kutilganidan kuchliroq holat ta'kidlanadi; odatda 都/也 natijani kuchaytiradi.",
            "ru": "В предложении подчеркивается более сильный или неожиданный случай; 都/也 обычно усиливает результат.",
            "tj": "Дар ҷумла ҳолати қавитар ё ғайричашмдошт таъкид мешавад; 都/也 натиҷаро қавитар мекунад.",
        },
        "condition": {
            "uz": "Birinchi qism shart yoki vaziyatni beradi, ikkinchi qism esa shu shartdagi natijani ko'rsatadi.",
            "ru": "Первая часть задает условие или ситуацию, вторая показывает результат при этом условии.",
            "tj": "Қисми аввал шарт ё вазъиятро медиҳад, қисми дуюм натиҷаи онро нишон медиҳад.",
        },
        "contrast": {
            "uz": "Oldingi fikrdan keyin qarama-qarshi yoki kutilmagan natija keladi; tarjimada 'ammo/lekin' ohangi kuchli.",
            "ru": "После первой мысли идет противоположный или неожиданный результат; смысл близок к 'однако/но'.",
            "tj": "Баъди фикри аввал натиҷаи муқобил ё ғайричашмдошт меояд; маънояш ба 'аммо/вале' наздик аст.",
        },
        "sequence": {
            "uz": "Bu qolip gapdagi fikrlarni tartiblaydi: qo'shimcha ma'lumot, davomiy qadam yoki parallel holat qo'shadi.",
            "ru": "Этот шаблон упорядочивает мысль: добавляет информацию, следующий шаг или параллельное действие.",
            "tj": "Ин қолаб фикрро тартиб медиҳад: маълумоти иловагӣ, қадами баъдӣ ё ҳолати ҳамзамон меорад.",
        },
        "topic": {
            "uz": "Qolip mavzu, soha yoki baholash nuqtasini oldinga chiqaradi; undan keyin asosiy fikr aytiladi.",
            "ru": "Шаблон выносит тему, сферу или точку оценки вперед; затем идет основная мысль.",
            "tj": "Қолаб мавзу, соҳа ё нуқтаи баҳоро пеш меорад; баъд фикри асосӣ гуфта мешавад.",
        },
        "complement": {
            "uz": "Bu yerda ma'no faqat fe'lda emas, fe'ldan keyingi qo'shimcha qismda ham turibdi; natija/yo'nalish/holatni tekshiring.",
            "ru": "Смысл не только в глаголе, но и в части после него; проверьте результат, направление или состояние.",
            "tj": "Маъно танҳо дар феъл нест, балки дар қисми баъди феъл ҳам ҳаст; натиҷа, самт ё ҳолатро санҷед.",
        },
        "generic": {
            "uz": "Avval gapdagi mantiqiy munosabatni toping, keyin xitoycha qolipni shu joyga qo'ying.",
            "ru": "Сначала найдите логическую связь в предложении, затем поставьте китайский шаблон в это место.",
            "tj": "Аввал робитаи мантиқии ҷумларо ёбед, баъд қолаби чиниро ба ҳамон ҷо гузоред.",
        },
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
        (("不仅", "不但"), {
            "uz": "Ikkinchi qismda odatda 也/还/而且 keladi; ikki tomonni ham ijobiy kuchaytiradi.",
            "ru": "Во второй части обычно стоит 也/还/而且; конструкция усиливает оба положительных признака.",
            "tj": "Дар қисми дуюм одатан 也/还/而且 меояд; ду хусусияти мусбатро қавитар мекунад.",
        }),
        (("从来",), {
            "uz": "Inkor ma'nosida ko'pincha 没/不 bilan ishlaydi: 从来没... = hech qachon ...magan.",
            "ru": "В отрицании обычно идет с 没/不: 从来没... = никогда не....",
            "tj": "Дар маънои инкор одатан бо 没/不 меояд: 从来没... = ҳеч вақт ... накардааст.",
        }),
        (("刚",), {
            "uz": "刚 fe'ldan oldin keladi va 'hozirgina/yangi' ma'nosini beradi; uzoq o'tmish uchun ishlatmang.",
            "ru": "刚 ставится перед глаголом и значит 'только что/недавно'; не используйте для далекого прошлого.",
            "tj": "刚 пеш аз феъл меояд ва маънои 'нав/ҳозир' медиҳад; барои гузаштаи дур истифода накунед.",
        }),
        (("即使", "尽管", "无论", "不管", "再"), {
            "uz": "Natija qismida ko'pincha 也/都/还 keladi; shu so'z natija o'zgarmasligini ko'rsatadi.",
            "ru": "В части результата часто стоит 也/都/还; оно показывает, что результат не меняется.",
            "tj": "Дар қисми натиҷа одатан 也/都/还 меояд; он тағйир наёфтани натиҷаро нишон медиҳад.",
        }),
        (("否则",), {
            "uz": "Avval maslahat/shart keladi, keyin 否则 bilan yomon yoki kutilmagan natija aytiladi.",
            "ru": "Сначала идет совет или условие, затем через 否则 называется нежелательный результат.",
            "tj": "Аввал маслиҳат ё шарт меояд, баъд бо 否则 натиҷаи номатлуб гуфта мешавад.",
        }),
        (("然而", "却", "相反", "不过"), {
            "uz": "Bular oddiy 'va' emas; oldingi fikrga burilish yoki qarama-qarshi natija qo'shadi.",
            "ru": "Это не простое 'и'; слова дают поворот мысли или противоположный результат.",
            "tj": "Инҳо 'ва'-и одӣ нестанд; гардиши фикр ё натиҷаи муқобил меоранд.",
        }),
        (("并且", "同时", "另外", "除此以外"), {
            "uz": "Ikkinchi fikr birinchisini davom ettiradi yoki qo'shimcha qiladi; qarama-qarshilik ma'nosi yo'q.",
            "ru": "Вторая мысль продолжает или дополняет первую; противопоставления здесь нет.",
            "tj": "Фикри дуюм аввалиро идома ё пурра мекунад; маънои муқобил нест.",
        }),
        (("对于", "在于", "说起"), {
            "uz": "Bu qolipdan keyin mavzu keladi; asosiy hukm yoki baho keyingi qismda aytiladi.",
            "ru": "После шаблона идет тема; главное суждение или оценка дается дальше.",
            "tj": "Баъди қолаб мавзу меояд; ҳукм ё баҳои асосӣ дар қисми баъдӣ гуфта мешавад.",
        }),
        (("是否",), {
            "uz": "是否 yozma va rasmiyroq uslub; og'zaki nutqda ko'pincha 是不是 ishlatiladi.",
            "ru": "是否 более письменное и официальное; в разговоре чаще используют 是不是.",
            "tj": "是否 бештар хаттӣ ва расмӣ аст; дар гуфтор бештар 是不是 истифода мешавад.",
        }),
        (("把",), {
            "uz": "把 dan keyingi obyektga nima bo'lganini fe'l va natija qismi bilan aniq ko'rsating.",
            "ru": "После 把 нужно ясно показать, что произошло с объектом, через глагол и результат.",
            "tj": "Баъди 把 бояд бо феъл ва натиҷа нишон диҳед, ки бо объект чӣ шуд.",
        }),
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
        eg_label = {"uz": "💬 Misollar:", "tj": "💬 Мисолҳо:", "ru": "💬 Примеры:"}
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
        "uz": "Quizdan o'ting: qani, shu qismdagi yangi so'zlar va grammatikadan nimani eslab qoldingiz?",
        "tj": "Quiz-ро гузаред: бинем, аз калимаҳои нав ва грамматикаи ҳамин қисм чӣ дар хотир монд?",
        "ru": "Пройдите quiz: посмотрим, что осталось в памяти по новым словам и грамматике этой части.",
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
        if _is_hsk4_lesson(lesson):
            _append_hsk4_grammar_item(lines, g, lang, i)
        else:
            _append_basic_grammar_item(lines, g, lang, i)

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
