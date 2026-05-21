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

_LESSON_2_VOCABULARY = [
    {"no": 1, "zh": "腿", "pinyin": "tuǐ", "pos": "n.", "uz": "oyoq", "ru": "нога", "tj": "по"},
    {"no": 2, "zh": "疼", "pinyin": "téng", "pos": "adj.", "uz": "og'riqli, og'rimoq", "ru": "болеть, больной", "tj": "дард кардан, дарднок"},
    {"no": 3, "zh": "脚", "pinyin": "jiǎo", "pos": "n.", "uz": "oyoq panjasi", "ru": "стопа, нога", "tj": "кафи по"},
    {"no": 4, "zh": "树", "pinyin": "shù", "pos": "n.", "uz": "daraxt", "ru": "дерево", "tj": "дарахт"},
    {"no": 5, "zh": "容易", "pinyin": "róngyì", "pos": "adj.", "uz": "oson", "ru": "лёгкий, простой", "tj": "осон"},
    {"no": 6, "zh": "难", "pinyin": "nán", "pos": "adj.", "uz": "qiyin", "ru": "трудный", "tj": "душвор"},
    {"no": 7, "zh": "太太", "pinyin": "tàitai", "pos": "n.", "uz": "xotin, xonim", "ru": "жена, госпожа", "tj": "зан, хонум"},
    {"no": 8, "zh": "秘书", "pinyin": "mìshū", "pos": "n.", "uz": "kotib, sekretar", "ru": "секретарь", "tj": "котиб"},
    {"no": 9, "zh": "经理", "pinyin": "jīnglǐ", "pos": "n.", "uz": "menejer, direktor", "ru": "менеджер, директор", "tj": "мудир, директор"},
    {"no": 10, "zh": "办公室", "pinyin": "bàngōngshì", "pos": "n.", "uz": "ofis, idora", "ru": "офис, кабинет", "tj": "идора, кабинет"},
    {"no": 11, "zh": "辆", "pinyin": "liàng", "pos": "m.", "uz": "transportlar uchun hisob so'zi", "ru": "счётное слово для транспорта", "tj": "ҳисобвожа барои нақлиёт"},
    {"no": 12, "zh": "楼", "pinyin": "lóu", "pos": "n.", "uz": "bino, qavat", "ru": "здание, этаж", "tj": "бино, ошёна"},
    {"no": 13, "zh": "拿", "pinyin": "ná", "pos": "v.", "uz": "olmoq, ushlamoq", "ru": "взять, держать", "tj": "гирифтан, доштан"},
    {"no": 14, "zh": "把", "pinyin": "bǎ", "pos": "m.", "uz": "tutqichli narsalar uchun hisob so'zi", "ru": "счётное слово для предметов с ручкой", "tj": "ҳисобвожа барои чизҳои дастадор"},
    {"no": 15, "zh": "伞", "pinyin": "sǎn", "pos": "n.", "uz": "soyabon", "ru": "зонт", "tj": "чатр"},
    {"no": 16, "zh": "胖", "pinyin": "pàng", "pos": "adj.", "uz": "semiz, to'la", "ru": "полный, толстый", "tj": "фарбеҳ"},
    {"no": 17, "zh": "其实", "pinyin": "qíshí", "pos": "adv.", "uz": "aslida, haqiqatan", "ru": "на самом деле", "tj": "дар асл"},
    {"no": 18, "zh": "瘦", "pinyin": "shòu", "pos": "adj.", "uz": "ozg'in, oriqlagan", "ru": "худой, похудевший", "tj": "лоғар"},
    {"no": 19, "zh": "周", "pinyin": "Zhōu", "pos": "proper noun", "uz": "Zhou (familiya)", "ru": "Чжоу (фамилия)", "tj": "Чжоу (насаб)"},
    {"no": 20, "zh": "周明", "pinyin": "Zhōu Míng", "pos": "proper noun", "uz": "Zhou Ming (ism)", "ru": "Чжоу Мин (имя)", "tj": "Чжоу Мин (ном)"},
]


