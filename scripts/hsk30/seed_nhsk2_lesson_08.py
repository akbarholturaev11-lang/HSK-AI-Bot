from __future__ import annotations

import json

SOURCE = {
    "book": "新HSK教程2",
    "pdf_path": "HSK 3.0 PDF/新HSK2 教材.pdf",
    "lfs_oid_sha256": "12a7ca82d9ede40e7bcdad36b4198e20db311d378d407b1f80dcc9b26b48f003",
    "pdf_pages": list(range(80, 89)),
    "printed_pages": list(range(64, 73)),
    "rights_note": "Dialogue reuse permitted by project owner.",
    "extraction_status": "verified_from_rendered_pages",
}

LESSON = {
    "level":"nhsk2",
    "lesson_order":8,
    "lesson_code":"NHSK2-L08",
    "title":"虽然你忘了，但是我记得",
    "title_pinyin":"Suīrán nǐ wàng le, dànshì wǒ jìde",
    "goal":json.dumps({
        "uz":"“比” bilan taqqoslash; 比 gaplarida 很/非常 o‘rniga 更/还 bilan darajani kuchaytirish; “虽然……但是……” bilan qarama-qarshilikni ifodalash; narx, kino va tug‘ilgan kun haqida gaplashish.",
        "ru":"Сравнивать с “比”; усиливать степень в сравнении с 更/还 вместо 很/非常; выражать уступительно-противительные отношения через “虽然……但是……”；обсуждать цену, кино и день рождения.",
        "tj":"Бо “比” муқоиса кардан; дар ҷумлаҳои муқоисавӣ ба ҷойи 很/非常 бо 更/还 дараҷаро қавӣ кардан; бо “虽然……但是……” зиддиятро ифода кардан; дар бораи нарх, кино ва зодрӯз суҳбат кардан."
    },ensure_ascii=False),
    "intro_text":json.dumps({
        "uz":"Dars soat tanlash, kino tanlash, restoranda tug‘ilgan kunni nishonlash va hikoya matni orqali uchta taqqoslash/qarama-qarshilik strukturasini o‘rgatadi.",
        "ru":"Урок через выбор часов, фильма, празднование дня рождения в ресторане и рассказ вводит три конструкции сравнения и противопоставления.",
        "tj":"Дарс тавассути интихоби соат, филм, ҷашни зодрӯз дар тарабхона ва матни ҳикоя се сохтори муқоиса ва зиддиятро меомӯзонад."
    },ensure_ascii=False),
    "vocabulary_json":json.dumps([
        {"no":1,"zh":"手表","pinyin":"shǒubiǎo","pos":"n.","uz":"qo‘l soati","ru":"наручные часы","tj":"соати дастӣ"},
        {"no":2,"zh":"左边","pinyin":"zuǒbian","pos":"n.","uz":"chap tomon","ru":"левая сторона","tj":"тарафи чап"},
        {"no":"2a","zh":"左","pinyin":"zuǒ","pos":"n.","uz":"chap","ru":"лево; левый","tj":"чап"},
        {"no":3,"zh":"比","pinyin":"bǐ","pos":"prep./v.","uz":"...dan; taqqoslamoq","ru":"чем; сравнивать","tj":"нисбат ба; муқоиса кардан"},
        {"no":4,"zh":"右边","pinyin":"yòubian","pos":"n.","uz":"o‘ng tomon","ru":"правая сторона","tj":"тарафи рост"},
        {"no":"4a","zh":"右","pinyin":"yòu","pos":"n.","uz":"o‘ng","ru":"право; правый","tj":"рост"},
        {"no":5,"zh":"记得","pinyin":"jìde","pos":"v.","uz":"eslamoq","ru":"помнить","tj":"дар хотир доштан"},
        {"no":6,"zh":"爱情片","pinyin":"àiqíngpiàn","pos":"n.","uz":"romantik film","ru":"романтический фильм","tj":"филми ошиқона"},
        {"no":7,"zh":"有意思","pinyin":"yǒu yìsi","pos":"adj.","uz":"qiziqarli","ru":"интересный","tj":"ҷолиб"},
        {"no":8,"zh":"点","pinyin":"diǎn","pos":"v.","uz":"tanlamoq; buyurtma bermoq","ru":"выбирать; заказывать","tj":"интихоб кардан; фармоиш додан"},
        {"no":9,"zh":"虽然","pinyin":"suīrán","pos":"conj.","uz":"garchi; ... bo‘lsa-da","ru":"хотя","tj":"гарчанде"},
        {"no":10,"zh":"但是","pinyin":"dànshì","pos":"conj.","uz":"ammo; lekin","ru":"но; однако","tj":"аммо; лекин"},
        {"no":11,"zh":"花","pinyin":"huā","pos":"v.","uz":"sarflamoq","ru":"тратить","tj":"сарф кардан"},
        {"no":12,"zh":"妻子","pinyin":"qīzi","pos":"n.","uz":"xotin; turmush o‘rtoq","ru":"жена","tj":"ҳамсар; зан"},
        {"no":13,"zh":"丈夫","pinyin":"zhàngfu","pos":"n.","uz":"er; turmush o‘rtoq","ru":"муж","tj":"шавҳар"},
        {"no":14,"zh":"饭馆","pinyin":"fànguǎn","pos":"n.","uz":"restoran; oshxona","ru":"ресторан; закусочная","tj":"тарабхона"}
    ],ensure_ascii=False),
    "proper_nouns_json":json.dumps([],ensure_ascii=False),
    "dialogue_json":json.dumps([
        {"block_no":1,"section_label":"课文 1","scene_zh":"在商场，王一雪和刘明在购物。","scene_uz":"Savdo markazida Wang Yixue va Liu Ming xarid qilmoqda.","scene_ru":"В торговом центре Ван Исюэ и Лю Мин делают покупки.","scene_tj":"Дар маркази савдо Ван Исюэ ва Лю Мин харид мекунанд.","dialogue":[
            {"speaker":"Wang Yixue","zh":"你看，这两块手表怎么样？","pinyin":"Nǐ kàn, zhè liǎng kuài shǒubiǎo zěnmeyàng?","uz":"Qara, bu ikki qo‘l soati qanday?","ru":"Посмотри, как тебе эти двое часов?","tj":"Бин, ин ду соат чӣ хеланд?"},
            {"speaker":"Liu Ming","zh":"都不错！","pinyin":"Dōu búcuò!","uz":"Ikkalasi ham yomon emas!","ru":"Оба неплохие!","tj":"Ҳардуяш ҳам бад нест!"},
            {"speaker":"Wang Yixue","zh":"我喜欢左边这个。","pinyin":"Wǒ xǐhuan zuǒbian zhège.","uz":"Menga chapdagisi yoqdi.","ru":"Мне нравится тот, что слева.","tj":"Ба ман тарафи чап писанд аст."},
            {"speaker":"Liu Ming","zh":"我也觉得左边的比右边的好看。","pinyin":"Wǒ yě juéde zuǒbian de bǐ yòubian de hǎokàn.","uz":"Menimcha ham chapdagisi o‘ngdagidan chiroyliroq.","ru":"Мне тоже кажется, что левый красивее правого.","tj":"Ба назари ман ҳам чапаш аз росташ зеботар аст."},
            {"speaker":"Wang Yixue","zh":"你看看要多少钱！","pinyin":"Nǐ kànkan yào duōshao qián!","uz":"Narxiga qara!","ru":"Посмотри, сколько стоит!","tj":"Нархашро бин!"},
            {"speaker":"Liu Ming","zh":"真不便宜！八千八！","pinyin":"Zhēn bù piányi! Bā qiān bā!","uz":"Juda qimmat ekan! Sakkiz ming sakkiz yuz!","ru":"Совсем недёшево! Восемь тысяч восемьсот!","tj":"Хеле гарон будааст! Ҳашт ҳазору ҳаштсад!"}
        ]},
        {"block_no":2,"section_label":"课文 2","scene_zh":"在电影院外面，王一雪和刘明在聊天儿。","scene_uz":"Kinoteatr tashqarisida Wang Yixue va Liu Ming suhbatlashmoqda.","scene_ru":"Снаружи кинотеатра Ван Исюэ и Лю Мин разговаривают.","scene_tj":"Берун аз кинотеатр Ван Исюэ ва Лю Мин суҳбат мекунанд.","dialogue":[
            {"speaker":"Liu Ming","zh":"今天有不少电影，我们看个电影吧。","pinyin":"Jīntiān yǒu bù shǎo diànyǐng, wǒmen kàn ge diànyǐng ba.","uz":"Bugun ancha film bor, bir film ko‘raylik.","ru":"Сегодня много фильмов, давай посмотрим один.","tj":"Имрӯз филмҳо бисёранд, биё як филм бинем."},
            {"speaker":"Wang Yixue","zh":"好啊！我们看哪个？","pinyin":"Hǎo a! Wǒmen kàn nǎge?","uz":"Mayli! Qaysinisini ko‘ramiz?","ru":"Хорошо! Какой посмотрим?","tj":"Хуб! Кадомашро мебинем?"},
            {"speaker":"Liu Ming","zh":"我记得你喜欢看爱情片，我们看那个爱情片，怎么样？","pinyin":"Wǒ jìde nǐ xǐhuan kàn àiqíngpiàn, wǒmen kàn nàge àiqíngpiàn, zěnmeyàng?","uz":"Esimda, sen romantik filmlarni yoqtirasan. O‘sha romantik filmni ko‘rsak qanday?","ru":"Я помню, ты любишь романтические фильмы. Как насчёт того?","tj":"Дар хотир дорам, ту филмҳои ошиқонаро дӯст медорӣ. Он филмро бинем, чӣ хел?"},
            {"speaker":"Wang Yixue","zh":"还是看这个吧，我看网上说这个电影比那个爱情片更有意思。","pinyin":"Háishi kàn zhège ba, wǒ kàn wǎngshang shuō zhège diànyǐng bǐ nàge àiqíngpiàn gèng yǒu yìsi.","uz":"Yaxshisi bunisini ko‘raylik. Internetda bu film o‘sha romantik filmdan qiziqroq deyilgan.","ru":"Лучше посмотрим этот. В интернете пишут, что он интереснее того романтического.","tj":"Беҳтараш ҳаминро бинем. Дар интернет гуфтаанд, ки ин аз он филми ошиқона ҷолибтар аст."},
            {"speaker":"Liu Ming","zh":"好。我去买票。","pinyin":"Hǎo. Wǒ qù mǎi piào.","uz":"Xo‘p. Men chipta olaman.","ru":"Хорошо. Я куплю билеты.","tj":"Хуб. Ман чипта мехарам."},
            {"speaker":"Wang Yixue","zh":"到网上买吧，网上买比在这里买便宜。","pinyin":"Dào wǎngshang mǎi ba, wǎngshang mǎi bǐ zài zhèlǐ mǎi piányi.","uz":"Internetdan ol, onlayn olish bu yerdan olishdan arzonroq.","ru":"Купи онлайн, в интернете дешевле, чем здесь.","tj":"Аз интернет бихар, онлайниаш аз ин ҷо арзонтар аст."}
        ]},
        {"block_no":3,"section_label":"课文 3","scene_zh":"在饭馆，王一雪和刘明在点菜。","scene_uz":"Restoranda Wang Yixue va Liu Ming taom buyurtma qilmoqda.","scene_ru":"В ресторане Ван Исюэ и Лю Мин заказывают блюда.","scene_tj":"Дар тарабхона Ван Исюэ ва Лю Мин хӯрок фармоиш медиҳанд.","dialogue":[
            {"speaker":"Liu Ming","zh":"您好！就要这几个菜吧，谢谢！","pinyin":"Nín hǎo! Jiù yào zhè jǐ ge cài ba, xièxie!","uz":"Salom! Shu bir nechta taomni olamiz, rahmat!","ru":"Здравствуйте! Возьмём эти блюда, спасибо!","tj":"Салом! Ҳамин чанд хӯрокро мегирем, раҳмат!"},
            {"speaker":"Wang Yixue","zh":"怎么点这么多菜？","pinyin":"Zěnme diǎn zhème duō cài?","uz":"Nega buncha ko‘p taom buyurtma qilding?","ru":"Зачем заказал столько блюд?","tj":"Чаро ин қадар хӯрок фармоиш додӣ?"},
            {"speaker":"Liu Ming","zh":"你想想，今天是几月几号？","pinyin":"Nǐ xiǎngxiang, jīntiān shì jǐ yuè jǐ hào?","uz":"O‘ylab ko‘r, bugun nechanchi sana?","ru":"Подумай, какое сегодня число?","tj":"Фикр кун, имрӯз чандуми моҳ аст?"},
            {"speaker":"Wang Yixue","zh":"8月27号。啊！我的生日！","pinyin":"Bā yuè èrshíqī hào. A! Wǒ de shēngrì!","uz":"27-avgust. Voy! Tug‘ilgan kunim!","ru":"27 августа. А! Мой день рождения!","tj":"27-уми август. Оҳ! Зодрӯзи ман!"},
            {"speaker":"Liu Ming","zh":"生日快乐！虽然你忘了，但是我记得。看看这是什么？","pinyin":"Shēngrì kuàilè! Suīrán nǐ wàng le, dànshì wǒ jìde. Kànkan zhè shì shénme?","uz":"Tug‘ilgan kuning bilan! Sen unutgan bo‘lsang ham, men esladim. Qara, bu nima?","ru":"С днём рождения! Хотя ты забыла, я помнил. Посмотри, что это?","tj":"Зодрӯз муборак! Гарчанде ту фаромӯш кардӣ, ман дар хотир доштам. Бин, ин чист?"},
            {"speaker":"Wang Yixue","zh":"手表！吃饭、看电影、买手表，今天花了不少钱吧？","pinyin":"Shǒubiǎo! Chī fàn, kàn diànyǐng, mǎi shǒubiǎo, jīntiān huāle bù shǎo qián ba?","uz":"Qo‘l soati! Ovqat, kino, soat — bugun ancha pul sarflading-a?","ru":"Часы! Ужин, кино, часы — сегодня ты потратил немало денег, да?","tj":"Соат! Хӯрок, кино, соат — имрӯз пули зиёд сарф кардӣ, ҳамин тавр?"},
            {"speaker":"Liu Ming","zh":"虽然花了一些钱，但是我们过了一个快乐的生日。","pinyin":"Suīrán huāle yìxiē qián, dànshì wǒmen guòle yí ge kuàilè de shēngrì.","uz":"Bir oz pul sarflagan bo‘lsak ham, quvonchli tug‘ilgan kun o‘tkazdik.","ru":"Хотя потратили немного денег, зато отметили счастливый день рождения.","tj":"Гарчанде каме пул сарф кардем, зодрӯзи хушҳол гузарондем."}
        ]},
        {"block_no":4,"section_label":"课文 4","scene_zh":"小语在讲述王一雪和刘明的一天。","scene_uz":"Xiaoyu Wang Yixue va Liu Mingning bir kunini hikoya qilmoqda.","scene_ru":"Сяоюй рассказывает об одном дне Ван Исюэ и Лю Мина.","scene_tj":"Сяоюй як рӯзи Ван Исюэ ва Лю Минро нақл мекунад.","dialogue":[
            {"speaker":"Narration","zh":"虽然妻子忘了今天是自己的生日，但是丈夫记得。丈夫请妻子去饭馆吃饭、去电影院看电影，还给妻子买了一块非常漂亮的手表。妻子觉得今天很快乐。","pinyin":"Suīrán qīzi wàngle jīntiān shì zìjǐ de shēngrì, dànshì zhàngfu jìde. Zhàngfu qǐng qīzi qù fànguǎn chī fàn, qù diànyǐngyuàn kàn diànyǐng, hái gěi qīzi mǎile yí kuài fēicháng piàoliang de shǒubiǎo. Qīzi juéde jīntiān hěn kuàilè.","uz":"Xotin bugun o‘zining tug‘ilgan kuni ekanini unutgan bo‘lsa-da, eri esladi. Eri uni restoranga ovqatga, kinoteatrga film ko‘rgani olib bordi va unga juda chiroyli qo‘l soati sotib oldi. Xotin bugun juda xursand bo‘ldi.","ru":"Хотя жена забыла, что сегодня её день рождения, муж помнил. Он пригласил её в ресторан, затем в кино и купил ей очень красивые часы. Жена была очень счастлива.","tj":"Гарчанде зан фаромӯш карда буд, ки имрӯз зодрӯзаш аст, шавҳар дар хотир дошт. Ӯ занашро ба тарабхона ва кино бурд ва барояш соати хеле зебо харид. Зан имрӯз хеле хушҳол буд."}
        ]}
    ],ensure_ascii=False),
    "grammar_json":json.dumps([
        {"no":1,"title_zh":"比较句（1）","title_uz":"Taqqoslash gapi (1)","title_ru":"Сравнительное предложение (1)","title_tj":"Ҷумлаи муқоисавӣ (1)","rule_zh":"本课学习用介词“比”来比较性质和状态差别的比较句。基本结构：A比B+形容词或形容词性短语。","rule_uz":"“比” sifat yoki holatdagi farqni taqqoslaydi. Asosiy tuzilma: A 比 B + sifat/sifatli birikma.","rule_ru":"“比” используется для сравнения различий в признаке или состоянии. Схема: A 比 B + прилагательное/прилагательная группа.","rule_tj":"“比” фарқи хусусият ё ҳолатро муқоиса мекунад. Сохтор: A 比 B + сифат/ибораи сифатӣ.","examples":[{"zh":"我也觉得左边的比右边的好看。"},{"zh":"今天比昨天冷。"},{"zh":"他觉得踢足球比打篮球有意思。"}]},
        {"no":2,"title_zh":"比较句（2）","title_uz":"Taqqoslash gapi (2)","title_ru":"Сравнительное предложение (2)","title_tj":"Ҷумлаи муқоисавӣ (2)","rule_zh":"在用“比”的比较句中，形容词前不能用“很”“非常”等程度副词，可以用“还”和“更”表示程度加深。","rule_uz":"“比” taqqoslash gapida sifat oldidan 很 yoki 非常 ishlatilmaydi; darajani kuchaytirish uchun 还 yoki 更 ishlatiladi.","rule_ru":"В предложениях с 比 перед прилагательным нельзя ставить 很/非常; усиление выражается 还 или 更.","rule_tj":"Дар ҷумлаҳои бо 比 пеш аз сифат 很/非常 намеояд; барои қавитар кардани дараҷа 还 ё 更 истифода мешавад.","examples":[{"zh":"我看网上说这个电影比那个爱情片更有意思。"},{"zh":"今天比昨天更热。"},{"zh":"我觉得奶茶比牛奶还好喝。"}]},
        {"no":3,"title_zh":"转折复句“虽然……，但是……”","title_uz":"Qarama-qarshi qo‘shma gap “虽然……，但是……”","title_ru":"Уступительно-противительное предложение “虽然……，但是……”","title_tj":"Ҷумлаи зиддиятии “虽然……，但是……”","rule_zh":"“虽然……，但是……”构成转折复句，“虽然”和“但是”可以成对使用，也可以只用其中一个。","rule_uz":"“虽然……但是……” qarama-qarshi ma’noli qo‘shma gap tuzadi. 虽然 va 但是 birga ham, bittasi alohida ham ishlatilishi mumkin.","rule_ru":"“虽然……但是……” образует уступительно-противительное сложное предложение; 虽然 и 但是 употребляются вместе или по отдельности.","rule_tj":"“虽然……但是……” ҷумлаи зиддиятӣ месозад; 虽然 ва 但是 метавонанд якҷо ё алоҳида истифода шаванд.","examples":[{"zh":"虽然你忘了，但是我记得。"},{"zh":"外边下雪了，但是不太冷。"},{"zh":"虽然觉得有点儿累，我还是走回家了。"}]}
    ],ensure_ascii=False)
}
