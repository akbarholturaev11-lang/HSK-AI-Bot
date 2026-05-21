import json


_LESSON_1_VOCABULARY = [
    {"no": 1, "zh": "周末", "pinyin": "zhōumò", "pos": "n.", "uz": "hafta oxiri, dam olish kuni", "ru": "выходные, конец недели", "tj": "охири ҳафта, рӯзи истироҳат"},
    {"no": 2, "zh": "打算", "pinyin": "dǎsuàn", "pos": "n./v.", "uz": "reja; rejalamoq, niyat qilmoq", "ru": "план; планировать, намереваться", "tj": "нақша; нақша кардан"},
    {"no": 3, "zh": "啊", "pinyin": "a", "pos": "part.", "uz": "gap oxirida tasdiq yoki himoya ohangini bildiruvchi yuklama", "ru": "частица в конце предложения для подтверждения или пояснения", "tj": "зарра дар охири ҷумла барои тасдиқ ё шарҳ"},
    {"no": 4, "zh": "跟", "pinyin": "gēn", "pos": "prep.", "uz": "bilan", "ru": "с, вместе с", "tj": "бо"},
    {"no": 5, "zh": "一直", "pinyin": "yìzhí", "pos": "adv.", "uz": "doimo, tinmay, davomli", "ru": "всё время, постоянно", "tj": "ҳамеша, пайваста"},
    {"no": 6, "zh": "游戏", "pinyin": "yóuxì", "pos": "n.", "uz": "o'yin", "ru": "игра", "tj": "бозӣ"},
    {"no": 7, "zh": "作业", "pinyin": "zuòyè", "pos": "n.", "uz": "uy vazifasi", "ru": "домашнее задание", "tj": "вазифаи хонагӣ"},
    {"no": 8, "zh": "着急", "pinyin": "zháojí", "pos": "adj.", "uz": "xavotirli, shoshilgan, tashvishlangan", "ru": "волноваться, беспокоиться", "tj": "ташвиш кашидан, нигарон шудан"},
    {"no": 9, "zh": "复习", "pinyin": "fùxí", "pos": "v.", "uz": "takrorlamoq, qayta o'qimoq", "ru": "повторять, готовиться", "tj": "такрор кардан, аз нав хондан"},
    {"no": 10, "zh": "南方", "pinyin": "nánfāng", "pos": "n.", "uz": "janub, janubiy tomon", "ru": "юг, южная сторона", "tj": "ҷануб, тарафи ҷанубӣ"},
    {"no": 11, "zh": "北方", "pinyin": "běifāng", "pos": "n.", "uz": "shimol, shimoliy tomon", "ru": "север, северная сторона", "tj": "шимол, тарафи шимолӣ"},
    {"no": 12, "zh": "面包", "pinyin": "miànbāo", "pos": "n.", "uz": "non, bulka", "ru": "хлеб, булка", "tj": "нон, булка"},
    {"no": 13, "zh": "带", "pinyin": "dài", "pos": "v.", "uz": "olib ketmoq, olib yurmoq", "ru": "брать с собой, нести", "tj": "бо худ гирифтан, бурдан"},
    {"no": 14, "zh": "地图", "pinyin": "dìtú", "pos": "n.", "uz": "xarita", "ru": "карта", "tj": "харита"},
    {"no": 15, "zh": "搬", "pinyin": "bān", "pos": "v.", "uz": "ko'chirmoq, tashimoq", "ru": "переносить, перевозить", "tj": "кӯчондан, кашондан"},
    {"no": 16, "zh": "小丽", "pinyin": "Xiǎolì", "pos": "proper noun", "uz": "Xiaoli (ism)", "ru": "Сяоли (имя)", "tj": "Сяоли (ном)"},
    {"no": 17, "zh": "小刚", "pinyin": "Xiǎogāng", "pos": "proper noun", "uz": "Xiaogang (ism)", "ru": "Сяоган (имя)", "tj": "Сяоган (ном)"},
]


