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


_LESSON_5_VOCABULARY = [
    {"no": 1, "zh": "发烧", "pinyin": "fāshāo", "pos": "v.", "uz": "isitmasi chiqmoq", "ru": "температурить", "tj": "таб кардан"},
    {"no": 2, "zh": "为", "pinyin": "wèi", "pos": "prep.", "uz": "uchun", "ru": "для, ради", "tj": "барои"},
    {"no": 3, "zh": "照顾", "pinyin": "zhàogù", "pos": "v.", "uz": "qaramoq, parvarish qilmoq", "ru": "заботиться, ухаживать", "tj": "нигоҳубин кардан"},
    {"no": 4, "zh": "用", "pinyin": "yòng", "pos": "v.", "uz": "kerak bo'lmoq, ishlatmoq", "ru": "нужно; использовать", "tj": "лозим шудан; истифода бурдан"},
    {"no": 5, "zh": "感冒", "pinyin": "gǎnmào", "pos": "v.", "uz": "shamollamoq", "ru": "простудиться", "tj": "шамол хӯрдан"},
    {"no": 6, "zh": "季节", "pinyin": "jìjié", "pos": "n.", "uz": "fasl", "ru": "сезон", "tj": "фасл"},
    {"no": 7, "zh": "当然", "pinyin": "dāngrán", "pos": "adv.", "uz": "albatta", "ru": "конечно", "tj": "албатта"},
    {"no": 8, "zh": "春(天)", "pinyin": "chūn(tiān)", "pos": "n.", "uz": "bahor", "ru": "весна", "tj": "баҳор"},
    {"no": 9, "zh": "草", "pinyin": "cǎo", "pos": "n.", "uz": "o't, maysa", "ru": "трава", "tj": "алаф"},
    {"no": 10, "zh": "夏(天)", "pinyin": "xià(tiān)", "pos": "n.", "uz": "yoz", "ru": "лето", "tj": "тобистон"},
    {"no": 11, "zh": "裙子", "pinyin": "qúnzi", "pos": "n.", "uz": "yubka, ko'ylak", "ru": "юбка, платье", "tj": "юбка, курта"},
    {"no": 12, "zh": "最近", "pinyin": "zuìjìn", "pos": "adv.", "uz": "yaqinda, oxirgi paytlarda", "ru": "недавно, в последнее время", "tj": "ба наздикӣ, вақтҳои охир"},
    {"no": 13, "zh": "越", "pinyin": "yuè", "pos": "adv.", "uz": "borgan sari, tobora", "ru": "чем дальше, тем; всё более", "tj": "ҳар қадар, торафт"},
    {"no": 14, "zh": "张", "pinyin": "Zhāng", "pos": "proper noun", "uz": "Zhang (familiya)", "ru": "Чжан (фамилия)", "tj": "Чжан (насаб)"},
]


_LESSON_5_DIALOGUES = [
    {
        "block_no": 1,
        "section_label": "课文 1",
        "scene_uz": "Xiaolining uyida",
        "scene_ru": "У Сяоли дома",
        "scene_tj": "Дар хонаи Сяоли",
        "word_nos": [1, 2],
        "grammar_nos": [1, 3],
        "dialogue": [
            {"speaker": "朋友", "zh": "我听说你身体不舒服，怎么了？", "pinyin": "Wǒ tīngshuō nǐ shēntǐ bù shūfu, zěnme le?", "uz": "Eshitishimcha, mazang yo'q ekan, nima bo'ldi?", "ru": "Я слышал, ты плохо себя чувствуешь, что случилось?", "tj": "Шунидам, ки худро хуб ҳис намекунӣ, чӣ шуд?"},
            {"speaker": "小丽", "zh": "前几天有点儿发烧，现在好多了。", "pinyin": "Qián jǐ tiān yǒudiǎnr fāshāo, xiànzài hǎoduō le.", "uz": "Bir necha kun oldin biroz isitmam bor edi, hozir ancha yaxshi.", "ru": "Несколько дней назад была небольшая температура, сейчас намного лучше.", "tj": "Чанд рӯз пеш каме таб доштам, ҳоло хеле беҳтар аст."},
            {"speaker": "朋友", "zh": "喝杯茶吧，这是我为你买的绿茶，很不错。", "pinyin": "Hē bēi chá ba, zhè shì wǒ wèi nǐ mǎi de lǜchá, hěn búcuò.", "uz": "Bir piyola choy ich, bu men sen uchun olgan yashil choy, juda yaxshi.", "ru": "Выпей чашку чая, это зелёный чай, который я купил для тебя, очень неплохой.", "tj": "Як пиёла чой нӯш, ин чойи сабзест, ки барои ту харидам, хеле хуб аст."},
            {"speaker": "小丽", "zh": "谢谢，我要吃药，不喝茶了。", "pinyin": "Xièxie, wǒ yào chī yào, bù hē chá le.", "uz": "Rahmat, dori ichishim kerak, endi choy ichmayman.", "ru": "Спасибо, мне нужно принять лекарство, чай уже не буду пить.", "tj": "Ташаккур, бояд дору хӯрам, дигар чой намехӯрам."},
            {"speaker": "朋友", "zh": "那喝杯水吧。", "pinyin": "Nà hē bēi shuǐ ba.", "uz": "Unda bir piyola suv ich.", "ru": "Тогда выпей стакан воды.", "tj": "Пас як пиёла об нӯш."},
            {"speaker": "小丽", "zh": "好的。", "pinyin": "Hǎo de.", "uz": "Xo'p.", "ru": "Хорошо.", "tj": "Хуб."},
        ],
    },
    {
        "block_no": 2,
        "section_label": "课文 2",
        "scene_uz": "Telefonda",
        "scene_ru": "По телефону",
        "scene_tj": "Дар телефон",
        "word_nos": [3, 4, 5, 14],
        "grammar_nos": [1],
        "dialogue": [
            {"speaker": "周太太", "zh": "对不起，我明天不能和你们出去玩儿了。", "pinyin": "Duìbuqǐ, wǒ míngtiān bù néng hé nǐmen chūqu wánr le.", "uz": "Kechirasiz, ertaga sizlar bilan aylanishga chiqa olmayman.", "ru": "Извините, завтра я не смогу пойти с вами гулять.", "tj": "Бубахшед, пагоҳ бо шумо берун рафта наметавонам."},
            {"speaker": "张太太", "zh": "为什么？怎么了？", "pinyin": "Wèi shénme? Zěnme le?", "uz": "Nega? Nima bo'ldi?", "ru": "Почему? Что случилось?", "tj": "Чаро? Чӣ шуд?"},
            {"speaker": "周太太", "zh": "我儿子生病了，我要在家照顾他。", "pinyin": "Wǒ érzi shēng bìng le, wǒ yào zài jiā zhàogù tā.", "uz": "O'g'lim kasal bo'lib qoldi, uyda unga qarashim kerak.", "ru": "Мой сын заболел, мне нужно дома ухаживать за ним.", "tj": "Писарам бемор шуд, бояд дар хона ӯро нигоҳубин кунам."},
            {"speaker": "张太太", "zh": "他吃药了吗？要不要去医院？", "pinyin": "Tā chī yào le ma? Yào bu yào qù yīyuàn?", "uz": "U dori ichdimi? Kasalxonaga borish kerakmi?", "ru": "Он принял лекарство? Нужно ехать в больницу?", "tj": "Ӯ дору хӯрд? Ба беморхона рафтан лозим аст?"},
            {"speaker": "周太太", "zh": "不用去医院，昨天吃了感冒药，现在好一些了。", "pinyin": "Búyòng qù yīyuàn, zuótiān chī le gǎnmào yào, xiànzài hǎo yìxiē le.", "uz": "Kasalxonaga borish shart emas, kecha shamollash dorisini ichdi, hozir biroz yaxshi.", "ru": "В больницу не нужно, вчера принял лекарство от простуды, сейчас немного лучше.", "tj": "Ба беморхона рафтан лозим нест, дирӯз доруи шамолхӯрӣ хӯрд, ҳоло каме беҳтар аст."},
            {"speaker": "张太太", "zh": "那我们下次再一起出去玩儿吧。", "pinyin": "Nà wǒmen xià cì zài yìqǐ chūqu wánr ba.", "uz": "Unda keyingi safar birga chiqamiz.", "ru": "Тогда в следующий раз вместе пойдём гулять.", "tj": "Пас дафъаи дигар якҷоя берун меравем."},
        ],
    },
    {
        "block_no": 3,
        "section_label": "课文 3",
        "scene_uz": "Xiaogangning uyida",
        "scene_ru": "У Сяогана дома",
        "scene_tj": "Дар хонаи Сяогang",
        "word_nos": [6, 7, 8, 9, 10, 11],
        "grammar_nos": [1],
        "dialogue": [
            {"speaker": "小丽", "zh": "你最喜欢哪个季节？", "pinyin": "Nǐ zuì xǐhuan nǎ ge jìjié?", "uz": "Qaysi faslni eng yaxshi ko'rasan?", "ru": "Какое время года тебе нравится больше всего?", "tj": "Кадом фаслро аз ҳама бештар дӯст медорӣ?"},
            {"speaker": "小刚", "zh": "当然是春天，天气不那么冷了，草和树都绿了，花也开了。", "pinyin": "Dāngrán shì chūntiān, tiānqì bù nàme lěng le, cǎo hé shù dōu lǜ le, huā yě kāi le.", "uz": "Albatta bahor, havo endi unchalik sovuq emas, o'tlar va daraxtlar yashillandi, gullar ham ochildi.", "ru": "Конечно весну: погода уже не такая холодная, трава и деревья стали зелёными, цветы тоже раскрылись.", "tj": "Албатта баҳорро: ҳаво дигар он қадар сард нест, алафу дарахтон сабз шуданд, гулҳо ҳам кушоданд."},
            {"speaker": "小丽", "zh": "我最喜欢夏天，因为我可以穿漂亮的裙子了。", "pinyin": "Wǒ zuì xǐhuan xiàtiān, yīnwèi wǒ kěyǐ chuān piàoliang de qúnzi le.", "uz": "Men yozni eng yaxshi ko'raman, chunki chiroyli ko'ylak kiyishim mumkin bo'ladi.", "ru": "Мне больше всего нравится лето, потому что можно носить красивое платье.", "tj": "Ман тобистонро аз ҳама бештар дӯст медорам, чунки метавонам куртаи зебо пӯшам."},
            {"speaker": "小刚", "zh": "那我也喜欢夏天了。", "pinyin": "Nà wǒ yě xǐhuan xiàtiān le.", "uz": "Unda men ham yozni yaxshi ko'rib qoldim.", "ru": "Тогда мне тоже стало нравиться лето.", "tj": "Пас ман ҳам тобистонро дӯст медорам."},
            {"speaker": "小丽", "zh": "怎么？你也有漂亮的裙子？", "pinyin": "Zěnme? Nǐ yě yǒu piàoliang de qúnzi?", "uz": "Nima? Senda ham chiroyli ko'ylak bormi?", "ru": "Что? У тебя тоже есть красивое платье?", "tj": "Чӣ? Ту ҳам куртаи зебо дорӣ?"},
            {"speaker": "小刚", "zh": "不，我喜欢看你穿漂亮的裙子。", "pinyin": "Bù, wǒ xǐhuan kàn nǐ chuān piàoliang de qúnzi.", "uz": "Yo'q, men seni chiroyli ko'ylakda ko'rishni yaxshi ko'raman.", "ru": "Нет, мне нравится смотреть, как ты носишь красивое платье.", "tj": "Не, ман дидани туро бо куртаи зебо дӯст медорам."},
        ],
    },
    {
        "block_no": 4,
        "section_label": "课文 4",
        "scene_uz": "Xiaogangning uyida",
        "scene_ru": "У Сяогана дома",
        "scene_tj": "Дар хонаи Сяогang",
        "word_nos": [12, 13],
        "grammar_nos": [1, 2],
        "dialogue": [
            {"speaker": "小丽", "zh": "我最近越来越胖了。", "pinyin": "Wǒ zuìjìn yuè lái yuè pàng le.", "uz": "Oxirgi paytlarda tobora semirib ketyapman.", "ru": "В последнее время я становлюсь всё полнее.", "tj": "Вақтҳои охир торафт фарбеҳ шуда истодаам."},
            {"speaker": "小刚", "zh": "谁说的？我觉得你越来越漂亮了。", "pinyin": "Shéi shuō de? Wǒ juéde nǐ yuè lái yuè piàoliang le.", "uz": "Kim aytdi? Menimcha sen tobora chiroyli bo'lyapsan.", "ru": "Кто сказал? По-моему, ты становишься всё красивее.", "tj": "Кӣ гуфт? Ба фикрам ту торафт зеботар мешавӣ."},
            {"speaker": "小丽", "zh": "你看，这条裙子是去年买的，今年就不能穿了。", "pinyin": "Nǐ kàn, zhè tiáo qúnzi shì qùnián mǎi de, jīnnián jiù bù néng chuān le.", "uz": "Qara, bu ko'ylakni o'tgan yili olgandim, bu yil kiyolmay qoldim.", "ru": "Смотри, это платье куплено в прошлом году, а в этом году уже не могу его носить.", "tj": "Бубин, ин куртаро соли гузашта харида будам, имсол дигар пӯшида наметавонам."},
            {"speaker": "小刚", "zh": "那是因为你吃得太多了，少吃点儿吧。", "pinyin": "Nà shì yīnwèi nǐ chī de tài duō le, shǎo chī diǎnr ba.", "uz": "Bu sen juda ko'p yeganing uchun, kamroq ye.", "ru": "Это потому что ты слишком много ешь, ешь поменьше.", "tj": "Ин барои он аст, ки бисёр мехӯрӣ, камтар бихӯр."},
            {"speaker": "小丽", "zh": "我做的饭越来越好吃，我能少吃吗？", "pinyin": "Wǒ zuò de fàn yuè lái yuè hǎochī, wǒ néng shǎo chī ma?", "uz": "Men pishirgan ovqat tobora mazali bo'lyapti, kam yeya olamanmi?", "ru": "Еда, которую я готовлю, становится всё вкуснее, разве я могу есть меньше?", "tj": "Хӯроке, ки ман мепазам, торафт болаззат мешавад, магар кам хӯрда метавонам?"},
        ],
    },
]


_LESSON_6_VOCABULARY = [
    {"no": 1, "zh": "眼镜", "pinyin": "yǎnjing", "pos": "n.", "uz": "ko'zoynak", "ru": "очки", "tj": "айнак"},
    {"no": 2, "zh": "突然", "pinyin": "tūrán", "pos": "adv.", "uz": "to'satdan", "ru": "вдруг, внезапно", "tj": "ногаҳон"},
    {"no": 3, "zh": "离开", "pinyin": "líkāi", "pos": "v.", "uz": "tark etmoq, ajralmoq", "ru": "покидать, расставаться", "tj": "тарк кардан, ҷудо шудан"},
    {"no": 4, "zh": "清楚", "pinyin": "qīngchu", "pos": "adj.", "uz": "aniq, ravshan", "ru": "ясный, чёткий", "tj": "равшан, аниқ"},
    {"no": 5, "zh": "刚才", "pinyin": "gāngcái", "pos": "n.", "uz": "hozirgina, sal oldin", "ru": "только что", "tj": "ҳозир, каме пеш"},
    {"no": 6, "zh": "帮忙", "pinyin": "bāng máng", "pos": "v.", "uz": "yordam bermoq", "ru": "помогать", "tj": "ёрӣ додан"},
    {"no": 7, "zh": "特别", "pinyin": "tèbié", "pos": "adv.", "uz": "ayniqsa, juda", "ru": "особенно, чрезвычайно", "tj": "махсусан, хеле"},
    {"no": 8, "zh": "讲", "pinyin": "jiǎng", "pos": "v.", "uz": "tushuntirmoq, aytmoq", "ru": "объяснять, говорить", "tj": "фаҳмондан, гуфтан"},
    {"no": 9, "zh": "明白", "pinyin": "míngbai", "pos": "adj.", "uz": "tushunarli, ravshan", "ru": "понятный, ясный", "tj": "фаҳмо, равшан"},
    {"no": 10, "zh": "锻炼", "pinyin": "duànliàn", "pos": "v.", "uz": "jismoniy mashq qilmoq", "ru": "заниматься физическими упражнениями", "tj": "машқи ҷисмонӣ кардан"},
    {"no": 11, "zh": "音乐", "pinyin": "yīnyuè", "pos": "n.", "uz": "musiqa", "ru": "музыка", "tj": "мусиқӣ"},
    {"no": 12, "zh": "公园", "pinyin": "gōngyuán", "pos": "n.", "uz": "park, bog'", "ru": "парк", "tj": "боғ"},
    {"no": 13, "zh": "聊天(儿)", "pinyin": "liáo tiān(r)", "pos": "v.", "uz": "suhbatlashmoq, gaplashmoq", "ru": "болтать, беседовать", "tj": "суҳбат кардан"},
    {"no": 14, "zh": "睡着", "pinyin": "shuì zháo", "pos": "v.", "uz": "uxlab qolmoq", "ru": "заснуть", "tj": "хоб рафтан"},
    {"no": 15, "zh": "更", "pinyin": "gèng", "pos": "adv.", "uz": "yanada, ko'proq", "ru": "ещё более", "tj": "боз ҳам"},
]