_LESSON_2_DIALOGUES = [
    {
        "block_no": 1,
        "section_label": "课文 1",
        "scene_uz": "Tog'dan tushayotgan yo'lda",
        "scene_ru": "На пути вниз с горы",
        "scene_tj": "Дар роҳи фаромадан аз кӯҳ",
        "word_nos": [1, 2, 3, 4, 5, 6],
        "grammar_nos": [1],
        "dialogue": [
            {"speaker": "小丽", "zh": "休息一下吧。", "pinyin": "Xiūxi yíxià ba.", "uz": "Bir oz dam olaylik.", "ru": "Давай немного отдохнём.", "tj": "Каме истироҳат кунем."},
            {"speaker": "小刚", "zh": "怎么了？", "pinyin": "Zěnme le?", "uz": "Nima bo'ldi?", "ru": "Что случилось?", "tj": "Чӣ шуд?"},
            {"speaker": "小丽", "zh": "我现在腿也疼，脚也疼。", "pinyin": "Wǒ xiànzài tuǐ yě téng, jiǎo yě téng.", "uz": "Hozir oyog'im ham, oyoq panjam ham og'riyapti.", "ru": "Сейчас у меня болят и ноги, и стопы.", "tj": "Ҳоло поям ҳам, кафи поям ҳам дард мекунад."},
            {"speaker": "小刚", "zh": "好，那边树多，我们过去坐一下吧。", "pinyin": "Hǎo, nàbiān shù duō, wǒmen guòqu zuò yíxià ba.", "uz": "Xo'p, u tomonda daraxt ko'p, borib bir oz o'tiraylik.", "ru": "Хорошо, там много деревьев, пойдём посидим немного.", "tj": "Хуб, он тараф дарахт бисёр аст, равем каме нишинем."},
            {"speaker": "小丽", "zh": "上来的时候我怎么没觉得这么累？", "pinyin": "Shànglái de shíhou wǒ zěnme méi juéde zhème lèi?", "uz": "Yuqoriga chiqayotganimda nega bunchalik charchaganimni sezmadim?", "ru": "Почему, когда поднималась, я не чувствовала такой усталости?", "tj": "Чаро вақти боло омадан ин қадар хастагиро ҳис накардам?"},
            {"speaker": "小刚", "zh": "上山容易下山难，你不知道？", "pinyin": "Shàng shān róngyì xià shān nán, nǐ bù zhīdào?", "uz": "Tog'ga chiqish oson, tushish qiyin, bilmaysanmi?", "ru": "Подниматься в гору легко, спускаться трудно, разве не знаешь?", "tj": "Ба кӯҳ баромадан осон, фаромадан душвор, намедонӣ?"},
        ],
    },
    {
        "block_no": 2,
        "section_label": "课文 2",
        "scene_uz": "Telefonda",
        "scene_ru": "По телефону",
        "scene_tj": "Дар телефон",
        "word_nos": [7, 8, 9, 10, 19, 20],
        "grammar_nos": [1, 2],
        "dialogue": [
            {"speaker": "周太太", "zh": "喂，你好，请问周明在吗？", "pinyin": "Wèi, nǐ hǎo, qǐngwèn Zhōu Míng zài ma?", "uz": "Alo, salom, Zhou Ming bormi?", "ru": "Алло, здравствуйте, скажите, Чжоу Мин на месте?", "tj": "Алло, салом, Zhou Ming ҳаст?"},
            {"speaker": "秘书", "zh": "周经理出去了，不在办公室。", "pinyin": "Zhōu jīnglǐ chūqu le, bú zài bàngōngshì.", "uz": "Menejer Zhou chiqib ketdi, ofisda emas.", "ru": "Менеджер Чжоу вышел, его нет в офисе.", "tj": "Мудир Чжоу баромадааст, дар идора нест."},
            {"speaker": "周太太", "zh": "他去哪儿了？什么时候回来？", "pinyin": "Tā qù nǎr le? Shénme shíhou huílai?", "uz": "U qayerga ketdi? Qachon qaytadi?", "ru": "Куда он ушёл? Когда вернётся?", "tj": "Ӯ ба куҷо рафт? Кай бармегардад?"},
            {"speaker": "秘书", "zh": "他出去办事了，下午回来。", "pinyin": "Tā chūqu bàn shì le, xiàwǔ huílai.", "uz": "U ish bilan chiqib ketdi, tushdan keyin qaytadi.", "ru": "Он вышел по делам, вернётся после обеда.", "tj": "Ӯ барои кор баромад, баъд аз нисфирӯзӣ бармегардад."},
            {"speaker": "周太太", "zh": "回来了就让他给我打个电话。", "pinyin": "Huílai le jiù ràng tā gěi wǒ dǎ ge diànhuà.", "uz": "Qaytgach menga qo'ng'iroq qilsin.", "ru": "Когда вернётся, пусть позвонит мне.", "tj": "Вақте баргашт, бигӯ ба ман занг занад."},
            {"speaker": "秘书", "zh": "好的，他到了办公室我就告诉他。", "pinyin": "Hǎo de, tā dào le bàngōngshì wǒ jiù gàosu tā.", "uz": "Xo'p, u ofisga kelgach unga aytaman.", "ru": "Хорошо, как только он придёт в офис, я ему скажу.", "tj": "Хуб, вақте ба идора омад, ба ӯ мегӯям."},
        ],
    },
    {
        "block_no": 3,
        "section_label": "课文 3",
        "scene_uz": "Bino kirishida do'stni kuzatish",
        "scene_ru": "У выхода из здания, провожая друга",
        "scene_tj": "Дар назди даромади бино, гусел кардани дӯст",
        "word_nos": [11, 12, 13, 14, 15],
        "grammar_nos": [1, 2],
        "dialogue": [
            {"speaker": "小刚", "zh": "雨下得真大。你怎么回去？我送你吧。", "pinyin": "Yǔ xià de zhēn dà. Nǐ zěnme huíqu? Wǒ sòng nǐ ba.", "uz": "Yomg'ir juda kuchli yog'yapti. Qanday qaytasan? Men seni kuzatib qo'yay.", "ru": "Дождь идёт очень сильный. Как ты вернёшься? Давай я провожу тебя.", "tj": "Борон хеле сахт меборад. Чӣ тавр бармегардӣ? Ман туро гусел кунам."},
            {"speaker": "小丽", "zh": "没事，我出去叫辆出租车就行了。", "pinyin": "Méi shì, wǒ chūqu jiào liàng chūzūchē jiù xíng le.", "uz": "Hechqisi yo'q, chiqib taksi chaqirsam bo'ladi.", "ru": "Ничего, выйду и вызову такси.", "tj": "Ҳеҷ гап не, берун рафта таксӣ мегирам."},
            {"speaker": "小刚", "zh": "那你等等，我上楼去给你拿把伞。", "pinyin": "Nà nǐ děngdeng, wǒ shàng lóu qù gěi nǐ ná bǎ sǎn.", "uz": "Unda kutib tur, yuqoriga chiqib senga soyabon olib kelaman.", "ru": "Тогда подожди, я поднимусь наверх и принесу тебе зонт.", "tj": "Пас интизор шав, ман боло меравам ва барои ту чатр меорам."},
            {"speaker": "小丽", "zh": "好的。我跟你一起上去吧。", "pinyin": "Hǎo de. Wǒ gēn nǐ yìqǐ shàngqu ba.", "uz": "Xo'p. Men sen bilan birga yuqoriga chiqay.", "ru": "Хорошо. Я поднимусь вместе с тобой.", "tj": "Хуб. Ман бо ту якҷоя боло меравам."},
            {"speaker": "小刚", "zh": "你在这儿等吧，我拿了伞就下来。", "pinyin": "Nǐ zài zhèr děng ba, wǒ ná le sǎn jiù xiàlai.", "uz": "Sen shu yerda kut, soyabonni olib darhol tushaman.", "ru": "Ты подожди здесь, я возьму зонт и сразу спущусь.", "tj": "Ту ҳамин ҷо интизор шав, ман чатрро гирифта фавран поён меоям."},
        ],
    },
    {
        "block_no": 4,
        "section_label": "课文 4",
        "scene_uz": "Uyda",
        "scene_ru": "Дома",
        "scene_tj": "Дар хона",
        "word_nos": [16, 17, 18],
        "grammar_nos": [3],
        "dialogue": [
            {"speaker": "周太太", "zh": "你看，我这么胖，怎么办呢？", "pinyin": "Nǐ kàn, wǒ zhème pàng, zěnme bàn ne?", "uz": "Qara, men shuncha semizman, nima qilaman?", "ru": "Смотри, я такая полная, что мне делать?", "tj": "Бубин, ман ин қадар фарбеҳам, чӣ кор кунам?"},
            {"speaker": "周明", "zh": "你每天晚上吃了饭就睡觉，也不出去走走，能不胖吗？", "pinyin": "Nǐ měitiān wǎnshang chī le fàn jiù shuìjiào, yě bù chūqu zǒuzou, néng bù pàng ma?", "uz": "Har kuni kechqurun ovqat yeysan-u uxlaysan, tashqariga chiqib yurmayapsan ham, semirmaslik mumkinmi?", "ru": "Каждый вечер поешь и сразу спишь, даже не выходишь прогуляться, как тут не поправиться?", "tj": "Ҳар шаб хӯрок мехӯрӣ ва мехобӣ, берун ҳам намебароӣ, чӣ тавр фарбеҳ намешавӣ?"},
            {"speaker": "周太太", "zh": "其实我每天都运动。", "pinyin": "Qíshí wǒ měitiān dōu yùndòng.", "uz": "Aslida men har kuni mashq qilaman.", "ru": "На самом деле я каждый день занимаюсь спортом.", "tj": "Дар асл ман ҳар рӯз варзиш мекунам."},
            {"speaker": "周明", "zh": "但是你一点儿也没瘦！你做什么运动了？", "pinyin": "Dànshì nǐ yìdiǎnr yě méi shòu! Nǐ zuò shénme yùndòng le?", "uz": "Lekin umuman ozmagansan! Qanday mashq qilding?", "ru": "Но ты совсем не похудела! Каким спортом ты занималась?", "tj": "Аммо ту тамоман лоғар нашудаӣ! Чӣ варзиш кардӣ?"},
            {"speaker": "周太太", "zh": "做饭啊。", "pinyin": "Zuò fàn a.", "uz": "Ovqat pishirish-da.", "ru": "Готовкой еды.", "tj": "Хӯрокпазӣ."},
        ],
    },
]