_LESSON_1_DIALOGUES = [
    {
        "block_no": 1,
        "section_label": "课文 1",
        "scene_uz": "Dam olish kuni rejalari haqida",
        "scene_ru": "О планах на выходные",
        "scene_tj": "Дар бораи нақшаҳои охири ҳафта",
        "word_nos": [1, 2, 3, 4, 16, 17],
        "grammar_nos": [1],
        "dialogue": [
            {"speaker": "小丽", "zh": "周末你有什么打算？", "pinyin": "Zhōumò nǐ yǒu shénme dǎsuàn?", "uz": "Hafta oxiri nima rejang bor?", "ru": "Какие у тебя планы на выходные?", "tj": "Охири ҳафта чӣ нақша дорӣ?"},
            {"speaker": "小刚", "zh": "我早就想好了，请你吃饭、看电影、喝咖啡。", "pinyin": "Wǒ zǎo jiù xiǎng hǎo le, qǐng nǐ chī fàn, kàn diànyǐng, hē kāfēi.", "uz": "Men allaqachon o'ylab qo'yganman: seni ovqatga, kinoga va qahvaga taklif qilaman.", "ru": "Я уже давно всё придумал: приглашу тебя поесть, посмотреть фильм и выпить кофе.", "tj": "Ман кайҳо фикр кардаам: туро ба хӯрок, кино ва қаҳва даъват мекунам."},
            {"speaker": "小丽", "zh": "请我？", "pinyin": "Qǐng wǒ?", "uz": "Meni taklif qilasanmi?", "ru": "Меня приглашаешь?", "tj": "Маро даъват мекунӣ?"},
            {"speaker": "小刚", "zh": "是啊，我已经找好饭馆了，电影票也买好了。", "pinyin": "Shì a, wǒ yǐjīng zhǎo hǎo fànguǎnr le, diànyǐngpiào yě mǎi hǎo le.", "uz": "Ha, restoran ham topib qo'ydim, kino chiptasini ham olib qo'ydim.", "ru": "Да, я уже нашёл ресторан и купил билеты в кино.", "tj": "Ҳа, тарабхонаро ёфтаам ва билетҳои киноро ҳам харидаам."},
            {"speaker": "小丽", "zh": "我还没想好要不要跟你去呢。", "pinyin": "Wǒ hái méi xiǎng hǎo yào bu yào gēn nǐ qù ne.", "uz": "Men hali sen bilan borish-bormaslikni o'ylab bo'lmadim.", "ru": "Я ещё не решила, идти с тобой или нет.", "tj": "Ман ҳанӯз фикр накардаам, ки бо ту равам ё не."},
        ],
    },
    {
        "block_no": 2,
        "section_label": "课文 2",
        "scene_uz": "Uyda",
        "scene_ru": "Дома",
        "scene_tj": "Дар хона",
        "word_nos": [5, 6, 7, 8, 9],
        "grammar_nos": [1, 2, 3],
        "dialogue": [
            {"speaker": "妈妈", "zh": "你一直玩儿电脑游戏，作业写完了吗？", "pinyin": "Nǐ yìzhí wánr diànnǎo yóuxì, zuòyè xiě wán le ma?", "uz": "Sen tinmay kompyuter o'yini o'ynayapsan, uy vazifangni yozib tugatdingmi?", "ru": "Ты всё время играешь в компьютерные игры. Домашнее задание написал?", "tj": "Ту ҳамеша бозии компютерӣ мекунӣ, вазифаи хонагиро навишта тамом кардӣ?"},
            {"speaker": "儿子", "zh": "都写完了。", "pinyin": "Dōu xiě wán le.", "uz": "Hammasini yozib tugatdim.", "ru": "Всё написал.", "tj": "Ҳамаро навишта тамом кардам."},
            {"speaker": "妈妈", "zh": "明天不是有考试吗？你怎么一点儿也不着急？", "pinyin": "Míngtiān bú shì yǒu kǎoshì ma? Nǐ zěnme yìdiǎnr yě bù zháojí?", "uz": "Ertaga imtihon bor-ku? Nega umuman xavotir olmaysan?", "ru": "Разве завтра нет экзамена? Почему ты совсем не волнуешься?", "tj": "Магар пагоҳ имтиҳон нест? Чаро тамоман ташвиш намекашӣ?"},
            {"speaker": "儿子", "zh": "我早就复习好了。", "pinyin": "Wǒ zǎo jiù fùxí hǎo le.", "uz": "Men allaqachon takrorlab bo'lganman.", "ru": "Я давно всё повторил.", "tj": "Ман кайҳо такрор кардаам."},
            {"speaker": "妈妈", "zh": "那也不能一直玩儿啊。", "pinyin": "Nà yě bù néng yìzhí wánr a.", "uz": "Unda ham tinmay o'ynayverish mumkin emas-ku.", "ru": "Но всё равно нельзя постоянно играть.", "tj": "Пас ҳам намешавад ҳамеша бозӣ кард."},
        ],
    },
    {
        "block_no": 3,
        "section_label": "课文 3",
        "scene_uz": "Sayohat rejasi haqida",
        "scene_ru": "О плане поездки",
        "scene_tj": "Дар бораи нақшаи сафар",
        "word_nos": [10, 11],
        "grammar_nos": [],
        "dialogue": [
            {"speaker": "小丽", "zh": "下个月我去旅游，你能跟我一起去吗？", "pinyin": "Xià ge yuè wǒ qù lǚyóu, nǐ néng gēn wǒ yìqǐ qù ma?", "uz": "Keyingi oy sayohatga boraman, men bilan birga bora olasanmi?", "ru": "В следующем месяце я еду путешествовать, можешь поехать со мной?", "tj": "Моҳи дигар ба сафар меравам, метавонӣ бо ман равӣ?"},
            {"speaker": "小刚", "zh": "我还没想好呢。你觉得哪儿最好玩儿？", "pinyin": "Wǒ hái méi xiǎng hǎo ne. Nǐ juéde nǎr zuì hǎowánr?", "uz": "Hali o'ylab bo'lmadim. Seningcha qayer eng qiziqarli?", "ru": "Я ещё не решил. Как ты думаешь, где интереснее всего?", "tj": "Ҳанӯз фикр накардаам. Ба фикри ту куҷо аз ҳама ҷолиб аст?"},
            {"speaker": "小丽", "zh": "南方啊，我们去年就是这个时候去的。", "pinyin": "Nánfāng a, wǒmen qùnián jiù shì zhège shíhou qù de.", "uz": "Janub, albatta. O'tgan yili aynan shu paytda borgandik.", "ru": "На юг, конечно. В прошлом году мы ездили как раз в это время.", "tj": "Ба ҷануб, албатта. Соли гузашта маҳз ҳамин вақт рафта будем."},
            {"speaker": "小刚", "zh": "南方太热了，北方好一些，不冷也不热。", "pinyin": "Nánfāng tài rè le, běifāng hǎo yìxiē, bù lěng yě bù rè.", "uz": "Janub juda issiq. Shimol yaxshiroq, sovuq ham emas, issiq ham emas.", "ru": "На юге слишком жарко. Север лучше: ни холодно, ни жарко.", "tj": "Ҷануб хеле гарм аст. Шимол беҳтар, на сард асту на гарм."},
        ],
    },
    {
        "block_no": 4,
        "section_label": "课文 4",
        "scene_uz": "Sayohatga tayyorgarlik",
        "scene_ru": "Подготовка к поездке",
        "scene_tj": "Омодагӣ ба сафар",
        "word_nos": [12, 13, 14, 15],
        "grammar_nos": [1, 2],
        "dialogue": [
            {"speaker": "小刚", "zh": "水果、面包、茶都准备好了，我们还带什么？", "pinyin": "Shuǐguǒ, miànbāo, chá dōu zhǔnbèi hǎo le, wǒmen hái dài shénme?", "uz": "Meva, non va choy hammasi tayyor. Yana nima olib ketamiz?", "ru": "Фрукты, хлеб и чай уже готовы. Что ещё возьмём?", "tj": "Мева, нон ва чой ҳама тайёр. Боз чӣ мегирем?"},
            {"speaker": "小丽", "zh": "手机、电脑、地图，一个也不能少。", "pinyin": "Shǒujī, diànnǎo, dìtú, yí ge yě bù néng shǎo.", "uz": "Telefon, kompyuter, xarita: bittasi ham kam bo'lmasin.", "ru": "Телефон, компьютер, карта: ни одной вещи нельзя забыть.", "tj": "Телефон, компютер, харита: яктояш ҳам кам нашавад."},
            {"speaker": "小刚", "zh": "这些我昨天下午就准备好了。", "pinyin": "Zhèxiē wǒ zuótiān xiàwǔ jiù zhǔnbèi hǎo le.", "uz": "Bularni kecha tushdan keyin tayyorlab qo'ygandim.", "ru": "Это я подготовил ещё вчера после обеда.", "tj": "Инҳоро дирӯз баъд аз нисфирӯзӣ тайёр карда будам."},
            {"speaker": "小丽", "zh": "再多带几件衣服吧。", "pinyin": "Zài duō dài jǐ jiàn yīfu ba.", "uz": "Yana bir nechta kiyim ko'proq olaylik.", "ru": "Давай возьмём ещё несколько вещей.", "tj": "Биё боз чанд либоси бештар гирем."},
            {"speaker": "小刚", "zh": "我们是去旅游，不是搬家，还是少带一些吧。", "pinyin": "Wǒmen shì qù lǚyóu, bú shì bān jiā, háishi shǎo dài yìxiē ba.", "uz": "Biz sayohatga ketyapmiz, uy ko'chirmayapmiz. Baribir kamroq olganimiz yaxshi.", "ru": "Мы едем путешествовать, а не переезжаем. Лучше взять поменьше.", "tj": "Мо ба сафар меравем, на хона мекӯчонем. Беҳтараш камтар гирем."},
        ],
    },
]


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