_LESSON_6_DIALOGUES = [
    {
        "block_no": 1,
        "section_label": "课文 1",
        "scene_uz": "Mehmonxonada",
        "scene_ru": "В гостиной",
        "scene_tj": "Дар меҳмонхона",
        "word_nos": [1, 2, 3, 4, 5, 6],
        "grammar_nos": [1, 2, 3],
        "dialogue": [
            {"speaker": "周明", "zh": "我的眼镜呢？怎么突然找不到了？你看见了吗？", "pinyin": "Wǒ de yǎnjing ne? Zěnme tūrán zhǎo bu dào le? Nǐ kànjiàn le ma?", "uz": "Ko'zoynagim qani? Qanday qilib birdan topolmay qoldim? Ko'rdingmi?", "ru": "Где мои очки? Почему вдруг не могу их найти? Ты видела?", "tj": "Айнакам куҷост? Чаро ногаҳон ёфта наметавонам? Дидӣ?"},
            {"speaker": "周太太", "zh": "我没看见啊。", "pinyin": "Wǒ méi kànjiàn a.", "uz": "Ko'rmadim-ku.", "ru": "Я не видела.", "tj": "Надидам."},
            {"speaker": "周明", "zh": "我离不开眼镜，没有眼镜，我一个字也看不清楚。", "pinyin": "Wǒ lí bu kāi yǎnjing, méiyǒu yǎnjing, wǒ yí ge zì yě kàn bu qīngchu.", "uz": "Men ko'zoynaksiz yurolmayman, ko'zoynaksiz bitta harfni ham aniq ko'rolmayman.", "ru": "Я не могу без очков, без них я ни одного иероглифа не вижу ясно.", "tj": "Ман бе айнак наметавонам, бе айнак ҳатто як ҳарфро равшан намебинам."},
            {"speaker": "周太太", "zh": "你去房间找找，是不是刚才放在桌子上了？", "pinyin": "Nǐ qù fángjiān zhǎozhao, shì bu shì gāngcái fàng zài zhuōzi shang le?", "uz": "Xonaga borib qidirib ko'r, hozirgina stol ustiga qo'ymadingmi?", "ru": "Пойди в комнату поищи, может, ты только что положил их на стол?", "tj": "Ба хона рафта ҷустуҷӯ кун, шояд ҳозир ба рӯи миз гузошта будӣ?"},
            {"speaker": "周明", "zh": "我怎么看得到啊？你快过来帮忙啊。", "pinyin": "Wǒ zěnme kàn de dào a? Nǐ kuài guòlai bāngmáng a.", "uz": "Qanday qilib ko'ra olaman? Tez kelib yordam ber.", "ru": "Как я смогу увидеть? Иди скорее помоги.", "tj": "Чӣ тавр дида метавонам? Зуд биё, ёрӣ деҳ."},
            {"speaker": "周太太", "zh": "好吧，我帮你去找找。", "pinyin": "Hǎo ba, wǒ bāng nǐ qù zhǎozhao.", "uz": "Mayli, qidirishga yordam beraman.", "ru": "Ладно, помогу тебе поискать.", "tj": "Хуб, ба ту дар ҷустуҷӯ ёрӣ медиҳам."},
        ],
    },
    {
        "block_no": 2,
        "section_label": "课文 2",
        "scene_uz": "Telefonda",
        "scene_ru": "По телефону",
        "scene_tj": "Дар телефон",
        "word_nos": [7, 8, 9, 10],
        "grammar_nos": [1, 3],
        "dialogue": [
            {"speaker": "同学", "zh": "今天的作业你做完了吗？", "pinyin": "Jīntiān de zuòyè nǐ zuòwán le ma?", "uz": "Bugungi uy vazifasini bajarib bo'ldingmi?", "ru": "Ты сделал сегодняшнее домашнее задание?", "tj": "Вазифаи хонагии имрӯзаро иҷро кардӣ?"},
            {"speaker": "儿子", "zh": "刚做完，你呢？", "pinyin": "Gāng zuòwán, nǐ ne?", "uz": "Hozirgina tugatdim, sen-chi?", "ru": "Только что закончил, а ты?", "tj": "Ҳозир тамом кардам, ту чӣ?"},
            {"speaker": "同学", "zh": "今天这些题特别难，我看不懂，不会做，你能帮我吗？", "pinyin": "Jīntiān zhèxiē tí tèbié nán, wǒ kàn bu dǒng, bú huì zuò, nǐ néng bāng wǒ ma?", "uz": "Bugungi masalalar juda qiyin, tushunmayapman, qila olmayapman, yordam bera olasanmi?", "ru": "Сегодняшние задания особенно трудные, я не понимаю и не умею делать, можешь помочь?", "tj": "Саволҳои имрӯза хеле душворанд, намефаҳмам, карда наметавонам, ёрӣ медиҳӣ?"},
            {"speaker": "儿子", "zh": "电话里讲不明白，你来我家吧，我给你讲讲。", "pinyin": "Diànhuà lǐ jiǎng bu míngbai, nǐ lái wǒ jiā ba, wǒ gěi nǐ jiǎngjiang.", "uz": "Telefonda tushuntirib bo'lmaydi, uyimga kel, senga tushuntirib beraman.", "ru": "По телефону не объяснить понятно, приходи ко мне домой, я тебе объясню.", "tj": "Дар телефон равшан фаҳмонда намешавад, ба хонаи ман биё, ба ту мефаҳмонам."},
            {"speaker": "同学", "zh": "好啊，我锻炼完了就过去。", "pinyin": "Hǎo a, wǒ duànliàn wán le jiù guòqu.", "uz": "Yaxshi, mashqni tugatib, darhol boraman.", "ru": "Хорошо, закончу тренировку и сразу приду.", "tj": "Хуб, машқро тамом карда, меоям."},
        ],
    },
    {
        "block_no": 3,
        "section_label": "课文 3",
        "scene_uz": "Dam olish xonasida",
        "scene_ru": "В комнате отдыха",
        "scene_tj": "Дар ҳуҷраи истироҳат",
        "word_nos": [11, 12, 13],
        "grammar_nos": [1],
        "dialogue": [
            {"speaker": "同事", "zh": "你怎么有点儿不高兴？", "pinyin": "Nǐ zěnme yǒudiǎnr bù gāoxìng?", "uz": "Nega biroz xafa ko'rinasan?", "ru": "Почему ты немного недоволен?", "tj": "Чаро каме нороҳатӣ?"},
            {"speaker": "小刚", "zh": "我想请小丽吃饭，但是找不到好饭馆。", "pinyin": "Wǒ xiǎng qǐng Xiǎolì chī fàn, dànshì zhǎo bu dào hǎo fànguǎnr.", "uz": "Xiaolini ovqatga taklif qilmoqchiman, lekin yaxshi restoran topa olmayapman.", "ru": "Я хочу пригласить Сяоли поесть, но не могу найти хороший ресторан.", "tj": "Мехоҳам Сяолиро ба хӯрок даъват кунам, аммо тарабхонаи хуб ёфта наметавонам."},
            {"speaker": "同事", "zh": "那你请她听音乐会吧，她喜欢听音乐。", "pinyin": "Nà nǐ qǐng tā tīng yīnyuèhuì ba, tā xǐhuan tīng yīnyuè.", "uz": "Unda uni konsertga taklif qil, u musiqa tinglashni yaxshi ko'radi.", "ru": "Тогда пригласи её на концерт, она любит слушать музыку.", "tj": "Пас ӯро ба консерт даъват кун, ӯ мусиқӣ шуниданро дӯст медорад."},
            {"speaker": "小刚", "zh": "音乐会人太多，买不到票。", "pinyin": "Yīnyuèhuì rén tài duō, mǎi bu dào piào.", "uz": "Konsertda odam juda ko'p, chipta olib bo'lmaydi.", "ru": "На концерте слишком много людей, билетов не купить.", "tj": "Дар консерт одам бисёр аст, билет харида намешавад."},
            {"speaker": "同事", "zh": "那去公园走走，聊聊天儿吧。", "pinyin": "Nà qù gōngyuán zǒuzou, liáo liáotiānr ba.", "uz": "Unda parkka borib sayr qilinglar, suhbatlashinglar.", "ru": "Тогда сходите в парк погулять и поболтать.", "tj": "Пас ба боғ рафта сайр кунед, суҳбат кунед."},
            {"speaker": "小刚", "zh": "公园太大，多累啊。", "pinyin": "Gōngyuán tài dà, duō lèi a.", "uz": "Park juda katta, juda charchatadi-ku.", "ru": "Парк слишком большой, как утомительно.", "tj": "Боғ хеле калон аст, чӣ қадар хаста мекунад."},
        ],
    },
    {
        "block_no": 4,
        "section_label": "课文 4",
        "scene_uz": "Mehmonxonada",
        "scene_ru": "В гостиной",
        "scene_tj": "Дар меҳмонхона",
        "word_nos": [14, 15],
        "grammar_nos": [1, 2],
        "dialogue": [
            {"speaker": "周太太", "zh": "你怎么还喝咖啡？", "pinyin": "Nǐ zěnme hái hē kāfēi?", "uz": "Nega yana qahva ichyapsan?", "ru": "Почему ты всё ещё пьёшь кофе?", "tj": "Чаро боз қаҳва менӯшӣ?"},
            {"speaker": "周明", "zh": "怎么了？", "pinyin": "Zěnme le?", "uz": "Nima bo'ldi?", "ru": "Что случилось?", "tj": "Чӣ шуд?"},
            {"speaker": "周太太", "zh": "你不是说晚上睡不着觉吗？", "pinyin": "Nǐ bú shì shuō wǎnshang shuì bu zháo jiào ma?", "uz": "Kechasi uxlay olmayman demaganmiding?", "ru": "Разве ты не говорил, что вечером не можешь заснуть?", "tj": "Магар нагуфта будӣ, ки шаб хобат намебарад?"},
            {"speaker": "周明", "zh": "没事，我只喝一杯。", "pinyin": "Méi shì, wǒ zhǐ hē yì bēi.", "uz": "Hechqisi yo'q, faqat bir piyola ichaman.", "ru": "Ничего, я выпью только одну чашку.", "tj": "Ҳеҷ гап не, танҳо як пиёла менӯшам."},
            {"speaker": "周太太", "zh": "你还是喝杯牛奶吧，可以睡得更好些。", "pinyin": "Nǐ háishi hē bēi niúnǎi ba, kěyǐ shuì de gèng hǎo xiē.", "uz": "Yaxshisi sut ich, yaxshiroq uxlaysan.", "ru": "Лучше выпей стакан молока, сможешь спать лучше.", "tj": "Беҳтараш як пиёла шир нӯш, беҳтар хоб мекунӣ."},
            {"speaker": "周明", "zh": "好吧，牛奶呢？", "pinyin": "Hǎo ba, niúnǎi ne?", "uz": "Mayli, sut qani?", "ru": "Ладно, а где молоко?", "tj": "Хуб, шир куҷост?"},
            {"speaker": "周太太", "zh": "还没买呢。", "pinyin": "Hái méi mǎi ne.", "uz": "Hali olganim yo'q.", "ru": "Ещё не купила.", "tj": "Ҳанӯз нахаридаам."},
        ],
    },
]


_LESSON_7_VOCABULARY = [
    {"no": 1, "zh": "同事", "pinyin": "tóngshì", "pos": "n.", "uz": "hamkasb", "ru": "коллега", "tj": "ҳамкор"},
    {"no": 2, "zh": "以前", "pinyin": "yǐqián", "pos": "n.", "uz": "oldin, ilgari", "ru": "раньше, прежде", "tj": "пештар, қаблан"},
    {"no": 3, "zh": "银行", "pinyin": "yínháng", "pos": "n.", "uz": "bank", "ru": "банк", "tj": "бонк"},
    {"no": 4, "zh": "久", "pinyin": "jiǔ", "pos": "adj.", "uz": "uzoq vaqt", "ru": "долго, длительный", "tj": "муддати дароз"},
    {"no": 5, "zh": "感兴趣", "pinyin": "gǎn xìngqù", "pos": "v.", "uz": "qiziqmoq", "ru": "интересоваться", "tj": "шавқ доштан"},
    {"no": 6, "zh": "结婚", "pinyin": "jié hūn", "pos": "v.", "uz": "turmush qurmoq, uylanmoq", "ru": "жениться, выходить замуж", "tj": "оиладор шудан"},
    {"no": 7, "zh": "欢迎", "pinyin": "huānyíng", "pos": "v.", "uz": "xush kelibsiz demoq, kutib olmoq", "ru": "приветствовать", "tj": "хуш омадед гуфтан, пешвоз гирифтан"},
    {"no": 8, "zh": "迟到", "pinyin": "chídào", "pos": "v.", "uz": "kech qolmoq", "ru": "опаздывать", "tj": "дер мондан"},
    {"no": 9, "zh": "半", "pinyin": "bàn", "pos": "num.", "uz": "yarim", "ru": "половина", "tj": "ним"},
    {"no": 10, "zh": "接", "pinyin": "jiē", "pos": "v.", "uz": "kutib olmoq, olib ketmoq", "ru": "встречать, забирать", "tj": "пешвоз гирифтан, бурдан"},
    {"no": 11, "zh": "刻", "pinyin": "kè", "pos": "m.", "uz": "chorak soat", "ru": "четверть часа", "tj": "чоряки соат"},
    {"no": 12, "zh": "差", "pinyin": "chà", "pos": "v.", "uz": "yetishmaslik, kam bo'lmoq", "ru": "не хватать, без", "tj": "кам будан"},
]


_LESSON_7_DIALOGUES = [
    {
        "block_no": 1,
        "section_label": "课文 1",
        "scene_uz": "Ofisda",
        "scene_ru": "В офисе",
        "scene_tj": "Дар идора",
        "word_nos": [1, 2, 3],
        "grammar_nos": [1],
        "dialogue": [
            {"speaker": "同事", "zh": "那个漂亮的新同事是谁？", "pinyin": "Nà ge piàoliang de xīn tóngshì shì shéi?", "uz": "Anavi chiroyli yangi hamkasb kim?", "ru": "Кто эта красивая новая коллега?", "tj": "Он ҳамкори нави зебо кист?"},
            {"speaker": "小刚", "zh": "那是小丽。", "pinyin": "Nà shì Xiǎolì.", "uz": "U Xiaoli.", "ru": "Это Сяоли.", "tj": "Ин Сяоли аст."},
            {"speaker": "同事", "zh": "她刚来北京吗？", "pinyin": "Tā gāng lái Běijīng ma?", "uz": "U Pekinga hozirgina keldimi?", "ru": "Она только что приехала в Пекин?", "tj": "Ӯ нав ба Пекин омад?"},
            {"speaker": "小刚", "zh": "不，她在北京工作三年了。", "pinyin": "Bù, tā zài Běijīng gōngzuò sān nián le.", "uz": "Yo'q, u Pekinda uch yil ishlagan.", "ru": "Нет, она уже три года работает в Пекине.", "tj": "Не, ӯ дар Пекин се сол кор кардааст."},
            {"speaker": "同事", "zh": "以前她在哪儿工作？", "pinyin": "Yǐqián tā zài nǎr gōngzuò?", "uz": "Oldin u qayerda ishlagan?", "ru": "Где она работала раньше?", "tj": "Пештар ӯ дар куҷо кор мекард?"},
            {"speaker": "小刚", "zh": "她在银行工作了两年以后来的我们公司。", "pinyin": "Tā zài yínháng gōngzuò le liǎng nián yǐhòu lái de wǒmen gōngsī.", "uz": "U bankda ikki yil ishlab, keyin bizning kompaniyaga kelgan.", "ru": "Она проработала в банке два года, потом пришла в нашу компанию.", "tj": "Ӯ дар бонк ду сол кор карда, баъд ба ширкати мо омад."},
        ],
    },
    {
        "block_no": 2,
        "section_label": "课文 2",
        "scene_uz": "Dam olish xonasida",
        "scene_ru": "В комнате отдыха",
        "scene_tj": "Дар ҳуҷраи истироҳат",
        "word_nos": [4, 5],
        "grammar_nos": [1, 2],
        "dialogue": [
            {"speaker": "同事", "zh": "周末你跟小丽去哪儿玩儿了？", "pinyin": "Zhōumò nǐ gēn Xiǎolì qù nǎr wánr le?", "uz": "Hafta oxiri Xiaoli bilan qayerga aylangani bording?", "ru": "Куда ты ходил с Сяоли на выходных?", "tj": "Охири ҳафта бо Сяоли ба куҷо рафта будӣ?"},
            {"speaker": "小刚", "zh": "我们去唱歌了。", "pinyin": "Wǒmen qù chàng gē le.", "uz": "Qo'shiq aytishga bordik.", "ru": "Мы ходили петь.", "tj": "Мо барои сурудхонӣ рафтем."},
            {"speaker": "同事", "zh": "你们唱了多久？", "pinyin": "Nǐmen chàng le duō jiǔ?", "uz": "Qancha vaqt qo'shiq aytdinglar?", "ru": "Как долго вы пели?", "tj": "Чанд вақт суруд хондед?"},
            {"speaker": "小刚", "zh": "我们唱了两个小时歌，晚上还去听音乐会了。", "pinyin": "Wǒmen chàng le liǎng ge xiǎoshí gē, wǎnshang hái qù tīng yīnyuèhuì le.", "uz": "Ikki soat qo'shiq aytdik, kechqurun yana konsertga bordik.", "ru": "Мы пели два часа, вечером ещё ходили на концерт.", "tj": "Ду соат суруд хондем, бегоҳ боз ба консерт рафтем."},
            {"speaker": "同事", "zh": "你们都对音乐感兴趣吗？", "pinyin": "Nǐmen dōu duì yīnyuè gǎn xìngqù ma?", "uz": "Ikkalangiz ham musiqaga qiziqasizmi?", "ru": "Вы оба интересуетесь музыкой?", "tj": "Ҳардуятон ба мусиқӣ шавқ доред?"},
            {"speaker": "小刚", "zh": "她对音乐感兴趣，我对她更感兴趣。", "pinyin": "Tā duì yīnyuè gǎn xìngqù, wǒ duì tā gèng gǎn xìngqù.", "uz": "U musiqaga qiziqadi, men esa unga ko'proq qiziqaman.", "ru": "Она интересуется музыкой, а я больше интересуюсь ею.", "tj": "Ӯ ба мусиқӣ шавқ дорад, ман бошад ба ӯ бештар шавқ дорам."},
        ],
    },
    {
        "block_no": 3,
        "section_label": "课文 3",
        "scene_uz": "Dam olish xonasida",
        "scene_ru": "В комнате отдыха",
        "scene_tj": "Дар ҳуҷраи истироҳат",
        "word_nos": [6, 7],
        "grammar_nos": [1],
        "dialogue": [
            {"speaker": "小刚", "zh": "我跟小丽下个月结婚，到时候欢迎你来。", "pinyin": "Wǒ gēn Xiǎolì xià ge yuè jié hūn, dào shíhou huānyíng nǐ lái.", "uz": "Men Xiaoli bilan keyingi oy turmush quraman, o'shanda kelishingdan xursand bo'lamiz.", "ru": "Мы с Сяоли в следующем месяце женимся, будем рады, если придёшь.", "tj": "Ман бо Сяоли моҳи дигар оиладор мешавам, он вақт хуш омадед."},
            {"speaker": "同事", "zh": "什么？结婚？", "pinyin": "Shénme? Jié hūn?", "uz": "Nima? Turmush qurasizlar?", "ru": "Что? Женитесь?", "tj": "Чӣ? Оиладор мешавед?"},
            {"speaker": "小刚", "zh": "对啊，突然吗？", "pinyin": "Duì a, tūrán ma?", "uz": "Ha, to'satdanmi?", "ru": "Да, неожиданно?", "tj": "Ҳа, ногаҳонӣ аст?"},
            {"speaker": "同事", "zh": "你们不是刚认识吗？", "pinyin": "Nǐmen bú shì gāng rènshi ma?", "uz": "Sizlar endigina tanishmaganmidilaring?", "ru": "Разве вы не только что познакомились?", "tj": "Магар шумо нав шинос нашуда будед?"},
            {"speaker": "小刚", "zh": "我跟她都认识五年了。", "pinyin": "Wǒ gēn tā dōu rènshi wǔ nián le.", "uz": "Men u bilan besh yildan beri tanishman.", "ru": "Мы знакомы уже пять лет.", "tj": "Ман бо ӯ панҷ сол боз шиносам."},
            {"speaker": "同事", "zh": "你跟她结婚，那我怎么办啊？", "pinyin": "Nǐ gēn tā jié hūn, nà wǒ zěnme bàn a?", "uz": "Sen u bilan turmush qursang, men nima qilaman?", "ru": "Если ты женишься на ней, что мне делать?", "tj": "Агар ту бо ӯ оиладор шавӣ, ман чӣ кор мекунам?"},
        ],
    },
    {
        "block_no": 4,
        "section_label": "课文 4",
        "scene_uz": "Kompaniya binosi eshigida",
        "scene_ru": "У выхода из здания компании",
        "scene_tj": "Дар баромади бинои ширкат",
        "word_nos": [8, 9, 10, 11, 12],
        "grammar_nos": [1, 3],
        "dialogue": [
            {"speaker": "小丽", "zh": "你看看手表，怎么迟到了？", "pinyin": "Nǐ kànkan shǒubiǎo, zěnme chídào le?", "uz": "Soatingga qara, nega kech qolding?", "ru": "Посмотри на часы, почему опоздал?", "tj": "Ба соатат нигоҳ кун, чаро дер мондӣ?"},
            {"speaker": "小刚", "zh": "没迟到啊。", "pinyin": "Méi chídào a.", "uz": "Kech qolmadim-ku.", "ru": "Я не опоздал.", "tj": "Ман дер намондам."},
            {"speaker": "小丽", "zh": "你不是说七点半来接我吗？你迟到了一刻钟。", "pinyin": "Nǐ bú shì shuō qī diǎn bàn lái jiē wǒ ma? Nǐ chídào le yí kè zhōng.", "uz": "Soat yetti yarimda meni olib ketaman demaganmiding? Sen chorak soat kech qolding.", "ru": "Разве ты не говорил, что заберёшь меня в 7:30? Ты опоздал на четверть часа.", "tj": "Магар нагуфта будӣ, ки соати ҳафту ним маро мебарӣ? Ту чоряк соат дер мондӣ."},
            {"speaker": "小刚", "zh": "现在不是七点半吗？", "pinyin": "Xiànzài bú shì qī diǎn bàn ma?", "uz": "Hozir yetti yarim emasmi?", "ru": "Разве сейчас не 7:30?", "tj": "Ҳоло ҳафту ним нест?"},
            {"speaker": "小丽", "zh": "已经差一刻八点了！我都在这儿坐了半个小时了。", "pinyin": "Yǐjīng chà yí kè bā diǎn le! Wǒ dōu zài zhèr zuò le bàn ge xiǎoshí le.", "uz": "Allaqachon sakkizga chorak qoldi! Men bu yerda yarim soat o'tiribman.", "ru": "Уже без четверти восемь! Я тут уже полчаса сижу.", "tj": "Аллакай чоряк ба ҳашт мондааст! Ман ин ҷо ним соат нишастаам."},
            {"speaker": "小刚", "zh": "不是我迟到了，是你的表快了一刻钟。", "pinyin": "Bú shì wǒ chídào le, shì nǐ de biǎo kuài le yí kè zhōng.", "uz": "Men kech qolmadim, sening soating chorak soat oldinda.", "ru": "Это не я опоздал, это твои часы спешат на четверть часа.", "tj": "Ман дер намондаам, соати ту чоряк соат пеш аст."},
        ],
    },
]


_LESSON_8_VOCABULARY = [
    {"no": 1, "zh": "又", "pinyin": "yòu", "pos": "adv.", "uz": "yana (amal allaqachon takrorlangan)", "ru": "снова (действие уже повторилось)", "tj": "боз (амал аллакай такрор шуд)"},
    {"no": 2, "zh": "满意", "pinyin": "mǎnyì", "pos": "v.", "uz": "mamnun bo'lmoq, qoniqmoq", "ru": "быть довольным", "tj": "қаноатманд будан"},
    {"no": 3, "zh": "电梯", "pinyin": "diàntī", "pos": "n.", "uz": "lift", "ru": "лифт", "tj": "лифт"},
    {"no": 4, "zh": "层", "pinyin": "céng", "pos": "m.", "uz": "qavatlar uchun hisob so'zi", "ru": "счётное слово для этажей", "tj": "ҳисобвожа барои ошёна"},
    {"no": 5, "zh": "害怕", "pinyin": "hàipà", "pos": "v.", "uz": "qo'rqmoq", "ru": "бояться", "tj": "тарсидан"},
    {"no": 6, "zh": "熊猫", "pinyin": "xióngmāo", "pos": "n.", "uz": "panda", "ru": "панда", "tj": "панда"},
    {"no": 7, "zh": "见面", "pinyin": "jiàn miàn", "pos": "v.", "uz": "uchrashmoq", "ru": "встречаться", "tj": "вохӯрдан"},
    {"no": 8, "zh": "安静", "pinyin": "ānjìng", "pos": "adj.", "uz": "tinch, sokin", "ru": "тихий, спокойный", "tj": "ором, сокит"},
    {"no": 9, "zh": "可乐", "pinyin": "kělè", "pos": "n.", "uz": "kola", "ru": "кола", "tj": "кола"},
    {"no": 10, "zh": "一会儿", "pinyin": "yíhuìr", "pos": "n.", "uz": "bir oz vaqt", "ru": "немного времени, момент", "tj": "як лаҳза, каме вақт"},
    {"no": 11, "zh": "马上", "pinyin": "mǎshàng", "pos": "adv.", "uz": "darhol", "ru": "сразу, немедленно", "tj": "фавран"},
    {"no": 12, "zh": "洗手间", "pinyin": "xǐshǒujiān", "pos": "n.", "uz": "hojatxona", "ru": "туалет", "tj": "ҳоҷатхона"},
    {"no": 13, "zh": "老", "pinyin": "lǎo", "pos": "adj.", "uz": "eski, keksa", "ru": "старый", "tj": "пир, кӯҳна"},
    {"no": 14, "zh": "几乎", "pinyin": "jīhū", "pos": "adv.", "uz": "deyarli", "ru": "почти", "tj": "қариб"},
    {"no": 15, "zh": "变化", "pinyin": "biànhuà", "pos": "v.", "uz": "o'zgarmoq; o'zgarish", "ru": "изменяться; изменение", "tj": "тағйир ёфтан; тағйирот"},
    {"no": 16, "zh": "健康", "pinyin": "jiànkāng", "pos": "adj.", "uz": "sog'lom", "ru": "здоровый", "tj": "солим"},
    {"no": 17, "zh": "重要", "pinyin": "zhòngyào", "pos": "adj.", "uz": "muhim", "ru": "важный", "tj": "муҳим"},
]