_LESSON_3_VOCABULARY = [
    {"no": 1, "zh": "还是", "pinyin": "háishi", "pos": "conj.", "uz": "yoki (savolda tanlov)", "ru": "или (в вопросе выбора)", "tj": "ё (дар саволи интихобӣ)"},
    {"no": 2, "zh": "爬山", "pinyin": "pá shān", "pos": "v.", "uz": "toqqa chiqmoq", "ru": "подниматься в гору", "tj": "ба кӯҳ баромадан"},
    {"no": 3, "zh": "小心", "pinyin": "xiǎoxīn", "pos": "adj.", "uz": "ehtiyotkor, ehtiyot bo'lmoq", "ru": "осторожный, быть осторожным", "tj": "эҳтиёткор, эҳтиёт шудан"},
    {"no": 4, "zh": "条", "pinyin": "tiáo", "pos": "m.", "uz": "shim/ko'ylak kabi narsalar uchun hisob so'zi", "ru": "счётное слово для брюк, платьев и т.п.", "tj": "ҳисобвожа барои шим, курта ва ғ."},
    {"no": 5, "zh": "裤子", "pinyin": "kùzi", "pos": "n.", "uz": "shim", "ru": "брюки, штаны", "tj": "шим"},
    {"no": 6, "zh": "记得", "pinyin": "jìde", "pos": "v.", "uz": "eslamoq, yodda tutmoq", "ru": "помнить", "tj": "дар ёд доштан"},
    {"no": 7, "zh": "衬衫", "pinyin": "chènshān", "pos": "n.", "uz": "ko'ylak, rubashka", "ru": "рубашка", "tj": "курта"},
    {"no": 8, "zh": "元", "pinyin": "yuán", "pos": "m.", "uz": "yuan, pul birligi", "ru": "юань, денежная единица", "tj": "юан, воҳиди пул"},
    {"no": 9, "zh": "新鲜", "pinyin": "xīnxiān", "pos": "adj.", "uz": "yangi, sarhil", "ru": "свежий", "tj": "тару тоза"},
    {"no": 10, "zh": "甜", "pinyin": "tián", "pos": "adj.", "uz": "shirin", "ru": "сладкий", "tj": "ширин"},
    {"no": 11, "zh": "只", "pinyin": "zhǐ", "pos": "adv.", "uz": "faqat", "ru": "только", "tj": "фақат"},
    {"no": 12, "zh": "放", "pinyin": "fàng", "pos": "v.", "uz": "qo'ymoq, joylashtirmoq", "ru": "класть, ставить", "tj": "гузоштан"},
    {"no": 13, "zh": "饮料", "pinyin": "yǐnliào", "pos": "n.", "uz": "ichimlik", "ru": "напиток", "tj": "нӯшокӣ"},
    {"no": 14, "zh": "或者", "pinyin": "huòzhě", "pos": "conj.", "uz": "yoki (darak gapda)", "ru": "или (в повествовательном предложении)", "tj": "ё (дар ҷумлаи хабарӣ)"},
    {"no": 15, "zh": "舒服", "pinyin": "shūfu", "pos": "adj.", "uz": "qulay, rohat, o'zini yaxshi his qilish", "ru": "удобный, комфортный", "tj": "роҳат, бароҳат"},
    {"no": 16, "zh": "花", "pinyin": "huā", "pos": "n.", "uz": "gul", "ru": "цветок", "tj": "гул"},
    {"no": 17, "zh": "绿", "pinyin": "lǜ", "pos": "adj.", "uz": "yashil", "ru": "зелёный", "tj": "сабз"},
]


