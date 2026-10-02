from __future__ import annotations

import json

SOURCE = {
    "book": "新HSK教程2",
    "pdf_path": "HSK 3.0 PDF/新HSK2 教材.pdf",
    "lfs_oid_sha256": "12a7ca82d9ede40e7bcdad36b4198e20db311d378d407b1f80dcc9b26b48f003",
    "pdf_pages": list(range(45, 53)),
    "printed_pages": list(range(29, 37)),
    "rights_note": "Dialogue reuse permitted by project owner.",
    "extraction_status": "verified_from_rendered_pages",
}

LESSON = {
    "level": "nhsk2",
    "lesson_order": 4,
    "lesson_code": "NHSK2-L04",
    "title": "你穿红色的很好看",
    "title_pinyin": "Nǐ chuān hóngsè de hěn hǎokàn",
    "goal": json.dumps({
        "uz": "“过” bilan o‘tgan tajribani aytish; 因为……所以…… bilan sabab-natijani ifodalash; “的” iborasidan foydalanish; kiyim va rang tanlash haqida gaplashish.",
        "ru": "Говорить о прошлом опыте с “过”; выражать причину и следствие с 因为……所以……; использовать конструкцию с “的”; обсуждать одежду и выбор цвета.",
        "tj": "Бо “过” таҷрибаи гузаштаеро баён кардан; бо 因为……所以…… сабабу натиҷаро ифода кардан; ибораи “的”-ро истифода бурдан; дар бораи либос ва интихоби ранг суҳбат кардан.",
    }, ensure_ascii=False),
    "intro_text": json.dumps({
        "uz": "Dars savdo markazida kiyim va sumka tanlash hamda kundalik yozuvi orqali tajriba, sabab-natija va “的” iborasini o‘rgatadi.",
        "ru": "Урок через выбор одежды и рюкзака в торговом центре и запись в дневнике вводит опыт с 过, причинно-следственную связь и фразу с 的.",
        "tj": "Дарс тавассути интихоби либос ва ҷузвдон дар маркази савдо ва навиштаи рӯзнома таҷриба бо 过, сабабу натиҷа ва ибораи 的-ро меомӯзонад.",
    }, ensure_ascii=False),
    "vocabulary_json": json.dumps([
        {"no":1,"zh":"过","pinyin":"guo","pos":"part.","uz":"o‘tgan tajribani bildiruvchi yuklama","ru":"частица прошедшего опыта","tj":"ҳиссачаи таҷрибаи гузашта"},
        {"no":2,"zh":"商场","pinyin":"shāngchǎng","pos":"n.","uz":"savdo markazi","ru":"торговый центр","tj":"маркази савдо"},
        {"no":3,"zh":"进去","pinyin":"jìnqu","pos":"v.","uz":"ichkariga kirmoq","ru":"зайти внутрь","tj":"ба дарун даромадан"},
        {"no":4,"zh":"条","pinyin":"tiáo","pos":"m.","uz":"uzun/ingichka narsalar uchun hisob so‘zi","ru":"счётное слово для длинных/узких предметов","tj":"воҳиди ҳисоб барои чизҳои дароз/борик"},
        {"no":5,"zh":"裤子","pinyin":"kùzi","pos":"n.","uz":"shim","ru":"брюки","tj":"шим"},
        {"no":6,"zh":"白色","pinyin":"báisè","pos":"n.","uz":"oq rang","ru":"белый цвет","tj":"ранги сафед"},
        {"no":7,"zh":"因为","pinyin":"yīnwèi","pos":"conj.","uz":"chunki; sababli","ru":"потому что","tj":"зеро; барои он ки"},
        {"no":8,"zh":"试","pinyin":"shì","pos":"v.","uz":"sinab ko‘rmoq","ru":"пробовать; примерять","tj":"санҷидан; пӯшида дидан"},
        {"no":9,"zh":"红色","pinyin":"hóngsè","pos":"n.","uz":"qizil rang","ru":"красный цвет","tj":"ранги сурх"},
        {"no":10,"zh":"所以","pinyin":"suǒyǐ","pos":"conj.","uz":"shuning uchun","ru":"поэтому","tj":"бинобар ин"},
        {"no":11,"zh":"书包","pinyin":"shūbāo","pos":"n.","uz":"maktab sumkasi; ryukzak","ru":"школьная сумка; рюкзак","tj":"ҷузвдони мактабӣ"},
        {"no":12,"zh":"过去","pinyin":"guòqu","pos":"v.","uz":"u tomonga o‘tmoq/bormoq","ru":"подойти; перейти туда","tj":"ба он тараф гузаштан/рафтан"},
        {"no":13,"zh":"绿色","pinyin":"lǜsè","pos":"n.","uz":"yashil rang","ru":"зелёный цвет","tj":"ранги сабз"},
        {"no":14,"zh":"黑色","pinyin":"hēisè","pos":"n.","uz":"qora rang","ru":"чёрный цвет","tj":"ранги сиёҳ"},
        {"no":15,"zh":"更","pinyin":"gèng","pos":"adv.","uz":"yanada; ko‘proq","ru":"ещё более","tj":"боз ҳам; бештар"},
        {"no":16,"zh":"颜色","pinyin":"yánsè","pos":"n.","uz":"rang","ru":"цвет","tj":"ранг"},
    ], ensure_ascii=False),
    "proper_nouns_json": json.dumps([], ensure_ascii=False),
    "dialogue_json": json.dumps([
        {"block_no":1,"section_label":"课文 1","scene_zh":"在商场门口，王一雪和刘小雪在聊天儿。","scene_uz":"Savdo markazi oldida Wang Yixue va Liu Xiaoxue suhbatlashmoqda.","scene_ru":"У входа в торговый центр Ван Исюэ и Лю Сяосюэ разговаривают.","scene_tj":"Дар назди маркази савдо Ван Исюэ ва Лю Сяосюэ суҳбат мекунанд.","dialogue":[
            {"speaker":"Liu Xiaoxue","zh":"妈妈，我们来过这家商场吗？","pinyin":"Māma, wǒmen láiguo zhè jiā shāngchǎng ma?","uz":"Oyi, biz bu savdo markaziga oldin kelganmizmi?","ru":"Мама, мы уже бывали в этом торговом центре?","tj":"Оча, мо пештар ба ин маркази савдо омада будем?"},
            {"speaker":"Wang Yixue","zh":"没来过，这是新开的。","pinyin":"Méi láiguo, zhè shì xīn kāi de.","uz":"Yo‘q, kelmaganmiz, bu yangi ochilgan.","ru":"Нет, не бывали, он недавно открылся.","tj":"Не, наомада будем, ин нав кушода шудааст."},
            {"speaker":"Liu Xiaoxue","zh":"我们进去看看吧。","pinyin":"Wǒmen jìnqu kànkan ba.","uz":"Ichkariga kirib ko‘raylik.","ru":"Давай зайдём и посмотрим.","tj":"Биё даромада тамошо кунем."},
            {"speaker":"Wang Yixue","zh":"好啊！你想买点儿什么？","pinyin":"Hǎo a! Nǐ xiǎng mǎi diǎnr shénme?","uz":"Mayli! Nima sotib olmoqchisan?","ru":"Хорошо! Что ты хочешь купить?","tj":"Хуб! Чӣ харидан мехоҳӣ?"},
            {"speaker":"Liu Xiaoxue","zh":"我想买条裤子。","pinyin":"Wǒ xiǎng mǎi tiáo kùzi.","uz":"Bir shim sotib olmoqchiman.","ru":"Я хочу купить брюки.","tj":"Мехоҳам як шим харам."},
            {"speaker":"Wang Yixue","zh":"没问题。","pinyin":"Méi wèntí.","uz":"Muammo yo‘q.","ru":"Без проблем.","tj":"Мушкил нест."},
        ]},
        {"block_no":2,"section_label":"课文 2","scene_zh":"在商场，王一雪和刘小雪在看衣服。","scene_uz":"Savdo markazida Wang Yixue va Liu Xiaoxue kiyim ko‘rmoqda.","scene_ru":"В торговом центре Ван Исюэ и Лю Сяосюэ выбирают одежду.","scene_tj":"Дар маркази савдо Ван Исюэ ва Лю Сяосюэ либос мебинанд.","dialogue":[
            {"speaker":"Liu Xiaoxue","zh":"妈妈，我想买这条白色的裤子。","pinyin":"Māma, wǒ xiǎng mǎi zhè tiáo báisè de kùzi.","uz":"Oyi, men mana bu oq shimni olmoqchiman.","ru":"Мама, я хочу купить эти белые брюки.","tj":"Оча, мехоҳам ҳамин шими сафедро харам."},
            {"speaker":"Wang Yixue","zh":"你有很多白色的衣服，为什么还买白色的？","pinyin":"Nǐ yǒu hěn duō báisè de yīfu, wèishénme hái mǎi báisè de?","uz":"Senda oq kiyimlar ko‘p-ku, nega yana oqini olmoqchisan?","ru":"У тебя много белой одежды, зачем снова покупать белое?","tj":"Ту либоси сафед бисёр дорӣ, чаро боз сафед мехарӣ?"},
            {"speaker":"Liu Xiaoxue","zh":"因为我喜欢白色啊！","pinyin":"Yīnwèi wǒ xǐhuan báisè a!","uz":"Chunki men oq rangni yoqtiraman!","ru":"Потому что мне нравится белый!","tj":"Зеро ман ранги сафедро дӯст медорам!"},
            {"speaker":"Wang Yixue","zh":"我觉得这条白色的不太好看，你试试那条红色的吧。","pinyin":"Wǒ juéde zhè tiáo báisè de bú tài hǎokàn, nǐ shìshi nà tiáo hóngsè de ba.","uz":"Menimcha, bu oq shim unchalik chiroyli emas, ana u qizilini sinab ko‘r.","ru":"По-моему, эти белые брюки не очень, примерь те красные.","tj":"Ба назарам, ин шими сафед он қадар зебо нест, он сурхро пӯшида бин."},
            {"speaker":"Liu Xiaoxue","zh":"我没穿过红色的，红色的好看吗？","pinyin":"Wǒ méi chuānguo hóngsè de, hóngsè de hǎokàn ma?","uz":"Men qizil kiyim kiyib ko‘rmaganman, qizili chiroylimi?","ru":"Я никогда не носила красное. Красное красиво?","tj":"Ман то ҳол сурх напӯшидаам, сурх зебо аст?"},
            {"speaker":"Wang Yixue","zh":"就是因为没穿过，所以要试试啊！","pinyin":"Jiù shì yīnwèi méi chuānguo, suǒyǐ yào shìshi a!","uz":"Aynan kiymaganing uchun sinab ko‘rishing kerak!","ru":"Вот именно потому, что не носила, и нужно попробовать!","tj":"Маҳз барои он ки напӯшидаӣ, бояд санҷида бинӣ!"},
        ]},
        {"block_no":3,"section_label":"课文 3","scene_zh":"在商场，王一雪和刘小雪在看书包。","scene_uz":"Savdo markazida Wang Yixue va Liu Xiaoxue sumkalarni ko‘rmoqda.","scene_ru":"В торговом центре Ван Исюэ и Лю Сяосюэ выбирают рюкзаки.","scene_tj":"Дар маркази савдо Ван Исюэ ва Лю Сяосюэ ҷузвдон мебинанд.","dialogue":[
            {"speaker":"Liu Xiaoxue","zh":"妈妈，我想买个新书包。","pinyin":"Māma, wǒ xiǎng mǎi ge xīn shūbāo.","uz":"Oyi, yangi sumka olmoqchiman.","ru":"Мама, я хочу купить новый рюкзак.","tj":"Оча, мехоҳам ҷузвдони нав харам."},
            {"speaker":"Wang Yixue","zh":"好，那边卖书包，我们过去看看吧。","pinyin":"Hǎo, nàbian mài shūbāo, wǒmen guòqu kànkan ba.","uz":"Xo‘p, u tomonda sumka sotishar ekan, borib ko‘raylik.","ru":"Хорошо, там продают рюкзаки, давай подойдём посмотрим.","tj":"Хуб, он тараф ҷузвдон мефурӯшанд, биё рафта бинем."},
            {"speaker":"Liu Xiaoxue","zh":"这么多漂亮的书包！","pinyin":"Zhème duō piàoliang de shūbāo!","uz":"Shuncha ko‘p chiroyli sumka!","ru":"Как много красивых рюкзаков!","tj":"Ин қадар ҷузвдони зебо!"},
            {"speaker":"Wang Yixue","zh":"红色的、绿色的、黑色的，你想买哪个？","pinyin":"Hóngsè de, lǜsè de, hēisè de, nǐ xiǎng mǎi nǎge?","uz":"Qizili, yashili, qorasi — qaysinisini olmoqchisan?","ru":"Красный, зелёный, чёрный — какой хочешь купить?","tj":"Сурх, сабз, сиёҳ — кадомашро мехоҳӣ?"},
            {"speaker":"Liu Xiaoxue","zh":"绿色的吧。","pinyin":"Lǜsè de ba.","uz":"Yashilini.","ru":"Наверное, зелёный.","tj":"Сабзашро."},
            {"speaker":"Wang Yixue","zh":"不错，我也觉得绿色的更好看。","pinyin":"Búcuò, wǒ yě juéde lǜsè de gèng hǎokàn.","uz":"Yomon emas, men ham yashili yanada chiroyli deb o‘ylayman.","ru":"Неплохо, мне тоже кажется, что зелёный красивее.","tj":"Бад нест, ба назари ман ҳам сабзаш зеботар аст."},
        ]},
        {"block_no":4,"section_label":"课文 4","scene_zh":"在房间，刘小雪在写日记。","scene_uz":"Xonada Liu Xiaoxue kundalik yozmoqda.","scene_ru":"В комнате Лю Сяосюэ пишет дневник.","scene_tj":"Дар ҳуҷра Лю Сяосюэ рӯзнома менависад.","dialogue":[
            {"speaker":"Narration","zh":"我和妈妈去了一家商场。因为是新开的，所以这几天东西很便宜。商场里的衣服颜色很多。我没穿过红色的裤子，妈妈让我试了试，我觉得我穿红色的也很好看。","pinyin":"Wǒ hé māma qùle yì jiā shāngchǎng. Yīnwèi shì xīn kāi de, suǒyǐ zhè jǐ tiān dōngxi hěn piányi. Shāngchǎng lǐ de yīfu yánsè hěn duō. Wǒ méi chuānguo hóngsè de kùzi, māma ràng wǒ shìle shì, wǒ juéde wǒ chuān hóngsè de yě hěn hǎokàn.","uz":"Men onam bilan bir savdo markaziga bordim. U yangi ochilgani uchun shu kunlarda narsalar juda arzon. Savdo markazidagi kiyimlarning ranglari ko‘p. Men ilgari qizil shim kiymagan edim, onam sinab ko‘rishimni aytdi; men qizil kiyim menga ham juda yarashadi deb o‘yladim.","ru":"Мы с мамой сходили в торговый центр. Поскольку он недавно открылся, в эти дни товары там дешёвые. Одежда представлена во многих цветах. Я раньше не носила красные брюки; мама предложила примерить, и мне показалось, что красное мне тоже очень идёт.","tj":"Ман бо модарам ба як маркази савдо рафтам. Азбаски он нав кушода шудааст, ин рӯзҳо чизҳо хеле арзонанд. Либосҳо рангҳои бисёр доранд. Ман пештар шими сурх напӯшида будам; модарам гуфт санҷида бинам ва ба назарам сурх ба ман ҳам хеле зебо меояд."},
        ]},
    ], ensure_ascii=False),
    "grammar_json": json.dumps([
        {"no":1,"title_zh":"动态助词“过”","title_uz":"Aspekt yuklamasi “过”","title_ru":"Аспектная частица “过”","title_tj":"Ҳиссачаи аспектии “过”","rule_zh":"动态助词“过”用在动词后面，表示动作曾在过去发生，但未持续到现在。基本结构：主语+动词+过+宾语。否定形式是在动词前面加“没（有）”。","rule_uz":"“过” fe’ldan keyin kelib, harakat o‘tmishda sodir bo‘lganini, lekin hozirgacha davom etmaganini bildiradi. Tuzilishi: ega+fe’l+过+obyekt. Inkor fe’l oldidan 没（有） bilan qilinadi.","rule_ru":"“过” ставится после глагола и показывает, что действие происходило в прошлом, но не продолжается сейчас. Схема: подлежащее+глагол+过+объект; отрицание — 没（有） перед глаголом.","rule_tj":"“过” баъди феъл омада, амале дар гузашта рух дода, то ҳозир идома наёфтанашро нишон медиҳад. Сохтор: мубтадо+феъл+过+объект; инкор бо 没（有） пеш аз феъл.","examples":[{"zh":"她去过中国。"},{"zh":"我吃过饺子，很好吃。"},{"zh":"她没去过中国。"},{"zh":"我们来过这家商场吗？"},{"zh":"陈天中吃过饺子没有？"},{"zh":"你看没看过那个电影？"}]},
        {"no":2,"title_zh":"因果复句“因为……，所以……”","title_uz":"Sabab-natija gapi “因为……，所以……”","title_ru":"Причинно-следственное предложение “因为……，所以……”","title_tj":"Ҷумлаи сабабу натиҷа “因为……，所以……”","rule_zh":"“因为……所以……”构成因果关系复句。“因为”和“所以”可以成对使用，也可以只用其中的一个。","rule_uz":"“因为……所以……” sabab-natija munosabatini bildiradi. 因为 va 所以 juft ishlatilishi ham, bittasi alohida ishlatilishi ham mumkin.","rule_ru":"“因为……所以……” образует причинно-следственное сложное предложение. 因为 и 所以 могут употребляться вместе или по отдельности.","rule_tj":"“因为……所以……” ҷумлаи сабабу натиҷаро месозад. 因为 ва 所以 метавонанд якҷо ё яке аз онҳо алоҳида истифода шаванд.","examples":[{"zh":"就是因为没穿过，所以要试试啊！"},{"zh":"因为我生病了，今天没去上班。"},{"zh":"我没去过他家，所以让他来车站接我。"}]},
        {"no":3,"title_zh":"“的”字短语","title_uz":"“的” iborasi","title_ru":"Фраза с “的”","title_tj":"Ибораи “的”","rule_zh":"结构助词“的”用在名词、代词、动词、形容词等后面，组成“的”字短语，相当于名词性短语。","rule_uz":"“的” ot, olmosh, fe’l yoki sifatdan keyin kelib, ot vazifasidagi “的” iborasini hosil qiladi.","rule_ru":"Структурная частица “的” после существительного, местоимения, глагола, прилагательного и т. п. образует именную фразу.","rule_tj":"Ҳиссачаи “的” баъди исм, ҷонишин, феъл, сифат ва ғайра омада, ибораи исмӣ месозад.","examples":[{"zh":"红色的、绿色的、黑色的，你想买哪个？"},{"zh":"这个面包是爸爸买的，妈妈买的在那儿。"},{"zh":"这件衣服太贵了，还是买那件便宜的吧。"}]},
    ], ensure_ascii=False),
}