_LESSON_8_DIALOGUES = [
    {
        "block_no": 1,
        "section_label": "课文 1",
        "scene_uz": "Dam olish xonasida",
        "scene_ru": "В комнате отдыха",
        "scene_tj": "Дар ҳуҷраи истироҳат",
        "word_nos": [1, 2, 3, 4, 5],
        "grammar_nos": [1],
        "dialogue": [
            {"speaker": "同事", "zh": "听说你最近打算买房子？", "pinyin": "Tīngshuō nǐ zuìjìn dǎsuàn mǎi fángzi?", "uz": "Eshitishimcha, oxirgi paytda uy olmoqchisan?", "ru": "Слышал, ты в последнее время собираешься купить квартиру?", "tj": "Шунидам, ки вақтҳои охир хона хариданӣ ҳастӣ?"},
            {"speaker": "小丽", "zh": "是，昨天去看了看，今天又去看了看，明天还要再去看看。", "pinyin": "Shì, zuótiān qù kànle kàn, jīntiān yòu qù kànle kàn, míngtiān hái yào zài qù kànkan.", "uz": "Ha, kecha borib ko'rdim, bugun yana borib ko'rdim, ertaga ham yana borib ko'raman.", "ru": "Да, вчера ходила посмотреть, сегодня снова ходила, завтра ещё раз пойду.", "tj": "Ҳа, дирӯз рафта дидам, имрӯз боз рафта дидам, пагоҳ ҳам боз меравам."},
            {"speaker": "同事", "zh": "都不满意吗？", "pinyin": "Dōu bù mǎnyì ma?", "uz": "Hech biridan mamnun emasmisan?", "ru": "Всеми недовольна?", "tj": "Аз ҳеҷ кадом қаноатманд нестӣ?"},
            {"speaker": "小丽", "zh": "一个没有电梯，不方便。一个有电梯，但是在二十层。", "pinyin": "Yí ge méiyǒu diàntī, bù fāngbiàn. Yí ge yǒu diàntī, dànshì zài èrshí céng.", "uz": "Bittasida lift yo'q, qulay emas. Bittasida lift bor, lekin yigirmanchi qavatda.", "ru": "В одном нет лифта, неудобно. В другом лифт есть, но он на двадцатом этаже.", "tj": "Яке лифт надорад, қулай нест. Яке лифт дорад, аммо дар ошёнаи бистум аст."},
            {"speaker": "同事", "zh": "二十层怎么了？", "pinyin": "Èrshí céng zěnme le?", "uz": "Yigirmanchi qavatga nima bo'pti?", "ru": "А что с двадцатым этажом?", "tj": "Ошёнаи бистум чӣ шудааст?"},
            {"speaker": "小丽", "zh": "太高了，往下看多害怕啊！", "pinyin": "Tài gāo le, wǎng xià kàn duō hàipà a!", "uz": "Juda baland, pastga qarash juda qo'rqinchli!", "ru": "Слишком высоко, вниз смотреть так страшно!", "tj": "Хеле баланд аст, ба поён нигоҳ кардан чӣ қадар тарснок!"},
        ],
    },
    {
        "block_no": 2,
        "section_label": "课文 2",
        "scene_uz": "Maktabda",
        "scene_ru": "В школе",
        "scene_tj": "Дар мактаб",
        "word_nos": [6, 7],
        "grammar_nos": [1],
        "dialogue": [
            {"speaker": "小明", "zh": "听说你下个星期就要回国了？", "pinyin": "Tīngshuō nǐ xià ge xīngqī jiù yào huí guó le?", "uz": "Eshitishimcha, keyingi hafta vataningga qaytasanmi?", "ru": "Слышал, на следующей неделе ты уже возвращаешься на родину?", "tj": "Шунидам, ҳафтаи дигар ба ватан бармегардӣ?"},
            {"speaker": "马可", "zh": "是啊，真不想离开北京。", "pinyin": "Shì a, zhēn bù xiǎng líkāi Běijīng.", "uz": "Ha, Pekinni tark etgim kelmayapti.", "ru": "Да, совсем не хочется покидать Пекин.", "tj": "Ҳа, аслан намехоҳам Пекинро тарк кунам."},
            {"speaker": "小明", "zh": "我下星期不在北京，不能去机场送你了。", "pinyin": "Wǒ xià xīngqī bú zài Běijīng, bù néng qù jīchǎng sòng nǐ le.", "uz": "Keyingi hafta Pekinda bo'lmayman, aeroportga kuzatgani bora olmayman.", "ru": "На следующей неделе меня не будет в Пекине, я не смогу проводить тебя в аэропорт.", "tj": "Ҳафтаи дигар дар Пекин нестам, ба фурудгоҳ гусел карда наметавонам."},
            {"speaker": "马可", "zh": "没关系，你忙吧。", "pinyin": "Méi guānxi, nǐ máng ba.", "uz": "Hechqisi yo'q, ishing bilan bo'laver.", "ru": "Ничего, занимайся своими делами.", "tj": "Ҳеҷ гап не, ба корат машғул шав."},
            {"speaker": "小明", "zh": "这个小熊猫送给你，欢迎你以后再到中国来。", "pinyin": "Zhè ge xiǎo xióngmāo sòng gěi nǐ, huānyíng nǐ yǐhòu zài dào Zhōngguó lái.", "uz": "Bu kichkina pandani senga sovg'a qilaman, kelajakda yana Xitoyga kelishingni kutamiz.", "ru": "Дарю тебе эту маленькую панду, будем рады, если потом снова приедешь в Китай.", "tj": "Ин пандаи хурдро ба ту тӯҳфа мекунам, хуш меоем, ки баъд боз ба Чин биёӣ."},
            {"speaker": "马可", "zh": "谢谢。希望以后能再见面。", "pinyin": "Xièxie. Xīwàng yǐhòu néng zài jiàn miàn.", "uz": "Rahmat. Kelajakda yana uchrashamiz degan umiddaman.", "ru": "Спасибо. Надеюсь, в будущем сможем снова встретиться.", "tj": "Ташаккур. Умедворам, ки баъд боз вохӯрем."},
        ],
    },
    {
        "block_no": 3,
        "section_label": "课文 3",
        "scene_uz": "Qahvaxonada",
        "scene_ru": "В кафе",
        "scene_tj": "Дар қаҳвахона",
        "word_nos": [8, 9, 10, 11, 12],
        "grammar_nos": [2, 3],
        "dialogue": [
            {"speaker": "小丽", "zh": "小刚，我们坐哪儿？", "pinyin": "Xiǎogāng, wǒmen zuò nǎr?", "uz": "Xiaogang, qayerga o'tiramiz?", "ru": "Сяоган, где сядем?", "tj": "Сяогang, куҷо менишинем?"},
            {"speaker": "小刚", "zh": "你坐哪儿我就坐哪儿。", "pinyin": "Nǐ zuò nǎr wǒ jiù zuò nǎr.", "uz": "Sen qayerga o'tirsang, men ham o'sha yerga o'tiraman.", "ru": "Где ты сядешь, там и я сяду.", "tj": "Ту куҷо нишинӣ, ман ҳам ҳамон ҷо мешинам."},
            {"speaker": "小丽", "zh": "坐这儿吧，这儿安静。你想喝什么饮料？", "pinyin": "Zuò zhèr ba, zhèr ānjìng. Nǐ xiǎng hē shénme yǐnliào?", "uz": "Shu yerga o'tiraylik, bu yer tinch. Qanday ichimlik ichmoqchisan?", "ru": "Сядем здесь, тут тихо. Что хочешь выпить?", "tj": "Ин ҷо менишинем, ин ҷо ором аст. Чӣ нӯшидан мехоҳӣ?"},
            {"speaker": "小刚", "zh": "你喝什么我就喝什么。", "pinyin": "Nǐ hē shénme wǒ jiù hē shénme.", "uz": "Sen nima ichsang, men ham shuni ichaman.", "ru": "Что ты выпьешь, то и я выпью.", "tj": "Ту чӣ нӯшӣ, ман ҳам ҳамонро менӯшам."},
            {"speaker": "小丽", "zh": "喝可乐吧。你等我一会儿，我马上回来。", "pinyin": "Hē kělè ba. Nǐ děng wǒ yíhuìr, wǒ mǎshàng huílai.", "uz": "Kola ichaylik. Meni biroz kut, darhol qaytaman.", "ru": "Давай колу. Подожди меня немного, я сразу вернусь.", "tj": "Кола менӯшем. Маро каме интизор шав, фавран бармегардам."},
            {"speaker": "小刚", "zh": "小丽，你去哪儿？你去哪儿我就去哪儿。", "pinyin": "Xiǎolì, nǐ qù nǎr? Nǐ qù nǎr wǒ jiù qù nǎr.", "uz": "Xiaoli, qayerga ketyapsan? Sen qayerga borsang, men ham boraman.", "ru": "Сяоли, куда ты? Куда ты, туда и я.", "tj": "Сяоли, ба куҷо меравӣ? Ту ба куҷо равӣ, ман ҳам меравам."},
            {"speaker": "小丽", "zh": "我去洗手间。", "pinyin": "Wǒ qù xǐshǒujiān.", "uz": "Hojatxonaga boraman.", "ru": "Я иду в туалет.", "tj": "Ба ҳоҷатхона меравам."},
        ],
    },
    {
        "block_no": 4,
        "section_label": "课文 4",
        "scene_uz": "Zhou Mingning uyida",
        "scene_ru": "У Чжоу Мина дома",
        "scene_tj": "Дар хонаи Чжоу Мин",
        "word_nos": [13, 14, 15, 16, 17],
        "grammar_nos": [2, 3],
        "dialogue": [
            {"speaker": "老同学", "zh": "快五年了，你几乎没变化。", "pinyin": "Kuài wǔ nián le, nǐ jīhū méi biànhuà.", "uz": "Deyarli besh yil bo'ldi, sen deyarli o'zgarmabsan.", "ru": "Почти пять лет прошло, ты почти не изменилась.", "tj": "Қариб панҷ сол шуд, ту қариб тағйир наёфтаӣ."},
            {"speaker": "周太太", "zh": "谁说的？我胖了，以前的衣服都不能穿了。", "pinyin": "Shéi shuō de? Wǒ pàng le, yǐqián de yīfu dōu bù néng chuān le.", "uz": "Kim aytdi? Men semirdim, oldingi kiyimlarimni kiya olmay qoldim.", "ru": "Кто сказал? Я поправилась, прежнюю одежду уже не могу носить.", "tj": "Кӣ гуфт? Ман фарбеҳ шудам, либосҳои пештараро дигар пӯшида наметавонам."},
            {"speaker": "老同学", "zh": "健康最重要，胖瘦没关系。", "pinyin": "Jiànkāng zuì zhòngyào, pàng shòu méi guānxi.", "uz": "Sog'liq eng muhim, semizlik yoki ozg'inlik muhim emas.", "ru": "Здоровье важнее всего, полнота или худоба не имеют значения.", "tj": "Саломатӣ аз ҳама муҳим аст, фарбеҳӣ ё лоғарӣ муҳим нест."},
            {"speaker": "周太太", "zh": "是呀，想吃什么就吃什么。", "pinyin": "Shì ya, xiǎng chī shénme jiù chī shénme.", "uz": "Ha-da, nima yegim kelsa, shuni yeyman.", "ru": "Да, что хочется есть, то и ем.", "tj": "Ҳа, чӣ хӯрдан хоҳам, ҳамонро мехӯрам."},
            {"speaker": "老同学", "zh": "你做饭还是周明做饭？", "pinyin": "Nǐ zuò fàn háishi Zhōu Míng zuò fàn?", "uz": "Ovqatni sen pishirasanmi yoki Zhou Mingmi?", "ru": "Ты готовишь или Чжоу Мин?", "tj": "Ту хӯрок мепазӣ ё Чжоу Мин?"},
            {"speaker": "周太太", "zh": "我做，我想吃什么就做什么，想吃多少就做多少。", "pinyin": "Wǒ zuò, wǒ xiǎng chī shénme jiù zuò shénme, xiǎng chī duōshao jiù zuò duōshao.", "uz": "Men pishiraman, nima yegim kelsa shuni pishiraman, qancha yegim kelsa shuncha pishiraman.", "ru": "Я готовлю: что хочу есть, то и готовлю, сколько хочу есть, столько и готовлю.", "tj": "Ман мепазам: чӣ хӯрдан хоҳам ҳамонро мепазам, чӣ қадар хоҳам ҳамон қадар мепазам."},
        ],
    },
]


_LESSON_9_VOCABULARY = [
    {"no": 1, "zh": "中文", "pinyin": "Zhōngwén", "pos": "n.", "uz": "xitoy tili", "ru": "китайский язык", "tj": "забони чинӣ"},
    {"no": 2, "zh": "班", "pinyin": "bān", "pos": "n.", "uz": "sinf, guruh", "ru": "класс, группа", "tj": "синф, гурӯҳ"},
    {"no": 3, "zh": "一样", "pinyin": "yíyàng", "pos": "adj.", "uz": "bir xil, xuddi ... kabi", "ru": "одинаковый, такой же", "tj": "якхела, мисли"},
    {"no": 4, "zh": "最后", "pinyin": "zuìhòu", "pos": "n.", "uz": "oxirgi, so'nggi", "ru": "последний", "tj": "охирин"},
    {"no": 5, "zh": "放心", "pinyin": "fàngxīn", "pos": "v.", "uz": "xotirjam bo'lmoq", "ru": "успокоиться, не беспокоиться", "tj": "хотирҷамъ шудан"},
    {"no": 6, "zh": "一定", "pinyin": "yídìng", "pos": "adv.", "uz": "albatta, aniq", "ru": "обязательно, непременно", "tj": "албатта, ҳатман"},
    {"no": 7, "zh": "担心", "pinyin": "dān xīn", "pos": "v.", "uz": "xavotir olmoq", "ru": "беспокоиться", "tj": "нигарон шудан"},
    {"no": 8, "zh": "比较", "pinyin": "bǐjiào", "pos": "adv.", "uz": "nisbatan, ancha", "ru": "сравнительно, довольно", "tj": "нисбатан"},
    {"no": 9, "zh": "了解", "pinyin": "liǎojiě", "pos": "v.", "uz": "bilmoq, tushunmoq", "ru": "понимать, знать", "tj": "фаҳмидан, донистан"},
    {"no": 10, "zh": "先", "pinyin": "xiān", "pos": "adv.", "uz": "avval, oldin", "ru": "сначала, заранее", "tj": "аввал"},
    {"no": 11, "zh": "中间", "pinyin": "zhōngjiān", "pos": "n.", "uz": "o'rta, orasida", "ru": "середина, посередине", "tj": "миёна"},
    {"no": 12, "zh": "参加", "pinyin": "cānjiā", "pos": "v.", "uz": "qatnashmoq, ishtirok etmoq", "ru": "участвовать", "tj": "иштирок кардан"},
    {"no": 13, "zh": "影响", "pinyin": "yǐngxiǎng", "pos": "n./v.", "uz": "ta'sir; ta'sir qilmoq", "ru": "влияние; влиять", "tj": "таъсир; таъсир кардан"},
    {"no": 14, "zh": "大山", "pinyin": "Dàshān", "pos": "proper noun", "uz": "Dashan (ism)", "ru": "Дашань (имя)", "tj": "Дашан (ном)"},
    {"no": 15, "zh": "李静", "pinyin": "Lǐ Jìng", "pos": "proper noun", "uz": "Li Jing (ism)", "ru": "Ли Цзин (имя)", "tj": "Ли Ҷинг (ном)"},
]


_LESSON_9_DIALOGUES = [
    {
        "block_no": 1,
        "section_label": "课文 1",
        "scene_uz": "Sinfda",
        "scene_ru": "В классе",
        "scene_tj": "Дар синф",
        "word_nos": [1, 2, 3, 14, 15],
        "grammar_nos": [1, 2],
        "dialogue": [
            {"speaker": "大山", "zh": "马可，你的中文越说越好了！", "pinyin": "Mǎkě, nǐ de Zhōngwén yuè shuō yuè hǎo le!", "uz": "Make, xitoychang tobora yaxshilanib boryapti!", "ru": "Марк, ты говоришь по-китайски всё лучше!", "tj": "Маке, забони чиниат торафт беҳтар мешавад!"},
            {"speaker": "马可", "zh": "哪里哪里，我们班李静说得更好。", "pinyin": "Nǎli nǎli, wǒmen bān Lǐ Jìng shuō de gèng hǎo.", "uz": "Yo'g'e, bizning sinfdagi Li Jing yanada yaxshiroq gapiradi.", "ru": "Да что ты, Ли Цзин из нашего класса говорит ещё лучше.", "tj": "Не, Ли Ҷинг аз синфи мо боз беҳтар ҳарф мезанад."},
            {"speaker": "大山", "zh": "怎么好？", "pinyin": "Zěnme hǎo?", "uz": "Qanchalik yaxshi?", "ru": "Насколько хорошо?", "tj": "Чӣ гуна хуб?"},
            {"speaker": "马可", "zh": "她的汉语说得跟中国人一样好。", "pinyin": "Tā de Hànyǔ shuō de gēn Zhōngguórén yíyàng hǎo.", "uz": "U xitoychani xitoyliklar kabi yaxshi gapiradi.", "ru": "Она говорит по-китайски так же хорошо, как китайцы.", "tj": "Ӯ забони чиниро мисли чиниҳо хуб ҳарф мезанад."},
            {"speaker": "大山", "zh": "李静？我怎么没听说过这个名字？", "pinyin": "Lǐ Jìng? Wǒ zěnme méi tīngshuō guo zhè ge míngzi?", "uz": "Li Jing? Nega bu ismni eshitmaganman?", "ru": "Ли Цзин? Почему я не слышал это имя?", "tj": "Ли Ҷинг? Чаро ин номро нашунидаам?"},
            {"speaker": "马可", "zh": "她是我们的汉语老师。", "pinyin": "Tā shì wǒmen de Hànyǔ lǎoshī.", "uz": "U bizning xitoy tili o'qituvchimiz.", "ru": "Она наша учительница китайского.", "tj": "Ӯ омӯзгори забони чинии мост."},
        ],
    },
    {
        "block_no": 2,
        "section_label": "课文 2",
        "scene_uz": "Tort do'konida",
        "scene_ru": "В кондитерской",
        "scene_tj": "Дар мағозаи торт",
        "word_nos": [4, 5, 6],
        "grammar_nos": [1],
        "dialogue": [
            {"speaker": "小丽", "zh": "别吃了，你已经吃了三块蛋糕了。", "pinyin": "Bié chī le, nǐ yǐjīng chī le sān kuài dàngāo le.", "uz": "Yema endi, allaqachon uch bo'lak tort yeding.", "ru": "Не ешь больше, ты уже съел три куска торта.", "tj": "Дигар нахӯр, аллакай се порча торт хӯрдӣ."},
            {"speaker": "小刚", "zh": "这是最后一块。", "pinyin": "Zhè shì zuìhòu yí kuài.", "uz": "Bu oxirgi bo'lak.", "ru": "Это последний кусок.", "tj": "Ин охирин порча аст."},
            {"speaker": "小丽", "zh": "你总是吃甜的东西，会越吃越胖。", "pinyin": "Nǐ zǒngshì chī tián de dōngxi, huì yuè chī yuè pàng.", "uz": "Sen doim shirin narsa yeysan, yegan sari semirasan.", "ru": "Ты всё время ешь сладкое, будешь толстеть всё больше.", "tj": "Ту ҳамеша ширинӣ мехӯрӣ, ҳар қадар хӯрӣ, ҳамон қадар фарбеҳ мешавӣ."},
            {"speaker": "小刚", "zh": "你放心，我一定不会变胖。", "pinyin": "Nǐ fàngxīn, wǒ yídìng bú huì biàn pàng.", "uz": "Xotirjam bo'l, men albatta semirmayman.", "ru": "Не волнуйся, я точно не потолстею.", "tj": "Хотирҷамъ бош, ман ҳатман фарбеҳ намешавам."},
            {"speaker": "小丽", "zh": "为什么？", "pinyin": "Wèi shénme?", "uz": "Nega?", "ru": "Почему?", "tj": "Чаро?"},
            {"speaker": "小刚", "zh": "我们家的人都很瘦，吃不胖。", "pinyin": "Wǒmen jiā de rén dōu hěn shòu, chī bu pàng.", "uz": "Bizning uydagilar hammasi ozg'in, yesayam semirmaydi.", "ru": "У нас в семье все худые, сколько ни едят, не толстеют.", "tj": "Дар хонаи мо ҳама лоғаранд, хӯранд ҳам фарбеҳ намешаванд."},
        ],
    },
    {
        "block_no": 3,
        "section_label": "课文 3",
        "scene_uz": "Tog'da",
        "scene_ru": "На горе",
        "scene_tj": "Дар кӯҳ",
        "word_nos": [7, 8, 9, 10, 11],
        "grammar_nos": [1],
        "dialogue": [
            {"speaker": "小丽", "zh": "我有点儿害怕。", "pinyin": "Wǒ yǒudiǎnr hàipà.", "uz": "Biroz qo'rqyapman.", "ru": "Мне немного страшно.", "tj": "Каме метарсам."},
            {"speaker": "小刚", "zh": "怎么了？", "pinyin": "Zěnme le?", "uz": "Nima bo'ldi?", "ru": "Что случилось?", "tj": "Чӣ шуд?"},
            {"speaker": "小丽", "zh": "山越高，路越难走。我也越爬越冷。", "pinyin": "Shān yuè gāo, lù yuè nán zǒu. Wǒ yě yuè pá yuè lěng.", "uz": "Tog' balandlashgan sari yo'l yurish qiyinlashyapti. Ko'tarilganim sari sovqotyapman.", "ru": "Чем выше гора, тем труднее идти. Чем больше поднимаюсь, тем холоднее.", "tj": "Ҳар қадар кӯҳ баланд бошад, роҳ ҳамон қадар душвор мешавад. Ҳар қадар боло равам, ҳамон қадар хунук мешавад."},
            {"speaker": "小刚", "zh": "不用担心，有我呢，我对这儿比较了解。", "pinyin": "Búyòng dānxīn, yǒu wǒ ne, wǒ duì zhèr bǐjiào liǎojiě.", "uz": "Xavotir olma, men borman, bu yerni nisbatan yaxshi bilaman.", "ru": "Не волнуйся, я здесь, я довольно хорошо знаю это место.", "tj": "Нигарон нашав, ман ҳастам, ин ҷоро нисбатан хуб медонам."},
            {"speaker": "小丽", "zh": "那我们先休息一下，一会儿再爬。", "pinyin": "Nà wǒmen xiān xiūxi yíxià, yíhuìr zài pá.", "uz": "Unda avval bir oz dam olaylik, keyin yana chiqamiz.", "ru": "Тогда сначала отдохнём немного, потом продолжим подниматься.", "tj": "Пас аввал каме истироҳат кунем, баъд боз мебароем."},
            {"speaker": "小刚", "zh": "好，一会儿我们可以从中间这条路上去。", "pinyin": "Hǎo, yíhuìr wǒmen kěyǐ cóng zhōngjiān zhè tiáo lù shàngqu.", "uz": "Yaxshi, keyin o'rtadagi shu yo'ldan chiqishimiz mumkin.", "ru": "Хорошо, потом можем подняться по этой средней дороге.", "tj": "Хуб, баъд метавонем аз ҳамин роҳи миёна боло равем."},
        ],
    },
    {
        "block_no": 4,
        "section_label": "课文 4",
        "scene_uz": "Xiaomingning uyida",
        "scene_ru": "У Сяомина дома",
        "scene_tj": "Дар хонаи Сяоминг",
        "word_nos": [12, 13],
        "grammar_nos": [1, 2],
        "dialogue": [
            {"speaker": "同学", "zh": "小明，你的眼睛怎么跟大熊猫一样了？", "pinyin": "Xiǎomíng, nǐ de yǎnjing zěnme gēn dà xióngmāo yíyàng le?", "uz": "Xiaoming, ko'zlaring nega katta pandanikiga o'xshab qolgan?", "ru": "Сяомин, почему твои глаза стали как у большой панды?", "tj": "Сяоминг, чаро чашмонат мисли пандаи калон шудаанд?"},
            {"speaker": "小明", "zh": "我这几天脚疼，没休息好。", "pinyin": "Wǒ zhè jǐ tiān jiǎo téng, méi xiūxi hǎo.", "uz": "Shu kunlarda oyog'im og'riyapti, yaxshi dam ololmadim.", "ru": "В эти дни у меня болят ноги, я плохо отдыхал.", "tj": "Ин чанд рӯз поям дард мекунад, хуб истироҳат накардам."},
            {"speaker": "同学", "zh": "去医院了吗？医生说什么？", "pinyin": "Qù yīyuàn le ma? Yīshēng shuō shénme?", "uz": "Kasalxonaga bordingmi? Shifokor nima dedi?", "ru": "Ходил в больницу? Что сказал врач?", "tj": "Ба беморхона рафтӣ? Духтур чӣ гуфт?"},
            {"speaker": "小明", "zh": "他让我多休息。休息得越多，好得越快。", "pinyin": "Tā ràng wǒ duō xiūxi. Xiūxi de yuè duō, hǎo de yuè kuài.", "uz": "U menga ko'proq dam olishni aytdi. Qancha ko'p dam olsam, shuncha tez tuzalaman.", "ru": "Он сказал мне больше отдыхать. Чем больше отдыхаю, тем быстрее поправляюсь.", "tj": "Ӯ гуфт, ки бештар истироҳат кунам. Ҳар қадар бештар истироҳат кунам, ҳамон қадар зудтар хуб мешавам."},
            {"speaker": "同学", "zh": "下个月的篮球比赛，你能参加吗？", "pinyin": "Xià ge yuè de lánqiú bǐsài, nǐ néng cānjiā ma?", "uz": "Keyingi oydagi basketbol musobaqasida qatnasha olasanmi?", "ru": "Сможешь участвовать в баскетбольном матче в следующем месяце?", "tj": "Дар мусобиқаи баскетболи моҳи дигар иштирок карда метавонӣ?"},
            {"speaker": "小明", "zh": "一定能参加，一点儿影响也没有。", "pinyin": "Yídìng néng cānjiā, yìdiǎnr yǐngxiǎng yě méiyǒu.", "uz": "Albatta qatnashaman, hech qanday ta'siri yo'q.", "ru": "Обязательно смогу участвовать, совсем не повлияет.", "tj": "Албатта иштирок карда метавонам, ҳеҷ таъсире надорад."},
        ],
    },
]


