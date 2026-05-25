import copy

from scripts.hsk4_upper_pdf_materials import (
    _exercise_payload,
    _homework_payload,
    _j,
    _mini_homework,
    _mini_quiz,
    _word_by_no,
)


def _word(no, zh, pinyin, pos, uz, ru, tj):
    return {"no": no, "zh": zh, "pinyin": pinyin, "pos": pos, "uz": uz, "ru": ru, "tj": tj}


def _line(speaker, zh, pinyin, uz, ru, tj):
    return {"speaker": speaker, "zh": zh, "pinyin": pinyin, "uz": uz, "ru": ru, "tj": tj}


def _grammar(no, title_zh, title_uz, title_ru, title_tj, rule_uz, rule_ru, rule_tj, example_zh, example_pinyin, example_uz, example_ru, example_tj):
    return {
        "no": no,
        "title_zh": title_zh,
        "title_uz": title_uz,
        "title_ru": title_ru,
        "title_tj": title_tj,
        "rule_uz": rule_uz,
        "rule_ru": rule_ru,
        "rule_tj": rule_tj,
        "formula": title_zh,
        "examples": [
            {
                "zh": example_zh,
                "pinyin": example_pinyin,
                "uz": example_uz,
                "ru": example_ru,
                "tj": example_tj,
            }
        ],
    }