def _mini_quiz(lesson_order: int, block_no: int, vocab: list[dict], grammar: list[dict], block: dict) -> list[dict]:
    words = [_word_by_no(vocab, no) for no in block.get("word_nos", [])]
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

    grammar_nos = block.get("grammar_nos") or []
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


def apply_hsk3_pdf_materials(lesson: dict) -> dict:
    lesson_order = int(lesson.get("lesson_order") or 0)
    if lesson_order != 1:
        return lesson

    grammar = json.loads(lesson.get("grammar_json") or "[]")
    dialogues = json.loads(json.dumps(_LESSON_1_DIALOGUES, ensure_ascii=False))
    for block in dialogues:
        block_no = int(block.get("block_no") or 0)
        words = [_word_by_no(_LESSON_1_VOCABULARY, no) for no in block.get("word_nos", [])]
        words = [word for word in words if word]
        block["mini_quiz"] = _mini_quiz(lesson_order, block_no, _LESSON_1_VOCABULARY, grammar, block)
        block["mini_homework"] = _mini_homework(block_no, words)

    lesson["vocabulary_json"] = json.dumps(_LESSON_1_VOCABULARY, ensure_ascii=False)
    lesson["dialogue_json"] = json.dumps(dialogues, ensure_ascii=False)
    return lesson