_LESSON_10_VOCABULARY = [
    {"no": 1, "zh": "个子", "pinyin": "gèzi", "pos": "n.", "uz": "bo'y, gavda balandligi", "ru": "рост", "tj": "қад"},
    {"no": 2, "zh": "矮", "pinyin": "ǎi", "pos": "adj.", "uz": "past bo'yli", "ru": "низкий, невысокий", "tj": "пастқад"},
    {"no": 3, "zh": "历史", "pinyin": "lìshǐ", "pos": "n.", "uz": "tarix", "ru": "история", "tj": "таърих"},
    {"no": 4, "zh": "体育", "pinyin": "tǐyù", "pos": "n.", "uz": "jismoniy tarbiya", "ru": "физкультура, спорт", "tj": "тарбияи ҷисмонӣ"},
    {"no": 5, "zh": "数学", "pinyin": "shùxué", "pos": "n.", "uz": "matematika", "ru": "математика", "tj": "математика"},
    {"no": 6, "zh": "方便", "pinyin": "fāngbiàn", "pos": "adj.", "uz": "qulay", "ru": "удобный", "tj": "қулай"},
    {"no": 7, "zh": "自行车", "pinyin": "zìxíngchē", "pos": "n.", "uz": "velosiped", "ru": "велосипед", "tj": "дучарха"},
    {"no": 8, "zh": "骑", "pinyin": "qí", "pos": "v.", "uz": "minmoq", "ru": "ехать верхом, ездить", "tj": "савор шудан"},
    {"no": 9, "zh": "旧", "pinyin": "jiù", "pos": "adj.", "uz": "eski", "ru": "старый, бывший в употреблении", "tj": "кӯҳна"},
    {"no": 10, "zh": "换", "pinyin": "huàn", "pos": "v.", "uz": "almashtirmoq", "ru": "менять, заменять", "tj": "иваз кардан"},
    {"no": 11, "zh": "地方", "pinyin": "dìfang", "pos": "n.", "uz": "joy", "ru": "место", "tj": "ҷой"},
    {"no": 12, "zh": "中介", "pinyin": "zhōngjiè", "pos": "n.", "uz": "vositachi, agent", "ru": "посредник, агент", "tj": "миёнарав, агент"},
    {"no": 13, "zh": "主要", "pinyin": "zhǔyào", "pos": "adj.", "uz": "asosiy, muhim", "ru": "главный, основной", "tj": "асосӣ"},
    {"no": 14, "zh": "环境", "pinyin": "huánjìng", "pos": "n.", "uz": "muhit, atrof-muhit", "ru": "среда, окружение", "tj": "муҳит"},
    {"no": 15, "zh": "附近", "pinyin": "fùjìn", "pos": "n.", "uz": "yaqin atrof", "ru": "поблизости, окрестности", "tj": "наздикӣ"},
]


_LESSON_10_DIALOGUES = [
    {
        "block_no": 1,
        "section_label": "课文 1",
        "scene_uz": "Sinfda",
        "scene_ru": "В классе",
        "scene_tj": "Дар синф",
        "word_nos": [1, 2],
        "grammar_nos": [1],
        "dialogue": [
            {"speaker": "朋友", "zh": "大山，你和马可谁个子高？", "pinyin": "Dàshān, nǐ hé Mǎkě shéi gèzi gāo?", "uz": "Dashan, sen bilan Make, kimning bo'yi balandroq?", "ru": "Дашань, кто выше ростом, ты или Марк?", "tj": "Дашан, ту ё Маке, қади кӣ баландтар аст?"},
            {"speaker": "大山", "zh": "马可比我高，我比马可矮一点儿。", "pinyin": "Mǎkě bǐ wǒ gāo, wǒ bǐ Mǎkě ǎi yìdiǎnr.", "uz": "Make mendan baland, men Makedan biroz pastroqman.", "ru": "Марк выше меня, я немного ниже Марка.", "tj": "Маке аз ман баландтар аст, ман аз Маке каме пасттарам."},
            {"speaker": "朋友", "zh": "那你们谁大？", "pinyin": "Nà nǐmen shéi dà?", "uz": "Unda sizlardan kim kattaroq?", "ru": "Тогда кто из вас старше?", "tj": "Пас кадоматон калонтар аст?"},
            {"speaker": "大山", "zh": "我比马可大两岁。", "pinyin": "Wǒ bǐ Mǎkě dà liǎng suì.", "uz": "Men Makedan ikki yosh kattaman.", "ru": "Я старше Марка на два года.", "tj": "Ман аз Маке ду сол калонтарам."},
            {"speaker": "朋友", "zh": "你们谁的汉语说得更好？", "pinyin": "Nǐmen shéi de Hànyǔ shuō de gèng hǎo?", "uz": "Sizlardan kim xitoychani yaxshiroq gapiradi?", "ru": "Кто из вас лучше говорит по-китайски?", "tj": "Кадоматон забони чиниро беҳтар ҳарф мезанед?"},
            {"speaker": "大山", "zh": "马可比我说得好一些，我的汉语没有他好。", "pinyin": "Mǎkě bǐ wǒ shuō de hǎo yìxiē, wǒ de Hànyǔ méiyǒu tā hǎo.", "uz": "Make mendan biroz yaxshiroq gapiradi, mening xitoycham unikidek yaxshi emas.", "ru": "Марк говорит немного лучше меня, мой китайский не так хорош, как его.", "tj": "Маке аз ман каме беҳтар ҳарф мезанад, забони чинии ман мисли ӯ хуб нест."},
        ],
    },
    {
        "block_no": 2,
        "section_label": "课文 2",
        "scene_uz": "Sinfda",
        "scene_ru": "В классе",
        "scene_tj": "Дар синф",
        "word_nos": [3, 4, 5],
        "grammar_nos": [1, 2],
        "dialogue": [
            {"speaker": "小明", "zh": "我喜欢历史课、体育课，不喜欢数学课。", "pinyin": "Wǒ xǐhuan lìshǐ kè, tǐyù kè, bù xǐhuan shùxué kè.", "uz": "Men tarix va jismoniy tarbiya darslarini yaxshi ko'raman, matematikani yoqtirmayman.", "ru": "Я люблю историю и физкультуру, не люблю математику.", "tj": "Ман дарси таърих ва тарбияи ҷисмониро дӯст медорам, математикаро дӯст намедорам."},
            {"speaker": "同学", "zh": "为什么？数学也很有意思啊。", "pinyin": "Wèi shénme? Shùxué yě hěn yǒu yìsi a.", "uz": "Nega? Matematika ham juda qiziqarli-ku.", "ru": "Почему? Математика тоже интересная.", "tj": "Чаро? Математика ҳам хеле ҷолиб аст."},
            {"speaker": "小明", "zh": "我觉得数学比历史难多了，我听不懂。", "pinyin": "Wǒ juéde shùxué bǐ lìshǐ nán duō le, wǒ tīng bu dǒng.", "uz": "Menimcha matematika tarixdan ancha qiyin, tushunmayman.", "ru": "По-моему, математика гораздо труднее истории, я не понимаю.", "tj": "Ба фикрам математика аз таърих хеле душвортар аст, намефаҳмам."},
            {"speaker": "同学", "zh": "别担心，我可以帮你。", "pinyin": "Bié dānxīn, wǒ kěyǐ bāng nǐ.", "uz": "Xavotir olma, men yordam bera olaman.", "ru": "Не волнуйся, я могу помочь.", "tj": "Нигарон нашав, ман ёрӣ дода метавонам."},
            {"speaker": "小明", "zh": "好啊，我们每天学多长时间？", "pinyin": "Hǎo a, wǒmen měi tiān xué duō cháng shíjiān?", "uz": "Yaxshi, har kuni qancha vaqt o'qiymiz?", "ru": "Хорошо, сколько времени будем заниматься каждый день?", "tj": "Хуб, ҳар рӯз чанд вақт мехонем?"},
            {"speaker": "同学", "zh": "一两个小时吧。", "pinyin": "Yì liǎng ge xiǎoshí ba.", "uz": "Bir-ikki soat.", "ru": "Один-два часа.", "tj": "Як-ду соат."},
        ],
    },
    {
        "block_no": 3,
        "section_label": "课文 3",
        "scene_uz": "Dam olish xonasida",
        "scene_ru": "В комнате отдыха",
        "scene_tj": "Дар ҳуҷраи истироҳат",
        "word_nos": [6, 7, 8, 9, 10],
        "grammar_nos": [1, 2],
        "dialogue": [
            {"speaker": "同事", "zh": "你最近比以前来得早多了，搬家了？", "pinyin": "Nǐ zuìjìn bǐ yǐqián lái de zǎo duō le, bān jiā le?", "uz": "Oxirgi paytda oldingidan ancha erta kelyapsan, ko'chdingmi?", "ru": "В последнее время ты приходишь намного раньше, переехала?", "tj": "Вақтҳои охир аз пеш хеле барвақт меоӣ, кӯчидӣ?"},
            {"speaker": "小丽", "zh": "是啊，你不知道？我上个月就搬家了，走路二十分钟就到。", "pinyin": "Shì a, nǐ bù zhīdào? Wǒ shàng ge yuè jiù bān jiā le, zǒu lù èrshí fēnzhōng jiù dào.", "uz": "Ha, bilmaysanmi? O'tgan oydayoq ko'chdim, piyoda yigirma daqiqada yetaman.", "ru": "Да, ты не знал? Я ещё в прошлом месяце переехала, пешком за двадцать минут дохожу.", "tj": "Ҳа, намедонӣ? Моҳи гузашта кӯчидам, пиёда дар бист дақиқа мерасам."},
            {"speaker": "同事", "zh": "那很方便啊。", "pinyin": "Nà hěn fāngbiàn a.", "uz": "Bu juda qulay ekan.", "ru": "Это очень удобно.", "tj": "Ин хеле қулай аст."},
            {"speaker": "小丽", "zh": "我还打算买辆自行车，骑车七八分钟就能到。", "pinyin": "Wǒ hái dǎsuàn mǎi liàng zìxíngchē, qí chē qī bā fēnzhōng jiù néng dào.", "uz": "Yana velosiped olmoqchiman, velosipedda yetti-sakkiz daqiqada yetaman.", "ru": "Ещё собираюсь купить велосипед, на велосипеде можно добраться за семь-восемь минут.", "tj": "Боз мехоҳам дучарха харам, бо дучарха дар ҳафт-ҳашт дақиқа мерасам."},
            {"speaker": "同事", "zh": "你不是有一辆吗？", "pinyin": "Nǐ bú shì yǒu yí liàng ma?", "uz": "Senda bittasi bor emasmi?", "ru": "Разве у тебя уже нет одного?", "tj": "Магар якто надорӣ?"},
            {"speaker": "小丽", "zh": "那辆太旧了，要换一辆，很便宜，两三百块钱。", "pinyin": "Nà liàng tài jiù le, yào huàn yí liàng, hěn piányi, liǎng sān bǎi kuài qián.", "uz": "U juda eski, boshqasiga almashtirish kerak, juda arzon, ikki-uch yuz yuan.", "ru": "Тот слишком старый, нужно поменять, очень дешево, двести-триста юаней.", "tj": "Он хеле кӯҳна аст, бояд дигар кунам, хеле арзон, дусад-се сад юан."},
        ],
    },
    {
        "block_no": 4,
        "section_label": "课文 4",
        "scene_uz": "Uy ko'rishda",
        "scene_ru": "Осмотр квартиры",
        "scene_tj": "Тамошои хона",
        "word_nos": [11, 12, 13, 14, 15],
        "grammar_nos": [1, 2],
        "dialogue": [
            {"speaker": "大山", "zh": "这两个地方的房子一样吗？", "pinyin": "Zhè liǎng ge dìfang de fángzi yíyàng ma?", "uz": "Bu ikki joydagi uylar bir xilmi?", "ru": "Квартиры в этих двух местах одинаковые?", "tj": "Хонаҳои ин ду ҷой якхелаанд?"},
            {"speaker": "中介", "zh": "不一样。您看，学校外边的房子比学校里边的大一些。", "pinyin": "Bù yíyàng. Nín kàn, xuéxiào wàibian de fángzi bǐ xuéxiào lǐbian de dà yìxiē.", "uz": "Bir xil emas. Qarang, maktab tashqarisidagi uy maktab ichkarisidagidan biroz kattaroq.", "ru": "Не одинаковые. Смотрите, квартира за пределами школы немного больше, чем внутри школы.", "tj": "Якхела нест. Бубинед, хонаи берун аз мактаб аз хонаи дохили мактаб каме калонтар аст."},
            {"speaker": "大山", "zh": "大小没关系，主要是环境，哪个更安静？", "pinyin": "Dàxiǎo méi guānxi, zhǔyào shì huánjìng, nǎ ge gèng ānjìng?", "uz": "Kattaligi muhim emas, asosiysi muhit, qaysisi tinchroq?", "ru": "Размер не важен, главное окружение, где тише?", "tj": "Андоза муҳим нест, асосӣ муҳит аст, кадомаш оромтар?"},
            {"speaker": "中介", "zh": "学校里边的没有学校外边的那么安静。", "pinyin": "Xuéxiào lǐbian de méiyǒu xuéxiào wàibian de nàme ānjìng.", "uz": "Maktab ichkarisidagisi maktab tashqarisidagidek tinch emas.", "ru": "Внутри школы не так тихо, как за её пределами.", "tj": "Дохили мактаб мисли беруни мактаб ором нест."},
            {"speaker": "大山", "zh": "哪个方便一些呢？", "pinyin": "Nǎ ge fāngbiàn yìxiē ne?", "uz": "Qaysisi biroz qulayroq?", "ru": "Какая немного удобнее?", "tj": "Кадомаш каме қулайтар?"},
            {"speaker": "中介", "zh": "学校里边比学校外边方便，附近有三四个车站。", "pinyin": "Xuéxiào lǐbian bǐ xuéxiào wàibian fāngbiàn, fùjìn yǒu sān sì ge chēzhàn.", "uz": "Maktab ichkarisidagisi tashqarisidagidan qulayroq, yaqin atrofda uch-to'rt bekat bor.", "ru": "Внутри школы удобнее, чем за её пределами, рядом есть три-четыре остановки.", "tj": "Дохили мактаб аз беруни мактаб қулайтар аст, дар наздикӣ се-чор истгоҳ ҳаст."},
        ],
    },
]


_LESSON_11_VOCABULARY = [
    {"no": 1, "zh": "图书馆", "pinyin": "túshūguǎn", "pos": "n.", "uz": "kutubxona", "ru": "библиотека", "tj": "китобхона"},
    {"no": 2, "zh": "借", "pinyin": "jiè", "pos": "v.", "uz": "qarzga olmoq, qarzga bermoq", "ru": "брать в долг, одалживать", "tj": "қарз гирифтан, қарз додан"},
    {"no": 3, "zh": "词典", "pinyin": "cídiǎn", "pos": "n.", "uz": "lug'at", "ru": "словарь", "tj": "луғат"},
    {"no": 4, "zh": "还", "pinyin": "huán", "pos": "v.", "uz": "qaytarmoq", "ru": "возвращать", "tj": "баргардондан"},
    {"no": 5, "zh": "灯", "pinyin": "dēng", "pos": "n.", "uz": "chiroq", "ru": "лампа, свет", "tj": "чароғ"},
    {"no": 6, "zh": "会议", "pinyin": "huìyì", "pos": "n.", "uz": "yig'ilish, majlis", "ru": "собрание, совещание", "tj": "маҷлис"},
    {"no": 7, "zh": "结束", "pinyin": "jiéshù", "pos": "v.", "uz": "tugamoq, yakunlanmoq", "ru": "заканчиваться", "tj": "ба поён расидан"},
    {"no": 8, "zh": "忘记", "pinyin": "wàngjì", "pos": "v.", "uz": "unutmoq", "ru": "забывать", "tj": "фаромӯш кардан"},
    {"no": 9, "zh": "空调", "pinyin": "kōngtiáo", "pos": "n.", "uz": "konditsioner", "ru": "кондиционер", "tj": "кондитсионер"},
    {"no": 10, "zh": "关", "pinyin": "guān", "pos": "v.", "uz": "o'chirmoq, yopmoq", "ru": "выключать, закрывать", "tj": "хомӯш кардан, бастан"},
    {"no": 11, "zh": "地铁", "pinyin": "dìtiě", "pos": "n.", "uz": "metro", "ru": "метро", "tj": "метро"},
    {"no": 12, "zh": "双", "pinyin": "shuāng", "pos": "m.", "uz": "juft narsalar uchun hisob so'zi", "ru": "счётное слово для парных предметов", "tj": "ҳисобвожа барои ҷуфт"},
    {"no": 13, "zh": "筷子", "pinyin": "kuàizi", "pos": "n.", "uz": "cho'pchalar", "ru": "палочки для еды", "tj": "чӯбчаҳои хӯрокхӯрӣ"},
    {"no": 14, "zh": "啤酒", "pinyin": "píjiǔ", "pos": "n.", "uz": "pivo", "ru": "пиво", "tj": "пиво"},
    {"no": 15, "zh": "口", "pinyin": "kǒu", "pos": "m.", "uz": "qultum, luqma uchun hisob so'zi", "ru": "счётное слово для глотков/кусков", "tj": "ҳисобвожа барои ҷуръа/луқма"},
    {"no": 16, "zh": "瓶子", "pinyin": "píngzi", "pos": "n.", "uz": "shisha, butilka", "ru": "бутылка", "tj": "шиша"},
    {"no": 17, "zh": "笔记本(电脑)", "pinyin": "bǐjìběn (diànnǎo)", "pos": "n.", "uz": "noutbuk", "ru": "ноутбук", "tj": "ноутбук"},
    {"no": 18, "zh": "电子邮件", "pinyin": "diànzǐ yóujiàn", "pos": "n.", "uz": "elektron pochta", "ru": "электронная почта", "tj": "почтаи электронӣ"},
    {"no": 19, "zh": "习惯", "pinyin": "xíguàn", "pos": "v./n.", "uz": "odatlanmoq; odat", "ru": "привыкать; привычка", "tj": "одат кардан; одат"},
]


