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
        "not_any": ["拿把", "一把", "两把", "三把", "这把", "那把", "几把"],
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
        "not_any": ["觉得", "记得", "看得到", "看不到", "听得到", "听不到", "买得到", "买不到", "找得到", "找不到"],
        "explanation_uz": "Harakat yoki holatning natijasi/darajasi qanday bo'lganini ko'rsatadi.",
        "explanation_ru": "Показывает результат или степень действия/состояния.",
        "explanation_tj": "Натиҷа ё дараҷаи амал/ҳолатро нишон медиҳад.",
    },
    {
        "pattern": "V 得/不 + result",
        "any": ["看得到", "看不到", "听得到", "听不到", "买得到", "买不到", "找得到", "找不到"],
        "explanation_uz": "Harakat natijasi amalga oshishi yoki oshmasligini bildiradi: ko'ra olish/ko'ra olmaslik kabi.",
        "explanation_ru": "Показывает, возможен ли результат действия: увидеть / не увидеть и т.п.",
        "explanation_tj": "Нишон медиҳад, ки натиҷаи амал имконпазир аст ё не: дида тавонистан / дида натавонистан.",
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
        "any": ["又年轻又漂亮", "又大又甜", "又快又好", "又好又便宜", "又便宜又好", "又高又大", "又白又胖"],
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
        "any": ["不冷也不热", "不快也不慢", "不高也不矮", "不大也不小", "不贵也不便宜", "不多也不少"],
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
        "not_any": ["杨笑笑"],
        "explanation_uz": "`一下` yoki fe'lni takrorlash iltimos/taklifni yumshatadi: 'biroz o'tiraylik', 'bir ko'rib olaylik'.",
        "explanation_ru": "`一下` или повтор глагола смягчает просьбу/предложение: 'немного посидим', 'посмотрим'.",
        "explanation_tj": "`一下` ё такрори феъл хоҳиш/таклифро мулоим мекунад: 'каме нишинем', 'каме бинем'.",
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


_PATTERN_TITLES = {
    "只要……就……": {
        "uz": "只要...就... - shart bajarilsa, natija bo'ladi",
        "ru": "只要...就... - если условие выполнено, будет результат",
        "tj": "只要...就... - агар шарт иҷро шавад, натиҷа мешавад",
    },
    "不但……而且……": {
        "uz": "不但...而且... - nafaqat..., balki...",
        "ru": "不但...而且... - не только..., но и...",
        "tj": "不但...而且... - на танҳо..., балки...",
    },
    "虽然……但是……": {
        "uz": "虽然...但是... - bo'lsa ham, lekin...",
        "ru": "虽然...但是... - хотя..., но...",
        "tj": "虽然...但是... - гарчанде..., аммо...",
    },
    "如果……就……": {
        "uz": "如果...就... - agar..., unda...",
        "ru": "如果...就... - если..., то...",
        "tj": "如果...就... - агар..., пас...",
    },
    "一边……一边……": {
        "uz": "一边...一边... - ikki ish bir vaqtda",
        "ru": "一边...一边... - два действия одновременно",
        "tj": "一边...一边... - ду амал ҳамзамон",
    },
    "除了……以外，还……": {
        "uz": "除了...以外，还... - bundan tashqari yana...",
        "ru": "除了...以外，还... - кроме этого, еще...",
        "tj": "除了...以外，还... - ғайр аз ин, боз...",
    },
    "被 + kim/nima + V": {
        "uz": "被-sentence - kimdir ta'sir qilgan holat",
        "ru": "被-конструкция - пассивное действие",
        "tj": "Сохтори 被 - амали маҷҳул",
    },
    "把 + object + V": {
        "uz": "把-sentence - obyektga nima qilinganini ko'rsatish",
        "ru": "把-конструкция - что сделали с объектом",
        "tj": "Сохтори 把 - бо объект чӣ карданд",
    },
    "为了 + maqsad": {
        "uz": "为了 - maqsadni aytish",
        "ru": "为了 - указать цель",
        "tj": "为了 - нишон додани мақсад",
    },
    "根据 + asos": {
        "uz": "根据 - bir asosga ko'ra",
        "ru": "根据 - на основании чего-то",
        "tj": "根据 - дар асоси чизе",
    },
    "关于 + mavzu": {
        "uz": "关于 - mavzu haqida",
        "ru": "关于 - о теме",
        "tj": "关于 - дар бораи мавзуъ",
    },
    "只有……才……": {
        "uz": "只有...才... - faqat shu shart bilan",
        "ru": "只有...才... - только при этом условии",
        "tj": "只有...才... - танҳо бо ин шарт",
    },
    "多么 + sifat": {
        "uz": "多么 - kuchli his bilan 'naqadar'",
        "ru": "多么 - эмоциональное 'как/насколько'",
        "tj": "多么 - эҳсосӣ 'чӣ қадар'",
    },
    "A 得 + natija/daraja": {
        "uz": "得 - harakatning natijasi yoki darajasi",
        "ru": "得 - результат или степень действия",
        "tj": "得 - натиҷа ё дараҷаи амал",
    },
    "V 得/不 + result": {
        "uz": "V得/不 + natija - qila olish/qila olmaslik",
        "ru": "V得/不 + результат - возможно/невозможно сделать",
        "tj": "V得/不 + натиҷа - тавонистан/натавонистан",
    },
    "V 出来 / 起来 / 下来": {
        "uz": "出来/起来/下来 - natija yoki o'zgarish ko'rindi",
        "ru": "出来/起来/下来 - результат или изменение",
        "tj": "出来/起来/下来 - натиҷа ё тағйир",
    },
    "V 好 / 完 / 到": {
        "uz": "V好/V完/V到 - ish yakunlandi yoki natija bo'ldi",
        "ru": "V好/V完/V到 - действие завершилось с результатом",
        "tj": "V好/V完/V到 - амал бо натиҷа анҷом шуд",
    },
    "V 着 + holat": {
        "uz": "V着 - davom etayotgan holat",
        "ru": "V着 - продолжающееся состояние",
        "tj": "V着 - ҳолати давомдор",
    },
    "越……越……": {
        "uz": "越...越... - borgan sari...",
        "ru": "越...越... - чем больше..., тем...",
        "tj": "越...越... - ҳар қадар..., ҳамон қадар...",
    },
    "越来越 + sifat": {
        "uz": "越来越 - tobora kuchayib borish",
        "ru": "越来越 - становиться все более...",
        "tj": "越来越 - торафт бештар шудан",
    },
    "又A又B": {
        "uz": "又A又B - ikki sifat birga",
        "ru": "又A又B - два качества одновременно",
        "tj": "又A又B - ду сифат якҷоя",
    },
    "一……也/都 + 不/没": {
        "uz": "一...也/都不 - mutlaq inkor",
        "ru": "一...也/都不 - полное отрицание",
        "tj": "一...也/都不 - инкори пурра",
    },
    "不A也不B": {
        "uz": "不A也不B - ikkalasi ham emas",
        "ru": "不A也不B - ни то, ни другое",
        "tj": "不A也不B - на ин, на он",
    },
    "就是 + vaqt/joy + V 的": {
        "uz": "就是...的 - aynan vaqt/joyni ta'kidlash",
        "ru": "就是...的 - подчеркнуть точное время/место",
        "tj": "就是...的 - таъкиди вақти/ҷои аниқ",
    },
    "还是 + tanlov savoli": {
        "uz": "还是 - savolda tanlash",
        "ru": "还是 - выбор в вопросе",
        "tj": "还是 - интихоб дар савол",
    },
    "或者 + tanlov": {
        "uz": "或者 - variantlardan biri",
        "ru": "或者 - один из вариантов",
        "tj": "或者 - яке аз вариантҳо",
    },
    "V 一 V / VV": {
        "uz": "V一下 / V一V - ishni biroz/yumshoq qilish",
        "ru": "V一下 / V一V - сделать немного, мягко попросить",
        "tj": "V一下 / V一V - амалро каме ва мулоим кардан",
    },
    "了": {
        "uz": "了 - ish tugadi yoki vaziyat o'zgardi",
        "ru": "了 - действие завершилось или ситуация изменилась",
        "tj": "了 - амал анҷом шуд ё вазъ тағйир ёфт",
    },
    "吗 / 呢 / 吧": {
        "uz": "吗/呢/吧 - savol yoki yumshoq ohang",
        "ru": "吗/呢/吧 - вопрос или мягкий тон",
        "tj": "吗/呢/吧 - савол ё оҳанги мулоим",
    },
}


def _localized_pattern(pattern: str, lang: str) -> str:
    return (_PATTERN_TITLES.get(pattern) or {}).get(lang) or pattern


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
            "pattern_uz": _localized_pattern(rule["pattern"], "uz"),
            "pattern_ru": _localized_pattern(rule["pattern"], "ru"),
            "pattern_tj": _localized_pattern(rule["pattern"], "tj"),
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
        "pattern_uz": "Dialogdagi tayyor gap qolipi",
        "pattern_ru": "Готовая фразовая модель из диалога",
        "pattern_tj": "Қолаби тайёри ҷумла аз муколама",
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
            normalized_notes = []
            for note in notes[:2]:
                if not isinstance(note, dict):
                    continue
                pattern = note.get("pattern") or ""
                if pattern:
                    note.setdefault("pattern_uz", _localized_pattern(pattern, "uz"))
                    note.setdefault("pattern_ru", _localized_pattern(pattern, "ru"))
                    note.setdefault("pattern_tj", _localized_pattern(pattern, "tj"))
                    used_patterns.add(pattern)
                normalized_notes.append(note)
            block["grammar_notes"] = normalized_notes
            continue

        note = _context_grammar_note(block, used_patterns)
        if note:
            block["grammar_notes"] = [note]
            used_patterns.add(note["pattern"])
        else:
            block["grammar_notes"] = []