HSK4_LOWER_PDF_MATERIALS = {
    11: {
        "title": "读书好，读好书，好读书",
        "goal": {
            "uz": "o'qish odati, imtihon va kitob tanlash haqida gapirish; 连, 否则, 无论, 然而 va 同时 grammatikalarini ishlatish",
            "ru": "говорить о чтении, экзаменах и выборе книг; использовать 连, 否则, 无论, 然而 и 同时",
            "tj": "дар бораи мутолиа, имтиҳон ва интихоби китоб гуфтугӯ кардан; истифодаи 连, 否则, 无论, 然而 ва 同时",
        },
        "intro_text": {
            "uz": "Bu darsda xitoycha gazeta o'qish, imtihonda vaqtni taqsimlash, kitob o'qish foydasi va o'qish odatini shakllantirishni o'rganasiz.",
            "ru": "В этом уроке вы научитесь говорить о чтении китайских газет, распределении времени на экзамене, пользе чтения и привычке читать.",
            "tj": "Дар ин дарс хондани рӯзномаи чинӣ, тақсими вақт дар имтиҳон, фоидаи мутолиа ва одати китобхониро меомӯзед.",
        },
        "vocabulary": [
            _word(1, "流利", "liúlì", "adj.", "ravon", "беглый, свободный", "равон"),
            _word(2, "厉害", "lìhai", "adj.", "zo'r, kuchli", "сильный, впечатляющий", "зӯр, қавӣ"),
            _word(3, "语法", "yǔfǎ", "n.", "grammatika", "грамматика", "грамматика"),
            _word(4, "准确", "zhǔnquè", "adj.", "aniq, to'g'ri", "точный, правильный", "дақиқ, дуруст"),
            _word(5, "词语", "cíyǔ", "n.", "so'z, ibora", "слово, выражение", "калима, ибора"),
            _word(6, "连", "lián", "prep.", "hatto", "даже", "ҳатто"),
            _word(7, "阅读", "yuèdú", "v.", "o'qimoq", "читать", "мутолиа кардан"),
            _word(8, "来得及", "láidejí", "v.", "ulgurmoq", "успеть", "вақт расидан"),
            _word(9, "复杂", "fùzá", "adj.", "murakkab", "сложный", "мураккаб"),
            _word(10, "只好", "zhǐhǎo", "adv.", "majbur bo'lmoq", "вынужденно", "маҷбурона"),
            _word(11, "填空", "tián kòng", "v.", "bo'sh joyni to'ldirmoq", "заполнять пропуски", "ҷойи холиро пур кардан"),
            _word(12, "猜", "cāi", "v.", "taxmin qilmoq", "угадывать", "тахмин кардан"),
            _word(13, "否则", "fǒuzé", "conj.", "aks holda", "иначе", "акс ҳол"),
            _word(14, "客厅", "kètīng", "n.", "mehmonxona, zal", "гостиная", "меҳмонхона"),
            _word(15, "无论", "wúlùn", "conj.", "qanday bo'lmasin", "независимо от", "новобаста аз"),
            _word(16, "杂志", "zázhì", "n.", "jurnal", "журнал", "маҷалла"),
            _word(17, "著名", "zhùmíng", "adj.", "mashhur", "известный", "машҳур"),
            _word(18, "页", "yè", "m.", "sahifa", "страница", "саҳифа"),
            _word(19, "增加", "zēngjiā", "v.", "oshirmoq, ko'paytirmoq", "увеличивать", "зиёд кардан"),
            _word(20, "文章", "wénzhāng", "n.", "maqola, matn", "статья, текст", "мақола, матн"),
            _word(21, "之", "zhī", "part.", "otlarni bog'lovchi zarracha", "книжная частица связи", "зарраи пайвандӣ"),
            _word(22, "内容", "nèiróng", "n.", "mazmun", "содержание", "мазмун"),
            _word(23, "然而", "rán'ér", "conj.", "biroq, ammo", "однако", "аммо"),
            _word(24, "看法", "kànfǎ", "n.", "fikr, qarash", "мнение, взгляд", "фикр, назар"),
            _word(25, "相同", "xiāngtóng", "adj.", "bir xil", "одинаковый", "якхела"),
            _word(26, "顺序", "shùnxù", "n.", "tartib", "порядок", "тартиб"),
            _word(27, "表示", "biǎoshì", "v.", "bildirmoq, ifodalamoq", "выражать", "ифода кардан"),
            _word(28, "养成", "yǎngchéng", "v.", "shakllantirmoq", "вырабатывать", "ташаккул додан"),
            _word(29, "同时", "tóngshí", "conj.", "bir vaqtda, shu bilan birga", "одновременно", "ҳамзамон"),
            _word(30, "精彩", "jīngcǎi", "adj.", "ajoyib", "замечательный", "аҷоиб"),
        ],
        "grammar": [
            _grammar(1, "连……也/都……", "hatto...ham", "даже...тоже", "ҳатто...ҳам", "Ekstremal misolni ajratib, ta'kidlaydi.", "Выделяет крайний пример для усиления.", "Ҳолати ифротиро барои таъкид ҷудо мекунад.", "你太厉害了！连中文报纸都看得懂。", "Nǐ tài lìhai le! Lián Zhōngwén bàozhǐ dōu kàn de dǒng.", "Juda zo'rsan! Hatto xitoycha gazetani ham tushunib o'qiyapsan.", "Ты молодец! Даже китайские газеты понимаешь.", "Ту зӯрӣ! Ҳатто рӯзномаи чиниро мефаҳмӣ."),
            _grammar(2, "否则", "aks holda", "иначе", "акс ҳол", "Oldingi shart bajarilmasa bo'ladigan natijani bildiradi.", "Показывает результат, если предыдущее условие не выполнено.", "Натиҷаи иҷро нашудани шарти пешинаро нишон медиҳад.", "看來要想考好，不但要认真复习，还得注意考试的方法，否则，会做的题也没时间做了。", "Kànlái yào xiǎng kǎo hǎo, bùdàn yào rènzhēn fùxí, hái děi zhùyì kǎoshì de fāngfǎ, fǒuzé, huì zuò de tí yě méi shíjiān zuò le.", "Yaxshi topshirish uchun nafaqat takrorlash, balki imtihon usuliga ham e'tibor kerak, aks holda bilgan savolga ham vaqt qolmaydi.", "Чтобы сдать хорошо, нужно не только повторять, но и следить за методом экзамена, иначе не хватит времени даже на знакомые задания.", "Барои хуб супоридан на танҳо такрор, балки усули имтиҳон ҳам муҳим аст, вагарна ба саволҳои медониста ҳам вақт намерасад."),
            _grammar(3, "无论……都/也……", "qanday bo'lmasin", "независимо от", "новобаста аз", "Shart qanday bo'lishidan qat'i nazar, natija o'zgarmaydi.", "Результат не меняется при любом условии.", "Натиҷа новобаста аз шарт тағйир намеёбад.", "无论是普通杂志，还是著名小说，只要打开它们，就会发现，世界上有那么多有意思的事情。", "Wúlùn shì pǔtōng zázhì, háishi zhùmíng xiǎoshuō, zhǐyào dǎkāi tāmen, jiù huì fāxiàn, shìjiè shang yǒu nàme duō yǒu yìsi de shìqing.", "Oddiy jurnalmi yoki mashhur romanmi, ochsangiz dunyoda juda ko'p qiziq narsalar borligini ko'rasiz.", "Будь то обычный журнал или известный роман, откроешь и увидишь, сколько в мире интересного.", "Маҷаллаи одӣ бошад ё романи машҳур, кушоӣ мефаҳмӣ, ки дар дунё чӣ қадар чизҳои ҷолиб ҳаст."),
            _grammar(4, "然而", "biroq, ammo", "однако", "аммо", "Ikkinchi yarim gap boshida kelib, burilish bildiradi.", "Вводит поворот мысли во второй части предложения.", "Дар қисми дуюм гардиши фикрро меорад.", "然而，你不能完全相信书本上的内容，要有自己的看法和判断。", "Rán'ér, nǐ bù néng wánquán xiāngxìn shūběn shang de nèiróng, yào yǒu zìjǐ de kànfǎ hé pànduàn.", "Biroq kitobdagi mazmunga butunlay ishonib qolmasdan, o'z fikr va hukmingiz bo'lishi kerak.", "Однако нельзя полностью верить содержанию книг, нужно иметь своё мнение и суждение.", "Аммо набояд ба мазмуни китоб пурра бовар кард, фикр ва баҳодиҳии худ лозим аст."),
            _grammar(5, "同时", "bir vaqtda; shu bilan birga", "одновременно; при этом", "ҳамзамон; дар айни вақт", "Qo'shimcha parallel natija yoki bir vaqtdagi holatni bog'laydi.", "Соединяет параллельный результат или одновременное действие.", "Натиҷаи параллел ё ҳолати ҳамзамонро мепайвандад.", "同时，它还会丰富你的情感，使你的生活更精彩。", "Tóngshí, tā hái huì fēngfù nǐ de qínggǎn, shǐ nǐ de shēnghuó gèng jīngcǎi.", "Shu bilan birga, u hissiyotlaringizni boyitib, hayotingizni yanada mazmunli qiladi.", "При этом оно обогащает чувства и делает жизнь ярче.", "Ҳамзамон, он эҳсосотатро ғанӣ карда, зиндагиро ҷолибтар мекунад."),
        ],
        "dialogues": [
            {
                "block_no": 1,
                "section_label": "课文 1",
                "scene_uz": "Mark xitoy tilini qanday o'rganishini tushuntiradi",
                "scene_ru": "Марк рассказывает, как он учит китайский",
                "scene_tj": "Марк мефаҳмонад, ки чӣ тавр чинӣ меомӯзад",
                "word_nos": [1, 2, 3, 4, 5, 6],
                "grammar_nos": [1],
                "dialogue": [
                    _line("大卫", "你来中国才一年，汉语就说得这么流利，真厉害！", "Nǐ lái Zhōngguó cái yì nián, Hànyǔ jiù shuō de zhème liúlì, zhēn lìhai!", "Xitoyga kelganingga endi bir yil bo'ldi, xitoychang shunchalik ravon, juda zo'r!", "Ты в Китае всего год, а говоришь по-китайски так бегло, здорово!", "Ба Чин ҳамагӣ як сол шуд омадӣ, вале чинӣ ин қадар равон мегӯӣ, зӯр!"),
                    _line("马克", "谢谢！其实我的语法不太好，很多句子说得都不太准确。", "Xièxie! Qíshí wǒ de yǔfǎ bú tài hǎo, hěn duō jùzi shuō de dōu bú tài zhǔnquè.", "Rahmat! Aslida grammatikam uncha yaxshi emas, ko'p gaplarni ham aniq ayta olmayman.", "Спасибо! На самом деле грамматика у меня не очень, многие фразы я говорю не совсем точно.", "Раҳмат! Дар асл грамматикам чандон хуб нест, бисёр ҷумлаҳоро дақиқ гуфта наметавонам."),
                    _line("大卫", "但是我看你跟中国人交流没什么问题，你是怎么做到的？", "Dànshì wǒ kàn nǐ gēn Zhōngguó rén jiāoliú méi shénme wèntí, nǐ shì zěnme zuò dào de?", "Lekin xitoyliklar bilan muloqotingda muammo yo'q ko'rinadi, bunga qanday erishding?", "Но я вижу, что ты без проблем общаешься с китайцами. Как тебе это удалось?", "Аммо мебинам бо чиниҳо бе мушкил муошират мекунӣ. Чӣ тавр ба ин расидӣ?"),
                    _line("马克", "平时多交一些中国朋友，经常和他们聊天儿，听说能力自然就能得到很大的提高。另外，我建议你坚持看中文报纸，这样能学到很多新词语。", "Píngshí duō jiāo yìxiē Zhōngguó péngyou, jīngcháng hé tāmen liáotiānr, tīngshuō nénglì zìrán jiù néng dédào hěn dà de tígāo. Lìngwài, wǒ jiànyì nǐ jiānchí kàn Zhōngwén bàozhǐ, zhèyàng néng xuédào hěn duō xīn cíyǔ.", "Odatda ko'proq xitoylik do'st orttirib, ular bilan tez-tez gaplashish kerak, shunda tinglash va gapirish tabiiy ravishda ancha yaxshilanadi. Yana xitoycha gazeta o'qishni davom ettirishni maslahat beraman, ko'p yangi so'z o'rganasan.", "Нужно заводить китайских друзей и часто с ними разговаривать, тогда аудирование и речь естественно улучшатся. Ещё советую регулярно читать китайские газеты, так выучишь много новых слов.", "Бояд бештар дӯстони чинӣ пайдо карда, бо онҳо зуд-зуд суҳбат кунӣ, он гоҳ шунидану гуфтан табиӣ беҳтар мешавад. Боз маслиҳат медиҳам рӯзномаи чинӣ бихонӣ, бисёр калимаи нав меомӯзӣ."),
                    _line("大卫", "你太厉害了！连中文报纸都看得懂。", "Nǐ tài lìhai le! Lián Zhōngwén bàozhǐ dōu kàn de dǒng.", "Juda zo'rsan! Hatto xitoycha gazetani ham tushunib o'qiyapsan.", "Ты просто молодец! Даже китайские газеты понимаешь.", "Ту хеле зӯрӣ! Ҳатто рӯзномаи чиниро мефаҳмӣ."),
                    _line("马克", "刚开始肯定有困难，不过遇到不认识的词语，你可以查词典，然后写在本子上，有空儿就拿出来复习一下，慢慢地就会发现中文报纸也没那么难了。", "Gāng kāishǐ kěndìng yǒu kùnnan, búguò yùdào bú rènshi de cíyǔ, nǐ kěyǐ chá cídiǎn, ránhòu xiě zài běnzi shang, yǒu kòngr jiù ná chūlai fùxí yíxià, mànmàn de jiù huì fāxiàn Zhōngwén bàozhǐ yě méi nàme nán le.", "Boshlanishida albatta qiyin bo'ladi, lekin notanish so'z uchrasa lug'atdan qarab, daftarga yozib qo'y, bo'sh vaqtda takrorla. Asta-sekin xitoycha gazeta ham unchalik qiyin emasligini ko'rasan.", "Сначала, конечно, трудно, но незнакомые слова можно смотреть в словаре, записывать в тетрадь и повторять в свободное время. Постепенно увидишь, что китайские газеты не такие уж трудные.", "Аввал албатта душвор аст, вале калимаи ношиносро аз луғат нигоҳ карда, ба дафтар навис ва вақти холӣ такрор кун. Оҳиста мефаҳмӣ, ки рӯзномаи чинӣ он қадар душвор нест."),
                ],
            },
            {
                "block_no": 2,
                "section_label": "课文 2",
                "scene_uz": "Xiaoxia va Xiaoyu imtihon natijasini muhokama qiladi",
                "scene_ru": "Сяося и Сяоюй обсуждают экзамен",
                "scene_tj": "Сяося ва Сяоюй натиҷаи имтиҳонро муҳокима мекунанд",
                "word_nos": [7, 8, 9, 10, 11, 12, 13],
                "grammar_nos": [2],
                "dialogue": [
                    _line("小夏", "考试结束了，你对自己的成绩满意吗？", "Kǎoshì jiéshù le, nǐ duì zìjǐ de chéngjì mǎnyì ma?", "Imtihon tugadi, natijangdan mamnunmisan?", "Экзамен закончился, ты доволен своим результатом?", "Имтиҳон тамом шуд, аз натиҷаат розӣ ҳастӣ?"),
                    _line("小雨", "说真的，我不太满意。这次阅读考试的题太多了，我没做完。", "Shuō zhēn de, wǒ bú tài mǎnyì. Zhè cì yuèdú kǎoshì de tí tài duō le, wǒ méi zuò wán.", "Rostini aytsam, uncha mamnun emasman. Bu safargi o'qish imtihonida savol juda ko'p edi, tugata olmadim.", "Честно говоря, не очень доволен. В этом экзамене по чтению было слишком много заданий, я не успел закончить.", "Росташ, чандон розӣ нестам. Дар ин имтиҳони хониш саволҳо хеле зиёд буданд, тамом карда натавонистам."),
                    _line("小夏", "两个小时的时间应该来得及吧？", "Liǎng ge xiǎoshí de shíjiān yīnggāi láidejí ba?", "Ikki soat vaqt yetishi kerak edi-ku?", "Двух часов должно было хватить, нет?", "Ду соат вақт бояд мерасид-ку?"),
                    _line("小雨", "这次主要是因为我先做了比较难、比较复杂的题，结果花了太多时间，后面简单的题我虽然会，可是时间来不及，最后只好放弃了。", "Zhè cì zhǔyào shì yīnwèi wǒ xiān zuò le bǐjiào nán, bǐjiào fùzá de tí, jiéguǒ huā le tài duō shíjiān, hòumian jiǎndān de tí wǒ suīrán huì, kěshì shíjiān láibují, zuìhòu zhǐhǎo fàngqì le.", "Asosan avval qiyinroq, murakkabroq savollarni ishlaganim uchun juda ko'p vaqt ketdi. Keyingi oson savollarni bilardim, lekin vaqt yetmadi, oxiri tashlab qo'yishga majbur bo'ldim.", "Главная причина в том, что я сначала делал трудные и сложные задания, потратил слишком много времени. Простые задания в конце я знал, но времени не хватило, пришлось отказаться.", "Сабабаш ин буд, ки аввал саволҳои душвору мураккабро кардам ва вақти зиёд рафт. Саволҳои осони охирро медонистам, вале вақт нарасид, маҷбур шудам тарк кунам."),
                    _line("小夏", "其实我考得也不怎么样。有几个填空题不会做，有几个选择题，实在想不出来该选哪个，就随便猜了一个答案，结果一个都没猜对。", "Qíshí wǒ kǎo de yě bù zěnmeyàng. Yǒu jǐ ge tiánkòng tí bú huì zuò, yǒu jǐ ge xuǎnzé tí, shízài xiǎng bu chūlai gāi xuǎn nǎ ge, jiù suíbiàn cāi le yí ge dá'àn, jiéguǒ yí ge dōu méi cāi duì.", "Men ham uncha yaxshi topshirmadim. Bir nechta to'ldirish savolini qila olmadim, bir nechta testda qaysi javobni tanlashni topolmay, tasodifan belgiladim, lekin bittasi ham to'g'ri chiqmadi.", "Я тоже сдал не очень. Несколько пропусков не смог сделать, в нескольких тестах не знал, что выбрать, просто угадал, но ни один ответ не оказался верным.", "Ман ҳам чандон хуб насупоридам. Чанд саволи ҷойи холиро карда натавонистам, дар чанд тест намедонистам кадомашро интихоб кунам, тахмин кардам, вале ҳеҷ яке дуруст нашуд."),
                    _line("小雨", "看来要想考好，不但要认真复习，还得注意考试的方法，否则，会做的题也没时间做了。", "Kànlái yào xiǎng kǎo hǎo, bùdàn yào rènzhēn fùxí, hái děi zhùyì kǎoshì de fāngfǎ, fǒuzé, huì zuò de tí yě méi shíjiān zuò le.", "Yaxshi topshirish uchun jiddiy takrorlashdan tashqari, imtihon usuliga ham e'tibor berish kerak ekan, aks holda bilgan savolga ham vaqt qolmaydi.", "Похоже, чтобы хорошо сдать, нужно не только серьёзно повторять, но и следить за методом экзамена, иначе не хватит времени даже на знакомые задания.", "Барои хуб супоридан на танҳо ҷиддӣ такрор кардан, балки ба усули имтиҳон ҳам диққат додан лозим, вагарна ба саволҳои медониста ҳам вақт намерасад."),
                ],
            },
            {
                "block_no": 3,
                "section_label": "课文 3",
                "scene_uz": "Xiaoli Xiaolinga o'qish foydasini aytadi",
                "scene_ru": "Сяоли рассказывает Сяолиню о пользе чтения",
                "scene_tj": "Сяоли ба Сяолин фоидаи хонданро мегӯяд",
                "word_nos": [14, 15, 16, 17, 18, 19],
                "grammar_nos": [3],
                "dialogue": [
                    _line("小林", "你的客厅里怎么到处是书啊？这些书你都喜欢看吗？", "Nǐ de kètīng li zěnme dàochù shì shū a? Zhèxiē shū nǐ dōu xǐhuan kàn ma?", "Mehmonxonangda nega hamma joy kitob? Bu kitoblarning hammasini o'qishni yoqtirasanmi?", "Почему у тебя в гостиной везде книги? Ты любишь читать все эти книги?", "Чаро дар меҳмонхонаат ҳама ҷо китоб аст? Ҳамаи ин китобҳоро хонданро дӯст медорӣ?"),
                    _line("小李", "当然，我每天都要看书。无论是普通杂志，还是著名小说，只要打开它们，就会发现，世界上有那么多有意思的事情，有那么多不一样的生活。", "Dāngrán, wǒ měi tiān dōu yào kàn shū. Wúlùn shì pǔtōng zázhì, háishi zhùmíng xiǎoshuō, zhǐyào dǎkāi tāmen, jiù huì fāxiàn, shìjiè shang yǒu nàme duō yǒu yìsi de shìqing, yǒu nàme duō bù yíyàng de shēnghuó.", "Albatta, men har kuni kitob o'qiyman. Oddiy jurnal bo'ladimi yoki mashhur romanmi, ochsangiz dunyoda qancha qiziq narsalar va turli hayotlar borligini ko'rasiz.", "Конечно, я каждый день читаю. Будь то обычный журнал или известный роман, откроешь и увидишь, сколько в мире интересного и сколько разных жизней.", "Албатта, ман ҳар рӯз китоб мехонам. Маҷаллаи одӣ бошад ё романи машҳур, кушоӣ мебинӣ, ки дар дунё чӣ қадар чизҳои ҷолиб ва зиндагии гуногун ҳаст."),
                    _line("小林", "想不到你工作那么忙，还能每天坚持阅读。", "Xiǎngbudào nǐ gōngzuò nàme máng, hái néng měi tiān jiānchí yuèdú.", "Ishing shunchalik band bo'lsa ham, har kuni o'qishni davom ettirishingni kutmagandim.", "Не думал, что при такой занятости ты всё равно читаешь каждый день.", "Фикр намекардам, бо ин қадар серкорӣ ҳар рӯз хонданро давом медиҳӣ."),
                    _line("小李", "如果3分钟读一页书，半个小时就可以读10页。每天花半个小时来读书，一个月就可以读300页，差不多就是一本书了。", "Rúguǒ sān fēnzhōng dú yí yè shū, bàn ge xiǎoshí jiù kěyǐ dú shí yè. Měi tiān huā bàn ge xiǎoshí lái dú shū, yí ge yuè jiù kěyǐ dú sānbǎi yè, chàbuduō jiùshì yì běn shū le.", "Agar 3 daqiqada bir sahifa o'qilsa, yarim soatda 10 sahifa bo'ladi. Har kuni yarim soat o'qisang, bir oyda 300 sahifa, deyarli bitta kitob o'qiysan.", "Если читать страницу за 3 минуты, за полчаса можно прочитать 10 страниц. Если читать по полчаса в день, за месяц будет 300 страниц, почти книга.", "Агар дар 3 дақиқа як саҳифа хонӣ, дар ним соат 10 саҳифа мешавад. Ҳар рӯз ним соат хонӣ, дар як моҳ 300 саҳифа, тақрибан як китоб мешавад."),
                    _line("小林", "是啊，一个真正爱看书的人总能找出时间来阅读。", "Shì a, yí ge zhēnzhèng ài kàn shū de rén zǒng néng zhǎo chū shíjiān lái yuèdú.", "Ha, kitobni chin yoqtiradigan odam o'qishga albatta vaqt topadi.", "Да, тот, кто действительно любит книги, всегда найдёт время для чтения.", "Ҳа, касе ки китобро воқеан дӯст медорад, барои хондан вақт меёбад."),
                    _line("小李", "坚持阅读，除了能增加知识外，还能帮助我减轻压力，人也会变得轻松起来。", "Jiānchí yuèdú, chúle néng zēngjiā zhīshi wài, hái néng bāngzhù wǒ jiǎnqīng yālì, rén yě huì biàn de qīngsōng qǐlai.", "O'qishni davom ettirish bilimni oshiradi, bundan tashqari bosimni kamaytirib, odamni yengillashtiradi.", "Регулярное чтение не только увеличивает знания, но и помогает мне снять стресс, человек становится легче.", "Давом додани хондан донишро зиёд мекунад, инчунин фишорро кам карда, одамро сабуктар мекунад."),
                ],
            },
            {
                "block_no": 4,
                "section_label": "课文 4",
                "scene_uz": "O'qish qaydlari o'qish qobiliyatini oshirishi haqida matn",
                "scene_ru": "Текст о том, как читательские заметки повышают навык чтения",
                "scene_tj": "Матн дар бораи он ки қайдҳои китобхонӣ маҳорати хонданро баланд мекунанд",
                "word_nos": [20, 21, 22, 23, 24],
                "grammar_nos": [4],
                "dialogue": [
                    _line("旁白", "根据调查，阅读能力好的人，不但容易找到工作，而且工资也比较高。", "Gēnjù diàochá, yuèdú nénglì hǎo de rén, bùdàn róngyì zhǎodào gōngzuò, érqiě gōngzī yě bǐjiào gāo.", "Tadqiqotga ko'ra, o'qish qobiliyati yaxshi odamlar ishni oson topadi va maoshi ham yuqoriroq bo'ladi.", "По данным опроса, людям с хорошим навыком чтения легче найти работу, и зарплата у них выше.", "Тибқи таҳқиқ, одамони дорои маҳорати хуби хондан корро осонтар меёбанд ва маошашон баландтар аст."),
                    _line("旁白", "怎么才能有效提高自己的阅读能力呢？做读书笔记就是其中一种好方法。", "Zěnme cái néng yǒuxiào tígāo zìjǐ de yuèdú nénglì ne? Zuò dúshū bǐjì jiù shì qízhōng yì zhǒng hǎo fāngfǎ.", "O'qish qobiliyatini qanday samarali oshirish mumkin? O'qish qaydlari yozish - yaxshi usullardan biri.", "Как эффективно повысить навык чтения? Один из хороших способов - делать читательские заметки.", "Чӣ тавр маҳорати хонданро самаранок беҳтар кардан мумкин? Яке аз роҳҳои хуб - қайдҳои китобхонӣ аст."),
                    _line("旁白", "读书笔记有很多种，最简单的就是把自己喜欢或者觉得有用的词语和句子记下来。", "Dúshū bǐjì yǒu hěn duō zhǒng, zuì jiǎndān de jiùshì bǎ zìjǐ xǐhuan huòzhě juéde yǒuyòng de cíyǔ hé jùzi jì xiàlai.", "O'qish qaydlarining turlari ko'p. Eng sodda usul - o'zingiz yoqtirgan yoki foydali deb bilgan so'z va gaplarni yozib borish.", "Есть много видов читательских заметок. Самый простой - записывать слова и предложения, которые понравились или кажутся полезными.", "Қайдҳои китобхонӣ навъҳои зиёд доранд. Роҳи содда - калимаҳо ва ҷумлаҳои писанд ё фоиданокро навиштан."),
                    _line("旁白", "另外，在看完一篇文章或一本书之后，还可以把它的主要内容和自己的想法写下来。", "Lìngwài, zài kàn wán yì piān wénzhāng huò yì běn shū zhīhòu, hái kěyǐ bǎ tā de zhǔyào nèiróng hé zìjǐ de xiǎngfǎ xiě xiàlai.", "Bundan tashqari, bir maqola yoki kitobni tugatgach, uning asosiy mazmuni va o'z fikringizni yozib qo'yish mumkin.", "Кроме того, после статьи или книги можно записать основное содержание и свои мысли.", "Ғайр аз ин, баъди хондани мақола ё китоб мазмуни асосӣ ва фикри худро навиштан мумкин."),
                    _line("旁白", "然而，你不能完全相信书本上的内容，要有自己的看法和判断。坚持做读书笔记，对提高阅读能力有很大帮助。", "Rán'ér, nǐ bù néng wánquán xiāngxìn shūběn shang de nèiróng, yào yǒu zìjǐ de kànfǎ hé pànduàn. Jiānchí zuò dúshū bǐjì, duì tígāo yuèdú nénglì yǒu hěn dà bāngzhù.", "Biroq kitobdagi mazmunga butunlay ishonib qolmasdan, o'z qarash va hukmingiz bo'lishi kerak. O'qish qaydlarini davomli yozish o'qish qobiliyatini oshirishga katta yordam beradi.", "Однако нельзя полностью верить содержанию книги, нужно иметь своё мнение и суждение. Регулярные заметки сильно помогают улучшить навык чтения.", "Аммо ба мазмуни китоб пурра бовар кардан мумкин нест, назари худ ва баҳодиҳии худ лозим аст. Давом додани қайдҳои китобхонӣ ба беҳтар шудани хондан бисёр ёрӣ медиҳад."),
                ],
            },
            {
                "block_no": 5,
                "section_label": "课文 5",
                "scene_uz": "读书好，读好书，好读书 iborasining ma'nosi haqida matn",
                "scene_ru": "Текст о смысле фразы 读书好，读好书，好读书",
                "scene_tj": "Матн дар бораи маънои ибораи 读书好，读好书，好读书",
                "word_nos": [25, 26, 27, 28, 29, 30],
                "grammar_nos": [5],
                "dialogue": [
                    _line("旁白", "“读书好，读好书，好读书”。虽然这句话只用了三个相同的汉字，但是不同的顺序却表示了不同的意思。", "Dú shū hǎo, dú hǎo shū, hào dú shū. Suīrán zhè jù huà zhǐ yòng le sān ge xiāngtóng de Hànzì, dànshì bùtóng de shùnxù què biǎoshì le bùtóng de yìsi.", "“O'qish yaxshi, yaxshi kitob o'qi, o'qishni yaxshi ko'r.” Bu gapda faqat uchta bir xil iyeroglif ishlatilgan bo'lsa ham, tartib o'zgarganda ma'no ham o'zgaradi.", "«Читать хорошо, читать хорошие книги, любить чтение». В этой фразе три одинаковых иероглифа, но разный порядок даёт разные смыслы.", "«Хондан хуб аст, китоби хуб хон, хонданро дӯст дор». Дар ин ҷумла се иероглифи якхела ҳаст, аммо тартиби гуногун маънои гуногун медиҳад."),
                    _line("旁白", "首先，“读书好”说的是读书有很多好处；其次，每个人的时间都是有限的，不可能把世界上每一本书都读完，所以要读好的书。", "Shǒuxiān, “dú shū hǎo” shuō de shì dúshū yǒu hěn duō hǎochu; qícì, měi ge rén de shíjiān dōu shì yǒuxiàn de, bù kěnéng bǎ shìjiè shang měi yì běn shū dōu dú wán, suǒyǐ yào dú hǎo de shū.", "Avvalo, “读书好” o'qishning foydasi ko'pligini bildiradi. Ikkinchidan, hammaning vaqti cheklangan, dunyodagi har bir kitobni o'qib bo'lmaydi, shuning uchun yaxshi kitob o'qish kerak.", "Во-первых, «读书好» говорит, что чтение полезно. Во-вторых, время каждого ограничено, невозможно прочитать все книги мира, поэтому нужно читать хорошие книги.", "Аввал, «读书好» фоидаи зиёди хонданро мегӯяд. Дуюм, вақти ҳар кас маҳдуд аст, ҳамаи китобҳои дунёро хондан имкон надорад, пас китобҳои хуб хондан лозим."),
                    _line("旁白", "最后，“好读书”就是要养成阅读的习惯，使读书真正成为自己的兴趣爱好。", "Zuìhòu, “hào dú shū” jiùshì yào yǎngchéng yuèdú de xíguàn, shǐ dúshū zhēnzhèng chéngwéi zìjǐ de xìngqù àihào.", "Oxirida, “好读书” o'qish odatini shakllantirib, o'qishni haqiqiy qiziqishga aylantirishdir.", "Наконец, «好读书» означает сформировать привычку читать и сделать чтение настоящим интересом.", "Ниҳоят, «好读书» маънои ташаккули одати хондан ва табдил додани хондан ба шавқи ҳақиқӣ аст."),
                    _line("旁白", "阅读有许多好处，它能丰富你的知识，让你找到解决问题的办法；同时，它还会丰富你的情感，使你的生活更精彩。", "Yuèdú yǒu xǔduō hǎochu, tā néng fēngfù nǐ de zhīshi, ràng nǐ zhǎodào jiějué wèntí de bànfǎ; tóngshí, tā hái huì fēngfù nǐ de qínggǎn, shǐ nǐ de shēnghuó gèng jīngcǎi.", "O'qishning foydasi ko'p: bilimingizni boyitadi, muammoni hal qilish yo'lini topishga yordam beradi. Shu bilan birga, hissiyotingizni boyitib, hayotingizni yanada mazmunli qiladi.", "У чтения много пользы: оно обогащает знания и помогает находить решения проблем. При этом оно обогащает чувства и делает жизнь ярче.", "Хондан фоидаи зиёд дорад: донишро ғанӣ мекунад ва роҳи ҳалли мушкилро меёбонад. Ҳамзамон эҳсосотро ғанӣ карда, зиндагиро ҷолибтар мекунад."),
                    _line("旁白", "所以，让阅读成为你的习惯吧！", "Suǒyǐ, ràng yuèdú chéngwéi nǐ de xíguàn ba!", "Shuning uchun o'qishni odatingizga aylantiring.", "Поэтому пусть чтение станет вашей привычкой.", "Пас бигзор хондан ба одати шумо табдил ёбад."),
                ],
            },
        ],
    },
}
_LESSON_12 = {
    "title": "用心发现世界",
    "goal": {
        "uz": "hayotdan yechim topish, tajribani yangilash va to'g'ri usul tanlash haqida gapirish; 并且, 再……也……, 对于, o'lchov so'zi takrori va 相反 grammatikalarini ishlatish",
        "ru": "говорить о поиске решений в жизни, пересмотре опыта и выборе метода; использовать 并且, 再……也……, 对于, повтор счётных слов и 相反",
        "tj": "дар бораи ёфтани роҳ аз зиндагӣ, нав кардани таҷриба ва интихоби усули дуруст гуфтугӯ кардан; истифодаи 并且, 再……也……, 对于, такрори шуморкалима ва 相反",
    },
    "intro_text": {
        "uz": "Bu darsda qoidaga yopishib qolmaslik, kundalik hayotdan bilim topish, o'qitish usuli, til ishlatish va o'rganishda to'g'ri metod tanlashni o'rganasiz.",
        "ru": "В этом уроке вы научитесь говорить о гибком отношении к правилам, знаниях из жизни, методах преподавания, языке и правильных способах учёбы.",
        "tj": "Дар ин дарс дар бораи сахт часпида нагирифтан ба қоида, дониш аз зиндагӣ, усули таълим, истифодаи забон ва интихоби роҳи дурусти омӯзиш меомӯзед.",
    },
    "vocabulary": [
        _word(1, "规定", "guīdìng", "n.", "qoida, belgilangan tartib", "правило, положение", "қоида, тартиб"),
        _word(2, "死", "sǐ", "adj.", "qattiq, o'zgarmas", "жёсткий, негибкий", "сахт, тағйирнопазир"),
        _word(3, "可惜", "kěxī", "adj.", "afsus, achinarli", "жаль, досадно", "афсӯс, ҳайф"),
        _word(4, "全部", "quánbù", "n.", "hammasi, butuni", "всё, полностью", "ҳама, пурра"),
        _word(5, "也许", "yěxǔ", "adv.", "balki, ehtimol", "может быть, возможно", "шояд, мумкин"),
        _word(6, "商量", "shāngliang", "v.", "maslahatlashmoq", "обсуждать, советоваться", "маслиҳат кардан"),
        _word(7, "并且", "bìngqiě", "conj.", "va, shuningdek", "и, а также", "ва, ҳамчунин"),
        _word(8, "盐", "yán", "n.", "tuz", "соль", "намак"),
        _word(9, "勺（子）", "sháo(zi)", "n.", "qoshiq", "ложка", "қошуқ"),
        _word(10, "保护", "bǎohù", "v.", "himoya qilmoq", "защищать", "ҳифз кардан"),
        _word(11, "作用", "zuòyòng", "n.", "ta'sir, vazifa", "роль, функция", "нақш, таъсир"),
        _word(12, "无法", "wúfǎ", "v.", "qila olmaslik", "быть не в состоянии", "натавонистан"),
        _word(13, "节", "jié", "m.", "bo'lim, dars qismi", "раздел, часть", "қисм, бахш"),
        _word(14, "详细", "xiángxì", "adj.", "batafsil", "подробный", "муфассал"),
        _word(15, "解释", "jiěshì", "v.", "tushuntirmoq", "объяснять", "шарҳ додан"),
        _word(16, "对于", "duìyú", "prep.", "...ga nisbatan, ...borasida", "по отношению к, что касается", "нисбат ба, дар мавриди"),
        _word(17, "叶子", "yèzi", "n.", "barg", "лист", "барг"),
        _word(18, "教育", "jiàoyù", "v.", "ta'lim bermoq, tarbiyalamoq", "обучать, воспитывать", "таълим додан, тарбия кардан"),
        _word(19, "使用", "shǐyòng", "v.", "ishlatmoq, foydalanmoq", "использовать", "истифода кардан"),
        _word(20, "语言", "yǔyán", "n.", "til", "язык", "забон"),
        _word(21, "直接", "zhíjiē", "adj.", "to'g'ridan-to'g'ri", "прямой, прямо", "бевосита, рӯирост"),
        _word(22, "引起", "yǐnqǐ", "v.", "keltirib chiqarmoq", "вызывать", "ба вуҷуд овардан"),
        _word(23, "误会", "wùhuì", "n.", "tushunmovchilik", "недоразумение", "нофаҳмӣ"),
        _word(24, "友好", "yǒuhǎo", "adj.", "do'stona", "дружелюбный", "дӯстона"),
        _word(25, "事半功倍", "shì bàn gōng bèi", "phrase", "kam kuch bilan ko'p natija", "получить больший результат меньшими усилиями", "бо кӯшиши кам натиҷаи зиёд гирифтан"),
        _word(26, "节约", "jiéyuē", "v.", "tejamoq", "экономить", "сарфа кардан"),
        _word(27, "力气", "lìqi", "n.", "kuch, mehnat", "силы, усилия", "қувват, заҳмат"),
        _word(28, "相反", "xiāngfǎn", "conj.", "aksincha", "наоборот, напротив", "баръакс"),
        _word(29, "任务", "rènwu", "n.", "vazifa", "задача", "вазифа"),
        _word(30, "意见", "yìjian", "n.", "fikr, taklif", "мнение, предложение", "фикр, пешниҳод"),
        _word(31, "仔细", "zǐxì", "adj.", "diqqatli, sinchkov", "внимательный, тщательно", "бодиққат"),
        _word(32, "达到", "dádào", "v.", "erishmoq", "достигать", "расидан"),
    ],
    "grammar": [
        _grammar(1, "并且", "va, shuningdek", "и, а также", "ва, ҳамчунин", "Ikki harakat yoki sifatni bog'lab, ikkinchi fikrni davom ettiradi.", "Соединяет два действия или качества и продолжает мысль.", "Ду амал ё сифатро пайваст карда, фикрро идома медиҳад.", "希望能及时发现问题，并且准确地找到解决问题的方法。", "Xīwàng néng jíshí fāxiàn wèntí, bìngqiě zhǔnquè de zhǎodào jiějué wèntí de fāngfǎ.", "Muammoni vaqtida topib, shuningdek uni aniq hal qilish yo'lini topishga umid qilaman.", "Надеюсь вовремя найти проблему и точно найти способ её решить.", "Умедворам мушкилро сари вақт ёфта, ҳамчунин роҳи дурусти ҳалро пайдо кунам."),
        _grammar(2, "再……也……", "qanchalik...bo'lsa ham", "как бы ни...", "ҳар қадар...ҳам", "Holat kuchaysa ham natija o'zgarmasligini bildiradi.", "Показывает, что результат не меняется даже при усилении условия.", "Нишон медиҳад, ки бо зиёд шудани шарт ҳам натиҷа дигар намешавад.", "这样穿得再久、洗的次数再多，衣服也不容易掉颜色。", "Zhèyàng chuān de zài jiǔ, xǐ de cìshù zài duō, yīfu yě bù róngyì diào yánsè.", "Shunday qilinsa, qancha uzoq kiyilsa ham, qancha ko'p yuvilsa ham, kiyimning rangi oson ketmaydi.", "Так одежда даже после долгой носки и частых стирок не будет легко линять.", "Ин тавр либос ҳар қадар дер пӯшида ва зиёд шуста шавад ҳам, ранги он осон намеравад."),
        _grammar(3, "对于", "...ga nisbatan; ...borasida", "что касается; по отношению к", "нисбат ба; дар мавриди", "Mavzu yoki obyektni oldinga chiqaradi.", "Выносит тему или объект обсуждения вперёд.", "Мавзӯъ ё объекти гуфтугӯро пеш меорад.", "那您认为对于老师来说，什么是最难做到的？", "Nà nín rènwéi duìyú lǎoshī lái shuō, shénme shì zuì nán zuò dào de?", "Unda sizningcha, o'qituvchi uchun eng qiyin narsa nima?", "Что, по-вашему, труднее всего сделать для учителя?", "Ба назари шумо, барои муаллим иҷрои чӣ чиз аз ҳама душвортар аст?"),
        _grammar(4, "名量词重叠", "o'lchov so'zini takrorlash", "повтор счётного слова", "такрори шуморкалима", "Bir-bir, ketma-ket yoki har bir qism bo'yicha bajarishni bildiradi.", "Означает действие по одному, последовательно или по частям.", "Як-як, пайдарпай ё қисм-қисм иҷро шуданро мефаҳмонад.", "老师把复杂的问题一节一节地解释清楚。", "Lǎoshī bǎ fùzá de wèntí yì jié yì jié de jiěshì qīngchu.", "O'qituvchi murakkab masalani bo'lim-bo'lim qilib tushuntirdi.", "Учитель объяснил сложный вопрос часть за частью.", "Муаллим масъалаи мураккабро қисм-қисм шарҳ дод."),
        _grammar(5, "相反", "aksincha", "наоборот", "баръакс", "Oldingi fikrga qarama-qarshi natija yoki holatni beradi.", "Вводит противоположный результат или ситуацию.", "Натиҷа ё ҳолати баръакси фикри пешинаро меорад.", "相反，如果方法不对，可能花五倍甚至十倍的时间都不能完成任务。", "Xiāngfǎn, rúguǒ fāngfǎ bú duì, kěnéng huā wǔ bèi shènzhì shí bèi de shíjiān dōu bù néng wánchéng rènwu.", "Aksincha, usul noto'g'ri bo'lsa, besh yoki hatto o'n baravar vaqt sarflab ham vazifani tugatolmaslik mumkin.", "Наоборот, если метод неверный, можно потратить в пять или даже десять раз больше времени и всё равно не выполнить задачу.", "Баръакс, агар усул нодуруст бошад, мумкин аст панҷ ё ҳатто даҳ баробар вақт сарф карда ҳам вазифа анҷом нашавад."),
    ],
    "dialogues": [
        {
            "block_no": 1,
            "section_label": "课文 1",
            "scene_uz": "Wang menejer tajribaga qattiq yopishib qolmaslikni maslahat beradi",
            "scene_ru": "Менеджер Ван советует не цепляться за старый опыт",
            "scene_tj": "Менеҷер Ван маслиҳат медиҳад, ки ба таҷрибаи кӯҳна сахт часпида нашаванд",
            "word_nos": [1, 2, 3, 4, 5, 6, 7],
            "grammar_nos": [1],
            "dialogue": [
                _line("王经理", "听说这次生意你到现在还没谈成。", "Tīngshuō zhè cì shēngyì nǐ dào xiànzài hái méi tán chéng.", "Eshitishimcha, bu safargi biznes kelishuvini haligacha bitira olmabsan.", "Слышал, ты до сих пор не договорился по этой сделке.", "Шунидам, ин дафъа кори тиҷоратро то ҳол ба анҷом нарасонидаӣ."),
                _line("马经理", "按我以前的经验，早应该谈成了，这次我也不知道哪儿出了问题。", "Àn wǒ yǐqián de jīngyàn, zǎo yīnggāi tán chéng le, zhè cì wǒ yě bù zhīdào nǎr chū le wèntí.", "Oldingi tajribam bo'yicha allaqachon kelishish kerak edi, bu safar qayerda muammo chiqqanini bilmayman.", "По моему прежнему опыту, уже давно должны были договориться, и я не знаю, где возникла проблема.", "Аз рӯи таҷрибаи пешинаам, бояд аллакай созиш мешуд, ин дафъа намедонам мушкил аз куҷо баромад."),
                _line("王经理", "有句话叫“规定和经验是死的，人是活的”。当“规定”和“经验”不能解决问题时，建议你改变一下自己的态度和想法。", "Yǒu jù huà jiào “guīdìng hé jīngyàn shì sǐ de, rén shì huó de”. Dāng “guīdìng” hé “jīngyàn” bù néng jiějué wèntí shí, jiànyì nǐ gǎibiàn yíxià zìjǐ de tàidu hé xiǎngfǎ.", "Bir gap bor: qoidalar va tajriba qattiq, odam esa moslasha oladi. Qoidalar va tajriba muammoni hal qilmasa, o'z munosabating va fikringni o'zgartir.", "Есть выражение: правила и опыт мёртвые, а человек живой. Когда правила и опыт не решают проблему, советую изменить отношение и мышление.", "Як сухан ҳаст: қоида ва таҷриба сахтанд, инсон бошад зинда аст. Вақте қоида ва таҷриба мушкилро ҳал намекунад, муносибат ва фикратро тағйир деҳ."),
                _line("马经理", "很多时候，我都习惯根据过去的经验做事，可惜，经验不是全部都是对的。", "Hěn duō shíhou, wǒ dōu xíguàn gēnjù guòqù de jīngyàn zuòshì, kěxī, jīngyàn bú shì quánbù dōu shì duì de.", "Ko'p payt ishni o'tgan tajribaga qarab qilishga o'rganib qolganman, afsuski, tajribaning hammasi ham to'g'ri emas.", "Часто я привык действовать по прошлому опыту, но жаль, что не весь опыт правильный.", "Бисёр вақт ман ба таҷрибаи гузашта такя мекунам, афсӯс, ки ҳама таҷриба дуруст нест."),
                _line("王经理", "遇到不能解决的问题时，我们应该试着走走以前从来没走过的路，也许这样就能找到解决问题的方法了。", "Yùdào bù néng jiějué de wèntí shí, wǒmen yīnggāi shìzhe zǒu zǒu yǐqián cónglái méi zǒuguo de lù, yěxǔ zhèyàng jiù néng zhǎodào jiějué wèntí de fāngfǎ le.", "Hal bo'lmaydigan muammoga duch kelsak, oldin hech yurmagan yo'ldan yurib ko'rish kerak, balki shunda yechim topilar.", "Когда сталкиваемся с нерешаемой проблемой, стоит попробовать путь, по которому раньше не ходили, возможно, так найдём решение.", "Вақте ба мушкили ҳалнашаванда рӯ ба рӯ мешавем, бояд роҳи пештар нарафтаро санҷем, шояд ҳамин тавр роҳ пайдо шавад."),
                _line("马经理", "好，我再跟同事商量商量，希望能及时发现问题，并且准确地找到解决问题的方法。", "Hǎo, wǒ zài gēn tóngshì shāngliang shāngliang, xīwàng néng jíshí fāxiàn wèntí, bìngqiě zhǔnquè de zhǎodào jiějué wèntí de fāngfǎ.", "Yaxshi, hamkasblarim bilan yana maslahatlashaman, muammoni vaqtida topib, uni aniq hal qilish yo'lini topamiz degan umiddaman.", "Хорошо, ещё посоветуюсь с коллегами, надеюсь вовремя найти проблему и точно найти способ её решить.", "Хуб, бо ҳамкорон боз маслиҳат мекунам, умедворам мушкилро сари вақт ёфта, роҳи дурусти ҳалро пайдо кунем."),
            ],
        },
        {
            "block_no": 2,
            "section_label": "课文 2",
            "scene_uz": "Gao o'qituvchi qiziga kiyim rangini saqlash usulini aytadi",
            "scene_ru": "Учитель Гао объясняет дочери, как сохранить цвет одежды",
            "scene_tj": "Муаллима Гао ба духтараш роҳи нигоҳ доштани ранги либосро мегӯяд",
            "word_nos": [8, 9, 10, 11, 12],
            "grammar_nos": [2],
            "dialogue": [
                _line("女儿", "妈，您看我刚买的裤子，洗完以后颜色怎么变得这么难看呢？", "Mā, nín kàn wǒ gāng mǎi de kùzi, xǐ wán yǐhòu yánsè zěnme biàn de zhème nánkàn ne?", "Oyi, yangi olgan shimimga qarang, yuvilgandan keyin rangi nega bunchalik xunuk bo'lib qoldi?", "Мама, посмотрите на брюки, которые я только купила: почему после стирки цвет стал таким некрасивым?", "Оча, шими нав харидаамро бинед, баъди шустан ранги он чаро ин қадар бад шуд?"),
                _line("高老师", "看来是掉颜色了，你洗的时候在水里加点儿盐就不会这样了。", "Kànlái shì diào yánsè le, nǐ xǐ de shíhou zài shuǐ li jiā diǎnr yán jiù bú huì zhèyàng le.", "Ko'rinishidan rangi chiqib ketibdi. Yuvganda suvga ozgina tuz solsang bunday bo'lmaydi.", "Похоже, она полиняла. Если при стирке добавить в воду немного соли, такого не будет.", "Аз афташ рангаш баромадааст. Ҳангоми шустан ба об каме намак андозӣ, чунин намешавад."),
                _line("女儿", "放盐？！盐不是用来做饭的吗？难道它还能让衣服不掉颜色？", "Fàng yán?! Yán bú shì yòng lái zuò fàn de ma? Nándào tā hái néng ràng yīfu bù diào yánsè?", "Tuz solish? Tuz ovqat qilish uchun emasmi? Nahotki u kiyim rangini ketkazmaslikka yordam bersa?", "Соль? Разве соль не для готовки? Неужели она может не дать одежде линять?", "Намак? Магар намак барои пухтупаз нест? Наход он ранги либосро нигоҳ медорад?"),
                _line("高老师", "当然。有些衣服第一次洗的时候会掉颜色，其实，有很多方法可以解决这个问题。", "Dāngrán. Yǒuxiē yīfu dì yī cì xǐ de shíhou huì diào yánsè, qíshí, yǒu hěn duō fāngfǎ kěyǐ jiějué zhège wèntí.", "Albatta. Ba'zi kiyimlar birinchi yuvishda rang chiqaradi, aslida bu muammoni hal qiladigan usullar ko'p.", "Конечно. Некоторая одежда линяет при первой стирке, на самом деле есть много способов решить эту проблему.", "Албатта. Баъзе либосҳо дар шустани аввал ранг медиҳанд, дар асл роҳҳои ҳалли ин мушкил зиёданд."),
                _line("高老师", "在水里加勺盐再洗是最简单的方法。用盐水来洗新衣服，这样穿得再久、洗的次数再多，衣服也不容易掉颜色。", "Zài shuǐ li jiā sháo yán zài xǐ shì zuì jiǎndān de fāngfǎ. Yòng yán shuǐ lái xǐ xīn yīfu, zhèyàng chuān de zài jiǔ, xǐ de cìshù zài duō, yīfu yě bù róngyì diào yánsè.", "Suvga bir qoshiq tuz solib yuvish eng oson usul. Yangi kiyimni tuzli suvda yuvsang, qancha uzoq kiyilsa ham, qancha ko'p yuvilsa ham, rangi oson ketmaydi.", "Самый простой способ - добавить ложку соли в воду. Если стирать новую одежду солёной водой, она не будет легко линять даже при долгой носке и частых стирках.", "Роҳи осонтарин ба об як қошуқ намак андохта шустан аст. Либоси навро бо оби намакдор шӯӣ, ҳар қадар дер пӯшида ва зиёд шуста шавад ҳам, ранги он осон намеравад."),
                _line("女儿", "我第一次听说盐有保护衣服颜色的作用，生活中还真有不少课本上无法学到的知识。", "Wǒ dì yī cì tīngshuō yán yǒu bǎohù yīfu yánsè de zuòyòng, shēnghuó zhōng hái zhēn yǒu bù shǎo kèběn shang wúfǎ xuédào de zhīshi.", "Tuz kiyim rangini himoya qilishini birinchi marta eshitdim. Hayotda darslikdan o'rganib bo'lmaydigan bilimlar haqiqatan ham ko'p ekan.", "Я впервые слышу, что соль защищает цвет одежды. В жизни действительно много знаний, которых нет в учебнике.", "Бори аввал мешунавам, ки намак ранги либосро муҳофизат мекунад. Дар зиндагӣ воқеан донишҳое зиёданд, ки аз китоб омӯхта намешаванд."),
                _line("高老师", "实际上，很多问题的答案都可以从生活中找到。但这需要你用眼睛去发现，用心去总结。", "Shíjì shang, hěn duō wèntí de dá'àn dōu kěyǐ cóng shēnghuó zhōng zhǎodào. Dàn zhè xūyào nǐ yòng yǎnjing qù fāxiàn, yòng xīn qù zǒngjié.", "Aslida ko'p savolning javobini hayotdan topish mumkin. Faqat buni ko'z bilan ko'rish va yurak bilan xulosa qilish kerak.", "На самом деле ответы на многие вопросы можно найти в жизни. Но для этого нужно замечать глазами и внимательно обобщать.", "Дар асл ҷавоби бисёр масъалаҳоро аз зиндагӣ ёфтан мумкин. Барои ин бояд бо чашм бинӣ ва бо диққат хулоса кунӣ."),
            ],
        },
        {
            "block_no": 3,
            "section_label": "课文 3",
            "scene_uz": "Gao o'qituvchi Wang professorning dars berish usulini o'rganadi",
            "scene_ru": "Учитель Гао изучает метод преподавания профессора Вана",
            "scene_tj": "Муаллима Гао усули дарсдиҳии профессор Ванро меомӯзад",
            "word_nos": [13, 14, 15, 16, 17, 18],
            "grammar_nos": [3, 4],
            "dialogue": [
                _line("高老师", "王教授，今天听完您的这节课，我终于明白为什么您的课那么受学生欢迎了。", "Wáng jiàoshòu, jīntiān tīng wán nín de zhè jié kè, wǒ zhōngyú míngbai wèishénme nín de kè nàme shòu xuésheng huānyíng le.", "Wang professor, bugun darsingizni tinglab, nega darslaringiz talabalar orasida bunchalik mashhur ekanini nihoyat tushundim.", "Профессор Ван, послушав сегодня ваш урок, я наконец понял, почему ваши занятия так нравятся студентам.", "Профессор Ван, имрӯз дарсатонро шунида, ниҳоят фаҳмидам, чаро дарсҳои шумо ба донишҷӯён ин қадар писанд аст."),
                _line("王教授", "谢谢！您能详细谈谈对我的课的看法吗？", "Xièxie! Nín néng xiángxì tán tan duì wǒ de kè de kànfǎ ma?", "Rahmat! Darsim haqidagi fikringizni batafsil aytib bera olasizmi?", "Спасибо! Можете подробно рассказать, что вы думаете о моём уроке?", "Раҳмат! Метавонед фикратонро дар бораи дарси ман муфассал гӯед?"),
                _line("高老师", "我发现您对学生特别了解，而且总是能用最简单的方法把复杂的问题解释清楚，让每个学生都能听懂，这一点真是值得我们好好儿学习。", "Wǒ fāxiàn nín duì xuésheng tèbié liǎojiě, érqiě zǒngshì néng yòng zuì jiǎndān de fāngfǎ bǎ fùzá de wèntí jiěshì qīngchu, ràng měi ge xuésheng dōu néng tīng dǒng, zhè yì diǎn zhēn shì zhíde wǒmen hǎohāor xuéxí.", "Siz talabalarni juda yaxshi tushunishingizni va murakkab masalalarni eng sodda usul bilan tushuntirib, har bir talabaga anglatishingizni ko'rdim. Bu biz uchun juda o'rganishga arziydi.", "Я заметил, что вы отлично понимаете студентов и всегда простым способом объясняете сложные вопросы так, что каждый понимает. Этому нам действительно стоит учиться.", "Ман дидам, ки шумо донишҷӯёнро хеле хуб мефаҳмед ва масъалаҳои мураккабро бо роҳи содда шарҳ медиҳед, то ҳар донишҷӯ фаҳмад. Ин барои мо арзандаи омӯзиш аст."),
                _line("王教授", "哪里哪里，这只是因为我对每个学生的能力水平比较了解。", "Nǎli nǎli, zhè zhǐshì yīnwèi wǒ duì měi ge xuésheng de nénglì shuǐpíng bǐjiào liǎojiě.", "Yo'g'e, bu faqat har bir talabamning qobiliyat darajasini nisbatan yaxshi bilganim uchun.", "Да что вы, просто я довольно хорошо понимаю уровень способностей каждого студента.", "Не, ин танҳо барои он аст, ки ман сатҳи қобилияти ҳар донишҷӯро нисбатан хуб медонам."),
                _line("高老师", "那您认为对于老师来说，什么是最难做到的？", "Nà nín rènwéi duìyú lǎoshī lái shuō, shénme shì zuì nán zuò dào de?", "Unda sizningcha, o'qituvchi uchun eng qiyin narsa nima?", "Тогда, по-вашему, что труднее всего для учителя?", "Пас, ба фикри шумо барои муаллим чӣ чиз аз ҳама душвортар аст?"),
                _line("王教授", "世界上没有完全相同的叶子，同样地，世界上也没有完全一样的人。所以，在教育学生时，要根据学生的特点选择不同的方法，我想这应该是最不容易做到的。", "Shìjiè shang méiyǒu wánquán xiāngtóng de yèzi, tóngyàng de, shìjiè shang yě méiyǒu wánquán yíyàng de rén. Suǒyǐ, zài jiàoyù xuésheng shí, yào gēnjù xuésheng de tèdiǎn xuǎnzé bùtóng de fāngfǎ, wǒ xiǎng zhè yīnggāi shì zuì bù róngyì zuò dào de.", "Dunyoda butunlay bir xil barg bo'lmaganidek, butunlay bir xil odam ham yo'q. Shuning uchun o'quvchini tarbiyalashda uning xususiyatiga qarab turli usul tanlash kerak, menimcha eng qiyini shu.", "В мире нет полностью одинаковых листьев, и так же нет полностью одинаковых людей. Поэтому в обучении студентов нужно выбирать методы по их особенностям, думаю, это самое трудное.", "Дар ҷаҳон барги комилан якхела нест, ҳамчунин одамони комилан якхела ҳам нестанд. Бинобар ин ҳангоми таълим бояд мувофиқи хусусияти донишҷӯ усули гуногун интихоб кард, ба назарам душвортаринаш ҳамин аст."),
            ],
        },
        {
            "block_no": 4,
            "section_label": "课文 4",
            "scene_uz": "Tildan to'g'ri foydalanish inson xarakterini ko'rsatishi haqida matn",
            "scene_ru": "Текст о том, как речь отражает характер человека",
            "scene_tj": "Матн дар бораи он ки гуфтор хислати инсонро нишон медиҳад",
            "word_nos": [19, 20, 21, 22, 23, 24],
            "grammar_nos": [3],
            "dialogue": [
                _line("旁白", "人人都会使用语言，但是怎么用语言把话说好却是一门艺术。", "Rénrén dōu huì shǐyòng yǔyán, dànshì zěnme yòng yǔyán bǎ huà shuō hǎo què shì yì mén yìshù.", "Hamma tildan foydalana oladi, lekin tildan foydalanib gapni yaxshi aytish - bu san'at.", "Каждый умеет пользоваться языком, но хорошо говорить с помощью языка - это искусство.", "Ҳар кас забонро истифода бурда метавонад, аммо бо забон хуб сухан гуфтан санъат аст."),
                _line("旁白", "看一个人怎么说话，往往可以比较准确地判断出他是一个什么样的人。", "Kàn yí ge rén zěnme shuōhuà, wǎngwǎng kěyǐ bǐjiào zhǔnquè de pànduàn chū tā shì yí ge shénme yàng de rén.", "Odam qanday gapirishiga qarab, ko'pincha uning qanday insonligini ancha aniq baholash mumkin.", "По тому, как человек говорит, часто можно довольно точно судить, что он за человек.", "Аз тарзи сухани инсон аксаран метавон нисбатан дақиқ фаҳмид, ки ӯ чӣ гуна одам аст."),
                _line("旁白", "有的人心里怎么想，嘴上就怎么说，即使是别人的缺点，他也会直接说出来，这样的人虽然很诚实，但是可能会引起别人的误会。", "Yǒu de rén xīn li zěnme xiǎng, zuǐ shang jiù zěnme shuō, jíshǐ shì biérén de quēdiǎn, tā yě huì zhíjiē shuō chūlai, zhèyàng de rén suīrán hěn chéngshí, dànshì kěnéng huì yǐnqǐ biérén de wùhuì.", "Ba'zi odamlar ichida nima o'ylasa, shuni aytadi. Hatto boshqalarning kamchiligini ham to'g'ridan-to'g'ri aytadi. Bunday odam rostgo'y bo'lsa ham, boshqalarda tushunmovchilik keltirib chiqarishi mumkin.", "Некоторые говорят всё, что думают, и даже чужие недостатки высказывают прямо. Такой человек честный, но может вызвать недоразумение.", "Баъзе одамон ҳар чӣ дар дил доранд, ҳамонро мегӯянд. Ҳатто камбудии дигаронро рӯирост мегӯянд. Чунин одам ростқавл бошад ҳам, метавонад нофаҳмӣ ба вуҷуд орад."),
                _line("旁白", "有的人虽然也看到了别人的缺点，但却不会直接指出来，而是通过别的方法来提醒，让他认识到自己的缺点，这样的人会让人觉得更友好。", "Yǒu de rén suīrán yě kàndào le biérén de quēdiǎn, dàn què bú huì zhíjiē zhǐ chūlai, ér shì tōngguò bié de fāngfǎ lái tíxǐng, ràng tā rènshi dào zìjǐ de quēdiǎn, zhèyàng de rén huì ràng rén juéde gèng yǒuhǎo.", "Ba'zilar boshqalarning kamchiligini ko'rsa ham, uni to'g'ridan-to'g'ri ko'rsatmaydi, boshqa usul bilan eslatib, o'z kamchiligini anglatadi. Bunday odamlar do'stonaroq tuyuladi.", "Другие, хотя и видят недостатки, не указывают прямо, а напоминают другим способом, чтобы человек сам осознал недостаток. Такие люди кажутся дружелюбнее.", "Баъзеҳо камбудии дигаронро бинанд ҳам, рӯирост нишон намедиҳанд, балки бо роҳи дигар ёдрас мекунанд, то шахс камбудии худро фаҳмад. Чунин одамон дӯстона менамоянд."),
            ],
        },
        {
            "block_no": 5,
            "section_label": "课文 5",
            "scene_uz": "O'qishda va ishda to'g'ri metod tanlash haqida matn",
            "scene_ru": "Текст о выборе правильного метода в учёбе и делах",
            "scene_tj": "Матн дар бораи интихоби усули дуруст дар омӯзиш ва кор",
            "word_nos": [25, 26, 27, 28, 29, 30, 31, 32],
            "grammar_nos": [5],
            "dialogue": [
                _line("旁白", "无论做什么事情，都要注意方法，学习尤其是这样。使用正确的方法，我们做起事来能“事半功倍”，也就是说，能节约时间，用较少的力气，取得更好的效果。", "Wúlùn zuò shénme shìqing, dōu yào zhùyì fāngfǎ, xuéxí yóuqí shì zhèyàng. Shǐyòng zhèngquè de fāngfǎ, wǒmen zuò qǐ shì lai néng “shì bàn gōng bèi”, yě jiù shì shuō, néng jiéyuē shíjiān, yòng jiào shǎo de lìqi, qǔdé gèng hǎo de xiàoguǒ.", "Nima ish qilmaylik, usulga e'tibor berish kerak, o'qishda ayniqsa shunday. To'g'ri usul ishlatilsa, kam kuch bilan ko'p natija olinadi, ya'ni vaqt tejaladi, kamroq kuch bilan yaxshiroq natijaga erishiladi.", "Что бы мы ни делали, нужно обращать внимание на метод, особенно в учёбе. Правильный метод даёт больший результат меньшими усилиями, экономит время и силы.", "Ҳар коре кунем, бояд ба усул аҳамият диҳем, махсусан дар омӯзиш. Усули дуруст бо кӯшиши кам натиҷаи зиёд медиҳад, вақт ва қувватро сарфа мекунад."),
                _line("旁白", "相反，如果方法不对，可能花五倍甚至十倍的时间都不能完成任务，结果变成了“事倍功半”。", "Xiāngfǎn, rúguǒ fāngfǎ bú duì, kěnéng huā wǔ bèi shènzhì shí bèi de shíjiān dōu bù néng wánchéng rènwu, jiéguǒ biàn chéng le “shì bèi gōng bàn”.", "Aksincha, usul noto'g'ri bo'lsa, besh yoki hatto o'n baravar vaqt sarflab ham vazifani tugatolmaslik mumkin, natija esa ko'p kuch bilan kam natija bo'ladi.", "Наоборот, если метод неверный, можно потратить в пять или даже десять раз больше времени и не выполнить задачу, получив малый результат большими усилиями.", "Баръакс, агар усул нодуруст бошад, мумкин аст панҷ ё ҳатто даҳ баробар вақт сарф карда ҳам вазифаро анҷом надиҳем, натиҷа бошад кӯшиши зиёд ва самари кам мешавад."),
                _line("旁白", "有一点需要提醒大家，别人的方法也许很有效，但是并不一定适合自己。", "Yǒu yì diǎn xūyào tíxǐng dàjiā, biérén de fāngfǎ yěxǔ hěn yǒuxiào, dànshì bìng bù yídìng shìhé zìjǐ.", "Bir narsani eslatish kerak: boshqalarning usuli juda samarali bo'lishi mumkin, lekin u albatta sizga mos keladi degani emas.", "Нужно напомнить одно: чужой метод может быть эффективным, но не обязательно подходит вам.", "Як чизро бояд ёдрас кард: усули дигарон шояд хеле самаранок бошад, аммо ҳатман ба худи шумо мувофиқ нест."),
                _line("旁白", "因此，我们应该在听取别人意见的同时，仔细考虑一下，再根据不同的情况选择不同的方法，这样才能达到最好的效果。", "Yīncǐ, wǒmen yīnggāi zài tīngqǔ biérén yìjian de tóngshí, zǐxì kǎolǜ yíxià, zài gēnjù bùtóng de qíngkuàng xuǎnzé bùtóng de fāngfǎ, zhèyàng cái néng dádào zuì hǎo de xiàoguǒ.", "Shuning uchun boshqalarning fikrini tinglar ekanmiz, diqqat bilan o'ylab, turli vaziyatga qarab turli usul tanlashimiz kerak, shundagina eng yaxshi natijaga erishamiz.", "Поэтому, слушая мнения других, нужно тщательно подумать и выбирать методы по разным ситуациям, только так можно добиться лучшего результата.", "Бинобар ин, ҳангоми шунидани фикри дигарон бояд бодиққат фикр карда, мувофиқи вазъиятҳои гуногун усулҳои гуногун интихоб кунем, танҳо ҳамин тавр ба натиҷаи беҳтарин мерасем."),
            ],
        },
    ],
}