_LESSON_3_DIALOGUES = [
    {
        "block_no": 1,
        "section_label": "课文 1",
        "scene_uz": "Xiaolining uyida",
        "scene_ru": "У Сяоли дома",
        "scene_tj": "Дар хонаи Сяоли",
        "word_nos": [1, 2, 3],
        "grammar_nos": [1],
        "dialogue": [
            {"speaker": "小刚", "zh": "明天是晴天还是阴天？", "pinyin": "Míngtiān shì qíngtiān háishi yīntiān?", "uz": "Ertaga havo ochiq bo'ladimi yoki bulutlimi?", "ru": "Завтра будет ясно или пасмурно?", "tj": "Пагоҳ ҳаво офтобӣ мешавад ё абрнок?"},
            {"speaker": "小丽", "zh": "阴天，电视上说多云。怎么了？有事？", "pinyin": "Yīntiān, diànshì shang shuō duōyún. Zěnme le? Yǒu shì?", "uz": "Bulutli, televizorda ko'p bulut bo'ladi dedi. Nima bo'ldi? Ishing bormi?", "ru": "Пасмурно, по телевизору сказали облачно. Что случилось? Есть дела?", "tj": "Абрнок, телевизион гуфт абрнок мешавад. Чӣ шуд? Коре дорӣ?"},
            {"speaker": "小刚", "zh": "没事，我们明天要去爬山。", "pinyin": "Méi shì, wǒmen míngtiān yào qù pá shān.", "uz": "Hech narsa, ertaga toqqa chiqmoqchimiz.", "ru": "Ничего, завтра мы собираемся идти в горы.", "tj": "Ҳеҷ чиз, пагоҳ мехоҳем ба кӯҳ бароем."},
            {"speaker": "小丽", "zh": "爬山的时候要小心点儿。", "pinyin": "Pá shān de shíhou yào xiǎoxīn diǎnr.", "uz": "Toqqa chiqayotganda ehtiyot bo'linglar.", "ru": "Когда будете подниматься в горы, будьте осторожны.", "tj": "Вақти ба кӯҳ баромадан эҳтиёт бошед."},
            {"speaker": "小刚", "zh": "好，你也去吗？", "pinyin": "Hǎo, nǐ yě qù ma?", "uz": "Xo'p, sen ham borasanmi?", "ru": "Хорошо, ты тоже пойдёшь?", "tj": "Хуб, ту ҳам меравӣ?"},
            {"speaker": "小丽", "zh": "我不去，我有事。", "pinyin": "Wǒ bú qù, wǒ yǒu shì.", "uz": "Bormayman, ishim bor.", "ru": "Я не пойду, у меня дела.", "tj": "Ман намеравам, кор дорам."},
        ],
    },
    {
        "block_no": 2,
        "section_label": "课文 2",
        "scene_uz": "Savdo markazida",
        "scene_ru": "В торговом центре",
        "scene_tj": "Дар маркази савдо",
        "word_nos": [4, 5, 6, 7, 8],
        "grammar_nos": [2],
        "dialogue": [
            {"speaker": "周太太", "zh": "你觉得这条裤子怎么样？", "pinyin": "Nǐ juéde zhè tiáo kùzi zěnmeyàng?", "uz": "Bu shim qalay deb o'ylaysiz?", "ru": "Как тебе эти брюки?", "tj": "Ин шим ба назарат чӣ хел?"},
            {"speaker": "周明", "zh": "我记得你已经有两条这样的裤子了。", "pinyin": "Wǒ jìde nǐ yǐjīng yǒu liǎng tiáo zhèyàng de kùzi le.", "uz": "Esimda, senda bunday shimdan allaqachon ikkita bor.", "ru": "Я помню, у тебя уже есть две пары таких брюк.", "tj": "Дар ёдам ҳаст, ту аллакай ду чунин шим дорӣ."},
            {"speaker": "周太太", "zh": "那我们再看看别的。", "pinyin": "Nà wǒmen zài kànkan bié de.", "uz": "Unda boshqa narsalarni ko'raylik.", "ru": "Тогда посмотрим что-нибудь другое.", "tj": "Пас чизҳои дигарро бинем."},
            {"speaker": "周明", "zh": "这件衬衫怎么样？", "pinyin": "Zhè jiàn chènshān zěnmeyàng?", "uz": "Bu ko'ylak-chi?", "ru": "Как эта рубашка?", "tj": "Ин курта чӣ хел?"},
            {"speaker": "周太太", "zh": "还不错，多少钱？", "pinyin": "Hái búcuò, duōshao qián?", "uz": "Yomon emas, qancha turadi?", "ru": "Неплохо, сколько стоит?", "tj": "Бад нест, чанд пул?"},
            {"speaker": "周明", "zh": "这上面写着320元。", "pinyin": "Zhè shàngmian xiězhe sān bǎi èrshí yuán.", "uz": "Bu yerida 320 yuan deb yozilgan.", "ru": "Здесь написано 320 юаней.", "tj": "Дар ин ҷо 320 юан навишта шудааст."},
            {"speaker": "周太太", "zh": "买一件。", "pinyin": "Mǎi yí jiàn.", "uz": "Bittasini olaylik.", "ru": "Купим одну.", "tj": "Якторо мехарем."},
        ],
    },
    {
        "block_no": 3,
        "section_label": "课文 3",
        "scene_uz": "Meva do'konida",
        "scene_ru": "В фруктовом магазине",
        "scene_tj": "Дар мағозаи мева",
        "word_nos": [9, 10, 11],
        "grammar_nos": [1, 2],
        "dialogue": [
            {"speaker": "周太太", "zh": "这些水果真新鲜，我们买西瓜还是苹果？", "pinyin": "Zhèxiē shuǐguǒ zhēn xīnxiān, wǒmen mǎi xīguā háishi píngguǒ?", "uz": "Bu mevalar juda sarhil, tarvuz olamizmi yoki olma?", "ru": "Эти фрукты очень свежие, купим арбуз или яблоки?", "tj": "Ин меваҳо хеле тару тозаанд, тарбуз мехарем ё себ?"},
            {"speaker": "周明", "zh": "西瓜吧。你看，这上面写着“西瓜不甜不要钱”。", "pinyin": "Xīguā ba. Nǐ kàn, zhè shàngmian xiězhe 'xīguā bù tián bú yào qián'.", "uz": "Tarvuz olaylik. Qara, bu yerda 'tarvuz shirin bo'lmasa pul olmaymiz' deb yozilgan.", "ru": "Давай арбуз. Смотри, здесь написано: «если арбуз не сладкий, денег не берём».", "tj": "Тарбуз гирем. Бубин, ин ҷо навиштааст: «агар тарбуз ширин набошад, пул намегирем»."},
            {"speaker": "周太太", "zh": "那我们买一个大点儿的吧。", "pinyin": "Nà wǒmen mǎi yí ge dà diǎnr de ba.", "uz": "Unda kattarog'ini olaylik.", "ru": "Тогда купим побольше.", "tj": "Пас яктои калонтарашро мехарем."},
            {"speaker": "周明", "zh": "再买几个苹果。", "pinyin": "Zài mǎi jǐ ge píngguǒ.", "uz": "Yana bir nechta olma olaylik.", "ru": "Ещё купим несколько яблок.", "tj": "Боз чанд себ мехарем."},
            {"speaker": "周太太", "zh": "好啊，今天晚上只吃水果不吃饭！", "pinyin": "Hǎo a, jīntiān wǎnshang zhǐ chī shuǐguǒ bù chī fàn!", "uz": "Yaxshi, bugun kechqurun faqat meva yeymiz, ovqat yemaymiz!", "ru": "Хорошо, сегодня вечером будем есть только фрукты, без ужина!", "tj": "Хуб, имрӯз бегоҳ фақат мева мехӯрем, хӯрок не!"},
        ],
    },
    {
        "block_no": 4,
        "section_label": "课文 4",
        "scene_uz": "Dam olish xonasida",
        "scene_ru": "В комнате отдыха",
        "scene_tj": "Дар ҳуҷраи истироҳат",
        "word_nos": [12, 13, 14, 15, 16, 17],
        "grammar_nos": [1, 2, 3],
        "dialogue": [
            {"speaker": "小丽", "zh": "桌子上放着很多饮料，你喝什么？", "pinyin": "Zhuōzi shang fàngzhe hěn duō yǐnliào, nǐ hē shénme?", "uz": "Stol ustida ko'p ichimlik turibdi, nima ichasan?", "ru": "На столе стоит много напитков, что будешь пить?", "tj": "Дар рӯи миз нӯшокиҳои бисёр гузошта шудаанд, чӣ менӯшӣ?"},
            {"speaker": "小刚", "zh": "茶或者咖啡都可以。你呢？你喝什么？", "pinyin": "Chá huòzhě kāfēi dōu kěyǐ. Nǐ ne? Nǐ hē shénme?", "uz": "Choy yoki qahva, ikkalasi ham bo'ladi. Sen-chi? Nima ichasan?", "ru": "Чай или кофе, всё подойдёт. А ты? Что будешь пить?", "tj": "Чой ё қаҳва, ҳарду мешавад. Ту чӣ? Чӣ менӯшӣ?"},
            {"speaker": "小丽", "zh": "我喝茶，茶是我的最爱。天冷了或者工作累了的时候，喝杯热茶会很舒服。", "pinyin": "Wǒ hē chá, chá shì wǒ de zuì ài. Tiān lěng le huòzhě gōngzuò lèi le de shíhou, hē bēi rè chá huì hěn shūfu.", "uz": "Men choy ichaman, choy eng yoqtirganim. Havo sovuq bo'lganda yoki ishda charchaganda bir piyola issiq choy ichish juda rohat.", "ru": "Я буду чай, чай — моё любимое. Когда холодно или устал на работе, чашка горячего чая очень приятна.", "tj": "Ман чой менӯшам, чой дӯстдоштаи ман аст. Вақте ҳаво сард аст ё аз кор хаста мешавӣ, як пиёла чойи гарм хеле роҳат аст."},
            {"speaker": "小刚", "zh": "你喜欢喝什么茶？", "pinyin": "Nǐ xǐhuan hē shénme chá?", "uz": "Qanday choy ichishni yoqtirasan?", "ru": "Какой чай ты любишь пить?", "tj": "Кадом чойро нӯшидан дӯст медорӣ?"},
            {"speaker": "小丽", "zh": "花茶、绿茶、红茶，我都喜欢。", "pinyin": "Huāchá, lǜchá, hóngchá, wǒ dōu xǐhuan.", "uz": "Gul choyi, ko'k choy, qora choy — hammasini yaxshi ko'raman.", "ru": "Цветочный, зелёный, красный чай — всё люблю.", "tj": "Чойи гул, чойи сабз, чойи сурх — ҳамаро дӯст медорам."},
        ],
    },
]