_LESSON_11_DIALOGUES = [
    {
        "block_no": 1,
        "section_label": "课文 1",
        "scene_uz": "Sinfda",
        "scene_ru": "В классе",
        "scene_tj": "Дар синф",
        "word_nos": [1, 2, 3, 4, 5],
        "grammar_nos": [1],
        "dialogue": [
            {"speaker": "小明", "zh": "我先走了。", "pinyin": "Wǒ xiān zǒu le.", "uz": "Men avval ketdim.", "ru": "Я сначала пойду.", "tj": "Ман аввал меравам."},
            {"speaker": "同学", "zh": "你去哪儿？", "pinyin": "Nǐ qù nǎr?", "uz": "Qayerga ketyapsan?", "ru": "Куда ты идёшь?", "tj": "Ба куҷо меравӣ?"},
            {"speaker": "小明", "zh": "我去图书馆借本书。", "pinyin": "Wǒ qù túshūguǎn jiè běn shū.", "uz": "Kutubxonaga kitob olishga boraman.", "ru": "Пойду в библиотеку взять книгу.", "tj": "Ба китобхона барои гирифтани китоб меравам."},
            {"speaker": "同学", "zh": "帮我把这本词典还了吧。", "pinyin": "Bāng wǒ bǎ zhè běn cídiǎn huán le ba.", "uz": "Menga yordam berib, shu lug'atni qaytarib qo'y.", "ru": "Помоги мне вернуть этот словарь.", "tj": "Ба ман ёрӣ деҳ, ин луғатро баргардон."},
            {"speaker": "小明", "zh": "好，等一会儿你离开教室的时候，记得把灯关了。", "pinyin": "Hǎo, děng yíhuìr nǐ líkāi jiàoshì de shíhou, jìde bǎ dēng guān le.", "uz": "Yaxshi, keyin sen sinfdan chiqqaningda, chiroqni o'chirishni esla.", "ru": "Хорошо, когда потом будешь уходить из класса, не забудь выключить свет.", "tj": "Хуб, баъд вақте аз синф мебароӣ, чароғро хомӯш карданро дар ёд дор."},
            {"speaker": "同学", "zh": "好的，放心吧。", "pinyin": "Hǎo de, fàngxīn ba.", "uz": "Xo'p, xotirjam bo'l.", "ru": "Хорошо, не волнуйся.", "tj": "Хуб, хотирҷамъ бош."},
        ],
    },
    {
        "block_no": 2,
        "section_label": "课文 2",
        "scene_uz": "Majlis xonasida",
        "scene_ru": "В конференц-зале",
        "scene_tj": "Дар толори маҷлис",
        "word_nos": [6, 7, 8, 9, 10, 11],
        "grammar_nos": [1, 2],
        "dialogue": [
            {"speaker": "周明", "zh": "会议结束后，别忘记把空调关了。", "pinyin": "Huìyì jiéshù hòu, bié wàngjì bǎ kōngtiáo guān le.", "uz": "Majlis tugagach, konditsionerni o'chirishni unutma.", "ru": "После окончания совещания не забудь выключить кондиционер.", "tj": "Баъд аз анҷоми маҷлис хомӯш кардани кондитсионерро фаромӯш накун."},
            {"speaker": "小丽", "zh": "好的。王经理两点左右来了个电话。", "pinyin": "Hǎo de. Wáng jīnglǐ liǎng diǎn zuǒyòu lái le ge diànhuà.", "uz": "Xo'p. Menejer Wang soat ikki atrofida qo'ng'iroq qildi.", "ru": "Хорошо. Менеджер Ван около двух позвонил.", "tj": "Хуб. Мудир Ванг тахминан соати ду занг зад."},
            {"speaker": "周明", "zh": "他已经到北京了？", "pinyin": "Tā yǐjīng dào Běijīng le?", "uz": "U allaqachon Pekinga yetibdimi?", "ru": "Он уже прибыл в Пекин?", "tj": "Ӯ аллакай ба Пекин расидааст?"},
            {"speaker": "小丽", "zh": "是的，他正坐地铁来我们公司呢。", "pinyin": "Shì de, tā zhèng zuò dìtiě lái wǒmen gōngsī ne.", "uz": "Ha, u hozir metroda kompaniyamizga kelyapti.", "ru": "Да, он сейчас едет в нашу компанию на метро.", "tj": "Ҳа, ӯ ҳоло бо метро ба ширкати мо меояд."},
            {"speaker": "周明", "zh": "等他到了就告诉我。", "pinyin": "Děng tā dào le jiù gàosu wǒ.", "uz": "U yetib kelgach, menga ayt.", "ru": "Когда он приедет, скажи мне.", "tj": "Вақте расид, ба ман гӯй."},
        ],
    },
    {
        "block_no": 3,
        "section_label": "课文 3",
        "scene_uz": "Mehmonxonada",
        "scene_ru": "В гостиной",
        "scene_tj": "Дар меҳмонхона",
        "word_nos": [12, 13, 14, 15, 16],
        "grammar_nos": [1],
        "dialogue": [
            {"speaker": "妈妈", "zh": "还差一双筷子，你去拿一下。", "pinyin": "Hái chà yì shuāng kuàizi, nǐ qù ná yíxià.", "uz": "Yana bir juft cho'pcha yetishmayapti, borib olib kel.", "ru": "Не хватает ещё одной пары палочек, сходи принеси.", "tj": "Боз як ҷуфт чӯбча намерасад, рафта биёр."},
            {"speaker": "儿子", "zh": "今天怎么做了这么多菜？", "pinyin": "Jīntiān zěnme zuò le zhème duō cài?", "uz": "Bugun nega buncha ko'p ovqat qildingiz?", "ru": "Почему сегодня приготовили так много блюд?", "tj": "Имрӯз чаро ин қадар хӯрок пухтед?"},
            {"speaker": "妈妈", "zh": "今天是你爸爸的生日。", "pinyin": "Jīntiān shì nǐ bàba de shēngrì.", "uz": "Bugun dadangning tug'ilgan kuni.", "ru": "Сегодня день рождения твоего папы.", "tj": "Имрӯз рӯзи таваллуди падарат аст."},
            {"speaker": "儿子", "zh": "真的啊？我把爸爸的生日忘了。那我们今天喝点儿啤酒吧。", "pinyin": "Zhēn de a? Wǒ bǎ bàba de shēngrì wàng le. Nà wǒmen jīntiān hē diǎnr píjiǔ ba.", "uz": "Rostdanmi? Dadamning tug'ilgan kunini unutibman. Unda bugun biroz pivo ichaylik.", "ru": "Правда? Я забыл день рождения папы. Тогда сегодня выпьем немного пива.", "tj": "Рост? Рӯзи таваллуди падарамро фаромӯш кардаам. Пас имрӯз каме пиво менӯшем."},
            {"speaker": "妈妈", "zh": "医生说你爸爸一口酒都不能喝，别让他看见酒瓶子。", "pinyin": "Yīshēng shuō nǐ bàba yì kǒu jiǔ dōu bù néng hē, bié ràng tā kànjiàn jiǔ píngzi.", "uz": "Shifokor dadang bir qultum ham ichmasin dedi, unga shisha ko'rsatma.", "ru": "Врач сказал, что твоему папе нельзя ни глотка алкоголя, не давай ему увидеть бутылку.", "tj": "Духтур гуфт, ки падарат ҳатто як ҷуръа шароб ҳам нӯшидан мумкин нест, нагузор шишаро бинад."},
        ],
    },
    {
        "block_no": 4,
        "section_label": "课文 4",
        "scene_uz": "Kompyuter haqida matn",
        "scene_ru": "Текст о компьютере",
        "scene_tj": "Матн дар бораи компютер",
        "word_nos": [17, 18, 19],
        "grammar_nos": [1, 2],
        "dialogue": [
            {"speaker": "旁白", "zh": "这个笔记本电脑我去年买的时候要五千块左右，现在便宜多了。", "pinyin": "Zhè ge bǐjìběn diànnǎo wǒ qùnián mǎi de shíhou yào wǔ qiān kuài zuǒyòu, xiànzài piányi duō le.", "uz": "Bu noutbukni o'tgan yili olganimda taxminan besh ming yuan edi, hozir ancha arzonlashdi.", "ru": "Когда я покупал этот ноутбук в прошлом году, он стоил около пяти тысяч юаней, сейчас намного дешевле.", "tj": "Вақте ин ноутбукро соли гузашта харидам, тақрибан панҷ ҳазор юан буд, ҳоло хеле арзон шудааст."},
            {"speaker": "旁白", "zh": "我想把这个电脑卖了，再买一个更好的。", "pinyin": "Wǒ xiǎng bǎ zhè ge diànnǎo mài le, zài mǎi yí ge gèng hǎo de.", "uz": "Bu kompyuterni sotib, yana yaxshirog'ini olmoqchiman.", "ru": "Я хочу продать этот компьютер и купить ещё лучше.", "tj": "Мехоҳам ин компютерро фурӯшам ва яктои беҳтарашро харам."},
            {"speaker": "旁白", "zh": "现在我每天起床后的第一件事就是打开电脑，看电子邮件。", "pinyin": "Xiànzài wǒ měi tiān qǐchuáng hòu de dì yī jiàn shì jiù shì dǎkāi diànnǎo, kàn diànzǐ yóujiàn.", "uz": "Hozir har kuni turganimdan keyingi birinchi ishim kompyuterni ochib, email ko'rish.", "ru": "Сейчас первое, что я делаю каждый день после подъёма, - включаю компьютер и проверяю электронную почту.", "tj": "Ҳоло ҳар рӯз баъд аз хестан аввалин корам кушодани компютер ва дидани почтаи электронӣ аст."},
            {"speaker": "旁白", "zh": "我已经很少写信，也很少用笔写字，已经习惯用电脑来学习和工作了。", "pinyin": "Wǒ yǐjīng hěn shǎo xiě xìn, yě hěn shǎo yòng bǐ xiě zì, yǐjīng xíguàn yòng diànnǎo lái xuéxí hé gōngzuò le.", "uz": "Men endi juda kam xat yozaman, ruchka bilan ham kam yozaman, kompyuterda o'qish va ishlashga odatlanganman.", "ru": "Я уже редко пишу письма и редко пишу ручкой, уже привык учиться и работать на компьютере.", "tj": "Ман аллакай хеле кам мактуб менависам, бо қалам ҳам кам менависам, ба истифодаи компютер барои таҳсил ва кор одат кардаам."},
            {"speaker": "旁白", "zh": "哪一天突然没有了电脑，我们怎么办呢？", "pinyin": "Nǎ yì tiān tūrán méiyǒu le diànnǎo, wǒmen zěnme bàn ne?", "uz": "Bir kuni to'satdan kompyuter bo'lmasa, nima qilamiz?", "ru": "Если однажды вдруг не станет компьютеров, что мы будем делать?", "tj": "Агар рӯзе ногаҳон компютер набошад, мо чӣ кор мекунем?"},
        ],
    },
]


_LESSON_12_VOCABULARY = [
    {"no": 1, "zh": "太阳", "pinyin": "tàiyáng", "pos": "n.", "uz": "quyosh", "ru": "солнце", "tj": "офтоб"},
    {"no": 2, "zh": "西", "pinyin": "xī", "pos": "n.", "uz": "g'arb", "ru": "запад", "tj": "ғарб"},
    {"no": 3, "zh": "生气", "pinyin": "shēng qì", "pos": "v.", "uz": "jahli chiqmoq", "ru": "сердиться", "tj": "хашмгин шудан"},
    {"no": 4, "zh": "行李箱", "pinyin": "xínglixiāng", "pos": "n.", "uz": "jomadon, chamadon", "ru": "чемодан", "tj": "ҷомадон"},
    {"no": 5, "zh": "自己", "pinyin": "zìjǐ", "pos": "pron.", "uz": "o'zi", "ru": "сам", "tj": "худ"},
    {"no": 6, "zh": "包", "pinyin": "bāo", "pos": "n.", "uz": "sumka, xalta", "ru": "сумка, пакет", "tj": "халта, сумка"},
    {"no": 7, "zh": "发现", "pinyin": "fāxiàn", "pos": "v.", "uz": "payqamoq, aniqlamoq", "ru": "обнаружить", "tj": "пай бурдан"},
    {"no": 8, "zh": "护照", "pinyin": "hùzhào", "pos": "n.", "uz": "pasport", "ru": "паспорт", "tj": "шиноснома"},
    {"no": 9, "zh": "起飞", "pinyin": "qǐfēi", "pos": "v.", "uz": "uchib ketmoq", "ru": "взлетать", "tj": "парвоз кардан"},
    {"no": 10, "zh": "司机", "pinyin": "sījī", "pos": "n.", "uz": "haydovchi", "ru": "водитель", "tj": "ронанда"},
    {"no": 11, "zh": "教", "pinyin": "jiāo", "pos": "v.", "uz": "o'qitmoq, o'rgatmoq", "ru": "учить, преподавать", "tj": "омӯзондан"},
    {"no": 12, "zh": "画", "pinyin": "huà", "pos": "v./n.", "uz": "chizmoq; rasm", "ru": "рисовать; рисунок", "tj": "расм кашидан; расм"},
    {"no": 13, "zh": "需要", "pinyin": "xūyào", "pos": "v.", "uz": "kerak bo'lmoq, ehtiyoj sezmoq", "ru": "нуждаться, требоваться", "tj": "лозим шудан"},
    {"no": 14, "zh": "黑板", "pinyin": "hēibǎn", "pos": "n.", "uz": "doska", "ru": "классная доска", "tj": "тахтаи синф"},
]


_LESSON_12_DIALOGUES = [
    {
        "block_no": 1,
        "section_label": "课文 1",
        "scene_uz": "Uyda",
        "scene_ru": "Дома",
        "scene_tj": "Дар хона",
        "word_nos": [1, 2, 3],
        "grammar_nos": [1],
        "dialogue": [
            {"speaker": "小丽", "zh": "今天太阳从西边出来了吗？", "pinyin": "Jīntiān tàiyáng cóng xībian chūlai le ma?", "uz": "Bugun quyosh g'arbdan chiqdimi?", "ru": "Сегодня солнце взошло на западе?", "tj": "Имрӯз офтоб аз ғарб баромад?"},
            {"speaker": "小刚", "zh": "怎么了？", "pinyin": "Zěnme le?", "uz": "Nima bo'ldi?", "ru": "Что случилось?", "tj": "Чӣ шуд?"},
            {"speaker": "小丽", "zh": "你怎么这么早就要睡觉了？以前都要12点以后才睡觉。", "pinyin": "Nǐ zěnme zhème zǎo jiù yào shuìjiào le? Yǐqián dōu yào shí'èr diǎn yǐhòu cái shuìjiào.", "uz": "Nega bunchalik erta uxlashga yotyapsan? Oldin doim soat 12 dan keyin uxlar eding.", "ru": "Почему ты так рано собираешься спать? Раньше ты всегда ложился после 12.", "tj": "Чаро ин қадар барвақт хоб карданӣ ҳастӣ? Пештар ҳамеша баъд аз соати 12 мехобидӣ."},
            {"speaker": "小刚", "zh": "我明天8点就要到公司。", "pinyin": "Wǒ míngtiān bā diǎn jiù yào dào gōngsī.", "uz": "Men ertaga soat 8 dayoq kompaniyaga yetib borishim kerak.", "ru": "Завтра мне уже в 8 нужно быть в компании.", "tj": "Ман пагоҳ соати 8 бояд ба ширкат расам."},
            {"speaker": "小丽", "zh": "有事吗？", "pinyin": "Yǒu shì ma?", "uz": "Biror ish bormi?", "ru": "Есть дела?", "tj": "Коре ҳаст?"},
            {"speaker": "小刚", "zh": "经理生气了，他告诉我，明天8点不到，以后就别来了。", "pinyin": "Jīnglǐ shēng qì le, tā gàosu wǒ, míngtiān bā diǎn bú dào, yǐhòu jiù bié lái le.", "uz": "Menejer jahli chiqdi, u menga: ertaga soat 8 da kelmasang, keyin umuman kelma, dedi.", "ru": "Менеджер рассердился и сказал мне: если завтра к 8 не придёшь, больше не приходи.", "tj": "Мудир хашмгин шуд, гуфт: агар пагоҳ соати 8 нарасӣ, дигар наё."},
        ],
    },
    {
        "block_no": 2,
        "section_label": "课文 2",
        "scene_uz": "Uyda",
        "scene_ru": "Дома",
        "scene_tj": "Дар хона",
        "word_nos": [4, 5, 6],
        "grammar_nos": [1, 2],
        "dialogue": [
            {"speaker": "小刚", "zh": "我要跟周经理去外地办事，明天的飞机。", "pinyin": "Wǒ yào gēn Zhōu jīnglǐ qù wàidì bàn shì, míngtiān de fēijī.", "uz": "Men menejer Zhou bilan boshqa joyga ishga boraman, ertaga samolyot.", "ru": "Я еду с менеджером Чжоу в другой город по делам, самолёт завтра.", "tj": "Ман бо мудир Чжоу ба ҷои дигар барои кор меравам, ҳавопаймо пагоҳ аст."},
            {"speaker": "小丽", "zh": "那我帮你把衣服放到行李箱里吧。什么时候回来？", "pinyin": "Nà wǒ bāng nǐ bǎ yīfu fàng dào xínglixiāng lǐ ba. Shénme shíhou huílai?", "uz": "Unda kiyimlaringni jomadonga solishga yordam beraman. Qachon qaytasan?", "ru": "Тогда я помогу положить одежду в чемодан. Когда вернёшься?", "tj": "Пас ба ту ёрӣ медиҳам, либосҳоро ба ҷомадон гузорем. Кай бармегардӣ?"},
            {"speaker": "小刚", "zh": "一个星期就回来。", "pinyin": "Yí ge xīngqī jiù huílai.", "uz": "Bir haftadayoq qaytaman.", "ru": "Вернусь уже через неделю.", "tj": "Як ҳафта пас бармегардам."},
            {"speaker": "小丽", "zh": "啊？一个星期以后才回来？", "pinyin": "A? Yí ge xīngqī yǐhòu cái huílai?", "uz": "A? Faqat bir haftadan keyin qaytasanmi?", "ru": "А? Только через неделю вернёшься?", "tj": "А? Танҳо баъд аз як ҳафта бармегардӣ?"},
            {"speaker": "小刚", "zh": "你要自己照顾好自己，我已经给你准备好吃的和喝的了。", "pinyin": "Nǐ yào zìjǐ zhàogù hǎo zìjǐ, wǒ yǐjīng gěi nǐ zhǔnbèi hǎo chī de hé hē de le.", "uz": "O'zingga yaxshi qarashing kerak, men senga yegulik va ichimliklarni tayyorlab qo'ydim.", "ru": "Ты должна сама хорошо о себе заботиться, я уже приготовил тебе еду и напитки.", "tj": "Бояд худатро хуб нигоҳубин кунӣ, ман барои ту хӯроку нӯшокиро тайёр кардаам."},
            {"speaker": "小丽", "zh": "好吧。我已经把我的照片放在你的包里了。", "pinyin": "Hǎo ba. Wǒ yǐjīng bǎ wǒ de zhàopiàn fàng zài nǐ de bāo lǐ le.", "uz": "Mayli. Men allaqachon rasmimni sumkangga solib qo'ydim.", "ru": "Ладно. Я уже положила свою фотографию в твою сумку.", "tj": "Хуб. Ман аллакай сурати худро ба сумкаат гузоштам."},
        ],
    },
    {
        "block_no": 3,
        "section_label": "课文 3",
        "scene_uz": "Aeroportda",
        "scene_ru": "В аэропорту",
        "scene_tj": "Дар фурудгоҳ",
        "word_nos": [7, 8, 9, 10],
        "grammar_nos": [1, 2],
        "dialogue": [
            {"speaker": "周明", "zh": "你怎么才来？", "pinyin": "Nǐ zěnme cái lái?", "uz": "Nega endi kelding?", "ru": "Почему ты только сейчас пришёл?", "tj": "Чаро танҳо ҳоло омадӣ?"},
            {"speaker": "小刚", "zh": "对不起，周经理，来机场的路上我才发现忘带护照了。", "pinyin": "Duìbuqǐ, Zhōu jīnglǐ, lái jīchǎng de lùshang wǒ cái fāxiàn wàng dài hùzhào le.", "uz": "Kechirasiz, menejer Zhou, aeroportga kelayotgan yo'lda pasportimni unutganimni payqadim.", "ru": "Извините, менеджер Чжоу, по дороге в аэропорт я только обнаружил, что забыл паспорт.", "tj": "Бубахшед, мудир Чжоу, дар роҳи фурудгоҳ танҳо фаҳмидам, ки шиносномаро фаромӯш кардаам."},
            {"speaker": "周明", "zh": "快点儿吧，飞机就要起飞了。", "pinyin": "Kuài diǎnr ba, fēijī jiù yào qǐfēi le.", "uz": "Tezroq bo'l, samolyot uchish arafasida.", "ru": "Поторопись, самолёт вот-вот взлетит.", "tj": "Зудтар, ҳавопаймо ҳозир парвоз мекунад."},
            {"speaker": "小刚", "zh": "您有钱吗？司机把我送到机场的时候，我才发现忘记带钱包了。", "pinyin": "Nín yǒu qián ma? Sījī bǎ wǒ sòng dào jīchǎng de shíhou, wǒ cái fāxiàn wàngjì dài qiánbāo le.", "uz": "Sizda pul bormi? Haydovchi meni aeroportga olib kelganda, hamyonimni unutganimni payqadim.", "ru": "У вас есть деньги? Когда водитель довёз меня до аэропорта, я только понял, что забыл кошелёк.", "tj": "Шумо пул доред? Вақте ронанда маро ба фурудгоҳ овард, танҳо фаҳмидам, ки ҳамёнро фаромӯш кардаам."},
            {"speaker": "周明", "zh": "我看你还是把重要的东西放在我这儿吧。", "pinyin": "Wǒ kàn nǐ háishi bǎ zhòngyào de dōngxi fàng zài wǒ zhèr ba.", "uz": "Menimcha, muhim narsalaringni baribir mening oldimga qo'yganing yaxshi.", "ru": "Думаю, важные вещи тебе всё-таки лучше оставить у меня.", "tj": "Ба фикрам, чизҳои муҳиматро беҳтараш назди ман гузор."},
        ],
    },
    {
        "block_no": 4,
        "section_label": "课文 4",
        "scene_uz": "O'qituvchi hikoyasi",
        "scene_ru": "Рассказ учителя",
        "scene_tj": "Ҳикояи омӯзгор",
        "word_nos": [11, 12, 13, 14],
        "grammar_nos": [2],
        "dialogue": [
            {"speaker": "旁白", "zh": "我是一个中学老师，教学生画画儿。", "pinyin": "Wǒ shì yí ge zhōngxué lǎoshī, jiāo xuésheng huà huàr.", "uz": "Men o'rta maktab o'qituvchisiman, o'quvchilarga rasm chizishni o'rgataman.", "ru": "Я учитель средней школы, учу учеников рисовать.", "tj": "Ман омӯзгори мактаби миёна ҳастам, ба донишомӯзон расмкашӣ меомӯзонам."},
            {"speaker": "旁白", "zh": "每次下课前，我都会把下次学生需要带的东西写在黑板上，但是每次上课时，总会有学生忘了拿铅笔，所以我有点儿生气，不是因为他们没带铅笔，是因为他们没有好的学习习惯。", "pinyin": "Měi cì xià kè qián, wǒ dōu huì bǎ xià cì xuésheng xūyào dài de dōngxi xiě zài hēibǎn shang, dànshì měi cì shàng kè shí, zǒng huì yǒu xuésheng wàng le ná qiānbǐ, suǒyǐ wǒ yǒudiǎnr shēng qì, bú shì yīnwèi tāmen méi dài qiānbǐ, shì yīnwèi tāmen méiyǒu hǎo de xuéxí xíguàn.", "uz": "Har safar dars tugashidan oldin keyingi safar o'quvchilar olib kelishi kerak bo'lgan narsalarni doskaga yozaman, lekin har safar darsda baribir kimdir qalam olib kelishni unutadi, shuning uchun biroz jahlim chiqadi. Bu ular qalam olib kelmagani uchun emas, yaxshi o'qish odati yo'qligi uchun.", "ru": "Каждый раз перед окончанием урока я пишу на доске, что ученикам нужно принести в следующий раз, но каждый раз на уроке кто-то забывает взять карандаш, поэтому я немного сержусь. Не потому, что они не принесли карандаш, а потому, что у них нет хорошей учебной привычки.", "tj": "Ҳар дафъа пеш аз анҷоми дарс чизҳоеро, ки дафъаи дигар донишомӯзон бояд биёранд, дар тахта менависам, аммо ҳар дафъа дар дарс донишомӯзе қалам оварданро фаромӯш мекунад, барои ҳамин каме хашмгин мешавам. На барои он ки қалам наоварданд, балки барои он ки одати хуби омӯзишӣ надоранд."},
        ],
    },
]