_LESSON_13 = {
    "title": "喝着茶看京剧",
    "goal": {
        "uz": "Pekin operasi, an'anaviy madaniyat, chopstik va choy haqida gapirish; 大概, 偶尔, 由, 进行 va 随着 grammatikalarini ishlatish",
        "ru": "говорить о пекинской опере, традиционной культуре, палочках и чае; использовать 大概, 偶尔, 由, 进行 и 随着",
        "tj": "дар бораи операи Пекин, фарҳанги суннатӣ, чӯбчаҳои хӯрок ва чой гуфтугӯ кардан; истифодаи 大概, 偶尔, 由, 进行 ва 随着",
    },
    "intro_text": {
        "uz": "Bu darsda Pekin operasi, chet ellik talabalar uchun Xitoy madaniyati, chopstikdan foydalanish va choy madaniyati haqida gapirishni o'rganasiz.",
        "ru": "В этом уроке вы научитесь говорить о пекинской опере, китайской культуре для иностранных студентов, использовании палочек и чайной культуре.",
        "tj": "Дар ин дарс дар бораи операи Пекин, фарҳанги Чин барои донишҷӯёни хориҷӣ, истифодаи чӯбчаҳо ва фарҳанги чой гуфтугӯ карданро меомӯзед.",
    },
    "vocabulary": [
        _word(1, "京剧", "jīngjù", "n.", "Pekin operasi", "пекинская опера", "операи Пекин"),
        _word(2, "演员", "yǎnyuán", "n.", "aktyor", "актёр", "актёр"),
        _word(3, "观众", "guānzhòng", "n.", "tomoshabin", "зрители, публика", "тамошобинон"),
        _word(4, "厚", "hòu", "adj.", "chuqur, qalin", "глубокий, толстый", "чуқур, ғафс"),
        _word(5, "演出", "yǎnchū", "v.", "sahnalashtirmoq, chiqish qilmoq", "выступать, давать представление", "намоиш додан, баромад кардан"),
        _word(6, "大概", "dàgài", "adv.", "taxminan", "примерно, вероятно", "тақрибан, эҳтимол"),
        _word(7, "来自", "láizì", "v.", "...dan kelmoq", "быть родом из", "аз ... омадан"),
        _word(8, "遍", "biàn", "m.", "marta, boshidan oxirigacha", "раз, от начала до конца", "маротиба, аз аввал то охир"),
        _word(9, "偶尔", "ǒu'ěr", "adv.", "ba'zan, gohida", "иногда, изредка", "гоҳ-гоҳ"),
        _word(10, "吃惊", "chījīng", "v.", "hayron qolmoq", "удивляться", "ҳайрон шудан"),
        _word(11, "基础", "jīchǔ", "n.", "asos, poydevor", "основа, база", "асос, поя"),
        _word(12, "表演", "biǎoyǎn", "v.", "ijro etmoq, ko'rsatmoq", "исполнять, выступать", "иҷро кардан, намоиш додан"),
        _word(13, "正常", "zhèngcháng", "adj.", "normal, odatiy", "нормальный", "муқаррарӣ"),
        _word(14, "申请", "shēnqǐng", "v.", "ariza bermoq", "подавать заявку", "ариза додан"),
        _word(15, "有趣", "yǒuqù", "adj.", "qiziqarli", "интересный", "ҷолиб"),
        _word(16, "开心", "kāixīn", "adj.", "xursand", "радостный, весёлый", "хурсанд"),
        _word(17, "继续", "jìxù", "v.", "davom etmoq", "продолжать", "давом додан"),
        _word(18, "由", "yóu", "prep.", "tomonidan", "кем-либо, от", "аз тарафи"),
        _word(19, "讨论", "tǎolùn", "v.", "muhokama qilmoq", "обсуждать", "муҳокима кардан"),
        _word(20, "大约", "dàyuē", "adv.", "taxminan", "примерно", "тақрибан"),
        _word(21, "餐厅", "cāntīng", "n.", "restoran, oshxona", "ресторан, столовая", "ошхона, тарабхона"),
        _word(22, "纸袋", "zhǐdài", "n.", "qog'oz paket", "бумажный пакет", "халтаи коғазӣ"),
        _word(23, "袋（子）", "dài(zi)", "n.", "paket, xalta", "пакет, мешок", "халта"),
        _word(24, "互联网", "hùliánwǎng", "n.", "internet", "интернет", "интернет"),
        _word(25, "进行", "jìnxíng", "v.", "amalga oshirmoq, olib bormoq", "проводить, осуществлять", "гузаронидан, анҷом додан"),
        _word(26, "错误", "cuòwù", "n.", "xato", "ошибка", "хато"),
        _word(27, "随着", "suízhe", "prep.", "...bilan birga, ...sari", "по мере, вместе с", "бо гузашти, ҳамроҳ бо"),
        _word(28, "十分", "shífēn", "adv.", "juda, nihoyatda", "очень, весьма", "хеле, бисёр"),
        _word(29, "普遍", "pǔbiàn", "adj.", "keng tarqalgan", "распространённый", "маъмул, паҳншуда"),
        _word(30, "部分", "bùfen", "n.", "qism", "часть", "қисм"),
        _word(31, "稍微", "shāowēi", "adv.", "biroz", "немного, слегка", "каме"),
        _word(32, "苦", "kǔ", "adj.", "achchiq", "горький", "талх"),
        _word(33, "省", "shěng", "n.", "provinsiya", "провинция", "вилоят"),
        _word(34, "广东省", "Guǎngdōng Shěng", "proper n.", "Guangdong provinsiyasi", "провинция Гуандун", "вилояти Гуандун"),
    ],
    "grammar": [
        _grammar(1, "大概", "taxminan; ehtimol", "примерно; вероятно", "тақрибан; эҳтимол", "Aniq bo'lmagan son yoki ehtimoliy fikrni bildiradi.", "Указывает приблизительное количество или вероятное мнение.", "Миқдори тахминӣ ё фикри эҳтимолиро нишон медиҳад.", "到现在大概唱了60多年了。", "Dào xiànzài dàgài chàng le liùshí duō nián le.", "Hozirgacha taxminan oltmish yildan ko'proq kuylagan.", "К настоящему времени он поёт уже примерно больше шестидесяти лет.", "То имрӯз тақрибан зиёда аз шаст сол сурудааст."),
        _grammar(2, "偶尔", "ba'zan, gohida", "иногда, изредка", "гоҳ-гоҳ", "Harakat doimiy emas, faqat ayrim payt bo'lishini bildiradi.", "Показывает, что действие происходит не постоянно, а иногда.", "Нишон медиҳад, ки амал доимӣ нест, гоҳ-гоҳ мешавад.", "偶尔跟中国人一起唱上几句。", "Ǒu'ěr gēn Zhōngguó rén yìqǐ chàng shang jǐ jù.", "Ba'zan xitoyliklar bilan bir necha misra kuylab qo'yaman.", "Иногда пою несколько строк вместе с китайцами.", "Гоҳ-гоҳ бо чиниҳо чанд ҷумла месароям."),
        _grammar(3, "由", "tomonidan", "кем-либо; от", "аз тарафи", "Ish kim tomonidan bajarilishini ko'rsatadi.", "Показывает, кем выполняется действие.", "Нишон медиҳад, ки амал аз тарафи кӣ иҷро мешавад.", "这次活动继续由你负责。", "Zhè cì huódòng jìxù yóu nǐ fùzé.", "Bu tadbirga yana sen mas'ul bo'lasan.", "За это мероприятие снова отвечаешь ты.", "Ин чорабинӣ боз аз тарафи ту масъулона бурда мешавад."),
        _grammar(4, "进行", "amalga oshirmoq, olib bormoq", "проводить, осуществлять", "гузаронидан, анҷом додан", "Rasmiyroq uslubda tadqiqot, muhokama, tekshiruv kabi ishlarni bajarishni bildiradi.", "В более официальном стиле обозначает проведение исследования, обсуждения, проверки и т.п.", "Бо услуби расмитар гузаронидани таҳқиқ, муҳокима, санҷиш ва ғайраро мефаҳмонад.", "有人在互联网上专门进行过调查。", "Yǒu rén zài hùliánwǎng shang zhuānmén jìnxíng guo diàochá.", "Kimdir internetda maxsus so'rov o'tkazgan.", "Кто-то специально проводил опрос в интернете.", "Касе дар интернет махсус таҳқиқ гузаронидааст."),
        _grammar(5, "随着", "...bilan birga; ...sari", "по мере; вместе с", "бо гузашти; ҳамроҳ бо", "Bir holat o'zgargani sari ikkinchi holat ham o'zgarishini bildiradi.", "Показывает, что с изменением одного состояния меняется другое.", "Нишон медиҳад, ки бо тағйири як ҳолат ҳолати дигар ҳам тағйир меёбад.", "随着人们对茶的认识的加深，慢慢开始把它当作解渴的饮料。", "Suízhe rénmen duì chá de rènshi de jiāshēn, mànmàn kāishǐ bǎ tā dàngzuò jiěkě de yǐnliào.", "Odamlarning choy haqidagi tushunchasi chuqurlashgani sari, uni asta-sekin chanqoq bosadigan ichimlik deb qabul qila boshlashdi.", "По мере углубления знаний о чае люди постепенно стали воспринимать его как напиток для утоления жажды.", "Бо амиқ шудани фаҳмиши мардум дар бораи чой, онро оҳиста-оҳиста нӯшокии рафъи ташнагӣ донистанд."),
    ],
    "dialogues": [
        {
            "block_no": 1,
            "section_label": "课文 1",
            "scene_uz": "Xiaoyu va Xiaxia bobosi Pekin operasi kuylashi haqida gaplashadi",
            "scene_ru": "Сяоюй и Сяося говорят о том, как дедушка Сяося поёт пекинскую оперу",
            "scene_tj": "Сяоюй ва Сяося дар бораи операи Пекини бобои Сяося суҳбат мекунанд",
            "word_nos": [1, 2, 3, 4, 5, 6],
            "grammar_nos": [1],
            "dialogue": [
                _line("小雨", "小夏，你爷爷京剧唱得真专业，我还以为他是京剧演员呢。", "Xiǎo Xià, nǐ yéye jīngjù chàng de zhēn zhuānyè, wǒ hái yǐwéi tā shì jīngjù yǎnyuán ne.", "Xiaxia, bobongiz Pekin operasini juda professional kuylarkan, uni aktyor deb o'ylabman.", "Сяося, твой дедушка так профессионально поёт пекинскую оперу, я думал, он актёр.", "Сяося, бобоят операи Пекинро бисёр касбӣ месарояд, ман фикр кардам ӯ актёр аст."),
                _line("小夏", "对啊，他本来就是京剧演员，年轻时在我们那儿很有名，深受观众们的喜爱。", "Duì a, tā běnlái jiùshì jīngjù yǎnyuán, niánqīng shí zài wǒmen nàr hěn yǒumíng, shēn shòu guānzhòng men de xǐ'ài.", "Ha, u aslida Pekin operasi aktyori bo'lgan, yoshligida biz tomonda juda mashhur, tomoshabinlar uni juda yaxshi ko'rgan.", "Да, он и был актёром пекинской оперы. В молодости он был у нас очень известен и любим зрителями.", "Ҳа, ӯ аслан актёри операи Пекин буд, ҷавонӣ дар ҷои мо хеле машҳур ва дӯстдоштаи тамошобинон буд."),
                _line("小雨", "你爷爷一定对京剧有着很深厚的感情。", "Nǐ yéye yídìng duì jīngjù yǒuzhe hěn shēnhòu de gǎnqíng.", "Bobongizning Pekin operasiga muhabbati juda chuqur bo'lsa kerak.", "У твоего дедушки наверняка очень глубокие чувства к пекинской опере.", "Бобоят ба операи Пекин эҳсоси хеле амиқ дорад."),
                _line("小夏", "是呀，他8岁就开始上台演出，到现在大概唱了60多年了，他对这门艺术的喜爱从来没有改变过。", "Shì ya, tā bā suì jiù kāishǐ shàng tái yǎnchū, dào xiànzài dàgài chàng le liùshí duō nián le, tā duì zhè mén yìshù de xǐ'ài cónglái méiyǒu gǎibiàn guo.", "Ha, u 8 yoshidan sahnaga chiqqan, hozirgacha taxminan oltmish yildan ko'proq kuylagan, bu san'atga muhabbati hech qachon o'zgarmagan.", "Да, он начал выступать на сцене в 8 лет и поёт уже примерно больше шестидесяти лет. Его любовь к этому искусству никогда не менялась.", "Ҳа, аз 8-солагӣ ба саҳна баромадааст, то имрӯз тақрибан беш аз шаст сол сурудааст, муҳаббаташ ба ин санъат ҳеҷ гоҳ тағйир наёфтааст."),
                _line("小雨", "这么说你喜欢听京剧也是受了你爷爷的影响？", "Zhème shuō nǐ xǐhuan tīng jīngjù yě shì shòu le nǐ yéye de yǐngxiǎng?", "Demak, Pekin operasini yoqtirishingga ham bobongiz ta'sir qilganmi?", "Значит, любовь к пекинской опере у тебя тоже под влиянием дедушки?", "Пас, дӯст доштани операи Пекин ҳам аз таъсири бобоят будааст?"),
                _line("小夏", "我小时候经常去看他的演出。平时他还给我讲很多京剧里的历史故事，让我学到了很多知识。", "Wǒ xiǎoshíhou jīngcháng qù kàn tā de yǎnchū. Píngshí tā hái gěi wǒ jiǎng hěn duō jīngjù li de lìshǐ gùshi, ràng wǒ xué dào le hěn duō zhīshi.", "Bolaligimda uning chiqishlarini tez-tez ko'rgani borardim. Odatda u menga Pekin operasidagi ko'p tarixiy hikoyalarni aytib berib, ko'p bilim o'rgatgan.", "В детстве я часто ходил смотреть его выступления. Обычно он ещё рассказывал мне много исторических сюжетов из оперы, и я многое узнал.", "Кӯдакӣ зуд-зуд намоишҳои ӯро медидaм. Одатан ба ман ҳикояҳои таърихии операи Пекинро мегуфт ва ман бисёр чиз омӯхтам."),
            ],
        },
        {
            "block_no": 2,
            "section_label": "课文 2",
            "scene_uz": "Xiaoyu va Mark Pekin operasini qanday o'rganganini muhokama qiladi",
            "scene_ru": "Сяоюй и Марк обсуждают, как Марк выучил пекинскую оперу",
            "scene_tj": "Сяоюй ва Марк муҳокима мекунанд, ки Марк операи Пекинро чӣ гуна омӯхтааст",
            "word_nos": [7, 8, 9, 10, 11, 12],
            "grammar_nos": [2],
            "dialogue": [
                _line("小雨", "真没想到你一个来自美国的外国留学生，能把京剧唱得这么好。", "Zhēn méi xiǎngdào nǐ yí ge láizì Měiguó de wàiguó liúxuéshēng, néng bǎ jīngjù chàng de zhème hǎo.", "AQShdan kelgan chet ellik talaba bo'lib, Pekin operasini bunchalik yaxshi kuylashingni kutmagandim.", "Не ожидал, что иностранный студент из США может так хорошо петь пекинскую оперу.", "Фикр намекардам, ки донишҷӯи хориҷӣ аз Амрико операи Пекинро ин қадар хуб месарояд."),
                _line("马克", "我常常跟着电视学唱京剧，然后一遍一遍地练习，偶尔跟中国人一起唱上几句。", "Wǒ chángcháng gēnzhe diànshì xué chàng jīngjù, ránhòu yí biàn yí biàn de liànxí, ǒu'ěr gēn Zhōngguó rén yìqǐ chàng shang jǐ jù.", "Men ko'pincha televizorga ergashib Pekin operasi kuylashni o'rganaman, keyin qayta-qayta mashq qilaman, ba'zida xitoyliklar bilan bir necha misra kuylayman.", "Я часто учусь петь пекинскую оперу по телевизору, затем многократно практикуюсь, иногда пою несколько строк с китайцами.", "Ман аксар вақт аз телевизор операи Пекинро ёд мегирам, баъд такрор ба такрор машқ мекунам, гоҳ-гоҳ бо чиниҳо чанд ҷумла месароям."),
                _line("小雨", "难道你从来没有接受过京剧方面的专门教育吗？", "Nándào nǐ cónglái méiyǒu jiēshòu guo jīngjù fāngmiàn de zhuānmén jiàoyù ma?", "Nahotki Pekin operasi bo'yicha hech qachon maxsus ta'lim olmagan bo'lsang?", "Неужели ты никогда не получал специального образования по пекинской опере?", "Наход ту ҳеҷ гоҳ аз рӯи операи Пекин таълими махсус нагирифтаӣ?"),
                _line("马克", "别吃惊，因为我以前学习过音乐，有一些音乐基础，又对京剧这种表演艺术非常感兴趣，所以能比较容易地学会它的唱法。", "Bié chījīng, yīnwèi wǒ yǐqián xuéxí guo yīnyuè, yǒu yìxiē yīnyuè jīchǔ, yòu duì jīngjù zhè zhǒng biǎoyǎn yìshù fēicháng gǎn xìngqù, suǒyǐ néng bǐjiào róngyì de xuéhuì tā de chàngfǎ.", "Hayron bo'lma, oldin musiqa o'rganganman, ozgina musiqiy asosim bor, yana Pekin operasi kabi sahna san'atiga juda qiziqaman, shuning uchun kuylash usulini nisbatan oson o'rgandim.", "Не удивляйся: раньше я изучал музыку, у меня есть основа, и мне очень интересна такая исполнительская форма, поэтому я довольно легко освоил манеру пения.", "Ҳайрон нашав: пештар мусиқӣ омӯхтаам, каме асоси мусиқӣ дорам ва ба чунин санъати иҷро хеле шавқ дорам, барои ҳамин тарзи сурудашро нисбатан осон омӯхтам."),
                _line("小雨", "你真厉害！竟然连很多中国人都听不懂的京剧也能学会。我还是比较喜欢听流行音乐。", "Nǐ zhēn lìhai! Jìngrán lián hěn duō Zhōngguó rén dōu tīng bù dǒng de jīngjù yě néng xuéhuì. Wǒ háishi bǐjiào xǐhuan tīng liúxíng yīnyuè.", "Juda zo'rsan! Ko'p xitoyliklar ham tushunmaydigan Pekin operasini o'rgana olibsan. Men baribir pop musiqa tinglashni ko'proq yoqtiraman.", "Ты молодец! Даже пекинскую оперу, которую многие китайцы не понимают, смог выучить. А я всё-таки больше люблю поп-музыку.", "Ту зӯрӣ! Ҳатто операи Пекинро, ки бисёр чиниҳо намефаҳманд, ёд гирифтаӣ. Ман бошад бештар мусиқии попро дӯст медорам."),
                _line("马克", "那是你不了解京剧的唱法。在音乐方面，京剧给了我很多新的想法。我还把京剧的一些特点增加到了自己的音乐中，达到了很好的效果。", "Nà shì nǐ bù liǎojiě jīngjù de chàngfǎ. Zài yīnyuè fāngmiàn, jīngjù gěi le wǒ hěn duō xīn de xiǎngfǎ. Wǒ hái bǎ jīngjù de yìxiē tèdiǎn zēngjiā dào le zìjǐ de yīnyuè zhōng, dádào le hěn hǎo de xiàoguǒ.", "Bu sen Pekin operasi kuylash usulini tushunmaganing uchun. Musiqa borasida Pekin operasi menga ko'p yangi fikr berdi. Men hatto uning ayrim xususiyatlarini o'z musiqamga qo'shib, yaxshi natijaga erishdim.", "Это потому, что ты не понимаешь манеру пения пекинской оперы. В музыке она дала мне много новых идей. Я добавил некоторые её особенности в свою музыку и получил хороший эффект.", "Ин барои он аст, ки ту тарзи сурудани операи Пекинро намефаҳмӣ. Дар мусиқӣ он ба ман фикрҳои нав дод. Ман баъзе хусусиятҳои онро ба мусиқии худ илова карда, натиҷаи хуб гирифтам."),
            ],
        },
        {
            "block_no": 3,
            "section_label": "课文 3",
            "scene_uz": "Li o'qituvchi madaniyat festivali o'tkazish uchun ruxsat so'raydi",
            "scene_ru": "Учитель Ли просит разрешение провести фестиваль китайской культуры",
            "scene_tj": "Муаллим Ли барои гузаронидани фестивали фарҳанги Чин иҷозат мепурсад",
            "word_nos": [13, 14, 15, 16, 17, 18, 19],
            "grammar_nos": [3],
            "dialogue": [
                _line("李老师", "校长，因为外国留学生不了解中国文化，有时候会影响他们和中国人之间的正常交流，甚至还可能引起误会，带来麻烦，所以我们想申请举办一次中国传统文化节活动。", "Xiàozhǎng, yīnwèi wàiguó liúxuéshēng bù liǎojiě Zhōngguó wénhuà, yǒu shíhou huì yǐngxiǎng tāmen hé Zhōngguó rén zhījiān de zhèngcháng jiāoliú, shènzhì hái kěnéng yǐnqǐ wùhuì, dàilái máfan, suǒyǐ wǒmen xiǎng shēnqǐng jǔbàn yí cì Zhōngguó chuántǒng wénhuà jié huódòng.", "Direktor, chet ellik talabalar Xitoy madaniyatini yaxshi bilmagani uchun ba'zan ularning xitoyliklar bilan normal muloqotiga ta'sir qiladi, hatto tushunmovchilik va muammo keltirishi mumkin. Shuning uchun Xitoy an'anaviy madaniyat festivali o'tkazishga ariza bermoqchimiz.", "Директор, иностранные студенты не знают китайскую культуру, поэтому иногда это влияет на нормальное общение с китайцами и даже вызывает недоразумения. Поэтому мы хотим подать заявку на проведение фестиваля традиционной китайской культуры.", "Ҷаноби директор, донишҷӯёни хориҷӣ фарҳанги Чинро намедонанд, баъзан ин ба муоширати онҳо бо чиниҳо таъсир мекунад ва ҳатто нофаҳмӣ меорад. Барои ҳамин мехоҳем барои фестивали фарҳанги суннатии Чин ариза диҳем."),
                _line("校长", "你们的想法很好，举办文化节活动，一方面能让各国学生更好地了解中国，另一方面也能为学生们提供互相交流和学习的机会。", "Nǐmen de xiǎngfǎ hěn hǎo, jǔbàn wénhuà jié huódòng, yì fāngmiàn néng ràng gè guó xuésheng gèng hǎo de liǎojiě Zhōngguó, lìng yì fāngmiàn yě néng wèi xuésheng men tígōng hùxiāng jiāoliú hé xuéxí de jīhuì.", "Fikringiz yaxshi. Madaniyat festivali bir tomondan turli mamlakat talabalariga Xitoyni yaxshiroq tushunishga yordam beradi, boshqa tomondan o'zaro muloqot va o'rganish imkonini beradi.", "Хорошая идея. Такой фестиваль, с одной стороны, поможет студентам разных стран лучше понять Китай, с другой - даст возможность общаться и учиться друг у друга.", "Фикратон хуб аст. Фестивали фарҳанг аз як тараф ба донишҷӯёни кишварҳои гуногун Чинро беҳтар мефаҳмонад, аз тарафи дигар имкони муошират ва омӯзиши байниҳамдигарӣ медиҳад."),
                _line("李老师", "谢谢您的支持！", "Xièxie nín de zhīchí!", "Qo'llab-quvvatlaganingiz uchun rahmat!", "Спасибо за вашу поддержку!", "Барои дастгириятон раҳмат!"),
                _line("校长", "上次的春游活动你们办得非常有趣，大家都玩儿得很开心，这次活动继续由你负责，相信也一定会很成功。", "Shàng cì de chūnyóu huódòng nǐmen bàn de fēicháng yǒuqù, dàjiā dōu wánr de hěn kāixīn, zhè cì huódòng jìxù yóu nǐ fùzé, xiāngxìn yě yídìng huì hěn chénggōng.", "O'tgan safargi bahor sayohatini juda qiziqarli o'tkazgandingiz, hamma xursand bo'lgandi. Bu tadbirga ham sen mas'ul bo'l, ishonamanki muvaffaqiyatli bo'ladi.", "Прошлая весенняя поездка у вас получилась очень интересной, все были довольны. За это мероприятие снова отвечаешь ты, уверен, оно тоже будет успешным.", "Сайри баҳории гузаштаатон хеле ҷолиб буд, ҳама хурсанд шуданд. Ин чорабинӣ ҳам аз тарафи ту идора шавад, бовар дорам муваффақ мешавад."),
                _line("李老师", "我们回去就开会讨论，星期五之前把详细的计划书发给您。", "Wǒmen huíqù jiù kāihuì tǎolùn, xīngqīwǔ zhīqián bǎ xiángxì de jìhuàshū fā gěi nín.", "Qaytiboq yig'ilishda muhokama qilamiz va juma kunigacha batafsil reja hujjatini sizga yuboramiz.", "Мы вернёмся, сразу обсудим на собрании и до пятницы отправим вам подробный план.", "Баргашта, дар ҷаласа муҳокима мекунем ва то рӯзи ҷумъа нақшаи муфассалро ба шумо мефиристем."),
                _line("校长", "好的，准备过程中有什么问题，你们可以直接来找我。", "Hǎo de, zhǔnbèi guòchéng zhōng yǒu shénme wèntí, nǐmen kěyǐ zhíjiē lái zhǎo wǒ.", "Yaxshi, tayyorgarlik jarayonida muammo bo'lsa, to'g'ridan-to'g'ri menga murojaat qilinglar.", "Хорошо, если в процессе подготовки будут вопросы, можете прямо обращаться ко мне.", "Хуб, агар дар раванди омодагӣ мушкил шавад, метавонед бевосита ба ман муроҷиат кунед."),
            ],
        },
        {
            "block_no": 4,
            "section_label": "课文 4",
            "scene_uz": "Chopstikdan to'g'ri foydalanish haqida matn",
            "scene_ru": "Текст о правильном использовании палочек",
            "scene_tj": "Матн дар бораи истифодаи дурусти чӯбчаҳо",
            "word_nos": [20, 21, 22, 23, 24, 25, 26],
            "grammar_nos": [4],
            "dialogue": [
                _line("旁白", "筷子在中国大约已经有3000多年的历史了。对外国人来说，使用筷子吃饭并不容易，所以，国外的一些中国餐厅在放筷子的纸袋上会提供使用筷子的详细说明。", "Kuàizi zài Zhōngguó dàyuē yǐjīng yǒu sānqiān duō nián de lìshǐ le. Duì wàiguó rén lái shuō, shǐyòng kuàizi chīfàn bìng bù róngyì, suǒyǐ, guówài de yìxiē Zhōngguó cāntīng zài fàng kuàizi de zhǐdài shang huì tígōng shǐyòng kuàizi de xiángxì shuōmíng.", "Chopstiklar Xitoyda taxminan 3000 yildan ortiq tarixga ega. Chet elliklar uchun chopstik bilan ovqatlanish oson emas, shuning uchun xorijdagi ba'zi xitoy restoranlari chopstik solingan qog'oz paketda batafsil ko'rsatma beradi.", "Палочки в Китае имеют историю примерно более 3000 лет. Иностранцам нелегко есть палочками, поэтому некоторые китайские рестораны за рубежом дают подробную инструкцию на бумажном пакете для палочек.", "Чӯбчаҳо дар Чин тақрибан зиёда аз 3000 сол таърих доранд. Барои хориҷиён бо чӯбча хӯрок хӯрдан осон нест, бинобар ин баъзе тарабхонаҳои чинӣ дар хориҷ дар халтаи коғазии чӯбчаҳо дастури муфассал медиҳанд."),
                _line("旁白", "不过，如果你认为每个中国人都会正确使用筷子，那就错了。", "Búguò, rúguǒ nǐ rènwéi měi ge Zhōngguó rén dōu huì zhèngquè shǐyòng kuàizi, nà jiù cuò le.", "Lekin har bir xitoylik chopstikdan to'g'ri foydalana oladi deb o'ylasangiz, adashasiz.", "Но если вы думаете, что каждый китаец правильно пользуется палочками, вы ошибаетесь.", "Аммо агар фикр кунед, ки ҳар чинӣ чӯбчаро дуруст истифода мебарад, хато мекунед."),
                _line("旁白", "有人在互联网上专门进行过调查，结果发现每六个中国人中就有一个使用筷子的方法是错误的。", "Yǒu rén zài hùliánwǎng shang zhuānmén jìnxíng guo diàochá, jiéguǒ fāxiàn měi liù ge Zhōngguó rén zhōng jiù yǒu yí ge shǐyòng kuàizi de fāngfǎ shì cuòwù de.", "Kimdir internetda maxsus so'rov o'tkazgan va natijada har olti xitoylikdan bittasi chopstikdan noto'g'ri foydalanishi aniqlangan.", "Кто-то специально провёл опрос в интернете и выяснил, что один из шести китайцев пользуется палочками неправильно.", "Касе дар интернет махсус таҳқиқ гузаронидааст ва маълум шудааст, ки аз ҳар шаш чинӣ яке чӯбчаро нодуруст истифода мебарад."),
                _line("旁白", "如果你想正确使用筷子，那就好好练习吧。", "Rúguǒ nǐ xiǎng zhèngquè shǐyòng kuàizi, nà jiù hǎohāo liànxí ba.", "Agar chopstikdan to'g'ri foydalanmoqchi bo'lsangiz, yaxshilab mashq qiling.", "Если хотите правильно пользоваться палочками, хорошо потренируйтесь.", "Агар хоҳед чӯбчаро дуруст истифода баред, хуб машқ кунед."),
            ],
        },
        {
            "block_no": 5,
            "section_label": "课文 5",
            "scene_uz": "Xitoy choy madaniyati haqida matn",
            "scene_ru": "Текст о китайской чайной культуре",
            "scene_tj": "Матн дар бораи фарҳанги чойи Чин",
            "word_nos": [27, 28, 29, 30, 31, 32, 33, 34],
            "grammar_nos": [5],
            "dialogue": [
                _line("旁白", "茶在中国有几千年的历史，是中国最常见的饮料。最早的时候，茶只是被当作一种药，而不是饮料。", "Chá zài Zhōngguó yǒu jǐqiān nián de lìshǐ, shì Zhōngguó zuì chángjiàn de yǐnliào. Zuì zǎo de shíhou, chá zhǐshì bèi dàngzuò yì zhǒng yào, ér bú shì yǐnliào.", "Choy Xitoyda bir necha ming yillik tarixga ega va Xitoyda eng keng tarqalgan ichimlikdir. Eng boshida choy ichimlik emas, dori sifatida ko'rilgan.", "Чай в Китае имеет историю в несколько тысяч лет и является самым распространённым напитком. В самом начале чай считался лекарством, а не напитком.", "Чой дар Чин чанд ҳазор сол таърих дорад ва маъмултарин нӯшокии Чин аст. Дар аввал чойро нӯшокӣ не, балки дору мешумориданд."),
                _line("旁白", "后来，随着人们对茶的认识的加深，慢慢开始把它当作解渴的饮料，这才慢慢有了中国的茶文化。", "Hòulái, suízhe rénmen duì chá de rènshi de jiāshēn, mànmàn kāishǐ bǎ tā dàngzuò jiěkě de yǐnliào, zhè cái mànmàn yǒu le Zhōngguó de chá wénhuà.", "Keyinchalik odamlarning choy haqidagi tushunchasi chuqurlashgani sari, uni asta-sekin chanqoq bosadigan ichimlik deb qabul qila boshlashdi va shundan Xitoy choy madaniyati paydo bo'ldi.", "Позже, по мере углубления понимания чая, люди постепенно стали считать его напитком для утоления жажды, и так постепенно возникла китайская чайная культура.", "Баъдтар, бо амиқ шудани фаҳмиши мардум дар бораи чой, онро оҳиста-оҳиста нӯшокии рафъи ташнагӣ донистанд ва ҳамин тавр фарҳанги чойи Чин пайдо шуд."),
                _line("旁白", "在中国，喝茶是一种十分普遍的生活习惯。对很多中国人来说，喝茶已成为他们生活中不可缺少的一部分。", "Zài Zhōngguó, hē chá shì yì zhǒng shífēn pǔbiàn de shēnghuó xíguàn. Duì hěn duō Zhōngguó rén lái shuō, hē chá yǐ chéngwéi tāmen shēnghuó zhōng bù kě quēshǎo de yí bùfen.", "Xitoyda choy ichish juda keng tarqalgan hayotiy odat. Ko'p xitoyliklar uchun choy ichish hayotining ajralmas qismiga aylangan.", "В Китае пить чай - очень распространённая жизненная привычка. Для многих китайцев чай стал неотъемлемой частью жизни.", "Дар Чин чой нӯшидан одати хеле маъмул аст. Барои бисёр чиниҳо чой нӯшидан қисми ҷудонашавандаи зиндагӣ шудааст."),
                _line("旁白", "但是有的饮料虽然名字叫“茶”，却并不是真正的茶。比如广东省的人爱喝的“凉茶”，它的味道稍微有点儿苦，其实是一种用中药做成的饮料。", "Dànshì yǒu de yǐnliào suīrán míngzi jiào “chá”, què bìng bú shì zhēnzhèng de chá. Bǐrú Guǎngdōng Shěng de rén ài hē de “liángchá”, tā de wèidào shāowēi yǒu diǎnr kǔ, qíshí shì yì zhǒng yòng zhōngyào zuò chéng de yǐnliào.", "Lekin ayrim ichimliklar nomida choy bo'lsa ham, haqiqiy choy emas. Masalan, Guangdongdagilar yoqtiradigan liangcha biroz achchiq bo'ladi, aslida u xitoy dorivor o'simliklaridan tayyorlangan ichimlik.", "Но некоторые напитки называются «чаем», хотя настоящим чаем не являются. Например, любимый в провинции Гуандун «ляньча» немного горький, на самом деле это напиток из китайских лекарственных трав.", "Аммо баъзе нӯшокиҳо номашон «чой» бошад ҳам, чойи ҳақиқӣ нестанд. Масалан, «лянча»-е, ки мардуми Гуандун дӯст медоранд, каме талх аст ва дар асл аз доруҳои чинӣ тайёр мешавад."),
            ],
        },
    ],
}