_LESSON_4_VOCABULARY = [
    {"no": 1, "zh": "比赛", "pinyin": "bǐsài", "pos": "n.", "uz": "musobaqa", "ru": "соревнование", "tj": "мусобиқа"},
    {"no": 2, "zh": "照片", "pinyin": "zhàopiàn", "pos": "n.", "uz": "surat, fotosurat", "ru": "фотография", "tj": "акс"},
    {"no": 3, "zh": "年级", "pinyin": "niánjí", "pos": "n.", "uz": "sinf, kurs, bosqich", "ru": "класс, курс", "tj": "синф, курс"},
    {"no": 4, "zh": "又", "pinyin": "yòu", "pos": "adv.", "uz": "ham, yana; 又...又... qolipida", "ru": "и, также; в конструкции 又...又...", "tj": "ҳам, боз; дар сохтори 又...又..."},
    {"no": 5, "zh": "聪明", "pinyin": "cōngming", "pos": "adj.", "uz": "aqlli, zukko", "ru": "умный, сообразительный", "tj": "доно, зирак"},
    {"no": 6, "zh": "热情", "pinyin": "rèqíng", "pos": "adj.", "uz": "samimiy, iliq, faol", "ru": "тёплый, радушный, энергичный", "tj": "самимӣ, гарму ҷӯшон"},
    {"no": 7, "zh": "努力", "pinyin": "nǔlì", "pos": "adj./v.", "uz": "tirishqoq; harakat qilmoq", "ru": "старательный; стараться", "tj": "боғайрат; кӯшиш кардан"},
    {"no": 8, "zh": "总是", "pinyin": "zǒngshì", "pos": "adv.", "uz": "har doim, doim", "ru": "всегда", "tj": "ҳамеша"},
    {"no": 9, "zh": "回答", "pinyin": "huídá", "pos": "v.", "uz": "javob bermoq", "ru": "отвечать", "tj": "ҷавоб додан"},
    {"no": 10, "zh": "站", "pinyin": "zhàn", "pos": "v.", "uz": "turmoq", "ru": "стоять", "tj": "истодан"},
    {"no": 11, "zh": "饿", "pinyin": "è", "pos": "adj.", "uz": "och, qorni och", "ru": "голодный", "tj": "гурусна"},
    {"no": 12, "zh": "超市", "pinyin": "chāoshì", "pos": "n.", "uz": "supermarket", "ru": "супермаркет", "tj": "супермаркет"},
    {"no": 13, "zh": "蛋糕", "pinyin": "dàngāo", "pos": "n.", "uz": "tort, pirog", "ru": "торт, пирожное", "tj": "торт, кулча"},
    {"no": 14, "zh": "年轻", "pinyin": "niánqīng", "pos": "adj.", "uz": "yosh", "ru": "молодой", "tj": "ҷавон"},
    {"no": 15, "zh": "认真", "pinyin": "rènzhēn", "pos": "adj.", "uz": "jiddiy, mas'uliyatli", "ru": "серьёзный, добросовестный", "tj": "ҷиддӣ, масъулиятнок"},
    {"no": 16, "zh": "客人", "pinyin": "kèrén", "pos": "n.", "uz": "mehmon, mijoz", "ru": "гость, клиент", "tj": "меҳмон, муштарӣ"},
    {"no": 17, "zh": "小明", "pinyin": "Xiǎomíng", "pos": "proper noun", "uz": "Xiaoming (ism)", "ru": "Сяомин (имя)", "tj": "Сяомин (ном)"},
    {"no": 18, "zh": "马可", "pinyin": "Mǎkě", "pos": "proper noun", "uz": "Marco (ism)", "ru": "Марко (имя)", "tj": "Марко (ном)"},
    {"no": 19, "zh": "李小美", "pinyin": "Lǐ Xiǎoměi", "pos": "proper noun", "uz": "Li Xiaomei (ism)", "ru": "Ли Сяомэй (имя)", "tj": "Ли Сяомэй (ном)"},
]