_LESSON_13_VOCABULARY = [
    {"no": 1, "zh": "终于", "pinyin": "zhōngyú", "pos": "adv.", "uz": "nihoyat, oxiri", "ru": "наконец", "tj": "ниҳоят"},
    {"no": 2, "zh": "爷爷", "pinyin": "yéye", "pos": "n.", "uz": "bobo", "ru": "дедушка", "tj": "бобо"},
    {"no": 3, "zh": "礼物", "pinyin": "lǐwù", "pos": "n.", "uz": "sovg'a", "ru": "подарок", "tj": "туҳфа"},
    {"no": 4, "zh": "奶奶", "pinyin": "nǎinai", "pos": "n.", "uz": "buvi", "ru": "бабушка", "tj": "биби"},
    {"no": 5, "zh": "遇到", "pinyin": "yùdào", "pos": "v.", "uz": "duch kelmoq, uchratmoq", "ru": "встретить, столкнуться", "tj": "дучор шудан, вохӯрдан"},
    {"no": 6, "zh": "一边", "pinyin": "yìbiān", "pos": "adv.", "uz": "bir vaqtda, bir tarafdan", "ru": "одновременно", "tj": "ҳамзамон"},
    {"no": 7, "zh": "过去", "pinyin": "guòqù", "pos": "n.", "uz": "o'tmish", "ru": "прошлое", "tj": "гузашта"},
    {"no": 8, "zh": "一般", "pinyin": "yìbān", "pos": "adj./adv.", "uz": "odatda; umumiy", "ru": "обычно; общий", "tj": "одатан; умумӣ"},
    {"no": 9, "zh": "愿意", "pinyin": "yuànyì", "pos": "v.", "uz": "xohlamoq, rozi bo'lmoq", "ru": "хотеть, быть готовым", "tj": "хостан, розӣ будан"},
    {"no": 10, "zh": "起来", "pinyin": "qǐlái", "pos": "v.", "uz": "turmoq, yuqoriga harakatlanmoq", "ru": "подниматься, вставать", "tj": "бархостан, боло шудан"},
    {"no": 11, "zh": "应该", "pinyin": "yīnggāi", "pos": "v.", "uz": "kerak, lozim", "ru": "следует, должен", "tj": "бояд"},
    {"no": 12, "zh": "生活", "pinyin": "shēnghuó", "pos": "n.", "uz": "hayot", "ru": "жизнь", "tj": "зиндагӣ"},
    {"no": 13, "zh": "校长", "pinyin": "xiàozhǎng", "pos": "n.", "uz": "maktab direktori", "ru": "директор школы", "tj": "директори мактаб"},
    {"no": 14, "zh": "坏", "pinyin": "huài", "pos": "adj.", "uz": "buzuq, yomon", "ru": "испорченный, плохой", "tj": "вайрон, бад"},
    {"no": 15, "zh": "经常", "pinyin": "jīngcháng", "pos": "adv.", "uz": "tez-tez, ko'pincha", "ru": "часто", "tj": "зуд-зуд"},
]


_LESSON_13_DIALOGUES = [
    {
        "block_no": 1,
        "section_label": "课文 1",
        "scene_uz": "Uyda",
        "scene_ru": "Дома",
        "scene_tj": "Дар хона",
        "word_nos": [1, 2, 3, 4],
        "grammar_nos": [1, 3],
        "dialogue": [
            {"speaker": "小丽", "zh": "你终于回来了！从哪儿买回来这么多东西啊？", "pinyin": "Nǐ zhōngyú huílai le! Cóng nǎr mǎi huílai zhème duō dōngxi a?", "uz": "Nihoyat qaytding! Shuncha narsani qayerdan sotib olib kelding?", "ru": "Наконец-то ты вернулся! Откуда ты купил столько вещей?", "tj": "Ниҳоят баргаштӣ! Ин қадар чизро аз куҷо харида овардӣ?"},
            {"speaker": "小刚", "zh": "都是从那边的商店买回来的。", "pinyin": "Dōu shì cóng nàbiān de shāngdiàn mǎi huílai de.", "uz": "Hammasini u yerdagi do'kondan sotib olib keldim.", "ru": "Всё купил в магазине там.", "tj": "Ҳамаро аз мағозаи он тараф харида овардам."},
            {"speaker": "小丽", "zh": "怎么还买红酒回来了？谁喝啊？", "pinyin": "Zěnme hái mǎi hóngjiǔ huílai le? Shéi hē a?", "uz": "Nega vino ham sotib olib kelding? Kim ichadi?", "ru": "Зачем ещё купил вино? Кто будет пить?", "tj": "Чаро боз шароб харида овардӣ? Кӣ менӯшад?"},
            {"speaker": "小刚", "zh": "这是给爷爷的礼物，明天我们一起送过去，看看爷爷奶奶。", "pinyin": "Zhè shì gěi yéye de lǐwù, míngtiān wǒmen yìqǐ sòng guòqu, kànkan yéye nǎinai.", "uz": "Bu bobomga sovg'a, ertaga birga olib borib, bobo-buvimni ko'ramiz.", "ru": "Это подарок дедушке, завтра вместе отвезём и навестим бабушку с дедушкой.", "tj": "Ин туҳфа барои бобо, пагоҳ якҷоя мебарем ва бобову бибиро мебинем."},
            {"speaker": "小丽", "zh": "那我的礼物呢？快拿出来让我看看。", "pinyin": "Nà wǒ de lǐwù ne? Kuài ná chūlai ràng wǒ kànkan.", "uz": "Unda mening sovg'am-chi? Tez olib chiq, ko'ray.", "ru": "А мой подарок? Доставай скорее, дай посмотреть.", "tj": "Пас туҳфаи ман чӣ? Зуд барор, бинам."},
            {"speaker": "小刚", "zh": "我不是已经回来了吗？", "pinyin": "Wǒ bú shì yǐjīng huílai le ma?", "uz": "Men allaqachon qaytib keldim-ku?", "ru": "Разве я уже не вернулся?", "tj": "Магар ман аллакай барнагаштам?"},
        ],
    },
    {
        "block_no": 2,
        "section_label": "课文 2",
        "scene_uz": "Uyda",
        "scene_ru": "Дома",
        "scene_tj": "Дар хона",
        "word_nos": [5, 6, 7],
        "grammar_nos": [1, 2, 3],
        "dialogue": [
            {"speaker": "小丽", "zh": "我今天看见你和一个女的进了咖啡店，她是谁啊？", "pinyin": "Wǒ jīntiān kànjiàn nǐ hé yí ge nǚ de jìn le kāfēidiàn, tā shì shéi a?", "uz": "Bugun seni bir ayol bilan qahvaxonaga kirganingni ko'rdim, u kim?", "ru": "Сегодня я видела, как ты вошёл в кафе с какой-то женщиной. Кто она?", "tj": "Имрӯз дидам, ки бо як зан ба қаҳвахона даромадӣ, ӯ кист?"},
            {"speaker": "小刚", "zh": "她是我今天在路上遇到的一个老同学。", "pinyin": "Tā shì wǒ jīntiān zài lùshang yùdào de yí ge lǎo tóngxué.", "uz": "U bugun yo'lda uchratgan eski sinfdoshim.", "ru": "Это моя старая одноклассница, которую я встретил сегодня по дороге.", "tj": "Ӯ ҳамсинфи пешинаам аст, ки имрӯз дар роҳ вохӯрдам."},
            {"speaker": "小丽", "zh": "你们就一起去喝咖啡了？", "pinyin": "Nǐmen jiù yìqǐ qù hē kāfēi le?", "uz": "Shunda birga qahva ichgani bordinglarmi?", "ru": "И вы сразу пошли вместе пить кофе?", "tj": "Пас якҷоя қаҳва нӯшидан рафтед?"},
            {"speaker": "小刚", "zh": "是啊，一边喝咖啡一边说了些过去的事。", "pinyin": "Shì a, yìbiān hē kāfēi yìbiān shuō le xiē guòqù de shì.", "uz": "Ha, qahva ichib o'tmishdagi ba'zi gaplarni gaplashdik.", "ru": "Да, пили кофе и говорили о прошлом.", "tj": "Ҳа, қаҳва нӯшида аз баъзе корҳои гузашта гап задем."},
            {"speaker": "小丽", "zh": "你回来得这么晚，是说了很多过去的事吗？", "pinyin": "Nǐ huílai de zhème wǎn, shì shuō le hěn duō guòqù de shì ma?", "uz": "Bunchalik kech qaytganing, o'tmishdagi ko'p narsalarni gaplashganingdanmi?", "ru": "Ты так поздно вернулся потому, что долго говорили о прошлом?", "tj": "Ин қадар дер баргаштанат аз он буд, ки бисёр чизҳои гузаштаро гуфтед?"},
            {"speaker": "小刚", "zh": "不是。没有公共汽车了，我是走回来的。", "pinyin": "Bú shì. Méiyǒu gōnggòng qìchē le, wǒ shì zǒu huílai de.", "uz": "Yo'q. Avtobus yo'q edi, men piyoda qaytib keldim.", "ru": "Нет. Автобусов уже не было, я вернулся пешком.", "tj": "Не. Автобус набуд, ман пиёда баргаштам."},
        ],
    },
    {
        "block_no": 3,
        "section_label": "课文 3",
        "scene_uz": "Telefonda",
        "scene_ru": "По телефону",
        "scene_tj": "Дар телефон",
        "word_nos": [8, 9, 10, 11, 12],
        "grammar_nos": [2],
        "dialogue": [
            {"speaker": "同事", "zh": "小丽，周末你一般跟小刚出去看电影吗？", "pinyin": "Xiǎolì, zhōumò nǐ yìbān gēn Xiǎogāng chūqu kàn diànyǐng ma?", "uz": "Xiaoli, dam olish kunlari odatda Xiaogang bilan kinoga chiqasanmi?", "ru": "Сяоли, по выходным ты обычно ходишь с Сяоганом в кино?", "tj": "Сяоли, охири ҳафта одатан бо Сяоганг кино дидан меравӣ?"},
            {"speaker": "小丽", "zh": "我很少去电影院看电影，我更愿意在家看电视。", "pinyin": "Wǒ hěn shǎo qù diànyǐngyuàn kàn diànyǐng, wǒ gèng yuànyì zài jiā kàn diànshì.", "uz": "Men kinoteatrga juda kam boraman, uyda televizor ko'rishni ko'proq xohlayman.", "ru": "Я редко хожу в кинотеатр, больше предпочитаю смотреть телевизор дома.", "tj": "Ман ба кинотеатр кам меравам, бештар дар хона телевизор диданро мехоҳам."},
            {"speaker": "同事", "zh": "看电视有什么意思啊？", "pinyin": "Kàn diànshì yǒu shénme yìsi a?", "uz": "Televizor ko'rishning nimasi qiziq?", "ru": "Что интересного в телевизоре?", "tj": "Телевизор дидан чӣ ҷолиб дорад?"},
            {"speaker": "小丽", "zh": "可以一边吃一边看，坐久了还可以站起来休息一会儿。", "pinyin": "Kěyǐ yìbiān chī yìbiān kàn, zuò jiǔ le hái kěyǐ zhàn qǐlai xiūxi yíhuìr.", "uz": "Yeb turib ko'rsa bo'ladi, uzoq o'tirsang turib biroz dam olsa bo'ladi.", "ru": "Можно есть и смотреть одновременно, а если долго сидишь, можно встать и отдохнуть.", "tj": "Метавонӣ ҳамзамон хӯрӣ ва бинӣ, дер нишинӣ, бархеста каме истироҳат мекунӣ."},
            {"speaker": "同事", "zh": "你应该多出去走走，这样你们的生活会更有意思。", "pinyin": "Nǐ yīnggāi duō chūqu zǒuzou, zhèyàng nǐmen de shēnghuó huì gèng yǒu yìsi.", "uz": "Ko'proq tashqariga chiqib sayr qilishing kerak, shunda hayotingiz qiziqroq bo'ladi.", "ru": "Тебе надо чаще выходить гулять, так ваша жизнь будет интереснее.", "tj": "Бояд бештар берун баромада сайр кунӣ, ҳамин тавр зиндагиятон ҷолибтар мешавад."},
            {"speaker": "小丽", "zh": "有他在，我的生活已经很有意思了。", "pinyin": "Yǒu tā zài, wǒ de shēnghuó yǐjīng hěn yǒu yìsi le.", "uz": "U bor ekan, hayotim allaqachon juda qiziq.", "ru": "Когда он рядом, моя жизнь уже очень интересная.", "tj": "Ӯ бошад, зиндагиям аллакай хеле ҷолиб аст."},
        ],
    },
    {
        "block_no": 4,
        "section_label": "课文 4",
        "scene_uz": "Eri haqida matn",
        "scene_ru": "Текст о муже",
        "scene_tj": "Матн дар бораи шавҳар",
        "word_nos": [13, 14, 15],
        "grammar_nos": [2],
        "dialogue": [
            {"speaker": "旁白", "zh": "刚结婚的时候，我丈夫是中学老师，他喜欢每天早上起床后，一边吃早饭一边看报纸。十年过去了，现在他已经是校长了，因为太忙，每天早上我起床后都看不到他，晚上很晚他才回到家。我真怕他累坏了。希望他能少一些会议，多一些休息，可以经常和我还有孩子在一起。", "pinyin": "Gāng jiéhūn de shíhou, wǒ zhàngfu shì zhōngxué lǎoshī, tā xǐhuan měi tiān zǎoshang qǐ chuáng hòu, yìbiān chī zǎofàn yìbiān kàn bàozhǐ. Shí nián guòqù le, xiànzài tā yǐjīng shì xiàozhǎng le, yīnwèi tài máng, měi tiān zǎoshang wǒ qǐ chuáng hòu dōu kàn bu dào tā, wǎnshang hěn wǎn tā cái huí dào jiā. Wǒ zhēn pà tā lèi huài le. Xīwàng tā néng shǎo yìxiē huìyì, duō yìxiē xiūxi, kěyǐ jīngcháng hé wǒ hái yǒu háizi zài yìqǐ.", "uz": "Yangi turmush qurganimizda erim o'rta maktab o'qituvchisi edi. U har kuni ertalab turgach nonushta qilib gazeta o'qishni yaxshi ko'rardi. O'n yil o'tdi, hozir u allaqachon maktab direktori. Juda bandligi sababli men har kuni ertalab turganimda uni ko'rmayman, kechqurun juda kech uyga qaytadi. Uning charchab qolishidan juda qo'rqaman. U kamroq majlis qilib, ko'proq dam olsa, men va bolam bilan tez-tez birga bo'lsa, deb umid qilaman.", "ru": "Когда мы только поженились, мой муж был учителем средней школы. Каждое утро после подъёма он любил завтракать и читать газету. Прошло десять лет, теперь он уже директор школы. Из-за занятости утром после подъёма я его не вижу, вечером он возвращается очень поздно. Я правда боюсь, что он переутомится. Надеюсь, у него будет меньше совещаний, больше отдыха, и он сможет чаще быть со мной и ребёнком.", "tj": "Вақте нав оиладор шудем, шавҳарам муаллими мактаби миёна буд. Ӯ ҳар саҳар баъди хестан ҳамзамон наҳорӣ мехӯрд ва рӯзнома мехонд. Даҳ сол гузашт, ҳоло ӯ аллакай директори мактаб аст. Азбаски хеле банд аст, ҳар саҳар баъди хестанам ӯро намебинам, шаб хеле дер ба хона меояд. Ман воқеан метарсам, ки ӯ аз хастагӣ хароб шавад. Умед дорам, ки маҷлисҳояш камтар, истироҳаташ бештар шавад ва зуд-зуд бо ману фарзанд бошад."},
        ],
    },
]


_LESSON_14_VOCABULARY = [
    {"no": 1, "zh": "打扫", "pinyin": "dǎsǎo", "pos": "v.", "uz": "tozalamoq, supurmoq", "ru": "убирать, подметать", "tj": "тоза кардан, рӯфтан"},
    {"no": 2, "zh": "干净", "pinyin": "gānjìng", "pos": "adj.", "uz": "toza", "ru": "чистый", "tj": "тоза"},
    {"no": 3, "zh": "然后", "pinyin": "ránhòu", "pos": "conj.", "uz": "keyin, undan so'ng", "ru": "потом, затем", "tj": "баъд, сипас"},
    {"no": 4, "zh": "冰箱", "pinyin": "bīngxiāng", "pos": "n.", "uz": "muzlatkich", "ru": "холодильник", "tj": "яхдон"},
    {"no": 5, "zh": "洗澡", "pinyin": "xǐ zǎo", "pos": "v.", "uz": "cho'milmoq, dush qabul qilmoq", "ru": "принимать ванну/душ", "tj": "оббозӣ кардан, душ гирифтан"},
    {"no": 6, "zh": "节目", "pinyin": "jiémù", "pos": "n.", "uz": "dastur, ko'rsatuv", "ru": "программа, передача", "tj": "барнома"},
    {"no": 7, "zh": "月亮", "pinyin": "yuèliang", "pos": "n.", "uz": "oy", "ru": "луна", "tj": "моҳ"},
    {"no": 8, "zh": "像", "pinyin": "xiàng", "pos": "v.", "uz": "o'xshamoq", "ru": "быть похожим", "tj": "монанд будан"},
    {"no": 9, "zh": "盘子", "pinyin": "pánzi", "pos": "n.", "uz": "tarelka, lagan", "ru": "тарелка", "tj": "табақ"},
    {"no": 10, "zh": "刮风", "pinyin": "guā fēng", "pos": "v.", "uz": "shamol esmoq", "ru": "быть ветреным", "tj": "шамол вазидан"},
    {"no": 11, "zh": "叔叔", "pinyin": "shūshu", "pos": "n.", "uz": "amaki", "ru": "дядя", "tj": "амак"},
    {"no": 12, "zh": "阿姨", "pinyin": "āyí", "pos": "n.", "uz": "xola, amma", "ru": "тётя", "tj": "хола, амма"},
    {"no": 13, "zh": "故事", "pinyin": "gùshi", "pos": "n.", "uz": "hikoya", "ru": "история, рассказ", "tj": "ҳикоя"},
    {"no": 14, "zh": "声音", "pinyin": "shēngyīn", "pos": "n.", "uz": "ovoz, tovush", "ru": "звук, голос", "tj": "овоз, садо"},
    {"no": 15, "zh": "菜单", "pinyin": "càidān", "pos": "n.", "uz": "menyu", "ru": "меню", "tj": "меню"},
    {"no": 16, "zh": "简单", "pinyin": "jiǎndān", "pos": "adj.", "uz": "oson, oddiy", "ru": "простой", "tj": "содда"},
    {"no": 17, "zh": "香蕉", "pinyin": "xiāngjiāo", "pos": "n.", "uz": "banan", "ru": "банан", "tj": "банан"},
]