def _add_lesson_12_13():
    HSK4_LOWER_PDF_MATERIALS[12] = copy.deepcopy(_LESSON_12)
    HSK4_LOWER_PDF_MATERIALS[13] = copy.deepcopy(_LESSON_13)


_add_lesson_12_13()


def apply_hsk4_lower_pdf_materials(lesson):
    raw_data = HSK4_LOWER_PDF_MATERIALS.get(int(lesson.get("lesson_order") or 0))
    data = copy.deepcopy(raw_data) if raw_data else None
    if not data:
        return lesson

    vocab = data["vocabulary"]
    grammar = data["grammar"]
    dialogues = data["dialogues"]

    for block in dialogues:
        block_no = int(block.get("block_no") or 0)
        words = [_word_by_no(vocab, no) for no in block.get("word_nos", [])]
        words = [word for word in words if word]
        block["mini_quiz"] = _mini_quiz(lesson["lesson_order"], block_no, vocab, grammar, block)
        block["mini_homework"] = _mini_homework(block_no, words)

    exercises, answers = _exercise_payload(vocab, grammar)
    lesson["title"] = data["title"]
    lesson["goal"] = _j(data["goal"])
    lesson["intro_text"] = _j(data["intro_text"])
    lesson["vocabulary_json"] = _j(vocab)
    lesson["grammar_json"] = _j(grammar)
    lesson["dialogue_json"] = _j(dialogues)
    lesson["exercise_json"] = _j(exercises)
    lesson["answers_json"] = _j(answers)
    lesson["homework_json"] = _j(_homework_payload(vocab, grammar))
    return lesson