_LESSON_4_DIALOGUES = [
    {
        "block_no": 1,
        "section_label": "课文 1",
        "scene_uz": "Sinfda",
        "scene_ru": "В классе",
        "scene_tj": "Дар синф",
        "word_nos": [1, 2, 3, 4, 17, 18],
        "grammar_nos": [1, 2],
        "dialogue": [
            {"speaker": "小明", "zh": "这是你们比赛的照片吗？", "pinyin": "Zhè shì nǐmen bǐsài de zhàopiàn ma?", "uz": "Bu sizlarning musobaqadagi suratingizmi?", "ru": "Это ваша фотография с соревнования?", "tj": "Ин акси мусобиқаи шумост?"},
            {"speaker": "马可", "zh": "是，这是我们比赛后照的。", "pinyin": "Shì, zhè shì wǒmen bǐsài hòu zhào de.", "uz": "Ha, bu musobaqadan keyin tushgan suratimiz.", "ru": "Да, это фото мы сделали после соревнования.", "tj": "Ҳа, ин аксро баъд аз мусобиқа гирифтаем."},
            {"speaker": "小明", "zh": "照得不错，你们都是一个年级的吗？", "pinyin": "Zhào de búcuò, nǐmen dōu shì yí ge niánjí de ma?", "uz": "Yaxshi tushibdi. Hammangiz bir sinfdamisiz?", "ru": "Хорошо получилось. Вы все из одного класса?", "tj": "Хуб баромадааст. Ҳамаатон аз як синфед?"},
            {"speaker": "马可", "zh": "不是。那个又高又漂亮的女孩儿是二年级的。", "pinyin": "Bú shì. Nà ge yòu gāo yòu piàoliang de nǚháir shì èr niánjí de.", "uz": "Yo'q. Ana u baland bo'yli va chiroyli qiz ikkinchi kursda.", "ru": "Нет. Та высокая и красивая девушка со второго курса.", "tj": "Не. Он духтари қадбаланду зебо аз курси дуюм аст."},
            {"speaker": "小明", "zh": "旁边那个拿着书笑的人是谁？", "pinyin": "Pángbiān nà ge názhe shū xiào de rén shì shéi?", "uz": "Yonidagi kitob ushlab kulib turgan odam kim?", "ru": "Кто тот человек рядом, который улыбается с книгой в руках?", "tj": "Касе ки паҳлӯяш китоб дар даст механдад, кист?"},
            {"speaker": "马可", "zh": "那是我！", "pinyin": "Nà shì wǒ!", "uz": "U menman!", "ru": "Это я!", "tj": "Ин манам!"},
        ],
    },
    {
        "block_no": 2,
        "section_label": "课文 2",
        "scene_uz": "Sinfda",
        "scene_ru": "В классе",
        "scene_tj": "Дар синф",
        "word_nos": [5, 6, 7, 8, 9, 10, 19],
        "grammar_nos": [1, 2, 3],
        "dialogue": [
            {"speaker": "小丽", "zh": "你觉得李小美怎么样？", "pinyin": "Nǐ juéde Lǐ Xiǎoměi zěnmeyàng?", "uz": "Li Xiaomei haqida qanday fikrdasan?", "ru": "Что ты думаешь о Ли Сяомэй?", "tj": "Ба фикрат Ли Сяомэй чӣ гуна аст?"},
            {"speaker": "同学", "zh": "她又聪明又热情，也很努力。", "pinyin": "Tā yòu cōngming yòu rèqíng, yě hěn nǔlì.", "uz": "U ham aqlli, ham samimiy, juda tirishqoq ham.", "ru": "Она и умная, и приветливая, и очень старательная.", "tj": "Вай ҳам доно, ҳам самимӣ ва хеле боғайрат аст."},
            {"speaker": "小丽", "zh": "我看她总是笑着回答老师的问题。", "pinyin": "Wǒ kàn tā zǒngshì xiàozhe huídá lǎoshī de wèntí.", "uz": "Ko'rsam, u doim kulib o'qituvchining savollariga javob beradi.", "ru": "Я вижу, она всегда отвечает на вопросы учителя с улыбкой.", "tj": "Мебинам, вай ҳамеша бо табассум ба саволҳои муаллим ҷавоб медиҳад."},
            {"speaker": "同学", "zh": "她对每个人都笑，也常常对我笑。", "pinyin": "Tā duì měi ge rén dōu xiào, yě chángcháng duì wǒ xiào.", "uz": "U hammaga kulib qaraydi, menga ham tez-tez kuladi.", "ru": "Она улыбается каждому и часто улыбается мне.", "tj": "Вай ба ҳар кас механдад, ба ман ҳам зуд-зуд механдад."},
            {"speaker": "小丽", "zh": "你是不是喜欢她啊？", "pinyin": "Nǐ shì bu shì xǐhuan tā a?", "uz": "Sen uni yoqtirib qoldingmi?", "ru": "Ты что, она тебе нравится?", "tj": "Ту ӯро дӯст медорӣ?"},
            {"speaker": "同学", "zh": "喜欢她的人太多了，你看那些拿着鲜花站在门口的，都是等她的。", "pinyin": "Xǐhuan tā de rén tài duō le, nǐ kàn nàxiē názhe xiānhuā zhàn zài ménkǒu de, dōu shì děng tā de.", "uz": "Uni yoqtiradiganlar juda ko'p. Qara, eshik oldida gul ushlab turganlarning hammasi uni kutyapti.", "ru": "Тех, кому она нравится, очень много. Видишь тех с цветами у двери? Все ждут её.", "tj": "Онҳое, ки ӯро дӯст медоранд, хеле зиёданд. Ана онҳое, ки дар назди дар гул доранд, ҳама ӯро интизоранд."},
        ],
    },
    {
        "block_no": 3,
        "section_label": "课文 3",
        "scene_uz": "Supermarket kirishida",
        "scene_ru": "У входа в супермаркет",
        "scene_tj": "Дар даромади супермаркет",
        "word_nos": [11, 12, 13],
        "grammar_nos": [1, 2],
        "dialogue": [
            {"speaker": "小刚", "zh": "我有点儿饿了，我们进超市买点儿东西吧。", "pinyin": "Wǒ yǒudiǎnr è le, wǒmen jìn chāoshì mǎi diǎnr dōngxi ba.", "uz": "Qornim biroz ochdi, supermarketga kirib biror narsa olaylik.", "ru": "Я немного проголодался, давай зайдём в супермаркет и что-нибудь купим.", "tj": "Ман каме гурусна шудам, ба супермаркет даромада чизе харем."},
            {"speaker": "小丽", "zh": "好啊，这家超市的蛋糕又便宜又好吃，一块只要2.99元。", "pinyin": "Hǎo a, zhè jiā chāoshì de dàngāo yòu piányi yòu hǎochī, yí kuài zhǐ yào èr diǎn jiǔ jiǔ yuán.", "uz": "Yaxshi, bu supermarketning torti ham arzon, ham mazali, bir bo'lagi faqat 2.99 yuan.", "ru": "Хорошо, в этом супермаркете торт и дешёвый, и вкусный: кусок всего 2.99 юаня.", "tj": "Хуб, торти ин супермаркет ҳам арзон, ҳам болаззат аст, як дона ҳамагӣ 2.99 юан."},
            {"speaker": "小刚", "zh": "我们买两块，回家吃着蛋糕看电视，怎么样？", "pinyin": "Wǒmen mǎi liǎng kuài, huí jiā chīzhe dàngāo kàn diànshì, zěnmeyàng?", "uz": "Ikki bo'lak olaylik, uyga borib tort yeb televizor ko'ramiz, qalay?", "ru": "Купим два куска, дома будем есть торт и смотреть телевизор, как тебе?", "tj": "Ду дона мехарем, ба хона рафта торт мехӯрему телевизор мебинем, чӣ хел?"},
            {"speaker": "小丽", "zh": "好啊，我再去买一些喝的。", "pinyin": "Hǎo a, wǒ zài qù mǎi yìxiē hē de.", "uz": "Yaxshi, men yana ichimlik olib kelaman.", "ru": "Хорошо, я ещё куплю что-нибудь выпить.", "tj": "Хуб, ман боз каме нӯшокӣ мехарам."},
            {"speaker": "小刚", "zh": "喝着咖啡吃蛋糕，太好了！", "pinyin": "Hēzhe kāfēi chī dàngāo, tài hǎo le!", "uz": "Qahva ichib tort yeyish, juda zo'r!", "ru": "Пить кофе и есть торт - отлично!", "tj": "Қаҳва нӯшида торт хӯрдан - хеле хуб!"},
        ],
    },
    {
        "block_no": 4,
        "section_label": "课文 4",
        "scene_uz": "Restoranda",
        "scene_ru": "В ресторане",
        "scene_tj": "Дар тарабхона",
        "word_nos": [14, 15, 16, 19],
        "grammar_nos": [1, 2, 3],
        "dialogue": [
            {"speaker": "经理", "zh": "您好！您找谁？", "pinyin": "Nín hǎo! Nín zhǎo shéi?", "uz": "Salom! Kimni izlayapsiz?", "ru": "Здравствуйте! Кого вы ищете?", "tj": "Салом! Шумо киро меҷӯед?"},
            {"speaker": "客人", "zh": "你们这儿是不是有一个又年轻又漂亮的服务员？", "pinyin": "Nǐmen zhèr shì bu shì yǒu yí ge yòu niánqīng yòu piàoliang de fúwùyuán?", "uz": "Sizlarda yosh va chiroyli ofitsiant qiz bormi?", "ru": "У вас здесь есть молодая и красивая официантка?", "tj": "Дар ин ҷо як хизматрасони ҷавону зебо ҳаст?"},
            {"speaker": "经理", "zh": "我们这儿年轻、漂亮的服务员有很多。", "pinyin": "Wǒmen zhèr niánqīng, piàoliang de fúwùyuán yǒu hěn duō.", "uz": "Bizda yosh va chiroyli ofitsiantlar ko'p.", "ru": "У нас много молодых и красивых официанток.", "tj": "Дар мо хизматрасонҳои ҷавону зебо бисёранд."},
            {"speaker": "客人", "zh": "她工作又认真又热情。", "pinyin": "Tā gōngzuò yòu rènzhēn yòu rèqíng.", "uz": "U ishda ham jiddiy, ham samimiy.", "ru": "Она работает и серьёзно, и приветливо.", "tj": "Вай дар кор ҳам ҷиддӣ, ҳам самимӣ аст."},
            {"speaker": "经理", "zh": "您能再说说吗？", "pinyin": "Nín néng zài shuōshuo ma?", "uz": "Yana biroz aytib bera olasizmi?", "ru": "Можете рассказать ещё?", "tj": "Метавонед боз каме гӯед?"},
            {"speaker": "客人", "zh": "她总是笑着跟客人说话。", "pinyin": "Tā zǒngshì xiàozhe gēn kèrén shuōhuà.", "uz": "U doim mijozlar bilan kulib gaplashadi.", "ru": "Она всегда разговаривает с гостями с улыбкой.", "tj": "Вай ҳамеша бо муштариён бо табассум суҳбат мекунад."},
            {"speaker": "经理", "zh": "啊，我知道了，你说的是李小美吧？", "pinyin": "A, wǒ zhīdào le, nǐ shuō de shì Lǐ Xiǎoměi ba?", "uz": "A, tushundim, siz Li Xiaomei haqida gapiryapsiz, shundaymi?", "ru": "А, понял, вы говорите о Ли Сяомэй, да?", "tj": "А, фаҳмидам, шумо дар бораи Ли Сяомэй мегӯед, ҳамин тавр?"},
        ],
    },
]


_PDF_MATERIALS = {
    1: (_LESSON_1_VOCABULARY, _LESSON_1_DIALOGUES),
    2: (_LESSON_2_VOCABULARY, _LESSON_2_DIALOGUES),
    3: (_LESSON_3_VOCABULARY, _LESSON_3_DIALOGUES),
    4: (_LESSON_4_VOCABULARY, _LESSON_4_DIALOGUES),
}


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
    material = _PDF_MATERIALS.get(lesson_order)
    if not material:
        return lesson

    vocab, source_dialogues = material
    grammar = json.loads(lesson.get("grammar_json") or "[]")
    dialogues = json.loads(json.dumps(source_dialogues, ensure_ascii=False))
    for block in dialogues:
        block_no = int(block.get("block_no") or 0)
        words = [_word_by_no(vocab, no) for no in block.get("word_nos", [])]
        words = [word for word in words if word]
        block["mini_quiz"] = _mini_quiz(lesson_order, block_no, vocab, grammar, block)
        block["mini_homework"] = _mini_homework(block_no, words)

    lesson["vocabulary_json"] = json.dumps(vocab, ensure_ascii=False)
    lesson["dialogue_json"] = json.dumps(dialogues, ensure_ascii=False)
    return lesson