_LESSON_14_DIALOGUES = [
    {
        "block_no": 1,
        "section_label": "课文 1",
        "scene_uz": "Uyda",
        "scene_ru": "Дома",
        "scene_tj": "Дар хона",
        "word_nos": [1, 2, 3, 4],
        "grammar_nos": [1, 2],
        "dialogue": [
            {"speaker": "周太太", "zh": "客人就要来了，你怎么还不打扫房间啊？", "pinyin": "Kèrén jiù yào lái le, nǐ zěnme hái bù dǎsǎo fángjiān a?", "uz": "Mehmonlar hozir keladi, nega hali xonani tozalamayapsiz?", "ru": "Гости вот-вот придут, почему ты ещё не убираешь комнату?", "tj": "Меҳмонон ҳозир меоянд, чаро ҳоло ҳам хонаро тоза намекунӣ?"},
            {"speaker": "周明", "zh": "别着急，我让孩子们打扫呢，客人来的时候，他们会把房间打扫干净。", "pinyin": "Bié zháojí, wǒ ràng háizimen dǎsǎo ne, kèrén lái de shíhou, tāmen huì bǎ fángjiān dǎsǎo gānjìng.", "uz": "Shoshilmang, bolalarga tozalatayapman, mehmonlar kelganda ular xonani tozalab qo'yishadi.", "ru": "Не волнуйся, я велел детям убирать, когда гости придут, они уберут комнату чисто.", "tj": "Шитоб накун, ба кӯдакон тоза кардан фармудам, вақте меҳмонон оянд, онҳо хонаро тоза мекунанд."},
            {"speaker": "周太太", "zh": "那你也不能看电视啊。", "pinyin": "Nà nǐ yě bù néng kàn diànshì a.", "uz": "Unda siz ham televizor ko'rib o'tirmasligingiz kerak.", "ru": "Но и ты не должен смотреть телевизор.", "tj": "Пас ту ҳам набояд телевизор бинӣ."},
            {"speaker": "周明", "zh": "你让我做什么？", "pinyin": "Nǐ ràng wǒ zuò shénme?", "uz": "Menga nima qilishni buyurasiz?", "ru": "Что ты хочешь, чтобы я сделал?", "tj": "Ба ман чӣ кор карданро мегӯӣ?"},
            {"speaker": "周太太", "zh": "先把茶和杯子放好，然后把冰箱里的西瓜拿出来。", "pinyin": "Xiān bǎ chá hé bēizi fàng hǎo, ránhòu bǎ bīngxiāng li de xīguā ná chūlai.", "uz": "Avval choy va piyolalarni qo'yib chiqing, keyin muzlatkichdagi tarvuzni olib chiqing.", "ru": "Сначала расставь чай и чашки, затем достань арбуз из холодильника.", "tj": "Аввал чой ва пиёлаҳоро ҷо ба ҷо кун, баъд тарбузро аз яхдон барор."},
            {"speaker": "周明", "zh": "太热了，我还是先把空调打开吧。", "pinyin": "Tài rè le, wǒ háishi xiān bǎ kōngtiáo dǎ kāi ba.", "uz": "Juda issiq, yaxshisi avval konditsionerni yoqay.", "ru": "Слишком жарко, я лучше сначала включу кондиционер.", "tj": "Хеле гарм аст, беҳтараш аввал кондитсионерро мекушоям."},
        ],
    },
    {
        "block_no": 2,
        "section_label": "课文 2",
        "scene_uz": "Telefonda",
        "scene_ru": "По телефону",
        "scene_tj": "Дар телефон",
        "word_nos": [5, 6],
        "grammar_nos": [1, 2],
        "dialogue": [
            {"speaker": "同事", "zh": "你在忙什么呢？刚才打你的手机你也不接。", "pinyin": "Nǐ zài máng shénme ne? Gāngcái dǎ nǐ de shǒujī nǐ yě bù jiē.", "uz": "Nima bilan bandsan? Hozirgina telefoningga qo'ng'iroq qildim, olmading.", "ru": "Чем ты занят? Я только что звонил тебе на мобильный, ты не ответил.", "tj": "Бо чӣ бандӣ? Ҳозир ба телефони дастият занг задам, нагирифтӣ."},
            {"speaker": "小刚", "zh": "对不起，我刚洗了个澡，没听见。有什么事吗？", "pinyin": "Duìbuqǐ, wǒ gāng xǐ le ge zǎo, méi tīngjiàn. Yǒu shénme shì ma?", "uz": "Kechirasiz, hozirgina cho'milgan edim, eshitmadim. Nima ish bor edi?", "ru": "Извини, я только что принимал душ и не услышал. Что случилось?", "tj": "Бубахшед, ҳозир оббозӣ карда будам, нашунидам. Чӣ кор буд?"},
            {"speaker": "同事", "zh": "我想问问你公司里的一些事情。", "pinyin": "Wǒ xiǎng wènwen nǐ gōngsī li de yìxiē shìqing.", "uz": "Kompaniyangizdagi ba'zi narsalarni so'ramoqchi edim.", "ru": "Я хотел спросить кое-что о твоей компании.", "tj": "Мехостам баъзе чизҳоро дар бораи ширкатат пурсам."},
            {"speaker": "小刚", "zh": "你先等一下，我去把电视关了。", "pinyin": "Nǐ xiān děng yíxià, wǒ qù bǎ diànshì guān le.", "uz": "Avval bir oz kut, televizorni o'chirib kelay.", "ru": "Подожди немного, я пойду выключу телевизор.", "tj": "Каме интизор шав, телевизорро хомӯш карда меоям."},
            {"speaker": "同事", "zh": "没关系，你先把电视节目看完吧，然后再给我回电话。", "pinyin": "Méi guānxi, nǐ xiān bǎ diànshì jiémù kàn wán ba, ránhòu zài gěi wǒ huí diànhuà.", "uz": "Hechqisi yo'q, avval televizor dasturini ko'rib tugat, keyin menga qayta qo'ng'iroq qil.", "ru": "Ничего, сначала досмотри телепередачу, потом перезвони мне.", "tj": "Ҳеҷ гап не, аввал барномаи телевизорро тамом кун, баъд ба ман занг зан."},
        ],
    },
    {
        "block_no": 3,
        "section_label": "课文 3",
        "scene_uz": "Xiaomingning uyida",
        "scene_ru": "У Сяомина дома",
        "scene_tj": "Дар хонаи Сяоминг",
        "word_nos": [7, 8, 9, 10, 11, 12, 13, 14],
        "grammar_nos": [1, 2, 3],
        "dialogue": [
            {"speaker": "同学", "zh": "今晚的月亮真漂亮，像白色的盘子一样。", "pinyin": "Jīn wǎn de yuèliang zhēn piàoliang, xiàng báisè de pánzi yíyàng.", "uz": "Bugungi oyning ko'rinishi juda chiroyli, oq tarelkaga o'xshaydi.", "ru": "Сегодняшняя луна очень красивая, как белая тарелка.", "tj": "Моҳи имшаб хеле зебо аст, мисли табақи сафед."},
            {"speaker": "小明", "zh": "是啊，外边也不刮风，我们坐在外边一边看月亮一边吃东西，怎么样？", "pinyin": "Shì a, wàibian yě bù guā fēng, wǒmen zuò zài wàibian yìbiān kàn yuèliang yìbiān chī dōngxi, zěnmeyàng?", "uz": "Ha, tashqarida shamol ham yo'q, tashqarida o'tirib oyga qarab ovqat yeymiz, qalay?", "ru": "Да, на улице и ветра нет. Посидим снаружи, будем смотреть на луну и есть, как тебе?", "tj": "Ҳа, берун шамол ҳам нест, берун нишаста ҳам моҳро бинему ҳам чизе бихӯрем, чӣ хел?"},
            {"speaker": "同学", "zh": "好啊，我先把桌椅搬出去，然后你把水果拿过来，我们听叔叔阿姨讲讲他们年轻时候的故事。", "pinyin": "Hǎo a, wǒ xiān bǎ zhuōyǐ bān chūqu, ránhòu nǐ bǎ shuǐguǒ ná guòlai, wǒmen tīng shūshu āyí jiǎngjiang tāmen niánqīng shíhou de gùshi.", "uz": "Yaxshi, men avval stol-stullarni tashqariga olib chiqaman, keyin sen mevalarni olib kel, amaki va xoladan yoshlikdagi hikoyalarini eshitamiz.", "ru": "Хорошо, я сначала вынесу стол и стулья, потом ты принеси фрукты, послушаем истории дяди и тёти о молодости.", "tj": "Хуб, ман аввал мизу курсиҳоро берун мебарам, баъд ту меваҳоро биёр, ҳикояҳои амаку холаро аз ҷавониашон мешунавем."},
            {"speaker": "小明", "zh": "太好了！记得给大山打个电话，让他马上过来。", "pinyin": "Tài hǎo le! Jìde gěi Dàshān dǎ ge diànhuà, ràng tā mǎshàng guòlai.", "uz": "Juda yaxshi! Dashanga telefon qilishni unutma, darhol kelsin.", "ru": "Отлично! Не забудь позвонить Дашаню, пусть сразу приходит.", "tj": "Хеле хуб! Ба Дашан занг заданро фаромӯш накун, бигзор фавран ояд."},
            {"speaker": "同学", "zh": "不用打了，你听外边的声音，一定是大山。", "pinyin": "Búyòng dǎ le, nǐ tīng wàibian de shēngyīn, yídìng shì Dàshān.", "uz": "Telefon qilish shart emas, tashqaridagi ovozni eshit, albatta Dashan.", "ru": "Не надо звонить, послушай звук снаружи, это наверняка Дашань.", "tj": "Занг задан лозим нест, овози берунро гӯш кун, албатта Дашан аст."},
        ],
    },
    {
        "block_no": 4,
        "section_label": "课文 4",
        "scene_uz": "Mevali guruch haqida matn",
        "scene_ru": "Текст о рисе с фруктами",
        "scene_tj": "Матн дар бораи биринҷи мевадор",
        "word_nos": [15, 16, 17],
        "grammar_nos": [1, 2],
        "dialogue": [
            {"speaker": "旁白", "zh": "你吃过水果饭吗？你在饭馆的菜单上见过水果饭吗？你想学着做水果饭吗？其实做水果饭很简单，先把米饭做好，然后再把一块块新鲜的水果放进去，水果饭就做好了。你可以做苹果饭、香蕉饭，要是你愿意，还可以做西瓜饭。多吃新鲜水果对身体好。", "pinyin": "Nǐ chī guo shuǐguǒ fàn ma? Nǐ zài fànguǎn de càidān shang jiàn guo shuǐguǒ fàn ma? Nǐ xiǎng xuézhe zuò shuǐguǒ fàn ma? Qíshí zuò shuǐguǒ fàn hěn jiǎndān, xiān bǎ mǐfàn zuò hǎo, ránhòu zài bǎ yí kuài kuài xīnxiān de shuǐguǒ fàng jìnqu, shuǐguǒ fàn jiù zuò hǎo le. Nǐ kěyǐ zuò píngguǒ fàn, xiāngjiāo fàn, yàoshi nǐ yuànyì, hái kěyǐ zuò xīguā fàn. Duō chī xīnxiān shuǐguǒ duì shēntǐ hǎo.", "uz": "Mevali guruch yeb ko'rganmisiz? Restoran menyusida mevali guruchni ko'rganmisiz? Mevali guruch tayyorlashni o'rganmoqchimisiz? Aslida mevali guruch tayyorlash juda oson: avval guruchni pishiring, keyin bo'lak-bo'lak yangi mevalarni ichiga soling, mevali guruch tayyor bo'ladi. Olmali guruch, bananli guruch qilishingiz mumkin, xohlasangiz tarvuzli guruch ham qilsa bo'ladi. Yangi mevalarni ko'p yeyish sog'liq uchun foydali.", "ru": "Вы ели фруктовый рис? Видели фруктовый рис в меню ресторана? Хотите научиться его готовить? На самом деле готовить фруктовый рис очень просто: сначала приготовьте рис, затем положите внутрь кусочки свежих фруктов, и фруктовый рис готов. Можно сделать рис с яблоком, с бананом, а если хотите, ещё и с арбузом. Есть больше свежих фруктов полезно для здоровья.", "tj": "Биринҷи мевадор хӯрдаед? Дар менюи тарабхона биринҷи мевадорро дидаед? Мехоҳед тайёр карданашро ёд гиред? Дар асл тайёр кардани он хеле содда аст: аввал биринҷро пазед, баъд пора-пора меваи тару тозаро дар он гузоред, биринҷи мевадор тайёр мешавад. Метавонед биринҷи себдор, банандор кунед, агар хоҳед, тарбуздор ҳам мешавад. Бисёр хӯрдани меваи тару тоза барои саломатӣ хуб аст."},
        ],
    },
]


_LESSON_15_VOCABULARY = [
    {"no": 1, "zh": "留学", "pinyin": "liú xué", "pos": "v.", "uz": "chet elda o'qimoq", "ru": "учиться за границей", "tj": "дар хориҷ таҳсил кардан"},
    {"no": 2, "zh": "水平", "pinyin": "shuǐpíng", "pos": "n.", "uz": "daraja, saviya", "ru": "уровень, стандарт", "tj": "сатҳ, дараҷа"},
    {"no": 3, "zh": "提高", "pinyin": "tí gāo", "pos": "v.", "uz": "oshirmoq, yaxshilamoq", "ru": "повышать, улучшать", "tj": "баланд кардан, беҳтар кардан"},
    {"no": 4, "zh": "练习", "pinyin": "liànxí", "pos": "n.", "uz": "mashq", "ru": "упражнение", "tj": "машқ"},
    {"no": 5, "zh": "完成", "pinyin": "wán chéng", "pos": "v.", "uz": "tugatmoq, yakunlamoq", "ru": "закончить, завершить", "tj": "тамом кардан"},
    {"no": 6, "zh": "句子", "pinyin": "jùzi", "pos": "n.", "uz": "gap, jumla", "ru": "предложение", "tj": "ҷумла"},
    {"no": 7, "zh": "其他", "pinyin": "qítā", "pos": "pron.", "uz": "boshqalar, qolganlari", "ru": "остальное, другие", "tj": "дигарон, боқимонда"},
    {"no": 8, "zh": "发", "pinyin": "fā", "pos": "v.", "uz": "yubormoq", "ru": "отправлять", "tj": "фиристодан"},
    {"no": 9, "zh": "要求", "pinyin": "yāoqiú", "pos": "n.", "uz": "talab", "ru": "требование", "tj": "талаб"},
    {"no": 10, "zh": "注意", "pinyin": "zhù yì", "pos": "v.", "uz": "e'tibor bermoq", "ru": "обращать внимание", "tj": "диққат додан"},
    {"no": 11, "zh": "上网", "pinyin": "shàng wǎng", "pos": "v.", "uz": "internetga kirmoq", "ru": "выходить в интернет", "tj": "ба интернет даромадан"},
    {"no": 12, "zh": "除了", "pinyin": "chúle", "pos": "prep.", "uz": "dan tashqari", "ru": "кроме", "tj": "ба ғайр аз"},
    {"no": 13, "zh": "新闻", "pinyin": "xīnwén", "pos": "n.", "uz": "yangiliklar", "ru": "новости", "tj": "хабарҳо"},
    {"no": 14, "zh": "花", "pinyin": "huā", "pos": "v.", "uz": "sarflamoq", "ru": "тратить", "tj": "сарф кардан"},
    {"no": 15, "zh": "极（了）", "pinyin": "jí (le)", "pos": "adv.", "uz": "juda, nihoyatda", "ru": "крайне, чрезвычайно", "tj": "ниҳоят"},
    {"no": 16, "zh": "节日", "pinyin": "jiérì", "pos": "n.", "uz": "bayram", "ru": "праздник", "tj": "ид"},
    {"no": 17, "zh": "举行", "pinyin": "jǔxíng", "pos": "v.", "uz": "o'tkazmoq", "ru": "проводить", "tj": "баргузор кардан"},
    {"no": 18, "zh": "世界", "pinyin": "shìjiè", "pos": "n.", "uz": "dunyo", "ru": "мир", "tj": "ҷаҳон"},
    {"no": 19, "zh": "街道", "pinyin": "jiēdào", "pos": "n.", "uz": "ko'cha", "ru": "улица", "tj": "кӯча"},
    {"no": 20, "zh": "各", "pinyin": "gè", "pos": "pron.", "uz": "har bir", "ru": "каждый", "tj": "ҳар"},
    {"no": 21, "zh": "文化", "pinyin": "wénhuà", "pos": "n.", "uz": "madaniyat", "ru": "культура", "tj": "фарҳанг"},
    {"no": 22, "zh": "小云", "pinyin": "Xiǎoyún", "pos": "proper noun", "uz": "Xiaoyun (ism)", "ru": "Сяоюнь (имя)", "tj": "Сяоюн (ном)"},
]


_LESSON_15_DIALOGUES = [
    {
        "block_no": 1,
        "section_label": "课文 1",
        "scene_uz": "Ofisda",
        "scene_ru": "В офисе",
        "scene_tj": "Дар идора",
        "word_nos": [1, 2, 3, 4, 5, 6, 7, 8],
        "grammar_nos": [1],
        "dialogue": [
            {"speaker": "大山", "zh": "老师，我来中国留学两年了，但是我的汉语水平提高得一点儿也不快啊。", "pinyin": "Lǎoshī, wǒ lái Zhōngguó liú xué liǎng nián le, dànshì wǒ de Hànyǔ shuǐpíng tí gāo de yìdiǎnr yě bù kuài a.", "uz": "Ustoz, Xitoyga o'qishga kelganimga ikki yil bo'ldi, lekin xitoy tili darajam deyarli tez oshmayapti.", "ru": "Учитель, я приехал в Китай учиться уже два года назад, но мой уровень китайского совсем не быстро растёт.", "tj": "Устод, ду сол шуд, ки ба Чин барои таҳсил омадам, аммо сатҳи забони чиниям тамоман зуд баланд намешавад."},
            {"speaker": "老师", "zh": "你每天认真学习，做练习、完成作业，一直不错啊。", "pinyin": "Nǐ měi tiān rènzhēn xuéxí, zuò liànxí, wán chéng zuòyè, yìzhí búcuò a.", "uz": "Sen har kuni jiddiy o'qiysan, mashq qilasan, uy vazifasini tugatasan, doim yaxshi-ku.", "ru": "Ты каждый день серьёзно учишься, делаешь упражнения, выполняешь домашнее задание, всё время неплохо.", "tj": "Ту ҳар рӯз ҷиддӣ мехонӣ, машқ мекунӣ, вазифаи хонагиро анҷом медиҳӣ, ҳамеша хуб аст."},
            {"speaker": "大山", "zh": "这是我昨天的作业，您帮我看看对不对？", "pinyin": "Zhè shì wǒ zuótiān de zuòyè, nín bāng wǒ kànkan duì bu duì?", "uz": "Bu kechagi uy vazifam, to'g'ri yoki yo'qligini ko'rib bera olasizmi?", "ru": "Это моё вчерашнее домашнее задание, посмотрите, правильно ли?", "tj": "Ин вазифаи хонагии дирӯзаам аст, мебинед дуруст аст ё не?"},
            {"speaker": "老师", "zh": "写得不错，除了这个句子意思有些不清楚外，其他都没什么问题。", "pinyin": "Xiě de búcuò, chúle zhè ge jùzi yìsi yǒuxiē bù qīngchu wài, qítā dōu méi shénme wèntí.", "uz": "Yaxshi yozilgan, faqat bu gapning ma'nosi biroz noaniq, qolganlarida muammo yo'q.", "ru": "Написано неплохо, кроме того, что смысл этого предложения немного неясен, с остальным проблем нет.", "tj": "Хуб навишта шудааст, ба ғайр аз он ки маънои ин ҷумла каме норавшан аст, боқимонда мушкил надорад."},
            {"speaker": "大山", "zh": "谢谢老师！", "pinyin": "Xièxie lǎoshī!", "uz": "Rahmat, ustoz!", "ru": "Спасибо, учитель!", "tj": "Ташаккур, устод!"},
            {"speaker": "老师", "zh": "以后有什么不明白的地方，可以给我打电话或者发电子邮件。", "pinyin": "Yǐhòu yǒu shénme bù míngbai de dìfang, kěyǐ gěi wǒ dǎ diànhuà huòzhě fā diànzǐ yóujiàn.", "uz": "Keyin tushunmagan joying bo'lsa, menga qo'ng'iroq qilishing yoki email yuborishing mumkin.", "ru": "Если потом что-то будет непонятно, можешь позвонить мне или отправить электронное письмо.", "tj": "Баъд агар чизе нофаҳмо бошад, метавонӣ ба ман занг занӣ ё почтаи электронӣ фиристӣ."},
        ],
    },
    {
        "block_no": 2,
        "section_label": "课文 2",
        "scene_uz": "Sinfda",
        "scene_ru": "В классе",
        "scene_tj": "Дар синф",
        "word_nos": [7, 9, 10, 22],
        "grammar_nos": [1],
        "dialogue": [
            {"speaker": "学生", "zh": "老师，除了小云，其他人都来了。", "pinyin": "Lǎoshī, chúle Xiǎoyún, qítā rén dōu lái le.", "uz": "Ustoz, Xiaoyundan tashqari hamma keldi.", "ru": "Учитель, кроме Сяоюнь, все пришли.", "tj": "Устод, ба ғайр аз Сяоюн ҳама омаданд."},
            {"speaker": "老师", "zh": "比赛马上就要开始了，小云怎么还没来？", "pinyin": "Bǐsài mǎshàng jiù yào kāishǐ le, Xiǎoyún zěnme hái méi lái?", "uz": "Musobaqa hozir boshlanadi, Xiaoyun nega hali kelmadi?", "ru": "Соревнование вот-вот начнётся, почему Сяоюнь ещё не пришла?", "tj": "Мусобиқа ҳозир сар мешавад, чаро Сяоюн ҳоло наомад?"},
            {"speaker": "学生", "zh": "刚才给她打电话了，她在路上呢。", "pinyin": "Gāngcái gěi tā dǎ diànhuà le, tā zài lùshang ne.", "uz": "Hozirgina unga qo'ng'iroq qildim, u yo'lda.", "ru": "Я только что звонил ей, она в пути.", "tj": "Ҳозир ба ӯ занг задам, дар роҳ аст."},
            {"speaker": "老师", "zh": "不等她了，我先给大家讲讲这次比赛的要求和一些需要注意的地方。", "pinyin": "Bù děng tā le, wǒ xiān gěi dàjiā jiǎngjiang zhè cì bǐsài de yāoqiú hé yìxiē xūyào zhù yì de dìfang.", "uz": "Uni kutmaymiz, avval hammaga bu musobaqaning talablarini va e'tibor berish kerak bo'lgan joylarini tushuntirib beraman.", "ru": "Не будем ждать её, сначала я расскажу всем требования этого соревнования и моменты, на которые нужно обратить внимание.", "tj": "Ӯро интизор намешавем, аввал ба ҳама талабҳои ин мусобиқа ва ҷойҳои лозими диққатро мефаҳмонам."},
            {"speaker": "学生", "zh": "老师，您放心，今天的比赛我们一定能拿第一。", "pinyin": "Lǎoshī, nín fàngxīn, jīntiān de bǐsài wǒmen yídìng néng ná dì yī.", "uz": "Ustoz, xavotir olmang, bugungi musobaqada albatta birinchi o'rinni olamiz.", "ru": "Учитель, не волнуйтесь, сегодня мы обязательно займём первое место.", "tj": "Устод, хотирҷамъ бошед, дар мусобиқаи имрӯз мо ҳатман ҷойи аввалро мегирем."},
        ],
    },
    {
        "block_no": 3,
        "section_label": "课文 3",
        "scene_uz": "Dam olish xonasida",
        "scene_ru": "В комнате отдыха",
        "scene_tj": "Дар утоқи истироҳат",
        "word_nos": [11, 12, 13, 14, 15],
        "grammar_nos": [1, 3],
        "dialogue": [
            {"speaker": "同事", "zh": "现在用电脑上网真方便啊！", "pinyin": "Xiànzài yòng diànnǎo shàng wǎng zhēn fāngbiàn a!", "uz": "Hozir kompyuterda internetga kirish juda qulay!", "ru": "Сейчас пользоваться интернетом на компьютере очень удобно!", "tj": "Ҳоло бо компютер ба интернет даромадан хеле қулай аст!"},
            {"speaker": "小刚", "zh": "是啊，除了看新闻，人们还可以在网上听歌、看电影、买东西。", "pinyin": "Shì a, chúle kàn xīnwén, rénmen hái kěyǐ zài wǎngshang tīng gē, kàn diànyǐng, mǎi dōngxi.", "uz": "Ha, yangilik ko'rishdan tashqari, odamlar internetda qo'shiq tinglash, film ko'rish va narsa sotib olishlari ham mumkin.", "ru": "Да, кроме просмотра новостей, люди могут в интернете слушать песни, смотреть фильмы и покупать вещи.", "tj": "Ҳа, ба ғайр аз дидани хабарҳо, одамон дар интернет суруд мешунаванд, кино мебинанд ва чиз мехаранд."},
            {"speaker": "同事", "zh": "对了，你从网上买的那件衣服呢？怎么没见你穿？", "pinyin": "Duì le, nǐ cóng wǎngshang mǎi de nà jiàn yīfu ne? Zěnme méi jiàn nǐ chuān?", "uz": "Aytgancha, internetdan olgan o'sha kiyiming-chi? Nega kiyganingni ko'rmadim?", "ru": "Кстати, где та одежда, которую ты купил в интернете? Почему я не видел, чтобы ты её носил?", "tj": "Дар омади гап, он либосе, ки аз интернет харидӣ, куҷост? Чаро туро дар он надидам?"},
            {"speaker": "小刚", "zh": "那件衣服我穿着有点儿小，给我弟弟了。", "pinyin": "Nà jiàn yīfu wǒ chuānzhe yǒudiǎnr xiǎo, gěi wǒ dìdi le.", "uz": "U kiyim menga biroz kichik bo'ldi, ukamga berdim.", "ru": "Эта одежда на мне была немного мала, я отдал её младшему брату.", "tj": "Он либос ба ман каме хурд буд, ба додарам додам."},
            {"speaker": "同事", "zh": "他满意吗？", "pinyin": "Tā mǎnyì ma?", "uz": "U rozi bo'ldimi?", "ru": "Он доволен?", "tj": "Ӯ қаноатманд аст?"},
            {"speaker": "小刚", "zh": "不用花钱，还有新衣服穿，他满意极了。", "pinyin": "Búyòng huā qián, hái yǒu xīn yīfu chuān, tā mǎnyì jí le.", "uz": "Pul sarflamaydi, yangi kiyim ham kiyadi, u nihoyatda mamnun.", "ru": "Не нужно тратить деньги, и есть новая одежда, он очень доволен.", "tj": "Пул сарф намекунад, либоси нав ҳам мепӯшад, хеле қаноатманд аст."},
        ],
    },
    {
        "block_no": 4,
        "section_label": "课文 4",
        "scene_uz": "Pivo bayrami haqida matn",
        "scene_ru": "Текст о пивном фестивале",
        "scene_tj": "Матн дар бораи ҷашни пиво",
        "word_nos": [16, 17, 18, 19, 20, 21],
        "grammar_nos": [1, 2],
        "dialogue": [
            {"speaker": "旁白", "zh": "除了春节、中秋节以外，啤酒节也是这里很重要的一个节日。这个地方每年夏天都要举行一次啤酒节。在啤酒节上，你可以喝到世界上不同地方的啤酒。除了喝啤酒，你还可以在街道两边看到世界上不同地方的歌舞，你想不想了解世界各个地方的啤酒文化？来这里的啤酒节看看吧。", "pinyin": "Chúle Chūnjié, Zhōngqiū Jié yǐwài, píjiǔ jié yě shì zhèlǐ hěn zhòngyào de yí ge jiérì. Zhège dìfang měi nián xiàtiān dōu yào jǔxíng yí cì píjiǔ jié. Zài píjiǔ jié shang, nǐ kěyǐ hēdào shìjiè shang bùtóng dìfang de píjiǔ. Chúle hē píjiǔ, nǐ hái kěyǐ zài jiēdào liǎng biān kàndào shìjiè shang bùtóng dìfang de gēwǔ, nǐ xiǎng bu xiǎng liǎojiě shìjiè gè ge dìfang de píjiǔ wénhuà? Lái zhèlǐ de píjiǔ jié kànkan ba.", "uz": "Bahor bayrami va O'rta kuz bayramidan tashqari, pivo festivali ham bu yerda juda muhim bayram. Bu joyda har yili yozda bir marta pivo festivali o'tkaziladi. Pivo festivalida dunyoning turli joylaridagi pivolarni ichib ko'rishingiz mumkin. Pivo ichishdan tashqari, ko'chaning ikki tomonida dunyoning turli joylaridagi qo'shiq va raqslarni ham ko'rishingiz mumkin. Dunyoning turli joylaridagi pivo madaniyatini bilishni xohlaysizmi? Bu yerdagi pivo festivaliga kelib ko'ring.", "ru": "Кроме Праздника весны и Праздника середины осени, пивной фестиваль здесь тоже очень важный праздник. В этом месте каждое лето проводят пивной фестиваль. На фестивале можно попробовать пиво из разных мест мира. Кроме пива, по обе стороны улицы можно увидеть песни и танцы разных стран. Хотите узнать пивную культуру разных мест мира? Приезжайте посмотреть местный пивной фестиваль.", "tj": "Ба ғайр аз Иди баҳор ва Иди миёнаи тирамоҳ, ҷашни пиво ҳам дар ин ҷо иди хеле муҳим аст. Ин ҷо ҳар тобистон як бор ҷашни пиво баргузор мешавад. Дар ҷашни пиво метавонед пивои ҷойҳои гуногуни ҷаҳонро бинӯшед. Ба ғайр аз пиво нӯшидан, дар ду тарафи кӯча метавонед суруду рақси ҷойҳои гуногуни ҷаҳонро бинед. Мехоҳед фарҳанги пивои ҷойҳои гуногуни ҷаҳонро фаҳмед? Ба ҷашни пивои ин ҷо омада бинед."},
        ],
    },
]


