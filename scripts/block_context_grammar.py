CONTEXT_GRAMMAR_RULES = [
    {
        "pattern": "只要……就……",
        "all": ["只要", "就"],
        "explanation_uz": "Shart va natijani bog'laydi: birinchi qism bajarilsa, ikkinchi qism tabiiy natija bo'ladi.",
        "explanation_ru": "Связывает условие и результат: если выполняется первая часть, вторая становится естественным результатом.",
        "explanation_tj": "Шарт ва натиҷаро мепайвандад: агар қисми аввал иҷро шавад, қисми дуюм натиҷаи табиӣ мешавад.",
    },
    {
        "pattern": "不但……而且……",
        "all": ["不但", "而且"],
        "explanation_uz": "Ikki ijobiy fikrni kuchaytirib bog'laydi: nafaqat birinchi sifat, balki ikkinchisi ham bor.",
        "explanation_ru": "Усиливает две положительные характеристики: не только первое, но и второе.",
        "explanation_tj": "Ду фикри мусбатро қавӣ мепайвандад: на танҳо якум, балки дуюм ҳам ҳаст.",
    },
    {
        "pattern": "虽然……但是……",
        "all": ["虽然", "但是"],
        "explanation_uz": "Qarama-qarshi ikki fikrni bog'laydi: birinchi qism tan olinadi, asosiy natija ikkinchi qismda keladi.",
        "explanation_ru": "Связывает два противопоставленных факта: первая часть признается, главный результат во второй.",
        "explanation_tj": "Ду фикри муқобилро мепайвандад: қисми аввал қабул мешавад, натиҷаи асосӣ дар қисми дуюм меояд.",
    },
    {
        "pattern": "如果……就……",
        "all": ["如果", "就"],
        "explanation_uz": "Faraziy shart va natijani bildiradi: agar shunday bo'lsa, keyingi harakat yoki holat yuz beradi.",
        "explanation_ru": "Показывает условие и результат: если произойдет первое, произойдет и второе.",
        "explanation_tj": "Шарт ва натиҷаро нишон медиҳад: агар якум шавад, дуюм ҳам мешавад.",
    },
    {
        "pattern": "一边……一边……",
        "all": ["一边"],
        "explanation_uz": "Ikki harakat bir vaqtda bajarilayotganini bildiradi.",
        "explanation_ru": "Показывает, что два действия выполняются одновременно.",
        "explanation_tj": "Нишон медиҳад, ки ду амал ҳамзамон иҷро мешаванд.",
    },
    {
        "pattern": "除了……以外，还……",
        "all": ["除了", "以外", "还"],
        "explanation_uz": "Asosiy narsadan tashqari yana qo'shimcha narsa borligini bildiradi.",
        "explanation_ru": "Показывает, что помимо основной вещи есть еще что-то дополнительное.",
        "explanation_tj": "Нишон медиҳад, ки ғайр аз чизи асосӣ боз чизи иловагӣ ҳаст.",
    },
    {
        "pattern": "被 + kim/nima + V",
        "all": ["被"],
        "explanation_uz": "Majhul nisbat: gap markazida ta'sir ko'rgan odam yoki narsa turadi.",
        "explanation_ru": "Пассивная конструкция: в центре объект или человек, на которого подействовали.",
        "explanation_tj": "Сохтори маҷҳул: маркази ҷумла одам ё чизест, ки таъсир дидааст.",
    },
    {
        "pattern": "把 + object + V",
        "all": ["把"],
        "explanation_uz": "Obyektni oldinga chiqarib, unga nima qilinganini aniq ko'rsatadi.",
        "explanation_ru": "Выносит объект вперед и ясно показывает, что с ним сделали.",
        "explanation_tj": "Объектро пеш меорад ва равшан нишон медиҳад, ки бо он чӣ карданд.",
    },
    {
        "pattern": "为了 + maqsad",
        "all": ["为了"],
        "explanation_uz": "Harakat nima maqsadda qilinayotganini bildiradi.",
        "explanation_ru": "Показывает цель действия.",
        "explanation_tj": "Ҳадафи амалро нишон медиҳад.",
    },
    {
        "pattern": "根据 + asos",
        "all": ["根据"],
        "explanation_uz": "Qaror, maslahat yoki harakat qaysi asosga ko'ra qilinishini bildiradi.",
        "explanation_ru": "Показывает, на каком основании делается вывод, совет или действие.",
        "explanation_tj": "Нишон медиҳад, ки қарор, маслиҳат ё амал бар кадом асос аст.",
    },
    {
        "pattern": "关于 + mavzu",
        "all": ["关于"],
        "explanation_uz": "Gap, savol yoki ma'lumot qaysi mavzu haqida ekanini bildiradi.",
        "explanation_ru": "Показывает тему разговора, вопроса или информации.",
        "explanation_tj": "Мавзӯи суҳбат, савол ё маълумотро нишон медиҳад.",
    },
    {
        "pattern": "只有……才……",
        "all": ["只有", "才"],
        "explanation_uz": "Faqat bitta shart bajarilgandagina natija yuz berishini bildiradi.",
        "explanation_ru": "Показывает, что результат возможен только при выполнении конкретного условия.",
        "explanation_tj": "Нишон медиҳад, ки натиҷа танҳо бо иҷрои як шарт мумкин аст.",
    },
    {
        "pattern": "多么 + sifat",
        "all": ["多么"],
        "explanation_uz": "Kuchli his-hayajon bilan 'naqadar/qanchalik' ma'nosini beradi.",
        "explanation_ru": "Передает эмоциональное 'как/насколько' перед признаком.",
        "explanation_tj": "Бо эҳсос маънои 'чӣ қадар/то чӣ андоза'-ро медиҳад.",
    },
    {
        "pattern": "A 得 + natija/daraja",
        "all": ["得"],
        "not_any": ["觉得", "记得"],
        "explanation_uz": "Harakat yoki holatning natijasi/darajasi qanday bo'lganini ko'rsatadi.",
        "explanation_ru": "Показывает результат или степень действия/состояния.",
        "explanation_tj": "Натиҷа ё дараҷаи амал/ҳолатро нишон медиҳад.",
    },
    {
        "pattern": "V 出来 / 起来 / 下来",
        "any": ["出来", "起来", "下来", "下去"],
        "explanation_uz": "Yo'nalish to'ldiruvchisi ko'chma ma'noda natija yoki o'zgarish sezilganini bildiradi.",
        "explanation_ru": "Направительный комплемент в переносном значении показывает результат или изменение.",
        "explanation_tj": "Пуркунандаи самтӣ дар маънои маҷозӣ натиҷа ё тағйирро нишон медиҳад.",
    },
    {
        "pattern": "V 好 / 完 / 到",
        "any": ["好了", "完了", "到了", "找到", "看好"],
        "explanation_uz": "Natija to'ldiruvchisi harakat yakunlanganini yoki maqsadga yetganini bildiradi.",
        "explanation_ru": "Результативный комплемент показывает завершение действия или достижение результата.",
        "explanation_tj": "Пуркунандаи натиҷа анҷоми амал ё расидан ба натиҷаро нишон медиҳад.",
    },
    {
        "pattern": "V 着 + holat",
        "all": ["着"],
        "not_any": ["着急"],
        "explanation_uz": "Harakatdan keyingi davom etayotgan holatni bildiradi.",
        "explanation_ru": "Показывает продолжающееся состояние после действия.",
        "explanation_tj": "Ҳолати давомдор баъди амалро нишон медиҳад.",
    },
    {
        "pattern": "越……越……",
        "all": ["越"],
        "explanation_uz": "Bir narsa o'zgargani sari ikkinchisi ham o'zgarishini bildiradi.",
        "explanation_ru": "Показывает, что с изменением одного признака меняется другой.",
        "explanation_tj": "Нишон медиҳад, ки бо тағйири як чиз чизи дигар ҳам тағйир меёбад.",
    },
    {
        "pattern": "越来越 + sifat",
        "all": ["越来越"],
        "explanation_uz": "Holat asta-sekin kuchayib borayotganini bildiradi.",
        "explanation_ru": "Показывает постепенное усиление признака.",
        "explanation_tj": "Қавитар шудани тадриҷии ҳолатро нишон медиҳад.",
    },
    {
        "pattern": "又A又B",
        "all": ["又"],
        "explanation_uz": "Bir odam yoki narsada ikki sifat birga borligini bildiradi.",
        "explanation_ru": "Показывает, что у одного предмета или человека есть два признака одновременно.",
        "explanation_tj": "Нишон медиҳад, ки дар як чиз ё одам ду сифат ҳамзамон ҳаст.",
    },
    {
        "pattern": "一……也/都 + 不/没",
        "any": ["一点儿也", "一点也", "一个也", "一件也", "一分也"],
        "explanation_uz": "Mutlaq inkor: 'umuman', 'bittayam', 'zarrachayam' ma'nosini kuchaytiradi.",
        "explanation_ru": "Полное отрицание: усиливает значение 'совсем', 'ни одного'.",
        "explanation_tj": "Инкори мутлақ: маънои 'тамоман', 'ягон ҳам'-ро қавӣ мекунад.",
    },
    {
        "pattern": "不A也不B",
        "any": ["也不"],
        "explanation_uz": "Ikki holatning ikkalasi ham yo'qligini bildiradi.",
        "explanation_ru": "Показывает отсутствие двух признаков одновременно.",
        "explanation_tj": "Набудани ду ҳолатро ҳамзамон нишон медиҳад.",
    },
    {
        "pattern": "还是 + tanlov savoli",
        "all": ["还是", "？"],
        "explanation_uz": "Savolda ikki variantdan birini tanlashni bildiradi.",
        "explanation_ru": "В вопросе показывает выбор между двумя вариантами.",
        "explanation_tj": "Дар савол интихоби байни ду вариантро нишон медиҳад.",
    },
    {
        "pattern": "或者 + tanlov",
        "all": ["或者"],
        "explanation_uz": "Darak gapda ikki imkoniyatdan birini bildiradi.",
        "explanation_ru": "В утверждении показывает один из двух возможных вариантов.",
        "explanation_tj": "Дар ҷумлаи хабарӣ яке аз ду имкониятро нишон медиҳад.",
    },
    {
        "pattern": "V 一 V / VV",
        "any": ["看一看", "等一等", "坐一下", "休息休息", "检查检查", "锻炼锻炼", "认识认识", "找找", "做做", "笑笑", "说说"],
        "explanation_uz": "Harakatni yumshoq, qisqa yoki sinab ko'rish ma'nosida aytadi.",
        "explanation_ru": "Смягчает действие: 'немного сделать', 'попробовать сделать'.",
        "explanation_tj": "Амалро мулоим мекунад: 'каме кардан', 'санҷида дидан'.",
    },
    {
        "pattern": "了",
        "all": ["了"],
        "explanation_uz": "Harakat tugagani yoki vaziyat o'zgarganini bildiradi.",
        "explanation_ru": "Показывает завершение действия или изменение ситуации.",
        "explanation_tj": "Анҷоми амал ё тағйири вазъро нишон медиҳад.",
    },
    {
        "pattern": "吗 / 呢 / 吧",
        "any": ["吗", "呢", "吧"],
        "explanation_uz": "Gap oxiridagi yuklama savol, yumshatish yoki taklif ohangini beradi.",
        "explanation_ru": "Финальная частица задает вопрос, смягчает тон или делает предложение.",
        "explanation_tj": "Ҳиссачаи охири ҷумла савол, мулоимӣ ё пешниҳодро медиҳад.",
    },
]