_LESSON_16_VOCABULARY = [
    {"no": 1, "zh": "城市", "pinyin": "chéngshì", "pos": "n.", "uz": "shahar", "ru": "город", "tj": "шаҳр"},
    {"no": 2, "zh": "如果", "pinyin": "rúguǒ", "pos": "conj.", "uz": "agar", "ru": "если", "tj": "агар"},
    {"no": 3, "zh": "认为", "pinyin": "rènwéi", "pos": "v.", "uz": "deb o'ylamoq, hisoblamoq", "ru": "считать, полагать", "tj": "фикр кардан, ҳисобидан"},
    {"no": 4, "zh": "皮鞋", "pinyin": "píxié", "pos": "n.", "uz": "charm tufli", "ru": "кожаная обувь", "tj": "пойафзоли чармӣ"},
    {"no": 5, "zh": "帽子", "pinyin": "màozi", "pos": "n.", "uz": "shlyapa, bosh kiyim", "ru": "шапка, шляпа", "tj": "кулоҳ"},
    {"no": 6, "zh": "长", "pinyin": "zhǎng", "pos": "v.", "uz": "o'smoq, ulg'aymoq", "ru": "расти, развиваться", "tj": "калон шудан, рушд кардан"},
    {"no": 7, "zh": "可爱", "pinyin": "kě'ài", "pos": "adj.", "uz": "yoqimli, shirin", "ru": "милый, очаровательный", "tj": "дилрабо, ширин"},
    {"no": 8, "zh": "米", "pinyin": "mǐ", "pos": "n.", "uz": "metr", "ru": "метр", "tj": "метр"},
    {"no": 9, "zh": "公斤", "pinyin": "gōngjīn", "pos": "n.", "uz": "kilogramm", "ru": "килограмм", "tj": "килограмм"},
    {"no": 10, "zh": "鼻子", "pinyin": "bízi", "pos": "n.", "uz": "burun", "ru": "нос", "tj": "бинӣ"},
    {"no": 11, "zh": "头发", "pinyin": "tóufa", "pos": "n.", "uz": "soch", "ru": "волосы", "tj": "мӯй"},
    {"no": 12, "zh": "检查", "pinyin": "jiǎnchá", "pos": "v.", "uz": "tekshirmoq, ko'rikdan o'tkazmoq", "ru": "проверять, осматривать", "tj": "санҷидан, муоина кардан"},
    {"no": 13, "zh": "刷牙", "pinyin": "shuā yá", "pos": "v.", "uz": "tish yuvmoq", "ru": "чистить зубы", "tj": "дандон шустан"},
    {"no": 14, "zh": "关系", "pinyin": "guānxì", "pos": "n.", "uz": "munosabat, aloqa", "ru": "отношение, связь", "tj": "муносибат, робита"},
    {"no": 15, "zh": "别人", "pinyin": "biérén", "pos": "n.", "uz": "boshqa odamlar", "ru": "другие люди", "tj": "дигарон"},
    {"no": 16, "zh": "词语", "pinyin": "cíyǔ", "pos": "n.", "uz": "so'z, ibora", "ru": "слово, выражение", "tj": "калима, ибора"},
]


_LESSON_16_DIALOGUES = [
    {
        "block_no": 1,
        "section_label": "课文 1",
        "scene_uz": "Kompaniyada",
        "scene_ru": "В компании",
        "scene_tj": "Дар ширкат",
        "word_nos": [1, 2, 3],
        "grammar_nos": [1, 2],
        "dialogue": [
            {"speaker": "小丽", "zh": "我不喜欢一直住在同一个城市，想去其他城市看一看。", "pinyin": "Wǒ bù xǐhuan yìzhí zhù zài tóng yí ge chéngshì, xiǎng qù qítā chéngshì kàn yi kàn.", "uz": "Men doim bir shaharda yashashni yoqtirmayman, boshqa shaharlarga borib ko'rmoqchiman.", "ru": "Мне не нравится всё время жить в одном городе, хочу съездить посмотреть другие города.", "tj": "Ман ҳамеша дар як шаҳр зиндагӣ карданро дӯст намедорам, мехоҳам ба шаҳрҳои дигар рафта бинам."},
            {"speaker": "周明", "zh": "我年轻的时候也这么想，但是那时候没有钱，如果有钱，就去了。", "pinyin": "Wǒ niánqīng de shíhou yě zhème xiǎng, dànshì nà shíhou méiyǒu qián, rúguǒ yǒu qián, jiù qù le.", "uz": "Men yoshligimda ham shunday o'ylardim, lekin o'shanda pul yo'q edi, agar pul bo'lganida, ketardim.", "ru": "Когда я был молодым, тоже так думал, но тогда не было денег. Если бы были деньги, я бы поехал.", "tj": "Ман дар ҷавонӣ ҳам ҳамин тавр фикр мекардам, аммо он вақт пул набуд, агар пул мебуд, мерафтам."},
            {"speaker": "小丽", "zh": "那您现在为什么不去？", "pinyin": "Nà nín xiànzài wèi shénme bù qù?", "uz": "Unda hozir nega bormaysiz?", "ru": "Тогда почему вы сейчас не едете?", "tj": "Пас ҳоло чаро намеравед?"},
            {"speaker": "周明", "zh": "现在钱不是问题了，主要是没有时间。", "pinyin": "Xiànzài qián bú shì wèntí le, zhǔyào shì méiyǒu shíjiān.", "uz": "Hozir pul muammo emas, asosiysi vaqt yo'q.", "ru": "Сейчас деньги уже не проблема, главное - нет времени.", "tj": "Ҳоло пул мушкил нест, асосан вақт нест."},
            {"speaker": "小丽", "zh": "我认为现在您有时间也不会出去玩儿。", "pinyin": "Wǒ rènwéi xiànzài nín yǒu shíjiān yě bú huì chūqu wánr.", "uz": "Menimcha, hozir vaqtingiz bo'lsa ham sayrga chiqmasdingiz.", "ru": "Я думаю, что сейчас, даже если у вас будет время, вы не поедете отдыхать.", "tj": "Ба фикрам, ҳоло агар вақт ҳам дошта бошед, берун истироҳат кардан намеравед."},
            {"speaker": "周明", "zh": "你说得对，我现在累得下了班就想睡觉。", "pinyin": "Nǐ shuō de duì, wǒ xiànzài lèi de xià le bān jiù xiǎng shuìjiào.", "uz": "To'g'ri aytding, men hozir shunchalik charchaganmanki, ishdan chiqqach faqat uxlashni xohlayman.", "ru": "Ты права, я сейчас так устаю, что после работы сразу хочу спать.", "tj": "Дуруст гуфтӣ, ман ҳоло чунон хастаам, ки баъди кор танҳо хоб кардан мехоҳам."},
        ],
    },
    {
        "block_no": 2,
        "section_label": "课文 2",
        "scene_uz": "Hamkasb uyida",
        "scene_ru": "У коллеги дома",
        "scene_tj": "Дар хонаи ҳамкор",
        "word_nos": [4, 5, 6, 7, 8, 9, 10, 11],
        "grammar_nos": [2, 3],
        "dialogue": [
            {"speaker": "同事", "zh": "谢谢你们来看我女儿。你送的小皮鞋和小帽子真漂亮！", "pinyin": "Xièxie nǐmen lái kàn wǒ nǚ'ér. Nǐ sòng de xiǎo píxié hé xiǎo màozi zhēn piàoliang!", "uz": "Qizimni ko'rgani kelganingiz uchun rahmat. Siz sovg'a qilgan kichik charm tufli va kichik shlyapa juda chiroyli!", "ru": "Спасибо, что пришли посмотреть мою дочь. Маленькие кожаные туфельки и шапочка, которые ты подарила, очень красивые!", "tj": "Ташаккур, ки духтарамро дидан омадед. Пойафзоли чармии хурд ва кулоҳи хурде, ки ту додӣ, хеле зебо аст!"},
            {"speaker": "小丽", "zh": "别客气，你女儿长得白白的、胖胖的，真可爱！现在多高了？", "pinyin": "Bié kèqi, nǐ nǚ'ér zhǎng de báibái de, pàngpàng de, zhēn kě'ài! Xiànzài duō gāo le?", "uz": "Arzimaydi, qizingiz oppoq, dumaloqqina bo'lib o'syapti, juda yoqimli! Hozir bo'yi qancha?", "ru": "Не за что, ваша дочь такая беленькая и пухленькая, очень милая! Какого она сейчас роста?", "tj": "Марҳамат, духтаратон сафедча ва фарбеҳча калон мешавад, хеле дилрабо! Ҳоло қаддаш чанд аст?"},
            {"speaker": "同事", "zh": "快1米了，25公斤。", "pinyin": "Kuài yì mǐ le, èrshíwǔ gōngjīn.", "uz": "Deyarli bir metr, 25 kilogramm.", "ru": "Почти один метр, 25 килограммов.", "tj": "Қариб як метр, 25 килограмм."},
            {"speaker": "小丽", "zh": "你看她鼻子小小的，头发黑黑的，长得像谁？", "pinyin": "Nǐ kàn tā bízi xiǎoxiǎo de, tóufa hēihēi de, zhǎng de xiàng shéi?", "uz": "Qarang, burni kichkinagina, sochi qop-qora, kimga o'xshab o'syapti?", "ru": "Посмотри, у неё маленький носик, чёрные волосы, на кого она похожа?", "tj": "Бин, биниаш хурдча, мӯяш сиёҳча, ба кӣ монанд калон мешавад?"},
            {"speaker": "同事", "zh": "像她爸爸，刚出生时她爸爸高兴得一个晚上都没睡着。", "pinyin": "Xiàng tā bàba, gāng chūshēng shí tā bàba gāoxìng de yí ge wǎnshang dōu méi shuì zháo.", "uz": "Dadasiga o'xshaydi, endi tug'ilganida dadasi xursandligidan butun kecha uxlay olmagan.", "ru": "На её папу. Когда она только родилась, её папа так радовался, что всю ночь не мог уснуть.", "tj": "Ба падараш монанд. Вақте нав таваллуд шуд, падараш аз хурсандӣ тамоми шаб хоб карда натавонист."},
        ],
    },
    {
        "block_no": 3,
        "section_label": "课文 3",
        "scene_uz": "Kompaniyada",
        "scene_ru": "В компании",
        "scene_tj": "Дар ширкат",
        "word_nos": [12, 13],
        "grammar_nos": [1],
        "dialogue": [
            {"speaker": "小刚", "zh": "我的牙还是很疼。", "pinyin": "Wǒ de yá háishi hěn téng.", "uz": "Tishim hali ham juda og'riyapti.", "ru": "У меня зуб всё ещё сильно болит.", "tj": "Дандонам ҳоло ҳам сахт дард мекунад."},
            {"speaker": "同事", "zh": "如果不舒服，就去医院检查一下吧。", "pinyin": "Rúguǒ bù shūfu, jiù qù yīyuàn jiǎnchá yíxià ba.", "uz": "Agar noqulay bo'lsa, kasalxonaga borib tekshirtir.", "ru": "Если плохо себя чувствуешь, сходи в больницу провериться.", "tj": "Агар нороҳат бошӣ, ба беморхона рафта як бор муоина кун."},
            {"speaker": "小刚", "zh": "检查好几次了，但是没什么用。", "pinyin": "Jiǎnchá hǎo jǐ cì le, dànshì méi shénme yòng.", "uz": "Bir necha marta tekshirtirdim, lekin foydasi bo'lmadi.", "ru": "Проверял уже несколько раз, но толку нет.", "tj": "Чанд бор муоина кардам, аммо фоида надошт."},
            {"speaker": "同事", "zh": "大夫怎么说的？", "pinyin": "Dàifu zěnme shuō de?", "uz": "Shifokor nima dedi?", "ru": "Что сказал врач?", "tj": "Духтур чӣ гуфт?"},
            {"speaker": "小刚", "zh": "每次医生都告诉我，回家好好儿刷牙。", "pinyin": "Měi cì yīshēng dōu gàosu wǒ, huí jiā hǎohāor shuā yá.", "uz": "Har safar shifokor uyga borib tishimni yaxshilab yuvishimni aytadi.", "ru": "Каждый раз врач говорит мне вернуться домой и хорошенько чистить зубы.", "tj": "Ҳар дафъа духтур мегӯяд, ки ба хона баргашта дандонҳоро хуб шуям."},
        ],
    },
    {
        "block_no": 4,
        "section_label": "课文 4",
        "scene_uz": "Insonlar munosabati haqida matn",
        "scene_ru": "Текст об отношениях между людьми",
        "scene_tj": "Матн дар бораи муносибати одамон",
        "word_nos": [14, 15, 16],
        "grammar_nos": [1, 2, 3],
        "dialogue": [
            {"speaker": "旁白", "zh": "很多人都觉得现在人和人的关系冷冷的，这可能是因为工作太忙，忙得没时间跟别人见面，累得不愿意和别人多说话。其实，我们应该多对别人笑笑，说话时如果能多用一些“您好”“谢谢”这样的词语，和别人的关系就会变得更好。", "pinyin": "Hěn duō rén dōu juéde xiànzài rén hé rén de guānxì lěnglěng de, zhè kěnéng shì yīnwèi gōngzuò tài máng, máng de méi shíjiān gēn biérén jiàn miàn, lèi de bù yuànyì hé biérén duō shuō huà. Qíshí, wǒmen yīnggāi duō duì biérén xiàoxiao, shuō huà shí rúguǒ néng duō yòng yìxiē 'nín hǎo' 'xièxie' zhèyàng de cíyǔ, hé biérén de guānxì jiù huì biàn de gèng hǎo.", "uz": "Ko'p odamlar hozir insonlar o'rtasidagi munosabatlar sovuqlashgan deb o'ylaydi. Buning sababi ish juda bandligi bo'lishi mumkin: bandlikdan boshqalar bilan uchrashishga vaqt yo'q, charchoqdan boshqalar bilan ko'p gaplashishni xohlamaydi. Aslida, biz boshqalarga ko'proq tabassum qilishimiz kerak. Gaplashayotganda “您好”, “谢谢” kabi so'zlarni ko'proq ishlatsak, boshqalar bilan munosabatimiz yanada yaxshilanadi.", "ru": "Многие считают, что сейчас отношения между людьми стали холодными. Возможно, это из-за того, что работа слишком занятая: из-за занятости нет времени встречаться с другими, из-за усталости не хочется много разговаривать. На самом деле нам следует чаще улыбаться другим. Если в разговоре чаще использовать такие выражения, как “您好” и “谢谢”, отношения с другими станут лучше.", "tj": "Бисёр одамон фикр мекунанд, ки ҳоло муносибати байни одамон сард шудааст. Ин шояд аз он бошад, ки кор хеле банд аст: аз бандӣ вақт барои вохӯрӣ бо дигарон нест, аз хастагӣ бо дигарон зиёд гап задан намехоҳанд. Дар асл, мо бояд ба дигарон бештар табассум кунем. Агар ҳангоми гап задан бештар калимаҳои монанди “您好” ва “谢谢”-ро истифода барем, муносибат бо дигарон беҳтар мешавад."},
        ],
    },
]


_PDF_MATERIALS = {
    1: (_LESSON_1_VOCABULARY, _LESSON_1_DIALOGUES),
    2: (_LESSON_2_VOCABULARY, _LESSON_2_DIALOGUES),
    3: (_LESSON_3_VOCABULARY, _LESSON_3_DIALOGUES),
    4: (_LESSON_4_VOCABULARY, _LESSON_4_DIALOGUES),
    5: (_LESSON_5_VOCABULARY, _LESSON_5_DIALOGUES),
    6: (_LESSON_6_VOCABULARY, _LESSON_6_DIALOGUES),
    7: (_LESSON_7_VOCABULARY, _LESSON_7_DIALOGUES),
    8: (_LESSON_8_VOCABULARY, _LESSON_8_DIALOGUES),
    9: (_LESSON_9_VOCABULARY, _LESSON_9_DIALOGUES),
    10: (_LESSON_10_VOCABULARY, _LESSON_10_DIALOGUES),
    11: (_LESSON_11_VOCABULARY, _LESSON_11_DIALOGUES),
    12: (_LESSON_12_VOCABULARY, _LESSON_12_DIALOGUES),
    13: (_LESSON_13_VOCABULARY, _LESSON_13_DIALOGUES),
    14: (_LESSON_14_VOCABULARY, _LESSON_14_DIALOGUES),
    15: (_LESSON_15_VOCABULARY, _LESSON_15_DIALOGUES),
    16: (_LESSON_16_VOCABULARY, _LESSON_16_DIALOGUES),
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