def _dialogue_lines(block: dict) -> list[dict]:
    lines = block.get("dialogue") or []
    return [line for line in lines if isinstance(line, dict)]


def _rule_matches(rule: dict, text: str) -> bool:
    excluded = rule.get("not_any") or []
    if excluded and any(item in text for item in excluded):
        return False
    required = rule.get("all") or []
    optional = rule.get("any") or []
    if required and not all(item in text for item in required):
        return False
    if optional and not any(item in text for item in optional):
        return False
    return bool(required or optional)


def _line_matches(rule: dict, line: dict) -> bool:
    return _rule_matches(rule, line.get("zh") or "")


def _context_grammar_note(block: dict, used_patterns: set[str]) -> dict | None:
    lines = _dialogue_lines(block)
    matches = [
        rule
        for rule in CONTEXT_GRAMMAR_RULES
        if any(_line_matches(rule, line) for line in lines)
    ]
    for rule in [item for item in matches if item["pattern"] not in used_patterns] or matches:
        example = next((line for line in lines if _line_matches(rule, line)), None) or (lines[0] if lines else {})
        return {
            "pattern": rule["pattern"],
            "explanation_uz": rule["explanation_uz"],
            "explanation_ru": rule["explanation_ru"],
            "explanation_tj": rule["explanation_tj"],
            "example_zh": example.get("zh") or "",
            "example_pinyin": example.get("pinyin") or "",
            "example_uz": example.get("uz") or "",
            "example_ru": example.get("ru") or "",
            "example_tj": example.get("tj") or "",
        }
    if not lines:
        return None
    example = lines[0]
    return {
        "pattern": "Dialogdagi tayyor gap qolipi",
        "explanation_uz": "Bu qismda eng foydali gapni tayyor qolip sifatida o'rganing va yangi so'zlarni shu qolipga almashtirib mashq qiling.",
        "explanation_ru": "В этой части выучите полезную фразу как готовую модель и тренируйте ее, заменяя новые слова.",
        "explanation_tj": "Дар ин қисм ҷумлаи фоиданокро ҳамчун қолаби тайёр омӯзед ва калимаҳои навро дар он иваз карда машқ кунед.",
        "example_zh": example.get("zh") or "",
        "example_pinyin": example.get("pinyin") or "",
        "example_uz": example.get("uz") or "",
        "example_ru": example.get("ru") or "",
        "example_tj": example.get("tj") or "",
    }


def normalize_block_grammar(dialogues: list[dict]) -> None:
    seen_nos = set()
    used_patterns = set()
    for block in dialogues:
        if not isinstance(block, dict):
            continue

        grammar_nos = block.get("grammar_nos") or []
        kept = []
        if isinstance(grammar_nos, list):
            for no in grammar_nos:
                try:
                    value = int(no)
                except (TypeError, ValueError):
                    continue
                if value in seen_nos:
                    continue
                seen_nos.add(value)
                kept.append(value)
        block["grammar_nos"] = kept

        notes = block.get("grammar_notes") or []
        if not isinstance(notes, list):
            notes = []
        if notes:
            block["grammar_notes"] = notes[:2]
            for note in block["grammar_notes"]:
                if isinstance(note, dict) and note.get("pattern"):
                    used_patterns.add(note["pattern"])
            continue

        note = _context_grammar_note(block, used_patterns)
        if note:
            block["grammar_notes"] = [note]
            used_patterns.add(note["pattern"])
        else:
            block["grammar_notes"] = []
